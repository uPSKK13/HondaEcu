import wx
from pydispatch import dispatcher

class HondaECU_AppPanel(wx.Frame):

    def __init__(self, parent, appid, appinfo):
        wx.Frame.__init__(self, parent, title="HondaECU :: %s" % (appinfo["label"]))
        self.appid = appid
        self.appinfo = appinfo
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Center()
        self.Show()

    def OnClose(self, event):
        dispatcher.send(signal="AppPanel", sender=self, appid=self.appid, action="close")
        self.Destroy()
