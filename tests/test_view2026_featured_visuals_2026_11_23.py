# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 目玉 30 本の見た目の直し(2026-11-23)の門。

* 英語版(日本語以外の全ページ)のストーリー GIF は、図の文字の監査(figure_text.json)で英語に
  読める図だけから組む。監査は図のバイトと照合し、図が変わったら古いと言う。
* 太陽電池 EL の表紙は PoC が書く日英併記の 2×2(real_cover)。
* ICP・白色干渉・LiDAR にも静止画の表紙からストーリー GIF を作る。
* LiDAR 図 13 は地図を枠で囲み、色の尺度との間に余白を空ける。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import audit_view2026_figure_text as audit  # noqa: E402
import gen_view2026_story_gifs as story  # noqa: E402

VIEW = ROOT / "docs" / "view2026"
ASSETS = ROOT / "docs" / "articles" / "assets" / "poc"
STORY = json.loads((VIEW / "story_gifs.json").read_text(encoding="utf-8"))["entries"]
TEXT = json.loads((VIEW / "figure_text.json").read_text(encoding="utf-8"))["entries"]

#: 2026-11-23 の点検で英語版に日本語が出ていた目玉(新しく上げた 7 本 + OCT・光弾性・CAD)。
REVIEWED = ("poc_fourier_ptychography", "poc_tdi_linescan", "poc_illumination_cone_vs_na",
            "poc_polarization_specular", "poc_moire_alignment", "poc_tem_ctf_thon_rings",
            "poc_solar_el_inspection", "poc_industrial_oct", "poc_photoelasticity",
            "poc_cad_scan_deviation")


def test_classifier_cases():
    assert audit.classify_string("α = β") == audit.CLASS_LATIN
    assert audit.classify_string("ヘアラインの傷 / hairline scratch") == audit.CLASS_BILINGUAL
    assert audit.classify_string("面の傾き θ [°]") == audit.CLASS_JAPANESE
    # 2 文字の略語(NA)は英語の語と数えない
    assert audit.classify_string("テレセン / NA") == audit.CLASS_JAPANESE
    # 凡例の点(・)は日本語の文字ではない
    assert audit.classify_string("・ α=0.5°") == audit.CLASS_LATIN
    assert audit.classify([]) == audit.CLASS_NONE
    assert audit.classify(None) == audit.CLASS_UNAUDITED
    assert audit.classify(["a / b", "x"]) == audit.CLASS_LATIN
    assert audit.classify(["傷 / scratch", "x"]) == audit.CLASS_BILINGUAL
    assert audit.classify(["傷 / scratch", "傷"]) == audit.CLASS_JAPANESE


def test_audit_covers_every_listed_poc_and_is_current():
    assert set(REVIEWED) <= set(audit.AUDITED_POCS)
    assert set(audit.AUDITED_POCS) <= set(TEXT)
    problems = audit.stale({"entries": TEXT})
    assert problems == [], problems
    for pid in audit.AUDITED_POCS:
        figures = TEXT[pid]["figures"]
        assert len(figures) >= 3, pid
        assert all(row["class"] in {audit.CLASS_NONE, audit.CLASS_LATIN, audit.CLASS_BILINGUAL,
                                    audit.CLASS_JAPANESE, audit.CLASS_UNAUDITED}
                   for row in figures.values()), pid


#: 2026-11-23 の監査で英語に読める図から組めた PoC(照明の円錐・白色干渉・偏光・太陽電池 EL・TEM)。
#: 残る 8 本は英語に読める図が無く、日本語のコマを残して台帳に限界を書いた。
MIN_ENGLISH_POCS = 5


def test_english_frames_never_use_a_japanese_figure():
    checked = 0
    english_pocs = 0
    for pid in audit.AUDITED_POCS:
        entry = STORY.get(pid)
        assert entry is not None and entry.get("status") == "gif", (pid, entry)
        en = entry["en"]
        classes = {name: row["class"] for name, row in TEXT[pid]["figures"].items()}
        assert en["text"] in (story.EN_FRAMES, story.EN_STILL, story.EN_LIMITATION), (pid, en)
        if en["text"] == story.EN_LIMITATION:
            # 英語に読める図が 1 枚も無い: 日本語版のコマを残し、台帳に理由を全部書く
            assert en["selected"] == entry["selected"], pid
            assert {x["file"] for x in en["not_english_ready"]} == set(entry["selected"]), pid
            continue
        for name in en["selected"]:
            assert classes.get(name) in audit.ENGLISH_READY, (pid, name, classes.get(name))
            checked += 1
        english_pocs += 1
        variant = entry["variants"]["en"]
        if en["text"] == story.EN_STILL:
            assert variant.get("static") is True and variant["frame_count"] == 1, pid
            assert variant["path"].endswith(en["selected"][0]), pid
            assert not (ASSETS / pid / "story.en.gif").exists(), pid
        else:
            assert len(en["selected"]) >= story.EN_MIN_FRAMES, pid
            assert variant["frame_count"] == len(en["selected"]), pid
            assert [f["file"] for f in variant["frames"]] == en["selected"], pid
        assert entry["stills"]["en"].rsplit("/", 1)[-1] in en["selected"], pid
    assert english_pocs >= MIN_ENGLISH_POCS and checked >= english_pocs, (english_pocs, checked)


