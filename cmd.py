import os, sys
from ecu import *

def HondaECU_CmdLine(args, version):

    offset = 0
    binfile = None
    ret = 1
    if args.mode in ["read","write","recover","checksum"]:
        if os.path.isabs(args.binfile):
            binfile = args.binfile
        else:
            binfile = os.path.abspath(os.path.expanduser(args.binfile))
        if args.mode == "read":
            ret = 0
        else:
            fbin = open(binfile, "rb")
            nbyts = os.path.getsize(binfile)
            byts = bytearray(fbin.read(nbyts))
            fbin.close()
            cksum = None
            if args.fix_checksum:
                if args.fix_checksum < nbyts:
                    cksum = args.fix_checksum
                else:
                    sys.stdout.write("Invalid checksum location\n")
                    sys.exit(-1)
            else:
                cksum = nbyts - 8
            print_header()
            sys.stdout.write("Validating checksum\n")
            byts, status = do_validation(byts, cksum, args.fix_checksum)
            if status == "fixed":
                if args.mode == "checksum":
                    fbin = open(binfile, "wb")
                    fbin.write(byts)
                    fbin.close()
                    status += " (permanent)"
                else:
                    status += " (temporary)"
            sys.stdout.write("  status: %s\n" % (status))
            if (status != "bad") and args.mode in ["recover","write"]:
                ret = 0
            else:
                ret = -1
    else:
        ret = 0

    if ret == 0:

        try:
            ecu = HondaECU()
        except FtdiError:
            sys.stderr.write("No flash adapters detected!\n")
            sys.exit(-2)

        if args.mode == "kline":
            f = [ecu.kline, ecu.kline_old, ecu.kline_new, ecu.kline_alt][args.type]
            while True:
                print(f())
            sys.exit(1)

        if args.mode in ["read","write","recover"] and ecu.kline():
            print_header()
            sys.stdout.write("Turn off bike\n")
            while ecu.kline():
                time.sleep(.1)
            time.sleep(.5)
        if not ecu.kline():
            sys.stdout.write("Turn on bike\n")
            while not ecu.kline():
                time.sleep(.1)
            time.sleep(.5)

        print_header()
        sys.stdout.write("Initializing ECU\n")
        initok = ecu.init(debug=args.debug)

        if initok:
            print_header()
            sys.stdout.write("Entering diagnostic mode\n")
            ecu.send_command([0x72],[0x00, 0xf0], debug=args.debug)
            info = ecu.send_command([0x72],[0x72, 0x00, 0x00, 0x05], debug=args.debug)
            sys.stdout.write("  ECM ID: %s\n" % " ".join(["%02x" % b for b in info[2][3:]]))

            if args.mode == "scan":
                print_header()
                sys.stdout.write("HDS Tables\n")
                for j in range(256):
                    info = ecu.send_command([0x72], [0x71, j], debug=args.debug)
                    if info and len(info[2][2:]) > 0:
                        sys.stdout.write(" %s\t%s\n" % (hex(j), repr([b for b in info[2][2:]])))

            elif args.mode == "faults":
                if args.clear:
                    print_header()
                    sys.stdout.write("Clearing fault codes\n")
                    while True:
                        info = ecu.send_command([0x72],[0x60, 0x03], debug=args.debug)[2]
                        if info[1] == 0x00:
                            break
                print_header()
                faults = ecu.get_faults(debug=args.debug)
                sys.stdout.write("Fault codes\n")
                if len(faults['current']) > 0:
                    sys.stdout.write("  Current:\n")
                    for code in faults['current']:
                        sys.stdout.write("    %s: %s\n" % (code, DTC[code] if code in DTC else "Unknown"))
                if len(faults['past']) > 0:
                    sys.stdout.write("  Past:\n")
                    for code in faults['past']:
                        sys.stdout.write("    %s: %s\n" % (code, DTC[code] if code in DTC else "Unknown"))

            elif args.mode == "read":
                print_header()
                sys.stdout.write("Security access\n")
                ecu.send_command([0x27],[0xe0, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x48, 0x6f], debug=args.debug)
                ecu.send_command([0x27],[0xe0, 0x77, 0x41, 0x72, 0x65, 0x59, 0x6f, 0x75], debug=args.debug)

                print_header()
                sys.stdout.write("Reading ECU\n")
                do_read_flash(ecu, binfile, debug=args.debug)
                print_header()
                sys.stdout.write("Validating checksum\n")
                with open(binfile, "rb") as fbin:
                    nbyts = os.path.getsize(binfile)
                    byts = bytearray(fbin.read(nbyts))
                    _, status = do_validation(byts, nbyts-8)
                    sys.stdout.write("  status: %s\n" % (status))

            elif args.mode == "write":
                print_header()
                sys.stdout.write("Initializing write process\n")
                ecu.do_init_write(debug=args.debug)

            elif args.mode == "recover":
                print_header()
                sys.stdout.write("Initializing recovery process\n")
                ecu.do_init_recover(debug=args.debug)

                print_header()
                sys.stdout.write("Entering enhanced diagnostic mode\n")
                ecu.send_command([0x72],[0x00, 0xf1], debug=args.debug)
                time.sleep(1)
                ecu.send_command([0x27],[0x00, 0x01, 0x00], debug=args.debug)

        if args.mode in ["write", "recover"] and (initok or args.force):

            print_header()
            sys.stdout.write("Erasing ECU\n")
            time.sleep(14)
            ecu.do_erase(debug=args.debug)
            ecu.do_erase_wait(debug=args.debug)

            print_header()
            sys.stdout.write("Writing ECU\n")
            do_write_flash(ecu, byts, offset=0, debug=args.debug)

            print_header()
            sys.stdout.write("Finalizing write process\n")
            ecu.do_post_write(debug=args.debug)

    print_header()
    sys.exit(ret)
