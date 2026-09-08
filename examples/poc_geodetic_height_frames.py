# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""座標が「もっともらしい数字」のまま数十メートル間違う —— 高さの基準と測地成果。

GNSS の受信機は緯度・経度・高さを返します。地図と設計図も緯度・経度・高さで
書かれています。**同じ 3 つの数字なのに、意味が違います** ——

* GNSS が返す高さは**楕円体高 h**(WGS84 楕円体の面からの高さ)、
  地図と設計図の高さは**標高 H**(ジオイド = 平均海面の延長からの高さ)。
  日本付近で ``H = h - N``、``N`` は概ね **+30〜+40 m**。
* 同じ「北緯 35 度 41 分」でも、旧日本測地系(Tokyo Datum)と世界測地系
  (JGD2011/WGS84)では**地上で数百メートル**離れた点を指します。
* さらに座標には**時刻**があります。プレート運動で地面ごと動くので、
  epoch の違う成果を混ぜると **年数 × 数 cm** ずれます。

どれも**例外を出しません**。緯度は緯度の範囲に、標高は標高らしい値に収まり、
地図にも載ります。この PoC は真値を全部自分で植えてから、
(a) 楕円体高を標高として使う、(b) 測地成果を取り違える、(c) 局所 ENU で
地球を平らとみなす、(d) 軸順・単位を取り違える、の 4 つを**別々に**測り、
**どれが静かに間違い、どれがうるさく壊れるか**を分けて数えます。

EXTEND: 実データに差し替えるなら :func:`terrain_hilly` / :func:`terrain_flat`
の戻り値(``(H, W)`` の標高格子 [m])を国土地理院の基盤地図情報 DEM
(5 m / 10 m メッシュ)に置き換え、:func:`geoid_height` を同じ機関の
ジオイド・モデル(日本のジオイド 2011 など)の格子に置き換えます。
GNSS の楕円体高は受信機の生ログ(または RINEX を処理した解)にあります。
**この PoC の中心である「真の N と比べる」は実データではできません** ——
ジオイド・モデル自身が観測から推定された量で、その真値は誰も持っていない
からです(モデルの版が変わると標高が数 cm 動きます)。実データでできるのは
§2 の**伝播の測り分け**(同じ誤差が傾斜には効かず体積には全部効く)と、
§3 の**独立な 2 つの絶対基準の突き合わせ**だけです。
なお基盤地図情報は**利用者登録が要る**ので、この PoC はダウンロードを一切
しません(規格の値は定数として本文に書いてあります)。

この PoC が示すこと(数字はすべて最終実行の実測値):

1. **床は 1 マイクロメートル**。``dem_geodetic_to_ecef`` → ``dem_ecef_to_geodetic``
   の往復を緯度 -85〜85 度・高さ -500〜9000 m の 4200 点で回すと、3 次元の
   位置ずれは最大 **1.07e-06 m**。★往復が閉じるだけでは「両方同じ向きに
   間違っている」を排除できないので、**独立に書いた反復解**とも突き合わせ
   ました(緯度の差 6.5e-12 度 = 7.2e-07 m、高さ 8.6e-07 m)。
   以降の誤差は全部この床の **10^6 倍以上**大きく、実装のせいではありません。
2. ★★**楕円体高を標高として使うと、高さは 36 m 間違うのに、傾斜は
   0.0086 度しか間違いません**。これが「引き算で消える誤差」と「消えない
   誤差」の分かれ目です。閉形式で先に予測して印字しました ——
   ジオイド高が一定なら傾斜の誤差は**厳密に 0**(実測 2.0e-14 度)、
   勾配 ``|∇N| = 1.531e-04`` があると誤差の上限は ``atan|∇N|`` = **0.008771 度**
   (実測の最大 0.008600 度)。予測と実測の差は中央値 7.4e-06 度・最大
   1.9e-03 度で、セルを 100 → 50 → 25 m と細かくすると 3.8e-03 → 1.9e-03
   → 6.3e-04 度と縮みます(**離散化**)。★ただし 2.0 倍 → 3.0 倍で、
   1 次と 2 次のあいだ。**最大値を作っているのは |∇H| の小さいセル
   (尾根・鞍部)だけ**で、中央値で語ると見落とします。
3. ★★**同じ 36 m が、体積には全部効きます**。1 km 四方の造成で設計面を
   標高 30.0 m と決め、現況を楕円体高で入れると土量が **+3.969e+07 m^3**
   ずれます(閉形式 A・N̄ = 1102500 m^2 × 36.00 m と 1.5e-08 m^3 一致)。
   ★対照群: 設計面も同じ GNSS から作れば誤差は **0.0 m^3** ——
   **汚染された物差しで汚染された対象を測ると、誤差は消えます**。
   現場は「合っている」ように見えたまま、外の測量成果と接続した瞬間にずれます。
4. ★★**浸水は 0 % か 100 % になります**。標高 32.0 m の水位に対し、真の
   浸水面積は 58081 セル中 **24325 セル(41.9 %)**。楕円体高で判定すると
   **0 セル(0.0 %)**、水位のほうに N を足し間違えると **58081 セル(100.0 %)**。
   ★0 % / 100 % は分母を疑えという話がありますが、これは小標本の産物では
   ありません —— 分母 58081 で、**構造的に**全滅しています(36 m の下駄が
   地形の起伏 46.2 m と同じ桁だから)。★逆に、起伏が 100 m を超える山地では
   部分的にしか壊れないので、「たまに変」に見えて**かえって見つけにくい**。
5. ★**ほとんど平らな土地では、ジオイドの勾配が流向をひっくり返します**。
   氾濫原(真の勾配の中央値 9.151e-05、``∇N`` と**逆向き**に置いた)に
   ``|∇N| = 1.531e-04`` を足すと、下り方向が 90 度以上回るセルが
   **42787 / 56169(76.2 %)**。閉形式(``|∇H|^2 + ∇H・∇N < 0`` のセル)の
   予測 **76.1 %** と一致しました。D8 流向(``dem_flow_direction``)では
   **56448 / 58081(97.2 %)** が別の隣へ流れます。★**傾斜の誤差 0.009 度は
   無視できても、平地では向きが逆になります** —— 灌漑・下水・内水氾濫の
   計算はここで壊れます。対照群(N 一定)は 0 セル、丘陵地(勾配が 60 倍)は
   2 / 56169。★**平らさと、向きが逆であることの両方**が要ります。
6. ★★**予測を 1 つ外しました**。視通(2 点の差)への影響を、はじめ
   ``|∇N|・d`` = **2.60 m** を上限に置きました。実測は 2120 組で最大
   **0.052 m** —— **50 分の 1** です。理由は、N の**線形部は視線にも地面にも
   同じだけ乗る**から(傾いた板を挟んでも見通しは変わらない)。残るのは
   N が弦から離れる量だけで、絞り直した上限 ``|N''|d^2/8`` = **0.144 m** の
   36 % に収まりました。判定が変わった組は **3 / 2120(0.14 %)**。
   同じ距離の地球曲率落ちは最大 **14.2 m** で、**そちらが 276 倍効きます**。
7. ★★**測地成果の取り違えは 447 m。しかも相対検査はほぼ盲目です**。
   日本の 1200 点で、旧日本測地系の数値をそのまま世界測地系として読むと
   地上で平均 **446.6 m**(281.6〜592.7 m)ずれます。緯度 +11.43 秒 /
   経度 -10.82 秒、**楕円体高も 41.50 m 跳ねます**。
   ★ところが、この誤りは ECEF 上の平行移動 + 楕円体の取り替えなので、
   **2 点間の距離はほとんど変わりません** —— 1 km 基線で **-0.1059 m**
   (-106.1 ppm、楕円体の長半径の差 -116 ppm からの予測どおり)。
   **絶対の誤り 446.6 m に対し、相対検査が見せてくれるのは 0.106 m ——
   4216 分の 1 です**。例外は 1 件も出ません。
   気づく手段は「独立な 2 つの**絶対**基準を突き合わせる」しかありません。
8. **epoch(座標の時刻)は年数 × 2.5 cm で効きます**。何年で何を割るかの表を
   §7 に出しました(代表値 2.5 cm/年: Scan-to-BIM の 5 mm は **0.2 年**、
   躯体の 10 mm は 0.4 年、土木の出来形 25 mm は 1.0 年、レーンレベルの
   100 mm は 4.0 年、一般地図の 1 m は 40.0 年)。
   ★**測量成果は「いつの」座標かを書かないと意味を持ちません**。
9. ★**局所 ENU の崖は閉形式で出ます。ただし方位で 0.4 % 動きます**。
   ``(1-k) d^2 / (2R)`` を測る前に印字して、``dem_geodetic_to_ecef`` で作った
   真の ECEF を自前の ENU 回転に通して突き合わせました —— 10 km で
   予測 **-7.8481 m** に対し、実測は**南北 -7.8652 m / 東西 -7.8303 m**。
   ★予測は両者の**あいだ**に来ます。子午線曲率半径 6357143 m と卯酉線
   曲率半径 6385412 m の違いなので、平均半径 1 本では原理的に当たりません
   (30 km では南北と東西で **0.316 m** 開きます)。
10. ★**屈折は崖を 7.2 % 遠くへ動かします**。曲率だけなら許容 5 mm を割るのは
    **252 m** ですが、標準大気(k = 0.13)なら **271 m**。
    ``1/sqrt(1-k)`` = 1.072 倍という予測どおりです。★ただし k は定数では
    ありません(夜間の逆転層では負にも 0.25 にもなる)ので、**この 7 %
    そのものが不確かさです**。
