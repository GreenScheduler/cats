from math import ceil
from .forecast import WindowedForecast

def get_starttime(data, method="simple", duration=None):
    """
    Get lowest carbon intensity in data depending on user method
    return dict of timestamp and carbon intensity

    duration is in minutes
    """
    # make sure size is not greater than data size (but needs to adjust to different intervals, comparison to len(data) incorrect here TODO)
    # if duration > len(data):
    #     raise ValueError(
    #         "Windowed method timespan cannot be greater than the cached timespan"
    #     )

    METHODS = ["simple", "windowed"]
    if method not in METHODS:
        raise ValueError(f"Invalid Carbon Intensity Method. Must be one of {METHODS}")

    if method == "simple":
        #  Return element with smallest 2nd value
        #  if multiple elements have the same value, return the first
        return min(data)

    if method == "windowed":
        # get length of interval between timestamps
        interval = (
            data[1].datetime - data[0].datetime
        ).total_seconds() / 60
        wf = WindowedForecast(
            data=data,
            window_size=ceil(duration / interval)
        )
        return wf[0], min(wf)
