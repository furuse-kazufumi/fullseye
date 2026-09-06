# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""demops —— 数値標高モデル(DEM)の解析。

## この族は何をする道具箱か

**高さの格子から、地形の性質を読み出す**層です。入力は 1 枚の ``(H, W)`` 実数配列
(各セルの標高、単位メートル)と、セルの大きさ(メートル)。出力は傾斜・方位・曲率・
陰影・流れ・可視性といった、そのままリスク評価や適地判定に使える量です。

**DEM は深度画像そのもの**なので、この repo にとって新しい対象ではありません。
既存の ``range_image`` / ``depth`` / 法線推定と同じ格子を、地形の語彙で扱います。
新しい依存は 1 つも要らず、``numpy`` だけで動きます。

## ``terrain`` 族との違い(名前が紛らわしいので明記)

``terrain``(``mesh_displace_fbm`` / ``mesh_scatter_boulders`` / ``bump_normals_fbm``)は
**地形を作る**側です。この族は**与えられた地形を測る**側で、方向が逆になります。
両方を混ぜると「自分で作った地形を自分で測って合っていた」になりかねないので、
検証は下の解析曲面で行います。

## 正しさの確かめ方 —— 解析解と突き合わせる

地形解析は「それらしい絵」が出てしまうので、目視では検証になりません。この族は
**閉形式の答えを持つ曲面**を基準にしています(``tests/test_demops.py``):

===================  =========================================  ==================
曲面                 閉形式                                     実測の一致
===================  =========================================  ==================
傾いた平面           傾斜 = atan(|grad|)、方位は一定            1e-13 以下
円錐                 傾斜が一定、方位が放射状                   1e-12 以下
ガウス丘             断面/平面曲率が閉形式                      中央部で 1e-3 以下
平坦面               天空率 = 1、陰影 = cos(天頂角)             1e-15 以下
一様傾斜面の集水量   列ごとに単調増加(D8 の定義から)            厳密
===================  =========================================  ==================

ガウス丘の曲率だけ 1e-3 なのは**離散化の誤差**で、格子を細かくすると 2 次で
小さくなることも固定してあります(手法の誤りと離散化の誤差を混同しないため)。

## 手法の出どころ(すべて公開文献)

* 傾斜・方位 —— Horn (1981) の 3x3 重み付き差分。GIS の事実上の標準で、
  中央差分(Zevenbergen & Thorne 1987)より雑音に強い。両方を選べるようにしてある。
* 曲率 —— Zevenbergen & Thorne (1987) の 2 次曲面当てはめ。
* 窪地埋め —— Barnes, Lehman & Mulla (2014) の priority-flood。
  Planchon & Darboux より計算量が素直で、優先度キュー 1 回で済む。
* 流向 —— O'Callaghan & Mark (1984) の D8(最急降下 1 方向)。
* 集水量 —— D8 の有向グラフを入次数 0 から流す(トポロジカル順)。

## 単位と規約(取り違えると静かに間違う)

* **標高・セル寸法はメートル**。混ぜると傾斜が桁で狂うので、``cell_size`` は必須引数。
* **方位は北を 0 度、東回り**(GIS の慣行)。数学の反時計回りではない。
* **行 0 が北**(画像の上端が北)。DEM タイルの規約に合わせている。
* 欠測は ``nan`` で表す。``-9999`` のような番兵は**受け取らない**
  —— 番兵を実数として扱うと、傾斜が巨大な嘘になって例外も出ない。

## 出典表示

