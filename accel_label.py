# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""accel_label — 領域の解析(連結成分のラベル付け + 領域ごとの集計)の torch 経路 / GPU region analysis.

``accel.ACCEL`` に載る手書きの経路(``kind="accel"``)。CPU と GPU のどちらの torch でも同じ式で走る。

ラベル付け :func:`label` は「最小の画素番号を伝える」反復(近傍の最小値 → 根への吊り下げ
``scatter_reduce(amin)`` → ポインタの飛び越し)で、収束したラベルは**各連結成分の最小の画素番号**
(= 行優先で最初の画素)になる。scipy ``ndimage.label`` は成分を行優先で最初の画素の順に 1, 2, ... と
番号づけるので、根を昇順に並べた順位が scipy の番号と一致する(``argmax`` の同点の選び方も同じ)。
それでも門(``tests/test_accel_label.py``)は番号でなく**領域の集合として**比べる。

領域ごとの集計は ``bincount``(面積)・``scatter_reduce``(外接矩形)で行い、整数のまま数えるので
面積・個数・外接矩形・重心の和は CPU と完全一致する。

op の 3 つの形:

* **領域 → 領域**(``(B,1,H,W)`` の 0/1 を返す): ``remove_small`` / ``select_shape`` / ``select_largest`` /
  ``select_shape_std`` / ``sk_clear_border`` / ``r2_sort_region`` / ``r3_background_seg`` /
  ``r3_select_region_point`` / ``fill_up_shape`` / ``sk_remove_holes`` / ``smallest_rectangle1``。
* **領域 → 特徴・ベクトル**(:data:`REDUCERS`、1 枚ごとに ``np.float64`` か 1-D 配列): ``count_obj`` /
  ``connect_and_holes`` / ``blob_count`` / ``cv_cc_count`` / ``area_center`` / ``area_frac``。
* **最大の成分の形の特徴**(:data:`REDUCERS`): GPU でラベル付けと最大の成分・外接矩形を求め、その成分
  だけを 1 画素の余白つきで切り出して、**op 自身の CPU の式**に渡す(``circularity`` ほか 20 op)。
  式は平行移動で変わらない量だけなので答えは同じ —— ただし重心の引き算の丸めが原点で変わるので、
  門は相対 1e-9 で比べる(整数の量は完全一致)。

