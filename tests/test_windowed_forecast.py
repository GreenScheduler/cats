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
    window = 160
    wf = WindowedForecast(DATA, window)

    assert len(wf) == NDATA - window

def test_values():
    # Check that we're able to estimate a integral with reasonable
    # accuracy.  In the following we compute
    # \int_{t}^{t+T} - sin(t) dt which is equal to
    # cos(t + T) - cos(t).  Note that we are careful to have
    # a step size `step` small compared the the integration window

    window = 160
    wf = WindowedForecast(DATA, window)
    expected = [

        math.cos((i + window) * step) - math.cos(i * step)
        for i in range(len(DATA) - window)
    ]
    # average
    expected = [e / (window * step) for e in expected]

    assert_allclose(
        actual=[p.value for p in wf],
        desired=expected,
        rtol=0.01
    )
