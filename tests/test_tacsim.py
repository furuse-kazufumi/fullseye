# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tacsim の門(視触覚センサ = 弾性膜 + カメラ: Hertz 接触の閉形式、3 色照明の合成、フォトメトリックステレオの逆算)。

第 2 実装の照合を中心に:
 1. 複合弾性率の極限、Hertz の恒等式(a² = Rδ、F の 2 形、p0 の 2 形)、圧力の面積分 = F、線接触の線積分 = F/L
 2. 表面変位の内外連続(値 δ/2・傾き −a/R)、スロープ閉形式(導出)を数値微分で検算
 3. 解析法線 = photometric.surface_normals(h/pitch)(中央 < 0.05°)、合成の各チャネル = photometric.render_lambertian
 4. Frankot-Chellappa の往復、Woodham の厳密性(ambient を引く)
 5. 当てはめ経路(a ≤ 1 %、F ≤ 2 %)、δ 経路(≤ 2 %)、模型なしのリングは −0.7 px/a の予測どおり内側、measure.fit_circle との一致
 6. 窓打ち切りの不足 = ū_z(r_max)/δ(閉形式)、ambient の寝かせ = ambient/sin(仰角)(予測と 1 pt)
 7. 構造のある入力: 4 形状の往復、円柱の幾何接触半幅 √(2Rd − d²)、照明の rank、fail-closed(綴りを壊した shape・Hertz でない組・光源 2 灯)
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import measure as FM
import photometric as PH
import tacsim as T

E, NU, R = 0.2e6, 0.48, 3.0e-3
ES = T.combined_modulus(E, NU)
HZ = T.hertz_sphere(0.08, R, ES)
A, D = HZ["a"], HZ["delta"]
LIGHTS = T.membrane_lights(55.0)
AMB = 0.03


@pytest.fixture(scope="module")
def scene():
    gh = T.membrane_indent_sphere(HZ, 256, 16.0e-3)
    rgb = T.membrane_render_rgb(gh["normals"], LIGHTS, ambient=AMB)
    rec = T.membrane_recover(rgb, LIGHTS, gh["pitch"], ambient=AMB)
    return gh, rgb, rec


def _pct(v, t):
    return 100.0 * (v - t) / t


# ── 1. 閉形式 ───────────────────────────────────────────────────────────────────
def test_combined_modulus_limits_and_fail_closed():
    assert ES == pytest.approx(E / (1 - NU * NU), rel=1e-12)
    assert T.combined_modulus(E, NU, E, NU) == pytest.approx(ES / 2, rel=1e-12)
    assert T.combined_modulus(E, NU, 1e30, 0.0) == pytest.approx(ES, rel=1e-6)   # 相手がほぼ剛体
    for bad in ((0.0, 0.3), (E, 1.0), (E, 0.3, -1.0, 0.0)):
        with pytest.raises(ValueError):
            T.combined_modulus(*bad)


@pytest.mark.parametrize("F", [0.005, 0.02, 0.08, 0.5])
def test_hertz_identities(F):
    hz = T.hertz_sphere(F, R, ES)
    a, d, p0 = hz["a"], hz["delta"], hz["p0"]
    assert a ** 3 == pytest.approx(3 * F * R / (4 * ES), rel=1e-12)
    assert a * a == pytest.approx(R * d, rel=1e-12)
    assert T.hertz_force(R, ES, a=a) == pytest.approx(F, rel=1e-12)
    assert T.hertz_force(R, ES, delta=d) == pytest.approx(F, rel=1e-12)
    assert p0 == pytest.approx(2 * ES * a / (math.pi * R), rel=1e-12)
    assert hz["pm"] == pytest.approx(2 * p0 / 3, rel=1e-12)
    with pytest.raises(ValueError):
        T.hertz_force(R, ES)
    with pytest.raises(ValueError):
        T.hertz_force(R, ES, a=a, delta=d)
    with pytest.raises(ValueError):
        T.hertz_sphere(-F, R, ES)


