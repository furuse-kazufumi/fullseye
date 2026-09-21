# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""videocube —— 動画を空間 × 時間の立方体として見る(Video Summagator の再実装)。

Nguyen・Niu・Liu「Video Summagator: An Interface for Video Summarization and Navigation」(ACM CHI 2012)は、
動画 (T, H, W) を (x, y, t) の立方体にし、**動かない背景を薄く、動く物体を濃く**するボリュームレンダリングで
「何が・どこを・いつ通ったか」を 1 枚の立体に見せ、切ったり回したりして目当ての場面へ飛ぶ道具。深層学習は
使わない。ここでは同じ考えを numpy + scipy.ndimage だけで op にした(公開コードは無いので再実装)。

* ``video_spacetime_cube``: 動画 → 立方体(``voxel``)。``mode="motion"`` は時間差分の大きさ(= 不透明度の元)、
  ``"intensity"`` は明るさ(= 色の元)。
* ``vol_render_transfer``: 立方体を任意の視点から**前から後ろへの α 合成**で描く(``rgb``)。色は時刻(虹)か
  もう 1 つの立方体の値。既存の ``render_volume_projection``(X 線 / MIP)では背景と動きを分けられない。
* ``video_cube_cut``: 立方体の断面(x–t = スリットスキャン、y–t、x–y)。「その行をいつ何が横切ったか」が 1 枚で見える。
* ``video_cube_orbit``: 立方体を回す動画(``rgbvideo``、展示と Studio の出口)。
* ``video_summary_keyframes``: 動きの量と場面の変化から代表フレームの添字(``indices``)。

Studio では Tools ▸ Video cube が同じ部品で対話的に動く(ドラッグで回転、断面の位置をスライダ、断面をクリックで
そのフレームへ)。
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy import ndimage as ndi

__all__ = [
    "video_spacetime_cube", "vol_render_transfer", "video_cube_cut", "video_cube_orbit",
    "video_summary_keyframes", "video_write_gif", "MAX_CUBE_ELEMENTS", "CUBE_MODES", "CUT_PLANES",
]

#: 立方体の要素数の上限(動画 (T, H, W) の積)。
MAX_CUBE_ELEMENTS = 2 ** 26
#: ``video_spacetime_cube`` の mode。motion = 動いた所、dark / bright = 暗い / 明るい所(EM の連続断面のような
#: **z スタック**を同じ立方体として見るため: 膜は暗い)、intensity = 明るさそのもの(色の元)。
CUBE_MODES = ("motion", "dark", "bright", "intensity")
#: ``video_cube_cut`` の断面。
CUT_PLANES = ("xt", "yt", "xy")


# --------------------------------------------------------------------------- #
# 入口                                                                          #
# --------------------------------------------------------------------------- #
def _video(video: Any, op: str, min_t: int = 1) -> np.ndarray:
    if isinstance(video, (list, tuple)):
        frames = [np.asarray(f, dtype=np.float64) for f in video]
        if not frames or any(f.ndim != 2 or f.shape != frames[0].shape for f in frames):
            raise ValueError(f"{op}: video frames must all be the same (H, W) shape")
        v = np.stack(frames, axis=0)
    else:
        v = np.asarray(video, dtype=np.float64)
    if v.ndim != 3:
        raise ValueError(f"{op}: video must be (T, H, W), got shape {v.shape}")
    if v.shape[0] < min_t or v.shape[1] < 2 or v.shape[2] < 2:
        raise ValueError(f"{op}: video needs T >= {min_t} and H, W >= 2, got shape {v.shape}")
    if v.size > MAX_CUBE_ELEMENTS:
        raise ValueError(f"{op}: video has {v.size} elements > MAX_CUBE_ELEMENTS={MAX_CUBE_ELEMENTS}")
    if not np.isfinite(v).all():
        raise ValueError(f"{op}: video must be finite")
    return v


def _cube(vol: Any, op: str, name: str = "vol", shape=None) -> np.ndarray:
    a = np.asarray(vol, dtype=np.float64)
    if a.ndim != 3 or a.size == 0:
        raise ValueError(f"{op}: {name} must be a non-empty (T, H, W) cube, got shape {a.shape}")
    if shape is not None and a.shape != tuple(shape):
        raise ValueError(f"{op}: {name} shape {a.shape} must match {tuple(shape)}")
    if a.size > MAX_CUBE_ELEMENTS:
        raise ValueError(f"{op}: {name} has {a.size} elements > MAX_CUBE_ELEMENTS={MAX_CUBE_ELEMENTS}")
    if not np.isfinite(a).all():
        raise ValueError(f"{op}: {name} must be finite")
    return a


