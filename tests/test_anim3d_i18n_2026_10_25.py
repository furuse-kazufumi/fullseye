# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""動く 3-D を ViEW2026 の入口ページに 8 言語で載せる仕組みの門(2026-10-25)。

* tools/anim3d_i18n.py: 未訳・数値の不一致・op 名の欠落・古い訳で **止まる**(壊して確かめる)
* pocviewer の detect_lang: ``?lang`` が最優先、無ければ navigator.language の写像(node で JS を実際に走らせる)
* 既定(detect_lang=False)の生成物は 1 バイトも変わらない
* 入口ページ: 動く 3-D のタイルは ?lang 付き・容量つき、ビューアは 8 言語そろう
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


I18N = _load("anim3d_i18n")
G = _load("gen_view2026_pages")
pv = I18N.pv


def _tr(ja, zh, tw, ko, de, hi, fr):
    return {"ja": ja, "zh": zh, "tw": tw, "ko": ko, "de": de, "hi": hi, "fr": fr}


def _spec():
    t = pv.viewer_text
    tab = {"kind": "anim3d", "id": "a", "label": t("箱", "Box"), "text": t("残像 1.2 s", "Trail 1.2 s"),
           "numbers": [pv.viewer_number(t("コマ", "Frames"), "150 @ 30 fps")],
           "events": [{"t": 0.0, "label": t("つかむ", "Grasp")}],
           "made": t("fs.viewer_anim3d_tab で作図", "Drawn by fs.viewer_anim3d_tab")}
    return {"id": "x", "title": t("見本", "Sample"), "subtitle": t("副題", "Sub"),
            "hint": {"ja": "回す", "en": "Rotate", "zh": "旋转", "tw": "旋轉", "ko": "회전", "de": "Drehen",
                     "hi": "घुमाएँ", "fr": "Tourner"},                # 作例が 8 言語を書いた文字列は表が要らない
            "tabs": [tab]}


def _table():
    return {"strings": {
        "Box": _tr("箱", "箱子", "箱子", "상자", "Kiste", "box", "Boîte"),
        "Trail 1.2 s": _tr("残像 1.2 s", "残影 1.2 s", "殘影 1.2 s", "잔상 1.2 s", "Spur 1.2 s", "trail 1.2 s",
                           "Traînée 1.2 s"),
        "Frames": _tr("コマ", "帧数", "影格數", "프레임", "Bilder", "frames", "Images"),
        "Grasp": _tr("つかむ", "抓取", "抓取", "파지", "Greifen", "पकड़ना", "Saisie"),
        "Drawn by fs.viewer_anim3d_tab": _tr("fs.viewer_anim3d_tab で作図", "由 fs.viewer_anim3d_tab 绘制",
                                             "由 fs.viewer_anim3d_tab 繪製", "fs.viewer_anim3d_tab 로 그림",
                                             "Gezeichnet mit fs.viewer_anim3d_tab", "fs.viewer_anim3d_tab से बना",
                                             "Tracé avec fs.viewer_anim3d_tab"),
        "Sample": _tr("見本", "示例", "範例", "예제", "Beispiel", "उदाहरण", "Exemple"),
        "Sub": _tr("副題", "副标题", "副標題", "부제", "Untertitel", "उपशीर्षक", "Sous-titre"),
    }}


def test_complete_table_fills_all_eight_languages():
    spec = _spec()
    out = I18N.translate(spec, _table())
    texts = list(I18N.iter_texts(out))
    assert len(texts) == 8
    assert all(set(d) == set(pv.LANGS) for _, d in texts)
    assert out["tabs"][0]["label"]["de"] == "Kiste"
    assert out["hint"]["de"] == "Drehen"                              # 作例自身の訳を上書きしない
    assert "zh" not in spec["tabs"][0]["label"]                       # 元の仕様は変えない


def test_untranslated_string_stops_and_is_named():
    t = _table()
    del t["strings"]["Grasp"]
    del t["strings"]["Sub"]
    with pytest.raises(I18N.GateError) as e:
        I18N.translate(_spec(), t)
    msg = str(e.value)
    assert "'Grasp'" in msg and "'Sub'" in msg and "未訳" in msg


