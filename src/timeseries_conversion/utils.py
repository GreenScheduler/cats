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
    data = [x.strip().split(',') for x in data]
    # timestamp, carbon intensity
    data = [[x[0], float(x[1])] for x in data]
    return data
