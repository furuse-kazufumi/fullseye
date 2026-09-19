# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsspc — fullseye statistical-process-control op registry.

Motivation (2026-09-13): fullseye produces measurements from images (measure1d /
shapestat / imgmetrics / blob) but had no operator to answer the line's question —
*is this process in control, and is it capable?* This registry is that pathway
(spc.py, 4 ops / 4 categories). Every op is a closed-form textbook / standards model
with an exact identity to check it against, not a fitted model (see the thresholds
in the guide and ``tests/test_spc.py``).

Provenance is public standards and textbooks only (docs/PROVENANCE.md naming rule —
no product or company names): Shewhart 1931 (control chart) / ISO 8258:1991 (A2, D3,
D4 constants) / Page, *Biometrika* 1954 (CUSUM) / Kane, *J. Quality Technology* 1986
(Cp, Cpk) / Hotelling 1947 (T² multivariate control).

Coexistence with existing assets (compose, do not re-implement):
  * measurements come from measure1d / shapestat / imgmetrics / blob. SPC consumes
    their plain 1-D series (signal) and (m, p) matrices — it adds the *quality
    verdict*, not new measurement.
  * general statistics = statistics / multivariate. Those describe a sample; SPC
    charts it against control limits over time. `spc_hotelling_t2` needs an inverse
    covariance but does not re-wrap the general estimators — it uses numpy.cov and
    fail-closes on a singular matrix.

Usage:
    import opsspc
    opsspc.list_ops("chart")
    opsspc.get("spc_xbar_r")(subgroups)
"""
import spc

_MOD = {"spc": spc}

# --------------------------------------------------------------------------
# Type vocabulary: no new word is coined (it all fits the existing pool).
# --------------------------------------------------------------------------
#   * matrix  — `spc_xbar_r` eats (m, n) subgroups and `spc_hotelling_t2` eats
#     (m, p) observations: general 2-D numeric matrices (opsmath's matrix), not
#     images. Row/column shape is validated at call time (fail-closed).
#   * signal  — `spc_cusum` / `spc_capability` eat a 1-D measurement series, the
#     same sort measure1d / dsp produce and consume.
#   * table   — every op returns a dict of chart limits, statistics and the
#     out-of-control indices: the existing table sort.
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    "chart": [
        ("spc_xbar_r", "spc", ["matrix"], "table"),
    ],
    "change": [
        ("spc_cusum", "spc", ["signal"], "table"),
        ("spc_ewma", "spc", ["signal"], "table"),
    ],
    "capability": [
        ("spc_capability", "spc", ["signal"], "table"),
    ],
    "multivariate": [
        ("spc_hotelling_t2", "spc", ["matrix"], "table"),
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


OPSSPC = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSSPC.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 — 意図的に**。4 op はすべて宣言型どおり
#: (dict = table)を素で返すので、adapter を挟まないほうが連鎖ファザーの検証が
#: 最も厳しい(素の返りをそのまま宣言と突き合わせる)。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSSPC[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSSPC[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSSPC[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSSPC.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsspc: {len(OPSSPC)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
