from datetime import datetime

import pytest

from cats.exceptions import InvalidLocationError
from cats.forecast import PointEstimate
from cats.providers import UKCarbonIntensityProvider


def test_get_data():
    """
    This just checks the API call runs and returns a list of point estimates

    Also confirms that datetime objects are timezone aware, as per
    https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive
    """

    timestamp = datetime.now()
    provider = UKCarbonIntensityProvider()
    response = provider.get_data(timestamp, "OX1")
    response_full_postcode = UKCarbonIntensityProvider().get_data(timestamp, "OX1 3QD")

    assert response == response_full_postcode
    assert isinstance(response.values, list)
    for item in response.values:
        assert isinstance(item, PointEstimate)
        assert (item.datetime.tzinfo is not None) and (
            item.datetime.tzinfo.utcoffset(item.datetime) is not None
        )


def test_bad_postcode():
    timestamp = datetime.now()
    provider = UKCarbonIntensityProvider()

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "OX40")

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "A")


def test_missing_location_raises_error():
    timestamp = datetime.now()
    provider = UKCarbonIntensityProvider()
    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp)
