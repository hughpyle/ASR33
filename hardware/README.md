# Interface Hardware

The Teletype data interface is a serial data connection using 20mA current loop.

Connecting this to modern computers requires some hardware.  There are a few options:
* Current loop to RS-232 serial.  This can be done with very simple electronics, and there are various commercially available
adapters.  But most computers nowadays don't use RS-232 either.
* Eric Volpe's [USB converter](http://heepy.net/index.php/USB-teletype), which can also work with the 60mA loop on 5-level Teletypes,
* Build your own USB converter.

The one I built is described in more detail [here](../tty-usb.pdf).  It has two parts:
1. [Hardware](./ltspice/) for the current loop, connecting to a Teensy microcontroller programmed with Arduino,
2. [Software](../teensytty/) for the adapter, including some "advanced" terminal functions such as delays and ANSI escape sequences.

