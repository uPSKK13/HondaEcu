from __future__ import division
from pylibftdi import Device
from struct import unpack
from tabulate import tabulate
import time
import binascii
from HondaECU import *

if __name__ == '__main__':
	
	TEMP_OFFSET = -50
	
	tables = {
		0x71: [0x00, 0x11, 0x20, 0x61, 0x70, 0xd0, 0xd1],
		#0x72: [],
		0x73: [0x00, 0x01, 0x02, 0x03, 0x04, 0x05],
		#0x74: []
	}

	# Initialize communication with ECU
	ecu = HondaECU()

	"""
	Scan tables
	"""
	#for j in range(0, 0x4c)[::-1]:
	for j in tables.keys():
		pdata = {}
		#for i in range(0,256):
		for i in tables[j]:
			if j == 0x72:
				info = ecu.send_command([0x72], [j, i, 0x00, 0x20], debug=True)
			else:
				info = ecu.send_command([0x72], [j, i], debug=True)
			a = ord(info[2][0])
			b = ord(info[2][1])
			if info and info[2] > 0:
				if a == 0x71 and (b == 0x11 or b == 0x61):
					data = unpack(">H12B3H", info[2][2:])
					pdata[b] = [
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
				elif a == 0x71 and (b == 0xd0):
					data = unpack(">14B", info[2][2:])
					pdata[b] = [
						("STARTED", data[1])
					]
				else:
					data = unpack(">%dB" % len(info[2][2:]), info[2][2:])
		for i,d in pdata.items():
			print("~~~ %02x ~~~" % i)
			print(tabulate(d))
