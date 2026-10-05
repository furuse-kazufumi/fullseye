# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""diabolo の門(ディアボロの解析模型を原文から写して確かめ、合成映像から軸・回転・張力を読む: 閉形式・厳密な糸・MuJoCo を真値に)。

numpy だけの門(常に走る):
 1. 焦点の恒等式 d_L + d_R = l(直した式 1b)、原文どおりの (1b) は間隔 1.1 m で NaN・0.3 m で 0.613 m
 2. 最近点の法線 = 勾配 û_L + û_R、公開実装の法線 (x/b, y/a, z/b) は 10° 以上ずれる、内外の符号
 3. 飛んでいる間の前進 Euler は真の放物線より g t dt/2 上(閉形式と 1e-12)
 4. 回転の式 (2) の望遠鏡和、μ = 1/r で滑らない転がり
 5. 厳密な糸(RATTLE): 棒が止まっていればエネルギーが有界、焦点軸が鉛直なら角運動量が丸めの桁で保存、張力の乗数 = m g a/(2b)
 6. 糸の V 字からの張力 = 閉形式、加速度を入れ忘れると残差が出る
 7. 投げ: 受けの時刻(閉形式 + 二分法)と論文の模型が 2 刻み以内、頂点のずれ = g t_apex dt/2、状態遷移の再分類が内部の状態と一致
 8. 合成映像 1 枚から軸(視線から 20° で 0.3° 以内)、45° は底の板が隠れて警報、読めないコマは NaN
 9. マーカーの位相(1 コマ)と回転数の枝選び(位相だけではナイキストで折り返す)
10. 綴り壊し 16 本は全部 ValueError、MJCF 文字列の部品
mujoco が要る門(無ければ skip):
11. MuJoCo の空間テンドン: 静止張力 = 閉形式、直線加速 0.5 s で厳密な糸と 5 mm 以内
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

import diabolo as D

P = D.diabolo_params()
G = P["g"]
CAM = D.diabolo_camera(position=(1.2, 0, 0.6), look_at=(0, 0, 0.6), shape=(240, 320), fovy_deg=16)


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


def _hang(sticks):
    s = np.asarray(sticks)
    sph = D.diabolo_spheroid(s[0], s[1], P["string_length"])
    return sph["center"] - np.array([0.0, 0.0, sph["b"]])


def _axis(th_deg, ph_deg):
    th, ph = math.radians(th_deg), math.radians(ph_deg)
    return np.array([math.cos(th), math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph)])


@pytest.fixture(scope="module")
def throw_sim():
    return D.diabolo_simulate(_hang(D._mo_throw(0)), [0, 0, 0], "throw", 2.0, 1e-3, P, model="paper")


@pytest.fixture(scope="module")
def tilted_frame():
    a = _axis(20, 120)
    c = np.array([0.0, 0.012, 0.597])
    img = D.diabolo_render(CAM, P, center=c, axis=a, phase=0.9, omega=2 * math.pi * 30, exposure=2e-3)
    return img, a, c


# ── 1, 2. 楕円体 ─────────────────────────────────────────────────────────────────
def test_spheroid_focal_identity_and_the_printed_formula():
    rng = np.random.default_rng(0)
    errs = []
    for _ in range(30):
        pl = rng.normal(0, 0.5, 3)
        pr = pl + rng.normal(0, 0.5, 3)
        ln = float(np.linalg.norm(pl - pr)) * rng.uniform(1.05, 3.0)
        sph = D.diabolo_spheroid(pl, pr, ln)
        e1, e2, _ = D._body_frame(sph["axis"])
        for th, ph in rng.uniform([0, 0], [np.pi, 2 * np.pi], (8, 2)):
            x = sph["center"] + sph["a"] * math.cos(th) * sph["axis"] + sph["b"] * math.sin(th) * (math.cos(ph) * e1 + math.sin(ph) * e2)
            errs.append(abs(np.linalg.norm(x - pl) + np.linalg.norm(x - pr) - ln) / ln)
    assert len(errs) == 240
    assert max(errs) < 1e-12
    assert math.isnan(D.diabolo_spheroid(*D._mo_fixed(0), 1.45)["b_paper_literal"])          # 論文の実機寸法で NaN
    s = D.diabolo_spheroid([0, 0.15, 1], [0, -0.15, 1], 1.45)
    assert abs(s["b"] - math.sqrt(0.725 ** 2 - 0.15 ** 2)) < 1e-15 and abs(s["b_paper_literal"] - math.sqrt(0.725 ** 2 - 0.15)) < 1e-15