def test_unaudited_pocs_keep_their_frames():
    unaudited = [pid for pid, e in STORY.items() if e.get("status") == "gif" and pid not in TEXT]
    assert len(unaudited) >= 10, len(unaudited)
    for pid in unaudited:
        en = STORY[pid]["en"]
        assert en["text"] == story.EN_NOT_AUDITED, pid
        assert en["selected"] == STORY[pid]["selected"], pid


def test_solar_cover_is_the_bilingual_real_cover():
    entry = STORY["poc_solar_el_inspection"]
    assert entry["cover"] == "15_real_cover.png"
    assert entry["thumbnail"]["source"].endswith("poc_solar_el_inspection/15_real_cover.png")
    assert entry["thumbnail"]["crop"] is None
    assert TEXT["poc_solar_el_inspection"]["figures"]["15_real_cover.png"]["class"] == audit.CLASS_BILINGUAL
    assert entry["en"]["selected"][0] == "15_real_cover.png"


def test_motion_exhibits_have_a_story_from_their_still_cover():
    assert len(story.MOTION_STORY_COVERS) == 3
    for pid, cover in story.MOTION_STORY_COVERS.items():
        entry = STORY[pid]
        assert entry["status"] == "gif", (pid, entry.get("reason"))
        assert entry["cover"] == cover, pid
        assert entry["selected"][0] == cover, pid
        assert (ASSETS / pid / "story.ja.gif").is_file(), pid


def test_lidar_dod_map_is_framed_away_from_the_colour_bar():
    src = (ROOT / "examples" / "poc_lidar_terrain_change.py").read_text(encoding="utf-8")
    assert "DOD_COLORBAR_GUTTER_PX = 24" in src and "DOD_MAP_FRAME_PX = 2" in src
    assert src.count("framed(signed_rgb(") == 3
    from PIL import Image
    with Image.open(ASSETS / "poc_lidar_terrain_change" / "13_real_dod.png") as im:
        assert im.size == (810, 643), im.size


def test_pages_use_the_language_still():
    src = (ROOT / "tools" / "gen_view2026_pages.py").read_text(encoding="utf-8")
    assert 'story.get("stills", {}).get(label_lang, story["still"])' in src


def test_rendered_pages_point_at_the_language_variant():
    """生成済みのページが台帳の言語別の版(英語は静止画のこともある)を指し、消した GIF を指さない。"""
    pages = {"ja": VIEW / "index.md", "en": VIEW / "en" / "index.md"}
    checked = 0
    for lang, page in pages.items():
        text = page.read_text(encoding="utf-8")
        for pid in audit.AUDITED_POCS:
            entry = STORY[pid]
            if pid not in text:
                continue
            variant = entry["variants"][lang]["path"]
            assert variant in text, (lang, pid, variant)
            assert entry["stills"][lang] in text, (lang, pid)
            if variant.endswith(".png"):
                assert "%s/story.%s.gif" % (pid, lang) not in text, (lang, pid)
            checked += 1
    assert checked >= len(audit.AUDITED_POCS), checked


def test_audit_rows_not_reproduced_are_not_english_ready():
    """監査の実行が repo の図を再現しなかった行は、区分が何であれ英語版に使わない。"""
    import gen_view2026_story_gifs as g
    pid = "poc_solar_el_inspection"
    ledger = {pid: json.loads(json.dumps(TEXT[pid]))}
    name = "15_real_cover.png"
    assert g._english_ready(pid, ledger)[name] == audit.CLASS_BILINGUAL
    ledger[pid]["figures"][name]["same_bytes_as_audit_run"] = False
    assert g._english_ready(pid, ledger)[name] == "not_reproduced_by_audit"
    ledger[pid]["figures"][name]["sha256"] = "0" * 64
    assert g._english_ready(pid, ledger)[name] == "changed_since_audit"
