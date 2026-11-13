# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""置かれたタオルの角・辺・折り線を、古典の画像処理だけで見つける(合成の描画。真値は描画側が持つ)。

Corners, sides and fold creases of a towel lying on a table, found with classical image processing only (a rendered,
synthetic scene; the truth lives on the renderer's side).

    py -3.11 examples/poc_cloth_towel_corners_synth.py

``CI`` では分岐しない(縮小モードは無い。常に同じ全量を走らせる、約 2.5 分)。``FULLSEYE_FIGURES=off`` で図の書き出しだけ止められる。
(実行時間: 描画が 1 枚約 0.16 秒で 1 条件 20 枚 x 20 条件を描くのが大半。種の本数は減らさない。)

【この PoC が答える問題】
洗濯物を畳むロボットの前段は「置かれた布のどこをつかむか」で、2024 年の公開ベンチでは古典の手作り手法が上位に入った
(ICRA 2024 Cloth Competition の報告)。この PoC は、**ほぼ平らに置かれた 1 枚の長方形のタオル**
(広げたまま / 半分に折る / 3 分の 1 を折り返す / 四つ折り)に範囲を絞り、角の位置・辺の向き・折り線・つかむ隅の順位が、
学習なしでどこまで出て、どの条件(台とのコントラスト・しわ・折り方・照明の方位)で、どの方法が壊れるかを、真値つきで数える。
重なり・しわくちゃ・服の形は扱わない(届かない)。**主張は隅の誤差(中央値と 90 % 点 [mm])を主にする**。再現率(5 mm 以内)は
補助の数: 重心から最も遠い 4 点という粗い基準線でも再現率は 0.94 に届き、方法の差は誤差のほうによく出る。

【描画の選択と理由】
MuJoCo の布(flex)は使わず、**自前の幾何**で描いた。理由: 試作(MuJoCo 3.10.0)では布が台を 1.5〜6 cm 貫通した。
今回さらに 3 通りの接触設定(solref/solimp/margin、self-collide 無し)で試したが、1 つは発散(NaN)、1 つは最小 z が −1.3 cm、
1 つは頂点が ±数十 m に飛び、直らなかった。貫通した絵は使わないと決めたので、貫通の無い構成を取った。
自前の幾何: 矩形の布を凸多角形の板の積み重ねとして 0〜2 回折る(折り線で鏡映、折った側が上、辺ごとに「折り目か切り口か」の旗を持つ)。
上から見たカメラ(1 画素 = 台の面で 1.00 mm、高さによる視差あり)で、厚み(1 層 2.5 mm)・しわ(解析的な平面波の和で高さと面内のずれ)・
布地の模様(縞・織り・裾の縫い目)・台の模様(木目と継ぎ目、または石目)・影・光学のぼけ・雑音を描く。折り目の縁は丸く(立ち上がり 4 mm)、切り口の縁は鋭い(1 mm)。
**真値は描画側**: 真の隅は、折りたたんだ座標の隅を、しわの面内のずれを戻した実位置にして、**隅の高さで**画素へ投影した点。
検出器は画像だけを受け取り、真値は採点でしか使わない(真値を 20 mm 平行移動した偽の真値で採点すると再現率 0、門)。
データは全部自作で、外部データは使っていない(ICRA 2024 のデータなどは権利が未確認なので使わない)。
**真値の高さの定義が 1 mm 前後の比較を左右する**: 隅の高さ(1〜4 層で 2.5〜10 mm)で投影した真値が本線。台の面で投影した真値で測ると
誤差の中央値は 提案(RGB)1.20・提案(色度)1.33・最小外接長方形 1.26・同(色度)2.24 mm になり、提案(RGB)と最小外接長方形の順位が入れ替わる
(差 −0.06 mm、10 組で −0.20〜−0.01)。つかむのは布の上面の隅なので隅の高さを本線にしたが、1 mm 前後の差は真値の定義の関数。

【描画に入れた仮定(結果の読み方に効く)】
* 照明は灰色の拡散光で、陰影は**反射率に定数を掛けるだけ**(色度は変わらない)。鏡面反射・色つきの影・レンズ歪みは無い。
* 布は**裾の縫い目**(切り口から 8 mm 内側の暗い細線)を持つ。折り目の辺には無い。私が描画に入れた手がかりで、実物のタオルが同じ位置・濃さで持つかは未確認。
* 折りは軸に平行な 3 通りと広げたままだけ。しわは高さと面内のずれだけで、折り返し・重なり・端のめくれは無い。台は平ら。
* 台の平均色をタオルの平均色(コントラスト 0)から濃い茶(1)へ寄せてコントラストを振る(ΔE = 両者の平均色の CIE Lab 距離)。

【方法(Fullseye の op が主役、新 op なし)】
* 領域: 画像の外周 10 px の中央値(=台の色)からの距離を ``gaussian``(σ = 0.3 + 2.7 a、a = 0.5 で 1.65 px)で平滑化 → ``otsu`` → ``fill_up`` → 最大の連結成分。
  距離は RGB(明るさを含む)と色度(明るさを捨てる)の 2 通り。
* 輪郭と辺: ``sk_find_contours`` で副画素の等値線(つまみ a は等値線の値でなく level = 0.2 + 0.5 a。届く範囲 0.2〜0.7 の外の値は画像の倍率で合わせる)
  → ``xg_gen_polygons``(Douglas-Peucker)→ 各辺を全最小二乗の直線にし、隣り合う直線の交点を隅とする(角の丸まりを避ける)。辺の長さと角度で棄却する。
* 提案 = 上の全体(長方形を仮定しない一般の多角形)。**基準線**は、``sk_corner_harris`` の極大を真の隅の数だけ(領域を使わない)、
  同じ領域の凸包の頂点を 4 個まで減らしたもの、領域の重心から最も遠い 4 点、同じ領域に外接する面積最小の長方形(長方形という前提を使う。RGB と色度の 2 通り)。
  比較実験として「交点を取らず多角形の頂点をそのまま隅にした版」(色度)も置いた。基準線は検出数を真の隅の数(4)に固定でき、提案より有利な設定。
* つかむ隅の順位: 隅の両側の辺の「裾の線の深さ」(辺から 8 mm 内側の暗い線)の小さい方を得点にする。両側とも切り口なら高い。
  もう一つの手がかり(折り目の丸みの陰影の帯の幅)も測った。
* 採点: 検出と真の隅を割り当て問題で 1 対 1 に組み、15 mm 以内で組めたものの誤差を数え、5 mm 以内を「見つかった」とする。種 20 本 x 条件ごとに、
  種ごとの再現率の平均と 95 % 区間(種の復元抽出)を出す。**1 つの種の値を主張にしない**。

【結果】主な数値は種 0〜19 の 1 組(実行ログの値)。[ ] は種の組を 10 組(種 0〜19 に 1000 の倍数を足した組)にしたときの最小〜最大。
条件の既定: 4 折り方 x 20 種 = 80 枚、ΔE 69、しわ 1 mm、照明の方位 90 度。
* 隅の誤差の中央値 mm [10 組の範囲] / 90 % 点 / 再現率:
    提案(色度)          1.08 [0.96, 1.08] / 1.98 / 0.997 [0.981, 1.000]
    最小外接長方形(RGB) 1.14 [1.02, 1.15] / 2.01 / 1.000
    提案(RGB)           1.55 [1.45, 1.67] / 3.00 [2.82, 3.04] / 0.991 [0.956, 0.994]
    最小外接長方形(色度) 1.66 [1.49, 1.66] / 2.53 / 1.000
    多角形の頂点のまま(色度) 1.94 [1.91, 2.04] / 3.11 / 0.994
    重心から最遠の 4 点   3.20 [3.2, 3.4] / 4.78 / 0.944 [0.912, 0.963]
    Harris のみ          3.62 [3.57, 3.69] / 4.78 / 0.919 [0.878, 0.934]
    凸包の頂点のみ       4.16 [4.04, 4.37] / 7.43 / 0.647 [0.634, 0.681]
  辺の向きの誤差は中央値 0.16 度(90 % 点 0.81 度)。折り線(80 本)は全部当たるが、**折り線は外周の辺なので辺が出れば当たる**
  (検出した辺のうち折り線は 0.333)。折り線と切り口の区別は辺の位置ではつかず、下の裾の線で行う。
* **基準線との勝ち負け**(きれいな条件、誤差の中央値): 最小外接長方形(RGB)は提案(RGB)に勝つ(差 +0.41 mm、10 組で +0.41〜+0.53)。
  提案(色度)は最小外接長方形(RGB)と同等〜わずかに良い(差 −0.06 mm、10 組で −0.15〜+0.00 = 負けない)。提案が長方形を仮定しない利点は、
  この PoC の折り方がすべて長方形なので使われていない。
* **壊れる値の表**(再現率が 0.9 に届く最低の ΔE / 0.9 を下回る最初のしわの振幅。種 0〜19 の値、[ ] は 10 組の範囲):
    方法                  ΔE            しわ
    提案(RGB)            46 [45, 59]    2 mm [2, 3]
    提案(色度)           32 [30, 34]    3 mm [3, 4]
    最小外接長方形(RGB)   46 [44, 48]    3 mm [3, 4]
    最小外接長方形(色度)  32 [30, 34]    3 mm [3, 3]
    Harris のみ          57 [56, 72]    2 mm [2, 2]
  「ΔE 39 未満で壊れる」のように 1 つの値で言えるのは方法ごとで、方法で違う(色度の距離は 32、RGB の距離は 46)。
* コントラスト(再現率、ΔE 0 / 19 / 32): 提案(RGB)0.15 / 0.21 / 0.57、提案(色度)0.00 / 0.59 / 1.00、最小外接長方形(RGB)0.12 / 0.19 / 0.39、
  同(色度)0.00 / 0.59 / 1.00、Harris 0.61 / 0.55 / 0.62。**全滅するのは ΔE 0**(領域の方法はどれも 0.15 以下で、領域を使わない Harris が最良)。
  ΔE 19 は色度の領域の方法と Harris が同程度で、種の組で大きくぶれる(色度の提案は 10 組で 0.35〜0.88)。
* しわ(再現率、しわ 3 mm / 4 mm。種 0〜19 の値、[ ] は 10 組の平均): 提案(RGB)0.50 / 0.30 [0.55 / 0.29]、提案(色度)0.80 / 0.68 [0.87 / 0.66]、
  最小外接長方形(RGB)0.82 / 0.55 [0.85 / 0.58]、同(色度)0.70 / 0.46 [0.73 / 0.46]、Harris 0.51 / 0.33 [0.51 / 0.30]、
  多角形の頂点のまま(色度)0.90 / 0.84 [0.90 / 0.78]。**しわが強いと提案(RGB)は Harris と同程度かそれ以下**(4 mm で 0.30 対 0.33)で、
  最小外接長方形(RGB)のほうがはるかに良い(0.55)。誤差の中央値は提案(色度)が 0 mm で 0.51 mm、4 mm で 3.22 mm。
  照明の方位(4 通り、ΔE 46): 提案(色度)は 0.97〜1.00、提案(RGB)は 0.90〜0.96 で、**20 本では方位の効果は見えなかった**(1 条件 4 点だけ)。
* つかむ隅の順位(折った 3 種 x 20 種、偶然 0.417): 得点が最上位の検出が開いた隅に当たる割合は 提案(RGB)0.917 [10 組で 0.83〜0.93]、提案(色度)0.950 [0.95〜1.00]、
  Harris 0.483、重心から最遠の 4 点 0.367、凸包 0.400、最小外接長方形 0.317(順位を持たない)。
  裾の縫い目を描かない対照(10 組を合わせた値): 提案(RGB)0.349、提案(色度)0.547(偶然 0.417)。
  辺が切り口かの AUC は裾の線の深さで 0.917 [0.917, 0.977]、折り目の丸みの陰影の帯で 0.590 [0.505, 0.608](期待した手がかりはほとんど効かなかった)。

【確認実験で支持されたこと / されなかったこと】
* 支持: 色度に替えると再現率が上がるのは**陰影(明るさ)がしわで乱れるとき**。増分は しわ 0 mm で +0.013 [+0.000, +0.037](10 組の平均 −0.005)、
  3 mm で +0.300 [+0.125, +0.463](同 +0.316)、4 mm で +0.375(同 +0.365)(用量反応)。ただし描画の陰影が反射率の定数倍なので、
  色度が陰影に不変なのは構成上のこと。色つきの影や鏡面のある実画像で同じとは言えない。
* 支持: 順位の手がかりは裾の縫い目(裾を描かないと提案(RGB)は 0.917 → 0.349)。
* 手がかり(原因の確認ではない): 交点を取らず多角形の頂点をそのまま隅にした版は、しわ 0 mm では悪く(誤差の中央値 2.4 mm、交点は 0.5 mm。10 組の平均)、
  しわ 4 mm では交点より良い(2.6 mm 対 3.3 mm。10 組の平均。再現率は +0.163 [+0.050, +0.300]、10 組の平均 +0.119)。しわで落ちる原因の一部が「直線の当てはめ」にあることを
  示唆するが、当てはめを替えて原因を切り分ける実験はしていない。
* **支持されなかった / 未特定**: 裾なしで提案(色度)が偶然より高い(+0.13、10 組の平均)理由。「漏れは見つからなかった(独立レビューで確認)」が、
  小さな偏りが残る。低コントラストで領域が壊れる理由を「陰影」と言い切る実験もしていない(IoU の低下は数えた)。

【門(179 本、実測の近くに帯)】
折りの幾何(層・折り目・開いた隅の数、領域の面積 / 真の隅の四角形の面積 0.995〜0.999)、方法ごとの誤差と再現率、基準線との差、
壊れる値の表、コントラスト・しわ・方位の条件ごとの再現率、辺の向き、折り線、順位と対照、確認実験、20 mm ずらした真値で 0。
帯の決め方は ``BANDS`` の上のコメント(種の組 8 つの最小・最大に幅 1 倍を足し、決定に使わない 2 組で全部通ることを確認)。
門の変異(わざと壊す)はこの repo の外で走らせた(独立レビューの 7 変異もすべて落ちた)。

    EXTEND: 実画像に替えるには ``evaluate`` の ``render_scene`` を撮った画像に替え、真値(隅)を人手の注釈にする。mm への換算は台の面での画素の大きさ。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import scipy.ndimage as ndi  # noqa: E402
from scipy.optimize import linear_sum_assignment  # noqa: E402
from scipy.spatial import ConvexHull  # noqa: E402

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

SHAPE = (480, 640)
F_PX = 700.0                       # 焦点距離 [px]
HC = 700.0                         # 台からカメラまで [mm]。台の面で 1 画素 = HC/F = 1.0 mm
CX, CY = 319.5, 239.5
W_T, L_T = 260.0, 180.0            # 広げたタオル(x が幅、y が長さ) [mm]
LAYER = 2.5                        # 1 層の厚み [mm]
W_RAW, W_CREASE = 1.0, 4.0         # 縁の立ち上がりの幅 [mm]: 切り口の縁は鋭く、折り目は丸い
AMBIENT = 0.35
ELEV = np.radians(50.0)            # 照明の高度
BLUR_PX = 0.8
SENSOR_NOISE = 0.01
FOLD_PLANS = {"flat": [], "half": [("y", 0.0)], "third": [("y", L_T / 6)], "quarter": [("y", 0.0), ("x", 0.0)]}


# ---------------------------------------------------------------------------------------------- 折り(凸多角形の積み重ね)
def _clip(V, flags, n, d):
    """凸多角形(反時計回り)を n·p - d >= 0 の側で切る。各辺の「折り目か」の旗も引き継ぐ(切り口は折り目)。"""
    out_v, out_f = [], []
    m = len(V)
    s = V @ n - d
    for i in range(m):
        a, b = V[i], V[(i + 1) % m]
        sa, sb = s[i], s[(i + 1) % m]
        if sa >= 0:
            out_v.append(a)
            out_f.append(flags[i])
            if sb < 0:
                t = sa / (sa - sb)
                out_v.append(a + t * (b - a))
                out_f.append(True)
        elif sb >= 0:
            t = sa / (sa - sb)
            out_v.append(a + t * (b - a))
            out_f.append(flags[i])
    if len(out_v) < 3:
        return None
    V2 = np.array(out_v)
    if abs(_area(V2)) < 1e-6:
        return None
    return V2, out_f


def _area(V):
    x, y = V[:, 0], V[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def fold_stack(plan):
    """矩形のタオルを plan の順に折る。返り値は 下から上の順の板の列 と 折り目の線分の列。

    板 = {V: 頂点(反時計回り), flags: 各辺が折り目か, M: 今の座標 → 広げた座標の 3x3, back: 裏返っているか}。
    """
    V = np.array([[-W_T / 2, -L_T / 2], [W_T / 2, -L_T / 2], [W_T / 2, L_T / 2], [-W_T / 2, L_T / 2]])
    sheets = [{"V": V, "flags": [False] * 4, "M": np.eye(3), "back": False}]
    creases = []
    for axis, pos in plan:
        n = np.array([0.0, 1.0]) if axis == "y" else np.array([1.0, 0.0])
        R = np.eye(3)                                      # 反射: p -> p - 2 (n·p - pos) n
        R[:2, :2] = np.eye(2) - 2 * np.outer(n, n)
        R[:2, 2] = 2 * pos * n
        keep, flip = [], []
        for sh in sheets:
            k = _clip(sh["V"], sh["flags"], -n, -pos)       # n·p <= pos の側(残る側)
            if k is not None:
                keep.append({"V": k[0], "flags": k[1], "M": sh["M"], "back": sh["back"]})
            f = _clip(sh["V"], sh["flags"], n, pos)         # n·p >= pos の側(折り返す側)
            if f is not None:
                Vr = (f[0] @ R[:2, :2].T + R[:2, 2])[::-1]  # 反射で向きが逆になるので並べ直す
                fl = list(f[1])
                fl = [fl[(len(fl) - 2 - j) % len(fl)] for j in range(len(fl))]
                flip.append({"V": Vr, "flags": fl, "M": sh["M"] @ R, "back": not sh["back"]})
        # 新しい折り目: 残る板が折り線の上に持つ頂点の端から端まで
        on = np.concatenate([sh["V"][np.abs(sh["V"] @ n - pos) < 1e-7] for sh in keep])
        t_dir = np.array([1.0, 0.0]) if axis == "y" else np.array([0.0, 1.0])
        ts = on @ t_dir
        p0 = pos * n + ts.min() * t_dir
        p1 = pos * n + ts.max() * t_dir
        new = []
        for a, b in creases:                                # 既存の折り目も同じに切って折り返す
            for side in (-1, 1):
                sa, sb = side * (a @ n - pos), side * (b @ n - pos)
                if sa < -1e-9 and sb < -1e-9:
                    continue
                if sa < -1e-9 or sb < -1e-9:
                    t = sa / (sa - sb)
                    c = a + t * (b - a)
                    a2, b2 = (c, b) if sa < 0 else (a, c)
                else:
                    a2, b2 = a, b
                if side == 1:
                    a2, b2 = R[:2, :2] @ a2 + R[:2, 2], R[:2, :2] @ b2 + R[:2, 2]
                new.append((a2, b2))
        new.append((p0, p1))
        # 重複(折り返して重なった同じ線分)を除く
        uniq = []
        for a, b in new:
            if not any((np.allclose(a, c) and np.allclose(b, d)) or (np.allclose(a, d) and np.allclose(b, c))
                       for c, d in uniq):
                uniq.append((a, b))
        creases = uniq
        sheets = keep + flip[::-1]                          # 積みを折り返すと順序が逆になって上に載る
    return sheets, creases


def count_layers(sheets, p, eps=1e-6):
    """点 p(折りたたんだ座標)を閉包に含む板の数。"""
    n = 0
    for sh in sheets:
        V = sh["V"]
        e = np.roll(V, -1, axis=0) - V
        d = (e[:, 0] * (p[1] - V[:, 1]) - e[:, 1] * (p[0] - V[:, 0])) / np.linalg.norm(e, axis=1)
        n += int(np.all(d >= -eps))
    return n


# ---------------------------------------------------------------------------------------------- しわ(解析的な波の和)
class Waves:
    """ランダムな平面波の和。どこでも値を返せるので、真値の隅も描画と同じ場から取れる。"""

    def __init__(self, rng, n=14, lam=(14.0, 60.0)):
        ang = rng.uniform(0, 2 * np.pi, n)
        lamb = rng.uniform(*lam, n)
        self.k = np.stack([np.cos(ang), np.sin(ang)], axis=1) * (2 * np.pi / lamb)[:, None]
        self.ph = rng.uniform(0, 2 * np.pi, n)
        self.a = rng.normal(size=n)
        self.a /= np.sqrt(np.sum(self.a ** 2) / 2.0)        # 値の標準偏差 1

    def __call__(self, x, y):
        out = np.zeros_like(x, dtype=float)
        for k, ph, a in zip(self.k, self.ph, self.a):
            out += a * np.cos(k[0] * x + k[1] * y + ph)
        return out

    def grad(self, x, y):
        gx = np.zeros_like(x, dtype=float)
        gy = np.zeros_like(x, dtype=float)
        for k, ph, a in zip(self.k, self.ph, self.a):
            s = -a * np.sin(k[0] * x + k[1] * y + ph)
            gx += s * k[0]
            gy += s * k[1]
        return gx, gy


def srgb_to_lab(rgb):
    rgb = np.asarray(rgb, float)
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def _smooth_step(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def render_scene(seed, fold="half", contrast=1.0, wrinkle=1.0, light_az=60.0, noise=SENSOR_NOISE, shadow=True,
                 hem=True):
    """タオルを台に置いた画像と、描画側が持つ真値。

    contrast: 台の平均色を、タオルの平均色(0)から濃い茶(1)へ寄せる量。wrinkle: しわの振幅 [mm]。
    light_az: 照明の方位 [度](画像の x 軸から)。高度は 50 度。
    """
    rng = np.random.default_rng(10_000 + seed)           # 配置・柄は種だけで決まる(条件を振っても同じ)
    theta = rng.uniform(0, 2 * np.pi)
    centre = rng.uniform(-30, 30, 2)
    hue = rng.uniform(0, 1)
    towel_rgb = np.clip(np.array([0.72, 0.74, 0.78]) + 0.18 * np.array(
        [np.cos(2 * np.pi * hue), np.cos(2 * np.pi * (hue + 1 / 3)), np.cos(2 * np.pi * (hue + 2 / 3))]), 0.1, 0.95)
    table_dark = np.array([0.30, 0.20, 0.12]) * rng.uniform(0.8, 1.2)
    table_rgb = np.clip((1 - contrast) * towel_rgb + contrast * table_dark, 0, 1)
    table_kind = int(rng.integers(0, 2))
    wood_dir = rng.uniform(0, np.pi)
    wood_period = rng.uniform(5.0, 12.0)
    wood_amp = rng.uniform(0.05, 0.09)
    seam_off = rng.uniform(0, 90.0)
    wr_h = Waves(rng, 8, (14, 60))
    wr_u = Waves(rng, 8, (14, 60))
    wr_v = Waves(rng, 8, (14, 60))
    r2 = np.random.default_rng(int(rng.integers(0, 2 ** 31)))
    r3 = np.random.default_rng(int(rng.integers(0, 2 ** 31)))
    sheets, creases = fold_stack(FOLD_PLANS[fold])
    c, s = np.cos(theta), np.sin(theta)

    def to_fold(xw, yw):                                  # 台 -> 折りたたんだ座標
        dx, dy = xw - centre[0], yw - centre[1]
        return c * dx + s * dy, -s * dx + c * dy

    def from_fold(qx, qy):
        return c * qx - s * qy + centre[0], s * qx + c * qy + centre[1]

    def disp(qx, qy):                                     # しわの面内のずれ [mm]
        return 0.5 * wrinkle * wr_u(qx, qy), 0.5 * wrinkle * wr_v(qx, qy)

    # タオルの周りの窓だけで層・高さ・色を計算する(全画面だと波の和が遅い)
    half = int(np.hypot(W_T, L_T) / 2 + 14)
    r_c = int(round(CY + F_PX * centre[1] / HC))
    c_c = int(round(CX + F_PX * centre[0] / HC))
    r0, r1 = max(r_c - half, 0), min(r_c + half + 1, SHAPE[0])
    c0, c1 = max(c_c - half, 0), min(c_c + half + 1, SHAPE[1])
    RS = (r1 - r0, c1 - c0)
    v_, u_ = np.mgrid[r0:r1, c0:c1].astype(float)
    ux, uy = (u_ - CX) / F_PX, (v_ - CY) / F_PX

    def cover(h):
        xw, yw = ux * (HC - h), uy * (HC - h)
        qx, qy = to_fold(xw, yw)
        dx, dy = disp(qx, qy)
        qx, qy = qx + dx, qy + dy
        covs = []
        for sh in sheets:
            V = sh["V"]
            m = len(V)
            cv = np.ones(RS)
            for i in range(m):
                a, b = V[i], V[(i + 1) % m]
                e = b - a
                d = (e[0] * (qy - a[1]) - e[1] * (qx - a[0])) / np.hypot(*e)
                w = W_CREASE if sh["flags"][i] else W_RAW
                cv = np.minimum(cv, _smooth_step(0.5 + d / w))
            covs.append(cv)
        return covs, qx, qy

    covs, qx, qy = cover(np.zeros(RS))
    tot = np.sum(covs, axis=0)
    h0 = LAYER * tot + wrinkle * wr_h(qx, qy) * np.minimum(tot, 1.0)
    covs, qx, qy = cover(h0)
    tot = np.sum(covs, axis=0)
    h = LAYER * tot + wrinkle * wr_h(qx, qy) * np.minimum(tot, 1.0)
    pitch = (HC - h) / F_PX
    hgy, hgx = np.gradient(h)
    gx, gy = hgx / pitch, hgy / pitch                     # 画素の (x, y) は台の座標と同じ向き
    nrm = np.sqrt(gx ** 2 + gy ** 2 + 1.0)
    Ld = np.array([np.cos(np.radians(light_az)) * np.cos(ELEV), np.sin(np.radians(light_az)) * np.cos(ELEV),
                   np.sin(ELEV)])
    shade_roi = AMBIENT + (1 - AMBIENT) * np.maximum(0.0, (-gx * Ld[0] - gy * Ld[1] + Ld[2]) / nrm) / np.sin(ELEV)

    top = np.full(RS, -1, int)                            # 上にある板(添字が大きい)の色を取る
    for i, cv in enumerate(covs):
        top[cv > 0.5] = i
    albedo_t = np.zeros(RS + (3,))
    for i, sh in enumerate(sheets):
        sel = top == i
        if not sel.any():
            continue
        Mx = sh["M"]
        X = Mx[0, 0] * qx + Mx[0, 1] * qy + Mx[0, 2]
        Y = Mx[1, 0] * qx + Mx[1, 1] * qy + Mx[1, 2]
        col = np.ones(RS + (3,)) * towel_rgb
        band = (np.abs(np.abs(Y) - (L_T / 2 - 32)) < 3.5) | (np.abs(np.abs(Y) - (L_T / 2 - 20)) < 1.5)
        col = np.where(band[..., None], towel_rgb * np.array([0.62, 0.70, 0.85]), col)
        hem_line = (np.abs(np.abs(X) - (W_T / 2 - 8)) < 0.6) | (np.abs(np.abs(Y) - (L_T / 2 - 8)) < 0.6)
        col = np.where(hem_line[..., None] & hem, col * 0.86, col)
        weave = 0.025 * np.sin(2 * np.pi * X / 1.6) * np.sin(2 * np.pi * Y / 1.6)
        col = col * (1 + weave[..., None]) * (0.97 if sh["back"] else 1.0)
        albedo_t[sel] = col[sel]

    # 全画面: 台の柄(画像の空間で作る。台の柄は真値に関係しない)
    V_, U_ = np.mgrid[0:SHAPE[0], 0:SHAPE[1]].astype(float)
    xt, yt = (U_ - CX) / F_PX * HC, (V_ - CY) / F_PX * HC
    warp = ndi.gaussian_filter(r2.normal(size=SHAPE), 30.0) * 30.0 * 4.0
    if table_kind == 0:                                   # 木目と板の継ぎ目
        ph = (np.cos(wood_dir) * xt + np.sin(wood_dir) * yt) / wood_period + warp
        pat = wood_amp * np.sin(2 * np.pi * ph)
        seam = np.abs(((xt + seam_off + 45.0) % 90.0) - 45.0)
        pat -= 0.22 * (seam < 0.8)
    else:                                                 # 石目: 細かい斑 + 大きな濃淡
        pat = 0.3 * ndi.gaussian_filter(r2.normal(size=SHAPE), 1.2) + 0.5 * warp / 4.0
        pat -= 0.18 * (np.abs(((yt + seam_off) % 120.0) - 60.0) > 59.2)
    img = np.clip(table_rgb * (1 + pat[..., None]), 0, 1)
    tot_full = np.zeros(SHAPE)
    top_full = np.full(SHAPE, -1, int)
    h_full = np.zeros(SHAPE)
    tot_full[r0:r1, c0:c1] = tot
    top_full[r0:r1, c0:c1] = top
    h_full[r0:r1, c0:c1] = h
    sl = (slice(r0, r1), slice(c0, c1))
    img[sl] = np.where((top >= 0)[..., None], albedo_t, img[sl])
    shade = np.ones(SHAPE)
    shade[sl] = shade_roi
    img = img * shade[..., None]
    if shadow:                                            # 台に落ちる影: 最上層の高さ分だけ光と反対へずらす
        hm = LAYER * max(count_layers(sheets, np.zeros(2)), 1)
        off = hm / np.tan(ELEV) / (HC / F_PX)
        sh_map = ndi.shift((tot_full > 0.5).astype(float), (-np.sin(np.radians(light_az)) * off,
                                                            -np.cos(np.radians(light_az)) * off),
                           order=1, mode="constant")
        sh_map = ndi.gaussian_filter(sh_map, 1.5)
        k = 1 - 0.5 * np.clip(sh_map, 0, 1) * (top_full < 0)
        img = img * k[..., None]
    img = ndi.gaussian_filter(img, (BLUR_PX, BLUR_PX, 0))
    img = np.clip(img + noise * r3.normal(size=img.shape), 0.0, 1.0)

    # 真値: 折りたたんだ座標の隅 -> 実際の位置(しわの面内ずれを戻す)-> 画素
    allv = np.concatenate([sh["V"] for sh in sheets])
    x0, x1 = allv[:, 0].min(), allv[:, 0].max()
    y0, y1 = allv[:, 1].min(), allv[:, 1].max()
    corners_fold = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])

    def world_px(qrest, z):
        q = np.array(qrest, float)
        for _ in range(8):                                # x + u(x) = q の解(不動点)
            dx, dy = disp(np.array([q[0]]), np.array([q[1]]))
            q2 = np.array(qrest, float) - np.array([dx[0], dy[0]])
            if np.allclose(q2, q, atol=1e-9):
                break
            q = q2
        xw, yw = from_fold(q[0], q[1])
        return np.array([CY + F_PX * yw / (HC - z), CX + F_PX * xw / (HC - z)]), np.array([xw, yw, z])

    corners_px, corners_mm, nlay, z_c = [], [], [], []
    for p in corners_fold:
        nl = count_layers(sheets, p)
        z = LAYER * nl + float(wrinkle * wr_h(np.array([p[0]]), np.array([p[1]]))[0])
        px, w3 = world_px(p, z)
        corners_px.append(px)
        corners_mm.append(w3)
        nlay.append(nl)
        z_c.append(z)
    open_c = []
    for p in corners_fold:
        on = False
        for a, b in creases:
            e = b - a
            dd = abs(e[0] * (p[1] - a[1]) - e[1] * (p[0] - a[0])) / np.hypot(*e)
            t = (p - a) @ e / (e @ e)
            on = on or (dd < 1e-6 and -1e-6 <= t <= 1 + 1e-6)
        open_c.append(not on)
    cre = []
    for a, b in creases:
        z = LAYER * max(count_layers(sheets, 0.5 * (a + b)), 1)
        cre.append((world_px(a, z)[0], world_px(b, z)[0]))
    truth = {"corners_px": np.array(corners_px), "corners_mm": np.array(corners_mm), "layers": np.array(nlay),
             "open": np.array(open_c), "creases_px": cre, "cover": tot_full > 0.5, "top": top_full,
             "height": h_full, "mm_per_px": float((HC - float(np.mean(z_c))) / F_PX),
             "contrast_dE": float(np.linalg.norm(srgb_to_lab(towel_rgb) - srgb_to_lab(table_rgb))), "fold": fold}
    return img, truth




# ---------------------------------------------------------------------------------------------- 検出(提案と基準線)
def border_median(img, w=10):
    b = np.concatenate([img[:w].reshape(-1, 3), img[-w:].reshape(-1, 3), img[:, :w].reshape(-1, 3),
                        img[:, -w:].reshape(-1, 3)])
    return np.median(b, axis=0)


def segment(img, chroma_only=False, sigma_a=0.5):
    """台の縁の色(画像の外周の中央値)からの距離 → 平滑化 → 大津 → 穴埋め → 最大の連結成分。
    返り値: 距離画像、マスク、等値線のしきい値。"""
    med = border_median(img)
    if chroma_only:                                         # 明るさを捨てた色度の距離(影に強いはずの変種)
        s = img.sum(2, keepdims=True) + 1e-6
        d = np.linalg.norm(img / s - med / med.sum(), axis=2)
    else:
        d = np.linalg.norm(img - med, axis=2)
    ds = np.asarray(fs.apply(d, "gaussian", a=sigma_a))      # σ = 0.3 + 2.7 a(a = 0.5 で 1.65 px)
    ds = ds / max(float(ds.max()), 1e-9)                     # 最大で割る(等値線の op は値の幅に敏感)
    m = np.asarray(fs.apply(ds, "otsu")) > 0.5
    m = np.asarray(fs.apply(m.astype(float), "fill_up")) > 0.5
    lab, n = ndi.label(m)
    if n == 0:
        return ds, m, float(ds.mean())
    sizes = ndi.sum(m, lab, np.arange(1, n + 1))
    m = lab == (1 + int(np.argmax(sizes)))
    lvl = 0.5 * (float(ds[m].mean()) + float(ds[~m].mean()))
    return ds, m, lvl


def _tls_line(P):
    c = P.mean(0)
    u, s, vt = np.linalg.svd(P - c, full_matrices=False)
    return c, vt[0]


def _intersect(c1, d1, c2, d2):
    A = np.array([d1, -d2]).T
    if abs(np.linalg.det(A)) < 1e-6:
        return None
    t = np.linalg.solve(A, c2 - c1)
    return c1 + t[0] * d1


def _turn(a, b, c):
    u, v = b - a, c - b
    return np.degrees(np.abs(np.arctan2(u[0] * v[1] - u[1] * v[0], u @ v)))


def edge_band_energy(lum, c, d, inward, length_px, k=7):
    """辺の内側 0..k px の輝度が、さらに内側(8..14 px)の中央値からどれだけ外れるか(折り目の丸みの帯の幅)。"""
    n = np.array([-d[1], d[0]])
    if n @ inward < 0:
        n = -n
    ts = np.linspace(-0.4, 0.4, 25) * length_px
    pts = c[None, :] + ts[:, None] * d[None, :]
    prof = []
    for off in list(range(0, k + 1)) + list(range(9, 15)):
        q = pts + off * n
        prof.append(ndi.map_coordinates(lum, [q[:, 0], q[:, 1]], order=1, mode="nearest"))
    prof = np.array(prof)
    ref = np.median(prof[k + 1:], axis=0)
    return float(np.mean(np.abs(prof[:k + 1] - ref[None, :])))


def hem_depth(lum, c, d, inward, length_px):
    """辺の内側 8 mm あたりの縫い目(裾の線)の深さ: 辺から 4〜6 px と 10〜12 px の輝度の平均より、7〜9 px の最小がどれだけ暗いか
    (辺に沿って平均した断面で。切り口の辺には裾の線があり、折り目の辺には無い)。"""
    n = np.array([-d[1], d[0]])
    if n @ inward < 0:
        n = -n
    ts = np.linspace(-0.4, 0.4, 25) * length_px
    pts = c[None, :] + ts[:, None] * d[None, :]
    prof = []
    for off in range(0, 17):
        q = pts + off * n
        prof.append(ndi.map_coordinates(lum, [q[:, 0], q[:, 1]], order=1, mode="nearest"))
    prof = np.mean(prof, axis=1)
    ref = 0.5 * (prof[4:7].mean() + prof[10:13].mean())
    return float((ref - prof[7:10].min()) / max(ref, 1e-6))


def detect_proposed(img, chroma_only=False, eps=0.02, min_side=25.0):
    """提案: 領域 → 等値線(副画素)→ Douglas-Peucker → 各辺を全最小二乗の直線 → 隣り合う直線の交点を隅とする。"""
    ds, m, lvl = segment(img, chroma_only=chroma_only)
    out = {"mask": m, "corners": np.zeros((0, 2)), "score": np.zeros(0), "vcorners": np.zeros((0, 2)), "sides": [],
           "ok": False, "ds": ds}
    if m.sum() < 400:
        return out
    # sk_find_contours のつまみ a は等値線の値そのものではない(level = 0.2 + 0.5 a、backends.py)。つまみが届く範囲は
    # 0.2〜0.7 で、低コントラストの等値線(0.19 など)は届かないので、画像を level 0.45(a = 0.5)に対応する倍率で
    # 掛けてから等値線を取る(元の画像の lvl の等値線と同じ)。
    a_lvl = 0.5
    c = fs.apply(np.clip(ds * (0.45 / max(lvl, 1e-6)), 0.0, 1.0), "sk_find_contours", a=a_lvl)
    if not c["cs"]:
        return out
    cont = np.asarray(max(c["cs"], key=len))
    if len(cont) < 20:
        return out
    poly = np.asarray(fs.apply({"shape": c["shape"], "cs": [cont]}, "xg_gen_polygons", a=eps)["cs"][0])
    poly = poly[:-1] if np.allclose(poly[0], poly[-1]) else poly
    # ほぼ直線(曲がりが 25 度未満)の頂点は隅ではない
    for _ in range(3):
        keep = [i for i in range(len(poly)) if _turn(poly[i - 1], poly[i], poly[(i + 1) % len(poly)]) >= 25.0]
        if len(keep) < 3 or len(keep) == len(poly):
            break
        poly = poly[keep]
    if len(poly) < 3:
        return out
    idx = np.array([int(np.argmin(np.sum((cont - p) ** 2, axis=1))) for p in poly])
    order = np.argsort(idx)
    poly, idx = poly[order], idx[order]
    nP, nC = len(poly), len(cont)
    centre = cont.mean(0)
    lum = ndi.gaussian_filter(img.mean(2), 0.7)
    sides = []
    for i in range(nP):
        a, b = idx[i], idx[(i + 1) % nP]
        arc = cont[a:b + 1] if b > a else np.vstack([cont[a:], cont[:b + 1]])
        n_arc = len(arc)
        cut = max(int(0.15 * n_arc), 2)
        core = arc[cut:n_arc - cut] if n_arc - 2 * cut >= 3 else arc
        length = float(np.linalg.norm(poly[(i + 1) % nP] - poly[i]))
        if len(core) < 3:
            sides.append(None)
            continue
        cc, dd = _tls_line(core)
        sides.append({"c": cc, "d": dd, "len": length,
                      "band": edge_band_energy(lum, cc, dd, centre - cc, length),
                      "hem": hem_depth(lum, cc, dd, centre - cc, length)})
    corners, scores, verts = [], [], []
    for i in range(nP):
        s0, s1 = sides[i - 1], sides[i]
        if s0 is None or s1 is None:
            continue
        p = _intersect(s0["c"], s0["d"], s1["c"], s1["d"])
        if p is None:
            continue
        ang = float(np.degrees(np.arccos(np.clip(abs(s0["d"] @ s1["d"]), 0, 1))))
        if ang < 60.0:
            continue
        if s0["len"] < min_side or s1["len"] < min_side:
            continue
        if np.linalg.norm(p - poly[i]) > 12.0:               # 交点が頂点から遠すぎる = 隣の直線がずれている
            continue
        corners.append(p)
        verts.append(poly[i])
        scores.append(min(s0["hem"], s1["hem"]))           # 両側の辺に裾の線がある隅ほど上位(切り口どうしの隅)
    out.update({"corners": np.array(corners).reshape(-1, 2), "score": np.array(scores),
                "vcorners": np.array(verts).reshape(-1, 2),
                "sides": [s for s in sides if s is not None and s["len"] >= 40.0], "ok": len(corners) > 0})
    return out


def _nms_peaks(resp, k, radius):
    r = resp.copy()
    pts, vals = [], []
    for _ in range(k):
        i = np.unravel_index(int(np.argmax(r)), r.shape)
        if r[i] <= 0:
            break
        pts.append(i)
        vals.append(r[i])
        r[max(i[0] - radius, 0):i[0] + radius + 1, max(i[1] - radius, 0):i[1] + radius + 1] = 0
    return np.array(pts, float).reshape(-1, 2), np.array(vals)


def detect_harris(img, k=4):
    """基準線 1: Harris の応答の極大を k 個(領域も辺も使わない)。k は真の隅の数(基準線に有利)。"""
    g = ndi.gaussian_filter(img.mean(2), 1.5)
    resp = np.asarray(fs.apply(g, "sk_corner_harris"))
    pts, vals = _nms_peaks(resp, k, 20)
    return {"corners": pts, "score": vals, "sides": []}


def detect_far(mask, k=4, radius=40):
    """基準線: 領域の輪郭のうち、領域の重心から最も遠い点を k 個(互いに radius px 以上離す)。凸包も多角形も使わない粗い方法。"""
    r, c = np.nonzero(mask & ~ndi.binary_erosion(mask))
    P = np.stack([r, c], 1).astype(float)
    if len(P) < 10:
        return {"corners": np.zeros((0, 2)), "score": np.zeros(0), "sides": []}
    rr, cc = np.nonzero(mask)
    d = np.linalg.norm(P - np.array([rr.mean(), cc.mean()]), axis=1)
    pts, vals = [], []
    for _ in range(k):
        i = int(np.argmax(d))
        if d[i] <= 0:
            break
        pts.append(P[i])
        vals.append(d[i])
        d[np.linalg.norm(P - P[i], axis=1) < radius] = 0
    return {"corners": np.array(pts).reshape(-1, 2), "score": np.array(vals), "sides": []}


def _visvalingam(H, k):
    pts = [p for p in H]
    area = []

    def tri(a, b, c):
        return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))

    pts = list(pts)
    while len(pts) > k:
        ar = [tri(pts[i - 1], pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
        del pts[int(np.argmin(ar))]
    ar = [tri(pts[i - 1], pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    return np.array(pts), np.array(ar)


def detect_hull(mask, k=4):
    """基準線 2: 同じ領域の凸包の頂点を、三角形の面積が小さい順に k 個まで減らす(Visvalingam)。"""
    r, c = np.nonzero(mask & ~ndi.binary_erosion(mask))
    P = np.stack([r, c], 1).astype(float)
    if len(P) < 10:
        return {"corners": np.zeros((0, 2)), "score": np.zeros(0), "sides": []}
    H = P[ConvexHull(P).vertices]
    pts, ar = _visvalingam(H, k)
    return {"corners": pts, "score": ar, "sides": []}


def detect_minrect(mask):
    """基準線 3: 同じ領域の凸包に外接する面積最小の長方形の 4 隅(長方形という前提を使う)。"""
    r, c = np.nonzero(mask & ~ndi.binary_erosion(mask))
    P = np.stack([r, c], 1).astype(float)
    if len(P) < 10:
        return {"corners": np.zeros((0, 2)), "score": np.zeros(0), "sides": []}
    H = P[ConvexHull(P).vertices]
    best = None
    for i in range(len(H)):
        e = H[(i + 1) % len(H)] - H[i]
        e = e / (np.linalg.norm(e) + 1e-12)
        nrm = np.array([-e[1], e[0]])
        a, b = H @ e, H @ nrm
        area = (a.max() - a.min()) * (b.max() - b.min())
        if best is None or area < best[0]:
            best = (area, e, nrm, a.min(), a.max(), b.min(), b.max())
    _, e, nrm, a0, a1, b0, b1 = best
    cs = np.array([a0 * e + b0 * nrm, a1 * e + b0 * nrm, a1 * e + b1 * nrm, a0 * e + b1 * nrm])
    sides = []
    for i in range(4):
        d = cs[(i + 1) % 4] - cs[i]
        sides.append({"c": 0.5 * (cs[i] + cs[(i + 1) % 4]), "d": d / np.linalg.norm(d), "len": float(np.linalg.norm(d))})
    return {"corners": cs, "score": np.zeros(4), "sides": sides}


# ---------------------------------------------------------------------------------------------- 採点(真値と突き合わせる)
def match_corners(det, truth_px, mm, gate_mm=15.0):
    """検出と真の隅を 1 対 1(割り当て問題)で組む。返り値: 真の隅ごとの誤差 [mm](組めなければ nan)と、検出ごとの対応先。"""
    D = np.asarray(det, float).reshape(-1, 2)
    T = np.asarray(truth_px, float)
    err = np.full(len(T), np.nan)
    owner = np.full(len(D), -1)
    if len(D) == 0:
        return err, owner
    C = np.linalg.norm(D[:, None, :] - T[None, :, :], axis=2) * mm
    ri, ci = linear_sum_assignment(np.minimum(C, 1e3))
    for r, c in zip(ri, ci):
        if C[r, c] <= gate_mm:
            err[c] = C[r, c]
            owner[r] = c
    return err, owner


def line_dist_angle(side, a, b):
    """検出した辺の直線と、真の線分(a, b)の中点・向きの差: (角度差 [度]、中点から直線までの距離 [px])。"""
    t = (b - a) / np.linalg.norm(b - a)
    ang = np.degrees(np.arccos(np.clip(abs(side["d"] @ t), 0, 1)))
    mid = 0.5 * (a + b)
    n = np.array([-side["d"][1], side["d"][0]])
    return float(ang), float(abs((mid - side["c"]) @ n))


def truth_sides(truth):
    cp = truth["corners_px"]
    sides = []
    for i in range(4):
        a, b = cp[i], cp[(i + 1) % 4]
        crease = False
        for ca, cb in truth["creases_px"]:
            if min(np.linalg.norm(ca - a) + np.linalg.norm(cb - b), np.linalg.norm(ca - b) + np.linalg.norm(cb - a)) < 1e9:
                mid = 0.5 * (ca + cb)
                t = (b - a) / np.linalg.norm(b - a)
                n = np.array([-t[1], t[0]])
                ang = np.degrees(np.arccos(np.clip(abs(((cb - ca) / np.linalg.norm(cb - ca)) @ t), 0, 1)))
                if ang < 2.0 and abs((mid - a) @ n) < 3.0:
                    crease = True
        sides.append((a, b, crease))
    return sides


METHODS = ("prop", "propc", "harris", "hull", "rect", "rectc")
FOUND_MM = 5.0
GATE_MM = 15.0
GRASP_MM = 8.0
CREASE_ANG, CREASE_MM = 3.0, 4.0


def evaluate(seed, fold="half", contrast=1.0, wrinkle=1.0, light_az=90.0, hem=True):
    """1 枚を描いて、全部の方法を採点した記録を返す。検出器は画像だけを見る(真値は採点でだけ使う)。"""
    img, tr = render_scene(seed, fold=fold, contrast=contrast, wrinkle=wrinkle, light_az=light_az, hem=hem)
    mm = tr["mm_per_px"]
    P = detect_proposed(img)
    Pc = detect_proposed(img, chroma_only=True)
    dets = {"prop": P, "propc": Pc, "propv": {"corners": Pc["vcorners"], "score": Pc["score"], "sides": []},
            "harris": detect_harris(img), "hull": detect_hull(P["mask"]), "far": detect_far(P["mask"]),
            "rect": detect_minrect(P["mask"]), "rectc": detect_minrect(Pc["mask"])}
    rec = {"seed": seed, "fold": fold, "dE": tr["contrast_dE"], "open": tr["open"], "mm_per_px": mm,
           "mask_iou": _iou(P["mask"], tr["cover"]), "mask_iou_c": _iou(Pc["mask"], tr["cover"]),
           "err_table": {}, "found": {}, "err": {}, "ndet": {}, "hit1": {}, "side": {}, "crease": {}, "crease_side": {}}
    sh_dir = np.array([-np.sin(np.radians(light_az)), -np.cos(np.radians(light_az))])    # 影が伸びる向き (row, col)
    for m, d in dets.items():
        err, owner = match_corners(d["corners"], tr["corners_px"], mm, GATE_MM)
        rec["err"][m] = err
        tbl = np.array([[CY + F_PX * y / HC, CX + F_PX * x / HC] for x, y, _ in tr["corners_mm"]])
        rec["err_table"][m] = match_corners(d["corners"], tbl, mm, GATE_MM)[0]
        rec["found"][m] = np.where(np.isfinite(err), err <= FOUND_MM, False)
        rec["ndet"][m] = len(d["corners"])
        # つかむ点: 得点が最上位の検出が、開いた(折り目に触れていない)真の隅の近くか
        if len(d["corners"]):
            top = d["corners"][int(np.argmax(d["score"]))]
            dd = np.linalg.norm(tr["corners_px"] - top, axis=1) * mm
            j = int(np.argmin(dd))
            rec["hit1"][m] = bool(dd[j] <= GRASP_MM and tr["open"][j])
        else:
            rec["hit1"][m] = False
        # 辺の向きの誤差(真の辺のうち最も近い向きとの差)
        ts = truth_sides(tr)
        angs = []
        for s in d["sides"]:
            if s["len"] < 40.0:
                continue
            best = min(line_dist_angle(s, a, b)[0] for a, b, _ in ts)
            angs.append(best)
        rec["side"][m] = angs
        # 折り線: 真の折り目ごとに、角度 3 度・距離 4 mm の内の検出した辺があるか
        hits = []
        for ca, cb in tr["creases_px"]:
            ok = False
            for s in d["sides"]:
                ang, dist = line_dist_angle(s, ca, cb)
                ok = ok or (ang <= CREASE_ANG and dist * mm <= CREASE_MM)
            hits.append(ok)
        rec["crease"][m] = hits
        # 検出した(長い)辺のうち、真の折り目に当たるものの割合を出すための 1 辺ごとの真偽
        rec["crease_side"][m] = [any(line_dist_angle(s, ca, cb)[0] <= CREASE_ANG and line_dist_angle(s, ca, cb)[1] * mm <= CREASE_MM
                                     for ca, cb in tr["creases_px"]) for s in d["sides"] if s["len"] >= 40.0]
    # 影の側へのずれ: 見つかった隅の誤差ベクトルを、影が伸びる向きへ射影した値 [mm]
    rec["shadow_proj"] = {}
    for m in ("prop", "propc"):
        D = dets[m]["corners"]
        proj = []
        if len(D):
            for k, tp in enumerate(tr["corners_px"]):
                dd = np.linalg.norm(D - tp, axis=1) * mm
                i = int(np.argmin(dd))
                if dd[i] <= GATE_MM:
                    proj.append(float(((D[i] - tp) * mm) @ sh_dir))
        rec["shadow_proj"][m] = proj
    # 辺ごとの帯の幅と、その辺が折り目か(提案の辺を、真の辺に向き・距離で対応づける)
    bands = []
    for s in dets["prop"]["sides"]:
        for a, b, crease in truth_sides(tr):
            ang, dist = line_dist_angle(s, a, b)
            if ang <= CREASE_ANG and dist * mm <= CREASE_MM:
                bands.append((s["hem"], s["band"], crease))
                break
    rec["bands"] = bands
    return rec


def _iou(a, b):
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else 0.0

# ---------------------------------------------------------------------------------------------- 実験
SEEDS = 20                                       # 種(配置・柄・しわ・雑音が変わる)。配置の分布を数える
FOLDS = ("flat", "half", "third", "quarter")
CONTRASTS = (0.0, 0.3, 0.5, 0.6, 0.7, 0.85, 1.0)  # 台の平均色をタオルの平均色(0)から濃い茶(1)へ
WRINKLES = (0.0, 1.0, 2.0, 3.0, 4.0)              # しわの振幅 [mm]
AZIMUTHS = (0.0, 90.0, 180.0, 270.0)              # 照明の方位 [度]
BASE = dict(fold="half", contrast=1.0, wrinkle=1.0, light_az=90.0)
LIGHT_CONTRAST = 0.7                              # 照明の方位を振る回の台の色(影と濃淡が効き始める所)
SHOWN = ("prop", "propc", "propv", "harris", "hull", "far", "rect", "rectc")
NAMES = {"prop": "提案(RGB)", "propc": "提案(色度)", "propv": "多角形の頂点のまま(色度)", "harris": "Harris のみ",
         "hull": "凸包の頂点のみ", "far": "重心から最遠の 4 点",
         "rect": "最小外接長方形", "rectc": "最小外接長方形(色度)"}

_CELLS = {}


def cell(fold, contrast, wrinkle, light_az):
    """1 条件 x SEEDS 枚の記録(同じ条件は 1 度だけ走らせる)。"""
    key = (fold, float(contrast), float(wrinkle), float(light_az))
    if key not in _CELLS:
        _CELLS[key] = [evaluate(s, fold=fold, contrast=contrast, wrinkle=wrinkle, light_az=light_az)
                       for s in range(SEEDS)]
    return _CELLS[key]


def boot_ci(per_seed, n=2000, seed=7):
    """種ごとの値の平均の 95 % 区間(種を復元抽出)。"""
    v = np.asarray(per_seed, float)
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, len(v), (n, len(v)))].mean(axis=1)
    return float(v.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def recall(recs, m):
    """隅の再現率(5 mm 以内に検出がある真の隅の割合)の、種ごとの値。"""
    return np.array([r["found"][m].mean() for r in recs])


def errs(recs, m, unit="mm"):
    """見つかった隅(15 mm の門の内)の誤差の全部(unit = mm か px)。"""
    e = np.concatenate([r["err"][m] for r in recs])
    e = e[np.isfinite(e)]
    if unit == "px":
        e = e / np.mean([r["mm_per_px"] for r in recs])
    return e


def quant(e, q):
    return float(np.percentile(e, q)) if len(e) else float("nan")


def crease_recall(recs, m):
    h = [x for r in recs for x in r["crease"][m]]
    return (float(np.mean(h)), len(h)) if h else (float("nan"), 0)


def hit1(recs, m):
    sel = [r for r in recs if r["fold"] != "flat"]
    return np.array([float(r["hit1"][m]) for r in sel])


def auc(pos, neg):
    """Mann-Whitney の AUC: pos の値が neg より大きい確率(同値は 1/2)。"""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    g = (pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()
    return float(g)


def overlay(img, tr, det, crop=190):
    """検出の重ね描き。赤の十字 = 提案の隅、青の円 = 真の隅(最後に描く)、緑 = 提案の辺、黄 = 真の折り目。線は 2 px 幅
    (縮小しても残る)。"""
    out = img.copy()
    H, W = SHAPE

    def put(r, c, col, t=2):
        r, c = int(round(r)), int(round(c))
        if 0 <= r < H - t and 0 <= c < W - t:
            out[r:r + t, c:c + t] = col

    def seg(a, b, col, step=0.5):
        n = int(np.linalg.norm(b - a) / step) + 1
        for t in np.linspace(0, 1, n):
            p = a + t * (b - a)
            put(p[0], p[1], col)

    for ca, cb in tr["creases_px"]:
        seg(ca, cb, (1.0, 1.0, 0.0))
    for s in det["sides"]:
        seg(s["c"] - s["d"] * s["len"] / 2, s["c"] + s["d"] * s["len"] / 2, (0.0, 1.0, 0.0))
    for p in det["corners"]:                                  # 検出の十字(長い腕)
        for d in range(-10, 11):
            put(p[0] + d, p[1], (1.0, 0.0, 0.0), 3)
            put(p[0], p[1] + d, (1.0, 0.0, 0.0), 3)
    for p in tr["corners_px"]:                                # 真の隅は円で、赤の上に最後に描く
        for ang in np.linspace(0, 2 * np.pi, 120):
            put(p[0] + 9 * np.sin(ang), p[1] + 9 * np.cos(ang), (0.0, 0.2, 1.0), 3)
    cen = tr["corners_px"].mean(0)
    r0 = int(np.clip(cen[0] - crop, 0, H - 2 * crop))
    c0 = int(np.clip(cen[1] - crop, 0, W - 2 * crop))
    return out[r0:r0 + 2 * crop, c0:c0 + 2 * crop]


def shoelace(P):
    x, y = P[:, 1], P[:, 0]
    return 0.5 * abs(float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))


# ---------------------------------------------------------------------------------------------- 門
NAMES_EN = {"prop": "proposed (RGB)", "propc": "proposed (chroma)", "propv": "polygon vertices (chroma)",
            "harris": "Harris only", "hull": "hull vertices only", "far": "4 farthest from centroid",
            "rect": "min-area rectangle", "rectc": "min-area rectangle (chroma)"}
_GATES = []


# 帯の決め方(2026-11-12): 種の組を 8 つ(種 0〜19 に 1000・2000・…・7000 を足した組)で PoC を走らせ、各門の値の最小・最大を取り、
# 幅(最大 - 最小)を両側に足した(幅が小さい門は 0.05 x max(1, |平均|) を足す)。1 組(種 0〜19)だけに合わせると別の組で 3〜4 本が落ち
# (独立レビュー)、5 組・幅の半分でも帯の決定に使っていない組で 10 本前後が落ちた。この 8 組・幅 1 倍の帯は、決定に使っていない
# 2 組(8000、9000)で 0 本落ちた。走査はこの repo の外で行った(PoC 本体の実行時間は増えない)。
BANDS = {
    'area ratio flat': (0.945, 1.045),
    'area ratio half': (0.9479, 1.049),
    'area ratio third': (0.948, 1.049),
    'area ratio quarter': (0.9484, 1.049),
    'median corner error prop [mm]': (1.281, 1.868),
    'p90 corner error prop [mm]': (2.691, 3.217),
    'recall prop (80 images)': (0.9062, 1.044),
    'median corner error propc [mm]': (0.8261, 1.212),
    'p90 corner error propc [mm]': (1.704, 2.147),
    'recall propc (80 images)': (0.9312, 1.05),
    'median corner error propv [mm]': (1.783, 2.173),
    'p90 corner error propv [mm]': (2.872, 3.574),
    'recall propv (80 images)': (0.9187, 1.044),
    'median corner error harris [mm]': (3.391, 3.867),
    'p90 corner error harris [mm]': (4.436, 5.125),
    'recall harris (80 images)': (0.8281, 0.9781),
    'median corner error hull [mm]': (3.78, 4.568),
    'p90 corner error hull [mm]': (5.576, 8.628),
    'recall hull (80 images)': (0.5875, 0.7313),
    'median corner error far [mm]': (3.042, 3.448),
    'p90 corner error far [mm]': (4.295, 5.071),
    'recall far (80 images)': (0.8687, 1.003),
    'median corner error rect [mm]': (0.9471, 1.253),
    'p90 corner error rect [mm]': (1.709, 2.283),
    'recall rect (80 images)': (0.95, 1.05),
    'median corner error rectc [mm]': (1.31, 1.842),
    'p90 corner error rectc [mm]': (2.162, 2.717),
    'recall rectc (80 images)': (0.95, 1.05),
    'median error prop(RGB) minus minrect(RGB) [mm]': (0.2942, 0.6353),
    'median error prop(chroma) minus minrect(RGB) [mm]': (-0.2446, 0.05253),
    'median error minrect(chroma) minus minrect(RGB) [mm]': (0.2669, 0.6816),
    'median corner error vs table-plane truth prop [mm]': (0.8469, 1.375),
    'median corner error vs table-plane truth propc [mm]': (1.033, 1.48),
    'median corner error vs table-plane truth rect [mm]': (0.996, 1.397),
    'median corner error vs table-plane truth rectc [mm]': (1.961, 2.374),
    'table-plane truth: prop(RGB) minus minrect(RGB) [mm]': (-0.3314, 0.1495),
    'contrast #0: recall prop': (-0.05, 0.25),
    'contrast #0: recall propc': (-0.05, 0.05),
    'contrast #0: recall rect': (0.0125, 0.35),
    'contrast #0: recall rectc': (-0.05, 0.05),
    'contrast #0: recall harris': (0.525, 0.75),
    'contrast #1: recall prop': (-0.0125, 0.4375),
    'contrast #1: recall propc': (0.0375, 0.975),
    'contrast #1: recall rect': (0.075, 0.4125),
    'contrast #1: recall rectc': (0.025, 1),
    'contrast #1: recall harris': (0.275, 0.725),
    'contrast #2: recall prop': (0.425, 0.875),
    'contrast #2: recall propc': (0.85, 1.075),
    'contrast #2: recall rect': (0.15, 0.8625),
    'contrast #2: recall rectc': (0.9, 1.05),
    'contrast #2: recall harris': (0.475, 0.775),
    'contrast #3: recall prop': (0.6, 0.9375),
    'contrast #3: recall propc': (0.925, 1.05),
    'contrast #3: recall rect': (0.55, 1.038),
    'contrast #3: recall rectc': (0.9375, 1.05),
    'contrast #3: recall harris': (0.475, 0.925),
    'contrast #4: recall prop': (0.75, 1.05),
    'contrast #4: recall propc': (0.9125, 1.05),
    'contrast #4: recall rect': (0.85, 1.038),
    'contrast #4: recall rectc': (0.95, 1.05),
    'contrast #4: recall harris': (0.5375, 1.062),
    'contrast #5: recall prop': (0.8875, 1.038),
    'contrast #5: recall propc': (0.925, 1.05),
    'contrast #5: recall rect': (0.925, 1.05),
    'contrast #5: recall rectc': (0.95, 1.05),
    'contrast #5: recall harris': (0.775, 1.037),
    'contrast #6: recall prop': (0.875, 1.062),
    'contrast #6: recall propc': (0.925, 1.05),
    'contrast #6: recall rect': (0.95, 1.05),
    'contrast #6: recall rectc': (0.95, 1.05),
    'contrast #6: recall harris': (0.875, 1.025),
    'wrinkle 0 mm: recall prop': (0.9125, 1.05),
    'wrinkle 0 mm: recall propc': (0.9, 1.05),
    'wrinkle 0 mm: recall rect': (0.95, 1.05),
    'wrinkle 0 mm: recall rectc': (0.95, 1.05),
    'wrinkle 0 mm: recall harris': (0.925, 1.05),
    'wrinkle 0 mm: recall propv': (0.9, 1.05),
    'wrinkle 0 mm: median error propc [mm]': (0.3684, 0.5826),
    'wrinkle 0 mm: median error propv [mm]': (1.992, 2.799),
    'wrinkle 0 mm: median error rect [mm]': (1.267, 1.525),
    'wrinkle 0 mm: median error rectc [mm]': (0.3105, 0.8211),
    'wrinkle 1 mm: recall prop': (0.875, 1.062),
    'wrinkle 1 mm: recall propc': (0.925, 1.05),
    'wrinkle 1 mm: recall rect': (0.95, 1.05),
    'wrinkle 1 mm: recall rectc': (0.95, 1.05),
    'wrinkle 1 mm: recall harris': (0.875, 1.025),
    'wrinkle 1 mm: recall propv': (0.9125, 1.05),
    'wrinkle 1 mm: median error propc [mm]': (0.7636, 1.291),
    'wrinkle 1 mm: median error propv [mm]': (2.215, 2.722),
    'wrinkle 1 mm: median error rect [mm]': (0.666, 1.481),
    'wrinkle 1 mm: median error rectc [mm]': (1.178, 1.659),
    'wrinkle 2 mm: recall prop': (0.5625, 1.087),
    'wrinkle 2 mm: recall propc': (0.9125, 1.038),
    'wrinkle 2 mm: recall rect': (0.85, 1.075),
    'wrinkle 2 mm: recall rectc': (0.875, 1.062),
    'wrinkle 2 mm: recall harris': (0.45, 0.975),
    'wrinkle 2 mm: recall propv': (0.8875, 1.025),
    'wrinkle 2 mm: median error propc [mm]': (1.167, 2.405),
    'wrinkle 2 mm: median error propv [mm]': (2.068, 2.911),
    'wrinkle 2 mm: median error rect [mm]': (1.478, 2.283),
    'wrinkle 2 mm: median error rectc [mm]': (1.984, 3.28),
    'wrinkle 3 mm: recall prop': (0.3875, 0.725),
    'wrinkle 3 mm: recall propc': (0.7, 1),
    'wrinkle 3 mm: recall rect': (0.5375, 1.1),
    'wrinkle 3 mm: recall rectc': (0.525, 0.9375),
    'wrinkle 3 mm: recall harris': (0.1, 0.925),
    'wrinkle 3 mm: recall propv': (0.8125, 0.9625),
    'wrinkle 3 mm: median error propc [mm]': (1.314, 3.706),
    'wrinkle 3 mm: median error propv [mm]': (1.979, 3.084),
    'wrinkle 3 mm: median error rect [mm]': (2.646, 3.57),
    'wrinkle 3 mm: median error rectc [mm]': (3.256, 4.542),
    'wrinkle 4 mm: recall prop': (0, 0.4875),
    'wrinkle 4 mm: recall propc': (0.425, 0.875),
    'wrinkle 4 mm: recall rect': (0.4, 0.7375),
    'wrinkle 4 mm: recall rectc': (0.325, 0.625),
    'wrinkle 4 mm: recall harris': (0.05, 0.5375),
    'wrinkle 4 mm: recall propv': (0.5625, 0.975),
    'wrinkle 4 mm: median error propc [mm]': (2.039, 4.703),
    'wrinkle 4 mm: median error propv [mm]': (2.137, 3.172),
    'wrinkle 4 mm: median error rect [mm]': (3.197, 5.494),
    'wrinkle 4 mm: median error rectc [mm]': (4.28, 6.016),
    'lowest dE with recall >= 0.9: prop': (30.76, 73.24),
    'first wrinkle with recall < 0.9: prop [mm]': (1, 4),
    'lowest dE with recall >= 0.9: propc': (27.38, 36.59),
    'first wrinkle with recall < 0.9: propc [mm]': (2, 5),
    'lowest dE with recall >= 0.9: rect': (39.16, 52.55),
    'first wrinkle with recall < 0.9: rect [mm]': (2, 5),
    'lowest dE with recall >= 0.9: rectc': (27.38, 36.59),
    'first wrinkle with recall < 0.9: rectc [mm]': (2.85, 3.15),
    'lowest dE with recall >= 0.9: harris': (39.29, 88.16),
    'first wrinkle with recall < 0.9: harris [mm]': (1.9, 2.1),
    'azimuth 0: recall prop': (0.7625, 0.9875),
    'azimuth 0: recall propc': (0.9125, 1.05),
    'azimuth 0: recall rect': (0.8375, 1.062),
    'azimuth 0: recall rectc': (0.95, 1.05),
    'azimuth 0: recall harris': (0.55, 1.038),
    'azimuth 90: recall prop': (0.75, 1.05),
    'azimuth 90: recall propc': (0.9125, 1.05),
    'azimuth 90: recall rect': (0.85, 1.038),
    'azimuth 90: recall rectc': (0.95, 1.05),
    'azimuth 90: recall harris': (0.5375, 1.062),
    'azimuth 180: recall prop': (0.7875, 1.05),
    'azimuth 180: recall propc': (0.925, 1.05),
    'azimuth 180: recall rect': (0.85, 1.075),
    'azimuth 180: recall rectc': (0.95, 1.05),
    'azimuth 180: recall harris': (0.575, 1.025),
    'azimuth 270: recall prop': (0.6875, 1.1),
    'azimuth 270: recall propc': (0.925, 1.05),
    'azimuth 270: recall rect': (0.775, 1.113),
    'azimuth 270: recall rectc': (0.95, 1.05),
    'azimuth 270: recall harris': (0.5875, 0.9625),
    'side direction error median prop [deg]': (0.08466, 0.2304),
    'side direction error p90 prop [deg]': (0.6091, 1.056),
    'side direction error median propc [deg]': (0.07221, 0.2092),
    'side direction error p90 propc [deg]': (0.2798, 1.079),
    'side direction error median rect [deg]': (0.04914, 0.1934),
    'side direction error p90 rect [deg]': (0.2405, 0.5181),
    'side direction error median rectc [deg]': (0.05519, 0.1958),
    'side direction error p90 rectc [deg]': (0.2228, 0.5475),
    'crease recall prop(RGB), 80 creases': (0.95, 1.05),
    'share of detected sides that are creases (no discrimination)': (0.2833, 0.3847),
    'grasp hit@1 minus chance: prop': (0.3167, 0.6167),
    'grasp hit@1 minus chance: propc': (0.4833, 0.6333),
    'grasp hit@1 minus chance: harris': (-0.1167, 0.1833),
    'grasp hit@1 minus chance: hull': (-0.2833, 0.3167),
    'grasp hit@1 minus chance: far': (-0.2, 0.25),
    'grasp hit@1 minus chance: rect': (-0.4, 0.35),
    'grasp hit@1 chance level': (0.3667, 0.4667),
    'grasp hit@1 minus chance without hem line: prop(RGB)': (-0.3333, 0.2167),
    'grasp hit@1 minus chance without hem line: prop(chroma)': (-0.2, 0.5),
    'AUC raw vs crease, hem depth': (0.8594, 1.033),
    'AUC raw vs crease, shading band (weak)': (0.403, 0.7098),
    'chroma - RGB recall gain, wrinkle 0 mm (mean)': (-0.1, 0.0875),
    'chroma - RGB recall gain, wrinkle 3 mm (mean)': (0.2, 0.4625),
    'chroma - RGB recall gain, wrinkle 4 mm (mean)': (0.0375, 0.7125),
    'vertex - intersection recall gain, wrinkle 0 mm (mean)': (-0.075, 0.05),
    'vertex - intersection recall gain, wrinkle 3 mm (mean)': (-0.125, 0.2125),
    'vertex - intersection recall gain, wrinkle 4 mm (mean)': (-0.125, 0.3625),
    'recall against truth shifted by 20 mm': (-0.05, 0.05),
}


def gate(name, value, fmt="%.3f"):
    """値が BANDS[名前] の帯の内にあること。帯は実測の近くに置く(ゆるい帯は通ってはいけない所を通す)。"""
    lo, hi = BANDS[name]
    ok = (lo is None or value >= lo) and (hi is None or value <= hi)
    band = "[%s, %s]" % ("-" if lo is None else fmt % lo, "-" if hi is None else fmt % hi)
    _GATES.append((name, ok))
    print("   gate %-58s %s  band %s  %s" % (name, fmt % value, band, "ok" if ok else "FAIL"))
    assert ok, "gate failed: %s = %s, band %s" % (name, fmt % value, band)


def geometry_checks():
    """折りの幾何: 層の数・折り目の数・開いた隅の数・面積が、折り方から決まる値と一致すること。"""
    want = {"flat": ((1, 1, 1, 1), 0, 4, W_T * L_T), "half": ((2, 2, 2, 2), 1, 2, W_T * L_T / 2),
            "third": ((1, 1, 2, 2), 1, 2, W_T * (L_T / 6 + L_T / 2)), "quarter": ((4, 4, 4, 4), 2, 1, W_T * L_T / 4)}
    ratios = []
    for f, (layers, ncre, nopen, area) in want.items():
        img, tr = render_scene(0, fold=f, contrast=1.0, wrinkle=0.0, light_az=90.0)
        assert tuple(tr["layers"]) == layers, (f, tr["layers"])
        assert len(tr["creases_px"]) == ncre and int(tr["open"].sum()) == nopen, (f, len(tr["creases_px"]), tr["open"])
        # 描いた画像の領域の面積(画素)と、真の隅を結んだ四角形の面積の比(上面の高さの視差で数 % ずれる)
        ratios.append(float(tr["cover"].sum() / shoelace(tr["corners_px"])))
        assert np.isfinite(img).all() and float(np.ptp(img)) > 0.2
    return ratios


def shifted_truth_recall(n=6, shift_mm=20.0):
    """対照: 真の隅を 20 mm 平行移動した偽の真値と突き合わせる。検出が当たるのは、本当にその画像の隅を見つけたときだけのはず
    (別の種の真値は隅どうしが 6 px しか離れない種があり、対照にならなかった)。"""
    found = []
    for s_ in range(n):
        img, tr = render_scene(s_, fold="half", contrast=1.0, wrinkle=1.0, light_az=90.0)
        fake = tr["corners_px"] + np.array([0.0, shift_mm / tr["mm_per_px"]])
        P = detect_proposed(img)
        err, _ = match_corners(P["corners"], fake, tr["mm_per_px"], GATE_MM)
        found.append(float(np.mean(np.isfinite(err) & (err <= FOUND_MM))))
    return float(np.mean(found))


def paired_diff(recs_a, recs_b, m_a, m_b):
    """種ごとの再現率の差(a - b)の平均と 95 % 区間。"""
    return boot_ci(recall(recs_a, m_a) - recall(recs_b, m_b))


METH5 = ("prop", "propc", "rect", "rectc", "harris")     # 条件を振る門で数える方法(基準線は最小外接長方形と Harris)


def lowest_de_ok(con, m, level=0.9):
    """再現率が level 以上になる最低の ΔE(届かなければ 99)。"""
    ok = [dE for _, dE, recs in con if recall(recs, m).mean() >= level]
    return min(ok) if ok else 99.0


def first_wrinkle_below(wri, m, level=0.9):
    """再現率が level を下回る最初のしわの振幅 [mm](下回らなければ 99)。"""
    bad = [w for w, recs in wri if recall(recs, m).mean() < level]
    return min(bad) if bad else 99.0


def main():
    t0 = time.time()
    print("PoC: 置かれたタオルの角・辺・折り線を古典の画像処理だけで見つける(合成、真値は描画側)")
    print("   描画: %dx%d px、台の面で 1 px = %.2f mm、タオル %.0fx%.0f mm、1 層 %.1f mm、種 %d 本/条件" %
          (SHAPE[1], SHAPE[0], HC / F_PX, W_T, L_T, LAYER, SEEDS))

    print("\n0. 折りの幾何と描画の整合")
    ratios = geometry_checks()
    print("   層・折り目・開いた隅の数は 4 つの折り方すべてで一致。領域の面積 / 真の隅の四角形の面積: %s" %
          " ".join("%.3f" % r for r in ratios))
    for f, r in zip(FOLDS, ratios):
        gate("area ratio %s" % f, r)

    print("\n1. 折り方(コントラスト・しわ 1 mm・方位 90 度): 隅の誤差(主)と再現率(補助。5 mm 以内)")
    base = {}
    for f in FOLDS:
        recs = cell(f, 1.0, 1.0, 90.0)
        base[f] = recs
        print("   %-8s" % f + "  ".join("%s %.2f" % (m, recall(recs, m).mean()) for m in SHOWN))
    allb = [r for f in FOLDS for r in base[f]]
    print("   誤差(見つかった隅、4 折り方 x %d 種の全部。検出数の平均も): " % SEEDS)
    summary = {}
    for m in SHOWN:
        e_mm, e_px = errs(allb, m), errs(allb, m, "px")
        rc = boot_ci(recall(allb, m))
        summary[m] = (rc, quant(e_mm, 50), quant(e_mm, 90), quant(e_px, 50), quant(e_px, 90))
        print("   %-22s 誤差 中央値 %.2f mm (%.2f px)  90%% 点 %.2f mm (%.2f px)  再現率 %.3f [%.3f, %.3f]  検出数 %.2f" %
              (NAMES[m], summary[m][1], summary[m][3], summary[m][2], summary[m][4], rc[0], rc[1], rc[2],
               np.mean([r["ndet"][m] for r in allb])))
    for m in SHOWN:
        gate("median corner error %s [mm]" % m, summary[m][1])
        gate("p90 corner error %s [mm]" % m, summary[m][2])
        gate("recall %s (80 images)" % m, summary[m][0][0])
    gate("median error prop(RGB) minus minrect(RGB) [mm]", summary["prop"][1] - summary["rect"][1])
    gate("median error prop(chroma) minus minrect(RGB) [mm]", summary["propc"][1] - summary["rect"][1])
    gate("median error minrect(chroma) minus minrect(RGB) [mm]", summary["rectc"][1] - summary["rect"][1])

    # 真値の高さの定義: 隅の高さで投影した真値(本線)と、台の面で投影した真値で、1 mm 前後の比較が変わるか
    tb = {m: float(np.median(np.concatenate([r["err_table"][m][np.isfinite(r["err_table"][m])] for r in allb])))
          for m in ("prop", "propc", "rect", "rectc")}
    print("   真値を台の面で投影した場合の誤差の中央値 [mm](本線は隅の高さで投影): " +
          "  ".join("%s %.2f(本線 %.2f)" % (m, tb[m], summary[m][1]) for m in tb))
    for m in tb:
        gate("median corner error vs table-plane truth %s [mm]" % m, tb[m])
    gate("table-plane truth: prop(RGB) minus minrect(RGB) [mm]", tb["prop"] - tb["rect"])

    print("\n2. コントラスト(ΔE: タオルと台の平均色の CIE Lab の距離)")
    con = []
    for c in CONTRASTS:
        recs = cell("half", c, 1.0, 90.0)
        dE = float(np.mean([r["dE"] for r in recs]))
        con.append((c, dE, recs))
        print("   ΔE %5.1f  領域 IoU %.2f(色度 %.2f)  " % (dE, np.mean([r["mask_iou"] for r in recs]),
                                                          np.mean([r["mask_iou_c"] for r in recs])) +
              "  ".join("%s %.2f" % (m, recall(recs, m).mean()) for m in SHOWN))
    for i, (_, dE, recs) in enumerate(con):
        for m in METH5:
            gate("contrast #%d: recall %s" % (i, m), recall(recs, m).mean())

    print("\n3. しわの振幅 [mm]")
    wri = []
    for w in WRINKLES:
        recs = cell("half", 1.0, w, 90.0)
        wri.append((w, recs))
        print("   %.0f mm  領域 IoU %.2f  " % (w, np.mean([r["mask_iou"] for r in recs])) +
              "  ".join("%s %.2f" % (m, recall(recs, m).mean()) for m in SHOWN) +
              "  誤差の中央値 " + " ".join("%s %.2f" % (m, quant(errs(recs, m), 50)) for m in ("propc", "propv", "rect", "rectc")))
    for i, (w, recs) in enumerate(wri):
        for m in METH5 + ("propv",):
            gate("wrinkle %.0f mm: recall %s" % (w, m), recall(recs, m).mean())
        for m in ("propc", "propv", "rect", "rectc"):
            gate("wrinkle %.0f mm: median error %s [mm]" % (w, m), quant(errs(recs, m), 50))

    print("\n   壊れる値の表(再現率が 0.9 を下回る境目)")
    brk = {}
    for m in METH5:
        brk[m] = (lowest_de_ok(con, m), first_wrinkle_below(wri, m))
        print("   %-22s 0.9 に届く最低の ΔE %5.1f   しわで 0.9 を下回る最初の振幅 %s mm" %
              (NAMES[m], brk[m][0], "なし" if brk[m][1] > 50 else "%.0f" % brk[m][1]))
        gate("lowest dE with recall >= 0.9: %s" % m, brk[m][0], "%.1f")
        gate("first wrinkle with recall < 0.9: %s [mm]" % m, brk[m][1], "%.1f")

    print("\n4. 照明の方位 [度](台の色 %.1f、ΔE %.0f)" % (LIGHT_CONTRAST, np.mean([r["dE"] for r in cell("half", LIGHT_CONTRAST, 1.0, 90.0)])))
    lig = []
    for a in AZIMUTHS:
        recs = cell("half", LIGHT_CONTRAST, 1.0, a)
        lig.append((a, recs))
        print("   %3.0f  " % a + "  ".join("%s %.2f" % (m, recall(recs, m).mean()) for m in SHOWN))
        for m in METH5:
            gate("azimuth %.0f: recall %s" % (a, m), recall(recs, m).mean())

    print("\n5. 辺の向きと折り線")
    sidm = {}
    for m in ("prop", "propc", "rect", "rectc"):
        v = np.array([x for r in allb for x in r["side"][m]])
        sidm[m] = (quant(v, 50), quant(v, 90), len(v))
        print("   %-22s 辺の向きの誤差 中央値 %.2f 度 90%%点 %.2f 度 (辺 %d 本)" % (NAMES[m], sidm[m][0], sidm[m][1], len(v)))
        gate("side direction error median %s [deg]" % m, sidm[m][0])
        gate("side direction error p90 %s [deg]" % m, sidm[m][1])
    folded = [r for f in ("half", "third", "quarter") for r in base[f]]
    cre = {}
    for m in ("prop", "propc", "rect", "rectc"):
        rc, n = crease_recall(folded, m)
        sides = [x for r in folded for x in r["crease_side"][m]]
        cre[m] = (rc, n, float(np.mean(sides)) if sides else float("nan"), len(sides))
        print("   %-22s 折り線の再現率 %.3f (%d 本)  検出した辺のうち折り線に当たる割合 %.3f (%d 辺)" %
              ((NAMES[m],) + cre[m]))
    gate("crease recall prop(RGB), 80 creases", cre["prop"][0])
    gate("share of detected sides that are creases (no discrimination)", cre["prop"][2])

    print("\n6. つかむ点(開いた隅 = 折り目に触れない隅)の順位: 得点が最上位の検出が開いた真の隅の 8 mm 以内にあるか")
    chance = float(np.mean([r["open"].sum() / 4.0 for r in folded]))
    hits = {m: hit1(folded, m) for m in ("prop", "propc", "harris", "hull", "far", "rect")}
    for m, v in hits.items():
        hm = boot_ci(v)
        print("   %-22s hit@1 %.3f [%.3f, %.3f]" % (NAMES[m], *hm))
    print("   偶然(開いた隅の割合の平均): %.3f" % chance)
    hem_off = {f: cell_hem_off(f) for f in ("half", "third", "quarter")}
    ho = [r for f in hem_off for r in hem_off[f]]
    print("   裾の縫い目を描かない対照: 提案(RGB) hit@1 %.3f、提案(色度) %.3f(偶然 %.3f)" %
          (hit1(ho, "prop").mean(), hit1(ho, "propc").mean(), float(np.mean([r["open"].sum() / 4.0 for r in ho]))))
    pos = [b[0] for r in folded for b in r["bands"] if not b[2]]
    neg = [b[0] for r in folded for b in r["bands"] if b[2]]
    pos_s = [b[1] for r in folded for b in r["bands"] if not b[2]]
    neg_s = [b[1] for r in folded for b in r["bands"] if b[2]]
    auc_hem, auc_shade = auc(pos, neg), auc(neg_s, pos_s)
    print("   辺が切り口(折り目でない)かの AUC: 裾の線の深さ %.3f、丸みの陰影の帯 %.3f(折り目の方が帯が広いとして)" % (auc_hem, auc_shade))
    for m, v in hits.items():
        gate("grasp hit@1 minus chance: %s" % m, v.mean() - chance)
    gate("grasp hit@1 chance level", chance)
    gate("grasp hit@1 minus chance without hem line: prop(RGB)", hit1(ho, "prop").mean() - chance)
    gate("grasp hit@1 minus chance without hem line: prop(chroma)", hit1(ho, "propc").mean() - chance)
    gate("AUC raw vs crease, hem depth", auc_hem)
    gate("AUC raw vs crease, shading band (weak)", auc_shade)

    print("\n7. 確認実験")
    d_w0 = paired_diff(cell("half", 1.0, 0.0, 90.0), cell("half", 1.0, 0.0, 90.0), "propc", "prop")
    d_w3 = paired_diff(cell("half", 1.0, 3.0, 90.0), cell("half", 1.0, 3.0, 90.0), "propc", "prop")
    d_w4 = paired_diff(cell("half", 1.0, 4.0, 90.0), cell("half", 1.0, 4.0, 90.0), "propc", "prop")
    print("   色度(明るさを捨てる)にしたときの再現率の増分(種ごとの差の平均と 95 %% 区間): しわ 0 mm %+.3f [%+.3f, %+.3f]、"
          "3 mm %+.3f [%+.3f, %+.3f]、4 mm %+.3f [%+.3f, %+.3f]" % (d_w0 + d_w3 + d_w4))
    gate("chroma - RGB recall gain, wrinkle 0 mm (mean)", d_w0[0])
    gate("chroma - RGB recall gain, wrinkle 3 mm (mean)", d_w3[0])
    gate("chroma - RGB recall gain, wrinkle 4 mm (mean)", d_w4[0])
    d_v = {w: paired_diff(cell("half", 1.0, w, 90.0), cell("half", 1.0, w, 90.0), "propv", "propc") for w in (0.0, 3.0, 4.0)}
    print("   交点を使わず多角形の頂点をそのまま隅にした版(色度)との再現率の差(頂点 - 交点): " +
          "、".join("しわ %.0f mm %+.3f [%+.3f, %+.3f]" % ((w,) + d_v[w]) for w in d_v))
    for w in d_v:
        gate("vertex - intersection recall gain, wrinkle %.0f mm (mean)" % w, d_v[w][0])
    wt = shifted_truth_recall()
    gate("recall against truth shifted by 20 mm", wt)
    print("   真値を 20 mm 平行移動した偽の真値と突き合わせた再現率: %.3f(正しい真値では %.3f)" % (wt, summary["prop"][0][0]))

    figures(summary, con, wri, hits)
    print("\n8. 実行時間 %.0f 秒" % (time.time() - t0))
    return dict(summary=summary, con=con, wri=wri, lig=lig, base=base, hits=hits, chance=chance, cre=cre, sidm=sidm,
                brk=brk, tb=tb)


def figures(summary, con, wri, hits):
    """図(``FULLSEYE_FIGURES=off`` なら何もしない)。説明文の数値は上の実験の値から作る(本文と食い違わない)。"""
    if figs.target_dir() is None:
        return
    panels, caps = [], []
    shots = [(f, 1.0, 1.0) for f in FOLDS] + [("half", 0.3, 1.0), ("half", 1.0, 4.0)]
    for f, c, w in shots:
        img, tr = render_scene(3, fold=f, contrast=c, wrinkle=w, light_az=90.0)
        det = detect_proposed(img, chroma_only=True)
        err, _ = match_corners(det["corners"], tr["corners_px"], tr["mm_per_px"], GATE_MM)
        ok = int(np.sum(np.isfinite(err) & (err <= FOUND_MM)))
        msg = "fold=%s, this seed's dE %.0f, wrinkle %.0f mm: %d/4 corners within 5 mm" % (f, tr["contrast_dE"], w, ok)
        if ok:
            msg += " (median %.1f mm)" % np.nanmedian(err[np.isfinite(err) & (err <= FOUND_MM)])
        panels.append(overlay(img, tr, det))
        caps.append(msg)
        assert float(np.ptp(panels[-1])) > 0.1
    # 重ね描きが見えること: 赤(検出)・青(真の隅の円)・黄(折り目)・緑(辺)が純色で何画素か残っている
    big = np.concatenate([p.reshape(-1, 3) for p in panels[:4]])
    for col in ((1.0, 0.0, 0.0), (0.0, 0.2, 1.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)):
        assert int(np.all(np.isclose(big, col), axis=1).sum()) > 100, col
    figs.save_grid("towel_overlays", panels, captions=caps, ncols=3, gray=False,
                   caption="synthetic towel, 1 mm per pixel. red cross = detected corner (chroma variant), blue circle = true corner, "
                           "yellow = true crease, green = detected side. bottom row: low contrast, strong wrinkle. "
                           "dE is this seed's; the mean over 20 seeds is %.0f" % np.mean([r["dE"] for r in cell("half", 1.0, 1.0, 90.0)]))

    def sweep(xs, getter, name_x, title, fname, caption):
        series, kinds, styles, colors = [], [], [], []
        for m, col, sty in (("prop", "emphasis", None), ("propc", "right", None), ("rect", "reference", "dashed"),
                            ("rectc", "neutral", "dashed"), ("harris", "wrong", None)):
            xv = np.array(xs, float)
            yv = np.array([getter(m, k) for k in range(len(xs))])
            series.append((NAMES_EN[m], xv, yv))
            kinds.append("line")
            styles.append(sty)
            colors.append(col)
            series.append(("", xv, yv))                              # 同じ色の点: 凡例の記号が線の上にも出る
            kinds.append("scatter")
            styles.append(None)
            colors.append(col)
        figs.save_plot(fname, series, xlabel=name_x, ylabel="corner recall within 5 mm", title=title, kinds=kinds,
                       styles=styles, colors=colors, ylim=(0.0, 1.05), caption=caption)

    sweep([dE for _, dE, _ in con], lambda m, k: recall(con[k][2], m).mean(), "colour difference between towel and table (CIE Lab dE)",
          "only at dE 0 do all region methods fail; Harris does not need a region", "towel_contrast",
          "half fold, wrinkle 1 mm, %d seeds per point. hull vertices and 4-farthest are in the table, not drawn" % SEEDS)
    sweep([w for w, _ in wri], lambda m, k: recall(wri[k][1], m).mean(), "wrinkle amplitude [mm]",
          "wrinkles: every method falls; the plain rectangle holds up too", "towel_wrinkle",
          "half fold, dE 69, %d seeds per point. min-area rectangle (RGB) is dashed" % SEEDS)
    rows = []
    for m in SHOWN:
        rc, e50, e90, p50, p90 = summary[m]
        rows.append([NAMES_EN[m], "%.2f (%.2f)" % (e50, p50), "%.2f (%.2f)" % (e90, p90), "%.3f [%.3f, %.3f]" % rc,
                     "%.2f" % hits[m].mean() if m in hits else "-"])
    cap = ("median error: min-area rectangle (RGB) %.2f mm, proposed (chroma) %.2f mm, proposed (RGB) %.2f mm. "
           "The rectangle prior wins in the clean case; the chroma proposal ties it and is better at 4 mm wrinkles"
           % (summary["rect"][1], summary["propc"][1], summary["prop"][1]))
    figs.save_table("towel_summary", ["method", "median err mm (px)", "p90 err mm (px)", "corner recall [95% CI]",
                                      "grasp hit@1"], rows,
                    title="4 folds x %d seeds, dE 69, wrinkle 1 mm" % SEEDS, caption=cap)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))


def cell_hem_off(fold):
    key = (fold, 1.0, 1.0, 90.0, "nohem")
    if key not in _CELLS:
        _CELLS[key] = [evaluate(s, fold=fold, contrast=1.0, wrinkle=1.0, light_az=90.0, hem=False) for s in range(SEEDS)]
    return _CELLS[key]


if __name__ == "__main__":
    main()
    print("PASS")
