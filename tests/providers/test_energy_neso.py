from datetime import datetime

from cats.forecast import PointEstimate
from cats.providers import UKGenerationDemandProvider


def test_get_data():
    """
    This just checks the API call runs and returns a list of point estimates

    Also confirms that datetime objects are timezone aware, as per
    https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive
    """

    timestamp = datetime.now()
    provider = UKGenerationDemandProvider()
    response = provider.get_data(timestamp)

    assert isinstance(response.values, list)
    for item in response.values:
        assert isinstance(item, PointEstimate)
        assert (item.datetime.tzinfo is not None) and (
            item.datetime.tzinfo.utcoffset(item.datetime) is not None
        )
