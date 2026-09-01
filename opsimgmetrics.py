# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsimgmetrics —— **2 枚の絵の差を測る** op の統一レジストリ。

実体は :mod:`imgmetrics`。ここは台帳(入出力の型、カテゴリ、答え合わせの
出所)だけを持つ。

## この台帳が他と違うところ ―― **外部基準の欄がある**

fullseye の op は大半が「変換する」op で、正しさは自分で作った参照実装か
閉じた形の解析解で確かめる。この族は違い、**外から検証できる op が混ざって
いる**。どの op がどの基準で裏が取れているかを ``VERIFIED_AGAINST`` に明示
してある ―― 「テストが通る」と「外部の基準と合う」は別のことなので。

============================  ==========================================
op                            答え合わせの出所
============================  ==========================================
``delta_e_2000``              Sharma, Wu & Dalal (2005) の公開検証表 34 組
                              (実測: 最大誤差 4.95e-05、表は小数 4 桁)
``ssim``                      scikit-image の独立実装(実測: 差 **0.0**)
``mutual_information``        恒等式 ``I(X;X) = H(X)``(実測: 誤差 <1e-12)
``psnr`` / ``mse``            閉じた形(一定差 0.1・幅 1.0 で厳密に 20 dB)
``rgb_to_lab``                白色点の定義(白 → L*=100、実測 100.0000039)
============================  ==========================================

## 型を新しく 2 つ作った理由

**混ぜると例外にならず、もっともらしく間違った数値が出るか**が判断基準
(この repo の分割規準)。

* ``lab`` を ``rgbimage`` と分けた。どちらも ``(..., 3)`` の float 配列で、
  ``delta_e_2000`` に sRGB を直接渡しても**例外は出ない** ―― L* を 0-1 の
  スケールで読むので、ΔE00 が 2 桁小さい「小さな色差」として静かに出る。
  形も dtype も同じなので述語でしか分けられない(``lab`` は L* が 0-100)。
* ``metrics`` を ``table`` と分けた。``compare_images`` は数値と**条件**
  (``contract``)を一緒に返す辞書で、条件を落とすと数値の意味が変わる。
  ``table`` 扱いで数値だけ抜く消費 op に流すと、``data_range`` が違う 2 回の
  測定が同じ表に並ぶ ―― これも例外にならない。

``scalar`` / ``image2d`` / ``rgbimage`` は既存語彙をそのまま使う。

## 既存 op との関係(再実装していないもの)

* **sRGB の伝達関数**は ``gfx2d.srgb_to_linear`` / ``linear_to_srgb`` が実体。
  ``imgmetrics`` 側は形を合わせて委譲するだけ(実測で両者は ``[0,1]`` の
  257 点で最大差 0.0 だったので、重複実装を削除して委譲に置き換えた)。
* **1 枚のエントロピー**は ``entropy_gray`` / ``entropy_image``(backends)が
  既にある。``image_entropy`` は**同時分布と整合する側**で、ビン割りが違う
  ので値は一致しない ―― ``mutual_information`` と足し引きできるのはこちら。
* **形の距離**は ``hausdorff_distance``(既存)。画素値の距離がこちら。

使い方::

    import opsimgmetrics
    opsimgmetrics.list_ops("fidelity")
    opsimgmetrics.call("psnr", a, b, data_range=1.0)
    opsimgmetrics.verified_against("delta_e_2000")
