from argparse import ArgumentParser
import requests
import subprocess
import yaml
from tempfile import NamedTemporaryFile
from pathlib import Path

from .timeseries_conversion import cat_converter  # noqa: F401
from .api_query import get_tuple  # noqa: F401
from .parsedata import writecsv  # noqa: F401

# from cats import findtime


def findtime(postcode, duration):
    tuples = get_tuple(postcode)
    result = parsedata.writecsv(data_tuples, duration)
    print(result)
    return result["timestamp"]


def parse_arguments():
    parser = ArgumentParser(prog="cats", description="A climate aware job scheduler")

    parser.add_argument("program")
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
    print("Location:", loc)

    runtime = findtime(loc, args.duration)

    subprocess.run(
        [
            args.program,
            "|",
            "at",
            "-m",
            f"{runtime:%m%d%H%M}",
        ]
    )


if __name__ == "__main__":
    main()
