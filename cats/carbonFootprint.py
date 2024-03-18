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
