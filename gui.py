import os
import sys
import usb1
import pylibftdi
import wx
import wx.adv
import platform
import time
import struct

from ecu import HondaECU, MaxRetriesException, validate_checksum, checksum8bit, checksum8bitHonda

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

class FlashDialog(wx.Dialog):

	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, size=(280,230))
		self.parent = parent
		mainbox = wx.BoxSizer(wx.VERTICAL)
		self.msgoff = wx.StaticText(self, wx.ID_ANY, "Turn off ECU", style=wx.ALIGN_CENTRE)
		self.msgon = wx.StaticText(self, wx.ID_ANY, "Turn on ECU", style=wx.ALIGN_CENTRE)
		self.msgread = wx.StaticText(self, wx.ID_ANY, "Reading ECU", style=wx.ALIGN_CENTRE)
		self.msgwrite = wx.StaticText(self, wx.ID_ANY, "Writing ECU", style=wx.ALIGN_CENTRE)
		self.offactivity = wx.adv.AnimationCtrl(self, wx.ID_ANY)
		self.onactivity = wx.adv.AnimationCtrl(self, wx.ID_ANY)
		self.offactivity.LoadFile(self.parent.waitoffgif)
		self.onactivity.LoadFile(self.parent.waitongif)
		self.progress = wx.Gauge(self, wx.ID_ANY)
		self.progress.SetRange(100)
		self.progress.SetValue(0)
		mainbox.Add(self.msgoff, 0, wx.ALIGN_CENTER|wx.TOP, 40)
		mainbox.Add(self.msgon, 0, wx.ALIGN_CENTER|wx.TOP, 40)
		mainbox.Add(self.msgread, 0, wx.ALIGN_CENTER|wx.TOP, 40)
		mainbox.Add(self.msgwrite, 0, wx.ALIGN_CENTER|wx.TOP, 40)
		mainbox.Add(self.offactivity, 0, wx.ALIGN_CENTER, 0)
		mainbox.Add(self.onactivity, 0, wx.ALIGN_CENTER, 0)
		mainbox.Add(self.progress, 0, wx.EXPAND|wx.ALIGN_CENTER|wx.ALL, 40)
		self.msgon.Show(False)
		self.msgread.Show(False)
		self.msgwrite.Show(False)
		self.offactivity.Show(False)
		self.SetSizer(mainbox)
		self.Layout()
		self.Center()

	def WaitOff(self):
		self.msgon.Show(False)
		self.msgoff.Show(True)
		self.msgread.Show(False)
		self.msgwrite.Show(False)
		self.progress.Show(False)
		self.onactivity.Show(False)
		self.offactivity.Show(True)
		self.onactivity.Stop()
		self.offactivity.Play()
		self.Layout()

	def WaitOn(self):
		self.msgon.Show(True)
		self.msgoff.Show(False)
		self.msgread.Show(False)
		self.msgwrite.Show(False)
		self.progress.Show(False)
		self.onactivity.Show(True)
		self.offactivity.Show(False)
		self.onactivity.Play()
		self.offactivity.Stop()
		self.Layout()

	def WaitRead(self):
		self.msgon.Show(False)
		self.msgoff.Show(False)
		self.msgread.Show(True)
		self.msgwrite.Show(False)
		self.progress.Show(True)
		self.onactivity.Show(False)
		self.offactivity.Show(False)
		self.onactivity.Stop()
		self.offactivity.Stop()
		self.Layout()

	def WaitWrite(self):
		self.msgon.Show(False)
		self.msgoff.Show(False)
		self.msgread.Show(False)
		self.msgwrite.Show(True)
		self.progress.Show(True)
		self.onactivity.Show(False)
		self.offactivity.Show(False)
		self.onactivity.Stop()
		self.offactivity.Stop()
		self.Layout()

