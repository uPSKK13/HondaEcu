#!/usr/bin/env python

from __future__ import division, print_function
import struct
import time
import sys
import os
import argparse

from HondaECU import *


if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('mode', choices=["read","write"], help="ECU mode")
	parser.add_argument('binfile', help="name of bin to read or write")
	parser.add_argument('--rom-size', default=256, type=int, help="size of ECU rom in bytes")
	db_grp = parser.add_argument_group('debugging options')
	db_grp.add_argument('--skip-power-check', action='store_true', help="don't test for k-line activity")
	db_grp.add_argument('--debug', action='store_true', help="turn on debugging output")

	args = parser.parse_args()
	
	if os.path.isabs(args.binfile):
		outfile = args.binfile
	else:
		outfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.binfile)

	ecu = HondaECU()

	if not args.skip_power_check:
		# In order to read flash we must send commands while the ECU's
		# bootloader is still active which is right after the bike powers up
		if ecu.kline():
			print("Turn off bike")
			while ecu.kline():
				time.sleep(.1)
		print("Turn on bike")
		while not ecu.kline():
			time.sleep(.1)
		time.sleep(.5)

	print("===============================================")
	print("Initializing ECU communications")
	ecu.init(debug=args.debug)
	ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)
	print("===============================================")
	print("Entering Boot Mode")
	ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f], debug=args.debug)
	ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75], debug=args.debug)
	time.sleep(.5)
	print("===============================================")
	print("Dumping ECU to file")
	maxbyte = 1024 * args.rom_size
	nbyte = 0
	readsize = 8
	with open(outfile, "w") as fbin:
		while nbyte < maxbyte:
			info = ecu.send_command([0x82, 0x82, 0x00], [int(nbyte/65536)] + map(ord,struct.pack("<H", nbyte % 65536)) + [readsize], debug=args.debug)
			fbin.write(info[2])
			fbin.flush()
			nbyte += readsize
			if nbyte % 64 == 0:
				sys.stdout.write(".")
				sys.stdout.flush()
			if nbyte % 1024 == 0:
				sys.stdout.write(" %dkb\n" % int(nbyte/1024))
	print("===============================================")
