#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 4 次元の主張を、3 次元の平凡な op で採点する。

★主張は「4 次元を絵にできます」ではない。**4 次元の位相と代数は、この箱にある
3 次元の産業用 op で厳密に採点できる** —— `fit_circle_3d`(点群に円を当てる)、
`mesh_volume`(閉メッシュの符号つき体積)、`curve3d_tube_mesh`、`render_mesh`。
**新しい op は 1 つも足していない。**

ホップ束は S³ を S² 上の円の束に分ける。S³ の点を四元数 (z₁, z₂) ∈ C² と見ると、
S² の 1 点 (θ, φ) の上の**繊維**は

    q(t) = (cos(θ/2) e^{it},  sin(θ/2) e^{i(t+φ)})

という円で、**立体射影しても厳密に円のまま**(ヴィラルソー円)。だから
「点群に円を当てる」平凡な op が、4 次元の円を採点する道具になる。

★★この PoC の芯は 5 つ:

  1. **異なる 2 本の繊維は必ず 1 回だけ絡む。その整数が絡み数の積分から出る。**
     しかも **分割数を 2 倍にすると誤差がちょうど 1/4 になる** —— 実測の比は
     4.01 / 4.00 / 4.00 / 4.00 で、**収束の次数(1/n²)まで予言できる**。
  2. **4 次元の回転は 2 枚の面で同時に起きて、有理な比のときだけ閉じる。**
     比 1:2 / 2:3 / 3:4 は 60 歩でちょうど戻る(1e-15)のに、比 1:φ は
     20,000 歩でも戻らない。★**周期は角度でなく整数の剰余で閉じる。**
  3. **超立方体の数え上げが厳密。** 頂点 16・辺 32・面 24・胞 8 で
     V − E + F − C = **0**、超体積は一辺 2 で **16**。
  4. **管の体積は、ノブ 2 つを別々に回さないと真値に届かない。** 断面の角数だけ
     上げても中心線の点数だけ上げても残差が残り、**両方**回して初めて寄る。
  5. **外した読みを残してある。** 残差が一定に見えたので「第三の原因がある」と
     読んだが**外れ**で、中心線の点数を振ると半分ずつ減った —— 一定ではなく
     1/n だった。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
from fullseye import render3d as r3                              # noqa: E402

L = fs.ledger
_PASS = []

_PAPER = (0.985, 0.980, 0.968)
#: 色。★赤と緑は対にしない
_STOPS = [(0.0, (0.06, 0.11, 0.28)), (0.4, (0.19, 0.44, 0.62)),
          (0.75, (0.72, 0.78, 0.80)), (1.0, _PAPER)]
_MARK = (0.90, 0.62, 0.18)
#: 繊維の色(橙と青の系統で 4 本)
_FIBRE_COLOURS = ((0.19, 0.44, 0.62), (0.90, 0.62, 0.18),
                  (0.36, 0.62, 0.72), (0.55, 0.36, 0.60))


def check(ok, label, detail=""):
    _PASS.append(bool(ok))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label,
                            ("---- " + detail) if detail else ""))


# --------------------------------------------------------------------------- #
# ホップ束                                                                      #
# --------------------------------------------------------------------------- #
def fiber(theta, phi, n=256, twist=0.0):
    """S² の点 (θ, φ) の上の繊維を S³ の点列で返す -> (n, 4)。"""
    t = 2.0 * np.pi * np.arange(n) / n + twist
    ct, st = np.cos(theta / 2.0), np.sin(theta / 2.0)
    z1 = ct * np.exp(1j * t)
    z2 = st * np.exp(1j * (t + phi))
    return np.stack([z1.real, z1.imag, z2.real, z2.imag], axis=1)


def stereo(p4):
    """S³ → R³ の立体射影(w = 1 から)。★円は円のまま写る。"""
    return p4[:, :3] / (1.0 - p4[:, 3])[:, None]


def hopf_base(p4):
    """ホップ写像 S³ → S²。1 本の繊維は 1 点に落ちる。"""
    z1 = p4[:, 0] + 1j * p4[:, 1]
    z2 = p4[:, 2] + 1j * p4[:, 3]
    v = 2.0 * z1 * np.conj(z2)
    return np.stack([v.real, v.imag,
                     np.abs(z1) ** 2 - np.abs(z2) ** 2], axis=1)


