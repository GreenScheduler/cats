import requests_cache
from datetime import datetime, timezone

from .CI_api_interface import CI_API_interface

class CI_API():
    def __init__(self, choice_CI_API):
        self.API = CI_API_interface(choice_CI_API)

    def get_forecast(
            self,
            location: str,
    ) -> list[list[tuple[datetime, int]]]:
        """
        Gets carbon intensity from the chosen API.

        carbonintensity.org.uk:
        Given the postcode and current time, return a set of predictions of the
        future carbon intensity. This wraps the API from carbonintensity.org.uk
        and is set up to cache data from call to call even accross different
        processes within the same half hour window. The returned prediction data
        is in half hour blocks starting from the half hour containing the current
        time and extending for 48 hours into the future.
        Parameter `location` should be a UK post code (just the first section), e.g. M15

        param location: [str]
        returns: a set of tuples with start time and carbon intensity
        """

        # get the time (as a datetime object) and update this to be the 'top' of
        # the current hour or half hour in UTZ plus one minute. So a call at
        # 17:47 BST will yield a timestamp of 16:31 UTC. This means that within
        # any given half hour we will always use the same timestamp. As this
        # becomes part of the URL, calls can be cached using standard HTTP
        #  caching layers
        # TODO why is that below needed at all?
        dt = datetime.now(timezone.utc)
        if dt.minute > 30:
            dt = dt.replace(minute=31, second=0, microsecond=0)
        else:
            dt = dt.replace(minute=1, second=0, microsecond=0)

        # Setup a session for the API call. This uses a global HTTP cache
        # with the URL as the key. Failed attempts are not cahched.
        session = requests_cache.CachedSession('cats_cache', use_temp=True)

        # get the carbon intensity api data
        r = session.get(self.API.get_request_url(timestamp=dt, location=location))
        data = r.json()
        return self.API.parse_response_data(data)


if __name__ == "__main__":
    # test example using Manchester as a location
    APIcall = CI_API(choice_CI_API='carbonintensity.org.uk')
    parsed_data = APIcall.get_forecast("M15")
    print()
