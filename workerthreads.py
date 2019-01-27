import time
import wx
from threading import Thread
from pydispatch import dispatcher
from pylibftdi import Driver, FtdiError, LibraryMissingError

from ecu import *

class USBMonitor(Thread):

	def __init__(self, parent):
		self.parent = parent
		self.ftdi_devices = {}
		Thread.__init__(self)

	def run(self):
		while self.parent.run:
			time.sleep(.5)
			new_devices = {}
			try:
				for device in Driver().list_devices():
					vendor, product, serial = map(lambda x: x.decode('latin1'), device)
					new_devices[serial] = (vendor, product)
					if not serial in self.ftdi_devices:
						wx.CallAfter(dispatcher.send, signal="USBMonitor", sender=self, action="add", vendor=vendor, product=product, serial=serial)
				for serial in self.ftdi_devices:
					if not serial in new_devices:
						wx.CallAfter(dispatcher.send, signal="USBMonitor", sender=self, action="remove", vendor=self.ftdi_devices[serial][0], product=self.ftdi_devices[serial][1], serial=serial)
			except FtdiError as e:
				if sys.exc_info()[0] == LibraryMissingError:
					wx.LogError(str(e))
					break
			except LibraryMissingError as e:
				wx.LogError(str(e))
				break
			self.ftdi_devices = new_devices

class KlineWorker(Thread):

	def __init__(self, parent):
		self.parent = parent
		self.__clear_data()
		dispatcher.connect(self.DeviceHandler, signal="FTDIDevice", sender=dispatcher.Any)
		Thread.__init__(self)

	def __cleanup(self):
		if self.ecu:
			self.ecu.dev.close()
			del self.ecu
		self.__clear_data()

	def __clear_data(self):
		self.ecu = None
		self.ready = False
		self.state = 0

	def update_state(self):
		state, status = self.ecu.detect_ecu_state_new()
		if state != self.state:
			self.state = state
			wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="state", value=(self.state,status))

	def DeviceHandler(self, action, vendor, product, serial):
		if action == "interrupt":
			pass
			# self.flash_mode = -1
			# self.update_state()
		elif action == "deactivate":
			if self.ecu:
				# print("Deactivating device (%s : %s : %s)" % (vendor, product, serial))
				self.__cleanup()
		elif action == "activate":
			# print("Activating device (%s : %s : %s)" % (vendor, product, serial))
			self.__clear_data()
			try:
				self.ecu = HondaECU(device_id=serial)
				self.ecu.setup()
				self.ready = True
			except FtdiError:
				pass

	def run(self):
		while self.parent.run:
			if not self.ready:
				time.sleep(.001)
			else:
				try:
					if self.state == 0:
						time.sleep(.250)
						self.update_state()
					else:
						if self.ecu.ping():
							pass
				except FtdiError:
					pass
				except AttributeError:
					pass
				except OSError:
					pass
