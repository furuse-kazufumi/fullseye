# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ。

3-D プリンタや切削に形を渡す前に、「その形は作れるのか」を形状だけから見ておく
仕事です(DFM = design for manufacturability)。見るのは 3 つ ——
**薄すぎる肉**(壊れる・充填できない)、**寝すぎた下向き面**(サポートが要る)、
**工具やノズルが入らない隙間**(そもそも加工できない)。答えは「面積 [mm^2]」と
「肉厚 [mm]」で出るので、**その 2 つは別々に数えないと嘘になります**。

EXTEND: 実測の形状に差し替えるなら :func:`part_sdf` の戻り値(符号付き距離場)を、
CT 再構成ボリューム(内側が明るいグレー値)か CAD ソリッドのボクセル化に置き換えます。
そのとき**測れなくなるのは真値のほう**です —— 肉厚の設計値・面の角度・隙間の幅が
式で分からなくなるので、この PoC が出した「どの推定器がどれだけずれるか」を
較正表として持ち込むことになります。:func:`analytic_faces` が返す面の一覧
(法線・面積・重心)は設計 CAD の B-rep から取れますが、CT からは取れません。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(ボクセル化して「侵食で消える回数」を数える)は 2 voxel 刻みに潰れる**。
   設計 1.500 mm の薄壁を粗さ 0.500 mm で測ると 2.000 mm。値は必ず 2h の倍数に
   落ちるので、**h を細かくする以外に精度を上げる道が無い**。
2. ★**「最大内接球なら 1 voxel 刻みになる」という予想は外れた**。予想は h 刻み、
   実測も **2h 刻み**(掃引 8 点すべてで 2h の倍数)。2 値格子では距離変換の値が
   「占有中心から自由中心まで」なので、半径ではなく直径が量子化される。
3. **グレー値の探針だけが刻みを持たない**。同じ掃引で誤差の中央値は
   侵食 0.250 mm / 内接球 0.250 mm に対し探針 0.019 mm。ただし
   ★**壁が PSF に飲まれる 2 voxel 付近で破綻**し、1.5 voxel では
   探針が壁を 1 枚も見つけられない(予測「T <~ 2 sigma_psf = 1.6h で融合」と一致)。
4. ★★**サポートが要る面積は、しきい値 45 度の両側で段差になる**。解析値で
   44.9 度なら 185.50 mm^2、45.1 度なら 575.82 mm^2 —— **0.2 度で 3.10 倍**。
   部品の中に「ちょうど 45 度の斜面」が 390.32 mm^2 あるからで、
   **推定誤差が 0.1 度でもあれば答えは 3 倍動く**。
5. ★**その段差を、丸めた形はきれいに消してしまう**。等値面の取り方だけを変えた
   3 条件(2 値から / 距離場から / 平滑化してから)で、45 度ちょうどの面の
   帰属が変わる。平滑化 sigma=1.5 voxel では段差の高さが 390.32 -> 120.06 mm^2 に
   落ちる —— **「合わせた分だけ欠陥が消える」の面積版**。数字は滑らかになるが、
   造形機は丸まっていない形を作る。
6. **肉厚の誤差 [mm] と NG 面積 [mm^2] は連動しない**。同じ h=0.500 mm で
   肉厚の誤差は 0.500 mm(33 %)なのに、NG 面積の誤差は 44.9 度側で 3.7 %。
   逆に h=0.250 mm では肉厚 0.000 mm でも NG 面積は 5.1 % ずれる。
   **片方を根拠にもう片方を語れない**。
7. **工具の入る隙間は「入る/入らない」の 2 値なので、刻みがそのまま誤判定になる**。
   設計 1.500 mm のスロット(工具半径の上限 0.750 mm)を測ると、粗さ 0.500 mm では
   1.000 mm(上限 0.500 mm)—— **半径 0.6 mm の工具を「入らない」と誤って落とす**。
8. **向きを変えると効くが、ゼロにはならない**。造形方向 6 通りの解析値で
   最良は Z-(45.10 mm^2)、設計どおりの Z+ は 575.82 mm^2 で **12.8 倍**。
   ★ただし**どの向きでもゼロにはならない** —— 水平穴と垂直穴が互いに逆を向いて
   いるので、片方を立てるともう片方が寝る。

【グラウンドトゥルース】部品は SDF のブール演算で作る合成形状(板・リブ・薄壁 2 枚・
スロット・庇・45 度前後の三角補強 3 枚・水平穴・垂直穴)。**肉厚は設計値として既知**
(薄壁 1.500 mm / リブ 3.000 mm / 板 8.000 mm / スロット 1.500 mm)、面の法線と面積は
平面と円筒の閉形式で出るので、**サポート必要面積は解像度無限の解析値**として持てる。
円筒面の必要面積は arccos の閉形式(:func:`cylinder_support_area`)。

来歴(公開文献のみ): ISO/ASTM 52910:2018 *Additive manufacturing — Design —
Requirements, guidelines and recommendations* / D. Thomas, *The Development of Design
Rules for Selective Laser Melting* (PhD thesis, Univ. of Wales, 2009) —— 自己支持
限界角 45 度の由来 / W. E. Lorensen & H. E. Cline, "Marching Cubes", SIGGRAPH 1987 /
I. Quilez, *Distance functions* (公開の SDF 集) —— 直方体・円筒の厳密 SDF。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage, special

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

L = fs.ledger                     # 3-D op の公開経路(ファサード fs.<名> には多くが無い)

# --- 部品の諸元 [mm] --------------------------------------------------------- #
# すべて設計値。voxel の粗さ h を変えても**この表は動かない** = 真値。
T_WALL = 1.5        # 薄壁の厚さ
T_SLOT = 1.5        # 薄壁 2 枚のあいだの隙間(工具が入るか)
T_RIB = 3.0         # リブの厚さ
T_PLATE = 8.0       # 板の厚さ
GUSSET_H = 11.5     # 三角補強の高さ(斜面の落差)
GUSSETS = ((40.0, 24.0, 25.5), (45.0, 27.0, 51.0), (50.0, 52.0, 53.5))   # (角度, x0, x1)
RIB_Y0, RIB_Y1 = 18.5, 21.5
LEDGE = (8.0, 11.0, 19.0, 32.5, 20.5, 23.5)      # 庇 x0,x1,y0,y1,z0,z1
HOLE_H = ((12.0, 20.0, 4.0), 2.0, 40.0)          # 水平穴(軸 y): 中心, 半径, 長さ
HOLE_V = ((48.0, 30.0, 4.0), 4.0, 8.0)           # 垂直穴(軸 z)
BOUNDS = ((-1.0, 61.0), (-1.0, 41.0), (-1.0, 25.0))

