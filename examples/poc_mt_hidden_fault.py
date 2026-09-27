# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""どのセンサーも正常値なのに、設備は異常 —— MT 法が単変量 3σ の見逃しを拾う量を測る。

    py -3.11 examples/poc_mt_hidden_fault.py

:mod:`poc_machine_condition_fusion` は「3 つ見ても同じものを 3 回見ている」ことを示した
(芯ずれでは 2X 振動・継手の発熱・軸心のずれが 1 つの重症度の別の顔)。それは逆に言うと
**健全な設備では特徴量どうしに強い相関がある**ということで、相関が壊れた瞬間は
**どの 1 つを見ても正常範囲**でありうる。単変量の「平均 ± 3σ」はその崩れを原理的に
見られない。MT 法(マハラノビス・タグチ)の MD は相関を含めた距離なので見られる。

この PoC が測る唯一の主張:

    **軽い故障では、単変量 3σ が「全特徴量とも正常範囲」と言う標本のうち、MT 法の MD が
    異常と言う標本が実測で何割あるか。** その割合が「相関を見ないと失う検出」の量。

検査する恒等式(下の assert、当てはめた数字は無い):

1. 単位空間の MD² の平均 = (N − 1)/N(ddof=1 で標準化した定義から厳密に出る)。
2. 2 特徴・相関 ρ の単位空間で、点 (+z, −z) の MD² = z²/(1 − ρ)(閉形式)。
   この点は各座標が ±z なので |z| < 3 なら単変量は決して鳴らない —— 「隠れた異常」の
   構成的な例。
3. MT の閾値は健全の**別標本**(学習に使わない)の MD の最大値に置き、誤警報 0 を
   両方式で同じ条件にする。閾値を先に決め、後から当てはめない。

この PoC が言えないこと: 素材は :mod:`poc_machine_condition_fusion` の合成モデル
(重症度 1 つから 3 センサが決まる構造)。実機では相関はもっと弱く、ここで出る割合は
**この合成モデルの上界**。主張は「相関を見ないと失う検出が測れる形になっている」まで。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "examples"))
import examplefig as figs  # noqa: E402
import spc  # noqa: E402
import poc_machine_condition_fusion as M  # noqa: E402

N_UNIT = 48          # 単位空間(健全)の標本数
N_HOLD = 32          # 閾値を決める健全の別標本
N_FAULT = 24         # 故障モード × 重症度 1 段あたりの標本数
SEVERITIES = (0.05, 0.1, 0.15, 0.2, 0.3, 0.5)   # 正常(0)と故障(1)の間の重み。軽い側を見る
FEATS = M.ALL_FEATS

_ORIG_PARAMS = M.mode_params


def blend_params(mode: str, sev: float) -> dict:
    """軽い故障 = 正常と「重症度 1 の故障」の線形内挿。

    ★元 PoC の :func:`poc_machine_condition_fusion.mode_params` は「重症度 × 故障値」で、
    重症度 0.03 のアンバランスは 1X 振動 0.007(正常 0.020 より**小さい**)、外輪傷は
    軸受の発熱 0.33 W(正常 2.5 W より**冷たい**)になる —— それは「軽い故障」でなく
    別の異常で、検出率が重症度に対して単調でなくなった(実測: 0.03 で 83 %、0.06 で 4 %)。
    ここでは sev ∈ [0, 1] を正常(0)と故障(1)の間の重みにする。sev=1 は元と同じ。
    """
    s = float(sev)
    n = _ORIG_PARAMS("正常", 1.0)
    f = _ORIG_PARAMS(mode, 1.0)
    if mode == "正常":
        return n

    def mix_dict(a, b):
        return {k: (1 - s) * a.get(k, 0.0) + s * b.get(k, 0.0) for k in set(a) | set(b)}
    return {"harm": mix_dict(n["harm"], f["harm"]), "axial": mix_dict(n["axial"], f["axial"]),
            "bpfo": (1 - s) * n["bpfo"] + s * f["bpfo"], "mod": (1 - s) * n["mod"] + s * f["mod"],
            "bb": (1 - s) * n["bb"] + s * f["bb"],
            "heat": tuple((1 - s) * x + s * y for x, y in zip(n["heat"], f["heat"])),
            "off": (1 - s) * n["off"] + s * f["off"], "ang": (1 - s) * n["ang"] + s * f["ang"]}


