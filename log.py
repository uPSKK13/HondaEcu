#!/usr/bin/env python

from __future__ import division, print_function

from pylibftdi import Device
from struct import unpack
import argparse
import platform
import datetime
import time
import os

from HondaECU import *

import sdnotify

n = sdnotify.SystemdNotifier()

get_time = time.time
if platform.system() == 'Windows':
	get_time = time.clock
getTime = get_time

def getDateTimeStamp():
	d = datetime.datetime.now().timetuple()
	return "%d-%02.d-%02.d_%02.d-%02.d-%02.d" % (d[0], d[1], d[2], d[3], d[4], d[5])

hds_tables = {
	10: [0x10, ">H12BHB"],
	11: [0x11, ">H12BHHH"]
}

if __name__ == '__main__':

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('--debug', action='store_true', help="turn on debugging output")
	args = parser.parse_args()

	ecu = HondaECU()
	ecu.setup()

	ecu.init(debug=args.debug)
	ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)

	hds_table = 10
	info = ecu.send_command([0x72], [0x71, 0x11], debug=args.debug)
	if len(info[2][2:]) == 20:
		hds_table = 11

	ds = getDateTimeStamp()
	n.notify("READY=1")
	with open("/var/log/HondaECU/%s.log" % (ds), "w") as log:
		info = ecu.send_command([0x72], [0x71, hds_tables[hds_table][0]], debug=args.debug, retries=0)
		while info and len(info[2][2:]) > 0:
			tt = time.time()
			data = list(unpack(hds_tables[hds_table][1], info[2][2:]))
			data = ["%.08f" % (tt)] + map(str,data)
			d = "\t".join(data)
			log.write(d)
			log.write("\n")
			log.flush()
			n.notify("WATCHDOG=1")
			info = ecu.send_command([0x72], [0x71, hds_tables[hds_table][0]], debug=args.debug, retries=0)
