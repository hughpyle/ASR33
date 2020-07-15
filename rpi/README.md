# Connecting to  Raspberry Pi

There are several ways to physically connect a Teleytpe to a Raspberry Pi:
* Directly to the GPIO serial lines, or
* Via the Teensy USB interface, or
* Via a RS-232 adapter, and a RS232-USB cable.

For this I'm going via Teensy, because of the various
line-discipline things implemented there in firmware
(case conversion, and so on).  But the direct 
GPIO serial connection works fine. 
There are [many other hardware options](https://github.com/hughpyle/ASR33/blob/master/doc/04-connections.md) too.

The port name given to the Teletype by Linux will 
change depending on the connection method.  With a Teensy
it will be "/dev/ttyACM0".  GPIO will be "/dev/ttyAMA0".
With a RS232-to-USB cable it'll usually be "/dev/ttyUSB0",
but might vary.  You can see all the ports using `ls /dev/tty*`.
Adjust the port name below accordingly.


## getty on systemd

The "getty" is the program that sets up the terminal
connection to the port, and sends it to the login program
so that you can start an interactive shell.

To request a getty on the 'ttyACM0' device (using `systemd`
which is standard in recent versions of raspbian OS),
```
sudo systemctl start getty@ttyACM0.service
```

To have this start automatically at boot,
```
sudo systemctl enable getty@ttyACM0.service
```
Now a `reboot` should immediately print the login message at the console connected to the ttyACM0 device.

Note though, we didn't tell the getty to use 110 baud connection.  So this probably isn't enough yet.


### Auto-login and other parameters

Create a directory,
```
sudo mkdir /etc/systemd/system/getty@ttyACM0.service.d
```

Then create a file `/etc/systemd/system/getty@ttyACM0.service.d/override.conf` with
contents below, replacing `username` with the desired linux user that should
automatically be logged in, and making sure that `ttyACM0` matches the port you're using.
```
[Service]
Type=simple
ExecStart=
ExecStart=-/sbin/agetty --nohostname --autologin username --noclear ttyACM0 110 tty33
```
(Yes, there are two `ExecStart=` lines).

You can omit `--autologin` if you want to log in from the terminal.  But be careful,
the getty doesn't really handle lowercase usernames or passwords.  So auto-login is
just easier (although obviously less secure.  Someone might use the Teletype to exfil
all your secrets on paper tape).

The `tty33` is the terminal type (defined in `/lib/terminfo/`) and
gives you a plain terminal without escape sequences for colors.

The `110` baud rate isn't needed if you're going via a Teensy or Arduino that can present a
full-speed interface to the USB port.


### Customizing settings after login

After login, you can use `stty` to set custom terminal settings if needed.  For example,
you may want to set `stty brkint` for BREAK to send Ctrl+C to the host.  
With the custom kernel (below), you'll probably want to add to your `.profile` something like this:
```
stty ispeed 110 ospeed 110 icrnl xcase iexten ofill cr1
```


### Using a custom Linux kernel

Linux originated in the 1990s and was never built with Teletype support in mind.
So it's missing some of the features from original Unix that you will want for
a natural Teletype experience, including upper-case escape characters and
carriage-return delay.  You can [build a custom kernel that includes these features](https://github.com/hughpyle/ASR33/blob/master/rpi/kernel/README.md).


### Using custom terminfo with a Teensy or Arduino interface

[My Teensy firmware](../firmware) implements wordwrap, automatic CR for NL,
delays for NL and CR, and other features, controlled by escape sequences.  If you're using
that firmware, the best settings are

* Compile the [terminfo file](../firmware/terminfo.txt): `sudo tic terminfo.txt`
* Use `tty33-amx` instead of `tty33` in the getty override.conf `ExecStart=...` line


### Using udev rules for more flexibility

With `udev` rules, you can control the name of the tty device.  This is
especially useful if you have several USB devices, and you want some of
them to have a 'getty' but not others.

For example, one configuration I'm playing with is to connect the Teletype
via RS-232 (using the [DeRamp adapter](http://deramp.com/tty_adapter.html)
and a [StarTech USB cable](https://www.startech.com/Cards-Adapters/Serial-Cards-Adapters/USB-to-RS232-Serial-Adapter-Cable%7EICUSB232V2)),
but I also want to connect a [DECwriter III](https://twitter.com/33asr/status/1154155283054243840) to the same host, 
using a [FTDI cable](https://www.ftdichip.com/Products/Cables/USBRS232.htm). 

With a file `/etc/udev/rules.d/50-terminals.rules`, here are some rules that
distinguish between the terminals based on which cable is plugged in, 
regardless which USB port it's connected to:
```
# The PL2303-based serial-to-USB cable is for the Teletype
SUBSYSTEM=="tty", DRIVERS=="pl2303", SYMLINK+="ttyASR33"

# The FTDI-based serial-to-USB cable is for the DECwriter
SUBSYSTEM=="tty", DRIVERS=="ftdi_sio", SYMLINK+="ttyLA120"
```

Then the Teletype appears on `/dev/ttyASR33` and has `getty@ttyASR33.service`
to automatically log in; and the DECwriter always connects on `/dev/ttyLA120`
and has `getty@ttyLA120.service` to automatically log in to its own Unix
account.

