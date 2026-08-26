"""photometric — フォトメトリックステレオと法線積分(Physical AI 外観検査・形状復元)。

既知の複数光源方向で撮った Lambertian 画像から画素ごとに法線 + アルベドを復元し、
Frankot-Chellappa の FFT 積分で法線場から深度(高さ場)を復元する。すべて閉形式で
ground-truth 数値検証できる。差別化 = 検査(法線マップで微小凹凸を顕在化)+ 世界モデル/
検査サンプル生成(render_lambertian で逆に合成 = 順方向レンダでループを閉じる)。

honest な前提: Lambertian + 既知光源 + 影なし(N·L>0)で線形最小二乗が厳密。影(N·L<0)や
スペキュラは線形性を破るので、頑健版(median / RANSAC over lights)が別途要る。
"""
import numpy as np


def _as_stack(images):
    a = np.asarray(images, dtype=np.float64)
    if a.ndim != 3:
        raise ValueError("images は (N,H,W) 形状が必要")
    return a


def photometric_stereo(images, lights, mask=None, normalize=True):
    """Lambertian フォトメトリックステレオ: 既知光源方向の N 枚から法線とアルベドを復元。→ (normals HxWx3, albedo HxW)。

    I_n = albedo * max(N·L_n, 0)。各画素で g = albedo*N を最小二乗 g = pinv(L) @ I で解き、
    albedo=|g|, normal=g/|g|。N>=3 必要。albedo~0 や mask 外の画素は normal=(0,0,1)。
    normalize=True で光源ベクトルを単位方向に正規化(render_lambertian と同一規約 = アルベド絶対値が正しく出る)。
    強度重み付き光源を使うなら normalize=False にし、合成側も生ベクトルで揃えること。
    """
    I = _as_stack(images)                       # (N,H,W)
    L = np.asarray(lights, dtype=np.float64)    # (N,3)
    if L.ndim != 2 or L.shape[1] != 3:
        raise ValueError("lights は (N,3) 形状が必要")
    N, H, W = I.shape
    if L.shape[0] != N:
        raise ValueError("images と lights の枚数が不一致")
    if N < 3:
        raise ValueError("光源は 3 方向以上必要")
    if normalize:
        L = L / (np.linalg.norm(L, axis=1, keepdims=True) + 1e-12)
    Iv = I.reshape(N, H * W)                     # (N,P)
    Lpinv = np.linalg.pinv(L)                    # (3,N)  最小二乗
    g = Lpinv @ Iv                              # (3,P)  = albedo*normal
    albedo = np.linalg.norm(g, axis=0)          # (P,)
    normals = np.zeros((3, H * W))
    good = albedo > 1e-8
    normals[:, good] = g[:, good] / albedo[good]
    normals[2, ~good] = 1.0
    normals = normals.T.reshape(H, W, 3)
    albedo = albedo.reshape(H, W)
    if mask is not None:
        m = np.asarray(mask, bool)
        normals[~m] = (0.0, 0.0, 1.0)
        albedo[~m] = 0.0
    return normals.astype(np.float32), albedo.astype(np.float32)


def normals_to_gradients(normals):
    """法線 (...,3) → 勾配 (p,q)=(dz/dx, dz/dy)。n ∝ (-p,-q,1) ゆえ p=-nx/nz, q=-ny/nz。"""
    n = np.asarray(normals, float)
    nz = n[..., 2]
    nz = np.where(np.abs(nz) < 1e-6, np.sign(nz) * 1e-6 + 1e-12, nz)
    p = -n[..., 0] / nz
    q = -n[..., 1] / nz
    return p, q


def integrate_gradients(p, q):
    """勾配場 (p,q) → 高さ場 z を Frankot-Chellappa(FFT)で最小二乗積分。→ z HxW(平均0基準)。

    Z_hat(wx,wy) = (-j wx P_hat - j wy Q_hat) / (wx^2 + wy^2)、原点=0。周期境界前提ゆえ端に歪み。
    """
    p = np.asarray(p, float)
    q = np.asarray(q, float)
    H, W = p.shape
    wy = (2.0 * np.pi * np.fft.fftfreq(H))[:, None]
    wx = (2.0 * np.pi * np.fft.fftfreq(W))[None, :]
    P = np.fft.fft2(p)
    Q = np.fft.fft2(q)
    denom = wx ** 2 + wy ** 2
    denom[0, 0] = 1.0
    Z = (-1j * wx * P - 1j * wy * Q) / denom
    Z[0, 0] = 0.0
    z = np.real(np.fft.ifft2(Z))
    return (z - z.mean()).astype(np.float64)


def integrate_normals(normals, mask=None):
    """法線場 → 高さ場 z を Frankot-Chellappa 積分。→ z HxW(定数分の自由度あり・平均0基準)。"""
    p, q = normals_to_gradients(normals)
    if mask is not None:
        m = np.asarray(mask, bool)
        p = np.where(m, p, 0.0)
        q = np.where(m, q, 0.0)
    return integrate_gradients(p, q)


def surface_normals(z):
    """高さ場 z(HxW)→ 単位法線 (H,W,3)。n ∝ (-dz/dx, -dz/dy, 1)。深度→法線の順変換。"""
    zy, zx = np.gradient(np.asarray(z, float))
    n = np.stack([-zx, -zy, np.ones_like(zx)], axis=-1)
    n /= (np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12)
    return n.astype(np.float32)


def render_lambertian(normals, albedo, light, ambient=0.0):
    """法線 + アルベド + 光源方向 → Lambertian 画像(検査サンプル生成 / GT 検証 / 逆レンダの順方向)。→ HxW。"""
    n = np.asarray(normals, float)
    L = np.asarray(light, float)
    L = L / (np.linalg.norm(L) + 1e-12)
    ndotl = np.clip(n[..., 0] * L[0] + n[..., 1] * L[1] + n[..., 2] * L[2], 0.0, None)
    a = np.asarray(albedo, float)
    return (a * (ndotl + ambient)).astype(np.float32)


def synthesize_ps_images(normals, albedo, lights, ambient=0.0):
    """既知の法線 + アルベド + 光源群 → フォトメトリックステレオ入力画像列 (N,H,W)。テスト / サンプル生成用。"""
    L = np.asarray(lights, float)
    return np.stack([render_lambertian(normals, albedo, L[i], ambient) for i in range(L.shape[0])], axis=0)


def angular_error_deg(n_a, n_b):
    """2 つの法線場の画素ごと角度誤差(度)。→ HxW。検証用。"""
    a = np.asarray(n_a, float)
    b = np.asarray(n_b, float)
    a = a / (np.linalg.norm(a, axis=-1, keepdims=True) + 1e-12)
    b = b / (np.linalg.norm(b, axis=-1, keepdims=True) + 1e-12)
    d = np.clip(np.sum(a * b, axis=-1), -1.0, 1.0)
    return np.degrees(np.arccos(d))
