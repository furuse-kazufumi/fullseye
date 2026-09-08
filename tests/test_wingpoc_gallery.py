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


def test_an_animated_figure_is_embedded_as_the_gif_itself():
    """★動く図を JPEG サムネに落とすと、記事では「クリックしないと動かない絵」になる。

    動きが主題の展示でそれをやると意味が消えるので、``.gif`` はそのまま埋める
    (静止の完成形は同じ展示の別の図として並んでいるので、受け皿はある)。
    2026-09-09、回転の展示を足したときに気づいた。
    """
    import io
    import json
    import os
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "tools"))
    import gen_wingpoc_gallery as G

    assets = os.path.join(root, "docs", "articles", "exhibits")
    cap = json.load(io.open(os.path.join(assets, "poc_captions.json"), encoding="utf-8"))
    animated = []
    for ex in cap["exhibits"]:
        mp = os.path.join(G.ASSETS, ex["id"], "figures.json")
        if not os.path.exists(mp):
            continue
        for fig in json.load(io.open(mp, encoding="utf-8")):
            if fig.get("animated"):
                animated.append((ex["id"], fig["file"]))
    assert animated, "動く図が 1 つも無い(この門は空を通している)"

    # サムネ関数は .gif をそのまま返す
    for poc_id, name in animated:
        assert G._thumb(poc_id, name) == name, (poc_id, name)

    # 記事にも .gif として埋まっている(JPEG に化けていない)
    for lang in ("ja", "en"):
        text = io.open(os.path.join(root, "docs", "articles",
                                    "fullseye_poc_museum_qiita_%s.md" % lang),
                       encoding="utf-8").read()
        for poc_id, name in animated:
            stem = os.path.splitext(name)[0]
            assert "![" in text and name in text, (lang, poc_id, name)
            assert stem + "_720.jpg" not in text, (lang, poc_id, "GIF が JPEG に化けている")
