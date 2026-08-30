"""形状ベースマッチングの GPU 実装(shapematch の conv2d 定式化).

**着想**: Steger 流の勾配方向スコアは

    score_map(r0,c0) = [ Σ_pt Uy[pt+off]·model_gy + Ux[pt+off]·model_gx ] / n

で、Uy,Ux は単位化した画像勾配。これは **モデルを勾配カーネル画像に描いた
cross-correlation** そのもの —— GPU が最も得意な密画素並列演算(粘菌ソルバの
起動レイテンシ律速な CG とは逆)。しかも **変換(角度×スケール)をカーネルの
バッチ軸(conv2d の out_channels)に積む** と、全変換を 2 回の conv2d で同時評価
できる。HALCON 本家は shape matching を CPU(SIMD/マルチコア)で回しており、
GPU 化していない —— ここは本実装の差別化点。

対応する metric:
- ``use_polarity``  —— max(0, score)。argmax は符号つき score のまま。
- ``ignore_global`` —— abs(score)。
- ``ignore_local``(点ごと abs)は和の前に非線形が入り conv で表現できない。
  これは HALCON も「偽陽性が出やすい」と警告する緩い metric なので、GPU では
  非対応(呼び出し側が CPU にフォールバックする)。

min_contrast は画像側マスク(mag<mc の画素の単位勾配を 0)で近似する。変換ごとに
mc は僅かに違うが、共有 mc(基準モデルの min_contrast)で全変換をまとめて conv
する。argmax(最良位置・最良変換)の一致で正しさを見る。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

try:
    import torch
    import torch.nn.functional as F
    _HAS_TORCH = True
except Exception:                                  # pragma: no cover
    _HAS_TORCH = False


def gpu_available() -> bool:
    return _HAS_TORCH and torch.cuda.is_available()


def _unit_grad_fields(image, mc):
    """画像の単位勾配 Uy,Ux(scipy sobel、CPU 厳密)。mag<mc は 0(min_contrast)。"""
    img = np.asarray(image, dtype=np.float64)
    gx = ndimage.sobel(img, axis=1)
    gy = ndimage.sobel(img, axis=0)
    mag = np.hypot(gx, gy)
    md = mag + 1e-9
    uy = gy / md
    ux = gx / md
    if mc and mc > 0.0:
        low = mag < mc
        uy = np.where(low, 0.0, uy)
        ux = np.where(low, 0.0, ux)
    return uy, ux


def _render_kernels(models, dtype):
    """変換済みモデル列 → 中央寄せした勾配カーネル (B,1,hmax,wmax) の Ky,Kx と n。

    各モデルは自分の shape の中央(h//2)を基準に pt を持つ。異なる h,w を共通の
    (hmax,wmax) に中央寄せで埋め、conv の padding=hmax//2 と整合させる。
    """
    hs = [m["shape"][0] for m in models]
    ws = [m["shape"][1] for m in models]
    hmax, wmax = max(hs), max(ws)
    B = len(models)
    Ky = np.zeros((B, hmax, wmax), dtype=dtype)
    Kx = np.zeros((B, hmax, wmax), dtype=dtype)
    ns = np.zeros(B, dtype=dtype)
    for b, m in enumerate(models):
        h, w = m["shape"]
        off_r = hmax // 2 - h // 2
        off_c = wmax // 2 - w // 2
        pr = m["pts"][:, 0] + off_r
        pc = m["pts"][:, 1] + off_c
        Ky[b, pr, pc] = m["grad"][:, 0]
        Kx[b, pr, pc] = m["grad"][:, 1]
        ns[b] = len(m["pts"])                       # 分母は全点数(画像外は 0 点)
    return Ky, Kx, ns, hmax, wmax


def score_maps(models, image, *, metric="use_polarity", mc=0.0,
               device="cuda", dtype="float32"):
    """変換済みモデル列 ``models`` を画像上で同時評価し、metric 適用済みの
    スコアマップ (B, H, W) を返す(numpy)。全変換を 2 回の conv2d で。

    ``models`` は同じ画像に対する複数の(角度×スケール)変換。``mc`` は共有
    min_contrast。``ncount`` も返す必要はない(各行 /n 済み)。
    """
    if not _HAS_TORCH:
        raise RuntimeError("torch is required")
    if metric == "ignore_local_polarity":
        raise ValueError("ignore_local_polarity cannot be expressed as a conv (use CPU instead)")
    dev = torch.device(device)
    ftype = torch.float32 if dtype == "float32" else torch.float64

    uy, ux = _unit_grad_fields(image, mc)
    H, W = uy.shape
    Uy = torch.as_tensor(uy, device=dev, dtype=ftype).reshape(1, 1, H, W)
    Ux = torch.as_tensor(ux, device=dev, dtype=ftype).reshape(1, 1, H, W)

    npd = np.float32 if dtype == "float32" else np.float64
    Ky_np, Kx_np, ns_np, hmax, wmax = _render_kernels(models, npd)
    Ky = torch.as_tensor(Ky_np, device=dev, dtype=ftype).unsqueeze(1)   # (B,1,hmax,wmax)
    Kx = torch.as_tensor(Kx_np, device=dev, dtype=ftype).unsqueeze(1)
    ns = torch.as_tensor(ns_np, device=dev, dtype=ftype).reshape(-1, 1, 1)

    pad = (hmax // 2, wmax // 2)
    # conv2d は相関(カーネル反転なし)。out[0,b] = Σ U[i+u-pad, j+v-pad]*K[b,u,v]
    cy = F.conv2d(Uy, Ky, padding=pad)[0]           # (B, H', W')
    cx = F.conv2d(Ux, Kx, padding=pad)[0]
    smap = (cy + cx) / ns                            # (B, H', W')
    smap = smap[:, :H, :W]                           # 偶数サイズの +1 を切る

    if metric == "ignore_global_polarity":
        smap = smap.abs()
    else:                                            # use_polarity
        smap = smap.clamp_min(0.0)
    return smap.cpu().numpy()


def search_transforms(model, image, combos, *, min_score=0.5,
                      device="cuda", dtype="float32", build_transform=None,
                      border_guard=True):
    """(angle, sr, sc) を GPU で同時掃引し最良の
    (score, row, col, angle, sr, sc) を返す(見つからなければ None)。

    ``build_transform(model, angle, sr, sc)`` は変換モデルを作る関数(shapematch の
    transform_model を渡す)。潰れた変換(None)は落とす。ピラミッドは使わない
    —— conv が密で速いので全解像度で十分(実測で CPU ピラミッドより速い)。
    """
    if build_transform is None:
        raise ValueError("must pass build_transform(transform_model)")
    metric = model.get("metric", "use_polarity")
    mc = float(model.get("min_contrast", 0.0))

    kept, keys = [], []
    for (ang, sr, sc) in combos:
        tm = build_transform(model, ang, sr, sc)
        if tm is None:
            continue
        kept.append(tm)
        keys.append((float(ang), float(sr), float(sc)))
    if not kept:
        return None

    smaps = score_maps(kept, image, metric=metric, mc=mc,
                       device=device, dtype=dtype)      # (B,H,W)
    best = None
    for b, (ang, sr, sc) in enumerate(keys):
        sm = smaps[b]
        if border_guard:
            h, w = kept[b]["shape"]
            hh, ww = h // 2, w // 2
            # モデルが完全に画像内に入る内部だけを見る(CPU の走査範囲に合わせる)
            view = sm[hh:sm.shape[0] - hh, ww:sm.shape[1] - ww]
            if view.size == 0:
                continue
            idx = np.argmax(view)
            r, c = np.unravel_index(idx, view.shape)
            r += hh
            c += ww
            score = float(sm[r, c])
        else:
            idx = np.argmax(sm)
            r, c = np.unravel_index(idx, sm.shape)
            score = float(sm[r, c])
        if best is None or score > best[0]:
            best = (score, int(r), int(c), ang, sr, sc)
    return best
