#!/usr/bin/env python3
"""Tools for composing overstrike ASCII art for Teletype.

Commands:
  --catalog     Extract individual character images from the overstrike scan
  --palette     Print useful overstrike pairs (pipe to Teletype to see them)
  --preview F   Terminal preview of a composition file
  --render F    Render a composition file to teletype format
  --rasterize F Rasterize a stroke-definition file to a composition

Composition file format (.src):
  Grid of 2-char tokens separated by spaces.
  __  = blank (space+space)
  X_  = single character X (no overstrike)
  XY  = character X overstruck with character Y

Stroke definition file (.strokes):
  Lines of the form:
    grid ROWS COLS
    h ROW COL_START COL_END [WEIGHT]     horizontal stroke
    v COL ROW_START ROW_END [WEIGHT]     vertical stroke
    d ROW1 COL1 ROW2 COL2 [WEIGHT]      diagonal stroke
    dot ROW COL                          dot/point
  WEIGHT: light (default), medium, heavy
"""

import sys
import os
import io
import math
import click
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# Character selection by visual effect.
# Prefer single characters (cleaner print) over overstrike pairs.
# Format: (layer1, layer2) — use space for layer2 when single-char.
#
# The key insight: characters like = already contain two horizontal lines,
# : contains two vertical dots, # is a grid — these provide sub-character
# resolution so the grid can be smaller.

CHAR_MAP = {
    # (stroke_types_in_cell) -> (char1, char2)
    # stroke types: "h"=horizontal, "v"=vertical, "dl"=diag-left(\),
    #               "dr"=diag-right(/), "dot"=dot

    # Single strokes — always prefer single characters
    "h":        "-",
    "v":        "I",
    "dl":       "\\",
    "dr":       "/",
    "dot":      ".",

    # Crossings — single character when possible
    "h+v":      "+",
    "dl+dr":    "X",

    # Crossings that need overstrike
    "h+dl":     ("-", "\\"),
    "h+dr":     ("-", "/"),
    "v+dl":     ("I", "\\"),
    "v+dr":     ("I", "/"),
    "h+v+dl":   ("+", "\\"),
    "h+v+dr":   ("+", "/"),

    # Weight variants — single characters
    "h_heavy":  "=",
    "v_heavy":  ("I", "!"),
    "h_low":    "_",
    "v_light":  ":",
    "dot_top":  "'",
}


def rasterize_strokes(stroke_defs):
    """Convert stroke definitions to a grid of (char1, char2) pairs.

    stroke_defs: list of stroke tuples:
      ("h", row, col_start, col_end, weight)
      ("v", col, row_start, row_end, weight)
      ("d", row1, col1, row2, col2, weight)
      ("dot", row, col)
      ("grid", rows, cols)
    """
    # Find grid dimensions
    rows = 7
    cols = 11
    for s in stroke_defs:
        if s[0] == "grid":
            rows, cols = s[1], s[2]

    # Track what strokes pass through each cell
    # Each cell gets a set of stroke types
    cells = [[set() for _ in range(cols)] for _ in range(rows)]
    weights = [[{} for _ in range(cols)] for _ in range(rows)]

    for s in stroke_defs:
        stype = s[0]
        if stype == "grid":
            continue

        if stype == "h":
            _, row, c0, c1, *rest = s
            weight = rest[0] if rest else "medium"
            for c in range(c0, c1 + 1):
                if 0 <= row < rows and 0 <= c < cols:
                    cells[row][c].add("h")
                    weights[row][c]["h"] = weight

        elif stype == "v":
            _, col, r0, r1, *rest = s
            weight = rest[0] if rest else "medium"
            for r in range(r0, r1 + 1):
                if 0 <= r < rows and 0 <= col < cols:
                    cells[r][col].add("v")
                    weights[r][col]["v"] = weight

        elif stype == "d":
            _, r0, c0, r1, c1, *rest = s
            weight = rest[0] if rest else "medium"
            # Bresenham-style line rasterization
            dr = r1 - r0
            dc = c1 - c0
            steps = max(abs(dr), abs(dc))
            if steps == 0:
                cells[r0][c0].add("dot")
                continue
            for i in range(steps + 1):
                t = i / steps
                r = round(r0 + dr * t)
                c = round(c0 + dc * t)
                if 0 <= r < rows and 0 <= c < cols:
                    if dc > 0 and dr != 0:
                        # Going right: upper-left to lower-right = \
                        cells[r][c].add("dl")
                        weights[r][c]["dl"] = weight
                    elif dc < 0 and dr != 0:
                        # Going left: upper-right to lower-left = /
                        cells[r][c].add("dr")
                        weights[r][c]["dr"] = weight
                    elif dc == 0:
                        cells[r][c].add("v")
                        weights[r][c]["v"] = weight
                    else:
                        # Horizontal (dr == 0)
                        cells[r][c].add("h")
                        weights[r][c]["h"] = weight

        elif stype == "dot":
            _, row, col = s
            if 0 <= row < rows and 0 <= col < cols:
                cells[row][col].add("dot")

    # Map each cell to a character or overstrike pair
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            types = cells[r][c]
            w = weights[r][c]
            pair = cell_to_char(types, w)
            row.append(pair)
        grid.append(row)

    return grid


