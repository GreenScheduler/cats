from collections import namedtuple
import datetime
import yaml


Estimates = namedtuple("Estimates", ["now", "best", "savings"])


class greenAlgorithmsCalculator:
    def __init__(
            self,
            config,
            jobinfo,
            duration,
            averageBest_carbonIntensity,
            averageNow_carbonIntensity,
    ):
        self.config = config
        self.jobinfo = jobinfo
        self.duration = duration
        self.averageBest_carbonIntensity = averageBest_carbonIntensity
        self.averageNow_carbonIntensity = averageNow_carbonIntensity

        ### Load fixed parameters
        with open("fixed_parameters.yaml", "r") as stream:
            try:
                self.fParams = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def formatText_footprint(self, footprint_g):
        """
        Format the text to display the carbon footprint
        :param footprint_g: [float] carbon footprint, in gCO2e
        :return: [str] the text to display
        """
        if footprint_g < 1e3:
            text_footprint = f"{footprint_g:,.2f} gCO2e"
        elif footprint_g < 1e6:
            text_footprint = f"{footprint_g / 1e3:,.2f} kgCO2e"
        else:
            text_footprint = f"{footprint_g / 1e3:,.2f} TCO2e"
        return text_footprint

    def _formatText_treemonths(self, tm_float):
        """
        Format the text to display the tree months
        :param tm_float: [float] tree-months
        :return: [str] the text to display
        """
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

    def _formatText_driving(self, dist):
        """
        Format the text to display the driving distance
        :param dist: [float] driving distance, in km
        :return: [str] text to display
        """
        if dist < 10:
            text_driving = f"driving {dist:,.2f} km"
        else:
            text_driving = f"driving {dist:,.0f} km"
        return text_driving

    def _formatText_flying(self, footprint_g, fParams):
        """
        Format the text to display about flying
        :param footprint_g: [float] carbon footprint, in gCO2e
        :param fParams: [dict] Fixed parameters, from fixed_parameters.yaml
        :return: [str] text to display
        """
        if footprint_g < 0.5 * fParams["flight_NY_SF"]:
            text_flying = f"{footprint_g / fParams['flight_PAR_LON']:,.2f} flights between Paris and London"
        elif footprint_g < 0.5 * fParams["flight_NYC_MEL"]:
            text_flying = f"{footprint_g / fParams['flight_NY_SF']:,.2f} flights between New York and San Francisco"
        else:
            text_flying = f"{footprint_g / fParams['flight_NYC_MEL']:,.2f} flights between New York and Melbourne"
        return text_flying

    def _calculate_energies(self):
        ### Power draw CPU and GPU
        partition_info = self.config["partitions"][self.jobinfo['partition']]
        if partition_info["type"] == "CPU":
            TDP2use4CPU = partition_info["TDP"]
            TDP2use4GPU = 0
        else:
            TDP2use4CPU = partition_info["TDP_CPU"]
            TDP2use4GPU = partition_info["TDP"]

        ### Energy usage
        # keeping the breakdown by component as it can be useful for reporting later
        energies = {
            "cpus": self.duration.total_seconds()
            / 3600
            * self.jobinfo['cpus']
            * TDP2use4CPU
            / 1000,  # in kWh
            "gpus": self.duration.total_seconds()
            / 3600
            * self.jobinfo['gpus']
            * TDP2use4GPU
            / 1000,  # in kWh
            "memory": self.duration.total_seconds()
            / 3600
            * self.jobinfo['memory']
            * self.fParams["power_memory_perGB"]
            / 1000,  # in kWh
        }

        energies["total"] = self.config["PUE"] * (
            energies["cpus"]
            + energies["gpus"]
            + energies["memory"]
        )

        return energies

    def _calculate_CF(self, energies):
        CFs = {
            'best': {},
            'now': {}
        }
        for key, energy in energies.items():
            CFs['best'][key] = energy * self.averageBest_carbonIntensity.value
            CFs['now'][key] = energy * self.averageNow_carbonIntensity.value

        return CFs

    def get_carbonFootprint(self):
        energies = self._calculate_energies()
        CFs = self._calculate_CF(energies)
        return CFs, energies
