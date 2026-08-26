"""match3d — 3D マッチング・マトリクス(データ構造 × 2D 手法 × データ変換)。docs/MATCH_3D_MATRIX.md。

核心: 多くの 3D 手法は「3D データを既知の 2D 手法が効く表現へ変換」して作れる。ここに変換
(splat / 投影 / FFT / 勾配場)と、それらに載る手法(NCC は accel_match、shape-based / phase
correlation はここ)を集約する。GPU=torch cu128 / RTX5090。cv2/HALCON が手薄な 3D voxel
マッチングの差別化領域。
"""
from __future__ import annotations

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    _HAS_TORCH = True
except Exception:  # pragma: no cover
    _HAS_TORCH = False

import accel_match as M   # 3D NCC / pyramid / sub-voxel


# ═══════════════════════════════════════════════════════════════════════════
# データ変換(構造 → 共通の voxel / 勾配 表現)
# ═══════════════════════════════════════════════════════════════════════════
def points_to_voxel(points, size, bounds=None, device="cpu", smooth=0.0):
    """点群 (N,3) → 密度 voxel (size³)。scatter_add で splat、任意で gaussian 平滑。

    bounds=(lo,hi) を与えれば複数雲を同一格子に載せられる(=マッチング前提)。
    """
    P = np.asarray(points, np.float64)
    if bounds is None:
        lo, hi = P.min(0), P.max(0)
    else:
        lo, hi = np.asarray(bounds[0], np.float64), np.asarray(bounds[1], np.float64)
    span = np.maximum(hi - lo, 1e-9)
    idx = np.clip(np.floor((P - lo) / span * (size - 1)).astype(np.int64), 0, size - 1)
    flat = (idx[:, 0] * size + idx[:, 1]) * size + idx[:, 2]
    g = torch.zeros(size ** 3, dtype=torch.float32, device=device)
    g.scatter_add_(0, torch.as_tensor(flat, device=device),
                   torch.ones(len(P), dtype=torch.float32, device=device))
    vol = g.view(size, size, size)
    if smooth > 0:
        vol = _gauss3d(vol[None, None], smooth)[0, 0]
    return vol.detach().cpu().numpy().astype(np.float64)


def gaussians_to_voxel(means, scales, opacities, size, bounds, device="cpu"):
    """3DGS(異方性ガウス)→ 密度 voxel。各ガウスを means に opacity で置き、平均 scale で平滑。

    近似(等方 splat + 平滑): 厳密な異方共分散ラスタライズは重いので、まず means を opacity 重み
    で splat → scale 平均ぶん gaussian 平滑。マッチングの coarse alignment には十分。
    """
    P = np.asarray(means, np.float64)
    op = np.asarray(opacities, np.float64).reshape(-1)
    lo, hi = np.asarray(bounds[0], np.float64), np.asarray(bounds[1], np.float64)
    span = np.maximum(hi - lo, 1e-9)
    idx = np.clip(np.floor((P - lo) / span * (size - 1)).astype(np.int64), 0, size - 1)
    flat = (idx[:, 0] * size + idx[:, 1]) * size + idx[:, 2]
    g = torch.zeros(size ** 3, dtype=torch.float32, device=device)
    g.scatter_add_(0, torch.as_tensor(flat, device=device),
                   torch.as_tensor(op, dtype=torch.float32, device=device))
    vol = g.view(size, size, size)
    sig = float(np.mean(scales)) / span.mean() * size if np.size(scales) else 1.0
    vol = _gauss3d(vol[None, None], max(0.5, sig))[0, 0]
    return vol.detach().cpu().numpy().astype(np.float64)


def voxel_to_mips(vol):
    """3D → 直交 3 方向の最大値投影(MIP)。2D 手法(accel の 2D NCC 等)を適用する入口。"""
    v = np.asarray(vol, np.float64)
    return [v.max(axis=0), v.max(axis=1), v.max(axis=2)]


def _gauss1d(sigma, device):
    r = max(1, int(4.0 * sigma + 0.5))
    x = torch.arange(-r, r + 1, dtype=torch.float32, device=device)
    k = torch.exp(-(x * x) / (2 * sigma * sigma))
    return k / k.sum()


def _gauss3d(t, sigma):
    k = _gauss1d(sigma, t.device)
    r = (k.numel() - 1) // 2
    for ax in range(3):
        dim = 2 + ax
        shp = [1, 1, 1, 1, 1]; shp[dim] = k.numel()
        pad = [0, 0, 0, 0, 0, 0]; pad[(2 - ax) * 2] = r; pad[(2 - ax) * 2 + 1] = r
        t = F.conv3d(F.pad(t, tuple(pad), mode="replicate"), k.view(*shp))
    return t


