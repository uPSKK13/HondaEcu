#!/usr/bin/env python

from __future__ import division, print_function
from pylibftdi import Device
from struct import unpack
import argparse
import platform
import datetime
import time

from tables import *
from HondaECU import *

get_time = time.time
if platform.system() == 'Windows':
    get_time = time.clock
getTime = get_time

def getDateTimeStamp():
    d = datetime.datetime.now().timetuple()
    return "%d%02d%02d%02d%02d%02d" % (d[0], d[1], d[2], d[3], d[4], d[5])

class HDS_TAB11(IsDescription):
	timestamp = Float64Col()
	hds_rpm = UInt16Col()
	hds_tps_volt = UInt8Col()
	hds_tps = UInt8Col()
	hds_ect_volt = UInt8Col()
	hds_ect = UInt8Col()
	hds_iat_volt = UInt8Col()
	hds_iat = UInt8Col()
	hds_map_volt = UInt8Col()
	hds_map = UInt8Col()
	hds_unk1 = UInt8Col()
	hds_unk2 = UInt8Col()
	hds_battery_volt = UInt8Col()
	hds_speed = UInt8Col()
	hds_ign = UInt8Col()
	hds_inj = UInt8Col()
	hds_unk3 = UInt8Col()

if __name__ == '__main__':

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('--debug', action='store_true', help="turn on debugging output")
	parser.add_argument('--table', type=int, default=17, help="table to log")
	parser.add_argument('--logfile', type=str, default='honda_kline_log.h5', help="log filename")
	args = parser.parse_args()

	ecu = HondaECU()

	print("===============================================")
	print("Initializing ECU communications")
	ecu.setup()
	ecu.init(debug=args.debug)
	ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)
	print("===============================================")

	h5 = open_file(args.logfile, mode="w", title="Honda KLine Engine Log")
	ds = getDateTimeStamp()
	log = h5.create_table("/", ds, HDS_TAB11, "Log starting on %s" % (ds))
	while True:
		t = time.time()
		info = ecu.send_command([0x72], [0x71, args.table], debug=args.debug)
		data = unpack(">H12B3H", info[2][2:])
		if args.debug:
			print(data)
		d = log.row
		d['timestamp'] = t
		d['hds_rpm'] = data[0]
		d['hds_tps_volt'] = data[1]
		d['hds_tps'] = data[2]
		d['hds_ect_volt'] = data[3]
		d['hds_ect'] = data[4]
		d['hds_iat_volt'] = data[5]
		d['hds_iat'] =data[6]
		d['hds_map_volt'] = data[7]
		d['hds_map'] = data[8]
		d['hds_unk1'] = data[9]
		d['hds_unk2'] = data[10]
		d['hds_battery_volt'] = data[11]
		d['hds_speed'] = data[12]
		d['hds_ign'] = data[13]
		d['hds_inj'] = data[14]
		d['hds_unk3'] = data[15]
		d.append()
		log.flush()
	h5.close()
	print("===============================================")
