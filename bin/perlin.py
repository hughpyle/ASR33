#!/usr/bin/env python

"""
Perlin noise experiments
- a background with a star 'cutout' overlay
"""

import math
import click
import noise
import imageio
import random
import numpy as np


def perlin(img, h, w):
    freq = w / 25000
    base = random.random() * 100000
    for x in range(h):
        for y in range(w):
            img[x, y] = noise.snoise2(x * freq,
                                      y * freq,
                                      base=base) * 127 + 127


def draw_star(img, h, w, points=5):
    w2 = w/2
    z = w2 * 0.82

    off = random.random() * math.pi
    for x in range(h):
        for y in range(w):
            xx = x - w2
            yy = y - w2
            dist = math.sqrt(xx * xx + yy * yy)
            ang = math.atan2(xx, yy)

            p5 = math.pi / points

            ang -= off * p5
            xx = dist * math.sin(ang)
            yy = dist * math.cos(ang)

            while ang > p5:
                # rotate
                ang -= 2 * p5
                xx = dist * math.sin(ang)
                yy = dist * math.cos(ang)
            while ang < -p5:
                # rotate
                ang += 2 * p5
                xx = dist * math.sin(ang)
                yy = dist * math.cos(ang)

            # 5-point star has points at (0,1) connected to (sin(144), cos(144))
            # slope of the line is 1.71795/0.696 =
            slope5 = (1 + math.cos((points - 1) * p5)) / math.sin((points - 1) * p5)
            try:
                if math.fabs(ang) < p5 and dist < z:
                    if math.fabs(xx / (yy-z)) < slope5:
                        img[x, y] = 0
            except ZeroDivisionError:
                pass


@click.command()
@click.option("--width", default=72)
@click.option("--height")
@click.option('--output', help='Output filename', default='perlin.png')
@click.argument('star')
def main(width, height, output, star):
    if not height:
        height = int(width * 3 / 4)
    w = width * 3
    h = height * 4

    img = np.zeros([h, w], dtype=np.uint8)

    perlin(img, h, w)

    if star:
        # Overlay with a N-pointed star
        draw_star(img, h, w, points=int(star))

    imageio.imsave(output, img)


if __name__ == "__main__":
    main()
