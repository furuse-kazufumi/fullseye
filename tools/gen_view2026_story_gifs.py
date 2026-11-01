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

from PIL import Image, ImageSequence


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


def _prepared_image(path: Path) -> Image.Image:
    with Image.open(path) as im:
        im = im.convert("RGB")
        scale = min(1.0, WIDTH / im.width, CONTENT_HEIGHT / im.height)
        if scale < 1.0:
            size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
            im = im.resize(size, Image.Resampling.LANCZOS)
        return im.copy()


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
    pictures = [_prepared_image(folder / r["file"]) for r in rows]
    frames, meta = [], []
    for i, (row, picture) in enumerate(zip(rows, pictures)):
        canvas = Image.new("RGB", (WIDTH, HEIGHT), "white")
        x, y = (WIDTH - picture.width) // 2, (CONTENT_HEIGHT - picture.height) // 2
        canvas.paste(picture, (x, y))
        dot_size, gap = 11, 7
        strip_width = len(rows) * dot_size + (len(rows) - 1) * gap
        dot_x = (WIDTH - strip_width) // 2
        dot_y = CONTENT_HEIGHT + (PROGRESS_HEIGHT - dot_size) // 2
        for j in range(len(rows)):
            canvas.paste(_progress_dot(j <= i, dot_size), (dot_x + j * (dot_size + gap), dot_y))
        frames.append(canvas)
        meta.append({"file": row["file"], "content_box": [x, y, picture.width, picture.height]})
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
        source = _prepared_image(folder / row["file"])
        out.append(_mad(source, frame.crop((x, y, x + w, y + h))))
    return out


def _digest(rows: list[dict], folder: Path, lang: str, version: str = "story-v4-square") -> str:
    h = hashlib.sha256()
    h.update((lang + "|" + version + "|" + json.dumps(rows, ensure_ascii=False, sort_keys=True)).encode("utf-8"))
    for row in rows:
        h.update((folder / row["file"]).read_bytes())
    return h.hexdigest()


def _write_gif(path: Path, rows: list[dict], folder: Path, lang: str,
               old: dict | None) -> tuple[dict | None, str | None]:
    digest = _digest(rows, folder, lang)
    if (old and old.get("source_sha256") == digest and path.is_file() and
            [x.get("file") for x in old.get("frames", [])] == [x["file"] for x in rows] and
            all("label" not in x and "shown_label" not in x for x in old.get("frames", []))):
        decoded = _decoded(path.read_bytes())
        if len(decoded) == len(rows) and all(x.size == (WIDTH, HEIGHT) for x in decoded):
            diffs = _content_mads(decoded, old["frames"], folder)
            if max(diffs, default=0.0) > COLOR_MAD_LIMIT:
                return None, "color_mad_over_%.1f" % COLOR_MAD_LIMIT
            old = dict(old); old.update(source_sha256=digest,
                                        color_mad=[round(x, 4) for x in diffs],
                                        max_color_mad=round(max(diffs, default=0.0), 4))
            return old, None
    frames, meta = _render(rows, folder)
    blob = _encode(frames)
    while len(blob) > MAX_BYTES and len(rows) > 3:
        rows = rows[:-1]
        frames, meta = _render(rows, folder)
        blob = _encode(frames)
        digest = _digest(rows, folder, lang)
    if len(blob) > MAX_BYTES:
        return None, "capacity_over_2_5_mb"
    decoded = _decoded(blob)
    diffs = _content_mads(decoded, meta, folder)
    if len(decoded) != len(frames):
        return None, "gif_frame_coalescing"
    if max(diffs, default=0.0) > COLOR_MAD_LIMIT:
        return None, "color_mad_over_%.1f" % COLOR_MAD_LIMIT
    path.write_bytes(blob)
    return {"path": path.relative_to(ROOT / "docs").as_posix(), "frames": meta,
            "frame_count": len(meta), "durations_ms": [FIRST_MS] + [OTHER_MS] * (len(meta) - 1),
            "bytes": len(blob), "color_mad": [round(x, 4) for x in diffs],
            "max_color_mad": round(max(diffs, default=0.0), 4), "source_sha256": digest}, None


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
        item = {**base, "selected": [x["file"] for x in selected],
                "excluded_frames": [], "variants": {}}
        failed = None
        for lang in ("ja", "en"):
            path = folder / ("story.%s.gif" % lang)
            variant, reason = _write_gif(path, selected, folder, lang,
                                         old.get(pid, {}).get("variants", {}).get(lang))
            if reason:
                failed = reason; break
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
              "schema": 2, "width": WIDTH, "height": HEIGHT, "max_bytes": MAX_BYTES,
              "color_metric": "mean absolute RGB channel difference inside the source-image content box",
              "color_mad_limit": COLOR_MAD_LIMIT, "first_duration_ms": FIRST_MS,
              "other_duration_ms": OTHER_MS, "target_count": len(targets), "entries": entries}
    text = json.dumps(ledger, ensure_ascii=False, indent=2) + "\n"
    LEDGER.write_text(text, encoding="utf-8", newline="\n")
    made = sum(x["status"] == "gif" for x in entries.values())
    print("ViEW2026 story GIFs: %d animated, %d static" % (made, len(entries) - made))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
