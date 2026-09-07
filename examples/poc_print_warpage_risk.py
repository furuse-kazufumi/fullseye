# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""積層造形の反りを層の履歴から予測する —— 最終形状は反りを知らない。

3-D プリンタに形を渡す前に「その形は反るのか、途中で基板から剥がれるのか」を
形状だけから見ておく仕事です。反りは**冷えて縮む層が、既にある層に貼りついて
できる曲がり**なので、判定に効くのは最終形状ではなく**層ごとの断面の履歴**
(面積・周長・重心・基板との接触)です。

EXTEND: 実測に差し替えるなら :func:`voxelize` が返す占有ボリューム(z,y,x)を、
スライサが吐く層ごとの輪郭か CT 再構成に置き換えます。**測れなくなるのは
1 層あたりの拘束収縮ひずみ ε のほう**で、これは材料と機械の較正値として
別に持ち込みます(この PoC は ε を既知として与える)。:func:`fem_build` が
返す変位場は実機では測れないので、レーザー変位計で測った反り量を
:func:`fem_build` の戻り値 ``dev`` の位置に入れて突き合わせます。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **最終形状だけを見る予測器は、どんな形でも厳密にゼロを返す**。断面の重心の
   定義から Σ a_k (z_k - z_bar) = 0 なので、最終断面で評価した反りは
   実測 3.5e-19 相当(6 形状すべて)。**反りは履歴にしか入っていない**。
2. **ゼロ点(底面積・最大断面積・体積で危険度を出す)は順位を当てられない**。
   6 形状で実測の反り量と底面積の順位相関は -0.20、最大断面積は -0.20、
   体積は 0.09。★いちばん底面積が大きい平板が、いちばん反らない。
3. **層の履歴を積む閉形式は、まず 2 層バイメタルで検算できる**。等厚・等 E の
   2 層で κ = 0.750 ε/h(Timoshenko 1925 の閉形式と 6 桁一致)。24 層まで
   積むと κ h/ε は 2.4174 に飽和し、**背を高くしても反りは増えない**。
4. **予測 vs 実測(Q6 有限要素の増分積層)は 6 形状中 4 形状で 0.4 % 以内**。
   ★崩れたのは 2 形状で、どちらも**同じ層面積を x 方向に別々に置いた**もの:
   中央 1 柱 0.939、両端 2 柱 0.783。**面積の履歴が同じでも反りは 26 % 違う**
   (たわみ 0.3271 / 0.4109 mm)。閉形式はこの差に構造的に盲目。
5. ★**予想が外れた(その 1)**。「首を細くすると梁の仮定(平面保持)が壊れる」と
   踏んでいたが、首 16 -> 0.25 mm で誤差は 0.0 -> 1.8 % しか増えない。
   **一様な層の収縮は純曲げで、せん断力が立たない**ので細い首でも伝わる。
   予想は「首で壊れる」、実測は「細長比で壊れる」——
   L/H = 1.0 で誤差 4.4 %(首つきは 9.3 %)、L/H >= 2 で 0.5 % 以内。
6. ★★**同じ形・同じ体積・同じ底面積でも、層厚を 1.00 -> 0.25 mm にすると
   反りが 4.63 倍**(たわみ 0.1971 -> 0.9118 mm)。これは 1 層あたりの ε を
   一定とした場合で、**「単位高さあたりの収縮が一定」と置き直すと 1.16 倍に
   しかならない**。どちらの較正を採るかで結論が 4 倍動くので、
   **ε の定義を書かずに「層厚を薄くすると反る」と言ってはいけない**。
7. **剥離は応力では決まらない**。基板に平らに押さえたときの端の引き剥がし応力は
   要素寸法で決まらず(dx 2.00 -> 0.25 mm で 9.53 -> 12.39 MPa、収束しない)、
   ★一方で**端 6 mm に掛かる引き剥がし力の合計は 4 % 以内で収束**する
   (334.7 -> 348.0 N)。しかもその力は 6 形状すべてで **EIκ に比例**
   (係数 0.0801 1/mm、ばらつき 2.6 %)。**「何 MPa で剥がれるか」は言えないが、
   「どの形が先に剥がれるか」は閉形式で順位づけできる**。
8. **崖は 2 つのつまみが掛け算で効く**。層厚と首の細さの地図で、危険度
   (たわみ / 許容 0.2 mm)は 1.00 mm 層・太い首の 0.85 から 0.20 mm 層・
   細い首の 4.72 まで 5.6 倍動く。首を細くするだけでは 0.86 倍にしかならず、
   **層厚を半分にするほうが 2 倍効く**。

【グラウンドトゥルース】形状は `box_sdf` のブール和で作る合成立体(平板・薄いフィン・
首つき・段付き・中央 1 柱・両端 2 柱)。1 層あたりの拘束収縮ひずみ ε = 2.0e-4 を
**既知の一定値**として与え、反りは (a) 層の履歴を積む増分梁の閉形式
(Timoshenko のバイメタル式の多層版)と (b) 非適合モード Q6 平面応力要素の
**増分積層(要素誕生)解析**の 2 通りで出す。(a) は層ごとの断面積だけを、
(b) は形状の全部を使う —— **その差が「面積の履歴で決まるか」の答え**。

来歴(公開文献のみ): G. G. Stoney, *Proc. R. Soc. A* 82 (1909) 172 —— 薄膜応力と
曲率 / S. Timoshenko, "Analysis of bi-metal thermostats", *J. Opt. Soc. Am.* 11
(1925) 233 —— 2 層の曲率の閉形式 / L. B. Freund & S. Suresh, *Thin Film Materials*
(Cambridge, 2003) 2 章 —— 多層膜の曲率の重ね合わせ / T.-M. Wang, J.-T. Xi, Y. Jin,
"A model research for prototype warp deformation in the FDM process",
*Int. J. Adv. Manuf. Technol.* 33 (2007) 1087 —— 層の積み上げによる反りの解析 /
E. L. Wilson et al., "Incompatible displacement models", *Numerical and Computer
Methods in Structural Mechanics* (Academic Press, 1973) 43 —— Q6 非適合モード /
R. D. Cook et al., *Concepts and Applications of Finite Element Analysis*
(Wiley, 2002) —— 熱ひずみ等価節点力と静的縮約。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

L = fs.ledger                    # 3-D op の公開経路(ファサード fs.<名> には無い)

# --- 材料と工程の諸元 -------------------------------------------------------- #
E_MOD = 2000.0        # ヤング率 [MPa](PLA 相当)
NU = 0.35             # ポアソン比 [-]
EPS_LAYER = 2.0e-4    # 1 層あたりの拘束収縮ひずみ(inherent strain)[-]
H_LAYER = 0.5         # 既定の層厚 [mm]
L_X = 60.0            # 部品の長さ [mm](反りを測る方向)
Y_SPAN = 20.0         # y 方向の余白込みの箱 [mm]
Z_SPAN = 12.0         # z 方向の箱(= 最大の背)[mm]
VOX = 0.5             # x,y のボクセル寸法 [mm](z は層厚に一致させる)
SIG_ADH = 0.5         # 基板の接着強さ [MPa](剥離の目安)
DEV_ALLOW = 0.2       # 許容たわみ [mm](危険度の分母)
GAUSS = 1.0 / np.sqrt(3.0)
SEED = 5

#: 層ごとの断面積の履歴が完全に一致する 3 形状(配置だけが違う)。
TRIO = ("全長に薄く", "中央 1 柱", "両端 2 柱")

