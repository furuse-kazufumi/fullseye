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
