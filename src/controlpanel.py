import sys
import os
import platform

import json
import time

from pydispatch import dispatcher

import wx
import wx.lib.buttons as buttons
import wx.lib.agw.labelbook as LB

import EnhancedStatusBar as ESB

from frames.info import HondaECU_InfoPanel
from frames.data import HondaECU_DatalogPanel
from frames.error import HondaECU_ErrorPanel
from frames.flash import HondaECU_FlashPanel
from frames.hrcsettings import HondaECU_HRCDataSettingsPanel

import usb.util

from threads.kline import KlineWorker
from threads.usb import USBMonitor

import tarfile

from ecmids import ECM_IDs

from eculib.honda import ECUSTATE, checksum8bitHonda

class HondaECU_AppButton(buttons.ThemedGenBitmapTextButton):

	def __init__(self, appid, enablestates, *args, **kwargs):
		self.appid = appid
		self.enablestates = enablestates
		buttons.ThemedGenBitmapTextButton.__init__(self, *args,**kwargs)
		self.SetInitialSize((128,64))

	def DrawLabel(self, dc, width, height, dx=0, dy=0):
		bmp = self.bmpLabel
		if bmp is not None:
			if self.bmpDisabled and not self.IsEnabled():
				bmp = self.bmpDisabled
			if self.bmpFocus and self.hasFocus:
				bmp = self.bmpFocus
			if self.bmpSelected and not self.up:
				bmp = self.bmpSelected
			bw,bh = bmp.GetWidth(), bmp.GetHeight()
			if not self.up:
				dx = dy = self.labelDelta
			hasMask = bmp.GetMask() is not None
		else:
			bw = bh = 0
			hasMask = False

		dc.SetFont(self.GetFont())
		if self.IsEnabled():
			dc.SetTextForeground(self.GetForegroundColour())
		else:
			dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

		label = self.GetLabel()
		tw, th = dc.GetTextExtent(label)
		if not self.up:
			dx = dy = self.labelDelta

		if bmp is not None:
			dc.DrawBitmap(bmp, (width-bw)/2, (height-bh-th-4)/2, hasMask)
		dc.DrawText(label, (width-tw)/2, (height+bh-th+4)/2)

