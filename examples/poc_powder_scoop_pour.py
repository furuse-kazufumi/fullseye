# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""粉体のすくいと注ぎを画像で測る —— スプーンですくった量を側面像の輪郭から、傾けて注いだ流量を流れの幅と速さから、
規則だけで(2026-10-05)。

物理シミュ × Fullseye 系列で granular(山の安息角・体積・Beverloo 排出)の続き。先行研究の粉体計量
(Kadokawa, Hamaya, Tanaka, IROS 2023, doi 10.1109/iros55552.2023.10342463)は秤の質量だけを観測に使う。ここは
**横から見た像** から、すくった量(体積 → 粒の数)と注ぎの流量(PIV の速さ × Boolean 模型で数えた粒の線密度)を読む
新モジュール scoop(15 op + mujoco の facade 2)を学習なしで組む。外から来る真値:
  * **閉形式**: 球冠の椀のすり切り V = π h (3a² + h²)/6、山盛り = 縁の上の安息角の円錐 (π/3) a³ tan φ(granular の
    heap_volume_cone と一致)、自由落下 v = √(v₀² + 2 g s)。
  * **確率幾何の標準結果**: 位置が独立な円板の和の被覆率 c = 1 − exp(−n π r²)(Boolean 模型)。合成器はこの式を使わない。
  * **体素の真値**: 縦長の楕円錐(1.6 : 1)を体素で数えた体積(回転体の仮定が外れる被験者)。
  * **第 2 実装(--full)**: MuJoCo の剛体球 —— 球冠の椀(薄板 118 枚)にすくった球の **個数**、口の開いた樋を傾けて
    こぼれた球が線を **横切った数**(流量の真値)。

