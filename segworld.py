# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""真値つきの合成世界(分割の採点用): 重なり合う円、ボロノイ結晶粒、影とハイライトのある工業部品、平均が同じで質感だけ違う
領域、照明の勾配の上の暗い物体、幅 1〜3 px の線とひび。どれも ``image``(float64 [0,1])・``labels``(int、0 = 背景)・
``truth``(閉形式で分かる量)を返し、テストは truth を画像から数え直して一致させる。

## 何を作るか

セグメンテーション拡充 第 1 陣「真値つき合成世界」。学習には使わない(採点の真値)。各世界は **1 つの手法を壊す理由** を
持つ ―― 1. 触れ合う粒は分水嶺の問題、2. 結晶粒は粒界の細線、3. 影は閾値を欺く、4. 質感は閾値では切れない、5. 照明の勾配は
大域閾値を壊す、6. 細い構造は平滑化で消える。

## 真値にする閉形式(門)

* 等しい半径 r の 2 円が中心間 d (< 2r) で重なるレンズの面積 A = 2 r² acos(d / 2r) − (d / 2) √(4r² − d²)。
  鎖状に置く(各円は前の円とだけ重なる)ので三重の重なりは無く、重なりの画素数 = Σ レンズ、和集合 = nπr² − Σ レンズ、
  ラベルは近い中心(垂直二等分線で分ける)なので各円の面積 = πr² − Σ レンズ/2。
* ボロノイ: セル = 矩形を全ての垂直二等分線の半平面で切った多角形(Sutherland–Hodgman)。面積は靴紐、Σ 面積 = H·W、
  粒界の長さ = 内部の辺(両端が矩形の縁でない辺)の長さの和を 2 で割る。画素 p(セル i)から粒界までの距離 =
  min_j (d_j² − d_i²) / (2 |s_j − s_i|)(二等分線までの距離の最小、境界が二等分線の和集合の部分集合なので等号)。
* 部品: 回転した矩形 w × h から円の穴を引いた面積 = w h − Σ π r²。影 = 部品のマスクを光の向きに平行移動した集合から部品を
  除いた画素(閉形式は無いので測った値)。
* 質感: 各領域の平均 = ``mean``(零平均の模様を足す、クリップは対称)、縞の周期 P・向き θ、理論の標準偏差
  (雑音 σ、縞 √(A²/2 + σ²))。
* 照明: I(x, y) = i0 + g_x x/(W−1) + g_y y/(H−1)、画像 = I · R + 雑音(R = 物体 ``reflectance``、背景 1)。物体は円(πr²)と
  整数辺の矩形(w h ちょうど)。
* 細い構造: 中心線(折れ線)からの距離 ≤ w/2 の画素。直線なら面積 = L w + π w²/4(スタジアム)。長さ = Σ 線分。

## 座標

画素の添字 (row, col) = (y, x)。画素の中心 = 整数座標、画素は [x − 0.5, x + 0.5] × [y − 0.5, y + 0.5] を占める。
多角形の領域は [−0.5, W − 0.5] × [−0.5, H − 0.5]。真値の点は (y, x) の順。

## 限界(self_reported)

* 円は等しい半径だけ(楕円・異なる半径は面積の分割が閉形式でない)。重なりは ``overlap`` = 1 − d/2r(中心間の距離で指定)。
  その割合に対応する画素の割合は ``overlap_measured`` で返す(閉形式の面積比 Σ レンズ/和集合 と画素の数え方の差だけずれる)。
* 影は 1 方向の平行移動(平行光、面の高さ一定)。半影はぼかしで作る(物理の形ではない)。
* 乱数は ``seed`` で固定。配置に失敗(詰め込み過ぎ)したら ValueError。
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy import ndimage as ndi

__all__ = [
    "MAX_WORLD_PIXELS", "MAX_OBJECTS",
    "world_blobs_touching", "world_grains_voronoi", "world_parts_with_shadow", "world_texture_regions",
    "world_gradient_illumination", "world_thin_structures", "lens_area", "voronoi_cells",
]

#: 1 つの世界の画素数の上限(距離の配列を (n, H, W) で持つので、n × 画素数を抑える)。
MAX_WORLD_PIXELS = 4_000_000
#: 1 つの世界の物体数の上限。
MAX_OBJECTS = 400


# ───────────────────────────── 入力の検査と共通の道具 ─────────────────────────────
def _size(size, op: str) -> Tuple[int, int]:
    try:
        h, w = int(size[0]), int(size[1])
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s: size must be (H, W) (got %r)" % (op, size)) from None
    if h < 16 or w < 16:
        raise ValueError("%s: size must be at least 16 x 16 (got %r)" % (op, size))
    if h * w > MAX_WORLD_PIXELS:
        raise ValueError("%s: size %r exceeds MAX_WORLD_PIXELS=%d" % (op, size, MAX_WORLD_PIXELS))
    return h, w


