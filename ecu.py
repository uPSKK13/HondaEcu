from __future__ import division
from pylibftdi import Device, FtdiError, Driver
from ctypes import *
import struct
import time
import binascii
import sys
import platform
import os
import math

ECM_IDs = {
	"\x01\x00\x2b\x01\x01": ("CBR1000RR","2006-2007","38770-MEL-D21"),
	"\x01\x00\x2b\x04\x02": ("CBR1000RR","2006-2007","38770-MEL-A22"),
	"\x01\x00\xf3\x04\x01": ("CBR1000RR","2012-2013","38770-MGP-A01"),
	"\x01\x01\x83\x01\x01": ("CBR1000RR","2014-2016","38770-MGP-D62"),
	"\x01\x01\x83\x04\x01": ("CBR1000RR","2014-2016","38770-MGP-A92"),
	"\x01\x01\x25\x05\x01": ("CBR500R","2013-2014","38770-MGZ-A03"),
	"\x01\x01\xf2\x01\x01": ("CB500F","2016","38770-MJW-D51"),
	"\x01\x01\x28\x01\x01": ("CB500X","?2013?","?"),
	"\x01\x01\xde\x01\x01": ("CB500X","?2016?","?")
}

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

def checksum8bitHonda(data):
	return ((sum(bytearray(data)) ^ 0xFF) + 1) & 0xFF

def checksum8bit(data):
	return 0xff - ((sum(bytearray(data))-1) >> 8)

def validate_checksum(byts, cksum):
	fcksum = byts[cksum]
	ccksum = checksum8bitHonda(byts[:cksum]+byts[(cksum+1):])
	return fcksum, ccksum

def do_validation(byts, cksum, fix=False):
	status = "bad"
	fcksum, ccksum = validate_checksum(byts, cksum)
	if fcksum != ccksum:
		if fix:
			byts[cksum] = ccksum
			status = "fixed"
	else:
		status = "good"
	return byts, status

def format_message(mtype, data):
	ml = len(mtype)
	dl = len(data)
	msgsize = 0x02 + ml + dl
	msg = mtype + [msgsize] + data
	msg += [checksum8bitHonda(msg)]
	assert(msg[ml] == len(msg))
	return msg, ml, dl

class HondaECU(object):

	def __init__(self, device_id=None):
		super(HondaECU, self).__init__()
		self.device_id = device_id
		self.dev = None
		self.error = 0
		self.resets = 0
		self.reset()

	def reset(self):
		if self.dev != None:
			del self.dev
			self.dev = None

		self.dev = Device(self.device_id, auto_detach=(platform.system()!="Windows"))
		self.setup()
		self.starttime = time.time()

	def time(self):
		return time.time() - self.starttime

	def setup(self):
		self.dev.ftdi_fn.ftdi_usb_reset()
		self.dev.ftdi_fn.ftdi_usb_purge_buffers()
		self.dev.ftdi_fn.ftdi_set_line_property(8, 1, 0)
		self.dev.baudrate = 10400

	def _break(self, ms, debug=False):
		self.dev.ftdi_fn.ftdi_set_bitmode(1, 0x01)
		self.dev._write(b'\x00')
		time.sleep(ms)
		self.dev._write(b'\x01')
		self.dev.ftdi_fn.ftdi_set_bitmode(0, 0x00)
		self.dev.flush()

	def init(self, debug=False, retries=0):
		ret = False
		self._break(.070)
		time.sleep(.130)
		info = self.send_command([0xfe],[0x72], debug=debug, retries=retries)
		if info != None and ord(info[0]) > 0:
			if ord(info[2]) == 0x72:
				ret = True
		return ret

	def kline(self):
		self.dev.flush()
		self.dev._write(b"\x00")
		return self.dev._read(1) == b"\x00"

	def send(self, buf, ml, timeout=.5):
		self.dev.flush()
		msg = "".join([chr(b) for b in buf]).encode("latin1")
		self.dev._write(msg)
		r = len(msg)
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

	def send_command(self, mtype, data=[], retries=10, debug=False):
		msg, ml, dl = format_message(mtype, data)
		while retries >= 0:
			if debug:
				sys.stderr.write("[%s] > [%s]" % (str.rjust("%.03f" % self.time(), 8),", ".join(["%02x" % m for m in msg])))
			resp = self.send(msg, ml)
			if resp == None:
				if debug:
					sys.stderr.write(" !%d \n" % (retries))
				retries -= 1
				time.sleep(0)
				continue
			else:
				if debug:
					sys.stderr.write("\n")
			if debug:
				sys.stderr.write("[%s] < [%s]" % (str.rjust("%.03f" % self.time(), 8),", ".join(["%02x" % r for r in resp])))
			invalid = (resp[-1] != checksum8bitHonda([r for r in resp[:-1]]))
			if invalid:
				if debug:
					sys.stderr.write(" !%d \n" % (retries))
				retries -= 1
				time.sleep(0)
				continue
			else:
				if debug:
					sys.stderr.write("\n")
			sys.stderr.flush()
			rmtype = resp[:ml]
			rml = resp[ml:(ml+1)]
			rdl = ord(rml) - 2 - len(rmtype)
			rdata = resp[(ml+1):-1]
			return (rmtype, rml, rdata, rdl)
		return None

	def do_init_recover(self, debug=False):
		self.send_command([0x7b], [0x00, 0x01, 0x02], debug=debug)
		self.send_command([0x7b], [0x00, 0x01, 0x03], debug=debug)
		self.send_command([0x7b], [0x00, 0x02, 0x76, 0x03, 0x17], debug=debug) # seed/key?
		self.send_command([0x7b], [0x00, 0x03, 0x75, 0x05, 0x13], debug=debug) # seed/key?
		self.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

	def do_init_write(self, debug=False):
		self.send_command([0x7d], [0x01, 0x01, 0x02], debug=debug)
		self.send_command([0x7d], [0x01, 0x01, 0x03], debug=debug)
		self.send_command([0x7d], [0x01, 0x02, 0x50, 0x47, 0x4d], debug=debug) # seed/key?
		self.send_command([0x7d], [0x01, 0x03, 0x2d, 0x46, 0x49], debug=debug) # seed/key?
		self.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

	def do_erase(self, debug=False):
		self.send_command([0x7e], [0x01, 0x02], debug=debug)
		self.send_command([0x7e], [0x01, 0x03, 0x00, 0x00], debug=debug)
		self.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

		self.send_command([0x7e], [0x01, 0x0b, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff], debug=debug) # password?
		self.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

		self.send_command([0x7e], [0x01, 0x0e, 0x01, 0x90], debug=debug)
		self.send_command([0x7e], [0x01, 0x01, 0x01], debug=debug)
		self.send_command([0x7e], [0x01, 0x04, 0xff], debug=debug)
		self.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

	def do_erase_wait(self, debug=False):
		while True:
			info = self.send_command([0x7e], [0x01, 0x05], debug=debug)
			if info[2][1] == 0x00:
				break
		self.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

	def do_post_write(self, debug=False):
		self.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

		self.send_command([0x7e], [0x01, 0x09], debug=debug)
		self.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

		self.send_command([0x7e], [0x01, 0x0a], debug=debug)
		self.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

		self.send_command([0x7e], [0x01, 0x0c], debug=debug)
		self.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

		self.send_command([0x7e], [0x01, 0x0d], debug=debug)
		self.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

	def get_faults(self, debug=False):
		faults = {'past':[], 'current':[]}
		for i in range(1,0x0c):
			info_current = self.send_command([0x72],[0x74, i], debug=debug)[2]
			for j in [3,5,7]:
				if info_current[j] != 0:
					faults['current'].append("%02d-%02d" % (info_current[j],info_current[j+1]))
			if info_current[2] == 0:
				break
		for i in range(1,0x0c):
			info_past = self.send_command([0x72],[0x73, i], debug=debug)[2]
			for j in [3,5,7]:
				if info_past[j] != 0:
					faults['past'].append("%02d-%02d" % (info_past[j],info_past[j+1]))
			if info_past[2] == 0:
				break
		return faults

