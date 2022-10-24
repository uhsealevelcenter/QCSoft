import calendar
from collections import defaultdict
from itertools import groupby
from pathlib import Path
from typing import Callable
from station_tools import filtering as filt

from station_tools import utils

import numpy as np
import glob
import os


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
        self.top_level_folder = None

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

    def assemble_ts_text(self):
        months = []
        for month in self.month_collection:
            prd_text = []
            others_text = []
            for key, sensor in month.sensor_collection.items():
                if key == "ALL":
                    continue
                id_sens = month.station_id + key
                id_sens = id_sens.rjust(8, ' ')
                year = str(sensor.date.astype(object).year)[-2:]
                year = year.rjust(4, ' ')
                m = "{:2}".format(sensor.date.astype(object).month)
                # day = "{:3}".format(sensor.date.astype(object).day)

                # To get the line counter, it is 60 minutes per hour x 24 hours in a day divided by data points
                # per row which can be obtained from .data.shape, and divided by the sampling rate. The number
                # given by that calculation tells after how many rows to reset the counter, that is how many rows of
                # data per day. This is true for all sensors besides PRD. PRD shows the actual hours (increments of
                # 3 per row)
                # TODO: ask Fee if there are any other sensors that have 15 minute sampling rate and check the
                # monp file if there is
                if key == "PRD":
                    line_count_multiplier = 3
                    prd_text.append(sensor.header)
                else:
                    line_count_multiplier = 1
                    others_text.append(sensor.header)
                for row, data_line in enumerate(sensor.data):
                    rows_per_day = 24 * 60 // sensor.data.shape[1] // int(sensor.rate)
                    line_num = (row % rows_per_day) * line_count_multiplier
                    day = 1 + (row // rows_per_day)
                    day = "{:3}".format(day)
                    line_num = "{:3}".format(line_num)
                    nan_ind = np.argwhere(np.isnan(data_line))
                    data_line[nan_ind] = 9999
                    sl_round_up = np.round(data_line).astype(
                        int)  # round up sealevel data and convert to int

                    # right justify with 5 spaces
                    spaces = 4
                    if int(sensor.rate) >= 5:
                        spaces = 5
                    data_str = ''.join([str(x).rjust(spaces, ' ') for x in sl_round_up])  # convert data to string
                    full_line_str = '{}{}{}{}{}{}'.format(id_sens, year, m, day, line_num, data_str)

                    if key == "PRD":
                        prd_text.append(full_line_str + "\n")
                    else:
                        others_text.append(full_line_str + "\n")

                # If there is data for sensor other than PRD append 9s at the nd
                if others_text:
                    others_text.append(80 * '9' + '\n')
            prd_text.append(80 * '9' + '\n')
            prd_text.extend(others_text)
            months.append([month, prd_text])
        return months

    def save_ts_files(self, text_collection, path=None, is_test_mode=False, callback: Callable = None):
        # text collection here refers to multiple text files for each month loaded
        success = []
        failure = []
        for text_file in text_collection:
            # text_file[0] is of type Month
            file_name = text_file[0].get_ts_filename()

            save_folder = text_file[0].get_save_folder()  # t + station_id
            save_path = utils.get_top_level_directory(parent_dir=path, is_test_mode=is_test_mode) / \
                        utils.HIGH_FREQUENCY_FOLDER / \
                        save_folder / str(
                text_file[0].year)
            utils.create_directory_if_not_exists(save_path)

            try:
                with open(Path(save_path / file_name), 'w') as the_file:
                    for lin in text_file[1]:
                        the_file.write(lin)
                    the_file.write(80 * '9' + '\n')
                    success.append({'title': "Success", 'message': "Success \n" + str(file_name) + " Saved to " +
                                                                   str(save_path) + "\n"})
            except IOError as e:
                failure.append({'title': "Error", 'message': "Cannot Save to " +
                                                             str(save_path) + "\n" + str(e) +
                                                             "\n Please select a different path to save to"})
        if callback:
            callback(success, failure)
        return success, failure

    def save_mat_high_fq(self, path: str, is_test_mode=False, callback: Callable = None):
        import scipy.io as sio

        success = []
        failure = []
        for month in self.month_collection:
            for key, sensor in month.sensor_collection.items():
                if key == "ALL":
                    continue
                sl_data = sensor.get_flat_data().copy()
                sl_data = utils.remove_9s(sl_data)
                sl_data = sl_data - int(sensor.height)
                time = filt.datenum2(sensor.get_time_vector())
                data_obj = [time, sl_data]

                file_name = month.get_mat_filename()[key]
                variable = file_name.split('.')[0]

                save_folder = month.get_save_folder()  # t + station_id
                save_path = utils.get_top_level_directory(parent_dir=path,
                                                       is_test_mode=is_test_mode) / utils.HIGH_FREQUENCY_FOLDER / \
                            save_folder / str(
                    month.year)
                utils.create_directory_if_not_exists(save_path)
                # transposing the data so that it matches the shape of the UHSLC matlab format
                matlab_obj = {'NNNN': variable, variable: np.transpose(data_obj, (1, 0))}
                try:
                    sio.savemat(Path(save_path / file_name), matlab_obj)
                    success.append(
                        {'title': "Success",
                         'message': "Success \n" + file_name + " Saved to " + str(save_path) + "\n"})
                except IOError as e:
                    failure.append({'title': "Error",
                                    'message': "Cannot Save to high frequency (.mat) data to" + str(
                                        save_path) + "\n" + str(
                                        e) + "\n Please select a different path to save to"})
        if callback:
            callback(success, failure)
        return success, failure

    def save_fast_delivery(self, din_path: str, path: str, is_test_mode=False, callback: Callable = None):
        # Todo: Refactor this into at least two more functions, one for daily fast deivery and one for hourly,
        #  each saving to both .mat and .dat
        import scipy.io as sio
        success = []
        failure = []
        for month in self.month_collection:
            data_obj = {}
            _data = month.sensor_collection.sensors
            station_num = month.station_id
            primary_sensor = filt.get_channel_priority(din_path, station_num)[
                0].upper()  # returns multiple sensor in order of importance
            if primary_sensor not in month.sensor_collection:
                failure.append({'title': "Error", 'message': "Your .din file says that {} "
                                                             "is the primary sensor but the file you have loaded does "
                                                             "not contain that sensor. Hourly and daily data will not be saved.".format(
                    primary_sensor)})
                return
            sl_data = _data[primary_sensor].get_flat_data().copy()
            sl_data = utils.remove_9s(sl_data)
            sl_data = sl_data - int(_data[primary_sensor].height)
            data_obj[primary_sensor.lower()] = {'time': filt.datenum2(_data[primary_sensor].get_time_vector()),
                                                'station': station_num, 'sealevel': sl_data}

            year = _data[primary_sensor].date.astype(object).year
            two_digit_year = str(year)[-2:]
            # month = _data[primary_sensor].date.astype(object).month

            #  Filter to hourly
            year_end = year
            month_end = month.month
            if month_end + 1 > 12:
                month_end = 1
                year_end = year + 1
            data_hr = filt.hr_process_2(data_obj, filt.datetime(year, month.month, 1, 0, 0, 0),
                                        filt.datetime(year_end, month_end + 1, 1, 0, 0, 0))

            # for channel parameters see filt.channel_merge function
            # We are not actually merging channels here (not needed for fast delivery)
            # But we still need to run the data through the merge function, even though we are only using one channel
            # in order to get the correct output data format suitable for the daily filter
            ch_params = [{primary_sensor.lower(): 0}]
            hourly_merged = filt.channel_merge(data_hr, ch_params)

            # Note that hourly merged returns a channel attribute which is an array of integers representing channel type.
            # used for a particular day of data. In Fast delivery, all the number should be the same because no merge
            # int -> channel name mapping is inside of filtering.py var_flag function
            data_day = filt.day_119filt(hourly_merged, self.location[0])

            month_str = "{:02}".format(month.month)

            save_folder = month.get_save_folder()  # t + station_id
            save_path = utils.get_top_level_directory(parent_dir=path,
                                                   is_test_mode=is_test_mode) / utils.FAST_DELIVERY_FOLDER / save_folder \
                        / str(
                month.year)
            utils.create_directory_if_not_exists(save_path)

            hourly_filename = str(save_path) + '/' + 'th' + str(station_num) + two_digit_year + month_str
            daily_filename = str(save_path) + '/' + 'da' + str(station_num) + two_digit_year + month_str

            monthly_mean = np.round(np.nanmean(data_day['sealevel'])).astype(int)

            hr_flat = np.concatenate(data_hr[primary_sensor.lower()]['sealevel'], axis=0)
            nan_ind_hr = np.argwhere(np.isnan(hr_flat))
            hr_flat[nan_ind_hr] = 9999
            sl_hr_round_up = np.round(hr_flat).astype(
                int)  # round up sealevel data and convert to int

            sl_hr_str = [str(x).rjust(5, ' ') for x in sl_hr_round_up]  # convert data to string

            # format the date and name strings to match the legacy daily .dat format
            month_str = str(month.month).rjust(2, ' ')
            station_name = month.station_id + self.name
            line_begin_str = '{}WOC {}{}'.format(station_name.ljust(7), year, month_str)
            counter = 1

            try:
                sio.savemat(daily_filename + '.mat', data_day)
                # Remove nans, replace with 9999 to match the legacy files
                nan_ind = np.argwhere(np.isnan(data_day['sealevel']))
                data_day['sealevel'][nan_ind] = 9999
                sl_round_up = np.round(data_day['sealevel']).astype(int)  # round up sealevel data and convert to int
                # right justify with 5 spaces
                sl_str = [str(x).rjust(5, ' ') for x in sl_round_up]  # convert data to string
                with open(daily_filename + '.dat', 'w') as the_file:
                    for i, sl in enumerate(sl_str):
                        if i % 11 == 0:
                            line_str = line_begin_str + str(counter) + " " + ''.join(sl_str[i:i + 11])
                            if counter == 3:
                                line_str = line_str.ljust(75)
                                final_str = line_str[:-(len(str(monthly_mean)) + 1)] + str(monthly_mean)
                                line_str = final_str
                            the_file.write(line_str + "\n")
                            counter += 1
                success.append({'title': "Success",
                                'message': "Success \n Daily Date Saved to " + str(save_path) + "\n"})
            except IOError as e:
                failure.append({'title': "Error",
                                'message': "Cannot Save Daily Data to " + daily_filename + "\n" + str(
                                    e) + "\n Please select a different path to save to"})

            # Save to legacy .dat hourly format
            metadata_header = '{}{}FSL{}  {} TMZONE=GMT    REF=00000 60 {} {} M {}'. \
                format(month.station_id,
                       self.name[0:3],
                       primary_sensor,
                       month.string_location,
                       month.name.upper(),
                       two_digit_year,
                       str(month.day_count))
            line_begin = '{}{} {} {}{}'.format(month.station_id,
                                               self.name[0:3],
                                               primary_sensor,
                                               str(year),
                                               str(month.month).rjust(2))

            day = 1
            counter = 0
            # Save hourly
            try:
                sio.savemat(hourly_filename + '.mat', data_hr)
                with open(hourly_filename + '.dat', 'w') as the_file:
                    the_file.write(metadata_header + "\n")
                    for i, sl in enumerate(sl_hr_str):
                        if i != 0 and i % 24 == 0:
                            counter = 0
                            day += 1
                        if i % 12 == 0:
                            counter += 1
                            line_str = line_begin + str(day).rjust(2) + str(counter) + ''.join(
                                sl_hr_str[i:i + 12]).rjust(5)
                            the_file.write(line_str + "\n")
                success.append({'title': "Success",
                                'message': "Success \n Hourly Data Saved to " + str(save_path) + "\n"})
            except IOError as e:
                failure.append({'title': "Error",
                                'message': "Cannot Save Hourly Data to " + hourly_filename + "\n" + str(
                                    e) + "\n Please select a different path to save to"})
        if callback:
            callback(success, failure)
        return success, failure

    def save_to_annual_file(self):
        ''' Loads all high frequency data for a station for a given year and saves it to a single file. One file per
        sensor.'''
        import scipy.io as sio
        #1) Get all high frequency .mat files for this year for this station
        # Beware of weird edge cases in which we might load month 12 and 1 for example
        #2) Load them into memory and append each sensor in the appropriate order
        #3) Save the annual file
        # Take care of cases when a new Sensor appears in a month or disappears
        # Todo: This is just a temporary solution, we should have a better way to handle this
        # We shouldn't be looking to only the first month to determine stuff
        month = self.month_collection[0]
        station_folder = month.get_save_folder()
        mat_files_path = self.top_level_folder / utils.PRODUCTION_DATA_TOP_FOLDER / utils.HIGH_FREQUENCY_FOLDER / \
                    station_folder / str(
            month.year)
        all_mat_files = sorted(glob.glob(str(mat_files_path)+'/*.mat'))
        sensors_set = set()
        months_sensor = {}
        # Next, Find all unique sensors letters in the file names:
        for file_name in all_mat_files:
            # Assuming that each sensor name is ALWAYS 3 letters long (not sure if a save assumption)
            sensor_name = file_name.split('.')[0][-3:]
            sensors_set.add(sensor_name)
            if sensor_name not in months_sensor:
                months_sensor[sensor_name] = [file_name]
            else:
                months_sensor[sensor_name].append(file_name)

        annual_mat_files_path = self.top_level_folder / utils.PRODUCTION_DATA_TOP_FOLDER / utils.HIGH_FREQUENCY_FOLDER / \
                         station_folder
        all_data = {}
        for sensor, file_name in months_sensor.items():
            for file in file_name:
                filename = file.split('/')[-1].split('.')[0]
                data = sio.loadmat(file)
                time = data[filename][:, 0]
                sealevel = data[filename][:, 1]
                if sensor not in all_data:
                    all_data[sensor] = {'time': [time], 'sealevel': [sealevel]}
                else:
                    all_data[sensor]['sealevel'] = np.append(all_data[sensor]['sealevel'], sealevel)
                    all_data[sensor]['time'] = np.append(all_data[sensor]['time'], time)
            data_obj = [all_data[sensor]['time'], all_data[sensor]['sealevel']]
            variable = station_folder + str(month.year) + sensor

            matlab_obj = {'NNNN': variable, variable: np.transpose(data_obj, (1, 0))}
            variable = Path(variable + '.mat')
            try:
                sio.savemat(Path(annual_mat_files_path / variable), matlab_obj)
            except IOError as e:
                print("Cannot Save Data to " + str(annual_mat_files_path) + "\n" + str(e) + "\n Please select a different path to save to")


class DataCollection:

    def __init__(self, station: Station = None):
        self.station = station
        self.sensors = self.combined_months()