def _finite(x: Any, op: str, name: str, lo=None, hi=None) -> float:
    if isinstance(x, (bool, np.bool_, str)) or x is None:
        raise ValueError(f"{op}: {name} must be a number, got {x!r}")
    v = float(x)
    if not np.isfinite(v):
        raise ValueError(f"{op}: {name} must be finite, got {v}")
    if lo is not None and v < lo:
        raise ValueError(f"{op}: {name} must be >= {lo}, got {v}")
    if hi is not None and v > hi:
        raise ValueError(f"{op}: {name} must be <= {hi}, got {v}")
    return v


def _count(x: Any, op: str, name: str, lo: int, hi: int | None = None) -> int:
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer)):
        raise ValueError(f"{op}: {name} must be an integer, got {x!r}")
    v = int(x)
    if v < lo or (hi is not None and v > hi):
        raise ValueError(f"{op}: {name} must be in [{lo}, {hi if hi is not None else 'inf'}], got {v}")
    return v


def _unit(v: np.ndarray) -> np.ndarray:
    """[0, 1] に正規化(定数なら 0)。"""
    lo, hi = float(v.min()), float(v.max())
    return (v - lo) / (hi - lo) if hi > lo else np.zeros_like(v)


# --------------------------------------------------------------------------- #
# 立方体                                                                        #
# --------------------------------------------------------------------------- #
def video_spacetime_cube(video, mode: str = "motion", sigma: float = 1.0, percentile: float = 99.5,
                         floor: float = 0.15) -> np.ndarray:
    """動画 (T, H, W) を空間 × 時間の立方体 ``(T, H, W)`` float [0, 1] にする(``voxel``)。

    ``mode="motion"``: 隣り合うフレームの差の大きさ |I_t − I_{t−1}| を空間で σ = ``sigma`` のガウスで平滑し、
    ``percentile`` 分位で 1 に正規化、``floor`` 未満を 0 に落として [0, 1] に伸ばす(先頭フレームは 0。
    センサ雑音の差分は床の下に沈む)。動く物体だけが立つので、``vol_render_transfer`` の**不透明度**になる ——
    静止した背景は透けて、軌跡が浮かぶ(Summagator の伝達関数)。
    ``mode="intensity"``: 明るさを [0, 1] に正規化(色の元、または背景を薄く敷く用)。
    ``mode="dark"`` / ``"bright"``: 暗い / 明るい所を不透明にする(σ で平滑、``floor`` 未満は 0)。動画でなく
    **z スタック**(EM の連続断面: 膜は暗い、蛍光: 細胞は明るい)を同じ立方体として見るため —— 先頭軸を
    時間でなく奥行きと読むだけで、断面(``video_cube_cut``)も回転(``video_cube_orbit``)も同じ op で動く。

    >>> alpha = video_spacetime_cube(clip, "motion")
    >>> color = video_spacetime_cube(clip, "intensity")
    >>> rgb = vol_render_transfer(alpha, color, yaw=35.0, pitch=25.0)
    >>> membranes = video_spacetime_cube(em_stack, "dark", sigma=1.0)      # ハエの脳の断面を積んだ立方体
    """
    op = "video_spacetime_cube"
    v = _video(video, op)
    if mode not in CUBE_MODES:
        raise ValueError(f"{op}: mode must be one of {CUBE_MODES}, got {mode!r}")
    if mode == "intensity":
        return _unit(v)
    s = _finite(sigma, op, "sigma", lo=0.0, hi=64.0)
    p = _finite(percentile, op, "percentile", lo=50.0, hi=100.0)
    fl = _finite(floor, op, "floor", lo=0.0, hi=0.99)
    if mode in ("dark", "bright"):
        u = _unit(v)
        d = 1.0 - u if mode == "dark" else u
        if s > 0.0:
            d = ndi.gaussian_filter(d, sigma=(0.0, s, s))
        top = float(np.percentile(d, p))
        return np.clip((d / top - fl) / (1.0 - fl), 0.0, 1.0) if top > 0.0 else np.zeros_like(d)
    d = np.zeros_like(v)
    if v.shape[0] >= 2:
        d[1:] = np.abs(np.diff(v, axis=0))
        if s > 0.0:
            d = ndi.gaussian_filter(d, sigma=(0.0, s, s))
    top = float(np.percentile(d, p))
    if top <= 0.0:
        return np.zeros_like(d)
    return np.clip((d / top - fl) / (1.0 - fl), 0.0, 1.0)


