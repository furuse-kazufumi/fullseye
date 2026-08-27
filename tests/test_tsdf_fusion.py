"""tsdf_fusion の GT 検証: 球を多視点で解析的深度にレンダ→融合→表面点が球面上に載るか。

GT は「実装の再導出」ではなく独立に閉形式で作る:
  * 深度画像 = カメラ光線と球の解析的交点の **perpendicular Z-depth**(2 次方程式の近根)。
  * 抽出表面点の半径誤差 median(|‖p-center‖ - R|) を voxel サイズと比較(見た目でない数値)。
  * 融合が単フレームより **裏面(自己遮蔽側)を埋める**ことを角度カバレッジで確認。
すべて 2 スケール(小座標 R=0.5 / 大座標 R=50)で回し、絶対 epsilon 依存(note_15 Class A)を排除。
"""
import numpy as np
import pytest

import tsdf_fusion
import visualhull  # look_at(eye, target, up) -> (R, t)、X_cam = R X + t(OpenCV 規約)


# ──────────────────────────────────────────────────────────────────────────
# 独立 GT: 解析的な球の深度レンダラ + 多視点カメラ
# ──────────────────────────────────────────────────────────────────────────
def _render_sphere_depth(center, radius, R, t, K, H, W):
    """カメラ (R,t,K) から半径 radius の球を見た解析的深度画像(交点の perpendicular Z、miss=0)。"""
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    Cc = R @ np.asarray(center, float) + np.asarray(t, float)      # 球中心をカメラ座標へ
    uu, vv = np.meshgrid(np.arange(W), np.arange(H))               # uu=u(col), vv=v(row)
    d = np.stack([(uu - cx) / fx, (vv - cy) / fy, np.ones_like(uu, float)], axis=-1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)                 # 単位光線方向(カメラ原点発)
    b = (d * Cc).sum(-1)                                           # d·Cc
    c = float(Cc @ Cc) - radius ** 2
    disc = b * b - c                                               # 判別式
    s_near = b - np.sqrt(np.clip(disc, 0.0, None))                 # 近い交点までの距離
    valid = (disc >= 0.0) & (s_near > 0.0)
    Zc = s_near * d[..., 2]                                        # perpendicular Z-depth
    depth = np.zeros((H, W), dtype=np.float64)
    depth[valid] = Zc[valid]
    return depth


