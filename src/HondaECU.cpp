#ifdef _WIN32
#include "mingw.thread.h"
#endif

#include "HondaECU.hpp"
#include "argagg.hpp"

#include <chrono>
#include <thread>
#include <sstream>
#include <iostream>
#include <iomanip>

using namespace std;
using namespace std::chrono;

unsigned char checksum8bitHonda(unsigned char msg[], unsigned int l)
{
  unsigned char csum = 0;
  for (int i=0; i<l; i++)
  {
    csum += msg[i];
  }
  return ((csum ^ 0xff) + 1) & 0xff;
}

void format_message(unsigned char msg[], unsigned char mtype[], unsigned int mtl, unsigned char data[], unsigned int dl)
{
  unsigned char l = 2 + mtl + dl;
  int i = 0;
  int j = 0;
  for (;i<mtl;i++)
  {
    msg[i] = mtype[i];
  }
  msg[i++] = l;
  for (;j<dl;j++)
  {
    msg[i+j] = data[j];
  }
  msg[l-1] = 0;
  msg[l-1] = checksum8bitHonda(msg, l);
}

HondaECU::HondaECU(struct ftdi_context *ftdi)
{
  this->ftdi = ftdi;
}

bool HondaECU::kline()
{
  unsigned short status;
  ftdi_poll_modem_status(this->ftdi, &status);
  return ((((status >> 8) & 0xff) & 0x16) == 0);
}

void HondaECU::setup()
{
  ftdi_usb_reset(this->ftdi);
  ftdi_usb_purge_buffers(this->ftdi);
  ftdi_set_line_property(this->ftdi, BITS_8, STOP_BIT_1, NONE);
  ftdi_set_baudrate(this->ftdi, 10400);
}

void HondaECU::interrupt(unsigned int ms)
{
  ftdi_set_bitmode(this->ftdi, 0x01, 0x01);
  ftdi_write_data(this->ftdi, this->zero, 1);
  std::this_thread::sleep_for(milliseconds(ms));
  ftdi_write_data(this->ftdi, this->one, 1);
  ftdi_set_bitmode(this->ftdi, 0x00, 0x00);
  ftdi_usb_purge_buffers(this->ftdi);
}

unsigned char * HondaECU::sendCommand(honda_ecu_command_t *cmd, bool debug)
{
  unsigned char buf[256];
  unsigned int ml = 2 + cmd->mtl + cmd->dl;
  unsigned int r,rr;
  format_message(buf, cmd->mtype, cmd->mtl, cmd->data, cmd->dl);
  if (debug) {
    cerr << "> [";
    for (int z=0;z<ml;z++)
    {
      cerr << (int)buf[z];
      if (z<ml-1)
      {
        cerr << ", ";
      }
    }
    cerr << "]" << endl;
  }
  ftdi_write_data(this->ftdi, buf, ml);
  r = ml;
  while (r>0)
    r -= ftdi_read_data(this->ftdi, buf, r);
  int i=0;
  int j=0;
  r = ml;
  stringstream inbuf(stringstream::out | stringstream::binary);
  r = cmd->mtl + 1;
  while (r>0)
  {
    rr = ftdi_read_data(this->ftdi, buf, r);
    inbuf.write(reinterpret_cast<const char *>(buf), rr);
    r -= rr;
  }
  unsigned int msize = inbuf.str().c_str()[cmd->mtl];
  inbuf.clear();
  unsigned char *resp = new unsigned char[msize]();
  for (;i<cmd->mtl+1;i++)
  {
    resp[i] = buf[i];
  }
  unsigned int p2 = msize - cmd->mtl - 1;
  r = p2;
  while (r>0)
  {
    rr = ftdi_read_data(this->ftdi, buf, r);
    inbuf.write(reinterpret_cast<const char *>(buf), rr);
    r -= rr;
  }
  for (;j<p2;j++)
  {
    resp[i+j] = buf[j];
  }
  if (debug) {
    cerr << "< [";
    for (int z=0;z<msize;z++)
    {
      cerr << (int)resp[z];
      if (z<msize-1)
      {
        cerr << ", ";
      }
    }
    cerr << "]" << endl;
  }
  return resp;
}

bool HondaECU::init(bool debug)
{
    this->interrupt(70);
    std::this_thread::sleep_for(milliseconds(130));
    ftdi_usb_purge_buffers(this->ftdi);
    honda_ecu_command_t *cmd = (honda_ecu_command_t*)malloc(sizeof(honda_ecu_command_t));
    cmd->mtype = new unsigned char[1]();
    cmd->mtype[0] = 0xfe;
    cmd->mtl = 1;
    cmd->data = new unsigned char[1]();
    cmd->data[0] = 0x72;
    cmd->dl = 1;
    unsigned char *resp = this->sendCommand(cmd, debug);
    delete[] cmd->mtype;
    delete[] cmd->data;
    free(cmd);
}

