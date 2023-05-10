import requests_cache
from datetime import datetime, timezone
from .parsedata import writecsv


def get_tuple(postcode) -> list[tuple[str, int]]:
    """gets carbon intensity API data for the next 48 hours from carbonintensity.org.uk
    param postcode: the UK post code (just the first section) of the location, e.g. M15
    returns: a set of tuples with start time and carbon intensity
    """

    # just get the first part of the postcode
    postcode = postcode.split()[0]
    
    # get the time (as a datetime object) for the top of
    # the current hour or half hour in UTZ
    dt = datetime.now(timezone.utc)
    if dt.minute > 30:
        dt = dt.replace(minute=31, second=0, microsecond=0)
    else:
        dt = dt.replace(minute=1, second=0, microsecond=0)
    timestamp = dt.strftime("%Y-%m-%dT%H:%MZ")

    # Setup a session for the HTTP cache
    session = requests_cache.CachedSession('cats_cache', use_temp=True)
    # get the carbon intensity api data
    r = session.get(
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
        response.append((timefrom, intensity))

    return response


if __name__ == "__main__":
    # test example using Manchester as a location
    data_tuples = get_tuple("M15")
    writecsv(data_tuples)
