import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cats.exceptions import InvalidLocationError, ProviderAuthenticationError
from cats.forecast import PointEstimate
from cats.providers import WattnetEuProvider


def has_auth_env_setup():
    """
    Return True if both client ID and client secret environment is set
    """
    client_id = os.environ.get("WATTNET_CLIENT_ID", "")
    client_secret = os.environ.get("WATTNET_CLIENT_SECRET", "")
    return (client_id != "") and (client_secret != "")


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


FAKE_RESPONSE = [
    {
        "footprint_type": "carbon",
        "unit": "gCO2/kWh",
        "series": [
            {
                "valid": True,
                "points": [
                    {
                        "timestamp": "2026-07-13T00:00:00Z",
                        "value": 171.15,
                        "updated_at": "2026-07-14T06:00:00Z",
                    },
                    {
                        "timestamp": "2026-07-13T00:15:00Z",
                        "value": 160.5,
                        "updated_at": "2026-07-14T06:00:00Z",
                        "new_field": "ignored",
                    },
                ],
                # Deprecated, must not be read
                "values": [["1999-01-01T00:00:00Z", -1]],
            }
        ],
    }
]


@patch("cats.providers.eu_wattnet.fetch_url", return_value=FAKE_RESPONSE)
@patch("cats.providers.eu_wattnet.requests.post")
def test_get_data_client_credentials_and_points(mock_post, mock_fetch, monkeypatch):
    monkeypatch.setenv("WATTNET_CLIENT_ID", "my-id")
    monkeypatch.setenv("WATTNET_CLIENT_SECRET", "my-secret")
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "t", "expires_in": 3600, "token_type": "Bearer"},
    )

    response = WattnetEuProvider().get_data(datetime.now(timezone.utc), "ES")

    assert mock_post.call_args.args[0] == WattnetEuProvider.TOKEN_URL
    assert mock_post.call_args.kwargs["data"] == {
        "grant_type": "client_credentials",
        "client_id": "my-id",
        "client_secret": "my-secret",
    }
    assert mock_fetch.call_args.kwargs["headers"] == {"Authorization": "Bearer t"}
    assert response.unit == "gCO2/kWh"
    assert response.values == [
        PointEstimate(171.15, datetime(2026, 7, 13, 0, 0, tzinfo=timezone.utc)),
        PointEstimate(160.5, datetime(2026, 7, 13, 0, 15, tzinfo=timezone.utc)),
    ]


def test_missing_client_credentials_raise(monkeypatch):
    monkeypatch.delenv("WATTNET_CLIENT_ID", raising=False)
    monkeypatch.setenv("WATTNET_CLIENT_SECRET", "my-secret")
    with pytest.raises(ProviderAuthenticationError):
        WattnetEuProvider().update_authorization_token()


def test_environmental_score_not_supported():
    assert "environmental_score" not in WattnetEuProvider.SUPPORTED_METRICS
