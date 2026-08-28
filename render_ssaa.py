# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""スーパーサンプリング・アンチエイリアス(SSAA)でメッシュを「映える静止画」に描く。

:mod:`render3d` の ``render_mesh`` は正直な **z-buffer** ラスタライザで、画素は中心が
三角形に入るか否かの二値被覆しか持たない — ドキュメント通り *アンチエイリアスなし*。
その結果、斜めのシルエット境界は階段状のジャギー(staircase aliasing)になる。ここでは
教科書どおりの **SSAA**(supersampling anti-aliasing)でそれを消す:

    目標解像度の ``ss`` 倍で ``render_mesh`` を実行して陰影を付け、``ss×ss`` 画素ブロックを
    面積平均(box / gauss)で 1 画素へ縮小する。1 出力画素は ``ss²`` 個のサブサンプルの
    平均になるため、境界画素は「被覆率(0〜1)」に応じた中間輝度を持ち、階段が滑らかな
    勾配に変わる。

なぜここに要るか(固有価値, honest):
  * ``render_mesh`` … ラスタライズの土台(depth / silhouette / 面法線)。AA は原理上持たない。
  * ``match3d.render_shaded`` / ``photometric.render_lambertian`` … 法線マップ → 陰影画像。
    これらも入力解像度そのままで、エッジのジャギーには手を付けない。
  * ``flow.py`` の "anti-aliased half-resolution" … オプティカルフローのガウスピラミッド
    (縮小前のプレフィルタ)であって、レンダリング画像のエッジ AA ではない。
  * **本モジュール** … 上の土台を **再発明せず** ``render_mesh`` を高解像度で呼び、面積平均で
    縮小する薄い層。汎用の :func:`antialias`(任意の高解像画像を縮小)と、エッジのエイリアス
    エネルギーを測る :func:`edge_alias_energy` を伴う。numpy + scipy のみ。

原理と限界(honest):
  * SSAA は **一様サンプリング** の平均であり解析的な被覆計算ではない。``ss`` が有限なので
    AA は近似で、``ss`` を上げるほど残留ジャギーは単調に減るが完全には消えない(``ss→∞``
    で真の被覆率に収束)。計算量は ``ss²`` に比例する(高解像レンダリングのコスト)。
  * ``render_mesh`` の制約(近平面クリップ無し・面法線フラット・透明/影無し)はそのまま
    受け継ぐ。SSAA はエッジと陰影の *サンプリング* を細かくするだけで、それらは直さない。
  * box フィルタは各サブサンプルを等重みで平均(= 正確な面積平均、標準的)。gauss は
    ブロック中心を重く見る円錐状の重みで、僅かに柔らかい(が僅かにボケる)。

Fail-closed: ``ss`` は 1 以上の整数(非整数・0 以下は ``ValueError``)、出力サイズは正で
``render3d.MAX_PIXELS`` 以下(``size*ss`` の総画素数を確保前に検査)、``antialias`` は
各辺が ``ss`` で割り切れることを要求する。``V`` / ``F`` / ``pose`` / ``intrinsics`` の
検証は ``render_mesh`` の fail-closed ガードへ委譲する。
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from render3d import MAX_PIXELS, render_mesh

__all__ = ["supersample_mesh", "antialias", "edge_alias_energy"]


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def _check_ss(ss) -> int:
    """``ss`` を 1 以上の整数へ検証(fail-closed)。"""
    if isinstance(ss, bool) or not isinstance(ss, (int, np.integer)):
        raise ValueError("ss must be an integer >= 1, got %r" % (ss,))
    s = int(ss)
    if s < 1:
        raise ValueError("ss must be >= 1, got %d" % (s,))
    return s


def _parse_size(size) -> tuple[int, int]:
    """``size`` を ``(height, width)`` へ。int は正方形、2-要素は (height, width)。"""
    if np.isscalar(size):
        h = w = int(size)
    else:
        arr = tuple(int(v) for v in size)
        if len(arr) != 2:
            raise ValueError("size must be an int or a (height, width) pair, got %r"
                             % (size,))
        h, w = arr
    if h <= 0 or w <= 0:
        raise ValueError("size must be positive, got height=%d width=%d" % (h, w))
    return h, w