def test_closest_point_normal_is_the_gradient_and_the_sign_convention():
    sph = D.diabolo_spheroid(*D._mo_fixed(0), 1.45)
    pl, pr = D._mo_fixed(0)
    e1, e2, _ = D._body_frame(sph["axis"])
    worst, worst_code, n = 0.0, 0.0, 0
    for th in np.linspace(0.1, np.pi - 0.1, 12):
        for ph in np.linspace(0, 2 * np.pi, 6, endpoint=False):
            x = sph["center"] + sph["a"] * math.cos(th) * sph["axis"] + sph["b"] * math.sin(th) * (math.cos(ph) * e1 + math.sin(ph) * e2)
            g = (x - pl) / np.linalg.norm(x - pl) + (x - pr) / np.linalg.norm(x - pr)
            gu = g / np.linalg.norm(g)
            out, inn = D.spheroid_closest(x + 0.01 * gu, sph), D.spheroid_closest(x - 0.01 * gu, sph)
            assert out["s"] < 0 < inn["s"] and abs(abs(out["s"]) - 0.01) < 1e-9
            worst = max(worst, D._angle_deg(gu, out["normal"]))
            worst_code = max(worst_code, D._angle_deg(gu, D._normal_code_variant(x, sph)))
            n += 1
    assert n == 72
    assert worst < 1e-9 and worst_code > 10.0


# ── 3, 4. 論文の 1 ステップ ─────────────────────────────────────────────────────
def test_forward_euler_offset_while_flying_is_g_t_dt_over_2():
    dt = 1e-3
    st = {"x": np.array([0.1, 0.0, 2.0]), "v": np.array([0.3, 0.2, 2.5]), "omega": 0.0, "mode": "flying"}
    sticks = np.array([[0, 0.15, 1.0], [0, -0.15, 1.0]])
    x0, v0 = st["x"].copy(), st["v"].copy()
    for i in range(1, 301):
        st = D.diabolo_dynamics_step(st, sticks, sticks, dt, P)
        t = i * dt
        assert st["mode"] == "flying"
        assert np.max(np.abs(st["x"] - (x0 + v0 * t + np.array([0, 0, -G * t * t / 2 + G * t * dt / 2])))) < 1e-12


def test_rotation_eq2_telescopes_and_mu_one_over_r_is_rolling():
    x0 = _hang(D._mo_linear_accel(0))
    r = D.diabolo_simulate(x0, [0, 0, 0], "linear_accel", 0.5, 1e-3, P, model="paper")
    assert np.all(r["mode"] == "on_string")
    dr = np.diff(np.linalg.norm(r["x"] - r["sticks"][:, 1], axis=1))
    pred = P["mu_acc"] * dr[dr > 0].sum() + P["mu_dec"] * dr[dr <= 0].sum()
    assert abs(pred - r["omega"][-1]) < 1e-9 * max(1.0, abs(r["omega"][-1]))
    Pr = D.diabolo_params(mu_acc=1 / P["axle_radius"], mu_dec=1 / P["axle_radius"])
    rr = D.diabolo_simulate(x0, [0, 0, 0], "linear_accel", 0.5, 1e-3, Pr, model="paper")
    d = np.linalg.norm(rr["x"] - rr["sticks"][:, 1], axis=1)
    assert np.max(np.abs(rr["omega"] * P["axle_radius"] - (d - d[0]))) < 1e-12


# ── 5. 厳密な糸 ─────────────────────────────────────────────────────────────────
def test_exact_string_conserves_energy_and_angular_momentum():
    s11 = D.diabolo_spheroid(*D._mo_fixed(0), 1.45)
    th = math.radians(20)
    x20 = s11["center"] + s11["b"] * np.array([math.sin(th), 0, -math.cos(th)])
    re = D.diabolo_simulate(x20, [0, 0, 0], "fixed", 1.0, 1e-3, P, model="exact")
    Esw = P["mass"] * G * s11["b"] * (1 - math.cos(th))
    assert (re["energy"].max() - re["energy"].min()) / Esw < 1.5e-5
    sv = D.diabolo_spheroid(*D._mo_vertical_axis(0), 1.45)
    zax = -0.3
    xv = sv["center"] + zax * sv["axis"] + sv["b"] * math.sqrt(1 - (zax / sv["a"]) ** 2) * np.array([1.0, 0, 0])
    r = D.diabolo_simulate(xv, [0.0, 1.8, 0.2], "vertical_axis", 1.0, 1e-3, P, model="exact", topology=False)
    Lz = r["x"][:, 0] * r["v"][:, 1] - r["x"][:, 1] * r["v"][:, 0]
    assert np.max(np.abs(Lz - Lz[0])) / abs(Lz[0]) < 1e-12
    assert np.mean(np.nan_to_num(r["tension"]) > 0) > 0.9            # ほぼ全刻で糸は張っている(自明な保存ではない)