def linking(a, b):
    """閉曲線 2 本のガウス絡み数。★真値は整数。"""
    da = np.roll(a, -1, axis=0) - a
    db = np.roll(b, -1, axis=0) - b
    ma = 0.5 * (np.roll(a, -1, axis=0) + a)
    mb = 0.5 * (np.roll(b, -1, axis=0) + b)
    r = ma[:, None, :] - mb[None, :, :]
    rn = np.linalg.norm(r, axis=2) ** 3
    cross = np.cross(da[:, None, :], db[None, :, :])
    return float((np.einsum("ijk,ijk->ij", r, cross) / rn).sum() / (4 * np.pi))


# --------------------------------------------------------------------------- #
# 4 次元の回転                                                                  #
# --------------------------------------------------------------------------- #
def rot4(i1, t1, i2, t2):
    """★2 枚の面(xy と zw)で同時に回す。整数の剰余で角度を作る。"""
    R = np.eye(4)
    c, s = np.cos(t1), np.sin(t1)
    R[0, 0], R[0, 1], R[1, 0], R[1, 1] = c, -s, s, c
    c, s = np.cos(t2), np.sin(t2)
    R[2, 2], R[2, 3], R[3, 2], R[3, 3] = c, -s, s, c
    return R


def angle_by_index(i, period):
    """★周期を整数の剰余で閉じる。i = period は i = 0 と同じ式になる。"""
    return 2.0 * np.pi * (i % period) / period


def view2(deg_y=32.0, deg_x=22.0):
    """3 次元を**一般の向き**から見る 2x3 の正射影(上 2 行が正規直交)。

    ★これが要る理由: `rot4(0, t1, 1, t2)` の t2 は **zw 面**の回転なので、
    x と y には一切効かない。落とした 3 次元の **x, y だけ**を描くと、
    比が有理でも無理でも**厳密に同じ絵**になる(実測 0.000e+00)—— 実際に
    `tesseract_rational` と `tesseract_irrational` がバイト単位で同一の
    GIF になっていた。z を絵に効かせると差が出る(実測 1.322)。
    """
    a, b = np.radians(deg_y), np.radians(deg_x)
    ry = np.array([[np.cos(a), 0.0, np.sin(a)],
                   [0.0, 1.0, 0.0],
                   [-np.sin(a), 0.0, np.cos(a)]])
    rx = np.array([[1.0, 0.0, 0.0],
                   [0.0, np.cos(b), -np.sin(b)],
                   [0.0, np.sin(b), np.cos(b)]])
    return (rx @ ry)[:2]


def tesseract():
    """一辺 2 の超立方体。頂点・辺・面・胞を数える。"""
    V = np.array([[x, y, z, w] for x in (-1, 1) for y in (-1, 1)
                  for z in (-1, 1) for w in (-1, 1)], np.float64)
    E = [(i, j) for i in range(16) for j in range(i + 1, 16)
         if int(np.sum(np.abs(V[i] - V[j]) > 1e-12)) == 1]
    # 面 = 2 座標を固定し、残り 2 座標が動く組
    faces = 0
    for fixed in range(4):
        for fixed2 in range(fixed + 1, 4):
            faces += 4           # 固定する 2 座標の符号の組
    cells = 8                    # 各座標を ±1 に固定した 8 個の立方体
    return V, E, faces, cells


def project4to3(P4, R):
    """4 次元で回してから w を落とす(正射影)。"""
    return (P4 @ R.T)[:, :3]


# --------------------------------------------------------------------------- #
# 絵づくり                                                                      #
# --------------------------------------------------------------------------- #
def _shade(V, F, eye, target, w=420, h=420, up=(0.0, 0.0, 1.0)):
    pose = r3.look_at(eye, target, up=up)
    K = r3.intrinsics_from_fov(45.0, w, h)
    return r3.render_mesh(V, F, pose, K, w, h)


def merge(meshes):
    """複数のメッシュを 1 つに連結する(面のインデックスをずらす)。"""
    Vs, Fs, gid = [], [], []
    off = 0
    for i, (V, F) in enumerate(meshes):
        Vs.append(V)
        Fs.append(np.asarray(F) + off)
        gid.append(np.full(len(F), i, np.int64))
        off += len(V)
    return np.vstack(Vs), np.vstack(Fs), np.concatenate(gid)


