import dataclasses
import json
import logging
from typing import Optional

from .carbonFootprint import Estimates
from .forecast import AverageEstimate


@dataclasses.dataclass
class CATSOutput:
    """
    Carbon Aware Task Scheduler output

    A dataclass to contain CATS output information for use
    with schedulers accompanied by methods to represent this
    information when reporting to users.
    """

    metric: str
    valueNow: AverageEstimate
    valueOptimal: AverageEstimate
    location: str
    countryISO3: str
    unit: str
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
Best job start time                       = {col_dt_opt}{self.valueOptimal.start:%Y-%m-%d %H:%M:%S}{col_normal}
{self.metric} if job started now       = {col_ci_now}{self.valueNow.value:.2f} {self.unit}{col_normal}
{self.metric} at optimal time          = {col_ci_opt}{self.valueOptimal.value:.2f} {self.unit}{col_normal}"""

        if self.emmissionEstimate:
            out += f"""
Estimated emissions if job started now    = {col_ee_now}{self.emmissionEstimate.now}{col_normal}
Estimated emissions at optimal time       = {col_ee_opt}{self.emmissionEstimate.best} (- {self.emmissionEstimate.savings}){col_normal}"""

        logging.info("Use '--format=json' to get this in machine readable format")
        return out

    def to_json(self, dateformat: str = "", **kwargs) -> str:
        data = dataclasses.asdict(self)
        for val in ["valueNow", "valueOptimal"]:
            if dateformat == "":
                data[val]["start"] = data[val]["start"].isoformat()
                data[val]["end"] = data[val]["end"].isoformat()
            else:
                data[val]["start"] = data[val]["start"].strftime(dateformat)
                data[val]["end"] = data[val]["end"].strftime(dateformat)

        return json.dumps(data, **kwargs)
