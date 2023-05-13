from argparse import ArgumentParser
from datetime import timedelta
import requests
import subprocess
import re
import yaml
import sys

from .timeseries_conversion import cat_converter  # noqa: F401
from .api_query import get_tuple  # noqa: F401
from .parsedata import writecsv  # noqa: F401
from .carbonFootprint import greenAlgorithmsCalculator

# from cats import findtime


def findtime(postcode, duration):
    tuples = get_tuple(postcode)
    result = writecsv(tuples, duration)
    sys.stderr.write(str(result) + "\n")
    return result["timestamp"]


def parse_arguments():
    parser = ArgumentParser(prog="cats", description="A climate aware job scheduler")

    #parser.add_argument("program")
    parser.add_argument("--loc")
    parser.add_argument("-d", "--duration", type=int, required=True)
    parser.add_argument("--jobinfo")
    parser.add_argument("--config")

    return parser


def validate_jobinfo(jobinfo: str):
    """Parses a string of job info keys in the form

    partition=CPU_partition,memory=8,ncpus=8,ngpus=0

    and checks all required info keys are present and of the right type.

    Returns
    -------

    info: dict
        A dictionary mapping info key to their specified values
    """

    expected_info_keys = (
        "partition",
        "memory",
        "cpus",
        "gpus",
    )
    info = {
        k: v
        for k, v in [match.groups() for match in re.finditer(r"(\w+)=(\w+)", jobinfo)]
    }
    missing_keys = set(expected_info_keys) - set(info.keys())
    if missing_keys:
        print(f"ERROR: Missing job info keys: {missing_keys}")
        return {}
    expected_partition_values = ("CPU_partition", "GPU_partition")
    if info["partition"] not in expected_partition_values:
        msg = (
            "ERROR: job info key 'partition' should be "
            f"one of {expected_partition_values}. Typo?"
        )
        print(msg)
        return {}
    for key in [k for k in info.keys() if k != "partition"]:
        try:
            info[key] = int(info[key])
        except ValueError:
            print(f"ERROR: job info key {key} should be numeric")
            return {}
    return info


def main(arguments=None):
    parser = parse_arguments()
    args = parser.parse_args(arguments)

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

    best_estimate = findtime(loc, args.duration)
#    subprocess.run(
#        [
#            args.program,
#            "|",
#            "at",
#            "-m",
#            f"{runtime:%m%d%H%M}",
#        ]
#    )

    sys.stderr.write(f"Best job start time: {best_estimate.datetime}\n")
    print(f"{best_estimate.datetime:%Y%m%d%H%M}")  # for POSIX compatibility with at -t

    if args.jobinfo:
        jobinfo = validate_jobinfo(args.jobinfo)
        if not jobinfo:
            print("ERROR: job info parsing failed, exiting now")
            exit(1)
        if not config:
            print("ERROR: config file not found, exiting now")
            exit(1)
        estim = greenAlgorithmsCalculator(
            config=config,
            runtime=timedelta(minutes=args.duration),
            averageBest_carbonIntensity=best_estimate.value, # TODO replace with real carbon intensity
            averageNow_carbonIntensity=290, # TODO replace with real carbon intensity
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
