# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC 展示館の記事(tools/gen_wingpoc_gallery.py)が腐らないための門。

* 生成物(翼 md × 2、記事 md × 2)が commit 済みの正本(poc_captions.json + 各 PoC の
  figures.json)と一致する(``--check`` 相当)。
* 記事が参照する画像が全部 repo にある(raw URL が 404 になる形で公開しない)。
* ローカルパス・赤緑マーカーが混ざらない。
* 展示の数が examples2d の poc_* と一致する(PoC を足したのに展示に無い、を止める)。
"""
from __future__ import annotations

import io
import os
import re
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "tools"))
sys.path.insert(0, _ROOT)

import gen_wingpoc_gallery as G   # noqa: E402


@pytest.fixture(scope="module")
def cap():
    return G._load()


def test_generated_articles_are_up_to_date(cap):
    c, byid = cap
    for lang in ("ja", "en"):
        wing_md, art_md = G.build(lang, c, byid)
        for path, text in ((G.OUT_WING[lang], wing_md), (G.OUT_ARTICLE[lang], art_md)):
            assert os.path.exists(path), path
            cur = io.open(path, encoding="utf-8").read()
            assert cur == text, ("%s が古い —— py -3.11 tools/gen_wingpoc_gallery.py" % os.path.basename(path))


def test_every_referenced_asset_exists():
    pat = re.compile(re.escape(G.RAW) + r"([A-Za-z0-9_./-]+)")
    for lang in ("ja", "en"):
        text = io.open(G.OUT_ARTICLE[lang], encoding="utf-8").read()
        missing = sorted({m for m in pat.findall(text)
                          if not os.path.exists(os.path.join(G.ASSETS, m.replace("/", os.sep)))})
        assert not missing, missing[:10]


def test_no_local_paths_or_traffic_lights():
    for lang in ("ja", "en"):
        text = io.open(G.OUT_ARTICLE[lang], encoding="utf-8").read()
        assert not G._LOCAL.search(text)
        assert "🔴" not in text and "🟢" not in text


def test_exhibit_set_matches_poc_examples(cap):
    c, byid = cap
    pocs = sorted(k for k in byid if k.startswith("poc_"))
    shown = sorted(e["id"] for e in c["exhibits"])
    assert shown == pocs, ("展示に無い PoC / PoC に無い展示: %s"
                           % sorted(set(pocs) ^ set(shown)))
