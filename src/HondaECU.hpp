#ifndef _HONDAECU_H_
#define _HONDAECU_H_

#include <ftdi.h>

typedef struct {
  unsigned char mtype[3];
  unsigned int mtl;
  unsigned char data[256];
  unsigned int dl;
} honda_ecu_command_t;

class HondaECU
{
public:
  HondaECU(struct ftdi_context *ftdi);
  bool kline();
  void setup();
  void interrupt(unsigned int ms);
  bool init(bool debug);
  unsigned char * sendCommand(honda_ecu_command_t *cmd, bool debug);
private:
  struct ftdi_context *ftdi;
  unsigned char zero[1] = {'\x00'};
  unsigned char one[1] = {'\x01'};
};

#endif