def cell_to_char(types, weights):
    """Map a set of stroke types to the best character or overstrike pair.

    Uses the full ASR33 character set including letters with built-in
    stroke junctions (T, L, J, E, F, Y, V, etc.) and ASCII-1963 glyphs
    (^ = up-arrow, _ = left-arrow) to minimize overstrike.
    """
    if not types:
        return (" ", " ")

    types = frozenset(types)

    # Single stroke types — always prefer single character (no overstrike)
    if types == {"dot"}:
        return (".", " ")
    if types == {"h"}:
        w = weights.get("h", "medium")
        if w == "heavy":
            return ("=", " ")
        return ("-", " ")
    if types == {"v"}:
        w = weights.get("v", "medium")
        if w == "heavy":
            return ("I", "!")
        elif w == "light":
            return (":", " ")
        return ("I", " ")
    if types == {"dl"}:
        return ("\\", " ")
    if types == {"dr"}:
        return ("/", " ")

    # Two-stroke crossings — single character when possible
    if types == {"h", "v"}:
        return ("+", " ")
    if types == {"dl", "dr"}:
        return ("Y", " ")   # Y = two diags meeting, better than X for kanji
    if types == {"h", "dl"}:
        return ("7", " ")   # 7 = horiz top + stroke down-right (matches \)
    if types == {"h", "dr"}:
        return ("/", "-")   # needs overstrike
    if types == {"v", "dl"}:
        return ("\\", "I")  # needs overstrike
    if types == {"v", "dr"}:
        return ("I", "/")   # needs overstrike
    if types == {"v", "dot"}:
        return ("!", " ")
    if types == {"h", "dot"}:
        return ("-", " ")

    # Three-stroke crossings
    if "h" in types and "v" in types and "dl" in types:
        return ("+", "\\")
    if "h" in types and "v" in types and "dr" in types:
        return ("+", "/")
    if "h" in types and "dl" in types and "dr" in types:
        return ("Y", "-")

    # Fallback: pick the most prominent stroke
    if "h" in types:
        return ("-", " ")
    if "v" in types:
        return ("I", " ")
    if "dl" in types:
        return ("\\", " ")
    if "dr" in types:
        return ("/", " ")
    return (".", " ")


def parse_stroke_file(text):
    """Parse a stroke definition file."""
    strokes = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        cmd = parts[0]
        if cmd == "grid":
            strokes.append(("grid", int(parts[1]), int(parts[2])))
        elif cmd == "h":
            row, c0, c1 = int(parts[1]), int(parts[2]), int(parts[3])
            weight = parts[4] if len(parts) > 4 else "medium"
            strokes.append(("h", row, c0, c1, weight))
        elif cmd == "v":
            col, r0, r1 = int(parts[1]), int(parts[2]), int(parts[3])
            weight = parts[4] if len(parts) > 4 else "medium"
            strokes.append(("v", col, r0, r1, weight))
        elif cmd == "d":
            r0, c0, r1, c1 = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
            weight = parts[5] if len(parts) > 5 else "medium"
            strokes.append(("d", r0, c0, r1, c1, weight))
        elif cmd == "dot":
            strokes.append(("dot", int(parts[1]), int(parts[2])))
        else:
            print(f"Warning: unknown stroke type: {cmd}", file=sys.stderr)
    return strokes


def parse_composition(text):
    """Parse a composition file into a 2D grid of (char1, char2) tuples."""
    grid = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = []
        for token in line.split():
            if token == "__":
                row.append((" ", " "))
            elif len(token) == 1:
                row.append((token, " "))
            elif len(token) == 2:
                c1 = token[0] if token[0] != "_" else " "
                c2 = token[1] if token[1] != "_" else " "
                row.append((c1, c2))
            else:
                raise ValueError(f"Bad token: {token!r}")
        grid.append(row)
    return grid


def grid_to_src(grid):
    """Convert a grid of (c1, c2) pairs back to .src format text."""
    lines = []
    for row in grid:
        tokens = []
        for c1, c2 in row:
            if c1 == " " and c2 == " ":
                tokens.append("__")
            elif c2 == " ":
                tokens.append(c1 + "_")
            elif c1 == " ":
                tokens.append("_" + c2)
            else:
                tokens.append(c1 + c2)
        lines.append(" ".join(tokens))
    return "\n".join(lines)


def render_teletype(grid, indent=0):
    """Convert grid to teletype overstrike format.

    Each line is layer1\\rlayer2 when overstrike is needed,
    or just layer1 when layer2 is all spaces.
    Lines are separated by \\r\\n.
    """
    prefix = " " * indent
    lines = []
    for row in grid:
        layer1 = (prefix + "".join(c1 for c1, c2 in row)).rstrip()
        layer2 = (prefix + "".join(c2 for c1, c2 in row)).rstrip()
        if layer2:
            lines.append(layer1 + "\r" + layer2)
        else:
            lines.append(layer1)
    return "\r\n".join(lines)


def preview_merged(grid, indent=0):
    """Terminal preview — pick the denser character at each position."""
    density = " .',-:;!/\\=+*01IJAX#@WM"
    prefix = " " * indent
    lines = []
    for row in grid:
        merged = ""
        for c1, c2 in row:
            d1 = density.find(c1) if c1 in density else len(density)
            d2 = density.find(c2) if c2 in density else len(density)
            merged += c2 if d2 > d1 else c1
        lines.append(prefix + merged)
    return "\n".join(lines)


