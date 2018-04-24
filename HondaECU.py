from __future__ import division
from pylibftdi import Device
from struct import unpack
from tabulate import tabulate
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

	def setup(self):
		if self.dev == None:
			self.dev = Device()
		self.dev.ftdi_fn.ftdi_set_line_property(8, 1, 0)
		self.dev.baudrate = 10400

	def _break(self, ms, debug=False):
		self.dev.ftdi_fn.ftdi_set_bitmode(1, 0x01)
		self.dev.write('\x00')
		time.sleep(ms)
		self.dev.write('\x01')
		self.dev.ftdi_fn.ftdi_set_bitmode(0, 0x00)
		self.dev.flush()

	def init(self, debug=False):
		self._break(.070)
		time.sleep(.130)
		self.send_command([0xfe],[0x72], debug=debug) # 0xfe <- KWP2000 fast init all nodes ?

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
		return ord(b.raw[1]) & 16 == 0

	def send(self, buf, ml):
		self.dev.flush()
		msg = ("".join([chr(b) for b in buf]))
		self.dev.write(msg)
		r = len(msg)
		while r > 0:
			r -= len(self.dev.read(r))
		buf = ""
		r = ml+1
		while r > 0:
			tmp = self.dev.read(r)
			r -= len(tmp)
			buf += tmp
		r = ord(buf[-1])-ml-1
		while r > 0:
			tmp = self.dev.read(r)
			r -= len(tmp)
			buf += tmp
		return buf

	def _format_message(self, mtype, data):
		ml = len(mtype)
		dl = len(data)
		msgsize = 0x02 + ml + dl
		msg = mtype + [msgsize] + data
		msg += [checksum8bitHonda(msg)]
		assert(msg[ml] == len(msg))
		return msg, ml, dl

	def send_command(self, mtype, data=[], debug=False):
		msg, ml, dl = self._format_message(mtype, data)
		if debug:
			sys.stderr.write(">   %s\n" % repr([dl, "".join([chr(b) for b in data])]))
			sys.stderr.write("->  %s\n" % repr(["%02x" % m for m in msg]))
		resp = self.send(msg, ml)
		ret = None
		if resp:
			assert(ord(resp[-1]) == checksum8bitHonda([ord(r) for r in resp[:-1]]))
			if debug:
				sys.stderr.write(" <- %s\n" % repr([binascii.hexlify(r) for r in resp]))
			rmtype = resp[:ml]
			rml = resp[ml:(ml+1)]
			rdl = ord(rml) - 2 - len(rmtype)
			rdata = resp[(ml+1):-1]
			if debug:
				sys.stderr.write("  < %s\n" % repr([rdl, rdata]))
			ret = (rmtype, rml, rdata, rdl)
		return ret
