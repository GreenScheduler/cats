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
    wf = WindowedForecast(DATA, window_size, start=DATA[0].datetime)

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
    wf = WindowedForecast(DATA, window_size, start=DATA[0].datetime)
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
        # Data points separated by 30 minutes intervals
        duration = window_size * 30
        result = min(WindowedForecast(data, duration, start=data[0].datetime))

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


def test_average_intensity_now():
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

        window_size = 11
        # Data points separated by 30 minutes intervals
        duration = window_size * 30
        result = WindowedForecast(data, duration, start=data[0].datetime)[0]

        # Intensity point estimates over best runtime period
        v = [p.value for p in data[:window_size + 1]]
        expected = CarbonIntensityAverageEstimate(
            start=data[0].datetime,
            end=data[window_size].datetime,
            value=sum(
                [0.5 * (a + b) for a, b in zip(v[:-1], v[1:])]
            ) / window_size
        )
        assert (result == expected)


def test_average_intensity_with_offset():
    # Case where job start and end time are not colocated with data
    # carbon intensity data points. In this case cats interpolate the
    # intensity value at beginning and end of each potential job
    # duration window.
    CI_forecast = [
        CarbonIntensityPointEstimate(datetime(2023,1,1,8,30), value=26),
        CarbonIntensityPointEstimate(datetime(2023,1,1,9,0), value=40),
        CarbonIntensityPointEstimate(datetime(2023,1,1,9,30), value=50),
        CarbonIntensityPointEstimate(datetime(2023,1,1,10,0), value=60),
        CarbonIntensityPointEstimate(datetime(2023,1,1,10,30), value=25),
    ]
    duration = 70  # in minutes
    # First available data point is for 08:00 but the job
    # starts 15 minutes later.
    job_start = datetime.fromisoformat("2023-01-01T08:45")
    result = WindowedForecast(CI_forecast, duration, start=job_start)[1]

    expected = CarbonIntensityAverageEstimate(
        start=datetime(2023,1,1,9,15),
        end=datetime(2023,1,1,10,25),
        value=(
            0.5 * (45 + 50) * 15 +
            0.5 * (50 + 60) * 30 +
            0.5 * (60 + 30.83) * 25
        ) / duration
    )
    assert result.start == expected.start
    assert result.end == result.end
    # Allow for 1% relative tolerance between result and expected
    # value.  Difference is probably due to truncating the
    # second interpolated value above.
    assert math.isclose(result.value, expected.value, rel_tol=0.01)

def test_average_intensity_with_offset_long_job():
    # Case where job start and end time are not colocated with data
    # carbon intensity data points. In this case cats interpolate the
    # intensity value at beginning and end of each potential job
    # duration window.
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

        duration = 194  # in minutes
        # First available data point is for 12:30 but the job
        # starts 18 minutes later.
        job_start = datetime.fromisoformat("2023-05-04T12:48")
        result = WindowedForecast(data, duration, start=job_start)[2]

        # First and last element in v are interpolated intensity value.
        # e.g v[0] = 15 + 18min * (18 - 15) / 30min = 16.8
        v = [16.8, 18, 19, 17, 16, 11, 11, 11, 11]
        data_timestep = data[1].datetime - data[0].datetime # 30 minutes
        expected = CarbonIntensityAverageEstimate(
            start=job_start + 2 * data_timestep,
            end=job_start + 2 * data_timestep + timedelta(minutes=duration),
            value=(
                0.5 * (v[0] + v[1]) * 12 +
                sum([0.5 * (a + b) * 30 for a, b in zip(v[1:-2], v[2:-1])]) +
                0.5 * (v[7] + v[8]) * 2
            ) / duration
        )
        assert (result == expected)

def test_average_intensity_with_offset_short_job():
    # Case where job is short: start and end time fall between two
    # consecutive data points (first and second).
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

        duration = 6  # in minutes
        # First available data point is for 12:30 but the job
        # starts 6 minutes later.
        job_start = datetime.fromisoformat("2023-05-04T12:48")
        result = WindowedForecast(data, duration, start=job_start)[2]

        # Job starts at 12:48 and ends at 12:54. For each candidate
        # running window, both start and end times fall between two
        # consecutive data points (e.g. 13:30 and 14:00 for the third
        # window).
        #
        # First and second element in v are interpolated intensity
        # values.  e.g v[0] = 15 + 18min * (18 - 15) / 30min = 16.8
        # and v[1] = v[-1] = 15 + 24min * (18 - 15) / 30min = 17.4
        v = [16.8, 17.4]
        data_timestep = data[1].datetime - data[0].datetime
        expected = CarbonIntensityAverageEstimate(
            start=job_start + 2 * data_timestep,
            end=job_start + 2 * data_timestep + timedelta(minutes=duration),
            value=sum(
                [0.5 * (a + b) for a, b in zip(v[:-1], v[1:])]
            ) / (len(v) - 1)
        )
        assert (result == expected)
