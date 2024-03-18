import datetime

from numpy.testing import assert_allclose

from cats.carbonFootprint import Estimates, get_footprint_reduction_estimate

JOBINFO = [(1, 2.0), (2, 3.0), (8, 1.0)]


def test_get_footprint_reduction_estimate():
    expected = Estimates(now=3.2, best=2.4, savings=0.8)
    est = get_footprint_reduction_estimate(
        PUE=1.0,
        jobinfo=JOBINFO,
        runtime=datetime.timedelta(minutes=60),
        average_best_ci=150,  # gCO2/kWh
        average_now_ci=200,  # gCO2/kWh
    )
    assert_allclose(expected, est)