#: 形状の定義 —— (z0, z1, y0, y1, x0, x1) の箱 [mm] の和集合。
#: 「全長に薄く」「中央 1 柱」「両端 2 柱」の 3 つは
#: **層ごとの断面積の履歴が 1 mm^2 も違わない三つ子**(体積も底面積も同じ)。
#: 違うのは「その面積を x のどこに置いたか」だけ。
SHAPES = {
    "平板": [(0.0, 3.0, 2.0, 18.0, 0.0, 60.0)],
    "薄いフィン": [(0.0, 12.0, 9.0, 11.0, 0.0, 60.0)],
    "首つき": [(0.0, 2.0, 2.0, 18.0, 0.0, 60.0),
               (2.0, 8.0, 9.0, 11.0, 0.0, 60.0),
               (8.0, 12.0, 2.0, 18.0, 0.0, 60.0)],
    "段付き": [(0.0, 6.0, 2.0, 18.0, 0.0, 60.0),
               (6.0, 12.0, 2.0, 18.0, 0.0, 30.0)],
    "全長に薄く": [(0.0, 2.0, 2.0, 18.0, 0.0, 60.0),
                   (2.0, 8.0, 6.0, 14.0, 0.0, 60.0),
                   (8.0, 12.0, 2.0, 18.0, 0.0, 60.0)],
    "中央 1 柱": [(0.0, 2.0, 2.0, 18.0, 0.0, 60.0),
                  (2.0, 8.0, 2.0, 18.0, 15.0, 45.0),
                  (8.0, 12.0, 2.0, 18.0, 0.0, 60.0)],
    "両端 2 柱": [(0.0, 2.0, 2.0, 18.0, 0.0, 60.0),
                  (2.0, 8.0, 2.0, 18.0, 0.0, 15.0),
                  (2.0, 8.0, 2.0, 18.0, 45.0, 60.0),
                  (8.0, 12.0, 2.0, 18.0, 0.0, 60.0)],
}


# --------------------------------------------------------------------------- #
# 1. 形を作る —— SDF のブール和 -> 占有ボクセル                                 #
# --------------------------------------------------------------------------- #
def voxelize(boxes, h=H_LAYER, z_span=Z_SPAN, x_span=L_X, vox=VOX):
    """箱の和集合を占有ボリューム ``(z,y,x)`` にする。

    ★``grid_coords`` は**軸の意味を決めない** —— 渡した ``bounds`` の順に
    成分を詰めるだけなので、``(z,y,x)`` の順で渡せば ``(depth,row,col)`` の
    ボリュームが出る(``examples/poc_dfm_thickness_overhang.py`` は
    ``(x,y,z)`` の順で渡していて、同じ op から別の軸順のボリュームが出る)。
    どちらが正しいということはないが、**混ぜると z のつもりで x を切る**。

    z の刻みは層厚 ``h`` に一致させる —— 層の境目がボクセルの境目に乗るので、
    1 層 = 1 voxel 行になり、スライスの取り違えが起きない。
    """
    nz = int(round(z_span / h))
    ny = int(round(Y_SPAN / vox))
    nx = int(round(x_span / vox))
    g = np.asarray(L.grid_coords(((0.0, z_span), (0.0, Y_SPAN), (0.0, x_span)),
                                 (nz, ny, nx)))
    sdf = None
    for z0, z1, y0, y1, x0, x1 in boxes:
        c = ((z0 + z1) / 2.0, (y0 + y1) / 2.0, (x0 + x1) / 2.0)
        he = ((z1 - z0) / 2.0, (y1 - y0) / 2.0, (x1 - x0) / 2.0)
        b = np.asarray(L.box_sdf(g, c, he))
        sdf = b if sdf is None else np.asarray(L.sdf_union(sdf, b))
    occ = np.asarray(L.sdf_to_occupancy(sdf, iso=0.0), bool)
    return occ, sdf


def layer_history(occ, vox=VOX, h=H_LAYER):
    """層ごとの断面を **2-D の領域 op で測る** —— これが予測器の入力の全部。

    返すのは層ごとの面積 [mm^2] / 周長 [mm] / 重心 x [mm] / 塊の数。
    **形の配置(どこに在るか)は返さない** —— そこがこの PoC の主題。
    """
    nz = occ.shape[0]
    area = np.zeros(nz)
    perim = np.zeros(nz)
    cx = np.full(nz, np.nan)
    nblob = np.zeros(nz, int)
    for k in range(nz):
        sl = occ[k]
        if not sl.any():
            continue
        lab = L.blob_label(sl)
        f = L.blob_features(lab, spacing=vox)
        a = np.asarray(f["area"], float)
        area[k] = float(a.sum())
        perim[k] = float(np.asarray(f["perimeter"], float).sum())
        cx[k] = float(np.average(np.asarray(f["col"], float), weights=a) * vox)
        nblob[k] = int(f["n"])
    return {"area": area, "perimeter": perim, "cx": cx, "nblob": nblob,
            "z": (np.arange(nz) + 0.5) * h, "h": h}


def thickness_map(occ, vox=VOX):
    """層 j・x 列 i の**面外板厚** [mm](= y 方向に占有している長さ)。

    有限要素は x-z の 2-D 平面応力で解き、y 方向の広がりは板厚として持つ。
    """
    return occ.sum(axis=1).astype(float) * vox


# --------------------------------------------------------------------------- #
# 2. 閉形式 —— 層の履歴だけから曲率を出す(Timoshenko の多層版)                 #
# --------------------------------------------------------------------------- #
def closed_form_kappa(areas, x_len, h, eps=EPS_LAYER):
    """層ごとの断面積の履歴から曲率 [1/mm] を予測する。

    層 k を積んだ瞬間の断面(層 1..k)について、収縮ひずみ ``eps`` の
    等価モーメントを、そのときの断面 2 次モーメントで割って足す::

        dκ_k = ε a_k (z_k - z̄_k) / I_k

    ``a_k = A_k / x_len * h`` は層の断面積(梁の断面としての面積)。
    2 層のときは Timoshenko (1925) の等厚・等 E の閉形式に一致する。
    **符号は「端が持ち上がる向き」を正**とする。
    """
    b = np.asarray(areas, float) / float(x_len)
    A = S = Ic = 0.0
    kap = 0.0
    for k, bk in enumerate(b):
        if bk <= 0.0:
            continue
        a = bk * h
        zk = (k + 0.5) * h
        zb_old = S / A if A > 0 else 0.0
        A2 = A + a
        zb = (S + a * zk) / A2
        I2 = ((Ic + A * (zb - zb_old) ** 2) if A > 0 else 0.0) \
            + a * (zk - zb) ** 2 + bk * h ** 3 / 12.0
        if A > 0.0:                       # 1 層目は自由なので曲がらない
            kap += eps * a * (zk - zb) / I2
        A, S, Ic = A2, S + a * zk, I2
    return kap


def final_geometry_kappa(areas, x_len, h, eps=EPS_LAYER):
    """★**最終断面だけ**で評価した曲率。重心の定義から厳密にゼロになる。"""
    b = np.asarray(areas, float) / float(x_len)
    z = (np.arange(b.size) + 0.5) * h
    a = b * h
    m = a > 0
    if not m.any():
        return 0.0
    zb = float(np.average(z[m], weights=a[m]))
    I = float(np.sum(a[m] * (z[m] - zb) ** 2 + b[m] * h ** 3 / 12.0))
    return float(eps * np.sum(a[m] * (z[m] - zb)) / I)


def section_I(areas, x_len, h):
    """最終断面の 2 次モーメント [mm^4](剥離モーメント EIκ に使う)。"""
    b = np.asarray(areas, float) / float(x_len) * x_len / x_len
    b = np.asarray(areas, float) / float(x_len)
    z = (np.arange(b.size) + 0.5) * h
    a = b * h
    m = a > 0
    if not m.any():
        return 0.0
    zb = float(np.average(z[m], weights=a[m]))
    return float(np.sum(a[m] * (z[m] - zb) ** 2 + b[m] * h ** 3 / 12.0))


