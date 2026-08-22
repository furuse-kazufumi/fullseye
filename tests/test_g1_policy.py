"""g1_policy_bridge: numpy 方策推論・チェックポイント読込・学習曲線パーサのテスト。

方策 MLP は「brax 純正推論との数値一致」が本体の検証(セッションで max 誤差 1.8e-7 を
実測済み)だが、CI では brax/WSL に依存できないので、ここでは
  * 合成パラメータでの前向き計算の代数的正しさ(手計算と一致)
  * 実チェックポイントがあれば読込形状と実ロールアウトのスモーク
  * 学習ログパーサの正確さ
を押さえる。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import g1_policy_bridge as G  # noqa: E402

_CKPT = "C:/dev/projects/onocollo-complete/out/humanoid/mjx_g1_walk12c_ckpt_15728640.pkl"
_REF = "C:/dev/projects/onocollo-complete/out/humanoid/g1_walk_cycle_straight.npy"
_XML = "C:/dev/projects/mujoco_menagerie/unitree_g1/scene.xml"


def _toy_policy(obs=4, act=2):
    """1 隠れ層の合成方策: 手で追える小ささで forward の式を固定する。"""
    W0 = np.array([[0.5, -0.2, 0.1],
                   [0.0, 0.3, -0.4],
                   [0.2, 0.1, 0.0],
                   [-0.1, 0.0, 0.2]])
    b0 = np.array([0.01, -0.02, 0.03])
    W1 = np.zeros((3, 2 * act))
    W1[0, 0] = 1.0
    W1[1, 1] = -1.0
    b1 = np.array([0.1, 0.0, 0.0, 0.0])
    return {"mean": np.zeros(obs), "std": np.ones(obs),
            "layers": [(W0, b0), (W1, b1)], "obs_size": obs, "act_size": act}


def test_policy_action_matches_hand_computation():
    pol = _toy_policy()
    obs = np.array([1.0, -0.5, 0.25, 2.0])
    h = obs @ pol["layers"][0][0] + pol["layers"][0][1]
    h = h * (1.0 / (1.0 + np.exp(-h)))                     # swish
    out = h @ pol["layers"][1][0] + pol["layers"][1][1]
    expect = np.tanh(out[:2])                               # 決定論 = tanh(loc)
    got = G.policy_action(pol, obs)
    assert np.allclose(got, expect, atol=1e-12)


def test_policy_action_normalizes_observation():
    pol = _toy_policy()
    pol["mean"] = np.array([1.0, 1.0, 1.0, 1.0])
    pol["std"] = np.array([2.0, 2.0, 2.0, 2.0])
    raw = np.array([3.0, 1.0, 5.0, -1.0])
    same = G.policy_action(_toy_policy(), (raw - pol["mean"]) / pol["std"])
    assert np.allclose(G.policy_action(pol, raw), same)


def test_policy_action_is_bounded_and_overflow_safe():
    pol = _toy_policy()
    a = G.policy_action(pol, np.array([1e6, -1e6, 1e6, -1e6]))
    assert np.all(np.isfinite(a)) and np.all(np.abs(a) <= 1.0)


def test_training_curves_parses_progress_lines(tmp_path):
    log = tmp_path / "walk.log"
    log.write_text(
        "[g1_x] step     100 (5/s) reward=1.5 ep_len=10 (0.20s) perr=0.17 crash=0.00\n"
        "noise line without step\n"
        "[g1_x] step     200 (6/s) reward=2.5 ep_len=20 (0.40s) perr=0.10 crash=0.50\n",
        encoding="utf-8")
    c = G.training_curves(str(log))
    assert list(c["step"]) == [100.0, 200.0]
    assert list(c["reward"]) == [1.5, 2.5]
    assert list(c["crash"]) == [0.0, 0.5]


needs_ckpt = pytest.mark.skipif(
    not (os.path.exists(_CKPT) and os.path.exists(_REF) and os.path.exists(_XML)),
    reason="実チェックポイント/参照/シーンが無い環境ではスキップ")


@needs_ckpt
def test_load_policy_real_checkpoint_shapes():
    p = G.load_policy(_CKPT)
    assert p["obs_size"] == 100 and p["act_size"] == 29
    assert len(p["layers"]) == 5                            # 4 hidden + head
    assert p["layers"][-1][1].shape == (58,)                # (loc, raw_scale)


@needs_ckpt
def test_session_smoke_rollout_short():
    s = G.G1PolicySession(_CKPT, _REF)
    obs = s.reset(0)
    assert obs.shape == (100,)
    for _ in range(25):                                     # 0.5 s で十分(スモーク)
        obs, done, info = s.step(obs)
        if done:
            break
    qp = np.stack(s.qpos_hist)
    assert len(qp) >= 2 and np.all(np.isfinite(qp))
    assert qp[-1, 0] > qp[0, 0] - 0.05                      # 後ろに吹っ飛んでいない


@needs_ckpt
def test_session_rejects_mismatched_vision_flag():
    with pytest.raises(ValueError):
        G.G1PolicySession(_CKPT, _REF, vision=True)         # mimic ckpt に vision 環境
