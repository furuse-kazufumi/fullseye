# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pocviewer(``fullseye.write_viewer``)—— PoC の結果を 1 枚の HTML ビューアにする公開 API の門。

固定するもの: 4 種のペイロード(mesh / points / frames / split)が組めて HTML として読める /
全タブの題が入る / 埋めた配列が量子化の刻みの半分以内で戻る / 外部 URL を読まない /
言語ごとに単言語のページに他言語の字が混ざらない / 訳が欠ければ(欠けた鍵を名指して)止まる /
壊れた仕様(形・NaN・未知のバッジ・未知の種類・空のタブ)は黙って通さない / MCP tool も同じ門を通る。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pocviewer as pv  # noqa: E402

RNG = np.random.default_rng(3)


def _tx(label: str) -> dict:
    """8 言語ぶんの文字列(テスト用に、言語ごとに違う字を入れる)。"""
    return {l: "%s-%s" % (label, l) for l in pv.LANGS}


def _tiny_tabs() -> list:
    pos = RNG.uniform([-3, 10, 100], [3, 20, 120], (200, 3))
    val = RNG.uniform(-1, 1, 200)
    cb = {"lo": -1.0, "hi": 1.0, "unit": "mm", "cmap": "div", "label": _tx("cbar")}
    tri = np.array([[0, 1, 2], [0, 2, 3], [1, 4, 2]])
    mpos = RNG.uniform(0, 5, (5, 3))
    frames = RNG.integers(0, 256, (6, 12, 16), dtype=np.uint8)
    xy = np.column_stack([np.linspace(3, 12, 6), np.linspace(4, 8, 6)])
    img = RNG.integers(0, 256, (10, 14, 3), dtype=np.uint8)
    return [
        pv.viewer_mesh_tab("m", _tx("mesh"), "passed", _tx("mtext"), mpos, tri, RNG.uniform(-1, 1, 5), cb,
                           numbers=[pv.viewer_number(_tx("nl"), "1.5 mm")]),
        pv.viewer_points_tab("p", _tx("points"), "limit", _tx("ptext"), pos, val=val, cbar=cb,
                             ghost=RNG.uniform(0, 1, (30, 3))),
        pv.viewer_points_tab("rgb", _tx("rgbpts"), "null", _tx("rtext"), pos,
                             rgb=RNG.integers(0, 256, (200, 3), dtype=np.uint8)),
        pv.viewer_frames_tab(
            "f", _tx("frames"), "passed", _tx("ftext"), frames, dt=0.2,
            boxes=[{"label": _tx("box"), "color": "#4fc3f7", "xy": xy, "size": [5, 5],
                    "flag": np.arange(6) > 3, "flag_text": _tx("flag")}],
            series=[{"label": _tx("ser"), "values": [1, 0.9, np.nan, 0.5, 0.4, 0.3], "lo": 0, "hi": 1,
                     "threshold": 0.6}]),
        pv.viewer_split_tab("s", _tx("split"), "limit", _tx("stext"), img, img[::-1], _tx("before"), _tx("after")),
    ]


def _spec(tabs=None) -> dict:
    return pv.viewer_spec("tiny", _tx("title"), _tx("sub"), _tx("hint"), tabs or _tiny_tabs(), credit=_tx("credit"))


def _data(html: str) -> dict:
    m = re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S)
    assert m, "DATA が見つからない"
    return json.loads(m.group(1))


class _P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: list = []
        self.attrs: list = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs += [(tag, k, v) for k, v in attrs]


# --------------------------------------------------------------------------- #
def test_every_payload_kind_builds_and_the_html_parses():
    html = pv._build_html(_spec(), list(pv.LANGS))
    p = _P()
    p.feed(html)
    assert {"canvas", "script", "style", "select"} <= set(p.tags)
    assert html.startswith("<!doctype html>")
    assert 'lang="ja"' in html.split("\n")[1]                       # 先頭の言語が既定


def test_every_tab_label_is_in_the_page_in_every_language():
    d = _data(pv._build_html(_spec(), list(pv.LANGS)))
    assert [t["id"] for t in d["tabs"]] == ["m", "p", "rgb", "f", "s"]
    for t, lab in zip(d["tabs"], ("mesh", "points", "rgbpts", "frames", "split")):
        for l in pv.LANGS:
            assert t["label"][l] == "%s-%s" % (lab, l)


