# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pocviewer の学習用の型(lesson)と、時間つまみの物理量の読み(axis)の門(2026-10-25)。

固定するもの:
* ``lesson`` が DATA に載り、持つページだけに型の塊(CSS / 下のカード / JS)が入る。
  カードは ① 問い → ② 予想 → ③ 再生 を上に、④ 式 → 説明 → ⑤ 限界 を再生の下に並べる。
* 選択肢は 2〜3 個、answer は範囲内の int、鍵の欠け・未知の鍵・足りない訳は ValueError。
* ``axis`` は anim3d だけ。values が (T,) でない・NaN・段の k が 0 始まりの狭義増加でない・未知の鍵は ValueError。
  読みは「量の名前 = 値 単位」で、段ごとに名前・単位が変わる(node があれば関数を実際に走らせる)。
* lesson も axis も持たないページは前と同じバイト列。見出しは 8 言語そろう。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pocviewer as pv  # noqa: E402

TN = 6


def _tx(label: str) -> dict:
    return {l: "%s-%s" % (label, l) for l in pv.LANGS}


def _lesson(**over):
    d = {"question": _tx("q"), "choices": [_tx("c0"), _tx("c1"), _tx("c2")], "answer": 1,
         "explain": _tx("ex"), "formula": {l: "n1 sin θ1 = n2 sin θ2\nsin θc = n2 / n1" for l in pv.LANGS},
         "limit": _tx("lim")}
    d.update(over)
    return d


def _axis(**over):
    d = {"values": np.linspace(0.0, 60.0, TN),
         "segments": [{"k": 0, "label": _tx("theta1"), "unit": "°", "decimals": 1},
                      {"k": 4, "label": _tx("theta0"), "unit": "mm", "decimals": 2}]}
    d.update(over)
    return d


def _tab(tid="a", badge="passed", **kw):
    c = np.array([[x, y, z] for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)])
    tri = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
           [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]
    return pv.viewer_anim3d_tab(tid, _tx("lab"), badge, _tx("txt"), np.arange(TN) / 10.0,
                                [{"name": "box", "pos": c, "faces": tri, "rgb": [79, 195, 247]}],
                                np.zeros((TN, 1, 3)), np.tile([1.0, 0, 0, 0], (TN, 1, 1)), **kw)


def _spec(tabs):
    return pv.viewer_spec("ls", _tx("title"), _tx("sub"), _tx("hint"), tabs)


def _data(html: str) -> dict:
    m = re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S)
    assert m, "DATA が見つからない"
    return json.loads(m.group(1))


def test_lesson_is_packed_and_the_block_is_injected():
    html = pv._build_html(_spec([_tab("a", lesson=_lesson()), _tab("b", "limit")]), list(pv.LANGS))
    d = _data(html)
    ls = d["tabs"][0]["lesson"]
    assert ls["answer"] == 1 and len(ls["choices"]) == 3 and ls["question"] == _tx("q")
    assert "lesson" not in d["tabs"][1]
    assert set(d["lu"]) == set(pv._LESSON_UI)
    for piece in ("function lessonTop", "function lessonBottom", "lessonBottom();", "aria-live",
                  '<div class="card" id="lesson2" style="display:none"></div>', "(t.lesson ? lessonTop(t)",
                  ".lsb.right"):
        assert piece in html, piece
    assert html.index('id="lesson2"') > html.index('id="plot"')            # ④ 式 ⑤ 限界は再生の下
    assert "axisText" not in html                                            # axis は別の塊


def test_lesson_and_checks_compose():
    row = {"what": _tx("w"), "criterion": "< 1e-9", "result": "1e-12", "ok": True}
    html = pv._build_html(_spec([_tab("a", lesson=_lesson(), checks=[row])]), ["ja", "en"])
    assert "badgeHTML(t) + '<b>' + esc(T(t.label)) + '</b>' + (t.lesson ? lessonTop(t)" in html
    assert "+ checksHTML(t);" in html


@pytest.mark.parametrize("over, msg", [
    ({"choices": [_tx("c0")]}, "2〜3 個"),
    ({"choices": [_tx("a"), _tx("b"), _tx("c"), _tx("d")]}, "2〜3 個"),
    ({"answer": 3}, "番号"),
    ({"answer": True}, "番号"),
    ({"answer": "1"}, "番号"),
    ({"extra": 1}, "未知の鍵"),
])
def test_broken_lesson_is_rejected(over, msg):
    with pytest.raises(ValueError, match=msg):
        pv._build_html(_spec([_tab(lesson=_lesson(**over))]), "ja")


def test_lesson_missing_key_and_translation_are_named():
    ls = _lesson()
    del ls["limit"]
    with pytest.raises(ValueError, match="limit"):
        pv._build_html(_spec([_tab(lesson=ls)]), "ja")
    with pytest.raises(ValueError, match=r"lesson\.choices\[2\]\.zh"):
        pv._build_html(_spec([_tab(lesson=_lesson(choices=[_tx("a"), _tx("b"), {"ja": "c", "en": "c"}]))]),
                       list(pv.LANGS))


