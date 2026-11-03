"""型のつながりを閉じた 20 op の門(2026-11-03)。真値は絵の外(閉じた式・既存 op との一致)。

どれも「本物の作り手の返り」を入れて確かめる —— 受け手の形の約束が産み手と
ずれていたら、ここで落ちる(合成した形だけで試すと、そのずれを見落とす)。
"""
from __future__ import annotations

import numpy as np
import pytest

import conngraph
import curve3d
import dsp
import edges3d
import geodesic3d
import ops
import optics
import range_image
import reprconv as R

match3d = pytest.importorskip("match3d")   # sobel3d / hessian3d は torch を使う


def _grid(n=12):
    return np.mgrid[0:n, 0:n, 0:n].astype(float)


# --------------------------------------------------------------------------- gradient
def test_gradient_magnitude_is_exact_on_a_linear_ramp_for_both_producers():
    z, y, x = _grid()
    ramp = 2 * z + 3 * y - x
    want = np.sqrt(4 + 9 + 1)
    inner = (slice(2, -2),) * 3
    m1 = R.gradient_magnitude(edges3d.gradient3d(ramp, sigma=0))
    m2 = R.gradient_magnitude(match3d.sobel3d(ramp))
    assert np.allclose(m1[inner], want, atol=1e-12)
    # sobel3d は利得 32 —— 割らなければ 32 倍に出る(割り忘れの退行を捕まえる)
    assert np.allclose(m2[inner], want, rtol=1e-6)


def test_gradient_shape_mismatch_is_refused():
    with pytest.raises(ValueError):
        R.gradient_magnitude((np.ones((4, 4, 4)), np.ones((4, 4, 4))))   # gvec に成分軸が無い
    with pytest.raises(ValueError):
        R.gradient_magnitude(np.ones((3, 4, 4, 4)))                        # どちらの形でもない


def test_gradient_coherence_separates_layers_from_noise():
    z, _y, _x = _grid(16)
    layers = np.sin(0.8 * z)
    noise = np.random.default_rng(0).random((16, 16, 16))
    inner = (slice(3, -3),) * 3
    c_layers = R.gradient_coherence(edges3d.gradient3d(layers, 1.0))[inner]
    c_noise = R.gradient_coherence(edges3d.gradient3d(noise, 1.0))[inner]
    assert c_layers.mean() > 0.99
    assert c_noise.mean() < 0.5
    assert 0.0 <= c_noise.min() and c_layers.max() <= 1.0
    # 比なので勾配の大きさに依らない
    c_scaled = R.gradient_coherence(edges3d.gradient3d(1000.0 * noise, 1.0))[inner]
    assert np.allclose(c_scaled, c_noise, atol=1e-9)
    # 勾配ゼロの体積は 0(分母 eps)
    assert np.all(R.gradient_coherence(edges3d.gradient3d(np.zeros((8, 8, 8)), 1.0)) == 0.0)


# --------------------------------------------------------------------------- hessian
def test_hessian_determinant_equals_det_of_the_quadratic_form():
    z, y, x = _grid()
    A = np.array([[2.0, 0.5, 0.1], [0.5, -1.0, 0.3], [0.1, 0.3, 1.5]])
    P = np.stack([z, y, x], -1)
    q = 0.5 * np.einsum("...i,ij,...j->...", P, A, P)
    det = R.hessian_determinant(match3d.hessian3d(q))
    inner = (slice(3, -3),) * 3
    # hessian3d は float32 なので相対 1e-4
    assert np.allclose(det[inner], np.linalg.det(A), rtol=1e-4)


def test_hessian_vesselness_prefers_tubes_over_blobs_and_respects_polarity():
    z, y, x = _grid(13)
    tube = np.exp(-((y - 6) ** 2 + (x - 6) ** 2) / 4.0)
    blob = np.exp(-((z - 6) ** 2 + (y - 6) ** 2 + (x - 6) ** 2) / 4.0)
    vt = R.hessian_vesselness(match3d.hessian3d(tube))
    vb = R.hessian_vesselness(match3d.hessian3d(blob))
    assert vt[6, 6, 6] > 0.5
    assert vb[6, 6, 6] < 0.2
    # 明るい管を暗い管として探すと中心は 0
    assert R.hessian_vesselness(match3d.hessian3d(tube), black_ridges=True)[6, 6, 6] == 0.0
    # 反転した体積の暗い管は、元の明るい管と同じ応答
    assert np.allclose(R.hessian_vesselness(match3d.hessian3d(-tube), black_ridges=True), vt, atol=1e-6)
    assert np.all(R.hessian_vesselness(match3d.hessian3d(np.zeros((6, 6, 6)))) == 0.0)