11. ★★**軸順と単位のうち、うるさく壊れるのは半分だけでした**。5 通りの
    取り違えを 3600 点で数えると、例外が出るのは緯経の入れ替えだけで、
    それも **1800 / 3600(50.0 %)**(``|経度| > 90`` のときだけ
    ``dem_geodetic_to_ecef`` の範囲検査に当たる)。残る 50 % と、
    度/ラジアン取り違え・経度の符号反転・ECEF の軸入れ替え・高さのフィート
    取り違えは **例外 0 件・返り値も完全に妥当な地球上の点**です。
    ★**チェーンの中で範囲を見ているのは 1 か所だけ**で、それが捕まえるのは
    5 つの故障のうち 1 つの、そのまた半分です。
12. **道具の穴 —— 変換の鎖が途中で切れています**。``fs.<name>`` /
    ``fs.op.<name>`` / ``fs.ledger.<name>`` / ``fs.op_find(語幹)`` の 4 層を
    引くと、``geoid`` / ``enu`` / ``datum`` / ``ortho`` / ``vertical`` /
    ``epoch`` / ``crs`` / ``utm`` / ``wgs84`` は **4 層とも 0 件**。
    在るのは ``dem_geodetic_to_ecef`` / ``dem_ecef_to_geodetic`` /
    ``dem_earth_curvature_drop`` / ``dem_geocentric_grid`` /
    ``dem_geodetic_slope`` / ``dem_cell_size_webmercator`` の 6 本だけで、
    **どれも WGS84 決め打ち**(``demops.WGS84_A`` / ``WGS84_F`` を直接参照)。
    ★つまり **この PoC の §3(測地成果の取り違え)は、fullseye の op だけでは
    再現すらできません** —— Bessel 楕円体を渡す口が無いからです。
    次に入れるべき op は §7 に具体案として並べました。

【グラウンドトゥルース】地形は 2 つとも**自分で書いた閉じた式**です ——
丘陵地 :func:`terrain_hilly`(平均勾配 + ガウス丘 + うねり)と、ほとんど
平らな氾濫原 :func:`terrain_flat`(勾配 8.0e-05 / -3.0e-05 + 小さなうねり)。
ジオイド高 :func:`geoid_height` も自分の式(定数 + 勾配 + 弱い 2 次)なので、
``∇N`` は解析的に厳密に書けます。測地成果の変換は ECEF 上の 3 パラメータ
平行移動 + 楕円体の取り替えで、**これも閉じた式**です。対照群は
(a) ジオイド高を一定にする、(b) 設計面も同じ楕円体高で作る、
(c) 同じ測地成果どうしで比べる、(d) 平面近似をやめて真の ECEF/ENU を使う、
の 4 つを 1 つずつ。

【来歴】WGS84 の定義値 a = 6378137.0 m / 1/f = 298.257223563 と、
大気屈折係数 k = 0.13(標準大気の慣行値)、平均地球半径 6371008.8 m は
``demops`` が持っている定数をそのまま使いました。Bessel 1841 楕円体の
a = 6377397.155 m / 1/f = 299.1528128 と、旧日本測地系 → WGS84 の 3 パラメータ
(-146.414, +507.337, +680.507) m は**慣用値として置いた仮定**で、
一次情報を確認していません(この PoC はダウンロードをしないので確認できない)。
日本付近のジオイド高 +36 m、その勾配 (1.10e-04, -0.50e-04) m/m、プレート運動
2.5 cm/年、および §5・§6 の許容差(5 / 10 / 25 / 100 / 1000 mm)も、
**代表値として置いた仮定**で、特定の規格・観測の値ではありません。
参照できる一次情報の所在は以下:
OGC Coordinate Transformation Standard <https://www.ogc.org/standards/ct/> /
ISO Geodetic Registry <https://geodetic.isotc211.org/> /
国土地理院 基盤地図情報 <https://service.gsi.go.jp/kiban/app/map/>
(★利用者登録が要るので、この PoC はダウンロードしません)。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --------------------------------------------------------------------------- #
# 定数 —— 「定義値」と「代表値として置いた仮定」を分けて書く                     #
# --------------------------------------------------------------------------- #
#: WGS84 楕円体の定義値。``demops.WGS84_A`` / ``WGS84_F`` と同じ値を持つ
#: (op 側の定数に触らず、この PoC の独立実装として書き下ろす)。
WGS84_A = 6378137.0
WGS84_INV_F = 298.257223563

#: Bessel 1841 楕円体(旧日本測地系が載っている楕円体)。**慣用値として置いた**
#: 仮定で、一次情報を確認していない。
BESSEL_A = 6377397.155
BESSEL_INV_F = 299.1528128

#: 旧日本測地系 → WGS84 の 3 パラメータ平行移動 [m](ECEF 上)。
#: **慣用値として置いた**仮定で、一次情報を確認していない。値そのものより
#: 「地上で数百 m」という桁と、「例外が出ない」という性質のほうがこの PoC の主題。
TOKYO_TO_WGS84_XYZ = (-146.414, 507.337, 680.507)

#: 平均地球半径 [m](IUGG)。``demops.EARTH_MEAN_RADIUS`` と同じ値。
EARTH_MEAN_R = 6371008.8

#: 大気屈折係数(標準大気の慣行値)。``dem_earth_curvature_drop`` の既定値。
#: **定数ではない** —— 夜間の逆転層では負にも 0.25 にもなる。
REFRACTION_K = 0.13

#: 日本付近のジオイド高の代表値 [m](概ね +30〜+40 m)。**代表値として置いた**。
GEOID_N0 = 36.0

#: ジオイド高の勾配 [m/m]。10 km で 1.10 m / -0.50 m 動く。**代表値として置いた**。
GEOID_GRAD = (1.10e-04, -0.50e-04)

#: ジオイド高の弱い 2 次項 [1/m]。場を平面にしないため(∇N をセルごとに変える)。
GEOID_CURV = 2.0e-09

#: プレート運動の速さ [m/年]。日本付近の代表値として置いた仮定。
PLATE_VELOCITY = 0.025

#: 格子。12.0 km 四方を 50 m で刻む(241 x 241 = 58081 セル)。
CELL_M, GRID_N = 50.0, 241

#: 現場の緯度経度(東京付近)。ENU の原点にも使う。
SITE_LAT, SITE_LON = 35.68, 139.77

#: 造成の設計面 [m](標高)と、浸水の水位 [m](標高)。どちらも T.P. のつもり。
DESIGN_LEVEL, FLOOD_LEVEL = 30.0, 32.0

#: 用途ごとの許容差 [m]。**代表値として置いた**仮定(規格の引用ではない)。
TOLERANCES = (
    ("Scan-to-BIM の点群合わせ", 0.005),
    ("建築躯体の出来形", 0.010),
    ("土木の出来形", 0.025),
    ("自動運転のレーンレベル", 0.100),
    ("一般の地図・GIS", 1.000),
)


# --------------------------------------------------------------------------- #
# グラウンドトゥルース —— 地形とジオイドを別々の閉じた式で置く                   #
# --------------------------------------------------------------------------- #
def terrain_hilly(x, y):
    """丘陵地の**標高 H** [m]。平均勾配 + ガウス丘 + うねり。"""
    return (30.0 + 2.50e-03 * (x - 6000.0) - 1.20e-03 * (y - 6000.0)
            + 18.0 * np.exp(-(((x - 4000.0) ** 2 + (y - 7500.0) ** 2)
                              / (2.0 * 1800.0 ** 2)))
            + 3.0 * np.sin(2 * np.pi * x / 3100.0) * np.cos(2 * np.pi * y / 2700.0))


def grad_hilly(x, y):
    """:func:`terrain_hilly` の勾配 ``(dH/dx, dH/dy)`` [m/m]。解析的に厳密。"""
    g = np.exp(-(((x - 4000.0) ** 2 + (y - 7500.0) ** 2) / (2.0 * 1800.0 ** 2)))
    kx, ky = 2 * np.pi / 3100.0, 2 * np.pi / 2700.0
    dx = (2.50e-03 - 18.0 * g * (x - 4000.0) / 1800.0 ** 2
          + 3.0 * kx * np.cos(kx * x) * np.cos(ky * y))
    dy = (-1.20e-03 - 18.0 * g * (y - 7500.0) / 1800.0 ** 2
          - 3.0 * ky * np.sin(kx * x) * np.sin(ky * y))
    return dx, dy


def terrain_flat(x, y):
    """ほとんど平らな氾濫原の**標高 H** [m]。勾配がジオイドの勾配と同じ桁。

    ★平均勾配を ``(-8.0e-05, +3.0e-05)`` と置いたのは意図的で、
    :data:`GEOID_GRAD` ``(+1.10e-04, -0.50e-04)`` と**逆向き**かつ**小さい**。
    現実の氾濫原の勾配(1 万分の 1 前後)とジオイドの勾配は互いに無関係な量
    なので、向きが揃うことも逆になることもあります —— この PoC は
    **逆になった土地**を置きました(揃っていれば流向は反転しません)。
    小さなうねりを重ねてあるので、反転するセルとしないセルが混ざります。
    """
    return (6.0 - 8.00e-05 * (x - 6000.0) + 3.00e-05 * (y - 6000.0)
            + 0.05 * np.sin(2 * np.pi * x / 6100.0) * np.cos(2 * np.pi * y / 5300.0))


def grad_flat(x, y):
    """:func:`terrain_flat` の勾配 ``(dH/dx, dH/dy)`` [m/m]。解析的に厳密。"""
    kx, ky = 2 * np.pi / 6100.0, 2 * np.pi / 5300.0
    dx = -8.00e-05 + 0.05 * kx * np.cos(kx * x) * np.cos(ky * y)
    dy = 3.00e-05 - 0.05 * ky * np.sin(kx * x) * np.sin(ky * y)
    return dx, dy


