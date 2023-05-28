from argparse import ArgumentParser
import requests
import yaml
from datetime import timedelta
import sys

from .api_query import CI_API
from .optimise_starttime import starttime_optimiser

class cats():
    def __init__(self, arguments=None):
        parser = self._parse_arguments()
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

        ### API choice ###

        if args.api_carbonintensity:
            self.choice_CI_API = args.api_carbonintensity
        elif 'api-carbonintensity' in self.config.keys():
            self.choice_CI_API = self.config["api-carbonintensity"]
        else:
            self.choice_CI_API = 'carbonintensity.org.uk' # default value is UK

        ### Pull and clean location ###
        # UK: we only keep the first part of a UK postcode

        if args.location:
            self.location = args.location
        elif "location" in self.config.keys():
            self.location = self.config["location"]
        else:
            self.location = self._pull_location_from_IP()
        # TODO what is location is not in the right country for the API?

        # TODO check validity of arguments (and clean/standardise them)

        ### Duration ###
        self.duration = timedelta(minutes=args.duration)

    def _parse_arguments(self):
        parser = ArgumentParser(
            prog="cats",
            description="A climate aware job scheduler."
        )
        # Required
        parser.add_argument(
            "-d", "--duration", type=int, required=True,
            help="Expected duration of the job in minutes."
        )

        # Optional
        parser.add_argument(
            "--api-carbonintensity", type=str,
            help="[optional] which API should be used to obtain carbon intensity forecasts."
                 "For now, only choice is 'carbonintensity.org.uk' (UK only) (default: 'carbonintensity.org.uk')"
        )
        # Note: 'api-carbonintensity' will become 'api_carbonintensity' when parsed by argparse
        parser.add_argument(
            "--location", type=str,
            help="[optional] location of the computing facility. For the UK, first half of a postcode (e.g. 'M15'), "
                 "for other APIs, see doc for exact format."
        )
        parser.add_argument("--jobinfo")
        parser.add_argument("--config")

        return parser

    def _pull_location_from_IP(self):
        r = requests.get("https://ipapi.co/json").json()
        return r["postal"]

    def run(self):
        # Get CI forecast
        instance_CI_API = CI_API(self.choice_CI_API)
        CI_forecast = instance_CI_API.get_forecast(self.location)

        # Find best starttime
        best_window, all_window_sorted = starttime_optimiser(CI_forecast).get_starttime(self.duration)


if __name__ == "__main__":
    instance_cats = cats()
    foo = instance_cats.run()

    print()
