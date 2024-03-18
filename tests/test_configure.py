import os
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
import yaml

from cats import parse_arguments
from cats.CI_api_interface import API_interfaces
from cats.configure import (
    CI_API_from_config_or_args,
    config_from_file,
    get_job_info,
    get_location_from_config_or_args,
)
from cats.constants import MEMORY_POWER_PER_GB

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


@patch("cats.configure.requests")
def test_get_location_from_config_or_args(mock_requests):
    expected_location = "SW7"
    mock_requests.get.return_value = Mock(
        **{
            "status_code": 200,
            "json.return_value": {"postal": expected_location},
        }
    )

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
    mock_requests.get.assert_called_once()
    assert location == expected_location


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


def test_get_jobinfo():
    profiles = {
        "CPU_partition": {
            "cpu": {
                "model": "Xeon Gold 6142",
                "power": 9.4,
                "nunits": 8,
            }
        },
        "GPU_partition": {
            "cpu": {"model": "AMD EPYC 7763", "power": 4.4, "nunits": 1},
            "gpu": {
                "nunits": 2,
                "power": 300,
            },
        },
    }
    args = parse_arguments().parse_args(["--duration", "2", "--memory", "8"])
    assert get_job_info(args, profiles) == [(8, 9.4), (8, MEMORY_POWER_PER_GB)]

    args = parse_arguments().parse_args(
        ["--duration", "2", "--profile", "GPU_partition", "--memory", "8"]
    )
    assert get_job_info(args, profiles) == [
        (1, 4.4),
        (2, 300),
        (8, MEMORY_POWER_PER_GB),
    ]

    args = parse_arguments().parse_args(
        ["--duration", "2", "--profile", "GPU_partition", "--cpu", "2", "--memory", "8"]
    )
    assert get_job_info(args, profiles) == [
        (2, 4.4),
        (2, 300),
        (8, MEMORY_POWER_PER_GB),
    ]

    args = parse_arguments().parse_args(
        ["--duration", "2", "--profile", "unknown_profile", "--memory", "8"]
    )
    with pytest.raises(SystemExit):
        get_job_info(args, profiles)
