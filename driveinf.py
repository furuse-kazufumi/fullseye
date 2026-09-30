# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""終わらない地図(区画を作り足し、離れた区画を捨てる): 決定的な区画の生成と、桁の落ちない座標。

世界を一辺 ``tile`` m の区画 (i, j)(整数)に分け、車の周りの区画だけを持つ。区画の中身は**区画の番号と世界の種だけ**で
決まる(乱数の状態を持ち越さない)ので、捨てた区画に戻ってきても 1 ビットも違わずに作り直せ、作る順番にも依らない。

- 位置は (i, j, 区画の中の x, y) で持つ(:func:`pose_normalize`)。全体の座標 (i·T + x) を浮動小数で持つと、遠くへ行くほど
  刻みが粗くなる(float32 なら 100 km で 8 mm、GPU の頂点は float32)。区画の中の座標は常に [0, T) なので刻みは一定。
- 起伏は全体で共通の整数格子(格子の番号 = 区画の番号 × 区画あたりの升目数 + 区画の中の升目の番号 —— 整数なので厳密)に
  置いた Perlin 雑音(勾配は格子の番号のハッシュ)。区画の中の小数だけで補間するので、区画の継ぎ目で連続し、桁も落ちない。
- 道は区画の辺ごとに「その辺を道が横切るか・どこで横切るか」を**辺の番号のハッシュ**で決める(両側の区画が同じ辺を同じ値で
  読む)ので、継ぎ目で必ずつながる。区画の中は、横切る点を区画の中の分岐点へ直線で結ぶ。道の周りは起伏を平らにする
  (隣の区画の道も見る —— 継ぎ目の近くの平らにする量が両側で一致するように)。

