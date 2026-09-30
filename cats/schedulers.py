import re
import shlex
import subprocess
from datetime import datetime

from .output import CATSOutput

# To add a scheduler, add a date format here
# and create a scheduler_<new>(...) function
SCHEDULER_DATE_FORMAT = {"at": "%Y%m%d%H%M", "sbatch": "%Y-%m-%dT%H:%M"}


def schedule_at(
    output: CATSOutput, args: list[str]
) -> tuple[str | None, str | None]:
    return schedule_at_start(output.valueOptimal.start, args)


def schedule_at_start(
    start_time: datetime, args: list[str], cwd: str | None = None
) -> tuple[str | None, str | None]:
    """Schedule job with optimal start time using at(1)

    :return: An at job ID and an error, if any
    """
    try:
        output = subprocess.check_output(
            [
                "at",
                "-t",
                start_time.strftime(SCHEDULER_DATE_FORMAT["at"]),
            ],
            input=shlex.join(args) + "\n",
            text=True,
            stderr=subprocess.STDOUT,
            cwd=cwd,
        )
        match = re.search(r"\bjob\s+(\d+)\b", output, re.IGNORECASE)
        if match is None:
            return None, "Could not determine at job ID from at output"
        return match.group(1), None
    except FileNotFoundError:
        return None, "No at command found in PATH, please install one"
    except subprocess.CalledProcessError as e:
        return None, f"Scheduling with at failed with code {e.returncode}, see output below:\n{e.output}"


def get_at_job_state(job_id: str) -> str | None:
    """Return PENDING when an at job is still in the queue."""
    try:
        queue_output = subprocess.check_output(
            ["atq"], text=True, stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    if any(
        line.split() and line.split()[0] == job_id
        for line in queue_output.splitlines()
    ):
        return "PENDING"
    return "NOT_PENDING"


def remove_at_job(job_id: str) -> None:
    subprocess.check_output(["atrm", job_id], stderr=subprocess.STDOUT)


def reschedule_at_job(
    job_id: str,
    start_time: datetime,
    args: list[str],
    cwd: str | None = None,
) -> tuple[str | None, str | None]:
    new_job_id, error = schedule_at_start(start_time, args, cwd)
    if error or new_job_id is None:
        return None, error or "Could not determine replacement at job ID"

    try:
        remove_at_job(job_id)
    except (OSError, subprocess.CalledProcessError) as error:
        try:
            remove_at_job(new_job_id)
        except (OSError, subprocess.CalledProcessError):
            pass
        return None, f"Could not remove previous at job {job_id}: {error}"
    return new_job_id, None


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
        return None, "No sbatch command found in PATH, ensure slurm is configured correctly"
    except subprocess.CalledProcessError as e:  # pragma: no cover
        return None, f"Scheduling with sbatch failed with code {e.returncode}, see output below:\n{e.output}"


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
