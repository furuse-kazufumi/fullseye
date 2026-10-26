#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""塩(NaCl)の結晶の粉末 X 線回折 —— なぜその角度にだけ光るのか(動く 3-D の教科書、2026-10-26)。

    py -3.11 tools/anim3d_i18n.py --build build_saltxrd_anim3d --out docs/view2026/anim3d/salt_xrd_anim3d.html
    py -3.11 tools/build_saltxrd_anim3d.py --check          # 書かずに、門の値の印字と HTML の生成だけ(ja/en)

結晶構造は COD 1000041(塩化ナトリウム、CC0)の CIF を ``data/cod_1000041/cod_1000041.cif`` に置いて ``cif_read`` で読む
(取得元のコメント行だけ外し、データは原文のまま)。反射の一覧(面間隔 d・Bragg の 2θ・多重度・|F|²・消滅)は
``powder_reflections``、2-D 検出器のデバイ環は ``debye_ring_image`` → ``azimuthal_integrate`` → ``diffraction_peaks``。
**数字はすべて op の出力**で、理論の線(閉じた式)は op とは別に書いて差を門にする:

* Bragg: ``2θ = 2 asin(λ / 2d)``、立方晶の面間隔 ``d = a / √(h² + k² + l²)``
* 消滅則(Fm-3m): h, k, l が全部偶数か全部奇数の面だけ残る。構造因子は ``F = 4 (f_Na ± f_Cl)``(全偶で +、全奇で −)
* 密度 ``ρ = Z M / (N_A a³)``(Z = 4)

タブ(1 タブ = 1 題材、各タブは ① 問い → ② 予想 → ③ 再生 → ④ 式 → ⑤ 限界):

* **結晶と面**: 単位胞(Na / Cl の球)に格子面 (hkl) の板を半透明で重ねる。つまみ = 面指数を順に(読みは面間隔 d)。
* **Bragg の幾何**: 2 枚の面で反射した 2 本の光線、行路差 2d sinθ。つまみ = θ。行路差が λ の整数倍の所でだけ受光面が光る。
* **粉末とデバイ環(限界の回)**: 単結晶 1 粒 → 粒の向きをばらばらに → 点が環に育つ。後半は λ を長くし、
  λ > 2d の面の環から消え、λ = 7 Å では 1 本も残らない(asin の定義域の外 = 限界。op の一覧に残る禁制の (100) は |F|² ≈ 4e-29 の数値ゼロ)。
* **消滅則**: 単位胞の 8 原子の波を 1 本ずつ描き、足し合わせる。混合パリティの面は 4 本ずつ打ち消して 0、
  全奇は f_Na − f_Cl で弱く、全偶は f_Na + f_Cl で強い。帯 = 計算した粉末パターンの棒図。

**regen_all には入れない**(``pocviewer.write_viewer`` で書く手回しの生成物。出力を変えたら手で回して commit)。
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
CIF = ROOT / "data" / "cod_1000041" / "cod_1000041.cif"
OUT_HTML = ROOT / "docs" / "view2026" / "anim3d" / "salt_xrd_anim3d.html"
LANGS = ("ja", "en")
FPS = 12.0
STAGE_FRAMES = 3

LAM = 1.5406                     # Cu Kα1 [Å](CIF の格子定数と同じ単位)
TT_MAX = 120.0                   # 反射の一覧の上限 2θ [deg]
Z_CELL = 4                       # 単位胞の化学式単位(CIF の _cell_formula_units_Z)
M_NA, M_CL = 22.98977, 35.453    # 原子量 [g/mol](手引書の値。op の ATOMIC_MASS とは別に書く)
N_A = 6.02214076e23
RHO_HANDBOOK = 2.17              # NaCl の密度の手引書の値 [g/cm³](25 °C)
B_ISO = 0.5                      # CIF に変位パラメータが無いので cif_read の既定 B [Å²]
NA_RGB, CL_RGB = (0.62, 0.52, 1.0), (0.35, 0.90, 0.55)
PLANE_RGB, PLANE_ALPHA = (1.0, 0.80, 0.35), 0.34
EST_RGB = (1.0, 0.84, 0.31)
USED_OPS = ("cif_read", "powder_reflections", "debye_ring_image", "azimuthal_integrate", "diffraction_peaks")


# --------------------------------------------------------------------------- #
# 相(CIF)と反射                                                                 #
# --------------------------------------------------------------------------- #
def load_phase():
    return L.cif_read(str(CIF))


def reflections(phase, lam=LAM, tmax=TT_MAX, include_extinct=True):
    return L.powder_reflections(phase, lam, two_theta_max=tmax, include_extinct=include_extinct)


def rows(ref):
    """反射の一覧を行の list に。"""
    return [{"hkl": tuple(int(v) for v in h), "d": float(d), "tt": float(tt), "m": int(m), "F2": float(f2),
             "I": float(i), "ext": bool(e)}
            for h, d, tt, m, f2, i, e in zip(ref["hkl"], ref["d"], ref["two_theta"], ref["multiplicity"], ref["F2"],
                                              ref["intensity"], ref["extinct"])]


def two_theta_closed(d, lam):
    """Bragg の閉形式 2θ = 2 asin(λ / 2d)[deg]。λ > 2d なら NaN(定義域の外)。"""
    s = lam / (2.0 * d)
    return float("nan") if s > 1 else math.degrees(2.0 * math.asin(s))


def d_cubic(a, hkl):
    return a / math.sqrt(sum(v * v for v in hkl))


def parity_allowed(hkl):
    p = {v % 2 for v in hkl}
    return len(p) == 1


def f0(symbol, s):
    """原子の散乱因子 f₀(s) = c + Σ aᵢ exp(−bᵢ s²)(係数は pxrd.FORM_FACTORS の表。式はここに別に書く)。"""
    import pxrd
    a1, a2, a3, a4, a5, c, b1, b2, b3, b4, b5 = pxrd.FORM_FACTORS[symbol][1]
    return c + sum(ai * math.exp(-bi * s * s) for ai, bi in ((a1, b1), (a2, b2), (a3, b3), (a4, b4), (a5, b5)))


def F2_closed(hkl, d, B=B_ISO):
    """閉じた式 |F|² = |4 (f_Na ± f_Cl)|² e^(−2Bs²)(全偶 +、全奇 −、混合 0)。s = 1/(2d)。"""
    s = 0.5 / d
    if not parity_allowed(hkl):
        return 0.0
    sign = 1.0 if hkl[0] % 2 == 0 else -1.0
    fn, fc = f0("Na1+", s) * math.exp(-B * s * s), f0("Cl1-", s) * math.exp(-B * s * s)
    return (4.0 * (fn + sign * fc)) ** 2


def atom_phases(hkl):
    """単位胞の 8 原子(Na 4 + Cl 4)の位相 2π h·x [rad] と種類。"""
    na = [(0, 0, 0), (0, .5, .5), (.5, 0, .5), (.5, .5, 0)]
    cl = [(.5, .5, .5), (.5, 0, 0), (0, .5, 0), (0, 0, .5)]
    return [("Na", 2 * math.pi * sum(h * x for h, x in zip(hkl, p))) for p in na] + \
           [("Cl", 2 * math.pi * sum(h * x for h, x in zip(hkl, p))) for p in cl]


def density_closed(a):
    return Z_CELL * (M_NA + M_CL) / (N_A * (a * 1e-8) ** 3)


# --------------------------------------------------------------------------- #
# 3-D の部品                                                                     #
# --------------------------------------------------------------------------- #
def merge(parts):
    P, F, C, o = [], [], [], 0
    for pos, faces, rgb in parts:
        pos = np.asarray(pos, float)
        P.append(pos)
        F.append(np.asarray(faces, int) + o)
        C.append(np.tile(np.asarray(rgb, float), (len(pos), 1)))
        o += len(pos)
    return np.concatenate(P), np.concatenate(F), np.concatenate(C)


def box(c, s):
    c, s = np.asarray(c, float), np.asarray(s, float) / 2
    v = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float) * s + c
    f = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
         [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]
    return v, np.array(f)


