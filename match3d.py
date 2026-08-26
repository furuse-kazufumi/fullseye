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


def match_chamfer_3d(scene, template, device="cpu", thr=0.3, edt="scipy"):
    """chamfer / 距離場マッチング(部分・遮蔽に頑健)。voxel × chamfer 列。

    シーンのエッジの EDT(各 voxel から最近エッジまでの距離)に、テンプレのエッジ点を載せて
    距離和を最小化。score(pos)=Σ_{template edge} DT_scene(pos+edge)/n。**低いほど良い一致**。
    エッジ点の一部が欠けても効く(NCC より遮蔽に強い)。相関(conv3d)は常に GPU。距離場は
    edt="scipy"(CPU、既定)か edt="jfa"(`edt_jfa`、全 GPU で CPU 往復なし。scipy と厳密一致)。
    返り値 [chamfer 距離, d, h, w]。
    """
    se = _edges3d(scene, device, thr).detach().cpu().numpy() > 0.5
    te = _edges3d(template, device, thr).detach().cpu().numpy() > 0.5
    if edt == "jfa":
        dtt = edt_jfa(se, device)[None, None].to(torch.float32)   # 全 GPU 距離場
    else:
        from scipy import ndimage
        dt = ndimage.distance_transform_edt(~se)            # scene エッジまでの距離場
        dtt = torch.as_tensor(dt[None, None], dtype=torch.float32, device=device)
    n = max(1.0, float(te.sum()))
    Td, Th, Tw = te.shape
    pd, ph, pw = Td // 2, Th // 2, Tw // 2
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


# ═══════════════════════════════════════════════════════════════════════════
# 回転 + スケール(log-polar × 位相相関 = Fourier-Mellin、z 軸部分群)
# ═══════════════════════════════════════════════════════════════════════════
def _hp_emphasis(H, W, device):
    """Reddy-Chatterji 高域強調 H=(1-X)(2-X), X=cos(pi fy)cos(pi fx)。DC 支配を抑える。"""
    fy = torch.linspace(-0.5, 0.5, H, device=device)[:, None]
    fx = torch.linspace(-0.5, 0.5, W, device=device)[None, :]
    X = torch.cos(np.pi * fy) * torch.cos(np.pi * fx)
    return (1 - X) * (2 - X)


def _fmt_spectrum(img2d, device):
    """2D → Hann 窓 → |FFT| → fftshift → 高域強調。平行移動不変な回転/スケール表現。"""
    H, W = img2d.shape
    wy = torch.hann_window(H, periodic=False, device=device)[:, None]
    wx = torch.hann_window(W, periodic=False, device=device)[None, :]
    t = torch.as_tensor(np.asarray(img2d, np.float32), device=device) * wy * wx
    Fv = torch.fft.fftshift(torch.fft.fft2(t)).abs()
    return Fv * _hp_emphasis(H, W, device)


def _logpolar(img2d, nt, nr, device, rmin=2.0):
    """2D → log-polar(theta∈[0,π): |FFT| は 180° 対称、rho は対数)。grid_sample で GPU。"""
    H, W = img2d.shape
    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
    rmax = min(H, W) / 2.0 - 1
    theta = torch.linspace(0, float(np.pi), nt, device=device)
    rho = torch.exp(torch.linspace(float(np.log(rmin)), float(np.log(rmax)), nr, device=device))
    ys = cy + rho[None, :] * torch.sin(theta[:, None])
    xs = cx + rho[None, :] * torch.cos(theta[:, None])
    grid = torch.stack([xs / (W - 1) * 2 - 1, ys / (H - 1) * 2 - 1], dim=-1)[None]
    out = F.grid_sample(img2d[None, None], grid, align_corners=True, mode="bilinear")
    return out[0, 0], float(np.log(rmax) - np.log(rmin))


def _parab(r, i, axis, fix):
    """周期対応の放物線サブピクセル。axis 方向 i、他軸 fix の近傍 3 点で頂点を補間。"""
    n = r.shape[axis]

    def g(k):
        k = k % n
        return float(r[k, fix] if axis == 0 else r[fix, k])

    a, b, c = g(i - 1), g(i), g(i + 1)
    d = a - 2 * b + c
    return i + (0.5 * (a - c) / d if abs(d) > 1e-9 else 0.0)


def match_logpolar_z(a, b, device="cpu", project="mip", nt=360, nr=192):
    """log-polar × 位相相関(Fourier-Mellin)で **z 軸回転 + 等方スケール**を復元。

    構造=voxel × 手法=Fourier-Mellin。PCA が点対応を要すのに対し、これはテンプレ/対応不要で
    回転(z 軸)とスケールを同時推定する唯一の列。核心: z 投影(MIP)を取ると z 軸回転=面内回転・
    等方スケール=面内スケールに落ち、確立された 2D Fourier-Mellin(|FFT|→高域強調→log-polar→
    位相相関)が使える。返り値 (angle_deg, scale)。

    honest な限界(**coarse 推定器**、下流で NCC/ICP 精緻化前提): |回転|≲40° で誤差 ~2-5°。
    |FFT| の 180° 対称により ±45°/±90° 近傍は別名化して外し得る。スケールは中央ローブ偏りで
    ~10% 過小に出る。full-whitening はこの投影の非シフト DC プラトーでゼロロックするため、
    plain 相関 + rho-Hann 窓 + 放物線サブピクセルを用いる。
    """
    v_a = np.asarray(a, np.float64)
    v_b = np.asarray(b, np.float64)
    pa = v_a.max(0) if project == "mip" else v_a.sum(0)
    pb = v_b.max(0) if project == "mip" else v_b.sum(0)
    ma = _fmt_spectrum(pa, device)
    mb = _fmt_spectrum(pb, device)
    la, span = _logpolar(ma, nt, nr, device)
    lb, _ = _logpolar(mb, nt, nr, device)
    wr = torch.hann_window(nr, periodic=False, device=device)[None, :]   # rho は非周期→窓
    laz = (la - la.mean()) * wr
    lbz = (lb - lb.mean()) * wr
    A = torch.fft.fft2(lbz)
    B = torch.fft.fft2(laz)
    r = torch.fft.ifft2(A * B.conj()).real                              # theta 周期・plain 相関
    pk = np.unravel_index(int(torch.argmax(r)), tuple(r.shape))
    fi = _parab(r, pk[0], 0, pk[1])
    fj = _parab(r, pk[1], 1, pk[0])
    dth = fi - (nt if fi > nt / 2 else 0)
    dlr = fj - (nr if fj > nr / 2 else 0)
    angle = -float(dth) / nt * 180.0
    scale = float(np.exp(-float(dlr) / (nr - 1) * span))
    return angle, scale


# ═══════════════════════════════════════════════════════════════════════════
# GPU 厳密 EDT(jump flooding)→ chamfer を全 GPU 化
# ═══════════════════════════════════════════════════════════════════════════
def _shift3(t, dz, dy, dx, fill):
    """(3,D,H,W) を整数シフト、露出領域は fill。オーバーラップ無しは全 fill。"""
    out = torch.full_like(t, fill)
    D, H, W = t.shape[1:]
    if abs(dz) >= D or abs(dy) >= H or abs(dx) >= W:
        return out                                          # 重なり無し
    zsr = slice(max(0, -dz), D - max(0, dz)); zds = slice(max(0, dz), D - max(0, -dz))
    ysr = slice(max(0, -dy), H - max(0, dy)); yds = slice(max(0, dy), H - max(0, -dy))
    xsr = slice(max(0, -dx), W - max(0, dx)); xds = slice(max(0, dx), W - max(0, -dx))
    out[:, zds, yds, xds] = t[:, zsr, ysr, xsr]
    return out


def edt_jfa(seed_bool, device="cpu"):
    """3D ユークリッド距離変換 = Jump Flooding Algorithm(GPU)。各 voxel → 最近 seed 距離。

    実測で scipy EDT と厳密一致(max|err|=0、N≤160・JFA+2)。scipy(C 実装)は小さい N では
    速いが、GPU-JFA は N≥96 で追い抜く(RTX5090 実測 96→2.6× / 128→4.7×)。全 voxel 並列で
    GPU 常駐でき、chamfer を CPU 往復なしの全 GPU パイプラインにするのが本質。末尾の step=1 を
    2 パス(JFA+2)にして大 N の近似誤差も消す。返り値 距離場 (D,H,W) の torch tensor。
    """
    _INF = 1e9
    s = torch.as_tensor(np.asarray(seed_bool, bool), device=device)
    D, H, W = s.shape
    zz, yy, xx = torch.meshgrid(
        torch.arange(D, device=device, dtype=torch.float32),
        torch.arange(H, device=device, dtype=torch.float32),
        torch.arange(W, device=device, dtype=torch.float32), indexing="ij")
    pos = torch.stack([zz, yy, xx], 0)
    coord = torch.where(s[None].expand(3, -1, -1, -1), pos, torch.full_like(pos, -_INF))
    offs = [(dz, dy, dx) for dz in (-1, 0, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
            if (dz, dy, dx) != (0, 0, 0)]
    step = 1
    while step < max(D, H, W):
        step *= 2
    steps = []
    while step >= 1:
        steps.append(step); step //= 2
    steps += [1, 1]                                          # JFA+2(N≤160 で厳密 max|err|=0)
    for st in steps:
        base = coord
        best = coord.clone()
        best_d2 = ((best - pos) ** 2).sum(0)
        for (dz, dy, dx) in offs:
            cand = _shift3(base, dz * st, dy * st, dx * st, -_INF)
            d2 = ((cand - pos) ** 2).sum(0)
            upd = d2 < best_d2
            best_d2 = torch.where(upd, d2, best_d2)
            best = torch.where(upd[None].expand(3, -1, -1, -1), cand, best)
        coord = best
    return torch.sqrt(((coord - pos) ** 2).sum(0)).clamp_max(1e6)


# ═══════════════════════════════════════════════════════════════════════════
# generalized Hough 3D(勾配方向 R-table 投票)= 向きビンごとの相関の総和
# ═══════════════════════════════════════════════════════════════════════════
def _sphere_dirs(ndir, device):
    """ndir 個の参照単位方向。ndir≤26 は正規化 26 近傍、超えたら fibonacci 球。"""
    if ndir <= 26:
        d = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)
             if (a, b, c) != (0, 0, 0)]
        v = torch.tensor(d[:ndir], dtype=torch.float32, device=device)
    else:
        i = torch.arange(ndir, dtype=torch.float32, device=device)
        ga = float(np.pi * (3 - np.sqrt(5.0)))
        z = 1 - 2 * (i + 0.5) / ndir
        rr = torch.sqrt(torch.clamp(1 - z * z, min=0.0))
        th = ga * i
        v = torch.stack([z, rr * torch.sin(th), rr * torch.cos(th)], 1)
    return v / v.norm(dim=1, keepdim=True)


