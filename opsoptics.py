# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsoptics — fullseye 光学 op の統一レジストリ(optics を一望・発見可能に)。

ユーザー方針(2026-09-01)「光学系で使うような演算 op が充実するといいな」。
fullseye は産業ビジョン(検査ライン)と Physical AI(ロボット知覚)の両方に
足場があり、その**手前**にあるのがレンズ・回折・偏光の計算 — 「どの焦点距離
か」「被写界深度はどれだけか」「回折で潰れる最小欠陥は何 µm か」「偏光板で
テカりは消えるか」。本レジストリはその台帳(optics.py、18 op / 4 カテゴリ)。

既存資産との棲み分け(**再実装せず import して合成**):
  * 光線と面の相互作用 = match3d(``reflect`` / ``refract`` (Snell) /
    ``snell_angle`` / ``fresnel_reflectance`` / ``normal_from_reflection``)。
    optics は近軸・スカラ。実際に面で曲がる光線が要るならそちら。
  * Zernike **フィット** = ``match3d.fit_zernike``。``wavefront_stats`` は
    その返り dict をそのまま食い、**match3d 自身の基底ビルダーを再利用**する
    ので規約がずれない(フィットは match3d、統計は optics)。
  * PSF ぼけ・逆畳み込み = volrestore(``vol_gaussian_psf`` /
    ``vol_richardson_lucy``)と complexops(``cx_wiener_deconvolve``)。
    ``psf_to_mtf`` は PSF を**特性化**するだけで復元はしない。
  * FFT / complex 画像 = complexops(``cx_fft`` 系・``phase_unwrap``)。
  * 位相シフト干渉法・縞投影 = fringe(``wrapped_phase`` が一般 N-step、
    ``unwrap_phase_2d`` / ``phase_to_height``)。4-step PSI をここに置くのは
    重複なので**置かない**。

使い方:
    import opsoptics
    opsoptics.list_ops("polarization")
    opsoptics.get("thin_lens")(focal_mm=50.0, object_mm=200.0)
"""
import optics

_MOD = {"optics": optics}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: image2d / signal / matrix / measurement(実スカラのみ)/
#   table(dict or list)/ pairs((n,2) 配列)/ cimage(2-D complex)/ vector
#
# 既存語彙をそのまま使った判断(新語を作らなかったもの):
#   * matrix   — ABCD(2x2 実)と Mueller(4x4 実)は**まさに行列**で、
#     mat_svd / mat_cond / stat_covariance にそのまま流せる。専用語を作ると
#     数学ファミリとの接続を切るだけで得が無い。
#   * cimage   — Jones 行列(2x2 complex)。complexops が既に使っている
#     「2-D complex 配列」語彙で、cx_magnitude / cx_phase がそのまま Jones
#     行列の振幅・位相を見せる(型として嘘が無い: 実際に 2-D complex)。
#   * table    — ABCD の素子リスト((kind, *params) の列)は list、返りの
#     計測値束は dict。TYPE_CHECKS の table は list|dict なのでどちらも該当。
#   * pairs    — (n,2) の (x, y) 配列(funct1d / dsp.spectrum と同じ規約)。
#     MTF 曲線・cos^4 曲線はまさにこれ。
#
# 新語彙 2 つと、その理由(**既存では型レベルの嘘になる**もののみ追加。
# 先例 = opsmath の cpoints / cscalar):
#   * jones  — Jones ベクトル: **長さ 2 固定**の complex 1-D (Ex, Ey)。
#     opsmath の ``cpoints`` は「複素平面上の順序つき点列(閉曲線)」で、
#     周回積分・巻き数は**点の順序と閉性**が答えそのもの。Jones ベクトルは
#     曲線ではなく 2 成分の場の振幅なので、cpoints を食える型として宣言すると
#     「64 点の輪郭を渡しても良い」という嘘になる(実際は常に ValueError)。
#     ``vector`` は (3,) 実ベクトル固定なので不可。
#   * stokes — Stokes ベクトル: **長さ 4 固定**の実 1-D (S0,S1,S2,S3) で、
#     さらに ``S0 >= sqrt(S1²+S2²+S3²)``(偏光度 <= 1)という**物理的実現
#     可能性**の制約を持つ。``signal`` は「1-D の標本化された関数」で長さも
#     意味も自由 — 256 点の正弦波を Stokes 枠に渡せると宣言するのは嘘で、
#     連鎖ファザーでも常に CONTRACT にしかならず偏光ファミリを一切通らない。
_CATALOG = {
    "geometric": [
        ("thin_lens", "optics", [], "table"),
        ("abcd_matrix", "optics", ["table"], "matrix"),
        ("abcd_trace", "optics", ["matrix"], "table"),
        ("depth_of_field", "optics", [], "table"),
        ("relative_illumination", "optics", [], "pairs"),
    ],
    "wave": [
        ("airy_pattern", "optics", [], "image2d"),
        ("angular_spectrum_propagate", "optics", ["cimage"], "cimage"),
        ("fraunhofer_pattern", "optics", ["image2d"], "image2d"),
        ("gaussian_beam", "optics", [], "table"),
    ],
    "imaging": [
        ("psf_to_mtf", "optics", ["image2d"], "pairs"),
        ("mtf_diffraction", "optics", [], "pairs"),
        ("wavefront_stats", "optics", ["table"], "table"),
    ],
    "polarization": [
        ("jones_element", "optics", [], "cimage"),
        ("jones_apply", "optics", ["cimage", "jones"], "jones"),
        ("stokes_from_jones", "optics", ["jones"], "stokes"),
        ("mueller_element", "optics", [], "matrix"),
        ("mueller_apply", "optics", ["matrix", "stokes"], "stokes"),
        ("stokes_analyze", "optics", ["stokes"], "table"),
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


OPSOPTICS = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSOPTICS.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath と同じ一級機構)。
#:
#: **現在は空 — 意図的に**。opsmath では ``mat_svd`` が数学慣習の
#: ``U, s, Vt = ...`` タプルを返すため adapter が要ったが、optics の 18 op は
#: すべて宣言型そのもの(dict / (n,2) 配列 / ndarray)を素で返す設計にしてある。
#: 空にしておくと :func:`call` は :func:`get` と同じ値を返し、連鎖ファザーの
#: TYPEMISS 検査が**素の返りをそのまま**宣言と突き合わせる = 検証が最も厳しい。
#: タプル返しの op を将来足すならここに登録すること(空欄を埋めるために既存の
#: 返り型をタプルへ変える、は本末転倒なのでしない)。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSOPTICS[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSOPTICS[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSOPTICS[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSOPTICS.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsoptics: {len(OPSOPTICS)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
