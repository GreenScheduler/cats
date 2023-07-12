import requests_cache
from datetime import datetime, timezone

from .forecast import CarbonIntensityPointEstimate

def get_CI_forecast(postcode: str, CI_API_interface) -> list[CarbonIntensityPointEstimate]:
    """
    get carbon intensity from carbonintensity.org.uk

    Given the postcode and an API interface, return a list of predictions of the
    future carbon intensity.

    param postcode: UK post code (just the first section), e.g. M15
    returns: a list of CarbonIntensityPointEstimate
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

    r = session.get(CI_API_interface.get_request_url(dt, postcode))
    data = r.json()

    return CI_API_interface.parse_response_data(data)


if __name__ == "__main__":
    # test example using Manchester as a location
    data_tuples = get_CI_forecast("M15")
