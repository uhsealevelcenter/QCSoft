

import numpy as np
from matplotlib.backends.qt_compat import QtCore

SETTINGS = QtCore.QSettings('UHSLC', 'com.uhslc.qcsoft')
LOAD_KEY = 'loadpath'
SAVE_KEY = 'savepath'
DIN_PATH_KEY = 'dinpath'
FD_PATH_KEY = 'fdpath'
HF_PATH_KEY = 'hfpath'
TEST_PATH_KEY = 'testpath'
PRODUCTION_PATH_KEY = 'productionpath'



def get_path(str_key):
    if SETTINGS.contains(str_key):
        return SETTINGS.value(str_key)
    else:
        SETTINGS.setValue(str_key, '~')
        return SETTINGS.value(str_key)
