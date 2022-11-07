import glob
import os
from datetime import datetime
from pathlib import Path
from typing import List, Callable

import numpy as np

TEST_DATA_TOP_FOLDER = Path('test_data')
PRODUCTION_DATA_TOP_FOLDER = Path('production_data')
FAST_DELIVERY_FOLDER = Path('fast_delivery')
HIGH_FREQUENCY_FOLDER = Path('high_frequency')

ALL_MONTHS_NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]


def create_directory_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_top_level_directory(parent_dir, is_test_mode=False):
    # Subdirectory of parent_dir where production data is saved
    if not is_test_mode:
        directory = Path(parent_dir / PRODUCTION_DATA_TOP_FOLDER)
        if directory.is_dir():
            return directory
        else:
            create_directory_if_not_exists(directory)
            return directory
    # Subdirectory of parent_dir where test data is saved
    else:
        test_directory = Path(parent_dir / TEST_DATA_TOP_FOLDER)
        if test_directory.is_dir():
            return test_directory
        else:
            create_directory_if_not_exists(test_directory)
            return test_directory


def remove_9s(data):
    nines_ind = np.where(data == 9999)
    data[nines_ind] = float('nan')
    return data


def get_missing_months(month_list):
    """ Returns a list of missing months from a list of months. If there are no missing it returns an empty list. """
    missing_months = []
    if ALL_MONTHS_NUMBERS == month_list:
        return missing_months
    missing_months = list(set(ALL_MONTHS_NUMBERS) - set(month_list))
    missing_months.sort()
    return missing_months


def get_hf_mat_files(path: Path, full_name=False):
    """
    Returns an object of all sensor files at the given path as keys and
    a list of all the months in the file as values if full_name is False
    or a list of all the full file names if full_name is True.
    :param path:
    :return: {"<sensor_id>": ["01', '02', ...], ...} or {"<sensor_id>": ["<file_name_01>", "<file_name_02>", ...], ...}
    """
    all_mat_files = sorted(glob.glob(str(path) + '/*.mat'))
    sensor_months = {}  # sensors and a list of months they appear in
    for file_name_list in all_mat_files:
        # Assuming that each sensor name is ALWAYS 3 letters long (not sure if a safe assumption)
        sensor_name = file_name_list.split('.mat')[0][-3:]
        if full_name:
            value = file_name_list
        else:
            value = file_name_list.split('.mat')[0][-5:-3]
        # sensors_set.add(sensor_name)
        if sensor_name not in sensor_months:
            sensor_months[sensor_name] = [value]
        else:
            sensor_months[sensor_name].append(value)
    return sensor_months


def datenum2(date):
    # TO make it work numpy datetime
    obj = []
    for d in date:
        obj.append(366 + d.astype(datetime).toordinal() + (
                d.astype(datetime) - datetime.fromordinal(d.astype(datetime).toordinal())).total_seconds() / (
                           24 * 60 * 60))
    return obj


def datenum(d):
    """
    Python equivalent of the Matlab datenum function.

    Parameters:
    -----------
    d: datetime object (e.g. datetime(yr,mon,day,hr,min,sec))

    Returns:
    --------
    float: datetime object converted to Matlab epoch

    """
    return 366 + d.toordinal() + (d - datetime.fromordinal(d.toordinal())).total_seconds() / (24 * 60 * 60)


def pairwise_diff(lst):
    diff = 0
    result = []
    for i in range(len(lst) - 1):
        # subtracting the alternate numbers
        diff = lst[i] - lst[i + 1]
        result.append(diff)
    return result


def is_valid_files(files: List[str], callback: Callable = None):
    dates = []
    names = []
    result = []
    success = []
    failure = []
    # extract dates and station 4 letter codes for every file that was loaded
    for file in files[0]:
        if file[-8:-4].isdigit():
            dates.append(int(file[-8:-4]))
            # check if monp file or a TS file
            if file.split("/")[-1][0] == "s":
                names.append(file.split("/")[-1][1:5])
            else:
                names.append(file.split("/")[-1][0:4])
    # check the difference between all dates
    # if the difference is not 1, then the files are not adjacent months
    for val in pairwise_diff(dates):
        # if we want the adjacent month from the adjacent year then need to add
        # check for -89 as well (and val != -89)
        if val != -1:
            result.append(val)
            failure.append({'title': "Error",
                            'message': "The months loaded are not adjacent or they are not properly sorted."})
    # check if the files selected are all from the same station
    if names[1:] != names[:-1]:
        failure.append({'title': "Error",
                        'message': "Files selected are all not from the same station"})
        return False

    success.append({'title': 'Success',
                    'message': "Files successfully loaded"})
    if callback:
        callback(success, failure)

    return len(result) == 0
