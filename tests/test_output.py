from datetime import datetime

import pytest

from cats import CATSOutput
from cats.carbonFootprint import Estimates
from cats.forecast import CarbonIntensityAverageEstimate

now_start = datetime(2024, 3, 15, 16, 0, 0)  # 4pm - 5pm
now_end = datetime(2024, 3, 15, 17, 0, 0)

optimal_start = datetime(2024, 3, 16, 2, 0, 0)  # 2am - 3am
optimal_end = datetime(2024, 3, 16, 3, 0, 0)

OUTPUT = CATSOutput(
    CarbonIntensityAverageEstimate(50, now_start, now_end),
    CarbonIntensityAverageEstimate(20, optimal_start, optimal_end),
    "OX1",
    "GBR",
)

OUTPUT_WITH_EMISSION_ESTIMATE = CATSOutput(
    CarbonIntensityAverageEstimate(50, now_start, now_end),
    CarbonIntensityAverageEstimate(20, optimal_start, optimal_end),
    "OX1",
    "GBR",
    Estimates(19, 9, 10),
)


@pytest.mark.parametrize(
    "output,expected",
    [
        (
            OUTPUT,
            """Best job start time 2024-03-16 02:00:00
Carbon intensity if job started now       = 50.00 gCO2eq/kWh
Carbon intensity at optimal time          = 20.00 gCO2eq/kWh

Use --format=json to get this in machine readable format""",
        ),
        (
            OUTPUT_WITH_EMISSION_ESTIMATE,
            """Best job start time 2024-03-16 02:00:00
Carbon intensity if job started now       = 50.00 gCO2eq/kWh
Carbon intensity at optimal time          = 20.00 gCO2eq/kWh
Estimated emissions if job started now    = 19
Estimated emissions at optimal time       = 9 (- 10)

Use --format=json to get this in machine readable format""",
        ),
    ],
)
def test_string_repr(output, expected):
    assert str(output) == expected


@pytest.mark.parametrize(
    "output,expected",
    [
        (
            OUTPUT,
            """{"carbonIntensityNow": {"end": "2024-03-15T17:00:00", "start": "2024-03-15T16:00:00", "value": 50}, """
            """"carbonIntensityOptimal": {"end": "2024-03-16T03:00:00", "start": "2024-03-16T02:00:00", "value": 20}, """
            """"countryISO3": "GBR", "emmissionEstimate": null, "location": "OX1"}""",
        ),
        (
            OUTPUT_WITH_EMISSION_ESTIMATE,
            """{"carbonIntensityNow": {"end": "2024-03-15T17:00:00", "start": "2024-03-15T16:00:00", "value": 50}, """
            """"carbonIntensityOptimal": {"end": "2024-03-16T03:00:00", "start": "2024-03-16T02:00:00", "value": 20}, """
            """"countryISO3": "GBR", "emmissionEstimate": [19, 9, 10], "location": "OX1"}""",
        ),
    ],
)
def test_output_json(output, expected):
    assert output.to_json(sort_keys=2) == expected


@pytest.mark.parametrize(
    "output,expected",
    [
        (
            OUTPUT,
            """{"carbonIntensityNow": {"end": "202403151700", "start": "202403151600", "value": 50}, """
            """"carbonIntensityOptimal": {"end": "202403160300", "start": "202403160200", "value": 20}, """
            """"countryISO3": "GBR", "emmissionEstimate": null, "location": "OX1"}""",
        ),
        (
            OUTPUT_WITH_EMISSION_ESTIMATE,
            """{"carbonIntensityNow": {"end": "202403151700", "start": "202403151600", "value": 50}, """
            """"carbonIntensityOptimal": {"end": "202403160300", "start": "202403160200", "value": 20}, """
            """"countryISO3": "GBR", "emmissionEstimate": [19, 9, 10], "location": "OX1"}""",
        ),
    ],
)
def test_output_json_with_dateformat(output, expected):
    # use date format expected by at(1)
    assert output.to_json(dateformat="%Y%m%d%H%M", sort_keys=2) == expected