def test_quantised_arrays_round_trip_within_half_a_step():
    tabs = _tiny_tabs()
    d = _data(pv._build_html(_spec(tabs), ["ja"]))
    A = d["arrays"]
    by = {t["id"]: t for t in d["tabs"]}
    for src in (tabs[1], tabs[2]):                                   # points
        rec = A[by[src["id"]]["pos"]]
        back = pv._decode_array(rec)
        assert back.shape == src["pos"].shape
        assert np.isfinite(back).all()
        assert (np.abs(back - src["pos"]) <= pv._quant_step(rec) / 2 + 1e-9).all()
    rec = A[by["p"]["val"]]                                          # 値(カラーバー範囲でクリップ)
    assert np.abs(pv._decode_array(rec) - np.clip(tabs[1]["val"], -1, 1)).max() <= pv._quant_step(rec)[0] / 2 + 1e-9
    assert np.array_equal(pv._decode_array(A[by["rgb"]["rgb"]]), tabs[2]["rgb"])       # 無損失
    assert np.array_equal(pv._decode_array(A[by["m"]["faces"]]), tabs[0]["faces"])
    assert np.array_equal(pv._decode_array(A[by["f"]["frames"]]), tabs[3]["frames"])
    assert np.array_equal(pv._decode_array(A[by["s"]["before"]]), tabs[4]["before"])
    ser = by["f"]["series"][0]["values"]
    assert ser[2] is None and ser[0] == 1.0                           # NaN は null


def test_identical_arrays_are_shared_between_tabs():
    pos = RNG.uniform(0, 10, (50, 3))
    cb = {"lo": 0, "hi": 1}
    tabs = [pv.viewer_points_tab("a", _tx("a"), "null", _tx("t"), pos, val=RNG.uniform(0, 1, 50), cbar=cb),
            pv.viewer_points_tab("b", _tx("b"), "passed", _tx("t"), pos, val=RNG.uniform(0, 1, 50), cbar=cb)]
    d = _data(pv._build_html(_spec(tabs), ["ja"]))
    assert d["tabs"][0]["pos"] == d["tabs"][1]["pos"]                 # 位置は 1 本
    assert d["tabs"][0]["val"] != d["tabs"][1]["val"]


def test_no_external_loads():
    html = pv._build_html(_spec(), list(pv.LANGS))
    assert "http://" not in html and "https://" not in html
    p = _P()
    p.feed(html)
    assert len(p.attrs) > 0                       # 属性を 1 つも読めていない(空)なら以下の検査は何も見ていない
    for tag, k, v in p.attrs:
        assert not (k in ("src", "href", "action") and v and re.match(r"(?i)(https?:)?//", v)), (tag, k, v)
    assert not re.search(r"@import|url\(|\bfetch\(|XMLHttpRequest|\bimport\(", html)


@pytest.mark.skipif(shutil.which("node") is None, reason="node が無い")
def test_the_page_script_is_valid_javascript(tmp_path):
    html = pv._build_html(_spec(), list(pv.LANGS))
    js = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    f = tmp_path / "v.js"
    f.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


# --------------------------------------------------------------------------- #
# 言語                                                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("lang", pv.LANGS)
def test_single_language_build_has_no_other_language_chrome(lang):
    tabs = [pv.viewer_points_tab("p", _tx("t"), "limit", _tx("x"), RNG.uniform(0, 1, (20, 3)),
                                 val=RNG.uniform(0, 1, 20), cbar={"lo": 0, "hi": 1, "label": _tx("c")})]
    html = pv._build_html(_spec(tabs), lang)
    d = _data(html)
    assert d["langs"] == [lang] and list(d["langnames"]) == [lang]
    for table in (d["ui"], d["badges"]):
        for k, v in table.items():
            assert list(v) == [lang], (k, list(v))                    # 構造: 余計な言語の鍵が無い
            assert v[lang] == (pv.UI.get(k) or pv.BADGES.get(k))[lang]
    # 文字の面: 他言語にだけある操作系の文字列が、ページのどこにも無い
    own = {s for table in (pv.UI, pv.BADGES) for v in table.values() for s in [v[lang]]}
    esc = lambda s: json.dumps(s, ensure_ascii=True)[1:-1]            # noqa: E731
    chrome = [x for tb in (d["ui"], d["badges"]) for v in tb.values() for x in v.values()]
    chrome += list(d["langnames"].values())
    for other in pv.LANGS:
        if other == lang:
            continue
        for table in (pv.UI, pv.BADGES):
            for key, v in table.items():
                s = v[other]
                if s in own or len(s) < 4:
                    continue
                assert s not in chrome, (lang, other, key, s)
                if not s.isascii():                                       # 他の文字体系は、ページ全体のどこにも無い
                    assert esc(s) not in html, (lang, other, key, s)
    assert d["title"] == {lang: "title-%s" % lang}                    # 仕様の文字列も要求した言語だけ


