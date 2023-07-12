from collections import namedtuple
from datetime import datetime

from .forecast import CarbonIntensityPointEstimate


APIInterface = namedtuple('APIInterface', ['get_request_url', 'parse_response_data'])

def ciuk_request_url(timestamp: datetime, postcode: str):
    return (
        "https://api.carbonintensity.org.uk/regional/intensity/"
        + timestamp.strftime("%Y-%m-%dT%H:%MZ")
        + "/fw48h/postcode/"
        + postcode
    )


def ciuk_parse_response_data(response: dict):
    """
    This wraps the API from carbonintensity.org.uk
    and is set up to cache data from call to call even accross different
    processes within the same half hour window. The returned prediction data
    is in half hour blocks starting from the half hour containing the current
    time and extending for 48 hours into the future.

    :param response:
    :return:
    """
    datefmt = "%Y-%m-%dT%H:%MZ"
    return [
        CarbonIntensityPointEstimate(
            datetime=datetime.strptime(d["from"], datefmt),
            value=d["intensity"]["forecast"],
        )
        for d in response["data"]["data"]
    ]

API_interfaces = {
    "carbonintensity.org.uk": APIInterface(
        get_request_url=ciuk_request_url,
        parse_response_data=ciuk_parse_response_data,
        ),
    }
