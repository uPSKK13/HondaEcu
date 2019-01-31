import struct
import time
import wx
import os
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from pydispatch import dispatcher
from ecu import ECM_IDs, DTC, ECUSTATE, do_validation

class HondaECU_AppPanel(wx.Frame):

	def __init__(self, parent, appid, appinfo, *args, **kwargs):
		wx.Frame.__init__(self, parent, title="HondaECU :: %s" % (appinfo["label"]), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER, *args, **kwargs)
		self.parent = parent
		self.appid = appid
		self.appinfo = appinfo
		self.Build()
		dispatcher.connect(self.KlineWorkerHandler, signal="KlineWorker", sender=dispatcher.Any)
		dispatcher.connect(self.DeviceHandler, signal="FTDIDevice", sender=dispatcher.Any)
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.Center()
		wx.CallAfter(self.Show)

	def OnClose(self, event):
		dispatcher.send(signal="AppPanel", sender=self, appid=self.appid, action="close")
		self.Destroy()

	def KlineWorkerHandler(self, info, value):
		pass

	def DeviceHandler(self, action, vendor, product, serial):
		pass

	def Build(self):
		pass

class HondaECU_InfoPanel(HondaECU_AppPanel):

	def Build(self):
		self.infop = wx.Panel(self)
		infopsizer = wx.GridBagSizer(4,2)
		ecmidl = wx.StaticText(self.infop, label="ECMID:")
		flashcountl = wx.StaticText(self.infop, label="Flash count:")
		modell = wx.StaticText(self.infop, label="Model:")
		ecul = wx.StaticText(self.infop, label="ECU P/N:")
		statel = wx.StaticText(self.infop, label="State:")
		ecmids = "unknown"
		models = "unknown"
		ecus = "unknown"
		flashcounts = "unknown"
		state = ECUSTATE.UNKNOWN
		if "state" in self.parent.ecuinfo:
			state = self.parent.ecuinfo["state"]
		if "ecmid" in self.parent.ecuinfo:
			ecmids = " ".join(["%02x" % i for i in self.parent.ecuinfo["ecmid"]])
			if self.parent.ecuinfo["ecmid"] in ECM_IDs:
				models = "%s (%s)" % (ECM_IDs[self.parent.ecuinfo["ecmid"]]["model"], ECM_IDs[self.parent.ecuinfo["ecmid"]]["year"])
				ecus = ECM_IDs[self.parent.ecuinfo["ecmid"]]["pn"]
		self.ecmid = wx.StaticText(self.infop, label=ecmids)
		if "flashcount" in self.parent.ecuinfo:
			flashcounts = str(self.parent.ecuinfo["flashcount"])
		self.flashcount = wx.StaticText(self.infop, label=flashcounts)
		self.model = wx.StaticText(self.infop, label=models)
		self.ecu = wx.StaticText(self.infop, label=ecus)
		self.state = wx.StaticText(self.infop, label=str(state))
		infopsizer.Add(ecmidl, pos=(0,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(modell, pos=(1,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(ecul, pos=(2,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(flashcountl, pos=(3,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(statel, pos=(4,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(self.ecmid, pos=(0,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(self.model, pos=(1,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(self.ecu, pos=(2,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(self.flashcount, pos=(3,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(self.state, pos=(4,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		self.infop.SetSizer(infopsizer)
		self.mainsizer = wx.BoxSizer(wx.VERTICAL)
		self.mainsizer.Add(self.infop, 1, wx.EXPAND|wx.ALL, border=20)
		self.SetSizer(self.mainsizer)
		self.Layout()
		self.mainsizer.Fit(self)

	def KlineWorkerHandler(self, info, value):
		if info == "ecmid":
			if len(value) > 0:
				ecmid = " ".join(["%02x" % i for i in value])
				model = "%s (%s)" % (ECM_IDs[value]["model"], ECM_IDs[self.parent.ecuinfo["ecmid"]]["year"])
				ecu = ECM_IDs[value]["pn"]
			else:
				ecmid = "unknown"
				model = "unknown"
				ecu = "unknown"
			self.ecmid.SetLabel(ecmid)
			self.model.SetLabel(model)
			self.ecu.SetLabel(ecu)
			self.Layout()
			self.mainsizer.Fit(self)
		elif info == "flashcount":
			if value >= 0:
				flashcount = str(value)
			else:
				flashcount = "unknown"
			self.flashcount.SetLabel(flashcount)
			self.Layout()
			self.mainsizer.Fit(self)

class ErrorListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
	def __init__(self, parent, ID, pos=wx.DefaultPosition,
				 size=wx.DefaultSize, style=0):
		wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
		ListCtrlAutoWidthMixin.__init__(self)
		self.setResizeColumn(2)

class HondaECU_ErrorPanel(HondaECU_AppPanel):

	def Build(self):
		self.SetMinSize((400,250))
		self.errorp = wx.Panel(self)

		self.errorlist = ErrorListCtrl(self.errorp, wx.ID_ANY, style=wx.LC_REPORT|wx.LC_HRULES)
		self.errorlist.InsertColumn(1,"DTC",format=wx.LIST_FORMAT_CENTER,width=50)
		self.errorlist.InsertColumn(2,"Description",format=wx.LIST_FORMAT_CENTER,width=-1)
		self.errorlist.InsertColumn(3,"Occurance",format=wx.LIST_FORMAT_CENTER,width=80)

		self.resetbutton = wx.Button(self.errorp, label="Clear Codes")
		self.resetbutton.Disable()

		self.errorsizer = wx.BoxSizer(wx.VERTICAL)
		self.errorsizer.Add(self.errorlist, 1, flag=wx.EXPAND|wx.ALL, border=10)
		self.errorsizer.Add(self.resetbutton, 0, flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.RIGHT, border=10)
		self.errorp.SetSizer(self.errorsizer)

		if "dtccount" in self.parent.ecuinfo and self.parent.ecuinfo["dtccount"] > 0:
			self.resetbutton.Enable(True)
		if "dtc" in self.parent.ecuinfo:
			for code in self.parent.ecuinfo["dtc"][hex(0x74)]:
				self.errorlist.Append([code, DTC[code] if code in DTC else "Unknown", "current"])
			for code in self.parent.ecuinfo["dtc"][hex(0x73)]:
				self.errorlist.Append([code, DTC[code] if code in DTC else "Unknown", "past"])

		self.mainsizer = wx.BoxSizer(wx.VERTICAL)
		self.mainsizer.Add(self.errorp, 1, wx.EXPAND)
		self.SetSizer(self.mainsizer)
		self.Layout()
		self.mainsizer.Fit(self)

		self.Bind(wx.EVT_BUTTON, self.OnClearCodes)

		wx.CallAfter(dispatcher.send, signal="ErrorPanel", sender=self, action="dtc.on")

	def OnClose(self, event):
		wx.CallAfter(dispatcher.send, signal="ErrorPanel", sender=self, action="dtc.off")
		HondaECU_AppPanel.OnClose(self, event)

	def OnClearCodes(self, event):
		self.resetbutton.Disable()
		self.errorlist.DeleteAllItems()
		wx.CallAfter(dispatcher.send, signal="ErrorPanel", sender=self, action="dtc.clear")

	def KlineWorkerHandler(self, info, value):
		if info == "dtccount":
			if value > 0:
				self.resetbutton.Enable(True)
			else:
				self.resetbutton.Enable(False)
				self.errorlist.DeleteAllItems()
		elif info == "dtc":
			self.errorlist.DeleteAllItems()
			for code in value[hex(0x74)]:
				self.errorlist.Append([code, DTC[code] if code in DTC else "Unknown", "current"])
			for code in value[hex(0x73)]:
				self.errorlist.Append([code, DTC[code] if code in DTC else "Unknown", "past"])
			self.Layout()

class HondaECU_DatalogPanel(HondaECU_AppPanel):

	def Build(self):
		self.datap = wx.Panel(self)

		self.d1pbox = wx.Panel(self)
		self.d1p = wx.Panel(self.d1pbox)
		self.d1psizer = wx.GridBagSizer()
		self.maintable = None
		self.sensors = {
			"Engine speed": [None,None,None,"rpm",0,True],
			"TPS sensor": [None,None,None,"°",2,True],
			"ECT sensor": [None,None,None,"°C",4,True],
			"IAT sensor": [None,None,None,"°C",6,True],
			"MAP sensor": [None,None,None,"kPa",8,True],
			"Battery voltage": [None,None,None,"V",11,True],
			"Vehicle speed": [None,None,None,"Km/h",12,True],
			"Injector duration": [None,None,None,"ms",13,True],
			"Ignition advance": [None,None,None,"°",14,True],
			"IACV pulse count": [None,None,None,"",15,True],
			"IACV command": [None,None,None,"",16,True],
		}
		for i,l in enumerate(self.sensors.keys()):
			self.sensors[l][0] = wx.StaticText(self.d1p, label="%s:" % l)
			self.sensors[l][1] = wx.StaticText(self.d1p, label="---")
			self.sensors[l][2] = wx.StaticText(self.d1p, label=self.sensors[l][3])
			self.d1psizer.Add(self.sensors[l][0], pos=(i,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, border=5)
			self.d1psizer.Add(self.sensors[l][1], pos=(i,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, border=5)
			self.d1psizer.Add(self.sensors[l][2], pos=(i,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL, border=5)
		if "data" in self.parent.ecuinfo:
			u = ">H12BHB"
			if not 0x11 in self.parent.ecuinfo["data"]:
				for s in ["IACV pulse count","IACV command"]:
					self.sensors[s][0].Hide()
					self.sensors[s][1].Hide()
					self.sensors[s][2].Hide()
					self.sensors[s][5] = False
			for t in [0x10,0x11,0x17]:
				if t == 0x11:
					u += "BH"
				elif t == 0x17:
					u += "BB"
				if t in self.parent.ecuinfo["data"]:
					data = list(struct.unpack(u, self.parent.ecuinfo["data"][t][1][2:]))
					data[1] = data[1]/0xff*5.0
					data[3] = data[3]/0xff*5.0
					data[4] = -40 + data[4]
					data[5] = data[5]/0xff*5.0
					data[6] = -40 + data[6]
					data[7] = data[7]/0xff*5.0
					data[11] = data[11]/10
					data[13] = data[13]/0xffff*265.5
					data[14] = -64 + data[14]/0xff*127.5
					if t == 0x11:
						data[16] = data[16]/0xffff*8.0
					for s in self.sensors:
						if self.sensors[s][5]:
							self.sensors[s][1].SetLabel(str(data[self.sensors[s][4]]))
					self.maintable = t
					break
		self.d1p.SetSizer(self.d1psizer)

		mt = "0x??"
		if not self.maintable is None:
			mt = "0x%x" % self.maintable
		self.d1pboxsizer = wx.StaticBoxSizer(wx.VERTICAL, self.d1pbox, "Table " + mt)
		self.d1pboxsizer.Add(self.d1p, 0, wx.ALL, border=10)
		self.d1pbox.SetSizer(self.d1pboxsizer)

		self.datapsizer = wx.GridBagSizer()
		self.datapsizer.Add(self.d1pbox, pos=(0,0), flag=wx.ALL, border=10)
		self.datap.SetSizer(self.datapsizer)

		self.mainsizer = wx.BoxSizer(wx.VERTICAL)
		self.mainsizer.Add(self.datap, 1, wx.EXPAND)
		self.SetSizer(self.mainsizer)
		self.Layout()
		self.mainsizer.Fit(self)

		wx.CallAfter(dispatcher.send, signal="DatalogPanel", sender=self, action="data.on")

	def OnClose(self, event):
		wx.CallAfter(dispatcher.send, signal="DatalogPanel", sender=self, action="data.off")
		HondaECU_AppPanel.OnClose(self, event)

	def KlineWorkerHandler(self, info, value):
		if info == "data":
			t = value[0]
			d = value[2][2:]
			if t in [0x10,0x11,0x17]:
				if self.maintable is None:
					if t != 0x11:
						for s in ["IACV pulse count","IACV command"]:
							self.sensors[s][0].Hide()
							self.sensors[s][1].Hide()
							self.sensors[s][2].Hide()
							self.sensors[s][5] = False
					self.maintable = t
					mt = "0x%x" % self.maintable
					self.d1pboxsizer.GetStaticBox().SetLabel("Table " + mt)
				u = ">H12BHB"
				if t == 0x11:
					u += "BH"
				elif t == 0x17:
					u += "BB"
				data = list(struct.unpack(u, d))
				data[1] = data[1]/0xff*5.0
				data[3] = data[3]/0xff*5.0
				data[4] = -40 + data[4]
				data[5] = data[5]/0xff*5.0
				data[6] = -40 + data[6]
				data[7] = data[7]/0xff*5.0
				data[11] = data[11]/10
				data[13] = data[13]/0xffff*265.5
				data[14] = -64 + data[14]/0xff*127.5
				if t == 0x11:
					data[16] = data[16]/0xffff*8.0
				for s in self.sensors:
					if self.sensors[s][5]:
						self.sensors[s][1].SetLabel(str(data[self.sensors[s][4]]))
			self.Layout()
			self.mainsizer.Fit(self)

	def DeviceHandler(self, action, vendor, product, serial):
		if action == "deactivate":
			for s in self.sensors:
				if self.sensors[s][5]:
					self.sensors[s][1].SetLabel("---")
			self.d1pboxsizer.GetStaticBox().SetLabel("Table 0x??")
			self.Layout()
			self.mainsizer.Fit(self)

class HondaECU_ReadPanel(HondaECU_AppPanel):

	def Build(self):
		self.bootwait = False
		self.statusbar = self.CreateStatusBar(1)
		self.statusbar.SetSize((-1, 28))
		self.statusbar.SetStatusStyles([wx.SB_SUNKEN])
		self.SetStatusBar(self.statusbar)

		self.readp = wx.Panel(self)
		self.wfilel = wx.StaticText(self.readp, label="File")
		self.readfpicker = wx.FilePickerCtrl(self.readp, wildcard="ECU dump (*.bin)|*.bin", style=wx.FLP_SAVE|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)
		self.offsetl = wx.StaticText(self.readp,label="Start Offset")
		self.offset = wx.TextCtrl(self.readp)
		self.offset.SetValue("0x0")
		self.gobutton = wx.Button(self.readp, label="Start")
		self.gobutton.Disable()

		self.optsbox = wx.BoxSizer(wx.HORIZONTAL)
		self.optsbox.Add(self.offsetl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.optsbox.Add(self.offset, 0)

		self.fpickerbox = wx.BoxSizer(wx.HORIZONTAL)
		self.fpickerbox.Add(self.readfpicker, 1)

		self.lastpulse = time.time()
		self.progress = wx.Gauge(self.readp, size=(400,-1))
		self.progress.SetRange(100)

		self.flashpsizer = wx.GridBagSizer()
		self.flashpsizer.Add(self.wfilel, pos=(0,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.flashpsizer.Add(self.fpickerbox, pos=(0,1), span=(1,5), flag=wx.EXPAND|wx.RIGHT, border=10)
		self.flashpsizer.Add(self.optsbox, pos=(1,0), span=(1,6), flag=wx.TOP, border=5)
		self.flashpsizer.Add(self.progress, pos=(2,0), span=(1,6), flag=wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND, border=20)
		self.flashpsizer.Add(self.gobutton, pos=(3,5), flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.RIGHT, border=10)
		self.flashpsizer.AddGrowableRow(3,1)
		self.flashpsizer.AddGrowableCol(5,1)
		self.readp.SetSizer(self.flashpsizer)

		self.mainsizer = wx.BoxSizer(wx.VERTICAL)
		self.mainsizer.Add(self.readp, 1, wx.EXPAND|wx.ALL, border=10)
		self.SetSizer(self.mainsizer)
		self.Layout()
		self.mainsizer.Fit(self)

		self.offset.Bind(wx.EVT_TEXT, self.OnValidateMode)
		self.readfpicker.Bind(wx.EVT_FILEPICKER_CHANGED, self.OnValidateMode)
		self.gobutton.Bind(wx.EVT_BUTTON, self.OnGo)

	def KlineWorkerHandler(self, info, value):
		if info == "progress":
			pulse = time.time()
			if pulse - self.lastpulse > .2:
				self.progress.Pulse()
				self.lastpulse = pulse
			self.statusbar.SetStatusText("Read " + value[1], 0)
		elif info == "read.result":
			self.statusbar.SetStatusText("Read complete (result=%s)" % value, 0)
		elif info == "state":
			if value == ECUSTATE.OFF:
				if self.bootwait:
					self.statusbar.SetStatusText("Turn on ECU!", 0)
		elif info == "password":
			if value:
				self.bootwait = False
			else:
				print("shit")

	def OnGo(self, event):
		offset = int(self.offset.GetValue(), 16)
		data = self.readfpicker.GetPath()
		self.gobutton.Disable()
		if self.parent.ecuinfo["state"] != ECUSTATE.READ:
			self.bootwait = True
			self.statusbar.SetStatusText("Turn off ECU!", 0)
		dispatcher.send(signal="ReadPanel", sender=self, data=data, offset=offset)

	def OnValidateMode(self, event):
		offset = None
		try:
			offset = int(self.offset.GetValue(), 16)
		except:
			pass
		if len(self.readfpicker.GetPath()) > 0 and offset != None and offset>=0:
			self.gobutton.Enable()
		else:
			self.gobutton.Disable()

class HondaECU_WritePanel(HondaECU_AppPanel):

	def Build(self):
		self.byts = None
		self.statusbar = self.CreateStatusBar(1)
		self.statusbar.SetSize((-1, 28))
		self.statusbar.SetStatusStyles([wx.SB_SUNKEN])
		self.SetStatusBar(self.statusbar)

		self.writep = wx.Panel(self)
		self.wfilel = wx.StaticText(self.writep, label="File")
		self.writefpicker = wx.FilePickerCtrl(self.writep,wildcard="ECU dump (*.bin)|*.bin", style=wx.FLP_OPEN|wx.FLP_FILE_MUST_EXIST|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)
		self.wchecksuml = wx.StaticText(self.writep,label="Checksum Location")
		self.fixchecksum = wx.CheckBox(self.writep, label="Fix")
		self.checksum = wx.TextCtrl(self.writep)
		self.offsetl = wx.StaticText(self.writep,label="Start Offset")
		self.offset = wx.TextCtrl(self.writep)
		self.offset.SetValue("0x0")
		self.gobutton = wx.Button(self.writep, label="Start")
		self.gobutton.Disable()
		self.checksum.Disable()

		self.optsbox = wx.BoxSizer(wx.HORIZONTAL)
		self.optsbox.Add(self.offsetl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.optsbox.Add(self.offset, 0)
		self.optsbox.Add(self.wchecksuml, 0, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.optsbox.Add(self.checksum, 0)
		self.optsbox.Add(self.fixchecksum, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)

		self.fpickerbox = wx.BoxSizer(wx.HORIZONTAL)
		self.fpickerbox.Add(self.writefpicker, 1)

		self.lastpulse = time.time()
		self.progress = wx.Gauge(self.writep, size=(400,-1))
		self.progress.SetRange(100)

		self.flashpsizer = wx.GridBagSizer()
		self.flashpsizer.Add(self.wfilel, pos=(0,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.flashpsizer.Add(self.fpickerbox, pos=(0,1), span=(1,5), flag=wx.EXPAND|wx.RIGHT, border=10)
		self.flashpsizer.Add(self.optsbox, pos=(1,0), span=(1,6), flag=wx.TOP, border=5)
		self.flashpsizer.Add(self.progress, pos=(2,0), span=(1,6), flag=wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND, border=20)
		self.flashpsizer.Add(self.gobutton, pos=(3,5), flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.RIGHT, border=10)
		self.flashpsizer.AddGrowableRow(3,1)
		self.flashpsizer.AddGrowableCol(5,1)
		self.writep.SetSizer(self.flashpsizer)

		self.mainsizer = wx.BoxSizer(wx.VERTICAL)
		self.mainsizer.Add(self.writep, 1, wx.EXPAND|wx.ALL, border=10)
		self.SetSizer(self.mainsizer)
		self.Layout()
		self.mainsizer.Fit(self)

		self.offset.Bind(wx.EVT_TEXT, self.OnValidateMode)
		self.writefpicker.Bind(wx.EVT_FILEPICKER_CHANGED, self.OnValidateMode)
		self.fixchecksum.Bind(wx.EVT_CHECKBOX, self.OnFix)
		self.checksum.Bind(wx.EVT_TEXT, self.OnValidateMode)
		self.gobutton.Bind(wx.EVT_BUTTON, self.OnGo)

	def OnFix(self, event):
		if self.fixchecksum.IsChecked():
			self.checksum.Enable()
		else:
			self.checksum.Disable()
		self.OnValidateMode(None)

	def KlineWorkerHandler(self, info, value):
		if info == "progress":
			if value[0]!= None and value[0] >= 0:
				self.progress.SetValue(value[0])
				self.statusbar.SetStatusText("Write: " + value[1], 0)
		elif info == "write.result":
			self.statusbar.SetStatusText("Write complete (result=%s)" % value, 0)

	def OnGo(self, event):
		offset = int(self.offset.GetValue(), 16)
		self.gobutton.Disable()
		dispatcher.send(signal="WritePanel", sender=self, data=self.byts, offset=offset)

	def OnValidateMode(self, event):
		offset = None
		try:
			offset = int(self.offset.GetValue(), 16)
		except:
			self.gobutton.Disable()
			return
		checksum = None
		try:
			if self.fixchecksum.IsChecked():
				checksum = int(self.checksum.GetValue(), 16)
			else:
				checksum = 0
		except:
			self.gobutton.Disable()
			return
		if len(self.writefpicker.GetPath()) > 0:
			if os.path.isfile(self.writefpicker.GetPath()):
				fbin = open(self.writefpicker.GetPath(), "rb")
				nbyts = os.path.getsize(self.writefpicker.GetPath())
				byts = bytearray(fbin.read(nbyts))
				fbin.close()
				if checksum >= nbyts:
					self.gobutton.Disable()
					return
				ret, status, self.byts = do_validation(byts, nbyts, checksum)
				if status != "bad":
					self.gobutton.Enable()
					return
		self.gobutton.Disable()

class HondaECU_TunePanelHelper(HondaECU_AppPanel):

	def gen_model_tree(self):
		modeltree = {}
		for ecmid, info in ECM_IDs.items():
			if not info["model"] in modeltree:
				modeltree[info["model"]] = {}
			if not info["year"] in modeltree[info["model"]]:
				modeltree[info["model"]][info["year"]] = {}
			if not info["pn"] in modeltree[info["model"]][info["year"]]:
				blcode = info["pn"].split("-")[1]
				modelstring = "%s_%s_%s" % (info["model"],blcode,info["year"])
				xdfdir = os.path.join(self.parent.basepath,"xdfs",modelstring)
				bindir = os.path.join(self.parent.basepath,"bins",modelstring)
				if os.path.exists(xdfdir) and os.path.exists(bindir):
					xdf = os.path.join(xdfdir,"38770-%s.xdf" % (blcode))
					bin = os.path.join(bindir,"%s.bin" % (info["pn"]))
					if os.path.isfile(xdf) and os.path.isfile(bin):
						modeltree[info["model"]][info["year"]][info["pn"]] = (ecmid,xdf,bin)
		models = list(modeltree.keys())
		for m in models:
			years = list(modeltree[m].keys())
			for y in years:
				if len(modeltree[m][y].keys()) == 0:
					del modeltree[m][y]
			if len(modeltree[m].keys()) == 0:
				del modeltree[m]
		return modeltree

	def Build(self):
		self.restrictions = {
			"CBR500R": {
				"MotoAmerica 2019: Junior Cup": {
					"Ignition": [10,4]
				}
			}
		}
		self.modeltree = self.gen_model_tree()
		self.tunepickerp = wx.Panel(self)
		tunepickerpsizer = wx.GridBagSizer()
		self.tunepickerp.SetSizer(tunepickerpsizer)
		self.newrp = wx.RadioButton(self.tunepickerp, wx.ID_ANY, "", style=wx.RB_GROUP, name="new")
		self.Bind(wx.EVT_RADIOBUTTON, self.HandleRadioButtons, self.newrp)
		self.openrp = wx.RadioButton(self.tunepickerp, wx.ID_ANY, "", name="open")
		self.Bind(wx.EVT_RADIOBUTTON, self.HandleRadioButtons, self.openrp)
		self.newp = wx.Panel(self.tunepickerp)
		newpsizer = wx.StaticBoxSizer(wx.VERTICAL, self.newp, "Start a new tune")
		modelp = wx.Panel(self.newp)
		modelpsizer = wx.GridBagSizer()
		modell = wx.StaticText(modelp, wx.ID_ANY, label="Model")
		yearl = wx.StaticText(modelp, wx.ID_ANY, label="Year")
		ecul = wx.StaticText(modelp, wx.ID_ANY, label="ECU")
		racel = wx.StaticText(modelp, wx.ID_ANY, label="Restrictions")
		self.model = wx.ComboBox(modelp, wx.ID_ANY, size=(350,-1), choices=list(self.modeltree.keys()))
		self.Bind(wx.EVT_COMBOBOX, self.ModelHandler, self.model)
		self.year = wx.ComboBox(modelp, wx.ID_ANY, size=(350,-1))
		self.Bind(wx.EVT_COMBOBOX, self.YearHandler, self.year)
		self.year.Disable()
		self.ecu = wx.ComboBox(modelp, wx.ID_ANY, size=(350,-1))
		self.Bind(wx.EVT_COMBOBOX, self.ECUHandler, self.ecu)
		self.ecu.Disable()
		self.race = wx.ComboBox(modelp, wx.ID_ANY, size=(350,-1))
		self.Bind(wx.EVT_COMBOBOX, self.RaceHandler, self.race)
		self.race.Disable()
		modelpsizer.Add(modell, pos=(0,0), flag=wx.ALIGN_RIGHT|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=5)
		modelpsizer.Add(yearl, pos=(1,0), flag=wx.ALIGN_RIGHT|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=5)
		modelpsizer.Add(ecul, pos=(2,0), flag=wx.ALIGN_RIGHT|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=5)
		modelpsizer.Add(racel, pos=(3,0), flag=wx.ALIGN_RIGHT|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=5)
		modelpsizer.Add(self.model, pos=(0,1), flag=wx.ALIGN_LEFT|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=5)
		modelpsizer.Add(self.year, pos=(1,1), flag=wx.ALIGN_LEFT|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=5)
		modelpsizer.Add(self.ecu, pos=(2,1), flag=wx.ALIGN_LEFT|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=5)
		modelpsizer.Add(self.race, pos=(3,1), flag=wx.ALIGN_LEFT|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=5)
		modelp.SetSizer(modelpsizer)
		newpsizer.Add(modelp, 1, wx.EXPAND|wx.ALL, border=10)
		self.newp.SetSizer(newpsizer)
		self.openp = wx.Panel(self.tunepickerp)
		self.openp.Disable()
		openpsizer = wx.StaticBoxSizer(wx.VERTICAL, self.openp, "Open an existing tune")
		self.openpicker = wx.FilePickerCtrl(self.openp, wildcard="HondaECU tune file (*.htf)|*.htf", style=wx.FLP_OPEN|wx.FLP_FILE_MUST_EXIST|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL, size=(400,-1))
		openpsizer.Add(self.openpicker, 1, wx.EXPAND|wx.ALL, border=10)
		self.openp.SetSizer(openpsizer)
		self.continueb = wx.Button(self.tunepickerp, label="Continue")
		self.continueb.Disable()
		tunepickerpsizer.Add(self.newrp, pos=(0,0), flag=wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=10)
		tunepickerpsizer.Add(self.openrp, pos=(1,0), flag=wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=10)
		tunepickerpsizer.Add(self.newp, pos=(0,1), flag=wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=10)
		tunepickerpsizer.Add(self.openp, pos=(1,1), flag=wx.ALIGN_RIGHT|wx.EXPAND|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=10)
		tunepickerpsizer.Add(self.continueb, pos=(2,0), span=(1,2), flag=wx.ALIGN_RIGHT|wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=10)

		self.mainsizer = wx.BoxSizer(wx.VERTICAL)
		self.mainsizer.Add(self.tunepickerp, 1, wx.EXPAND|wx.ALL, border=10)
		self.SetSizer(self.mainsizer)
		self.Layout()
		self.mainsizer.Fit(self)

		self.Bind(wx.EVT_BUTTON, self.OnContinue, self.continueb)
		self.Bind(wx.EVT_FILEPICKER_CHANGED, self.ValidateContinueButton, self.openpicker)

	def OnContinue(self, event):
		if self.newrp.GetValue():
			ecupn = self.ecu.GetValue()
			model = self.model.GetValue()
			year = self.year.GetValue()
			r = self.race.GetValue()
			restrictions = None
			if r != "":
				if r in self.restrictions[model]:
					restrictions = self.restrictions[model][r]
			else:
				r = None
			metainfo = {
				"model": model,
				"year": year,
				"ecupn": ecupn,
				"restriction":	r,
				"restrictions":	restrictions
			}
			_, xdf, bin = self.modeltree[model][year][ecupn]
			dispatcher.send(signal="TunePanelHelper", sender=self, xdf=xdf, bin=bin, metainfo=metainfo, htf=None)
			wx.CallAfter(self.Destroy)
		elif self.openrp.GetValue():
			dispatcher.send(signal="TunePanelHelper", sender=self, xdf=None, bin=None, metainfo=None, htf=self.openpicker.GetPath())
			wx.CallAfter(self.Destroy)

	def ValidateContinueButton(self, event):
		if self.newrp.GetValue():
			if self.ecu.GetValue() != "":
				self.continueb.Enable()
			else:
				self.continueb.Disable()
		elif self.openrp.GetValue():
			if os.path.isfile(self.openpicker.GetPath()):
				self.continueb.Enable()
			else:
				self.continueb.Disable()
		else:
			self.continueb.Disable()

	def HandleRadioButtons(self, event):
		if event.GetEventObject().GetName() == "open":
			self.openp.Enable()
			self.newp.Disable()
		elif event.GetEventObject().GetName() == "new":
			self.openp.Disable()
			self.newp.Enable()
		self.ValidateContinueButton(None)

	def ModelHandler(self, event):
		self.year.Clear()
		self.year.SetValue("")
		self.ecu.Clear()
		self.ecu.SetValue("")
		self.race.Clear()
		self.race.SetValue("")
		model = event.GetEventObject().GetValue()
		if model in self.restrictions:
			for r in self.restrictions[model]:
				self.race.Append(r)
		years = self.modeltree[model].keys()
		if len(years) > 0:
			for y in years:
				self.year.Append(y)
			self.year.Enable()
			self.race.Enable()
		else:
			self.year.Disable()
			self.ecu.Disable()
			self.race.Disable()
		self.ValidateContinueButton(None)

	def YearHandler(self, event):
		self.ecu.Clear()
		self.ecu.SetValue("")
		ecus = self.modeltree[self.model.GetValue()][event.GetEventObject().GetValue()].keys()
		if len(ecus) > 0:
			for e in ecus:
				self.ecu.Append(e)
			self.ecu.Enable()
		else:
			self.ecu.Disable()
		self.ValidateContinueButton(None)

	def ECUHandler(self, event):
		self.ValidateContinueButton(None)

	def RaceHandler(self, event):
		self.ValidateContinueButton(None)
