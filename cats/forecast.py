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
        self.data = data
        self.data_stepsize = data[1].datetime - data[0].datetime
        self.start = start
        # TODO: Expect duration as a timedelta directly
        self.end = start + timedelta(minutes=duration)

        # Find number of data points in a window, by finding the index
        # of the first data point past the job end time. Could be done
        # with the bisect module in the stdlib for python 3.10+ ('key'
        # parameter was introduced in 3.10).
        #
        # bisect_left(data, self.end, key=lambda x: x.datetime)
        #
        def bisect_left(data, t):
            for i, d in enumerate(data):
                if d.datetime >= t:
                    return i
        self.ndata = bisect_left(data, self.end) + 1

    def __getitem__(self, index: int) -> CarbonIntensityAverageEstimate:
        """Return the average of timeseries data from index over the
        window size.  Data points are integrated using the trapeziodal
        rule, that is assuming that forecast data points are joined
        with a straight line.

        Integral value between two points is the intensity value at
        the midpoint times the duration between the two points.  This
        duration is assumed to be unity and the average is computed by
        dividing the total integral value by the number of intervals.
        """
        midpt = [
            0.5 * (a.value + b.value)
            for a, b in zip(
                    self.data[index: index + self.ndata - 1],
                    self.data[index + 1: index + self.ndata]
            )]

        # Account for the fact that the start and end of each window
        # might not fall exactly on data points.  The starting
        # intensity is interpolated between the first (index) and
        # second data point (index + 1) in the window.  The ending
        # intensity value is interpolated between the last and
        # penultimate data points in he window.
        start = self.start + index * self.data_stepsize
        i = self.interp(self.data[index], self.data[index + 1], when=start)
        midpt[0] = 0.5 * (i + self.data[index + 1].value)

        end = self.end + index * self.data_stepsize
        i = self.interp(
            self.data[index + self.ndata - 2],
            self.data[index + self.ndata - 1],
            when=end,
        )
        midpt[-1] = 0.5 * (self.data[index + self.ndata - 2].value + i)

        return CarbonIntensityAverageEstimate(
            start=start,
            end=end,
            value=sum(midpt) / (self.ndata - 1),
        )

    @staticmethod
    def interp(
            p1: CarbonIntensityPointEstimate,
            p2: CarbonIntensityPointEstimate,
            when: datetime
    ):
        """Return value of carbon intensity at a time between data
        points, assuming points are joined by a straight line (linear
        interpolation).
        """
        timestep = (p2.datetime - p1.datetime).total_seconds()

        slope = (p2.value - p1.value) / timestep
        offset = (when - p1.datetime).total_seconds()
        # import pdb; pdb.set_trace()
        return p1.value + slope * offset  # Value at t = start

    def __iter__(self):
        for index in range(self.__len__()):
            yield self.__getitem__(index)

    def __len__(self):
        return len(self.data) - self.ndata
