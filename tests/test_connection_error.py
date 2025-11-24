import pytest
from unittest.mock import patch
from requests.exceptions import ConnectionError

import cats.CI_api_query as ciq
from cats.CI_api_interface import API_interfaces


def test_connection_error_print(capfd):
    api_interface = API_interfaces["carbonintensity.org.uk"]

    with patch("cats.CI_api_query.requests_cache.CachedSession.get") as mock_get:
        mock_get.side_effect = ConnectionError("boom")

        ciq.get_CI_forecast("OX1", api_interface)

        out, err = capfd.readouterr()

        assert "Unable to connect" in out