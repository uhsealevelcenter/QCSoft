from matplotlib.backends.qt_compat import QtCore, QtWidgets, QtGui
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s
try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig)

#https://stackoverflow.com/questions/18196799/how-can-i-show-a-pyqt-modal-dialog-and-get-data-out-of-its-controls-once-its-clo
class DateDialog(QtWidgets.QDialog):
    def __init__(self, parent = None):
        super(DateDialog, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel(self)
        label.setObjectName(_fromUtf8("label"))
        label.setText(_translate("RefWindow", "When was the reference level changed?", None))
        layout.addWidget(label)

        # nice widget for editing the date
        self.datetime = QtWidgets.QDateTimeEdit(self)
        self.datetime.setCalendarPopup(True)
        self.datetime.setDateTime(QtCore.QDateTime.currentDateTime())
        self.datetime.setDisplayFormat("yyyy-MM-dd HH:mm")
        layout.addWidget(self.datetime)

        # OK and Cancel buttons
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # get current date and time from the dialog
    def dateTime(self):
        return self.datetime.dateTime()

    # static method to create the dialog and return (date, time, accepted)
    @staticmethod
    def getDateTime(parent = None):
        dialog = DateDialog(parent)
        result = dialog.exec_()
        date = dialog.dateTime()
        return (date.date(), date.time(), result == QtWidgets.QDialog.Accepted)
