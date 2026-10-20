"""Performance batch 20: exact-result gates against the pre-change paths."""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix, diags

import motion


def _components_original(vertices, faces):
    from collections import defaultdict
    parent = np.arange(len(vertices))
    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != x:
            nxt = parent[x]; parent[x] = root; x = nxt
        return root
    for a, b, c in faces:
        ra, rb, rc = find(int(a)), find(int(b)), find(int(c))
        parent[rb] = ra; parent[rc] = ra
    groups = defaultdict(list)
    for fi, face in enumerate(faces):
        groups[find(int(face[0]))].append(fi)
    out = []
    for flist in groups.values():
        selected = faces[flist]; used = np.unique(selected)
        remap = -np.ones(len(vertices), np.int64); remap[used] = np.arange(used.size)
        out.append((int(used.min()), np.ascontiguousarray(vertices[used], np.float64),
                    np.ascontiguousarray(remap[selected], np.int64)))
    out.sort(key=lambda row: row[0])
    return [(v, f) for _, v, f in out]


def _laplacian_step_original(points, edges, factor):
    summed = np.zeros_like(points); degree = np.zeros(len(points))
    i, j = edges[:, 0], edges[:, 1]
    np.add.at(summed, i, points[j]); np.add.at(summed, j, points[i])
    np.add.at(degree, i, 1.0); np.add.at(degree, j, 1.0)
    mask = degree > 0; out = points.copy()
    out[mask] = points[mask] + factor * (summed[mask] / degree[mask, None] - points[mask])
    return out


def _smooth_taubin_original(vertices, faces, iterations=10, lamb=.5, mu=-.53):
    import meshrepair
    edges = meshrepair._unique_edges(faces); out = vertices.copy()
    for _ in range(iterations):
        out = _laplacian_step_original(out, edges, lamb)
        out = _laplacian_step_original(out, edges, mu)
    return np.ascontiguousarray(out, np.float64)


def _umbrella_original(faces, n):
    a, b, c = faces[:, 0], faces[:, 1], faces[:, 2]
    rows = np.concatenate([a, b, b, c, c, a]); cols = np.concatenate([b, a, c, b, a, c])
    adjacency = coo_matrix((np.ones(rows.size), (rows, cols)), shape=(n, n)).tocsr()
    adjacency.data[:] = 1.0
    degree = np.asarray(adjacency.sum(axis=1)).ravel(); inv = np.zeros(n)
    mask = degree > 0; inv[mask] = 1.0 / degree[mask]
    return (diags(inv) @ adjacency).tocsr(), mask


def _homography_dlt_original(src, dst):
    rows = []
    for (x, y), (u, v) in zip(np.asarray(src, float), np.asarray(dst, float)):
        rows.extend(([-x, -y, -1, 0, 0, 0, u*x, u*y, u],
                     [0, 0, 0, -x, -y, -1, v*x, v*y, v]))
    _, _, vt = np.linalg.svd(np.asarray(rows))
    h = vt[-1].reshape(3, 3)
    return h / h[2, 2]


def _world_plane_original(cam_par, pose, image_points, scale=1.0):
    import calib
    k = calib._K(cam_par); pose = np.asarray(pose, float)
    rotation, translation = pose[:3, :3], pose[:3, 3]
    inverse = np.linalg.inv(k); out = []
    for row, col in np.asarray(image_points, float).reshape(-1, 2):
        direction = rotation.T @ (inverse @ np.array([col, row, 1.0]))
        origin = -rotation.T @ translation
        point = origin + (-origin[2] / direction[2]) * direction
        out.append(point[:2] * scale)
    return np.asarray(out)


def test_106_110_mesh_paths_match_reference_results():
    import meshrepair
    import mesh_smooth
    v = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.],
                  [4., 0., 0.], [5., 0., 0.], [4., 1., 0.]])
    f = np.array([[0, 1, 2], [3, 4, 5]])
    parts = meshrepair.components(v, f)
    assert len(parts) == 2
    np.testing.assert_array_equal(parts[0][1], [[0, 1, 2]])
    w, has = mesh_smooth._umbrella_operator(f, len(v))
    block = np.array([[0, .5, .5], [.5, 0, .5], [.5, .5, 0]])
    expected = np.zeros((6, 6))
    expected[:3, :3] = expected[3:, 3:] = block
    np.testing.assert_array_equal(w.toarray(), expected)
    assert has.all()


