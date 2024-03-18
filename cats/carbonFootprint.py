import datetime
from collections import namedtuple

import yaml

Estimates = namedtuple("Estimates", ["now", "best", "savings"])


class greenAlgorithmsCalculator:
    def __init__(
        self,
        PUE: float,
        jobinfo: list[tuple[int, float]],
        runtime: datetime.timedelta,
        averageBest_carbonIntensity: float,
        averageNow_carbonIntensity: float,
    ):
        """
        :param PUE: [float] Cluster PUE
        :param jobinfo: [list[tuple[int, float]]]
        :param runtime: [datetime.timedelta]
        :param averageBest_carbonIntensity: [float] in gCO2e/kWh
        :param averageNow_carbonIntensity: [float] in gCO2e/kWh
        """

        #  Load fixed parameters
        with open("fixed_parameters.yaml", "r") as stream:
            try:
                self.fParams = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        self.PUE = PUE
        self.jobinfo = jobinfo
        self.runtime = runtime
        self.averageBest_carbonIntensity = averageBest_carbonIntensity
        self.averageNow_carbonIntensity = averageNow_carbonIntensity

    def formatText_footprint(self, footprint_g):
        """
        Format the text to display the carbon footprint
        :param footprint_g: [float] carbon footprint, in gCO2e
        :return: [str] the text to display
        """
        if footprint_g < 1e3:
            text_footprint = f"{footprint_g:,.0f} gCO2e"
        elif footprint_g < 1e6:
            text_footprint = f"{footprint_g / 1e3:,.0f} kgCO2e"
        else:
            text_footprint = f"{footprint_g / 1e3:,.0f} TCO2e"
        return text_footprint

    def formatText_treemonths(self, tm_float):
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

    def formatText_driving(self, dist):
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

    def formatText_flying(self, footprint_g, fParams):
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

    def get_footprint(self):
        runtime = self.runtime.total_seconds() / 3600
        energy = (
            self.PUE
            * runtime
            * sum([(nunits * power) / 1000 for nunits, power in self.jobinfo])
        )
        best = energy * self.averageBest_carbonIntensity
        now = energy * self.averageNow_carbonIntensity

        return Estimates(
            *[self.formatText_footprint(e) for e in [now, best, now - best]]
        )
