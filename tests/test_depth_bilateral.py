"""depth_bilateral — エッジ保存 深度デノイズ / 穴埋め の ground-truth 検証。

全テストは閉形式または既知値で判定する:
  * bilateral の定数画像=恒等、スケール共変性(k 倍で出力も厳密 k 倍)は解析的に厳密。
  * 段差保存は「素朴ガウスは段差をぼかす」を対照群にして bilateral の優位を判別ケースで確認。
  * fill_holes は平面(線形場=離散調和の不動点)を復元する GT。定数は厳密、傾斜は収束残差のみ。
スケール依存の性質は ≥2 スケールで検証(絶対 epsilon 混入=失敗モード A の防止)。
"""
import numpy as np
import pytest
from scipy import ndimage

import depth_bilateral as DB


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def _piecewise_planar(scale=1.0, seed=0, noise_frac=0.02, step_frac=0.2):
    """区分的平面(共通傾斜 + 中央で段差)+ ガウスノイズ。clean/noisy/step/col を返す。

    scale で全深度を相似拡大。ノイズ std と段差は scale 相対(絶対閾値を避ける)。
    """
    H = W = 48
    uu, vv = np.meshgrid(np.arange(W), np.arange(H))
    base = 20.0 * scale
    slope_x, slope_y = 0.05 * scale, 0.03 * scale
    step = step_frac * base
    clean = base + slope_x * uu + slope_y * vv
    col = W // 2
    clean[:, col:] += step
    rng = np.random.default_rng(seed)
    noisy = clean + rng.normal(0.0, noise_frac * base, clean.shape)
    return clean, noisy, step, col


def _rmse(a, b, sl=np.s_[5:-5, 5:-5]):
    return float(np.sqrt(np.mean((a[sl] - b[sl]) ** 2)))


def _edge_jump(a, col, rows=np.s_[6:-6]):
    """境界列 col と col-1 の隣接列深度差の平均(段差の鮮鋭さの指標)。"""
    return float(np.mean(a[rows, col] - a[rows, col - 1]))


# --------------------------------------------------------------------------------------
# bilateral_filter_depth
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("scale", [1.0, 1000.0])
def test_bilateral_reduces_noise_and_preserves_step(scale):
    """[GT] bilateral はノイズを減らし(RMSE↓)、段差を保存する(素朴ガウスは段差をぼかす)。

    range_sigma を noise_std < range_sigma < step に取ると、同じ面のノイズは平滑し、段差(> range_sigma)は
    跨がない。対照の gaussian_filter は段差をぼかすため段差近傍の隣接列ジャンプが崩れる。≥2 スケールで確認。
    """
    clean, noisy, step, col = _piecewise_planar(scale=scale)
    noise_std = 0.02 * (20.0 * scale)
    ss = 2.0
    sr = 3.0 * noise_std  # noise_std < sr < step

    filt = DB.bilateral_filter_depth(noisy, ss, sr)
    gauss = ndimage.gaussian_filter(noisy, ss)

    rmse_noisy = _rmse(noisy, clean)
    rmse_bilat = _rmse(filt, clean)
    rmse_gauss = _rmse(gauss, clean)
    # ノイズ低減(素朴ガウスより良い; ガウスは段差をぼかし逆に悪化しうる)。
    assert rmse_bilat < 0.5 * rmse_noisy, f"scale={scale}: bilat {rmse_bilat} vs noisy {rmse_noisy}"
    assert rmse_bilat < rmse_gauss, f"scale={scale}: bilat {rmse_bilat} vs gauss {rmse_gauss}"

    # 段差保存: 隣接列ジャンプ / 真の段差。bilateral≈1、gauss は大きくぼける。
    true_jump = _edge_jump(clean, col)
    r_bilat = _edge_jump(filt, col) / true_jump
    r_gauss = _edge_jump(gauss, col) / true_jump
    assert r_bilat > 0.7, f"scale={scale}: bilateral が段差を保存していない r={r_bilat}"
    assert r_gauss < 0.4, f"scale={scale}: 対照ガウスが段差を保存(判別性なし) r={r_gauss}"
    assert r_bilat > 2.0 * r_gauss, f"scale={scale}: bilateral の段差保存優位が不十分"