def test_pressure_integrals_equal_load():
    trapz = getattr(np, "trapezoid", None) or np.trapz
    rr = np.linspace(0, A, 40001)
    disk = 2 * math.pi * trapz(T.hertz_pressure(rr, A, HZ["p0"]) * rr, rr)
    assert disk == pytest.approx(0.08, rel=2e-4)
    cyl = T.hertz_cylinder(50.0, R, ES)
    xs = np.linspace(-cyl["b"], cyl["b"], 40001)
    line = trapz(cyl["p0"] * np.sqrt(np.maximum(0, 1 - (xs / cyl["b"]) ** 2)), xs)
    assert line == pytest.approx(50.0, rel=2e-4)
    assert cyl["b"] ** 2 == pytest.approx(4 * 50 * R / (math.pi * ES), rel=1e-12)
    assert cyl["pm"] == pytest.approx(math.pi / 4 * cyl["p0"], rel=1e-12)
    assert T.hertz_pressure(np.array([A, 2 * A]), A, HZ["p0"]).tolist() == [0.0, 0.0]


# ── 2. 表面変位とスロープの導出 ────────────────────────────────────────────────────
def test_surface_uz_continuity_and_slope_derivation():
    r = np.linspace(0, A, 300)
    uz = T.hertz_surface_uz(r, A, D, R)
    assert uz[0] == pytest.approx(D, abs=1e-15)
    assert np.max(np.abs(uz - (D - r * r / (2 * R)))) < 1e-12
    eps = 1e-7 * A
    lo = T.hertz_surface_uz(np.array([A - eps]), A, D, R)[0]
    hi = T.hertz_surface_uz(np.array([A + eps]), A, D, R)[0]
    assert abs(lo - hi) < 1e-9 and lo == pytest.approx(D / 2, rel=1e-5)
    rr = np.linspace(0.05 * A, 6 * A, 5000)
    h = 1e-9
    num = -(T.hertz_surface_uz(rr + h, A, D, R) - T.hertz_surface_uz(rr - h, A, D, R)) / (2 * h)
    assert np.max(np.abs(num - T._hertz_slope(rr, A, R))) < 1e-6 * (A / R)
    assert T._hertz_slope(np.array([A]), A, R)[0] == pytest.approx(A / R, rel=1e-12)
    far = 40 * A                                                           # 遠方場 ū_z → F/(πE* r)(Boussinesq の点荷重)
    assert T.hertz_surface_uz(np.array([far]), A, D, R)[0] == pytest.approx(0.08 / (math.pi * ES * far), rel=2e-3)
    with pytest.raises(ValueError):
        T.hertz_surface_uz(r, A, 1.1 * D, R)                                  # Hertz でない組


# ── 3. 合成の第 2 実装 ───────────────────────────────────────────────────────────
def test_analytic_normals_match_surface_normals_and_render(scene):
    gh, rgb, _ = scene
    n2 = PH.surface_normals(gh["h"] / gh["pitch"])
    ang = PH.angular_error_deg(gh["normals"], n2)
    assert float(np.median(ang)) < 0.05 and float(np.percentile(ang, 99)) < 0.6     # 中心差分の格子で近い
    for k in range(3):
        ref = PH.render_lambertian(gh["normals"], 1.0, LIGHTS[k], ambient=AMB)
        assert np.allclose(rgb[..., k], ref, atol=1e-6)
    assert gh["contact"].sum() == pytest.approx(math.pi * (A / gh["pitch"]) ** 2, rel=0.03)
    with pytest.raises(ValueError):
        T.membrane_indent_sphere(HZ, 256, 3 * A)                                 # 窓が狭すぎる
    with pytest.raises(ValueError):
        T.membrane_render_rgb(gh["normals"], LIGHTS[:2])


