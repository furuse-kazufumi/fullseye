"""accel_vol — 3D volume op の GPU 化(accel の 2D 版に対応する volume sort 版)。

進化 champion の vol_count / vol_denoise は **全段が volume op**(vol_median / vol_gaussian /
vol_erode / vol_dilate / vol_threshold)で、accel(2D)では 0% しか GPU に載らない。ここで
その 3D 版を torch(conv3d / max_pool3d / reflect pad)で実装し、この 2 champion を
0%→~100% GPU 化する(``accel_bridge`` が volume 区間を検出してここへ流す)。

honest parity gate: core(``ops.RT["vol_*"]`` = scipy.ndimage)と **interior <5e-3 一致**する
ものだけ載せる。border は reflect/pool 規約が scipy と端で違う(accel 2D と同根)。3D volume は
voxel 数が H×W×D と大きく、GPU の帯域が最も効く領域。

core 意味論(ops.py):
- vol_gaussian: ``ndimage.gaussian_filter(v, sigma=0.3+2.7*a)``(全軸同 σ、truncate=4.0)
- vol_median:   ``ndimage.median_filter(v, size=3)``(3³、a 非依存)
- vol_erode:    ``ndimage.grey_erosion(v, size=1+2*(1+int(a)))``(a<1 で 3³、a==1 で 5³)
- vol_dilate:   ``ndimage.grey_dilation(v, size=同上)``
- vol_threshold:``(v > a)``(→ 2 値 volume。bit 一致)
"""
from __future__ import annotations

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    _HAS_TORCH = True
except Exception:  # pragma: no cover
    _HAS_TORCH = False


def _to_vol_batch(vols, device):
    """list[(D,H,W)] -> (B,1,D,H,W) float32 tensor。"""
    x = np.stack([np.asarray(v, np.float64) for v in vols])[:, None]
    return torch.as_tensor(x, dtype=torch.float32, device=device)


def _from_vol_batch(t):
    return [a[0] for a in t.detach().cpu().numpy().astype(np.float64)]


def _gauss_kernel(sigma, device):
    r = max(1, int(4.0 * sigma + 0.5))               # scipy truncate=4.0
    x = torch.arange(-r, r + 1, dtype=torch.float32, device=device)
    k = torch.exp(-(x * x) / (2 * sigma * sigma))
    return k / k.sum()


def _sep_conv3d(t, k):
    """3 軸で分離可能 1D conv(reflect パディング)。t=(B,1,D,H,W)。"""
    r = (k.numel() - 1) // 2
    for axis in range(3):                             # 0=D, 1=H, 2=W
        shape = [1, 1, 1, 1, 1]
        shape[2 + axis] = k.numel()
        ker = k.view(*shape)
        pad = [0, 0, 0, 0, 0, 0]                      # (w0,w1,h0,h1,d0,d1)
        pad[(2 - axis) * 2] = r
        pad[(2 - axis) * 2 + 1] = r
        t = F.conv3d(F.pad(t, tuple(pad), mode="reflect"), ker)
    return t


def _vol_kmorph(a):
    return 1 + 2 * (1 + int(a))                       # core: 3(a<1) / 5(a==1)


# each: (batch tensor, a, b, device) -> batch tensor
def _vol_gaussian(t, a, b, dev):
    return _sep_conv3d(t, _gauss_kernel(0.3 + 2.7 * a, dev))


def _vol_median(t, a, b, dev):
    p = F.pad(t, (1, 1, 1, 1, 1, 1), mode="reflect")
    D, H, W = t.shape[2], t.shape[3], t.shape[4]
    nb = [p[:, :, dz:dz + D, dy:dy + H, dx:dx + W]
          for dz in range(3) for dy in range(3) for dx in range(3)]
    return torch.stack(nb, dim=0).median(dim=0).values   # 3³=27 近傍の中央値


def _vol_erode(t, a, b, dev):
    k = _vol_kmorph(a)
    return -F.max_pool3d(-t, k, stride=1, padding=k // 2)


def _vol_dilate(t, a, b, dev):
    k = _vol_kmorph(a)
    return F.max_pool3d(t, k, stride=1, padding=k // 2)


def _vol_threshold(t, a, b, dev):
    return (t > a).float()


# vol accel op 名 -> (fn, 再現する core op 名)
VOL_ACCEL = {
    "vol_gaussian_g": (_vol_gaussian, "vol_gaussian"),
    "vol_median_g": (_vol_median, "vol_median"),
    "vol_erode_g": (_vol_erode, "vol_erode"),
    "vol_dilate_g": (_vol_dilate, "vol_dilate"),
    "vol_threshold_g": (_vol_threshold, "vol_threshold"),
}


def run_batch_vol(name, vols, a=0.5, b=0.4, device="cpu"):
    t = _to_vol_batch(vols, device)
    return _from_vol_batch(VOL_ACCEL[name][0](t, a, b, device).clamp(0, 1))


def run_pipeline_vol(steps, vols, device="cpu"):
    """volume 版の常駐パイプライン。steps=[(vol_accel名,a,b),...]。転送1回で 3D op 連鎖。"""
    t = _to_vol_batch(vols, device)
    for name, a, b in steps:
        t = VOL_ACCEL[name][0](t, a, b, device).clamp(0, 1)
    return _from_vol_batch(t)


# --------------------------------------------------------------------------- #
# parity gate: core(scipy.ndimage)との interior 一致を確認する CLI            #
# --------------------------------------------------------------------------- #
def _interior_max(ref, got, m=2):
    if ref.shape[0] > 2 * m:
        s = (slice(m, -m),) * ref.ndim
        return float(np.max(np.abs(ref[s] - got[s])))
    return float(np.max(np.abs(ref - got)))


def _op_margin(name, a):
    """faithful を測る interior margin。gaussian は端の reflect 規約差がカーネル半径ぶん
    内側まで届くので、その半径を除外する(median/morph/threshold は端 2px で十分)。"""
    if name == "vol_gaussian_g":
        sigma = 0.3 + 2.7 * a
        return max(2, int(4.0 * sigma + 0.5))        # = カーネル半径
    return 2


def main(device="cpu") -> int:
    import ops
    rng = np.random.default_rng(0)
    # 実 champion サイズ(32³)。小さすぎる volume だと大カーネル gaussian が端支配になる。
    vols = [np.clip(rng.random((32, 32, 32)), 0, 1) for _ in range(3)]
    print(f"=== accel_vol parity (device={device}, 32³, interior=端からカーネル半径除外) ===")
    ok = 0
    for name, (fn, core) in VOL_ACCEL.items():
        a, b = 0.53, 0.49
        m = _op_margin(name, a)
        got = run_batch_vol(name, vols, a, b, device)
        worst = 0.0
        for v, g in zip(vols, got):
            ref = np.clip(np.asarray(ops.RT[core](np.asarray(v, np.float64), a, b),
                                     np.float64), 0, 1)
            worst = max(worst, _interior_max(ref, np.asarray(g, np.float64), m))
        faithful = worst < 5e-3
        ok += faithful
        print(f"  {name:18s} <- {core:14s} interior_max(m={m:2d})={worst:.2e} "
              f"{'faithful' if faithful else 'DRIFT'}")
    print(f"faithful: {ok}/{len(VOL_ACCEL)}")
    return 0 if ok == len(VOL_ACCEL) else 1


if __name__ == "__main__":
    import sys
    dev = "cuda" if "--device" in sys.argv and "cuda" in sys.argv else "cpu"
    raise SystemExit(main(dev))
