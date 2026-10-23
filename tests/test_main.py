# Tests main() function
import io
import json
import logging
import os
import stat
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from cats.cli import (
    configure_logging,
    is_pipe,
    main,
    parse_arguments,
    print_banner,
)
from cats.constants import CATS_ASCII_BANNER_COLOUR, CATS_ASCII_BANNER_NO_COLOUR
from cats.exceptions import InvalidLocationError
from cats.forecast import AverageEstimate, PointEstimate, Timeseries
from cats.output import CATSOutput
from cats.schedulers import SCHEDULER_DATE_FORMAT, schedule_at, schedule_sbatch
from cats.version import version

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


def _wide_flat_series(
    metric: str, unit: str, value: float, starttime: datetime | None = None
) -> Timeseries:
    "A flat series spanning well beyond any real 'now' at 30 minute resolution"
    if starttime is not None:
        start = starttime
    else:
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


@pytest.mark.parametrize(
    "flags,expected_verbose,expected_log_level",
    [
        ([], 0, None),
        (["-v"], 1, None),
        (["-vv"], 2, None),
        (["-v", "-v"], 2, None),
        (["-vvv"], 3, None),
        (["--verbose"], 1, None),
        (["--verbosity"], 1, None),
        (["--log-level", "debug"], 0, "DEBUG"),
        (["--log-level=info"], 0, "INFO"),
        (["--log-level=WARNING"], 0, "WARNING"),
        (["--log-level=error"], 0, "ERROR"),
        (["--log-level=critical"], 0, "CRITICAL"),
        (["-v", "--log-level=DEBUG"], 1, "DEBUG"),
    ],
)
def test_parse_arguments_verbosity(flags, expected_verbose, expected_log_level):
    parser = parse_arguments()
    args = parser.parse_args(flags + ["-d", "30"])
    assert args.verbose == expected_verbose
    assert args.log_level == expected_log_level


@pytest.mark.parametrize(
    "verbosity,log_level,expected_level",
    [
        (0, None, logging.WARNING),
        (1, None, logging.INFO),
        (2, None, logging.DEBUG),
        (3, None, logging.DEBUG),
        (0, "DEBUG", logging.DEBUG),
        (0, "INFO", logging.INFO),
        (0, "WARNING", logging.WARNING),
        (0, "ERROR", logging.ERROR),
        (0, "CRITICAL", logging.CRITICAL),
        (1, "DEBUG", logging.DEBUG),
    ],
)
def test_configure_logging(verbosity, log_level, expected_level):
    configure_logging(verbosity=verbosity, log_level=log_level)
    assert logging.getLogger().level == expected_level


def test_main_verbosity_output(caplog):
    main(["--list-providers"])
    assert logging.getLogger().level == logging.WARNING

    main(["--list-providers", "-v"])
    assert logging.getLogger().level == logging.INFO

    main(["--list-providers", "-vv"])
    assert logging.getLogger().level == logging.DEBUG

    main(["--list-providers", "--log-level=ERROR"])
    assert logging.getLogger().level == logging.ERROR


@pytest.mark.parametrize(
    "isatty_val,st_mode,fileno_raises,expected",
    [
        (False, stat.S_IFIFO, False, True),  # Connected to a pipe (FIFO)
        (True, stat.S_IFIFO, False, False),  # isatty is True (terminal)
        (False, stat.S_IFREG, False, False),  # Regular file redirect
        (False, stat.S_IFCHR, False, False),  # Character device
        (False, 0, True, False),  # fileno raises UnsupportedOperation (e.g. StringIO)
    ],
)
def test_is_pipe(isatty_val, st_mode, fileno_raises, expected):
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = isatty_val
    if fileno_raises:
        mock_stdout.fileno.side_effect = io.UnsupportedOperation
    else:
        mock_stdout.fileno.return_value = 1

    mock_stat = MagicMock(st_mode=st_mode)
    with patch("sys.stdout", mock_stdout), patch("os.fstat", return_value=mock_stat):
        assert is_pipe() is expected


