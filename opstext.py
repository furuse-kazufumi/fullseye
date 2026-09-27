# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opstext — fullseye text-region op registry (where is the text, without a recogniser).

Motivation (2026-09-27): fullseye stopped at OCR pre-processing (deskew, binarise,
components) and had no layer that answers "where is the text". Recognisers (trained
models) stay out of scope by design; the geometry of text — a stroke has a nearly
constant width — is enough for a classical detector (Epshtein, Ofek & Wexler 2010).

Type vocabulary: **no new word**. ``swt_map`` eats an ``image2d`` and returns a ``table``
(the width map plus counts); ``text_candidates`` eats the width map (a ``matrix``) and returns
a ``table`` of boxes; ``text_lines`` eats a ``table`` and returns a ``table``. (The chain-fuzz
gate named the first draft's ``image`` as a type nobody produces — the vocabulary is
``image2d`` / ``matrix``, 2026-09-27.)

Usage:
    import opstext
    opstext.list_ops("detect")
    opstext.get("swt_map")(gray)["swt"]
"""
import textregion

_MOD = {"textregion": textregion}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # ストローク幅そのもの。真値 = 矩形ストロークで幅が厳密な整数。
    "stroke": [
        ("swt_map", "textregion", ["image2d"], "table"),
    ],
    # 幅の一定な成分を文字候補に。規則は Epshtein 2010 §4(分散・縦横比・大きさ)。
    "detect": [
        ("text_candidates", "textregion", ["matrix"], "table"),
    ],
    # 候補を行にまとめる(高さ・隙間・ストローク幅が近いもの)。
    "layout": [
        ("text_lines", "textregion", ["table"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = fn.__doc__.strip().splitlines()[0] if fn is not None and fn.__doc__ else ""
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSTEXT = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSTEXT.items() if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。空 — 全 op が dict(= table)を素で返す。
ADAPTERS = {}


def get(name):
    """op 名から関数を引く(無ければ KeyError)。"""
    return OPSTEXT[name]["func"]


def info(name):
    """op の登録情報(category / in / out / doc)。"""
    m = OPSTEXT[name]
    return {k: m[k] for k in ("category", "module", "in", "out", "doc")}


def call(name, *args, **kwargs):
    """登録名で呼ぶ。"""
    return get(name)(*args, **kwargs)


def missing():
    """台帳に在るが実体が無い op(ゼロであることを試験が確かめる)。"""
    return [n for n, m in OPSTEXT.items() if m["func"] is None]
