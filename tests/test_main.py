# Tests main() function
import subprocess
from datetime import datetime, timedelta
from unittest.mock import patch

from cats import SCHEDULER_DATE_FORMAT, CATSOutput, main, schedule_at
from cats.CI_api_interface import API_interfaces, InvalidLocationError
from cats.forecast import CarbonIntensityAverageEstimate

API = API_interfaces["carbonintensity.org.uk"]

AT_OUTPUT = "%a %b %d %H:%M:%S %Y"
now_start = (datetime.now() + timedelta(minutes=1)).replace(second=0)
now_end = now_start + timedelta(minutes=5)

OUTPUT = CATSOutput(
    CarbonIntensityAverageEstimate(20, now_start, now_end),
    CarbonIntensityAverageEstimate(20, now_start, now_end),
    "OX1",
    "GBR",
)


def test_schedule_at_success(fp):
    fp.register_subprocess(["ls"], stdout=b"foobar.txt")
    fp.register_subprocess(
        [
            "at",
            "-t",
            OUTPUT.carbonIntensityOptimal.start.strftime(SCHEDULER_DATE_FORMAT["at"]),
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


def test_schedule_at_missing():
    assert (
        schedule_at(OUTPUT, ["ls"], at_command="at_imaginary")
        == "No at command found in PATH, please install one"
    )


def test_schedule_at_failure():
    assert schedule_at(OUTPUT, ["ls"], at_command="/usr/bin/false").startswith(
        "Scheduling with at failed with code 1, see output below:"
    )


def raiseLocationError():
    raise InvalidLocationError


@patch("cats.CI_api_query.get_CI_forecast")
def test_main_failures(get_CI_forecast):
    get_CI_forecast.return_value = {}
    get_CI_forecast.side_effect = raiseLocationError

    # CATS should fail when command is supplied, but no scheduler
    assert main(["-c", "ls", "-d", "5"]) == 1

    # Invalid location
    assert main(["-d", "5", "--loc", "oxford"]) == 1

    # Duration larger than API maximum
    assert main(["-d", "5000", "--loc", "OX1"]) == 1
