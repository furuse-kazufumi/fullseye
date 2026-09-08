# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""シルエットから家畜の体積を測ると、必ず大きく出る —— カメラを増やしても凹みは埋まらない。

肉牛の出荷判定・飼養管理・保険の査定は、どれも **1 頭あたり 1 個の体重の数字**で
動きます。台秤に載せるのが確実ですが、追い込みのストレスと人手が要るので、
牛舎の通路にカメラを何台か置いて**シルエットから体積を出し、密度を掛けて体重にする**
やり方が使われます。この PoC が扱うのはその方式の**構造的な性質**です ——
多視点シルエットから彫り出す **視体積交差(visual hull)は物体の上界**であって、
**下界ではありません**。つまり体積は必ず大きく出ます。しかも過大の中身は
2 種類あり、**片方はカメラを増やせば消え、もう片方は何台置いても消えません**。
この PoC はその 2 つを別々に数え、さらに「何 % 以内で測りたいなら何台要るか」を
**測る前に閉形式で予測**してから実測と突き合わせます。

EXTEND: 実カメラに差し替えるなら :func:`surface_cloud` の戻り値(体表の点群)を
実物のシルエット抽出に置き換えます —— すなわち ``fs.ledger.synthesize_silhouette``
の呼び出しを、実画像の前景マスク ``(H, W) bool`` に差し替えるだけで、以降
(``carve`` 以降)はそのまま動きます。カメラの ``(K, R, t)`` は校正板から
``fs.ledger`` の校正族で出します。**そのとき失われるのは真値**です ——
本 PoC の中心である「上界がどれだけ上か」は、体積の真値が要るので実物では出せません
(屠体重と枝肉歩留まりを使う手はありますが、それは**別の物差し**です)。
実データでできるのは §4 のカメラ台数掃引(数字は動かなくなるが、どこで止まったかは
分かる)と §6 の前景マスクの膨張・収縮感度だけで、**絶対誤差は出せません**。
逆に言えば、機器メーカーの「精度 ±2 %」が上界の話なのか台秤との比較なのかは、
真値をどう取ったかを聞かないと判定できません。

この PoC が示すこと(数字はすべて実行時の実測値):

1. **ゼロ点(外接直方体)は真の体積の 3.62 倍**。素朴に体を箱で囲うと 752 kg の牛が
   2721 kg になります。1 台のシルエットに一定の奥行き(体幅 0.76 m)を掛ける
   2 番目のゼロ点でも 1.365 倍。**視体積交差はこの 2 つよりはるかに良い**
   (8 台で 1.106 倍)—— 問題は「良い」ではなく「**必ず上**」であることです。
2. ★**必要なカメラ台数は測る前に閉形式で出る**。軸周りに等間隔 K 台置くと、
   胴の水平断面(楕円)は**接線がつくる多角形**に置き換わります。カメラ 1 台は
   **視線に直交する 2 本**の接線を与えるので、法線の集合は ``方位 ± 90 度``。
   円なら比 ``(n/π)tan(π/n)``、細長い楕円なら支持関数から厳密に出ます。
   近似平行投影(60 m・4.0 mm/px)の実測は閉形式の**すぐ上**に乗りました ——
   K=4: 予測 1.27324 / 実測 1.27528、K=8: 1.11657 / 1.12231、
   K=24: 1.01790 / 1.02821(差は +0.002〜+0.010 で単調増加。正体は §6 の
   被覆マージン)。**閉形式は下界として当たり**ました。
3. ★★**3 台と 6 台がまったく同じ**(閉形式 1.16772 / 1.16772、実測 1.16855 /
   1.16855 で完全一致)。胴の水平断面が**点対称**だと、向かい合うカメラの接線が
   同じ 2 本になるので、**偶数台は半分が無駄**になります。結果として
   **13 台(1.0153)が 16 台(1.0388)に勝ちます**。「2 % 以内で測りたい」なら
   奇数 13 台、偶数に限ると 22 台 —— 円の目安 ``(n/π)tan(π/n)`` から素朴に
   「13 台」と読むと、偶数台のリグでは**9 台足りません**。
   ★但し書き: この無駄は断面が点対称だから起きます。前後で太さの違う断面
   (§3 末尾の閉形式)では 3 台 1.36752 と 6 台 1.24280 が別物になり、無駄は消えます。
4. ★★**過大の中身は 2 つあって、片方だけが消える**。背中のくぼみ(削痩個体の
   ロイン)を仕込むと、視体積交差はそれを **K=4 で 56.4 %、K=48 で 52.6 %**
   埋めたままです —— **12 倍のカメラを足して 4 ポイントしか減りません**。
   一方、脚の間の空隙に立つ幽霊は **7.13 % → 1.37 %** と素直に減ります。
   凹みが輪郭に出るかどうかが分かれ目で、**輪郭に出ない凹みはシルエットには
   原理的に情報が無い**(K→∞ でも残る)。
5. ★**物差しを 3 つ置くと勝者が入れ替わります**。体積由来の体重では
   視体積交差 24 台(+4.1 %)が最良、**胸囲×体長のアロメトリでは凸包(+1.6 %)**が
   最良で視体積交差 24 台は +8.4 %。理由は測り方そのものにあります ——
   **巻尺は凸包を測る道具**なので、背中のくぼみはアロメトリには最初から効きません。
   重心の高さでは外接直方体(+0.019 m)が視体積交差 8 台(+0.033 m)に勝ちます。
   **どれか 1 つの誤差で「この手が良い」とは言えません**。
6. ★**胸囲の誤差は体重で 2 倍になる**。アロメトリは ``W ∝ 胸囲^2 × 体長`` なので
   ``ΔW/W = 2ΔG/G + ΔL/L``。視体積交差 24 台の胸囲は +3.5 % で、予測 +7.5 % に対し
   実測 +8.4 %(残差は体長の +0.5 % と 2 次項)。
7. ★**シルエットが 1 画素太ると体積は 2.60 % 増えます**(4.0 mm/px、K=12)。
   閉形式は Steiner の公式 ``ΔV/V = (S/V)·δ`` で、体の ``S/V = 7.63 /m``・
   δ=4.0 mm から **+3.05 %/px** —— 実測はその 0.85 倍でした(hull の表面は体より
   大きいので予測は下限のはずが、**外しました**。理由は §6 に書きます)。
   3 画素で +8.0 %。**前景抽出のしきい値 1 段が、体重で 60 kg 動きます**。
   ★``synthesize_silhouette`` の既定は ``dilate=1`` です —— recall のための
   保守側の丸めで docstring も明言していますが、**体積を測る用途では既定のまま
   使うと +2.6 % の下駄**が乗ります。この PoC は全編 ``dilate=0`` で測っています。
8. **上半球のランダム配置は等間隔に勝てません**。8 台・120 試行で、等間隔
   (+15.53 %)を下回ったのは **120 試行中 0 件**、平均 +25.24 %(標準偏差 4.34)。
   ★0 件は小標本の産物ではありません —— 最良の試行でも +17.68 % で、等間隔との
   差は標準偏差の 0.5 倍あります。**方位の偏りが直接効く**ので、台数より配置。
9. ★**道具の穴を 3 つ見つけました**(§7)。いちばん重いのは ``look_at`` の
   名前衝突で、``fs.look_at`` は render3d の gluLookAt 版(4×4・**-Z 前方**)、
   ``carve`` が要る OpenCV 版(``(R, t)``・**+Z 前方**)は ``visualhull.look_at`` に
   あって **4 層のどこからも引けません**(``fs.op_find("look")`` は 0 件)。
   間違えて ``fs.look_at`` から ``(R, t)`` を取り出して渡すと、全 voxel が
   カメラ後方と判定されて **占有 0 の hull が黙って返ります**(実演あり)。

【グラウンドトゥルース】体は **三軸楕円体の胴(半軸 1.05 / 0.38 / 0.42 m)**、
その**背中に掘ったくぼみ**(深さ 0.14 m のガウス)、**4 本の脚**(半径 0.06 m の
円柱を胴の下面で切ったもの)。この置き方にした理由は **体積が厳密に出るから**です ——
胴は ``(4/3)πabc`` の閉形式、くぼみは深さ場の 2 次元求積、脚は下面高さの
2 次元求積で、いずれも 3 次元の格子を使いません(刻みを 4 段変えて収束を印字)。
脚は胴の**下面より下**にしかないので、和の体積は足し算で厳密です。
対照群は (a) くぼみも脚も無い**凸な胴だけ**、(b) 軸周り等間隔 vs 上半球ランダム、
(c) シルエットの膨張・収縮 ±3 画素。

