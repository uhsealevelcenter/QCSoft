# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:/Users/komar/AppData/Local/Temp/stacked_designDpdhnE.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1199, 894)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.stackedWidget = QtWidgets.QStackedWidget(self.centralwidget)
        self.stackedWidget.setAutoFillBackground(False)
        self.stackedWidget.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.stackedWidget.setFrameShadow(QtWidgets.QFrame.Plain)
        self.stackedWidget.setObjectName("stackedWidget")
        self.page = QtWidgets.QWidget()
        self.page.setEnabled(True)
        self.page.setObjectName("page")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.page)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.verticalLayout_left_main = QtWidgets.QVBoxLayout()
        self.verticalLayout_left_main.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.verticalLayout_left_main.setObjectName("verticalLayout_left_main")
        # self.label_3 = QtWidgets.QLabel(self.page)
        # self.label_3.setToolTip("")
        # self.label_3.setAlignment(QtCore.Qt.AlignCenter)
        # self.label_3.setObjectName("label_3")
        # self.verticalLayout_left_main.addWidget(self.label_3)
        self.switchwidget = SwitchWidget(self.page)
        self.switchwidget.setMaximumSize(QtCore.QSize(120, 80))
        self.switchwidget.setObjectName("switchwidget")
        self.verticalLayout_left_main.addWidget(self.switchwidget)
        self.save_btn = QtWidgets.QPushButton(self.page)
        self.save_btn.setToolTipDuration(-1)
        self.save_btn.setAutoDefault(False)
        self.save_btn.setDefault(False)
        self.save_btn.setFlat(False)
        self.save_btn.setObjectName("save_btn")
        self.verticalLayout_left_main.addWidget(self.save_btn)
        self.verticalLayout_left_top_main = QtWidgets.QVBoxLayout()
        self.verticalLayout_left_top_main.setObjectName("verticalLayout_left_top_main")
        self.line_2 = QtWidgets.QFrame(self.page)
        self.line_2.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_2.setObjectName("line_2")
        self.verticalLayout_left_top_main.addWidget(self.line_2)
        self.verticalLayout_left_top = QtWidgets.QVBoxLayout()
        self.verticalLayout_left_top.setObjectName("verticalLayout_left_top")
        self.radioButton = QtWidgets.QRadioButton(self.page)
        self.radioButton.setChecked(True)
        self.radioButton.setObjectName("radioButton")
        self.buttonGroup_data = QtWidgets.QButtonGroup(MainWindow)
        self.buttonGroup_data.setObjectName("buttonGroup_data")
        self.buttonGroup_data.addButton(self.radioButton)
        self.verticalLayout_left_top.addWidget(self.radioButton)
        self.radioButton_4 = QtWidgets.QRadioButton(self.page)
        self.radioButton_4.setObjectName("radioButton_4")
        self.buttonGroup_data.addButton(self.radioButton_4)
        self.verticalLayout_left_top.addWidget(self.radioButton_4)
        self.radioButton_3 = QtWidgets.QRadioButton(self.page)
        self.radioButton_3.setObjectName("radioButton_3")
        self.buttonGroup_data.addButton(self.radioButton_3)
        self.verticalLayout_left_top.addWidget(self.radioButton_3)
        self.radioButton_2 = QtWidgets.QRadioButton(self.page)
        self.radioButton_2.setObjectName("radioButton_2")
        self.buttonGroup_data.addButton(self.radioButton_2)
        self.verticalLayout_left_top.addWidget(self.radioButton_2)
        self.verticalLayout_left_top_main.addLayout(self.verticalLayout_left_top)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_left_top_main.addItem(spacerItem)
        self.verticalLayout_left_main.addLayout(self.verticalLayout_left_top_main)
        self.line = QtWidgets.QFrame(self.page)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout_left_main.addWidget(self.line)
        self.verticalLayout_bottom_main = QtWidgets.QVBoxLayout()
        self.verticalLayout_bottom_main.setObjectName("verticalLayout_bottom_main")
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_bottom_main.addItem(spacerItem1)
        self.verticalLayout_bottom = QtWidgets.QVBoxLayout()
        self.verticalLayout_bottom.setObjectName("verticalLayout_bottom")
        self.checkBox = QtWidgets.QCheckBox(self.page)
        self.checkBox.setEnabled(True)
        self.checkBox.setChecked(False)
        self.checkBox.setObjectName("checkBox")
        self.buttonGroup_residual = QtWidgets.QButtonGroup(MainWindow)
        self.buttonGroup_residual.setObjectName("buttonGroup_residual")
        self.buttonGroup_residual.setExclusive(False)
        self.buttonGroup_residual.addButton(self.checkBox)
        self.verticalLayout_bottom.addWidget(self.checkBox)
        self.checkBox_2 = QtWidgets.QCheckBox(self.page)
        self.checkBox_2.setChecked(False)
        self.checkBox_2.setObjectName("checkBox_2")
        self.buttonGroup_residual.addButton(self.checkBox_2)
        self.verticalLayout_bottom.addWidget(self.checkBox_2)
        self.checkBox_3 = QtWidgets.QCheckBox(self.page)
        self.checkBox_3.setChecked(False)
        self.checkBox_3.setObjectName("checkBox_3")
        self.buttonGroup_residual.addButton(self.checkBox_3)
        self.verticalLayout_bottom.addWidget(self.checkBox_3)
        self.checkBox_4 = QtWidgets.QCheckBox(self.page)
        self.checkBox_4.setChecked(False)
        self.checkBox_4.setAutoRepeat(False)
        self.checkBox_4.setAutoExclusive(False)
        self.checkBox_4.setTristate(False)
        self.checkBox_4.setObjectName("checkBox_4")
        self.buttonGroup_residual.addButton(self.checkBox_4)
        self.verticalLayout_bottom.addWidget(self.checkBox_4)
        self.verticalLayout_bottom_main.addLayout(self.verticalLayout_bottom)
        self.line_3 = QtWidgets.QFrame(self.page)
        self.line_3.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_3.setObjectName("line_3")
        self.verticalLayout_bottom_main.addWidget(self.line_3)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.radioButton_Hourly = QtWidgets.QRadioButton(self.page)
        self.radioButton_Hourly.setChecked(False)
        self.radioButton_Hourly.setObjectName("radioButton_Hourly")
        self.buttonGroup_resolution = QtWidgets.QButtonGroup(MainWindow)
        self.buttonGroup_resolution.setObjectName("buttonGroup_resolution")
        self.buttonGroup_resolution.addButton(self.radioButton_Hourly)
        self.verticalLayout.addWidget(self.radioButton_Hourly)
        self.radioButton_Minute = QtWidgets.QRadioButton(self.page)
        self.radioButton_Minute.setChecked(True)
        self.radioButton_Minute.setObjectName("radioButton_Minute")
        self.buttonGroup_resolution.addButton(self.radioButton_Minute)
        self.verticalLayout.addWidget(self.radioButton_Minute)
        self.verticalLayout_bottom_main.addLayout(self.verticalLayout)
        self.verticalLayout_left_main.addLayout(self.verticalLayout_bottom_main)
        self.gridLayout_2.addLayout(self.verticalLayout_left_main, 0, 0, 1, 1)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.page)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.lineEdit = QtWidgets.QLineEdit(self.page)
        self.lineEdit.setEnabled(True)
        self.lineEdit.setMinimumSize(QtCore.QSize(100, 0))
        self.lineEdit.setAcceptDrops(True)
        self.lineEdit.setReadOnly(True)
        self.lineEdit.setObjectName("lineEdit")
        self.horizontalLayout.addWidget(self.lineEdit)
        self.label_2 = QtWidgets.QLabel(self.page)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.lineEdit_2 = QtWidgets.QLineEdit(self.page)
        self.lineEdit_2.setEnabled(True)
        self.lineEdit_2.setMinimumSize(QtCore.QSize(100, 0))
        self.lineEdit_2.setMaximumSize(QtCore.QSize(150, 16777215))
        self.lineEdit_2.setDragEnabled(False)
        self.lineEdit_2.setReadOnly(True)
        self.lineEdit_2.setObjectName("lineEdit_2")
        self.horizontalLayout.addWidget(self.lineEdit_2)
        self.refLevelEdit = QtWidgets.QLineEdit(self.page)
        self.refLevelEdit.setMinimumSize(QtCore.QSize(100, 0))
        self.refLevelEdit.setMaximumSize(QtCore.QSize(150, 16777215))
        self.refLevelEdit.setMaxLength(32000)
        self.refLevelEdit.setObjectName("refLevelEdit")
        self.horizontalLayout.addWidget(self.refLevelEdit)
        self.ref_level_btn = QtWidgets.QPushButton(self.page)
        self.ref_level_btn.setObjectName("ref_level_btn")
        self.horizontalLayout.addWidget(self.ref_level_btn)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.mplwidget_top = MatplotlibWidget(self.page)
        self.mplwidget_top.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
        self.mplwidget_top.setStyleSheet("background-color: rgb(255, 255, 255);\n"
"font: 8pt \"Arial\";")
        self.mplwidget_top.setObjectName("mplwidget_top")
        self.verticalLayout_2.addWidget(self.mplwidget_top)
        self.mplwidget_bottom = MatplotlibWidget(self.page)
        self.mplwidget_bottom.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.mplwidget_bottom.setObjectName("mplwidget_bottom")
        self.verticalLayout_2.addWidget(self.mplwidget_bottom)
        self.gridLayout_2.addLayout(self.verticalLayout_2, 0, 1, 1, 1)
        self.stackedWidget.addWidget(self.page)
        self.page_2 = QtWidgets.QWidget()
        self.page_2.setEnabled(True)
        self.page_2.setObjectName("page_2")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.page_2)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.gridLayout_3 = QtWidgets.QGridLayout()
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.label_title = QtWidgets.QLabel(self.page_2)
        self.label_title.setEnabled(True)
        self.label_title.setMaximumSize(QtCore.QSize(16777215, 50))
        font = QtGui.QFont()
        font.setPointSize(16)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.label_title.setFont(font)
        self.label_title.setAlignment(QtCore.Qt.AlignCenter)
        self.label_title.setObjectName("label_title")
        self.verticalLayout_3.addWidget(self.label_title)
        self.textBrowser = QtWidgets.QTextBrowser(self.page_2)
        self.textBrowser.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.textBrowser.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.textBrowser.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.textBrowser.setObjectName("textBrowser")
        self.verticalLayout_3.addWidget(self.textBrowser)
        self.line_4 = QtWidgets.QFrame(self.page_2)
        self.line_4.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_4.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_4.setObjectName("line_4")
        self.verticalLayout_3.addWidget(self.line_4)
        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.gridLayout_5 = QtWidgets.QGridLayout()
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.pushButton_load_folder = QtWidgets.QPushButton(self.page_2)
        self.pushButton_load_folder.setObjectName("pushButton_load_folder")
        self.gridLayout_5.addWidget(self.pushButton_load_folder, 1, 1, 1, 1)
        self.lineEdit_din = QtWidgets.QLineEdit(self.page_2)
        self.lineEdit_din.setReadOnly(True)
        self.lineEdit_din.setObjectName("lineEdit_din")
        self.gridLayout_5.addWidget(self.lineEdit_din, 2, 0, 1, 1)
        self.pushButton_din = QtWidgets.QPushButton(self.page_2)
        self.pushButton_din.setObjectName("pushButton_din")
        self.gridLayout_5.addWidget(self.pushButton_din, 2, 1, 1, 1)
        self.lineEditLoadPath = QtWidgets.QLineEdit(self.page_2)
        self.lineEditLoadPath.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEditLoadPath.sizePolicy().hasHeightForWidth())
        self.lineEditLoadPath.setSizePolicy(sizePolicy)
        self.lineEditLoadPath.setReadOnly(True)
        self.lineEditLoadPath.setObjectName("lineEditLoadPath")
        self.gridLayout_5.addWidget(self.lineEditLoadPath, 1, 0, 1, 1)
        self.pushButton_save_folder = QtWidgets.QPushButton(self.page_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_save_folder.sizePolicy().hasHeightForWidth())
        self.pushButton_save_folder.setSizePolicy(sizePolicy)
        self.pushButton_save_folder.setMaximumSize(QtCore.QSize(200, 16777215))
        self.pushButton_save_folder.setObjectName("pushButton_save_folder")
        self.gridLayout_5.addWidget(self.pushButton_save_folder, 0, 1, 1, 1)
        self.lineEditPath = QtWidgets.QLineEdit(self.page_2)
        self.lineEditPath.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEditPath.sizePolicy().hasHeightForWidth())
        self.lineEditPath.setSizePolicy(sizePolicy)
        self.lineEditPath.setReadOnly(True)
        self.lineEditPath.setPlaceholderText("")
        self.lineEditPath.setObjectName("lineEditPath")
        self.gridLayout_5.addWidget(self.lineEditPath, 0, 0, 1, 1)
        self.verticalLayout_4.addLayout(self.gridLayout_5)
        self.backButton = QtWidgets.QPushButton(self.page_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.backButton.sizePolicy().hasHeightForWidth())
        self.backButton.setSizePolicy(sizePolicy)
        self.backButton.setMaximumSize(QtCore.QSize(200, 16777215))
        self.backButton.setObjectName("backButton")
        self.verticalLayout_4.addWidget(self.backButton)
        self.verticalLayout_3.addLayout(self.verticalLayout_4)
        self.gridLayout_3.addLayout(self.verticalLayout_3, 0, 0, 1, 1)
        self.gridLayout_4.addLayout(self.gridLayout_3, 0, 0, 1, 1)
        self.stackedWidget.addWidget(self.page_2)
        self.gridLayout.addWidget(self.stackedWidget, 0, 1, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1199, 18))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuHelp = QtWidgets.QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionOpen = QtWidgets.QAction(MainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.actionOpen_TS = QtWidgets.QAction(MainWindow)
        self.actionOpen_TS.setObjectName("actionOpen_TS")
        self.actionReload = QtWidgets.QAction(MainWindow)
        self.actionReload.setObjectName("actionReload")
        self.actionQuit = QtWidgets.QAction(MainWindow)
        self.actionQuit.setObjectName("actionQuit")
        self.actionInstructions = QtWidgets.QAction(MainWindow)
        self.actionInstructions.setObjectName("actionInstructions")
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionReload)
        self.menuFile.addAction(self.actionOpen_TS)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionQuit)
        self.menuHelp.addAction(self.actionInstructions)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        self.stackedWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        # self.label_3.setText(_translate("MainWindow", "Production"))
        self.save_btn.setToolTip(_translate("MainWindow", "<html><head/><body><p>Testing ToolTip</p></body></html>"))
        self.save_btn.setText(_translate("MainWindow", "Save"))
        self.radioButton.setText(_translate("MainWindow", "PRD"))
        self.radioButton_4.setText(_translate("MainWindow", "Sensor3"))
        self.radioButton_3.setText(_translate("MainWindow", "Sensor2"))
        self.radioButton_2.setText(_translate("MainWindow", "Sensor1"))
        self.checkBox.setText(_translate("MainWindow", "PRD"))
        self.checkBox_2.setText(_translate("MainWindow", "Sensor1"))
        self.checkBox_3.setText(_translate("MainWindow", "Sensor2"))
        self.checkBox_4.setText(_translate("MainWindow", "Sensor3"))
        self.radioButton_Hourly.setText(_translate("MainWindow", "Hourly"))
        self.radioButton_Minute.setText(_translate("MainWindow", "Minute"))
        self.label.setText(_translate("MainWindow", "Meta Data:"))
        self.label_2.setText(_translate("MainWindow", "Months:"))
        self.refLevelEdit.setPlaceholderText(_translate("MainWindow", "Enter New Ref Level"))
        self.ref_level_btn.setText(_translate("MainWindow", "Change Ref Level"))
        self.label_title.setText(_translate("MainWindow", "Software manual"))
        self.textBrowser.setHtml(_translate("MainWindow",
                                            "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
                                            "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
                                            "p, li { white-space: pre-wrap; }\n"
                                            "</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8pt; font-weight:400; font-style:normal;\">\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">INITIAL SETUP:</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">------------------</span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">To save/load files to/from a server, connect to a server from your operating system (e.g CMD + K on a MAC, WIN + R on Windows), and then follow the instruction below:</span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">    1) Specify the default loading folder by clicking &quot;Change Load Folder&quot; button</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">    2) Specify the default saving folder by clicking &quot;Change Save Folder&quot; button</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">    3) Specify the .din file path to load stations sensrors information</span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">FOLDER STRUCTURE:</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">-------------------------</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Inside the folder specified in step (2) above the strucuture would look as following:</span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">Your-chosen-folder/</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|</span><span style=\" font-size:12pt; font-weight:600;\"> -- production_data/</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    | -- high_frequency/</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     | -- t123/</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     |    | --  2019/</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     |    |      | -- t123201901enc.mat</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     |    |      | -- t123201901rad.mat</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     |    |      | -- t123201901prs.mat</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     |    |      | -- t1231901enc.dat</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    | -- fast_delivery/ </span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     | -- t123/</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     |    | --  2019</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     |    |      | -- th1231901.dat</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     |    |      | -- th1231901.mat</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     |    |      | -- da1231901.dat</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    |     |    |      | -- da1231901.mat</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|</span><span style=\" font-size:12pt; font-weight:600;\"> -- test_data/</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    | -- high_frequency/</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">|    | -- fast_delivery/</span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Data inside of both the </span><span style=\" font-size:12pt; font-weight:600;\">high_frequency</span><span style=\" font-size:12pt;\"> and </span><span style=\" font-size:12pt; font-weight:600;\">fast_delivery</span><span style=\" font-size:12pt;\"> folders will contain subdirectories (one for each station -- e.g. </span><span style=\" font-size:12pt; font-weight:600;\">t123</span><span style=\" font-size:12pt;\">) letter t followed by a three digit station ID. And then every station folder will have a subfolder for each year that data belongs to (e.g. </span><span style=\" font-size:12pt; font-weight:600;\">2019</span><span style=\" font-size:12pt;\">). The station subfolder in </span><span style=\" font-size:12pt; font-weight:600;\">high_frequency</span><span style=\" font-size:12pt;\"> directory will contain multiple yearly, high frequency .mat files, which are created by appending multiple monthy high frequency .mat files for the corresponding year (not shown in the folder structure above). </span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Note that the high frequency .mat files are in the following format:</span></p>\n"
                                            "<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">t</span><span style=\" font-size:12pt;\">&lt;three_digit_station_ID&gt;</span><span style=\" font-size:12pt; font-weight:600;\">YYYYMM</span><span style=\" font-size:12pt;\">&lt;three_letter_sensor&gt;</span><span style=\" font-size:12pt; font-weight:600;\">.mat</span></p>\n"
                                            "<p align=\"center\" style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt; font-weight:600;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">High frequency .dat file (also known as TS file or legacy file) format is the following:</span></p>\n"
                                            "<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">t</span><span style=\" font-size:12pt;\">&lt;three_digit_station_ID&gt;</span><span style=\" font-size:12pt; font-weight:600;\">YYMM</span><span style=\" font-size:12pt;\">&lt;three_letter_sensor&gt;</span><span style=\" font-size:12pt; font-weight:600;\">.mat</span></p>\n"
                                            "<p align=\"center\" style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt; font-weight:600;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Fast delivery hourly and daily data files begin with </span><span style=\" font-size:12pt; font-weight:600;\">th</span><span style=\" font-size:12pt;\"> and </span><span style=\" font-size:12pt; font-weight:600;\">da</span><span style=\" font-size:12pt;\">, respectively, followed by the three-digit station id followed by a two-digit year and two-digit month (see the above folder strucutre and file name examples).</span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">test_data </span><span style=\" font-size:12pt;\">folder is a place where we store the data during testing period. Testing is enabled by switching the testing/produciton toggle. The subfolder structure of the </span><span style=\" font-size:12pt; font-weight:600;\">test_data</span><span style=\" font-size:12pt;\"> folder is exactly the same as the one for </span><span style=\" font-size:12pt; font-weight:600;\">production_data</span><span style=\" font-size:12pt;\">.</span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">If no path is specified, the path will default to your home directory on your local machine or you will be asked to set it up.  If different local directory needs to be used, this can be achieved by performing the same steps above. </span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">DATA LOADING:</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">-------------------</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">        Press CTRL (CMD) + O to load unprocessed (monp) data</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">        Press CTRL (CMD) + T to load processed (ts) data</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">        Press CTRL (CMD) + R to reload the same data file and undo all changes</span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">DATA MANIPULATION:</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">---------------------------</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">        To delete a single data point press &quot;D&quot;</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">        To delete multiple data points use right mouse click (or CTRL + Left Click) to circle the points</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">        To change a reference level for a specific channel, enter a new reference level in &quot;Enter New Reference Level&quot; text box</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">        and then click &quot;Change Ref Level&quot; button. This will prompt you with a calendar and time selector to choose a point when an</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">        adjustment to the reference level was made (usually supplied by technicians). The time/date selector can be modified</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">        incrementally by using UP/DOWN arrows or simply by clicking the desired time/date portion to be changed and typing in</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">        the time of change. Using TAB will scroll through year-month-day hour:minute sections.</span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">DATA NAVIGATION:</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">-----------------------</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Use LEFT and RIGHT arrow to pan through the data</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Press &quot;B&quot; to scroll backward through the individual data points</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Press &quot;N&quot; to scroll forward through the individual data points</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Click on any particular data point to zoom in on that data section</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Press &quot;0&quot; to reset the view back to the entire data set</span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">UNDO ACTIONS:</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">-------------------</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Press CTRL (CMD) + Z to undo data deletion</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Press CTRL (CMD) + B to undo bulk data deletion</span></p>\n"
                                            "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">SAVE DATA:</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">--------------</span></p>\n"
                                            "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Click the &quot;SAVE&quot; button to save changes to a &quot;TS&quot; file</span></p></body></html>"))
        self.pushButton_load_folder.setText(_translate("MainWindow", "Change Load Folder"))
        self.lineEdit_din.setPlaceholderText(_translate("MainWindow", "Click the button on the right to choose the din file from which primary sensors are loaded"))
        self.pushButton_din.setText(_translate("MainWindow", "Set .din file"))
        self.pushButton_save_folder.setText(_translate("MainWindow", "Change Save Folder"))
        self.backButton.setText(_translate("MainWindow", "Back To Main Menu"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuHelp.setTitle(_translate("MainWindow", "Help"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.actionOpen.setShortcut(_translate("MainWindow", "Ctrl+O"))
        self.actionOpen_TS.setText(_translate("MainWindow", "Open TS"))
        self.actionOpen_TS.setShortcut(_translate("MainWindow", "Ctrl+T"))
        self.actionReload.setText(_translate("MainWindow", "Reload"))
        self.actionReload.setShortcut(_translate("MainWindow", "Ctrl+R"))
        self.actionQuit.setText(_translate("MainWindow", "Quit"))
        self.actionQuit.setShortcut(_translate("MainWindow", "Ctrl+Q"))
        self.actionInstructions.setText(_translate("MainWindow", "Instructions"))
        self.actionInstructions.setShortcut(_translate("MainWindow", "F1"))


from MyQTDesignerPlugins.matplotlibwidget import MatplotlibWidget
from MyQTDesignerPlugins.switchwidget import SwitchWidget
