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


def test_photometric_stereo_lit_only_removes_attached_shadow_bias():
    """★付着影のバイアス(2026-09-04 修正): モデルの max(N·L, 0) は非線形なので、
    N·L < 0 の観測を線形最小二乗にそのまま入れると解が偏る。影も AO も無い球で
    実測 6.5°。`lit_only=True` は画素ごとに点灯している光源だけで解き直し、0.00x° に戻す。"""
    import numpy as np
    import photometric as P

    n = 128
    y, x = np.mgrid[-1:1:n * 1j, -1:1:n * 1j]
    r2 = x * x + y * y
    m = r2 < 0.98
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    N = np.stack([x, y, z], -1)
    N = N / np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-12)

    L = []
    for a in np.linspace(0, 2 * np.pi, 6, endpoint=False):
        v = np.array([np.cos(a) * 0.85, np.sin(a) * 0.85, 0.53])
        L.append(v / np.linalg.norm(v))
    L = np.array(L)
    imgs = [np.clip(np.einsum("ijk,k->ij", N, l), 0.0, None) * 0.8 * m for l in L]

    def err(nr):
        d = np.clip(np.abs(np.einsum("ijk,ijk->ij", nr, N)), 0.0, 1.0)
        return float(np.median(np.degrees(np.arccos(d))[m]))

    plain, _ = P.photometric_stereo(imgs, L, mask=m)
    lit, _ = P.photometric_stereo(imgs, L, mask=m, lit_only=True)
    e_plain, e_lit = err(plain), err(lit)
    assert e_plain > 2.0, f"付着影のバイアスが再現していない: {e_plain:.3f} deg"
    assert e_lit < 0.05, f"lit_only がバイアスを取り切れていない: {e_lit:.3f} deg"
    assert e_lit < 0.05 * e_plain


def test_photometric_stereo_lit_only_falls_back_when_too_few_lights():
    """点灯光源が 3 未満の画素は全光源の解に戻す(fail-open) — 形と有限性は保つ。"""
    import numpy as np
    import photometric as P

    imgs = [np.zeros((8, 8)) for _ in range(4)]
    imgs[0][:] = 0.5                                    # 1 灯しか点いていない
    L = np.array([[0, 0, 1.0], [0.5, 0, 0.87], [-0.5, 0, 0.87], [0, 0.5, 0.87]])
    nr, al = P.photometric_stereo(imgs, L, lit_only=True)
    assert nr.shape == (8, 8, 3) and al.shape == (8, 8)
    assert np.isfinite(nr).all() and np.isfinite(al).all()
