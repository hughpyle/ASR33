# Experimental linux kernel support for Teletype ASR33 terminal

This adds kernel support for a few things that the
Teletype ASR33 (and other similar obsolete hardware)
need for usability:

* CRDLY (carriage-return delay) settings allowing
  time for the carriage to return before the next
  character is printed.  CR delays use two fills
  (`stty ofill cr1`, suitable for tty33 and tn300
  terminals) or four (`stty ofill cr2`, suitable
  for tty37 and ti700). Also `stty ofdel` fills
  with the DEL character instead of NUL.
* NLDLY (new-line delay) setting `nl1` similarly,
  adds two fill characters (NUL or DEL).
* XCASE so that you can distinguish between upper-
  and lower-case characters (the Teletype only has
  uppercase printing).  Prints uppercase characters
  prefixed with `\`.  On input, `\` indicates that
  the next character should be converted to uppercase.
  Normally this is used with: `stty icanon lcase`.

XCASE has special handling for common punctuation that is not
available in ASCII-63 terminals:
```
  \^  to  ~
  \!  to  |
  \(  to  {
  \)  to  }
  \'  to  `
```

Also, if ONLRET, newline performs the carriage-return function
and should also use the carriage-return delays.

This change is based on linux 4.19 kernel, by forking the Raspbian 10 tree (Buster).
It's had fairly limited testing on pi3 and pi4.  Patch and full file are in this directory.
There's a repo with these changes at [https://github.com/hughpyle/linux],
and you can see the diff [here](https://github.com/raspberrypi/linux/compare/rpi-4.19.y...hughpyle:teletype).

## Building

Building this kernel on a Raspberry Pi is really straightforward:

1. Install the tools and dependencies needed to build:
    ```bash
    sudo apt install git bc bison flex libssl-dev make
    ```
        
1. Check out a copy of [the forked repo](https://github.com/hughpyle/linux): 
    ```bash
    git clone --depth=1 https://github.com/hughpyle/linux
    ```

1. Configure the kernel, build and install, following the 
[instructions here](https://www.raspberrypi.org/documentation/linux/kernel/building.md).
Be sure to backup your `/boot` directory first, in case anything goes wrong.


## License

The contents of this directory are part of Linux and are
provided under the GNU General Public License version 2.
Outside this directory, other license terms apply.

