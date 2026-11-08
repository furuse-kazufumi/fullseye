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
                               "two_or_fewer_readable_frames_after_crop",
                               "capacity_over_2_5_mb", "gif_frame_coalescing"} or
               v["reason"].startswith("color_mad_over_") for v in static.values())


def test_gifs_match_sources_durations_colour_and_capacity():
    assert LEDGER["width"] == LEDGER["height"] == 720
    for pid, item in LEDGER["entries"].items():
        if item["status"] != "gif":
            continue
        assert item["selected"][0] == item["cover"]
        assert len(item["selected"]) == len(set(item["selected"]))
        assert all(x["reason"] in {"crop_text_only", "crop_content_below_threshold",
                                   "capacity_limit"} for x in item["excluded_frames"])

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
            dot_size, gap = 11, 7
            dot_x = (G.WIDTH - len(frames) * dot_size - (len(frames) - 1) * gap) // 2
            dot_y = G.CONTENT_HEIGHT + (G.PROGRESS_HEIGHT - dot_size) // 2
            for i, frame in enumerate(frames):
                centres = [frame.getpixel((dot_x + j * (dot_size + gap) + dot_size // 2,
                                           dot_y + dot_size // 2)) for j in range(len(frames))]
                assert all(sum(pixel) < 300 for pixel in centres[:i + 1])
                assert all(sum(pixel) > 700 for pixel in centres[i + 1:])
            for i, (frame, meta) in enumerate(zip(frames, variant["frames"])):
                assert "label" not in meta and "shown_label" not in meta
                x, y, w, h = meta["content_box"]
                row = dict(meta)
                if "thumbnail" in row:
                    row["_thumbnail"] = row["thumbnail"]
                source = G._prepared_row(row, G.ASSETS / pid)
                assert source.size == (w, h)
                assert 0 <= x <= 720 - w and 0 <= y <= 720 - h
                assert _mad(source, frame.crop((x, y, x + w, y + h))) <= LEDGER["color_mad_limit"]
                if i:
                    # 題または左右両端の文字を守る contain は、細帯回避より意味保存を優先する。
                    if "contain_reason" not in meta:
                        assert w * h / (G.WIDTH * G.CONTENT_HEIGHT) >= LEDGER["min_content_fraction"]
                    with Image.open(G.ASSETS / pid / meta["file"]) as original:
                        ratio = original.width / original.height
                        if "crop" in meta:
                            assert ratio <= G.MIN_ASPECT or ratio >= G.MAX_ASPECT
                        if G.PREVIOUS_MAX_ASPECT < ratio <= G.MAX_ASPECT:
                            assert "crop" not in meta
                        if G.MIN_ASPECT <= ratio < G.PREVIOUS_MIN_ASPECT:
                            assert "crop" not in meta
            assert max(variant["color_mad"]) <= LEDGER["color_mad_limit"]


def test_all_ledger_crops_are_reserved_for_aspect_ratios_at_least_2_4_or_at_most_0_42():
    crops = []
    for item in LEDGER["entries"].values():
        if item["status"] != "gif":
            continue
        crops.extend(frame for frame in item["variants"]["ja"]["frames"] if "crop" in frame)
    assert crops
    assert all(frame["source_aspect"] >= G.MAX_ASPECT or
               frame["source_aspect"] <= G.MIN_ASPECT for frame in crops)


def test_the_thirty_text_only_crops_stay_excluded():
    excluded = [frame for item in LEDGER["entries"].values()
                for frame in item.get("excluded_frames", [])
                if frame["reason"] == "crop_text_only"]
    # 2026-11-08 +1: poc_pv_thermal_survey の代表を実データの図(11_real_dtu_conditions)に替えたので、元の代表
    #   01_norm_table.png(縦横比 4.6 の表)が表紙でなく途中のコマの候補になり、文字だけの切り出しとして外れた。
    # 2026-11-09 +1: 収蔵 2026.309 の 03_numbers.png(数字だけの表)が外れる。
    #   (統合で両方が入って 30 → 32。どちらも下で名指しで確かめる)
    assert len(excluded) == 32
    names = {(pid, frame["file"]) for pid, item in LEDGER["entries"].items()
             for frame in item.get("excluded_frames", []) if frame["reason"] == "crop_text_only"}
    assert ("poc_3d_sensor_modalities", "03_numbers.png") in names
    assert ("poc_pv_thermal_survey", "01_norm_table.png") in names


def test_the_three_reported_graph_and_table_frames_are_contained_whole():
    expected = {
        "poc_industrial_oct": {"14_lateral_vs_dof.png"},
        "poc_hyperspectral_foreign_matter": {
            "02_real_vs_model_band_depth.png", "03_real_polymer_confusion.png"},
    }
    for pid, files in expected.items():
        frames = {frame["file"]: frame for frame in
                  LEDGER["entries"][pid]["variants"]["ja"]["frames"]}
        for file in files:
            assert frames[file]["contain_reason"] == "aspect_within_2_4"
            assert "crop" not in frames[file]


def test_first_frame_matches_the_saved_thumbnail_at_320_pixels():
    matched = 0
    for pid, item in LEDGER["entries"].items():
        if item["status"] != "gif" or "thumbnail" not in item:
            continue
        thumb_path = ROOT / "docs/view2026/thumbs" / (pid + ".jpg")
        with Image.open(thumb_path) as thumb, Image.open(ROOT / "docs" / item["variants"]["ja"]["path"]) as gif:
            first = next(ImageSequence.Iterator(gif)).convert("RGB").resize(
                thumb.size, Image.Resampling.LANCZOS)
            assert _mad(first, thumb.convert("RGB")) <= LEDGER["color_mad_limit"], pid
        matched += 1
    assert matched == sum(x["status"] == "gif" and "thumbnail" in x
                          for x in LEDGER["entries"].values())


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


def test_story_figures_in_the_caption_ledger_order_the_frames(tmp_path):
    """台帳の story_figures は表紙の後ろの順を決め、無い名前は黙って飛ばさず止める。"""
    import pytest
    for n in ("a.png", "b.png", "c.png", "d.png"):
        Image.new("RGB", (40, 30), "white").save(tmp_path / n)
    figs = [{"file": "a.png", "name": "scene"}, {"file": "b.png", "name": "real_cover"},
            {"file": "c.png", "name": "real_x"}, {"file": "d.png", "name": "real_y"}]
    got = G.chosen_frames(figs, "b.png", tmp_path, ["real_y", "real_x"])
    assert [f["file"] for f in got] == ["b.png", "d.png", "c.png"]
    assert [f["file"] for f in G.chosen_frames(figs, "b.png", tmp_path, None)][0] == "b.png"
    with pytest.raises(SystemExit):
        G.chosen_frames(figs, "b.png", tmp_path, ["nope"])
    with pytest.raises(SystemExit):                       # 重複
        G.chosen_frames(figs, "b.png", tmp_path, ["real_x", "real_x"])
    many = [{"file": "m%d.png" % i, "name": "m%d" % i} for i in range(G.MAX_FRAMES)]
    for f in many:
        Image.new("RGB", (40, 30), "white").save(tmp_path / f["file"])
    with pytest.raises(SystemExit):                       # 表紙の後ろに入りきらない個数
        G.chosen_frames(figs + many, "b.png", tmp_path, [f["name"] for f in many])
    ok = G.chosen_frames(figs + many, "b.png", tmp_path, [f["name"] for f in many[:G.MAX_FRAMES - 1]])
    assert len(ok) == G.MAX_FRAMES