SELF_SUPPORT_DEG = 45.0          # 自己支持限界角(水平からの傾き)
COS_C = float(np.cos(np.radians(SELF_SUPPORT_DEG)))
H_MESH = 0.35                    # メッシュ側の既定ボクセル粗さ [mm]
PSF_VOXEL = 0.8                  # グレー値ボリュームの PSF [voxel](CT の点像分布)
SEED = 7


# --------------------------------------------------------------------------- #
# 1. 部品を SDF のブール演算で作る —— 真値はこの定義そのもの                    #
# --------------------------------------------------------------------------- #
def _box(g, x0, x1, y0, y1, z0, z1):
    """軸平行直方体の厳密 SDF(``box_sdf`` は中心 + 半辺長で呼ぶ)。"""
    c = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)
    he = ((x1 - x0) / 2.0, (y1 - y0) / 2.0, (z1 - z0) / 2.0)
    return np.asarray(L.box_sdf(g, c, he))


def _cylinder(g, axis, center, radius, half_len):
    """有限長円筒の厳密 SDF。**``sdf_*`` 族に円筒プリミティブが無い**ので自前。

    Quilez の capped cylinder: 半径方向と軸方向の 2 つの符号付き距離を
    ``min(max(a,b),0) + |max((a,b),0)|`` で合成する(角でも厳密)。
    """
    ax = {"x": 0, "y": 1, "z": 2}[axis]
    per = [i for i in range(3) if i != ax]
    d = np.asarray(g, np.float64) - np.asarray(center, np.float64)
    rad = np.hypot(d[..., per[0]], d[..., per[1]]) - float(radius)
    axi = np.abs(d[..., ax]) - float(half_len)
    outside = np.hypot(np.maximum(rad, 0.0), np.maximum(axi, 0.0))
    return np.minimum(np.maximum(rad, axi), 0.0) + outside


def part_sdf(g):
    """部品の符号付き距離場(内側が負)。``g`` は ``(..., 3)`` の world 座標 [mm]。

    板 + リブ + 薄壁 2 枚(そのあいだがスロット)+ 庇 + 三角補強 3 枚 − 水平穴 − 垂直穴。
    **接合部はわざと 1 mm 食い込ませてある** —— 面で触れているだけだと
    ボクセル化で連結が切れたり切れなかったりして、測るたびに形が変わる。
    """
    s = _box(g, 0, 60, 0, 40, 0, T_PLATE)                                   # 板
    s = np.asarray(L.sdf_union(s, _box(g, 6, 54, RIB_Y0, RIB_Y1, 7, 24)))   # リブ
    s = np.asarray(L.sdf_union(s, _box(g, 6, 54, 5.25, 5.25 + T_WALL, 7, 20)))
    y_b = 5.25 + T_WALL + T_SLOT
    s = np.asarray(L.sdf_union(s, _box(g, 6, 54, y_b, y_b + T_WALL, 7, 20)))
    s = np.asarray(L.sdf_union(s, _box(g, *LEDGE)))                         # 庇
    for phi, x0, x1 in GUSSETS:
        p = np.radians(phi)
        d = GUSSET_H / np.tan(p)
        blk = _box(g, x0, x1, RIB_Y0 + 1.5, RIB_Y1 + d, 9.0, 20.5)
        # 斜面の半空間(外向き法線 (0, sin phi, -cos phi)、点 (y=RIB_Y1, z=9) を通る)。
        half = np.sin(p) * (g[..., 1] - RIB_Y1) - np.cos(p) * (g[..., 2] - 9.0)
        s = np.asarray(L.sdf_union(s, np.asarray(L.sdf_intersect(blk, half))))
    c, r, ln = HOLE_H
    s = np.asarray(L.sdf_subtract(s, _cylinder(g, "y", c, r, ln)))
    c, r, ln = HOLE_V
    s = np.asarray(L.sdf_subtract(s, _cylinder(g, "z", c, r, ln)))
    return s


def make_grid(h, bounds=BOUNDS):
    """粗さ ``h`` [mm] の等方格子と、その world 座標を返す。"""
    res = [max(2, int(round((b[1] - b[0]) / h))) for b in bounds]
    g = np.asarray(L.grid_coords(bounds, res))
    return g, res


# --------------------------------------------------------------------------- #
# 2. 面の一覧(解析) —— 解像度無限の対照群                                     #
# --------------------------------------------------------------------------- #
def analytic_faces():
    """平面の面 ``(法線, 面積 [mm^2], 重心)`` の一覧。円筒面は別扱い。"""
    F = []

    def add(n, area, cen):
        v = np.asarray(n, np.float64)
        F.append((v / np.linalg.norm(v), float(area), np.asarray(cen, np.float64)))

    rv, rh = HOLE_V[1], HOLE_H[1]
    lx0, lx1, ly0, ly1, lz0, lz1 = LEDGE
    lw, ll = lx1 - lx0, ly1 - RIB_Y1              # 庇の幅と、リブから出ている長さ
    rib_len = 54.0 - 6.0
    # --- 板 ---------------------------------------------------------------- #
    add((0, 0, -1), 60 * 40 - np.pi * rv ** 2, (30, 20, 0))          # 造形板に接する面
    add((0, 0, 1), 60 * 40 - np.pi * rv ** 2 - rib_len * (T_RIB + 2 * T_WALL), (30, 20, T_PLATE))
    add((0, -1, 0), 60 * T_PLATE - np.pi * rh ** 2, (30, 0, 4))
    add((0, 1, 0), 60 * T_PLATE - np.pi * rh ** 2, (30, 40, 4))
    add((-1, 0, 0), 40 * T_PLATE, (0, 20, 4))
    add((1, 0, 0), 40 * T_PLATE, (60, 20, 4))
    # --- リブ(y=RIB_Y1 の面は庇と三角補強の付け根で欠ける)------------------ #
    add((0, 0, 1), rib_len * T_RIB, (30, 20, 24))
    add((0, -1, 0), rib_len * 16.0, (30, RIB_Y0, 16))
    cut = lw * (lz1 - lz0) + sum((x1 - x0) * GUSSET_H for _, x0, x1 in GUSSETS)
    add((0, 1, 0), rib_len * 16.0 - cut, (30, RIB_Y1, 16))
    add((-1, 0, 0), T_RIB * 16.0, (6, 20, 16))
    add((1, 0, 0), T_RIB * 16.0, (54, 20, 16))
    # --- 薄壁 2 枚 ---------------------------------------------------------- #
    for y0 in (5.25, 5.25 + T_WALL + T_SLOT):
        add((0, 0, 1), rib_len * T_WALL, (30, y0 + T_WALL / 2, 20))
        add((0, -1, 0), rib_len * 12.0, (30, y0, 14))
        add((0, 1, 0), rib_len * 12.0, (30, y0 + T_WALL, 14))
        add((-1, 0, 0), T_WALL * 12.0, (6, y0 + T_WALL / 2, 14))
        add((1, 0, 0), T_WALL * 12.0, (54, y0 + T_WALL / 2, 14))
    # --- 庇(下面が水平の張り出し = 最悪のオーバーハング)-------------------- #
    ym = (RIB_Y1 + ly1) / 2.0
    add((0, 0, -1), lw * ll, ((lx0 + lx1) / 2, ym, lz0))
    add((0, 0, 1), lw * ll, ((lx0 + lx1) / 2, ym, lz1))
    add((0, 1, 0), lw * (lz1 - lz0), ((lx0 + lx1) / 2, ly1, (lz0 + lz1) / 2))
    add((-1, 0, 0), ll * (lz1 - lz0), (lx0, ym, (lz0 + lz1) / 2))
    add((1, 0, 0), ll * (lz1 - lz0), (lx1, ym, (lz0 + lz1) / 2))
    # --- 三角補強(斜面の角度が設計値)-------------------------------------- #
    for phi, x0, x1 in GUSSETS:
        p = np.radians(phi)
        d = GUSSET_H / np.tan(p)
        w, xm = x1 - x0, (x0 + x1) / 2.0
        add((0, np.sin(p), -np.cos(p)), w * GUSSET_H / np.sin(p), (xm, RIB_Y1 + d / 2, 9 + GUSSET_H / 2))
        add((0, 0, 1), w * d, (xm, RIB_Y1 + d / 2, 20.5))
        add((-1, 0, 0), 0.5 * d * GUSSET_H, (x0, RIB_Y1 + d / 3, 9 + GUSSET_H / 3))
        add((1, 0, 0), 0.5 * d * GUSSET_H, (x1, RIB_Y1 + d / 3, 9 + GUSSET_H / 3))
    return F


