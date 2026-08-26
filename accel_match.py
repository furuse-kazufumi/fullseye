"""accel_match — NCC テンプレートマッチング(ncc_locate)の GPU 化。

進化 champion locate / locate_rot は ``illuminate -> ncc_locate``。illuminate は accel で GPU 化
済み、残る ncc_locate(正規化相互相関 = normxcorr2)をここで GPU 化すると両 champion が
**100% GPU**(single 常駐)になる。NCC は correlate(mean-free テンプレート)+ uniform_filter
(box)による局所正規化 = conv2d / avg_pool の組合せで、shapematch_gpu と同じ GPU の本領。

core 一致(ops._ncc_map / _ncc_locate):
- num = ndimage.correlate(v, T-mean(T), mode='constant')      # zero-pad 相関
- m1  = uniform_filter(v,  size=T.shape, mode='constant')       # 局所平均(zero-pad)
- m2  = uniform_filter(v², size=T.shape, mode='constant')
- den = sqrt(max(m2-m1², 0) * T.size) * ||T-mean(T)||
- full-overlap 位置のみ有効、その他 0。out = clip(num/den, -1, 1)。
- ncc_locate = [max(out), argmax_row, argmax_col](MATCH 特徴、終端)。

honest: float32 で計算するので core(float64)と ~1e-6 の丸め差。argmax 位置は通常一致
(タスク指標 = 位置誤差 1/(1+px)で検証)。
"""
from __future__ import annotations

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    _HAS_TORCH = True
except Exception:  # pragma: no cover
    _HAS_TORCH = False


