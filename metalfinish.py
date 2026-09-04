# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""metalfinish — 加工された金属表面(仕上げの筋・粗さ・材質)を作る。

動機(2026-09-04、ユーザー「いろいろ加工されたいろんな素材の金属表面とかを再現できると
良いね」): 金属の見え方は **材質(何でできているか)× 仕上げ(どう加工したか)** で決まる。
材質は複素屈折率 n+ik(`glassmirror`)、仕上げは**微小面の向きと粗さの場**で決まる。
ここは後者を作る層で、出力はそのまま `matappear.ward_anisotropic` に渡せる。

仕上げの分類(実際の機械加工に対応):
  * `linear`     ヘアライン / 研磨目 — 一方向の筋。ベルトサンダ・不織布研磨。
  * `circular`   旋盤の削り目 / スピン仕上げ — 中心まわりの同心円。
  * `radial`     放射状のブラシ目 — 中心から外へ。
  * `crosshatch` ローレット / ホーニング — 2 方向の交差目。
  * `random`     ビーズブラスト / 梨地 — 無方向(等方粗さ)。

内容(5 op + 1 ヘルパ):
  * `tangent_field`    — 仕上げ種別 → 微小面の筋方向の場 (H,W,3)
  * `roughness_field`  — 同 → 異方性粗さ (αx, αy) の場 (H,W,2)。**台帳には登録しない**:
    返りが (H,W,2) で既存の sort(image2d / normalmap / pairs …)のどれとも形が違い、
    この 1 op のために新語彙を作る価値が無いため。`finish_shade` の内部で使う。
  * `micro_normals`    — 加工痕そのものを法線へ刻む(旋盤の送りマーク・ローレットの山)
  * `blast_normals`    — ビーズブラスト/梨地の無方向な微小凹凸を法線へ
  * `finish_shade`     — 法線 + 仕上げ + 材質 → 線形 sRGB(拡散なしの反射成分)
  * `finish_catalog`   — 仕上げ × 材質の一覧(名前 → 既定パラメータ)

