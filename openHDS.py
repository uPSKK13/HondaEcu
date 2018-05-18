#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import pylibftdi

from HondaECU import *

class OpenHDS(QMainWindow):

	def onDeviceActivated(self, idx):
		self.ecu = HondaECU(str(self.devices[idx][2],encoding="latin1"))
		self.ecu.setup()
		if self.ecu.init(debug=True) != None:
			self.statusIcon.setPixmap(QPixmap("status.png"))

	def __init__(self):
		super().__init__()
		self.ecu = None
		self.setWindowTitle('Open Honda Diagnostic System')
		self.setMinimumWidth(400)
		self.layout = QVBoxLayout()
		self.form_layout = QFormLayout()
		self.device_list = QComboBox(self)
		self.devices = pylibftdi.driver.Driver().list_devices()
		self.device_list.addItems([repr(d) for d in self.devices])
		self.device_list.activated[int].connect(self.onDeviceActivated)
		self.form_layout.addRow('Device:', self.device_list)
		self.layout.addLayout(self.form_layout)
		self.tabs = QTabWidget()
		self.info_tab = QWidget()
		self.flash_tab = QWidget()
		self.engine_data_tab = QWidget()
		self.tabs.addTab(self.info_tab,"Info")
		self.tabs.addTab(self.flash_tab,"Flash")
		self.tabs.addTab(self.engine_data_tab,"Engine Data")
		self.layout.addWidget(self.tabs)
		self.centralWidget = QWidget(self)
		self.centralWidget.setLayout(self.layout)
		self.setCentralWidget(self.centralWidget)
		self.statusIcon = QLabel()
		self.statusIcon.setPixmap(QPixmap("status-offline.png"))
		self.statusLabel = QLabel()
		#self.statusLabel.setText('Looking for ECU...')
		self.statusBar = QStatusBar()
		self.statusBar.addWidget(self.statusIcon)
		self.statusBar.addWidget(self.statusLabel)
		self.setStatusBar(self.statusBar)

		if len(self.devices) > 0:
			self.onDeviceActivated(0)

		self.show()

if __name__ == '__main__':

	app = QApplication(sys.argv)
	openHDS = OpenHDS()
	sys.exit(app.exec_())