def _default_shade(view: dict, light, ambient: float) -> np.ndarray:
    """法線マップ + 光源 → Lambertian グレースケール陰影(背景は 0 でマスク)。

    ``match3d.render_shaded`` と同じ Lambertian だが、法線ゼロの背景を ``silhouette`` で
    0 に落とす(``render_shaded`` は背景に ``ambient`` を残すので、それだと縮小時に
    背景が灰色になりエッジ被覆の中間輝度と混ざる)。光源はカメラ空間で与える。"""
    n = np.asarray(view["normals"], np.float64)          # (H, W, 3)
    sil = np.asarray(view["silhouette"], np.float64)     # (H, W)
    L = np.asarray(light, np.float64).reshape(3)
    ln = np.linalg.norm(L)
    if not np.isfinite(ln) or ln < 1e-12:
        raise ValueError("light direction must be a non-zero finite vector")
    L = L / ln
    ndl = np.clip(n[..., 0] * L[0] + n[..., 1] * L[1] + n[..., 2] * L[2], 0.0, 1.0)
    img = ambient + (1.0 - ambient) * ndl
    return img * sil


# --------------------------------------------------------------------------- #
# generic downsampler                                                         #
# --------------------------------------------------------------------------- #
def antialias(hi_res_image, ss, filter: str = "box") -> np.ndarray:
    """高解像画像を整数倍 ``ss`` で縮小(area-average anti-aliasing)。

    ``hi_res_image`` は ``(H*ss, W*ss)`` または ``(H*ss, W*ss, C)`` の float 画像。各
    ``ss×ss`` ブロックを重み付き平均して ``(H, W[, C])`` を返す。``filter``:

      * ``"box"``   — 等重み平均(正確な面積平均、SSAA の標準)。
      * ``"gauss"`` — ブロック中心を重く見るガウス重み(σ = ss/2、僅かに柔らかい)。

    Fail-closed: ``ss`` は 1 以上の整数、入力は 2D / 3D、各辺は ``ss`` で割り切れること。
    非有限値があれば ``ValueError``(平均で NaN が伝播しないよう確保前に拒否)。"""
    s = _check_ss(ss)
    a = np.asarray(hi_res_image, np.float64)
    if a.ndim not in (2, 3):
        raise ValueError("hi_res_image must be 2-D or 3-D, got shape %r" % (a.shape,))
    if not np.isfinite(a).all():
        raise ValueError("hi_res_image contains non-finite values")
    H, W = a.shape[0], a.shape[1]
    if H % s != 0 or W % s != 0:
        raise ValueError("image %dx%d not divisible by ss=%d" % (H, W, s))
    h, w = H // s, W // s

    if filter == "box":
        wy = np.full(s, 1.0 / s)
        wx = wy
    elif filter == "gauss":
        x = np.arange(s) - (s - 1) / 2.0
        sigma = max(s / 2.0, 1e-6)
        g = np.exp(-0.5 * (x / sigma) ** 2)
        g = g / g.sum()
        wy = g
        wx = g
    else:
        raise ValueError("filter must be 'box' or 'gauss', got %r" % (filter,))

    if a.ndim == 2:
        blk = a.reshape(h, s, w, s)
        return np.einsum("i,j,aibj->ab", wy, wx, blk, optimize=True)
    c = a.shape[2]
    blk = a.reshape(h, s, w, s, c)
    return np.einsum("i,j,aibjk->abk", wy, wx, blk, optimize=True)


