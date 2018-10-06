import os
import sys
import usb1
import wx

class HondaECU_GUI(wx.Frame):

    def PollUSBDevices(self, event):
        new_devices = self.usbcontext.getDeviceList(skip_on_error=True)
        for device in new_devices:
            if device.getVendorID() == 0x403:
                if device.getProductID() in [0x6001, 0x60010, 0x6011, 0x6014, 0x6015]:
                    if not device in self.ftdi_devices:
                        print("Adding device (%s) to list" % device)
                        self.ftdi_devices.append(device)
                        self.UpdateDeviceList()
        for device in self.ftdi_devices:
            if not device in new_devices:
                if device == self.ftdi_active:
                    # TODO: CLOSE ACTIVE DEVICE
                    print("Deactivating device (%s)" % self.ftdi_active)
                    self.ftdi_active = None
                self.ftdi_devices.remove(device)
                self.UpdateDeviceList()
                print("Removing device (%s) from list" % device)

    def hotplug_callback(self, context, device, event):
        if device.getProductID() in [0x6001, 0x60010, 0x6011, 0x6014, 0x6015]:
            if event == usb1.HOTPLUG_EVENT_DEVICE_ARRIVED:
                if not device in self.ftdi_devices:
                    print("Adding device (%s) to list" % device)
                    self.ftdi_devices.append(device)
                    self.UpdateDeviceList()
            elif event == usb1.HOTPLUG_EVENT_DEVICE_LEFT:
                if device in self.ftdi_devices:
                    if device == self.ftdi_active:
                        # TODO: CLOSE ACTIVE DEVICE
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

        wx.Frame.__init__(self, None, title="HondaECU", size=(400,250), style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))

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
        flashbox = wx.StaticBoxSizer(wx.HORIZONTAL, panel, "Flash Operations")
        databox = wx.StaticBoxSizer(wx.HORIZONTAL, panel, "Engine Data")

        self.m_devices = wx.Choice(panel, wx.ID_ANY)
        devicebox.Add(self.m_devices, 1, wx.EXPAND | wx.ALL, 5)

        self.m_read = wx.Button(panel, wx.ID_ANY, "Read")
        self.m_write = wx.Button(panel, wx.ID_ANY, "Write")
        self.m_recover = wx.Button(panel, wx.ID_ANY, "Recover")
        self.m_checksum = wx.Button(panel, wx.ID_ANY, "Checksum")
        flashbox.AddStretchSpacer(1)
        flashbox.Add(self.m_read, 0, wx.ALL, 5)
        flashbox.Add(self.m_write, 0, wx.ALL, 5)
        flashbox.Add(self.m_recover, 0, wx.ALL, 5)
        flashbox.Add(self.m_checksum, 0, wx.ALL, 5)
        flashbox.AddStretchSpacer(1)

        self.m_scan = wx.Button(panel, wx.ID_ANY, "Scan")
        self.m_log = wx.Button(panel, wx.ID_ANY, "Log")
        databox.AddStretchSpacer(1)
        databox.Add(self.m_scan, 0, wx.ALL, 5)
        databox.Add(self.m_log, 0, wx.ALL, 5)
        databox.AddStretchSpacer(1)

        mainbox.AddStretchSpacer(1)
        mainbox.Add(devicebox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        mainbox.AddStretchSpacer(1)
        mainbox.Add(flashbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        mainbox.AddStretchSpacer(1)
        mainbox.Add(databox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        mainbox.AddStretchSpacer(1)

        panel.SetSizer(mainbox)
        panel.Layout()
        self.Centre()

        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.m_devices.Bind(wx.EVT_CHOICE, self.OnDeviceSelected)
        #self.Bind(wx.EVT_CLOSE, self.OnClose)

        if self.usbhotplug:
            print('Registering hotplug callback...')
            self.usbcontext.hotplugRegisterCallback(self.hotplug_callback, vendor_id=0x403)
            print('Callback registered. Monitoring events.')
        else:
            self.usbpolltimer = wx.Timer(self, wx.ID_ANY)
            self.Bind(wx.EVT_TIMER, self.PollUSBDevices)
            self.usbpolltimer.Start(250)

    def OnDeviceSelected(self, event):
        newdevice = self.ftdi_devices[self.m_devices.GetSelection()]
        if self.ftdi_active != None:
            if self.ftdi_active != newdevice:
                print("Deactivating device (%s)" % self.ftdi_active)
                # TODO: CLOSE ACTIVE DEVICE
                pass
        self.ftdi_active = newdevice
        print("Activating device (%s)" % self.ftdi_active)
        # TODO: OPEN ACTIVE DEVICE


    def UpdateDeviceList(self):
        self.m_devices.Clear()
        for i,d in enumerate(self.ftdi_devices):
            self.m_devices.Append(str(d) + " | " + d.getSerialNumber())
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
