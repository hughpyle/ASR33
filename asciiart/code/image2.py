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

# TODO: use some triple-strike characters for very dark printing
# TODO: explore approaches to global optimization (be robust against deformation less than 1 character-size)

import sys
import json
import os
import numpy as np
import imageio
import io
import click
from skimage import feature, transform, color, exposure, util


# The character itself is 4x3
BROWS = 4
BCOLS = 3
CELLPX = 16

HOG_ORIENTATIONS = 8
VISUALIZE = False  # True

# How many overstrike passes
ROUNDS = 2

PREPARED_FILE = os.path.join(os.path.dirname(__file__), "chars_overstrike.json")


# Load and pre-process an image file
def load_image(filename, width, invert, gamma):
    # Read the image
    img = imageio.imread(filename)

    if img.shape[-1] == 4:
        # Blend the alpha channel
        img = color.rgba2rgb(img, background=(0, 0, 0))

    # Grayscale
    img = color.rgb2gray(img)

    # Adjust the exposure
    img = exposure.adjust_gamma(img, gamma)

    if invert:
        img = util.invert(img)

    # Resample and adjust the aspect ratio
    width_px = (3 * width) * CELLPX

    img_width = 1.0 * width_px
    img_height = int(img.shape[0] * 3 * (img_width / (4 * img.shape[1])))
    img = transform.resize(img, (img_height, img_width), anti_aliasing=True, mode='reflect')

    img = (img - img.min()) / (img.max() - img.min())
    return img


def process(image):
    (rows, cols) = image.shape
    cellsize = CELLPX

    # Make sure the image is a multiple of 3x5 x cellsize in both dimensions
    rn = cellsize * BROWS
    cn = cellsize * BCOLS
    newshape = (((rows + rn - 1) // rn) * rn, ((cols + cn - 1) // cn) * cn)
    if newshape != image.shape:
        image = np.resize(image, newshape)
        (rows, cols) = image.shape
    n_cells_row = int(rows // cellsize)  # number of cells along row-axis
    n_cells_col = int(cols // cellsize)  # number of cells along col-axis

    # Put a dot in the middle of each cell, so that the HOG
    # doesn't end up as exactly zero for areas with no gradient
    for iy in range(0, n_cells_row):
        for ix in range(0, n_cells_col):
            px = ix * cellsize
            py = iy * cellsize
            image[py + int(cellsize / 2), px + int(cellsize / 2)] += 0.001
            image[py + int(cellsize / 2), px + int(cellsize / 2)+1] += 0.001
            image[py + int(cellsize / 2)+1, px + int(cellsize / 2)] += 0.001
            image[py + int(cellsize / 2)+1, px + int(cellsize / 2)+1] += 0.001

    # HOG the whole image
    fd, img = feature.hog(image,
                          orientations=HOG_ORIENTATIONS,
                          pixels_per_cell=(cellsize, cellsize),
                          cells_per_block=(1, 1),
                          block_norm='L1',  # ''L2-Hys',
                          visualize=True,  # VISUALIZE,
                          feature_vector=False)

    # With 1x1 blocks we don't care about some of the fd dimensions
    # Remove them for easier coding
    fd = np.squeeze(fd)

    # Normalize each histogram to the luminance of the block it derived from
    for iy in range(0, n_cells_row):
        for ix in range(0, n_cells_col):
            px = ix * cellsize
            py = iy * cellsize
            cell = image[py: py + cellsize, px: px + cellsize]
            luminance = cell.mean()
            if VISUALIZE:
                hog_cell = img[py: py + cellsize, px: px + cellsize]
                hcm = hog_cell.mean()
                hog_cell *= luminance / (hcm + sys.float_info.epsilon)

            fd_cell = fd[iy, ix]
            fdm = fd_cell.mean()
            fd_cell *= luminance / (fdm + sys.float_info.epsilon)

    if VISUALIZE:
        # Normalize the image-of-HOG and save it just so we can see
        img *= 1 / img.max()
        imageio.imsave("hog.png", img)

    return fd


def render(fd, outfile, chars1, chars2, indent=0, title=None):
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

    # Retain only the character combinations for chars1/chars2
    if chars1:
        chars1 = " " + chars1
        chars = {k: v for k, v in chars.items() if k[0] in chars1}
    if chars2:
        chars2 = " " + chars2
        chars = {k: v for k, v in chars.items() if k[1] in chars2}

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

        if outfile != "-":
            print(line1 + " " + line2)

        # Don't forget to strip trailing spaces from each line, they just waste time!
        result.append(((" " * indent) + line1).rstrip() + "\r" + ((" " * indent) + line2).rstrip())

    # Write a text file with all the iterations
    if outfile == "-":
        outfile = 1

    if title is None:
        title = b"\r\n"

    with io.open(outfile, "wb") as f:
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write("\r\n".join(result).encode("utf-8"))
        f.write(b"\r\n")
        f.write(title)
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")
        f.write(b"\r\n")


@click.command()
@click.option('--width', default=66, help='Image width (characters)')
@click.option('--invert', is_flag=True, default=False, help='Invert colors')
@click.option('--gamma', default=1.0, help='Gamma correction')
@click.option('--indent', default=0, help='Indent with spaces')
@click.option('--chars1', help='Characters to use in the first layer')
@click.option('--chars2', help='Characters to use in the second layer')
@click.option('--title', help='Title text')
@click.option('--output', help='Output filename (use "-" for stdout)')
@click.argument('filename')
def main(filename, width, invert, gamma, indent, chars1, chars2, title, output):
    # Aspect ratio is determined by the input image.
    # Width is determined here.
    img = load_image(filename, width, invert, gamma)
    # imageio.imsave("test.jpg", img)

    # Analyze the image
    hog_fd = process(img)

    if title:
        # title is a string
        # center it, and make bytes
        title = " " * int(indent + (width - len(title))/2) + title
        title = title.encode("utf-8")

    # Map to ASCII
    if not output:
        output = filename + ".txt"
    render(hog_fd, output, chars1, chars2, indent, title)


if __name__ == "__main__":
    main()
