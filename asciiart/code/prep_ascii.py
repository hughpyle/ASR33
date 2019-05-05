#!/usr/bin/env python
# Copyright (c) Hugh Pyle 2018.   MIT license.

"""Play with some images

This is the single-character version.
The map is a scan of the printed table of all the ASCII-63 teletype characters.

Reads characters from the map.
Calculates luminance and gradient histograms.
Writes them all to a JSON file that can be used for rendering later.

"""

import sys
import json
import numpy as np
import imageio
import io
import click
from skimage import feature, exposure, transform


# Aspect ratio for Teletype characters (full cell, not just the printed region)
# is 5x3, so we break down the histogram into sub-characters for histogram and luminance matching
# The character itself is 4x3
BROWS = 4
BCOLS = 3

# This image is from a 600dpi flatbed scan, which makes for nice round numbers (and a flat image)
SCALE = 3
CHARS_LEFTMARGIN =  SCALE * 318
CHARS_COLUMNWIDTH = SCALE * 601
CHARS_TOPMARGIN =   SCALE * 306
CHARS_ROWHEIGHT =   SCALE * 100
CHARS_CHARWIDTH =   SCALE * 60

loaded_files = {}

# Which character from the 5 available?
INDEX = 2


# Load and cache an image file, normalized as float, inverted
def load_image(filename):
    if filename in loaded_files:
        return loaded_files[filename]
    img = imageio.imread(filename, as_gray=True).astype(np.float)

    # Normalize the whole image
    # img *= 1.0/(img.max() - img.min())
    img = (img - np.min(img))/np.ptp(img)

    # Normalize on a sigmoid curve to better separate ink from paper
    k = 10
    img = np.sqrt(1 / (1 + np.exp(k * (img - 0.5))))

    loaded_files[filename] = img
    return img


# Pull out the image of a single character.
# Each character has multiple images, specify index (0-5) to choose one
def chars_image(c, index=0, count=1):
    oc = ord(c)
    if oc < ord(' '):
        return None
    if oc > ord('_'):
        return None

    row = (oc - ord(' ')) % 16
    column = int((oc - ord(' ')) / 16)

    pixX = CHARS_LEFTMARGIN + (CHARS_COLUMNWIDTH * column) + (index * CHARS_CHARWIDTH)
    pixY = CHARS_TOPMARGIN + (CHARS_ROWHEIGHT * row)

    # Get the full original image
    full_image = load_image("chars_ascii.jpg")

    char = full_image[pixY: pixY + CHARS_ROWHEIGHT, pixX: pixX + count * CHARS_CHARWIDTH]

    # invert so ink>paper
    # char = 1 - char

    return char


# Calculate the average luminance for a character
def luminance(image):
    return np.mean(image)


