import os
from typing import Callable

from PyQt5.QtWidgets import QMainWindow
from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
from pandas import Series, date_range

import filtering as filt
import settings as st
from dialogs import DateDialog
from interactive_plot import PointBrowser
from sensor import *

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
    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(HelpScreen, self).__init__()

        # Object for data persistence
        # self.settings = QtCore.QSettings('UHSLC', 'com.uhslc.qcsoft')
        # st.SETTINGS.remove("savepath")
        self.ui = parent

        # If a save path hasn't been defined, give it a home directory
        if (st.get_path(st.SAVE_KEY)):
            self.ui.lineEditPath.setPlaceholderText(st.get_path(st.SAVE_KEY))
        else:
            st.SETTINGS.setValue(st.SAVE_KEY, os.path.expanduser('~'))
            self.ui.lineEditPath.setPlaceholderText(os.path.expanduser('~'))

        self.ui.lineEditLoadPath.setPlaceholderText(st.get_path(st.LOAD_KEY))

        # If a fast delivery save path hasn't been defined, give it a home directory
        if (st.get_path(st.FD_PATH)):
            self.ui.lineEditFDPath.setPlaceholderText(st.get_path(st.FD_PATH))
        else:
            st.SETTINGS.setValue(st.FD_PATH, os.path.expanduser('~'))
            self.ui.lineEditFDPath.setPlaceholderText(os.path.expanduser('~'))

        # If a high frequency data save path hasn't been defined, give it a home directory
        if (st.get_path(st.HF_PATH)):
            self.ui.lineEditHFPath.setPlaceholderText(st.get_path(st.HF_PATH))
        else:
            st.SETTINGS.setValue(st.HF_PATH, os.path.expanduser('~'))
            self.ui.lineEditHFPath.setPlaceholderText(os.path.expanduser('~'))

        if st.get_path(st.DIN_PATH):
            self.ui.lineEdit_din.setPlaceholderText(st.get_path(st.DIN_PATH))

        saveButton = self.ui.pushButton_save_folder
        loadButton = self.ui.pushButton_load_folder
        dinSave = self.ui.pushButton_din
        FDSave = self.ui.pushButton_fd_folder
        hf_save = self.ui.pushButton_hf_data

        saveButton.clicked.connect(lambda: self.savePath(self.ui.lineEditPath, st.SAVE_KEY))
        loadButton.clicked.connect(lambda: self.savePath(self.ui.lineEditLoadPath, st.LOAD_KEY))
        dinSave.clicked.connect(lambda: self.saveDIN(self.ui.lineEdit_din, st.DIN_PATH))
        FDSave.clicked.connect(lambda: self.savePath(self.ui.lineEditFDPath, st.FD_PATH))
        hf_save.clicked.connect(lambda: self.savePath(self.ui.lineEditFDPath, st.HF_PATH))

    def savePath(self, lineEditObj, setStr):
        folder_name = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select a Folder')
        if (folder_name):
            st.SETTINGS.setValue(setStr, folder_name)
            st.SETTINGS.sync()
            lineEditObj.setPlaceholderText(st.get_path(setStr))
            lineEditObj.setText("")
        else:
            pass

    def saveDIN(self, lineEditObj, setStr):
        filters = "*.din"
        if st.DIN_PATH:
            path = st.DIN_PATH
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


