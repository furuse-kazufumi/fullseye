# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsaoi —— 自動外観検査(AOI)の前段 op の統一レジストリ。

実体は ``aoi.py``(3 op / 3 カテゴリ。numpy のみ)。

## なぜ足したか(2026-09-15)

この repo は「測る」層を深く持っている(``measure1d`` のサブピクセル計測、``blob2d`` の
連結成分、``shapestats`` の形態統計、``spc`` の管理図)。ところが検査ラインで**その手前に
必ず入る 3 段**が、公開層の 4 つ(``fullseye.<名前>`` / ``fullseye.op.<名前>`` /
``fullseye.ledger.<名前>`` / ``fullseye.op_find``)のどこにも無かった:

1. **照明の落ちを戻す** —— 近いのは ``background_flatten`` だが、あれは低次曲面の
   **引き算**で、掛け算で効く利得も暗電流も戻せない。
2. **基準画像へ合わせる** —— 画像 2 枚の並進を 1 個返す口が無かった。``frame_align`` は
   星の対応(点状の特徴)が要り、``piv_cross_correlate`` は窓ごとの**場**を返す。
   この穴は ``examples/poc_print_registration.py`` の 9 節が**独立に**、4 層すべてを
   引いた実測つきで報告していた。
3. **タイルごとの量を地図にする** —— ``scale.process_tiled`` と ``vol_tiled_map`` は
   タイルごとに op を掛けて**同じ大きさの出力**を返す道具(記憶量を抑える側)で、
   タイルごとの**量**は返らない。

## 型語彙: **新語を 1 つも作らない**

3 op の入出力は既存の ``image2d`` と ``table`` にそのまま収まる。

* ``image2d`` —— :func:`aoi.flat_field_correct` の入出力。2-D の画像そのもの。
* ``table`` —— :func:`aoi.register_image` と :func:`aoi.tiled_map` の返り。並進・不定性の
  量・残差・タイルの監査をまとめた dict。

``register_image`` が ``shift`` 型(整数 ``(dz, dy, dx)``)を名乗らないのは、あれが 3-D の
可逆な整数シフトのための語で、ここで返すのは**副画素の 2 成分 + 当てになるかどうかの量**
だから。``(shift, info)`` のタプルにもしない —— 台帳の adapter は**タプルの 2 番目以降を
捨てる**ので、``info`` が ``.raw`` 無しには届かなくなる(``piv_cross_correlate`` で実際に
起きた事故。``_LedgerNamespace`` の docstring に経緯がある)。dict 1 つなら、どの経路から
呼んでも量が揃って出る。

**登録面は 6 つ**: この台帳 / ``tools/opdocs.LEDGER_DIMS`` / ``typed_catalog``
(``catalog()`` と ``RESULT_ADAPTERS``)/ ``opassist._LEDGERS`` / ``pyproject`` の
py-modules / ``examples2d.EXAMPLES``(動く例)。

Usage::

    import opsaoi
    opsaoi.list_ops("geometric")
    opsaoi.get("register_image")(ref, mov)
"""
import aoi

_MOD = {"aoi": aoi}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 明るさを直す —— 照明の落ちとセンサの感度ばらつきを割り算で戻す。
    "photometric": [
        ("flat_field_correct", "aoi", ["image2d", "image2d"], "image2d"),
    ],
    # 位置を合わせる —— 平行移動 1 個と、合っていないと分かる量。
    "geometric": [
        ("register_image", "aoi", ["image2d", "image2d"], "table"),
    ],
    # まとめる —— タイルごとの量を小さな地図に(半端なタイルの監査つき)。
    "aggregate": [
        ("tiled_map", "aoi", ["image2d"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = ""
            if fn is not None and fn.__doc__:
                doc = fn.__doc__.strip().splitlines()[0]
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSAOI = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSAOI.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 —— 意図的**。3 op とも宣言型どおりの値を
#: 1 つだけ素で返す(``image2d`` は ndarray、残り 2 つは dict = table)。adapter を
#: 挟まないほうが連鎖ファザーの検証が最も厳しく、``register_image`` が量を
#: 落とさないのは**返りを dict 1 つに設計したから**であって adapter のおかげではない。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSAOI[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSAOI[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSAOI[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSAOI.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsaoi: {len(OPSAOI)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
