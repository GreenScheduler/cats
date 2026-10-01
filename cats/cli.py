# pyright: reportUninitializedInstanceVariable=none, reportUnknownArgumentType=none, reportUnusedCallResult=none, reportUnknownMemberType=none
import datetime
import os
import sys
from argparse import Action, ArgumentParser, RawDescriptionHelpFormatter
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any, Optional, cast

import requests

from .carbonFootprint import Estimates, get_footprint_reduction_estimate
from .configure import Args, get_runtime_config
from .constants import CATS_ASCII_BANNER_COLOUR, CATS_ASCII_BANNER_NO_COLOUR
from .exceptions import (
    DurationExceedsWindowError,
    InvalidLocationError,
    InvalidMetricError,
    MissingArgumentError,
    PriceConstraintUnsatisfiableError,
    ProviderAuthenticationError,
    SchedulerError,
    UnsupportedProviderError,
)
from .forecast import WindowedForecast
from .output import CATSOutput
from .plotting import plotplan
from .pricing import (
    find_best_within_price_constraint,
    price_at_window,
    price_covers_window,
    resolve_price_series,
)
from .providers import CompositeProvider, get_provider, list_providers
from .schedulers import SCHEDULER_DATE_FORMAT, schedule_at, schedule_sbatch
from .version import version


def is_headless() -> bool:
    return (
        sys.platform.startswith("linux")
        and "DISPLAY" not in os.environ
        and "WAYLAND_DISPLAY" not in os.environ
    )


def indent_lines(lines, spaces):
    return "\n".join(" " * spaces + line for line in lines.split("\n"))


def print_providers():
    "Print the registered data providers and their properties"
    for name, provider_cls in sorted(list_providers().items()):
        instance = provider_cls()
        docstring = (provider_cls.__doc__ or "").strip().splitlines()
        summary = docstring[0].strip() if docstring else ""
        print(f"{name}")
        print(f"    {summary}")
        print(
            "    max duration: "
            f"{instance.get_max_duration_minutes()} min, "
            "resolution: "
            f"{instance.get_temporal_resolution_minutes()} min"
        )
        if instance.SUPPORTED_METRICS:
            metrics = ", ".join(
                f"{m} (default)" if m == instance.DEFAULT_METRIC else m
                for m in sorted(instance.SUPPORTED_METRICS)
            )
            print(f"    metrics: {metrics}")


def print_locations(api: str | None = None, metric: str | None = None):
    "Print the valid --location codes of one provider, or of all of them"
    providers = list_providers()
    if api:
        providers = {api: get_provider(api)}
    for name, provider_cls in sorted(providers.items()):
        instance = provider_cls()
        groups = instance.list_locations(metric)
        print(name)
        if not groups:
            print("    (no location list available)")
        for group in groups:
            print(f"  {group.heading}")
            if group.note:
                print(f"    {group.note}")
            if group.locations:
                print(indent_lines(format_locations(group.locations), 4))
        print()


