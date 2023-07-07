import cats
from cats.CI_api_interface import API_interfaces
from cats.forecast import CarbonIntensityPointEstimate

def test_api_call():
    """
    This just checks the API call runs and returns a list of tuples
    """

    api_interface = API_interfaces["carbonintensity.org.uk"]
    response = cats.api_query.get_CI_forecast(
        postcode='OX1',
        request_url=api_interface.get_request_url,
        parse_data_from_json=api_interface.parse_response_data,
    )

    assert isinstance(response, list)
    for item in response:
        assert isinstance(item, CarbonIntensityPointEstimate)
