from argparse import ArgumentParser
from datetime import timedelta
import requests
import subprocess
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
    parser.add_argument("-d", "--duration", required=True)

    return parser


def main(arguments=None):
    with open("config.yml", "r") as f:
        config = yaml.safe_load(f)
    parser = parse_arguments()
    args = parser.parse_args(arguments)

    if not args.loc:
        if "postcode" not in config.keys():
            r = requests.get("https://ipapi.co/json").json()
            loc = r["postal"]
        else:
            loc = config["postcode"]
    else:
        loc = args.loc
    #print("Location:", loc)

    runtime = findtime(loc, args.duration)
    print(f"{runtime:%H:%M %b %d %Y}")
#    subprocess.run(
#        [
#            args.program,
#            "|",
#            "at",
#            "-m",
#            f"{runtime:%m%d%H%M}",
#        ]
#    )

    footprint = greenAlgorithmsCalculator(
        partition = args.partition,
        runtime = timedelta(minutes = 120),
        memory = args.memory,
        nCPUcores = args.ncpus,
        nGPUcores = args.ngpus,
        averageBest_carbonIntensity = 80.,
        averageNow_carbonIntensity = 162.,
        starttime=runtime
    ).get_footprint()


if __name__ == "__main__":
    main()
