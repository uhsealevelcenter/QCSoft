from PyQt5.QtWidgets import QMainWindow
from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
import matplotlib.dates as mdates
from pandas import Series, date_range

import os
import logging
import requests
import numpy as np
import pandas as pd
import settings as st
import uhslc_station_tools.utils
from io import StringIO
from dialogs import DateDialog
from interactive_plot import PointBrowser
from uhslc_station_tools.sensor import *
from pandas import Series

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

def _db_debug_enabled():

    return str(os.getenv("TSDB_LOG_DEBUG", "0")).strip().lower() in ("1", "true", "on")

def debug_print_db_series(sensor_name, t_db, y_db):
    """
    Print DB overlay data as a dataframe with useful diagnostics.
    Safe for debugging and will not modify the data.
    """

    try:
        df = pd.DataFrame({
            "time": t_db,
            "value_mm": y_db
        })

        if _db_debug_enabled():
            print("\n================ DB OVERLAY DEBUG ================")
            print("Sensor:", sensor_name)
            print("Rows:", len(df))

            print("\nHead:")
            print(df.head(10))

            print("\nTail:")
            print(df.tail(10))

            print("\nSummary statistics:")
            print(df["value_mm"].describe())

            print("\nSpecial values:")
            print("NaN count:", df["value_mm"].isna().sum())
            print("9999 count:", np.sum(df["value_mm"] == 9999))
            print("9.999 count:", np.sum(df["value_mm"] == 9.999))
            print("-131072 count:", np.sum(df["value_mm"] == -131072))

            print("\nExtremes:")
            print("Min:", np.nanmin(df["value_mm"]))
            print("Max:", np.nanmax(df["value_mm"]))

            print("==================================================\n")

            # optional: dump to CSV for inspection
            # df.to_csv(f"db_overlay_debug_{sensor_name}.csv", index=False)

    except Exception as e:
        print("DB DEBUG ERROR:", e)


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
        t (array-like): Time array (datetime-like objects preferred).
        data (array-like): Sensor data array.
        sens (str): Sensor key string.

    Returns:
        numpy.ndarray: Indices of detected outliers.
    """

    channel_freq = station.month_collection[0].sensor_collection.sensors[sens].rate
    try:
        channel_freq = int(channel_freq)
    except Exception:
        channel_freq = 60

    _freq = str(channel_freq) + 'min'

    # Ensure missing sentinel handled even if caller didn't mask.
    nonines_data = np.array(data, dtype=float, copy=True)
    nonines_data[nonines_data == 9999] = np.nan

    # Use actual timestamps to avoid date_range length mismatch.
    idx = pd.to_datetime(t)

    ts = Series(nonines_data, index=idx)

    # Resample and linearly interpolate missing values.
    # Resample returns a Resampler; interpolate fills the NaNs.
    upsampled = ts.resample(_freq)
    interp = upsampled.interpolate()

    # window_size so the window is ~60 minutes long; must be >= 1.
    window_size = 60 // channel_freq if channel_freq > 0 else 1
    if window_size < 1:
        window_size = 1

    # moving_average removes big outliers before calculating moving average.
    y_av = moving_average(np.asarray(interp.tolist()), window_size)

    # Residual and sigma thresholding.
    residual = nonines_data - y_av
    std = np.nanstd(residual)
    sigma = 3.0

    itemindex = np.where((nonines_data > y_av + (sigma * std)) |
                         (nonines_data < y_av - (sigma * std)))
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
        
        # DB overlay state.
        self._db_overlay_station = None  # Station object loaded from DB
        self._db_overlay_artists = []  # matplotlib artists for DB overlay
        self._db_overlay_enabled = False  # whether overlay should be shown

        # Track the spacer widget used to push the DB overlay checkbox down.
        self._db_overlay_spacer = None

        # While True, Save is temporarily disabled until required background DB
        # prefetch queries finish or fail.
        self._db_save_gate_pending = False

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
        self.toolbar1.update()  # Update the toolbar memory.
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

    def _should_enable_save_button(self):
        """
        Determine whether Save should be enabled based on current UI state.

        Save should remain disabled when:
          - background DB prefetch is still pending
          - no station is loaded
          - current selection is ALL
          - current selected sensor is FSL
        """
        if self._db_save_gate_pending:
            return False

        if not self.station:
            return False

        # If plotting ALL, Save should stay disabled.
        if getattr(self, "_plotting_all", False):
            return False

        # Existing behavior: do not allow save when default FSL path is active.
        if getattr(self, "sens_str", None) == "FSL":
            return False

        return True

    def _refresh_save_button_enabled(self):
        """
        Apply the correct enabled/disabled state to the Save button based on
        current station / sensor / DB-gate state.
        """

        try:
            self.ui.save_btn.setEnabled(self._should_enable_save_button())
        except Exception:
            pass

    def set_db_save_gate_pending(self, pending: bool):
        """
        Temporarily disable Save while background DB prefetch is still running.
        Save is always re-evaluated when pending becomes False.
        """

        self._db_save_gate_pending = bool(pending)
        self._refresh_save_button_enabled()

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

        # Clear old DB overlay immediately when a new station is being loaded.
        self.reset_db_overlay_for_new_station()

        # If the checkbox/spacer are currently in the layout, remove them so they don't get deleteLater()'d.
        if hasattr(self, "db_overlay_checkbox") and self.db_overlay_checkbox is not None:
            try:
                self.ui.verticalLayout_left_top.removeWidget(self.db_overlay_checkbox)
                self.db_overlay_checkbox.setParent(None)
            except Exception:
                pass

        if hasattr(self, "_db_overlay_spacer") and self._db_overlay_spacer is not None:
            try:
                self.ui.verticalLayout_left_top.removeWidget(self._db_overlay_spacer)
                self._db_overlay_spacer.setParent(None)
            except Exception:
                pass
            self._db_overlay_spacer = None

        # Remove all sensor checkbox widgets from the layout every time new data is loaded.
        for i in reversed(range(self.ui.verticalLayout_left_top.count())):
            item = self.ui.verticalLayout_left_top.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for i in reversed(range(self.ui.verticalLayout_bottom.count())):
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
        else:
            self.sensor_dict["PRD"].setChecked(True)
            self.sens_str = "PRD"
            self.sensor_dict2["PRD"].setEnabled(False)

        self.sensor_dict2["ALL"].setEnabled(False)
        self.plot(all=False)
        self._refresh_save_button_enabled()
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
        
        # Add DB overlay checkbox under the FD buttons, pushed down near the 
        # bottom of the top-left panel.
        if hasattr(self, "db_overlay_checkbox") and self.db_overlay_checkbox is not None:
            try:
                # Detach from any previous parent/layout
                self.db_overlay_checkbox.setParent(None)
            except Exception:
                pass

            # Add DB overlay checkbox under the FD buttons, pushed down near the
            # bottom of the top-left panel.
            if hasattr(self, "db_overlay_checkbox") and self.db_overlay_checkbox is not None:
                try:
                    # Ensure it's detached from any previous parent/layout
                    self.db_overlay_checkbox.setParent(None)
                except Exception:
                    pass

                # Create exactly one expanding spacer that we track, so we don't leak spacers across reloads.
                if getattr(self, "_db_overlay_spacer", None) is not None:
                    try:
                        self._db_overlay_spacer.deleteLater()
                    except Exception:
                        pass
                    self._db_overlay_spacer = None

                self._db_overlay_spacer = QtWidgets.QWidget()
                self._db_overlay_spacer.setSizePolicy(
                    QtWidgets.QSizePolicy.Preferred,
                    QtWidgets.QSizePolicy.Expanding
                )

                self.ui.verticalLayout_left_top.addWidget(self._db_overlay_spacer)
                self.ui.verticalLayout_left_top.addWidget(self.db_overlay_checkbox)


    def on_sensor_changed(self, btn):
        """
        Handle sensor selection changes and update plots.

        Args:
            btn: QRadioButton clicked.
        """

        if btn.text() == "ALL":
            # TODO: plot_all and plot should be merged to one function.
            self.ui.ref_level_btn.setEnabled(False)
            self._set_resolution_enabled(True)
            # Force overlay to use PRD (when available) so DB PRD is always de-meaned consistently.
            try:
                if hasattr(self, "station") and self.station and "PRD" in self.station.aggregate_months.get("data", {}):
                    self.sens_str = "PRD"
            except Exception:
                pass

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
            self.ui.ref_level_btn.setEnabled(True)
            self._set_resolution_enabled(True)
            self.sens_str = btn.text()
            self._update_top_canvas(btn.text())
            self.ui.lineEdit.setText(self.station.month_collection[0].sensor_collection.sensors[self.sens_str].header)
            self.update_graph_values()

        self._refresh_save_button_enabled()

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
        self._plotting_all = bool(all)
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
                self._static_ax.set_title(title)

                self._static_ax.autoscale(enable=True, axis='both', tight=True)
                self._static_ax.set_xlim([t[0], t[-1]])
                self._static_ax.margins(0.05, 0.05)

                self.ui.mplwidget_top.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
                self.ui.mplwidget_top.canvas.setFocus()
                self.ui.mplwidget_top.canvas.figure.tight_layout()
                self.toolbar1.update()  # Update the toolbar memory.

        # Freeze y-limits based ONLY on file data (non-DB).
        ymin, ymax = self._static_ax.get_ylim()

        # Draw DB overlay (should not affect final y-lims).
        self._render_db_overlay_if_possible()

        # Restore file-driven y-limits.
        self._static_ax.set_ylim(ymin, ymax)

        # If overlay is disabled / not ready, we still need a legend for ALL mode.
        if all and (not getattr(self, "_db_overlay_enabled", False) or not getattr(self, "_db_overlay_station", None)):
            self._static_ax.legend(loc="best")

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

        self._plotting_all = False

        data_flat = self.station.aggregate_months['data'][sens]

        # Copy for plotting/outlier detection only (do not mutate underlying stored data).
        plot_data = np.array(data_flat, dtype=float, copy=True)
        plot_data[plot_data == 9999] = np.nan

        if not np.any(np.isfinite(plot_data)):
            self.show_custom_message("Warning", "The {0} sensor has no data".format(sens))

        self._static_ax.clear()

        # Disconnect old callbacks.
        self.ui.mplwidget_top.canvas.mpl_disconnect(self.pid)
        self.ui.mplwidget_top.canvas.mpl_disconnect(self.cid)

        if self.browser:
            self.browser.onDataEnd -= self.show_message
            self.browser.disconnect()

        time = self.station.aggregate_months['time'][sens]

        # Plot.
        self.line, = self._static_ax.plot(time, plot_data, '-', picker=5, lw=0.5, markersize=3)
        self._static_ax.set_title('select a point you would like to remove and press "D"')

        # Create browser + run its update (this is likely where your ylim gets overwritten).
        self.browser = PointBrowser(
            time, plot_data, self._static_ax, self.line, self._static_fig,
            find_outliers(self.station, time, plot_data, sens)
        )
        self.browser.onDataEnd += self.show_message
        self.browser.on_sensor_change_update()

        # Match original behavior: data-driven autoscale with a small margin.
        self._static_ax.autoscale(enable=True, axis='both', tight=True)
        self._static_ax.margins(0.05, 0.05)

        # Also pin x-lims like your plot() method does, so it behaves consistently.
        try:
            self._static_ax.set_xlim([time[0], time[-1]])
        except Exception:
            pass

        self._static_ax.margins(0.05, 0.05)

        # Reconnect callbacks.
        self.pid = self.ui.mplwidget_top.canvas.mpl_connect('pick_event', self.browser.onpick)
        self.cid = self.ui.mplwidget_top.canvas.mpl_connect('key_press_event', self.browser.onpress)

        self.toolbar1.update()
        self.ui.mplwidget_top.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.ui.mplwidget_top.canvas.setFocus()

        # Ensure redraw.
        self.ui.mplwidget_top.canvas.figure.tight_layout()

        # Freeze y-limits based ONLY on file data (non-DB).
        ymin, ymax = self._static_ax.get_ylim()

        # Draw DB overlay if available (does nothing if not enabled/ready).
        self._render_db_overlay_if_possible()

        # Restore file-driven y-limits.
        self._static_ax.set_ylim(ymin, ymax)

        self.ui.mplwidget_top.canvas.draw()

    def set_db_overlay_enabled(self, enabled: bool):
        """
        Called by ApplicationWindow when overlay checkbox is toggled.
        """

        self._db_overlay_enabled = bool(enabled)

        if not self._db_overlay_enabled:
            # If disabled, remove overlay immediately and keep cached DB station.
            self._clear_db_overlay_artists()
        else:
            # If enabled, draw immediately if we already have DB data.
            self._render_db_overlay_if_possible()

        try:
            self.ui.mplwidget_top.canvas.draw_idle()
        except Exception:
            pass

    def set_db_overlay_station(self, station_db):
        """
        Called by ApplicationWindow when DB overlay data is ready.
        Stores DB station object and renders overlay if possible.
        """

        self._db_overlay_station = station_db

        # Only draw if overlay is enabled.
        self._render_db_overlay_if_possible()

        # Make the overlay appear immediately without requiring a sensor change.
        try:
            self.ui.mplwidget_top.canvas.draw_idle()
        except Exception:
            pass

    def clear_db_overlay(self):
        """
        Called by ApplicationWindow when overlay checkbox is unchecked.
        Removes overlay lines from the plot (keeps cached DB station object).
        """

        self._db_overlay_enabled = False
        self._clear_db_overlay_artists()
        try:
            self.ui.mplwidget_top.canvas.draw()
        except Exception:
            pass

    def reset_db_overlay_for_new_station(self):
        """
        Called when a new station/file is being loaded.
        Ensures old DB overlay from the previous station does not remain visible.
        """
        # Remove any plotted overlay lines immediately.
        self._clear_db_overlay_artists()

        # Clear the cached DB station so _render_db_overlay_if_possible() becomes a no-op.
        self._db_overlay_station = None

        # Keep the user's checkbox preference (enabled/disabled) as-is.
        # If you prefer to force it off while loading, uncomment the next line:
        # self._db_overlay_enabled = False

        try:
            self.ui.mplwidget_top.canvas.draw_idle()
        except Exception:
            pass

    def _clear_db_overlay_artists(self):

        if not hasattr(self, "_db_overlay_artists") or not self._db_overlay_artists:
            return
        for a in list(self._db_overlay_artists):
            try:
                a.remove()
            except Exception:
                pass
        self._db_overlay_artists = []

        # Also remove legend if it exists; it will be re-created on next plot.
        try:
            leg = self._static_ax.get_legend()
            if leg is not None:
                leg.remove()
        except Exception:
            pass

    def _render_db_overlay_if_possible(self):
        """
        Draw DB overlay on the top plot using the currently selected sensor (self.sens_str).

        Does nothing if:
        - overlay checkbox is not enabled
        - no DB station loaded
        - no current station loaded
        - fast-delivery mode active

        If plotting 'ALL', overlays all sensors that exist in both the file station and DB station.
        Otherwise overlays only the currently selected sensor.
        """

        # If checkbox not enabled, never draw overlay.
        if not getattr(self, "_db_overlay_enabled", False):
            return

        # Always clear any existing overlay before re-drawing.
        self._clear_db_overlay_artists()

        # Must have base station + db station.
        if not getattr(self, "station", None):
            return
        if not getattr(self, "_db_overlay_station", None):
            return

        # If fast delivery view is active, skip overlay.
        if hasattr(self, "fd_active") and self.fd_active:
            return

        # Need an active sensor selection and it must not be ALL.
        sens = getattr(self, "sens_str", None)
        # If we're plotting ALL, overlay all sensors that exist in both stations.
        def _norm(k):
            return str(k).strip().upper()

        if getattr(self, "_plotting_all", False):
            base_keys_raw = list(self.station.aggregate_months.get("data", {}).keys())
            db_keys_raw   = list(self._db_overlay_station.aggregate_months.get("data", {}).keys())

            base_map = {_norm(k): k for k in base_keys_raw}
            db_map   = {_norm(k): k for k in db_keys_raw}

            common = sorted(set(base_map) & set(db_map))
            # drop non-sensors
            common = [k for k in common if k not in ("ALL")]

            # store as pairs so we can index each station correctly even if raw keys differ
            sens_list = [(base_map[k], db_map[k], k) for k in common]
        else:
            if not sens:
                return

            # Resolve raw keys in each station using normalized mapping (robust to case/whitespace).
            base_keys_raw = list(self.station.aggregate_months.get("data", {}).keys())
            db_keys_raw = list(self._db_overlay_station.aggregate_months.get("data", {}).keys())

            base_map = {_norm(k): k for k in base_keys_raw}
            db_map = {_norm(k): k for k in db_keys_raw}

            k_norm = _norm(sens)
            base_sens = base_map.get(k_norm)
            db_sens = db_map.get(k_norm)

            if base_sens is None or db_sens is None:
                return  # sensor not present in one of the stations

            sens_list = [(base_sens, db_sens, k_norm)]

        # If DB station doesn't have this sensor, skip silently.
        for base_sens, db_sens, label_sens in sens_list:
            try:
                t_db = self._db_overlay_station.aggregate_months["time"][db_sens]
                y_db = self._db_overlay_station.aggregate_months["data"][db_sens]
            except Exception:
                continue

            # Copy database data to np array.
            y_db = np.array(y_db, dtype=float, copy=True)

            # Mask known missing data sentinels in meters.
            y_db[np.isclose(y_db, 9.999) | (y_db == 9999.0)] = np.nan

            # Convert meters (DB) -> millimeters (file data units).
            y_db = y_db * 1000.0

            # Mask other found missing value for de-meaning.
            y_db[y_db == -131072.0] = np.nan

            # -------- DEBUG PRINT --------
            debug_print_db_series(label_sens, t_db, y_db)
            # -----------------------------

            # In ALL mode, match file plotting behavior: demean each series.
            if getattr(self, "_plotting_all", False):
                if _db_debug_enabled():
                    logging.info(
                        "DB overlay ALL: sens=%s db_sens=%r n=%d finite=%d mean=%.3f",
                        label_sens, db_sens, len(y_db), int(np.isfinite(y_db).sum()), float(np.nanmean(y_db))
                    )

                    # --- DEBUG: distribution + extreme negatives ---
                    finite = y_db[np.isfinite(y_db)]
                    if finite.size > 0:
                        p = np.nanpercentile(finite, [0, 0.1, 1, 5, 50, 95, 99, 99.9, 100])
                        logging.info(
                            "DB overlay ALL dist %s: n=%d finite=%d "
                            "p0=%.3f p0.1=%.3f p1=%.3f p5=%.3f p50=%.3f p95=%.3f p99=%.3f p99.9=%.3f p100=%.3f",
                            label_sens, len(y_db), finite.size,
                            p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8]
                        )

                        # Print the 10 most negative finite values with timestamps
                        idx_finite = np.where(np.isfinite(y_db))[0]
                        order = np.argsort(y_db[idx_finite])  # ascending
                        worst = idx_finite[order[:10]]
                        rows = [(str(t_db[i]), float(y_db[i])) for i in worst]
                        logging.info("DB overlay ALL worst negatives %s (time, y_mm): %s", label_sens, rows)
                    # --- end DEBUG ---

                m = np.nanmean(y_db)
                if np.isnan(m):
                    m = 0.0
                y_plot = y_db - m
                logging.info("DB overlay ALL demean check %s: mean_before=%.3f mean_after=%.3f",
                            label_sens, float(m), float(np.nanmean(y_plot)))
            else:
                y_plot = y_db

            # Plot overlay (use default color cycle; style distinguishes it).
            try:
                line_db, = self._static_ax.plot(t_db, y_plot, '--', lw=0.8, alpha=0.3, label=f"{label_sens} (DB)")
                self._db_overlay_artists.append(line_db)
            except Exception:
                continue

        # Rebuild legend once (includes file lines + all DB lines).
        try:
            self._static_ax.legend(loc="best")
        except Exception:
            pass

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

        # Commit the current interactive plot edits before saving.
        # _update_top_canvas() uses a plotting copy so database overlay work cannot
        # mutate station data accidentally; this explicit commit keeps the final
        # output consistent with the points the user deleted on screen, even if
        # they click Save without switching sensors first.
        if self.browser is not None and not getattr(self, "_plotting_all", False):
            self.update_graph_values()

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

            # DB upsert hook; executes only when TSDB_EXECUTE_WRITES=1 and test_mode is off. 
            try:
                hook = getattr(self, "db_upsert_hook", None)
                if callable(hook):
                    hook(
                        station=self.station,
                        target_start_yyyymm=target_start_month,
                        target_end_yyyymm=target_end_month,
                        is_test_mode=self.is_test_mode(),
                    )
            except Exception:
                logging.exception("DB upsert hook failed; continuing because file output is primary")

        # Fast delivery export (requires .din path).
        din_path = st.get_path(st.DIN_PATH_KEY)
        if not din_path:
            self.show_custom_message(
                "Warning",
                "The fast delivery data cannot be processed because you haven't selected "
                "the .din file location. Press F1 to open the menu and select it, then "
                "click Save again.",
            )
            return

        # Save fast delivery.
        self.station.save_fast_delivery(din_path=din_path, path=save_path, is_test_mode=self.is_test_mode(),
                                        target_start_yyyymm=target_start_month, target_end_yyyymm=target_end_month,
                                        callback=self.file_saving_notifications)

        try:
            fd_hook = getattr(self, "fd_db_upsert_hook", None)
            if callable(fd_hook):
                fd_hook(
                    station=self.station,
                    target_start_yyyymm=target_start_month,
                    target_end_yyyymm=target_end_month,
                    is_test_mode=self.is_test_mode(),
                )
        except Exception:
            logging.exception("FD DB upsert hook failed; continuing because file output is primary")

        # Annual data saved only if we are not dealing with someone else's hourly data.
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
        station_num_str = str(int(station_num)).zfill(3)
        url = "https://uhslc.soest.hawaii.edu/data/csv/fast/{0}/{1}{2}.csv".format(
            mode, mode[0], station_num_str
        )

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
