"""photometric — フォトメトリックステレオ + 法線積分の ground-truth 検証。"""
import numpy as np
import photometric as PH


def _bump(H=48, W=48, amp=3.0):
    """滑らかな凸バンプの高さ場(法線が概ね +z、影ゼロで PS 線形が厳密になる)。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    cy, cx = (H - 1) / 2, (W - 1) / 2
    r2 = ((xx - cx) / (0.4 * W)) ** 2 + ((yy - cy) / (0.4 * H)) ** 2
    return amp * np.exp(-r2)


_LIGHTS = np.array([
    [0.0, 0.0, 1.0],
    [0.4, 0.0, 1.0],
    [-0.4, 0.0, 1.0],
    [0.0, 0.4, 1.0],
    [0.0, -0.4, 1.0],
], float)


def test_photometric_stereo_recovers_normals():
    """既知法線から合成した画像列で法線を復元し、角度誤差が小さいことを確認。"""
    z = _bump()
    n_gt = PH.surface_normals(z)
    albedo_gt = np.full(z.shape, 0.8)
    imgs = PH.synthesize_ps_images(n_gt, albedo_gt, _LIGHTS)
    n_rec, alb_rec = PH.photometric_stereo(imgs, _LIGHTS)
    err = PH.angular_error_deg(n_gt, n_rec)
    assert err.mean() < 1.0, f"mean angular error {err.mean():.3f} deg"
    assert np.abs(alb_rec.mean() - 0.8) < 0.02, f"albedo {alb_rec.mean():.3f}"


def test_integrate_normals_recovers_shape():
    """法線を積分して高さ場を復元。内部領域で元形状と高相関(定数分は無視)。"""
    z = _bump()
    n_gt = PH.surface_normals(z)
    z_rec = PH.integrate_normals(n_gt)
    # 周期境界の端歪みを避け内部で比較
    zc = z[8:-8, 8:-8].ravel()
    rc = z_rec[8:-8, 8:-8].ravel()
    zc = zc - zc.mean()
    rc = rc - rc.mean()
    corr = np.corrcoef(zc, rc)[0, 1]
    assert corr > 0.98, f"shape corr {corr:.4f}"


def test_end_to_end_ps_then_integrate():
    """画像列 → PS で法線復元 → 積分で高さ復元、の一気通し。元形状と高相関。"""
    z = _bump(amp=2.0)
    n_gt = PH.surface_normals(z)
    imgs = PH.synthesize_ps_images(n_gt, np.full(z.shape, 0.7), _LIGHTS)
    n_rec, _ = PH.photometric_stereo(imgs, _LIGHTS)
    z_rec = PH.integrate_normals(n_rec)
    zc = z[8:-8, 8:-8].ravel(); rc = z_rec[8:-8, 8:-8].ravel()
    corr = np.corrcoef(zc - zc.mean(), rc - rc.mean())[0, 1]
    assert corr > 0.97, f"e2e shape corr {corr:.4f}"


def test_render_lambertian_matches_dot():
    """render_lambertian が N·L(clamp)と一致(閉形式の順方向)。"""
    n = np.zeros((1, 1, 3)); n[0, 0] = [0.0, 0.0, 1.0]
    img = PH.render_lambertian(n, np.ones((1, 1)), [0.0, 0.0, 1.0])
    assert abs(float(img[0, 0]) - 1.0) < 1e-5
    img2 = PH.render_lambertian(n, np.ones((1, 1)), [1.0, 0.0, 0.0])
    assert abs(float(img2[0, 0])) < 1e-5  # 垂直光は側面成分ゼロ


def test_flat_surface_zero_gradient():
    """平坦面 → 法線は +z、積分結果はほぼ平坦。"""
    z = np.zeros((32, 32))
    n = PH.surface_normals(z)
    assert np.allclose(n[..., 2], 1.0, atol=1e-5)
    z_rec = PH.integrate_normals(n)
    assert np.ptp(z_rec) < 1e-6