def geoid_height(x, y, constant=False):
    """ジオイド高 **N** [m]。``constant=True`` が対照群(勾配ゼロ)。

    ``H = h - N``。日本付近の代表値 +36 m に、代表値として置いた勾配と
    弱い 2 次項を載せる。**自分の式なので ∇N は厳密に書ける**(:func:`grad_geoid`)。
    """
    if constant:
        return np.full(np.shape(x), GEOID_N0, np.float64)
    gx, gy = GEOID_GRAD
    return (GEOID_N0 + gx * (x - 6000.0) + gy * (y - 6000.0)
            + GEOID_CURV * ((x - 6000.0) ** 2 - (y - 6000.0) ** 2))


def grad_geoid(x, y, constant=False):
    """:func:`geoid_height` の勾配 ``(dN/dx, dN/dy)`` [m/m]。"""
    if constant:
        z = np.zeros(np.shape(x), np.float64)
        return z, z.copy()
    gx, gy = GEOID_GRAD
    return (gx + 2.0 * GEOID_CURV * (x - 6000.0),
            gy - 2.0 * GEOID_CURV * (y - 6000.0))


def site_grid():
    """作業格子の ``(x, y)`` [m]。行 0 が北なので y は上から下へ減らす。"""
    xs = np.arange(GRID_N) * CELL_M
    gx, gy = np.meshgrid(xs, xs[::-1])
    return gx, gy


# --------------------------------------------------------------------------- #
# 独立実装 —— op を「往復が閉じる」だけで信用しないための第 2 の物差し           #
# --------------------------------------------------------------------------- #
def ref_geodetic_to_ecef(lat_deg, lon_deg, h_m, a=WGS84_A, inv_f=WGS84_INV_F):
    """測地座標 → ECEF [m]。**楕円体を引数で選べる**(op は WGS84 決め打ち)。"""
    f = 1.0 / inv_f
    e2 = f * (2.0 - f)
    phi, lam = np.radians(lat_deg), np.radians(lon_deg)
    sp, cp = np.sin(phi), np.cos(phi)
    n = a / np.sqrt(1.0 - e2 * sp * sp)                 # 卯酉線曲率半径
    return np.stack([(n + h_m) * cp * np.cos(lam),
                     (n + h_m) * cp * np.sin(lam),
                     (n * (1.0 - e2) + h_m) * sp], axis=-1)


def ref_ecef_to_geodetic(xyz, a=WGS84_A, inv_f=WGS84_INV_F, iters=60):
    """ECEF → 測地座標。**反復法**(op の Bowring 閉形式とは別の解き方)。"""
    f = 1.0 / inv_f
    e2 = f * (2.0 - f)
    xyz = np.asarray(xyz, np.float64)
    x, y, z = xyz[..., 0], xyz[..., 1], xyz[..., 2]
    p = np.hypot(x, y)
    lat = np.arctan2(z, p * (1.0 - e2))
    for _ in range(iters):
        n = a / np.sqrt(1.0 - e2 * np.sin(lat) ** 2)
        h = p / np.cos(lat) - n
        lat = np.arctan2(z, p * (1.0 - e2 * n / (n + h)))
    n = a / np.sqrt(1.0 - e2 * np.sin(lat) ** 2)
    h = p / np.cos(lat) - n
    return np.stack([np.degrees(lat), np.degrees(np.arctan2(y, x)), h], axis=-1)


def enu_rotation(lat_deg, lon_deg):
    """ECEF → 局所 ENU の回転行列 ``(3, 3)``。**op には無いので自前**。"""
    p, l_ = math.radians(lat_deg), math.radians(lon_deg)
    return np.array([
        [-math.sin(l_), math.cos(l_), 0.0],
        [-math.sin(p) * math.cos(l_), -math.sin(p) * math.sin(l_), math.cos(p)],
        [math.cos(p) * math.cos(l_), math.cos(p) * math.sin(l_), math.sin(p)],
    ], np.float64)


def meridian_radius(lat_deg, a=WGS84_A, inv_f=WGS84_INV_F):
    """子午線曲率半径 M [m](南北方向の曲がり)。"""
    f = 1.0 / inv_f
    e2 = f * (2.0 - f)
    s = math.sin(math.radians(lat_deg))
    return a * (1.0 - e2) / (1.0 - e2 * s * s) ** 1.5


def prime_vertical_radius(lat_deg, a=WGS84_A, inv_f=WGS84_INV_F):
    """卯酉線曲率半径 N [m](東西方向の曲がり)。"""
    f = 1.0 / inv_f
    e2 = f * (2.0 - f)
    s = math.sin(math.radians(lat_deg))
    return a / math.sqrt(1.0 - e2 * s * s)


def ground_distance(lat_a, lon_a, lat_b, lon_b):
    """2 点の**楕円体面上での**直線距離 [m](弦長。数百 m の比較には十分)。"""
    pa = np.asarray(fs.ledger.dem_geodetic_to_ecef(lat_a, lon_a, 0.0), np.float64)
    pb = np.asarray(fs.ledger.dem_geodetic_to_ecef(lat_b, lon_b, 0.0), np.float64)
    return np.linalg.norm(pa - pb, axis=-1)


def sample_line(field, cell, p0, p1, n):
    """``p0`` → ``p1``(ともに格子の ``(列 [m], 行 [m])``)を n 等分して双一次標本。"""
    h, w = field.shape
    t = np.linspace(0.0, 1.0, n)
    cx = (p0[0] + (p1[0] - p0[0]) * t) / cell
    ry = (p0[1] + (p1[1] - p0[1]) * t) / cell
    i0 = np.clip(np.floor(ry), 0, h - 2).astype(np.int64)
    j0 = np.clip(np.floor(cx), 0, w - 2).astype(np.int64)
    fy, fx = np.clip(ry - i0, 0.0, 1.0), np.clip(cx - j0, 0.0, 1.0)
    return ((1 - fy) * (1 - fx) * field[i0, j0] + (1 - fy) * fx * field[i0, j0 + 1]
            + fy * (1 - fx) * field[i0 + 1, j0] + fy * fx * field[i0 + 1, j0 + 1])


def angular_diff(a, b):
    """2 つの方位 [度] の差 ``[0, 180]``。どちらかが平坦(-1)なら ``nan``。"""
    d = np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64))
    d = np.minimum(d, 360.0 - d)
    bad = (np.asarray(a) < 0.0) | (np.asarray(b) < 0.0)
    return np.where(bad, np.nan, d)


# --------------------------------------------------------------------------- #
def section_floor():
    """§1 まず床を測る —— 往復が閉じるだけでは足りない。"""
    print("=== 1. 変換そのものの誤差の床(以降の誤差はこれと比べる)===")
    lat = np.linspace(-85.0, 85.0, 35)
    lon = np.linspace(-180.0, 175.0, 24)
    hgt = np.array([-500.0, 0.0, 500.0, 2000.0, 9000.0])
    la, lo, hh = (v.ravel() for v in np.meshgrid(lat, lon, hgt, indexing="ij"))
    print(f"  格子: 緯度 {lat[0]:.0f}〜{lat[-1]:.0f} 度 x 経度 {lon.size} 本 x "
          f"高さ {hgt.min():.0f}〜{hgt.max():.0f} m = **{la.size} 点**(乱数ではない)")

    xyz = np.asarray(fs.ledger.dem_geodetic_to_ecef(la, lo, hh), np.float64)
    got = np.asarray(fs.ledger.dem_ecef_to_geodetic(xyz), np.float64)
    back = np.asarray(fs.ledger.dem_geodetic_to_ecef(got[:, 0], got[:, 1], got[:, 2]),
                      np.float64)
    rt3d = float(np.linalg.norm(back - xyz, axis=1).max())
    rt_lat_m = float(np.abs(got[:, 0] - la).max()) * 111320.0
    rt_h = float(np.abs(got[:, 2] - hh).max())

    # ★往復は「両方同じ向きに間違っている」を排除できない。独立実装と突き合わせる。
    fwd_gap = float(np.abs(xyz - ref_geodetic_to_ecef(la, lo, hh)).max())
    ref = ref_ecef_to_geodetic(xyz)
    inv_lat_deg = float(np.abs(got[:, 0] - ref[:, 0]).max())
    inv_h = float(np.abs(got[:, 2] - ref[:, 2]).max())

    print(f"  往復(op → op)     3 次元 {rt3d:.3e} m / 緯度 {rt_lat_m:.3e} m / "
          f"高さ {rt_h:.3e} m")
    print(f"  独立実装との差       順 {fwd_gap:.3e} m / 逆 緯度 "
          f"{inv_lat_deg * 111320.0:.3e} m({inv_lat_deg:.3e} 度)/ 高さ {inv_h:.3e} m")
    print("  → ★往復が閉じるだけでは足りない(同じ向きに間違っていても閉じる)。")
    print("     op の逆変換は Bowring の閉形式、こちらは反復法 —— **別の解き方**で")
    print("     一致したので、床はマイクロメートルだと言ってよい。")
    print(f"  → 以降の誤差はすべてこの床の 10^6 倍以上。**実装のせいではない**。")
    return {"n": int(la.size), "rt3d": rt3d, "rt_lat_m": rt_lat_m, "rt_h": rt_h,
            "fwd_gap": fwd_gap, "inv_lat_deg": inv_lat_deg, "inv_h": inv_h}