class HondaECU_LogPanel(wx.Frame):

	def __init__(self, parent):
		self.auto = True
		wx.Frame.__init__(self, parent, title="HondaECU :: Debug Log", size=(640,480))
		self.SetMinSize((640,480))

		self.menubar = wx.MenuBar()
		self.SetMenuBar(self.menubar)
		fileMenu = wx.Menu()
		self.menubar.Append(fileMenu, '&File')
		saveItem = wx.MenuItem(fileMenu, wx.ID_SAVEAS, '&Save As\tCtrl+S')
		self.Bind(wx.EVT_MENU, self.OnSave, saveItem)
		fileMenu.Append(saveItem)
		fileMenu.AppendSeparator()
		quitItem = wx.MenuItem(fileMenu, wx.ID_EXIT, '&Quit\tCtrl+Q')
		self.Bind(wx.EVT_MENU, self.OnClose, quitItem)
		fileMenu.Append(quitItem)
		viewMenu = wx.Menu()
		self.menubar.Append(viewMenu, '&View')
		self.autoscrollItem = viewMenu.AppendCheckItem(wx.ID_ANY, 'Auto scroll log')
		self.autoscrollItem.Check()
		self.logText = wx.TextCtrl(self, style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.logText, 1, wx.EXPAND|wx.ALL, 5)
		self.SetSizer(sizer)
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.Layout()
		# sizer.Fit(self)
		self.Center()
		self.starttime = time.time()
		wx.CallAfter(dispatcher.connect, self.ECUDebugHandler, signal="ecu.debug", sender=dispatcher.Any)

	def OnSave(self, event):
		with wx.FileDialog(self, "Save debug log", wildcard="Debug log files (*.txt)|*.txt", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
			if fileDialog.ShowModal() == wx.ID_CANCEL:
				return
			pathname = fileDialog.GetPath()
			try:
				with open(pathname, 'w') as file:
					file.write(self.logText.GetValue())
			except IOError:
				print("Cannot save current data in file '%s'." % pathname)

	def OnClose(self, event):
		self.Hide()

	def ECUDebugHandler(self, msg):
		msg = "[%.4f] %s\n" % (time.time()-self.starttime, msg)
		if self.autoscrollItem.IsChecked():
			wx.CallAfter(self.logText.AppendText, msg)
		else:
			wx.CallAfter(self.logText.WriteText, msg)

class HondaECU_ControlPanel(wx.Frame):

	def __init__(self, version_full, nobins=False, restrictions=None, force_restrictions=False):
		self.nobins = nobins
		self.restrictions = restrictions
		self.force_restrictions = force_restrictions
		self.run = True
		self.active_ftdi_device = None
		self.ftdi_devices = {}
		self.__clear_data()

		if getattr(sys, 'frozen', False):
			self.basepath = sys._MEIPASS
		else:
			self.basepath = os.path.dirname(os.path.realpath(__file__))

		self.version_full = version_full
		self.version_short = self.version_full.split("-")[0]

		self.apps = {
			"info": {
				"label":"ECU Info",
				"icon":"images/info2.png",
				"conflicts":["flash","hrc"],
				"panel":HondaECU_InfoPanel,
			},
			"flash": {
				"label":"Flash",
				"icon":"images/chip2.png",
				"conflicts":["data","hrc"],
				"panel":HondaECU_FlashPanel,
				# "disabled":True,
				"enable": [ECUSTATE.OK, ECUSTATE.RECOVER_OLD, ECUSTATE.RECOVER_NEW, ECUSTATE.WRITEx00, ECUSTATE.WRITEx30, ECUSTATE.READ],
			},
			"data": {
				"label":"Data Logging",
				"icon":"images/monitor.png",
				"conflicts":["flash","hrc"],
				"panel":HondaECU_DatalogPanel,
				# "disabled":True,
				"enable": [ECUSTATE.OK],
			},
			"dtc": {
				"label":"Trouble Codes",
				"icon":"images/warning.png",
				"conflicts":["flash","hrc"],
				"panel":HondaECU_ErrorPanel,
				# "disabled":True,
				"enable": [ECUSTATE.OK],
			},
		}
		self.appanels = {}

		wx.Frame.__init__(self, None, title="HondaECU %s" % (self.version_short), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER, size=(500,300))

		ib = wx.IconBundle()
		ib.AddIcon(os.path.join(self.basepath,"images","honda.ico"))
		self.SetIcons(ib)

		self.menubar = wx.MenuBar()
		self.SetMenuBar(self.menubar)
		fileMenu = wx.Menu()
		self.menubar.Append(fileMenu, '&File')
		quitItem = wx.MenuItem(fileMenu, wx.ID_EXIT, '&Quit\tCtrl+Q')
		self.Bind(wx.EVT_MENU, self.OnClose, quitItem)
		fileMenu.Append(quitItem)
		helpMenu = wx.Menu()
		self.menubar.Append(helpMenu, '&Help')
		debugItem = wx.MenuItem(helpMenu, wx.ID_ANY, 'Show debug log')
		self.Bind(wx.EVT_MENU, self.OnDebug, debugItem)
		helpMenu.Append(debugItem)
		helpMenu.AppendSeparator()
		detectmapItem = wx.MenuItem(helpMenu, wx.ID_ANY, 'Detect map id')
		self.Bind(wx.EVT_MENU, self.OnDetectMap, detectmapItem)
		helpMenu.Append(detectmapItem)
		checksumItem = wx.MenuItem(helpMenu, wx.ID_ANY, 'Validate bin checksum')
		self.Bind(wx.EVT_MENU, self.OnBinChecksum, checksumItem)
		helpMenu.Append(checksumItem)

		self.statusicons = [
			wx.Image(os.path.join(self.basepath, "images/bullet_black.png"), wx.BITMAP_TYPE_ANY).ConvertToBitmap(),
			wx.Image(os.path.join(self.basepath, "images/bullet_yellow.png"), wx.BITMAP_TYPE_ANY).ConvertToBitmap(),
			wx.Image(os.path.join(self.basepath, "images/bullet_green.png"), wx.BITMAP_TYPE_ANY).ConvertToBitmap(),
			wx.Image(os.path.join(self.basepath, "images/bullet_blue.png"), wx.BITMAP_TYPE_ANY).ConvertToBitmap(),
			wx.Image(os.path.join(self.basepath, "images/bullet_purple.png"), wx.BITMAP_TYPE_ANY).ConvertToBitmap(),
			wx.Image(os.path.join(self.basepath, "images/bullet_red.png"), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		]
		self.statusbar = ESB.EnhancedStatusBar(self, -1)
		self.SetStatusBar(self.statusbar)
		self.statusbar.SetSize((-1, 28))
		self.statusicon = wx.StaticBitmap(self.statusbar)
		self.statusicon.SetBitmap(self.statusicons[0])
		self.ecmidl = wx.StaticText(self.statusbar)
		self.flashcountl = wx.StaticText(self.statusbar)
		self.dtccountl = wx.StaticText(self.statusbar)
		self.statusbar.SetFieldsCount(4)
		self.statusbar.SetStatusWidths([32, 170, 130, 110])
		self.statusbar.AddWidget(self.statusicon, pos=0)
		self.statusbar.AddWidget(self.ecmidl, pos=1, horizontalalignment=ESB.ESB_ALIGN_LEFT)
		self.statusbar.AddWidget(self.flashcountl, pos=2, horizontalalignment=ESB.ESB_ALIGN_LEFT)
		self.statusbar.AddWidget(self.dtccountl, pos=3, horizontalalignment=ESB.ESB_ALIGN_LEFT)
		self.statusbar.SetStatusStyles([wx.SB_SUNKEN,wx.SB_SUNKEN,wx.SB_SUNKEN,wx.SB_SUNKEN])

		self.outerp = wx.Panel(self)

		self.adapterboxp = wx.Panel(self.outerp)
		self.adapterboxsizer = wx.StaticBoxSizer(wx.VERTICAL, self.adapterboxp, "FTDI Devices:")
		self.adapterboxp.SetSizer(self.adapterboxsizer)
		self.adapterlist = wx.Choice(self.adapterboxp, wx.ID_ANY, size=(-1,32))
		self.adapterboxsizer.Add(self.adapterlist, 1, wx.ALL|wx.EXPAND, border=10)

		self.labelbook = LB.LabelBook(self.outerp, agwStyle=LB.INB_FIT_LABELTEXT|LB.INB_LEFT|LB.INB_DRAW_SHADOW|LB.INB_GRADIENT_BACKGROUND)

		self.bookpages = {}
		maxdims = [0,0]
		for a,d in self.apps.items():
			enablestates = None
			if "enable" in self.apps[a]:
				enablestates = self.apps[a]["enable"]
			self.bookpages[a] = d["panel"](self, a, self.apps[a], enablestates)
			x,y = self.bookpages[a].GetSize()
			if x > maxdims[0]:
				maxdims[0] = x
			if y > maxdims[1]:
				maxdims[1] = y
			self.labelbook.AddPage(self.bookpages[a], d["label"], False)
		for k in self.bookpages.keys():
			self.bookpages[k].SetMinSize(maxdims)

		self.outersizer = wx.BoxSizer(wx.VERTICAL)
		self.outersizer.Add(self.adapterboxp, 0, wx.EXPAND | wx.ALL, 5)
		self.outersizer.Add(self.labelbook, 1, wx.EXPAND | wx.ALL, 5)
		self.outerp.SetSizer(self.outersizer)

		self.mainsizer = wx.BoxSizer(wx.VERTICAL)
		self.mainsizer.Add(self.outerp, 1, wx.EXPAND)
		self.mainsizer.SetSizeHints(self)
		self.SetSizer(self.mainsizer)

		self.adapterlist.Bind(wx.EVT_CHOICE, self.OnAdapterSelected)
		self.Bind(wx.EVT_CLOSE, self.OnClose)

		self.debuglog = HondaECU_LogPanel(self)

		dispatcher.connect(self.USBMonitorHandler, signal="USBMonitor", sender=dispatcher.Any)
		dispatcher.connect(self.AppPanelHandler, signal="AppPanel", sender=dispatcher.Any)
		dispatcher.connect(self.KlineWorkerHandler, signal="KlineWorker", sender=dispatcher.Any)

		self.usbmonitor = USBMonitor(self)
		self.klineworker = KlineWorker(self)

		self.Layout()
		self.Center()
		self.Show()

		self.usbmonitor.start()
		self.klineworker.start()

	def __clear_data(self):
		self.ecuinfo = {}

	def __clear_widgets(self):
		self.ecmidl.SetLabel("")
		self.flashcountl.SetLabel("")
		self.dtccountl.SetLabel("")
		self.statusicon.SetBitmap(self.statusicons[0])
		self.statusicon.Show(False)
		self.statusbar.OnSize(None)

	def KlineWorkerHandler(self, info, value):
		if info in ["ecmid","flashcount","dtc","dtccount","state"]:
			self.ecuinfo[info] = value
			if info == "state":
				self.statusicon.SetToolTip(wx.ToolTip("state: %s" % (str(value).split(".")[-1])))
				if value in [ECUSTATE.OFF,ECUSTATE.UNKNOWN]: #BLACK
					self.statusicon.SetBitmap(self.statusicons[0])
				elif value in [ECUSTATE.RECOVER_OLD,ECUSTATE.RECOVER_NEW]: #YELLOW
					self.statusicon.SetBitmap(self.statusicons[1])
				elif value in [ECUSTATE.OK]: #GREEN
					self.statusicon.SetBitmap(self.statusicons[2])
				elif value in [ECUSTATE.READ,ECUSTATE.READING,ECUSTATE.WRITEx00,ECUSTATE.WRITEx10,ECUSTATE.WRITEx20,ECUSTATE.WRITEx30,ECUSTATE.WRITEx40,ECUSTATE.WRITEx50,ECUSTATE.WRITING,ECUSTATE.ERASING,ECUSTATE.INIT_WRITE,ECUSTATE.INIT_RECOVER]: #BLUE
					self.statusicon.SetBitmap(self.statusicons[3])
				elif value in [ECUSTATE.POSTWRITEx0F,ECUSTATE.WRITEx0F]: #PURPLE
					self.statusicon.SetBitmap(self.statusicons[4])
				elif value in [ECUSTATE.POSTWRITEx00,ECUSTATE.POSTWRITEx12]: #RED
					self.statusicon.SetBitmap(self.statusicons[5])
			elif info == "ecmid":
				self.ecmidl.SetLabel("   ECM ID: %s" % " ".join(["%02x" % i for i in value]))
			elif info == "flashcount":
				if value >= 0:
					self.flashcountl.SetLabel("   Flash Count: %d" % value)
			elif info == "dtccount":
				if value >= 0:
					self.dtccountl.SetLabel("   DTC Count: %d" % value)
			self.statusbar.OnSize(None)
		elif info == "data":
			if not info in self.ecuinfo:
				self.ecuinfo[info] = {}
			self.ecuinfo[info][value[0]] = value[1:]

	def OnClose(self, event):
		self.run = False
		self.usbmonitor.join()
		self.klineworker.join()
		for w in wx.GetTopLevelWindows():
			w.Destroy()

	def OnDetectMap(self, event):
		with wx.FileDialog(self, "Open ECU dump file", wildcard="ECU dump (*.bin)|*.bin", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
			if fileDialog.ShowModal() == wx.ID_CANCEL:
				return
			pathname = fileDialog.GetPath()
			ecupn = os.path.splitext(os.path.split(pathname)[-1])[0]
			for i in ECM_IDs.values():
				if ecupn == i["pn"] and "keihinaddr" in i:
					fbin = open(pathname, "rb")
					nbyts = os.path.getsize(pathname)
					byts = bytearray(fbin.read(nbyts))
					fbin.close()
					idadr = int(i["keihinaddr"],16)
					wx.MessageDialog(None, "Map ID: " + byts[idadr:(idadr+7)].decode("ascii"), "", wx.CENTRE|wx.STAY_ON_TOP).ShowModal()
					return
			wx.MessageDialog(None, "Map ID: unknown", "", wx.CENTRE|wx.STAY_ON_TOP).ShowModal()

	def OnBinChecksum(self, event):
		with wx.FileDialog(self, "Open ECU dump file", wildcard="ECU dump (*.bin)|*.bin", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
			if fileDialog.ShowModal() == wx.ID_CANCEL:
				return
			pathname = fileDialog.GetPath()
			fbin = open(pathname, "rb")
			nbyts = os.path.getsize(pathname)
			byts = bytearray(fbin.read(nbyts))
			fbin.close()
			wx.MessageDialog(None, "Checksum: %s" % ("good" if checksum8bitHonda(byts)==0 else "bad"), "", wx.CENTRE|wx.STAY_ON_TOP).ShowModal()
			return

	def OnDebug(self, event):
		self.debuglog.Show()

	def OnAppButtonClicked(self, event):
		b = event.GetEventObject()
		if not b.appid in self.appanels:
			enablestates = None
			if "enable" in self.apps[b.appid]:
				enablestates = self.apps[b.appid]["enable"]
			self.appanels[b.appid] = self.apps[b.appid]["panel"](self, b.appid, self.apps[b.appid], enablestates)
			self.appbuttons[b.appid].Disable()
		self.appanels[b.appid].Raise()

	def USBMonitorHandler(self, action, device, config):
		dirty = False
		if action == "error":
			if platform.system() == "Windows":
				wx.MessageDialog(None, "libusb error: make sure libusbk is installed", "", wx.CENTRE|wx.STAY_ON_TOP).ShowModal()
		elif action == "add":
			if not device in self.ftdi_devices:
				self.ftdi_devices[device] = config
				dirty = True
		elif action =="remove":
			if device in self.ftdi_devices:
				if device == self.active_ftdi_device:
					dispatcher.send(signal="FTDIDevice", sender=self, action="deactivate", device=self.active_ftdi_device, config=self.ftdi_devices[self.active_ftdi_device])
					self.active_ftdi_device = None
					self.__clear_data()
				del self.ftdi_devices[device]
				dirty = True
		if len(self.ftdi_devices) > 0:
			if not self.active_ftdi_device:
				self.active_ftdi_device = list(self.ftdi_devices.keys())[0]
				dispatcher.send(signal="FTDIDevice", sender=self, action="activate", device=self.active_ftdi_device, config=self.ftdi_devices[self.active_ftdi_device])
				dirty = True
		else:
				pass
		if dirty:
			self.adapterlist.Clear()
			for device in self.ftdi_devices:
				cfg = self.ftdi_devices[device]
				self.adapterlist.Append("Bus %03d Device %03d: %s %s %s" % (cfg.bus, cfg.address, usb.util.get_string(cfg,cfg.iManufacturer), usb.util.get_string(cfg,cfg.iProduct), usb.util.get_string(cfg,cfg.iSerialNumber)))
			if self.active_ftdi_device:
				self.adapterlist.SetSelection(list(self.ftdi_devices.keys()).index(self.active_ftdi_device))


	def OnAdapterSelected(self, event):
		device = list(self.ftdi_devices.keys())[self.adapterlist.GetSelection()]
		if device != self.active_ftdi_device:
			if self.active_ftdi_device != None:
				dispatcher.send(signal="FTDIDevice", sender=self, action="deactivate", device=self.active_ftdi_device, config=self.ftdi_devices[self.active_ftdi_device])
			self.__clear_data()
			self.active_ftdi_device = device
			dispatcher.send(signal="FTDIDevice", sender=self, action="activate", device=self.active_ftdi_device, config=self.ftdi_devices[self.active_ftdi_device])

	def AppPanelHandler(self, appid, action):
		if action == "close":
			if appid in self.appanels:
				del self.appanels[appid]
				self.appbuttons[appid].Enable()
