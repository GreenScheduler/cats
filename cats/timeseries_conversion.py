"""
Timeseries conversion
"""

import datetime
from .forecast import WindowedForecast


def csv_loader(filename):
    """
    Load csv file without dependencies

    Expected Contents:

    COL1: Timestamp
    COL2: Carbon Intensity
    """
    with open(filename, "r") as f:
        data = f.readlines()

    # Remove header
    data = data[1:]
    # Remove trailing whitespace and split by comma
    data = [x.strip().split(",") for x in data]
    # Convert timestamp to datetime
    data = [
        [datetime.datetime.strptime(x[0], "%Y-%m-%dT%H:%MZ"), float(x[3])] for x in data
    ]
    return data


def check_duration(size, data):
    # make sure size is not None
    if size is None:
        raise ValueError("Windowed method requires timespan to be provided")
    # make sure size is can be converted to integer
    try:
        size = int(size)
    except ValueError:
        raise ValueError("Windowed method requires timespan to be an integer or float")
    # make sure size is positive
    if size <= 0:
        raise ValueError("Windowed method requires timespan to be positive")
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
        rtn = min(data, key=lambda x: x[1])
        rtn = {
            "timestamp": rtn[0],
            "carbon_intensity": rtn[1],
            "est_total_carbon": rtn[1],
        }
        return rtn

    if method == "windowed":
        num_intervals = check_duration(duration, data)
        return min(WindowedForecast(data, num_intervals))


def cat_converter(filename, method="simple", duration=None):
    # Load CSV
    data = csv_loader(filename)
    # Get lowest carbon intensity
    lowest = get_lowest_carbon_intensity(data, method, duration=duration)
    # Return timestamp and carbon intensity
    return lowest