@pytest.mark.parametrize("lang", pv.LANGS)
def test_every_language_has_every_chrome_string(lang):
    for k, v in list(pv.UI.items()) + list(pv.BADGES.items()):
        assert v.get(lang, "").strip(), (k, lang)
    assert pv.LANG_NAMES[lang]


def test_a_missing_translation_raises_and_names_the_keys(tmp_path):
    spec = _spec()
    del spec["tabs"][0]["text"]["zh"]
    spec["title"].pop("ko")
    with pytest.raises(ValueError) as ei:
        pv._build_html(spec, ["ja", "zh", "ko"])
    msg = str(ei.value)
    assert "tab m.text.zh" in msg and "title.ko" in msg
    out = tmp_path / "x.html"
    with pytest.raises(ValueError):
        pv.write_viewer(spec, out, ["ja", "zh"])
    assert not out.exists()                                           # 失敗したら何も書かない
    pv._build_html(spec, ["ja", "en"])                                 # 要求していない言語の欠けは問わない


def test_a_plain_string_is_not_accepted_for_a_translated_field():
    spec = _spec()
    spec["subtitle"] = "日本語だけ"
    with pytest.raises(ValueError, match="subtitle"):
        pv._build_html(spec, "ja")


@pytest.mark.parametrize("bad", [[], ["xx"], ["ja", "ja"], "english"])
def test_bad_lang_argument_raises(bad):
    with pytest.raises(ValueError):
        pv._build_html(_spec(), bad)


# --------------------------------------------------------------------------- #
# fail-closed                                                                    #
# --------------------------------------------------------------------------- #
def test_invalid_specs_are_rejected_not_passed_through():
    ok = _tiny_tabs()
    with pytest.raises(ValueError, match="tabs"):
        pv.viewer_spec("x", _tx("a"), _tx("b"), _tx("c"), [])
    with pytest.raises(ValueError, match="tabs"):
        pv._build_html({"title": _tx("a"), "subtitle": _tx("b"), "hint": _tx("c"), "tabs": []}, "ja")
    with pytest.raises(ValueError, match="badge"):
        pv._build_html(_spec([dict(ok[1], badge="pass")]), "ja")                        # 旧名は通さない
    with pytest.raises(ValueError, match="kind"):
        pv._build_html(_spec([dict(ok[1], kind="volume")]), "ja")
    nan_pos = ok[1]["pos"].copy()
    nan_pos[3, 1] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        pv._build_html(_spec([dict(ok[1], pos=nan_pos)]), "ja")
    with pytest.raises(ValueError, match="pos"):
        pv._build_html(_spec([dict(ok[1], pos=ok[1]["pos"][:, :2])]), "ja")
    with pytest.raises(ValueError, match="faces"):
        pv._build_html(_spec([dict(ok[0], faces=np.array([[0, 1, 99]]))]), "ja")
    with pytest.raises(ValueError, match="val"):
        pv._build_html(_spec([dict(ok[1], val=ok[1]["val"][:-1])]), "ja")
    with pytest.raises(ValueError, match="frames"):
        pv._build_html(_spec([dict(ok[3], frames=np.zeros((4, 4), np.uint8))]), "ja")
    with pytest.raises(ValueError, match="xy"):
        pv._build_html(_spec([dict(ok[3], boxes=[dict(ok[3]["boxes"][0], xy=np.zeros((5, 2)))])]), "ja")
    with pytest.raises(ValueError, match="before"):
        pv._build_html(_spec([dict(ok[4], after=ok[4]["after"][:, :, 0])]), "ja")
    with pytest.raises(ValueError, match="cbar"):
        pv._build_html(_spec([dict(ok[1], cbar={"lo": 1, "hi": 1})]), "ja")
    dup = [dict(ok[1]), dict(ok[1])]
    with pytest.raises(ValueError, match="重複"):
        pv._build_html(_spec(dup), "ja")
    with pytest.raises(ValueError, match="id"):
        pv._build_html(_spec([dict(ok[1], id="a b")]), "ja")


