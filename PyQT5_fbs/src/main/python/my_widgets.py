from PyQt5.QtWidgets import QMainWindow
from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
import matplotlib.dates as mdates
from pandas import Series, date_range

import os
import requests
import pandas as pd
import settings as st
import uhslc_station_tools.utils
from io import StringIO
from dialogs import DateDialog
from interactive_plot import PointBrowser
from uhslc_station_tools.sensor import *

if is_pyqt5():
    pass
else:
    pass

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


class HelpScreen(QMainWindow):
    """
    GUI window to manage save/load paths and .din file selection.
    Provides user interaction for setting application directories.
    """

    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """
        Initialize the Help/Settings window and wire up folder pickers.

        Args:
            parent: Parent UI object containing the relevant Qt widgets.
        """

        super(HelpScreen, self).__init__()

        # Object for data persistence.
        self.ui = parent

        # If a save path hasn't been defined, give it a home directory.
        if (st.get_path(st.SAVE_KEY)):
            self.ui.lineEditPath.setPlaceholderText(st.get_path(st.SAVE_KEY))
        else:
            st.SETTINGS.setValue(st.SAVE_KEY, os.path.expanduser('~'))
            self.ui.lineEditPath.setPlaceholderText(os.path.expanduser('~'))

        self.ui.lineEditLoadPath.setPlaceholderText(st.get_path(st.LOAD_KEY))

        if st.get_path(st.DIN_PATH_KEY):
            self.ui.lineEdit_din.setPlaceholderText(st.get_path(st.DIN_PATH_KEY))

        saveButton = self.ui.pushButton_save_folder
        loadButton = self.ui.pushButton_load_folder
        dinSave = self.ui.pushButton_din

        saveButton.clicked.connect(lambda: self.savePath(self.ui.lineEditPath, st.SAVE_KEY))
        loadButton.clicked.connect(lambda: self.savePath(self.ui.lineEditLoadPath, st.LOAD_KEY))
        dinSave.clicked.connect(lambda: self.saveDIN(self.ui.lineEdit_din, st.DIN_PATH_KEY))

    def savePath(self, lineEditObj, setStr):
        """
        Open folder picker dialog and save selected path to settings.

        Args:
            lineEditObj: QLineEdit widget to update placeholder text.
            setStr: Key string for storing the path in settings.
        """

        folder_name = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select a Folder')

        if (folder_name):
            st.SETTINGS.setValue(setStr, folder_name)
            st.SETTINGS.sync()
            lineEditObj.setPlaceholderText(st.get_path(setStr))
            lineEditObj.setText("")
        else:
            pass

    def saveDIN(self, lineEditObj, setStr):
        """
        Open file picker dialog to select a `.din` file and save its path.

        Args:
            lineEditObj: QLineEdit widget to update placeholder text.
            setStr: Key string for storing the .din file path in settings.
        """

        filters = "*.din"
        if st.DIN_PATH_KEY:
            path = st.DIN_PATH_KEY
        else:
            path = os.path.expanduser('~')

        file_name = QtWidgets.QFileDialog.getOpenFileNames(self, 'Open File', path, filters)

        if file_name:
            st.SETTINGS.setValue(setStr, file_name[0][0])
            st.SETTINGS.sync()
            lineEditObj.setPlaceholderText(st.get_path(setStr))
            lineEditObj.setText("")
        else:
            pass


def date_time_to_isostring(date, time):
    """
    Convert date and time Qt objects to ISO 8601 string.

    Args:
        date: QDate object.
        time: QTime object.

    Returns:
        str: ISO 8601 formatted datetime string.
    """

    return date.toString('yyyy-MM-dd') + 'T' + time.toString("HH:mm")