def test_axis_is_packed_for_tabs_with_a_time_slider():
    html = pv._build_html(_spec([_tab("a", axis=_axis())]), ["ja", "en"])
    a = _data(html)["tabs"][0]["axis"]
    assert a["v"] == pytest.approx(list(np.linspace(0, 60, TN)))
    assert [g["k"] for g in a["seg"]] == [0, 4] and a["seg"][1]["unit"] == "mm" and a["seg"][1]["dec"] == 2
    assert "function axisText" in html and "tab.axis ? axisText(tab, f)" in html
    fr = pv.viewer_frames_tab("f", _tx("l"), "null", _tx("t"), np.zeros((TN, 3, 3), np.uint8))
    fr["axis"] = _axis()
    packed = _data(pv._build_html(_spec([fr]), "ja"))["tabs"][0]
    assert packed["axis"]["v"] == pytest.approx(list(np.linspace(0, 60, TN)))
    split = pv.viewer_split_tab("s", _tx("l"), "null", _tx("t"), np.zeros((3, 3), np.uint8),
                                np.zeros((3, 3), np.uint8), _tx("a"), _tx("b"))
    split["axis"] = _axis()
    with pytest.raises(ValueError, match="時間つまみ"):
        pv._build_html(_spec([split]), "ja")


@pytest.mark.parametrize("over, msg", [
    ({"values": np.zeros(TN - 1)}, "T の不一致"),
    ({"values": np.r_[np.zeros(TN - 1), np.nan]}, "NaN"),
    ({"segments": []}, "segments"),
    ({"segments": [{"k": 1, "label": _tx("x")}]}, "k = 0"),
    ({"segments": [{"k": 0, "label": _tx("x")}, {"k": 0, "label": _tx("y")}]}, "狭義の増加"),
    ({"segments": [{"k": 0, "label": _tx("x")}, {"k": TN, "label": _tx("y")}]}, "狭義の増加"),
    ({"segments": [{"k": 0, "label": _tx("x"), "decimals": 9}]}, "decimals"),
    ({"segments": [{"k": 0, "label": _tx("x"), "color": "red"}]}, "未知の鍵"),
    ({"extra": 1}, "未知の鍵"),
])
def test_broken_axis_is_rejected(over, msg):
    with pytest.raises(ValueError, match=msg):
        pv._build_html(_spec([_tab(axis=_axis(**over))]), "ja")


def test_page_without_lesson_or_axis_is_byte_identical():
    html = pv._build_html(_spec([_tab("a"), _tab("b", "limit")]), ["ja", "en"])
    assert pv._build_html(_spec([dict(_tab("a"), lesson=None, axis=None), _tab("b", "limit")]), ["ja", "en"]) == html
    assert "lessonTop" not in html and "axisText" not in html and "lesson2" not in html
    assert "<style>%s</style>" % pv._CSS in html and pv._BODY in html
    assert pv._JS.split("__DATA__")[0] in html and pv._JS.split("__DATA__")[1] in html


def test_lesson_headings_cover_all_eight_languages():
    for k, v in pv._LESSON_UI.items():
        assert set(v) == set(pv.LANGS) and all(x.strip() for x in v.values()), k
    assert "**" not in json.dumps(pv._LESSON_UI, ensure_ascii=False)


@pytest.mark.skipif(shutil.which("node") is None, reason="node が無い")
def test_axis_text_and_lesson_cards_render_in_node(tmp_path):
    html = pv._build_html(_spec([_tab("a", lesson=_lesson(), axis=_axis())]), ["ja", "en"])
    d = _data(html)
    grab = lambda name: re.search(r"function %s\(.*?\n\}\n" % name, html, re.S).group(0)   # noqa: E731
    stub = ("const D = %s; let L = 'en'; const lsPick = {a: 0}; const ABC = 'ABC';\n"
            "const T = o => o == null ? '' : (typeof o === 'string' ? o : (o[L] || ''));\n"
            "const LU = k => T(D.lu[k]);\n"
            "const esc = s => String(s).replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));\n"
            "const box = {style: {}, innerHTML: ''}; const $ = id => box; const get = () => D.tabs[0];\n" % json.dumps(d))
    f = tmp_path / "t.js"
    f.write_text(stub + grab("axisText") + grab("lessonTop") + grab("lessonBottom") +
                 "const t = D.tabs[0]; lessonBottom();\n"
                 "console.log(JSON.stringify([axisText(t, 0), axisText(t, 3), axisText(t, 5), lessonTop(t), box.innerHTML]));\n",
                 encoding="utf-8")
    r = subprocess.run(["node", str(f)], capture_output=True, text=True, stdin=subprocess.DEVNULL, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    a0, a3, a5, top, bottom = json.loads(r.stdout)
    assert a0 == "theta1-en = 0.0°" and a3 == "theta1-en = 36.0°" and a5 == "theta0-en = 60.00 mm"
    assert top.index("①") < top.index("②") < top.index("③")
    assert top.count("<button") == 3 and "Not quite. The answer is B." in top and "ex-en" in top
    assert 'class="lsb wrong"' in top and 'class="lsb right"' in top
    assert bottom.index("④") < bottom.index("Explanation") < bottom.index("⑤")
    assert "n1 sin θ1 = n2 sin θ2<br>sin θc = n2 / n1" in bottom and "txt-en" in bottom and "lim-en" in bottom


@pytest.mark.skipif(shutil.which("node") is None, reason="node が無い")
def test_the_full_page_script_is_valid_javascript(tmp_path):
    row = {"what": _tx("w"), "criterion": "< 1e-9", "result": "1e-12", "ok": True}
    html = pv._build_html(_spec([_tab("a", lesson=_lesson(), axis=_axis(), checks=[row])]), list(pv.LANGS), True)
    js = html.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    f = tmp_path / "p.js"
    f.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr
