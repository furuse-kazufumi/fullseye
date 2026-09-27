# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""textregion — 文字らしい領域を学習なしで見つける(Stroke Width Transform 系)。

なぜこの族か(2026-09-27): fullseye は OCR の前処理(傾き・二値化・連結成分)までで止まり、
「どこに文字があるか」を出す層が無かった。認識器(学習済みモデル)は載せない方針なので、
文字の**幾何**だけで領域を出す古典 —— ストローク幅が一定である、という性質 —— を op にする。
来歴: Epshtein, Ofek & Wexler, "Detecting Text in Natural Scenes with Stroke Width Transform",
CVPR 2010。

真値(このモジュールの試験が突き合わせるもの、当てはめた数字は無い):
  - 幅 w の矩形ストロークの SWT 中央値 = w(整数、厳密)。
  - 画像を k 倍に拡大すると SWT も k 倍(矩形で厳密)。
  - フォント描画した文字の矩形(1 px 単位で既知)に対する候補の再現率。

すべて numpy + scipy.ndimage のみ。入力は 2-D の灰色画像(float 0..1 か uint8)。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["swt_map", "text_candidates", "text_lines"]

_MAX_SIDE = 8192


def _as_gray(img, op: str) -> np.ndarray:
    a = np.asarray(img)
    if a.ndim == 3 and a.shape[2] in (3, 4):
        a = a[..., :3].astype(np.float64).mean(axis=2)
    if a.ndim != 2:
        raise ValueError("%s: expected a 2-D grey image, got shape %r" % (op, a.shape))
    if a.size == 0 or max(a.shape) > _MAX_SIDE:
        raise ValueError("%s: image size %r out of range" % (op, a.shape))
    a = a.astype(np.float64)
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: image has non-finite values" % op)
    if a.max() > 1.0:
        a = a / 255.0
    return a


def _edges_and_gradient(g: np.ndarray, sigma: float, dark_on_light: bool):
    """エッジ = **文字側(暗い側)の内側の境界画素**、勾配 = 平滑化した画像の Sobel。

    ★規約(真値のため): Canny 風の非最大抑制はエッジを境界のどちら側に落とすかが
    不定で、矩形ストロークの幅が w±1 に化けた(2026-09-27 実測: 3→4、9→8)。ここでは
    境界画素を「文字側で、4 近傍に地の画素を持つ画素」と定め、幅 = 向かい合う境界画素の
    中心間距離 + 1 とする。これで軸に沿う矩形ストロークの幅は整数で厳密に出る。
    文字と地の分離は中間値(min と max の平均)で、暗い文字なら g < 中間値 が文字側。
    """
    s = ndimage.gaussian_filter(g, sigma) if sigma > 0 else g
    gx = ndimage.sobel(s, axis=1)
    gy = ndimage.sobel(s, axis=0)
    thr = 0.5 * (float(g.min()) + float(g.max()))
    ink = (g < thr) if dark_on_light else (g > thr)
    if g.max() <= g.min():
        return np.zeros_like(g, bool), gx, gy, ink
    inner = ndimage.binary_erosion(ink, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]), border_value=0)
    edges = ink & ~inner
    return edges, gx, gy, ink