def test_hessian_wrong_form_is_refused():
    with pytest.raises(ValueError):
        R.hessian_determinant([np.zeros((4, 4, 4))] * 5)
    with pytest.raises(ValueError):
        R.hessian_vesselness([np.zeros((4, 4, 4))] * 6, alpha=0.0)


# --------------------------------------------------------------------------- frame
def test_frame_axis_tangent_of_a_helix_matches_the_closed_form():
    t = np.linspace(0, 4 * np.pi, 400)
    a, c = 1.0, 0.3
    helix = np.stack([a * np.cos(t), a * np.sin(t), c * t], 1)
    T = R.frame_axis(curve3d.frenet_frame(helix), "tangent")
    want = np.stack([-a * np.sin(t), a * np.cos(t), np.full_like(t, c)], 1) / np.hypot(a, c)
    assert np.allclose(T[2:-2], want[2:-2], atol=1e-3)
    B = R.frame_axis(curve3d.frenet_frame(helix), "binormal")
    assert np.allclose(B[2:-2, 2], a / np.hypot(a, c), atol=1e-3)   # 陪法線の z 成分は一定


def test_frame_axis_refuses_the_undefined_normal_of_a_straight_line():
    line = np.stack([np.linspace(0, 1, 50), np.zeros(50), np.zeros(50)], 1)
    fr = curve3d.frenet_frame(line)
    assert R.frame_axis(fr, "tangent").shape == (50, 3)
    with pytest.raises(ValueError, match="undefined"):
        R.frame_axis(fr, "normal")
    with pytest.raises(ValueError):
        R.frame_axis(fr, "sideways")


# --------------------------------------------------------------------------- graph
def test_knn_graph_reaches_the_conn_graph_family():
    rng = np.random.default_rng(1)
    pts = np.concatenate([rng.random((40, 3)), rng.random((40, 3)) + 10.0])
    g = geodesic3d.knn_graph(pts, 5)
    W = R.knn_graph_to_conn_graph(g)
    assert W.shape == (80, 80) and np.allclose(W, W.T) and np.all(np.diag(W) == 0)
    lab = conngraph.graph_components(W)
    assert len(np.unique(lab)) == 2 and len(np.unique(lab[:40])) == 1
    idx, dist = g
    assert np.isclose(W[0, idx[0, 0]], 1.0 / dist[0, 0])
    Wd = R.knn_graph_to_conn_graph(g, weight="distance", symmetric=False)
    assert np.isclose(Wd[3, idx[3, 1]], dist[3, 1]) and np.count_nonzero(Wd) == idx.size


def test_knn_graph_bad_input_is_refused():
    pts = np.random.default_rng(2).random((10, 3))
    idx, dist = geodesic3d.knn_graph(pts, 3)
    with pytest.raises(ValueError):
        R.knn_graph_to_conn_graph((idx + 100, dist))
    with pytest.raises(ValueError):
        R.knn_graph_to_conn_graph((idx, np.zeros_like(dist)))          # 距離 0 は逆数にできない
    with pytest.raises(ValueError):
        R.knn_graph_to_conn_graph((idx, dist), weight="cosine")


# --------------------------------------------------------------------------- pointmap
def test_pointmap_to_points_equals_depth_to_points():
    rng = np.random.default_rng(3)
    depth = 1.0 + rng.random((9, 11))
    depth[2, 3] = 0.0                       # 無効深度
    K = dict(fx=120.0, fy=110.0, cx=5.0, cy=4.0)
    pm = range_image.depth_to_organized_points(depth, **K)
    got = R.pointmap_to_points(pm, drop_nonpositive_z=True)
    want = match3d.depth_to_points(depth, **K)
    assert got.shape == want.shape == (98, 3)
    assert np.allclose(got, want, atol=1e-12)
    pm2 = pm.copy()
    pm2[0, 0] = np.nan
    assert R.pointmap_to_points(pm2).shape == (98, 3)   # NaN の 1 行だけ落ちる(z=0 の行は残る)
    with pytest.raises(ValueError):
        R.pointmap_to_points(np.full((2, 2, 3), np.nan))


# --------------------------------------------------------------------------- match
def test_match_component_reads_area_center():
    reg = np.zeros((20, 20))
    reg[5:9, 2:12] = 1.0
    ac = ops.RT["area_center"](reg, 0.5, 0.5)
    assert R.match_component(ac, 0) == 40.0
    assert R.match_component(ac, 1) == pytest.approx(6.5)
    assert R.match_component(ac, 2) == pytest.approx(6.5)
    with pytest.raises(ValueError):
        R.match_component(ac, 3)
    with pytest.raises(ValueError):
        R.match_component(ac, -1)


