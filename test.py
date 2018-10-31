#!/usr/bin/env python

from __future__ import division, print_function
import struct
import time
import sys
import os
import argparse
import code

from HondaECU import *

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
db_grp = parser.add_argument_group('debugging options')
db_grp.add_argument('--debug', action='store_true', help="turn on debugging output")
args = parser.parse_args()

ecu = HondaECU()
ecu.setup()
ecu.wakeup()
ecu.ping()
# while True:
#     info = ecu.send_command([0x72], [0x71, 0xd1])
#     print([i for i in info[2][2:]])
# if ecu.kline():
#     sys.stdout.write("Turn off bike\n")
#     while ecu.kline():
#         time.sleep(.1)
# if not ecu.kline():
#     sys.stdout.write("Turn on bike\n")
#     while not ecu.kline():
#         time.sleep(.1)
#     time.sleep(1)


# ecu.ping()
# for k,v in ecu.probe_tables().items():
#     print(hex(k),v)

#ecu.send_command([0x7e], [0x01, 0x08], debug=args.debug)
ecu.send_command([0x82, 0x82, 0x00], [0,0,0])
#ecu.do_post_write(debug=True)
#code.interact(local=dict(globals(), **locals()))
sys.exit(1)











ecu.ping(debug=args.debug)
ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)
ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f], debug=args.debug)
ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75], debug=args.debug)
readsize = 12
location = 1024*256 - 256
while True:
    tmp = ecu.send_command([0x82, 0x82, 0x00], format_read(location) + [readsize], debug=args.debug)
    if not tmp:
        readsize -= 1
        if readsize < 1:
            break
    else:
        location += readsize






# while True:
#     ecu.ping(debug=args.debug)
#     ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)
#     ecu.send_command([0x72],[0x71, 0x00], debug=args.debug)
# print("")
# ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug, retries=0)
# print("")
#ecu.send_command([0x7b], [0x00, 0x01, 0x01], debug=args.debug)
# ecu.send_command([0x7b], [0x00, 0x01, 0x02], debug=args.debug, retries=0)
# ecu.send_command([0x7b], [0x00, 0x01, 0x03], debug=args.debug, retries=0)
# ecu.send_command([0x7b], [0x00, 0x02, 0x76, 0x03, 0x17], debug=args.debug, retries=0)
# ecu.send_command([0x7b], [0x00, 0x03, 0x75, 0x05, 0x13], debug=args.debug, retries=0)
# print("")
# ecu.send_command([0x72],[0x00, 0xf1], debug=args.debug)
# time.sleep(3)
# for i in range(256):
#     for j in range(256):
#         info = ecu.send_command([0x27],[0x00, i, j], debug=True, retries=0)
#         if info: print(i,j,info)
# time.sleep(14)
# print("")
# ecu.do_erase(debug=args.debug)
# print("")
# ecu.do_erase_wait(debug=args.debug)
# print("")
# ecu.send_command([0x7e], [0x01, 0x02], debug=args.debug, retries=0)
# ecu.send_command([0x7e], [0x01, 0x05], debug=args.debug, retries=0)
# ecu.send_command([0x7e], [0x01, 0x08], debug=args.debug, retries=0)
# ecu.send_command([0x7e], [0x01, 0x09], debug=args.debug, retries=0)
# ecu.send_command([0x7e], [0x01, 0x0a], debug=args.debug, retries=0)
# ecu.send_command([0x7e], [0x01, 0x0c], debug=args.debug, retries=0)
# ecu.send_command([0x7e], [0x01, 0x0d], debug=args.debug, retries=0)
#

# #ecu.do_post_write(debug=args.debug)
