#!/usr/bin/env python3
"""Academic cross-discipline sample gallery for articles + debugging.

Builds a museum-style gallery of "before -> after" fullseye processing montages
across academic fields (medicine / archaeology / biology / space / paleontology
/ geology / meteorology / oceanography / botany).

Two data routes:
  A) Real open-licensed downloads (NASA images API = public domain, Met Museum
     Open Access = CC0, Smithsonian Open Access = CC0).
     Every download's source URL + license is recorded.
  B) AI-generated simulated data (Google gemini-2.5-flash-image first --
     OpenAI credits were exhausted at build time -- fallback gpt-image-1) for
     fields where clean licensing is hard. Every generated image is labeled
     "AI-generated (model) simulated data" on the image itself, in the
     attribution table and in the article snippet. Never presented as real.

Outputs (never touches GALLERY.md / existing gen_* tools):
  data/academic_samples/                    download + generation cache (re-run safe)
  docs/articles/assets/academic_<slug>.png  full montage (original -> processed)
  docs/articles/assets/academic_<slug>_thumb.jpg   720px-wide JPG q85
  docs/articles/assets/ACADEMIC_ATTRIBUTION.md     source/license table
  docs/articles/assets/_academic_gallery_snippet.md  article snippet (raw URLs)

Usage:
  py -3.11 tools/gen_academic_gallery.py                    # everything
  py -3.11 tools/gen_academic_gallery.py --subjects space,biology
  py -3.11 tools/gen_academic_gallery.py --skip-ai          # real downloads only
  py -3.11 tools/gen_academic_gallery.py --only ammonite    # slug substring
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import fullseye as fs  # noqa: E402
import fourierdesc as fd  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

DATA = os.path.join(ROOT, "data", "academic_samples")
ASSETS = os.path.join(ROOT, "docs", "articles", "assets")
RAW_BASE = "https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets"
UA = "fullseye-academic-gallery/1.0 (open-data sample fetch; polite, low volume)"
API_KEYS_PATH = r"C:\dev\api-keys.json"
AI_MAX = 40  # hard cap on AI generations per full run (billing guard)

FINDINGS: list[str] = []          # op bugs / oddities discovered while processing
AI_GENERATED_NOW: list[str] = []  # slugs actually billed this run (not cached)

# --------------------------------------------------------------------------- io


def log(msg: str) -> None:
    print(msg, flush=True)


def http_get(url: str, timeout: int = 60, retries: int = 2) -> bytes:
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # polite: short backoff, few retries
            last = e
            if attempt < retries:
                time.sleep(3.0 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries + 1} tries: {url}: {last}")


def cached_download(url: str, fname: str, meta: dict) -> str | None:
    """Download url into DATA/fname unless cached. Writes fname.meta.json. None on failure."""
    os.makedirs(DATA, exist_ok=True)
    dest = os.path.join(DATA, fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    try:
        blob = http_get(url)
    except Exception as e:
        log(f"  [skip] download failed: {url} ({e})")
        return None
    with open(dest, "wb") as f:
        f.write(blob)
    meta = dict(meta)
    meta["download_url"] = url
    with open(dest + ".meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    log(f"  [dl] {fname} ({len(blob) // 1024} KB)")
    return dest


def load_image(path: str, max_side: int = 1024) -> np.ndarray:
    """Any raster file -> float64 RGB HxWx3 in [0,1], downscaled to max_side."""
    im = Image.open(path)
    if im.mode in ("I;16", "I;16B", "I"):
        arr = np.asarray(im, dtype=np.float64)
        lo, hi = np.percentile(arr, [0.5, 99.5])
        arr = np.clip((arr - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
        im = Image.fromarray((arr * 255).astype(np.uint8), "L")
    im = im.convert("RGB")
    w, h = im.size
    s = max(w, h)
    if s > max_side:
        im = im.resize((max(1, w * max_side // s), max(1, h * max_side // s)), Image.LANCZOS)
    return np.asarray(im, dtype=np.float64) / 255.0


def to_u8(arr: np.ndarray) -> np.ndarray:
    a = np.clip(np.nan_to_num(np.asarray(arr, dtype=np.float64)), 0.0, 1.0)
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    return (a * 255).astype(np.uint8)


# ---------------------------------------------------------------- op wrappers


def gray(col: np.ndarray) -> np.ndarray:
    return fs.apply(col, "rgb1_to_gray")


def ap(img: np.ndarray, name: str, a: float = 0.5, b: float = 0.5):
    """fullseye.apply with the debug mandate: exceptions / NaN / degenerate output
    are recorded as findings (with a minimal repro line) instead of crashing."""
    try:
        out = fs.apply(img, name, a, b)
    except Exception as e:
        FINDINGS.append(
            f"op `{name}` raised {type(e).__name__}: {e} -- repro: "
            f"fs.apply(<{img.shape if hasattr(img, 'shape') else type(img)} float01>, '{name}', {a}, {b})"
        )
        raise
    if isinstance(out, np.ndarray):
        if not np.all(np.isfinite(out)):
            FINDINGS.append(
                f"op `{name}` produced non-finite values (a={a}, b={b}, in shape {img.shape})"
            )
        elif out.size and float(np.max(out)) == float(np.min(out)):
            FINDINGS.append(
                f"op `{name}` produced a constant image ({float(np.max(out)):.3f}) "
                f"(a={a}, b={b}, in shape {img.shape}) -- possibly degenerate on this data"
            )
    return out


def norm01(arr: np.ndarray) -> np.ndarray:
    """Robust display normalization (1..99.5 percentile) so a few extreme
    pixels do not flatten the whole map."""
    a = np.asarray(arr, dtype=np.float64)
    lo, hi = np.nanpercentile(a, [1.0, 99.5])
    return np.zeros_like(a) if hi - lo < 1e-12 else np.clip((a - lo) / (hi - lo), 0.0, 1.0)


def heat(arr: np.ndarray) -> np.ndarray:
    """Scalar [0,1] map -> simple perceptual pseudocolor (dark blue -> yellow)."""
    a = np.clip(norm01(arr), 0, 1)
    r = np.clip(1.5 * a - 0.25, 0, 1)
    g = np.clip(1.5 * a - 0.10, 0, 1) ** 1.2
    b = np.clip(1.0 - 1.6 * a, 0, 1) * 0.8 + 0.15 * (1 - a)
    return np.stack([r, g, b], axis=-1)


def overlay(col: np.ndarray, mask: np.ndarray, color=(1.0, 0.15, 0.1), alpha=0.85) -> np.ndarray:
    return fs.overlay_mask(col, mask > 0.5, color=color, alpha=alpha)


# ------------------------------------------------------------------- montage


def _font(size: int):
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def montage(panels: list[tuple[str, np.ndarray]], out_png: str, ai_tag: str | None = None,
            panel_h: int = 512) -> None:
    """Side-by-side labeled panels -> PNG. ai_tag stamps every panel corner."""
    gap, bar = 6, 34
    font, tagfont = _font(18), _font(15)
    ims = []
    for label, arr in panels:
        u8 = to_u8(arr)
        im = Image.fromarray(u8)
        w, h = im.size
        im = im.resize((max(1, int(w * panel_h / h)), panel_h), Image.LANCZOS)
        ims.append((label, im))
    total_w = sum(im.size[0] for _, im in ims) + gap * (len(ims) - 1)
    canvas = Image.new("RGB", (total_w, panel_h + bar), (24, 24, 28))
    draw = ImageDraw.Draw(canvas, "RGBA")
    x = 0
    for label, im in ims:
        canvas.paste(im, (x, 0))
        if ai_tag:
            tw = draw.textlength(ai_tag, font=tagfont)
            draw.rectangle([x + 6, 6, x + 14 + tw, 28], fill=(0, 0, 0, 170))
            draw.text((x + 10, 8), ai_tag, fill=(255, 210, 90), font=tagfont)
        draw.text((x + 8, panel_h + 7), label, fill=(235, 235, 235), font=font)
        x += im.size[0] + gap
    canvas.save(out_png)


def write_thumb(png_path: str, thumb_path: str, width: int = 720) -> None:
    im = Image.open(png_path).convert("RGB")
    w, h = im.size
    im = im.resize((width, max(1, h * width // w)), Image.LANCZOS)
    im.save(thumb_path, "JPEG", quality=85)


# --------------------------------------------------------------- data route A


def fetch_nasa(query: str, slug: str) -> tuple[str, dict] | None:
    """NASA images API (public domain). Returns (path, source_meta)."""
    cache = os.path.join(DATA, f"{slug}.jpg")
    metap = cache + ".meta.json"
    if os.path.exists(cache) and os.path.exists(metap):
        return cache, json.load(open(metap, encoding="utf-8"))
    try:
        d = json.loads(http_get(
            "https://images-api.nasa.gov/search?q=" + urllib.parse.quote(query)
            + "&media_type=image&page_size=5"))
        items = d["collection"]["items"]
        if not items:
            return None
        item = items[0]
        data0 = item["data"][0]
        # asset manifest -> prefer ~large, else ~orig, else first jpg
        assets = json.loads(http_get(item["href"]))
        # collection.json is a plain JSON list of URL strings
        if isinstance(assets, dict):
            assets = assets.get("collection", {}).get("items", [])
        hrefs = [u["href"] if isinstance(u, dict) else str(u) for u in assets]
        hrefs = [u.replace("http://", "https://") for u in hrefs]
        pick = (next((u for u in hrefs if "~large" in u), None)
                or next((u for u in hrefs if "~medium" in u), None)
                or next((u for u in hrefs if "~orig" in u and u.lower().endswith((".jpg", ".png"))), None)
                or next((u for u in hrefs if u.lower().endswith(".jpg")), None))
        if not pick:
            return None
        meta = {
            "title": data0.get("title", ""),
            "source": f"https://images.nasa.gov/details/{data0.get('nasa_id', '')}",
            "license": "Public domain (NASA)",
            "credit": data0.get("secondary_creator") or data0.get("center", "NASA"),
        }
        p = cached_download(pick.replace(" ", "%20"), f"{slug}.jpg", meta)
        return (p, meta) if p else None
    except Exception as e:
        log(f"  [skip] NASA fetch failed for '{query}': {e}")
        return None


def fetch_met(query: str, slug: str, max_checks: int = 10) -> tuple[str, dict] | None:
    """Met Museum Open Access (CC0 only: isPublicDomain=true)."""
    cache = os.path.join(DATA, f"{slug}.jpg")
    metap = cache + ".meta.json"
    if os.path.exists(cache) and os.path.exists(metap):
        return cache, json.load(open(metap, encoding="utf-8"))
    try:
        d = json.loads(http_get(
            "https://collectionapi.metmuseum.org/public/collection/v1/search?q="
            + urllib.parse.quote(query) + "&hasImages=true"))
        for oid in (d.get("objectIDs") or [])[:max_checks]:
            time.sleep(0.4)  # polite
            try:
                obj = json.loads(http_get(
                    f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}"))
            except Exception:
                continue
            if not obj.get("isPublicDomain"):
                continue
            img = obj.get("primaryImageSmall") or obj.get("primaryImage")
            if not img:
                continue
            meta = {
                "title": obj.get("title", ""),
                "source": obj.get("objectURL", f"https://www.metmuseum.org/art/collection/search/{oid}"),
                "license": "CC0 (The Met Open Access)",
                "credit": "The Metropolitan Museum of Art",
            }
            p = cached_download(img, f"{slug}.jpg", meta)
            if p:
                return p, meta
        log(f"  [skip] Met: no public-domain image for '{query}'")
        return None
    except Exception as e:
        log(f"  [skip] Met fetch failed for '{query}': {e}")
        return None


def fetch_smithsonian(query: str, slug: str) -> tuple[str, dict] | None:
    """Smithsonian Open Access, CC0 media only (DEMO_KEY, very low volume)."""
    cache = os.path.join(DATA, f"{slug}.jpg")
    metap = cache + ".meta.json"
    if os.path.exists(cache) and os.path.exists(metap):
        return cache, json.load(open(metap, encoding="utf-8"))
    try:
        d = json.loads(http_get(
            "https://api.si.edu/openaccess/api/v1.0/search?q=" + urllib.parse.quote(query)
            + "&api_key=DEMO_KEY&rows=10"))
        for row in d.get("response", {}).get("rows", []):
            dnr = row.get("content", {}).get("descriptiveNonRepeating", {})
            for m in dnr.get("online_media", {}).get("media", []):
                if m.get("type") != "Images":
                    continue
                if (m.get("usage", {}) or {}).get("access") != "CC0":
                    continue
                url = m.get("content") or m.get("thumbnail")
                if not url:
                    continue
                meta = {
                    "title": row.get("title", ""),
                    "source": dnr.get("record_link") or dnr.get("guid", ""),
                    "license": "CC0 (Smithsonian Open Access)",
                    "credit": dnr.get("data_source", "Smithsonian Institution"),
                }
                p = cached_download(url, f"{slug}.jpg", meta)
                if p:
                    return p, meta
        log(f"  [skip] Smithsonian: no CC0 image for '{query}'")
        return None
    except Exception as e:
        log(f"  [skip] Smithsonian fetch failed for '{query}': {e}")
        return None


# --------------------------------------------------------------- data route B


def _openai_key() -> str | None:
    try:
        return json.load(open(API_KEYS_PATH, encoding="utf-8")).get("OPENAI_API_KEY")
    except Exception:
        return None


def _gemini_key() -> str | None:
    try:
        return json.load(open(API_KEYS_PATH, encoding="utf-8")).get("GEMINI_API_KEY")
    except Exception:
        return None


def _save_ai(cache: str, metap: str, blob: bytes, model: str, provider: str,
             prompt: str, slug: str) -> tuple[str, dict]:
    with open(cache, "wb") as f:
        f.write(blob)
    meta = {
        "title": f"AI-generated simulated data ({model})",
        "source": f"generated by {provider} {model}",
        "license": f"AI-generated ({provider} {model}) -- simulated data, NOT a real specimen/scan",
        "credit": f"{provider} {model}",
        "model": model,
        "prompt": prompt,
    }
    with open(metap, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    AI_GENERATED_NOW.append(f"{slug} ({model})")
    log(f"  [ai] generated {slug} with {model}")
    return cache, meta


def generate_ai(prompt: str, slug: str) -> tuple[str, dict] | None:
    """AI simulated-data image. Tries Gemini 2.5 Flash Image first (OpenAI
    account had no credits at build time, 2026-08-30), then OpenAI gpt-image-1.
    Cached on disk; each slug is billed at most once across re-runs."""
    cache = os.path.join(DATA, f"{slug}.png")
    metap = cache + ".meta.json"
    if os.path.exists(cache) and os.path.exists(metap):
        return cache, json.load(open(metap, encoding="utf-8"))
    gkey = _gemini_key()
    if gkey:
        try:
            body = {"contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseModalities": ["IMAGE"]}}
            req = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.5-flash-image:generateContent?key={gkey}",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "User-Agent": UA},
                method="POST")
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.loads(r.read())
            for part in resp["candidates"][0]["content"]["parts"]:
                if "inlineData" in part:
                    blob = base64.b64decode(part["inlineData"]["data"])
                    return _save_ai(cache, metap, blob, "gemini-2.5-flash-image",
                                    "Google", prompt, slug)
            log(f"  [ai] gemini returned no image part for {slug}")
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode()[:200]
            except Exception:
                detail = ""
            log(f"  [ai] gemini failed for {slug}: HTTP {e.code} {detail}")
        except Exception as e:
            log(f"  [ai] gemini failed for {slug}: {e}")
    okey = _openai_key()
    if okey:
        try:
            body = {"model": "gpt-image-1", "prompt": prompt,
                    "size": "1024x1024", "quality": "medium", "n": 1}
            req = urllib.request.Request(
                "https://api.openai.com/v1/images/generations",
                data=json.dumps(body).encode(),
                headers={"Authorization": f"Bearer {okey}",
                         "Content-Type": "application/json", "User-Agent": UA},
                method="POST")
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.loads(r.read())
            item = resp["data"][0]
            blob = (base64.b64decode(item["b64_json"]) if "b64_json" in item
                    else http_get(item["url"]))
            return _save_ai(cache, metap, blob, "gpt-image-1", "OpenAI", prompt, slug)
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode()[:200]
            except Exception:
                detail = ""
            log(f"  [ai] gpt-image-1 failed for {slug}: HTTP {e.code} {detail}")
        except Exception as e:
            log(f"  [ai] gpt-image-1 failed for {slug}: {e}")
    if not gkey and not okey:
        log(f"  [skip] no GEMINI_API_KEY / OPENAI_API_KEY for {slug}")
    return None


# ------------------------------------------------------------------- recipes
# Each recipe: (color_float01) -> (panels[(label, arr)], ops_used[str])


def rec_enhance(col):
    g = gray(col)
    c = ap(g, "cv_clahe", 0.6, 0.5)
    u = np.clip(ap(c, "unsharp", 0.6, 0.5), 0, 1)
    return ([("original", col), ("cv_clahe (local contrast)", c), ("cv_clahe -> unsharp", u)],
            ["rgb1_to_gray", "cv_clahe", "unsharp"])


def rec_xray(col):
    g = gray(col)
    c = ap(g, "cv_clahe", 0.65, 0.5)
    s = norm01(ap(g, "sobel_amp", 0.5, 0.5))
    return ([("original", col), ("cv_clahe (bone/lung detail)", c), ("sobel_amp edge map", heat(s))],
            ["rgb1_to_gray", "cv_clahe", "sobel_amp"])


def rec_edges(col):
    g = gray(col)
    e = ap(g, "canny", 0.5, 0.5)
    return ([("original", col), ("canny edges", 1.0 - e),
             ("edge overlay", overlay(col, e))],
            ["rgb1_to_gray", "canny", "overlay_mask"])


def rec_filaments(col, top_pct: float = 3.0, med_a: float = 0.2):
    """Filament extraction shown as a colored overlay, not a raw response map.

    The raw sk_frangi response is salt-and-pepper on busy data (star fields):
    the op ignores its a/b knobs (docs/KNOWN_ISSUES.md #2, fixed scale set), so
    we cannot tune it. Instead: median prefilter (kills point sources like
    stars), frangi, keep only the top `top_pct`% strongest response, drop tiny
    speckle components (sk_area_opening), then overlay the surviving filaments
    in magenta on a dimmed original so the reader sees WHERE they run.
    """
    g = gray(col)
    c = ap(g, "cv_clahe", 0.6, 0.5)
    m = ap(c, "cv_median", med_a, 0.5)  # 3x3 (med_a=0.2) or 5x5 (0.5): kill point/spike noise
    f = norm01(ap(m, "sk_frangi", 0.5, 0.5))
    thr = float(np.percentile(f, 100.0 - top_pct))
    mask = (f >= thr).astype(np.float64)
    mask = ap(mask, "sk_area_opening", 0.5, 0.5)  # drop specks < ~66 px
    base = np.stack([g] * 3, axis=-1) * 0.5  # dimmed gray: overlay pops
    ov = overlay(base, mask, color=(1.0, 0.2, 0.85), alpha=0.95)
    return ([("original", col), ("cv_clahe", c),
             (f"sk_frangi filaments (top {top_pct:.0f}% overlay)", ov)],
            ["rgb1_to_gray", "cv_clahe", "cv_median", "sk_frangi",
             "sk_area_opening", "overlay_mask"])


def rec_texture(col):
    g = gray(col)
    t = norm01(ap(g, "std_filter", 0.5, 0.5))
    lw = norm01(ap(g, "texture_laws", 0.5, 0.5))
    return ([("original", col), ("std_filter (texture energy)", heat(t)),
             ("texture_laws", heat(lw))],
            ["rgb1_to_gray", "std_filter", "texture_laws"])


def rec_gabor(col):
    g = gray(col)
    ga = norm01(ap(g, "sk_gabor", 0.5, 0.5))
    t = norm01(ap(g, "std_filter", 0.5, 0.5))
    return ([("original", col), ("sk_gabor response", heat(ga)),
             ("std_filter (texture energy)", heat(t))],
            ["rgb1_to_gray", "sk_gabor", "std_filter"])


def rec_segment_count(col, invert=False, min_area=25):
    g = gray(col)
    objs = fs.segment_objects(g, threshold="otsu", invert=invert, min_area=min_area)
    labels = np.zeros(g.shape, dtype=np.int32)
    for i, o in enumerate(objs, start=1):
        labels[o["mask"]] = i
    colored = fs.colorize_labels(labels)
    n = len(objs)
    binm = (labels > 0).astype(float)
    n_op = ap(binm, "count_obj", 0.5, 0.5)
    return ([("original", col), ("otsu segmentation", 1.0 - binm),
             (f"labeled objects (count = {n})", colored)],
            ["rgb1_to_gray", "segment_objects(otsu)", "count_obj", "colorize_labels"]), n, n_op


def rec_multiotsu(col):
    g = gray(col)
    q = ap(g, "xsk2_multiotsu", 0.5, 0.5)
    lv = np.unique(np.round(q, 6))
    labels = np.searchsorted(lv, np.round(q, 6)).astype(np.int32)
    colored = fs.colorize_labels(labels + 1)
    return ([("original", col), ("multi-Otsu classes", q), ("class pseudocolor", colored)],
            ["rgb1_to_gray", "xsk2_multiotsu", "colorize_labels"])


def rec_dstretch(col):
    """DStretch-style decorrelation on RGB.

    NOTE (recorded as a finding): fs.spec_decorrelation_stretch refuses B=3
    (RGB is the `color` sort, cubes are B>3) -- by-contract fail-closed, but it
    means the classic archaeology "DStretch on an RGB photo" use case has no
    spectral-op path. The registered HALCON-parity op `principal_comp`
    (color->color PCA) covers it.
    """
    ds = norm01(ap(col, "principal_comp", 0.5, 0.5))
    g = gray(col)
    c = ap(g, "cv_clahe", 0.6, 0.5)
    return ([("original", col), ("principal_comp (decorrelation)", ds), ("cv_clahe", c)],
            ["principal_comp", "rgb1_to_gray", "cv_clahe"])


def rec_fft(col):
    g = gray(col)
    c = ap(g, "cv_clahe", 0.55, 0.5)
    spec = np.log1p(fs.cx_magnitude(fs.cx_fft(g)))
    lo, hi = float(spec.min()), float(spec.max())  # full range: spectrum has a huge DC peak
    spec = (spec - lo) / max(hi - lo, 1e-12)
    return ([("original", col), ("cv_clahe", c), ("log |FFT| spectrum", spec)],
            ["rgb1_to_gray", "cv_clahe", "cx_fft", "cx_magnitude"])


def rec_flowdir(col):
    g = ap(gray(col), "cv_clahe", 0.6, 0.5)   # enhance first: cloud decks are low-contrast
    amp = norm01(ap(g, "sobel_amp", 0.5, 0.5))
    dire = ap(g, "sobel_dir", 0.5, 0.5)
    theta = dire * 2 * np.pi
    u, v = amp * np.cos(theta), amp * np.sin(theta)
    wheel = fs.colorize_flow(u, v)
    return ([("original", col), ("sobel_amp", heat(amp)),
             ("gradient direction wheel", wheel)],
            ["rgb1_to_gray", "cv_clahe", "sobel_amp", "sobel_dir", "colorize_flow"])


def rec_relief(col):
    g = gray(col)
    th = norm01(ap(g, "gray_tophat", 0.6, 0.5)) ** 0.5  # gamma for display
    c = ap(g, "cv_clahe", 0.6, 0.5)
    return ([("original", col), ("gray_tophat (carving relief)", th), ("cv_clahe", c)],
            ["rgb1_to_gray", "gray_tophat", "cv_clahe"])


def rec_skeleton(col, invert=False):
    g = gray(col)
    binm = ap(g, "otsu", 0.5, 0.5)
    if invert:
        binm = 1.0 - binm
    binm = ap(binm, "fill_up", 0.5, 0.5)
    sk = ap(binm, "morph_skeleton", 0.5, 0.5)
    return ([("original", col), ("otsu region", 1.0 - binm),
             ("morph_skeleton overlay", overlay(col, sk, color=(0.1, 1.0, 0.3)))],
            ["rgb1_to_gray", "otsu", "fill_up", "morph_skeleton", "overlay_mask"])


def rec_distance(col, invert=False):
    g = gray(col)
    binm = ap(g, "otsu", 0.5, 0.5)
    if invert:
        binm = 1.0 - binm
    binm = ap(binm, "fill_up", 0.5, 0.5)
    dt = norm01(ap(binm, "dist_transform", 0.5, 0.5))
    return ([("original", col), ("otsu region", 1.0 - binm), ("dist_transform", heat(dt))],
            ["rgb1_to_gray", "otsu", "fill_up", "dist_transform"])


def rec_efd(col):
    """Shape description: silhouette -> elliptic Fourier reconstruction overlay.

    NOTE (bug workaround, reported as a finding): fullseye op
    `gen_contour_region_xld` returns boundary points in raster order, not traced
    order, which silently breaks order-sensitive consumers like
    fourierdesc.elliptic_fourier. We therefore order the boundary by angle around
    the centroid (star-convex approximation, fine for vase silhouettes).
    """
    g = gray(col)
    binm = ap(g, "otsu", 0.5, 0.5)
    if float(binm.mean()) > 0.5:  # foreground should be minority
        binm = 1.0 - binm
    binm = ap(binm, "fill_up", 0.5, 0.5)
    objs = fs.segment_objects(binm, threshold=0.5, min_area=200)
    if not objs:
        raise RuntimeError("EFD: no object found")
    mask = max(objs, key=lambda o: o["area"])["mask"]
    # Ordered boundary trace (marching squares). Angle-sort fails on
    # non-star-convex shapes (amphora handles), so trace properly.
    from skimage import measure
    contours = measure.find_contours(mask.astype(float), 0.5)
    pts = max(contours, key=len)  # (row, col), ordered
    model = fd.elliptic_fourier(pts, 40)
    base = to_u8(col)
    im = Image.fromarray(base)
    draw = ImageDraw.Draw(im)
    colors = {2: (255, 80, 80), 8: (255, 200, 60), 32: (80, 255, 120)}
    for nh, c in colors.items():
        rec = fd.reconstruct(model, 400, n_harmonics=nh)
        poly = [(float(x), float(y)) for y, x in rec]
        draw.line(poly + [poly[0]], fill=c, width=3)
    efd_panel = np.asarray(im, dtype=np.float64) / 255.0
    return ([("original", col), ("silhouette (otsu + fill_up)", 1.0 - mask.astype(float)),
             ("elliptic Fourier: 2 / 8 / 32 harmonics", efd_panel)],
            ["rgb1_to_gray", "otsu", "fill_up", "segment_objects",
             "fourierdesc.elliptic_fourier", "fourierdesc.reconstruct"])


# ------------------------------------------------------------------ exhibits

RECIPES = {
    "enhance": rec_enhance, "xray": rec_xray, "edges": rec_edges,
    "filaments": rec_filaments, "texture": rec_texture, "gabor": rec_gabor,
    "multiotsu": rec_multiotsu, "dstretch": rec_dstretch, "fft": rec_fft,
    "flowdir": rec_flowdir, "relief": rec_relief, "efd": rec_efd,
}

# (subject, slug, fetch spec, recipe, caption-ja)
# fetch spec: ("nasa", query) | ("met", query) | ("bbbc",) | ("si", query) | ("ai", prompt)
EXHIBITS = [
    # ----- 宇宙 (real, NASA public domain)
    ("space", "space_carina", ("nasa", "carina nebula cosmic cliffs webb"), "filaments",
     "星雲のフィラメント構造を sk_frangi(血管強調フィルタ)で抽出"),
    ("space", "space_mars", ("nasa", "mars dunes hirise nili patera"), "texture",
     "火星 Nili Patera 砂丘のテクスチャを std_filter / texture_laws で解析"),
    ("space", "space_galaxy", ("nasa", "spiral galaxy hubble messier 51"), "fft",
     "渦巻銀河の周波数構造を cx_fft スペクトルで可視化"),
    # ----- 地質学 (real NASA + AI)
    ("geology", "geo_earth", ("nasa", "grand canyon from space"), "dstretch",
     "衛星画像の岩相を decorrelation stretch(リモートセンシング定番)で強調"),
    ("geology", "geo_mineral", ("ai", "Macro photograph of a cluster of amethyst quartz crystals on a dark background, studio lighting, sharp facets, scientific mineralogy specimen photography, no text"), "edges",
     "鉱物結晶のファセット稜線を canny で抽出"),
    ("geology", "geo_thin_section", ("ai", "Polarized light microscopy image of a granite rock thin section, interference colors, interlocking mineral grains of quartz feldspar and biotite, petrographic microscope view, no text"), "multiotsu",
     "岩石薄片(偏光顕微鏡風)を multi-Otsu で鉱物粒子に分類"),
    # ----- 気象学 (real NASA + AI)
    ("meteorology", "met_hurricane", ("nasa", "hurricane florence space station"), "flowdir",
     "ハリケーンの渦構造を sobel_dir 勾配方向ホイールで可視化"),
    ("meteorology", "met_supercell", ("ai", "Dramatic wide-angle photograph of a supercell thunderstorm over the great plains, rotating wall cloud, storm chasing photography, natural light, no text"), "enhance",
     "スーパーセル積乱雲(AI 生成)を cv_clahe + unsharp で構造強調"),
    # ----- 考古学 (real Met CC0 + AI)
    ("archaeology", "arch_amphora", ("met", "terracotta amphora"), "efd",
     "土器シルエットを楕円フーリエ記述子(EFD)で形状復元(2/8/32 高調波)"),
    ("archaeology", "arch_relief", ("met", "assyrian relief"), "relief",
     "石碑レリーフの彫刻を gray_tophat で浮き彫り強調"),
    ("archaeology", "arch_cave_painting", ("ai", "Prehistoric cave painting of bulls and horses in ochre and charcoal pigments on a limestone cave wall, Lascaux style, dim warm lighting, archaeological photography, no text"), "dstretch",
     "洞窟壁画(AI 生成)を decorrelation stretch で顔料強調(DStretch 手法)"),
    ("archaeology", "arch_cuneiform", ("ai", "Close-up photograph of an ancient clay tablet covered in cuneiform script, raking light emphasizing the wedge-shaped impressions, museum artifact photography, no text"), "relief",
     "楔形文字粘土板(AI 生成)を gray_tophat で文字刻印強調"),
    # ----- 生物学 (real BBBC CC-BY + AI)
    ("biology", "bio_cells", ("bbbc",), "segment_count",
     "HT29 細胞蛍光顕微鏡像(BBBC001)を otsu 分割 -> ラベル彩色 -> count_obj で計数"),
    ("biology", "bio_neuron", ("ai", "Fluorescence microscopy image of a single neuron with long branching dendrites, green fluorescent protein labeling on black background, confocal microscope, scientific imaging, no text"), "filaments",
     "神経細胞蛍光像(AI 生成)の樹状突起を sk_frangi でトレース"),
    ("biology", "bio_diatoms", ("ai", "Dark-field light microscopy image of many diverse diatoms with intricate glass shells scattered on a dark background, various geometric shapes, scientific microscopy, no text"), "segment_count",
     "珪藻顕微鏡像(AI 生成)を分割・計数"),
    ("biology", "bio_deepsea", ("ai", "Deep sea anglerfish with glowing bioluminescent lure in the dark abyss, underwater scientific expedition photography, faint blue light, no text"), "enhance",
     "深海生物(AI 生成)の暗部を cv_clahe で増強"),
    ("biology", "bio_butterfly", ("ai", "Extreme macro photograph of a blue morpho butterfly wing showing iridescent scales in overlapping rows, scientific macro photography, no text"), "gabor",
     "蝶の翅鱗粉(AI 生成)の周期構造を sk_gabor で解析"),
    # ----- 古生物学 (real Smithsonian CC0 + AI 生体復元が目玉)
    ("paleontology", "paleo_ammonite_real", ("si", "ammonite fossil"), "edges",
     "アンモナイト化石(Smithsonian CC0)の螺旋を canny で抽出"),
    ("paleontology", "paleo_trex", ("ai", "Photorealistic life reconstruction of a Tyrannosaurus rex with detailed scaly textured skin and subtle feathering on the back, standing full-body side view in a Cretaceous floodplain with ferns, overcast natural light, museum-quality paleoart, no text"), "texture",
     "ティラノサウルス生体復元(AI 生成)の皮膚テクスチャを std_filter で解析"),
    ("paleontology", "paleo_triceratops", ("ai", "Photorealistic life reconstruction of a Triceratops with wrinkled elephant-like skin and keratinous frill, full body view in a Cretaceous forest clearing, soft morning light, museum-quality paleoart, no text"), "multiotsu",
     "トリケラトプス生体復元(AI 生成)を multi-Otsu で領域分類"),
    ("paleontology", "paleo_feathered", ("ai", "Photorealistic life reconstruction of a Velociraptor covered in brown and white feathers, bird-like posture, full body side view on a Cretaceous desert dune, golden hour light, museum-quality paleoart, no text"), "gabor",
     "羽毛恐竜生体復元(AI 生成)の羽毛流れを sk_gabor で解析"),
    ("paleontology", "paleo_ammonite_section", ("ai", "Polished cross-section of an ammonite fossil showing the logarithmic spiral of chambers filled with amber and honey colored calcite crystals, macro photography on black background, no text"), "fft",
     "アンモナイト断面(AI 生成)の対数螺旋を FFT スペクトルで観察"),
    ("paleontology", "paleo_trilobite", ("ai", "Detailed trilobite fossil embedded in gray shale rock, raking light showing the segmented exoskeleton in relief, paleontology specimen photography, no text"), "relief",
     "三葉虫化石(AI 生成)の体節を gray_tophat で浮き彫り強調"),
    # ----- 医学 (AI のみ: 実データはライセンス困難)
    ("medicine", "med_chest_xray", ("ai", "Chest X-ray radiograph style grayscale medical image of a healthy adult thorax, ribs lungs and heart shadow visible, frontal PA view, radiology style, simulated educational image, no text no patient information"), "xray",
     "胸部X線風画像(AI 生成)を cv_clahe + sobel_amp で強調・エッジ抽出"),
    ("medicine", "med_histology", ("ai", "Hematoxylin and eosin stained histology slide of intestinal tissue under a light microscope, pink and purple cells with visible nuclei and villi structures, pathology microscopy, simulated educational image, no text"), "multiotsu",
     "H&E 組織切片風画像(AI 生成)を multi-Otsu で組織構造分類"),
    ("medicine", "med_brain_mri", ("ai", "Axial T1-weighted brain MRI scan style grayscale medical image showing brain anatomy with clear gray and white matter contrast, radiology style, simulated educational image, no text no patient information"), "enhance",
     "脳 MRI 風画像(AI 生成)を cv_clahe + unsharp で組織コントラスト強調"),
    ("medicine", "med_blood_smear", ("ai", "Light microscopy image of a blood smear with many red blood cells and a few purple stained white blood cells, hematology microscopy at high magnification, simulated educational image, no text"), "segment_count",
     "血液塗抹風画像(AI 生成)の血球を分割・計数"),
    ("medicine", "med_anatomy_heart", ("ai", "Vintage anatomical illustration of a human heart with labeled chambers drawn in the style of a 19th century medical atlas, sepia ink on aged paper, detailed engraving style, simulated illustration"), "edges",
     "解剖図風イラスト(AI 生成)の輪郭を canny で抽出"),
    # ----- 海洋学 / 植物学 (AI)
    ("oceanography", "ocean_coral", ("ai", "Vibrant coral reef with diverse coral species and small tropical fish, clear turquoise water, underwater marine biology survey photography, natural sunlight rays, no text"), "multiotsu",
     "サンゴ礁(AI 生成)を multi-Otsu で被覆分類(海洋調査風)"),
    ("botany", "bot_fern", ("ai", "Backlit photograph of a single fern frond showing the branching vein network and fractal leaflet pattern, dark background, botanical photography, no text"), "filaments",
     "シダ葉脈(AI 生成)を sk_frangi で葉脈抽出"),
    ("botany", "bot_pollen", ("ai", "Scanning electron microscope style grayscale image of diverse pollen grains with spiky and patterned surfaces, SEM microscopy, scientific imaging, no text"), "segment_count",
     "花粉 SEM 風画像(AI 生成)を分割・計数"),
]


# ---------------------------------------------------------------------- main


def run_exhibit(subject: str, slug: str, spec: tuple, recipe: str, caption: str,
                skip_ai: bool, skip_real: bool):
    kind = spec[0]
    log(f"[{subject}] {slug} ({kind}, recipe={recipe})")
    if kind == "ai":
        if skip_ai:
            log("  [skip] --skip-ai")
            return None
        got = generate_ai(spec[1], f"ai_{slug}")
    else:
        if skip_real:
            log("  [skip] --skip-real")
            return None
        if kind == "nasa":
            got = fetch_nasa(spec[1], f"real_{slug}")
        elif kind == "met":
            got = fetch_met(spec[1], f"real_{slug}")
        elif kind == "bbbc":
            got = fetch_bbbc001(f"real_{slug}")
        elif kind == "si":
            got = fetch_smithsonian(spec[1], f"real_{slug}")
        else:
            raise ValueError(kind)
    if not got:
        return None
    path, meta = got
    col = load_image(path)
    is_ai = kind == "ai"
    count_note = ""
    try:
        if recipe == "segment_count":
            invert = slug in ("med_blood_smear",)  # dark objects on bright field
            (panels, ops_used), n, n_op = rec_segment_count(col, invert=invert)
            count_note = f" 検出数 = {n}"
            if int(n_op) != n:
                FINDINGS.append(
                    f"count_obj={int(n_op)} vs segment_objects={n} on {slug}: count_obj "
                    "uses 4-connectivity while segment_objects defaults to 8-connectivity "
                    "(verified: a diagonal pixel pair counts as 2 vs 1) -- API consistency gap")
        elif recipe == "filaments":
            # per-subject response density: nebula ridges / fern veins are
            # broader + fainter than neuron dendrites, so keep a larger slice
            # NOTE: keep the median at 3x3 even for the star field -- a 5x5
            # median turns bright stars into small disks whose frangi ring
            # response survives area opening as dots (tried, visually worse).
            top = {"space_carina": 10.0, "bot_fern": 8.0}.get(slug, 3.0)
            panels, ops_used = rec_filaments(col, top_pct=top)
        else:
            panels, ops_used = RECIPES[recipe](col)
    except Exception as e:
        log(f"  [fail] recipe {recipe} on {slug}: {e}")
        return None
    ai_model = meta.get("model", "")
    ai_tag = f"AI-generated ({ai_model})" if is_ai else None
    out_png = os.path.join(ASSETS, f"academic_{slug}.png")
    montage(panels, out_png, ai_tag=ai_tag)
    thumb = os.path.join(ASSETS, f"academic_{slug}_thumb.jpg")
    write_thumb(out_png, thumb)
    log(f"  [ok] {os.path.basename(out_png)}  ops: {', '.join(ops_used)}")
    return {
        "subject": subject, "slug": slug, "is_ai": is_ai, "meta": meta,
        "ops": ops_used, "caption": caption + count_note,
        "png": os.path.basename(out_png), "thumb": os.path.basename(thumb),
    }


SUBJECT_JA = {
    "space": "宇宙", "geology": "地質学", "meteorology": "気象学",
    "archaeology": "考古学", "biology": "生物学", "paleontology": "古生物学",
    "medicine": "医学", "oceanography": "海洋学", "botany": "植物学",
}


def write_attribution(results: list[dict]) -> None:
    p = os.path.join(ASSETS, "ACADEMIC_ATTRIBUTION.md")
    lines = [
        "# Academic gallery — attribution / 出典とライセンス",
        "",
        "`academic_*.png` (tools/gen_academic_gallery.py 生成) の全素材の出典。",
        "**「AI 生成」列が Yes の画像は画像生成 AI(モデル名は表に記載)による模擬データであり、実在の標本・スキャン・観測ではない。**",
        "実データはすべて public domain / CC0 / CC-BY のみを使用。",
        "",
        "| 画像 | 分野 | 素材 | AI 生成 | 出典 / ライセンス | 使用 op |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda r: (r["subject"], r["slug"])):
        m = r["meta"]
        ai = f"**Yes** ({m.get('model', '')})" if r["is_ai"] else "No"
        if r["is_ai"]:
            src = f"AI 生成模擬データ({m.get('credit', m.get('model', ''))})— 実データではない"
        else:
            src = f"[{m.get('credit', 'source')}]({m.get('source', '')}) — {m.get('license', '')}"
        title = (m.get("title", "") or "").replace("|", "/")[:60]
        lines.append(
            f"| `{r['png']}` | {SUBJECT_JA.get(r['subject'], r['subject'])} | {title} | {ai} | {src} | {', '.join(r['ops'])} |")
    lines += ["", f"生成日: {time.strftime('%Y-%m-%d')} / スクリプト: `tools/gen_academic_gallery.py`", ""]
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"[write] {p}")


def write_snippet(results: list[dict]) -> None:
    p = os.path.join(ASSETS, "_academic_gallery_snippet.md")
    lines = [
        "<!-- 記事貼り付け用スニペット: 学問分野横断ギャラリー (gen_academic_gallery.py) -->",
        "<!-- 画像はサムネ(720px JPG)。フル解像度は _thumb を外した .png -->",
        "",
    ]
    order = ["paleontology", "space", "medicine", "biology", "archaeology",
             "geology", "meteorology", "oceanography", "botany"]
    by_subj: dict[str, list[dict]] = {}
    for r in results:
        by_subj.setdefault(r["subject"], []).append(r)
    for s in order:
        if s not in by_subj:
            continue
        lines.append(f"## {SUBJECT_JA.get(s, s)}")
        lines.append("")
        for r in by_subj[s]:
            m = r["meta"]
            lines.append(f"![{r['slug']}]({RAW_BASE}/{r['thumb']})")
            if r["is_ai"]:
                origin = f"素材: **AI 生成({m.get('credit', m.get('model', ''))})による模擬データ**(実在の標本・スキャンではない)"
            else:
                origin = f"素材: {m.get('credit', '')} — {m.get('license', '')}([出典]({m.get('source', '')}))"
            lines.append(f"*{r['caption']}(op: `{'`, `'.join(r['ops'])}`)。{origin}*")
            lines.append("")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"[write] {p}")


def main() -> int:
    apar = argparse.ArgumentParser()
    apar.add_argument("--subjects", default="", help="comma-separated subject filter")
    apar.add_argument("--only", default="", help="slug substring filter")
    apar.add_argument("--skip-ai", action="store_true")
    apar.add_argument("--skip-real", action="store_true")
    apar.add_argument("--max-ai", type=int, default=AI_MAX)
    args = apar.parse_args()

    os.makedirs(DATA, exist_ok=True)
    os.makedirs(ASSETS, exist_ok=True)
    subjects = {s.strip() for s in args.subjects.split(",") if s.strip()}

    todo = []
    n_ai = 0
    for subject, slug, spec, recipe, caption in EXHIBITS:
        if subjects and subject not in subjects:
            continue
        if args.only and args.only not in slug:
            continue
        if spec[0] == "ai":
            n_ai += 1
            if n_ai > args.max_ai:
                log(f"[cap] --max-ai {args.max_ai} reached; skipping {slug}")
                continue
        todo.append((subject, slug, spec, recipe, caption))

    # Pre-generate AI images with limited parallelism (network-bound, polite=3)
    ai_jobs = [(slug, spec[1]) for _, slug, spec, _, _ in todo if spec[0] == "ai"]
    if ai_jobs and not args.skip_ai:
        log(f"[ai] ensuring {len(ai_jobs)} generated images (cached ones are free)")
        with ThreadPoolExecutor(max_workers=3) as ex:
            list(ex.map(lambda j: generate_ai(j[1], f"ai_{j[0]}"), ai_jobs))

    results = []
    for subject, slug, spec, recipe, caption in todo:
        r = run_exhibit(subject, slug, spec, recipe, caption, args.skip_ai, args.skip_real)
        if r:
            results.append(r)

    if results:
        write_attribution(results)
        write_snippet(results)

    log("")
    log(f"=== done: {len(results)}/{len(todo)} exhibits ===")
    subj_counts: dict[str, int] = {}
    for r in results:
        subj_counts[r["subject"]] = subj_counts.get(r["subject"], 0) + 1
    for s, c in sorted(subj_counts.items()):
        log(f"  {s}: {c}")
    if AI_GENERATED_NOW:
        log(f"AI images billed this run: {len(AI_GENERATED_NOW)}")
        for s in AI_GENERATED_NOW:
            log(f"  {s}")
    if FINDINGS:
        log("--- findings (op oddities) ---")
        for fi in FINDINGS:
            log("  " + fi)
    manifest = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results, "findings": FINDINGS,
        "ai_billed_this_run": AI_GENERATED_NOW,
    }
    with open(os.path.join(DATA, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
