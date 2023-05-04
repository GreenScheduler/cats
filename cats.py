from argparse import ArgumentParser
import requests
from cats import findtime

parser = ArgumentParser(prog="cats", description="A climate ware job scheduler")

parser.add_argument("program")
parser.add_argument("--loc")
parser.add_argument("-d", "--duration", required=True)

args = parser.parse_args()

if not args.loc:
    r = requests.get("https://ipapi.co/json").json()
    loc = r["postal"]
runtime = findtime()

subprocess.run(
    [
        args.program,
        "|",
        "at",
        "-m",
        f"{runtime:%m%d%H%M}",
    ]
)
