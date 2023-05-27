import requests_cache
from typing import Callable
from datetime import datetime, timezone
from .parsedata import writecsv


def get_tuple(
    postcode: str,
    request_url: Callable[[datetime, str], str],
    parse_data_from_json: Callable[[dict], list[tuple[datetime, int]]],
) -> list[list[tuple[datetime, int]]]:
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

    # Setup a session for the API call. This uses a global HTTP cache
    # with the URL as the key. Failed attempts are not cahched.
    session = requests_cache.CachedSession('cats_cache', use_temp=True)
    # get the carbon intensity api data

    r = session.get(request_url(dt, postcode))
    data = r.json()

    return parse_data_from_json(data)


if __name__ == "__main__":
    # test example using Manchester as a location
    data_tuples = get_tuple("M15")
    writecsv(data_tuples)
