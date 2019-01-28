import wx
from pydispatch import dispatcher
from ecu import ECM_IDs

class HondaECU_AppPanel(wx.Frame):

    def __init__(self, parent, appid, appinfo, *args, **kwargs):
        wx.Frame.__init__(self, parent, title="HondaECU :: %s" % (appinfo["label"]), *args, **kwargs)
        self.parent = parent
        self.appid = appid
        self.appinfo = appinfo
        self.Build()
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Center()
        self.Show()

    def OnClose(self, event):
        dispatcher.send(signal="AppPanel", sender=self, appid=self.appid, action="close")
        self.Destroy()

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
        ecmid = wx.StaticText(self.infop, label=ecmids)
        if "flashcount" in self.parent.ecuinfo:
            flashcounts = str(self.parent.ecuinfo["flashcount"])
        flashcount = wx.StaticText(self.infop, label=flashcounts)
        model = wx.StaticText(self.infop, label=models)
        ecu = wx.StaticText(self.infop, label=ecus)
        infopsizer.Add(ecmidl, pos=(0,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
        infopsizer.Add(modell, pos=(1,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
        infopsizer.Add(ecul, pos=(2,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
        infopsizer.Add(flashcountl, pos=(3,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
        infopsizer.Add(ecmid, pos=(0,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
        infopsizer.Add(model, pos=(1,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
        infopsizer.Add(ecu, pos=(2,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
        infopsizer.Add(flashcount, pos=(3,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=5)
        self.infop.SetSizer(infopsizer)
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(self.infop, 0, wx.ALL, border=20)
        self.SetSizer(mainsizer)
        self.Layout()
        mainsizer.Fit(self)