# --------------------------------------------------------------------------- #
# supersampled mesh render                                                    #
# --------------------------------------------------------------------------- #
def supersample_mesh(V, F, pose=None, intrinsics=None, size=256, ss: int = 3,
                     light=(0.0, 0.0, 1.0), ambient: float = 0.1,
                     shade: Optional[Callable[[dict], np.ndarray]] = None,
                     filter: str = "box") -> np.ndarray:
    """メッシュを SSAA でアンチエイリアス描画 -> float 画像 ``(H, W)`` (or ``(H, W, C)``)。

    ``render_mesh`` を **目標サイズの ``ss`` 倍**で呼び、陰影を付けてから ``ss×ss`` 面積平均で
    目標 ``size`` へ縮小する。``ss=1`` は縮小なし = ``render_mesh`` 生の(エイリアスありの)
    ベースライン。

    *pose* は 4x4 object->camera 行列(解像度非依存、そのまま使う)。*intrinsics* ``K`` は
    **目標 ``size`` 用**の 3x3 ピンホール行列で、高解像レンダリングのため内部で ``fx, fy,
    cx, cy`` を ``ss`` 倍にスケールする(出力は目標 ``size`` なので K の意味は目標基準)。
    どちらも ``None`` なら ``render_mesh`` が ``auto_view`` で自動フレーミングする(``auto_view``
    のフレーミングは解像度不変なので ``ss`` を変えても構図は同じ)。

    *shade* は ``shade(view_dict) -> (H*ss, W*ss[, C])`` の callable で、高解像 ``render_mesh``
    出力(``depth`` / ``silhouette`` / ``normals``)を陰影画像へ写す。``None`` のとき既定の
    Lambertian(*light* をカメラ空間の光源, *ambient* を環境光として法線から陰影, 背景 0)。
    *filter* は縮小重み(``"box"`` / ``"gauss"``, :func:`antialias` 参照)。

    Fail-closed: ``ss`` は 1 以上の整数、``size`` は正、``size*ss`` の総画素は
    ``render3d.MAX_PIXELS`` 以下。メッシュ・カメラの妥当性は ``render_mesh`` が検査する。"""
    s = _check_ss(ss)
    h, w = _parse_size(size)
    hs, ws = h * s, w * s
    if float(hs) * float(ws) > MAX_PIXELS:
        raise ValueError("supersampled render %dx%d = %.3g px, over the %d cap "
                         "(render3d.MAX_PIXELS) — lower size or ss"
                         % (ws, hs, float(hs) * float(ws), MAX_PIXELS))

    # 目標 K は目標 size 用。高解像レンダリングのため fx,fy,cx,cy を ss 倍する。
    Khi = None
    if intrinsics is not None:
        Khi = np.asarray(intrinsics, np.float64).copy()
        if Khi.shape != (3, 3):
            raise ValueError("intrinsics must be 3x3, got %r" % (Khi.shape,))
        Khi[:2, :] *= s

    view = render_mesh(V, F, pose=pose, intrinsics=Khi, width=ws, height=hs)

    if shade is None:
        hi = _default_shade(view, light, ambient)
    else:
        hi = np.asarray(shade(view), np.float64)
        if hi.shape[:2] != (hs, ws):
            raise ValueError("shade returned %r, expected leading (%d, %d)"
                             % (hi.shape, hs, ws))

    return antialias(hi, s, filter=filter)


# --------------------------------------------------------------------------- #
# aliasing metric                                                             #
# --------------------------------------------------------------------------- #
def edge_alias_energy(img) -> float:
    """エッジのエイリアス(ジャギー)エネルギー = ラプラシアンの RMS(小さいほど滑らか)。

    ラスタライズのエイリアスは階段状の鋭い角(高い 2 階微分)として現れる。ラプラシアンは
    高周波を強調するため、その二乗平均平方根(RMS)は境界の階段度を単調に捉える — SSAA で
    エッジが滑らかな勾配になれば、ラプラシアンの高周波エネルギーは減る(low-pass は高周波を
    減衰させ、ラプラシアンはそれを増幅するので、平滑化されたエッジほど本量は小さい)。

    平坦な内部・背景はラプラシアン ≈ 0 で寄与しないため、実質エッジ帯の量になる。カラー画像は
    チャンネル平均。同一形状・同一コントラストの画像どうしを比較するための相対指標。"""
    from scipy.ndimage import laplace

    a = np.asarray(img, np.float64)
    if a.ndim == 3:
        a = a.mean(axis=-1)
    if a.ndim != 2:
        raise ValueError("img must be 2-D or 3-D, got shape %r" % (np.asarray(img).shape,))
    lap = laplace(a, mode="nearest")
    return float(np.sqrt(np.mean(lap * lap)))
