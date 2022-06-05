import numpy as np


class Sensor:
    """
    rate   : sampling rate,
    height : switch height,
    type   : sensor type,
    date   : the initial date/time,
    data   : sea level measurements
    """

    def __init__(self, rate: int, height: int, sensor_type: str, date: str, data: [int], time_info: str, header: str):
        self.rate = rate
        self.height = height
        self.type = sensor_type
        self.date = date
        self.data = data
        self.time_info = time_info
        self.header = header

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

    def __getitem__(self, name):
        return self.sensors[name]

    def __iter__(self):
        return iter(self.sensors)

    def keys(self):
        return self.sensors.keys()

    def items(self):
        return self.sensors.items()

    def values(self):
        return self.sensors.values()


class Month:

    def __init__(self, month: int, year: int, sensors: SensorCollection, st_id: str):
        self.month = month
        self.year = year
        self.name = 'january'  # Todo: this is a placeholder, the month name should be mapped to integers 1 through 12
        self.sensor_collection = sensors
        self.station_id = st_id

    def assemble_root_filename(self):
        month_int = self.month
        month_str = "{:02}".format(month_int)
        year_str = "{:02}".format(self.year)
        station_num = self.station_id
        root_filename = '{}{}{}'.format(station_num, year_str, month_str)
        return root_filename

    def get_ts_filename(self):
        file_name = '{}{}{}'.format('t', self.assemble_root_filename(), '.dat')
        return file_name

    def get_mat_filename(self):
        sensor_file = {}
        for key, sensor in self.sensor_collection.items():
            file_name = '{}{}{}'.format(self.assemble_root_filename(), key.lower(), '.mat')
            sensor_file[key] = file_name

        return sensor_file


# It should be like this: Each Station has a Month/Months associated with it, and then each Month has one or more
# Sensors. This
# way we can
# account for removal/addition of sensors between months.
# I've been going a lot back and forth between whether Station should have Months or whether the Month should have
# one Station. The right approach seems to be that each Station can have one or multiple months loaded with it,
# and each month has its own Sensors with their own data.

class Station:
    def __init__(self, name: str, location: [float, float], month: [Month]):
        self.name = name
        self.location = location
        self.month_collection = month
        self.aggregate_months = self.combine_months()

    def month_length(self):
        return len(self.month_collection)

    def combine_months(self):
        """
        Combines sealevel data for multiple months for each sensor
        """

        combined_sealevel_data = {}
        comb_time_vector = {}

        for _month in self.month_collection:

            for key, value in _month.sensor_collection.sensors.items():
                if 'ALL' not in key:
                    if key in combined_sealevel_data:
                        combined_sealevel_data[key] = np.concatenate(
                            (combined_sealevel_data[key], _month.sensor_collection.sensors[
                                key].get_flat_data()), axis=0)
                    else:
                        combined_sealevel_data[key] = _month.sensor_collection.sensors[key].get_flat_data()

                if 'ALL' not in key:
                    if key in comb_time_vector:
                        comb_time_vector[key] = np.concatenate(
                            (comb_time_vector[key], _month.sensor_collection.sensors[
                                key].get_time_vector()), axis=0)
                    else:
                        comb_time_vector[key] = _month.sensor_collection.sensors[key].get_time_vector()
        combined = {'data': combined_sealevel_data, 'time': comb_time_vector}
        return combined

    def back_propagate_changes(self, combined_data):
        """
        Because we combine multiple months of data, we need the ability to split the data back to individual months as
        we are making changes to data (during cleaning) and we need to save those changes.
        :param combined_data: an object comprised of sensors keys holding sea level data
        """

        so_far_index = {}  # Keeps track of data sizes for each sensor for each month so that we can separate it
        # properly by each month
        for i, _month in enumerate(self.month_collection):
            for key, value in _month.sensor_collection.sensors.items():
                if 'ALL' not in key:
                    # We need to keep track of the previous data size so we can slide the index for each new month
                    if key in combined_data:
                        if i == 0:
                            so_far_index[key] = 0
                        else:
                            previous_data_size = self.month_collection[i - 1].sensor_collection.sensors[key].data.size
                            so_far_index[key] = so_far_index[key] + previous_data_size
                        data_size = _month.sensor_collection.sensors[key].data.size
                        data_shape = _month.sensor_collection.sensors[key].data.shape
                        try:
                            _month.sensor_collection.sensors[key].data = np.reshape(
                                combined_data[key][so_far_index[key]:data_size + so_far_index[key]],
                                data_shape)
                        except ValueError as e:
                            print(e, "i: {}, month: {}, sensor:{}".format(i, _month.month, key))


class DataCollection:

    def __init__(self, station: Station = None):
        self.station = station
        self.sensors = self.combined_months()