def format_locations(locations: dict[str, str]) -> str:
    "Format codes in aligned columns, or one per line if they have names"
    if not locations:
        return ""
    if any(locations.values()):
        width = max(len(code) for code in locations)
        return "\n".join(
            f"{code:<{width}}  {name}".rstrip() for code, name in locations.items()
        )
    width = max(len(code) for code in locations) + 2
    columns = max(1, 76 // width)
    codes = list(locations)
    return "\n".join(
        "".join(code.ljust(width) for code in codes[i : i + columns]).rstrip()
        for i in range(0, len(codes), columns)
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

    def parse_signal_weight(string: str) -> tuple[str, float]:
        name, sep, weight_str = string.partition("=")
        if not sep:
            raise ValueError(f"--signal must be in NAME=WEIGHT format, got {string!r}")
        try:
            weight = float(weight_str)
        except ValueError:
            raise ValueError(
                f"--signal weight must be a number, got {weight_str!r} in {string!r}"
            )
        return name, weight

    ### Required

    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        help="[required, unless --list-providers or --list-locations is given] "
        "Expected duration "
        "of the job in minutes.",
    )

    ### Optional

    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List the registered data providers and their properties, then exit "
        "(no --duration needed).",
    )
    parser.add_argument(
        "--list-locations",
        nargs="?",
        const="",
        default=None,
        metavar="API",
        help="List the valid --location codes, then exit (no --duration needed). "
        "Location codes differ between providers. Use -a / --api (or give an API "
        "name here) to list only that provider's, otherwise all are listed. Combine with --metric to restrict to one metric, since "
        "some providers use different codes per metric.",
    )
    parser.add_argument(
        "--metric",
        type=str,
        help="Which metric to request from the chosen provider, for providers that "
        "serve more than one. Run --list-providers to see each provider's "
        "supported metrics and its default. Ignored by providers that only serve "
        "a single metric.",
    )
    parser.add_argument(
        "--signal",
        type=parse_signal_weight,
        action="append",
        metavar="NAME=WEIGHT",
        help="Repeatable. Selects which signals to combine, and their relative "
        "weight, when using the 'composite' provider. Valid signal names: "
        "carbon, price, renewables, water, water_stress, "
        "environmental_score. Weights don't need to sum to 1 (normalised "
        "automatically). Example: "
        "--signal carbon=0.4 --signal price=0.3 --signal renewables=0.3. "
        "With no --signal given, every no-extra-authentication signal available "
        "for that location is combined with equal weight. Ignored by all other "
        "providers.",
    )
    price_constraint_group = parser.add_mutually_exclusive_group()
    price_constraint_group.add_argument(
        "--max-price",
        type=float,
        help="Restrict the job start time search to windows whose average day-ahead "
        "price does not exceed this absolute cap (GBP/MWh for a GB postcode, "
        "EUR/MWh for a wattnet.eu zone). Works with any --api/--metric, not just "
        "'composite': price is fetched separately for the location regardless of "
        "which metric is being optimised. The search is also implicitly capped to "
        "whatever forecast horizon price data currently covers, which is often "
        "shorter than the chosen metric's own horizon. Raises an error if no "
        "candidate start time satisfies the cap. Mutually exclusive with "
        "--max-price-increase-pct.",
    )
    price_constraint_group.add_argument(
        "--max-price-increase-pct",
        type=float,
        help="Restrict the job start time search to windows whose average day-ahead "
        "price is not more than this many percent above the price if the job "
        "started right now. Same location/horizon behaviour as --max-price; "
        "mutually exclusive with it.",
    )

    parser.add_argument(
        "-s",
        "--scheduler",
        type=str,
        help="Pass command using `-c` to scheduler.",
        choices=["at", "sbatch"],
    )

    class StoreApi(Action):
        "Store --api and remember it was given, as it has a default value"

        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values)
            namespace.api_given = True

    parser.set_defaults(api_given=False)
    parser.add_argument(
        "-a",
        "--api",
        action=StoreApi,
        type=str,
        default="carbonintensity.org.uk",
        help="API to use to obtain forecasts. Overrides `config.yml`. "
        "Run --list-providers to see the available APIs, their metrics and "
        "location formats. Default: `carbonintensity.org.uk`.",
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
    args = cast(Args, parser.parse_args(arguments))
    colour_output = args.no_colour or args.no_color

    if args.list_providers:
        print_providers()
        return

    if args.list_locations is not None:
        api = args.list_locations or (args.api if args.api_given else None)
        print_locations(api, args.metric)
        return

    if args.duration is None:
        raise MissingArgumentError(
            "-d / --duration is required, unless --list-providers or "
            "--list-locations is given"
        )

    if args.command and not args.scheduler:
        raise MissingArgumentError(
            "To run a command or sbatch script with -c / --comand, you must specify scheduler with -s / --scheduler"
        )

    provider_cls, location, duration, jobinfo, PUE = get_runtime_config(args)
    provider_kwargs: dict[str, Any] = {}
    if provider_cls is CompositeProvider and args.signal:
        provider_kwargs["api_data"] = {"signals": dict(args.signal)}
    provider = provider_cls(**provider_kwargs)

    # Validate and parse window constraints
    try:
        start_constraint, end_constraint, max_window = validate_window_constraints(
            args.start_window, args.end_window, args.window
        )
    except ValueError as e:
        raise ValueError(f"Error in window constraints: {e}")
    # Check against both API limit and user-specified window
    max_duration_minutes = provider.get_max_duration_minutes(metric=args.metric)
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
    now_utc = datetime.datetime.now(timezone.utc)
    forecast = provider.get_data(now_utc, location, metric=args.metric)

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
    now_avg = wf[0]

    #####################################################
    ## Price: constraint (if requested) and reporting  ##
    #####################################################

    # Reused for both the constrained search below and the always-on price
    # report: price is fetched for the location independently of whichever
    # metric/provider is actually being optimised (see cats/pricing.py). A
    # location composite doesn't recognise (neither a GB postcode nor a
    # wattnet.eu zone code, e.g. energy-charts.info's own native zone codes
    # used directly rather than through composite) is treated the same as
    # "no price signal available" for the best-effort report, but as a hard
    # error when a price constraint was explicitly requested.
    price_constraint_requested = (
        args.max_price is not None or args.max_price_increase_pct is not None
    )
    try:
        price_series = resolve_price_series(
            location, now_utc, provider_cls=provider_cls
        )
    except InvalidLocationError:
        if price_constraint_requested:
            raise
        price_series = None

    if price_constraint_requested:
        if price_series is None:
            raise InvalidLocationError(
                f"{location}. No day-ahead price data available for this location; "
                "cannot use --max-price/--max-price-increase-pct here."
            )
        best_avg = find_best_within_price_constraint(
            wf,
            price_series.values,
            duration,
            args.max_price,
            args.max_price_increase_pct,
        )
    else:
        best_avg = min(wf)

    output = CATSOutput(
        forecast.metric,
        now_avg,
        best_avg,
        location,
        "GBR",
        unit=forecast.unit,
        colour=not colour_output,
    )

    if (
        price_series is not None
        and price_covers_window(price_series.values, now_avg.start, now_avg.end)
        and price_covers_window(price_series.values, best_avg.start, best_avg.end)
    ):
        price_now = price_at_window(price_series.values, now_avg.start, duration)
        price_best = price_at_window(price_series.values, best_avg.start, duration)
        output.priceEstimate = Estimates(price_now, price_best, price_now - price_best)
        output.priceUnit = price_series.unit

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
        if args.scheduler == "at":
            err = schedule_at(output, args.command.split())
        elif args.scheduler == "sbatch":
            err = schedule_sbatch(output, args.command.split())
        else:  # pragma: no cover - we already check for valid scheduler in parse_arguments
            err = f"Scheduler {args.scheduler} not in supported schedulers: {SCHEDULER_DATE_FORMAT.keys()}"
        if err:
            raise SchedulerError(err)


def main(arguments: list[str] | None = None):
    try:
        run_cats(arguments)
        return 0
    except InvalidLocationError as e:
        print(f"Invalid location: {e}")
    except InvalidMetricError as e:
        print(f"Invalid metric: {e}")
    except UnsupportedProviderError as e:
        print(f"Unsupported provider: {e}")
    except ProviderAuthenticationError as e:
        print(f"Failed to authenticate with data provider: {e}")
    except MissingArgumentError as e:
        print(f"One or more arguments missing: {e}")
    except DurationExceedsWindowError as e:
        print(f"Duration exceeds limit: {e}")
    except PriceConstraintUnsatisfiableError as e:
        print(f"Price constraint not satisfiable: {e}")
    except SchedulerError as e:
        print(f"Scheduler error: {e}")
    except requests.exceptions.JSONDecodeError as e:
        print(f"Failed to decode JSON from data provider: {e}")
    except requests.exceptions.HTTPError as e:
        print(f"Failed to connect to HTTP server from data provider: {e}")
    except ValueError as e:
        print(f"Value error: {e}")
    except Exception:
        # If exception is not expected, raise
        raise
    return 1
