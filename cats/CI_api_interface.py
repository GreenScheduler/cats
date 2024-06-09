import sys
from collections import namedtuple
from datetime import datetime
from zoneinfo import ZoneInfo

from .forecast import CarbonIntensityPointEstimate


class InvalidLocationError(Exception):
    pass


APIInterface = namedtuple(
    "APIInterface", ["get_request_url", "parse_response_data", "max_duration"]
)


def ciuk_request_url(timestamp: datetime, postcode: str):
    # This transformation is specific to the CI-UK API.
    # get the time (as a datetime object) and update this to be the 'top' of
    # the current hour or half hour in UTZ plus one minute. So a call at
    # 17:47 BST will yield a timestamp of 16:31 UTC. This means that within
    # any given half hour we will always use the same timestamp.
    # As this becomes part of the URL, calls can be cached using standard HTTP
    # caching layer.
    if timestamp.minute > 30:
        dt = timestamp.replace(minute=31, second=0, microsecond=0)
    else:
        dt = timestamp.replace(minute=1, second=0, microsecond=0)

    if len(postcode) > 4:
        sys.stderr.write(f"Warning: truncating postcode {postcode} to ")
        postcode = postcode[:-3].strip()
        sys.stderr.write(f"{postcode}.\n")

    return (
        "https://api.carbonintensity.org.uk/regional/intensity/"
        + dt.strftime("%Y-%m-%dT%H:%MZ")
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

    def invalid_code(r: dict) -> bool:
        try:
            return "postcode" in r["error"]["message"]
        except KeyError:
            return False

    # carbonintensity.org.uk API's response behavior is inconsistent
    # with regards to bad postcodes. Passing a single character in the
    # URL will give a 400 error code with a useful message.  However
    # giving a longer string, not matching a valid postcode, lead to
    # no response at all.
    if (not response) or invalid_code(response):
        raise InvalidLocationError

    datefmt = "%Y-%m-%dT%H:%MZ"
    # The "Z" at the end of the format string indicates UTC,
    # however, strptime does not know how to parse this, so we
    # need to add tzinfo data.
    utc = ZoneInfo("UTC")
    return [
        CarbonIntensityPointEstimate(
            datetime=datetime.strptime(d["from"], datefmt).replace(tzinfo=utc),
            value=d["intensity"]["forecast"],
        )
        for d in response["data"]["data"]
    ]


API_interfaces = {
    "carbonintensity.org.uk": APIInterface(
        get_request_url=ciuk_request_url,
        parse_response_data=ciuk_parse_response_data,
        max_duration=2850,  # 48h - 30min so that carbon intensity is defined over the last interval
    ),
}
