#!/usr/bin/env python3
"""Build the short story GIFs used by the ViEW2026 2-D exhibits.

Frame selection is deliberately mechanical and reviewable.  The current exhibit media is
always frame 1 (the cover).  From the remaining raster figures, in ``figures.json`` order,
we keep the earliest scene/raw/input, process/intermediate, result/truth/error, and
limit/failure figure suggested by its file/name; unfilled slots are spread through the
remaining ordered figures.  Thus the cover still works when animation is stopped, while
the following frames read as scene -> processing -> result -> truth/error -> limit.  A
PoC with only one or two usable raster figures remains static; three figures are retained
when that is all the author supplied, rather than duplicating a frame to reach four.

Japanese and English paths are both made for the page contract, although the frames carry
no generated heading: the source figures already identify themselves.  Progress is shown
only by bitmap dots.  GIFs are only rewritten when the selected source digest changes,
avoiding Pillow-version byte drift while still making stale inputs regenerate.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

try:
    from tools.gen_view2026_thumbs import (
        DOCS as THUMB_DOCS,
        SIZE as THUMB_SIZE,
        SPEC as THUMB_SPEC,
        _contain_square,
        _load as _load_thumb_source,
        _square,
        thumbnail_specs,
    )
except ModuleNotFoundError:  # ``py tools/gen_view2026_story_gifs.py``
    from gen_view2026_thumbs import (  # type: ignore[no-redef]
        DOCS as THUMB_DOCS,
        SIZE as THUMB_SIZE,
        SPEC as THUMB_SPEC,
        _contain_square,
        _load as _load_thumb_source,
        _square,
        thumbnail_specs,
    )


ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "docs" / "view2026"
ASSETS = ROOT / "docs" / "articles" / "assets" / "poc"
EXHIBITS = VIEW / "exhibits.json"
CAPTIONS = ROOT / "docs" / "articles" / "exhibits" / "poc_captions.json"
LEDGER = VIEW / "story_gifs.json"
WIDTH = 720
HEIGHT = 720
PROGRESS_HEIGHT = 30
CONTENT_HEIGHT = HEIGHT - PROGRESS_HEIGHT
MAX_BYTES = 2_500_000
MAX_FRAMES = 6
COLOR_MAD_LIMIT = 6.0
FIRST_MS = 2500
OTHER_MS = 1600
MIN_ASPECT = 0.60
MAX_ASPECT = 1.67
MIN_LAPLACIAN_DENSITY = 0.0005
MIN_CONTENT_FRACTION = 0.36
RASTER = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
EYE_CATCHERS = """poc_phase_measuring_deflectometry poc_industrial_oct
poc_hyperspectral_foreign_matter poc_thin_film_reflectometry poc_cad_scan_deviation
poc_telecentric_metrology poc_tem_ctf_thon_rings poc_virtual_sem_kv_cd_bse
poc_dual_energy_xray poc_weld_radiograph_porosity poc_good_sample_variation_model
poc_code_matching_breakdown poc_fourier_ptychography poc_photoelasticity""".split()

ROLE_WORDS = (
    ("scene", "raw", "input", "sample", "photo", "image", "scan", "radiograph", "bscan"),
    ("process", "intermediate", "filter", "unwrap", "profile", "spectrum", "map", "recovery"),
    ("result", "detect", "recon", "measure", "output", "truth", "error", "residual", "compare", "vs"),
    ("limit", "failure", "break", "cliff", "ambigu", "bias", "noise", "sweep", "tradeoff"),
)


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _is_target(e: dict, caption: dict, figures: list[dict], excluded_anim3d: set[str]) -> bool:
    """2-D still-led exhibit, including motion cards whose caption ledger names a still."""
    ext = Path(e.get("media", "")).suffix.lower()
    named = caption.get("figure")
    named_still = any(f.get("name") == named and not f.get("animated") and
                      Path(f.get("file", "")).suffix.lower() in RASTER for f in figures)
    return e["id"] not in excluded_anim3d and (e["id"] in EYE_CATCHERS or
            not e.get("motion") or ext in RASTER or named_still)


def _usable(row: dict, folder: Path) -> bool:
    p = folder / row.get("file", "")
    return (not row.get("animated")) and p.suffix.lower() in RASTER and p.is_file()


def choose_frames(figures: list[dict], representative: str, folder: Path) -> list[dict]:
    """Choose cover first, then scene -> process -> result/truth/error -> limit.

    Figure order is the tie-breaker for every role.  Empty role slots are filled by
    evenly spaced figures in original order; the same file can never be selected twice.
    """
    usable = [f for f in figures if _usable(f, folder)]
    cover = next((f for f in figures if f.get("file") == representative and
                  (folder / f.get("file", "")).is_file()), None)
    if cover is None:
        return []
    rest = [f for f in usable if f is not cover]
    wanted: list[dict] = []
    for words in ROLE_WORDS:
        hit = next((f for f in rest if f not in wanted and any(
            w in (str(f.get("name", "")) + " " + str(f.get("file", ""))).lower() for w in words)), None)
        if hit is not None:
            wanted.append(hit)
    left = [f for f in rest if f not in wanted]
    room = MAX_FRAMES - 1 - len(wanted)
    if room > 0 and left:
        if len(left) <= room:
            wanted += left
        else:
            idx = [round(i * (len(left) - 1) / max(1, room - 1)) for i in range(room)]
            wanted += [left[i] for i in dict.fromkeys(idx)]
    order = {id(f): i for i, f in enumerate(figures)}
    return [cover] + sorted(wanted, key=lambda f: order[id(f)])[: MAX_FRAMES - 1]


def _cover_file(exhibit: dict, caption: dict, figures: list[dict], folder: Path) -> str | None:
    """Prefer the current still media, then the caption ledger's principal still, then figure 1."""
    media = exhibit.get("media", "")
    exact = next((f for f in figures if f.get("file") == media and _usable(f, folder)), None)
    if exact:
        return exact["file"]
    named = next((f for f in figures if f.get("name") == caption.get("figure") and _usable(f, folder)), None)
    if named:
        return named["file"]
    stem = Path(media).stem
    animated = next((f for f in figures if Path(f.get("file", "")).stem == stem and
                     (folder / f.get("file", "")).is_file()), None)
    if animated:
        return animated["file"]
    first = next((f for f in figures if _usable(f, folder)), None)
    return first["file"] if first else None


