"""gaits(四足歩容生成)の CPU 回帰。合成4脚モデルで脚検出とトロット軌道を確認。"""
from __future__ import annotations
import numpy as np
import pytest

mujoco = pytest.importorskip("mujoco")
import gaits  # noqa: E402

_XML = """
<mujoco><worldbody>
 <body name="trunk" pos="0 0 .3"><freejoint/>
  <geom type="box" size=".2 .1 .05"/>
  <body name="fl" pos=".2 .1 0"><joint name="FL_thigh_joint" type="hinge" axis="0 1 0"/>
    <geom type="capsule" size=".02 .08"/>
    <body name="flc" pos="0 0 -.16"><joint name="FL_calf_joint" type="hinge" axis="0 1 0"/><geom type="capsule" size=".02 .08"/></body></body>
  <body name="fr" pos=".2 -.1 0"><joint name="FR_thigh_joint" type="hinge" axis="0 1 0"/>
    <geom type="capsule" size=".02 .08"/>
    <body name="frc" pos="0 0 -.16"><joint name="FR_calf_joint" type="hinge" axis="0 1 0"/><geom type="capsule" size=".02 .08"/></body></body>
  <body name="rl" pos="-.2 .1 0"><joint name="RL_thigh_joint" type="hinge" axis="0 1 0"/>
    <geom type="capsule" size=".02 .08"/>
    <body name="rlc" pos="0 0 -.16"><joint name="RL_calf_joint" type="hinge" axis="0 1 0"/><geom type="capsule" size=".02 .08"/></body></body>
  <body name="rr" pos="-.2 -.1 0"><joint name="RR_thigh_joint" type="hinge" axis="0 1 0"/>
    <geom type="capsule" size=".02 .08"/>
    <body name="rrc" pos="0 0 -.16"><joint name="RR_calf_joint" type="hinge" axis="0 1 0"/><geom type="capsule" size=".02 .08"/></body></body>
 </body>
</worldbody></mujoco>
"""


def _model():
    return mujoco.MjModel.from_xml_string(_XML)


def test_detects_four_legs():
    legs = gaits._leg_joints(_model())
    assert set(legs) == {("F", "L"), ("F", "R"), ("R", "L"), ("R", "R")}
    for v in legs.values():
        assert "thigh" in v and "calf" in v


def test_trot_shape_and_motion():
    m = _model()
    home = np.zeros(m.nq); home[3] = 1.0        # 単位クォータニオン
    traj = gaits.quadruped_trot(m, home, n_frames=30)
    assert traj.shape == (30, m.nq)
    assert np.abs(traj - home).max() > 0.1      # 実際に動く


def test_trot_diagonal_in_phase():
    """対角脚(FL,RR)が同位相・(FR,RL)が逆位相。"""
    m = _model()
    home = np.zeros(m.nq); home[3] = 1.0
    legs = gaits._leg_joints(m)
    traj = gaits.quadruped_trot(m, home, n_frames=40)
    fl = traj[:, legs[("F", "L")]["thigh"]]
    rr = traj[:, legs[("R", "R")]["thigh"]]
    fr = traj[:, legs[("F", "R")]["thigh"]]
    assert np.corrcoef(fl, rr)[0, 1] > 0.95      # 同位相
    assert np.corrcoef(fl, fr)[0, 1] < -0.95     # 逆位相


def test_build_unknown_is_none():
    assert gaits.build(_model(), np.zeros(_model().nq), "gallop") is None
