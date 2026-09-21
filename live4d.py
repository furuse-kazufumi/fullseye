# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""live4d —— 生きている組織の 3D+t(x, y, z, t)を古典手法だけで「短い 3D 動画像」にする op 族。

動画生成 AI は「もっともらしい動き」を発明する。ここでは内容を発明しない代わりに、

* 実在する微小な動きを見える量に**増幅**する(Eulerian の線形拡大、Wu et al. SIGGRAPH 2012)
* 体積の間の**変位場**を測り(Lucas–Kanade の n 次元版)、粒子を流して**軌跡**を時刻の色で描く
* 短い実測の**時間を滑らかに埋める**(前後の流れで合成する中間フレーム、遮蔽は往復の一致で検出)
* 焦点掃引の時系列から**高さ場の動画**を起こす(合焦度の最大、放物線で副ボクセル)
* 物理で**生成**する(既知の半径則で拍動する殻、既知の速さで分かれる塊 = 真値つきの入力)

のどれもが説明可能で、真値つきの合成系列で数値検証できる。

型は既存の語彙に 1 語だけ足す: ``volseq`` = 体積の時系列 ``(T, Z, Y, X)``(T >= 2)。``video`` (T, H, W) と
``voxel`` (Z, Y, X) は既存。``volseq`` を ``video`` に畳む op(``volseq_mip_video`` / ``volseq_cut_video``)が
あるので、この先は videocube(空間 × 時間の立方体)にそのまま流れる。分ける基準は repo 共通の 1 つ ——
``volseq`` を ``voxel`` として渡すと ndim が違って例外になる(黙って間違わない)が、``video`` (T, H, W) と
``voxel`` (Z, Y, X) は形が同じで「時間軸を奥行きと読む」のが videocube の設計なので、そこは分けない。

全 op は numpy + scipy のみ(``scene_flow_lk`` の torch 版に対する numpy の対応物が ``vol_flow_3d``)。
入力は fail-closed(形・有限性・範囲を検査して ValueError)。
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy import ndimage as ndi

import videocube
from videocube import _count, _finite, _time_colors, _unit

__all__ = [
    "MAX_SERIES_ELEMENTS",
    "volseq_synth_beating", "volseq_synth_dividing",
    "volseq_mip_video", "volseq_cut_video",
    "vol_flow_3d", "volseq_speed", "volseq_pathline_render", "volseq_pathline_orbit",
    "video_interpolate_flow", "volseq_interpolate_flow", "volseq_magnify_motion",
    "volseq_render_orbit", "focus_sweep_height_video", "focus_sweep_surface_video",
]

#: 体積の時系列の上限要素数(float64 で 512 MB)。超えたら ValueError(黙って間引かない)。
MAX_SERIES_ELEMENTS = 2 ** 26


# --------------------------------------------------------------------------- #
# 検査                                                                          #
# --------------------------------------------------------------------------- #
def _series(x: Any, op: str, name: str = "volseq", min_t: int = 2) -> np.ndarray:
    if isinstance(x, (list, tuple)):
        vols = [np.asarray(v, dtype=np.float64) for v in x]
        if not vols or any(v.ndim != 3 or v.shape != vols[0].shape for v in vols):
            raise ValueError(f"{op}: {name} frames must all be the same (Z, Y, X) shape")
        a = np.stack(vols, axis=0)
    else:
        a = np.asarray(x, dtype=np.float64)
    if a.ndim != 4 or a.size == 0:
        raise ValueError(f"{op}: {name} must be a volume series (T, Z, Y, X), got shape {a.shape}")
    if a.shape[0] < min_t or min(a.shape[1:]) < 2:
        raise ValueError(f"{op}: {name} needs T >= {min_t} and Z, Y, X >= 2, got shape {a.shape}")
    if a.size > MAX_SERIES_ELEMENTS:
        raise ValueError(f"{op}: {name} has {a.size} elements > MAX_SERIES_ELEMENTS={MAX_SERIES_ELEMENTS}")
    if not np.isfinite(a).all():
        raise ValueError(f"{op}: {name} must be finite")
    return a


def _vol(x: Any, op: str, name: str) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    if a.ndim != 3 or a.size == 0 or min(a.shape) < 2:
        raise ValueError(f"{op}: {name} must be a (Z, Y, X) volume with every side >= 2, got shape {a.shape}")
    if a.size > MAX_SERIES_ELEMENTS:
        raise ValueError(f"{op}: {name} has {a.size} elements > MAX_SERIES_ELEMENTS={MAX_SERIES_ELEMENTS}")
    if not np.isfinite(a).all():
        raise ValueError(f"{op}: {name} must be finite")
    return a


def _shape3(shape: Any, op: str) -> tuple[int, int, int]:
    try:
        vals = list(shape)
    except TypeError:
        raise ValueError(f"{op}: shape must be three integers (Z, Y, X), got {shape!r}") from None
    if (len(vals) != 3 or any(isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) for v in vals)
            or min(int(v) for v in vals) < 4):
        raise ValueError(f"{op}: shape must be three integers >= 4 (Z, Y, X), got {shape!r}")
    return tuple(int(v) for v in vals)  # type: ignore[return-value]


def _seeded(seed: Any, op: str) -> np.random.Generator:
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)):
        raise ValueError(f"{op}: seed must be an integer, got {seed!r}")
    return np.random.default_rng(int(seed))


