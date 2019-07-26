import sys
import time
import wx
import usb.core
import usb.util
import pyftdi.ftdi
from threading import Thread
from pydispatch import dispatcher

class USBMonitor(Thread):

	def __init__(self, parent):
		self.parent = parent
		self.ftdi_devices = {}
		Thread.__init__(self)

	def run(self):
		while self.parent.run:
			time.sleep(.5)
			new_devices = {}
			for cfg in usb.core.find(find_all=True, idVendor=pyftdi.ftdi.Ftdi.FTDI_VENDOR):
				device = "%03d:%03d" % (cfg.bus,cfg.address)
				new_devices[device] = cfg
				if not device in self.ftdi_devices:
					wx.CallAfter(dispatcher.send, signal="USBMonitor", sender=self, action="add", device=device, config=cfg)
			for device in self.ftdi_devices:
				if not device in new_devices:
					wx.CallAfter(dispatcher.send, signal="USBMonitor", sender=self, action="remove", device=device, config=self.ftdi_devices[device])
			self.ftdi_devices = new_devices
