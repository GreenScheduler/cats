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
