import wx

from pydispatch import dispatcher

class HondaECU_AppPanel(wx.Panel):

	def __init__(self, parent, appid, appinfo, enablestates, *args, **kwargs):
		wx.Panel.__init__(self, parent.labelbook, *args, **kwargs)
		self.parent = parent
		self.appid = appid
		self.appinfo = appinfo
		self.enablestates = enablestates
		self.Build()
		dispatcher.connect(self.KlineWorkerHandler, signal="KlineWorker", sender=dispatcher.Any)
		dispatcher.connect(self.DeviceHandler, signal="FTDIDevice", sender=dispatcher.Any)
		# self.Bind(wx.EVT_CLOSE, self.OnClose)
		# self.Center()
		# wx.CallAfter(self.Show)

	# def OnClose(self, event):
	# 	dispatcher.send(signal="AppPanel", sender=self, appid=self.appid, action="close")
	# 	self.Destroy()

	def KlineWorkerHandler(self, info, value):
		pass

	def DeviceHandler(self, action, vendor, product, serial):
		pass

	def Build(self):
		pass