@pytest.mark.parametrize("scale", [3.0, 3000.0])
def test_bilateral_constant_is_identity(scale):
    """[GT] 一様深度では全 range/空間重みが対称で num/den=定数、出力は入力に厳密一致(恒等)。"""
    d = np.full((25, 25), 7.0 * scale)
    out = DB.bilateral_filter_depth(d, spatial_sigma=2.5, range_sigma=0.5 * scale)
    assert np.allclose(out, 7.0 * scale, atol=1e-9 * scale, rtol=0.0)


@pytest.mark.parametrize("k", [10.0, 1000.0])
def test_bilateral_scale_covariance(k):
    """[GT] 閉形式のスケール共変性: bilateral(k·d, ss, k·sr) = k·bilateral(d, ss, sr)。

    range 重み exp(-(Δd)^2/2sr^2) は (Δd,sr) を同率スケールすると不変、値は k 倍。絶対閾値が無いことの証明。
    ≥2 の k で確認。
    """
    _, noisy, _, _ = _piecewise_planar(scale=1.0, seed=3)
    ss, sr = 2.0, 1.0
    f1 = DB.bilateral_filter_depth(noisy, ss, sr)
    f2 = DB.bilateral_filter_depth(k * noisy, ss, k * sr)
    denom = k * np.max(np.abs(f1))
    assert np.max(np.abs(f2 - k * f1)) / denom < 1e-12, f"k={k}: covariance broken"


def test_bilateral_invalid_center_stays_and_no_poison():
    """[GT] 無効中心(NaN)は出力も NaN(値を捏造しない)、かつ NaN は近傍へ伝播しない(重み 0 で除外)。"""
    clean, _, _, _ = _piecewise_planar()
    z = clean.copy()
    z[24, 24] = np.nan
    out = DB.bilateral_filter_depth(z, 2.0, 1.0, invalid=None)
    assert np.isnan(out[24, 24]), "無効中心は NaN のまま残すべき"
    assert np.isfinite(out[24, 25]) and np.isfinite(out[23, 24]), "近傍は有限(NaN 伝播なし)"
    assert int(np.sum(np.isnan(out))) == 1, "穴以外に偽 NaN が発生してはならない"


def test_bilateral_sentinel_invalid_excluded():
    """[GT] sentinel=0 の無効画素は近傍として寄与しない(=有効値だけで平均)。

    一様値 5.0 の中に 0 の穴を 1 つ置くと、有効近傍は全て 5.0 なので有効画素の出力は厳密 5.0
    (穴が寄与するなら 5 未満に引っ張られる)。中心の穴自体は元値 0 のまま残る。
    """
    d = np.full((15, 15), 5.0)
    d[7, 7] = 0.0
    out = DB.bilateral_filter_depth(d, 2.0, 1.0, invalid=0.0)
    mask = np.ones_like(d, bool)
    mask[7, 7] = False
    assert np.allclose(out[mask], 5.0, atol=1e-12), "穴が平均を汚染している"
    assert out[7, 7] == 0.0, "無効中心は元値のまま"


@pytest.mark.parametrize(
    "kwargs",
    [dict(spatial_sigma=0.0, range_sigma=1.0), dict(spatial_sigma=1.0, range_sigma=0.0),
     dict(spatial_sigma=-1.0, range_sigma=1.0), dict(spatial_sigma=1.0, range_sigma=np.nan)],
)
def test_bilateral_fail_closed_sigma(kwargs):
    """[fail-closed] 非正/非有限 sigma は ValueError(縮退を静かに通さない)。"""
    with pytest.raises(ValueError):
        DB.bilateral_filter_depth(np.ones((8, 8)), **kwargs)


def test_bilateral_fail_closed_shape():
    """[fail-closed] 2D 以外の入力は ValueError。"""
    with pytest.raises(ValueError):
        DB.bilateral_filter_depth(np.ones((4, 4, 3)), 1.0, 1.0)


