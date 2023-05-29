import cats
from cats.CI_api_query import CI_API
from cats.CI_api_interface import CarbonIntensityEstimate

def test_api_call():
    """
    This just checks the API call runs and returns a list of tuples
    """

    APIcall = CI_API(choice_CI_API='carbonintensity.org.uk')
    parsed_data = APIcall.get_forecast("M15")

    assert isinstance(parsed_data, list)
    for item in parsed_data:
        assert isinstance(item, CarbonIntensityEstimate)
