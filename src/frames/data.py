import wx
import struct
from .base import HondaECU_AppPanel
from pydispatch import dispatcher

class HondaECU_DatalogPanel(HondaECU_AppPanel):

	def prepare_data1(self, data, t):
		data[1] = round(data[1]/0xff*5.0,2)
		data[2] = round(data[2]/1.6,2)
		data[3] = round(data[3]/0xff*5.0,2)
		data[4] = -40 + data[4]
		data[5] = round(data[5]/0xff*5.0,2)
		data[6] = -40 + data[6]
		data[7] = round(data[7]/0xff*5.0,2)
		data[11] = round(data[11]/10,2)
		data[13] = round(data[13]/0xffff*265.5,2)
		data[14] = round(-64 + data[14]/0xff*127.5,2)
		if t == 0x11:
			data[16] = round(data[16]/0xffff*8.0,4)
		return data

	def Build(self):
		self.datap = wx.Panel(self)

		self.d1pbox = wx.Panel(self)
		self.d1p = wx.Panel(self.d1pbox)
		self.d1psizer = wx.GridBagSizer()
		self.maintable = None
		self.sensors = {
			"Engine speed": [None,None,None,"rpm",0,True],
			"TPS sensor": [None,None,None,"%",2,True],
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
				if t in self.parent.ecuinfo["data"]:
					dd = self.parent.ecuinfo["data"][t][1][2:]
					if t == 0x11:
						u += "BH"
					elif t == 0x17:
						u += "BB"
					data = self.prepare_data1(list(struct.unpack(u, dd)), t)
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
				dd = self.parent.ecuinfo["data"][t][1][2:]
				if t == 0x11:
					u += "BH"
				elif t == 0x17:
					u += "BB"
				data = self.prepare_data1(list(struct.unpack(u, dd)), t)
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