def section_geoid_slope():
    """§2 楕円体高を標高として使う —— 傾斜は差なので、ほぼ消える。"""
    print("\n=== 2. 崖(a) 楕円体高 h と標高 H —— まず閉形式で予測してから測る ===")
    gx, gy = site_grid()
    out = {}
    for label, constant in (("勾配あり", False), ("N 一定(対照群)", True)):
        h_true = terrain_hilly(gx, gy)                       # 標高 H
        n_fld = geoid_height(gx, gy, constant)               # ジオイド高 N
        h_ell = h_true + n_fld                               # 楕円体高 h
        dhx, dhy = grad_hilly(gx, gy)
        dnx, dny = grad_geoid(gx, gy, constant)
        # ★予測(測る前に印字する): 傾斜は atan|∇H|。h を使うと atan|∇H+∇N|。
        pred = (np.degrees(np.arctan(np.hypot(dhx + dnx, dhy + dny)))
                - np.degrees(np.arctan(np.hypot(dhx, dhy))))
        bound = math.degrees(math.atan(float(np.hypot(dnx, dny).max())))
        s_true = np.asarray(fs.ledger.dem_slope(h_true, CELL_M))
        s_wrong = np.asarray(fs.ledger.dem_slope(h_ell, CELL_M))
        inner = (slice(2, -2), slice(2, -2))                 # 端は pad="edge" なので外す
        meas = (s_wrong - s_true)[inner]
        gap = float(np.abs(meas - pred[inner]).max())
        gap_med = float(np.median(np.abs(meas - pred[inner])))
        print(f"  [{label}]  |∇N| 最大 {float(np.hypot(dnx, dny).max()):.3e}"
              f"  → 予測の上限 atan|∇N| = {bound:.6f} 度")
        print(f"     高さの誤差 h-H:  {float((h_ell - h_true).min()):+.3f} 〜 "
              f"{float((h_ell - h_true).max()):+.3f} m(平均 "
              f"{float((h_ell - h_true).mean()):+.3f} m)")
        print(f"     傾斜の誤差:  予測 最大 {float(np.abs(pred[inner]).max()):.6f} 度 / "
              f"実測 最大 {float(np.abs(meas).max()):.6f} 度")
        print(f"     予測と実測の差: 中央値 {gap_med:.2e} 度 / 最大 {gap:.2e} 度")
        out[label] = {"bound": bound, "pred": float(np.abs(pred[inner]).max()),
                      "meas": float(np.abs(meas).max()), "gap": gap,
                      "gap_med": gap_med,
                      "dh": float((h_ell - h_true).mean()),
                      "h_true": h_true, "n_fld": n_fld, "h_ell": h_ell,
                      "s_diff": s_wrong - s_true}
    print("  → ★**36 m 間違っているのに、傾斜は 0.009 度しか間違わない**。")
    print("     傾斜は差なので N の**定数部が丸ごと消える**(N 一定の対照群は厳密に 0)。")
    print("     残るのは勾配 ∇N だけで、それも atan|∇N| で頭打ち。")
    # ★予測と実測の最大差は「模型の誤り」か「離散化」かを分ける。セルを細かくする。
    conv = []
    for cell in (100.0, 50.0, 25.0):
        n = int(round(12000.0 / cell)) + 1
        xs = np.arange(n) * cell
        cx, cy = np.meshgrid(xs, xs[::-1])
        h_t = terrain_hilly(cx, cy)
        h_e = h_t + geoid_height(cx, cy)
        dhx, dhy = grad_hilly(cx, cy)
        dnx, dny = grad_geoid(cx, cy)
        p = (np.degrees(np.arctan(np.hypot(dhx + dnx, dhy + dny)))
             - np.degrees(np.arctan(np.hypot(dhx, dhy))))
        m = (np.asarray(fs.ledger.dem_slope(h_e, cell))
             - np.asarray(fs.ledger.dem_slope(h_t, cell)))
        inner = (slice(2, -2), slice(2, -2))
        conv.append((cell, float(np.abs(m[inner] - p[inner]).max())))
    print("  → 予測と実測の最大差は**離散化**。セル寸法を変えて確かめる:")
    for cell, err in conv:
        print(f"     セル {cell:5.1f} m: 最大差 {err:.3e} 度")
    print(f"     セルを半分にすると差は {conv[0][1] / conv[1][1]:.1f} 分の 1 → "
          f"{conv[1][1] / conv[2][1]:.1f} 分の 1 と縮む。")
    print("     ★**1 次と 2 次のあいだで、きれいには乗らない**。中央値のほうは")
    print(f"     {gap_med:.1e} 度 しかないので、最大値を作っているのは一部のセルだけ ——")
    print("     |∇H| の小さいセル(尾根・鞍部)では傾斜の**向き**が決まらないので、")
    print("     解析勾配と 3x3 差分がいちばん食い違う。**平均で語ると見落とす**。")
    print("  → **消えない量はこの後の §3(体積)・§4(浸水)・§5(流向)に出る**。")
    if figs.enabled():
        a = out["勾配あり"]
        figs.save_grid(
            "geoid_frames",
            [a["h_true"], a["n_fld"], a["h_ell"], a["s_diff"]],
            ["真の標高 H [m](地図・設計図の高さ)", "ジオイド高 N [m](代表値 +36 m)",
             "楕円体高 h = H + N [m](GNSS が返す高さ)", "傾斜の誤差 [度](0 が暗)"],
            ncols=2, signed=[False, False, False, True],
            title="同じ地形の 3 つの高さ —— 目で見て区別がつかない",
            caption=f"h と H は平均 {a['dh']:+.2f} m 違うが、**塗り分けの絵は"
                    f"ほとんど同じ**(自動で伸縮するので)。右下だけが実害の大きさで、"
                    f"傾斜の誤差は最大 {a['meas']:.4f} 度 —— つまり傾斜には効かない。")
    out["conv"] = conv
    return out


def section_volume_and_flood():
    """§3・§4 体積と浸水 —— 差を取らない量には 36 m が丸ごと効く。"""
    print("\n=== 3. 崖(b) 造成の土量 —— 閉形式 ΔV = A・N̄ を先に印字 ===")
    gx, gy = site_grid()
    h_true = terrain_hilly(gx, gy)
    n_fld = geoid_height(gx, gy)
    h_ell = h_true + n_fld
    # 1 km 四方の造成区画(格子の中央)。
    site = (np.abs(gx - 6000.0) <= 500.0) & (np.abs(gy - 6000.0) <= 500.0)
    area = float(site.sum()) * CELL_M * CELL_M
    n_bar = float(n_fld[site].mean())
    pred = area * n_bar
    print(f"  区画 {area:.0f} m^2({int(site.sum())} セル)、設計面 標高 "
          f"{DESIGN_LEVEL:.1f} m、区画平均の N̄ = {n_bar:.2f} m")
    print(f"  予測: ΔV = A・N̄ = {pred:+.4e} m^3")
    v_true = float((h_true[site] - DESIGN_LEVEL).sum()) * CELL_M * CELL_M
    v_wrong = float((h_ell[site] - DESIGN_LEVEL).sum()) * CELL_M * CELL_M
    # 対照群: 設計面も同じ GNSS(楕円体高)で決めたら誤差は消える。
    v_both = float((h_ell[site] - (DESIGN_LEVEL + n_bar)).sum()) * CELL_M * CELL_M
    print(f"  {'':>28}{'土量 [m^3]':>16}{'真値との差':>16}")
    print(f"  {'真値(標高で計算)':>28}{v_true:>16.4e}{0.0:>16.1f}")
    print(f"  {'楕円体高を標高として使用':>28}{v_wrong:>16.4e}{v_wrong - v_true:>+16.4e}")
    print(f"  {'対照群: 設計面も楕円体高で':>28}{v_both:>16.4e}{v_both - v_true:>+16.4e}")
    print(f"  → 予測と実測の差 {abs((v_wrong - v_true) - pred):.2e} m^3(閉形式どおり)。")
    print("  → ★**対照群で誤差が消える**のが厄介。物差し(設計面)も同じ枠で汚せば、")
    print("     引き算で消える —— **消えたのは誤差ではなく、誤差の見え方**。")
    print("     この現場は「合っている」ように見えたまま、外の測量成果と接続した")
    print("     瞬間に 36 m ずれる。")

    print("\n=== 4. 崖(c) 浸水 —— 0 % と 100 %。ただし分母を先に出す ===")
    total = int(h_true.size)
    a_true = int((h_true <= FLOOD_LEVEL).sum())
    a_wrong = int((h_ell <= FLOOD_LEVEL).sum())
    a_flip = int((h_true <= FLOOD_LEVEL + n_bar).sum())      # 水位のほうに N を足す誤り
    print(f"  分母 = {total} セル、地形の起伏 {float(h_true.max() - h_true.min()):.1f} m、"
          f"水位 標高 {FLOOD_LEVEL:.1f} m")
    print(f"  {'判定の仕方':>34}{'浸水セル':>10}{'割合':>10}")
    for name, cnt in (("真値(標高 H で判定)", a_true),
                      ("楕円体高 h をそのまま使う", a_wrong),
                      ("水位のほうに N を足してしまう", a_flip)):
        print(f"  {name:>34}{cnt:>10}{100.0 * cnt / total:>9.1f}%")
    print("  → ★0 % / 100 % は小標本の産物ではない。**分母 58081 で構造的に全滅**")
    print(f"     している —— 下駄 {n_bar:.1f} m が地形の起伏 "
          f"{float(h_true.max() - h_true.min()):.1f} m と同じ桁だから。")
    print("     ★逆に言えば、**起伏が 100 m を超える山地では部分的にしか壊れず、")
    print("     「たまに変」に見えるので、かえって見つけにくい**。")
    if figs.enabled():
        figs.save_grid(
            "flood_masks",
            [h_true, (h_true <= FLOOD_LEVEL).astype(float),
             (h_ell <= FLOOD_LEVEL).astype(float),
             (h_true <= FLOOD_LEVEL + n_bar).astype(float)],
            ["真の標高 H [m]", f"真値: {FLOOD_LEVEL:.0f} m で浸水(明)",
             "楕円体高で判定 → どこも浸かない", "水位に N を足す → 全部浸かる"],
            ncols=2,
            title="浸水判定は 0 % か 100 % になる —— 例外は 1 件も出ない",
            caption=f"分母 {total} セル。真値 {a_true}({100.0 * a_true / total:.1f} %)"
                    f"に対し、誤用は {a_wrong} と {a_flip}。**どちらの絵も"
                    f"「もっともらしい」**(全面浸水は津波の図に見える)。")
    return {"area": area, "n_bar": n_bar, "pred": pred, "v_true": v_true,
            "v_wrong": v_wrong, "v_both": v_both, "total": total,
            "a_true": a_true, "a_wrong": a_wrong, "a_flip": a_flip,
            "relief": float(h_true.max() - h_true.min())}


