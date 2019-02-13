from __future__ import division
from pylibftdi import Device
from ctypes import *
import struct
import time
import binascii
import sys
import platform
import os
import math
import code
from pydispatch import dispatcher
from enum import Enum

class ECUSTATE(Enum):
	UNKNOWN = -1
	OFF = 0
	READ = 1
	OK = 2
	RECOVER_OLD = 3
	RECOVER_NEW = 4
	WRITE_INIT_OLD = 5
	WRITE_INIT_NEW = 6
	ERASE = 7
	WRITE = 8
	WRITE_GOOD = 9
	WRITE_UNKNOWN1 = 10
	ERROR = 11

ECM_IDs = {
	b"\x01\x00\x2b\x01\x01": {"model":"CBR1000RR","year":"2006-2007","pn":"38770-MEL-D21","checksum":"0x3fff8","ecmidaddr":"0x23381","keihinaddr":"0x3FFDE"},
	b"\x01\x00\x2b\x03\x01": {"model":"CBR1000RR","year":"2006-2007","pn":"38770-MEL-F21","checksum":"0x3fff8","ecmidaddr":"0x23381","keihinaddr":"0x3FFDE"},
	b"\x01\x00\x2b\x04\x01": {"model":"CBR1000RR","year":"2006-2007","pn":"38770-MEL-A21","checksum":"0x3fff8","ecmidaddr":"0x23381","keihinaddr":"0x3FFDE"},
	b"\x01\x00\x2b\x04\x02": {"model":"CBR1000RR","year":"2006-2007","pn":"38770-MEL-A22","checksum":"0x3fff8","ecmidaddr":"0x23381","keihinaddr":"0x3FFDE"},

	b"\x01\x00\x5e\x01\x03": {"model":"CBR1000RR","year":"2008-2011","pn":"38770-MFL-644","checksum":"0x3fff8"},
	b"\x01\x00\x5e\x03\x01": {"model":"CBR1000RR","year":"2008-2011","pn":"38770-MFL-622","checksum":"0x3fff8"},
	b"\x01\x00\x5e\x04\x01": {"model":"CBR1000RR","year":"2008-2011","pn":"38770-MFL-671","checksum":"0x3fff8"},
	b"\x01\x00\x5e\x05\x03": {"model":"CBR1000RR","year":"2008-2011","pn":"38770-MFL-773","checksum":"0x3fff8"},
	b"\x01\x00\xb0\x01\x02": {"model":"CBR1000RR","year":"2008-2011","pn":"38770-MFL-761","checksum":"0x3fff8"},
	b"\x01\x00\xb0\x03\x01": {"model":"CBR1000RR","year":"2008-2011","pn":"38770-MFL-741","checksum":"0x3fff8"},
	b"\x01\x00\xb7\x01\x01": {"model":"CBR1000RR","year":"2008-2011","pn":"38770-MFL-D21","checksum":"0x3fff8"},
	b"\x01\x00\xb7\x03\x01": {"model":"CBR1000RR","year":"2008-2011","pn":"38770-MFL-F21","checksum":"0x3fff8"},
	b"\x01\x00\xb7\x04\x01": {"model":"CBR1000RR","year":"2008-2011","pn":"38770-MFL-A21","checksum":"0x3fff8"},

	b"\x01\x00\xf3\x04\x01": {"model":"CBR1000RR","year":"2012-2013","pn":"38770-MGP-A01","checksum":"0x3fff8"},
	b"\x01\x01\x83\x01\x01": {"model":"CBR1000RR","year":"2014-2016","pn":"38770-MGP-D62","checksum":"0x3fff8"},
	b"\x01\x01\x83\x04\x01": {"model":"CBR1000RR","year":"2014-2016","pn":"38770-MGP-A92","checksum":"0x3fff8"},
	b"\x01\x01\x25\x05\x01": {"model":"CBR500R","year":"2013-2016","pn":"38770-MGZ-A03","checksum":"0x3fff8","ecmidaddr":"0x17FC7","keihinaddr":"0x32D80"},
	b"\x01\x01\x25\x0b\x01": {"model":"CBR500R","year":"2013-2016","pn":"38770-MGZ-C02","checksum":"0x3fff8","ecmidaddr":"0x17FC7","keihinaddr":"0x32D80"},
	b"\x01\x01\x25\x01\x01": {"model":"CBR500R","year":"2013-2016","pn":"38770-MGZ-D02","checksum":"0x3fff8","ecmidaddr":"0x17FC7","keihinaddr":"0x32D80"},
	b"\x01\x02\xf2\x05\x11": {"model":"CBR500R","year":"2017-2018","pn":"38770-MJW-AQ1","checksum":"0x3fff8","ecmidaddr":"0x18BB7","keihinaddr":"0x3FA70"},
	b"\x01\x01\x35\x05\x01": {"model":"MSX125","year":"2014-2016","pn":"38770-K26-911","checksum":"0x9fff","offset":"0x4000","ecmidaddr":"0x97cd","keihinaddr":"0x7601"},
	b"\x01\x02\x13\x05\x01": {"model":"MSX125","year":"2017-2019","pn":"38770-K26-B13","checksum":"0x5fff","offset":"0x8000","ecmidaddr":"0x23B8","keihinaddr":"0x1"},
	b"\x01\x02\x57\x05\x01": {"model":"MSX125","year":"2017-2019","pn":"38770-K26-C31","checksum":"0x5fff","offset":"0x8000","ecmidaddr":"0x260C","keihinaddr":"0x1"},
	# b"\x01\x01\xf2\x01\x01": {"model":"CB500F","year":"2016","pn":"38770-MJW-D51","checksum":"0x3fff8"}
	# b"\x01\x01\x28\x01\x01": {"model":"CB500X","?2013?","?"},
	# b"\x01\x01\xde\x01\x01": {"model":"CB500X","?2016?","?"}
}

