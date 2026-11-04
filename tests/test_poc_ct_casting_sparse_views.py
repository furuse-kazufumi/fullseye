"""poc_ct_casting_sparse_views の門を小さな格子で回す(PoC 全体は test_poc_scripts_run が走らせる)。

ここで見るのは、PoC が頼る**真値の側**が本当に真値であること —— 閉形式の体積・閉形式の投影と
離散の投影の一致・随伴性 —— と、空隙の計測が真値の体積でそのまま正しい答えを返すこと。
再構成の順位そのものは PoC 本体の門(full / reduced)が見る。
"""
import math

import numpy as np

from examples import poc_ct_casting_sparse_views as P


def test_drawn_void_volume_matches_the_closed_form():
    solid = P.LG.ellipsoid_phantom(P.N, (P.CAST,), supersample=4)
    for row in P.VOIDS_TEST:
        one = P.LG.ellipsoid_phantom(P.N, (P.CAST, row), supersample=4)
        v = float(np.sum(solid - one)) * P.VOX ** 3
        assert abs(v / P.void_volume_mm3(row) - 1) < 0.02


def test_closed_form_volume_is_four_thirds_pi_abc():
    row = (0.0, 0.0, 0.0, 0.5, 0.25, 0.125, 0.0, -1.0)
    h = P.half_mm()
    assert math.isclose(P.void_volume_mm3(row), 4 / 3 * math.pi * 0.5 * 0.25 * 0.125 * h ** 3)


def test_discrete_projection_converges_to_the_closed_form():
    table = (P.CAST,) + P.VOIDS_TEST
    coarse = P.projector_gap(table, 16, views=4)[0]
    fine = P.projector_gap(table, 32, views=4)[0]
    assert np.isfinite(coarse) and coarse > 0
    assert fine < 0.75 * coarse


def test_projector_pair_is_adjoint_and_the_gate_has_teeth():
    g = P.LG.ct_scan_geometry("cone", n_views=6, n_u=20, n_v=20, vol_shape=16, voxel=P.VOX)
    gap, lhs, _ = P.adjoint_gap(g)
    assert abs(lhs) > 0 and gap < 1e-6
    g_off = P.LG.ct_scan_geometry("cone", n_views=6, n_u=20, n_v=20, vol_shape=16, voxel=P.VOX,
                                  offset_u=0.5)
    assert P.adjoint_gap(g, g_t=g_off)[0] > 1e-3


def test_void_measurement_on_the_truth_finds_every_void():
    truth = P.LG.ellipsoid_phantom(P.N, (P.CAST,) + P.VOIDS_TEST, supersample=2)
    s = P.summarize(truth, truth, P.VOIDS_TEST)
    assert s["missed"] == 0 and s["false"] == 0 and s["rms_err"] == 0.0
    assert s["vol_err"] < 0.35
    assert s["cen_err"] < P.VOX


def test_void_measurement_counts_a_blank_volume_as_all_missed():
    truth = P.LG.ellipsoid_phantom(P.N, (P.CAST,), supersample=1)
    s = P.summarize(truth, truth, P.VOIDS_TEST)
    assert s["missed"] == len(P.VOIDS_TEST) and s["vol_err"] == 1.0
