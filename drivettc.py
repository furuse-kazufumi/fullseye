# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drivettc — 教習所の世界で τ 理論(Lee 1976)の「衝突までの時間」を、世界の側の真値で採点する。

Lee (1976) の τ は、近づく面の像が広がる速さだけで決まる衝突までの時間 —— 距離も速度も知らずに
``τ = Z / (−Ż)``(Z = 面までの奥行き)。等速なら **dτ/dt = −1**(1 秒に 1 秒ずつ減る)。
このモジュールは、その τ を **3 つの経路** で出して同じ世界で突き合わせる:

  1. **真値**(:func:`ttc_truth`): カメラの深度像(:func:`driveworld.world_camera` の ``depth``)と 2 コマの間の
     剛体運動 ``T_rel`` から、画素ごとの真の奥行き変化 → ``τ = Z₀ · Δt / (Z₀ − Z₁)``。閉形式、推定なし。
  2. **流れから**(:func:`ttc_from_flow`): 光学流(:func:`flow.optical_flow_lk` など、または :func:`flow_from_depth_motion`
     の真の流れ)→ :func:`sceneflow.time_to_contact`(画素ごと、拡大の中心 FoE からの半径 / 半径方向の流れ)→ 秒。
  3. **大きさから**(:func:`ttc_from_scale`): 対象の見かけの幅 w₀ → w₁ から ``τ₀ = Δt · w₁ / (w₁ − w₀)``。

恒等式(門になる): 純並進の剛体運動では、2 コマの差分の流れから :func:`sceneflow.time_to_contact` が返す値は
**ちょうど 1 コマ分 τ が減った値** ``τ₁ = τ₀ − Δt``(像点は FoE から ``Z₀/Z`` 倍の位置に写るので
``r² / (Δr · r) = Z₁ / (Z₀ − Z₁)``)。だから真の流れを入れると 1e-9 で一致し、推定した流れを入れたときの差は
すべて **流れの推定誤差** に帰着する。

フレーム規約(:mod:`render3d` / :mod:`driveworld` と同じ): カメラは −Z を見る(右 = +X、上 = +Y)、
``pose`` は world → camera の 4×4、``depth = −Z_c``、画素中心は整数座標(``col = fx·X/depth + cx``、
``row = cy − fy·Y/depth``)。流れの規約(:mod:`flow` と同じ): ``(x, y)`` の特徴が ``(x + u, y + v)`` へ動く。

参考: D. N. Lee, "A theory of visual control of braking based on information about time-to-collision",
*Perception* 5, 1976. Longuet-Higgins & Prazdny (1980) 拡大の中心。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "camera_backproject", "camera_project", "relative_motion", "foe_from_motion", "flow_from_depth_motion",
    "ttc_truth", "ttc_from_flow", "ttc_from_scale", "ttc_from_range", "label_extent",
]


def _K(K) -> np.ndarray:
    K = np.asarray(K, np.float64)
    if K.shape != (3, 3):
        raise ValueError("K must be 3x3")
    if not (K[0, 0] > 0 and K[1, 1] > 0):
        raise ValueError("K must have positive focal lengths")
    return K


def _T(T, name="T") -> np.ndarray:
    T = np.asarray(T, np.float64)
    if T.shape != (4, 4):
        raise ValueError("%s must be 4x4" % name)
    if not np.allclose(T[3], [0, 0, 0, 1]):
        raise ValueError("%s must be a homogeneous rigid transform (last row 0 0 0 1)" % name)
    return T


def _depth(depth) -> np.ndarray:
    Z = np.asarray(depth, np.float64)
    if Z.ndim != 2:
        raise ValueError("depth must be a 2-D (H, W) map")
    return Z


def camera_backproject(depth, K) -> np.ndarray:
    """深度像 (H, W) をカメラ座標の点 (H, W, 3) に戻す(render3d の規約: −Z が前、深度 = −Z_c)。

    深度が非有限か ≤ 0 の画素は NaN。画素中心は整数座標(``depth[r, c]`` は ``(u, v) = (c, r)`` の深度)。
    :func:`camera.depth_to_points` は OpenCV 規約(+Z 前)なので、driveworld のカメラにはこちらを使う。"""
    Z = _depth(depth)
    K = _K(K)
    H, W = Z.shape
    ok = np.isfinite(Z) & (Z > 0)
    d = np.where(ok, Z, np.nan)
    rr, cc = np.mgrid[0:H, 0:W].astype(np.float64)
    X = (cc - K[0, 2]) / K[0, 0] * d
    Y = (K[1, 2] - rr) / K[1, 1] * d
    return np.stack([X, Y, -d], axis=-1)


