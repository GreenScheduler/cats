from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass(order=True)
class CarbonIntensityPointEstimate:
    """Represents a single data point within a carbon intensity
    timeseries. Use order=True in order to enable comparison of class
    instance based on the sort_index attribute.  See
    https://peps.python.org/pep-0557
    """
    datetime: datetime
    value: float

    def __post_init__(self):
        self.sort_index = self.value


class WindowedForecast:

    def __init__(self, data: list[tuple[datetime, int]], window_size: int):
        self.times = [row[0] for row in data]
        self.intensities = [row[1] for row in data]
        self.window_size = window_size

    def __getitem__(self, index):
        v = [
            0.5 * (a + b)
            for a, b in zip(
                    self.intensities[index: index + self.window_size - 1],
                    self.intensities[index + 1 : index + self.window_size]
            )]

        avg = sum(v) / self.window_size
        return CarbonIntensityPointEstimate(
            self.times[index], avg
        )

    def __iter__(self):
        for index in range(self.__len__()):
            yield self.__getitem__(index)

    def __len__(self):
        return len(self.times) - self.window_size
