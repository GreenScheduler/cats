# Tests main() function
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import requests

from cats.cli import main, print_banner
from cats.constants import CATS_ASCII_BANNER_COLOUR, CATS_ASCII_BANNER_NO_COLOUR
from cats.exceptions import InvalidLocationError
from cats.forecast import AverageEstimate, PointEstimate, Timeseries
from cats.output import CATSOutput
from cats.schedulers import SCHEDULER_DATE_FORMAT, schedule_at, schedule_sbatch

AT_OUTPUT = "%a %b %d %H:%M:%S %Y"
now_start = (datetime.now() + timedelta(minutes=1)).replace(second=0)
now_end = now_start + timedelta(minutes=5)

OUTPUT = CATSOutput(
    "Carbon intensity",
    AverageEstimate(20, now_start, now_end, 0.0, 0.0),
    AverageEstimate(20, now_start, now_end, 0.0, 0.0),
    "OX1",
    "GBR",
    "gCO2eq/kWh",
)


@pytest.mark.parametrize("disable_colour", [False, True])
def test_print_banner(disable_colour, capsys):
    print_banner(disable_colour)
    expected_output = (
        CATS_ASCII_BANNER_NO_COLOUR if disable_colour else CATS_ASCII_BANNER_COLOUR
    )
    assert capsys.readouterr().out.strip() == expected_output.strip()


def test_schedule_sbatch_success(fp):
    fp.register_subprocess(
        [
            "sbatch",
            "--begin",
            OUTPUT.valueOptimal.start.strftime(SCHEDULER_DATE_FORMAT["sbatch"]),
            "./script.sh",
        ],
        stdout=b"Submitted batch job 123456",
    )
    schedule_sbatch(OUTPUT, ["./script.sh"])


def test_schedule_sbatch_failure():
    assert schedule_sbatch(OUTPUT, ["./script.sh"])


@pytest.mark.parametrize(
    "exc,err",
    [
        (
            FileNotFoundError,
            "No sbatch command found in PATH, ensure slurm is configured correctly",
        ),
        (
            subprocess.CalledProcessError(1, "sbatch"),
            "Scheduling with sbatch failed with code 1, see output below:\nNone",
        ),
    ],
)
def test_schedule_sbatch_side_effects(exc, err):
    with patch("subprocess.check_output", side_effect=exc):
        assert schedule_sbatch(OUTPUT, ["./script.sh"]) == err


def test_schedule_at_success(fp):
    fp.register_subprocess(["ls"], stdout=b"foobar.txt")
    fp.register_subprocess(
        [
            "at",
            "-t",
            OUTPUT.valueOptimal.start.strftime(SCHEDULER_DATE_FORMAT["at"]),
        ]
    )
    schedule_at(OUTPUT, ["ls"])
    # check that the job was correctly scheduled by checking the at queue (atq)
    fp.register_subprocess(
        ["atq"], stdout=f"1\t\t{now_start.strftime(AT_OUTPUT)}".encode("utf-8")
    )
    assert now_start.strftime(AT_OUTPUT) in subprocess.check_output(["atq"]).decode(
        "utf-8"
    )


@pytest.mark.parametrize(
    "exc,err",
    [
        (FileNotFoundError, "No at command found in PATH, please install one"),
        (
            subprocess.CalledProcessError(1, "at"),
            "Scheduling with at failed with code 1, see output below:\nNone",
        ),
    ],
)
def test_schedule_at_side_effects(exc, err):
    with patch("subprocess.check_output", side_effect=exc):
        assert schedule_at(OUTPUT, ["ls"]) == err


def raiseLocationError(*args, **kwargs):  # pyright: ignore[reportUnusedParameter, reportUnknownParameterType]
    raise InvalidLocationError


@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_main_failures(get_data):
    get_data.return_value = {}
    get_data.side_effect = raiseLocationError

    # CATS should fail when command is supplied, but no scheduler
    assert main(["-c", "ls", "-d", "5"]) == 1

    # Invalid location
    assert main(["-d", "5", "--loc", "oxford"]) == 1

    # Duration larger than API maximum
    assert main(["-d", "5000", "--loc", "OX1"]) == 1

    # Missing required --duration (and --list-providers not given)
    assert main([]) == 1


def test_list_providers(capsys):
    assert main(["--list-providers"]) == 0
    out = capsys.readouterr().out
    for name in [
        "carbonintensity.org.uk",
        "wattnet.eu",
        "energy-charts.info",
        "octopus.energy",
    ]:
        assert name in out


def test_list_locations_all(capsys):
    "No --duration needed; every provider's location scheme is shown"
    assert main(["--list-locations"]) == 0
    out = capsys.readouterr().out
    for name in [
        "carbonintensity.org.uk",
        "wattnet.eu",
        "energy-charts.info",
        "octopus.energy",
    ]:
        assert name in out
    assert "OX1" in out
    assert "London" in out
    assert "DE-LU" in out


def test_list_locations_single_provider(capsys):
    assert main(["--list-locations", "octopus.energy"]) == 0
    out = capsys.readouterr().out
    assert "octopus.energy" in out
    assert "East England" in out
    assert "wattnet.eu" not in out


