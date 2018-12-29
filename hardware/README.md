# Interface Hardware

The Teletype data interface is a serial data connection using 20mA current loop.

Interfacing this to modern computers requires some hardware.  There are various options for this:
* Current loop to RS-232 serial.  This can be done with very simple electronics, and there are various commercially available
adapters.  But most computers nowadays don't use RS-232 either.
* Eric Volpe's (USB converter](http://heepy.net/index.php/USB-teletype)
* Build your own USB converter.

The one I built is described in more detail [here](../tty-usb.pdf).  It has two parts:
1. [Hardware](./ltspice/) for the current loop, connecting to a Teensy microcontroller programmed with Arduino,
2. [Software](../teensytty/) for the adapter, including some "advanced" terminal functions such as ANSI escape sequences.

