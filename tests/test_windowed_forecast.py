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

def test_windowed_forecast():
    runtime = 160
    wf = WindowedForecast(DATA, runtime)

    assert len(wf) == NDATA - runtime

    expected = [
        math.cos((i + runtime) * step) - math.cos(i * step)
        for i in range(len(DATA) - runtime)
    ]
    # average
    expected = [e / (runtime * step) for e in expected]

    assert_allclose(
        actual=[p[1] for p in wf],
        desired=expected,
        rtol=0.01
    )