def test_is_pipe_exceptions():
    # If sys.stdout is None
    with patch("sys.stdout", None):
        assert is_pipe() is False

    # If sys.stdout doesn't have isatty
    mock_stdout = object()
    with patch("sys.stdout", mock_stdout):
        assert is_pipe() is False

    # If isatty raises an exception
    mock_raising = MagicMock()
    mock_raising.isatty.side_effect = RuntimeError("stream error")
    with patch("sys.stdout", mock_raising):
        assert is_pipe() is False

    # If fileno raises ValueError (e.g. closed stream)
    mock_closed = MagicMock()
    mock_closed.isatty.return_value = False
    mock_closed.fileno.side_effect = ValueError("I/O operation on closed file")
    with patch("sys.stdout", mock_closed):
        assert is_pipe() is False


def test_is_pipe_real_pipe():
    r, w = os.pipe()
    try:
        with open(w, "w") as pipe_out:
            with patch("sys.stdout", pipe_out):
                assert is_pipe() is True
    finally:
        os.close(r)


def test_is_pipe_real_file(tmp_path):
    f_path = tmp_path / "stdout.txt"
    with open(f_path, "w") as file_out:
        with patch("sys.stdout", file_out):
            assert is_pipe() is False


@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
@patch("cats.cli.is_pipe", return_value=True)
def test_auto_json_when_piped(
    mock_is_pipe, mock_carbon_get_data, mock_resolve_price_series, capsys
):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity", "gCO2eq/kWh", 100.0
    )
    mock_resolve_price_series.return_value = _wide_flat_series(
        "Day-ahead electricity price", "GBP/MWh", 150.0
    )

    # When piped, output should be JSON by default without --format=json
    assert main(["-d", "30", "--loc", "OX1"]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["location"] == "OX1"
    assert data["metric"] == "Carbon intensity"
    assert data["valueNow"]["value"] == pytest.approx(100.0)
    assert data["valueOptimal"]["value"] == pytest.approx(100.0)
    assert CATS_ASCII_BANNER_COLOUR.strip() not in out
    assert CATS_ASCII_BANNER_NO_COLOUR.strip() not in out


@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
@patch("cats.cli.is_pipe", return_value=True)
def test_format_text_overrides_pipe(
    mock_is_pipe, mock_carbon_get_data, mock_resolve_price_series, capsys
):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity", "gCO2eq/kWh", 100.0
    )
    mock_resolve_price_series.return_value = _wide_flat_series(
        "Day-ahead electricity price", "GBP/MWh", 150.0
    )

    # User can explicitly request text format even when piped
    assert main(["-d", "30", "--loc", "OX1", "--format", "text"]) == 0
    out = capsys.readouterr().out
    assert "Best job start time" in out
    assert "Price if job started now" in out


@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
@patch("cats.cli.is_pipe", return_value=False)
def test_format_json_in_terminal(
    mock_is_pipe, mock_carbon_get_data, mock_resolve_price_series, capsys
):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity", "gCO2eq/kWh", 100.0
    )
    mock_resolve_price_series.return_value = _wide_flat_series(
        "Day-ahead electricity price", "GBP/MWh", 150.0
    )

    # Explicit --format=json outputs JSON even when not piped
    assert main(["-d", "30", "--loc", "OX1", "--format", "json"]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["location"] == "OX1"
    assert data["metric"] == "Carbon intensity"


def test_format_invalid_choice():
    with pytest.raises(SystemExit):
        main(["-d", "30", "--loc", "OX1", "--format", "yaml"])


@pytest.mark.parametrize("flag", ["-V", "--version"])
def test_version_flag(flag, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main([flag])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    output = captured.out or captured.err
    assert f"cats {version}" in output


@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_no_color_environment_variable(
    mock_carbon_get_data, mock_resolve_price_series, monkeypatch, capsys
):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity", "gCO2eq/kWh", 100.0
    )
    mock_resolve_price_series.return_value = _wide_flat_series(
        "Day-ahead electricity price", "GBP/MWh", 150.0
    )

    # With NO_COLOR set to a non-empty value, no ANSI colour escape codes
    # should be emitted.
    monkeypatch.setenv("NO_COLOR", "1")
    assert main(["-d", "30", "--loc", "OX1"]) == 0
    out_no_color = capsys.readouterr().out
    assert "\33[" not in out_no_color

    # Per https://no-color.org, an empty NO_COLOR should NOT disable colour.
    monkeypatch.setenv("NO_COLOR", "")
    assert main(["-d", "30", "--loc", "OX1"]) == 0
    out_empty_env = capsys.readouterr().out
    assert "\33[" in out_empty_env

    # Without NO_COLOR and without --no-colour, colour is still used.
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert main(["-d", "30", "--loc", "OX1"]) == 0
    out_colored = capsys.readouterr().out
    assert "\33[" in out_colored


@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_forecast_only(mock_carbon_get_data, capsys):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity",
        "gCO2eq/kWh",
        100.0,
        starttime=datetime(2026, 2, 2, 10, 0, 0, 0),
    )
    # THe forecast-only flag print JSON output
    assert main(["--forecast-only"]) == 0
    out = capsys.readouterr().out
    result = json.loads(out)
    # We test a bunch of output values - but not all of them
    assert result["metric"] == "Carbon intensity"
    assert result["unit"] == "gCO2eq/kWh"
    assert result["values"][0]["value"] == 100.0
    assert result["values"][0]["datetime"] == "2026-02-02T10:00:00"
    assert result["values"][1]["value"] == 100.0
    assert result["values"][1]["datetime"] == "2026-02-02T10:30:00"
    assert result["values"][-1]["value"] == 100.0
    assert result["values"][-1]["datetime"] == "2026-02-04T11:30:00"


