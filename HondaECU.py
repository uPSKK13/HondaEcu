import argparse

from cmd import *
from gui2 import *

__VERSION__ = "2.0.0_beta1"

class Hex(object):
	def __call__(self, value):
		return int(value, 16)

class MultOf8(object):
	def __call__(self, value):
		value = int(value)
		if value % 8 == 0:
			return value
		else:
			raise argparse.ArgumentTypeError("%d is not a multiple of 8" % (value))

def Main():
	default_checksum = '0x3fff8'
	default_romsize = 256

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	subparsers = parser.add_subparsers(metavar='mode',dest='mode')

	parser_read = subparsers.add_parser('read', help='read ecu to binfile')
	parser_read.add_argument('binfile', help="name of output binfile")
	parser_read.add_argument('--rom-size', default=-1, type=int, help="size of ecu rom in kilobytes")
	parser_read.add_argument('--offset', default=0, help="read offset (must be multiple of 8)", type=MultOf8())

	parser_write = subparsers.add_parser('write', help='write ecu from binfile')
	parser_write.add_argument('binfile', help="name of input binfile")
	parser_write.add_argument('--rom-size', default=default_romsize, type=int, help="size of ecu rom in kilobytes")
	parser_write.add_argument('--fix-checksum', type=Hex(), help="hex location to fix binfile checksum")
	parser_write.add_argument('--force', action='store_true', help="force write (old-school recovery)")

	parser_recover = subparsers.add_parser('recover', help='recover ecu from binfile')
	parser_recover.add_argument('binfile', help="name of input binfile")
	parser_recover.add_argument('--rom-size', default=default_romsize, type=int, help="size of ecu rom in kilobytes")
	parser_recover.add_argument('--fix-checksum', type=Hex(), help="hex location to fix binfile checksum")

	parser_checksum = subparsers.add_parser('checksum', help='validate binfile checksum')
	parser_checksum.add_argument('binfile', help="name of input binfile")
	parser_checksum.add_argument('--fix-checksum', type=Hex(), help="hex location to fix binfile checksum")

	parser_scan = subparsers.add_parser('scan', help='scan engine data')

	parser_faults = subparsers.add_parser('faults', help='read fault codes')
	parser_faults.add_argument('--clear', action='store_true', help="clear fault codes")

	parser_log = subparsers.add_parser('log', help='log engine data')

	parser_recover = subparsers.add_parser('kline', help='kline tests')
	parser_recover.add_argument('--type', default=0, type=int, choices=[0,1,2,3], help="kline test type")

	db_grp = parser.add_argument_group('debugging options')
	db_grp.add_argument('--debug', action='store_true', help="turn on debugging output")
	db_grp.add_argument('--verbose', action='store_true', help="turn on verbose output")
	db_grp.add_argument('--noredirect', action='store_true', help="dont redirect stdout/stderr")
	db_grp.add_argument('--latency', type=int, help="latency timer")
	db_grp.add_argument('--skip-power-check', action='store_true', help="skip power check")
	args = parser.parse_args()

	if args.mode == None:
		app = wx.App()
		gui = HondaECU_GUI(args, __VERSION__)
		app.MainLoop()
	else:
		HondaECU_CmdLine(args, __VERSION__)

if __name__ == '__main__':
	Main()
