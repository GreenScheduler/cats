from argparse import ArgumentParser
from datetime import datetime, timedelta
import requests
import yaml
import sys

from .check_clean_arguments import validate_jobinfo, validate_duration
from .optimise_starttime import get_avg_estimates  # noqa: F401
from .CI_api_interface import API_interfaces, InvalidLocationError
from .CI_api_query import get_CI_forecast  # noqa: F401
from .carbonFootprint import greenAlgorithmsCalculator

def parse_arguments():
    """
    Parse command line arguments
    :return: [dict] parsed arguments
    """
    description_text = """
    The Climate-Aware Task Scheduler (cats) command line programme helps you run your
    calculations in a way that minimises their impact on the climate by delaying computation
    until a time when the ammount of CO2 produced to generate the power you will use is
    predicted to be minimised. By default, the command simply returns information about
    when the calculation should be undertaken and compares the carbon intensity (gCO2/kWh)
    of running the calculation now with the carbon intensity at that time in the future.
    To undertake this calculation, cats needs to know the predicted duration of the 
    calculation (which you must supply, see `-d`) and your location (which can be inferred from
    your IP address (but see `-l`). If additional information about the power consumption of
    your computer is available (see `--jobinfo`) the predicted CO2 usage will be reported.

    To make use of this information, you will need to couple cats with a task scheduler of some
    kind. The `--scheduler` option is designed to make this easy by returning the start time
    in a format sutible for commonly available scheduling software.
    """

    example_text = """
    Examples\n
    ********\n
    
    Cats can be used to report information on the best time to run a calculation and the amount
    of CO2. Information about a 90 minute calculation in centeral Oxford can be found by running:

        cats -d 90 --loc OX1 --jobinfo="cpus=2,gpus=0,memory=8,partition=CPU_partition"

    The `at` scheduler is available from the command line on  most Linux and MacOS computers,
    and can be the easest way to use cats to minimise the carbon intensity of calculations on
    smaller computers. For example, the above calculation can be scheduled by running:

        mycommand | at -t `cats -d 90 --loc OX1 -s at`
    """

    parser = ArgumentParser(prog="cats", description=description_text, epilog=example_text)

    ### Required

    parser.add_argument(
        "-d", "--duration", type=int, required=True, help="[required] Expected duration of the job in minutes.")

    ### Optional

    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress all output except the optimised run time.")

    parser.add_argument(
        "-s", "--scheduler", type=str,
        help="Format optimised run time for the chosen scheduler. Implies -q such that standard output can"
             "be fed directly into the scheduler. See examples, below. For now, only choice is `at`."
             "Default: human readable time information."
    )
    parser.add_argument(
        "-a", "--api", type=str,
        help="API to use to obtain carbon intensity forecasts. Overrides `config.yml`. "
             "For now, only choice is `carbonintensity.org.uk` (hence UK only forecasts). "
             "Default: `carbonintensity.org.uk`."
    )
    parser.add_argument(
        "-l", "--location", type=str,
        help="Location of the computing facility. For the UK, first half of a postcode (e.g. `M15`), "
             "for other APIs, see documentation for exact format. Overrides `config.yml`. "
             "Default: if absent, location based in IP address is used."
    )
    parser.add_argument(
        "--config", type=str,
        help="Path to a configuration file. The file is required to obtain carbon footprint estimates. "
             "Default: `config.yml` in current directory."
             "Template found at https://github.com/GreenScheduler/cats/blob/main/config.yml."
    )
    parser.add_argument(
        "--jobinfo", type=str,
        help="Resources used by the job in question, used to estimate total energy usage and carbon footprint. "
             "E.g. `cpus=2,gpus=0,memory=8,partition=CPU_partition`. Valid components are "
             "`cpus`: number of CPU cores; `gpus`: number of GPUs; `memory`: memory available in GB; "
             "`partition`: one of the partitions keys given in `config.yml`. "
             "Default: if absent, the total carbon footprint is not estimated."
    )

    return parser


def main(arguments=None):
    parser = parse_arguments()
    args = parser.parse_args(arguments)

    ##################################
    ## Validate and clean arguments ##
    ##################################

    ## config file
    if args.config:
        # if path to config file provided, it is used
        with open(args.config, "r") as f:
            config = yaml.safe_load(f)
        sys.stderr.write(f"Using provided config file: {args.config}\n")
    else:
        # if no path provided, look for `config.yml` in current directory
        try:
            with open("config.yml", "r") as f:
                config = yaml.safe_load(f)
            sys.stderr.write("Using config.yml found in current directory\n")
        except FileNotFoundError:
            config = {}
            sys.stderr.write("WARNING: config file not found\n")

    ## CI API choice
    list_CI_APIs = ['carbonintensity.org.uk']

    choice_CI_API = 'carbonintensity.org.uk' # default value
    if 'api' in config.keys():
        choice_CI_API = config["api"]
    if args.api:
        choice_CI_API = args.api

    if choice_CI_API not in list_CI_APIs:
        raise ValueError(f"{choice_CI_API} is not a valid API choice, it needs to be one of {list_CI_APIs}.")
    sys.stderr.write(f"Using {choice_CI_API} for carbon intensity forecasts\n")

    ## Location
    if args.location:
        location = args.location
        sys.stderr.write(f"Using location provided: {location}\n")
    elif "location" in config.keys():
        location = config["location"]
        sys.stderr.write(f"Using location from config file: {location}\n")
    else:
        r = requests.get("https://ipapi.co/json").json()
        postcode = r["postal"]
        location = postcode
        sys.stderr.write(f"WARNING: location not provided. Estimating location from IP address: {location}.\n")

    ## Duration
    duration = validate_duration(args.duration)

    ########################
    ## Obtain CI forecast ##
    ########################

    CI_API_interface = API_interfaces[choice_CI_API]
    try:
        CI_forecast = get_CI_forecast(location, CI_API_interface)
    except InvalidLocationError:
        sys.stderr.write(f"Error: unknown location {location}\n")
        sys.stderr.write(
            "Location should be be specified as the outward code,\n"
            "for example 'SW7' for postcode 'SW7 EAZ'.\n"
        )
        sys.exit(1)

    #############################
    ## Find optimal start time ##
    #############################

    # Find best possible average carbon intensity, along
    # with corresponding job start time.
    now_avg, best_avg = get_avg_estimates(
        CI_forecast, duration=duration
    )
    sys.stderr.write(str(best_avg) + "\n")

    sys.stderr.write(f"Best job start time: {best_avg.start}\n")
    print(f"{best_avg.start:%Y%m%d%H%M}")  # for POSIX compatibility with at -t

    ################################
    ## Calculate carbon footprint ##
    ################################

    error_message = "Not enough information to estimate total carbon footprint, both --jobinfo and config files are needed.\n"

    if args.jobinfo:
        jobinfo = validate_jobinfo(args.jobinfo, expected_partition_names=config['partitions'].keys())

        if not (jobinfo and config):
            sys.stderr.write(error_message)
        else:
            estim = greenAlgorithmsCalculator(
                config=config,
                runtime=timedelta(minutes=args.duration),
                averageBest_carbonIntensity=best_avg.value, # TODO replace with real carbon intensity
                averageNow_carbonIntensity=now_avg.value,
                **jobinfo,
            ).get_footprint()

            sys.stderr.write(f"Estimated emmissions for running job now: {estim.now}\n")
            msg = (
                f"Estimated emmissions for running delayed job: {estim.best})\n"
                f" (- {estim.savings})"
            )
            sys.stderr.write(msg)


if __name__ == "__main__":
    main()