def _count(n, name: str, op: str, lo: int = 1, hi: int = MAX_OBJECTS) -> int:
    try:
        k = int(n)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be an integer (got %r)" % (op, name, n)) from None
    if not (lo <= k <= hi):
        raise ValueError("%s: %s must be in [%d, %d] (got %d)" % (op, name, lo, hi, k))
    return k


def _finite(v, name: str, op: str) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number (got %r)" % (op, name, v)) from None
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite (got %r)" % (op, name, v))
    return x


def _unit(v, name: str, op: str, lo: float = 0.0, hi: float = 1.0, closed_hi: bool = True) -> float:
    x = _finite(v, name, op)
    if x < lo or x > hi or (x == hi and not closed_hi):
        raise ValueError("%s: %s must be in [%g, %g%s (got %r)" % (op, name, lo, hi, "]" if closed_hi else ")", v))
    return x


def _rng(seed) -> np.random.Generator:
    try:
        return np.random.default_rng(int(seed))
    except (TypeError, ValueError):
        raise ValueError("seed must be an integer (got %r)" % (seed,)) from None


def _grid(h: int, w: int) -> Tuple[np.ndarray, np.ndarray]:
    yy, xx = np.mgrid[0:h, 0:w]
    return yy.astype(np.float64), xx.astype(np.float64)


def _finish(image: np.ndarray, rng: np.random.Generator, noise: float, sigma: float = 0.0) -> np.ndarray:
    """ぼかし(sigma > 0)→ 雑音 → [0, 1] に切る。"""
    im = ndi.gaussian_filter(image, sigma) if sigma > 0 else image
    if noise > 0:
        im = im + rng.normal(0.0, noise, im.shape)
    return np.clip(im, 0.0, 1.0)


# ───────────────────────────── 1. 触れ合う粒 ─────────────────────────────
def lens_area(r: float, d: float) -> float:
    """等しい半径 r の 2 円(中心間 d)の重なりの面積(閉形式)。d ≥ 2r なら 0。"""
    if d >= 2.0 * r * (1.0 - 1e-12):          # 接するだけ(丸めで 2r をわずかに下回っても 0)
        return 0.0
    return max(2.0 * r * r * math.acos(d / (2.0 * r)) - 0.5 * d * math.sqrt(4.0 * r * r - d * d), 0.0)


