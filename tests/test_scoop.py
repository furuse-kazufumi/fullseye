# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""scoop の門(粉体のすくいと注ぎを画像で測る: すくった量を側面像の輪郭から、注ぎの流量を流れの幅と速さから、規則だけで)。

numpy だけの門(常に走る):
 1. 球冠の椀の閉形式: すり切り vs 体素の数え上げ 1e-3、満杯の恒等式、山盛り = granular の円錐、h > a・深すぎる充填は ValueError
 2. 合成の側面像 → 回転体の体積(Pappus、5 状態、雑音 ±0.1)0.6 % —— 合成と読みが同じ模型なので配管の検査; 円板の和は途中まで
    満たした椀で −1 % より低い(f² の罠を数で残す)
 3. 不透明の椀: 縁の上 + すり切りの閉形式、縁の上が空なら ValueError(assume_level で閉形式)、透明な椀の深さは閉形式の逆
 4. 2 方向: 楕円錐 1.6 : 1 の体素の真値 0.5 %、片方だけは −30 % / +50 % を超えて外れる
 5. 流れ: PIV の速さ vs 自由落下 2 %、Boolean 模型の流量 vs 実現した横切り数 8 %、素朴な数え方は密な流れで 0.8 倍未満
 6. 壊れる場所: 粒が少ない流れは reliable=False、もっと少ないと PIV が立たず ValueError、飽和は ValueError
 7. 傾けの導出: dA/dθ の閉形式 = 数値微分、F(0) = 0・F(φ) = 1・単調、granular の小角の近似より早くこぼれ始める
 8. 傾いた器の像 → 断面積 vs 閉形式 0.5 %、殻の補正は長さ × 半径
 9. 体積 → 粒の数・質量、画像で足りるか(31 g は画像、10 mg は秤、a/d < 5 は秤)
10. MJCF 文字列(mujoco 不要): 椀の薄板と球の数、樋は mocap、contact_tc < 2 timestep は ValueError
11. 綴り壊しと引数の範囲 → ValueError
12. 入口: __all__ の全部が実在、docstring に角括弧の直後の丸括弧が無い、acos を使わない
mujoco が要る門(無ければ skip):
13. 椀にすくった 150 個が全部残り、2 方向の像の体積から読んだ充填率が 0.50〜0.58(PoC の較正値 0.539 の近く)
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

import granular as G
import scoop as S


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


# ── 1. 閉形式 ───────────────────────────────────────────────────────────────
def test_bowl_closed_form_matches_voxels_and_identities():
    a, h = 1.0, 0.4
    g = S.spoon_bowl_volume(a, h, fill_depth=h, phi_deg=30.0)
    n = 200
    x = (np.arange(n) + 0.5) / n * 2 * a - a
    X, Y = np.meshgrid(x, x)
    rr2 = X * X + Y * Y
    zz = (np.arange(n) + 0.5) / n * h
    cnt = sum(int(np.sum(rr2 <= max(g["R"] ** 2 - (g["R"] - z) ** 2, 0.0))) for z in zz)
    assert cnt * (2 * a / n) ** 2 * (h / n) == pytest.approx(g["V_struck"], rel=1e-3)
    assert g["V_struck"] == pytest.approx(math.pi * h * (3 * a * a + h * h) / 6, rel=1e-12)
    assert g["V_fill"] == pytest.approx(g["V_struck"], rel=1e-12)
    assert g["V_heap"] == pytest.approx(G.heap_volume_cone(R=a, phi_deg=30.0)["V"], rel=1e-12)
    assert _raises(S.spoon_bowl_volume, 1.0, 1.2) and _raises(S.spoon_bowl_volume, 1.0, 0.4, fill_depth=0.5)


# ── 2〜3. 側面像 → 体積 ─────────────────────────────────────────────────────
def test_side_view_volume_states_and_disc_trap():
    errs, disc = [], []
    for fill, hf in ((0.4, 0.0), (0.7, 0.0), (1.0, 0.0), (1.0, 0.5), (1.0, 1.0)):
        for noise in (0.0, 0.1):
            w = S.scoop_synth_side(120, 48, fill=fill, heap_frac=hf, phi_deg=30.0, noise=noise, seed=1)
            v = S.revolution_volume_side(w["side"], w["pitch"])
            errs.append(v["V"] / w["truth"]["V"] - 1)
            if noise == 0.0 and fill < 1.0:
                disc.append(v["V_discs"] / w["truth"]["V"] - 1)
    assert len(errs) == 10 and len(disc) == 2
    assert max(map(abs, errs)) < 0.006            # 合成と読みが同じ軸対称の模型 → 配管の検査
    assert min(disc) < -0.01                      # 行の幅の円板の和は f² で数え落とす(罠を数で残す)


