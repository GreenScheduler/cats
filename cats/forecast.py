from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(order=True)
class CarbonIntensityPointEstimate:
    """Represents a single data point within an intensity
    timeseries. Use order=True in order to enable comparison of class
    instance based on the sort_index attribute.  See
    https://peps.python.org/pep-0557

    """
    sort_index: float = field(init=False, repr=False)
    datetime: datetime
    value: float

    def __post_init__(self):
        self.sort_index = self.value


@dataclass(order=True)
class CarbonIntensityAverageEstimate:
    """Represents a single data point within an *integrated* carbon
    intensity timeseries. Use order=True in order to enable comparison
    of class instance based on the sort_index attribute.  See
    https://peps.python.org/pep-0557
    """
    sort_index: float = field(init=False, repr=False)
    start: datetime  # Start of the time-integration window
    end: datetime  # End of the time-integration window
    value: float

    def __post_init__(self):
        self.sort_index = self.value


class WindowedForecast:

    def __init__(self, data: list[CarbonIntensityPointEstimate], window_size: int):
        self.times = [point.datetime for point in data]
        self.intensities = [point.value for point in data]
        # Integration window size in number of time intervals covered
        # by the window.
        self.window_size = window_size

    def __getitem__(self, index: int) -> CarbonIntensityAverageEstimate:
        """Return the average of timeseries data from index over the
        window size.  Data points are integrated using the trapeziodal
        rule, that is assuming that forecast data points are joined
        with a straight line.
        """
        v = [  # If you think of a better name, pls help!
            0.5 * (a + b)
            for a, b in zip(
                    self.intensities[index: index + self.window_size],
                    self.intensities[index + 1 : index + self.window_size + 1]
            )]

        return CarbonIntensityAverageEstimate(
            start=self.times[index],
            # Note that `end` points to the _start_ of the last
            # interval in the window.
            end=self.times[index + self.window_size],
            value=sum(v) / self.window_size,
        )

    def __iter__(self):
        for index in range(self.__len__()):
            yield self.__getitem__(index)

    def __len__(self):
        return len(self.times) - self.window_size - 1