def video_cube_cut(video, plane: str = "xt", position: float = 0.5) -> np.ndarray:
    """立方体の断面 1 枚(``image2d``)。``"xt"`` = 行 ``position`` のスリットスキャン (T, W)、``"yt"`` = 列の (T, H)、
    ``"xy"`` = 時刻 ``position`` のフレーム (H, W)。``position`` は [0, 1] の割合(行・列・時刻の何割目か)。

    x–t 断面では、右へ動く物体は右下がりの筋、止まっている物体は縦の帯になる —— **速度が傾きとして読める**。

    >>> streak = video_cube_cut(clip, "xt", position=0.4)      # 4 割目の行を横切ったものの記録
    """
    op = "video_cube_cut"
    v = _video(video, op)
    if plane not in CUT_PLANES:
        raise ValueError(f"{op}: plane must be one of {CUT_PLANES}, got {plane!r}")
    pos = _finite(position, op, "position", lo=0.0, hi=1.0)
    T, H, W = v.shape
    if plane == "xt":
        return v[:, int(round(pos * (H - 1))), :].copy()
    if plane == "yt":
        return v[:, :, int(round(pos * (W - 1)))].copy()
    return v[int(round(pos * (T - 1)))].copy()


# --------------------------------------------------------------------------- #
# 描く                                                                          #
# --------------------------------------------------------------------------- #
def _time_colors(n: int) -> np.ndarray:
    """時刻 → 色(青 → 緑 → 黄 → 赤、(n, 3) in [0, 1])。赤緑で良否を言うのではなく順序を言う。"""
    t = np.linspace(0.0, 1.0, n)
    r = np.clip(1.5 * t - 0.25, 0.0, 1.0)
    g = np.clip(1.0 - np.abs(2.0 * t - 1.0) * 1.2 + 0.2, 0.0, 1.0)
    b = np.clip(1.0 - 1.8 * t, 0.0, 1.0)
    return np.stack([r, g, b], axis=1)


def _rotation(yaw: float, pitch: float) -> np.ndarray:
    """立方体座標 (t, y, x)(単位立方体、中心原点)→ 視点座標 (depth, v, u)。yaw は t–x 面の回転、pitch は仰角。"""
    cy, sy = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
    cp, sp = np.cos(np.radians(pitch)), np.sin(np.radians(pitch))
    # 基準の視線 = +t 方向(時間軸を奥行きに、x を横、y を縦)
    Ry = np.array([[cy, 0.0, -sy], [0.0, 1.0, 0.0], [sy, 0.0, cy]])          # t–x 面
    Rp = np.array([[cp, -sp, 0.0], [sp, cp, 0.0], [0.0, 0.0, 1.0]])          # depth–y 面
    return Rp @ Ry


def _draw_line(img: np.ndarray, p0, p1, color) -> None:
    n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))) + 1
    ys = np.round(np.linspace(p0[0], p1[0], n)).astype(int)
    xs = np.round(np.linspace(p0[1], p1[1], n)).astype(int)
    ok = (ys >= 0) & (ys < img.shape[0]) & (xs >= 0) & (xs < img.shape[1])
    img[ys[ok], xs[ok]] = color