def _prepared_image(path: Path, crop: list[int] | tuple[int, int, int, int] | None = None) -> Image.Image:
    with Image.open(path) as im:
        im = im.convert("RGB")
        if crop is not None:
            x, y, w, h = crop
            im = im.crop((x, y, x + w, y + h))
        scale = min(WIDTH / im.width, CONTENT_HEIGHT / im.height)
        size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
        if size != im.size:
            im = im.resize(size, Image.Resampling.LANCZOS)
        return im.copy()


def _dense_crop(im: Image.Image) -> tuple[list[int] | None, float]:
    """極端比率の図から、絶対値 Laplacian の総和が最大になる窓を選ぶ。"""
    gray = np.asarray(im.convert("L"), dtype=np.int16)
    h, w = gray.shape
    lap = np.zeros((h, w), dtype=np.int32)
    lap[1:-1, 1:-1] = np.abs(
        4 * gray[1:-1, 1:-1] - gray[:-2, 1:-1] - gray[2:, 1:-1]
        - gray[1:-1, :-2] - gray[1:-1, 2:]
    )
    if w / h > MAX_ASPECT:
        crop_w = min(w, max(1, int(MAX_ASPECT * h)))
        scores = np.convolve(lap.sum(axis=0, dtype=np.int64),
                             np.ones(crop_w, dtype=np.int64), mode="valid")
        x, y, crop_h = int(np.argmax(scores)), 0, h
        score = int(scores[x])
    elif w / h < MIN_ASPECT:
        crop_h = min(h, max(1, int(w / MIN_ASPECT)))
        scores = np.convolve(lap.sum(axis=1, dtype=np.int64),
                             np.ones(crop_h, dtype=np.int64), mode="valid")
        x, y, crop_w = 0, int(np.argmax(scores)), w
        score = int(scores[y])
    else:
        return None, 0.0
    density = score / (1020.0 * crop_w * crop_h)
    return [x, y, crop_w, crop_h], density


def _text_only_name(row: dict) -> bool:
    """切り出すと列や文章の断片にしかならない明示的な表・数表を見分ける。"""
    tokens = set(Path(row.get("file", "")).stem.lower().split("_"))
    return bool(tokens & {"table", "numbers"})


