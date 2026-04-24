#!/usr/bin/env python3
"""Render Kanji characters as overstrike ASCII art for Teletype.

Generates PNG images of individual Kanji characters, then calls image2.py
to process each one.  The results are composed side-by-side.

Usage:
  python3 kanji_render.py --height 8 --gap 2
  python3 kanji_render.py --all-heights
"""

import os
import sys
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

# The four lines of the Han board
LINES = [
    "生死事大",
    # "無常迅速",
    # "各宜醒覚",
    # "慎勿放逸",
]

FONTS = {
    # Serif / calligraphic — brush-stroke variation (thin horizontals, thick verticals)
    "mincho_w3": "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",  # light
    "mincho_w6": "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",  # medium (index 2)
    "songti_light": "/System/Library/Fonts/Supplemental/Songti.ttc",  # light
    "songti": "/System/Library/Fonts/Supplemental/Songti.ttc",  # regular
    "songti_bold": "/System/Library/Fonts/Supplemental/Songti.ttc",  # bold
    # Sans-serif
    "gothic_w3": "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "gothic_w6": "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "gothic_w8": "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
}

# Font index within .ttc files (for fonts with multiple faces)
FONT_INDEX = {
    "mincho_w3": 0,
    "mincho_w6": 2,
    "songti_light": 3,
    "songti": 6,
    "songti_bold": 1,
}

CHARSETS = {
    "hammersley": ("'.", "0-"),
    "expanded": ("'.:", "0-="),
    "contrast": ("'.:", "0-=#"),
    "strokes": (" .'-", " \\/"),
}

# Per-character width for each target line height (with square images)
CHAR_WIDTHS = {
    5: 8,
    6: 9,
    7: 11,
    8: 14,
    10: 18,
}

IMAGE2 = os.path.join(os.path.dirname(__file__), "image2.py")


def render_single_kanji(ch, font_path, font_size=400, padding=20, font_index=0):
    """Render one kanji character to a square PNG file, return its path."""
    font = ImageFont.truetype(font_path, size=font_size, index=font_index)
    bbox = font.getbbox(ch)
    cw = bbox[2] - bbox[0]
    ch_h = bbox[3] - bbox[1]
    # Make the image square so height is predictable for a given width
    size = max(cw, ch_h) + padding * 2
    img = Image.new('RGB', (size, size), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Center the character
    x = (size - cw) // 2 - bbox[0]
    y = (size - ch_h) // 2 - bbox[1]
    draw.text((x, y), ch, fill=(0, 0, 0), font=font)
    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img.save(tmp.name)
    tmp.close()
    return tmp.name


def run_image2(png_path, width, chars1, chars2, gamma=1.5, jitter=0):
    """Call image2.py on a PNG and return list of (layer1, layer2) tuples."""
    out = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    out.close()
    try:
        cmd = [
            sys.executable, IMAGE2,
            "--width", str(width),
            "--invert",
            "--gamma", str(gamma),
            "--chars1", chars1,
            "--chars2", chars2,
            "--output", out.name,
        ]
        if jitter > 0:
            cmd.extend(["--jitter", str(jitter)])
        cmd.append(png_path)
        subprocess.run(cmd, check=True, capture_output=True)

        with open(out.name, "rb") as f:
            data = f.read().decode("utf-8")

        # Parse: lines are separated by \r\n, each line has layer1\rlayer2
        lines = []
        for raw in data.split("\r\n"):
            if not raw.strip():
                continue
            parts = raw.split("\r")
            if len(parts) == 2:
                lines.append((parts[0], parts[1]))
            elif len(parts) == 1 and parts[0].strip():
                lines.append((parts[0], ""))
        return lines
    finally:
        os.unlink(out.name)


def compose_line(char_results, char_width, gap_chars=1):
    """Compose multiple character results side-by-side.

    Returns list of (layer1, layer2) tuples for the composed line.
    """
    n_lines = min(len(cr) for cr in char_results)
    gap = " " * gap_chars
    composed = []
    for row in range(n_lines):
        parts1 = []
        parts2 = []
        for cr in char_results:
            l1, l2 = cr[row]
            parts1.append(l1.ljust(char_width))
            parts2.append(l2.ljust(char_width))
        composed.append((gap.join(parts1), gap.join(parts2)))
    return composed


def merge_display(l1, l2):
    """Merge two overstrike layers for terminal display (pick denser char)."""
    density = " .',-:;=+0#@XWM"
    maxlen = max(len(l1), len(l2))
    l1 = l1.ljust(maxlen)
    l2 = l2.ljust(maxlen)
    out = ""
    for c1, c2 in zip(l1, l2):
        d1 = density.find(c1) if c1 in density else len(density)
        d2 = density.find(c2) if c2 in density else len(density)
        out += c2 if d2 > d1 else c1
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--font', default="songti_light")
    parser.add_argument('--height', type=int, default=7)
    parser.add_argument('--charset', default="strokes")
    parser.add_argument('--gamma', type=float, default=1.5)
    parser.add_argument('--jitter', type=int, default=4, help='Sub-cell jitter in pixels (0=off, 4=25%%)')
    parser.add_argument('--gap', type=int, default=1, help='Gap characters between kanji')
    parser.add_argument('--indent', type=int, default=0, help='Left indent')
    parser.add_argument('--all-heights', action='store_true', help='Render at heights 5-8')
    args = parser.parse_args()

    outdir = os.path.join(os.path.dirname(__file__), "..", "kanji")
    os.makedirs(outdir, exist_ok=True)

    heights = [5, 6, 7, 8] if args.all_heights else [args.height]

    for height in heights:
        font_path = FONTS[args.font]
        char_width = CHAR_WIDTHS[height]
        chars1, chars2 = CHARSETS[args.charset]

        print(f"\n{'=' * 72}")
        print(f"Font: {args.font} | Height: {height} lines | {char_width} chars/kanji")
        print(f"Charset: {args.charset} | chars1='{chars1}' chars2='{chars2}' | gamma={args.gamma}")
        print(f"{'=' * 72}")

        indent = " " * args.indent
        all_composed = []

        for text in LINES:
            # Render each character to PNG, process with image2.py
            char_results = []
            png_paths = []
            font_index = FONT_INDEX.get(args.font, 0)
            for ch in text:
                png = render_single_kanji(ch, font_path, font_index=font_index)
                png_paths.append(png)
                lines = run_image2(png, char_width, chars1, chars2, args.gamma, args.jitter)
                char_results.append(lines)

            # Clean up PNGs
            for p in png_paths:
                print(p)
                # os.unlink(p)

            # Compose side by side
            composed = compose_line(char_results, char_width, args.gap)
            all_composed.append(composed)

            # Display merged preview
            for l1, l2 in composed:
                print(indent + merge_display(l1, l2))
            print()

        # Save teletype format
        tag = f"han_{args.font}_{height}lines_{args.charset}"
        outfile = os.path.join(outdir, f"{tag}.txt")
        with open(outfile, "wb") as f:
            f.write(b"\r\n\r\n")
            for composed in all_composed:
                for l1, l2 in composed:
                    l1 = indent + l1.rstrip()
                    l2 = indent + l2.rstrip()
                    f.write((l1 + "\r" + l2 + "\r\n").encode("utf-8"))
                f.write(b"\r\n")
            f.write(b"\r\n")
        print(f"  -> {outfile}")


if __name__ == "__main__":
    main()
