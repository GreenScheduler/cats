from contextlib import contextmanager
from pathlib import Path
import os

import pytest
import yaml

from cats.configure import config_from_file
from cats.configure import get_location_from_config_or_args
from cats.configure import CI_API_from_config_or_args
from cats import parse_arguments
from cats.CI_api_interface import API_interfaces

CATS_CONFIG = {
    "location": "EH8",
    "api": "carbonintensity.org.uk",
}

@contextmanager
def change_dir(p):
    current_dir = os.getcwd()
    os.chdir(p)
    yield
    os.chdir(current_dir)


@pytest.fixture
def local_config_file(tmp_path_factory):
    p = tmp_path_factory.mktemp("temp") / "config.yml"
    with open(p, "w") as stream:
        yaml.dump(CATS_CONFIG, stream)
    return p.parent


def test_config_from_file():
    missing_file = "missing.yaml"
    with pytest.raises(FileNotFoundError):
        config_from_file(missing_file)
        config_from_file()

def test_config_from_file_default(local_config_file):
    with change_dir(local_config_file):
        configmapping = config_from_file()
    assert configmapping == CATS_CONFIG

def test_get_location_from_config_or_args():
    expected_location = "SW7"
    args = parse_arguments().parse_args(
        ["--location", expected_location, "--duration", "1"]
    )
    location = get_location_from_config_or_args(args, CATS_CONFIG)
    assert location == expected_location

    args = parse_arguments().parse_args(["--duration", "1"])
    location = get_location_from_config_or_args(args, CATS_CONFIG)
    assert location == CATS_CONFIG["location"]

    args = parse_arguments().parse_args(["--duration", "1"])
    config = {}
    location = get_location_from_config_or_args(args, config)
    assert location != ""

def get_CI_API_from_config_or_args(args, config):
    expected_interface = API_interfaces["carbonintensity.org.uk"]
    args = parse_arguments().parse_args(
        ["--api", "carbonintensity.org.uk", "--duration", "1"]
    )
    API_interface = CI_API_from_config_or_args(args, CATS_CONFIG)
    assert API_interface == expected_interface

    args = parse_arguments().parse_args(["--duration", "1"])
    API_interface = CI_API_from_config_or_args(args, CATS_CONFIG)
    assert API_interface == expected_interface

    args = parse_arguments().parse_args(
        ["--api", "doesnotexist.co.uk", "--duration", "1"]
    )
    API_interface = CI_API_from_config_or_args(args, CATS_CONFIG)
    with pytest.raises(KeyError):
        CI_API_from_config_or_args(args, CATS_CONFIG)
