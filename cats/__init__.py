import dataclasses
import json
import logging
import subprocess
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import timedelta
from pathlib import Path
from typing import Optional

from .carbonFootprint import Estimates, get_footprint_reduction_estimate
from .CI_api_interface import InvalidLocationError
from .CI_api_query import get_CI_forecast  # noqa: F401
from .configure import get_runtime_config
from .forecast import CarbonIntensityAverageEstimate
from .optimise_starttime import get_avg_estimates  # noqa: F401

__version__ = "1.0.0"

# To add a scheduler, add a date format here
# and create a scheduler_<new>(...) function
SCHEDULER_DATE_FORMAT = {"at": "%Y%m%d%H%M"}


def indent_lines(lines, spaces):
    return "\n".join(" " * spaces + line for line in lines.split("\n"))


def parse_arguments():
    """
    Parse command line arguments
    :return: [dict] parsed arguments
    """
    description_text = f"""
    Climate-Aware Task Scheduler (version {__version__})
    --------------------------------------------------------------------------
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
    and the amount of CO2. Information about a 90 minute calculation in centeral
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
    documentation. An
    example config file is given below:

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
        help="Pass command using `-c` to scheduler. Currently, the only supported scheduler is at",
        choices=["at"],
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
        help="Number of cpus used by the job",
    )
    parser.add_argument(
        "--gpu",
        type=positive_integer,
        help="Number of cpus used by the job",
    )
    parser.add_argument(
        "--memory",
        type=positive_integer,
        help="Amount of memory used by the job, in GB",
    )

    return parser


@dataclasses.dataclass
class CATSOutput:
    """Carbon Aware Task Scheduler output"""

    carbonIntensityNow: CarbonIntensityAverageEstimate
    carbonIntensityOptimal: CarbonIntensityAverageEstimate
    location: str
    countryISO3: str
    emmissionEstimate: Optional[Estimates] = None

    def __str__(self) -> str:
        out = f"""Best job start time {self.carbonIntensityOptimal.start}
Carbon intensity if job started now       = {self.carbonIntensityNow.value:.2f} gCO2eq/kWh
Carbon intensity at optimal time          = {self.carbonIntensityOptimal.value:.2f} gCO2eq/kWh"""

        if self.emmissionEstimate:
            out += f"""
Estimated emissions if job started now    = {self.emmissionEstimate.now}
Estimated emissions at optimal time       = {self.emmissionEstimate.best} (- {self.emmissionEstimate.savings})"""

        out += "\n\nUse --format=json to get this in machine readable format"
        return out

    def to_json(self, dateformat: str = "", **kwargs) -> str:
        data = dataclasses.asdict(self)
        for ci in ["carbonIntensityNow", "carbonIntensityOptimal"]:
            if dateformat == "":
                data[ci]["start"] = data[ci]["start"].isoformat()
                data[ci]["end"] = data[ci]["end"].isoformat()
            else:
                data[ci]["start"] = data[ci]["start"].strftime(dateformat)
                data[ci]["end"] = data[ci]["end"].strftime(dateformat)

        return json.dumps(data, **kwargs)


def schedule_at(
    output: CATSOutput, args: list[str], at_command: str = "at"
) -> Optional[str]:
    """Schedule job with optimal start time using at(1)

    :return: Error as a string, or None if successful
    """
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    try:
        subprocess.check_output(
            (
                at_command,
                "-t",
                output.carbonIntensityOptimal.start.strftime(
                    SCHEDULER_DATE_FORMAT["at"]
                ),
            ),
            stdin=proc.stdout,
        )
        return None
    except FileNotFoundError:
        return "No at command found in PATH, please install one"
    except subprocess.CalledProcessError as e:
        return f"Scheduling with at failed with code {e.returncode}, see output below:\n{e.output}"


def main(arguments=None) -> int:
    parser = parse_arguments()
    args = parser.parse_args(arguments)
    if args.command and not args.scheduler:
        print(
            "cats: To run a command with the -c or --command option, you must\n"
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
    now_avg, best_avg = get_avg_estimates(CI_forecast, duration=duration)
    output = CATSOutput(now_avg, best_avg, location, "GBR")

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
            dateformat = SCHEDULER_DATE_FORMAT.get(args.dateformat, "")
        else:
            dateformat = args.dateformat or ""
        print(output.to_json(dateformat, sort_keys=True, indent=2))
    else:
        print(output)
    if args.command and args.scheduler == "at":
        if err := schedule_at(output, args.command.split()):
            print(err)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