# Calculate the HOG for a character (as a single histogram)
def hog_char(image, count, luminance):
    rows = image.shape[0]
    cols = image.shape[1]
    rows_cellsize = int(image.shape[0]/BROWS)
    cols_cellsize = int(image.shape[1]/BCOLS)
    fd, img = feature.hog(image,
                          orientations=8,
                          pixels_per_cell=(rows_cellsize, cols_cellsize),  # (16, 16),
                          cells_per_block=(1, 1),
                          block_norm='L2-Hys',
                          visualize=True,
                          feature_vector=False)

    # With 1x1 blocks we don't care about some of the fd dimensions
    # Remove them for easier coding
    fd = np.squeeze(fd)

    # Normalize each histogram to the luminance of the block it derived from
    n_cells_row = int(rows // rows_cellsize)  # number of cells along row-axis
    n_cells_col = int(cols // cols_cellsize)  # number of cells along col-axis

    for iy in range(0, n_cells_row):
        for ix in range(0, n_cells_col):
            px = ix * cols_cellsize
            py = iy * rows_cellsize
            # cell = image[py: py + rows_cellsize, px: px + cols_cellsize]
            # luminance = cell.mean()

            hog_cell = img[py: py + rows_cellsize, px: px + cols_cellsize]
            hog_cell *= luminance / (hog_cell.mean() + sys.float_info.epsilon)

            fd_cell = fd[iy, ix]
            fd_cell *= luminance / (fd_cell.mean() + sys.float_info.epsilon)

    return (fd, img)


def analyze_table_image():
    # (Later: run this over all 5 of the char instances)

    luminances = {}

    # Find the minimum bounding-box for each character
    rowbounds = [1e10, 0]
    colbounds = [1e10, 0]
    for i in range(ord(' '), ord('_')+1):
        c = chr(i)
        img = chars_image(c, index=INDEX)
        luminances[c] = img.mean()
        if c != ' ':
            edges = np.unravel_index(np.argmax(img > 0.4, axis=None), img.shape)
            if edges[0] < rowbounds[0]:
                rowbounds[0] = edges[0]
            if edges[1] < colbounds[0]:
                colbounds[0] = edges[1]
            flp = np.flip(img)
            edges = np.unravel_index(np.argmax(flp > 0.4, axis=None), img.shape)
            if img.shape[0] - edges[0] > rowbounds[1]:
                rowbounds[1] = img.shape[0] - edges[0]
            if img.shape[1] - edges[1] > colbounds[1]:
                colbounds[1] = img.shape[1] - edges[1]
            edges = None

    # characters sorted by increasing luminance
    sl = sorted(luminances, key=luminances.get)

    # Normalize all the luminances.
    # We want to reduce the difference between the smallest (lightest printable character, e.g. apostrophe) and space,
    # otherwise the resulting image gets too much whitespace.  So the minimum and slope take this into account.
    minl = luminances[sl[0]]    # zero-point (space)
    manl = luminances[sl[1]]    # lightest-printable
    maxl = luminances[sl[-1]]   # darkest
    fudg = 0.05                 # where we want the lightest-printable to be
    for c in sl:
        if luminances[c] == minl:
            luminances[c] = 0
        else:
            # manl => fudg
            # maxl => 1.0
            luminances[c] = fudg + ((luminances[c] - manl)*(1.0 - fudg) / (maxl - manl))

    for c in sl:
        print("\"{}\", {}".format(c, luminances[c]))

    bylum = "".join(sl)
    print(bylum)

    # calculate the HOG for each character
    fds = {}
    chars = []
    images = []
    for i in range(ord(' '), ord('_')+1):
        c = chr(i)

        img = chars_image(c, index=INDEX)
        char = img[rowbounds[0]: rowbounds[1], colbounds[0]: colbounds[1]]
        chars.append(char)
        (fd, image) = hog_char(char, 1, luminances[c])

        fds[c] = fd.tolist()
        images.append(image)

    # Save a combined image of HOGs
#    im = np.concatenate(tuple(images))
#    im *= 1 / im.max()
#    imageio.imsave("ascii.jpg", im)

    # Save a conbined image of characters
#    im = np.concatenate(tuple(chars))
#    im *= 1 / im.max()
#    imageio.imsave("ascii1.jpg", im)

#    im = np.concatenate(tuple(chars), axis=1)
#    im *= 1 / im.max()
#    imageio.imsave("ascii2.jpg", im)

    # Save the JSON
    with io.open("chars_ascii.json", "w") as afile:
        json.dump(fds, afile, indent=2)


def print_table():
    # Print the ASCII characters table.
    print("\n\n\n")
    print("\n\nASCII character table\n\n")

    data = []
    for p in range(0, 0x10):
        data.append("")

    for c in range(0x20, 0x60):
        index = c % 0x10
        s = data[index]
        s = s + "     {}".format(chr(c) * 5)
        data[index] = s

    for s in data:
        print(s)
    print("\n\n\n")


@click.command()
@click.option('--table', is_flag=True, default=False, help='Print the character table')
def main(table):
    if table:
        print_table()
    else:
        analyze_table_image()


if __name__ == "__main__":
    main()



