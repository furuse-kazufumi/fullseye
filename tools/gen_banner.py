#!/usr/bin/env python3
"""Generate the Fullseye repository banner (GitHub social preview / README hero).

Produces ``docs/articles/assets/fullseye_banner.png`` at exactly 1280x640
(GitHub social-preview recommended size, 2:1) and keeps it under 1 MB.

Layout: a leaflet-style mosaic of real Fullseye outputs (12 tiles, 6x2 grid)
on top, with a title band at the bottom (name, tagline, pip install).

All tiles are cropped from *verified real outputs* that already live in the
repo (``docs/articles/assets/``). No AI-generated imagery, no third-party
branding. Numbers in the tagline match the measured counts in README.md
(731 distinct 2-D ops + 265 3-D ops ~= 1,000).

Reproducible: ``py -3.11 tools/gen_banner.py``

Variants
--------
``--variant banner`` (default)
    The original 12-tile 1280x640 GitHub social-preview banner. Unchanged.
``--variant mosaic``
    ``docs/articles/assets/fullseye_mosaic.png`` — a dense 1200x1200 square
    (7x7 = 49 tiles) for LinkedIn feed posts.  Optimised to *overwhelm* at
    feed size (~550 px) with colour/subject variety rather than per-tile
    legibility.  Tiles come from verified assets in ``docs/articles/assets``
    and ``examples_3d/_gallery``; montages are cropped per panel.  Tiles cut
    from AI-generated simulated source data (see ACADEMIC_ATTRIBUTION.md)
    always show the *processed* analysis panel and are kept under 1/3 of the
    grid.  ``py -3.11 tools/gen_banner.py --variant mosaic``
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "articles" / "assets"
OUT_PATH = ASSETS / "fullseye_banner.png"

# ---------------------------------------------------------------------------
# Canvas geometry
# ---------------------------------------------------------------------------
W, H = 1280, 640          # GitHub social preview: 1280x640 (2:1)
BAND_H = 160              # bottom title band
MARGIN = 12               # outer margin around the mosaic
GAP = 8                   # gap between tiles
COLS, ROWS = 6, 2         # 12 tiles
ACCENT_H = 4              # thin multi-hue accent strip above the band
CORNER_R = 7              # tile corner radius

BG = (13, 17, 23)         # GitHub-dark canvas (#0d1117)
BAND_BG = (13, 17, 23)
FG = (240, 246, 252)      # near-white title text
FG_DIM = (139, 148, 158)  # dimmed tagline text (#8b949e)
PILL_BG = (22, 27, 34)    # code pill background (#161b22)
PILL_BORDER = (48, 54, 61)
PILL_FG = (126, 231, 135)  # terminal-green pip command

# Accent strip hues, echoing "many different ops" (drawn as a smooth blend).
ACCENT_STOPS = [
    (86, 156, 214),   # blue
    (78, 201, 176),   # teal
    (245, 200, 92),   # amber
    (232, 125, 62),   # orange
    (214, 92, 158),   # magenta
]

# ---------------------------------------------------------------------------
# Tile list (edit freely).  Each entry:
#   (filename under docs/articles/assets/, fractional crop box (x0,y0,x1,y1))
# The fractional box selects the interesting panel inside montage images;
# a center "cover crop" to the tile aspect is then taken inside that box.
# Order = left-to-right, top-to-bottom on the 6x2 grid.
# ---------------------------------------------------------------------------
TILES = [
    # -- row 1 ------------------------------------------------------------
    # Real asteroid Itokawa point cloud, surface-curvature coloring (3D ops)
    ("itokawa_montage.png",        (0.655, 0.155, 0.860, 0.460)),
    # Edge orientation painted as hue (sobel_dir)
    ("science_edge_compass.png",   (0.505, 0.000, 1.000, 0.915)),
    # Sub-pixel metrology on a stepped shaft (measure_pairs)
    ("industrial_metrology.png",   (0.635, 0.020, 0.950, 0.800)),
    # Watershed instance segmentation of coins, color-labelled
    ("science_watershed_foam.png", (0.505, 0.000, 1.000, 0.830)),
    # Surface-defect heatmap (|img - median| background subtraction)
    ("industrial_defect.png",      (0.370, 0.040, 0.540, 0.450)),
    # Volumetric X-ray style render of a dinosaur skeleton (3D volume ops)
    ("science_dino_xray.png",      (0.020, 0.400, 0.980, 0.920)),
    # -- row 2 ------------------------------------------------------------
    # Frangi vesselness filaments over the Carina nebula (JWST data)
    ("academic_space_carina.png",  (0.670, 0.000, 1.000, 0.930)),
    # Distance transform shown as rainbow ripples
    ("science_distance_ripple.png", (0.670, 0.000, 1.000, 0.850)),
    # Bin-picking grasp candidates from a top-down depth camera (MuJoCo)
    ("phai_binpick.png",           (0.670, 0.000, 1.000, 0.910)),
    # Event camera (DVS) simulation: ON/OFF change events, teal/magenta
    ("physical_ai_montage.png",    (0.765, 0.200, 0.875, 0.445)),
    # Elliptic Fourier descriptor fit of an amphora silhouette
    ("academic_arch_amphora.png",  (0.670, 0.000, 1.000, 0.940)),
    # LiDAR bird's-eye view: ground removal + clustering + oriented boxes
    ("phai_lidar_clusters.png",    (0.620, 0.120, 0.920, 0.830)),
]

# ---------------------------------------------------------------------------
# Mosaic variant (LinkedIn): 1200x1200, 7x7 = 49 tiles + slim brand band.
# Each entry: (source key, fractional crop box, provenance)
#   source key   "name.png" -> docs/articles/assets/, "3d:name.png" ->
#                examples_3d/_gallery/
#   provenance   "real" = real-world data, "demo" = Fullseye-rendered
#                synthetic scene/figure, "ai" = AI-generated simulated source
#                (processed panel only; capped below 1/3 of the grid).
# Order = left-to-right, top-to-bottom; hand-interleaved for colour variety.
# ---------------------------------------------------------------------------
MOSAIC_W = MOSAIC_H = 1200
MOSAIC_BAND_H = 96
MOSAIC_MARGIN = 8
MOSAIC_GAP = 5
MOSAIC_COLS = MOSAIC_ROWS = 7
MOSAIC_CORNER_R = 5
MOSAIC_OUT = ASSETS / "fullseye_mosaic.png"

MOSAIC_TILES = [
    # -- row 1 ------------------------------------------------------------
    ("itokawa_montage.png",         (0.680, 0.190, 0.840, 0.420), "real"),
    ("science_edge_compass.png",    (0.505, 0.000, 1.000, 0.915), "demo"),
    ("academic_med_blood_smear.png", (0.672, 0.000, 1.000, 1.000), "ai"),
    ("science_dino_xray.png",       (0.020, 0.400, 0.980, 0.920), "demo"),
    ("academic_geo_mineral.png",    (0.672, 0.000, 1.000, 1.000), "ai"),
    ("phai_lidar_clusters.png",     (0.620, 0.120, 0.920, 0.830), "demo"),
    ("academic_bot_fern.png",       (0.672, 0.000, 1.000, 1.000), "ai"),
    # -- row 2 ------------------------------------------------------------
    ("academic_space_carina.png",   (0.670, 0.000, 1.000, 0.930), "real"),
    ("industrial_metrology.png",    (0.635, 0.020, 0.950, 0.800), "demo"),
    ("science_distance_ripple.png", (0.670, 0.000, 1.000, 0.850), "demo"),
    ("academic_arch_amphora.png",   (0.670, 0.000, 1.000, 0.940), "real"),
    ("phai_stereo_obstacles.png",   (0.340, 0.000, 0.660, 1.000), "demo"),
    ("academic_bio_diatoms.png",    (0.672, 0.000, 1.000, 1.000), "ai"),
    ("science_watershed_foam.png",  (0.505, 0.000, 1.000, 0.830), "demo"),
    # -- row 3 ------------------------------------------------------------
    ("academic_paleo_triceratops.png", (0.672, 0.000, 1.000, 1.000), "ai"),
    ("3d:render_beauty_hero.png",   (0.050, 0.050, 0.950, 0.950), "demo"),
    ("academic_met_hurricane.png",  (0.800, 0.000, 1.000, 1.000), "real"),
    ("physical_ai_montage.png",     (0.765, 0.200, 0.875, 0.445), "demo"),
    ("academic_geo_thin_section.png", (0.672, 0.000, 1.000, 1.000), "ai"),
    ("evis_muscle_heatmap_still.png", (0.000, 0.000, 1.000, 1.000), "demo"),
    ("academic_arch_cave_painting.png", (0.339, 0.000, 0.661, 1.000), "ai"),
    # -- row 4 ------------------------------------------------------------
    ("phai_binpick.png",            (0.670, 0.000, 1.000, 0.910), "demo"),
    ("academic_bio_butterfly.png",  (0.339, 0.000, 0.661, 1.000), "ai"),
    ("industrial_defect.png",       (0.370, 0.040, 0.540, 0.450), "demo"),
    ("gear_hero.png",               (0.000, 0.000, 1.000, 1.000), "demo"),
    ("academic_ocean_coral.png",    (0.672, 0.000, 1.000, 1.000), "ai"),
    ("science_alife_worlds.png",    (0.500, 0.080, 1.000, 0.900), "demo"),
    ("academic_paleo_ammonite_real.png", (0.800, 0.000, 1.000, 1.000), "real"),
    # -- row 5 ------------------------------------------------------------
    ("academic_med_histology.png",  (0.672, 0.000, 1.000, 1.000), "ai"),
    ("science_dragon_anaglyph.png", (0.100, 0.100, 0.900, 0.900), "demo"),
    ("academic_geo_earth.png",      (0.672, 0.000, 1.000, 1.000), "real"),
    ("3d:fit_primitives_ext.png",   (0.020, 0.050, 0.480, 0.950), "demo"),
    ("academic_med_chest_xray.png", (0.672, 0.000, 1.000, 1.000), "ai"),
    ("hand_hero.png",               (0.000, 0.000, 1.000, 1.000), "demo"),
    ("academic_bot_pollen.png",     (0.672, 0.000, 1.000, 1.000), "ai"),
    # -- row 6 ------------------------------------------------------------
    ("evis_bean_track_fullseye_still.png", (0.500, 0.000, 1.000, 1.000), "demo"),
    ("academic_space_galaxy.png",   (0.339, 0.000, 0.661, 1.000), "real"),
    ("op_taxonomy.png",             (0.680, 0.520, 1.000, 1.000), "demo"),
    ("academic_paleo_trex.png",     (0.672, 0.000, 1.000, 1.000), "ai"),
    ("phai_focus_stack.png",        (0.670, 0.000, 1.000, 0.500), "demo"),
    ("academic_bio_neuron.png",     (0.672, 0.000, 1.000, 1.000), "ai"),
    ("3d:watershed3d.png",          (0.500, 0.000, 1.000, 0.950), "demo"),
    # -- row 7 ------------------------------------------------------------
    ("academic_space_mars.png",     (0.780, 0.000, 1.000, 1.000), "real"),
    ("industrial_blobs.png",        (0.340, 0.000, 0.660, 1.000), "demo"),
    ("academic_met_supercell.png",  (0.672, 0.000, 1.000, 1.000), "ai"),
    ("science_fourier_stars.png",   (0.050, 0.060, 0.500, 0.940), "demo"),
    ("academic_paleo_feathered.png", (0.672, 0.000, 1.000, 1.000), "ai"),
    ("industrial_barcode.png",      (0.000, 0.000, 1.000, 0.850), "demo"),
    ("evis_stereo_fullseye_still.png", (0.500, 0.000, 1.000, 1.000), "demo"),
]

MOSAIC_TAGLINE = ("~1,000 explainable classical vision ops "
                  "(731 2-D + 265 3-D) · pure numpy")

TITLE = "Fullseye"
TAGLINE = ("~1,000 explainable classical vision ops "
           "(731 2-D + 265 3-D)  \u00b7  Physical AI sensing  \u00b7  pure numpy")
PIP_CMD = "$ pip install fullseye"


def _font(path_candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for p in path_candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()  # pragma: no cover


FONT_DIR = "C:/Windows/Fonts"
F_TITLE = lambda s: _font([f"{FONT_DIR}/segoeuib.ttf", f"{FONT_DIR}/arialbd.ttf"], s)
F_TEXT = lambda s: _font([f"{FONT_DIR}/segoeui.ttf", f"{FONT_DIR}/arial.ttf"], s)
F_MONO = lambda s: _font([f"{FONT_DIR}/consola.ttf", f"{FONT_DIR}/cour.ttf"], s)


def cover_crop(im: Image.Image, frac_box, tile_w: int, tile_h: int) -> Image.Image:
    """Crop `frac_box` (fractions of the source), then center cover-crop that
    region to the tile aspect ratio and resize to (tile_w, tile_h)."""
    sw, sh = im.size
    x0, y0, x1, y1 = frac_box
    bx0, by0 = int(x0 * sw), int(y0 * sh)
    bx1, by1 = int(x1 * sw), int(y1 * sh)
    bw, bh = bx1 - bx0, by1 - by0
    want = tile_w / tile_h
    have = bw / bh
    if have > want:                      # box wider than tile -> trim sides
        new_w = int(bh * want)
        off = (bw - new_w) // 2
        bx0, bx1 = bx0 + off, bx0 + off + new_w
    else:                                # box taller than tile -> trim top/bot
        new_h = int(bw / want)
        off = (bh - new_h) // 2
        by0, by1 = by0 + off, by0 + off + new_h
    region = im.crop((bx0, by0, bx1, by1))
    return region.resize((tile_w, tile_h), Image.LANCZOS)


def rounded_mask(w: int, h: int, r: int) -> Image.Image:
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    return m


def draw_accent(canvas: Image.Image, y: int) -> None:
    """Thin horizontal strip blending through ACCENT_STOPS."""
    d = ImageDraw.Draw(canvas)
    n = len(ACCENT_STOPS) - 1
    for x in range(W):
        t = x / (W - 1) * n
        i = min(int(t), n - 1)
        f = t - i
        c0, c1 = ACCENT_STOPS[i], ACCENT_STOPS[i + 1]
        col = tuple(int(c0[k] + (c1[k] - c0[k]) * f) for k in range(3))
        d.line([(x, y), (x, y + ACCENT_H - 1)], fill=col)


def build() -> Image.Image:
    canvas = Image.new("RGB", (W, H), BG)

    # --- mosaic ---------------------------------------------------------
    mosaic_h = H - BAND_H - ACCENT_H
    tile_w = (W - 2 * MARGIN - (COLS - 1) * GAP) // COLS
    tile_h = (mosaic_h - MARGIN - GAP - GAP) // ROWS  # top margin + row gap + bottom gap
    x_left = (W - (COLS * tile_w + (COLS - 1) * GAP)) // 2  # re-center leftover px
    mask = rounded_mask(tile_w, tile_h, CORNER_R)

    for idx, (name, box) in enumerate(TILES):
        src = Image.open(ASSETS / name).convert("RGB")
        tile = cover_crop(src, box, tile_w, tile_h)
        r, c = divmod(idx, COLS)
        x = x_left + c * (tile_w + GAP)
        y = MARGIN + r * (tile_h + GAP)
        canvas.paste(tile, (x, y), mask)

    # --- accent strip + band -------------------------------------------
    band_top = H - BAND_H
    draw_accent(canvas, band_top - ACCENT_H)
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, band_top, W, H), fill=BAND_BG)
    draw_accent(canvas, band_top)  # strip sits at the band's top edge

    # Title
    f_title = F_TITLE(58)
    tx, ty = 36, band_top + 22
    d.text((tx, ty), TITLE, font=f_title, fill=FG)
    title_w = d.textlength(TITLE, font=f_title)

    # pip install pill, right-aligned, vertically centered on the title
    f_mono = F_MONO(25)
    pip_w = d.textlength(PIP_CMD, font=f_mono)
    pad_x, pad_y = 18, 11
    pill_w = int(pip_w) + 2 * pad_x
    pill_h = 25 + 2 * pad_y
    px1 = W - 36
    px0 = px1 - pill_w
    py0 = ty + 14
    py1 = py0 + pill_h
    d.rounded_rectangle((px0, py0, px1, py1), radius=9,
                        fill=PILL_BG, outline=PILL_BORDER, width=2)
    d.text((px0 + pad_x, py0 + pad_y - 3), PIP_CMD, font=f_mono, fill=PILL_FG)

    # Tagline under the title
    f_tag = F_TEXT(24)
    d.text((tx + 2, ty + 78), TAGLINE, font=f_tag, fill=FG_DIM)

    _ = title_w  # (kept for future layout tweaks)
    return canvas


def _mosaic_src(key: str) -> Path:
    if key.startswith("3d:"):
        return ROOT / "examples_3d" / "_gallery" / key[3:]
    return ASSETS / key


def build_mosaic() -> Image.Image:
    """1200x1200 dense 7x7 mosaic + slim bottom brand band (LinkedIn)."""
    n_ai = sum(1 for _, _, kind in MOSAIC_TILES if kind == "ai")
    assert len(MOSAIC_TILES) == MOSAIC_COLS * MOSAIC_ROWS, len(MOSAIC_TILES)
    assert n_ai * 3 <= len(MOSAIC_TILES), f"AI-derived tiles over 1/3: {n_ai}"

    canvas = Image.new("RGB", (MOSAIC_W, MOSAIC_H), BG)

    mosaic_h = MOSAIC_H - MOSAIC_BAND_H - ACCENT_H
    tile_w = (MOSAIC_W - 2 * MOSAIC_MARGIN
              - (MOSAIC_COLS - 1) * MOSAIC_GAP) // MOSAIC_COLS
    tile_h = (mosaic_h - 2 * MOSAIC_MARGIN
              - (MOSAIC_ROWS - 1) * MOSAIC_GAP) // MOSAIC_ROWS
    x_left = (MOSAIC_W - (MOSAIC_COLS * tile_w
                          + (MOSAIC_COLS - 1) * MOSAIC_GAP)) // 2
    mask = rounded_mask(tile_w, tile_h, MOSAIC_CORNER_R)

    for idx, (key, box, _kind) in enumerate(MOSAIC_TILES):
        src = Image.open(_mosaic_src(key)).convert("RGB")
        tile = cover_crop(src, box, tile_w, tile_h)
        r, c = divmod(idx, MOSAIC_COLS)
        x = x_left + c * (tile_w + MOSAIC_GAP)
        y = MOSAIC_MARGIN + r * (tile_h + MOSAIC_GAP)
        canvas.paste(tile, (x, y), mask)

    # --- accent strip + brand band -------------------------------------
    band_top = MOSAIC_H - MOSAIC_BAND_H
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, band_top, MOSAIC_W, MOSAIC_H), fill=BAND_BG)
    # thin accent gradient at the band's top edge (reuse banner stops)
    n = len(ACCENT_STOPS) - 1
    for x in range(MOSAIC_W):
        t = x / (MOSAIC_W - 1) * n
        i = min(int(t), n - 1)
        f = t - i
        c0, c1 = ACCENT_STOPS[i], ACCENT_STOPS[i + 1]
        col = tuple(int(c0[k] + (c1[k] - c0[k]) * f) for k in range(3))
        d.line([(x, band_top - ACCENT_H), (x, band_top - 1)], fill=col)

    # Title (left) / pip pill (right) / tagline (left, under title)
    f_title = F_TITLE(38)
    tx, ty = 28, band_top + 12
    d.text((tx, ty), TITLE, font=f_title, fill=FG)

    f_mono = F_MONO(19)
    pip_w = d.textlength(PIP_CMD, font=f_mono)
    pad_x, pad_y = 14, 9
    pill_w = int(pip_w) + 2 * pad_x
    pill_h = 19 + 2 * pad_y
    px1 = MOSAIC_W - 28
    px0 = px1 - pill_w
    py0 = band_top + (MOSAIC_BAND_H - pill_h) // 2
    d.rounded_rectangle((px0, py0, px1, py0 + pill_h), radius=8,
                        fill=PILL_BG, outline=PILL_BORDER, width=2)
    d.text((px0 + pad_x, py0 + pad_y - 2), PIP_CMD, font=f_mono, fill=PILL_FG)

    f_tag = F_TEXT(19)
    d.text((tx + 2, ty + 52), MOSAIC_TAGLINE, font=f_tag, fill=FG_DIM)
    return canvas


def save(canvas: Image.Image, out_path: Path = OUT_PATH) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, optimize=True, compress_level=9)
    size = out_path.stat().st_size
    if size >= 1_000_000:
        # GitHub social preview requires < 1 MB: quantize with dithering.
        q = canvas.quantize(colors=256, method=Image.MEDIANCUT,
                            dither=Image.FLOYDSTEINBERG)
        q.save(out_path, optimize=True)
        size = out_path.stat().st_size
    print(f"wrote {out_path} ({canvas.size[0]}x{canvas.size[1]}, {size:,} bytes)")
    if size >= 1_000_000:
        print("WARNING: still >= 1 MB", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--variant", choices=("banner", "mosaic"),
                    default="banner",
                    help="banner = 1280x640 GitHub social preview (default); "
                         "mosaic = 1200x1200 dense LinkedIn mosaic")
    args = ap.parse_args()
    if args.variant == "mosaic":
        save(build_mosaic(), MOSAIC_OUT)
    else:
        save(build())


if __name__ == "__main__":
    main()
