#!/usr/bin/env python
# Copyright (c) Hugh Pyle 2018.   MIT license.

"""Play with some images

This is the 2D (overstrike) version.
The map is a scan of the printed table of all the overstrike combinations

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
from skimage import feature, transform


# Aspect ratio for Teletype characters (full cell, not just the printed region)
# is 5x3, so we break down the histogram into sub-characters for histogram and luminance matching
# The character itself is 4x3
BROWS = 4
BCOLS = 3

# This image is from a 600dpi flatbed scan, which makes for nice round numbers (and a fairly flat image).
# Requires some rotation (there's still some residual distortion from the print or the scan, but it's close).
ROTATION = 3.145
SHEAR = -0.007
TRANSLATION = (5088, 8400)
SCALE = 1
CHARS_LEFTMARGIN =  SCALE * 519  # 59
CHARS_TOPMARGIN =   SCALE * 1405  # 75
CHARS_ROWHEIGHT =   SCALE * 99.1
CHARS_CHARWIDTH =   SCALE * 60.0

STARTCHAR = 0x20
ENDCHAR = 0x5f

loaded_files = {}


# Load and cache an image file, normalized as float, inverted
def load_image(filename):
    if filename in loaded_files:
        return loaded_files[filename]
    img = imageio.imread(filename, as_gray=True).astype(np.float)

    # Warp it to be reasonably squared
    tf = transform.AffineTransform(rotation=ROTATION, shear=SHEAR, translation=TRANSLATION)
    img = transform.warp(img, inverse_map=tf)

    # Normalize the whole image
    # img *= 1.0/(img.max() - img.min())
    img = (img - np.min(img))/np.ptp(img)

    # Normalize on a sigmoid curve to better separate ink from paper
    k = 10
    img = np.sqrt(1 / (1 + np.exp(k * (img - 0.5))))

    # imageio.imsave("chars_overstrike_rot.png", img)
    loaded_files[filename] = img
    return img


# Pull out the image of a character-pair, c1 overstruck with c2.
# The character at (x, y) should be the same as the character at (y, x) but due to printing may be slightly
# different.  We just analyze them all anyway, and it'll sort out in the final mapping.
# (Could double the performance by folding in half, but we don't care really)
def one_chars_image(c1, c2):
    cc = c1 + c2
    oc1 = ord(c1)
    if oc1 < ord(' '):
        raise ValueError("Character? " + c1)
    if oc1 > ord('_'):
        raise ValueError("Character? " + c1)
    oc2 = ord(c2)
    if oc2 < ord(' '):
        raise ValueError("Character? " + c2)
    if oc2 > ord('_'):
        raise ValueError("Character? " + c2)

    # The character at (col, row)
    col = (oc2 - ord(' '))
    row = (oc1 - ord(' '))

    pixX = int(CHARS_LEFTMARGIN + (CHARS_CHARWIDTH * col))
    pixY = int(CHARS_TOPMARGIN + (CHARS_ROWHEIGHT * row))

    # Get the full original image
    full_image = load_image("chars_overstrike.jpg")

    # Pull out the character from its (x,y) position
    img = full_image[pixY: pixY + int(CHARS_ROWHEIGHT), pixX: pixX + int(CHARS_CHARWIDTH)]

    # invert so ink>paper
    # char = 1 - char

    # Find the bounding-box of the printed character.
    # (Many are way off center, e.g. comma and apostrophe)
    edges1 = (0, 0)
    edges2 = (int(CHARS_ROWHEIGHT), int(CHARS_CHARWIDTH))
    if cc != '  ':
        # Top and left bounds
        edges1 = np.unravel_index(np.argmax(img > 0.4, axis=None), img.shape)
        # Bottom and right bounds
        flp = np.flip(img)
        edges2 = np.unravel_index(np.argmax(flp > 0.4, axis=None), img.shape)
        # edges2 = (img.shape[0] - edges[0], img.shape[1] - edges[1])

    # Save some cropped images.  Each should ideally be just a single character-cell.
#    if c1 in " #$01JKXY^_" and c2 in " !@123AJKZ[]_":
#        imageio.imsave("char_{:x}_{:x}.jpg".format(oc2, oc1), char)

    return img, edges1, edges2


def chars_image(c1, c2):
    img, edges1a, edges2a = one_chars_image(c1, c2)
    _, edges1b, edges2b = one_chars_image(c2, c1)
    topdiff = edges1b[0] - edges1a[0]
    leftdiff = 0  # edges1b[1] - edges1a[1]
    img = np.roll(img, int(topdiff/2), axis=0)
    # img = np.roll(img, -int(leftdiff/2), axis=1)
    return img, (edges1a[0] + int(topdiff/2), edges1a[1] + int(leftdiff/2)), (edges2a[0] + int(topdiff/2), edges2a[1] + int(leftdiff/2))
    # return img, (edges1a[0], edges1a[1]), (edges2a[0], edges2a[1])


# Calculate the average luminance for a character
def luminance(image):
    return np.mean(image)


# Calculate the HOG for a character-pair (as a single histogram)
def hog_char(image, luminance):
    rows = image.shape[0]
    cols = image.shape[1]
    rows_cellsize = int(image.shape[0]/BROWS)
    cols_cellsize = int(image.shape[1]/BCOLS)
    fd, img = feature.hog(image,
                          orientations=8,
                          pixels_per_cell=(rows_cellsize, cols_cellsize),  # (16, 16),
                          cells_per_block=(1, 1),
                          block_norm='L1',
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
    luminances = {}

    # Find the minimum bounding-box for each character-pair

    # rowbounds/colbounds will be the largest box of any character
    rowbounds = [1e10, 0]
    colbounds = [1e10, 0]

    for i in range(STARTCHAR, ENDCHAR+1):
        for j in range(STARTCHAR, ENDCHAR+1):
            c1 = chr(i)
            c2 = chr(j)
            cc = c1 + c2
            # Pull out the character-pair from the whole image
            img, edges1, edges2 = chars_image(c1, c2)
            luminances[cc] = img.mean()

            # Find the bounding-box of the printed character.
            # (Many are way off center, e.g. comma and apostrophe)
            if cc != '  ':
                if edges1[0] < rowbounds[0]:
                    rowbounds[0] = edges1[0]
                if edges1[1] < colbounds[0]:
                    colbounds[0] = edges1[1]
                if img.shape[0] - edges2[0] > rowbounds[1]:
                    rowbounds[1] = img.shape[0] - edges2[0]
                if img.shape[1] - edges2[1] > colbounds[1]:
                    colbounds[1] = img.shape[1] - edges2[1]

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

    # calculate the HOG for each character-pair
    fds = {}
    chars = []
    images = []
    for i in range(STARTCHAR, ENDCHAR + 1):
        for j in range(STARTCHAR, ENDCHAR + 1):
            c1 = chr(i)
            c2 = chr(j)
            cc = c1 + c2

            img, edges1, edges2 = chars_image(c1, c2)
            char = img[rowbounds[0]: rowbounds[1], colbounds[0]: colbounds[1]]

            # Keep a small set for visual inspection
            if c1 in " #$012345AFJKLMWXY^_" and c2 in " =_":
                chars.append(char)

            (fd, image) = hog_char(char, luminances[cc])

            fds[cc] = fd.tolist()
            images.append(image)

    # Save a combined image of HOGs
#    im = np.concatenate(tuple(images))
#    im *= 1 / im.max()
#    imageio.imsave("overstrike.png", im)

#    # Save a combined image of characters
    im = np.concatenate(tuple(chars))
    im *= 1 / im.max()
    # imageio.imsave("overstrike1.png", im)

    im = np.concatenate(tuple(chars), axis=1)
    im *= 1 / im.max()
    # imageio.imsave("overstrike2.png", im)

    # Save the JSON
    with io.open("chars_overstrike.json", "w") as afile:
        json.dump(fds, afile, indent=2)


def print_table():
    # Print the "all combinations" ASCII overstrike table.
    print("")
    for rows in range(STARTCHAR, ENDCHAR + 1):
        line = ""
        for cols in range(STARTCHAR, ENDCHAR + 1):
            line = line + chr(cols)
        # print(line + "\r" + (len(line) * chr(rows)))
        print((len(line) * chr(rows)) + "\r" + line)
    print("\n\n\n")


@click.command()
@click.option('--table', is_flag=True, default=False, help='Print the overstrike table')
def main(table):
    if table:
        print_table()
    else:
        analyze_table_image()


if __name__ == "__main__":
    main()