def swt_map(img, dark_on_light: bool = True, sigma: float = 1.0, max_width: int = 64,
            angle_tol: float = np.pi / 6):
    """Stroke Width Transform —— 各画素に、その画素を含むストロークの幅を書く。

    文字側の境界画素から、勾配の向きに沿って文字の内側へ光線を飛ばし、向かい合う境界
    画素(勾配がほぼ逆向き)に当たったら、光線上の全画素に幅(境界画素の中心間距離 + 1)
    を書く(既に小さい値があれば小さい方)。Epshtein 2010 §3 の手順で、2 回目の走査で
    光線上の中央値より大きい値を中央値に置き換える(角の過大を抑える)。エッジの規約は
    :func:`_edges_and_gradient` に書いた(矩形ストロークで幅が厳密に整数になる)。

    Returns dict: ``swt``(幅の配列、ストローク外は 0)/ ``edges`` / ``n_rays`` /
    ``n_hits``(向かい合うエッジに当たった光線の数)。
    """
    op = "swt_map"
    g = _as_gray(img, op)
    if max_width < 1:
        raise ValueError("%s: max_width must be >= 1" % op)
    edges, gx, gy, ink = _edges_and_gradient(g, sigma, dark_on_light)
    h, w = g.shape
    swt = np.full((h, w), np.inf)
    mag = np.hypot(gx, gy)
    ey, ex = np.nonzero(edges)
    n_rays = int(ey.size)
    n_hits = 0
    rays = []
    sign = -1.0 if dark_on_light else 1.0   # 暗い文字: 勾配は暗→明なので、逆向きに進むと内側へ
    for y0, x0 in zip(ey, ex):
        # ★幅 1 のストローク(2026-09-27 実測: size 16 のフォントは縦の連が 1 px で、行の再現率が
        #   雑音に依らず 0 % だった)。境界画素の 1 歩先が既に地なら、その画素だけの幅 1。
        #   勾配は 1 px の棒では消えて向きが定まらないので、勾配を使わず 4 近傍で決める:
        #   上下がともに地、または左右がともに地なら、その画素の幅は 1。
        up = y0 == 0 or not ink[y0 - 1, x0]
        dn = y0 == h - 1 or not ink[y0 + 1, x0]
        lf = x0 == 0 or not ink[y0, x0 - 1]
        rt = x0 == w - 1 or not ink[y0, x0 + 1]
        if (up and dn) or (lf and rt):
            if 1.0 < swt[y0, x0]:
                swt[y0, x0] = 1.0
            rays.append(([(y0, x0)], 1.0))
            n_hits += 1
            continue
        m = mag[y0, x0]
        if m <= 0:
            continue
        dx, dy = sign * gx[y0, x0] / m, sign * gy[y0, x0] / m
        path = []
        x, y = float(x0), float(y0)
        for _ in range(max_width):
            x += dx
            y += dy
            xi, yi = int(round(x)), int(round(y))
            if xi < 0 or yi < 0 or xi >= w or yi >= h:
                break
            if (xi, yi) == (x0, y0):
                continue
            path.append((yi, xi))
            if edges[yi, xi]:
                m2 = mag[yi, xi]
                if m2 <= 0:
                    break
                dx2, dy2 = sign * gx[yi, xi] / m2, sign * gy[yi, xi] / m2
                # 向かい合う = ほぼ逆向き
                if dx * dx2 + dy * dy2 <= -np.cos(angle_tol):
                    width = float(np.hypot(xi - x0, yi - y0)) + 1.0   # 境界画素の中心間 + 1
                    pts = [(y0, x0)] + path
                    for py, px in pts:
                        if width < swt[py, px]:
                            swt[py, px] = width
                    rays.append((pts, width))
                    n_hits += 1
                break
    # 2 回目: 光線上の中央値で頭打ち
    for pts, width in rays:
        vals = np.array([swt[p] for p in pts])
        med = float(np.median(vals[np.isfinite(vals)])) if np.any(np.isfinite(vals)) else width
        for p in pts:
            if swt[p] > med:
                swt[p] = med
    swt[~np.isfinite(swt)] = 0.0
    return {"swt": swt, "edges": edges, "n_rays": n_rays, "n_hits": n_hits}