def section_flow_direction():
    """§5 平地では流向が逆になる —— 傾斜が無事でも向きは無事ではない。"""
    print("\n=== 5. 崖(d) ほとんど平らな土地の流向 —— ∇N が ∇H と同じ桁になる ===")
    gx, gy = site_grid()
    out = {}
    for label, terr, grad, constant in (
            ("氾濫原・勾配あり", terrain_flat, grad_flat, False),
            ("氾濫原・N 一定(対照群)", terrain_flat, grad_flat, True),
            ("丘陵地(勾配 60 倍)", terrain_hilly, grad_hilly, False)):
        h_true = terr(gx, gy)
        h_ell = h_true + geoid_height(gx, gy, constant)
        dhx, dhy = grad(gx, gy)
        dnx, dny = grad_geoid(gx, gy, constant)
        # ★予測(閉形式): 下り方向が 90 度以上回る ⇔ ∇H・(∇H+∇N) < 0
        #   ⇔ |∇H|^2 + ∇H・∇N < 0。測る前に率を出しておく。
        dot = dhx * (dhx + dnx) + dhy * (dhy + dny)
        inner = (slice(2, -2), slice(2, -2))
        pred_rate = float((dot[inner] < 0.0).mean())
        a_true = np.asarray(fs.ledger.dem_aspect(h_true, CELL_M))
        a_wrong = np.asarray(fs.ledger.dem_aspect(h_ell, CELL_M))
        diff = angular_diff(a_true, a_wrong)[inner]
        valid = int(np.isfinite(diff).sum())
        flips = int(np.nansum(diff > 90.0))
        d8_true = np.asarray(fs.ledger.dem_flow_direction(h_true, CELL_M))
        d8_wrong = np.asarray(fs.ledger.dem_flow_direction(h_ell, CELL_M))
        d8_diff = int((d8_true != d8_wrong).sum())
        gmed = float(np.median(np.hypot(dhx, dhy)))
        print(f"  [{label}]")
        print(f"     真の勾配の中央値 {gmed:.3e} / |∇N| 最大 "
              f"{float(np.hypot(dnx, dny).max()):.3e}")
        print(f"     予測(閉形式)の反転率 {100.0 * pred_rate:.1f} %  → "
              f"実測 {flips} / {valid} = {100.0 * flips / max(valid, 1):.1f} %")
        print(f"     D8 流向が別の隣を指すセル {d8_diff} / {int(d8_true.size)} = "
              f"{100.0 * d8_diff / d8_true.size:.1f} %")
        out[label] = {"pred": pred_rate, "flips": flips, "valid": valid,
                      "d8": d8_diff, "d8_total": int(d8_true.size), "gmed": gmed,
                      "a_true": a_true, "a_wrong": a_wrong, "h_true": h_true}
    print("  → ★**傾斜の誤差 0.009 度は無視できても、向きは逆になる**。平地では")
    print("     ∇H が ∇N と同じ桁で、この土地では**向きが逆**なので、足すと反転する。")
    print("     灌漑・下水・内水氾濫の計算はここで壊れる —— 例外は出ない。")
    print("  → 対照群(N 一定)は 0 セル。丘陵地(勾配 60 倍)もほぼ 0。")
    print("     ★**平らさと、向きが逆であることの両方**が要る。どちらか欠けると起きない。")
    if figs.enabled():
        a = out["氾濫原・勾配あり"]
        d = angular_diff(a["a_true"], a["a_wrong"])
        figs.save_grid(
            "flow_flip",
            [a["h_true"], a["a_true"], a["a_wrong"], np.nan_to_num(d, nan=0.0)],
            [f"氾濫原の標高 H [m](起伏 "
             f"{float(a['h_true'].max() - a['h_true'].min()):.1f} m)", "真の斜面方位 [度]",
             "楕円体高で出した方位 [度]", "方位の差 [度](明るいほど逆向き)"],
            ncols=2,
            title="平らな土地では、ジオイドの勾配が水を逆に流す",
            caption=f"真の勾配の中央値 {a['gmed']:.2e} に対し |∇N| は 1.2e-04。"
                    f"90 度以上回ったセルは {a['flips']} / {a['valid']} "
                    f"({100.0 * a['flips'] / max(a['valid'], 1):.1f} %)。"
                    "**方位の絵は 2 枚とも「地形図らしく」見える**。")
    return out


def section_line_of_sight():
    """§6 視通 —— 差の量なので、ジオイドはほぼ効かない(効くのは曲率)。"""
    print("\n=== 6. 視通(差の量)—— どれだけ効かないかを数える ===")
    gx, gy = site_grid()
    h_true = terrain_hilly(gx, gy)
    h_ell = h_true + geoid_height(gx, gy)
    obs = [(x, y) for x in np.linspace(600.0, 11400.0, 8)
           for y in np.linspace(600.0, 11400.0, 8)]
    tgt = [(x, y) for x in np.linspace(1200.0, 10800.0, 6)
           for y in np.linspace(1200.0, 10800.0, 6)]
    dnx, dny = grad_geoid(gx, gy)
    span = float(np.hypot(gx.max() - gx.min(), gy.max() - gy.min()))
    bound = float(np.hypot(dnx, dny).max()) * span
    # ★2 つ目の(こちらが本命の)閉形式。視線は両端の h で引くので、N の**線形部**は
    #   視線にも地面にも同じだけ乗って消える。残るのは N が弦から離れる量 =
    #   |N''| d^2 / 8。この場の N'' は 2C(cos^2θ - sin^2θ) なので |N''| <= 2C。
    tight = 2.0 * GEOID_CURV * span * span / 8.0
    print(f"  予測(素朴)の上限: |∇N| 最大 x 対角長 {span:.0f} m = {bound:.2f} m")
    print(f"  ★予測(絞った): N の**線形部は視線にも同じだけ乗って消える**ので、")
    print(f"     残るのは弦からのずれ |N''|d^2/8 = {tight:.3f} m だけ。50 倍違う。")
    eye = 3.0
    pairs = 0
    flips = 0
    worst = 0.0
    drops = []
    for (ox, oy) in obs:
        for (tx, ty) in tgt:
            d = math.hypot(tx - ox, ty - oy)
            if d < 2000.0:
                continue
            pairs += 1
            n = 64
            t = np.linspace(0.0, 1.0, n)
            dist = t * d
            # 地球の曲率落ち(op)。視線も地面も同じ補正を受けるが、**地面のほうが
            # 端点で 0・中央で最大**なので、遮蔽余裕には残る。
            drop = np.asarray(fs.ledger.dem_earth_curvature_drop(dist, REFRACTION_K))
            drop = drop - (dist / d) * drop[-1]
            for field, store in ((h_true, 0), (h_ell, 1)):
                prof = sample_line(field, CELL_M, (ox, oy), (tx, ty), n) - drop
                los = prof[0] + eye + (prof[-1] + eye - prof[0] - eye) * t
                margin = float(np.min(los - prof))
                if store == 0:
                    m0 = margin
                else:
                    m1 = margin
            worst = max(worst, abs(m1 - m0))
            if (m0 >= 0.0) != (m1 >= 0.0):
                flips += 1
            drops.append(float(np.max(np.asarray(
                fs.ledger.dem_earth_curvature_drop(d, REFRACTION_K)))))
    print(f"  組数 {pairs}(2 km 以上離れた組だけ)、目線 {eye:.1f} m")
    print(f"  遮蔽余裕の変化 最大 {worst:.3f} m")
    print(f"     素朴な上限 {bound:.2f} m の {bound / max(worst, 1e-9):.0f} 分の 1、"
          f"絞った上限 {tight:.3f} m の {100.0 * worst / tight:.0f} %")
    print(f"  判定が変わった組 {flips} / {pairs} = {100.0 * flips / pairs:.2f} %")
    print(f"  参考: 同じ距離の地球曲率落ち(k={REFRACTION_K})は最大 "
          f"{max(drops):.1f} m —— **こちらが {max(drops) / max(worst, 1e-9):.0f} 倍効く**")
    print("  → ★はじめ ∇N・d(2.60 m)を上限に置いたが、実測はその 50 分の 1。")
    print("     **線形な下駄は視線にも同じだけ乗る**ので、傾いた板を挟んでも")
    print("     見通しは変わらない。残るのは N の**曲率**だけ —— 予測を絞り直した。")
    return {"pairs": pairs, "flips": flips, "worst": worst, "bound": bound,
            "tight": tight, "drop_max": max(drops)}


