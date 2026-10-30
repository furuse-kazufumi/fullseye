"""Physics honesty gates for the tote-picking benchmark."""
from __future__ import annotations

import ast
import inspect

import numpy as np
import pytest

import totepick as T


pytestmark = pytest.mark.skipif(T.validate_mujoco_asset()["skipped"], reason="[skip] MuJoCo/Menagerie unavailable")


def run(seed=7, **kw):
    return T._attempt(T.PRODUCTS[2], T.METHODS[1], seed, 0, render_depth=False, **kw)


def test_attempt_integrates_mujoco_and_is_deterministic():
    a = run(); b = run()
    assert a == b
    assert a[3]["mj_steps"] > 1000
    assert a[2] == pytest.approx(4.336)


def test_open_hand_cannot_succeed():
    outcomes = [run(i, grip=False)[0] for i in range(3)]
    assert sum(outcomes) == 0


def test_success_definition_is_final_truth_only():
    src = inspect.getsource(T._attempt)
    tree = ast.parse(src)
    # Random calls exist for initial pose/noise, but no random comparison decides success.
    success_assign = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                      and any(isinstance(x, ast.Name) and x.id == "success" for x in n.targets)]
    assert len(success_assign) == 1
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr in {"random", "uniform", "choice"}
                   for n in ast.walk(success_assign[0].value))
    assert "inside and speed<.03" in src


def test_tactile_comes_from_contact_force_and_changes_control():
    src = inspect.getsource(T)
    assert "mj_contactForce" in src
    assert "data.ctrl=np.clip" in src
    safe = T.read_fingertip_tactile(10, 1, .5, (0, 0))
    slip = T.read_fingertip_tactile(2, 2, .2, (0, 0))
    assert not safe.slipping and slip.slipping


def test_friction_and_mass_change_physics_response():
    # Same initial condition; these are measured contact/motion responses, not odds.
    low = run(11, friction_scale=.25)[3]
    nominal = run(11, friction_scale=1.)[3]
    light = run(13, mass_scale=.4)[3]
    heavy = run(13, mass_scale=2.)[3]
    assert (low["tactile_events"], low["final_position_m"]) != (nominal["tactile_events"], nominal["final_position_m"])
    assert not np.allclose(light["final_position_m"], heavy["final_position_m"], atol=1e-5)


def test_perception_has_no_truth_state_access():
    src = inspect.getsource(T.depth_grasp_candidates)
    assert "qpos" not in src and "MjData" not in src
    depth=np.ones((40,50)); depth[5:15,8:20]=.3
    assert T.depth_grasp_candidates(depth)


def test_no_attachment_or_product_pose_write_after_initialization():
    src=inspect.getsource(T._attempt)
    assert "weld" not in src and "eq_" not in src and "mocap" not in src[src.find("pg="):].replace("mocap_pos[moc]", "")
    result=T.run_benchmark(1, max_retries=0, render_depth=False)
    assert result["contact"]["adhesion"] is False
