from datetime import datetime, timedelta

from cats.forecast import (
    CarbonIntensityAverageEstimate,
    CarbonIntensityPointEstimate,
    WindowedForecast,
)

def test_127_bug_report():
    """
    Regression test for the bug report in issue 127
    As far as I can tell, the best option for the provided data is to 
    start at once on a decreasing trend. However, our results do
    differ to those reported in the issue. I think because of the 
    fixes that went in before version 1.1.
    """
    # Reported input data
    d = datetime(year=2025, month=3, day=10, hour=15)
    data = [
        CarbonIntensityPointEstimate(
        datetime=d + timedelta(minutes=idt*30),
        value=v,
    )
    for idt, v in zip(range(19),
                      [14, 20, 20, 22, 13, 40, 49, 76, 91, 86, 
                       61, 28, 24, 26, 25, 27, 27, 26, 23])
    ]

    # Reported job data
    duration = 30  # in minutes
    job_start = datetime.fromisoformat("2025-03-10T16:24")

    result = WindowedForecast(data, duration, start=job_start)

    now_avg, best_avg = result[0], min(result)

    interp1 = 20 + (2.0/30)*24 # interpolate onto earlest start time (now)
    interp2 = 13 + (9.0/30)*6 # interpolate onto end time
    expected_best = CarbonIntensityAverageEstimate(
        start=datetime(2025, 3, 10, 16, 24),
        end=datetime(2025, 3, 10, 16, 54),
        value=(0.5*(interp1 + 22)*6 + 0.5*(22 + interp2)*24)/30 , # integral
        start_value= interp1, 
        end_value= interp2 
    )

    assert now_avg == expected_best
    assert best_avg == expected_best