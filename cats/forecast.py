from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(order=True)
class CarbonIntensityPointEstimate:
    """Represents a single data point within an intensity
    timeseries. Use order=True in order to enable comparison of class
    instance based on the first attribute. See
    https://peps.python.org/pep-0557
    """

    value: float  # the first attribute is used automatically for sorting methods
    datetime: datetime

    def __repr__(self):
        return f"{self.datetime.isoformat()}\t{self.value}"


@dataclass(order=True)
class CarbonIntensityAverageEstimate:
    """Represents a single data point within an *integrated* carbon
    intensity timeseries. Use order=True in order to enable comparison
    of class instance based on the first attribute.  See
    https://peps.python.org/pep-0557
    """

    value: float
    start: datetime  # Start of the time-integration window
    end: datetime  # End of the time-integration window


class WindowedForecast:
    def __init__(
        self,
        data: list[CarbonIntensityPointEstimate],
        duration: int,  # in minutes
        start: datetime,
    ):
        self.data_stepsize = data[1].datetime - data[0].datetime
        self.start = start
        # TODO: Expect duration as a timedelta directly
        self.end = start + timedelta(minutes=duration)

        # Restrict data points so that start time falls within the
        # first data interval.  In other we don't need any data prior
        # the closest data preceding (on the left of) the job start
        # time.
        def bisect_right(data, t):
            for i, d in enumerate(data):
                if d.datetime > t:
                    return i - 1

        # bisect_right(data, start) returns the index of the first
        # data point with datetime value immediately preceding the job
        # start time
        self.data = data[bisect_right(data, start) :]

        # Find number of data points in a window, by finding the index
        # of the closest data point past the job end time. Could be
        # done with the bisect module in the stdlib for python 3.10+
        # ('key' parameter was introduced in 3.10).
        #
        # bisect_left(data, self.end, key=lambda x: x.datetime)
        #
        def bisect_left(data, t):
            for i, d in enumerate(data):
                if d.datetime + self.data_stepsize >= t:
                    return i + 1

        self.ndata = bisect_left(self.data, self.end)  # window size

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

        # Account for the fact that the start and end of each window
        # might not fall exactly on data points.  The starting
        # intensity is interpolated between the first (index) and
        # second data point (index + 1) in the window.  The ending
        # intensity value is interpolated between the last and
        # penultimate data points in the window.
        window_start = self.start + index * self.data_stepsize
        window_end = self.end + index * self.data_stepsize

        # lbound: carbon intensity point estimate at window start
        lbound = self.interp(
            self.data[index],
            self.data[index + 1],
            when=window_start,
        )
        # rbound: carbon intensity point estimate at window end
        # Handle case when last data point exactly matches last carbon intensity,
        # so there is no further data point to interpolate from.
        if index + self.ndata == len(self.data):
            rbound = self.data[-1]
        else:
            rbound = self.interp(
                self.data[index + self.ndata - 1],
                self.data[index + self.ndata],
                when=window_end,
            )
        # window_data <- [lbound] + [...bulk...] + [rbound] where
        # lbound and rbound are interpolated intensity values.
        window_data = [lbound] + self.data[index + 1 : index + self.ndata] + [rbound]
        acc = [
            0.5 * (a.value + b.value) * (b.datetime - a.datetime).total_seconds()
            for a, b in zip(window_data[:-1], window_data[1:])
        ]
        duration = window_data[-1].datetime - window_data[0].datetime
        return CarbonIntensityAverageEstimate(
            start=window_start,
            end=window_end,
            value=sum(acc) / duration.total_seconds(),
        )

    @staticmethod
    def interp(
        p1: CarbonIntensityPointEstimate,
        p2: CarbonIntensityPointEstimate,
        when: datetime,
    ) -> CarbonIntensityPointEstimate:
        """Return carbon intensity pt estimate at a time between data
        points, assuming points are joined by a straight line (linear
        interpolation).
        """
        timestep = (p2.datetime - p1.datetime).total_seconds()

        slope = (p2.value - p1.value) / timestep
        offset = (when - p1.datetime).total_seconds()

        return CarbonIntensityPointEstimate(
            value=p1.value + slope * offset,
            datetime=when,
        )

    def __iter__(self):
        for index in range(self.__len__()):
            yield self.__getitem__(index)

    def __len__(self):
        return len(self.data) - self.ndata + 1