def test_list_locations_with_api_flag(capsys):
    assert main(["--list-locations", "--api", "wattnet.eu"]) == 0
    out = capsys.readouterr().out
    assert "wattnet.eu" in out
    assert "octopus.energy" not in out
    assert "carbonintensity.org.uk" not in out


def test_list_locations_metric_filters_energycharts(capsys):
    assert main(["--list-locations", "energy-charts.info", "--metric", "price"]) == 0
    out = capsys.readouterr().out
    assert "DE-LU" in out
    assert "Country codes" not in out
    assert (
        main(["--list-locations", "energy-charts.info", "--metric", "renewables"]) == 0
    )
    out = capsys.readouterr().out
    assert "Country codes" in out
    assert "DE-LU" not in out


def test_list_locations_unknown_provider():
    assert main(["--list-locations", "nope"]) == 1


def test_list_locations_codes_validate():
    "Every code a provider lists must be accepted by its own validate_location"
    from cats.providers import list_providers

    for name, cls in list_providers().items():
        instance = cls()
        for group in instance.list_locations():
            assert group.locations, name
            for code in group.locations:
                instance.validate_location(code)


def _wide_flat_series(metric: str, unit: str, value: float) -> Timeseries:
    "A flat series spanning well beyond any real 'now' at 30 minute resolution"
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    return Timeseries(
        metric,
        values=[
            PointEstimate(value=value, datetime=start + timedelta(minutes=30 * i))
            for i in range(100)  # 2h before "now" through ~48h after
        ],
        unit=unit,
    )


def test_max_price_mutually_exclusive_with_max_price_increase_pct():
    with pytest.raises(SystemExit):
        main(
            [
                "-d",
                "30",
                "--loc",
                "OX1",
                "--max-price",
                "100",
                "--max-price-increase-pct",
                "10",
            ]
        )


@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_unsatisfiable_price_constraint_reports_error(
    mock_carbon_get_data, mock_resolve_price_series, capsys
):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity", "gCO2eq/kWh", 100.0
    )
    mock_resolve_price_series.return_value = _wide_flat_series(
        "Day-ahead electricity price", "GBP/MWh", 100.0
    )

    assert main(["-d", "30", "--loc", "OX1", "--max-price", "1"]) == 1
    assert "Price constraint not satisfiable" in capsys.readouterr().out


@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_price_report_appears_when_price_available(
    mock_carbon_get_data, mock_resolve_price_series, capsys
):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity", "gCO2eq/kWh", 100.0
    )
    mock_resolve_price_series.return_value = _wide_flat_series(
        "Day-ahead electricity price", "GBP/MWh", 150.0
    )

    assert main(["-d", "30", "--loc", "OX1"]) == 0
    out = capsys.readouterr().out
    assert "Price if job started now" in out
    assert "150.00 GBP/MWh" in out


@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_price_report_absent_when_price_data_out_of_range(
    mock_carbon_get_data, mock_resolve_price_series, capsys
):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity", "gCO2eq/kWh", 100.0
    )
    # Price data exists but is nowhere near the present, so it cannot cover
    # either the "now" or the chosen window: the report must be omitted
    # entirely rather than shown with a stale/misleading comparison.
    mock_resolve_price_series.return_value = Timeseries(
        "Day-ahead electricity price",
        values=[
            PointEstimate(
                value=100.0, datetime=datetime(2020, 1, 1, tzinfo=timezone.utc)
            ),
            PointEstimate(
                value=100.0, datetime=datetime(2020, 1, 1, 1, tzinfo=timezone.utc)
            ),
        ],
        unit="GBP/MWh",
    )

    assert main(["-d", "30", "--loc", "OX1"]) == 0
    assert "Price if job started now" not in capsys.readouterr().out


def raiseHTTPError(*args, **kwargs):  # pyright: ignore[reportUnusedParameter, reportUnknownParameterType]
    raise requests.exceptions.HTTPError


def raiseJSONError(*args, **kwargs):  # pyright: ignore[reportUnusedParameter, reportUnknownParameterType]
    raise requests.exceptions.JSONDecodeError


@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_main_http_ukci_errors(get_data):
    get_data.return_value = {}
    get_data.side_effect = raiseHTTPError

    # CATS should return 1 when we get an HTTP error
    assert main(["-c", "ls", "-d", "5"]) == 1

    get_data.return_value = {}
    get_data.side_effect = raiseJSONError

    # CATS should return 1 when we get an JSON error
    assert main(["-c", "ls", "-d", "5"]) == 1


@patch("cats.providers.WattnetEuProvider.get_data")
def test_main_http_wattnet_errors(get_data):
    get_data.return_value = {}
    get_data.side_effect = raiseHTTPError

    # CATS should return 1 when we get an HTTP error
    assert main(["-c", "ls", "-d", "5"]) == 1

    get_data.return_value = {}
    get_data.side_effect = raiseJSONError

    # CATS should return 1 when we get an JSON error
    assert main(["-c", "ls", "-d", "5"]) == 1
