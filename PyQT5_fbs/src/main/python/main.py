import sys

from PyQt5 import QtWidgets
from fbs_runtime.application_context import cached_property
from fbs_runtime.application_context.PyQt5 import ApplicationContext

from my_widgets import *
from uhslc_station_tools.extractor import load_station_data
from uhslc_station_tools.utils import is_valid_files
from uhslcdesign import Ui_MainWindow
# from qt_material import apply_stylesheet
# import darkdetect

if is_pyqt5():
    pass
else:
    pass


class AppContext(ApplicationContext):  # 1. Subclass ApplicationContext
    def run(self):  # 2. Implement run()
        version = self.build_settings["version"]
        name = self.build_settings["app_name"]
        # if sys.platform == 'darwin' and darkdetect.isDark():
        #     p = self.app.palette()
        #     p.setColor(QPalette.Base, QColor(101, 101, 101))
        #     p.setColor(QPalette.WindowText, QColor(231, 231, 231))
        #     p.setColor(QPalette.Text, QColor(231, 231, 231))
        #     self.app.setPalette(p)
        self.window.setWindowTitle(name + " v" + str(version))
        self.window.show()
        return self.app.exec_()  # 3. End run() with this line

    @cached_property
    def window(self):
        return ApplicationWindow()


class ApplicationWindow(QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Create Screen objects
        self.start_screen = Start(self.ui)
        self.help_screen = HelpScreen(self.ui)

        self.ui.actionInstructions.triggered.connect(lambda: self.ui.stackedWidget.setCurrentIndex(1))
        self.ui.backButton.clicked.connect(lambda: self.ui.stackedWidget.setCurrentIndex(0))

        close_app = self.ui.actionQuit
        close_app.triggered.connect(self.close_application)

        open_file = self.ui.actionOpen
        open_file.triggered.connect(self.file_open)

        reload_file = self.ui.actionReload
        reload_file.triggered.connect(self.get_loaded_files)

        opents_file = self.ui.actionOpen_TS
        opents_file.triggered.connect(self.open_ts)

    def file_open(self, reload=False, ts=False):
        if not reload:
            # filters = "s*.dat;; ts*.dat"
            if ts:
                filters = "t*.dat"
            else:
                filters = "s*.dat"
            if ts:
                if st.get_path(st.SAVE_KEY):
                    path = st.get_path(st.SAVE_KEY)
                else:
                    # path = "C:\\Users\\komar\\OneDrive\\Desktop\\monp"
                    path = os.path.expanduser('~')
            else:
                if st.get_path(st.LOAD_KEY):
                    path = st.get_path(st.LOAD_KEY)
                else:
                    # path = "C:\\Users\\komar\\OneDrive\\Desktop\\monp"
                    path = os.path.expanduser('~')
            self.file_name = QtWidgets.QFileDialog.getOpenFileNames(self, 'Open File', path, filters)

        # Validating files selected.
        if is_valid_files(self.file_name[0]):
            pass
        else:
            self.critical_dialog(title="ERROR",
                                 text="Warning, wrong files selected",
                                 info_text=("Files must be from the same station and be consecutive months "
                                            "in chronological order (e.g., Dec → Jan is allowed). "
                                            "Please select valid files to continue."),
                                 details=''''MAC:
            The files are loaded in order in which they were selected. Select files from the oldest to the youngest.\nWINDOWS:
            The order is determined by the file order in the File Explorer. The files should be sorted by name before selecting them.
            ''')
            return

        try:
            # self.file_name[0] is an array of filenames loaded.
            month_count = len(self.file_name[0])
            self.ui.lineEdit_2.setText("Loaded: " + str(month_count) + " months")

            station = load_station_data(self.file_name[0])

            self.start_screen.station = station
            self.start_screen.make_sensor_buttons(station.month_collection[0].sensor_collection.sensors)

        except (FileNotFoundError, IndexError) as e:
            print('Error:', e)

    def critical_dialog(self, title, text, info_text, details):
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setInformativeText(info_text)
        msg_box.setDetailedText(str(details))
        msg_box.setDefaultButton(QtWidgets.QMessageBox.Ok)
        msg_box.exec_()

    def close_application(self):
        choice = QtWidgets.QMessageBox.question(self, 'Warning', "Are you sure you want to quit?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if choice == QtWidgets.QMessageBox.Yes:
            sys.exit()
        else:
            pass

    def get_loaded_files(self):
        self.file_open(reload=True)

    def open_ts(self):
        self.file_open(reload=False, ts=True)
        # return self.file_name;


if __name__ == '__main__':
    appctxt = AppContext()  # 4. Instantiate the subclass
    # apply_stylesheet(appctxt.app, theme='dark_blue.xml')
    exit_code = appctxt.run()  # 5. Invoke run()
    sys.exit(exit_code)