def test_lights_rank_and_fail_closed():
    L = T.membrane_lights(55.0)
    assert L.shape == (3, 3) and np.allclose(np.linalg.norm(L, axis=1), 1.0)
    assert np.linalg.matrix_rank(L) == 3
    with pytest.raises(ValueError):
        T.membrane_lights(55.0, azimuths_deg=(0.0, 120.0))
    with pytest.raises(ValueError):
        T.membrane_lights(0.0)
    with pytest.raises(ValueError):
        T.membrane_lights(90.0, azimuths_deg=(0.0, 120.0, 240.0))                # 真上 3 灯 = 同一方向


# ── 4. 逆算の厳密性 ─────────────────────────────────────────────────────────────
def test_frankot_chellappa_roundtrip_and_woodham_exactness(scene):
    gh, _, rec = scene
    inside = gh["r"] < 1.5 * A
    z = PH.integrate_normals(gh["normals"]) * gh["pitch"]
    rms = np.sqrt(np.mean(((z - z[inside].mean()) - (gh["h"] - gh["h"][inside].mean()))[inside] ** 2))
    assert rms < 0.01 * D
    ang = PH.angular_error_deg(rec["normals"], gh["normals"])
    lit = np.min(np.stack([gh["normals"] @ LIGHTS[k] for k in range(3)], 0), 0) > 0.05
    assert float(np.median(ang[lit])) < 0.05 and float(np.percentile(ang[lit], 99)) < 1.0
    assert rec["height"].shape == gh["h"].shape and abs(rec["height"].mean()) < 1e-12


@pytest.mark.parametrize("F", [0.02, 0.05, 0.12])
def test_fit_and_delta_routes_within_target(F):
    hz = T.hertz_sphere(F, R, ES)
    gh = T.membrane_indent_sphere(hz, 256, 16.0e-3)
    rec = T.membrane_recover(T.membrane_render_rgb(gh["normals"], LIGHTS, ambient=AMB), LIGHTS, gh["pitch"], ambient=AMB)
    fit = T.contact_radius_fit(rec["normals"], gh["X"], gh["Y"], R, gh["pitch"])
    assert abs(_pct(fit["a"], hz["a"])) < 1.0
    assert abs(_pct(T.hertz_force(R, ES, a=fit["a"]), F)) < 2.0
    assert fit["delta"] == pytest.approx(fit["a"] ** 2 / R, rel=1e-12)
    dB = T.membrane_delta_from_normals(rec["normals"], gh["X"], gh["Y"], gh["pitch"])
    assert abs(_pct(dB, hz["delta"])) < 2.0
    assert abs(_pct(T.hertz_force(R, ES, delta=dB), F)) < 3.0


def test_ring_is_model_free_and_biased_as_predicted(scene):
    gh, _, rec = scene
    ring = T.contact_radius_ring(rec["height"], gh["pitch"])
    a_px = A / gh["pitch"]
    bias = _pct(ring["a"], A)
    assert bias < 0.0 and abs(bias - 100 * ring["bias_px_per_a"] / a_px) < 1.5
    assert abs(_pct(ring["a_circle"], ring["a"])) < 1.0 and ring["rms_px"] < 1.0
    assert len(ring["radii_px"]) == 72 and abs(ring["cy"] - 127.5) < 0.3 and abs(ring["cx"] - 127.5) < 0.3
    ph = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    pts = np.column_stack([60 + 20 * np.sin(ph), 70 + 20 * np.cos(ph)])
    fc = FM.fit_circle(pts)
    assert fc["r"] == pytest.approx(20.0, abs=1e-9) and fc["cy"] == pytest.approx(60.0, abs=1e-9)
    with pytest.raises(ValueError):
        T.contact_radius_ring(np.zeros((64, 64)), gh["pitch"])                # へこみなし


def test_fit_on_true_normals_and_scaling_exponent():
    gh = T.membrane_indent_sphere(HZ, 256, 16.0e-3)
    fit = T.contact_radius_fit(gh["normals"], gh["X"], gh["Y"], R, gh["pitch"], centre_xy=(0.0, 0.0))
    assert abs(_pct(fit["a"], A)) < 0.3 and fit["rms"] < 0.01 * (A / R)
    Fs = np.array([0.02, 0.05, 0.12])
    a_fit = []
    for F in Fs:
        hz = T.hertz_sphere(F, R, ES)
        g = T.membrane_indent_sphere(hz, 256, 16.0e-3)
        a_fit.append(T.contact_radius_fit(g["normals"], g["X"], g["Y"], R, g["pitch"], centre_xy=(0.0, 0.0))["a"])
    assert np.polyfit(np.log(Fs), np.log(a_fit), 1)[0] == pytest.approx(1 / 3, abs=0.01)