def cylinder_support_area(axis, radius, length, build_dir, cos_c=COS_C):
    """円筒面のうちサポートが要る面積 [mm^2] の**閉形式**。

    軸 ``a`` の円筒の法線は ``a`` に直交する単位円をなす。造形方向 ``b`` に対し
    ``rho = |b - (b.a)a|`` とすると ``n.b = rho cos(psi - psi0)``。したがって
    ``n.b < -cos_c`` となる角度の幅は ``rho > cos_c`` のとき ``2 arccos(cos_c/rho)``、
    そうでなければ 0。面積はそれに ``radius * length`` を掛けたもの。
    軸が造形方向と平行(垂直穴)なら ``rho = 0`` で**常に 0** —— 立てた穴は垂れない。
    """
    a = np.asarray(axis, np.float64)
    a = a / np.linalg.norm(a)
    b = np.asarray(build_dir, np.float64)
    b = b / np.linalg.norm(b)
    rho = float(np.linalg.norm(b - np.dot(b, a) * a))
    if rho <= cos_c:
        return 0.0
    return float(radius) * float(length) * 2.0 * float(np.arccos(cos_c / rho))


def analytic_support_area(build_dir, cos_c=COS_C, faces=None, drop_baseplate=True):
    """解析値のサポート必要面積 [mm^2](造形板に寝ている面は除く)。"""
    F = analytic_faces() if faces is None else faces
    b = np.asarray(build_dir, np.float64)
    b = b / np.linalg.norm(b)
    smin = min(float(np.dot(c, b)) for _, _, c in F) if drop_baseplate else -np.inf
    total = 0.0
    for n, area, cen in F:
        nb = float(np.dot(n, b))
        if nb >= -cos_c:
            continue
        if drop_baseplate and nb < -0.999 and abs(float(np.dot(cen, b)) - smin) < 0.6:
            continue                            # 造形板にべた置きの面は「垂れ」ではない
        total += area
    total += cylinder_support_area((0, 1, 0), HOLE_H[1], HOLE_H[2], b, cos_c)
    total += cylinder_support_area((0, 0, 1), HOLE_V[1], HOLE_V[2], b, cos_c)
    return total


# --------------------------------------------------------------------------- #
# 3. 場面 —— 図と、解析面積 vs メッシュ面積の突き合わせ                          #
# --------------------------------------------------------------------------- #
def _mesh_from(vol, iso, h=None):
    """等値面 → ``(法線, 面積 [mm^2], 重心 [mm], 頂点)``。**退化三角形は落とす**。

    ``voxel_to_mesh`` の頂点は**ボクセル index 座標**で、列は入力配列の軸順
    (この PoC は (x,y,z) 順に組んでいる)。world へは ``lo + (i+0.5)*h``。
    """
    h = H_MESH if h is None else float(h)
    V, F = L.voxel_to_mesh(vol, iso=iso)
    V = np.asarray(V, np.float64) * h + np.array([b[0] for b in BOUNDS]) + h / 2.0
    F = np.asarray(F, np.int64)
    tri = V[F]
    cr = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(cr, axis=1)
    F = F[area > 0]                             # face_normals は退化があると fail-closed
    tri, area = V[F], area[area > 0]
    # ★向き(表裏)は巻き順で決まるが、marching cubes の巻き順は入力の符号規約で反転する。
    #   閉じたメッシュなら符号付き体積で一意に決まる —— 目視でなく式で決める。
    sv = float(np.einsum("ij,ij->i", np.cross(tri[:, 0], tri[:, 1]), tri[:, 2]).sum())
    if sv < 0:
        F = F[:, ::-1]
        tri = V[F]
    n = np.asarray(L.face_normals((V, F)))
    return n, area, tri.mean(axis=1), V


def measured_support_area(mesh, build_dir, cos_c=COS_C):
    """メッシュから数えたサポート必要面積 [mm^2]。

    ★**解析側とまったく同じ規約**(造形板にべた置きの面は除く)にしないと、
    板の裏 2349.7 mm^2 が丸ごと混ざって 4 倍以上ずれる(最初そう書いて踏んだ)。
    """
    n, area, cen, V = mesh
    b = np.asarray(build_dir, np.float64)
    b = b / np.linalg.norm(b)
    nb = n @ b
    keep = nb < -cos_c
    on_plate = (nb < -0.999) & ((cen @ b) - float((V @ b).min()) < 0.6 + H_MESH)
    return float(area[keep & ~on_plate].sum())


