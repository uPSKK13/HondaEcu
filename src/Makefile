HONDAECU_BINS = HondaECU HondaECU.exe

all: $(HONDAECU_BINS)

clean: clean
	make -f makefile.unx clean
	make -f makefile.win clean

HondaECU:
	make -f makefile.unx

HondaECU.exe:
	make -f makefile.win

.PHONY: all clean
