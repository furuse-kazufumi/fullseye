#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""離散 Gauss–Bonnet「どんな形でも、曲がり方を全部足すと同じ数になる」を、つまみを動かしながら 3-D で見る(2026-10-26)。

    py -3.11 tools/build_gaussbonnet_anim3d.py            # docs/anim3d/gauss_bonnet.html を書く(ja / en)
    py -3.11 tools/build_gaussbonnet_anim3d.py --check    # 書かずに、門の値の印字と HTML の生成だけ
    py -3.11 tools/anim3d_i18n.py --build build_gaussbonnet_anim3d --out docs/anim3d/gauss_bonnet.html   # 8 言語版(commit するのはこれ)

真値 = 定理。閉じた三角形メッシュの頂点ごとの角欠損 K_v = 2π − Σ(その頂点の三角形の角)を全部足すと、
Σ K_v = 2π χ、χ = V − E + F(Descartes の定理 = 離散 Gauss–Bonnet)。K は角度(幾何)から、χ は頂点・辺・面の数
(組合せ)から出るので、2 つの経路は独立。op は ``angle_defect``(K と総和)と ``mesh_euler_characteristic``(χ)。
新しい op は無い。

各タブは 1 つの量(掃引面の高さ、管まわりの角)を時間でゆっくり振り、面が通り過ぎた頂点の K を足し上げていく。
頂点の色は K(op の出力。手で塗った色ではない)。処理の帯(ページの panes)は 4 段:

1. 掃引(いまの高さ・足した頂点の数)
2. angle_defect(形ごとの Σ K / 2π の途中の値、棒グラフ)
3. mesh_euler_characteristic(V − E + F = χ)
4. 定理(Σ K / 2π と χ の差)。**真値の線 = 門の値**。

タブ(1 タブ = 1 題材):

* **球 → 立方体**(5 つの形を並べる): 球を立方体へ角ばらせていくと、K は 8 つの角に集まる(立方体は角だけ π/2)。
  それでも Σ K は 4π のまま(χ = 2)。
* **トーラス**(半透明): 外側の正の K と内側の負の K が打ち消して Σ K = 0(χ = 0)。管まわりの角を回しながら足す。
* **穴の数を増やす**: 球・トーラス・穴 2 つ・穴 3 つ。χ = 2 − 2g、Σ K = 4π, 0, −4π, −8π。穴 2 つ・3 つの形は
  ``tools/import_gaussbonnet_meshes.py``(陰関数 → marching cubes → 間引き)が作った ``data/gaussbonnet/genus*.npz``。
* **実物: 小惑星イトカワ**: 実測の形(``data/itokawa_shape/gaskell_q64.npz``、CC0)。でこぼこでも Σ K / 2π = χ = 2。
* **境界のある面(限界の回)**: 半球の皿では 2π − Σθ を足しただけでは 2πχ にならない(境界の頂点に測地曲率の項 π − Σθ が要る)。
  隣の恐竜の骨格の走査(``data/gaussbonnet/triceratops_scan.npz``、CC0)は 1 つの閉曲面ではなく開いた面片の集まりで、
  χ は形でなく面片の数を語る。

学習用の型: 各タブは pocviewer の ``lesson``(① 問い → ② 予想 → ③ 再生 → ④ 式 → ⑤ 限界)、時間つまみの読みは ``axis``、
バッジの表は ``checks``(値は :func:`gates` の門の値、ok は基準との比較で決める。手で書いた数字は入れない)。
限界の回は最初に置かない。**regen_all には入れない**(``pocviewer.write_viewer`` で書く手回しの生成物)。
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fullseye as fs  # noqa: E402
import pocviewer as pv  # noqa: E402

T = pv.viewer_text
L = fs.ledger
OUT_HTML = ROOT / "docs" / "anim3d" / "gauss_bonnet.html"
DATA = ROOT / "data"
LANGS = ("ja", "en")
FPS = 15.0
NF = 49                          # 1 タブのコマ数(掃引を 3.2 秒で)
STAGE_FRAMES = 3                 # 帯の強調が 1 段に留まるコマ数
TWO_PI = 2.0 * math.pi

#: 帯と説明に出す op(登録名。fs.ledger.<name>)
USED_OPS = ("angle_defect", "mesh_euler_characteristic", "mesh_torus", "geodesic_dome")

SWEEP_RGB = (0.85, 0.88, 0.95)
SWEEP_ALPHA = 0.28
SERIES_COLORS = ("#ffd54f", "#80cbc4", "#ce93d8", "#90caf9", "#f48fb1")


# --------------------------------------------------------------------------- #
# op(登録名で呼ぶ)                                                             #
# --------------------------------------------------------------------------- #
def _vf(x):
    """op の戻り(tuple か dict)を (V, F) に。"""
    if isinstance(x, dict):
        return np.asarray(x["vertices"], float), np.asarray(x["faces"], int)
    V, F = x
    return np.asarray(V, float), np.asarray(F, int)


def defect(V, F) -> dict:
    """``angle_defect``(登録 op): 頂点ごとの K、総和、2πχ、境界の頂点。"""
    return L.angle_defect(np.asarray(V, float), np.asarray(F, int))


def euler(V, F) -> dict:
    """``mesh_euler_characteristic``(登録 op): V, E, F, χ, 種数, 閉じているか。"""
    return L.mesh_euler_characteristic(np.asarray(V, float), np.asarray(F, int))


def components(V, F) -> int:
    """面でつながった部品の数(scipy。op ではない帳簿の数)。"""
    import scipy.sparse as sp
    import scipy.sparse.csgraph as cg
    F = np.asarray(F, int)
    I = np.r_[F[:, 0], F[:, 1], F[:, 2]]
    J = np.r_[F[:, 1], F[:, 2], F[:, 0]]
    A = sp.coo_matrix((np.ones(len(I)), (I, J)), shape=(len(V), len(V)))
    _n, lab = cg.connected_components(A, directed=False)
    return int(len(np.unique(lab[np.unique(F)])))


# --------------------------------------------------------------------------- #
# 形                                                                             #
# --------------------------------------------------------------------------- #
def cube_grid(n: int):
    """立方体の表面を n × n の格子で三角形に(辺・角の頂点は共有、閉じた 2-多様体、χ = 2)。外向きの巻き。"""
    idx: dict = {}
    pts: list = []

    def vid(c):
        c = tuple(int(x) for x in c)
        if c not in idx:
            idx[c] = len(pts)
            pts.append(c)
        return idx[c]

    faces = []
    for axis in range(3):
        for side in (0, n):
            for a in range(n):
                for b in range(n):
                    def P(a_, b_):
                        c = [0, 0, 0]
                        c[axis], c[(axis + 1) % 3], c[(axis + 2) % 3] = side, a_, b_
                        return c
                    v00, v10, v01, v11 = vid(P(a, b)), vid(P(a + 1, b)), vid(P(a, b + 1)), vid(P(a + 1, b + 1))
                    if side == n:
                        faces += [[v00, v10, v11], [v00, v11, v01]]
                    else:
                        faces += [[v00, v11, v10], [v00, v01, v11]]
    V = np.asarray(pts, float) / n * 2.0 - 1.0
    return V, np.asarray(faces, int)


def cube_sphere(n: int, q):
    """立方体の格子を q ノルムの単位球面へ写す(q = 2 で球、q が大きいほど角ばり、None で立方体)。"""
    V, F = cube_grid(n)
    if q is None:
        return V, F
    nrm = np.sum(np.abs(V) ** q, axis=1) ** (1.0 / q)
    return V / nrm[:, None], F


def load_npz(name: str):
    d = np.load(DATA / "gaussbonnet" / name)
    return np.asarray(d["vertices"], float), np.asarray(d["faces"], int)


def load_itokawa():
    """イトカワの形(cm の整数 → m)。"""
    d = np.load(DATA / "itokawa_shape" / "gaskell_q64.npz")
    return np.asarray(d["vertices_cm"], float) / 100.0, np.asarray(d["faces"], int)


def load_scan():
    """恐竜の骨格の走査(間引き済み)。glTF の y 上・z 長手を、ここでは z 上・x 長手に置き直す。"""
    d = np.load(DATA / "gaussbonnet" / "triceratops_scan.npz")
    V = np.asarray(d["vertices"], float)[:, [2, 0, 1]]
    meta = {k: int(d[k]) for k in ("source_vertices", "source_faces", "source_boundary_edges", "source_components", "source_chi")}
    return V, np.asarray(d["faces"], int), meta


def box_mesh(size):
    s = np.asarray(size, float) / 2
    v = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float) * s
    f = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
         [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]
    return v, np.array(f)


def arrange_row(shapes, gap: float):
    """形 [(V, F)] を x 軸に沿って並べる。戻り = x のオフセットの列(z, y はそのまま)。"""
    offs, x = [], 0.0
    for k, (V, _F) in enumerate(shapes):
        w = V[:, 0].max() - V[:, 0].min()
        if k > 0:
            x += w / 2
        offs.append(x - (V[:, 0].max() + V[:, 0].min()) / 2)
        x += w / 2 + gap
    c = (offs[0] + shapes[0][0][:, 0].min() + offs[-1] + shapes[-1][0][:, 0].max()) / 2
    return [o - c for o in offs]


def identity_quat(Tn, B):
    q = np.zeros((Tn, B, 4))
    q[..., 0] = 1.0
    return q


def sweep_frames(z_hi, z_lo, Tn):
    """掃引面の高さ: 上の少し外 → 下の少し外を等間隔で(最初と最後のコマで全頂点が入る・入らない)。"""
    pad = 0.02 * (z_hi - z_lo)
    return np.linspace(z_hi + pad, z_lo - pad, Tn)