FONTS = {
    "gothic_w3": ("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 0),
    "gothic_w6": ("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 0),
    "mincho_w3": ("/System/Library/Fonts/ヒラギノ明朝 ProN.ttc", 0),
    "mincho_w6": ("/System/Library/Fonts/ヒラギノ明朝 ProN.ttc", 2),
}


def font_to_grid(ch, font_path, font_index=0, rows=8, cols=None):
    """Render a character from a TrueType font and classify each grid cell
    by stroke direction using morphological opening with directional
    structuring elements.

    If cols is None, it's computed from rows to produce a physically square
    result on the ASR33 (10 cpi horizontal, 6 lpi vertical).
    """
    from scipy.ndimage import binary_opening

    if cols is None:
        cols = round(rows * 10 / 6)

    cell_px = 40
    w_px = cols * cell_px
    h_px = rows * cell_px

    # Render the kanji at native square proportions, then stretch
    # horizontally to fill the grid.  The Teletype's narrow cells
    # (0.1" wide × 0.167" tall) compress it back to square on paper.
    # This ensures the character content fills the full grid width.
    ref_size = 200
    ref_font = ImageFont.truetype(font_path, size=ref_size, index=font_index)
    ref_bbox = ref_font.getbbox(ch)
    ref_h = ref_bbox[3] - ref_bbox[1]
    # Scale to fill 92% of the grid height
    font_size = int(h_px * 0.92 * ref_size / ref_h)

    font = ImageFont.truetype(font_path, size=font_size, index=font_index)
    bbox = font.getbbox(ch)
    glyph_w = bbox[2] - bbox[0]
    glyph_h = bbox[3] - bbox[1]

    # Render at native proportions into a tight image
    margin = 4
    img_native = Image.new('L', (glyph_w + margin * 2, glyph_h + margin * 2), 255)
    draw = ImageDraw.Draw(img_native)
    draw.text((margin - bbox[0], margin - bbox[1]), ch, fill=0, font=font)

    # Stretch to fill the full pixel grid
    img = img_native.resize((w_px, h_px), Image.LANCZOS)

    binary = np.array(img) < 128

    # Directional structuring elements — must be longer than stroke width
    # to avoid false detections on thick strokes at high resolutions.
    # Scale with font size (which determines stroke width).
    slen = max(cell_px * 7 // 10, font_size // 10)
    aspect = w_px / h_px  # ~1.67 for standard Teletype correction

    # Horizontal SE must be longer than stretched stroke width to avoid
    # false h detection on thick verticals.  Scale by aspect ratio.
    slen_h = max(slen, int(slen * aspect))
    h_se = np.zeros((3, slen_h), dtype=bool); h_se[1, :] = True
    v_se = np.zeros((slen, 3), dtype=bool); v_se[:, 1] = True

    # Diagonal SEs: aspect-corrected angle (~30° from horizontal)
    dl_len = slen
    dl_se = np.zeros((dl_len, int(dl_len * aspect)), dtype=bool)
    for i in range(dl_len):
        j = int(i * aspect)
        if j < dl_se.shape[1]:
            dl_se[i, j] = True
    dr_se = np.fliplr(dl_se)

    h_map = binary_opening(binary, h_se)
    v_map = binary_opening(binary, v_se)
    dl_map = binary_opening(binary, dl_se)
    dr_map = binary_opening(binary, dr_se)

    # Edge margin: check this many pixels at each cell edge for connectivity
    em = cell_px // 5

    # First pass: detect stroke types per cell
    cell_types = []
    for r in range(rows):
        row_types = []
        for c in range(cols):
            y0, y1 = r * cell_px, (r + 1) * cell_px
            x0, x1 = c * cell_px, (c + 1) * cell_px
            cell_area = cell_px * cell_px

            covs = {
                "h":  h_map[y0:y1, x0:x1].sum() / cell_area,
                "v":  v_map[y0:y1, x0:x1].sum() / cell_area,
                "dl": dl_map[y0:y1, x0:x1].sum() / cell_area,
                "dr": dr_map[y0:y1, x0:x1].sum() / cell_area,
            }
            ink_cov = binary[y0:y1, x0:x1].sum() / cell_area
            max_cov = max(covs.values())

            types = set()
            for direction, cov in covs.items():
                if cov >= 0.03 and (cov >= max_cov * 0.4 or cov >= 0.05):
                    types.add(direction)

            if not types and ink_cov > 0.04:
                types.add("dot")

            row_types.append(types)
        cell_types.append(row_types)

    # Second pass: suppress weak detections.
    # If a cell has both H and V but one is much weaker, keep only the dominant.
    # Dense cells (high ink coverage) use a relaxed threshold to preserve
    # directional diversity — multiple overlapping strokes benefit from
    # secondary direction signals that would be noise in sparse areas.
    for r in range(rows):
        for c in range(cols):
            types = cell_types[r][c]
            if len(types) < 2:
                continue
            y0, y1 = r * cell_px, (r + 1) * cell_px
            x0, x1 = c * cell_px, (c + 1) * cell_px
            cell_area = cell_px * cell_px
            covs = {
                "h":  h_map[y0:y1, x0:x1].sum() / cell_area,
                "v":  v_map[y0:y1, x0:x1].sum() / cell_area,
                "dl": dl_map[y0:y1, x0:x1].sum() / cell_area,
                "dr": dr_map[y0:y1, x0:x1].sum() / cell_area,
            }
            ink_cov = binary[y0:y1, x0:x1].sum() / cell_area
            dominant = max((covs.get(t, 0), t) for t in types)
            # Dense cells: relax from 50% to 40% to preserve diversity
            threshold = 0.4 if ink_cov > 0.6 else 0.5
            cell_types[r][c] = {t for t in types
                                if covs.get(t, 0) >= dominant[0] * threshold}

    # Third pass: suppress false orthogonal detections on thick strokes.
    # A thick diagonal triggers horizontal/vertical SEs; a thick vertical
    # triggers horizontal SE (especially with pre-stretch).
    # Only suppress when the secondary direction lacks a pure continuation
    # (a neighbor in its own direction that doesn't also have the primary).
    # This pass is NARROW: only h-vs-diagonal and h-vs-v conflicts, and only
    # when the secondary direction is clearly weaker.
    for r in range(rows):
        for c in range(cols):
            types = cell_types[r][c]
            if len(types) < 2:
                continue

            y0, y1 = r * cell_px, (r + 1) * cell_px
            x0, x1 = c * cell_px, (c + 1) * cell_px
            cell_area = cell_px * cell_px
            covs = {
                "h":  h_map[y0:y1, x0:x1].sum() / cell_area,
                "v":  v_map[y0:y1, x0:x1].sum() / cell_area,
                "dl": dl_map[y0:y1, x0:x1].sum() / cell_area,
                "dr": dr_map[y0:y1, x0:x1].sum() / cell_area,
            }

            # h appearing with diagonal: suppress h if it has no pure-h neighbor
            if "h" in types and ("dl" in types or "dr" in types):
                pure_h = any(
                    0 <= nc < cols and "h" in cell_types[r][nc]
                    and "dl" not in cell_types[r][nc]
                    and "dr" not in cell_types[r][nc]
                    for nc in [c-1, c+1])
                if not pure_h:
                    types.discard("h")

            # v appearing with diagonal: suppress v if it has no pure-v neighbor
            if "v" in types and ("dl" in types or "dr" in types):
                pure_v = any(
                    0 <= nr < rows and "v" in cell_types[nr][c]
                    and "dl" not in cell_types[nr][c]
                    and "dr" not in cell_types[nr][c]
                    for nr in [r-1, r+1])
                if not pure_v:
                    types.discard("v")

            # h appearing with v where h is weaker: likely false h from
            # thick vertical (common with pre-stretch).  Suppress the
            # weaker direction if it's less than 60% of the dominant.
            if "h" in types and "v" in types:
                if covs["h"] < covs["v"] * 0.6:
                    types.discard("h")
                elif covs["v"] < covs["h"] * 0.6:
                    types.discard("v")

    # Fourth pass: suppress isolated single-cell strokes (fragments/noise).
    for r in range(rows):
        for c in range(cols):
            types = cell_types[r][c]
            if not types:
                continue
            cleaned = set()
            for t in types:
                has_neighbor = False
                if t == "h":
                    has_neighbor = ((c > 0 and "h" in cell_types[r][c-1]) or
                                   (c < cols-1 and "h" in cell_types[r][c+1]))
                elif t == "v":
                    has_neighbor = ((r > 0 and "v" in cell_types[r-1][c]) or
                                   (r < rows-1 and "v" in cell_types[r+1][c]))
                elif t == "dl":
                    has_neighbor = ((r > 0 and c > 0 and "dl" in cell_types[r-1][c-1]) or
                                   (r < rows-1 and c < cols-1 and "dl" in cell_types[r+1][c+1]))
                elif t == "dr":
                    has_neighbor = ((r > 0 and c < cols-1 and "dr" in cell_types[r-1][c+1]) or
                                   (r < rows-1 and c > 0 and "dr" in cell_types[r+1][c-1]))
                elif t == "dot":
                    has_neighbor = True
                if has_neighbor:
                    cleaned.add(t)
            if not cleaned:
                y0, y1 = r * cell_px, (r + 1) * cell_px
                x0, x1 = c * cell_px, (c + 1) * cell_px
                ink = binary[y0:y1, x0:x1].mean()
                if ink > 0.08:
                    cleaned.add("dot")
            cell_types[r][c] = cleaned

    # Fifth pass: thin double-width strokes.
    # When adjacent cells have the same direction and continuous ink between them
    # (same physical stroke), keep only the cell with more coverage.
    for r in range(rows):
        for c in range(cols - 1):
            types_a = cell_types[r][c]
            types_b = cell_types[r][c + 1]
            # Horizontal thinning: adjacent vertical-only cells
            if types_a == {"v"} and types_b == {"v"}:
                y0, y1 = r * cell_px, (r + 1) * cell_px
                # Check if ink is continuous at the boundary between cells
                bx = (c + 1) * cell_px
                boundary = binary[y0:y1, max(0, bx - 2):bx + 2]
                if boundary.any():
                    x0a = c * cell_px
                    x0b = (c + 1) * cell_px
                    cov_a = v_map[y0:y1, x0a:x0a + cell_px].sum()
                    cov_b = v_map[y0:y1, x0b:x0b + cell_px].sum()
                    if cov_a <= cov_b:
                        cell_types[r][c] = set()
                    else:
                        cell_types[r][c + 1] = set()
            # Thin adjacent same-diagonal cells on same row
            for diag in ["dl", "dr"]:
                if types_a == {diag} and types_b == {diag}:
                    y0, y1 = r * cell_px, (r + 1) * cell_px
                    bx = (c + 1) * cell_px
                    boundary = binary[y0:y1, max(0, bx - 2):bx + 2]
                    if boundary.any():
                        dmap = dl_map if diag == "dl" else dr_map
                        x0a = c * cell_px
                        x0b = (c + 1) * cell_px
                        cov_a = dmap[y0:y1, x0a:x0a + cell_px].sum()
                        cov_b = dmap[y0:y1, x0b:x0b + cell_px].sum()
                        if cov_a <= cov_b:
                            cell_types[r][c] = set()
                        else:
                            cell_types[r][c + 1] = set()

    # Sixth pass: edge connectivity + neighbor awareness for character choice
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            types = cell_types[r][c]
            if not types:
                row.append((" ", " "))
                continue

            y0, y1 = r * cell_px, (r + 1) * cell_px
            x0, x1 = c * cell_px, (c + 1) * cell_px

            edges = {}
            if "h" in types:
                edges["h_left"] = h_map[y0:y1, max(0,x0-em):x0+em].any()
                edges["h_right"] = h_map[y0:y1, x1-em:min(w_px,x1+em)].any()
            if "v" in types:
                edges["v_top"] = v_map[max(0,y0-em):y0+em, x0:x1].any()
                edges["v_bot"] = v_map[y1-em:min(h_px,y1+em), x0:x1].any()

            nbr = {}
            nbr["left_has_h"] = c > 0 and "h" in cell_types[r][c-1]
            nbr["right_has_h"] = c < cols-1 and "h" in cell_types[r][c+1]
            nbr["top_has_v"] = r > 0 and "v" in cell_types[r-1][c]
            nbr["bot_has_v"] = r < rows-1 and "v" in cell_types[r+1][c]
            nbr["left_has_v"] = c > 0 and "v" in cell_types[r][c-1]
            nbr["right_has_v"] = c < cols-1 and "v" in cell_types[r][c+1]
            nbr["top_has_h"] = r > 0 and "h" in cell_types[r-1][c]
            nbr["bot_has_h"] = r < rows-1 and "h" in cell_types[r+1][c]
            nbr["right2_has_h"] = c < cols-2 and "h" in cell_types[r][c+2]
            nbr["left2_has_h"] = c > 1 and "h" in cell_types[r][c-2]

            # Diagonal continuation: does the diagonal have a neighbor
            # in its own direction? (for terminal detection)
            if "dl" in types:  # \ direction
                nbr["dl_prev"] = r > 0 and c > 0 and "dl" in cell_types[r-1][c-1]
                nbr["dl_next"] = r < rows-1 and c < cols-1 and "dl" in cell_types[r+1][c+1]
            if "dr" in types:  # / direction
                nbr["dr_prev"] = r > 0 and c < cols-1 and "dr" in cell_types[r-1][c+1]
                nbr["dr_next"] = r < rows-1 and c > 0 and "dr" in cell_types[r+1][c-1]

            # Sub-threshold h coverage for shallow-angle detection
            if "dl" in types or "dr" in types:
                cell_area = cell_px * cell_px
                nbr["h_trace"] = h_map[y0:y1, x0:x1].sum() / cell_area

            # For = detection: check if horizontal ink is continuous across
            # the boundary with the cell above (closely-spaced double horizontal)
            if r > 0 and "h" in cell_types[r-1][c] and "h" in types:
                by = r * cell_px  # boundary y
                boundary = binary[max(0, by - em):by + em, x0:x1]
                nbr["h_continuous_above"] = boundary.mean() > 0.15
            else:
                nbr["h_continuous_above"] = False

            row.append(edges_to_char(frozenset(types), edges, nbr))
        grid.append(row)
    return grid


def edges_to_char(types, edges, nbr=None):
    """Choose the best single character based on stroke types, edge connectivity,
    and neighbor context.

    Uses ASR33 characters with built-in junctions (T, L, J, 7, [, ], etc.)
    to avoid overstrike wherever possible.
    """
    if nbr is None:
        nbr = {}

    h_left = edges.get("h_left", False)
    h_right = edges.get("h_right", False)
    v_top = edges.get("v_top", False)
    v_bot = edges.get("v_bot", False)

    # Neighbor context
    left_h = nbr.get("left_has_h", False)
    right_h = nbr.get("right_has_h", False)
    top_v = nbr.get("top_has_v", False)
    bot_v = nbr.get("bot_has_v", False)

    # Directional connectivity (set for all types, not just h+v)
    goes_left = h_left or left_h
    goes_right = h_right or right_h
    goes_up = v_top or top_v
    goes_down = v_bot or bot_v

    # --- Single stroke types ---
    if types == frozenset({"h"}):
        # _ (left-arrow on ASR33) for closely-spaced double horizontals.
        # Lighter weight than =- overstrike, single print.
        h_continuous_above = nbr.get("h_continuous_above", False)
        if h_continuous_above:
            return ("_", " ")
        return ("-", " ")
    if types == frozenset({"v"}):
        return ("I", " ")
    if types == frozenset({"dl"}):
        # \ diagonal — calligraphic effects:
        # terminals first (serif hints), then shallow angle for mid-stroke
        dl_prev = nbr.get("dl_prev", False)
        dl_next = nbr.get("dl_next", False)
        if not dl_prev and dl_next:
            return ("\\", "'")   # entry terminal — press mark at top
        if dl_prev and not dl_next:
            return ("\\", ".")   # exit terminal — foot at bottom
        h_trace = nbr.get("h_trace", 0)
        if h_trace > 0.02 and dl_prev and dl_next:
            return ("\\", "-")   # shallow angle (mid-stroke only)
        return ("\\", " ")
    if types == frozenset({"dr"}):
        # / diagonal — mirror
        dr_prev = nbr.get("dr_prev", False)
        dr_next = nbr.get("dr_next", False)
        if not dr_prev and dr_next:
            return ("/", "'")    # entry terminal
        if dr_prev and not dr_next:
            return ("/", ".")    # exit terminal
        h_trace = nbr.get("h_trace", 0)
        if h_trace > 0.02 and dr_prev and dr_next:
            return ("/", "-")    # shallow angle (mid-stroke only)
        return ("/", " ")
    if types == frozenset({"dot"}):
        return (".", " ")

    # --- H + V junctions ---
    if types == frozenset({"h", "v"}):
        # H: two parallel verticals bridged by horizontal.
        # Detect when left AND right neighbors also have vertical strokes.
        left_v = nbr.get("left_has_v", False)
        right_v = nbr.get("right_has_v", False)
        if left_v and right_v and goes_left and goes_right:
            return ("H", " ")   # double-vertical with horizontal bridge

        if goes_left and goes_right and goes_up and goes_down:
            return ("+", " ")    # full crossing
        if goes_left and goes_right and goes_down and not goes_up:
            return ("T", " ")    # horiz top, vert goes down
        if goes_left and goes_right and goes_up and not goes_down:
            return ("+", " ")    # inverted T — use + (no single char)
        if goes_up and goes_right and not goes_down and not goes_left:
            return ("L", " ")    # vert from above, horiz goes right
        if goes_up and goes_left and not goes_down and not goes_right:
            return ("J", " ")    # vert from above, hook goes left
        if goes_down and goes_right and not goes_up and not goes_left:
            return ("L", " ")    # corner going down+right

        # Brackets: require (1) horizontal continues at least 2 cells
        # (a genuine stroke, not thick-vert bleed), and (2) vertical extends.
        vert_extends = goes_up or goes_down
        # Check h extends 2+ cells in the indicated direction
        right_h_2 = (right_h and
                     nbr.get("right2_has_h", False))
        left_h_2 = (left_h and
                    nbr.get("left2_has_h", False))
        if goes_right and not goes_left:
            if right_h_2 and vert_extends:
                return ("[", " ")
            return ("+", " ")
        if goes_left and not goes_right:
            if left_h_2 and vert_extends:
                return ("]", " ")
            return ("+", " ")
        return ("+", " ")

    # --- Diagonal combinations ---
    if types == frozenset({"dl", "dr"}):
        # Y has fork opening UP — correct when diagonals converge upward
        # (e.g. top of 各). Wrong when they diverge downward (e.g. 大's fork).
        # Check: if vertical neighbor above, diags are diverging → use I instead.
        if top_v:
            return ("I", " ")
        return ("Y", " ")
    if types == frozenset({"h", "dl"}):
        # 7 at corner (horizontal ends, diagonal begins);
        # overstrike at genuine crossing
        if goes_left and not goes_right:
            return ("7", " ")
        return ("-", "\\")
    if types == frozenset({"h", "dr"}):
        if goes_right and not goes_left:
            return ("/", " ")
        return ("-", "/")
    if types == frozenset({"v", "dl"}):
        if goes_up and not goes_down:
            return ("J", " ")
        return ("\\", "I")
    if types == frozenset({"v", "dr"}):
        if goes_up and not goes_down:
            return ("L", " ")
        return ("I", "/")

    # --- Three+ stroke combinations ---
    if "h" in types and "v" in types:
        return ("+", " ")
    if "h" in types:
        return ("-", " ")
    if "v" in types:
        return ("I", " ")
    if "dl" in types:
        return ("\\", " ")
    if "dr" in types:
        return ("/", " ")
    return (".", " ")


SCAN_FILE = os.path.join(os.path.dirname(__file__), "chars_overstrike.jpg")
SCAN_ROTATION = 3.145
SCAN_SHEAR = -0.007
SCAN_TRANSLATION = (5088, 8400)
SCAN_LEFT = 519
SCAN_TOP = 1405
SCAN_ROWH = 99.1
SCAN_COLW = 60.0

_scan_cache = None

def load_scan():
    """Load and warp the overstrike character scan. Cached."""
    global _scan_cache
    if _scan_cache is not None:
        return _scan_cache
    import imageio.v2 as imageio
    from skimage import transform as sktransform
    img = imageio.imread(SCAN_FILE, mode='F')
    tf = sktransform.AffineTransform(
        rotation=SCAN_ROTATION, shear=SCAN_SHEAR, translation=SCAN_TRANSLATION)
    img = sktransform.warp(img, inverse_map=tf)
    img = (img - img.min()) / (img.max() - img.min())
    img = np.sqrt(1 / (1 + np.exp(10 * (img - 0.5))))
    _scan_cache = img
    return img


def get_scan_char(c1, c2):
    """Get the scanned image of character c1 overstruck with c2."""
    scan = load_scan()
    row = ord(c1) - 0x20
    col = ord(c2) - 0x20
    px = int(SCAN_LEFT + SCAN_COLW * col)
    py = int(SCAN_TOP + SCAN_ROWH * row)
    return scan[py:py + int(SCAN_ROWH), px:px + int(SCAN_COLW)]


def render_board_image(texts, font_path, font_index, rows=8, gap=1):
    """Render lines of kanji as a preview image using scanned character cells.

    texts: list of strings, e.g. ["生死事大", "無常迅速", ...]
    Returns a numpy array (grayscale image).
    """
    ch = int(SCAN_ROWH)
    cw = int(SCAN_COLW)

    # Use actual blank paper from the scan as background
    blank_cell = get_scan_char(' ', ' ')
    paper_val = blank_cell.mean()

    line_images = []
    for text in texts:
        grids = [font_to_grid(c, font_path, font_index, rows) for c in text]
        cols_per = len(grids[0][0])
        total_cols = len(grids) * cols_per + (len(grids) - 1) * gap
        img = np.full((rows * ch, total_cols * cw), paper_val)

        for r in range(rows):
            col_offset = 0
            for gi, grid in enumerate(grids):
                if gi > 0:
                    col_offset += gap
                for cc in range(cols_per):
                    c1, c2 = grid[r][cc]
                    if c1 == ' ' and c2 == ' ':
                        continue
                    cell = get_scan_char(c1, c2)
                    x0 = (col_offset + cc) * cw
                    y0 = r * ch
                    h = min(cell.shape[0], ch)
                    w = min(cell.shape[1], cw)
                    img[y0:y0+h, x0:x0+w] = np.maximum(
                        img[y0:y0+h, x0:x0+w], cell[:h, :w])
                col_offset += cols_per

        line_images.append(img)
        line_images.append(np.full((ch, img.shape[1]), paper_val))

    return np.vstack(line_images[:-1])


def extract_catalog(scan_path, outdir):
    """Extract individual character pair images from the overstrike scan."""
    import imageio.v2 as imageio
    import numpy as np
    from skimage import transform as sktransform

    # Constants from prep_overstrike.py
    ROTATION = 3.145
    SHEAR = -0.007
    TRANSLATION = (5088, 8400)
    LEFT = 519
    TOP = 1405
    ROWH = 99.1
    COLW = 60.0

    img = imageio.imread(scan_path, mode='F')
    tf = sktransform.AffineTransform(rotation=ROTATION, shear=SHEAR, translation=TRANSLATION)
    img = sktransform.warp(img, inverse_map=tf)

    os.makedirs(outdir, exist_ok=True)

    # Extract just the useful single characters (overstrike with space)
    # and a curated set of pairs
    singles = " .'-,=_/\\!I:1+*#0()[]^X@"
    for ch in singles:
        oc = ord(ch) - 0x20
        # Character with space: row=0 (space), col=oc
        px = int(LEFT + COLW * oc)
        py = int(TOP + ROWH * 0)  # row 0 = space
        cell = img[py:py + int(ROWH), px:px + int(COLW)]
        name = f"single_{oc:02x}_{ch if ch.isalnum() else 'x{:02x}'.format(ord(ch))}"
        imageio.imsave(os.path.join(outdir, f"{name}.png"), (cell * 255).astype(np.uint8))

    # Extract useful overstrike pairs
    pairs = [
        ("-", "I"), ("-", "!"), ("-", "/"), ("-", "\\"), ("-", "_"),
        ("=", "I"), ("=", "!"),
        ("I", "!"), ("I", ":"), ("I", "/"), ("I", "\\"),
        ("/", "\\"),
        ("+", "/"), ("+", "\\"),
    ]
    for c1, c2 in pairs:
        r = ord(c1) - 0x20
        c = ord(c2) - 0x20
        px = int(LEFT + COLW * c)
        py = int(TOP + ROWH * r)
        cell = img[py:py + int(ROWH), px:px + int(COLW)]
        n1 = c1 if c1.isalnum() else f"x{ord(c1):02x}"
        n2 = c2 if c2.isalnum() else f"x{ord(c2):02x}"
        imageio.imsave(os.path.join(outdir, f"pair_{n1}_{n2}.png"), (cell * 255).astype(np.uint8))

    print(f"Extracted {len(singles)} singles + {len(pairs)} pairs to {outdir}")


@click.command()
@click.option("--catalog", type=click.Path(), help="Extract char images from scan to this directory")
@click.option("--palette", is_flag=True, help="Print overstrike palette (pipe to Teletype)")
@click.option("--board", is_flag=True, help="Render the full han board (text + scan preview image)")
@click.option("--from-font", "from_font", help="Character(s) to render from font (e.g. '事' or '生死事大')")
@click.option("--font", "font_name", default="gothic_w3", help="Font name (gothic_w3/w6, mincho_w3/w6)")
@click.option("--rows", default=8, help="Grid rows per character")
@click.option("--cols", default=0, help="Grid cols (0 = auto for square kanji at 10cpi/6lpi)")
@click.option("--preview", "preview_file", type=click.Path(), help="Preview a .src or .strokes file")
@click.option("--render", "render_file", type=click.Path(), help="Render to teletype format")
@click.option("--rasterize", "rasterize_file", type=click.Path(), help="Rasterize .strokes to .src")
@click.option("--output", type=click.Path(), help="Output file")
@click.option("--indent", default=0, help="Left indent")
@click.option("--gap", default=1, help="Gap between characters")
def main(catalog, palette, board, from_font, font_name, rows, cols, preview_file, render_file, rasterize_file, output, indent, gap):
    if catalog:
        scan = os.path.join(os.path.dirname(__file__), "chars_overstrike.jpg")
        extract_catalog(scan, catalog)
        return

    if palette:
        # Print useful pairs as overstrike — pipe to Teletype to see actual results
        singles = [
            (" ", "blank"), (".", "dot-bottom"), ("'", "dot-top"),
            (",", "comma"), ("-", "horizontal"), ("_", "h-bottom"),
            ("=", "h-double"), ("/", "diag-up"), ("\\", "diag-down"),
            ("!", "vert+dot"), ("I", "vertical"), (":", "vert-dots"),
            ("1", "vert+flag"), ("+", "cross"), ("*", "asterisk"),
            ("X", "diag-cross"), ("#", "hash"), ("(", "left-arc"),
            (")", "right-arc"), ("^", "caret"), ("J", "hook"),
        ]
        for ch, label in singles:
            sample = ch * 6
            print(f"  {sample}   {ch!r:4s} {label}")
        return

    if board:
        import imageio.v2 as imageio

        font_path, font_index = FONTS[font_name]
        texts = ["生死事大", "無常迅速", "各宜醒覚", "慎勿放逸"]

        outdir = os.path.join(os.path.dirname(__file__), "..", "kanji")
        os.makedirs(outdir, exist_ok=True)

        # Text preview
        for text in texts:
            grids = [font_to_grid(c, font_path, font_index, rows, cols or None) for c in text]
            cols_per = len(grids[0][0])
            for r in range(rows):
                parts = []
                for grid in grids:
                    line = ""
                    for c1, c2 in grid[r]:
                        density = " .',-:;!/\\=+*017IJLTYAHX#@EFH"
                        d1 = density.find(c1) if c1 in density else len(density)
                        d2 = density.find(c2) if c2 in density else len(density)
                        line += c2 if d2 > d1 else c1
                    parts.append(line.ljust(cols_per))
                print((" " * indent) + (" " * gap).join(parts))
            print()

        # Scan-based preview image
        board_img = render_board_image(texts, font_path, font_index, rows, gap)
        img_path = os.path.join(outdir, f"han_board_{font_name}_{rows}rows.png")
        imageio.imsave(img_path, (board_img * 255).astype(np.uint8))
        print(f"Saved: {img_path}")

        # Teletype output file
        if output:
            all_lines = []
            for text in texts:
                grids = [font_to_grid(c, font_path, font_index, rows, cols or None) for c in text]
                cols_per = len(grids[0][0])
                for r in range(rows):
                    l1_parts, l2_parts = [], []
                    for grid in grids:
                        l1_parts.append("".join(c1 for c1, c2 in grid[r]).ljust(cols_per))
                        l2_parts.append("".join(c2 for c1, c2 in grid[r]).ljust(cols_per))
                    layer1 = (" " * indent + (" " * gap).join(l1_parts)).rstrip()
                    layer2 = (" " * indent + (" " * gap).join(l2_parts)).rstrip()
                    if layer2:
                        all_lines.append(layer1 + "\r" + layer2)
                    else:
                        all_lines.append(layer1)
                all_lines.append("")  # blank line between kanji rows
                all_lines.append("")
            tty = "\r\n".join(all_lines)
            with io.open(output, "wb") as f:
                f.write(b"\r\n\r\n")
                f.write(tty.encode("utf-8"))
                f.write(b"\r\n\r\n")
            print(f"Saved: {output}")
        return

    if from_font:
        font_path, font_index = FONTS[font_name]
        grids = []
        for ch in from_font:
            grids.append(font_to_grid(ch, font_path, font_index, rows, cols or None))

        # Compose side by side
        gap_str = " " * gap
        for r in range(rows):
            parts_src = []
            parts_preview = []
            for grid in grids:
                src_tokens = []
                preview_line = ""
                for c1, c2 in grid[r]:
                    if c1 == " " and c2 == " ": src_tokens.append("__")
                    elif c2 == " ": src_tokens.append(c1 + "_")
                    elif c1 == " ": src_tokens.append("_" + c2)
                    else: src_tokens.append(c1 + c2)
                    density = " .',-:;!/\\=+*01IJAX#@WM"
                    d1 = density.find(c1) if c1 in density else len(density)
                    d2 = density.find(c2) if c2 in density else len(density)
                    preview_line += c2 if d2 > d1 else c1
                parts_src.append(" ".join(src_tokens))
                parts_preview.append(preview_line.ljust(cols))
            print(gap_str.join(parts_preview))
        print()

        # Render teletype output if requested
        if output:
            all_composed = []
            for r in range(rows):
                l1_parts = []
                l2_parts = []
                for grid in grids:
                    l1 = "".join(c1 for c1, c2 in grid[r]).ljust(cols)
                    l2 = "".join(c2 for c1, c2 in grid[r]).ljust(cols)
                    l1_parts.append(l1)
                    l2_parts.append(l2)
                layer1 = (" " * indent + gap_str.join(l1_parts)).rstrip()
                layer2 = (" " * indent + gap_str.join(l2_parts)).rstrip()
                if layer2:
                    all_composed.append(layer1 + "\r" + layer2)
                else:
                    all_composed.append(layer1)
            tty = "\r\n".join(all_composed)
            with io.open(output, "wb") as f:
                f.write(b"\r\n\r\n")
                f.write(tty.encode("utf-8"))
                f.write(b"\r\n\r\n")
            print(f"Saved: {output}")
        return

    filepath = rasterize_file or preview_file or render_file
    if not filepath:
        click.echo("Use --from-font CHAR, --palette, --catalog DIR, --rasterize FILE, --preview FILE, or --render FILE")
        return

    with open(filepath) as f:
        text = f.read()

    # Determine if this is a stroke file or a composition file
    is_strokes = filepath.endswith(".strokes") or rasterize_file
    if is_strokes:
        stroke_defs = parse_stroke_file(text)
        grid = rasterize_strokes(stroke_defs)
    else:
        grid = parse_composition(text)

    # Output
    if rasterize_file:
        src = grid_to_src(grid)
        if output:
            with open(output, "w") as f:
                f.write(src + "\n")
            print(f"Saved: {output}")
        else:
            print(src)
        print()
        print("Preview:")
        print(preview_merged(grid, indent))

    elif preview_file:
        print(preview_merged(grid, indent))

    elif render_file:
        tty = render_teletype(grid, indent)
        if output:
            with io.open(output, "wb") as f:
                f.write(b"\r\n\r\n")
                f.write(tty.encode("utf-8"))
                f.write(b"\r\n\r\n")
            print(f"Saved: {output}")
        else:
            for row in grid:
                l1 = "".join(c1 for c1, c2 in row)
                l2 = "".join(c2 for c1, c2 in row)
                print(f"  {l1}  |  {l2}")


if __name__ == "__main__":
    main()
