#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""レンズ 1 枚から光学系へ —— 教科書の結像を動く 3-D に(2026-10-24)。

    py -3.11 tools/build_lens_system_anim3d.py            # docs/anim3d/textbook_lens_system.html を書く
    py -3.11 tools/build_lens_system_anim3d.py --check    # 書かずに、数字の印字と HTML の生成だけ
    py -3.11 tools/build_lens_system_anim3d.py --help

教科書の図は 1 枚の静止画だが、ここでは 1 つの量をゆっくり振り、像が連続に変わる様子を見せる。
4 タブ(1 タブ = 1 題材)。光線はすべて fullseye の実光線追跡(:func:`raytrace.trace_rays` /
``chief_ray`` / ``ray_bundle``)が実際に追った経路で、手で描いた線は無い。近軸の式(理論の線 = 門の値)
と並べ、差が開く所を「限界」の段として正直に見せる。

* **薄レンズの結像**(つまみ = 物体の位置 a): ``lens_system`` + ``paraxial_trace``(焦点距離と主点)→
  ``thin_lens``(1/a + 1/b = 1/f → 像の位置 b と倍率 m)→ ``trace_rays``(矢印の各点を実光線で運んだ
  スクリーンの像)→ 理論の線 b(a) と比べる。a が f を割ると像は虚像(正立・拡大、虫めがね)。
* **レンズメーカーの式**(つまみ = 曲率半径 R と材料): ``material_optical_constants``(材料ライブラリの
  屈折率)→ ``thick_lens``(厚肉レンズの閉形式)→ ``paraxial_trace`` → ``trace_rays``。理論の線は
  薄肉の 1/f = (n−1)(1/R1 − 1/R2)。強く曲げると薄肉の式から外れる(限界)。
* **2 枚組と ABCD 行列**(つまみ = 2 枚の間隔 d): ``abcd_matrix`` → ``abcd_trace`` → ``paraxial_trace``
  → ``trace_rays``。1/f = 1/f1 + 1/f2 − d/(f1 f2)。d = f1 + f2 で焦点距離が無限大(望遠鏡)。
  厚いレンズは**主点から測れば**薄レンズの式がそのまま使える(門は 1e-9 で一致)。
* **絞りと瞳**(つまみ = 画角 θ): ``paraxial_trace``(入射瞳・射出瞳)→ ``chief_ray`` → ``ray_bundle``
  (ケラレ)→ ``relative_illumination``(cos⁴ 則)。実光線から求めた周辺の明るさ(瞳の見かけの面積 ×
  像の面積の伸び)を cos⁴ と比べ、レンズの縁が光束を切る所から cos⁴ より暗くなる(限界)。

学習用の型(2026-10-25): 各タブは pocviewer の ``lesson``(① 問い → ② 予想 → ③ 再生 → ④ 式 → ⑤ 限界)、
時間つまみの読みは ``axis``(物体の位置 a・曲率半径 R と屈折率 n・主点の間隔 d・画角 θ)、バッジの表は ``checks``
(値は :func:`gates` の門の値、ok は基準との比較で決める)。ok:false の行がある回だけ badge を limit にし、限界の回は
最初に置かない。説明文の「限界:」の段は lesson の ⑤ 限界へ移す。8 言語版は
``py -3.11 tools/anim3d_i18n.py --build build_lens_system_anim3d --out docs/anim3d/textbook_lens_system.html``
で書く(この生成器を直接回すと ja/en だけになる)。

収差の題材(``feat/anim3d-textbook-aberrations``)と重ならないよう、ここは**結像の位置と大きさ・瞳**に
重心を置く。出典は一般的な教科書の式(Hecht『Optics』5 章・6 章、Born & Wolf 4 章、鶴田匡夫『応用光学』)。

``regen_all`` には入れない(build_agv_vision_anim3d と同じく ``pocviewer.write_viewer`` で書く手回しの生成物。
出力を変えたら手で回して commit する)。門は ``tests/test_lens_system_anim3d.py``。

呼び出し例(数字だけ欲しいとき)::

    import sys; sys.path.insert(0, "tools")
    import build_lens_system_anim3d as L
    rec = L.run_imaging()          # タブごとの記録(コマごとの op の値・理論値・光線)
    print(rec["b_thin"][:3], rec["b_para"][:3])
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import annotate  # noqa: E402
import materials  # noqa: E402
import optics  # noqa: E402
import pocviewer as pv  # noqa: E402
import raytrace as rt  # noqa: E402

T = pv.viewer_text
OUT_HTML = ROOT / "docs" / "anim3d" / "textbook_lens_system.html"
LANGS = ("ja", "en")
INF = float("inf")
WL_UM = rt.WL_D                                   # d 線(587.56 nm)。材料の屈折率もこの波長で引く
WL_NM = WL_UM * 1000.0

FPS = 15.0
NF = 88                                           # 1 タブのコマ数(約 6 秒。HTML を 3 MB 以内に)
STAGE_RGB = ((0.31, 0.76, 0.97), (1.00, 0.72, 0.30), (0.51, 0.78, 0.52), (1.00, 0.84, 0.31))
STAGE_HEX = ("#4fc3f7", "#ffb74d", "#81c784", "#ffd54f")
GREY = (150, 150, 150)
BLOCK = (229, 115, 115)

# 光学台(全タブ共通): 光軸は z = 0、台の上面は z = -24 mm。使わない部品はここへしまう(台の中は見えない)
BENCH_TOP, BENCH_BOT, BENCH_W = -24.0, -40.0, 13.5
PARK_Z = 0.5 * (BENCH_TOP + BENCH_BOT)
BOX = 50.0                                         # 光線を描く箱(光軸からの横・上下 mm)


def U8(c):
    return [int(round(255 * v)) for v in c]


# =========================================================================== #
# 形(メッシュ)                                                               #
# =========================================================================== #
def _sag(R, r):
    """球面のサグ(面の頂点から光軸方向へのずれ、mm)。R = inf は平面。"""
    if not math.isfinite(R):
        return np.zeros_like(np.asarray(r, float))
    return R - np.sign(R) * np.sqrt(np.maximum(R * R - np.asarray(r, float) ** 2, 0.0))


def lens_mesh(R1, R2, t, ap, n_ang=16, n_rad=3):
    """球面レンズ(光軸 = 局所 x、前の頂点が x = 0)。面ごと・縁で頂点を分けて陰影をにじませない。"""
    a = np.linspace(0, 2 * np.pi, n_ang, endpoint=False)
    rs = np.linspace(0, ap, n_rad + 1)[1:]
    pos, tri = [], []

    def face(xfun, flip):
        k0 = len(pos)
        pos.append([xfun(0.0), 0.0, 0.0])
        for r in rs:
            for th in a:
                pos.append([xfun(r), r * math.cos(th), r * math.sin(th)])
        for i in range(n_ang):
            j = (i + 1) % n_ang
            tr_ = [k0, k0 + 1 + i, k0 + 1 + j]
            tri.append(tr_[::-1] if flip else tr_)
        for ri in range(n_rad - 1):
            b0, b1 = k0 + 1 + ri * n_ang, k0 + 1 + (ri + 1) * n_ang
            for i in range(n_ang):
                j = (i + 1) % n_ang
                q = [[b0 + i, b1 + i, b1 + j], [b0 + i, b1 + j, b0 + j]]
                tri.extend([x[::-1] for x in q] if flip else q)
    face(lambda r: float(_sag(R1, r)), False)
    face(lambda r: t + float(_sag(R2, r)), True)
    x1, x2 = float(_sag(R1, ap)), t + float(_sag(R2, ap))
    k0 = len(pos)
    for th in a:
        pos.append([x1, ap * math.cos(th), ap * math.sin(th)])
        pos.append([x2, ap * math.cos(th), ap * math.sin(th)])
    for i in range(n_ang):
        j = (i + 1) % n_ang
        tri += [[k0 + 2 * i, k0 + 2 * j, k0 + 2 * j + 1], [k0 + 2 * i, k0 + 2 * j + 1, k0 + 2 * i + 1]]
    return np.array(pos, float), np.array(tri, int)


def prism_mesh(L, r, n=6):
    """光線の棒: 局所 x の 0..L に沿った細い n 角柱(側面だけ)。"""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring = np.column_stack([np.cos(a), np.sin(a)]) * r
    pos = np.vstack([np.column_stack([np.zeros(n), ring]), np.column_stack([np.full(n, L), ring])])
    tri = []
    for i in range(n):
        j = (i + 1) % n
        tri += [[i, j, n + j], [i, n + j, n + i]]
    return pos, np.array(tri)


def box_mesh(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    c = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    pos, tri = [], []
    for q in quads:
        k = len(pos)
        pos += [c[i] for i in q]
        tri += [[k, k + 1, k + 2], [k, k + 2, k + 3]]
    return np.array(pos), np.array(tri)


def cylinder_z(r, z0, z1, n=14):
    """局所 z に沿った円柱(支柱)。"""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring = np.column_stack([r * np.cos(a), r * np.sin(a)])
    pos = np.vstack([np.column_stack([ring, np.full(n, z0)]), np.column_stack([ring, np.full(n, z1)])])
    tri = [[i, (i + 1) % n, n + (i + 1) % n] for i in range(n)] + [[i, n + (i + 1) % n, n + i] for i in range(n)]
    return pos, np.array(tri)


def cone_z(r, h, n=14):
    """矢印の頭: 先端が局所の原点、底面が z = -h(上向きの矢印の頭)。"""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pos = [[0.0, 0.0, 0.0]] + [[r * math.cos(x), r * math.sin(x), -h] for x in a] + [[0.0, 0.0, -h]]
    tri = [[0, 1 + (i + 1) % n, 1 + i] for i in range(n)] + [[n + 1, 1 + i, 1 + (i + 1) % n] for i in range(n)]
    return np.array(pos, float), np.array(tri)


def sphere_mesh(r, n_lat=7, n_lon=12):
    pos = [[0, 0, r]]
    for i in range(1, n_lat):
        th = math.pi * i / n_lat
        for j in range(n_lon):
            ph = 2 * math.pi * j / n_lon
            pos.append([r * math.sin(th) * math.cos(ph), r * math.sin(th) * math.sin(ph), r * math.cos(th)])
    pos.append([0, 0, -r])
    tri, last = [], len(pos) - 1
    for j in range(n_lon):
        tri.append([0, 1 + j, 1 + (j + 1) % n_lon])
    for i in range(n_lat - 2):
        b0, b1 = 1 + i * n_lon, 1 + (i + 1) * n_lon
        for j in range(n_lon):
            k = (j + 1) % n_lon
            tri += [[b0 + j, b1 + j, b1 + k], [b0 + j, b1 + k, b0 + k]]
    b0 = 1 + (n_lat - 2) * n_lon
    for j in range(n_lon):
        tri.append([last, b0 + (j + 1) % n_lon, b0 + j])
    return np.array(pos, float), np.array(tri)


def ring_x(r_in, r_out, w, n=32):
    """光軸(局所 x)に垂直な輪(絞りの羽根・瞳の目印)。厚さ w。"""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pos, tri = [], []
    for x in (-w / 2, w / 2):
        for r in (r_in, r_out):
            pos += [[x, r * math.cos(th), r * math.sin(th)] for th in a]
    pos = np.array(pos, float)
    # 層: 0 = 前の内, 1 = 前の外, 2 = 後の内, 3 = 後の外
    def quad(l0, l1, flip=False):
        for i in range(n):
            j = (i + 1) % n
            q = [[l0 * n + i, l1 * n + i, l1 * n + j], [l0 * n + i, l1 * n + j, l0 * n + j]]
            tri.extend([x[::-1] for x in q] if flip else q)
    quad(0, 1)
    quad(2, 3, True)
    quad(1, 3)
    quad(0, 2, True)
    return pos, np.array(tri)


# =========================================================================== #
# 四元数 (w, x, y, z)                                                         #
# =========================================================================== #
Q0 = np.array([1.0, 0.0, 0.0, 0.0])
Q_FLIP_X = np.array([0.0, 1.0, 0.0, 0.0])         # x 軸まわり 180°(下向きの矢印の頭)
Q_FLAT = np.array([math.sqrt(0.5), 0.0, -math.sqrt(0.5), 0.0])   # 局所 x を上(z)へ: レンズを寝かせて台の中へしまう


def q_from_x(d):
    """局所 +x を単位ベクトル d へ向ける回転。"""
    d = np.asarray(d, float)
    d = d / np.linalg.norm(d)
    c = d[0]
    if c < -1 + 1e-12:
        return np.array([0.0, 0.0, 0.0, 1.0])
    q = np.array([1.0 + c, 0.0, -d[2], d[1]])      # cross(x, d) = (0, -d_z, d_y)
    return q / np.linalg.norm(q)


# =========================================================================== #
# 場面: 物体(メッシュ 1 回 + コマごとの姿勢)と光線の棒の溜め                    #
# =========================================================================== #
class Scene:
    """1 タブの 3-D。光線は長さの違う細い棒を組み合わせて描く(棒は剛体なので伸び縮みしない)。

    線分 P→Q(長さ D)は、D 以下の長さの棒を大きい順に D に届くまで選び、P から並べ、最後の棒は Q で
    終わるように重ねる(はみ出さない)。使わない棒・部品は光学台の中にしまう(見えない)。
    """

    def __init__(self, n, x_lo, x_hi, rod_r=None, lengths=(512.0, 256.0, 128.0, 64.0, 32.0, 16.0, 8.0, 4.0, 2.0)):
        self.n, self.x_lo, self.x_hi = n, float(x_lo), float(x_hi)
        if rod_r is None:                                      # 光線の太さは場面の長さに比例(画面で 1.5 px ほど)
            rod_r = 0.0011 * (x_hi - x_lo)
        self.rod_r, self.lengths = rod_r, tuple(sorted(lengths, reverse=True))
        self.items = []                           # (body dict, xyz (n,3), quat (n,4))
        self.segs = [[] for _ in range(n)]         # コマごとの (色の名前, P, Q)
        self.colors = {}
        self.park_x = 0.5 * (x_lo + x_hi)
        bench = box_mesh((x_lo - 15, -BENCH_W, BENCH_BOT), (x_hi + 15, BENCH_W, BENCH_TOP))
        self.add("bench", bench, (58, 64, 74))

    def park(self, half_len=0.0):
        return np.array([self.park_x - half_len, 0.0, PARK_Z])

    def add(self, name, mesh, rgb, xyz=None, quat=None, label=None, alpha=None):
        pos, tri = mesh
        xyz = np.zeros((self.n, 3)) if xyz is None else np.asarray(xyz, float)
        if xyz.shape == (3,):
            xyz = np.tile(xyz, (self.n, 1))
        quat = np.tile(Q0, (self.n, 1)) if quat is None else np.asarray(quat, float)
        if quat.shape == (4,):
            quat = np.tile(quat, (self.n, 1))
        b = {"name": name, "pos": pos, "faces": tri, "rgb": list(rgb)}
        if label is not None:
            b["label"] = label
        if alpha is not None:                                  # 光が通る部品(レンズ)は半透明
            b["alpha"] = float(alpha)
        self.items.append((b, xyz, quat))

    def color(self, key, rgb):
        self.colors[key] = list(rgb)

    def seg(self, k, key, p, q):
        """線分 P→Q を描く(場面の箱で切る: 光軸方向は台の範囲、横と上下は ±BOX mm)。"""
        p, q = np.asarray(p, float), np.asarray(q, float)
        if not (np.all(np.isfinite(p)) and np.all(np.isfinite(q))):
            return
        lo = np.array([self.x_lo - 10.0, -BOX, -BOX])
        hi = np.array([self.x_hi + 10.0, BOX, BOX])
        d = q - p
        t0, t1 = 0.0, 1.0
        for ax in range(3):                                    # Liang–Barsky
            if abs(d[ax]) < 1e-12:
                if p[ax] < lo[ax] or p[ax] > hi[ax]:
                    return
                continue
            a, b = (lo[ax] - p[ax]) / d[ax], (hi[ax] - p[ax]) / d[ax]
            t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
            if t0 >= t1:
                return
        p, q = p + t0 * d, p + t1 * d
        if np.linalg.norm(q - p) >= self.lengths[-1]:
            self.segs[k].append((key, p, q))

    def polyline(self, k, key, pts):
        pts = np.asarray(pts, float)
        for a, b in zip(pts[:-1], pts[1:]):
            self.seg(k, key, a, b)

    def _alloc(self):
        """コマごとに線分を棒で覆う割り当て(棒の溜めを小さく保つ)。

        棒の溜めはコマをまたいで共有する。各線分は長い順に、(1) 残りを 1 本で覆える空きの棒のうち最も短いもの、
        (2) 残りの 1/3 以上ある空きの棒のうち最も長いもの、(3) どちらも無ければ残りを覆える最も短い棒(無ければ
        線分以下で最長の棒)を溜めに足す —— の順に選ぶ。どの棒も線分より長くはしない(はみ出さない)。
        """
        pool = {}
        plans = []
        for k in range(self.n):
            avail = dict(pool)
            used = {}
            plan = []
            for key, p, q in sorted(self.segs[k], key=lambda x: -float(np.linalg.norm(x[2] - x[1]))):
                d = q - p
                D = float(np.linalg.norm(d))
                u = d / D
                fits = [L for L in self.lengths if L <= D + 1e-9]
                cur = 0.0
                while cur < D - 1e-9:
                    rem = D - cur
                    fin = [L for L in fits if avail.get((key, L), 0) > 0 and L >= rem - 1e-9]
                    big = [L for L in fits if avail.get((key, L), 0) > 0 and L >= rem / 3.0]
                    if fin:
                        L = min(fin)
                    elif big:
                        L = max(big)
                    else:
                        cover = [L for L in fits if L >= rem - 1e-9]
                        L = min(cover) if cover else fits[0]
                        pool[(key, L)] = pool.get((key, L), 0) + 1
                        avail[(key, L)] = avail.get((key, L), 0) + 1
                    avail[(key, L)] -= 1
                    i = used.get((key, L), 0)
                    used[(key, L)] = i + 1
                    st = min(cur, D - L)
                    plan.append(((key, L, i), p + st * u, q_from_x(u)))
                    cur = st + L
            plans.append(plan)
        return pool, plans

    def build(self):
        need, plans = self._alloc()
        rods = {}
        for (key, L), cnt in sorted(need.items()):
            mesh = prism_mesh(L, self.rod_r)
            for i in range(cnt):
                xyz = np.tile(self.park(L / 2), (self.n, 1))
                quat = np.tile(Q0, (self.n, 1))
                rods[(key, L, i)] = (xyz, quat)
                self.items.append(({"name": "ray_%s_%g_%d" % (key, L, i), "pos": mesh[0], "faces": mesh[1],
                                    "rgb": self.colors[key]}, xyz, quat))
        for k, plan in enumerate(plans):
            for rid, p, q in plan:
                rods[rid][0][k] = p
                rods[rid][1][k] = q
        bodies = [b for b, _, _ in self.items]
        xyz = np.stack([x for _, x, _ in self.items], 1)
        quat = np.stack([q for _, _, q in self.items], 1)
        return bodies, xyz, quat, sum(need.values())


# =========================================================================== #
# 光線の経路(raytrace の座標 → 世界)                                          #
# =========================================================================== #
def to_world(p, x0):
    """raytrace の (x, y, z)(z = 光軸、y = 画角の向き)→ 世界 (x0 + z, x, y)(世界の z は上)。"""
    p = np.asarray(p, float)
    return np.stack([x0 + p[..., 2], p[..., 0], p[..., 1]], -1)


def vertex_z(system):
    """各面の頂点の光軸上の位置(最初の頂点 = 0)。"""
    z, out = 0.0, []
    for s in system["surfaces"]:
        out.append(z)
        z += float(s["t"]) if s["t"] is not None else 0.0
    return np.array(out)


def ray_paths(system, tr, x0, skip_glass=True):
    """trace_rays の出力 → 光線ごとの折れ線(世界座標)と「どこで止められたか」。

    ガラスの中の区間は描かない(レンズは不透明に描くので見えない)。ケラレた光線は、最後に通った面から
    止めた面の頂点の平面まで伸ばして止める(``blocked`` = その面の番号、通ったものは -1)。
    """
    P, Dd = tr["points"], tr["dirs"]
    surf = system["surfaces"]
    zv = vertex_z(system)
    glass = [rt.refractive_index(s["n"], WL_UM) > 1.0001 for s in surf]
    out = []
    for r in range(P.shape[0]):
        pts = P[r]
        fin = np.all(np.isfinite(pts), axis=1)
        blocked = -1
        if not fin.all():
            j = int(np.argmin(fin))                                     # 最初の NaN(面 j-1 で止められた)
            blocked = j - 1
            last, d = pts[j - 1], Dd[r, j - 1]
            if j - 1 < len(zv) and np.all(np.isfinite(d)) and abs(d[2]) > 1e-9:
                tt = (zv[j - 1] - last[2]) / d[2]
                pts = np.vstack([pts[:j], last + max(tt, 0.0) * d])
            else:
                pts = pts[:j]
        segs = []
        for k in range(len(pts) - 1):
            inside = skip_glass and 1 <= k <= len(surf) and glass[k - 1]
            if not inside:
                segs.append((to_world(pts[k], x0), to_world(pts[k + 1], x0)))
        out.append({"segs": segs, "blocked": blocked, "end": to_world(pts[-1], x0)})
    return out


def nearest_point(P, D):
    """直線群 P + s D(D は単位)に最も近い点(最小二乗)。実像も虚像も同じ式。"""
    D = D / np.linalg.norm(D, axis=1, keepdims=True)
    A = np.zeros((3, 3))
    b = np.zeros(3)
    for p, d in zip(P, D):
        M = np.eye(3) - np.outer(d, d)
        A += M
        b += M @ p
    return np.linalg.solve(A, b)


# =========================================================================== #
# 処理の帯(panes)                                                           #
# =========================================================================== #
PW, PH = 116, 64                                  # 1 段の小窓
COL_W, HEAD, GAP = 132, 19, 12
STRIP_H = 20
BG = 0.11


class Canvas:
    """小窓の描画(numpy、縁をぼかさない = PNG を小さく)。座標は (x 右, y 上) の値域で渡す。"""

    def __init__(self, xr, yr, w=PW, h=PH, bg=0.07):
        self.img = np.full((h, w, 3), bg)
        self.xr, self.yr, self.w, self.h = xr, yr, w, h

    def rc(self, x, y):
        c = (x - self.xr[0]) / (self.xr[1] - self.xr[0]) * (self.w - 1)
        r = (self.yr[1] - y) / (self.yr[1] - self.yr[0]) * (self.h - 1)
        return r, c

    def dot(self, x, y, rad, col):
        r, c = self.rc(x, y)
        self._dot(r, c, rad, col)

    def _dot(self, r, c, rad, col):
        if not (np.isfinite(r) and np.isfinite(c)):
            return
        y0, y1 = max(0, int(r - rad - 1)), min(self.h, int(r + rad + 2))
        x0, x1 = max(0, int(c - rad - 1)), min(self.w, int(c + rad + 2))
        if y0 >= y1 or x0 >= x1:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1]
        m = np.hypot(yy - r, xx - c) <= rad + 0.25
        self.img[y0:y1, x0:x1][m] = col

    def line(self, x0, y0, x1, y1, col, w=0.5):
        r0, c0 = self.rc(x0, y0)
        r1, c1 = self.rc(x1, y1)
        if not all(np.isfinite([r0, c0, r1, c1])):
            return
        n = int(max(abs(r1 - r0), abs(c1 - c0)) * 1.5) + 2
        if n > 4000:
            return
        for t in np.linspace(0, 1, n):
            r, c = r0 + t * (r1 - r0), c0 + t * (c1 - c0)
            ri, ci = int(round(r)), int(round(c))
            if w <= 0.5:
                if 0 <= ri < self.h and 0 <= ci < self.w:
                    self.img[ri, ci] = col
            else:
                self._dot(r, c, w, col)

    def poly(self, xs, ys, col, w=0.5):
        for i in range(len(xs) - 1):
            self.line(xs[i], ys[i], xs[i + 1], ys[i + 1], col, w)

    def text(self, s, x, y, col=(0.85, 0.85, 0.85), size=9, anchor="lt"):
        r, c = self.rc(x, y)
        self.textpx(s, c, r, col, size, anchor)

    def textpx(self, s, c, r, col=(0.85, 0.85, 0.85), size=9, anchor="lt", clear=True):
        if clear:                                              # 字の下の線を消す(読めるように)。幅は字数からの見積もり
            w = min(self.w, int(len(s) * size * 0.62) + 4)
            h = size + 4
            x0 = int(c) if anchor[0] == "l" else int(c) - w if anchor[0] == "r" else int(c) - w // 2
            y0 = int(r) if anchor[1] == "t" else int(r) - h if anchor[1] == "b" else int(r) - h // 2
            x0, y0 = max(0, x0 - 1), max(0, y0 - 1)
            self.img[y0:y0 + h, x0:x0 + w] = self.img[0, 0] if self.img.ndim == 3 else self.img[0, 0]
        self.img = _text(self.img, s, (c, r), col, size, anchor)


