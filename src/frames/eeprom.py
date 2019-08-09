import wx
import string
import os
import time
import tarfile
import json
from .base import HondaECU_AppPanel
from pydispatch import dispatcher

from eculib.honda import *

class HondaECU_EEPROMPanel(HondaECU_AppPanel):

	def Build(self):
		self.wildcard = "EEPROM dump (*.bin)|*.bin"
		self.mainp = wx.Panel(self)

		self.formatbox = wx.RadioBox(self.mainp, label="Fill byte", choices=["0x00","0xFF"])

		self.wfilel = wx.StaticText(self.mainp, label="File")
		self.fpickerbox = wx.BoxSizer(wx.HORIZONTAL)
		self.fpickerbox.Add(self.wfilel, 1)
		self.fpickerbox.Add(self.formatbox, 0)

		self.readfpicker = wx.FilePickerCtrl(self.mainp, wildcard=self.wildcard, style=wx.FLP_SAVE|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)
		self.writefpicker = wx.FilePickerCtrl(self.mainp,wildcard=self.wildcard, style=wx.FLP_OPEN|wx.FLP_FILE_MUST_EXIST|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)

		self.mainsizer = wx.BoxSizer(wx.VERTICAL)
		self.mainsizer.Add(self.mainp, 1, wx.EXPAND|wx.ALL, border=10)
		self.SetSizer(self.mainsizer)

		self.gobutton = wx.Button(self.mainp, label="Read")
		self.gobutton.Disable()

		self.fpickerbox = wx.BoxSizer(wx.HORIZONTAL)
		self.fpickerbox.AddSpacer(5)
		self.fpickerbox.Add(self.readfpicker, 1)
		self.fpickerbox.Add(self.writefpicker, 1)

		self.modebox = wx.RadioBox(self.mainp, label="Mode", choices=["Read","Write","Format"])

		self.eeprompsizer = wx.GridBagSizer()
		self.eeprompsizer.Add(self.wfilel, pos=(0,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.eeprompsizer.Add(self.fpickerbox, pos=(0,1), span=(1,5), flag=wx.EXPAND|wx.RIGHT|wx.BOTTOM, border=10)
		self.eeprompsizer.Add(self.modebox, pos=(1,0), span=(1,2), flag=wx.ALIGN_LEFT|wx.ALIGN_BOTTOM|wx.LEFT, border=10)
		self.eeprompsizer.Add(self.gobutton, pos=(2,5), flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.RIGHT, border=10)
		self.eeprompsizer.AddGrowableRow(1,1)
		self.eeprompsizer.AddGrowableCol(5,1)
		self.mainp.SetSizer(self.eeprompsizer)

		self.mainsizer = wx.BoxSizer(wx.VERTICAL)
		self.mainsizer.Add(self.mainp, 1, wx.EXPAND|wx.ALL, border=10)
		self.SetSizer(self.mainsizer)

		self.readfpicker.Hide()
		self.formatbox.Hide()

		self.Fit()
		self.Layout()

		self.OnModeChange(None)

		self.modebox.Bind(wx.EVT_RADIOBOX, self.OnModeChange)

	def OnValidateMode(self, event):
		pass

	def OnModeChange(self, event):
		if self.modebox.GetSelection() == 0:
			self.gobutton.SetLabel("Read")
			self.writefpicker.Hide()
			self.formatbox.Hide()
			self.readfpicker.Show()
			self.wfilel.Show()
		elif self.modebox.GetSelection() == 1:
			self.gobutton.SetLabel("Write")
			self.writefpicker.Show()
			self.formatbox.Hide()
			self.readfpicker.Hide()
			self.wfilel.Show()
		else:
			self.gobutton.SetLabel("Format")
			self.writefpicker.Hide()
			self.formatbox.Show()
			self.readfpicker.Hide()
			self.wfilel.Hide()
		self.OnValidateMode(None)
		self.Layout()
