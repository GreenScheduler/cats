# from datetime import datetime, timedelta
# import math
# from numpy.testing import assert_allclose
# from cats.forecast import WindowedForecast
#
# d = datetime(year=2023, month=1, day=1)
# NDATA = 200
# step = math.pi / NDATA
# DATA = [
#     (d + timedelta(minutes=i), - math.sin(i * step))
#     for i in range(NDATA)
# ]

# TODO temporarily commented out while issue #42 is being sorted
#
# def test_has_right_length():
#     window_size = 160  # In number of time intervals
#     wf = WindowedForecast(DATA, window_size)
#
#     # Expecting (200 - 160 - 1) (39) data points in the time
#     # integrated timeseries.
#     assert len(wf) == NDATA - window_size - 1
#
#
# def test_values():
#     # Check that we're able to estimate a integral with reasonable
#     # accuracy.  In the following we compute
#     # \int_{t}^{t+T} - sin(t) dt which is equal to
#     # cos(t + T) - cos(t).  Note that we are careful to have
#     # a step size `step` small compared the the integration window
#
#     window_size = 160
#     wf = WindowedForecast(DATA, window_size)
#     expected = [
#
#         math.cos((i + window_size) * step) - math.cos(i * step)
#         for i in range(len(DATA) - window_size - 1)
#     ]
#     # average
#     expected = [e / (window_size * step) for e in expected]
#
#     assert_allclose(
#         actual=[p.value for p in wf],
#         desired=expected,
#         rtol=0.01
#     )

from cats.optimise_starttime import windowed_forecast
from cats.CI_api_interface import CarbonIntensityEstimate
from datetime import datetime
import math

CI_forecast = [
CarbonIntensityEstimate(start=datetime(2023,1,1,8,30), end=datetime(2023,1,1,9,0),value=26),
    CarbonIntensityEstimate(start=datetime(2023,1,1,9,0), end=datetime(2023,1,1,9,30),value=40),
    CarbonIntensityEstimate(start=datetime(2023,1,1,9,30), end=datetime(2023,1,1,10,0),value=50),
    CarbonIntensityEstimate(start=datetime(2023,1,1,10,0), end=datetime(2023,1,1,10,30),value=60),
    CarbonIntensityEstimate(start=datetime(2023,1,1,10,30), end=datetime(2023,1,1,11,0),value=25),
]

wf = windowed_forecast(CI_forecast = CI_forecast, method=None)
foo = wf._calculate_averageCI_over_runtime(datetime(2023,1,1,9,15), datetime(2023,1,1,10,25), 'sum')
expected_result_sum = (40*15+50*30+60*25)/70
assert math.isclose(foo, expected_result_sum), "Sum integration returned the wrong result."

bar = wf._calculate_averageCI_over_runtime(datetime(2023,1,1,9,15), datetime(2023,1,1,10,25), 'trapezoidal')
start_new = 45
end_new = 60 + (25-60)/30*25
expected_result_trapezoidal = ((start_new+50)*15/2 + (50+60)*30/2 + (60+end_new)*25/2)/70
assert math.isclose(bar, expected_result_trapezoidal), "Trapezoidal integration returned the wrong result."
