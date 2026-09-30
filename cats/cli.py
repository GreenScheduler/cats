# pyright: reportUninitializedInstanceVariable=none, reportUnknownArgumentType=none, reportUnusedCallResult=none, reportUnknownMemberType=none
import datetime
import json
import logging
import os
import shlex
import sqlite3
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import timedelta, timezone
from pathlib import Path
from typing import Optional, cast

from .carbonFootprint import get_footprint_reduction_estimate
from .configure import Args, get_runtime_config
from .constants import CATS_ASCII_BANNER_COLOUR, CATS_ASCII_BANNER_NO_COLOUR
from .exceptions import (
    DurationExceedsWindowError,
    InvalidLocationError,
    MissingArgumentError,
    ProviderAuthenticationError,
    SchedulerError,
    UnsupportedProviderError,
)
from .forecast import WindowedForecast
from .history import (
    get_jobs_requiring_state_refresh,
    read_schedule_checks,
    record_schedule_check,
    summarize_schedule_checks,
    update_schedule_job_state,
)
from .output import CATSOutput
from .plotting import plotplan
from .schedulers import (
    SCHEDULER_DATE_FORMAT,
    get_sbatch_job_state,
    schedule_at,
    schedule_sbatch,
)
from .version import version


def is_headless() -> bool:
    return (
        sys.platform.startswith("linux")
        and "DISPLAY" not in os.environ
        and "WAYLAND_DISPLAY" not in os.environ
    )


def indent_lines(lines, spaces):
    return "\n".join(" " * spaces + line for line in lines.split("\n"))


def _workload_key(command: str) -> str:
    parts = shlex.split(command)
    for index, part in enumerate(parts):
        if part.startswith("--job-name="):
            return part.split("=", 1)[1]
        if part in ("--job-name", "-J") and index + 1 < len(parts):
            return parts[index + 1]
        if part.startswith("-J") and len(part) > 2:
            return part[2:]

    if not parts:
        return "unknown"
    candidate = parts[0] if not parts[0].startswith("-") else parts[-1]
    return Path(candidate).name or "unknown"


def _refresh_history_job_states(history_db: str) -> None:
    try:
        job_ids = get_jobs_requiring_state_refresh(history_db)
    except (OSError, sqlite3.Error) as error:
        logging.warning("Could not read tracked Slurm jobs from CATS history: %s", error)
        return

    for job_id in job_ids:
        state = get_sbatch_job_state(job_id)
        if state is None:
            continue
        try:
            update_schedule_job_state(history_db, job_id, state)
        except (OSError, sqlite3.Error) as error:
            logging.warning(
                "Could not update Slurm state for job %s in CATS history: %s",
                job_id,
                error,
            )


def print_banner(disable_colour):
    """Print an ASCII art banner with the CATS title, optionally in colour."""
    if disable_colour:
        print(CATS_ASCII_BANNER_NO_COLOUR)
    else:
        print(CATS_ASCII_BANNER_COLOUR)


def parse_time_constraint(
    time_str: str, timezone_info=None
) -> Optional[datetime.datetime]:
    """
    Parse a time constraint string into a datetime object.

    :param time_str: Time string in various formats (HH:MM, YYYY-MM-DDTHH:MM, etc.)
    :param timezone_info: Default timezone if not specified in the string
    :return: Parsed datetime object
    :raises ValueError: If the time string cannot be parsed
    """
    if not time_str:
        return None

    # If timezone_info is not provided, use system local timezone
    if timezone_info is None:
        timezone_info = datetime.datetime.now().astimezone().tzinfo

    # Try to parse as full ISO format first
    try:
        if "T" in time_str:
            # Full datetime string
            if time_str.endswith("Z"):
                time_str = time_str[:-1] + "+00:00"
            elif time_str[-6] not in ["+", "-"] and time_str[-3] != ":":
                # No timezone info, add default
                dt = datetime.datetime.fromisoformat(time_str)
                return dt.replace(tzinfo=timezone_info)
            return datetime.datetime.fromisoformat(time_str)
        else:
            # Time only (HH:MM or HH:MM:SS)
            time_part = datetime.time.fromisoformat(time_str)
            today = datetime.datetime.now().date()
            return datetime.datetime.combine(today, time_part, tzinfo=timezone_info)
    except ValueError as e:
        raise ValueError(f"Unable to parse time constraint '{time_str}': {e}")


