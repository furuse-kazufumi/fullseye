# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""偏光 op を外部の第 2 実装(pypolar / py-pol / polanalyser)と突き合わせる。

同じ仕様を別の人が書いた実装は、単一実装のテストが原理的に見つけられない物を出す。
3 本とも **optional**(入っていなければ skip)。CI には入れていないので、これは
「手元で回す差分検査」であり、結果の記録は ``docs/capabilities/polarization-imaging.md`` の
裏づけ節にある(2026-09-18 実測)。道具版 = ``tools/diff_polarization_external.py``(表を印字)。

★差が出る所は**規約の違い**として固定してある(不具合ではないと切り分け済み):
  * 回転子: fullseye は状態を +θ 回す(能動)。pypolar ``op_rotation`` / polanalyser ``rotator``
    は座標の回転(受動)で、fullseye の ``rotator(-θ)`` に等しい。
  * Jones の位相・利き手: library ごとに規約が違い(pypolar は既定と alternate の 2 つ)、
    Jones 行列そのものは 0 度以外で一致しない。fullseye の Jones を fullseye の Stokes 写像で
    Mueller にすると pypolar の Mueller 素子と 1e-15 で一致する —— 比べる場所は Mueller。
    ``[1, i]/√2`` の S3 は fullseye が −1(左)、pypolar は +1(Stokes 定義側の符号規約)。
  * 楕円率: fullseye は偏光成分 |P| で正規化(½ asin(S3/|P|))、pypolar は S0 で割る
    (½ asin(S3/S0))。完全偏光では一致し、部分偏光で違う。
  * demosaic の縁: fullseye はモザイクを鏡映、OpenCV は自前の縁処理。内側 2 画素を除いて一致。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import optics as O  # noqa: E402
import specularity as S  # noqa: E402

pm = pytest.importorskip("pypolar.mueller")
pj = pytest.importorskip("pypolar.jones")

ANGLES = np.arange(0.0, 180.0, 7.5)


@pytest.mark.parametrize("kind", ["polarizer", "quarter_wave", "half_wave"])
def test_mueller_elements_agree_with_pypolar_to_machine_precision(kind):
    fn = {"polarizer": pm.op_linear_polarizer, "quarter_wave": pm.op_quarter_wave_plate,
          "half_wave": pm.op_half_wave_plate}[kind]
    for a in ANGLES:
        assert np.allclose(O.mueller_element(kind, a), fn(np.radians(a)), atol=1e-12)


def test_mueller_retarder_agrees_with_pypolar_for_every_retardance():
    for a in ANGLES:
        for r in (30.0, 60.0, 90.0, 120.0, 180.0):
            assert np.allclose(O.mueller_element("retarder", a, r),
                               pm.op_retarder(np.radians(a), np.radians(r)), atol=1e-12)


def test_rotator_is_the_active_rotation_ie_pypolar_at_minus_theta():
    """★規約差として固定: 一致するのは −θ の方。+θ で一致し始めたら向きが変わっている。"""
    for a in ANGLES:
        assert np.allclose(O.mueller_element("rotator", a), pm.op_rotation(-np.radians(a)), atol=1e-12)
        if abs(np.sin(2.0 * np.radians(a))) > 1e-9:            # ±θ が同じ行列になる角は除く
            assert not np.allclose(O.mueller_element("rotator", a), pm.op_rotation(np.radians(a)), atol=1e-6)


_BASIS = (np.array([1.0, 0.0]), np.array([0.0, 1.0]),
          np.array([1.0, 1.0]) / np.sqrt(2.0), np.array([1.0, 1.0j]) / np.sqrt(2.0))


def _jones_to_mueller_via_fullseye(J):
    """fullseye 自身の Jones→Stokes 写像で 4 つの基底状態を通し、M を解く。"""
    s_in = np.array([O.stokes_from_jones(e) for e in _BASIS]).T
    s_out = np.array([O.stokes_from_jones(J @ e) for e in _BASIS]).T
    return s_out @ np.linalg.inv(s_in)


def test_jones_layer_reaches_the_external_mueller_matrices_through_its_own_stokes_map():
    """★Jones の位相・利き手の規約は library ごとに違う(pypolar は既定と alternate の
    2 つを持ち、fullseye はそのどちらとも 0 度以外で一致しない)。比べるなら Mueller の
    領域で: fullseye の Jones を fullseye の Stokes 写像で Mueller にし、pypolar の
    Mueller 素子と突き合わせる。これで Jones 層・Stokes 写像・Mueller 層の 3 つが
    外部の第 2 実装に対して閉じる。"""
    for kind, fn in (("polarizer", lambda t: pm.op_linear_polarizer(t)),
                     ("quarter_wave", lambda t: pm.op_quarter_wave_plate(t)),
                     ("half_wave", lambda t: pm.op_half_wave_plate(t)),
                     ("retarder", lambda t: pm.op_retarder(t, np.radians(65.0))),
                     ("rotator", lambda t: pm.op_rotation(-t))):
        for a in ANGLES:
            mine = _jones_to_mueller_via_fullseye(O.jones_element(kind, a, 65.0))
            assert np.allclose(mine, fn(np.radians(a)), atol=1e-12), (kind, a)


