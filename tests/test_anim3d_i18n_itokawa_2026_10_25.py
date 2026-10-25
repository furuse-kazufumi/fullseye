# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""小惑星イトカワの重力の動く 3-D の 8 言語版(ViEW2026、2026-10-25)の門。

``docs/anim3d/itokawa_gravity.html`` は生成器 ``tools/build_itokawa_anim3d.py`` を翻訳の層 ``tools/anim3d_i18n.py`` で
走らせて書く(``py -3.11 tools/anim3d_i18n.py --build build_itokawa_anim3d --out docs/anim3d/itokawa_gravity.html``)。
ここでは (1) commit 済みの翻訳表が今の生成器の文字列と合う(未訳・古い訳・数値/op 名の不一致 0、使われない訳 0)、
(2) commit 済みのページがその表で作った 8 言語版とバイト一致する(生成器か表を変えて作り直し忘れたら落ちる)、
(3) 訳に ``**`` と外部 URL が無い —— を確かめる。

(2) の比べ方: ページは 2.5 MB なので ``assert html == want`` にしない(pytest の assertion rewriting が 2 本の
文字列を difflib に通し、CI で 10 分の timeout に当たった —— 2026-10-25 の run 40215975176)。共通の門
``anim3d_i18n.check_same_page`` が SHA-256 を先に比べ、違えば最初に違うバイトの位置・両側の前後 200 文字・
違う行の数を短い文にして、作り直したページを一時フォルダに書いてそのパスも出す。
"""
from __future__ import annotations

import importlib.util
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER = "build_itokawa_anim3d"
PAGE = os.path.join(ROOT, "docs", "anim3d", "itokawa_gravity.html")


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_itokawa_t", os.path.join(ROOT, "tools", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


I18N = _load("anim3d_i18n")
PLATEAU_URL = "https://www.geospatial.jp/ckan/dataset/plateau-14100-yokohama-city-2020"


@pytest.fixture(scope="module")
def spec_and_table():
    spec = I18N.pick_spec(I18N.capture_specs(I18N.example_script(BUILDER)), None)
    return spec, I18N.load_table(BUILDER)


def test_committed_table_passes(spec_and_table):
    spec, table = spec_and_table
    n = len({d["en"] for _, d in I18N.iter_texts(spec)})
    assert n > 50, "文字列が %d 本しか見つからない(横取りが壊れていないか)" % n
    problems, unused = I18N.audit(spec, table)
    assert problems == [], problems[:5]
    assert unused == [], unused[:5]


def test_translations_have_no_bold_marks_or_urls(spec_and_table):
    _, table = spec_and_table
    assert len(table["strings"]) > 50
    for en, tr in table["strings"].items():
        for lang in I18N.NEW_LANGS:
            v = tr[lang]
            assert "**" not in v, (en, lang)
            # PLATEAU の出典表示の例に含まれる データセットの URL だけは許す(ライセンスの表示が優先)。他は禁止。
            v2 = v.replace(PLATEAU_URL, "")
            assert not re.search(r"https?://|www\.", v2), (en, lang)


def test_committed_page_is_the_eight_language_build(spec_and_table):
    spec, table = spec_and_table
    with open(PAGE, encoding="utf-8") as f:
        html = f.read()
    data = json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))
    assert data["langs"] == list(I18N.LANGS)
    assert "function pickLang" in html, "ブラウザの言語で開く(detect_lang)になっていない"
    want = I18N.pv._build_html(I18N.translate(spec, table), list(I18N.LANGS), detect_lang=True)
    I18N.check_same_page(html, want, PAGE, BUILDER)
