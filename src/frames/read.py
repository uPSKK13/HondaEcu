import wx
import os
import time
from .base import HondaECU_AppPanel
from pydispatch import dispatcher

from ecu import *

class HondaECU_ReadPanel(HondaECU_AppPanel):

	def Build(self):
		self.bootwait = False
		self.statusbar = self.CreateStatusBar(1)
		self.statusbar.SetSize((-1, 28))
		self.statusbar.SetStatusStyles([wx.SB_SUNKEN])
		self.SetStatusBar(self.statusbar)

		self.outerp = wx.Panel(self)
		self.readp = wx.Panel(self.outerp)
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
		self.progress = wx.Gauge(self.readp, size=(400,-1), style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)
		self.progress.SetRange(100)

		self.flashpsizer = wx.GridBagSizer()
		self.flashpsizer.Add(self.wfilel, pos=(0,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.flashpsizer.Add(self.fpickerbox, pos=(0,1), span=(1,5), flag=wx.EXPAND|wx.RIGHT|wx.BOTTOM, border=10)
		self.flashpsizer.Add(self.optsbox, pos=(1,0), span=(1,6), flag=wx.BOTTOM, border=20)
		self.flashpsizer.Add(self.progress, pos=(2,0), span=(1,6), flag=wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND, border=20)
		self.flashpsizer.Add(self.gobutton, pos=(3,5), flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.RIGHT, border=10)
		self.flashpsizer.AddGrowableRow(3,1)
		self.flashpsizer.AddGrowableCol(5,1)
		self.readp.SetSizer(self.flashpsizer)

		self.outersizer = wx.BoxSizer(wx.VERTICAL)
		self.outersizer.Add(self.readp, 1, wx.EXPAND|wx.ALL, border=10)
		self.outerp.SetSizer(self.outersizer)

		self.mainsizer = wx.BoxSizer(wx.VERTICAL)
		self.mainsizer.Add(self.outerp, 1, wx.EXPAND)
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
			self.progress.SetValue(0)
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