def test_106_108_110_match_original_implementations():
    import meshrepair
    import mesh_smooth
    rng = np.random.default_rng(106)
    rows, cols = np.mgrid[:18, :20]
    vertices = np.column_stack((cols.ravel(), rows.ravel(), rng.normal(size=rows.size)))
    faces = []
    for row in range(17):
        for col in range(19):
            a = row * 20 + col
            faces.extend(((a, a + 1, a + 20), (a + 1, a + 21, a + 20)))
    faces = np.asarray(faces, np.int64)
    expected_parts = _components_original(vertices, faces)
    actual_parts = meshrepair.components(vertices, faces)
    assert len(actual_parts) == len(expected_parts)
    for actual, expected in zip(actual_parts, expected_parts):
        np.testing.assert_array_equal(actual[0], expected[0])
        np.testing.assert_array_equal(actual[1], expected[1])
    np.testing.assert_array_equal(meshrepair.smooth_taubin(vertices, faces, 3),
                                  _smooth_taubin_original(vertices, faces, 3))
    actual_w, actual_mask = mesh_smooth._umbrella_operator(faces, len(vertices))
    expected_w, expected_mask = _umbrella_original(faces, len(vertices))
    np.testing.assert_array_equal(actual_w.toarray(), expected_w.toarray())
    np.testing.assert_array_equal(actual_mask, expected_mask)


def test_116_curve_shortcuts_match_original_full_derivatives():
    import curve3d
    t = np.linspace(0, 20, 1000)
    curve = np.column_stack((np.cos(t), np.sin(t), .03 * t))
    r1, r2, r3 = curve3d._d(curve)
    tangent = r1 / (np.linalg.norm(r1, axis=1, keepdims=True) + 1e-12)
    normal_part = r2 - np.sum(r2 * tangent, axis=1, keepdims=True) * tangent
    normal = normal_part / (np.linalg.norm(normal_part, axis=1, keepdims=True) + 1e-12)
    for actual, expected in zip(curve3d.frenet_frame(curve),
                                (tangent, normal, np.cross(tangent, normal))):
        np.testing.assert_array_equal(actual, expected)
    cross_norm = np.linalg.norm(np.cross(r1, r2), axis=1)
    speed = np.linalg.norm(r1, axis=1); length = float(np.median(speed))
    curvature = cross_norm / (speed ** 3 + 1e-12 * length ** 3)
    cumulative, _ = curve3d.arc_length(curve)
    expected_total = float(np.sum(curvature * np.gradient(cumulative)))
    assert curve3d.total_curvature(curve) == expected_total


def test_142_143_calibration_matches_original_implementations():
    import calib
    rng = np.random.default_rng(142)
    src = rng.normal(size=(30, 2)); transform = np.array([[1.2, .1, 3], [-.2, .9, 4], [.01, -.02, 1]])
    hom = np.column_stack((src, np.ones(len(src)))) @ transform.T
    dst = hom[:, :2] / hom[:, 2, None]
    np.testing.assert_array_equal(calib._homography_dlt(src, dst),
                                  _homography_dlt_original(src, dst))
    camera = {"fx": 800., "fy": 810., "cx": 320., "cy": 240.}
    pose = np.eye(4); pose[:3, 3] = (1, 2, 10)
    points = rng.uniform((0, 0), (480, 640), size=(200, 2))
    np.testing.assert_allclose(calib.image_points_to_world_plane(camera, pose, points),
                               _world_plane_original(camera, pose, points), atol=1e-12, rtol=0)


def test_109_112_115_117_118_selectable_paths_keep_contracts():
    import curvature3d
    import curve3d
    import meshrepair
    rng = np.random.default_rng(112)
    points = rng.normal(size=(90, 3))
    combined = curvature3d.curvature_descriptors(points, 14, include_normals=True)
    k1, k2, normals = curvature3d._curvatures(points, 14)
    np.testing.assert_array_equal(combined["k1"], k1)
    np.testing.assert_array_equal(combined["k2"], k2)
    np.testing.assert_array_equal(combined["normals"], normals)
    curve = rng.normal(size=(500, 3)).cumsum(axis=0)
    np.testing.assert_allclose(curve3d.resample_uniform(curve, 800, method="fast"),
                               curve3d.resample_uniform(curve, 800), atol=1e-12, rtol=0)
    rows, cols = np.mgrid[:10, :12]
    vertices = np.column_stack((cols.ravel(), rows.ravel(), rng.normal(size=rows.size)))
    faces = []
    for row in range(9):
        for col in range(11):
            a = row * 12 + col
            faces.extend(((a, a + 1, a + 12), (a + 1, a + 13, a + 12)))
    faces = np.asarray(faces)
    np.testing.assert_allclose(meshrepair.smooth_taubin(vertices, faces, 4, method="csr"),
                               meshrepair.smooth_taubin(vertices, faces, 4), atol=1e-12, rtol=0)


