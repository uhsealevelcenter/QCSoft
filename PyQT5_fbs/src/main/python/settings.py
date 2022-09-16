from matplotlib.backends.qt_compat import QtCore

SETTINGS = QtCore.QSettings('UHSLC', 'com.uhslc.qcsoft')
print("MY SETTING FILENAME",SETTINGS.fileName())
LOAD_KEY = 'loadpath'
SAVE_KEY = 'savepath'
DIN_PATH = 'dinpath'
FD_PATH  = 'fdpath'
HF_PATH  = 'hfpath'


def get_path(str_key):
    if SETTINGS.contains(str_key):
        return SETTINGS.value(str_key)
    else:
        SETTINGS.setValue(str_key, '~')
        return SETTINGS.value(str_key)
