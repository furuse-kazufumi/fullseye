# -*- coding: utf-8 -*-
"""Shared helpers for the appendix-F op-category demo strips.

Grid figure: rows = input variations (>=3), cols = pipeline stages
(input / naive-baseline / op-output). Every panel gets a small label bar
(op name in English + Japanese note). Output: PNG <= 400 KB, width ~900-1000 px.
All processing is real Fullseye code (ops registry / unified facade / modules).
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, r"C:\dev\projects\imgevolve")
os.chdir(r"C:\dev\projects\imgevolve")

OUT = r"C:\dev\projects\onocollo-complete\docs\qiita\20260822_g1_evis\ops"
AI_DIR = r"C:\dev\projects\imgevolve\studio_assets\sample_sources_ai"
SAMPLES = r"C:\dev\projects\imgevolve\studio_assets\sample_images"
os.makedirs(OUT, exist_ok=True)

FONT = ImageFont.truetype(r"C:\Windows\Fonts\meiryo.ttc", 15)
FONT_SMALL = ImageFont.truetype(r"C:\Windows\Fonts\meiryo.ttc", 13)

CELL_W = 300          # panel width, 3 cols -> ~910 px total
LABEL_H = 22
GAP = 4


# ---------------------------------------------------------------- inputs
def _center_square(im: Image.Image) -> Image.Image:
    w, h = im.size
    s = min(w, h)
    return im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))


def ai(name, size=384, color=False):
    """AI-generated (Gemini) input photo -> float [0,1], square."""
    im = Image.open(os.path.join(AI_DIR, name + ".png"))
    im = _center_square(im).resize((size, size), Image.LANCZOS)
    im = im.convert("RGB" if color else "L")
    return np.asarray(im).astype(np.float64) / 255.0


def sample(name, size=384, color=False):
    """imgevolve bundled sample image -> float [0,1], square."""
    im = Image.open(os.path.join(SAMPLES, name + ".png"))
    im = _center_square(im).resize((size, size), Image.LANCZOS)
    im = im.convert("RGB" if color else "L")
    return np.asarray(im).astype(np.float64) / 255.0


def skdata(name, size=384, color=False):
    """scikit-image bundled classic test image -> float [0,1], square."""
    import skimage.data as d
    arr = getattr(d, name)()
    if arr.ndim == 3 and not color:
        arr = arr[..., :3].mean(axis=2)
    arr = arr.astype(np.float64)
    if arr.max() > 1.5:
        arr /= 255.0
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    im = _center_square(im).resize((size, size), Image.LANCZOS)
    return np.asarray(im).astype(np.float64) / 255.0


# ---------------------------------------------------------------- display
def to_u8(a, normalize=False):
    a = np.asarray(a, dtype=np.float64)
    if normalize:
        lo, hi = float(np.nanmin(a)), float(np.nanmax(a))
        if hi - lo < 1e-12:
            hi = lo + 1.0
        a = (a - lo) / (hi - lo)
    a = np.clip(a, 0.0, 1.0)
    return (a * 255.0 + 0.5).astype(np.uint8)


def rgb(a, normalize=False):
    u = to_u8(a, normalize)
    if u.ndim == 2:
        u = np.stack([u] * 3, axis=-1)
    return u


def colorize_labels(lab, background=None):
    """label image -> distinct colours; optional gray background where lab==0."""
    lab = np.asarray(lab)
    vals = [v for v in np.unique(lab) if v > 0]
    rng = np.random.default_rng(7)
    out = np.zeros(lab.shape + (3,), dtype=np.uint8)
    if background is not None:
        out[:] = (rgb(background) * 0.35).astype(np.uint8)
    palette = rng.integers(70, 255, size=(max(len(vals), 1), 3))
    for i, v in enumerate(vals):
        out[lab == v] = palette[i]
    return out


def annotate(img_u8, text, xy=(6, 6), color=(255, 230, 60)):
    im = Image.fromarray(img_u8)
    d = ImageDraw.Draw(im)
    bbox = d.textbbox(xy, text, font=FONT)
    d.rectangle([bbox[0] - 4, bbox[1] - 2, bbox[2] + 4, bbox[3] + 2], fill=(20, 20, 25))
    d.text(xy, text, font=FONT, fill=color)
    return np.asarray(im)


def grid(rows, out_name, cell_w=CELL_W):
    """rows: list of rows; each row = list of (label, rgb_uint8) panels.

    Saves to OUT/out_name, palette-compressing until <= 400 KB.
    """
    ncols = max(len(r) for r in rows)
    W = ncols * cell_w + (ncols - 1) * GAP
    # resize each panel to cell_w, compute row heights
    prepared, heights = [], []
    for r in rows:
        pr = []
        h_max = 0
        for label, arr in r:
            im = Image.fromarray(arr)
            h = int(round(im.height * cell_w / im.width))
            pr.append((label, im.resize((cell_w, h), Image.LANCZOS)))
            h_max = max(h_max, h)
        prepared.append(pr)
        heights.append(h_max + LABEL_H)
    H = sum(heights) + GAP * (len(rows) - 1)
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    y = 0
    for pr, rh in zip(prepared, heights):
        x = 0
        for label, im in pr:
            d.rectangle([x, y, x + cell_w - 1, y + LABEL_H - 1], fill=(34, 38, 46))
            d.text((x + 5, y + 3), label, font=FONT_SMALL, fill=(235, 235, 240))
            canvas.paste(im, (x, y + LABEL_H))
            x += cell_w + GAP
        y += rh + GAP
    path = os.path.join(OUT, out_name)
    _save_small(canvas, path)
    return path


def _save_small(canvas: Image.Image, path: str, limit=400_000):
    canvas.save(path, optimize=True)
    for colors in (256, 160, 96, 64):
        if os.path.getsize(path) <= limit:
            break
        q = canvas.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
        q.save(path, optimize=True)
    scale = 1.0
    while os.path.getsize(path) > limit and scale > 0.45:   # shrink until it fits
        scale *= 0.85
        w, h = canvas.size
        small = canvas.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        small.quantize(colors=128, method=Image.MEDIANCUT).save(path, optimize=True)
    print("saved %s (%d KB)" % (os.path.basename(path), os.path.getsize(path) // 1024))


# ---------------------------------------------------------------- manifest
MANIFEST = os.path.join(OUT, "_manifest_entries.json")


def record(entry: dict):
    data = []
    if os.path.exists(MANIFEST):
        data = json.load(open(MANIFEST, encoding="utf-8"))
    data = [e for e in data if e.get("file") != entry.get("file")]
    data.append(entry)
    json.dump(data, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def run_jobs(jobs):
    import traceback
    ok, bad = [], []
    for name, fn in jobs:
        try:
            fn()
            ok.append(name)
        except Exception as e:
            traceback.print_exc()
            bad.append((name, "%s: %s" % (type(e).__name__, e)))
    print("\n=== %d ok, %d failed ===" % (len(ok), len(bad)))
    for n, msg in bad:
        print("FAIL", n, msg)