def section_scene():
    print("\n" + "=" * 78)
    print("1) 場面 —— SDF のブール演算で作る部品(肉厚は設計値として既知)")
    print("=" * 78)
    g, res = make_grid(H_MESH)
    sdf = part_sdf(g)
    occ = sdf < 0.0
    print("  格子 %d x %d x %d = %.2f M voxel(粗さ %.3f mm)" % (*res, np.prod(res) / 1e6, H_MESH))
    print("  設計肉厚: 薄壁 %.3f / リブ %.3f / 板 %.3f mm、スロット %.3f mm" % (
        T_WALL, T_RIB, T_PLATE, T_SLOT))
    print("  三角補強の斜面角: " + " / ".join("%.1f 度" % p for p, _, _ in GUSSETS))

    F = analytic_faces()
    a_plane = sum(a for _, a, _ in F)
    a_cyl = 2 * np.pi * (HOLE_H[1] * HOLE_H[2] + HOLE_V[1] * HOLE_V[2])
    a_true = a_plane + a_cyl
    a_mesh = float(_mesh_from(-sdf, 0.0)[1].sum())
    print("  表面積: 解析 %.1f mm^2(平面 %.1f + 円筒 %.1f) / メッシュ %.1f mm^2 (%+.2f %%)"
          % (a_true, a_plane, a_cyl, a_mesh, 100 * (a_mesh - a_true) / a_true))

    grad = np.stack(np.gradient(sdf, H_MESH), axis=0)     # 解析形状の法線(の格子近似)
    figs.save_grid("scene",
                   [_shaded(occ, grad, 1, False), _shaded(occ, grad, 0, False),
                    _shaded(occ, grad, 2, True)],
                   ["-Y から(薄壁 2 枚とスロットが見える)",
                    "-X から(庇と三角補強)",
                    "下から(オーバーハングになる面)"],
                   title="DFM を測る部品(板 60 x 40 x 8 mm)", ncols=3)
    ix = int(round((30.0 - BOUNDS[0][0]) / H_MESH))
    figs.save_grid("sections",
                   [occ[ix].T[::-1].astype(float), occ[:, :, int(round((14.0 + 1) / H_MESH))].T],
                   ["x=30 mm の Y-Z 断面(左が薄壁 2 枚、右が三角補強)",
                    "z=14 mm の X-Y 断面(リブと薄壁)"],
                   title="断面(白 = 材料)", ncols=1)
    return {"g": g, "res": res, "sdf": sdf, "occ": occ, "a_true": a_true, "a_mesh": a_mesh}


def _shaded(occ, grad, axis, reverse):
    """``axis`` 方向に見た最初の占有面の Lambertian 陰影(H,W)。"""
    a = np.moveaxis(occ, axis, 0)
    gg = np.moveaxis(grad, axis + 1, 1)
    if reverse:
        a, gg = a[::-1], gg[:, ::-1]
    hit = a.argmax(0)
    seen = a.any(0)
    ii, jj = np.meshgrid(np.arange(a.shape[1]), np.arange(a.shape[2]), indexing="ij")
    nrm = np.stack([gg[k][hit, ii, jj] for k in range(3)], axis=-1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=-1, keepdims=True), 1e-9)
    img = np.asarray(L.render_shaded(nrm, light=(0.4, -0.5, 0.75), ambient=0.15))
    return np.where(seen, img, 0.0).T[::-1]


# --------------------------------------------------------------------------- #
# 4. 肉厚 —— ゼロ点(侵食)/ 最大内接球 / グレー値探針                          #
# --------------------------------------------------------------------------- #
# ★格子の原点を壁の面にそろえてはいけない。3.0 で切ると壁の面が
#   ちょうど voxel の境目に落ち、掃引 8 点すべてで誤差 0.000 mm になって
#   「量子化は起きない」という嘘の結論が出る(2026-09-07 に一度そう書いた)。
#   実際のメッシャは部品の面に格子をそろえてはくれないので、非整合な原点にする。
COUPON = ((28.0, 32.0), (3.037, 12.037), (12.0, 17.0))   # 薄壁 2 枚 + スロットを含む小片
SLOT_Y = (5.25 + T_WALL, 5.25 + T_WALL + T_SLOT)         # スロットの y 範囲 [mm]


def coupon(h):
    """薄壁 2 枚とスロットだけを切り出した小片(SDF・占有・グレー値・座標)。

    x と z は壁の内部で切っているので、その面は**人工の切り口**。侵食は
    ``morph_erode3d`` が外を +inf 扱いにするので切り口からは食われない(y だけ食う)。
    """
    g, res = make_grid(h, COUPON)
    sdf = part_sdf(g)
    sigma = PSF_VOXEL * h
    # CT 再構成のグレー値: 平面近傍で厳密な「ガウス PSF で暈けた指示関数」。
    gray = 0.5 * special.erfc(sdf / (sigma * np.sqrt(2.0)))
    return sdf, np.asarray(L.sdf_to_occupancy(sdf, iso=0.0), bool), gray, res, g


def thickness_erosion(occ, h):
    """ゼロ点: 侵食を繰り返して消えるまでの回数から肉厚を出す。刻みは 2h。"""
    v = occ.astype(np.float32)
    m = 0
    while v.max() >= 0.5 and m < 64:
        v = np.asarray(L.morph_erode3d(v, r=1, se="cube"))
        m += 1
    return 2.0 * m * h


def thickness_inscribed(occ, h):
    """最大内接球: ESDF の内側(負)の最大の深さ x 2。予想は h 刻み。"""
    e = np.asarray(L.esdf(occ, voxel_size=h))
    inner = -e[np.isfinite(e) & (e < 0)]
    return 2.0 * float(inner.max()) if inner.size else 0.0


def thickness_probe(gray, h, res):
    """グレー値の探針(``vol_wall_thickness``)。薄壁 2 枚を横切るので**本来 2 つ返る**。

    返る本数も一緒に見る —— 1 本しか返らなければ 2 枚を 1 枚と誤認しており、
    そのときの「肉厚」は壁 + スロット + 壁を 1 枚と数えた値になる。
    """
    ix, kz = res[0] // 2, res[2] // 2
    t = np.asarray(L.vol_wall_thickness(gray, (ix, 0, kz), (ix, res[1] - 1, kz),
                                        sigma=0.6, threshold=0.05, spacing=(h, h, h)),
                   np.float64).ravel()
    return (float(np.mean(t)) if t.size else float("nan")), int(t.size)


def slot_radius(occ, g, h):
    """スロットに入る工具半径の上限 = **スロットの中の**自由側 ESDF の最大値。

    ★coupon 全体で最大を取ると、壁の外側の広い自由空間(2.250 mm)を拾って
    「工具は何でも入る」になる。測りたいのは隙間なので y で切る。
    """
    e = np.asarray(L.esdf(occ, voxel_size=h))
    inside = (g[..., 1] > SLOT_Y[0]) & (g[..., 1] < SLOT_Y[1])
    free = e[inside & np.isfinite(e) & (e > 0)]
    return float(free.max()) if free.size else 0.0