def test_opaque_and_transparent_reads():
    wh = S.scoop_synth_side(120, 48, heap_frac=1.0, phi_deg=30.0)
    rd = S.scoop_volume_read(wh["side_above"], wh["rim_row"], 120, 48, wh["pitch"])
    assert rd["V"] == pytest.approx(wh["truth"]["V"], rel=2e-3) and rd["state"] == "heaped" and rd["rim_full"]
    assert rd["heap_angle_deg"] == pytest.approx(30.0, abs=0.2)
    wl = S.scoop_synth_side(120, 48)
    assert _raises(S.scoop_volume_read, wl["side_above"], wl["rim_row"], 120, 48, wl["pitch"])
    rl = S.scoop_volume_read(wl["side_above"], wl["rim_row"], 120, 48, wl["pitch"], assume_level=True)
    assert rl["V"] == pytest.approx(wl["truth"]["V"], rel=1e-9) and rl["state"] == "level"
    wu = S.scoop_synth_side(120, 48, fill=0.4)
    ru = S.scoop_volume_read(wu["side"], wu["rim_row"], 120, 48, wu["pitch"], opaque=False)
    assert ru["state"] == "under" and ru["fill_depth_px"] == pytest.approx(0.4 * 48, abs=0.5)


# ── 4. 2 方向 ───────────────────────────────────────────────────────────────
def test_two_views_recover_an_elliptic_heap():
    ax, by, H = 60.0, 96.0, 70.0
    rows, cols, ss = int(H) + 10, 2 * int(by) + 20, 4
    zc = np.arange(rows * ss)[::-1] / ss + 0.5 / ss - 5

    def sil(semi):
        xs = (np.arange(cols * ss) + 0.5) / ss - cols / 2
        Z = zc[:, None]
        m = (Z >= 0) & (Z <= H) & (np.abs(xs[None, :]) <= semi * (1 - np.clip(Z, 0, H) / H))
        return m.reshape(rows, ss, cols, ss).mean(axis=(1, 3))

    tv = S.two_view_volume(sil(ax), sil(by), 1.0)
    Vt = math.pi * ax * by * H / 3
    assert tv["V"] == pytest.approx(Vt, rel=5e-3)
    assert tv["V_a"] / Vt - 1 < -0.3 and tv["V_b"] / Vt - 1 > 0.5 and tv["ellipticity"] == pytest.approx(1.6, abs=0.02)


# ── 5〜6. 流れ ──────────────────────────────────────────────────────────────
def test_stream_speed_and_boolean_flux():
    st = S.stream_synth(3000, 1e-3, 8e-3, n_frames=32, seed=3)
    bands = [40, 96, 152]
    f = S.stream_flux_read(st["frames"], st["dt"], st["truth"]["radius_px"], band_rows=bands)
    tr = st["truth"]["crossings"][bands]
    assert np.max(np.abs(f["v"] * st["pitch"] / st["truth"]["v"][bands] - 1)) < 0.02
    assert np.max(np.abs(f["flux"] / tr - 1)) < 0.08
    assert np.max(f["flux_naive"] / tr) < 0.8 and f["reliable"]


def test_stream_breaks_with_few_particles_or_saturation():
    bands = [40, 96, 152]
    few = S.stream_synth(60, 1e-3, 8e-3, n_frames=32, seed=3)
    assert not S.stream_flux_read(few["frames"], few["dt"], few["truth"]["radius_px"], band_rows=bands)["reliable"]
    st0 = S.stream_synth(20, 1e-3, 8e-3, n_frames=32, seed=3)
    assert _raises(S.stream_flux_read, st0["frames"], st0["dt"], st0["truth"]["radius_px"], band_rows=bands)
    assert _raises(S.stream_areal_density, np.array([0.2, 0.97]), 2.0)
    assert np.all(np.isfinite(S.stream_areal_density(np.array([0.2, 0.97]), 2.0, mode="clip")))
    c = np.array([0.0, 0.3, 0.6])
    assert np.allclose(S.stream_areal_density(c, 1.0), -np.log1p(-c) / math.pi)


# ── 7〜8. 傾け ──────────────────────────────────────────────────────────────
def test_tilt_wedge_derivative_and_comparison():
    L, h0, phi = 0.08, 0.02, 30.0
    eps = 1e-4
    for t in (3.0, 12.0, 25.0):
        num = (S.tilt_wedge_retained(t - eps, phi, L, h0)["A"] - S.tilt_wedge_retained(t + eps, phi, L, h0)["A"]) / math.radians(2 * eps)
        an = S.tilt_pour_rate(t, 10.0, phi, L, h0, 0.03, 1500.0)["rate_area"] / math.radians(10.0)
        assert num == pytest.approx(an, rel=1e-6)
    Fs = [S.tilt_wedge_retained(t, phi, L, h0)["fraction"] for t in np.linspace(0, phi, 61)]
    assert len(Fs) == 61
    assert Fs[0] == 0.0 and Fs[-1] == pytest.approx(1.0, abs=1e-12) and all(b >= a - 1e-15 for a, b in zip(Fs, Fs[1:]))
    m = S.tilt_wedge_retained(3.0, phi, L, h0)
    assert m["fraction"] > 0.0 and m["F_small_angle"] == 0.0 and m["theta_c_small_angle_deg"] > 3.0
    assert _raises(S.tilt_wedge_retained, 95.0, 30.0, 1.0, 0.1) and _raises(S.tilt_pour_rate, 5.0, 0.0, 30.0, 1.0, 0.1, 0.1, 1000.0)


