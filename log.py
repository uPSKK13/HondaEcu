#!/usr/bin/env python3

from __future__ import division, print_function

from pylibftdi import Device, FtdiError
from struct import unpack
import argparse
import platform
import datetime
import time
import os, sys

from HondaECU import *

import asyncio

get_time = time.time
if platform.system() == 'Windows':
	get_time = time.clock
getTime = get_time

def getDateTimeStamp():
	d = datetime.datetime.now().timetuple()
	return "%d-%02.d-%02.d_%02.d-%02.d-%02.d" % (d[0], d[1], d[2], d[3], d[4], d[5])

hds_tables = {
	10: [0x10, ">H12BHB", ["rpm","tps_volt","tps","ect_volt","ect","iat_volt","iat","map_volt","map","unk1","unk2","batt_volt","speed","ign"]],
	11: [0x11, ">H12BHHH", ["rpm","tps_volt","tps","ect_volt","ect","iat_volt","iat","map_volt","map","unk1","unk2","batt_volt","speed","ign","inj","o2_volt"]]
}

class timestamp(object):
	def __init__(self, timestamp):
		self.timestamp = timestamp

async def log_hds_table(loop, ecu, lock, hds_table):
	ds = getDateTimeStamp()
	with open("/var/log/HondaECU/%s.log" % (ds), "w") as log:
		header = ["timestamp","resets"] + hds_tables[hds_table][2]
		d = "\t".join(header)
		log.write(d)
		log.write("\n")
		log.flush()
		while True:
			info = None
			with await lock:
				if ecu.error == 0:
					try:
						info = ecu.send_command([0x72], [0x71, hds_tables[hds_table][0]], debug=args.debug, retries=0)
						if info and len(info[2][2:]) > 0:
							data = list(unpack(hds_tables[hds_table][1], info[2][2:]))
							data = ["%.08f" % (time.time()), "%d" % (ecu.resets)] + list(map(str,data))
							d = "\t".join(data)
							log.write(d)
							log.write("\n")
							log.flush()
						else:
							ecu.error = 1
					except FtdiError:
						ecu.error = 2
			await asyncio.sleep(0)

async def watchdog(loop, ecu, lock):
	while True:
		with await lock:
			try:
				if ecu.error > 0:
					if ecu.error > 1:
						ecu.reset()
						ecu.setup()
					if ecu.kline():
						if ecu.init():
							ecu.error = 0
							ecu.resets += 1
			except FtdiError:
				ecu.error = 3
		await asyncio.sleep(0)


if __name__ == '__main__':

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('--debug', action='store_true', help="turn on debugging output")
	args = parser.parse_args()

	while True:
		try:
			ecu = HondaECU()
			ecu.setup()
			while not ecu.init(debug=args.debug):
				time.sleep(0)
			break
		except FtdiError:
			time.sleep(0)

	hds_table = 10
	info = ecu.send_command([0x72], [0x71, 0x11], debug=args.debug)
	if len(info[2][2:]) == 20:
		hds_table = 11

	lock = asyncio.Lock()
	loop = asyncio.get_event_loop()
	loop.create_task(watchdog(loop, ecu, lock))
	loop.create_task(log_hds_table(loop, ecu, lock, hds_table))

	loop.run_forever()
	loop.close()
