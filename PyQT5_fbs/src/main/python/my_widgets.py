from matplotlib.backends.qt_compat import QtCore, QtWidgets, QtGui, is_pyqt5

import os

import numpy as np
from interactive_plot import PointBrowser
from sensor import Sensor, Station
from extractor2 import DataExtractor
from dialogs import DateDialog
import settings as st
import pandas._libs.tslibs.np_datetime
import pandas._libs.tslibs.nattype
import pandas._libs.skiplist
from pandas import Series, date_range
import filtering as filt
from uhslcdesign import Ui_MainWindow
from PyQt5.QtWidgets import QMainWindow


if is_pyqt5():
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
else:
    from matplotlib.backends.backend_qt4agg import (
            FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

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

class HelpScreen(QtWidgets.QWidget):

    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(HelpScreen, self).__init__(parent)

        # Object for data persistence
        # self.settings = QtCore.QSettings('UHSLC', 'com.uhslc.qcsoft')
        # st.SETTINGS.remove("savepath")

        self.layout = QtWidgets.QVBoxLayout()

        l1 = QtWidgets.QLabel()
        l2 = QtWidgets.QLabel()

        fontTitle = QtGui.QFont()
        fontTitle.setPointSize(16)
        fontTitle.setBold(True)
        fontTitle.setWeight(75)

        fontTitlePara = QtGui.QFont()
        fontTitlePara.setPointSize(12)
        fontTitlePara.setBold(False)
        fontTitlePara.setWeight(50)

        l1.setFont(fontTitle)
        l2.setFont(fontTitlePara)
        l1.setText("Program manual")
        l2.setText(
        '''
        INITIAL SETUP:
        -------------
        To save/load files to/from a server, connect to a server first (e.g CMD + K on a MAC,
        WIN + R on Windows), and then follow the instruction below:
        1) Specify the default loading folder by clicking "Change Load Folder" button
        2) Specify the default saving folder by clicking "Change Save Folder" button

        If no path is specified, the path will default to your home directory

        DATA LOADING:
        -------------
        Press CTRL (CMD) + O to load data unprocessed (monp) data
        Press CTRL (CMD) + T to load data processed (ts) data
        Press CTRL (CMD) + R to reload the same data file and undo all changes

        DATA MANIPULATION:
        -----------------
        To delete a single data point press "D"
        To delete multiple data points use right mouse click (or CTRL + Left Click) to circle the points
        To change a reference level for a specific channel, enter a new reference level in "Enter New Reference Level" text box
        and then click "Change Ref Level" button. This will prompt you with a calendar and time selector to choose a point when an
        adjustment to the reference level was made (usually supplied by technicians). The time/date selector can be modified
        incrementally by using UP/DOWN arrows or simply by clicking the desired time/date portion to be changed and typing in
        the time of change. Using TAB will scroll through year-month-day hour:minute sections.

        DATA NAVIGATION:
        ----------------
        Use LEFT and RIGHT arrow to pan through the data
        Press "B" to scroll backward through the individual data points
        Press "N" to scroll forward through the individual data points
        Click on any particular data point to zoom in on that data section
        Press "0" to reset the view back to the entire data set

        UNDO ACTIONS:
        -------------
        Press CTRL (CMD) + Z to undo data deletion
        Press CTRL (CMD) + B to undo bulk data deletion

        SAVE DATA:
        ----------
        Click the "SAVE" button to save changes to a "TS" file
        '''
        )
        l1.setAlignment(QtCore.Qt.AlignCenter)
        l2.setAlignment(QtCore.Qt.AlignTop)

        self.layout.addWidget(l1)
        self.layout.addStretch()
        self.layout.addWidget(l2)


        self.lineEditPath = QtWidgets.QLineEdit()
        self.lineEditPath.setObjectName(_fromUtf8("lineEditPath"))
        self.lineEditPath.setDisabled(True)
        self.lineEditPath.setFixedWidth(280)

        # If a save path hasn't been defined, give it a home directory
        if(st.get_path(st.SAVE_KEY)):
            self.lineEditPath.setPlaceholderText(st.get_path(st.SAVE_KEY))
        else:
            st.SETTINGS.setValue(st.SAVE_KEY,os.path.expanduser('~'))
            self.lineEditPath.setPlaceholderText(os.path.expanduser('~'))

        self.layout.addWidget(self.lineEditPath)

        saveButton = QtWidgets.QPushButton("Change Save Folder")
        saveButton.setFixedWidth(180)
        self.layout.addWidget(saveButton)



        self.lineEditLoadPath = QtWidgets.QLineEdit()
        self.lineEditLoadPath.setObjectName(_fromUtf8("lineEditLoadPath"))
        self.lineEditLoadPath.setPlaceholderText(st.get_path(st.LOAD_KEY))
        self.lineEditLoadPath.setDisabled(True)
        self.lineEditLoadPath.setFixedWidth(280)


        self.layout.addWidget(self.lineEditLoadPath)

        loadButton = QtWidgets.QPushButton("Change Load Folder")
        loadButton.setFixedWidth(180)
        self.layout.addWidget(loadButton)


        button = QtWidgets.QPushButton("Back to main")
        self.layout.addWidget(button)


        self.layout.addStretch()
        # self.button1 = QtWidgets.QPushButton("Button 1")
        # self.layout.addWidget(self.button1)
        #
        # self.button2 = QtWidgets.QPushButton("Button 2")
        # self.layout.addWidget(self.button2)

        self.setLayout(self.layout)
        button.clicked.connect(self.clicked.emit)
        saveButton.clicked.connect(lambda: self.savePath(self.lineEditPath,st.SAVE_KEY))
        loadButton.clicked.connect(lambda: self.savePath(self.lineEditLoadPath,st.LOAD_KEY))

    def savePath(self, lineEditObj, setStr):
        folder_name = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select a Folder')
        if(folder_name):
            st.SETTINGS.setValue(setStr, folder_name)
            st.SETTINGS.sync()
            lineEditObj.setPlaceholderText(st.get_path(setStr))
            lineEditObj.setText("")
        else:
            pass

class QHLine(QtWidgets.QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)

class Start(QMainWindow):

    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(Start, self).__init__()
        self.ui = parent
        self.sens_objects = {} ## Collection of Sensor objects for station for one month
        self.home()

    def home(self):
        print("HOME CALLED")
        # print("static_canvas",self.static_canvas)
        self.ui.mplwidget_top.canvas.figure.clf()
        self.ui.mplwidget_bottom.canvas.figure.clf()
        self._static_ax = self.ui.mplwidget_top.canvas.figure.subplots()
        self._static_fig = self.ui.mplwidget_top.canvas.figure
        self.pid = -99
        self.cid = -98
        self.toolbar1 = self._static_fig.canvas.toolbar #Get the toolbar handler
        self.toolbar1.update() #Update the toolbar memory
        # self._residual_fig = self.ui.mplwidget_bottom.canvas.figure
        self._residual_ax = self.ui.mplwidget_bottom.canvas.figure.subplots()
        self.ui.save_btn.clicked.connect(self.save_to_ts_files)

    def make_sensor_buttons(self, sensors):
        # Remove all sensor checkbox widgets from the layout
        # every time new data is loaded
        for i in range(self.ui.verticalLayout_left_top.count()):
            item = self.ui.verticalLayout_left_top.itemAt(i)
            # self.verticalLayout_left_top.removeWidget(item.widget())
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for i in range(self.ui.verticalLayout_bottom.count()):
            item = self.ui.verticalLayout_bottom.itemAt(i)
            # self.verticalLayout_left_top.removeWidget(item.widget())
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # sensors' keys are names of all sensors which carry
        # all of the data associated with it
        # Make copy of it so we can use its keys and assign radio buttons to it
        # If we do not make a copy then the  sensors values would get
        # overwritten by radio button objects
        self.sensor_dict = dict(sensors)
        self.sensor_dict2 = dict(sensors)

        # Counter added to figure out when the last item was added
        # Set alignment of the last item to push all the radio buttons up
        counter = len(sensors.items())
        for key,value in sensors.items():
            counter -= 1
            self.sensor_radio_btns = QtWidgets.QRadioButton(key, self)
            self.sensor_check_btns = QtWidgets.QCheckBox(key, self)
            self.sensor_dict[key] = self.sensor_radio_btns
            self.sensor_dict2[key] = self.sensor_check_btns
            self.ui.buttonGroup_data.addButton(self.sensor_dict[key])
            self.ui.buttonGroup_residual.addButton(self.sensor_dict2[key])
            if(counter>0):
                self.ui.verticalLayout_left_top.addWidget(self.sensor_dict[key])
                self.ui.verticalLayout_bottom.addWidget(self.sensor_dict2[key])
            else:
                self.ui.verticalLayout_left_top.addWidget(self.sensor_dict[key],0, QtCore.Qt.AlignTop)
                self.ui.verticalLayout_bottom.addWidget(self.sensor_dict2[key],0, QtCore.Qt.AlignTop)

            self.sensor_dict[key].setText(key)

        # radio_btn_HF = QtWidgets.QRadioButton("Minute", self)
        # radio_btn_HF.setChecked(True)
        self.mode = self.ui.radioButton_Minute.text()

        self.sensor_dict["PRD"].setChecked(True)
        self.sens_str = "PRD"
        # self.sensor_dict2["PRD"].setEnabled(False)
        self.sensor_dict2["ALL"].setEnabled(False)
        self.plot(all=False)
        self.ui.buttonGroup_data.buttonClicked.connect(self.on_sensor_changed)
        self.ui.buttonGroup_residual.buttonClicked.connect(self.on_residual_sensor_changed)
        self.ui.buttonGroup_resolution.buttonClicked.connect(self.on_frequency_changed)

    def on_sensor_changed(self, btn):
        print (btn.text())
        if(btn.text() == "ALL"):
            # TODO: plot_all and plot should be merged to one function
            self.ui.save_btn.setEnabled(False)
            self.ui.ref_level_btn.setEnabled(False)
            self.plot(all=True)
        else:
            self.ui.save_btn.setEnabled(True)
            self.ui.ref_level_btn.setEnabled(True)
            self.sens_str = btn.text()
            self._update_top_canvas(btn.text())
            self.ui.lineEdit.setText(self.sens_objects[self.sens_str].header[0])
            self.update_graph_values()

        # Update residual buttons and graph when the top sensor is changed
        # self.on_residual_sensor_changed(None)
        # Clear residual buttons and graph when the top sensor is changed
        for button in self.ui.buttonGroup_residual.buttons():
            button.setChecked(False)
        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()
        # print("ref height:",self.sens_objects[self.sens_str].height)

    def on_frequency_changed(self, btn):
        print ("Frequency changed",btn.text())
        self.mode = btn.text()
        if(self.mode == "Minute"):
            self.sensor_dict2["PRD"].setEnabled(True)
        else:
            self.sensor_dict2["PRD"].setEnabled(False)
        self.on_residual_sensor_changed()

    def update_graph_values(self):
        # convert 'nans' back to 9999s
        nan_ind = np.argwhere(np.isnan(self.browser.data))
        self.browser.data[nan_ind] = 9999
        # we want the sensor data object to point to self.browser.data and not self.browser.data.copy()
        # because when the self.browser.data is modified on the graph
        # the sensor data object will automatically be modified as well
        self.sens_objects[self.sens_str].data = self.browser.data

    def on_residual_sensor_changed(self):
        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()

        checkedItems = [button for button in self.ui.buttonGroup_residual.buttons() if button.isChecked()]
        if(checkedItems):
            for button in checkedItems:
                self.calculate_and_plot_residuals(self.sens_str, button.text(), self.mode)
        else:
            self._residual_ax.cla()
            self._residual_ax.figure.canvas.draw()

    def plot(self, all=False):
        # Set the data browser object to NoneType on every file load
        self.browser = None
        self._static_ax.cla()
        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()

        if all:
            lineEditText = 'No Header -- Plotting all sensors'
            sens_objects = self.sens_objects
            title = 'Relative levels = signal - average over selected period'
        else:
            lineEditText = self.sens_objects[self.sens_str].header[0]
            sens_objects = [self.sens_str]
            title = 'Tide Prediction'
        self.ui.lineEdit.setText(lineEditText)
        for sens in sens_objects:
            ## Set 9999s to NaN so they don't show up on the graph
            ## when initially plotted
            ## nans are converted back to 9999s when file is saved
            if sens == "ALL":
                pass
            else:
                data_flat = self.sens_objects[sens].get_flat_data()
                time = self.sens_objects[sens].get_time_vector()
                nines_ind = np.where(data_flat == 9999)
                data_flat[nines_ind] = float('nan')
                if all:
                    mean = np.nanmean(data_flat)
                else:
                    mean = 0
                # t = np.linspace(0, 10, 501)
                # t = np.arange(data.size)

                t = time
                y = data_flat - mean
                # self._static_ax.plot(t, np.tan(t), ".")
                line, = self._static_ax.plot(t, y, '-', picker=5,lw=0.5,markersize=3)  # 5 points tolerance
                # self._static_fig = self.static_canvas.figure
                if all:
                    line.set_label(sens)
                    self._static_ax.legend()
                self._static_ax.set_title(title)

                self._static_ax.autoscale(enable=True, axis='both', tight=True)
                self._static_ax.set_xlim([t[0], t[-1]])
                self._static_ax.margins(0.05, 0.05)

                self.ui.mplwidget_top.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
                self.ui.mplwidget_top.canvas.setFocus()
                self.ui.mplwidget_top.canvas.figure.tight_layout()
                # self.toolbar1 = self._static_fig.canvas.toolbar #Get the toolbar handler
                self.toolbar1.update() #Update the toolbar memory
                self.ui.mplwidget_top.canvas.draw()

    def calculate_and_plot_residuals(self, sens_str1, sens_str2, mode):
        # resample_freq = min(int(self.sens_objects[sens_str1].rate), int(self.sens_objects[sens_str2].rate))
        # _freq = str(resample_freq)+'min'
        #
        # # Get a date range to create pandas time Series
        # # using the sampling frequency of the sensor
        # rng1 = date_range(self.sens_objects[sens_str1].date, periods = self.sens_objects[sens_str1].data.size, freq=_freq)
        # ts1 = Series(self.sens_objects[sens_str1].data, rng1)
        #
        # rng2 = date_range(self.sens_objects[sens_str2].date, periods = self.sens_objects[sens_str2].data.size, freq=_freq)
        # ts2 = Series(self.sens_objects[sens_str2].data, rng2)

        # resample the data and linearly interpolate the missing values
        # upsampled = ts.resample(_freq)
        # interp = upsampled.interpolate()
        if mode == "Hourly":
            data_obj ={}
            # data_obj["prd"]={'time':filt.datenum2(self.sens_objects["PRD"].get_time_vector()), 'station':'014', 'sealevel':self.sens_objects["PRD"].get_flat_data().copy()}
            # for key in self.sens_objects.keys():
            #     print("KEY", key)
            sl_data = self.sens_objects[sens_str1].get_flat_data().copy()
            sl_data = self.remove_9s(sl_data)
            sl_data = sl_data - int(self.sens_objects[sens_str1].height)
            data_obj[sens_str1.lower()]={'time':filt.datenum2(self.sens_objects[sens_str1].get_time_vector()), 'station':'014', 'sealevel':sl_data}

            sl_data2 = self.sens_objects[sens_str2].get_flat_data().copy()
            sl_data2 = self.remove_9s(sl_data2)
            sl_data2 = sl_data2 - int(self.sens_objects[sens_str2].height)
            data_obj[sens_str2.lower()]={'time':filt.datenum2(self.sens_objects[sens_str2].get_time_vector()), 'station':'014', 'sealevel':sl_data2}

            year = self.sens_objects[sens_str2].date.astype(object).year
            month = self.sens_objects[sens_str2].date.astype(object).month
            data_hr = filt.hr_process_2(data_obj, filt.datetime(year,month,1,0,0,0), filt.datetime(year,month+1,1,0,0,0))


            if sens_str1 != "PRD":
                hr_resid = data_hr[sens_str1.lower()]["sealevel"]-data_hr[sens_str2.lower()]["sealevel"]
                time = [ filt.matlab2datetime(tval[0]) for tval in data_hr[list(data_hr.keys())[0]]['time'] ]
                self.generic_plot(self.ui.mplwidget_bottom.canvas, time, hr_resid,sens_str1,sens_str2,"Hourly Residual", is_interactive = False)
            else:
                self.show_custom_message("Warning", "For hourly residual an actual channel needs to be selected in the top plot.")
                self.generic_plot(self.ui.mplwidget_bottom.canvas, [0], [0],sens_str1,sens_str2,"Choose a channel in the top plot other than PRD", is_interactive = False)

        else:
            newd1 = self.resample2(sens_str1)
            newd2 = self.resample2(sens_str2)
            # newd1 = ts1.resample(_freq).interpolate()
            # newd2 = ts2.resample(_freq).interpolate()
            if(newd1.size>newd2.size):
                resid = newd2 - newd1[:newd2.size]
            else:
                resid = newd1 - newd2[:newd1.size]

            # time = np.array([self.sens_objects[sens_str1].date + np.timedelta64(i*int(1), 'm') for i in range(resid.size)])
            # time = np.arange(resid.size)
            time = date_range(self.sens_objects[sens_str1].date, periods = resid.size, freq='1min')
            self.generic_plot(self.ui.mplwidget_bottom.canvas, time, resid,sens_str1,sens_str2, "Residual", is_interactive = False)

    def generic_plot(self, canvas, x, y,sens1, sens2, title, is_interactive):
        print("GENERIC PLOT CALLED")
        # self._residual_ax = canvas.figure.subplots()

        line, = self._residual_ax.plot(x, y, '-', picker=5,lw=0.5,markersize=3)  # 5 points tolerance
        line.set_gid(sens2)
        self._residual_fig = canvas.figure
        self._residual_ax.set_title(title)
        line.set_label(title+": "+sens1+" - "+sens2)
        self._residual_ax.autoscale(enable=True, axis='both', tight=True)
        self._residual_ax.set_xlim([x[0], x[-1]])
        self._residual_ax.margins(0.05, 0.05)
        self._residual_ax.legend()

        if(is_interactive):
            self.browser = PointBrowser(x,y,self._residual_ax,line,self._residual_fig, self.find_outliers(x, y, sens1))
            self.browser.onDataEnd += self.show_message
            canvas.mpl_connect('pick_event', self.browser.onpick)
            canvas.mpl_connect('key_press_event', self.browser.onpress)
            ## need to activate focus onto the mpl canvas so that the keyboard can be used
            canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
            canvas.setFocus()

        self._residual_ax.figure.tight_layout()
        self.toolbar2 = self._residual_fig.canvas.toolbar #Get the toolbar handler
        self.toolbar2.update() #Update the toolbar memory

        self._residual_ax.figure.canvas.draw()


    def _update_top_canvas(self, sens):
        data_flat = self.sens_objects[sens].get_flat_data()
        nines_ind = np.where(data_flat == 9999)
        # nonines_data = data_flat.copy()
        # nonines_data[nines_ind] = float('nan')
        # data_flat = nonines_data
        # data_flat =data_flat - np.nanmean(data_flat)
        if(len(nines_ind[0])<data_flat.size):
            # data_flat[nines_ind] = float('nan')
            pass
        else:
            self.show_custom_message("Warning", "The following sensor has no data")
        self._static_ax.clear()
        # disconnect canvas pick and press events when a new sensor is selected
        # to eliminate multiple callbacks on sensor change
        # self.static_canvas.mpl_disconnect(self.pidP)
        # self.static_canvas.mpl_disconnect(self.cidP)
        self.ui.mplwidget_top.canvas.mpl_disconnect(self.pid)
        self.ui.mplwidget_top.canvas.mpl_disconnect(self.cid)
        if self.browser:
            self.browser.onDataEnd -= self.show_message
            self.browser.disconnect()
        # time = np.arange(data_flat.size)
        time = self.sens_objects[sens].get_time_vector()
        self.line, = self._static_ax.plot(time, data_flat, '-', picker=5,lw=0.5,markersize=3)

        self._static_ax.set_title('select a point you would like to remove and press "D"')
        self.browser = PointBrowser(time,data_flat,self._static_ax,self.line,self._static_fig, self.find_outliers(time, data_flat, sens) )
        self.browser.onDataEnd += self.show_message
        self.browser.on_sensor_change_update()
        # update event ids so that they can be disconnect on next sensor change
        self.pid = self.ui.mplwidget_top.canvas.mpl_connect('pick_event', self.browser.onpick)
        self.cid  = self.ui.mplwidget_top.canvas.mpl_connect('key_press_event', self.browser.onpress)
        ## need to activate focus onto the mpl canvas so that the keyboard can be used
        self.toolbar1.update()
        self.ui.mplwidget_top.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.ui.mplwidget_top.canvas.setFocus()

    def find_outliers(self, t, data, sens):

        channel_freq = self.sens_objects[sens].rate
        _freq = channel_freq+'min'


        nines_ind = np.where(data == 9999)
        nonines_data = data.copy()
        nonines_data[nines_ind] = float('nan')
        # Get a date range to create pandas time Series
        # using the sampling frequency of the sensor
        rng = date_range(t[0], t[-1], freq=_freq)
        ts = Series(nonines_data, rng)

        # resample the data and linearly interpolate the missing values
        upsampled = ts.resample(_freq)
        interp = upsampled.interpolate()

        # calculate a window size for moving average routine so the window
        # size is always 60 minutes long
        window_size = 60//int(channel_freq)

        # calculate moving average including the interolated data
        # moving_average removes big outliers before calculating moving average
        y_av = self.moving_average(np.asarray(interp.tolist()), window_size)
        # y_av = self.moving_average(data, 30)
        # missing=np.argwhere(np.isnan(y_av))
        # y_av[missing] = np.nanmean(y_av)

        # calculate the residual between the actual data and the moving average
        # and then find the data that lies outside of sigma*std
        residual = nonines_data - y_av
        std = np.nanstd(residual)
        sigma = 3.0

        itemindex =np.where( (nonines_data > y_av + (sigma*std)) | (nonines_data < y_av - (sigma*std)) )
        return itemindex

    def moving_average(self, data, window_size):
        """ Computes moving average using discrete linear convolution of two one dimensional sequences.
        Args:
        -----
                data (pandas.Series): independent variable
                window_size (int): rolling window size

        Returns:
        --------
                ndarray of linear convolution

        References:
        ------------
        [1] Wikipedia, "Convolution", http://en.wikipedia.org/wiki/Convolution.
        [2] API Reference: https://docs.scipy.org/doc/numpy/reference/generated/numpy.convolve.html

        """
        # REMOVE GLOBAL OUTLIERS FROM MOVING AVERAGE CALCULATION nk
        filtered_data = data.copy()
        # my_mad=np.nanmedian(np.abs(filtered_data-np.nanmedian(filtered_data)))
        # my_mean=np.nanmean(filtered_data)

        my_mean=np.nanmean(filtered_data)
        my_std = np.nanstd(filtered_data)

        # itemindex = np.where(((filtered_data>my_mean+4*my_mad )  | (filtered_data<my_mean-4*my_mad)))
        itemindex = np.where(((filtered_data>my_mean+3*my_std )  | (filtered_data<my_mean-3*my_std)))
        filtered_data[itemindex]=np.nanmean(filtered_data)
        # Fix boundary effects by adding prepending and appending values to the data
        filtered_data = np.insert(filtered_data,0,np.ones(window_size)*np.nanmean(filtered_data[:window_size//2]))
        filtered_data = np.insert(filtered_data,filtered_data.size,np.ones(window_size)*np.nanmean(filtered_data[-window_size//2:]))
        window = np.ones(int(window_size))/float(window_size)
        # return (np.convolve(filtered_data, window, 'same')[window_size:-window_size],itemindex)
        return np.convolve(filtered_data, window, 'same')[window_size:-window_size]

    def resample2(self, sens_str):
        data = self.sens_objects[sens_str].data.copy()
        nines_ind = np.where(data == 9999)
        data[nines_ind] = float('nan')
        ave = np.nanmean(data)
        datas = data[0:-1]-ave#int(self.sens_objects[sens_str].height)
        datae = data[1:]-ave#int(self.sens_objects[sens_str].height)
        yc = (datae - datas)/int(self.sens_objects[sens_str].rate)

        min_data = []
        for j in range(0,len(datas)):
            for i in range(0,int(self.sens_objects[sens_str].rate)):
                min_data.append(float(datas[j]+yc[j]))
        # nan_ind = np.argwhere(np.isnan(min_data))
        # min_data[nan_ind] = 9999
        return np.asarray(min_data)

    def show_message(self, *args):
        print("SHOW MESSAGE",*args)
        # choice = QtWidgets.QMessageBox.information(self, 'The end of data has been reached',  'The end of data has been reached', QtWidgets.QMessageBox.Ok)
        self.show_custom_message(*args, *args)

    def show_ref_dialog(self):
        try:
            self.browser
        except AttributeError:
            self.show_custom_message("Error!", "Data needs to be loaded first.")
            return
        else:
            if(self.is_digit(str(self.refLevelEdit.text()))):
                # text, result = QtWidgets.QInputDialog.getText(self, 'My Input Dialog', 'Enter start date and time:')
                date, time, result = DateDialog.getDateTime(self)
                ISOstring = date.toString('yyyy-MM-dd')+'T'+time.toString("HH:mm")
                if result:

                    REF_diff = int(str(self.refLevelEdit.text())) - int(self.sens_objects[self.sens_str].height)
                    new_REF = REF_diff + int(self.sens_objects[self.sens_str].height)
                    #offset the data
                    self.browser.offset_data(ISOstring, REF_diff)
                    # format the new reference to a 4 character string (i.e add leading zeros if necessary)
                    # update the header
                    new_header = self.sens_objects[self.sens_str].header[0][:60]+'{:04d}'.format(new_REF)+self.sens_objects[self.sens_str].header[0][64:]
                    self.sens_objects[self.sens_str].header[0] = new_header
                    self.ui.lineEdit.setText(self.sens_objects[self.sens_str].header[0])
                    print("Succesfully changed to: ", str(self.refLevelEdit.text()))

            else:
                self.show_custom_message("Error!", "The value entered is not a number.")
                return

    def is_digit(self, n):
        try:
            int(n)
            return True
        except ValueError:
            return  False

    def remove_9s(self, data):
        nines_ind = np.where(data == 9999)
        data[nines_ind] = float('nan')
        return data

    def show_custom_message(self, title, descrip):
        choice = QtWidgets.QMessageBox.information(self, title,  descrip, QtWidgets.QMessageBox.Ok)

    def save_to_ts_files(self):
        # Deleting tkey "ALL" from the list of sensors
        if "ALL" in self.sens_objects:
            del self.sens_objects["ALL"]
        if(self.sens_objects):
            months = len(self.sens_objects["PRD"].line_num)  # amount of months loaded
            # print("Amount of months loaded", months)
            assem_data=[[] for j in range(months)]  # initial an empty list of lists with the number of months
            nan_ind = np.argwhere(np.isnan(self.browser.data))
            # print("NAN INDICES",nan_ind)
            # self.browser.data[nan_ind] = 9999
            # self.sens_objects[self.sens_str].data = self.browser.data
            # separate PRD from the rest because it has to be saved on the top file
            # Because dictionaries are unordered
            prd_list = [[] for j in range(months)]

            # Cycle through each month loaded
            for m in range(months):
                # Cycle through each month loaded, where key is the sensor name
                # Use value instead of self.sens_objects[key]?
                for key, value in self.sens_objects.items():
                    # Add header
                    # separate PRD from the rest because it has to be saved on the top file
                    if(key == "PRD"):
                        prd_list[m].append(self.sens_objects[key].header[m].strip("\n"))
                    else:
                        assem_data[m].append(self.sens_objects[key].header[m].strip("\n"))
                    # The ugly range is calculating start and end line numbers for each month that was Loaded
                    # so that the data can be saved to separate, monthly files
                    for i in range(sum(self.sens_objects[key].line_num[:])-sum(self.sens_objects[key].line_num[m:]), sum(self.sens_objects[key].line_num[:])-sum(self.sens_objects[key].line_num[m:])+self.sens_objects[key].line_num[m]):
                        # File formatting is differs based on the sampling rate of a sensor
                        if(int(self.sens_objects[key].rate)>=5):
                            # ys_str_list.append(' '.join(str(e) for e in ys[i*12:12+i*12].tolist()))
                            # Get only sealevel reading, without anything else (no time/date etc)
                            data = ''.join('{:5.0f}'.format(e) for e in self.sens_objects[key].data.flatten()[i*12:12+i*12].tolist())
                            # The columns/rows containing only time/data and no sealevel measurements
                            # it_col_formatted = self.sens_objects[key].time_info[i].split(" ")
                            # it_col_formatted[0] = ' '
                            # it_col_formatted[1] = self.sens_objects[key].type
                            # it_col_formatted[3] = self.sens_objects[key].time_info[0].split(" ")[3][-2:] #formatting year to a 2 digit
                            it_col_formatted = '  '+self.sens_objects[key].type+'  '+self.sens_objects[key].time_info[i][8:12].strip()[-2:] + self.sens_objects[key].time_info[i][12:20]
                            # assem_data.append(info_time_col[i][0:]+data)
                            if(key == "PRD"):
                                prd_list[m].append(''.join(it_col_formatted)+data)
                            else:
                                assem_data[m].append(''.join(it_col_formatted)+data)
                        else:
                            # ys_str_list.append(''.join(str(e) for e in ys[i*15:15+i*15].tolist()))
                            data = ''.join('{:4.0f}'.format(e) for e in self.sens_objects[key].data.flatten()[i*15:15+i*15].tolist())
                            # it_col_formatted = self.sens_objects[key].time_info[i].split(" ")
                            # it_col_formatted[0] = ' '
                            # it_col_formatted[1] = self.sens_objects[key].type
                            # it_col_formatted[3] = self.sens_objects[key].time_info[0].split(" ")[3][-2:] #formatting year to a 2 digit
                            it_col_formatted = '  '+self.sens_objects[key].type+'  '+self.sens_objects[key].time_info[i][8:12].strip()[-2:] + self.sens_objects[key].time_info[i][12:20]
                            # assem_data.append(info_time_col[i][0:]+data)
                            assem_data[m].append(''.join(it_col_formatted)+data)
                    if(key == "PRD"):
                        prd_list[m].append('9'*80)
                    else:
                        assem_data[m].append('9'*80)
                del data
                # find the start date lines of each monp file that was loaded
                date_str = self.sens_objects[key].time_info[sum(self.sens_objects[key].line_num[:])-sum(self.sens_objects[key].line_num[m:])]
                month_int = int(date_str[12:14][-2:])
                month_str = "{:02}".format(month_int)
                year_str = date_str[8:12][-2:]
                station_num = self.sens_objects[key].type[0:-3]
                file_name ='t' + station_num + year_str + month_str + '.dat'
                try:
                    with open(st.get_path(st.SAVE_KEY) + '/' + file_name, 'w') as the_file:
                        for lin in prd_list[m]:
                            the_file.write(lin+"\n")
                        for line in assem_data[m]:
                            the_file.write(line+"\n")
                        # Each file ends with two lines of 80 9s that's why adding an additional one
                        the_file.write('9'*80+"\n")
                    self.show_custom_message("Success", "Success \n" + file_name + " Saved to " + st.get_path(st.SAVE_KEY) + "\n")
                except IOError as e:
                    self.show_custom_message("Error", "Cannot Save to " + st.get_path(st.SAVE_KEY) + "\n" + str(e) + "\n Please select a different path to save to")
            # if result == True:
            #     print("Succesfully changed to: ", str(self.refLevelEdit.text()))
        else:
            self.show_custom_message("Warning", "You haven't loaded any data.")
