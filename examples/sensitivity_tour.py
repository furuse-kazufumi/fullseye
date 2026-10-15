# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sensitivity_tour — どのつまみが効くか・組でしか効かないか・データから決まるのはどれか・モデルに何が足りないか。

    py -3.11 examples/sensitivity_tour.py

【この例が示すこと】
1. **Sobol' 指数(Ishigami 関数)** —— 感度解析の標準の試験関数 f = sin x1 + 7 sin² x2 + 0.1 x3⁴ sin x1。
   x3 は単独では何もしない(S1 = 0)が、x1 との組で全分散の 24 % を動かす(ST = 0.2437)。1 つずつ振ると
   x3 は「効かない」と見落とす。推定値の 95 % 区間が解析値(Ishigami & Homma 1990)を含むことを確かめる。
2. **Morris のふるい(検査カメラ 6 条件)** —— 傷の見えに効く条件を 7 軌道 x 7 = 49 回で選り分ける。何もしない
   2 つの条件(ダミー)は「効かない」に落ち、角度は「非線形か交互作用」に入る。
3. **交絡(Brun ら 2001 の共線性指数)** —— 照明の強さ・露光・ゲインは画像を同じように明るくする。画素の感度の
   列が平行になり γ = ∞:画像から決まるのは 強さ x 露光 x ゲイン(積)だけで、1 つずつは決まらない。
   係数合わせの前にこれを言わないと、合わせた「露光」は意味の無い数になる。
4. **残差 PCA(モデルに何が足りないか)** —— 実物の画像には周辺減光(cos⁴)がある。周辺減光を知らないモデルで
   12 枚を合わせると、残差に雑音を越える構造(2 成分 —— 減光 x 像なので、角度と露光で形も大きさも変わる)が残り、
   第 1 成分の形は「減光 x 像」そのもの。モデルに入れると構造は 0 成分。

【グラウンドトゥルース】Ishigami の解析値、線形のダミーの μ* = 0、強さ・露光・ゲインの積の対称性、
cos⁴ の形(相関で比べる)。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs      # noqa: E402
import fullseye as fs          # noqa: E402  公開経路(fs.ledger.<名前>)から呼ぶ

N = 64
FULL_WELL = 4095.0


