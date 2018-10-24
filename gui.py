import os, sys
import usb1
import pylibftdi
import wx
import wx.adv
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

from ecu import *

binsizes = {
	"56kB":56,
	"256kB":256,
	"512kB":512,
	"1024kB":1024
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

DEVICE_STATE_SETUP = -2
DEVICE_STATE_ERROR = -1
DEVICE_STATE_INIT_A = 0
DEVICE_STATE_INIT_B = 1
DEVICE_STATE_UNKNOWN = 2
DEVICE_STATE_CONNECTED = 3
DEVICE_STATE_CLEAR_CODES = 4
DEVICE_STATE_POWER_OFF = 5
DEVICE_STATE_POWER_ON = 6
DEVICE_STATE_READ_SECURITY = 7
DEVICE_STATE_READ = 8
DEVICE_STATE_WRITE_INIT = 9
DEVICE_STATE_RECOVER_INIT = 10
DEVICE_STATE_ERASE = 11
DEVICE_STATE_ERASE_WAIT = 12
DEVICE_STATE_WRITE = 13
DEVICE_STATE_WRITE_FINALIZE = 14
DEVICE_STATE_POST_READ = 15
DEVICE_STATE_POST_WRITE = 16

class ErrorListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
	def __init__(self, parent, ID, pos=wx.DefaultPosition,
				 size=wx.DefaultSize, style=0):
		wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
		ListCtrlAutoWidthMixin.__init__(self)
		self.setResizeColumn(2)

class ErrorPanel(wx.Panel):

	def __init__(self, gui):
		wx.Panel.__init__(self, gui.notebook)

		self.errorlist = ErrorListCtrl(self, wx.ID_ANY, style=wx.LC_REPORT)
		self.errorlist.InsertColumn(1,"DTC",format=wx.LIST_FORMAT_CENTER,width=50)
		self.errorlist.InsertColumn(2,"Description",format=wx.LIST_FORMAT_CENTER,width=-1)
		self.errorlist.InsertColumn(3,"Occurance",format=wx.LIST_FORMAT_CENTER,width=80)

		self.resetbutton = wx.Button(self, label="Clear Codes")
		self.resetbutton.Disable()

		self.errorsizer = wx.BoxSizer(wx.VERTICAL)
		self.errorsizer.Add(self.errorlist, 1, flag=wx.EXPAND|wx.ALL, border=10)
		self.errorsizer.Add(self.resetbutton, 0, flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.RIGHT, border=10)
		self.SetSizer(self.errorsizer)

		self.Bind(wx.EVT_BUTTON, gui.OnClearCodes)

class InfoPanel(wx.Panel):

	def __init__(self, gui):
		wx.Panel.__init__(self, gui.notebook)

		self.ecmidl = wx.StaticText(self, label="ECM ID:")
		self.ecmid = wx.StaticText(self, label="")
		self.statusl = wx.StaticText(self, label="Status:")
		self.status = wx.StaticText(self, label="")
		self.flashcountl = wx.StaticText(self,label="Flash count:")
		self.flashcount = wx.StaticText(self, label="")

		self.infopsizer = wx.GridBagSizer(0,0)
		self.infopsizer.Add(self.ecmidl, pos=(0,0), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=10)
		self.infopsizer.Add(self.ecmid, pos=(0,1), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT, border=10)
		self.infopsizer.Add(self.statusl, pos=(1,0), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=10)
		self.infopsizer.Add(self.status, pos=(1,1), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT, border=10)
		self.infopsizer.Add(self.flashcountl, pos=(2,0), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=10)
		self.infopsizer.Add(self.flashcount, pos=(2,1), flag=wx.LEFT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT, border=10)
		self.infopsizer.AddGrowableCol(1,1)
		self.SetSizer(self.infopsizer)

class DataPanel(wx.Panel):

	def __init__(self, gui):
		wx.Panel.__init__(self, gui.notebook)

		enginespeedl = wx.StaticText(self, label="Engine speed")
		vehiclespeedl = wx.StaticText(self, label="Vehicle speed")
		ectsensorl = wx.StaticText(self, label="ECT sensor")
		iatsensorl = wx.StaticText(self, label="IAT sensor")
		mapsensorl = wx.StaticText(self, label="MAP sensor")
		tpsensorl = wx.StaticText(self, label="TP sensor")
		batteryvoltagel = wx.StaticText(self, label="Battery")
		injectorl = wx.StaticText(self, label="Injector")
		advancel = wx.StaticText(self, label="Advance")
		iacvpl = wx.StaticText(self, label="IACV pulse count")
		iacvcl = wx.StaticText(self, label="IACV command")
		eotsensorl = wx.StaticText(self, label="EOT sensor")
		tcpsensorl = wx.StaticText(self, label="TCP sensor")
		apsensorl = wx.StaticText(self, label="AP sensor")
		racvalvel = wx.StaticText(self, label="RAC valve direction")
		o2volt1l = wx.StaticText(self, label="O2 sensor voltage #1")
		o2heat1l = wx.StaticText(self, label="O2 sensor heater #1")
		sttrim1l = wx.StaticText(self, label="ST fuel trim #1")

		self.enginespeedl = wx.StaticText(self, label="---")
		self.vehiclespeedl = wx.StaticText(self, label="---")
		self.ectsensorl = wx.StaticText(self, label="---")
		self.iatsensorl = wx.StaticText(self, label="---")
		self.mapsensorl = wx.StaticText(self, label="---")
		self.tpsensorl = wx.StaticText(self, label="---")
		self.batteryvoltagel = wx.StaticText(self, label="---")
		self.injectorl = wx.StaticText(self, label="---")
		self.advancel = wx.StaticText(self, label="---")
		self.iacvpl = wx.StaticText(self, label="---")
		self.iacvcl = wx.StaticText(self, label="---")
		self.eotsensorl = wx.StaticText(self, label="---")
		self.tcpsensorl = wx.StaticText(self, label="---")
		self.apsensorl = wx.StaticText(self, label="---")
		self.racvalvel = wx.StaticText(self, label="---")
		self.o2volt1l = wx.StaticText(self, label="---")
		self.o2heat1l = wx.StaticText(self, label="---")
		self.sttrim1l = wx.StaticText(self, label="---")

		enginespeedlu = wx.StaticText(self, label="rpm")
		vehiclespeedlu = wx.StaticText(self, label="Km/h")
		ectsensorlu = wx.StaticText(self, label="°C")
		iatsensorlu = wx.StaticText(self, label="°C")
		mapsensorlu = wx.StaticText(self, label="kPa")
		tpsensorlu = wx.StaticText(self, label="°")
		batteryvoltagelu = wx.StaticText(self, label="V")
		injectorlu = wx.StaticText(self, label="ms")
		advancelu = wx.StaticText(self, label="°")
		iacvplu = wx.StaticText(self, label="Steps")
		iacvclu = wx.StaticText(self, label="g/sec")
		eotsensorlu = wx.StaticText(self, label="°C")
		tcpsensorlu = wx.StaticText(self, label="kPa")
		apsensorlu = wx.StaticText(self, label="kPa")
		racvalvelu = wx.StaticText(self, label="l/min")
		o2volt1lu = wx.StaticText(self, label="V")

		o2volt2l = wx.StaticText(self, label="O2 sensor voltage #2")
		o2heat2l = wx.StaticText(self, label="O2 sensor heater #2")
		sttrim2l = wx.StaticText(self, label="ST fuel trim #2")
		basvl = wx.StaticText(self, label="Bank angle sensor input")
		egcvil = wx.StaticText(self, label="EGCV position input")
		egcvtl = wx.StaticText(self, label="EGCV position target")
		egcvll = wx.StaticText(self, label="EGCV load")
		lscl = wx.StaticText(self, label="Linear solenoid current")
		lstl = wx.StaticText(self, label="Linear solenoid target")
		lsvl = wx.StaticText(self, label="Linear solenoid load")
		oscl = wx.StaticText(self, label="Overflow solenoid")
		estl = wx.StaticText(self, label="Exhaust surface temp")
		icsl = wx.StaticText(self, label="Ignition cut-off switch")
		ersl = wx.StaticText(self, label="Engine run switch")
		scsl = wx.StaticText(self, label="SCS")
		fpcl = wx.StaticText(self, label="Fuel pump control")
		intakeairl = wx.StaticText(self, label="Intake AIR control valve")
		pairvl = wx.StaticText(self, label="PAIR solenoid valve")

		self.o2volt2l = wx.StaticText(self, label="---")
		self.o2heat2l = wx.StaticText(self, label="---")
		self.sttrim2l = wx.StaticText(self, label="---")
		self.basvl = wx.StaticText(self, label="---")
		self.egcvil = wx.StaticText(self, label="---")
		self.egcvtl = wx.StaticText(self, label="---")
		self.egcvll = wx.StaticText(self, label="---")
		self.lscl = wx.StaticText(self, label="---")
		self.lstl = wx.StaticText(self, label="---")
		self.lsvl = wx.StaticText(self, label="---")
		self.oscl = wx.StaticText(self, label="---")
		self.estl = wx.StaticText(self, label="---")
		self.icsl = wx.StaticText(self, label="---")
		self.ersl = wx.StaticText(self, label="---")
		self.scsl = wx.StaticText(self, label="---")
		self.fpcl = wx.StaticText(self, label="---")
		self.intakeairl = wx.StaticText(self, label="---")
		self.pairvl = wx.StaticText(self, label="---")

		o2volt2lu = wx.StaticText(self, label="V")
		basvlu = wx.StaticText(self, label="V")
		egcvilu = wx.StaticText(self, label="V")
		egcvtlu = wx.StaticText(self, label="V")
		egcvllu = wx.StaticText(self, label="%")
		lsclu = wx.StaticText(self, label="A")
		lstlu = wx.StaticText(self, label="A")
		lsvlu = wx.StaticText(self, label="%")
		osclu = wx.StaticText(self, label="%")
		estlu = wx.StaticText(self, label="°C")

		fc1l = wx.StaticText(self, label="Fan control")
		basl = wx.StaticText(self, label="Bank angle sensor")
		esl = wx.StaticText(self, label="Emergency switch")
		mstsl = wx.StaticText(self, label="MST switch")
		lsl = wx.StaticText(self, label="Limit switch")
		otssl = wx.StaticText(self, label="OTS switch")
		lysl = wx.StaticText(self, label="LY switch")
		otscl = wx.StaticText(self, label="OTS control")
		evapl = wx.StaticText(self, label="EVAP pc solenoid")
		vtecl = wx.StaticText(self, label="VTEC valve pressure switch")
		pcvl = wx.StaticText(self, label="PCV solenoid")
		startersl = wx.StaticText(self, label="Starter switch signal")
		startercl = wx.StaticText(self, label="Starter switch command")
		fc2l = wx.StaticText(self, label="Fan control 2nd level")
		gearsl = wx.StaticText(self, label="Gear position switch")
		startervl = wx.StaticText(self, label="Starter solenoid valve")
		mainrl = wx.StaticText(self, label="Main relay control")
		filampl = wx.StaticText(self, label="FI control lamp")

		self.fc1l = wx.StaticText(self, label="---")
		self.basl = wx.StaticText(self, label="---")
		self.esl = wx.StaticText(self, label="---")
		self.mstsl = wx.StaticText(self, label="---")
		self.lsl = wx.StaticText(self, label="---")
		self.otssl = wx.StaticText(self, label="---")
		self.lysl = wx.StaticText(self, label="---")
		self.otscl = wx.StaticText(self, label="---")
		self.evapl = wx.StaticText(self, label="---")
		self.vtecl = wx.StaticText(self, label="---")
		self.pcvl = wx.StaticText(self, label="---")
		self.startersl = wx.StaticText(self, label="---")
		self.startercl = wx.StaticText(self, label="---")
		self.fc2l = wx.StaticText(self, label="---")
		self.gearsl = wx.StaticText(self, label="---")
		self.startervl = wx.StaticText(self, label="---")
		self.mainrl = wx.StaticText(self, label="---")
		self.filampl = wx.StaticText(self, label="---")

		self.datapsizer = wx.GridBagSizer(1,5)

		self.datapsizer.Add(enginespeedl, pos=(0,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.TOP, border=10)
		self.datapsizer.Add(vehiclespeedl, pos=(1,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(ectsensorl, pos=(2,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(iatsensorl, pos=(3,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(mapsensorl, pos=(4,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(tpsensorl, pos=(5,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(batteryvoltagel, pos=(6,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(injectorl, pos=(7,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(advancel, pos=(8,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(iacvpl, pos=(9,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(iacvcl, pos=(10,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(eotsensorl, pos=(11,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(tcpsensorl, pos=(12,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(apsensorl, pos=(13,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(racvalvel, pos=(14,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(o2volt1l, pos=(15,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT, border=10)
		self.datapsizer.Add(o2heat1l, pos=(16,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(sttrim1l, pos=(17,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.BOTTOM, border=10)

		self.datapsizer.Add(self.enginespeedl, pos=(0,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.TOP, border=10)
		self.datapsizer.Add(self.vehiclespeedl, pos=(1,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.ectsensorl, pos=(2,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.iatsensorl, pos=(3,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.mapsensorl, pos=(4,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.tpsensorl, pos=(5,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.batteryvoltagel, pos=(6,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.injectorl, pos=(7,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.advancel, pos=(8,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.iacvpl, pos=(9,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.iacvcl, pos=(10,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.eotsensorl, pos=(11,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.tcpsensorl, pos=(12,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.apsensorl, pos=(13,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.racvalvel, pos=(14,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.o2volt1l, pos=(15,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.o2heat1l, pos=(16,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.sttrim1l, pos=(17,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.BOTTOM, border=10)

		self.datapsizer.Add(enginespeedlu, pos=(0,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.TOP, border=10)
		self.datapsizer.Add(vehiclespeedlu, pos=(1,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(ectsensorlu, pos=(2,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(iatsensorlu, pos=(3,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(mapsensorlu, pos=(4,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(tpsensorlu, pos=(5,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(batteryvoltagelu, pos=(6,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(injectorlu, pos=(7,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(advancelu, pos=(8,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(iacvplu, pos=(9,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(iacvclu, pos=(10,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(eotsensorlu, pos=(11,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(tcpsensorlu, pos=(12,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(apsensorlu, pos=(13,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(racvalvelu, pos=(14,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(o2volt1lu, pos=(15,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)

		self.datapsizer.Add(o2volt2l, pos=(0,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.TOP, border=10)
		self.datapsizer.Add(o2heat2l, pos=(1,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(sttrim2l, pos=(2,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(basvl, pos=(3,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(egcvil, pos=(4,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(egcvtl, pos=(5,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(egcvll, pos=(6,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(lscl, pos=(7,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(lstl, pos=(8,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(lsvl, pos=(9,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(oscl, pos=(10,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(estl, pos=(11,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(icsl, pos=(12,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(ersl, pos=(13,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(scsl, pos=(14,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(fpcl, pos=(15,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(intakeairl, pos=(16,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(pairvl, pos=(17,4), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.BOTTOM, border=10)

		self.datapsizer.Add(self.o2volt2l, pos=(0,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.TOP, border=10)
		self.datapsizer.Add(self.o2heat2l, pos=(1,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.sttrim2l, pos=(2,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.basvl, pos=(3,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.egcvil, pos=(4,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.egcvtl, pos=(5,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.egcvll, pos=(6,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.lscl, pos=(7,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.lstl, pos=(8,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.lsvl, pos=(9,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.oscl, pos=(10,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.estl, pos=(11,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.icsl, pos=(12,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.ersl, pos=(13,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.scsl, pos=(14,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.fpcl, pos=(15,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.intakeairl, pos=(16,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(self.pairvl, pos=(17,5), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.BOTTOM, border=10)

		self.datapsizer.Add(o2volt2lu, pos=(0,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.TOP, border=10)
		self.datapsizer.Add(basvlu, pos=(3,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(egcvilu, pos=(4,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(egcvtlu, pos=(5,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(egcvllu, pos=(6,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(lsclu, pos=(7,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(lstlu, pos=(8,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(lsvlu, pos=(9,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(osclu, pos=(10,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(estlu, pos=(11,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)

		self.datapsizer.Add(fc1l, pos=(0,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.TOP, border=10)
		self.datapsizer.Add(basl, pos=(1,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(esl, pos=(2,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(mstsl, pos=(3,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(lsl, pos=(4,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(otssl, pos=(5,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(lysl, pos=(6,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(otscl, pos=(7,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(evapl, pos=(8,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(vtecl, pos=(9,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(pcvl, pos=(10,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(startersl, pos=(11,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(startercl, pos=(12,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(fc2l, pos=(13,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(gearsl, pos=(14,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(startervl, pos=(15,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(mainrl, pos=(16,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=0)
		self.datapsizer.Add(filampl, pos=(17,8), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.BOTTOM, border=10)

		self.datapsizer.Add(self.fc1l, pos=(0,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT|wx.TOP, border=10)
		self.datapsizer.Add(self.basl, pos=(1,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.esl, pos=(2,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.mstsl, pos=(3,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.lsl, pos=(4,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.otssl, pos=(5,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.lysl, pos=(6,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.otscl, pos=(7,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.evapl, pos=(8,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.vtecl, pos=(9,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.pcvl, pos=(10,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.startersl, pos=(11,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.startercl, pos=(12,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.fc2l, pos=(13,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.gearsl, pos=(14,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.startervl, pos=(15,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.mainrl, pos=(16,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		self.datapsizer.Add(self.filampl, pos=(17,9), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT|wx.BOTTOM, border=10)

		self.datapsizer.AddGrowableCol(3,1)
		self.datapsizer.AddGrowableCol(7,1)
		for r in range(18):
			self.datapsizer.AddGrowableRow(r,1)

		self.SetSizer(self.datapsizer)

class FlashPanel(wx.Panel):

	def __init__(self, gui):
		wx.Panel.__init__(self, gui.notebook)

		self.mode = wx.RadioBox(self, label="Mode", choices=["Read","Write","Recover"])
		self.wfilel = wx.StaticText(self, label="File")
		self.wsizel = wx.StaticText(self, label="Size")
		self.wchecksuml = wx.StaticText(self,label="Checksum")
		self.readfpicker = wx.FilePickerCtrl(self, wildcard="ECU dump (*.bin)|*.bin", style=wx.FLP_SAVE|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)
		self.writefpicker = wx.FilePickerCtrl(self,wildcard="ECU dump (*.bin)|*.bin", style=wx.FLP_OPEN|wx.FLP_FILE_MUST_EXIST|wx.FLP_USE_TEXTCTRL|wx.FLP_SMALL)
		self.fixchecksum = wx.CheckBox(self, label="Fix")
		self.size = wx.Choice(self, choices=["Auto"]+list(binsizes.keys()))
		self.checksum = wx.Choice(self, choices=list(checksums))
		self.gobutton = wx.Button(self, label="Start")

		self.writefpicker.Show(False)
		self.fixchecksum.Show(False)
		self.checksum.Show(False)
		self.wchecksuml.Show(False)
		self.gobutton.Disable()
		self.checksum.Disable()
		self.size.SetSelection(0)

		self.optsbox = wx.BoxSizer(wx.HORIZONTAL)
		self.optsbox.Add(self.wsizel, 0, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.optsbox.Add(self.size, 0)
		self.optsbox.Add(self.wchecksuml, 0, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.optsbox.Add(self.checksum, 0)
		self.optsbox.Add(self.fixchecksum, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)

		self.fpickerbox = wx.BoxSizer(wx.HORIZONTAL)
		self.fpickerbox.Add(self.readfpicker, 1)
		self.fpickerbox.Add(self.writefpicker, 1)

		self.flashpsizer = wx.GridBagSizer(0,0)
		self.flashpsizer.Add(self.mode, pos=(0,0), span=(1,6), flag=wx.ALL|wx.ALIGN_CENTER, border=20)
		self.flashpsizer.Add(self.wfilel, pos=(1,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border=10)
		self.flashpsizer.Add(self.fpickerbox, pos=(1,1), span=(1,5), flag=wx.EXPAND|wx.RIGHT, border=10)
		self.flashpsizer.Add(self.optsbox, pos=(2,0), span=(1,6), flag=wx.TOP, border=5)
		self.flashpsizer.Add(self.gobutton, pos=(4,5), flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.BOTTOM|wx.RIGHT, border=10)
		self.flashpsizer.AddGrowableRow(3,1)
		self.flashpsizer.AddGrowableCol(5,1)
		self.SetSizer(self.flashpsizer)

		self.fixchecksum.Bind(wx.EVT_CHECKBOX, self.OnFix)
		self.mode.Bind(wx.EVT_RADIOBOX, gui.OnModeChange)
		self.gobutton.Bind(wx.EVT_BUTTON, gui.OnGo)

	def OnFix(self, event):
		if self.fixchecksum.IsChecked():
			self.checksum.Enable()
		else:
			self.checksum.Disable()

	def setEmergency(self, emergency):
		if emergency:
			self.mode.EnableItem(0, False)
			self.mode.EnableItem(1, False)
			self.mode.EnableItem(2, True)
			self.mode.SetSelection(2)
		else:
			self.mode.EnableItem(0, True)
			self.mode.EnableItem(1, True)
			self.mode.EnableItem(2, True)

class FlashDialog(wx.Dialog):

	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, size=(300,250))
		self.parent = parent

		self.offimg = wx.Image(self.parent.offpng, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		self.onimg = wx.Image(self.parent.onpng, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		self.goodimg = wx.Image(self.parent.goodpng, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		self.badimg = wx.Image(self.parent.badpng, wx.BITMAP_TYPE_ANY).ConvertToBitmap()

		self.msg = wx.StaticText(self, label="", style=wx.ALIGN_CENTRE)
		self.msg2 = wx.StaticText(self, label="", style=wx.ALIGN_CENTRE)
		self.image = wx.StaticBitmap(self)
		self.progress = wx.Gauge(self)
		self.progress.SetRange(100)
		self.progress.SetValue(0)
		self.button = wx.Button(self, label="Close")
		self.button.Show(False)

		mainbox = wx.BoxSizer(wx.VERTICAL)
		mainbox.Add(self.msg, 0, wx.ALIGN_CENTER|wx.TOP, 30)
		mainbox.Add(self.image, 0, wx.ALIGN_CENTER|wx.TOP, 10)
		mainbox.Add(self.progress, 0, wx.EXPAND|wx.ALL, 40)
		mainbox.Add(self.msg2, 0, wx.ALIGN_CENTER, 0)
		mainbox.Add(self.button, 0, wx.ALIGN_CENTER, 0)
		self.SetSizer(mainbox)

		self.Layout()
		self.Center()

		self.button.Bind(wx.EVT_BUTTON, self.OnButton)

	def OnButton(self, event):
		self.EndModal(1)

	def WaitOff(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Turn off ECU")
		self.msg2.SetLabel("")
		self.image.SetBitmap(self.offimg)
		self.image.Show(True)
		self.progress.Show(False)
		self.button.Show(False)
		self.Layout()

	def WaitOn(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Turn on ECU")
		self.msg2.SetLabel("")
		self.image.SetBitmap(self.onimg)
		self.image.Show(True)
		self.progress.Show(False)
		self.button.Show(False)
		self.Layout()

	def WaitRead(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Reading ECU")
		self.msg2.SetLabel("")
		self.image.SetBitmap(wx.NullBitmap)
		self.image.Show(False)
		self.progress.Show(True)
		self.button.Show(False)
		self.Layout()

	def WaitWrite(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Writing ECU")
		self.msg2.SetLabel("")
		self.image.SetBitmap(wx.NullBitmap)
		self.image.Show(False)
		self.progress.Show(True)
		self.button.Show(False)
		self.Layout()

	def WaitRecover(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Recovering ECU")
		self.msg2.SetLabel("")
		self.image.SetBitmap(wx.NullBitmap)
		self.image.Show(False)
		self.progress.Show(True)
		self.button.Show(False)
		self.Layout()

	def WaitReadGood(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Read Successful")
		self.msg2.SetLabel("")
		self.image.SetBitmap(self.goodimg)
		self.image.Show(True)
		self.progress.Show(False)
		self.button.Show(True)
		self.Layout()

	def WaitReadBad(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Read Unsuccessful")
		self.msg2.SetLabel("")
		self.image.SetBitmap(self.badimg)
		self.image.Show(True)
		self.progress.Show(False)
		self.button.Show(True)
		self.Layout()

	def WaitWriteGood(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Write Successful")
		self.msg2.SetLabel("")
		self.image.SetBitmap(self.goodimg)
		self.image.Show(True)
		self.progress.Show(False)
		self.button.Show(True)
		self.Layout()

	def WaitWriteBad(self):
		self.progress.SetValue(0)
		self.msg.SetLabel("Write Unsuccessful")
		self.msg2.SetLabel("")
		self.image.SetBitmap(self.badimg)
		self.image.Show(True)
		self.progress.Show(False)
		self.button.Show(True)
		self.Layout()

class HondaECU_GUI(wx.Frame):

	def TimerActions(self, event):
		if not self.usbhotplug:
			try:
				new_devices = self.usbcontext.getDeviceList(skip_on_error=True)
				for device in new_devices:
					if device.getVendorID() == pylibftdi.driver.FTDI_VENDOR_ID:
						if device.getProductID() in pylibftdi.driver.USB_PID_LIST:
							if not device in self.ftdi_devices:
								if self.args.debug:
									sys.stderr.write("Adding device (%s) to list\n" % device)
								self.ftdi_devices.append(device)
								self.UpdateDeviceList()
				for device in self.ftdi_devices:
					if not device in new_devices:
						if device == self.ftdi_active:
							self.deactivateDevice()
							self.infop.ecmid.SetLabel("")
							self.infop.status.SetLabel("")
							self.infop.flashcount.SetLabel("")
							self.infop.Layout()
						self.ftdi_devices.remove(device)
						self.UpdateDeviceList()
						if self.args.debug:
							sys.stderr.write("Removing device (%s) from list\n" % device)
			except OSError:
				pass
		if self.device_state == DEVICE_STATE_CONNECTED:
			if self.ecu.kline():
				if len(self.idle_actions[self.notebook.GetSelection()]) > 0:
					self.idle_actions[self.notebook.GetSelection()][self.device_state_index]()
					self.device_state_index = (self.device_state_index + 1) % len(self.idle_actions[self.notebook.GetSelection()])
			else:
				self.device_state = DEVICE_STATE_ERROR
		elif self.device_state == DEVICE_STATE_POST_READ:
			pass
		elif self.device_state == DEVICE_STATE_POST_WRITE:
			if not self.ecu.kline():
				self.device_state = DEVICE_STATE_ERROR

	def hotplug_callback(self, context, device, event):
		if device.getProductID() in pylibftdi.driver.USB_PID_LIST:
			if event == usb1.HOTPLUG_EVENT_DEVICE_ARRIVED:
				if not device in self.ftdi_devices:
					if self.args.debug:
						sys.stderr.write("Adding device (%s) to list\n" % device)
					self.ftdi_devices.append(device)
					self.UpdateDeviceList()
			elif event == usb1.HOTPLUG_EVENT_DEVICE_LEFT:
				if device in self.ftdi_devices:
					if device == self.ftdi_active:
						self.deactivateDevice()
					self.ftdi_devices.remove(device)
					self.UpdateDeviceList()
					if self.args.debug:
						sys.stderr.write("Removing device (%s) from list\n" % device)

	def deactivateDevice(self):
		if self.ecu != None:
			self.ecu.dev.close()
			del self.ecu
			self.ecu = None
		if self.args.debug:
			sys.stderr.write("Deactivating device (%s)\n" % self.ftdi_active)
		self.ftdi_active = None
		self.flashp.gobutton.Disable()
		self.infop.ecmid.SetLabel("")
		self.infop.status.SetLabel("")
		self.infop.flashcount.SetLabel("")
		self.infop.Layout()

	def initRead(self, rom_size):
		self.maxbyte = 1024 * rom_size
		if self.maxbyte < 0:
			self.maxbyte = math.inf
		self.nbyte = 0
		self.readsize = 8

	def initWrite(self):
		self.i = 0
		self.maxb = len(self.byts)
		self.maxi = self.maxb/128
		self.writesize = 128

	def __init__(self, args, version):
		title = "HondaECU %s" % (version)
		if args.debug:
			sys.stderr.write(title)
			sys.stderr.write("\n-------------------------\n")
		self.args = args
		self.state_delay = time.time()
		self.ecu = None
		self.device_state = DEVICE_STATE_SETUP
		self.device_state_index = 0
		self.ftdi_devices = []
		self.ftdi_active = None
		self.file = None
		self.usbcontext = usb1.USBContext()
		self.usbhotplug = self.usbcontext.hasCapability(usb1.CAP_HAS_HOTPLUG)
		self.flashop = False

		wx.Frame.__init__(self, None, title=title)
		self.SetMinSize(wx.Size(700,550))

		self.statusbar = self.CreateStatusBar(1)

		if getattr(sys, 'frozen', False ):
			self.basepath = sys._MEIPASS
		else:
			self.basepath = os.path.dirname(os.path.realpath(__file__))
		ip = os.path.join(self.basepath,"honda.ico")
		self.offpng = os.path.join(self.basepath, "power_off.png")
		self.onpng = os.path.join(self.basepath, "power_on.png")
		self.goodpng = os.path.join(self.basepath, "flash_good.png")
		self.badpng = os.path.join(self.basepath, "flash_bad.png")

		ib = wx.IconBundle()
		ib.AddIcon(ip)
		self.SetIcons(ib)

		menuBar = wx.MenuBar()
		menu = wx.Menu()
		m_exit = menu.Append(wx.ID_EXIT, "E&xit\tAlt-X", "Close window and exit program.")
		self.Bind(wx.EVT_MENU, self.OnClose, m_exit)
		menuBar.Append(menu, "&File")
		self.SetMenuBar(menuBar)

		self.panel = wx.Panel(self)

		devicebox = wx.StaticBoxSizer(wx.HORIZONTAL, self.panel, "FTDI Devices")
		self.m_devices = wx.Choice(self.panel, wx.ID_ANY)
		devicebox.Add(self.m_devices, 1, wx.EXPAND | wx.ALL, 5)

		self.notebook = wx.Notebook(self.panel, wx.ID_ANY)

		self.infop = InfoPanel(self)
		self.flashp = FlashPanel(self)
		self.datap = DataPanel(self)
		self.errorp = ErrorPanel(self)

		self.notebook.AddPage(self.infop, "ECU Info")
		self.notebook.AddPage(self.flashp, "Flash Operations")
		self.notebook.AddPage(self.datap, "Diagnostic Tables")
		self.notebook.AddPage(self.errorp, "Error Codes")

		self.faults = {'past':[], 'current':[], 'past_new':[], 'current_new':[]}

		self.idle_actions = [
			[
				self.Get_Info
			],
			[
				self.ValidateModes
			],
			[],
			[
				self.Get_Current_Faults,
				self.Get_Past_Faults,
				self.Update_Error_list
			]
		]

		self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)

		mainbox = wx.BoxSizer(wx.VERTICAL)
		mainbox.Add(devicebox, 0, wx.EXPAND | wx.ALL, 10)
		mainbox.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 10)
		self.notebook.Layout()
		self.panel.SetSizer(mainbox)
		self.panel.Layout()
		self.Centre()

		self.Show()

		self.Bind(wx.EVT_IDLE, self.OnIdle)
		self.m_devices.Bind(wx.EVT_CHOICE, self.OnDeviceSelected)
		self.Bind(wx.EVT_CLOSE, self.OnClose)

		self.flashdlg = FlashDialog(self)

		if self.usbhotplug:
			if self.args.debug:
				sys.stderr.write('Registering hotplug callback...\n')
			self.usbcontext.hotplugRegisterCallback(self.hotplug_callback, vendor_id=pylibftdi.driver.FTDI_VENDOR_ID)
			if self.args.debug:
				sys.stderr.write('Callback registered. Monitoring events.\n')

		self.idletimer = wx.Timer(self, wx.ID_ANY)
		self.Bind(wx.EVT_TIMER, self.TimerActions)
		self.idletimer.Start(250)

	def Get_Info(self):
		if not self.emergency:
			info = self.ecu.send_command([0x72],[0x72, 0x00, 0x00, 0x05], debug=self.args.debug, retries=0)
			if info:
				self.infop.ecmid.SetLabel("%s" % " ".join(["%02x" % b for b in info[2][3:]]))
			info = self.ecu.send_command([0x7d], [0x01, 0x01, 0x03], debug=self.args.debug, retries=0)
			if info:
				self.infop.status.SetLabel("dirty" if info[2][2] == 0xff else "clean")
				self.infop.flashcount.SetLabel(str(int(info[2][4])))
			self.infop.Layout()

	def _get_faults(self, type, debug):
		faults = []
		for i in range(1,0x0c):
			info_current = self.ecu.send_command([0x72],[type, i], debug=debug)[2]
			for j in [3,5,7]:
				if info_current[j] != 0:
					faults.append("%02d-%02d" % (info_current[j],info_current[j+1]))
			if info_current[2] == 0:
				break
		return sorted(faults)

	def Get_Current_Faults(self):
		if not self.emergency:
			self.faults["current_new"] = self._get_faults(0x74, debug=self.args.debug)

	def Get_Past_Faults(self):
		if not self.emergency:
			self.faults["past_new"] = self._get_faults(0x73, debug=self.args.debug)

	def Update_Error_list(self):
		if self.faults["current"] != self.faults["current_new"] or self.faults["past"] != self.faults["past_new"]:
			self.errorp.errorlist.DeleteAllItems()
			faultcount = 0
			for code in self.faults["current_new"]:
				self.errorp.errorlist.Append([code, DTC[code] if code in DTC else "Unknown", "current"])
				faultcount += 1
			for code in self.faults["past_new"]:
				self.errorp.errorlist.Append([code, DTC[code] if code in DTC else "Unknown", "past"])
				faultcount += 1
			self.errorp.resetbutton.Enable(faultcount > 0)
			self.errorp.Layout()
			self.faults["current"] = self.faults["current_new"]
			self.faults["past"] = self.faults["past_new"]

	def OnPageChanged(self, event):
		self.device_state_index = 0
		event.Skip()

	def OnClearCodes(self, event):
		self.errorp.resetbutton.Enable(False)
		if self.args.debug:
			sys.stderr.write('Clearing codes\n')
		self.statusbar.SetStatusText("Clearing diagnostic trouble codes...")
		self.device_state = DEVICE_STATE_CLEAR_CODES

	def OnGo(self, event):
		self.device_state = DEVICE_STATE_POWER_OFF
		self.flashop = True
		self.flashdlg.WaitOff()
		self.flashdlg.ShowModal()
		self.flashop = False

	def OnModeChange(self, event):
		if self.flashp.mode.GetSelection() == 0:
			self.flashp.fixchecksum.Show(False)
			self.flashp.writefpicker.Show(False)
			self.flashp.readfpicker.Show(True)
			self.flashp.wchecksuml.Show(False)
			self.flashp.checksum.Show(False)
			self.flashp.wsizel.Show(True)
			self.flashp.size.Show(True)
		else:
			self.flashp.wchecksuml.Show(True)
			self.flashp.checksum.Show(True)
			self.flashp.fixchecksum.Show(True)
			self.flashp.writefpicker.Show(True)
			self.flashp.readfpicker.Show(False)
			self.flashp.wsizel.Show(False)
			self.flashp.size.Show(False)
		self.flashp.Layout()

	def OnDeviceSelected(self, event):
		self.statusbar.SetStatusText("")
		newdevice = self.ftdi_devices[self.m_devices.GetSelection()]
		if self.ftdi_active != None:
			if self.ftdi_active != newdevice:
				self.deactivateDevice()
		self.ftdi_active = newdevice
		try:
			self.device_state = DEVICE_STATE_ERROR
			self.statusbar.SetStatusText("")
			self.ecu = HondaECU(device_id=self.ftdi_active.getSerialNumber())
			if self.args.debug:
				sys.stderr.write("Activating device (%s)\n" % self.ftdi_active)
			self.device_state = DEVICE_STATE_INIT_A
		except usb1.USBErrorNotSupported as e:
			self.ecu = None
			self.statusbar.SetStatusText("Incorrect driver for device, install libusbK with Zadig!")
		except usb1.USBErrorBusy:
			self.ecu = None

	def UpdateDeviceList(self):
		self.m_devices.Clear()
		for i,d in enumerate(self.ftdi_devices):
			n = str(d)
			try:
				s = d.getSerialNumber()
				if s == None:
					pass
				n += " | " + s
			except usb1.USBErrorNotSupported:
				pass
			except usb1.USBErrorBusy:
				pass
			except usb1.USBErrorNoDevice:
				continue
			except usb1.USBErrorIO:
				continue
			except usb1.USBErrorPipe:
				continue
			self.m_devices.Append(n)
			if self.ftdi_active == d:
				self.m_devices.SetSelection(i)
			if self.ftdi_active == None:
				self.ftdi_active = self.ftdi_devices[0]
				self.m_devices.SetSelection(0)
				self.OnDeviceSelected(None)

	def OnClose(self, event):
		for d in self.ftdi_devices:
			d.close()
		for w in wx.GetTopLevelWindows():
			w.Destroy()

	def startErase(self):
		self.write_wait = time.time()
		self.device_state = DEVICE_STATE_ERASE
		self.flashdlg.msg2.SetLabel("Waiting")
		self.flashdlg.progress.SetRange(12)
		self.flashdlg.progress.SetValue(12)
		self.flashdlg.Layout()
		if self.args.debug:
			sys.stderr.write("Waiting\n")

	def ValidateModes(self):
		go = False
		if self.flashp.mode.GetSelection() == 0:
			if len(self.flashp.readfpicker.GetPath()) > 0:
				go = True
		else:
			if len(self.flashp.writefpicker.GetPath()) > 0:
				if os.path.isfile(self.flashp.writefpicker.GetPath()):
					if self.flashp.fixchecksum.IsChecked():
						if self.flashp.checksum.GetSelection() > -1:
							go = True
					else:
						go = True
				if go:
					fbin = open(self.flashp.writefpicker.GetPath(), "rb")
					nbyts = os.path.getsize(self.flashp.writefpicker.GetPath())
					self.byts = bytearray(fbin.read(nbyts))
					fbin.close()
					cksum = None
					if self.flashp.fixchecksum.IsChecked():
						if self.flashp.checksum.GetSelection() > -1 and int(checksums[self.flashp.checksum.GetSelection()],16) < nbyts:
							 cksum = int(checksums[self.flashp.checksum.GetSelection()],16)
						else:
							go = False
					else:
						cksum = nbyts - 8
					if go:
						self.byts, status = do_validation(self.byts, cksum, self.flashp.fixchecksum.IsChecked())
						go = (status != "bad")
		if go:
			self.flashp.gobutton.Enable()
		else:
			self.flashp.gobutton.Disable()

	def SetEmergency(self, emergency):
		self.emergency = emergency
		self.flashp.setEmergency(self.emergency)
		self.OnModeChange(None)

	def OnIdle(self, event):
		#print(self.device_state)
		if self.usbhotplug:
			self.usbcontext.handleEventsTimeout(0)
		try:
			if self.device_state == DEVICE_STATE_ERROR:
				if self.ecu.kline():
					self.device_state = DEVICE_STATE_INIT_A
					self.state_delay = time.time()
				else:
					self.statusbar.SetStatusText("Turn on ECU!")
			elif self.device_state == DEVICE_STATE_INIT_A and time.time() > self.state_delay+.5:
				self.SetEmergency(False)
				if self.ecu.kline():
					self.ecu._break(.070)
					self.device_state = DEVICE_STATE_INIT_B
					self.state_delay = time.time()
				else:
					self.device_state = DEVICE_STATE_ERROR
			elif self.device_state == DEVICE_STATE_INIT_B and time.time() > self.state_delay+.130:
				info = self.ecu.send_command([0xfe],[0x72], debug=self.args.debug, retries=0)
				if info and info[2][0] == 0x72:
					self.ecu.send_command([0x72],[0x00, 0xf0], debug=self.args.debug)
					self.statusbar.SetStatusText("ECU connected!")
					if self.flashop:
						if self.flashp.mode.GetSelection() == 0:
							self.device_state = DEVICE_STATE_READ_SECURITY
							self.flashdlg.WaitRead()
						elif self.flashp.mode.GetSelection() == 1:
							self.device_state = DEVICE_STATE_WRITE_INIT
							self.flashdlg.WaitWrite()
						elif self.flashp.mode.GetSelection() == 2:
							self.write_wait = time.time()
							self.device_state = DEVICE_STATE_RECOVER_INIT
							self.flashdlg.WaitWrite()
					else:
						self.device_state = DEVICE_STATE_CONNECTED
					self.state_delay = time.time()
				else:
					self.device_state = DEVICE_STATE_UNKNOWN
			elif self.device_state == DEVICE_STATE_UNKNOWN:
				if self.ecu.send_command([0x7e], [0x01, 0x02], debug=self.args.debug, retries=0) != None:
					self.statusbar.SetStatusText("ECU connected (emergency)!")
					self.SetEmergency(True)
					self.device_state = DEVICE_STATE_CONNECTED
				else:
					self.device_state = DEVICE_STATE_ERROR
			elif self.device_state == DEVICE_STATE_CLEAR_CODES:
				self.errorp.errorlist.DeleteAllItems()
				self.errorp.Layout()
				info = self.ecu.send_command([0x72],[0x60, 0x03], debug=self.args.debug, retries=0)
				if info and info[2][1] == 0x00:
					self.statusbar.SetStatusText("ECU connected!")
					self.device_state = DEVICE_STATE_CONNECTED
			elif self.device_state == DEVICE_STATE_POWER_OFF:
				if not self.ecu.kline():
					self.device_state = DEVICE_STATE_POWER_ON
					self.flashdlg.WaitOn()
			elif self.device_state == DEVICE_STATE_POWER_ON:
				if self.ecu.kline():
					if self.emergency:
						self.flashdlg.WaitRecover()
						self.startErase()
					else:
						self.device_state = DEVICE_STATE_INIT_A
					self.state_delay = time.time()
			elif self.device_state == DEVICE_STATE_READ_SECURITY:
				if self.args.debug:
					sys.stderr.write("Security access\n")
				self.ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f], debug=self.args.debug)
				self.ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75], debug=self.args.debug)
				if self.flashp.size.GetSelection() == 0:
					maxbyte = -1
				else:
					maxbyte = list(binsizes.values())[self.flashp.size.GetSelection()-1]
				self.initRead(maxbyte)
				self.file = open(self.flashp.readfpicker.GetPath(), "wb")
				if self.args.debug:
					sys.stderr.write("Reading ECU\n")
				self.device_state = DEVICE_STATE_READ
			elif self.device_state == DEVICE_STATE_READ:
				if self.nbyte < self.maxbyte:
					info = self.ecu.send_command([0x82, 0x82, 0x00], [int(self.nbyte/65536)] + [b for b in struct.pack("<H", self.nbyte % 65536)] + [self.readsize], debug=self.args.debug)
					if info != None:
						self.file.write(info[2])
						self.file.flush()
						self.nbyte += self.readsize
						if self.maxbyte!=math.inf:
							self.flashdlg.progress.SetValue(int(100*self.nbyte/self.maxbyte))
							self.flashdlg.msg2.SetLabel("%dB of %dB" % (self.nbyte, self.maxbyte))
						else:
							self.flashdlg.progress.SetValue(100)
							self.flashdlg.msg2.SetLabel("%dB" % (self.nbyte))
						self.flashdlg.Layout()
					else:
						self.flashdlg.WaitReadBad()
						self.device_state = DEVICE_STATE_ERROR
						self.statusbar.SetStatusText("")
				else:
					self.device_state = DEVICE_STATE_POST_READ
					self.statusbar.SetStatusText("Read complete, power-cycle ECU!")
					self.file.close()
					self.flashdlg.WaitReadGood()
			elif self.device_state == DEVICE_STATE_RECOVER_INIT:
				if self.args.debug:
					sys.stdout.write("Initializing recovery process\n")
				self.ecu.do_init_recover(debug=self.args.debug)
				if self.args.debug:
					sys.stdout.write("Entering enhanced diagnostic mode\n")
				self.ecu.send_command([0x72],[0x00, 0xf1], debug=self.args.debug)
				self.ecu.send_command([0x27],[0x00, 0x9f, 0x00], debug=self.args.debug)
				self.startErase()
			elif self.device_state == DEVICE_STATE_WRITE_INIT:
				if self.args.debug:
					sys.stderr.write("Initializing write process\n")
				try:
					self.ecu.do_init_write(debug=self.args.debug)
					self.startErase()
				except MaxRetriesException:
					if self.initok:
						if self.args.debug:
							sys.stderr.write("Switching to recovery mode\n")
						self.device_state = DEVICE_STATE_RECOVER_INIT
					else:
						self.startErase()
			elif self.device_state == DEVICE_STATE_ERASE:
				if time.time() > self.write_wait+12:
					self.eraseinc = 0
					self.flashdlg.msg2.SetLabel("Erasing ECU")
					self.flashdlg.progress.SetRange(180)
					self.flashdlg.progress.SetValue(0)
					self.flashdlg.Layout()
					if self.args.debug:
						sys.stderr.write("Erasing ECU\n")
					self.ecu.do_erase()
					self.device_state = DEVICE_STATE_ERASE_WAIT
				else:
					self.flashdlg.progress.SetValue(int(12-round(time.time()-self.write_wait)))
			elif self.device_state == DEVICE_STATE_ERASE_WAIT:
				info = self.ecu.send_command([0x7e], [0x01, 0x05], debug=self.args.debug)
				if info[2][1] == 0x00:
					self.ecu.send_command([0x7e], [0x01, 0x01, 0x00], debug=self.args.debug)
					self.initWrite()
					if self.args.debug:
						sys.stderr.write("Writing ECU\n")
					self.device_state = DEVICE_STATE_WRITE
					self.flashdlg.progress.SetRange(100)
					self.flashdlg.progress.SetValue(0)
					self.flashdlg.msg2.SetLabel("")
					self.flashdlg.Layout()
				else:
					self.eraseinc += 1
					if self.eraseinc > 180:
						self.eraseinc = 180
					self.flashdlg.progress.SetValue(self.eraseinc)
			elif self.device_state == DEVICE_STATE_WRITE:
				if self.i < self.maxi:
					bytstart = [s for s in struct.pack(">H",(8*self.i))]
					if self.i+1 == self.maxi:
						bytend = [s for s in struct.pack(">H",0)]
					else:
						bytend = [s for s in struct.pack(">H",(8*(self.i+1)))]
					d = list(self.byts[((self.i+0)*128):((self.i+1)*128)])
					x = bytstart + d + bytend
					c1 = checksum8bit(x)
					c2 = checksum8bitHonda(x)
					x = [0x01, 0x06] + x + [c1, c2]
					info = self.ecu.send_command([0x7e], x, debug=self.args.debug)
					if info:
						if ord(info[1]) != 5:
							info = None
						else:
							self.i += 1
							if self.i % 2 == 0:
								info = self.ecu.send_command([0x7e], [0x01, 0x08], debug=self.args.debug)
							self.flashdlg.progress.SetValue(int(100*self.i/self.maxi))
							self.flashdlg.msg2.SetLabel("%dB of %dB" % (self.i*128, self.maxb))
							self.flashdlg.Layout()
					if not info:
						self.flashdlg.WaitWriteBad()
						self.device_state = DEVICE_STATE_ERROR
						self.statusbar.SetStatusText("")
				else:
					self.device_state = DEVICE_STATE_WRITE_FINALIZE
			elif self.device_state == DEVICE_STATE_WRITE_FINALIZE:
				if self.args.debug:
					sys.stderr.write("Finalizing write process\n")
				self.ecu.do_post_write(debug=self.args.debug)
				self.device_state = DEVICE_STATE_POST_WRITE
				self.statusbar.SetStatusText("Write successful, power-cycle ECU!")
				self.flashdlg.WaitWriteGood()
		except pylibftdi._base.FtdiError:
			self.device_state = DEVICE_STATE_ERROR
			self.statusbar.SetStatusText("")
		except usb1.USBErrorPipe:
			self.device_state = DEVICE_STATE_ERROR
			self.statusbar.SetStatusText("")
		event.RequestMore()
