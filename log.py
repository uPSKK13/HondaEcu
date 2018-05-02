#!/usr/bin/env python

from __future__ import division, print_function
from pylibftdi import Device
from struct import unpack
import argparse
import platform
import datetime
import time
import sys, atexit
from distutils.version import StrictVersion

import tables
from tables import *
from HondaECU import *

get_time = time.time
if platform.system() == 'Windows':
	get_time = time.clock
getTime = get_time

def getDateTimeStamp():
	d = datetime.datetime.now().timetuple()
	return "%d%02d%02d%02d%02d%02d" % (d[0], d[1], d[2], d[3], d[4], d[5])

def my_close_open_files(verbose):
	open_files = tables.file._open_files
	are_open_files = len(open_files) > 0
	if verbose and are_open_files:
		sys.stderr.write("Closing remaining open files:")
	if StrictVersion(tables.__version__) >= StrictVersion("3.1.0"):
		handlers = list(open_files.handlers)
	else:
		keys = open_files.keys()
		handlers = []
		for key in keys:
			handlers.append(open_files[key])
	for fileh in handlers:
		if verbose:
			sys.stderr.write("%s..." % fileh.filename)
		fileh.close()
		if verbose:
			sys.stderr.write("done")
	if verbose and are_open_files:
		sys.stderr.write("\n")
atexit.register(my_close_open_files, False)

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
	parser.add_argument('--logfile', type=str, default='honda_kline_log.h5', help="log filename")
	args = parser.parse_args()

	atexit.register(my_close_open_files, False)
	FILTERS = tables.Filters(complib='zlib', complevel=5)
	h5 = open_file(args.logfile, mode="w", title="Honda KLine Engine Log", filters=FILTERS)

	ecu = HondaECU()

	while True:
		try:
			ecu.setup()
			while not ecu.kline():
				time.sleep(.1)
			ecu.init(debug=args.debug)
			ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)
			ds = getDateTimeStamp()
			log = h5.create_table("/", "EngineData_%s" % ds, HDS_TAB11, "Log starting on %s" % (ds))
			try:
				while True:
					t = time.time()
					info = ecu.send_command([0x72], [0x71, 0x11], debug=args.debug)
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
			except:
				log.flush()
			log.close()
		except:
			time.sleep(1)
