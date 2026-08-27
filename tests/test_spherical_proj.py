"""spherical_proj の ground-truth テスト(LiDAR 球面/円柱レンジ画像)。

GT は実装から独立に構成する:
  * 球面点群は「半径 R・既知 (方位角, 仰角)」から閉形式の球面→直交変換で生成し、
    その **元の 3D 点** を真値として往復(project→unproject)を検証する。
  * range は距離の閉形式(=R, または円柱半径 ρ0)で期待値が分かる。
全数値ケースを座標スケール 1 倍と 1000 倍で回し、tolerance はスケール相対(絶対 epsilon 不使用)。
縮退/不正入力は fail-closed(ValueError)、空入力は honest な空出力を確認する。
"""
import numpy as np
import pytest
from scipy.spatial import cKDTree

import spherical_proj as sp

SCALES = [1.0, 1000.0]
V_FOV = (-25.0, 15.0)


# ---------------------------------------------------------------------------
# 独立 GT ヘルパ(実装非依存の球面→直交変換)
# ---------------------------------------------------------------------------
def sph_to_cart(R, az_rad, el_rad):
    """半径・方位角・仰角[rad] → 直交座標(x=前方,y=左,z=上)。数学的恒等、実装非依存の GT。"""
    R = np.asarray(R, float); az = np.asarray(az_rad, float); el = np.asarray(el_rad, float)
    ce = np.cos(el)
    return np.stack([R * ce * np.cos(az), R * ce * np.sin(az), R * np.sin(el)], axis=-1)


def cyl_to_cart(rho, az_rad, z):
    """水平半径・方位角[rad]・高さ → 直交座標。実装非依存の GT。"""
    rho = np.asarray(rho, float); az = np.asarray(az_rad, float); z = np.asarray(z, float)
    return np.stack([rho * np.cos(az), rho * np.sin(az), z], axis=-1)


def cell_angles(h_res, v_res, v_fov):
    """1 セルの方位/仰角幅[rad]。往復誤差の理論境界(半セル)に使う。"""
    az_bin = 2.0 * np.pi / h_res
    el_bin = np.radians((v_fov[1] - v_fov[0]) / v_res)
    return az_bin, el_bin


# ---------------------------------------------------------------------------
# 1. 球面上の点は非空セルの range が全て ≈ R(スケール相対 rtol)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("R", SCALES)
def test_sphere_nonempty_ranges_equal_R(R):
    rng = np.random.default_rng(0)
    az = rng.uniform(-np.pi + 0.02, np.pi - 0.02, size=4000)
    # v_fov を十分カバーする仰角(帯の外は drop されるが、非空セルは必ず球面上=距離 R)
    el = np.radians(rng.uniform(-40.0, 40.0, size=4000))
    pts = sph_to_cart(R, az, el)
    img = sp.project_spherical(pts, h_res=512, v_res=64, v_fov=V_FOV)
    vals = img[img > 0]
    assert vals.size > 0
    # range は距離の閉形式(=R)。量子化されるのは角度だけなので range は R に一致(rtol 相対)。
    assert np.allclose(vals, R, rtol=1e-6), f"nonempty ranges should all equal R={R}"


# ---------------------------------------------------------------------------
# 2. project→unproject の往復が元点を角度分解能内で復元(中央値誤差 < ~2 セル×R)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("R", SCALES)
def test_roundtrip_within_angular_resolution(R):
    h_res, v_res = 1024, 64
    rng = np.random.default_rng(1)
    n = 500
    # 帯の内側(境界の fp/clip 影響を避けて 1° マージン)、seam を跨がない範囲でランダム。
    az = rng.uniform(-np.pi + 0.05, np.pi - 0.05, size=n)
    el = np.radians(rng.uniform(V_FOV[0] + 1.0, V_FOV[1] - 1.0, size=n))
    gt = sph_to_cart(R, az, el)                                   # 独立 GT の元 3D 点

    img = sp.project_spherical(gt, h_res=h_res, v_res=v_res, v_fov=V_FOV)
    rec = sp.unproject_spherical(img, v_fov=V_FOV)
    assert rec.shape[0] > 0

    # 復元点は各々いずれかの元点の近傍(半セル量子化)にあるはず。
    d, _ = cKDTree(gt).query(rec, k=1)
    az_bin, el_bin = cell_angles(h_res, v_res, V_FOV)
    bound = R * (az_bin + el_bin)                                 # ~2 セル角 × R
    assert np.median(d) < bound, f"median roundtrip err {np.median(d):.4g} !< {bound:.4g}"
    assert np.max(d) < 2.0 * bound, f"max roundtrip err {np.max(d):.4g} !< {2*bound:.4g}"
    # slant range は量子化されない → 復元点の距離は R のまま。
    assert np.allclose(np.linalg.norm(rec, axis=1), R, rtol=1e-6)