def world_blobs_touching(n: int = 10, overlap: float = 0.2, seed: int = 0, *, size=(160, 160), radius: float = 14.0,
                         noise: float = 0.03) -> Dict[str, object]:
    """重なり合う円(細胞・粒)の世界: 鎖状に置いた等しい半径の円、各円は前の円とだけ中心間 2r(1 − overlap) で重なる。

    ラベル = 円の内側で最も近い中心(重なりは垂直二等分線で分ける)。画像 = 明るい内部 + 暗い縁 + 重なりはやや明るい
    + ぼかし + 雑音(細胞の見た目)。鎖がそれ以上伸ばせなければ新しい鎖を始める(その円は誰とも重ならない)。
    返り値: ``image``、``labels``、``count_map``(各画素を覆う円の数)、``truth`` = {``n``、``centers`` (n, 2) [y, x]、``radius``、
    ``overlap``、``pairs`` (m, 2)(重なる組)、``lens_area`` (m,)(閉形式)、``areas`` (n,)(πr² − Σ レンズ/2)、``union_area``、
    ``overlap_measured``(2 つ以上に覆われた画素 / 和集合の画素)}。置けなければ ValueError。"""
    op = "world_blobs_touching"
    n = _count(n, "n", op)
    ov = _unit(overlap, "overlap", op, 0.0, 0.8)
    h, w = _size(size, op)
    r = _finite(radius, "radius", op)
    if r < 3.0:
        raise ValueError("%s: radius must be >= 3 (got %r)" % (op, radius))
    nz = _unit(noise, "noise", op, 0.0, 0.5)
    if n * h * w > MAX_WORLD_PIXELS * 4:
        raise ValueError("%s: n x pixels too large" % op)
    rng = _rng(seed)
    m = r + 2.0
    d_pair = 2.0 * r * (1.0 - ov)
    sep = 2.0 * r + 2.0
    centers: List[np.ndarray] = []
    pairs: List[Tuple[int, int]] = []
    tries = 0
    while len(centers) < n:
        tries += 1
        if tries > 20000:
            raise ValueError("%s: could not place %d blobs of radius %g in %r (too crowded)" % (op, n, r, (h, w)))
        if centers:
            placed = False
            for _ in range(24):
                th = rng.uniform(0.0, 2.0 * math.pi)
                c = centers[-1] + d_pair * np.array([math.sin(th), math.cos(th)])
                if not (m <= c[0] <= h - 1 - m and m <= c[1] <= w - 1 - m):
                    continue
                others = centers[:-1]
                if others and np.min(np.hypot(*(np.array(others) - c).T)) < sep:
                    continue
                pairs.append((len(centers) - 1, len(centers)))
                centers.append(c)
                placed = True
                break
            if placed:
                continue
        c = np.array([rng.uniform(m, h - 1 - m), rng.uniform(m, w - 1 - m)])
        if centers and np.min(np.hypot(*(np.array(centers) - c).T)) < sep:
            continue
        centers.append(c)
    C = np.array(centers)
    yy, xx = _grid(h, w)
    dist = np.sqrt((yy[None] - C[:, 0, None, None]) ** 2 + (xx[None] - C[:, 1, None, None]) ** 2)
    inside = dist <= r
    count_map = inside.sum(axis=0).astype(np.int64)
    dmask = np.where(inside, dist, np.inf)
    labels = np.where(count_map > 0, np.argmin(dmask, axis=0) + 1, 0).astype(np.int64)
    edge = np.where(inside, r - dist, -np.inf).max(axis=0)          # 内側の縁からの深さ(最大)
    img = np.full((h, w), 0.22)
    body = count_map > 0
    img[body] = 0.72
    img[body & (edge < 1.5)] = 0.50
    img[count_map >= 2] += 0.08
    image = _finish(img, rng, nz, sigma=0.6)
    P = np.array(pairs, np.int64).reshape(-1, 2)
    lens = np.array([lens_area(r, float(np.hypot(*(C[a] - C[b])))) for a, b in P])
    areas = np.full(n, math.pi * r * r)
    for (a, b), L in zip(P, lens):
        areas[a] -= 0.5 * L
        areas[b] -= 0.5 * L
    union_px = int(body.sum())
    truth = {"n": n, "centers": C, "radius": r, "overlap": ov, "pairs": P, "lens_area": lens, "areas": areas,
             "union_area": n * math.pi * r * r - float(lens.sum()),
             "overlap_measured": float((count_map >= 2).sum()) / union_px if union_px else 0.0}
    return {"image": image, "labels": labels, "count_map": count_map, "truth": truth}


# ───────────────────────────── 2. ボロノイ結晶粒 ─────────────────────────────
def _clip_halfplane(poly: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """多角形 poly (k, 2) [y, x] を半平面 {p: |p − a| ≤ |p − b|} で切る(Sutherland–Hodgman)。"""
    nrm = b - a
    mid = 0.5 * (a + b)
    out = []
    k = len(poly)
    for i in range(k):
        p, q = poly[i], poly[(i + 1) % k]
        sp, sq = float(np.dot(p - mid, nrm)), float(np.dot(q - mid, nrm))
        if sp <= 0:
            out.append(p)
        if (sp < 0 < sq) or (sq < 0 < sp):
            t = sp / (sp - sq)
            out.append(p + t * (q - p))
    return np.array(out).reshape(-1, 2)


def voronoi_cells(seeds, size) -> Dict[str, object]:
    """矩形 [−0.5, W − 0.5] × [−0.5, H − 0.5] の中の種のボロノイ分割を多角形で返す(半平面の総当たり、O(n²))。

    返り値: ``polygons``(多角形の列、各 (k, 2) [y, x])、``areas``(靴紐)、``edge_length_total``(内部の辺の長さの和)、
    ``n_edges``(内部の辺の数)、``perimeter_internal`` (n,)(各セルの内部の辺の長さ)。"""
    op = "voronoi_cells"
    h, w = _size(size, op)
    S = np.asarray(seeds, np.float64)
    if S.ndim != 2 or S.shape[1] != 2 or S.shape[0] == 0 or not np.isfinite(S).all():
        raise ValueError("%s: seeds must be a finite (n, 2) array of [y, x]" % op)
    n = len(S)
    if n > 1:
        D = np.sqrt(((S[:, None, :] - S[None, :, :]) ** 2).sum(-1))
        if np.min(D[~np.eye(n, dtype=bool)]) < 1e-9:
            raise ValueError("%s: two seeds coincide" % op)
    rect = np.array([[-0.5, -0.5], [-0.5, w - 0.5], [h - 0.5, w - 0.5], [h - 0.5, -0.5]])
    polys, areas, per_int, total, n_edges = [], [], [], 0.0, 0
    for i in range(n):
        poly = rect
        for j in range(n):
            if j != i and len(poly) >= 3:
                poly = _clip_halfplane(poly, S[i], S[j])
        polys.append(poly)
        if len(poly) < 3:
            areas.append(0.0)
            per_int.append(0.0)
            continue
        y, x = poly[:, 0], poly[:, 1]
        areas.append(0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))))
        li = 0.0
        for k in range(len(poly)):
            p, q = poly[k], poly[(k + 1) % len(poly)]
            mid = 0.5 * (p + q)
            di = float(np.hypot(*(mid - S[i])))
            dj = np.hypot(S[:, 0] - mid[0], S[:, 1] - mid[1])
            dj[i] = np.inf
            if abs(float(dj.min()) - di) < 1e-6 * max(1.0, di):
                seg = float(np.hypot(*(q - p)))
                li += seg
                total += seg
                n_edges += 1
        per_int.append(li)
    return {"polygons": polys, "areas": np.array(areas), "edge_length_total": 0.5 * total, "n_edges": n_edges // 2,
            "perimeter_internal": np.array(per_int)}