def tube(p0, p1, r, n=6):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    a = p1 - p0
    ln = np.linalg.norm(a)
    a = a / ln
    h = np.array([0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(a, h)
    u /= np.linalg.norm(u)
    w = np.cross(a, u)
    ang = 2 * np.pi * np.arange(n) / n
    ring = np.cos(ang)[:, None] * u + np.sin(ang)[:, None] * w
    v = np.concatenate([p0 + r * ring, p1 + r * ring, [p0, p1]])
    f = []
    for i in range(n):
        j = (i + 1) % n
        f += [[i, j, n + j], [i, n + j, n + i], [2 * n, j, i], [2 * n + 1, n + i, n + j]]
    return v, np.array(f)


def sphere(r, nlat=5, nlon=8):
    v = [[0.0, 0.0, r]]
    for i in range(1, nlat):
        th = math.pi * i / nlat
        for j in range(nlon):
            ph = 2 * math.pi * j / nlon
            v.append([r * math.sin(th) * math.cos(ph), r * math.sin(th) * math.sin(ph), r * math.cos(th)])
    v.append([0.0, 0.0, -r])
    bottom = len(v) - 1
    f = []
    for j in range(nlon):
        f.append([0, 1 + j, 1 + (j + 1) % nlon])
    for i in range(nlat - 2):
        for j in range(nlon):
            a, b = 1 + i * nlon + j, 1 + i * nlon + (j + 1) % nlon
            f += [[a, a + nlon, b + nlon], [a, b + nlon, b]]
    base = 1 + (nlat - 2) * nlon
    for j in range(nlon):
        f.append([bottom, base + (j + 1) % nlon, base + j])
    return np.array(v), np.array(f)


def slab(sx, sy, th):
    """局所 xy 面の板(法線 +z)。"""
    return box((0, 0, 0), (sx, sy, th))


def q_align(a, b):
    """単位ベクトル a を b に回す四元数 (w, x, y, z)。"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    c = float(np.dot(a, b))
    if c > 1 - 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0])
    if c < -1 + 1e-12:
        ax = np.cross(a, [1.0, 0.0, 0.0])
        if np.linalg.norm(ax) < 1e-9:
            ax = np.cross(a, [0.0, 1.0, 0.0])
        ax /= np.linalg.norm(ax)
        return np.array([0.0, *ax])
    ax = np.cross(a, b)
    ax /= np.linalg.norm(ax)
    ang = math.acos(c)
    return np.array([math.cos(ang / 2), *(math.sin(ang / 2) * ax)])


def q_mul(p, q):
    w1, x1, y1, z1 = p
    w2, x2, y2, z2 = q
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def q_rot(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def q_small(rng, deg):
    ax = rng.normal(size=3)
    ax /= np.linalg.norm(ax)
    a = math.radians(deg) / 2
    return np.array([math.cos(a), *(math.sin(a) * ax)])


def q_random(rng):
    q = rng.normal(size=4)
    return q / np.linalg.norm(q)


def q_dir_xz(d):
    """局所 +x を x-z 面の向き d に回す(y 軸まわり)。"""
    beta = math.atan2(-d[2], d[0])
    return np.array([math.cos(beta / 2), 0.0, math.sin(beta / 2), 0.0])


def body(name, mesh, label=None, alpha=None):
    pos, faces, rgb = mesh
    b = {"name": name, "pos": pos, "faces": faces, "rgb": np.clip(rgb, 0, 1)}
    if label is not None:
        b["label"] = label
    if alpha is not None:
        b["alpha"] = float(alpha)
    return b


def ease(p):
    p = min(1.0, max(0.0, p))
    return 0.5 - 0.5 * math.cos(math.pi * p)


def sweep(lo, hi, n, slow=()):
    x = np.linspace(lo, hi, 4001)
    sp = np.ones_like(x)
    for c, hw, f in slow:
        sp = np.minimum(sp, np.where(np.abs(x - c) < hw, f, 1.0))
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (1 / sp[1:] + 1 / sp[:-1]) * np.diff(x))])
    u = np.linspace(0, cum[-1], n)
    return np.interp(u, cum, x)


def line_pts(p0, p1, n):
    s = np.linspace(0, 1, n)[:, None]
    return np.asarray(p0, float) + s * (np.asarray(p1, float) - np.asarray(p0, float))


# --------------------------------------------------------------------------- #
# 単位胞(Na / Cl の球と格子面の板)                                                #
# --------------------------------------------------------------------------- #
def cell_bodies(a, r_na=0.55, r_cl=0.95):
    """単位胞 [0, a]³ の 27 格子点(a/2 刻み)に Na / Cl の球、辺は細い管。"""
    na, cl = [], []
    for i in (0, 1, 2):
        for j in (0, 1, 2):
            for k in (0, 1, 2):
                p = np.array([i, j, k]) * a / 2
                (na if (i + j + k) % 2 == 0 else cl).append(p)
    sn, sc = sphere(r_na), sphere(r_cl)
    edges = []
    for s_, e_ in (((0, 0, 0), (1, 0, 0)), ((0, 0, 0), (0, 1, 0)), ((0, 0, 0), (0, 0, 1)), ((1, 1, 1), (0, 1, 1)),
                   ((1, 1, 1), (1, 0, 1)), ((1, 1, 1), (1, 1, 0)), ((1, 0, 0), (1, 1, 0)), ((1, 0, 0), (1, 0, 1)),
                   ((0, 1, 0), (1, 1, 0)), ((0, 1, 0), (0, 1, 1)), ((0, 0, 1), (1, 0, 1)), ((0, 0, 1), (0, 1, 1))):
        edges.append((*tube(np.array(s_) * a, np.array(e_) * a, 0.06, 4), (0.55, 0.60, 0.68)))
    return [body("na", merge([(sn[0] + p, sn[1], NA_RGB) for p in na]), T("Na⁺(小)", "Na⁺ (small)")),
            body("cl", merge([(sc[0] + p, sc[1], CL_RGB) for p in cl]), T("Cl⁻(大)", "Cl⁻ (large)")),
            body("cell", merge(edges), T("単位胞 a × a × a", "unit cell a × a × a"))]


def plane_stack(hkl, a, n_planes):
    """面 (hkl) の板の位置(胞の中心に近い n_planes 枚、hX + kY + lZ = m a の順)と法線・面間隔。"""
    v = np.array(hkl, float)
    nrm = v / np.linalg.norm(v)
    d = a / np.linalg.norm(v)
    pc = float(np.dot(np.full(3, a / 2), nrm))
    m0 = int(round(pc / d))
    ms = [m0 + i - n_planes // 2 for i in range(n_planes)]
    return [m * d * nrm for m in ms], nrm, d


# --------------------------------------------------------------------------- #
# 処理の帯(ラスタ)                                                              #
# --------------------------------------------------------------------------- #
PW, PH, HEAD, GAP = 146, 82, 20, 10
BG = 0.11
STAGE_RGB = [(0.80, 0.80, 0.80), (0.40, 0.80, 0.45), (0.31, 0.76, 0.97), EST_RGB]
STAGE_NAME = ("1 crystal (CIF)", "2 fullseye op", "3 pattern", "4 theory - op")
_TXT_CACHE: dict = {}


def _txt(img, s, x, y, color, size=9):
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


def mini_plot(img, box_, curves, xlim, ylim, cursor=None, guides=(), sticks=()):
    """小さなグラフ。curves = [(xs, ys, color)]、sticks = [(x, y, color)](棒図)、guides = [(x|None, y|None, color)]。"""
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
    for x, y, col in sticks:
        if xlim[0] <= x <= xlim[1]:
            _seg(img, rc(x, ylim[0]), rc(x, min(y, ylim[1])), col)
    for xs, ys, col in curves:
        xs, ys = np.asarray(xs, float), np.asarray(ys, float)
        for i in range(len(xs) - 1):
            if np.isfinite(ys[i]) and np.isfinite(ys[i + 1]):
                _seg(img, rc(xs[i], np.clip(ys[i], *ylim)), rc(xs[i + 1], np.clip(ys[i + 1], *ylim)), col)
    if cursor is not None:
        x, y, col = cursor
        if xlim[0] <= x <= xlim[1]:
            a = rc(x, ylim[0])
            _seg(img, (r0, a[1]), (r0 + h - 1, a[1]), (0.45, 0.45, 0.45))
            if y is not None and np.isfinite(y):
                p = rc(x, np.clip(y, *ylim))
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        _px(img, int(p[0]) + dr, int(p[1]) + dc, col)


def _heads(names=STAGE_NAME):
    key = ("heads",) + tuple(names)
    if key in _TXT_CACHE:
        return _TXT_CACHE[key]
    heads = []
    for s in range(4):
        row = []
        for on in (False, True):
            hb = np.full((HEAD, PW, 3), BG)
            _txt(hb, names[s], 4, HEAD // 2, STAGE_RGB[s] if on else (0.55, 0.55, 0.55), 10)
            row.append(hb)
        heads.append(row)
    tag = np.full((16, 70, 3), BG)
    _txt(tag, "Fullseye", 14, 8, (0.45, 0.62, 0.80), 9)
    _TXT_CACHE[key] = (heads, tag)
    return heads, tag


def panel_text(lines, plot=None):
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


# 線形代数の丸め屑は OS / BLAS によって末尾が変わる。教材に意味があるのは
# 1e-12 未満であることなので、0 も含めて安定した上限だけを表示する。
DUST = 1e-12


def _e(x):
    return "< 1e-12" if abs(x) < DUST else "%.1e" % x


def hkl_s(hkl):
    return "(%d%d%d)" % tuple(hkl)


# --------------------------------------------------------------------------- #
# タブ 1: 結晶と格子面                                                            #
# --------------------------------------------------------------------------- #
PLANE_FAMILIES = ((1, 1, 1), (2, 0, 0), (2, 2, 0), (3, 1, 1), (2, 2, 2), (4, 0, 0))
SEG1 = 12
N_PLANES = 4


def build_crystal(phase, ref_rows):
    a = phase["cell"][0]
    byhkl = {r["hkl"]: r for r in ref_rows}
    Tn = SEG1 * len(PLANE_FAMILIES)
    t = np.arange(Tn) / FPS
    bodies = cell_bodies(a)
    sx = 1.45 * a
    for j in range(N_PLANES):
        bodies.append(body("plane%d" % j, merge([(*slab(sx, sx, 0.03 * a), PLANE_RGB)]),
                           T("格子面 (hkl)、間隔 d", "lattice planes (hkl), spacing d") if j == 0 else None, PLANE_ALPHA))
    bodies.append(body("probe", merge([(*sphere(0.28, 6, 10), (1.0, 1.0, 1.0))]), T("面から次の面へ(距離 d)", "from one plane to the next (distance d)")))
    B = len(bodies)
    xyz = np.zeros((Tn, B, 3))
    quat = np.zeros((Tn, B, 4))
    quat[..., 0] = 1.0
    recs, axis_vals, events = [], np.zeros(Tn), []
    for fi, hkl in enumerate(PLANE_FAMILIES):
        pos, nrm, d = plane_stack(hkl, a, N_PLANES)
        qn = q_align([0, 0, 1], nrm)
        r = byhkl[hkl]
        events.append({"t": float(t[fi * SEG1]), "label": T("面 %s、d = %.3f Å" % (hkl_s(hkl), d), "planes %s, d = %.3f Å" % (hkl_s(hkl), d))})
        for f in range(SEG1):
            k = fi * SEG1 + f
            axis_vals[k] = d
            for j in range(N_PLANES):
                p = ease((f - 1.2 * j) / 4.0)
                xyz[k, 3 + j] = pos[j] + (1.0 - p) * 1.0 * a * nrm
                quat[k, 3 + j] = qn
            u = ease((f - 6) / 5.0)
            xyz[k, 3 + N_PLANES] = pos[1] + u * (pos[2] - pos[1])
            recs.append({"hkl": hkl, "d": d, "row": r, "d_closed": d_cubic(a, hkl), "tt_closed": two_theta_closed(d, LAM)})
    # 帯
    allowed = [r for r in ref_rows if not r["ext"]]
    imax = max(r["I"] for r in allowed)
    sticks_all = [(r["tt"], 100 * r["I"] / imax, (0.5, 0.5, 0.5)) for r in allowed]
    band = []
    for k, rc_ in enumerate(recs):
        band.append(band_frame(crystal_panels(rc_, phase, a, sticks_all, imax), active_stage(k)))
    series = [{"label": T("面間隔 d(op)", "spacing d (op)"), "values": np.array([r["d"] for r in recs]), "lo": 1.0, "hi": 3.5,
               "unit": "Å", "decimals": 3, "color": "#ffd54f"},
              {"label": T("2θ(op)", "2θ (op)"), "values": np.array([r["row"]["tt"] for r in recs]), "lo": 20, "hi": 70,
               "unit": "°", "decimals": 2, "color": "#90caf9"}]
    axis = {"values": axis_vals, "segments": [{"k": fi * SEG1, "label": T("面 %s の面間隔 d" % hkl_s(h), "spacing d of planes %s" % hkl_s(h)),
                                               "unit": "Å", "decimals": 3} for fi, h in enumerate(PLANE_FAMILIES)]}
    return {"t": t, "bodies": bodies, "xyz": xyz, "quat": quat, "clouds": [], "events": events, "series": series,
            "band": np.stack(band), "recs": recs, "axis": axis, "a": a}


def crystal_panels(r, phase, a, sticks_all, imax):
    hkl, d, row = r["hkl"], r["d"], r["row"]
    p1 = panel_text([("NaCl  rock salt", (0.9, 0.9, 0.9)), ("Fm-3m  Z = 4", (0.75, 0.75, 0.75)),
                     ("a = %.3f A (COD 1000041)" % a, (1.0, 1.0, 1.0)),
                     ("rho = %.3f g/cm3" % phase["density"], (0.75, 0.75, 0.75)), ("(cif_read)", (0.55, 0.55, 0.55))])
    p2 = panel_text([("cif_read ->", (0.55, 0.9, 0.6)), ("powder_reflections", (0.55, 0.9, 0.6)),
                     ("hkl %s  m = %d" % (hkl_s(hkl), row["m"]), (0.9, 0.9, 0.9)), ("d = %.4f A" % row["d"], (1.0, 1.0, 1.0)),
                     ("2theta = %.3f deg" % row["tt"], (1.0, 1.0, 1.0))])

    def plot(p):
        mini_plot(p, (20, 4, PH - 24, PW - 8), [], (20, 120), (0, 105),
                  sticks=sticks_all + [(row["tt"], 100 * row["I"] / imax, EST_RGB)])
    p3 = panel_text([("Cu K-alpha %.4f A" % LAM, (0.8, 0.8, 0.8))], plot)
    p4 = panel_text([("d = a / sqrt(h2+k2+l2)", EST_RGB), ("  = %.4f A" % r["d_closed"], (0.95, 0.95, 0.95)),
                     ("2th = 2 asin(lam/2d)", EST_RGB), ("  = %.4f deg" % r["tt_closed"], (0.95, 0.95, 0.95)),
                     ("diff %s / %s" % (_e(abs(r["d_closed"] - row["d"])), _e(abs(r["tt_closed"] - row["tt"]))), (0.6, 1.0, 0.6))])
    return [p1, p2, p3, p4]


# --------------------------------------------------------------------------- #
# タブ 2: Bragg の幾何(θ を振る)                                                  #
# --------------------------------------------------------------------------- #
N_BRAGG = 5                       # 反射する面の枚数
RAY_L = 22.0
DET_L = 26.0


def interference(theta_deg, d, lam, n=N_BRAGG):
    """n 枚の面からの反射の干渉強度(正規化)。φ = 2π (2 d sinθ) / λ。"""
    phi = 2 * math.pi * 2 * d * math.sin(math.radians(theta_deg)) / lam
    s = math.sin(phi / 2)
    if abs(s) < 1e-12:
        return 1.0
    return (math.sin(n * phi / 2) / (n * s)) ** 2


def build_bragg(phase, ref_rows):
    a = phase["cell"][0]
    r200 = next(r for r in ref_rows if r["hkl"] == (2, 0, 0))
    d = r200["d"]
    orders = [r for r in ref_rows if r["hkl"] in ((2, 0, 0), (4, 0, 0), (6, 0, 0))]
    th_b = [r["tt"] / 2 for r in orders]
    Tn = 84
    th = sweep(4.0, 62.0, Tn, slow=[(x, 2.0, 0.22) for x in th_b])
    t = np.arange(Tn) / FPS
    # 面と原子(a/2 の市松)
    sn, sc = sphere(0.45, 4, 8), sphere(0.7, 4, 8)
    atoms_na, atoms_cl, slabs = [], [], []
    xs = np.arange(-5, 6) * a / 2
    for j in range(N_BRAGG):
        z = -j * d
        slabs.append((*box((0, 0, z), (30.0, 12.0, 0.12)), PLANE_RGB))
        for i, x in enumerate(xs):
            for yy, par in ((-a / 4, 0), (a / 4, 1)):
                (atoms_na if (i + par + j) % 2 == 0 else atoms_cl).append(np.array([x, yy, z]))
    bodies = [body("planes", merge(slabs), T("(200) の面 %d 枚、間隔 d = %.3f Å" % (N_BRAGG, d), "%d (200) planes, spacing d = %.3f Å" % (N_BRAGG, d)), 0.30),
              body("na", merge([(sn[0] + p, sn[1], NA_RGB) for p in atoms_na]), T("Na⁺", "Na⁺")),
              body("cl", merge([(sc[0] + p, sc[1], CL_RGB) for p in atoms_cl]), T("Cl⁻", "Cl⁻")),
              body("source", merge([(*box((-5, 0, 0), (10, 5, 5)), (0.35, 0.36, 0.45))]), T("X 線源(平行な光線)", "X-ray source (parallel rays)")),
              body("screen", merge([(*box((0.5, 0, 0), (1.0, 14, 14)), (0.18, 0.18, 0.20))]), T("受光面", "detector screen"))]
    B = len(bodies)
    xyz = np.zeros((Tn, B, 3))
    quat = np.zeros((Tn, B, 4))
    quat[..., 0] = 1.0
    clouds, recs = [], []
    A = np.array([0.0, 0.0, 0.0])
    for k in range(Tn):
        thr = math.radians(th[k])
        din = np.array([math.cos(thr), 0.0, -math.sin(thr)])
        dout = np.array([math.cos(thr), 0.0, math.sin(thr)])
        I = interference(th[k], d, LAM)
        xyz[k, 3] = A - RAY_L * din
        quat[k, 3] = q_dir_xz(din)
        xyz[k, 4] = A + DET_L * dout
        quat[k, 4] = q_dir_xz(dout)
        P, C = [], []
        glow = 0.30 + 0.70 * I
        for j in range(3):                                       # 面 0, 1, 2 で反射する 3 本
            Bp = A + np.array([0.0, 0.0, -j * d])
            q = line_pts(Bp - RAY_L * din, Bp, 44)
            P.append(q)
            C.append(np.tile((0.92, 0.92, 0.88), (len(q), 1)))
            q = line_pts(Bp, Bp + DET_L * dout, 52)[1:]
            P.append(q)
            C.append(np.tile(np.array([0.95, 0.95, 0.75]) * glow, (len(q), 1)))
        Bp = A + np.array([0.0, 0.0, -d])
        F1, F2 = Bp - d * math.sin(thr) * din, Bp + d * math.sin(thr) * dout
        for s_, e_ in ((F1, Bp), (Bp, F2)):
            q = line_pts(s_, e_, 10)
            P.append(q)
            C.append(np.tile((1.0, 0.55, 0.20), (len(q), 1)))
        # 受光面の光点(明るさ = 干渉強度)
        ang = np.linspace(0, 2 * np.pi, 16, endpoint=False)
        for rr in (0.0, 0.9, 1.8):
            spot = A + (DET_L - 0.2) * dout + rr * (np.cos(ang)[:, None] * np.array([0.0, 1.0, 0.0]) + np.sin(ang)[:, None] * np.cross(dout, [0.0, 1.0, 0.0]))
            P.append(spot)
            C.append(np.tile(np.array([1.0, 0.95, 0.55]) * (0.15 + 0.85 * I), (16, 1)))
        clouds.append({"k": k, "pos": np.concatenate(P), "rgb": np.clip(np.concatenate(C), 0, 1), "point_size": 0.28})
        delta = 2 * d * math.sin(thr)
        recs.append({"th": th[k], "I": I, "delta": delta, "n": delta / LAM, "d": d})
    th_curve = np.linspace(4, 62, 233)
    I_curve = np.array([interference(x, d, LAM) for x in th_curve])
    band = [band_frame(bragg_panels(r, orders, th_b, th_curve, I_curve), active_stage(k)) for k, r in enumerate(recs)]
    events = [{"t": 0.0, "label": T("θ を上げる", "raise θ")}]
    for r, name in zip(orders, ("1 (200)", "2 (400)", "3 (600)")):
        kb = int(np.argmax(th >= r["tt"] / 2))
        events.append({"t": float(t[kb]), "label": T("n = %s で輝く: θ = %.2f°" % (name, r["tt"] / 2), "bright at n = %s: θ = %.2f°" % (name, r["tt"] / 2))})
    series = [{"label": T("受光面の強度(%d 枚の干渉)" % N_BRAGG, "detector intensity (%d-plane interference)" % N_BRAGG),
               "values": np.array([r["I"] for r in recs]), "lo": 0, "hi": 1, "decimals": 3, "color": "#ffd54f"},
              {"label": T("行路差 / λ", "path difference / λ"), "values": np.array([r["n"] for r in recs]), "lo": 0, "hi": 3.5,
               "decimals": 3, "color": "#90caf9"}]
    axis = {"values": th, "segments": [{"k": 0, "label": T("X 線と面の角 θ", "angle θ between X-ray and planes"), "unit": "°", "decimals": 2}]}
    return {"t": t, "bodies": bodies, "xyz": xyz, "quat": quat, "clouds": clouds, "events": events, "series": series,
            "band": np.stack(band), "recs": recs, "axis": axis, "d": d, "orders": orders, "th_b": th_b}


def bragg_panels(r, orders, th_b, th_curve, I_curve):
    p1 = panel_text([("(200) planes x %d" % N_BRAGG, (0.9, 0.9, 0.9)), ("d = %.4f A" % r["d"], (1.0, 1.0, 1.0)),
                     ("lambda = %.4f A" % LAM, (0.75, 0.75, 0.75)), ("theta = %.2f deg" % r["th"], (1.0, 1.0, 1.0))])
    lines = [("powder_reflections", (0.55, 0.9, 0.6)), ("2theta (op):", (0.8, 0.8, 0.8))]
    for o in orders:
        lines.append(("  %s %.3f deg" % (hkl_s(o["hkl"]), o["tt"]), (0.9, 0.9, 0.9)))
    p2 = panel_text(lines)

    def plot(p):
        mini_plot(p, (32, 4, PH - 36, PW - 8), [(th_curve, I_curve, (0.95, 0.85, 0.5))], (4, 62), (0, 1.05),
                  cursor=(r["th"], r["I"], EST_RGB), guides=[(x, None, (0.5, 0.4, 0.3)) for x in th_b])
    p3 = panel_text([("path 2d sin th = %.3f A" % r["delta"], (0.9, 0.9, 0.9)), ("  = %.3f lambda  I = %.2f" % (r["n"], r["I"]), (1.0, 1.0, 1.0))], plot)
    near = min(range(3), key=lambda i: abs(th_b[i] - r["th"]))
    o = orders[near]
    tt_c = two_theta_closed(r["d"] / (near + 1), LAM)
    p4 = panel_text([("2d sin th = n lambda", EST_RGB), ("n = %d:" % (near + 1), (0.95, 0.95, 0.95)),
                     ("2th = 2 asin(n lam/2d)", EST_RGB), ("  = %.4f deg" % tt_c, (0.95, 0.95, 0.95)),
                     ("op %.4f  diff %s" % (o["tt"], _e(abs(o["tt"] - tt_c))), (0.6, 1.0, 0.6))])
    return [p1, p2, p3, p4]


# --------------------------------------------------------------------------- #
# タブ 3: 粉末とデバイ環(限界の回: λ を長くする)                                     #
# --------------------------------------------------------------------------- #
DET_D, DET_HALF = 30.0, 40.0      # 検出器の距離と半幅(任意の長さの単位)
N_GRAIN = 16
NA1, NA2, NB = 20, 30, 34
LAM_END = 7.0
TOL_DEG = 0.4
IMG = 128


def equivalents(hkl):
    """立方晶の等価な面の法線(置換と符号)。"""
    import itertools
    out = set()
    for perm in itertools.permutations(hkl):
        for sg in itertools.product((1, -1), repeat=3):
            v = tuple(p * s for p, s in zip(perm, sg))
            if any(v):
                out.add(v)
    return [np.array(v, float) / np.linalg.norm(v) for v in sorted(out)]


def detector_geometry(lam=LAM, n=IMG):
    """op(debye_ring_image)の検出器の幾何。3-D の検出器(距離 DET_D、半幅 DET_HALF)と同じ角度範囲。"""
    pix = 2 * DET_HALF / n
    return {"cx": n / 2 - 0.5, "cy": n / 2 - 0.5, "distance": DET_D, "pixel": pix, "wavelength": lam}


def spots_for(Rm, fam, lam, tol_deg=TOL_DEG):
    """向き Rm の結晶が、面の族 fam(各 (hkl) に法線の一覧と 2θ・明るさ)で検出器に作る点。"""
    kin = np.array([0.0, 0.0, 1.0])
    out = []
    for hkl, normals, tt, bright in fam:
        thb = math.radians(tt / 2)
        for n0 in normals:
            n = Rm @ n0
            s = float(np.dot(kin, n))
            if abs(math.degrees(math.asin(min(1.0, abs(s)))) - math.degrees(thb)) > tol_deg:
                continue
            kout = kin - 2 * s * n
            if kout[2] <= 0.05:
                continue
            P = kout * (DET_D / kout[2])
            if abs(P[0]) > DET_HALF or abs(P[1]) > DET_HALF:
                continue
            out.append((P, bright, hkl))
    return out


def live_rows(rr, f2_ref):
    """|F|² が Cu Kα の最大の 1e-9 倍を越える行だけ。op の extinct は残った中での相対判定なので、全部が禁制の
    λ(> 2d(111))では |F|² ≈ 4e-29 の (100) が 1 行「残る」—— それは数値ゼロとして数えない(絶対のしきい値)。"""
    return [r for r in rr if r["F2"] > 1e-9 * f2_ref]


def ring_points(tt, bright, n=72, lam_scale=1.0):
    r = DET_D * math.tan(math.radians(tt))
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    P = np.c_[r * np.cos(ang), r * np.sin(ang), np.full(n, DET_D - 0.5)]
    ok = (np.abs(P[:, 0]) <= DET_HALF) & (np.abs(P[:, 1]) <= DET_HALF)
    return P[ok]


def debye_image(phase, lam, counts):
    """op の検出器像(平方根で見やすく、uint8)。環が 1 本も無ければ op は ValueError で止まる → 真っ黒。"""
    try:
        im = L.debye_ring_image(phase, [1.0], detector_geometry(lam), shape=(IMG, IMG), size=900.0,
                                instrumental_fwhm=0.15, counts=counts, background=0.02, seed=0)
        img = np.asarray(im["image"], float)
        return (np.sqrt(np.clip(img / max(img.max(), 1e-9), 0, 1)) * 255).astype(np.uint8), img
    except ValueError:
        return np.zeros((IMG, IMG), np.uint8), None


def ring_profile(raw, lam, n_bins):
    """op の像の方位積分(azimuthal_integrate)。空の bin(NaN)は落とす。"""
    az = L.azimuthal_integrate(raw, detector_geometry(lam, IMG), n_bins=n_bins)
    x, y = np.asarray(az["two_theta"], float), np.asarray(az["intensity"], float)
    ok = np.isfinite(y)
    return x[ok], y[ok]


def build_powder(phase, ref_rows):
    Tn = NA1 + NA2 + NB
    t = np.arange(Tn) / FPS
    rng = np.random.default_rng(20261026)
    tt_edge = math.degrees(math.atan(DET_HALF * math.sqrt(2) / DET_D))
    allowed = [r for r in ref_rows if not r["ext"]]
    imax = max(r["I"] for r in allowed)
    fam = [(r["hkl"], equivalents(r["hkl"]), r["tt"], math.sqrt(r["I"] / imax)) for r in allowed if r["tt"] < tt_edge]
    f2_ref = max(r["F2"] for r in allowed)
    # 物体: 粒 N_GRAIN 個(前半は同じ向きで密に = 単結晶、後半はばらばら = 粉)・ビーム・検出器
    g = 1.6
    bodies = [body("grain%d" % i, merge([(*box((0, 0, 0), (g, g, g)), (0.86, 0.86, 0.90) if i % 2 else (0.72, 0.74, 0.82))]),
                   T("結晶の粒(16 個)", "crystal grains (16)") if i == 0 else None) for i in range(N_GRAIN)]
    bodies += [body("beam", merge([(*tube((0, 0, -46), (0, 0, -4), 0.35, 8), (0.95, 0.95, 0.88))]), T("入ってくる X 線", "incoming X-ray")),
               body("detector", merge([(*box((0, 0, DET_D), (2 * DET_HALF, 2 * DET_HALF, 0.6)), (0.14, 0.14, 0.17))]), T("検出器", "detector"))]
    B = len(bodies)
    xyz = np.zeros((Tn, B, 3))
    quat = np.zeros((Tn, B, 4))
    quat[..., 0] = 1.0
    # 粒の配置: 単結晶 = 4×2×2 の密な塊、粉 = 半径 6 の中にばらばら
    tight = np.array([[(i % 4) - 1.5, (i // 4 % 2) - 0.5, (i // 8) - 0.5] for i in range(N_GRAIN)]) * g * 1.05
    loose = rng.normal(size=(N_GRAIN, 3)) * 2.4
    q_single = q_random(rng)
    q_grain = [q_random(rng) for _ in range(N_GRAIN)]
    spots, clouds, recs = [], [], []
    n_orient = 0
    for k in range(Tn):
        phase_name = "A1" if k < NA1 else ("A2" if k < NA1 + NA2 else "B")
        if phase_name == "A1":
            q_single = q_mul(q_small(rng, 2.5), q_single)
            n_orient = 1
            Rs = [q_rot(q_single)]
            for i in range(N_GRAIN):
                xyz[k, i], quat[k, i] = tight[i], q_single
        else:
            u = ease((k - NA1) / 6.0)
            for i in range(N_GRAIN):
                q_grain[i] = q_mul(q_small(rng, 9.0), q_grain[i])
                xyz[k, i] = tight[i] + u * (loose[i] - tight[i])
                quat[k, i] = q_grain[i]
            Rs = [q_rot(q) for q in q_grain] + [q_rot(q_random(rng)) for _ in range(8)]
            if phase_name == "A2":
                n_orient += len(Rs)
        lam = LAM
        P, C = [], []
        hits = []
        if phase_name != "B":
            for Rm in Rs:
                hits += spots_for(Rm, fam, LAM)
            for Pp, bright, hkl in hits:
                spots.append((Pp, bright, hkl))
            if spots:
                sp = np.array([s[0] for s in spots])
                sp[:, 2] = DET_D - 0.5
                br = np.array([s[1] for s in spots])
                P.append(sp)
                C.append(np.c_[np.full(len(sp), 1.0), 0.55 + 0.45 * br, 0.25 + 0.5 * br])
            if phase_name == "A1":
                for Pp, bright, hkl in hits:                     # 単結晶の回: 回折した光線も描く
                    q = line_pts([0, 0, 0], Pp, 30)
                    P.append(q)
                    C.append(np.tile((1.0, 0.9, 0.5), (len(q), 1)))
            lam_rows = allowed
            n_rings = sum(1 for r in allowed if r["tt"] < tt_edge)
        else:
            lam = LAM + (LAM_END - LAM) * ease((k - NA1 - NA2) / (NB - 1))
            lam_rows = live_rows(rows(reflections(phase, lam, tmax=179.0, include_extinct=False)), f2_ref)
            im_ = max([r["I"] for r in lam_rows], default=1.0)
            n_rings = 0
            for r in lam_rows:
                if r["tt"] < tt_edge:
                    pts = ring_points(r["tt"], math.sqrt(r["I"] / im_))
                    if len(pts):
                        n_rings += 1
                        P.append(pts)
                        b = math.sqrt(r["I"] / im_)
                        C.append(np.tile((1.0, 0.55 + 0.45 * b, 0.25 + 0.5 * b), (len(pts), 1)))
        if not P:
            P.append(np.array([[0.0, 0.0, DET_D - 0.5]]))
            C.append(np.array([[0.14, 0.14, 0.17]]))
        clouds.append({"k": k, "pos": np.concatenate(P), "rgb": np.clip(np.concatenate(C), 0, 1), "point_size": 0.6})
        recs.append({"phase": phase_name, "lam": lam, "n_orient": n_orient, "n_spots": len(spots), "n_hits": len(hits),
                     "n_rings": n_rings, "rows": lam_rows})
    # 帯と op の検出器像(露光が溜まる → λ を振る)
    exposure_steps = 8
    lam_steps = sorted({round(r["lam"], 2) for r in recs if r["phase"] == "B"})
    lam_steps = [lam_steps[i] for i in np.linspace(0, len(lam_steps) - 1, 10).astype(int)]
    img_cache, prof_cache = {}, {}
    frames = []
    for k, r in enumerate(recs):
        if r["phase"] == "B":
            lam_k = min(lam_steps, key=lambda x: abs(x - r["lam"]))
            key = ("B", lam_k)
            cnt = 2.0e4
        else:
            step = max(1, int(math.ceil(exposure_steps * (k + 1) / (NA1 + NA2))))
            key = ("A", step)
            cnt = 2.0e4 * step / exposure_steps
            lam_k = LAM
        if key not in img_cache:
            img, raw = debye_image(phase, lam_k, cnt)
            img_cache[key] = img
            if raw is not None:
                prof_cache[key] = ring_profile(raw, lam_k, 160)
            else:
                prof_cache[key] = (np.linspace(0, tt_edge, 2), np.zeros(2))
        r["img_key"] = key
        frames.append(img_cache[key])
    # Cu Kα の像の方位積分 → 山の位置(op の経路 2)
    _img_full, raw_full = debye_image(phase, LAM, None)
    assert raw_full is not None
    px_, py_ = ring_profile(raw_full, LAM, 240)
    peaks = L.diffraction_peaks(px_, py_, min_snr=6.0)
    band = [band_frame(powder_panels(r, prof_cache[r["img_key"]], allowed, tt_edge, peaks), active_stage(k)) for k, r in enumerate(recs)]
    events = [{"t": 0.0, "label": T("単結晶 1 粒(全部の粒が同じ向き)", "single crystal (all grains aligned)")},
              {"t": float(t[NA1]), "label": T("粉: 粒の向きをばらばらに → 点が環へ", "powder: grains in random orientations → spots become rings")},
              {"t": float(t[NA1 + NA2]), "label": T("λ を長くする → 環が広がり、消える", "lengthen λ → rings grow and vanish")}]
    for r0 in ((1, 1, 1), (2, 0, 0), (2, 2, 0)):
        d0 = next(r["d"] for r in allowed if r["hkl"] == r0)
        kk = [k for k, r in enumerate(recs) if r["phase"] == "B" and r["lam"] > 2 * d0]
        if kk:
            events.append({"t": float(t[kk[0]]), "label": T("λ > 2d%s = %.2f Å: この面は消える" % (hkl_s(r0), 2 * d0), "λ > 2d%s = %.2f Å: this ring is gone" % (hkl_s(r0), 2 * d0))})
    series = [{"label": T("検出器の点の数(積算)", "spots on the detector (accumulated)"), "values": np.array([r["n_spots"] for r in recs], float),
               "lo": 0, "hi": max(r["n_spots"] for r in recs) * 1.05, "decimals": 0, "color": "#ffd54f"},
              {"label": T("検出器に写る環の数", "rings on the detector"), "values": np.array([r["n_rings"] for r in recs], float),
               "lo": 0, "hi": 8, "decimals": 0, "color": "#90caf9"}]
    axis = {"values": np.array([r["lam"] if r["phase"] == "B" else r["n_orient"] for r in recs], float),
            "segments": [{"k": 0, "label": T("結晶の向きの数 n", "number of crystal orientations n"), "unit": "", "decimals": 0},
                         {"k": NA1, "label": T("見た向きの数 n(積算)", "orientations seen n (accumulated)"), "unit": "", "decimals": 0},
                         {"k": NA1 + NA2, "label": T("波長 λ", "wavelength λ"), "unit": "Å", "decimals": 2}]}
    return {"t": t, "bodies": bodies, "xyz": xyz, "quat": quat, "clouds": clouds, "events": events, "series": series,
            "band": np.stack(band), "frames": np.stack(frames), "recs": recs, "axis": axis, "spots": spots, "fam": fam,
            "peaks": peaks, "tt_edge": tt_edge, "allowed": allowed}


def powder_panels(r, prof, allowed, tt_edge, peaks):
    if r["phase"] == "B":
        p1 = panel_text([("powder, all orientations", (0.9, 0.9, 0.9)), ("lambda = %.3f A" % r["lam"], (1.0, 1.0, 1.0)),
                         ("2 d(111) = %.3f A" % (2 * next(x["d"] for x in allowed if x["hkl"] == (1, 1, 1))), (0.75, 0.75, 0.75)),
                         ("rings seen: %d" % r["n_rings"], (0.9, 0.9, 0.9))])
    else:
        p1 = panel_text([("single crystal" if r["phase"] == "A1" else "powder (%d orient.)" % r["n_orient"], (0.9, 0.9, 0.9)),
                         ("lambda = %.4f A (Cu)" % r["lam"], (1.0, 1.0, 1.0)), ("hits now: %d" % r["n_hits"], (0.9, 0.9, 0.9)),
                         ("spots total: %d" % r["n_spots"], (0.9, 0.9, 0.9))])
    lines = [("powder_reflections", (0.55, 0.9, 0.6)), ("debye_ring_image", (0.55, 0.9, 0.6)), ("azimuthal_integrate", (0.55, 0.9, 0.6))]
    vis = [x for x in r["rows"] if x["tt"] < tt_edge]
    lines.append(("rings: %s" % " ".join("%d%d%d" % x["hkl"] for x in vis[:4]), (0.9, 0.9, 0.9)))
    lines.append(("no ring < %.0f deg" % tt_edge if not vis else "%d rings < %.0f deg" % (len(vis), tt_edge), (0.9, 0.9, 0.9) if vis else (1.0, 0.5, 0.4)))
    p2 = panel_text(lines)
    xs, ys = prof
    ymax = float(ys.max()) if ys.size and ys.max() > 0 else 1.0

    def plot(p):
        mini_plot(p, (20, 4, PH - 24, PW - 8), [(xs, ys / ymax, (0.95, 0.85, 0.5))], (0, tt_edge), (0, 1.05),
                  guides=[(x["tt"], None, (0.4, 0.35, 0.3)) for x in r["rows"] if x["tt"] < tt_edge])
    p3 = panel_text([("ring profile (op image)", (0.8, 0.8, 0.8))], plot)
    d111 = next(x["d"] for x in allowed if x["hkl"] == (1, 1, 1))
    s = r["lam"] / (2 * d111)
    l4 = [("2th = 2 asin(lam / 2d)", EST_RGB), ("(111): lam/2d = %.3f" % s, (0.95, 0.95, 0.95))]
    if s <= 1:
        tt_c = two_theta_closed(d111, r["lam"])
        op = next((x["tt"] for x in r["rows"] if x["hkl"] == (1, 1, 1)), float("nan"))
        l4 += [("theory 2th = %.3f deg" % tt_c, (0.95, 0.95, 0.95)), ("op     2th = %.3f deg" % op, (0.95, 0.95, 0.95)),
               ("diff = %s deg" % _e(abs(op - tt_c)), (0.6, 1.0, 0.6))]
    else:
        l4 += [("> 1: asin undefined", (1.0, 0.5, 0.4)), ("no reflection at all", (1.0, 0.5, 0.4)), ("(op: only |F|2 ~ 0 rows)", (1.0, 0.5, 0.4))]
    p4 = panel_text(l4)
    return [p1, p2, p3, p4]


# --------------------------------------------------------------------------- #
# タブ 4: 消滅則(8 原子の波を足す)                                                #
# --------------------------------------------------------------------------- #
EXT_FAMILIES = ((1, 0, 0), (1, 1, 0), (1, 1, 1), (2, 0, 0), (2, 1, 0), (2, 2, 0))
SEG4 = 12
WAVE_L, WAVE_N = 14.0, 40


def build_extinction(phase, ref_rows):
    a = phase["cell"][0]
    byhkl = {r["hkl"]: r for r in ref_rows}
    Tn = SEG4 * len(EXT_FAMILIES)
    t = np.arange(Tn) / FPS
    bodies = cell_bodies(a)
    sx = 1.75 * a
    for j in range(3):
        bodies.append(body("plane%d" % j, merge([(*slab(sx, sx, 0.03 * a), PLANE_RGB)]),
                           T("面 (hkl)(間隔 d)", "planes (hkl) (spacing d)") if j == 0 else None, PLANE_ALPHA))
    bodies.append(body("stage", merge([(*box((a / 2 + 2.0 + WAVE_L / 2, -0.4, a / 2 - 2.5), (WAVE_L + 1.5, 0.15, 2 * a + 12)), (0.16, 0.17, 0.20))]),
                       T("8 原子の波とその和(右)", "the 8 atom waves and their sum (right)")))
    B = len(bodies)
    xyz = np.zeros((Tn, B, 3))
    quat = np.zeros((Tn, B, 4))
    quat[..., 0] = 1.0
    f2max = max(r["F2"] for r in ref_rows)
    clouds, recs, events, axis_vals = [], [], [], np.zeros(Tn)
    x0 = a / 2 + 2.0 + 0.75
    xw = x0 + np.linspace(0, WAVE_L, WAVE_N)
    ztop = a / 2 + a + 2.0
    for fi, hkl in enumerate(EXT_FAMILIES):
        pos, nrm, d = plane_stack(hkl, a, 3)
        qn = q_align([0, 0, 1], nrm)
        r = byhkl[hkl]
        ph = atom_phases(hkl)
        s = 0.5 / d
        amp = {"Na": f0("Na1+", s), "Cl": f0("Cl1-", s)}
        amax = max(amp.values())
        f2c = F2_closed(hkl, d)
        events.append({"t": float(t[fi * SEG4]), "label": T("%s: %s" % (hkl_s(hkl), "混合パリティ → 消える" if not parity_allowed(hkl) else ("全部奇数 → 弱い" if hkl[0] % 2 else "全部偶数 → 強い")),
                                                        "%s: %s" % (hkl_s(hkl), "mixed parity → vanishes" if not parity_allowed(hkl) else ("all odd → weak" if hkl[0] % 2 else "all even → strong")))})
        for f in range(SEG4):
            k = fi * SEG4 + f
            axis_vals[k] = 100 * r["F2"] / f2max
            for j in range(3):
                xyz[k, 3 + j], quat[k, 3 + j] = pos[j], qn
            wt = 2 * math.pi * f / SEG4
            P, C = [], []
            total = np.zeros(WAVE_N)
            for j, (sp, phj) in enumerate(ph):
                A_ = 0.9 * amp[sp] / amax
                y = A_ * np.sin(2 * np.pi * (xw - x0) / 4.2 - wt + phj)
                total += (amp[sp] / amax) * np.sin(2 * np.pi * (xw - x0) / 4.2 - wt + phj)
                z = ztop - 2.0 * j
                P.append(np.c_[xw, y, np.full(WAVE_N, z)])
                C.append(np.tile(NA_RGB if sp == "Na" else CL_RGB, (WAVE_N, 1)))
            zs = ztop - 2.0 * 8 - 4.5
            P.append(np.c_[xw, total * 0.9, np.full(WAVE_N, zs)])
            C.append(np.tile(EST_RGB, (WAVE_N, 1)))
            P.append(np.c_[xw, np.zeros(WAVE_N), np.full(WAVE_N, zs)])
            C.append(np.tile((0.35, 0.35, 0.38), (WAVE_N, 1)))
            clouds.append({"k": k, "pos": np.concatenate(P), "rgb": np.clip(np.concatenate(C), 0, 1), "point_size": 0.22})
            recs.append({"hkl": hkl, "d": d, "row": r, "F2_closed": f2c, "amp": amp, "phases": ph, "sum_amp": float(np.max(np.abs(total)))})
    allowed = [r for r in ref_rows if not r["ext"]]
    imax = max(r["I"] for r in allowed)
    sticks_all = [(r["tt"], 100 * r["I"] / imax, (0.5, 0.5, 0.5)) for r in allowed]
    band = [band_frame(ext_panels(rc_, sticks_all, imax, f2max), active_stage(k)) for k, rc_ in enumerate(recs)]
    series = [{"label": T("|F|²(op、最大 = 100)", "|F|² (op, max = 100)"), "values": axis_vals, "lo": 0, "hi": 105, "unit": "%",
               "decimals": 1, "color": "#ffd54f"},
              {"label": T("和の波の振幅(相対)", "amplitude of the summed wave (relative)"), "values": np.array([r["sum_amp"] for r in recs]) / 4.0 / (1 + 1e-12),
               "lo": 0, "hi": 1.6, "decimals": 2, "color": "#90caf9"}]
    axis = {"values": axis_vals, "segments": [{"k": fi * SEG4, "label": T("%s の |F|²(最大 = 100)" % hkl_s(h), "|F|² of %s (max = 100)" % hkl_s(h)),
                                               "unit": "%", "decimals": 1} for fi, h in enumerate(EXT_FAMILIES)]}
    return {"t": t, "bodies": bodies, "xyz": xyz, "quat": quat, "clouds": clouds, "events": events, "series": series,
            "band": np.stack(band), "recs": recs, "axis": axis, "a": a}


def ext_panels(r, sticks_all, imax, f2max):
    hkl, row = r["hkl"], r["row"]
    par = "all even" if parity_allowed(hkl) and hkl[0] % 2 == 0 else ("all odd" if parity_allowed(hkl) else "mixed parity")
    p1 = panel_text([("Fm-3m: F-centred", (0.9, 0.9, 0.9)), ("hkl %s" % hkl_s(hkl), (1.0, 1.0, 1.0)), (par, (1.0, 1.0, 1.0)),
                     ("d = %.4f A" % r["d"], (0.75, 0.75, 0.75)), ("f_Na %.2f  f_Cl %.2f" % (r["amp"]["Na"], r["amp"]["Cl"]), (0.75, 0.75, 0.75))])
    p2 = panel_text([("powder_reflections", (0.55, 0.9, 0.6)), ("|F|2 = %.1f" % row["F2"], (1.0, 1.0, 1.0)),
                     ("rel = %.1f %%" % (100 * row["F2"] / f2max), (0.9, 0.9, 0.9)), ("extinct: %s" % ("yes" if row["ext"] else "no"), (1.0, 0.5, 0.4) if row["ext"] else (0.6, 1.0, 0.6)),
                     ("2theta = %.3f deg" % row["tt"], (0.75, 0.75, 0.75))])

    def plot(p):
        cur = [(row["tt"], 100 * row["I"] / imax if not row["ext"] else 100, EST_RGB if not row["ext"] else (1.0, 0.4, 0.3))]
        mini_plot(p, (20, 4, PH - 24, PW - 8), [], (10, 120), (0, 105), sticks=sticks_all + cur)
    p3 = panel_text([("sticks: op pattern" if not row["ext"] else "red = would be here", (0.8, 0.8, 0.8))], plot)
    if parity_allowed(hkl):
        sgn = "+" if hkl[0] % 2 == 0 else "-"
        l4 = [("F = 4 (f_Na %s f_Cl)" % sgn, EST_RGB), ("|F|2 e^-2Bs2 = %.1f" % r["F2_closed"], (0.95, 0.95, 0.95)),
              ("op  |F|2 = %.1f" % row["F2"], (0.95, 0.95, 0.95)), ("diff = %s" % _e(abs(row["F2"] - r["F2_closed"])), (0.6, 1.0, 0.6))]
    else:
        l4 = [("1 + e^(i pi(h+k))", EST_RGB), (" + e^(i pi(k+l)) + e^(i pi(h+l))", EST_RGB), ("= 0 (mixed parity)", (0.95, 0.95, 0.95)),
              ("op |F|2 = %s" % _e(row["F2"]), (0.6, 1.0, 0.6))]
    p4 = panel_text(l4)
    return [p1, p2, p3, p4]


# --------------------------------------------------------------------------- #
# 門(理論の線との差)と、ページの組み立て                                            #
# --------------------------------------------------------------------------- #
def run_all():
    phase = load_phase()
    ref = reflections(phase)
    rr = rows(ref)
    return {"phase": phase, "ref": ref, "rows": rr, "crystal": build_crystal(phase, rr), "bragg": build_bragg(phase, rr),
            "powder": build_powder(phase, rr), "ext": build_extinction(phase, rr)}


def gates(res) -> dict:
    """理論の線との差(門の値)。テストもこの関数の値を見る。"""
    g = {}
    ph, rr = res["phase"], res["rows"]
    a = ph["cell"][0]
    allowed = [r for r in rr if not r["ext"]]
    forbidden = [r for r in rr if r["ext"]]
    g["n_rows"], g["n_allowed"], g["n_forbidden"] = len(rr), len(allowed), len(forbidden)
    g["a"], g["density_op"] = a, float(ph["density"])
    g["two_theta_max_diff_deg"] = max(abs(r["tt"] - two_theta_closed(r["d"], LAM)) for r in rr)
    g["d_max_diff_A"] = max(abs(r["d"] - d_cubic(a, r["hkl"])) for r in rr)
    g["density_closed"] = density_closed(a)
    g["density_rel_diff"] = abs(ph["density"] - g["density_closed"]) / g["density_closed"]
    g["density_handbook"] = RHO_HANDBOOK
    g["density_vs_handbook_pct"] = 100 * abs(ph["density"] - RHO_HANDBOOK) / RHO_HANDBOOK
    # Bragg: n 枚の干渉の山(細かい掃引)が op の (200)(400)(600) の θ に立つ
    bg = res["bragg"]
    fine = np.linspace(4.0, 62.0, 58001)
    I = np.array([interference(x, bg["d"], LAM) for x in fine])
    peaks = []
    for thb in bg["th_b"]:
        win = (fine > thb - 3) & (fine < thb + 3)
        peaks.append(float(fine[win][int(np.argmax(I[win]))]))
    g["bragg_peak_vs_op_max_dig_deg"] = max(abs(p - thb) for p, thb in zip(peaks, bg["th_b"]))
    g["bragg_orders_two_theta"] = [o["tt"] for o in bg["orders"]]
    g["bragg_closed_orders_max_diff_deg"] = max(abs(o["tt"] - two_theta_closed(bg["d"] / (n + 1), LAM)) for n, o in enumerate(bg["orders"]))
    g["bragg_I_at_peaks_min"] = min(interference(thb, bg["d"], LAM) for thb in bg["th_b"])
    g["bragg_I_between_max"] = max(interference(x, bg["d"], LAM) for x in np.linspace(bg["th_b"][0] + 4.5, bg["th_b"][1] - 4.5, 400))
    # 粉末: 検出器の点の 2θ(幾何から)= その面の op の 2θ
    pw = res["powder"]
    devs = []
    for P, _b, hkl in pw["spots"]:
        tt_geom = math.degrees(math.atan(math.hypot(P[0], P[1]) / DET_D))
        tt_op = next(r["tt"] for r in rr if r["hkl"] == hkl)
        devs.append(abs(tt_geom - tt_op))
    g["n_spots"] = len(devs)
    g["spot_two_theta_max_dev_deg"] = max(devs) if devs else float("nan")
    pk = np.asarray(pw["peaks"]["two_theta"])
    g["n_image_peaks"] = int(len(pk))
    g["image_peak_vs_op_max_diff_deg"] = max(min(abs(p - r["tt"]) for r in allowed) for p in pk) if len(pk) else float("nan")
    g["rings_cu"] = sum(1 for r in allowed if r["tt"] < pw["tt_edge"])
    d111 = next(r["d"] for r in allowed if r["hkl"] == (1, 1, 1))
    g["two_d_111"] = 2 * d111
    g["lam_end"] = LAM_END
    end_rows = rows(reflections(ph, LAM_END, tmax=179.0, include_extinct=False))
    f2_ref = max(r["F2"] for r in allowed)
    g["rings_at_lam_end"] = len(live_rows(end_rows, f2_ref))
    g["op_rows_at_lam_end"] = len(end_rows)                       # op の一覧に残る行(相対しきい値の端の数値ゼロ)
    g["op_F2_at_lam_end"] = max((r["F2"] for r in end_rows), default=0.0)
    g["last_B_rings"] = pw["recs"][-1]["n_rings"]
    # 消滅則
    mixed = [r for r in rr if not parity_allowed(r["hkl"])]
    same = [r for r in rr if parity_allowed(r["hkl"])]
    g["n_mixed"], g["n_same"] = len(mixed), len(same)
    f2max = max(r["F2"] for r in rr)
    g["mixed_F2_max_rel"] = max(r["F2"] for r in mixed) / f2max
    g["same_F2_min_rel"] = min(r["F2"] for r in same) / f2max
    g["forbidden_is_exactly_mixed"] = all(r["ext"] == (not parity_allowed(r["hkl"])) for r in rr)
    g["F2_closed_max_rel_diff"] = max(abs(r["F2"] - F2_closed(r["hkl"], r["d"])) / f2max for r in rr)
    f111 = next(r["F2"] for r in rr if r["hkl"] == (1, 1, 1))
    f200 = next(r["F2"] for r in rr if r["hkl"] == (2, 0, 0))
    g["F2_111_over_200"] = f111 / f200
    return g


def _row(what_ja, what_en, criterion, result, ok):
    return {"what": T(what_ja, what_en), "criterion": criterion, "result": result, "ok": bool(ok)}


def salt_checks(g):
    return {
        "crystal": [
            _row("2θ: powder_reflections と 2 asin(λ/2d)(反射 %d 本、全部)" % g["n_rows"],
                 "2θ: powder_reflections vs 2 asin(λ/2d) (all %d reflections)" % g["n_rows"],
                 "< 1e-9 °", "%s °" % _e(g["two_theta_max_diff_deg"]), g["two_theta_max_diff_deg"] < 1e-9),
            _row("面間隔 d: op と a / √(h²+k²+l²)", "spacing d: op vs a / √(h²+k²+l²)",
                 "< 1e-12 Å", "%s Å" % _e(g["d_max_diff_A"]), g["d_max_diff_A"] < 1e-12),
            _row("密度: cif_read と Z M / (N_A a³)(原子量は手引書の値)", "density: cif_read vs Z M / (N_A a³) (handbook atomic masses)",
                 "< 1e-4", _e(g["density_rel_diff"]), g["density_rel_diff"] < 1e-4),
            _row("密度と手引書の値 %.2f g/cm³ の差" % RHO_HANDBOOK, "density vs the handbook value %.2f g/cm³" % RHO_HANDBOOK,
                 "< 1 %", "%.2f %%" % g["density_vs_handbook_pct"], g["density_vs_handbook_pct"] < 1.0)],
        "bragg": [
            _row("(200)(400)(600) の 2θ: op と 2 asin(nλ/2d)", "2θ of (200)(400)(600): op vs 2 asin(nλ/2d)",
                 "< 1e-9 °", "%s °" % _e(g["bragg_closed_orders_max_diff_deg"]), g["bragg_closed_orders_max_diff_deg"] < 1e-9),
            _row("%d 枚の干渉の山(0.001° 刻みの掃引)が op の θ に立つ" % N_BRAGG, "the %d-plane interference peaks (0.001° sweep) stand at the op's θ" % N_BRAGG,
                 "< 0.002 °", "%.4f °" % g["bragg_peak_vs_op_max_dig_deg"], g["bragg_peak_vs_op_max_dig_deg"] < 0.002),
            _row("山の頂の強度と、山の間(頂から 4.5° 以上離れた所)の最大", "intensity at the peaks vs the maximum between them (more than 4.5° from a peak)",
                 T("頂 > 0.999、間 < 0.1", "peaks > 0.999, between < 0.1"), "%.4f / %.4f" % (g["bragg_I_at_peaks_min"], g["bragg_I_between_max"]),
                 g["bragg_I_at_peaks_min"] > 0.999 and g["bragg_I_between_max"] < 0.1)],
        "powder": [
            _row("検出器の点 %d 個の 2θ(位置から)と、その面の op の 2θ(Bragg の許容 θ ± %.1f° の 2 倍)" % (g["n_spots"], TOL_DEG),
                 "2θ of the %d detector spots (from position) vs the op's 2θ of that plane (twice the Bragg tolerance θ ± %.1f°)" % (g["n_spots"], TOL_DEG),
                 "< %.1f °" % (2 * TOL_DEG), "%.3f °" % g["spot_two_theta_max_dev_deg"], g["spot_two_theta_max_dev_deg"] < 2 * TOL_DEG),
            _row("debye_ring_image → azimuthal_integrate → diffraction_peaks の山 %d 本と op の 2θ" % g["n_image_peaks"],
                 "%d peaks from debye_ring_image → azimuthal_integrate → diffraction_peaks vs the op's 2θ" % g["n_image_peaks"],
                 "< 0.2 °", "%.3f °" % g["image_peak_vs_op_max_diff_deg"], g["image_peak_vs_op_max_diff_deg"] < 0.2),
            _row("限界: λ = %.1f Å > 2d(111) = %.2f Å でも環が残るか" % (g["lam_end"], g["two_d_111"]),
                 "limit: does any ring survive at λ = %.1f Å > 2d(111) = %.2f Å?" % (g["lam_end"], g["two_d_111"]),
                 T("環 1 本以上", "1 ring or more"),
                 T("%d 本(op の一覧に残る %d 行は |F|² = %s の数値ゼロ)" % (g["rings_at_lam_end"], g["op_rows_at_lam_end"], _e(g["op_F2_at_lam_end"])),
                   "%d rings (the %d row left in the op's list has |F|² = %s, numerically zero)" % (g["rings_at_lam_end"], g["op_rows_at_lam_end"], _e(g["op_F2_at_lam_end"]))),
                 g["rings_at_lam_end"] >= 1)],
        "ext": [
            _row("混合パリティの面 %d 本の |F|²(op)" % g["n_mixed"], "|F|² (op) of the %d mixed-parity planes" % g["n_mixed"],
                 "< 1e-20 × max", _e(g["mixed_F2_max_rel"]), g["mixed_F2_max_rel"] < 1e-20),
            _row("消滅の印 = 混合パリティ(反射 %d 本、全部)" % g["n_rows"], "extinct flag = mixed parity (all %d reflections)" % g["n_rows"],
                 T("全部一致", "all match"), T("一致", "match") if g["forbidden_is_exactly_mixed"] else T("不一致", "mismatch"), g["forbidden_is_exactly_mixed"]),
            _row("|F|²: op と 4 (f_Na ± f_Cl) e^(−Bs²) の閉じた式", "|F|²: op vs the closed form 4 (f_Na ± f_Cl) e^(−Bs²)",
                 "< 1e-9 × max", _e(g["F2_closed_max_rel_diff"]), g["F2_closed_max_rel_diff"] < 1e-9)],
    }


def salt_lessons(g):
    return {
        "crystal": {
            "question": T("面間隔 d が小さい面ほど、X 線はどんな角度 2θ に出てくる?", "The smaller the spacing d of the planes, at what angle 2θ does the X-ray come out?"),
            "choices": [T("小さい角度", "A smaller angle"), T("大きい角度", "A larger angle"), T("d によらない", "It does not depend on d")],
            "answer": 1,
            "explain": T("sin θ = λ / 2d なので d が小さいほど θ が大きい。(111) は d = 3.245 Å で 2θ = 27.47°、(400) は d = 1.405 Å で 2θ = 66.49°(Cu Kα、op の値)。",
                         "sin θ = λ / 2d, so a smaller d gives a larger θ: (111) has d = 3.245 Å and 2θ = 27.47°, (400) has d = 1.405 Å and 2θ = 66.49° (Cu Kα, op values)."),
            "formula": T("d = a / √(h² + k² + l²)\n2θ = 2 asin(λ / 2d)\nρ = Z M / (N_A a³)、Z = 4", "d = a / √(h² + k² + l²)\n2θ = 2 asin(λ / 2d)\nρ = Z M / (N_A a³), Z = 4"),
            "limit": T("立方晶の面間隔は a と (hkl) だけで決まる。この CIF の a = 5.62 Å は 3 桁の値で、密度は手引書の 2.17 g/cm³ より 0.8 % 大きい。"
                       "同じ d の面(333 と 511 など)は粉末では同じ 2θ に重なり、区別できない。",
                       "In a cubic crystal the spacing depends only on a and (hkl). This CIF gives a = 5.62 Å to 3 digits, so the density comes out 0.8 % above the handbook 2.17 g/cm³. "
                       "Planes with the same d (333 and 511, for example) fall on the same 2θ in a powder and cannot be told apart."),
        },
        "bragg": {
            "question": T("結晶に X 線を当て、面との角 θ を上げていく。はね返った光は?", "Shine X-rays on the crystal and raise the angle θ to the planes. The reflected light…"),
            "choices": [T("どの角度でも同じ強さ", "Is equally strong at every angle"), T("決まった角度でだけ強く光る", "Is bright only at particular angles"),
                        T("角度が大きいほど強い", "Gets stronger as the angle grows")],
            "answer": 1,
            "explain": T("隣の面から戻る光の行路差は 2d sinθ。これが λ の整数倍の角度でだけ波の山が重なり、%d 枚ぶんが足し合って強く光る((200) は θ = %.2f°、(400) は %.2f°)。"
                         "それ以外の角度では打ち消し合って暗い。" % (N_BRAGG, g["bragg_orders_two_theta"][0] / 2, g["bragg_orders_two_theta"][1] / 2),
                         "The path difference between neighbouring planes is 2d sinθ. Only where it is a whole number of wavelengths do the crests line up and all %d planes add up "
                         "((200) at θ = %.2f°, (400) at %.2f°); elsewhere they cancel and the detector stays dark." % (N_BRAGG, g["bragg_orders_two_theta"][0] / 2, g["bragg_orders_two_theta"][1] / 2)),
            "formula": T("2d sinθ = nλ\nI_N(θ) = [sin(Nφ/2) / (N sin(φ/2))]²、φ = 2π · 2d sinθ / λ", "2d sinθ = nλ\nI_N(θ) = [sin(Nφ/2) / (N sin(φ/2))]², φ = 2π · 2d sinθ / λ"),
            "limit": T("%d 枚の面の干渉として描いたので山には幅がある。実際の結晶は何千枚もの面を持ち、山は鋭い(Scherrer: 幅 ∝ 1/枚数)。"
                       "吸収と、面ごとの反射率の違い(構造因子)は入れていない。" % N_BRAGG,
                       "Drawn as the interference of %d planes, so the peaks have a width. A real crystal has thousands of planes and sharp peaks (Scherrer: width ∝ 1/number). "
                       "Absorption and the different reflectivity of each plane (structure factor) are not included." % N_BRAGG),
        },
        "powder": {
            "question": T("粉末の X 線の波長 λ を長くしていく。検出器の環は?", "Make the X-ray wavelength λ longer and longer. The rings on the detector…"),
            "choices": [T("小さくなる", "Shrink"), T("大きくなり、やがて 1 本ずつ消える", "Grow, then disappear one by one"), T("変わらない", "Stay the same")],
            "answer": 1,
            "explain": T("sin θ = λ / 2d なので λ が長いほど環は大きい。λ が 2d を越えた面は sin θ > 1 になり、どの角度にも環を作れない。"
                         "λ = %.1f Å > 2d(111) = %.2f Å では残る面が 1 つも無い(限界の回。op の一覧には禁制の (100) が |F|² = %s の数値ゼロで 1 行残る —— 消滅の判定が残った中での相対値だから)。" % (g["lam_end"], g["two_d_111"], _e(g["op_F2_at_lam_end"])),
                         "sin θ = λ / 2d, so a longer λ makes larger rings. Once λ exceeds 2d for a plane, sin θ > 1 and that plane cannot diffract at any angle. "
                         "At λ = %.1f Å > 2d(111) = %.2f Å no plane is left (the limit tab; the op's list still holds one row, the forbidden (100) with |F|² = %s, numerically zero — its extinction test is relative to what remains)." % (g["lam_end"], g["two_d_111"], _e(g["op_F2_at_lam_end"]))),
            "formula": T("単結晶: 条件を満たす向きの面だけが点を作る\n粉末 = 全部の向き → 点が半頂角 2θ の円錐 = 環\n環の半径 r = D tan 2θ、λ > 2d なら環なし",
                         "single crystal: only planes in the right orientation make a spot\npowder = every orientation → spots fill a cone of half-angle 2θ = a ring\nring radius r = D tan 2θ; no ring if λ > 2d"),
            "limit": T("粒の向きの偏り(選択配向)があると環の明るさが方位で変わるが、ここでは一様とした。環の幅は結晶子の大きさ(Scherrer)と装置で決まり、"
                       "debye_ring_image の像は結晶子 900 Å・装置の幅 0.15° の設定。吸収は入れていない。",
                       "If the grains prefer some orientations (texture) the ring brightness varies around the ring; here they are uniform. The ring width comes from the crystallite size (Scherrer) "
                       "and the instrument; the debye_ring_image frames use 900 Å crystallites and a 0.15° instrumental width. Absorption is not included."),
        },
        "ext": {
            "question": T("面 (100) は結晶の中にちゃんとある。粉末パターンに (100) の山は出る?", "The (100) planes certainly exist in the crystal. Does the powder pattern show a (100) peak?"),
            "choices": [T("出る(面があるから)", "Yes (the planes are there)"), T("出ない(間の面が打ち消す)", "No (the plane halfway between cancels it)"),
                        T("弱く出る", "Yes, but weakly")],
            "answer": 1,
            "explain": T("面心格子では (100) の面と面の真ん中に同じ中身の面があり、そこからの波はちょうど半波長ずれて打ち消す。h, k, l が混合パリティの面は全部 0。"
                         "全部奇数の面は Na と Cl の波が逆向きで f_Na − f_Cl だけ残り弱い((111)/(200) の |F|² の比 = %.3f)。全部偶数は f_Na + f_Cl で強い。" % g["F2_111_over_200"],
                         "In a face-centred lattice an identical plane sits exactly halfway between the (100) planes; its wave is half a wavelength out of step and cancels. Every plane with mixed-parity h, k, l gives 0. "
                         "All-odd planes leave only f_Na − f_Cl (the Na and Cl waves oppose) and are weak (|F|² ratio (111)/(200) = %.3f); all-even planes add f_Na + f_Cl and are strong." % g["F2_111_over_200"]),
            "formula": T("F(hkl) = Σ_j f_j e^(2πi (h x_j + k y_j + l z_j))\nFm-3m: F = 4 (f_Na + f_Cl)(全偶)、4 (f_Na − f_Cl)(全奇)、0(混合)\n強度 ∝ m |F|² / (sin²θ cosθ)",
                         "F(hkl) = Σ_j f_j e^(2πi (h x_j + k y_j + l z_j))\nFm-3m: F = 4 (f_Na + f_Cl) (all even), 4 (f_Na − f_Cl) (all odd), 0 (mixed)\nintensity ∝ m |F|² / (sin²θ cosθ)"),
            "limit": T("強度は構造因子 |F|² と Lorentz 因子の近似で、吸収・偏光・結晶子の大きさ(Scherrer)・異常分散は入れていない。"
                       "散乱因子はイオン(Na⁺、Cl⁻)の 5 ガウス近似、変位は CIF に無いので B = 0.5 Å² と置いた。",
                       "Intensities use the structure factor |F|² and the Lorentz factor only: absorption, polarisation, crystallite size (Scherrer) and anomalous dispersion are left out. "
                       "The scattering factors are the 5-Gaussian fit for the ions (Na⁺, Cl⁻), and the displacement is set to B = 0.5 Å² because the CIF has none."),
        },
    }


def _tab(tab_id, label, badge, text, d, numbers, view, extra_panes=()):
    panes = [{"label": T("Fullseye の処理の帯(結晶 → op → パターン → 理論との差。いま効いている段を色で強調)",
                         "Fullseye processing band (crystal → op → pattern → theory vs op; the active stage is highlighted)"),
              "frames": d["band"], "png": True}] + list(extra_panes)
    return pv.viewer_anim3d_tab(tab_id, label, badge, text, d["t"], d["bodies"], d["xyz"], d["quat"], clouds=d["clouds"],
                                events=d["events"], series=d["series"], panes=panes, numbers=numbers, view=view)


def build_spec(res, g):
    N = pv.viewer_number
    cr, bg, pw, ex = res["crystal"], res["bragg"], res["powder"], res["ext"]
    tab1 = _tab(
        "crystal", T("結晶と格子面", "The crystal and its lattice planes"), "passed",
        T("塩(NaCl)の単位胞: 一辺 a = %.3f Å の立方体に Na⁺(紫、小)と Cl⁻(緑、大)が交互に並ぶ。結晶構造は CIF(COD 1000041)を cif_read で読んだもの。"
          "X 線が「反射」する格子面 (hkl) を半透明の板で重ね、(111) → (200) → (220) → (311) → (222) → (400) と順に切り替える。"
          "面の間隔 d = a / √(h²+k²+l²) は指数が大きいほど狭く、白い球が面から次の面へ渡る距離がそれ。"
          "帯には powder_reflections が出した d と 2θ、そして棒図(粉末パターン)のどの山がいまの面かを示す。"
          "(111) の面は Na だけを通り、Cl の面がその真ん中にある —— これが (111) の山が弱い理由(消滅則のタブ)。" % cr["a"],
          "The unit cell of salt (NaCl): a cube of edge a = %.3f Å with Na⁺ (violet, small) and Cl⁻ (green, large) alternating. The structure comes from a CIF (COD 1000041) read by cif_read. "
          "The lattice planes (hkl) that 'reflect' the X-rays are drawn as translucent sheets, switching through (111) → (200) → (220) → (311) → (222) → (400). "
          "Their spacing d = a / √(h²+k²+l²) shrinks as the indices grow; the white ball travels exactly that distance from one plane to the next. "
          "The band shows the d and 2θ from powder_reflections and which stick of the powder pattern is the current plane. "
          "The (111) planes pass through Na only, with a Cl plane halfway between them — which is why the (111) peak is weak (extinction tab)." % cr["a"]),
        cr,
        [N(T("格子定数 a(cif_read)", "lattice constant a (cif_read)"), "%.3f Å" % g["a"]),
         N(T("密度: op / Z M/(N_A a³) / 手引書", "density: op / Z M/(N_A a³) / handbook"), "%.4f / %.4f / %.2f g/cm³" % (g["density_op"], g["density_closed"], g["density_handbook"])),
         N(T("2θ: op と閉形式の差(反射 %d 本)" % g["n_rows"], "2θ: op vs closed form (%d reflections)" % g["n_rows"]), "%s °" % _e(g["two_theta_max_diff_deg"]))],
        {"az": 0.7, "el": 0.30, "dist": 0.72})
    tab2 = _tab(
        "bragg", T("Bragg の幾何: 行路差が λ の整数倍の角度だけ", "Bragg geometry: only where the path difference is a whole number of λ"), "passed",
        T("(200) の面 %d 枚(間隔 d = %.3f Å)に、波長 λ = %.4f Å の平行な X 線を角 θ で当てる。隣の面で反射した光の行路差(橙)は 2d sinθ。"
          "θ を上げていくと、行路差が λ・2λ・3λ になる角度でだけ全部の面からの波の山が重なり、右の受光面が明るく光る。それ以外の角度では %d 枚の波が打ち消し合って暗い。"
          "光る角度 θ = %.2f°、%.2f°、%.2f° は powder_reflections の (200)(400)(600) の 2θ の半分と一致する(帯の 4 段目に差)。" % (N_BRAGG, bg["d"], LAM, N_BRAGG, bg["th_b"][0], bg["th_b"][1], bg["th_b"][2]),
          "Parallel X-rays of wavelength λ = %.4f Å hit %d (200) planes (spacing d = %.3f Å) at an angle θ. The extra path of the ray reflected by the next plane (orange) is 2d sinθ. "
          "As θ rises, only at the angles where that path is λ, 2λ or 3λ do the waves from all planes crest together and the detector on the right lights up; elsewhere the %d waves cancel and it stays dark. "
          "The bright angles θ = %.2f°, %.2f°, %.2f° are half the 2θ of (200)(400)(600) from powder_reflections (difference in the band's 4th stage)." % (LAM, N_BRAGG, bg["d"], N_BRAGG, bg["th_b"][0], bg["th_b"][1], bg["th_b"][2])),
        bg,
        [N(T("光る角度 θ(n = 1, 2, 3)", "bright angles θ (n = 1, 2, 3)"), "%.2f / %.2f / %.2f °" % tuple(bg["th_b"])),
         N(T("干渉の山と op の θ の差", "interference peaks vs the op's θ"), "%.4f °" % g["bragg_peak_vs_op_max_dig_deg"])],
        {"az": -1.5708, "el": 0.18, "dist": 0.62})
    tab3 = _tab(
        "powder", T("粉末とデバイ環(と、その限界)", "Powder and Debye rings (and their limit)"), "limit",
        T("X 線(白)が結晶に当たり、回折した光が奥の検出器に写る。最初は 16 個の粒が全部同じ向き = 単結晶 1 粒: Bragg の条件を満たす面がたまにしか無く、点がぱらぱらとしか写らない。"
          "次に粒の向きをばらばらにする = 粉末。あらゆる向きの面があるので、同じ 2θ の点が円周に並び、環(デバイ環)に育つ。環の半径は r = D tan 2θ。"
          "下の帯の 2 段目は op の経路: debye_ring_image が作った検出器像を azimuthal_integrate で 1 次元にし、diffraction_peaks の山を powder_reflections の 2θ と比べる。"
          "後半は波長 λ を %.2f Å から %.1f Å へ長くする。環は広がり、検出器の外へ出て、λ が 2d を越えた面から順に消える。λ = %.1f Å > 2d(111) = %.2f Å では 1 本も残らない(バッジの表の「外れた」の行)。"
          % (LAM, LAM_END, LAM_END, g["two_d_111"]),
          "X-rays (white) hit the crystal and the diffracted light lands on the detector behind. At first all 16 grains share one orientation = a single crystal: only now and then does a plane meet the Bragg condition, so only scattered spots appear. "
          "Then the grains are turned every which way = a powder. Every orientation is present, so spots of the same 2θ line up on a circle and grow into rings (Debye rings), of radius r = D tan 2θ. "
          "The band's 2nd stage is the op path: debye_ring_image renders the detector image, azimuthal_integrate folds it to one dimension, and diffraction_peaks' peaks are compared with the 2θ of powder_reflections. "
          "Then the wavelength λ grows from %.2f Å to %.1f Å. The rings expand, leave the detector, and vanish one by one once λ exceeds 2d for that plane. At λ = %.1f Å > 2d(111) = %.2f Å none is left (the 'outside' row of the badge's table)."
          % (LAM, LAM_END, LAM_END, g["two_d_111"])),
        pw,
        [N(T("Cu Kα で検出器に写る環の数", "rings on the detector at Cu Kα"), "%d" % g["rings_cu"]),
         N(T("点の 2θ(位置)と op の 2θ の最大の差", "spot 2θ (from position) vs op 2θ, max difference"), "%.3f °" % g["spot_two_theta_max_dev_deg"]),
         N(T("像の山(diffraction_peaks)と op の 2θ の差", "image peaks (diffraction_peaks) vs op 2θ"), "%.3f °" % g["image_peak_vs_op_max_diff_deg"]),
         N(T("限界: λ = %.1f Å で残る環" % LAM_END, "limit: rings left at λ = %.1f Å" % LAM_END), "%d" % g["last_B_rings"])],
        {"az": -1.5708, "el": -1.05, "dist": 0.78, "target": [0.0, 0.0, 8.0]},
        extra_panes=[{"label": T("debye_ring_image(op)の検出器像: 露光が溜まる → λ を振る", "detector image from debye_ring_image (op): exposure builds up → λ sweeps"),
                      "frames": pw["frames"], "png": True}])
    tab4 = _tab(
        "ext", T("消滅則: どの面が消えるか", "Extinction rule: which planes vanish"), "passed",
        T("右に単位胞の 8 原子(Na 4、紫 / Cl 4、緑)それぞれが散乱する波を 1 本ずつ描き、いちばん下に足し合わせた波(黄)を出す。各波の位相は 2π(hx + ky + lz)、振幅は散乱因子 f。"
          "(100)(110)(210) のような混合パリティの面では、面心格子の 4 つの Na が 2 本ずつ逆位相で打ち消し、Cl も同じで、和は 0 —— 面はあるのに山は出ない。"
          "全部奇数の (111) では Na の 4 本と Cl の 4 本が逆向きで、f_Na − f_Cl だけが残って弱い。全部偶数の (200)(220) は 8 本が同じ向きで f_Na + f_Cl、強い。"
          "帯の棒図は powder_reflections の粉末パターンで、赤い棒は「消えた面がもし出るならここ」。閉じた式 4 (f_Na ± f_Cl) と op の |F|² の差が 4 段目。",
          "On the right, each of the 8 atoms in the unit cell (4 Na, violet / 4 Cl, green) scatters its own wave, and the summed wave (yellow) is drawn at the bottom. Each wave has phase 2π(hx + ky + lz) and amplitude f, the scattering factor. "
          "For mixed-parity planes such as (100)(110)(210), the 4 Na of the face-centred lattice cancel in opposite-phase pairs, the Cl likewise, and the sum is 0 — the planes exist, yet no peak appears. "
          "For the all-odd (111), the 4 Na waves oppose the 4 Cl waves and only f_Na − f_Cl survives: weak. For the all-even (200)(220) all 8 waves agree, f_Na + f_Cl: strong. "
          "The sticks in the band are the powder pattern from powder_reflections; a red stick marks where a vanished plane would have been. The 4th stage compares the closed form 4 (f_Na ± f_Cl) with the op's |F|²."),
        ex,
        [N(T("混合パリティ %d 本の |F|²(最大比)" % g["n_mixed"], "|F|² of the %d mixed-parity planes (relative to max)" % g["n_mixed"]), _e(g["mixed_F2_max_rel"])),
         N(T("|F|² の比 (111) / (200)", "|F|² ratio (111) / (200)"), "%.3f" % g["F2_111_over_200"]),
         N(T("|F|²: op と閉じた式の差(最大比)", "|F|²: op vs closed form (relative to max)"), _e(g["F2_closed_max_rel_diff"]))],
        {"az": 1.25, "el": 0.22, "dist": 0.8})
    checks, lessons = salt_checks(g), salt_lessons(g)
    tabs = [tab1, tab2, tab3, tab4]
    for tb, d in zip(tabs, (cr, bg, pw, ex)):
        tb["checks"], tb["lesson"], tb["axis"] = checks[tb["id"]], lessons[tb["id"]], d["axis"]
    if tabs[0]["badge"] == "limit":
        raise AssertionError("限界の回を最初のタブにしない")
    return pv.viewer_spec(
        "salt_xrd_anim3d",
        T("塩の結晶の粉末 X 線回折 —— なぜその角度にだけ光るのか", "Powder X-ray diffraction of salt — why it shines only at those angles"),
        T("面間隔・角度・波長を動かすと、Bragg の式の答えが環になる —— 計算は fullseye の pxrd op", "Move the spacing, the angle and the wavelength and Bragg's law becomes a ring — computed by fullseye's pxrd ops"),
        T("各タブは ① 問い → ② 予想(選択肢を押すと答えが開く)→ ③ 再生(▶)→ ④ 式 → ⑤ 限界 の順。時間つまみの読みは面間隔・角度・波長などの物理量。"
          "下の帯の 4 段は順に光る(結晶 → op → パターン → 理論との差)。バッジを押すと、確かめた項目・基準・結果の表が開く。ドラッグで視点を回す。",
          "Each tab runs ① question → ② predict (tap a choice to reveal the answer) → ③ play (▶) → ④ equation → ⑤ limit. The time slider reads a physical quantity such as spacing, angle or wavelength. "
          "The four band stages light up in turn (crystal → op → pattern → theory vs op). Tap a badge to open what was checked, the criterion and the result. Drag to orbit."),
        tabs,
        credit=T("結晶構造: COD 1000041(塩化ナトリウム、Abrahams & Bernstein 1965)、CC0。数値はすべて fullseye の pxrd op の出力で、理論の線は op とは別に書いた閉じた式。",
                 "Crystal structure: COD 1000041 (sodium chloride, Abrahams & Bernstein 1965), CC0. All numbers are outputs of fullseye's pxrd ops; the theory lines are closed forms written independently of the ops."))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="書かずに、門の値の印字と HTML の生成だけ")
    ap.add_argument("--out", default=str(OUT_HTML))
    a = ap.parse_args(argv)
    res = run_all()
    g = gates(res)
    for k, v in g.items():
        print("%-36s %s" % (k, v))
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
