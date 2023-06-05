import csv
from datetime import datetime, timedelta
import math
from pathlib import Path
from numpy.testing import assert_allclose
from cats.forecast import (
    CarbonIntensityPointEstimate, WindowedForecast,
    CarbonIntensityAverageEstimate,
)

d = datetime(year=2023, month=1, day=1)
NDATA = 200
step = math.pi / NDATA
DATA = [
    CarbonIntensityPointEstimate(
        datetime=d + timedelta(minutes=i),
        value=-1. *  math.sin(i * step),
    )
    for i in range(NDATA)
]

TEST_DATA = Path(__file__).parent / "carbon_intensity_24h.csv"


def test_has_right_length():
    window_size = 160  # In number of time intervals
    wf = WindowedForecast(DATA, window_size)

    # Expecting (200 - 160 - 1) (39) data points in the time
    # integrated timeseries.
    assert len(wf) == NDATA - window_size - 1


def test_values():
    # Check that we're able to estimate a integral with reasonable
    # accuracy.  In the following we compute
    # \int_{t}^{t+T} - sin(t) dt which is equal to
    # cos(t + T) - cos(t).  Note that we are careful to have
    # a step size `step` small compared the the integration window

    window_size = 160
    wf = WindowedForecast(DATA, window_size)
    expected = [

        math.cos((i + window_size) * step) - math.cos(i * step)
        for i in range(len(DATA) - window_size - 1)
    ]
    # average
    expected = [e / (window_size * step) for e in expected]

    assert_allclose(
        actual=[p.value for p in wf],
        desired=expected,
        rtol=0.01
    )


def test_minimise_average():
    with open(TEST_DATA, "r") as f:
        csvfile = csv.reader(f, delimiter=",")
        next(csvfile)  # Skip header line
        data = [
            CarbonIntensityPointEstimate(
                datetime=datetime.fromisoformat(datestr[:-1]),
                value=float(intensity_value),
            )
            for datestr, _, _, intensity_value in csvfile
        ]

        window_size = 6
        result = min(WindowedForecast(data, window_size))

        # Intensity point estimates over best runtime period
        v = [10, 8, 7, 7, 5, 8, 8]
        expected = CarbonIntensityAverageEstimate(
            start=datetime.fromisoformat("2023-05-05T12:00"),
            end=datetime.fromisoformat("2023-05-05T15:00"),
            value=sum(
                [0.5 * (a + b) for a, b in zip(v[:-1], v[1:])]
            ) / window_size
        )
        assert (result == expected)
