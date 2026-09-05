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
    """地形位置指数 TPI —— 自セルと 8 近傍平均の差 [m]。正が尾根、負が谷。"""
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
    """集水量が閾値を超えたセルを河道とみなす二値マスク。"""
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
    out = np.zeros((h, w))
    yy, xx = np.mgrid[0:h, 0:w]
    for step in range(1, reach + 1):
        sy = np.rint(yy + uy * step).astype(np.int64)
        sx = np.rint(xx + ux * step).astype(np.int64)
        ok = (sy >= 0) & (sy < h) & (sx >= 0) & (sx < w)
        zs = np.where(ok, a[np.clip(sy, 0, h - 1), np.clip(sx, 0, w - 1)], -np.inf)
        ang = np.degrees(np.arctan((zs - a) / (step * c)))
        out = np.maximum(out, np.where(ok, ang, 0.0))
    return out


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