門(既定 15 本 + --full 10 本)。図(既定の出力先は out/figures/<PoC 名>/、FULLSEYE_FIGURE_DIR で変更): 4 つの状態の
スプーンの側面像に閉形式の輪郭と読んだ体積(等倍)、楕円錐の 2 方向、**流れの GIF(PIV の速さ)**、高さごとの速さと
自由落下、Boolean 模型と素朴な数え方、傾けて出る割合の 2 つの模型、画像で足りるかの帯; --full: MuJoCo のすくい 3 量、
**注ぎの GIF**、出た割合(数 vs 模型 vs 画像)、流量の時系列(画像 vs 横切り数)、外の真値との表。
正直に: 合成の側面像と回転体の読みは同じ軸対称の模型なので往復は配管の検査(独立な被験者は楕円錐の体素と MuJoCo)。
MuJoCo の充填率は 1 回で較正する(輪郭が粒の外側の包絡なので、充填そのものは分からない)。傾けて出る割合の模型は
**φ を当てはめた** 比較で、口の楔の導出は口に縁のある器(granular の lip="wall")よりよく合うが、奥の平らな層は実際には流れて
薄くなる(斜面の流れの h_stop 型の挙動、一次情報は未読で模型に入れていない)。Beverloo は桁の照合だけ。
Run: py -3.11 examples/poc_powder_scoop_pour.py [--full]        (--full は mujoco)
"""
from __future__ import annotations

import math
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import annotate as AN  # noqa: E402
import examplefig as figs  # noqa: E402
import granular as G  # noqa: E402
import scoop as S  # noqa: E402

FULL = "--full" in sys.argv
_GATES: list[tuple[str, bool]] = []


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    except Exception as exc:  # noqa: BLE001  別の例外は fail-closed ではない
        print("    (wrong exception %s: %s)" % (type(exc).__name__, exc))
        return False
    return False


# ======================================================================================================================
# 図の道具(numpy だけ)
# ======================================================================================================================
def _rgb(cov):
    g = np.clip(np.asarray(cov, float), 0, 1)
    return np.stack([0.10 + 0.78 * g, 0.10 + 0.70 * g, 0.12 + 0.52 * g], axis=-1)


def _line(img, p0, p1, color, width=1.5, dash=0):
    """(row, col) の 2 点を結ぶ太線。``dash`` > 0 なら dash 画素ごとに描く / 抜くを繰り返す。"""
    (r0, c0), (r1, c1) = p0, p1
    n = int(max(abs(r1 - r0), abs(c1 - c0)) * 2) + 2
    rr, cc = np.linspace(r0, r1, n), np.linspace(c0, c1, n)
    h, w = img.shape[:2]
    k = int(math.ceil(width))
    for t, (r, c) in enumerate(zip(rr, cc)):
        if dash and (t // (2 * dash)) % 2 == 1:
            continue
        for dr in range(-k, k + 1):
            for dc in range(-k, k + 1):
                if dr * dr + dc * dc <= width * width:
                    i, j = int(round(r)) + dr, int(round(c)) + dc
                    if 0 <= i < h and 0 <= j < w:
                        img[i, j] = color
    return img


def _polyline(img, pts, color, width=1.0, dash=0):
    assert len(pts) >= 2
    for p, q in zip(pts[:-1], pts[1:]):
        _line(img, p, q, color, width, dash)
    return img


def _text(img, s, xy, fs=16, anchor="lt"):
    try:
        return np.asarray(AN.text_box(img, s, xy, anchor=anchor, font_size=fs), dtype=np.float64)
    except Exception as exc:  # noqa: BLE001  文字が収まらない等は図を落とさず素の絵(理由は errors に残る)
        figs._errors.append("text_box: %r" % (exc,))
        return img


def _pad_to(frames, h, w):
    out = []
    for f in frames:
        pad = np.empty((h, w, 3))
        pad[:] = (0.10, 0.10, 0.12)
        pad[:f.shape[0], :f.shape[1]] = f[:h, :w]
        out.append(pad)
    return out


def _wedge_synth(theta_deg, L_px, h0_px, phi_deg, lip_rc, shape, ss=4):
    """傾いた器の中の口の楔の断面(器の座標で y ≤ min(h₀, x tan(φ−θ)))を世界の像に描いた被覆率(副標本)。"""
    rows, cols = shape
    c, s = math.cos(math.radians(theta_deg)), math.sin(math.radians(theta_deg))
    t = math.tan(math.radians(phi_deg - theta_deg))
    yy, xx = np.mgrid[0:rows * ss, 0:cols * ss].astype(np.float64)
    yy, xx = (yy + 0.5) / ss, (xx + 0.5) / ss
    dx, up = xx - lip_rc[1], lip_rc[0] - yy
    xf, yf = dx * c + up * s, -dx * s + up * c
    m = (xf >= 0) & (xf <= L_px) & (yf >= 0) & (yf <= np.minimum(h0_px, xf * t))
    return m.reshape(rows, ss, cols, ss).mean(axis=(1, 3))


# ======================================================================================================================
def numpy_part() -> dict:
    print("== 1. numpy の門(閉形式・合成・体素・Boolean 模型)")
    t0 = time.perf_counter()
    out = {}
    # 門 1 すり切りの閉形式 vs 体素
    a, h = 1.0, 0.4
    g = S.spoon_bowl_volume(a, h, fill_depth=h, phi_deg=30.0)
    n = 300
    x = (np.arange(n) + 0.5) / n * 2 * a - a
    X, Y = np.meshgrid(x, x)
    rr2 = X * X + Y * Y
    zz = (np.arange(n) + 0.5) / n * h
    cnt = sum(int(np.sum(rr2 <= max(g["R"] ** 2 - (g["R"] - z) ** 2, 0.0))) for z in zz)
    Vvox = cnt * (2 * a / n) ** 2 * (h / n)
    gcone = G.heap_volume_cone(R=a, phi_deg=30.0)["V"]
    gate("門 1 すり切りの閉形式 vs 体素の数え上げ、満杯の恒等式、山盛り = granular の円錐",
         abs(Vvox / g["V_struck"] - 1) < 1e-3 and abs(g["V_fill"] - g["V_struck"]) < 1e-12 and abs(g["V_heap"] - gcone) < 1e-12
         and _raises(S.spoon_bowl_volume, 1.0, 1.2) and _raises(S.spoon_bowl_volume, 1.0, 0.4, fill_depth=0.5),
         "V = πh(3a²+h²)/6 = %.6f、体素 300² × 300 で %.6f(%+.1e)、V_fill(h) − V_struck = %.1e、山盛り %.6f = granular %.6f;"
         " 半球より深い椀と満杯を超える深さは ValueError" % (g["V_struck"], Vvox, Vvox / g["V_struck"] - 1, g["V_fill"] - g["V_struck"], g["V_heap"], gcone))
    # 門 2 合成の側面像 → 体積(5 状態)
    states = ((0.4, 0.0), (0.7, 0.0), (1.0, 0.0), (1.0, 0.5), (1.0, 1.0))
    errs, errs_n, disc = [], [], []
    syn = []
    for fill, hf in states:
        w = S.scoop_synth_side(120, 48, fill=fill, heap_frac=hf, phi_deg=30.0)
        v = S.revolution_volume_side(w["side"], w["pitch"])
        wn = S.scoop_synth_side(120, 48, fill=fill, heap_frac=hf, phi_deg=30.0, noise=0.1, seed=1)
        vn = S.revolution_volume_side(wn["side"], wn["pitch"])
        errs.append(v["V"] / w["truth"]["V"] - 1)
        errs_n.append(vn["V"] / w["truth"]["V"] - 1)
        disc.append(v["V_discs"] / w["truth"]["V"] - 1)
        syn.append((w, v))
    assert len(errs) == len(states)
    gate("門 2 合成の側面像 → 回転体の体積(Pappus、5 状態、雑音 ±0.1)",
         max(map(abs, errs)) < 0.006 and max(map(abs, errs_n)) < 0.006 and min(disc) < -0.01,
         "雑音なし %s、雑音 ±0.1 %s(門 0.6 %%; 合成と読みが同じ軸対称の模型 = 配管の検査)。行の幅を直径にした円板の和は途中まで満たした椀で %s"
         "(平らな面が行を横切ると f² で数え落とす罠 → Pappus の線形和に直した)"
         % ([round(e * 100, 2) for e in errs], [round(e * 100, 2) for e in errs_n], [round(e * 100, 2) for e in disc[:2]]))
    out["syn"] = syn
    # 門 3 不透明の椀(縁の上 + 閉形式)と透明な椀の深さ
    wh = syn[4][0]
    rd = S.scoop_volume_read(wh["side_above"], wh["rim_row"], 120, 48, wh["pitch"])
    wl = syn[2][0]
    rl = S.scoop_volume_read(wl["side_above"], wl["rim_row"], 120, 48, wl["pitch"], assume_level=True)
    wu = syn[0][0]
    ru = S.scoop_volume_read(wu["side"], wu["rim_row"], 120, 48, wu["pitch"], opaque=False)
    gate("門 3 金属の椀は縁の上だけ見える: V = すり切り + 縁の上、見えなければ ValueError、透明な椀の深さは閉形式の逆",
         abs(rd["V"] / wh["truth"]["V"] - 1) < 2e-3 and rd["state"] == "heaped" and abs(rd["heap_angle_deg"] - 30.0) < 0.2
         and _raises(S.scoop_volume_read, wl["side_above"], wl["rim_row"], 120, 48, wl["pitch"])
         and abs(rl["V"] / wl["truth"]["V"] - 1) < 1e-9 and ru["state"] == "under" and abs(ru["fill_depth_px"] - 0.4 * 48) < 0.5,
         "山盛りの読み %+.2f %%、山の斜面 %.2f 度(真値 30)、縁の上が空なら「すり切りか足りないかは横から分からない」で拒否、"
         "assume_level で閉形式そのもの; 透明な椀 40 %% の深さ %.2f px(真値 19.2)"
         % ((rd["V"] / wh["truth"]["V"] - 1) * 100, rd["heap_angle_deg"], ru["fill_depth_px"]))
    # 門 4 2 方向 vs 楕円錐の体素
    ax_, by_, H = 60.0, 96.0, 70.0
    rows, cols, ss = int(H) + 10, 2 * int(by_) + 20, 4
    zc = np.arange(rows * ss)[::-1] / ss + 0.5 / ss - 5

    def _sil(semi):
        xs = (np.arange(cols * ss) + 0.5) / ss - cols / 2
        Z = zc[:, None]
        m = (Z >= 0) & (Z <= H) & (np.abs(xs[None, :]) <= semi * (1 - np.clip(Z, 0, H) / H))
        return m.reshape(rows, ss, cols, ss).mean(axis=(1, 3))

    sx, sy = _sil(ax_), _sil(by_)
    # 体素の真値(独立): 0.5 px の格子で楕円錐の中の点を数える
    gx = (np.arange(int(4 * by_)) + 0.5) * 0.5 - by_
    GX, GY = np.meshgrid(gx, gx)
    q = (GX / ax_) ** 2 + (GY / by_) ** 2
    zv = (np.arange(int(2 * H)) + 0.5) * 0.5
    Vvox = sum(int(np.sum(q <= (1 - z / H) ** 2)) for z in zv) * 0.125
    tv = S.two_view_volume(sx, sy, 1.0)
    gate("門 4 縦長の盛り(楕円錐 1.6 : 1)を 2 方向から: 体素の真値と一致、片方だけの回転体は外れる",
         abs(tv["V"] / Vvox - 1) < 5e-3 and tv["V_a"] / Vvox - 1 < -0.3 and tv["V_b"] / Vvox - 1 > 0.5,
         "2 方向 %+.2f %%(体素 0.5 px で %.0f px³、閉形式 πabH/3 = %.0f)、片方だけ %+.1f %% / %+.1f %%(扁平さ %.2f)"
         % ((tv["V"] / Vvox - 1) * 100, Vvox, math.pi * ax_ * by_ * H / 3, (tv["V_a"] / Vvox - 1) * 100, (tv["V_b"] / Vvox - 1) * 100, tv["ellipticity"]))
    out["ell"] = (sx, sy, tv, Vvox)
    # 門 5〜7 流れ(合成)
    bands = [40, 96, 152]
    res = {}
    for q_ in (400, 3000):
        st = S.stream_synth(q_, 1e-3, 8e-3, n_frames=32, seed=3)
        f = S.stream_flux_read(st["frames"], st["dt"], st["truth"]["radius_px"], band_rows=bands, particle_mass=1.3e-5)
        res[q_] = (st, f)
    verr = max(float(np.max(np.abs(f["v"] * st["pitch"] / st["truth"]["v"][bands] - 1))) for st, f in res.values())
    gate("門 5 流れの速さ(PIV、全コマ対の中央値)vs 自由落下 √(v₀² + 2gs)", verr < 0.02,
         "最大 %.2f %%(門 2 %%; 2 つの流量 × 3 高さ、窓 32 px、0.5 mm/px、1.5 ms/コマ)" % (verr * 100))
    st, f = res[3000]
    tr = st["truth"]["crossings"][bands]
    st1, f1 = res[400]
    tr1 = st1["truth"]["crossings"][bands]
    rb = f["flux"] / tr
    rn = f["flux_naive"] / tr
    gate("門 6 流量 = PIV の速さ × Boolean 模型の線密度 vs 実現した横切り数(合成器は模型の式を使わない)",
         float(np.max(np.abs(rb - 1))) < 0.08 and abs(float(np.mean(f1["flux"] / tr1)) - 1) < 0.08 and float(np.max(rn)) < 0.8,
         "密な流れ(被覆率 最大 %.2f)%s、薄い流れ %s(門 8 %%); 素朴な c/(πr²) は密な流れで %s(重なりで数え落とす)"
         % (f["c_max_seen"], np.round(rb, 3).tolist(), np.round(f1["flux"] / tr1, 3).tolist(), np.round(rn, 2).tolist()))
    gate("門 7 流量の連続(3 つの高さで同じ粒の数 / 秒、流れは落ちるほど薄くなる)",
         all(ff_["flux_spread"] < 2.0 * float(np.max(ff_["rel_err_poisson"])) for ff_ in (f, f1)),
         "帯の間の (max − min)/平均 = 密 %.3f・薄 %.3f、どちらも数え上げの揺らぎ(±%.0f %% / ±%.0f %%)の 2 倍以内; 線密度は %s 個/px と"
         "落ちるほど減り、速さが補う" % (f["flux_spread"], f1["flux_spread"], 100 * float(np.max(f["rel_err_poisson"])),
                                    100 * float(np.max(f1["rel_err_poisson"])), np.round(f["lam"], 3).tolist()))
    out["stream"] = res
    # 門 8 傾けの導出: 微分と積分の恒等式、granular の近似との差
    L, h0, phi = 0.08, 0.02, 30.0
    r0 = S.tilt_wedge_retained(0.0, phi, L, h0)
    nmid = 1200                                                # 中点則(θ = φ で流量が 0 に落ちる端を跨がない)
    ths = (np.arange(nmid) + 0.5) * phi / nmid
    rates = np.array([S.tilt_pour_rate(t, 10.0, phi, L, h0, 0.03, 1500.0)["rate"] for t in ths])
    tot = float(rates.sum() * (phi / nmid) / 10.0)
    eps = 1e-4
    dmax = 0.0
    for t in (3.0, 12.0, 25.0):
        num = (S.tilt_wedge_retained(t - eps, phi, L, h0)["A"] - S.tilt_wedge_retained(t + eps, phi, L, h0)["A"]) / math.radians(2 * eps)
        an = S.tilt_pour_rate(t, 10.0, phi, L, h0, 0.03, 1500.0)["rate_area"] / math.radians(10.0)
        dmax = max(dmax, abs(num / an - 1))
    Fs = [S.tilt_wedge_retained(t, phi, L, h0)["fraction"] for t in np.linspace(0.0, phi, 61)]
    m5 = S.tilt_wedge_retained(5.0, phi, L, h0)
    gate("門 8 傾けて出る量(口の楔の導出): dA/dθ の閉形式 = 数値微分、∫流量 dt = 初めの量、F(0) = 0・F(φ) = 1・単調",
         dmax < 1e-6 and abs(tot / (r0["A0"] * 0.03 * 1500.0) - 1) < 1e-5 and Fs[0] == 0.0 and abs(Fs[-1] - 1) < 1e-12
         and all(b >= a_ - 1e-15 for a_, b in zip(Fs, Fs[1:])),
         "微分 %.1e、積分 %+.1e; θ = 5 度で口の楔 %.3f 対 口に縁のある器 %.3f(後者は θ_c = %.2f 度までこぼれない)"
         % (dmax, tot / (r0["A0"] * 0.03 * 1500.0) - 1, m5["fraction"], m5["F_lip_wall"], m5["theta_c_lip_wall_deg"]))
    out["tilt"] = (L, h0, phi)
    # 門 9 傾いた器の像 → 断面積
    shape, lip = (150, 250), (120.0, 30.0)
    e9 = []
    for th in (0.0, 8.0, 16.0, 24.0):
        sim = _wedge_synth(th, 200.0, 45.0, 32.0, lip, shape)
        rdt = S.tilted_surface_read(sim, lip[0], lip[1], th, 200.0, wall_px=90.0)
        exact = G._tilt_wedge_area(math.tan(math.radians(32.0 - th)), 200.0, 45.0)
        e9.append(rdt["area_px"] / exact - 1)
    assert len(e9) == 4
    gate("門 9 傾いた器の側面像 → 器の中の断面積(器の座標に直して数える)vs 閉形式 ∫min(h₀, x tan(φ−θ))dx",
         max(map(abs, e9)) < 5e-3, "θ = 0 / 8 / 16 / 24 度で %s %%(門 0.5 %%)" % [round(e * 100, 3) for e in e9])
    # 門 10 画像で足りるか
    big = S.scoop_image_limit(0.03, 1e-4, 0.5e-3, 800.0, h=0.015)
    mg = S.scoop_image_limit(0.03, 1e-4, 0.5e-3, 800.0, h=0.015, target_mass=10e-6)
    few = S.scoop_image_limit(0.03, 1e-4, 3.5e-3, 1500.0, h=0.012)
    gate("門 10 画像で足りるか(規則): 山盛り 31 g は画像、10 mg は秤、粒が少ない(a/d < 5)は秤",
         big["verdict"] == "image" and mg["verdict"] == "scale" and few["verdict"] == "scale",
         "31 g の椀 %.1f %% → %s; 10 mg に縮めた椀(縁の半径 %.1f mm)%.0f %% → %s; 3.5 mm の粒 a/d = %.1f → %s"
         % (big["rel_err"] * 100, big["verdict"], mg["a_for_target"] * 1e3, mg["rel_err_target"] * 100, mg["verdict"], few["a_over_d"], few["verdict"]))
    out["limit"] = (big, mg, few)
    # 門 11 壊れる場所: 粒が少ない流れ、飽和
    stf = S.stream_synth(60, 1e-3, 8e-3, n_frames=32, seed=3)
    ff = S.stream_flux_read(stf["frames"], stf["dt"], stf["truth"]["radius_px"], band_rows=bands)
    st0 = S.stream_synth(20, 1e-3, 8e-3, n_frames=32, seed=3)
    std = S.stream_synth(9000, 1e-3, 8e-3, n_frames=8, seed=3)
    gate("門 11 壊れる場所: 粒が少ないと数え上げの揺らぎ(reliable=False)、さらに少ないと PIV が立たず ValueError、密すぎると飽和で ValueError",
         (not ff["reliable"]) and res[3000][1]["reliable"]
         and _raises(S.stream_flux_read, st0["frames"], st0["dt"], st0["truth"]["radius_px"], band_rows=bands)
         and _raises(S.stream_flux_read, std["frames"], std["dt"], std["truth"]["radius_px"], band_rows=bands),
         "60 個/s: 帯を横切った推定 %s 個(±%s %%)→ reliable=False(3000 個/s は %s 個で True); 20 個/s は PIV の窓が立たない; 9000 個/s は被覆率 0.95 超"
         % (np.round(ff["n_crossed_est"], 1).tolist(), np.round(100 * ff["rel_err_poisson"]).tolist(), np.round(res[3000][1]["n_crossed_est"]).tolist()))
    out["few"] = (stf, ff)
    # 門 12 綴り壊しと引数の範囲
    gate("門 12 綴り壊しと引数の範囲 → ValueError",
         _raises(S.stream_areal_density, np.full(5, 0.3), 2.0, mode="clipp") and _raises(S.scoop_scene_mjcf, 10, cone="eliptic")
         and _raises(S.pour_scene_mjcf, solver="CGG") and _raises(S.scoop_synth_side, 100, 40, fill=0.5, heap_frac=0.3)
         and _raises(S.two_view_volume, np.zeros((10, 10)), np.zeros((12, 10)), 1.0) and _raises(S.tilt_wedge_retained, 95.0, 30.0, 1.0, 0.1)
         and _raises(S.scoop_count, 1.0, 1.0, 1.5) and _raises(S.revolution_volume_side, np.zeros((8, 8)), 1.0),
         "mode / cone / solver の綴り違い、山なのに満たしていない、行数の違う 2 方向、θ ≥ 90、充填率 > 1、空の像")
    # 門 13 MJCF 文字列(mujoco 不要)
    sc = S.scoop_scene_mjcf(150)
    pc = S.pour_scene_mjcf()
    gate("門 13 MJCF 文字列(mujoco 不要): 椀の薄板と球の数、樋は mocap、contact_tc < 2 timestep は拒否",
         sc["xml"].count("<freejoint/>") == 150 and sc["info"]["n_tiles"] == sc["xml"].count('type="box"') and 'mocap="true"' in pc["xml"]
         and pc["xml"].count("<freejoint/>") == pc["info"]["n"] and _raises(S.scoop_scene_mjcf, 10, contact_tc=0.002)
         and _raises(S.pour_scene_mjcf, h0=0.05, wall=0.04),
         "椀の板 %d 枚・球 150、樋の球 %d(4 層の千鳥)" % (sc["info"]["n_tiles"], pc["info"]["n"]))
    # 門 14 入口の棚卸し
    src = Path(S.__file__).read_text(encoding="utf-8")
    docs_ok = all("](" not in (getattr(S, nm).__doc__ or "") for nm in S.__all__)
    gate("門 14 入口: __all__ の全部が実在、docstring に ']( ' が無い、acos を使わない、ローカルパスを書かない",
         all(callable(getattr(S, nm, None)) for nm in S.__all__) and docs_ok and "acos" not in src and not re.search(r"[A-Za-z]:[\\/](Users|dev)", src),
         "%d 本" % len(S.__all__))
    dt = time.perf_counter() - t0
    # ★2026-10-07: 共有ランナーでは同じ計算が手元の数倍かかる(poc_reproducible_icp で 6 s → 41〜57 s)。
    #   CI(py3.10)で 5.33 s になり落ちた。主張は手元の 5 s、CI は 8 倍の枠で「桁が変わっていない」だけを見る。
    budget = 40.0 if __import__("os").environ.get("GITHUB_ACTIONS") else 5.0
    gate("門 15 既定の門の所要 ≤ %g s" % budget, dt <= budget, "%.2f s(手元の主張は ≤ 5 s)" % dt)
    return out


# ======================================================================================================================
def _render_fill(pos, r, a, zb, pitch, ext, z0, height):
    Q = pos.copy()
    Q[:, 2] -= z0
    sx = G.spheres_to_silhouette(Q, r, pitch, ext, height)
    sy = G.spheres_to_silhouette(Q[:, [1, 0, 2]], r, pitch, ext, height)
    return sx, sy, Q


def full_part(out: dict) -> dict:
    print("== 2. MuJoCo の門(剛体球のすくいと注ぎ = 第 2 実装)")
    t0 = time.perf_counter()
    a, h, zr = 0.03, 0.012, 0.10
    zb = zr - h
    fills = {}
    for r, ns in ((0.002, (150, 330, 600)), (0.0035, (28, 62, 112))):
        for n in ns:
            for seed in (0, 1):
                run = S.scoop_mujoco_fill(n, r, a=a, h=h, rim_height=zr, duration=1.2, seed=seed)
                pitch, ext, z0, height = 0.25e-3, a + 0.008, zb - 0.002, 0.04
                sx, sy, Q = _render_fill(run["pos"], r, a, zb, pitch, ext, z0, height)
                tv = S.two_view_volume(sx, sy, pitch)
                rim_row = int(round((height - (zr - z0)) / pitch))
                vp = 4.0 / 3.0 * math.pi * r ** 3
                fills[(r, n, seed)] = {"run": run, "sx": sx, "sy": sy, "tv": tv, "nu_eff": run["n_retained"] * vp / tv["V"],
                                       "rim_row": rim_row, "pitch": pitch, "ext": ext, "z0": z0, "height": height, "Q": Q}
    # 門 16 すくった粒の数(r = 2 mm): 較正 1 回 → 他 5 本
    def _errs(r, n_cal):
        nu = fills[(r, n_cal, 0)]["nu_eff"]
        e = {}
        for (rr_, n, seed), d in fills.items():
            if rr_ != r or (n == n_cal and seed == 0):
                continue
            vp = 4.0 / 3.0 * math.pi * r ** 3
            Nimg = S.scoop_count(d["tv"]["V"], r, nu)["N"]
            e[(n, seed)] = Nimg / d["run"]["n_retained"] - 1
        return nu, e

    nu2, e2 = _errs(0.002, 330)
    assert len(e2) == 5
    gate("門 16 すくった粒の数(半径 2 mm、縁 30 mm): 充填率を 1 回(330 個)で較正 → 他の 5 本(150 / 600 個 × seed)の 2 方向の像 vs MuJoCo の個数",
         max(map(abs, e2.values())) < 0.05 and all(fills[k]["run"]["n_retained"] == k[1] for k in fills if k[0] == 0.002),
         "較正 ν = %.3f(輪郭は粒の外側の包絡なので充填より小さい); 誤差 %s(門 5 %%)。量が多いほど ν が上がる系統(自由表面の殻の割合)"
         % (nu2, {"%d/s%d" % k: round(v * 100, 1) for k, v in e2.items()}))
    # 門 17 金属の椀の読み(縁の上 + 閉形式)vs 2 方向
    eo, rf = [], []
    for n in (330, 600):
        d = fills[(0.002, n, 0)]
        rd = S.scoop_volume_read(d["sx"], d["rim_row"], a / d["pitch"], h / d["pitch"], d["pitch"], fit_angle=False)
        eo.append(rd["V"] / d["tv"]["V"] - 1)
        rf.append((rd["heap_base_frac"], rd["rim_full"]))
    gate("門 17 金属の椀として読む(縁より下は見えない: すり切りの閉形式 + 縁の上の回転体)vs 2 方向の像; 山の裾が縁に届かないと旗",
         abs(eo[1]) < 0.03 and rf[1][1] and (not rf[0][1]) and eo[0] > 0.0,
         "600 個(裾 %.2f、rim_full)%+.1f %%(門 3 %%); 330 個(裾 %.2f = 山になりかけ、rim_full=False)%+.1f %% —— 縁の際は粒の中心が届かず"
         "椀が満ちきらない分だけ閉形式が多い、旗で知らせる" % (rf[1][0], eo[1] * 100, rf[0][0], eo[0] * 100))
    # 門 18 壊れる場所: 粒が大きい(a/d = 4.3)
    nu3, e3 = _errs(0.0035, 62)
    lim2 = S.scoop_image_limit(a, 0.25e-3, 0.002, 1400.0, h=h, rel_tol=0.08)
    lim3 = S.scoop_image_limit(a, 0.25e-3, 0.0035, 1400.0, h=h, rel_tol=0.08)
    gate("門 18 壊れる場所: 粒が大きい(半径 3.5 mm、a/d = 4.3、28〜112 個)と同じ較正でも誤差が倍以上、規則は秤と言う",
         max(map(abs, e3.values())) > 2.0 * max(map(abs, e2.values())) and lim3["verdict"] == "scale" and lim2["verdict"] == "image",
         "誤差 %s(r = 2 mm の最大 %.1f %% に対し %.1f %%)、規則の目安(許容 8 %%)%.1f %% → %s / %.1f %% → %s(a/d = %.1f < 5)"
         % ({"%d/s%d" % k: round(v * 100, 1) for k, v in e3.items()}, 100 * max(map(abs, e2.values())), 100 * max(map(abs, e3.values())),
            lim2["rel_err"] * 100, lim2["verdict"], lim3["rel_err"] * 100, lim3["verdict"], lim3["a_over_d"]))
    out.update(fills=fills, nu2=nu2, e2=e2, e3=e3, eo=eo)
    # ---- 注ぎ ----
    pr = S.scoop_mujoco_pour(0.08, 0.024, 0.028, 0.002, wall=0.05, wall_mu=0.02, omega_deg_s=15.0, theta_end_deg=34.0, settle=0.3)
    info = pr["info"]
    r, zl, L = info["radius"], info["lip_height"], info["L"]
    si, th, T = pr["start_index"], pr["theta_deg"], pr["times"]
    dtf = float(T[1] - T[0])
    pitch, x_lo, x_hi, s_top, rows = 0.5e-3, -0.054, 0.010, 0.010, 192
    ext, xc, height = (x_hi - x_lo) / 2, (x_hi + x_lo) / 2, rows * pitch
    bands = [60, 100, 140]
    s_b = np.array([s_top + (b + 0.5) * pitch for b in bands])

    def _stream_frame(k):
        P = pr["frames"][k].copy()
        P[:, 0] -= xc
        P[:, 2] -= (zl - s_top - height)
        return G.spheres_to_silhouette(P, r, pitch, ext, height, supersample=4)

    chunks = []
    for lo in (6.0, 10.0, 14.0, 18.0, 22.0):
        ks = [k for k in range(si, len(th)) if lo <= th[k] < lo + 4.0]
        fr = [_stream_frame(k) for k in ks]
        f = S.stream_flux_read(fr, dtf, r / pitch, band_rows=bands, c_max=0.97, particle_mass=info["mass_each"])
        Z = np.array([pr["frames"][k][:, 2] for k in ks])
        truth = np.array([((Z[:-1] > zl - s) & (Z[1:] <= zl - s)).sum() / ((len(ks) - 1) * dtf) for s in s_b])
        chunks.append({"lo": lo, "ks": ks, "f": f, "truth": truth, "frames": fr})
    assert len(chunks) == 5
    # 門 19 速さ vs 自由落下(v₀ と g を当てる)
    vv = np.concatenate([c["f"]["v"] * pitch for c in chunks])
    ss_ = np.tile(s_b, len(chunks))
    v0_fit = math.sqrt(max(float(np.mean(vv ** 2 - 2.0 * S.G_STD * ss_)), 0.0))     # g は既知、口を離れる速さだけ当てる
    vres = vv / np.sqrt(v0_fit ** 2 + 2.0 * S.G_STD * ss_) - 1
    k_, b_ = np.polyfit(ss_, vv ** 2, 1)
    g_fit = k_ / 2.0
    gate("門 19 注ぎの流れの速さ(MuJoCo の像の PIV)vs 自由落下 √(v₀² + 2gs)(g は既知、v₀ だけ当てる)",
         float(np.max(np.abs(vres))) < 0.02, "残差 最大 %.2f %%(門 2 %%、5 区間 × 3 高さ)、v₀ = %.2f m/s; 参考に g も当てると %.2f m/s²(落差 40 mm の範囲で v₀ と相関)"
         % (100 * float(np.max(np.abs(vres))), v0_fit, g_fit))
    # 門 20 流量 vs 横切り数
    ratios = np.array([c["f"]["flux"] / c["truth"] for c in chunks])
    naive = np.array([c["f"]["flux_naive"] / c["truth"] for c in chunks])
    gate("門 20 流量(Boolean 模型 × PIV)vs MuJoCo で線を横切った球の数(傾き 6〜26 度の 5 区間 × 3 高さ)",
         float(np.max(np.abs(ratios - 1))) < 0.10 and float(np.mean(np.abs(ratios - 1))) < float(np.mean(np.abs(naive - 1))),
         "比 %s(門 10 %%)、素朴な数え方は %s; 真値 %s 個/s" % (np.round(ratios.mean(axis=1), 3).tolist(), np.round(naive.mean(axis=1), 3).tolist(),
                                                     [int(round(c["truth"].mean())) for c in chunks]))
    # 門 21 出た量 = ∫ 流量 dt vs 数
    dur = np.array([(len(c["ks"]) - 1) * dtf for c in chunks])
    n_img = float(np.sum([c["f"]["flux_mean"] * d for c, d in zip(chunks, dur)]))
    n_true = float(np.sum([c["truth"].mean() * d for c, d in zip(chunks, dur)]))
    k_a, k_b = chunks[0]["ks"][0], chunks[-1]["ks"][-1]
    n_counted = int(pr["n_out"][k_b] - pr["n_out"][k_a])
    gate("門 21 注いだ量 = 像の流量の時間積分 vs MuJoCo でこぼれた球の数(6〜26 度)",
         abs(n_img / n_counted - 1) < 0.08, "像 %.0f 個 = %.1f g、横切り数 %.0f 個、器から出た数 %d 個(%+.1f %%、門 8 %%)"
         % (n_img, n_img * info["mass_each"] * 1e3, n_true, n_counted, (n_img / n_counted - 1) * 100))
    # 門 22 傾き依存: 口の楔 vs 口に縁のある器(どちらも厳密な tan(φ − θ)、φ をそれぞれ当てる)
    n0 = pr["n_start"]
    sel = np.arange(si, len(th))
    Fm = pr["n_out"][sel] / n0
    tt = th[sel]
    keep = (tt > 0.0) & (Fm < 0.98)
    h_eff = None
    # 初めの量から実効の深さ: 置いた後の断面積 = 球の数 × v_p / (ν B)、ν は器の像から読む代わりに h を当てはめに含める
    best_o, best_s = None, None
    for phi in np.arange(18.0, 45.0, 0.25):
        for hh in np.arange(0.012, 0.030, 0.001):
            Fo = np.array([S.tilt_wedge_retained(t, phi, L, hh)["fraction"] for t in tt[keep][::6]])
            Fs = np.array([S.tilt_wedge_retained(t, phi, L, hh)["F_lip_wall"] for t in tt[keep][::6]])
            eo_, es_ = float(np.sqrt(np.mean((Fo - Fm[keep][::6]) ** 2))), float(np.sqrt(np.mean((Fs - Fm[keep][::6]) ** 2)))
            if best_o is None or eo_ < best_o[0]:
                best_o = (eo_, phi, hh)
            if best_s is None or es_ < best_s[0]:
                best_s = (es_, phi, hh)
    first = float(tt[np.argmax(Fm > 0.02)])
    thc_small = S.tilt_wedge_retained(0.0, best_s[1], L, best_s[2])["theta_c_lip_wall_deg"]
    h_eff = best_o[2]
    gate("門 22 傾き角への依存(出た割合 F(θ)): 口の楔の導出 vs 口に縁のある器(granular、どちらも厳密な tan(φ − θ))、φ と深さをそれぞれ当てはめ",
         best_o[0] < 0.7 * best_s[0] and first < thc_small,
         "口の楔 RMS %.3f(φ %.2f 度、深さ %.0f mm)vs 縁のある器 %.3f(φ %.2f 度)—— 楔が %.1f 倍よく合う; 2 %% 出た角 %.1f 度 < 縁のある器の θ_c %.1f 度"
         "(口に壁が無いとすぐこぼれ始める)。2026-10-05 前の granular の小角の近似 tan φ − tan θ では RMS 0.038 だった。"
         "φ は当てはめで独立でない、奥の層は実際には流れて薄くなる(模型に無い)"
         % (best_o[0], best_o[1], best_o[2] * 1e3, best_s[0], best_s[1], best_s[0] / best_o[0], first, thc_small))
    # 門 23 Beverloo の桁(口の流れの層を等価直径に)
    peak = max(float(c["truth"].mean()) for c in chunks) * info["mass_each"]
    rho_b = 0.58 * info["density"]
    Dh = 2.0 * h_eff * info["B"] / (h_eff + info["B"])
    Wb = G.beverloo_rate(Dh, 2 * r, rho_b)
    gate("門 23 注ぎの流量 vs Beverloo の桁(口の層を等価直径に)—— ゆっくり傾ける限り流量は傾ける速さで決まり、口の通す力より下",
         0.1 < peak / Wb < 1.0, "最大 %.1f g/s vs Beverloo %.1f g/s(D_h %.1f mm、ρ_b %.0f kg/m³ は充填率 0.58 の仮定)= 比 %.2f(門 0.1〜1、桁だけ)"
         % (peak * 1e3, Wb * 1e3, Dh * 1e3, rho_b, peak / Wb))
    # 門 24 残量の像(包絡の殻を引いた断面積)vs 数
    pit2, ext2, z_lo2, h2 = 0.25e-3, 0.09, zl - 0.03, 0.09
    lip_row, lip_col = (h2 - (zl - z_lo2)) / pit2, ext2 / pit2
    Fi, Ft, Fth, Fr, base, base_raw = [], [], [], [], None, None
    for k in range(si, len(th), 24):
        P = pr["frames"][k].copy()
        P[:, 2] -= z_lo2
        sil = G.spheres_to_silhouette(P, r, pit2, ext2, h2)
        try:
            rdt = S.tilted_surface_read(sil, lip_row, lip_col, th[k], L / pit2, wall_px=info["wall"] / pit2, shell_px=r / pit2,
                                        smooth_px=int(2 * r / pit2) | 1)
        except ValueError:
            break
        if base is None:
            base, base_raw = rdt["area_corrected"], rdt["area_px"]
        Fi.append(1 - rdt["area_corrected"] / base)
        Fr.append(1 - rdt["area_px"] / base_raw)
        Fth.append(float(th[k]))
        Ft.append(pr["n_out"][k] / n0)
    Fi, Ft, Fr = np.array(Fi), np.array(Ft), np.array(Fr)
    assert len(Fi) >= 10
    gate("門 24 器に残る量の像(断面積 − 粒半径 × 自由表面の長さ)vs MuJoCo の数", float(np.max(np.abs(Fi - Ft))) < 0.10,
         "出た割合の差 最大 %.3f(門 0.10、%d コマ; 殻を引かない断面積だと %.3f)—— 像は数より遅れる(輪郭は粒の外側の包絡、流れる表層は膨らむ)"
         % (float(np.max(np.abs(Fi - Ft))), len(Fi), float(np.max(np.abs(Fr - Ft)))))
    dt = time.perf_counter() - t0
    gate("門 25 --full の所要 ≤ 240 s(機械の混み具合で倍まで揺れる)", dt <= 240.0, "%.1f s(すくい 12 本、注ぎ %.1f s・%d 球・%d 歩)" % (dt, pr["elapsed_s"], info["n"], info["steps"]))
    out.update(pour=pr, chunks=chunks, s_b=s_b, g_fit=g_fit, v0_fit=v0_fit, vres=100 * float(np.max(np.abs(vres))), best_o=best_o, best_s=best_s, Fm=Fm, tt=tt, Fi=Fi, Ft=Ft, Fi_theta=np.array(Fth),
               n_img=n_img, n_counted=n_counted, peak=peak, Wb=Wb, Dh=Dh, stream_geom=(pitch, ext, xc, height, s_top))
    return out


# ======================================================================================================================
def _figures_numpy(out: dict) -> None:
    # 01 スプーンの側面像 4 状態(等倍)に閉形式の輪郭
    panels = []
    for (fill, hf), lab in zip(((0.4, 0.0), (1.0, 0.0), (1.0, 0.5), (1.0, 1.0)), ("40 % filled", "level (struck)", "heap, base 0.5 a", "full heap")):
        w = S.scoop_synth_side(240, 96, fill=fill, heap_frac=hf, phi_deg=30.0, pitch=0.05e-3, margin_px=14, noise=0.05, seed=2)
        v = S.revolution_volume_side(w["side"], w["pitch"])
        img = _rgb(w["side"])
        a_, h_, R_ = w["truth"]["a_px"], w["truth"]["h_px"], w["truth"]["R_px"]
        rr, ax = w["rim_row"], w["axis_col"]
        pts = []
        for z in np.linspace(0, h_, 60):
            rad = math.sqrt(max(R_ * R_ - (R_ - z) ** 2, 0.0))
            pts.append((rr + h_ - z, ax - rad))
        pts2 = [(p0, 2 * ax - p1) for p0, p1 in pts]
        _polyline(img, pts, (0.35, 0.65, 1.0), 1.2)
        _polyline(img, pts2, (0.35, 0.65, 1.0), 1.2)
        _line(img, (rr, ax - a_ - 6), (rr, ax + a_ + 6), (0.35, 0.65, 1.0), 1.0, dash=4)
        head = np.empty((40, img.shape[1], 3))
        head[:] = (0.10, 0.10, 0.12)
        head = _text(head, "%s   read %.1f / truth %.1f mm3" % (lab, v["V"] * 1e9, w["truth"]["V"] * 1e9), (6, 4), fs=14)
        panels.append((head, img))
    h_max = max(im.shape[0] for _, im in panels)
    w_max = max(im.shape[1] for _, im in panels)
    cells = []
    for head, im in panels:                                    # 椀の底をそろえる(上に背景を足す)、見出しは絵の外
        cell = np.empty((40 + h_max, w_max, 3))
        cell[:] = (0.10, 0.10, 0.12)
        cell[:40, :head.shape[1]] = head
        cell[40 + h_max - im.shape[0]:, :im.shape[1]] = im
        cells.append(cell)
    sep = np.ones((cells[0].shape[0], 6, 3))
    grid = np.vstack([np.hstack([cells[0], sep, cells[1]]), np.ones((6, 2 * w_max + 6, 3)), np.hstack([cells[2], sep, cells[3]])])
    figs.save("scoop_spoon_side_views_states", grid,
              caption="球冠の椀(縁の半径 240 px = 12 mm、深さ 96 px、0.05 mm/px)の中の粉の側面像(被覆率、雑音 ±0.05、等倍)。青 = 椀の内面(閉形式)、"
                      "破線 = 縁。下 2 枚は縁の上に安息角 30 度の円錐。Pappus の形で読んだ体積と閉形式の真値。")
    # 02 楕円錐 2 方向
    sx, sy, tv, Vvox = out["ell"]
    img = np.hstack([_rgb(sx), np.ones((sx.shape[0], 6, 3)), _rgb(sy)])
    img = _text(img, "view along y (width 2a)        view along x (width 2b)", (6, 4), fs=14)
    img = _text(img, "two views %+.2f %%   one view: %+.0f %% / %+.0f %%" % ((tv["V"] / Vvox - 1) * 100, (tv["V_a"] / Vvox - 1) * 100,
                                                                           (tv["V_b"] / Vvox - 1) * 100), (6, 26), fs=14)
    figs.save("scoop_elliptic_heap_two_views", img,
              caption="縦長の盛り(楕円錐 1.6 : 1)を直交する 2 方向から見た像(等倍)。2 方向の楕円の和は体素の真値に %+.2f %%、"
                      "片方だけの回転体は %+.0f %% / %+.0f %% 外れる。" % ((tv["V"] / Vvox - 1) * 100, (tv["V_a"] / Vvox - 1) * 100, (tv["V_b"] / Vvox - 1) * 100))
    # 03 流れの GIF(合成、PIV の速さを帯に)
    st, f = out["stream"][3000]
    gif = []
    for k, fr in enumerate(st["frames"][:24]):
        im = _rgb(fr)
        im = np.kron(im, np.ones((2, 2, 1)))
        for b, v in zip(f["rows"], f["v"]):
            _line(im, (2 * b, 0), (2 * b, im.shape[1] - 1), (0.35, 0.65, 1.0), 0.8, dash=3)
        im = _text(im, "t = %.1f ms" % (k * st["dt"] * 1e3), (4, 4), fs=13)
        gif.append((np.clip(im, 0, 1) * 255).astype(np.uint8))
    assert len(gif) >= 10
    figs.save_gif("scoop_stream_synthetic_frames", gif, fps=8.0,
                  caption="合成の流れ(3000 個/s、半径 1 mm、幅 8 mm、0.5 mm/px を 2 倍の最近傍、1.5 ms/コマ)。破線 = 流量を読む 3 つの帯。")
    # 04 速さ vs 自由落下
    s_rows = st["s_rows"]
    sp = []
    for q_, (st_, f_) in out["stream"].items():
        sp.append(("PIV, %d /s" % q_, st_["s_rows"][f_["rows"].astype(int)] * 1e3, f_["v"] * st_["pitch"]))
    sp.append(("free fall sqrt(v0^2 + 2 g s)", s_rows * 1e3, st["truth"]["v"]))
    figs.save_plot("scoop_stream_speed_vs_freefall", sp, xlabel="fall distance below the lip s [mm]", ylabel="speed [m/s]",
                   title="Stream speed: PIV vs free fall", size=(760, 440), styles=[None, None, "dashed"], kinds=["scatter", "scatter", "line"],
                   colors=["emphasis", "neutral", "reference"], caption="PIV(全コマ対の中央値)の速さと自由落下の閉形式。")
    # 05 Boolean 模型 vs 素朴(流量を振って真値との比)
    qs = (200, 600, 1500, 3000, 5000)
    cm, rb_, rn_ = [], [], []
    for q_ in qs:
        st_ = S.stream_synth(q_, 1e-3, 8e-3, n_frames=24, seed=5)
        f_ = S.stream_flux_read(st_["frames"], st_["dt"], st_["truth"]["radius_px"], band_rows=[40, 96, 152], c_max=0.99)
        tr_ = st_["truth"]["crossings"][[40, 96, 152]]
        cm.append(f_["c_max_seen"])
        rb_.append(float(np.mean(f_["flux"] / tr_)))
        rn_.append(float(np.mean(f_["flux_naive"] / tr_)))
    assert len(cm) == len(qs)
    figs.save_plot("scoop_boolean_model_vs_naive",
                   [("Boolean model -ln(1-c)/(pi r^2)", np.array(cm), np.array(rb_)), ("naive c/(pi r^2)", np.array(cm), np.array(rn_)),
                    ("truth", np.array([0.0, 1.0]), np.array([1.0, 1.0]))],
                   xlabel="peak time-mean coverage of the stream", ylabel="measured flow / true line crossings",
                   title="Counting particles through overlap (synthetic streams, 200 ... 5000 /s)", size=(760, 440),
                   styles=[None, None, "dashed"], kinds=["scatter", "scatter", "line"], colors=["emphasis", "wrong", "reference"],
                   caption="合成の流れの流量を 200〜5000 個/s に振り、像から読んだ流量を実現した横切り数で割る。Boolean 模型の逆は %s、"
                           "素朴な c/(πr²) は被覆率とともに数え落とす(%s)。" % ([round(x, 2) for x in rb_], [round(x, 2) for x in rn_]))
    # 06 傾けて出る割合の 2 模型
    L, h0, phi = out["tilt"]
    ths = np.linspace(0, phi, 121)
    figs.save_plot("scoop_tilt_models",
                   [("open lip wedge (this module)", ths, [S.tilt_wedge_retained(t, phi, L, h0)["fraction"] for t in ths]),
                    ("lip with a wall (granular)", ths, [S.tilt_wedge_retained(t, phi, L, h0)["F_lip_wall"] for t in ths])],
                   xlabel="tilt theta [deg]", ylabel="fraction poured", title="Tilting a trough: two quasi-static models (phi 30, h0/L 0.25)",
                   size=(760, 440), styles=[None, "dashed"], colors=["emphasis", "reference"],
                   caption="口に壁の無い器(前面が初めから安息角の斜面)は θ = 0⁺ からこぼれ、口に縁のある器(granular の lip=\"wall\"、初めは口まで"
                           "平らに満ちている)は θ_c まで 1 粒も出ない。どちらも楔の傾きは厳密な tan(φ − θ)。")
    # 07 画像で足りるか
    big, mg, few = out["limit"]
    aa = np.geomspace(1e-3, 0.05, 40)
    rel = [S.scoop_image_limit(x, 1e-4, 0.5e-3, 800.0)["rel_err"] for x in aa]
    figs.save_plot("scoop_image_vs_scale",
                   [("relative error of a heaped scoop, 0.1 mm/px, 1 mm grains", aa * 1e3, np.array(rel) * 100),
                    ("5 % tolerance", np.array([1.0, 50.0]), np.array([5.0, 5.0]))],
                   xlabel="rim radius a [mm]", ylabel="relative error [%]", title="When the image is enough and when to use the scale",
                   size=(760, 440), styles=[None, "dashed"], colors=["emphasis", "reference"],
                   caption="山盛りの椀の体積の誤差の目安(表面積 × (0.5 px + 0.25 r))。31 g の椀は %.1f %%、10 mg の椀(縁 %.1f mm)は %.0f %% → 秤。"
                           % (big["rel_err"] * 100, mg["a_for_target"] * 1e3, mg["rel_err_target"] * 100))


def _figures_mujoco(out: dict) -> None:
    fills = out["fills"]
    # 08 MuJoCo のすくい 3 量(陰影つき、等倍)
    ims = []
    for n in (150, 330, 600):
        d = fills[(0.002, n, 0)]
        im = G.spheres_render_shaded(d["Q"], 0.002, d["pitch"], d["ext"], d["height"])
        rr = d["rim_row"]
        _line(im, (rr, 0), (rr, im.shape[1] - 1), (0.35, 0.65, 1.0), 0.8, dash=5)
        info_ = d["run"]["info"]
        zc_ = info_["bottom_height"] + info_["R"] - d["z0"]
        arc = [((d["height"] - (zc_ - math.sqrt(info_["R"] ** 2 - xx ** 2))) / d["pitch"], (xx + d["ext"]) / d["pitch"])
               for xx in np.linspace(-info_["a"], info_["a"], 80)]
        _polyline(im, arc, (0.35, 0.65, 1.0), 1.2)                 # 椀の内面(閉形式、描画には写らない薄板の位置)
        Nimg = S.scoop_count(d["tv"]["V"], 0.002, out["nu2"])["N"]
        im = _text(im, "MuJoCo %d spheres   image %.0f" % (d["run"]["n_retained"], Nimg), (6, 4), fs=14)
        ims.append(im)
    figs.save("scoop_mujoco_fills_render", np.vstack(ims),
              caption="球冠の椀(青 = 内面の閉形式、縁 30 mm、深さ 12 mm、薄板 118 枚)にすくった剛体球(半径 2 mm)150 / 330 / 600 個"
                      "(陰影つき正射影、0.25 mm/px、等倍)。破線 = 縁。2 方向の像の体積 × 較正した充填率 %.3f で数えた個数。" % out["nu2"])
    # 09 注ぎの GIF
    pr = out["pour"]
    info = pr["info"]
    r, zl = info["radius"], info["lip_height"]
    gif = []
    si = pr["start_index"]
    for k in range(si, len(pr["frames"]), 20):
        P = pr["frames"][k].copy()
        P[:, 2] -= (zl - 0.11)
        im = G.spheres_render_shaded(P, r, 0.5e-3, 0.09, 0.17)
        thr = math.radians(pr["theta_deg"][k])

        def _rc(xw, zw):
            return ((0.17 - (zw - (zl - 0.11))) / 0.5e-3, (xw + 0.09) / 0.5e-3)

        Lw, Ww = info["L"], info["wall"]
        p_lip, p_back = (0.0, zl), (Lw * math.cos(thr), zl + Lw * math.sin(thr))
        p_top = (p_back[0] - Ww * math.sin(thr), p_back[1] + Ww * math.cos(thr))
        _polyline(im, [_rc(*p_lip), _rc(*p_back), _rc(*p_top)], (0.35, 0.65, 1.0), 1.2)   # 樋の床と奥壁(描画に写らない)
        im = _text(im, "theta %.1f deg   poured %d / %d" % (pr["theta_deg"][k], pr["n_out"][k], pr["n_start"]), (6, 4), fs=14)
        gif.append((np.clip(im, 0, 1) * 255).astype(np.uint8))
    assert len(gif) >= 10
    figs.save_gif("scoop_mujoco_pour_render", gif, fps=10.0,
                  caption="口の開いた樋(青 = 床と奥壁、床 80 mm、幅 24 mm、滑らかな側壁)を口の縁を軸に 15 度/s で傾ける(剛体球 %d 個、0.5 mm/px、"
                          "陰影つき正射影)。数は傾け始めに器にあった球のうち口を越えた数。" % info["n"])
    # 10 出た割合
    tt, Fm = out["tt"], out["Fm"]
    bo, bs = out["best_o"], out["best_s"]
    L = info["L"]
    figs.save_plot("scoop_mujoco_poured_fraction",
                   [("MuJoCo count", tt, Fm),
                    ("open lip wedge, phi %.1f, h %.0f mm" % (bo[1], bo[2] * 1e3), tt, [S.tilt_wedge_retained(t, bo[1], L, bo[2])["fraction"] for t in tt]),
                    ("lip with a wall, phi %.1f" % bs[1], tt, [S.tilt_wedge_retained(t, bs[1], L, bs[2])["F_lip_wall"] for t in tt]),
                    ("image (area - shell)", out["Fi_theta"], out["Fi"])],
                   xlabel="tilt theta [deg]", ylabel="fraction poured", title="Pouring by tilting: MuJoCo vs the two models", size=(760, 440),
                   styles=[None, "dashed", "dotted", None], kinds=["line", "line", "line", "scatter"], colors=["neutral", "emphasis", "reference", "right"],
                   caption="MuJoCo の数(真値)と 2 つの準静的模型(φ と深さを当てはめ; 口の楔 RMS %.3f、口に縁のある器 %.3f)。点 = 像の断面積から読んだ割合。"
                           % (bo[0], bs[0]))
    # 11 流量の時系列
    ch = out["chunks"]
    figs.save_plot("scoop_mujoco_flux_image_vs_count",
                   [("image: Boolean x PIV", [c["lo"] + 2 for c in ch], [c["f"]["flux_mean"] for c in ch]),
                    ("MuJoCo line crossings", [c["lo"] + 2 for c in ch], [c["truth"].mean() for c in ch]),
                    ("image: naive count x PIV", [c["lo"] + 2 for c in ch], [float(np.mean(c["f"]["flux_naive"])) for c in ch])],
                   xlabel="tilt theta [deg] (centre of 4 deg window)", ylabel="flow [spheres/s]", title="Pour rate from the stream image",
                   size=(760, 440), styles=[None, "dashed", "dotted"], kinds=["scatter", "line", "scatter"], colors=["emphasis", "reference", "neutral"],
                   caption="流れの像から読んだ流量(3 高さの平均)と MuJoCo で線を横切った数。傾くほど流量が増える(供給で決まる)。")
    # 12 表
    hdr = ["quantity", "image (this module)", "outside truth", "difference", "gate"]
    rows = [["scooped count, r 2 mm (5 runs)", "max err %.1f %%" % (100 * max(map(abs, out["e2"].values()))), "MuJoCo sphere count", "-", "< 5 %"],
            ["scooped count, r 3.5 mm (a/d 4.3)", "max err %.1f %%" % (100 * max(map(abs, out["e3"].values()))), "MuJoCo sphere count", "-", "> 2x"],
            ["stream speed vs free fall (v0 %.2f m/s)" % out["v0_fit"], "max resid %.2f %%" % out["vres"], "sqrt(v0^2 + 2 g s)", "-", "2 %"],
            ["poured spheres 6-26 deg", "%.0f" % out["n_img"], "%d (count)" % out["n_counted"], "%+.1f %%" % ((out["n_img"] / out["n_counted"] - 1) * 100), "8 %"],
            ["peak pour rate [g/s]", "%.1f" % (out["peak"] * 1e3), "Beverloo %.1f (D_h %.1f mm)" % (out["Wb"] * 1e3, out["Dh"] * 1e3),
             "ratio %.2f" % (out["peak"] / out["Wb"]), "0.1 .. 1"]]
    figs.save_table("scoop_mujoco_vs_references", hdr, rows, title="MuJoCo rigid spheres vs the image readings",
                    caption="第 2 実装(MuJoCo の剛体球)と像の読み。数の真値は MuJoCo の個数と線の横切り。")


def figures(out: dict) -> None:
    print("== 図")
    _figures_numpy(out)
    if "fills" in out:
        _figures_mujoco(out)
    else:
        print("  図 08〜12 は --full(MuJoCo)のときだけ")
    print("  figures:", figs.errors() or "ok")


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    out = numpy_part()
    if FULL:
        out = full_part(out)
    else:
        skip("門 16〜25(MuJoCo)", "--full のときだけ(mujoco)")
    if figs.enabled():
        figures(out)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
