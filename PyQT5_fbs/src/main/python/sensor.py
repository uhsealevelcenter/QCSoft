import calendar
from collections import defaultdict
from itertools import groupby
from pathlib import Path

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

    def update_header_ref(self, reference_level):
        """
        Upates this sensor's header with a new reference level
        :return:
         New header as a string
        """
        new_header = self.header[:60] + '{:04d}'.format(reference_level) + self.header[64:]
        self.header = new_header
        return self.header

    def get_reference_difference(self, new_reference):
        """
        Given the new reference level, return the difference between the new and the old one.
        It is used for offsetting the sealevel data
        :param new_reference:
        :return:
            the int difference
        """
        diff = new_reference - self.height
        return diff

    def set_reference_height(self, new_reference):
        self.height = new_reference

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
        self.name = calendar.month_abbr[month]
        self.sensor_collection = sensors
        self.station_id = st_id
        self.day_count = calendar.monthrange(year, month)[1]

    def assemble_root_filename(self, four_digit_year=False):
        month_int = self.month
        month_str = "{:02}".format(month_int)
        if not four_digit_year:
            year_str = str(self.year)[2:]
        else:
            year_str = str(self.year)
        station_num = self.station_id
        root_filename = '{}{}{}'.format(station_num, year_str, month_str)
        return root_filename

    def get_ts_filename(self):
        file_name = '{}{}{}'.format('t', self.assemble_root_filename(), '.dat')
        return Path(file_name)

    def get_mat_filename(self):
        sensor_file = {}
        for key, sensor in self.sensor_collection.items():
            file_name = 't{}{}{}'.format(self.assemble_root_filename(four_digit_year=True), key.lower(), '.mat')
            sensor_file[key] = file_name

        return sensor_file

    def get_save_folder(self):
        return '{}{}'.format('t', self.station_id)


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

    def all_equal(self, iterable):
        "Returns True if all the elements are equal to each other"
        g = groupby(iterable)
        return next(g, True) and not next(g, False)

    def get_sampling_rates(self):
        """
        Ensure that the sampling rate between sensors for different months is the same
        """

        # Collect all rates for each sensor for all months
        rates = defaultdict(list)
        for month in self.month_collection:
            for key, sensor in month.sensor_collection.sensors.items():
                if key != "ALL":
                    rates[key].append(sensor.rate)
        # Check if rates for each sensor are equal
        result = {}
        for sensor, rate in rates.items():
            result[sensor] = self.all_equal(rate)

        return result

    def is_sampling_inconsistent(self):
        return False in self.get_sampling_rates().values()

    def update_header_reference_level(self, date, new_level, sens):
        months_updated = 0
        for month in self.month_collection:
            # Todo: This should catch all months, even if the loaded months wrap into a new
            #  year, ie. we loaded month 11, 12, 1. But write a test for it
            if month.month >= date.month() or month.sensor_collection[sens].date.astype(
                    object).year > date.year():
                months_updated += 1
                ref_diff = month.sensor_collection.sensors[sens].get_reference_difference(new_level)
                new_header = month.sensor_collection.sensors[sens].update_header_ref(new_level)
                month.sensor_collection.sensors[sens].set_reference_height(new_level)
        return months_updated, ref_diff, new_header

class DataCollection:

    def __init__(self, station: Station = None):
        self.station = station
        self.sensors = self.combined_months()
