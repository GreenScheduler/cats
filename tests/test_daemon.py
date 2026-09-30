import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta

from cats import daemon
from cats.history import read_schedule_checks, record_schedule_check


def test_process_dynamic_jobs_reschedules_pending_job(monkeypatch, tmp_path):
    db_path = tmp_path / "history.sqlite3"
    record_schedule_check(
        db_path,
        workload_key="sleep",
        duration_minutes=5,
        location="RG1",
        action="submitted",
        dynamic=True,
        api="carbonintensity.org.uk",
        active_job_id="123456",
        slurm_state="PENDING",
    )
    optimal_start = datetime.now().astimezone() + timedelta(hours=4)
    original_start = optimal_start - timedelta(hours=2)
    updates = []

    monkeypatch.setattr(daemon, "get_sbatch_job_state", lambda job_id: "PENDING")
    monkeypatch.setattr(daemon, "get_sbatch_job_start_time", lambda job_id: original_start)
    monkeypatch.setattr(
        daemon,
        "update_sbatch_job_start_time",
        lambda job_id, start: updates.append((job_id, start)),
    )
    monkeypatch.setattr(
        daemon.subprocess,
        "check_output",
        lambda *args, **kwargs: json.dumps(
            {
                "valueNow": {"value": 80.0},
                "valueOptimal": {
                    "start": optimal_start.isoformat(),
                    "value": 40.0,
                },
            }
        ),
    )

    daemon.process_dynamic_jobs_once(str(db_path), cats_executable="cats")

    assert updates == [("123456", optimal_start)]
    records = read_schedule_checks(db_path)
    assert records[-1]["action"] == "rescheduled"
    assert records[-1]["dynamic"] is True
    assert records[-1]["optimal_ci_g_per_kwh"] == 40.0


def test_process_dynamic_jobs_does_not_reforecast_running_job(monkeypatch, tmp_path):
    db_path = tmp_path / "history.sqlite3"
    record_schedule_check(
        db_path,
        workload_key="sleep",
        duration_minutes=5,
        location="RG1",
        action="submitted",
        dynamic=True,
        active_job_id="123456",
        slurm_state="PENDING",
    )
    monkeypatch.setattr(daemon, "get_sbatch_job_state", lambda job_id: "RUNNING")
    monkeypatch.setattr(
        daemon.subprocess,
        "check_output",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected forecast")),
    )

    daemon.process_dynamic_jobs_once(str(db_path), cats_executable="cats")

    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            state = connection.execute(
                "SELECT slurm_state FROM schedule_checks WHERE active_job_id = ?",
                ("123456",),
            ).fetchone()[0]
    assert state == "RUNNING"