def _plan_rows(pid: str, rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """先頭にサムネ仕様を付け、以後の極端比率だけ内容の濃い窓へ切り出す。"""
    specs, contained = thumbnail_specs()
    by_id = {thumb_pid: (rel, frame, crop) for thumb_pid, rel, frame, crop in specs}
    planned = [dict(rows[0])]
    if pid in by_id:
        rel, frame, crop = by_id[pid]
        planned[0]["_thumbnail"] = {
            "source": rel,
            "frame": frame,
            "crop": list(crop) if crop is not None else None,
            "mode": "contain" if pid in contained else "square",
            "rendered": "view2026/thumbs/%s.jpg" % pid,
        }
    excluded = []
    for row in rows[1:]:
        candidate = dict(row)
        with Image.open(ASSETS / pid / row["file"]) as source:
            ratio = source.width / source.height
            crop, density = _dense_crop(source) if ratio < MIN_ASPECT or ratio > MAX_ASPECT else (None, 0.0)
        if crop is not None and _text_only_name(row):
            excluded.append({"file": row["file"], "reason": "crop_text_only",
                             "source_aspect": round(ratio, 6)})
            continue
        if crop is not None and density < MIN_LAPLACIAN_DENSITY:
            excluded.append({"file": row["file"], "reason": "crop_content_below_threshold",
                             "source_aspect": round(ratio, 6),
                             "laplacian_density": round(density, 8)})
            continue
        if crop is not None:
            candidate["crop"] = crop
            candidate["source_aspect"] = round(ratio, 6)
            candidate["laplacian_density"] = round(density, 8)
        planned.append(candidate)
    return planned, excluded


def _prepared_row(row: dict, folder: Path) -> Image.Image:
    thumb = row.get("_thumbnail")
    if thumb:
        source = _load_thumb_source(THUMB_DOCS / thumb["source"], thumb["frame"])
        if thumb["mode"] == "contain":
            preview = _contain_square(source, THUMB_SIZE)
        else:
            preview = _square(source, thumb["crop"], THUMB_SIZE)
        # JPEG 圧縮後のサムネそのものを拡大し、320 px に戻したときの色も揃える。
        rendered = THUMB_DOCS / thumb["rendered"]
        with Image.open(rendered) as saved:
            saved = saved.convert("RGB")
            if saved.size != preview.size:
                raise ValueError("サムネイルの寸法が仕様と違う: %s" % rendered)
            return saved.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    return _prepared_image(folder / row["file"], row.get("crop"))


def _progress_dot(filled: bool, size: int = 11) -> Image.Image:
    """Return a tiny deterministic bitmap circle without invoking a text/drawing API."""
    centre = (size - 1) / 2
    outer2 = centre * centre
    inner2 = (centre - 2) * (centre - 2)
    dark, white = (35, 42, 55), (255, 255, 255)
    pixels = []
    for y in range(size):
        for x in range(size):
            radius2 = (x - centre) ** 2 + (y - centre) ** 2
            pixels.append(dark if radius2 <= outer2 and (filled or radius2 >= inner2) else white)
    dot = Image.new("RGB", (size, size), white)
    dot.putdata(pixels)
    return dot


def _render(rows: list[dict], folder: Path) -> tuple[list[Image.Image], list[dict]]:
    pictures = [_prepared_row(r, folder) for r in rows]
    frames, meta = [], []
    for i, (row, picture) in enumerate(zip(rows, pictures)):
        canvas = Image.new("RGB", (WIDTH, HEIGHT), "white")
        if row.get("_thumbnail"):
            x, y = (WIDTH - picture.width) // 2, (HEIGHT - picture.height) // 2
        else:
            x, y = (WIDTH - picture.width) // 2, (CONTENT_HEIGHT - picture.height) // 2
        canvas.paste(picture, (x, y))
        dot_size, gap = 11, 7
        strip_width = len(rows) * dot_size + (len(rows) - 1) * gap
        dot_x = (WIDTH - strip_width) // 2
        dot_y = CONTENT_HEIGHT + (PROGRESS_HEIGHT - dot_size) // 2
        for j in range(len(rows)):
            canvas.paste(_progress_dot(j <= i, dot_size), (dot_x + j * (dot_size + gap), dot_y))
        frames.append(canvas)
        item = {"file": row["file"], "content_box": [x, y, picture.width, picture.height]}
        if row.get("crop") is not None:
            item.update(crop=row["crop"], source_aspect=row["source_aspect"],
                        laplacian_density=row["laplacian_density"])
        if row.get("_thumbnail"):
            item["thumbnail"] = row["_thumbnail"]
        meta.append(item)
    return frames, meta


def _encode(frames: list[Image.Image]) -> bytes:
    pal = [f.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                      dither=Image.Dither.NONE) for f in frames]
    out = io.BytesIO()
    pal[0].save(out, format="GIF", save_all=True, append_images=pal[1:], loop=0,
                duration=[FIRST_MS] + [OTHER_MS] * (len(pal) - 1), disposal=2,
                optimize=True, comment=b"ViEW2026 story GIF")
    return out.getvalue()


