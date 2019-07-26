import sys
import time
import wx
import usb.backend.libusb1
from ctypes import c_void_p, c_int
import usb.core
import usb.util
import pyftdi.ftdi
from threading import Thread
from pydispatch import dispatcher

class USBMonitor(Thread):

	def __init__(self, parent):
		self.parent = parent
		self.ftdi_devices = {}
		self.backend = None
		# self.backend = usb.backend.libusb1.get_backend(find_library=lambda x: "libusb-1.0.dll")
		# if self.backend:
		# 	self.backend.lib.libusb_set_option.argtypes = [c_void_p, c_int]
		# 	self.backend.lib.libusb_set_option(self.backend.ctx, 1)
		Thread.__init__(self)

	def run(self):
		while self.parent.run:
			time.sleep(.5)
			new_devices = {}
			if self.backend:
				devices = usb.core.find(find_all=True, idVendor=pyftdi.ftdi.Ftdi.FTDI_VENDOR, backend=self.backend)
			else:
				devices = usb.core.find(find_all=True, idVendor=pyftdi.ftdi.Ftdi.FTDI_VENDOR)
			for cfg in devices:
				device = "%03d:%03d" % (cfg.bus,cfg.address)
				new_devices[device] = cfg
				if not device in self.ftdi_devices:
					wx.CallAfter(dispatcher.send, signal="USBMonitor", sender=self, action="add", device=device, config=cfg)
			for device in self.ftdi_devices:
				if not device in new_devices:
					wx.CallAfter(dispatcher.send, signal="USBMonitor", sender=self, action="remove", device=device, config=self.ftdi_devices[device])
			self.ftdi_devices = new_devices