# --------------------------------------------------------------------------- positions
def test_indices_to_positions_feeds_point_spectrum_with_the_true_period():
    period_idx, dx = 25, 0.004               # 25 標本ごとの事象、1 標本 = 4 mm
    sig = np.zeros(2000)
    sig[::period_idx] = 1.0
    peaks = dsp.find_peaks(sig)
    pos = R.indices_to_positions(peaks, spacing=dx)
    assert np.allclose(np.diff(pos), period_idx * dx)
    sp = dsp.point_spectrum(pos, f_max=15.0)   # 完全な周期列は高調波 20, 30 も同じ強さなので基本波の手前で切る
    f = np.asarray(sp["freq"])
    p = np.asarray(sp["power"])
    f_peak = f[np.argmax(p * (f > 1.0))]
    assert f_peak == pytest.approx(1.0 / (period_idx * dx), rel=0.02)
    with pytest.raises(ValueError):
        R.indices_to_positions([1.5, 2.0])
    with pytest.raises(ValueError):
        R.indices_to_positions([1, 2], spacing=0.0)


# --------------------------------------------------------------------------- synapse_table
def test_synapse_table_from_a_csv_table_builds_the_same_graph():
    tab = {"pre": np.array([0, 1, 2, 0]), "post": np.array([1, 2, 0, 1]),
           "n": np.array([3, 1, 2, 4])}
    st = R.synapse_table_from_table(tab, count="n")
    W = conngraph.graph_from_synapses(st)
    assert W[0, 1] == 7 and W[1, 2] == 1 and W[2, 0] == 2
    assert np.array_equal(R.synapse_table_from_table(tab)[:, 2], np.ones(4))
    # table_read_csv の形({"columns": ..., "units": ..., "meta": ...})も同じ表になる
    import fileio
    csv_text = ("pre,post,n\n# units:,id,id,count\n# source: test\n# generated_at: 2026-11-03\n"
                "# coordinate_meaning: neuron ids\n0,1,3\n1,2,1\n2,0,2\n0,1,4\n")
    assert np.array_equal(R.synapse_table_from_table(fileio.table_read_csv(csv_text), count="n"), st)
    with pytest.raises(ValueError):
        R.synapse_table_from_table({"pre": [0.5], "post": [1]})          # 座標を id として読まない
    with pytest.raises(ValueError):
        R.synapse_table_from_table({"pre": [0], "post": [1]}, count="n")


# --------------------------------------------------------------------------- jones
@pytest.mark.parametrize("psi,chi", [(0.0, 0.0), (30.0, 0.0), (0.0, 45.0), (10.0, -15.0), (-60.0, 20.0)])
def test_jones_state_round_trips_through_stokes(psi, chi):
    s = optics.stokes_from_jones(R.jones_state(psi, chi))
    want = [1.0, np.cos(np.radians(2 * chi)) * np.cos(np.radians(2 * psi)),
            np.cos(np.radians(2 * chi)) * np.sin(np.radians(2 * psi)), np.sin(np.radians(2 * chi))]
    assert np.allclose(s, want, atol=1e-12)
    a = optics.stokes_analyze(s)
    assert a["ellipticity_deg"] == pytest.approx(chi, abs=1e-9)
    if abs(chi) < 45.0:
        d = (a["azimuth_deg"] - psi) % 180.0          # 方位角は 180 度で同じ楕円
        assert min(d, 180.0 - d) == pytest.approx(0.0, abs=1e-9)


def test_jones_state_circular_is_the_documented_vector_and_malus_holds():
    assert np.allclose(R.jones_state(0.0, 45.0), np.array([1.0, -1.0j]) / np.sqrt(2))
    pol = optics.jones_element("polarizer", angle_deg=60.0)
    out = optics.jones_apply(pol, R.jones_state(0.0, 0.0))
    assert np.sum(np.abs(out) ** 2) == pytest.approx(np.cos(np.radians(60.0)) ** 2, abs=1e-12)
    with pytest.raises(ValueError):
        R.jones_state(0.0, 50.0)


# --------------------------------------------------------------------------- tokens
def test_tokens_to_matrix_is_a_bit_exact_copy():
    t = np.random.default_rng(4).standard_normal((7, 5))
    m = R.tokens_to_matrix(t)
    assert np.array_equal(m, t) and m is not t
    with pytest.raises(ValueError):
        R.tokens_to_matrix(np.ones(5))


