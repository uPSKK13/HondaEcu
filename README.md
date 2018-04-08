## Hardware

The easiest way to talk to the ECU via the k-line is a USB to serial (TTL) converter,
and a serial to k-line converter. This code assumes you are using a FTDI based USB to
serial converter though others may work. I used a FTDI Friend from [Adafruit!](https://www.adafruit.com/product/284).
For the serial to k-line converter I used the schematic below since it contained no
special ICs, just common transistors and R/C components that I had laying around the house.

![kline_interface_1](http://pinoutguide.com/images/upload/pinout_117944425_image.png)

A much nicer looking k-line to serial converter that I plan on implementing next is
this one that uses one that uses optocouplers to keep the bike power isolated from
your electronics.

![kline_interface_2](http://projects.gonzos.net/wp-content/uploads/2017/04/CTX-kline-interface-1024x514.png)


## Tuning Software

* http://www.tunerpro.net
* http://www.romraider.com
* https://www.evc.de/en/product/ols/software


## General Resources

* http://forum.pgmfi.org/index.php
* http://ecuhacking.activeboard.com
* http://www.motorsport-brix.de
* http://projects.gonzos.net/ctx-obd


## Donation

If you found this project useful, please consider donating.

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=XL3H864LE567E)
