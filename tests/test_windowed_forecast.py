from datetime import datetime, timedelta
import math
from numpy.testing import assert_allclose
from cats.forecast import WindowedForecast

d = datetime(year=2023, month=1, day=1)
NDATA = 200
step = math.pi / NDATA
DATA = [
    (d + timedelta(minutes=i), - math.sin(i * step))
    for i in range(NDATA)
]


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