def moving_average(data, window_size):
    """
    Computes moving average using discrete linear convolution of two one dimensional sequences.

    Args:
        data (pandas.Series): independent variable
        window_size (int): rolling window size

    Returns:
        ndarray of linear convolution

    References:
    ------------
    [1] Wikipedia, "Convolution", http://en.wikipedia.org/wiki/Convolution.
    [2] API Reference: https://docs.scipy.org/doc/numpy/reference/generated/numpy.convolve.html

    """

    # REMOVE GLOBAL OUTLIERS FROM MOVING AVERAGE CALCULATION nk
    filtered_data = data.copy()

    my_mean = np.nanmean(filtered_data)
    my_std = np.nanstd(filtered_data)

    itemindex = np.where(((filtered_data > my_mean + 3 * my_std) | (filtered_data < my_mean - 3 * my_std)))
    filtered_data[itemindex] = np.nanmean(filtered_data)

    # Fix boundary effects by adding prepending and appending values to the data.
    filtered_data = np.insert(filtered_data, 0, np.ones(window_size) * np.nanmean(filtered_data[:window_size // 2]))
    filtered_data = np.insert(filtered_data, filtered_data.size,
                              np.ones(window_size) * np.nanmean(filtered_data[-window_size // 2:]))
    window = np.ones(int(window_size)) / float(window_size)

    return np.convolve(filtered_data, window, 'same')[window_size:-window_size]


def find_outliers(station, t, data, sens):
    """
    Identify outlier indices in sensor data relative to moving average.

    Args:
        station: Station object containing sensor metadata.
        t (array-like): Time array.
        data (array-like): Sensor data array.
        sens (str): Sensor key string.

    Returns:
        numpy.ndarray: Indices of detected outliers.
    """

    channel_freq = station.month_collection[0].sensor_collection.sensors[sens].rate
    _freq = channel_freq + 'min'

    nines_ind = np.where(data == 9999)
    nonines_data = data.copy()
    nonines_data[nines_ind] = float('nan')

    # Get a date range to create pandas time Series using the sampling frequency of the sensor.
    rng = date_range(t[0], t[-1], freq=_freq)
    ts = Series(nonines_data, rng)

    # Resample the data and linearly interpolate the missing values.
    upsampled = ts.resample(_freq)
    interp = upsampled.interpolate()

    # calculate a window size for moving average routine so the window
    # size is always 60 minutes long.
    window_size = 60 // int(channel_freq)

    # Calculate moving average including the interolated data.
    # moving_average removes big outliers before calculating moving average.
    y_av = moving_average(np.asarray(interp.tolist()), window_size)

    # Calculate the residual between the actual data and the moving average
    # and then find the data that lies outside of sigma*std.
    residual = nonines_data - y_av
    std = np.nanstd(residual)
    sigma = 3.0

    itemindex = np.where((nonines_data > y_av + (sigma * std)) | (nonines_data < y_av - (sigma * std)))
    return itemindex


class Start(QMainWindow):
    """
    Main GUI for visualizing and interacting with sensor data.
    Handles plotting, residuals, reference adjustments, and saving.
    """

    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """
        Initialize the main plotting window and UI state.

        Args:
            parent: Parent UI object with Matplotlib widgets and controls.
        """

        super(Start, self).__init__()
        self.ui = parent
        self.station = None
        self.home()

    def home(self):
        """
        Set up/refresh plotting canvases, toolbars, and button connections.
        """

        self.ui.mplwidget_top.canvas.figure.clf()
        self.ui.mplwidget_bottom.canvas.figure.clf()
        self._static_ax = self.ui.mplwidget_top.canvas.figure.subplots()
        self._static_fig = self.ui.mplwidget_top.canvas.figure
        self.pid = -99
        self.cid = -98
        self.toolbar1 = self._static_fig.canvas.toolbar  # Get the toolbar handler.
        self.toolbar1.update()  # Update the toolbar memory
        self._residual_ax = self.ui.mplwidget_bottom.canvas.figure.subplots()
        self.ui.save_btn.clicked.connect(self.save_button)
        self.ui.ref_level_btn.clicked.connect(self.show_ref_dialog)

    def is_test_mode(self):
        """
        Check if application is in test mode.

        Returns:
            bool: True if test mode is enabled, False otherwise.
        """

        # If switch button is in far right position (which is checked state, red button)
        # then test-mode is on and vice-versa for pruduction.
        return self.ui.switchwidget.button.isChecked()

    def _set_resolution_enabled(self, enabled: bool):
        """
        Enable or disable hourly/minute resolution radio buttons.

        Args:
            enabled (bool): Whether buttons should be enabled.
        """

        if hasattr(self.ui, "buttonGroup_resolution"):
            for b in self.ui.buttonGroup_resolution.buttons():
                b.setEnabled(enabled)

    def make_sensor_buttons(self, sensors):
        """
        Create sensor radio and checkbox buttons dynamically.

        Args:
            sensors (dict): Mapping of sensor names to sensor objects.
        """

        if self.station.is_sampling_inconsistent():
            self.show_custom_message("Error", "It appears that the sampling rate for one of the sensors differs "
                                              "between two different months. This is not allowed. Please process "
                                              "each of the months individually")
            self.station = None
            return

        # Remove all sensor checkbox widgets from the layout every time new data is loaded.
        for i in range(self.ui.verticalLayout_left_top.count()):
            item = self.ui.verticalLayout_left_top.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for i in range(self.ui.verticalLayout_bottom.count()):
            item = self.ui.verticalLayout_bottom.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # Sensors' keys are names of all sensors which carry all of the data associated with it.
        # Make copy of it so we can use its keys and assign radio buttons to it.
        # If we do not make a copy then the sensors values would get
        # overwritten by radio button objects.
        self.sensor_dict = dict(sensors)
        self.sensor_dict2 = dict(sensors)

        # Counter added to figure out when the last item was added.
        # Set alignment of the last item to push all the radio buttons up.
        self.sensor_button_group = []
        counter = len(sensors.items())
        for key, value in sensors.items():
            counter -= 1
            self.sensor_radio_btns = QtWidgets.QRadioButton(key, self)
            self.sensor_check_btns = QtWidgets.QCheckBox(key, self)
            self.sensor_dict[key] = self.sensor_radio_btns
            self.sensor_dict2[key] = self.sensor_check_btns
            self.ui.buttonGroup_data.addButton(self.sensor_dict[key])
            self.ui.buttonGroup_residual.addButton(self.sensor_dict2[key])
            if counter > 0:
                self.ui.verticalLayout_left_top.addWidget(self.sensor_dict[key])
                self.ui.verticalLayout_bottom.addWidget(self.sensor_dict2[key])
            else:
                self.ui.verticalLayout_left_top.addWidget(self.sensor_dict[key], 0, QtCore.Qt.AlignTop)
                self.ui.verticalLayout_bottom.addWidget(self.sensor_dict2[key], 0, QtCore.Qt.AlignTop)

            self.sensor_dict[key].setText(key)
            self.sensor_button_group.append(self.sensor_radio_btns)

        self.mode = self.ui.radioButton_Minute.text()

        # Make sure we default back to default on new file load.
        self.ui.radioButton_Minute.setChecked(True)

        if 'FSL' in self.sensor_dict.keys():
            self.sensor_dict['FSL'].setChecked(True)
            self.sensor_dict['FSL'].setEnabled(False)
            self.sensor_dict['ALL'].setEnabled(False)
            self.sens_str = "FSL"
            self.ui.save_btn.setEnabled(False)
        else:
            self.sensor_dict["PRD"].setChecked(True)
            self.sens_str = "PRD"
            self.sensor_dict2["PRD"].setEnabled(False)

        self.sensor_dict2["ALL"].setEnabled(False)
        self.plot(all=False)
        self.ui.buttonGroup_data.buttonClicked.connect(self.on_sensor_changed)
        self.ui.buttonGroup_residual.buttonClicked.connect(self.on_residual_sensor_changed)
        self.ui.buttonGroup_resolution.buttonClicked.connect(self.on_frequency_changed)
        line_sep = QtWidgets.QFrame()
        line_sep.setFrameShape(QtWidgets.QFrame.HLine)
        line_sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.ui.verticalLayout_left_top.addSpacing(10)
        self.ui.verticalLayout_left_top.addWidget(line_sep)

        # Add daily and hourly fast delivery buttons to top-left panel.
        self.daily_button = QtWidgets.QRadioButton("Daily FD\nWeb v Local", self)
        self.ui.buttonGroup_data.addButton(self.daily_button)
        self.daily_button.clicked.connect(lambda: self.plot_fast_delivery("daily"))
        self.ui.verticalLayout_left_top.addWidget(self.daily_button)
        self.hourly_button = QtWidgets.QRadioButton("Hourly FD\nWeb v Local", self)
        self.ui.buttonGroup_data.addButton(self.hourly_button)
        self.hourly_button.clicked.connect(lambda: self.plot_fast_delivery("hourly"))
        self.ui.verticalLayout_left_top.addWidget(self.hourly_button)
        self.daily_web_button = QtWidgets.QRadioButton("Daily FD\nAll Web", self)
        self.ui.buttonGroup_data.addButton(self.daily_web_button)
        self.daily_web_button.clicked.connect(lambda: self.plot_fast_delivery_web("daily"))
        self.ui.verticalLayout_left_top.addWidget(self.daily_web_button)
        self.hourly_web_button = QtWidgets.QRadioButton("Hourly FD\nAll Web", self)
        self.ui.buttonGroup_data.addButton(self.hourly_web_button)
        self.hourly_web_button.clicked.connect(lambda: self.plot_fast_delivery_web("hourly"))
        self.ui.verticalLayout_left_top.addWidget(self.hourly_web_button)

    def on_sensor_changed(self, btn):
        """
        Handle sensor selection changes and update plots.

        Args:
            btn: QRadioButton clicked.
        """

        if btn.text() == "ALL":
            # TODO: plot_all and plot should be merged to one function.
            self.ui.save_btn.setEnabled(False)
            self.ui.ref_level_btn.setEnabled(False)
            self._set_resolution_enabled(True)
            self.plot(all=True)
        elif btn.text() in ["Daily FD\nWeb v Local", "Hourly FD\nWeb v Local", 
                            "Daily FD\nAll Web", "Hourly FD\nAll Web"]:
            return
        else:
            # Update the fast delivery flag.
            self.fd_active = False
            for button in self.ui.buttonGroup_residual.buttons():
                if button.text() not in ["PRD", "ALL"]:
                    button.setEnabled(True)
                else:
                    button.setEnabled(False)
            self.ui.save_btn.setEnabled(True)
            self.ui.ref_level_btn.setEnabled(True)
            self._set_resolution_enabled(True)
            self.sens_str = btn.text()
            self._update_top_canvas(btn.text())
            self.ui.lineEdit.setText(self.station.month_collection[0].sensor_collection.sensors[self.sens_str].header)
            self.update_graph_values()

        # Clear residual buttons and graph when the top sensor is changed.
        for button in self.ui.buttonGroup_residual.buttons():
            button.setChecked(False)
        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()

    def on_frequency_changed(self, btn):
        """
        Handle frequency radio button changes.

        Args:
            btn: QRadioButton clicked.
        """

        print("Frequency changed", btn.text())
        self.mode = btn.text()
        self.on_residual_sensor_changed()

    def update_graph_values(self):
        """
        Synchronize modified data on plot with station object.
        """

        # Convert 'nans' back to 9999s.
        nan_ind = np.argwhere(np.isnan(self.browser.data))
        self.browser.data[nan_ind] = 9999

        # We want the sensor data object to point to self.browser.data and not self.browser.data.copy()
        # because when the self.browser.data is modified on the graph the sensor data object will 
        # automatically be modified as well.
        self.station.aggregate_months['data'][self.sens_str] = self.browser.data

    def on_residual_sensor_changed(self):
        """
        Update residual plot based on selected residual sensor(s).
        """

        # Safety measure to ensure no residual buttons available when fast delivery is selected.
        if hasattr(self, "fd_active") and self.fd_active:
            self._residual_ax.cla()
            self._residual_ax.figure.canvas.draw()
            for button in self.ui.buttonGroup_residual.buttons():
                button.setEnabled(False)
            return

        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()

        checkedItems = [button for button in self.ui.buttonGroup_residual.buttons() if button.isChecked()]
        if (checkedItems):
            for button in checkedItems:
                self.calculate_and_plot_residuals(self.sens_str, button.text(), self.mode)
        else:
            self._residual_ax.cla()
            self._residual_ax.figure.canvas.draw()

    def plot(self, all=False):
        """
        Plot selected sensor data or all sensors on top canvas.

        Args:
            all (bool): If True, plot all sensors; otherwise selected.
        """

        # Set the data browser object to NoneType on every file load.
        self.browser = None
        self._static_ax.cla()
        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()

        if all:
            lineEditText = 'No Header -- Plotting all sensors'
            sens_objects = self.station.aggregate_months['data']
            title = 'Relative levels = signal - average over selected period'
        else:
            lineEditText = self.station.month_collection[0].sensor_collection.sensors[self.sens_str].header
            sens_objects = [self.sens_str]
            title = 'Tide Prediction'

        self.ui.lineEdit.setText(lineEditText)

        for sens in sens_objects:

            # Set 9999s to NaN so they don't show up on the graph when initially plotted.
            # Nans are converted back to 9999s when file is saved.
            if sens == "ALL":
                pass
            else:
                data_flat = self.station.aggregate_months['data'][sens]
                time = self.station.aggregate_months['time'][sens]
                nines_ind = np.where(data_flat == 9999)
                data_flat[nines_ind] = float('nan')
                if all:
                    mean = np.nanmean(data_flat)
                else:
                    mean = 0

                t = time
                y = data_flat - mean
                line, = self._static_ax.plot(t, y, '-', picker=5, lw=0.5, markersize=3)  # 5 points tolerance.
                if all:
                    line.set_label(sens)
                    self._static_ax.legend()
                self._static_ax.set_title(title)

                self._static_ax.autoscale(enable=True, axis='both', tight=True)
                self._static_ax.set_xlim([t[0], t[-1]])
                self._static_ax.margins(0.05, 0.05)

                self.ui.mplwidget_top.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
                self.ui.mplwidget_top.canvas.setFocus()
                self.ui.mplwidget_top.canvas.figure.tight_layout()
                self.toolbar1.update()  # Update the toolbar memory
                self.ui.mplwidget_top.canvas.draw()

    def calculate_and_plot_residuals(self, sens_str1, sens_str2, mode):
        """
        Compute residuals between two sensors and plot them.

        Args:
            sens_str1 (str): First sensor key.
            sens_str2 (str): Second sensor key.
            mode (str): Plotting mode ("Hourly" or "Minute").
        """

        if mode == "Hourly":
            data_obj = {}

            sl_data = self.station.aggregate_months["data"][sens_str1].copy()
            sl_data = utils.remove_9s(sl_data)
            sl_data = sl_data - int(self.station.month_collection[0].sensor_collection.sensors[sens_str1].height)
            data_obj[sens_str1.lower()] = {'time': utils.datenum2(self.station.aggregate_months['time'][
                                                                                    sens_str1]),
                                           'station': '014', 'sealevel': sl_data}

            sl_data2 = self.station.aggregate_months["data"][sens_str2].copy()
            sl_data2 = utils.remove_9s(sl_data2)
            sl_data2 = sl_data2 - int(self.station.month_collection[0].sensor_collection.sensors[sens_str2].height)
            data_obj[sens_str2.lower()] = {'time': utils.datenum2(self.station.aggregate_months['time'][
                                                                                    sens_str2]),
                                           'station': '014', 'sealevel': sl_data2}

            year = self.station.month_collection[0].sensor_collection.sensors[sens_str2].date.astype(object).year
            month = self.station.month_collection[0].sensor_collection.sensors[sens_str2].date.astype(object).month
            year_end = year
            month_end = month
            if month_end + 1 > 12:
                month_end = 1
                year_end = year + 1

            data_hr = filt.hr_process(data_obj, datetime(year, month, 1, 0, 0, 0),
                                        datetime(year_end, month_end + 1, 1, 0, 0, 0))

            # Subtract the mean from the sensor data for comparison with new tide prediction.
            if sens_str1 == 'PRD':
                sensor_data_flat = data_hr[sens_str2.lower()]["sealevel"].flatten()
                sensor_data_mean = np.nanmean(sensor_data_flat)
                data_hr[sens_str2.lower()]["sealevel"] = [[element - sensor_data_mean for element in sublist]
                                                          for sublist in data_hr[sens_str2.lower()]["sealevel"]]

            hr_resid = data_hr[sens_str1.lower()]["sealevel"] - data_hr[sens_str2.lower()]["sealevel"]
            time = [filt.matlab2datetime(tval[0]) for tval in data_hr[list(data_hr.keys())[0]]['time']]

            self.generic_plot(self.ui.mplwidget_bottom.canvas, time, hr_resid, sens_str1, sens_str2,
                              "Hourly Residual", is_interactive=False)

        else:

            newd1 = self.resample2(sens_str1)
            newd2 = self.resample2(sens_str2)
            if newd1.size > newd2.size:
                resid = newd2 - newd1[:newd2.size]
            else:
                resid = newd1 - newd2[:newd1.size]

            time = date_range(self.station.month_collection[0].sensor_collection.sensors[sens_str1].date,
                              periods=resid.size, freq='1min')

            self.generic_plot(self.ui.mplwidget_bottom.canvas, time, resid, sens_str1, sens_str2, "Residual",
                              is_interactive=False)

    def generic_plot(self, canvas, x, y, sens1, sens2, title, is_interactive):
        """
        Generic plotting function for residual or comparison plots.

        Args:
            canvas: Matplotlib canvas.
            x (array-like): Time values.
            y (array-like): Data values.
            sens1 (str): Label for first sensor.
            sens2 (str): Label for second sensor.
            title (str): Plot title.
            is_interactive (bool): Whether to enable point browser.
        """

        line, = self._residual_ax.plot(x, y, '-', picker=5, lw=0.5, markersize=3)  # 5 points tolerance.
        line.set_gid(sens2)
        self._residual_fig = canvas.figure
        self._residual_ax.set_title(title)
        line.set_label(title + ": " + sens1 + " - " + sens2)
        self._residual_ax.autoscale(enable=True, axis='both', tight=True)
        self._residual_ax.set_xlim([x[0], x[-1]])
        self._residual_ax.margins(0.05, 0.05)
        self._residual_ax.legend()

        if (is_interactive):
            self.browser = PointBrowser(x, y, self._residual_ax, line, self._residual_fig,
                                        find_outliers(self.station, x, y, sens1))
            self.browser.onDataEnd += self.show_message
            canvas.mpl_connect('pick_event', self.browser.onpick)
            canvas.mpl_connect('key_press_event', self.browser.onpress)
            ## need to activate focus onto the mpl canvas so that the keyboard can be used
            canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
            canvas.setFocus()

        self._residual_ax.figure.tight_layout()
        self.toolbar2 = self._residual_fig.canvas.toolbar  # Get the toolbar handler
        self.toolbar2.update()  # Update the toolbar memory
        self._residual_ax.figure.canvas.draw()

    def _update_top_canvas(self, sens):
        """
        Refresh the top canvas with data for a specific sensor.

        Args:
            sens (str): Sensor key string.
        """

        data_flat = self.station.aggregate_months['data'][sens]
        nines_ind = np.where(data_flat == 9999)

        if (len(nines_ind[0]) < data_flat.size):
            if np.all(np.isnan(data_flat)):
                self.show_custom_message("Warning", f"The {sens} sensor has no data")
        else:
            self.show_custom_message("Warning", f"The {sens} sensor has no data")

        self._static_ax.clear()

        # Disconnect canvas pick and press events when a new sensor is selected
        # to eliminate multiple callbacks on sensor change.
        self.ui.mplwidget_top.canvas.mpl_disconnect(self.pid)
        self.ui.mplwidget_top.canvas.mpl_disconnect(self.cid)

        if self.browser:
            self.browser.onDataEnd -= self.show_message
            self.browser.disconnect()

        time = self.station.aggregate_months['time'][sens]
        self.line, = self._static_ax.plot(time, data_flat, '-', picker=5, lw=0.5, markersize=3)

        self._static_ax.set_title('select a point you would like to remove and press "D"')
        self.browser = PointBrowser(time, data_flat, self._static_ax, self.line, self._static_fig,
                                    find_outliers(self.station, time, data_flat, sens))

        self.browser.onDataEnd += self.show_message
        self.browser.on_sensor_change_update()

        # Update event ids so that they can be disconnect on next sensor change.
        self.pid = self.ui.mplwidget_top.canvas.mpl_connect('pick_event', self.browser.onpick)
        self.cid = self.ui.mplwidget_top.canvas.mpl_connect('key_press_event', self.browser.onpress)

        # Need to activate focus onto the mpl canvas so that the keyboard can be used.
        self.toolbar1.update()
        self.ui.mplwidget_top.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.ui.mplwidget_top.canvas.setFocus()

    def resample2(self, sens_str):
        """
        Resample sensor data to minute resolution.

        Args:
            sens_str (str): Sensor key string.

        Returns:
            numpy.ndarray: Resampled data array.
        """

        data = self.station.aggregate_months['data'][sens_str].copy()
        nines_ind = np.where(data == 9999)
        data[nines_ind] = float('nan')
        ave = np.nanmean(data)
        datas = data[0:-1] - ave  # int(self.sens_objects[sens_str].height)
        datae = data[1:] - ave  # int(self.sens_objects[sens_str].height)
        yc = (datae - datas) / int(self.station.month_collection[0].sensor_collection.sensors[sens_str].rate)

        min_data = []
        for j in range(0, len(datas)):
            for i in range(0, int(self.station.month_collection[0].sensor_collection.sensors[sens_str].rate)):
                min_data.append(float(datas[j] + yc[j]))

        return np.asarray(min_data)

    def _plot_on_top_canvas(self, time_series_dict, title=""):
        """
        Plot multiple sensor time series on the top canvas.

        Args:
            time_series_dict (dict): Mapping of sensor names to (time, data) like
                {
                    "PRD": (time_array, sealevel_array),
                    "RAD": (time_array, sealevel_array),
                    ...
                }
            title (str, optional): Title for plot.
        """

        self._static_ax.clear()
        self.ui.mplwidget_top.canvas.mpl_disconnect(self.pid)
        self.ui.mplwidget_top.canvas.mpl_disconnect(self.cid)

        for label, (t, y) in time_series_dict.items():
            if t.size == 0 or y.size == 0:
                continue
            t_dt = [datetime.fromordinal(int(val)) + timedelta(days=val % 1) - timedelta(days=366) for val in t]
            self._static_ax.plot(t_dt, y, '-', lw=0.5, markersize=3, label=label)

        self._static_ax.set_title(title or "Hourly Averages")
        self._static_ax.autoscale(enable=True, axis='both', tight=True)

        # Set global x limits based on first series.
        first_key = next(iter(time_series_dict))
        t_dt_first = [datetime.fromordinal(int(val)) + timedelta(days=val % 1) - timedelta(days=366) for val in time_series_dict[first_key][0]]
        self._static_ax.set_xlim([t_dt_first[0], t_dt_first[-1]])
        self._static_ax.margins(0.05, 0.05)
        self._static_ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        self._static_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self._static_ax.legend(loc='upper left')
        self.toolbar1.update()
        self.ui.mplwidget_top.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.ui.mplwidget_top.canvas.setFocus()
        self.ui.mplwidget_top.canvas.draw()

    def show_message(self, *args):
        """
        Wrapper to display a custom message box.
        """

        print("SHOW MESSAGE", *args)

        self.show_custom_message(*args, *args)

    def show_ref_dialog(self):
        """
        Open dialog for adjusting sensor reference level.
        """

        if len(self.station.month_collection) > 1:
            self.show_custom_message("Warning", "Adjusting reference level for multiple months is not tested "
                                                "and could produce unwanted behaviour. Please load one month only "
                                                "to change the level")
            return

        try:
            self.browser
        except AttributeError:
            self.show_custom_message("Error!", "Data needs to be loaded first.")
            return

        else:

            if self.is_digit(str(self.ui.refLevelEdit.text())):

                date, time, result = DateDialog.getDateTime(self)
                ISOstring = date_time_to_isostring(date, time)

                if result:

                    new_REF = int(str(self.ui.refLevelEdit.text()))
                    months_updated, ref_diff, new_header = self.station.update_header_reference_level(date, new_REF,
                                                                                                      self.sens_str)
                    self.ui.lineEdit.setText(new_header)

                    # Offset the data.
                    if months_updated == 0:
                        self.show_custom_message("Warning!", "The date picked is not within the available range")
                    else:
                        # TODO: We could now maybe offset the data directly on sensor object as opposed ot offsetting
                        # it through the matplotlib widget by writing a new method on sensor similar to the two new
                        # methods added. This method would just take the new_ref (from which it calculates ref_diff)
                        # and ISOstring.
                        self.browser.offset_data(ISOstring, ref_diff)

            else:
                self.show_custom_message("Error!", "The value entered is not a number.")
                return

    def is_digit(self, n):
        """
        Check if string can be parsed as integer.

        Args:
            n (str): Input string.

        Returns:
            bool: True if integer, False otherwise.
        """

        try:
            int(n)
            return True
        except ValueError:
            return False

    def show_custom_message(self, title, descrip):
        """
        Display a custom QMessageBox.

        Args:
            title (str): Message box title.
            descrip (str): Message description.
        """

        choice = QtWidgets.QMessageBox.information(self, title, descrip, QtWidgets.QMessageBox.Ok)

    def save_button(self):
        """
        Save modified sensor data and export to files.

        This method performs full data export for the currently loaded station.
        It now ensures that all output products — time-series text files, MATLAB
        high-frequency files, and fast delivery datasets — are saved over a
        **consistent (start_yyyymm, end_yyyymm)** range derived from the loaded
        months.

        Behavior:
            1. Applies all user edits (data cleaning) to loaded data.
            2. Determines a common date range using
                :func:`utils.extract_yyyymm_range_from_months`.
            3. Exports:
                - `.dat` time-series files
                - `.mat` high-frequency files
                - fast-delivery merged files
            4. If available, also exports annual summaries.
            5. Displays a warning if no data or missing `.din` path.

        Raises:
            Warning dialog if no data is loaded or `.din` file path is missing.
        """

        if not self.station:
            self.show_custom_message("Warning", "You haven't loaded any data.")
            return

        if not self.station.month_collection:
            self.show_custom_message("Warning", "No monthly data available to save.")
            return

        # Updates all the user made changes (data cleaning) for all the data loaded.
        self.station.back_propagate_changes(self.station.aggregate_months['data'])
        text_data = self.station.assemble_ts_text()
        save_path = st.get_path(st.SAVE_KEY)
        self.station.top_level_folder = save_path

        # Get the target start and end times in yyyymm format for output valid over a
        # consistent date range.
        target_start_month, target_end_month = utils.extract_yyyymm_range_from_months(self.station.month_collection)

        # High frequency data saved only if we are not dealing with someone else's hourly data.
        if not self.station.month_collection[0]._hourly_data:
            self.station.save_ts_files(text_data, path=save_path, is_test_mode=self.is_test_mode(),
                                       target_start_yyyymm=target_start_month, target_end_yyyymm=target_end_month,
                                       callback=self.file_saving_notifications)
            self.station.save_mat_high_fq(path=save_path, is_test_mode=self.is_test_mode(),
                                          target_start_yyyymm=target_start_month, target_end_yyyymm=target_end_month,
                                          callback=self.file_saving_notifications)

        # Fast delivery export (requires .din path)
        din_path = st.get_path(st.DIN_PATH_KEY)
        if not din_path:
            self.show_custom_message(
                "Warning",
                "The fast delivery data cannot be processed because you haven't selected "
                "the .din file location. Press F1 to open the menu and select it, then "
                "click Save again.",
            )
            return

        # Save fast delivery
        self.station.save_fast_delivery(din_path=din_path, path=save_path, is_test_mode=self.is_test_mode(),
                                        target_start_yyyymm=target_start_month, target_end_yyyymm=target_end_month,
                                        callback=self.file_saving_notifications)

        # annual data saved only if we are not dealing with someone else's hourly data
        if not self.station.month_collection[0]._hourly_data:
            self.station.save_to_annual_file(path=save_path, is_test_mode=self.is_test_mode(),
                                         callback=self.file_saving_notifications)

    def fetch_uh_web_fd_data(self, station_num, mode):
        """
        Fetch and parse UH Fast Delivery CSV data.

        Args:
            station_num (int): Station identifier.
            mode (str): "daily" or "hourly".

        Returns:
            tuple: (numpy.ndarray of times, numpy.ndarray of values),
                   or (None, None) on failure.
        """

        # Url to fast delivery data on the web.
        url = f"https://uhslc.soest.hawaii.edu/data/csv/fast/{mode}/{mode[0]}{station_num}.csv"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"WARNING: Failed to fetch UH FD {mode} data for station {station_num}: {e}")
            return None, None

        try:

            # Read raw CSV without header.
            df = pd.read_csv(StringIO(response.text), header=None)

            if mode == "hourly":
                # Format: year, month, day, hour, value.
                df.columns = ["year", "month", "day", "hour", "value"]
                df["datetime"] = pd.to_datetime(
                    dict(year=df.year, month=df.month, day=df.day, hour=df.hour), errors="coerce"
                )
            else:
                # Format: year, month, day, value.
                df.columns = ["year", "month", "day", "value"]
                df["datetime"] = pd.to_datetime(
                    dict(year=df.year, month=df.month, day=df.day), errors="coerce"
                )

            df = df.dropna(subset=["datetime"]) 
            datetime64_array = np.array([np.datetime64(d) for d in df["datetime"]])
            fd_time = np.array(utils.datenum2(datetime64_array))
            fd_sealevel = df["value"].astype(float).to_numpy()
            return fd_time, fd_sealevel

        except Exception as e:
            print(f"WARNING: Failed to parse UH FD {mode} CSV for station {station_num}: {e}")
            return None, None

    def plot_fast_delivery(self, mode):
        """
        Plot local vs UH web Fast Delivery data with residuals.

        Args:
            mode (str): "daily" or "hourly".
        """

        # If no station data, do nothing.
        if not self.station:
            return

        # Disable residual buttons when plotting fast delivery.
        for button in self.ui.buttonGroup_residual.buttons():
            button.setChecked(False)
            button.setEnabled(False)
        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()

        # Flags used to track plotting.
        self.fd_active = True
        self.sens_str = None
        self._set_resolution_enabled(False)

        # Path to relevant fast delivery data files for plotting.
        root_path = st.get_path(st.SAVE_KEY)
        station_num = self.station.month_collection[0].station_id
        fd_station_dir = 't' + str(station_num)
        fd_path = os.path.join(root_path, 'production_data', 'fast_delivery', fd_station_dir)
        all_fd_files = utils.list_station_mat_files(fd_path, str(station_num), mode)

        # Trap and warn if there are no fast delivery files for the station in the production_data directory.
        if not all_fd_files:
            self._static_ax.cla()
            self._static_ax.figure.canvas.draw()
            QtWidgets.QMessageBox.warning(self, "No Data", f"No {mode} FD files exist in the production_data directory for station {station_num}.")
            return

        # Trap and warn if an issue occurs loading the fast delivery files for the station in the production_data directory.
        try:
            fd_time, fd_sealevel = utils.load_and_concatenate_mat_files(all_fd_files)
        except Exception as e:
            print(f"ERROR loading {mode} FD files for station {station_num}: {e}")
            self._static_ax.cla()
            self._static_ax.figure.canvas.draw()
            QtWidgets.QMessageBox.warning(self, "No Data", f"Issue loading {mode} FD files in the production_data directory for station {station_num}.")
            return

        # Fetch UH web FD data.
        fd_time_web, fd_sealevel_web = self.fetch_uh_web_fd_data(station_num, mode)

        # Clean -32767 placeholders.
        if fd_time_web is not None and fd_sealevel_web is not None:
            fd_sealevel_web = np.where(fd_sealevel_web == -32767, np.nan, fd_sealevel_web)
            mask = ~np.isnan(fd_sealevel_web)
            fd_time_web = fd_time_web[mask]
            fd_sealevel_web = fd_sealevel_web[mask]

        # Ensure local and web daily data represents noon for apples to apples comparison.
        if mode.lower() == "daily":
            if fd_time is not None:
                fd_time = np.floor(np.asarray(fd_time, float)) + 0.5
            if fd_time_web is not None:
                fd_time_web = np.floor(np.asarray(fd_time_web, float)) + 0.5

        # If no web series, fall back to local-only behavior.
        if fd_time_web is None or fd_sealevel_web is None:

            # Plot local-only on top.
            fd_dict = {"FD_local": (fd_time, fd_sealevel)}
            t_min = fd_time.min()
            t_max = fd_time.max()
            x_min_dt = datetime.fromordinal(int(t_min)) + timedelta(days=t_min % 1) - timedelta(days=366)
            x_max_dt = datetime.fromordinal(int(t_max)) + timedelta(days=t_max % 1) - timedelta(days=366)
            self._plot_on_top_canvas(fd_dict, title=f"All {mode.capitalize()} Fast Delivery Sea Level Data ({station_num})")
            self._static_ax.set_xlim([x_min_dt, x_max_dt])
            self.ui.mplwidget_top.canvas.draw()
            # Bottom plot: keep empty.
            self._residual_ax.cla()
            self._residual_ax.figure.canvas.draw()
            self.ui.mplwidget_bottom.canvas.draw()
            return

        # Convert MATLAB datenums to Python datetimes.
        local_dt = [datetime.fromordinal(int(v)) + timedelta(days=v % 1) - timedelta(days=366) for v in fd_time]
        web_dt = [datetime.fromordinal(int(v)) + timedelta(days=v % 1) - timedelta(days=366) for v in fd_time_web]

        # If daily, force both series to noon so days align cleanly.
        if mode.lower() == "daily":
            local_dt = [d.replace(hour=12, minute=0, second=0, microsecond=0) for d in local_dt]
            web_dt = [d.replace(hour=12, minute=0, second=0, microsecond=0) for d in web_dt]

        # Index and clean to NaN. 
        idx_local = pd.to_datetime(local_dt).round("s")
        idx_web = pd.to_datetime(web_dt).round("s")
        s_local = pd.Series(fd_sealevel, index=idx_local).replace({-32767: np.nan, 9999: np.nan})
        s_web = pd.Series(fd_sealevel_web, index=idx_web).replace({-32767: np.nan, 9999: np.nan})

        # If daily: after noon normalization, drop any duplicates per day.
        if mode.lower() == "daily":
            s_local = s_local[~s_local.index.duplicated(keep="last")]
            s_web = s_web[~s_web.index.duplicated(keep="last")]

        # Align on common times only (inner join) and drop NaNs.
        aligned = pd.concat(
            [s_local.rename("local"), s_web.rename("web")],
            axis=1, join="inner"
        ).dropna()

        # No overlap; warn and keep plots empty to avoid misleading visuals.
        if aligned.empty:
            self._static_ax.cla()
            self._static_ax.figure.canvas.draw()
            QtWidgets.QMessageBox.warning(
                self, "No Overlap",
                f"No overlapping timestamps between local and web {mode} FD data for station {station_num}."
            )
            self._residual_ax.cla()
            self._residual_ax.figure.canvas.draw()
            return

        # Prepare aligned series.
        local_mm = aligned["local"].round().to_numpy()
        web_vals = aligned["web"].to_numpy()
        common_dt = aligned.index.to_pydatetime()
        common_matlab = np.array([utils.datenum(d) for d in common_dt], dtype=float)

        # Top plot - web v local comparison.
        fd_dict = {
            "FD_web": (common_matlab, web_vals),
            "FD_local": (common_matlab, local_mm),
        }
        t_min = common_matlab.min()
        t_max = common_matlab.max()
        x_min_dt = datetime.fromordinal(int(t_min)) + timedelta(days=t_min % 1) - timedelta(days=366)
        x_max_dt = datetime.fromordinal(int(t_max)) + timedelta(days=t_max % 1) - timedelta(days=366)

        self._plot_on_top_canvas(
            fd_dict,
            title=f"Web v Local (Common Times) {mode.capitalize()} Fast Delivery Sea Level Data ({station_num})"
        )
        self._static_ax.set_xlim([x_min_dt, x_max_dt])
        self.ui.mplwidget_top.canvas.draw()

        # Bottom plot - residuals on common times.
        resid = local_mm - web_vals
        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()
        self.generic_plot(
            self.ui.mplwidget_bottom.canvas,
            aligned.index.to_pydatetime(),  # x-axis is real datetimes here
            resid,
            "FD_local",
            "FD_web",
            f"{mode.capitalize()} FD Residuals (Local - Web, Common Times)",
            is_interactive=False
        )
        self.ui.mplwidget_bottom.canvas.draw()

    def plot_fast_delivery_web(self, mode):
        """
        Plot UH web Fast Delivery data only (no residuals).

        Args:
            mode (str): "daily" or "hourly".
        """

        # If no station data, do nothing.
        if not self.station:
            return

        # Disable residual buttons; clear bottom plot.
        for button in self.ui.buttonGroup_residual.buttons():
            button.setChecked(False)
            button.setEnabled(False)
        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()

        # Flags used to track plotting.
        self.fd_active = True
        self.sens_str = None
        self._set_resolution_enabled(False)

        # Fetch UH web FD data only.
        station_num = self.station.month_collection[0].station_id
        fd_time_web, fd_sealevel_web = self.fetch_uh_web_fd_data(station_num, mode)

        # Trap and warn on fetch/parse failure.
        if fd_time_web is None or fd_sealevel_web is None:
            self._static_ax.cla()
            self._static_ax.figure.canvas.draw()
            QtWidgets.QMessageBox.warning(
                self,
                "No Data",
                f"No {mode} UH web FD data available for station {station_num}."
            )
            return

        # Clean placeholders.
        fd_sealevel_web = np.where(fd_sealevel_web == -32767, np.nan, fd_sealevel_web)
        mask = ~np.isnan(fd_sealevel_web)
        fd_time_web = fd_time_web[mask]
        fd_sealevel_web = fd_sealevel_web[mask]

        # If daily, normalize to noon for a stable daily timestamp.
        if mode.lower() == "daily":
            fd_time_web = np.floor(np.asarray(fd_time_web, float)) + 0.5

        # Build dict for the top canvas and compute x-lims.
        fd_dict = {"FD_web": (fd_time_web, fd_sealevel_web)}

        t_min = fd_time_web.min()
        t_max = fd_time_web.max()
        x_min_dt = datetime.fromordinal(int(t_min)) + timedelta(days=t_min % 1) - timedelta(days=366)
        x_max_dt = datetime.fromordinal(int(t_max)) + timedelta(days=t_max % 1) - timedelta(days=366)

        # Plot web-only data on the top canvas.
        self._plot_on_top_canvas(
            fd_dict,
            title=f"All Web-Only {mode.capitalize()} Fast Delivery Sea Level Data ({station_num})"
        )

        # Override x-axis accounting for entire web dataset.
        self._static_ax.set_xlim([x_min_dt, x_max_dt])
        self.ui.mplwidget_top.canvas.draw()

        # Bottom plot stays empty for web-only view.
        self._residual_ax.cla()
        self._residual_ax.figure.canvas.draw()
        self.ui.mplwidget_bottom.canvas.draw()

    def file_saving_notifications(self, success, failure):
        """
        Show notifications for file saving results.

        Args:
            success (list): List of successful save messages.
            failure (list): List of failure save messages.
        """

        if success:
            for m in success:
                self.show_custom_message(m['title'], m['message'])
        if failure:
            for m in failure:
                self.show_custom_message(m['title'], m['message'])
