import requests_cache
from datetime import datetime, timezone
from .parsedata import writecsv


def get_tuple(postcode) -> list[tuple[str, int]]:
    """
    get carbon intensity from carbonintensity.org.uk

    Given the postcode and current time, return a set of predictions of the
    future carbon intensity. This wraps the API from carbonintensity.org.uk
    and is set up to cache data from call to call even accross different
    processes within the same half hour window. The returned prediction data
    is in half hour blocks starting from the half hour containing the current
    time and extending for 48 hours into the future.

    param postcode: UK post code (just the first section), e.g. M15
    returns: a set of tuples with start time and carbon intensity
    """
    # just get the first part of the postcode, assume spaces are included
    postcode = postcode.split()[0]
    
    # get the time (as a datetime object) and update this to be the 'top' of
    # the current hour or half hour in UTZ plus one minute. So a call at 
    # 17:47 BST will yield a timestamp of 16:31 UTC. This means that within
    # any given half hour we will always use the same timestamp. As this 
    # becomes part of the URL, calls can be cached using standard HTTP 
    # caching layers
    dt = datetime.now(timezone.utc)
    if dt.minute > 30:
        dt = dt.replace(minute=31, second=0, microsecond=0)
    else:
        dt = dt.replace(minute=1, second=0, microsecond=0)
    timestamp = dt.strftime("%Y-%m-%dT%H:%MZ")

    # Setup a session for the API call. This uses a global HTTP cache
    # with the URL as the key. Failed attempts are not cahched.
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