def _text(img, s, xy, col, size, anchor="lt", max_width=None):
    """annotate.text_box(fullseye の注記 op)で字を描き、字の縁を 2 値にする(PNG を小さく保つ)。"""
    base = np.asarray(img, float)
    if max_width is None:                                  # 収まる幅(はみ出すなら字を小さく。小さくしても収まらなければ例外)
        x = float(xy[0])
        max_width = int((base.shape[1] - x - 1) if anchor[0] == "l" else (x - 1) if anchor[0] == "r"
                        else 2 * min(x, base.shape[1] - x) - 2)
    out = annotate.text_box(base.copy(), s, (float(xy[0]), float(xy[1])), anchor=anchor, font_size=size,
                            min_font_size=6, pad=0, wrap=False, line_spacing=1.0, text_color=tuple(col),
                            box_alpha=0.0, max_width=max_width)
    out = np.clip(out, 0, 1)
    diff = np.abs(out - base).sum(-1)
    m = diff > 0.22 * np.abs(np.asarray(col) - base).sum(-1).clip(0.05)
    res = base.copy()
    res[m] = col
    return res


def band_heads(stage_text):
    """帯の見出し(段ごと、強調あり / なし)を前もって描く。stage_text = op の登録名 4 つ(説明は pane の見出しに)。"""
    heads = []
    for s, opname in enumerate(stage_text):
        row = []
        for on in (False, True):
            hb = np.full((HEAD, COL_W, 3), BG)
            col = STAGE_RGB[s] if on else (0.55, 0.55, 0.55)
            hb = _text(hb, opname, (3, 2), col, 10, "lt", max_width=COL_W - 6)
            row.append(hb)
        heads.append(row)
    return heads


def band_frame(panels, active, heads, lines):
    """1 コマの帯: 4 段の小窓(いま効いている段 = ``active`` を色で強調)+ 下にその時刻の式と数字の 1 行。

    op ごとの値・理論値・差はページの時系列(``series``、ヘッダに毎コマの値が出る)に回す —— 字を毎コマ
    画像に焼くと HTML が太る(1 行 ≈ 0.9 KB / コマ)。
    """
    cols = []
    for s, p in enumerate(panels):
        on = s == active
        body = p if on else 0.55 * p + 0.45 * BG
        lp = (COL_W - PW) // 2
        body = np.pad(body, ((0, 0), (lp, COL_W - PW - lp), (0, 0)), constant_values=BG)
        fr = np.concatenate([heads[s][1 if on else 0], body], axis=0)
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
    strip = np.full((STRIP_H, out.shape[1], 3), BG)
    for i, (s, col) in enumerate(lines[:1]):
        strip = _text(strip, s, (4, 2), col, 11, "lt", max_width=out.shape[1] - 56)
    strip = _text(strip, "Fullseye", (out.shape[1] - 4, STRIP_H - 3), (0.45, 0.62, 0.80), 9, "rb")
    out = np.concatenate([out, strip], axis=0)
    return np.rint(np.clip(out, 0, 1) * 255).astype(np.uint8)