def test_127_fast_reconstruction_and_137_preallocation_match_exact(tmp_path):
    import motionmag
    import video
    rng = np.random.default_rng(127)
    clip = rng.normal(size=(12, 16, 18))
    exact = motionmag.motion_magnify(clip, 1.0, 1.0, 3.0, 12.0, scales=1, orientations=2)
    fast = motionmag.motion_magnify(clip, 1.0, 1.0, 3.0, 12.0, scales=1,
                                    orientations=2, method="fast")
    np.testing.assert_allclose(fast["video"], exact["video"], atol=1e-12, rtol=0)
    path = tmp_path / "frames.gif"
    frames = rng.random((8, 12, 14))
    video.write_video(path, frames, fps=8, verify=False)
    np.testing.assert_array_equal(video.read_frames(path, method="preallocate"),
                                  video.read_frames(path))


def test_111_normals_match_old_curvature_path():
    import curvature3d
    rng = np.random.default_rng(111)
    p = rng.normal(size=(120, 3))
    old = curvature3d._curvatures(p, 18)[2]
    np.testing.assert_allclose(curvature3d.estimate_normals(p, 18), old, atol=1e-12, rtol=0)


def test_119_bandpass_matches_two_inverse_transforms():
    import signal1d
    y = np.random.default_rng(119).normal(size=2048)
    high = signal1d._apply_gain(y, signal1d._gauss_lp_gain(y.size, .4))
    low = signal1d._apply_gain(y, signal1d._gauss_lp_gain(y.size, .1))
    np.testing.assert_allclose(signal1d.bandpass(y), high - low, atol=1e-10, rtol=0)


def test_124_125_phase_paths_match_reference_contract():
    import complexops
    x = np.linspace(0, 12 * np.pi, 1000)[None]
    wrapped = (x + np.pi) % (2 * np.pi) - np.pi
    np.testing.assert_array_equal(complexops.phase_unwrap(wrapped), np.unwrap(wrapped, axis=1))


def test_126_real_transform_variant_matches_exact():
    import motionmag
    x = np.random.default_rng(126).normal(size=(32, 9, 11))
    expected = motionmag.temporal_bandpass(x, 2, 6, 32)
    np.testing.assert_allclose(
        motionmag.temporal_bandpass(x, 2, 6, 32, method="fast"), expected,
        atol=1e-10, rtol=0)


def _dominant_motion_old(u, v, robust=True, trim=0.25, iters=3):
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    h, w = u.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    a = np.stack([np.ones(h * w), xx.ravel(), yy.ravel()], axis=1)
    bu, bv = u.ravel(), v.ravel()
    finite = np.isfinite(bu) & np.isfinite(bv)
    if int(finite.sum()) < 3:
        return np.full((2, 3), np.nan)
    af, buf, bvf = a[finite], bu[finite], bv[finite]
    cu, *_ = np.linalg.lstsq(af, buf, rcond=None)
    cv, *_ = np.linalg.lstsq(af, bvf, rcond=None)
    if robust:
        for _ in range(max(1, int(iters))):
            resid = np.hypot(buf - af @ cu, bvf - af @ cv)
            threshold = np.quantile(resid, 1.0 - float(trim))
            keep = resid <= threshold
            if int(keep.sum()) < 3:
                break
            cu, *_ = np.linalg.lstsq(af[keep], buf[keep], rcond=None)
            cv, *_ = np.linalg.lstsq(af[keep], bvf[keep], rcond=None)
    return np.stack([cu, cv], axis=0)