def running(Kz, z_plane):
    """頂点の (K, z) と、各コマの掃引面の高さ → 面より上の頂点の K の和(コマごと)。"""
    K, z = Kz
    return np.array([K[z >= zp].sum() for zp in z_plane])


# --------------------------------------------------------------------------- #
# 処理の帯(ラスタ。文字は 2 値で描いて PNG を小さく)                            #
# --------------------------------------------------------------------------- #
PW, PH, HEAD, GAP = 146, 82, 20, 10
BG = 0.11
EST_RGB = (1.0, 0.84, 0.31)
STAGE_RGB = [(0.80, 0.80, 0.80), (0.40, 0.80, 0.45), (0.31, 0.76, 0.97), EST_RGB]
STAGE_NAME = ("1 sweep", "2 angle_defect", "3 euler V-E+F", "4 theorem")
_TXT_CACHE: dict = {}


def _txt(img, s, x, y, color, size=9):
    """文字を 2 値で(縁のぼかしなし)。同じ文字列・大きさの型は使い回す。"""
    import annotate
    key = (s, size)
    m = _TXT_CACHE.get(key)
    if m is None:
        w = max(8, int(len(s) * size * 0.75) + 8)
        layer = np.zeros((size * 2 + 4, w, 3))
        out = annotate.text_box(layer, s, (1, size + 2), anchor="lm", font_size=size, min_font_size=size, pad=0,
                                wrap=False, line_spacing=1.0, text_color=(1.0, 1.0, 1.0), box_alpha=0.0)
        m = np.asarray(out)[..., 0] > 0.42
        _TXT_CACHE[key] = m
    h, w = img.shape[:2]
    y0 = int(y) - m.shape[0] // 2
    ys, xs = np.nonzero(m)
    ys, xs = ys + y0, xs + int(x)
    ok = (ys >= 0) & (ys < h) & (xs >= 0) & (xs < w)
    img[ys[ok], xs[ok]] = color


def _px(img, r, c, color):
    h, w = img.shape[:2]
    r, c = np.asarray(r).astype(int), np.asarray(c).astype(int)
    ok = (r >= 0) & (r < h) & (c >= 0) & (c < w)
    img[r[ok], c[ok]] = color


def _seg(img, p0, p1, color):
    n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))) + 1
    t = np.linspace(0, 1, n + 1)
    _px(img, np.rint(p0[0] + t * (p1[0] - p0[0])), np.rint(p0[1] + t * (p1[1] - p0[1])), color)


def mini_plot(img, box_, curves, xlim, ylim, cursor=None, guides=()):
    """小さなグラフ。``curves`` = [(xs, ys, color)]。``guides`` = [(x か None, y か None, color)]。"""
    r0, c0, h, w = box_
    img[r0:r0 + h, c0:c0 + w] = 0.16

    def rc(x, y):
        return (r0 + h - 1 - (y - ylim[0]) / (ylim[1] - ylim[0]) * (h - 1),
                c0 + (x - xlim[0]) / (xlim[1] - xlim[0]) * (w - 1))
    for gx, gy, col in guides:
        if gx is not None:
            a, b = rc(gx, ylim[0]), rc(gx, ylim[1])
            for rr in range(int(b[0]), int(a[0]) + 1, 2):
                _px(img, rr, int(round(a[1])), col)
        if gy is not None:
            a, b = rc(xlim[0], gy), rc(xlim[1], gy)
            for cc in range(int(a[1]), int(b[1]) + 1, 2):
                _px(img, int(round(a[0])), cc, col)
    for xs, ys, col in curves:
        xs, ys = np.asarray(xs, float), np.asarray(ys, float)
        for i in range(len(xs) - 1):
            if np.isfinite(ys[i]) and np.isfinite(ys[i + 1]):
                a = rc(xs[i], np.clip(ys[i], *ylim))
                b = rc(xs[i + 1], np.clip(ys[i + 1], *ylim))
                _seg(img, a, b, col)
    if cursor is not None:
        x, y, col = cursor
        a = rc(x, ylim[0])
        _seg(img, (r0, a[1]), (r0 + h - 1, a[1]), (0.45, 0.45, 0.45))
        if y is not None and np.isfinite(y):
            p = rc(x, np.clip(y, *ylim))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    _px(img, int(p[0]) + dr, int(p[1]) + dc, col)


