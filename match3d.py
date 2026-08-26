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


def mesh_to_voxel(vertices, faces, size, bounds=None, samples=40000,
                  device="cpu", smooth=0.8):
    """mesh(頂点+面)→ 密度 voxel。面上を一様サンプリング → splat(mesh 行を全手法へ接続)。

    三角形上の一様点は barycentric(sqrt トリック)。占有 voxel が要るなら閾値化する。
    """
    V = np.asarray(vertices, np.float64)
    Fc = np.asarray(faces, np.int64)
    tri = V[Fc]                                          # (F,3,3)
    areas = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0],
                                          tri[:, 2] - tri[:, 0]), axis=1)
    p = areas / areas.sum()
    rng = np.random.default_rng(0)
    pick = rng.choice(len(Fc), size=samples, p=p)
    u = rng.random(samples); v = rng.random(samples)
    over = u + v > 1
    u[over] = 1 - u[over]; v[over] = 1 - v[over]
    t = tri[pick]
    pts = t[:, 0] + u[:, None] * (t[:, 1] - t[:, 0]) + v[:, None] * (t[:, 2] - t[:, 0])
    return points_to_voxel(pts, size, bounds, device, smooth)


def depth_to_points(depth, fx, fy, cx, cy, stride=1):
    """深度マップ(2.5D)→ point cloud(ピンホール逆投影)。depth 行を全手法へ接続。"""
    d = np.asarray(depth, np.float64)[::stride, ::stride]
    vv, uu = np.mgrid[0:d.shape[0], 0:d.shape[1]]
    z = d.reshape(-1)
    ok = z > 0
    u = (uu.reshape(-1)[ok] * stride - cx) * z[ok] / fx
    v = (vv.reshape(-1)[ok] * stride - cy) * z[ok] / fy
    return np.stack([u, v, z[ok]], axis=1)


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


def moment_axes(points, weights=None):
    """点群/重み付き点の **重心 + 主軸**(慣性テンソルの固有ベクトル)。姿勢推定の基礎。

    返り値 (centroid(3,), axes(3,3) 列=主軸, eigvals(3,))。固有値降順。回転の正準化に使う。
    """
    P = np.asarray(points, np.float64)
    w = np.ones(len(P)) if weights is None else np.asarray(weights, np.float64)
    w = w / w.sum()
    c = (P * w[:, None]).sum(0)
    Q = P - c
    cov = (Q * w[:, None]).T @ Q
    vals, vecs = np.linalg.eigh(cov)
    order = np.argsort(vals)[::-1]
    return c, vecs[:, order], vals[order]


def match_pca(pts_scene, pts_model):
    """PCA 姿勢マッチング(構造=point cloud × 手法=主軸整列)。

    両雲の主軸を合わせる粗い剛体変換(回転 R + 並進 t)を返す。NCC/位相相関が扱えない
    **回転**をここで担う(符号の 4 通り曖昧性は最小二乗で解消)。返り値 (R(3,3), t(3,))。
    """
    cs, As, _ = moment_axes(pts_scene)
    cm, Am, _ = moment_axes(pts_model)
    best = None
    Qs = np.asarray(pts_scene, np.float64) - cs
    Qm = np.asarray(pts_model, np.float64) - cm
    # 主軸の符号 4 通り(det=+1 の回転のみ)を試し、残差最小を選ぶ
    for sx in (1, -1):
        for sy in (1, -1):
            S = np.diag([sx, sy, sx * sy])
            R = As @ S @ Am.T
            if np.linalg.det(R) < 0:
                continue
            resid = float(np.mean(np.linalg.norm(
                Qs[:min(len(Qs), len(Qm))] - (R @ Qm[:min(len(Qs), len(Qm))].T).T, axis=1)))
            if best is None or resid < best[0]:
                best = (resid, R)
    R = best[1] if best else np.eye(3)
    t = cs - R @ cm
    return R, t


