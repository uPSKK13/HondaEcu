from __future__ import division, print_function
import struct
import time
import sys
import argparse

from HondaECU import *


if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('--debug', action='store_true', help="turn on debugging output")
	parser.add_argument('--skip-power-check', action='store_true', help="don't test for k-line activity")
	args = parser.parse_args()
	
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
	print("Special Handshake")
	ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f], debug=args.debug)
	ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75], debug=args.debug)
	print("===============================================")
	
	# Can't seem to get anything back from ECU after this point
	# I am pretty sure we are not longer talking with the ECU but a 
	# processor in the ECU. The following probably conforms to LIN-BUS
	# specs and python might not be precise enough, idk

	time.sleep(.05)
	ecu.send_command([0x82, 0x82, 0x08],[0x37, 0x01, 0x07], debug=args.debug)
	time.sleep(.2)
	print("===============================================")
	
	rbytes = 12
	maxbytes = 1024 * 256
	offset = 0
	rom = ""
	while offset < maxbytes:
		info = ecu.send_command([0x82, 0x82, 0x00],map(ord,struct.pack(">I",offset)[1:]) + [rbytes], debug=args.debug)
		if info == None:
			sys.exit(-1)
		rom += info[2]
		offset += rbytes
