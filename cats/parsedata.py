import bisect
from datetime import datetime, timedelta

from .forecast import CarbonIntensityPointEstimate


def avg_carbon_intensity(data: list[CarbonIntensityPointEstimate],
                         start: datetime, runtime: timedelta):
    """Returns the averaged carbon intensity for a job given its start
    time and runtime.
    """
    datetimes = [point.datetime for point in data]
    intensities = [point.value for point in data]

    # lo is the index of the data point coming just before (or equal
    # to) the start time
    lo = bisect.bisect(datetimes, start) - 1
    # hi is the index of the data point coming just after (or equal
    # to) the expected finish time
    hi = bisect.bisect(datetimes, start + runtime)

    return sum(intensities[lo : hi + 1]) / (hi - lo + 1)
