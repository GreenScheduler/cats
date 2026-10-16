import os
from contextlib import contextmanager
from pathlib import Path
from typing import cast
from unittest.mock import Mock, patch

import pytest

import cats
from cats.cli import parse_arguments
from cats.configure import (
    Args,
    config_from_file,
    get_job_info,
    get_location_from_config_or_args,
    provider_from_config_or_args,
)
from cats.constants import MEMORY_POWER_PER_GB
from cats.exceptions import UnsupportedProviderError
from cats.providers import GBCarbonIntensityProvider

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
    p = tmp_path_factory.mktemp("temp") / "config.toml"
    p.write_text("\n".join(f'{k} = "{v}"' for k, v in CATS_CONFIG.items()))
    return p.parent


def test_config_from_file():
    missing_file = "missing.toml"
    with pytest.raises(FileNotFoundError):
        config_from_file(missing_file)
        config_from_file()


def test_config_from_file_default(local_config_file):
    with change_dir(local_config_file):
        configmapping = config_from_file()
    assert configmapping == CATS_CONFIG


def test_config_from_file_path(local_config_file):
    configmapping = config_from_file(str(local_config_file / "config.toml"))
    assert configmapping == CATS_CONFIG


@pytest.mark.parametrize("filename", ["cats_config.yml", "config.yaml"])
def test_config_from_file_warns_legacy_yaml(tmp_path, caplog, filename):
    (tmp_path / filename).write_text('location: "EH8"\n')
    with change_dir(tmp_path):
        assert config_from_file() == {}
    assert f"please convert {filename} to TOML" in caplog.text


def test_config_from_env_warns_yaml(tmp_path, caplog, monkeypatch):
    monkeypatch.setenv("CATS_CONFIG_FILE", str(tmp_path / "config.yml"))
    assert config_from_file() == {}
    assert "YAML configuration files are no longer supported" in caplog.text


def test_config_from_env(local_config_file, monkeypatch):
    monkeypatch.setenv("CATS_CONFIG_FILE", str(local_config_file / "config.toml"))
    configmapping = config_from_file()
    assert configmapping == CATS_CONFIG


def test_example_config_parses():
    config = config_from_file(str(Path(cats.__file__).with_name("config.toml")))
    assert set(config["profiles"]) == {"my_cpu_only_profile", "my_gpu_profile"}


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


def get_provider_from_config_or_args(args, config):
    args = cast(
        Args,
        parse_arguments().parse_args(
            ["--api", "carbonintensity.org.uk", "--duration", "1"]
        ),
    )
    assert provider_from_config_or_args(args, CATS_CONFIG) == GBCarbonIntensityProvider

    args = cast(Args, parse_arguments().parse_args(["--duration", "1"]))
    assert provider_from_config_or_args(args, CATS_CONFIG) == GBCarbonIntensityProvider

    args = cast(
        Args,
        parse_arguments().parse_args(
            ["--api", "doesnotexist.co.uk", "--duration", "1"]
        ),
    )
    with pytest.raises(UnsupportedProviderError):
        _ = provider_from_config_or_args(args, CATS_CONFIG)


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
