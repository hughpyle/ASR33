#!/usr/bin/env python
# Copyright (c) Hugh Pyle 2018.   MIT license.

"""Print an image using ASCII text.

This implements a "sub-character" matching scheme using a "histogram of oriented gradients" (HOG)
for each ASR53 printable character (uppercase ASCII, no lowercase).  The histogram data is prepared separately.

The ASR33 has 0.1" character pitch horizontally and 0.16" vertically
For a "small" square print we want the target width=32 and height=20 characters.

Each character has been analyzed as 3x4 blocks.
For consistent performance we resize the original image to 16x16 for each cell of those blocks.

Here
- read the input image as grayscale
- resize to the target resolution (3px per character horizontally, 5px per character vertically)
- Compute HOG for this image
- For each character-sized block, find the best matching character-pair from the json dataset
  (which contains HOGs for each combination of characters, from a scanned overprint image)
- Repeat several times to allow for overprint.

A simple matching algorithm is: "minimum of histograms" aka "intersection of histograms", which is just
sum{fifteen histograms per block}( sum{8 bins per histogram}( min(image_histogram[i], character_histogram[i]) ))
then choose the character with the largest result.

Maybe try others if that doesn't look so good (e.g. results in too much ink), e.g.
correlation instead of min().

Take care that empty image regions pick the "space" character!
"""

import sys
import json
import numpy as np
import imageio
import io
import click
from skimage import feature, transform, color, exposure


# The character itself is 4x3
BROWS = 4
BCOLS = 3


HOG_ORIENTATIONS = 8
VISUALIZE = True

# How many overstrike passes
ROUNDS = 2

PREPARED_FILE = "chars_overstrike.json"


# Load and pre-process an image file
def load_image(filename, width, invert, gamma):
    # Read the image
    img = imageio.imread(filename)

    if img.shape[-1] == 4:
        # Blend the alpha channel
        img = color.rgba2rgb(img)

    # Grayscale
    img = color.rgb2gray(img)

    # Resample and adjust the aspect ratio
    width_px = (3 * width) * 16

    img_width = 1.0 * width_px
    img_height = int(img.shape[0] * 3 * (img_width / (4 * img.shape[1])))
    img = transform.resize(img, (img_height, img_width), anti_aliasing=True, mode='constant')

    # Asjust the exposure
    img = exposure.adjust_gamma(img, gamma)

    if invert:
        img = 1 - img

    return img


def process(image):
    (rows, cols) = image.shape
    cellsize = 16

    # Make sure the image is a multiple of 3x5 x cellsize in both dimensions
    rn = cellsize * BROWS
    cn = cellsize * BCOLS
    newshape = (((rows + rn - 1) // rn) * rn, ((cols + cn - 1) // cn) * cn)
    if newshape != image.shape:
        image = np.resize(image, newshape)

    # HOG the whole image
    fd, img = feature.hog(image,
                          orientations=HOG_ORIENTATIONS,
                          pixels_per_cell=(cellsize, cellsize),
                          cells_per_block=(1, 1),
                          block_norm='L2-Hys',
                          visualize=VISUALIZE,
                          feature_vector=False)

    # With 1x1 blocks we don't care about some of the fd dimensions
    # Remove them for easier coding
    fd = np.squeeze(fd)

    # Normalize each histogram to the luminance of the block it derived from
    n_cells_row = int(rows // cellsize)  # number of cells along row-axis
    n_cells_col = int(cols // cellsize)  # number of cells along col-axis
    for iy in range(0, n_cells_row):
        for ix in range(0, n_cells_col):
            px = ix * cellsize
            py = iy * cellsize
            cell = image[py: py + cellsize, px: px + cellsize]
            luminance = cell.mean()
            if VISUALIZE:
                hog_cell = img[py: py + cellsize, px: px + cellsize]
                hog_cell *= luminance / (hog_cell.mean() + sys.float_info.epsilon)

            fd_cell = fd[iy, ix]
            fd_cell *= luminance / (fd_cell.mean() + sys.float_info.epsilon)

    if VISUALIZE:
        # Normalize the image-of-HOG and save it just so we can see
        img *= 1 / img.max()
        imageio.imsave("hog.png", img)

    return fd


def render(fd, outfile, indent=0):
    # The fd is a histograms-of-gradients
    n_cells_row = fd.shape[0]
    n_cells_col = fd.shape[1]

    # Load the previously-prepared histograms for the print characters.
    # This is structured as a dictionary, indexed by character-pair, with each value being
    # {
    # "XY": [
    #       [
    #        [ ... 8 histogram values ...],
    #       ]
    #      ],
    # }
    with open(PREPARED_FILE, "rb") as data:
        chars = json.load(data)

    # Make as numpy
    for c in chars.keys():
        chars[c] = np.array(chars[c])

    charlums = {c: chars[c].mean() for c in chars.keys()}

    result = []
    # Look at each 3x5 block in the HOG and match it to the best 3x5 block in the chars.
    # (There's probably some numpy way to do this all at once, which would improve perf)
    for iy in range(0, n_cells_row, BROWS):
        line1 = ''
        line2 = ''
        for ix in range(0, n_cells_col, BCOLS):
            fd_cell = fd[iy: iy+BROWS, ix: ix+BCOLS]
            mean = fd_cell.mean()

            best = 1e10
            char = '  '
            for c in chars.keys():
                if mean >= charlums[c]:
                    # Correlation: L2 distance
                    corr = np.linalg.norm(chars[c] - fd_cell)
                    # print("{}: {} = {}: {}".format(c, chars[c].shape, fd_cell.shape, corr))
                    if corr < best:
                        best = corr
                        char = c

            line1 = line1 + char[0]
            line2 = line2 + char[1]

        print(line1 + " " + line2)
        result.append((" " * indent) + line1 + "\r" + (" " * indent) + line2)

    # Write a text file with all the iterations
    with io.open(outfile, "wb") as f:
        f.write("\r\n".join(result).encode("utf-8"))
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")


@click.command()
@click.option('--width', default=70, help='Image width (characters)')
@click.option('--invert', is_flag=True, default=False, help='Invert colors')
@click.option('--gamma', default=1.0, help='gamma')
@click.option('--indent', default=0, help='indent')
@click.argument('filename')
def main(filename, width, invert, gamma, indent):
    # Aspect ratio is determined by the input image.
    # Width is determined here.
    img = load_image(filename, width, invert, gamma)
    imageio.imsave("test.jpg", img)

    # Analyze the image
    hog_fd = process(img)

    # Map to ASCII
    render(hog_fd, filename + ".txt", indent)


if __name__ == "__main__":
    main()