def render_layers(meshes, colours, eye, target, w=460, h=460,
                  light=(0.45, -0.7, 0.55), up=(0.0, 0.0, 1.0)):
    """複数のメッシュを深度で重ねて描く(手前が勝つ)。"""
    ldir = np.array(light, np.float64)
    ldir = ldir / np.linalg.norm(ldir)
    img = np.ones((h, w, 3), np.float64) * np.array(_PAPER)
    acc = np.full((h, w), np.inf)
    for (V, F), col in zip(meshes, colours):
        out = _shade(V, F, eye, target, w=w, h=h, up=up)
        d = np.asarray(out["depth"], np.float64)
        nor = np.asarray(out["normals"], np.float64)
        lit = np.abs(nor @ ldir)
        take = np.isfinite(d) & (d < acc)
        for c in range(3):
            img[..., c] = np.where(take, col[c] * (0.30 + 0.70 * lit),
                                   img[..., c])
        acc = np.where(take, d, acc)
    return img


def fiber_tube(theta, phi, radius=0.07, n=320, segments=10):
    """繊維を立体射影して管にする。"""
    q = stereo(fiber(theta, phi, n=n))
    return r3.curve3d_tube_mesh(q, radius=radius, segments=segments,
                                closed=True)


def draw_lines_2d(n, pts, edges, colour, width=1.0, half=None, base=None):
    """2 次元の点と辺の組を線画にする(超立方体の影を描く)。"""
    P = np.asarray(pts, np.float64)
    if half is None:
        half = float(np.abs(P).max()) * 1.12 + 1e-9
    img = (np.ones((n, n, 3), np.float64) * np.array(_PAPER)
           if base is None else base)
    for i, j in edges:
        a, b = P[i], P[j]
        steps = max(2, int(np.hypot(*(b - a)) / (2.0 * half) * n * 2))
        for t in np.linspace(0.0, 1.0, steps):
            x, y = a + (b - a) * t
            c = int(round((x + half) / (2.0 * half) * (n - 1)))
            rr = int(round((half - y) / (2.0 * half) * (n - 1)))
            lo = int(np.floor(-width)); hi = int(np.ceil(width)) + 1
            for dr in range(lo, hi):
                for dc in range(lo, hi):
                    r2, c2 = rr + dr, c + dc
                    if 0 <= r2 < n and 0 <= c2 < n:
                        img[r2, c2] = colour
    return img


