# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pocviewer のバッジの説明(定義の一言 + 確かめた項目の表 + 凡例)の門(2026-10-25)。

固定するもの:
* タブの任意の鍵 ``checks`` が DATA に載り、どれかのタブが持つページだけに説明の塊(CSS / 凡例 / JS)が入る。
* ``checks`` を持たないページは前と同じバイト列(説明の塊が入らない・本体の JS / CSS / 本文がそのまま)。
* ok:false の行があるのに badge が passed なら ValueError(fail-closed)。limit / null なら通る。
* 空の list・未知の鍵・欠けた鍵・bool でない ok・足りない訳は ValueError(黙って通さない)。
* 表記・定義・凡例・表の見出しが 8 言語そろう。en の表記は "Checked" で、"gate" は定義の文の中だけ。
  凡例は 3 種のバッジの表記を全部名指しする(「門を通った」と「限界を見せる」を対で読ませる)。
* 表の HTML(node があれば実際に関数を走らせる)、ページの JS の構文(node があれば)。
* 翻訳の層 anim3d_i18n が checks の文字列を拾い、数値トークンの照合も通す。
"""
from __future__ import annotations

import importlib.util
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


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tx(label: str) -> dict:
    return {l: "%s-%s" % (label, l) for l in pv.LANGS}


def _cube():
    c = np.array([[x, y, z] for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)])
    tri = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
           [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]
    return c, tri


def _tab(tid="a", badge="passed", checks=None):
    pos, tri = _cube()
    T = 4
    t = np.arange(T) / 10.0
    xyz = np.zeros((T, 1, 3))
    quat = np.tile([1.0, 0, 0, 0], (T, 1, 1))
    return pv.viewer_anim3d_tab(tid, _tx("lab" + tid), badge, _tx("txt" + tid), t,
                                [{"name": "box", "pos": pos, "faces": tri, "rgb": [79, 195, 247]}], xyz, quat,
                                checks=checks)


def _row(ok=True, what="w"):
    return {"what": _tx(what), "criterion": "< 1e-9", "result": "3.2e-12", "ok": ok}


def _spec(tabs):
    return pv.viewer_spec("bh", _tx("title"), _tx("sub"), _tx("hint"), tabs)


def _data(html: str) -> dict:
    m = re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S)
    assert m, "DATA が見つからない"
    return json.loads(m.group(1))


# --------------------------------------------------------------------------- 載る・入る
def test_checks_are_packed_and_the_help_block_is_injected():
    html = pv._build_html(_spec([_tab("a", "passed", [_row(), _row(what="v")]), _tab("b", "limit")]),
                          list(pv.LANGS))
    d = _data(html)
    a, b = d["tabs"]
    assert len(a["checks"]) == 2
    assert a["checks"][0] == {"what": _tx("w"), "criterion": "< 1e-9", "result": "3.2e-12", "ok": True}
    assert "checks" not in b                                       # 無いタブは定義の一言だけ
    assert d["badges"]["passed"]["en"] == "Checked"
    assert d["badges"]["passed"]["ja"] == "門を通った"
    assert set(d["bh"]) == {"def", "legend", "ui"}
    assert set(d["bh"]["def"]) == {"passed", "limit", "null"}
    for piece in ("function badgeHTML", "function checksHTML", "function renderLegend", "aria-expanded",
                  "renderLegend(); renderTabs(); renderMeta();", "badgeHTML(t) + '<b>'", "+ checksHTML(t);",
                  '<div class="legend" id="legend"></div>', ".bhbox[hidden]", "e.key === 'Enter'"):
        assert html.count(piece) >= 1, piece
    assert html.count(pv._JS_BH) == 1


def test_checks_through_the_helper_default_none_make_no_key():
    for fn, extra in ((pv.viewer_frames_tab, {"frames": np.zeros((2, 3, 3), np.uint8)}),
                      (pv.viewer_split_tab, {"before": np.zeros((3, 3), np.uint8), "after": np.zeros((3, 3), np.uint8),
                                             "label_before": _tx("b"), "label_after": _tx("a")})):
        assert "checks" not in fn("x", _tx("l"), "null", _tx("t"), **extra)
        assert fn("x", _tx("l"), "null", _tx("t"), checks=[_row()], **extra)["checks"] == [_row()]
    pos, tri = _cube()
    assert "checks" not in pv.viewer_mesh_tab("m", _tx("l"), "null", _tx("t"), pos, tri, np.zeros(8),
                                              {"lo": 0, "hi": 1})
    assert "checks" in pv.viewer_points_tab("p", _tx("l"), "null", _tx("t"), pos, rgb=np.zeros((8, 3), np.uint8),
                                            checks=[_row()])


def test_page_without_checks_is_byte_identical():
    """checks を持たないページは前と同じ(公開済みのビューアに drift を出さない)。"""
    spec = _spec([_tab("a"), _tab("b", "limit")])
    html = pv._build_html(spec, ["ja", "en"])
    spec2 = _spec([dict(_tab("a"), checks=None), _tab("b", "limit")])    # None は「無い」と同じ
    assert pv._build_html(spec2, ["ja", "en"]) == html
    assert "badgeHTML" not in html and "legend" not in html and "bhbox" not in html
    assert "<style>%s</style>" % pv._CSS in html and pv._BODY in html
    assert pv._JS.split("__DATA__")[0] in html and pv._JS.split("__DATA__")[1] in html
    d = _data(html)
    assert "bh" not in d and d["badges"]["passed"]["en"] == pv.BADGES["passed"]["en"]


# --------------------------------------------------------------------------- fail-closed
def test_failed_row_under_a_passed_badge_is_rejected():
    with pytest.raises(ValueError, match="passed なのに ok:false"):
        pv._build_html(_spec([_tab("a", "passed", [_row(), _row(ok=False)])]), "ja")


@pytest.mark.parametrize("badge", ["limit", "null"])
def test_failed_rows_are_allowed_under_limit_and_null(badge):
    d = _data(pv._build_html(_spec([_tab("a", badge, [_row(ok=False), _row()])]), "ja"))
    assert [c["ok"] for c in d["tabs"][0]["checks"]] == [False, True]


@pytest.mark.parametrize("bad, msg", [
    ([], "1 行以上"),
    ("x", "1 行以上"),
    ([dict(_row(), extra=1)], "未知の鍵"),
    ([{"what": _tx("w"), "criterion": "< 1", "ok": True}], "result"),
    ([dict(_row(), ok=1)], "True / False"),
    ([dict(_row(), ok="yes")], "True / False"),
    ([dict(_row(), result="  ")], "空の値"),
    (["row"], "dict"),
])
def test_broken_checks_are_rejected(bad, msg):
    with pytest.raises(ValueError, match=msg):
        pv._build_html(_spec([_tab("a", "limit", bad)]), "ja")


def test_missing_translation_in_checks_is_named():
    row = dict(_row(), what={"ja": "項目", "en": "item"}, result={"ja": "1", "en": "1"})
    with pytest.raises(ValueError, match=r"checks\[0\]\.what\.zh"):
        pv._build_html(_spec([_tab("a", "passed", [row])]), list(pv.LANGS))
    pv._build_html(_spec([_tab("a", "passed", [row])]), ["ja", "en"])        # 要求した言語だけ見る


# --------------------------------------------------------------------------- 8 言語
def test_help_strings_cover_all_eight_languages():
    for k, v in pv._BADGE_HELP.items():
        for part in ("label", "def"):
            assert set(v[part]) == set(pv.LANGS), (k, part)
            assert all(isinstance(x, str) and x.strip() for x in v[part].values()), (k, part)
    assert set(pv._BADGE_LEGEND) == set(pv.LANGS) and all(x.strip() for x in pv._BADGE_LEGEND.values())
    for k, v in pv._CHECK_UI.items():
        assert set(v) == set(pv.LANGS) and all(x.strip() for x in v.values()), k
    assert set(pv._BADGE_HELP) == set(pv.BADGES)


def test_english_says_checked_and_gate_only_inside_the_definition():
    assert pv._BADGE_HELP["passed"]["label"]["en"] == "Checked"
    assert pv._BADGE_HELP["passed"]["def"]["ja"].startswith("門 = 自動の答え合わせ。")
    assert "gate" in pv._BADGE_HELP["passed"]["def"]["en"]
    for v in pv._BADGE_HELP.values():
        assert "gate" not in v["label"]["en"].lower()
    assert pv._BADGE_HELP["passed"]["label"]["zh"] == "已验证" and pv._BADGE_HELP["passed"]["label"]["tw"] == "已驗證"


def test_legend_names_all_three_badges_so_passed_and_limit_read_as_a_pair():
    for l in pv.LANGS:
        for k in ("passed", "limit", "null"):
            assert pv._BADGE_HELP[k]["label"][l] in pv._BADGE_LEGEND[l], (l, k)
    # 限界の定義も「門を通った」側を名指す(対)。en / de / fr は文の中で活用形になるので語幹で見る
    stem = {"en": "checked", "de": "geprüft", "fr": "vérifié"}
    for l in pv.LANGS:
        assert stem.get(l, pv._BADGE_HELP["passed"]["label"][l]) in pv._BADGE_HELP["limit"]["def"][l], l


def test_public_text_has_no_bold_markers_or_urls():
    blob = json.dumps([pv._BADGE_HELP, pv._BADGE_LEGEND, pv._CHECK_UI], ensure_ascii=False)
    assert "**" not in blob and "http" not in blob


# --------------------------------------------------------------------------- 表の HTML と JS
@pytest.mark.skipif(shutil.which("node") is None, reason="node が無い")
def test_checks_table_html_is_rendered_by_the_page_function(tmp_path):
    html = pv._build_html(_spec([_tab("a", "limit", [_row(), dict(_row(ok=False), what=_tx("<x>"))])]),
                          ["ja", "en"])
    fn = re.search(r"function checksHTML\(t\)\{.*?\n\}\n", html, re.S).group(0)
    bfn = re.search(r"function badgeHTML\(t\)\{.*?\n\}\n", html, re.S).group(0)
    d = _data(html)
    stub = ("const D = %s; let L = 'en'; const bhOpen = {a: true};\n"
            "const T = o => o == null ? '' : (typeof o === 'string' ? o : (o[L] || ''));\n"
            "const BU = k => T(D.bh.ui[k]);\n"
            "const esc = s => String(s).replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));\n"
            % json.dumps(d))
    f = tmp_path / "t.js"
    f.write_text(stub + fn + bfn + "const t = D.tabs[0];\nconsole.log(JSON.stringify([checksHTML(t), badgeHTML(t)]));\n",
                 encoding="utf-8")
    r = subprocess.run(["node", str(f)], capture_output=True, text=True, stdin=subprocess.DEVNULL, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    box, badge = json.loads(r.stdout)
    assert box.count("<tr") == 3 and "<table" in box and " hidden" not in box
    for s in ("What was checked", "Criterion", "Result", "&lt; 1e-9", "3.2e-12", "✓ pass", "✗ outside",
              "w-en", "&lt;x&gt;-en", pv._BADGE_HELP["limit"]["def"]["en"]):
        assert s in box, s
    assert 'aria-expanded="true"' in badge and 'role="button"' in badge and 'tabindex="0"' in badge
    assert "Shows the limit" in badge


@pytest.mark.skipif(shutil.which("node") is None, reason="node が無い")
def test_the_help_page_script_is_valid_javascript(tmp_path):
    html = pv._build_html(_spec([_tab("a", "passed", [_row()]), _tab("b", "null")]), list(pv.LANGS), True)
    js = html.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    f = tmp_path / "p.js"
    f.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr


# --------------------------------------------------------------------------- 翻訳の層
def test_i18n_layer_picks_up_check_strings_and_checks_numbers():
    I18N = _load("anim3d_i18n")
    t = pv.viewer_text
    row = {"what": t("屈折角 30° の誤差", "Refraction error at 30°"), "criterion": "< 1e-9",
           "result": t("最大 3.2e-12 rad", "max 3.2e-12 rad"), "ok": True}
    spec = {"id": "x", "title": t("見本", "Sample"), "subtitle": t("副", "Sub"), "hint": t("回す", "Rotate"),
            "tabs": [dict(_tab("a"), label=t("箱", "Box"), text=t("説明", "Text"), checks=[row])]}
    found = {d["en"] for _, d in I18N.iter_texts(spec)}
    assert {"Refraction error at 30°", "max 3.2e-12 rad"} <= found
    tr = lambda ja, en_like: {"ja": ja, **{l: en_like for l in I18N.NEW_LANGS}}   # noqa: E731
    table = {"strings": {"Sample": tr("見本", "S"), "Sub": tr("副", "S"), "Rotate": tr("回す", "R"),
                         "Box": tr("箱", "B"), "Text": tr("説明", "T"),
                         "Refraction error at 30°": tr("屈折角 30° の誤差", "err 30°"),
                         "max 3.2e-12 rad": tr("最大 3.2e-12 rad", "max 3.2e-12 rad")}}
    spec8 = I18N.translate(spec, table)
    assert spec8["tabs"][0]["checks"][0]["what"]["de"] == "err 30°"
    assert spec8["tabs"][0]["checks"][0]["criterion"] == "< 1e-9"           # 全言語共通の文字列はそのまま
    pv._build_html(spec8, list(pv.LANGS), True)
    table["strings"]["max 3.2e-12 rad"]["fr"] = "max 3.3e-12 rad"            # 数字の古い訳
    with pytest.raises(I18N.GateError, match="数値トークン"):
        I18N.translate(spec, table)
