from datetime import datetime, timezone

import requests_cache

from .forecast import CarbonIntensityPointEstimate


def get_CI_forecast(
    location: str, CI_API_interface
) -> list[CarbonIntensityPointEstimate]:
    """
    Get carbon intensity from an API

    Given the location and an API interface, return a list of predictions of the
    future carbon intensity.

    param location: [str] Depends on country. UK postcode (just the first section), e.g. M15.
    returns: a list of CarbonIntensityPointEstimate
    """

    # Setup a session for the API call. This uses a global HTTP cache
    # with the URL as the key. Failed attempts are not cached.
    session = requests_cache.CachedSession("cats_cache", use_temp=True)

    # get the carbon intensity api data
    r = session.get(
        CI_API_interface.get_request_url(datetime.now(timezone.utc), location)
    )
    data = r.json()

    return CI_API_interface.parse_response_data(data)


if __name__ == "__main__":  # pragma: no cover
    from .CI_api_interface import API_interfaces

    # test example using Manchester as a location
    data_tuples = get_CI_forecast("M15", API_interfaces["carbonintensity.org.uk"])
