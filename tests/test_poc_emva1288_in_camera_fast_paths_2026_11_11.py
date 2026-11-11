"""``examples/poc_emva1288_in_camera_processing.py`` の「その場で重ねる」計算が、素直な式と 1 ビットも違わないこと。

2026-11-11、この PoC の CPU 時間の門(60 秒)が共有ランナーで 63.0 秒になって落ちた。門は動かさず、
一時配列を作らない書き方に直して計算を軽くした。軽くした書き方が値を変えていないことを、ここで固定する
(乱数の列・丸め・切り取りのどれかがずれると、PoC の 27 件の検査(うち 1 件が CPU 時間の門)の数字が黙って変わる)。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

POC = Path(__file__).resolve().parents[1] / "examples" / "poc_emva1288_in_camera_processing.py"


@pytest.fixture(scope="module")
def poc():
    spec = importlib.util.spec_from_file_location("poc_emva1288_in_camera_processing_under_test", POC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _naive_raw(m, sensor, rng, mu_p):
    e = rng.poisson(m.ETA * mu_p * sensor["prnu"])
    return np.clip(np.round(m.K * (e + rng.normal(0.0, m.SD, (m.H, m.W))) + m.OFF + sensor["dsnu"]), 0, m.MAXDN)


def _naive_box3(y):
    r = y + np.roll(y, 1, 0) + np.roll(y, -1, 0)
    return (r + np.roll(r, 1, 1) + np.roll(r, -1, 1)) / 9.0


@pytest.mark.parametrize("mu_p", [0.0, 3.0, 400.0, 9000.0, 40000.0])
def test_raw_matches_the_plain_formula_bit_for_bit(poc, mu_p):
    sensor = poc.make_sensor()
    cam = poc.Camera("raw", "", sensor, np.random.default_rng(7))
    ref_rng = np.random.default_rng(7)
    for _ in range(3):                      # 続けて呼んでも乱数の列がずれない
        got = cam.raw(mu_p)
        want = _naive_raw(poc, sensor, ref_rng, mu_p)
        assert got.dtype == want.dtype
        assert np.array_equal(got, want)
    if mu_p >= 40000.0:
        assert (got == poc.MAXDN).any()     # 上の切り取りが実際に働く露光を含めている
    if mu_p == 0.0:
        assert got.min() >= 0.0 and got.std() > 0.0


def test_raw_does_not_touch_the_sensor_maps(poc):
    sensor = poc.make_sensor()
    before = {k: np.array(v, copy=True) for k, v in sensor.items()}
    cam = poc.Camera("tnr", "", sensor, np.random.default_rng(3), temporal=poc.ALPHA)
    cam.frames(5000.0, 2)
    for k, v in before.items():
        assert np.array_equal(sensor[k], v), k


def test_temporal_filter_matches_the_plain_recursion(poc):
    sensor = poc.make_sensor()
    a = poc.ALPHA
    cam = poc.Camera("tnr", "", sensor, np.random.default_rng(11), temporal=a)
    got = cam.frames(6000.0, 3, burn=4)
    rng = np.random.default_rng(11)
    st = _naive_raw(poc, sensor, rng, 6000.0)
    for _ in range(4):
        st = a * _naive_raw(poc, sensor, rng, 6000.0) + (1 - a) * st
    want = []
    for _ in range(3):
        st = a * _naive_raw(poc, sensor, rng, 6000.0) + (1 - a) * st
        want.append(np.clip(np.round(st), 0, poc.MAXDN))
    assert len(got) == 3
    for g, w in zip(got, want):
        assert np.array_equal(g, w)
    assert not np.array_equal(got[0], got[1])   # 返した 3 枚が同じ配列の使い回しになっていない


@pytest.mark.parametrize("a,b", [(0.7, 0.3), (1.5, -0.5)])
def test_blend_with_box_matches_the_plain_formula_and_keeps_its_input(poc, a, b):
    rng = np.random.default_rng(5)
    y = np.round(rng.uniform(-50.0, poc.MAXDN + 50.0, (poc.H, poc.W)))
    y[:8, :8] = -50.0                       # 平らな区画: 平均を混ぜても範囲の外に残る
    y[8:16, :8] = poc.MAXDN + 50.0
    keep = y.copy()
    got = poc.blend_with_box(a, b)(y)
    want = np.clip(np.round(a * y + b * _naive_box3(y)), 0, poc.MAXDN)
    assert np.array_equal(got, want)
    assert np.array_equal(poc.box3_wrap(y), _naive_box3(y))
    assert np.array_equal(y, keep)
    assert got.min() == 0.0 and got.max() == poc.MAXDN   # 両側の切り取りが働く入力になっている


def test_round_clip_dn_and_clip_dn(poc):
    rng = np.random.default_rng(9)
    x = rng.uniform(-10.0, 1100.0, (64, 80))
    x[0, :4] = [0.5, 1.5, 2.5, -0.5]                       # 偶数丸めの境目
    keep = x.copy()
    q = poc.round_clip_dn(x, 1023)
    assert np.array_equal(q, np.clip(np.round(x), 0, 1023))
    assert np.array_equal(x, keep)                          # round_clip_dn は入力を書き換えない
    z = x.copy()
    out = poc.clip_dn(z, 1023)
    assert out is z                                         # clip_dn はその場で書き換える
    assert np.array_equal(z, np.clip(keep, 0, 1023))
    assert not np.signbit(poc.clip_dn(np.array([-0.0, -3.0]))).any()   # -0.0 は +0.0 になる(np.clip は -0.0 を残す)


def test_gain2_clip_matches_the_plain_formula_and_keeps_its_input(poc):
    rng = np.random.default_rng(13)
    y = np.round(rng.uniform(0.0, poc.MAXDN, (poc.H, poc.W)))
    y[:4, :4] = poc.MAXDN                                   # 2 倍で必ず上限を超える画素
    y[4:8, :4] = 100.0                                      # 2 倍しても切り取られない画素
    keep = y.copy()
    got = poc.gain2_clip(y)
    assert np.array_equal(got, np.clip(2.0 * keep, 0, poc.MAXDN))
    assert np.array_equal(y, keep)                          # 入力(raw の出力)を書き換えない
    assert got is not y
    assert got.max() == poc.MAXDN and (got[:4, :4] == poc.MAXDN).all()   # 上限の切り取りが働く
    assert (got[4:8, :4] == 200.0).all()                    # ゲインが 2 倍である


def test_the_gain2_camera_uses_gain2_clip(poc):
    # main() が組む gain2 のカメラが、テストした関数をそのまま使っていること(lambda に戻ると上のテストが空になる)
    src = Path(poc.__file__).read_text(encoding="utf-8")
    assert src.count("proc=gain2_clip, kernel=W_GAIN") == 1
    assert "lambda y: clip_dn" not in src