def find_compat_bins(base, ecmid):
	bins = {}
	for id in ECM_IDs:
		if id[:3] == ecmid[:3]:
			p = os.path.join(base,ECM_IDs[id]["model"]+"_"+ECM_IDs[id]["pn"].split("-")[1]+"_"+ECM_IDs[id]["year"],ECM_IDs[id]["pn"]+".bin")
			if os.path.isfile(p):
				bins[id] = ECM_IDs[id]
				bins[id]["bin"] = p
	return bins

DTC = {
	"01-01": "MAP sensor circuit low voltage",
	"01-02": "MAP sensor circuit high voltage",
	"02-01": "MAP sensor performance problem",
	"07-01": "ECT sensor circuit low voltage",
	"07-02": "ECT sensor circuit high voltage",
	"08-01": "TP sensor circuit low voltage",
	"08-02": "TP sensor circuit high voltage",
	"09-01": "IAT sensor circuit low voltage",
	"09-02": "IAT sensor circuit high voltage",
	"11-01": "VS sensor no signal",
	"12-01": "No.1 primary injector circuit malfunction",
	"13-01": "No.2 primary injector circuit malfunction",
	"14-01": "No.3 primary injector circuit malfunction",
	"15-01": "No.4 primary injector circuit malfunction",
	"16-01": "No.1 secondary injector circuit malfunction",
	"17-01": "No.2 secondary injector circuit malfunction",
	"18-01": "CMP sensor no signal",
	"19-01": "CKP sensor no signal",
	"21-01": "0₂ sensor malfunction",
	"23-01": "0₂ sensor heater malfunction",
	"25-02": "Knock sensor circuit malfunction",
	"25-03": "Knock sensor circuit malfunction",
	"29-01": "IACV circuit malfunction",
	"33-02": "ECM EEPROM malfunction",
	"34-01": "ECV POT low voltage malfunction",
	"34-02": "ECV POT high voltage malfunction",
	"35-01": "EGCA malfunction",
	"48-01": "No.3 secondary injector circuit malfunction",
	"49-01": "No.4 secondary injector circuit malfunction",
	"51-01": "HESD linear solenoid malfunction",
	"54-01": "Bank angle sensor circuit low voltage",
	"54-02": "Bank angle sensor circuit high voltage",
	"56-01": "Knock sensor IC malfunction",
	"86-01": "Serial communication malfunction"
}

def format_read(location):
	tmp = struct.unpack(">4B",struct.pack(">I",location))
	return [tmp[1], tmp[3], tmp[2]]

def checksum8bitHonda(data):
	return ((sum(bytearray(data)) ^ 0xFF) + 1) & 0xFF

def checksum8bit(data):
	return 0xff - ((sum(bytearray(data))-1) >> 8)

def validate_checksums(byts, nbyts, cksum):
	ret = False
	fixed = False
	if cksum > 0 and cksum < nbyts:
		byts[cksum] = checksum8bitHonda(byts[:cksum]+byts[(cksum+1):])
		fixed = True
	ret = checksum8bitHonda(byts)==0
	return ret, fixed, byts

def do_validation(byts, nbyts, cksum=0):
	status = "good"
	ret, fixed, byts = validate_checksums(byts, nbyts, cksum)
	if not ret:
		status = "bad"
	elif fixed:
		status = "fixed"
	return ret, status, byts

