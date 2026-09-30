import re
import subprocess
from datetime import datetime
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
                output.valueOptimal.start.strftime(SCHEDULER_DATE_FORMAT["at"]),
            ),
            stdin=proc.stdout,
        )
        return None
    except FileNotFoundError:
        return "No at command found in PATH, please install one"
    except subprocess.CalledProcessError as e:
        return f"Scheduling with at failed with code {e.returncode}, see output below:\n{e.output}"


def schedule_sbatch(
    output: CATSOutput, args: list[str]
) -> tuple[str | None, str | None]:
    """Schedule job with optimal start time using sbatch(1)

    :return: A Slurm job ID and an error, if any
    """
    try:
        sbatch_output = subprocess.check_output(
            [
                "sbatch",
                "--begin",
                output.valueOptimal.start.strftime(SCHEDULER_DATE_FORMAT["sbatch"]),
                *args,
            ]
        )
        print(sbatch_output.decode("utf-8"))
        match = re.search(rb"Submitted batch job (\d+)", sbatch_output)
        if match is None:
            return None, "Could not determine Slurm job ID from sbatch output"
        return match.group(1).decode("ascii"), None
    except FileNotFoundError:
        return (
            None,
            "No sbatch command found in PATH, ensure slurm is configured correctly",
        )
    except subprocess.CalledProcessError as e:  # pragma: no cover
        return (
            None,
            f"Scheduling with sbatch failed with code {e.returncode}, see output below:\n{e.output}",
        )


def get_sbatch_job_state(job_id: str) -> str | None:
    """Return the current or final Slurm state for a job, if available."""
    try:
        queue_output = subprocess.check_output(
            ["squeue", "-h", "-j", job_id, "-o", "%T"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if queue_output:
            return queue_output.splitlines()[0].strip().upper()
    except (OSError, subprocess.CalledProcessError):
        pass

    try:
        accounting_output = subprocess.check_output(
            [
                "sacct",
                "--noheader",
                "--parsable2",
                "--jobs",
                job_id,
                "--format=JobIDRaw,State",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    for line in accounting_output.splitlines():
        fields = line.strip().split("|")
        if len(fields) >= 2 and fields[0] == job_id:
            state = fields[1].strip().split()[0].rstrip("+").upper()
            return state or None
    return None


def get_sbatch_job_start_time(job_id: str) -> datetime | None:
    try:
        output = subprocess.check_output(
            ["scontrol", "show", "job", "-o", job_id],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    match = re.search(r"(?:^|\s)StartTime=([^\s]+)", output)
    if match is None or match.group(1) in {"Unknown", "N/A"}:
        return None

    try:
        return datetime.fromisoformat(match.group(1)).astimezone()
    except ValueError:
        return None


def update_sbatch_job_start_time(job_id: str, start_time: datetime) -> None:
    subprocess.check_output(
        [
            "scontrol",
            "update",
            f"JobId={job_id}",
            f"StartTime={start_time.astimezone().strftime('%Y-%m-%dT%H:%M:%S')}",
        ],
        text=True,
        stderr=subprocess.STDOUT,
    )