def validate_window_constraints(
    start_window: Optional[datetime.datetime],
    end_window: Optional[datetime.datetime],
    window_minutes: int,
) -> tuple[Optional[datetime.datetime], Optional[datetime.datetime], int]:
    """
    Validate window constraints.

    :param start_window: Start window constraint datetime
    :param end_window: End window constraint datetime
    :param window_minutes: Maximum window duration in minutes
    :return: Tuple of (start_datetime, end_datetime, validated_window_minutes)
    :raises ValueError: If constraints are invalid
    """
    if window_minutes < 1 or window_minutes > 2820:
        raise ValueError("Window must be between 1 and 2820 minutes (47 hours)")

    if start_window and end_window:
        if start_window >= end_window:
            raise ValueError("Start window must be before end window")

    return start_window, end_window, window_minutes


def parse_arguments():
    """
    Parse command line arguments
    :return: [dict] parsed arguments
    """
    description_text = f"""
    Climate-Aware Task Scheduler (version {version})

    The Climate-Aware Task Scheduler (cats) command line program helps you run
    your calculations in a way that minimises their impact on the climate by
    delaying computation until a time when the ammount of CO2 produced to
    generate the power you will use is predicted to be minimised.

    By default, the command simply returns information about when the
    calculation should be undertaken and compares the carbon intensity
    (gCO2/kWh) of running the calculation now with the carbon intensity at that
    time in the future. To undertake this calculation, cats needs to know the
    predicted duration of the calculation (which you must supply, see `-d`) and
    your location, either inferred from your IP address, or passed using `-l`.
    If additional information about the power consumption of your computer is
    available and passed to CATS via the `--config` option, the predicted CO2
    usage will be reported.

    To make use of this information, you will need to couple cats with a task
    scheduler of some kind. The command to schedule is specified with the `-c`
    or `--command` parameter, and the scheduler can be selected using the
    `--scheduler` option.

    Example:
       cats -d 1 --loc RG1 --scheduler=at --command='ls'
    """

    config_text = indent_lines(
        Path(__file__).with_name("config.yml").read_text(), spaces=8
    )
    example_text = f"""
    Examples

    CATS can be used to report information on the best time to run a calculation
    and the amount of CO2. Information about a 90 minute calculation in central
    Oxford can be found by running:

        cats -d 90 --loc OX1

    The `at` scheduler is available from the command line on most Linux and
    MacOS computers, and can be the easest way to use cats to minimise the
    carbon intensity of calculations on smaller computers. For example, the
    above calculation can be scheduled by running:

        cats -d 90 --loc OX1 -s at -c 'mycommand'

    To report carbon footprint, pass the `--config` option to select a
    configuration file and the `--profile` option to select a profile.
    The configuration file is documented in the Quickstart section of the online
    documentation. An example config file is given below:

.. code-block:: yaml

{config_text}
    """

    parser = ArgumentParser(
        prog="cats",
        description=description_text,
        epilog=example_text,
        formatter_class=RawDescriptionHelpFormatter,
    )

    def positive_integer(string: str):
        n = int(string)
        assert n >= 0
        return n

    ### Required

    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        help="[required unless --show-data] Expected duration of the job in minutes.",
    )

    ### Optional

    parser.add_argument(
        "--show-data",
        action="store_true",
        help="Display all saved CATS scheduling history as JSON (requires CATS_HISTORY_DB).",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Summarize tracked jobs and estimated CO2 savings (requires CATS_HISTORY_DB).",
    )
    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="Re-evaluate a pending sbatch job over time (requires --scheduler sbatch and CATS_HISTORY_DB).",
    )

    parser.add_argument(
        "-s",
        "--scheduler",
        type=str,
        help="Pass command using `-c` to scheduler.",
        choices=["at", "sbatch"],
    )
    parser.add_argument(
        "-a",
        "--api",
        type=str,
        default="carbonintensity.org.uk",
        help="API to use to obtain carbon intensity forecasts. Overrides `config.yml`. "
        "There is a choice of `carbonintensity.org.uk` (only forecasts in Great Britain)"
        "or `wattnet.eu` (experimental, for forecasts across Europe). "
        "Default: `carbonintensity.org.uk`.",
    )
    parser.add_argument(
        "-c", "--command", help="Command to schedule, requires --scheduler to be set"
    )
    parser.add_argument(
        "--dateformat",
        help="Output date format in strftime(3) format or one of the supported schedulers ('at').",
    )
    parser.add_argument(
        "-l",
        "--location",
        type=str,
        help="Location of the computing facility with a format that depends on the API used."
        "For `carbonintensity.org.uk` the first half of a postcode (e.g. `M15`) is used, "
        "for other APIs, see documentation for exact format. Overrides `config.yml`. "
        "Default: if absent, location based in IP address is used.",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to a configuration file. The file is required to obtain carbon footprint estimates. "
        "Default: `config.yml` in current directory."
        "Template found at https://github.com/GreenScheduler/cats/blob/main/config.yml.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        help="Hardware profile, specified in configuration file",
    )
    parser.add_argument(
        "--format",
        type=str,
        help="Format to output optimal start time and carbon emmission"
        "estimate savings in. Currently only JSON is supported.",
        choices=["json"],
    )
    parser.add_argument(
        "-f",
        "--footprint",
        action="store_true",
    )
    parser.add_argument(
        "--cpu",
        type=positive_integer,
        help="Number of CPUs used by the job",
    )
    parser.add_argument(
        "--gpu",
        type=positive_integer,
        help="Number of GPUs used by the job",
    )
    parser.add_argument(
        "--memory",
        type=positive_integer,
        help="Amount of memory used by the job, in GB",
    )
    parser.add_argument(
        "-n",
        "--no-colour",
        action="store_true",
        help="Disable all terminal output colouring",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable all terminal output colouring (alias to --no-colour)",
    )
    parser.add_argument(
        "--plot",
        help="Create a plot of the forecast and optimised plan for the job. "
        "This needs matplotlib to be installed, e.g. install with "
        "\"pip install 'climate-aware-task-scheduler[plots]'\"",
        action="store_true",
    )
    parser.add_argument("--save-plot", help="Saves plot to filename")
    parser.add_argument(
        "--window",
        type=positive_integer,
        help="Maximum time window to search for optimal start time, in minutes. "
        "Must be between 1 and 2820 (47 hours). Default: 2820 minutes (47 hours).",
        default=2820,
    )
    parser.add_argument(
        "--start-window",
        type=parse_time_constraint,
        help="Earliest time the job is allowed to start, in ISO format (e.g., '2024-01-15T09:00'). "
        "If only time is provided (e.g., '09:00'), today's date is assumed. "
        "Timezone info is optional and defaults to system timezone.",
    )
    parser.add_argument(
        "--end-window",
        type=parse_time_constraint,
        help="Latest time the job is allowed to start, in ISO format (e.g., '2024-01-15T17:00'). "
        "If only time is provided (e.g., '17:00'), today's date is assumed. "
        "Timezone info is optional and defaults to system timezone.",
    )

    return parser


