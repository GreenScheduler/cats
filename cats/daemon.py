"""Background worker for dynamically scheduled Slurm jobs."""

import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime

from .history import (
    get_dynamic_schedule_checks,
    record_schedule_check,
    update_schedule_job_state,
)
from .schedulers import (
    get_sbatch_job_start_time,
    get_sbatch_job_state,
    update_sbatch_job_start_time,
)

DEFAULT_INTERVAL_SECONDS = 3600
DEFAULT_API = "carbonintensity.org.uk"


def process_dynamic_jobs_once(
    db_path: str,
    cats_executable: str | None = None,
) -> None:
    cats_executable = (
        cats_executable or os.environ.get("CATS_EXECUTABLE") or shutil.which("cats")
    )
    if not cats_executable:
        raise RuntimeError("Could not find the CATS executable for daemon forecasts")

    for job in get_dynamic_schedule_checks(db_path):
        job_id = str(job["active_job_id"])
        state = get_sbatch_job_state(job_id)
        if state is None:
<<<<<<< HEAD
            logging.warning("Could not read state for dynamic Slurm job %s", job_id)
=======
            logging.warning(
                "Could not read state for dynamic %s job %s", scheduler, job_id
            )
>>>>>>> a17a830f1a070c5390a7e28631c2ee88089ecac5
            continue

        update_schedule_job_state(db_path, job_id, state)
        if state != "PENDING":
            continue

        try:
            forecast_output = subprocess.check_output(
                [
                    cats_executable,
                    "--duration",
                    str(job["duration_minutes"]),
                    "--location",
                    str(job["location"]),
                    "--api",
                    str(job.get("api") or DEFAULT_API),
                    "--window",
                    str(job.get("max_window_minutes") or 2820),
                    "--format=json",
                ],
                text=True,
            )
            forecast = json.loads(forecast_output)
            optimal = forecast["valueOptimal"]
            optimal_start = datetime.fromisoformat(optimal["start"]).astimezone()
            current_start = get_sbatch_job_start_time(job_id)
            should_update = (
                current_start is None
                or abs((optimal_start - current_start).total_seconds()) >= 60
            )

            action = "unchanged"
            error_message = None
            if should_update:
                try:
<<<<<<< HEAD
                    update_sbatch_job_start_time(job_id, optimal_start)
=======
                    if scheduler == "at":
                        active_job_id, error_message = reschedule_at_job(
                            job_id,
                            optimal_start,
                            shlex.split(str(job["command"])),
                            str(job["working_directory"])
                            if job.get("working_directory")
                            else None,
                        )
                        if error_message or active_job_id is None:
                            raise RuntimeError(
                                error_message or "at rescheduling failed"
                            )
                        update_schedule_job_state(
                            db_path, job_id, "RESCHEDULED", scheduler="at"
                        )
                    else:
                        update_sbatch_job_start_time(job_id, optimal_start)
>>>>>>> a17a830f1a070c5390a7e28631c2ee88089ecac5
                    action = "rescheduled"
                except (OSError, subprocess.CalledProcessError) as error:
                    action = "update_failed"
                    error_message = str(error)
                    logging.warning(
                        "Could not update dynamic Slurm job %s: %s", job_id, error
                    )

            record_schedule_check(
                db_path,
                workload_key=str(job["workload_key"]),
                duration_minutes=int(job["duration_minutes"]),
                location=str(job["location"]),
                action=action,
                dynamic=True,
                api=str(job.get("api") or DEFAULT_API),
                max_window_minutes=int(job.get("max_window_minutes") or 2820),
                current_ci_g_per_kwh=forecast["valueNow"]["value"],
                optimal_start_utc=optimal_start.isoformat(),
                optimal_ci_g_per_kwh=optimal["value"],
                previous_job_id=job_id,
                active_job_id=job_id,
                slurm_state="PENDING",
                error=error_message,
            )
        except (
            OSError,
            subprocess.CalledProcessError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            logging.warning(
                "Dynamic scheduling check failed for job %s: %s", job_id, error
            )


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("CATS_DAEMON_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    db_path = os.environ.get("CATS_HISTORY_DB")
    if not db_path:
        raise SystemExit("CATS_HISTORY_DB must be set for catsd")

    try:
        interval = int(os.environ.get("CATS_DAEMON_INTERVAL_SECONDS", "3600"))
    except ValueError as error:
        raise SystemExit("CATS_DAEMON_INTERVAL_SECONDS must be an integer") from error
    if interval < 1:
        raise SystemExit("CATS_DAEMON_INTERVAL_SECONDS must be positive")

    logging.info("CATS dynamic scheduler started; polling every %s seconds", interval)
    while True:
        try:
            process_dynamic_jobs_once(db_path)
        except Exception:
            logging.exception("CATS dynamic scheduling cycle failed")
        time.sleep(interval)