# --------------------------------------------------------------------------- 落とした鎖(レシピの網羅、W2)
def test_vx_sobel_table_reaches_vx_magnitude():
    import vxcore
    img = (np.tile(np.arange(12.0), (10, 1)) * 10).astype(np.uint8)
    t = vxcore.vx_sobel3x3(img, border="replicate")
    gx, gy = R.table_field_image2d(t, "gx"), R.table_field_image2d(t, "gy")
    assert gx.dtype == np.int16 and np.array_equal(gx, t["gx"])
    mag = vxcore.vx_magnitude(gx, gy)
    assert np.asarray(mag).shape == img.shape
    with pytest.raises(ValueError, match="no field"):
        R.table_field_image2d(t, "gz")
    with pytest.raises(ValueError):
        R.table_field_signal(t, "gx")                 # 2-D の欄を 1-D として通さない


def test_table_fields_read_csv_tables_and_scalars():
    import fileio
    csv_text = ("t,v\n# units:,s,V\n# source: test\n# generated_at: 2026-11-03\n"
                "# coordinate_meaning: time\n0,1\n1,3\n2,5\n")
    tab = fileio.table_read_csv(csv_text)
    assert np.array_equal(R.table_field_signal(tab, "v"), [1.0, 3.0, 5.0])
    assert R.table_field_measurement({"width": np.array([4.5])}, "width") == 4.5
    with pytest.raises(ValueError):
        R.table_field_measurement({"width": np.array([1.0, 2.0])}, "width")
    m = R.table_field_matrix({"swt": np.zeros((3, 4))}, "swt")
    assert m.shape == (3, 4) and m.dtype == np.float64


def test_pairs_peak_x_reads_the_spectrum_peak():
    x = np.arange(1000) / 1000.0
    for f0 in (123.0, 123.5, 200.25):
        freqs, mag = dsp.spectrum(np.sin(2 * np.pi * f0 * x), 1000.0)
        assert R.pairs_peak_x((freqs, mag), x_min=1.0) == pytest.approx(f0, abs=0.26)
    freqs, mag = dsp.spectrum(1.0 + 0.1 * np.sin(2 * np.pi * 50.0 * x), 1000.0)
    assert R.pairs_peak_x((freqs, mag)) == 0.0                     # DC が最大(docstring の注意)
    assert R.pairs_peak_x((freqs, mag), x_min=1.0) == pytest.approx(50.0, abs=1e-6)
    with pytest.raises(ValueError):
        R.pairs_peak_x((freqs, mag), x_min=1e6)


def test_keypoint_swaps_fix_the_mirrored_pnp_pose():
    rng = np.random.default_rng(5)
    P = rng.uniform(-0.5, 0.5, (12, 3))
    K = np.array([[800.0, 0, 320], [0, 800.0, 240], [0, 0, 1]])
    t_true = np.array([0.1, -0.05, 3.0])
    uv = (K @ (P + t_true).T).T
    uv = uv[:, :2] / uv[:, 2:]
    rowcol = uv[:, ::-1]
    assert np.array_equal(R.keypoints_rowcol_to_uv(rowcol), uv)
    assert np.array_equal(R.keypoints_uv_to_rowcol(R.keypoints_rowcol_to_uv(rowcol)), rowcol)
    import pnp3d
    Rm, t = pnp3d.dlt_pose(P, R.keypoints_rowcol_to_uv(rowcol), K)
    assert np.allclose(t, t_true, atol=1e-6)


def test_pose_to_matrix_packs_r_and_t_and_refuses_non_rotations():
    th = np.radians(30.0)
    Rz = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
    M = R.pose_to_matrix((Rz, [1.0, 2.0, 3.0]))
    assert np.array_equal(M[:3, :3], Rz) and np.array_equal(M[:3, 3], [1, 2, 3])
    assert np.array_equal(M[3], [0, 0, 0, 1])
    assert np.array_equal(R.pose_to_matrix(M), M)
    assert np.array_equal(R.pose_to_matrix({"R": Rz, "t": [1, 2, 3]}), M)
    with pytest.raises(ValueError):
        R.pose_to_matrix((2.0 * Rz, [0, 0, 0]))             # 相似変換は剛体ではない
    with pytest.raises(ValueError):
        R.pose_to_matrix((np.diag([1.0, 1.0, -1.0]), [0, 0, 0]))   # 鏡映


def test_indices_to_positions_refuses_an_empty_list_by_name():
    with pytest.raises(ValueError, match="indices: empty"):
        R.indices_to_positions([], spacing=0.5)