# --------------------------------------------------------------------------- #
# 合成の生成源(真値つき)                                                        #
# --------------------------------------------------------------------------- #
def volseq_synth_beating(shape=(24, 32, 32), n_frames: int = 24, period: float = 12.0, amplitude: float = 2.0,
                         radius: float = 8.0, thickness: float = 1.5, noise: float = 0.0, seed: int = 0) -> np.ndarray:
    """既知の半径則で拍動する殻の体積時系列 ``(T, Z, Y, X)``(``volseq``、値は [0, 1] + 雑音)。

    半径は ``r(t) = radius + amplitude · sin(2π t / period)``(t はフレーム番号)、殻は中心からの距離 d に
    対する ``exp(−(d − r(t))² / (2 · thickness²))``。鼓動する心筋や収縮する細胞の最小モデルで、
    **真値 = 半径則そのもの**なので、増幅・補間・描画の各 op を「半径の読み取り」で数値検証できる。
    ``noise`` > 0 なら正規雑音(標準偏差)を足す(``seed`` で再現)。

    >>> s = volseq_synth_beating((16, 24, 24), n_frames=12, period=12.0, amplitude=1.0)
    >>> s.shape
    (12, 16, 24, 24)
    """
    op = "volseq_synth_beating"
    Z, Y, X = _shape3(shape, op)
    T = _count(n_frames, op, "n_frames", 2, 4096)
    P = _finite(period, op, "period", lo=1e-9)
    A = _finite(amplitude, op, "amplitude", lo=0.0)
    R = _finite(radius, op, "radius", lo=0.0)
    th = _finite(thickness, op, "thickness", lo=1e-9)
    ns = _finite(noise, op, "noise", lo=0.0)
    if T * Z * Y * X > MAX_SERIES_ELEMENTS:
        raise ValueError(f"{op}: {T}x{Z}x{Y}x{X} exceeds MAX_SERIES_ELEMENTS={MAX_SERIES_ELEMENTS}")
    rng = _seeded(seed, op)
    zz, yy, xx = np.meshgrid(np.arange(Z) - (Z - 1) / 2.0, np.arange(Y) - (Y - 1) / 2.0,
                             np.arange(X) - (X - 1) / 2.0, indexing="ij")
    d = np.sqrt(zz ** 2 + yy ** 2 + xx ** 2)
    out = np.empty((T, Z, Y, X), dtype=np.float64)
    for t in range(T):
        r = R + A * np.sin(2.0 * np.pi * t / P)
        out[t] = np.exp(-(d - r) ** 2 / (2.0 * th ** 2))
    if ns > 0.0:
        out += rng.normal(0.0, ns, size=out.shape)
    return out


def volseq_synth_dividing(shape=(24, 32, 32), n_frames: int = 24, split_frame: int = 8, speed: float = 0.5,
                          sigma: float = 2.5, axis: int = 3, noise: float = 0.0, seed: int = 0) -> np.ndarray:
    """既知の速さで二つに分かれる塊の体積時系列 ``(T, Z, Y, X)``(``volseq``)。

    ``split_frame`` までは中心に 1 つのガウス塊(標準偏差 ``sigma``)、それ以降は 2 つの塊が ``axis``
    (1 = z, 2 = y, 3 = x)に沿って ``±speed · (t − split_frame)`` voxel ずつ離れる(細胞分裂の最小モデル)。
    **真値 = 中心の位置**なので、流れ(``vol_flow_3d``)は ``±speed`` の並進、軌跡は直線になるはず。

    >>> s = volseq_synth_dividing((16, 24, 24), n_frames=12, split_frame=4, speed=0.5)
    >>> s.shape
    (12, 16, 24, 24)
    """
    op = "volseq_synth_dividing"
    Z, Y, X = _shape3(shape, op)
    T = _count(n_frames, op, "n_frames", 2, 4096)
    ts = _count(split_frame, op, "split_frame", 0, T - 1)
    v = _finite(speed, op, "speed", lo=0.0)
    sg = _finite(sigma, op, "sigma", lo=1e-9)
    ax = _count(axis, op, "axis", 1, 3)
    ns = _finite(noise, op, "noise", lo=0.0)
    if T * Z * Y * X > MAX_SERIES_ELEMENTS:
        raise ValueError(f"{op}: {T}x{Z}x{Y}x{X} exceeds MAX_SERIES_ELEMENTS={MAX_SERIES_ELEMENTS}")
    rng = _seeded(seed, op)
    grids = np.meshgrid(np.arange(Z) - (Z - 1) / 2.0, np.arange(Y) - (Y - 1) / 2.0,
                        np.arange(X) - (X - 1) / 2.0, indexing="ij")
    out = np.empty((T, Z, Y, X), dtype=np.float64)
    for t in range(T):
        off = v * max(t - ts, 0)
        if off == 0.0:
            d2 = grids[0] ** 2 + grids[1] ** 2 + grids[2] ** 2
            out[t] = np.exp(-d2 / (2.0 * sg ** 2))
        else:
            acc = np.zeros((Z, Y, X))
            for sign in (-1.0, 1.0):
                d2 = sum((g - (sign * off if i == ax - 1 else 0.0)) ** 2 for i, g in enumerate(grids))
                acc += np.exp(-d2 / (2.0 * sg ** 2))
            out[t] = acc
    if ns > 0.0:
        out += rng.normal(0.0, ns, size=out.shape)
    return out


# --------------------------------------------------------------------------- #
# 系列 → 動画(videocube への橋)                                                 #
# --------------------------------------------------------------------------- #
def volseq_mip_video(volseq, axis: int = 1) -> np.ndarray:
    """体積時系列を軸 ``axis``(1 = z, 2 = y, 3 = x)の最大値投影で動画 ``(T, H, W)`` に畳む(``video``)。

    畳んだ先は ``video_spacetime_cube`` / ``video_cube_cut`` / ``motion_magnify`` など 2D+t の op がそのまま
    使える。最大値投影は「奥行きのどこかにあれば見える」投影なので、重なりは失われる(何を失ったかは
    ``volseq_cut_video`` の断面と見比べる)。
    """
    op = "volseq_mip_video"
    S = _series(volseq, op)
    ax = _count(axis, op, "axis", 1, 3)
    return S.max(axis=ax)


