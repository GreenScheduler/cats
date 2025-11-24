import pytest

import cats
from cats.CI_api_interface import API_interfaces, InvalidLocationError
from cats.forecast import CarbonIntensityPointEstimate


def test_api_call():
    """
    This just checks the API call runs and returns a list of point estimates

    Also confirms that datetime objects are timezone aware, as per
    https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive
    """

    api_interface = API_interfaces["carbonintensity.org.uk"]
    response = cats.CI_api_query.get_CI_forecast("OX1", api_interface)
    response_full_postcode = response = cats.CI_api_query.get_CI_forecast(
        "OX1 3QD", api_interface
    )
    assert response == response_full_postcode
    assert isinstance(response, list)
    for item in response:
        assert isinstance(item, CarbonIntensityPointEstimate)
        assert (item.datetime.tzinfo is not None) and (
            item.datetime.tzinfo.utcoffset(item.datetime) is not None
        )


def test_bad_postcode():
    api_interface = API_interfaces["carbonintensity.org.uk"]

    with pytest.raises(InvalidLocationError):
        cats.CI_api_query.get_CI_forecast("OX48", api_interface)

    with pytest.raises(InvalidLocationError):
        cats.CI_api_query.get_CI_forecast("A", api_interface)
