# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opssimcal — fullseye sim-to-real calibration op registry (fit a physical model's knobs to real images).

Motivation (2026-10-15): "given real images, feed the error back and adjust the coefficients
the computation uses". fullseye has many forward models (vignetting, blur, thin films,
telecentric distortion, pixel shift) and the statistics to plan and screen them
(``opsmultivar``), but nothing that closes the loop from a measured image to the model's
coefficients — with the refusal that matters most: a knob the images cannot determine gets no
number. This registry is that loop.

Categories:
  * ``model``  — the forward model and its data (``simcal.py``): build a ``simmodel`` from a
    chain of ops and knobs with units/ranges/scales, run it, attach measured images (alignment,
    ROI, exposure normalisation).
  * ``fit``    — which knobs matter and their values (``simcal.py``): screening on the
    noise-whitened outputs (Morris / Sobol' / collinearity) and the weighted least-squares fit
    that refuses undetermined knobs.
  * ``check``  — how far to trust the values (``simcalcheck.py``): Fisher information,
    Cramér-Rao bound and profile likelihood; Laplace / bootstrap intervals; over-fitting gates on
    held-out images (TRAIN / OBSERVED / LOCKED); residual PCA against the Tracy-Widom edge
    (model discrepancy). Each withdraws the estimates it does not support.
  * ``report`` — one table of the result (``simcalcheck.py``).

Provenance is public literature only (docs/PROVENANCE.md naming rule): Levenberg 1944;
Marquardt 1963; Nelder & Mead 1965; Kennedy & O'Hagan 2001; Brun, Reichert & Künsch 2001;
Morris 1991; Saltelli et al. 2010; Lamboni, Monod & Makowski 2011 (variance-weighted indices over
principal components); McCullagh & Nelder 1989 (iteratively re-weighted least squares); EMVA 1288
Release 4.0 (camera noise model); Raue et al. 2009 (profile likelihood); Efron 1979 (bootstrap);
Johnstone 2001 (Tracy-Widom edge); Brynjarsdóttir & O'Hagan 2014.

Usage:
    import opssimcal
    opssimcal.list_ops("fit")
    opssimcal.get("simcal_fit")(opssimcal.get("simcal_model")())
"""
import simcal
import simcalcheck

_MOD = {"simcal": simcal, "simcalcheck": simcalcheck}

# --------------------------------------------------------------------------
# Type vocabulary: TWO new words, ``simmodel`` and ``calresult``.
# --------------------------------------------------------------------------
#   * simmodel — a dict: the chain (op names + fixed arguments), the knobs (step, argument,
#     range, unit, linear/log scale, prior, role), conditions, the camera noise model, an
#     optional stochastic port, and — after simcal_observe — the measured images with masks.
#     Not a ``table``: a table is data, a simmodel is a runnable model; handing a model where a
#     result is expected (or the reverse) must fail at the type, not deep inside a fit.
#   * calresult — a dict: the estimates the data support (and ONLY those), the undetermined
#     knobs with reasons, determined combinations, errors per split, residual maps, and the
#     sections the checking ops fill. Not a ``table``: a table's numbers are all usable; a
#     calresult carries an optimiser end point that is explicitly NOT an estimate for the
#     refused knobs, and an op that read it as a table would publish those numbers.
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 模型: 順方向の連鎖とつまみ、実行、実画像の取り付け。
    "model": [
        ("simcal_model", "simcal", [], "simmodel"),
        ("simcal_simulate", "simcal", ["simmodel"], "images"),
        ("simcal_observe", "simcal", ["simmodel", "images"], "simmodel"),
    ],
    # 合わせ: 効くつまみのふるいと、決まらないつまみを拒否する当てはめ。
    "fit": [
        ("simcal_screen", "simcal", ["simmodel"], "table"),
        ("simcal_fit", "simcal", ["simmodel"], "calresult"),
    ],
    # 検査: 決まるか(下界・プロファイル)、どれだけ確かか、取り置いた画像で持つか、模型に何が足りないか。
    #   どれも calresult を受けて calresult を返し、支えられない点推定は理由をつけて取り下げる。
    "check": [
        ("simcal_identifiability", "simcalcheck", ["calresult"], "calresult"),
        ("simcal_uncertainty", "simcalcheck", ["calresult"], "calresult"),
        ("simcal_validate", "simcalcheck", ["calresult", "simmodel"], "calresult"),
        ("simcal_discrepancy", "simcalcheck", ["calresult"], "calresult"),
    ],
    # 報告: 表 1 枚(走らせなかった検査は「not run」と書く)。
    "report": [
        ("simcal_report", "simcalcheck", ["calresult"], "table"),
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


OPSSIMCAL = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSSIMCAL.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 — 意図的に**。全 op が宣言型どおり
#: (simmodel / calresult = dict、images = 2-D 配列の list、table = dict)を素で返す。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSSIMCAL[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSSIMCAL[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSSIMCAL[name]


def missing():
    """台帳にあるのに実体の無い op(空であるべき)。"""
    return [n for n, m in OPSSIMCAL.items() if m["func"] is None]


if __name__ == "__main__":
    for c in categories():
        print(c, list_ops(c))
    print("missing:", missing())
