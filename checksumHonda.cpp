#include <iostream>
#include <cstdio>

using namespace std;

#include <argagg.hpp>

#define MAX_BYTES 262144

int main(int argc, char **argv)
{
  using argagg::parser_results;
  using argagg::parser;
  using std::cerr;
  using std::cout;
  using std::endl;
  using std::ostringstream;
  using std::string;

  parser argparser {{
      {
        "help", {"-h", "--help"},
        "Print help and exit", 0},
      {
        "fix", {"--fix"},
        "Fix checksum (default: false)", 0},
    }};

  // Define our usage text.
  ostringstream usage;
  usage
    << "Usage: " << argv[0] << " [OPTIONS]... [FILE]" << endl
    << endl;

  ostringstream header;
  header
    << "Honda Checksum Utility v1.0" << endl;

  argagg::parser_results args;
  try {
    args = argparser.parse(argc, argv);
  } catch (const std::exception& e) {
    argagg::fmt_ostream fmt(cerr);
    fmt << usage.str() << argparser << endl
        << "Encountered exception while parsing arguments: " << e.what()
        << endl;
    return EXIT_FAILURE;
  }

  // If the help flag was specified then spit out the usage and help text and
  // exit.
  if (args["help"]) {
    cerr << header.str();
    argagg::fmt_ostream fmt(cerr);
    fmt << usage.str() << argparser;
    return EXIT_SUCCESS;
  }

  if (args.pos.size()==1) {
    FILE *bin;
    int csum_old = 0;
    int csum_new = 0;
    string status;
    bin = fopen(args.pos[0], "rb");
    if (!bin)
      return EXIT_FAILURE;
    unsigned char buffer[MAX_BYTES];
    fread(buffer, sizeof(unsigned char), MAX_BYTES, bin);
    fclose(bin);
    csum_old = buffer[MAX_BYTES-8];
    buffer[MAX_BYTES-8] = 0;
    for (int i=0; i<MAX_BYTES; i++) {
      csum_new += buffer[i];
    }
    csum_new = ((csum_new ^ 0xff) + 1) & 0xff;
    cout << "file checksum: " << csum_old << endl;
    cout << "computed checksum: " << csum_new << endl;
    if (csum_old == csum_new) {
      status = "good";
    } else {
      if (args["fix"]) {
        buffer[MAX_BYTES-8] = csum_new;
        bin = fopen(args.pos[0], "wb");
        fwrite(buffer, sizeof(unsigned char), MAX_BYTES, bin);
        fclose(bin);
        status = "fixed";
      } else {
        status = "bad";
      }
    }
    cout << "status: " << status << endl;
  }

  return EXIT_SUCCESS;
}