def sobel3d(vol, device="cpu"):
    """3D 勾配 (gz,gy,gx)。導関数[-1,0,1]×平滑[1,2,1] の分離 conv3d。"""
    t = torch.as_tensor(np.asarray(vol, np.float32)[None, None], device=device)
    deriv = torch.tensor([-1.0, 0.0, 1.0], device=device)
    smooth = torch.tensor([1.0, 2.0, 1.0], device=device)
    grads = []
    for d in range(3):
        out = t
        for ax in range(3):
            k = deriv if ax == d else smooth
            r = 1
            shp = [1, 1, 1, 1, 1]; shp[2 + ax] = 3
            pad = [0, 0, 0, 0, 0, 0]; pad[(2 - ax) * 2] = r; pad[(2 - ax) * 2 + 1] = r
            out = F.conv3d(F.pad(out, tuple(pad), mode="replicate"), k.view(*shp))
        grads.append(out)
    return grads[0], grads[1], grads[2]      # (gz,gy,gx) 各 (1,1,D,H,W)


# ═══════════════════════════════════════════════════════════════════════════
# 手法(2D → 3D)
# ═══════════════════════════════════════════════════════════════════════════
def match_phase_3d(a, b, device="cpu"):
    """3D 位相相関(FFT)。b を a に合わせる整数シフト (dz,dy,dx) を返す。

    Reddy & Chatterji の 3D 版。相互パワースペクトルの逆 FFT のピーク = 平行移動。テンプレート
    不要・全 volume・O(N log N)。回転/スケールは別途(PCA / log-polar)。
    """
    A = torch.fft.fftn(torch.as_tensor(np.asarray(a, np.float32), device=device))
    B = torch.fft.fftn(torch.as_tensor(np.asarray(b, np.float32), device=device))
    R = A * B.conj()
    R = R / (R.abs() + 1e-9)
    r = torch.fft.ifftn(R).real
    pk = np.unravel_index(int(torch.argmax(r).item()), r.shape)
    shp = r.shape
    return tuple(int(p - s if p > s // 2 else p) for p, s in zip(pk, shp))   # 折り返し補正


def _unit_grad3d(vol, device, mc=0.0):
    gz, gy, gx = sobel3d(vol, device)
    mag = torch.sqrt(gz * gz + gy * gy + gx * gx)
    m = (mag > mc).float()
    inv = m / mag.clamp_min(1e-8)
    return gz * inv, gy * inv, gx * inv, m


def match_shape_3d(vol, template, device="cpu", mc=0.05, subvoxel=True):
    """3D 形状ベース(勾配方向)マッチング = 2D shapematch_gpu の voxel 版(「輪郭マッチング」)。

    テンプレとシーンの **単位勾配ベクトルの内積和**(Steger 流)。強度/コントラストに不変で、
    エッジ/形状で一致を測る。score(pos)=Σ<û_scene(pos+dt), û_model(dt)>/n を 3 成分の conv3d で。
    """
    sz, sy, sx, _ = _unit_grad3d(vol, device, mc)           # 単位勾配(シーン)
    tz, ty, tx, tm = _unit_grad3d(np.asarray(template, np.float64), device, mc)
    n = float(tm.sum().clamp_min(1.0))
    Td, Th, Tw = np.asarray(template).shape
    pd, ph, pw = Td // 2, Th // 2, Tw // 2

    def corr(scene, ker):
        return F.conv3d(F.pad(scene, (pw, pw, ph, ph, pd, pd)), ker)

    score = (corr(sz, tz) + corr(sy, ty) + corr(sx, tx)) / n
    D, H, W = np.asarray(vol).shape
    lo = (pd, ph, pw); hi = (D - (Td - 1 - pd), H - (Th - 1 - ph), W - (Tw - 1 - pw))
    mask = torch.zeros_like(score)
    if all(h > l for l, h in zip(lo, hi)):
        mask[:, :, lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = 1.0
    score = (score * mask)[0, 0].detach().cpu().numpy().astype(np.float64)
    idx = np.unravel_index(int(np.argmax(score)), score.shape)
    pos = M._subvoxel_com(score, idx, 2) if subvoxel else [float(i) for i in idx]
    return np.array([float(score[idx])] + pos)


def match_points_ncc(pts_scene, pts_model, size, bounds, device="cpu", smooth=0.8):
    """点群同士マッチング(構造=point cloud × 手法=NCC、変換=splat)。model を scene 内で定位。"""
    vs = points_to_voxel(pts_scene, size, bounds, device, smooth)
    vm_full = points_to_voxel(pts_model, size, bounds, device, smooth)
    nz = np.argwhere(vm_full > vm_full.max() * 0.05)
    if len(nz) == 0:
        return np.array([0.0, 0.0, 0.0, 0.0])
    lo = nz.min(0); hi = nz.max(0) + 1
    tmpl = vm_full[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]      # model の bbox を切り出しテンプレ化
    return M.ncc_locate_3d([vs], tmpl, device, subvoxel=True)[0]
