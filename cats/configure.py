"""This module exports a function that processes both command line
arguments and configuration file. This function returns a
configuration for cats to make a request to a carcon intensity
forecast provider.  A configuration consits of:

- location
- job duration
- Interface to carbon intensity forecast provider (See TODO)
"""
from collections.abc import Mapping
from typing import Any

import yaml

from .CI_api_interface import API_interfaces, APIInterface


def configure(args):
    configmapping = config_from_file(configpath=args.config)
    CI_API_interface = CI_API_from_config_or_args(args, configmapping)

    return configmapping, CI_API_interface


def config_from_file(configpath = "") -> Mapping[str, Any]:
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
        api = 'carbonintensity.org.uk'  # default value
        logging.warning(
            "Unspecified carbon intensity forecast service, "
            f"using {api}"
        )
    try:
        return API_interfaces[api]
    except KeyError:
        logging.error(
            f"Error: {api} is not a valid API choice. It must be one of "
            "\n".join(API_interfaces.keys())
        )