def test_number_mismatch_stops():
    t = _table()
    t["strings"]["Trail 1.2 s"]["de"] = "Spur 1.5 s"                  # 数字が古い訳
    with pytest.raises(I18N.GateError, match="de: 数値トークン"):
        I18N.translate(_spec(), t)


def test_unit_change_stops():
    t = _table()
    t["strings"]["Trail 1.2 s"]["zh"] = "残影 1.2 秒"                  # 単位が落ちた
    with pytest.raises(I18N.GateError, match="zh: 数値トークン"):
        I18N.translate(_spec(), t)


def test_missing_op_name_stops():
    t = _table()
    t["strings"]["Drawn by fs.viewer_anim3d_tab"]["ko"] = "뷰어로 그림"
    with pytest.raises(I18N.GateError, match=r"ko: op 名・コード片が訳に無い \['fs.viewer_anim3d_tab'\]"):
        I18N.translate(_spec(), t)


def test_stale_japanese_stops():
    t = _table()
    t["strings"]["Box"]["ja"] = "箱(旧)"
    with pytest.raises(I18N.GateError, match="古い訳"):
        I18N.translate(_spec(), t)


def test_empty_translation_stops():
    t = _table()
    t["strings"]["Box"]["hi"] = " "
    with pytest.raises(I18N.GateError, match="hi: 訳が空"):
        I18N.translate(_spec(), t)


def test_tokenisers():
    assert I18N.num_tokens("Top-down height image (0-0.6 m)") == {"0": 1, "0.6m": 1}
    assert I18N.num_tokens("Binarised: height 2-10 cm") == {"2": 1, "10cm": 1}
    assert I18N.num_tokens("fs.viewer_anim3d_tab uint16") == {}       # 名前の中の数字は数えない
    assert I18N.num_tokens("第3步 1e-4 rad") == {"3": 1, "1e-4rad": 1}  # CJK の直後の数字は数える
    assert I18N.code_tokens("use fs.viewer_anim3d_tab and drawTranslucent()") == {
        "fs.viewer_anim3d_tab": 1, "drawTranslucent()": 1}


def test_missing_json_is_a_pasteable_template():
    t = _table()
    del t["strings"]["Box"]
    js = I18N.missing_json("x", _spec(), t)
    assert js["missing"] == 1 and set(js["strings"]) == {"Box"}
    row = js["strings"]["Box"]
    assert row["ja"] == "箱" and all(row[l] == "" for l in I18N.NEW_LANGS)


# --------------------------------------------------------------------------- 言語の選び方
def _mini_spec():
    t = pv.viewer_text
    return pv.viewer_spec("m", t("a", "a"), t("b", "b"), t("c", "c"),
                          [pv.viewer_split_tab("s", t("d", "d"), "passed", t("e", "e"),
                                               [[0, 1], [2, 3]], [[3, 2], [1, 0]], t("f", "f"), t("g", "g"))])


def test_default_build_is_unchanged_and_detect_is_opt_in():
    spec = _mini_spec()
    plain = pv._build_html(spec, ["ja", "en"])
    assert pv._JS_LANG_LINE in plain and "pickLang" not in plain      # 既定 = 従来のページそのもの
    det = pv._build_html(spec, ["ja", "en"], detect_lang=True)
    assert "function pickLang" in det and pv._JS_LANG_LINE not in det
    assert det.replace(pv._JS_PICK_LANG, pv._JS_LANG_LINE) == plain   # 違いはこの 1 か所だけ


