# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""投稿器(tools/qiita_post_poc.py)の記事選びが事故らないための門。

★事故の形は「更新したつもりが、同じ記事をもう 1 本作る」。投稿器は台帳
``qiita_items.json`` に鍵が無ければ **POST**(新規)に回るので、手書きの記事を
既定の一括投稿に混ぜると、走らせるたびに重複が増える —— 例外は出ない。

見ているもの:

* 引数無しの一括投稿に **手書きの記事(``external``)が入らない**。
* 名指しすれば入り、その原稿が実在する。
* 手書きの記事は **投稿済みとして台帳に登録されている**(登録が無い = 次の実行で
  新規作成される、という意味なので、登録そのものを門にする)。
"""
from __future__ import annotations

import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "tools"))

import qiita_post_poc as Q   # noqa: E402

_EX = os.path.join(_ROOT, "docs", "articles", "exhibits")


def _cap():
    with open(os.path.join(_EX, "poc_captions.json"), encoding="utf-8") as f:
        return json.load(f)


def _items():
    with open(os.path.join(_EX, "qiita_items.json"), encoding="utf-8") as f:
        return json.load(f)


def _assert_no_hand_written(parts):
    """既定の一括投稿に手書きの記事が混ざっていないこと(門の本体)。"""
    bad = [p["id"] for p in parts if p["kind"] == "external"]
    assert not bad, (
        "引数無しの投稿に手書きの記事が入っている: %s —— 台帳に鍵が無ければ "
        "POST に回るので、走らせるたびに同じ記事が増える" % ", ".join(bad))


def test_the_default_run_never_touches_a_hand_written_article():
    _assert_no_hand_written(Q._parts(_cap()))


def test_the_hand_written_guard_catches_a_widened_default():
    """★門を壊して確かめる —— 既定に ``external`` を混ぜたら落ちること。"""
    with pytest.raises(AssertionError) as e:
        _assert_no_hand_written(Q._parts(_cap(), kinds=Q.DEFAULT_KINDS + ("external",)))
    assert "lane_math_article" in str(e.value)


def test_naming_a_hand_written_article_reaches_its_manuscript():
    parts = Q._parts(_cap(), kinds=Q.DEFAULT_KINDS + ("external",))
    ext = [p for p in parts if p["kind"] == "external"]
    assert ext, "手書きの記事が 1 本も無い(この門は何も見ていない)"
    for p in ext:
        for lang in ("ja", "en"):
            path = Q._body_path(p, lang)
            assert os.path.exists(path), "%s の原稿が無い: %s" % (p["id"], path)


def test_a_hand_written_article_is_recorded_as_already_posted():
    items = _items()
    parts = Q._parts(_cap(), kinds=Q.DEFAULT_KINDS + ("external",))
    for p in (x for x in parts if x["kind"] == "external"):
        for lang in ("ja", "en"):
            slot = Q._slot(p, lang)
            assert slot in items, (
                "%s が台帳に無い —— この状態で投稿すると新しい記事が作られる "
                "(既存の記事を更新したいなら id を先に登録すること)" % slot)
            assert items[slot].get("id"), "%s に記事 id が無い" % slot
