import requests
from datetime import datetime
import parsedata


def get_tuple(postcode, duration) -> list[tuple[str, int]]:
    """gets carbon intensity API data for the next 48 hours from carbonintensity.org.uk
    param postcode: the UK post code (just the first section) of the location, e.g. M15
    returns: a set of tuples with start time and carbon intensity
    """

    # get the carbon intensity api data
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
    r = requests.get(
        "https://api.carbonintensity.org.uk/regional/intensity/"
        + timestamp
        + "/fw48h/postcode/"
        + postcode
    )

    data = r.json()

    # convert into a tuple
    response = []
    for d in data["data"]["data"]:
        timefrom = d["from"]
        intensity = d["intensity"]["forecast"]
        response.append((timefrom, intensity),duration = duration)

    return response


if __name__ == "__main__":
    # test example using Manchester as a location
    data_tuples = get_tuple("M15")
    parsedata.writecsv(data_tuples)