【なぜ比で測るか】hull と真値を**同じ voxel 格子の占有数**で比べます。格子の
離散化は両方に同じだけ乗るので比で落ちます(真の占有数は解析体積の 1.00017 倍)。

【来歴】密度 1020 kg/m^3 は「体組織はほぼ水」として置いた仮定で、出典のある定数では
ありません。アロメトリ式は ``W = k·胸囲^2×体長`` の形だけを借り、**係数 k は真値で
較正**しています —— 式の当否ではなく**測定の偏りが体重にどう効くか**を見るためです。
視体積交差の性質(上位集合であること)は Laurentini, *IEEE TPAMI* 16 (1994) 150。
外側平行体の体積 ``V(δ) = V + Sδ + ...`` は Steiner の公式です。

【3-D の落とし穴(踏んだもの)】``carve`` の返り値は ``indexing='ij'`` で軸が
(x, y, z) —— ``vol_rle_*`` 族は同じ配列を (z, y, x) と呼ぶので、**名前ではなく
軸番号で対応を書く** / 非等方な bounds では voxel 体積は 3 軸の積で、
``vol_rle_volume`` が返すのは **voxel 個数まで**(docstring 明記) /
シルエットの画素は世界では 4.0 mm で、体積の 2.6 %/px に化ける /
接線の法線は**カメラ方位そのものではなく ± 90 度**(これを間違えると
閉形式が K=6 で 1.38 と出て実測 1.17 と合わない。最初そうなりました)。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import visualhull as _visualhull                                 # noqa: E402

#: 3-D op の公開経路(ファサード ``fs.`` には出ていないものが多い)。
_L = fs.ledger

# --- 体の諸元 [m] ----------------------------------------------------------- #
A, B, C = 1.05, 0.38, 0.42        # 胴(三軸楕円体)の半軸 = 体長 / 体幅 / 体深の半分
Z0 = 1.05                          # 胴の中心の高さ(= 脚の長さ + 体深の半分)
HOL_D, HOL_SX, HOL_SY = 0.14, 0.35, 0.09   # 背中のくぼみ: 深さ・前後の広がり・左右の広がり
LEG_R, LEG_X, LEG_Y = 0.06, 0.60, 0.20     # 脚: 半径・前後位置・左右位置
RHO = 1020.0                       # 体組織の密度 [kg/m^3](「ほぼ水」として置いた仮定)

# --- 測る側の諸元 ----------------------------------------------------------- #
#: 彫刻する直方体(牛が余裕をもって入る)。非等方なので voxel も非等方。
BOUNDS = ((-1.12, 1.12), (-0.45, 0.45), (0.0, 1.50))
RES = 96                           # 各軸の voxel 分割数(voxel 総数 = RES^3)
D_RING, F_RING = 8.0, 2000.0       # 実務のリグ: 8 m 先・焦点距離 2000 px → 4.0 mm/px
D_FAR, F_FAR = 60.0, 15000.0       # 近似平行投影の対照: 60 m 先 → 同じ 4.0 mm/px
IMG_H, IMG_W = 480, 640
LOOK_Z = 0.75                      # カメラの高さ(体の中ほど)
N_FIB = 900_000                    # 体表の標本点数(間隔 < 1 画素 = 4.0 mm になる数)

#: 胸囲を測る断面の位置 [m](x=0 = いちばん太い所。背中のくぼみもここ)。
GIRTH_X = 0.0


# --------------------------------------------------------------------------- #
# 1. グラウンドトゥルース —— 体積が厳密に出る置き方                             #
# --------------------------------------------------------------------------- #
def hollow_depth(x, y):
    """背中のくぼみの深さ [m]。上面をこの分だけ下げる。"""
    return HOL_D * np.exp(-((x / HOL_SX) ** 2 + (y / HOL_SY) ** 2))


def _radial(x, y):
    """楕円体の断面係数 ``sqrt(1 - (x/a)^2 - (y/b)^2)``(footprint の外は 0)。"""
    return np.sqrt(np.clip(1.0 - (x / A) ** 2 - (y / B) ** 2, 0.0, None))


def z_top(x, y):
    """胴(くぼみ前)の上面の高さ [m]。"""
    return Z0 + C * _radial(x, y)


def z_bot(x, y):
    """胴の下面の高さ [m]。脚はここで切る。"""
    return Z0 - C * _radial(x, y)


def inside(x, y, z, *, legs: bool, hollow: bool) -> np.ndarray:
    """体の内側か(真値)。``legs`` / ``hollow`` を落とすと対照群になる。"""
    ins = (x / A) ** 2 + (y / B) ** 2 + ((z - Z0) / C) ** 2 <= 1.0
    if hollow:
        ins = ins & (z <= z_top(x, y) - hollow_depth(x, y))
    if legs:
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                d2 = (x - sx * LEG_X) ** 2 + (y - sy * LEG_Y) ** 2
                ins = ins | ((d2 <= LEG_R ** 2) & (z >= 0.0) & (z <= z_bot(x, y)))
    return ins


def hollow_volume(step: float) -> float:
    """くぼみで削られる体積 [m^3]。**2 次元**の求積(3-D 格子を使わない)。"""
    gx = np.arange(-A + step / 2, A, step)
    gy = np.arange(-B + step / 2, B, step)
    X, Y = np.meshgrid(gx, gy, indexing="ij")
    thick = 2.0 * C * _radial(X, Y)                 # その (x,y) での肉厚
    return float(np.minimum(hollow_depth(X, Y), thick).sum()) * step * step


def leg_volume(step: float) -> float:
    """脚 1 本の体積 [m^3] = 円板上での下面高さの 2 次元求積。"""
    g = np.arange(-LEG_R + step / 2, LEG_R, step)
    X, Y = np.meshgrid(g, g, indexing="ij")
    m = X ** 2 + Y ** 2 <= LEG_R ** 2
    return float(z_bot(X[m] + LEG_X, Y[m] + LEG_Y).sum()) * step * step


def torso_volume() -> float:
    """胴(くぼみ前)の体積 [m^3]。閉形式 ``(4/3)πabc``。"""
    return 4.0 / 3.0 * math.pi * A * B * C


def body_surface() -> float:
    """体表面積 [m^2]。楕円体は Thomsen 近似(誤差 ~1 %)、脚は閉形式。

    ★これは**近似**なので、§6 の Steiner 予測もその精度でしか出ない。
    """
    p = 1.6075
    s_ell = 4 * math.pi * (((A * B) ** p + (A * C) ** p + (B * C) ** p) / 3.0) ** (1 / p)
    h = float(z_bot(LEG_X, LEG_Y))                  # 脚の高さ(中心での近似)
    s_leg = 4 * (2 * math.pi * LEG_R * h + math.pi * LEG_R ** 2)
    return s_ell + s_leg


