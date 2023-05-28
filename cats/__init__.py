from argparse import ArgumentParser
import requests
import yaml
from datetime import timedelta, datetime, timezone
import sys
import re

from .CI_api_query import CI_API
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
            sys.stdout.write(f"Using provided config file: {args.config}\n")
        else:
            try:
                # if no path provided, look for `config.yml` in current directory
                with open("config.yml", "r") as f:
                    self.config = yaml.safe_load(f)
                sys.stdout.write("Using config.yml found in current directory\n")
            except FileNotFoundError:
                # config file not essential, so initialised as None if missing
                sys.stderr.write("WARNING: config file not found\n")
                self.config = {}

        ### Pull and clean location ###
        # UK: we only keep the first part of a UK postcode

        if args.location:
            self.location = args.location
            sys.stdout.write(f"Using location provied: {self.location}\n")
        elif "location" in self.config.keys():
            self.location = self.config["location"]
            sys.stdout.write(f"Using location from config file: {self.location}\n")
        else:
            self.location = self._pull_location_from_IP()
            sys.stderr.write(f"WARNING: location not provided. Estimating location from IP address: {self.location}.\n")
        # TODO what is location is not in the right country for the API?

        # TODO check validity of arguments (and clean/standardise them)

        ### API choice ###

        if args.api_carbonintensity:
            self.choice_CI_API = args.api_carbonintensity
        elif 'api-carbonintensity' in self.config.keys():
            self.choice_CI_API = self.config["api-carbonintensity"]
        else:
            self.choice_CI_API = 'carbonintensity.org.uk'  # default value is UK
        sys.stdout.write(f"Using {self.choice_CI_API} for carbon intensity forecasts.\n")

        ### Duration ###
        self.duration = timedelta(minutes=args.duration)

        ### jobinfo ###
        self.jobinfo = self._validate_jobinfo(args.jobinfo) if (args.jobinfo and self.config) else None

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
            help="[optional] which API should be used to obtain carbon intensity forecasts. Overrides `config.yml`."
                 "For now, only choice is 'carbonintensity.org.uk' (UK only) (default: 'carbonintensity.org.uk')"
        )
        # Note: 'api-carbonintensity' will become 'api_carbonintensity' when parsed by argparse
        parser.add_argument(
            "--location", type=str,
            help="[optional] location of the computing facility. For the UK, first half of a postcode (e.g. 'M15'), "
                 "for other APIs, see doc for exact format. Overrides `config.yml`. "
                 "If absent, location based in IP address is used."
        )
        parser.add_argument(
            "--config", type=str,
            help="[optional] path to a config file, default is `config.yml` in current directory. "
                 "Config file is required to obtain carbon footprint estimates."
                 "template at https://github.com/GreenScheduler/cats/blob/main/config.yml"
        )

        parser.add_argument(
            "--jobinfo", type=str,
            help="Resources used by the job in question, used to estimate total energy usage and carbon footprint. "
                 "E.g. 'cpus=2,gpus=0,memory=8,partition=CPU_partition'. "
                 "`cpus`: number of CPU cores, `gpus`: number of GPUs, `memory`: memory available in GB, "
                 "`partition`: one of the partitions keys in `config.yml`."
        )

        return parser

    def _pull_location_from_IP(self):
        r = requests.get("https://ipapi.co/json").json()
        return r["postal"]

    def _validate_jobinfo(self, jobinfo: str):
        '''
        Parses a string of job info keys in the form

        partition=CPU_partition,memory=8,cpus=8,gpus=0

        and checks all required info keys are present and of the right type.
        :param jobinfo: [str]
        :return: [dict] A dictionary mapping info key to their specified values
        '''

        expected_info_keys = (
            "partition",
            "memory",
            "cpus",
            "gpus",
        )
        info = dict([match.groups() for match in re.finditer(r"(\w+)=(\w+)", jobinfo)])

        # Check if some information is missing
        missing_keys = set(expected_info_keys) - set(info.keys())
        if missing_keys:
            sys.stderr.write(f"ERROR: Missing job info keys: {missing_keys}, energy usage cannot be estimated.\n")
            return None

        # Validate partition value
        expected_partition_values = self.config['partitions'].keys()
        if info["partition"] not in expected_partition_values:
            sys.stderr.write(
                "ERROR: job info key 'partition' should be "
                f"one of {expected_partition_values}. Typo?"
            )
            return None

        # check that `cpus`, `gpus` and `memory` are numeric and convert to int
        for key in [k for k in info if k != "partition"]:
            try:
                info[key] = int(info[key])
            except ValueError:
                sys.stderr.write(f"ERROR: job info key {key} should be numeric")
                return None

        return info

    def _str_datetime(self, dt):
        return dt.strftime("%d/%m/%Y-%H:%M UTC")

    def _writeout_progress(self, stage):
        if stage=='forecast_obtained':
            sys.stdout.write(
                f"\nCarbon intensity forecast loaded for between {self._str_datetime(self.CI_forecast[0].start)} "
                f"and {self._str_datetime(self.CI_forecast[-1].end)}.\n"
            ) # TODO check why it was stderr originally

        if stage=='best_starttime':
            in_delta = self.best_window.start - datetime.now(timezone.utc)
            sys.stdout.write(f"\nBest start time: {self._str_datetime(self.best_window.start)} (in {in_delta.total_seconds()/3600:.1f} hours)")
            sys.stdout.write(f"\n\t Expected end time: {self._str_datetime(self.best_window.end)}")
            sys.stdout.write(f"\n\t Expected average carbon intensity: {self.best_window.value:.2f} gCO2e/kWh\n")
            # TODO check what unit the forecast comes in (should be grams)

    def run(self):
        ### Get CI forecast
        instance_CI_API = CI_API(self.choice_CI_API)
        self.CI_forecast = instance_CI_API.get_forecast(self.location)
        self._writeout_progress('forecast_obtained')

        ### Find best starttime
        self.best_window, self.all_window_sorted = starttime_optimiser(self.CI_forecast).get_starttime(self.duration)
        self._writeout_progress('best_starttime')
        # print(f"{self.best_window.start:%Y%m%d%H%M}")  # TODO check if still needed: for POSIX compatibility with at -t

        ### Calculate total energy usage and carbon footprint
        if not (self.jobinfo and self.config):
            sys.stderr.write("Not enough information to estimate total carbon footprint, both --jobinfo and config files are needed.")
        else:
            pass

        print()

if __name__ == "__main__":
    instance_cats = cats()
    foo = instance_cats.run()

    print()