unsigned char * do_validation(bool *cont, const char* binfile, bool fix)
{
  cout << "==============================================================================" << endl;
  FILE *bin;
  *cont = false;
  unsigned int csum_old = 0;
  unsigned int csum_new = 0;
  string status;
  bin = fopen(binfile, "rb");
  if (!bin)
    return NULL;
  fseek(bin, 0L, SEEK_END);
  long lSize = ftell(bin);
  rewind(bin);
  unsigned char *buffer = (unsigned char*)calloc(1, lSize+1);
  fread(buffer, lSize, 1, bin);
  fclose(bin);
  csum_old = buffer[lSize-8];
  buffer[lSize-8] = 0;
  csum_new = checksum8bitHonda(buffer, lSize);
  if (fix)
    cout << "Fixing bin file checksum" << endl;
  else
    cout << "Validating bin file checksum" << endl;
  cout << "  file checksum: " << csum_old << endl;
  cout << "  computed checksum: " << csum_new << endl;
  if (csum_old == csum_new)
  {
    status = "good";
    *cont = true;
  }
  else
  {
    if (fix)
    {
      buffer[lSize-8] = csum_new;
      bin = fopen(binfile, "wb");
      fwrite(buffer, sizeof(unsigned char), lSize, bin);
      fclose(bin);
      status = "fixed";
      *cont = true;
    }
    else
    {
      status = "bad";
    }
  }
  cout << "  status: " << status << endl;
  return buffer;
}

