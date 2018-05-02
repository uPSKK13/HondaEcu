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
		if self.dev != None:
			self.dev.close()
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
		info = self.send_command([0xfe],[0x72], debug=debug, retries=0) # 0xfe <- KWP2000 fast init all nodes ?
		return ord(info[2]) == 0x72 if info else False

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

	def send(self, buf, ml, timeout=.5):
		self.dev.flush()
		msg = ("".join([chr(b) for b in buf]))
		self.dev.write(msg)
		r = len(msg)
		while r > 0:
			r -= len(self.dev.read(r))
		to = time.time()
		buf = ""
		r = ml+1
		while r > 0:
			tmp = self.dev.read(r)
			r -= len(tmp)
			buf += tmp
			if time.time() - to > timeout: return None
		r = ord(buf[-1])-ml-1
		while r > 0:
			tmp = self.dev.read(r)
			r -= len(tmp)
			buf += tmp
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
				continue
			else:
				if debug:
					sys.stderr.write("\n")
			if debug:
				sys.stderr.write(" <- %s" % repr([binascii.hexlify(r) for r in resp]))
			invalid = ord(resp[-1]) != checksum8bitHonda([ord(r) for r in resp[:-1]])
			if invalid:
				if debug:
					sys.stderr.write(" !%d \n" % (retries))
				retries -= 1
				continue
			else:
				if debug:
					sys.stderr.write("\n")
			rmtype = resp[:ml]
			rml = resp[ml:(ml+1)]
			rdl = ord(rml) - 2 - len(rmtype)
			rdata = resp[(ml+1):-1]
			if debug:
				sys.stderr.write("  < %s\n" % repr([rdl, rdata]))
			return (rmtype, rml, rdata, rdl)