規約: 法線マップは (H,W,3)(長さ 0 = 背景)。方向はすべてカメラ系で、視線は +Z。
粗さ α は Ward の楕円ガウス微小面の広がり(小さいほど鏡面に近い)。
"""
from __future__ import annotations

import numpy as np

import glassmirror
import matappear

FINISHES = ("linear", "circular", "radial", "crosshatch", "random")

#: 仕上げの既定パラメータ(αx = 筋方向、αy = 直交方向、grain = 微小凹凸の強さ)。
#: 値は「鏡面研磨 → ヘアライン → 梨地」の順に粗くなるよう並べた設計値で、
#: 実測値ではない(実面の粗さは Ra で規定される — ここは見え方のための代理値)。
_FINISH_DEFAULTS = {
    "linear":    {"alpha_x": 0.32, "alpha_y": 0.022, "grain": 0.010},
    "circular":  {"alpha_x": 0.30, "alpha_y": 0.020, "grain": 0.012},
    "radial":    {"alpha_x": 0.30, "alpha_y": 0.020, "grain": 0.012},
    "crosshatch": {"alpha_x": 0.18, "alpha_y": 0.045, "grain": 0.020},
    "random":    {"alpha_x": 0.16, "alpha_y": 0.16, "grain": 0.030},
}


def _shape2(shape, op: str):
    s = tuple(int(v) for v in shape)
    if len(s) != 2 or min(s) < 1:
        raise ValueError(f"{op}: shape must be (H, W) with positive sides: got {shape!r}")
    return s


def _finish(kind: str, op: str) -> str:
    k = str(kind).lower()
    if k not in _FINISH_DEFAULTS:
        raise ValueError(f"{op}: unknown finish {kind!r}; known: {FINISHES}")
    return k


def _center(center, shape, op: str):
    if center is None:
        return (shape[0] - 1) / 2.0, (shape[1] - 1) / 2.0
    c = np.asarray(center, dtype=np.float64).reshape(-1)
    if c.size != 2 or not np.all(np.isfinite(c)):
        raise ValueError(f"{op}: center must be a finite (row, col) pair")
    return float(c[0]), float(c[1])


def finish_catalog() -> dict:
    """仕上げ名 → 既定パラメータの表(αx, αy, grain)。

    値は設計値であって実測の Ra ではない ―― そこは正直に。粗さの**順序**
    (鏡面研磨 < ヘアライン < 交差目 < 梨地)が意味を持つ量。
    """
    return {k: dict(v) for k, v in _FINISH_DEFAULTS.items()}


def tangent_field(shape, kind="linear", angle_deg=0.0, center=None) -> np.ndarray:
    """仕上げの**筋の向き**を (H, W, 3) の接線場として作る。

    shape: (H, W)。kind: `FINISHES` のいずれか。
    angle_deg: linear / crosshatch の筋の向き [deg] (画像座標、+x から反時計回り)。
    center: circular / radial の中心 (row, col)。既定は画像中心。

    返り値: (H, W, 3) の単位接線場(z 成分 0 = 面内)。`random` は画素ごとに
    向きを散らす(無方向 = ビーズブラスト)。

    ★ 定ベクトルではなく**場**なのが要点: 旋盤の削り目は同心円なので、
    一定方向の接線ではハイライトが物理的に成立しない。
    """
    op = "tangent_field"
    h, w = _shape2(shape, op)
    k = _finish(kind, op)
    if k in ("linear", "crosshatch"):
        a = np.radians(float(angle_deg))
        t = np.zeros((h, w, 3))
        t[..., 0] = np.cos(a)
        t[..., 1] = np.sin(a)
        return t
    if k in ("circular", "radial"):
        cy, cx = _center(center, (h, w), op)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
        dy, dx = yy - cy, xx - cx
        r = np.maximum(np.hypot(dy, dx), 1e-9)
        if k == "radial":
            t = np.stack([dx / r, dy / r, np.zeros_like(r)], -1)
        else:                                    # 同心円 = 半径に直交
            t = np.stack([-dy / r, dx / r, np.zeros_like(r)], -1)
        return t
    rng = np.random.default_rng(0)               # random: 画素ごとに無方向
    a = rng.uniform(0.0, np.pi, (h, w))
    return np.stack([np.cos(a), np.sin(a), np.zeros_like(a)], -1)


def roughness_field(shape, kind="linear", scale=1.0, patchiness=0.0, seed=0) -> np.ndarray:
    """仕上げの**異方性粗さ** (αx, αy) を (H, W, 2) の場として作る。

    shape / kind: 上記と同じ。scale: 既定粗さへの倍率(>0)。
    patchiness: 粗さのむら(0–1)。研磨むら・工具摩耗の再現。0 で一様。
    seed: むらの乱数種。

    返り値: (H, W, 2) の正の粗さ場。`random` は αx == αy(等方 = 無方向仕上げ)。
    """
    op = "roughness_field"
    h, w = _shape2(shape, op)
    k = _finish(kind, op)
    sc = float(scale)
    if not np.isfinite(sc) or sc <= 0.0:
        raise ValueError(f"{op}: scale must be positive: got {scale!r}")
    pt = float(patchiness)
    if not np.isfinite(pt) or not (0.0 <= pt <= 1.0):
        raise ValueError(f"{op}: patchiness must lie in [0, 1]: got {patchiness!r}")
    d = _FINISH_DEFAULTS[k]
    base = np.array([d["alpha_x"], d["alpha_y"]], dtype=np.float64) * sc
    out = np.broadcast_to(base, (h, w, 2)).copy()
    if pt > 0.0:
        rng = np.random.default_rng(int(seed))
        # 低周波のむら(粗い格子を作って線形に引き伸ばす = 依存を増やさない fBm 代用)
        g = rng.normal(0.0, 1.0, (max(h // 16, 2), max(w // 16, 2)))
        yi = np.linspace(0, g.shape[0] - 1, h)
        xi = np.linspace(0, g.shape[1] - 1, w)
        rows = np.stack([np.interp(xi, np.arange(g.shape[1]), g[int(round(y))]) for y in yi])
        out *= (1.0 + pt * np.clip(rows, -2.0, 2.0))[..., None]
    return np.maximum(out, 1e-4)


def micro_normals(normals, kind="linear", pitch_px=9.0, depth=0.06,
                  angle_deg=0.0, center=None) -> np.ndarray:
    """加工痕そのものを**法線に刻む**(旋盤の送りマーク・ローレットの山)。

    normals: (H, W, 3) の法線マップ。kind / angle_deg / center: `tangent_field` と同じ。
    pitch_px: 痕の間隔 [px]。depth: 傾ける強さ(0 で無加工)。

    返り値: 摂動後の単位法線マップ。背景(長さ 0)はそのまま 0。

    `random` は方向を持たないので何もしない(そちらは `blast_normals`)。
    痕は**筋に直交する向き**へ傾ける ―― 筋に沿って傾けても筋にならない。
    """
    op = "micro_normals"
    N, mask = matappear._normal_map(normals, op)
    k = _finish(kind, op)
    p = float(pitch_px)
    if not np.isfinite(p) or p <= 0.0:
        raise ValueError(f"{op}: pitch_px must be positive: got {pitch_px!r}")
    dep = float(depth)
    if not np.isfinite(dep) or dep < 0.0:
        raise ValueError(f"{op}: depth must be >= 0: got {depth!r}")
    if k == "random" or dep == 0.0:
        return N * mask[..., None]

    h, w = N.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    T = tangent_field((h, w), k, angle_deg=angle_deg, center=center)
    # 筋に直交する面内軸に沿って、のこぎり状の位相を作る
    perp = np.stack([-T[..., 1], T[..., 0], np.zeros_like(T[..., 0])], -1)
    phase = (xx * perp[..., 0] + yy * perp[..., 1]) * (2.0 * np.pi / p)
    tilt = dep * np.cos(phase)
    out = N + tilt[..., None] * perp
    if k == "crosshatch":                        # 交差目 = もう 1 方向を重ねる
        phase2 = (xx * T[..., 0] + yy * T[..., 1]) * (2.0 * np.pi / p)
        out = out + (dep * np.cos(phase2))[..., None] * T
    out = out / np.maximum(np.linalg.norm(out, axis=-1, keepdims=True), 1e-12)
    return out * mask[..., None]


def blast_normals(normals, grain=0.03, cell_px=3.0, seed=0) -> np.ndarray:
    """ビーズブラスト / 梨地の**無方向な微小凹凸**を法線へ載せる。

    grain: 傾きの強さ(0–1 程度)。cell_px: 粒の大きさ [px] (大きいほど粗い梨地)。

    返り値: 摂動後の単位法線マップ。方向統計を持たないので、ハイライトは
    伸びずに**広がる** ―― これがヘアラインとの見分けどころ。
    """
    op = "blast_normals"
    N, mask = matappear._normal_map(normals, op)
    g = float(grain)
    if not np.isfinite(g) or g < 0.0:
        raise ValueError(f"{op}: grain must be >= 0: got {grain!r}")
    c = float(cell_px)
    if not np.isfinite(c) or c <= 0.0:
        raise ValueError(f"{op}: cell_px must be positive: got {cell_px!r}")
    h, w = N.shape[:2]
    rng = np.random.default_rng(int(seed))
    gh, gw = max(int(h / c), 2), max(int(w / c), 2)
    noise = rng.normal(0.0, 1.0, (gh, gw, 2))
    yi = np.clip((np.arange(h) * gh / h).astype(int), 0, gh - 1)
    xi = np.clip((np.arange(w) * gw / w).astype(int), 0, gw - 1)
    pert = noise[np.ix_(yi, xi)] * g
    out = N + np.stack([pert[..., 0], pert[..., 1], np.zeros((h, w))], -1)
    out = out / np.maximum(np.linalg.norm(out, axis=-1, keepdims=True), 1e-12)
    return out * mask[..., None]


def finish_shade(normals, kind="linear", metal="al", light=(0.3, 0.4, 0.87),
                 view=(0.0, 0.0, 1.0), angle_deg=0.0, center=None,
                 scale=1.0, patchiness=0.0, strength=1.0, seed=0) -> np.ndarray:
    """**材質 × 仕上げ**で金属面を陰影付けする → 線形 sRGB (H, W, 3)。

    材質は複素屈折率から色を作り(`glassmirror.metal_mirror_rgb`)、仕上げは
    接線場と異方性粗さから微小面の分布を作る(`matappear.ward_anisotropic`)。
    さらに角度依存の Fresnel を掛けるので、**縁ほど明るくなる**(金属でも起きる)。

    normals: (H, W, 3)。kind: `FINISHES`。metal: `glassmirror.METALS`。
    strength: 全体の強さ。その他は `tangent_field` / `roughness_field` と同じ。

    返り値: (H, W, 3) 線形 sRGB(拡散項は含まない — 金属に拡散反射は無い)。
    """
    op = "finish_shade"
    N, mask = matappear._normal_map(normals, op)
    k = _finish(kind, op)
    h, w = N.shape[:2]
    T = tangent_field((h, w), k, angle_deg=angle_deg, center=center)
    A = roughness_field((h, w), k, scale=scale, patchiness=patchiness, seed=seed)
    # Ward は αx/αy がスカラなので、粗さ場は代表値 + むらの倍率として掛ける
    ax, ay = float(np.median(A[..., 0])), float(np.median(A[..., 1]))
    lobe = matappear.ward_anisotropic(N * mask[..., None], light=light, view=view,
                                      tangent=T, alpha_x=ax, alpha_y=ay)
    if patchiness > 0.0:
        lobe = lobe * (A[..., 0] / max(ax, 1e-12))
    V = np.asarray(view, dtype=np.float64)
    V = V / max(float(np.linalg.norm(V)), 1e-12)
    cos_v = np.abs(np.sum(N * V[None, None, :], axis=-1))
    rgb = glassmirror.metal_mirror_rgb(metal, cos_v)          # (H, W, 3)
    out = rgb * (float(strength) * lobe)[..., None]
    return np.clip(out, 0.0, None) * mask[..., None]