def active_stage(k):
    """帯の強調: 0.6 秒ずつ 1 → 2 → 3 → 4 段と回す(処理の流れを見せる)。"""
    return int(k // 9) % 4


def fmt(x, nd=1):
    if not np.isfinite(x):
        return "∞"
    return ("%." + str(nd) + "f") % x


def n_of(material):
    """材料ライブラリ(materials)の屈折率を d 線で引く。光学系にはこの数値を渡す(同じ表を参照)。"""
    return float(materials.material_optical_constants(material, WL_NM)["n"])


def singlet(R1, R2, t, ap, n, nxt=None):
    """両面の球面レンズの 2 面(後の面の後ろの距離は nxt、None = 近軸の像まで)。"""
    return [{"R": R1, "t": t, "n": n, "ap": ap}, {"R": R2, "t": nxt, "n": 1.0, "ap": ap}]


def times():
    return np.arange(NF) / FPS


# =========================================================================== #
# 薄レンズの結像                                                              #
# =========================================================================== #
LENS_A = {"R1": 102.0, "R2": -102.0, "t": 5.0, "ap": 16.0, "glass": "N-BK7"}
H_OBJ = 8.0                                        # 物体(矢印)の高さ mm
S_END, S_J2F = 2.0, 10                             # f / a を線形に振って a = 3.2f → 0.5f。10 コマ目がちょうど a = 2f
X_END_A = 470.0                                    # 光線を描く右端(世界 x)
X_LO_A = -365.0


def arrow_glyph(h, step=0.5):
    """矢印の形の点(物体面、(x, y) mm)。軸 + 頭の三角の 2 辺。"""
    ys = np.arange(0.0, h + 1e-9, step)
    pts = [(0.0, y) for y in ys]
    hw, hh = 0.32 * h, 0.35 * h
    for u in np.linspace(0, 1, 9)[1:]:
        pts.append((-hw * (1 - u), h - hh + hh * u))
        pts.append((hw * (1 - u), h - hh + hh * u))
    return np.array(pts)


def run_imaging(n_frames=NF):
    """物体の位置 a を振る。op の値(paraxial_trace / thin_lens / trace_rays)と理論の線をコマごとに記録。"""
    L = LENS_A
    n = n_of(L["glass"])
    s0 = (0.5 - S_J2F * S_END / (n_frames - 1)) / (1.0 - S_J2F / (n_frames - 1))
    s = np.linspace(s0, S_END, n_frames)
    if np.any(np.abs(s - 1.0) < 1e-6):
        raise ValueError("a コマが a = f にちょうど乗る(像が無限遠): n_frames を変える")
    sys0 = rt.lens_system(singlet(L["R1"], L["R2"], L["t"], L["ap"], n), stop=0, object_mm=200.0)
    para0 = rt.paraxial_trace(sys0)
    f = para0["efl"]
    xH, xH2 = para0["pp_front"], L["t"] + para0["pp_rear"]           # 主点 H, H'(最初の頂点から)
    a = f / s
    glyph = arrow_glyph(H_OBJ)
    rec = {"f": f, "n": n, "xH": xH, "xH2": xH2, "a": a, "t": times()[:n_frames], "frames": []}
    keys = ("b_thin", "m_thin", "b_para", "m_para", "b_ray", "m_ray", "x_img")
    for k in keys:
        rec[k] = np.zeros(n_frames)
    for i in range(n_frames):
        obj = a[i] - xH                                              # 最初の頂点から物体まで
        system = rt.lens_system(singlet(L["R1"], L["R2"], L["t"], L["ap"], n), stop=0, object_mm=obj)
        para = rt.paraxial_trace(system)
        tl = optics.thin_lens(focal_mm=f, object_mm=float(a[i]))
        b, m = tl["image_mm"], tl["magnification"]
        x_img = xH2 + b                                              # 像の位置(最初の頂点から)
        real_in = b > 0 and x_img <= X_END_A - 10
        end_z = x_img if real_in else X_END_A
        tip = np.array([0.0, H_OBJ, -obj])
        dirs, kinds = [], []
        dirs.append([0.0, 0.0, 1.0]); kinds.append("p")                                      # 光軸に平行
        dirs.append([0.0, -H_OBJ, xH + obj]); kinds.append("p")                             # 主点(節点)へ
        F = np.array([0.0, 0.0, xH - f])
        dF = tip - F if tip[2] > F[2] else F - tip
        dirs.append(list(dF)); kinds.append("p")                                             # 前の焦点を通る
        for th in np.linspace(0, 2 * np.pi, 6, endpoint=False):                             # 立体の円錐(縁の 0.8)
            q = np.array([0.8 * L["ap"] * math.cos(th), 0.8 * L["ap"] * math.sin(th), 0.0])
            dirs.append(list(q - tip)); kinds.append("c")
        nls = 8
        for th in np.linspace(0, 2 * np.pi, nls, endpoint=False):                           # 像の位置を測る光線
            q = np.array([0.45 * L["ap"] * math.cos(th), 0.45 * L["ap"] * math.sin(th), 0.0])
            dirs.append(list(q - tip)); kinds.append("m")
        D = np.array(dirs, float)
        D /= np.linalg.norm(D, axis=1, keepdims=True)
        O = np.tile(tip, (len(D), 1))
        tr = rt.trace_rays(system, O, D, image_mm=end_z - L["t"])
        ns = len(system["surfaces"])
        sel = np.array([k == "m" for k in kinds]) & tr["valid"]
        pimg = nearest_point(tr["points"][sel, ns], tr["dirs"][sel, ns])
        b_ray = pimg[2] - xH2
        m_ray = pimg[1] / H_OBJ
        # 矢印の各点を実光線で運ぶ(主点へ向かう 1 本 + 0.45 の輪 6 本 → 最小二乗の交点)
        gl_img = []
        for gx, gy in glyph:
            p0 = np.array([gx, gy, -obj])
            tg = [np.array([0.0, 0.0, xH])] + [np.array([0.45 * L["ap"] * math.cos(th), 0.45 * L["ap"] * math.sin(th), 0.0])
                                                for th in np.linspace(0, 2 * np.pi, 6, endpoint=False)]
            Dg = np.array([q - p0 for q in tg])
            Dg /= np.linalg.norm(Dg, axis=1, keepdims=True)
            tg_ = rt.trace_rays(system, np.tile(p0, (len(Dg), 1)), Dg, image_mm=10.0)
            ok = tg_["valid"]
            gl_img.append(nearest_point(tg_["points"][ok, ns], tg_["dirs"][ok, ns])[:2] if ok.sum() >= 2 else (np.nan, np.nan))
        rec["frames"].append({"system": system, "tr": tr, "kinds": kinds, "pimg": pimg, "real_in": real_in,
                              "end_z": end_z, "glyph_img": np.array(gl_img, float), "obj": obj})
        rec["b_thin"][i], rec["m_thin"][i] = b, m
        rec["b_para"][i] = para["image_mm"] - para0["pp_rear"]       # 後の主点から測った近軸の像
        rec["m_para"][i] = para["magnification"]
        rec["b_ray"][i], rec["m_ray"][i] = b_ray, m_ray
        rec["x_img"][i] = x_img
    rec["glyph"] = glyph
    return rec


def collimated(heights, lateral=(), z0=-60.0, angle_deg=0.0):
    """平行光の光線: 子午面(y)の高さの列 + 横(x)の列。z0 の面から出す。"""
    O = [[0.0, h, z0] for h in heights] + [[x, 0.0, z0] for x in lateral]
    a = math.radians(angle_deg)
    D = np.tile([0.0, math.sin(a), math.cos(a)], (len(O), 1))
    return np.array(O, float), D


def axis_crossing(p, d):
    """子午面の光線(点 p, 向き d)が光軸(y = 0)を横切る z。"""
    if abs(d[1]) < 1e-15:
        return INF
    return float(p[2] - p[1] / d[1] * d[2])


# =========================================================================== #
# レンズメーカーの式                                                          #
# =========================================================================== #
AP_B, TE_B = 12.0, 1.5                             # 半口径・縁の厚さ(曲げても縁の厚さを保つ)
R_STEPS = np.geomspace(300.0, 24.0, 12)
NF_B1 = 54                                         # 曲率を振るコマ(12 段、1 段 4〜5 コマ)
R_FIX = 50.0
MATS_B = ("WATER", "PMMA", "N-BK7", "POLYCARBONATE", "N-SF11", "N-LASF9")
H_RAYS_B = (-10.0, -6.5, -3.0, 0.0, 3.0, 6.5, 10.0)
LAT_B = (-8.0, 8.0)
X_HI_B = 370.0


def thickness_for(R, ap=AP_B, te=TE_B):
    return te + 2.0 * float(_sag(abs(R), ap))


def run_lensmaker(n_frames=NF):
    """曲率半径 R(両凸、R1 = R, R2 = −R)を振り、次に材料を替える。op の値と薄肉の式を記録。"""
    rec = {"t": times()[:n_frames], "frames": []}
    keys = ("R", "n", "thick", "f_thin", "f_thick", "f_para", "bfl_para", "f_ray", "pp_rear")
    for k in keys:
        rec[k] = np.zeros(n_frames)
    rec["mat"], rec["shape"] = [], []
    nf2 = n_frames - NF_B1
    for i in range(n_frames):
        if i < NF_B1:
            j = min(len(R_STEPS) - 1, i * len(R_STEPS) // NF_B1)
            R, mat, shape = float(R_STEPS[j]), "N-BK7", j
        else:
            m = min(len(MATS_B) - 1, (i - NF_B1) * len(MATS_B) // max(1, nf2))
            R, mat, shape = R_FIX, MATS_B[m], len(R_STEPS) + m
        t = thickness_for(R)
        n = n_of(mat)
        f_thin = 1.0 / ((n - 1.0) * (1.0 / R - 1.0 / (-R)))             # 薄肉のレンズメーカーの式(理論の線)
        tk = rt.thick_lens(R1=R, R2=-R, thickness=t, index=n)
        system = rt.lens_system(singlet(R, -R, t, AP_B, n), stop=0)
        para = rt.paraxial_trace(system)
        O, D = collimated(H_RAYS_B, LAT_B)
        x_end = min(t + para["bfl"] + 60.0, X_HI_B)
        tr = rt.trace_rays(system, O, D, image_mm=x_end - t)
        ns = len(system["surfaces"])
        top = int(np.argmax(H_RAYS_B))
        zc = axis_crossing(tr["points"][top, ns], tr["dirs"][top, ns]) if tr["valid"][top] else np.nan
        f_ray = zc - (t + tk["pp_rear"])                                # 後の主点から縁の光線の交点まで
        rec["frames"].append({"system": system, "tr": tr, "x_end": x_end, "z_cross": zc})
        for k, v in zip(keys, (R, n, t, f_thin, tk["efl"], para["efl"], para["bfl"], f_ray, tk["pp_rear"])):
            rec[k][i] = v
        rec["mat"].append(mat)
        rec["shape"].append(shape)
    return rec


# =========================================================================== #
# 2 枚組と ABCD 行列                                                          #
# =========================================================================== #
L1_C = {"R1": 102.0, "R2": -102.0, "t": 5.0, "ap": 15.0, "glass": "N-BK7"}
L2_C = {"R1": 52.0, "R2": -52.0, "t": 5.0, "ap": 11.0, "glass": "N-BK7"}
GAP_RANGE = (4.0, 236.0)
H_RAYS_C = (-9.0, -4.5, 0.0, 4.5, 9.0)
LAT_C = (-6.0, 6.0)
X_LO_C, X_HI_C = -80.0, 470.0


def run_doublet(n_frames=NF):
    """2 枚の間隔(L1 の後の頂点 → L2 の前の頂点)g を振る。ABCD(主点から測った薄レンズ)と実の処方を比べる。"""
    n = n_of(L1_C["glass"])
    p1 = rt.paraxial_trace(rt.lens_system(singlet(L1_C["R1"], L1_C["R2"], L1_C["t"], L1_C["ap"], n), stop=0))
    p2 = rt.paraxial_trace(rt.lens_system(singlet(L2_C["R1"], L2_C["R2"], L2_C["t"], L2_C["ap"], n), stop=0))
    f1, f2 = p1["efl"], p2["efl"]
    gaps = np.linspace(GAP_RANGE[0], GAP_RANGE[1], n_frames)
    rec = {"f1": f1, "f2": f2, "n": n, "p1": p1, "p2": p2, "gap": gaps, "t": times()[:n_frames], "frames": []}
    keys = ("d_pp", "f_formula", "f_abcd", "f_para", "x_F", "x_F_para", "x_H", "y_out", "u_out", "det", "f_ray")
    for k in keys:
        rec[k] = np.full(n_frames, np.nan)
    t1, t2 = L1_C["t"], L2_C["t"]
    for i, g in enumerate(gaps):
        d_pp = g + p2["pp_front"] - p1["pp_rear"]                       # H1' → H2
        M = optics.abcd_matrix([("lens", f1), ("free", d_pp), ("lens", f2)])
        A, C = M[0, 0], M[1, 0]
        ab = optics.abcd_trace(M, height_mm=9.0, angle_mrad=0.0)
        f_formula = 1.0 / (1.0 / f1 + 1.0 / f2 - d_pp / (f1 * f2))
        x_H2r = t1 + g + t2 + p2["pp_rear"]                             # L2 の後の主点(最初の頂点から)
        f_abcd = -1.0 / C if abs(C) > 1e-15 else INF
        x_F = x_H2r - A / C if abs(C) > 1e-15 else INF
        x_H = x_H2r + (1.0 - A) / C if abs(C) > 1e-15 else INF
        surf = singlet(L1_C["R1"], L1_C["R2"], t1, L1_C["ap"], n, nxt=g) + \
            singlet(L2_C["R1"], L2_C["R2"], t2, L2_C["ap"], n, nxt=100.0)
        system = rt.lens_system(surf, stop=0)
        para = rt.paraxial_trace(system)
        z_last = t1 + g + t2
        O, D = collimated(H_RAYS_C, LAT_C)
        x_end = X_HI_C
        if math.isfinite(x_F) and z_last < x_F < X_HI_C - 60:
            x_end = x_F + 50.0
        tr = rt.trace_rays(system, O, D, image_mm=x_end - z_last)
        ns = len(system["surfaces"])
        top = int(np.argmax(H_RAYS_C))
        pt, dt = tr["points"][top, ns], tr["dirs"][top, ns]
        zc = axis_crossing(pt, dt) if tr["valid"][top] else np.nan
        # 縁の光線の主面: 入る光線(高さ 9)の延長と出る光線の延長が交わる z(実光線)
        zh = float(pt[2] + (9.0 - pt[1]) / dt[1] * dt[2]) if tr["valid"][top] and abs(dt[1]) > 1e-12 else np.nan
        rec["frames"].append({"system": system, "tr": tr, "x_end": x_end, "z_last": z_last, "M": M,
                              "z_cross": zc, "z_hray": zh})
        vals = (d_pp, f_formula, f_abcd, para["efl"], x_F, z_last + para["bfl"], x_H, ab["height_mm"],
                ab["angle_mrad"], ab["determinant"], zc - x_H if math.isfinite(x_H) else np.nan)
        for k, v in zip(keys, vals):
            rec[k][i] = v
    return rec


# =========================================================================== #
# 絞りと瞳                                                                    #
# =========================================================================== #
L_D = {"R1": 82.0, "R2": -82.0, "t": 4.0, "ap": 11.0, "glass": "N-BK7"}
GAP_D = 16.0                                        # レンズ ↔ 絞り
STOP_R = 4.0
FIELD_MAX = 21.0


def pupil_system(ap=L_D["ap"]):
    """レンズ / 絞り / レンズ(対称)。物体は無限遠。ap = None ならレンズの縁で光束を切らない(門の比べ用)。"""
    n = n_of(L_D["glass"])
    s = [{"R": L_D["R1"], "t": L_D["t"], "n": n, "ap": ap},
         {"R": L_D["R2"], "t": GAP_D, "n": 1.0, "ap": ap},
         {"R": INF, "t": GAP_D, "n": 1.0, "ap": STOP_R},
         {"R": L_D["R1"], "t": L_D["t"], "n": n, "ap": ap},
         {"R": L_D["R2"], "t": None, "n": 1.0, "ap": ap}]
    return rt.lens_system(s, stop=2)


def beam_area(system, theta_deg, pitch=0.12):
    """画角 θ の平行光束のうち像まで届く断面積(光束に垂直な面で数える、mm²)。実光線の数え上げ。

    格子は実の主光線(``chief_ray``)の出発点を中心に、入射瞳の半径の 2.2 倍 + 3 mm 四方。届いた光線が
    格子の縁に触れたら格子が足りない(数え漏れ)ので ValueError(黙って小さい値を返さない)。
    """
    para = rt.paraxial_trace(system)
    half = 2.2 * para["ep_radius"] + 3.0
    th = math.radians(theta_deg)
    d = np.array([0.0, math.sin(th), math.cos(th)])
    e1, e2 = np.array([1.0, 0.0, 0.0]), np.array([0.0, math.cos(th), -math.sin(th)])
    cr = rt.chief_ray(system, field=float(theta_deg))
    c = cr["points"][0] if cr["valid"] else np.array([0.0, 0.0, para["ep_position"]]) - 60.0 * d
    u = np.arange(-half, half + 1e-9, pitch)
    U, V = np.meshgrid(u, u)
    O = c + U.reshape(-1, 1) * e1 + V.reshape(-1, 1) * e2
    tr = rt.trace_rays(system, O, np.tile(d, (len(O), 1)))
    v = tr["valid"]
    edge = (np.abs(U.ravel()) > half - 2 * pitch) | (np.abs(V.ravel()) > half - 2 * pitch)
    if (v & edge).any():
        raise ValueError("beam_area: the transmitted beam reaches the edge of the launch grid at %.2f deg" % theta_deg)
    return float(v.sum()) * pitch * pitch


def real_relative_illumination(system, thetas, dth=0.25, parts=False):
    """実光線の周辺光量: E(θ)/E(0) = [A(θ)/A(0)] · f² sinθ / (y dy/dθ)(y = 主光線の像高、A = 届く光束の断面積)。

    物体側の放射輝度が一様なら、像の小さな輪に入る光は「瞳の見かけの面積 × 立体角」、輪の面積は y dy。
    ひずみも瞳のゆがみもケラレも無ければ A(θ) = A(0) cosθ、y = f tanθ で、ちょうど cos⁴θ になる。
    """
    para = rt.paraxial_trace(system)
    f = para["efl"]
    A0 = beam_area(system, 0.0)
    out, ar, st = [], [], []
    for th in thetas:
        th = float(th)
        if th < 1e-6:
            out.append(1.0); ar.append(1.0); st.append(1.0)
            continue
        y = rt.chief_ray(system, field=th)["image_y"]
        yp = rt.chief_ray(system, field=th + dth)["image_y"]
        ym = rt.chief_ray(system, field=max(th - dth, 0.0))["image_y"]
        dy = (yp - ym) / math.radians(th + dth - max(th - dth, 0.0))
        a = beam_area(system, th) / A0
        s_ = f * f * math.sin(math.radians(th)) / (y * dy)
        out.append(a * s_); ar.append(a); st.append(s_)
    if parts:
        return np.array(out), np.array(ar), np.array(st)
    return np.array(out)


def fan_rays(system, para, theta_deg, n_mer=7, n_sag=4):
    """入射瞳を少し大きめに覆う平行光: 子午面 n_mer 本 + 横 n_sag 本(ケラレが見えるように 1.5 倍)。"""
    th = math.radians(theta_deg)
    d = np.array([0.0, math.sin(th), math.cos(th)])
    zc = para["ep_position"]
    c = np.array([0.0, 0.0, zc]) - (zc + 40.0) / d[2] * d                # 入射瞳の中心を狙い、z = -40 から
    r = 1.5 * para["ep_radius"]
    O = [c + np.array([0.0, v * math.cos(th), -v * math.sin(th)]) for v in np.linspace(-r, r, n_mer)]
    O += [c + np.array([v, 0.0, 0.0]) for v in (-r, -0.5 * r, 0.5 * r, r)][:n_sag]
    return np.array(O), np.tile(d, (len(O), 1))


def run_pupils(n_frames=NF):
    """画角 θ を 0 → 32° に振る。瞳(paraxial_trace)・主光線(chief_ray)・ケラレ(ray_bundle)・cos⁴ を記録。"""
    system = pupil_system()
    para = rt.paraxial_trace(system)
    th = np.linspace(0.0, FIELD_MAX, n_frames)
    rec = {"para": para, "theta": th, "t": times()[:n_frames], "frames": [], "system": system}
    keys = ("y_chief", "y_tan", "vig", "stop_hit")
    for k in keys:
        rec[k] = np.zeros(n_frames)
    rec["cos4"] = optics.relative_illumination(half_angle_deg=FIELD_MAX, samples=n_frames)[:, 1]
    rec["ri_real"], rec["ri_area"], rec["ri_stretch"] = real_relative_illumination(system, th, parts=True)
    rec["theta_noclip"] = th[::8]
    rec["ri_noclip"] = real_relative_illumination(pupil_system(ap=None), rec["theta_noclip"])
    rec["zv"] = vertex_z(system)
    for i, a in enumerate(th):
        cr = rt.chief_ray(system, field=float(a))
        rb = rt.ray_bundle(system, field=float(a), rings=5)
        O, D = fan_rays(system, para, float(a))
        tr = rt.trace_rays(system, O, D)
        rec["frames"].append({"chief": cr, "bundle": rb, "tr": tr})
        rec["y_chief"][i] = cr["image_y"]
        rec["y_tan"][i] = para["efl"] * math.tan(math.radians(a))
        rec["vig"][i] = float(rb["valid"].mean())
        rec["stop_hit"][i] = float(cr["points"][3, 1])                 # 主光線が絞りの面を通る高さ(0 のはず)
    return rec


# =========================================================================== #
# 3-D と帯の組み立て(タブごと)                                               #
# =========================================================================== #
GLASS_RGB = (170, 214, 238)
# レンズの不透明度(pocviewer の bodies[*]["alpha"])。半透明にして、ガラスの中と後ろを通る光線を透かして見せる。
# 鏡筒の絞り・スクリーン・センサー・台・支柱は光を通さないので不透明のまま。
GLASS_ALPHA = 0.3
#: 材料表のキー(コードの中だけ) → 画面に出す一般名 (ja, en, 帯の短い英字)。硝材のカタログ名(製品の型番)は
#: 公開物の画面にも帯の PNG にも出さない(tests/test_no_company_names_in_public_pocs.py)。ガラスは一般名 +
#: (n_d, V_d)を出す(値は materials.abbe_number のカタログ値)。
MAT_NAMES = {"WATER": ("水", "water", "water"), "PMMA": ("アクリル(PMMA)", "acrylic (PMMA)", "acrylic"),
             "POLYCARBONATE": ("ポリカーボネート", "polycarbonate", "polycarbonate"),
             "N-BK7": ("クラウンガラス", "crown glass", "crown"),
             "N-SF11": ("重フリントガラス", "dense flint glass", "dense flint"),
             "N-LASF9": ("ランタン系高屈折率ガラス", "lanthanum dense flint glass", "La dense flint")}
_GLASSES = ("N-BK7", "N-SF11", "N-LASF9")


def mat_label(key, lang="ja", nd_vd=True):
    """材料表のキーの一般名。ja / en はガラスなら「クラウンガラス(n_d = 1.5168, V_d = 64.17)」、band は帯の短い英字。"""
    ja, en, band = MAT_NAMES[key]
    if lang == "band":
        return band
    name = ja if lang == "ja" else en
    if not (nd_vd and key in _GLASSES):
        return name
    ab = materials.abbe_number(key)
    nd = ab["nd_catalog"] if ab.get("nd_catalog") is not None else ab["nd"]
    vd = ab["vd_catalog"] if ab.get("vd_catalog") is not None else ab["vd"]
    return ("%s(n_d = %.4f, V_d = %.2f)" if lang == "ja" else "%s (n_d = %.4f, V_d = %.2f)") % (name, nd, vd)


MAT_RGB = {"WATER": (120, 180, 255), "PMMA": (200, 230, 245), "N-BK7": GLASS_RGB,
           "POLYCARBONATE": (225, 215, 190), "N-SF11": (230, 200, 160), "N-LASF9": (240, 180, 150)}
WHITE = (235, 235, 235)


def _stage_colors(sc):
    for i, h in enumerate(STAGE_HEX):
        sc.color("s%d" % i, U8(STAGE_RGB[i]))
    sc.color("grey", GREY)
    sc.color("block", BLOCK)


def _draw_paths(sc, k, paths, key, block_key=None, stop_index=None, stop_key="grey"):
    for pth in paths:
        kk = key
        if block_key and pth["blocked"] >= 0:
            kk = stop_key if pth["blocked"] == stop_index else block_key
        for a, b in pth["segs"]:
            sc.seg(k, kk, a, b)


def _lens_body(sc, name, L, n_xyz, rgb=GLASS_RGB, post=True):
    sc.add(name, lens_mesh(L["R1"], L["R2"], L["t"], L["ap"]), rgb, xyz=n_xyz, alpha=GLASS_ALPHA)
    if post:
        xyz = np.asarray(n_xyz, float)
        xyz = (np.tile(xyz, (sc.n, 1)) if xyz.shape == (3,) else xyz) + np.array([L["t"] / 2, 0.0, 0.0])
        sc.add(name + "_post", cylinder_z(2.2, BENCH_TOP, -L["ap"] - 0.5), (120, 124, 132), xyz=xyz)


def _marker(sc, name, r, rgb, pts, label=None):
    """点の目印(球)。pts (n,3)、NaN のコマは台の中へしまう。"""
    pts = np.array(pts, float)
    bad = ~np.all(np.isfinite(pts), axis=1)
    pts[bad] = sc.park()
    sc.add(name, sphere_mesh(r), rgb, xyz=pts, label=label)


def _in_x(x, lo, hi):
    return np.isfinite(x) and lo <= x <= hi


def _graph_axes(cv, xt=(), yt=(), xl="", yl=""):
    for x in xt:
        cv.line(x, cv.yr[0], x, cv.yr[1], (0.20, 0.20, 0.22))
    for y in yt:
        cv.line(cv.xr[0], y, cv.xr[1], y, (0.20, 0.20, 0.22))


# ----------------------------------------------------------------------------- 薄レンズの結像
def build_imaging_tab(rec):
    n_ = len(rec["a"])
    L = LENS_A
    f, xH, xH2 = rec["f"], rec["xH"], rec["xH2"]
    sc = Scene(n_, X_LO_A, X_END_A + 12)
    _stage_colors(sc)
    _lens_body(sc, "lens", L, np.zeros(3))
    obj_x = np.array([-fr["obj"] for fr in rec["frames"]])
    head = 2.4
    xyz_o = np.column_stack([obj_x, np.zeros(n_), np.zeros(n_)])
    sc.add("object", cylinder_z(0.8, 0.0, H_OBJ - head), WHITE, xyz=xyz_o,
           label=T("物体(矢印、高さ 8 mm)", "object (arrow, 8 mm tall)"))
    sc.add("object_head", cone_z(2.2, head), WHITE, xyz=xyz_o + np.array([0, 0, H_OBJ]))
    sc.add("object_post", cylinder_z(1.4, BENCH_TOP, -0.5), (120, 124, 132), xyz=xyz_o)
    # 像の矢印(thin_lens の b, m)。頭は円錐、軸は棒。範囲外は台の中
    head_xyz, head_q = np.zeros((n_, 3)), np.tile(Q0, (n_, 1))
    scr_xyz = np.tile([X_END_A + 8, 0.0, 0.0], (n_, 1))
    img_pt = np.full((n_, 3), np.nan)
    for k, fr in enumerate(rec["frames"]):
        b, m, x_img = rec["b_thin"][k], rec["m_thin"][k], rec["x_img"][k]
        show = _in_x(x_img, X_LO_A + 4, X_END_A - 4) and abs(m * H_OBJ) < 62
        if show:
            tip = np.array([x_img, 0.0, m * H_OBJ])
            base = np.array([x_img, 0.0, 0.0])
            u = np.sign(m)
            sc.seg(k, "s1", base, tip - np.array([0, 0, u * head]))
            head_xyz[k] = tip
            head_q[k] = Q0 if m > 0 else Q_FLIP_X
        else:
            head_xyz[k] = sc.park()
        if fr["real_in"]:
            scr_xyz[k] = [x_img + 1.6, 0.0, 0.0]
        p = to_world(fr["pimg"], 0.0)
        if _in_x(p[0], X_LO_A + 4, X_END_A - 4) and abs(p[2]) < 70:
            img_pt[k] = p
        paths = ray_paths(fr["system"], fr["tr"], 0.0)
        for ir, (pth, kind) in enumerate(zip(paths, fr["kinds"])):
            if kind == "m":
                continue
            for a_, b_ in pth["segs"]:
                sc.seg(k, "s2", a_, b_)
            if b < 0 and kind == "p" and pth["blocked"] < 0:            # 虚像: 出た光線を後ろへ伸ばす(灰)
                ns = len(fr["system"]["surfaces"])
                p0 = fr["tr"]["points"][ir, ns]
                d0 = fr["tr"]["dirs"][ir, ns]
                zt = max(fr["pimg"][2], X_LO_A + 2)
                if d0[2] > 1e-9:
                    q = p0 + (zt - p0[2]) / d0[2] * d0
                    sc.seg(k, "grey", to_world(p0, 0.0), to_world(q, 0.0))
    sc.add("image_head", cone_z(2.2, head), U8(STAGE_RGB[1]), xyz=head_xyz, quat=head_q,
           label=T("像(thin_lens の b と m)", "image (b and m from thin_lens)"))
    sc.add("screen", box_mesh((-0.8, -30.0, BENCH_TOP), (0.8, 30.0, 30.0)), (205, 205, 200), xyz=scr_xyz,
           label=T("スクリーン(実像のときだけ像の位置へ)", "screen (moves to the image when it is real)"))
    _marker(sc, "ray_image", 1.7, U8(STAGE_RGB[3]), img_pt, label=T("実光線の像の点", "image point of the real rays"))
    for nm, x in (("F", xH - f), ("F2", xH2 + f), ("2F", xH - 2 * f), ("2F2", xH2 + 2 * f)):
        _marker(sc, nm, 1.9 if "2" not in nm[:1] else 1.3, U8(STAGE_RGB[0]) if not nm.startswith("2") else (90, 140, 170),
                np.tile([x, 0.0, 0.0], (n_, 1)))
    bodies, xyz, quat, nrods = sc.build()
    # ---------------------------------------------------------------- 帯
    heads = band_heads(["paraxial_trace", "thin_lens", "trace_rays", "theory line b(a)"])
    frames = []
    a_f = rec["a"] / f
    for k, fr in enumerate(rec["frames"]):
        a, b, m = rec["a"][k], rec["b_thin"][k], rec["m_thin"][k]
        # 1: 処方 → f, H, H'
        c1 = Canvas((X_LO_A, X_END_A), (-34, 34))
        c1.line(X_LO_A, 0, X_END_A, 0, (0.35, 0.35, 0.38))
        c1.line(0, -L["ap"], 0, L["ap"], (0.67, 0.84, 0.93), 1.0)
        for x in (xH - f, xH2 + f):
            c1.dot(x, 0, 2.0, STAGE_RGB[0])
        c1.line(-fr["obj"], 0, -fr["obj"], H_OBJ * 2, (0.92, 0.92, 0.92), 0.8)
        c1.textpx("f = %.2f mm" % f, 3, 2, STAGE_RGB[0], 9)
        c1.textpx("%s  R ±102  t 5" % mat_label(LENS_A["glass"], "band"), 3, PH - 2, (0.7, 0.7, 0.7), 8, "lb")
        # 2: thin_lens → b, m(数直線、f 単位)
        c2 = Canvas((-3.6, 4.6), (-5.5, 5.5))
        c2.line(-3.6, 0, 4.6, 0, (0.35, 0.35, 0.38))
        for x in (-2, -1, 1, 2):
            c2.line(x, -0.4, x, 0.4, STAGE_RGB[0])
        c2.line(0, -2.2, 0, 2.2, (0.67, 0.84, 0.93), 1.0)
        c2.line(-a / f, 0, -a / f, 1.0, (0.92, 0.92, 0.92), 0.8)
        if abs(b / f) < 4.5:
            c2.line(b / f, 0, b / f, float(np.clip(m, -5.2, 5.2)), STAGE_RGB[1], 1.0)
        c2.textpx("b = %s mm  m = %+.2f" % (fmt(b, 1), m), 3, 2, STAGE_RGB[1], 9)
        # 3: trace_rays → 像(矢印の各点の像)。物体の大きさ(白)と比べる
        c3 = Canvas((-40 * PW / PH, 40 * PW / PH), (-40, 40))
        c3.line(c3.xr[0], 0, c3.xr[1], 0, (0.22, 0.22, 0.24))
        g = rec["glyph"]
        for gx, gy in g:
            c3.dot(gx - 20, gy, 0.5, (0.55, 0.55, 0.55))
        gi = fr["glyph_img"]
        col3 = STAGE_RGB[2] if b > 0 else (0.62, 0.86, 0.64)
        for gx, gy in gi:
            if np.isfinite(gx) and abs(gy) < 45:
                c3.dot(gx + 18, gy, 0.6, col3)
        c3.textpx("object", 3, PH - 2, (0.6, 0.6, 0.6), 8, "lb")
        c3.textpx(("real, inverted" if b > 0 else "virtual, upright"), PW - 3, 2, col3, 9, "rt")
        # 4: 理論の線 b(a)/f と op の点
        c4 = Canvas((0.25, 3.25), (-6.5, 6.5))
        _graph_axes(c4, xt=(1.0, 2.0, 3.0), yt=(0.0,))
        aa = np.linspace(0.26, 3.24, 300)
        bb = 1.0 / (1.0 - 1.0 / aa)
        for i in range(len(aa) - 1):
            if abs(bb[i]) < 7 and abs(bb[i + 1]) < 7 and np.sign(bb[i]) == np.sign(bb[i + 1]):
                c4.line(aa[i], bb[i], aa[i + 1], bb[i + 1], (0.85, 0.85, 0.85))
        for j in range(k + 1):
            c4.dot(a_f[j], rec["b_ray"][j] / f, 0.7, STAGE_RGB[2])
            c4.dot(a_f[j], rec["b_thin"][j] / f, 0.6, STAGE_RGB[1])
        c4.dot(a_f[k], np.clip(rec["b_thin"][k] / f, -6.4, 6.4), 2.2, STAGE_RGB[3])
        c4.textpx("b/f", 3, 2, (0.7, 0.7, 0.7), 8)
        c4.textpx("a/f", PW - 3, PH - 2, (0.7, 0.7, 0.7), 8, "rb")
        state = "inverted real image" if b > 0 else "upright virtual image"
        l1 = ("1/a + 1/b = 1/f :  1/%.1f + 1/b = 1/%.2f  →  b = %s mm,  m = −b/a = %+.2f  (%s)   real rays: %s mm"
              % (a, f, fmt(b, 1), m, state, fmt(rec["b_ray"][k], 1)))
        db = rec["b_ray"][k] - b
        frames.append(band_frame([c1.img, c2.img, c3.img, c4.img], active_stage(k), heads,
                                 [(l1, STAGE_RGB[3])]))
    # ---------------------------------------------------------------- 段・数字
    t = rec["t"]
    k2f = int(np.argmin(np.abs(rec["a"] - 2 * f)))
    kf = int(np.argmax(rec["a"] < f))
    rel = np.abs(rec["b_ray"] - rec["b_thin"]) / np.abs(rec["b_thin"])
    klim = int(np.argmax(rel > 0.10))
    events = [{"t": float(t[0]), "label": T("a = 3f: 小さな倒立の実像", "a = 3f: small inverted real image")},
              {"t": float(t[k2f]), "label": T("a = 2f: 同じ大きさ(m = −1)", "a = 2f: same size (m = −1)")},
              {"t": float(t[klim]), "label": T("限界: 実光線が近軸の式から 10% ずれる", "limit: real rays 10% off the paraxial formula")},
              {"t": float(t[kf]), "label": T("a < f: 虚像(虫めがね)", "a < f: virtual image (magnifier)")}]
    events.sort(key=lambda e: e["t"])
    def win(v, lo, hi):                                                 # 枠の外は「—」(切り詰めた値を見せない)
        v = np.asarray(v, float).copy()
        v[(v < lo) | (v > hi)] = np.nan
        return v
    series = [{"label": T("b(thin_lens)", "b (thin_lens)"), "values": win(rec["b_thin"], -900, 1500), "lo": -900,
               "hi": 1500, "color": STAGE_HEX[1], "unit": "mm", "decimals": 2},
              {"label": T("b(paraxial_trace)", "b (paraxial_trace)"), "values": win(rec["b_para"], -900, 1500),
               "lo": -900, "hi": 1500, "color": STAGE_HEX[0], "unit": "mm", "decimals": 2},
              {"label": T("b(実光線)", "b (real rays)"), "values": win(rec["b_ray"], -900, 1500), "lo": -900, "hi": 1500,
               "color": STAGE_HEX[2], "unit": "mm", "decimals": 1},
              {"label": T("差(実光線 − 式)", "real − formula"), "values": win(100 * (rec["b_ray"] - rec["b_thin"]) / np.abs(rec["b_thin"]), -40, 40),
               "lo": -40, "hi": 40, "color": STAGE_HEX[3], "unit": "%", "decimals": 1},
              {"label": T("m(倍率)", "m (magnification)"), "values": win(rec["m_thin"], -10, 10), "lo": -10, "hi": 10,
               "color": "#e0e0e0", "unit": "", "decimals": 2}]
    info = {"nrods": nrods, "k2f": k2f, "kf": kf, "klim": klim, "rel": rel}
    return bodies, xyz, quat, frames, events, series, info


# ----------------------------------------------------------------------------- レンズメーカーの式
def build_lensmaker_tab(rec):
    n_ = len(rec["R"])
    sc = Scene(n_, -70.0, X_HI_B + 10)
    _stage_colors(sc)
    shapes = sorted(set(rec["shape"]))
    for sh in shapes:
        k0 = rec["shape"].index(sh)
        R, t_ = rec["R"][k0], rec["thick"][k0]
        mat = rec["mat"][k0]
        on = np.array([rec["shape"][k] == sh for k in range(n_)])
        xyz = np.where(on[:, None], 0.0, np.array([sc.park_x, 0.0, PARK_Z - t_ / 2])[None, :])
        quat = np.where(on[:, None], Q0[None, :], Q_FLAT[None, :])
        sc.add("lens_%d" % sh, lens_mesh(R, -R, t_, AP_B), MAT_RGB.get(mat, GLASS_RGB), xyz=xyz, quat=quat,
               alpha=GLASS_ALPHA)
    sc.add("lens_post", cylinder_z(2.2, BENCH_TOP, -AP_B - 0.5), (120, 124, 132), xyz=np.array([1.0, 0, 0]))
    fpar = np.full((n_, 3), np.nan)
    fthin = np.full((n_, 3), np.nan)
    hring = np.full((n_, 3), np.nan)
    for k, fr in enumerate(rec["frames"]):
        for pth in ray_paths(fr["system"], fr["tr"], 0.0):
            for a_, b_ in pth["segs"]:
                sc.seg(k, "s3", a_, b_)
        t_ = rec["thick"][k]
        xF = t_ + rec["bfl_para"][k]
        if xF < X_HI_B:
            fpar[k] = [xF, 0, 0]
        xT = t_ + rec["pp_rear"][k] + rec["f_thin"][k]                     # 薄肉の式の焦点(後の主点から f)
        if xT < X_HI_B:
            fthin[k] = [xT, 0, 0]
        hring[k] = [t_ + rec["pp_rear"][k], 0, 0]
    _marker(sc, "F_paraxial", 1.9, U8(STAGE_RGB[2]), fpar, label=T("焦点 F′(paraxial_trace)", "focus F′ (paraxial_trace)"))
    _marker(sc, "F_thin", 1.3, WHITE, fthin, label=T("薄肉の式の焦点", "focus by the thin-lens lensmaker formula"))
    sc.add("H_rear", ring_x(AP_B + 1.5, AP_B + 3.0, 0.8), U8(STAGE_RGB[1]), xyz=hring,
           label=T("後ろの主点 H′(thick_lens)", "rear principal point H′ (thick_lens)"))
    bodies, xyz, quat, nrods = sc.build()
    heads = band_heads(["material_optical_constants", "thick_lens", "paraxial_trace", "trace_rays"])
    frames = []
    disp = {}
    p_thin = 1000.0 / rec["f_thin"]
    p_thick = 1000.0 / rec["f_thick"]
    p_ray = 1000.0 / rec["f_ray"]
    for k, fr in enumerate(rec["frames"]):
        mat, n, R, t_ = rec["mat"][k], rec["n"][k], rec["R"][k], rec["thick"][k]
        if mat not in disp:
            disp[mat] = materials.material_dispersion(mat, 440.0, 800.0, 73)
        d = disp[mat]
        c1 = Canvas((440, 800), (1.30, 1.95))
        _graph_axes(c1, xt=(500, 600, 700), yt=(1.4, 1.5, 1.6, 1.7, 1.8, 1.9))
        c1.poly(d[:, 0], d[:, 1], (0.75, 0.75, 0.75))
        c1.dot(WL_NM, n, 2.2, STAGE_RGB[0])
        c1.textpx("%s  n_d = %.4f" % (mat_label(mat, "band"), n), 3, 2, STAGE_RGB[0], 9)
        c1.textpx("λ 440–800 nm", PW - 3, PH - 2, (0.6, 0.6, 0.6), 8, "rb")
        c2 = Canvas((-14, 30), (-13, 13))
        rr = np.linspace(-AP_B, AP_B, 60)
        c2.poly(_sag(R, rr), rr, (0.67, 0.84, 0.93))
        c2.poly(t_ + _sag(-R, rr), rr, (0.67, 0.84, 0.93))
        c2.line(t_ + rec["pp_rear"][k], -12, t_ + rec["pp_rear"][k], 12, STAGE_RGB[1])
        c2.textpx("R = ±%.1f  t = %.2f" % (R, t_), 3, 2, (0.75, 0.75, 0.75), 8)
        c2.textpx("f = %.2f" % rec["f_thick"][k], PW - 3, PH - 2, STAGE_RGB[1], 9, "rb")
        c3 = Canvas((-20, 320), (-12, 12))
        c3.line(-20, 0, 320, 0, (0.3, 0.3, 0.32))
        mg = rt.paraxial_trace(fr["system"])["marginal"]
        zF = t_ + rec["bfl_para"][k]
        c3.poly([-20, 0, t_, zF], [10, 10, 10 * mg["y"][1] / mg["y"][0], 0], STAGE_RGB[2])
        c3.dot(zF, 0, 2.0, STAGE_RGB[2])
        c3.textpx("efl %.2f  bfl %.2f" % (rec["f_para"][k], rec["bfl_para"][k]), 3, 2, STAGE_RGB[2], 9)
        c4 = Canvas((0, 62), (0, 62))
        _graph_axes(c4, xt=(20, 40, 60), yt=(20, 40, 60))
        c4.line(0, 0, 62, 62, (0.85, 0.85, 0.85))
        for j in range(k + 1):
            c4.dot(p_thin[j], p_ray[j], 0.8, STAGE_RGB[3])
            c4.dot(p_thin[j], p_thick[j], 0.7, STAGE_RGB[1])
        c4.dot(p_thin[k], p_thick[k], 2.0, STAGE_RGB[1])
        c4.textpx("1/f [D]", 3, 2, (0.7, 0.7, 0.7), 8)
        c4.textpx("(n−1)(1/R1−1/R2) [D]", PW - 3, PH - 2, (0.7, 0.7, 0.7), 8, "rb")
        dev = 100 * (rec["f_thick"][k] - rec["f_thin"][k]) / rec["f_thin"][k]
        l1 = ("1/f = (n − 1)(1/R1 − 1/R2) = (%.4f − 1)(1/%.1f + 1/%.1f)  →  f = %.2f mm   [%s]   thick_lens %.2f (%+.1f%%)"
              % (n, R, R, rec["f_thin"][k], mat_label(mat, "band"), rec["f_thick"][k],
                 100 * (rec["f_thick"][k] - rec["f_thin"][k]) / rec["f_thin"][k]))
        frames.append(band_frame([c1.img, c2.img, c3.img, c4.img], active_stage(k), heads,
                                 [(l1, STAGE_RGB[3])]))
    t = rec["t"]
    dev = np.abs(rec["f_thick"] - rec["f_thin"]) / rec["f_thin"]
    klim = int(np.argmax(dev[:NF_B1] > 0.05))
    events = [{"t": float(t[0]), "label": T("R = 300 mm: 薄いレンズ", "R = 300 mm: a thin lens")},
              {"t": float(t[klim]), "label": T("限界: 薄肉の式から 5% ずれる", "limit: 5% off the thin-lens formula")},
              {"t": float(t[NF_B1]), "label": T("材料を替える(R = 50 mm)", "change the material (R = 50 mm)")}]
    for mname in ("N-SF11",):
        events.append({"t": float(t[rec["mat"].index(mname)]),
                       "label": T("高屈折率のガラス(%s)" % mat_label(mname, "ja", False),
                                  "high-index glass (%s)" % mat_label(mname, "en", False))})
    series = [{"label": T("n(材料ライブラリ)", "n (material library)"), "values": rec["n"], "lo": 1.3, "hi": 1.9,
               "color": STAGE_HEX[0], "unit": "", "decimals": 4},
              {"label": T("f(薄肉の式)", "f (thin formula)"), "values": rec["f_thin"], "lo": 0, "hi": 300,
               "color": "#e0e0e0", "unit": "mm", "decimals": 2},
              {"label": T("f(thick_lens)", "f (thick_lens)"), "values": rec["f_thick"], "lo": 0, "hi": 300,
               "color": STAGE_HEX[1], "unit": "mm", "decimals": 2},
              {"label": T("f(paraxial_trace)", "f (paraxial_trace)"), "values": rec["f_para"], "lo": 0, "hi": 300,
               "color": STAGE_HEX[2], "unit": "mm", "decimals": 2},
              {"label": T("f(実光線、高さ 10 mm)", "f (real ray, 10 mm)"), "values": rec["f_ray"], "lo": 0, "hi": 300,
               "color": STAGE_HEX[3], "unit": "mm", "decimals": 2}]
    info = {"nrods": nrods, "klim": klim, "dev": dev}
    return bodies, xyz, quat, frames, events, series, info


# ----------------------------------------------------------------------------- 2 枚組と ABCD
def build_doublet_tab(rec):
    n_ = len(rec["gap"])
    sc = Scene(n_, X_LO_C, X_HI_C + 10)
    _stage_colors(sc)
    _lens_body(sc, "lens1", L1_C, np.zeros(3))
    x2 = np.column_stack([L1_C["t"] + rec["gap"], np.zeros(n_), np.zeros(n_)])
    _lens_body(sc, "lens2", L2_C, x2)
    fpar = np.full((n_, 3), np.nan)
    hring = np.full((n_, 3), np.nan)
    for k, fr in enumerate(rec["frames"]):
        for pth in ray_paths(fr["system"], fr["tr"], 0.0):
            for a_, b_ in pth["segs"]:
                sc.seg(k, "s3", a_, b_)
        if _in_x(rec["x_F_para"][k], X_LO_C, X_HI_C - 5):
            fpar[k] = [rec["x_F_para"][k], 0, 0]
        if _in_x(rec["x_H"][k], X_LO_C, X_HI_C - 5):
            hring[k] = [rec["x_H"][k], 0, 0]
        zh = fr["z_hray"]
        if _in_x(zh, X_LO_C + 2, X_HI_C - 5):                          # 主面の作図(灰): 入る光線の延長と出る光線の延長
            sc.seg(k, "grey", [0.0, 0.0, 9.0], [zh, 0.0, 9.0])
            top = int(np.argmax(H_RAYS_C))
            ns = len(fr["system"]["surfaces"])
            pe = to_world(fr["tr"]["points"][top, ns], 0.0)
            sc.seg(k, "grey", pe, [zh, 0.0, 9.0])
    _marker(sc, "F_paraxial", 1.9, U8(STAGE_RGB[2]), fpar, label=T("焦点 F′(paraxial_trace)", "focus F′ (paraxial_trace)"))
    on = np.all(np.isfinite(hring), axis=1)
    sc.add("H_rear", ring_x(11.6, 12.8, 0.8), U8(STAGE_RGB[0]),              # 範囲外は寝かせて台の中へ
           xyz=np.where(on[:, None], hring, sc.park()[None, :]), quat=np.where(on[:, None], Q0[None, :], Q_FLAT[None, :]),
           label=T("系の後ろの主点 H′(abcd_matrix)", "rear principal plane H′ of the pair (abcd_matrix)"))
    bodies, xyz, quat, nrods = sc.build()
    heads = band_heads(["abcd_matrix", "abcd_trace", "paraxial_trace", "trace_rays"])
    f1, f2 = rec["f1"], rec["f2"]
    frames = []
    P = 1000.0 / rec["f_abcd"]
    Pp = 1000.0 / rec["f_para"]
    Pr = 1000.0 / rec["f_ray"]
    for k, fr in enumerate(rec["frames"]):
        M = fr["M"]
        d = rec["d_pp"][k]
        c1 = Canvas((0, 1), (0, 1))
        c1.textpx("[ %+.4f   %+.2f ]" % (M[0, 0], M[0, 1]), 8, 18, STAGE_RGB[0], 10)
        c1.textpx("[ %+.5f  %+.4f ]" % (M[1, 0], M[1, 1]), 8, 34, STAGE_RGB[0], 10)
        c1.textpx("d = %.1f mm  det = %.6f" % (d, rec["det"][k]), 4, PH - 3, (0.7, 0.7, 0.7), 8, "lb")
        # 2: abcd_trace — 高さ 9 の光線(主点の面から主点の面へ)
        ab1 = optics.abcd_trace(optics.abcd_matrix([("lens", f1), ("free", d)]), 9.0, 0.0)
        c2 = Canvas((-30, 300), (-12, 12))
        c2.line(-30, 0, 300, 0, (0.3, 0.3, 0.32))
        c2.line(0, -10, 0, 10, (0.67, 0.84, 0.93))
        c2.line(d, -10, d, 10, (0.67, 0.84, 0.93))
        yo, uo = rec["y_out"][k], rec["u_out"][k] / 1000.0
        c2.poly([-30, 0, d, 300], [9, 9, ab1["height_mm"], yo + uo * (300 - d)], STAGE_RGB[1])
        c2.textpx("y′ = %.2f  θ′ = %.1f mrad" % (yo, rec["u_out"][k]), 3, 2, STAGE_RGB[1], 9)
        # 3: paraxial_trace の f と F′ の位置(数直線)
        c3 = Canvas((X_LO_C, X_HI_C), (-12, 12))
        c3.line(X_LO_C, 0, X_HI_C, 0, (0.3, 0.3, 0.32))
        c3.line(0, -8, 0, 8, (0.67, 0.84, 0.93))
        c3.line(L1_C["t"] + rec["gap"][k], -6, L1_C["t"] + rec["gap"][k], 6, (0.67, 0.84, 0.93))
        if _in_x(rec["x_F_para"][k], X_LO_C, X_HI_C):
            c3.dot(rec["x_F_para"][k], 0, 2.2, STAGE_RGB[2])
        if _in_x(rec["x_H"][k], X_LO_C, X_HI_C):
            c3.line(rec["x_H"][k], -9, rec["x_H"][k], 9, STAGE_RGB[0])
        c3.textpx("efl = %s mm" % fmt(rec["f_para"][k], 1), 3, 2, STAGE_RGB[2], 9)
        # 4: 屈折力 1/f と間隔 d(理論 = 直線)
        c4 = Canvas((0, 250), (-25, 32))
        _graph_axes(c4, xt=(100, 200), yt=(0,))
        dd = np.array([0.0, 250.0])
        c4.line(dd[0], 1000 * (1 / f1 + 1 / f2 - dd[0] / (f1 * f2)), dd[1], 1000 * (1 / f1 + 1 / f2 - dd[1] / (f1 * f2)),
                (0.85, 0.85, 0.85))
        for j in range(k + 1):
            if np.isfinite(Pr[j]):
                c4.dot(rec["d_pp"][j], Pr[j], 0.8, STAGE_RGB[3])
            c4.dot(rec["d_pp"][j], P[j], 0.6, STAGE_RGB[0])
        c4.dot(rec["d_pp"][k], Pp[k], 2.0, STAGE_RGB[2])
        c4.textpx("1/f [D]", 3, 2, (0.7, 0.7, 0.7), 8)
        c4.textpx("d [mm]", PW - 3, PH - 2, (0.7, 0.7, 0.7), 8, "rb")
        l1 = ("1/f = 1/f1 + 1/f2 − d/(f1·f2) = 1/%.1f + 1/%.1f − %.1f/(%.1f·%.1f)  →  f = %s mm   (d between principal planes)"
              % (f1, f2, d, f1, f2, fmt(rec["f_formula"][k], 1)))
        frames.append(band_frame([c1.img, c2.img, c3.img, c4.img], active_stage(k), heads,
                                 [(l1, STAGE_RGB[3])]))
    t = rec["t"]
    kaf = int(np.argmax(rec["d_pp"] > f1 + f2))
    events = [{"t": float(t[0]), "label": T("くっつけた 2 枚: 1/f ≈ 1/f1 + 1/f2", "lenses together: 1/f ≈ 1/f1 + 1/f2")},
              {"t": float(t[kaf]), "label": T("d = f1 + f2: 焦点距離が無限大(望遠鏡)", "d = f1 + f2: infinite focal length (telescope)")},
              {"t": float(t[min(len(t) - 1, kaf + 12)]), "label": T("その先: f が負(光は 2 枚の間で 1 度集まる)", "beyond: f turns negative (light focuses once between the lenses)")}]
    series = [{"label": T("1/f(式)", "1/f (formula)"), "values": 1000.0 / rec["f_formula"], "lo": -25, "hi": 32,
               "color": "#e0e0e0", "unit": "D", "decimals": 3},
              {"label": T("1/f(abcd_matrix)", "1/f (abcd_matrix)"), "values": P, "lo": -25, "hi": 32,
               "color": STAGE_HEX[0], "unit": "D", "decimals": 3},
              {"label": T("1/f(paraxial_trace)", "1/f (paraxial_trace)"), "values": Pp, "lo": -25, "hi": 32,
               "color": STAGE_HEX[2], "unit": "D", "decimals": 3},
              {"label": T("1/f(実光線、高さ 9 mm)", "1/f (real ray, 9 mm)"), "values": Pr, "lo": -25, "hi": 32,
               "color": STAGE_HEX[3], "unit": "D", "decimals": 3},
              {"label": T("det M", "det M"), "values": rec["det"], "lo": 0.9, "hi": 1.1, "color": STAGE_HEX[1],
               "unit": "", "decimals": 6}]
    info = {"nrods": nrods, "kaf": kaf}
    return bodies, xyz, quat, frames, events, series, info


# ----------------------------------------------------------------------------- 絞りと瞳
def build_pupil_tab(rec):
    th = rec["theta"]
    n_ = len(th)
    system, para, zv = rec["system"], rec["para"], rec["zv"]
    z_img = zv[-1] + para["bfl"]
    sc = Scene(n_, -60.0, z_img + 30)
    _stage_colors(sc)
    L = dict(L_D)
    _lens_body(sc, "lens1", L, np.zeros(3))
    _lens_body(sc, "lens2", L, np.array([zv[3], 0, 0]))
    sc.add("stop", ring_x(STOP_R, 14.0, 0.8), (70, 72, 80), xyz=np.array([zv[2], 0, 0]),
           label=T("開口絞り(半径 4 mm)", "aperture stop (radius 4 mm)"))
    sc.add("stop_post", cylinder_z(1.8, BENCH_TOP, -14.0), (120, 124, 132), xyz=np.array([zv[2], 0, 0]))
    sc.add("entrance_pupil", ring_x(para["ep_radius"], para["ep_radius"] + 0.7, 0.5), U8(STAGE_RGB[0]),
           xyz=np.array([para["ep_position"], 0, 0]), label=T("入射瞳(前から見た絞りの像)", "entrance pupil (the stop seen from the front)"))
    sc.add("exit_pupil", ring_x(para["xp_radius"], para["xp_radius"] + 0.7, 0.5), U8(STAGE_RGB[0]),
           xyz=np.array([zv[-1] + para["xp_position"], 0, 0]), label=T("射出瞳(後ろから見た絞りの像)", "exit pupil (the stop seen from the back)"))
    sc.add("sensor", box_mesh((-0.8, -16, -16), (0.8, 16, 16)), (60, 70, 60), xyz=np.array([z_img + 1.0, 0, 0]),
           label=T("像面(センサー)", "image plane (sensor)"))
    sc.add("sensor_post", cylinder_z(1.8, BENCH_TOP, -16.0), (120, 124, 132), xyz=np.array([z_img + 1.0, 0, 0]))
    pimg = np.full((n_, 3), np.nan)
    for k, fr in enumerate(rec["frames"]):
        _draw_paths(sc, k, ray_paths(system, fr["tr"], 0.0), "s2", "block", stop_index=2)
        cr = fr["chief"]
        if cr["valid"]:
            pts = cr["points"]
            for i in range(len(pts) - 1):
                if not (1 <= i <= len(system["surfaces"]) and rt.refractive_index(system["surfaces"][i - 1]["n"], WL_UM) > 1.0001):
                    sc.seg(k, "s1", to_world(pts[i], 0.0), to_world(pts[i + 1], 0.0))
            pimg[k] = to_world(pts[-1], 0.0) + np.array([-1.2, 0, 0])
    _marker(sc, "image_point", 1.5, U8(STAGE_RGB[3]), pimg, label=T("像の点(主光線が像面に届く所)", "image point (where the chief ray lands)"))
    bodies, xyz, quat, nrods = sc.build()
    heads = band_heads(["paraxial_trace", "chief_ray", "ray_bundle", "relative_illumination"])
    frames = []
    f = para["efl"]
    for k, fr in enumerate(rec["frames"]):
        a = th[k]
        c1 = Canvas((-10, z_img + 5), (-14, 14))
        c1.line(-10, 0, z_img + 5, 0, (0.3, 0.3, 0.32))
        for z in (zv[0], zv[3]):
            c1.line(z + 2, -L["ap"], z + 2, L["ap"], (0.67, 0.84, 0.93))
        c1.line(zv[2], STOP_R, zv[2], 13, (0.6, 0.6, 0.6), 0.8)
        c1.line(zv[2], -13, zv[2], -STOP_R, (0.6, 0.6, 0.6), 0.8)
        for z, r in ((para["ep_position"], para["ep_radius"]), (zv[-1] + para["xp_position"], para["xp_radius"])):
            c1.line(z, -r, z, r, STAGE_RGB[0], 0.8)
        c1.textpx("EP r %.2f at %.1f mm" % (para["ep_radius"], para["ep_position"]), 3, 2, STAGE_RGB[0], 8)
        c1.textpx("F/%.2f  f %.1f" % (para["fno"], f), PW - 3, PH - 2, (0.7, 0.7, 0.7), 8, "rb")
        c2 = Canvas((0, FIELD_MAX + 1), (0, 22))
        _graph_axes(c2, xt=(10, 20), yt=(10, 20))
        tt = np.linspace(0, FIELD_MAX + 1, 60)
        c2.poly(tt, f * np.tan(np.radians(tt)), (0.85, 0.85, 0.85))
        for j in range(k + 1):
            if np.isfinite(rec["y_chief"][j]):
                c2.dot(th[j], rec["y_chief"][j], 0.7, STAGE_RGB[1])
        c2.textpx("y = %.2f mm (f·tanθ %.2f)" % (rec["y_chief"][k], rec["y_tan"][k]), 3, 2, STAGE_RGB[1], 8)
        c3 = Canvas((-1.25 * PW / PH, 1.25 * PW / PH), (-1.25, 1.25))
        ang = np.linspace(0, 2 * np.pi, 80)
        c3.poly(np.cos(ang), np.sin(ang), (0.45, 0.45, 0.45))
        pu, ok = fr["bundle"]["pupil"], fr["bundle"]["valid"]
        for (px, py), v in zip(pu, ok):
            c3.dot(px, py, 1.3, STAGE_RGB[2] if v else (0.90, 0.45, 0.45))
        c3.textpx("pass %d%%" % round(100 * rec["vig"][k]), 3, 2, STAGE_RGB[2], 9)
        c4 = Canvas((0, FIELD_MAX + 1), (0.0, 1.05))
        _graph_axes(c4, xt=(10, 20), yt=(0.5, 1.0))
        c4.poly(th, rec["cos4"], (0.85, 0.85, 0.85))
        for tq, rq in zip(rec["theta_noclip"], rec["ri_noclip"]):
            c4.dot(tq, rq, 0.8, (0.55, 0.55, 0.60))
        for j in range(k + 1):
            if np.isfinite(rec["ri_real"][j]):
                c4.dot(th[j], rec["ri_real"][j], 0.7, STAGE_RGB[3])
        if np.isfinite(rec["ri_real"][k]):
            c4.dot(a, rec["ri_real"][k], 2.0, STAGE_RGB[3])
        c4.textpx("E/E0", 3, 2, (0.7, 0.7, 0.7), 8)
        c4.textpx("θ [°]", PW - 3, PH - 2, (0.7, 0.7, 0.7), 8, "rb")
        ri = rec["ri_real"][k]
        l1 = ("E/E0 = cos⁴θ = cos⁴(%.1f°) = %.3f   real rays: area %.3f × stretch %.3f = %s (%s)"
              % (a, rec["cos4"][k], rec["ri_area"][k], rec["ri_stretch"][k], fmt(ri, 3),
                 ("%+.1f%%" % (100 * (ri - rec["cos4"][k]) / rec["cos4"][k])) if np.isfinite(ri) else "—"))
        frames.append(band_frame([c1.img, c2.img, c3.img, c4.img], active_stage(k), heads,
                                 [(l1, STAGE_RGB[3])]))
    t = rec["t"]
    kv = int(np.argmax(rec["vig"] < 0.999))
    klim = int(np.argmax(rec["ri_real"] < 0.8 * rec["cos4"]))
    events = [{"t": float(t[0]), "label": T("θ = 0: 光軸の上", "θ = 0: on axis")},
              {"t": float(t[kv]), "label": T("ケラレ始め(レンズの縁が光束を切る)", "vignetting starts (a lens rim clips the beam)")},
              {"t": float(t[klim]), "label": T("限界: cos⁴ より 20% 暗い", "limit: 20% darker than cos⁴")}]
    series = [{"label": T("θ", "θ"), "values": th, "lo": 0, "hi": FIELD_MAX, "color": "#9e9e9e", "unit": "°",
               "decimals": 2},
              {"label": T("cos⁴θ(relative_illumination)", "cos⁴θ (relative_illumination)"), "values": rec["cos4"],
               "lo": 0, "hi": 1.05, "color": "#e0e0e0", "unit": "", "decimals": 3},
              {"label": T("実光線の周辺光量", "real-ray illumination"), "values": rec["ri_real"], "lo": 0, "hi": 1.05,
               "color": STAGE_HEX[3], "unit": "", "decimals": 3},
              {"label": T("ray_bundle の通る割合", "ray_bundle pass fraction"), "values": rec["vig"], "lo": 0, "hi": 1.05,
               "color": STAGE_HEX[2], "unit": "", "decimals": 3},
              {"label": T("主光線の像高(chief_ray)", "chief-ray height (chief_ray)"), "values": rec["y_chief"], "lo": 0,
               "hi": 25, "color": STAGE_HEX[1], "unit": "mm", "decimals": 2}]
    info = {"nrods": nrods, "kv": kv, "klim": klim}
    return bodies, xyz, quat, frames, events, series, info


# =========================================================================== #
# ページ                                                                       #
# =========================================================================== #
VIEW = {"az": -1.5708 + 0.35, "el": 0.32}
# 台が長い(物体〜スクリーンが 500 mm 超)タブは、斜めから近づくと手前の台だけが大きく写り部品が奥で小さくなる。
# 正面寄り・少し遠くから見る(遠近の歪みを抑える)。
VIEW_LONG = {"az": -1.5708 + 0.12, "el": 0.22}


def _pane(frames, ja, en):
    return {"label": T(ja, en), "frames": np.stack(frames), "png": True}


def run_all():
    """4 タブの記録(op の値・理論値・光線)。"""
    return {"imaging": run_imaging(), "lensmaker": run_lensmaker(), "doublet": run_doublet(), "pupils": run_pupils()}


def summary(res) -> dict:
    """門と説明に使う数字(実測)。"""
    A, B, C, D = res["imaging"], res["lensmaker"], res["doublet"], res["pupils"]
    k3 = 0
    k2 = int(np.argmin(np.abs(A["a"] - 2 * A["f"])))
    relA = np.abs(A["b_ray"] - A["b_thin"]) / np.abs(A["b_thin"])
    devB = np.abs(B["f_thick"] - B["f_thin"]) / B["f_thin"]
    ok = np.isfinite(C["f_para"]) & np.isfinite(C["f_abcd"])
    noclip_ok = D["theta_noclip"] <= 10.0 + 1e-9
    cos4_nc = np.cos(np.radians(D["theta_noclip"])) ** 4
    return {
        "A_f": A["f"], "A_para_vs_thin": float(np.max(np.abs(A["b_para"] - A["b_thin"]) / np.abs(A["b_thin"]))),
        "A_ray_3f": float(relA[k3]), "A_ray_2f": float(relA[k2]), "A_m_2f": float(A["m_thin"][k2]),
        "B_thick_vs_para": float(np.max(np.abs(B["f_thick"] - B["f_para"]) / B["f_para"])),
        "B_dev_R300": float(devB[0]), "B_dev_R24": float(devB[NF_B1 - 1]),
        "B_ray_R24": float(B["f_ray"][NF_B1 - 1]), "B_thin_R24": float(B["f_thin"][NF_B1 - 1]),
        "B_thick_R24": float(B["f_thick"][NF_B1 - 1]),
        "C_abcd_vs_para": float(np.max(np.abs(C["f_abcd"][ok] - C["f_para"][ok]) / np.abs(C["f_para"][ok]))),
        "C_formula_vs_abcd": float(np.max(np.abs(C["f_formula"][ok] - C["f_abcd"][ok]) / np.abs(C["f_abcd"][ok]))),
        "C_det": float(np.max(np.abs(C["det"] - 1.0))), "C_afocal_d": C["f1"] + C["f2"],
        "D_ep": (D["para"]["ep_position"], D["para"]["ep_radius"]), "D_stop_hit": float(np.nanmax(np.abs(D["stop_hit"]))),
        "D_noclip_10deg": float(np.max(np.abs(D["ri_noclip"][noclip_ok] - cos4_nc[noclip_ok]) / cos4_nc[noclip_ok])),
        "D_noclip_max": float(np.nanmax((D["ri_noclip"] - cos4_nc) / cos4_nc)),
        "D_ri_end": float(D["ri_real"][-1]), "D_cos4_end": float(D["cos4"][-1]), "D_theta_end": float(D["theta"][-1]),
        "D_vig_end": float(D["vig"][-1]),
    }


# =========================================================================== #
# 学習用の型(2026-10-25): 門の値 → checks / lesson / axis                     #
# =========================================================================== #
def _stopped_down_rel(a_over_f_list=(3.0, 2.0, 1.5)):
    """独立経路: 半径の 5% の輪だけの実光線が集まる位置と thin_lens の像の位置の相対差(最大)。"""
    Ls = LENS_A
    n = n_of(Ls["glass"])
    worst = 0.0
    for a_over_f in a_over_f_list:
        p0 = rt.paraxial_trace(rt.lens_system(singlet(Ls["R1"], Ls["R2"], Ls["t"], Ls["ap"], n), stop=0, object_mm=200.0))
        f, xH, xH2 = p0["efl"], p0["pp_front"], Ls["t"] + p0["pp_rear"]
        a = a_over_f * f
        system = rt.lens_system(singlet(Ls["R1"], Ls["R2"], Ls["t"], Ls["ap"], n), stop=0, object_mm=a - xH)
        tip = np.array([0.0, 0.0, -(a - xH)])
        q = [np.array([0.05 * Ls["ap"] * math.cos(t), 0.05 * Ls["ap"] * math.sin(t), 0.0]) for t in np.linspace(0, 6.2, 8)]
        D = np.array([x - tip for x in q])
        D /= np.linalg.norm(D, axis=1, keepdims=True)
        tr = rt.trace_rays(system, np.tile(tip, (len(D), 1)), D, image_mm=50.0)
        ns = len(system["surfaces"])
        p = nearest_point(tr["points"][:, ns], tr["dirs"][:, ns])
        b = optics.thin_lens(focal_mm=f, object_mm=a)["image_mm"]
        worst = max(worst, abs((p[2] - xH2) - b) / b)
    return float(worst)


def _low_ray_focus_diff(gaps=(10.0, 60.0, 200.0)):
    """独立経路: 高さ 0.01 mm の実光線が光軸を横切る z と paraxial_trace の F′ の差(mm、2 枚組の間隔 3 通り)。"""
    n = n_of(L1_C["glass"])
    worst = 0.0
    for g in gaps:
        surf = singlet(L1_C["R1"], L1_C["R2"], L1_C["t"], L1_C["ap"], n, nxt=g) + \
            singlet(L2_C["R1"], L2_C["R2"], L2_C["t"], L2_C["ap"], n, nxt=100.0)
        system = rt.lens_system(surf, stop=0)
        para = rt.paraxial_trace(system)
        z_last = L1_C["t"] + g + L2_C["t"]
        O, D = collimated([0.01])
        tr = rt.trace_rays(system, O, D)
        zc = axis_crossing(tr["points"][0, 4], tr["dirs"][0, 4])
        worst = max(worst, abs(zc - (z_last + para["bfl"])))
    return float(worst)


def gates(res) -> dict:
    """門の値(テストと同じ量)。checks・lesson の数字はすべてここから引く(手で書いた数字は入れない)。"""
    g = dict(summary(res))
    A, B, C, D = res["imaging"], res["lensmaker"], res["doublet"], res["pupils"]
    # 薄レンズの結像
    g["A_resid"] = float(np.max(np.abs(1.0 / A["a"] + 1.0 / A["b_thin"] - 1.0 / A["f"])))
    k2 = int(np.argmin(np.abs(A["a"] - 2 * A["f"])))
    g["A_m_2f_err"] = float(abs(A["m_thin"][k2] + 1.0))
    g["A_stopdown_rel"] = _stopped_down_rel()
    rel = np.abs(A["b_ray"] - A["b_thin"]) / np.abs(A["b_thin"])
    far = A["a"] >= 2 * A["f"] - 1e-9
    near = (A["a"] > A["f"]) & (A["a"] < 1.3 * A["f"])
    g["A_edge_far"], g["A_edge_near"] = float(rel[far].max()), float(rel[near].max())
    g["A_virtual_ok"] = bool(np.all(A["b_thin"][A["a"] > A["f"]] > 0) and np.all(A["b_thin"][A["a"] < A["f"]] < 0))
    g["A_a_range_f"] = (float(A["a"][0] / A["f"]), float(A["a"][-1] / A["f"]))
    # レンズメーカーの式
    g["B_n_lib"] = float(max(abs(n - materials.material_optical_constants(m, WL_NM)["n"]) for m, n in zip(B["mat"], B["n"])))
    phase2 = B["mat"][NF_B1:]
    kk = [NF_B1 + phase2.index(m) for m in MATS_B]
    g["B_f_by_mat"] = {m: float(B["f_thick"][k]) for m, k in zip(MATS_B, kk)}
    g["B_n_by_mat"] = {m: float(B["n"][k]) for m, k in zip(MATS_B, kk)}
    g["B_f_shrinks"] = bool(np.all(np.diff(B["f_thick"][kk]) < 0))
    g["B_thick_R24_mm"] = float(B["thick"][NF_B1 - 1])
    # 2 枚組と ABCD
    fin = np.isfinite(C["x_F"])
    g["C_xF_mm"] = float(np.max(np.abs(C["x_F"][fin] - C["x_F_para"][fin])))
    g["C_low_ray_mm"] = _low_ray_focus_diff()
    P = 1.0 / C["f_abcd"]
    k = int(np.argmax(C["d_pp"] > C["f1"] + C["f2"]))
    g["C_power_flips"] = bool(np.all(np.diff(P) < 0) and P[k - 1] > 0 > P[k])
    g["C_d_range"] = (float(C["d_pp"][0]), float(C["d_pp"][-1]))
    g["C_f_first"] = float(C["f_abcd"][0])
    # 絞りと瞳
    cr = rt.chief_ray(D["system"], field=0.5)
    p, d = cr["points"][0], cr["dirs"][0]
    g["D_ep_cross_mm"] = float(abs(p[2] - p[1] / d[1] * d[2] - D["para"]["ep_position"]))
    g["D_xp_sym"] = float(abs(D["para"]["xp_position"] + D["para"]["ep_position"]))
    g["D_cos4_op"] = float(np.max(np.abs(D["cos4"] - np.cos(np.radians(D["theta"])) ** 4)))
    g["D_near_axis"] = float(abs(D["ri_real"][1] - D["cos4"][1]))
    g["D_theta_near"] = float(D["theta"][1])
    g["D_ratio_end"] = float(D["ri_real"][-1] / D["cos4"][-1])
    return g


def _e(x):
    """門の値の印字(0 はそのまま 0、他は指数 1 桁)。"""
    return "0" if x == 0 else "%.1e" % x


def _row(what_ja, what_en, criterion, result, ok):
    """checks の 1 行。ok は門の値と基準の比較で決める(手で True と書かない)。"""
    return {"what": T(what_ja, what_en), "criterion": criterion, "result": result, "ok": bool(ok)}


def textbook_checks(g):
    """各タブの「確かめた項目 / 基準 / 結果」。値は :func:`gates` の値(tests/test_lens_system_anim3d.py と同じ基準)。

    同じ式から出した値どうしの比較は「規約の確認」と書き、独立した経路(実光線)の検算を必ず 1 行入れる。
    """
    yes, no = T("成立", "holds"), T("不成立", "fails")
    return {
        "imaging": [
            _row("像の位置 b: thin_lens(薄レンズの式)と paraxial_trace(厚いレンズの近軸追跡、主点から測る)、全コマ",
                 "image distance b: thin_lens (thin-lens formula) vs paraxial_trace (thick-lens paraxial trace from the principal planes), every frame",
                 "< 1e-9", _e(g["A_para_vs_thin"]), g["A_para_vs_thin"] < 1e-9),
            _row("独立経路: 半径の 5% の実光線(trace_rays)が集まる位置と thin_lens の b(a = 3f / 2f / 1.5f)",
                 "independent path: where real rays at 5% of the radius (trace_rays) meet vs thin_lens b (a = 3f / 2f / 1.5f)",
                 "< 1e-3", _e(g["A_stopdown_rel"]), g["A_stopdown_rel"] < 1e-3),
            _row("規約の確認: thin_lens の b が 1/a + 1/b = 1/f を満たす(同じ式の残差)",
                 "convention check: thin_lens b satisfies 1/a + 1/b = 1/f (residual of the same formula)",
                 "< 1e-12", _e(g["A_resid"]), g["A_resid"] < 1e-12),
            _row("規約の確認: a = 2f の倍率 m と −1 の差", "convention check: magnification m at a = 2f vs −1",
                 "< 1e-12", _e(g["A_m_2f_err"]), g["A_m_2f_err"] < 1e-12),
            _row("a > f で実像(b > 0)、a < f で虚像(b < 0)", "a > f gives a real image (b > 0), a < f a virtual one (b < 0)",
                 T("全コマ", "every frame"), yes if g["A_virtual_ok"] else no, g["A_virtual_ok"]),
            _row("縁(半径の 0.45)の実光線と thin_lens の差: a ≥ 2f", "edge rays (0.45 of the radius) vs thin_lens: a ≥ 2f",
                 "< 0.02", "%.4f" % g["A_edge_far"], g["A_edge_far"] < 0.02),
            _row("縁の実光線と thin_lens の差: f < a < 1.3f(限界が見えること)",
                 "edge rays vs thin_lens: f < a < 1.3f (the limit must show)",
                 "> 0.10", "%.3f" % g["A_edge_near"], g["A_edge_near"] > 0.10)],
        "lensmaker": [
            _row("独立経路: 焦点距離を thick_lens(厚肉の閉形式)と paraxial_trace(面ごとの近軸追跡)で、全コマ",
                 "independent path: focal length from thick_lens (closed form) vs paraxial_trace (surface-by-surface paraxial trace), every frame",
                 "< 1e-12", _e(g["B_thick_vs_para"]), g["B_thick_vs_para"] < 1e-12),
            _row("規約の確認: 光線追跡に渡した n と material_optical_constants(d 線)の n",
                 "convention check: n given to the ray trace vs material_optical_constants (d line)",
                 "= 0", _e(g["B_n_lib"]), g["B_n_lib"] == 0.0),
            _row("R = 50 mm で n が上がると f が縮む(材料 6 種、thick_lens)",
                 "at R = 50 mm, f shrinks as n rises (6 materials, thick_lens)",
                 T("単調に減る", "decreases monotonically"), yes if g["B_f_shrinks"] else no, g["B_f_shrinks"]),
            _row("薄肉の式のずれ(R = 300 mm)", "thin-lens formula error (R = 300 mm)",
                 "< 0.002", "%.5f" % g["B_dev_R300"], g["B_dev_R300"] < 0.002),
            _row("薄肉の式のずれ(R = 24 mm、限界が見えること)", "thin-lens formula error (R = 24 mm; the limit must show)",
                 "> 0.05", "%.4f" % g["B_dev_R24"], g["B_dev_R24"] > 0.05)],
        "doublet": [
            _row("焦点距離: abcd_matrix(主点から測った薄レンズ 2 枚)と paraxial_trace(実の処方)、全コマ",
                 "focal length: abcd_matrix (two thin lenses from the principal planes) vs paraxial_trace (real prescription), every frame",
                 "< 1e-9", _e(g["C_abcd_vs_para"]), g["C_abcd_vs_para"] < 1e-9),
            _row("後ろの焦点 F′ の位置: ABCD と paraxial_trace", "rear focus F′ position: ABCD vs paraxial_trace",
                 "< 1e-6 mm", "%s mm" % _e(g["C_xF_mm"]), g["C_xF_mm"] < 1e-6),
            _row("独立経路: 高さ 0.01 mm の実光線(trace_rays)が光軸を横切る所と paraxial_trace の F′(間隔 3 通り)",
                 "independent path: where a 0.01 mm real ray (trace_rays) crosses the axis vs paraxial_trace F′ (3 spacings)",
                 "< 1e-3 mm", "%s mm" % _e(g["C_low_ray_mm"]), g["C_low_ray_mm"] < 1e-3),
            _row("1/f1 + 1/f2 − d/(f1 f2) と abcd_matrix の f", "1/f1 + 1/f2 − d/(f1 f2) vs abcd_matrix f",
                 "< 1e-9", _e(g["C_formula_vs_abcd"]), g["C_formula_vs_abcd"] < 1e-9),
            _row("det M = 1(abcd_trace)", "det M = 1 (abcd_trace)", "< 1e-12", _e(g["C_det"]), g["C_det"] < 1e-12),
            _row("屈折力 1/f が d について単調に減り、d = f1 + f2 で正から負へ",
                 "power 1/f decreases with d and changes sign at d = f1 + f2",
                 T("成立すること", "must hold"), yes if g["C_power_flips"] else no, g["C_power_flips"])],
        "pupils": [
            _row("主光線(chief_ray)が絞りの面を通る高さ、全コマ", "height of the chief ray (chief_ray) at the stop, every frame",
                 "< 1e-6 mm", "%s mm" % _e(g["D_stop_hit"]), g["D_stop_hit"] < 1e-6),
            _row("独立経路: 画角 0.5° の主光線を物体側へ延ばして光軸と交わる所と、paraxial_trace の入射瞳",
                 "independent path: the 0.5° chief ray extended backwards to the axis vs paraxial_trace entrance pupil",
                 "< 0.05 mm", "%.4f mm" % g["D_ep_cross_mm"], g["D_ep_cross_mm"] < 0.05),
            _row("規約の確認: 対称な系で射出瞳 = 入射瞳の鏡像", "convention check: in a symmetric system the exit pupil mirrors the entrance pupil",
                 "< 1e-9 mm", "%s mm" % _e(g["D_xp_sym"]), g["D_xp_sym"] < 1e-9),
            _row("規約の確認: relative_illumination と cos⁴θ(同じ式)", "convention check: relative_illumination vs cos⁴θ (same formula)",
                 "< 1e-12", _e(g["D_cos4_op"]), g["D_cos4_op"] < 1e-12),
            _row("縁で切らない実光線の明るさと cos⁴(10° まで)", "real-ray illumination without rim clipping vs cos⁴ (up to 10°)",
                 "< 0.01", "%.4f" % g["D_noclip_10deg"], g["D_noclip_10deg"] < 0.01),
            _row("光軸の近く(%.2f°)の実光線の明るさと cos⁴" % g["D_theta_near"],
                 "real-ray illumination near the axis (%.2f°) vs cos⁴" % g["D_theta_near"],
                 "< 0.01", "%.4f" % g["D_near_axis"], g["D_near_axis"] < 0.01),
            _row("限界: レンズの縁で切るとき、%.0f° の実光線の明るさ ÷ cos⁴ が 1 の 10%% 以内か" % g["D_theta_end"],
                 "limit: with the rims clipping, is real-ray illumination ÷ cos⁴ at %.0f° within 10%% of 1?" % g["D_theta_end"],
                 "0.9–1.1", "%.3f" % g["D_ratio_end"], 0.9 <= g["D_ratio_end"] <= 1.1)],
    }


def textbook_lessons(res, g):
    """各タブの学習用の型(問い → 予想 → 再生 → 式 → 限界)。答えの説明の数字は :func:`gates` の値。"""
    C = res["doublet"]
    a0, a1 = g["A_a_range_f"]
    nb = g["B_n_by_mat"]
    return {
        "imaging": {
            "question": T("凸レンズの前の物体を、%.1ff の所から %.1ff までレンズに近づけていく。スクリーンに映る像はどうなる?" % (a0, a1),
                          "An object in front of a convex lens moves from %.1ff to %.1ff. What happens to the image on the screen?" % (a0, a1)),
            "choices": [T("近づくほど小さくなる", "It gets smaller as the object comes closer"),
                        T("大きくなりながら遠ざかり、f より近いとスクリーンに映らなくなる", "It grows and moves away; inside f nothing forms on the screen"),
                        T("大きさは変わらず、位置だけ動く", "Same size; only its position moves")],
            "answer": 1,
            "explain": T("1/a + 1/b = 1/f から、a = 2f で b = 2f・倍率 m = %+.3f(同じ大きさで上下さかさま)。a が f に近づくと b は"
                         "どんどん大きくなり、a < f では b < 0: 光は集まらず、レンズ越しに見える正立の虚像(虫めがね)になる。"
                         "このレンズの f = %.2f mm(paraxial_trace)。" % (g["A_m_2f"], g["A_f"]),
                         "From 1/a + 1/b = 1/f: at a = 2f, b = 2f and m = %+.3f (same size, upside down). As a nears f, b grows "
                         "without bound; for a < f, b < 0: the light no longer meets and you see an upright virtual image through "
                         "the lens (a magnifier). This lens has f = %.2f mm (paraxial_trace)." % (g["A_m_2f"], g["A_f"])),
            "formula": T("1/a + 1/b = 1/f(a, b は主点から測る)\n倍率: m = −b / a\nb < 0 なら虚像(正立)",
                         "1/a + 1/b = 1/f (a and b measured from the principal planes)\nmagnification: m = −b / a\n"
                         "b < 0 means a virtual (upright) image"),
            "limit": None,
        },
        "lensmaker": {
            "question": T("両凸レンズの面の曲率半径 R を 300 mm から 24 mm まで小さくする(強く曲げる)。焦点距離と薄肉の式はどうなる?",
                          "Make the surfaces of a biconvex lens more curved: R from 300 mm down to 24 mm. What happens to the focal "
                          "length and to the thin-lens formula?"),
            "choices": [T("焦点距離は短くなり、薄肉の式はずっと当たる", "f gets shorter and the thin-lens formula stays exact"),
                        T("焦点距離は短くなるが、強く曲げるほど薄肉の式から外れる", "f gets shorter, but the more curved, the further it drifts from the thin-lens formula"),
                        T("焦点距離は長くなる", "f gets longer")],
            "answer": 1,
            "explain": T("1/f は (1/R1 − 1/R2) に比例するので、R を小さくすると f は短くなる。ただし強く曲げたレンズは厚くなる"
                         "(R = 24 mm で %.1f mm)。薄肉の式のずれは R = 300 mm で %.2f%%、R = 24 mm で %.1f%%(薄肉 %.1f mm、"
                         "厚肉 %.1f mm)。後半の材料の入れ替えでは、R = 50 mm のまま n が水 %.4f → ランタン系 %.4f と上がり、"
                         "f は %.1f mm → %.1f mm に縮む。" % (
                             g["B_thick_R24_mm"], 100 * g["B_dev_R300"], 100 * g["B_dev_R24"], g["B_thin_R24"], g["B_thick_R24"],
                             nb["WATER"], nb["N-LASF9"], g["B_f_by_mat"]["WATER"], g["B_f_by_mat"]["N-LASF9"]),
                         "1/f is proportional to (1/R1 − 1/R2), so a smaller R gives a shorter f. But a strongly curved lens is "
                         "thick (%.1f mm at R = 24 mm). The thin-lens error is %.2f%% at R = 300 mm and %.1f%% at R = 24 mm "
                         "(thin %.1f mm, thick %.1f mm). In the second half, at R = 50 mm, n goes from water %.4f to the "
                         "lanthanum glass %.4f and f shrinks from %.1f mm to %.1f mm." % (
                             g["B_thick_R24_mm"], 100 * g["B_dev_R300"], 100 * g["B_dev_R24"], g["B_thin_R24"], g["B_thick_R24"],
                             nb["WATER"], nb["N-LASF9"], g["B_f_by_mat"]["WATER"], g["B_f_by_mat"]["N-LASF9"])),
            "formula": T("薄肉: 1/f = (n − 1)(1/R1 − 1/R2)\n厚肉: 1/f = (n − 1)[1/R1 − 1/R2 + (n − 1) t / (n R1 R2)]\n"
                         "両凸(R1 = R, R2 = −R)の薄肉: f = R / (2(n − 1))",
                         "thin lens: 1/f = (n − 1)(1/R1 − 1/R2)\nthick lens: 1/f = (n − 1)[1/R1 − 1/R2 + (n − 1) t / (n R1 R2)]\n"
                         "biconvex (R1 = R, R2 = −R), thin: f = R / (2(n − 1))"),
            "limit": None,
        },
        "doublet": {
            "question": T("f1 = %.1f mm と f2 = %.1f mm の凸レンズ 2 枚の間隔を広げていく。全体の焦点距離はどうなる?" % (C["f1"], C["f2"]),
                          "Two convex lenses, f1 = %.1f mm and f2 = %.1f mm, move apart. What happens to the focal length of the pair?"
                          % (C["f1"], C["f2"])),
            "choices": [T("間隔によらず一定", "It stays the same whatever the gap"),
                        T("短くなり続ける", "It keeps getting shorter"),
                        T("長くなり、d = f1 + f2 で無限大(望遠鏡)、その先は負になる", "It grows, becomes infinite at d = f1 + f2 (a telescope), then turns negative")],
            "answer": 2,
            "explain": T("屈折力 1/f = 1/f1 + 1/f2 − d/(f1 f2) は間隔 d の一次式で、d が増えると減る。d = %.1f mm(主点の間)で f = %.1f mm、"
                         "d = f1 + f2 = %.1f mm で屈折力が 0、平行光が平行光のまま出る(望遠鏡)。その先は f < 0(発散)。"
                         % (g["C_d_range"][0], g["C_f_first"], g["C_afocal_d"]),
                         "The power 1/f = 1/f1 + 1/f2 − d/(f1 f2) is linear in the gap d and falls as d grows. At d = %.1f mm "
                         "(between principal planes) f = %.1f mm; at d = f1 + f2 = %.1f mm the power is zero and parallel light "
                         "leaves parallel (a telescope). Beyond that f < 0 (diverging)." % (g["C_d_range"][0], g["C_f_first"], g["C_afocal_d"])),
            "formula": T("1/f = 1/f1 + 1/f2 − d / (f1 f2)\nM = [[1, 0], [−1/f2, 1]] · [[1, d], [0, 1]] · [[1, 0], [−1/f1, 1]]\n"
                         "f = −1 / C(M = [[A, B], [C, D]])、det M = AD − BC = 1",
                         "1/f = 1/f1 + 1/f2 − d / (f1 f2)\nM = [[1, 0], [−1/f2, 1]] · [[1, d], [0, 1]] · [[1, 0], [−1/f1, 1]]\n"
                         "f = −1 / C (M = [[A, B], [C, D]]), det M = AD − BC = 1"),
            "limit": None,
        },
        "pupils": {
            "question": T("斜めから入る平行光の角度 θ を 0° から %.0f° まで上げる。画面の端の明るさは、教科書の cos⁴θ 則どおりに落ちる?" % FIELD_MAX,
                          "Raise the angle θ of the incoming parallel light from 0° to %.0f°. Does the brightness at the edge of "
                          "the picture fall exactly as the textbook cos⁴θ law says?" % FIELD_MAX),
            "choices": [T("いつも cos⁴θ どおり", "Always exactly cos⁴θ"),
                        T("レンズの縁が光束を切り始めると、cos⁴θ よりずっと暗くなる", "Once a lens rim starts clipping the beam, it gets much darker than cos⁴θ"),
                        T("角度によらず同じ明るさ", "Same brightness at every angle")],
            "answer": 1,
            "explain": T("縁で切らない場合、10° までは実光線の明るさが cos⁴ と %.1f%% 以内で合う。縁で切ると %.0f° で cos⁴ の %.3f に"
                         "対し実光線は %.3f(比 %.3f)。ray_bundle で瞳を通る光線は %.0f%% しか残らない(ケラレ)。"
                         % (100 * g["D_noclip_10deg"], g["D_theta_end"], g["D_cos4_end"], g["D_ri_end"], g["D_ratio_end"], 100 * g["D_vig_end"]),
                         "Without rim clipping, real-ray illumination matches cos⁴ within %.1f%% up to 10°. With the rims, at "
                         "%.0f° cos⁴ gives %.3f but the real rays give %.3f (ratio %.3f); only %.0f%% of the rays from ray_bundle "
                         "get through (vignetting)." % (100 * g["D_noclip_10deg"], g["D_theta_end"], g["D_cos4_end"], g["D_ri_end"],
                                                          g["D_ratio_end"], 100 * g["D_vig_end"])),
            "formula": T("cos⁴ 則: E/E0 = cos⁴θ\n実光線: E/E0 = [A(θ) / A(0)] · f² sinθ / (y dy/dθ)\n"
                         "A = 像まで届く光束の断面積、y = 主光線の像高(≈ f tanθ)",
                         "cos⁴ law: E/E0 = cos⁴θ\nreal rays: E/E0 = [A(θ) / A(0)] · f² sinθ / (y dy/dθ)\n"
                         "A = cross-section of the beam reaching the image, y = chief-ray image height (≈ f tanθ)"),
            "limit": None,
        },
    }


#: 説明文(text)の限界の段を lesson の「⑤ 限界」に移すときの足し書き(式が仮定していること)。
LIMIT_EXTRA = {
    "imaging": T("式は単色(d 線)の光で、収差は入れていない。",
                 "The formula uses one colour (the d line) and leaves out aberrations."),
    "lensmaker": T("屈折率は d 線の 1 つだけで、色による焦点のずれ(色収差)は入れていない。",
                   "Only the d-line index is used; the colour-dependent focus shift (chromatic aberration) is left out."),
    "doublet": T("d は頂点の間でなく主点の間で測る(頂点の間で測ると式が合わない)。",
                 "d is measured between the principal planes, not the vertices (vertex spacing does not fit the formula)."),
    "pupils": T("物体側の明るさ(放射輝度)は一様と仮定している。",
                "The object side is assumed to have uniform radiance."),
}


def split_limit(text):
    """説明文の「限界:」の段を切り出す → (説明, 限界)。ja は「限界: 」、en は「Limit: 」でちょうど 1 回ずつ。"""
    head, tail = {}, {}
    for lang, mark in (("ja", "限界: "), ("en", "Limit: ")):
        s = text[lang]
        if s.count(mark) != 1:
            raise ValueError("説明文の %s に「%s」がちょうど 1 回ない(%d 回)" % (lang, mark, s.count(mark)))
        a, b = s.split(mark)
        head[lang], tail[lang] = a.rstrip(), b.strip()
    return T(head["ja"], head["en"]), T(tail["ja"], tail["en"])


def textbook_axes(res):
    """各タブの時間つまみの読み(物理量)。"""
    A, B, C, D = res["imaging"], res["lensmaker"], res["doublet"], res["pupils"]
    return {
        "imaging": {"values": np.asarray(A["a"], float),
                    "segments": [{"k": 0, "label": T("物体の位置 a(前の主点から)", "object distance a (from the front principal plane)"),
                                  "unit": "mm", "decimals": 1}]},
        "lensmaker": {"values": np.r_[B["R"][:NF_B1], B["n"][NF_B1:]],
                      "segments": [{"k": 0, "label": T("面の曲率半径 R(クラウンガラス)", "surface radius R (crown glass)"),
                                    "unit": "mm", "decimals": 0},
                                   {"k": NF_B1, "label": T("屈折率 n(d 線、R = 50 mm のまま材料を替える)",
                                                           "index n (d line; material changes at R = 50 mm)"),
                                    "unit": "", "decimals": 4}]},
        "doublet": {"values": np.asarray(C["d_pp"], float),
                    "segments": [{"k": 0, "label": T("2 枚の間隔 d(主点の間)", "lens spacing d (between principal planes)"),
                                  "unit": "mm", "decimals": 1}]},
        "pupils": {"values": np.asarray(D["theta"], float),
                   "segments": [{"k": 0, "label": T("光の入射角(画角)θ", "field angle θ"), "unit": "°", "decimals": 1}]},
    }


def attach_lessons(tabs, res, g):
    """タブに checks・lesson・axis を付ける。説明文の限界の段は lesson の ⑤ 限界へ移す。

    ★ok:false の行がある回だけ badge を limit にする(全部通った回は passed)。限界の回を最初のタブにしない。
    """
    checks, lessons, axes = textbook_checks(g), textbook_lessons(res, g), textbook_axes(res)
    for tb in tabs:
        tid = tb["id"]
        text, lim = split_limit(tb["text"])
        ex = LIMIT_EXTRA[tid]
        ls = dict(lessons[tid])
        ls["limit"] = T(lim["ja"] + ex["ja"], lim["en"] + " " + ex["en"])
        tb["text"], tb["lesson"], tb["checks"], tb["axis"] = text, ls, checks[tid], axes[tid]
        tb["badge"] = "limit" if any(not r["ok"] for r in checks[tid]) else "passed"
    if tabs[0]["badge"] == "limit":
        raise AssertionError("限界の回を最初のタブにしない(成功の回を見てから壊れ方を見る順)")
    return tabs


def build_spec(res):
    S = gates(res)
    A, B, C, D = res["imaging"], res["lensmaker"], res["doublet"], res["pupils"]
    tabs, infos = [], {}
    # ------------------------------------------------------------- 薄レンズの結像
    bodies, xyz, quat, frames, events, series, info = build_imaging_tab(A)
    infos["imaging"] = info
    text = T(
        "【言葉】焦点距離 f = 平行な光が 1 点に集まるまでの距離。主点 H, H′ = 厚いレンズで距離を測る基準の面(薄いレンズなら"
        "レンズの真ん中)。実像 = 光が本当に集まってスクリーンに映る像。虚像 = 光は集まらず、レンズ越しに見えるだけの像。"
        "倍率 m = 像の大きさ ÷ 物体の大きさ(マイナスは上下さかさま)。\n"
        "物体(白い矢印)をレンズから 3f の所から 0.5f まで近づける。緑の線は fullseye の光線追跡 trace_rays が実際に追った光、"
        "オレンジの矢印は thin_lens が 1/a + 1/b = 1/f から出した像。a = 2f で同じ大きさ、a が f に近づくと像は遠くへ逃げて"
        "大きくなり、f を割ると光は集まらなくなって正立の虚像(虫めがね)に変わる(灰の線 = 出た光を後ろへ伸ばした線)。\n"
        "限界: 近軸の式は「光軸のすぐそばの光」だけの式。レンズの縁寄り(半径の 0.45)を通る実光線は a = 3f で %.1f%%、"
        "a = 2f で %.1f%% 手前で集まり、a が f に近づくと差が大きく開く(式は無限遠、実光線は有限)。"
        "thin_lens と paraxial_trace(厚いレンズの近軸の追跡、主点から測る)は全コマで相対 %.0e 以内で一致(門)。" % (
            100 * S["A_ray_3f"], 100 * S["A_ray_2f"], S["A_para_vs_thin"] + 1e-300),
        "Terms: focal length f = where parallel light meets. Principal planes H, H′ = the reference planes from which "
        "distances are measured in a thick lens (the middle of a thin lens). Real image = light really converges and "
        "shows on a screen. Virtual image = light never meets; you only see it through the lens. Magnification m = "
        "image size / object size (minus = upside down).\n"
        "The object (white arrow) moves from 3f to 0.5f. Green lines are rays that fullseye's trace_rays actually traced; "
        "the orange arrow is the image thin_lens computes from 1/a + 1/b = 1/f. At a = 2f the image is the same size; as a "
        "approaches f the image runs away and grows; inside f the light no longer meets and the image becomes an upright "
        "virtual image (a magnifier; grey lines are the outgoing rays extended backwards).\n"
        "Limit: the paraxial formula is for rays close to the axis. Real rays through 0.45 of the radius meet %.1f%% "
        "short at a = 3f and %.1f%% at a = 2f, and the gap opens up as a nears f (formula: infinity; real rays: finite). "
        "thin_lens and paraxial_trace (thick lens, measured from the principal planes) agree to %.0e on every frame (gate)." % (
            100 * S["A_ray_3f"], 100 * S["A_ray_2f"], S["A_para_vs_thin"] + 1e-300))
    nums = [pv.viewer_number(T("焦点距離 f(paraxial_trace)", "focal length f (paraxial_trace)"), "%.2f mm" % S["A_f"]),
            pv.viewer_number(T("thin_lens と paraxial_trace の差(最大)", "thin_lens vs paraxial_trace (max)"),
                             "%.0e" % S["A_para_vs_thin"]),
            pv.viewer_number(T("a = 2f の倍率", "magnification at a = 2f"), "%+.3f" % S["A_m_2f"]),
            pv.viewer_number(T("実光線の像の位置のずれ(3f / 2f)", "real-ray image shift (3f / 2f)"),
                             "%.1f%% / %.1f%%" % (100 * S["A_ray_3f"], 100 * S["A_ray_2f"]))]
    tabs.append(pv.viewer_anim3d_tab(
        "imaging", T("薄レンズの結像", "Thin-lens imaging"), "passed", text, A["t"], bodies, xyz, quat,
        events=events, series=series, numbers=nums, view=dict(VIEW_LONG, dist=0.5),
        panes=[_pane(frames, "Fullseye の処理の帯: paraxial_trace(f と主点、水色の点 F)→ thin_lens(b と m、オレンジの矢印)"
                             "→ trace_rays(矢印の各点を実光線で運んだ像、緑の線)→ 理論の線 b(a)(白)と比べる(黄色の点)。"
                             "下の 1 行 = その時刻の式と数字(op ごとの値は左上の一覧と下のグラフ)",
                     "Fullseye processing band: paraxial_trace (f and principal planes, light-blue F) → thin_lens (b and m, "
                     "orange arrow) → trace_rays (the arrow carried point by point by real rays, green) → compare with the "
                     "theory line b(a) (white; yellow dot). Bottom line: the formula with this instant's numbers (per-op values in the "
                     "list at top left and the graph below)")]))
    # ------------------------------------------------------------- レンズメーカーの式
    bodies, xyz, quat, frames, events, series, info = build_lensmaker_tab(B)
    infos["lensmaker"] = info
    text = T(
        "【言葉】屈折率 n = 光がその材料の中でどれだけ遅くなるか(水 1.33、ふつうのガラス 1.52)。曲率半径 R = レンズの面を"
        "球の一部とみたときの球の半径(小さいほど強く曲がった面)。屈折力 1/f = 光を曲げる強さ(単位 D = 1/m)。\n"
        "前半は両凸レンズの面の半径 R を 300 mm から 24 mm まで小さくし、後半は R = 50 mm のまま材料を 水 → アクリル(PMMA)→ "
        "クラウンガラス → ポリカーボネート → 重フリントガラス → ランタン系高屈折率ガラスと替える(各ガラスの n_d・V_d は下の数値)。"
        "屈折率は fullseye の材料ライブラリ "
        "(material_optical_constants)から引き、同じ数字を光線追跡に渡す。白い点が薄肉の式 1/f = (n−1)(1/R1 − 1/R2) の焦点、"
        "緑の点が paraxial_trace の焦点、黄色の線が trace_rays の実光線。\n"
        "限界: 薄肉の式はレンズの厚みを 0 とみなす。R = 300 mm では差 %.2f%% だが、R = 24 mm(厚さ 7.9 mm)では %.1f%% 外れる"
        "(薄肉 %.1f mm、厚肉 %.1f mm)。さらに縁(高さ 10 mm)の実光線は %.1f mm で集まる。厚肉の閉形式 thick_lens と"
        "paraxial_trace は全コマ相対 %.0e 以内で一致(門)。" % (
            100 * S["B_dev_R300"], 100 * S["B_dev_R24"], S["B_thin_R24"], S["B_thick_R24"], S["B_ray_R24"],
            S["B_thick_vs_para"] + 1e-300),
        "Terms: refractive index n = how much light slows down in the material (water 1.33, ordinary glass 1.52). "
        "Radius of curvature R = the radius of the sphere a lens surface is part of (smaller = more strongly curved). "
        "Power 1/f = how strongly the lens bends light (unit D = 1/m).\n"
        "First the surfaces of a biconvex lens go from R = 300 mm to 24 mm; then, at R = 50 mm, the material changes: "
        "water → acrylic (PMMA) → crown glass → polycarbonate → dense flint glass → lanthanum dense flint glass (n_d and V_d "
        "of each glass are in the numbers below). The index comes from fullseye's material "
        "library (material_optical_constants) and the same number goes into the ray trace. White dot: focus from the "
        "thin-lens formula 1/f = (n−1)(1/R1 − 1/R2); green dot: paraxial_trace; yellow lines: real rays from trace_rays.\n"
        "Limit: the thin-lens formula treats the lens as having zero thickness. At R = 300 mm it is off by %.2f%%; at "
        "R = 24 mm (7.9 mm thick) by %.1f%% (thin %.1f mm, thick %.1f mm), and the edge ray (10 mm high) meets at %.1f mm. "
        "The closed-form thick_lens and paraxial_trace agree to %.0e on every frame (gate)." % (
            100 * S["B_dev_R300"], 100 * S["B_dev_R24"], S["B_thin_R24"], S["B_thick_R24"], S["B_ray_R24"],
            S["B_thick_vs_para"] + 1e-300))
    nums = [pv.viewer_number(T("thick_lens と paraxial_trace の差(最大)", "thick_lens vs paraxial_trace (max)"),
                             "%.0e" % S["B_thick_vs_para"]),
            pv.viewer_number(T("薄肉の式のずれ(R = 300 / 24 mm)", "thin formula error (R = 300 / 24 mm)"),
                             "%.2f%% / %.1f%%" % (100 * S["B_dev_R300"], 100 * S["B_dev_R24"])),
            pv.viewer_number(T("材料", "materials"), T(" · ".join(mat_label(m, "ja") for m in MATS_B),
                                                       " · ".join(mat_label(m, "en") for m in MATS_B)))]
    tabs.append(pv.viewer_anim3d_tab(
        "lensmaker", T("レンズメーカーの式", "Lensmaker's equation"), "passed", text, B["t"], bodies, xyz, quat,
        events=events, series=series, numbers=nums, view=dict(VIEW_LONG, dist=0.42),
        panes=[_pane(frames, "Fullseye の処理の帯: material_optical_constants(材料ライブラリの n、分散曲線の上の点)→ "
                             "thick_lens(厚いレンズの閉形式、オレンジ = 後ろの主点 H′)→ paraxial_trace(近軸の光線、緑 = F′)→ "
                             "trace_rays(実光線、黄)。右端: 白い線 = 薄肉の式(門の値)、横軸 (n−1)(1/R1−1/R2)、縦軸 1/f",
                     "Fullseye processing band: material_optical_constants (n from the material library, on its dispersion "
                     "curve) → thick_lens (closed form; orange = rear principal plane H′) → paraxial_trace (paraxial ray; "
                     "green = F′) → trace_rays (real rays, yellow). Right: white line = thin-lens formula (the gate), "
                     "x = (n−1)(1/R1−1/R2), y = 1/f")]))
    # ------------------------------------------------------------- 2 枚組と ABCD
    bodies, xyz, quat, frames, events, series, info = build_doublet_tab(C)
    infos["doublet"] = info
    text = T(
        "【言葉】ABCD 行列 = 光線の「高さ y と傾き θ」の 2 つの数を、レンズや空間を通すたびに 2×2 の行列を掛けて運ぶ計算の"
        "道具。系全体も 1 つの行列にまとまり、焦点距離は f = −1/C。主点 H′ = 2 枚組を「1 枚の薄いレンズ」とみなしたときの"
        "レンズの位置(灰の線: 入ってくる光線と出ていく光線を延ばして交わる所)。\n"
        "f1 = %.1f mm と f2 = %.1f mm の 2 枚の間隔を広げていく。1/f = 1/f1 + 1/f2 − d/(f1·f2) は d について一直線"
        "(右端のグラフの白い線)。d = f1 + f2 = %.1f mm で屈折力が 0(焦点距離が無限大)、平行光が平行光のまま出る = 望遠鏡。"
        "その先は f が負になる。\n"
        "ここで大事な点: 実のレンズは厚いので、d を「主点の間」で測ると薄レンズの ABCD がそのまま当たる "
        "(abcd_matrix と実の処方の paraxial_trace が全コマ相対 %.0e で一致、det M = 1 も %.0e で成立: 門)。"
        "限界: 高さ 9 mm の実光線(黄色)は近軸の焦点より手前で集まり、望遠鏡の近くでは差が大きく開く。" % (
            C["f1"], C["f2"], S["C_afocal_d"], S["C_abcd_vs_para"] + 1e-300, S["C_det"] + 1e-300),
        "Terms: ABCD matrix = a way to carry a ray's height y and slope θ through each lens or gap by multiplying a 2×2 "
        "matrix; the whole system becomes one matrix and its focal length is f = −1/C. Principal plane H′ = where the "
        "pair acts like one thin lens (grey lines: the incoming and outgoing rays extended until they meet).\n"
        "The gap between f1 = %.1f mm and f2 = %.1f mm widens. 1/f = 1/f1 + 1/f2 − d/(f1·f2) is a straight line in d "
        "(white line in the right graph). At d = f1 + f2 = %.1f mm the power is zero (infinite focal length): parallel "
        "light leaves parallel — a telescope. Beyond that f is negative.\n"
        "Key point: real lenses are thick, and if d is measured between the principal planes the thin-lens ABCD holds "
        "exactly (abcd_matrix vs paraxial_trace of the real prescription agree to %.0e on every frame; det M = 1 to %.0e: "
        "gates). Limit: the real 9 mm ray (yellow) meets short of the paraxial focus, and near the telescope setting the "
        "gap opens up." % (C["f1"], C["f2"], S["C_afocal_d"], S["C_abcd_vs_para"] + 1e-300, S["C_det"] + 1e-300))
    nums = [pv.viewer_number(T("f1 / f2(paraxial_trace)", "f1 / f2 (paraxial_trace)"), "%.2f / %.2f mm" % (C["f1"], C["f2"])),
            pv.viewer_number(T("abcd_matrix と paraxial_trace の差(最大)", "abcd_matrix vs paraxial_trace (max)"),
                             "%.0e" % S["C_abcd_vs_para"]),
            pv.viewer_number(T("望遠鏡になる間隔 f1 + f2", "telescope spacing f1 + f2"), "%.1f mm" % S["C_afocal_d"])]
    tabs.append(pv.viewer_anim3d_tab(
        "doublet", T("2 枚組と ABCD 行列", "Two lenses and ABCD matrices"), "passed", text, C["t"], bodies, xyz, quat,
        events=events, series=series, numbers=nums, view=dict(VIEW_LONG, dist=0.42),
        panes=[_pane(frames, "Fullseye の処理の帯: abcd_matrix(2×2 の行列、水色 = 主点 H′)→ abcd_trace(高さ 9 mm の近軸光線)"
                             "→ paraxial_trace(実の処方の f と F′、緑)→ trace_rays(実光線、黄)。右端: 白い線 = "
                             "1/f1 + 1/f2 − d/(f1·f2)(門の値)",
                     "Fullseye processing band: abcd_matrix (the 2×2 matrix; light blue = principal plane H′) → abcd_trace "
                     "(the paraxial 9 mm ray) → paraxial_trace (f and F′ of the real prescription, green) → trace_rays (real "
                     "rays, yellow). Right: white line = 1/f1 + 1/f2 − d/(f1·f2) (the gate)")]))
    # ------------------------------------------------------------- 絞りと瞳
    bodies, xyz, quat, frames, events, series, info = build_pupil_tab(D)
    infos["pupils"] = info
    ep_z, ep_r = S["D_ep"]
    text = T(
        "【言葉】開口絞り = 光束の太さを決める穴(暗い輪)。入射瞳 = 前から覗いたときに見える絞りの像、射出瞳 = 後ろから"
        "見た絞りの像(水色の輪)。主光線 = 絞りの中心を通る光線(オレンジ)。ケラレ = レンズの縁が斜めの光束を切ること"
        "(赤い線 = 縁で切られた光、灰の線 = 絞りで止まった光)。周辺減光 = 画面の端ほど暗くなること。教科書の cos⁴ 則: E/E0 = cos⁴θ。\n"
        "2 枚のレンズの間に絞りを置いた対称な系で、斜めから来る平行光の角度 θ を 0 → %.0f° に振る。paraxial_trace が"
        "入射瞳を頂点から %.1f mm・半径 %.2f mm と出し、chief_ray は全コマで絞りの中心から %.0e mm 以内を通る(門)。\n"
        "限界: cos⁴ は「瞳がゆがまず、どこも切られない」ときの式。縁で切らない場合でも 10° までは %.1f%% 以内で合うが、"
        "その先は瞳の見かけが広がって cos⁴ より最大 %.0f%% 明るい(灰の点)。縁で切ると %.0f° で cos⁴ の %.3f に対し"
        "実光線は %.3f(ray_bundle で通る光線は %.0f%%)—— cos⁴ だけで周辺の明るさを見積もると外れる。" % (
            FIELD_MAX, ep_z, ep_r, S["D_stop_hit"] + 1e-300, 100 * S["D_noclip_10deg"], 100 * S["D_noclip_max"],
            S["D_theta_end"], S["D_cos4_end"], S["D_ri_end"], 100 * S["D_vig_end"]),
        "Terms: aperture stop = the hole that sets how thick the beam is (dark ring). Entrance pupil = the stop as seen "
        "from the front; exit pupil = as seen from the back (light-blue rings). Chief ray = the ray through the centre "
        "of the stop (orange). Vignetting = a lens rim clipping an oblique beam (red = rays clipped by a rim; grey = rays stopped by the stop). Relative "
        "illumination = the picture getting darker towards the edge; the textbook cos⁴ law says E/E0 = cos⁴θ.\n"
        "A symmetric system with the stop between two lenses; the angle θ of the incoming parallel light goes 0 → %.0f°. "
        "paraxial_trace puts the entrance pupil %.1f mm from the first vertex with radius %.2f mm, and chief_ray passes "
        "within %.0e mm of the stop centre on every frame (gate).\n"
        "Limit: cos⁴ assumes an undistorted pupil and no clipping. Without rim clipping it holds within %.1f%% up to 10°, "
        "beyond which the pupil looks larger and the edge is up to %.0f%% brighter than cos⁴ (grey dots). With the rims, at "
        "%.0f° cos⁴ gives %.3f but the real rays give %.3f (ray_bundle passes %.0f%% of the rays) — cos⁴ alone is the "
        "wrong estimate." % (FIELD_MAX, ep_z, ep_r, S["D_stop_hit"] + 1e-300, 100 * S["D_noclip_10deg"],
                             100 * S["D_noclip_max"], S["D_theta_end"], S["D_cos4_end"], S["D_ri_end"], 100 * S["D_vig_end"]))
    nums = [pv.viewer_number(T("入射瞳(位置 / 半径)", "entrance pupil (position / radius)"), "%.2f / %.2f mm" % (ep_z, ep_r)),
            pv.viewer_number(T("F 値(paraxial_trace)", "F-number (paraxial_trace)"), "%.2f" % D["para"]["fno"]),
            pv.viewer_number(T("%.0f° の周辺光量: cos⁴ / 実光線" % S["D_theta_end"], "illumination at %.0f°: cos⁴ / real rays" % S["D_theta_end"]),
                             "%.3f / %.3f" % (S["D_cos4_end"], S["D_ri_end"]))]
    tabs.append(pv.viewer_anim3d_tab(
        "pupils", T("絞りと瞳(cos⁴)", "Stops and pupils (cos⁴)"), "limit", text, D["t"], bodies, xyz, quat,
        events=events, series=series, numbers=nums, view=dict(VIEW, dist=0.55),
        panes=[_pane(frames, "Fullseye の処理の帯: paraxial_trace(入射瞳・射出瞳、水色)→ chief_ray(主光線、オレンジ。白い線 = "
                             "f·tanθ)→ ray_bundle(瞳の上の光線、緑 = 通る・赤 = 切られる)→ relative_illumination(白い線 = cos⁴ = "
                             "門の値、黄 = 実光線、灰 = 縁で切らない場合)",
                     "Fullseye processing band: paraxial_trace (entrance / exit pupils, light blue) → chief_ray (orange; white "
                     "line = f·tanθ) → ray_bundle (rays across the pupil: green passes, red is clipped) → relative_illumination "
                     "(white = cos⁴ = the gate, yellow = real rays, grey = no rim clipping)")]))
    attach_lessons(tabs, res, S)
    spec = pv.viewer_spec(
        "textbook_lens_system",
        T("レンズ 1 枚から光学系へ", "From one lens to an optical system"),
        T("教科書の結像を、つまみを振って動かす。光線は fullseye の光線追跡、式は門の値",
          "Textbook imaging with the knob turning. Rays come from fullseye's ray tracer; the formulas are the gates"),
        T("各タブは ① 問い → ② 予想(選択肢を押すと答えが開く)→ ③ 再生(▶)→ ④ 式 → ⑤ 限界 の順。時間つまみの読みは"
          "物体の位置・曲率半径・間隔・入射角などの物理量。帯の 4 段は 0.6 秒ずつ順に光る。バッジを押すと、確かめた項目・基準・"
          "結果の表が開く。ドラッグで視点を回す。レンズは半透明で、ガラスの中を通る光線が透けて見える。",
          "Each tab runs ① question → ② predict (tap a choice to reveal the answer) → ③ play (▶) → ④ equation → ⑤ limit. "
          "The time slider reads a physical quantity: object distance, radius, spacing or field angle. The four band stages "
          "light up in turn. Tap a badge to open what was checked, the criterion and the result. Drag to orbit. The lenses "
          "are translucent, so the rays inside the glass show through."),
        tabs)
    return spec, S, infos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="書かずに、数字の印字と HTML の生成だけ")
    ap.add_argument("--out", default=str(OUT_HTML))
    a = ap.parse_args(argv)
    res = run_all()
    spec, S, infos = build_spec(res)
    for k, v in S.items():
        print("%-20s %s" % (k, v))
    for k, v in infos.items():
        print("%-10s rods %d" % (k, v["nrods"]))
    if a.check:
        n = len(pv._build_html(spec, list(LANGS)).encode("utf-8"))
        print("ok: %d bytes (not written)" % n)
        return 0
    path = pv.write_viewer(spec, a.out, list(LANGS))
    print("wrote %s (%.2f MB)" % (path, Path(path).stat().st_size / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