"""
import imgmetrics

_MOD = {"imgmetrics": imgmetrics}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 色空間。lab が新語(rgbimage と混ぜても例外にならないため分けた)
    "colorspace": [
        ("rgb_to_lab", "imgmetrics", ["rgbimage"], "lab"),
        ("lab_to_rgb", "imgmetrics", ["lab"], "rgbimage"),
        ("rgb_to_xyz", "imgmetrics", ["rgbimage"], "rgbimage"),
        ("xyz_to_lab", "imgmetrics", ["rgbimage"], "lab"),
    ],
    # 色差。delta_e_map だけが画像入口(他は lab 入口)
    "colordiff": [
        ("delta_e_2000", "imgmetrics", ["lab", "lab"], "image2d"),
        ("delta_e_76", "imgmetrics", ["lab", "lab"], "image2d"),
        ("delta_e_map", "imgmetrics", ["rgbimage", "rgbimage"], "image2d"),
    ],
    # 忠実度。スカラを返すものと、マップを返すもの
    "fidelity": [
        ("mse", "imgmetrics", ["image2d", "image2d"], "scalar"),
        ("rmse", "imgmetrics", ["image2d", "image2d"], "scalar"),
        ("psnr", "imgmetrics", ["image2d", "image2d"], "scalar"),
        ("ssim", "imgmetrics", ["image2d", "image2d"], "scalar"),
        ("ms_ssim", "imgmetrics", ["image2d", "image2d"], "scalar"),
        ("ssim_map", "imgmetrics", ["image2d", "image2d"], "image2d"),
    ],
    # 情報量。すべて同じビン割りで整合する
    "information": [
        ("image_entropy", "imgmetrics", ["image2d"], "scalar"),
        ("joint_entropy", "imgmetrics", ["image2d", "image2d"], "scalar"),
        ("mutual_information", "imgmetrics", ["image2d", "image2d"], "scalar"),
        ("normalized_mutual_information", "imgmetrics", ["image2d", "image2d"], "scalar"),
        ("joint_histogram", "imgmetrics", ["image2d", "image2d"], "image2d"),
    ],
    # 圧縮距離。画像コーデックは使わない(その実装の癖を測ってしまう)
    "compression": [
        ("compressed_size", "imgmetrics", ["image2d"], "scalar"),
        ("ncd", "imgmetrics", ["image2d", "image2d"], "scalar"),
    ],
    # まとめ。metrics が新語(数値と条件を一緒に持つ)
    "report": [
        ("compare_images", "imgmetrics", ["image2d", "image2d"], "metrics"),
        ("data_range_of", "imgmetrics", ["image2d"], "scalar"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            reg[name] = {
                "category": cat,
                "module": mod,
                "in": list(ins),
                "out": out,
                "func": getattr(_MOD[mod], name, None),
            }
    return reg


OPSIMGMETRICS = _build()


#: **外部の基準で裏が取れている op** と、その出所・実測値。
#: 「テストが通る」と「外部と合う」は別のことなので分けて持つ。
VERIFIED_AGAINST = {
    "delta_e_2000": {
        "source": "Sharma, Wu & Dalal, Color Res. Appl. 30(1):21-30, 2005 の検証表 34 組",
        "kind": "published reference table",
        "measured": "34/34 一致、最大誤差 4.95e-05(表は小数 4 桁)",
    },
    "ssim": {
        "source": "scikit-image の独立実装(gaussian_weights, sigma=1.5, 母分散)",
        "kind": "independent implementation",
        "measured": "0.98535447 対 0.98535447、差 0.0",
    },
    "mutual_information": {
        "source": "恒等式 I(X; X) = H(X)",
        "kind": "analytic identity",
        "measured": "誤差 < 1e-12",
    },
    "psnr": {
        "source": "閉じた形 10*log10(range^2 / mse)",
        "kind": "closed form",
        "measured": "一定差 0.1・幅 1.0 で厳密に 20 dB",
    },
    "rgb_to_lab": {
        "source": "CIE 1976 L*a*b* と D65 白色点の定義",
        "kind": "definition",
        "measured": "白 → L* = 100.0000039(公表定数どうしの 7 桁目の不一致ぶん)",
    },
}

#: **推測せず明示を要求する引数**。ここが本族の中心的な設計判断で、
#: chain fuzz が既定値で埋めて回すと意味が変わってしまう場所。
REQUIRES_EXPLICIT = {
    "data_range": (
        "float 画像で [0,1] に収まらないものは推測しない。255 と決めつけると "
        "PSNR が 20*log10(255) = 48.13 dB ずれるが例外は出ない"
    ),
    "bins": "相互情報量はビン数に依存して上振れする(既定 64 を明示引数にしてある)",
    "crop_border": "SSIM は縁を落とすかどうかで値が変わる(既定 True)",
    "weights": "MS-SSIM は段数が違うと別の指標。足りない絵で黙って段を減らさない",
}

#: 新設した型と、それを既存語彙と混ぜたときに**例外でなく何が起きるか**。
NEW_SORTS = {
    "lab": "rgbimage と形も dtype も同じ。sRGB を渡すと ΔE00 が 2 桁小さく静かに出る",
    "metrics": "table と混ぜると contract(data_range 等)が落ち、条件の違う測定が同じ表に並ぶ",
}


def list_ops(category=None):
    """op 名の一覧(カテゴリ指定可)。"""
    if category is None:
        return sorted(OPSIMGMETRICS)
    return sorted(n for n, m in OPSIMGMETRICS.items() if m["category"] == category)


def categories():
    """カテゴリ一覧。"""
    return sorted({m["category"] for m in OPSIMGMETRICS.values()})


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSIMGMETRICS[name]["func"]


def call(name, *args, **kwargs):
    """op を実行する。"""
    return OPSIMGMETRICS[name]["func"](*args, **kwargs)


def info(name):
    """op のメタ情報。"""
    return OPSIMGMETRICS[name]


def missing():
    """台帳にあるが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSIMGMETRICS.items() if m["func"] is None]


def verified_against(name=None):
    """外部基準で裏が取れている op の出所と実測値。"""
    return VERIFIED_AGAINST if name is None else VERIFIED_AGAINST.get(name)


if __name__ == "__main__":     # pragma: no cover - 手元確認用
    print(f"opsimgmetrics: {len(OPSIMGMETRICS)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    print(f"外部基準で裏が取れている op: {len(VERIFIED_AGAINST)} / {len(OPSIMGMETRICS)}")
    for n, v in VERIFIED_AGAINST.items():
        print(f"  {n:22s} {v['kind']:26s} {v['measured']}")
