# Paper-Tape Patterns

This directory has a collection of "papertape pattern definition files".  You can use them to punch 8-level tape with bubbles, diamonds, grids, hearts, space invaders, Gray sequences, skulls, text in multiple fonts, and whatever else you can imagine.

The results are fun.

[![do not cross](../../pix/tape_donotcross_x300.jpg)](../../pix/tape_donotcross.jpg)
[![fade patterns](../../pix/tape_fade_x300.jpg)](../../pix/tape_fade.jpg)
[![all the fonts](../../pix/tape_fonts_x300.jpg)](../../pix/tape_fonts.jpg)
[![invaders](../../pix/tape_invaders_x300.jpg)](../../pix/tape_invaders.jpg)
[![hi score](../../pix/tape_invaders2_x300.jpg)](../../pix/tape_invaders2.jpg)
[![skulls](../../pix/tape_skulls_x300.jpg)](../../pix/tape_skulls.jpg)
[![valentine](../../pix/tape_valentine_x300.jpg)](../../pix/tape_valentine.jpg)
[![xmas wrap](../../pix/tape_xmas_x300.jpg)](../../pix/tape_xmas.jpg)
[![more invaders](../../pix/tape_book1_x300.jpg)](../../pix/tape_book1.jpg)
[![text messages](../../pix/tape_book2_x300.jpg)](../../pix/tape_book2.jpg)

### Generating the patterns

[This Python script](https://github.com/hughpyle/ASR33/blob/master/bin/pattern) reads a pattern-file and converts it to the binary message that punches the pattern on tape.
You may need to `pip install pillow click` before you can run it.

```bash
$ ./pattern --help
Usage: pattern [OPTIONS] PATTERN [WORDS]...

  Print patterns to punchtape.

Options:
  --font PATH  Font: 6x13, 6x13B, 6x13O, 7x13, 7x13B, 7x13O, cga, cgathin,
               chicago, cl, helv, lur12, lur8, mod3270, mod6x13, nex6x10,
               small, smallcaps, vt100
  --part TEXT  Write only one named part of a pattern-file
  --all        Write all the available parts in a pattern-file (slow!)
  --svg        Write SVG, not binary
  --test       Write text preview, not binary
  --list       List the available patterns
  --help       Show this message and exit.
```

For example, this prints out the pattern in a readable form on your terminal:
```
./pattern invaders --test
```

If you have a tape punch on `/dev/tty` you can run without "--test" to punch it:
```
./pattern invaders > /dev/tty
```

### Text on tape

The pattern named `text` can print words onto tape, using any of the bitmap fonts in the
[fonts directory](https://github.com/hughpyle/ASR33/blob/master/bin/fonts/).

For example,
```
pattern text --font vt100 'Tape is fun!' --test
```

The pattern file includes parts with some variations on shifting (moving the text baseline,
and whether to drop the 'sprocket hole' bit); for example
```
pattern text --part small 'Tape is fun!' --test
pattern text --part inverted 'Negative space' --test
```

For interactive printing, it's really convenient to just type at the keyboard and
have the letters punched immediately.  The `tapei` script does this.  Just run
```
tapei
```
and type anything;  interrupt with Ctrl+C or Ctrl+D to finish.  Optionally you can
specify a font name with `tapei --font`.


### Tape on paper 

To sketch out your own designs, send [this postScript file](template.ps) to your printer.

[![sketching template](../../pix/tape_template_x300.jpg)](../../pix/tape_template.jpg)

You can print "ready-made" patterns using the SVG output,
``` 
./pattern invaders --svg > file.svg && open file.svg
```
The resulting SVG looks like this,

[![invaders svg](../../pix/tape_invaders.svg)](../../pix/tape_invaders.svg)

---

For next-level reperforating: follow [ef1j95](https://twitter.com/ef1j95) on twitter.