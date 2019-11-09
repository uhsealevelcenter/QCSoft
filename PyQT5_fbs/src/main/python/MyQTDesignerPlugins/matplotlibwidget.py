from PyQt5.QtCore import QSize
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QSizePolicy
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib import rcParams

rcParams['font.size'] = 9


# class MatplotlibWidget(Canvas):
#     def __init__(self, parent=None, title='', xlabel='', ylabel='',
#                  xlim=None, ylim=None, xscale='linear', yscale='linear',
#                  width=4, height=3, dpi=100):
#         self.figure = Figure(figsize=(width, height), dpi=dpi)
#         self.toolbar = NavigationToolbar2QT(self.canvas,self)
#         self.toolbar.update()
#         self.axes = self.figure.add_subplot(111)
#         self.axes.set_title(title)
#         self.axes.set_xlabel(xlabel)
#         self.axes.set_ylabel(ylabel)
#         if xscale is not None:
#             self.axes.set_xscale(xscale)
#         if yscale is not None:
#             self.axes.set_yscale(yscale)
#         if xlim is not None:
#             self.axes.set_xlim(*xlim)
#         if ylim is not None:
#             self.axes.set_ylim(*ylim)
#
#         super(MatplotlibWidget, self).__init__(self.figure)
#         self.setParent(parent)
#         super(MatplotlibWidget, self).setSizePolicy(
#             QSizePolicy.Expanding, QSizePolicy.Expanding)
#         super(MatplotlibWidget, self).updateGeometry()
#
#     def sizeHint(self):
#         return QSize(*self.get_width_height())
#
#     def minimumSizeHint(self):
#         return QSize(10, 10)

class MplCanvas(Canvas):

    def __init__( self ):
        self.fig = Figure()
        self.ax = self.fig.add_subplot( 111 )

        Canvas.__init__( self, self.fig )
        Canvas.setSizePolicy( self, QSizePolicy.Expanding,QSizePolicy.Expanding )
        Canvas.updateGeometry( self )

    def sizeHint(self):
        return QSize(*self.get_width_height())

    def minimumSizeHint(self):
        return QSize(10, 10)


class MatplotlibWidget(QtWidgets.QWidget):

    def __init__( self, parent = None ):
        QtWidgets.QWidget.__init__( self, parent )
        self.canvas = MplCanvas() #create canvas that will hold our plot
        self.navi_toolbar = NavigationToolbar2QT(self.canvas, self) #createa navigation toolbar for our plot canvas

        self.vbl = QtWidgets.QVBoxLayout()
        self.vbl.addWidget(self.navi_toolbar)
        self.vbl.addWidget( self.canvas )

        self.setLayout( self.vbl )
