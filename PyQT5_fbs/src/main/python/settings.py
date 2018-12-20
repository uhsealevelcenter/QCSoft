from matplotlib.backends.qt_compat import QtCore

SETTINGS = QtCore.QSettings('UHSLC', 'com.uhslc.qcsoft')
LOAD_KEY = "loadpath"
SAVE_KEY = "savepath"

def getPath(str_key):
    return SETTINGS.value(str_key)