NaN / inf を含む入力は CPU の op をそのまま呼ぶ(``select_largest`` などは CPU が ``FsValueError`` を
投げる契約。GPU の側で 0.5 以下として黙って数えない)。
"""
from __future__ import annotations

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    _HAS_TORCH = True
except Exception:  # pragma: no cover
    _HAS_TORCH = False

#: 1 回のラベル付けの反復の上限(超えたら RuntimeError = GPU の失敗として記録され CPU で続く)。
MAX_ITERS = 100_000
#: 前半の 1 反復あたりのポインタの飛び越しの回数(同期しない固定回数)。
JUMPS = 3
#: 前半: 収束の判定(装置との同期)を挟むまでの反復の数。判定は 3 回(1 + 2 + 4 = 7 反復)。
#: 2026-11-03: 反復ごと + 飛び越しごとに ``torch.equal`` で同期していた版(後半と同じ)は一辺 128 で 3.5〜4.5 ms、
#: 前半の形だけにした版は 2048 の渦巻き(深い木)で 15 ms(旧 5.6 ms)。前半で収まらない入力だけ後半へ
#: 渡すと、測った 9 点(3 入力 x 3 辺)の全部で両者の速い方とほぼ同じ(実測は docs/perf/logs/label の 2 回目)。
PHASE1_BLOCKS = (1, 2, 4)


# ---- ラベル付け -------------------------------------------------------------------------------
def _neighbour_min(L, conn: int, big: int):
    """(B,H,W) の int64 ラベル *L* の近傍(自分を含む)の最小値。画像の外は *big*。"""
    P = F.pad(L, (1, 1, 1, 1), value=big)
    m = torch.minimum(L, P[:, :-2, 1:-1])
    m = torch.minimum(m, P[:, 2:, 1:-1])
    m = torch.minimum(m, P[:, 1:-1, :-2])
    m = torch.minimum(m, P[:, 1:-1, 2:])
    if conn == 8:
        m = torch.minimum(m, P[:, :-2, :-2])
        m = torch.minimum(m, P[:, :-2, 2:])
        m = torch.minimum(m, P[:, 2:, :-2])
        m = torch.minimum(m, P[:, 2:, 2:])
    return m


def label(mask, conn: int = 4):
    """``(labels, fidx)``。*mask* = (B,H,W) bool、*conn* = 4 か 8。

    ``labels`` は (B,H,W) int64: 前景は所属する成分の最小の通し画素番号(``b*H*W + y*W + x``)、
    背景は ``B*H*W``。``fidx`` = 前景画素の通し番号(昇順)。
    """
    if conn not in (4, 8):
        raise ValueError("conn must be 4 or 8; got %r" % (conn,))
    B, H, W = mask.shape
    N = B * H * W
    dev = mask.device
    idx = torch.arange(N, device=dev, dtype=torch.int64).view(B, H, W)
    L = torch.where(mask, idx, torch.full_like(idx, N))
    fidx = torch.nonzero(mask.reshape(-1)).squeeze(1)
    if fidx.numel() == 0:
        return L, fidx
    Lf = L.view(-1)

    def step():
        cur = Lf[fidx]
        m = _neighbour_min(L, conn, N).reshape(-1)[fidx]
        # 根への吊り下げ: 今のラベル(同じ成分の画素)の値を、近傍の最小値まで下げる
        Lf.scatter_reduce_(0, cur, m, reduce="amin")
        Lf[fidx] = torch.minimum(Lf[fidx], m)
        # ポインタの飛び越し(ラベルのラベルを引く)を固定回数。同期しない
        for _ in range(JUMPS):
            Lf[fidx] = Lf[Lf[fidx]]

    # 収束 = 1 反復で何も変わらない(近傍の最小値が自分以上 = 成分の上で一定、かつ飛び越しが止まる)。
    # 前半: 飛び越しは固定回数、判定は PHASE1_BLOCKS の区切りでだけ(浅い木はここで終わる)。
    done = 0
    for block in PHASE1_BLOCKS:
        for _ in range(block - 1):
            step()
        prev = Lf[fidx].clone()
        step()
        done += block
        if torch.equal(Lf[fidx], prev):
            return L, fidx
    # 後半: 深い木(渦巻きのような長い成分)。飛び越しを落ち着くまで回し、反復ごとに判定する。
    while done < MAX_ITERS:
        prev = Lf[fidx].clone()
        cur = Lf[fidx]
        m = _neighbour_min(L, conn, N).reshape(-1)[fidx]
        Lf.scatter_reduce_(0, cur, m, reduce="amin")
        Lf[fidx] = torch.minimum(Lf[fidx], m)
        while True:
            cur = Lf[fidx]
            nxt = Lf[cur]
            if torch.equal(nxt, cur):
                break
            Lf[fidx] = nxt
        done += 1
        if torch.equal(Lf[fidx], prev):
            return L, fidx
    raise RuntimeError("accel_label.label did not converge in %d iterations" % MAX_ITERS)


def _areas(L, fidx, N):
    """通し画素番号ごとの面積(根の位置にだけ値が入る、長さ N)。"""
    return torch.bincount(L.view(-1)[fidx], minlength=N)


def _roots(L, fidx):
    """根(成分の代表 = 最小の画素番号)を昇順に。"""
    lab = L.view(-1)[fidx]
    return fidx[lab == fidx]


def _keep(L, flag):
    """``flag``(長さ N+1 の bool、最後は背景)の立った成分の画素だけ 1 の (B,1,H,W) float。"""
    return flag[L].unsqueeze(1).float()


def _flag_of(roots, N, dev):
    f = torch.zeros(N + 1, dtype=torch.bool, device=dev)
    f[roots] = True
    return f


def _bin_t(t):
    return t[:, 0] > 0.5


def _finite(t) -> bool:
    return bool(torch.isfinite(t).all())


def _cpu_op(core):
    """登録簿の CPU の op(NaN / inf の入力で使う。CPU と同じ例外・同じ答え)。"""
    import ops
    return ops.RT[core]


def _per_image_cpu(core, t, a, b):
    fn = _cpu_op(core)
    arr = t.detach().cpu().numpy().astype(np.float64)
    return [fn(arr[i, 0], a, b) for i in range(arr.shape[0])]


def _to_region(outs, t):
    """CPU の答え(1 枚ごとの 2-D)を (B,1,H,W) float に戻す。"""
    x = np.stack([np.asarray(o, np.float32) for o in outs])[:, None]
    return torch.as_tensor(x, device=t.device)


def _knob(x) -> float:
    """``backends_regions3._knob`` と同じ(非有限は 0.5、[0,1] に切る)。"""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not np.isfinite(x):
        return 0.5
    return min(1.0, max(0.0, x))


# ---- 領域 → 領域 -------------------------------------------------------------------------------
def _select_by_area(t, thr_of, conn=4):
    m = _bin_t(t)
    B, H, W = m.shape
    N = B * H * W
    L, fidx = label(m, conn)
    if fidx.numel() == 0:
        return torch.zeros_like(t)
    area = _areas(L, fidx, N)
    roots = _roots(L, fidx)
    keep = area[roots].double() >= thr_of(H, W)
    return _keep(L, _flag_of(roots[keep], N, t.device))


def _remove_small(t, a, b, dev):
    """``ops.remove_small``: 4 連結、面積が ``(0.01+0.15a)*画素数`` 以上の成分を残す。"""
    return _select_by_area(t, lambda H, W: (0.01 + 0.15 * a) * (H * W))


def _select_shape(t, a, b, dev):
    """``select_shape``(``remove_small`` 種): 4 連結、面積 ``int(16+200a)`` 以上を残す。"""
    thr = int(16 + a * 200)
    return _select_by_area(t, lambda H, W: thr)


def _largest_roots(L, fidx, N, HW, B):
    """1 枚ごとの最大の成分の根(同点は最小の根 = scipy の argmax と同じ)。無い枚は -1。"""
    area = _areas(L, fidx, N)
    roots = _roots(L, fidx)
    out = torch.full((B,), -1, dtype=torch.int64, device=L.device)
    if roots.numel() == 0:
        return out
    img = roots // HW
    a = area[roots]
    best = torch.zeros(B, dtype=torch.int64, device=L.device).scatter_reduce(0, img, a, reduce="amax",
                                                                             include_self=True)
    cand = roots[a == best[img]]
    big = torch.full((B,), N, dtype=torch.int64, device=L.device)
    big.scatter_reduce_(0, cand // HW, cand, reduce="amin")
    return torch.where(big == N, out, big)


def _select_largest(t, a, b, dev):
    """``select_largest`` / ``select_shape_std``: 4 連結、最大の成分だけ。"""
    m = _bin_t(t)
    B, H, W = m.shape
    N = B * H * W
    L, fidx = label(m, 4)
    if fidx.numel() == 0:
        return torch.zeros_like(t)
    big = _largest_roots(L, fidx, N, H * W, B)
    return _keep(L, _flag_of(big[big >= 0], N, t.device))


def _select_largest_finite(t, a, b, dev):
    """``select_largest``(ops)は NaN / inf を拒む(CPU の op に任せる)。"""
    if not _finite(t):
        return _to_region(_per_image_cpu("select_largest", t, a, b), t)
    return _select_largest(t, a, b, dev)


def _clear_border(t, a, b, dev):
    """``sk_clear_border``: 8 連結(skimage ``label`` の既定)、画像の縁に触れる成分を消す。"""
    m = _bin_t(t)
    B, H, W = m.shape
    N = B * H * W
    L, fidx = label(m, 8)
    if fidx.numel() == 0:
        return torch.zeros_like(t)
    edge = torch.zeros((B, H, W), dtype=torch.bool, device=t.device)
    edge[:, 0, :] = True
    edge[:, -1, :] = True
    edge[:, :, 0] = True
    edge[:, :, -1] = True
    touch = L[edge & m]
    flag = torch.ones(N + 1, dtype=torch.bool, device=t.device)
    flag[touch] = False
    flag[N] = False
    return _keep(L, flag)


def _sort_region(t, a, b, dev):
    """``r2_sort_region``: 4 連結、面積の降順で ``round(a*(n-1))`` 番目。

    順位は CPU と同じ ``np.argsort``(同点の扱いも同じ)を、成分ごとの面積の短い列に当てて決める。
    """
    m = _bin_t(t) & torch.isfinite(t[:, 0])
    B, H, W = m.shape
    N = B * H * W
    HW = H * W
    L, fidx = label(m, 4)
    if fidx.numel() == 0:
        return torch.zeros_like(t)
    area = _areas(L, fidx, N)
    roots = _roots(L, fidx)
    r_np = roots.cpu().numpy()
    a_np = area[roots].cpu().numpy().astype(np.float64)
    chosen = []
    for i in range(B):
        sel = (r_np // HW) == i
        if not sel.any():
            continue
        sizes = a_np[sel]
        n = sizes.size
        order = np.argsort(sizes)[::-1]
        k = min(n - 1, max(0, int(round(_knob(a) * (n - 1)))))
        chosen.append(int(r_np[sel][int(order[k])]))
    roots_keep = torch.as_tensor(chosen, dtype=torch.int64, device=t.device)
    return _keep(L, _flag_of(roots_keep, N, t.device))


def _background_seg(t, a, b, dev):
    """``r3_background_seg``: 背景(補集合)の 4 連結成分のうち、面積が ``a * 最大`` 以上のもの。"""
    m = _bin_t(t) & torch.isfinite(t[:, 0])
    bg = ~m
    B, H, W = m.shape
    N = B * H * W
    HW = H * W
    L, fidx = label(bg, 4)
    if fidx.numel() == 0:
        return torch.zeros_like(t)
    area = _areas(L, fidx, N)
    roots = _roots(L, fidx)
    img = roots // HW
    s = area[roots].double()
    mx = torch.zeros(B, dtype=torch.float64, device=t.device).scatter_reduce(0, img, s, reduce="amax",
                                                                             include_self=True)
    keep = s >= _knob(a) * mx[img]
    return _keep(L, _flag_of(roots[keep], N, t.device))


def _select_region_point(t, a, b, dev):
    """``r3_select_region_point``: 4 連結、``(round(a*(H-1)), round(b*(W-1)))`` の画素を含む成分。"""
    m = _bin_t(t) & torch.isfinite(t[:, 0])
    B, H, W = m.shape
    N = B * H * W
    r = min(H - 1, max(0, int(round(_knob(a) * (H - 1)))))
    c = min(W - 1, max(0, int(round(_knob(b) * (W - 1)))))
    L, fidx = label(m, 4)
    if fidx.numel() == 0:
        return torch.zeros_like(t)
    lv = L[:, r, c]
    lv = lv[lv < N]
    return _keep(L, _flag_of(lv, N, t.device))


_HOLE_INCLUSIVE: list = []


def _holes_inclusive() -> bool:
    """``remove_small_holes(area_threshold=N)`` が面積ちょうど N の穴を埋めるか(skimage 0.26 は埋める、
    0.25 以前は埋めない)。CPU の op が使う実装に 1 回だけ当てて決める(版の番号に頼らない)。"""
    if not _HOLE_INCLUSIVE:
        import backends_auto
        probe = np.ones((5, 5), bool)
        probe[2, 2] = False                                   # 面積 1 の穴
        filled = bool(backends_auto._remove_small_holes(probe, area_threshold=1)[2, 2])
        _HOLE_INCLUSIVE.append(filled)
    return _HOLE_INCLUSIVE[0]


def _fill_small_holes(t, thr):
    """補集合の 4 連結成分のうち面積が閾値以下(または未満)のものを埋める(縁に触れる成分も数える)。"""
    m = _bin_t(t)
    bg = ~m
    B, H, W = m.shape
    N = B * H * W
    L, fidx = label(bg, 4)
    if fidx.numel() == 0:
        return m.unsqueeze(1).float()
    area = _areas(L, fidx, N)
    roots = _roots(L, fidx)
    s = area[roots]
    small = (s <= thr) if _holes_inclusive() else (s < thr)
    flag = _flag_of(roots[small], N, t.device)
    return (m | flag[L]).unsqueeze(1).float()


def _fill_up_shape(t, a, b, dev):
    """``fill_up_shape``(``remove_holes`` 種): 面積 ``int(16+200a)`` の穴まで埋める。"""
    return _fill_small_holes(t, int(16 + a * 200))


def _sk_remove_holes(t, a, b, dev):
    """``sk_remove_holes``: 面積 ``int(8+60a)`` の穴まで埋める。"""
    return _fill_small_holes(t, int(8 + a * 60))


def _smallest_rectangle1(t, a, b, dev):
    """``smallest_rectangle1``(``shape_bbox`` 種): 前景全体の軸平行の外接矩形を塗る。"""
    m = _bin_t(t)
    B, H, W = m.shape
    rows = m.any(dim=2)
    cols = m.any(dim=1)
    ar_h = torch.arange(H, device=t.device)
    ar_w = torch.arange(W, device=t.device)
    big = H + W + 1
    r0 = torch.where(rows, ar_h, big).amin(dim=1)
    r1 = torch.where(rows, ar_h, -1).amax(dim=1)
    c0 = torch.where(cols, ar_w, big).amin(dim=1)
    c1 = torch.where(cols, ar_w, -1).amax(dim=1)
    inr = (ar_h[None, :] >= r0[:, None]) & (ar_h[None, :] <= r1[:, None])
    inc = (ar_w[None, :] >= c0[:, None]) & (ar_w[None, :] <= c1[:, None])
    return (inr[:, :, None] & inc[:, None, :]).unsqueeze(1).float()


# ---- 領域 → 特徴・ベクトル(REDUCERS: 1 枚ごとに np の値を返す) ------------------------------------
def _count(t, conn):
    m = _bin_t(t)
    B, H, W = m.shape
    L, fidx = label(m, conn)
    if fidx.numel() == 0:
        return [np.float64(0.0)] * B
    roots = _roots(L, fidx)
    n = torch.bincount(roots // (H * W), minlength=B).cpu().numpy()
    return [np.float64(int(k)) for k in n]


def _count8(t, a, b, dev):
    """``count_obj`` / ``connect_and_holes``: 8 連結の成分の個数。"""
    return _count(t, 8)


def _blob_count(t, a, b, dev):
    """``blob_count``: 8 連結の成分の個数(NaN / inf は CPU の op が拒む)。"""
    if not _finite(t):
        return _per_image_cpu("blob_count", t, a, b)
    return _count(t, 8)


def _cv_cc_count(t, a, b, dev):
    """``cv_cc_count``: 8 連結(``cv2.connectedComponents`` の既定)の個数。非有限の入力は CPU の op が拒む。"""
    if not _finite(t):
        return _per_image_cpu("cv_cc_count", t, a, b)
    return _count(t, 8)


def _area_center(t, a, b, dev):
    """``area_center``: ``(面積 [画素], 重心の行, 重心の列)``。空なら ``(0, (H-1)/2, (W-1)/2)``。"""
    if not _finite(t):
        return _per_image_cpu("area_center", t, a, b)
    m = _bin_t(t)
    B, H, W = m.shape
    ys = torch.arange(H, device=t.device, dtype=torch.int64)[None, :, None]
    xs = torch.arange(W, device=t.device, dtype=torch.int64)[None, None, :]
    mi = m.to(torch.int64)
    area = mi.sum(dim=(1, 2))
    sy = (mi * ys).sum(dim=(1, 2))
    sx = (mi * xs).sum(dim=(1, 2))
    vals = torch.stack([area, sy, sx], 1).cpu().numpy()
    out = []
    for n, y, x in vals:
        if n <= 0:
            out.append(np.array([0.0, (H - 1) / 2.0, (W - 1) / 2.0]))
        else:
            out.append(np.array([float(n), float(y) / float(n), float(x) / float(n)]))
    return out


def _area_frac(t, a, b, dev):
    """``area_frac``: 前景画素の割合。"""
    m = _bin_t(t)
    B, H, W = m.shape
    if H * W == 0:
        return _per_image_cpu("area_frac", t, a, b)
    n = m.to(torch.int64).sum(dim=(1, 2)).cpu().numpy()
    return [np.float64(np.float64(int(k)) / np.float64(H * W)) for k in n]


def _largest_crop_feature(core):
    """最大の成分(4 連結)を GPU で求め、余白つきで切り出して op 自身の CPU の式へ渡す。

    切り出す窓は外接矩形を余白だけ広げ、**画像の内側に切る**(画像の縁で切れる所は CPU でも縁)。
    余白は 1 画素(収縮の縁の扱い ``border_value=0`` を保つ)。``rectangularity`` だけは同じモーメントの
    矩形を画像の中に描いて重ねるので、矩形が窓に収まる余白(外接矩形の対角線の長さ)を取る —— 重心から
    矩形の角までは ``sqrt(3(λ1+λ2))`` で、``λ1+λ2`` は外接矩形の中の点の分散なので対角線の半分の 2 乗以下。
    """
    def fn(t, a, b, dev):
        m = _bin_t(t)
        B, H, W = m.shape
        N = B * H * W
        HW = H * W
        cpu = _cpu_op(core)
        L, fidx = label(m, 4)
        if fidx.numel() == 0:
            return [cpu(np.zeros((H, W)), a, b) for _ in range(B)]
        big = _largest_roots(L, fidx, N, HW, B)
        sel = L.view(-1)[fidx]
        hit = big[fidx // HW] == sel                       # 最大の成分の画素
        p = fidx[hit]
        img = p // HW
        yy = (p % HW) // W
        xx = p % W
        inf = torch.full((B,), N, dtype=torch.int64, device=t.device)
        neg = torch.full((B,), -1, dtype=torch.int64, device=t.device)
        box = torch.stack([inf.clone().scatter_reduce(0, img, yy, "amin"),
                           neg.clone().scatter_reduce(0, img, yy, "amax"),
                           inf.clone().scatter_reduce(0, img, xx, "amin"),
                           neg.clone().scatter_reduce(0, img, xx, "amax")], 1).cpu().numpy()
        crops = []
        for i in range(B):
            r0, r1, c0, c1 = (int(v) for v in box[i])
            if r1 < 0:
                crops.append(None)
                continue
            pad = 1
            if core == "rectangularity":
                pad = int(np.ceil(np.hypot(r1 - r0 + 1, c1 - c0 + 1))) + 2
            r0, c0 = max(0, r0 - pad), max(0, c0 - pad)
            r1, c1 = min(H - 1, r1 + pad), min(W - 1, c1 + pad)
            sub = (L[i, r0:r1 + 1, c0:c1 + 1] == big[i]).cpu().numpy()
            crops.append(sub.astype(np.float64))
        return [cpu(c, a, b) if c is not None else cpu(np.zeros((H, W)), a, b) for c in crops]
    fn.__name__ = "_largest_crop"
    return fn

# ---- 最大の成分の形の特徴を GPU の上で(2026-11-03 第 2 便) ---------------------------------------
# 最初の版は最大の成分を切り出して op 自身の CPU の式へ渡していた。最大の成分が画像の大半を占める入力
# (spiral / blobs)では CPU の式が全体と同じ重さになり 0.67〜0.91 倍で不採用だった。ここでは重い部分
# (収縮・輪郭の画素・モーメントの和・穴の数え上げ)を GPU で行い、**最後の式だけ** CPU の同じ関数に通す:
#
# * 整数で決まる量(面積・外接矩形・境界画素の数・周囲長の符号のヒストグラム・穴の面積)は GPU で数えて
#   完全一致。周囲長はヒストグラム(50 本)と重みの内積を CPU で skimage と同じ式で取る(bit 一致)。
# * 重心から輪郭画素までの距離(circularity / roundness)は輪郭画素の座標(行優先)を戻し、CPU と同じ
#   numpy の式で距離・最大・平均・標準偏差を取る(bit 一致)。
# * モーメント(7 種と、regionprops の向き・軸長)は float64 の行列積で中心モーメントまでを GPU で求め、
#   正規化・Hu・慣性テンソル・固有値は skimage の関数そのものに通す。和の順序だけが違う(相対 1e-12 程度)。
#
# skimage の無い環境(numpy の双子で答える CPU)では CPU の op をそのまま呼ぶ。


def _skimage():
    import backends_auto
    return backends_auto._HAS_SK


def _erode4(x):
    """``ndimage.binary_erosion(x)``(十字の構造要素、``border_value=0``)。x = (B,H,W) bool。"""
    P = F.pad(x.to(torch.uint8), (1, 1, 1, 1), value=0).bool()
    return x & P[:, :-2, 1:-1] & P[:, 2:, 1:-1] & P[:, 1:-1, :-2] & P[:, 1:-1, 2:]


def _largest_mask(t):
    """``(big, has)``: 1 枚ごとの最大の 4 連結成分のマスク (B,H,W) と、成分があるか (B,) の np.bool_。"""
    m = _bin_t(t)
    B, H, W = m.shape
    N = B * H * W
    L, fidx = label(m, 4)
    if fidx.numel() == 0:
        return torch.zeros_like(m), np.zeros(B, bool)
    big = _largest_roots(L, fidx, N, H * W, B)
    has = (big >= 0)
    mask = (L == big.view(B, 1, 1)) & has.view(B, 1, 1)
    return mask, has.cpu().numpy()


def _empty_value(core, H, W, a, b):
    return _cpu_op(core)(np.zeros((H, W)), a, b)


def _gpu_feature(core, per_image):
    """``per_image(big_i, i) -> 値`` を成分のある枚に当て、無い枚は CPU の op の空の答え。"""
    def fn(t, a, b, dev):
        if not _skimage():
            return _per_image_cpu(core, t, a, b)
        big, has = _largest_mask(t)
        B, H, W = big.shape
        return [per_image(big[i], a, b) if has[i] else _empty_value(core, H, W, a, b) for i in range(B)]
    fn.__name__ = "_gpu_feature"
    return fn


def _bbox(big_i):
    rows = torch.nonzero(big_i.any(dim=1)).squeeze(1)
    cols = torch.nonzero(big_i.any(dim=0)).squeeze(1)
    return int(rows[0]), int(rows[-1]), int(cols[0]), int(cols[-1])


def _area(big_i) -> int:
    return int(big_i.sum())


def _contour_coords(big_i):
    """``_contour_pixels`` の画素の (行, 列)(行優先の順、np.int64)。"""
    c = big_i & ~_erode4(big_i[None])[0]
    yx = torch.nonzero(c).cpu().numpy()
    return yx[:, 0], yx[:, 1]


def _all_coords(big_i):
    yx = torch.nonzero(big_i).cpu().numpy()
    return yx[:, 0], yx[:, 1]


def _centre_distances_gpu(big_i):
    """``backends_auto._centre_distances`` と同じ値(重心は整数の和から、距離は numpy で)。"""
    area = _area(big_i)
    if area <= 0:
        return None, 0.0
    H, W = big_i.shape
    ys = torch.arange(H, device=big_i.device, dtype=torch.int64)
    xs = torch.arange(W, device=big_i.device, dtype=torch.int64)
    bi = big_i.to(torch.int64)
    sy = int((bi.sum(dim=1) * ys).sum())
    sx = int((bi.sum(dim=0) * xs).sum())
    cy, cx = float(np.float64(sy) / np.float64(area)), float(np.float64(sx) / np.float64(area))
    by, bx = _contour_coords(big_i)
    if by.size == 0:
        by, bx = _all_coords(big_i)
    return np.hypot(by - cy, bx - cx), float(area)


def _circularity(big_i, a, b):
    import backends_auto as A
    d, F_ = _centre_distances_gpu(big_i)
    return np.float64(A._halcon_circularity(d, F_))


def _roundness(big_i, a, b):
    import backends_auto as A
    d, _F = _centre_distances_gpu(big_i)
    return np.float64(A._halcon_roundness(d))


_PERIM_WEIGHTS: list = []


def _perimeter_weights():
    if not _PERIM_WEIGHTS:
        import math
        w = np.zeros(50, dtype=np.float64)
        w[[5, 7, 15, 17, 25, 27]] = 1
        w[[21, 33]] = math.sqrt(2)
        w[[13, 23]] = (1 + math.sqrt(2)) / 2
        _PERIM_WEIGHTS.append(w)
    return _PERIM_WEIGHTS[0]


def _perimeter(big_i) -> float:
    """``skimage.measure.perimeter(big, 4)``: 境界画素の 3x3 の符号([[10,2,10],[2,1,2],[10,2,10]])の
    ヒストグラム(GPU、整数)と重みの内積(CPU、skimage と同じ式)。"""
    border = (big_i & ~_erode4(big_i[None])[0]).to(torch.int64)
    P = F.pad(border[None, None].float(), (1, 1, 1, 1), value=0)[0, 0].to(torch.int64)
    code = (P[1:-1, 1:-1] + 2 * (P[:-2, 1:-1] + P[2:, 1:-1] + P[1:-1, :-2] + P[1:-1, 2:])
            + 10 * (P[:-2, :-2] + P[:-2, 2:] + P[2:, :-2] + P[2:, 2:]))
    hist = torch.bincount(code.reshape(-1), minlength=50).cpu().numpy()
    return hist @ _perimeter_weights()


def _contlength(big_i, a, b):
    return np.float64(_perimeter(big_i) or 1.0)


def _compactness(big_i, a, b):
    import backends_auto as A
    per = _perimeter(big_i) or 1.0
    return np.float64(A._halcon_compactness(per, float(_area(big_i))))


def _classify_shape(big_i, a, b):
    """``ops.classify_shape``: ``min(1, 4π面積/境界画素数²)``(境界 = 成分 - 十字の収縮、整数)。"""
    area = float(_area(big_i))
    per = float((big_i & ~_erode4(big_i[None])[0]).sum())
    return np.float64(min(1.0, 4 * np.pi * area / (per * per)) if per > 0 else 0.0)


def _height_width_ratio(big_i, a, b):
    r0, r1, c0, c1 = _bbox(big_i)
    return np.float64((r1 + 1 - r0) / max(c1 + 1 - c0, 1))


def _area_holes(big_i, a, b):
    """``(area_filled - area) / max(area_filled, 1)``。穴 = 補集合の 8 連結成分で画像の縁に触れないもの(regionprops の image_filled は 3x3 の構造要素)
    (外接矩形の切り出しの縁に触れる背景は、矩形の外の背景を通って画像の縁に繋がるので同じ)。"""
    H, W = big_i.shape
    bg = ~big_i
    L, fidx = label(bg[None], 8)
    N = H * W
    edge = torch.zeros((H, W), dtype=torch.bool, device=big_i.device)
    edge[0, :] = True
    edge[-1, :] = True
    edge[:, 0] = True
    edge[:, -1] = True
    outside = torch.zeros(N + 1, dtype=torch.bool, device=big_i.device)
    outside[L[0][edge & bg]] = True
    holes = int((bg & ~outside[L[0]]).sum())
    area = _area(big_i)
    filled = area + holes
    return np.float64((filled - area) / max(filled, 1))


def _moments_raw_central(img64, center=None):
    """skimage ``moments_central(image, center, order=3)`` を float64 の行列積で(2-D)。center=None は
    生のモーメントから重心(skimage と同じ)。"""
    H, W = img64.shape
    dev = img64.device
    r = torch.arange(H, device=dev, dtype=torch.float64)
    c = torch.arange(W, device=dev, dtype=torch.float64)
    p = torch.arange(4, device=dev, dtype=torch.float64)
    if center is None:
        M = (r[:, None] ** p[None, :]).T @ img64 @ (c[:, None] ** p[None, :])
        M = M.cpu().numpy()
        center = (M[1, 0] / M[0, 0], M[0, 1] / M[0, 0])
    pr = (r - float(center[0]))[:, None] ** p[None, :]
    pc = (c - float(center[1]))[:, None] ** p[None, :]
    return (pr.T @ img64 @ pc).cpu().numpy()


def _moment_feature(metric):
    def per_image(big_i, a, b):
        import backends_auto as A
        mu = _moments_raw_central(big_i.to(torch.float64))
        nu = A._moments_normalized(mu)
        hu = A._moments_hu(nu)
        table = {"moment2": abs(nu[2, 0] + nu[0, 2]), "moment3": abs(nu[3, 0] + nu[0, 3]),
                 "moment_central": abs(nu[2, 0] + nu[1, 1] + nu[0, 2]),
                 "hu1": abs(hu[0]), "hu2": abs(hu[1]), "hu3": abs(hu[2]), "hu4": abs(hu[3])}
        return np.float64(float(table[metric]))
    return per_image


class _Props:
    """regionprops の向き・軸長・面積だけを、外接矩形の局所座標のモーメント(GPU)から作る。"""

    def __init__(self, big_i):
        from skimage import measure as skm
        r0, r1, c0, c1 = _bbox(big_i)
        crop = big_i[r0:r1 + 1, c0:c1 + 1].to(torch.float64)
        self.area = float(_area(big_i))
        mu = _moments_raw_central(crop)          # 局所座標・重心は生のモーメントから(regionprops と同じ)
        T = skm.inertia_tensor(np.zeros((2, 2)), mu, spacing=(1.0, 1.0))
        ev = skm.inertia_tensor_eigvals(np.zeros((2, 2)), mu=mu, T=T)
        self.inertia_tensor = T
        self.axis_major_length = 4 * np.sqrt(ev[0])
        self.axis_minor_length = 4 * np.sqrt(ev[-1])
        a_, b_, _b, c_ = T.flat
        if a_ - c_ == 0:
            self.orientation = np.pi / 4.0 if b_ < 0 else -np.pi / 4.0
        else:
            self.orientation = 0.5 * np.arctan2(-2 * b_, c_ - a_)


def _orientation(big_i, a, b):
    pr = _Props(big_i)
    return np.float64((pr.orientation + np.pi / 2) / np.pi)


def _eccentricity(big_i, a, b):
    import backends_auto as A
    pr = _Props(big_i)
    return A._halcon_eccentricity(pr.axis_major_length / 2.0, pr.axis_minor_length / 2.0, pr.area)


def _elliptic_axis(big_i, a, b):
    import backends_auto as A
    return A._ellipse_axes(_Props(big_i))


#: GPU の上で計算する形の特徴(残り 3 op は凸包・最大弦・モーメント矩形の重ね合わせで、CPU の式のまま)。
GPU_SHAPE_FEATURES = {
    "circularity": _circularity, "roundness": _roundness, "contlength": _contlength,
    "compactness": _compactness, "classify_shape": _classify_shape, "height_width_ratio": _height_width_ratio,
    "area_holes": _area_holes, "orientation_region": _orientation, "eccentricity": _eccentricity,
    "elliptic_axis": _elliptic_axis,
    "moments_region_2nd": _moment_feature("moment2"), "moments_region_3rd": _moment_feature("moment3"),
    "moments_region_central": _moment_feature("moment_central"),
    "moments_region_2nd_invar": _moment_feature("hu1"), "moments_region_central_invar": _moment_feature("hu2"),
    "moments_region_2nd_rel_invar": _moment_feature("hu3"), "moments_region_3rd_invar": _moment_feature("hu4"),
}


#: 最大の成分だけを読む形の特徴(``_largest_label`` の後の式が平行移動で変わらないもの)。
LARGEST_CROP_OPS = (
    "circularity", "compactness", "convexity", "rectangularity", "eccentricity", "orientation_region",
    "roundness", "diameter_region", "contlength", "area_holes", "height_width_ratio", "moments_region_2nd",
    "moments_region_2nd_invar", "moments_region_3rd", "moments_region_central", "moments_region_central_invar",
    "moments_region_2nd_rel_invar", "moments_region_3rd_invar", "elliptic_axis", "classify_shape",
)


def table() -> dict:
    """``accel.ACCEL`` に足す行 ``{accel名: (fn, core名, halcon名)}``。"""
    rows = {
        "lbl_remove_small": (_remove_small, "remove_small", "select_shape"),
        "lbl_select_shape": (_select_shape, "select_shape", "select_shape"),
        "lbl_select_largest": (_select_largest_finite, "select_largest", "select_shape_std"),
        "lbl_select_shape_std": (_select_largest, "select_shape_std", "select_shape_std"),
        "lbl_clear_border": (_clear_border, "sk_clear_border", ""),
        "lbl_sort_region": (_sort_region, "r2_sort_region", "sort_region"),
        "lbl_background_seg": (_background_seg, "r3_background_seg", "background_seg"),
        "lbl_select_region_point": (_select_region_point, "r3_select_region_point", "select_region_point"),
        "lbl_fill_up_shape": (_fill_up_shape, "fill_up_shape", "fill_up_shape"),
        "lbl_sk_remove_holes": (_sk_remove_holes, "sk_remove_holes", "fill_up"),
        "lbl_smallest_rectangle1": (_smallest_rectangle1, "smallest_rectangle1", "smallest_rectangle1"),
        "lbl_count_obj": (_count8, "count_obj", "count_obj"),
        "lbl_connect_and_holes": (_count8, "connect_and_holes", "connect_and_holes"),
        "lbl_cv_cc_count": (_cv_cc_count, "cv_cc_count", "connection"),
        "lbl_blob_count": (_blob_count, "blob_count", "count_obj"),
        "lbl_area_center": (_area_center, "area_center", "area_center"),
        "lbl_area_frac": (_area_frac, "area_frac", "area_center"),
    }
    for core in LARGEST_CROP_OPS:
        if core in GPU_SHAPE_FEATURES:
            rows["lbl_" + core] = (_gpu_feature(core, GPU_SHAPE_FEATURES[core]), core, core)
        else:
            rows["lbl_" + core] = (_largest_crop_feature(core), core, core)
    return rows


#: 実測の門を通って ``accel.ACCEL`` に載る core op(RTX 5090、``tools/bench_label_ops.py``、2 回目の測定 =
#: ラベル付けの同期を減らし、形の特徴を GPU の上で計算した版)。``fullseye/data/GPU_ACCEL_USE.json`` の ``use``
#: が立った op と同じ集合であることを門が見る(``tests/test_accel_label.py``)。37 op のうち 34(単独 11)。
#: 不採用の 3 op(``convexity`` / ``diameter_region`` / ``rectangularity``)は凸包・最大弦・モーメント矩形の
#: 重ね合わせを CPU の式のままにしていて、最大の成分が画像の大半を占める入力で常駐でも 1 倍に届かない。
ADOPTED = frozenset({
    "area_center", "area_frac", "area_holes", "blob_count", "circularity",
    "classify_shape", "compactness", "connect_and_holes", "contlength", "count_obj",
    "cv_cc_count", "eccentricity", "elliptic_axis", "fill_up_shape", "height_width_ratio",
    "moments_region_2nd", "moments_region_2nd_invar", "moments_region_2nd_rel_invar", "moments_region_3rd", "moments_region_3rd_invar",
    "moments_region_central", "moments_region_central_invar", "orientation_region", "r2_sort_region", "r3_background_seg",
    "r3_select_region_point", "remove_small", "roundness", "select_largest", "select_shape",
    "select_shape_std", "sk_clear_border", "sk_remove_holes", "smallest_rectangle1",
})


#: 領域 → 特徴・ベクトル の accel 名(``accel.run_batch`` / ``run_pipeline`` は 0..1 に切らず、
#: 1 枚ごとの np の値を返す。鎖では区間の最後にしか置けない)。
REDUCERS = frozenset({"lbl_count_obj", "lbl_connect_and_holes", "lbl_cv_cc_count", "lbl_blob_count",
                      "lbl_area_center", "lbl_area_frac"} | {"lbl_" + c for c in LARGEST_CROP_OPS})