def _decoded(blob: bytes) -> list[Image.Image]:
    with Image.open(io.BytesIO(blob)) as im:
        return [f.convert("RGB").copy() for f in ImageSequence.Iterator(im)]


def _mad(a: Image.Image, b: Image.Image) -> float:
    aa, bb = a.tobytes(), b.tobytes()
    return sum(abs(x - y) for x, y in zip(aa, bb)) / len(aa)


def _content_mads(decoded: list[Image.Image], meta: list[dict], folder: Path) -> list[float]:
    """Measure palette loss on the source-picture rectangle, never diluted by white padding."""
    out = []
    for frame, row in zip(decoded, meta):
        x, y, w, h = row["content_box"]
        prepared = dict(row)
        if "thumbnail" in prepared:
            prepared["_thumbnail"] = prepared["thumbnail"]
        source = _prepared_row(prepared, folder)
        out.append(_mad(source, frame.crop((x, y, x + w, y + h))))
    return out


def _digest(rows: list[dict], folder: Path, lang: str, version: str = "story-v8-rendered-thumb") -> str:
    h = hashlib.sha256()
    h.update((lang + "|" + version + "|" + json.dumps(rows, ensure_ascii=False, sort_keys=True)).encode("utf-8"))
    for row in rows:
        h.update((folder / row["file"]).read_bytes())
        if row.get("_thumbnail"):
            h.update((THUMB_DOCS / row["_thumbnail"]["source"]).read_bytes())
            h.update((THUMB_DOCS / row["_thumbnail"]["rendered"]).read_bytes())
    return h.hexdigest()


def _write_gif(path: Path, rows: list[dict], folder: Path, lang: str,
               old: dict | None) -> tuple[dict | None, str | None, list[dict]]:
    digest = _digest(rows, folder, lang)
    if (old and old.get("source_sha256") == digest and path.is_file() and
            [x.get("file") for x in old.get("frames", [])] == [x["file"] for x in rows] and
            all("label" not in x and "shown_label" not in x for x in old.get("frames", []))):
        decoded = _decoded(path.read_bytes())
        if len(decoded) == len(rows) and all(x.size == (WIDTH, HEIGHT) for x in decoded):
            diffs = _content_mads(decoded, old["frames"], folder)
            if max(diffs, default=0.0) > COLOR_MAD_LIMIT:
                return None, "color_mad_over_%.1f" % COLOR_MAD_LIMIT, rows
            old = dict(old); old.update(source_sha256=digest,
                                        color_mad=[round(x, 4) for x in diffs],
                                        max_color_mad=round(max(diffs, default=0.0), 4))
            return old, None, rows
    frames, meta = _render(rows, folder)
    blob = _encode(frames)
    while len(blob) > MAX_BYTES and len(rows) > 3:
        rows = rows[:-1]
        frames, meta = _render(rows, folder)
        blob = _encode(frames)
        digest = _digest(rows, folder, lang)
    if len(blob) > MAX_BYTES:
        return None, "capacity_over_2_5_mb", rows
    decoded = _decoded(blob)
    diffs = _content_mads(decoded, meta, folder)
    if len(decoded) != len(frames):
        return None, "gif_frame_coalescing", rows
    if max(diffs, default=0.0) > COLOR_MAD_LIMIT:
        return None, "color_mad_over_%.1f" % COLOR_MAD_LIMIT, rows
    path.write_bytes(blob)
    return {"path": path.relative_to(ROOT / "docs").as_posix(), "frames": meta,
            "frame_count": len(meta), "durations_ms": [FIRST_MS] + [OTHER_MS] * (len(meta) - 1),
            "bytes": len(blob), "color_mad": [round(x, 4) for x in diffs],
            "max_color_mad": round(max(diffs, default=0.0), 4), "source_sha256": digest}, None, rows


