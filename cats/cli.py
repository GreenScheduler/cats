import cats
from cats.configure import *
from cats.constants import CATS_ASCII_BANNER_COLOUR, CATS_ASCII_BANNER_NO_COLOUR
from cats.carbonFootprint import get_footprint_reduction_estimate
from cats.CI_api_interface import InvalidLocationError
from cats.CI_api_query import get_CI_forecast  # noqa: F401
from cats.plotting import plotplan
from cats.forecast import WindowedForecast


import datetime
import logging
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import timedelta
from pathlib import Path


def indent_lines(lines, spaces):
    return "\n".join(" " * spaces + line for line in lines.split("\n"))


def print_banner(disable_colour):
    """Print an ASCII art banner with the CATS title, optionally in colour."""
    if disable_colour:
        print(CATS_ASCII_BANNER_NO_COLOUR)
    else:
        print(CATS_ASCII_BANNER_COLOUR)


def parse_arguments():
    """
    Parse command line arguments
    :return: [dict] parsed arguments
    """
    description_text = f"""
    Climate-Aware Task Scheduler (version {cats.__version__})

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
    ********

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

    def positive_integer(string):
        n = int(string)
        assert n >= 0
        return n

    ### Required

    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        required=True,
        help="[required] Expected duration of the job in minutes.",
    )

    ### Optional

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
        help="API to use to obtain carbon intensity forecasts. Overrides `config.yml`. "
        "For now, only choice is `carbonintensity.org.uk` (hence UK only forecasts). "
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
        help="Location of the computing facility. For the UK, first half of a postcode (e.g. `M15`), "
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

    return parser


def main(arguments=None) -> int:
    parser = parse_arguments()
    args = parser.parse_args(arguments)
    colour_output = args.no_colour or args.no_color

    # Print CATS ASCII art banner, before any output from printing or logging
    print_banner(colour_output)

    if args.command and not args.scheduler:
        print(
            "cats: To run a command or sbatch script with the -c or --command option, you must\n"
            "      specify the scheduler with the -s or --scheduler option"
        )
        return 1

    CI_API_interface, location, duration, jobinfo, PUE = get_runtime_config(args)
    if duration > CI_API_interface.max_duration:
        print(
            f"""API allows a maximum job duration of {CI_API_interface.max_duration} minutes.
This is usually due to forecast limitations."""
        )
        return 1

    ########################
    ## Obtain CI forecast ##
    ########################

    try:
        CI_forecast = get_CI_forecast(location, CI_API_interface)
    except InvalidLocationError:
        logging.error(f"Error: unknown location {location}\n")
        logging.error(
            "Location should be be specified as the outward code,\n"
            "for example 'SW7' for postcode 'SW7 EAZ'.\n"
        )
        return 1

    #############################
    ## Find optimal start time ##
    #############################

    # Find best possible average carbon intensity, along
    # with corresponding job start time.
    wf = WindowedForecast(
        CI_forecast, duration, start=datetime.datetime.now().astimezone()
    )
    now_avg, best_avg = wf[0], min(wf)
    output = cats.CATSOutput(now_avg, best_avg, location, "GBR", colour=not colour_output)

    ################################
    ## Calculate carbon footprint ##
    ################################

    if args.footprint:
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
            dateformat = cats.SCHEDULER_DATE_FORMAT.get(args.dateformat, "")
        else:
            dateformat = args.dateformat or ""
        print(output.to_json(dateformat, sort_keys=True, indent=2))
    else:
        print(output)
    if args.plot:
        plotplan(CI_forecast, output)
    if args.command:
        if args.scheduler == "at":
            err = cats.schedule_at(output, args.command.split())
        elif args.scheduler == "sbatch":
            err = cats.schedule_sbatch(output, args.command.split())
        else:  # pragma: no cover - we already check for valid scheduler in parse_arguments
            err = f"Scheduler {args.scheduler} not in supported schedulers: {cats.SCHEDULER_DATE_FORMAT.keys()}"
        if err:
            print(err)
            return 1
    return 0
