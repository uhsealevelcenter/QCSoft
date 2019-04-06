from matplotlib.backends.qt_compat import QtCore, QtWidgets, QtGui, is_pyqt5

import os

import numpy as np
import interactive_plot as dp
from sensor import Sensor, Station
from extractor2 import DataExtractor
from dialogs import DateDialog
import settings as st
import pandas._libs.tslibs.np_datetime
import pandas._libs.tslibs.nattype
import pandas._libs.skiplist
from pandas import Series, date_range


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
        Press Ctrl (Cmd) + O to load data
        To delete a data point press "D"
        Use left and right arrow to pan through the data
        Press "b" to scroll backwards through the individual data points
        Press "n" to scroll forward through the individual data points
        Click on any particular data point to zoom in on that data section
        Press "0" to reset the view back to the entire data set
        Press Ctrl (Cmd) + Z to undo data deletion

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


class Start(QtWidgets.QWidget):

    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(Start, self).__init__(parent)
        # layout = QtWidgets.QHBoxLayout()
        # button = QtWidgets.QPushButton('Go to second!')
        # layout.addWidget(button)
        # self.setLayout(layout)
        # button.clicked.connect(self.clicked.emit)
        print("START SCREEN INIT CALLED")
        self.sens_objects = {} ## Collection of Sensor objects for station for one month
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))


        self.verticalLayout_left_main = QtWidgets.QVBoxLayout()
        self.verticalLayout_left_main.setObjectName(_fromUtf8("verticalLayout_left_main"))

        self.verticalLayout_left_top = QtWidgets.QVBoxLayout()
        self.verticalLayout_left_top.setObjectName(_fromUtf8("verticalLayout_left"))

        self.verticalLayout_right = QtWidgets.QVBoxLayout()
        self.verticalLayout_right.setObjectName(_fromUtf8("verticalLayout_right"))




        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))

        self.label = QtWidgets.QLabel()
        self.label.setObjectName(_fromUtf8("label"))
        self.label.setText(_translate("MainWindow", "Meta Data:", None))
        self.horizontalLayout.addWidget(self.label)

        self.lineEdit = QtWidgets.QLineEdit()
        self.lineEdit.setObjectName(_fromUtf8("lineEdit"))
        self.lineEdit.setDisabled(True)
        # self.lineEdit.setFixedWidth(300)
        self.horizontalLayout.addWidget(self.lineEdit)

        self.label2 = QtWidgets.QLabel()
        self.label2.setObjectName(_fromUtf8("label"))
        self.label2.setText(_translate("MainWindow", "Monhts:", None))
        self.horizontalLayout.addWidget(self.label2)

        self.lineEdit2 = QtWidgets.QLineEdit()
        self.lineEdit2.setObjectName(_fromUtf8("lineEdit"))
        self.lineEdit2.setDisabled(True)
        self.lineEdit2.setFixedWidth(200)
        self.horizontalLayout.addWidget(self.lineEdit2)

        self.refLevelEdit = QtWidgets.QLineEdit()
        self.refLevelEdit.setObjectName(_fromUtf8("refLevelEdit"))
        self.refLevelEdit.setPlaceholderText('Enter New Reference Level')
        self.horizontalLayout.addWidget(self.refLevelEdit)
        self.refLevelEdit.setFixedWidth(180)

        self.btnRefLevel = QtWidgets.QPushButton("Change Ref level", self)
        self.btnRefLevel.setStatusTip('Changes the selected sensor\'s reference level after choosing date/time')
        self.horizontalLayout.addWidget(self.btnRefLevel)
        self.btnRefLevel.clicked.connect(self.show_ref_dialog)


        self.verticalLayout_right.addLayout(self.horizontalLayout)

        self.static_canvas = FigureCanvas(Figure(figsize=(20, 4)))
        self.verticalLayout_right.addWidget(NavigationToolbar(self.static_canvas, self))
        self.verticalLayout_right.addWidget(self.static_canvas)

        # self.addToolBar(NavigationToolbar(self.static_canvas, self))

        self.residual_canvas = FigureCanvas(Figure(figsize=(20, 4)))
        self.verticalLayout_right.addWidget(NavigationToolbar(self.residual_canvas, self))
        self.verticalLayout_right.addWidget(self.residual_canvas)
        self._residual_ax = self.residual_canvas.figure.subplots()
        # self.addToolBar(QtCore.Qt.BottomToolBarArea,
        #                 NavigationToolbar(self.residual_canvas, self)
        # test = NavigationToolbar(self.residual_canvas, self)
        # # test.setAllowedAreas ( QtCore.Qt.BottomToolBarArea)
        # self.verticalLayout_right.addWidget(test)




        self.gridLayout.addLayout(self.verticalLayout_right, 0, 1, 1, 1)
        self.home()

    def home(self):
        btn = QtWidgets.QPushButton("Save", self)
        btn.setStatusTip('Save to a File')
        self.verticalLayout_left_top.addWidget(btn, 0, QtCore.Qt.AlignTop)

        self.verticalLayout_left_main.addLayout(self.verticalLayout_left_top)

        self.verticalLayout_bottom = QtWidgets.QVBoxLayout()
        self.verticalLayout_bottom.setObjectName("verticalLayout_bottom")

        pushButton_2 = QtWidgets.QPushButton("Residual",self)
        pushButton_2.setObjectName("pushButton_2")
        self.verticalLayout_bottom.addWidget(pushButton_2, 0, QtCore.Qt.AlignTop)
        self.verticalLayout_left_main.addLayout(self.verticalLayout_bottom)

        self.gridLayout.addLayout(self.verticalLayout_left_main, 0, 0, 1, 1)

        self.setLayout(self.gridLayout)
        btn.clicked.connect(self.save_to_ts_files)

        # pushButton_2.clicked.connect(self.calculate_and_plot_residuals)

    # def _update_canvas(self):
    #     self._residual_ax.clear()
    #     t = np.linspace(0, 10, 101)
    #     # Shift the sinusoid as a function of time.
    #     self._residual_ax.plot(t, np.sin(t + time.time()))
    #     self._residual_ax.figure.canvas.draw()

    def make_sensor_buttons(self, sensors):
        self.radio_button_group = QtWidgets.QButtonGroup()
        self.radio_button_group.setExclusive(True)

        self.check_button_group = QtWidgets.QButtonGroup()
        self.check_button_group.setExclusive(False)
        # self.verticalLayout_left_top.setParent(None)
        # for button in self.radio_button_group.buttons():
        print("NK", self.radio_button_group.buttons())
            # self.radio_button_group.removeButton(button)


        print("self.verticalLayout_left_top widget count", self.verticalLayout_left_top.count())
        # Remove all sensor checkbox widgets from the layout
        # every time a new sensor is selected
        for i in range(self.verticalLayout_left_top.count()):
            item = self.verticalLayout_left_top.itemAt(i)
            # self.verticalLayout_left_top.removeWidget(item.widget())
            widget = item.widget()
            if widget is not None and i!=0:
                widget.deleteLater()
        for i in range(self.verticalLayout_bottom.count()):
            item = self.verticalLayout_bottom.itemAt(i)
            # self.verticalLayout_left_top.removeWidget(item.widget())
            widget = item.widget()
            if widget is not None and i!=0:
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
            self.radio_button_group.addButton(self.sensor_dict[key])
            self.check_button_group.addButton(self.sensor_dict2[key])
            if(counter>0):
                self.verticalLayout_left_top.addWidget(self.sensor_dict[key])
                self.verticalLayout_bottom.addWidget(self.sensor_dict2[key])
            else:
                self.verticalLayout_left_top.addWidget(self.sensor_dict[key],0, QtCore.Qt.AlignTop)
                self.verticalLayout_bottom.addWidget(self.sensor_dict2[key],0, QtCore.Qt.AlignTop)

            self.sensor_dict[key].setText(key)

        # spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        # self.verticalLayout_left_top.addItem(spacerItem)
        self.sensor_dict["PRD"].setChecked(True)
        self.sens_str = "PRD"
        self.radio_button_group.buttonClicked.connect(self.on_sensor_changed)
        self.check_button_group.buttonClicked.connect(self.on_residual_sensor_changed)

    def on_sensor_changed(self, btn):
        print (btn.text())
        self.sens_str = btn.text()
        self._update_top_canvas(btn.text())
        self.lineEdit.setText(self.sens_objects[self.sens_str].header[0])
        self.update_graph_values()

        # Update residual buttons and graph when the top sensor is changed
        # self.on_residual_sensor_changed(None)
        # Clear residual buttons and graph when the top sensor is changed
        for button in self.check_button_group.buttons():
            button.setChecked(False)
        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()
        # print("ref height:",self.sens_objects[self.sens_str].height)

    def update_graph_values(self):
        # convert 'nans' back to 9999s
        nan_ind = np.argwhere(np.isnan(self.browser.data))
        self.browser.data[nan_ind] = 9999
        self.sens_objects[self.sens_str].data = self.browser.data

    def on_residual_sensor_changed(self, btn):
        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()

        checkedItems = [button for button in self.check_button_group.buttons() if button.isChecked()]
        if(checkedItems):
            for button in checkedItems:
                self.calculate_and_plot_residuals(self.sens_str, button.text())
        else:
            self._residual_ax.cla()
            self._residual_ax.figure.canvas.draw()

        # if(btn.isChecked()):
        #     self.calculate_and_plot_residuals(self.sens_str, btn.text())
        # else:
        #     # remove artist from the plot
        #     for line in self._residual_ax.lines:
        #         if(line.get_gid() == btn.text()):
        #             line.set_label('_nolegend_')
        #             line.remove()
        #             # self._residual_ax.get_legend().remove()
        #             self._residual_ax.figure.canvas.draw_idle()

    def plot(self, time, data):
        self.static_canvas.figure.clf()
        self._static_ax = self.static_canvas.figure.subplots()

        # t = np.linspace(0, 10, 501)
        t = np.arange(data.size)
        t = time
        y = data
        # self._static_ax.plot(t, np.tan(t), ".")
        self.line, = self._static_ax.plot(t, y, '-', picker=5,lw=0.5,markersize=3)  # 5 points tolerance
        self._static_fig = self.static_canvas.figure
        self._static_ax.set_title('click on point you would like to remove and press "D"')

        self._static_ax.autoscale(enable=True, axis='both', tight=True)
        self._static_ax.set_xlim([t[0], t[-1]])
        self._static_ax.margins(0.05, 0.05)

        self.browser = dp.PointBrowser(t,y,self._static_ax,self.line,self._static_fig, self.find_outliers(t, data, "PRD"))
        self.browser.onDataEnd += self.show_message
        self.pid = self.static_canvas.mpl_connect('pick_event', self.browser.onpick)
        self.cid = self.static_canvas.mpl_connect('key_press_event', self.browser.onpress)
        ## need to activate focus onto the mpl canvas so that the keyboard can be used
        self.static_canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.static_canvas.setFocus()
        self.static_canvas.figure.tight_layout()
        self.toolbar1 = self._static_fig.canvas.toolbar #Get the toolbar handler
        self.toolbar1.update() #Update the toolbar memory

        self.static_canvas.draw()

    def calculate_and_plot_residuals(self, sens_str1, sens_str2):
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
        self.generic_plot(self.residual_canvas, time, resid,sens_str1,sens_str2, is_interactive = False)

    def generic_plot(self, canvas, x, y,sens1, sens2, is_interactive):

        # self._residual_ax = canvas.figure.subplots()

        line, = self._residual_ax.plot(x, y, '-', picker=5,lw=0.5,markersize=3)  # 5 points tolerance
        line.set_gid(sens2)
        self._residual_fig = canvas.figure
        self._residual_ax.set_title('Residual: '+sens1+" - "+sens2)
        line.set_label('Residual: '+sens1+" - "+sens2)
        self._residual_ax.autoscale(enable=True, axis='both', tight=True)
        self._residual_ax.set_xlim([x[0], x[-1]])
        self._residual_ax.margins(0.05, 0.05)
        self._residual_ax.legend()

        if(is_interactive):
            self.browser = dp.PointBrowser(x,y,self._residual_ax,line,self._residual_fig, self.find_outliers(x, y, sens1))
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
        if(len(nines_ind[0])<data_flat.size):
            # data_flat[nines_ind] = float('nan')
            pass
        else:
            self.show_custom_message("Warning", "The following sensor has no data")
        self._static_ax.clear()
        # disconnect canvas pick and press events when a new sensor is selected
        # to eliminate multiple callbacks on sensor change
        self.static_canvas.mpl_disconnect(self.pid)
        self.static_canvas.mpl_disconnect(self.cid)
        self.browser.onDataEnd -= self.show_message
        self.browser.disconnect()
        # time = np.arange(data_flat.size)
        time = self.sens_objects[sens].get_time_vector()
        self.line, = self._static_ax.plot(time, data_flat, '-', picker=5,lw=0.5,markersize=3)


        self.browser = dp.PointBrowser(time,data_flat,self._static_ax,self.line,self._static_fig, self.find_outliers(time, data_flat, sens) )
        self.browser.onDataEnd += self.show_message
        self.browser.on_sensor_change_update()
        # update event ids so that they can be disconnect on next sensor change
        self.pid = self.static_canvas.mpl_connect('pick_event', self.browser.onpick)
        self.cid  = self.static_canvas.mpl_connect('key_press_event', self.browser.onpress)
        ## need to activate focus onto the mpl canvas so that the keyboard can be used
        self.toolbar1.update()
        self.static_canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.static_canvas.setFocus()
        # TODO: All of the below should be moved to interactive_plot.py
        # self._static_ax.autoscale(enable=True, axis='x', tight=True)
        # self._static_ax.set_xlim([time[0], time[-1]])
        # self._static_ax.margins(0.05, 0.05)
        # self._static_ax.figure.canvas.flush_events()
        # self._static_ax.figure.canvas.draw()

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
        datas = data[0:-1]-ave
        datae = data[1:]-ave
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
                    print("Succesfully changed to: ", str(self.refLevelEdit.text()))
                    REF_diff = int(str(self.refLevelEdit.text())) - int(self.sens_objects[self.sens_str].height)
                    new_REF = REF_diff + int(self.sens_objects[self.sens_str].height)

                    # format the new reference to a 4 character string (i.e add leading zeros if necessary)
                    # update the header
                    new_header = self.sens_objects[self.sens_str].header[0][:60]+'{:04d}'.format(new_REF)+self.sens_objects[self.sens_str].header[0][64:]
                    self.sens_objects[self.sens_str].header[0] = new_header
                    self.lineEdit.setText(self.sens_objects[self.sens_str].header[0])
                    #offset the data
                    self.browser.offset_data(ISOstring, REF_diff)
            else:
                self.show_custom_message("Error!", "The value entered is not a number.")
                return

    def is_digit(self, n):
        try:
            int(n)
            return True
        except ValueError:
            return  False
    def show_custom_message(self, title, descrip):
        choice = QtWidgets.QMessageBox.information(self, title,  descrip, QtWidgets.QMessageBox.Ok)

    def save_to_ts_files(self):
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
                        the_file.write('9'*80)
                    self.show_custom_message("Success", "Success \n" + file_name + " Saved to " + st.get_path(st.SAVE_KEY) + "\n")
                except IOError as e:
                    self.show_custom_message("Error", "Cannot Save to " + st.get_path(st.SAVE_KEY) + "\n" + str(e) + "\n Please select a different path to save to")
            # if result == True:
            #     print("Succesfully changed to: ", str(self.refLevelEdit.text()))
        else:
            self.show_custom_message("Warning", "You haven't loaded any data.")
