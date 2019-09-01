# Connecting to  Raspberry Pi

There are several ways to physically connect a Teleytpe to a Raspberry Pi:
* Directly to the GPIO serial lines, or
* Via the Teensy USB interface, or
* Via a RS-232 adapter, and a RS232-USB cable.

For this I'm going via Teensy, because of the various
line-discipline things implemented there in firmware
(case conversion, and so on).  But I think the direct 
GPIO serial connection should work fine too.  In that
case the port would be ttyAMA0 instead of ttyACM0 below.

You can see all the ports using `ls /dev/tty*` 

## getty on systemd

Recent versions of raspbian use `systemd`.
To request a getty on the 'ttyACM0' device,
```
sudo systemctl start getty@ttyACM0.service
```

To have this start automatically at boot,
```
sudo systemctl enable getty@ttyACM0.service
```
Now a `reboot` should immediately print the login message at the console connected to the ttyACM0 device.

You can see all the getty properties using
```
sudo systemctl show getty@ttyACM0.service
```


### Auto-login

Create a directory,
```
sudo mkdir /etc/systemd/system/getty@ttyACM0.service.d
```

Then create a file `/etc/systemd/system/getty@ttyACM0.service.d/override.conf` with
contents below, replacing `userename` with the desired linux user that should
automatically be logged in:
```
[Service]
Type=simple
ExecStart=
ExecStart=-/sbin/agetty --nohostname --autologin username --noclear ttyACM0 tty33
```
(Yes, there are two `ExecStart=` lines).
The `tty33` is the terminal type (defined in `/lib/terminfo/`) and
gives you a plain terminal without escape sequences for colors.

You may need to set `stty brkint` for BREAK to send Ctrl+C to the host.


### Using custom terminfo

The [Teensy firmware](../firmware) implements wordwrap, automatic CR for NL,
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