def format_message(mtype, data):
	ml = len(mtype)
	dl = len(data)
	msgsize = 0x02 + ml + dl
	msg = mtype + [msgsize] + data
	msg += [checksum8bitHonda(msg)]
	assert(msg[ml] == len(msg))
	return msg, ml, dl

class HondaECU(object):

	def __init__(self, device_id=None, latency=None, baudrate=10400):
		super(HondaECU, self).__init__()
		self.device_id = device_id
		self.dev = None
		self.error = 0
		self.resets = 0
		self.latency = latency
		self.baudrate = baudrate
		self.reset()

	def reset(self):
		if self.dev != None:
			del self.dev
			self.dev = None

		self.dev = Device(self.device_id, auto_detach=(platform.system()!="Windows"))
		self.setup()

	def setup(self):
		self.dev.ftdi_fn.ftdi_usb_reset()
		self.dev.ftdi_fn.ftdi_usb_purge_buffers()
		self.dev.ftdi_fn.ftdi_set_line_property(8, 1, 0)
		self.dev.baudrate = self.baudrate
		if self.latency:
			self.dev.ftdi_fn.ftdi_set_latency_timer(self.latency)
		latency = c_ubyte()
		self.dev.ftdi_fn.ftdi_get_latency_timer(byref(latency))

	def _break(self, ms):
		self.dev.ftdi_fn.ftdi_set_bitmode(1, 0x01)
		self.dev._write(b'\x00')
		time.sleep(ms)
		self.dev._write(b'\x01')
		self.dev.ftdi_fn.ftdi_set_bitmode(0, 0x00)
		self.dev.flush()

	def wakeup(self):
		self._break(.070)
		time.sleep(.130)

	def ping(self):
		return self.send_command([0xfe],[0x72], retries=0) != None

	def probe_tables(self, tables=None):
		if not tables:
			tables = [0x10, 0x11, 0x17, 0x20, 0x21, 0x60, 0x61, 0x67, 0x70, 0x71, 0xd0, 0xd1]
		ret = {}
		for t in tables:
			info = self.send_command([0x72], [0x71, t])
			if info:
				if info[3] > 2:
					ret[t] = [info[3],info[2]]
			else:
				return {}
		return ret

	def init(self):
		self.wakeup()
		return self.ping()

	def kline_new(self):
		pin_byte = c_ubyte()
		self.dev.ftdi_fn.ftdi_read_pins(byref(pin_byte))
		return (pin_byte.value == 0xff)

	def kline(self, timeout=.05):
		self.dev.flush()
		self.dev._write(b"\x00")
		to = time.time()
		while time.time() - to < timeout:
			tmp = self.dev._read(1)
			if len(tmp) == 1:
				return tmp == b"\x00"
		return False

	def kline_alt(self):
		self.dev.flush()
		self.dev._write(b"\xff")
		return self.dev._read(1) == b"\xff"

	def kline_old(self):
		b = create_string_buffer(2)
		self.dev.ftdi_fn.ftdi_poll_modem_status(b)
		return b.raw[1] & 16 == 0

	def send(self, buf, ml, timeout=.001):
		self.dev.flush()
		msg = "".join([chr(b) for b in buf]).encode("latin1")
		self.dev._write(msg)
		r = len(msg)
		timeout = .05 + timeout * r
		to = time.time()
		while r > 0:
			r -= len(self.dev._read(r))
			if time.time() - to > timeout: return None
		buf = bytearray()
		r = ml+1
		while r > 0:
			tmp = self.dev._read(r)
			r -= len(tmp)
			buf.extend(tmp)
			if time.time() - to > timeout: return None
		r = buf[-1]-ml-1
		while r > 0:
			tmp = self.dev._read(r)
			r -= len(tmp)
			buf.extend(tmp)
			if time.time() - to > timeout: return None
		return buf

	def send_command(self, mtype, data=[], retries=1):
		msg, ml, dl = format_message(mtype, data)
		r = 0
		while r <= retries:
			dispatcher.send(signal="ecu.debug", sender=self, msg="%d > [%s]" % (r, ", ".join(["%02x" % m for m in msg])))
			resp = self.send(msg, ml)
			if resp:
				if checksum8bitHonda(resp[:-1]) == resp[-1]:
					dispatcher.send(signal="ecu.debug", sender=self, msg="%d < [%s]" % (r, ", ".join(["%02x" % r for r in resp])))
					rmtype = resp[:ml]
					valid = False
					if ml == 3:
						valid = (rmtype[:2] == bytearray(map(lambda x: x | 0x10, mtype[:2])))
					elif ml == 1:
						valid = (rmtype == bytearray(map(lambda x: x & 0xf, mtype)))
					if valid:
						rml = resp[ml:(ml+1)]
						rdl = ord(rml) - 2 - len(rmtype)
						rdata = resp[(ml+1):-1]
						return (rmtype, rml, rdata, rdl)
					else:
						return None
			r += 1

	def detect_ecu_state_new(self):
		t0 = self.send_command([0x72], [0x71, 0x00], retries=0)
		if t0 is None:
			self.wakeup()
			self.ping()
			t0 = self.send_command([0x72], [0x71, 0x00], retries=0)
		if not t0 is None:
			if bytes(t0[2][5:7]) != b"\x00\x00":
				return ECUSTATE.OK
			else:
				if self.send_command([0x7d], [0x01, 0x01, 0x00], retries=0):
					return ECUSTATE.RECOVER_OLD
				if self.send_command([0x7b], [0x00, 0x01, 0x01], retries=0):
					return ECUSTATE.RECOVER_NEW
		else:
			writestatus = self.send_command([0x7e], [0x01, 0x01, 0x00], retries=0)
			if not writestatus is None:
				if writestatus[2][1] == 0x0f:
					return ECUSTATE.WRITE_GOOD
				elif writestatus[2][1] == 0x10:
					return ECUSTATE.WRITE_INIT_OLD
				elif writestatus[2][1] == 0x20:
					return ECUSTATE.WRITE_INIT_NEW
				elif writestatus[2][1] == 0x30:
					return ECUSTATE.ERASE
				elif writestatus[2][1] == 0x40:
					return ECUSTATE.WRITE
				elif writestatus[2][1] == 0x0:
					return ECUSTATE.WRITE_UNKNOWN1
				else:
					return ECUSTATE.ERROR
			else:
				readinfo = self.send_command([0x82, 0x82, 0x00], [0x00, 0x00, 0x00, 0x08], retries=0)
				if not readinfo is None:
					return ECUSTATE.READ
		return ECUSTATE.OFF if not self.kline() else ECUSTATE.UNKNOWN

	def do_init_recover(self):
		self.send_command([0x7b], [0x00, 0x01, 0x01])
		self.send_command([0x7b], [0x00, 0x01, 0x02])
		self.send_command([0x7b], [0x00, 0x01, 0x03])
		self.send_command([0x7b], [0x00, 0x02, 0x76, 0x03, 0x17])
		self.send_command([0x7b], [0x00, 0x03, 0x75, 0x05, 0x13])

	def do_init_write(self):
		self.send_command([0x7d], [0x01, 0x01, 0x01])
		self.send_command([0x7d], [0x01, 0x01, 0x02])
		self.send_command([0x7d], [0x01, 0x01, 0x03])
		self.send_command([0x7d], [0x01, 0x02, 0x50, 0x47, 0x4d])
		self.send_command([0x7d], [0x01, 0x03, 0x2d, 0x46, 0x49])

	def do_erase(self):
		self.send_command([0x7e], [0x01, 0x02])
		self.send_command([0x7e], [0x01, 0x03, 0x00, 0x00])
		self.send_command([0x7e], [0x01, 0x0b, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff])
		self.send_command([0x7e], [0x01, 0x0e, 0x01, 0x90])
		self.send_command([0x7e], [0x01, 0x01, 0x01])
		self.send_command([0x7e], [0x01, 0x04, 0xff])

	def do_erase_wait(self):
		cont = 1
		while cont:
			info = self.send_command([0x7e], [0x01, 0x05])
			if info:
				if info[2][1] == 0x00:
					cont = 0
			else:
				cont = -1
		if cont == 0:
			into = self.send_command([0x7e], [0x01, 0x01, 0x00])

	def do_post_write(self):
		self.send_command([0x7e], [0x01, 0x09])
		time.sleep(.5)
		self.send_command([0x7e], [0x01, 0x0a])
		time.sleep(.5)
		self.send_command([0x7e], [0x01, 0x0c])
		time.sleep(.5)
		info = self.send_command([0x7e], [0x01, 0x0d])
		if info: return (info[2][1] == 0x0f)

	def get_faults(self):
		faults = {'past':[], 'current':[]}
		for i in range(1,0x0c):
			info_current = self.send_command([0x72],[0x74, i])[2]
			for j in [3,5,7]:
				if info_current[j] != 0:
					faults['current'].append("%02d-%02d" % (info_current[j],info_current[j+1]))
			if info_current[2] == 0:
				break
		for i in range(1,0x0c):
			info_past = self.send_command([0x72],[0x73, i])[2]
			for j in [3,5,7]:
				if info_past[j] != 0:
					faults['past'].append("%02d-%02d" % (info_past[j],info_past[j+1]))
			if info_past[2] == 0:
				break
		return faults
