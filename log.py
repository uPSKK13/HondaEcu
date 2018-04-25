#!/usr/bin/env python

from __future__ import division, print_function
from pylibftdi import Device
from struct import unpack
from tabulate import tabulate
import argparse

from HondaECU import *

if __name__ == '__main__':

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('--debug', action='store_true', help="turn on debugging output")
	parser.add_argument('--table', type=int, default=17, help="table to log")
	parser.add_argument('--logfile', type=str, default=None, help="file to write log to")
	args = parser.parse_args()

	ecu = HondaECU()

	print("===============================================")
	print("Initializing ECU communications")
	ecu.setup()
	ecu.init(debug=args.debug)
	ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)
	print("===============================================")

	log = None
	if args.logfile != None:
		log = open(args.logfile, "w")
	while True:
		info = ecu.send_command([0x72], [0x71, args.table], debug=args.debug)
		log.write(info[2][2:])
		log.write("\n")
		log.flush()
		if args.debug:
			data = unpack(">%dB" % len(info[2][2:]) , info[2][2:])
			print(data)
	if log != None:
		log.close()
	print("===============================================")
