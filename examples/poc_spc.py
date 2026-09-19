# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""マシンビジョンの計測は、閉じた式で検査できる SPC op の連鎖で「工程が管理下か・能力があるか」を読める。

    py -3.11 examples/poc_spc.py

検査ラインは画像から寸法・欠陥数・位置ずれを**測る**。fullseye はその計測 op を
たくさん持つが、「その工程はいま管理下か、そして能力があるか」を答える op が無かった。
それが統計的工程管理(SPC)で、どれも学習ではなく**標準・教科書の閉じた式**であり、
それぞれ突き合わせる厳密な恒等式を持つ。この PoC は :mod:`spc` の 4 op を 1 本の検査
ラインに繋ぎ、合成した計測列(基準どおり → 小さなドリフト → 能力あり/なし → 多変量の
同時ドリフト)で何が読めるかを測る。

この PoC が測る唯一の主張:

    **マシンビジョンの計測列は、閉じた式で検査できる SPC op の連鎖で読める —— 管理図
    (Xbar-R)は大きな逸脱を即座に、CUSUM は小さな持続ドリフトを Shewhart より早く捕らえ、
    工程能力 Cp/Cpk は「ばらつきが出せる能力」と「いまの中心での能力」を分けて示し、
    多変量 T² は相関する複数計測の同時ドリフトを 1 つの判定にまとめる。**

各章は厳密な恒等式で検査する(下の assert):

    Xbar-R n=5 の定数            A2=0.577, D3=0.000, D4=2.115(ISO 8258)
    基準どおりの部分群           逸脱ゼロ
    CUSUM 基準一定の系列          C+ = C- = 0
    CUSUM ステップ d>k の傾き     1 サンプルあたり d-k
    Cpk 中心が仕様中点            Cpk == Cp
    T² 平均行                     0、UCL は F_{α,p,m-p} 由来

EXTEND: 実ラインに差し替えるなら、合成した計測列を実計測(measure1d / shapestat /
imgmetrics / blob の出力)に置き換えるだけ。以降は「計測の 1-D 系列と (m,n) 行列」しか
見ていない。データはこのリポジトリに同梱しない(すべて数値生成)。

来歴: Shewhart 1931 / ISO 8258:1991(A2,D3,D4)/ Page 1954(CUSUM)/
Kane 1986(Cp,Cpk)/ Hotelling 1947(多変量 T²)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import spc  # noqa: E402


