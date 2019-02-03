import argparse

from wx import App
from controlpanel import HondaECU_ControlPanel

if __name__ == '__main__':

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('--noredirect', action='store_true', help="don't redirect stdout/stderr to gui")
	args = parser.parse_args()

	app = App(redirect=not args.noredirect)
	gui = HondaECU_ControlPanel()
	app.MainLoop()