def test_write_viewer_returns_the_path_and_writes_one_file(tmp_path):
    out = tmp_path / "sub" / "v.html"
    got = pv.write_viewer(_spec(), out, ["ja", "en", "fr"])
    assert got == str(out) and out.is_file()
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_integer_json_images_are_taken_as_0_255():
    img = [[[0, 128, 255]] * 4] * 3                                    # JSON 経由の入れ子 list
    d = _data(pv._build_html(_spec([pv.viewer_split_tab("s", _tx("a"), "null", _tx("b"), img, img,
                                                       _tx("c"), _tx("d"))]), "ja"))
    assert pv._decode_array(d["arrays"][d["tabs"][0]["before"]]).max() == 255
    with pytest.raises(ValueError, match="0..255"):
        pv._build_html(_spec([pv.viewer_split_tab("s", _tx("a"), "null", _tx("b"), [[300]], [[1]],
                                                 _tx("c"), _tx("d"))]), "ja")


def test_the_public_facade_exposes_the_api():
    import fullseye as fs
    for n in ("write_viewer", "viewer_spec", "viewer_text", "viewer_number", "viewer_mesh_tab",
              "viewer_points_tab", "viewer_frames_tab", "viewer_split_tab", "pocviewer"):
        assert hasattr(fs, n), n
    assert fs.write_viewer is pv.write_viewer
    assert fs.viewer_text("a", "b", de="c") == {"ja": "a", "en": "b", "de": "c"}
    with pytest.raises(ValueError):
        fs.viewer_text("a", "b", xx="c")


# --------------------------------------------------------------------------- #
# MCP                                                                            #
# --------------------------------------------------------------------------- #
def _json_spec() -> dict:
    """MCP に渡す JSON(配列は入れ子の list)。"""
    pos = RNG.uniform(0, 1, (12, 3)).tolist()
    return json.loads(json.dumps(pv.viewer_spec(
        "mcp_tiny", _tx("t"), _tx("s"), _tx("h"),
        [pv.viewer_points_tab("a", _tx("a"), "passed", _tx("x"), pos, val=RNG.uniform(0, 1, 12).tolist(),
                              cbar={"lo": 0, "hi": 1})]), default=lambda o: o.tolist()))


def test_mcp_tool_writes_into_the_sandbox_and_rejects_bad_input():
    from fullseye.mcp import Catalog, call_tool
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import ArgError, TOOLS
    assert "fullseye_write_viewer" in TOOLS
    cat, store = Catalog.load(), HandleStore()
    r = call_tool("fullseye_write_viewer", {"spec": _json_spec(), "lang": ["ja", "de"]}, cat, store)
    assert r["isError"] is False
    path = r["structuredContent"]["path"]
    assert os.path.dirname(path) == store.thumb_dir and os.path.isfile(path)
    assert r["content"][1]["type"] == "resource_link" and r["content"][1]["mimeType"] == "text/html"
    assert _data(open(path, encoding="utf-8").read())["langs"] == ["ja", "de"]
    for bad in ({"spec": _json_spec(), "name": "../evil"}, {"spec": _json_spec(), "name": "a/b"},
                {"spec": _json_spec(), "lang": ["xx"]}, {"spec": _json_spec(), "lang": [1]},
                {"spec": {"tabs": []}}, {"spec": []}, {"spec": _json_spec(), "extra": 1}):
        with pytest.raises(ArgError):
            call_tool("fullseye_write_viewer", bad, cat, store)
    s2 = _json_spec()
    del s2["title"]["fr"]
    with pytest.raises(ArgError, match="title.fr"):                  # 欠けた訳は -32602(補わない)
        call_tool("fullseye_write_viewer", {"spec": s2, "lang": ["ja", "fr"]}, cat, store)


# --------------------------------------------------------------------------- #
# ViEW2026 の「触って見る」第 2 弾(tools/build_view2026_viewers.py の 4 本)。          #
# 各 PoC の関数を呼び直して作る(手で写した数字は 1 つも無い)ので、ここで 1 本ずつ実際に組んで固める。  #
# --------------------------------------------------------------------------- #
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECOND_BATCH = {
    "poc_thermography_ndt": ["frames", "split", "split", "split"],
    "poc_grating_interferometry": ["frames", "split", "frames", "split", "split"],
    "poc_phase_measuring_deflectometry": ["split", "frames", "split", "split", "split", "split"],
    "poc_asteroid_curvature": ["points", "points", "points", "points"],
}
THIRD_BATCH = {
    "poc_focus_stacking", "poc_interferometry_step", "poc_polarization_specular",
    "poc_photoelasticity", "poc_compound_eye",
    "poc_ct_void_morphology", "poc_active_contours",
}


def _builders():
    for p in (os.path.join(_ROOT, "tools"), _ROOT):
        if p not in sys.path:
            sys.path.insert(0, p)
    import build_view2026_viewers as B
    return B


