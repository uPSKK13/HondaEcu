import os
import sys
import usb1
import pylibftdi
import wx
import platform

from ecu import HondaECU

class HondaECU_GUI(wx.Frame):

    binsizes = {
        "56k":56,
        "256k":256,
        "512k":512,
        "1024k":1024
    }
    checksums = [
        "0xDFEF",
        "0x18FFE",
        "0x19FFE",
        "0x1FFFA",
        "0x3FFF8",
        "0x7FFF8",
        "0xFFFF8"
    ]

    def PollUSBDevices(self, event):
        new_devices = self.usbcontext.getDeviceList(skip_on_error=True)
        for device in new_devices:
            if device.getVendorID() == pylibftdi.driver.FTDI_VENDOR_ID:
                if device.getProductID() in pylibftdi.driver.USB_PID_LIST:
                    if not device in self.ftdi_devices:
                        print("Adding device (%s) to list" % device)
                        self.ftdi_devices.append(device)
                        self.UpdateDeviceList()
        for device in self.ftdi_devices:
            if not device in new_devices:
                if device == self.ftdi_active:
                    self.ecu.dev.close()
                    del self.ecu
                    self.ecu = None
                    print("Deactivating device (%s)" % self.ftdi_active)
                    self.ftdi_active = None
                self.ftdi_devices.remove(device)
                self.UpdateDeviceList()
                print("Removing device (%s) from list" % device)

    def hotplug_callback(self, context, device, event):
        if device.getProductID() in pylibftdi.driver.USB_PID_LIST:
            if event == usb1.HOTPLUG_EVENT_DEVICE_ARRIVED:
                if not device in self.ftdi_devices:
                    print("Adding device (%s) to list" % device)
                    self.ftdi_devices.append(device)
                    self.UpdateDeviceList()
            elif event == usb1.HOTPLUG_EVENT_DEVICE_LEFT:
                if device in self.ftdi_devices:
                    if device == self.ftdi_active:
                        self.ecu.dev.close()
                        del self.ecu
                        self.ecu = None
                        print("Deactivating device (%s)" % self.ftdi_active)
                        self.ftdi_active = None
                    self.ftdi_devices.remove(device)
                    self.UpdateDeviceList()
                    print("Removing device (%s) from list" % device)

    def __init__(self, usbcontext):
        self.ftdi_devices = []
        self.ftdi_active = None
        self.usbcontext = usbcontext
        self.usbhotplug = self.usbcontext.hasCapability(usb1.CAP_HAS_HOTPLUG)

        wx.Frame.__init__(self, None, title="HondaECU", size=(560,460), style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))

        self.statusbar = self.CreateStatusBar(1)

        if getattr( sys, 'frozen', False ) :
            ip = os.path.join(sys._MEIPASS,"honda.ico")
        else:
            ip = os.path.join(os.path.dirname(os.path.realpath(__file__)),"honda.ico")

        ib = wx.IconBundle()
        ib.AddIcon(ip)
        self.SetIcons(ib)

        menuBar = wx.MenuBar()
        menu = wx.Menu()
        m_exit = menu.Append(wx.ID_EXIT, "E&xit\tAlt-X", "Close window and exit program.")
        self.Bind(wx.EVT_MENU, self.OnClose, m_exit)
        menuBar.Append(menu, "&File")
        self.SetMenuBar(menuBar)

        panel = wx.Panel(self)
        mainbox = wx.BoxSizer(wx.VERTICAL)
        devicebox = wx.StaticBoxSizer(wx.HORIZONTAL, panel, "FTDI Devices")

        self.m_devices = wx.Choice(panel, wx.ID_ANY)
        devicebox.Add(self.m_devices, 1, wx.EXPAND | wx.ALL, 5)

        self.notebook = wx.Notebook(panel, wx.ID_ANY)

        flashp = wx.Panel(self.notebook)
        self.flashpsizer = wx.GridBagSizer(0,0)
        self.mode = wx.RadioBox(flashp, wx.ID_ANY, "Mode", choices=["Read","Write","Recover"])
        self.flashpsizer.Add(self.mode, pos=(0,0), span=(1,6), flag=wx.ALL|wx.ALIGN_CENTER, border=20)
        wfilel = wx.StaticText(flashp, wx.ID_ANY, "File")
        self.readfpicker = wx.FilePickerCtrl(flashp, wx.ID_ANY, wildcard="ECU dump (*.bin)|*.bin", style=wx.FLP_SAVE|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)
        self.writefpicker = wx.FilePickerCtrl(flashp, wx.ID_ANY, wildcard="ECU dump (*.bin)|*.bin", style=wx.FLP_OPEN|wx.FLP_FILE_MUST_EXIST|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)
        self.writefpicker.Show(False)
        self.flashpsizer.Add(wfilel, pos=(1,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
        self.fpickerbox = wx.BoxSizer(wx.HORIZONTAL)
        self.fpickerbox.Add(self.readfpicker, 1)
        self.fpickerbox.Add(self.writefpicker, 1)
        self.flashpsizer.Add(self.fpickerbox, pos=(1,1), span=(1,5), flag=wx.EXPAND|wx.RIGHT, border=10)
        wsizel = wx.StaticText(flashp, wx.ID_ANY, "Size")
        self.writesize = wx.Choice(flashp, wx.ID_ANY, choices=list(self.binsizes.keys()))
        self.flashpsizer.Add(wsizel, pos=(2,0), flag=wx.TOP|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.flashpsizer.Add(self.writesize, pos=(2,1), span=(1,1), flag=wx.TOP, border=5)
        wchecksuml = wx.StaticText(flashp, wx.ID_ANY, "Checksum")
        self.checksum = wx.Choice(flashp, wx.ID_ANY, choices=list(self.checksums))
        self.fixchecksum = wx.CheckBox(flashp, wx.ID_ANY, "Fix")
        self.flashpsizer.Add(wchecksuml, pos=(2,3), flag=wx.TOP|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.flashpsizer.Add(self.checksum, pos=(2,4), flag=wx.TOP, border=5)
        self.flashpsizer.Add(self.fixchecksum, pos=(2,5), flag=wx.TOP|wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.progress = wx.Gauge(flashp, wx.ID_ANY)
        self.progress.SetRange(100)
        self.progress.SetValue(0)
        self.flashpsizer.Add(self.progress, pos=(4,0), span=(1,6), flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_CENTER, border=10)
        self.gobutton = wx.Button(flashp, wx.ID_ANY, "Start")
        self.gobutton.Disable()
        self.flashpsizer.Add(self.gobutton, pos=(5,5), flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.BOTTOM|wx.RIGHT, border=10)
        self.flashpsizer.AddGrowableRow(3,1)
        self.flashpsizer.AddGrowableCol(5,1)
        flashp.SetSizer(self.flashpsizer)
        self.notebook.AddPage(flashp, "Flash Operations")

        datap = wx.Panel(self.notebook)
        self.notebook.AddPage(datap, "Diagnostic Tables")

        errorp = wx.Panel(self.notebook)
        self.notebook.AddPage(errorp, "Error Codes")

        mainbox.Add(devicebox, 0, wx.EXPAND | wx.ALL, 10)
        mainbox.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(mainbox)
        panel.Layout()
        self.Centre()

        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.m_devices.Bind(wx.EVT_CHOICE, self.OnDeviceSelected)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.mode.Bind(wx.EVT_RADIOBOX, self.OnModeChange)

        if self.usbhotplug:
            print('Registering hotplug callback...')
            self.usbcontext.hotplugRegisterCallback(self.hotplug_callback, vendor_id=pylibftdi.driver.FTDI_VENDOR_ID)
            print('Callback registered. Monitoring events.')
        else:
            self.usbpolltimer = wx.Timer(self, wx.ID_ANY)
            self.Bind(wx.EVT_TIMER, self.PollUSBDevices)
            self.usbpolltimer.Start(250)

    def OnModeChange(self, event):
        if self.mode.GetSelection() == 0:
            self.writefpicker.Show(False)
            self.readfpicker.Show(True)
        else:
            self.readfpicker.Show(False)
            self.writefpicker.Show(True)
        self.fpickerbox.Layout()

    def OnDeviceSelected(self, event):
        self.statusbar.SetStatusText("")
        newdevice = self.ftdi_devices[self.m_devices.GetSelection()]
        if self.ftdi_active != None:
            if self.ftdi_active != newdevice:
                print("Deactivating device (%s)" % self.ftdi_active)
                if self.ecu != None:
                    self.ecu.dev.close()
                    del self.ecu
                    self.ecu = None
        self.ftdi_active = newdevice
        print("Activating device (%s)" % self.ftdi_active)
        try:
            self.ecu = HondaECU(device_id=self.ftdi_active.getSerialNumber())
        except usb1.USBErrorNotSupported as e:
            self.ecu = None
            self.statusbar.SetStatusText("Incorrect driver for device, install libusbK with Zadig!")

    def UpdateDeviceList(self):
        self.m_devices.Clear()
        for i,d in enumerate(self.ftdi_devices):
            n = str(d)
            try:
                n += " | " + d.getSerialNumber()
            except usb1.USBErrorNotSupported:
                pass
            self.m_devices.Append(n)
            if self.ftdi_active == d:
                self.m_devices.SetSelection(i)
            if self.ftdi_active == None:
                self.ftdi_active = self.ftdi_devices[0]
                self.m_devices.SetSelection(0)
                self.OnDeviceSelected(None)

    def OnClose(self, event):
        dlg = wx.MessageDialog(self,
            "Do you really want to close this application?",
            "Confirm Exit", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            for d in self.ftdi_devices:
                d.close()
            self.Destroy()

    def OnIdle(self, event):
        if self.usbhotplug:
            self.usbcontext.handleEventsTimeout(0)
        event.RequestMore()

if __name__ == '__main__':

    usbcontext = usb1.USBContext()
    app = wx.App(redirect=False)
    gui = HondaECU_GUI(usbcontext)
    gui.Show()
    app.MainLoop()