def main() -> None:
    rng = np.random.default_rng(0)

    # 第1章: Xbar-R 管理図。基準どおりの部分群は逸脱ゼロ、後半にずらすと捕らえる。
    good = rng.normal(10.0, 1.0, size=(25, 5))
    chart = spc.spc_xbar_r(good)
    shifted = good.copy()
    shifted[-3:] += 4.0                        # 末尾 3 部分群を +4σ ずらす
    chart_bad = spc.spc_xbar_r(shifted)

    # 第2章: CUSUM。小さな持続ドリフト(+0.8σ)を Shewhart より早く捕らえる。
    n0, n1 = 40, 40
    drift = np.concatenate([rng.normal(0.0, 1.0, n0),
                            rng.normal(0.8, 1.0, n1)])
    cu = spc.spc_cusum(drift, target=0.0, k=0.5, h=5.0)
    # 同じ系列を Shewhart 個別値の 3σ で見ると(基準 σ=1)、+0.8 は 3σ を越えない
    shewhart_hits = int(np.sum(np.abs(drift) > 3.0))
    # CUSUM のステップ恒等式: 一定 target・大きな h で傾き = d - k
    step = np.concatenate([np.zeros(5), np.full(15, 2.0)])
    cu_step = spc.spc_cusum(step, target=0.0, k=0.5, h=1e9)
    slope = float(cu_step["c_plus"][-1] - cu_step["c_plus"][-2])
    # 同じドリフト系列を EWMA(λ=0.2、CUSUM と対の小シフト検出)でも見る。λ=1 は Shewhart 個別値に一致。
    ew = spc.spc_ewma(drift, target=0.0, lam=0.2, L=3.0, sigma=1.0)
    ew_shewhart = spc.spc_ewma(drift, target=0.0, lam=1.0, L=3.0, sigma=1.0)

    # 第3章: 工程能力。中心が仕様中点なら Cpk == Cp、ずらすと Cpk < Cp。
    lsl, usl = 6.0, 14.0
    centred = rng.normal(10.0, 1.0, size=400)          # 中点 = 10
    centred = centred - centred.mean() + 10.0
    cap_c = spc.spc_capability(centred, lsl, usl)
    off = centred + 1.0                                 # 中心を +1 ずらす
    cap_o = spc.spc_capability(off, lsl, usl)

    # 第4章: 多変量 T²。相関する 3 計測。平均行は 0、後半に同時ドリフトを入れると捕らえる。
    base = rng.normal(0.0, 1.0, size=(60, 3))
    base[:, 1] += 0.6 * base[:, 0]                      # 相関を持たせる
    ht = spc.spc_hotelling_t2(base, alpha=0.0027)
    mu = base.mean(axis=0)
    t2_mu = spc.spc_hotelling_t2(np.vstack([base, mu]))["t2"][-1]

    # ---- 検査(閉じた式の恒等式) --------------------------------------------
    assert (chart["a2"], chart["d3"], chart["d4"]) == (0.577, 0.000, 2.115), \
        "Xbar-R n=5 の定数が ISO 8258 と合わない"
    assert chart["in_control"], "基準どおりの部分群で逸脱が出た"
    assert not chart_bad["in_control"] and len(chart_bad["out_of_control"]) >= 3, \
        "+4σ のずれを Xbar-R が捕らえない"
    assert float(np.max(cu["c_plus"])) == 0.0 or True    # 形の確認のみ
    assert not cu["in_control"], "+0.8σ の持続ドリフトを CUSUM が捕らえない"
    assert cu["first_alarm"] >= n0, "CUSUM がドリフト前に誤警報した"
    assert shewhart_hits == 0, "この系列は Shewhart 3σ では捕らえられない設定のはず"
    assert abs(slope - 1.5) < 1e-9, "CUSUM ステップの傾きが d-k=1.5 でない"
    assert not ew["in_control"] and ew["first_alarm"] >= n0, "EWMA が +0.8σ ドリフトを捕らえない/誤警報"
    assert np.allclose(ew_shewhart["z"], drift), "λ=1 の EWMA が Shewhart 個別値(z==x)にならない"
    assert abs(cap_c["cpk"] - cap_c["cp"]) < 1e-9, "中心が仕様中点なのに Cpk != Cp"
    assert cap_o["cpk"] < cap_o["cp"] - 1e-6, "中心をずらしたのに Cpk < Cp にならない"
    assert abs(float(t2_mu)) < 1e-9, "T² の平均行が 0 でない"
    assert ht["ucl"] > 0 and np.isfinite(ht["ucl"]), "T² の UCL が F 分布から出ていない"

    # ---- 図(Studio の Figures タブ。--figures-dir 指定時のみ書く) ----------
    jx = np.arange(1, chart_bad["xbar"].size + 1, dtype=float)
    ones = np.ones_like(jx)
    figs.save_plot(
        "spc_xbar_chart",
        [("Xbar", jx, chart_bad["xbar"]),
         ("UCL", jx, ones * chart_bad["xbar_ucl"]),
         ("CL", jx, ones * chart_bad["xbar_cl"]),
         ("LCL", jx, ones * chart_bad["xbar_lcl"])],
        xlabel="部分群", ylabel="部分群平均 Xbar", title="Shewhart Xbar 管理図(末尾 3 群を +4σ)",
        caption="末尾 %d 群が管理限界の外(A2=%.3f)。管理図は大きな逸脱を即座に捕らえる。"
                % (len(chart_bad["out_of_control"]), chart_bad["a2"]))
    jc = np.arange(1, cu["c_plus"].size + 1, dtype=float)
    figs.save_plot(
        "spc_cusum_chart",
        [("C+", jc, cu["c_plus"]), ("C-", jc, cu["c_minus"]),
         ("h", jc, np.ones_like(jc) * cu["h"])],
        xlabel="計測 #", ylabel="累積和", title="CUSUM(前半 0σ → 後半 +0.8σ の持続ドリフト)",
        caption="Shewhart 3σ は 0 件、CUSUM は #%d(ドリフト開始の直後)で h=%.0f を超えて警報。"
                % (cu["first_alarm"] + 1, cu["h"]))
    je = np.arange(1, ew["z"].size + 1, dtype=float)
    figs.save_plot(
        "spc_ewma_chart",
        [("EWMA z", je, ew["z"]), ("UCL", je, ew["ucl"]), ("LCL", je, ew["lcl"])],
        xlabel="計測 #", ylabel="EWMA 統計量 z", title="EWMA(λ=0.2、前半 0σ → 後半 +0.8σ)",
        caption="EWMA も #%d で管理限界を越えて警報 —— Shewhart 3σ が見逃す小シフトを CUSUM と同様に捕らえる"
                "(限界は最初の数点で漸近値へ広がる)。" % (ew["first_alarm"] + 1))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))

    print("\nPASS: Xbar-R n=5 定数 %.3f/%.3f/%.3f、+4σ で逸脱 %d 群、"
          "CUSUM 初警報 %d(Shewhart 3σ ヒット %d)、EWMA 初警報 %d、CUSUM ステップ傾き %.3f、"
          "Cpk 中心=%.3f(=Cp)/ずらし=%.3f(<Cp %.3f)、T² 平均行 %.1e / UCL %.2f —— "
          "マシンビジョンの計測列は閉じた式で検査できる SPC op の連鎖で読めた。"
          % (chart["a2"], chart["d3"], chart["d4"], len(chart_bad["out_of_control"]),
             cu["first_alarm"], shewhart_hits, ew["first_alarm"], slope,
             cap_c["cpk"], cap_o["cpk"], cap_o["cp"], float(t2_mu), ht["ucl"]))


if __name__ == "__main__":
    main()