def test_the_viewer_registry_counts_are_fixed():
    B = _builders()
    assert len(B.BUILDERS) == 14                                     # 第 1 弾 3 + 第 2 弾 4 + 引数掃引 7
    assert set(SECOND_BATCH) <= set(B.BUILDERS)
    d = json.load(open(os.path.join(_ROOT, "docs", "view2026", "exhibits.json"), encoding="utf-8"))
    assert [i["id"] for i in d["viewers"]["items"]] == list(B.BUILDERS)   # 案内ページの並び = 登録の並び
    assert len(B.BUILDERS) == 14                                     # 空の対象を周って「通った」ことにしない
    for pid in B.BUILDERS:
        assert os.path.isfile(os.path.join(_ROOT, "docs", "view2026", "viewers", pid + ".html")), pid


@pytest.mark.parametrize("pid", sorted(THIRD_BATCH))
def test_parameter_sweep_viewer_has_a_physical_slider_and_is_small(pid):
    B = _builders()
    spec = B.BUILDERS[pid]()
    assert len(spec["tabs"]) == 1 and spec["tabs"][0]["kind"] == "frames"
    axis = spec["tabs"][0]["axis"]
    assert len(axis["values"]) == len(spec["tabs"][0]["frames"])
    assert axis["segments"][0]["label"] and axis["segments"][0]["k"] == 0
    # ★2026-10-30: 運動拡大の掃引は振幅を 40 倍にしても指標が 3.93 -> 3.97 で平らだった(64 px 用の読み出しを
    #   160 px の動画に当てていた)。つまみを動かしても絵も指標も変わらないビューアは偽物なので止める。
    fr = [np.asarray(f, np.float64) for f in spec["tabs"][0]["frames"]]
    assert len(fr) >= 8 and np.ptp(fr[-1] - fr[0]) > 0, "端のコマが同じ"
    for s in spec["tabs"][0]["series"]:
        v = np.asarray(s["values"], np.float64)
        assert np.ptp(v) > 0.05 * max(np.abs(v).max(), 1e-12), "指標が平ら: %s" % s["label"]
    assert len(pv._build_html(spec, B.ALL_LANGS).encode("utf-8")) < 5_000_000


@pytest.mark.parametrize("pid", sorted(SECOND_BATCH))
def test_second_batch_viewer_builds_with_all_languages_and_fails_closed(pid, tmp_path):
    B = _builders()
    spec = B.BUILDERS[pid]()
    kinds = SECOND_BATCH[pid]
    assert [t["kind"] for t in spec["tabs"]] == kinds
    assert {t["badge"] for t in spec["tabs"]} - {"passed"}           # 成功だけを並べない(限界か零点が最低 1 つ)
    out = pv.write_viewer(spec, tmp_path / (pid + ".html"), B.ALL_LANGS)
    html = open(out, encoding="utf-8").read()
    d = _data(html)
    assert d["langs"] == list(pv.LANGS) and len(d["tabs"]) == len(kinds)
    assert len(html.encode("utf-8")) < 8_000_000                      # 第 2 弾は軽く(各 8 MB 未満)
    assert not re.search(r"(?<![0-9A-Za-z])[A-Za-z]:[\\/]", html), "ドライブ文字つきのパスが入っている"   # 手元のパスを入れない
    assert "/users/" not in html.lower() and "/home/" not in html.lower()
    tabs = spec["tabs"]
    assert tabs and len(pv.LANGS) == 8
    for lang in pv.LANGS:                                             # 全タブの題が全言語にある(空の訳を通さない)
        for t in tabs:
            assert t["label"][lang].strip() and t["text"][lang].strip(), (pid, t["id"], lang)
    spec["tabs"][0]["text"].pop("hi")                                 # 1 言語だけ欠ければ止まる(補わない)
    with pytest.raises(ValueError, match="hi"):
        pv._build_html(spec, B.ALL_LANGS)


def test_a_shipped_second_batch_file_is_the_current_builder_output_in_shape():
    """docs/view2026/viewers/ の実物が、いまの仕様と同じタブ構成・言語であること(古い生成物を残さない)。"""
    assert len(SECOND_BATCH) == 4
    for pid, kinds in SECOND_BATCH.items():
        d = _data(open(os.path.join(_ROOT, "docs", "view2026", "viewers", pid + ".html"), encoding="utf-8").read())
        assert d["langs"] == list(pv.LANGS) and len(d["tabs"]) == len(kinds), pid