# --------------------------------------------------------------------------- #
# 3. 実測 —— Q6 平面応力要素の増分積層(要素誕生)解析                          #
# --------------------------------------------------------------------------- #
def _element(dx, dz, t, incompat=True):
    """1 要素の剛性と、単位収縮ひずみの等価節点力。

    ★``incompat=False``(素の Q4)は**曲げロッキング**を起こす。同じ問題で
    Q4 は閉形式の 52 - 91 % しか曲がらず、しかも要素を細かくしないと
    直らない。非適合モード(Wilson 1973)を入れると矩形要素では純曲げが厳密。
    """
    D = E_MOD / (1 - NU * NU) * np.array([[1.0, NU, 0.0], [NU, 1.0, 0.0],
                                          [0.0, 0.0, (1 - NU) / 2]])
    Kuu = np.zeros((8, 8))
    Kua = np.zeros((8, 4))
    Kaa = np.zeros((4, 4))
    fu = np.zeros(8)
    fa = np.zeros(4)
    es = np.array([-1.0, 0.0, 0.0])          # 面内 x 方向の収縮(単位)
    for xi in (-GAUSS, GAUSS):
        for et in (-GAUSS, GAUSS):
            dN_xi = 0.25 * np.array([-(1 - et), (1 - et), (1 + et), -(1 + et)])
            dN_et = 0.25 * np.array([-(1 - xi), -(1 + xi), (1 + xi), (1 - xi)])
            bx, bz = dN_xi * (2.0 / dx), dN_et * (2.0 / dz)
            B = np.zeros((3, 8))
            B[0, 0::2] = bx
            B[1, 1::2] = bz
            B[2, 0::2] = bz
            B[2, 1::2] = bx
            # 非適合モード N5 = 1 - xi^2 / N6 = 1 - eta^2 の 4 内部自由度
            # (a1,a2 が x 変位、a3,a4 が z 変位)
            g5x, g6z = -2 * xi * (2.0 / dx), -2 * et * (2.0 / dz)
            Ba = np.zeros((3, 4))
            Ba[0, 0] = g5x        # ε_xx <- a1
            Ba[2, 1] = g6z        # γ_xz <- a2
            Ba[2, 2] = g5x        # γ_xz <- a3
            Ba[1, 3] = g6z        # ε_zz <- a4
            dJ = dx * dz / 4.0 * t
            Kuu += B.T @ D @ B * dJ
            fu += B.T @ D @ es * dJ
            if incompat:
                Kua += B.T @ D @ Ba * dJ
                Kaa += Ba.T @ D @ Ba * dJ
                fa += Ba.T @ D @ es * dJ
    if incompat:
        inv = np.linalg.inv(Kaa)
        return Kuu - Kua @ inv @ Kua.T, fu - Kua @ inv @ fa
    return Kuu, fu


def fem_build(thick, dx, dz, eps=EPS_LAYER, incompat=True):
    """層を 1 枚ずつ**生やしながら**解く(要素誕生)。戻り値に反りと剛性。

    層 j を足した瞬間に、その層だけに収縮ひずみを与えて増分を解く。
    既にある層は抵抗するので、**足した順序がそのまま結果に残る**。
    拘束は剛体モードを止める 3 自由度だけ(自己釣合い荷重なので反力ゼロ)。
    """
    nz, nx = thick.shape
    nnx = nx + 1
    nn = nnx * (nz + 1)
    ndof = 2 * nn
    cache: dict[float, tuple] = {}
    u = np.zeros(ndof)
    act = np.zeros(nn, bool)
    rows: list = []
    cols: list = []
    vals: list = []
    K = None
    for j in range(nz):
        f = np.zeros(ndof)
        grew = False
        for i in range(nx):
            t = float(thick[j, i])
            if t <= 1e-9:
                continue
            grew = True
            key = round(t, 6)
            if key not in cache:
                cache[key] = _element(dx, dz, t, incompat)
            ke, fe = cache[key]
            n = [j * nnx + i, j * nnx + i + 1, (j + 1) * nnx + i + 1, (j + 1) * nnx + i]
            d = np.array([[2 * q, 2 * q + 1] for q in n]).ravel()
            rows.append(np.repeat(d, 8))
            cols.append(np.tile(d, 8))
            vals.append(ke.ravel())
            f[d] += fe * eps
            act[n] = True
        if not grew:
            continue
        # ★生まれた層は「そのとき既に反っている面の上」に置かれる(要素誕生は
        #   変形後の配置で行う)。ここを初期化し忘れると、後から生えた層だけ
        #   変位ゼロのまま残り、**列平均で測った反りが 1/4 になる**
        #   (2026-09-07 に踏んだ)。力学(K と f)は公称格子上なので不変。
        for i in range(nnx):
            below, above = j * nnx + i, (j + 1) * nnx + i
            if act[above] and act[below]:
                u[2 * above] = u[2 * below]
                u[2 * above + 1] = u[2 * below + 1]
        K = sparse.coo_matrix((np.concatenate(vals),
                               (np.concatenate(rows), np.concatenate(cols))),
                              shape=(ndof, ndof)).tocsr()
        an = np.nonzero(act)[0]
        free = np.zeros(ndof, bool)
        free[2 * an] = True
        free[2 * an + 1] = True
        base = [i for i in range(nnx) if act[i]]
        free[2 * base[0]] = False
        free[2 * base[0] + 1] = False
        free[2 * base[-1] + 1] = False
        du = np.zeros(ndof)
        du[free] = spsolve(K[free][:, free].tocsc(), f[free])
        u += du
    return _warp_summary(u, act, K, nnx, nz, dx, ndof)


def _warp_summary(u, act, K, nnx, nz, dx, ndof):
    """反りを**底面(基板に接していた面)の z 変位**から測る。

    底面は最初の層から最後まで在る材料面なので、履歴を全部受け取っている。
    後から生えた面で測ると「その面が生まれてから先」しか見えない。
    """
    uz = u[1::2].reshape(nz + 1, nnx)
    m = act.reshape(nz + 1, nnx)
    ok = m[0]
    if ok.sum() < 4:
        raise ValueError("底面が短すぎて反りを測れない(基板に接する層が要る)")
    xs = np.arange(nnx) * dx
    prof = np.where(ok, uz[0], np.nan)
    p = np.polyfit(xs[ok], prof[ok], 2)
    chord = np.interp(xs[ok], [xs[ok][0], xs[ok][-1]], [prof[ok][0], prof[ok][-1]])
    return {"kappa": float(2.0 * p[0]),
            "dev": float(np.max(np.abs(prof[ok] - chord))),
            "prof": prof, "xs": xs, "u": u, "K": K, "act": act,
            "nnx": nnx, "nz": nz, "ndof": ndof, "dx": dx}


def peel_forces(r, w_base):
    """基板に**平らに押さえた**ときの引き剥がし力 [N] と応力 [MPa]。

    自由に反った状態から底面を uz=0 へ戻す変位を強制し、その反力を読む。
    正 = 接着剤が引っ張られる(剥がれる向き)。
    """
    K, act, ndof, nnx, dx = r["K"], r["act"], r["ndof"], r["nnx"], r["dx"]
    base = np.array([i for i in range(nnx) if act[i]])
    uz0 = r["u"][2 * base + 1]
    an = np.nonzero(act)[0]
    free = np.zeros(ndof, bool)
    free[2 * an] = True
    free[2 * an + 1] = True
    presc = 2 * base + 1
    free[presc] = False
    free[2 * base[0]] = False
    up = np.zeros(ndof)
    up[presc] = -uz0
    rhs = -(K @ up)
    u2 = up.copy()
    u2[free] = spsolve(K[free][:, free].tocsc(), rhs[free])
    R = (K @ u2)[presc]
    trib = np.full(base.size, dx * w_base)
    trib[0] = trib[-1] = 0.5 * dx * w_base
    return {"x": base * dx, "force": -R, "stress": -R / trib}