def scratch_scene(angle_deg, power, exposure_ms, gain_lin, seed=0, noise=True, vignette=0.0):
    """金属面の細い傷を撮った 12 bit 画像(doe_plan_tour と同じモデル、ゲインは倍率、周辺減光を足せる)。"""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N].astype(float)
    d = (x - y) / np.sqrt(2.0)
    h = -3.0 * np.exp(-0.5 * (d / 2.0) ** 2) + 0.05 * np.random.default_rng(0).standard_normal((N, N))
    gy, gx = np.gradient(h)
    n = np.stack([-gx, -gy, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=0)
    a = np.radians(angle_deg)
    light = np.array([np.cos(a) / np.sqrt(2), -np.cos(a) / np.sqrt(2), np.sin(a)])
    half = light + np.array([0.0, 0.0, 1.0])
    half /= np.linalg.norm(half)
    refl = 0.3 * np.clip(np.tensordot(light, n, 1), 0, None) + 0.7 * np.clip(np.tensordot(half, n, 1), 0, None) ** 40
    if vignette:
        r = np.hypot(x - N / 2, y - N / 2) / (N / 2)
        refl = refl * np.cos(np.arctan(vignette * r)) ** 4               # cos⁴ の周辺減光
    e = power * exposure_ms * 150.0 * refl
    if noise:
        e = e + np.sqrt(np.maximum(e, 0)) * rng.standard_normal((N, N)) + 2.0 * rng.standard_normal((N, N))
    dn = np.clip(e * gain_lin, 0, FULL_WELL)
    if noise:
        dn = np.round(dn)
    on, bg = np.abs(d) < 1.5, np.abs(d) > 8
    return dn, float(abs(dn[on].mean() - dn[bg].mean()) / max(dn[bg].std(), 1e-9))


def ishigami(x, a=7.0, b=0.1):
    return np.sin(x[:, 0]) + a * np.sin(x[:, 1]) ** 2 + b * x[:, 2] ** 4 * np.sin(x[:, 0])


def run() -> dict:
    t0 = time.perf_counter()
    out = {}

    # ---- 1. Sobol'(Ishigami)---------------------------------------------------- #
    a, b = 7.0, 0.1
    V = a ** 2 / 8 + b * math.pi ** 4 / 5 + b ** 2 * math.pi ** 8 / 18 + 0.5
    V1, V2, V13 = 0.5 * (1 + b * math.pi ** 4 / 5) ** 2, a ** 2 / 8, b ** 2 * math.pi ** 8 * (1 / 18 - 1 / 50)
    s1_true, st_true = np.array([V1, V2, 0.0]) / V, np.array([V1 + V13, V2, V13]) / V
    rng3 = [("x1", -math.pi, math.pi), ("x2", -math.pi, math.pi), ("x3", -math.pi, math.pi)]
    sal = fs.ledger.doe_saltelli(2 ** 12, rng3, seed=1)
    sob = fs.ledger.sens_sobol(sal, ishigami(sal["natural"]), n_boot=400, seed=0)
    print("1) Ishigami(%d 回の評価)" % sob["n_evaluations"])
    for i, nm in enumerate(sob["factors"]):
        print("   %s  S1 %.3f [%.3f, %.3f](解析 %.4f)  ST %.3f [%.3f, %.3f](解析 %.4f)"
              % (nm, sob["S1"][i], *sob["S1_ci"][i], s1_true[i], sob["ST"][i], *sob["ST_ci"][i], st_true[i]))
    inside = ((sob["S1_ci"][:, 0] <= s1_true) & (s1_true <= sob["S1_ci"][:, 1])
              & (sob["ST_ci"][:, 0] <= st_true) & (st_true <= sob["ST_ci"][:, 1]))
    assert inside.all() and np.allclose(np.round(s1_true, 4), [0.3139, 0.4424, 0]) \
        and np.allclose(np.round(st_true, 4), [0.5576, 0.4424, 0.2437])

    # ---- 2. Morris のふるい(検査カメラ)--------------------------------------------- #
    six = [("angle", 10.0, 70.0, "deg"), ("power", 0.5, 1.5, "a.u."), ("exposure", 2.0, 8.0, "ms"),
           ("gain", 1.0, 4.0, "x"), ("dummy_tilt", -2.0, 2.0, "deg"), ("dummy_temp", 20.0, 30.0, "C")]
    mo = fs.ledger.doe_morris(7, six, levels=4, seed=5, n_candidates=100)
    nm_ = fs.ledger.doe_decode(mo)
    ym = np.array([scratch_scene(r[0], r[1], r[2], r[3], seed=0)[1] for r in nm_])
    sm = fs.ledger.sens_morris(mo, ym)
    print("2) Morris %d 回: " % len(ym) + " / ".join("%s μ*=%.2f σ=%.2f(%s)" % (f, m, s, c) for f, m, s, c
                                                    in zip(sm["factors"], sm["mu_star"], sm["sigma"], sm["class"])))
    assert sm["class"][4] == sm["class"][5] == "negligible" and sm["ranking"][0] == "angle"

    # ---- 3. 交絡(画素の感度の列)------------------------------------------------- #
    base = dict(angle=30.0, power=1.0, exposure=4.0, gain=2.0)
    names = ["angle", "power", "exposure", "gain"]

    def img(p):
        return scratch_scene(p["angle"], p["power"], p["exposure"], p["gain"], noise=False)[0].ravel()

    f0 = img(base)
    assert f0.max() < FULL_WELL                                      # 基点は飽和していない(線形の範囲)
    cols = []
    for k in names:                                                  # 対数の感度 d image / d log θ(相対で 1 %)
        hi, lo = dict(base), dict(base)
        hi[k] *= 1.01
        lo[k] /= 1.01
        cols.append((img(hi) - img(lo)) / (2 * math.log(1.01)))
    S = np.column_stack(cols) / f0.std()
    conf = fs.ledger.mv_confounding(S, names, log_params=True)
    grp = conf["confounded_groups"][0] if conf["confounded_groups"] else None
    print("3) 共線性指数 γ(4 つ全部)= %s、交絡の組 %s" % (conf["gamma_full"], [p for p, _g in conf["confounded_pairs"]]))
    if grp:
        print("   組 %s: 決まる %s / 決まらない %s / 1 つずつ決まる %s"
              % (grp["parameters"], grp["determined"][:1], grp["undetermined"], conf["determined_individually"]))
    assert grp is not None and set(grp["parameters"]) == {"power", "exposure", "gain"}
    det = grp["determined"][0]
    assert all(("%s^1" % k) in det for k in ("power", "exposure", "gain")), det
    assert conf["determined_individually"] == ["angle"]

    # ---- 4. 残差 PCA(モデルに何が足りないか)----------------------------------------- #
    lh = fs.ledger.doe_lhs(12, [("angle", 20.0, 60.0, "deg"), ("exposure", 2.0, 6.0, "ms")], seed=3)
    runs = fs.ledger.doe_decode(lh)
    real = np.stack([scratch_scene(a_, 1.0, e_, 2.0, seed=10 + i, vignette=0.6)[0].ravel()
                     for i, (a_, e_) in enumerate(runs)])
    sim_naive = np.stack([scratch_scene(a_, 1.0, e_, 2.0, noise=False)[0].ravel() for a_, e_ in runs])
    sim_full = np.stack([scratch_scene(a_, 1.0, e_, 2.0, noise=False, vignette=0.6)[0].ravel() for a_, e_ in runs])
    # 残差は雑音の大きさで割って標準化する(光子雑音は明るい画素ほど大きい: σ_DN = ゲイン x sqrt(電子 + 読み出し²))。
    # 割らないと「明るい回は残差も大きい」が構造に見える。雑音モデルはモデル側の明るさから(実物の値は使わない)。
    sd_naive = 2.0 * np.sqrt(sim_naive / 2.0 + 4.0)
    sd_full = 2.0 * np.sqrt(sim_full / 2.0 + 4.0)
    res_naive = (real - sim_naive) / sd_naive
    res_full = (real - sim_full) / sd_full
    rp_naive = fs.ledger.mv_residual_pca(res_naive, noise_sigma=1.0)
    rp_full = fs.ledger.mv_residual_pca(res_full, noise_sigma=1.0)
    missing = ((sim_full - sim_naive) / sd_naive).mean(axis=0)        # 足りないもの(周辺減光 x 像)の平均の形
    corr = abs(float(np.corrcoef(rp_naive["loadings"][:, 0], missing)[0, 1])) if rp_naive["n_structural"] else 0.0
    sigma_noise = 1.0
    print("4) 残差 PCA(雑音で標準化、Marchenko-Pastur の端): 周辺減光を知らないモデル → 構造 %d 成分(残差の"
          "エネルギーの %.0f%%、足りないものの形との相関 %.2f)/ 知っているモデル → %d 成分(雑音 σ = %.0f)"
          % (rp_naive["n_structural"], 100 * rp_naive["structural_energy_share"], corr, rp_full["n_structural"], sigma_noise))
    assert rp_naive["n_structural"] >= 1 and corr > 0.8 and rp_full["n_structural"] == 0

    # ---- 図 ---------------------------------------------------------------------- #
    if figs.enabled():
        xs = np.arange(3)
        figs.save_plot("sobol_ishigami",
                       [("S1(推定)", xs - 0.1, sob["S1"]), ("ST(推定)", xs + 0.1, sob["ST"]),
                        ("S1 の解析値", xs - 0.1, s1_true), ("ST の解析値", xs + 0.1, st_true)]
                       + [("", [i - 0.1, i - 0.1], list(sob["S1_ci"][i])) for i in range(3)]
                       + [("", [i + 0.1, i + 0.1], list(sob["ST_ci"][i])) for i in range(3)],
                       kinds=["scatter", "scatter", "scatter", "scatter"] + ["line"] * 6,
                       colors=["emphasis", "right", "reference", "reference"] + ["emphasis"] * 3 + ["right"] * 3,
                       xlim=(-0.5, 2.5), ylim=(-0.05, 0.7),
                       xlabel="x1(0)/ x2(1)/ x3(2)", ylabel="分散の割合",
                       title="x3 は単独では 0、組では 24 % —— Sobol' の S1 と ST(縦線 = 95 % 区間)",
                       caption="Ishigami 関数(a = 7, b = 0.1)を %d 回評価(Saltelli 2010 の A・B・A_B 行列、Sobol' 列)。"
                               "S1 = 単独の寄与、ST = 交互作用を含めた寄与。x3 は x1 との積の項でしか効かないので S1 = 0・"
                               "ST = 0.2437。解析値(Ishigami & Homma 1990)はどれも 95 %% 区間の中。" % sob["n_evaluations"])
        role = ["emphasis", "neutral", "right", "wrong", "reference", "reference"]
        figs.save_plot("morris_screen",
                       [("%s(%s)" % (f, c), [m], [s]) for f, m, s, c in
                        zip(sm["factors"], sm["mu_star"], sm["sigma"], sm["class"])]
                       + [("σ = μ*", [0, sm["mu_star"].max()], [0, sm["mu_star"].max()])],
                       kinds=["scatter"] * 6 + ["line"], styles=[None] * 6 + ["dashed"], colors=role + ["neutral"],
                       xlim=(-0.05 * sm["mu_star"].max(), 1.15 * sm["mu_star"].max()),
                       ylim=(-0.05 * sm["mu_star"].max(), 1.15 * sm["mu_star"].max()),
                       xlabel="μ*(効きの大きさ、範囲全体あたりの見えの変化)", ylabel="σ(場所によって効きが変わる度合い)",
                       title="Morris のふるい —— 49 回で 6 条件を選り分ける",
                       caption="右ほど効く、上ほど他の条件しだいで効き方が変わる(非線形か交互作用)。何もしない 2 条件"
                               "(dummy)は原点に落ちる。角度は効きが大きく、σ も大きい。ゲインもほぼ 0 —— 信号と雑音を同じ倍率で"
                               "増やすだけで光子は増えないから(強さと露光は光子を増やすので効く)。")
        if grp:
            ang = np.degrees(np.arccos(np.clip(np.corrcoef(S.T), -1, 1)))
            figs.save_table("confounding", ["", *names],
                            [[n1, *["%.1f°" % ang[i, j] for j in range(4)]] for i, n1 in enumerate(names)],
                            title="感度の列どうしの角度(0° = 区別できない)",
                            caption="強さ・露光・ゲインの感度の列は互いに 0°(平行)。共線性指数 γ = ∞、雑音の無い画像から"
                                    "決まるのは %s(積)だけ。角度だけは 1 つで決まる。ゲインと光子を分けるのは雑音の統計"
                                    "(光子伝達曲線、EMVA 1288)の側。" % det)
        load = rp_naive["loadings"][:, 0].reshape(N, N) if rp_naive["n_structural"] else np.zeros((N, N))
        figs.save_grid("residual_structure",
                       [real[0].reshape(N, N) / FULL_WELL, res_naive[0].reshape(N, N), load,
                        res_full[0].reshape(N, N)],
                       captions=["実物(周辺減光あり)", "残差(減光を知らない)", "残差 PCA の第 1 成分", "残差(減光を入れた)"],
                       signed=[False, True, True, True], gray=[True, False, False, False], ncols=4,
                       title="残差に残った形は、モデルに足りないもの",
                       caption="12 枚の残差の PCA(雑音で割って標準化、Marchenko-Pastur の端)。周辺減光を知らないモデルでは %d 成分が雑音の上に出て、第 1 成分の"
                               "形は「周辺減光 x 像」と相関 %.2f。モデルに入れると構造は 0 成分 —— 残差は雑音だけ。"
                               "残差は雑音の大きさ(光子雑音 + 読み出し雑音)で割ってから見る。" % (rp_naive["n_structural"], corr))
    assert not figs.errors(), figs.errors()

    out["sobol_inside_ci"] = bool(inside.all())
    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  sensitivity_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
