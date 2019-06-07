# ASCII Art with Overstrike

[![Salvador Dali](misc_pictures/dali_x500.jpg)](misc_pictures/dali.txt.jpg)  

I've been experimenting with various ways to print graphics on the [Teletype ASR33 terminal](https://github.com/hughpyle/ASR33).  

Teletype printed art is more constrained than ANSI- or ASCII-Art on modern machines, since there's no color, no block-graphic or line-graphic characters, no lowercase, and quite a limited set of punctuation (missing the underscore, vertical-bar, curly braces, etc.)  On the other hand, as a hardcopy printer, we can overtype multiple characters at the same location.


These experiments cover a few ways to convert a graphic image into a text image:

* Convert the source image to grayscale, then match each part of the image to the **luminance** of a printed character.  For example, a sorted list of the Teletype characters by printed weight (e.g. `'.-,/^_\)+><(!";=1:?][J7I*YLT35CV49FO6D#AZUGS02$%P&WXEQH8B@KRNM`) can be mapped onto grayscale image luminance.  The weights of the printed characters don't make a linear luminance scale, so it can be better to use just a subset of the available characters (e.g. ` '-/<JIY3OPHKM`).  
* Add **overstrike**.  The teletype can print a line of text, then CR, then overprint, and this can be repeated several times to put a lot of ink on the paper.  Of course there are gaps in the final print even with heavy overstrike, because it's not possible to print between the lines or between the characters.
* Divide each printed character, and each region of the image, into several **sub-character pixels** so that (for example) `,` or `'` would be selected differently even if they had the same printed weight.  This can produce noticeably more realistic images for the same amount of printing.
* Analyze the **orientation of gradients** and edges in the image and the printed character.  For example, ` / ` and ` \ ` would be selected to match the direction of an edge.  Again this can help to produce clearer prints of complex images.  This step is quite compute-heavy and probably gives marginal benefit over subpixel luminance, but it was a fun coding challenge (and a good way to learn numpy and scikit-image)!

