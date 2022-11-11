from PyQt5.QtWidgets import QMainWindow
from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
from pandas import date_range

import settings as st
import station_tools.utils
from dialogs import DateDialog
from interactive_plot import PointBrowser
from station_tools.sensor import *
from station_tools.utils import find_outliers

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

        # # If a fast delivery save path hasn't been defined, give it a home directory
        # if (st.get_path(st.FD_PATH)):
        #     self.ui.lineEditFDPath.setPlaceholderText(st.get_path(st.FD_PATH))
        # else:
        #     st.SETTINGS.setValue(st.FD_PATH, os.path.expanduser('~'))
        #     self.ui.lineEditFDPath.setPlaceholderText(os.path.expanduser('~'))
        #
        # # If a high frequency data save path hasn't been defined, give it a home directory
        # if (st.get_path(st.HF_PATH)):
        #     self.ui.lineEditHFPath.setPlaceholderText(st.get_path(st.HF_PATH))
        # else:
        #     st.SETTINGS.setValue(st.HF_PATH, os.path.expanduser('~'))
        #     self.ui.lineEditHFPath.setPlaceholderText(os.path.expanduser('~'))

        if st.get_path(st.DIN_PATH_KEY):
            self.ui.lineEdit_din.setPlaceholderText(st.get_path(st.DIN_PATH_KEY))

        saveButton = self.ui.pushButton_save_folder
        loadButton = self.ui.pushButton_load_folder
        dinSave = self.ui.pushButton_din
        # FDSave = self.ui.pushButton_fd_folder
        # hf_save = self.ui.pushButton_hf_data

        saveButton.clicked.connect(lambda: self.savePath(self.ui.lineEditPath, st.SAVE_KEY))
        loadButton.clicked.connect(lambda: self.savePath(self.ui.lineEditLoadPath, st.LOAD_KEY))
        dinSave.clicked.connect(lambda: self.saveDIN(self.ui.lineEdit_din, st.DIN_PATH))
        # FDSave.clicked.connect(lambda: self.savePath(self.ui.lineEditFDPath, st.FD_PATH))
        # hf_save.clicked.connect(lambda: self.savePath(self.ui.lineEditFDPath, st.HF_PATH))

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
    return date.toString('yyyy-MM-dd') + 'T' + time.toString("HH:mm")


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

    def is_test_mode(self):
        # If switch button is in far right position (which is checked state, red button), test mode is on.
        # Vice versa for production
        return self.ui.switchwidget.button.isChecked()

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
            sl_data = utils.remove_9s(sl_data)
            sl_data = sl_data - int(self.station.month_collection[0].sensor_collection.sensors[sens_str1].height)
            data_obj[sens_str1.lower()] = {'time': station_tools.utils.datenum2(self.station.aggregate_months['time'][
                                                                                    sens_str1]),
                                           'station': '014', 'sealevel': sl_data}

            sl_data2 = self.station.aggregate_months["data"][sens_str2].copy()
            sl_data2 = utils.remove_9s(sl_data2)
            sl_data2 = sl_data2 - int(self.station.month_collection[0].sensor_collection.sensors[sens_str2].height)
            data_obj[sens_str2.lower()] = {'time': station_tools.utils.datenum2(self.station.aggregate_months['time'][
                                                                                    sens_str2]),
                                           'station': '014', 'sealevel': sl_data2}

            year = self.station.month_collection[0].sensor_collection.sensors[sens_str2].date.astype(object).year
            month = self.station.month_collection[0].sensor_collection.sensors[sens_str2].date.astype(object).month
            year_end = year
            month_end = month
            if month_end + 1 > 12:
                month_end = 1
                year_end = year + 1
            data_hr = filt.hr_process_2(data_obj, filt.datetime(year, month, 1, 0, 0, 0),
                                        filt.datetime(year_end, month_end + 1, 1, 0, 0, 0))

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

        # if (is_interactive):
        #     self.browser = PointBrowser(x, y, self._residual_ax, line, self._residual_fig,
        #                                 find_outliers(self.station, x, y, sens1))
        #     self.browser.onDataEnd += self.show_message
        #     canvas.mpl_connect('pick_event', self.browser.onpick)
        #     canvas.mpl_connect('key_press_event', self.browser.onpress)
        #     ## need to activate focus onto the mpl canvas so that the keyboard can be used
        #     canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        #     canvas.setFocus()

        self._residual_ax.figure.tight_layout()
        self.toolbar2 = self._residual_fig.canvas.toolbar  # Get the toolbar handler
        self.toolbar2.update()  # Update the toolbar memory

        self._residual_ax.figure.canvas.draw()

    def _update_top_canvas(self, sens):
        aggregate_data = self.station.aggregate_months.copy()
        data_flat = aggregate_data['data'][sens]
        outliers = aggregate_data['outliers'][sens]
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
        time = aggregate_data['time'][sens]
        self.line, = self._static_ax.plot(time, data_flat, '-', picker=5, lw=0.5, markersize=3)

        self._static_ax.set_title('select a point you would like to remove and press "D"')
        self.browser = PointBrowser(time, data_flat, self._static_ax, self.line, self._static_fig, (outliers,))
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
                # text, result = QtWidgets.QInputDialog.getText(self, 'My Input Dialog', 'Enter start date and time:')
                date, time, result = DateDialog.getDateTime(self)
                ISOstring = date_time_to_isostring(date, time)
                if result:
                    new_REF = int(str(self.ui.refLevelEdit.text()))
                    months_updated, ref_diff, new_header = self.station.update_header_reference_level(date, new_REF,
                                                                                                      self.sens_str)
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
            text_data = self.station.assemble_ts_text()
            save_path = st.get_path(st.SAVE_KEY)
            self.station.top_level_folder = save_path

            self.station.save_ts_files(text_data, path=save_path, is_test_mode=self.is_test_mode(),
                                       callback=self.file_saving_notifications)
            self.station.save_mat_high_fq(path=save_path, is_test_mode=self.is_test_mode(),
                                          callback=self.file_saving_notifications)

            # 1. Check if the .din file was added and that it still exist at that path
            #       b) also check that a save folder is set up
            # 2. If it does. load in the primary channel for our station
            # 3. If it does not exist, display a warning message on how to add it and that the FD data won't be saved
            # 4. Perform filtering and save
            if st.get_path(st.DIN_PATH_KEY):
                din_path = st.get_path(st.DIN_PATH_KEY)
            else:
                self.show_custom_message("Warning",
                                         "The fast delivery data cannot be processed because you haven't selected"
                                         "the .din file location. Press F1 to access the menu to select it. And "
                                         "then click the save button again.")
                return

            # if st.get_path(st.FD_PATH_KEY):
            #     save_path = st.get_path(st.FD_PATH_KEY)
            # else:
            #     self.show_custom_message("Warning",
            #                              "Please select a location where you would like your hourly and daily data"
            #                              "to be saved. Click save again once selected.")
            #     return

            self.station.save_fast_delivery(din_path=din_path, path=save_path, is_test_mode=self.is_test_mode(),
                                            callback=self.file_saving_notifications)
            self.station.save_to_annual_file(path=save_path, is_test_mode=self.is_test_mode(),
                                             callback=self.file_saving_notifications)
        else:
            self.show_custom_message("Warning", "You haven't loaded any data.")

    def file_saving_notifications(self, success, failure):
        if success:
            for m in success:
                self.show_custom_message(m['title'], m['message'])
        if failure:
            for m in failure:
                self.show_custom_message(m['title'], m['message'])
