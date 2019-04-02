import sys
from PyQt5 import QtGui, QtCore, QtWidgets

class mymainwindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)

app = QtWidgets.QApplication(sys.argv)
mywindow = mymainwindow()
mywindow.show()
app.exec_()