def vol_render_transfer(vol, color=None, yaw: float = 35.0, pitch: float = 25.0, size: int = 256,
                        alpha_gain: float = 1.0, static_alpha: float = 0.0, background=(0.04, 0.04, 0.06),
                        frame: bool = True, depth_samples: int | None = None) -> np.ndarray:
    """立方体を任意の視点から**前から後ろへの α 合成**で描く ``(size, size, 3)`` float [0, 1](``rgb``)。

    ``vol`` (T, H, W) は不透明度 [0, 1](``video_spacetime_cube(mode="motion")``)。色は ``color`` を渡せば
    その値(同じ形、[0, 1] に正規化される)のグレー、渡さなければ**時刻の色**(青 = 始め → 赤 = 終わり)。
    軌跡を時刻で塗ると「どちらへ動いたか」が 1 枚で読める。``static_alpha`` > 0 なら静止した背景(``color`` の
    明るさ、無ければ灰)を薄く重ねる —— 値は**立方体の最長辺の長さを貫いたときの合計の不透明度**(0.15 なら
    最長辺ぶん奥まで見て 15 %、短い辺の向きならそれより薄い)で、サンプル数には依らない(Summagator の「静的な内容」)。正射影、視線に沿って ``depth_samples`` 点
    (既定 = 立方体の最大辺)を三線形補間で拾い、``C = Σ α_i c_i Π_{j<i}(1 − α_j)``。
    ``frame=True`` で立方体の 12 辺を薄く描く(向きの手掛かり)。

    ``yaw`` は時間軸と x 軸の面での回転(0 = 時間軸を奥行きに見る = 動画をそのまま見る向き)、``pitch`` は仰角。
    1 枚あたりの計算量は ``size² × depth_samples``(256² × 64 で約 0.3 s)。

    >>> rgb = vol_render_transfer(video_spacetime_cube(clip), yaw=40.0, pitch=20.0, static_alpha=0.02)
    """
    op = "vol_render_transfer"
    A = _cube(vol, op, "vol")
    if A.min() < 0.0 or A.max() > 1.0:
        raise ValueError(f"{op}: vol must be opacities in [0, 1] (video_spacetime_cube output), got range "
                         f"[{A.min():.3g}, {A.max():.3g}]")
    C = None if color is None else _unit(_cube(color, op, "color", A.shape))
    yw = _finite(yaw, op, "yaw")
    pt = _finite(pitch, op, "pitch")
    n = _count(size, op, "size", 8, 4096)
    g = _finite(alpha_gain, op, "alpha_gain", lo=0.0)
    sa = _finite(static_alpha, op, "static_alpha", lo=0.0, hi=1.0)
    bg = np.asarray(background, dtype=np.float64).reshape(-1)
    if bg.shape != (3,) or not np.isfinite(bg).all() or bg.min() < 0.0 or bg.max() > 1.0:
        raise ValueError(f"{op}: background must be an RGB triple in [0, 1], got {background!r}")
    if not isinstance(frame, (bool, np.bool_)):
        raise ValueError(f"{op}: frame must be a bool, got {frame!r}")
    T, H, W = A.shape
    nd = max(T, H, W) if depth_samples is None else _count(depth_samples, op, "depth_samples", 2, 4096)
    if n * n * nd > MAX_CUBE_ELEMENTS * 4:
        raise ValueError(f"{op}: size² × depth_samples = {n * n * nd} is too large; lower size or depth_samples")
    R = _rotation(yw, pt)                                   # cube (t, y, x) → view (depth, v, u)
    Rinv = R.T
    dims = np.array([T, H, W], dtype=np.float64)
    half = dims / 2.0
    radius = float(np.sqrt((half ** 2).sum()))              # 立方体を収める球
    # 視点座標の格子: u(横)・v(縦)は [-radius, radius]、depth も同じ範囲を nd 点
    u = np.linspace(-radius, radius, n)
    v = np.linspace(-radius, radius, n)
    d = np.linspace(-radius, radius, nd)
    D, V, U = np.meshgrid(d, v, u, indexing="ij")           # (nd, n, n)
    view = np.stack([D.ravel(), V.ravel(), U.ravel()], axis=0)          # (3, N)
    cube = Rinv @ view                                      # (3, N) in (t, y, x), centred
    coords = cube + (half - 0.5)[:, None]                   # voxel index space
    a_motion = np.clip(ndi.map_coordinates(A, coords, order=1, mode="constant", cval=0.0).reshape(nd, n, n) * g, 0.0, 1.0)
    inside = ((coords >= -0.5) & (coords <= (dims - 0.5)[:, None])).all(axis=0).reshape(nd, n, n)
    # 静止した背景の薄い不透明度: static_alpha は**最長辺の長さを貫いたときの合計**。1 サンプルあたりは
    # 1 − (1 − sa)^(step / L)(step = サンプル間隔、L = 最長辺)—— サンプル数にも視線の向きにも依らず、
    # 通った長さだけで濃さが決まる(サンプル数に比例させると深い立方体ほど中が見えなくなる)
    step = 2.0 * radius / max(nd - 1, 1)
    a_static = (1.0 - (1.0 - sa) ** (step / float(dims.max()))) * inside if sa > 0.0 else np.zeros_like(a_motion)
    grey = (ndi.map_coordinates(C, coords, order=1, mode="constant", cval=0.0).reshape(nd, n, n)
            if C is not None else np.full((nd, n, n), 0.5))
    if C is None:
        # 動きの色 = 時刻(t の線形補間。map_coordinates を 3 回回すより速い)
        tcol = _time_colors(T)
        ti = np.clip(coords[0], 0.0, T - 1)
        i0 = np.floor(ti).astype(int)
        i1 = np.minimum(i0 + 1, T - 1)
        w = (ti - i0)[:, None]
        c_motion = (tcol[i0] * (1.0 - w) + tcol[i1] * w).reshape(nd, n, n, 3)
    else:
        c_motion = np.repeat(grey[..., None], 3, axis=-1)
    c_static = np.repeat(grey[..., None], 3, axis=-1)
    alpha = 1.0 - (1.0 - a_motion) * (1.0 - a_static)      # 2 つの層を同じサンプルで重ねる
    num = a_motion[..., None] * c_motion + a_static[..., None] * (1.0 - a_motion)[..., None] * c_static
    col = np.where(alpha[..., None] > 0.0, num / np.maximum(alpha, 1e-12)[..., None], 0.0)
    # 前から後ろへ: T_i = Π_{j<i} (1 − α_j)
    trans = np.cumprod(1.0 - alpha, axis=0)
    trans = np.concatenate([np.ones((1, n, n)), trans[:-1]], axis=0)
    weight = alpha * trans                                  # (nd, n, n)
    img = (weight[..., None] * col).sum(axis=0)
    img += (trans[-1] * (1.0 - alpha[-1]))[..., None] * bg  # 残りの透過分は背景
    img = np.clip(img, 0.0, 1.0)
    if frame:
        corners = np.array([[t, y, x] for t in (0, T) for y in (0, H) for x in (0, W)], dtype=np.float64) - half
        pv = (R @ corners.T).T                              # (8, 3): depth, v, u
        to_px = lambda q: ((q[1] + radius) / (2 * radius) * (n - 1), (q[2] + radius) / (2 * radius) * (n - 1))  # noqa: E731
        edges = [(i, j) for i in range(8) for j in range(i + 1, 8) if bin(i ^ j).count("1") == 1]
        line_col = np.array([0.55, 0.55, 0.6])
        for i, j in edges:
            _draw_line(img, to_px(pv[i]), to_px(pv[j]), line_col)
    return img[::-1]                                        # v を上向きに


