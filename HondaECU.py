import os
import sys
import usb1
import pylibftdi
import wx
import wx.adv
import platform
import time
import struct
import argparse

from ecu import *

DEVICE_STATE_ERROR = -2
DEVICE_STATE_UNKNOWN = -1
DEVICE_STATE_SETUP = 0
DEVICE_STATE_CONNECTED = 1
DEVICE_STATE_READY = 2
DEVICE_STATE_POWER_OFF = 3
DEVICE_STATE_POWER_ON = 4
DEVICE_STATE_INIT = 5
DEVICE_STATE_READ_SECURITY = 6
DEVICE_STATE_READ = 7
DEVICE_STATE_WRITE_INIT = 8
DEVICE_STATE_RECOVER_INIT = 9
DEVICE_STATE_ERASE = 10
DEVICE_STATE_ERASE_WAIT = 11
DEVICE_STATE_WRITE = 12
DEVICE_STATE_WRITE_FINALIZE = 13

binsizes = {
	"56k":56,
	"256k":256,
	"512k":512,
	"1024k":1024
}
checksums = [
	"0xDFEF",
	"0x18FFE",
	"0x19FFE",
	"0x1FFFA",
	"0x3FFF8",
	"0x7FFF8",
	"0xFFFF8"
]

class InfoPanel(wx.Panel):

	def __init__(self, gui):
		wx.Panel.__init__(self, gui.notebook)

		self.ecmidl = wx.StaticText(self, label="ECM ID:")
		self.ecmid = wx.StaticText(self, label="")
		self.statusl = wx.StaticText(self, label="Status:")
		self.status = wx.StaticText(self, label="")
		self.flashcountl = wx.StaticText(self,label="Flash count:")
		self.flashcount = wx.StaticText(self, label="")

		self.infopsizer = wx.GridBagSizer(0,0)
		self.infopsizer.Add(self.ecmidl, pos=(0,0), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=10)
		self.infopsizer.Add(self.ecmid, pos=(0,1), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT, border=10)
		self.infopsizer.Add(self.statusl, pos=(1,0), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=10)
		self.infopsizer.Add(self.status, pos=(1,1), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT, border=10)
		self.infopsizer.Add(self.flashcountl, pos=(2,0), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=10)
		self.infopsizer.Add(self.flashcount, pos=(2,1), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT, border=10)
		self.infopsizer.AddGrowableCol(1,1)
		self.SetSizer(self.infopsizer)

