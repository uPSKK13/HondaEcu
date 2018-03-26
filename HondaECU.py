from __future__ import division
from pylibftdi import Device
from struct import unpack
from tabulate import tabulate
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
	
	TEMP_OFFSET = -50

	# Initialize communication with ECU
	ecu = HondaECU()
	ecu.send([0xfe, 0x04, 0xff, 0xff], False)
	ecu.send([0x72, 0x05, 0x00, 0xf0, 0x99])

	"""
	Scan tables
	"""
	pdata = {}
	for i in range(0,255):
	#for i in [0x00, 0x11, 0x20, 0x61, 0x70, 0xd0, 0xd1]:
		info = ecu.send_command(0x72, 0x71, i)
		if info[1] > 0:
			tbl = ord(info[0])
			print(binascii.hexlify(info[0]), [binascii.hexlify(i) for i in info[2]])
			if tbl == 0x11 or tbl == 0x61:
				data = unpack(">H12B3H", info[2])
				pdata[tbl] = [
					("RPM", data[0]),
					("TPS_volt", data[1]*5/256),
					("TPS_%", data[2]/1.6),
					("ECT_volt", data[3]*5/256),
					("ECT_deg_C", data[4]+TEMP_OFFSET),
					("IAT_volt", data[5]*5/256),
					("IAT_deg_C", data[6]+TEMP_OFFSET),
					("MAP_volt", data[7]*5/256),
					("MAP_kpa", data[8]),
					("?UNK1", data[9]),
					("?UNK2", data[10]),
					("BATT_volt", data[11]/10),
					("SPEED_kph", data[12]),
					("IGN_ang", data[13]/10),
					("*INJ_ms", data[14]),
					("?UNK3", data[15])
				]
			elif tbl == 0xd0:
				data = unpack(">14B", info[2])
				pdata[tbl] = [
					("STARTED", data[1])
				]
			else:
				data = unpack(">%dB" % info[1], info[2])
	print("")
	print("")
	for i,d in pdata.items():
		print("~~~ %02x ~~~" % i)
		print(tabulate(d))