def volseq_cut_video(volseq, plane: str = "xy", position: float = 0.5) -> np.ndarray:
    """体積時系列を 1 枚の断面で切った動画 ``(T, H, W)``(``video``)。

    ``plane`` は ``"xy"``(z を固定)/ ``"xz"``(y を固定)/ ``"yz"``(x を固定)、``position`` は固定する
    軸に沿った相対位置 [0, 1]。断面は最大値投影と違って重なりを失わないが、断面から外れた動きは見えない。
    """
    op = "volseq_cut_video"
    S = _series(volseq, op)
    if plane not in ("xy", "xz", "yz"):
        raise ValueError(f"{op}: plane must be 'xy', 'xz' or 'yz', got {plane!r}")
    p = _finite(position, op, "position", lo=0.0, hi=1.0)
    axis = {"xy": 1, "xz": 2, "yz": 3}[plane]
    idx = int(round(p * (S.shape[axis] - 1)))
    return np.take(S, idx, axis=axis)


# --------------------------------------------------------------------------- #
# 流れ(n 次元 Lucas–Kanade、ピラミッド + warp)                                  #
# --------------------------------------------------------------------------- #
def _warp(img: np.ndarray, flow: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """``img(x + scale · flow(x))`` を三線形(二重線形)補間で拾う。端は最近傍の値で埋める。"""
    grids = np.meshgrid(*[np.arange(n, dtype=np.float64) for n in img.shape], indexing="ij")
    coords = np.stack([g + scale * f for g, f in zip(grids, flow)], axis=0)
    return ndi.map_coordinates(img, coords, order=1, mode="nearest")


def _resize(a: np.ndarray, shape: tuple[int, ...]) -> np.ndarray:
    if a.shape == tuple(shape):
        return a
    return ndi.zoom(a, [s / float(n) for s, n in zip(shape, a.shape)], order=1, mode="nearest", grid_mode=True)


def _lk_flow_nd(a: np.ndarray, b: np.ndarray, win: int, pyr_levels: int, iters: int, reg: float) -> np.ndarray:
    """``b(x) ≈ a(x − d)`` となる密な変位場 d ``(ndim, *shape)`` を、窓内最小二乗の Lucas–Kanade で解く。

    ピラミッド(各段 1/2、``pyr_levels`` 段)の粗い側から、現在の d で ``b`` を引き戻した ``Iw(x) = b(x + d)``
    と ``a`` の差 ``It`` を、``∇Iw · Δd = −It`` の窓和最小二乗(構造テンソル + 対角の正則化 ``reg``)で
    Gauss–Newton 反復する。1 反復の更新は各軸 ±2 に抑える(発散防止)。
    """
    nd = a.ndim
    size = 2 * win + 1
    # ピラミッド: 最小辺が 4 を割る段は作らない
    shapes = [a.shape]
    while len(shapes) < pyr_levels and min(shapes[-1]) >= 8:
        shapes.append(tuple(max(4, n // 2) for n in shapes[-1]))
    pyr_a = [a] + [_resize(ndi.gaussian_filter(a, 1.0), s) for s in shapes[1:]]
    pyr_b = [b] + [_resize(ndi.gaussian_filter(b, 1.0), s) for s in shapes[1:]]
    flow = np.zeros((nd,) + shapes[-1], dtype=np.float64)
    eye = np.eye(nd)
    for lv in range(len(shapes) - 1, -1, -1):
        A, B = pyr_a[lv], pyr_b[lv]
        if flow.shape[1:] != A.shape:
            ratio = np.array(A.shape, dtype=np.float64) / np.array(flow.shape[1:], dtype=np.float64)
            flow = np.stack([_resize(flow[i], A.shape) * ratio[i] for i in range(nd)], axis=0)
        for _ in range(iters):
            Iw = _warp(B, flow)
            It = Iw - A
            grads = np.gradient(0.5 * (Iw + A))
            # 構造テンソルと右辺の窓和
            G = np.empty(A.shape + (nd, nd))
            rhs = np.empty(A.shape + (nd,))
            for i in range(nd):
                rhs[..., i] = -ndi.uniform_filter(grads[i] * It, size=size, mode="nearest")
                for j in range(i, nd):
                    gij = ndi.uniform_filter(grads[i] * grads[j], size=size, mode="nearest")
                    G[..., i, j] = gij
                    G[..., j, i] = gij
            G += reg * eye
            delta = np.linalg.solve(G, rhs[..., None])[..., 0]           # (*shape, nd)
            delta = np.clip(delta, -2.0, 2.0)
            flow = flow + np.moveaxis(delta, -1, 0)
    return flow


def vol_flow_3d(vol_a, vol_b, win: int = 3, pyr_levels: int = 3, iters: int = 5, reg: float = 1e-3) -> np.ndarray:
    """2 つの体積の間の密な変位場 ``(3, Z, Y, X)``(``flow_dense``、成分 dz, dy, dx [voxel])。

    ``vol_b(x) ≈ vol_a(x − d)``、つまり ``vol_a`` の構造が ``+d`` 動いて ``vol_b`` になる(torch 版
    ``scene_flow_lk`` と同じ約束)。Lucas–Kanade の 3 次元版を numpy + scipy だけで: ``win`` は窓の半幅
    (窓は一辺 2·win + 1)、``pyr_levels`` はピラミッド段数(大変位ほど増やす、各段 1/2)、``iters`` は各段の
    warp 反復、``reg`` は構造テンソル対角の正則化(平坦部の 0 除算回避。大きいほど平坦部の流れが 0 に寄る)。
    テクスチャの無い平坦部では流れは決まらない(開口問題)—— 信じるのは勾配のある場所だけ。

    >>> a = volseq_synth_dividing((16, 24, 24), n_frames=4, split_frame=0, speed=1.0)
    >>> d = vol_flow_3d(a[1], a[2]); d.shape
    (3, 16, 24, 24)
    """
    op = "vol_flow_3d"
    A = _vol(vol_a, op, "vol_a")
    B = _vol(vol_b, op, "vol_b")
    if A.shape != B.shape:
        raise ValueError(f"{op}: vol_a and vol_b must share one shape, got {A.shape} vs {B.shape}")
    w = _count(win, op, "win", 1, 16)
    lv = _count(pyr_levels, op, "pyr_levels", 1, 8)
    it = _count(iters, op, "iters", 1, 50)
    rg = _reg(reg, op)
    return _lk_flow_nd(A, B, w, lv, it, rg)


def _reg(reg: Any, op: str) -> float:
    """構造テンソル対角の正則化は**正**でなければならない(0 だと平坦部で特異行列 → LinAlgError、fail-closed でない)。"""
    rg = _finite(reg, op, "reg", lo=0.0)
    if rg <= 0.0:
        raise ValueError(f"{op}: reg must be > 0 (a flat window makes the structure tensor singular), got {rg}")
    return rg


def _series_flows(S: np.ndarray, win: int, pyr_levels: int, iters: int, reg: float) -> np.ndarray:
    return np.stack([_lk_flow_nd(S[t], S[t + 1], win, pyr_levels, iters, reg) for t in range(S.shape[0] - 1)], axis=0)


def volseq_speed(volseq, win: int = 3, pyr_levels: int = 3, iters: int = 5, reg: float = 1e-3) -> np.ndarray:
    """体積時系列の隣り合うフレーム間の**速さ** ``|d|`` [voxel/frame] を ``(T − 1, Z, Y, X)`` で返す(``volseq``)。

    各フレーム対に ``vol_flow_3d`` を当てた大きさ。どこが・いつ動いたかの地図で、``volseq_render_orbit(mode="speed")``
    の色もこれ。T >= 3 が要る(返りも ``volseq`` = T − 1 >= 2 枚)。
    """
    op = "volseq_speed"
    S = _series(volseq, op, min_t=3)
    w = _count(win, op, "win", 1, 16)
    lv = _count(pyr_levels, op, "pyr_levels", 1, 8)
    it = _count(iters, op, "iters", 1, 50)
    rg = _reg(reg, op)
    F = _series_flows(S, w, lv, it, rg)
    return np.sqrt((F ** 2).sum(axis=1))


def _sample_flow(flow: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """(3, Z, Y, X) の流れを点 (N, 3) で三線形に拾う → (N, 3)。"""
    return np.stack([ndi.map_coordinates(flow[i], pts.T, order=1, mode="nearest") for i in range(3)], axis=1)


def _pathline_cubes(S: np.ndarray, n_seeds: int, win: int, pyr_levels: int, iters: int, reg: float,
                    seed: int, trail_sigma: float, min_speed: float, min_intensity: float):
    """粒子を流して軌跡を立方体に描く → (不透明度 (Z,Y,X), 色 (Z,Y,X,3), 軌跡 (N, T, 3), 静止の灰 (Z,Y,X))。"""
    T = S.shape[0]
    F = _series_flows(S, win, pyr_levels, iters, reg)                      # (T-1, 3, Z, Y, X)
    speed0 = np.sqrt((F ** 2).sum(axis=1)).max(axis=0)                     # どこかの時刻で動いた場所
    # 種は「動いていて、かつ構造のある(明るい)」場所にだけ撒く —— 平坦部の流れは決まらず(開口問題)、
    # ピラミッドの粗い段の推定が残るので、速さだけで選ぶと真っ暗な隅にも種が落ちて立方体が軌跡で埋まる
    lo, hi = np.percentile(S[0], 1.0), np.percentile(S[0], 99.5)
    bright = S[0] >= lo + min_intensity * (hi - lo) if hi > lo else np.ones(S.shape[1:], bool)
    rng = np.random.default_rng(seed)
    cand = np.argwhere((speed0 >= min_speed) & bright)
    if len(cand) == 0:
        raise ValueError("volseq_pathline: nothing bright (>= min_intensity=%g of the range) moves faster than "
                         "min_speed=%g voxel/frame — lower one of them" % (min_intensity, min_speed))
    pick = cand[rng.choice(len(cand), size=min(n_seeds, len(cand)), replace=False)].astype(np.float64)
    pick += rng.uniform(-0.5, 0.5, size=pick.shape)
    tracks = np.empty((len(pick), T, 3))
    tracks[:, 0] = pick
    alive = np.ones(len(pick), bool)
    last = np.full(len(pick), T - 1)                                       # 各粒子の軌跡が終わるフレーム
    thr = lo + min_intensity * (hi - lo)
    for t in range(T - 1):
        p = tracks[:, t]
        # F[t] は「p の中身が p + d(p) へ動く」1 コマぶんの変位場(速度場ではない)ので、写像そのものを使う。
        # 中点法にすると d(x) = x のような場で 2p でなく 2.5p へ飛ぶ(Codex の指摘 2026-09-21、検証済み)
        q = p + _sample_flow(F[t], p)
        # 明るい所(構造のある所)を出た粒子はそこで止める —— 平坦部の流れは決まらないので、
        # 追い続けると偽の流れに乗って軌跡が立方体中に伸びる(実測)
        val = ndi.map_coordinates(S[t + 1], q.T, order=1, mode="nearest")
        died = alive & (val < thr)
        last[died] = t
        alive &= ~died
        tracks[:, t + 1] = np.where(alive[:, None], q, p)
    dims = np.array(S.shape[1:], dtype=np.float64)
    alpha = np.zeros(S.shape[1:])
    col = np.zeros(S.shape[1:] + (3,))
    tcol = _time_colors(T)
    # 線分を細かく刻んで点を撒く(端は落とす)
    for t in range(T - 1):
        live = last > t
        if not live.any():
            break
        p0, p1 = tracks[live, t], tracks[live, t + 1]
        n_sub = int(np.ceil(np.abs(p1 - p0).max())) * 2 + 1
        for s in np.linspace(0.0, 1.0, n_sub, endpoint=False):
            q = p0 + s * (p1 - p0)
            c = tcol[t] * (1.0 - s) + tcol[t + 1] * s
            qi = np.rint(q).astype(int)
            ok = ((qi >= 0) & (qi < dims)).all(axis=1)
            qi = qi[ok]
            alpha[qi[:, 0], qi[:, 1], qi[:, 2]] = 1.0
            col[qi[:, 0], qi[:, 1], qi[:, 2]] = c
    if trail_sigma > 0.0:
        alpha_s = ndi.gaussian_filter(alpha, trail_sigma)
        colw = np.stack([ndi.gaussian_filter(col[..., i] * alpha, trail_sigma) for i in range(3)], axis=-1)
        col = np.where(alpha_s[..., None] > 1e-9, colw / np.maximum(alpha_s, 1e-9)[..., None], 0.0)
        alpha = alpha_s / max(float(alpha_s.max()), 1e-9)
    grey = _unit(S[0])
    return np.clip(alpha, 0.0, 1.0), np.clip(col, 0.0, 1.0), tracks, grey


def _pathline_args(op, volseq, n_seeds, win, pyr_levels, iters, reg, seed, trail_sigma, min_speed, min_intensity):
    S = _series(volseq, op, min_t=3)
    return (S, _count(n_seeds, op, "n_seeds", 1, 100000), _count(win, op, "win", 1, 16),
            _count(pyr_levels, op, "pyr_levels", 1, 8), _count(iters, op, "iters", 1, 50),
            _reg(reg, op), int(_count(seed, op, "seed", 0)),
            _finite(trail_sigma, op, "trail_sigma", lo=0.0), _finite(min_speed, op, "min_speed", lo=0.0),
            _finite(min_intensity, op, "min_intensity", lo=0.0, hi=1.0))


def volseq_pathline_render(volseq, n_seeds: int = 200, yaw: float = 35.0, pitch: float = 25.0, size: int = 256,
                           static_alpha: float = 0.03, win: int = 3, pyr_levels: int = 3, iters: int = 5,
                           reg: float = 1e-3, seed: int = 0, trail_sigma: float = 0.7,
                           min_speed: float = 0.1, min_intensity: float = 0.3) -> np.ndarray:
    """粒子を流れに乗せて描いた**軌跡の立体** ``(size, size, 3)``(``rgb``)—— 動きを 1 枚の静止画で見せる。

    隣り合うフレームの変位場(``vol_flow_3d``)で、動いていて(速さ >= ``min_speed``)かつ明るい(最初の
    フレームの値域の ``min_intensity`` 以上 = 構造のある)場所から撒いた ``n_seeds`` 個の粒子を変位場の写像どおりに移流し、
    軌跡を**時刻の色**(青 = 始め → 赤 = 終わり)で立方体に描いて ``vol_render_transfer`` で任意視点から
    合成する。``static_alpha`` > 0 なら最初のフレームの明るさを薄い灰で重ねる(どこを流れたかの手掛かり)。
    ``trail_sigma`` は軌跡の太さ(voxel)。テクスチャの無い場所の流れは決まらない(開口問題)ので、
    種を明るい場所に限る —— 速さだけで選ぶと真っ暗な隅にも種が落ちて立方体が軌跡で埋まる(実測)。
    """
    op = "volseq_pathline_render"
    args = _pathline_args(op, volseq, n_seeds, win, pyr_levels, iters, reg, seed, trail_sigma, min_speed, min_intensity)
    alpha, col, _tracks, grey = _pathline_cubes(*args)
    return videocube.vol_render_transfer(alpha, color=col, yaw=yaw, pitch=pitch, size=size,
                                         static_alpha=static_alpha, static_color=grey)


def volseq_pathline_orbit(volseq, n_frames: int = 36, n_seeds: int = 200, pitch: float = 25.0, size: int = 256,
                          yaw_start: float = 0.0, yaw_span: float = 360.0, static_alpha: float = 0.03,
                          win: int = 3, pyr_levels: int = 3, iters: int = 5, reg: float = 1e-3, seed: int = 0,
                          trail_sigma: float = 0.7, min_speed: float = 0.1, min_intensity: float = 0.3) -> np.ndarray:
    """``volseq_pathline_render`` の軌跡の立体を回して見る ``(n_frames, size, size, 3)``(``rgbvideo``)。

    流れと軌跡は 1 回だけ計算し、視点だけを ``yaw_start`` から ``yaw_span`` 度ぶん回す。``video_write_gif`` で
    そのまま GIF に書ける。
    """
    op = "volseq_pathline_orbit"
    nf = _count(n_frames, op, "n_frames", 1, 4096)
    y0 = _finite(yaw_start, op, "yaw_start")
    ys = _finite(yaw_span, op, "yaw_span")
    args = _pathline_args(op, volseq, n_seeds, win, pyr_levels, iters, reg, seed, trail_sigma, min_speed, min_intensity)
    alpha, col, _tracks, grey = _pathline_cubes(*args)
    frames = [videocube.vol_render_transfer(alpha, color=col, yaw=y0 + ys * i / nf, pitch=pitch, size=size,
                                            static_alpha=static_alpha, static_color=grey) for i in range(nf)]
    return np.stack(frames, axis=0)


# --------------------------------------------------------------------------- #
# 時間 —— 補間と増幅                                                            #
# --------------------------------------------------------------------------- #
def _interpolate_nd(frames: np.ndarray, factor: int, win: int, pyr_levels: int, iters: int, reg: float,
                    occlusion_tau: float) -> np.ndarray:
    """フレーム列 (T, *shape) を ``factor`` 倍の枚数に(端は元のフレーム、間は前後の流れで合成)。"""
    T = frames.shape[0]
    out = [frames[0]]
    for t in range(T - 1):
        a, b = frames[t], frames[t + 1]
        d_ab = _lk_flow_nd(a, b, win, pyr_levels, iters, reg)          # a の構造が +d_ab 動いて b
        d_ba = _lk_flow_nd(b, a, win, pyr_levels, iters, reg)
        # 往復の一致: a→b→a で戻ってこない場所は遮蔽か推定失敗
        err_a = np.sqrt(((d_ab + _warp_field(d_ba, d_ab)) ** 2).sum(axis=0))
        err_b = np.sqrt(((d_ba + _warp_field(d_ab, d_ba)) ** 2).sum(axis=0))
        for k in range(1, factor):
            s = k / float(factor)
            # 出力位置 x の中身は、a では x − s·d、b では x + (1 − s)·d(b から見た流れで引く)
            fa = _warp(a, d_ab, scale=-s)
            fb = _warp(b, d_ba, scale=-(1.0 - s))
            wa = (1.0 - s) * np.exp(-err_a / occlusion_tau)
            wb = s * np.exp(-err_b / occlusion_tau)
            wsum = wa + wb
            blend = np.where(wsum > 1e-9, (wa * fa + wb * fb) / np.maximum(wsum, 1e-9),
                             a if s < 0.5 else b)
            out.append(blend)
        out.append(b)
    return np.stack(out, axis=0)


def _warp_field(field: np.ndarray, by: np.ndarray) -> np.ndarray:
    """ベクトル場 ``field`` を ``by`` で引き戻す: ``field(x + by(x))``。"""
    return np.stack([_warp(field[i], by) for i in range(field.shape[0])], axis=0)


def video_interpolate_flow(video, factor: int = 2, win: int = 3, pyr_levels: int = 3, iters: int = 3,
                           reg: float = 1e-3, occlusion_tau: float = 1.0) -> np.ndarray:
    """動画 ``(T, H, W)`` を流れで補間して ``(T + (T − 1)(factor − 1), H, W)`` に(``video``、時間の超解像)。

    隣り合うフレーム a, b の間に ``factor − 1`` 枚を、前向きの流れ(a → b)と後ろ向きの流れ(b → a)で
    それぞれ引き戻した像の重みつき平均で作る(流れは**出力画素の位置で**引く近似 —— 場が一様でない所では
    始点で定義された変位を終点で読むずれが出る。厳密には逆写像を解く必要があり、ここではしない)。重みは時刻の近さ × 往復一致(a → b → a で戻る誤差
    ``e`` に対し ``exp(−e / occlusion_tau)``)—— 遮蔽や推定失敗で戻らない場所は、その側の像を信じない。
    大きすぎる変位(ピラミッドで追えない)や新しく現れる物体は補間できず、二重像になる —— 補間は
    「実測の間を埋める」道具で、無いものを発明する道具ではない。真値つきの検証は、2 倍のフレームレートで
    合成 → 半分に間引く → 補間 → 抜いたフレームと比べる(``examples/poc_live4d.py``)。
    """
    op = "video_interpolate_flow"
    V = videocube._video(video, op, min_t=2)
    f = _count(factor, op, "factor", 1, 64)
    w = _count(win, op, "win", 1, 16)
    lv = _count(pyr_levels, op, "pyr_levels", 1, 8)
    it = _count(iters, op, "iters", 1, 50)
    rg = _reg(reg, op)
    tau = _finite(occlusion_tau, op, "occlusion_tau", lo=1e-9)
    if f == 1:
        return V.copy()
    if V.size * f > videocube.MAX_CUBE_ELEMENTS:
        raise ValueError(f"{op}: the interpolated video would have {V.size * f} elements > MAX_CUBE_ELEMENTS")
    return _interpolate_nd(V, f, w, lv, it, rg, tau)


def volseq_interpolate_flow(volseq, factor: int = 2, win: int = 3, pyr_levels: int = 3, iters: int = 5,
                            reg: float = 1e-3, occlusion_tau: float = 1.0) -> np.ndarray:
    """体積時系列 ``(T, Z, Y, X)`` を 3 次元の流れで補間して ``(T + (T − 1)(factor − 1), Z, Y, X)`` に(``volseq``)。

    ``video_interpolate_flow`` と同じ手順の 3 次元版(流れは ``vol_flow_3d``)。ライトシートの z-stack は
    時間方向が粗い(1 体積に秒単位)ので、ここを埋めると「回しながら動く」動画になる。
    """
    op = "volseq_interpolate_flow"
    S = _series(volseq, op)
    f = _count(factor, op, "factor", 1, 64)
    w = _count(win, op, "win", 1, 16)
    lv = _count(pyr_levels, op, "pyr_levels", 1, 8)
    it = _count(iters, op, "iters", 1, 50)
    rg = _reg(reg, op)
    tau = _finite(occlusion_tau, op, "occlusion_tau", lo=1e-9)
    if f == 1:
        return S.copy()
    if S.size * f > MAX_SERIES_ELEMENTS:
        raise ValueError(f"{op}: the interpolated series would have {S.size * f} elements > MAX_SERIES_ELEMENTS")
    return _interpolate_nd(S, f, w, lv, it, rg, tau)


def volseq_magnify_motion(volseq, alpha: float = 10.0, f_lo: float = 0.05, f_hi: float = 0.4, fps: float = 1.0,
                          sigma: float = 0.5) -> np.ndarray:
    """体積時系列の**帯域内の微小な動きを alpha 倍**にする(``volseq``、Eulerian の線形拡大の 3 次元版)。

    Wu et al.(SIGGRAPH 2012)の線形 Eulerian: 各体積を空間ガウス(``sigma``)で平滑化した層を、時間方向に
    帯域通過(``[f_lo, f_hi]`` Hz、``fps`` は体積のフレームレート、FFT の理想帯域)して ``alpha − 1`` 倍を
    元に足し戻す。並進 δ の像 ``I(x − δ(t))`` を 1 次で展開すると帯域内の時間変化は ``−δ · ∇I`` なので、
    足し戻した結果の変位は ``alpha · δ``(``alpha`` は変位の倍率: 1 で恒等、0 で帯域内の動きを消す)。
    成り立つのは **小さな動き**だけ —— 目安は ``alpha · δ < λ / 8``(λ は平滑化後の空間波長 ≈ 4·sigma)。
    それを超えると像が壊れる(増幅でなく歪み)。雑音も同じ倍率で増幅される(SNR は良くならない)。

    >>> s = volseq_synth_beating((16, 24, 24), n_frames=24, period=8.0, amplitude=0.1)
    >>> volseq_magnify_motion(s, alpha=8.0, f_lo=0.08, f_hi=0.2, fps=1.0).shape
    (24, 16, 24, 24)
    """
    op = "volseq_magnify_motion"
    S = _series(volseq, op, min_t=4)
    a = _finite(alpha, op, "alpha")
    lo = _finite(f_lo, op, "f_lo", lo=0.0)
    hi = _finite(f_hi, op, "f_hi", lo=0.0)
    r = _finite(fps, op, "fps", lo=1e-9)
    sg = _finite(sigma, op, "sigma", lo=0.0)
    if not lo < hi <= r / 2.0:
        raise ValueError(f"{op}: need 0 <= f_lo < f_hi <= fps/2, got f_lo={lo}, f_hi={hi}, fps={r}")
    T = S.shape[0]
    L = ndi.gaussian_filter(S, (0.0, sg, sg, sg)) if sg > 0.0 else S
    L = L - L.mean(axis=0, keepdims=True)
    freqs = np.abs(np.fft.rfftfreq(T, d=1.0 / r))
    band = ((freqs >= lo) & (freqs <= hi)).astype(np.float64)
    if band.sum() == 0.0:
        raise ValueError(f"{op}: no FFT bin falls in [{lo}, {hi}] Hz for T={T}, fps={r} — widen the band or add frames")
    B = np.fft.irfft(np.fft.rfft(L, axis=0) * band[:, None, None, None], n=T, axis=0)
    return S + (a - 1.0) * B


# --------------------------------------------------------------------------- #
# 描く                                                                          #
# --------------------------------------------------------------------------- #
def volseq_render_orbit(volseq, n_frames: int = 36, pitch: float = 25.0, yaw_start: float = 0.0,
                        yaw_span: float = 360.0, size: int = 256, mode: str = "intensity", loops: int = 1,
                        percentile: float = 99.5, floor: float = 0.0, opacity_gain: float = 1.0,
                        depth_samples: int | None = None, win: int = 3, pyr_levels: int = 3, iters: int = 5,
                        reg: float = 1e-3) -> np.ndarray:
    """体積時系列を**時間を進めながら視点を回して**描く ``(n_frames, size, size, 3)``(``rgbvideo``)。

    フレーム i は時刻 ``t = (i / n_frames) · T · loops mod T``(隣り合う体積の線形補間)の体積を、
    yaw ``yaw_start + yaw_span · i / n_frames`` から ``vol_render_transfer`` で合成する。不透明度は明るさ
    (系列全体の ``percentile`` で正規化、``floor`` 未満は透明)。``mode="intensity"`` は灰の明るさで、
    ``mode="speed"`` は隣り合うフレーム間の速さ(``volseq_speed``、青 = 遅い → 赤 = 速い)で塗る。
    ``loops`` 周ぶん時間を回すと 1 周の軌道で拍動が何回も見える。``video_write_gif`` でそのまま GIF に。
    """
    op = "volseq_render_orbit"
    S = _series(volseq, op)
    nf = _count(n_frames, op, "n_frames", 1, 4096)
    y0 = _finite(yaw_start, op, "yaw_start")
    ys = _finite(yaw_span, op, "yaw_span")
    lp = _count(loops, op, "loops", 1, 1000)
    pc = _finite(percentile, op, "percentile", lo=0.0, hi=100.0)
    fl = _finite(floor, op, "floor", lo=0.0, hi=1.0)
    g = _finite(opacity_gain, op, "opacity_gain", lo=0.0)
    if mode not in ("intensity", "speed"):
        raise ValueError(f"{op}: mode must be 'intensity' or 'speed', got {mode!r}")
    T = S.shape[0]
    lo = float(S.min())
    hi = float(np.percentile(S, pc))
    A = np.clip((S - lo) / (hi - lo), 0.0, 1.0) if hi > lo else np.zeros_like(S)
    A = np.where(A >= fl, A, 0.0) * g
    A = np.clip(A, 0.0, 1.0)
    C = None
    if mode == "speed":
        w = _count(win, op, "win", 1, 16)
        lv = _count(pyr_levels, op, "pyr_levels", 1, 8)
        it = _count(iters, op, "iters", 1, 50)
        rg = _reg(reg, op)
        if T < 3:
            raise ValueError(f"{op}: mode='speed' needs T >= 3 volumes")
        sp = np.sqrt((_series_flows(S, w, lv, it, rg) ** 2).sum(axis=1))    # (T-1, Z, Y, X)
        sp = np.concatenate([sp, sp[-1:]], axis=0)
        sp = sp / max(float(np.percentile(sp, 99.0)), 1e-9)
        ramp = _time_colors(256)
        C = ramp[np.clip((sp * 255).astype(int), 0, 255)]                  # (T, Z, Y, X, 3)
    frames = []
    for i in range(nf):
        tt = (i / float(nf)) * T * lp
        t0 = int(np.floor(tt)) % T
        t1 = (t0 + 1) % T
        wgt = tt - np.floor(tt)
        vol = A[t0] * (1.0 - wgt) + A[t1] * wgt
        # 色: intensity は明るさの灰(color を渡さないと vol_render_transfer は先頭軸 = z を時刻の色で塗る)
        col = vol if C is None else C[t0] * (1.0 - wgt) + C[t1] * wgt
        frames.append(videocube.vol_render_transfer(vol, color=col, yaw=y0 + ys * i / nf, pitch=pitch, size=size,
                                                    depth_samples=depth_samples, static_alpha=0.0))
    return np.stack(frames, axis=0)


def _focus_heights(S: np.ndarray, w: int, op: str) -> np.ndarray:
    T, Z, Y, X = S.shape
    if Z < 3:
        raise ValueError(f"{op}: each frame needs Z >= 3 focus planes, got {Z}")
    heights = np.empty((T, Y, X))
    yy, xx = np.meshgrid(np.arange(Y), np.arange(X), indexing="ij")
    for t in range(T):
        fm = np.stack([ndi.uniform_filter(np.abs(ndi.laplace(S[t, z])), w, mode="nearest") for z in range(Z)], axis=0)
        k_raw = fm.argmax(axis=0)
        k = np.clip(k_raw, 1, Z - 2)
        fm1, f0, fp1 = fm[k - 1, yy, xx], fm[k, yy, xx], fm[k + 1, yy, xx]
        denom = fm1 - 2.0 * f0 + fp1
        delta = np.where(np.abs(denom) > 1e-12, 0.5 * (fm1 - fp1) / np.where(np.abs(denom) > 1e-12, denom, 1.0), 0.0)
        # 端の面が最大なら放物線は引けない → その面の整数高さをそのまま返す(内側へ寄せない)
        heights[t] = np.where(k_raw == k, k + np.clip(delta, -0.5, 0.5), k_raw)
    return heights


def focus_sweep_height_video(volseq, window: int = 5) -> np.ndarray:
    """焦点掃引(各フレームが z の合焦スタック)の時系列から**高さ場の動画** ``(T, Y, X)`` を起こす(``video``、
    単位は z の枚数)。

    合焦度は局所ラプラシアン絶対値の平均(``window``、Sum-Modified-Laplacian)、各画素の高さは合焦度が
    最大の z を放物線で副ボクセル精度にしたもの(``depth_from_focus`` の時系列版)。数値が欲しいときはこちら、
    絵が欲しいときは ``focus_sweep_surface_video``。テクスチャの無い画素は合焦度が平らで高さが決まらない。
    """
    op = "focus_sweep_height_video"
    S = _series(volseq, op, min_t=1)
    w = _count(window, op, "window", 1, 64)
    return _focus_heights(S, w, op)


def focus_sweep_surface_video(volseq, window: int = 5, zscale: float = 1.0, light=(0.4, 0.4, 0.8),
                              ambient: float = 0.25) -> np.ndarray:
    """焦点掃引(各フレームが z の合焦スタック)の時系列から**陰影つきの高さ場の動画** ``(T, Y, X, 3)`` を
    起こす(``rgbvideo``)。

    高さは ``focus_sweep_height_video`` と同じ(合焦度の最大を放物線で副ボクセルに)。高さ場の勾配から
    法線を作り(``zscale`` は z 1 枚の実長 / 画素の実長)、``light`` 方向のランバート陰影(``ambient`` を
    下駄に)を**高さの色**(青 = 低い → 赤 = 高い)に掛ける。掃引の途中で対象が動くと層の整合が崩れて
    高さが跳ぶ(その時刻だけ疑う)。
    """
    op = "focus_sweep_surface_video"
    S = _series(volseq, op, min_t=1)
    w = _count(window, op, "window", 1, 64)
    zs = _finite(zscale, op, "zscale", lo=1e-9)
    amb = _finite(ambient, op, "ambient", lo=0.0, hi=1.0)
    lt = np.asarray(light, dtype=np.float64).reshape(-1)
    if lt.shape != (3,) or not np.isfinite(lt).all() or np.linalg.norm(lt) < 1e-12:
        raise ValueError(f"{op}: light must be a non-zero (z, y, x) direction, got {light!r}")
    lt = lt / np.linalg.norm(lt)
    T, Z, Y, X = S.shape
    heights = _focus_heights(S, w, op)
    lo, hi = float(heights.min()), float(heights.max())
    ramp = _time_colors(256)
    out = np.empty((T, Y, X, 3))
    for t in range(T):
        h = heights[t] * zs
        gy, gx = np.gradient(h)
        n = np.stack([np.ones_like(h), -gy, -gx], axis=-1)              # (z, y, x) の法線
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        shade = amb + (1.0 - amb) * np.clip(n @ lt, 0.0, 1.0)
        hc = (heights[t] - lo) / (hi - lo) if hi > lo else np.zeros_like(h)
        out[t] = ramp[np.clip((hc * 255).astype(int), 0, 255)] * shade[..., None]
    return np.clip(out, 0.0, 1.0)