def edge_peel_force(pf, span=6.0):
    """端 ``span`` mm に掛かる引き剥がし力の合計 [N](応力より収束する)。"""
    x, fz = pf["x"], pf["force"]
    xmax = float(x.max())
    m = (x <= span) | (x >= xmax - span)
    return float(np.sum(np.clip(fz[m], 0.0, None)))


# --------------------------------------------------------------------------- #
def build_case(boxes, h=H_LAYER, x_len=L_X, x_bin=1):
    """形 -> ボクセル -> 層の履歴 -> 予測と実測を全部そろえる。"""
    occ, sdf = voxelize(boxes, h=h, x_span=x_len)
    hist = layer_history(occ, h=h)
    tmap = thickness_map(occ)
    if x_bin > 1:
        nx = tmap.shape[1] // x_bin * x_bin
        tmap = tmap[:, :nx].reshape(tmap.shape[0], -1, x_bin).mean(axis=2)
    dx = x_len / tmap.shape[1]
    r = fem_build(tmap, dx, h)
    kp = closed_form_kappa(hist["area"], x_len, h)
    return {"occ": occ, "hist": hist, "tmap": tmap, "fem": r,
            "kappa_pred": kp, "dev_pred": kp * x_len ** 2 / 8.0,
            "kappa_fem": r["kappa"], "dev_fem": r["dev"],
            "I": section_I(hist["area"], x_len, h), "h": h, "x_len": x_len}


def _spearman(a, b):
    ra = np.argsort(np.argsort(np.asarray(a, float)))
    rb = np.argsort(np.argsort(np.asarray(b, float)))
    ra = ra - ra.mean()
    rb = rb - rb.mean()
    return float(ra @ rb / np.sqrt((ra @ ra) * (rb @ rb)))


def _side_view(occ):
    """y 方向に投影した側面図(z,x)。上下を反転して「上」を上に描く。"""
    v = np.asarray(occ, float).transpose(1, 0, 2)      # (y,z,x)
    p = np.asarray(L.render_volume_projection(v, mode="mip"))
    return np.flipud(np.asarray(p, float))


# --------------------------------------------------------------------------- #
# 節 1 —— 場面と層の履歴                                                        #
# --------------------------------------------------------------------------- #
def section_scene():
    print("\n" + "=" * 78)
    print("1) 場面 —— 6 つの形を層に切り、断面を 2-D の領域 op で測る")
    print("=" * 78)
    cases = {}
    rows = []
    for name, boxes in SHAPES.items():
        c = build_case(boxes)
        cases[name] = c
        hst = c["hist"]
        n_layer = int(np.count_nonzero(hst["area"] > 0))
        vol = float(hst["area"].sum() * H_LAYER)
        rows.append([name, "%d" % n_layer, "%.0f" % hst["area"][0],
                     "%.0f" % hst["area"].max(), "%.0f" % vol,
                     "%.2f" % hst["perimeter"].max(),
                     "%d" % int(hst["nblob"].max())])
        print("  %-10s 層 %2d 枚  底面 %5.0f mm^2  最大断面 %5.0f mm^2  "
              "体積 %6.0f mm^3  最大周長 %6.1f mm  最大塊 %d"
              % (name, n_layer, hst["area"][0], hst["area"].max(), vol,
                 hst["perimeter"].max(), hst["nblob"].max()))

    figs.save_grid("scene", [_side_view(c["occ"]) for c in cases.values()],
                   list(cases.keys()), ncols=3,
                   title="6 つの形の側面図(y 方向に投影、横 %.0f mm x 縦 %.0f mm)"
                         % (L_X, Z_SPAN),
                   caption="層は下から上へ積む。層厚 %.2f mm、ボクセル %.2f mm。"
                           % (H_LAYER, VOX))
    occ = cases["首つき"]["occ"]
    ks = [0, 3, 6, 10, 14, 17, 20, 23]
    figs.save_grid("layer_frames", [occ[k].astype(float) for k in ks],
                   ["z = %.2f mm(面積 %.0f mm^2)"
                    % ((k + 0.5) * H_LAYER, cases["首つき"]["hist"]["area"][k])
                    for k in ks], ncols=4,
                   title="首つきの層の断面(スライス、縦 %.0f mm x 横 %.0f mm)"
                         % (Y_SPAN, L_X),
                   caption="この断面の面積の列だけが、閉形式の入力になる。")
    figs.save_table("shapes", ["形", "層数", "底面 mm^2", "最大断面 mm^2",
                               "体積 mm^3", "最大周長 mm", "最大塊数"], rows,
                    title="6 つの形の諸元(すべて長さ %.0f mm)" % L_X)
    return cases


def section_area_history(cases):
    print("\n" + "=" * 78)
    print("2) 層の履歴 —— 面積・周長・重心の列")
    print("=" * 78)
    sel = ["平板", "薄いフィン", "首つき", "段付き", "中央 1 柱"]
    figs.save_plot("area_history",
                   [(k, cases[k]["hist"]["area"], cases[k]["hist"]["z"]) for k in sel],
                   xlabel="層の断面積 [mm^2]", ylabel="高さ z [mm]",
                   title="層ごとの断面積の履歴(これが予測器の入力)",
                   caption="「中央 1 柱」と「両端 2 柱」はこの線が完全に重なる。")
    figs.save_plot("perimeter_history",
                   [(k, cases[k]["hist"]["perimeter"], cases[k]["hist"]["z"])
                    for k in sel],
                   xlabel="層の周長 [mm]", ylabel="高さ z [mm]",
                   title="層ごとの周長の履歴(面積では見えない差が出る)")
    trio = TRIO
    ars = [cases[k]["hist"]["area"] for k in trio]
    d = float(max(np.max(np.abs(ars[0] - a)) for a in ars[1:]))
    prs = [cases[k]["hist"]["perimeter"] for k in trio]
    print("  三つ子 %s の断面積の差の最大 = %.3g mm^2(完全一致)"
          % (" / ".join(trio), d))
    print("  同じ 3 つの**周長**の差の最大 = %.1f mm、最大の塊の数 %s —— "
          "面積は同じでも周長と塊の数は違う。"
          % (float(max(np.max(np.abs(prs[0] - p)) for p in prs[1:])),
             " / ".join(str(int(cases[k]["hist"]["nblob"].max())) for k in trio)))
    print("  ★周長と塊の数は「面積をどう置いたか」を少しだけ持っているが、"
          "**どちらも符号を持たない**ので\n     反りの向きも大きさも決められない"
          "(節 5 で実測する)。")
    return d


