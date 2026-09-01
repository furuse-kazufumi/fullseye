# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsmath — fullseye 数学 op の統一レジストリ(mathops を一望・発見可能に)。

ユーザー方針(2026-08-31)「数学系 op を Fullseye の op として充実させたい。
数学辞典に載る問題を全て扱えるくらいの op 量を目指す」。本レジストリはその
台帳 — 第一陣は視覚計測を支える 3 分野 16 op(mathops.py、数学系 RAD コーパス
4 分野で選定を裏取り)。FFT/複素画像は complexops・volfreq・dsp に、1D 関数は
funct1d に既存で、ここでは重複させない。

拡張ロードマップ(tier、docs/NEXT_OPS_PLAN_2026-08-31.md §F が正本):
  tier1 線形代数/統計/補間・多項式(済 16op)→ tier2 複素解析の計算可能な
  切り口(済 10op: 周回積分・Cauchy 積分公式・偏角の原理・Laurent 係数/留数・
  Joukowski/Möbius 等角写像・Cauchy-Riemann 残差)→ tier3 最適化/特殊関数 → …

使い方:
    import opsmath
    opsmath.list_ops("linalg")
    opsmath.get("mat_svd")(...)
"""
import numpy as np

import mathops

_MOD = {"mathops": mathops}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   種別語彙: matrix(2-D)/ signal(1-D array)/ measurement / table(dict)/
#   pairs / roots(complex 配列)
#
# tier2(complex)で足した語彙と、その理由(既存語彙で表現できないもののみ追加):
#   * cpoints  — 複素平面上の**順序つき点列**(閉曲線・写像の像)。`roots` も
#     complex 1-D だが意味が違う: roots は「解の集合」で順序に意味が無く、
#     閉じてもいない。周回積分・偏角の原理は**点の順序と閉性**が結果そのもの
#     (順序を入れ替えれば巻き数が変わる)なので、roots を輪郭として食える型に
#     すると型レベルの嘘になる。`signal` は実 1-D なので不可。
#   * cscalar  — 複素スカラ(∮f dz、f(w)、留数)。`measurement` は
#     「スカラのみ」と決めた実数プール(chain_fuzz の TYPE_CHECKS が
#     int/float に限定)で、複素を混ぜると下流の実数 op が生 TypeError で
#     落ちる(= 第 3 波で実測されたプール汚染)。分けるのが正解。
#   * cimage   — 2-D complex 画像。**新語ではなく complexops(cx_*)が既に
#     使っている語彙の再利用**で、cx_fft → cplx_cr_residual のように
#     FFT 系と数学系が型で繋がる。
_CATALOG = {
    "linalg": [
        ("mat_solve", "mathops", ["matrix", "signal"], "signal"),
        ("mat_lstsq", "mathops", ["matrix", "signal"], "table"),
        ("mat_svd", "mathops", ["matrix"], "table"),
        ("mat_eigh", "mathops", ["matrix"], "table"),
        ("mat_pinv", "mathops", ["matrix"], "matrix"),
        ("mat_cond", "mathops", ["matrix"], "measurement"),
    ],
    "stats": [
        ("stat_describe", "mathops", ["signal"], "table"),
        ("stat_histogram", "mathops", ["signal"], "pairs"),
        ("stat_covariance", "mathops", ["matrix"], "matrix"),
        ("stat_correlation", "mathops", ["matrix"], "matrix"),
        ("stat_zscore", "mathops", ["signal"], "signal"),
    ],
    "interp_poly": [
        ("interp_linear", "mathops", ["signal", "signal", "signal"], "signal"),
        ("interp_cubic", "mathops", ["signal", "signal", "signal"], "signal"),
        ("poly_fit", "mathops", ["signal", "signal"], "table"),
        ("poly_eval", "mathops", ["signal", "signal"], "signal"),
        ("poly_roots", "mathops", ["signal"], "roots"),
    ],
    "complex": [
        ("cplx_contour_circle", "mathops", [], "cpoints"),
        ("cplx_poly_eval", "mathops", ["signal", "cpoints"], "cpoints"),
        ("cplx_contour_integral", "mathops", ["cpoints", "cpoints"], "cscalar"),
        ("cplx_winding_number", "mathops", ["cpoints"], "measurement"),
        ("cplx_cauchy_value", "mathops", ["cpoints", "cpoints"], "cscalar"),
        ("cplx_argument_principle", "mathops", ["cpoints", "cpoints"], "measurement"),
        ("cplx_laurent_coeffs", "mathops", ["cpoints", "cpoints"], "table"),
        ("cplx_joukowski", "mathops", ["cpoints"], "cpoints"),
        ("cplx_mobius", "mathops", ["cpoints"], "cpoints"),
        ("cplx_cr_residual", "mathops", ["cimage"], "measurement"),
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


OPSMATH = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSMATH.items() if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d/ops1d と同じ一級機構)。素の関数は
#: 数学慣習の tuple(``U, s, Vt = mat_svd(A)``)を保ち、台帳経由 :func:`call`
#: は宣言どおり table(dict)を返す。連鎖ファザーが宣言との一致を機械検証する
#: (2026-09-01 math 次元追加の初走行で mat_svd/mat_eigh の型の嘘として検出)。
RESULT_ADAPTERS = {
    "mat_svd": lambda r: {"U": r[0], "s": r[1], "Vt": r[2]},
    "mat_eigh": lambda r: {"w": r[0], "V": r[1]},
    # stat_histogram は np.histogram 規約の ``(counts (b,), edges (b+1,))`` を返す。
    # **長さが違うので「対」ではない**(実測 10 と 11)。`pairs` の正典は (N,2) か
    # 「**同じ長さ**の 1-D 2 本」で、消費側 6 op はこの不揃いを名指しで拒否する
    # ("pairs: 2-tuple must hold two 1-D arrays of equal length; got (10,) and
    # (11,)" — 実測)。2026-09-02 まで pairs の述語が ``lambda v: True`` だった
    # ため型の嘘として現れなかった。
    # bin 幅は edges から一意に決まるので、**bin 中心 × 度数**の対 (b,2) に組み直す
    # (funct_1d_to_pairs が x 列を作るのと同じ読み方)。素の (counts, edges) は
    # ``opsmath.get("stat_histogram")`` でそのまま取れる。
    "stat_histogram": lambda r: np.stack(
        [(np.asarray(r[1][:-1], np.float64) + np.asarray(r[1][1:], np.float64)) / 2.0,
         np.asarray(r[0], np.float64)], axis=1)
    if isinstance(r, tuple) and len(r) == 2 else r,
}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSMATH[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSMATH[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSMATH[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSMATH.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsmath: {len(OPSMATH)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
