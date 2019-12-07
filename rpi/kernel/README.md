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

This change is based on linux 4.19 kernel,
Raspbian 10 (Buster).  Limited testing on a pi4.
Patch and full file are in this directory.
There's a repo with these changes at
[https://github.com/hughpyle/linux]

Building this kernel on a Raspberry Pi is really
straightforward; just follow the instructions at
[https://www.raspberrypi.org/documentation/linux/kernel/building.md]

## License

The contents of this directory are part of Linux and are
provided under the GNU General Public License version 2.
Outside this directory, other license terms apply.