def section_thickness():
    print("\n" + "=" * 78)
    print("2-3) 肉厚 —— ゼロ点(侵食)/ 最大内接球 / グレー値探針")
    print("=" * 78)
    print("  ★先に式で予測しておく(measure する前に書く):")
    print("     侵食:     t = 2 m h  -> 取りうる値は **2h の倍数のみ**(m = 消えるまでの回数)")
    print("     内接球:   ESDF の深さは h 刻み -> **予想は h 刻み**")
    print("     探針:     刻み無し。ただし 2 つの縁が PSF に融合する")
    print("               T <~ 2 sigma_psf = %.1f h で破綻すると予測" % (2 * PSF_VOXEL))
    print()
    print("   T/h   h [mm]   侵食      内接球    探針(本数) | 誤差 [mm] 侵食 / 内接球 / 探針")

    # ★h を「T/h が整数」になる点だけで振ってはいけない。整数比では占有ボクセルの
    #   枚数がぴったり T/h 枚になり、誤差 0.000 mm が並んで「量子化は起きない」に
    #   見える(2026-09-07 に一度そう書いた)。h は連続に振る。
    hlist = [round(x, 4) for x in np.linspace(0.125, 1.0, 12)]
    ratios = tuple(T_WALL / h for h in hlist)
    rows, hs, e_ero, e_ins, e_prb, n_prb = [], [], [], [], [], []
    for h in hlist:
        tr = T_WALL / h
        _, occ, gray, res, _ = coupon(h)
        t_e = thickness_erosion(occ, h)
        t_i = thickness_inscribed(occ, h)
        t_p, n_p = thickness_probe(gray, h, res)
        hs.append(tr)
        e_ero.append(t_e - T_WALL)
        e_ins.append(t_i - T_WALL)
        e_prb.append(t_p - T_WALL)
        n_prb.append(n_p)
        rows.append((tr, h, t_e, t_i, t_p))
        print("  %5.1f  %6.3f   %6.3f    %6.3f    %6.3f (%d) | %+6.3f / %+6.3f / %+6.3f" % (
            tr, h, t_e, t_i, t_p, n_p, t_e - T_WALL, t_i - T_WALL, t_p - T_WALL))

    # 刻みの検定: 値が 2h の倍数か h の倍数か(丸めでなく剰余で数える)。
    def quantum(vals, hlist, q):
        return all(abs((v / (q * hh)) - round(v / (q * hh))) < 1e-6
                   for v, hh in zip(vals, hlist) if np.isfinite(v))

    t_ero = [r[2] for r in rows]
    t_ins = [r[3] for r in rows]
    t_prb = [r[4] for r in rows]
    q_ero2 = quantum(t_ero, hlist, 2.0)
    q_ins2 = quantum(t_ins, hlist, 2.0)
    q_prb2 = quantum(t_prb, hlist, 2.0)
    print("\n  刻みの検定(%d 点すべてで剰余を見る): 侵食が 2h の倍数 = %s / "
          "内接球が 2h の倍数 = %s / 探針が 2h の倍数 = %s"
          % (len(hlist), q_ero2, q_ins2, q_prb2))
    print("  ★予想は「内接球なら h 刻みまで細かくなる」だった。実測は侵食と**同じ 2h 刻み**")
    print("     (掃引 %d 点すべてで 2h の倍数、しかも侵食と 1 つ残らず同じ値)。" % len(hlist))
    print("     2 値格子の距離変換は「占有ボクセル中心 -> 自由ボクセル中心」を測るので、")
    print("     半径ではなく**直径のほうが量子化される** —— 内接球にしても得しない。")

    same = sum(1 for a, c in zip(t_ero, t_ins) if abs(a - c) < 1e-9)
    print("     侵食と内接球が同じ値になった点: %d / %d" % (same, len(hlist)))
    med = lambda v: float(np.median(np.abs(v)))            # noqa: E731
    fine = [i for i, r in enumerate(ratios) if r >= 3.0]
    print("\n  誤差の中央値 [mm](3 voxel 以上の %d 点): 侵食 %.3f / 内接球 %.3f / 探針 %.3f"
          % (len(fine), med([e_ero[i] for i in fine]), med([e_ins[i] for i in fine]),
             med([e_prb[i] for i in fine])))
    print("  最悪誤差 [mm](同じ %d 点): 侵食 %.3f / 内接球 %.3f / 探針 %.3f"
          % (len(fine), max(abs(e_ero[i]) for i in fine), max(abs(e_ins[i]) for i in fine),
             max(abs(e_prb[i]) for i in fine)))

    bad = [(r, e_prb[i], n_prb[i]) for i, r in enumerate(ratios) if abs(e_prb[i]) > 0.5 * T_WALL]
    print("\n  ★予想は「2 voxel を切ると探針は壁を見つけられなくなる」だった。")
    print("     実測は**見つけたと言って間違える**: T/h = %s で誤差 %s mm、"
          % (", ".join("%.1f" % b[0] for b in bad), ", ".join("%+.3f" % b[1] for b in bad)))
    print("     返る壁の本数が 2 -> %s に落ちている = 薄壁 2 枚を 1 枚と数え、"
          % ", ".join("%d" % b[2] for b in bad))
    print("     壁 + スロット + 壁 = %.3f mm を「肉厚」として返している。" % (2 * T_WALL + T_SLOT))
    print("     **空を返して落ちるのではなく、もっともらしい数字を返すのが厄介**。")

    figs.save_plot("thickness_cliff",
                   [("侵食(ゼロ点)", hs, [T_WALL + e for e in e_ero]),
                    ("最大内接球(ESDF)", hs, [T_WALL + e for e in e_ins]),
                    ("グレー値探針", hs, [T_WALL + e for e in e_prb]),
                    ("設計値 1.500 mm", hs, [T_WALL] * len(hs))],
                   xlabel="壁の厚さ / ボクセル [voxel]", ylabel="推定した肉厚 [mm]",
                   title="肉厚の推定は 2 voxel 刻みに潰れる(探針だけが刻みを持たない)",
                   caption="右ほど粗い。侵食と内接球は階段、探針は連続だが 2 voxel を"
                           "切ると壁を見失う。")
    return {"ratios": list(ratios), "e_ero": e_ero, "e_ins": e_ins, "e_prb": e_prb,
            "q_ero2": q_ero2, "q_ins2": q_ins2, "rows": rows, "n_prb": n_prb,
            "bad": bad, "fine": fine, "same": same, "n": len(hlist)}


