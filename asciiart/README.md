# ASCII Art

I've been experimenting with various ways to create Teletype-printed images.

Here's some Python code for an approach that provides quite high-resolution rendering, and uses the full Teletype character set (no underscores!) with overstrike for solid color.

This approach is really more complicated than necessary.  You could get very similar results with a much simpler approach.  But I wanted to learn some numpy and skimage, and the results are fun :)  
## Preparation
First I printed out and scanned a table of all the combinations of overstrike characters.  The table is symmetrical about the diagonal, but that doesn't matter for the processing.
```
python image2.py --table
```  
[![overstrike](chars_overstrike_x500.jpg)](chars_overstrike.jpg)

Then, some code reads this image, pulls out each character-sized box, and analyzes it using a [Histogram of Oriented Gradients](http://scikit-image.org/docs/dev/auto_examples/features_detection/plot_hog.html) (HOG).  Actually, each character box is subdivided into 3x4 squares, and the HOG is calculated for each "pixel".  The results are saved in a [data file](chars_overstrike.json).
```
python prep_overstrike.py
```

## Processing a picture

To process a picture, it's resized to a multiple of 198 pixels (66 characters, 3 "sub-character pixels" per character), and analyzed using the HOG algorithm.

Then, each block in the image's HOG is matched to the blocks in the data.  The best match is the character that's not too dark, and that has the best correlation between the pair of histograms.

This gives us the best-matching overstrike character pair.  Finally, the results are collected into two lines of text for each row of the result.  The first line is printed, then a CR (carriage return) without a linefeed, then the second line, then CR+LF.

```
$ python image2.py --help
Usage: image2.py [OPTIONS] FILENAME

Options:
  --width INTEGER   Image width (characters)
  --invert          Invert colors
  --gamma FLOAT     gamma
  --indent INTEGER  indent
  --help            Show this message and exit.
```
[![Salvador Dali](dali_x500.jpg)](dali.txt.jpg)  

 
### Other resources

There's a large selection of historical "text art" on [textfiles.com](http://www.textfiles.com/art/).  Some of this is drafted by hand, and some by computer.  In the RTTY collection (images sent over radio-teletype) and the DECUS collection (images from the minicomputer scene) you'll find several that use overstrike, including the famous [Mona Lisa](http://textfiles.com/art/DECUS/mona_lisa_2.txt).  Some of these are for 132-column lineprinters.

To print lettering, use `figlet` ([http://www.figlet.org/](http://www.figlet.org/)).

 