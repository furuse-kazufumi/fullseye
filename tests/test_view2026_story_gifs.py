# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""ViEW2026 story GIF の正方形・表紙・順序・色・容量・静止フォールバックの門。"""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "gen_view2026_story_gifs", ROOT / "tools" / "gen_view2026_story_gifs.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
LEDGER = json.loads((ROOT / "docs/view2026/story_gifs.json").read_text(encoding="utf-8"))


def _figures(pid: str) -> list[dict]:
    p = ROOT / "docs/articles/assets/poc" / pid / "figures.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []


def _mad(a: Image.Image, b: Image.Image) -> float:
    aa, bb = a.convert("RGB").tobytes(), b.convert("RGB").tobytes()
    return sum(abs(x - y) for x, y in zip(aa, bb)) / len(aa)


def test_ledger_covers_every_target_and_prioritises_the_fourteen_eye_catchers():
    data = json.loads((ROOT / "docs/view2026/exhibits.json").read_text(encoding="utf-8"))
    caps = {x["id"]: x for x in json.loads(G.CAPTIONS.read_text(encoding="utf-8"))["exhibits"]}
    excluded = {x["id"] for x in data["exhibits"] if x.get("category") == "anim3d"}
    expected = [x["id"] for x in data["all"] if G._is_target(
        x, caps.get(x["id"], {}), _figures(x["id"]), excluded)]
    entries = LEDGER["entries"]
    assert set(entries) == set(expected)
    assert list(entries)[:len(G.EYE_CATCHERS)] == G.EYE_CATCHERS
    assert all(entries[x]["status"] == "gif" for x in G.EYE_CATCHERS)


def test_every_static_target_has_an_explicit_reason():
    static = {k: v for k, v in LEDGER["entries"].items() if v["status"] == "static"}
    assert static
    assert all(v.get("reason") for v in static.values())
    assert all(v["reason"] in {"figures_json_missing", "two_or_fewer_raster_figures",
                               "capacity_over_2_5_mb", "gif_frame_coalescing"} or
               v["reason"].startswith("color_mad_over_") for v in static.values())


def test_gifs_match_sources_durations_colour_and_capacity():
    assert LEDGER["width"] == LEDGER["height"] == 720
    for pid, item in LEDGER["entries"].items():
        if item["status"] != "gif":
            continue
        assert item["selected"][0] == item["cover"]
        assert len(item["selected"]) == len(set(item["selected"]))
        assert item["excluded_frames"] == []
        source_pictures = []
        for name in item["selected"]:
            picture = G._prepared_image(G.ASSETS / pid / name)
            source_pictures.append((picture.size, picture.tobytes()))
        assert all(a != b for a, b in zip(source_pictures, source_pictures[1:])), pid

        for lang, variant in item["variants"].items():
            path = ROOT / "docs" / variant["path"]
            assert path.is_file() and path.stat().st_size == variant["bytes"] <= LEDGER["max_bytes"]
            with Image.open(path) as gif:
                durations = []
                frames = []
                for frame in ImageSequence.Iterator(gif):
                    durations.append(frame.info.get("duration"))
                    frames.append(frame.convert("RGB").copy())
            assert len(frames) == variant["frame_count"] == len(variant["frames"])
            assert durations == variant["durations_ms"]
            assert durations[0] == 2500 and all(x == 1600 for x in durations[1:])
            assert all(f.size == (720, 720) and
                       len(f.getcolors(maxcolors=257) or []) <= 256 for f in frames)
            progress_ink = [sum(pixel != (255, 255, 255) for pixel in
                                frame.crop((0, G.CONTENT_HEIGHT, 720, 720)).get_flattened_data())
                            for frame in frames]
            assert progress_ink == sorted(progress_ink)
            assert len(set(progress_ink)) == len(frames)
            for frame, meta in zip(frames, variant["frames"]):
                assert "label" not in meta and "shown_label" not in meta
                x, y, w, h = meta["content_box"]
                source = G._prepared_image(G.ASSETS / pid / meta["file"])
                assert source.size == (w, h)
                assert 0 <= x <= 720 - w and 0 <= y <= G.CONTENT_HEIGHT - h
                assert _mad(source, frame.crop((x, y, x + w, y + h))) <= LEDGER["color_mad_limit"]
            assert max(variant["color_mad"]) <= LEDGER["color_mad_limit"]


def test_generator_has_no_text_drawing_calls():
    source = (ROOT / "tools/gen_view2026_story_gifs.py").read_text(encoding="utf-8")
    assert "ImageDraw" not in source
    assert "ImageFont" not in source
    assert ".text(" not in source


def test_pages_use_english_outside_japanese_and_stop_for_reduced_motion():
    ja = (ROOT / "docs/view2026/index.md").read_text(encoding="utf-8")
    en = (ROOT / "docs/view2026/en/index.md").read_text(encoding="utf-8")
    zh = (ROOT / "docs/view2026/zh/index.md").read_text(encoding="utf-8")
    assert "story.ja.gif" in ja and "story.en.gif" not in ja
    assert "story.en.gif" in en and "story.ja.gif" not in en
    assert "story.en.gif" in zh and "story.ja.gif" not in zh
    for page in (ja, en, zh):
        assert 'media="(prefers-reduced-motion: reduce)"' in page
        assert "<picture>" in page