int main(int argc, char **argv)
{
  using argagg::parser_results;
  using argagg::parser;

  parser argparser {{
    {
      "help", {"-h", "--help"},
      "Print help and exit", 0},
    {
      "device", {"-d","--device"},
      "Device number (default: 0)", 1},
    {
      "size", {"-s","--size"},
      "Read/write size in Kb (default: 256)", 1},
    {
      "fix", {"--fix"},
      "Fix checksum (default: false)", 0},
    {
      "debug", {"--debug"},
      "Enable debug output (default: false)", 0},
  }};

  // Define our usage text.
  ostringstream usage;
  usage
    << "Usage: " << argv[0] << " [-h] [-d] [--fix] {read|write|recover|checksum} binfile" << endl
    << endl;

  ostringstream header;
  header
    << "HondaECU v1.0" << endl;

  argagg::parser_results args;
  argagg::fmt_ostream fmt(cout);
  try {
    args = argparser.parse(argc, argv);
  } catch (const std::exception& e) {
    fmt << usage.str() << argparser << endl
        << "Encountered exception while parsing arguments: " << e.what()
        << endl;
    return EXIT_FAILURE;
  }

  if (args["help"]) {
    cout << header.str();
    argagg::fmt_ostream fmt(cout);
    fmt << usage.str() << argparser;
    return EXIT_SUCCESS;
  }

  unsigned int size = 256;
  if (args["size"])
    size = args["size"].as<int>();

  bool debug = false;
  if (args["debug"])
    debug = true;

  if (args.pos.size()!=2)
  {
    fmt << usage.str() << argparser << endl;
  }
  else
  {
    struct ftdi_context *ftdi;
    struct ftdi_device_list *devlist;

    ftdi = ftdi_new();
    if (ftdi==NULL)
      return EXIT_FAILURE;
    if (ftdi_init(ftdi)!=0)
      return EXIT_FAILURE;

    int ndev = ftdi_usb_find_all(ftdi, &devlist, 0, 0);
    int dev = 0;
    if (args["device"])
    {
      dev = args["device"].as<int>();
      if (dev>=ndev) {
        cout << "Device number out of range!" << endl;
        return EXIT_FAILURE;
      }
    }

    if (!(strcmp(args.pos[0],"read")==0 || strcmp(args.pos[0],"write")==0 || strcmp(args.pos[0],"recover")==0 || strcmp(args.pos[0],"checksum")==0))
    {
      fmt << usage.str() << argparser << endl;
      return EXIT_FAILURE;
    }

    bool cont = false;
    unsigned char *buffer;
    if (strcmp(args.pos[0],"read")!=0)
    {
      buffer = do_validation(&cont, args.pos[1], args["fix"]);
      if (strcmp(args.pos[0],"checksum")==0) {
        cont = false;
      }
    }
    if (cont || strcmp(args.pos[0],"read")==0)
    {
      ftdi_usb_open_dev(ftdi, devlist[dev].dev);
      HondaECU *ecu = new HondaECU(ftdi);
      cout << "==============================================================================" << endl;
      if (ecu->kline()) {
        cout << "Turn off bike/ECU" << endl;
        while (ecu->kline())
          std::this_thread::sleep_for(milliseconds(100));
      }
      cout << "Turn on bike/ECU" << endl;
      while (!ecu->kline())
        std::this_thread::sleep_for(milliseconds(100));
      std::this_thread::sleep_for(milliseconds(500));
      ecu->setup();
      honda_ecu_command_t *cmd = (honda_ecu_command_t*)malloc(sizeof(honda_ecu_command_t));
      unsigned char *resp;
      if (strcmp(args.pos[0],"recover")!=0) {
        cout << "==============================================================================" << endl;
        cout << "Initializing ECU communications" << endl;
        ecu->init(debug);
        cmd->mtl = 1;
        cmd->mtype = new unsigned char[cmd->mtl]();
        cmd->mtype[0] = 0x72;
        cmd->dl = 2;
        cmd->data = new unsigned char[cmd->dl]();
        cmd->data[0] = 0x00;
        cmd->data[1] = 0xf0;
        resp = ecu->sendCommand(cmd, debug);
        delete[] resp;
        delete[] cmd->mtype;
        delete[] cmd->data;
      }
      if (strcmp(args.pos[0],"write")==0) {
        cout << "==============================================================================" << endl;
				cout << "Writing bin file to ECU" << endl;
      } else if (strcmp(args.pos[0],"read")==0) {
        cout << "==============================================================================" << endl;
				cout << "Entering Boot Mode" << endl;
        cmd->mtl = 1;
        cmd->mtype = new unsigned char[cmd->mtl]();
        cmd->mtype[0] = 0x27;
        cmd->dl = 8;
        cmd->data = new unsigned char[cmd->dl]();
        cmd->data[0] = 0xe0;
        cmd->data[1] = 0x48;
        cmd->data[2] = 0x65;
        cmd->data[3] = 0x6c;
        cmd->data[4] = 0x6c;
        cmd->data[5] = 0x6f;
        cmd->data[6] = 0x48;
        cmd->data[7] = 0x6f;
        resp = ecu->sendCommand(cmd, debug);
        delete[] resp;
        delete[] cmd->mtype;
        delete[] cmd->data;
        cmd->mtl = 1;
        cmd->mtype = new unsigned char[cmd->mtl]();
        cmd->mtype[0] = 0x27;
        cmd->dl = 8;
        cmd->data = new unsigned char[cmd->dl]();
        cmd->data[0] = 0xe0;
        cmd->data[1] = 0x77;
        cmd->data[2] = 0x41;
        cmd->data[3] = 0x72;
        cmd->data[4] = 0x65;
        cmd->data[5] = 0x59;
        cmd->data[6] = 0x6f;
        cmd->data[7] = 0x75;
        resp = ecu->sendCommand(cmd, debug);
        delete[] resp;
        delete[] cmd->mtype;
        delete[] cmd->data;
        cout << "==============================================================================" << endl;
				cout << "Dumping ECU to bin file" << endl;
        unsigned int maxbyte = 1024 * size;
        unsigned int nbyte = 0;
        unsigned int readsize = 8;
        unsigned short offset;
        unsigned int ms = duration_cast< milliseconds >(system_clock::now().time_since_epoch()).count();
        unsigned int msn;
        FILE *bin = fopen(args.pos[1], "wb");
        while (nbyte < maxbyte)
        {
          offset = nbyte % 65536;
          cmd->mtl = 3;
          cmd->mtype = new unsigned char[cmd->mtl]();
          cmd->mtype[0] = 0x82;
          cmd->mtype[1] = 0x82;
          cmd->mtype[2] = 0x00;
          cmd->dl = 4;
          cmd->data = new unsigned char[cmd->dl]();
          cmd->data[0] = nbyte/65536;
          cmd->data[1] = (offset >> 0) & 0xff;
          cmd->data[2] = (offset >> 8) & 0xff;
          cmd->data[3] = readsize;
          resp = ecu->sendCommand(cmd, debug);
          nbyte = nbyte + readsize;
          if (nbyte % 256 == 0)
            cout << "." << flush;
          if (nbyte % (16*1024) == 0)
          {
            msn = duration_cast< milliseconds >(system_clock::now().time_since_epoch()).count();
            cout << " " << nbyte/1024 << "kB " << std::setprecision(5) << (1024*16.0)/(msn-ms)*1000 << " Bps" << endl;
            ms = msn;
          }
          fwrite(&resp[4], sizeof(unsigned char), readsize, bin);
          fflush(bin);
          delete[] resp;
          delete[] cmd->mtype;
          delete[] cmd->data;
        }
        fclose(bin);
        buffer = do_validation(&cont, args.pos[1], false);
      }
      free(cmd);
    }
    if (buffer)
      free(buffer);
    cout << "==============================================================================" << endl;
  }
}