def ncc_map_batch(images, template, device="cpu"):
    """images(list[2D])の各要素に対する NCC マップ(list[2D])。core _ncc_map と一致。"""
    T = np.asarray(template, np.float64)
    imgs = [np.asarray(i, np.float64) for i in images]
    H, W = imgs[0].shape
    if T.ndim != 2:
        return [np.zeros((H, W)) for _ in imgs]
    Tz = T - float(T.mean())
    tnorm = float(np.sqrt(np.sum(Tz * Tz)))
    if tnorm < 1e-12:
        return [np.zeros((H, W)) for _ in imgs]
    Th, Tw = T.shape
    ph, pw = Th // 2, Tw // 2
    v = torch.as_tensor(np.stack(imgs)[:, None], dtype=torch.float32, device=device)
    ker = torch.as_tensor(Tz[None, None], dtype=torch.float32, device=device)
    ones = torch.ones(1, 1, Th, Tw, dtype=torch.float32, device=device)

    def corr(x, k):                                   # zero-pad 相関(F.conv2d は非反転=相関)
        return F.conv2d(F.pad(x, (pw, pw, ph, ph)), k)

    num = corr(v, ker)
    m1 = corr(v, ones) / (Th * Tw)
    m2 = corr(v * v, ones) / (Th * Tw)
    den = torch.sqrt(torch.clamp(m2 - m1 * m1, min=0.0) * float(T.size)) * tnorm
    out = torch.where(den > 1e-12, num / den, torch.zeros_like(num)).clamp(-1.0, 1.0)
    # full-overlap 位置のみ有効(core と同じ lo..hi、その他 0)
    lo_r, lo_c = Th // 2, Tw // 2
    hi_r, hi_c = H - (Th - 1 - Th // 2), W - (Tw - 1 - Tw // 2)
    mask = torch.zeros_like(out)
    if hi_r > lo_r and hi_c > lo_c:
        mask[:, :, lo_r:hi_r, lo_c:hi_c] = 1.0
    out = out * mask
    return [o[0] for o in out.detach().cpu().numpy().astype(np.float64)]


def ncc_locate_batch(images, template, device="cpu"):
    """各画像に対する [max_corr, argmax_row, argmax_col](core _ncc_locate と一致)。"""
    if template is None:
        return [np.array([0.0, 0.0, 0.0]) for _ in images]
    out = []
    for m in ncc_map_batch(images, template, device):
        idx = np.unravel_index(int(np.argmax(m)), m.shape)
        out.append(np.array([float(m[idx]), float(idx[0]), float(idx[1])]))
    return out


def ncc_map_3d(volumes, template, device="cpu"):
    """3D 正規化相互相関マップ(list[3D])。2D `ncc_map_batch` の voxel 版。

    cv2 に 3D matchTemplate は無い。num=correlate(mean-free T)、m1/m2=box3d(局所平均/二乗平均)、
    den=sqrt(max(m2-m1²,0)*T.size)*||Tz|| を conv3d で GPU 実行。full-overlap 位置のみ有効。
    """
    T = np.asarray(template, np.float64)
    vols = [np.asarray(v, np.float64) for v in volumes]
    D, H, W = vols[0].shape
    if T.ndim != 3:
        return [np.zeros((D, H, W)) for _ in vols]
    Tz = T - float(T.mean())
    tnorm = float(np.sqrt(np.sum(Tz * Tz)))
    if tnorm < 1e-12:
        return [np.zeros((D, H, W)) for _ in vols]
    Td, Th, Tw = T.shape
    pd, ph, pw = Td // 2, Th // 2, Tw // 2
    v = torch.as_tensor(np.stack(vols)[:, None], dtype=torch.float32, device=device)
    ker = torch.as_tensor(Tz[None, None], dtype=torch.float32, device=device)
    ones = torch.ones(1, 1, Td, Th, Tw, dtype=torch.float32, device=device)

    def corr(x, k):                                   # zero-pad 相関(conv3d は非反転)
        return F.conv3d(F.pad(x, (pw, pw, ph, ph, pd, pd)), k)

    num = corr(v, ker)
    m1 = corr(v, ones) / (Td * Th * Tw)
    m2 = corr(v * v, ones) / (Td * Th * Tw)
    den = torch.sqrt(torch.clamp(m2 - m1 * m1, min=0.0) * float(T.size)) * tnorm
    out = torch.where(den > 1e-12, num / den, torch.zeros_like(num)).clamp(-1.0, 1.0)
    lo = (Td // 2, Th // 2, Tw // 2)
    hi = (D - (Td - 1 - Td // 2), H - (Th - 1 - Th // 2), W - (Tw - 1 - Tw // 2))
    mask = torch.zeros_like(out)
    if all(h > l for l, h in zip(lo, hi)):
        mask[:, :, lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = 1.0
    out = out * mask
    return [o[0] for o in out.detach().cpu().numpy().astype(np.float64)]


def _subvoxel_com(m, idx, win=2):
    """相関ピーク近傍(±win)の正値を重みにした空間重心(center of mass)= sub-voxel 定位。

    argmax は整数量子化で ±0.5vox の誤差を持つ。応答マップの COM を取ると連続座標で
    ピークを精密化できる(位相相関の sub-pixel と同系)。HALCON area_center 的な重心も同原理。
    """
    slices = tuple(slice(max(0, i - win), min(s, i + win + 1)) for i, s in zip(idx, m.shape))
    w = np.clip(m[slices], 0.0, None)
    tot = float(w.sum())
    if tot <= 1e-12:
        return [float(i) for i in idx]
    axes = [np.arange(sl.start, sl.stop) for sl in slices]
    grids = np.meshgrid(*axes, indexing="ij")
    return [float((g * w).sum() / tot) for g in grids]


def ncc_locate_3d(volumes, template, device="cpu", subvoxel=True, win=2):
    """各 volume の [max_corr, d, h, w]。subvoxel=True なら重心で連続座標に精密化。"""
    if template is None:
        return [np.array([0.0, 0.0, 0.0, 0.0]) for _ in volumes]
    out = []
    for m in ncc_map_3d(volumes, template, device):
        idx = np.unravel_index(int(np.argmax(m)), m.shape)
        pos = _subvoxel_com(m, idx, win) if subvoxel else [float(i) for i in idx]
        out.append(np.array([float(m[idx])] + pos))
    return out


def _downsample3d(vol, factor, device):
    t = torch.as_tensor(np.asarray(vol, np.float32)[None, None], device=device)
    return F.avg_pool3d(t, factor)[0, 0].cpu().numpy().astype(np.float64)


def ncc_locate_3d_pyramid(volumes, template, device="cpu", levels=2, win=3,
                          subvoxel=True):
    """3D voxel ピラミッドサーチ(coarse-to-fine)。大 volume で全探索より速い。

    粗解像度(1/2^levels)で全 NCC → 概略位置 → 全解像度でその周り ±win を局所 NCC で精密化 →
    重心で sub-voxel。HALCON/OpenCV の画像ピラミッドマッチングの voxel 版。全探索 NCC と同じ
    位置を出しつつ、探索コストを「粗全探索(voxel 1/8^levels)+ 微小窓」に落とす。
    """
    T = np.asarray(template, np.float64)
    # 粗テンプレートが小さくなりすぎない様に level を自動制限(coarse T >= ~3vox)
    max_lv = max(0, int(np.floor(np.log2(min(T.shape) / 3.0))))
    levels = min(levels, max_lv)
    if levels <= 0:
        return ncc_locate_3d(volumes, template, device, subvoxel, win)
    f = 2 ** levels
    Tc = _downsample3d(T, f, device)
    out = []
    for vol in volumes:
        v = np.asarray(vol, np.float64)
        vc = _downsample3d(v, f, device)
        cm = ncc_map_3d([vc], Tc, device)[0]                  # 粗全探索
        ci = np.unravel_index(int(np.argmax(cm)), cm.shape)
        # 全解像度へ写像(粗 voxel c → 全解像度 [c*f, c*f+f) の中心)+ その周りの窓を精密化。
        # ★窓はテンプレより大きくないと full-overlap 位置がゼロになる → r = T//2 + f(粗誤差) + win。
        center = [min(s - 1, max(0, c * f + f // 2)) for c, s in zip(ci, v.shape)]
        sl = tuple(slice(max(0, c - (ts // 2 + f + win)), min(s, c + ts // 2 + f + win + 1))
                   for c, ts, s in zip(center, T.shape, v.shape))
        crop = v[sl]
        fm = ncc_map_3d([crop], T, device)[0]                 # 局所全 NCC
        fi = np.unravel_index(int(np.argmax(fm)), fm.shape)
        pos = _subvoxel_com(fm, fi, min(win, 2)) if subvoxel else [float(i) for i in fi]
        pos = [p + sl[k].start for k, p in enumerate(pos)]    # 窓オフセットを戻す
        out.append(np.array([float(fm[fi])] + pos))
    return out


# match accel op 名 -> 再現する core op 名
MATCH_ACCEL = {"ncc_locate": "ncc_locate"}


def main(device="cpu") -> int:
    import ops
    from problems import _template  # locate と同じ 11px テンプレート
    rng = np.random.default_rng(0)
    T = _template(11)
    ops.set_match_template(T)
    rr = T.shape[0] // 2
    imgs, gts = [], []
    for _ in range(4):
        base = rng.random((48, 48)) * 0.4
        r = int(rng.integers(rr + 1, 48 - rr - 1)); c = int(rng.integers(rr + 1, 48 - rr - 1))
        base[r - rr:r + rr + 1, c - rr:c + rr + 1] = np.maximum(
            base[r - rr:r + rr + 1, c - rr:c + rr + 1], T)
        imgs.append(np.clip(base + rng.normal(0, 0.1, base.shape), 0, 1)); gts.append((r, c))
    print(f"=== accel_match parity (device={device}) ===")
    gpu = ncc_locate_batch(imgs, T, device)
    worst_score, worst_pos = 0.0, 0
    for im, g, (gr, gc) in zip(imgs, gpu, gts):
        cpu = ops.RT["ncc_locate"](np.asarray(im, np.float64), 0.0, 0.0)
        worst_score = max(worst_score, abs(cpu[0] - g[0]))
        worst_pos = max(worst_pos, abs(cpu[1] - g[1]) + abs(cpu[2] - g[2]))
    print(f"  score |Δ| max={worst_score:.2e}  argmax pos |Δ| max={worst_pos:.0f} px")
    ok = worst_score < 5e-3 and worst_pos == 0
    print("faithful" if ok else "DRIFT")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    dev = "cuda" if "cuda" in sys.argv else "cpu"
    raise SystemExit(main(dev))
