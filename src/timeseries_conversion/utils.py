"""
Utils module timeseries conversion
"""


def csv_loader(filename):
    """
    Load csv file without dependencies

    Expected Contents:

    COL1: Timestamp
    COL2: Carbon Intensity
    """
    with open(filename, 'r') as f:
        data = f.readlines()

    # Remove header
    data = data[1:]
    # Remove trailing whitespace and split by comma
    data = [x.strip().split(',') for x in data]
    # timestamp, carbon intensity
    data = [[x[0], float(x[1])] for x in data]
    return data


def get_lowest_carbon_intensity(data, method='simple'):
    """
    Get lowest carbon intensity in data depending on user method
    return dict of timestamp and carbon intensity
    """
    if method not in ['simple', 'windowed']:
        raise ValueError('Invalid Carbon Intensity Method')

    if method == 'simple':
        #  Return element with smallest 2nd value
        rtn = min(data, key=lambda x: x[1])
        rtn = {'timestamp': rtn[0], 'carbon_intensity': rtn[1]}

    return rtn
