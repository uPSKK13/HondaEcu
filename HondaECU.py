from __future__ import division
from pylibftdi import Device
from struct import unpack
from tabulate import tabulate
from ctypes import *
import time
import binascii
import sys

class HondaECU(object):

	def __init__(self, *args, **kwargs):
		super(HondaECU, self).__init__(*args, **kwargs)
		self.dev = Device()
		self.dev.ftdi_fn.ftdi_set_line_property(8, 1, 0)
		self.dev.baudrate = 10400

	def init(self, full=True, debug=False):
		self.dev.ftdi_fn.ftdi_set_bitmode(1, 0x01)
		self.dev.write('\x00')
		time.sleep(.070)
		self.dev.write('\x01')
		time.sleep(.130)
		self.dev.ftdi_fn.ftdi_set_bitmode(0, 0x00)
		self.dev.flush()
		if full:
			self.send_command([0xfe],[0x72], debug=debug)

	def _cksum(self, data):
		return -sum(data) % 256

	def kline(self):
		b = create_string_buffer(2)
		self.dev.ftdi_fn.ftdi_poll_modem_status(b)
		return ord(b.raw[1]) & 16 == 0

	def send(self, buf):
		msg = ("".join([chr(b) for b in buf]))
		self.dev.write(msg)
		time.sleep(.05)
		self.dev.read(buf[1]) # READ AND DISCARD CMD ECHO
		buf = self.dev.read(2)
		if len(buf) > 0:
			buf += self.dev.read(ord(buf[1])-2)
			return buf
			
	def send_command(self, mtype, data=[], debug=False):
		ml = len(mtype)
		dl = len(data)
		msgsize = 0x02 + ml + dl
		msg = mtype + [msgsize] + data
		msg += [self._cksum(msg)]
		assert(msg[ml] == len(msg))
		if debug:
			sys.stderr.write(">   %s\n" % repr([msgsize, "".join([chr(b) for b in msg])]))
			sys.stderr.write("->  %s\n" % repr(["%02x" % m for m in msg]))
		resp = self.send(msg)
		ret = None
		if resp:
			assert(ord(resp[-1]) == self._cksum([ord(r) for r in resp[:-1]]))
			if debug: sys.stderr.write(" <- %s\n" % repr([binascii.hexlify(r) for r in resp]))
			rmtype = resp[:ml]
			rml = ord(resp[ml:(ml+1)]) - 2 - len(rmtype)
			rdata = resp[(ml+1):-1]
			if debug: sys.stderr.write("  < %s\n" % repr([rml, rdata]))
			ret = (rmtype, rml, rdata)
		return ret
