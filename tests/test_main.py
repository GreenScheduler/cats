# Tests main() function
import subprocess
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from cats.cli import main, print_banner
from cats.constants import CATS_ASCII_BANNER_COLOUR, CATS_ASCII_BANNER_NO_COLOUR
from cats.exceptions import InvalidLocationError
from cats.forecast import AverageEstimate
from cats.output import CATSOutput
from cats.schedulers import (
    SCHEDULER_DATE_FORMAT,
    get_sbatch_job_state,
    reschedule_at_job,
    schedule_at,
    schedule_at_start,
    schedule_sbatch,
)

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
    assert schedule_sbatch(OUTPUT, ["./script.sh"]) == ("123456", None)


def test_schedule_sbatch_failure():
    job_id, error = schedule_sbatch(OUTPUT, ["./script.sh"])
    assert job_id is None
    assert error


def test_get_sbatch_job_state_from_queue():
    with patch(
        "cats.schedulers.subprocess.check_output", return_value="RUNNING\n"
    ) as check_output:
        assert get_sbatch_job_state("123456") == "RUNNING"
    assert check_output.call_count == 1


def test_get_sbatch_job_state_from_accounting():
    with patch(
        "cats.schedulers.subprocess.check_output",
        side_effect=["", "123456|COMPLETED\n"],
    ) as check_output:
        assert get_sbatch_job_state("123456") == "COMPLETED"
    assert check_output.call_count == 2


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
        assert schedule_sbatch(OUTPUT, ["./script.sh"]) == (None, err)


def test_schedule_at_success(fp):
    fp.register_subprocess(
        [
            "at",
            "-t",
            OUTPUT.valueOptimal.start.strftime(SCHEDULER_DATE_FORMAT["at"]),
        ],
        stdout=b"job 1 at Wed Sep 30 12:00:00 2026",
    )
    assert schedule_at(OUTPUT, ["ls"]) == ("1", None)
    # check that the job was correctly scheduled by checking the at queue (atq)
    fp.register_subprocess(
        ["atq"], stdout=f"1\t\t{now_start.strftime(AT_OUTPUT)}".encode("utf-8")
    )
    assert now_start.strftime(AT_OUTPUT) in subprocess.check_output(["atq"]).decode(
        "utf-8"
    )


def test_schedule_at_submits_command_script(monkeypatch):
    with patch(
        "cats.schedulers.subprocess.check_output",
        return_value="job 18 at Thu Oct  1 12:00:00 2026",
    ) as check_output, patch("cats.schedulers.subprocess.Popen") as popen:
        assert schedule_at_start(
            now_start, ["sleep", "120"], "/work"
        ) == ("18", None)

    assert check_output.call_args.kwargs["stderr"] == subprocess.STDOUT
    assert check_output.call_args.args[0][0] == "at"
    assert check_output.call_args.kwargs["input"] == "sleep 120\n"
    assert check_output.call_args.kwargs["cwd"] == "/work"
    popen.assert_not_called()


def test_reschedule_at_job_adds_replacement_before_removing_old(monkeypatch):
    operations = []
    start = now_start + timedelta(hours=1)

    monkeypatch.setattr(
        "cats.schedulers.schedule_at_start",
        lambda start_time, args, cwd=None: (
            operations.append(("add", start_time, args, cwd)) or "2",
            None,
        ),
    )
    monkeypatch.setattr(
        "cats.schedulers.remove_at_job",
        lambda job_id: operations.append(("remove", job_id)),
    )

    assert reschedule_at_job("1", start, ["sleep", "300"]) == ("2", None)
    assert operations == [
        ("add", start, ["sleep", "300"], None),
        ("remove", "1"),
    ]


@pytest.mark.parametrize(
    "exc,err",
    [
        (
            FileNotFoundError,
            (None, "No at command found in PATH, please install one"),
        ),
        (
            subprocess.CalledProcessError(1, "at"),
            (None, "Scheduling with at failed with code 1, see output below:\nNone"),
        ),
    ],
)
def test_schedule_at_side_effects(exc, err):
    with patch("subprocess.check_output", side_effect=exc):
        assert schedule_at(OUTPUT, ["ls"]) == err


def raiseLocationError(*args, **kwargs):  # pyright: ignore[reportUnusedParameter, reportUnknownParameterType]
    raise InvalidLocationError


@patch("cats.providers.UKCarbonIntensityProvider.get_data")
def test_main_failures(get_data):
    get_data.return_value = {}
    get_data.side_effect = raiseLocationError

    # CATS should fail when command is supplied, but no scheduler
    assert main(["-c", "ls", "-d", "5"]) == 1

    # Invalid location
    assert main(["-d", "5", "--loc", "oxford"]) == 1

    # Duration larger than API maximum
    assert main(["-d", "5000", "--loc", "OX1"]) == 1