M.mode_params = blend_params   # 生成器(vib_record / thermal_frame / shaft_points)はこれを引く


def features(mode: str, sev: float, seed: int) -> dict:
    """重症度を直接指定して 3 センサの特徴量を作る(既存 PoC の生成器をそのまま使う)。"""
    out = {}
    out.update(M.vib_features(*M.vib_record(mode, sev, seed)))
    out.update(M.thermal_features(M.thermal_frame(mode, sev, seed), M.PITCH))
    out.update(M.shape_features(*M.shaft_points(mode, sev, seed)))
    return out


def matrix(mode: str, sev: float, n: int, seed0: int) -> np.ndarray:
    rows = [features(mode, sev, seed0 + k) for k in range(n)]
    return M.to_matrix(rows, FEATS)


def main() -> None:
    unit = matrix("正常", 1.0, N_UNIT, 10_000)
    us = spc.spc_mt_unit_space(unit)
    # 恒等式 1: 単位空間の MD² 平均 = (N−1)/N
    assert abs(us["md_sq_mean"] - (N_UNIT - 1) / N_UNIT) < 1e-9, us["md_sq_mean"]
    mu, sd, inv = us["mean"], us["std"], us["inv_corr"]

    def score(x):
        r = spc.spc_mt_distance(x, mean=mu, std=sd, inv_corr=inv)
        z = (x - mu) / sd
        return r["md"], np.abs(z).max(axis=1)

    hold = matrix("正常", 1.0, N_HOLD, 20_000)
    md_h, zmax_h = score(hold)
    thr_md = float(md_h.max())              # 健全の別標本で誤警報 0 になる閾値
    thr_z = float(zmax_h.max())             # 単変量も同じ別標本で誤警報 0 に揃えた閾値
    fa_uni = float(np.mean(zmax_h > 3.0))   # 慣習の 3σ は p=20 で偶然に鳴る(その率)
    print("単位空間 N=%d p=%d、MD² 平均 %.6f(厳密値 %.6f)、疑似逆行列=%s、平らな特徴 %d"
          % (N_UNIT, us["p"], us["md_sq_mean"], (N_UNIT - 1) / N_UNIT, us["pseudo_inverse"], us["flat_features"]))
    print("閾値(健全の別標本 %d 本で両方式とも誤警報 0): MT は MD > %.2f / 単変量は max|z| > %.2f。"
          "慣習の |z| > 3 は p=%d 特徴では偶然に %.1f %% 鳴る(同じ別標本)。"
          % (N_HOLD, thr_md, thr_z, us["p"], 100 * fa_uni))
    print()
    print("%-10s %5s | %8s %9s %8s | %s" % ("モード", "重症度", "単変量3σ", "単変量同条件", "MT法",
                                            "単変量(同条件)が『全部正常』と言った標本のうち MT が異常と言った数"))
    hidden_total = uni_silent_total = 0
    curves = {}                      # モード -> (単変量同条件の検出率, MT の検出率)
    cloud = []                       # (max|z|, MD, 隠れていたか) 全故障標本の散布
    for mode in M.FAULTS:
        curves[mode] = ([], [])
        for sev in SEVERITIES:
            x = matrix(mode, sev, N_FAULT, 30_000 + 100 * M.MODES.index(mode) + int(sev * 100))
            md, zmax = score(x)
            uni3 = zmax > 3.0
            uni = zmax > thr_z
            mt = md > thr_md
            silent = ~uni
            hidden = int(np.sum(mt & silent))
            hidden_total += hidden
            uni_silent_total += int(silent.sum())
            curves[mode][0].append(100 * uni.mean())
            curves[mode][1].append(100 * mt.mean())
            cloud.append((zmax, md, mt & silent))
            print("%-10s %5.2f | %7.1f%% %8.1f%% %7.1f%% | %d / %d"
                  % (mode, sev, 100 * uni3.mean(), 100 * uni.mean(), 100 * mt.mean(), hidden, int(silent.sum())))
    print()

    # 恒等式 2: 2 特徴の単位空間で (+z, −z) の MD² = z²/(1−ρ)。単変量は鳴らない。
    corr = us["corr"]
    iu = np.triu_indices(us["p"], 1)
    a, b = (int(v) for v in np.array(iu).T[np.argmax(corr[iu])])
    rho = float(corr[a, b])
    two = unit[:, [a, b]]
    us2 = spc.spc_mt_unit_space(two)
    z = 2.5
    pt = us2["mean"] + us2["std"] * np.array([[+z, -z]])
    r2 = spc.spc_mt_distance(pt, mean=us2["mean"], std=us2["std"], inv_corr=us2["inv_corr"])
    closed = z * z / (1.0 - rho)
    assert abs(float(r2["md_sq"][0]) - closed) < 1e-9 * max(1.0, closed), (r2["md_sq"][0], closed)
    print("構成的な例: 最も相関の強い 2 特徴 %s, %s(ρ=%.3f)で点 (+%.1fσ, −%.1fσ) —— 単変量は鳴らず、"
          "MD² = %.2f(閉形式 z²/(1−ρ) = %.2f、一致)" % (FEATS[a], FEATS[b], rho, z, z, r2["md_sq"][0], closed))
    frac = hidden_total / max(uni_silent_total, 1)

    # ---- 図 ----------------------------------------------------------------
    zs = np.concatenate([c[0] for c in cloud]); ms = np.concatenate([c[1] for c in cloud])
    hid = np.concatenate([c[2] for c in cloud])
    # 重い故障は MD 70・max|z| 200 まで飛ぶので、閾値の周辺(単変量の閾値の 2 倍・MT の 4 倍)に絞る
    xl, yl = 2.0 * thr_z, 4.0 * thr_md
    win = (zs <= xl) & (ms <= yl)
    figs.save_plot(
        "mt_hidden_cloud",
        [("故障標本", zs[win & ~hid], ms[win & ~hid]), ("単変量は正常・MT は異常", zs[win & hid], ms[win & hid]),
         ("単変量の閾値", np.array([thr_z, thr_z]), np.array([0.0, yl])),
         ("MT の閾値", np.array([0.0, xl]), np.array([thr_md, thr_md])),
         ("健全の別標本", zmax_h, md_h)],
        xlabel="max|z|(単変量が見る最大のずれ)", ylabel="MD(MT 法の距離)",
        title="どの 1 つを見ても正常範囲なのに、距離では異常", xlim=(0.0, xl), ylim=(0.0, yl),
        kinds=("scatter", "scatter", "line", "line", "scatter"),
        caption="左上の領域(単変量の閾値より左・MT の閾値より上)が「相関を見ないと失う検出」。%d 標本中 %d 本。"
                "枠の外(重い故障、%d 本)は両方式とも異常と言う。" % (uni_silent_total, hidden_total, int((~win).sum())))
    sv = np.array(SEVERITIES, float)
    slug = {"芯ずれ": "misalignment", "アンバランス": "unbalance", "軸受外輪傷": "bearing_outer",
            "潤滑不良": "lubrication", "ゆるみ": "looseness"}   # 図の名前は ASCII(URL と git のため)
    for mode in M.FAULTS:
        u, t = curves[mode]
        k = int(np.argmax(np.array(t) - np.array(u)))          # 差が最大の重症度
        figs.save_plot(
            "mt_vs_univariate_" + slug[mode],
            [("単変量(同条件)", sv, np.array(u)), ("MT 法", sv, np.array(t))],
            xlabel="重症度(正常 0 〜 故障 1 の重み)", ylabel="検出率 [%]",
            title="%s: 誤警報 0 に揃えた 2 方式の検出率" % mode, ylim=(0.0, 100.0),
            caption="%s。差が最大なのは重症度 %.2f で、単変量 %.1f %% に対し MT 法 %.1f %%。"
                    "重症度 %.2f 以上は両方式とも %.0f %%。閾値は健全の別標本 %d 本で両方式とも誤警報 0。"
                    % (mode, sv[k], u[k], t[k], sv[-1], t[-1], N_HOLD))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS: 誤警報 0 に揃えた単変量が『全特徴量とも正常範囲』と言った %d 標本のうち、MT 法は %d 標本(%.0f %%)を"
          "異常と言った。" % (uni_silent_total, hidden_total, 100 * frac))


if __name__ == "__main__":
    main()
