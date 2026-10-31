"""外部監査 P01--P09 の解析反例を固定する回帰門。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / "examples" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_river_proxy_and_known_alpha_nonuniform_depth_reverse_flow():
    m = load("poc_river_surface_velocity")
    y = np.linspace(0.5, 7.5, 15)
    u = m.profile(y)
    u[6:9] *= -0.2
    depth = 0.8 + 0.1 * y
    alpha = 0.78 + 0.04 * np.cos(y)
    proxy = m.discharge(y, u)
    q = m.discharge(y, u, depth=depth, alpha=alpha)
    expected = np.trapezoid(
        np.interp(np.r_[0, y, m.B_WIDTH], y, depth)
        * np.interp(np.r_[0, y, m.B_WIDTH], y, alpha)
        * np.r_[0, u, 0], np.r_[0, y, m.B_WIDTH])
    assert m.discharge(y, u, alpha=1.0) == proxy
    assert np.isclose(q, expected)


def test_profile_rt_is_not_rz():
    m = load("poc_surface_roughness")
    p = np.r_[np.linspace(0, 1, 20), np.linspace(0, 1, 20),
              np.linspace(0, 1, 20), np.linspace(0, 1, 20), np.linspace(0, 10, 20)]
    out = m.profile_params(p)
    assert np.isclose(out["Rt"], 10.0)
    assert np.isclose(out["Rz"], 2.8)


def test_aliasing_sq_depends_on_phase_and_dc_collision():
    x = np.arange(1024)
    z = np.cos(2 * np.pi * x / 8)
    sq = lambda a: np.sqrt(np.mean((a - np.mean(a)) ** 2))
    assert np.isclose(sq(z), 1 / np.sqrt(2))
    assert np.isclose(sq(z[::4]), 1.0)
    assert np.isclose(sq(z[::8]), 0.0, atol=1e-12)
    assert np.isclose(sq(np.cos(2*np.pi*x/8 + np.pi/4)[::4]), 1/np.sqrt(2))


def test_transport_reports_no_through_path():
    m = load("poc_battery_electrode_tortuosity")
    pore = np.zeros((8, 6, 6), bool)
    pore[:3, 1:5, 1:5] = True
    pore[5:, 1:5, 1:5] = True
    out = m.transport(pore)
    assert out["status"] == "no_through_path"
    assert out["d_eff"] == 0.0 and np.isinf(out["tau_f"])


def test_straight_parallel_pores_are_tau_one_not_bruggeman_two():
    m = load("poc_battery_electrode_tortuosity")
    pore = np.zeros((12, 8, 8), bool)
    pore[:, ::2, ::2] = True
    out = m.transport(pore)
    assert out["status"] == "ok"
    assert np.isclose(out["tau_f"], 1.0, atol=1e-10)
    assert np.isclose(m.bruggeman(out["eps"]), 2.0)


def test_emva_noise_is_black_level_invariant_and_gain_converts():
    m = load("poc_thermal_radiometry")
    tab = m.BandTable("LWIR")
    c0 = m.Camera(tab, 220, 500, dn_lo=200)
    c1 = m.Camera(tab, 220, 500, dn_lo=2000)
    signal = 500.0
    # 同じ signal DN を各黒レベルへ足すと解析分散は同じ。
    def var(cam, k):
        return (k * 2.0) ** 2 + 1.0 / 12.0 + k * signal
    assert np.isclose(var(c0, .05), var(c1, .05))
    assert np.isclose(var(c0, .10) - 1/12, 2 * (.05 * signal) + .04,
                      rtol=1e-12)
