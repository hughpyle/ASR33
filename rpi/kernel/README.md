# Experimental linux kernel support for Teletype ASR33 terminal

This adds kernel support for a few things that the
Teletype ASR33 (and other similar obsolete hardware)
need for usability:

* CRDLY (carriage-return delay) settings allowing
  time for the carriage to return before the next
  character is printed.  With `stty ofill cr3`, the
  output after a CR has 3 nulls added.  Similarly for
  cr2, cr1.  Also `stty ofdel` fills with the DEL
  character instead of NUL.
* NLDLY (new-line delay) setting `nl1` similarly.
* XCASE so that you can distinguish between upper-
  and lower-case characters (the Teletype only has
  uppercase printing).  Prints uppercase characters
  prefixed with `\`.  On input, `\` indicates that
  the next character should be converted to uppercase.
  Normally this is used with: `stty icanon lcase`.

This change is based on linux 4.19 kernel,
Raspbian 10 (Buster).  Limited testing on a pi4.
Patch and full file are in this directory.
There's a repo with these changes at
[https://github.com/hughpyle/linux]

Building this kernel on a Raspberry Pi is really
straightfoward; just follow the instructions at
[https://www.raspberrypi.org/documentation/linux/kernel/building.md]


