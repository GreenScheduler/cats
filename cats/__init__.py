from argparse import ArgumentParser
import requests
import yaml
from datetime import datetime, timezone
import sys

from .check_clean_arguments import sanityChecks_arguments
from .CI_api_query import CI_API
from .optimise_starttime import windowed_forecast
from .carbon_footprint import greenAlgorithmsCalculator

class cats:
    def __init__(self, arguments=None):
        parser = self._parse_arguments()
        args = parser.parse_args(arguments)

        self.sanityChecks_arguments = sanityChecks_arguments()

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

        ### API choice ###

        self.list_CI_APIs = ['carbonintensity.org.uk']

        if args.api_carbonintensity:
            self.choice_CI_API = args.api_carbonintensity
        elif 'api-carbonintensity' in self.config.keys():
            self.choice_CI_API = self.config["api-carbonintensity"]
        else:
            self.choice_CI_API = 'carbonintensity.org.uk'  # default value is UK

        if self.choice_CI_API not in self.list_CI_APIs:
            raise ValueError(f"{self.choice_CI_API} is not a valid API choice, it needs to be one of {self.list_CI_APIs}.")

        sys.stdout.write(f"Using {self.choice_CI_API} for carbon intensity forecasts.\n")

        ### Integration method for CI forecasts ###
        if args.integration_method:
            self.integration_method  = args.integration_method
        elif "integration-method" in self.config.keys():
            self.integration_method = self.config["integration-method"]
        else:
            self.integration_method = 'sum'

            ### Pull and clean location ###
        # UK: we only keep the first part of a UK postcode

        if args.location:
            self.location = self.sanityChecks_arguments.validate_location(args.location, self.choice_CI_API)
            sys.stdout.write(f"Using location provided: {self.location}\n")
        elif "location" in self.config.keys():
            self.location = self.sanityChecks_arguments.validate_location(self.config["location"], self.choice_CI_API)
            sys.stdout.write(f"Using location from config file: {self.location}\n")
        else:
            self.location = self.sanityChecks_arguments.validate_location(self._pull_location_from_IP(), self.choice_CI_API)
            sys.stderr.write(f"WARNING: location not provided. Estimating location from IP address: {self.location}.\n")
        # TODO what is location is not in the right country for the API?

        ### Duration [timedelta] ###
        self.duration = self.sanityChecks_arguments.validate_duration(args.duration)

        ### jobinfo [dict] ###
        self.jobinfo = self.sanityChecks_arguments.validate_jobinfo(args.jobinfo, self.config) if (args.jobinfo and self.config) else None

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
        ) # Note: 'api-carbonintensity' will become 'api_carbonintensity' when parsed by argparse
        parser.add_argument(
            "--integration-method", type=str,
            help="[optional] how carbon intensity is being averaged over the entire runtime. "
                 "Either 'sum' or 'trapezoidal' (default: 'sum')."
        )
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

    def _str_datetime(self, dt):
        return dt.strftime("%d/%m/%Y-%H:%M UTC")

    def _writeout_progress(self, stage):
        if stage=='forecast_obtained':
            sys.stdout.write(
                f"\nCarbon intensity forecast loaded for between {self._str_datetime(self.CI_forecast[0].start)} "
                f"and {self._str_datetime(self.CI_forecast[-1].end)}.\n"
            ) # TODO check why it was stderr originally

        if stage=='best_starttime':
            # TODO fix clearer message when job should start now
            in_delta = self.best_window.start - datetime.now(timezone.utc)
            sys.stdout.write(f"\nBest start time: {self._str_datetime(self.best_window.start)} (in {in_delta.total_seconds()/3600:.1f} hours)\n")
            sys.stdout.write(f"\t Expected end time: {self._str_datetime(self.best_window.end)}\n")
            sys.stdout.write(f"\t Expected average carbon intensity: {self.best_window.value:.2f} gCO2e/kWh\n")

        if stage=='carbon_footprint':
            sys.stdout.write(f"\nEstimated carbon footprint of running job at best time: {self.GAcalc.formatText_footprint(self.CFs['best']['total'])}\n")
            sys.stdout.write(f"\tvs running it now: {self.GAcalc.formatText_footprint(self.CFs['now']['total'])} "
                             f"({self.GAcalc.formatText_footprint(self.CFs['now']['total']-self.CFs['best']['total'])} saved)\n")
            sys.stdout.write(f"\tvs running at worst time ({self._str_datetime(self.worst_window.start)}): {self.GAcalc.formatText_footprint(self.CFs['worst']['total'])} "
                             f"({self.GAcalc.formatText_footprint(self.CFs['worst']['total']-self.CFs['best']['total'])} saved)\n")
            sys.stdout.write(f"\t- Estimated energy usage: {self.energies['total']:.2f} kWh\n")

    def run(self):
        ### Get CI forecast
        instance_CI_API = CI_API(self.choice_CI_API)
        self.CI_forecast = instance_CI_API.get_forecast(self.location)
        self._writeout_progress('forecast_obtained')

        ### Find best starttime
        self.best_window, self.all_windows = windowed_forecast(self.CI_forecast, self.integration_method).get_starttime(self.duration)
        self.window_now = self.all_windows[0]
        self.worst_window = max(self.all_windows)
        self._writeout_progress('best_starttime')
        # print(f"{self.best_window.start:%Y%m%d%H%M}")  # TODO check if still needed: for POSIX compatibility with at -t

        ### Calculate total energy usage and carbon footprint
        if not (self.jobinfo and self.config):
            sys.stderr.write("Not enough information to estimate total carbon footprint, both --jobinfo and config files are needed.")
        else:
            self.GAcalc = greenAlgorithmsCalculator(
                config = self.config,
                jobinfo=self.jobinfo,
                duration=self.duration,
                averageBest_carbonIntensity=self.best_window,
                averageNow_carbonIntensity=self.window_now,
                averageWorst_carbonIntensity=self.worst_window
            )
            self.CFs, self.energies = self.GAcalc.get_carbonFootprint()
            self._writeout_progress('carbon_footprint')

if __name__ == "__main__":
    instance_cats = cats()
    foo = instance_cats.run()

