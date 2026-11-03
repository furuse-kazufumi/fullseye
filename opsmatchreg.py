# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsmatchreg —— 照合と位置合わせの op の統一レジストリ / matching and registration ledger.

実体は ``featmatch.py``(特徴点と照合と頑健推定、6 op)と ``intensityreg.py``(強度による位置合わせ、
6 op)。numpy + scipy だけ。

## なぜ足したか(2026-11-03)

監査(``completeness_audit_2026_11_03``)で、スケール不変の 2-D 特徴と照合は OpenCV・scikit-image・
kornia の全部にあるのに Fullseye は数を数えるだけ(``xcv_orb_count``)、強度による位置合わせは
ECC・MI 目的のアフィン・B-spline FFD が無いと出た。土台は標準のアルゴリズムで、その上に
**合成の真値による精度の地図**(条件ごとの表・画素ごとの誤差・収束の範囲)を載せる。

## 既存 op との関係

* :mod:`features`(Harris / FAST + 正規化パッチ + 比の検定)—— 並存。``features_orb`` は
  ``features.fast_corners`` を再利用し、``features_match`` の実数の規則は ``features.match_descriptors``
  と同じ(テストで組の一致を固定)。
* ``mosaic.proj_match_points_ransac`` —— 並存((row, col)・正規化なし・固定回数)。``ransac_homography``
  は (x, y)・正規化 DLT(``twoview._homography_dlt`` を再利用)・MSAC・適応回数・LO。貼り合わせは
  既存の ``mosaic.gen_projective_mosaic`` をそのまま使う(H の向きが同じ (x, y))。
* ``reconstruction.match_fundamental_matrix_ransac`` —— 並存。``ransac_fundamental`` は
  ``twoview.fundamental_8point`` を再利用。
* ``aoi.register_image``(位相相関の並進)・``deformreg.demons_register``(demons)—— 精度の地図と
  収束の範囲の比べる相手として ``method="phase"`` / ``"demons"`` で呼ぶ。場の向きは demons と同じ。
* ``imgmetrics.mutual_information`` —— 指標。``register_mi`` の目的関数は振り分けつきの別の推定量。

## 型語彙: **新語を 1 つも作らない**

* ``image2d`` —— 入力の画像。
* ``table`` —— 特徴(``kind="features"``)・照合(``"feature_matches"``)・推定(``"homography"`` /
  ``"fundamental"``)・位置合わせ(``"registration"``)・精度(``"feature_accuracy"`` /
  ``"registration_accuracy"`` / ``"capture_range"``)。``kind`` の違う表は ``ValueError``。
* ``flow2d`` —— 変形場 ``(2, H, W)`` の ``(dy, dx)``(PIV 族の型。``registration_to_flow2d`` の出口と
  ``register_accuracy_map`` の真値の入口)。

**登録面**: この台帳 / ``tools/opdocs.LEDGER_DIMS`` / ``typed_catalog``(``catalog()`` と
``RESULT_ADAPTERS``)/ ``opassist._LEDGERS`` / ``pyproject`` の py-modules / ``examples2d.EXAMPLES``。

Usage::

    import opsmatchreg
    opsmatchreg.list_ops("featmatch")
    opsmatchreg.get("features_sift")(image)
"""
import featmatch
import intensityreg

_MOD = {"featmatch": featmatch, "intensityreg": intensityreg}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 特徴点と照合 —— スケール・回転に強い点と記述子、照合、頑健推定、条件ごとの精度の表。
    "featmatch": [
        ("features_sift", "featmatch", ["image2d"], "table"),
        ("features_orb", "featmatch", ["image2d"], "table"),
        ("features_match", "featmatch", ["table", "table"], "table"),
        ("ransac_homography", "featmatch", ["table"], "table"),
        ("ransac_fundamental", "featmatch", ["table"], "table"),
        ("features_accuracy_table", "featmatch", ["image2d"], "table"),
    ],
    # 強度による位置合わせ —— ECC / MI / B-spline FFD、場の取り出し、精度の地図、収束の範囲。
    "intensityreg": [
        ("register_ecc", "intensityreg", ["image2d", "image2d"], "table"),
        ("register_mi", "intensityreg", ["image2d", "image2d"], "table"),
        ("register_ffd", "intensityreg", ["image2d", "image2d"], "table"),
        ("registration_to_flow2d", "intensityreg", ["table"], "flow2d"),
        ("register_accuracy_map", "intensityreg", ["image2d", "flow2d"], "table"),
        ("register_capture_range", "intensityreg", ["image2d"], "table"),
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


OPSMATCHREG = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSMATCHREG.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 —— 意図的**。12 op とも宣言型どおりの値を 1 つだけ素で返す
#: (table は dict、flow2d は (2, H, W) の ndarray)。量(内れ値・収束・誤差の内訳)は dict の中にある。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSMATCHREG[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSMATCHREG[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSMATCHREG[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSMATCHREG.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsmatchreg: {len(OPSMATCHREG)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
