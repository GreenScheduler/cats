import json
from datetime import datetime

import pytest

from cats.carbonFootprint import Estimates
from cats.forecast import AverageEstimate
from cats.output import CATSOutput

now_start = datetime(2024, 3, 15, 16, 0, 0)  # 4pm - 5pm
now_end = datetime(2024, 3, 15, 17, 0, 0)

optimal_start = datetime(2024, 3, 16, 2, 0, 0)  # 2am - 3am
optimal_end = datetime(2024, 3, 16, 3, 0, 0)

OUTPUT = CATSOutput(
    "Carbon intensity",
    AverageEstimate(50, now_start, now_end, 0.0, 0.0),
    AverageEstimate(20, optimal_start, optimal_end, 0.0, 0.0),
    "OX1",
    "GBR",
    "gCO2eq/kWh",
)

OUTPUT_WITH_EMISSION_ESTIMATE = CATSOutput(
    "Carbon intensity",
    AverageEstimate(50, now_start, now_end, 0.0, 0.0),
    AverageEstimate(20, optimal_start, optimal_end, 0.0, 0.0),
    "OX1",
    "GBR",
    "gCO2eq/kWh",
    Estimates(19, 9, 10),
)

OUTPUT_WITH_PRICE_ESTIMATE = CATSOutput(
    "Carbon intensity",
    AverageEstimate(50, now_start, now_end, 0.0, 0.0),
    AverageEstimate(20, optimal_start, optimal_end, 0.0, 0.0),
    "OX1",
    "GBR",
    "gCO2eq/kWh",
    priceEstimate=Estimates(150.0, 100.0, 50.0),
    priceUnit="GBP/MWh",
)

OUTPUT_WITH_PRICE_INCREASE = CATSOutput(
    "Carbon intensity",
    AverageEstimate(50, now_start, now_end, 0.0, 0.0),
    AverageEstimate(20, optimal_start, optimal_end, 0.0, 0.0),
    "OX1",
    "GBR",
    "gCO2eq/kWh",
    # Optimising for carbon picked a window that is more expensive than now:
    # savings = now - best = 143.05 - 214.29 = -71.24 (a price *increase*).
    priceEstimate=Estimates(143.05, 214.29, -71.24),
    priceUnit="GBP/MWh",
)

# A longer metric label (e.g. wattnet.eu's environmental_score) combined with
# a price report: the "=" column must still line up, even though the label
# lengths of "Environmental score if job started now" and "Price if job
# started now" differ substantially.
OUTPUT_WITH_LONG_METRIC_AND_PRICE = CATSOutput(
    "Environmental score",
    AverageEstimate(19.59, now_start, now_end, 0.0, 0.0),
    AverageEstimate(18.75, optimal_start, optimal_end, 0.0, 0.0),
    "DE",
    "DEU",
    "-score",
    priceEstimate=Estimates(17.49, 158.37, 17.49 - 158.37),
    priceUnit="EUR/MWh",
)

# The reduction is reported by default; this output explicitly hides it.
OUTPUT_WITHOUT_REDUCTION = CATSOutput(
    "Carbon intensity",
    AverageEstimate(50, now_start, now_end, 0.0, 0.0),
    AverageEstimate(20, optimal_start, optimal_end, 0.0, 0.0),
    "OX1",
    "GBR",
    "gCO2eq/kWh",
    show_reduction=False,
)