def section_datum():
    """§7 測地成果の取り違え —— もっともらしいまま数百 m。"""
    print("\n=== 7. 崖(e) 測地成果(datum)—— 例外は出ない。相対検査もほぼ盲目 ===")
    lat = np.linspace(26.0, 45.0, 40)
    lon = np.linspace(128.0, 146.0, 30)
    la, lo = (v.ravel() for v in np.meshgrid(lat, lon, indexing="ij"))
    print(f"  日本を覆う格子 {la.size} 点(乱数ではない)。旧日本測地系の数値を")
    print("  そのまま世界測地系として読んだら、地上でどれだけずれるか。")
    # 旧測地系の (lat, lon) → Bessel ECEF → 3 パラメータ平行移動 → WGS84 測地座標
    xyz = ref_geodetic_to_ecef(la, lo, 0.0, BESSEL_A, BESSEL_INV_F)
    xyz = xyz + np.asarray(TOKYO_TO_WGS84_XYZ, np.float64)
    got = np.asarray(fs.ledger.dem_ecef_to_geodetic(xyz), np.float64)
    shift = ground_distance(la, lo, got[:, 0], got[:, 1])
    print(f"  地上のずれ  最小 {shift.min():.1f} m / 平均 {shift.mean():.1f} m / "
          f"最大 {shift.max():.1f} m")
    print(f"  緯度 {float((got[:, 0] - la).mean()) * 3600:+.2f} 秒 / "
          f"経度 {float((got[:, 1] - lo).mean()) * 3600:+.2f} 秒 / "
          f"楕円体高 {float(got[:, 2].mean()):+.2f} m")
    print("  ★どの値も**緯度は緯度の範囲、経度は経度の範囲**に収まっている。")
    print("     例外は 1 件も出ない。地図に載せれば日本の上に載る。")

    # 相対検査: 1 km 基線の長さは、平行移動では変わらない(楕円体の差だけ残る)
    d_lat = 1000.0 / 111132.0
    b_bessel = np.linalg.norm(
        ref_geodetic_to_ecef(la, lo, 0.0, BESSEL_A, BESSEL_INV_F)
        - ref_geodetic_to_ecef(la + d_lat, lo, 0.0, BESSEL_A, BESSEL_INV_F), axis=1)
    b_wgs = np.linalg.norm(
        np.asarray(fs.ledger.dem_geodetic_to_ecef(la, lo, 0.0), np.float64)
        - np.asarray(fs.ledger.dem_geodetic_to_ecef(la + d_lat, lo, 0.0), np.float64),
        axis=1)
    rel = float((b_bessel - b_wgs).mean())
    ppm = 1e6 * float(((b_bessel - b_wgs) / b_wgs).mean())
    pred_ppm = 1e6 * (BESSEL_A - WGS84_A) / WGS84_A
    ratio = float(shift.mean()) / abs(rel)
    print(f"  1 km 基線の長さの差  {rel:+.4f} m ({ppm:+.1f} ppm)")
    print(f"     予測: 長半径の差 (a_B - a_W)/a_W = {pred_ppm:+.1f} ppm")
    print(f"  → ★**絶対の誤り {shift.mean():.1f} m に対し、相対検査が見せるのは "
          f"{abs(rel):.4f} m —— {ratio:.0f} 分の 1**。")
    print("     平行移動は距離を変えないので、構造的にそうなる。基準点間の点検測量を")
    print("     何本やっても、この 447 m には**原理的に届かない**。")
    print("     気づく手段は「独立な 2 つの**絶対**基準の突き合わせ」だけ。")

    print("\n  --- epoch(座標の時刻)—— 静かに、しかし止まらない ---")
    print(f"  プレート運動 {PLATE_VELOCITY * 100:.1f} cm/年(代表値として置いた仮定)")
    print(f"  {'用途':>26}{'許容差':>10}{'割るまでの年数':>16}")
    rows = []
    for name, tol in TOLERANCES:
        yrs = tol / PLATE_VELOCITY
        print(f"  {name:>26}{tol * 1000:>8.0f} mm{yrs:>14.1f} 年")
        rows.append((name, f"{tol * 1000:.0f} mm", f"{yrs:.1f} 年",
                     f"{PLATE_VELOCITY * 100 * 10:.0f} cm / 10 年"))
    print("  → ★成果に epoch を書かないと、**古い成果ほど静かにずれ続ける**。")
    figs.save_table("epoch_tolerance", ["用途", "許容差", "割るまでの年数", "10 年での移動"],
                    rows, title="epoch の違いは年数 x 2.5 cm で効く",
                    caption="プレート運動 2.5 cm/年 は代表値として置いた仮定。"
                            "Scan-to-BIM の許容差は 3 か月で割る。")
    if figs.enabled():
        years = np.linspace(0.0, 50.0, 51)
        figs.save_plot(
            "epoch_drift",
            [("プレート運動による移動", years, years * PLATE_VELOCITY)]
            + [(f"{n}({t * 1000:.0f} mm)", years, np.full_like(years, t))
               for n, t in TOLERANCES[:3]],
            xlabel="epoch の差 [年]", ylabel="地上での移動量 [m]",
            title="座標には時刻がある —— 何年で、どの許容差を割るか",
            caption="2.5 cm/年(代表値)。Scan-to-BIM の 5 mm は 0.2 年、"
                    "土木の出来形 25 mm は 1.0 年で割る。")
        figs.save_plot(
            "datum_shift",
            [("測地成果の取り違え(地上のずれ)", la, shift)],
            xlabel="緯度 [度]", ylabel="地上のずれ [m]", kinds=["scatter"],
            title="旧測地系の数値を世界測地系として読むと 300〜600 m",
            caption=f"日本の {la.size} 点。**例外は 1 件も出ず、"
                    f"緯度経度は妥当な範囲に収まる**。"
                    f"相対検査で見えるのは 1 km あたり {abs(rel):.3f} m だけ。")
    return {"n": int(la.size), "mean": float(shift.mean()), "min": float(shift.min()),
            "max": float(shift.max()), "dlat_sec": float((got[:, 0] - la).mean()) * 3600,
            "dlon_sec": float((got[:, 1] - lo).mean()) * 3600,
            "dh": float(got[:, 2].mean()), "rel": rel, "ppm": ppm,
            "pred_ppm": pred_ppm, "ratio": ratio}


def section_enu():
    """§8 局所 ENU の平面近似 —— 崖は閉形式。ただし方位で動く。"""
    print("\n=== 8. 崖(f) 局所 ENU の平面近似 —— 予測を先に印字する ===")
    print(f"  予測: 距離 d の点は (1-k)d^2/(2R) だけ下がる。R = {EARTH_MEAN_R:.1f} m、")
    print(f"        k = {REFRACTION_K}(標準大気の慣行値。**定数ではない**)")
    m_r = meridian_radius(SITE_LAT)
    n_r = prime_vertical_radius(SITE_LAT)
    print(f"  ★ただし「R」は方位で変わる: 北緯 {SITE_LAT} 度で 子午線 {m_r:.0f} m / "
          f"卯酉線 {n_r:.0f} m(平均 {EARTH_MEAN_R:.0f} m はそのあいだ)")
    origin = np.asarray(fs.ledger.dem_geodetic_to_ecef(SITE_LAT, SITE_LON, 0.0),
                        np.float64)[0]
    rot = enu_rotation(SITE_LAT, SITE_LON)
    print(f"  {'d [m]':>8}{'予測(曲率のみ)':>18}{'予測(屈折込み)':>18}"
          f"{'実測 南北':>12}{'実測 東西':>12}{'南北-東西':>12}")
    dists = (100.0, 500.0, 1000.0, 5000.0, 10000.0, 30000.0)
    rows, ns, es, pr = [], [], [], []
    for d in dists:
        pred_c = -float(fs.ledger.dem_earth_curvature_drop(d, 0.0))
        pred_r = -float(fs.ledger.dem_earth_curvature_drop(d, REFRACTION_K))
        lat_n = SITE_LAT + math.degrees(d / m_r)
        lon_e = SITE_LON + math.degrees(d / (n_r * math.cos(math.radians(SITE_LAT))))
        up_n = float((rot @ (np.asarray(fs.ledger.dem_geodetic_to_ecef(
            lat_n, SITE_LON, 0.0), np.float64)[0] - origin))[2])
        up_e = float((rot @ (np.asarray(fs.ledger.dem_geodetic_to_ecef(
            SITE_LAT, lon_e, 0.0), np.float64)[0] - origin))[2])
        print(f"  {d:>8.0f}{pred_c:>18.4f}{pred_r:>18.4f}{up_n:>12.4f}{up_e:>12.4f}"
              f"{up_n - up_e:>12.4f}")
        rows.append((f"{d:.0f}", f"{pred_c:.4f}", f"{up_n:.4f}", f"{up_e:.4f}",
                     f"{up_n - up_e:+.4f}"))
        ns.append(up_n)
        es.append(up_e)
        pr.append(pred_c)
    print("  → ★予測は南北と東西の**あいだ**に来る。平均半径 1 本では原理的に")
    print(f"     当たらない(30 km で南北と東西が {ns[-1] - es[-1]:.3f} m 開く)。")
    print("     ★屈折を入れた予測は**実測より浅い** —— 実測は幾何だけで、屈折は")
    print("     光の曲がりなので、同じ絵に並べるものではない(向きが同じなだけ)。")

    print(f"\n  {'用途':>26}{'許容差':>10}{'曲率のみ':>12}{'屈折込み':>12}{'比':>8}")
    trows = []
    for name, tol in TOLERANCES:
        d_c = math.sqrt(2.0 * EARTH_MEAN_R * tol)
        d_r = math.sqrt(2.0 * EARTH_MEAN_R * tol / (1.0 - REFRACTION_K))
        print(f"  {name:>26}{tol * 1000:>8.0f} mm{d_c:>10.0f} m{d_r:>10.0f} m"
              f"{d_r / d_c:>8.3f}")
        trows.append((name, f"{tol * 1000:.0f} mm", f"{d_c:.0f} m", f"{d_r:.0f} m",
                      f"{d_r / d_c:.3f}"))
    ratio = math.sqrt(1.0 / (1.0 - REFRACTION_K))
    print(f"  → 予測: 屈折は崖を 1/sqrt(1-k) = {ratio:.3f} 倍遠くへ動かす —— 表と一致。")
    print("     ★ただし k は定数ではない(夜間の逆転層で負にも 0.25 にもなる)ので、")
    print(f"     **この {100 * (ratio - 1):.1f} % そのものが不確かさ**。")
    figs.save_table("enu_tolerance",
                    ["用途", "許容差", "曲率のみで割る距離", "屈折込みで割る距離", "比"],
                    trows, title="局所 ENU を平面とみなしてよい距離",
                    caption="d = sqrt(2R・tol/(1-k))。許容差は代表値として置いた仮定。"
                            "Scan-to-BIM の 5 mm は 270 m で割る。")
    figs.save_table("enu_drop", ["d [m]", "予測 (曲率のみ)", "実測 南北", "実測 東西",
                                 "南北-東西"], rows,
                    title="平面近似の落ち幅 —— 予測は方位のあいだに来る",
                    caption="真の ECEF(dem_geodetic_to_ecef)を自前の ENU 回転に"
                            "通して測った。曲率半径が方位で違うので一致はしない。")
    if figs.enabled():
        dd = np.asarray(dists)
        figs.save_plot(
            "enu_curvature",
            [("閉形式 -d^2/(2R)", dd, np.asarray(pr)),
             ("実測(南北)", dd, np.asarray(ns)),
             ("実測(東西)", dd, np.asarray(es))],
            xlabel="局所 ENU 原点からの距離 [m]", ylabel="真の高さ(ENU の up)[m]",
            title="「地球は平ら」の崖は d^2/(2R) —— 10 km で 7.8 m",
            caption="3 本はほぼ重なる(それが言いたいこと: 崖は測る前に閉形式で出る)。"
                    "★重なって見えない差は次の図で。")
        figs.save_plot(
            "enu_residual",
            [("実測(南北) - 閉形式", dd, np.asarray(ns) - np.asarray(pr)),
             ("実測(東西) - 閉形式", dd, np.asarray(es) - np.asarray(pr))],
            xlabel="距離 [m]", ylabel="閉形式との差 [m]",
            title="平均半径 1 本では当たらない —— 予測は南北と東西のあいだ",
            caption=f"子午線 {m_r:.0f} m / 卯酉線 {n_r:.0f} m / 平均 "
                    f"{EARTH_MEAN_R:.0f} m。30 km で南北と東西が "
                    f"{abs(ns[-1] - es[-1]):.3f} m 開く。★「閉形式で出る」は"
                    "「1 つの数字で出る」ではない。")
    return {"dists": dists, "north": ns, "east": es, "pred": pr,
            "gap30": ns[-1] - es[-1], "ratio": ratio, "m_r": m_r, "n_r": n_r}


