from datetime import datetime
from .forecast import WindowedForecast


def get_avg_estimates(data, duration=None):
    """
    Get lowest carbon intensity in data depending on user method
    return dict of timestamp and carbon intensity

    duration is in minutes
    """
    # make sure size is not greater than data size (but needs to
    # adjust to different intervals, comparison to len(data) incorrect
    # here TODO)
    # if duration > len(data):
    #     raise ValueError(
    #         "Windowed method timespan cannot be greater than the cached timespan"
    #     )
    wf = WindowedForecast(data, duration, start=datetime.now())
    return wf[0], min(wf)
