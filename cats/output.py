import dataclasses
import json
import logging
from typing import Optional

from .carbonFootprint import Estimates
from .forecast import CarbonIntensityAverageEstimate

@dataclasses.dataclass
class CATSOutput:
    """
    Carbon Aware Task Scheduler output
    
    A dataclass to contain CATS output information for use
    with schedulers accompanied by methods to represent this
    information when reporting to users.
    """

    carbonIntensityNow: CarbonIntensityAverageEstimate
    carbonIntensityOptimal: CarbonIntensityAverageEstimate
    location: str
    countryISO3: str
    emmissionEstimate: Optional[Estimates] = None
    colour: bool = False

    def __str__(self) -> str:
        if self.colour:
            # Default colour
            col_normal = "\33[0m"  # reset any colour

            # Colours to indicate optimal/better results
            col_dt_opt = "\33[32m"  # green i.e. 'good' in traffic light rating
            col_ci_opt = "\33[32m"  # green
            col_ee_opt = "\33[32m"  # green

            # Colours to indicate original and non-optimal results
            col_ci_now = "\33[31m"  # red i.e. 'bad' in traffic light rating
            col_ee_now = "\33[31m"  # red
        else:
            col_normal = ""
            col_dt_opt = ""
            col_ci_opt = ""
            col_ci_now = ""
            col_ee_now = ""
            col_ee_opt = ""

        out = f"""
Best job start time                       = {col_dt_opt}{self.carbonIntensityOptimal.start:%Y-%m-%d %H:%M:%S}{col_normal}
Carbon intensity if job started now       = {col_ci_now}{self.carbonIntensityNow.value:.2f} gCO2eq/kWh{col_normal}
Carbon intensity at optimal time          = {col_ci_opt}{self.carbonIntensityOptimal.value:.2f} gCO2eq/kWh{col_normal}"""

        if self.emmissionEstimate:
            out += f"""
Estimated emissions if job started now    = {col_ee_now}{self.emmissionEstimate.now}{col_normal}
Estimated emissions at optimal time       = {col_ee_opt}{self.emmissionEstimate.best} (- {self.emmissionEstimate.savings}){col_normal}"""

        logging.info("Use '--format=json' to get this in machine readable format")
        return out

    def to_json(self, dateformat: str = "", **kwargs) -> str:
        data = dataclasses.asdict(self)
        for ci in ["carbonIntensityNow", "carbonIntensityOptimal"]:
            if dateformat == "":
                data[ci]["start"] = data[ci]["start"].isoformat()
                data[ci]["end"] = data[ci]["end"].isoformat()
            else:
                data[ci]["start"] = data[ci]["start"].strftime(dateformat)
                data[ci]["end"] = data[ci]["end"].strftime(dateformat)

        return json.dumps(data, **kwargs)