"""This module exports a function :py:func:`configure
<cats.configure.configure>` that processes both command line arguments
and configuration file. This function returns a runtime configuration
for cats to make a request to a carcon intensity forecast provider.  A
runtime configuration consits of:

- location (postcode)
- job duration
- Interface to carbon intensity forecast provider (See TODO)

"""

import logging
import sys
from collections.abc import Mapping
from typing import Any, Optional

import requests
import yaml

from .CI_api_interface import API_interfaces, APIInterface
from .constants import MEMORY_POWER_PER_GB

__all__ = ["get_runtime_config"]


def get_runtime_config(
    args,
) -> tuple[APIInterface, str, int, Optional[list[tuple[int, float]]], Optional[float]]:
    """Return the runtime cats configuration from list of command line
    arguments and content of configuration file.

    Returns a tuple containing an instance of :py:class:`APIInterface
    <cats.CI_api_interface.APIInterface>`, the location as a string,
    the duration in minutes as an integer, as well as information on
    the number of cpus/gpus used by the job and their power consumption.

    :param args: Command line arguments
    :return: Runtime cats configuration
    :rtype: tuple[APIInterface, str, int, list[tuple[int, float]]]
    :raises ValueError: If job duration cannot be interpreted as a positive integer.

    """
    configmapping = config_from_file(configpath=args.config)
    CI_API_interface = CI_API_from_config_or_args(args, configmapping)
    location = get_location_from_config_or_args(args, configmapping)

    msg = "Job duration must be a positive integer (number of minutes)"
    try:
        duration = int(args.duration)
    except ValueError:
        logging.error(msg)
        raise ValueError
    if duration <= 0:
        logging.error(msg)
        raise ValueError

    if args.footprint:
        for entry in ["profiles", "PUE"]:
            if entry not in configmapping.keys():
                logging.error(f"Missing entry {entry} in configuration file")
                sys.exit(1)
        jobinfo = get_job_info(args, configmapping["profiles"])
        PUE = configmapping["PUE"]
    else:
        jobinfo = None
        PUE = None

    return CI_API_interface, location, duration, jobinfo, PUE


def config_from_file(configpath="") -> Mapping[str, Any]:
    if configpath:
        # if path to config file provided, it is used
        with open(configpath, "r") as f:
            return yaml.safe_load(f)
        logging.info(f"Using provided config file: {configpath}\n")
    else:
        # if no path provided, look for `config.yml` in current directory
        try:
            with open("config.yml", "r") as f:
                return yaml.safe_load(f)
            logging.info("Using config.yml found in current directory\n")
        except FileNotFoundError:
            logging.warning("config file not found")
            return {}


def CI_API_from_config_or_args(args, config) -> APIInterface:
    try:
        api = args.api if args.api else config["api"]
    except KeyError:
        api = "carbonintensity.org.uk"  # default value
        logging.warning(f"Unspecified carbon intensity forecast service, using {api}")
    try:
        interface = API_interfaces[api]
    except KeyError:
        logging.error(
            f"Error: {api} is not a valid API choice. It must be one of " "\n".join(
                API_interfaces.keys()
            )
        )
    return interface


def get_location_from_config_or_args(args, config) -> str:
    if args.location:
        location = args.location
        logging.info(f"Using location provided from command line: {location}")
        return location
    if "location" in config.keys():
        location = config["location"]
        logging.info(f"Using location from config file: {location}")
        return location

    r = requests.get("https://ipapi.co/json/")
    if r.status_code != 200:
        logging.error(
            "Could not get location from ipapi.co.\n"
            f"Got Error {r.status_code} - {r.json()['reason']}\n"
            f"{r.json()['message']}"
        )
        sys.exit(1)
    location = r.json()["postal"]
    assert location
    logging.warning(
        f"location not provided. Estimating location from IP address: {location}."
    )
    return location


def read_device_config(args, key, config):
    if not (nunits := getattr(args, key.lower()) or config.get("nunits")):
        logging.error(f"No number of units specified for device {key}")
    try:
        power = config["power"]
    except KeyError:
        logging.error(f"Can't find power specification for device {key}")
        power = None
    return nunits, power


def get_job_info(args, profiles: dict) -> list[tuple[int, float]]:
    if args.profile:
        try:
            profile = profiles[args.profile]
        except KeyError:
            logging.error(
                f"job info key 'profile' should be one of {profiles.keys()}. Typo?\n"
            )
            sys.exit(1)
    else:
        profile_key, profile = next(iter(profiles.items()))
        logging.warning(f"Using default profile {profile_key}")

    jobinfo = [read_device_config(args, k, v) for k, v in profile.items()]
    if not args.memory:
        logging.error("Missing memory footprint, use --memory")
        sys.exit(1)
    jobinfo += [(args.memory, MEMORY_POWER_PER_GB)]
    if any([not (nunits and power) for nunits, power in jobinfo]):
        logging.error(f"Errors when processing profile {profile_key}")
        sys.exit(1)
    return jobinfo
