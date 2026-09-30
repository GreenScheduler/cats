"""
Base API provider
-----------------

This module provides the base provider class from which all API providers for
CATS are derived from. To define a new provider, create a new class derived from
BaseProvider, overriding all the abstract methods and register it
using the ``@provider`` decorator to register the provider.
"""

# pyright: reportAny=none

from __future__ import annotations

import tempfile
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, ClassVar

from ..cache import Cache
from ..exceptions import UnsupportedProviderError
from ..forecast import Timeseries
from ..version import user_agent

PROVIDERS: dict[str, type[BaseProvider]] = {}


def fetch_url(url: str, headers: dict[str, str] | None = None) -> Any:
    """
    Fetch and decode json representation of a provider's forecast data

    The provider is responsible for formatting a `url` which typically includes
    location, time and format information for the desired forecast. This is
    either extracted from a cache (if the forecast has been requested before with
    the same URL) or requested from the provider. The provider can also add `headers`
    as needed. This function always includes the CATS user_agent in the headers
    used in the request. Successful responses are cached, decoded from json to
    python objects and returned to the provider (which is responsible for extracting
    the required information). Python objects may be returned as a dictionary or a list,
    depending on the structure of the json. Failed requests may return empty
    dictionaries or lists, or may include debugging information. The provider is
    responsible for checking this.

    :raises requests.exceptions.JSONDecodeError: If the response body does not
            contain valid json.
    :raises requests.exceptions.HTTPError: If the HTTP request fails
    """
    # Use a global HTTP cache in the temp directory with the URL as the key.
    # Entries expire after a day. Failed attempts are not cached.
    cache = Cache(Path(tempfile.gettempdir()), expires_after=timedelta(days=1))
    headers = headers or {}
    headers.update(user_agent)
    response = cache.get(url, headers=headers)
    # Catch and raise any HTTP errors
    response.raise_for_status()
    return response.json()  # pyright: ignore[reportUnknownMemberType]


class BaseProvider(ABC):
    "Base provider class from which API providers in CATS derive from"

    BASE_URL: ClassVar[str]

    def __init__(
        self, api_data: dict[str, Any] | None = None, base_url: str | None = None
    ):
        self.api_data: dict[str, Any] | None = api_data
        self.base_url: str = base_url or self.BASE_URL

    @abstractmethod
    def validate_location(self, location: str | None) -> str:
        "Returns location if valid, otherwise raises InvalidLocationError"

    @abstractmethod
    def get_max_duration_minutes(self, metric: str | None = None) -> int:
        "Returns maximum supported duration in minutes for a particular metric"

    @abstractmethod
    def get_temporal_resolution_minutes(self, metric: str | None = None) -> int:
        "Returns temporal resolution in minutes for a metric"

    @abstractmethod
    def get_data(
        self,
        timestamp: datetime,
        location: str | None = None,
        metric: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Timeseries:
        """Retrieves data from provider API

        :param timestamp: Timestamp from which to start forecast data retrieval
        :param location: Location for which to start forecast data retrieval
        :param metric: Optional, if specified selects a specific metric from provider
        :param headers: Optional, if specified, passes additional headers, such as for authentication
        :return: Timeseries as a list of PointEstimate classes
        """


def provider(name: str) -> Callable[[type[BaseProvider]], type[BaseProvider]]:
    "Decorator to register a provider class with CATS"

    def decorator(cls: type[BaseProvider]):
        PROVIDERS[name] = cls
        return cls

    return decorator


def get_provider(name: str) -> type[BaseProvider]:
    if name in PROVIDERS:
        return PROVIDERS[name]
    raise UnsupportedProviderError(name)
