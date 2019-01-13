# Teletype Model 33 ASR

The [Teletype Model 33](https://en.wikipedia.org/wiki/Teletype_Model_33) was a very successful [computer terminal](https://en.wikipedia.org/wiki/Computer_terminal) in the late 1960s and 1970s.  It has an important historical role in several innovations, including the [ASCII  character set](https://en.wikipedia.org/wiki/ASCII) and the [development of Unix](https://homepage.cs.uri.edu/~thenry/resources/unix_art/ch02s01.html) and [BASIC](http://dtss.dartmouth.edu/).

[![teletype model 33](pix/20180925_170552_x400.jpg)](pix/20180925_170552.jpg)

### Some Background: ASCII, Unix and the ASR33

The history of the _teletypewriter_ – mechanical devices for digital communication – spans [from the earliest digital communications to global news and messaging networks](http://www.samhallas.co.uk/repository/telegraph/teletype_story.pdf).

With the Model 33 Teletype, *interactive terminals* became the standard UI for _minicomputers_ such as the [DEC PDP-8](https://www.computerhistory.org/revolution/minicomputers/11/331) and [PDP-11](https://dave.cheney.net/2017/12/04/what-have-we-learned-from-the-pdp-11) – also allowing multiple users to simultaneously work on the same computer! – and as affordable consoles for the first generation of _personal computers_ including the [Altair 8800](https://en.wikipedia.org/wiki/Altair_8800).


#### Terminal
A terminal consists of __data input__ and __data display__, connected to a computer system.   The teletype has a keyboard for input, and a printer for display.  The printer prints 72 characters per line on continuous-roll paper, and includes a bell (so that a typist can tell when nearing the end of a line, but also for notification).

#### Paper Tape
In the "ASR" (Automatic Send-Receive) Teletype models there are two additional I/O devices: a paper-tape reader for input, and a paper-tape punch for output.  [Punched paper tape](https://en.wikipedia.org/wiki/Punched_tape) is a great way to store and communicate data, although it's limited in capacity (10 characters per inch, or 2.66 kilometers per megabyte), slow (the Teletype can read/write at 10 bytes per second), and tears quite easily.

#### ASCII
The keyboard and printer use ASCII, which is a 7-bit character encoding [standardized in 1963](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.96.678&rep=rep1&type=pdf), with numbers, upper-case letters (no lowercase!), punctuation, and several _control characters_.  (Some of the punctuation is [unusual](https://twitter.com/33asr/status/1052956789086531584)).

An eighth data bit can be used for [parity](https://en.wikipedia.org/wiki/Parity_bit), depending on the exact model of Teletype keyboard.  The tape punch and reader can use all 8 bits.

[![ASCII printed by teletype](pix/ascii_print_x500.jpg)](pix/ascii_print.jpg) [![ASCII documentation](pix/ascii_table_x500.jpg)](pix/ascii_table.jpg)

#### Serial Data
The data connection is a serial [current loop](https://en.wikipedia.org/wiki/Digital_current_loop_interface) (two-wire system).  There are two independent current loops, one for "send" and another for "receive".  They are quite reliable over moderate distances (up to several kilometers), which is handy if your nearest computer is a long way away.

On the "send" (keyboard and tape reader), the teletype doesn't have any electronics!  The 8-bit parallel connections go to a [distributor](https://www.youtube.com/watch?v=E0T1zj1MuPc) with a rotating brush (driven by a motor and clutch) that make or break the current loop for each bit in turn.

On the "receive" side (printer and tape punch), the serial current loop is distributed to a set of solenoids that lift [codebars](https://www.youtube.com/watch?v=d-VPz2ZT0CQ) to move the print head and punch pins.  There's some electronics here: a simple solid-state amplifier from the 20mA loop to 500mA to drive the solenoids.

PCs generally used the [RS-232](https://en.wikipedia.org/wiki/RS-232) serial interface standard, which is based on voltage rather than current.  But this has itself been superseded by [USB](https://www.electronics-notes.com/articles/connectivity/usb-universal-serial-bus/standards.php).

The Model 33's data format – 1 start bit, 8 data bits and 2 stop bits – is simple, but obsolete.  By USB standards, a teletype is ridiculously slow; very few hardware interfaces (UARTs) can be found nowadays that will connect at the blazing speed of 10 characters per second (110 bits per second).

[![Serial data](pix/waveform_x300.jpg)](pix/waveform.jpg)


---

# This Project

In the early 1980s, I was lucky to attend a high-school that had a Teletype connected to the [PR1ME](https://en.wikipedia.org/wiki/Prime_Computer) cluster at the University of Surrey.  As user SCH008, this was my early gateway to the world of networked computers.  It's amazingly fun to revisit some of those experiences.

Although the Teletype hardware and [original Unix software](http://www.lemis.com/grog/Documentation/Lions/index.php) has been superseded by 50 years' of layered improvement, the hard-copy teletype is still the canonical `tty`.

This project is an ongoing exploration of how to use it with modern computers, including:
* The physical connection (current-loop serial to USB),
* The logical connection as a terminal (`getty`, the line discipline, and related things),
* Making the Unix commandline and essential software usable with a hard-copy terminal where "carriage return" takes hundreds of milliseconds, with no scroll-back, no "erase" or "clear", no back-space, no lower-case, no color, no graphics, and no cursor, 
* Connecting to today's information utilities,
* Connecting to vintage systems and simulations,
* Fun with printing and paper tape.
 
Follow along – and contribute please! – [here on GitHub](https://github.com/hughpyle/ASR33), and [@33asr on Twitter](https://twitter.com/33asr).

[![teletype ASR33 on pedestal](pix/20181014_101010_x500.jpg)](pix/20181014_101010.jpg)


---

* Initial project notes: [pdf](tty-usb.pdf) and [pptx](tty-usb.pptx).

* **[pix](pix)**: 
Photos and other pictures.

* **[hardware](hardware)**: 
Hardware for 20mA current loop send and receive.

* **[teensytty](teensytty)**:
Using a Teensy microcontroller for the ASR33-to-USB interface.

* **[osx](osx)**:
Setting up a getty on macOS.

* **[rpi](rpi)**:
Setting up a getty on Raspberry Pi (raspbian).

* **[bin](bin)**:
Some command-line utilities for the tty user.  Put this on your PATH.

* **[asciiart](asciiart)**:
Using the unique features of a hardcopy terminal, including _overstrike_, for [ASCII Art](https://en.wikipedia.org/wiki/ASCII_art).

* **[cups](cups)**:
Using [CUPS](https://en.wikipedia.org/wiki/CUPS) to make the Teletype appear as a network printer.

* **[other_material](other_material)**:
Related source documentation and reference material.


The contents of this project are published under the [MIT license](LICENSE).

---

I'm indebted to Wayne Durkee for bringing this machine back to life; Dave Tumey for recreated parts; to many Greenkeys list members and others for their inspiration and vast expertise.