class HondaECU_GUI(wx.Frame):

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

	def PollUSBDevices(self, event):
		new_devices = self.usbcontext.getDeviceList(skip_on_error=True)
		for device in new_devices:
			if device.getVendorID() == pylibftdi.driver.FTDI_VENDOR_ID:
				if device.getProductID() in pylibftdi.driver.USB_PID_LIST:
					if not device in self.ftdi_devices:
						print("Adding device (%s) to list" % device)
						self.ftdi_devices.append(device)
						self.UpdateDeviceList()
		for device in self.ftdi_devices:
			if not device in new_devices:
				if device == self.ftdi_active:
					self.ecu.dev.close()
					del self.ecu
					self.ecu = None
					print("Deactivating device (%s)" % self.ftdi_active)
					self.ftdi_active = None
				self.ftdi_devices.remove(device)
				self.UpdateDeviceList()
				print("Removing device (%s) from list" % device)

	def hotplug_callback(self, context, device, event):
		if device.getProductID() in pylibftdi.driver.USB_PID_LIST:
			if event == usb1.HOTPLUG_EVENT_DEVICE_ARRIVED:
				if not device in self.ftdi_devices:
					print("Adding device (%s) to list" % device)
					self.ftdi_devices.append(device)
					self.UpdateDeviceList()
			elif event == usb1.HOTPLUG_EVENT_DEVICE_LEFT:
				if device in self.ftdi_devices:
					if device == self.ftdi_active:
						self.ecu.dev.close()
						del self.ecu
						self.ecu = None
						print("Deactivating device (%s)" % self.ftdi_active)
						self.ftdi_active = None
					self.ftdi_devices.remove(device)
					self.UpdateDeviceList()
					print("Removing device (%s) from list" % device)

	def initRead(self, rom_size):
		self.maxbyte = 1024 * rom_size
		self.nbyte = 0
		self.readsize = 8

	def initWrite(self, rom_size):
		self.i = 0
		self.maxi = len(self.byts)/128
		self.writesize = 128

	def __init__(self, usbcontext):
		self.init_wait = -1
		self.write_wait = -1
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
		self.waitoffgif = os.path.join(self.basepath, "waitoff.gif")
		self.waitongif = os.path.join(self.basepath, "waiton.gif")

		ib = wx.IconBundle()
		ib.AddIcon(ip)
		self.SetIcons(ib)

		menuBar = wx.MenuBar()
		menu = wx.Menu()
		m_exit = menu.Append(wx.ID_EXIT, "E&xit\tAlt-X", "Close window and exit program.")
		self.Bind(wx.EVT_MENU, self.OnClose, m_exit)
		menuBar.Append(menu, "&File")
		self.SetMenuBar(menuBar)

		panel = wx.Panel(self)
		mainbox = wx.BoxSizer(wx.VERTICAL)
		devicebox = wx.StaticBoxSizer(wx.HORIZONTAL, panel, "FTDI Devices")

		self.m_devices = wx.Choice(panel, wx.ID_ANY)
		devicebox.Add(self.m_devices, 1, wx.EXPAND | wx.ALL, 5)

		self.notebook = wx.Notebook(panel, wx.ID_ANY)

		flashp = wx.Panel(self.notebook)
		self.flashpsizer = wx.GridBagSizer(0,0)
		self.mode = wx.RadioBox(flashp, wx.ID_ANY, "Mode", choices=["Read","Write","Recover"])
		self.flashpsizer.Add(self.mode, pos=(0,0), span=(1,6), flag=wx.ALL|wx.ALIGN_CENTER, border=20)
		wfilel = wx.StaticText(flashp, wx.ID_ANY, "File")
		self.readfpicker = wx.FilePickerCtrl(flashp, wx.ID_ANY, wildcard="ECU dump (*.bin)|*.bin", style=wx.FLP_SAVE|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)
		self.writefpicker = wx.FilePickerCtrl(flashp, wx.ID_ANY, wildcard="ECU dump (*.bin)|*.bin", style=wx.FLP_OPEN|wx.FLP_FILE_MUST_EXIST|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)
		self.writefpicker.Show(False)
		self.flashpsizer.Add(wfilel, pos=(1,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.fpickerbox = wx.BoxSizer(wx.HORIZONTAL)
		self.fpickerbox.Add(self.readfpicker, 1)
		self.fpickerbox.Add(self.writefpicker, 1)
		self.flashpsizer.Add(self.fpickerbox, pos=(1,1), span=(1,5), flag=wx.EXPAND|wx.RIGHT, border=10)
		wsizel = wx.StaticText(flashp, wx.ID_ANY, "Size")
		self.size = wx.Choice(flashp, wx.ID_ANY, choices=list(self.binsizes.keys()))
		self.flashpsizer.Add(wsizel, pos=(2,0), flag=wx.TOP|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
		self.flashpsizer.Add(self.size, pos=(2,1), span=(1,1), flag=wx.TOP, border=5)
		wchecksuml = wx.StaticText(flashp, wx.ID_ANY, "Checksum")
		self.checksum = wx.Choice(flashp, wx.ID_ANY, choices=list(self.checksums))
		self.fixchecksum = wx.CheckBox(flashp, wx.ID_ANY, "Fix")
		self.fixchecksum.Show(False)
		self.flashpsizer.Add(wchecksuml, pos=(2,3), flag=wx.TOP|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
		self.flashpsizer.Add(self.checksum, pos=(2,4), flag=wx.TOP, border=5)
		self.flashpsizer.Add(self.fixchecksum, pos=(2,5), flag=wx.TOP|wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
		self.gobutton = wx.Button(flashp, wx.ID_ANY, "Start")
		#self.gobutton.Disable()
		self.flashpsizer.Add(self.gobutton, pos=(4,5), flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.BOTTOM|wx.RIGHT, border=10)
		self.flashpsizer.AddGrowableRow(3,1)
		self.flashpsizer.AddGrowableCol(5,1)
		flashp.SetSizer(self.flashpsizer)
		self.notebook.AddPage(flashp, "Flash Operations")

		datap = wx.Panel(self.notebook)
		self.notebook.AddPage(datap, "Diagnostic Tables")

		errorp = wx.Panel(self.notebook)
		self.notebook.AddPage(errorp, "Error Codes")

		mainbox.Add(devicebox, 0, wx.EXPAND | wx.ALL, 10)
		mainbox.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 10)

		panel.SetSizer(mainbox)
		panel.Layout()
		self.Centre()

		self.Bind(wx.EVT_IDLE, self.OnIdle)
		self.m_devices.Bind(wx.EVT_CHOICE, self.OnDeviceSelected)
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.mode.Bind(wx.EVT_RADIOBOX, self.OnModeChange)
		self.gobutton.Bind(wx.EVT_BUTTON, self.OnGo)

		self.flashdlg = FlashDialog(self)

		if self.usbhotplug:
			print('Registering hotplug callback...')
			self.usbcontext.hotplugRegisterCallback(self.hotplug_callback, vendor_id=pylibftdi.driver.FTDI_VENDOR_ID)
			print('Callback registered. Monitoring events.')
		else:
			self.usbpolltimer = wx.Timer(self, wx.ID_ANY)
			self.Bind(wx.EVT_TIMER, self.PollUSBDevices)
			self.usbpolltimer.Start(250)

	def OnGo(self, event):
		if self.ecu.kline():
			self.device_state = DEVICE_STATE_POWER_OFF
			self.flashdlg.WaitOff()
		else:
			self.device_state = DEVICE_STATE_POWER_ON
			self.flashdlg.WaitOn()
		if self.flashdlg.ShowModal() == 1:
			print('All good')
		else:
			print('Abort')

	def OnModeChange(self, event):
		if self.mode.GetSelection() == 0:
			self.writefpicker.Show(False)
			self.readfpicker.Show(True)
			self.fixchecksum.Show(False)
		else:
			self.readfpicker.Show(False)
			self.writefpicker.Show(True)
			self.fixchecksum.Show(True)
		self.fpickerbox.Layout()
		self.flashpsizer.Layout()

	def OnDeviceSelected(self, event):
		self.statusbar.SetStatusText("")
		newdevice = self.ftdi_devices[self.m_devices.GetSelection()]
		if self.ftdi_active != None:
			if self.ftdi_active != newdevice:
				print("Deactivating device (%s)" % self.ftdi_active)
				if self.ecu != None:
					self.ecu.dev.close()
					del self.ecu
					self.ecu = None
		self.ftdi_active = newdevice
		print("Activating device (%s)" % self.ftdi_active)
		try:
			self.device_state = DEVICE_STATE_UNKNOWN
			self.ecu = HondaECU(device_id=self.ftdi_active.getSerialNumber())
			self.device_state = DEVICE_STATE_SETUP
		except usb1.USBErrorNotSupported as e:
			self.ecu = None
			self.statusbar.SetStatusText("Incorrect driver for device, install libusbK with Zadig!")

	def UpdateDeviceList(self):
		self.m_devices.Clear()
		for i,d in enumerate(self.ftdi_devices):
			n = str(d)
			try:
				n += " | " + d.getSerialNumber()
			except usb1.USBErrorNotSupported:
				pass
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
		ready = (self.size.GetSelection() > -1) and (self.checksum.GetSelection() > -1)
		if self.mode.GetSelection() == 0:
			p = self.readfpicker.GetPath()
		else:
			p = self.writefpicker.GetPath()
		if len(p) == 0:
			ready = False
		# if ready:
		# 	self.device_state = DEVICE_STATE_READY
		# 	self.gobutton.Enable()
		# else:
		# 	self.device_state = DEVICE_STATE_CONNECTED
		# 	self.gobutton.Disable()
		return ready

	def OnIdle(self, event):
		if self.usbhotplug:
			self.usbcontext.handleEventsTimeout(0)
		if self.device_state == DEVICE_STATE_SETUP:
			if self.ecu != None:
				if self.ecu.loopTest() and self.ecu.kline():
					self.ecu.setup()
					# if self.ecu.init(debug=True):
					self.device_state = DEVICE_STATE_CONNECTED
					# 	self.statusbar.SetStatusText("ECU connected!")
			else:
				self.device_state = DEVICE_STATE_UNKNOWN
		elif self.device_state in [DEVICE_STATE_CONNECTED, DEVICE_STATE_READY]:
			self.ValidateModes()
		elif self.device_state == DEVICE_STATE_POWER_OFF:
			if not self.ecu.kline():
				self.device_state = DEVICE_STATE_POWER_ON
				self.flashdlg.WaitOn()
		elif self.device_state == DEVICE_STATE_POWER_ON:
			if self.ecu.kline():
				self.device_state = DEVICE_STATE_INIT
				self.init_wait = time.time()
		elif self.device_state == DEVICE_STATE_INIT and time.time() > self.init_wait+.5:
			try:
				self.initok = self.ecu.init(debug=True)
			except MaxRetriesException:
				self.initok = False
			if self.initok:
				print("Entering diagnostic mode")
				self.ecu.send_command([0x72],[0x00, 0xf0], debug=True)
			if self.mode.GetSelection() == 0:
				self.device_state = DEVICE_STATE_READ_SECURITY
				self.flashdlg.WaitRead()
			elif self.mode.GetSelection() == 1:
				self.device_state = DEVICE_STATE_WRITE_INIT
				self.flashdlg.WaitWrite()
			elif self.mode.GetSelection() == 2:
				self.write_wait = time.time()
				self.device_state = DEVICE_STATE_ERASE
				print("Erasing ECU")
				self.flashdlg.WaitWrite()
		elif self.device_state == DEVICE_STATE_READ_SECURITY:
			print("Security access")
			self.ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f], debug=True)
			self.ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75], debug=True)
			self.initRead(list(self.binsizes.values())[self.size.GetSelection()])
			self.file = open(self.readfpicker.GetPath(), "wb")
			print("Reading ECU")
			self.device_state = DEVICE_STATE_READ
		elif self.device_state == DEVICE_STATE_READ:
			if self.nbyte < self.maxbyte:
				info = self.ecu.send_command([0x82, 0x82, 0x00], [int(self.nbyte/65536)] + [b for b in struct.pack("<H", self.nbyte % 65536)] + [self.readsize], debug=True)
				self.file.write(info[2])
				self.file.flush()
				self.nbyte += self.readsize
				self.flashdlg.progress.SetValue(int(100*self.nbyte/self.maxbyte))
			else:
				self.device_state = DEVICE_STATE_READY
				self.file.close()
				self.flashdlg.EndModal(1)
		elif self.device_state == DEVICE_STATE_RECOVER_INIT:
			self.ecu.do_init_recover(debug=True)
			self.write_wait = time.time()
			self.device_state = DEVICE_STATE_ERASE
			print("Erasing ECU")
		elif self.device_state == DEVICE_STATE_WRITE_INIT:
			print("Initializing write process")
			try:
				self.ecu.do_init_write(debug=True)
				self.write_wait = time.time()
				self.device_state = DEVICE_STATE_ERASE
				print("Erasing ECU")
			except MaxRetriesException:
				if self.initok:
					print("Switching to recovery mode")
					self.device_state = DEVICE_STATE_RECOVER_INIT
				else:
					self.write_wait = time.time()
					self.device_state = DEVICE_STATE_ERASE
					print("Erasing ECU")
		elif self.device_state == DEVICE_STATE_ERASE and time.time() > self.write_wait+12:
			self.ecu.do_erase()
			self.device_state = DEVICE_STATE_ERASE_WAIT
		elif self.device_state == DEVICE_STATE_ERASE_WAIT:
			info = self.ecu.send_command([0x7e], [0x01, 0x05], debug=True)
			if info[2][1] == 0x00:
				self.ecu.send_command([0x7e], [0x01, 0x01, 0x00], debug=True)
				with open(self.writefpicker.GetPath(), "rb") as fbin:
					self.byts, fcksum, ccksum, fixed = validate_checksum(bytearray(fbin.read(os.path.getsize(self.writefpicker.GetPath()))), int(self.checksums[self.checksum.GetSelection()], 16), self.fixchecksum.IsChecked())
				self.initWrite(list(self.binsizes.values())[self.size.GetSelection()])
				print("Writing ECU")
				self.device_state = DEVICE_STATE_WRITE
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
				info = self.ecu.send_command([0x7e], x, debug=True)
				if ord(info[1]) != 5:
					self.device_state = DEVICE_STATE_ERROR
				self.i += 1
				if self.i % 2 == 0:
					self.ecu.send_command([0x7e], [0x01, 0x08], debug=True)
				self.flashdlg.progress.SetValue(int(100*self.i/self.maxi))
			else:
				self.device_state = DEVICE_STATE_WRITE_FINALIZE
		elif self.device_state == DEVICE_STATE_WRITE_FINALIZE:
			print("Finalizing write process")
			self.ecu.do_post_write(debug=True)
			self.device_state = DEVICE_STATE_READY
			self.flashdlg.EndModal(1)
		event.RequestMore()
		#print(self.device_state)

if __name__ == '__main__':

	usbcontext = usb1.USBContext()
	app = wx.App(redirect=False)
	gui = HondaECU_GUI(usbcontext)
	gui.Show()
	app.MainLoop()
