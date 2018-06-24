#!/usr/bin/env python

from __future__ import division, print_function
import struct
import time
import sys
import os
import argparse

from HondaECU import *

def do_validation(binfile, fix=False):
	print("===============================================")
	if fix == "fix_checksum":
		print("Fixing bin file checksum")
	else:
		print("Validating bin file checksum")
	with open(binfile, "rb") as fbin:
		bytes, fcksum, ccksum, fixed = ecu.validate_checksum(bytearray(fbin.read(os.path.getsize(binfile))))
		if fixed:
			stats = "fixed"
		elif fcksum == ccksum:
			status = "good"
		else:
			status = "bad"
		print("  file checksum: %s" % fcksum)
		print("  calculated checksum: %s" % ccksum)
		print("  status: %s" % status)
		return bytes, fcksum, ccksum, fixed

if __name__ == '__main__':

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('mode', choices=["read","write","recover","validate_checksum","fix_checksum"], help="ECU mode")
	parser.add_argument('binfile', help="name of bin to read or write")
	parser.add_argument('--rom-size', default=256, type=int, help="size of ECU rom in kilobytes")
	db_grp = parser.add_argument_group('debugging options')
	db_grp.add_argument('--skip-power-check', action='store_true', help="don't test for k-line activity")
	db_grp.add_argument('--debug', action='store_true', help="turn on debugging output")

	args = parser.parse_args()

	if os.path.isabs(args.binfile):
		binfile = args.binfile
	else:
		binfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.binfile)

	ecu = HondaECU()

	if args.mode == "validate_checksum" or args.mode == "fix_checksum":
		do_validation(binfile, args.mode == "fix_checksum")
	else:
		ecu.setup()

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
		# <- 0x02 0x04 0x00 0xfa

		if args.mode == "read":
			print("===============================================")
			print("Entering Boot Mode")
			ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f], debug=args.debug)
			ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75], debug=args.debug)
			print("===============================================")
			print("Dumping ECU to bin file")
			maxbyte = 1024 * args.rom_size
			nbyte = 0
			readsize = 8
			with open(binfile, "wb") as fbin:
				t = time.time()
				while nbyte < maxbyte:
					info = ecu.send_command([0x82, 0x82, 0x00], [int(nbyte/65536)] + [b for b in struct.pack("<H", nbyte % 65536)] + [readsize], debug=args.debug)
					fbin.write(info[2])
					fbin.flush()
					nbyte += readsize
					if nbyte % 64 == 0:
						sys.stdout.write(".")
						sys.stdout.flush()
					if nbyte % 1024 == 0:
						n = time.time()
						sys.stdout.write(" %dkb %.02fbps\n" % (int(nbyte/1024),1024/(n-t)))
						t = n
			do_validation(binfile)

		elif args.mode == "recover":
			print("===============================================")
			print("Recovering ECU")
			ecu.do_init_recover(debug=args.debug)
            ecu.send_command([0x72],[0x00, 0xf1], debug=args.debug)
			ecu.send_command([0x27],[0x00, 0x9f, 0x00], debug=args.debug)
            ecu.do_pre_write(debug=args.debug)
            ecu.do_pre_write_wait(debug=args.debug)
            ecu.send_command([0x7e], [0x01, 0xa0, 0x02], debug=args.debug) # ?size

		elif args.mode == "write":
			print("===============================================")
			print("Writing bin file to ECU")
			ecu.do_init_write(debug=args.debug)
			ecu.do_pre_write(debug=args.debug)
            ecu.do_pre_write_wait(debug=args.debug)

	print("===============================================")
