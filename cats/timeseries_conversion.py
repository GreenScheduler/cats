"""
Timeseries conversion
"""

from .forecast import WindowedForecast


def check_duration(size, data):
    # make sure size is not greater than data size
    if size > len(data):
        raise ValueError(
            "Windowed method timespan cannot be greater than the cached timespan"
        )

    # get length of interval between timestamps
    interval = (data[1][0] - data[0][0]).total_seconds() / 60
    # count number of intervals in size
    num_intervals = int((size / interval) + 0.5)  # round to nearest integer (UP)

    return num_intervals


def get_lowest_carbon_intensity(data, method="simple", duration=None):
    """
    Get lowest carbon intensity in data depending on user method
    return dict of timestamp and carbon intensity

    duration is in minutes
    """
    METHODS = ["simple", "windowed"]
    if method not in METHODS:
        raise ValueError(f"Invalid Carbon Intensity Method. Must be one of {METHODS}")

    if method == "simple":
        #  Return element with smallest 2nd value
        #  if multiple elements have the same value, return the first
        return min(data)

    if method == "windowed":
        num_intervals = check_duration(duration, data)
        return min(WindowedForecast(data, num_intervals))
