from argparse import ArgumentParser
import requests
import subprocess

# from cats import findtime


def parse_arguments():
    parser = ArgumentParser(prog="cats", description="A climate ware job scheduler")

    parser.add_argument("program")
    parser.add_argument("--loc")
    parser.add_argument("-d", "--duration", required=True)

    return parser


def main(arguments=None):
    parser = parse_arguments()
    args = parser.parse_args(arguments)

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


if __name__ == "__main__":
    main()
