#!/usr/bin/env python

from __future__ import division, print_function
import struct
import time
import sys
import os
import argparse

from HondaECU import *

def print_header():
	sys.stdout.write("===================================================\n")

def do_validation(binfile, cksum, fix=False):
	print_header()
	if fix:
		sys.stdout.write("Fixing bin file checksum\n")
	else:
		sys.stdout.write("Validating bin file checksum\n")
	with open(binfile, "rb") as fbin:
		byts, fcksum, ccksum, fixed = validate_checksum(bytearray(fbin.read(os.path.getsize(binfile))), cksum, fix)
		if fixed:
			status = "fixed"
		elif fcksum == ccksum:
			status = "good"
		else:
			status = "bad"
		sys.stdout.write("  file checksum: %s\n" % fcksum)
		sys.stdout.write("  calculated checksum: %s\n" % ccksum)
		sys.stdout.write("  status: %s\n" % status)
		return byts, fcksum, ccksum, fixed

def do_read_flash(ecu, binfile, rom_size, debug=False):
	maxbyte = 1024 * rom_size
	nbyte = 0
	readsize = 8
	with open(binfile, "wb") as fbin:
		t = time.time()
		while nbyte < maxbyte:
			info = ecu.send_command([0x82, 0x82, 0x00], [int(nbyte/65536)] + [b for b in struct.pack("<H", nbyte % 65536)] + [readsize], debug=args.debug)
			fbin.write(info[2])
			fbin.flush()
			nbyte += readsize
			if nbyte % 256 == 0:
				sys.stdout.write(".")
			if nbyte % 8192 == 0:
				n = time.time()
				sys.stdout.write(" %dkB %.02fBps\n" % (int(nbyte/1024),8192/(n-t)))
				t = n
			sys.stdout.flush()

def do_write_flash(ecu, byts, debug=False, offset=0):
	writesize = 128
	maxi = len(byts)/128
	i = offset
	t = time.time()
	while i < maxi:
		bytstart = [s for s in struct.pack(">H",(8*i))]
		if i+1 == maxi:
			bytend = [s for s in struct.pack(">H",0)]
		else:
			bytend = [s for s in struct.pack(">H",(8*(i+1)))]
		d = list(byts[((i+0)*128):((i+1)*128)])
		x = bytstart + d + bytend
		c1 = checksum8bit(x)
		c2 = checksum8bitHonda(x)
		x = [0x01, 0x06] + x + [c1, c2]
		info = ecu.send_command([0x7e], x, debug=debug)
		if ord(info[1]) != 5:
			sys.stdout.write(" error\n")
			sys.exit(1)
		i += 1
		if i % 2 == 0:
			ecu.send_command([0x7e], [0x01, 0x08], debug=debug)
		if i % 4 == 0:
			sys.stdout.write(".")
		if i % 128 == 0:
			n = time.time()
			w = (i*writesize)
			sys.stdout.write(" %4dkB %.02fBps\n" % (int(w/1024),(128*128)/(n-t)))
			t = n
		sys.stdout.flush()

if __name__ == '__main__':

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('mode', choices=["read","write","recover","validate_checksum","fix_checksum"], help="ECU mode")
	parser.add_argument('binfile', help="name of bin to read or write")
	parser.add_argument('--checksum', default='0x3fff8', type=Hex(), help="hex location of checksum in ECU bin")
	parser.add_argument('--rom-size', default=256, type=int, help="size of ECU bin in kilobytes")
	parser.add_argument('--fix-checksum', action='store_true', help="fix checksum before write/recover")
	db_grp = parser.add_argument_group('debugging options')
	db_grp.add_argument('--debug', action='store_true', help="turn on debugging output")
	args = parser.parse_args()

	offset = 0

	if os.path.isabs(args.binfile):
		binfile = args.binfile
	else:
		binfile = os.path.abspath(os.path.expanduser(args.binfile))

	ret = 1
	if args.mode != "read":
		byts, fcksum, ccksum, fixed = do_validation(binfile, args.checksum, args.mode == "fix_checksum" or args.fix_checksum)
		if (fcksum == ccksum or fixed) and args.mode in ["recover","write"]:
			ret = 0
		else:
			ret = -1
	else:
		ret = 0

	if ret == 0:

		ecu = HondaECU()
		ecu.setup()

		print_header()
		if ecu.kline():
			sys.stdout.write("Turn off bike\n")
			while ecu.kline():
				time.sleep(.1)
		sys.stdout.write("Turn on bike\n")
		while not ecu.kline():
			time.sleep(.1)
		time.sleep(.5)

		print_header()
		sys.stdout.write("Wake-up ECU\n")
		try:
			initok = ecu.init(debug=args.debug)
			print_header()
			sys.stdout.write("Entering diagnostic mode\n")
			ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)
		except MaxRetriesException:
			initok = False
		except:
			sys.exit(-1)

		if args.mode == "read":
			print_header()
			sys.stdout.write("Security access\n")
			ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f], debug=args.debug)
			ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75], debug=args.debug)

			print_header()
			sys.stdout.write("Reading ECU\n")
			do_read_flash(ecu, binfile, args.rom_size, debug=args.debug)
			do_validation(binfile, args.checksum)

		else:
			if args.mode == "write":
				print_header()
				sys.stdout.write("Initializing write process\n")
				try:
					ecu.do_init_write(debug=args.debug)
				except MaxRetriesException:
					args.mode = "recover"
					sys.stdout.write("Switching to recovery mode\n")
				except:
					sys.exit(-1)

			if args.mode == "recover":
				if initok:
					print_header()
					sys.stdout.write("Initializing recovery process\n")
					ecu.do_init_recover(debug=args.debug)

					print_header()
					sys.stdout.write("Entering enhanced diagnostic mode\n")
					ecu.send_command([0x72],[0x00, 0xf1], debug=args.debug)
					ecu.send_command([0x27],[0x00, 0x9f, 0x00], debug=args.debug)

			print_header()
			sys.stdout.write("Erasing ECU\n")
			ecu.do_erase(debug=args.debug)

			print_header()
			sys.stdout.write("Writing ECU\n")
			do_write_flash(ecu, byts, offset=0, debug=args.debug)

			print_header()
			sys.stdout.write("Finalizing write process\n")
			ecu.do_post_write(debug=args.debug)

	print_header()
	sys.exit(ret)