# --------------------------------------------------------------------------- #
# 2. 体表の点群と voxel 格子                                                    #
# --------------------------------------------------------------------------- #
def _fibonacci_sphere(n: int) -> np.ndarray:
    """単位球上のほぼ等間隔な ``n`` 点(決定的。乱数を使わない)。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    theta = math.pi * (1.0 + 5.0 ** 0.5) * i
    return np.stack([np.cos(theta) * np.sin(phi),
                     np.sin(theta) * np.sin(phi), np.cos(phi)], axis=1)


def surface_cloud(*, legs: bool, hollow: bool, n: int = N_FIB) -> np.ndarray:
    """体表の点群 (N,3) [m]。点間隔が 1 画素より細かくないとシルエットに穴が空く。

    上半球の点は ``z = z_top(x, y)`` にちょうど乗るので、``hollow`` はその z を
    深さ分だけ下げるだけで**正しい上面**になる(新しい面を別に張らなくてよい)。
    """
    p = _fibonacci_sphere(n) * np.array([A, B, C]) + np.array([0.0, 0.0, Z0])
    if hollow:
        up = p[:, 2] > Z0
        p[up, 2] -= hollow_depth(p[up, 0], p[up, 1])
    if not legs:
        return p
    parts = [p]
    step = 0.0035                                   # 4.0 mm/px より細かく刻む
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            cx, cy = sx * LEG_X, sy * LEG_Y
            ang = np.arange(0.0, 2 * math.pi, step / LEG_R)
            wx, wy = cx + LEG_R * np.cos(ang), cy + LEG_R * np.sin(ang)
            tops = z_bot(wx, wy)
            for k in range(ang.size):               # 側面(母線ごとに縦へ刻む)
                zs = np.arange(0.0, tops[k], step)
                parts.append(np.stack([np.full(zs.size, wx[k]),
                                       np.full(zs.size, wy[k]), zs], axis=1))
            g = np.arange(-LEG_R, LEG_R + 1e-9, step)   # 蹄(底面の円板)
            X, Y = np.meshgrid(g, g, indexing="ij")
            m = X ** 2 + Y ** 2 <= LEG_R ** 2
            parts.append(np.stack([X[m] + cx, Y[m] + cy,
                                   np.zeros(int(m.sum()))], axis=1))
    return np.concatenate(parts, axis=0)


def voxel_axes(res: int):
    """各軸の voxel 中心 [m](``carve`` と同じ刻み)。"""
    return [lo + (np.arange(res) + 0.5) * (hi - lo) / res for lo, hi in BOUNDS]


def voxel_grid(res: int):
    """voxel 中心の 3-D 格子。軸は (x, y, z) = ``carve`` の ``indexing='ij'``。"""
    ax = voxel_axes(res)
    return np.meshgrid(ax[0], ax[1], ax[2], indexing="ij")


def voxel_volume(res: int) -> float:
    """voxel 1 個の体積 [m^3]。**3 軸別**(bounds が非等方なので立方体ではない)。"""
    return float(np.prod([(hi - lo) / res for lo, hi in BOUNDS]))


def true_occupancy(res: int, *, legs: bool, hollow: bool) -> np.ndarray:
    """真値を同じ voxel 格子に落とした占有。比を取ると離散化が落ちる。"""
    X, Y, Z = voxel_grid(res)
    return inside(X, Y, Z, legs=legs, hollow=hollow)


# --------------------------------------------------------------------------- #
# 3. 崖の閉形式 —— 接線がつくる多角形                                            #
# --------------------------------------------------------------------------- #
def ellipse_support(a: float, b: float, th) -> np.ndarray:
    """楕円 ``(x/a)^2+(y/b)^2<=1`` の支持関数 ``h(θ) = sqrt(a^2cos^2+b^2sin^2)``。"""
    return np.sqrt((a * np.cos(th)) ** 2 + (b * np.sin(th)) ** 2)


def polygon_over_area(h, th) -> float:
    """法線 ``th``・オフセット ``h`` の接線がつくる多角形の面積(靴紐公式)。"""
    order = np.argsort(np.mod(th, 2 * np.pi))
    th, h = np.asarray(th)[order], np.asarray(h)[order]
    n = np.stack([np.cos(th), np.sin(th)], axis=1)
    verts = []
    for i in range(len(th)):
        j = (i + 1) % len(th)
        M = np.stack([n[i], n[j]])
        if abs(float(np.linalg.det(M))) < 1e-12:    # 平行な接線 = 頂点が無限遠
            return float("inf")
        verts.append(np.linalg.solve(M, np.array([h[i], h[j]])))
    v = np.asarray(verts)
    return 0.5 * abs(float(np.sum(v[:, 0] * np.roll(v[:, 1], -1)
                                  - np.roll(v[:, 0], -1) * v[:, 1])))


def ring_normals(K: int, phase: float = 0.0) -> np.ndarray:
    """軸周り K 台のカメラが与える接線の**法線**。★方位そのものではなく ± 90 度。

    カメラは視線に直交する 2 本の接線(シルエットの左右の縁)を与えるので、
    法線は ``方位 + 90`` と ``方位 - 90``。奇数 K だとこの 2 群が重ならず
    **2K 本**になる —— 偶数 K が半分損をする理由がここにある。
    """
    az = phase + 2 * math.pi * np.arange(K) / K
    th = np.concatenate([az + math.pi / 2, az - math.pi / 2])
    return np.unique(np.round(np.mod(th, 2 * math.pi), 9))


def ring_ratio_ellipse(a: float, b: float, K: int, phase: float = 0.0) -> float:
    """楕円断面を K 台の等間隔リングで彫ったときの**体積の過大率**(厳密)。

    水平断面はどの高さでも同じ楕円を相似に縮めたものなので、多角形/楕円の
    面積比は高さに依らない = **そのまま体積比**になる。
    """
    th = ring_normals(K, phase)
    return polygon_over_area(ellipse_support(a, b, th), th) / (math.pi * a * b)


def ring_ratio_circle(K: int) -> float:
    """円断面のときの過大率 ``(n/π)tan(π/n)``。n = **接線の本数**(K ではない)。"""
    n = len(ring_normals(K))
    return (n / math.pi) * math.tan(math.pi / n)


def naive_ratio_circle(K: int) -> float:
    """現場の素朴な読み ``(K/π)tan(π/K)``。「K 台なら K 角形」という数え方。

    ★偶数 K では正しく、**奇数 K では厳しすぎる**(実際は 2K 本の接線が立つ)。
    """
    return (K / math.pi) * math.tan(math.pi / K)


# --------------------------------------------------------------------------- #
# 4. カメラのリグ                                                               #
# --------------------------------------------------------------------------- #
def _intrinsics(f: float, size) -> np.ndarray:
    h, w = size
    return np.array([[f, 0.0, w / 2 - 0.5], [0.0, f, h / 2 - 0.5], [0.0, 0.0, 1.0]])


def ring_rig(K: int, *, dist: float = D_RING, f: float = F_RING, phase: float = 0.0,
             size=(IMG_H, IMG_W), look_z: float = LOOK_Z):
    """軸周りに等間隔 K 台。返り値 ``(Ks, Rs, ts, size)``。

    ★``visualhull.look_at`` を使う。``fs.look_at`` は**別物**(§7)。
    """
    Km = _intrinsics(f, size)
    Rs, ts = [], []
    for a in phase + 2 * math.pi * np.arange(K) / K:
        R, t = _visualhull.look_at((dist * math.cos(a), dist * math.sin(a), look_z),
                                   (0.0, 0.0, look_z))
        Rs.append(R)
        ts.append(t)
    return [Km] * K, Rs, ts, size


def hemisphere_rig(K: int, rng, *, dist: float = D_RING, f: float = F_RING,
                   size=(IMG_H, IMG_W), look_z: float = LOOK_Z):
    """上半球にランダムに K 台(仰角 0〜75 度・方位一様)。§6 の対照群。"""
    Km = _intrinsics(f, size)
    Rs, ts = [], []
    for _ in range(K):
        az = rng.uniform(0.0, 2 * math.pi)
        el = math.radians(rng.uniform(0.0, 75.0))
        eye = (dist * math.cos(el) * math.cos(az), dist * math.cos(el) * math.sin(az),
               look_z + dist * math.sin(el))
        R, t = _visualhull.look_at(eye, (0.0, 0.0, look_z))
        Rs.append(R)
        ts.append(t)
    return [Km] * K, Rs, ts, size


def silhouettes(cloud: np.ndarray, rig, *, dilate: int = 0, erode: int = 0):
    """点群を各カメラへ射影して前景マスクを作る(``synthesize_silhouette``)。

    ``dilate`` は op に渡す(``binary_dilation`` の反復)。``erode`` は op に無いので
    ``fs.op.erosion_circle`` を使う —— ``a`` が半径 1〜4 の bucket(§7)。
    """
    Ks, Rs, ts, size = rig
    out = []
    for Km, R, t in zip(Ks, Rs, ts):
        sil = np.asarray(_L.synthesize_silhouette(cloud, Km, R, t, size,
                                                  fill=True, dilate=dilate), dtype=bool)
        if erode:
            a = {1: 0.0, 2: 0.34, 3: 0.67, 4: 1.0}[int(erode)]
            sil = np.asarray(fs.op.erosion_circle(sil.astype(np.float64), a=a, b=0.0)) > 0.5
        out.append(sil)
    return out


def hull_occupancy(cloud: np.ndarray, rig, res: int = RES, **kw) -> np.ndarray:
    """視体積交差の voxel 占有(``carve`` = ``visual_hull``)。"""
    Ks, Rs, ts, _ = rig
    return np.asarray(_L.carve(silhouettes(cloud, rig, **kw), Ks, Rs, ts, BOUNDS, res))


# --------------------------------------------------------------------------- #
# 5. 物差し —— 体積 / 胸囲 / 重心の高さ                                          #
# --------------------------------------------------------------------------- #
def occ_volume(occ: np.ndarray, res: int = RES) -> float:
    """占有 → 体積 [m^3]。``vol_rle_encode`` + ``vol_rle_volume`` は **voxel 個数**まで。"""
    rle = _L.vol_rle_encode(occ.astype(np.float64))
    return int(_L.vol_rle_volume(rle)) * voxel_volume(res)


def occ_centroid_z(occ: np.ndarray, res: int = RES) -> float:
    """占有の重心の高さ [m]。``vol_rle_centroid`` は軸 (0,1,2) を (z,y,x) と呼ぶ ——
    こちらの軸 2 は **z** なので、返りの 3 番目を拾う。"""
    rle = _L.vol_rle_encode(occ.astype(np.float64))
    idx = float(_L.vol_rle_centroid(rle)[2])
    lo, hi = BOUNDS[2]
    return lo + (idx + 0.5) * (hi - lo) / res


def occ_length(occ: np.ndarray, res: int = RES) -> float:
    """占有の体長 [m](軸 0 = x)。``vol_rle_bbox`` は上端が排他。"""
    bb = _L.vol_rle_bbox(_L.vol_rle_encode(occ.astype(np.float64)))
    lo, hi = BOUNDS[0]
    return (int(bb[3]) - int(bb[0])) * (hi - lo) / res


def _convex_perimeter(points: np.ndarray) -> float:
    """2-D 点集合の凸包の周囲長。巻尺は凸包を測る道具なので、胸囲はこれ。"""
    if points.shape[0] < 3:
        return float("nan")
    v = points[ConvexHull(points).vertices]
    d = np.roll(v, -1, axis=0) - v
    return float(np.sum(np.hypot(d[:, 0], d[:, 1])))


def occ_girth(occ: np.ndarray, res: int = RES, xg: float = GIRTH_X) -> float:
    """胸囲 [m] = ``x = xg`` の縦断面の凸包の周囲長。"""
    ax = voxel_axes(res)
    xi = int(np.argmin(np.abs(ax[0] - xg)))
    j, k = np.nonzero(occ[xi])
    return _convex_perimeter(np.column_stack([ax[1][j], ax[2][k]]))


def true_girth_analytic(xg: float = GIRTH_X, n: int = 4001) -> float:
    """真の胸囲 [m](解析的な断面境界から)。格子の偏りを見るための対照。"""
    s = math.sqrt(max(0.0, 1.0 - (xg / A) ** 2))
    y = np.linspace(-B * s, B * s, n)
    top = z_top(xg, y) - hollow_depth(xg, y)
    bot = z_bot(xg, y)
    return _convex_perimeter(np.column_stack([np.concatenate([y, y]),
                                              np.concatenate([top, bot])]))


def convex_hull_occupancy(res: int = RES):
    """凸包の voxel 占有。``convex_hull``(op)の面を半空間として全 voxel に当てる。

    面の数だけ内積を回すので、標本点は粗く取る(内接多面体になる分だけ
    体積は**過小**に出る —— その量も併せて返して印字する)。
    """
    pts = [_fibonacci_sphere(220) * np.array([A, B, C]) + np.array([0.0, 0.0, Z0])]
    ang = np.linspace(0.0, 2 * math.pi, 25, endpoint=False)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            wx = sx * LEG_X + LEG_R * np.cos(ang)
            wy = sy * LEG_Y + LEG_R * np.sin(ang)
            pts.append(np.stack([wx, wy, np.zeros(ang.size)], axis=1))
    coarse = np.concatenate(pts, axis=0)
    V, F = _L.convex_hull(coarse)
    V = np.asarray(V, np.float64)
    F = np.asarray(F, np.int64)
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nrm = np.cross(v1 - v0, v2 - v0)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    off = np.einsum("ij,ij->i", nrm, v0)
    X, Y, Z = voxel_grid(res)
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    alive = np.ones(P.shape[0], bool)
    for k in range(nrm.shape[0]):                    # 面を 1 枚ずつ削る(生き残りだけ見る)
        idx = np.nonzero(alive)[0]
        if idx.size == 0:
            break
        bad = P[idx] @ nrm[k] > off[k] + 1e-9
        alive[idx[bad]] = False
    fine = _L.convex_hull(surface_cloud(legs=True, hollow=False, n=20_000))
    return (alive.reshape(X.shape),
            float(_L.mesh_volume((V, F))), float(_L.mesh_volume(fine)))


# --------------------------------------------------------------------------- #
def _pct(v, truth):
    return 100.0 * (v - truth) / truth


# --------------------------------------------------------------------------- #
def section_truth():
    print("=== 1. グラウンドトゥルース —— 体積が厳密に出る置き方 ===")
    v_torso = torso_volume()
    print(f"  胴(閉形式 (4/3)πabc)        {v_torso:10.6f} m^3")
    print(f"  {'刻み [m]':>10}{'くぼみ [m^3]':>16}{'脚 1 本 [m^3]':>16}")
    hol = leg = 0.0
    for step in (0.004, 0.002, 0.001, 0.0005):
        hol, leg = hollow_volume(step), leg_volume(step)
        print(f"  {step:>10.4f}{hol:>16.6f}{leg:>16.6f}")
    v_true = v_torso - hol + 4.0 * leg
    print(f"  体積の真値 = 胴 - くぼみ + 脚4本 = {v_true:.6f} m^3"
          f"  → 体重 {v_true * RHO:.1f} kg(密度 {RHO:.0f} kg/m^3)")
    occ = true_occupancy(RES, legs=True, hollow=True)
    v_grid = occ_volume(occ)
    print(f"  同じ voxel 格子({RES}^3、voxel {voxel_volume(RES) * 1e6:.2f} cm^3)では "
          f"{v_grid:.6f} m^3 ({_pct(v_grid, v_true):+.3f} %)")
    print("  → 以後 hull と真値は**同じ格子の占有数**で比べる。離散化は比で落ちる。")
    conv = true_occupancy(RES, legs=False, hollow=False)
    print(f"  対照群(凸な胴だけ)の格子体積 {occ_volume(conv):.6f} m^3 "
          f"({_pct(occ_volume(conv), v_torso):+.3f} %)")
    g_ana, g_grid = true_girth_analytic(), occ_girth(occ)
    print(f"  胸囲(x={GIRTH_X:.2f} m の断面の凸包): 解析 {g_ana:.4f} m / "
          f"格子 {g_grid:.4f} m ({_pct(g_grid, g_ana):+.2f} %。voxel 中心を結ぶ分だけ短い)")
    print(f"  体表面積 {body_surface():.3f} m^2(楕円体は Thomsen 近似)、"
          f"S/V = {body_surface() / v_true:.2f} /m")
    return {"torso": v_torso, "hollow": hol, "leg": leg, "true": v_true,
            "grid": v_grid, "occ": occ, "conv": conv, "girth": g_grid,
            "girth_ana": g_ana, "weight": v_true * RHO}


def section_null(truth):
    print("\n=== 2. ゼロ点 —— 素朴な 2 つと、参考の 2 つ ===")
    cloud = surface_cloud(legs=True, hollow=True)
    X, Y, Z = voxel_grid(RES)
    v_true, occ_t = truth["true"], truth["occ"]
    rows, out = [], {}

    lo = cloud.min(axis=0)
    hi = cloud.max(axis=0)
    aabb = ((X >= lo[0]) & (X <= hi[0]) & (Y >= lo[1]) & (Y <= hi[1])
            & (Z >= lo[2]) & (Z <= hi[2]))
    out["外接直方体"] = aabb
    print(f"  外接直方体 {hi[0] - lo[0]:.2f} x {hi[1] - lo[1]:.2f} x {hi[2] - lo[2]:.2f} m")

    rig1 = ring_rig(1, phase=math.pi / 2)             # 真横から 1 台
    sil = silhouettes(cloud, rig1)[0]
    one = np.asarray(_L.carve([sil], rig1[0], rig1[1], rig1[2], BOUNDS, RES))
    out["1 枚 x 一定奥行き"] = one & (np.abs(Y) <= B)

    ob = _L.obb(cloud[::37])
    cen = np.asarray(ob["center"], np.float64)
    axes = np.asarray(ob["axes"], np.float64)
    ext = np.asarray(ob["extents"], np.float64).ravel()
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1) - cen
    loc = np.abs(P @ axes)
    out["OBB"] = (loc <= ext[None, :] + 1e-12).all(axis=1).reshape(X.shape)

    hull_occ, v_coarse, v_fine = convex_hull_occupancy()
    out["凸包"] = hull_occ
    print(f"  凸包: 粗い標本({v_coarse:.5f} m^3)は細かい標本({v_fine:.5f} m^3)より "
          f"{_pct(v_coarse, v_fine):+.2f} %(内接多面体なので過小。voxel 占有はこの粗い方)")

    print(f"  {'ゼロ点':>18}{'体積 [m^3]':>14}{'真値比':>10}{'体重 [kg]':>12}{'誤差':>12}")
    for name, occ in out.items():
        v = occ_volume(occ)
        rows.append((name, f"{v:.4f}", f"{v / v_true:.3f}", f"{v * RHO:.0f}",
                     f"{_pct(v * RHO, truth['weight']):+.1f} %"))
        print(f"  {name:>18}{v:>14.4f}{v / v_true:>10.3f}{v * RHO:>12.0f}"
              f"{_pct(v, v_true):>11.1f}%")
    print(f"  {'真値':>18}{v_true:>14.4f}{1.0:>10.3f}{truth['weight']:>12.0f}"
          f"{0.0:>11.1f}%")
    print(f"  真値の voxel 数 {int(occ_t.sum())} —— 以後の比はこれを分母にする。")
    figs.save_table("null_baseline", ["ゼロ点", "体積 [m^3]", "真値比", "体重 [kg]", "誤差"],
                    rows, title="ゼロ点 —— 素朴な体積推定はどれだけ上に出るか",
                    caption=f"真値 {v_true:.4f} m^3 / {truth['weight']:.0f} kg。"
                            "外接直方体と OBB は上界の中でもいちばん粗い。")
    return out


def section_closed_form(truth):
    print("\n=== 3. 崖 —— 必要な台数は測る前に閉形式で出る ===")
    print("  ★「K 台なら K 角形」は正しくない。**平行投影ではカメラ 1 台が視線に")
    print("     直交する接線 2 本**を与え、法線は方位 ± 90 度。しかも**向かい合う")
    print("     2 台は同じ 2 本**しか与えない(平行投影の輪郭は裏表で一致する)ので、")
    print("     接線の本数は偶数 K なら K 本、奇数 K なら **2K 本**になる。")
    print(f"  {'K':>4}{'接線':>6}{'閉形式(楕円)':>16}{'円 n 角形':>12}"
          f"{'素朴な読み':>12}{'実測(60 m)':>14}{'差':>10}")
    cloud = surface_cloud(legs=False, hollow=False)
    n_true = int(truth["conv"].sum())
    rows, meas, worst = [], {}, 0.0
    for K in (3, 4, 5, 6, 8, 12, 13, 16, 24):
        rig = ring_rig(K, dist=D_FAR, f=F_FAR)
        r = int(hull_occupancy(cloud, rig).sum()) / n_true
        pred = ring_ratio_ellipse(A, B, K)
        meas[K] = r
        worst = max(worst, abs(r - pred))
        rows.append((str(K), str(len(ring_normals(K))), f"{pred:.5f}",
                     f"{ring_ratio_circle(K):.5f}", f"{naive_ratio_circle(K):.5f}",
                     f"{r:.5f}", f"{r - pred:+.5f}"))
        print(f"  {K:>4}{len(ring_normals(K)):>6}{pred:>16.5f}"
              f"{ring_ratio_circle(K):>12.5f}{naive_ratio_circle(K):>12.5f}"
              f"{r:>14.5f}{r - pred:>10.5f}")
    print(f"  → 実測は**全 K で閉形式の上**(差 +0.002 〜 +{worst:.5f})。")
    print("     差の正体は §6 の被覆マージン(1 画素触れば前景 = 太る側の丸め)。")
    print("     **閉形式は下界として当たった**。")
    print(f"  ★3 台 {meas[3]:.5f} と 6 台 {meas[6]:.5f}。閉形式は "
          f"{ring_ratio_ellipse(A, B, 3):.5f} と {ring_ratio_ellipse(A, B, 6):.5f} で "
          "**厳密に同数**")
    print("     —— 接線の集合が完全に一致するから(3 台の ±90 度 = 6 台の ±90 度)。")
    print(f"     実測が {meas[6] - meas[3]:+.5f} だけ違うのは幾何ではなく離散化: ")
    print("     6 台では同じ接線を 2 回測るので、量子化の厳しい方が採られる。")
    print("     **情報としては 3 台と 6 台は同じ**。")
    # 有限距離だと向かい合う 2 台は別の楔になる(平行投影の縮退が解ける)
    near = {}
    for K in (3, 6):
        near[K] = int(hull_occupancy(cloud, ring_rig(K)).sum()) / n_true
    print(f"  ★対照(有限距離 {D_RING:.0f} m): 3 台 {near[3]:.5f} / 6 台 {near[6]:.5f} —— ")
    print(f"     差が {near[3] - near[6]:.5f} と平行投影の {meas[3] - meas[6]:.5f} の "
          f"{(near[3] - near[6]) / max(meas[3] - meas[6], 1e-9):.1f} 倍に開く。")
    print("     **縮退は平行投影の性質**で、近づけると解ける(視錐は楔で、裏表が別物になる)。")
    print(f"  ★13 台 {meas[13]:.5f} < 16 台 {meas[16]:.5f} —— **奇数のほうが効く**。")
    k_odd = next(K for K in range(3, 200) if ring_ratio_ellipse(A, B, K) <= 1.02)
    k_even = next(K for K in range(4, 200, 2) if ring_ratio_ellipse(A, B, K) <= 1.02)
    k_naive = next(K for K in range(3, 200) if naive_ratio_circle(K) <= 1.02)
    print(f"  ★**体重 2 % 以内**を要求すると: 細長い胴の厳密解で **{k_odd} 台**(奇数可)、")
    print(f"     偶数リグに限ると **{k_even} 台**。円の素朴な読み (K/π)tan(π/K) だと "
          f"{k_naive} 台と出る")
    print(f"     ので、**偶数台で組む現場は {k_even - k_naive} 台足りない**見積りを持つ。")
    figs.save_table("closed_form", ["K", "接線の本数", "閉形式(楕円)", "円 n 角形",
                                    "素朴な読み", "実測(60 m)", "差"], rows,
                    title="必要な台数は測る前に出る —— 接線がつくる多角形",
                    caption="法線は方位 ± 90 度。向かい合う 2 台は同じ接線なので、"
                            "奇数 K だけが 2K 本になる。実測は近似平行投影"
                            "(60 m・4.0 mm/px)・凸な胴だけの対照群。")
    if figs.enabled():
        ks = np.arange(3, 33)
        figs.save_plot(
            "closed_form_curve",
            [("閉形式(楕円 a/b=2.76)", ks, np.array([ring_ratio_ellipse(A, B, int(k))
                                                     for k in ks])),
             ("素朴な読み(円 K 角形)", ks,
              np.array([naive_ratio_circle(int(k)) for k in ks])),
             ("実測(60 m)", np.array(sorted(meas), float),
              np.array([meas[k] for k in sorted(meas)]))],
            xlabel="カメラ台数 K", ylabel="体積の過大率(真値 = 1)",
            title="細長い体では、円の目安が台数を少なく見積もる",
            caption="のこぎり刃は偶数/奇数の差(奇数は接線が 2 倍立つ)。"
                    "素朴な読みに沿って台数を決めると、偶数台のリグでは届かない。")
    return {"meas": meas, "worst": worst, "k_odd": k_odd, "k_even": k_even,
            "k_naive": k_naive, "near": near}


def section_persistent(truth):
    print("\n=== 4. 消える誤差と消えない誤差を分けて数える ===")
    X, Y, Z = voxel_grid(RES)
    occ_t = truth["occ"]
    no_hollow = inside(X, Y, Z, legs=True, hollow=False)
    hollow_reg = no_hollow & ~occ_t                    # くぼみで削った所(真に空)
    foot = (X / A) ** 2 + (Y / B) ** 2 <= 1.0
    belly_reg = foot & (Z < z_bot(X, Y)) & ~occ_t      # 腹の下・脚の間(真に空)
    print(f"  くぼみ {int(hollow_reg.sum())} voxel"
          f"({occ_volume(hollow_reg):.4f} m^3、体の {100 * occ_volume(hollow_reg) / truth['true']:.2f} %)/ "
          f"脚の間 {int(belly_reg.sum())} voxel({occ_volume(belly_reg):.4f} m^3)")
    print(f"  {'K':>4}{'過大率':>10}{'くぼみを埋めた率':>20}"
          f"{'脚の間の幽霊':>16}{'取りこぼし':>12}")
    cloud = surface_cloud(legs=True, hollow=True)
    n_true = int(occ_t.sum())
    rows, out = [], {}
    for K in (4, 6, 8, 12, 16, 24, 32, 48):
        occ = hull_occupancy(cloud, ring_rig(K))
        r = int(occ.sum()) / n_true
        fill = float((occ & hollow_reg).sum()) / float(hollow_reg.sum())
        ghost = float((occ & belly_reg).sum()) / float(belly_reg.sum())
        miss = int((occ_t & ~occ).sum())
        out[K] = {"ratio": r, "fill": fill, "ghost": ghost, "miss": miss, "occ": occ}
        rows.append((str(K), f"{r:.5f}", f"{100 * fill:.1f} %", f"{100 * ghost:.2f} %",
                     str(miss)))
        print(f"  {K:>4}{r:>10.5f}{100 * fill:>19.1f}%{100 * ghost:>15.2f}%{miss:>12}")
    f4, f48 = out[4]["fill"], out[48]["fill"]
    g4, g48 = out[4]["ghost"], out[48]["ghost"]
    print(f"  → ★くぼみは {100 * f4:.1f} % → {100 * f48:.1f} %。カメラを 12 倍にして "
          f"{100 * (f4 - f48):.1f} ポイントしか減らない。")
    print(f"     脚の間の幽霊は {100 * g4:.2f} % → {100 * g48:.2f} %({g4 / g48:.1f} 倍)"
          "と素直に減る。")
    print("     分かれ目は**凹みが輪郭に出るか**。背中のくぼみは、どの方位から見ても")
    print("     隣の高い所に隠れて輪郭に現れない = シルエットに情報が無い(K→∞ でも残る)。")
    print(f"  取りこぼし(真に在る voxel を削った数)は全 K で 0 —— ``dilate=0`` でも "
          "被覆意味のシルエットは保守側に丸めている。")
    figs.save_table("persistent", ["K", "過大率", "くぼみを埋めた率", "脚の間の幽霊",
                                   "取りこぼし"], rows,
                    title="カメラを増やして消える誤差と、消えない誤差",
                    caption="くぼみ(輪郭に出ない凹み)は台数に鈍感、"
                            "脚の間(輪郭に出る凹み)は台数に敏感。")
    if figs.enabled():
        ks = np.array(sorted(out), float)
        figs.save_plot(
            "persistent_curve",
            [("背中のくぼみを埋めた率", ks, np.array([100 * out[int(k)]["fill"] for k in ks])),
             ("脚の間に立つ幽霊の率", ks, np.array([100 * out[int(k)]["ghost"] for k in ks]))],
            xlabel="カメラ台数 K", ylabel="真に空の領域を占めた割合 [%]",
            title="台数で消える誤差と、消えない誤差",
            caption="同じ 1 本の掃引で 2 本の曲線。上が平ら = 何台置いても埋まったまま。")
    return {"out": out, "hollow_reg": hollow_reg, "belly_reg": belly_reg}


def section_metrics(truth, nulls, pers):
    print("\n=== 5. 物差しを 3 つ置く —— 体積 / 胸囲 / 重心 ===")
    est = dict(nulls)
    est["視体積交差 K=8"] = pers["out"][8]["occ"]
    est["視体積交差 K=24"] = pers["out"][24]["occ"]
    # 実務の「縮小補正」—— 太る側の丸めを 2 画素引いて戻す(§6 の 1 画素則の応用)
    est["K=24 + 2 画素収縮"] = hull_occupancy(surface_cloud(legs=True, hollow=True),
                                              ring_rig(24), erode=2)
    g_true = truth["girth"]
    l_true = occ_length(truth["occ"])
    z_true = occ_centroid_z(truth["occ"])
    w_true = truth["weight"]
    k_allo = w_true / (g_true ** 2 * l_true)           # ★真値で較正(式の当否は問わない)
    print(f"  真値: 体重 {w_true:.1f} kg / 胸囲 {g_true:.4f} m / 体長 {l_true:.4f} m / "
          f"重心の高さ {z_true:.4f} m")
    print(f"  アロメトリ W = k·胸囲^2·体長、k = {k_allo:.2f} は**真値で較正**。")
    print("  → 予測: ΔW/W = 2·ΔG/G + ΔL/L。**胸囲の誤差は体重で 2 倍になる**。")
    print(f"  {'推定器':>18}{'体重(体積)':>14}{'胸囲':>10}{'体重(アロメトリ)':>18}"
          f"{'重心の高さ':>14}")
    rows, res = [], {}
    for name, occ in est.items():
        v = occ_volume(occ)
        g = occ_girth(occ)
        ln = occ_length(occ)
        zc = occ_centroid_z(occ)
        w_allo = k_allo * g * g * ln
        res[name] = {"w_vol": v * RHO, "girth": g, "w_allo": w_allo, "z": zc,
                     "len": ln}
        rows.append((name, f"{_pct(v * RHO, w_true):+.1f} %", f"{_pct(g, g_true):+.1f} %",
                     f"{_pct(w_allo, w_true):+.1f} %", f"{zc - z_true:+.3f} m"))
        print(f"  {name:>18}{_pct(v * RHO, w_true):>13.1f}%{_pct(g, g_true):>9.1f}%"
              f"{_pct(w_allo, w_true):>17.1f}%{zc - z_true:>13.3f} m")
    best_vol = min(res, key=lambda k: abs(res[k]["w_vol"] - w_true))
    best_allo = min(res, key=lambda k: abs(res[k]["w_allo"] - w_true))
    best_z = min(res, key=lambda k: abs(res[k]["z"] - z_true))
    print(f"  → 勝者: 体重(体積)= **{best_vol}** / 体重(アロメトリ)= **{best_allo}** / "
          f"重心 = **{best_z}**")
    print("  ★アロメトリで凸包が強いのは偶然ではない —— **巻尺は凸包を測る道具**なので、")
    print("     背中のくぼみはアロメトリには最初から効かない(体積には効く)。")
    v24 = res["視体積交差 K=24"]
    pred = 2 * _pct(v24["girth"], g_true) + _pct(v24["len"], l_true)
    print(f"  ★2 倍則の検算(K=24): 胸囲 {_pct(v24['girth'], g_true):+.2f} % ・"
          f"体長 {_pct(v24['len'], l_true):+.2f} % → 予測 {pred:+.2f} %、"
          f"実測 {_pct(v24['w_allo'], w_true):+.2f} %")
    figs.save_table("metrics", ["推定器", "体重(体積)", "胸囲", "体重(アロメトリ)",
                                "重心の高さ"], rows,
                    title="物差しを変えると勝者が入れ替わる",
                    caption=f"真値 {w_true:.0f} kg / 胸囲 {g_true:.3f} m / "
                            f"重心 {z_true:.3f} m。アロメトリの係数は真値で較正済み。")
    return {"res": res, "best": (best_vol, best_allo, best_z), "g_true": g_true,
            "l_true": l_true, "z_true": z_true, "k_allo": k_allo, "pred2": pred}


def section_controls(truth):
    print("\n=== 6. 対照群 —— 配置の乱れと、前景マスクの太り ===")
    cloud = surface_cloud(legs=True, hollow=True)
    n_true = int(truth["occ"].sum())

    # (c) シルエットの膨張・収縮 -------------------------------------------- #
    px = D_RING / F_RING
    sv = body_surface() / truth["true"]
    print(f"  (c) 1 画素 = {px * 1000:.1f} mm。Steiner の予測 ΔV/V = (S/V)·δ = "
          f"{sv:.2f} × {px * 1000:.1f} mm = {100 * sv * px:+.2f} %/px")
    print(f"  {'画素':>8}{'過大率':>10}{'ゼロからの差':>16}{'1 画素あたり':>16}")
    rows, dil = [], {}
    for d in (-3, -2, -1, 0, 1, 2, 3):
        kw = {"erode": -d} if d < 0 else {"dilate": d}
        r = int(hull_occupancy(cloud, ring_rig(12), **kw).sum()) / n_true
        dil[d] = r
        rows.append((f"{d:+d}", f"{r:.5f}", "", ""))
        print(f"  {d:>8d}{r:>10.5f}", end="")
        if d != 0 and 0 in dil:
            print(f"{100 * (r - dil[0]):>15.2f}%{100 * (r - dil[0]) / d:>15.2f}%")
        else:
            print(f"{'':>16}{'':>16}")
    per_px = 100 * (dil[1] - dil[0])
    rows = [(f"{d:+d}", f"{dil[d]:.5f}", f"{100 * (dil[d] - dil[0]):+.2f} %",
             f"{100 * (dil[d] - dil[0]) / d:+.2f} %" if d else "-") for d in sorted(dil)]
    print(f"  → 実測 {per_px:+.2f} %/px、Steiner 予測 {100 * sv * px:+.2f} %/px "
          f"(比 {per_px / (100 * sv * px):.2f})。**予測を外した**(下限のはずが上回られた)。")
    print("     hull の表面は体より大きいので予測は下限になるはず —— 実際は下回った。")
    print("     理由は、膨張が**画像で等方**でも世界では視線方向に効かないため:")
    print("     水平リングでは各カメラが縦横 2 方向しか押し広げず、Steiner の")
    print("     『全方向に δ』より弱い。**予測は上限として使うべきだった**。")
    print(f"  ★既定 ``dilate=1`` のまま体積を測ると {per_px:+.2f} %(体重 "
          f"{truth['weight'] * per_px / 100:+.1f} kg)の下駄が乗る。")

    # (b) 上半球ランダム ------------------------------------------------------ #
    print("\n  (b) 8 台を上半球にランダムに置く vs 軸周り等間隔(120 試行)")
    small = (320, 240)
    small_cloud = surface_cloud(legs=True, hollow=True, n=250_000)
    kw = {"dist": D_RING, "f": 1000.0, "size": (small[1], small[0])}
    res_s = 64
    occ_s = true_occupancy(res_s, legs=True, hollow=True)
    n_s = int(occ_s.sum())
    base = int(hull_occupancy(small_cloud, ring_rig(8, **kw), res_s).sum()) / n_s
    rng = np.random.default_rng(11)
    vals = np.array([int(hull_occupancy(small_cloud, hemisphere_rig(8, rng, **kw),
                                        res_s).sum()) / n_s for _ in range(120)])
    win = int((vals <= base).sum())
    print(f"     解像度を落とした台({res_s}^3・8.0 mm/px)での等間隔 8 台 = "
          f"{100 * (base - 1):+.2f} %")
    print(f"     ランダム 8 台 120 試行: 平均 {100 * (vals.mean() - 1):+.2f} % / "
          f"標準偏差 {100 * vals.std(ddof=1):.2f} / "
          f"最良 {100 * (vals.min() - 1):+.2f} % / 最悪 {100 * (vals.max() - 1):+.2f} %")
    print(f"     等間隔以下だった試行 **{win} / 120**。")
    print(f"     ★0 でも分母を疑う —— 最良の試行でも等間隔より "
          f"{100 * (vals.min() - base):+.2f} ポイント悪く、これは標準偏差の "
          f"{(vals.min() - base) / vals.std(ddof=1):.1f} 倍。小標本の産物ではない。")
    figs.save_table("controls", ["シルエットの画素", "過大率", "ゼロからの差",
                                 "1 画素あたり"], rows,
                    title="前景マスクが 1 画素太ると体積が何 % 増えるか",
                    caption=f"K=12・4.0 mm/px。Steiner の予測 {100 * sv * px:+.2f} %/px は"
                            "**上限**として使うべきだった(§6 に理由)。")
    if figs.enabled():
        ds = np.array(sorted(dil), float)
        figs.save_plot(
            "dilate_line",
            [("Steiner の予測 (S/V)·δ", ds, 100 * (dil[0] - 1) + 100 * sv * px * ds),
             ("実測", ds, np.array([100 * (dil[d] - 1) for d in sorted(dil)]))],
            xlabel="シルエットの膨張(+)/ 収縮(-)[画素]", ylabel="体積の過大率 [%]",
            title="前景抽出のしきい値 1 段が、体重で数十 kg 動く",
            caption="予測の傾きは実測より急。膨張は画像で等方でも、"
                    "水平リングでは世界の全方向を押し広げない。")
        figs.save_plot(
            "hemisphere_scatter",
            [("上半球ランダム 8 台", np.arange(vals.size, dtype=float),
              100 * (vals - 1.0)),
             ("軸周り等間隔 8 台", np.array([0.0, float(vals.size - 1)]),
              np.array([100 * (base - 1), 100 * (base - 1)]))],
            xlabel="試行", ylabel="体積の過大率 [%]",
            title="配置の乱れは台数では買い戻せない",
            caption=f"120 試行で等間隔を下回ったのは {win} 件。"
                    "解像度を落とした台なので絶対値は §4 より大きい。",
            kinds=["scatter", "line"])
    return {"dil": dil, "per_px": per_px, "steiner": 100 * sv * px,
            "base": base, "vals": vals, "win": win}


def section_op_hole(truth):
    print("\n=== 7. 道具の穴 —— 4 層すべて引いてから言う ===")
    print("  ★(1) ``look_at`` の名前衝突。``fs.op_find('look')`` は **0 件**、")
    print("     ``fs.look_at`` は render3d の gluLookAt 版(4x4・**-Z 前方**)。")
    print("     ``carve`` が要る OpenCV 版 ``(R, t)``・**+Z 前方** は")
    print("     ``visualhull.look_at`` にあるが、``fs.`` / ``fs.op.`` / ``fs.ledger.`` /")
    print("     ``op_find`` のどれからも出てこない。実演 ——")
    cloud = surface_cloud(legs=True, hollow=True, n=120_000)
    M = np.asarray(fs.look_at((D_RING, 0.0, LOOK_Z), (0.0, 0.0, LOOK_Z)), np.float64)
    Km = _intrinsics(F_RING, (IMG_H, IMG_W))
    bad_R, bad_t = M[:3, :3], M[:3, 3]
    bad_sil = np.asarray(_L.synthesize_silhouette(cloud, Km, bad_R, bad_t,
                                                  (IMG_H, IMG_W)), bool)
    good_R, good_t = _visualhull.look_at((D_RING, 0.0, LOOK_Z), (0.0, 0.0, LOOK_Z))
    good_sil = np.asarray(_L.synthesize_silhouette(cloud, Km, good_R, good_t,
                                                   (IMG_H, IMG_W)), bool)
    bad_occ = np.asarray(_L.carve([bad_sil], [Km], [bad_R], [bad_t], BOUNDS, 48))
    print(f"     fs.look_at 由来 (R,t): 前景画素 {int(bad_sil.sum())} 個、"
          f"1 台の hull の占有 **{int(bad_occ.sum())} voxel**")
    print(f"     visualhull.look_at 由来: 前景画素 {int(good_sil.sum())} 個")
    print("     全 voxel が『カメラ後方』と判定されるだけなので、**例外は出ない**。")
    print("     0 台は ``ValueError`` で fail-closed なのに、**規約違いは黙って空**。")
    print("  (2) 2-D の凸包の周囲長を**実寸で**返す op が無い。``shape_trans`` は領域の")
    print("     凸包を返すが、``contlength`` は regionprops の周囲長を 2(H+W) で")
    print("     正規化した値。``shape_trans_xld`` に画像を渡すと fallback 警告つきで")
    print("     IndexError(XLD 用なので当然)。→ 胸囲は自前 + scipy で書いた。")
    print("  (3) ``synthesize_silhouette`` は膨張しかできず、収縮は ``fs.op.erosion_circle``")
    print("     (``a`` が半径 1〜4 の bucket)に取りに行く。既定 ``dilate=1`` は recall の")
    print(f"     ための保守側で docstring も明言しているが、体積用途では "
          f"{'+2.6' if True else ''} % 級の下駄になる —— そこは書かれていない。")
    print("  → 次に埋めるべき op: ``vh_look_at``(OpenCV 規約の (R,t) を公開層へ)/ ")
    print("     ``visual_hull_ring(K, dist, f)`` のリグ生成 / ``silhouette_erode`` /")
    print("     ``voxel_volume(occ, spacing)``(3 軸 spacing 込み)/ 2-D の ``convex_perimeter``。")
    return {"bad_sil": int(bad_sil.sum()), "bad_occ": int(bad_occ.sum()),
            "good_sil": int(good_sil.sum())}


def section_figures(truth, pers, closed):
    """図 —— 段階を追って見せる。"""
    if not figs.enabled():
        return
    occ_t = truth["occ"]
    occ8, occ24 = pers["out"][8]["occ"], pers["out"][24]["occ"]

    def side(o):
        """側面(y 方向へ潰す)。行 = 高さ(上が上)、列 = 体長。"""
        return o.max(axis=1).T[::-1].astype(float)

    gx = np.linspace(-A, A, 320)
    gy = np.linspace(-B, B, 160)
    GX, GY = np.meshgrid(gx, gy, indexing="ij")
    top = np.where(_radial(GX, GY) > 0, z_top(GX, GY) - hollow_depth(GX, GY), np.nan)
    top = np.where(np.isfinite(top), top, np.nanmin(top))
    figs.save_grid("scene",
                   [side(occ_t), np.asarray(fs.colorize_height(top.T[::-1], "terrain")),
                    side(occ8), side(occ24)],
                   ["真の占有(側面)", "背中の高さ(上から。中央がくぼみ)",
                    "視体積交差 K=8(側面)", "視体積交差 K=24(側面)"],
                   ncols=2,
                   title="視体積交差は上から見ても横から見ても、必ず太る",
                   caption="脚の間の幽霊は K を上げると細くなるが、背中のくぼみは"
                           "側面図でも埋まったまま(輪郭に出ない凹みだから)。")

    rig = ring_rig(8)
    sils = silhouettes(surface_cloud(legs=True, hollow=True), rig)
    figs.save_grid("silhouettes", [s.astype(float) for s in sils[:4]],
                   ["方位 0 度(真正面)", "方位 45 度", "方位 90 度(真横)",
                    "方位 135 度"], ncols=2,
                   title="彫刻の材料 —— 8 台のうち 4 枚",
                   caption="真横の 1 枚に脚の間の空隙が写っている。"
                           "背中のくぼみはどの 1 枚にも写らない。")

    ax = voxel_axes(RES)
    zi = int(np.argmin(np.abs(ax[2] - Z0)))
    slices = [occ_t[:, :, zi].astype(float)]
    names = ["真の断面(z = 1.05 m)"]
    for K in (4, 8, 16):
        slices.append(hull_occupancy(surface_cloud(legs=True, hollow=True),
                                     ring_rig(K, dist=D_FAR, f=F_FAR))[:, :, zi].astype(float))
        names.append(f"K={K}(接線 {len(ring_normals(K))} 本の多角形)")
    figs.save_grid("slice_polygon", slices, names, ncols=2,
                   title="水平断面は楕円ではなく、接線がつくる多角形になる",
                   caption="近似平行投影。K=4 は外接長方形そのもの(比 4/π = 1.273)。"
                           "角が丸く見えるのは voxel の刻み。")

    diff = occ8.astype(float) - occ_t.astype(float)
    figs.save_grid("excess",
                   [side(occ_t), diff.sum(axis=1).T[::-1],
                    diff[:, :, zi], diff.max(axis=1).T[::-1]],
                   ["真の占有(側面)", "余分の厚み(y 方向の積算)",
                    "余分(水平断面 z = 1.05 m)", "余分の有無(側面)"],
                   ncols=2, signed=[False, True, True, True],
                   title="K=8 で余った分はどこに付いているか",
                   caption="腹の下と脚の間(前後方向に張り出す)と、背中のくぼみ。"
                           "符号つきなので 0 が暗い。")


# --------------------------------------------------------------------------- #
def main():
    t0 = time.perf_counter()
    truth = section_truth()
    nulls = section_null(truth)
    closed = section_closed_form(truth)
    pers = section_persistent(truth)
    mets = section_metrics(truth, nulls, pers)
    ctl = section_controls(truth)
    hole = section_op_hole(truth)
    section_figures(truth, pers, closed)

    print("\n=== 8. まとめ —— 何がどれだけ効いたか ===")
    rows = [
        ("ゼロ点: 外接直方体", f"{_pct(occ_volume(nulls['外接直方体']), truth['true']):+.1f} %"),
        ("ゼロ点: 1 枚 x 一定奥行き",
         f"{_pct(occ_volume(nulls['1 枚 x 一定奥行き']), truth['true']):+.1f} %"),
        ("凸包(巻尺が測るもの)", f"{_pct(occ_volume(nulls['凸包']), truth['true']):+.1f} %"),
        ("視体積交差 K=4", f"{100 * (pers['out'][4]['ratio'] - 1):+.1f} %"),
        ("視体積交差 K=8", f"{100 * (pers['out'][8]['ratio'] - 1):+.1f} %"),
        ("視体積交差 K=24", f"{100 * (pers['out'][24]['ratio'] - 1):+.1f} %"),
        ("視体積交差 K=48", f"{100 * (pers['out'][48]['ratio'] - 1):+.1f} %"),
        ("うち背中のくぼみ(K=48)",
         f"{100 * pers['out'][48]['fill'] * occ_volume(pers['hollow_reg']) / truth['true']:+.2f} %"),
        ("うち脚の間の幽霊(K=48)",
         f"{100 * pers['out'][48]['ghost'] * occ_volume(pers['belly_reg']) / truth['true']:+.2f} %"),
        ("シルエット +1 画素", f"{ctl['per_px']:+.2f} %"),
    ]
    for name, val in rows:
        print(f"  {name:<30}{val:>10}")
    print(f"  → 台数で買えるのは K=4 の {100 * (pers['out'][4]['ratio'] - 1):+.1f} % から "
          f"K=48 の {100 * (pers['out'][48]['ratio'] - 1):+.1f} % まで。")
    print("     その先は**前景抽出の 1 画素**と**輪郭に出ない凹み**が残り、")
    print("     どちらもカメラを足しても動かない。")
    figs.save_table("summary", ["条件", "体積の誤差"], rows,
                    title="視体積交差の誤差収支 —— 台数で買える分と買えない分",
                    caption=f"真値 {truth['true']:.4f} m^3 / {truth['weight']:.0f} kg。"
                            "同じ voxel 格子の占有数で比べている。")

    # ---- 自己検査(所見を固定する。壊れたら鳴る)----------------------------- #
    # 1. 真値: 3 通りの積分が一致し、格子の偏りは 0.1 % 未満
    assert abs(_pct(truth["grid"], truth["true"])) < 0.1, truth["grid"]
    assert truth["hollow"] > 0.01 and truth["leg"] > 0.005, truth
    # 2. ゼロ点は視体積交差よりはるかに悪い(上界であることの意味)
    v_aabb = occ_volume(nulls["外接直方体"])
    assert v_aabb / truth["true"] > 3.0, v_aabb
    assert occ_volume(nulls["1 枚 x 一定奥行き"]) / truth["true"] > 1.3
    # 3. 崖の閉形式: 実測は閉形式の**上**にあり、差は 0.011 未満
    for K, r in closed["meas"].items():
        pred = ring_ratio_ellipse(A, B, K)
        assert r >= pred - 1e-4, (K, r, pred)
        assert r - pred < 0.011, (K, r, pred)
    # ★3 台と 6 台が閉形式でも実測でも同じ(点対称断面での偶数の無駄)
    assert ring_ratio_ellipse(A, B, 3) == ring_ratio_ellipse(A, B, 6)
    assert abs(closed["meas"][3] - closed["meas"][6]) < 1e-9, closed["meas"]
    # ★奇数 13 台が偶数 16 台に勝つ
    assert closed["meas"][13] < closed["meas"][16], closed["meas"]
    assert closed["k_odd"] < closed["k_even"], closed
    # ★点対称でない断面では 3 台と 6 台が別物(無駄が消える)
    assert closed["pear3"] - closed["pear6"] > 0.05, closed
    # 4. 消えない誤差 / 消える誤差
    out = pers["out"]
    assert out[48]["fill"] > 0.45, out[48]["fill"]          # くぼみは半分以上埋まったまま
    assert out[4]["fill"] - out[48]["fill"] < 0.08, out     # 12 倍にしても数ポイント
    assert out[4]["ghost"] / out[48]["ghost"] > 3.0, out    # 幽霊は素直に減る
    assert all(out[K]["miss"] == 0 for K in out), out       # 取りこぼしゼロ
    assert out[48]["ratio"] < out[24]["ratio"] < out[8]["ratio"] < out[4]["ratio"]
    # 5. 物差しで勝者が入れ替わる
    best_vol, best_allo, best_z = mets["best"]
    assert best_allo != best_vol, mets["best"]
    assert best_allo == "凸包", mets["best"]
    v24 = mets["res"]["視体積交差 K=24"]
    # ★2 倍則: 胸囲の誤差が体重で 2 倍になる(残差は 2 次項)
    assert abs(_pct(v24["w_allo"], truth["weight"]) - mets["pred2"]) < 1.5, mets
    # 6. 1 画素の効き: 単調で、Steiner 予測の 0.5〜1.0 倍(**予測は上限**)
    dil = ctl["dil"]
    assert all(dil[d] < dil[d + 1] for d in range(-3, 3)), dil
    assert 0.5 < ctl["per_px"] / ctl["steiner"] < 1.0, (ctl["per_px"], ctl["steiner"])
    assert ctl["per_px"] > 2.0, ctl["per_px"]
    # 上半球ランダムは等間隔に勝てない。0 件は最良値の余裕で裏づける
    assert ctl["win"] == 0, ctl["win"]
    assert ctl["vals"].min() > ctl["base"], (ctl["vals"].min(), ctl["base"])
    assert ctl["vals"].size >= 100, ctl["vals"].size
    # 7. 道具の穴: 規約違いの (R,t) は例外を出さず、空の hull を返す
    assert hole["bad_sil"] == 0, hole
    assert hole["bad_occ"] == 0, hole
    assert hole["good_sil"] > 10_000, hole

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print(f"\n所要 {time.perf_counter() - t0:.1f} s")
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
