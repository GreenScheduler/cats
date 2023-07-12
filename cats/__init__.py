from argparse import ArgumentParser
from datetime import datetime, timedelta
import requests
import yaml
import sys

from .check_clean_arguments import validate_jobinfo, validate_duration
from .optimise_starttime import get_starttime  # noqa: F401
from .CI_api_interface import API_interfaces
from .CI_api_query import get_CI_forecast  # noqa: F401
from .parsedata import avg_carbon_intensity  # noqa: F401
from .carbonFootprint import greenAlgorithmsCalculator

def parse_arguments():
    parser = ArgumentParser(prog="cats", description="A climate aware job scheduler")

    #parser.add_argument("program")
    parser.add_argument("--loc")
    parser.add_argument("-d", "--duration", type=int, required=True)
    parser.add_argument("--jobinfo")
    parser.add_argument("--config")

    return parser


def main(arguments=None):
    parser = parse_arguments()
    args = parser.parse_args(arguments)

    ## Validate and clean arguments

    if args.config:
        with open(args.config, "r") as f:
            config = yaml.safe_load(f)
    else:
        # if no path provided, look for `config.yml` in current directory
        try:
            with open("config.yml", "r") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            config = dict()

    if not args.loc:
        if "postcode" not in config.keys():
            r = requests.get("https://ipapi.co/json").json()
            loc = r["postal"]
        else:
            loc = config["postcode"]
    else:
        loc = args.loc
    #print("Location:", loc)

    duration = validate_duration(args.duration)

    ## Obtain CI forecast
    CI_API_interface = API_interfaces["carbonintensity.org.uk"]  # TODO give choice of API to user
    CI_forecast = get_CI_forecast(loc, CI_API_interface)

    ## Find optimal start time
    best_window = get_starttime(CI_forecast, method="windowed", duration=duration)
    sys.stderr.write(str(best_window) + "\n")

#    subprocess.run(
#        [
#            args.program,
#            "|",
#            "at",
#            "-m",
#            f"{runtime:%m%d%H%M}",
#        ]
#    )

    sys.stderr.write(f"Best job start time: {best_window.start}\n")
    print(f"{best_window.start:%Y%m%d%H%M}")  # for POSIX compatibility with at -t

    if args.jobinfo:
        jobinfo = validate_jobinfo(args.jobinfo)
        if not jobinfo:
            print("ERROR: job info parsing failed, exiting now")
            exit(1)
        if not config:
            print("ERROR: config file not found, exiting now")
            exit(1)
        now_avg_ci = avg_carbon_intensity(
            data=CI_forecast, start=datetime.now(), runtime=timedelta(args.duration)
        )
        estim = greenAlgorithmsCalculator(
            config=config,
            runtime=timedelta(minutes=args.duration),
            averageBest_carbonIntensity=best_window.value, # TODO replace with real carbon intensity
            averageNow_carbonIntensity=now_avg_ci,
            **jobinfo,
        ).get_footprint()

        print(" -!-!- Carbon footprint estimation is a work in progress, coming soon!")
        # Commenting these out while waiting for real carbon intensities
        # print(f"Estimated emmissions for running job now: {estim.now}")
        # msg = (
        #     f"Estimated emmissions for running delayed job: {estim.best})"
        #     f" (- {estim.savings})"
        # )
        # print(msg)


if __name__ == "__main__":
    main()