def video_cube_orbit(video, n_frames: int = 36, pitch: float = 25.0, yaw_start: float = 0.0, yaw_span: float = 360.0,
                     size: int = 256, sigma: float = 1.0, alpha_gain: float = 1.0, static_alpha: float = 0.02,
                     color: str = "time", mode: str = "motion", depth_samples: int | None = None,
                     floor: float = 0.15) -> np.ndarray:
    """立方体を回す色動画 ``(n_frames, size, size, 3)`` float [0, 1](``rgbvideo``)。

    ``video_spacetime_cube(mode)`` を不透明度に(``"motion"`` = 動画の軌跡、``"dark"`` / ``"bright"`` = z スタックの膜や
    細胞)、``color="time"`` なら先頭軸(時刻 / 奥行き)の色、``"intensity"`` なら明るさで塗り、yaw を ``yaw_start`` から
    ``yaw_span`` 度ぶん等分に回す(pitch 固定)。展示と Studio の出口。``video_write_gif`` でそのまま GIF にできる。

    >>> frames = video_cube_orbit(clip, n_frames=24, size=200)
    >>> video_write_gif(frames, "cube.gif", fps=10)
    """
    op = "video_cube_orbit"
    v = _video(video, op)
    nf = _count(n_frames, op, "n_frames", 1, 4096)
    y0 = _finite(yaw_start, op, "yaw_start")
    ys = _finite(yaw_span, op, "yaw_span")
    if color not in ("time", "intensity"):
        raise ValueError(f"{op}: color must be 'time' or 'intensity', got {color!r}")
    if mode not in CUBE_MODES or mode == "intensity":
        raise ValueError(f"{op}: mode must be 'motion', 'dark' or 'bright', got {mode!r}")
    A = video_spacetime_cube(v, mode, sigma=sigma, floor=floor)
    C = video_spacetime_cube(v, "intensity") if color == "intensity" else None
    out = np.empty((nf, int(size), int(size), 3))
    for k in range(nf):
        out[k] = vol_render_transfer(A, C, yaw=y0 + ys * k / nf, pitch=pitch, size=size, alpha_gain=alpha_gain,
                                     static_alpha=static_alpha, depth_samples=depth_samples)
    return out