# --------------------------------------------------------------------------------------
# joint_bilateral
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("scale", [1.0, 500.0])
def test_joint_bilateral_guide_drives_edge_preservation(scale):
    """[GT] joint bilateral はガイドのエッジで段差を保存する。判別ケース: エッジ有ガイド vs 平坦ガイド。

    深度の段差と同位置にエッジを持つガイドを与えると段差を保存しつつノイズ低減。エッジの無い平坦ガイドは
    段差情報が無く段差を跨いで平滑=ぼける。両者の段差ジャンプの差で「ガイドが効いている」ことを判別。
    """
    clean, noisy, step, col = _piecewise_planar(scale=scale, seed=7)
    H, W = clean.shape
    guide_edge = np.zeros((H, W))
    guide_edge[:, col:] = 1.0  # 深度段差と同位置の鮮鋭エッジ(値域 1.0)
    guide_flat = np.zeros((H, W))  # エッジ無し

    ss, sr = 2.5, 0.25  # ガイド値の単位: エッジ振幅 1.0 >> sr なので段差保存
    f_edge = DB.joint_bilateral(noisy, guide_edge, ss, sr)
    f_flat = DB.joint_bilateral(noisy, guide_flat, ss, sr)

    assert _rmse(f_edge, clean) < 0.5 * _rmse(noisy, clean), f"scale={scale}: エッジガイドでノイズ低減せず"

    true_jump = _edge_jump(clean, col)
    r_edge = _edge_jump(f_edge, col) / true_jump
    r_flat = _edge_jump(f_flat, col) / true_jump
    assert r_edge > 0.7, f"scale={scale}: エッジガイドが段差を保存していない r={r_edge}"
    assert r_flat < 0.4, f"scale={scale}: 平坦ガイドが段差を保存(判別性なし) r={r_flat}"
    assert r_edge > 2.0 * r_flat, f"scale={scale}: ガイド駆動のエッジ保存が確認できない"


def test_joint_bilateral_shape_mismatch_fail_closed():
    """[fail-closed] guide と depth の形状不一致は ValueError。"""
    with pytest.raises(ValueError):
        DB.joint_bilateral(np.ones((10, 10)), np.ones((10, 9)), 1.0, 1.0)


# --------------------------------------------------------------------------------------
# fill_holes
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("const", [7.0, 7000.0])
def test_fill_holes_flat_exact(const):
    """[GT] 一様深度の穴は厳密に定数へ補間される(定数場は離散調和の不動点、EDT 初期化も厳密)。≥2 スケール。"""
    d = np.full((30, 30), const)
    d[12:18, 12:18] = 0.0  # 6x6 の穴
    out = DB.fill_holes(d, max_radius=10.0)
    assert not np.any(np.isnan(out)), "max_radius 内の穴が埋まっていない"
    assert np.allclose(out, const, atol=1e-9 * const, rtol=0.0), "定数の復元が厳密でない"


@pytest.mark.parametrize("scale", [1.0, 1000.0])
def test_fill_holes_tilted_plane(scale):
    """[GT] 傾斜平面 z=a·u+b·v+c は線形=離散調和の不動点。穴内を厳密解へ収束補間する。≥2 スケール。

    真値は解析的な平面値(実装の再導出ではない独立 GT)。判定はスケール相対の相対誤差。
    """
    H = W = 40
    uu, vv = np.meshgrid(np.arange(W), np.arange(H))
    a, b, c = 0.2 * scale, 0.1 * scale, 15.0 * scale
    truth = a * uu + b * vv + c
    d = truth.copy()
    hole = np.zeros((H, W), bool)
    hole[20:27, 20:27] = True  # 7x7 の穴
    d[hole] = 0.0
    out = DB.fill_holes(d, max_radius=12.0)
    assert not np.any(np.isnan(out))
    # 正規化は平面自身の変動幅(ptp)で行う。median(truth)=DC で割ると DC 依存の早期収束
    # バグに構造的に盲目になる(勾配が 50% ずれても DC が大きければ rel≈0 で緑になる)。
    rel = np.max(np.abs(out[hole] - truth[hole])) / float(np.ptp(truth[hole]))
    assert rel < 1e-3, f"scale={scale}: 平面復元の相対誤差 {rel} が大きすぎる"
    # 有効画素は不変(Dirichlet 境界)。
    assert np.allclose(out[~hole], truth[~hole], atol=1e-9 * scale)


