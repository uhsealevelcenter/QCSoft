import numpy as np


class Sensor:
    """
    rate   : sampling rate,
    height : switch height,
    type   : sensor type,
    date   : the initial date/time,
    data   : sea level measurements
    """

    def __init__(self, rate: int, height: int, sensor_type: str, date: str, data: [int], time_info: str, header: str,
                 line_count: int):
        self.rate = rate
        self.height = height
        self.type = sensor_type
        self.date = date
        self.data = data
        self.time_info = time_info
        self.header = header
        self.line_count = line_count

    def get_flat_data(self):
        return self.data.flatten()

    def get_time_vector(self):
        return np.array(
            [self.date + np.timedelta64(i * int(self.rate), 'm') for i in range(self.get_flat_data().size)])

    def __repr__(self):
        return self.type


class SensorCollection:
    def __init__(self, sensors: Sensor = None):
        if sensors is None:
            sensors = {}
        self.sensors = sensors

    def add_sensor(self, sensor: Sensor):
        self.sensors[sensor.type] = sensor


class Month:

    def __init__(self, month: int, sensors: SensorCollection):
        self.month = month
        self.name = 'january'  # Todo: this is a placeholder, the month name should ne calculated based on the
        # integer 1 through 12
        self.sensor_collection = sensors


# It should be like this: Each Station has a Month/Months associated with it, and then each Month has one or more
# Sensors. This
# way we can
# account for removal/addition of sensors between months.
# I've been going a lot back and forth between whether Station should have Months or whether the Month should have
# one Station. The right approach seems to be that each Station can have one or multiple months loaded with it,
# and each month has its own Sensors with their own data.

class Station:
    def __init__(self, name: str, location: [float, float], station_id: str, month: [Month]):
        self.name = name
        self.location = location
        self.id = station_id
        self.month_collection = month


class DataCollection:

    def __init__(self, month: Month = None):
        if month is None:
            months = []
        self.months = months

    def add_sensor(self, month: Month):
        self.months.append(month)
