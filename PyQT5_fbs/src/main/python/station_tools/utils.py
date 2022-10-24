import os
from pathlib import Path

import numpy as np

TEST_DATA_TOP_FOLDER = Path('test_data')
PRODUCTION_DATA_TOP_FOLDER = Path('production_data')
FAST_DELIVERY_FOLDER = Path('fast_delivery')
HIGH_FREQUENCY_FOLDER = Path('high_frequency')


def create_directory_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_top_level_directory(parent_dir, is_test_mode=False):
    # parent_dir = Path(st.get_path(st.SAVE_KEY))
    # Directory where production data is saved
    if not is_test_mode:
        directory = Path(parent_dir / PRODUCTION_DATA_TOP_FOLDER)
        if directory.is_dir():
            return directory
        else:
            create_directory_if_not_exists(directory)
            return directory
    # Directory where test data is saved
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