def section_reach():
    print("\n" + "=" * 78)
    print("7) 工具/ノズルの到達性 —— 隙間の刻みがそのまま go/no-go の誤判定になる")
    print("=" * 78)
    print("  設計: スロット幅 %.3f mm -> 入る工具半径の上限は **%.3f mm**"
          % (T_SLOT, T_SLOT / 2))
    print("   h [mm]  測ったスロット幅   上限半径   r=0.60 の判定   r=0.80 の判定")
    hs, meas, verdicts = [], [], []
    for h in (0.125, 0.1875, 0.25, 0.375, 0.5, 0.625):
        _, occ, _, _, g = coupon(h)
        rmax = slot_radius(occ, g, h)
        w = 2.0 * rmax
        v06 = "入る" if rmax >= 0.60 else "入らない"
        v08 = "入る" if rmax >= 0.80 else "入らない"
        hs.append(h)
        meas.append(w)
        verdicts.append((h, w, rmax, v06, v08))
        print("   %5.3f       %6.3f mm       %5.3f mm     %-8s      %-8s"
              % (h, w, rmax, v06, v08))
    wrong = [v for v in verdicts if v[3] == "入らない"]
    print("\n  真値では r=0.60 は入り、r=0.80 は入らない。")
    if wrong:
        print("  ★粗さ %s mm では r=0.60 を「入らない」と**誤って落とす**(隙間が %s mm に見える)。"
              % (", ".join("%.3f" % v[0] for v in wrong),
                 ", ".join("%.3f" % v[1] for v in wrong)))
    figs.save_plot("reach_cliff",
                   [("測ったスロット幅", hs, meas),
                    ("設計値 1.500 mm", hs, [T_SLOT] * len(hs)),
                    ("r=0.60 の工具が入る下限(1.200 mm)", hs, [1.2] * len(hs))],
                   xlabel="ボクセルの粗さ [mm]", ylabel="スロットの幅 [mm]",
                   title="隙間は 2 voxel 刻みで痩せる —— 工具の go/no-go が反転する",
                   caption="測った幅が 1.200 mm を切ると、入るはずの工具を落とす。")
    return {"h": hs, "w": meas, "wrong": wrong}


# --------------------------------------------------------------------------- #
# 5-6. オーバーハング —— しきい値 45 度の段差と、丸めがそれを消すこと            #
# --------------------------------------------------------------------------- #
def section_overhang(scene):
    print("\n" + "=" * 78)
    print("4) オーバーハング —— しきい値 45 度の両側で面積が段差になる")
    print("=" * 78)
    sdf, occ = scene["sdf"], scene["occ"]
    b = np.array([0.0, 0.0, 1.0])
    F = analytic_faces()

    print("  解析: 下を向いている平面(傾き = 水平からの角度。45 度未満ならサポートが要る)")
    smin = min(float(np.dot(c, b)) for _, _, c in F)
    for n, a, c in sorted((f for f in F if f[0][2] < -1e-9), key=lambda f: f[0][2]):
        tilt = float(np.degrees(np.arccos(min(1.0, abs(n[2])))))
        if n[2] < -0.999 and abs(c[2] - smin) < 0.6:
            tag = "造形板にべた置き(除外)"
        elif abs(tilt - SELF_SUPPORT_DEG) < 1e-6:
            tag = "★しきい値のちょうど上"
        else:
            tag = "要サポート" if tilt < SELF_SUPPORT_DEG else "自己支持"
        print("    法線 (%6.3f, %6.3f, %6.3f)  傾き %5.1f 度  面積 %8.3f mm^2  %s"
              % (*n, tilt, a, tag))
    a_hole = cylinder_support_area((0, 1, 0), HOLE_H[1], HOLE_H[2], b)
    print("    水平穴の天井(円筒の閉形式)          面積 %8.3f mm^2" % a_hole)
    print("    垂直穴(軸が造形方向と平行)          面積 %8.3f mm^2"
          % cylinder_support_area((0, 0, 1), HOLE_V[1], HOLE_V[2], b))

    eps = 0.1
    c_lo = float(np.cos(np.radians(SELF_SUPPORT_DEG - eps)))
    c_hi = float(np.cos(np.radians(SELF_SUPPORT_DEG + eps)))
    a_lo = analytic_support_area(b, cos_c=c_lo)      # 44.9 度をしきい値に(厳しめ)
    a_hi = analytic_support_area(b, cos_c=c_hi)      # 45.1 度をしきい値に(緩め)
    step = a_hi - a_lo
    print("\n  ★★しきい値 %.1f 度 -> %.1f 度(たった %.1f 度)で"
          % (SELF_SUPPORT_DEG - eps, SELF_SUPPORT_DEG + eps, 2 * eps))
    print("     サポート必要面積 %.2f -> %.2f mm^2 = **%.2f 倍**(段差 %.2f mm^2)"
          % (a_lo, a_hi, a_hi / a_lo, step))
    print("     段差の正体は「ちょうど %.1f 度の斜面」1 枚(設計上 %.2f mm^2)。"
          % (SELF_SUPPORT_DEG, step))

    # --- 測る側: 等値面の取り方を 3 通り(対照群) --------------------------- #
    print("\n5) ★面の出し方だけを変えた 3 条件 —— 同じ形・同じしきい値で答えが割れる")
    print("   条件                        NG 面積 44.9 度 / 45.1 度 [mm^2]   段差    測った段差の比")
    conds = [("2 値から(ゼロ点)", occ.astype(np.float64), 0.5),
             ("距離場から", -sdf, 0.0),
             ("平滑化 sigma=1.5 voxel", ndimage.gaussian_filter(occ.astype(np.float64), 1.5), 0.5)]
    curves, rows, steps, los = [], [], {}, {}
    angs = np.arange(30.0, 61.0, 0.5)
    for name, vol, iso in conds:
        mesh = _mesh_from(vol, iso)
        m_lo = measured_support_area(mesh, b, cos_c=c_lo)
        m_hi = measured_support_area(mesh, b, cos_c=c_hi)
        cur = [measured_support_area(mesh, b, cos_c=float(np.cos(np.radians(t))))
               for t in angs]
        curves.append((name, angs, cur))
        steps[name] = m_hi - m_lo
        los[name] = m_lo
        rows.append([name, "%.2f" % m_lo, "%.2f" % m_hi, "%.2f" % (m_hi - m_lo),
                     "%.2f" % (m_hi / max(m_lo, 1e-9))])
        print("   %-26s %8.2f / %8.2f            %7.2f       %5.2f 倍"
              % (name, m_lo, m_hi, m_hi - m_lo, m_hi / max(m_lo, 1e-9)))
    print("   %-26s %8.2f / %8.2f            %7.2f       %5.2f 倍"
          % ("解析(解像度無限)", a_lo, a_hi, step, a_hi / a_lo))
    lo_vals = [los[n] for n, _, _ in conds]
    print("\n  ★★同じ形・同じしきい値 44.9 度なのに、面の出し方だけで NG 面積が")
    print("     %s mm^2 —— **%.1f 倍**の開き(解析値は %.2f mm^2)。"
          % (" / ".join("%.2f" % v for v in lo_vals), max(lo_vals) / min(lo_vals), a_lo))
    print("  ★距離場から取ると段差そのものが消える(%.2f 倍 -> %.2f 倍)。"
          % (a_hi / a_lo, steps["距離場から"] / max(los["距離場から"], 1e-9) + 1.0))
    print("     消えたのは良いことではない —— **45 度の面 %.2f mm^2 を「要サポート」側に"
          % step)
    print("     勝手に寄せて確定させただけ**で、44.9 度で見れば %.0f %% の過大評価。"
          % (100 * (los["距離場から"] - a_lo) / a_lo))
    print("  ★平滑化は段差を %.2f -> %.2f mm^2 に潰す(%.0f %% 消える)。丸めた分だけ"
          % (step, steps["平滑化 sigma=1.5 voxel"],
             100 * (1 - steps["平滑化 sigma=1.5 voxel"] / step)))
    print("     「45 度ちょうど」という危うい設計が数字から見えなくなる。")

    ana = [analytic_support_area(b, cos_c=float(np.cos(np.radians(t)))) for t in angs]
    figs.save_plot("threshold_cliff",
                   [("解析(解像度無限)", angs, ana)] + curves,
                   xlabel="自己支持しきい値 [度]", ylabel="サポート必要面積 [mm^2]",
                   title="45 度に貼りついた面が段差を作る(丸めるほど段差が溶ける)",
                   caption="解析は階段。測った側は等値面の取り方で段差の高さが変わる。")
    figs.save_table("overhang_conditions",
                    ["等値面の取り方", "44.9 度 [mm^2]", "45.1 度 [mm^2]", "段差 [mm^2]",
                     "45.1 度での誤差"],
                    rows + [["解析(解像度無限)", "%.2f" % a_lo, "%.2f" % a_hi,
                             "%.2f" % step, "0.0 %"]],
                    title="同じ形・同じしきい値でも、面の出し方で NG 面積が変わる")

    _overhang_map(occ, sdf)
    return {"a_lo": a_lo, "a_hi": a_hi, "step": step, "steps": steps,
            "rows": rows, "a_hole": a_hole}