def camera_project(P, K):
    """カメラ座標の点 (..., 3) を画素へ: ``(col, row, depth)``(depth = −Z_c、≤ 0 は背後で col/row は NaN)。"""
    P = np.asarray(P, np.float64)
    if P.shape[-1] != 3:
        raise ValueError("points must be (..., 3)")
    K = _K(K)
    depth = -P[..., 2]
    safe = np.where(depth > 1e-12, depth, np.nan)
    col = K[0, 0] * (P[..., 0] / safe) + K[0, 2]
    row = K[1, 2] - K[1, 1] * (P[..., 1] / safe)
    return col, row, depth


def relative_motion(pose0, pose1, motion=None) -> np.ndarray:
    """2 コマの間の、カメラ座標で見た点の剛体運動 ``T_rel``(``P_c1 = T_rel · P_c0``)。

    ``pose0`` / ``pose1`` は各コマの world → camera(:func:`driveworld.camera_pose`)。``motion`` は対象が世界で動いた
    4×4(world → world、静止した世界なら None = 単位)。``T_rel = pose1 · motion · pose0⁻¹``。"""
    P0 = _T(pose0, "pose0")
    P1 = _T(pose1, "pose1")
    M = np.eye(4) if motion is None else _T(motion, "motion")
    return P1 @ M @ np.linalg.inv(P0)


def foe_from_motion(K, T_rel) -> np.ndarray:
    """拡大の中心(FoE)の画素 ``(col, row)``: 相対運動の並進 ``t`` を無限遠で投影した点。

    ``T_rel`` の回転が単位でないと FoE は定義されない(``ValueError``)。奥行き方向の並進が 0(純粋な横滑り)なら
    ``(nan, nan)``。"""
    K = _K(K)
    T = _T(T_rel, "T_rel")
    if not np.allclose(T[:3, :3], np.eye(3), atol=1e-9):
        raise ValueError("foe_from_motion: T_rel must be a pure translation (rotation makes the FoE undefined)")
    t = T[:3, 3]
    tz = -t[2]                                   # 前(−Z)へ向かう成分を正に
    if abs(tz) < 1e-12:
        return np.array([np.nan, np.nan])
    return np.array([K[0, 0] * t[0] / tz + K[0, 2], K[1, 2] - K[1, 1] * t[1] / tz])


def flow_from_depth_motion(depth, K, T_rel) -> dict:
    """深度像と剛体運動から **真の像の流れ**: ``{"u", "v", "valid", "depth1"}``(各 (H, W))。

    画素の 3-D 点を ``T_rel`` で動かして再投影し、``u = col₁ − col₀``、``v = row₁ − row₀``。動かした後に
    カメラの背後へ行く点や深度の無い画素は ``valid = False``(u, v は NaN)。``depth1`` は動かした後の深度。
    光学流の推定器の採点に使う真値(推定器と同じ規約: (x, y) → (x + u, y + v))。"""
    Z = _depth(depth)
    K = _K(K)
    T = _T(T_rel, "T_rel")
    H, W = Z.shape
    P0 = camera_backproject(Z, K)
    P1 = P0 @ T[:3, :3].T + T[:3, 3]
    col1, row1, d1 = camera_project(P1, K)
    rr, cc = np.mgrid[0:H, 0:W].astype(np.float64)
    valid = np.isfinite(Z) & (Z > 0) & np.isfinite(col1) & np.isfinite(row1) & (d1 > 0)
    u = np.where(valid, col1 - cc, np.nan)
    v = np.where(valid, row1 - rr, np.nan)
    return {"u": u, "v": v, "valid": valid, "depth1": np.where(valid, d1, np.nan)}


def ttc_truth(depth, K, T_rel, dt: float) -> dict:
    """画素ごとの **真の τ**(秒、最初のコマの時刻で)と閉じる速さ: ``{"tau", "closing_speed", "depth1", "valid"}``。

    ``τ₀ = Z₀ · Δt / (Z₀ − Z₁)``(Lee 1976 の ``Z / (−Ż)`` を 2 コマの差分で。等速なら厳密)。近づかない画素
    (``Z₁ ≥ Z₀``)は ``inf``。``closing_speed = (Z₀ − Z₁) / Δt``(m/s、正 = 近づく)。"""
    if not (dt > 0):
        raise ValueError("dt must be positive")
    Z = _depth(depth)
    f = flow_from_depth_motion(Z, K, T_rel)
    d1 = f["depth1"]
    dz = Z - d1
    closing = dz / float(dt)
    tau = np.full(Z.shape, np.inf)
    ok = f["valid"] & (dz > 1e-12)
    tau[ok] = Z[ok] * float(dt) / dz[ok]
    tau[~f["valid"]] = np.nan
    return {"tau": tau, "closing_speed": np.where(f["valid"], closing, np.nan), "depth1": d1, "valid": f["valid"]}


