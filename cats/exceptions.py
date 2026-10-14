"Exceptions used in CATS"


class InvalidLocationError(Exception):
    "Location passed was invalid for chosen provider"


class UnsupportedProviderError(Exception):
    "Provider is unsupported"


class ProviderResponseError(Exception):
    "The provider is unable to generate a valid response to the query"


class ProviderAuthenticationError(Exception):
    "Provider authentication failed"


class MissingArgumentError(Exception):
    "One or more required arguments are missing"


class DurationExceedsWindowError(Exception):
    "Duration of the job exceeds available forecast or window duration"


class SchedulerError(Exception):
    "Error occurred while scheduling job"
