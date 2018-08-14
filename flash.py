#!/usr/bin/env python

from __future__ import division, print_function
import struct
import time
import sys
import os
import argparse

from HondaECU import *

def do_validation(binfile, fix=False):
	print("==============================================================================")
	if fix:
		print("Fixing bin file checksum")
	else:
		print("Validating bin file checksum")
	with open(binfile, "rb") as fbin:
		byts, fcksum, ccksum, fixed = validate_checksum(bytearray(fbin.read(os.path.getsize(binfile))), fix)
		if fixed:
			status = "fixed"
		elif fcksum == ccksum:
			status = "good"
		else:
			status = "bad"
		print("  file checksum: %s" % fcksum)
		print("  calculated checksum: %s" % ccksum)
		print("  status: %s" % status)
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
			if nbyte % 64 == 0:
				sys.stdout.write(".")
			if nbyte % 1024 == 0:
				n = time.time()
				sys.stdout.write(" %dkB %.02fBps\n" % (int(nbyte/1024),1024/(n-t)))
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
		sys.stdout.write(".")
		if i % 64 == 0:
			n = time.time()
			w = (i*writesize)
			sys.stdout.write(" %dkB %.02fBps\n" % (int(w/1024),(64*128)/(n-t)))
			t = n
		sys.stdout.flush()

def do_post_write(ecu, debug=False):
	time.sleep(3)
	ecu.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)
	ecu.send_command([0x7e], [0x01, 0x09], debug=debug)
	ecu.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)
	ecu.send_command([0x7e], [0x01, 0x0a], debug=debug)
	ecu.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)
	ecu.send_command([0x7e], [0x01, 0x0c], debug=debug)
	ecu.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)
	ecu.send_command([0x7e], [0x01, 0x0d], debug=debug)
	ecu.send_command([0x7e], [0x01, 0x01, 0x00], debug=debug)

if __name__ == '__main__':

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('mode', choices=["read","write","recover","validate_checksum","fix_checksum"], help="ECU mode")
	parser.add_argument('binfile', help="name of bin to read or write")
	parser.add_argument('--write-mode', type=int, choices=[0,1], default=0, help="ECU write technique")
	parser.add_argument('--recover-mode', type=int, choices=[0,1], default=0, help="ECU recover technique")
	parser.add_argument('--rom-size', default=256, type=int, help="size of ECU rom in kilobytes")
	db_grp = parser.add_argument_group('debugging options')
	db_grp.add_argument('--skip-power-check', action='store_true', help="don't test for k-line activity")
	db_grp.add_argument('--fix-checksum', action='store_true', help="fix checksum before write/recover")
	db_grp.add_argument('--debug', action='store_true', help="turn on debugging output")
	args = parser.parse_args()

	offset = 0

	if os.path.isabs(args.binfile):
		binfile = args.binfile
	else:
		binfile = os.path.abspath(os.path.expanduser(args.binfile))

	ret = 1
	if args.mode != "read":
		byts, fcksum, ccksum, fixed = do_validation(binfile, args.mode == "fix_checksum" or args.fix_checksum)
		if (fcksum == ccksum or fixed) and args.mode in ["recover","write"]:
			ret = 0
		else:
			ret = -1
	else:
		ret = 0

	if ret == 0:

		ecu = HondaECU()
		ecu.setup()

		if not args.skip_power_check:
			print("===============================================")
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

		if args.mode == "read":
			print("===============================================")
			print("Reading ECU")
			ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)
			ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f], debug=args.debug)
			ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75], debug=args.debug)
			do_read_flash(ecu, binfile, args.rom_size, debug=args.debug)
			do_validation(binfile)

		elif args.mode == "write":
			print("===============================================")
			print("Writing ECU")
			ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)
			ecu.do_init_write(debug=args.debug)
			ecu.do_pre_write(debug=args.debug)
			ecu.do_pre_write_wait(debug=args.debug)
			do_write_flash(ecu, byts, offset=0, debug=args.debug)
			do_post_write(ecu, debug=args.debug)

		elif args.mode == "recover":
			print("===============================================")
			print("Recovering ECU")
			ecu.do_init_recover(debug=args.debug)
			ecu.send_command([0x72],[0x00, 0xf1], debug=args.debug)
			ecu.send_command([0x27],[0x00, 0x9f, 0x00], debug=args.debug)
			ecu.do_pre_write(debug=args.debug)
			ecu.do_pre_write_wait(debug=args.debug)
			do_write_flash(ecu, byts, offset=0, debug=args.debug)
			do_post_write(ecu, debug=args.debug)

	print("===============================================")
	sys.exit(ret)
