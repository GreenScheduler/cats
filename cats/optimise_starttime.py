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
    # NB: datetime.now().astimezone() gives us a timezone aware datetime object
    # in the current system timezone. The resulting start time from the forecast
    # works in terms of this timezone (even if the data is in another timezone)
    # so we end up with something in system time if data is in utc and system
    # time is in bst (for example)
    wf = WindowedForecast(data, duration, start=datetime.now().astimezone())
    return wf[0], min(wf)