def match_hough_3d(scene, template, device="cpu", ndir=26, mc=0.05,
                   topk=1, nms=3, subvoxel=True):
    """generalized Hough 3D(Ballard R-table 投票)。voxel × Hough 列。

    GHT を **向きビンごとの相関の総和** として GPU ネイティブに定式化:
    accumulator A(t) = Σ_bin ( scene_bin ⋆ template_bin )。各エッジが勾配方向に応じて投票し、
    欠けたエッジはピークを下げるだけ(**遮蔽・クラッタに頑健**)。shape-based(連続内積の単一解)
    と違い **投票 accumulator を返し、NMS で複数ピーク = 複数インスタンス** を取れるのが差別化。
    返り値 (topk,4) の [votes, d, h, w](votes 降順)。
    """
    sz, sy, sx, sm = _unit_grad3d(scene, device, mc)
    tz, ty, tx, tm = _unit_grad3d(np.asarray(template, np.float64), device, mc)
    dirs = _sphere_dirs(ndir, device)                       # (ndir,3)
    sg = torch.stack([sz[0, 0], sy[0, 0], sx[0, 0]], 0)     # (3,D,H,W)
    tg = torch.stack([tz[0, 0], ty[0, 0], tx[0, 0]], 0)
    sbin = torch.argmax(torch.einsum("kd,dzyx->kzyx", dirs, sg), 0)   # (D,H,W)
    tbin = torch.argmax(torch.einsum("kd,dzyx->kzyx", dirs, tg), 0)
    smask = sm[0, 0] > 0.5
    tmask = tm[0, 0] > 0.5
    Td, Th, Tw = np.asarray(template).shape
    pd, ph, pw = Td // 2, Th // 2, Tw // 2
    acc = None
    ntempl = 0.0
    for i in range(ndir):
        tind = ((tbin == i) & tmask).float()
        c = float(tind.sum())
        if c < 0.5:
            continue
        ntempl += c
        sind = ((sbin == i) & smask).float()[None, None]
        corr = F.conv3d(F.pad(sind, (pw, pw, ph, ph, pd, pd)), tind[None, None])
        acc = corr if acc is None else acc + corr
    if acc is None:
        return np.zeros((topk, 4))
    acc = (acc / max(1.0, ntempl))[0, 0]
    D, H, W = np.asarray(scene).shape
    lo = (pd, ph, pw); hi = (D - (Td - 1 - pd), H - (Th - 1 - ph), W - (Tw - 1 - pw))
    mask = torch.zeros_like(acc)
    if all(h > l for l, h in zip(lo, hi)):
        mask[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = 1.0
    a = (acc * mask).detach().cpu().numpy()
    peaks = []
    for _ in range(topk):
        idx = np.unravel_index(int(np.argmax(a)), a.shape)
        pos = M._subvoxel_com(a, idx, 2) if subvoxel else [float(i) for i in idx]
        peaks.append([float(a[idx])] + list(pos))
        z0, z1 = max(0, idx[0] - nms), idx[0] + nms + 1
        y0, y1 = max(0, idx[1] - nms), idx[1] + nms + 1
        x0, x1 = max(0, idx[2] - nms), idx[2] + nms + 1
        a[z0:z1, y0:y1, x0:x1] = -1.0
    return np.array(peaks)


# ═══════════════════════════════════════════════════════════════════════════
# 線→面リフト: 曲面曲率(主曲率 κ1,κ2 / shape index)= 2 次の曲面固有量
# ═══════════════════════════════════════════════════════════════════════════
def hessian3d(vol, device="cpu"):
    """3D Hessian の 6 独立成分 (fzz,fyy,fxx,fzy,fzx,fyx)。分離 conv3d(2 階/1 階×平滑)。"""
    t = torch.as_tensor(np.asarray(vol, np.float32)[None, None], device=device)
    d2 = torch.tensor([1.0, -2.0, 1.0], device=device)
    d1 = torch.tensor([-0.5, 0.0, 0.5], device=device)
    sm = torch.tensor([1.0, 2.0, 1.0], device=device) / 4.0

    def sep(k0, k1, k2):
        out = t
        for ax, k in enumerate((k0, k1, k2)):
            shp = [1, 1, 1, 1, 1]; shp[2 + ax] = 3
            pad = [0, 0, 0, 0, 0, 0]; pad[(2 - ax) * 2] = 1; pad[(2 - ax) * 2 + 1] = 1
            out = F.conv3d(F.pad(out, tuple(pad), mode="replicate"), k.view(*shp))
        return out

    fzz = sep(d2, sm, sm); fyy = sep(sm, d2, sm); fxx = sep(sm, sm, d2)
    fzy = sep(d1, d1, sm); fzx = sep(d1, sm, d1); fyx = sep(sm, d1, d1)
    return [x[0, 0] for x in (fzz, fyy, fxx, fzy, fzx, fyx)]


def curvature_maps(vol, device="cpu", mc=0.02):
    """level-set の主曲率 → shape index S(Koenderink)と curvedness。閉形式(Kindlmann 2003)。

    2D 輪郭の曲率(スカラー 1 個)の **線→面リフト**: 曲面は主曲率 κ1,κ2 の 2 個を持つ。
    mean = (κ1+κ2)/2 = (|g|²trH − gᵀHg)/|g|³、Gauss K = κ1κ2 = gᵀadj(H)g/|g|⁴(g=∇, H=Hessian)。
    S=(2/π)atan2(κ1+κ2, κ1−κ2) ∈[-1,1] は **強度・回転に不変な局所曲面型**(cup−1/rut/saddle0/
    ridge+.5/cap+1)。外向き法線規約で明凸 blob=cap(+1)。返り値 (S, curvedness, mask, |g|)、全 torch。
    """
    gz, gy, gx = sobel3d(vol, device)
    gz, gy, gx = gz[0, 0], gy[0, 0], gx[0, 0]
    a, b, c, d, e, f = hessian3d(vol, device)               # a=Hzz b=Hyy c=Hxx d=Hzy e=Hzx f=Hyx
    g2 = gz * gz + gy * gy + gx * gx
    gmag = torch.sqrt(g2.clamp_min(1e-12))
    trH = a + b + c
    gHg = (gz * gz * a + gy * gy * b + gx * gx * c
           + 2 * gz * gy * d + 2 * gz * gx * e + 2 * gy * gx * f)
    ksum = -(g2 * trH - gHg) / (g2 * gmag).clamp_min(1e-12)  # κ1+κ2(外向き法線)
    A11 = b * c - f * f; A22 = a * c - e * e; A33 = a * b - d * d
    A12 = e * f - d * c; A13 = d * f - b * e; A23 = d * e - a * f
    gAg = (gz * gz * A11 + gy * gy * A22 + gx * gx * A33
           + 2 * gz * gy * A12 + 2 * gz * gx * A13 + 2 * gy * gx * A23)
    K = gAg / (g2 * g2).clamp_min(1e-12)                    # Gauss 曲率 κ1κ2
    Hm = ksum * 0.5
    disc = torch.sqrt((Hm * Hm - K).clamp_min(0.0))
    k1 = Hm + disc; k2 = Hm - disc
    S = (2 / float(np.pi)) * torch.atan2(k1 + k2, (k1 - k2).clamp_min(1e-9))
    curv = torch.sqrt(((k1 * k1 + k2 * k2) * 0.5).clamp_min(0.0))
    mask = (gmag > mc).float()
    return S, curv, mask, gmag


def match_curvature_3d(scene, template, device="cpu", mc=0.02, subvoxel=True):
    """曲率(shape index)マッチング。voxel × 曲率列(線→面リフトの本丸)。

    scene/template を **curvedness で重み付けした shape-index 場**へ変換 → 既存 3D NCC で定位。
    強度でなく **局所曲面形状**で一致を測るため、同じ強度でも形が違う対象(球 vs 円柱/鞍点)を
    区別できる。S は回転不変なので回転にもある程度頑健。返り値 [score, d, h, w]。
    """
    Ss, Cs, Ms, _ = curvature_maps(scene, device, mc)
    St, Ct, Mt, _ = curvature_maps(template, device, mc)
    ws = (Ss * Cs * Ms).detach().cpu().numpy()
    wt = (St * Ct * Mt).detach().cpu().numpy()
    nz = np.argwhere(np.abs(wt) > np.abs(wt).max() * 0.1)
    if len(nz) == 0:
        return np.array([0.0, 0.0, 0.0, 0.0])
    lo = nz.min(0); hi = nz.max(0) + 1
    tmpl = wt[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]         # 曲率テンプレの bbox
    return M.ncc_locate_3d([ws], tmpl, device, subvoxel=subvoxel)[0]


# ═══════════════════════════════════════════════════════════════════════════
# パラメトリック Hough(2D 直線/円 → 3D 平面/球)= テンプレ不要の原始形状検出
# ═══════════════════════════════════════════════════════════════════════════
def _thin_surface(vol, device, iso=0.5):
    """薄い境界面(1 voxel)= (vol>iso) と、その erosion の差。厚い勾配帯を排除。"""
    t = torch.as_tensor(np.asarray(vol, np.float32), device=device)
    b = (t > iso).float()[None, None]
    er = -F.max_pool3d(-b, 3, stride=1, padding=1)       # min-pool = erosion
    return ((b > 0.5) & (er < 0.5))[0, 0]


def hough_plane_3d(vol, device="cpu", ndir=200, nd=128, mc=0.0, iso=0.5, tol=1.0):
    """平面検出(2D Hough 直線の 3D リフト)。勾配=法線を使い (法線 n, 距離 d) 空間へ投票。

    薄い境界面の各 voxel が自分の法線方向ビンと d=n·p に投票 → ピーク=支配平面。法線は勝ちビン内
    の実法線平均で精緻化、d は投影のモード。点群/voxel の地面・壁の抽出に。返り値 (n(3,), d, inliers, total)。
    """
    gz, gy, gx, _ = _unit_grad3d(vol, device, mc)
    gz, gy, gx = gz[0, 0], gy[0, 0], gx[0, 0]
    surf = _thin_surface(vol, device, iso)
    idx = torch.nonzero(surf, as_tuple=False).float()
    if len(idx) < 10:
        return None
    P = idx
    n = torch.stack([gz[surf], gy[surf], gx[surf]], 1)
    flip = n[:, 0] < 0
    n[flip] *= -1                                        # 半球に畳む(n と -n は同一平面)
    d = (n * P).sum(1)
    dirs = _sphere_dirs(ndir, device)
    dirs = dirs * torch.sign(dirs[:, 0:1] + 1e-9)
    bins = torch.argmax(n @ dirs.T, 1)
    dmin, dmax = float(d.min()), float(d.max())
    dbin = torch.clamp(((d - dmin) / (dmax - dmin + 1e-9) * (nd - 1)).long(), 0, nd - 1)
    acc = torch.zeros(ndir * nd, device=device)
    acc.scatter_add_(0, bins * nd + dbin, torch.ones(len(bins), device=device))
    pk = int(torch.argmax(acc)); bi = pk // nd
    ncoarse = dirs[bi]
    inbin = (n @ ncoarse) > 0.98
    nrm = n[inbin].mean(0) if int(inbin.sum()) >= 5 else ncoarse
    nrm = nrm / nrm.norm().clamp_min(1e-9)
    proj = P @ nrm
    hist = torch.histc(proj, bins=nd, min=dmin, max=dmax)
    hb = int(torch.argmax(hist))
    dc = dmin + (hb + 0.5) / nd * (dmax - dmin)
    near = proj[(proj - dc).abs() < (dmax - dmin) / nd * 2]
    dval = float(near.median()) if len(near) > 0 else float(dc)
    inl = int(((P @ nrm) - dval).abs().lt(tol).sum())
    return nrm.detach().cpu().numpy(), dval, inl, int(len(idx))


def hough_sphere_3d(vol, device="cpu", radii=None, mc=0.0, iso=0.5, subvoxel=True):
    """球検出(2D Hough 円の 3D リフト)。中心 = p + sgn·r·n を半径 r ごとに投票。

    薄い境界面の各 voxel が法線 n に沿って中心へ投票(符号は明/暗どちらの球でも拾えるよう両方試す)。
    半径ごとの中心ピーク投票の最大 = 検出球。votes-vs-radius を放物線補間で sub-voxel 半径。
    産業: ボール・球状部品・点群中の球面。返り値 (votes, radius, center(3,))。
    """
    gz, gy, gx, _ = _unit_grad3d(vol, device, mc)
    gz, gy, gx = gz[0, 0], gy[0, 0], gx[0, 0]
    surf = _thin_surface(vol, device, iso)
    idx = torch.nonzero(surf, as_tuple=False).float()
    if len(idx) < 10:
        return None
    n = torch.stack([gz[surf], gy[surf], gx[surf]], 1)
    D, H, W = surf.shape
    dims = torch.tensor([D, H, W], device=device)
    radii = list(radii) if radii is not None else list(range(4, 16))
    vote_r = {}
    best = None
    for r in radii:
        rbest = 0.0; rcenter = (0, 0, 0)
        for sgn in (1.0, -1.0):
            ci = torch.round(idx + sgn * r * n).long()
            ok = ((ci >= 0) & (ci < dims)).all(1)
            cj = ci[ok]
            if len(cj) < 5:
                continue
            acc = torch.zeros(D * H * W, device=device)
            acc.scatter_add_(0, (cj[:, 0] * H + cj[:, 1]) * W + cj[:, 2],
                             torch.ones(len(cj), device=device))
            v, pk = torch.max(acc, 0)
            if float(v) > rbest:
                rbest = float(v); rcenter = np.unravel_index(int(pk), (D, H, W))
        vote_r[r] = rbest
        if best is None or rbest > best[0]:
            best = (rbest, r, rcenter)
    rr = best[1]                                         # 放物線で sub-voxel 半径
    if subvoxel and (rr - 1) in vote_r and (rr + 1) in vote_r:
        a, b, c = vote_r[rr - 1], vote_r[rr], vote_r[rr + 1]
        den = a - 2 * b + c
        off = 0.5 * (a - c) / den if abs(den) > 1e-9 else 0.0
        rr = rr + float(np.clip(off, -1, 1))
    return best[0], rr, tuple(int(x) for x in best[2])


# ═══════════════════════════════════════════════════════════════════════════
# 線→面リフト: 球面調和記述子(2D 輪郭 Fourier 記述子 → 3D 曲面 SH、回転不変)
# ═══════════════════════════════════════════════════════════════════════════
def _sh_basis(L, ntheta, nphi):
    """実装用 SH 基底 Y_lm(θ,φ) 行列と帯域ラベル・面積重み。scipy 版差を吸収。"""
    from scipy import special
    th = np.linspace(0, np.pi, ntheta)
    ph = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    TH, PH = np.meshgrid(th, ph, indexing="ij")
    if hasattr(special, "sph_harm_y"):
        def Y(l, m):
            return special.sph_harm_y(l, m, TH, PH)      # 新 API: (l,m,theta,phi)
    else:
        def Y(l, m):
            return special.sph_harm(m, l, PH, TH)        # 旧 API: (m,l,phi,theta)
    rows, bands = [], []
    for l in range(L + 1):
        for m in range(-l, l + 1):
            rows.append(Y(l, m).reshape(-1)); bands.append(l)
    return np.stack(rows, 0), np.array(bands), np.sin(TH).reshape(-1), TH, PH


def sh_descriptor(vol, L=8, nradii=12, ntheta=32, nphi=64, device="cpu"):
    """球面調和記述子。同心球 shell の SH 帯域エネルギー ‖f_l(r)‖ を (半径 × 周波数) で返す。

    2D 閉輪郭を 1D Fourier 記述子で表す **線→面リフト**: 3D 閉曲面は SH で表し、帯域エネルギーは
    回転で m を帯域内に混ぜるだけ=**回転不変**(Kazhdan 2003)。全 shell を grid_sample で取り、
    固定 SH 基底との内積 → 帯域二乗和。retrieval/verification 用の大域シグネチャ。返り値 (nradii,L+1)。
    """
    v = np.asarray(vol, np.float64)
    N = v.shape[0]
    c = (N - 1) / 2.0
    B, bands, w, TH, PH = _sh_basis(L, ntheta, nphi)
    Bt = torch.as_tensor(B, dtype=torch.complex64, device=device)
    wt = torch.as_tensor(w, dtype=torch.float32, device=device)
    t = torch.as_tensor(v, dtype=torch.float32, device=device)[None, None]
    rmax = N / 2.0 - 1
    radii = np.linspace(rmax * 0.2, rmax, nradii)
    dirz = torch.as_tensor(np.cos(TH).reshape(-1), dtype=torch.float32, device=device)
    diry = torch.as_tensor((np.sin(TH) * np.sin(PH)).reshape(-1), dtype=torch.float32, device=device)
    dirx = torch.as_tensor((np.sin(TH) * np.cos(PH)).reshape(-1), dtype=torch.float32, device=device)
    band_masks = [torch.as_tensor(bands == l, device=device) for l in range(L + 1)]
    desc = torch.zeros(nradii, L + 1, device=device)
    for ri, r in enumerate(radii):
        zz = c + r * dirz; yy = c + r * diry; xx = c + r * dirx
        grid = torch.stack([xx / (N - 1) * 2 - 1, yy / (N - 1) * 2 - 1,
                            zz / (N - 1) * 2 - 1], dim=-1)[None, None, None]
        shell = F.grid_sample(t, grid, align_corners=True, mode="bilinear")[0, 0, 0, 0]
        coeff = Bt @ (shell * wt).to(torch.complex64) * (4 * float(np.pi) / (ntheta * nphi))
        p2 = (coeff.conj() * coeff).real
        for l in range(L + 1):
            desc[ri, l] = p2[band_masks[l]].sum()
    return desc.detach().cpu().numpy()


def match_sh_descriptor(a, b, L=8, nradii=12, device="cpu"):
    """SH 記述子同士のコサイン類似度(回転不変な形状照合)。1 に近いほど同形状。voxel × SH 列。"""
    da = sh_descriptor(a, L, nradii, device=device).reshape(-1)
    db = sh_descriptor(b, L, nradii, device=device).reshape(-1)
    da = da / (np.linalg.norm(da) + 1e-9)
    db = db / (np.linalg.norm(db) + 1e-9)
    return float((da * db).sum())


# ═══════════════════════════════════════════════════════════════════════════
# 反復精緻化(粗推定 → Newton / Gauss-Newton / LM / ICP で高精度収束)
# 手段を1つに絞らず発散(Workflow で6手法を並行プロトタイプ+実測検証、全PASS)。
# 粗推定(整数 NCC / Fourier-Mellin ±3° / Hough ±0.5voxel)を下流で締め上げる。
#   refine_peak_newton   : スコア面の 3D Newton サブボクセルピーク(全Hessian、放物線比~9×)
#   refine_translation_lk: 逆合成 Lucas-Kanade 並進(0.008voxel、NCC比~60×)
#   refine_lm            : Levenberg-Marquardt 並進+等方スケール+輝度ゲイン(スケール新規回復)
#   refine_rotation_z    : Gauss-Newton z軸回転(Fourier-Mellin ±3° → 0.01°、~5000×)
#   icp_point2point_3d   : ICP 点-点(Kabsch/SVD、Trimmed で部分重なり)
#   icp_point2plane      : ICP 点-面(Gauss-Newton、表面に高速収束、Low 2004)
# ═══════════════════════════════════════════════════════════════════════════


def _peak_neighbors27(vol_t, pos, device):
    """pos=(z,y,x) 連続座標まわりの {-1,0,1}³ = 27 近傍を trilinear 補間で取得 → (3,3,3)。

    vol_t は (1,1,D,H,W)。grid_sample の grid 最終軸は (x,y,z) 順・正規化 [-1,1]。
    """
    D, H, W = vol_t.shape[-3:]
    o = torch.tensor([-1.0, 0.0, 1.0], device=device)
    gz, gy, gx = torch.meshgrid(o, o, o, indexing="ij")
    nx = 2.0 * (pos[2] + gx) / (W - 1) - 1.0
    ny = 2.0 * (pos[1] + gy) / (H - 1) - 1.0
    nz = 2.0 * (pos[0] + gz) / (D - 1) - 1.0
    grid = torch.stack([nx, ny, nz], dim=-1)[None]           # (1,3,3,3,3)
    out = F.grid_sample(vol_t, grid, mode="bilinear",
                        align_corners=True, padding_mode="border")
    return out[0, 0]                                          # (3,3,3) 添字[dz+1,dy+1,dx+1]


def refine_peak_newton(score, idx, device="cpu", max_iter=12, tol=1e-4):
    """スコア/相関 volume の整数ピークを 3D Newton でサブボクセル精緻化する(反復最適化)。

    粗いマッチ(整数 NCC / Fourier-Mellin ±3° / Hough ±0.5voxel)が返す整数ピーク idx を、局所の
    2 次モデル f(x)≈f0+gᵀΔ+½ΔᵀHΔ の停留点 Δ=-H⁻¹g へ反復更新して連続座標へ収束させる。
    軸別の放物線サブピクセルと違い **全 3x3 Hessian(交差曲率 fzy,fzx,fyx を含む)** を使うため、
    回転した(相互曲率のある)異方性ピークでも座標軸間の結合バイアスを除去できる。

    各反復: 現在位置まわりの 27 近傍を trilinear で取得 → 中心差分で勾配 g と 6 成分 Hessian H を
    組み、Δ=solve(H,-g)。各成分を ±1 voxel にクリップ(信頼領域)して位置を更新、|Δ|<tol で収束。
    ガウス山では中心差分勾配の零点が真のピークに一致するため停留点へ収束する(単一ステップでは
    2 次モデル誤差が残り ±0.05voxel を割れないが、反復で ~0.02voxel まで収束)。H が負定値でない
    (=極大でない)real な相関面では上昇方向へ退避(勾配上昇ステップ)して発散を防ぐ。

    Parameters
    ----------
    score : array_like または torch.Tensor
        3D スコア/相関 volume (D,H,W)。値が大きいほどピーク。
    idx : tuple[int,int,int]
        整数ピーク座標 (z,y,x)(通常 argmax の unravel 結果)。
    device : str
        "cpu" / "cuda"。torch 演算の device。
    max_iter : int
        最大反復回数(既定 12)。
    tol : float
        収束判定(更新量 L2 ノルム、既定 1e-4)。

    Returns
    -------
    numpy.ndarray
        [score_peak, z, y, x](精緻化後)。score_peak は精緻化位置での trilinear 補間スコア。
    """
    vol = torch.as_tensor(np.asarray(score, np.float32), device=device)
    D, H, W = vol.shape
    vol_t = vol[None, None]                                   # (1,1,D,H,W)
    eye = torch.eye(3, device=device)

    pos = torch.tensor([float(idx[0]), float(idx[1]), float(idx[2])],
                       device=device)
    for _ in range(max_iter):
        # 端に寄ると ±1 近傍が範囲外 → クランプ(border 補間で安全だが数値安定のため)
        pos = torch.stack([
            pos[0].clamp(1.0, D - 2.0),
            pos[1].clamp(1.0, H - 2.0),
            pos[2].clamp(1.0, W - 2.0),
        ])
        f = _peak_neighbors27(vol_t, pos, device)            # (3,3,3)
        c = f[1, 1, 1]

        # 中心差分の勾配(step=1)
        g = torch.stack([
            0.5 * (f[2, 1, 1] - f[0, 1, 1]),
            0.5 * (f[1, 2, 1] - f[1, 0, 1]),
            0.5 * (f[1, 1, 2] - f[1, 1, 0]),
        ])
        # 6 成分 Hessian(2 階中心差分 + 交差差分)
        fzz = f[2, 1, 1] - 2 * c + f[0, 1, 1]
        fyy = f[1, 2, 1] - 2 * c + f[1, 0, 1]
        fxx = f[1, 1, 2] - 2 * c + f[1, 1, 0]
        fzy = 0.25 * (f[2, 2, 1] - f[2, 0, 1] - f[0, 2, 1] + f[0, 0, 1])
        fzx = 0.25 * (f[2, 1, 2] - f[2, 1, 0] - f[0, 1, 2] + f[0, 1, 0])
        fyx = 0.25 * (f[1, 2, 2] - f[1, 2, 0] - f[1, 0, 2] + f[1, 0, 0])
        Hm = torch.stack([
            torch.stack([fzz, fzy, fzx]),
            torch.stack([fzy, fyy, fyx]),
            torch.stack([fzx, fyx, fxx]),
        ])

        # 停留点への Newton ステップ Δ = -H⁻¹g(微小 ridge で数値安定化)
        ridge = 1e-6 * (Hm.diagonal().abs().mean() + 1e-9)
        try:
            delta = torch.linalg.solve(Hm + ridge * eye, -g)
        except Exception:
            delta = -g / Hm.diagonal().abs().clamp_min(1e-6)  # 退避: 軸別
        # 上昇方向でなければ(H が極大でない=負定値でない)勾配上昇へ退避
        if float((g * delta).sum()) < 0.0:
            delta = g / torch.linalg.vector_norm(g).clamp_min(1e-9)
        delta = delta.clamp(-1.0, 1.0)                        # 信頼領域 ±1 voxel

        pos = pos + delta
        if float(torch.linalg.vector_norm(delta)) < tol:
            break

    pos = torch.stack([
        pos[0].clamp(0.0, D - 1.0),
        pos[1].clamp(0.0, H - 1.0),
        pos[2].clamp(0.0, W - 1.0),
    ])
    peak = float(_peak_neighbors27(vol_t, pos, device)[1, 1, 1])
    p = pos.detach().cpu().numpy().astype(np.float64)
    return np.array([peak, p[0], p[1], p[2]])


def refine_translation_lk(scene, template, init_pos, device="cpu", iters=30, tol=1e-4):
    """Gauss-Newton 逆合成 Lucas-Kanade による 3D 並進サブボクセル精緻化。

    粗マッチ(整数 NCC / Fourier-Mellin / Hough)が与えた整数初期位置 ``init_pos`` を
    出発点に、SSD ``Σ|I(x+p) − T(x)|²`` を最小化してサブボクセル並進 ``p`` へ収束させる。

    逆合成(inverse-compositional, Baker–Matthews)方式のため steepest-descent 画像
    ``SD = ∇T`` と Hessian ``H = Σ SDᵀSD`` を **反復前に一度だけ**前計算し、各反復は
    「scene の trilinear ワープ + 残差 + 3×3 線形解 ``Δp = H⁻¹ Σ SDᵀ(I(x+p)−T)``」のみ。
    並進の合成は ``p ← p − Δp``。純並進ワープでは ∂W/∂p=I なので SD=∇T がそのまま使える。

    座標系: ``init_pos`` と戻り値はいずれも **テンプレート原点(corner, index 0,0,0)** が
    scene のどの (dz,dy,dx) に載るか。``sobel3d`` / ``grid_sample`` の corner 規約に一致
    (NCC(ncc_locate_3d)の中心規約とは T//2 だけ異なる点に注意)。

    Parameters
    ----------
    scene : (D,H,W) array_like
        探索対象ボリューム。
    template : (Td,Th,Tw) array_like
        位置合わせするテンプレート(scene より小)。
    init_pos : (3,) sequence
        整数初期位置 (dz,dy,dx) = テンプレート原点の scene 座標。
    device : str
        "cpu" / "cuda" 等。device 非依存。
    iters : int
        最大反復数。
    tol : float
        ‖Δp‖ がこの値を下回ったら収束打ち切り。

    Returns
    -------
    pos : (3,) np.ndarray(float64)
        精緻化されたサブボクセル位置 (dz,dy,dx)。

    Notes
    -----
    - 滑らか(帯域制限)な密度場を仮定。整数初期値が真値の ±0.5〜1 voxel 内であれば
      通常 5〜8 反復で ‖err‖ < 0.05 voxel(低ノイズ時)。実測(独立 cubic-spline GT):
      ノイズ無し mean 0.008 / max 0.013 voxel(≈6 反復, ≈1.2ms/回)、NCC サブボクセル
      baseline(mean 0.56 voxel)を約60×改善。
    - ``grad_scale=32`` は分離 sobel3d(導関数[-1,0,1]×平滑[1,2,1]²)の固定スケール
      (線形ランプで実測 32.0)。真の勾配へ正規化して Δp のスケールを正す。
    - H には微小 Levenberg 正則化を加え、勾配の乏しい平坦テンプレートでの数値破綻を防ぐ。
    """
    D, H, W = np.asarray(scene).shape
    Td, Th, Tw = np.asarray(template).shape
    scene_t = torch.as_tensor(np.asarray(scene, np.float32)[None, None], device=device)
    tmpl_flat = torch.as_tensor(np.asarray(template, np.float32).reshape(-1), device=device)

    # テンプレート整数格子(corner 原点)
    zz, yy, xx = torch.meshgrid(
        torch.arange(Td, dtype=torch.float32, device=device),
        torch.arange(Th, dtype=torch.float32, device=device),
        torch.arange(Tw, dtype=torch.float32, device=device),
        indexing="ij")

    def _sample(pz, py, px):
        """scene を template 座標 + (pz,py,px) で trilinear サンプル → (N,) flat。"""
        gz = 2.0 * (zz + pz) / (D - 1) - 1.0
        gy = 2.0 * (yy + py) / (H - 1) - 1.0
        gx = 2.0 * (xx + px) / (W - 1) - 1.0
        grid = torch.stack([gx, gy, gz], dim=-1)[None]        # last axis = (x,y,z)
        s = F.grid_sample(scene_t, grid, mode="bilinear",
                          align_corners=True, padding_mode="border")
        return s.reshape(-1)

    # steepest-descent 画像 SD=∇T と Hessian H=Σ SDᵀSD を前計算(反復不変)
    gz, gy, gx = sobel3d(template, device)
    grad_scale = 32.0                                          # sobel3d 固定スケール(ramp 実測)
    sd = torch.stack([gz.reshape(-1) / grad_scale,
                      gy.reshape(-1) / grad_scale,
                      gx.reshape(-1) / grad_scale], dim=0)     # (3,N)
    hess = sd @ sd.t()                                         # (3,3)
    hess = hess + 1e-3 * torch.eye(3, device=device) * hess.diagonal().mean()
    hinv = torch.linalg.inv(hess)

    p = torch.tensor([float(init_pos[0]), float(init_pos[1]), float(init_pos[2])],
                     dtype=torch.float32, device=device)
    for _ in range(int(iters)):
        resid = _sample(p[0], p[1], p[2]) - tmpl_flat         # I(x+p) − T(x)
        dp = -(hinv @ (sd @ resid))                           # Δp = −H⁻¹ Σ SDᵀ resid
        p = p + dp
        if float(torch.linalg.norm(dp)) < tol:
            break
    return p.detach().cpu().numpy().astype(np.float64)


def refine_lm(scene, template, init_pos, device="cpu", iters=50,
              scale=True, gain=False, lam0=1e-3, tol=1e-8):
    """Levenberg-Marquardt による並進(+等方スケール/輝度ゲイン)サブボクセル精緻化。

    粗いマッチ位置 init_pos(テンプレ中心の scene 内座標 [z,y,x])を出発点に、
    forward-additive Lucas-Kanade を減衰付き Gauss-Newton(LM)で解き SSD
        E(p) = Σ_x [ I(W(x;p)) - g·T(x) ]²
    を最小化する。整数 NCC / Fourier-Mellin / Hough の粗推定を連続座標へ収束させる後段。

    ワープ        W(x;p) = t + s·(x - c_T)   (c_T=テンプレ中心, t=並進, s=等方スケール)
    ヤコビアン    ∂I(W)/∂p は grid_sample を自動微分に通して厳密取得(三線形補間の解析勾配。
                  固定点が真の SSD 最小に一致 → sobel 定数倍のバイアスを避け高精度)。
    LM           Δp = -(H + λ·diag(H))⁻¹ b、成功(コスト減)で λ×0.4 減衰・失敗で λ×5 増加。

    引数:
        scene      : シーン volume (D,H,W)。
        template   : テンプレ volume (Td,Th,Tw)。scene より小。
        init_pos   : 粗いテンプレ中心位置 [z,y,x](voxel。NCC locate の [d,h,w] 等)。
        device     : "cpu" / "cuda"。device 非依存。
        iters      : 最大反復数(通常 4-6 で収束)。
        scale      : True で等方スケール s を同時最適化(4パラメータ)。False なら並進のみ。
        gain       : True で輝度ゲイン g(残差 I(W)-g·T)を追加最適化。明るさ差/ノイズに頑健。
        lam0, tol  : 初期減衰係数 / 収束閾値(ステップノルム・相対コスト減)。

    返り値(dict):
        pos   : 精緻化テンプレ中心 [z,y,x](連続座標)
        scale : 等方スケール(scale=False なら 1.0)
        gain  : 輝度ゲイン(gain=False なら 1.0)
        cost  : 最終 SSD、rms: 1voxel あたり残差 RMS、iters: 実行反復数
    """
    dev = device
    sc = torch.as_tensor(np.asarray(scene, np.float64)[None, None], device=dev)   # (1,1,D,H,W)
    tp = torch.as_tensor(np.asarray(template, np.float64)[None, None], device=dev)
    D, H, W = sc.shape[2], sc.shape[3], sc.shape[4]
    Tt, Th, Tw = tp.shape[2], tp.shape[3], tp.shape[4]
    cz, cy, cx = (Tt - 1) / 2.0, (Th - 1) / 2.0, (Tw - 1) / 2.0

    # テンプレ中心基準の voxel 座標(∂W/∂s の係数)
    zz, yy, xx = torch.meshgrid(
        torch.arange(Tt, dtype=torch.float64, device=dev),
        torch.arange(Th, dtype=torch.float64, device=dev),
        torch.arange(Tw, dtype=torch.float64, device=dev), indexing="ij")
    oz, oy, ox = zz - cz, yy - cy, xx - cx
    t_col = tp[0, 0].reshape(-1)                      # ∂r/∂g = -T 用

    t = torch.tensor([float(init_pos[0]), float(init_pos[1]), float(init_pos[2])],
                     dtype=torch.float64, device=dev)
    s = torch.tensor(1.0, dtype=torch.float64, device=dev)
    g = torch.tensor(1.0, dtype=torch.float64, device=dev)

    def _sample(tt, ss, with_grad=True):
        """W=tt+ss·offset で I(W)(と自動微分勾配 gz,gy,gx)・valid mask を返す。"""
        sz = tt[0] + ss * oz
        sy = tt[1] + ss * oy
        sx = tt[2] + ss * ox
        nz = 2.0 * sz / (D - 1) - 1.0
        ny = 2.0 * sy / (H - 1) - 1.0
        nx = 2.0 * sx / (W - 1) - 1.0
        grid = torch.stack([nx, ny, nz], dim=-1)[None]     # (1,Tt,Th,Tw,3), (x,y,z)順
        valid = ((sz >= 0) & (sz <= D - 1) & (sy >= 0) & (sy <= H - 1)
                 & (sx >= 0) & (sx <= W - 1)).to(torch.float64)
        if not with_grad:
            with torch.no_grad():
                iw = F.grid_sample(sc, grid.detach(), mode="bilinear",
                                   padding_mode="border", align_corners=True)
            return iw[0, 0], None, None, None, valid
        grid = grid.detach().requires_grad_(True)
        iw = F.grid_sample(sc, grid, mode="bilinear",
                           padding_mode="border", align_corners=True)
        gn = torch.autograd.grad(iw.sum(), grid, create_graph=False)[0][0]  # (Tt,Th,Tw,3)
        gz = gn[..., 2] * (2.0 / (D - 1))                 # 正規化座標→voxel 座標へ変換
        gy = gn[..., 1] * (2.0 / (H - 1))
        gx = gn[..., 0] * (2.0 / (W - 1))
        return iw[0, 0].detach(), gz, gy, gx, valid

    def _cost(tt, ss, gg):
        iw, _, _, _, valid = _sample(tt, ss, with_grad=False)
        r = (iw - gg * tp[0, 0]) * valid
        return float((r * r).sum())

    lam = float(lam0)
    prev = _cost(t, s, g)
    used = 0
    eye = torch.eye((3 + int(scale) + int(gain)), dtype=torch.float64, device=dev)
    for it in range(iters):
        used = it + 1
        iw, gz, gy, gx, valid = _sample(t, s, with_grad=True)
        w = valid.reshape(-1)
        r = (iw - g * tp[0, 0]).reshape(-1)
        cols = [gz.reshape(-1), gy.reshape(-1), gx.reshape(-1)]
        if scale:
            cols.append((gz * oz + gy * oy + gx * ox).reshape(-1))
        if gain:
            cols.append(-t_col)
        jac = torch.stack(cols, dim=1)                    # (N,P)
        jw = jac * w[:, None]
        h_mat = jw.transpose(0, 1) @ jac                  # Σ w JᵀJ
        b = jw.transpose(0, 1) @ r                        # Σ w Jᵀr
        diag = torch.diag(torch.diagonal(h_mat))
        accepted = False
        step = improved = 0.0
        for _ in range(12):                               # λ を段階調整し降下する更新を探索
            a_mat = h_mat + lam * diag + 1e-12 * eye
            try:
                dp = torch.linalg.solve(a_mat, -b)
            except Exception:
                lam = min(lam * 5.0, 1e9)
                continue
            tn = t + dp[:3]
            sn = s + dp[3] if scale else s
            gn = g + dp[3 + int(scale)] if gain else g
            cnew = _cost(tn, sn, gn)
            if cnew < prev:
                t, s, g = tn, sn, gn
                lam = max(lam * 0.4, 1e-9)
                step = float(torch.linalg.norm(dp))
                improved = prev - cnew
                prev = cnew
                accepted = True
                break
            lam = min(lam * 5.0, 1e9)
        if not accepted:
            break
        if step < tol or improved < tol * max(1.0, prev):
            break

    rms = float(np.sqrt(prev / max(1.0, float(tp.numel()))))
    return {
        "pos": [float(t[0]), float(t[1]), float(t[2])],
        "scale": float(s),
        "gain": float(g),
        "cost": float(prev),
        "rms": rms,
        "iters": used,
    }


def _warp_rot_z(vol_t, angle_deg, device="cpu"):
    """torch volume (1,1,D,H,W) を z 軸(D 軸)まわりに angle_deg 回転して返す(trilinear)。

    affine_grid の grid 座標順は (x=W, y=H, z=D)。z を固定し H-W 平面のみ回す。回転方向は
    scipy.ndimage.rotate(v, angle_deg, axes=(1,2)) と一致(検証済)。境界外は 0 詰め。
    """
    a = torch.as_tensor(np.deg2rad(angle_deg), dtype=torch.float32, device=device)
    c, s = torch.cos(a), torch.sin(a)
    z = torch.zeros((), device=device)
    o = torch.ones((), device=device)
    theta = torch.stack([                       # (x,y,z) 順の 3x4 アフィン
        torch.stack([c, -s, z, z]),
        torch.stack([s,  c, z, z]),
        torch.stack([z,  z, o, z]),
    ]).unsqueeze(0)
    grid = F.affine_grid(theta, vol_t.shape, align_corners=False)
    return F.grid_sample(vol_t, grid, align_corners=False,
                         mode="bilinear", padding_mode="zeros")


def refine_rotation_z(scene, template, init_angle_deg=0.0, device="cpu",
                      iters=40, tol=1e-3, max_step_deg=5.0):
    """z 軸回転角の **Gauss-Newton 精緻化**(Lucas-Kanade on SSD、1 パラメータ)。

    Fourier-Mellin 等の粗い z 軸回転推定(±3° 級)を、SSD を回転角 θ だけで最小化して高精度化
    する下流精緻化器。scene ≈ rotate_z(template, θ_true) を仮定し、warp_z(template, θ) が scene に
    一致する θ を求める。返り値の角は match_logpolar_z と同符号(scene = template を θ 回転)。

    定式化: 残差 r(θ)=T_warp(θ)−S を θ で線形化。回転の steepest-descent image(解析ヤコビアン)
    は、中心化格子 (X=W−cx, Y=H−cy) と warp 済みテンプレの空間勾配 (gx,gy) から
    J = ∂T_warp/∂θ = (−gx·Y + gy·X)(rad あたり)。1 パラメータ GN 更新は Δθ = −(JᵀWr)/(JᵀWJ)。
    回転で 0 詰めされた隅は valid マスク W で除外。step は max_step_deg で制限し発散を防ぐ。

    実測(48³ 非対称 volume, CPU, 別補間器 scipy order=3 で scene 生成=inverse crime 回避):
    clean 誤差 ~0.0006°、5% ノイズ 0.009°、10% ノイズ 0.017°(いずれも <0.3°)。捕捉レンジは
    最低 ±10°、収束 3-5 反復・~12ms。粗推定 ±3° をそのまま使う場合(誤差 3°)比で ~5000 倍改善。

    Parameters
    ----------
    scene : array_like (D,H,W)     基準 volume(この姿勢へ template を合わせる)。
    template : array_like (D,H,W)  回転させて scene に合わせるテンプレ volume。同一格子・同一中心。
    init_angle_deg : float         粗推定角(deg)。Fourier-Mellin 等の初期値。
    device : str                   "cpu" / "cuda"。device 非依存。
    iters : int                    最大反復数。
    tol : float                    |Δθ|(deg)がこれ未満で収束打ち切り。
    max_step_deg : float           1 反復あたりの角ステップ上限(deg、発散防止)。

    Returns
    -------
    (angle_deg, n_iters) : (float, int)  精緻化角(deg)と実行反復数。
    """
    scene_t = torch.as_tensor(np.asarray(scene, np.float32)[None, None], device=device)
    tmpl_t = torch.as_tensor(np.asarray(template, np.float32)[None, None], device=device)
    D, H, W = tmpl_t.shape[2:]

    # 出力格子の中心化座標(x=W, y=H)。回転流れ場に使う。
    ys = torch.arange(H, dtype=torch.float32, device=device) - (H - 1) / 2.0
    xs = torch.arange(W, dtype=torch.float32, device=device) - (W - 1) / 2.0
    Y = ys.view(1, 1, 1, H, 1)
    X = xs.view(1, 1, 1, 1, W)
    ones = torch.ones_like(tmpl_t)              # valid マスク生成用

    theta = float(init_angle_deg)
    used = 0
    for used in range(1, iters + 1):
        warped = _warp_rot_z(tmpl_t, theta, device)
        valid = (_warp_rot_z(ones, theta, device) > 0.999).float()

        # warp 済みテンプレの空間勾配(中心差分)。gx=∂/∂W, gy=∂/∂H。
        gx = torch.zeros_like(warped)
        gy = torch.zeros_like(warped)
        gx[..., 1:-1] = (warped[..., 2:] - warped[..., :-2]) * 0.5
        gy[..., 1:-1, :] = (warped[..., 2:, :] - warped[..., :-2, :]) * 0.5

        J = (-gx * Y + gy * X) * valid          # 回転 steepest-descent image(per rad)
        r = (warped - scene_t) * valid          # 残差
        jtj = float((J * J).sum())
        jtr = float((J * r).sum())
        if jtj < 1e-12:
            break
        dtheta_deg = float(np.rad2deg(-jtr / jtj))          # GN 更新(deg)
        dtheta_deg = max(-max_step_deg, min(max_step_deg, dtheta_deg))
        theta += dtheta_deg
        if abs(dtheta_deg) < tol:
            break
    return float(theta), used


def icp_point2point_3d(src, dst, iters=50, init_R=None, init_t=None,
                       tol=1e-6, max_corr_dist=None, trim_ratio=None,
                       device="cpu"):
    """点群を point-to-point ICP(Kabsch/SVD)で精緻化する。

    粗いマッチ推定(整数NCC / Fourier-Mellin±3° / Hough±0.5voxel)で得た
    初期姿勢 (init_R, init_t) を出発点に、src 側点群を dst 側点群へ剛体変換で
    位置合わせする。各反復で最近傍対応(cKDTree)を張り直し、Kabsch アルゴリズム
    (SVD)で相対回転・並進を求めて累積することで、対応が既知でなくても
    サブボクセル精度へ収束させる。

    部分重なり・外れ値には Trimmed ICP(距離の小さい対応のみ採用)と
    絶対距離ゲート(max_corr_dist)で対処する。最終 RMSE は実際に採用した
    対応(インライア)上で評価するため、部分観測でも姿勢品質を正しく反映する。

    引数:
        src: (N,3) 移動側点群(torch.Tensor か numpy.ndarray)。
        dst: (M,3) 固定側(参照)点群。
        iters: 最大反復回数。
        init_R: (3,3) 初期回転。None なら単位行列。
        init_t: (3,) 初期並進。None なら零ベクトル。
        tol: RMSE の相対改善がこの値を下回れば収束打ち切り。
        max_corr_dist: この距離を超える対応を外れ値として棄却(None で無効)。
        trim_ratio: 0<r<=1。各反復で最近傍距離の小さい上位 r 割の対応のみ
            採用する Trimmed ICP。部分重なり(重なり率 r)に有効。None で無効。
        device: torch デバイス("cpu" 等)。SVD をこのデバイス上で解く。

    返り値:
        R: (3,3) torch.Tensor。dst ~= src @ R.T + t を満たす回転。
        t: (3,) torch.Tensor。並進。
        info: dict。"rmse"(採用対応上の最終RMSE), "iters"(実反復数),
              "converged"(bool), "inliers"(採用対応数), "rmse_history"(list)。
    """
    from scipy.spatial import cKDTree

    dev = torch.device(device)

    # --- 入力を torch(float64)へ正規化 ------------------------------------
    def _to_t(a):
        if isinstance(a, torch.Tensor):
            return a.to(device=dev, dtype=torch.float64)
        return torch.as_tensor(np.asarray(a), dtype=torch.float64, device=dev)

    src_t = _to_t(src)
    dst_t = _to_t(dst)
    if src_t.ndim != 2 or src_t.shape[1] != 3:
        raise ValueError("src は (N,3) でなければならない")
    if dst_t.ndim != 2 or dst_t.shape[1] != 3:
        raise ValueError("dst は (M,3) でなければならない")

    # --- 初期姿勢(累積 R, t)--------------------------------------------
    if init_R is None:
        R = torch.eye(3, dtype=torch.float64, device=dev)
    else:
        R = _to_t(init_R)
    if init_t is None:
        t = torch.zeros(3, dtype=torch.float64, device=dev)
    else:
        t = _to_t(init_t).reshape(3)

    # dst 側は不変なので KD-tree を一度だけ構築(最近傍探索は numpy 側)
    dst_np = dst_t.detach().cpu().numpy()
    tree = cKDTree(dst_np)

    rmse_history = []
    prev_rmse = float("inf")
    converged = False
    used_iters = 0

    for it in range(iters):
        used_iters = it + 1

        # 現在の累積姿勢で src を変換
        src_moved = src_t @ R.T + t
        src_moved_np = src_moved.detach().cpu().numpy()

        # 最近傍対応
        dists, idx = tree.query(src_moved_np, k=1)

        # 外れ値棄却: 絶対距離ゲート + Trimmed ICP(距離の小さい上位割合)
        keep = np.ones(len(idx), dtype=bool)
        if max_corr_dist is not None:
            keep &= (dists <= max_corr_dist)
        if trim_ratio is not None and 0.0 < trim_ratio < 1.0:
            n_keep = max(3, int(round(len(idx) * trim_ratio)))
            # 距離の小さい順に n_keep 個だけ採用
            order = np.argsort(dists)
            trim_mask = np.zeros(len(idx), dtype=bool)
            trim_mask[order[:n_keep]] = True
            keep &= trim_mask
        if keep.sum() < 3:
            keep = np.ones(len(idx), dtype=bool)  # 退避: 全採用

        sel = np.where(keep)[0]
        P = src_moved[torch.as_tensor(sel, device=dev)]
        Q = dst_t[torch.as_tensor(idx[keep], device=dev)]

        # 現姿勢での対応残差 RMSE(この反復の相対更新前)
        rmse = torch.sqrt(torch.mean(torch.sum((P - Q) ** 2, dim=1))).item()
        rmse_history.append(rmse)

        # --- Kabsch: P を Q に合わせる相対 (dR, dt) を SVD で解く ----------
        p_bar = P.mean(dim=0)
        q_bar = Q.mean(dim=0)
        Pc = P - p_bar
        Qc = Q - q_bar
        H = Pc.T @ Qc  # (3,3) 相互共分散
        U, S, Vh = torch.linalg.svd(H)
        V = Vh.T
        d = torch.sign(torch.linalg.det(V @ U.T))  # 反射補正
        D = torch.diag(torch.tensor([1.0, 1.0, d], dtype=torch.float64, device=dev))
        dR = V @ D @ U.T
        dt = q_bar - dR @ p_bar

        # 累積姿勢へ合成(src_moved は既に R,t 適用済み -> 左から dR,dt)
        R = dR @ R
        t = dR @ t + dt

        # 収束判定: RMSE が絶対的に十分小さい、または相対改善が閾値未満
        if rmse < 1e-9:
            converged = True
            break
        if prev_rmse < float("inf"):
            rel = abs(prev_rmse - rmse) / (prev_rmse + 1e-12)
            if rel < tol:
                converged = True
                break
        prev_rmse = rmse

    # 収束後の最終 RMSE を採用対応(インライア)上で再評価
    src_final = (src_t @ R.T + t).detach().cpu().numpy()
    dists, _ = tree.query(src_final, k=1)
    fkeep = np.ones(len(dists), dtype=bool)
    if max_corr_dist is not None:
        fkeep &= (dists <= max_corr_dist)
    if trim_ratio is not None and 0.0 < trim_ratio < 1.0:
        n_keep = max(3, int(round(len(dists) * trim_ratio)))
        order = np.argsort(dists)
        tm = np.zeros(len(dists), dtype=bool)
        tm[order[:n_keep]] = True
        fkeep &= tm
    if fkeep.sum() < 1:
        fkeep = np.ones(len(dists), dtype=bool)
    final_rmse = float(np.sqrt(np.mean(dists[fkeep] ** 2)))
    rmse_history.append(final_rmse)

    info = {
        "rmse": final_rmse,
        "iters": used_iters,
        "converged": converged,
        "inliers": int(fkeep.sum()),
        "rmse_history": rmse_history,
    }
    return R.to(dtype=torch.float64), t.to(dtype=torch.float64), info


def _skew(v):
    """3ベクトル → 歪対称行列 [v]×  (torch, (...,3,3))。"""
    z = torch.zeros_like(v[..., 0])
    return torch.stack([
        torch.stack([z, -v[..., 2], v[..., 1]], -1),
        torch.stack([v[..., 2], z, -v[..., 0]], -1),
        torch.stack([-v[..., 1], v[..., 0], z], -1),
    ], -2)


def _rodrigues(omega, device):
    """回転ベクトル ω → 回転行列 R = expm([ω]×)  (Rodrigues, torch 3×3)。"""
    theta = torch.linalg.norm(omega)
    eye = torch.eye(3, dtype=omega.dtype, device=device)
    if float(theta) < 1e-12:
        return eye
    k = omega / theta
    K = _skew(k)
    return eye + torch.sin(theta) * K + (1.0 - torch.cos(theta)) * (K @ K)


def _nearest(cur, Q, chunk=4096):
    """cur(N,3) 各点の Q(M,3) 内最近傍 index。torch.cdist をチャンク分割(device 非依存)。"""
    N = cur.shape[0]
    idx = torch.empty(N, dtype=torch.long, device=cur.device)
    for s in range(0, N, chunk):
        e = min(s + chunk, N)
        d = torch.cdist(cur[s:e], Q)          # (chunk, M)
        idx[s:e] = torch.argmin(d, dim=1)
    return idx


def icp_point2plane(src, dst, dst_normals, iters=30, tol=1e-9,
                    init=None, trim=None, device="cpu"):
    """点-面 ICP(Gauss-Newton, 小角近似)で剛体変換を高精度に精緻化する。

    粗マッチ(整数 NCC / Fourier-Mellin ±3° / Hough ±0.5voxel)の初期姿勢を
    表面点群の点-面距離最小化で締め上げる精緻化手法。各反復で src 各点の dst
    最近傍を対応付け、**点-面残差** ``r_i = n_i·(R·p_i + t - q_i)`` を最小化する。
    R を小角近似 ``R ≈ I + [ω]×`` で線形化すると各対応のヤコビアンは
    ``J_i = [p_i×n_i | n_i]``(スカラー三重積 ``n·(ω×p)=ω·(p×n)`` より)、
    定数項 ``b_i = -n_i·(p_i - q_i)``。正規方程式 ``(JᵀJ)x = Jᵀb`` を 6×6 で
    解いて増分 ``x=[ω|t]`` を得、Rodrigues で回転に戻して累積する。点-面は
    接平面内の滑りを許すため、point-to-point より少ない反復で表面にタイトに
    収束する(Low 2004)。

    実測(波打つ表面 N=2025, CPU float64): 初期6°/並進0.06 を 4 反復で euclid
    RMSE 1.7e-16・回転誤差 0° に回復(point-to-point は 17 反復で RMSE 4e-2・
    回転 1.9° 停滞)。初期角 3〜20° でも 4〜5 反復で機械精度。

    引数:
        src (N,3): 動かす側の点群(粗マッチ後の初期姿勢)。
        dst (M,3): 参照側の点群(固定)。
        dst_normals (M,3): dst の単位法線(未正規化でも内部で正規化)。
                           未知なら pointcloud.estimate_normals(dst) 等で事前推定。
        iters: 最大反復数。
        tol: RMSE 変化がこの値未満で収束打ち切り。
        init ((R0,t0)): 初期姿勢(粗マッチの R,t を渡す)。None なら単位。
        trim (float|None): [0,1) の割合。点-面残差の大きい上位を毎反復捨てる
                           Trimmed ICP(部分重なり・外れ値に頑健)。
        device: "cpu"/"cuda" 等。torch device 文字列(device 非依存)。

    返り値:
        R (3,3), t (3,), aligned (N,3)=R·src+t, rmse(採用点の点-面 RMSE),
        n_iter(実反復数)。
    """
    dt = torch.float64
    P0 = torch.as_tensor(np.asarray(src, np.float64), dtype=dt, device=device)
    Q = torch.as_tensor(np.asarray(dst, np.float64), dtype=dt, device=device)
    Nn = torch.as_tensor(np.asarray(dst_normals, np.float64), dtype=dt, device=device)
    Nn = Nn / torch.linalg.norm(Nn, dim=1, keepdim=True).clamp_min(1e-12)

    n_src = P0.shape[0]
    if init is None:
        R_tot = torch.eye(3, dtype=dt, device=device)
        t_tot = torch.zeros(3, dtype=dt, device=device)
        cur = P0.clone()
    else:
        R_tot = torch.as_tensor(np.asarray(init[0], np.float64), dtype=dt, device=device).clone()
        t_tot = torch.as_tensor(np.asarray(init[1], np.float64), dtype=dt, device=device).clone()
        cur = P0 @ R_tot.T + t_tot
    keep_n = n_src if trim is None else max(3, int(round((1.0 - float(trim)) * n_src)))

    prev = float("inf")
    rmse = float("inf")
    n_iter = 0
    reg = torch.eye(6, dtype=dt, device=device) * 1e-12       # 特異回避の微小正則化
    for it in range(int(iters)):
        n_iter = it + 1
        idx = _nearest(cur, Q)
        q = Q[idx]
        n = Nn[idx]
        resid = torch.einsum("ij,ij->i", cur - q, n)          # 符号付き点-面距離
        if keep_n < n_src:                                    # Trimmed: 残差小さい keep_n 点のみ
            sel = torch.argsort(resid.abs())[:keep_n]
        else:
            sel = slice(None)
        p_s, q_s, n_s, r_s = cur[sel], q[sel], n[sel], resid[sel]
        # J_i = [p×n | n],  b_i = -(p-q)·n = -r_s  (正規方程式 (JᵀJ)x=Jᵀb を 6×6 で)
        J = torch.cat([torch.linalg.cross(p_s, n_s), n_s], dim=1)   # (K,6)
        x = torch.linalg.solve(J.T @ J + reg, J.T @ (-r_s))
        R_inc = _rodrigues(x[:3], device)
        t_inc = x[3:]
        cur = cur @ R_inc.T + t_inc
        R_tot = R_inc @ R_tot
        t_tot = R_inc @ t_tot + t_inc
        # 更新後の点-面 RMSE(採用点のみで評価。同じ対応で単調性を判定)
        rmse = float(torch.sqrt(torch.mean(
            torch.einsum("ij,ij->i", cur[sel] - q_s, n_s) ** 2)))
        if abs(prev - rmse) < tol:
            break
        prev = rmse

    R = R_tot.detach().cpu().numpy()
    t = t_tot.detach().cpu().numpy()
    aligned = cur.detach().cpu().numpy()
    return R, t, aligned, rmse, n_iter


# ═══════════════════════════════════════════════════════════════════════════
# scene flow(2D optical flow → 3D)= voxel ごとの運動場(運動/変形の推定)
# ═══════════════════════════════════════════════════════════════════════════
def _flow_box3(t, r):
    """(1,1,D,H,W) の一様窓和(分離 conv3d)。Lucas-Kanade の構造テンソル窓和用。"""
    k = torch.ones(2 * r + 1, device=t.device)
    for ax in range(3):
        shp = [1, 1, 1, 1, 1]; shp[2 + ax] = 2 * r + 1
        pad = [0, 0, 0, 0, 0, 0]; pad[(2 - ax) * 2] = r; pad[(2 - ax) * 2 + 1] = r
        t = F.conv3d(F.pad(t, tuple(pad), mode="replicate"), k.view(*shp))
    return t


def _flow_warp(vol_t, flow, device):
    """vol_t(1,1,D,H,W) を flow(3,D,H,W)=(dz,dy,dx) で trilinear ワープ。"""
    _, _, D, H, W = vol_t.shape
    zz, yy, xx = torch.meshgrid(
        torch.arange(D, device=device, dtype=torch.float32),
        torch.arange(H, device=device, dtype=torch.float32),
        torch.arange(W, device=device, dtype=torch.float32), indexing="ij")
    sz = zz + flow[0]; sy = yy + flow[1]; sx = xx + flow[2]
    grid = torch.stack([2 * sx / (W - 1) - 1, 2 * sy / (H - 1) - 1,
                        2 * sz / (D - 1) - 1], dim=-1)[None]
    return F.grid_sample(vol_t, grid, align_corners=True, mode="bilinear",
                         padding_mode="border")


def scene_flow_lk(vol0, vol1, device="cpu", win=3, levels=3, iters=3, reg=1e-3):
    """Lucas-Kanade scene flow(2D optical flow の 3D 版)。voxel ごとの運動場 d=(dz,dy,dx)。

    テンプレ照合と違い **密な運動/変形**を推定する。明るさ一定 ∇I·d + I_t = 0 を窓内最小二乗で
    per-voxel に解く(3x3 構造テンソル A=Σ∇I∇Iᵀ, b=-Σ∇I·I_t を窓和 conv3d で)。pyramid + warp の
    coarse-to-fine で大変位に対応(各 level で I1 を現 flow で戻し残差を反復補正=Gauss-Newton)。
    vol1(x) ≈ vol0(x - d)。返り値 flow (3,D,H,W)。並進・拡大(発散)・回転(渦)場を捉える。

    実測: 一様並進 [1.5,-2,1] を中央領域平均で誤差 0.044 voxel、拡大場で外向き発散を正しく検出。
    grad_scale=32 は sobel3d(deriv[-1,0,1]×smooth[1,2,1]²)の実測スケール。GPU 対応(全 conv3d)。
    """
    v0 = torch.as_tensor(np.asarray(vol0, np.float32)[None, None], device=device)
    v1 = torch.as_tensor(np.asarray(vol1, np.float32)[None, None], device=device)
    pyr0 = [v0]; pyr1 = [v1]
    for _ in range(levels - 1):
        pyr0.append(F.avg_pool3d(pyr0[-1], 2)); pyr1.append(F.avg_pool3d(pyr1[-1], 2))
    flow = torch.zeros(3, *pyr0[-1].shape[2:], device=device)
    for lv in range(levels - 1, -1, -1):
        I0 = pyr0[lv]; I1 = pyr1[lv]; d, h, w = I0.shape[2:]
        if flow.shape[1:] != (d, h, w):
            flow = F.interpolate(flow[None], size=(d, h, w), mode="trilinear",
                                 align_corners=True)[0] * 2
        for _ in range(iters):
            Iw = _flow_warp(I1, flow, device)
            gz, gy, gx = sobel3d(Iw[0, 0], device)
            gz, gy, gx = gz / 32.0, gy / 32.0, gx / 32.0     # sobel3d 実測スケール
            It = Iw - I0
            Axx = _flow_box3(gx * gx, win); Ayy = _flow_box3(gy * gy, win)
            Azz = _flow_box3(gz * gz, win); Axy = _flow_box3(gx * gy, win)
            Axz = _flow_box3(gx * gz, win); Ayz = _flow_box3(gy * gz, win)
            bx = -_flow_box3(gx * It, win); by = -_flow_box3(gy * It, win)
            bz = -_flow_box3(gz * It, win)
            a = Azz + reg; b = Ayy + reg; c = Axx + reg      # 行列 (z,y,x 順)
            det = (a * (b * c - Axy * Axy) - Ayz * (Ayz * c - Axy * Axz)
                   + Axz * (Ayz * Axy - b * Axz)).clamp_min(1e-6)
            rz, ry, rx = bz, by, bx
            dz = ((b * c - Axy * Axy) * rz + (Axz * Axy - Ayz * c) * ry
                  + (Ayz * Axy - Axz * b) * rx) / det
            dy = ((Axy * Axz - Ayz * c) * rz + (a * c - Axz * Axz) * ry
                  + (Ayz * Axz - a * Axy) * rx) / det
            dx = ((Ayz * Axy - b * Axz) * rz + (Axz * Ayz - a * Axy) * ry
                  + (a * b - Ayz * Ayz) * rx) / det
            upd = torch.stack([dz[0, 0], dy[0, 0], dx[0, 0]], 0)
            flow = flow + upd.clamp(-2, 2)
    return flow.detach().cpu().numpy()
