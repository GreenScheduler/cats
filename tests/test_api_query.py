import cats

def test_api_call():
    """
    This just checks the API call runs and returns a list of tuples
    """

    response = cats.api_query.get_tuple('OX1')

    assert isinstance(response, list) 
    for item in response:
        assert isinstance(item, tuple) 