def _fib_dirs(n):
    """Fibonacci 球で n 個の単位方向(視点配置用、ほぼ等方)。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    ga = np.pi * (1.0 + 5.0 ** 0.5)
    th = ga * i
    return np.stack([np.sin(phi) * np.cos(th),
                     np.sin(phi) * np.sin(th),
                     np.cos(phi)], axis=1)


def _build_scene(radius, n_views, H=100, W=100, focal=130.0):
    """半径 radius の球を n_views で囲む解析的シーン一式を返す。

    距離 D=4*radius(比を固定 → focal はスケール不変)。bounds は球中心 ± 1.25*radius の cube。
    """
    center = np.array([0.17, -0.11, 0.08], float) * radius        # 原点非対称(判別性)
    D = 4.0 * radius
    eyes = center[None, :] + D * _fib_dirs(n_views)
    K = np.array([[focal, 0.0, (W - 1) / 2.0],
                  [0.0, focal, (H - 1) / 2.0],
                  [0.0, 0.0, 1.0]], float)
    depths, Ks, Rs, ts = [], [], [], []
    for eye in eyes:
        R, t = visualhull.look_at(eye, center, up=(0.0, 0.0, 1.0))
        depths.append(_render_sphere_depth(center, radius, R, t, K, H, W))
        Ks.append(K); Rs.append(R); ts.append(t)
    m = 1.25 * radius
    bounds = ((center[0] - m, center[0] + m),
              (center[1] - m, center[1] + m),
              (center[2] - m, center[2] + m))
    res = 64
    voxel = 2.0 * m / res
    trunc = 4.0 * voxel                                           # 表面帯 = 数 voxel
    return dict(center=center, radius=radius, eyes=eyes, depths=depths,
                Ks=Ks, Rs=Rs, ts=ts, bounds=bounds, res=res, trunc=trunc, voxel=voxel)


def _radius_error_median(pts, center, radius):
    r = np.linalg.norm(pts - np.asarray(center, float), axis=1)
    return float(np.median(np.abs(r - radius)))


# ──────────────────────────────────────────────────────────────────────────
# 1) 表面点が球面上に載る(2 スケール = 絶対 epsilon 排除)
# ──────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("radius", [0.5, 50.0])
def test_extracted_points_lie_on_sphere(radius):
    sc = _build_scene(radius, n_views=12)
    tsdf, weight = tsdf_fusion.fuse(sc["depths"], sc["Ks"], sc["Rs"], sc["ts"],
                                    sc["bounds"], sc["res"], sc["trunc"])
    pts = tsdf_fusion.extract_surface_points(tsdf, weight, sc["bounds"], sc["res"])
    assert pts.shape[0] > 500, "十分な表面点が抽出されるべき"
    err = _radius_error_median(pts, sc["center"], radius)
    # 交点は voxel 辺の線形補間 + 画素量子化(0.5px)由来の系統誤差。閾値は voxel サイズに相対。
    assert err < 2.0 * sc["voxel"], f"radius median err {err:.4g} vs voxel {sc['voxel']:.4g}"
    # 分布の広がり(percentile)も voxel の数倍以内であること。
    r = np.linalg.norm(pts - sc["center"], axis=1)
    p90 = float(np.percentile(np.abs(r - radius), 90))
    assert p90 < 4.0 * sc["voxel"], f"p90 err {p90:.4g} vs voxel {sc['voxel']:.4g}"


# ──────────────────────────────────────────────────────────────────────────
# 2) 融合は単フレームより裏面(自己遮蔽側)を埋める = 被覆改善
# ──────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("radius", [0.5, 50.0])
def test_fusion_fills_holes_vs_single_frame(radius):
    sc = _build_scene(radius, n_views=14)
    center = sc["center"]
    # 単フレーム(視点 0 のみ)
    ts_single, w_single = tsdf_fusion.fuse([sc["depths"][0]], [sc["Ks"][0]],
                                           [sc["Rs"][0]], [sc["ts"][0]],
                                           sc["bounds"], sc["res"], sc["trunc"])
    p_single = tsdf_fusion.extract_surface_points(ts_single, w_single, sc["bounds"], sc["res"])
    # 全フレーム融合
    ts_full, w_full = tsdf_fusion.fuse(sc["depths"], sc["Ks"], sc["Rs"], sc["ts"],
                                       sc["bounds"], sc["res"], sc["trunc"])
    p_full = tsdf_fusion.extract_surface_points(ts_full, w_full, sc["bounds"], sc["res"])

    o0 = (sc["eyes"][0] - center) / np.linalg.norm(sc["eyes"][0] - center)  # 視点0 の外向き
    # 「裏面」= 視点0 から見て球の向こう側(自己遮蔽で単フレームでは観測不能)
    far_single = int(np.sum((p_single - center) @ o0 < 0))
    far_full = int(np.sum((p_full - center) @ o0 < 0))
    frac_single = far_single / max(len(p_single), 1)
    frac_full = far_full / max(len(p_full), 1)

    assert frac_single < 0.05, f"単フレームは裏面をほぼ観測しないはず (frac={frac_single:.3f})"
    assert frac_full > 0.25, f"融合は裏面を実質的に埋めるはず (frac={frac_full:.3f})"
    assert far_full > 10 * max(far_single, 1), "裏面点数が単フレームより桁違いに増える"
    assert len(p_full) > len(p_single), "融合で総表面点が増える(被覆改善)"


# ──────────────────────────────────────────────────────────────────────────
# 3) 符号規約の判別テスト(表面手前=+ / 内側=−、独立に構成)
# ──────────────────────────────────────────────────────────────────────────
def test_sign_convention_front_positive_inside_negative():
    sc = _build_scene(2.0, n_views=1)  # 1 視点で十分(局所符号を見る)
    tsdf, weight = tsdf_fusion.fuse(sc["depths"], sc["Ks"], sc["Rs"], sc["ts"],
                                    sc["bounds"], sc["res"], sc["trunc"])
    center, radius = sc["center"], sc["radius"]
    o0 = (sc["eyes"][0] - center) / np.linalg.norm(sc["eyes"][0] - center)
    delta = 0.5 * sc["trunc"]                              # trunc 内なので両点とも観測される
    p_out = center + (radius + delta) * o0                 # 表面より手前(空き空間)
    p_in = center + (radius - delta) * o0                  # 表面より内側

    def _voxel_val(p):
        b = np.asarray(sc["bounds"], float)
        r = sc["res"]
        idx = ((p - b[:, 0]) / (b[:, 1] - b[:, 0]) * r - 0.5)
        i, j, k = np.clip(np.rint(idx).astype(int), 0, r - 1)
        return tsdf[i, j, k], weight[i, j, k]

    v_out, w_out = _voxel_val(p_out)
    v_in, w_in = _voxel_val(p_in)
    assert w_out > 0 and w_in > 0, "両点とも観測されているべき"
    assert v_out > 0, f"手前 voxel は正(空き空間)であるべき: {v_out}"
    assert v_in < 0, f"内側 voxel は負であるべき: {v_in}"


# ──────────────────────────────────────────────────────────────────────────
# 4) 縮退/空入力の honest な扱い(fail-closed か空返し)
# ──────────────────────────────────────────────────────────────────────────
def test_empty_frames_fail_closed():
    bounds = ((-1, 1), (-1, 1), (-1, 1))
    with pytest.raises(ValueError):
        tsdf_fusion.fuse([], [], [], [], bounds, 16, 0.1)


def test_all_invalid_depth_returns_empty_surface():
    # 全画素 0(=無効)の深度のみ → どの voxel も観測されず weight=0 → 表面点は空(詐称しない)
    bounds = ((-1, 1), (-1, 1), (-1, 1))
    res = 24
    K = np.array([[100.0, 0, 12.0], [0, 100.0, 12.0], [0, 0, 1.0]])
    R = np.eye(3)
    t = np.array([0.0, 0.0, 5.0])
    depth0 = np.zeros((25, 25))
    tsdf, weight = tsdf_fusion.fuse([depth0, depth0], [K, K], [R, R], [t, t],
                                    bounds, res, 0.2)
    assert float(weight.max()) == 0.0, "有効観測ゼロなら weight は全 0"
    pts = tsdf_fusion.extract_surface_points(tsdf, weight, bounds, res)
    assert pts.shape == (0, 3), "観測が無ければ表面点は空 (0,3)"


def test_new_volume_and_integrate_validation():
    # 退化 bounds / 非正 res / 非正 trunc は fail-closed
    with pytest.raises(ValueError):
        tsdf_fusion.new_volume(((0, 0), (0, 1), (0, 1)), 8)      # 幅 0 の軸
    with pytest.raises(ValueError):
        tsdf_fusion.new_volume(((0, 1), (0, 1), (0, 1)), 0)      # res=0
    tsdf, weight = tsdf_fusion.new_volume(((0, 1), (0, 1), (0, 1)), 8)
    assert tsdf.dtype == np.float32 and weight.dtype == np.float32
    assert np.all(tsdf == 1.0) and np.all(weight == 0.0)
    K = np.eye(3); K[0, 2] = 5; K[1, 2] = 5
    with pytest.raises(ValueError):
        tsdf_fusion.integrate(tsdf, weight, np.zeros((10, 10)), K, np.eye(3),
                              np.array([0, 0, 1.0]), trunc=0.0, bounds=((0, 1), (0, 1), (0, 1)))


# ──────────────────────────────────────────────────────────────────────────
# 5) 融合の単調性: 同じ表面を複数回統合しても表面は動かない(重み平均の整合)
# ──────────────────────────────────────────────────────────────────────────
def test_repeated_integration_is_consistent():
    sc = _build_scene(3.0, n_views=1)
    depth, K, R, t = sc["depths"][0], sc["Ks"][0], sc["Rs"][0], sc["ts"][0]
    # 1 回統合
    tsdf1, w1 = tsdf_fusion.new_volume(sc["bounds"], sc["res"])
    tsdf_fusion.integrate(tsdf1, w1, depth, K, R, t, sc["trunc"], bounds=sc["bounds"])
    p1 = tsdf_fusion.extract_surface_points(tsdf1, w1, sc["bounds"], sc["res"])
    # 同じフレームを 3 回統合(移動平均なので TSDF 値は不変のはず → 表面も不変)
    tsdf3, w3 = tsdf_fusion.new_volume(sc["bounds"], sc["res"])
    for _ in range(3):
        tsdf_fusion.integrate(tsdf3, w3, depth, K, R, t, sc["trunc"], bounds=sc["bounds"])
    assert float(w3.max()) == 3.0, "同じ画素は 3 回観測で weight=3"
    obs = w1 > 0
    assert np.allclose(tsdf1[obs], tsdf3[obs], atol=1e-6), "同一観測の反復で TSDF は不変"
    p3 = tsdf_fusion.extract_surface_points(tsdf3, w3, sc["bounds"], sc["res"])
    assert p1.shape == p3.shape
