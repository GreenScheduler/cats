import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

_TERMINAL_SLURM_STATES = (
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "TIMEOUT",
    "PREEMPTED",
    "NODE_FAIL",
    "OUT_OF_MEMORY",
    "BOOT_FAIL",
    "DEADLINE",
    "REVOKED",
    "SPECIAL_EXIT",
)


def record_schedule_check(
    db_path: str | Path,
    *,
    workload_key: str,
    duration_minutes: int,
    location: str,
    action: str,
    dynamic: bool = False,
    api: str = "carbonintensity.org.uk",
    max_window_minutes: int = 2820,
    current_ci_g_per_kwh: float | None = None,
    optimal_start_utc: str | None = None,
    optimal_ci_g_per_kwh: float | None = None,
    estimated_emissions_now_g: float | None = None,
    estimated_emissions_optimal_g: float | None = None,
    previous_job_id: str | None = None,
    active_job_id: str | None = None,
    slurm_state: str | None = None,
    error: str | None = None,
) -> int:
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive")

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    checked_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS schedule_checks (
                    id INTEGER PRIMARY KEY,
                    workload_key TEXT NOT NULL,
                    checked_at_utc TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL
                        CHECK (duration_minutes > 0),
                    location TEXT NOT NULL,
                    current_ci_g_per_kwh REAL,
                    optimal_start_utc TEXT,
                    optimal_ci_g_per_kwh REAL,
                    estimated_emissions_now_g REAL,
                    estimated_emissions_optimal_g REAL,
                    action TEXT NOT NULL,
                    dynamic INTEGER NOT NULL DEFAULT 0
                        CHECK (dynamic IN (0, 1)),
                    api TEXT NOT NULL DEFAULT 'carbonintensity.org.uk',
                    max_window_minutes INTEGER NOT NULL DEFAULT 2820
                        CHECK (max_window_minutes > 0),
                    previous_job_id TEXT,
                    active_job_id TEXT,
                    slurm_state TEXT,
                    error TEXT
                )
            """)
            _ensure_history_columns(connection)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS schedule_checks_workload_time
                ON schedule_checks (workload_key, checked_at_utc)
            """)

            cursor = connection.execute(
                """
                INSERT INTO schedule_checks (
                    workload_key,
                    checked_at_utc,
                    duration_minutes,
                    location,
                    current_ci_g_per_kwh,
                    optimal_start_utc,
                    optimal_ci_g_per_kwh,
                    estimated_emissions_now_g,
                    estimated_emissions_optimal_g,
                    action,
                    dynamic,
                    api,
                    max_window_minutes,
                    previous_job_id,
                    active_job_id,
                    slurm_state,
                    error
<<<<<<< HEAD
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workload_key,
                checked_at_utc,
                duration_minutes,
                location,
                current_ci_g_per_kwh,
                optimal_start_utc,
                optimal_ci_g_per_kwh,
                estimated_emissions_now_g,
                estimated_emissions_optimal_g,
                action,
                int(dynamic),
                api,
                max_window_minutes,
                previous_job_id,
                active_job_id,
                slurm_state,
                error,
            ))

            return cursor.lastrowid


def read_schedule_checks(db_path: str | Path) -> list[dict[str, object]]:
    path = Path(db_path)
    if not path.is_file():
        return []

    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        with connection:
            table_exists = connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'schedule_checks'
                """
            ).fetchone()
            if table_exists is None:
                return []

            _ensure_history_columns(connection)
            records = []
            for row in connection.execute("SELECT * FROM schedule_checks ORDER BY id"):
                record = dict(row)
                record["dynamic"] = bool(record["dynamic"])
                records.append(record)
            return records


