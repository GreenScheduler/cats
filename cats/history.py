from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

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
                    previous_job_id TEXT,
                    active_job_id TEXT,
                    slurm_state TEXT,
                    error TEXT
                )
            """)
            _ensure_dynamic_column(connection)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS schedule_checks_workload_time
                ON schedule_checks (workload_key, checked_at_utc)
            """)

            cursor = connection.execute("""
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
                    previous_job_id,
                    active_job_id,
                    slurm_state,
                    error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

            _ensure_dynamic_column(connection)
            records = []
            for row in connection.execute("SELECT * FROM schedule_checks ORDER BY id"):
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


def update_schedule_job_state(
    db_path: str | Path, job_id: str, state: str
) -> None:
    path = Path(db_path)
    if not path.is_file():
        return

    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute(
                "UPDATE schedule_checks SET slurm_state = ? WHERE active_job_id = ?",
                (state, job_id),
            )


def _ensure_dynamic_column(connection: sqlite3.Connection) -> None:
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(schedule_checks)")
    }
    if "dynamic" not in columns:
        connection.execute("""
            ALTER TABLE schedule_checks
            ADD COLUMN dynamic INTEGER NOT NULL DEFAULT 0
                CHECK (dynamic IN (0, 1))
        """)