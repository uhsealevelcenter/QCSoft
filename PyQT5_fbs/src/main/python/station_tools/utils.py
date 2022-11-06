import os
from datetime import datetime
from pathlib import Path

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
