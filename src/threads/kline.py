import time
import wx
from threading import Thread
from pydispatch import dispatcher
from pylibftdi import Driver, FtdiError, LibraryMissingError
import numpy as np

from ecu import *

class KlineWorker(Thread):

	def __init__(self, parent):
		self.parent = parent
		self.__clear_data()
		dispatcher.connect(self.DeviceHandler, signal="FTDIDevice", sender=dispatcher.Any)
		dispatcher.connect(self.ErrorPanelHandler, signal="ErrorPanel", sender=dispatcher.Any)
		dispatcher.connect(self.DatalogPanelHandler, signal="DatalogPanel", sender=dispatcher.Any)
		dispatcher.connect(self.ReadPanelHandler, signal="ReadPanel", sender=dispatcher.Any)
		dispatcher.connect(self.WritePanelHandler, signal="WritePanel", sender=dispatcher.Any)
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
		self.sendwriteinit = False
		self.sendrecoverinint = False
		self.senderase = False
		self.readinfo = None
		self.writeinfo = None
		self.state = ECUSTATE.UNKNOWN
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

	def WritePanelHandler(self, data, offset):
		self.writeinfo = [data,offset,None]
		if self.state in [ECUSTATE.OK, ECUSTATE.RECOVER_OLD]:
			self.sendwriteinit = True
		elif self.state == ECUSTATE.RECOVER_NEW:
			self.sendrecoverinint = True
		elif self.state in [ECUSTATE.ERASE, ECUSTATE.WRITE_UNKNOWN1]:
			self.senderase = True
		else:
			raise Exception("Unhandled ECU state in WritePanelHandler()")

	def ReadPanelHandler(self, data, offset):
		if self.state != ECUSTATE.READ:
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
		state = self.ecu.detect_ecu_state_new()
		if state != self.state:
			self.state = state
			wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="state", value=self.state)

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

	def do_write_flash(self, byts, offset=0):
		writesize = 128
		ossize = len(byts)
		maxi = int(ossize/writesize)
		offseti = int(offset/16)
		i = 0
		w = 0
		t = time.time()
		rate = 0
		size = 0
		done = False
		while not self.writeinfo is None and i < maxi and not done:
			w = (i*writesize)
			bytstart = [s for s in struct.pack(">H",offseti+(8*i))]
			if i+1 == maxi:
				bytend = [s for s in struct.pack(">H",0)]
			else:
				bytend = [s for s in struct.pack(">H",offseti+(8*(i+1)))]
			d = list(byts[((i+0)*writesize):((i+1)*writesize)])
			x = bytstart + d + bytend
			c1 = checksum8bit(x)
			c2 = checksum8bitHonda(x)
			x = [0x01, 0x06] + x + [c1, c2]
			info = self.ecu.send_command([0x7e], x)
			if not info or ord(info[1]) != 5:
				return False
			if info[2][1] == 0:
				done = True
			n = time.time()
			wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="progress", value=(i/maxi*100,"%.02fKB of %.02fKB @ %s" % (w/1024.0, ossize/1024.0, "%.02fB/s" % (rate) if rate > 0 else "---")))
			if n-t > 1:
				rate = (w-size)/(n-t)
				t = n
				size = w
			i += 1
		info = self.ecu.send_command([0x7e], [0x01, 0x08])
		if not info is None:
			ret = info[2][1] == 0x0
		else:
			ret = False
		wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="progress", value=(i/maxi*100,"%.02fKB of %.02fKB @ %s" % ((w-offset)/1024.0, ossize/1024.0, "%.02fB/s" % (rate) if rate > 0 else "---")))
		return ret

	def do_unknown(self):
		self.reset_state()
		time.sleep(.250)
		self.update_state()

	def run(self):
		while self.parent.run:
			if not self.ready:
				time.sleep(.001)
			else:
				try:
					if self.state == ECUSTATE.UNKNOWN:
						self.do_unknown()
						if self.state == ECUSTATE.OK and self.sendpassword:
							p1 = self.ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f])
							p2 = self.ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75])
							passok = (p1 != None) and (p2 != None)
							wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="password", value=passok)
							self.sendpassword = False
					elif self.state == ECUSTATE.READ:
						if not self.readinfo is None and self.readinfo[2] == None:
							self.readinfo[2] = self.do_read_flash()
							wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="read.result", value=self.readinfo[2])
						else:
							self.do_unknown()
					elif self.state in [ECUSTATE.WRITE_INIT_OLD, ECUSTATE.WRITE_INIT_NEW, ECUSTATE.WRITE_UNKNOWN1] or (self.senderase and self.state == ECUSTATE.ERASE):
						if self.senderase and not self.writeinfo is None and self.writeinfo[2] == None:
							wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="erase", value=None)
							if self.state in [ECUSTATE.WRITE_INIT_OLD, ECUSTATE.WRITE_INIT_NEW, ECUSTATE.WRITE_UNKNOWN1]:
								for i in range(14):
									w = 14-i
									wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="progress", value=(w/14*100, "waiting for %d seconds" % (w)))
									time.sleep(1)
								wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="progress", value=(0, "waiting for %d seconds" % (w)))
							cont = 1
							e = 0
							wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="progress", value=(np.clip(e/160*100,0,100), "erasing ecu"))
							self.ecu.do_erase()
							while cont:
								wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="progress", value=(np.clip(e/160*100,0,100), "erasing ecu"))
								e += 1
								info = self.ecu.send_command([0x7e], [0x01, 0x05])
								if info:
									if info[2][1] == 0x00:
										cont = 0
								else:
									cont = -1
									raise Exception("Unhandled ECU state in WritePanelHandler()")
							if cont == 0:
								into = self.ecu.send_command([0x7e], [0x01, 0x01, 0x00])
								self.senderase = False
							self.update_state()
						else:
							self.do_unknown()
					elif self.state == ECUSTATE.ERASE:
						if not self.senderase and not self.writeinfo is None and self.writeinfo[2] == None:
							wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="write", value=None)
							if self.do_write_flash(self.writeinfo[0], offset=self.writeinfo[1]):
								 self.writeinfo[2] = "good" if self.ecu.do_post_write() else "bad"
								 wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="write.result", value=self.writeinfo[2])
							self.update_state()
						else:
							self.do_unknown()
					else:
						if self.ecu.ping():
							if not self.writeinfo is None and self.writeinfo[2] == None:
								if self.sendwriteinit:
									wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="init.write", value=None)
									self.ecu.do_init_write()
									self.sendwriteinit = False
									self.senderase = True
								elif self.sendrecoverinint:
									wx.CallAfter(dispatcher.send, signal="KlineWorker", sender=self, info="init.recover", value=None)
									self.ecu.do_init_recover()
									self.ecu.send_command([0x72],[0x00, 0xf1])
									time.sleep(1)
									self.ecu.send_command([0x27],[0x00, 0x01, 0x00])
									self.sendrecoverinint = False
									self.senderase = True
							else:
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
							self.state = ECUSTATE.UNKNOWN
				except FtdiError:
					pass
				except AttributeError:
					pass
				except OSError:
					pass