def world_grains_voronoi(n: int = 36, seed: int = 0, *, size=(192, 192), jitter: float = 0.8, boundary_width: float = 1.5,
                         noise: float = 0.02) -> Dict[str, object]:
    """ボロノイ結晶粒の世界: 格子の升から n 個を選んで ``jitter`` だけ揺らした種、ラベル = 最も近い種の番号(1..n)。

    画像 = 粒ごとの明るさ(0.4〜0.75)× 粒界の暗い線(幅 ``boundary_width``、粒界までの距離の閉形式で描く)+ 雑音。
    背景は無い(全画素がどれかの粒)。
    返り値: ``image``、``labels``、``edge_distance``(各画素から粒界までの距離)、``truth`` = {``n``、``seeds`` (n, 2)、``areas``
    (多角形、靴紐)、``edge_length_total``(内部の辺の長さの和)、``n_edges``、``polygons``、``boundary_width``、``total_area`` = H·W}。"""
    op = "world_grains_voronoi"
    n = _count(n, "n", op, 2)
    h, w = _size(size, op)
    jt = _unit(jitter, "jitter", op, 0.0, 1.0, closed_hi=False)
    bw = _finite(boundary_width, "boundary_width", op)
    if bw <= 0:
        raise ValueError("%s: boundary_width must be > 0 (got %r)" % (op, boundary_width))
    nz = _unit(noise, "noise", op, 0.0, 0.5)
    if n * h * w > MAX_WORLD_PIXELS * 4:
        raise ValueError("%s: n x pixels too large" % op)
    rng = _rng(seed)
    g = int(math.ceil(math.sqrt(n)))
    sy, sx = h / g, w / g
    cells = rng.choice(g * g, n, replace=False)
    gy, gx = cells // g, cells % g
    S = np.stack([(gy + 0.5) * sy - 0.5 + rng.uniform(-0.5, 0.5, n) * jt * sy,
                  (gx + 0.5) * sx - 0.5 + rng.uniform(-0.5, 0.5, n) * jt * sx], axis=1)
    yy, xx = _grid(h, w)
    d2 = (yy[None] - S[:, 0, None, None]) ** 2 + (xx[None] - S[:, 1, None, None]) ** 2
    lab0 = np.argmin(d2, axis=0)
    labels = (lab0 + 1).astype(np.int64)
    Dss = np.sqrt(((S[:, None, :] - S[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(Dss, np.inf)
    d2i = np.take_along_axis(d2, lab0[None], axis=0)[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        cand = (d2 - d2i[None]) / (2.0 * Dss[:, lab0])          # (n, H, W): 二等分線までの距離(自分は inf/0 → inf)
    cand[np.arange(n)[:, None, None] == lab0[None]] = np.inf
    edge_distance = cand.min(axis=0)
    shade = rng.uniform(0.40, 0.75, n)[lab0]
    dark = np.exp(-(edge_distance / (0.6 * bw)) ** 2)
    image = _finish(shade * (1.0 - 0.8 * dark), rng, nz)
    vc = voronoi_cells(S, (h, w))
    truth = {"n": n, "seeds": S, "areas": vc["areas"], "edge_length_total": vc["edge_length_total"], "n_edges": vc["n_edges"],
             "polygons": vc["polygons"], "boundary_width": bw, "total_area": float(h * w)}
    return {"image": image, "labels": labels, "edge_distance": edge_distance, "truth": truth}


# ───────────────────────────── 3. 影のある部品 ─────────────────────────────
def world_parts_with_shadow(seed: int = 0, *, size=(200, 260), n_parts: int = 3, light_angle: float = 35.0,
                            shadow_length: float = 9.0, noise: float = 0.02) -> Dict[str, object]:
    """工業部品(回転した矩形 + 円の穴)と、斜めの照明による影・面の明暗・ハイライトの世界。真値 = 部品(穴は背景、影は背景)。

    光は ``light_angle``(度、画像の x 軸から y 軸へ)の向きに差す平行光。影 = 部品のマスクを光の向きに ``shadow_length``
    だけずらした集合から部品を除いた画素(穴は光を通す)。部品の面は光に向く側が明るく、遠い側は影と同じくらい暗い
    (閾値が欺かれる理由)。ハイライトは光に向く側の縁の近くのガウス。
    返り値: ``image``、``labels``(部品 1..n)、``shadow``(bool)、``truth`` = {``n_parts``、``parts``(center, w, h, angle, holes)、
    ``areas``(w h − Σ π r²)、``shadow_offset`` (dy, dx)、``shadow_area``(測った画素数)、``light_angle``}。"""
    op = "world_parts_with_shadow"
    h, w = _size(size, op)
    n = _count(n_parts, "n_parts", op, 1, 40)
    ang = math.radians(_finite(light_angle, "light_angle", op))
    sl = _finite(shadow_length, "shadow_length", op)
    if sl < 0:
        raise ValueError("%s: shadow_length must be >= 0 (got %r)" % (op, shadow_length))
    nz = _unit(noise, "noise", op, 0.0, 0.5)
    rng = _rng(seed)
    L = np.array([math.sin(ang), math.cos(ang)])                   # (y, x) 光の進む向き
    off = np.round(sl * L).astype(np.int64)
    parts: List[dict] = []
    tries = 0
    while len(parts) < n:
        tries += 1
        if tries > 5000:
            raise ValueError("%s: could not place %d parts in %r" % (op, n, (h, w)))
        pw, ph = rng.uniform(40.0, 70.0), rng.uniform(26.0, 46.0)
        R = 0.5 * math.hypot(pw, ph)
        c = np.array([rng.uniform(R + sl + 3, h - 1 - R - sl - 3), rng.uniform(R + sl + 3, w - 1 - R - sl - 3)])
        if any(np.hypot(*(c - q["center"])) < R + q["R"] + sl + 6 for q in parts):
            continue
        th = rng.uniform(0.0, math.pi)
        holes = []
        for _ in range(int(rng.integers(1, 3))):
            for _k in range(40):
                hr = rng.uniform(4.0, 7.0)
                u = rng.uniform(-(pw / 2 - hr - 4), pw / 2 - hr - 4)
                v = rng.uniform(-(ph / 2 - hr - 4), ph / 2 - hr - 4)
                if all(math.hypot(u - hu, v - hv) >= hr + r2 + 3 for hu, hv, r2 in holes):
                    holes.append((u, v, hr))
                    break
        parts.append({"center": c, "w": pw, "h": ph, "angle": th, "holes": holes, "R": R})
    yy, xx = _grid(h, w)
    labels = np.zeros((h, w), np.int64)
    img = 0.55 + 0.04 * (xx / (w - 1) - 0.5)
    areas = []
    for k, p in enumerate(parts):
        dy, dx = yy - p["center"][0], xx - p["center"][1]
        u = dx * math.cos(p["angle"]) + dy * math.sin(p["angle"])
        v = -dx * math.sin(p["angle"]) + dy * math.cos(p["angle"])
        mask = (np.abs(u) <= p["w"] / 2) & (np.abs(v) <= p["h"] / 2)
        for hu, hv, hr in p["holes"]:
            mask &= (u - hu) ** 2 + (v - hv) ** 2 > hr * hr
        labels[mask] = k + 1
        s = -(dy * L[0] + dx * L[1]) / p["R"]                     # 光に向く側 +1
        face = 0.55 + 0.25 * np.clip(s, -1.0, 1.0)
        hl = p["center"] - 0.45 * p["R"] * L
        face = face + 0.3 * np.exp(-((yy - hl[0]) ** 2 + (xx - hl[1]) ** 2) / (2.0 * 5.0 ** 2))
        img[mask] = face[mask]
        areas.append(p["w"] * p["h"] - sum(math.pi * hr * hr for _u, _v, hr in p["holes"]))
    body = labels > 0
    shifted = np.zeros_like(body)
    ys, xs = slice(max(off[0], 0), h + min(off[0], 0)), slice(max(off[1], 0), w + min(off[1], 0))
    yd, xd = slice(max(-off[0], 0), h + min(-off[0], 0)), slice(max(-off[1], 0), w + min(-off[1], 0))
    shifted[ys, xs] = body[yd, xd]
    shadow = shifted & ~body
    img[shadow] = 0.27
    image = _finish(img, rng, nz, sigma=0.7)
    truth = {"n_parts": n, "parts": [{"center": p["center"], "w": p["w"], "h": p["h"], "angle": p["angle"], "holes": p["holes"]}
                                     for p in parts],
             "areas": np.array(areas), "shadow_offset": (int(off[0]), int(off[1])), "shadow_area": int(shadow.sum()),
             "light_angle": math.degrees(ang)}
    return {"image": image, "labels": labels, "shadow": shadow, "truth": truth}


# ───────────────────────────── 4. 質感だけ違う領域 ─────────────────────────────
def world_texture_regions(seed: int = 0, *, size=(192, 192), n_regions: int = 3, mean: float = 0.5,
                          noise: float = 0.03) -> Dict[str, object]:
    """平均が同じで分散・周期だけ違う 2〜4 領域の世界(閾値では切れない)。真値 = 領域ラベル(1..n、背景なし)。

    領域 = 離した種の最近傍(ボロノイ)。模様は順に: 小さい雑音(σ = noise)、大きい雑音(σ = 4 noise)、縞(周期 P₁・向き θ₁、
    振幅 0.2)+ 雑音、縞(周期 P₂・向き θ₂)+ 雑音。どれも零平均で ``mean`` に足す(クリップは ±0.45 で対称 = 平均を保つ)。
    返り値: ``image``、``labels``、``truth`` = {``n_regions``、``mean``、``seeds``、``specs``(kind, std(理論)、period、angle(度)、amp)}。"""
    op = "world_texture_regions"
    h, w = _size(size, op)
    n = _count(n_regions, "n_regions", op, 2, 4)
    mu = _unit(mean, "mean", op, 0.45, 0.55)
    nz = _unit(noise, "noise", op, 0.0, 0.1, closed_hi=True)
    if nz <= 0:
        raise ValueError("%s: noise must be > 0 (the first two textures are noise)" % op)
    rng = _rng(seed)
    yy, xx = _grid(h, w)
    S = np.empty((0, 2))
    tries = 0
    while len(S) < n:
        tries += 1
        if tries > 2000:
            raise ValueError("%s: could not place %d seeds" % (op, n))
        c = np.array([[rng.uniform(0.2 * h, 0.8 * h), rng.uniform(0.2 * w, 0.8 * w)]])
        if len(S) == 0 or np.min(np.hypot(*(S - c).T)) >= 0.35 * min(h, w):
            S = np.vstack([S, c])
    d2 = (yy[None] - S[:, 0, None, None]) ** 2 + (xx[None] - S[:, 1, None, None]) ** 2
    lab0 = np.argmin(d2, axis=0)
    labels = (lab0 + 1).astype(np.int64)
    periods = rng.choice([6, 8, 10, 12, 14, 16], 2, replace=False).astype(float)
    angles = rng.uniform(10.0, 170.0, 2)
    amp = 0.2
    specs = [{"kind": "noise", "std": nz, "period": 0.0, "angle": 0.0, "amp": 0.0},
             {"kind": "noise", "std": 4.0 * nz, "period": 0.0, "angle": 0.0, "amp": 0.0},
             {"kind": "stripes", "std": math.sqrt(amp * amp / 2 + nz * nz), "period": float(periods[0]), "angle": float(angles[0]), "amp": amp},
             {"kind": "stripes", "std": math.sqrt(amp * amp / 2 + nz * nz), "period": float(periods[1]), "angle": float(angles[1]), "amp": amp}][:n]
    pat = np.zeros((h, w))
    for k, sp in enumerate(specs):
        m = lab0 == k
        if sp["kind"] == "noise":
            pat[m] = rng.normal(0.0, sp["std"], int(m.sum()))
        else:
            th = math.radians(sp["angle"])
            s = xx * math.cos(th) + yy * math.sin(th)
            pat[m] = (sp["amp"] * np.sin(2.0 * math.pi * s / sp["period"]))[m] + rng.normal(0.0, nz, int(m.sum()))
    image = np.clip(mu + np.clip(pat, -0.45, 0.45), 0.0, 1.0)
    truth = {"n_regions": n, "mean": mu, "seeds": S, "specs": specs}
    return {"image": image, "labels": labels, "truth": truth}


# ───────────────────────────── 5. 照明の勾配 ─────────────────────────────
def world_gradient_illumination(seed: int = 0, *, size=(160, 220), n_objects: int = 8, gradient=(0.45, 0.2), i0: float = 0.3,
                                reflectance: float = 0.35, noise: float = 0.03) -> Dict[str, object]:
    """照明の勾配 + 雑音の上の暗い物体の世界(大域閾値が壊れ、局所閾値・フラットフィールドで切れる)。

    I(x, y) = i0 + g_x x/(W−1) + g_y y/(H−1)(i0 + g_x + g_y ≤ 1)、画像 = I · R + 雑音。R = 背景 1、物体 ``reflectance``。
    物体は円(半径 8〜14)と整数辺の矩形(14〜28)、互いに離す。
    返り値: ``image``、``labels``(1..n)、``illumination``、``reflectance_map``、``truth`` = {``n_objects``、``objects``(kind, params)、
    ``areas``(πr² / w h)、``i0``、``gradient``、``reflectance``、``noise``}。"""
    op = "world_gradient_illumination"
    h, w = _size(size, op)
    n = _count(n_objects, "n_objects", op, 1, 60)
    try:
        gx, gy = _finite(gradient[0], "gradient[0]", op), _finite(gradient[1], "gradient[1]", op)
    except (TypeError, IndexError):
        raise ValueError("%s: gradient must be (g_x, g_y)" % op) from None
    i_0 = _finite(i0, "i0", op)
    if gx < 0 or gy < 0 or i_0 <= 0 or i_0 + gx + gy > 1.0:
        raise ValueError("%s: need i0 > 0, gradient >= 0 and i0 + g_x + g_y <= 1 (got %r, %r)" % (op, i0, gradient))
    rf = _unit(reflectance, "reflectance", op, 0.0, 1.0, closed_hi=False)
    nz = _unit(noise, "noise", op, 0.0, 0.5)
    rng = _rng(seed)
    yy, xx = _grid(h, w)
    illum = i_0 + gx * xx / (w - 1) + gy * yy / (h - 1)
    labels = np.zeros((h, w), np.int64)
    objects, areas = [], []
    tries = 0
    while len(objects) < n:
        tries += 1
        if tries > 5000:
            raise ValueError("%s: could not place %d objects in %r" % (op, n, (h, w)))
        if rng.random() < 0.5:
            r = rng.uniform(8.0, 14.0)
            c = np.array([rng.uniform(r + 3, h - 1 - r - 3), rng.uniform(r + 3, w - 1 - r - 3)])
            R = r
            o = {"kind": "disc", "center": c, "radius": r}
        else:
            bw, bh = int(rng.integers(14, 29)), int(rng.integers(14, 29))
            y0, x0 = int(rng.integers(3, h - bh - 3)), int(rng.integers(3, w - bw - 3))
            c = np.array([y0 + (bh - 1) / 2.0, x0 + (bw - 1) / 2.0])
            R = 0.5 * math.hypot(bw, bh)
            o = {"kind": "rect", "y0": y0, "x0": x0, "h": bh, "w": bw, "center": c}
        if any(np.hypot(*(c - q["center"])) < R + q["R"] + 4 for q in objects):
            continue
        o["R"] = R
        objects.append(o)
        k = len(objects)
        if o["kind"] == "disc":
            labels[(yy - c[0]) ** 2 + (xx - c[1]) ** 2 <= r * r] = k
            areas.append(math.pi * r * r)
        else:
            labels[o["y0"]:o["y0"] + o["h"], o["x0"]:o["x0"] + o["w"]] = k
            areas.append(float(o["w"] * o["h"]))
    refl = np.where(labels > 0, rf, 1.0)
    image = _finish(illum * refl, rng, nz)
    truth = {"n_objects": n, "objects": [{kk: v for kk, v in o.items() if kk != "R"} for o in objects],
             "areas": np.array(areas), "i0": i_0, "gradient": (gx, gy), "reflectance": rf, "noise": nz}
    return {"image": image, "labels": labels, "illumination": illum, "reflectance_map": refl, "truth": truth}


# ───────────────────────────── 6. 細い構造 ─────────────────────────────
def _polyline_distance(yy: np.ndarray, xx: np.ndarray, P: np.ndarray) -> np.ndarray:
    """各画素の中心から折れ線 P (m, 2) [y, x] までの距離(線分ごとの点–線分距離の最小)。"""
    best = np.full(yy.shape, np.inf)
    for a, b in zip(P[:-1], P[1:]):
        v = b - a
        L2 = float(v @ v)
        t = ((yy - a[0]) * v[0] + (xx - a[1]) * v[1]) / L2 if L2 > 0 else np.zeros_like(yy)
        t = np.clip(t, 0.0, 1.0)
        best = np.minimum(best, np.hypot(yy - (a[0] + t * v[0]), xx - (a[1] + t * v[1])))
    return best


def _polyline_samples(P: np.ndarray, step: float = 1.0) -> np.ndarray:
    out = []
    for a, b in zip(P[:-1], P[1:]):
        L = float(np.hypot(*(b - a)))
        k = max(int(L / step), 1)
        out.append(a + (b - a) * np.linspace(0.0, 1.0, k + 1)[:, None])
    return np.vstack(out)


def world_thin_structures(seed: int = 0, *, size=(200, 200), n: int = 6, widths: Sequence[float] = (1.0, 2.0, 3.0),
                          noise: float = 0.03) -> Dict[str, object]:
    """幅 1〜3 px の線(直線)とひび(折れ線)の世界。真値 = 中心線と幅。ラベル = 構造の番号(1..n、互いに離す)。

    構造 k は直線(2 点)と折れ線(7 点のランダムウォーク)を交互に、幅は ``widths`` を順に使う。画素は中心線からの距離
    ≤ w/2 なら構造。画像 = 明るい背景(0.82 + 緩い勾配)に、幅が細いほど薄い暗線(w = 1: 0.5、2: 0.38、3: 0.26)、
    縁は距離で反エイリアス、わずかにぼかし + 雑音。
    返り値: ``image``、``labels``、``distance``(各画素から最も近い中心線までの距離)、``truth`` = {``n``、``kinds``、``widths``、
    ``lengths``(Σ 線分)、``length_total``、``polylines``((m, 2) [y, x] の列)、``areas_stadium``(L w + π w²/4)}。"""
    op = "world_thin_structures"
    h, w = _size(size, op)
    n = _count(n, "n", op, 1, 60)
    ws = [_finite(v, "widths", op) for v in widths]
    if not ws or min(ws) < 0.5 or max(ws) > 8.0:
        raise ValueError("%s: widths must be non-empty with values in [0.5, 8] (got %r)" % (op, widths))
    nz = _unit(noise, "noise", op, 0.0, 0.5)
    rng = _rng(seed)
    yy, xx = _grid(h, w)
    m = 6.0
    polys: List[np.ndarray] = []
    kinds: List[str] = []
    samples = np.empty((0, 2))
    tries = 0
    while len(polys) < n:
        tries += 1
        if tries > 4000:
            raise ValueError("%s: could not place %d structures in %r" % (op, n, (h, w)))
        kind = "line" if len(polys) % 2 == 0 else "crack"
        if kind == "line":
            a = np.array([rng.uniform(m, h - 1 - m), rng.uniform(m, w - 1 - m)])
            th = rng.uniform(0.0, math.pi)
            L = rng.uniform(0.3, 0.6) * min(h, w)
            P = np.array([a, a + L * np.array([math.sin(th), math.cos(th)])])
        else:
            pts = [np.array([rng.uniform(m, h - 1 - m), rng.uniform(m, w - 1 - m)])]
            th = rng.uniform(0.0, 2.0 * math.pi)
            for _ in range(6):
                th += rng.normal(0.0, 0.5)
                pts.append(pts[-1] + rng.uniform(14.0, 22.0) * np.array([math.sin(th), math.cos(th)]))
            P = np.array(pts)
        if P[:, 0].min() < m or P[:, 0].max() > h - 1 - m or P[:, 1].min() < m or P[:, 1].max() > w - 1 - m:
            continue
        sm = _polyline_samples(P)
        if len(samples) and np.min(np.sqrt(((sm[:, None, :] - samples[None, :, :]) ** 2).sum(-1))) < 9.0:
            continue
        polys.append(P)
        kinds.append(kind)
        samples = np.vstack([samples, sm])
    labels = np.zeros((h, w), np.int64)
    distance = np.full((h, w), np.inf)
    img = 0.82 + 0.05 * (yy / (h - 1) - 0.5)
    wid, lens = [], []
    for k, P in enumerate(polys):
        wk = ws[k % len(ws)]
        d = _polyline_distance(yy, xx, P)
        labels[d <= wk / 2] = k + 1
        distance = np.minimum(distance, d)
        depth = 0.2 + 0.12 * wk
        img = img - depth * np.clip(wk / 2 + 0.5 - d, 0.0, 1.0)
        wid.append(wk)
        lens.append(float(np.sum(np.hypot(*(np.diff(P, axis=0)).T))))
    image = _finish(img, rng, nz, sigma=0.4)
    W = np.array(wid)
    Lg = np.array(lens)
    truth = {"n": n, "kinds": kinds, "widths": W, "lengths": Lg, "length_total": float(Lg.sum()), "polylines": polys,
             "areas_stadium": Lg * W + math.pi * W * W / 4.0}
    return {"image": image, "labels": labels, "distance": distance, "truth": truth}
