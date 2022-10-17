from pathlib import Path

from matplotlib.backends.qt_compat import QtCore

SETTINGS = QtCore.QSettings('UHSLC', 'com.uhslc.qcsoft')
LOAD_KEY = 'loadpath'
SAVE_KEY = 'savepath'
DIN_PATH_KEY = 'dinpath'
FD_PATH_KEY = 'fdpath'
HF_PATH_KEY = 'hfpath'
TEST_PATH_KEY = 'testpath'
PRODUCTION_PATH_KEY = 'productionpath'
TEST_DATA_TOP_FOLDER = Path('test_data')
PRODUCTION_DATA_TOP_FOLDER = Path('production_data')
FAST_DELIVERY_FOLDER = Path('fast_delivery')
HIGH_FREQUENCY_FOLDER = Path('high_frequency')


def get_path(str_key):
    if SETTINGS.contains(str_key):
        return SETTINGS.value(str_key)
    else:
        SETTINGS.setValue(str_key, '~')
        return SETTINGS.value(str_key)