##################################################

def print_header():
	sys.stdout.write("===================================================\n")

def do_read_flash(ecu, binfile, rom_size=-1, offset=0, debug=False):
	if rom_size < 0:
		maxbyte = math.inf
	else:
		maxbyte = 1024 * rom_size
	nbyte = offset
	readsize = 8
	with open(binfile, "wb") as fbin:
		t = time.time()
		while nbyte < maxbyte:
			info = ecu.send_command([0x82, 0x82, 0x00], [int(nbyte/65536)] + [b for b in struct.pack("<H", nbyte % 65536)] + [readsize], debug=debug)
			if info == None:
				break
			fbin.write(info[2])
			fbin.flush()
			nbyte += readsize
			if nbyte % 256 == 0:
				sys.stdout.write(".")
			if nbyte % 8192 == 0:
				n = time.time()
				sys.stdout.write(" %dkB %.02fBps\n" % (int(nbyte/1024),8192/(n-t)))
				t = n
			sys.stdout.flush()

def do_write_flash(ecu, byts, debug=False, offset=0):
	writesize = 128
	maxi = len(byts)/128
	i = offset
	t = time.time()
	while i < maxi:
		bytstart = [s for s in struct.pack(">H",(8*i))]
		if i+1 == maxi:
			bytend = [s for s in struct.pack(">H",0)]
		else:
			bytend = [s for s in struct.pack(">H",(8*(i+1)))]
		d = list(byts[((i+0)*128):((i+1)*128)])
		x = bytstart + d + bytend
		c1 = checksum8bit(x)
		c2 = checksum8bitHonda(x)
		x = [0x01, 0x06] + x + [c1, c2]
		info = ecu.send_command([0x7e], x, debug=debug)
		if ord(info[1]) != 5:
			sys.stdout.write(" error\n")
			sys.exit(1)
		i += 1
		if i % 2 == 0:
			ecu.send_command([0x7e], [0x01, 0x08], debug=debug)
		if i % 4 == 0:
			sys.stdout.write(".")
		if i % 128 == 0:
			n = time.time()
			w = (i*writesize)
			sys.stdout.write(" %4dkB %.02fBps\n" % (int(w/1024),(128*128)/(n-t)))
			t = n
		sys.stdout.flush()
