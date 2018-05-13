from __future__ import division
from pylibftdi import Device, FtdiError, Driver
from struct import unpack
from ctypes import *
import time
import binascii
import sys

def checksum8bitHonda(data):
	return ((sum(bytearray(data)) ^ 0xFF) + 1) & 0xFF

class HondaECU(object):

	def __init__(self, *args, **kwargs):
		super(HondaECU, self).__init__(*args, **kwargs)
		self.dev = None
		self.error = 0
		self.resets = 0
		self.reset()

	def reset(self):
		if self.dev != None:
			del self.dev
			self.dev = None
		self.dev = Device()

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

	def init(self, debug=False):
		ret = False
		self._break(.070)
		time.sleep(.130)
		self.dev.flush()
		info = self.send_command([0xfe],[0x72], debug=debug, retries=0) # 0xfe <- KWP2000 fast init all nodes ?
		if info != None and ord(info[0]) > 0:
			if ord(info[2]) == 0x72:
				ret = True
		return ret

	def validate_checksum(self, bytes, fix=False):
		cksum = len(bytes)-8
		fcksum = ord(bytes[cksum])
		ccksum = checksum8bitHonda(bytes[:cksum]+bytes[(cksum+1):])
		fixed = False
		if fix:
			if fcksum != ccksum:
				fixed = True
				bytes[cksum] = ccksum
		return bytes, fcksum, ccksum, fixed

	def kline(self):
		b = create_string_buffer(2)
		self.dev.ftdi_fn.ftdi_poll_modem_status(b)
		return b.raw[1] & 16 == 0

	def send(self, buf, ml, timeout=.5):
		self.dev.flush()
		msg = "".join([chr(b) for b in buf]).encode('latin1')
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

	def _format_message(self, mtype, data):
		ml = len(mtype)
		dl = len(data)
		msgsize = 0x02 + ml + dl
		msg = mtype + [msgsize] + data
		msg += [checksum8bitHonda(msg)]
		assert(msg[ml] == len(msg))
		return msg, ml, dl

	def send_command(self, mtype, data=[], retries=10, debug=False):
		msg, ml, dl = self._format_message(mtype, data)
		first = True
		while first or retries > 0:
			first = False
			if debug:
				sys.stderr.write(">   %s\n" % repr([dl, "".join([chr(b) for b in data])]))
				sys.stderr.write("->  %s" % repr(["%02x" % m for m in msg]))
			resp = self.send(msg, ml)
			ret = None
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
				sys.stderr.write(" <- %s" % repr(["%02x" % r for r in resp]))
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
			rmtype = resp[:ml]
			rml = resp[ml:(ml+1)]
			rdl = ord(rml) - 2 - len(rmtype)
			rdata = resp[(ml+1):-1]
			if debug:
				sys.stderr.write("  < %s\n" % repr([rdl, rdata.decode("latin1")]))
			return (rmtype, rml, rdata, rdl)
