# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pcl_augment — 3D 点群 (N,3) のデータ拡張(Physical AI 学習支援, numpy+scipy)。

学習用の点群を「もっともらしくランダムに崩した variant」へ増やすための拡張群。
深度/ステレオ/LiDAR から起こした点群で 6-DoF 姿勢推定・把持・セグメンテーションの
方策を鍛えるとき、クリーンな 1 サンプルからセンサ揺らぎ・視点変化・欠損を模した
多数の学習サンプルを decision-free に生成する(古典的 domain randomisation)。

姉妹モジュールとの棲み分け(固有価値):
    - :mod:`pcl_filter` は雲を「整える」決定論的フィルタ(外れ値除去・voxel 間引き)。
      本モジュールは逆に、学習を頑健化するため雲を「確率的に崩す」。
    - :mod:`deform3d` は与えた対応へ滑らかな写像を「当てはめる」非剛体レジストレーション。
      本モジュールの ``elastic_deform`` は対応を必要とせず、乱数変位場そのものを生成する。
    - :mod:`backends_aug` は 2D 画像のセンサ劣化。本モジュールは 3D 点群専用で無関係。

決定論: すべての公開 API は ``seed`` で完全再現(同 seed→同結果, 異 seed→相違)。
座標系: ``points`` = (N, 3) の float、単位はワールド/カメラ実寸。cv2/skimage 不使用、
近傍探索のみ ``scipy.spatial.cKDTree``。

