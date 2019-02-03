import wx

from pydispatch import dispatcher

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
