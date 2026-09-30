from contextlib import closing
import json
import sqlite3
from types import SimpleNamespace

from cats import cli
from cats.forecast import AverageEstimate
from cats.history import (
    get_jobs_requiring_state_refresh,
    record_schedule_check,
    read_schedule_checks,
    update_schedule_job_state,
)
from cats.output import CATSOutput


def test_show_data_prints_all_records_without_duration(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "history.sqlite3"
    record_schedule_check(
        db_path,
        workload_key="analysis.sh",
        duration_minutes=30,
        location="RG1",
        action="submitted",
        active_job_id="123456",
    )
    monkeypatch.setenv("CATS_HISTORY_DB", str(db_path))

    assert cli.main(["--show-data"]) == 0

    records = json.loads(capsys.readouterr().out)
    assert len(records) == 1
    assert records[0]["workload_key"] == "analysis.sh"
    assert records[0]["active_job_id"] == "123456"


def test_report_deduplicates_jobs_and_separates_completed_savings(
    monkeypatch, tmp_path, capsys
):
    db_path = tmp_path / "history.sqlite3"
    record_schedule_check(
        db_path,
        workload_key="analysis.sh",
        duration_minutes=120,
        location="OX1",
        action="submitted",
        dynamic=True,
        active_job_id="completed-job",
        slurm_state="COMPLETED",
        estimated_emissions_now_g=1000.0,
        estimated_emissions_optimal_g=800.0,
    )
    record_schedule_check(
        db_path,
        workload_key="analysis.sh",
        duration_minutes=120,
        location="OX1",
        action="unchanged",
        dynamic=True,
        active_job_id="completed-job",
        slurm_state="COMPLETED",
        estimated_emissions_now_g=900.0,
        estimated_emissions_optimal_g=500.0,
    )
    record_schedule_check(
        db_path,
        workload_key="failed.sh",
        duration_minutes=60,
        location="RG1",
        action="submitted",
        active_job_id="failed-job",
        slurm_state="FAILED",
        estimated_emissions_now_g=300.0,
        estimated_emissions_optimal_g=100.0,
    )
    record_schedule_check(
        db_path,
        workload_key="pending.sh",
        duration_minutes=60,
        location="OX1",
        action="submitted",
        active_job_id="pending-job",
        slurm_state="PENDING",
    )
    monkeypatch.setenv("CATS_HISTORY_DB", str(db_path))
    monkeypatch.setattr(cli, "_refresh_history_job_states", lambda _: None)

    assert cli.main(["--report", "--format", "json"]) == 0

    report = json.loads(capsys.readouterr().out)
    assert report["schedule_checks"] == 4
    assert report["tracked_jobs"] == 3
    assert report["completed_jobs"] == 1
    assert report["failed_jobs"] == 1
    assert report["active_jobs"] == 1
    assert report["completed_runtime_hours"] == 2
    assert report["estimated_co2_saved_g_all_tracked_jobs"] == 400
    assert report["estimated_co2_saved_g_completed_jobs"] == 200
    assert report["completed_jobs_with_emissions_estimate"] == 1
    assert report["completed_jobs_by_location"]["OX1"]["completed_jobs"] == 1


def test_cli_records_successful_sbatch_submission(monkeypatch, tmp_path):
    start = cli.datetime.datetime.now().astimezone()
    now = AverageEstimate(100.0, start, start, 100.0, 100.0)
    optimal = AverageEstimate(50.0, start, start, 50.0, 50.0)

    class FakeProvider:
        def get_max_duration_minutes(self):
            return 2820

        def get_data(self, *args):
            return SimpleNamespace(
                metric="Carbon intensity",
                unit="gCO2eq/kWh",
                values=[],
            )

    class FakeWindowedForecast:
        def __init__(self, *args, **kwargs):
            pass

        def __getitem__(self, index):
            return now

        def __iter__(self):
            return iter([optimal])

    db_path = tmp_path / "history.sqlite3"
    monkeypatch.setenv("CATS_HISTORY_DB", str(db_path))
    monkeypatch.setattr(
        cli, "get_runtime_config", lambda args: (FakeProvider, "OX1", 5, None, None)
    )
    monkeypatch.setattr(cli, "WindowedForecast", FakeWindowedForecast)
    monkeypatch.setattr(cli, "schedule_sbatch", lambda output, args: ("123456", None))

    cli.run_cats(
        [
            "--duration",
            "5",
            "--loc",
            "OX1",
            "--scheduler",
            "sbatch",
            "--command",
            "./script.sh",
            "--dynamic",
        ]
    )

    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            row = connection.execute(
                """
                SELECT workload_key, duration_minutes, location,
                       current_ci_g_per_kwh, optimal_ci_g_per_kwh,
                      action, dynamic, active_job_id, max_window_minutes
                FROM schedule_checks
                """
            ).fetchone()

    assert row == (
        "script.sh",
        5,
        "OX1",
        100.0,
        50.0,
        "submitted",
        1,
        "123456",
        2820,
    )


def test_record_schedule_check_creates_database_and_record(tmp_path):
    db_path = tmp_path / "nested" / "history.sqlite3"

    record_id = record_schedule_check(
        db_path,
        workload_key="analysis.sh",
        duration_minutes=30,
        location="RG1",
        action="submitted",
        current_ci_g_per_kwh=100.0,
        optimal_start_utc="2026-09-30T12:00:00+00:00",
        optimal_ci_g_per_kwh=50.0,
        active_job_id="123456",
    )

    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            row = connection.execute(
                """
                SELECT workload_key, duration_minutes, location, current_ci_g_per_kwh,
                       optimal_start_utc, optimal_ci_g_per_kwh, action, active_job_id
                FROM schedule_checks WHERE id = ?
                """,
                (record_id,),
            ).fetchone()

    assert row == (
        "analysis.sh",
        30,
        "RG1",
        100.0,
        "2026-09-30T12:00:00+00:00",
        50.0,
        "submitted",
        "123456",
    )


def test_job_state_refresh_stops_for_terminal_state(tmp_path):
    db_path = tmp_path / "history.sqlite3"
    record_schedule_check(
        db_path,
        workload_key="analysis.sh",
        duration_minutes=30,
        location="RG1",
        action="submitted",
        active_job_id="123456",
        slurm_state="PENDING",
    )

    assert get_jobs_requiring_state_refresh(db_path) == ["123456"]
    update_schedule_job_state(db_path, "123456", "COMPLETED")
    assert get_jobs_requiring_state_refresh(db_path) == []


def test_read_schedule_checks_migrates_dynamic_column(tmp_path):
    db_path = tmp_path / "history.sqlite3"
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE schedule_checks (
                    id INTEGER PRIMARY KEY,
                    workload_key TEXT NOT NULL,
                    active_job_id TEXT
                )
            """)
            connection.execute(
                "INSERT INTO schedule_checks (workload_key, active_job_id) VALUES (?, ?)",
                ("older-job", "123456"),
            )

    records = read_schedule_checks(db_path)

    assert records[0]["dynamic"] is False
    assert records[0]["max_window_minutes"] == 2820