def ttc_from_flow(u, v, dt: float, *, foe=None, mask=None, min_speed: float = 1e-3, at_first_frame: bool = True) -> dict:
    """光学流から τ(秒): ``{"tau_map", "tau", "n", "foe"}``。

    :func:`sceneflow.time_to_contact`(画素ごと、コマ単位、FoE からの半径² / 半径方向の流れ)を秒に直す。
    2 コマの差分の流れが返すのは **2 コマ目の時刻の τ**(``Z₁ / (Z₀ − Z₁)`` コマ)なので、``at_first_frame=True``
    (既定)は 1 コマ足して最初のコマの τ にする(等速なら厳密、:func:`ttc_truth` と同じ時刻)。
    ``foe`` を省くと流れから推定する(:func:`sceneflow.focus_of_expansion`)。真の FoE は :func:`foe_from_motion`。
    ``tau`` は ``mask``(省略時は全画素)の中で有限・正の τ の中央値(無ければ ``inf``)、``n`` はその画素数。"""
    import sceneflow
    if not (dt > 0):
        raise ValueError("dt must be positive")
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    if u.shape != v.shape or u.ndim != 2:
        raise ValueError("u and v must be equal-shape 2-D flow fields")
    uf = np.where(np.isfinite(u), u, 0.0)
    vf = np.where(np.isfinite(v), v, 0.0)
    if foe is None:
        foe = sceneflow.focus_of_expansion(uf, vf, min_speed)
    foe = np.asarray(foe, np.float64).reshape(2)
    if not np.all(np.isfinite(foe)):
        nan = np.full(u.shape, np.nan)
        return {"tau_map": nan, "tau": float("inf"), "n": 0, "foe": foe}
    frames = sceneflow.time_to_contact(uf, vf, foe=foe, min_speed=min_speed)
    tau = frames * float(dt)
    if at_first_frame:
        tau = np.where(np.isfinite(tau), tau + float(dt), tau)
    tau[~(np.isfinite(u) & np.isfinite(v))] = np.nan
    sel = np.isfinite(tau) & (tau > 0)
    if mask is not None:
        m = np.asarray(mask, bool)
        if m.shape != u.shape:
            raise ValueError("mask must have the flow's shape")
        sel &= m
    n = int(sel.sum())
    rep = float(np.median(tau[sel])) if n else float("inf")
    return {"tau_map": tau, "tau": rep, "n": n, "foe": foe}


def ttc_from_scale(w0: float, w1: float, dt: float) -> float:
    """見かけの大きさの変化から τ(秒、最初のコマの時刻で): ``τ₀ = Δt · w₁ / (w₁ − w₀)``。

    像の幅は奥行きに反比例(``w ∝ 1/Z``)なので ``w₀/w₁ = Z₁/Z₀`` → ``τ₀ = Z₀ Δt / (Z₀ − Z₁) = Δt / (1 − w₀/w₁)``。
    Lee の ``θ/θ̇`` を前進差分にした ``Δt · w₀ / (w₁ − w₀)`` は 2 コマ目の τ で、ちょうど Δt 小さい。
    大きくならなければ(``w₁ ≤ w₀``)``inf``。幅は正でなければ ``ValueError``。"""
    w0 = float(w0)
    w1 = float(w1)
    if not (w0 > 0 and w1 > 0):
        raise ValueError("widths must be positive")
    if not (dt > 0):
        raise ValueError("dt must be positive")
    if w1 <= w0:
        return float("inf")
    return float(dt) * w1 / (w1 - w0)


def ttc_from_range(distance: float, closing_speed: float) -> float:
    """距離と閉じる速さから τ = d / v(秒)。世界の姿勢から出す真値(v ≤ 0 なら ``inf``、d < 0 は ``ValueError``)。"""
    d = float(distance)
    if d < 0:
        raise ValueError("distance must be non-negative")
    v = float(closing_speed)
    if v <= 0:
        return float("inf")
    return d / v


def label_extent(label, value: int) -> dict:
    """ラベル像の中で値 ``value`` の画素の箱: ``{"col0", "col1", "row0", "row1", "width", "height", "n"}``。

    幅・高さは画素数(``col1 − col0 + 1``)。無ければ全部 0。:func:`ttc_from_scale` の入力(完全な検出器の代役)。"""
    L = np.asarray(label)
    if L.ndim != 2:
        raise ValueError("label must be 2-D")
    m = L == int(value)
    if not m.any():
        return {"col0": 0, "col1": 0, "row0": 0, "row1": 0, "width": 0, "height": 0, "n": 0}
    rows = np.where(m.any(axis=1))[0]
    cols = np.where(m.any(axis=0))[0]
    return {"col0": int(cols[0]), "col1": int(cols[-1]), "row0": int(rows[0]), "row1": int(rows[-1]),
            "width": int(cols[-1] - cols[0] + 1), "height": int(rows[-1] - rows[0] + 1), "n": int(m.sum())}
