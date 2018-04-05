from __future__ import division
from pylibftdi import Device
from struct import unpack
from tabulate import tabulate
import struct
import time
import binascii
from HondaECU import *
import sys
import code

ecu = HondaECU()

code.interact(local=dict(globals(), **locals()))
