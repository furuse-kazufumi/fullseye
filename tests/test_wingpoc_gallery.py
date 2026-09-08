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


def test_every_poc_file_is_registered():
    """★**ファイル**の側から数える(2026-09-08)。

    それまでこの門の鎖は「登録 (`examples2d.EXAMPLES`) ↔ 展示
    (`poc_captions.json`)」だけで閉じていて、**`examples/poc_*.py` を置いた
    だけで登録しなかった PoC には誰も気づかなかった**。`test_poc_scripts_run`
    は glob で拾うので走りはするが、索引・図の配線・展示館・記事のどれにも
    出てこない —— 「配布はされているのに公開経路がゼロ」と同じ形が、
    例の側で起きる。実測: この門を足した時点で `poc_rail_corrugation` と
    `poc_web_roll_periodicity` の 2 本が未登録のまま走っていた。
    """
    import examples2d as E
    reg = {e["id"] for e in E.EXAMPLES if e["id"].startswith("poc_")}
    files = {os.path.splitext(f)[0]
             for f in os.listdir(os.path.join(_ROOT, "examples"))
             if f.startswith("poc_") and f.endswith(".py")}
    assert files == reg, ("登録の無い PoC ファイル / ファイルの無い登録: %s"
                          % sorted(files ^ reg))
