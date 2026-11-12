# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_pyedit_i18n — Python エディタ部品(色分け・補完・変数・ウォッチ)の画面の文の対訳(Qt なし)。

対訳は ``studio_assets/studio_pyedit_i18n.json``(英語を正とし、en 以外の 5 言語 ja・zh・tw・ko・de を持つ)。
部品は ``tr`` という「英語の文 → 今の言語の文」の関数を受け取って呼ぶ。Studio へ繋ぐときは

    * そのまま ``studio.tr`` を渡す(下の ``merge_into`` で i18n.json の 'strings' へ移した後)、または
    * ``make_tr("ja")`` の戻り値を渡す(単体で動かすとき)。

表に無い文・未訳の言語は**英語のまま**返す(壊れた訳より原文。Studio の ``tr`` と同じ)。
"""
from __future__ import annotations

import json
import os
from typing import Callable

#: 対訳を持つ言語(en は原文なので表には持たない)。
LANGS = ("en", "ja", "zh", "tw", "ko", "de")
_TABLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studio_assets", "studio_pyedit_i18n.json")
_CACHE: dict = {}


def load_table(path: str | None = None) -> dict:
    """対訳の表 ``{英語の文: {言語: 訳}}``。読めない・壊れていれば ``ValueError``(黙って空にしない)。"""
    path = path or _TABLE_PATH
    if path in _CACHE:
        return _CACHE[path]
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError("対訳の表を読めません: %s (%s)" % (path, exc)) from exc
    strings = data.get("strings") if isinstance(data, dict) else None
    if not isinstance(strings, dict):
        raise ValueError("対訳の表に 'strings' がありません: %s" % path)
    _CACHE[path] = strings
    return strings


def make_tr(lang: str = "en", table: dict | None = None) -> Callable[[str], str]:
    """言語 ``lang`` の ``tr`` を作る。知らない言語は ``ValueError``。"""
    if lang not in LANGS:
        raise ValueError("言語は %s のどれか(来たのは %r)" % (" / ".join(LANGS), lang))
    tab = load_table() if table is None else table

    def tr(text: str) -> str:
        if lang == "en" or not text:
            return text
        return tab.get(text, {}).get(lang, text)

    tr.lang = lang
    return tr


def identity_tr(text: str) -> str:
    """翻訳しない ``tr``(既定)。"""
    return text


def missing(table: dict | None = None) -> list:
    """``[(英語の文, 足りない言語)]``。全部そろっていれば空。"""
    tab = load_table() if table is None else table
    out = []
    for key, row in tab.items():
        for lang in LANGS[1:]:
            if not isinstance(row, dict) or not str(row.get(lang, "")).strip():
                out.append((key, lang))
    return out


def merge_into(i18n_data: dict, table: dict | None = None) -> dict:
    """Studio の ``i18n.json``(読み込んだ dict)の ``'strings'`` へ、この表を足した新しい dict を返す。

    既にある文は上書きしない(Studio 側の訳を優先)。``studio_assets/i18n.json`` を直接書き換えるのは繋ぐ人の仕事。
    """
    tab = load_table() if table is None else table
    out = dict(i18n_data)
    strings = dict(out.get("strings", {}))
    for key, row in tab.items():
        strings.setdefault(key, dict(row))
    out["strings"] = strings
    return out