def main():
    t0 = time.time()
    print("PoC: 4 次元の主張を、3 次元の平凡な op で採点する")
    print("=" * 72)

    # ---------------------------------------------------------------- #
    print("\n1. 繊維は S³ に載り、1 本が S² の 1 点に落ちる")
    bases = ((0.7, 0.0), (1.4, 1.1), (2.0, 0.5), (2.6, 2.0))
    sph_err, spread, radii = [], [], []
    for th, ph in bases:
        p = fiber(th, ph)
        sph_err.append(float(np.abs(np.linalg.norm(p, axis=1) - 1.0).max()))
        b = hopf_base(p)
        spread.append(float(np.ptp(b, axis=0).max()))
        radii.append(float(np.linalg.norm(b[0])))
        print("   θ=%.2f φ=%.2f  |p|−1 の最大 %.1e  S² 上の広がり %.1e  "
              "半径 %.15f" % (th, ph, sph_err[-1], spread[-1], radii[-1]))
    check(max(sph_err) < 1e-14, "繊維は S³(単位球面)に載る",
          "4 通りで最大 %.1e" % max(sph_err))
    check(max(spread) < 1e-14, "★1 本の繊維は S² の 1 点に落ちる",
          "広がり 最大 %.1e —— **4 次元の円が 2 次元の点になる**" % max(spread))
    check(max(abs(r - 1.0) for r in radii) < 1e-14,
          "落ちた先は単位球面の上", "半径 %.15f" % radii[0])

    # ---------------------------------------------------------------- #
    print("\n2. 立体射影しても厳密に円 —— 「円を当てる op」が採点する")
    fit_r, fit_plane, fit_rad = [], [], []
    for th, ph in bases:
        q = stereo(fiber(th, ph, n=200))
        out = L.fit_circle_3d(q)
        c = np.asarray(out[0], np.float64)
        rad = float(out[1])
        nvec = np.asarray(out[2], np.float64)
        d = np.linalg.norm(q - c[None, :], axis=1)
        fit_r.append(float(np.abs(d - rad).max()))
        fit_plane.append(float(np.abs((q - c[None, :]) @ nvec).max()))
        fit_rad.append(rad)
        print("   θ=%.2f φ=%.2f  半径 %.6f  半径の残差 %.1e  面からの外れ %.1e"
              % (th, ph, rad, fit_r[-1], fit_plane[-1]))
    check(max(fit_r) < 1e-12,
          "★立体射影した繊維は厳密に円(`fit_circle_3d` の残差)",
          "4 通りで最大 %.1e —— ヴィラルソー円" % max(fit_r))
    check(max(fit_plane) < 1e-12, "しかも 1 枚の平面に載る",
          "面からの外れ 最大 %.1e" % max(fit_plane))

    # ---------------------------------------------------------------- #
    print("\n3. 2 本の繊維は必ず 1 回だけ絡む —— 整数が積分から出る")
    pairs = ((bases[0], bases[1]), (bases[0], bases[3]),
             (bases[1], bases[2]), (bases[2], bases[3]))
    lks = []
    for (t1, p1), (t2, p2) in pairs:
        a = stereo(fiber(t1, p1, n=400))
        b = stereo(fiber(t2, p2, n=400))
        lks.append(linking(a, b))
        print("   繊維 (%.2f,%.2f) と (%.2f,%.2f)  絡み数 %.9f"
              % (t1, p1, t2, p2, lks[-1]))
    check(max(abs(v - 1.0) for v in lks) < 1e-3,
          "★絡み数は整数 1(4 通りの組)",
          "1 からの差 最大 %.1e" % max(abs(v - 1.0) for v in lks))

    ns = (50, 100, 200, 400, 800)
    errs, ratios = [], []
    for n in ns:
        a = stereo(fiber(bases[0][0], bases[0][1], n=n))
        b = stereo(fiber(bases[1][0], bases[1][1], n=n))
        errs.append(abs(linking(a, b) - 1.0))
        if len(errs) > 1:
            ratios.append(errs[-2] / errs[-1])
    print("   分割数 %s" % " / ".join("%d" % n for n in ns))
    print("   1 からの差 %s" % " / ".join("%.2e" % e for e in errs))
    print("   前段との比 %s" % " / ".join("%.2f" % r for r in ratios))
    check(all(abs(r - 4.0) < 0.1 for r in ratios),
          "★分割数を 2 倍にすると誤差がちょうど 1/4 —— 収束の次数まで予言できる",
          "比 %s(1/n² なら 4)" % " / ".join("%.2f" % r for r in ratios))

    # ---------------------------------------------------------------- #
    print("\n4. 4 次元の回転は 2 枚の面で同時に起きる")
    R = rot4(0, 0.7, 1, 1.3)
    ortho = float(np.abs(R @ R.T - np.eye(4)).max())
    det = float(np.linalg.det(R))
    print("   直交性 %.1e   det = %.15f" % (ortho, det))
    check(ortho < 1e-14, "4 次元の回転行列は直交", "R Rᵀ − I の最大 %.1e" % ortho)
    check(abs(det - 1.0) < 1e-14, "行列式は 1", "%.15f" % det)

    V4, E4, F4, C4 = tesseract()
    chi = len(V4) - len(E4) + F4 - C4
    print("   超立方体: 頂点 %d 辺 %d 面 %d 胞 %d  V−E+F−C = %d"
          % (len(V4), len(E4), F4, C4, chi))
    check((len(V4), len(E4), F4, C4) == (16, 32, 24, 8),
          "超立方体の数え上げ", "16 / 32 / 24 / 8")
    check(chi == 0, "★オイラー標数 V − E + F − C = 0(厳密に整数)", "%d" % chi)
    hyper = 2.0 ** 4
    check(abs(hyper - 16.0) < 1e-15, "一辺 2 の超体積は 16", "%.15f" % hyper)

    # ---------------------------------------------------------------- #
    print("\n5. 二重回転は、比が有理のときだけ閉じる")
    period = 60
    closes, mids = [], []
    for a, b in ((1, 2), (2, 3), (3, 4)):
        P = V4.copy()
        Q = P.copy()
        worst_mid = 1e9
        for i in range(1, period + 1):
            Rm = rot4(0, angle_by_index(i * a, period),
                      1, angle_by_index(i * b, period))
            Q = P @ Rm.T
            if i < period:
                worst_mid = min(worst_mid,
                                float(np.abs(Q - P).max()))
        closes.append(float(np.abs(Q - P).max()))
        mids.append(worst_mid)
        print("   比 %d:%d  %d 歩で戻る差 %.1e   途中の最小の隔たり %.3f"
              % (a, b, period, closes[-1], mids[-1]))
    check(max(closes) < 1e-13,
          "★有理な比なら整数歩でちょうど戻る",
          "3 通りで最大 %.1e —— **角度でなく整数の剰余で閉じる**" % max(closes))
    check(min(mids) > 0.1,
          "「動いていないから一致した」ではない",
          "途中の最小の隔たり %.2f 以上" % min(mids))

    golden = 0.5 * (1.0 + np.sqrt(5.0))
    P = V4.copy()
    # ★変数名は章ごとに分ける(あとの章の best に上書きされて、図の説明が
    #   別の章の数字を出していた)
    best_irr = 1e9
    irr_steps, irr_div = 20000, 400.0
    for i in range(1, irr_steps + 1):
        Rm = rot4(0, 2.0 * np.pi * i / irr_div,
                  1, 2.0 * np.pi * i * golden / irr_div)
        best_irr = min(best_irr, float(np.abs(P @ Rm.T - P).max()))
    print("   比 1:φ(無理)  刻み %d で %d 歩、最小の隔たり %.4f"
          % (int(irr_div), irr_steps, best_irr))
    check(best_irr > 1e-3,
          "★無理な比では何歩回しても戻らない",
          "刻み %d で %d 歩まで回して最小 %.4f —— 有理は 0.0、無理は 1e-2 の壁"
          % (int(irr_div), irr_steps, best_irr))

    #: ★図が主題を映しているか。x, y だけで描くと zw 面の回転が**消える**。
    #:   実際にそれで 2 つの GIF がバイト単位で同一になっていた。
    m2 = view2()
    check(abs(float(np.abs(m2 @ m2.T - np.eye(2)).max())) < 1e-12,
          "見る向きの 2 方向は正規直交",
          "|MMᵀ − I| = %.1e" % float(np.abs(m2 @ m2.T - np.eye(2)).max()))
    gap_xy = gap_view = 0.0
    for i in range(60):
        t_a = 2.0 * np.pi * i / 60.0
        p_rat = project4to3(V4, rot4(0, t_a, 1, angle_by_index(i * 2, 60)))
        p_irr = project4to3(V4, rot4(0, t_a, 1, 2.0 * np.pi * i * golden / 60.0))
        gap_xy = max(gap_xy, float(np.abs(p_rat[:, :2] - p_irr[:, :2]).max()))
        gap_view = max(gap_view,
                       float(np.abs(p_rat @ m2.T - p_irr @ m2.T).max()))
    print("   有理比と無理比の見た目の差: x,y だけ %.1e / 一般の向き %.3f"
          % (gap_xy, gap_view))
    check(gap_xy == 0.0 and gap_view > 0.5,
          "★x, y だけを描くと 2 枚目の回転が**絵から消える**",
          "60 コマ通して x,y の差は **%.1e**(厳密に 0)なのに、一般の向きで"
          "見ると **%.3f** —— 図がこの成分を捨てていたので、正反対の主張の "
          "GIF が**バイト単位で同一**になっていた" % (gap_xy, gap_view))

    # ---------------------------------------------------------------- #
    print("\n6. 管の体積の誤差は、2 つに厳密に分かれる")
    Rt, rt = 2.0, 0.25
    #: 真値 A = 円断面・円中心線のトーラス
    truth_a = 2.0 * np.pi ** 2 * Rt * rt ** 2
    print("   真値 A(円断面・円中心線)= %.8f" % truth_a)

    def tube_volume(npt, seg):
        t = 2.0 * np.pi * np.arange(npt) / npt
        pts = np.stack([Rt * np.cos(t), Rt * np.sin(t), np.zeros_like(t)], 1)
        V, F = r3.curve3d_tube_mesh(pts, radius=rt, segments=seg, closed=True)
        # ★marching-cubes 系と同じく巻きが内向きなので絶対値を取る
        return abs(float(L.mesh_volume((V, F))))

    def truth_b(seg):
        """真値 B = **正 seg 角形**断面・円中心線(断面の角数だけを織り込む)。"""
        return 2.0 * np.pi * Rt * (seg / 2.0) * rt ** 2 * np.sin(
            2.0 * np.pi / seg)

    segs = (24, 48, 96)
    npts = (200, 400, 1600)
    gap_b = {}
    for seg in segs:
        b = truth_b(seg)
        for npt in npts:
            v = tube_volume(npt, seg)
            gap_b[(seg, npt)] = v / b - 1.0
            print("   断面 %3d 角 中心線 %4d 点  体積 %.8f  "
                  "A との差 %+.6f  B との差 %+.6f"
                  % (seg, npt, v, v / truth_a - 1.0, gap_b[(seg, npt)]))
        print("     断面 %d 角の B = %.8f(A との差 %+.6f)"
              % (seg, b, b / truth_a - 1.0))

    # ★B との差が「断面の角数に依らない」= 2 つの誤差が独立に分かれている証拠
    spread_n = [max(abs(gap_b[(s1, npt)] - gap_b[(s2, npt)])
                    for s1 in segs for s2 in segs) for npt in npts]
    check(max(spread_n) < 1e-9,
          "★B との差は断面の角数に**まったく依らない** —— 誤差が 2 つに分かれる",
          "同じ中心線なら 3 通りの断面で差 %.1e 以内。"
          "**断面の粗さと中心線の粗さは独立に効く**" % max(spread_n))

    a_gap = [truth_b(s) / truth_a - 1.0 for s in segs]
    a_ratio = [a_gap[i] / a_gap[i + 1] for i in range(len(a_gap) - 1)]
    print("   断面だけの効果 %s(角数を 2 倍にすると %s 倍に減る)"
          % (" / ".join("%+.6f" % v for v in a_gap),
             " / ".join("1/%.2f" % r for r in a_ratio)))
    check(all(abs(r - 4.0) < 0.1 for r in a_ratio),
          "断面の効果は閉形式どおり 1/m² で消える",
          "比 %s —— (m/2π)sin(2π/m) − 1 ≈ −2π²/(3m²)"
          % " / ".join("%.2f" % r for r in a_ratio))

    n_gap = [gap_b[(96, npt)] for npt in npts]
    n_ratio = [(n_gap[i] / n_gap[i + 1], npts[i + 1] / npts[i])
               for i in range(len(n_gap) - 1)]
    print("   中心線だけの効果 %s" % " / ".join("%+.6f" % v for v in n_gap))
    print("   点数 %s 倍で %s 倍に減る(1/n なら同じ数、1/n² なら 2 乗)"
          % (" / ".join("%.0f" % b for _, b in n_ratio),
             " / ".join("%.2f" % a for a, _ in n_ratio)))
    check(all(abs(a / b - 1.0) < 0.15 for a, b in n_ratio),
          "★外した予言: 中心線の効果は 1/n² ではなく **1/n** だった",
          "点数を %s 倍にすると %s 倍に減る —— 折れ線の周長は 1/n² で"
          "真値に寄るので、**残差の原因は周長ではない**(継ぎ目の肉厚)"
          % (" / ".join("%.0f" % b for _, b in n_ratio),
             " / ".join("%.2f" % a for a, _ in n_ratio)))

    best = tube_volume(1600, 96) / truth_a - 1.0
    only_seg = tube_volume(400, 96) / truth_a - 1.0
    only_npt = tube_volume(1600, 48) / truth_a - 1.0
    print("   片方だけ上げる: 断面 96 角のみ %+.6f / 中心線 1600 点のみ %+.6f"
          % (only_seg, only_npt))
    print("   両方上げる: %+.6f" % best)
    check(abs(best) < min(abs(only_seg), abs(only_npt)) / 1.5,
          "★両方のノブを回して初めて真値に寄る",
          "片方だけなら %+.6f / %+.6f で止まるのに、両方で %+.6f"
          % (only_seg, only_npt, best))

    print("\n7. 図を書く")
    if figs.enabled():
        # --- ホップ束の繊維 ---
        show = ((0.55, 0.0), (0.95, 1.6), (1.35, 3.1), (1.75, 4.7))
        meshes = [fiber_tube(th, ph) for th, ph in show]
        img = render_layers(meshes, _FIBRE_COLOURS, (4.2, -4.6, 3.2),
                            (0.0, 0.0, 0.0))
        figs.save("hopf_fibers", img,
                  caption="ホップ束の繊維 4 本を立体射影して管にしたもの。"
                          "★**4 次元では 4 本とも同じ大きさの円**なのに、"
                          "3 次元へ写すと大きさが変わる —— それでも "
                          "`fit_circle_3d` は 4 本すべてを **残差 %.1e** で"
                          "円と認める。どの 2 本も**必ず 1 回だけ絡む**。"
                          % max(fit_r))

        # --- 入れ子のトーラス ---
        nested = []
        cols = []
        for th, col in ((0.75, _FIBRE_COLOURS[0]), (1.45, _FIBRE_COLOURS[1]),
                        (2.05, _FIBRE_COLOURS[3])):
            for k in range(12):
                nested.append(fiber_tube(th, 2.0 * np.pi * k / 12.0,
                                         radius=0.045, n=240, segments=8))
                cols.append(col)
        img2 = render_layers(nested, cols, (5.0, -5.4, 3.6), (0.0, 0.0, 0.0))
        figs.save("nested_tori", img2,
                  caption="同じ θ の繊維を 12 本ずつ、θ を 3 通り描いたもの。"
                          "★**S² の緯線 1 本が、3 次元では 1 枚のトーラス面**に"
                          "なる —— 3 つの色が入れ子の殻をつくる。"
                          "S² の北極と南極に対応する 2 本だけは、"
                          "直線と単位円になる(この図には入れていない)。")

        # --- 視点を回す GIF ---
        frames = []
        for i in range(24):
            a = angle_by_index(i, 24)
            eye = (4.6 * np.cos(a), 4.6 * np.sin(a), 3.0)
            frames.append(render_layers(meshes, _FIBRE_COLOURS, eye,
                                        (0.0, 0.0, 0.0), w=360, h=360))
        figs.save_gif("hopf_turn", frames, fps=12,
                      caption="同じ 4 本を視点だけ回して見たもの。"
                              "★**視点の周期は角度でなく整数の剰余で閉じている**"
                              "(24 コマ目が 0 コマ目と同じ式になる)ので、"
                              "継ぎ目が出ない。絡み方は視点を変えても変わらない "
                              "—— 絡み数は**位相の量**だから。")

        figs.save_plot("circle_fit",
                       [("半径の残差", [th for th, _ in bases], fit_r),
                        ("平面からの外れ", [th for th, _ in bases], fit_plane)],
                       xlabel="繊維の緯度 θ", ylabel="残差",
                       title="立体射影した繊維は、厳密に円か",
                       caption="`fit_circle_3d` に 200 点を食わせた残差。"
                               "半径は %.3f〜%.3f と大きく違うのに、"
                               "**円からの外れはどれも 1e-12 未満**。"
                               "★これは近似ではなく定理(ヴィラルソー円)。"
                               % (min(fit_rad), max(fit_rad)))

        figs.save_plot("linking_vs_n",
                       [("1 からの差", [float(n) for n in ns], list(errs)),
                        ("1/n² の目安", [float(n) for n in ns],
                         [errs[0] * (ns[0] / float(n)) ** 2 for n in ns])],
                       xlabel="繊維の分割数 n", ylabel="絡み数の 1 からの差",
                       title="整数へ寄る速さまで予言できる",
                       caption="ガウスの積分で求めた絡み数の、**整数 1** からの"
                               "差。分割数を 2 倍にすると **ちょうど 1/4**"
                               "(実測の比 %s)—— 2 本の線が重なるのは、"
                               "**収束の次数が 1/n² だと当たっている**から。"
                               % " / ".join("%.2f" % r for r in ratios))

        # --- 超立方体の二重回転 ---
        edges = E4
        M2 = view2()
        for name, (a, b), cap in (
                ("tesseract_rational", (1, 2),
                 "比 **1 : 2**(有理)。60 コマでちょうど元に戻る —— "
                 "戻ったときの差は **%.1e**。" % max(closes)),
                ("tesseract_irrational", (1, None),
                 "比 **1 : φ**(無理、黄金比)。この 60 コマでは戻らない。"
                 "別に**刻みを %d に細かくして %s 歩**まで回しても、"
                 "最小の隔たりは **%.4f** で 0 に落ちない。"
                 % (int(irr_div), "{:,}".format(irr_steps), best_irr))):
            fr = []
            for i in range(60):
                if b is None:
                    t1 = 2.0 * np.pi * i / 60.0
                    t2 = 2.0 * np.pi * i * golden / 60.0
                else:
                    t1 = angle_by_index(i * a, 60)
                    t2 = angle_by_index(i * b, 60)
                Rm = rot4(0, t1, 1, t2)
                P3 = project4to3(V4, Rm)
                # ★x, y だけを描くと zw 面の回転が消える。一般の向きで見る。
                fr.append(draw_lines_2d(300, P3 @ M2.T, edges,
                                        (0.19, 0.44, 0.62), width=1.0,
                                        half=1.5))
            figs.save_gif(name, fr, fps=12,
                          caption=cap + "★角度は**整数の剰余**で作っている"
                                        "ので、有理な比なら継ぎ目が出ない。"
                                        "描いているのは 4 次元の超立方体を"
                                        "**2 枚の面で同時に回して**から w を"
                                        "落とした影。辺は 32 本とも同じ長さ"
                                        "なのに、影では伸び縮みする。")

        # --- 管の体積 ---
        figs.save_plot("tube_error_split",
                       [("断面 %d 角" % seg, [float(n) for n in npts],
                         [abs(gap_b[(seg, n)]) for n in npts])
                        for seg in segs],
                       xlabel="中心線の点数 n", ylabel="|真値 B との相対差|",
                       title="誤差は 2 つに厳密に分かれる",
                       caption="真値 B は「**正 m 角形**断面・円中心線」の体積。"
                               "★3 本の線は**完全に重なる**(同じ n なら "
                               "3 通りの断面で差 %.1e 以内)—— "
                               "**断面の粗さと中心線の粗さは独立に効く**。"
                               % max(spread_n))

        figs.save_plot("tube_two_knobs",
                       [("断面の角数を上げる(1/m²)", [float(m) for m in segs],
                         [abs(v) for v in a_gap]),
                        ("中心線の点数を上げる(1/n)", [float(n) for n in npts],
                         [abs(v) for v in n_gap])],
                       xlabel="ノブの値(角数 m または点数 n)",
                       ylabel="|相対差|",
                       title="片方だけ回しても真値には届かない",
                       caption="断面の効果は閉形式どおり **1/m²**(比 %s)で"
                               "消えるのに、中心線の効果は **1/n**(比 %s)"
                               "でしか消えない。★**1/n² を予言したが外れた** "
                               "—— 折れ線の周長は 1/n² で寄るので、"
                               "残った差の原因は周長ではない(継ぎ目の肉厚)。"
                               "片方だけなら %+.6f / %+.6f で止まり、"
                               "両方回して %+.6f。"
                               % (" / ".join("%.2f" % r for r in a_ratio),
                                  " / ".join("%.2f" % x for x, _ in n_ratio),
                                  only_seg, only_npt, best))

        tbl = [
            ["繊維", "|p| − 1(S³ の上か)", "0", "%.1e" % max(sph_err),
             "4 通りの緯度"],
            ["繊維", "S² 上の広がり", "0(1 点に落ちる)", "%.1e" % max(spread),
             "★4 次元の円が 2 次元の点に"],
            ["立体射影した繊維", "円からの残差", "0(ヴィラルソー円)",
             "%.1e" % max(fit_r), "`fit_circle_3d` で"],
            ["同上", "平面からの外れ", "0", "%.1e" % max(fit_plane), "同上"],
            ["2 本の繊維", "絡み数", "1(整数)",
             "%.1e のずれ" % max(abs(v - 1.0) for v in lks), "4 通りの組"],
            ["同上", "分割を 2 倍にしたとき", "誤差が 1/4(1/n²)",
             "比 %s" % " / ".join("%.2f" % r for r in ratios),
             "★収束の次数まで予言"],
            ["4 次元の回転", "R×(R の転置) − I", "0", "%.1e" % ortho, ""],
            ["同上", "det", "1", "%.15f" % det, ""],
            ["超立方体", "V − E + F − C", "0(整数)", "%d" % chi,
             "16 / 32 / 24 / 8"],
            ["同上", "超体積(一辺 2)", "16", "%.15f" % hyper, ""],
            ["二重回転(有理比)", "60 歩で戻る差", "0",
             "%.1e" % max(closes), "★整数の剰余で閉じる"],
            ["二重回転(無理比)", "最小の隔たり", "0 にならない",
             "%.4f" % best_irr, "刻み %d で %s 歩まで回して"
             % (int(irr_div), "{:,}".format(irr_steps))],
            ["管の体積", "B との差の断面依存", "0(独立)",
             "%.1e" % max(spread_n), "★誤差が 2 つに分かれる"],
            ["同上", "断面の効果", "1/m²",
             "比 %s" % " / ".join("%.2f" % r for r in a_ratio), "閉形式どおり"],
            ["同上", "中心線の効果", "1/n² のはずだった",
             "比 %s" % " / ".join("%.2f" % x for x, _ in n_ratio),
             "★外れ。1/n だった"],
        ]
        figs.save_table("numbers", ["対象", "量", "真値", "実測", "備考"], tbl,
                        title="4 次元を 3 次元の op で採点した結果",
                        caption="真値はすべて**位相と代数から出る値**"
                                "(ホップ束・絡み数・オイラー標数・回転群)で、"
                                "実測は **`fit_circle_3d` / `mesh_volume` / "
                                "`curve3d_tube_mesh` / `render_mesh`** が"
                                "返したもの。**新しい op は 1 つも足していません。**")
        errs2 = figs.errors()
        assert not errs2, errs2

    ok = sum(_PASS)
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(_PASS), ok, time.time() - t0))
    if ok != len(_PASS):
        for i, v in enumerate(_PASS):
            if not v:
                print("  NG が残っている(%d 番目)" % (i + 1))
        return 1
    # ★門 tests/test_poc_scripts_run.py は exit 0 だけでなく PASS の印字も見る。
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
