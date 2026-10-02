"""19 巡目の門: けん玉の連続技(もしかめ = 大皿 ↔ 中皿、3 皿 = 大皿 → 小皿 → 中皿)。

実行: py -3.11 -m pytest -q tests/test_kendama_combo.py(実演の組み立ては examples/poc_kendama.py の _combo_run)
門:
 1. 放つ: 皿から離れた後の頂点 = 離れた瞬間の高さ + v²/2g(真空、2e-6 m: 1 ms の標本の最大値)、飛翔中の ½v² + gz は 1e-9 で不変
 2. 位置と速度を目標にする制御: 上限(v_max・a_max)を最後の 1 歩も破らない、(x*, v*) に着く
 3. 対照: 旧来の位置だけの制御は頂点 20 cm で 1 回も受けられない(too_fast)、新しい制御は相対速さ < 0.5 m/s で受ける
 4. 真値で もしかめ・3 皿 各 10 回連続: 毎回「昇ってから下降中に受ける」、持ち替え中の隙間 > 0、糸は張らない、角速度 ≤ 30 rad/s
 5. 画像だけの知覚で 振り上げ + もしかめ 10 回・3 皿 10 回(飛び始めは画像から)
 6. 後方互換(kendama_clearance の R_ken、camera_perceiver の flight_from)と協会の級の表
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np
import pytest

# ★2026-10-02: 以前は examples/ を sys.path の先頭に**入れっぱなし**にしていた。同じ xdist ワーカーで後から
#   ``import event_camera`` した test_sensor_sims が、ルートの event_camera.py でなく同名の
#   examples/event_camera.py(デモ)を拾い ``run_event_demo`` が無いと落ちた(ワーカーへの振り分け次第で出る)。
#   PoC はファイルから直接読み、sys.path を汚さない。
_POC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "poc_kendama.py")
_spec = importlib.util.spec_from_file_location("poc_kendama", _POC)
CD = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("poc_kendama", CD)
_spec.loader.exec_module(CD)
import kendama as KD  # noqa: E402
import kendamaworld as KW  # noqa: E402

MOSI = KD.COMBO_SEQUENCES["mosikame"]
THREE = KD.COMBO_SEQUENCES["three_cups"]


def _run(seq, n=10, rho=1.2, **kw):
    kp = KD.kendama_params(trick="ozara", rho=rho)
    return kp, KD.kendama_combo_simulate(kp, seq, n_catch=n, hand0=(0.0, 0.0, 1.1), contact=CD._contact_combo(kp), **kw)


def test_toss_apex_closed_form_vacuum():
    kp, r = _run(MOSI, n=4, rho=0.0)
    assert r["count"] == 4
    for c in r["catches"]:
        assert c["v_release"][2] > 1.0
        assert abs(c["apex"] - c["apex_closed"]) < 2e-6
        assert c["energy_drift"] < 1e-9


def test_move_pos_vel_bounds_and_reaches():
    rng = np.random.default_rng(0)
    for _ in range(200):
        p, v = rng.normal(0, 0.1, 3), rng.normal(0, 1.0, 3)
        v *= min(1.0, 2.0 / np.linalg.norm(v))
        _, v2, a = KD._move_pos_vel(p, v, rng.normal(0, 0.1, 3), rng.normal(0, 2, 3), float(rng.uniform(0, 0.3)), 1e-3, 2.5, 20.0)
        assert np.linalg.norm(v2) <= 2.5 * (1 + 1e-12)
        assert np.linalg.norm(a) <= 20.0 * (1 + 1e-9)
    # 実行可能な目標には着く: 静止から 0.3 s で 5 cm 下、下向き 1.5 m/s
    p, v = np.zeros(3), np.zeros(3)
    tgt, tv = np.array([0.0, 0.0, -0.05]), np.array([0.0, 0.0, -1.5])
    for k in range(300):
        p, v, _ = KD._move_pos_vel(p, v, tgt, tv, 0.3 - k * 1e-3, 1e-3, 2.5, 20.0)
    assert np.linalg.norm(p - tgt) < 2e-3 and np.linalg.norm(v - tv) < 0.05


def test_position_only_controller_cannot_catch_but_pos_vel_can():
    _, old = _run(MOSI, n=3, controller="position")
    _, new = _run(MOSI, n=3)
    assert old["count"] == 0 and old["end_reason"] == "too_fast"
    assert new["count"] == 3 and max(c["rel_speed"] for c in new["catches"]) < 0.5


@pytest.mark.parametrize("seq", [MOSI, THREE])
def test_truth_ten_in_a_row(seq):
    kp, r = _run(seq, n=10)
    assert r["count"] == 10 and r["end_reason"] == "done" and r["grade"] == "5級"
    tricks = [c["trick"] for c in r["catches"]]
    assert tricks == [seq[(k + 1) % len(seq)] for k in range(10)]
    assert all(c["rose_then_fell"] for c in r["catches"])
    up = np.array([c["apex"] - c["z_catch"] for c in r["catches"]])
    # 頂点 = 計画した受ける位置の 20.1〜20.2 cm 上(真空で測った)。実際に受けるのは手元が加速度の上限で少し遅れて 1.1〜1.8 cm 高い所
    assert np.all((up > 0.17) & (up < 0.21))
    assert not r["taut"].any()                                                  # 糸は張らない(皿の近くでは弛んでいる)
    assert r["max_omega"] <= 30.0 + 1e-9
    assert r["min_gap"] > -5e-4
    # 持ち替えの間(R が変わっている歩)の隙間は十分に正
    Rs = r["R"]
    rot = np.array([not np.allclose(Rs[i], Rs[i - 1]) for i in range(1, len(Rs))])
    idx = np.flatnonzero(rot) + 1
    assert idx.size > 50
    gaps = KW.kendama_clearance(kp, r["hand"][idx], r["p"][idx], R_ken=Rs[idx], grip=np.zeros(3))["gap"]
    assert gaps.min() > 0.005                                                    # 測って もしかめ 27 mm・3 皿 8.8 mm
    # 手元の上限(最後の 1 歩も)
    assert np.linalg.norm(r["hand_a"], axis=1).max() <= 20.0 * (1 + 1e-9)
    assert np.linalg.norm(r["hand_v"], axis=1).max() <= 2.5 * (1 + 1e-9)


@pytest.mark.parametrize("seq", [MOSI, THREE])
def test_image_only_ten_in_a_row(seq):
    res = CD._combo_run(seq, n_catch=10, perception="image")
    assert res["swing"]["caught"] and res["combo"] is not None
    cb = res["combo"]
    assert cb["count"] == 10 and cb["end_reason"] == "done"
    assert res["count_total"] == 11
    per = res["per"]
    assert len(per.flights) == 10 and len(per.fits) > 100                    # 飛び始めを毎回画像から決め、放物線を当てた
    assert all(c["rose_then_fell"] for c in cb["catches"])
    assert max(c["rel_speed"] for c in cb["catches"]) < 0.6


def test_backward_compat_and_grades():
    kp = KD.kendama_params(trick="chuzara")
    H = np.array([0.0, 0.0, 1.0])
    P = H + np.array([[0.05, 0.0, 0.2], [0.0, 0.03, -0.1]])
    a = KW.kendama_clearance(kp, H, P)["gap"]
    b = KW.kendama_clearance(kp, H, P, R_ken=kp["R_ken"], grip=kp["grip"])["gap"]
    c = KW.kendama_clearance(kp, H, P, R_ken=np.repeat(kp["R_ken"][None], 2, 0))["gap"]
    assert np.array_equal(a, b) and np.allclose(a, c, atol=1e-15)
    w = KW.kendama_world(kp, n=12)
    with pytest.raises(ValueError):
        KW.camera_perceiver(w, KW.kendama_rig(kp), flight_from="ball")
    assert [KD._mosikame_grade(n) for n in (3, 4, 10, 19, 20, 50, 99, 100)] == \
        ["級外", "6級", "5級", "5級", "4級", "1級", "1級", "準初段"]
    with pytest.raises(ValueError):
        KD.kendama_combo_simulate(KD.kendama_params(), ("ozara",))
    with pytest.raises(ValueError):
        KD.kendama_combo_simulate(KD.kendama_params(), MOSI, a_max=9.0)
