from matplotlib.backends.qt_compat import QtCore

SETTINGS = QtCore.QSettings('UHSLC', 'com.uhslc.qcsoft')
LOAD_KEY = 'loadpath'
SAVE_KEY = 'savepath'
DIN_PATH = 'dinpath'
FD_PATH  = 'fdpath'
HF_PATH  = 'hfpath'


def get_path(str_key):
    return SETTINGS.value(str_key)