def text_candidates(swt, min_area: int = 8, max_var_ratio: float = 0.5,
                    aspect_range=(0.1, 10.0), max_height: int = 300):
    """SWT の連結成分を文字候補に絞る(幅のばらつき・縦横比・大きさ)。

    Epshtein 2010 §4 の規則: 成分内のストローク幅の分散が平均に対して小さい /
    縦横比が極端でない / 大きすぎない。``swt`` は :func:`swt_map` の ``swt``。
    Returns dict: ``boxes``(N×4 の [y0, x0, y1, x1]、半開区間)/ ``labels`` /
    ``stroke_width``(各成分の中央値)/ ``n_components``(絞る前の数)。
    """
    op = "text_candidates"
    s = np.asarray(swt, dtype=np.float64)
    if s.ndim != 2:
        raise ValueError("%s: swt must be 2-D" % op)
    lab, n = ndimage.label(s > 0, structure=np.ones((3, 3)))
    boxes, widths, keep_ids = [], [], []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if sl is None:
            continue
        m = lab[sl] == i
        vals = s[sl][m]
        area = int(m.sum())
        if area < min_area:
            continue
        mean = float(vals.mean())
        if mean <= 0 or float(vals.std()) / mean > max_var_ratio:
            continue
        hgt = sl[0].stop - sl[0].start
        wid = sl[1].stop - sl[1].start
        if hgt > max_height or not (aspect_range[0] <= wid / max(hgt, 1) <= aspect_range[1]):
            continue
        boxes.append((sl[0].start, sl[1].start, sl[0].stop, sl[1].stop))
        widths.append(float(np.median(vals)))
        keep_ids.append(i)
    out_lab = np.zeros_like(lab)
    for k, i in enumerate(keep_ids, start=1):
        out_lab[lab == i] = k
    return {"boxes": np.array(boxes, dtype=int).reshape(-1, 4), "labels": out_lab,
            "stroke_width": np.array(widths), "n_components": int(n)}


def text_lines(boxes, stroke_width=None, overlap_ratio: float = 0.5, gap_ratio: float = 3.0,
               width_ratio: float = 3.0):
    """文字候補の矩形を行にまとめる(縦に重なり、横に近く、ストローク幅が近いものを繋ぐ)。

    ★規則の根拠(2026-09-27 実測): 候補は字画ごとの断片になる(横棒と 'l' では高さが 5 倍
    違う)ので「高さが近い」を条件にすると 3 行が 30〜60 行に割れた。行の同一性は**縦の
    重なり**(小さい方の高さの ``overlap_ratio`` 以上)で判定し、横の隙間は大きい方の高さの
    ``gap_ratio`` 倍以内、ストローク幅は ``width_ratio`` 倍以内。

    Returns dict: ``lines``(M×4 の矩形)/ ``members``(各行の候補 index のリスト)。
    """
    op = "text_lines"
    b = np.asarray(boxes, dtype=int).reshape(-1, 4)
    n = b.shape[0]
    sw = None if stroke_width is None else np.asarray(stroke_width, dtype=float)
    if sw is not None and sw.shape[0] != n:
        raise ValueError("%s: stroke_width has %d entries for %d boxes" % (op, sw.shape[0], n))
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    hs = b[:, 2] - b[:, 0]
    for i in range(n):
        for j in range(i + 1, n):
            hi, hj = hs[i], hs[j]
            if sw is not None and max(sw[i], sw[j]) > width_ratio * max(min(sw[i], sw[j]), 1e-9):
                continue
            # 縦の重なりが小さい方の高さの overlap_ratio 以上、横の隙間が高さの gap_ratio 倍以内
            ov = min(b[i, 2], b[j, 2]) - max(b[i, 0], b[j, 0])
            if ov < overlap_ratio * max(min(hi, hj), 1):
                continue
            gap = max(b[i, 1], b[j, 1]) - min(b[i, 3], b[j, 3])
            if gap > gap_ratio * max(hi, hj):
                continue
            parent[find(i)] = find(j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    lines, members = [], []
    for g in groups.values():
        bb = b[g]
        lines.append((bb[:, 0].min(), bb[:, 1].min(), bb[:, 2].max(), bb[:, 3].max()))
        members.append(sorted(g, key=lambda k: b[k, 1]))
    order = np.argsort([ln[0] * 10_000 + ln[1] for ln in lines]) if lines else []
    return {"lines": np.array([lines[k] for k in order], dtype=int).reshape(-1, 4),
            "members": [members[k] for k in order]}
