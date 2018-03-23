from __future__ import division
from pylibftdi import Device
from struct import unpack
import time
import binascii

class HondaECU(Device):
	
	def __init__(self, *args, **kwargs):
		super(HondaECU, self).__init__(*args, **kwargs)
		self.ftdi_fn.ftdi_set_bitmode(1, 0x01)
		self.write('\x00')
		time.sleep(.050)
		self.write('\x01')
		time.sleep(.130)
		self.ftdi_fn.ftdi_set_bitmode(0, 0x00)
		self.ftdi_fn.ftdi_set_line_property(8, 1, 0)
		self.baudrate = 10400
		self.flush()
		
	def __cksum(self, data):
		return -sum(data) % 256

	def send(self, buf, response=True):
		assert(buf[1] == len(buf))
		msg = ("".join([chr(b) for b in buf]))
		self.write(msg)
		time.sleep(.025)
		self.read(buf[1])
		if response:
			time.sleep(.025)
			buf = self.read(2)
			buf += self.read(ord(buf[1])-2)
			return buf
			
	def send_command(self, id1, id2, tid, start=None, offset=None):
		if start != None and offset!= None:
			data = [id1, 0x07, id2, tid, start, offset]
		else:
			data = [id1, 0x05, id2, tid]
		data += [self.__cksum(data)]
		resp = self.send(data)
		assert(ord(resp[-1]) == self.__cksum([ord(r) for r in resp[:-1]]))
		return (resp[3],ord(resp[1])-5,resp[4:-1])
		
if __name__ == '__main__':
	
	# Initialize communication with ECU
	ecu = HondaECU()
	ecu.send([0xfe, 0x04, 0xff, 0xff], False)
	ecu.send([0x72, 0x05, 0x00, 0xf0, 0x99])

	# Scan tables
	while True:
		print("".join("="*160))
		#for i in range(0,255):
		for i in [0x00, 0x11, 0x20, 0x61, 0x70, 0xd0, 0xd1]:
			info = ecu.send_command(0x72, 0x71, i)
			if info[1] > 0:
				print(binascii.hexlify(info[0]), info[1], unpack("%dB" % info[1], info[2]))