def _motion_segments_old(u, v, threshold, min_area=25, smooth=1.0):
    ru, rv = np.asarray(u, np.float64), np.asarray(v, np.float64)
    mag = np.hypot(ru, rv)
    mask = mag > float(threshold)
    if smooth and smooth > 0:
        it = int(round(smooth))
        padded = ndimage.binary_closing(np.pad(mask, it, mode="edge"), iterations=it)
        mask = padded[it:-it, it:-it]
    labels, count = ndimage.label(mask)
    segments = []
    for label in range(1, count + 1):
        ys, xs = np.where(labels == label)
        if xs.size < int(min_area):
            mask[ys, xs] = False
            continue
        segments.append({
            "area": int(xs.size),
            "centroid": (float(ys.mean()), float(xs.mean())),
            "bbox": (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())),
            "mean_speed": float(mag[ys, xs].mean()),
        })
    segments.sort(key=lambda row: row["area"], reverse=True)
    return mask, segments


def _detect_events_old(energy, threshold=None, k=2.0):
    e = np.asarray(energy, np.float64)
    if e.size == 0:
        return np.zeros(0, dtype=int)
    threshold = float(e.mean() + float(k) * e.std()) if threshold is None else float(threshold)
    events = []
    for i in range(e.size):
        if e[i] <= threshold:
            continue
        left = e[i - 1] if i > 0 else -np.inf
        right = e[i + 1] if i < e.size - 1 else -np.inf
        if e[i] >= left and e[i] >= right:
            events.append(i)
    return np.array(events, dtype=int)


def test_131_dominant_motion_matches_two_rhs_reference():
    rng = np.random.default_rng(131)
    y, x = np.mgrid[:70, :90]
    u = 1e6 + 0.002 * x - 0.003 * y + rng.normal(0, 1e-8, x.shape)
    v = -1e6 + 0.004 * x + 0.001 * y + rng.normal(0, 1e-8, x.shape)
    u[10:25, 30:60] += 2.0
    v[10:25, 30:60] -= 3.0
    u[0, 0] = np.nan
    expected = _dominant_motion_old(u, v)
    np.testing.assert_array_equal(motion.dominant_motion(u, v), expected)
    np.testing.assert_allclose(motion.dominant_motion(u, v, method="fast"),
                               expected, atol=1e-8, rtol=0)


def test_132_motion_segments_matches_reference_stats_and_boxes():
    u = np.zeros((80, 100)); v = np.zeros_like(u)
    u[0:12, 3:20] = 2.5
    v[35:60, 50:85] = 4.0
    expected = _motion_segments_old(u, v, 1.0, min_area=10, smooth=1)
    actual = motion.motion_segments(u, v, 1.0, subtract_dominant=False, min_area=10, smooth=1)
    np.testing.assert_array_equal(actual[0], expected[0])
    assert actual[1] == expected[1]


def test_133_motion_energy_series_matches_materialized_reference(monkeypatch):
    import flow

    def fake_flow(a, b, **kwargs):
        return b - a, (b - a) * kwargs.get("scale", 2.0)

    monkeypatch.setattr(flow, "optical_flow_lk", fake_flow)
    frames = [np.full((19, 23), value) for value in (1, 2, 4, 9)]
    seq = [np.asarray(frame, np.float64) for frame in frames]
    expected = np.array([
        motion.frame_motion_energy(*fake_flow(a, b, scale=3.0))
        for a, b in zip(seq[:-1], seq[1:])
    ])
    np.testing.assert_array_equal(
        motion.motion_energy_series((frame for frame in frames), scale=3.0), expected)


def test_134_flow_from_model_is_bit_identical_to_full_grids():
    model = np.array([[1e6, 1e-9, -2e-9], [-1e6, 3e-9, 4e-9]])
    h, w = 137, 211
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    expected = (model[0, 0] + model[0, 1] * xx + model[0, 2] * yy,
                model[1, 0] + model[1, 1] * xx + model[1, 2] * yy)
    for actual, old in zip(motion.flow_from_model(model, (h, w)), expected):
        np.testing.assert_array_equal(actual, old)


def test_135_detect_events_matches_loops_for_flat_peaks_and_nan():
    for energy in (np.array([]), np.array([0., 2., 2., 0., np.nan, 3., 0.]),
                   np.random.default_rng(135).normal(size=10001)):
        np.testing.assert_array_equal(motion.detect_events(energy, threshold=1.0),
                                      _detect_events_old(energy, threshold=1.0))