参考(公開): Simard et al. "Best Practices for CNN" (2003, elastic deformation)、
DeVries & Taylor "Improved Regularization ... with Cutout" (2017)、
Shoemake "Uniform Random Rotations" (Graphics Gems III, 1992)。
"""
from __future__ import annotations

from typing import Optional, Union, Mapping, Any, Tuple

import numpy as np

__all__ = [
    "jitter",
    "random_rotation",
    "random_scale",
    "random_dropout",
    "elastic_deform",
    "cutout",
    "augment",
]


# --------------------------------------------------------------------------- #
# 入力正規化                                                                  #
# --------------------------------------------------------------------------- #
def _as_points(a, name: str = "points") -> np.ndarray:
    """array-like を float64 の ``(N,3)`` 配列へ正規化する(型だけでなく実次元を検証)。

    長さ 3 の 1 次元入力は単一点として ``(1,3)`` に昇格。形状が不正なら ``ValueError``
    を送出する(縮退入力を黙って通さない = fail-closed, note_15 Class B)。"""
    arr = np.asarray(a, dtype=np.float64)
    if arr.ndim == 1:
        if arr.shape[0] != 3:
            raise ValueError(f"{name}: 1-D input must have length 3, got {arr.shape[0]}")
        arr = arr.reshape(1, 3)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"{name} must be (N, 3), got shape {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")
    return arr


def _seed_children(seed: int, n: int) -> list[int]:
    """1 つの seed から独立・決定論的な子 seed を ``n`` 個生成(段間の相関を断つ)。"""
    ss = np.random.SeedSequence(int(seed))
    return [int(s.generate_state(1, dtype=np.uint32)[0]) for s in ss.spawn(n)]


# --------------------------------------------------------------------------- #
# jitter                                                                      #
# --------------------------------------------------------------------------- #
def jitter(points, sigma: float, clip: Optional[float] = None, seed: int = 0) -> np.ndarray:
    """各点に等方ガウスノイズ ``N(0, sigma)`` を付加(センサ位置ノイズの模倣)。

    ``sigma`` はワールド単位の標準偏差(ユーザ指定パラメータ)。``clip`` を与えると
    各成分の変位を ``[-clip, clip]`` に切り詰める(外れ変位の抑制)。大 N ではノイズの
    平均≈0・標準偏差≈sigma となる。返り値は入力と同形状 ``(N,3)``。"""
    P = _as_points(points)
    sigma = float(sigma)
    if sigma < 0.0:
        raise ValueError("sigma must be >= 0")
    if P.shape[0] == 0 or sigma == 0.0:
        return P.copy()
    rng = np.random.default_rng(int(seed))
    noise = rng.normal(0.0, sigma, size=P.shape)
    if clip is not None:
        c = float(clip)
        if c <= 0.0:
            raise ValueError("clip must be > 0 when given")
        noise = np.clip(noise, -c, c)
    return P + noise


# --------------------------------------------------------------------------- #
# random_rotation                                                             #
# --------------------------------------------------------------------------- #
def _quat_to_matrix(q: np.ndarray) -> np.ndarray:
    """単位クォータニオン ``[w,x,y,z]`` → 正規直交回転行列(det=+1)。"""
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w),     2 * (x * z + y * w)],
        [2 * (x * y + z * w),     1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w),     2 * (y * z + x * w),     1 - 2 * (x * x + y * y)],
    ], dtype=np.float64)


def random_rotation(points, seed: int = 0,
                    max_angle: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
    """ランダム回転を適用し ``(rotated, R)`` を返す(視点変化の模倣)。

    ``R`` は正規直交・``det=+1``(``rotated = points @ R.T`` = 各点に ``R`` を左作用、
    逆変換は ``rotated @ R``)。``max_angle=None`` なら Shoemake 法で一様ランダム回転、
    ``max_angle`` 指定(ラジアン, 期待 ``[0, π]``)なら軸を球面一様・角を ``[0, max_angle]``
    一様に取り、回転角を制限する(``arccos((tr R -1)/2) ≤ max_angle`` を厳密に保証)。"""
    P = _as_points(points)
    rng = np.random.default_rng(int(seed))

    if max_angle is None:
        # Shoemake: 単位クォータニオンを一様サンプル → det=+1 の Haar 回転。
        u1, u2, u3 = rng.random(3)
        q = np.array([
            np.sqrt(u1) * np.cos(2 * np.pi * u3),        # w
            np.sqrt(1 - u1) * np.sin(2 * np.pi * u2),    # x
            np.sqrt(1 - u1) * np.cos(2 * np.pi * u2),    # y
            np.sqrt(u1) * np.sin(2 * np.pi * u3),        # z
        ], dtype=np.float64)
        R = _quat_to_matrix(q)
    else:
        ma = float(max_angle)
        if ma < 0.0:
            raise ValueError("max_angle must be >= 0")
        # 軸: 3D ガウスを正規化して球面一様。角: [0, max_angle] 一様。
        axis = rng.standard_normal(3)
        nrm = np.linalg.norm(axis)
        if nrm < 1e-12:                                  # 極稀な零ベクトル → 既定軸
            axis = np.array([0.0, 0.0, 1.0])
            nrm = 1.0
        axis = axis / nrm
        theta = rng.uniform(0.0, ma)
        # Rodrigues の公式で軸角 → 回転行列。
        K = np.array([
            [0.0, -axis[2], axis[1]],
            [axis[2], 0.0, -axis[0]],
            [-axis[1], axis[0], 0.0],
        ], dtype=np.float64)
        R = np.eye(3) + np.sin(theta) * K + (1 - np.cos(theta)) * (K @ K)

    rotated = P @ R.T
    return rotated, R


# --------------------------------------------------------------------------- #
# random_scale                                                                #
# --------------------------------------------------------------------------- #
def random_scale(points, lo: float, hi: float, seed: int = 0) -> Tuple[np.ndarray, float]:
    """一様スケール ``s ~ U(lo, hi)`` を原点まわりに適用し ``(scaled, s)`` を返す。

    ``scaled = points * s``。bbox 対角長はちょうど ``s`` 倍になる(``s > 0`` なので
    ``max``/``min`` が共に ``s`` 倍 → 対角 ``‖max-min‖`` も ``s`` 倍)。物体スケールの
    ばらつき(距離/センサ倍率)を学習に注入する。``0 < lo <= hi`` を要求(fail-closed)。"""
    P = _as_points(points)
    lo = float(lo)
    hi = float(hi)
    if not (lo > 0.0):
        raise ValueError("lo must be > 0 (scale factor)")
    if hi < lo:
        raise ValueError("hi must be >= lo")
    rng = np.random.default_rng(int(seed))
    s = float(rng.uniform(lo, hi))
    return P * s, s


# --------------------------------------------------------------------------- #
# random_dropout                                                              #
# --------------------------------------------------------------------------- #
def random_dropout(points, ratio: float, seed: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    """点の ``ratio`` 割合をランダム除去し ``(kept, kept_idx)`` を返す(欠損の模倣)。

    残す点数は ``round((1-ratio)*N)``。``kept_idx`` は元配列への昇順インデックスで、
    ``kept == points[kept_idx]`` が厳密に成り立つ。オクルージョン/疎な視点による
    点欠損を学習で再現する。``0 <= ratio <= 1`` を要求。"""
    P = _as_points(points)
    ratio = float(ratio)
    if not (0.0 <= ratio <= 1.0):
        raise ValueError("ratio must be in [0, 1]")
    n = P.shape[0]
    keep = int(round((1.0 - ratio) * n))
    keep = max(0, min(n, keep))
    rng = np.random.default_rng(int(seed))
    kept_idx = np.sort(rng.permutation(n)[:keep]).astype(np.int64)
    return P[kept_idx], kept_idx


# --------------------------------------------------------------------------- #
# elastic_deform                                                              #
# --------------------------------------------------------------------------- #
def elastic_deform(points, sigma: float, alpha: float, seed: int = 0) -> np.ndarray:
    """滑らかな乱数変位場で弾性変形(相関距離 ``sigma``, RMS 振幅 ``alpha``)。

    各点に独立ガウス乱数ベクトルを置き、空間ガウス重み ``exp(-d²/2σ²)`` で平滑化した
    変位場を生成する(近接点は coherent に動く)。場は RMS を 1 に正規化してから
    ``alpha`` 倍するので、変位の RMS ノルムはちょうど ``alpha`` になる(``σ→∞`` で場は
    定数=剛体並進, ``σ→0`` で各点独立)。非剛体な物体変形/柔軟物の学習に。

    注意(honest): 近傍探索は ``cKDTree.query_pairs(r=3σ)``。``σ`` が雲の直径に近いほど
    ペア数は O(N²) に近づくため、大規模雲では ``σ`` を局所スケールに保つこと。"""
    P = _as_points(points)
    sigma = float(sigma)
    alpha = float(alpha)
    if sigma < 0.0:
        raise ValueError("sigma must be >= 0")
    n = P.shape[0]
    if n == 0:
        return P.copy()
    rng = np.random.default_rng(int(seed))
    raw = rng.standard_normal((n, 3))

    if sigma == 0.0 or n == 1:
        disp = raw
    else:
        from scipy.spatial import cKDTree
        num = raw.copy()                        # 自己重み 1 * raw_i
        den = np.ones(n)
        r = 3.0 * sigma
        pairs = cKDTree(P).query_pairs(r, output_type="ndarray")
        if pairs.size:
            i = pairs[:, 0]
            j = pairs[:, 1]
            d2 = np.sum((P[i] - P[j]) ** 2, axis=1)
            w = np.exp(-d2 / (2.0 * sigma * sigma))
            np.add.at(num, i, w[:, None] * raw[j])
            np.add.at(num, j, w[:, None] * raw[i])
            np.add.at(den, i, w)
            np.add.at(den, j, w)
        disp = num / den[:, None]

    rms = np.sqrt(np.mean(np.sum(disp ** 2, axis=1)))
    if rms > 0.0:
        disp = disp / rms                       # RMS ノルム = 1 に正規化
    return P + alpha * disp


# --------------------------------------------------------------------------- #
# cutout                                                                       #
# --------------------------------------------------------------------------- #
def cutout(points, extent: Union[float, np.ndarray], seed: int = 0
           ) -> Tuple[np.ndarray, np.ndarray]:
    """空間的な軸平行ボックス領域を除去し ``(kept, kept_idx)`` を返す(局所欠損の模倣)。

    既存の点を 1 つ一様サンプルして中心とし、辺長 ``extent``(スカラ=立方体, または
    ``(3,)``=各軸辺長)のボックス内の点をすべて除去する。中心点自身が必ず入るため
    最低 1 点は除去される。除去点は必ず辺長 ``extent`` のボックスに収まる(空間的に
    局所的 = ランダム散布とは判別可能)。``kept == points[kept_idx]``、``extent > 0``。"""
    P = _as_points(points)
    ext = np.asarray(extent, dtype=np.float64)
    if ext.ndim == 0:
        ext = np.full(3, float(ext))
    if ext.shape != (3,):
        raise ValueError("extent must be a scalar or shape (3,)")
    if not np.all(ext > 0.0):
        raise ValueError("extent must be > 0")
    n = P.shape[0]
    if n == 0:
        return P.copy(), np.empty(0, np.int64)
    rng = np.random.default_rng(int(seed))
    center = P[int(rng.integers(n))]
    half = ext / 2.0
    inside = np.all(np.abs(P - center) <= half, axis=1)
    kept_idx = np.where(~inside)[0].astype(np.int64)
    return P[kept_idx], kept_idx


# --------------------------------------------------------------------------- #
# augment (合成)                                                             #
# --------------------------------------------------------------------------- #
# 段の適用順(固定): 幾何変換 → ノイズ → 点除去。段ごとに独立な子 seed を割り当てる。
_STAGE_ORDER = ("rotation", "scale", "elastic", "jitter", "dropout", "cutout")


def augment(points, config: Mapping[str, Any], seed: int = 0) -> np.ndarray:
    """``config`` に従い各拡張を合成適用し点群を返す(決定論, ``seed`` 依存)。

    ``config`` は段名→パラメータ dict のマップ。適用順は固定で
    ``rotation → scale → elastic → jitter → dropout → cutout``。存在する段のみ実行し、
    各段には ``seed`` から派生した独立子 seed を与える。段名/パラメータ例::

        {"rotation": {"max_angle": 0.2}, "scale": {"lo": 0.9, "hi": 1.1},
         "elastic": {"sigma": 0.1, "alpha": 0.02}, "jitter": {"sigma": 0.01, "clip": 0.03},
         "dropout": {"ratio": 0.1}, "cutout": {"extent": 0.1}}

    返り値は変換後の ``(M,3)`` 点群のみ(``R``/``s``/``idx`` は破棄)。未知の段名は
    ``ValueError``(タイポを黙って無視しない = fail-closed)。"""
    P = _as_points(points)
    unknown = set(config) - set(_STAGE_ORDER)
    if unknown:
        raise ValueError(f"unknown augmentation stage(s): {sorted(unknown)}")

    child = _seed_children(seed, len(_STAGE_ORDER))
    for k, stage in enumerate(_STAGE_ORDER):
        if stage not in config:
            continue
        p = dict(config[stage] or {})
        s = child[k]
        if stage == "rotation":
            P, _ = random_rotation(P, seed=s, max_angle=p.get("max_angle"))
        elif stage == "scale":
            P, _ = random_scale(P, lo=p["lo"], hi=p["hi"], seed=s)
        elif stage == "elastic":
            P = elastic_deform(P, sigma=p["sigma"], alpha=p["alpha"], seed=s)
        elif stage == "jitter":
            P = jitter(P, sigma=p["sigma"], clip=p.get("clip"), seed=s)
        elif stage == "dropout":
            P, _ = random_dropout(P, ratio=p["ratio"], seed=s)
        elif stage == "cutout":
            P, _ = cutout(P, extent=p["extent"], seed=s)
    return P
