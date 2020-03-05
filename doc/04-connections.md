# Connecting to Computers

The Teletype Model 33 has always been used as a computer terminal.
But there are some challenges in connecting it to modern computers,
both due to the huge diversity of machines and operating systems, and
the fact that Teletypes have been obsolete for a *long* time.

For example, you'd expect that "the original Unix terminal" would easily
connect to a modern Linux server.  But Linux was written in the 90s and
had no need to fully support obsolete mechanical terminals.  You'll
find kernel code with comments such as [this](https://github.com/raspberrypi/linux/blob/rpi-4.19.y/drivers/tty/n_tty.c#L418):
```
 * Note that Linux currently ignores TABDLY, CRDLY, VTDLY, FFDLY
 * and NLDLY.  They simply aren't relevant in the world today.
 * If you ever need them, add them here.
```
Relevant or not, the Teletype still needs a delay after carriage-return
(CRDLY) to allow time for the carriage to return before the next
character prints.  Linux is open-source, [so I fixed it](../rpi/kernel/).
But with many systems it's necessary to handle these requirements some
other way.

## Connection Methods

For a usable connection, we need to deal with the electrical signal,
the data format, and the various idiosyncrasies of a Teletype:
* Electrically, the Teletype connection is a 20mA serial [current loop](https://en.wikipedia.org/wiki/Digital_current_loop_interface).
This can be a single loop ("half duplex"), or separate loops for send
and receive ("full duplex").
* The data format sends and receives each character in an 11-bit frame,
with one start bit, 8 data bits, and 2 stop bits.  Various Teletype
keyboards set the 8th bit in different ways: always off, always on, or
with odd or even [parity](https://en.wikipedia.org/wiki/Parity_bit). 
* This runs at 110 baud (10 characters per second). 
* The character set is ASCII-63, which has upper-case letters but not
lowercase.  Return and newline are separate keys.  There's no "tab" key.
Ideally your operating system should handle uppercase-only terminals and
still provide a way to edit mixed-case text and run mixed-case commands.
* Depending on your application, it might be useful to have software
support for automatic carriage-return, tab-stops, and even back-space. 
* The carriage return takes around 250 milliseconds, during which time you
shouldn't print any other characters.  Line-feed also takes some time. 

### Direct Current-Loop Connections

If you're lucky, the computer at hand supports all these natively, in
which case just connect the Teletype directly with a pair of cables.
If your computer is a PDP-11, or any other 70s minicomputer, there's a
good chance this will work.  Some rare PCs also have a current-loop
connection.

Note: the Teletype doesn't supply power for the loop.

[picture]

### RS-232 Connections

By the 80s, current-loop terminal interfaces largely disappeared in
favor of RS-232, which became the standard serial connection on PCs and
workstations until the early 2000s.  If you have a 25-pin (DB25) or
9-pin (DE9) serial port, all  that's needed is a current-loop to RS-232
adapter.

* The [DeRamp TTY adapter](https://deramp.com/tty_adapter.html) may be the most convenient of these.  It plugs
dircetly into the Molex connectors on the Teletype control unit, and
has a RJ-11 socket for 4-wire "telephone-cord" connection.  At the
computer end, just use a DE9 or DB25 [RJ11 modular adapter](https://www.amazon.com/gp/product/B07QVFGLNY/)
and plug in to the serial port.
* It's also quite straightforward to build your own RS-232 adapter.  The
  "[simplest loop](../hardware/simplest_loop)" and other
  [very simple circuits](https://wiki.theretrowagon.com/wiki/20ma_current_loop_to_RS-232_conversion)
  use less than a dozen components.
* More complex circuits generally use opto-isolators to electrically 
  separate the Teletype loop from the computer.  For example the
  [DEC VT100 interface](../hardware/VT100_RS232_loop_adapter.pdf) is
  fairly readable.
* Many other commercial adapters are available.  You'll want one that
  includes a "loop supply", i.e. that can provide the loop current.

[picture]

RS-232 is also the simplest hardware connection to a Raspberry Pi or
similar development board.  The Raspberry Pi GPIO connector has serial
data lines at 5V (TTL) voltage, and a [RS-232 level shifter](https://www.sparkfun.com/products/449)
can be used to adapt the RS-232 voltages very easily.  Note that
Raspbian or other Linux still needs a [custom kernel patch](../rpi/kernel/)
to properly handle upper/lower case and CR/LF delays. 

[picture]

### USB Connections

You can connect with USB, using a RS-232 to USB
adapter or cable.  But not all USB adapters can run as slow as 110 baud,
so be careful to check the specs.
* Adapters based on Prolific PL2303, such as [this StarTech cable](https://www.amazon.com/gp/product/B003WOWBBW/),
work well.  Depending on your computer, the OS might need a driver. 
* Adapters based on FTDI FT232RQ, such as [this Sabrent cable](https://www.amazon.com/gp/product/B006AA04K0/),
do **not** work at serial speeds lower than 300 baud. 

[picture]

I took the approach of building my own current-loop to USB interface
using a Teensy microcontroller.  This makes for a very flexible solution
because most of the software issues (delays, case conversion) can be
handled in Arduino code on the microcontroller, and the computer just
thinks it's talking to a modern terminal.
* More details about this custom hardware
* Alternatives [Volpe](https://teletype.net/display/TEL/Volpe+USB+Interface+Board)
* Other alternatives

[picture]

### WiFi

Finally, an option that's worth exploring:  directly to WiFi.

ESP8266 board (like this one)[https://www.amazon.com/gp/product/B010O1G1ES]

[picture]