class FlashPanel(wx.Panel):

	def __init__(self, gui):
		wx.Panel.__init__(self, gui.notebook)

		self.mode = wx.RadioBox(self, label="Mode", choices=["Read","Write","Recover"])
		self.wfilel = wx.StaticText(self, label="File")
		self.wsizel = wx.StaticText(self, label="Size")
		self.wchecksuml = wx.StaticText(self,label="Checksum")
		self.readfpicker = wx.FilePickerCtrl(self, wildcard="ECU dump (*.bin)|*.bin", style=wx.FLP_SAVE|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)
		self.writefpicker = wx.FilePickerCtrl(self,wildcard="ECU dump (*.bin)|*.bin", style=wx.FLP_OPEN|wx.FLP_FILE_MUST_EXIST|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)
		self.fixchecksum = wx.CheckBox(self, label="Fix")
		self.size = wx.Choice(self, choices=list(binsizes.keys()))
		self.checksum = wx.Choice(self, choices=list(checksums))
		self.gobutton = wx.Button(self, label="Start")

		self.writefpicker.Show(False)
		self.fixchecksum.Show(False)
		self.gobutton.Disable()

		self.fpickerbox = wx.BoxSizer(wx.HORIZONTAL)
		self.fpickerbox.Add(self.readfpicker, 1)
		self.fpickerbox.Add(self.writefpicker, 1)

		self.flashpsizer = wx.GridBagSizer(0,0)
		self.flashpsizer.Add(self.mode, pos=(0,0), span=(1,6), flag=wx.ALL|wx.ALIGN_CENTER, border=20)
		self.flashpsizer.Add(self.wfilel, pos=(1,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.flashpsizer.Add(self.fpickerbox, pos=(1,1), span=(1,5), flag=wx.EXPAND|wx.RIGHT, border=10)
		self.flashpsizer.Add(self.wsizel, pos=(2,0), flag=wx.TOP|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
		self.flashpsizer.Add(self.size, pos=(2,1), span=(1,1), flag=wx.TOP, border=5)
		self.flashpsizer.Add(self.wchecksuml, pos=(2,3), flag=wx.TOP|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
		self.flashpsizer.Add(self.checksum, pos=(2,4), flag=wx.TOP, border=5)
		self.flashpsizer.Add(self.fixchecksum, pos=(2,5), flag=wx.TOP|wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
		self.flashpsizer.Add(self.gobutton, pos=(4,5), flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.BOTTOM|wx.RIGHT, border=10)
		self.flashpsizer.AddGrowableRow(3,1)
		self.flashpsizer.AddGrowableCol(5,1)
		self.SetSizer(self.flashpsizer)

		self.mode.Bind(wx.EVT_RADIOBOX, gui.OnModeChange)
		self.gobutton.Bind(wx.EVT_BUTTON, gui.OnGo)

class FlashDialog(wx.Dialog):

	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, size=(280,230))
		self.parent = parent

		self.offimg = wx.Image(self.parent.offpng, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		self.onimg = wx.Image(self.parent.onpng, wx.BITMAP_TYPE_ANY).ConvertToBitmap()

		self.msg = wx.StaticText(self, label="", style=wx.ALIGN_CENTRE)
		self.msg2 = wx.StaticText(self, label="", style=wx.ALIGN_CENTRE)
		self.image = wx.StaticBitmap(self)
		self.progress = wx.Gauge(self)
		self.progress.SetRange(100)
		self.progress.SetValue(0)

		mainbox = wx.BoxSizer(wx.VERTICAL)
		mainbox.Add(self.msg, 0, wx.ALIGN_CENTER|wx.TOP, 30)
		mainbox.Add(self.image, 0, wx.ALIGN_CENTER|wx.TOP, 10)
		mainbox.Add(self.progress, 0, wx.EXPAND|wx.ALL, 40)
		mainbox.Add(self.msg2, 0, wx.ALIGN_CENTER, 0)
		self.SetSizer(mainbox)

		self.Layout()
		self.Center()

	def WaitOff(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Turn off ECU")
		self.msg2.SetLabel("")
		self.image.SetBitmap(self.offimg)
		self.image.Show(True)
		self.progress.Show(False)
		self.Layout()

	def WaitOn(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Turn on ECU")
		self.msg2.SetLabel("")
		self.image.SetBitmap(self.onimg)
		self.image.Show(True)
		self.progress.Show(False)
		self.Layout()

	def WaitRead(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Reading ECU")
		self.msg2.SetLabel("")
		self.image.SetBitmap(wx.NullBitmap)
		self.image.Show(False)
		self.progress.Show(True)
		self.Layout()

	def WaitWrite(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Writing ECU")
		self.msg2.SetLabel("")
		self.image.SetBitmap(wx.NullBitmap)
		self.image.Show(False)
		self.progress.Show(True)
		self.Layout()

class HondaECU_GUI(wx.Frame):

	def PollUSBDevices(self, event):
		try:
			new_devices = self.usbcontext.getDeviceList(skip_on_error=True)
			for device in new_devices:
				if device.getVendorID() == pylibftdi.driver.FTDI_VENDOR_ID:
					if device.getProductID() in pylibftdi.driver.USB_PID_LIST:
						if not device in self.ftdi_devices:
							if self.args.debug:
								sys.stderr.write("Adding device (%s) to list\n" % device)
							self.ftdi_devices.append(device)
							self.UpdateDeviceList()
			for device in self.ftdi_devices:
				if not device in new_devices:
					if device == self.ftdi_active:
						self.deactivateDevice()
						self.infop.ecmid.SetLabel("")
						self.infop.status.SetLabel("")
						self.infop.flashcount.SetLabel("")
						self.infop.Layout()
					self.ftdi_devices.remove(device)
					self.UpdateDeviceList()
					if self.args.debug:
						sys.stderr.write("Removing device (%s) from list\n" % device)
		except OSError:
			pass

	def hotplug_callback(self, context, device, event):
		if device.getProductID() in pylibftdi.driver.USB_PID_LIST:
			if event == usb1.HOTPLUG_EVENT_DEVICE_ARRIVED:
				if not device in self.ftdi_devices:
					if self.args.debug:
						sys.stderr.write("Adding device (%s) to list\n" % device)
					self.ftdi_devices.append(device)
					self.UpdateDeviceList()
			elif event == usb1.HOTPLUG_EVENT_DEVICE_LEFT:
				if device in self.ftdi_devices:
					if device == self.ftdi_active:
						self.deactivateDevice()
					self.ftdi_devices.remove(device)
					self.UpdateDeviceList()
					if self.args.debug:
						sys.stderr.write("Removing device (%s) from list\n" % device)

	def deactivateDevice(self):
		if self.ecu != None:
			self.ecu.dev.close()
			del self.ecu
			self.ecu = None
		if self.args.debug:
			sys.stderr.write("Deactivating device (%s)\n" % self.ftdi_active)
		self.ftdi_active = None
		self.flashp.gobutton.Disable()
		self.infop.ecmid.SetLabel("")
		self.infop.status.SetLabel("")
		self.infop.flashcount.SetLabel("")
		self.infop.Layout()

	def initRead(self, rom_size):
		self.maxbyte = 1024 * rom_size
		self.nbyte = 0
		self.readsize = 8

	def initWrite(self, rom_size):
		self.i = 0
		self.maxi = len(self.byts)/128
		self.writesize = 128

	def __init__(self, args, usbcontext):
		self.args = args
		self.init_wait = -1
		self.write_wait = -1
		self.ecu = None
		self.device_state = DEVICE_STATE_UNKNOWN
		self.ftdi_devices = []
		self.ftdi_active = None
		self.file = None
		self.usbcontext = usbcontext
		self.usbhotplug = self.usbcontext.hasCapability(usb1.CAP_HAS_HOTPLUG)

		wx.Frame.__init__(self, None, title="HondaECU", size=(560,460), style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))

		self.statusbar = self.CreateStatusBar(1)

		if getattr(sys, 'frozen', False ):
			self.basepath = sys._MEIPASS
		else:
			self.basepath = os.path.dirname(os.path.realpath(__file__))
		ip = os.path.join(self.basepath,"honda.ico")
		self.offpng = os.path.join(self.basepath, "power_off.png")
		self.onpng = os.path.join(self.basepath, "power_on.png")

		ib = wx.IconBundle()
		ib.AddIcon(ip)
		self.SetIcons(ib)

		menuBar = wx.MenuBar()
		menu = wx.Menu()
		m_exit = menu.Append(wx.ID_EXIT, "E&xit\tAlt-X", "Close window and exit program.")
		self.Bind(wx.EVT_MENU, self.OnClose, m_exit)
		menuBar.Append(menu, "&File")
		self.SetMenuBar(menuBar)

		self.panel = wx.Panel(self)

		devicebox = wx.StaticBoxSizer(wx.HORIZONTAL, self.panel, "FTDI Devices")
		self.m_devices = wx.Choice(self.panel, wx.ID_ANY)
		devicebox.Add(self.m_devices, 1, wx.EXPAND | wx.ALL, 5)

		self.notebook = wx.Notebook(self.panel, wx.ID_ANY)
		self.infop = InfoPanel(self)
		self.flashp = FlashPanel(self)

		self.notebook.AddPage(self.infop, "ECU Info")
		self.notebook.AddPage(self.flashp, "Flash Operations")

		datap = wx.Panel(self.notebook)
		self.notebook.AddPage(datap, "Diagnostic Tables")

		errorp = wx.Panel(self.notebook)
		self.notebook.AddPage(errorp, "Error Codes")

		self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
		# self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)

		mainbox = wx.BoxSizer(wx.VERTICAL)
		mainbox.Add(devicebox, 0, wx.EXPAND | wx.ALL, 10)
		mainbox.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 10)
		self.notebook.Layout()
		self.panel.SetSizer(mainbox)
		self.panel.Layout()
		self.Centre()

		self.Bind(wx.EVT_IDLE, self.OnIdle)
		self.m_devices.Bind(wx.EVT_CHOICE, self.OnDeviceSelected)
		self.Bind(wx.EVT_CLOSE, self.OnClose)

		self.flashdlg = FlashDialog(self)

		if self.usbhotplug:
			if self.args.debug:
				sys.stderr.write('Registering hotplug callback...\n')
			self.usbcontext.hotplugRegisterCallback(self.hotplug_callback, vendor_id=pylibftdi.driver.FTDI_VENDOR_ID)
			if self.args.debug:
				sys.stderr.write('Callback registered. Monitoring events.\n')
		else:
			self.usbpolltimer = wx.Timer(self, wx.ID_ANY)
			self.Bind(wx.EVT_TIMER, self.PollUSBDevices)
			self.usbpolltimer.Start(250)

	def OnPageChanged(self, event):
		event.Skip()

	def OnPageChanging(self, event):
		event.Skip()

	def OnGo(self, event):
		self.device_state = DEVICE_STATE_POWER_OFF
		self.flashdlg.WaitOff()
		if self.flashdlg.ShowModal() == 1:
			pass
		else:
			self.device_state = DEVICE_STATE_UNKNOWN
			self.statusbar.SetStatusText("")

	def OnModeChange(self, event):
		if self.flashp.mode.GetSelection() == 0:
			self.flashp.fixchecksum.Show(False)
			self.flashp.writefpicker.Show(False)
			self.flashp.readfpicker.Show(True)
		else:
			self.flashp.fixchecksum.Show(True)
			self.flashp.writefpicker.Show(True)
			self.flashp.readfpicker.Show(False)
		self.flashp.Layout()

	def OnDeviceSelected(self, event):
		self.statusbar.SetStatusText("")
		newdevice = self.ftdi_devices[self.m_devices.GetSelection()]
		if self.ftdi_active != None:
			if self.ftdi_active != newdevice:
				self.deactivateDevice()
		self.ftdi_active = newdevice
		try:
			self.device_state = DEVICE_STATE_UNKNOWN
			self.statusbar.SetStatusText("")
			self.ecu = HondaECU(device_id=self.ftdi_active.getSerialNumber())
			if self.args.debug:
				sys.stderr.write("Activating device (%s)\n" % self.ftdi_active)
			self.device_state = DEVICE_STATE_SETUP
		except usb1.USBErrorNotSupported as e:
			self.ecu = None
			self.statusbar.SetStatusText("Incorrect driver for device, install libusbK with Zadig!")
		except usb1.USBErrorBusy:
			self.ecu = None

	def UpdateDeviceList(self):
		self.m_devices.Clear()
		for i,d in enumerate(self.ftdi_devices):
			n = str(d)
			try:
				n += " | " + d.getSerialNumber()
			except usb1.USBErrorNotSupported:
				pass
			except usb1.USBErrorBusy:
				pass
			except usb1.USBErrorNoDevice:
				continue
			except usb1.USBErrorIO:
				continue
			self.m_devices.Append(n)
			if self.ftdi_active == d:
				self.m_devices.SetSelection(i)
			if self.ftdi_active == None:
				self.ftdi_active = self.ftdi_devices[0]
				self.m_devices.SetSelection(0)
				self.OnDeviceSelected(None)

	def OnClose(self, event):
		for d in self.ftdi_devices:
			d.close()
		self.Destroy()

	def ValidateModes(self):
		ready = (self.flashp.size.GetSelection() > -1) and (self.flashp.checksum.GetSelection() > -1)
		if self.flashp.mode.GetSelection() == 0:
			p = self.flashp.readfpicker.GetPath()
		else:
			p = self.flashp.writefpicker.GetPath()
		if len(p) == 0:
			ready = False
		if ready:
			self.device_state = DEVICE_STATE_READY
			self.flashp.gobutton.Enable()
		else:
			self.device_state = DEVICE_STATE_CONNECTED
			self.flashp.gobutton.Disable()
		return ready

	def OnIdle(self, event):
		if self.usbhotplug:
			self.usbcontext.handleEventsTimeout(0)
		try:
			if self.device_state == DEVICE_STATE_UNKNOWN:
				if self.ftdi_active != None:
					self.deactivateDevice()
				self.UpdateDeviceList()
			elif self.device_state == DEVICE_STATE_SETUP:
				if self.ecu != None:
					if self.ecu.init(debug=self.args.debug):
						self.device_state = DEVICE_STATE_CONNECTED
						info = self.ecu.send_command([0x72],[0x72, 0x00, 0x00, 0x05], debug=args.debug, retries=0)
						self.infop.ecmid.SetLabel("%s" % " ".join(["%02x" % b for b in info[2][3:]]))
						info = self.ecu.send_command([0x7d], [0x01, 0x01, 0x03], debug=args.debug, retries=0)
						if info!=None:
							self.infop.status.SetLabel("dirty" if info[2][2] == 0xff else "clean")
							self.infop.flashcount.SetLabel(str(int(info[2][4])))
						self.infop.Layout()
						self.statusbar.SetStatusText("ECU connected!")
					else:
						self.statusbar.SetStatusText("Cannot connect to ECU, check connections and power cycle ECU!")
				else:
					self.device_state = DEVICE_STATE_UNKNOWN
			elif self.device_state in [DEVICE_STATE_CONNECTED, DEVICE_STATE_READY]:
				info = self.ecu.send_command([0x72],[0x00, 0xf0], debug=self.args.debug, retries=0)
				if info!=None and info[2]==b"\x00":
					self.ValidateModes()
				else:
					self.device_state = DEVICE_STATE_UNKNOWN
			elif self.device_state == DEVICE_STATE_POWER_OFF:
				if not self.ecu.init(debug=self.args.debug):
					self.device_state = DEVICE_STATE_POWER_ON
					self.flashdlg.WaitOn()
			elif self.device_state == DEVICE_STATE_POWER_ON:
				if self.ecu.init(debug=self.args.debug):
					self.device_state = DEVICE_STATE_INIT
					self.init_wait = time.time()
			elif self.device_state == DEVICE_STATE_INIT and time.time() > self.init_wait+.5:
				self.initok = self.ecu.init(debug=self.args.debug)
				if self.initok:
					if self.args.debug:
						sys.stderr.write("Entering diagnostic mode\n")
					self.ecu.send_command([0x72],[0x00, 0xf0], debug=self.args.debug)
				if self.flashp.mode.GetSelection() == 0:
					self.device_state = DEVICE_STATE_READ_SECURITY
					self.flashdlg.WaitRead()
				elif self.flashp.mode.GetSelection() == 1:
					self.device_state = DEVICE_STATE_WRITE_INIT
					self.flashdlg.WaitWrite()
				elif self.flashp.mode.GetSelection() == 2:
					self.write_wait = time.time()
					self.device_state = DEVICE_STATE_RECOVER_INIT
					self.flashdlg.WaitWrite()
			elif self.device_state == DEVICE_STATE_READ_SECURITY:
				if self.args.debug:
					sys.stderr.write("Security access\n")
				self.ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f], debug=self.args.debug)
				self.ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75], debug=self.args.debug)
				self.initRead(list(binsizes.values())[self.flashp.size.GetSelection()])
				self.file = open(self.flashp.readfpicker.GetPath(), "wb")
				if self.args.debug:
					sys.stderr.write("Reading ECU\n")
				self.device_state = DEVICE_STATE_READ
			elif self.device_state == DEVICE_STATE_READ:
				if self.nbyte < self.maxbyte:
					info = self.ecu.send_command([0x82, 0x82, 0x00], [int(self.nbyte/65536)] + [b for b in struct.pack("<H", self.nbyte % 65536)] + [self.readsize], debug=self.args.debug)
					if info != None:
						self.file.write(info[2])
						self.file.flush()
						self.nbyte += self.readsize
						self.flashdlg.progress.SetValue(int(100*self.nbyte/self.maxbyte))
						self.flashdlg.msg2.SetLabel("%dB of %dB" % (self.nbyte, self.maxbyte))
						self.flashdlg.Layout()
					else:
						self.flashdlg.EndModal(-1)
						self.device_state = DEVICE_STATE_UNKNOWN
						self.statusbar.SetStatusText("")
				else:
					self.device_state = DEVICE_STATE_READY
					self.file.close()
					self.flashdlg.EndModal(1)
			elif self.device_state == DEVICE_STATE_RECOVER_INIT:
				if self.args.debug:
					sys.stdout.write("Initializing recovery process\n")
				self.ecu.do_init_recover(debug=self.args.debug)
				if self.args.debug:
					sys.stdout.write("Entering enhanced diagnostic mode\n")
				self.ecu.send_command([0x72],[0x00, 0xf1], debug=args.debug)
				self.ecu.send_command([0x27],[0x00, 0x9f, 0x00], debug=args.debug)
				self.write_wait = time.time()
				self.device_state = DEVICE_STATE_ERASE
				self.flashdlg.msg2.SetLabel("Waiting")
				self.flashdlg.progress.SetRange(12)
				self.flashdlg.progress.SetValue(12)
				self.flashdlg.Layout()
				if self.args.debug:
					sys.stderr.write("Waiting\n")
			elif self.device_state == DEVICE_STATE_WRITE_INIT:
				if self.args.debug:
					sys.stderr.write("Initializing write process\n")
				try:
					self.ecu.do_init_write(debug=self.args.debug)
					self.write_wait = time.time()
					self.device_state = DEVICE_STATE_ERASE
					self.flashdlg.msg2.SetLabel("Waiting")
					self.flashdlg.progress.SetRange(12)
					self.flashdlg.progress.SetValue(12)
					self.flashdlg.Layout()
					if self.args.debug:
						sys.stderr.write("Waiting\n")
				except MaxRetriesException:
					if self.initok:
						if self.args.debug:
							sys.stderr.write("Switching to recovery mode\n")
						self.device_state = DEVICE_STATE_RECOVER_INIT
					else:
						self.write_wait = time.time()
						self.device_state = DEVICE_STATE_ERASE
						self.flashdlg.msg2.SetLabel("Waiting")
						self.flashdlg.progress.SetRange(12)
						self.flashdlg.progress.SetValue(12)
						self.flashdlg.Layout()
						if self.args.debug:
							sys.stderr.write("Waiting\n")
			elif self.device_state == DEVICE_STATE_ERASE:
				if time.time() > self.write_wait+12:
					self.eraseinc = 0
					self.flashdlg.msg2.SetLabel("Erasing ECU")
					self.flashdlg.progress.SetRange(180)
					self.flashdlg.progress.SetValue(0)
					self.flashdlg.Layout()
					if self.args.debug:
						sys.stderr.write("Erasing ECU\n")
					self.ecu.do_erase()
					self.device_state = DEVICE_STATE_ERASE_WAIT
				else:
					self.flashdlg.progress.SetValue(int(12-round(time.time()-self.write_wait)))
			elif self.device_state == DEVICE_STATE_ERASE_WAIT:
				info = self.ecu.send_command([0x7e], [0x01, 0x05], debug=self.args.debug)
				if info[2][1] == 0x00:
					self.ecu.send_command([0x7e], [0x01, 0x01, 0x00], debug=self.args.debug)
					with open(self.flashp.writefpicker.GetPath(), "rb") as fbin:
						self.byts, fcksum, ccksum, fixed = validate_checksum(bytearray(fbin.read(os.path.getsize(self.flashp.writefpicker.GetPath()))), int(checksums[self.flashp.checksum.GetSelection()], 16), self.flashp.fixchecksum.IsChecked())
					self.initWrite(list(binsizes.values())[self.flashp.size.GetSelection()])
					if self.args.debug:
						sys.stderr.write("Writing ECU\n")
					self.device_state = DEVICE_STATE_WRITE
					self.flashdlg.progress.SetRange(100)
					self.flashdlg.progress.SetValue(0)
					self.flashdlg.msg2.SetLabel("")
					self.flashdlg.Layout()
				else:
					self.eraseinc += 1
					if self.eraseinc > 180:
						self.eraseinc = 180
					self.flashdlg.progress.SetValue(self.eraseinc)
			elif self.device_state == DEVICE_STATE_WRITE:
				if self.i < self.maxi:
					bytstart = [s for s in struct.pack(">H",(8*self.i))]
					if self.i+1 == self.maxi:
						bytend = [s for s in struct.pack(">H",0)]
					else:
						bytend = [s for s in struct.pack(">H",(8*(self.i+1)))]
					d = list(self.byts[((self.i+0)*128):((self.i+1)*128)])
					x = bytstart + d + bytend
					c1 = checksum8bit(x)
					c2 = checksum8bitHonda(x)
					x = [0x01, 0x06] + x + [c1, c2]
					info = self.ecu.send_command([0x7e], x, debug=self.args.debug)
					if ord(info[1]) != 5:
						self.device_state = DEVICE_STATE_ERROR
					self.i += 1
					if self.i % 2 == 0:
						self.ecu.send_command([0x7e], [0x01, 0x08], debug=self.args.debug)
					self.flashdlg.progress.SetValue(int(100*self.i/self.maxi))
					self.flashdlg.msg2.SetLabel("%dB of %dB" % (self.i*128, list(binsizes.values())[self.flashp.size.GetSelection()]*1024))
					self.flashdlg.Layout()
				else:
					self.device_state = DEVICE_STATE_WRITE_FINALIZE
			elif self.device_state == DEVICE_STATE_WRITE_FINALIZE:
				if self.args.debug:
					sys.stderr.write("Finalizing write process\n")
				self.ecu.do_post_write(debug=self.args.debug)
				self.device_state = DEVICE_STATE_READY
				self.flashdlg.EndModal(1)
		except pylibftdi._base.FtdiError:
			self.device_state = DEVICE_STATE_UNKNOWN
			self.statusbar.SetStatusText("")
		except usb1.USBErrorPipe:
			self.device_state = DEVICE_STATE_UNKNOWN
			self.statusbar.SetStatusText("")
		event.RequestMore()
		#print(self.device_state)

if __name__ == '__main__':

	default_checksum = '0x3fff8'
	default_romsize = 256

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	subparsers = parser.add_subparsers(metavar='mode',dest='mode')

	parser_read = subparsers.add_parser('read', help='read ecu to binfile')
	parser_read.add_argument('binfile', help="name of output binfile")
	parser_read.add_argument('--checksum', default=default_checksum, type=Hex(), help="hex location of checksum in binfile")
	parser_read.add_argument('--rom-size', default=default_romsize, type=int, help="size of ecu rom in kilobytes")

	parser_write = subparsers.add_parser('write', help='write ecu from binfile')
	parser_write.add_argument('binfile', help="name of input binfile")
	parser_write.add_argument('--checksum', default=default_checksum, type=Hex(), help="hex location of checksum in binfile")
	parser_write.add_argument('--rom-size', default=default_romsize, type=int, help="size of ecu rom in kilobytes")
	parser_write.add_argument('--fix-checksum', action='store_true', help="fix checksum before write")
	parser_write.add_argument('--force', action='store_true', help="force write (old-school recovery)")

	parser_recover = subparsers.add_parser('recover', help='recover ecu from binfile')
	parser_recover.add_argument('binfile', help="name of input binfile")
	parser_recover.add_argument('--checksum', default=default_checksum, type=Hex(), help="hex location of checksum in binfile")
	parser_recover.add_argument('--rom-size', default=default_romsize, type=int, help="size of ecu rom in kilobytes")
	parser_recover.add_argument('--fix-checksum', action='store_true', help="fix checksum before recover")

	parser_checksum = subparsers.add_parser('checksum', help='validate binfile checksum')
	parser_checksum.add_argument('binfile', help="name of input binfile")
	parser_checksum.add_argument('--checksum', default=default_checksum, type=Hex(), help="hex location of checksum in binfile")
	parser_checksum.add_argument('--fix-checksum', action='store_true', help="fix checksum in binfile")

	parser_scan = subparsers.add_parser('scan', help='scan engine data')

	parser_faults = subparsers.add_parser('faults', help='read fault codes')
	parser_faults.add_argument('--clear', action='store_true', help="clear fault codes")

	parser_log = subparsers.add_parser('log', help='log engine data')

	#subparsers.required = True

	db_grp = parser.add_argument_group('debugging options')
	db_grp.add_argument('--debug', action='store_true', help="turn on debugging output")
	args = parser.parse_args()

	if args.mode == None:

		usbcontext = usb1.USBContext()
		app = wx.App(redirect=False)
		gui = HondaECU_GUI(args, usbcontext)
		gui.Show()
		app.MainLoop()

	else:

		offset = 0
		binfile = None
		ret = 1
		if not args.mode in ["faults", "scan", "log", "read"]:
			if os.path.isabs(args.binfile):
				binfile = args.binfile
			else:
				binfile = os.path.abspath(os.path.expanduser(args.binfile))

			byts, fcksum, ccksum, fixed = do_validation(binfile, args.checksum, args.fix_checksum)
			if (fcksum == ccksum or fixed) and args.mode in ["recover","write"]:
				ret = 0
			else:
				ret = -1
		else:
			ret = 0

		if ret == 0:

			try:
				ecu = HondaECU()
			except FtdiError:
				sys.stderr.write("No flash adapters detected!\n")
				sys.exit(-2)

			initok = False
			if ecu.init(debug=args.debug):
				if args.mode not in ["scan","log","faults"]:
					print_header()
					sys.stdout.write("Turn off bike\n")
					while ecu.init(debug=args.debug):
						time.sleep(.1)
				else:
					initok = True
			if not initok:
				sys.stdout.write("Turn on bike\n")
				while not ecu.init(debug=args.debug):
					time.sleep(.1)
				time.sleep(.5)
				initok = True

			if initok:
				print_header()
				sys.stdout.write("ECU connected\n")
				print_header()
				sys.stdout.write("Entering diagnostic mode\n")
				ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)
				info = ecu.send_command([0x72],[0x72, 0x00, 0x00, 0x05], debug=args.debug)
				sys.stdout.write("  ECM ID: %s\n" % " ".join(["%02x" % b for b in info[2][3:]]))

				if args.mode == "scan":
					print_header()
					sys.stdout.write("HDS Tables\n")
					for j in range(256):
						info = ecu.send_command([0x72], [0x71, j], debug=args.debug)
						if info and len(info[2][2:]) > 0:
							sys.stdout.write(" %s\t%s\n" % (hex(j), repr([b for b in info[2][2:]])))

				elif args.mode == "faults":
					if args.clear:
						print_header()
						sys.stdout.write("Clearing fault codes\n")
						while True:
							info = ecu.send_command([0x72],[0x60, 0x03], debug=args.debug)[2]
							if info[1] == 0x00:
								break
					print_header()
					sys.stdout.write("Fault codes\n")
					faults = {'past':[], 'current':[]}
					for i in range(1,0x0c):
						info_current = ecu.send_command([0x72],[0x74, i], debug=args.debug)[2]
						for j in [3,5,7]:
							if info_current[j] != 0:
								faults['current'].append("%02d-%02d" % (info_current[j],info_current[j+1]))
						if info_current[2] == 0:
							break
					for i in range(1,0x0c):
						info_past = ecu.send_command([0x72],[0x73, i], debug=args.debug)[2]
						for j in [3,5,7]:
							if info_past[j] != 0:
								faults['past'].append("%02d-%02d" % (info_past[j],info_past[j+1]))
						if info_past[2] == 0:
							break
					if len(faults['current']) > 0:
						sys.stdout.write("  Current:\n")
						for code in faults['current']:
							sys.stdout.write("    %s: %s\n" % (code, DTC[code]))
					if len(faults['past']) > 0:
						sys.stdout.write("  Past:\n")
						for code in faults['past']:
							sys.stdout.write("    %s: %s\n" % (code, DTC[code]))

				elif args.mode == "read":
					print_header()
					sys.stdout.write("Security access\n")
					ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f], debug=args.debug)
					ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75], debug=args.debug)

					print_header()
					sys.stdout.write("Reading ECU\n")
					do_read_flash(ecu, binfile, args.rom_size, debug=args.debug)
					do_validation(binfile, args.checksum)

				elif args.mode == "write":
					print_header()
					sys.stdout.write("Initializing write process\n")
					ecu.do_init_write(debug=args.debug)

				elif args.mode == "recover":
					print_header()
					sys.stdout.write("Initializing recovery process\n")
					ecu.do_init_recover(debug=args.debug)

					print_header()
					sys.stdout.write("Entering enhanced diagnostic mode\n")
					ecu.send_command([0x72],[0x00, 0xf1], debug=args.debug)
					ecu.send_command([0x27],[0x00, 0x9f, 0x00], debug=args.debug)

			if args.mode in ["write", "recover"] and (initok or args.force):

				print_header()
				sys.stdout.write("Erasing ECU\n")
				time.sleep(14)
				ecu.do_erase(debug=args.debug)
				ecu.do_erase_wait(debug=args.debug)

				print_header()
				sys.stdout.write("Writing ECU\n")
				do_write_flash(ecu, byts, offset=0, debug=args.debug)

				print_header()
				sys.stdout.write("Finalizing write process\n")
				ecu.do_post_write(debug=args.debug)

		print_header()
		sys.exit(ret)