def test_static_tension_multiplier_equals_closed_form():
    for gap in (0.6, 1.3):
        r = D.diabolo_simulate(_hang(D._mo_fixed(0, gap)), [0, 0, 0], {"kind": "fixed", "gap": gap}, 0.1, 1e-3, P, model="exact")
        cf = D.string_tension_static(gap, P)
        assert abs(r["tension"][-1] / cf["tension"] - 1) < 1e-9
        assert abs(cf["tension"] - P["mass"] * G * 0.725 / (2 * cf["sag"])) < 1e-12


def test_tension_from_the_v_of_the_string():
    gap = 1.1
    xh = _hang(D._mo_fixed(0, gap))
    pl, pr = D._mo_fixed(0, gap)
    t = D.string_tension_from_sag(pl, pr, xh, P["mass"])
    assert abs(t["tension"] / D.string_tension_static(gap, P)["tension"] - 1) < 1e-12 and t["residual_N"] < 1e-12
    acc = np.array([0.0, 0.5, 0.0])                        # 横に加速しているのに入れ忘れると釣り合いが破れる
    xs = xh + np.array([0.0, 0.05, 0.0])
    assert D.string_tension_from_sag(pl, pr, xs, P["mass"])["residual_N"] > 0.05
    assert D.string_tension_from_sag(pl, pr, xh, P["mass"], accel=acc)["residual_N"] > 0.1


# ── 7. 投げと受け ───────────────────────────────────────────────────────────────
def test_catch_time_apex_offset_and_state_reclassification(throw_sim):
    r = throw_sim
    md = r["mode"]
    fly = np.nonzero(md == "flying")[0]
    assert len(fly) > 100
    k0 = int(fly[0])
    k1 = k0 + int(np.nonzero(md[k0:] != "flying")[0][0])
    tr = D.diabolo_throw_catch_truth(r["x"][k0], r["v"][k0], D._mo_throw(1.0), P, t_max=2.0)
    assert abs((r["t"][k1] - r["t"][k0]) - tr["t_catch"]) <= 2e-3
    zmax = float(r["x"][k0:k1, 2].max())
    assert abs((zmax - tr["apex_z"]) - G * tr["t_apex"] * 1e-3 / 2) < 1e-5
    assert np.mean(D.diabolo_state_sequence(r["x"], r["sticks"], P) == md) >= 0.995


# ── 8, 9. 視覚 ──────────────────────────────────────────────────────────────────
def test_axis_from_one_frame_and_the_alarm(tilted_frame):
    img, a, c = tilted_frame
    r = D.diabolo_axis_from_image(img, CAM, P)
    assert D._angle_deg(r["axis"], a) < 0.3 and np.linalg.norm(r["center"] - c) < 1e-3 and r["ok"]
    img45 = D.diabolo_render(CAM, P, center=[0, 0.01, 0.6], axis=_axis(45, 135))
    assert not D.diabolo_axis_from_image(img45, CAM, P)["ok"]                    # 底の板が壁に隠れる
    blank = np.full((240, 320, 3), 0.55)
    tr = D.diabolo_track([img, blank], CAM, P)
    assert tr["ok"].tolist() == [True, False] and np.all(np.isnan(tr["center"][1])) and np.all(np.isfinite(tr["center"][0]))


