import sys
import os
import wx
import usb1
import pylibftdi
import time
from threading import Thread
from wx.lib.pubsub import pub
from ecu import *

class USBMonitor(Thread):

	def __init__(self, parent):
		self.parent = parent
		self.usbcontext = usb1.USBContext()
		self.ftdi_devices = {}
		Thread.__init__(self)

	def run(self):
		while self.parent.run:
			time.sleep(.5)
			try:
				new_devices = {}
				for device in self.usbcontext.getDeviceList(skip_on_error=True):
					if device.getVendorID() == pylibftdi.driver.FTDI_VENDOR_ID and device.getProductID() in pylibftdi.driver.USB_PID_LIST:
						serial = device.getSerialNumber()
						new_devices[serial] = device
						if not serial in self.ftdi_devices:
							pub.sendMessage("USBMonitor", action="add", device=str(device), serial=serial)
				for serial in self.ftdi_devices:
					if not serial in new_devices:
						pub.sendMessage("USBMonitor", action="remove", device=str(device), serial=serial)
				self.ftdi_devices = new_devices
			except usb1.USBErrorPipe:
				pass
			except usb1.USBErrorNoDevice:
				pass
			except usb1.USBErrorIO:
				pass
			except usb1.USBErrorBusy:
				pass

class KlineWorker(Thread):

	def __init__(self, parent):
		self.parent = parent
		self.ecu = None
		self.ready = False
		pub.subscribe(self.DeviceHandler, "HondaECU.device")
		Thread.__init__(self)

	def DeviceHandler(self, action, device, serial):
		if action == "deactivate":
			if self.ecu:
				wx.LogVerbose("Deactivating device (%s | %s)" % (device, serial))
				self.ecu.dev.close()
				del self.ecu
				self.ecu = None
				self.ready = False
				self.state = 0
		elif action == "activate":
			wx.LogVerbose("Activating device (%s | %s)" % (device, serial))
			self.ecu = HondaECU(device_id=serial, dprint=wx.LogDebug)
			self.ecu.setup()
			self.ecu.wakeup()
			self.ready = True
			self.state = 0

	def run(self):
		while self.parent.run:
			if self.ready and self.ecu:
				self.state, status = self.ecu.detect_ecu_state()
				wx.LogVerbose("ECU state: %s" % (status))
				if self.state == 1:
					tables = " ".join([hex(x) for x in self.ecu.probe_tables()])
					wx.LogVerbose("HDS tables: %s" % tables)

class HondaECU_GUI(wx.Frame):

	def __init__(self, args, version):
		# Initialize GUI things
		wx.Log.SetActiveTarget(wx.LogStderr())
		wx.Log.SetVerbose(args.verbose)
		if not args.debug:
			wx.Log.SetLogLevel(wx.LOG_Info)
		self.run = True
		self.active_device = None
		self.devices = {}
		title = "HondaECU %s" % (version)
		if getattr(sys, 'frozen', False):
			self.basepath = sys._MEIPASS
		else:
			self.basepath = os.path.dirname(os.path.realpath(__file__))
		ip = os.path.join(self.basepath,"honda.ico")

		# Initialize threads
		self.usbmonitor = USBMonitor(self)
		self.klineworker = KlineWorker(self)

		# Setup GUI
		wx.Frame.__init__(self, None, title=title)
		self.SetMinSize(wx.Size(800,600))
		ib = wx.IconBundle()
		ib.AddIcon(ip)
		self.SetIcons(ib)

		# Bind event handlers
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		pub.subscribe(self.USBMonitorHandler, "USBMonitor")

		# Post GUI-setup actions
		self.Centre()
		self.Show()
		self.usbmonitor.start()
		self.klineworker.start()

	def OnClose(self, event):
		self.run = False
		self.usbmonitor.join()
		self.klineworker.join()
		for w in wx.GetTopLevelWindows():
			w.Destroy()

	def USBMonitorHandler(self, action, device, serial):
		if action == "add":
			wx.LogVerbose("Adding device (%s | %s)" % (device, serial))
			if not serial in self.devices:
				self.devices[serial] = device
		elif action =="remove":
			wx.LogVerbose("Removing device (%s | %s)" % (device, serial))
			if serial in self.devices:
				if serial == self.active_device:
					pub.sendMessage("HondaECU.device", action="deactivate", device=self.devices[self.active_device], serial=self.active_device)
					self.active_device = None
				del self.devices[serial]
		if not self.active_device and len(self.devices) > 0:
			self.active_device = list(self.devices.keys())[0]
			pub.sendMessage("HondaECU.device", action="activate", device=self.devices[self.active_device], serial=self.active_device)