# --------------------------------------------------------------------------- #
# 書き出す                                                                      #
# --------------------------------------------------------------------------- #
def video_write_gif(frames, path: str, fps: float = 10.0) -> str:
    """フレーム列をアニメーション GIF に書く(``text`` = 書いたパス)。使い回しの出口。

    ``frames`` は灰の ``video`` (T, H, W) か色の ``rgbvideo`` (F, H, W, 3)。float は [0, 1] を 0..255 に、
    整数はそのまま uint8 に(範囲外は切る)。**全フレームを保存する**(Pillow は前と同じ絵を 1 コマに
    畳んで数を減らすので、``video.write_video`` の全コマ保存経路を使い、書いた後に枚数を読み戻して確かめる)。
    Pillow が無ければ ImportError(optional 依存)。``path`` は ``.gif`` で終わること。

    >>> video_write_gif(video_cube_orbit(clip, n_frames=24), "out/cube.gif", fps=12)
    'out/cube.gif'
    """
    op = "video_write_gif"
    if not isinstance(path, str) or not path.lower().endswith(".gif"):
        raise ValueError(f"{op}: path must be a str ending in .gif, got {path!r}")
    f = _finite(fps, op, "fps", lo=0.1, hi=120.0)
    a = np.asarray(frames)
    if a.ndim not in (3, 4) or (a.ndim == 4 and a.shape[-1] != 3) or a.shape[0] < 1:
        raise ValueError(f"{op}: frames must be (T, H, W) grey or (F, H, W, 3) rgb, got shape {a.shape}")
    if a.size > MAX_CUBE_ELEMENTS * 3:
        raise ValueError(f"{op}: {a.size} elements exceed the cap {MAX_CUBE_ELEMENTS * 3}")
    if a.dtype.kind == "f":
        if not np.isfinite(a).all():
            raise ValueError(f"{op}: frames must be finite")
        u8 = (np.clip(a, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    elif a.dtype.kind in "iub":
        u8 = np.clip(a, 0, 255).astype(np.uint8)
    else:
        raise ValueError(f"{op}: frames must be numeric, got dtype {a.dtype}")
    import video as _video_mod
    _video_mod.write_video(path, [fr for fr in u8], fps=f)
    return path


# --------------------------------------------------------------------------- #
# 要約                                                                          #
# --------------------------------------------------------------------------- #
def video_summary_keyframes(video, k: int = 5, min_gap: int | None = None, bins: int = 32) -> np.ndarray:
    """代表フレームの添字 ``(k,)`` int64、昇順(``indices``)。

    フレームごとの得点 = 動きの量(|I_t − I_{t−1}| の平均、[0, 1] に正規化)+ 場面の変化(ヒストグラムの
    χ² 距離、正規化)。得点の高い順に、既に選んだフレームから ``min_gap``(既定 T // (2k))以上離れたものを
    貪欲に ``k`` 枚選ぶ。T < k なら全フレーム。学習なしの「何かが起きたフレーム」であって、意味の要約ではない。

    >>> idx = video_summary_keyframes(clip, k=4)
    >>> thumbnails = clip[idx]
    """
    op = "video_summary_keyframes"
    v = _video(video, op)
    kk = _count(k, op, "k", 1, 100000)
    nb = _count(bins, op, "bins", 2, 4096)
    T = v.shape[0]
    if T <= kk:
        return np.arange(T, dtype=np.int64)
    gap = T // (2 * kk) if min_gap is None else _count(min_gap, op, "min_gap", 0, T)
    motion = np.zeros(T)
    motion[1:] = np.abs(np.diff(v, axis=0)).mean(axis=(1, 2))
    lo, hi = float(v.min()), float(v.max())
    edges = np.linspace(lo, hi if hi > lo else lo + 1.0, nb + 1)
    hists = np.stack([np.histogram(f, bins=edges)[0].astype(np.float64) for f in v])
    hists /= max(1.0, float(v[0].size))
    chi = np.zeros(T)
    for t in range(1, T):
        a, b = hists[t], hists[t - 1]
        den = a + b
        chi[t] = float(np.sum(np.where(den > 0, (a - b) ** 2 / np.where(den > 0, den, 1.0), 0.0)))
    score = _unit(motion) + _unit(chi)
    chosen: list[int] = []
    for t in np.argsort(-score, kind="stable"):
        if all(abs(int(t) - c) >= gap for c in chosen):
            chosen.append(int(t))
            if len(chosen) == kk:
                break
    return np.array(sorted(chosen), dtype=np.int64)