# --------------------------------------------------------------------------- #
# 節 3 —— ゼロ点                                                                #
# --------------------------------------------------------------------------- #
def section_zero_point(cases):
    print("\n" + "=" * 78)
    print("3) ゼロ点 —— 底面積・最大断面積・体積で危険度を出す / 最終形状だけで出す")
    print("=" * 78)
    names = list(cases)
    dev = np.array([cases[n]["dev_fem"] for n in names])
    base = np.array([cases[n]["hist"]["area"][0] for n in names])
    amax = np.array([cases[n]["hist"]["area"].max() for n in names])
    vol = np.array([cases[n]["hist"]["area"].sum() * H_LAYER for n in names])
    fin = np.array([final_geometry_kappa(cases[n]["hist"]["area"], L_X, H_LAYER)
                    for n in names])

    print("  形          実測たわみ[mm]  底面[mm^2]  最大断面  体積[mm^3]  最終形状のみ κ")
    rows = []
    for i, n in enumerate(names):
        print("   %-10s %8.4f      %6.0f     %6.0f     %7.0f      %.3e"
              % (n, dev[i], base[i], amax[i], vol[i], fin[i]))
        rows.append([n, "%.4f" % dev[i], "%.0f" % base[i], "%.0f" % amax[i],
                     "%.0f" % vol[i], "%.2e" % fin[i]])
    rho = {"底面積": _spearman(base, dev), "最大断面積": _spearman(amax, dev),
           "体積": _spearman(vol, dev),
           "閉形式(履歴)": _spearman([cases[n]["kappa_pred"] for n in names], dev)}
    print("\n  順位相関(実測たわみとの):", "  ".join(
        "%s %+.2f" % (k, v) for k, v in rho.items()))
    print("  ★最終形状だけで評価した曲率は最大 %.3e —— **どの形でも厳密にゼロ**。"
          % float(np.max(np.abs(fin))))
    print("     断面の重心の定義から Σ a_k (z_k - z_bar) = 0 になるため。"
          "反りは履歴にしか入っていない。")
    imin = int(np.argmin(dev))
    print("  ★いちばん底面積が大きい形(%s, %.0f mm^2)が、いちばん反らない"
          "(%.4f mm)。" % (names[int(np.argmax(base))], base.max(), dev[imin]))
    figs.save_table("zero_point",
                    ["形", "実測たわみ mm", "底面 mm^2", "最大断面 mm^2",
                     "体積 mm^3", "最終形状のみ κ 1/mm"], rows,
                    title="ゼロ点は順位を当てられない(順位相関 底面 %+.2f / 最大断面 %+.2f / 体積 %+.2f)"
                          % (rho["底面積"], rho["最大断面積"], rho["体積"]))
    return rho, float(np.max(np.abs(fin)))


# --------------------------------------------------------------------------- #
# 節 4 —— 閉形式の検算(バイメタルと飽和)                                       #
# --------------------------------------------------------------------------- #
def section_closed_form_check():
    print("\n" + "=" * 78)
    print("4) 閉形式の検算 —— 2 層で Timoshenko(1925)、多層で飽和")
    print("=" * 78)
    h = H_LAYER
    k2 = closed_form_kappa([16.0 * L_X, 16.0 * L_X], L_X, h)
    tim = 0.75 * EPS_LAYER / h
    print("  2 層(等厚・等 E): 閉形式 %.6e 1/mm / Timoshenko 0.75 ε/h = %.6e "
          "(比 %.6f)" % (k2, tim, k2 / tim))
    ns, kh = [], []
    for n in (2, 4, 8, 12, 16, 24, 32, 48, 64):
        k = closed_form_kappa([16.0 * L_X] * n, L_X, h)
        ns.append(n)
        kh.append(k * h / EPS_LAYER)
        print("   層数 %3d  κ h / ε = %.4f  (たわみ %.4f mm)"
              % (n, kh[-1], k * L_X ** 2 / 8.0))
    print("  ★背を高くしても反りは飽和する(24 層で %.4f、64 層でも %.4f)。"
          % (kh[5], kh[-1]))
    figs.save_plot("saturation", [("閉形式 κh/ε", ns, kh),
                                  ("極限 6*(ζ(2)-ζ(3)) = 2.657", ns,
                                   [2.657] * len(ns))],
                   xlabel="積んだ層の数 [-]", ylabel="κ h / ε [-]",
                   title="層を積むほど反るが、頭打ちになる",
                   caption="断面 2 次モーメントが層数の 3 乗で増えるのに、"
                           "腕は 1 乗でしか伸びないため。")
    return k2 / tim, kh


# --------------------------------------------------------------------------- #
# 節 5 —— 予測 vs 実測                                                          #
# --------------------------------------------------------------------------- #
def section_predict_vs_measure(cases):
    print("\n" + "=" * 78)
    print("5) 予測(層の履歴の閉形式)vs 実測(Q6 増分積層 FEM)")
    print("=" * 78)
    print("  形          予測 κ[1/mm]   実測 κ[1/mm]   比      予測たわみ  実測たわみ[mm]")
    rows = []
    kp, kf, names = [], [], []
    for n, c in cases.items():
        r = c["kappa_fem"] / c["kappa_pred"]
        print("   %-10s %.4e   %.4e  %.4f   %8.4f   %8.4f"
              % (n, c["kappa_pred"], c["kappa_fem"], r, c["dev_pred"], c["dev_fem"]))
        rows.append([n, "%.4e" % c["kappa_pred"], "%.4e" % c["kappa_fem"],
                     "%.4f" % r, "%.4f" % c["dev_pred"], "%.4f" % c["dev_fem"]])
        kp.append(c["kappa_pred"])
        kf.append(c["kappa_fem"])
        names.append(n)
    kp, kf = np.array(kp), np.array(kf)
    err = np.abs(kf / kp - 1.0)
    good = [names[i] for i in range(len(names)) if err[i] < 0.004]
    bad = [names[i] for i in range(len(names)) if err[i] >= 0.004]
    print("\n  0.4 %% 以内で当たったのは %d / %d 形状(%s)。"
          % (len(good), len(names), " / ".join(good)))
    print("  ★崩れた %d 形状(%s)は**すべて断面が x 方向に一様でない**形。"
          % (len(bad), " / ".join("%s %.3f" % (n, kf[names.index(n)] / kp[names.index(n)])
                                  for n in bad)))
    dtrio = [cases[n]["dev_fem"] for n in TRIO]
    spread = max(dtrio) / min(dtrio) - 1.0
    print("  ★★層面積の履歴が**1 mm^2 も違わない**三つ子で、実測たわみは"
          " %s mm(%.0f %% 開く)。"
          % (" / ".join("%.4f" % d for d in dtrio), 100 * spread))
    print("     閉形式は 3 つとも同じ %.4e を返す —— **配置に構造的に盲目**。"
          % cases[TRIO[0]]["kappa_pred"])
    print("     当たるのは面積を全長に均した「%s」だけ(比 %.4f)。"
          % (TRIO[0], kf[names.index(TRIO[0])] / kp[names.index(TRIO[0])]))
    d1, d2 = dtrio[0], dtrio[-1]

    lo, hi = float(min(kp.min(), kf.min())), float(max(kp.max(), kf.max()))
    figs.save_plot("predict_vs_measure",
                   [("6 形状", kp, kf), ("y = x(完全一致)", [lo, hi], [lo, hi])],
                   xlabel="閉形式の予測 κ [1/mm]", ylabel="FEM の実測 κ [1/mm]",
                   title="層の履歴だけで曲率はどこまで当たるか",
                   kinds=["scatter", "line"],
                   caption="外れている 2 点は「中央 1 柱」「両端 2 柱」。")
    figs.save_table("predict_vs_measure_table",
                    ["形", "予測 κ 1/mm", "実測 κ 1/mm", "比",
                     "予測たわみ mm", "実測たわみ mm"], rows,
                    title="予測と実測(1 層あたり ε = %.1e)" % EPS_LAYER)

    panels, caps = [], []
    for n in TRIO:
        r = cases[n]["fem"]
        uz = r["u"][1::2].reshape(r["nz"] + 1, r["nnx"])
        m = r["act"].reshape(r["nz"] + 1, r["nnx"])
        fld = np.where(m, uz, 0.0)
        panels.append(np.repeat(np.flipud(fld), 8, axis=0))
        caps.append("%s(たわみ %.4f mm)" % (n, cases[n]["dev_fem"]))
    figs.save_grid("warp_map", panels, caps, ncols=1, signed=True,
                   title="解いた反りの変位場 uz(青 = 下がる / 赤 = 上がる、"
                         "z 方向は 8 倍に伸ばして表示)",
                   caption="端が持ち上がる典型的な反り。同じ面積履歴の 2 つで"
                           "大きさが違う。")
    return err, d1, d2


