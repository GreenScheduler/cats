from argparse import ArgumentParser
import requests
import yaml

class cats():
    def __init__(self, arguments=None):
        parser = self.parse_arguments()
        args = parser.parse_args(arguments)

        ### config file ###

        if args.config:
            # if path to config file provided, it is used
            with open(args.config, "r") as f:
                self.config = yaml.safe_load(f)
        else:
            try:
                # if no path provided, look for `config.yml` in current directory
                with open("config.yml", "r") as f:
                    self.config = yaml.safe_load(f)
            except FileNotFoundError:
                # config file not essential, so initialised as empty dict if missing
                self.config = {}

        ### Pull and clean postcode ###
        # UK: we only keep the first part of a UK postcode

        if args.loc:
            self.loc = args.loc
        elif "postcode" in self.config.keys():
            self.loc = self.config["postcode"]
        else:
            self.loc = self.pull_location_from_IP()


    def parse_arguments(self):
        parser = ArgumentParser(prog="cats", description="A climate aware job scheduler")
        # parser.add_argument("program")
        parser.add_argument("--loc")
        parser.add_argument("-d", "--duration", type=int, required=True)
        parser.add_argument("--jobinfo")
        parser.add_argument("--config")

        return parser

    def pull_location_from_IP(self):
        r = requests.get("https://ipapi.co/json").json()
        return r["postal"]

if __name__ == "__main__":
    cats()
