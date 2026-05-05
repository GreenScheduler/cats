import subprocess

from typing import Optional

from .carbonFootprint import Estimates, get_footprint_reduction_estimate
from .CI_api_interface import InvalidLocationError
from .CI_api_query import get_CI_forecast  # noqa: F401
from .configure import get_runtime_config
from .plotting import plotplan
from .output import CATSOutput
from .forecast import (
    CarbonIntensityAverageEstimate,
    WindowedForecast,
)
from .cli import ( # Functions moved - this is for testing
    main,
    parse_time_constraint,
    validate_window_constraints,
    parse_arguments,
    print_banner,
) 
from .version import version as __version__

# To add a scheduler, add a date format here
# and create a scheduler_<new>(...) function
SCHEDULER_DATE_FORMAT = {"at": "%Y%m%d%H%M", "sbatch": "%Y-%m-%dT%H:%M"}

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