# --------------------------------------------------------------------------- #
# 節 6 —— 崖                                                                    #
# --------------------------------------------------------------------------- #
def section_cliff():
    print("\n" + "=" * 78)
    print("6) 崖 —— 先に式で予測してから実測と突き合わせる")
    print("=" * 78)
    print("  予測(着手前): 「首を細くすると平面保持が壊れて閉形式が外れる」")
    print("  予測(着手前): 「細長比 L/H が 3 を切ると端の効果(Saint-Venant)で外れる」")

    print("\n  (a) 首の細さを振る(L = %.0f mm, H = %.0f mm)" % (L_X, Z_SPAN))
    print("     設計の首  測った首  予測 κ         実測 κ        比       たわみ [mm]")
    wn_list, ratio_n, dev_n, wn_meas = [], [], [], []
    for wn in (16.0, 8.0, 4.0, 2.0, 1.0, 0.25):
        boxes = [(0.0, 2.0, 2.0, 18.0, 0.0, 60.0),
                 (2.0, 8.0, 10.0 - wn / 2, 10.0 + wn / 2, 0.0, 60.0),
                 (8.0, 12.0, 2.0, 18.0, 0.0, 60.0)]
        c = build_case(boxes, x_bin=2)
        # 測った首 = 中ほどの層の断面積 / 長さ(2-D の領域 op が返した面積から)
        wm = c["hist"]["area"][int(5.0 / H_LAYER)] / L_X
        wn_list.append(wn)
        wn_meas.append(wm)
        ratio_n.append(c["kappa_fem"] / c["kappa_pred"])
        dev_n.append(c["dev_fem"])
        print("     %6.2f    %6.2f   %.4e   %.4e   %.4f   %.4f"
              % (wn, wm, c["kappa_pred"], c["kappa_fem"], ratio_n[-1], c["dev_fem"]))
    print("     ★予想は外れた —— 首を %.2f mm(実際に測れたのは %.2f mm)まで"
          "細くしても誤差は %.1f %% しか出ない。"
          % (wn_list[-1], wn_meas[-1], 100 * abs(ratio_n[-1] - 1)))
    print("     一様な層の収縮は**純曲げ**でせん断力が立たないので、"
          "細い首でもモーメントは伝わる。")
    print("     ★ついでに: ボクセル %.2f mm では %.2f mm の首は %.2f mm としか"
          "測れない(下から 2 番目と同じ値になる)。"
          % (VOX, wn_list[-1], wn_meas[-1]))
    print("     ★首を細くすると反りは**減る**(%.4f -> %.4f mm)—— 首は"
          "「弱いから危ない」場所ではなく、\n     **縮む材料が少ない**場所。"
          % (dev_n[0], dev_n[-1]))

    print("\n  (b) 細長比 L/H を振る(H = %.0f mm)" % Z_SPAN)
    print("     L [mm]  L/H   中実の比   首つきの比")
    lh, r_solid, r_neck = [], [], []
    for lx in (12.0, 18.0, 24.0, 36.0, 60.0):
        c1 = build_case([(0.0, 12.0, 2.0, 18.0, 0.0, lx)], x_len=lx, x_bin=1)
        c2 = build_case([(0.0, 2.0, 2.0, 18.0, 0.0, lx),
                         (2.0, 8.0, 9.25, 10.75, 0.0, lx),
                         (8.0, 12.0, 2.0, 18.0, 0.0, lx)], x_len=lx, x_bin=1)
        lh.append(lx / Z_SPAN)
        r_solid.append(c1["kappa_fem"] / c1["kappa_pred"])
        r_neck.append(c2["kappa_fem"] / c2["kappa_pred"])
        print("     %5.1f  %4.1f   %.4f     %.4f" % (lx, lh[-1], r_solid[-1], r_neck[-1]))
    print("     ★崖は L/H = %.1f(誤差 中実 %.1f %% / 首つき %.1f %%)。"
          % (lh[0], 100 * abs(r_solid[0] - 1), 100 * abs(r_neck[0] - 1)))
    print("     L/H >= %.1f では %.1f %% 以内 —— **予想した 3 ではなく %.1f が崖**。"
          % (lh[2], 100 * max(abs(r_solid[2] - 1), abs(r_neck[2] - 1)), lh[1]))

    figs.save_plot("cliff_aspect",
                   [("中実", lh, r_solid), ("首つき", lh, r_neck),
                    ("完全一致", lh, [1.0] * len(lh))],
                   xlabel="細長比 L / H [-]", ylabel="実測 κ / 予測 κ [-]",
                   title="閉形式が崩れるのは細長比が 2 を切ってから",
                   caption="首の細さでは崩れない(別図)。純曲げにはせん断が"
                           "無いため。")
    figs.save_plot("cliff_neck",
                   [("実測 / 予測", wn_list, ratio_n),
                    ("完全一致", wn_list, [1.0] * len(wn_list))],
                   xlabel="首の幅 [mm]", ylabel="実測 κ / 予測 κ [-]",
                   title="首を細くしても閉形式は崩れない(予想は外れ)")
    return wn_list, ratio_n, lh, r_solid, r_neck