@pytest.mark.parametrize(
    "output,expected",
    [
        (
            OUTPUT,
            """
Best job start time                 = 2024-03-16 02:00:00
Carbon intensity if job started now = 50.00 gCO2eq/kWh
Carbon intensity at optimal time    = 20.00 gCO2eq/kWh
Carbon intensity reduction          = 30.00 gCO2eq/kWh""",
        ),
        (
            OUTPUT_WITH_EMISSION_ESTIMATE,
            """
Best job start time                    = 2024-03-16 02:00:00
Carbon intensity if job started now    = 50.00 gCO2eq/kWh
Carbon intensity at optimal time       = 20.00 gCO2eq/kWh
Carbon intensity reduction             = 30.00 gCO2eq/kWh
Estimated emissions if job started now = 19
Estimated emissions at optimal time    = 9 (- 10)""",
        ),
        (
            OUTPUT_WITH_PRICE_ESTIMATE,
            """
Best job start time                 = 2024-03-16 02:00:00
Carbon intensity if job started now = 50.00 gCO2eq/kWh
Carbon intensity at optimal time    = 20.00 gCO2eq/kWh
Carbon intensity reduction          = 30.00 gCO2eq/kWh
Price if job started now            = 150.00 GBP/MWh
Price at chosen start time          = 100.00 GBP/MWh (- 50.00)""",
        ),
        (
            OUTPUT_WITH_PRICE_INCREASE,
            """
Best job start time                 = 2024-03-16 02:00:00
Carbon intensity if job started now = 50.00 gCO2eq/kWh
Carbon intensity at optimal time    = 20.00 gCO2eq/kWh
Carbon intensity reduction          = 30.00 gCO2eq/kWh
Price if job started now            = 143.05 GBP/MWh
Price at chosen start time          = 214.29 GBP/MWh (+ 71.24)""",
        ),
        (
            OUTPUT_WITH_LONG_METRIC_AND_PRICE,
            """
Best job start time                    = 2024-03-16 02:00:00
Environmental score if job started now = 19.59 -score
Environmental score at optimal time    = 18.75 -score
Environmental score reduction          = 0.84 -score
Price if job started now               = 17.49 EUR/MWh
Price at chosen start time             = 158.37 EUR/MWh (+ 140.88)""",
        ),
        (
            OUTPUT_WITHOUT_REDUCTION,
            """
Best job start time                 = 2024-03-16 02:00:00
Carbon intensity if job started now = 50.00 gCO2eq/kWh
Carbon intensity at optimal time    = 20.00 gCO2eq/kWh""",
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
            """{"colour": false, "countryISO3": "GBR", "emmissionEstimate": null, "location": "OX1", "metric": "Carbon intensity", """
            """"priceEstimate": null, "priceUnit": null, "reduction": 30.0, "unit": "gCO2eq/kWh", """
            """"valueNow": {"end": "2024-03-15T17:00:00", "end_value": 0.0, "start": "2024-03-15T16:00:00", "start_value": 0.0, "value": 50}, """
            """"valueOptimal": {"end": "2024-03-16T03:00:00", "end_value": 0.0, "start": "2024-03-16T02:00:00", "start_value": 0.0, "value": 20}}""",
        ),
        (
            OUTPUT_WITH_EMISSION_ESTIMATE,
            """{"colour": false, "countryISO3": "GBR", "emmissionEstimate": [19, 9, 10], "location": "OX1", "metric": "Carbon intensity", """
            """"priceEstimate": null, "priceUnit": null, "reduction": 30.0, "unit": "gCO2eq/kWh", """
            """"valueNow": {"end": "2024-03-15T17:00:00", "end_value": 0.0, "start": "2024-03-15T16:00:00", "start_value": 0.0, "value": 50}, """
            """"valueOptimal": {"end": "2024-03-16T03:00:00", "end_value": 0.0, "start": "2024-03-16T02:00:00", "start_value": 0.0, "value": 20}}""",
        ),
        (
            OUTPUT_WITHOUT_REDUCTION,
            """{"colour": false, "countryISO3": "GBR", "emmissionEstimate": null, "location": "OX1", "metric": "Carbon intensity", """
            """"priceEstimate": null, "priceUnit": null, "reduction": null, "unit": "gCO2eq/kWh", """
            """"valueNow": {"end": "2024-03-15T17:00:00", "end_value": 0.0, "start": "2024-03-15T16:00:00", "start_value": 0.0, "value": 50}, """
            """"valueOptimal": {"end": "2024-03-16T03:00:00", "end_value": 0.0, "start": "2024-03-16T02:00:00", "start_value": 0.0, "value": 20}}""",
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
            """{"colour": false, "countryISO3": "GBR", "emmissionEstimate": null, "location": "OX1", "metric": "Carbon intensity", """
            """"priceEstimate": null, "priceUnit": null, "reduction": 30.0, "unit": "gCO2eq/kWh", """
            """"valueNow": {"end": "202403151700", "end_value": 0.0, "start": "202403151600", "start_value": 0.0, "value": 50}, """
            """"valueOptimal": {"end": "202403160300", "end_value": 0.0, "start": "202403160200", "start_value": 0.0, "value": 20}}""",
        ),
        (
            OUTPUT_WITH_EMISSION_ESTIMATE,
            """{"colour": false, "countryISO3": "GBR", "emmissionEstimate": [19, 9, 10], "location": "OX1", "metric": "Carbon intensity", """
            """"priceEstimate": null, "priceUnit": null, "reduction": 30.0, "unit": "gCO2eq/kWh", """
            """"valueNow": {"end": "202403151700", "end_value": 0.0, "start": "202403151600", "start_value": 0.0, "value": 50}, """
            """"valueOptimal": {"end": "202403160300", "end_value": 0.0, "start": "202403160200", "start_value": 0.0, "value": 20}}""",
        ),
        (
            OUTPUT_WITHOUT_REDUCTION,
            """{"colour": false, "countryISO3": "GBR", "emmissionEstimate": null, "location": "OX1", "metric": "Carbon intensity", """
            """"priceEstimate": null, "priceUnit": null, "reduction": null, "unit": "gCO2eq/kWh", """
            """"valueNow": {"end": "202403151700", "end_value": 0.0, "start": "202403151600", "start_value": 0.0, "value": 50}, """
            """"valueOptimal": {"end": "202403160300", "end_value": 0.0, "start": "202403160200", "start_value": 0.0, "value": 20}}""",
        ),
    ],
)
def test_output_json_with_dateformat(output, expected):
    # use date format expected by at(1)
    assert output.to_json(dateformat="%Y%m%d%H%M", sort_keys=2) == expected