def test_marker_phase_one_frame_and_spin_branch(tilted_frame):
    img, a, c = tilted_frame
    mp = D.diabolo_marker_phase(img, CAM, P, D.diabolo_axis_from_image(img, CAM, P))
    assert abs(math.remainder(mp["phase"] - 0.9, 2 * math.pi)) < 0.02
    assert abs(mp["smear"] - 2 * math.pi * 30 * 2e-3) < 0.2                      # 弧の幅は粗い(枝を選べれば足りる)
    fps, expo = 120.0, 2e-3
    dt = 1 / fps
    wrapped = []
    for rps in (10, 50, 70, 110):
        w = 2 * math.pi * rps
        phs = np.mod(0.4 + w * dt * np.arange(4), 2 * np.pi)
        sms = np.full(4, w * expo * 1.05)
        assert abs(D.diabolo_spin_from_markers(phs, sms, dt, expo)["omega"] / w - 1) < 1e-9
        if abs(D.diabolo_spin_from_markers(phs, sms, dt, expo, use_smear=False)["omega"] / w - 1) > 0.05:
            wrapped.append(rps)
    assert wrapped == [70, 110]                                                   # ナイキスト 60 rev/s を超えた分だけ折り返す


# ── 10. fail-closed と MJCF ─────────────────────────────────────────────────────
def test_spelling_breaks_fail_closed():
    st0 = {"x": [0, 0, .5], "v": [0, 0, 0], "omega": 0, "mode": "on_string"}
    fx = D._mo_fixed(0)
    probes = [lambda: D.diabolo_params("rde"), lambda: D.diabolo_params(mu_acel=1.0), lambda: D.diabolo_params(mass=-0.1),
              lambda: D.diabolo_simulate([0, 0, .5], [0, 0, 0], "fixed", 0.01, 1e-3, P, model="papr"),
              lambda: D.diabolo_simulate([0, 0, .5], [0, 0, 0], "fixd", 0.01, 1e-3, P),
              lambda: D.diabolo_simulate([0, 0, .5], [0, 0, 0], {"kind": "swing", "ampl": 0.1}, 0.01, 1e-3, P),
              lambda: D.diabolo_simulate([0, 0, .5], [0, 0, 0], 3.0, 0.01, 1e-3, P),
              lambda: D.diabolo_dynamics_step(st0, fx, fx, 1e-3, P, plane_rule="papr"),
              lambda: D.diabolo_dynamics_step(st0, fx, fx, 1e-3, P, rotation="cod"),
              lambda: D.diabolo_dynamics_step(dict(st0, mode="on-string"), fx, fx, 1e-3, P),
              lambda: D.diabolo_spheroid([0, 1, 1], [0, -1, 1], 1.45),
              lambda: D.diabolo_spheroid([0, np.nan, 1], [0, -0.5, 1], 1.45),
              lambda: D.diabolo_spin_from_markers([0.1], [0.1], 1e-2, 2e-3),
              lambda: D.diabolo_track([], CAM, P),
              lambda: D.diabolo_axis_from_image(np.zeros((240, 320)), CAM, P),
              lambda: D.diabolo_state_sequence(np.zeros((3, 3)), np.zeros((2, 2, 3)), P)]
    assert len(probes) == 16
    assert [i for i, fn in enumerate(probes) if not _raises(fn)] == []


def test_scene_mjcf_parts():
    root = ET.fromstring(D.diabolo_scene_mjcf(P))
    sp = root.find("tendon/spatial")
    assert sp is not None and sp.get("range") == "0 1.45" and [s.get("site") for s in sp if s.tag == "site"] == ["sL", "sD", "sR"]
    assert sum(1 for b in root.iter("body") if b.get("mocap") == "true") == 2
    assert abs(float(next(root.iter("inertial")).get("mass")) - P["mass"]) < 1e-12
    w = ET.fromstring(D.diabolo_scene_mjcf(P, wrap_axle=True))
    assert w.find("tendon/spatial/geom").get("geom") == "axle"
    assert _raises(lambda: D.diabolo_scene_mjcf(P, solref=(0.0005,)))


# ── 11. MuJoCo ──────────────────────────────────────────────────────────────────
def test_mujoco_tendon_matches_closed_form_and_exact_string():
    pytest.importorskip("mujoco")
    rest = D.diabolo_mujoco_simulate(P, _hang(D._mo_fixed(0)), [0, 0, 0], "fixed", 0.3)
    assert abs(rest["tension"][-1] / D.string_tension_static(1.1, P)["tension"] - 1) < 1e-4
    x0 = _hang(D._mo_linear_accel(0))
    re = D.diabolo_simulate(x0, [0, 0, 0], "linear_accel", 0.5, 1e-4, P, model="exact")
    rm = D.diabolo_mujoco_simulate(P, x0, [0, 0, 0], "linear_accel", 0.5)
    assert len(rm["t"]) == 501
    assert np.max(np.linalg.norm(rm["x"] - re["x"][::10], axis=1)) < 5e-3
