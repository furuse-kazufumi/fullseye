# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Physics invariants for the generic reusable-rocket PoC / 汎用再使用ロケット PoC の物理不変量。"""
from __future__ import annotations

import numpy as np
import pytest

import rocketlanding as rl


def test_propellant_depletes_mass_and_clips_the_last_thrust() -> None:
    """Propellant and body mass decrease, with no fictitious final impulse / 燃料・質量は減り、枯渇後の架空推力は出さない。"""
    fuel = rl.NOMINAL_FUEL
    fuels, masses = [], []
    for _ in range(24):
        fuel, delivered = rl.propellant_step(fuel, 180.0)
        fuels.append(fuel)
        masses.append(rl.DRY_MASS + fuel)
        assert 0.0 < delivered <= 180.0
    assert np.all(np.diff(fuels) < 0.0)
    assert np.all(np.diff(masses) < 0.0)

    left, clipped = rl.propellant_step(0.001, 1000.0)
    assert left == 0.0
    assert 0.0 < clipped < 1000.0
    assert rl.propellant_step(0.0, 1000.0) == (0.0, 0.0)


def test_zero_thrust_closed_form_has_downward_signed_velocity() -> None:
    """Zero thrust follows the signed free-fall equation / 推力ゼロでは符号付き速度が自由落下式に従う。"""
    z, vz = rl.free_fall_state(11.0, -2.0, 0.4)
    assert z == pytest.approx(11.0 - 2.0 * 0.4 - 0.5 * rl.G0 * 0.4**2)
    assert vz == pytest.approx(-2.0 - rl.G0 * 0.4)
    assert vz < -2.0


def test_mujoco_zero_thrust_agrees_with_the_independent_free_fall_truth() -> None:
    """The simulator plant matches free fall before contact / 接触前の MuJoCo プラントを閉形式真値で検算する。"""
    err = rl.mujoco_free_fall_check()
    assert err["height_error_m"] < 1e-9
    assert err["velocity_error_mps"] < 1e-9


def test_seed_fixed_wind_repeats_but_other_seed_changes() -> None:
    """Seed controls the complete wind input / seed が風入力を完全に再現する。"""
    a = np.vstack([rl.fixed_wind(41, t, 12.0) for t in (0.0, 0.7, 2.1)])
    b = np.vstack([rl.fixed_wind(41, t, 12.0) for t in (0.0, 0.7, 2.1)])
    changed = np.vstack([rl.fixed_wind(42, t, 12.0) for t in (0.0, 0.7, 2.1)])
    assert np.array_equal(a, b)
    assert not np.array_equal(a, changed)
    assert np.all(a[:, 2] == 0.0)


def test_failure_cases_reduce_fuel_or_exceed_nominal_wind() -> None:
    """Failure cases cross a documented plant limit / 失敗ケースは文書化したプラント限界を越える。"""
    nominal = rl.case_spec("nominal", 3)
    shortage = rl.case_spec("fuel_shortage", 7)
    strong_wind = rl.case_spec("strong_wind", 19)
    assert shortage.fuel_kg < nominal.fuel_kg
    assert strong_wind.wind_n > nominal.wind_n
    with pytest.raises(ValueError, match="nominal"):
        rl.case_spec("typo", 3)
