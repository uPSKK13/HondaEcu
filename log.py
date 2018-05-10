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

async def log_hds(lock, log, last_update, ecu, hds_table, resets):
	info = None
	with await lock:
		if ecu != None:
			info = ecu.send_command([0x72], [0x71, hds_tables[hds_table][0]], debug=args.debug, retries=0)
	while info and len(info[2][2:]) > 0:
		last_update.timestamp = time.time()
		data = list(unpack(hds_tables[hds_table][1], info[2][2:]))
		data = ["%.08f" % (last_update.timestamp), "%d" % (resets)] + list(map(str,data))
		d = "\t".join(data)
		log.write(d)
		log.write("\n")
		log.flush()
		await asyncio.sleep(0)
		with await lock:
			if ecu != None:
				info = ecu.send_command([0x72], [0x71, hds_tables[hds_table][0]], debug=args.debug, retries=0)
			else:
				break

async def watchdog(lock, loop, ecu, hds_table):
	ds = getDateTimeStamp()
	resets = 0
	with open("/var/log/HondaECU/%s.log" % (ds), "w") as log:
		header = ["timestamp","resets"] + hds_tables[hds_table][2]
		d = "\t".join(header)
		log.write(d)
		log.write("\n")
		log.flush()
		restart = False
		last_update = timestamp(0)
		logtask = loop.create_task(log_hds(lock, log, last_update, ecu, hds_table, resets))
		while True:
			old_update = last_update.timestamp
			await asyncio.sleep(1)
			if last_update.timestamp == -1:
				loop.stop()
				break
			elif last_update.timestamp == -2:
				restart = True
			elif old_update == last_update.timestamp:
				logtask.cancel()
				asyncio.sleep(0)
				with await lock:
					del ecu.dev
				await asyncio.sleep(1)
				restart = True
			if restart:
				resets += 1
				with await lock:
					ecu = newECU()
				while ecu == None:
					await asyncio.sleep(0)
					with await lock:
						ecu = newECU()
				restart = False
				last_update.timestamp = 0
				logtask = loop.create_task(log_hds(lock, log, last_update, ecu, hds_table, resets))

def newECU():
	try:
		ecu = HondaECU()
		ecu.setup()
		return ecu
	except:
		return None

if __name__ == '__main__':

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('--debug', action='store_true', help="turn on debugging output")
	args = parser.parse_args()

	ecu = newECU()
	while not ecu.init(debug=args.debug):
		time.sleep(0)

	hds_table = 10
	info = ecu.send_command([0x72], [0x71, 0x11], debug=args.debug)
	if len(info[2][2:]) == 20:
		hds_table = 11

	lock = asyncio.Lock()
	loop = asyncio.get_event_loop()
	loop.create_task(watchdog(lock, loop, ecu, hds_table))

	loop.run_forever()
	loop.close()