def test_stokes_analyze_matches_pypolar_where_the_definitions_coincide():
    rng = np.random.default_rng(1)
    for _ in range(100):
        v = rng.normal(size=3)
        s = np.array([1.0, *(v / np.linalg.norm(v))])            # 完全偏光: 楕円率の定義が一致する
        a = O.stokes_analyze(s)
        assert abs(a["dop"] - pm.degree_of_polarization(s)) < 1e-12
        assert abs(np.radians(a["ellipticity_deg"]) - pm.ellipticity_angle(s)) < 1e-12
        d = abs(np.radians(a["azimuth_deg"]) - pm.ellipse_orientation(s)) % np.pi
        assert min(d, np.pi - d) < 1e-12
    # 部分偏光では fullseye は |P| で正規化する(pypolar は S0)。一致しないのが正しい。
    s = np.array([1.0, 0.3, 0.0, 0.4])
    assert abs(np.radians(O.stokes_analyze(s)["ellipticity_deg"]) - 0.5 * np.arcsin(0.4 / 0.5)) < 1e-12
    assert abs(pm.ellipticity_angle(s) - 0.5 * np.arcsin(0.4)) < 1e-12


def test_polanalyser_agrees_on_dolp_mueller_fit_and_demosaic_interior():
    pa = pytest.importorskip("polanalyser")
    h, w = 24, 32
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    s0 = 0.6 + 0.2 * np.sin(xx / 5.0)
    dolp = 0.1 + 0.8 * xx / (w - 1)
    aolp = np.radians(180.0 * yy / (h - 1))
    frames = np.stack([0.5 * s0 * (1.0 + dolp * np.cos(2.0 * (np.radians(a) - aolp)))
                       for a in O.POLARIZATION_SWEEP_ANGLES])
    st = pa.calcStokes(frames, np.radians(O.POLARIZATION_SWEEP_ANGLES))
    assert np.allclose(S.polarization_dolp_map(frames), pa.cvtStokesToDoLP(st), atol=1e-12)
    # Mueller の最小二乗: 同じ設計で同じ答え
    gens, anas = [], []
    for a in np.arange(0.0, 180.0, 30.0):
        p = O.mueller_element("polarizer", a)
        gens += [p, O.mueller_element("quarter_wave", a + 20.0) @ p]
        anas += [p, p @ O.mueller_element("quarter_wave", a + 20.0)]
    psg = np.array([g for g in gens for _ in anas])
    psa = np.array([a for _ in gens for a in anas])
    m_true = O.mueller_element("polarizer", 10.0) @ O.mueller_element("retarder", 30.0, 70.0)
    inten = np.einsum("nj,jk,nk->n", psa[:, 0, :], m_true, psg[:, :, 0])
    assert np.allclose(O.mueller_from_intensities(inten, psg, psa), pa.calcMueller(inten, psg, psa), atol=1e-12)
    # demosaic: 内側は 16 bit の量子化(1.5e-5)の範囲で一致、縁は縁処理が違う。
    rng = np.random.default_rng(0)
    raw = rng.random((64, 80))
    mine = O.polarization_demosaic(raw)
    theirs = [x.astype(float) / 65535.0
              for x in pa.demosaicing((raw * 65535).astype(np.uint16), pa.COLOR_PolarMono)]
    for k in range(4):
        assert np.abs(mine[k][2:-2, 2:-2] - theirs[k][2:-2, 2:-2]).max() < 5e-5


def test_py_pol_agrees_on_the_mueller_elements():
    Mueller = pytest.importorskip("py_pol.mueller").Mueller
    for a in ANGLES:
        t = np.radians(a)
        assert np.allclose(O.mueller_element("polarizer", a),
                           np.asarray(Mueller().diattenuator_perfect(azimuth=t).M).reshape(4, 4), atol=1e-12)
        assert np.allclose(O.mueller_element("retarder", a, 65.0),
                           np.asarray(Mueller().retarder_linear(ret=np.radians(65.0), azimuth=t).M).reshape(4, 4),
                           atol=1e-12)
