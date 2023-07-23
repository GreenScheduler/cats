from math import ceil
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

    def __init__(
            self,
            data: list[CarbonIntensityPointEstimate],
            duration: int,  # in minutes
            start: datetime,
    ):
        self.times = [point.datetime for point in data]
        self.intensities = [point.value for point in data]
        # Integration window size in number of time intervals covered
        # by the window.
        self.data_stepsize = data[1].datetime - data[0].datetime
        self.window_size = ceil(duration / (self.data_stepsize.total_seconds() / 60))
        self.start = start
        # TODO: Expect duration as a timedelta directly
        self.duration = timedelta(minutes=duration)

    @staticmethod
    def interp(
            p1: CarbonIntensityPointEstimate,
            p2: CarbonIntensityPointEstimate,
            p: datetime
    ):
        timestep = (p2.datetime - p1.datetime).total_seconds()

        slope = (p2.value - p1.value) / timestep
        offset = (p - p1.datetime).total_seconds()
        # import pdb; pdb.set_trace()
        return p1.value + slope * offset  # Value at t = start

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

        start = self.start + index * self.data_stepsize
        p1 = CarbonIntensityPointEstimate(self.times[index], self.intensities[index])
        p2 = CarbonIntensityPointEstimate(self.times[index + 1], self.intensities[index + 1])
        v[0] = 0.5 * (self.interp(p1, p2, start) + self.intensities[index + 1])

        end = self.start + index * self.data_stepsize + self.duration
        p1 = CarbonIntensityPointEstimate(self.times[index + self.window_size - 1], self.intensities[index + self.window_size - 1])
        p2 = CarbonIntensityPointEstimate(self.times[index + self.window_size], self.intensities[index + self.window_size])
        v[-1] = 0.5 * (
            self.intensities[index + self.window_size - 1] + self.interp(p1, p2, end)
        )

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
