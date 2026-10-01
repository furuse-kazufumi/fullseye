# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsvx — OpenVX 1.3.1 が「渡せ」「返せ」と言う素の口の台帳(第 1 陣 6 op)。

Motivation (2026-09-25 の照合、2026-10-01 着手): OpenVX 1.3.1 の視覚関数 61 本を本文まで読んで照合したら、17 件は
「対応はあるが入口か出口の形が違う」だった。合成 op(``sobel_mag`` / ``nonmax_suppression_amp`` / ``f2_lut_trans``)は
引数 ``(v, a, b)`` で出力を [0, 1] に正規化する進化用で、規格の順序(gx と gy を別々に受ける・任意の表を引く・規格どおりに
隣を比べる)では使えない。この台帳はその素の口を、規範文 [REQ-NNNN] をそのまま門にして足す。合成 op は消さない。

Type vocabulary: **no new word**. 画像は ``image2d``(U8 / S16 の dtype は呼び出し時に検査して止める —— 黙って丸めない)。
``vx_sobel3x3`` は gx・gy と有効領域を ``table`` で返す。大きさ・位相・表引き・非極大の抑制は ``image2d``、
ヒストグラムは ``pairs``(升の下端, 数)。表引きの表は ``signal``(1-D)。

Usage:
    import opsvx
    opsvx.list_ops("gradient")
    opsvx.get("vx_sobel3x3")(u8, border="replicate")["gx"]
"""
import vxcore

_MOD = {"vxcore": vxcore}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 3.46 Sobel 3x3 / 3.31 Magnitude / 3.41 Phase。gx と gy を別々に運ぶ(REQ-0415・0270・0364)。
    "gradient": [
        ("vx_sobel3x3", "vxcore", ["image2d"], "table"),
        ("vx_magnitude", "vxcore", ["image2d", "image2d"], "image2d"),
        ("vx_phase", "vxcore", ["image2d", "image2d"], "image2d"),
    ],
    # 3.47 TableLookup / 3.26 Histogram(REQ-0421・0422・0230)。
    "pixel": [
        ("vx_table_lookup", "vxcore", ["image2d", "signal"], "image2d"),
        ("vx_histogram", "vxcore", ["image2d"], "pairs"),
    ],
    # 3.39 Non-Maxima Suppression(REQ-0334〜0337)。前の隣には ≥、後ろの隣には >。
    "suppress": [
        ("vx_nonmax_suppression", "vxcore", ["image2d"], "image2d"),
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


OPSVX = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSVX.items() if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。空 — 全 op が dict(= table)を素で返す。
ADAPTERS = {}


def get(name):
    """op 名から関数を引く(無ければ KeyError)。"""
    return OPSVX[name]["func"]


def info(name):
    """op の登録情報(category / in / out / doc)。"""
    m = OPSVX[name]
    return {k: m[k] for k in ("category", "module", "in", "out", "doc")}


def call(name, *args, **kwargs):
    """登録名で呼ぶ。"""
    return get(name)(*args, **kwargs)


def missing():
    """台帳に在るが実体が無い op(ゼロであることを試験が確かめる)。"""
    return [n for n, m in OPSVX.items() if m["func"] is None]
