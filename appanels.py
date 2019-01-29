import struct
import time
import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from pydispatch import dispatcher
from ecu import ECM_IDs, DTC

class HondaECU_AppPanel(wx.Frame):

	def __init__(self, parent, appid, appinfo, *args, **kwargs):
		wx.Frame.__init__(self, parent, title="HondaECU :: %s" % (appinfo["label"]), *args, **kwargs)
		self.parent = parent
		self.appid = appid
		self.appinfo = appinfo
		self.Build()
		dispatcher.connect(self.KlineWorkerHandler, signal="KlineWorker", sender=dispatcher.Any)
		dispatcher.connect(self.DeviceHandler, signal="FTDIDevice", sender=dispatcher.Any)
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.Center()
		self.Show()

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

	def __init__(self, *args, **kwargs):
		kwargs["style"] = wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER
		HondaECU_AppPanel.__init__(self, *args, **kwargs)

	def Build(self):
		self.infop = wx.Panel(self)
		infopsizer = wx.GridBagSizer(4,2)
		ecmidl = wx.StaticText(self.infop, label="ECMID:")
		flashcountl = wx.StaticText(self.infop, label="Flash count:")
		modell = wx.StaticText(self.infop, label="Model:")
		ecul = wx.StaticText(self.infop, label="ECU P/N:")
		ecmids = "unknown"
		models = "unknown"
		ecus = "unknown"
		flashcounts = "unknown"
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
		infopsizer.Add(ecmidl, pos=(0,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(modell, pos=(1,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(ecul, pos=(2,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(flashcountl, pos=(3,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(self.ecmid, pos=(0,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(self.model, pos=(1,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(self.ecu, pos=(2,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
		infopsizer.Add(self.flashcount, pos=(3,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
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

	def __init__(self, *args, **kwargs):
		kwargs["style"] = wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER
		HondaECU_AppPanel.__init__(self, *args, **kwargs)

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

	def __init__(self, *args, **kwargs):
		kwargs["style"] = wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER
		HondaECU_AppPanel.__init__(self, *args, **kwargs)
		self.SetInitialSize((500,200))

	def Build(self):
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

	def OnGo(self, event):
		offset = int(self.offset.GetValue(), 16)
		data = self.readfpicker.GetPath()
		self.gobutton.Disable()
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
