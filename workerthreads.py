import time
import wx
from threading import Thread
from pydispatch import dispatcher
from pylibftdi import Driver, FtdiError, LibraryMissingError

from ecu import *

class USBMonitor(Thread):

	def __init__(self, parent):
		self.parent = parent
		self.ftdi_devices = {}
		Thread.__init__(self)

	def run(self):
		while self.parent.run:
			time.sleep(.5)
			new_devices = {}
			try:
				for device in Driver().list_devices():
					vendor, product, serial = map(lambda x: x.decode('latin1'), device)
					new_devices[serial] = (vendor, product)
					if not serial in self.ftdi_devices:
						wx.CallAfter(dispatcher.send, signal="USBMonitor", sender=self, action="add", vendor=vendor, product=product, serial=serial)
				for serial in self.ftdi_devices:
					if not serial in new_devices:
						wx.CallAfter(dispatcher.send, signal="USBMonitor", sender=self, action="remove", vendor=self.ftdi_devices[serial][0], product=self.ftdi_devices[serial][1], serial=serial)
			except FtdiError as e:
				if sys.exc_info()[0] == LibraryMissingError:
					wx.LogError(str(e))
					break
			except LibraryMissingError as e:
				wx.LogError(str(e))
				break
			self.ftdi_devices = new_devices

class KlineWorker(Thread):

	def __init__(self, parent):
		self.parent = parent
		self.__clear_data()
		dispatcher.connect(self.DeviceHandler, signal="FTDIDevice", sender=dispatcher.Any)
		dispatcher.connect(self.ErrorPanelHandler, signal="ErrorPanel", sender=dispatcher.Any)
		dispatcher.connect(self.DatalogPanelHandler, signal="DatalogPanel", sender=dispatcher.Any)
		dispatcher.connect(self.ReadPanelHandler, signal="ReadPanel", sender=dispatcher.Any)
		Thread.__init__(self)

	def __cleanup(self):
		if self.ecu:
			self.ecu.dev.close()
			del self.ecu
		self.__clear_data()

	def __clear_data(self):
		self.ecu = None
		self.ready = False
		self.sendpassword = False
		self.readinfo = None
		self.state = 0
		self.reset_state()

	def reset_state(self):
		self.ecmid = bytearray()
		self.errorcodes = {}
		self.update_errors = False
		self.clear_codes = False
		self.flashcount = -1
		self.dtccount = -1
		self.update_tables = False
		self.tables = None
		wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="ecmid", value=bytes(self.ecmid))
		wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="flashcount", value=self.flashcount)

	def ReadPanelHandler(self, data, offset):
		if self.state != 7:
			self.sendpassword = True
		self.readinfo = [data,offset,None]

	def DatalogPanelHandler(self, action):
		if action == "data.on":
			self.update_tables = True
		elif action == "data.off":
			self.update_tables = False

	def ErrorPanelHandler(self, action):
		if action == "dtc.clear":
			self.clear_codes = True
		elif action == "dtc.on":
			self.update_errors = True
		elif action == "dtc.off":
			self.update_errors = False

	def update_state(self):
		state, status = self.ecu.detect_ecu_state_new()
		if state != self.state:
			self.state = state
			wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="state", value=(self.state,status))

	def DeviceHandler(self, action, vendor, product, serial):
		if action == "interrupt":
			raise Exception()
		elif action == "deactivate":
			if self.ecu:
				self.__cleanup()
		elif action == "activate":
			self.__clear_data()
			try:
				self.ecu = HondaECU(device_id=serial)
				self.ecu.setup()
				self.ready = True
			except FtdiError:
				pass

	def do_read_flash(self):
		readsize = 12
		location = self.readinfo[1]
		binfile = self.readinfo[0]
		status = "bad"
		with open(binfile, "wb") as fbin:
			t = time.time()
			size = location
			rate = 0
			while not self.readinfo is None:
				info = self.ecu.send_command([0x82, 0x82, 0x00], format_read(location) + [readsize])
				if not info:
					readsize -= 1
					if readsize < 1:
						break
				else:
					fbin.write(info[2])
					fbin.flush()
					location += readsize
					n = time.time()
					wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="progress", value=(-1,"%.02fKB @ %s" % (location/1024.0, "%.02fB/s" % (rate) if rate > 0 else "---")))
					if n-t > 1:
						rate = (location-size)/(n-t)
						t = n
						size = location
			wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="progress", value=(-1,"%.02fKB @ %s" % (location/1024.0, "%.02fB/s" % (rate) if rate > 0 else "---")))
		with open(binfile, "rb") as fbin:
			nbyts = os.path.getsize(binfile)
			if nbyts > 0:
				byts = bytearray(fbin.read(nbyts))
				_, status, _ = do_validation(byts, nbyts)
			return status

	def run(self):
		while self.parent.run:
			if not self.ready:
				time.sleep(.001)
			else:
				try:
					if self.state == 0:
						self.reset_state()
						time.sleep(.250)
						self.update_state()
						if self.state == 1 and self.sendpassword:
							print(self.ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f]))
							print(self.ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75]))
							self.sendpassword = False
					elif self.state == 7:
						if not self.readinfo is None and self.readinfo[2] == None:
							self.readinfo[2] = self.do_read_flash()
							wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="read.result", value=self.readinfo[2])
						else:
							time.sleep(.001)
					else:
						if self.ecu.ping():
							if not self.ecmid:
								info = self.ecu.send_command([0x72], [0x71, 0x00])
								if info:
									self.ecmid = info[2][2:7]
									wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="ecmid", value=bytes(self.ecmid))
							if self.flashcount < 0:
								info = self.ecu.send_command([0x7d], [0x01, 0x01, 0x03])
								if info:
									self.flashcount = int(info[2][4])
									wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="flashcount", value=self.flashcount)
							while self.clear_codes:
								info = self.ecu.send_command([0x72],[0x60, 0x03])
								if info:
									if info[2][1] == 0x00:
										self.dtccount = -1
										self.errorcodes = {}
										self.clear_codes = False
								else:
									self.dtccount = -1
									self.errorcodes = {}
									self.clear_codes = False
							if self.update_errors or self.dtccount < 0:
								errorcodes = {}
								for type in [0x74,0x73]:
									errorcodes[hex(type)] = []
									for i in range(1,0x0c):
										info = self.ecu.send_command([0x72],[type, i])
										if info:
											for j in [3,5,7]:
												if info[2][j] != 0:
													errorcodes[hex(type)].append("%02d-%02d" % (info[2][j],info[2][j+1]))
											if info[2] == 0:
												break
										else:
											break
								dtccount = sum([len(c) for c in errorcodes.values()])
								if self.dtccount != dtccount:
									self.dtccount = dtccount
									wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="dtccount", value=self.dtccount)
								if self.errorcodes != errorcodes:
									self.errorcodes = errorcodes
									wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="dtc", value=self.errorcodes)
							if not self.tables:
								tables = self.ecu.probe_tables()
								if len(tables) > 0:
									self.tables = tables
									tables = " ".join([hex(x) for x in self.tables.keys()])
									# print("HDS tables: %s" % tables)
									for t, d in self.tables.items():
										wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="data", value=(t,d[0],d[1]))
							else:
								if self.update_tables:
									for t in self.tables:
										info = self.ecu.send_command([0x72], [0x71, t])
										if info:
											if info[3] > 2:
												self.tables[t] = [info[3],info[2]]
												wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="data", value=(t,info[3],info[2]))
						else:
							self.state = 0
				except FtdiError:
					pass
				except AttributeError:
					pass
				except OSError:
					pass