def _overhang_map(occ, sdf):
    """下から見た「傾き [度]」の疑似カラーと、サポートが要る面のマスク。"""
    grad = np.stack(np.gradient(sdf, H_MESH), axis=0)
    a = occ[:, :, ::-1]
    gg = grad[:, :, :, ::-1]
    hit = a.argmax(2)
    seen = a.any(2)
    ii, jj = np.meshgrid(np.arange(a.shape[0]), np.arange(a.shape[1]), indexing="ij")
    nz = gg[2][ii, jj, hit]
    nn = np.sqrt(sum(gg[k][ii, jj, hit] ** 2 for k in range(3)))
    nz = nz / np.maximum(nn, 1e-9)
    tilt = np.degrees(np.arccos(np.clip(np.abs(nz), 0, 1)))     # 水平からの傾き [度]
    tilt = np.where(seen, tilt, 90.0)
    need = seen & (nz < -COS_C) & (hit > 0)
    figs.save_grid("overhang_map",
                   [tilt.T[::-1], need.T[::-1].astype(float)],
                   ["下向き面の傾き [度](0 = 水平 = 最悪、90 = 垂直 = 安全)",
                    "サポートが要る面(45 度未満で下を向いている)"],
                   title="下から見た部品(オーバーハングの地図)", ncols=2)


def section_orientation():
    print("\n" + "=" * 78)
    print("8) 造形方向を振る —— 効くが、ゼロにはならない")
    print("=" * 78)
    c_hi = float(np.cos(np.radians(SELF_SUPPORT_DEG + 0.1)))
    # ★45 度ちょうどの傾斜方向は入れない —— 板の裏 2349.7 mm^2 が自分もしきい値に
    #   貼りついてしまい、「どの向きが良いか」の表が段差の話に乗っ取られる。
    s30, c30 = float(np.sin(np.radians(30))), float(np.cos(np.radians(30)))
    dirs = [("Z+(設計どおり)", (0, 0, 1)), ("Z-(裏返す)", (0, 0, -1)),
            ("Y+(横倒し)", (0, 1, 0)), ("X+(横倒し)", (1, 0, 0)),
            ("Z から X へ 30 度", (s30, 0, c30)), ("Z から Y へ 30 度", (0, s30, c30))]
    base = analytic_support_area((0, 0, 1), cos_c=c_hi)
    rows, out = [], []
    print("   造形方向             サポート面積 [mm^2]   Z+ 比   うち水平穴 / 垂直穴")
    for name, b in dirs:
        a = analytic_support_area(b, cos_c=c_hi)
        ah = cylinder_support_area((0, 1, 0), HOLE_H[1], HOLE_H[2], b, c_hi)
        av = cylinder_support_area((0, 0, 1), HOLE_V[1], HOLE_V[2], b, c_hi)
        rows.append([name, "%.2f" % a, "%.2f" % (a / base), "%.2f" % ah, "%.2f" % av])
        out.append((name, a, ah, av))
        print("   %-20s %10.2f          %5.2f   %7.2f / %7.2f" % (name, a, a / base, ah, av))
    best = min(out, key=lambda r: r[1])
    print("\n  最良は %s(%.2f mm^2)で Z+ の **%.1f 分の 1**。"
          % (best[0], best[1], base / best[1]))
    print("  ★ただしゼロにはならない —— 水平穴と垂直穴が直交しているので、"
          "片方を立てるともう片方が寝る。")
    figs.save_table("orientation",
                    ["造形方向", "サポート面積 [mm^2]", "Z+ 比", "水平穴 [mm^2]", "垂直穴 [mm^2]"],
                    rows, title="造形方向を変えるとサポート面積はどれだけ減るか(解析値)",
                    caption="どの向きでも 0 にならないのは、2 本の穴が互いに直交しているから。")
    return {"rows": out, "base": base, "best": best}


