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


def configure(args):
    configmapping = config_from_file(configpath=args.config)
    return configmapping


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
