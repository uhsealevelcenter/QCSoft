from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QObject, QSize, QPointF, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSlot, Qt
from PyQt5.QtGui import QPainter, QPalette, QLinearGradient, QGradient, QColor
from PyQt5.QtWidgets import QAbstractButton


class SwitchPrivate(QObject):
    def __init__(self, q, parent=None):
        QObject.__init__(self, parent=parent)
        self.button = QColor(10, 240, 10)
        self.mPointer = q
        self.mPosition = 0.0
        self.mGradient = QLinearGradient()
        self.mGradient.setSpread(QGradient.PadSpread)

        self.animation = QPropertyAnimation(self)
        self.animation.setTargetObject(self)
        self.animation.setPropertyName(b'position')
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.InOutExpo)

        self.animation.finished.connect(self.mPointer.update)

    @pyqtProperty(float)
    def position(self):
        return self.mPosition

    @position.setter
    def position(self, value):
        self.mPosition = value
        self.mPointer.update()

    def draw(self, painter):
        r = self.mPointer.rect()
        margin = r.height() / 10
        shadow = self.mPointer.palette().color(QPalette.Dark)
        light = self.mPointer.palette().color(QPalette.Light)
        # button = self.mPointer.palette().color(QPalette.Button)
        painter.setPen(Qt.NoPen)

        self.mGradient.setColorAt(0, shadow.darker(130))
        self.mGradient.setColorAt(1, light.darker(130))
        self.mGradient.setStart(0, r.height())
        self.mGradient.setFinalStop(0, 0)
        painter.setBrush(self.mGradient)
        painter.drawRoundedRect(r, r.height() / 2, r.height() / 2)

        self.mGradient.setColorAt(0, shadow.darker(140))
        self.mGradient.setColorAt(1, light.darker(160))
        self.mGradient.setStart(0, 0)
        self.mGradient.setFinalStop(0, r.height())
        painter.setBrush(self.mGradient)
        painter.drawRoundedRect(r.adjusted(margin, margin, -margin, -margin), r.height() / 2, r.height() / 2)

        self.mGradient.setColorAt(0, self.button.darker(130))
        self.mGradient.setColorAt(1, self.button)

        painter.setBrush(self.mGradient)

        x = r.height() / 2.0 + self.mPosition * (r.width() - r.height())
        painter.drawEllipse(QPointF(x, r.height() / 2), r.height() / 2 - margin, r.height() / 2 - margin)

    @pyqtSlot(bool, name='animate')
    def animate(self, checked):
        self.animation.setDirection(QPropertyAnimation.Forward if checked else QPropertyAnimation.Backward)
        self.animation.start()
        if checked:
            self.button = QColor(230, 50, 0)
        else:
            self.button = QColor(10, 240, 10)

    def __del__(self):
        del self.animation


class Switch(QAbstractButton):
    def __init__(self, parent=None):
        QAbstractButton.__init__(self, parent=parent)
        self.dPtr = SwitchPrivate(self)
        self.setCheckable(True)
        self.label = QtWidgets.QLabel(self)
        self.label.setToolTip("Files will be saved to production folder")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.label.setText(QtCore.QCoreApplication.translate("MainWindow", "Production"))
        self.clicked.connect(self.dPtr.animate)

    def sizeHint(self):
        return QSize(84, 84)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.dPtr.draw(painter)

    def resizeEvent(self, event):
        self.update()

    def __del__(self):
        del self.dPtr


class SwitchWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.button = Switch()  # create switch
        self.button.setToolTip("Files will be saved to production folder")
        self.button.setMinimumHeight(40)
        self.vbl = QtWidgets.QVBoxLayout()

        self.vbl.addWidget(self.button.label)
        self.vbl.addWidget(self.button)
        self.setLayout(self.vbl)

        self.button.clicked.connect(self.on_clicked)

    def on_clicked(self, checked):
        text = 'Test' if checked else 'Production'
        tooltip_text = 'Files will be saved to test folder' if checked else 'Files will be saved to production ' \
                                                                            'folder'
        self.button.label.setText(QtCore.QCoreApplication.translate("MainWindow", text))
        self.button.setToolTip(tooltip_text)
        self.button.label.setToolTip(tooltip_text)
