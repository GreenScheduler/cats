import utils as tsutils


def cat_converter(filename, method='simple'):
    # Load CSV
    data = tsutils.csv_loader(filename)
    # Get lowest carbon intensity
    lowest = tsutils.get_lowest_carbon_intensity(data, method)