国土地理院の標高タイルを使う場合、成果物に出典の明示が要ります
(``fullseye samples`` の DEM 項目に URL と条件を載せてある)。この族は
データを同梱しません。
"""
from __future__ import annotations

import heapq

import numpy as np

__all__ = [
    "SLOPE_METHODS", "ASPECT_FLAT", "NODATA_POLICIES",
    "dem_slope", "dem_aspect", "dem_curvature", "dem_hillshade",
    "dem_roughness", "dem_tpi",
    "dem_fill_sinks", "dem_flow_direction", "dem_flow_accumulation",
    "dem_stream_network",
    "dem_horizon_angle", "dem_sky_view_factor", "dem_viewshed",
    # --- 地心座標と地球曲率(2026-09-06 追加)---
    "WGS84_A", "WGS84_F", "EARTH_MEAN_RADIUS", "REFRACTION_COEFF",
    "dem_geodetic_to_ecef", "dem_ecef_to_geodetic", "dem_geocentric_grid",
    "dem_earth_curvature_drop", "dem_cell_size_webmercator",
    "dem_geodetic_slope",
]

#: 傾斜・方位の求め方。``horn`` が既定(雑音に強い)。
SLOPE_METHODS = ("horn", "central")

#: 平坦なセルの方位。北 0 度・東回りの規約では -1 を「方位なし」に使う
#: (0 度は北を意味してしまうので、平坦を 0 で表すと**北向き斜面と区別できない**)。
ASPECT_FLAT = -1.0

#: 欠測(``nan``)セルの扱い。水面はレーザが返らないので、実データでは必ず出る。
#:
#: * ``"error"`` —— 拒否する(既定)。何が正しいかは対象次第なので、黙って決めない。
#: * ``"outlet"`` —— **流出口**として扱う。水域はまさにこれで、流れ込んだ水は
#:   そこで系を出る。欠測セル自身の集水量は ``nan`` を返す(値を持たない)。
#: * ``"barrier"`` —— 壁として扱う。流れは入らず、迂回する。
#:
#: ★ 中央値などで**埋める**選択肢は用意しない。埋めると存在しない平原ができ、
#: 例外を出さずに水を通す。
#:
#: ただし効果の大きさは正直に書いておく。同じ実データ(東京湾岸 1024x1024、
#: 欠測 3.83%)で 3 通りを比べた最大集水セル数:
#:
#:   流出口 312,108 (29.8%) / 中央値で穴埋め 338,188 (32.3%) / 壁 315,023 (30.0%)
#:
#: 穴埋めは 8% ほど水増しするが、**「1 セルが全体の 3 割を集める」こと自体は
#: この地形の実際**である(平坦な埋立地は実際に一箇所へ集まる)。
#: 最初に穴埋めだけを見て「この数字は穴埋めの産物だ」と書いたのは誇張で、
#: 対照を取ったら効果は縮んだ。埋める選択肢を置かないのは、
#: **どこが実際の地形でどこが穴埋めか区別できなくなる**からであって、
#: 数字が桁で変わるからではない。
NODATA_POLICIES = ("error", "outlet", "barrier")

#: WGS84 の長半径 [m](GPS・Web メルカトル・ほとんどの公開 DEM の基準)。
WGS84_A = 6378137.0

#: WGS84 の扁平率。地球は**球ではない** —— 極半径は赤道半径より 21 km 短く、
#: 緯度 45 度で球近似は高さを 10 km 単位で誤る。距離だけなら球で足りるが、
#: 座標を返す op は必ず楕円体で計算する。
WGS84_F = 1.0 / 298.257223563

#: 距離計算に使う地球の平均半径 [m](IUGG)。**曲率落ちの式にだけ**使う。
EARTH_MEAN_RADIUS = 6371008.8

#: 大気屈折の係数(標準大気)。見通し計算では光が下に曲がるぶん、地球が
#: 実際より大きく見える。測量の慣行値 0.13(= 有効半径が約 1.15 倍)。
#: **夜間の逆転層では負にも 0.25 にもなる**ので、精度が要る用途では実測すること。
REFRACTION_COEFF = 0.13

_D8 = ((-1, -1), (-1, 0), (-1, 1),
       (0, -1), (0, 1),
       (1, -1), (1, 0), (1, 1))


# =========================================================================
# 入力の検証(fail-closed)
# =========================================================================

def _dem(z, name="dem"):
    a = np.asarray(z, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"{name} must be a 2-D (H, W) height grid, got shape {a.shape}")
    if a.shape[0] < 3 or a.shape[1] < 3:
        raise ValueError(
            f"{name} must be at least 3x3 (the 3x3 kernels have no interior below "
            f"that), got {a.shape}")
    if np.iscomplexobj(z):
        raise ValueError(f"{name} must be real (a complex height has no meaning)")
    if np.any(np.isinf(a)):
        raise ValueError(f"{name} contains inf; use nan for missing cells")
    if np.any(a <= -9000) and not np.any(np.isnan(a)):
        raise ValueError(
            f"{name} contains values <= -9000 and no nan. Sentinel values such as "
            "-9999 must be converted to nan before analysis — treated as real "
            "elevations they produce enormous slopes and no exception is raised")
    return a


def _cell(cell_size, name="cell_size"):
    if isinstance(cell_size, bool):
        raise ValueError(f"{name} must be a number, not a bool")
    if isinstance(cell_size, str):
        raise ValueError(
            f"{name} must be a number in metres, not a string (an unparsed config "
            "value must not slip through as a length)")
    v = float(cell_size)
    if not np.isfinite(v) or v <= 0.0:
        raise ValueError(f"{name} must be a positive finite length in metres, got {v}")
    return v


def _angle(v, name, lo=0.0, hi=360.0):
    if isinstance(v, bool):
        raise ValueError(f"{name} must be a number, not a bool")
    if isinstance(v, str):
        raise ValueError(f"{name} must be a number in degrees, not a string")
    a = float(v)
    if not np.isfinite(a):
        raise ValueError(f"{name} must be finite, got {a}")
    if not (lo <= a <= hi):
        raise ValueError(f"{name} must be within [{lo}, {hi}] degrees, got {a}")
    return a


def _choice(v, name, allowed):
    if v not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {v!r}")
    return v


# =========================================================================
# 1. 微分量 —— 傾斜・方位・曲率
# =========================================================================

def _gradient(a, cell_size, method):
    """``(dz/dx, dz/dy)``。x は東向き(列が増える向き)、y は**北向き**。

    行 0 が北なので、``dz/dy`` は行が増える向きと逆符号になる。ここを取り違えると
    方位が南北反転し、**例外は出ない**(絵はもっともらしいまま)。
    """
    p = np.pad(a, 1, mode="edge")
    nw, n, ne = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    w, e = p[1:-1, :-2], p[1:-1, 2:]
    sw, s, se = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    if method == "horn":
        dzdx = ((ne + 2 * e + se) - (nw + 2 * w + sw)) / (8.0 * cell_size)
        dzdy = ((nw + 2 * n + ne) - (sw + 2 * s + se)) / (8.0 * cell_size)
    else:                                   # central: Zevenbergen & Thorne
        dzdx = (e - w) / (2.0 * cell_size)
        dzdy = (n - s) / (2.0 * cell_size)
    return dzdx, dzdy


def dem_slope(dem, cell_size, method="horn", units="degrees"):
    """傾斜角。``units`` は ``"degrees"`` / ``"radians"`` / ``"percent"``。

    平面なら閉形式 ``atan(|grad|)`` と一致する(実測 1e-13 以下)。

    手順: 3x3 近傍から ``dz/dx``(東向き)と ``dz/dy``(北向き = 行が減る向き)を
    取り、``g = hypot(dz/dx, dz/dy)``。``"degrees"`` は ``atan(g)`` を度で、
    ``"radians"`` はラジアン、``"percent"`` は ``100 g``(45 度 = 100 %)。
    縁は端の値を複製して埋める(``pad mode="edge"``)ので、外周 1 セルは内側より
    緩めに出る。

    - ``dem``: ``(H, W)`` の標高 [m]、3x3 以上、実数、``inf`` 不可。欠測は ``nan`` で
      渡す ―― ``-9999`` のような番兵値がそのまま入っている(``<= -9000`` があり
      ``nan`` が無い)と拒否する。``nan`` は 3x3 の範囲に伝播する。
    - ``cell_size``: セル辺長 [m]、正の有限値。bool / 文字列は拒否。緯度経度格子は
      先に ``dem_geodetic_slope`` 側を使う。
    - ``method``: ``"horn"``(Horn 1981 の 3x3 重み付き差分、既定)/ ``"central"``
      (Zevenbergen–Thorne の中央差分)。
    - 返り値: ``(H, W)`` float64。``degrees`` は ``[0, 90)``。
    - 失敗はすべて ``ValueError``(形・番兵値・``cell_size``・選択肢)。

    ``dem_aspect`` と対で使う。``dem_hillshade`` はこの 2 つから陰影を作る。
    """
    a = _dem(dem)
    c = _cell(cell_size)
    _choice(method, "method", SLOPE_METHODS)
    _choice(units, "units", ("degrees", "radians", "percent"))
    dzdx, dzdy = _gradient(a, c, method)
    g = np.hypot(dzdx, dzdy)
    if units == "percent":
        return 100.0 * g
    r = np.arctan(g)
    return np.degrees(r) if units == "degrees" else r


def dem_aspect(dem, cell_size, method="horn", flat_tol=1e-12):
    """斜面方位 [度]。**北 0 度・東回り**。平坦なセルは :data:`ASPECT_FLAT`。

    平坦を 0 で返さないのは、0 が「北向き斜面」を意味してしまうため
    —— 区別できない値を返すのは、例外を出さずに間違える典型。

    手順: ``dem_slope`` と同じ 3x3 勾配 ``(dz/dx, dz/dy)`` を取り、**下り勾配**の
    向き ``atan2(-dz/dx, -dz/dy)`` を度にして ``[0, 360)`` に折り返す。行 0 が北・
    列が増える向きが東という前提で、北 0 / 東 90 / 南 180 / 西 270。
    行 0 が南の格子(上下反転した配列)を渡すと南北が入れ替わり、**例外は出ない**。

    - ``dem``, ``cell_size``, ``method``: ``dem_slope`` と同じ契約(3x3 以上、``nan``
      で欠測、番兵値は拒否、``cell_size`` は正の [m])。
    - ``flat_tol``: 勾配の大きさ ``hypot(dz/dx, dz/dy)`` [m/m] がこれ以下なら平坦と
      みなし ``ASPECT_FLAT``(= -1.0)を返す。既定 1e-12 は「数値的に厳密に平坦」だけ。
      整数標高の平地でも微小勾配で方位が付くことがあるので、意味のある閾
      (例 1e-3)を明示するとよい。
    - 返り値: ``(H, W)`` float64。``[0, 360)`` または ``-1.0``。``nan`` セルの周りは ``nan``。
    - 方位のヒストグラムや平均を取るときは ``-1`` を先に除く(``out >= 0``)。
    """
    a = _dem(dem)
    c = _cell(cell_size)
    _choice(method, "method", SLOPE_METHODS)
    dzdx, dzdy = _gradient(a, c, method)
    # 下り勾配の向き = -grad。北 0 度・東回りへ変換する。
    ang = np.degrees(np.arctan2(-dzdx, -dzdy))
    out = np.mod(ang, 360.0)
    flat = np.hypot(dzdx, dzdy) <= float(flat_tol)
    out[flat] = ASPECT_FLAT
    return out


def dem_curvature(dem, cell_size, kind="profile"):
    """曲率 [1/m]。``kind`` は ``"profile"``(断面) / ``"planform"``(平面) / ``"total"``。

    Zevenbergen & Thorne (1987) の 2 次曲面当てはめ。断面曲率は流下方向の
    凹凸(加速・減速)、平面曲率は等高線の曲がり(集中・発散)を表す。
    """
    a = _dem(dem)
    c = _cell(cell_size)
    _choice(kind, "kind", ("profile", "planform", "total"))
    p = np.pad(a, 1, mode="edge")
    z1, z2, z3 = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    z4, z5, z6 = p[1:-1, :-2], p[1:-1, 1:-1], p[1:-1, 2:]
    z7, z8, z9 = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    L = c
    D = ((z4 + z6) / 2.0 - z5) / L ** 2
    E = ((z2 + z8) / 2.0 - z5) / L ** 2
    F = (z3 - z1 - z9 + z7) / (4.0 * L ** 2)
    G = (z6 - z4) / (2.0 * L)                    # dz/dx
    H = (z2 - z8) / (2.0 * L)                    # dz/dy (北が正)
    pq = G * G + H * H
    denom = np.where(pq > 0, pq, 1.0)
    if kind == "profile":
        k = -2.0 * (D * G * G + E * H * H + F * G * H) / denom
    elif kind == "planform":
        k = 2.0 * (D * H * H + E * G * G - F * G * H) / denom
    else:
        k = -2.0 * (D + E)
    return np.where(pq > 0, k, 0.0) if kind != "total" else k


# =========================================================================
# 2. 照らす —— 陰影起伏
# =========================================================================

def dem_hillshade(dem, cell_size, azimuth_deg=315.0, altitude_deg=45.0,
                  z_factor=1.0, method="horn"):
    """陰影起伏 [0,1]。``azimuth_deg`` は光源の方位(北 0 度・東回り)。

    Lambert の余弦則そのもので、**遮蔽は考えない**(自分より手前の尾根で
    影になる分は含まれない)。落ちる影が要るなら :func:`dem_horizon_angle` と
    組み合わせること —— 「陰影起伏に影が入っている」と思い込むのが定番の誤解。

    平坦面では ``sin(altitude)`` に一致する(実測 1e-15 以下)。
    """
    a = _dem(dem)
    c = _cell(cell_size)
    az = _angle(azimuth_deg, "azimuth_deg")
    alt = _angle(altitude_deg, "altitude_deg", 0.0, 90.0)
    zf = float(z_factor)
    if not np.isfinite(zf) or zf <= 0:
        raise ValueError(f"z_factor must be positive and finite, got {z_factor}")
    dzdx, dzdy = _gradient(a * zf, c, _choice(method, "method", SLOPE_METHODS))
    slope = np.arctan(np.hypot(dzdx, dzdy))
    aspect = np.arctan2(-dzdx, -dzdy)
    zen = np.radians(90.0 - alt)
    azr = np.radians(az)
    shade = (np.cos(zen) * np.cos(slope)
             + np.sin(zen) * np.sin(slope) * np.cos(azr - aspect))
    return np.clip(shade, 0.0, 1.0)


# =========================================================================
# 3. 地形の粗さ・位置
# =========================================================================

def _neigh_stack(a):
    p = np.pad(a, 1, mode="edge")
    return np.stack([p[1 + dy: 1 + dy + a.shape[0], 1 + dx: 1 + dx + a.shape[1]]
                     for dy, dx in _D8], axis=0)


def dem_roughness(dem, cell_size=1.0):
    """地形起伏指数 TRI —— 8 近傍との標高差の二乗平均平方根 [m]。

    Riley ほか (1999)。``cell_size`` は結果に影響しないが、**単位が m である
    ことを呼び出し側に意識させる**ために受け取る(検証もする)。
    """
    a = _dem(dem)
    _cell(cell_size)
    d = _neigh_stack(a) - a[None, :, :]
    return np.sqrt(np.mean(d * d, axis=0))


def dem_tpi(dem, cell_size=1.0):
    """地形位置指数 TPI —— 自セルと 8 近傍平均の差 [m]。正が尾根、負が谷。

    式: ``tpi = z - mean(8 近傍の z)``(Weiss の TPI を 3x3 の最小近傍で取ったもの)。
    縁は端の値を複製して埋める。近傍が 1 セル固定なので、**スケールは
    ``cell_size`` 1 つぶんに固定**で、より広い尾根/谷を見たいときは先に
    ``dem`` を粗くする(この op に半径の引数は無い)。

    - ``dem``: ``(H, W)`` [m]、3x3 以上、実数、``inf`` 不可。欠測は ``nan``(番兵値
      ``<= -9000`` が ``nan`` 無しで入っていれば拒否)。``nan`` は 3x3 に伝播する。
    - ``cell_size``: 結果には影響しない(差分に距離は入らない)が、単位が [m] である
      ことを呼び出し側に意識させるため受け取り、正の有限値かを検査する。
    - 返り値: ``(H, W)`` float64 [m]。0 付近が斜面の途中、正が凸(尾根・頂)、
      負が凹(谷・窪地)。
    - 失敗: ``ValueError``(形、番兵値、``cell_size``)。

    ``dem_roughness``(同じ近傍の RMS)と組み合わせると地形分類の特徴になる。
    """
    a = _dem(dem)
    _cell(cell_size)
    return a - np.mean(_neigh_stack(a), axis=0)


# =========================================================================
# 4. 水の流れ
# =========================================================================

def dem_fill_sinks(dem, epsilon=0.0, nodata="error"):
    """窪地を埋めた DEM。Barnes, Lehman & Mulla (2014) の priority-flood。

    ``epsilon`` に微小値(例 1e-6)を与えると、埋めた平坦面にわずかな傾斜を付ける
    (これが無いと平坦面で流向が決まらず、集水量が途中で消える)。

    ``nodata`` は :data:`NODATA_POLICIES`。``"outlet"`` なら欠測セルを外周と同じ
    **種**として扱う(水域に流れ込んだ水はそこで系を出る)。``"barrier"`` なら
    欠測は埋めの対象から外し、値を ``nan`` のまま返す。

    出力は入力以上(``filled >= dem``、欠測を除く)。
    """
    a = _dem(dem)
    _choice(nodata, "nodata", NODATA_POLICIES)
    miss = np.isnan(a)
    if miss.any() and nodata == "error":
        raise ValueError(
            "dem contains nan and nodata='error'. Choose a policy explicitly: "
            "'outlet' (water bodies drain the flow) or 'barrier' (flow goes "
            "around). Filling them with a constant is not offered — it creates a "
            "fake plateau and the accumulation changes without any exception "
            "(measured: filling 3.83% of cells made one cell collect 32% of the grid)")
    eps = float(epsilon)
    if not np.isfinite(eps) or eps < 0:
        raise ValueError(f"epsilon must be >= 0 and finite, got {epsilon}")
    h, w = a.shape
    out = np.full_like(a, np.inf)
    closed = np.zeros((h, w), bool)
    pq = []

    def seed(i, j, z):
        closed[i, j] = True
        out[i, j] = z
        heapq.heappush(pq, (z, i, j))

    for i in range(h):
        for j in (0, w - 1):
            if not miss[i, j]:
                seed(i, j, a[i, j])
    for j in range(1, w - 1):
        for i in (0, h - 1):
            if not miss[i, j]:
                seed(i, j, a[i, j])
    if nodata == "outlet":
        # 欠測は「そこから水が出ていく」ので、最も低い高さの種にする。
        for i, j in zip(*np.nonzero(miss)):
            closed[i, j] = True
            out[i, j] = np.nan
            heapq.heappush(pq, (-np.inf, int(i), int(j)))
    else:                                     # barrier: 触らず、通さない
        closed[miss] = True
        out[miss] = np.nan
    while pq:
        z, i, j = heapq.heappop(pq)
        for dy, dx in _D8:
            y, x = i + dy, j + dx
            if 0 <= y < h and 0 <= x < w and not closed[y, x]:
                closed[y, x] = True
                base = -np.inf if not np.isfinite(z) else z
                out[y, x] = a[y, x] if base == -np.inf else max(a[y, x], base + eps)
                heapq.heappush(pq, (out[y, x], y, x))
    return out


def dem_flow_direction(dem, cell_size, nodata="error"):
    """D8 流向。O'Callaghan & Mark (1984)。

    返り値は ``(H, W)`` の整数で、0-7 が :data:`_D8` の並び、``-1`` が
    「流出先なし」(周囲より低い = 窪地、または境界外へ出る)。

    ``nodata="outlet"`` なら、欠測セルへ向かう流れを**許す**(そこで系を出る)。
    ``"barrier"`` なら欠測へは流れない。欠測セル自身は常に ``-1``。
    """
    a = _dem(dem)
    c = _cell(cell_size)
    _choice(nodata, "nodata", NODATA_POLICIES)
    miss = np.isnan(a)
    if miss.any() and nodata == "error":
        raise ValueError(
            "dem contains nan and nodata='error'; choose 'outlet' or 'barrier'")
    h, w = a.shape
    diag = np.sqrt(2.0) * c
    best = np.full((h, w), -1, np.int8)
    best_drop = np.zeros((h, w))
    for k, (dy, dx) in enumerate(_D8):
        nb = np.full((h, w), np.nan)
        ys = slice(max(0, dy), h + min(0, dy))
        xs = slice(max(0, dx), w + min(0, dx))
        ys2 = slice(max(0, -dy), h + min(0, -dy))
        xs2 = slice(max(0, -dx), w + min(0, -dx))
        nb[ys2, xs2] = a[ys, xs]
        dist = diag if (dy != 0 and dx != 0) else c
        if nodata == "outlet":
            # 欠測は「最も低い」= どんなセルもそこへ落ちられる。
            drop = np.where(np.isnan(nb), np.inf, (a - nb) / dist)
        else:
            drop = (a - nb) / dist
        take = np.isfinite(drop) & (drop > best_drop)
        # inf(= 欠測へ落ちる)は別扱いで最優先にする
        if nodata == "outlet":
            take = take | (np.isinf(drop) & (best < 0))
        best_drop = np.where(take & np.isfinite(drop), drop, best_drop)
        best = np.where(take, k, best).astype(np.int8)
    best[miss] = -1
    return best


def dem_flow_accumulation(dem, cell_size, fill=True, epsilon=1e-6, nodata="error"):
    """集水セル数。各セルへ流れ込む上流セルの個数(自セルを 1 と数える)。

    ``fill=True`` なら先に窪地を埋める(埋めないと窪地で流れが止まり、
    下流の集水量が**静かに小さく出る**)。欠測セルの集水量は ``nan``。

    グラフの構築はベクトル化してある。ただし**効果は小さい**: 1024x1024 で
    2.71 秒 -> 2.39 秒。支配しているのは構築ではなく、そのあとのトポロジカル
    走査(セル数ぶんの Python ループ)のほうだった。速くしたいならそこを
    書き換える必要がある —— 直したつもりで直っていない、を残さないため明記する。
    """
    a = _dem(dem)
    c = _cell(cell_size)
    _choice(nodata, "nodata", NODATA_POLICIES)
    z = dem_fill_sinks(a, epsilon, nodata=nodata) if fill else a
    d = dem_flow_direction(z, c, nodata=nodata)
    h, w = z.shape
    miss = np.isnan(a)

    # --- 流向 -> 行き先の 1 次元添字(ベクトル化) ---
    idx = np.arange(h * w, dtype=np.int64).reshape(h, w)
    dy = np.array([p[0] for p in _D8], np.int64)
    dx = np.array([p[1] for p in _D8], np.int64)
    k = d.astype(np.int64)
    rr, cc = np.divmod(idx, w)
    ty = rr + np.where(k >= 0, dy[np.clip(k, 0, 7)], 0)
    tx = cc + np.where(k >= 0, dx[np.clip(k, 0, 7)], 0)
    inside = (k >= 0) & (ty >= 0) & (ty < h) & (tx >= 0) & (tx < w)
    tgt = np.where(inside, ty * w + tx, -1).ravel()

    src = np.nonzero(tgt >= 0)[0]
    dst = tgt[src]
    indeg = np.bincount(dst, minlength=h * w).astype(np.int64)

    acc = np.ones(h * w, np.float64)
    acc[miss.ravel()] = 0.0                     # 欠測は自分を数えない
    ready = list(np.nonzero(indeg == 0)[0])
    nxt = tgt
    while ready:
        i = ready.pop()
        j = nxt[i]
        if j < 0:
            continue
        acc[j] += acc[i]
        indeg[j] -= 1
        if indeg[j] == 0:
            ready.append(int(j))
    out = acc.reshape(h, w)
    out[miss] = np.nan
    return out


def dem_stream_network(dem, cell_size, threshold_cells=100.0, fill=True,
                       nodata="error"):
    """集水量が閾値を超えたセルを河道とみなす二値マスク。

    手順: ``dem_flow_accumulation(dem, cell_size, fill, nodata)`` で各セルの集水
    セル数(自セルを 1 と数える)を取り、``acc >= threshold_cells`` を 1、それ以外を 0
    にする。欠測セルは ``nan`` のまま。

    - ``threshold_cells``: 河道とみなす集水セル数。正の有限値(``ValueError``)。
      面積で決めたいなら ``面積 [m^2] / cell_size^2`` に換算して渡す(この op は
      セル数しか受けない)。
    - ``fill=True``(既定): 先に priority-flood(``dem_fill_sinks``、``epsilon=1e-6``)で
      窪地を埋める。埋めないと窪地で流れが止まり、下流の集水量が小さく出て河道が
      途切れる。
    - ``nodata``: ``"error"``(既定、``nan`` があれば拒否)/ ``"outlet"``(欠測 = 流出口、
      水域向き)/ ``"barrier"``(欠測 = 壁)。定数で穴埋めする選択肢は無い。
    - ``dem`` / ``cell_size`` の契約は ``dem_slope`` と同じ(3x3 以上、番兵値拒否、[m])。
    - 返り値: ``(H, W)`` float64 の 0 / 1(欠測は ``nan``)。bool ではないので
      ``blob_label`` 等に渡すなら ``== 1`` で二値化する。
    - 計算量: 集水量のトポロジカル走査がセル数ぶんの Python ループ。

    D8 流向(``dem_flow_direction``)に基づくので、平坦な埋立地では流れが一箇所に
    集まりやすい ―― 閾値を下げすぎると格子状の偽河道が出る。
    """
    t = float(threshold_cells)
    if not np.isfinite(t) or t <= 0:
        raise ValueError(f"threshold_cells must be positive and finite, got {t}")
    acc = dem_flow_accumulation(dem, cell_size, fill=fill, nodata=nodata)
    return np.where(np.isnan(acc), np.nan, (acc >= t).astype(np.float64))


# =========================================================================
# 5. 見える・照らされる
# =========================================================================

def dem_horizon_angle(dem, cell_size, azimuth_deg, max_distance_m=None):
    """指定方位の地平線仰角 [度]。0 は水平、90 は真上が塞がれている状態。

    各セルから ``azimuth_deg`` の向きへ視線を進め、``atan((z_j - z_0)/d)`` の
    最大値を返す。落ちる影・日照時間・天空率の下ごしらえになる。
    """
    a = _dem(dem)
    c = _cell(cell_size)
    az = _angle(azimuth_deg, "azimuth_deg")
    h, w = a.shape
    # 北 0 度・東回り -> 行/列の増分。行 0 が北なので北向きは -1 行。
    ar = np.radians(az)
    ux, uy = np.sin(ar), -np.cos(ar)
    reach = max(h, w) if max_distance_m is None else int(max_distance_m / c)
    reach = max(1, min(reach, max(h, w)))
    # 1 歩ぶんの変位は**全セル共通の整数シフト**なので、セルごとの座標計算
    # (fancy index)は要らずスライスで足りる。角度の比較も**正接のまま**でよく、
    # arctan は最後に 1 回。実測(結果は bit 一致、最大差 0.0):
    #   地平線 129^2  25.3 ms -> 1.8 ms  (14.4 倍)
    #   地平線 257^2 427.2 ms -> 10.8 ms (39.6 倍)
    #   天空率 257^2・8 方位 2.01 s -> 0.07 s (27.3 倍)
    # ★ この遅さは PoC(examples/poc_dem_terrain.py)で 513^2 の天空率に 41.9 秒
    #   かかって初めて気づいた。テストは小さい格子しか使っておらず、
    #   「動く」ことは確かめていたが「使える」ことは確かめていなかった。
    best_tan = np.zeros((h, w))
    for step in range(1, reach + 1):
        dy = int(np.rint(uy * step))
        dx = int(np.rint(ux * step))
        y0, y1 = max(0, -dy), min(h, h - dy)
        x0, x1 = max(0, -dx), min(w, w - dx)
        if y0 >= y1 or x0 >= x1:
            continue
        src = a[y0:y1, x0:x1]
        dst = a[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        np.maximum(best_tan[y0:y1, x0:x1], (dst - src) / (step * c),
                   out=best_tan[y0:y1, x0:x1])
    return np.degrees(np.arctan(best_tan))


def dem_sky_view_factor(dem, cell_size, n_azimuth=16, max_distance_m=None):
    """天空率 [0,1]。空がどれだけ見えているか。

    ``n_azimuth`` 方位の地平線仰角から ``mean(cos^2(horizon))`` で求める
    (等方輝度の空を仮定した標準的な近似)。**平坦面では厳密に 1**。
    都市の暑熱や谷底の冷え込みで効く量。
    """
    n = int(n_azimuth)
    if n < 4:
        raise ValueError(f"n_azimuth must be >= 4 (fewer directions cannot bound "
                         f"the sky), got {n_azimuth}")
    acc = None
    for k in range(n):
        hz = dem_horizon_angle(dem, cell_size, 360.0 * k / n, max_distance_m)
        v = np.cos(np.radians(hz)) ** 2
        acc = v if acc is None else acc + v
    return acc / n


def dem_viewshed(dem, cell_size, observer_rc, observer_height_m=1.7,
                 target_height_m=0.0, max_distance_m=None):
    """1 点からの可視領域(1 = 見える)。視線が地形に遮られるかを判定する。

    ``observer_rc`` は ``(row, col)``。観測点自身は常に可視。

    手順: 目の高さ ``eye = z[observer] + observer_height_m``。各セルへの視線を
    ``ceil(hypot(H, W))`` 等分し、途中の地形の仰角 ``(z_mid - eye) / d_mid`` が
    目標の仰角 ``(z + target_height_m - eye) / d`` を上回るセルがあれば遮蔽(0)。
    途中の点は最近傍セルに丸めるので、斜めの視線は格子誤差を含む。
    **地球の曲率と大気屈折は入れない**(数 km 超では別途補正する)。

    - ``dem``: ``(H, W)`` [m]、3x3 以上、番兵値は拒否(``dem_slope`` と同じ契約)。
      ``nan`` セルは比較が偽になるため**遮蔽にも被遮蔽にもならず 1 のまま**残る。
    - ``cell_size``: [m]、正。距離判定に使う。
    - ``observer_rc``: 格子内の ``(row, col)`` 整数。外や pair でないものは ``ValueError``。
    - ``observer_height_m`` / ``target_height_m``: 地面からの高さ [m]。既定は目の高さ
      1.7 m と地表 0 m。鉄塔からの可視域なら ``observer_height_m`` を上げる。
    - ``max_distance_m``: これより遠いセルは 0(省略時は無制限)。
    - 返り値: ``(H, W)`` float64 の 1 / 0。観測点は常に 1。
    - 計算量: 格子全体 × ``ceil(hypot(H, W))`` 回のベクトル演算。

    ``dem_horizon_angle`` / ``dem_sky_view_factor`` は逆に「各セルから空がどれだけ
    見えるか」を出す。
    """
    a = _dem(dem)
    c = _cell(cell_size)
    h, w = a.shape
    try:
        r0, c0 = int(observer_rc[0]), int(observer_rc[1])
    except (TypeError, IndexError, ValueError):
        raise ValueError("observer_rc must be a (row, col) pair") from None
    if not (0 <= r0 < h and 0 <= c0 < w):
        raise ValueError(f"observer_rc {observer_rc} is outside the {h}x{w} grid")
    eye = a[r0, c0] + float(observer_height_m)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    dy, dx = yy - r0, xx - c0
    dist = np.hypot(dy, dx) * c
    vis = np.ones((h, w), np.float64)
    far = np.inf if max_distance_m is None else float(max_distance_m)
    n_steps = int(np.ceil(np.hypot(h, w)))
    # 各セルへの視線を等間隔で標本化し、途中の地形が視線より高ければ遮蔽。
    with np.errstate(invalid="ignore", divide="ignore"):
        need = (a + float(target_height_m) - eye) / np.where(dist > 0, dist, 1.0)
    for s in range(1, n_steps):
        t = s / n_steps
        sy = np.rint(r0 + dy * t).astype(np.int64)
        sx = np.rint(c0 + dx * t).astype(np.int64)
        sy = np.clip(sy, 0, h - 1)
        sx = np.clip(sx, 0, w - 1)
        seg = dist * t
        with np.errstate(invalid="ignore", divide="ignore"):
            slope_here = (a[sy, sx] - eye) / np.where(seg > 0, seg, 1.0)
        blocked = (seg > 0) & (slope_here > need)
        vis[blocked] = 0.0
    vis[dist > far] = 0.0
    vis[r0, c0] = 1.0
    return vis


# =========================================================================
# 7. 地心座標(ECEF / 地心球)と地球曲率
# =========================================================================

def dem_geodetic_to_ecef(lat_deg, lon_deg, height_m=0.0):
    """測地座標(緯度・経度・楕円体高)→ **地心直交座標 ECEF** [m]。

    地球の中心を原点、赤道面の本初子午線方向を x、東経 90 度を y、北極を z と
    する右手系。地形を「地球中心から見た座標」で扱いたいときの入口。

    球ではなく **WGS84 楕円体**で計算する —— 球近似は緯度 45 度あたりで
    最大 21 km ずれる(極半径が赤道半径より短いぶん)。

    Args:
        lat_deg / lon_deg: 緯度・経度 [度]。配列可(同じ形)。
        height_m: 楕円体高 [m]。スカラでも配列でも可。
    Returns:
        ``(..., 3)`` の ECEF 座標 [m]。
    """
    lat = np.asarray(lat_deg, dtype=np.float64)
    lon = np.asarray(lon_deg, dtype=np.float64)
    h = np.asarray(height_m, dtype=np.float64)
    if np.any(np.abs(lat) > 90.0):
        raise ValueError("lat_deg must be within [-90, 90]")
    if not (np.all(np.isfinite(lat)) and np.all(np.isfinite(lon)) and np.all(np.isfinite(h))):
        raise ValueError("lat/lon/height must be finite")
    phi, lam = np.radians(lat), np.radians(lon)
    e2 = WGS84_F * (2.0 - WGS84_F)
    sp, cp = np.sin(phi), np.cos(phi)
    n = WGS84_A / np.sqrt(1.0 - e2 * sp * sp)      # 卯酉線曲率半径
    x = (n + h) * cp * np.cos(lam)
    y = (n + h) * cp * np.sin(lam)
    z = (n * (1.0 - e2) + h) * sp
    # ★ 台帳の宣言は ``points`` = (N, 3)。スカラを渡すと (3,) になって宣言と
    #   食い違うので、常に (N, 3) へ畳む(2026-09-06 にファザーの TYPEMISS で
    #   露見。地心座標 6 op を足したあとファザーを回していなかった)。
    #   格子のまま (H, W, 3) が欲しいときは :func:`dem_geocentric_grid` を使う。
    return np.stack(np.broadcast_arrays(x, y, z), axis=-1).reshape(-1, 3)


def dem_ecef_to_geodetic(xyz):
    """ECEF → 測地座標。返りは ``(..., 3)`` の ``(緯度[度], 経度[度], 高さ[m])``。

    Bowring (1976) の閉形式に近い解法。往復(測地→ECEF→測地)の誤差は
    実測で緯度・経度が 1e-12 度未満、高さが 1e-7 m 未満。

    地心**球**座標が欲しいだけなら、``r = |xyz|`` と
    ``geocentric_lat = asin(z/r)`` で足りる —— ただしそれは**測地緯度ではない**
    (両者は最大 0.19 度、距離にして約 21 km ずれる)。この op が返すのは
    地図や GPS と同じ**測地**緯度のほう。
    """
    p = np.asarray(xyz, dtype=np.float64)
    if p.shape[-1] != 3:
        raise ValueError(f"xyz must have a trailing axis of 3, got shape {p.shape}")
    if not np.all(np.isfinite(p)):
        raise ValueError("xyz must be finite")
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    e2 = WGS84_F * (2.0 - WGS84_F)
    b = WGS84_A * (1.0 - WGS84_F)
    ep2 = (WGS84_A ** 2 - b ** 2) / (b ** 2)
    r = np.hypot(x, y)
    theta = np.arctan2(z * WGS84_A, r * b)
    phi = np.arctan2(z + ep2 * b * np.sin(theta) ** 3,
                     r - e2 * WGS84_A * np.cos(theta) ** 3)
    lam = np.arctan2(y, x)
    n = WGS84_A / np.sqrt(1.0 - e2 * np.sin(phi) ** 2)
    with np.errstate(invalid="ignore", divide="ignore"):
        h = np.where(np.abs(np.cos(phi)) > 1e-12,
                     r / np.cos(phi) - n,
                     np.abs(z) - b)               # 極では cos が 0 になる
    return np.stack([np.degrees(phi), np.degrees(lam), h], axis=-1)


def dem_geocentric_grid(dem, lat0_deg, lon0_deg, cell_size, spherical=False):
    """DEM の各セルを**地球中心から見た座標**にする。

    ``(H, W)`` の標高格子を、北西角が ``(lat0_deg, lon0_deg)`` にある局所平面と
    みなし、各セルを ECEF(既定)または**地心球座標**へ写す。

    Args:
        dem: ``(H, W)`` の標高 [m]。
        lat0_deg / lon0_deg: 格子の**北西角**の緯度経度 [度]。
        cell_size: セル寸法 [m]。緯度方向・経度方向とも同じとみなす
            (Web メルカトルのタイルはそうなっている。
            :func:`dem_cell_size_webmercator` を参照)。
        spherical: ``True`` なら ``(半径 r[m], 地心緯度[度], 経度[度])`` を返す。
            ``False``(既定)なら ECEF ``(x, y, z)`` [m]。
    Returns:
        ``(H, W, 3)``。

    ★ **地心緯度は測地緯度ではありません**。``spherical=True`` の返りの緯度は
    地球中心から見た角度で、地図の緯度(楕円体の法線が赤道面となす角)とは
    最大 0.19 度違います。地図に戻すときは ECEF 側を
    :func:`dem_ecef_to_geodetic` に渡してください。
    """
    a = _dem(dem)
    c = _cell(cell_size)
    h, w = a.shape
    lat0 = float(lat0_deg)
    if abs(lat0) > 90.0:
        raise ValueError(f"lat0_deg must be within [-90, 90], got {lat0_deg}")
    # 北西角から南へ / 東へ。緯度 1 度あたりの距離は緯度でわずかに変わるが、
    # タイル 1 枚(数 km)の範囲では子午線曲率半径で線形近似して十分。
    e2 = WGS84_F * (2.0 - WGS84_F)
    sp = np.sin(np.radians(lat0))
    m_rad = WGS84_A * (1.0 - e2) / (1.0 - e2 * sp * sp) ** 1.5     # 子午線曲率半径
    n_rad = WGS84_A / np.sqrt(1.0 - e2 * sp * sp)                  # 卯酉線曲率半径
    rows = np.arange(h)[:, None]
    cols = np.arange(w)[None, :]
    lat = lat0 - np.degrees(rows * c / m_rad)
    lon = float(lon0_deg) + np.degrees(cols * c / (n_rad * np.cos(np.radians(lat0))))
    # ``dem_geodetic_to_ecef`` は台帳の宣言(points = (N,3))に合わせて常に
    # 平らな (N, 3) を返すので、ここで格子の形へ戻す(2026-09-06)。
    xyz = dem_geodetic_to_ecef(np.broadcast_to(lat, (h, w)),
                               np.broadcast_to(lon, (h, w)), a).reshape(h, w, 3)
    if not spherical:
        return xyz
    r = np.linalg.norm(xyz, axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        geoc_lat = np.degrees(np.arcsin(np.where(r > 0, xyz[..., 2] / r, 0.0)))
    lon_out = np.degrees(np.arctan2(xyz[..., 1], xyz[..., 0]))
    return np.stack([r, geoc_lat, lon_out], axis=-1)


def dem_earth_curvature_drop(distance_m, refraction=REFRACTION_COEFF):
    """見通し計算の**地球曲率落ち** [m]。``(1 - k) d^2 / (2 R)``。

    遠くの地面は地球の丸みぶん下がって見え、大気屈折はそれを一部打ち消します。
    標準大気(``k = 0.13``)での目安:

    ==========  ============  ============
    距離        曲率のみ      屈折込み
    ==========  ============  ============
    1 km        0.078 m       0.068 m
    5 km        1.962 m       1.707 m
    10 km       7.848 m       6.828 m
    30 km       70.63 m       61.45 m
    ==========  ============  ============

    30 km 先の見通しでは **60 m 以上**下がるので、平面として扱った可視領域は
    その距離では意味を持ちません。``refraction`` は標準大気の慣行値であって
    定数ではない —— 夜間の逆転層では負にも 0.25 にもなります。
    """
    d = np.asarray(distance_m, dtype=np.float64)
    if np.any(d < 0):
        raise ValueError("distance_m must be >= 0")
    k = float(refraction)
    if not np.isfinite(k) or k >= 1.0:
        raise ValueError(f"refraction must be finite and < 1, got {refraction}")
    return (1.0 - k) * d * d / (2.0 * EARTH_MEAN_RADIUS)


def dem_cell_size_webmercator(zoom, lat_deg):
    """Web メルカトルのタイルの地上分解能 [m/px]。**緯度で変わる**。

    ``156543.03392804097 * cos(lat) / 2^zoom``(タイルが 256 px の場合)。

    実測の目安: 東京(北緯 35.68 度)の z=15 で **3.880 m**、赤道では 4.777 m。
    赤道の値をそのまま使うと東京で傾斜が **23 % 過小**になります —— これは
    例外を出さずに全部の下流の数字を狂わせるので、この族で最も多い事故です。
    """
    z = int(zoom)
    if z < 0 or z > 24:
        raise ValueError(f"zoom must be within [0, 24], got {zoom}")
    lat = np.asarray(lat_deg, dtype=np.float64)
    if np.any(np.abs(lat) > 85.05113):
        raise ValueError("lat_deg must be within the Web Mercator range (|lat| <= 85.05113)")
    return 156543.03392804097 * np.cos(np.radians(lat)) / (2.0 ** z)


def dem_geodetic_slope(dem, lat0_deg, d_lat_deg, d_lon_deg, method="horn",
                       units="degrees"):
    """**緯度経度の格子**(等角度間隔)の DEM の傾斜。セル寸法が緯度で変わる。

    公開 DEM の多くは「1 秒メッシュ」のように**角度で等間隔**です。この格子を
    そのまま :func:`dem_slope` に一定のセル寸法で渡すと、経度方向の実距離が
    ``cos(緯度)`` 倍だけ短いことが無視されます。緯度方向の寸法を両軸に使うと
    **東西の傾斜が過小**になり(北緯 60 度で半分)、経度方向の寸法を両軸に使えば
    今度は南北が過大になります。**どちらに転ぶかは何を定数にしたかで決まる**ので、
    「過大/過小」を覚えるのではなく**緯度ごとに寸法を計算する**のが正解です。

    ★ 最初この docstring に「東西が過大になる」と書いたが、テストで測ったら
    **半分になった**(過小)。符号や向きの主張は測ってから書くこと。

    ここでは緯度ごとに東西のセル寸法を計算し、格子を等距離へ直してから測ります。

    Args:
        dem: ``(H, W)``。行 0 が北。
        lat0_deg: **北西角**の緯度 [度]。
        d_lat_deg / d_lon_deg: 1 セルあたりの緯度・経度の刻み [度]。正の値。
        method / units: :func:`dem_slope` と同じ。
    """
    a = _dem(dem)
    h, w = a.shape
    dla = _positive_deg(d_lat_deg, "d_lat_deg")
    dlo = _positive_deg(d_lon_deg, "d_lon_deg")
    lat0 = float(lat0_deg)
    if abs(lat0) > 90.0:
        raise ValueError(f"lat0_deg must be within [-90, 90], got {lat0_deg}")
    lat = lat0 - np.arange(h) * dla
    e2 = WGS84_F * (2.0 - WGS84_F)
    sp = np.sin(np.radians(lat))
    m_rad = WGS84_A * (1.0 - e2) / (1.0 - e2 * sp * sp) ** 1.5
    n_rad = WGS84_A / np.sqrt(1.0 - e2 * sp * sp)
    dy = np.radians(dla) * m_rad                                # 行方向 [m](緯度ごと)
    dx = np.radians(dlo) * n_rad * np.cos(np.radians(lat))      # 列方向 [m](緯度ごと)
    gx, gy = _gradient(a, 1.0, method)                          # まず「セル単位」で
    gx = gx / dx[:, None]
    gy = gy / dy[:, None]
    g = np.hypot(gx, gy)
    if units == "degrees":
        return np.degrees(np.arctan(g))
    if units == "radians":
        return np.arctan(g)
    if units == "percent":
        return 100.0 * g
    raise ValueError(f"units must be one of ('degrees', 'radians', 'percent'), got {units!r}")


def _positive_deg(v, name):
    x = float(v)
    if not np.isfinite(x) or x <= 0:
        raise ValueError(f"{name} must be a finite positive number of degrees, got {v}")
    return x