def run_cats(arguments: list[str] | None = None):
    "Main CLI runner, raises exceptions"
    parser = parse_arguments()
    parsed_args = parser.parse_args(arguments)
    if parsed_args.show_data or parsed_args.report:
        if parsed_args.show_data and parsed_args.report:
            parser.error("--show-data and --report cannot be used together")
        history_db = os.environ.get("CATS_HISTORY_DB")
        if not history_db:
            parser.error("CATS_HISTORY_DB is not set; history database path is unknown")
        try:
            _refresh_history_job_states(history_db)
            records = read_schedule_checks(history_db)
        except (OSError, sqlite3.Error) as error:
            parser.error(f"Could not read CATS history database: {error}")
        if parsed_args.report:
            report = summarize_schedule_checks(records)
            if parsed_args.format == "json":
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print("CATS scheduling report")
                print(f"60{report['schedule_checks']}")
                print(f"Tracked jobs: {report['tracked_jobs']}")
                print(
                    "Job states: "
                    f"{report['completed_jobs']} completed, "
                    f"{report['active_jobs']} active, "
                    f"{report['failed_jobs']} failed, "
                    f"{report['unknown_state_jobs']} unknown"
                )
                print(f"Dynamic jobs: {report['dynamic_jobs']}")
                print(
                    "Scheduled runtime of completed jobs: "
                    f"{report['completed_runtime_hours']:.2f} hours"
                )
                completed_savings = report[
                    "estimated_co2_saved_g_completed_jobs"
                ]
                print(
                    "Estimated CO2 savings for completed jobs: "
                    f"{completed_savings:.2f} g "
                    f"({completed_savings / 1000:.3f} kg; "
                    f"{report['completed_jobs_with_emissions_estimate']} of "
                    f"{report['completed_jobs']} jobs have footprint estimates)"
                )
                print(
                    "Estimated CO2 savings for all tracked jobs: "
                    f"{report['estimated_co2_saved_g_all_tracked_jobs']:.2f} g "
                    f"({report['jobs_with_emissions_estimate']} jobs with estimates)"
                )
                if report["completed_jobs_by_location"]:
                    print("Completed jobs by location:")
                    for location, totals in sorted(
                        report["completed_jobs_by_location"].items()
                    ):
                        print(
                            f"  {location}: {totals['completed_jobs']} jobs, "
                            f"{totals['estimated_co2_saved_g']:.2f} g estimated CO2 saved"
                        )
        elif records:
            print(json.dumps(records, indent=2))
        else:
            print("No CATS history records found.")
        return

    if parsed_args.duration is None:
        parser.error("the following arguments are required: -d/--duration")

    args = cast(Args, parsed_args)
    colour_output = args.no_colour or args.no_color

    if args.command and not args.scheduler:
        raise MissingArgumentError(
            "To run a command or sbatch script with -c / --comand, you must specify scheduler with -s / --scheduler"
        )
    if args.dynamic and (not args.command or args.scheduler != "sbatch"):
        raise MissingArgumentError(
            "--dynamic requires --scheduler sbatch and a command passed with --command"
        )
    if args.dynamic and not os.environ.get("CATS_HISTORY_DB"):
        raise MissingArgumentError(
            "--dynamic requires CATS_HISTORY_DB to be configured for job tracking"
        )

    provider_cls, location, duration, jobinfo, PUE = get_runtime_config(args)
    provider = provider_cls()

    # Validate and parse window constraints
    try:
        start_constraint, end_constraint, max_window = validate_window_constraints(
            args.start_window, args.end_window, args.window
        )
    except ValueError as e:
        raise ValueError(f"Error in window constraints: {e}")
    # Check against both API limit and user-specified window
    max_duration_minutes = provider.get_max_duration_minutes()
    effective_max_duration = min(max_duration_minutes, max_window)
    if duration > effective_max_duration:
        if max_window < max_duration_minutes:
            raise DurationExceedsWindowError(f"{duration=}, {max_window=}")
        else:
            raise DurationExceedsWindowError(
                f"{duration=}, maximum forecast duration is {max_duration_minutes}"
            )

    ########################
    ## Obtain CI forecast ##
    ########################
    forecast = provider.get_data(datetime.datetime.now(timezone.utc), location)

    #############################
    ## Find optimal start time ##
    #############################

    # Find best possible average carbon intensity, along
    # with corresponding job start time.
    search_start = datetime.datetime.now().astimezone()

    # Apply start window constraint if provided
    if start_constraint:
        # Ensure start constraint is in the same timezone as search_start
        if start_constraint.tzinfo != search_start.tzinfo:
            start_constraint = start_constraint.astimezone(search_start.tzinfo)
        search_start = max(search_start, start_constraint)

    wf = WindowedForecast(
        forecast.values,
        duration,
        start=search_start,
        max_window_minutes=max_window,
        end_constraint=end_constraint,
    )
    now_avg, best_avg = wf[0], min(wf)
    output = CATSOutput(
        forecast.metric,
        now_avg,
        best_avg,
        location,
        "GBR",
        unit=forecast.unit,
        colour=not colour_output,
    )

    ################################
    ## Calculate carbon footprint ##
    ################################

    if args.footprint and forecast.metric == "Carbon intensity":
        assert PUE is not None, "PUE not set by get_runtime_config!"
        assert jobinfo is not None, "jobinfo not set by get_runtime_config!"
        output.emmissionEstimate = get_footprint_reduction_estimate(
            PUE=PUE,
            jobinfo=jobinfo,
            runtime=timedelta(minutes=args.duration),
            average_best_ci=best_avg.value,
            average_now_ci=now_avg.value,
        )

    if args.format == "json":
        if isinstance(args.dateformat, str) and "%" not in args.dateformat:
            dateformat = SCHEDULER_DATE_FORMAT.get(args.dateformat, "")
        else:
            dateformat = args.dateformat or ""
        print(output.to_json(dateformat, sort_keys=True, indent=2))
    else:
        # Print CATS ASCII art banner, before any output from printing or logging
        print_banner(colour_output)
        print(output)
    if args.plot or args.save_plot:
        default_filename = (
            "cats-"
            + datetime.datetime.now()
            .isoformat(timespec="seconds")
            .replace("-", "")
            .replace(":", "")
            + ".png"
        )
        filename = (
            default_filename
            if (is_headless() and args.save_plot is None)
            else args.save_plot
        )
        plotplan(forecast, output, filename)
        if filename:
            print("Saved plot to:", filename)
    if args.command:
        job_id = None
        history_db = os.environ.get("CATS_HISTORY_DB")
        if args.scheduler == "sbatch" and history_db:
            _refresh_history_job_states(history_db)

        if args.scheduler == "at":
            err = schedule_at(output, args.command.split())
        elif args.scheduler == "sbatch":
            job_id, err = schedule_sbatch(output, args.command.split())
        else:  # pragma: no cover - we already check for valid scheduler in parse_arguments
            err = f"Scheduler {args.scheduler} not in supported schedulers: {SCHEDULER_DATE_FORMAT.keys()}"
        if err:
            raise SchedulerError(err)

        if args.scheduler == "sbatch" and job_id and history_db:
            estimate = output.emmissionEstimate
            slurm_state = get_sbatch_job_state(job_id) or "PENDING"
            try:
                record_schedule_check(
                    history_db,
                    workload_key=_workload_key(args.command),
                    duration_minutes=duration,
                    location=location,
                    action="submitted",
                    dynamic=args.dynamic,
                    api=args.api,
                    max_window_minutes=max_window,
                    current_ci_g_per_kwh=now_avg.value,
                    optimal_start_utc=output.valueOptimal.start.astimezone(
                        timezone.utc
                    ).isoformat(),
                    optimal_ci_g_per_kwh=output.valueOptimal.value,
                    estimated_emissions_now_g=(estimate.now if estimate else None),
                    estimated_emissions_optimal_g=(estimate.best if estimate else None),
                    active_job_id=job_id,
                    slurm_state=slurm_state,
                )
            except (OSError, sqlite3.Error) as error:
                logging.warning(
                    "Slurm job %s was submitted, but its CATS history could not be saved: %s",
                    job_id,
                    error,
                )


def main(arguments: list[str] | None = None):
    try:
        run_cats(arguments)
        return 0
    except InvalidLocationError as e:
        print(f"Invalid location: {e}")
    except UnsupportedProviderError as e:
        print(f"Unsupported provider: {e}")
    except ProviderAuthenticationError as e:
        print(f"Failed to authenticate with data provider: {e}")
    except MissingArgumentError as e:
        print(f"One or more arguments missing: {e}")
    except DurationExceedsWindowError as e:
        print(f"Duration exceeds limit: {e}")
    except SchedulerError as e:
        print(f"Scheduler error: {e}")
    except ValueError as e:
        print(f"Value error: {e}")
    except Exception:
        # If exception is not expected, raise
        raise
    return 1
