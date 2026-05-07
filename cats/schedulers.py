import subprocess

from typing import Optional

from .output import CATSOutput

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