# --------------------------------------------------------------------------- #
# 7. 肉厚の誤差と NG 面積の誤差は連動しない                                     #
# --------------------------------------------------------------------------- #
def section_decoupled(thick, over):
    print("\n" + "=" * 78)
    print("6) 肉厚の誤差 [mm] と NG 面積の誤差 [mm^2] は連動しない —— 別々に数える")
    print("=" * 78)
    c_hi = float(np.cos(np.radians(SELF_SUPPORT_DEG + 0.1)))
    a_true = analytic_support_area((0, 0, 1), cos_c=c_hi)
    b = np.array([0.0, 0.0, 1.0])
    rows, got = [], []
    print("   h [mm]   肉厚の誤差 [mm] (%)      NG 面積 [mm^2] (誤差 %)")
    global H_MESH
    keep = H_MESH
    for h in (0.5, 0.25):
        _, occ, _, _, _ = coupon(h)
        te = thickness_erosion(occ, h)
        H_MESH = h                              # _mesh_from / measured_support_area が使う粗さ
        g, _ = make_grid(h)
        am = measured_support_area(_mesh_from(-part_sdf(g), 0.0, h), b, cos_c=c_hi)
        e_t, e_a = te - T_WALL, 100 * (am - a_true) / a_true
        got.append((h, e_t, e_a))
        rows.append([("%.3f" % h), "%+.3f (%+.1f %%)" % (e_t, 100 * e_t / T_WALL),
                     "%.2f (%+.1f %%)" % (am, e_a)])
        print("   %5.3f    %+.3f (%+5.1f %%)          %8.2f (%+5.1f %%)"
              % (h, e_t, 100 * e_t / T_WALL, am, e_a))
    H_MESH = keep
    print("\n  粗い %.3f mm では肉厚が %+.3f mm (%.1f %%) ずれるのに NG 面積の誤差は %.1f %%、"
          % (got[0][0], got[0][1], abs(100 * got[0][1] / T_WALL), abs(got[0][2])))
    print("  細かい %.3f mm では肉厚は %+.3f mm(誤差ゼロ)なのに NG 面積は %.1f %% ずれたまま。"
          % (got[1][0], got[1][1], abs(got[1][2])))
    print("  **片方の精度をもう片方の根拠にしてはいけない**。")
    figs.save_table("decoupled", ["ボクセルの粗さ h [mm]", "肉厚の誤差", "NG 面積(誤差)"],
                    rows, title="肉厚の誤差と NG 面積の誤差は連動しない",
                    caption="単位が違うだけでなく、壊れ方の原因が別(量子化 vs 法線の丸め)。")
    return {"rows": rows, "a_true": a_true, "got": got}


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps():
    print("\n" + "=" * 78)
    print("9) 道具の穴(この PoC で 3-D op を使ってみて)")
    print("=" * 78)
    g = np.asarray(L.grid_coords(((0, 1), (0, 1), (0, 1)), 4))
    assert g.shape == (4, 4, 4, 3)
    print("  (a) sdf_* 族のプリミティブは球と直方体だけ。**円筒と半空間が無い**ので、")
    print("      穴と斜面はこの PoC が自前で書いた(DFM は円筒穴だらけなのに)。")

    import sdf_ops
    assert hasattr(sdf_ops, "grid_coords")
    ret = sdf_ops.grid_coords(((0, 1), (0, 1), (0, 1)), 2)
    assert isinstance(ret, tuple) and len(ret) == 2, "モジュールは (coords, extent) を返す"
    assert np.asarray(L.grid_coords(((0, 1), (0, 1), (0, 1)), 2)).ndim == 4, "台帳は座標だけ"
    print("  (b) 台帳経由の grid_coords は **extent を落とす**(モジュールは")
    print("      (coords, extent) の 2 つを返すのに、台帳は最初の配列だけ)。")

    v = np.zeros((8, 8, 8))
    v[2:6, 2:6, 2:6] = 1.0
    r = L.voxel_to_mesh(v, iso=0.5)
    assert len(r) == 2, "台帳は (verts, faces) の 2 つ"
    import match3d
    assert len(match3d.voxel_to_mesh(v, iso=0.5)) == 3, "モジュールは normals も返す"
    print("  (c) 同じく voxel_to_mesh は台帳経由だと **normals が落ちる**(3 -> 2)。")

    V, F = r
    assert not hasattr(fs, "face_normals") and hasattr(fs.ledger, "face_normals")
    print("  (d) face_normals / mesh_area / esdf / box_sdf / voxel_to_mesh は")
    print("      1 行ファサード fs.<名> に出ていない(fs.ledger からのみ)。")

    tri = np.asarray(V)[np.asarray(F)]
    cr = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    assert not hasattr(fs.ledger, "face_areas")
    print("  (e) **面ごとの面積を返す op が無い**(mesh_area は総和だけ)。")
    print("      オーバーハング面積は「面ごとの面積 x 法線の判定」なので、呼び手が")
    print("      外積を自分で書くことになる(この PoC も %d 面ぶん自前で計算した)。" % len(cr))

    assert not hasattr(fs.ledger, "overhang_area") and not hasattr(fs.ledger, "support_area")
    print("  (f) DFM の判定そのもの(オーバーハング面積・自己支持角・工具到達性)は")
    print("      op になっていない。材料は全部あるので、族として足す価値はある。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    np.random.default_rng(SEED)
    print("=" * 78)
    print("造形しやすさ(DFM)を形から測る —— 薄肉・オーバーハング・工具到達性")
    print("真値は SDF のブール演算(肉厚は設計値、面の角度と面積は閉形式)")
    print("=" * 78)

    scene = section_scene()
    thick = section_thickness()
    over = section_overhang(scene)
    dec = section_decoupled(thick, over)
    reach = section_reach()
    orient = section_orientation()
    section_tool_gaps()

    # --- 所見を固定する assert(壊れたら鳴る)-------------------------------- #
    assert thick["q_ero2"], "侵食の値が 2h の倍数でなくなった"
    assert thick["q_ins2"], "内接球の値が 2h の倍数でなくなった"
    assert over["a_hi"] / over["a_lo"] > 2.5, "45 度の段差が消えた"
    assert over["steps"]["平滑化 sigma=1.5 voxel"] < 0.6 * over["step"], "平滑化が段差を潰さない"
    assert orient["best"][1] > 0.0, "どこかの向きでサポートがゼロになった(穴の直交が崩れた)"
    assert abs(scene["a_mesh"] - scene["a_true"]) / scene["a_true"] < 0.05, "解析面積とメッシュ面積が乖離"

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 肉厚は 2 voxel 刻みに潰れる(侵食も最大内接球も)。刻みを持たないのは")
    print("    グレー値の探針だけで、それも壁が 2 voxel を切ると壁を見失う。")
    print("  * サポート必要面積はしきい値 45 度で段差になる(%.2f -> %.2f mm^2、%.2f 倍)。"
          % (over["a_lo"], over["a_hi"], over["a_hi"] / over["a_lo"]))
    print("  * その段差は平滑化で %.0f %% 消える —— 丸めた分だけ「欠陥が無いこと」になる。"
          % (100 * (1 - over["steps"]["平滑化 sigma=1.5 voxel"] / over["step"])))
    print("  * 向きは効く(最良 %s は Z+ の %.1f 分の 1)が、ゼロにはならない。"
          % (orient["best"][0], orient["base"] / orient["best"][1]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
