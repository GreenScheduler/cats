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

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, ClassVar

import requests_cache

from ..exceptions import UnsupportedProviderError
from ..forecast import Timeseries
from ..version import user_agent

PROVIDERS: dict[str, type[BaseProvider]] = {}


def fetch_url(url: str, headers: dict[str, str] | None = None) -> Any:
    # Setup a session for the API call. This uses a global HTTP cache
    # with the URL as the key. Failed attempts are not cached.
    session = requests_cache.CachedSession("cats_cache", use_temp=True)
    headers = headers or {}
    headers.update(user_agent)
    return session.get(url, headers=headers).json()  # pyright: ignore[reportUnknownMemberType]


class BaseProvider(ABC):
    "Base provider class from which API providers in CATS derive from"

    BASE_URL: ClassVar[str]

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key: str | None = api_key
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
