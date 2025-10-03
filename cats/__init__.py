import dataclasses
import json
import logging
import subprocess

from typing import Optional

from .carbonFootprint import Estimates, get_footprint_reduction_estimate
from .CI_api_interface import InvalidLocationError
from .CI_api_query import get_CI_forecast  # noqa: F401
from .configure import get_runtime_config
from .plotting import plotplan
from .forecast import CarbonIntensityAverageEstimate, WindowedForecast

__version__ = "1.1.0"

# To add a scheduler, add a date format here
# and create a scheduler_<new>(...) function
SCHEDULER_DATE_FORMAT = {"at": "%Y%m%d%H%M", "sbatch": "%Y-%m-%dT%H:%M"}


@dataclasses.dataclass
class CATSOutput:
    """Carbon Aware Task Scheduler output"""

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


def schedule_at(output: CATSOutput, args: list[str]) -> Optional[str]:
    """Schedule job with optimal start time using at(1)

    :return: Error as a string, or None if successful
    """
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    try:
        subprocess.check_output(
            (
                "at",
                "-t",
                output.carbonIntensityOptimal.start.strftime(
                    SCHEDULER_DATE_FORMAT["at"]
                ),
            ),
            stdin=proc.stdout,
        )
        return None
    except FileNotFoundError:
        return "No at command found in PATH, please install one"
    except subprocess.CalledProcessError as e:
        return f"Scheduling with at failed with code {e.returncode}, see output below:\n{e.output}"


def schedule_sbatch(output: CATSOutput, args: list[str]) -> Optional[str]:
    """Schedule job with optimal start time using sbatch(1)

    :return: Error as a string, or None if successful
    """
    try:
        sbatch_output = subprocess.check_output(
            [
                "sbatch",
                "--begin",
                output.carbonIntensityOptimal.start.strftime(
                    SCHEDULER_DATE_FORMAT["sbatch"]
                ),
                *args,
            ]
        )
        print(sbatch_output.decode("utf-8"))
        return None
    except FileNotFoundError:
        return "No sbatch command found in PATH, ensure slurm is configured correctly"
    except subprocess.CalledProcessError as e:  # pragma: no cover
        return f"Scheduling with sbatch failed with code {e.returncode}, see output below:\n{e.output}"