def match_mip_2d(scene_vol, model_vol, device="cpu"):
    """MIP 投影 → 2D NCC(構造=voxel → 2D × 手法=NCC、変換=直交 MIP)。

    3 直交方向の最大値投影で 3 枚の 2D 問題に落とし、既存の 2D NCC で定位 → 3 枚から 3D 座標を
    冗長推定。全 3D NCC より安く coarse alignment に。回転が無い平行移動探索向き。
    """
    sm = voxel_to_mips(scene_vol)
    mm = voxel_to_mips(model_vol)
    # 各投影で model MIP の bbox を切り出しテンプレ化 → 2D NCC
    axis_coords = {0: (1, 2), 1: (0, 2), 2: (0, 1)}   # 投影 ax が捨てる軸→残る 2 軸
    acc = {0: [], 1: [], 2: []}
    for ax in (0, 1, 2):
        s2, m2 = sm[ax], mm[ax]
        nz = np.argwhere(m2 > m2.max() * 0.05)
        if len(nz) == 0:
            continue
        lo = nz.min(0); hi = nz.max(0) + 1
        tmpl = m2[lo[0]:hi[0], lo[1]:hi[1]]
        r = M.ncc_locate_batch([s2], tmpl, device)[0]     # [score,row,col]=残る 2 軸の座標
        a0, a1 = axis_coords[ax]
        acc[a0].append(r[1]); acc[a1].append(r[2])
    pos = [float(np.mean(acc[k])) if acc[k] else 0.0 for k in (0, 1, 2)]
    return np.array(pos)


def _edges3d(vol, device, thr_ratio=0.3):
    gz, gy, gx = sobel3d(vol, device)
    mag = torch.sqrt(gz * gz + gy * gy + gx * gx)[0, 0]
    return (mag > thr_ratio * float(mag.max())).float()


def match_chamfer_3d(scene, template, device="cpu", thr=0.3):
    """chamfer / 距離場マッチング(部分・遮蔽に頑健)。voxel × chamfer 列。

    シーンのエッジの EDT(各 voxel から最近エッジまでの距離)に、テンプレのエッジ点を載せて
    距離和を最小化。score(pos)=Σ_{template edge} DT_scene(pos+edge)/n。**低いほど良い一致**。
    エッジ点の一部が欠けても効く(NCC より遮蔽に強い)。EDT は scipy CPU(GPU 厳密 EDT は
    jump-flooding 近似が将来課題)、相関(conv3d)は GPU。返り値 [chamfer 距離, d, h, w]。
    """
    from scipy import ndimage
    se = _edges3d(scene, device, thr).detach().cpu().numpy() > 0.5
    te = _edges3d(template, device, thr).detach().cpu().numpy() > 0.5
    dt = ndimage.distance_transform_edt(~se)                 # scene エッジまでの距離場
    n = max(1.0, float(te.sum()))
    Td, Th, Tw = te.shape
    pd, ph, pw = Td // 2, Th // 2, Tw // 2
    dtt = torch.as_tensor(dt[None, None], dtype=torch.float32, device=device)
    ker = torch.as_tensor(te[None, None].astype(np.float32), device=device)
    score = F.conv3d(F.pad(dtt, (pw, pw, ph, ph, pd, pd)), ker)[0, 0] / n
    D, H, W = np.asarray(scene).shape
    big = float(score.max()) + 1.0
    lo = (pd, ph, pw); hi = (D - (Td - 1 - pd), H - (Th - 1 - ph), W - (Tw - 1 - pw))
    mask = torch.full_like(score, big)
    if all(h > l for l, h in zip(lo, hi)):
        mask[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = 0.0
    s = (score + mask).detach().cpu().numpy()                # 無効位置は大 → argmin で除外
    idx = np.unravel_index(int(np.argmin(s)), s.shape)
    return np.array([float(s[idx]), float(idx[0]), float(idx[1]), float(idx[2])])


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