ハッシュは SplitMix64(Steele, Lea, Flood 2014)を整数だけで計算する(環境に依らない)。
"""
from __future__ import annotations

import hashlib

import numpy as np

__all__ = [
    "tile_hash", "tile_uniform", "pose_normalize", "tile_params", "tile_edge_crossing", "tile_roads", "tile_road_distance",
    "tile_height", "tile_mesh", "tile_digest", "tile_stream", "global_to_tile",
]

_M64 = (1 << 64) - 1


def _splitmix64(x: int) -> int:
    x = (x + 0x9E3779B97F4A7C15) & _M64
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _M64
    return z ^ (z >> 31)


def tile_hash(i: int, j: int, seed: int, salt: int = 0) -> int:
    """区画(か格子点・辺)の番号 (i, j) と世界の種・用途の塩から 64 ビットの整数を出す(SplitMix64 を 4 回、整数だけ)。
    負の番号も扱う(2 の補数で 64 ビットに折る)。同じ入力なら環境に依らず同じ値。"""
    h = _splitmix64(int(seed) & _M64)
    for v in (int(i), int(j), int(salt)):
        h = _splitmix64(h ^ (v & _M64))
    return h


def tile_uniform(i: int, j: int, seed: int, salt: int = 0) -> float:
    """:func:`tile_hash` の上位 53 ビットを [0, 1) の一様な実数に(倍精度で厳密に表せる)。"""
    return (tile_hash(i, j, seed, salt) >> 11) * (1.0 / (1 << 53))


def pose_normalize(i: int, j: int, x: float, y: float, tile: float):
    """(区画, 区画の中の座標) を、座標が [0, tile) に入るように区画を繰り上げ・繰り下げる。返り値 (i, j, x, y)。
    ★全体の座標に足してから割り直すのでなく、区画の中の座標だけを動かす —— 刻みが距離に依らない。"""
    if not (tile > 0):
        raise ValueError("tile must be positive")
    di, x = divmod(float(x), float(tile))
    dj, y = divmod(float(y), float(tile))
    return int(i) + int(di), int(j) + int(dj), float(x), float(y)


def global_to_tile(X: float, Y: float, tile: float):
    """全体の座標 → (i, j, x, y)(比較用。遠い座標は既に浮動小数の刻みで丸まっている)。"""
    return pose_normalize(0, 0, X, Y, tile)


def tile_params(tile: float = 200.0, cells: int = 8, relief: float = 6.0, road_width: float = 7.0, flat: float = 18.0,
                blend: float = 20.0, p_road: float = 0.85, jitter: float = 0.25, seed: int = 20261001) -> dict:
    """区画の表。``tile`` = 一辺 [m]、``cells`` = 区画あたりの格子の升目数(起伏の波長 ≈ tile/cells)、``relief`` = 起伏の振幅 [m]、
    ``road_width`` [m]、道から ``flat`` m は平ら、そこから ``blend`` m で起伏へ戻す(★flat は地面の格子の三角形が道に掛かっても
    地面が道より上に出ない幅: 道幅の半分 + 格子の対角 —— 10 m の格子で 3.5 + 14.1 ≈ 18 m。6 m では道が地面に埋もれた)、``p_road`` = 辺を道が横切る確率、
    ``jitter`` = 区画の中の分岐点のずらし(区画の一辺に対する割合)、``seed`` = 世界の種。"""
    if tile <= 0 or cells < 1 or not (0 <= p_road <= 1) or not (0 <= jitter < 0.5) or flat < 0 or blend <= 0:
        raise ValueError("bad tile parameters")
    return {"tile": float(tile), "cells": int(cells), "relief": float(relief), "road_width": float(road_width), "flat": float(flat),
            "blend": float(blend), "p_road": float(p_road), "jitter": float(jitter), "seed": int(seed)}


def tile_edge_crossing(i: int, j: int, side: str, tp: dict):
    """区画 (i, j) の辺を道が横切る位置(区画の中の座標、辺に沿った 0..tile)。無ければ None。
    ``side`` ∈ {"E", "W", "N", "S"}。★辺の番号で決める: 区画 (i, j) の E と区画 (i+1, j) の W は同じ辺(同じハッシュ)。"""
    T = tp["tile"]
    if side == "E":
        key = (2 * (int(i) + 1), int(j))
    elif side == "W":
        key = (2 * int(i), int(j))
    elif side == "N":
        key = (int(i), 2 * (int(j) + 1) + 1)
    elif side == "S":
        key = (int(i), 2 * int(j) + 1)
    else:
        raise ValueError("side must be E/W/N/S")
    # 縦の辺(E/W)は番号の第 1 成分が偶数、横の辺(N/S)は第 2 成分が奇数 —— 塩で分けて衝突しないように
    salt = 1 if side in ("E", "W") else 2
    if tile_uniform(key[0], key[1], tp["seed"], salt) >= tp["p_road"]:
        return None
    return T * (0.2 + 0.6 * tile_uniform(key[0], key[1], tp["seed"], salt + 10))


def tile_roads(i: int, j: int, tp: dict) -> dict:
    """区画の中の道: 横切る点(区画の中の座標)と分岐点、分岐点から各点への線分。返り値
    ``{"hub" (2,), "ends" [(side, (x, y))], "segments" (K, 2, 2)}``(横切る点が無ければ空)。"""
    T = tp["tile"]
    hub = T * (0.5 + tp["jitter"] * (2 * np.array([tile_uniform(i, j, tp["seed"], 3), tile_uniform(i, j, tp["seed"], 4)]) - 1))
    ends = []
    for side in ("E", "W", "N", "S"):
        c = tile_edge_crossing(i, j, side, tp)
        if c is None:
            continue
        pt = {"E": (T, c), "W": (0.0, c), "N": (c, T), "S": (c, 0.0)}[side]
        ends.append((side, pt))
    segs = np.array([[hub, np.asarray(pt, float)] for _, pt in ends]) if ends else np.zeros((0, 2, 2))
    return {"hub": hub, "ends": ends, "segments": segs}


def _seg_distance(P, segs):
    """点 (N, 2) から線分の束 (K, 2, 2) への最短距離 (N,)(線分が無ければ inf)。"""
    if len(segs) == 0:
        return np.full(len(P), np.inf)
    a = segs[:, 0][None]
    b = segs[:, 1][None]
    ab = b - a
    t = np.clip(np.sum((P[:, None] - a) * ab, -1) / np.maximum(np.sum(ab * ab, -1), 1e-300), 0.0, 1.0)
    q = a + t[..., None] * ab
    return np.sqrt(np.sum((P[:, None] - q) ** 2, -1)).min(axis=1)


def tile_road_distance(i: int, j: int, x, y, tp: dict) -> np.ndarray:
    """区画 (i, j) の中の点 (x, y)(区画の中の座標)から最寄りの道の中心線までの距離。★隣の 8 区画の道も見る
    (隣の道を区画の中の座標へずらして)—— 継ぎ目の近くで両側の区画が同じ距離を出すため。"""
    T = tp["tile"]
    P = np.column_stack([np.ravel(x), np.ravel(y)]).astype(np.float64)
    d = np.full(len(P), np.inf)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            segs = tile_roads(i + di, j + dj, tp)["segments"]
            if len(segs):
                d = np.minimum(d, _seg_distance(P, segs + np.array([di * T, dj * T])))
    return d.reshape(np.shape(x))


def _grad(ix, iy, seed):
    """格子点 (ix, iy)(全体の整数の番号)の勾配: 単位円上の角 = ハッシュ。ix, iy は int64 の配列。"""
    ang = np.empty(ix.shape)
    flat_i, flat_j = ix.ravel(), iy.ravel()
    out = ang.ravel()
    for k in range(flat_i.size):
        out[k] = 2 * np.pi * tile_uniform(int(flat_i[k]), int(flat_j[k]), seed, 7)
    return np.cos(ang), np.sin(ang)


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


def tile_height(i: int, j: int, x, y, tp: dict) -> np.ndarray:
    """区画 (i, j) の中の点 (x, y) の地面の高さ [m]: 全体の整数格子の Perlin 雑音 × relief、道の周りは平ら
    (``flat`` m まで 0、``blend`` m で smoothstep)。格子の番号 = 区画の番号 × cells + 升目の番号(整数で厳密)、
    補間は升目の中の小数だけ —— 継ぎ目で連続し、遠くでも桁が落ちない。"""
    T, n = tp["tile"], tp["cells"]
    c = T / n
    x = np.asarray(x, np.float64)
    y = np.asarray(y, np.float64)
    gx, gy = x / c, y / c
    cx = np.clip(np.floor(gx).astype(np.int64), 0, n - 1)      # 区画の中の升目(x = T ちょうどは最後の升目の右端)
    cy = np.clip(np.floor(gy).astype(np.int64), 0, n - 1)
    fx, fy = gx - cx, gy - cy
    ix0 = int(i) * n + cx
    iy0 = int(j) * n + cy
    val = np.zeros_like(fx)
    u, v = _fade(fx), _fade(fy)
    for ox, oy, wx, wy in ((0, 0, 1 - u, 1 - v), (1, 0, u, 1 - v), (0, 1, 1 - u, v), (1, 1, u, v)):
        gxv, gyv = _grad(ix0 + ox, iy0 + oy, tp["seed"])
        val = val + wx * wy * (gxv * (fx - ox) + gyv * (fy - oy))
    h = tp["relief"] * val
    d = tile_road_distance(i, j, x, y, tp)
    s = np.clip((d - tp["flat"]) / tp["blend"], 0.0, 1.0)
    return h * (s * s * (3 - 2 * s))


def tile_mesh(i: int, j: int, tp: dict, step: float = 10.0) -> dict:
    """区画 (i, j) の地面の格子メッシュ(区画の中の座標)と道の面。返り値 ``{"V" (N, 3), "F" (M, 3), "label" (M,),
    "color" (M, 3), "roads" (tile_roads の返り値)}``。地面 = ラベル 0、道 = ラベル 1(道は地面の少し上の帯)。"""
    T = tp["tile"]
    k = int(round(T / step))
    if k < 1 or abs(k * step - T) > 1e-9 * T:
        raise ValueError("step must divide the tile size")
    xs = np.linspace(0.0, T, k + 1)
    X, Y = np.meshgrid(xs, xs)
    Z = tile_height(i, j, X, Y, tp)
    V = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    idx = np.arange((k + 1) ** 2).reshape(k + 1, k + 1)
    a, b, c_, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()
    F = np.concatenate([np.column_stack([a, b, c_]), np.column_stack([a, c_, d])])
    col = np.tile([[0.32, 0.52, 0.26]], (len(F), 1))
    lab = np.zeros(len(F), np.int64)
    roads = tile_roads(i, j, tp)
    Vs, Fs = [V], [F]
    base = len(V)
    hw = 0.5 * tp["road_width"]
    nr = 0
    for s in roads["segments"]:
        dvec = s[1] - s[0]
        L = float(np.linalg.norm(dvec))
        if L < 1e-9:
            continue
        nrm = np.array([-dvec[1], dvec[0]]) / L
        # ★道の帯は step ごとに切る: 描画器(render3d)は頂点が 1 つでもカメラの後ろにある三角形を捨てるので、100 m 級の
        #   1 枚の帯は車載カメラから丸ごと消えた(2026-10-01)
        n_piece = max(1, int(np.ceil(L / step)))
        for k in range(n_piece):
            p0 = s[0] + dvec * (k / n_piece)
            p1 = s[0] + dvec * ((k + 1) / n_piece)
            q = np.array([p0 + nrm * hw, p0 - nrm * hw, p1 - nrm * hw, p1 + nrm * hw])
            Vs.append(np.column_stack([q, np.full(4, 0.02)]))
            Fs.append(np.array([[base, base + 1, base + 2], [base, base + 2, base + 3]]))
            base += 4
            nr += 1
    V = np.concatenate(Vs)
    F = np.concatenate(Fs)
    col = np.concatenate([col, np.tile([[0.22, 0.22, 0.24]], (2 * nr, 1))])
    lab = np.concatenate([lab, np.ones(2 * nr, np.int64)])
    return {"V": V, "F": F, "label": lab, "color": col, "roads": roads, "ij": (int(i), int(j))}


def tile_digest(mesh: dict) -> str:
    """区画のメッシュの指紋(SHA-256、頂点・面・ラベル・色のバイト列)。作り直しのビット一致の門に使う。"""
    h = hashlib.sha256()
    for k in ("V", "F", "label", "color"):
        a = np.ascontiguousarray(mesh[k])
        h.update(str(a.dtype).encode())
        h.update(str(a.shape).encode())
        h.update(a.tobytes())
    return h.hexdigest()


def tile_stream(cache: dict, i: int, j: int, tp: dict, radius: int = 1, step: float = 10.0) -> dict:
    """車のいる区画 (i, j) の周り (2·radius + 1)² 区画を持ち、外れた区画を捨てる(``cache`` をその場で書き換える)。
    返り値 ``{"loaded": [(i, j)], "evicted": [(i, j)], "n": 持っている区画の数}``。"""
    want = {(int(i) + a, int(j) + b) for a in range(-radius, radius + 1) for b in range(-radius, radius + 1)}
    evicted = [k for k in list(cache) if k not in want]
    for k in evicted:
        del cache[k]
    loaded = []
    for k in sorted(want):
        if k not in cache:
            cache[k] = tile_mesh(k[0], k[1], tp, step)
            loaded.append(k)
    return {"loaded": loaded, "evicted": evicted, "n": len(cache)}