@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_reduction_in_output_by_default(
    mock_carbon_get_data, mock_resolve_price_series, capsys
):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity", "gCO2eq/kWh", 100.0
    )
    # No price data: the price report would otherwise add unrelated lines
    # (and require a network request) to the output under test.
    mock_resolve_price_series.return_value = None
    assert main(["-d", "30", "--loc", "OX1"]) == 0
    out = capsys.readouterr().out
    assert "Carbon intensity reduction" in out
    assert "0.00 gCO2eq/kWh" in out


@pytest.mark.parametrize("flag", ["-e", "--hide-reduction", "--exclude-savings"])
@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_hide_reduction_flag(
    mock_carbon_get_data, mock_resolve_price_series, flag, capsys
):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity", "gCO2eq/kWh", 100.0
    )
    mock_resolve_price_series.return_value = None
    assert main(["-d", "30", "--loc", "OX1", flag]) == 0
    out = capsys.readouterr().out
    assert "Carbon intensity reduction" not in out


@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_reduction_in_json_output_by_default(
    mock_carbon_get_data, mock_resolve_price_series, capsys
):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity", "gCO2eq/kWh", 100.0
    )
    mock_resolve_price_series.return_value = None
    assert main(["-d", "30", "--loc", "OX1", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "reduction" in data
    assert data["reduction"] == 0.0


@pytest.mark.parametrize("flag", ["-e", "--hide-reduction", "--exclude-savings"])
@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_hide_reduction_in_json_output(
    mock_carbon_get_data, mock_resolve_price_series, flag, capsys
):
    mock_carbon_get_data.return_value = _wide_flat_series(
        "Carbon intensity", "gCO2eq/kWh", 100.0
    )
    mock_resolve_price_series.return_value = None
    assert main(["-d", "30", "--loc", "OX1", "--format", "json", flag]) == 0
    data = json.loads(capsys.readouterr().out)
    # The key is always present so that the JSON schema does not depend on
    # the flag, but the value is hidden when the flag is given.
    assert "reduction" in data
    assert data["reduction"] is None


@patch("cats.cli.resolve_price_series")
@patch("cats.providers.GBCarbonIntensityProvider.get_data")
def test_reduction_non_zero_calculation_in_main(
    mock_carbon_get_data, mock_resolve_price_series, capsys
):
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    # First 6 steps (past through now) are 100.0, future steps drop to 40.0
    values = [
        PointEstimate(
            value=100.0 if i < 6 else 40.0, datetime=start + timedelta(minutes=30 * i)
        )
        for i in range(100)
    ]
    mock_carbon_get_data.return_value = Timeseries(
        "Carbon intensity", values, "gCO2eq/kWh"
    )
    mock_resolve_price_series.return_value = None
    assert main(["-d", "30", "--loc", "OX1"]) == 0
    out = capsys.readouterr().out
    assert "Carbon intensity reduction" in out
    assert "60.00 gCO2eq/kWh" in out


def test_help_documents_the_reduction_flags():
    # The flag is the user-facing contract for the new output line, so make
    # sure it stays discoverable from --help.
    help_text = parse_arguments().format_help()
    assert "--hide-reduction" in help_text
    assert "--exclude-savings" in help_text
    assert "reduction" in help_text