def test_fill_holes_large_offset_small_slope():
    """[GT 回帰] 大 DC + 小勾配(遠距離センサの実態)で平面を厳密復元する。

    収束 tol を DC(median|d|)基準にすると tol が勾配信号を超過し Jacobi が 1 歩で停止 →
    EDT 階段のまま 50% 誤差になる。変動幅(ptp)基準なら任意 DC で収束する。判定は平面の
    変動幅相対(DC で割らない)。offset を 1e6 まで振っても勾配 0.03/px を厳密復元できること。
    """
    H = W = 40
    uu, vv = np.meshgrid(np.arange(W), np.arange(H))
    truth = 1.0e6 + 0.03 * uu            # 大 DC・小勾配(DC/変動幅 ~ 1e6)
    d = truth.copy()
    hole = np.zeros((H, W), bool)
    hole[16:23, 16:23] = True
    d[hole] = 0.0
    out = DB.fill_holes(d, max_radius=12.0)
    assert not np.any(np.isnan(out[hole]))
    rel = np.max(np.abs(out[hole] - truth[hole])) / float(np.ptp(truth[hole]))
    assert rel < 1e-3, f"大 DC 平面の復元誤差 {rel}(変動幅相対)が大きすぎる=早期収束バグ"


def test_fill_holes_deep_hole_fail_closed():
    """[fail-closed] max_radius を超える深い穴は補間せず NaN で残す。境界近傍は埋まる。"""
    d = np.full((40, 40), 9.0)
    d[10:30, 10:30] = 0.0  # 20x20 の大穴、中心は有効画素から ~10px
    out = DB.fill_holes(d, max_radius=3.0)
    assert np.isnan(out[20, 20]), "max_radius を超える深部は NaN で残すべき"
    assert np.isfinite(out[11, 11]) and abs(out[11, 11] - 9.0) < 1e-6, "境界近傍(半径内)は埋まるべき"


def test_fill_holes_nan_and_sentinel_both_treated():
    """[GT] NaN と sentinel=0 の双方を穴とみなして補間する(一様場では厳密復元)。"""
    d = np.full((20, 20), 4.0)
    d[5, 5] = np.nan
    d[14, 14] = 0.0
    out = DB.fill_holes(d, max_radius=6.0)
    assert np.allclose(out, 4.0, atol=1e-9), "NaN/sentinel の双方が復元されるべき"


def test_fill_holes_no_holes_is_identity():
    """[GT] 穴が無ければ入力のコピーをそのまま返す。"""
    d = np.array([[1.0, 2.0], [3.0, 4.0]])
    out = DB.fill_holes(d, max_radius=2.0)
    assert np.array_equal(out, d) and out is not d


@pytest.mark.parametrize("bad_r", [0.0, -1.0, np.nan])
def test_fill_holes_fail_closed_radius(bad_r):
    """[fail-closed] 非正/非有限 max_radius は ValueError。"""
    with pytest.raises(ValueError):
        DB.fill_holes(np.ones((5, 5)), bad_r)


def test_fill_holes_fully_invalid_fail_closed():
    """[fail-closed] 全画素無効(補間の足場なし)は ValueError(勝手に値を作らない)。"""
    with pytest.raises(ValueError):
        DB.fill_holes(np.zeros((6, 6)), max_radius=3.0)


def test_fill_holes_fail_closed_shape():
    """[fail-closed] 2D 以外は ValueError。"""
    with pytest.raises(ValueError):
        DB.fill_holes(np.ones((4, 4, 2)), 2.0)
