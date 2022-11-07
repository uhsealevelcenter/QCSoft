import os

from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin
from PyQt5.QtGui import QIcon
from matplotlib import rcParams
from switchwidget import SwitchWidget

rcParams['font.size'] = 9


class SwitchPlugin(QPyDesignerCustomWidgetPlugin):
    def __init__(self, parent=None):
        super(SwitchPlugin, self).__init__(parent)
        self._initialized = False

    def initialize(self, editor):
        self._initialized = True

    def isInitialized(self):
        return self._initialized

    def createWidget(self, parent):
        return SwitchWidget(parent)

    def name(self):
        return 'SwitchWidget'

    def group(self):
        return 'PyQt'

    def icon(self):
        return QIcon(os.path.join(
            rcParams['datapath'], 'images', 'matplotlib.png'))

    def toolTip(self):
        return ''

    def whatsThis(self):
        return ''

    def isContainer(self):
        return False

    def domXml(self):
        return '<widget class="SwitchWidget" name="switchwidget">\n' \
               '</widget>\n'

    def includeFile(self):
        return 'switchwidget'
