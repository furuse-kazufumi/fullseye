"""Fullseye 統一 I/F — 小 spike (Qt 風・人間が書いて自然な API).

要件定義 docs/UNIFIED_API_REQUIREMENTS.md を、既存実装の**薄いラッパ**で具体化する
additive な spike(既存 809 op を一切変更しない・throwaway 可)。§9 既定 = 混成・eager・
一般語彙+HALCON エイリアス・API 先行。

  # 画像 op = core オブジェクトのチェーン(文のように読める)
  edges = Image.load("scene.png").to_gray().gaussian(sigma=1.4).sobel().threshold(0.2)
  # 長い尾(654 進化 op)は escape hatch で残す
  out   = Image(arr).op("emboss", a=0.6)
  # 視覚 op = 名前空間モジュール + 設定オブジェクト + 動詞メソッド(Qt ウィジェット風)
  depth = stereo.SGM(max_disp=64).compute(left, right)
  cloud = camera.Pinhole(K).backproject(depth)
  plane, inl = pcseg.PlaneRANSAC(thresh=0.02).fit(cloud)

★設計原則(approach B・単一実装): 自然 API は下層(scipy.ndimage 等)を**自然パラメータで直接**
呼ぶ。進化 op の a/b は探索用の正規化・有界エンコード(例 gaussian: sigma=0.3+2.7*a)であり、
人間 API の**パラメータ範囲まで漏らさない**。同じ下層関数を呼ぶので進化 op と drift しない。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import ndimage

import fullseye as fs

_LUMA = np.array([0.299, 0.587, 0.114])          # Rec.601 輝度(標準 gray 変換)


def _norm01(v: np.ndarray) -> np.ndarray:
    """[0,1] へ正規化(sobel/canny の勾配強度表示用。既存 _norm と同義)。"""
    lo, hi = float(v.min()), float(v.max())
    return (v - lo) / (hi - lo) if hi > lo else np.zeros_like(v)


# ── 画像 op = チェーン可能な core オブジェクト(eager・不変)─────────────────── #
class Image:
    """1 枚の画像(float64)を包む不変オブジェクト。各メソッドは新 Image を返し、チェーンできる。

    自然パラメータ(sigma / size / level)で下層 scipy を直接呼ぶ(approach B)。進化 registry の
    汎用 a/b ノブは `.op(name, a, b)` エスケープハッチにのみ残す(654 op の長い尾へのアクセス)。
    """

    __slots__ = ("array",)

    def __init__(self, array: np.ndarray) -> None:
        self.array = np.asarray(array, dtype=np.float64)

    # --- 生成 / 取り出し --- #
    @classmethod
    def load(cls, path: str | Path) -> "Image":
        return cls(fs.imread(str(path)) if hasattr(fs, "imread") else _imread_fallback(path))

    def save(self, path: str | Path) -> "Image":
        if hasattr(fs, "imwrite"):
            fs.imwrite(str(path), self.array)
        return self

    def _wrap(self, arr: np.ndarray) -> "Image":
        return Image(arr)

    # --- 画像 op(自然名・自然パラメータ)--- #
    def to_gray(self) -> "Image":
        if self.array.ndim == 3 and self.array.shape[-1] == 3:
            return self._wrap(self.array @ _LUMA)
        return self

    def gaussian(self, sigma: float = 1.0) -> "Image":
        return self._wrap(ndimage.gaussian_filter(self.array, sigma=sigma))

    def median(self, size: int = 3) -> "Image":
        return self._wrap(ndimage.median_filter(self.array, size=size))

    def sobel(self) -> "Image":
        g = np.hypot(ndimage.sobel(self.array, axis=1), ndimage.sobel(self.array, axis=0))
        return self._wrap(_norm01(g))

    def threshold(self, level: float = 0.5) -> "Image":
        return self._wrap((self.array > level).astype(np.float64))

    def canny(self, sigma: float = 1.0, low: float = 0.1) -> "Image":
        g = ndimage.gaussian_filter(self.array, sigma=sigma)
        m = _norm01(np.hypot(ndimage.sobel(g, axis=1), ndimage.sobel(g, axis=0)))
        return self._wrap((m > low).astype(np.float64))

    # --- morphology(自然 API=下層 scipy 直呼び。grey/binary 両対応の grey 版)--- #
    def erode(self, size: int = 3) -> "Image":
        return self._wrap(ndimage.grey_erosion(self.array, size=size))

    def dilate(self, size: int = 3) -> "Image":
        return self._wrap(ndimage.grey_dilation(self.array, size=size))

    def opening(self, size: int = 3) -> "Image":
        """erode→dilate: 小さな明領域(ノイズ)を除去。"""
        return self._wrap(ndimage.grey_opening(self.array, size=size))

    def closing(self, size: int = 3) -> "Image":
        """dilate→erode: 小さな暗穴を埋める。"""
        return self._wrap(ndimage.grey_closing(self.array, size=size))

    def morph_gradient(self, size: int = 3) -> "Image":
        """dilate - erode: 輪郭(境界)を抽出。"""
        return self._wrap(_norm01(ndimage.grey_dilation(self.array, size=size)
                                  - ndimage.grey_erosion(self.array, size=size)))

    # --- 長い尾(654 進化 op)へのエスケープハッチ --- #
    def op(self, name: str, a: float = 0.5, b: float = 0.5) -> "Image":
        """進化 registry の任意 op を汎用 a/b ノブで適用(自然 API 未整備の op 用)。"""
        return self._wrap(fs.apply(self.array, name, a=a, b=b))

    def __repr__(self) -> str:
        return f"Image(shape={self.array.shape}, dtype={self.array.dtype})"


def _imread_fallback(path: str | Path) -> np.ndarray:
    from imageio import v3 as iio
    return np.asarray(iio.imread(str(path)), dtype=np.float64) / 255.0


# ── stereo / camera / pcseg = 名前空間モジュール(設定オブジェクト+動詞メソッド)── #
@dataclass
class _StereoSGM:
    max_disp: int = 64
    window: int = 5
    P1: float = 5.0
    P2: float = 50.0
    paths: int = 4

    def compute(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        return fs.disparity_sgm(left, right, max_disp=self.max_disp, window=self.window,
                                P1=self.P1, P2=self.P2, paths=self.paths)


@dataclass
class _CameraPinhole:
    K: np.ndarray

    def backproject(self, depth: np.ndarray, organized: bool = False):
        return fs.depth_to_points(depth, self.K, organized=organized)


@dataclass
class _PcsegPlaneRANSAC:
    thresh: float = 0.02
    iters: int = 200
    seed: int = 0

    def fit(self, points: np.ndarray):
        return fs.fit_plane_ransac(points, thresh=self.thresh, iters=self.iters, seed=self.seed)


# 名前空間っぽくアクセスできるよう束ねる(Qt の QtWidgets.QPushButton 風の見た目)
class stereo:  # noqa: N801 — namespace module 風(クラスを名前空間として使う)
    SGM = _StereoSGM


class camera:  # noqa: N801
    Pinhole = _CameraPinhole


class pcseg:  # noqa: N801
    PlaneRANSAC = _PcsegPlaneRANSAC


def _demo() -> None:
    rng = np.random.default_rng(0)

    print("== 画像 op = チェーン(自然名・自然パラメータ)==")
    scene = rng.random((40, 60))
    edges = Image(scene).to_gray().gaussian(sigma=1.4).sobel().threshold(0.2)
    print("  Image(scene).to_gray().gaussian(1.4).sobel().threshold(0.2) ->", edges)
    # 長い尾のエスケープハッチ(654 進化 op がそのまま使える)
    blurred = Image(scene).op("gaussian", a=0.5)
    print("  Image(scene).op('gaussian', a=0.5)                          ->", blurred)

    print("\n== 視覚 op = 設定オブジェクト+動詞メソッド(Qt ウィジェット風)==")
    left = rng.random((32, 48))
    right = np.roll(left, 2, axis=1)
    disp = stereo.SGM(max_disp=8).compute(left, right)
    print("  stereo.SGM(max_disp=8).compute(l, r)      ->", type(disp).__name__, disp.shape)
    K = np.array([[50.0, 0, 24.0], [0, 50.0, 16.0], [0, 0, 1.0]])
    cloud = camera.Pinhole(K).backproject(np.full((32, 48), 3.0))
    cloud = cloud if isinstance(cloud, np.ndarray) else np.asarray(cloud)
    print("  camera.Pinhole(K).backproject(depth)      ->", cloud.shape)
    xs, ys = np.meshgrid(np.linspace(-1, 1, 20), np.linspace(-1, 1, 20))
    pts = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    pts += rng.normal(0, 0.002, pts.shape)
    plane, inl = pcseg.PlaneRANSAC(thresh=0.02).fit(pts)
    print("  pcseg.PlaneRANSAC(thresh=0.02).fit(cloud) -> plane", np.asarray(plane).shape,
          "inliers", int(np.asarray(inl).sum()), "/", len(pts))

    print("\n[spike OK] 統一 I/F(画像チェーン + 視覚設定オブジェクト + 長い尾エスケープ)が実装に薄く載って動作")


if __name__ == "__main__":
    _demo()
