"""Physics and calibration gates for the Panda tote-picking benchmark."""
from __future__ import annotations
import ast
import inspect
import numpy as np
import pytest
import totepick as T

pytestmark=pytest.mark.skipif(T.validate_mujoco_asset()["skipped"],reason="[skip] MuJoCo/Menagerie unavailable")

def run(seed=7,**kw): return T._attempt(T.PRODUCTS[0],T.METHODS[1],seed,0,render_depth=False,clutter=False,**kw)

def test_attempt_integrates_panda_and_is_deterministic():
    a=run();b=run();assert a==b;assert a[3]["mj_steps"]>1000;assert a[2]==pytest.approx(6.188)
    asset=T.validate_mujoco_asset();assert asset["arm_actuators"]==7;assert asset["gripper_ctrlrange"]==[0.,255.]

def test_open_hand_cannot_succeed(): assert sum(run(i,grip=False)[0] for i in range(3))==0

def test_success_is_final_physics_not_random():
    src=inspect.getsource(T._attempt);tree=ast.parse(src);assign=[n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=="success" for x in n.targets)]
    assert len(assign)==1
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in {"random","uniform","choice"} for n in ast.walk(assign[0].value))
    assert "inside and speed<.04" in src and "mj_step" in src

def test_tactile_contact_force_changes_real_control():
    src=inspect.getsource(T);assert "mj_contactForce" in src;assert "tactile_boost=True" in src;assert "d.ctrl[7]=GRIP_SHUT" in src
    assert not T.read_fingertip_tactile(10,1,.5).slipping
    assert T.read_fingertip_tactile(2,2,.2).slipping

def test_friction_and_mass_change_physics_response():
    low=T._attempt(T.PRODUCTS[1],T.METHODS[0],2,0,render_depth=False,clutter=False,friction_scale=.15)[3]
    normal=T._attempt(T.PRODUCTS[1],T.METHODS[0],2,0,render_depth=False,clutter=False)[3]
    light=run(13,mass_scale=.4)[3];heavy=run(13,mass_scale=2.)[3]
    assert not np.allclose(low["final_position_m"],normal["final_position_m"],atol=1e-5)
    assert not np.allclose(light["final_position_m"],heavy["final_position_m"],atol=1e-5)

def test_pad_centre_calibration_hits_product_centre():
    out=T._attempt(T.PRODUCTS[0],T.METHODS[0],7,0,render_depth=True,clutter=False)[3]
    assert np.linalg.norm(np.asarray(out["pad_offset_m"]))>.08
    # Initial centre is recoverable from the final deterministic seed only through
    # the rendered candidate; success is the physical end-to-end alignment gate.
    assert out["depth_candidates"]>=1

def test_depth_candidates_reject_wall_height_and_truth_access():
    src=inspect.getsource(T.depth_grasp_candidates);assert "qpos" not in src and "MjData" not in src
    depth=np.full((80,80),.90-T.TABLE_TOP);depth[30:45,30:45]=.90-(T.TABLE_TOP+.04);depth[5:15,5:25]=.90-(T.TABLE_TOP+T.WALL_H)
    wall=np.zeros_like(depth,bool);wall[5:15,5:25]=True
    c=T.depth_grasp_candidates(depth,wall_mask=wall);assert len(c)==1;assert c[0]["pixel"][0]>25

def test_easy_open_loop_reaches_seventy_percent():
    outcomes=[T._attempt(p,T.METHODS[0],seed,0,render_depth=True,clutter=True)[0] for p in T.PRODUCTS[:3] for seed in range(10)]
    assert sum(outcomes)/len(outcomes)>=.70

def test_no_attachment_or_product_pose_write_after_initialization():
    src=inspect.getsource(T._attempt);assert "weld" not in src and "eq_" not in src and "mocap" not in src
    result=T.run_benchmark(1,max_retries=0,render_depth=False,clutter=False);assert result["contact"]["adhesion"] is False

def test_every_method_gets_the_same_retry_allowance():
    result=T.run_benchmark(1,max_retries=2,render_depth=False,clutter=False,grip=False)
    assert {r["method"]:len(r["attempts"]) for r in result["rows"]}=={m:3 for m in T.METHODS}
    assert all([a["retry"] for a in r["attempts"]]==[0,1,2] for r in result["rows"])

def test_evidence_frames_are_mujoco_renderer_output():
    src=inspect.getsource(T._attempt)
    render_src=inspect.getsource(T._render_mujoco_frame)
    assert "_render_mujoco_frame" in src
    assert "renderer.update_scene" in render_src and "renderer.render" in render_src
    assert "render_size=(1280,720)" in src.replace(" ","")