def bars(img, box_, values, targets, colors, ylim):
    """棒グラフ: 形ごとの Σ K / 2π の途中の値(棒)と χ(白い横線 = 真値)。"""
    r0, c0, h, w = box_
    img[r0:r0 + h, c0:c0 + w] = 0.16
    n = len(values)
    bw = max(3, (w - 4) // n - 3)

    def row(y):
        return int(round(r0 + h - 1 - (y - ylim[0]) / (ylim[1] - ylim[0]) * (h - 1)))
    z = row(0.0)
    for cc in range(c0, c0 + w, 2):
        _px(img, z, cc, (0.4, 0.4, 0.4))
    for i, (v, tg, col) in enumerate(zip(values, targets, colors)):
        cl = c0 + 2 + i * (bw + 3)
        a, b = sorted((z, row(float(np.clip(v, *ylim)))))
        img[a:b + 1, cl:cl + bw] = col
        rt = row(float(np.clip(tg, *ylim)))
        img[max(r0, rt - 1):min(r0 + h, rt + 1), cl - 1:cl + bw + 1] = (1.0, 1.0, 1.0)


def _heads(names=STAGE_NAME):
    key = ("heads",) + tuple(names)
    if key in _TXT_CACHE:
        return _TXT_CACHE[key]
    heads = []
    for s in range(4):
        row_ = []
        for on in (False, True):
            hb = np.full((HEAD, PW, 3), BG)
            _txt(hb, names[s], 4, HEAD // 2, STAGE_RGB[s] if on else (0.55, 0.55, 0.55), 10)
            row_.append(hb)
        heads.append(row_)
    tag = np.full((16, 70, 3), BG)
    _txt(tag, "Fullseye", 14, 8, (0.45, 0.62, 0.80), 9)
    _TXT_CACHE[key] = (heads, tag)
    return heads, tag


def panel_text(lines, plot=None):
    """1 段の中身: 文字の行 [(文字列, 色)] と、任意の小さなグラフ(関数 img → None)。"""
    p = np.full((PH, PW, 3), BG)
    y = 7
    for s, col in lines:
        if s:
            _txt(p, s, 3, y, col, 9)
        y += 11
    if plot is not None:
        plot(p)
    return p


def band_frame(panels, active, names=STAGE_NAME):
    """4 段を横に並べ、``active`` の段を強調。"""
    heads, tag = _heads(tuple(names))
    cols = []
    for s, p in enumerate(panels):
        on = s == active
        fr = np.concatenate([heads[s][1 if on else 0], p], axis=0)
        bc = STAGE_RGB[s] if on else (0.25, 0.25, 0.25)
        fr = np.pad(fr, ((2, 2), (2, 2), (0, 0)), constant_values=0)
        fr[:2], fr[-2:], fr[:, :2], fr[:, -2:] = bc, bc, bc, bc
        cols.append(fr)
        if s < 3:
            arr = np.full((fr.shape[0], GAP, 3), BG)
            mid = HEAD + 2 + PH // 2
            ac = STAGE_RGB[s + 1] if s + 1 == active else (0.45, 0.45, 0.45)
            arr[mid - 1:mid + 2, 1:GAP - 5] = ac
            for t in range(5):
                arr[mid - (5 - t):mid + (5 - t) + 1, GAP - 6 + t] = ac
            cols.append(arr)
    out = np.concatenate(cols, axis=1)
    strip = np.full((tag.shape[0], out.shape[1], 3), BG)
    strip[:, -tag.shape[1] - 2:-2] = tag
    out = np.concatenate([out, strip], axis=0)
    return (np.rint(np.clip(out, 0, 1) * 63) * 4).astype(np.uint8)


def active_stage(k):
    return (k // STAGE_FRAMES) % 4


def _e(x):
    """門の値の印字(0 はそのまま 0、他は指数 1 桁)。"""
    return "0" if x == 0 else "%.1e" % x


def _hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


# --------------------------------------------------------------------------- #
# 共通: 形の列を掃引面で足し上げるタブ                                           #
# --------------------------------------------------------------------------- #
def sweep_tab(shapes, names, gap, alpha=None, plane_pad=0.6):
    """``shapes`` = [(V, F)] を x に並べ、掃引面を上から下へ動かす。戻り = 帯以外の全部(recs に形ごとの門の値)。"""
    offs = arrange_row(shapes, gap)
    recs, bodies, Ks = [], [], []
    world = []
    for (V, F), name, ox in zip(shapes, names, offs):
        d, e = defect(V, F), euler(V, F)
        recs.append({"name": name, "V": e["V"], "E": e["E"], "F": e["F"], "chi": e["chi"], "genus": e["genus"], "closed": e["closed"],
                     "boundary_edges": e["boundary_edges"], "nonmanifold_edges": e["nonmanifold_edges"],
                     "total": d["total"], "two_pi_chi": d["two_pi_chi"], "K": d["defect"], "is_boundary": d["is_boundary"],
                     "n_boundary_vertices": int(d["is_boundary"].sum()), "ox": ox})
        Ks.append(d["defect"])
        world.append(V + np.array([ox, 0.0, 0.0]))
        b = {"name": name, "pos": V, "faces": F, "val": d["defect"]}
        if alpha is not None:
            b["alpha"] = float(alpha)
        bodies.append(b)
    W = np.concatenate(world)
    z_hi, z_lo = W[:, 2].max(), W[:, 2].min()
    zp = sweep_frames(z_hi, z_lo, NF)
    t = np.arange(NF) / FPS
    sums = [running((r["K"], w[:, 2]), zp) for r, w in zip(recs, world)]
    counts = [np.array([(w[:, 2] >= z).sum() for z in zp]) for w in world]
    x0, x1 = W[:, 0].min() - plane_pad, W[:, 0].max() + plane_pad
    y0, y1 = W[:, 1].min() - plane_pad, W[:, 1].max() + plane_pad
    pv_, pf_ = box_mesh((x1 - x0, y1 - y0, 0.012 * (z_hi - z_lo)))
    bodies.append({"name": "sweep", "pos": pv_, "faces": pf_, "rgb": SWEEP_RGB, "alpha": SWEEP_ALPHA})
    B = len(bodies)
    xyz = np.zeros((NF, B, 3))
    for j, ox in enumerate(offs):
        xyz[:, j, 0] = ox
    xyz[:, B - 1, 0], xyz[:, B - 1, 1], xyz[:, B - 1, 2] = (x0 + x1) / 2, (y0 + y1) / 2, zp
    return {"t": t, "bodies": bodies, "xyz": xyz, "quat": identity_quat(NF, B), "recs": recs, "sums": sums, "counts": counts,
            "zp": zp, "z_range": (z_lo, z_hi), "world": world}


def sweep_series(d, labels, chis):
    out = []
    for j, (s, lab, chi) in enumerate(zip(d["sums"], labels, chis)):
        v = s / TWO_PI
        lo, hi = round(min(0.0, v.min(), chi) - 0.3, 1), round(max(0.0, v.max(), chi) + 0.3, 1)
        out.append({"label": lab, "values": v, "lo": lo, "hi": hi, "decimals": 3, "color": SERIES_COLORS[j % len(SERIES_COLORS)],
                    "threshold": float(chi)})
    return out


def sweep_axis(d, label, unit="", decimals=2):
    return {"values": d["zp"], "segments": [{"k": 0, "label": label, "unit": unit, "decimals": decimals}]}


def sweep_band(d, short, extra4=None):
    """掃引のタブの帯。``short`` = 帯に出す形の短い英字名。"""
    recs, zp = d["recs"], d["zp"]
    chis = [r["chi"] for r in recs]
    cols = [_hex_rgb(SERIES_COLORS[j % len(SERIES_COLORS)]) for j in range(len(recs))]
    lo = min(0.0, min(chis)) - 0.5
    hi = max(0.0, max(chis)) + 0.5
    frames = []
    nV = sum(r["V"] for r in recs)
    for k in range(NF):
        swept = int(sum(c[k] for c in d["counts"]))
        p1 = panel_text([("%d shape%s, %d vertices" % (len(recs), "s" if len(recs) > 1 else "", nV), (0.9, 0.9, 0.9)),
                         ("plane z = %.2f" % zp[k], (1.0, 1.0, 1.0)),
                         ("swept %d / %d" % (swept, nV), (0.75, 0.75, 0.75)),
                         ("colour = K_v (angle defect)", (0.6, 0.6, 0.6))])
        vals = [s[k] / TWO_PI for s in d["sums"]]

        def plot(p, vals=vals):
            bars(p, (14, 4, PH - 18, PW - 8), vals, chis, cols, (lo, hi))
        p2 = panel_text([("sum K / 2pi so far", (0.55, 0.9, 0.6))], plot)
        lines3 = []
        for r, nm in zip(recs, short):
            if len(recs) <= 3:                               # 大きな数は 2 行に(1 行は 26 字まで)
                lines3.append(("%s V%d E%d" % (nm, r["V"], r["E"]), (0.85, 0.85, 0.85)))
                lines3.append(("  F%d chi=%d" % (r["F"], r["chi"]), (0.95, 0.95, 0.95)))
            else:
                lines3.append(("%s %d-%d+%d=%d" % (nm, r["V"], r["E"], r["F"], r["chi"]), (0.85, 0.85, 0.85)))
        p3 = panel_text(lines3[:6])
        if k == NF - 1:
            l4 = [("sum K = 2 pi chi", EST_RGB)]
            for r, nm in zip(recs, short):
                l4.append(("%s %.2f/%d d=%s" % (nm, r["total"] / TWO_PI, r["chi"], _e(abs(r["total"] - r["two_pi_chi"]))), (0.6, 1.0, 0.6)))
            if extra4:
                l4 = l4[:6 - len(extra4)] + extra4
        else:
            l4 = [("sum K = 2 pi chi", EST_RGB), ("so far / target:", (0.95, 0.95, 0.95))]
            for r, nm, v in zip(recs, short, vals):
                l4.append(("%s %.2f / %d" % (nm, v, r["chi"]), (0.85, 0.85, 0.85)))
        p4 = panel_text(l4[:6])
        frames.append(band_frame([p1, p2, p3, p4], active_stage(k)))
    return np.stack(frames)


# --------------------------------------------------------------------------- #
# タブ 1: 球 → 立方体                                                           #
# --------------------------------------------------------------------------- #
SHARPEN_Q = (2.0, 3.0, 5.0, 10.0, None)
SHARPEN_N = 14
SHARPEN_SHORT = ("sphere", "q=3", "q=5", "q=10", "cube")


def build_sharpen():
    shapes = [cube_sphere(SHARPEN_N, q) for q in SHARPEN_Q]
    d = sweep_tab(shapes, ["sphere", "q3", "q5", "q10", "cube"], gap=0.9)
    d["kmax"] = [float(r["K"].max()) for r in d["recs"]]
    cube = d["recs"][-1]
    corners = np.abs(cube["K"] - math.pi / 2) < 1e-9
    d["cube_corners"] = int(corners.sum())
    d["cube_rest_max"] = float(np.abs(cube["K"][~corners]).max())
    d["band"] = sweep_band(d, SHARPEN_SHORT)
    d["labels"] = [T("球(q = 2)", "sphere (q = 2)"), T("q = 3", "q = 3"), T("q = 5", "q = 5"), T("q = 10", "q = 10"),
                   T("立方体", "cube")]
    return d


# --------------------------------------------------------------------------- #
# タブ 2: トーラス(管まわりの角で足す)                                           #
# --------------------------------------------------------------------------- #
TORUS_R, TORUS_r, TORUS_NU, TORUS_NV = 2.0, 0.8, 72, 36


def build_torus():
    V, F = _vf(L.mesh_torus(TORUS_R, TORUS_r, TORUS_NU, TORUS_NV))
    d, e = defect(V, F), euler(V, F)
    K = d["defect"]
    ring = np.arange(V.shape[0]) % TORUS_NV                       # 頂点 i·n_v + j の j = 管まわりの番号
    ring_sum = np.array([K[ring == j].sum() for j in range(TORUS_NV)])
    v_deg = np.linspace(0.0, 360.0, NF)
    j_of = np.minimum(TORUS_NV - 1, np.floor(v_deg / 360.0 * TORUS_NV).astype(int))
    j_of[-1] = TORUS_NV - 1
    cum = np.array([ring_sum[:j + 1].sum() for j in j_of])
    t = np.arange(NF) / FPS
    bodies = [{"name": "torus", "pos": V, "faces": F, "val": K, "alpha": 0.62,
               "label": T("トーラス(R = 2, r = 0.8、半透明)", "torus (R = 2, r = 0.8, translucent)")}]
    clouds = []
    for k in range(NF):
        P = V[ring == j_of[k]]
        clouds.append({"k": k, "pos": P, "color": "#ffffff", "point_size": 0.09})
    xyz = np.zeros((NF, 1, 3))
    outer = float(K[np.cos(ring * TWO_PI / TORUS_NV) > 1e-9].sum())
    inner = float(K[np.cos(ring * TWO_PI / TORUS_NV) < -1e-9].sum())
    recs = {"V": e["V"], "E": e["E"], "F": e["F"], "chi": e["chi"], "genus": e["genus"], "closed": e["closed"],
            "total": d["total"], "two_pi_chi": d["two_pi_chi"], "K": K, "outer": outer, "inner": inner, "ring_sum": ring_sum,
            "kmax": float(K.max()), "kmin": float(K.min())}
    frames = []
    for k in range(NF):
        j = j_of[k]
        p1 = panel_text([("torus R=%.1f r=%.1f" % (TORUS_R, TORUS_r), (0.9, 0.9, 0.9)), ("%d x %d vertices" % (TORUS_NU, TORUS_NV), (0.75, 0.75, 0.75)),
                         ("tube angle v = %.0f deg" % v_deg[k], (1.0, 1.0, 1.0)), ("ring %d / %d" % (j + 1, TORUS_NV), (0.75, 0.75, 0.75)),
                         ("outer K > 0, inner K < 0", (0.6, 0.6, 0.6))])
        vv = np.arange(TORUS_NV) * 360.0 / TORUS_NV

        def plot(p, j=j):
            mini_plot(p, (26, 4, PH - 30, PW - 8), [(vv, ring_sum / TWO_PI, (0.55, 0.9, 0.6)), (v_deg, cum / TWO_PI, EST_RGB)],
                      (0, 360), (-0.6, 0.6), cursor=(v_deg[k], cum[k] / TWO_PI, EST_RGB), guides=[(None, 0.0, (0.5, 0.5, 0.5))])
        p2 = panel_text([("ring sum K / 2pi (green)", (0.55, 0.9, 0.6)), ("running sum (yellow)", EST_RGB)], plot)
        p3 = panel_text([("V - E + F", (0.85, 0.85, 0.85)), ("%d - %d + %d" % (e["V"], e["E"], e["F"]), (0.95, 0.95, 0.95)),
                         ("= chi = %d" % e["chi"], (1.0, 1.0, 1.0)), ("genus = %s" % e["genus"], (0.75, 0.75, 0.75))])
        if k == NF - 1:
            l4 = [("sum K = 2 pi chi = 0", EST_RGB), ("outer %.4f" % (outer / TWO_PI), (0.95, 0.95, 0.95)),
                  ("inner %.4f" % (inner / TWO_PI), (0.95, 0.95, 0.95)), ("sum %.3f  d=%s" % (d["total"] / TWO_PI, _e(abs(d["total"]))), (0.6, 1.0, 0.6))]
        else:
            l4 = [("sum K = 2 pi chi = 0", EST_RGB), ("so far %.4f (x 2pi)" % (cum[k] / TWO_PI), (0.95, 0.95, 0.95))]
        p4 = panel_text(l4)
        frames.append(band_frame([p1, p2, p3, p4], active_stage(k)))
    return {"t": t, "bodies": bodies, "xyz": xyz, "quat": identity_quat(NF, 1), "clouds": clouds, "recs": recs, "cum": cum,
            "v_deg": v_deg, "j_of": j_of, "band": np.stack(frames)}


# --------------------------------------------------------------------------- #
# タブ 3: 穴の数                                                                #
# --------------------------------------------------------------------------- #
GENUS_SHORT = ("g=0", "g=1", "g=2", "g=3")


def build_genus():
    sphere = _vf(L.geodesic_dome(6, 1.0))
    torus = _vf(L.mesh_torus(1.0, 0.42, 48, 24))
    shapes = [sphere, torus, load_npz("genus2.npz"), load_npz("genus3.npz")]
    d = sweep_tab(shapes, ["g0", "g1", "g2", "g3"], gap=0.9)
    d["band"] = sweep_band(d, GENUS_SHORT)
    d["labels"] = [T("球(穴 0)", "sphere (0 holes)"), T("トーラス(穴 1)", "torus (1 hole)"), T("穴 2 つ", "2 holes"), T("穴 3 つ", "3 holes")]
    return d


# --------------------------------------------------------------------------- #
# タブ 4: 実物 —— 小惑星イトカワ                                                 #
# --------------------------------------------------------------------------- #
def build_asteroid():
    V, F = load_itokawa()
    d = sweep_tab([(V, F)], ["itokawa"], gap=0.0, plane_pad=20.0)
    r = d["recs"][0]
    d["neg_share"] = float((r["K"] < 0).mean())
    d["kmax"], d["kmin"] = float(r["K"].max()), float(r["K"].min())
    d["length_m"] = float(V[:, 0].max() - V[:, 0].min())
    d["band"] = sweep_band(d, ("itokawa",), extra4=[("%d%% of vertices K < 0" % round(100 * d["neg_share"]), (0.75, 0.75, 0.75))])
    d["labels"] = [T("イトカワ(実測の形、頂点 %d)" % r["V"], "Itokawa (measured shape, %d vertices)" % r["V"])]
    return d


# --------------------------------------------------------------------------- #
# タブ 5: 境界のある面(限界の回)                                                 #
# --------------------------------------------------------------------------- #
BOWL_FREQ, BOWL_R = 8, 1.2
SCAN_SCALE = 0.7


def build_boundary():
    V, F = _vf(L.geodesic_dome(BOWL_FREQ, 1.0, True))
    V = V * BOWL_R
    V[:, 2] = -V[:, 2]                                             # 上向きの皿に(巻きも反転して外向きのまま)
    F = F[:, [0, 2, 1]]
    Vs, Fs, meta = load_scan()
    Vs = (Vs - Vs.mean(axis=0)) * SCAN_SCALE
    d = sweep_tab([(V, F), (Vs, Fs)], ["bowl", "scan"], gap=1.0)
    bowl, scan = d["recs"]
    # 皿: 2π − Σθ だけの和(境界の頂点に π − Σθ を使わない)。op の K は境界で π − Σθ なので、境界の頂点ぶん π を戻す。
    wb = d["world"][0]
    naive_K = bowl["K"] + math.pi * bowl["is_boundary"]
    d["bowl_naive_total"] = float(naive_K.sum())
    d["bowl_naive_running"] = running((naive_K, wb[:, 2]), d["zp"])
    d["bowl_interior_total"] = float(bowl["K"][~bowl["is_boundary"]].sum())
    d["bowl_turning_total"] = float(bowl["K"][bowl["is_boundary"]].sum())
    d["scan_meta"] = meta
    d["scan_components"] = components(Vs, Fs)
    naive_scan = scan["K"] + math.pi * scan["is_boundary"]
    d["scan_naive_total"] = float(naive_scan.sum())
    extra = [("bowl 2pi-sum only: %.2f" % (d["bowl_naive_total"] / TWO_PI), (1.0, 0.5, 0.4)),
             ("bowl rim pi-sum: %.2f" % (bowl["total"] / TWO_PI), (0.6, 1.0, 0.6)),
             ("scan %d patches chi %d" % (d["scan_components"], scan["chi"]), (0.75, 0.75, 0.75))]
    d["band"] = sweep_band(d, ("bowl", "scan"), extra4=extra)
    d["labels"] = [T("半球の皿(境界あり、χ = 1)", "hemisphere bowl (with boundary, χ = 1)"),
                   T("恐竜の骨格の走査(開いた面片の集まり)", "dinosaur skeleton scan (open patches)")]
    return d


# --------------------------------------------------------------------------- #
# 全部 → 門の値 → 表・学習用の型 → 仕様                                           #
# --------------------------------------------------------------------------- #
def run_all():
    return {"sharpen": build_sharpen(), "torus": build_torus(), "genus": build_genus(), "asteroid": build_asteroid(),
            "boundary": build_boundary()}


def gates(res) -> dict:
    """定理との差(門の値)。テストもこの関数の値を見る。"""
    g = {}
    s = res["sharpen"]
    g["sharpen_max_diff"] = max(abs(r["total"] - r["two_pi_chi"]) for r in s["recs"])
    g["sharpen_chis"] = [r["chi"] for r in s["recs"]]
    g["sharpen_all_closed"] = bool(all(r["closed"] for r in s["recs"]))
    g["sphere_total_vs_4pi"] = abs(s["recs"][0]["total"] - 4 * math.pi)
    g["sharpen_kmax"] = s["kmax"]
    g["cube_corners"] = s["cube_corners"]
    g["cube_rest_max"] = s["cube_rest_max"]
    g["sharpen_vertices"] = [r["V"] for r in s["recs"]]
    tr = res["torus"]["recs"]
    g["torus_total_abs"] = abs(tr["total"])
    g["torus_chi"] = tr["chi"]
    g["torus_genus"] = tr["genus"]
    g["torus_V"], g["torus_E"], g["torus_F"] = tr["V"], tr["E"], tr["F"]
    g["torus_outer"] = tr["outer"]
    g["torus_inner"] = tr["inner"]
    g["torus_cancel"] = abs(tr["outer"] + tr["inner"])
    g["torus_kmax"], g["torus_kmin"] = tr["kmax"], tr["kmin"]
    ge = res["genus"]
    g["genus_max_diff"] = max(abs(r["total"] - r["two_pi_chi"]) for r in ge["recs"])
    g["genus_chis"] = [r["chi"] for r in ge["recs"]]
    g["genus_genera"] = [r["genus"] for r in ge["recs"]]
    g["genus_all_closed"] = bool(all(r["closed"] for r in ge["recs"]))
    a = res["asteroid"]["recs"][0]
    g["asteroid_diff"] = abs(a["total"] - a["two_pi_chi"])
    g["asteroid_chi"] = a["chi"]
    g["asteroid_closed"] = bool(a["closed"])
    g["asteroid_boundary_edges"] = a["boundary_edges"]
    g["asteroid_nonmanifold_edges"] = a["nonmanifold_edges"]
    g["asteroid_V"], g["asteroid_F"] = a["V"], a["F"]
    g["asteroid_neg_share"] = res["asteroid"]["neg_share"]
    g["asteroid_total_over_2pi"] = a["total"] / TWO_PI
    g["asteroid_kmax"], g["asteroid_kmin"] = res["asteroid"]["kmax"], res["asteroid"]["kmin"]
    g["asteroid_length_m"] = res["asteroid"]["length_m"]
    bd = res["boundary"]
    bowl, scan = bd["recs"]
    g["bowl_chi"] = bowl["chi"]
    g["bowl_boundary_vertices"] = bowl["n_boundary_vertices"]
    g["bowl_naive_total"] = bd["bowl_naive_total"]
    g["bowl_naive_diff"] = abs(bd["bowl_naive_total"] - bowl["two_pi_chi"])
    g["bowl_op_diff"] = abs(bowl["total"] - bowl["two_pi_chi"])
    g["bowl_interior_total"] = bd["bowl_interior_total"]
    g["bowl_turning_total"] = bd["bowl_turning_total"]
    g["scan_components"] = bd["scan_components"]
    g["scan_boundary_edges"] = scan["boundary_edges"]
    g["scan_nonmanifold_edges"] = scan["nonmanifold_edges"]
    g["scan_chi"] = scan["chi"]
    g["scan_V"], g["scan_F"] = scan["V"], scan["F"]
    g["scan_op_diff"] = abs(scan["total"] - scan["two_pi_chi"])
    g["scan_naive_diff"] = abs(bd["scan_naive_total"] - scan["two_pi_chi"])
    g["scan_source"] = bd["scan_meta"]
    return g


def _row(what_ja, what_en, criterion, result, ok):
    """checks の 1 行。ok は門の値と基準の比較(手で True と書かない)。"""
    return {"what": T(what_ja, what_en), "criterion": criterion, "result": result, "ok": bool(ok)}


def gb_checks(g):
    """各タブの「確かめた項目 / 基準 / 結果」。値は gates() の値(テストと同じ基準)。"""
    sc = g["scan_source"]
    return {
        "sharpen": [
            _row("Σ K / 2π(angle_defect)と χ = V − E + F(mesh_euler_characteristic)の一致(5 つの形)",
                 "Σ K / 2π (angle_defect) vs χ = V − E + F (mesh_euler_characteristic), all 5 shapes",
                 "< 1e-9", _e(g["sharpen_max_diff"] / TWO_PI), g["sharpen_max_diff"] < 1e-9),
            _row("球の Σ K と 4π の差", "sphere: Σ K vs 4π", "< 1e-9", _e(g["sphere_total_vs_4pi"]), g["sphere_total_vs_4pi"] < 1e-9),
            _row("立方体: K = π/2 の頂点がちょうど 8 つ(他は 0)", "cube: exactly 8 vertices with K = π/2 (all others 0)",
                 "8, < 1e-9", "%d, %s" % (g["cube_corners"], _e(g["cube_rest_max"])), g["cube_corners"] == 8 and g["cube_rest_max"] < 1e-9),
            _row("最大の K は球 → 立方体で単調に増える", "the largest K grows monotonically from sphere to cube",
                 T("単調増加", "monotone"), "%.3f → %.3f" % (g["sharpen_kmax"][0], g["sharpen_kmax"][-1]),
                 bool(np.all(np.diff(g["sharpen_kmax"]) > 0)))],
        "torus": [
            _row("Σ K(angle_defect)と 2πχ = 0 の差", "Σ K (angle_defect) vs 2πχ = 0", "< 1e-9", _e(g["torus_total_abs"]), g["torus_total_abs"] < 1e-9),
            _row("χ = V − E + F = 0、種数 1(mesh_euler_characteristic)", "χ = V − E + F = 0, genus 1 (mesh_euler_characteristic)",
                 "0, 1", "%d, %s" % (g["torus_chi"], g["torus_genus"]), g["torus_chi"] == 0 and g["torus_genus"] == 1),
            _row("外側(K > 0)の和 + 内側(K < 0)の和", "outer sum (K > 0) + inner sum (K < 0)", "< 1e-9", _e(g["torus_cancel"]),
                 g["torus_cancel"] < 1e-9 and g["torus_outer"] > 0 > g["torus_inner"])],
        "genus": [
            _row("Σ K / 2π と χ の一致(球・トーラス・穴 2 つ・穴 3 つ)", "Σ K / 2π vs χ for sphere, torus, 2 holes, 3 holes",
                 "< 1e-9", _e(g["genus_max_diff"] / TWO_PI), g["genus_max_diff"] < 1e-9),
            _row("χ = 2 − 2g = 2, 0, −2, −4(組合せで数えた値)", "χ = 2 − 2g = 2, 0, −2, −4 (counted combinatorially)",
                 "2, 0, -2, -4", ", ".join(str(c) for c in g["genus_chis"]), g["genus_chis"] == [2, 0, -2, -4]),
            _row("4 つとも閉じた曲面(境界辺 0・非多様体辺 0)", "all 4 are closed surfaces (0 boundary edges, 0 non-manifold edges)",
                 T("すべて閉", "all closed"), T("すべて閉", "all closed") if g["genus_all_closed"] else T("開いた形がある", "some are open"),
                 g["genus_all_closed"])],
        "asteroid": [
            _row("閉じているか(境界辺・非多様体辺)", "closed surface? (boundary edges, non-manifold edges)", "0, 0",
                 "%d, %d" % (g["asteroid_boundary_edges"], g["asteroid_nonmanifold_edges"]), g["asteroid_closed"]),
            _row("Σ K / 2π(頂点 %d・面 %d)と χ = 2" % (g["asteroid_V"], g["asteroid_F"]),
                 "Σ K / 2π (%d vertices, %d faces) vs χ = 2" % (g["asteroid_V"], g["asteroid_F"]),
                 "< 1e-9", _e(g["asteroid_diff"] / TWO_PI), g["asteroid_diff"] < 1e-9 and g["asteroid_chi"] == 2),
            _row("負の K(鞍の形)の頂点があるのに、和は 4π", "vertices with negative K (saddles) exist, yet the sum is 4π",
                 "> 0", "%.0f%%" % (100 * g["asteroid_neg_share"]), g["asteroid_neg_share"] > 0)],
        "boundary": [
            _row("皿(境界あり、χ = 1): 2π − Σθ を全部足した値と 2πχ の差 —— 限界: 境界では一致しない",
                 "bowl (with boundary, χ = 1): Σ(2π − Σθ) over all vertices vs 2πχ — the limit: it fails on a boundary",
                 "< 1e-9", "%.1f × 2π" % (g["bowl_naive_diff"] / TWO_PI), g["bowl_naive_diff"] < 1e-9),
            _row("皿: 境界の頂点に π − Σθ(測地曲率)を使った angle_defect の和と 2πχ の差",
                 "bowl: angle_defect sum with π − Σθ (geodesic curvature) on the %d boundary vertices vs 2πχ" % g["bowl_boundary_vertices"],
                 "< 1e-9", _e(g["bowl_op_diff"]), g["bowl_op_diff"] < 1e-9),
            _row("走査は 1 つの閉曲面ではない(面片の数、境界辺の数)", "the scan is not one closed surface (patches, boundary edges)",
                 "> 1, > 0", "%d, %d" % (g["scan_components"], g["scan_boundary_edges"]), g["scan_components"] > 1 and g["scan_boundary_edges"] > 0),
            _row("走査でも面片ごとの定理は成り立つ: 境界の項つきの Σ K / 2π と χ = %d" % g["scan_chi"],
                 "the theorem still holds patch by patch: Σ K / 2π with boundary terms vs χ = %d" % g["scan_chi"],
                 "< 1e-9", _e(g["scan_op_diff"] / TWO_PI), g["scan_op_diff"] < 1e-9)],
    }


def gb_lessons(g):
    """各タブの学習用の型(問い → 予想 → 再生 → 式 → 限界)。答えの説明の数字は gates() の値。"""
    sc = g["scan_source"]
    return {
        "sharpen": {
            "question": T("球をだんだん角ばらせて立方体にする。頂点ごとの曲がり(角欠損 K)を全部足した値はどうなる?",
                          "A sphere is sharpened step by step into a cube. What happens to the total of the curvature (angle defect K) over all vertices?"),
            "choices": [T("角が立つので増える", "It grows, because corners appear"),
                        T("平らな面が増えるので減る", "It shrinks, because flat faces appear"),
                        T("変わらない(4π のまま)", "It stays the same (4π)")],
            "answer": 2,
            "explain": T("K は角に集まるが、和は変わらない。Σ K = 2πχ で χ = V − E + F = 2 は形を変えても同じ。立方体では 8 つの角だけ K = π/2 "
                         "(8 × π/2 = 4π)で、辺や面の上の頂点は K = 0。球では K が全頂点に薄く広がり(最大 %.3f)、立方体では角に %.3f。"
                         % (g["sharpen_kmax"][0], g["sharpen_kmax"][-1]),
                         "K gathers at the corners, but the total does not change: Σ K = 2πχ with χ = V − E + F = 2 for every shape. "
                         "On the cube only the 8 corners carry K = π/2 (8 × π/2 = 4π); vertices on edges and faces have K = 0. On the "
                         "sphere K is spread thinly over all vertices (at most %.3f); on the cube it is %.3f at a corner."
                         % (g["sharpen_kmax"][0], g["sharpen_kmax"][-1])),
            "formula": T("K_v = 2π − Σ θ(頂点 v のまわりの三角形の角)\nΣ_v K_v = 2π χ\nχ = V − E + F(球と同じ形なら 2)",
                         "K_v = 2π − Σ θ (angles of the triangles around vertex v)\nΣ_v K_v = 2π χ\nχ = V − E + F (2 for anything shaped like a sphere)"),
            "limit": T("1 点の K は三角形の分割に依る(細かく割れば 1 点の K は小さくなる)。分割に依らないのは和だけ。角欠損は曲率そのものではなく"
                       "「曲率 × その頂点が受け持つ面積」で、面積で割った曲率密度は分割で変わる。",
                       "K at one vertex depends on the triangulation (a finer mesh makes each K smaller). Only the total is independent of it. "
                       "The angle defect is not curvature itself but curvature × the area the vertex accounts for; the density per area changes "
                       "with the mesh."),
        },
        "torus": {
            "question": T("ドーナツ(トーラス)の頂点ごとの K を全部足すと?", "Add up K over every vertex of a doughnut (torus). What is the total?"),
            "choices": [T("球と同じ 4π", "4π, like a sphere"), T("0", "0"), T("負の数", "A negative number")],
            "answer": 1,
            "explain": T("外側(管の外周)は球のように膨らみ K > 0、内側(穴の近く)は鞍の形で K < 0。外側の和 %.4f × 2π と内側の和 %.4f × 2π が"
                         "ちょうど打ち消し、Σ K = 0。χ = V − E + F = %d − %d + %d = 0 なので定理どおり。"
                         % (g["torus_outer"] / TWO_PI, g["torus_inner"] / TWO_PI, g["torus_V"], g["torus_E"], g["torus_F"]),
                         "The outside of the tube bulges like a sphere (K > 0); near the hole the surface is saddle-shaped (K < 0). The outer sum "
                         "%.4f × 2π and the inner sum %.4f × 2π cancel exactly, so Σ K = 0. And χ = V − E + F = %d − %d + %d = 0, as the theorem says."
                         % (g["torus_outer"] / TWO_PI, g["torus_inner"] / TWO_PI, g["torus_V"], g["torus_E"], g["torus_F"])),
            "formula": T("Σ_v K_v = 2π χ = 0(トーラスは χ = 0)\n管まわりの角 v の輪ごとの和 ∝ cos v(外側 + / 内側 −)",
                         "Σ_v K_v = 2π χ = 0 (a torus has χ = 0)\nsum over the ring at tube angle v ∝ cos v (+ outside, − inside)"),
            "limit": T("1 つの輪の和は格子の取り方(n_u × n_v)で変わる。和が 0 になるのは閉じたトーラスのとき。管を切って開くと境界ができ、"
                       "境界の項が要る(限界の回)。",
                       "The sum over one ring depends on the grid (n_u × n_v). The total is 0 because the torus is closed; cutting the tube open "
                       "creates a boundary and boundary terms are needed (see the limit tab)."),
        },
        "genus": {
            "question": T("穴を 1 つ増やすごとに、Σ K はどう変わる?", "Each extra hole changes Σ K by how much?"),
            "choices": [T("変わらない", "Not at all"), T("4π ずつ減る", "It drops by 4π per hole"), T("2π ずつ減る", "It drops by 2π per hole")],
            "answer": 1,
            "explain": T("穴(種数)g の閉曲面は χ = 2 − 2g。球 2、トーラス 0、穴 2 つ −2、穴 3 つ −4 で、Σ K = 2πχ は 4π, 0, −4π, −8π。"
                         "穴が増えるほど鞍の部分(K < 0)が増える。4 つの形で Σ K / 2π と χ の差は最大 %s。" % _e(g["genus_max_diff"] / TWO_PI),
                         "A closed surface with g holes (genus g) has χ = 2 − 2g: sphere 2, torus 0, two holes −2, three holes −4, so Σ K = 2πχ is "
                         "4π, 0, −4π, −8π. More holes mean more saddle regions (K < 0). Over the four shapes the largest gap between Σ K / 2π and "
                         "χ is %s." % _e(g["genus_max_diff"] / TWO_PI)),
            "formula": T("χ = 2 − 2g(g = 穴の数)\nΣ_v K_v = 2π(2 − 2g) = 4π − 4πg", "χ = 2 − 2g (g = number of holes)\nΣ_v K_v = 2π(2 − 2g) = 4π − 4πg"),
            "limit": T("穴の数を読めるのは閉じた向き付け可能な曲面だけ。境界や非多様体の辺(3 枚以上の面が集まる辺)があると、χ はあっても種数は決まらない。",
                       "Holes can be counted this way only on a closed orientable surface. With boundaries or non-manifold edges (an edge shared by 3 "
                       "or more faces) χ still exists but the genus is undefined."),
        },
        "asteroid": {
            "question": T("小惑星イトカワの実測の形(頂点 %d)。でこぼこで、くびれもある。Σ K はいくら?" % g["asteroid_V"],
                          "The measured shape of asteroid Itokawa (%d vertices): lumpy, with a neck. What is Σ K?" % g["asteroid_V"]),
            "choices": [T("でこぼこの分だけ 4π より大きい", "More than 4π, because of the bumps"), T("ちょうど 4π", "Exactly 4π"),
                        T("形が複雑すぎて決まらない", "Undetermined, the shape is too complex")],
            "answer": 1,
            "explain": T("くびれ(鞍の形)では K < 0 で、頂点の %.0f%% が負。それでも穴が無い閉曲面なので χ = 2、Σ K / 2π = %.12f。"
                         "でこぼこは正と負で打ち消し、残るのは位相(穴の数)だけ。" % (100 * g["asteroid_neg_share"], g["asteroid_total_over_2pi"]),
                         "At the neck (saddle-shaped) K < 0, and %.0f%% of the vertices are negative. Still, the surface is closed without a hole, so "
                         "χ = 2 and Σ K / 2π = %.12f. Bumps cancel between positive and negative; only the topology (number of holes) remains."
                         % (100 * g["asteroid_neg_share"], g["asteroid_total_over_2pi"])),
            "formula": T("Σ_v K_v = 2π χ = 4π(閉じていて穴が無い)\n境界辺 0・非多様体辺 0 → 閉じている",
                         "Σ_v K_v = 2π χ = 4π (closed, no hole)\n0 boundary edges, 0 non-manifold edges → closed"),
            "limit": T("この形は画像から作られた模型(頂点 %d)で、実物の細かい岩は入っていない。和 4π は模型の位相を言うだけで、"
                       "表面の粗さや岩の数は語らない。" % g["asteroid_V"],
                       "This is a model built from images (%d vertices); the small rocks of the real body are not in it. The total 4π speaks about the "
                       "model's topology only, not about roughness or the number of boulders." % g["asteroid_V"]),
        },
        "boundary": {
            "question": T("球を半分に切った皿(境界あり、χ = 1)。頂点ごとに 2π − Σθ を足すと 2πχ = 2π になる?",
                          "A hemisphere bowl (with a boundary, χ = 1). Does adding 2π − Σθ over its vertices give 2πχ = 2π?"),
            "choices": [T("なる", "Yes"), T("ならない(境界の項が要る)", "No, boundary terms are needed")],
            "answer": 1,
            "explain": T("縁の頂点は平らに開いていて、まわりの角の和は π 前後。2π − Σθ は縁で π 近く余り、全部足すと %.1f × 2π になって 2π にならない。"
                         "縁の頂点に π − Σθ(境界の測地曲率の項)を使うと、内側 %.4f × 2π + 縁 %.4f × 2π = 1 × 2π でちょうど 2πχ(差 %s)。"
                         % (g["bowl_naive_total"] / TWO_PI, g["bowl_interior_total"] / TWO_PI, g["bowl_turning_total"] / TWO_PI, _e(g["bowl_op_diff"])),
                         "A rim vertex is open and flat, so the angles around it add up to about π. Using 2π − Σθ leaves nearly π extra at every rim "
                         "vertex; the total becomes %.1f × 2π, not 2π. With π − Σθ (the geodesic-curvature term) on the rim, interior %.4f × 2π + "
                         "rim %.4f × 2π = 1 × 2π, exactly 2πχ (gap %s)."
                         % (g["bowl_naive_total"] / TWO_PI, g["bowl_interior_total"] / TWO_PI, g["bowl_turning_total"] / TWO_PI, _e(g["bowl_op_diff"]))),
            "formula": T("境界あり: Σ_内部 (2π − Σθ) + Σ_境界 (π − Σθ) = 2π χ\nχ = V − E + F = 1(円板)",
                         "with boundary: Σ_interior (2π − Σθ) + Σ_boundary (π − Σθ) = 2π χ\nχ = V − E + F = 1 (a disc)"),
            "limit": T("これが限界の回。隣の恐竜の骨格は 3-D 走査の模型で、継ぎ目で頂点が切れた %d 枚の開いた面片(間引き前は %d 枚、境界辺 %d 本)。"
                       "面片ごとに定理は成り立つが χ = %d は面片の数を語るだけで、恐竜の形(穴の数)は読めない。閉じた 1 枚の面にするには走査の修復が要る。"
                       % (g["scan_components"], sc["source_components"], sc["source_boundary_edges"], g["scan_chi"]),
                       "This is the limit tab. The dinosaur skeleton next to the bowl is a 3-D scan: %d open patches cut apart at texture seams "
                       "(%d patches and %d boundary edges before decimation). The theorem holds patch by patch, but χ = %d only counts patches; it "
                       "says nothing about the dinosaur's shape (its holes). Reading that would need the scan to be repaired into one closed surface."
                       % (g["scan_components"], sc["source_components"], sc["source_boundary_edges"], g["scan_chi"])),
        },
    }


def _tab(tab_id, label, badge, text, d, numbers, view, cbar, series, axis, clouds=None, events=None):
    return pv.viewer_anim3d_tab(
        tab_id, label, badge, text, d["t"], d["bodies"], d["xyz"], d["quat"], clouds=clouds, events=events, series=series,
        panes=[{"label": T("Fullseye の処理の帯(掃引 → angle_defect → V − E + F → 定理との差。いま効いている段を色で強調)",
                           "Fullseye processing band (sweep → angle_defect → V − E + F → theorem vs op; the active stage is highlighted)"),
                "frames": d["band"], "png": True}],
        cbar=cbar, numbers=numbers, view=view, axis=axis)


def _ev(d, labels):
    """掃引の段: 始まり・中ほど・終わり。"""
    t = d["t"]
    return [{"t": float(t[0]), "label": labels[0]}, {"t": float(t[len(t) // 2]), "label": labels[1]}, {"t": float(t[-1]), "label": labels[2]}]


def build_spec(res, g):
    s, tr, ge, a, bd = res["sharpen"], res["torus"], res["genus"], res["asteroid"], res["boundary"]
    N = pv.viewer_number
    for d in (s, ge, a, bd):
        for b, lab in zip(d["bodies"], d["labels"]):
            b["label"] = lab
    z_lab = T("掃引面の高さ z", "sweep plane height z")
    tab1 = _tab(
        "sharpen", T("球 → 立方体: K は角に集まる、和は変わらない", "Sphere → cube: K gathers at the corners, the total stays"), "passed",
        T("同じ格子(各面 %d × %d)を q ノルムの球面に写した 5 つの形。q = 2 が球、q を大きくすると角ばり、右端は立方体。頂点の色は角欠損 K "
          "(angle_defect の出力)で、球では薄く一様、立方体では 8 つの角だけ π/2。半透明の面が上から下へ通り過ぎた頂点の K を足していくと、"
          "途中の値は形で違うのに、終わりは 5 つとも Σ K / 2π = 2 = χ(mesh_euler_characteristic が頂点・辺・面の数から数えた値)。"
          "下のグラフの線が χ(真値 = 門の値)。" % (SHARPEN_N, SHARPEN_N),
          "Five shapes from the same grid (%d × %d per face) mapped to q-norm spheres: q = 2 is the sphere, larger q sharpens the corners, "
          "the right end is the cube. Vertex colour is the angle defect K (output of angle_defect): thin and uniform on the sphere, π/2 at the 8 "
          "corners of the cube and nothing elsewhere. As the translucent plane sweeps down, the K of the vertices it has passed is added up; "
          "the running totals differ, yet all five end at Σ K / 2π = 2 = χ (counted from vertices, edges and faces by mesh_euler_characteristic). "
          "The line in each graph is χ, the ground truth = the gate's value." % (SHARPEN_N, SHARPEN_N)),
        s,
        [N(T("Σ K / 2π と χ の差(5 つの形の最大)", "Σ K / 2π vs χ (largest of 5)"), _e(g["sharpen_max_diff"] / TWO_PI)),
         N(T("最大の K: 球 / 立方体", "largest K: sphere / cube"), "%.3f / %.3f" % (g["sharpen_kmax"][0], g["sharpen_kmax"][-1])),
         N(T("頂点の数(1 つの形)", "vertices per shape"), "%d" % g["sharpen_vertices"][0])],
        {"az": -1.35, "el": 0.42, "dist": 0.78},
        {"lo": -0.12, "hi": 0.12, "unit": "rad", "cmap": "div", "label": T("角欠損 K_v", "angle defect K_v")},
        sweep_series(s, [T("球 Σ K / 2π", "sphere Σ K / 2π"), T("q = 3", "q = 3"), T("q = 5", "q = 5"), T("q = 10", "q = 10"),
                         T("立方体 Σ K / 2π", "cube Σ K / 2π")], [r["chi"] for r in s["recs"]]),
        sweep_axis(s, z_lab),
        events=_ev(s, [T("上から掃引を始める", "start sweeping from the top"), T("半分: 球は 1、立方体は 4 つの角で 1", "halfway: sphere 1, cube 1 from 4 corners"),
                       T("終わり: 5 つとも 2 = χ", "end: all five reach 2 = χ")]))
    tab2 = _tab(
        "torus", T("トーラス: 外の正と内の負が打ち消して 0", "Torus: outside positive, inside negative, total 0"), "passed",
        T("R = %.0f、r = %.1f のトーラス(%d × %d の格子、mesh_torus)。色は K で、橙 = 正(外側)、青 = 負(内側の鞍)。半透明なので穴の内側の青も"
          "見える。白い輪は管まわりの角 v の位置で、v を 0°(外の赤道)→ 90°(上)→ 180°(内の赤道)→ 360° と回しながら輪ごとの K を足す。"
          "途中の和は 90° で最大になり、180° で 0 に戻り、270° で最小、360° でまた 0。外側の和 %.4f × 2π と内側の和 %.4f × 2π が打ち消す。"
          % (TORUS_R, TORUS_r, TORUS_NU, TORUS_NV, g["torus_outer"] / TWO_PI, g["torus_inner"] / TWO_PI),
          "A torus with R = %.0f and r = %.1f (%d × %d grid, mesh_torus). Colour is K: orange = positive (outside), blue = negative (the saddle "
          "inside). It is translucent, so the blue inside the hole shows. The white ring marks the tube angle v; as v runs 0° (outer equator) → 90° "
          "(top) → 180° (inner equator) → 360°, the K of each ring is added. The running sum peaks at 90°, returns to 0 at 180°, bottoms at 270° "
          "and is 0 again at 360°. The outer sum %.4f × 2π and the inner sum %.4f × 2π cancel."
          % (TORUS_R, TORUS_r, TORUS_NU, TORUS_NV, g["torus_outer"] / TWO_PI, g["torus_inner"] / TWO_PI)),
        tr,
        [N(T("Σ K(angle_defect)", "Σ K (angle_defect)"), _e(g["torus_total_abs"])),
         N(T("χ = V − E + F、種数", "χ = V − E + F, genus"), "%d, %s" % (g["torus_chi"], g["torus_genus"])),
         N(T("K の範囲(最小 / 最大)", "range of K (min / max)"), "%.4f / %.4f" % (g["torus_kmin"], g["torus_kmax"]))],
        {"az": -1.1, "el": 0.75, "dist": 0.72},
        {"lo": -g["torus_kmax"], "hi": g["torus_kmax"], "unit": "rad", "cmap": "div", "label": T("角欠損 K_v", "angle defect K_v")},
        [{"label": T("輪までの Σ K / 2π", "Σ K / 2π up to this ring"), "values": tr["cum"] / TWO_PI, "lo": -0.6, "hi": 0.6, "decimals": 4,
          "color": SERIES_COLORS[0], "threshold": 0.0},
         {"label": T("この輪の K の和 / 2π", "K of this ring / 2π"), "values": tr["recs"]["ring_sum"][tr["j_of"]] / TWO_PI, "lo": -0.06, "hi": 0.06,
          "decimals": 4, "color": SERIES_COLORS[1], "threshold": 0.0}],
        {"values": tr["v_deg"], "segments": [{"k": 0, "label": T("管まわりの角 v", "tube angle v"), "unit": "°", "decimals": 0}]},
        clouds=tr["clouds"],
        events=[{"t": float(tr["t"][0]), "label": T("外の赤道(v = 0°)から", "from the outer equator (v = 0°)")},
                {"t": float(tr["t"][NF // 2]), "label": T("内の赤道(v = 180°): 和が 0 に戻る", "inner equator (v = 180°): the sum is back to 0")},
                {"t": float(tr["t"][-1]), "label": T("一周: Σ K = 0", "full turn: Σ K = 0")}])
    tab3 = _tab(
        "genus", T("穴の数: χ = 2 − 2g、Σ K = 4π, 0, −4π, −8π", "Number of holes: χ = 2 − 2g, Σ K = 4π, 0, −4π, −8π"), "passed",
        T("球(geodesic_dome)、トーラス(mesh_torus)、穴 2 つ、穴 3 つ(梯子の形のグラフを管で太らせた陰関数の等値面)。穴が増えるほど青(K < 0)の"
          "鞍が増える。掃引面が通り過ぎた頂点の K を足すと、終わりの Σ K / 2π は 2, 0, −2, −4 = χ = 2 − 2g。穴の数は「曲がり方を全部足す」だけで読める。",
          "Sphere (geodesic_dome), torus (mesh_torus), two holes, three holes (iso-surfaces of a ladder-shaped graph thickened into tubes). "
          "More holes, more blue saddles (K < 0). Adding K over the vertices the plane has passed ends at Σ K / 2π = 2, 0, −2, −4 = χ = 2 − 2g: "
          "the number of holes can be read just by adding up the curvature."),
        ge,
        [N(T("Σ K / 2π と χ の差(4 つの最大)", "Σ K / 2π vs χ (largest of 4)"), _e(g["genus_max_diff"] / TWO_PI)),
         N(T("χ(組合せ): 球 / トーラス / 穴 2 / 穴 3", "χ (counted): sphere / torus / 2 holes / 3 holes"), " / ".join(str(c) for c in g["genus_chis"]))],
        {"az": -1.35, "el": 0.5, "dist": 0.8},
        {"lo": -0.15, "hi": 0.15, "unit": "rad", "cmap": "div", "label": T("角欠損 K_v", "angle defect K_v")},
        sweep_series(ge, [T("球", "sphere"), T("トーラス", "torus"), T("穴 2 つ", "2 holes"), T("穴 3 つ", "3 holes")], [r["chi"] for r in ge["recs"]]),
        sweep_axis(ge, z_lab),
        events=_ev(ge, [T("上から掃引を始める", "start sweeping from the top"), T("半分: 穴の鞍で和が下がる", "halfway: the saddles pull the sums down"),
                        T("終わり: 2, 0, −2, −4", "end: 2, 0, −2, −4")]))
    tab4 = _tab(
        "asteroid", T("実物: 小惑星イトカワでも 4π", "A real object: asteroid Itokawa also gives 4π"), "passed",
        T("探査機の画像から作られた小惑星イトカワの形(頂点 %d・面 %d、x 方向の長さ %.0f m)。色は K で、くびれや窪みの鞍では青(負)。頂点の %.0f%% が"
          "K < 0 なのに、掃引面が通り過ぎた頂点を全部足すと Σ K / 2π = %.6f = χ = 2。閉じていて穴が無いことは mesh_euler_characteristic が"
          "境界辺 0・非多様体辺 0 で確かめる。"
          % (g["asteroid_V"], g["asteroid_F"], g["asteroid_length_m"], 100 * g["asteroid_neg_share"], g["asteroid_total_over_2pi"]),
          "The shape of asteroid Itokawa built from spacecraft images (%d vertices, %d faces, %.0f m along x). Colour is K; the saddles at the neck "
          "and in hollows are blue (negative). %.0f%% of the vertices have K < 0, yet adding every vertex the plane has passed gives Σ K / 2π = "
          "%.6f = χ = 2. That the surface is closed with no hole is checked by mesh_euler_characteristic: 0 boundary edges, 0 non-manifold edges."
          % (g["asteroid_V"], g["asteroid_F"], g["asteroid_length_m"], 100 * g["asteroid_neg_share"], g["asteroid_total_over_2pi"])),
        a,
        [N(T("Σ K / 2π と χ = 2 の差", "Σ K / 2π vs χ = 2"), _e(g["asteroid_diff"] / TWO_PI)),
         N(T("境界辺・非多様体辺", "boundary edges, non-manifold edges"), "%d, %d" % (g["asteroid_boundary_edges"], g["asteroid_nonmanifold_edges"])),
         N(T("K の範囲(最小 / 最大)", "range of K (min / max)"), "%.3f / %.3f" % (g["asteroid_kmin"], g["asteroid_kmax"]))],
        {"az": -1.2, "el": 0.45, "dist": 0.78},
        {"lo": -0.1, "hi": 0.1, "unit": "rad", "cmap": "div", "label": T("角欠損 K_v", "angle defect K_v")},
        sweep_series(a, [T("イトカワ Σ K / 2π", "Itokawa Σ K / 2π")], [2]),
        sweep_axis(a, z_lab, unit="m", decimals=0),
        events=_ev(a, [T("上から掃引を始める", "start sweeping from the top"), T("半分: くびれの負の K が効く", "halfway: the neck's negative K pulls down"),
                       T("終わり: 2 = χ", "end: 2 = χ")]))
    sc = g["scan_source"]
    tab5 = _tab(
        "boundary", T("境界のある面(限界の回): 皿と、骨格の走査", "Surfaces with a boundary (the limit tab): a bowl and a skeleton scan"), "limit",
        T("左は半球の皿(geodesic_dome の半球、縁の頂点 %d)。境界があるので χ = V − E + F = 1。縁の頂点にも 2π − Σθ を使って足すと %.1f × 2π に"
          "なり、2πχ = 2π にならない(バッジの表の落ちた行)。縁では π − Σθ(境界の測地曲率の項)を使うのが離散 Gauss–Bonnet で、angle_defect は"
          "そうしている(内側 %.4f + 縁 %.4f = 1)。右は恐竜の骨格の 3-D 走査(館の公開データ、面を間引いた)。1 枚の面に見えるが、テクスチャの継ぎ目で"
          "頂点が切れた %d 枚の開いた面片で、境界辺 %d 本。面片ごとに定理は成り立つ(Σ K / 2π = χ = %d)が、この χ は面片の数で、恐竜の形は語らない。"
          % (g["bowl_boundary_vertices"], g["bowl_naive_total"] / TWO_PI, g["bowl_interior_total"] / TWO_PI, g["bowl_turning_total"] / TWO_PI,
             g["scan_components"], g["scan_boundary_edges"], g["scan_chi"]),
          "Left: a hemisphere bowl (geodesic_dome hemisphere, %d rim vertices). It has a boundary, so χ = V − E + F = 1. Adding 2π − Σθ at the rim "
          "vertices too gives %.1f × 2π, not 2πχ = 2π (the failed row in the badge's table). Discrete Gauss–Bonnet uses π − Σθ (the geodesic-"
          "curvature term) on the rim, and angle_defect does so (interior %.4f + rim %.4f = 1). Right: a 3-D scan of a dinosaur skeleton (a "
          "museum's open data, decimated). It looks like one surface but is %d open patches cut at texture seams, with %d boundary edges. The "
          "theorem holds patch by patch (Σ K / 2π = χ = %d), but this χ counts patches and says nothing about the dinosaur's shape."
          % (g["bowl_boundary_vertices"], g["bowl_naive_total"] / TWO_PI, g["bowl_interior_total"] / TWO_PI, g["bowl_turning_total"] / TWO_PI,
             g["scan_components"], g["scan_boundary_edges"], g["scan_chi"])),
        bd,
        [N(T("皿: 2π − Σθ だけの和 / 2π(χ = 1 のはず)", "bowl: Σ(2π − Σθ) / 2π (χ should be 1)"), "%.3f" % (g["bowl_naive_total"] / TWO_PI)),
         N(T("皿: 境界の項つき(angle_defect)と 2πχ の差", "bowl: with boundary terms (angle_defect) vs 2πχ"), _e(g["bowl_op_diff"])),
         N(T("走査: 面片 / 境界辺 / χ", "scan: patches / boundary edges / χ"), "%d / %d / %d" % (g["scan_components"], g["scan_boundary_edges"], g["scan_chi"]))],
        {"az": -1.3, "el": 0.5, "dist": 0.8},
        {"lo": -0.3, "hi": 0.3, "unit": "rad", "cmap": "div", "label": T("角欠損 K_v(縁は π − Σθ)", "angle defect K_v (π − Σθ on a rim)")},
        [{"label": T("皿: 2π − Σθ だけの和 / 2π", "bowl: Σ(2π − Σθ) / 2π"), "values": bd["bowl_naive_running"] / TWO_PI, "lo": -0.3,
          "hi": round(max(1.3, g["bowl_naive_total"] / TWO_PI + 0.3), 1), "decimals": 3, "color": "#ff8a65", "threshold": 1.0},
         {"label": T("皿: 境界の項つき Σ K / 2π", "bowl: Σ K / 2π with boundary terms"), "values": bd["sums"][0] / TWO_PI, "lo": -0.3, "hi": 1.3,
          "decimals": 3, "color": SERIES_COLORS[0], "threshold": 1.0},
         {"label": T("走査: 境界の項つき Σ K / 2π", "scan: Σ K / 2π with boundary terms"), "values": bd["sums"][1] / TWO_PI, "lo": -50.0,
          "hi": g["scan_chi"] + 200.0, "decimals": 1, "color": SERIES_COLORS[3], "threshold": float(g["scan_chi"])}],
        sweep_axis(bd, z_lab),
        events=_ev(bd, [T("上から掃引を始める", "start sweeping from the top"), T("半分: 皿の縁に届く", "halfway: the plane reaches the rim"),
                        T("終わり: 皿は 1 = χ、2π − Σθ だけなら外れる", "end: bowl 1 = χ; with 2π − Σθ only it misses")]))
    checks, lessons = gb_checks(g), gb_lessons(g)
    tabs = [tab1, tab2, tab3, tab4, tab5]
    for tb in tabs:
        tb["checks"], tb["lesson"] = checks[tb["id"]], lessons[tb["id"]]
    if tabs[0]["badge"] == "limit":
        raise AssertionError("限界の回を最初のタブにしない(成功の回を見てから壊れ方を見る順)")
    spec = pv.viewer_spec(
        "gauss_bonnet",
        T("どんな形でも、曲がり方を全部足すと同じ数になる(離散 Gauss–Bonnet)", "Add up the curvature of any shape and you get the same number (discrete Gauss–Bonnet)"),
        T("頂点ごとの角欠損 K を足し上げる —— 計算は fullseye の angle_defect と mesh_euler_characteristic",
          "Adding up the angle defect K vertex by vertex — computed by fullseye's angle_defect and mesh_euler_characteristic"),
        T("各タブは ① 問い → ② 予想(選択肢を押すと答えが開く)→ ③ 再生(▶)→ ④ 式 → ⑤ 限界 の順。時間つまみの読みは掃引面の高さなどの量。"
          "下の帯の 4 段は順に光る(掃引 → angle_defect → V − E + F → 定理との差)。バッジを押すと、確かめた項目・基準・結果の表が開く。ドラッグで視点を回す。",
          "Each tab runs ① question → ② predict (tap a choice to reveal the answer) → ③ play (▶) → ④ equation → ⑤ limit. The time slider "
          "reads a quantity such as the sweep plane height. The four band stages light up in turn (sweep → angle_defect → V − E + F → theorem vs op). "
          "Tap a badge to open what was checked, the criterion and the result. Drag to orbit."),
        tabs,
        credit=T("小惑星イトカワの形: Gaskell Itokawa Shape Model V1.1(NASA Planetary Data System、CC0 1.0、面は原本のまま)。恐竜の骨格の走査: "
                 "Triceratops horridus(Smithsonian Institution、CC0、面を %dk → %dk に間引いた)。穴 2 つ・3 つの形は合成。"
                 % (round(sc["source_faces"] / 1e3), round(g["scan_F"] / 1e3)),
                 "Asteroid Itokawa shape: Gaskell Itokawa Shape Model V1.1 (NASA Planetary Data System, CC0 1.0, faces as in the original). Dinosaur "
                 "skeleton scan: Triceratops horridus (Smithsonian Institution, CC0, decimated from %dk to %dk faces). The 2-hole and 3-hole shapes "
                 "are synthetic." % (round(sc["source_faces"] / 1e3), round(g["scan_F"] / 1e3))))
    return spec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="書かずに、門の値の印字と HTML の生成だけ")
    ap.add_argument("--out", default=str(OUT_HTML))
    a = ap.parse_args(argv)
    res = run_all()
    g = gates(res)
    for k, v in g.items():
        print("%-28s %s" % (k, v))
    spec = build_spec(res, g)
    if a.check:
        n = len(pv._build_html(spec, list(LANGS)).encode("utf-8"))
        print("ok: %d bytes (not written)" % n)
        return 0
    path = pv.write_viewer(spec, a.out, list(LANGS))
    print("wrote %s (%.2f MB)" % (path, Path(path).stat().st_size / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