# ── 6. 窓打ち切りと ambient(間違いの量が閉形式で予測できる) ──────────────────────────
def test_window_tail_and_ambient_bias_match_closed_form(scene):
    gh, rgb, _ = scene
    d_none = T.membrane_delta_from_normals(gh["normals"], gh["X"], gh["Y"], gh["pitch"], tail="none")
    d_tail = T.membrane_delta_from_normals(gh["normals"], gh["X"], gh["Y"], gh["pitch"])
    r_max = float(min(np.abs(gh["X"]).max(), np.abs(gh["Y"]).max()))
    tail_cf = T.hertz_surface_uz(np.array([r_max]), A, D, R)[0] / D
    assert abs(-_pct(d_none, D) / 100 - tail_cf) < 0.01 and abs(_pct(d_tail, D)) < 1.0
    d0 = T.membrane_delta_from_normals(T.membrane_recover(rgb, LIGHTS, gh["pitch"])["normals"], gh["X"], gh["Y"], gh["pitch"])
    assert abs(-_pct(d0, D) - 100 * AMB / math.sin(math.radians(55.0))) < 1.0
    with pytest.raises(ValueError):
        T.membrane_delta_from_normals(gh["normals"], gh["X"], gh["Y"], gh["pitch"], tail="bousinesq")   # 綴りを壊す


# ── 7. 構造のある入力 ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("shape", T.SHAPES)
def test_shapes_roundtrip(shape):
    g = T.membrane_indent_shape(shape, 0.3e-3, n=128, fov=6.0e-3, R=R)
    rec = T.membrane_recover(T.membrane_render_rgb(g["normals"], LIGHTS, ambient=AMB), LIGHTS, g["pitch"], ambient=AMB)
    c = g["contact"]
    assert c.any() and not c.all()
    zr = rec["height"] - rec["height"][~c].mean()
    ht = g["h"] - g["h"][~c].mean()
    assert np.sqrt(np.mean((zr[c] - ht[c]) ** 2)) < 0.10 * 0.3e-3
    assert -0.3e-3 - 1e-12 <= g["h"].min() < -0.3e-3 + 2e-6              # 画素中心が原点に無い分(pitch²/2R ≈ 0.4 µm)だけ浅い
    if shape == "cylinder":
        half = 0.5 * c.sum(axis=1).max() * g["pitch"]
        assert abs(half - math.sqrt(2 * R * 0.3e-3 - 0.3e-3 ** 2)) < g["pitch"]
        assert np.array_equal(c[0], c[-1])                                  # 軸方向に不変
    if shape == "sphere":
        assert c.sum() == pytest.approx(math.pi * (math.sqrt(2 * R * 0.3e-3 - 0.3e-3 ** 2) / g["pitch"]) ** 2, rel=0.03)
    if shape == "edge":
        assert np.array_equal(c[0], c[-1]) and c[:, 0].sum() == 0


def test_shape_fail_closed():
    with pytest.raises(ValueError):
        T.membrane_indent_shape("spere", 0.3e-3)
    with pytest.raises(ValueError):
        T.membrane_indent_shape("sphere", 4e-3, R=3e-3)
    with pytest.raises(ValueError):
        T.membrane_indent_shape("edge", 0.3e-3, edge_deg=90.0)
    with pytest.raises(ValueError):
        T.membrane_recover(np.zeros((8, 8)), LIGHTS, 1e-5)
    with pytest.raises(ValueError):
        T.contact_radius_fit(np.zeros((8, 8, 3)), np.zeros((8, 8)), np.zeros((9, 8)), R, 1e-5)