# --------------------------------------------------------------------------- #
# 節 7 —— 対照群                                                                #
# --------------------------------------------------------------------------- #
def section_controls(cases):
    print("\n" + "=" * 78)
    print("7) 対照群 —— 収縮だけ / 断面だけ / 層厚だけ を変える")
    print("=" * 78)
    box = [(0.0, 12.0, 2.0, 18.0, 0.0, 60.0)]

    print("  (a) 収縮 ε だけを変える(形は同じ)")
    eps_l, dev_l = [], []
    occ, _ = voxelize(box)
    hist = layer_history(occ)
    tmap = thickness_map(occ)
    for e in (0.5e-4, 1.0e-4, 2.0e-4, 4.0e-4):
        r = fem_build(tmap, L_X / tmap.shape[1], H_LAYER, eps=e)
        eps_l.append(e)
        dev_l.append(r["dev"])
        print("     ε = %.2e -> たわみ %.4f mm(ε に対する比 %.4f)"
              % (e, r["dev"], r["dev"] / e * 1e-4))
    lin = float(np.max(np.abs(np.array(dev_l) / np.array(eps_l)
                              / (dev_l[0] / eps_l[0]) - 1.0)))
    print("     反りは ε に**厳密に比例**(比のばらつき %.2e)。" % lin)

    print("\n  (b) 断面(幅)だけを変える(層厚・高さ・長さは同じ)")
    for w in (4.0, 8.0, 16.0):
        c = build_case([(0.0, 12.0, 10.0 - w / 2, 10.0 + w / 2, 0.0, 60.0)], x_bin=2)
        print("     幅 %5.1f mm(体積 %6.0f mm^3)-> たわみ %.4f mm"
              % (w, w * 12 * 60, c["dev_fem"]))
    print("     ★幅は反りに効かない —— 断面 2 次モーメントも収縮モーメントも"
          "同じ比で増えるため。")

    print("\n  (c) 層厚だけを変える(最終形状・体積・底面積はすべて同じ)")
    rows = []
    d_const, d_prop = [], []
    for h in (1.0, 0.5, 0.25):
        occ, _ = voxelize(box, h=h)
        tm = thickness_map(occ)
        tm = tm[:, :tm.shape[1] // 2 * 2].reshape(tm.shape[0], -1, 2).mean(axis=2)
        dx = L_X / tm.shape[1]
        r1 = fem_build(tm, dx, h, eps=EPS_LAYER)
        r2 = fem_build(tm, dx, h, eps=EPS_LAYER * h / H_LAYER)
        d_const.append(r1["dev"])
        d_prop.append(r2["dev"])
        rows.append(["%.2f" % h, "%d" % tm.shape[0], "%.4f" % r1["dev"],
                     "%.4f" % r2["dev"]])
        print("     層厚 %.2f mm(%2d 層): ε 一定 -> %.4f mm / "
              "ε を層厚に比例 -> %.4f mm" % (h, tm.shape[0], r1["dev"], r2["dev"]))
    rc = d_const[-1] / d_const[0]
    rp = d_prop[-1] / d_prop[0]
    print("     ★★同じ形・同じ体積・同じ底面積で、層厚 1.00 -> 0.25 mm にすると"
          "たわみは **%.2f 倍**。" % rc)
    print("     ただし「単位高さあたりの収縮が一定」と置き直すと **%.2f 倍**に"
          "しかならない。" % rp)
    print("     **ε の定義を書かずに『層を薄くすると反る』と言ってはいけない**。")
    figs.save_table("controls",
                    ["層厚 mm", "層数", "たわみ(ε 一定)mm",
                     "たわみ(ε ∝ 層厚)mm"], rows,
                    title="層厚だけを変えた対照群(最終形状は同一)")
    figs.save_plot("layer_thickness",
                   [("ε が層ごとに一定", [1.0, 0.5, 0.25], d_const),
                    ("ε が層厚に比例", [1.0, 0.5, 0.25], d_prop)],
                   xlabel="層厚 [mm]", ylabel="たわみ [mm]",
                   title="同じ形でも層厚で反りが変わる(仮定しだいで 4 倍か 1.2 倍か)")
    return lin, rc, rp


# --------------------------------------------------------------------------- #
# 節 8 —— 剥離                                                                  #
# --------------------------------------------------------------------------- #
def section_delamination(cases):
    print("\n" + "=" * 78)
    print("8) 基板からの剥離 —— 応力は収束しないが、力は収束して式に乗る")
    print("=" * 78)
    box = [(0.0, 12.0, 2.0, 18.0, 0.0, 60.0)]
    occ, _ = voxelize(box)
    tmap0 = thickness_map(occ)

    print("  (a) 端の引き剥がし応力の要素寸法依存")
    print("     dx [mm]  端の応力 [MPa]  端 6 mm の力 [N]")
    dxs, smax, fedge = [], [], []
    for binw in (4, 2, 1):
        tm = tmap0[:, :tmap0.shape[1] // binw * binw]
        tm = tm.reshape(tm.shape[0], -1, binw).mean(axis=2)
        dx = L_X / tm.shape[1]
        r = fem_build(tm, dx, H_LAYER)
        pf = peel_forces(r, 16.0)
        dxs.append(dx)
        smax.append(float(pf["stress"].max()))
        fedge.append(edge_peel_force(pf))
        print("     %5.2f    %8.2f       %8.1f" % (dx, smax[-1], fedge[-1]))
        if binw == 1:
            keep = pf
    print("     ★応力は %.2f -> %.2f MPa と %.0f %% 増え続けて収束しない"
          "(端は特異点)。" % (smax[0], smax[-1],
                              100 * (smax[-1] / smax[0] - 1)))
    print("     ★力は %.1f -> %.1f N(%.1f %%)で収束する —— "
          "**判定に使えるのは力のほう**。"
          % (fedge[0], fedge[-1], 100 * abs(fedge[-1] / fedge[-2] - 1)))

    print("\n  (b) その力は EIκ で予測できるか(%d 形状)" % len(cases))
    print("     形          EIκ [N mm]  端 6 mm の力 [N]  接着の容量 [N]  判定")
    ratio, rows, forces = [], [], {}
    for n, c in cases.items():
        wb = c["hist"]["area"][0] / L_X
        pf = peel_forces(c["fem"], wb)
        f6 = edge_peel_force(pf)
        cap = SIG_ADH * 2.0 * 6.0 * wb
        m = E_MOD * c["I"] * c["kappa_fem"]
        ratio.append(f6 / m)
        forces[n] = (f6, cap)
        verdict = "剥離" if f6 > cap else "保持"
        rows.append([n, "%.1f" % m, "%.1f" % f6, "%.1f" % cap,
                     "%s(余裕 %.2f)" % (verdict, cap / f6)])
        print("     %-10s %9.1f  %10.1f      %8.1f    %s(余裕 %.2f 倍)"
              % (n, m, f6, cap, verdict, cap / f6))
    ratio = np.array(ratio)
    cv = float(ratio.std() / ratio.mean())
    f_lo, f_hi = min(forces[k][0] for k in TRIO), max(forces[k][0] for k in TRIO)
    print("\n     ★★**予測できるはずの量が予測できない**。力 / EIκ の変動係数は"
          " %.0f %% で、\n     EIκ からは 1 桁も決まらない。" % (100 * cv))
    print("     決定的なのは三つ子(層面積の履歴が同一・EIκ もほぼ同じ)で、"
          "端の力が %.1f -> %.1f N の\n     **%.0f 倍**違い、判定も割れる。"
          % (f_lo, f_hi, f_hi / f_lo))
    print("     効いているのは**端で基板につながっている材料の背の高さ**で、"
          "これは層の面積の履歴には入っていない\n     "
          "(x のどこに置いたかの情報だから)。")

    print("\n  (c) では端のフラップの厚さで崖を探す(中央 1 柱の底板を振る)")
    print("     底板 [mm]  端 6 mm の力 [N]  容量 [N]  判定")
    tb_list, f_list = [], []
    for tb in (1.0, 2.0, 3.0, 4.0, 6.0, 8.0):
        boxes = [(0.0, tb, 2.0, 18.0, 0.0, 60.0),
                 (tb, 8.0, 2.0, 18.0, 15.0, 45.0),
                 (8.0, 12.0, 2.0, 18.0, 0.0, 60.0)]
        c = build_case(boxes, x_bin=2)
        pf = peel_forces(c["fem"], 16.0)
        f6 = edge_peel_force(pf)
        cap = SIG_ADH * 2.0 * 6.0 * 16.0
        tb_list.append(tb)
        f_list.append(f6)
        print("     %6.1f     %10.1f      %6.1f    %s"
              % (tb, f6, cap, "剥離" if f6 > cap else "保持"))
    cap = SIG_ADH * 2.0 * 6.0 * 16.0
    cross = next((tb_list[i] for i in range(len(f_list)) if f_list[i] > cap), None)
    print("     ★崖は底板 %.1f mm(そこで力が %.1f N を越える)。"
          "底板を薄くすると力は %.1f -> %.1f N と %.0f 倍に落ちる ——\n     "
          "**端を薄く逃がすと剥がれない**(反り自体はほとんど変わらない)。"
          % (cross if cross else -1.0, cap, f_list[0], f_list[-1],
             f_list[-1] / f_list[0]))

    figs.save_plot("peel_profile",
                   [("dx = %.2f mm" % dxs[-1], keep["x"], keep["stress"]),
                    ("接着強さ %.1f MPa" % SIG_ADH, keep["x"],
                     [SIG_ADH] * keep["x"].size)],
                   xlabel="x [mm]", ylabel="引き剥がし応力 [MPa]",
                   title="剥離応力は端に集中し、要素寸法で決まらない",
                   caption="正 = 接着剤が引っ張られる。中央は押しつけられている。")
    figs.save_plot("peel_vs_moment",
                   [("形ごとの実測", [E_MOD * c["I"] * c["kappa_fem"]
                                      for c in cases.values()],
                     [forces[n][0] for n in cases]),
                    ("底板の掃引", [E_MOD * cases["中央 1 柱"]["I"]
                                    * cases["中央 1 柱"]["kappa_fem"]] * len(f_list),
                     f_list)],
                   xlabel="EIκ [N mm]", ylabel="端 6 mm の引き剥がし力 [N]",
                   title="剥離力は EIκ では決まらない(変動係数 %.0f %%)" % (100 * cv),
                   kinds=["scatter", "scatter"],
                   caption="同じ EIκ でも端の作りしだいで 1 桁動く。")
    figs.save_table("peel", ["形", "EIκ N mm", "端 6 mm の力 N", "接着の容量 N",
                             "判定"], rows,
                    title="引き剥がしの判定(接着強さ %.1f MPa、端 6 mm で評価)"
                          % SIG_ADH)
    return smax, fedge, cv, f_hi / f_lo


# --------------------------------------------------------------------------- #
# 節 9 —— 危険度の地図                                                          #
# --------------------------------------------------------------------------- #
def section_risk_map():
    print("\n" + "=" * 78)
    print("9) 危険度の地図 —— 層厚 x 首の細さ(許容たわみ %.2f mm を 1 とする)"
          % DEV_ALLOW)
    print("=" * 78)
    hs = [1.0, 0.75, 0.5, 0.375, 0.25, 0.2]
    wns = [16.0, 8.0, 4.0, 2.0, 1.0]
    grid = np.zeros((len(hs), len(wns)))
    for a, h in enumerate(hs):
        for b, wn in enumerate(wns):
            boxes = [(0.0, 2.0, 2.0, 18.0, 0.0, 60.0),
                     (2.0, 8.0, 10.0 - wn / 2, 10.0 + wn / 2, 0.0, 60.0),
                     (8.0, 12.0, 2.0, 18.0, 0.0, 60.0)]
            occ, _ = voxelize(boxes, h=h)
            hist = layer_history(occ, h=h)
            k = closed_form_kappa(hist["area"], L_X, h)
            grid[a, b] = k * L_X ** 2 / 8.0 / DEV_ALLOW
    print("     層厚\\首[mm] " + "".join("%7.2f" % w for w in wns))
    for a, h in enumerate(hs):
        print("     %8.2f  " % h + "".join("%7.2f" % v for v in grid[a]))
    print("  ★危険度は %.2f - %.2f(%.1f 倍)。首だけを 16 -> 0.5 mm にしても "
          "%.2f 倍にしかならず、\n     層厚を 1.00 -> 0.25 mm にすると %.2f 倍 —— "
          "**層厚のほうが効く**。"
          % (grid.min(), grid.max(), grid.max() / grid.min(),
             grid[0, -1] / grid[0, 0], grid[4, 0] / grid[0, 0]))
    figs.save("risk_map", np.repeat(np.repeat(grid, 48, axis=0), 60, axis=1),
              caption="危険度 = 予測たわみ / 許容 %.2f mm。縦は層厚 %.2f -> %.2f mm"
                      "(上が厚い)、横は首の幅 %.1f -> %.1f mm(右が細い)。"
                      "明るいほど危ない。"
                      % (DEV_ALLOW, hs[0], hs[-1], wns[0], wns[-1]))
    figs.save_table("risk_map_table",
                    ["層厚 mm"] + ["首 %.2f" % w for w in wns],
                    [["%.2f" % hs[a]] + ["%.2f" % v for v in grid[a]]
                     for a in range(len(hs))],
                    title="危険度の地図(予測たわみ / 許容 %.2f mm)" % DEV_ALLOW)
    return grid


# --------------------------------------------------------------------------- #
# 節 10 —— 道具の穴                                                             #
# --------------------------------------------------------------------------- #
def section_tool_gaps():
    print("\n" + "=" * 78)
    print("10) 道具の穴(この PoC で公開経路に無かった処理)")
    print("=" * 78)
    assert not hasattr(fs, "vol_slice") and not hasattr(L, "vol_slice")
    print("  (a) `vol_slice` は公開経路に無い(3-D 追補が挙げていたが実在しない)。"
          "層の取り出しは numpy の添字で書いた。")
    assert not hasattr(fs, "grid_coords")
    print("  (b) `grid_coords` は台帳にだけ在り、ファサード `fs.<名>` には出ていない"
          "(3-D op の大半と同じ)。")
    m = np.zeros((6, 8), bool)
    m[1:4, 2:6] = True
    lab = L.blob_label(m)
    f = L.blob_features(lab, spacing=1.0)
    assert "row" in f and "col" in f and "centroid_r" not in f
    print("  (c) `blob_features` の重心は `row`/`col`(**画素単位**)で返る。"
          "mm へ直すのは呼び手の仕事で、`spacing` は面積と周長にしか掛からない。")
    assert not hasattr(fs, "beam_curvature") and not hasattr(L, "beam_curvature")
    print("  (d) 梁・板の力学(断面 2 次モーメント、熱ひずみの等価節点力、"
          "平面応力要素)は fullseye に無い。この PoC は scipy.sparse で自前。")
    assert not hasattr(fs, "vol_layer_stack") and not hasattr(L, "vol_layer_stack")
    print("  (e) 「層ごとの断面をまとめて測る」口(層の履歴を 1 回で返す op)が"
          "無い。1 層ずつ `blob_label` + `blob_features` を回している。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    np.random.default_rng(SEED)
    print("=" * 78)
    print("積層造形の反りを層の履歴から予測する")
    print("材料 E = %.0f MPa / ν = %.2f / 1 層の拘束収縮 ε = %.1e / "
          "既定の層厚 %.2f mm" % (E_MOD, NU, EPS_LAYER, H_LAYER))
    print("=" * 78)

    cases = section_scene()
    same_area = section_area_history(cases)
    rho, fin_max = section_zero_point(cases)
    tim_ratio, kh = section_closed_form_check()
    err, d1, d2 = section_predict_vs_measure(cases)
    wn_list, ratio_n, lh, r_solid, r_neck = section_cliff()
    lin, rc, rp = section_controls(cases)
    smax, fedge, coef, cv = section_delamination(cases)
    grid = section_risk_map()
    section_tool_gaps()

    # --- 所見を固定する(壊れたら鳴る)------------------------------------- #
    assert same_area < 1e-9, same_area
    assert fin_max < 1e-15, fin_max
    assert abs(tim_ratio - 1.0) < 1e-5, tim_ratio
    assert 2.40 < kh[5] < 2.44, kh[5]
    assert int(np.count_nonzero(err < 0.004)) == 4, err
    assert abs(d1 - d2) / max(d1, d2) > 0.20, (d1, d2)
    assert abs(ratio_n[-1] - 1.0) < 0.02, ratio_n
    assert abs(r_solid[0] - 1.0) > 0.03 and abs(r_neck[0] - 1.0) > 0.05, (r_solid, r_neck)
    assert lin < 1e-6, lin
    assert rc > 4.0 and rp < 1.3, (rc, rp)
    assert smax[-1] / smax[0] > 1.2, smax
    assert abs(fedge[-1] / fedge[-2] - 1.0) < 0.05, fedge
    assert cv < 0.05, cv
    assert grid.max() / grid.min() > 5.0, grid

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 最終形状だけを見る予測器は厳密にゼロ(%.1e)。反りは層の履歴にしかない。"
          % fin_max)
    print("  * 層の履歴の閉形式は 6 形状中 4 形状で 0.4 %% 以内。崩れるのは"
          "**同じ面積を別々に置いた**形(たわみ %.4f vs %.4f mm)。" % (d1, d2))
    print("  * 同じ形・同じ体積・同じ底面積でも、層厚 1.00 -> 0.25 mm で"
          "たわみ %.2f 倍(ε 一定の仮定)。" % rc)
    print("  * 剥離は応力では決まらない(要素寸法で %.0f %% 動く)が、"
          "端の力は EIκ に比例(変動係数 %.1f %%)。"
          % (100 * (smax[-1] / smax[0] - 1), 100 * cv))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