def main() -> int:
    data = _json(EXHIBITS)
    all_rows = {e["id"]: e for e in data["all"]}
    cap_rows = {x["id"]: x for x in _json(CAPTIONS)["exhibits"]}
    excluded_anim3d = {e["id"] for e in data["exhibits"] if e.get("category") == "anim3d"}
    figure_rows = {}
    for e in data["all"]:
        p = ASSETS / e["id"] / "figures.json"
        figure_rows[e["id"]] = _json(p) if p.is_file() else []
    targets = [e for e in data["all"] if _is_target(
        e, cap_rows.get(e["id"], {}), figure_rows[e["id"]], excluded_anim3d)]
    rank = {name: i for i, name in enumerate(EYE_CATCHERS)}
    targets.sort(key=lambda e: (rank.get(e["id"], len(rank)), list(all_rows).index(e["id"])))
    old = _json(LEDGER).get("entries", {}) if LEDGER.is_file() else {}
    entries = {}
    for exhibit in targets:
        pid, folder = exhibit["id"], ASSETS / exhibit["id"]
        base = {"representative": exhibit.get("media", ""), "status": "static"}
        fig_path = folder / "figures.json"
        if not fig_path.is_file():
            entries[pid] = {**base, "reason": "figures_json_missing"}; continue
        figures = figure_rows[pid]
        cover = _cover_file(exhibit, cap_rows.get(pid, {}), figures, folder)
        selected = choose_frames(figures, cover or "", folder)
        if len(selected) <= 2:
            entries[pid] = {**base, "reason": "two_or_fewer_raster_figures", "usable_figures": len(selected)}; continue
        if not selected:
            entries[pid] = {**base, "reason": "representative_not_a_static_figure"}; continue
        selected, excluded_frames = _plan_rows(pid, selected)
        if len(selected) <= 2:
            for lang in ("ja", "en"):
                path = folder / ("story.%s.gif" % lang)
                if path.exists():
                    path.unlink()
            entries[pid] = {**base, "reason": "two_or_fewer_readable_frames_after_crop",
                            "selected": [x["file"] for x in selected],
                            "excluded_frames": excluded_frames,
                            "usable_figures": len(selected)}
            continue
        item = {**base, "selected": [x["file"] for x in selected],
                "excluded_frames": excluded_frames, "variants": {}}
        if selected[0].get("_thumbnail"):
            item["thumbnail"] = selected[0]["_thumbnail"]
        failed = None
        for lang in ("ja", "en"):
            path = folder / ("story.%s.gif" % lang)
            variant, reason, used = _write_gif(path, selected, folder, lang,
                                               old.get(pid, {}).get("variants", {}).get(lang))
            if reason:
                failed = reason; break
            if len(used) < len(selected):
                item["excluded_frames"].extend(
                    {"file": row["file"], "reason": "capacity_limit"} for row in selected[len(used):])
                selected = used
                item["selected"] = [x["file"] for x in selected]
            item["variants"][lang] = variant
        if failed:
            for lang in ("ja", "en"):
                path = folder / ("story.%s.gif" % lang)
                if path.exists():
                    path.unlink()
            item = {**base, "reason": failed}
        else:
            cap = cap_rows.get(pid, {})
            representative = selected[0]
            item.update(status="gif", reason=None,
                        cover=representative["file"],
                        still=(folder / next((f["file"] for f in selected if _usable(f, folder)),
                                             representative["file"])).relative_to(ROOT / "docs").as_posix(),
                        alt={"ja": representative.get("caption") or exhibit["label"]["ja"],
                             "en": cap.get("lead_en") or cap.get("title_en") or exhibit["label"]["en"]})
        entries[pid] = item
    ledger = {"_": "Generated by tools/gen_view2026_story_gifs.py; do not edit.",
              "schema": 3, "width": WIDTH, "height": HEIGHT, "max_bytes": MAX_BYTES,
              "color_metric": "mean absolute RGB channel difference inside the source-image content box",
              "color_mad_limit": COLOR_MAD_LIMIT, "first_duration_ms": FIRST_MS,
              "other_duration_ms": OTHER_MS, "target_count": len(targets),
              "crop_aspect_range": [MIN_ASPECT, MAX_ASPECT],
              "crop_metric": "maximum summed absolute 4-neighbour Laplacian",
              "min_laplacian_density": MIN_LAPLACIAN_DENSITY,
              "min_content_fraction": MIN_CONTENT_FRACTION,
              "manual_thumbnail_spec_count": len(THUMB_SPEC), "entries": entries}
    text = json.dumps(ledger, ensure_ascii=False, indent=2) + "\n"
    LEDGER.write_text(text, encoding="utf-8", newline="\n")
    made = sum(x["status"] == "gif" for x in entries.values())
    print("ViEW2026 story GIFs: %d animated, %d static" % (made, len(entries) - made))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