# ---------------------------------------------------------------------------
# 3. 既知方位/仰角が期待セルに落ちる(意味的アンカー、実装式の再導出でない)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("R", SCALES)
def test_forward_point_hits_center_column(R):
    """前方(+x, φ=0)の点は中央列 h_res//2 に落ち、range=R。"""
    h_res = 1024
    pts = np.array([[R, 0.0, 0.0]])                              # 真正面, 仰角 0
    img = sp.project_spherical(pts, h_res=h_res, v_res=64, v_fov=V_FOV)
    rows, cols = np.nonzero(img > 0)
    assert rows.size == 1
    assert cols[0] == h_res // 2, f"forward (+x) should map to center column, got {cols[0]}"
    assert np.isclose(img[rows[0], cols[0]], R, rtol=1e-6)


def test_elevation_top_and_bottom_rows():
    """仰角帯の上端付近 → 行 0(上)、下端付近 → 行 v_res-1(下)。"""
    v_res = 64
    R = 10.0
    top = sph_to_cart(R, 0.0, np.radians(V_FOV[1] - 0.5))[None, :]   # 上端寄り
    bot = sph_to_cart(R, 0.0, np.radians(V_FOV[0] + 0.5))[None, :]   # 下端寄り
    img_top = sp.project_spherical(top, h_res=256, v_res=v_res, v_fov=V_FOV)
    img_bot = sp.project_spherical(bot, h_res=256, v_res=v_res, v_fov=V_FOV)
    r_top = np.nonzero(img_top > 0)[0][0]
    r_bot = np.nonzero(img_bot > 0)[0][0]
    assert r_top == 0, f"top-of-FOV point should land on row 0, got {r_top}"
    assert r_bot == v_res - 1, f"bottom-of-FOV point should land on last row, got {r_bot}"


def test_elevation_ordering_higher_is_smaller_row():
    """高い仰角ほど小さい行(上)に来る(方位角は同一)。"""
    R = 5.0
    hi = sph_to_cart(R, 0.0, np.radians(10.0))[None, :]
    lo = sph_to_cart(R, 0.0, np.radians(-20.0))[None, :]
    row_hi = np.nonzero(sp.project_spherical(hi, v_fov=V_FOV) > 0)[0][0]
    row_lo = np.nonzero(sp.project_spherical(lo, v_fov=V_FOV) > 0)[0][0]
    assert row_hi < row_lo


# ---------------------------------------------------------------------------
# 4. スケール: R を 2 倍にすると range が 2 倍(同一角度セット)
# ---------------------------------------------------------------------------
def test_range_scales_linearly_with_radius():
    rng = np.random.default_rng(2)
    az = rng.uniform(-np.pi + 0.05, np.pi - 0.05, size=300)
    el = np.radians(rng.uniform(V_FOV[0] + 1.0, V_FOV[1] - 1.0, size=300))
    img1 = sp.project_spherical(sph_to_cart(1.0, az, el), v_fov=V_FOV)
    img2 = sp.project_spherical(sph_to_cart(2.0, az, el), v_fov=V_FOV)
    m1, m2 = img1 > 0, img2 > 0
    assert np.array_equal(m1, m2), "同一角度セットは同じセルを占有するはず"
    assert np.allclose(img2[m2], 2.0 * img1[m1], rtol=1e-6)


# ---------------------------------------------------------------------------
# 5. 円柱投影
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("rho0", SCALES)
def test_cylinder_nonempty_ranges_equal_rho(rho0):
    """半径 ρ0 の円柱上の点 → 非空セルの値は全て ≈ ρ0(水平半径, スケール相対)。"""
    rng = np.random.default_rng(3)
    az = rng.uniform(-np.pi + 0.02, np.pi - 0.02, size=3000)
    z = rng.uniform(-1.0, 1.0, size=3000)
    pts = cyl_to_cart(rho0, az, z)
    img = sp.project_cylindrical(pts, h_res=512, z_bins=64, z_range=(-1.0, 1.0))
    vals = img[img > 0]
    assert vals.size > 0
    assert np.allclose(vals, rho0, rtol=1e-6)


def test_cylinder_forward_center_column_and_z_ordering():
    """円柱: 前方(+x)は中央列, 高い z ほど小さい行。値=水平半径 ρ。"""
    h_res = 512
    zr = (-1.0, 1.0)
    fwd = np.array([[3.0, 0.0, 0.0]])
    img = sp.project_cylindrical(fwd, h_res=h_res, z_bins=64, z_range=zr)
    rows, cols = np.nonzero(img > 0)
    assert rows.size == 1 and cols[0] == h_res // 2
    assert np.isclose(img[rows[0], cols[0]], 3.0, rtol=1e-6)     # ρ=hypot(3,0)=3

    hi = np.array([[2.0, 0.0, 0.9]]); lo = np.array([[2.0, 0.0, -0.9]])
    row_hi = np.nonzero(sp.project_cylindrical(hi, z_range=zr) > 0)[0][0]
    row_lo = np.nonzero(sp.project_cylindrical(lo, z_range=zr) > 0)[0][0]
    assert row_hi < row_lo


