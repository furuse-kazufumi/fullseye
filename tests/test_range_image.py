"""range_image — organized 深度処理の ground-truth 検証。"""
import numpy as np
import range_image as RI


def test_normals_from_depth_plane():
    """傾斜平面 z=a*u+b*v+c の法線が解析値 (-a,-b,1)/|.| と一致(正射・向き固定なし)。"""
    H = W = 40
    a, b, c = 0.3, -0.15, 20.0
    uu, vv = np.meshgrid(np.arange(W), np.arange(H))
    depth = a * uu + b * vv + c
    n = RI.normals_from_depth(depth, orient_to_camera=False)
    exp = np.array([-a, -b, 1.0]); exp /= np.linalg.norm(exp)
    inner = n[4:-4, 4:-4].reshape(-1, 3)
    dots = np.abs(inner @ exp)
    assert dots.min() > 0.999, f"min|dot|={dots.min():.5f}"


def test_normals_orient_to_camera():
    """front-facing 平面で orient_to_camera=True なら全法線がカメラ向き(nz<0)。"""
    H = W = 30
    depth = 0.2 * np.arange(W)[None, :] + 15.0 + np.zeros((H, W))
    n = RI.normals_from_depth(depth, orient_to_camera=True)
    assert np.all(n[..., 2] < 0), "全法線が視点向き(nz<0)であるべき"


def test_perspective_backprojection_center():
    """透視逆投影で主点画素は (0,0,d) に写る。"""
    H = W = 21
    depth = np.full((H, W), 5.0)
    P = RI.depth_to_organized_points(depth, fx=50.0, fy=50.0, cx=10.0, cy=10.0)
    assert np.allclose(P[10, 10], [0.0, 0.0, 5.0], atol=1e-6)
    assert P.shape == (H, W, 3)


def test_occlusion_edges_step():
    """深度ステップ(前景/背景)で境界が検出され、平坦部は検出されない。"""
    depth = np.full((20, 20), 10.0)
    depth[:, 10:] = 20.0
    e = RI.occlusion_edges(depth, rel_thresh=0.05)
    assert e[:, 9:11].any(), "ステップ境界が検出されるべき"
    assert not e[:, :5].any() and not e[:, 15:].any(), "平坦部は非検出"


def test_bearing_angle_ramp():
    """一方向ランプで bearing angle が概ね一定の非ゼロ値。"""
    depth = (0.5 * np.arange(30)[:, None] + np.zeros((30, 25))) + 10.0
    ba = RI.bearing_angle_image(depth, direction="down")
    inner = ba[2:-2, 2:-2]
    assert abs(np.degrees(np.arctan2(0.5, 1.0)) - inner.mean()) < 1.0
    assert inner.std() < 0.5


def test_valid_mask():
    depth = np.array([[1.0, 0.0], [np.nan, 3.0]])
    m = RI.valid_mask(depth)
    assert m.tolist() == [[True, False], [False, True]]


def test_occlusion_edges_continuous_slope_not_flagged():
    """[bug5] 完全連続の傾斜面(遮蔽なし)は遮蔽エッジとして検出してはならない。

    旧実装は一階勾配(=slope)を rel_thresh*median_depth と比較する次元不整合で、
    傾斜が median に対し大きい(=深度が小さい)と傾斜面全体を誤検出していた
    (この入力で旧挙動は occ_rate=1.000)。正しくは二階差分 ≈ 0 で occ_rate=0。
    """
    uu, vv = np.meshgrid(np.arange(30), np.arange(30))
    depth = 0.15 * uu + 0.5  # 完全連続な傾斜、全画素 depth>0
    e = RI.occlusion_edges(depth, rel_thresh=0.05)
    assert not e.any(), f"連続傾斜面は非遮蔽であるべき(occ_rate={e.mean():.3f})"


def test_occlusion_edges_fronto_parallel_step_detected():
    """[bug5] 正対の深度段差(fronto-parallel step)は段差位置で検出される。

    傾斜と段差を分離しても、真の不連続は取りこぼさないこと(行方向の段差)。
    """
    depth = np.full((20, 20), 8.0)
    depth[10:, :] = 25.0  # 行 9/10 の間に段差
    e = RI.occlusion_edges(depth, rel_thresh=0.05)
    assert e[9:11, :].any(), "段差位置(行9/10)が検出されるべき"
    assert not e[:5, :].any() and not e[15:, :].any(), "平坦部は非検出"


def test_normals_from_depth_degenerate_shape_rejected():
    """[bug10] 単一行(H=1)/単一列(W=1)は法線が定義できず ValueError で拒否。

    旧実装は np.gradient が要素不足で不親切な例外を投げていた。縮退軸の勾配を
    0 とみなすと cross(dPx,0)=[0,0,0] の縮退法線を静かに返すため、fail-closed で拒否する。
    """
    import pytest

    # 明示的で分かりやすいメッセージ(旧 numpy 内部の "Shape of array too small" ではなく
    # 2x2 未満は法線が定義できない旨)を要求 → 旧挙動では FAIL、新挙動で PASS。
    for shp in [(1, 10), (10, 1), (1, 1)]:
        with pytest.raises(ValueError, match=r"2x2"):
            RI.normals_from_depth(np.full(shp, 5.0))
    # 2x2 以上は従来どおり通ること(回帰の下限確認)
    n = RI.normals_from_depth(np.full((2, 2), 5.0), orient_to_camera=False)
    assert n.shape == (2, 2, 3)