def test_tilted_container_area_read():
    rows, cols, ss = 150, 250, 4
    lip = (120.0, 30.0)
    for th in (0.0, 12.0, 24.0):
        c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
        t = math.tan(math.radians(32.0 - th))
        yy, xx = np.mgrid[0:rows * ss, 0:cols * ss].astype(np.float64)
        yy, xx = (yy + 0.5) / ss, (xx + 0.5) / ss
        dx, up = xx - lip[1], lip[0] - yy
        xf, yf = dx * c + up * s, -dx * s + up * c
        m = (xf >= 0) & (xf <= 200) & (yf >= 0) & (yf <= np.minimum(45.0, xf * t))
        img = m.reshape(rows, ss, cols, ss).mean(axis=(1, 3))
        r = S.tilted_surface_read(img, lip[0], lip[1], th, 200.0, wall_px=90.0, shell_px=2.0)
        assert r["area_px"] == pytest.approx(S._wedge_area(t, 200.0, 45.0), rel=5e-3)
        assert r["area_corrected"] == pytest.approx(r["area_px"] - 2.0 * r["surface_len_px"], rel=1e-12)
    assert _raises(S.tilted_surface_read, np.zeros((20, 20)), 10, 2, 5.0, 10.0)


# ── 9. 数と規則 ─────────────────────────────────────────────────────────────
def test_count_and_image_vs_scale():
    c = S.scoop_count(1e-6, 1e-3, 0.6, density=2500.0)
    assert c["N"] == pytest.approx(1e-6 * 0.6 / (4 / 3 * math.pi * 1e-9), rel=1e-12)
    assert c["mass"] == pytest.approx(0.6 * 2500.0 * 1e-6, rel=1e-12) and c["bulk_density"] == pytest.approx(1500.0)
    assert S.scoop_image_limit(0.03, 1e-4, 0.5e-3, 800.0, h=0.015)["verdict"] == "image"
    assert S.scoop_image_limit(0.03, 1e-4, 0.5e-3, 800.0, h=0.015, target_mass=10e-6)["verdict"] == "scale"
    assert S.scoop_image_limit(0.03, 1e-4, 3.5e-3, 1500.0, h=0.012)["verdict"] == "scale"
    assert _raises(S.scoop_count, 1.0, 1.0, 1.5) and _raises(S.scoop_count, -1.0, 1.0, 0.5)


# ── 10〜11. MJCF と綴り ─────────────────────────────────────────────────────
def test_mjcf_strings_and_spelling():
    sc = S.scoop_scene_mjcf(150)
    assert sc["xml"].count("<freejoint/>") == 150 and sc["info"]["n_tiles"] == sc["xml"].count('type="box"')
    pc = S.pour_scene_mjcf()
    assert 'mocap="true"' in pc["xml"] and pc["xml"].count("<freejoint/>") == pc["info"]["n"]
    assert _raises(S.scoop_scene_mjcf, 10, contact_tc=0.002) and _raises(S.pour_scene_mjcf, h0=0.05, wall=0.04)
    assert _raises(S.scoop_scene_mjcf, 10, cone="eliptic") and _raises(S.pour_scene_mjcf, solver="CGG")
    assert _raises(S.stream_areal_density, np.full(5, 0.3), 2.0, mode="clipp")
    assert _raises(S.scoop_synth_side, 100, 40, fill=0.5, heap_frac=0.3)
    assert _raises(S.two_view_volume, np.zeros((10, 10)), np.zeros((12, 10)), 1.0)
    assert _raises(S.revolution_volume_side, np.zeros((8, 8)), 1.0)


# ── 12. 入口 ────────────────────────────────────────────────────────────────
def test_entry_points_and_docstrings():
    assert len(S.__all__) >= 15
    for nm in S.__all__:
        fn = getattr(S, nm)
        assert callable(fn) and fn.__doc__ and "](" not in fn.__doc__, nm
    src = Path(S.__file__).read_text(encoding="utf-8")
    assert "acos" not in src


# ── 13. MuJoCo ─────────────────────────────────────────────────────────────
def test_mujoco_scoop_fill_packing():
    pytest.importorskip("mujoco")
    r = 0.002
    run = S.scoop_mujoco_fill(150, r, duration=1.0)
    assert run["n_retained"] == 150
    i = run["info"]
    z0 = i["bottom_height"] - 0.002
    Q = run["pos"].copy()
    Q[:, 2] -= z0
    ext, pitch, height = i["a"] + 0.008, 0.25e-3, 0.04
    sx = G.spheres_to_silhouette(Q, r, pitch, ext, height)
    sy = G.spheres_to_silhouette(Q[:, [1, 0, 2]], r, pitch, ext, height)
    nu = 150 * 4 / 3 * math.pi * r ** 3 / S.two_view_volume(sx, sy, pitch)["V"]
    assert 0.50 < nu < 0.58