[Here's some Python code](https://github.com/hughpyle/ASR33/blob/master/asciiart/code/image2.py) that includes all of these aspects, and provides (relatively!) quite high-resolution rendering.
  
Printing is slow and noisy.  A full-page image is around 8KB and can take up to 15 minutes to print.


## Preparation

First I printed out and scanned a table of all the two-character overstrike combinations.  The first column, and the first row, are overstrike with space, i.e. single-strike characters.  The table is symmetrical about the diagonal, but that doesn't matter for the processing.
```
python prep_overstrike.py --table
```  
[![overstrike](misc_pictures/chars_overstrike_x500.jpg)](code/chars_overstrike.jpg)

Then, [some code](code/prep_overstrike.py) reads this image, pulls out each character-sized box, and analyzes it using a [Histogram of Oriented Gradients](http://scikit-image.org/docs/dev/auto_examples/features_detection/plot_hog.html) (HOG).  Actually, each character box is subdivided into 3x4 squares, and the HOG is calculated for each "pixel".  The results are saved in a [data file](code/chars_overstrike.json).

```
python prep_overstrike.py
```

Small distortions in the print and scan result in some misalignments to the rectangular block for each character.  Future work would improve the way that each printed character is found in the scanned table.

## Processing a picture

[![björk - debut](album_covers/album_debut_250.jpg)](album_covers/album_debut.txt.jpg)
[![primal scream - screamadelica](album_covers/album_screamadelica_250.jpg)](album_covers/album_screamadelica.txt.jpg)
[![clash - london calling ](album_covers/album_clash_250.jpg)](album_covers/album_clash.txt.jpg)
[![lamb - fear of fours](album_covers/album_fours_250.jpg)](album_covers/album_fours.txt.jpg)
[![john coltrane - blue train](album_covers/album_bluetrain_250.jpg)](album_covers/album_bluetrain.txt.jpg)
[![led zeppelin](album_covers/album_ledzep_250.jpg)](album_covers/album_ledzep.txt.jpg)

The [code to process a picture](code/image2.py) first resizes to a multiple of 198 pixels (66 characters print width by default, and 3 "sub-character pixels" per character), then analyzes each block using the HOG algorithm.

Then, each block in the image's HOG is matched to the blocks in the data.  The best match is the character that's not too dark, and that has the best correlation between the pair of histograms.

This gives us the best-matching overstrike character pair.  Finally, the results are collected into two lines of text for each row of the result.  The first line is printed, then a CR (carriage return) without a linefeed, then the second line, then CR+LF.

```
$ python image2.py --help
Usage: image2.py [OPTIONS] FILENAME

Options:
  --width INTEGER   Image width (characters)
  --invert          Invert colors
  --gamma FLOAT     Gamma correction
  --indent INTEGER  Indent with spaces
  --help            Show this message and exit.
```

For complex images, you may need to experiment with contrast and gamma correction for best results.

[![Minion](misc_pictures/minion_x500.jpg)](misc_pictures/minion.txt.jpg)  


### Try it yourself

If you don't have a vintage hardcopy printer that can over-strike, it's still pretty easy to run this code and print with modern equipment.  Using [enscript](https://www.gnu.org/software/enscript/):
```
enscript -l --output page.ps album_screamadelica.jpg.txt
```
The resulting PostScript file `page.ps` can be viewed or printed, and should look pretty close to the renderings you see on this page.  If you install the [Teletype-based font](https://www.dafont.com/teletype-1945-1985.font) you may be able to get `enscript` to render a very close analog.


## Other resources

There's a large selection of historical text art on [textfiles.com](http://www.textfiles.com/art/).  Some of this is drafted by hand, and some with the help of a computer.  In the RTTY collection (images sent over radio-teletype) and the DECUS collection (images from the minicomputer scene) you'll find several that use overstrike, including the famous [Mona Lisa](http://textfiles.com/art/DECUS/mona_lisa_2.txt).  The larger images are for 132-column lineprinters (the Teletype only has 72 characters per line), and even for multiple pages horizontally.  [Here's a short interview](http://q7.neurotica.com/Oldtech/ASCII/) with Samuel Harbison, who pioneered this stuff at Princeton in the early 70s.  Another archive of material, including Harbison's files for Buzz Aldrin, Spock, and others (in EBCDIC and ASCII), can be found on [David Gesswein's PDP-8 site](http://www.pdp8online.com/ftp/ascii_art/).

Thanks to discussions on [Show HN](https://news.ycombinator.com/item?id=19040389) I've learned that ASCII-art generators with better effective resolution than the character-level luminance approach are quite actively studied.
For example: Wang et al. (2004) - [Image quality assessment: From error visibility to structural similarity](http://www.cns.nyu.edu/pub/lcv/wang03-preprint.pdf) introduced a [Structutred Similarity Index Metric](http://en.wikipedia.org/wiki/Structural_similarity) (SSIM), which shows good results.
Later, Xu al. (2010) - [Structure-based ASCII Art](https://www.cse.cuhk.edu.hk/~ttwong/papers/asciiart/asciiart.html) go further, building very compact ASCII renderings from line-art.  The [PixLab](https://art.pixlab.io/) project uses a trained classifier to render at video speed.
And recently, Fujisawa et el. (2017), and  Matsumoto et al. (2018) - [ASCII Art Classification based on Deep Neural Networks](http://www.jsoftware.us/vol13/355-SE3002.pdf) use the Histogram of Oriented Gradients (HOG) together with a neural-network based classifiers to get really good quality.
So, my little HOG retrocomputing project is accidentally almost state-of-the-art (-_-)  

[Akiyama (2017)](https://github.com/OsciiArt/DeepAA) is using convolutional NN trained on hand-drawn ASCII art to make some really amazing images.  Take a look.  

`jp2a` ([https://csl.name/jp2a/](https://csl.name/jp2a/)) is a simple fast tool for converting images to text.  It supports ANSI color effects and HTML output, and is quite good for plaintext.  As far as I can tell it doesn't do overstrike.

To print lettering, use `figlet` ([http://www.figlet.org/](http://www.figlet.org/)).  It has a vast collection of fonts, although many of them rely on the underscore, which isn't present on the Teletype printwheel.

I'll be posting occasional updates on [twitter](https://twitter.com/33asr).  

[![emoji shark](emoji/framed_emoji_shark_x250.jpg)](https://raw.githubusercontent.com/hughpyle/ASR33/master/asciiart/emoji/framed_emoji_shark.jpg)
[![emoji apple](emoji/framed_emoji_apple_x250.jpg)](https://raw.githubusercontent.com/hughpyle/ASR33/master/asciiart/emoji/framed_emoji_apple.jpg)
[![emoji fish](emoji/framed_emoji_fish_x250.jpg)](https://raw.githubusercontent.com/hughpyle/ASR33/master/asciiart/emoji/framed_emoji_fish.jpg)
 
You can buy prints on [my Etsy store](https://www.etsy.com/shop/asr33).

