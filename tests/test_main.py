# Tests main() function
import subprocess
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from cats import CATSOutput, main, schedule_at
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


@pytest.mark.skip
def test_schedule_at():
    schedule_at(OUTPUT, ["ls"])
    assert now_start.strftime(AT_OUTPUT) in subprocess.check_output(["atq"]).decode(
        "utf-8"
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
