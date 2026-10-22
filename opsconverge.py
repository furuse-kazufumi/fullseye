# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsconverge — fullseye convergent-computation op registry (iterate until converged, and prove it).

Motivation (2026-10-15): "if the simulation is to come really close to reality, some
computations will have to be the convergent kind." fullseye's forward models were single-shot
(direct light only, a fixed number of bounces, a fixed number of samples, a fixed number of
deconvolution iterations) and the few that iterated (lens optimisation, astro stacking, flow)
each had their own private idea of "converged". A model that leaves out the inter-reflections
of a groove can still be fitted to a real image — its coefficients absorb the missing light —
so the calibration layer (``opssimcal``) needs forward models that converge AND say how far
from the limit they are. This registry is that common contract.

Categories:
  * ``iterate``      — the fixed-point driver (``converge.py``): plain / Aitken / Anderson
    (Walker & Ni 2011 eq. 3.1, QR with column dropping), residual history, an a-posteriori
    error bound, and a refusal instead of a value when it does not converge.
  * ``verification`` — is the discretisation fine enough (``converge.py``): observed order and
    grid convergence index (Celik et al. 2008 eqs. 1-7, non-constant ratio and oscillatory
    convergence).
  * ``montecarlo``   — sampling until the interval is narrow enough (``converge.py``) and the
    photon transport in layered turbid media (``mcphoton.py``, MCML rules) with confidence
    intervals, gated on the MCML manual's Tables 6.1 / 6.2.
  * ``stopping``     — when to stop an inverse iteration (``deconvstop.py``): Richardson-Lucy
    stopped by the Poisson discrepancy (Bertero et al. 2010, tau = 1) or Morozov's principle,
    refusing data outside the model's range (Benvenuto & Piana 2012).

Provenance is public literature only (docs/PROVENANCE.md naming rule): Walker & Ni 2011;
Anderson 1965; Aitken 1926; Celik et al. 2008; Roache 1994; Chow & Robbins 1965; Wang, Jacques
& Zheng 1995 and the MCML manual (Wang & Jacques); van de Hulst 1980; Giovanelli 1955; Prahl
et al. 1989; Bertero, Boccacci, Talenti, Zanella & Zanni 2010; Benvenuto & Piana 2012;
Morozov 1966; Richardson 1972; Lucy 1974.

Usage:
    import opsconverge
    opsconverge.list_ops("iterate")
    opsconverge.get("iterate_fixed_point")("cos", method="anderson")
"""
import converge
import deconvstop
import mcphoton

_MOD = {"converge": converge, "mcphoton": mcphoton, "deconvstop": deconvstop}

# --------------------------------------------------------------------------
# Type vocabulary: NO new word.
# --------------------------------------------------------------------------
#   Every op returns a ``table`` (a dict). A record that did NOT converge never carries its
#   last iterate under the value key (``x`` / ``mean`` / ``image`` are None, the iterate sits
#   under ``last_iterate``), and the default for the fixed-point driver and the sequential mean
#   is to raise (``MetricContractError``) — so a table read naively cannot publish an
#   unconverged number, which is the test for whether a new type would be needed.
#   * image2d — the blurred, noisy image handed to the stopped deconvolution.
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 反復: 不動点反復の汎用ドライバ(加速つき、収束しなければ値を返さない)。
    "iterate": [
        ("iterate_fixed_point", "converge", [], "table"),
    ],
    # 検証: 格子(標本数)を 3 段振って、観測収束次数と GCI。
    "verification": [
        ("conv_observed_order", "converge", [], "table"),
        ("conv_gci", "converge", [], "table"),
    ],
    # モンテカルロ: 区間が許容幅に入るまで足す / 多層スラブの光子輸送(信頼区間つき)。
    "montecarlo": [
        ("mc_sequential_mean", "converge", [], "table"),
        ("mc_photon_slab", "mcphoton", [], "table"),
    ],
    # 止め方: 逆問題の反復を食い違い原理で止める(止まらなければモデルの値域外)。
    "stopping": [
        ("iv_richardson_lucy_until", "deconvstop", ["image2d"], "table"),
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


OPSCONVERGE = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSCONVERGE.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 — 意図的に**。全 op が宣言型どおり table(dict)を素で返す。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSCONVERGE[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSCONVERGE[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSCONVERGE[name]


def missing():
    """台帳にあるのに実体の無い op(空であるべき)。"""
    return [n for n, m in OPSCONVERGE.items() if m["func"] is None]


if __name__ == "__main__":
    for c in categories():
        print(c, list_ops(c))
    print("missing:", missing())