def summarize_schedule_checks(
    records: list[dict[str, object]],
) -> dict[str, object]:
    """Summarize tracked jobs once each, despite dynamic forecast history rows."""
    jobs: dict[str, dict[str, object]] = {}
    for record in records:
        job_id = record.get("active_job_id")
        if job_id is None:
            continue

        key = str(job_id)
        job = jobs.get(key)
        if job is None:
            job = {
                "state": record.get("slurm_state"),
                "dynamic": bool(record.get("dynamic")),
                "duration_minutes": record.get("duration_minutes"),
                "location": record.get("location") or "unknown",
                "workload_key": record.get("workload_key") or "unknown",
                "estimated_emissions_now_g": record.get("estimated_emissions_now_g"),
                "estimated_emissions_optimal_g": record.get(
                    "estimated_emissions_optimal_g"
                ),
            }
            jobs[key] = job
        else:
            job["state"] = record.get("slurm_state") or job["state"]
            job["dynamic"] = bool(job["dynamic"]) or bool(record.get("dynamic"))
            for field in (
                "estimated_emissions_now_g",
                "estimated_emissions_optimal_g",
            ):
                if job[field] is None and record.get(field) is not None:
                    job[field] = record[field]

    completed = [
        job for job in jobs.values() if str(job["state"] or "").upper() == "COMPLETED"
    ]
    failed = [
        job
        for job in jobs.values()
        if str(job["state"] or "").upper() in _TERMINAL_SLURM_STATES
        and str(job["state"] or "").upper() != "COMPLETED"
    ]
    active = [
        job
        for job in jobs.values()
        if job["state"] is not None
        and str(job["state"]).upper() not in _TERMINAL_SLURM_STATES
    ]
    unknown = [job for job in jobs.values() if job["state"] is None]

    def savings(job: dict[str, object]) -> float | None:
        now = job["estimated_emissions_now_g"]
        optimal = job["estimated_emissions_optimal_g"]
        if now is None or optimal is None:
            return None
        return float(now) - float(optimal)

    estimated_jobs = [job for job in jobs.values() if savings(job) is not None]
    completed_estimated_jobs = [job for job in completed if savings(job) is not None]

    def total_savings(items: list[dict[str, object]]) -> float:
        return sum(savings(job) or 0.0 for job in items)

    by_location: dict[str, dict[str, float | int]] = {}
    by_workload: dict[str, dict[str, float | int]] = {}
    for job in completed:
        saved = savings(job)
        for grouping, key in (
            (by_location, str(job["location"])),
            (by_workload, str(job["workload_key"])),
        ):
            totals = grouping.setdefault(
                key, {"completed_jobs": 0, "estimated_co2_saved_g": 0.0}
            )
            totals["completed_jobs"] += 1
            if saved is not None:
                totals["estimated_co2_saved_g"] += saved

    return {
        "schedule_checks": len(records),
        "tracked_jobs": len(jobs),
        "completed_jobs": len(completed),
        "failed_jobs": len(failed),
        "active_jobs": len(active),
        "unknown_state_jobs": len(unknown),
        "dynamic_jobs": sum(bool(job["dynamic"]) for job in jobs.values()),
        "completed_runtime_hours": sum(
            int(job["duration_minutes"] or 0) for job in completed
        )
        / 60,
        "jobs_with_emissions_estimate": len(estimated_jobs),
        "completed_jobs_with_emissions_estimate": len(completed_estimated_jobs),
        "estimated_co2_saved_g_all_tracked_jobs": total_savings(estimated_jobs),
        "estimated_co2_saved_g_completed_jobs": total_savings(completed_estimated_jobs),
        "completed_jobs_by_location": by_location,
        "completed_jobs_by_workload": by_workload,
    }


def get_dynamic_schedule_checks(db_path: str | Path) -> list[dict[str, object]]:
    path = Path(db_path)
    if not path.is_file():
        return []

    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        with connection:
            table_exists = connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'schedule_checks'
                """
            ).fetchone()
            if table_exists is None:
                return []

            _ensure_history_columns(connection)
            placeholders = ", ".join("?" for _ in _TERMINAL_SLURM_STATES)
            rows = connection.execute(
                """
                SELECT checks.*
                FROM schedule_checks AS checks
                JOIN (
                    SELECT active_job_id, MAX(id) AS latest_id
                    FROM schedule_checks
                    WHERE dynamic = 1 AND active_job_id IS NOT NULL
                    GROUP BY active_job_id
                ) AS latest ON checks.id = latest.latest_id
                WHERE checks.slurm_state IS NULL
                   OR UPPER(checks.slurm_state) NOT IN (%s)
                ORDER BY checks.id
                """ % placeholders,
                _TERMINAL_SLURM_STATES,
=======
                """
                % placeholders,
                _TERMINAL_JOB_STATES,
>>>>>>> a17a830f1a070c5390a7e28631c2ee88089ecac5
            )
            records = []
            for row in rows:
                record = dict(row)
                record["dynamic"] = bool(record["dynamic"])
                records.append(record)
            return records


def get_jobs_requiring_state_refresh(db_path: str | Path) -> list[str]:
    path = Path(db_path)
    if not path.is_file():
        return []

    placeholders = ", ".join("?" for _ in _TERMINAL_SLURM_STATES)
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            rows = connection.execute(
                f"""
                SELECT DISTINCT active_job_id
                FROM schedule_checks
                WHERE active_job_id IS NOT NULL
                  AND (slurm_state IS NULL OR UPPER(slurm_state) NOT IN ({placeholders}))
                ORDER BY active_job_id
                """,
                _TERMINAL_SLURM_STATES,
            )
            return [row[0] for row in rows]


def update_schedule_job_state(db_path: str | Path, job_id: str, state: str) -> None:
    path = Path(db_path)
    if not path.is_file():
        return

    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute(
                "UPDATE schedule_checks SET slurm_state = ? WHERE active_job_id = ?",
                (state, job_id),
            )


def _ensure_history_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(schedule_checks)")
    }
    if "dynamic" not in columns:
        connection.execute("""
            ALTER TABLE schedule_checks
            ADD COLUMN dynamic INTEGER NOT NULL DEFAULT 0
                CHECK (dynamic IN (0, 1))
        """)
    if "api" not in columns:
        connection.execute("""
            ALTER TABLE schedule_checks
            ADD COLUMN api TEXT NOT NULL DEFAULT 'carbonintensity.org.uk'
        """)
    if "max_window_minutes" not in columns:
        connection.execute("""
            ALTER TABLE schedule_checks
            ADD COLUMN max_window_minutes INTEGER NOT NULL DEFAULT 2820
                CHECK (max_window_minutes > 0)
<<<<<<< HEAD
        """)
