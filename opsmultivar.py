# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsmultivar — fullseye design-of-experiments / multivariate / sensitivity op registry.

Motivation (2026-10-15): to tune the coefficients of a physical model from real images,
the first questions are statistical — which settings to run, which knobs change the
picture, which knobs can only be told apart in combination. fullseye had the pieces
(``mathnumerics.low_discrepancy``, ``mathspectral.n_sources_mdl``, ``spc``'s SN ratio
and ANOVA tables) but no plan, no table-level PCA/PLS and no response surface. This
registry is that general-purpose family; the calibration layer builds on it.

Categories:
  * ``plan``   — which runs to make (``doe.py``): Latin hypercube, Taguchi orthogonal
    arrays copied from published tables, 2^(k-p) fractions, central composite and
    Box-Behnken designs.
  * ``coding`` — natural units <-> coded −1..+1 (``doe.py``).

Provenance is public literature only (docs/PROVENANCE.md naming rule): McKay, Beckman &
Conover 1979; Taguchi 1987 / Bose & Bush 1952 (tables via the University of York and NIST
Dataplot); Box & Hunter 1961 (fractions, NIST/SEMATECH e-Handbook Table 3.17); Box & Wilson
1951; Box & Behnken 1960.

Usage:
    import opsmultivar
    opsmultivar.list_ops("plan")
    opsmultivar.get("doe_orthogonal_array")("L9", 4)
"""
import doe

_MOD = {"doe": doe}

# --------------------------------------------------------------------------
# Type vocabulary: ONE new word, ``design``.
# --------------------------------------------------------------------------
#   * design — a dict carrying BOTH the coded matrix (−1..+1, what the statistics is
#     computed on) and the natural matrix (bench settings), with factor names, units,
#     ranges, per-factor scale (linear/log) and the confounding (alias) table. Not a
#     ``matrix``: the coded and natural matrices have the same shape and dtype, and a
#     quadratic fit on the wrong one returns a differently-centred surface without any
#     error (mixing them lies silently, so the types are split).
#   * matrix — natural-unit settings handed to doe_encode / returned by doe_decode.
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 計画: どの条件で走らせるか。入力なし(因子の範囲は引数)→ design。
    "plan": [
        ("doe_lhs", "doe", [], "design"),
        ("doe_orthogonal_array", "doe", [], "design"),
        ("doe_fractional_factorial", "doe", [], "design"),
        ("doe_central_composite", "doe", [], "design"),
        ("doe_box_behnken", "doe", [], "design"),
    ],
    # 符号化: 自然単位 ⇔ −1..+1(線形 / 対数)。
    "coding": [
        ("doe_encode", "doe", ["matrix"], "design"),
        ("doe_decode", "doe", ["design"], "matrix"),
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


OPSMULTIVAR = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSMULTIVAR.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 — 意図的に**。全 op が宣言型どおり
#: (design = dict / matrix = ndarray / table = dict)を素で返す。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSMULTIVAR[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSMULTIVAR[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSMULTIVAR[name]


def missing():
    """台帳にあるのに実体の無い op(空であるべき)。"""
    return [n for n, m in OPSMULTIVAR.items() if m["func"] is None]


if __name__ == "__main__":
    for c in categories():
        print(c, list_ops(c))
    print("missing:", missing())
