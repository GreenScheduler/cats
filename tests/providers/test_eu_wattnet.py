import os
from datetime import datetime

import pytest

from cats.exceptions import InvalidLocationError
from cats.forecast import PointEstimate
from cats.providers import WattnetEuProvider


def has_auth_env_setup():
    """
    Return True if both email and password environment is set
    """
    email = os.environ.get("CATS_WATTNET_EMAIL", "")
    password = os.environ.get("CATS_WATTNET_PASSWORD", "")
    return (email != "") and (password != "")


@pytest.mark.skipif(
    not has_auth_env_setup(), reason="No authentication token found in environment"
)
def test_get_data():
    """
    This just checks the API call runs and returns a list of point estimates

    Also confirms that datetime objects are timezone aware, as per
    https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive

    The tests do not run if the authentication tokens are not set in the appropriate environment
    variables
    """
    timestamp = datetime.now()
    provider = WattnetEuProvider()
    response = provider.get_data(timestamp, "GB")

    assert isinstance(response.values, list)
    for item in response.values:
        assert isinstance(item, PointEstimate)
        assert (item.datetime.tzinfo is not None) and (
            item.datetime.tzinfo.utcoffset(item.datetime) is not None
        )


def test_bad_postcode():
    timestamp = datetime.now()
    provider = WattnetEuProvider()

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "OX4")

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "A")


def test_missing_location_raises_error():
    timestamp = datetime.now()
    provider = WattnetEuProvider()
    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp)
