import datetime
import yaml

class greenAlgorithmsCalculator():

    def __init__(self,
                 partition, runtime, memory, nCPUcores, nGPUcores,
                 averageBest_carbonIntensity, averageNow_carbonIntensity
                 ):
        '''

        :param partition: [str] has to match one of the partitions in `config.yml`
        :param runtime: [datetime.timedelta]
        :param memory: [int] in GB
        :param nCPUcores: [int]
        :param nGPUcores: [int]
        :param averageBest_carbonIntensity: [float] in gCO2e/kWh
        :param averageNow_carbonIntensity: [float] in gCO2e/kWh
        '''
        ### Load cluster specific info
        with open("config.yml", "r") as stream:
            try:
                self.cluster_info = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        ### Load fixed parameters
        with open("fixed_parameters.yaml", "r") as stream:
            try:
                self.fParams = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        self.partition = partition
        self.runtime = runtime
        self.memory = memory
        self.nCPUcores = nCPUcores
        self.nGPUcores = nGPUcores
        self.averageBest_carbonIntensity = averageBest_carbonIntensity
        self.averageNow_carbonIntensity = averageNow_carbonIntensity

    def formatText_footprint(self, footprint_g):
        '''
        Format the text to display the carbon footprint
        :param footprint_g: [float] carbon footprint, in gCO2e
        :return: [str] the text to display
        '''
        if footprint_g < 1e3:
            text_footprint = f"{footprint_g:,.0f} gCO2e"
        elif footprint_g < 1e6:
            text_footprint = f"{footprint_g / 1e3:,.0f} kgCO2e"
        else:
            text_footprint = f"{footprint_g / 1e3:,.0f} TCO2e"
        return text_footprint

    def formatText_treemonths(self, tm_float):
        '''
        Format the text to display the tree months
        :param tm_float: [float] tree-months
        :return: [str] the text to display
        '''
        tm = int(tm_float)
        ty = int(tm / 12)
        if tm < 1:
            text_trees = f"{tm_float:.3f} tree-months"
        elif tm == 1:
            text_trees = f"{tm_float:.1f} tree-month"
        elif tm < 6:
            text_trees = f"{tm_float:.1f} tree-months"
        elif tm <= 24:
            text_trees = f"{tm} tree-months"
        elif tm < 120:
            text_trees = f"{ty} tree-years and {tm - ty * 12} tree-months"
        else:
            text_trees = f"{ty} tree-years"
        return text_trees

    def formatText_driving(self,dist):
        '''
        Format the text to display the driving distance
        :param dist: [float] driving distance, in km
        :return: [str] text to display
        '''
        if dist < 10:
            text_driving = f"driving {dist:,.2f} km"
        else:
            text_driving = f"driving {dist:,.0f} km"
        return text_driving

    def formatText_flying(self, footprint_g, fParams):
        '''
        Format the text to display about flying
        :param footprint_g: [float] carbon footprint, in gCO2e
        :param fParams: [dict] Fixed parameters, from fixed_parameters.yaml
        :return: [str] text to display
        '''
        if footprint_g < 0.5 * fParams['flight_NY_SF']:
            text_flying = f"{footprint_g / fParams['flight_PAR_LON']:,.2f} flights between Paris and London"
        elif footprint_g < 0.5 * fParams['flight_NYC_MEL']:
            text_flying = f"{footprint_g / fParams['flight_NY_SF']:,.2f} flights between New York and San Francisco"
        else:
            text_flying = f"{footprint_g / fParams['flight_NYC_MEL']:,.2f} flights between New York and Melbourne"
        return text_flying

    def calculate_energies(self):

        ### Power draw CPU and GPU
        partition_info = self.cluster_info['partitions'][self.partition]
        if partition_info['type'] == 'CPU':
            TDP2use4CPU = partition_info['TDP']
            TDP2use4GPU = 0
        else:
            TDP2use4CPU = partition_info['TDP_CPU']
            TDP2use4GPU = partition_info['TDP']

        ### Energy usage
        energies = {
            'energy_CPUs': self.runtime.total_seconds() / 3600 * self.nCPUcores * TDP2use4CPU / 1000,  # in kWh
            'energy_GPUs': self.runtime.total_seconds() / 3600 * self.nGPUcores * TDP2use4GPU / 1000,  # in kWh
            'energy_memory': self.runtime.total_seconds() / 3600 * self.memory * self.fParams['power_memory_perGB'] / 1000  # in kWh
        }

        energies['total_energy'] = self.cluster_info['PUE'] * (energies['energy_CPUs'] + energies['energy_GPUs'] + energies['energy_memory'])

        return energies

    def calculate_CF(self, energies):

        CF_best = {
            'CF_CPUs': energies['energy_CPUs'] * self.averageBest_carbonIntensity,
            'CF_GPUs': energies['energy_GPUs'] * self.averageBest_carbonIntensity,
            'CF_memory': energies['energy_memory'] * self.averageBest_carbonIntensity,
            'total_CF': energies['total_energy'] * self.averageBest_carbonIntensity
        }

        CF_now = {
            'CF_CPUs': energies['energy_CPUs'] * self.averageNow_carbonIntensity,
            'CF_GPUs': energies['energy_GPUs'] * self.averageNow_carbonIntensity,
            'CF_memory': energies['energy_memory'] * self.averageNow_carbonIntensity,
            'total_CF': energies['total_energy'] * self.averageNow_carbonIntensity
        }

        return CF_best, CF_now

    def get_results(self, energies, CF_best, CF_now):

        clusterName = self.cluster_info['cluster_name']

        text_total_CFbest = self.formatText_footprint(CF_best['total_CF'])
        text_total_CFnow = self.formatText_footprint(CF_now['total_CF'])
        text_diffCF = self.formatText_footprint(CF_now['total_CF'] - CF_best['total_CF'])

        report = f'''
                  #####  Your carbon footprint on the {clusterName} platform  #####

                  By running at the suggested time: {text_total_CFbest}
                  
                  ...vs running now: {text_total_CFnow} (- {text_diffCF})
                
        '''

        return report

    def get_footprint(self):
        energies = self.calculate_energies()
        CF_best, CF_now = self.calculate_CF(energies)

        return get_results(energies, CF_best, CF_now)

if __name__ == "__main__":
    GAcalc = greenAlgorithmsCalculator(
        partition = 'GPU_partition',
        runtime = datetime.timedelta(hours = 5),
        memory = 32,
        nCPUcores = 3,
        nGPUcores = 16,
        averageBest_carbonIntensity = 80,
        averageNow_carbonIntensity = 290
    )
    rslt = GAcalc.get_footprint()