def test_reduction_properties():
    out = CATSOutput(
        "Carbon intensity",
        AverageEstimate(141.53, now_start, now_end, 0.0, 0.0),
        AverageEstimate(120.40, optimal_start, optimal_end, 0.0, 0.0),
        "RG6",
        "GBR",
        "gCO2eq/kWh",
    )
    assert out.reduction == 21.13
    assert out.savings == 21.13


def test_reduction_is_always_a_float():
    # The values of the estimates may be ints (as in the fixtures above), in
    # which case a naive difference would be an int too and the JSON output
    # would change type depending on the input data.
    out = CATSOutput(
        "Carbon intensity",
        AverageEstimate(50, now_start, now_end, 0.0, 0.0),
        AverageEstimate(20, optimal_start, optimal_end, 0.0, 0.0),
        "OX1",
        "GBR",
        "gCO2eq/kWh",
    )
    assert isinstance(out.reduction, float)
    assert isinstance(json.loads(out.to_json())["reduction"], float)


def _reported_figures(output):
    """The numeric figures a reader sees in the text output, by line label."""
    figures = {}
    for line in str(output).splitlines():
        label, sep, value = line.partition("=")
        if not sep:
            continue
        try:
            figures[label.strip()] = float(value.strip().split()[0])
        except ValueError:
            # Not a numeric figure (e.g. the start time)
            continue
    return figures


def test_reduction_line_agrees_with_the_reported_figures():
    # The reduction is only useful if it is the difference between the two
    # figures reported above it.  Like the price savings, it is computed from
    # the unrounded values, so the difference of the printed figures can be
    # up to 0.01 out in the last decimal place.
    out = CATSOutput(
        "Carbon intensity",
        AverageEstimate(141.53, now_start, now_end, 0.0, 0.0),
        AverageEstimate(120.40, optimal_start, optimal_end, 0.0, 0.0),
        "RG6",
        "GBR",
        "gCO2eq/kWh",
    )
    figures = _reported_figures(out)
    now = figures["Carbon intensity if job started now"]
    optimal = figures["Carbon intensity at optimal time"]
    reduction = figures["Carbon intensity reduction"]
    assert reduction == pytest.approx(now - optimal, abs=0.01)
    # The JSON output has to agree with the text output
    assert json.loads(out.to_json())["reduction"] == pytest.approx(reduction, abs=0.01)


def test_string_repr_reduction_colour():
    out = CATSOutput(
        "Carbon intensity",
        AverageEstimate(50, now_start, now_end, 0.0, 0.0),
        AverageEstimate(20, optimal_start, optimal_end, 0.0, 0.0),
        "OX1",
        "GBR",
        "gCO2eq/kWh",
        colour=True,
    )
    s = str(out)
    assert "\33[32m30.00 gCO2eq/kWh\33[0m" in s


def test_string_repr_negative_reduction_colour():
    out = CATSOutput(
        "Carbon intensity",
        AverageEstimate(20, now_start, now_end, 0.0, 0.0),
        AverageEstimate(50, optimal_start, optimal_end, 0.0, 0.0),
        "OX1",
        "GBR",
        "gCO2eq/kWh",
        colour=True,
    )
    s = str(out)
    assert "\33[31m-30.00 gCO2eq/kWh\33[0m" in s


def test_reduction_negative_zero_normalization():
    out = CATSOutput(
        "Carbon intensity",
        AverageEstimate(10.001, now_start, now_end, 0.0, 0.0),
        AverageEstimate(10.004, optimal_start, optimal_end, 0.0, 0.0),
        "OX1",
        "GBR",
        "gCO2eq/kWh",
        colour=True,
    )
    assert out.reduction == 0.0
    assert not str(out.reduction).startswith("-")
    assert "\33[32m0.00 gCO2eq/kWh\33[0m" in str(out)
    data = json.loads(out.to_json())
    assert data["reduction"] == 0.0
