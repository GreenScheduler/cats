from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(order=True)
class CarbonIntensityEstimate:
    """Represents an average carbon intensity for a timeperiod.
    Use order=True in order to enable comparison of class
    instance based on the sort_index attribute. See
    https://peps.python.org/pep-0557

    """
    value: float # value needs to be first for the sort function to work
    start: datetime
    end: datetime

    def __post_init__(self):
        self.sort_index = self.value # TODO check whether that's useful
        self.timedelta = self.end - self.start

class CI_API_interface():
    def __init__(self, choice_CI_API):
        '''
        This class contains API-specific functions to get URLs and then parse the response data
        :param choice_API: [str] one of ['carbonintensity.org.uk']
        '''
        assert choice_CI_API in ['carbonintensity.org.uk']
        self.choice_CI_API = choice_CI_API

    def get_request_url(self, timestamp: datetime, location: str):
        if self.choice_CI_API == 'carbonintensity.org.uk':
            # Clean postcode in case a full one is provided (with space in the middle)
            postcode_cleaned = location.split()[0]

            return (
                    "https://api.carbonintensity.org.uk/regional/intensity/"
                    + timestamp.strftime("%Y-%m-%dT%H:%MZ")
                    + "/fw48h/postcode/"
                    + postcode_cleaned
            )

        # Other countries/APIs can be added here

        else:
            return ''

    def parse_response_data(self, response: dict):
        if self.choice_CI_API == 'carbonintensity.org.uk':
            # Create a list of CarbonIntensityEstimate objects
            # (each being a triple of start and end datetimes and a CI)
            return [
                CarbonIntensityEstimate(
                    start=self.parsetime(d["from"]),
                    end=self.parsetime(d["to"]),
                    value=d["intensity"]["forecast"],
                )
                for d in response["data"]["data"]
            ]

        # Other countries/APIs can be added here

        else:
            return []

    ### Below are helper functions ###
    def parsetime(self, datestr: str) -> datetime:
        """parse the date string (for now, based on UK API format)
        param datestr: a date string from the api
        returns: a datetime value
        """
        if self.choice_CI_API == 'carbonintensity.org.uk':
            dateformat = "%Y-%m-%dT%H:%MZ"
            return datetime.strptime(datestr, dateformat).replace(tzinfo=timezone.utc)


if __name__ == "__main__":
    import requests

    CI_API = CI_API_interface('carbonintensity.org.uk')
    request_url = CI_API.get_request_url(timestamp=datetime.now(timezone.utc), location='M15')
    response = requests.get(request_url).json()
    parsed_response = CI_API.parse_response_data(response)
    print()