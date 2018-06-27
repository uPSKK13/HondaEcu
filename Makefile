.PHONY: all clean

CFLAGS := -std=c++11

all: windows linux

linux:
	g++ ${CFLAGS} checksumHonda.cpp -o checksumHonda

windows:
	i686-w64-mingw32-g++-win32 ${CFLAGS} -mconsole -lgdi32 -static checksumHonda.cpp -o checksumHonda.exe

clean:
	rm -rf checksumHonda
	rm -rf checksumHonda.exe
