# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsmath — fullseye 数学 op の統一レジストリ(mathops を一望・発見可能に)。

ユーザー方針(2026-08-31)「数学系 op を Fullseye の op として充実させたい。
数学辞典に載る問題を全て扱えるくらいの op 量を目指す」。本レジストリはその
台帳 — 第一陣は視覚計測を支える 3 分野 16 op(mathops.py、数学系 RAD コーパス
4 分野で選定を裏取り)。FFT/複素画像は complexops・volfreq・dsp に、1D 関数は
funct1d に既存で、ここでは重複させない。

拡張ロードマップ(tier、docs/NEXT_OPS_PLAN_2026-08-31.md §F が正本):
  tier1 線形代数/統計/補間・多項式(済)→ tier2 複素解析の計算可能な切り口
  (Cauchy 積分・偏角の原理・等角写像)→ tier3 最適化/特殊関数 → …

使い方:
    import opsmath
    opsmath.list_ops("linalg")
    opsmath.get("mat_svd")(...)
"""
import mathops

_MOD = {"mathops": mathops}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   種別語彙: matrix(2-D)/ signal(1-D array)/ measurement / table(dict)/
#   pairs / roots(complex 配列)
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


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSMATH[name]["func"]


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