def test_cylinder_range_scales_with_rho():
    """水平半径 ρ0 を 2 倍 → 円柱レンジも 2 倍(同一 az/z セット)。"""
    rng = np.random.default_rng(4)
    az = rng.uniform(-np.pi + 0.05, np.pi - 0.05, size=300)
    z = rng.uniform(-0.9, 0.9, size=300)
    img1 = sp.project_cylindrical(cyl_to_cart(1.0, az, z), z_range=(-1.0, 1.0))
    img2 = sp.project_cylindrical(cyl_to_cart(2.0, az, z), z_range=(-1.0, 1.0))
    m1, m2 = img1 > 0, img2 > 0
    assert np.array_equal(m1, m2)
    assert np.allclose(img2[m2], 2.0 * img1[m1], rtol=1e-6)


# ---------------------------------------------------------------------------
# 6. 近い点優先(同セルは最小 range)
# ---------------------------------------------------------------------------
def test_nearest_point_wins_same_cell():
    """同一方向の 2 点(近/遠)は同セルに落ち、近い方の range が残る。"""
    near = np.array([2.0, 0.0, 0.0])
    far = np.array([9.0, 0.0, 0.0])                              # 同じ +x 方向・同仰角
    img = sp.project_spherical(np.stack([far, near]), v_fov=V_FOV)
    vals = img[img > 0]
    assert vals.size == 1
    assert np.isclose(vals[0], 2.0, rtol=1e-6), "近い点(range=2)が残るべき"


# ---------------------------------------------------------------------------
# 7. 空入力・退化点は honest(fail-closed か空出力)
# ---------------------------------------------------------------------------
def test_empty_points_returns_zero_image():
    img = sp.project_spherical(np.empty((0, 3)), h_res=128, v_res=32, v_fov=V_FOV)
    assert img.shape == (32, 128)
    assert np.count_nonzero(img) == 0


def test_origin_point_is_dropped():
    """センサ原点上の点は方向未定義 → 落とす(全ゼロ)。"""
    img = sp.project_spherical(np.array([[0.0, 0.0, 0.0]]), v_fov=V_FOV)
    assert np.count_nonzero(img) == 0


def test_unproject_empty_returns_empty():
    out = sp.unproject_spherical(np.zeros((32, 128)), v_fov=V_FOV)
    assert out.shape == (0, 3)


def test_out_of_fov_points_dropped():
    """v_fov 外(真上・真下)の点は投影されない。"""
    up = np.array([[0.0, 0.0, 5.0]])                            # 仰角 +90°(帯外)
    down = np.array([[0.0, 0.0, -5.0]])                         # 仰角 -90°(帯外)
    assert np.count_nonzero(sp.project_spherical(up, v_fov=V_FOV)) == 0
    assert np.count_nonzero(sp.project_spherical(down, v_fov=V_FOV)) == 0


# ---------------------------------------------------------------------------
# 8. 不正入力は fail-closed(ValueError)
# ---------------------------------------------------------------------------
def test_bad_point_shape_raises():
    with pytest.raises(ValueError):
        sp.project_spherical(np.zeros((10, 2)))


def test_bad_v_fov_raises():
    with pytest.raises(ValueError):
        sp.project_spherical(np.zeros((3, 3)), v_fov=(15.0, -25.0))   # min >= max


def test_bad_resolution_raises():
    with pytest.raises(ValueError):
        sp.project_spherical(np.zeros((3, 3)), h_res=0)


def test_unproject_non_2d_raises():
    with pytest.raises(ValueError):
        sp.unproject_spherical(np.zeros((4, 4, 4)))


def test_cylinder_degenerate_zrange_raises():
    """全点が同じ z・z_range 未指定 → 高さビンが縮退 → fail-closed(詐称しない)。"""
    pts = np.array([[1.0, 0.0, 0.5], [0.0, 1.0, 0.5], [-1.0, 0.0, 0.5]])  # 全て z=0.5
    with pytest.raises(ValueError):
        sp.project_cylindrical(pts, z_range=None)


def test_cylinder_bad_zrange_raises():
    with pytest.raises(ValueError):
        sp.project_cylindrical(np.zeros((3, 3)), z_range=(1.0, 1.0))      # 幅ゼロ
