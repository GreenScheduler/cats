from dataclasses import dataclass
from datetime import datetime, timezone
from collections import namedtuple

@dataclass(order=True)
class CarbonIntensityEstimate:
    """Represents an average carbon intensity for a timeperiod.
    Use order=True in order to enable comparison of class
    instance based on the sort_index attribute. See
    https://peps.python.org/pep-0557

    value: needs to be in gCO2e

    """
    value: float # value needs to be first for the sort function to work
    start: datetime
    end: datetime

    def __post_init__(self):
        self.sort_index = self.value # TODO check whether that's useful
        self.timedelta = self.end - self.start

APIinterface = namedtuple('APIInterface', ['get_request_url', 'parse_response_data'])

### for the UK API 'carbonintensity.org.uk' ###

def ciuk_request_url(timestamp: datetime, location: str):
    postcode_cleaned = location.split()[0]
    return (
            "https://api.carbonintensity.org.uk/regional/intensity/"
            + timestamp.strftime("%Y-%m-%dT%H:%MZ")
            + "/fw48h/postcode/"
            + postcode_cleaned
    )

def ciuk_parse_response_data(response: dict):
    def ciuk_parsetime(datestr: str) -> datetime:
        dateformat = "%Y-%m-%dT%H:%MZ"
        return datetime.strptime(datestr, dateformat).replace(tzinfo=timezone.utc)

    return [
        CarbonIntensityEstimate(
            start=ciuk_parsetime(d["from"]),
            end=ciuk_parsetime(d["to"]),
            value=d["intensity"]["forecast"], # convert to gCO2e if needed
        )
        for d in response["data"]["data"]
    ]

API_interfaces = {
    "carbonintensity.org.uk": APIinterface(
        get_request_url=ciuk_request_url,
        parse_response_data=ciuk_parse_response_data,
        ),
    }

if __name__ == "__main__":
    import requests

    interface = API_interfaces['carbonintensity.org.uk']
    request_url = interface.get_request_url(timestamp=datetime.now(timezone.utc), location='M15')
    response = requests.get(request_url).json()
    parsed_response = interface.parse_response_data(response)

    print()