def section_axis_order():
    """§9 軸順・単位 —— うるさく壊れるか、静かに通るか、1 つずつ数える。"""
    print("\n=== 9. 軸順とラジアン/度 —— **静かに間違うものだけが危ない** ===")
    lat = np.linspace(-85.0, 85.0, 60)
    lon = np.linspace(-180.0, 177.0, 60)
    la, lo = (v.ravel() for v in np.meshgrid(lat, lon, indexing="ij"))
    hh = np.full(la.shape, 100.0)
    total = int(la.size)
    truth = np.asarray(fs.ledger.dem_geodetic_to_ecef(la, lo, hh), np.float64)
    print(f"  標本 {total} 点(全球の格子。乱数ではない)。高さは 100 m。")
    print(f"  {'取り違え':>28}{'例外':>10}{'静かに通る':>12}{'位置の誤り(中央値)':>22}")
    rows, out = [], {}
    for name, mutate in (
            ("緯経の入れ替え", lambda: (lo, la, hh)),
            ("ラジアンを度として渡す", lambda: (np.radians(la), np.radians(lo), hh)),
            ("経度の符号反転", lambda: (la, -lo, hh)),
            ("高さがフィート(m と誤認)", lambda: (la, lo, hh / 0.3048)),
    ):
        a, b, c = mutate()
        raised = 0
        errs = []
        for k in range(total):
            try:
                got = np.asarray(fs.ledger.dem_geodetic_to_ecef(
                    float(a[k]), float(b[k]), float(c[k])), np.float64)[0]
            except ValueError:
                raised += 1
                continue
            errs.append(float(np.linalg.norm(got - truth[k])))
        quiet = total - raised
        med = float(np.median(errs)) if errs else float("nan")
        print(f"  {name:>28}{raised:>10}{quiet:>12}{med:>20.1f} m")
        rows.append((name, f"{raised} / {total}", f"{quiet} / {total}",
                     f"{med:.0f} m", "うるさい" if raised else "静か"))
        out[name] = {"raised": raised, "quiet": quiet, "median": med}

    # ECEF 側の軸入れ替え(逆変換に入る側)。範囲検査が無いので必ず静かに通る。
    perm = truth[:, [1, 0, 2]]
    g_ok = np.asarray(fs.ledger.dem_ecef_to_geodetic(truth), np.float64)
    g_bad = np.asarray(fs.ledger.dem_ecef_to_geodetic(perm), np.float64)
    inrange = int(((np.abs(g_bad[:, 0]) <= 90.0) & (np.abs(g_bad[:, 1]) <= 180.0)).sum())
    med = float(np.median(ground_distance(g_ok[:, 0], g_ok[:, 1],
                                          g_bad[:, 0], g_bad[:, 1])))
    print(f"  {'ECEF の x と y を入れ替え':>28}{0:>10}{total:>12}{med:>20.1f} m")
    print(f"     → 返った緯度経度が妥当な範囲に収まった点 {inrange} / {total} "
          f"= {100.0 * inrange / total:.1f} %")
    rows.append(("ECEF の x と y を入れ替え", f"0 / {total}", f"{total} / {total}",
                 f"{med:.0f} m", "静か"))
    out["ECEF の軸入れ替え"] = {"raised": 0, "quiet": total, "median": med,
                                "inrange": inrange}
    swap = out["緯経の入れ替え"]
    print(f"  → ★例外を出したのは**緯経の入れ替えだけ**、それも {swap['raised']} / "
          f"{total} = {100.0 * swap['raised'] / total:.1f} %。")
    print("     `dem_geodetic_to_ecef` の `lat_deg must be within [-90, 90]` に")
    print("     当たるのは **|経度| > 90 のときだけ**で、残り半分は静かに通る。")
    print("  → ★**危なくないのはこの半分だけ**。あとの 4 つは例外 0 件、返り値も")
    print("     完全に妥当な地球上の点。**チェーンの中で範囲を見ているのは 1 か所**。")
    figs.save_table("axis_order",
                    ["取り違え", "例外が出た", "静かに通った", "位置の誤り(中央値)",
                     "分類"], rows,
                    title="軸順・単位の取り違え —— うるさいのは 5 分の 1 の、その半分",
                    caption=f"全球 {total} 点。例外が出るのは緯度が [-90, 90] を"
                            "外れたときだけ。**それ以外は全部「もっともらしい」座標**。")
    return {"total": total, "cases": out}


def section_tool_gap():
    """§10 道具の穴 —— 4 層を全部引いてから「無い」と言う。"""
    print("\n=== 10. 道具の穴 —— 4 層(fs. / fs.op. / fs.ledger. / op_find)を引く ===")
    stems = ("geoid", "enu", "datum", "ortho", "vertical", "msl", "epoch", "crs",
             "utm", "wgs84", "tokyo", "jgd", "ecef", "geodetic")
    fs_names = {n for n in dir(fs) if not n.startswith("_")}
    op_names = {n for n in dir(fs.op) if not n.startswith("_")}
    led_names = {n for n in dir(fs.ledger) if not n.startswith("_")}
    print(f"  {'語幹':>12}{'fs.':>8}{'fs.op.':>8}{'fs.ledger.':>12}{'op_find':>10}"
          f"  {'中身':<44}")
    rows = []
    for stem in stems:
        a = sorted(n for n in fs_names if stem in n.lower())
        b = sorted(n for n in op_names if stem in n.lower())
        c = sorted(n for n in led_names if stem in n.lower())
        d = fs.op_find(stem)
        body = ", ".join(sorted({*a, *b, *c, *(r["op"] for r in d)}))[:44] or "—"
        print(f"  {stem:>12}{len(a):>8}{len(b):>8}{len(c):>12}{len(d):>10}  {body:<44}")
        rows.append((stem, str(len(a)), str(len(b)), str(len(c)), str(len(d)), body))
    have = sorted(n for n in led_names
                  if n.startswith("dem_") and ("geo" in n or "ecef" in n
                                               or "curvature_drop" in n
                                               or "webmercator" in n))
    print(f"  → 在るのは 6 本だけ: {', '.join(have)}")
    print("  → ★**どれも WGS84 決め打ち**(demops.WGS84_A / WGS84_F を直接参照。")
    print("     楕円体を引数で渡す口が無い)。だから §7 の測地成果の取り違えは、")
    print("     **fullseye の op だけでは再現すらできない** —— この PoC は Bessel")
    print("     楕円体の順変換を自前で書いた(ref_geodetic_to_ecef の a / inv_f)。")
    print("  → ★**件数だけ見て「在る」と言ってはいけない**: ecef / geodetic は")
    print("     op_find が 3 / 4 件を返すが、中身は同じ 2 本(+ typed ラッパ)。")
    figs.save_table("tool_gap",
                    ["語幹", "fs.", "fs.op.", "fs.ledger.", "op_find", "中身"], rows,
                    title="変換の鎖はどこで切れているか(4 層すべてを引いた結果)",
                    caption="geoid / enu / datum / ortho / vertical / epoch / crs / "
                            "utm は 4 層とも 0 件。ECEF の出入口だけが在る。")
    return {"have": have, "rows": rows}