def assemble_ts_text(station: Station):
    months = []
    for month in station.month_collection:
        prd_text = []
        others_text = []
        for key, sensor in month.sensor_collection.items():
            if key == "ALL":
                continue
            id_sens = month.station_id + key
            id_sens = id_sens.rjust(8, ' ')
            year = str(sensor.date.astype(object).year)[-2:]
            year = year.rjust(4, ' ')
            m = "{:2}".format(sensor.date.astype(object).month)
            # day = "{:3}".format(sensor.date.astype(object).day)

            # To get the line counter, it is 60 minutes per hour x 24 hours in a day divided by data points
            # per row which can be obtained from .data.shape, and divided by the sampling rate. The number
            # given by that calculation tells after how many rows to reset the counter, that is how many rows of
            # data per day. This is true for all sensors besides PRD. PRD shows the actual hours (increments of
            # 3 per row)
            # TODO: ask Fee if there are any other sensors that have 15 minute sampling rate and check the
            # monp file if there is
            if key == "PRD":
                line_count_multiplier = 3
                prd_text.append(sensor.header)
            else:
                line_count_multiplier = 1
                others_text.append(sensor.header)
            for row, data_line in enumerate(sensor.data):
                rows_per_day = 24 * 60 // sensor.data.shape[1] // int(sensor.rate)
                line_num = (row % rows_per_day) * line_count_multiplier
                day = 1 + (row // rows_per_day)
                day = "{:3}".format(day)
                line_num = "{:3}".format(line_num)
                nan_ind = np.argwhere(np.isnan(data_line))
                data_line[nan_ind] = 9999
                sl_round_up = np.round(data_line).astype(
                    int)  # round up sealevel data and convert to int

                # right justify with 5 spaces
                spaces = 4
                if int(sensor.rate) >= 5:
                    spaces = 5
                data_str = ''.join([str(x).rjust(spaces, ' ') for x in sl_round_up])  # convert data to string
                full_line_str = '{}{}{}{}{}{}'.format(id_sens, year, m, day, line_num, data_str)

                if key == "PRD":
                    prd_text.append(full_line_str + "\n")
                else:
                    others_text.append(full_line_str + "\n")

            # If there is data for sensor other than PRD append 9s at the nd
            if others_text:
                others_text.append(80 * '9' + '\n')
        prd_text.append(80 * '9' + '\n')
        prd_text.extend(others_text)
        months.append([month, prd_text])
    return months


def save_ts_files(text_collection, path=st.get_path(st.SAVE_KEY), callback: Callable = None):
    # text collection here refers to multiple text files for each month loaded
    success = []
    failure = []
    for text_file in text_collection:
        file_name = text_file[0].get_ts_filename()
        try:
            with open(path + '/' + file_name, 'w') as the_file:
                for lin in text_file[1]:
                    the_file.write(lin)
                the_file.write(80 * '9' + '\n')
                success.append({'title': "Success", 'message': "Success \n" + file_name + " Saved to " +
                                                               path + "\n"})
        except IOError as e:
            failure.append({'title': "Error", 'message': "Cannot Save to " +
                                                         path + "\n" + str(e) +
                                                         "\n Please select a different path to save to"})
    if callback:
        callback(success, failure)
    return success, failure


def remove_9s(data):
    nines_ind = np.where(data == 9999)
    data[nines_ind] = float('nan')
    return data


def save_mat_high_fq(station: Station, path: str, callback: Callable = None):
    import scipy.io as sio

    success = []
    failure = []
    for month in station.month_collection:
        for key, sensor in month.sensor_collection.items():
            if key == "ALL":
                continue
            sl_data = sensor.get_flat_data().copy()
            sl_data = remove_9s(sl_data)
            sl_data = sl_data - int(sensor.height)
            time = filt.datenum2(sensor.get_time_vector())
            data_obj = [time, sl_data]

            file_name = month.get_mat_filename()[key]
            variable = file_name.split('.')[0]
            # transposing the data so that it matches the shape of the UHSLC matlab format
            matlab_obj = {'NNNN': variable, variable: np.transpose(data_obj, (1, 0))}
            try:
                sio.savemat(path + '/' + file_name, matlab_obj)
                success.append(
                    {'title': "Success", 'message': "Success \n" + file_name + " Saved to " + path + "\n"})
            except IOError as e:
                failure.append({'title': "Error",
                                'message': "Cannot Save to high frequency (.mat) data to" + path + "\n" + str(
                                    e) + "\n Please select a different path to save to"})
    if callback:
        callback(success, failure)
    return success, failure


def save_fast_delivery(station: Station, save_path: str, din_path: str, callback: Callable = None):
    # Todo: Refactor this into at least two more functions, one for daily fast deivery and one for hourly,
    #  each saving to both .mat and .dat
    import scipy.io as sio
    success = []
    failure = []
    for month in station.month_collection:
        data_obj = {}
        _data = month.sensor_collection.sensors
        station_num = month.station_id
        primary_sensor = filt.get_channel_priority(din_path, station_num)[
            0].upper()  # returns multiple sensor in order of importance
        if primary_sensor not in month.sensor_collection:
            failure.append({'title': "Error", 'message': "Your .din file says that {} "
                                                         "is the primary sensor but the file you have loaded does "
                                                         "not contain that sensor. Hourly and daily data will not be saved.".format(
                primary_sensor)})
            return
        sl_data = _data[primary_sensor].get_flat_data().copy()
        sl_data = remove_9s(sl_data)
        sl_data = sl_data - int(_data[primary_sensor].height)
        data_obj[primary_sensor.lower()] = {'time': filt.datenum2(_data[primary_sensor].get_time_vector()),
                                            'station': station_num, 'sealevel': sl_data}

        year = _data[primary_sensor].date.astype(object).year
        two_digit_year = str(year)[-2:]
        # month = _data[primary_sensor].date.astype(object).month

        #  Filter to hourly
        data_hr = filt.hr_process_2(data_obj, filt.datetime(year, month.month, 1, 0, 0, 0),
                                    filt.datetime(year, month.month + 1, 1, 0, 0, 0))

        # for channel parameters see filt.channel_merge function
        # We are not actually merging channels here (not needed for fast delivery)
        # But we still need to run the data through the merge function, even though we are only using one channel
        # in order to get the correct output data format suitable for the daily filter
        ch_params = [{primary_sensor.lower(): 0}]
        hourly_merged = filt.channel_merge(data_hr, ch_params)

        # Note that hourly merged returns a channel attribute which is an array of integers representing channel type.
        # used for a particular day of data. In Fast delivery, all the number should be the same because no merge
        # int -> channel name mapping is inside of filtering.py var_flag function
        data_day = filt.day_119filt(hourly_merged, station.location[0])

        month_str = "{:02}".format(month.month)
        hourly_filename = save_path + '/' + 'th' + str(station_num) + two_digit_year + month_str
        daily_filename = save_path + '/' + 'da' + str(station_num) + two_digit_year + month_str

        monthly_mean = np.round(np.nanmean(data_day['sealevel'])).astype(int)

        hr_flat = np.concatenate(data_hr[primary_sensor.lower()]['sealevel'], axis=0)
        nan_ind_hr = np.argwhere(np.isnan(hr_flat))
        hr_flat[nan_ind_hr] = 9999
        sl_hr_round_up = np.round(hr_flat).astype(
            int)  # round up sealevel data and convert to int

        sl_hr_str = [str(x).rjust(5, ' ') for x in sl_hr_round_up]  # convert data to string

        # format the date and name strings to match the legacy daily .dat format
        month_str = str(month.month).rjust(2, ' ')
        station_name = month.station_id + station.name
        line_begin_str = '{}WOC {}{}'.format(station_name.ljust(7), year, month_str)
        counter = 1
        try:
            sio.savemat(daily_filename + '.mat', data_day)
            # Remove nans, replace with 9999 to match the legacy files
            nan_ind = np.argwhere(np.isnan(data_day['sealevel']))
            data_day['sealevel'][nan_ind] = 9999
            sl_round_up = np.round(data_day['sealevel']).astype(int)  # round up sealevel data and convert to int
            # right justify with 5 spaces
            sl_str = [str(x).rjust(5, ' ') for x in sl_round_up]  # convert data to string
            with open(daily_filename + '.dat', 'w') as the_file:
                for i, sl in enumerate(sl_str):
                    if i % 11 == 0:
                        line_str = line_begin_str + str(counter) + " " + ''.join(sl_str[i:i + 11])
                        if counter == 3:
                            line_str = line_str.ljust(75)
                            final_str = line_str[:-(len(str(monthly_mean)) + 1)] + str(monthly_mean)
                            line_str = final_str
                        the_file.write(line_str + "\n")
                        counter += 1
            success.append({'title': "Success",
                            'message': "Success \n Daily Date Saved to " + st.get_path(
                                st.FD_PATH) + "\n"})
        except IOError as e:
            failure.append({'title': "Error",
                            'message': "Cannot Save Daily Data to " + daily_filename + "\n" + str(
                                e) + "\n Please select a different path to save to"})

        # Save to legacy .dat hourly format
        metadata_header = '{}{}FSL{}  {} TMZONE=GMT    REF=00000 60 {} {} M {}'. \
            format(month.station_id,
                   station.name[0:3],
                   primary_sensor,
                   month.string_location,
                   month.name.upper(),
                   two_digit_year,
                   str(month.day_count))
        line_begin = '{}{} {} {}{}'.format(month.station_id,
                                           station.name[0:3],
                                           primary_sensor,
                                           str(year),
                                           str(month.month).rjust(2))

        day = 1
        counter = 0
        # Save hourly
        try:
            sio.savemat(hourly_filename + '.mat', data_hr)
            with open(hourly_filename + '.dat', 'w') as the_file:
                the_file.write(metadata_header + "\n")
                for i, sl in enumerate(sl_hr_str):
                    if i != 0 and i % 24 == 0:
                        counter = 0
                        day += 1
                    if i % 12 == 0:
                        counter += 1
                        line_str = line_begin + str(day).rjust(2) + str(counter) + ''.join(
                            sl_hr_str[i:i + 12]).rjust(5)
                        the_file.write(line_str + "\n")
            success.append({'title': "Success",
                            'message': "Success \n Hourly Data Saved to " + st.get_path(
                                st.FD_PATH) + "\n"})
        except IOError as e:
            failure.append({'title': "Error",
                            'message': "Cannot Save Hourly Data to " + hourly_filename + "\n" + str(
                                e) + "\n Please select a different path to save to"})
    if callback:
        callback(success, failure)
    return success, failure


def date_time_to_isostring(date, time):
    return date.toString('yyyy-MM-dd') + 'T' + time.toString("HH:mm")


def moving_average(data, window_size):
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

    my_mean = np.nanmean(filtered_data)
    my_std = np.nanstd(filtered_data)

    # itemindex = np.where(((filtered_data>my_mean+4*my_mad )  | (filtered_data<my_mean-4*my_mad)))
    itemindex = np.where(((filtered_data > my_mean + 3 * my_std) | (filtered_data < my_mean - 3 * my_std)))
    filtered_data[itemindex] = np.nanmean(filtered_data)
    # Fix boundary effects by adding prepending and appending values to the data
    filtered_data = np.insert(filtered_data, 0, np.ones(window_size) * np.nanmean(filtered_data[:window_size // 2]))
    filtered_data = np.insert(filtered_data, filtered_data.size,
                              np.ones(window_size) * np.nanmean(filtered_data[-window_size // 2:]))
    window = np.ones(int(window_size)) / float(window_size)
    # return (np.convolve(filtered_data, window, 'same')[window_size:-window_size],itemindex)
    return np.convolve(filtered_data, window, 'same')[window_size:-window_size]


def find_outliers(station, t, data, sens):
    channel_freq = station.month_collection[0].sensor_collection.sensors[sens].rate
    _freq = channel_freq + 'min'

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
    window_size = 60 // int(channel_freq)

    # calculate moving average including the interolated data
    # moving_average removes big outliers before calculating moving average
    y_av = moving_average(np.asarray(interp.tolist()), window_size)
    # y_av = self.moving_average(data, 30)
    # missing=np.argwhere(np.isnan(y_av))
    # y_av[missing] = np.nanmean(y_av)

    # calculate the residual between the actual data and the moving average
    # and then find the data that lies outside of sigma*std
    residual = nonines_data - y_av
    std = np.nanstd(residual)
    sigma = 3.0

    itemindex = np.where((nonines_data > y_av + (sigma * std)) | (nonines_data < y_av - (sigma * std)))
    return itemindex


class Start(QMainWindow):
    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(Start, self).__init__()
        self.ui = parent
        self.station = None
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
        self.toolbar1 = self._static_fig.canvas.toolbar  # Get the toolbar handler
        self.toolbar1.update()  # Update the toolbar memory
        # self._residual_fig = self.ui.mplwidget_bottom.canvas.figure
        self._residual_ax = self.ui.mplwidget_bottom.canvas.figure.subplots()
        self.ui.save_btn.clicked.connect(self.save_button)
        self.ui.ref_level_btn.clicked.connect(self.show_ref_dialog)

    def make_sensor_buttons(self, sensors):
        if self.station.is_sampling_inconsistent():
            self.show_custom_message("Error", "It appears that the sampling rate for one of the sensors differs "
                                              "between two different months. This is not allowed. Please process "
                                              "each of the months individually")
            self.station = None
            return
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

        # radio_btn_HF = QtWidgets.QRadioButton("Minute", self)
        # radio_btn_HF.setChecked(True)
        self.mode = self.ui.radioButton_Minute.text()
        # Makes sure we default back to default on new file load
        self.ui.radioButton_Minute.setChecked(True)

        self.sensor_dict["PRD"].setChecked(True)
        self.sens_str = "PRD"
        self.sensor_dict2["PRD"].setEnabled(False)
        self.sensor_dict2["ALL"].setEnabled(False)
        self.plot(all=False)
        self.ui.buttonGroup_data.buttonClicked.connect(self.on_sensor_changed)
        self.ui.buttonGroup_residual.buttonClicked.connect(self.on_residual_sensor_changed)
        self.ui.buttonGroup_resolution.buttonClicked.connect(self.on_frequency_changed)

    def on_sensor_changed(self, btn):
        print(btn.text())
        if btn.text() == "ALL":
            # TODO: plot_all and plot should be merged to one function
            self.ui.save_btn.setEnabled(False)
            self.ui.ref_level_btn.setEnabled(False)
            self.plot(all=True)
        else:
            self.ui.save_btn.setEnabled(True)
            self.ui.ref_level_btn.setEnabled(True)
            self.sens_str = btn.text()
            self._update_top_canvas(btn.text())
            self.ui.lineEdit.setText(self.station.month_collection[0].sensor_collection.sensors[self.sens_str].header)
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
        print("Frequency changed", btn.text())
        self.mode = btn.text()
        self.on_residual_sensor_changed()

    def update_graph_values(self):
        # convert 'nans' back to 9999s
        nan_ind = np.argwhere(np.isnan(self.browser.data))
        self.browser.data[nan_ind] = 9999
        # we want the sensor data object to point to self.browser.data and not self.browser.data.copy()
        # because when the self.browser.data is modified on the graph
        # the sensor data object will automatically be modified as well
        # self.station[self.sens_str].data = self.browser.data
        self.station.aggregate_months['data'][self.sens_str] = self.browser.data

    def on_residual_sensor_changed(self):
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
        # Set the data browser object to NoneType on every file load
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
            ## Set 9999s to NaN so they don't show up on the graph
            ## when initially plotted
            ## nans are converted back to 9999s when file is saved
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
                # t = np.linspace(0, 10, 501)
                # t = np.arange(data.size)

                t = time
                y = data_flat - mean
                # self._static_ax.plot(t, np.tan(t), ".")
                line, = self._static_ax.plot(t, y, '-', picker=5, lw=0.5, markersize=3)  # 5 points tolerance
                # self._static_fig = self.static_canvas.figure
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
                # self.toolbar1 = self._static_fig.canvas.toolbar #Get the toolbar handler
                self.toolbar1.update()  # Update the toolbar memory
                self.ui.mplwidget_top.canvas.draw()

    def calculate_and_plot_residuals(self, sens_str1, sens_str2, mode):
        # resample the data and linearly interpolate the missing values
        # upsampled = ts.resample(_freq)
        # interp = upsampled.interpolate()
        if mode == "Hourly":
            data_obj = {}

            sl_data = self.station.aggregate_months["data"][sens_str1].copy()
            sl_data = remove_9s(sl_data)
            sl_data = sl_data - int(self.station.month_collection[0].sensor_collection.sensors[sens_str1].height)
            data_obj[sens_str1.lower()] = {'time': filt.datenum2(self.station.aggregate_months['time'][
                                                                     sens_str1]),
                                           'station': '014', 'sealevel': sl_data}

            sl_data2 = self.station.aggregate_months["data"][sens_str2].copy()
            sl_data2 = remove_9s(sl_data2)
            sl_data2 = sl_data2 - int(self.station.month_collection[0].sensor_collection.sensors[sens_str2].height)
            data_obj[sens_str2.lower()] = {'time': filt.datenum2(self.station.aggregate_months['time'][
                                                                     sens_str2]),
                                           'station': '014', 'sealevel': sl_data2}

            year = self.station.month_collection[0].sensor_collection.sensors[sens_str2].date.astype(object).year
            month = self.station.month_collection[0].sensor_collection.sensors[sens_str2].date.astype(object).month
            data_hr = filt.hr_process_2(data_obj, filt.datetime(year, month, 1, 0, 0, 0),
                                        filt.datetime(year, month + 1, 1, 0, 0, 0))

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
        print("GENERIC PLOT CALLED")
        # self._residual_ax = canvas.figure.subplots()

        line, = self._residual_ax.plot(x, y, '-', picker=5, lw=0.5, markersize=3)  # 5 points tolerance
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
        data_flat = self.station.aggregate_months['data'][sens]
        nines_ind = np.where(data_flat == 9999)
        # nonines_data = data_flat.copy()
        # nonines_data[nines_ind] = float('nan')
        # data_flat = nonines_data
        # data_flat =data_flat - np.nanmean(data_flat)
        if (len(nines_ind[0]) < data_flat.size):
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
        time = self.station.aggregate_months['time'][sens]
        self.line, = self._static_ax.plot(time, data_flat, '-', picker=5, lw=0.5, markersize=3)

        self._static_ax.set_title('select a point you would like to remove and press "D"')
        self.browser = PointBrowser(time, data_flat, self._static_ax, self.line, self._static_fig,
                                    find_outliers(self.station, time, data_flat, sens))
        self.browser.onDataEnd += self.show_message
        self.browser.on_sensor_change_update()
        # update event ids so that they can be disconnect on next sensor change
        self.pid = self.ui.mplwidget_top.canvas.mpl_connect('pick_event', self.browser.onpick)
        self.cid = self.ui.mplwidget_top.canvas.mpl_connect('key_press_event', self.browser.onpress)
        ## need to activate focus onto the mpl canvas so that the keyboard can be used
        self.toolbar1.update()
        self.ui.mplwidget_top.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.ui.mplwidget_top.canvas.setFocus()

    def resample2(self, sens_str):
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
        # nan_ind = np.argwhere(np.isnan(min_data))
        # min_data[nan_ind] = 9999
        return np.asarray(min_data)

    def show_message(self, *args):
        print("SHOW MESSAGE", *args)
        # choice = QtWidgets.QMessageBox.information(self, 'The end of data has been reached',  'The end of data has been reached', QtWidgets.QMessageBox.Ok)
        self.show_custom_message(*args, *args)


    def show_ref_dialog(self):
        if len(self.station.month_collection) > 1:
            self.show_custom_message("Warning","Adjusting reference level for multiple months is not tested "
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
                # text, result = QtWidgets.QInputDialog.getText(self, 'My Input Dialog', 'Enter start date and time:')
                date, time, result = DateDialog.getDateTime(self)
                ISOstring = date_time_to_isostring(date, time)
                if result:
                    new_REF = int(str(self.ui.refLevelEdit.text()))
                    months_updated, ref_diff, new_header = self.station.update_header_reference_level(date, new_REF, self.sens_str)
                    self.ui.lineEdit.setText(new_header)
                    # offset the data
                    if months_updated == 0:
                        self.show_custom_message("Warning!", "The date picked is not within the available range")
                    else:
                        # TODO: We could now maybe offset the data directly on sensor object as opposed ot offsetting
                        #  it through the matplotlib widget by writing a new method on sensor similar to the two new
                        #  methods added. This method would just take the new_ref (from which it calculates ref_diff)
                        #  and ISOstring
                        self.browser.offset_data(ISOstring, ref_diff)
            else:
                self.show_custom_message("Error!", "The value entered is not a number.")
                return

    def is_digit(self, n):
        try:
            int(n)
            return True
        except ValueError:
            return False

    def show_custom_message(self, title, descrip):
        choice = QtWidgets.QMessageBox.information(self, title, descrip, QtWidgets.QMessageBox.Ok)

    def save_button(self):
        if self.station:
            # updates all the user made changes (data cleaning) for all the data loaded
            self.station.back_propagate_changes(self.station.aggregate_months['data'])
            text_data = assemble_ts_text(self.station)
            save_ts_files(text_data, callback=self.file_saving_notifications)
            if st.get_path(st.HF_PATH):
                save_path = st.get_path(st.HF_PATH)
            else:
                self.show_custom_message("Warning",
                                         "Please select a location where you would like your high "
                                         "frequency matlab data "
                                         "to be saved. Click save again once selected.")
                return
            save_mat_high_fq(self.station, save_path, callback=self.file_saving_notifications)

            # 1. Check if the .din file was added and that it still exist at that path
            #       b) also check that a save folder is set up
            # 2. If it does. load in the primary channel for our station
            # 3. If it does not exist, display a warning message on how to add it and that the FD data won't be saved
            # 4. Perform filtering and save
            if st.get_path(st.DIN_PATH):
                din_path = st.get_path(st.DIN_PATH)
            else:
                self.show_custom_message("Warning",
                                         "The fast delivery data cannot be processed because you haven't selected"
                                         "the .din file location. Press F1 to access the menu to select it. And "
                                         "then click the save button again.")
                return

            if st.get_path(st.FD_PATH):
                save_path = st.get_path(st.FD_PATH)
            else:
                self.show_custom_message("Warning",
                                         "Please select a location where you would like your hourly and daily data"
                                         "to be saved. Click save again once selected.")
                return

            save_fast_delivery(self.station, save_path, din_path, self.file_saving_notifications)
        else:
            self.show_custom_message("Warning", "You haven't loaded any data.")

    def file_saving_notifications(self, success, failure):
        if success:
            for m in success:
                self.show_custom_message(m['title'], m['message'])
        if failure:
            for m in failure:
                self.show_custom_message(m['title'], m['message'])
