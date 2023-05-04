'''
Timeseries conversion
'''

import datetime


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
        [datetime.datetime.strptime(x[0], "%Y-%m-%dT%H:%M:%S"), float(x[1])]
        for x in data
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
    return size


def get_lowest_carbon_intensity(data, method="simple", size=None):
    """
    Get lowest carbon intensity in data depending on user method
    return dict of timestamp and carbon intensity

    lenght is in minutes
    """
    if method not in ["simple", "windowed"]:
        raise ValueError("Invalid Carbon Intensity Method")

    if method == "simple":
        #  Return element with smallest 2nd value
        #  if multiple elements have the same value, return the first
        rtn = min(data, key=lambda x: x[1])
        rtn = {"timestamp": rtn[0], "carbon_intensity": rtn[1]}

    if method == "windowed":
        size = check_duration(size, data)
        #  calculate the windowed carbon intensity
        windowed_data = [[], []]
        for i in range(len(data) - size):
            windowed_data[0].append(data[i][0])
            windowed_data[1].append(sum([x[1] for x in data[i : i + size]]) / size)
        #  Return element with smallest 2nd value
        #  if multiple elements have the same value, return the first
        rtn = min(windowed_data, key=lambda x: x[1])
        rtn = {"timestamp": rtn[0], "carbon_intensity": rtn[1]}

    return rtn


def cat_converter(filename, method='simple'):
    # Load CSV
    data = csv_loader(filename)
    # Get lowest carbon intensity
    lowest = get_lowest_carbon_intensity(data, method)
    # Return timestamp and carbon intensity
    return lowest