def main():
    t0 = time.perf_counter()
    floor = section_floor()
    slope = section_geoid_slope()
    vol = section_volume_and_flood()
    flow = section_flow_direction()
    los = section_line_of_sight()
    datum = section_datum()
    enu = section_enu()
    axis = section_axis_order()
    gap = section_tool_gap()

    print("\n=== 11. まとめ —— 同じ 36 m が、量によって全部効いたり全く効かなかったり ===")
    gr = slope["勾配あり"]
    fp = flow["氾濫原・勾配あり"]
    rows = [
        ("高さそのもの", f"{gr['dh']:+.2f} m", "消えない", "静か"),
        ("傾斜(差)", f"{gr['meas']:.4f} 度", "ほぼ消える", "静か"),
        ("視通の余裕(差)", f"{los['worst']:.2f} m", "ほぼ消える", "静か"),
        ("造成の土量(絶対)", f"{vol['v_wrong'] - vol['v_true']:+.3e} m^3",
         "全部効く", "静か"),
        ("浸水面積(絶対)", f"{100.0 * vol['a_true'] / vol['total']:.1f} % → "
                            f"{100.0 * vol['a_wrong'] / vol['total']:.1f} %",
         "全部効く", "静か"),
        ("平地の流向(向き)", f"{100.0 * fp['flips'] / max(fp['valid'], 1):.1f} % が反転",
         "向きが逆に", "静か"),
        ("測地成果の取り違え", f"{datum['mean']:.1f} m", "消えない", "静か"),
        ("epoch 10 年", f"{PLATE_VELOCITY * 10:.2f} m", "消えない", "静か"),
        ("平面近似 10 km", f"{enu['pred'][4]:.2f} m", "消えない", "静か(閉形式で予測可)"),
        ("緯経の入れ替え", f"半分は例外、半分は "
                           f"{axis['cases']['緯経の入れ替え']['median']:.0f} m",
         "半分だけ露見", "半分うるさい"),
        ("度/ラジアン取り違え",
         f"{axis['cases']['ラジアンを度として渡す']['median']:.0f} m", "消えない", "静か"),
    ]
    print(f"  {'量':>22}{'誤りの大きさ':>26}{'伝播':>14}{'壊れ方':>20}")
    for a, b, c, d in rows:
        print(f"  {a:>22}{b:>26}{c:>14}{d:>20}")
    print("  → ★**静かに間違うものが 11 件中 10 件**。うるさく壊れるのは緯経の")
    print("     入れ替えの、そのまた半分だけ。**危ないのは静かなほう**。")
    figs.save_table("summary", ["量", "誤りの大きさ", "伝播", "壊れ方"], rows,
                    title="ジオイド・測地成果・平面近似 —— 何がどこまで伝わるか",
                    caption="同じ 36 m が、差を取る量ではほぼ消え、絶対量では全部効き、"
                            "平地の向きでは逆転する。**例外はほとんど出ない**。")

    print("\n=== 12. 次に入れるべき op(この PoC で自前で書いた分)===")
    for name, why in (
            ("geoid_height(lat, lon, model)", "楕円体高と標高を往き来する入口。"
             "モデルの版を明示させる(版が変わると標高が数 cm 動く)"),
            ("ellipsoidal_to_orthometric(h, N) / その逆", "H = h - N。**符号を"
             "間違えると 72 m ずれる**ので、引き算を人に書かせない"),
            ("enu_from_ecef(xyz, lat0, lon0, h0) / ecef_from_enu", "この PoC で"
             "自前実装(enu_rotation)。局所座標の入口が無いのが一番の穴"),
            ("datum_shift(xyz, from_crs, to_crs)", "3/7 パラメータ Helmert。"
             "いまは楕円体を渡す口すら無い"),
            ("epoch_shift(xyz, from_epoch, to_epoch, velocity)", "座標に時刻を"
             "持たせる。**書かない限り古い成果は静かにずれ続ける**"),
            ("CRSSpec / VerticalDatumSpec / ENUFrame(型)", "★本命。"
             "lat/lon/h を裸の float3 で回すのをやめれば、§9 の 5 件のうち"
             "少なくとも 4 件は**型で止まる**"),
            ("*_ellipsoid 引数(既存 6 本に追加)", "WGS84 決め打ちを解く。"
             "Bessel / GRS80 / Clarke を渡せないと歴史成果を扱えない"),
    ):
        print(f"  - {name}\n      {why}")

    # ---- 自己検査(所見を固定する。壊れたら鳴る)-----------------------------
    # §1 床。往復も独立実装との差もマイクロメートル級。
    assert floor["n"] == 4200, floor["n"]
    assert floor["rt3d"] < 1e-4, floor["rt3d"]
    assert floor["fwd_gap"] == 0.0, floor["fwd_gap"]
    assert floor["inv_h"] < 1e-4, floor["inv_h"]
    # §2 対照群(N 一定)は傾斜に**厳密に**効かない。勾配ありでも上限を超えない。
    assert slope["N 一定(対照群)"]["meas"] < 1e-9, slope["N 一定(対照群)"]["meas"]
    assert slope["勾配あり"]["meas"] <= slope["勾配あり"]["bound"] + 1e-9
    assert slope["勾配あり"]["gap_med"] < 1e-5, slope["勾配あり"]["gap_med"]
    assert slope["勾配あり"]["meas"] < 0.01, "傾斜への影響が 0.01 度を超えた"
    # 予測と実測の最大差は離散化(2 次収束)。セルを半分にすると 3 倍以上縮む。
    cv = slope["conv"]
    assert [c for c, _ in cv] == [100.0, 50.0, 25.0], cv
    assert cv[0][1] > cv[1][1] > cv[2][1], cv
    assert cv[0][1] / cv[1][1] > 1.5, cv
    assert abs(slope["勾配あり"]["dh"] - GEOID_N0) < 1.0
    # §3 体積は閉形式 A・N̄ どおり。対照群では誤差が消える。
    assert abs((vol["v_wrong"] - vol["v_true"]) - vol["pred"]) < 1e-3, vol
    assert abs(vol["v_both"] - vol["v_true"]) < 1e-6, vol["v_both"] - vol["v_true"]
    # §4 浸水は 0 % と 100 %。分母は 58081 で、小標本ではない。
    assert vol["total"] == GRID_N * GRID_N == 58081
    assert vol["a_wrong"] == 0 and vol["a_flip"] == vol["total"], vol
    assert 0.2 < vol["a_true"] / vol["total"] < 0.5, vol["a_true"]
    # §5 平地では反転する。閉形式の予測と実測が合う。対照群と丘陵地では起きない。
    fp = flow["氾濫原・勾配あり"]
    assert fp["flips"] / fp["valid"] > 0.5, fp
    assert abs(fp["flips"] / fp["valid"] - fp["pred"]) < 0.02, fp
    assert flow["氾濫原・N 一定(対照群)"]["flips"] == 0
    assert flow["丘陵地(勾配 60 倍)"]["flips"] / \
        flow["丘陵地(勾配 60 倍)"]["valid"] < 0.05
    # §6 視通は**絞ったほうの**上限を超えない(素朴な上限は 50 倍ゆるい)。
    assert los["worst"] <= los["tight"] + 1e-6, los
    assert los["worst"] < 0.1 * los["bound"], "素朴な上限が実は妥当だった"
    assert los["drop_max"] > 50.0 * los["worst"], los
    assert los["flips"] / los["pairs"] < 0.05, los
    # §7 測地成果は数百 m。相対検査は 3 桁分盲目。ppm は長半径の差で説明できる。
    assert 250.0 < datum["mean"] < 700.0, datum["mean"]
    assert abs(datum["ppm"] - datum["pred_ppm"]) < 15.0, datum
    assert datum["ratio"] > 1000.0, datum["ratio"]
    assert abs(datum["dh"]) > 30.0, datum["dh"]
    # §8 平面近似。予測は南北と東西の**あいだ**(等号は求めない)。
    for k in range(len(enu["dists"])):
        assert enu["north"][k] <= enu["pred"][k] <= enu["east"][k], (k, enu)
    assert abs(enu["gap30"]) > 0.2, enu["gap30"]
    assert abs(enu["ratio"] - 1.0 / math.sqrt(1.0 - REFRACTION_K)) < 1e-12
    # §9 うるさく壊れるのは緯経の入れ替えの半分だけ。あとは例外 0 件。
    swap = axis["cases"]["緯経の入れ替え"]
    assert abs(swap["raised"] / axis["total"] - 0.5) < 0.02, swap
    for name in ("ラジアンを度として渡す", "経度の符号反転",
                 "高さがフィート(m と誤認)", "ECEF の軸入れ替え"):
        assert axis["cases"][name]["raised"] == 0, name
    assert axis["cases"]["ECEF の軸入れ替え"]["inrange"] == axis["total"]
    # §10 穴。geoid / enu / datum は 4 層とも 0 件(埋まったらここが鳴る = 目的)。
    for stem in ("geoid", "enu", "datum", "ortho", "epoch", "crs", "utm",
                 "msl", "wgs84", "tokyo", "jgd"):
        assert len(fs.op_find(stem)) == 0, f"{stem} の op が増えた(嬉しい)"
        assert not [n for n in dir(fs) if stem in n.lower() and not n.startswith("_")], stem
    # ★``vertical`` だけは op_find が 5 件返す。**中身は 1 つも関係ない**
    #   (``boundary_vertices`` などの語幹一致)—— 件数で「在る」と言ってはいけない。
    assert not [r for r in fs.op_find("vertical") if "vertical" in r["op"].lower()]
    assert len(gap["have"]) == 6, gap["have"]

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print(f"\n所要 {time.perf_counter() - t0:.1f} s")
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
