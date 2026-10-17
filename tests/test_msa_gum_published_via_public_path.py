# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MSA / GUM の公表例題を、**利用者が叩く公開の入口**(``fullseye.op_run`` + 表の契約)で再現する。

外部 AI のレビュー(PyPI 0.6.0)は「契約が表(列名 → 1-D 配列の dict)に変わり、公表値の再現が未再測定」と
書いた。一次検証(2026-10-18): ``tests/test_msa.py`` は 2026-09-23 から表の契約で公表値を再現しており
(0.6.0 にも入っている)、0.6.0 の venv で ``op_run`` から叩いても同じ値が出た —— 指摘は誤検出。ただし
既存の門は ``spc.*`` を直接呼んでいて、``op_run``(台帳の adapter・前提チェック・種の補完)を通る公開の道は
数えていなかった。ここはその道だけを足す。

数値の出典(``tests/test_msa.py`` の転記を流用。今回、一次資料を開いての再照合はしていない —— 未確認):

* 測定システム解析の参考マニュアル第 4 版の分散分析法の例題(10 部品 x 3 人 x 3 回)。EV 0.199933 / AV 0.226838 / GRR 0.302373 /
  PV 1.042327 / TV 1.085、寄与率 3.4 / 4.4 / 7.8 / 92.2 %、%GRR 27.9、ndc 4.861。★この手引きは有償で、
  今回は開けていない。
* JCGM 100:2008 附属書 H.1(端度器の校正): u_c = 32 nm、ν_eff = 16、k = 2.12。
* JCGM 100:2008 附属書 H.2(抵抗・リアクタンス・インピーダンスの同時測定): R = 127.732 Ω (u 0.071)、
  X = 219.847 Ω (u 0.295)、Z = 254.260 Ω (u 0.236)、相関係数 −0.36 / 0.86 / −0.65。
* JCGM 101:2008 §9.2(加法モデル、4 入力 u = 1): 正規で 95 % 区間 ±3.92、矩形で ±3.88。
* JCGM 101:2008 §9.4(比較損失 δY = X1² + X2²、u = 0.005、x1 = x2 = 0): モンテカルロの平均 50e-6・
  標準不確かさ 50e-6・区間 [0, 150e-6]。
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import fullseye as fs  # noqa: E402


def _test_msa():
    spec = importlib.util.spec_from_file_location("_test_msa_data", os.path.join(ROOT, "tests", "test_msa.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gauge_rr_worked_example_through_op_run():
    T = _test_msa()._reference_table()
    assert set(T) == {"part", "operator", "value"} and all(np.ndim(v) == 1 for v in T.values())
    G, notes = fs.op_run("msa_gauge_rr", T, pool_alpha=0.05)
    s = dict(zip(G["component"], G["sigma"]))
    for name, published in (("repeatability", 0.199933), ("reproducibility", 0.226838),
                            ("gauge_rr", 0.302373), ("part", 1.042327)):
        assert abs(s[name] - published) < 5e-6, (name, s[name], published)
    assert abs(s["total"] - 1.085) < 5e-4
    pc = dict(zip(G["component"], G["pct_contribution"]))
    for name, published in (("repeatability", 3.4), ("reproducibility", 4.4),
                            ("gauge_rr", 7.8), ("part", 92.2)):
        assert abs(pc[name] - published) < 0.05, (name, pc[name], published)
    assert abs(G["ndc"][0] - 4.861) < 5e-3
    assert abs(G["pct_grr"][0] - 27.9) < 0.05


def test_gauge_rr_probe_a_corrupted_reading_moves_the_answer():
    """探針: 1 読みを 0.5 だけ書き換えると公表値から外れる(門が素通りしていない)。"""
    T = _test_msa()._reference_table()
    T["value"] = T["value"].copy()
    T["value"][0] += 0.5
    G, _ = fs.op_run("msa_gauge_rr", T, pool_alpha=0.05)
    s = dict(zip(G["component"], G["sigma"]))
    assert abs(s["repeatability"] - 0.199933) > 1e-3


def _h1_budget():
    l_s_nm = 50e6
    return {"u": np.array([25.0, 5.8, 3.9, 6.7, 0.58e-6, 0.029]),
            "sensitivity": np.array([1.0, 1.0, 1.0, 1.0, l_s_nm * (-0.1), l_s_nm * 11.5e-6]),
            "dof": np.array([18.0, 24.0, 5.0, 8.0, 50.0, 2.0])}


def test_jcgm100_h1_through_op_run():
    E, _ = fs.op_run("gum_expanded", _h1_budget(), level=0.95)
    assert abs(E["u_combined"][0] - 32.0) < 0.5
    assert E["dof_used"][0] == 16.0
    assert abs(E["coverage_factor"][0] - 2.12) < 5e-3
    P, _ = fs.op_run("gum_propagate", _h1_budget())
    for got, published in zip(np.sqrt(P["contribution"]), [25.0, 5.8, 3.9, 6.7, 2.9, 16.6]):
        assert abs(got - published) < 0.1


def test_jcgm100_h2_through_op_run():
    v, i, ph, u, R = _test_msa()._impedance_budget()
    for sens, pub_u in (([np.cos(ph) / i, -v * np.cos(ph) / i ** 2, -v * np.sin(ph) / i], 0.071),
                        ([np.sin(ph) / i, -v * np.sin(ph) / i ** 2, v * np.cos(ph) / i], 0.295),
                        ([1.0 / i, -v / i ** 2, 0.0], 0.236)):
        g, _ = fs.op_run("gum_propagate", {"u": np.asarray(u), "sensitivity": np.asarray(sens)},
                         correlation=R)
        assert abs(g["u_combined"][0] - pub_u) < 1.5e-3, (g["u_combined"][0], pub_u)
    # 探針: 相関を落とすと R の u_c は 2 倍を超えて外れる(相関が本当に効いている)
    g0, _ = fs.op_run("gum_propagate", {"u": np.asarray(u), "sensitivity": np.asarray(
        [np.cos(ph) / i, -v * np.cos(ph) / i ** 2, -v * np.sin(ph) / i])})
    assert g0["u_combined"][0] > 2 * 0.071


def test_jcgm101_9_2_additive_model_through_op_run():
    lin = {"u": np.ones(4), "sensitivity": np.ones(4)}
    M, _ = fs.op_run("gum_monte_carlo", lin, n=200_000, seed=1)
    assert abs(M["half_width"][0] - 3.92) < 0.05
    rect = {**lin, "distribution": np.array(["rectangular"] * 4, dtype=object)}
    Mr, _ = fs.op_run("gum_monte_carlo", rect, n=200_000, seed=1, distribution="distribution")
    assert abs(Mr["half_width"][0] - 3.88) < 0.03
    assert Mr["half_width"][0] < M["half_width"][0]


def test_jcgm101_9_4_comparison_loss_through_op_run():
    tab = {"u": np.array([0.005, 0.005]), "sensitivity": np.ones(2),
           "value": np.zeros(2), "power": np.array([2.0, 2.0])}
    M, _ = fs.op_run("gum_monte_carlo", tab, n=200_000, seed=3, value="value", power="power")
    assert abs(M["mean"][0] * 1e6 - 50.0) < 1.0
    assert abs(M["u_monte_carlo"][0] * 1e6 - 50.0) < 1.5
    assert abs(M["low"][0]) < 1e-9
    assert abs(M["high"][0] * 1e6 - 150.0) < 3.0
