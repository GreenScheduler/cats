from datetime import datetime, timedelta


class WindowedForecast:

    def __init__(self, data: list[tuple[datetime, int]], window_size: int):
        self.times = [row[0] for row in data]
        self.intensities = [row[1] for row in data]
        self.window_size = window_size

    def __getitem__(self, index):
        avg = sum(
            self.intensities[index:index + self.window_size]
        ) / self.window_size
        return (self.times[index], avg)

    def __iter__(self):
        for index in range(self.__len__()):
            yield self.__getitem__(index)

import math
data = [
    (datetime.today() + timedelta(minutes=i), math.sin(i * (math.pi / 10)))
    for i in range(10)
]
        
        
    
    def __len__(self):
        return len(self.times) - self.window_size
