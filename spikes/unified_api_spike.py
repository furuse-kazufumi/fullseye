"""Fullseye 統一 I/F — 小 spike (Qt 風・設定オブジェクト+動詞メソッド).

要件定義 docs/UNIFIED_API_REQUIREMENTS.md の §7 設計方針を、既存 perception 実装の
**薄いラッパ**で具体化する additive な spike(既存 op を一切変更しない・throwaway 可)。
狙い: 使う側のサンプルコードが Qt ウィジェット風に自然に読めることを実コードで示す。

    depth = stereo.SGM(max_disp=64).compute(left, right)
    cloud = camera.Pinhole(K).backproject(depth)
    plane = pcseg.PlaneRANSAC(thresh=0.02).fit(cloud)

内部は fullseye facade を呼ぶだけ(disparity_sgm / depth_to_points / fit_plane_ransac)。
本 spike は §9 判断の既定(混成・eager・一般語彙・API 先行)に基づく。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import fullseye as fs


# ── stereo(名前空間モジュール風)─────────────────────────────────────────── #
@dataclass
class SGM:
    """Semi-Global Matching の設定オブジェクト。`compute(left, right)` で視差を返す。

    Qt 風: 設定(パラメータ)を構築時に持ち、動詞メソッドで実行する。既定は sensible。
    """
    max_disp: int = 64
    window: int = 5
    P1: float = 5.0
    P2: float = 50.0
    paths: int = 4

    def compute(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        return fs.disparity_sgm(left, right, max_disp=self.max_disp, window=self.window,
                                P1=self.P1, P2=self.P2, paths=self.paths)


# ── camera(名前空間モジュール風)────────────────────────────────────────── #
@dataclass
class Pinhole:
    """ピンホールカメラ(内部行列 K)。`backproject(depth)` で 3D 点群に戻す。"""
    K: np.ndarray

    def backproject(self, depth: np.ndarray, organized: bool = False):
        return fs.depth_to_points(depth, self.K, organized=organized)


# ── pcseg(名前空間モジュール風)─────────────────────────────────────────── #
@dataclass
class PlaneRANSAC:
    """RANSAC 平面当てはめ。`fit(points)` で (平面, インライア) を返す。"""
    thresh: float = 0.02
    iters: int = 200
    seed: int = 0

    def fit(self, points: np.ndarray):
        return fs.fit_plane_ransac(points, thresh=self.thresh, iters=self.iters, seed=self.seed)


def _demo() -> None:
    rng = np.random.default_rng(0)

    # 1) stereo: 小さな合成ステレオ対 → 視差
    left = rng.random((32, 48)).astype(np.float64)
    right = np.roll(left, 2, axis=1)          # 2px シフト = 視差 ~2 の合成対
    disp = SGM(max_disp=8, window=5).compute(left, right)
    print("stereo.SGM(max_disp=8).compute(l, r)      ->", type(disp).__name__, getattr(disp, "shape", None))

    # 2) camera: 合成 depth + K → 点群
    K = np.array([[50.0, 0, 24.0], [0, 50.0, 16.0], [0, 0, 1.0]])
    depth = np.full((32, 48), 3.0)
    cloud = Pinhole(K).backproject(depth)
    cloud_arr = cloud if isinstance(cloud, np.ndarray) else np.asarray(cloud)
    print("camera.Pinhole(K).backproject(depth)      ->", type(cloud).__name__, cloud_arr.shape)

    # 3) pcseg: 合成平面点群 → RANSAC 平面
    xs, ys = np.meshgrid(np.linspace(-1, 1, 20), np.linspace(-1, 1, 20))
    plane_pts = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])   # z=0 平面
    plane_pts += rng.normal(0, 0.002, plane_pts.shape)                          # 微小ノイズ
    result = PlaneRANSAC(thresh=0.02).fit(plane_pts)
    print("pcseg.PlaneRANSAC(thresh=0.02).fit(cloud)  ->", type(result).__name__,
          [type(x).__name__ for x in result] if isinstance(result, tuple) else "")

    print("\n[spike OK] 設定オブジェクト+動詞メソッドの統一 I/F が実実装に薄く載って動作")


if __name__ == "__main__":
    _demo()