@pytest.mark.skipif(shutil.which("node") is None, reason="node が無い")
def test_pick_lang_mapping_in_node():
    fn = pv._JS_PICK_LANG.split("\nlet L = ")[0]
    cases = [  # (?lang, navigator.language, ページの言語, 期待)
        ("ko", "de-DE", "all", "ko"),                                  # ?lang が最優先
        ("xx", "de-DE", "all", "de"),                                  # 未対応の ?lang は無視
        (None, "zh-TW", "all", "tw"), (None, "zh-HK", "all", "tw"), (None, "zh-MO", "all", "tw"),
        (None, "zh-Hant-TW", "all", "tw"), (None, "zh-CN", "all", "zh"), (None, "zh", "all", "zh"),
        (None, "zh-Hans-SG", "all", "zh"), (None, "ko-KR", "all", "ko"), (None, "de-AT", "all", "de"),
        (None, "hi-IN", "all", "hi"), (None, "fr-CA", "all", "fr"), (None, "ja-JP", "all", "ja"),
        (None, "ja", "all", "ja"), (None, "es-ES", "all", "en"), (None, "", "all", "en"),
        (None, "en-GB", "all", "en"), (None, "dev", "all", "en"),     # "de" で始まるだけでは de にしない
        (None, "de-DE", "ja,en", "en"),                                # ページに無い言語 → en
        (None, "de-DE", "ja,zh", "ja"),                                # en も無い → 先頭
    ]
    langs_all = list(pv.LANGS)
    js = fn + "\nconst C = %s;\nconsole.log(JSON.stringify(C.map(c => pickLang(c[0], c[1], c[2]))));" % json.dumps(
        [[q, n, langs_all if L == "all" else L.split(",")] for q, n, L, _ in cases])
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
    assert out.returncode == 0, out.stderr
    got = json.loads(out.stdout)
    assert got == [c[3] for c in cases], list(zip(cases, got))


# --------------------------------------------------------------------------- 入口ページ
def _inject_anim3d(d, tmp_path, langs):
    """公開件数に依存しない、テスト専用の動く 3-D 展示を 1 本加える。"""
    viewer = tmp_path / "injected_anim3d.html"
    viewer.write_text(
        '<script>const viewer={"langs":%s}; function pickLang() {}</script>'
        % json.dumps(langs),
        encoding="utf-8",
    )
    tr = {lang: "temporary viewer" for lang in d["langs"]}
    d["exhibits"].append({
        "id": "injected_anim3d",
        "category": "anim3d",
        "media_path": str(viewer),
        "motion": True,
        "source_url": "",
        "label": tr,
        "see": tr,
        "num": {lang: "" for lang in d["langs"]},
        "youtube_url": "",
    })
    return d["exhibits"][-1], viewer


def test_entry_page_links_anim3d_with_lang_and_size(tmp_path):
    d = G.load()
    e, path = _inject_anim3d(d, tmp_path, list(pv.LANGS))
    assert e["category"] == "anim3d"
    assert G._viewer_langs(path) == list(pv.LANGS)
    html = path.read_text(encoding="utf-8")
    assert "function pickLang" in html and "http://" not in html and "https://" not in html
    mb = G._viewer_mb(d, e)
    assert len(d["langs"]) == 8
    for l in d["langs"]:
        page = G.build(d, l)
        assert "%s?lang=%s" % (G._media_rel(d, e), l) in page
        assert "%s · %s" % (e["label"][l], mb) in page                # タイルに容量
        assert d["ui"]["kind_anim3d"][l] in page


def test_viewer_lacking_a_language_stops_the_generator(tmp_path):
    d = G.load()
    _inject_anim3d(d, tmp_path, ["ja", "en"])
    bad = G.validate(d)
    assert bad, "言語の欠けたビューアを止めなかった"
    assert any("ビューアに無い言語" in b for b in bad)


def test_entry_pages_build_with_no_public_anim3d():
    d = G.load()
    assert not [e for e in d["exhibits"] if G._is_viewer(d, e)]
    for lang in d["langs"]:
        page = G.build(d, lang)
        assert page.startswith('<div class="vlang" markdown="1">')


def test_committed_table_passes_for_the_sample():
    """見本の作例を実際に走らせ、commit 済みの表で 8 言語がそろう(作例の文字列が変われば落ちる)。"""
    spec = I18N.pick_spec(I18N.capture_specs(I18N.example_script("interactive_anim3d_viewer")), None)
    problems, unused = I18N.audit(spec, I18N.load_table("interactive_anim3d_viewer"))
    assert problems == [] and unused == []
