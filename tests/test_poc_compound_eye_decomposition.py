# -*- coding: utf-8 -*-
"""複眼 PoC 第 2 章の対照実験(誤差の分解)の回帰テスト(2026-10-11)。

``examples/poc_compound_eye.py`` の SNR 利得は N=49 で 5.33 と √49=7.00 を大きく下回る。
対照実験 :func:`superposition_decomposition` はこれを「床(ノイズ無しの重ね-真)」と
「雑音項(ノイズだけを重ねたもの)」に分け、

* 雑音項の利得は N=49 まで √N に従う(実測 7.05)
* 周縁 8 画素を除けば全体の利得も N=49 で 7.19
* 床はスロープ 1.0 × 半径 4 = 最大シフトの外周 4 画素にだけある(内側は 1e-15 の丸め屑)

を示す。論文(ViEW2026)が引く数字なので、ここで固定する。分解を壊したら
(周縁を除かない・雑音項に信号を混ぜる・床の幅を数え違える)必ず落ちるよう、
帯は実測値のまわりに狭く取る。
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
POC = ROOT / "examples" / "poc_compound_eye.py"


@pytest.fixture(scope="module")
def decomp():
    spec = importlib.util.spec_from_file_location("_poc_compound_eye_for_test", POC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.superposition_decomposition()


def _row(decomp, n):
    return next(r for r in decomp["rows"] if r[1] == n)


def test_noise_only_gain_follows_sqrt_n_up_to_49(decomp):
    for _r, n, _tot, g_noise, sq, _in in decomp["rows"]:
        assert abs(g_noise - sq) < 0.08, (n, g_noise, sq)
    _r, n, _tot, g_noise, sq, _in = _row(decomp, 49)
    assert sq == pytest.approx(7.0)
    assert g_noise == pytest.approx(7.05, abs=0.03)        # 実測 7.05


def test_total_gain_saturates_but_border_excluded_gain_does_not(decomp):
    _r, _n, g_tot, _noise, sq, g_in = _row(decomp, 49)
    assert decomp["border"] == 8
    assert g_tot == pytest.approx(5.33, abs=0.03)          # 第 2 章の飽和(実測 5.33)
    assert g_in == pytest.approx(7.19, abs=0.03)           # 周縁 8px 除外(実測 7.19)
    assert g_in > 0.95 * sq > g_tot


def test_noiseless_floor_lives_only_in_outer_4_px(decomp):
    assert decomp["floor_extent"] == 4
    floor = {k: (rms, mx) for k, rms, mx in decomp["floor"]}
    assert floor[3][1] > 1e-3                              # 3px 除外ではまだ床がある
    for k in (4, 5, 8):                                    # 4px 以上除けば丸め屑だけ
        assert floor[k][1] < 1e-12, (k, floor[k])
    assert floor[0][0] > 0.01                              # 全画素の床 RMS(実測 1.09e-2)
    assert math.isclose(floor[0][0], 1.09e-2, rel_tol=0.02)
