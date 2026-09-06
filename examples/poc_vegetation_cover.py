# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""畑の緑を数える —— 被覆率の真値を自分で置いて、指数と閾値がどこで壊れるかを測る。

EXTEND: 実際の圃場画像に差し替えるなら ``observe()`` が返す ``(cube, truth)`` の対を、
撮影した多バンド画像と、その手作業ラベル(または高解像度で撮り直した参照画像を
落とした被覆率)に置き換える。**真値は「画素ラベル」ではなく「画素ごとの葉の面積率」**
にすること —— 二値ラベルにした瞬間、この PoC のいちばん重要な軸(混合画素)が
測れなくなる。バンドは 470 / 550 / 660 / 840 nm の 4 枚を仮定している。近赤外の
中心波長は葉の反射が立ち上がる 700〜750 nm より十分長く取る(赤縁の上に置くと、
わずかな波長ずれで植生指数が大きく動く)。

この PoC が示すこと:

1. **ゼロ点(大津の二値化を緑チャネルに掛ける)を先に測る** —— 指数を使う手法が
   これに勝てないなら勝てないと書く。実測ではゼロ点は **どの生育段階でも
   +7〜+16 pp 上振れ**し、指数を使う 3 手法はいずれもその 1/4 以下に収まる。
2. **どの指標を見るかで「壊れている段階」が変わる** —— ゼロ点の被覆率の偏りが
   いちばん悪いのは中期(+16.3 pp)だが、画素の適合率がいちばん悪いのは発芽期
   (0.474)。**1 つの数字にまとめると、この 2 つのうち片方が必ず消える**。
3. **偏り(bias)と散らばり(scatter)を分ける** —— 被覆率は「平均して合っている」
   ことが要求される量なので、平均誤差と標準偏差を混ぜた 1 つの誤差指標にすると
   系統的に上振れする手法を見逃す。実測では散らばりはどの手法も 0.5 pp 以下で、
   **効いている差はほぼ全部が偏り**だった —— つまり枚数を増やしても消えない。
4. **混合画素は閾値法の原理的な限界** —— 画素が葉より大きくなると、どこに閾値を
   置いても被覆率は偏る。アンミキシングだけが分数のまま答えられる。
5. **影は「暗さ」を手掛かりにする手法を殺す** —— 影の中の土は葉より暗い。
6. **端成分を盲目的に取る(PPI)は、純画素が足りないからではなく雑音で壊れる**。
   σ=0.004 の雑音を足しただけで、純粋な葉が 67 % ある場面で PPI は葉を 1 つも
   拾わなくなる。**純画素が多いほど壊れやすい**(票が割れるため)。予想と逆。

主な実測(96x96 画素、生育 3 段階 x 4 枚 = 12 枚、影 0.8、乾いた土、晴れ)。
偏り [pp] ± 散らばり [pp]、適合率 / 再現率は画素単位:

  ======================= ============= ============= ============= =============
  手法                    発芽 6.7 %    中期 37.4 %   繁茂 81.2 %   繁茂 適/再
  ======================= ============= ============= ============= =============
  大津・緑(ゼロ点)        +7.0 ± 0.2   +16.3 ± 0.3   +11.2 ± 0.2   0.883 / 0.993
  ExG + 大津               -0.5 ± 0.2    -2.7 ± 0.2    -2.1 ± 0.3   0.999 / 0.962
  NDVI + 大津              +1.9 ± 0.1    +3.6 ± 0.1    +3.2 ± 0.1   0.973 / 1.000
  アンミックス3(+影)      +0.7 ± 0.0    +1.3 ± 0.0    +1.1 ± 0.0   0.982 / 0.999
  ======================= ============= ============= ============= =============

(表の数字は実行のたびに印字される。ここに書いたのは手元で走らせた値。)

★ この PoC が出した道具の穴は末尾の「まとめ」節と、親への報告に列挙してある。
要点だけ: (a) ``otsu`` / ``sk_otsu`` / ``cv_otsu`` の 3 つが同じ入力に違う答えを
返す(``otsu`` と ``cv_otsu`` は ``[0,1]`` に切り詰めてから数えるので、生カウントを
渡すと壊れる。アフィン不変なのは ``sk_otsu`` だけ)。(b) ``spec_unmix`` は
B=3 を拒否するので、**色画像を分光的に解く経路が族に無い**。(c)
``spec_endmembers_ppi`` は選んだ画素の *添字* を返さないので、MNF 空間で PPI を
掛けてから元の分光を引く定石が組めない。
"""
from __future__ import annotations

import time
import unicodedata

import numpy as np

import fullseye as fs
import specops

# --------------------------------------------------------------------------- #
# 表示                                                                          #
# --------------------------------------------------------------------------- #
def _dw(s):
    """全角を 2 桁と数えた表示幅(str.format は文字数で数えるので桁が揃わない)。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def pad(s, n, right=True):
    """表示幅 ``n`` に詰める。``right`` なら右寄せ。"""
    s = str(s)
    sp = " " * max(0, n - _dw(s))
    return sp + s if right else s + sp


# --------------------------------------------------------------------------- #
# 分光 —— 材質ごとの反射率(4 バンド: 470 / 550 / 660 / 840 nm)                  #
# --------------------------------------------------------------------------- #
#: バンド中心波長 [nm]。青・緑・赤・近赤外。
BANDS_NM = (470.0, 550.0, 660.0, 840.0)
B_BLUE, B_GREEN, B_RED, B_NIR = 0, 1, 2, 3

#: 材質の反射率。可視は葉緑素の吸収で低く、近赤外は葉の細胞壁での散乱で跳ね上がる
#: (いわゆる赤縁)。乾いた土は波長とともに単調に上がる。湿ると水膜で全体が暗くなる
#: が **形は変わらない**(= 正規化指数では区別がつかない)。枯れ葉は葉緑素を失って
#: 赤の吸収が消え、近赤外は葉の構造が残るぶん高いまま —— これが可視域指数の弱点。
RHO = {
    "leaf":      np.array([0.045, 0.095, 0.040, 0.500]),   # 緑葉
    "soil_dry":  np.array([0.100, 0.150, 0.200, 0.270]),   # 乾いた土
    "soil_wet":  np.array([0.045, 0.068, 0.090, 0.122]),   # 湿った土(暗い)
    "senescent": np.array([0.090, 0.170, 0.290, 0.420]),   # 枯れ葉
}

#: 影の中に届く天空光の割合(バンドごと)。空気分子の散乱は短波長ほど強いので
#: **影は青い**。この波長依存を入れないと、影は全バンド一様な暗さになってしまい、
#: 正規化指数が影に強い/弱いという肝心の性質が測れなくなる。
DIFFUSE = np.array([0.50, 0.32, 0.22, 0.14])

LAB_SOIL, LAB_LEAF, LAB_SENESCENT = 0, 1, 2

#: 副画素格子の一辺 [副画素]。すべての場面をこの格子に描き、あとから画素へ落とす。
FIELD_SUB = 576
#: 葉の長さ [副画素]。画素の大きさを振るときは **これを固定して画素側を変える**。
LEAF_LEN_SUB = 60.0

#: 生育段階 —— (名前, 葉の長さ倍率, 1 株あたりの葉数)。
STAGES = (("発芽期", 0.33, 4), ("中期", 0.62, 8), ("繁茂期", 0.90, 14))


# --------------------------------------------------------------------------- #
# 群落の合成 —— 畝があり、葉が重なり、条間に土が見える                            #
# --------------------------------------------------------------------------- #
def _draw_leaf(lab, cy, cx, length, width, theta, value):
    """披針形(先が尖った)の葉を 1 枚描く。``|v| <= (w/2)(1-(u/a)^2)^0.6``。

    楕円ではなく先を尖らせるのは見た目のためではなく、**縁の画素の混ざり方**を
    変えるため。楕円は縁が丸いので混合画素が細い帯にしか出ないが、尖った葉先と
    葉の重なりは面積の割に長い縁を作る —— 実際の群落で混合画素が多い理由がそれ。
    """
    a = 0.5 * length
    b = 0.5 * width
    r = int(np.ceil(max(a, b))) + 1
    y0, y1 = max(0, int(cy) - r), min(lab.shape[0], int(cy) + r + 1)
    x0, x1 = max(0, int(cx) - r), min(lab.shape[1], int(cx) + r + 1)
    if y1 <= y0 or x1 <= x0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dy = yy - cy
    dx = xx - cx
    ct, st = np.cos(theta), np.sin(theta)
    u = dx * ct + dy * st                      # 葉の長軸方向
    v = -dx * st + dy * ct                     # 幅方向
    t = np.clip(1.0 - (u / a) ** 2, 0.0, None)
    inside = np.abs(v) <= b * t ** 0.6
    sub = lab[y0:y1, x0:x1]
    sub[inside] = value


def make_field(seed, stage_idx, *, senescent_frac=0.0, row_spacing_sub=96.0,
               plant_spacing_sub=64.0, shadow_shift_sub=(14, 9)):
    """副画素格子に群落を描き、``(label, shadow)`` を返す。

    畝は縦方向(列)に走り、条間には土が見える。株はその畝の上に間隔を空けて並び、
    株ごとに葉が放射状に出て**隣の株と重なる**。一様乱数のまだらではなく、この
    「重なりと条間」があることが要 —— まだらだと縁の長さが面積に比例してしまい、
    混合画素の割合が被覆率と一緒に動いてしまう。

    影は群落マスクを ``shadow_shift_sub`` だけずらして、そこが土である所を影とする。
    **葉の自己遮蔽は入れていない**(入れると影の強さの効き方が二重になり、崖が
    どちらの由来か分けられなくなる)。
    """
    rng = np.random.default_rng(1000 * seed + stage_idx + 7 * int(100 * senescent_frac))
    n = FIELD_SUB
    lab = np.zeros((n, n), np.uint8)
    _, growth, n_leaves = STAGES[stage_idx]
    n_rows = max(1, int(round(n / row_spacing_sub)))
    for k in range(n_rows):
        xc0 = (k + 0.5) * n / n_rows
        y = rng.uniform(0.0, plant_spacing_sub)
        while y < n + plant_spacing_sub:
            xc = xc0 + rng.normal(0.0, 0.06 * row_spacing_sub)
            base = rng.uniform(0.0, 2.0 * np.pi)
            for j in range(n_leaves):
                theta = base + 2.0 * np.pi * j / n_leaves + rng.normal(0.0, 0.25)
                ln = LEAF_LEN_SUB * growth * rng.uniform(0.75, 1.30)
                wd = 0.34 * ln
                # 葉柄のぶん、株の中心から長軸方向に押し出す
                cy = y + 0.45 * ln * np.sin(theta)
                cx = xc + 0.45 * ln * np.cos(theta)
                val = (LAB_SENESCENT if rng.random() < senescent_frac else LAB_LEAF)
                _draw_leaf(lab, cy, cx, ln, wd, theta, val)
            y += plant_spacing_sub * rng.uniform(0.8, 1.2)
    canopy = lab != LAB_SOIL
    dy, dx = shadow_shift_sub
    shifted = np.zeros_like(canopy)
    shifted[dy:, dx:] = canopy[:n - dy, :n - dx]
    return lab, shifted & ~canopy


def observe(field, sub, *, soil="soil_dry", shadow=0.8, gain=1.0, noise=0.004, seed=0):
    """センサ模型 —— 副画素格子の場を ``sub`` x ``sub`` で面積平均して画素へ落とす。

    返り値は ``(cube (H,W,4), truth (H,W))``。``truth`` は **その画素に入った緑葉の
    面積率**で、こちらが自分で置いたものなので厳密に既知。枯れ葉は緑葉ではないので
    ``truth`` に数えない(枯れ葉を植生に数えるかは目的次第 —— ここでは「緑の被覆率」)。

    混合は放射輝度の面積平均として起きる。これが線形混合モデルそのものなので、
    アンミキシングにとっては**いちばん都合のよい**条件である(実際の群落は多重散乱
    があり線形からずれる)。それでも壊れる所が出るなら、実場面ではもっと壊れる。
    """
    lab, shad = field
    n = lab.shape[0]
    if n % sub:
        raise ValueError(f"副画素格子 {n} が画素サイズ {sub} で割り切れない")
    h = n // sub
    # 行の並びはラベルの並び(0=土, 1=緑葉, 2=枯れ葉)。ここを取り違えると土と葉の
    # 分光が入れ替わり、それでも例外は出ずに「もっともらしく間違った」絵が出る。
    rho = np.stack([RHO[soil], RHO["leaf"], RHO["senescent"]], 0)
    refl = rho[lab]                                    # (n, n, 4)
    illum = np.where(shad[:, :, None], 1.0 - shadow * (1.0 - DIFFUSE[None, None, :]), 1.0)
    rad = gain * refl * illum
    cube = rad.reshape(h, sub, h, sub, 4).mean(axis=(1, 3))
    truth = (lab == LAB_LEAF).reshape(h, sub, h, sub).mean(axis=(1, 3))
    if noise > 0.0:
        cube = cube + np.random.default_rng(9000 + seed).normal(0.0, noise, cube.shape)
    return cube, truth


# --------------------------------------------------------------------------- #
# 手法 —— どれも「画素ごとの緑葉の割合の推定値 [0,1]」を返す                      #
# --------------------------------------------------------------------------- #
#: 大津は ``otsu`` / ``sk_otsu`` / ``cv_otsu`` の 3 つがあり **同じ入力に違う答えを
#: 返す**(末尾の道具の穴の節で数字を出す)。ここでは 3 つのうち唯一アフィン変換に
#: 不変な ``sk_otsu`` を使う —— 大津の閾値は本来「入力を a*x+b に変えても同じ画素で
#: 切れる」もので、指数のように値域が ``[0,1]`` に収まらない量に掛ける以上、
#: そこが崩れる実装は使えない。
OTSU_OP = "sk_otsu"


def otsu_upper(x, op=OTSU_OP):
    """大津の閾値より **大きい**側を True にした bool マスク。"""
    return fs.apply(np.asarray(x, np.float64), op) > 0.5


def exg(cube):
    """ExG = 2g - r - b(色度座標)。可視 3 バンドだけで計算でき、**倍率に不変**。

    分母で割るので、晴れ / 曇りの明るさの違いや影の「暗さそのもの」は落ちる。
    落ちないのは影の**色**(天空光は青い)のほうで、そのぶん土の ExG が持ち上がる。
    """
    s = cube[:, :, B_BLUE] + cube[:, :, B_GREEN] + cube[:, :, B_RED] + 1e-9
    return (2.0 * cube[:, :, B_GREEN] - cube[:, :, B_RED] - cube[:, :, B_BLUE]) / s


def ndvi(cube):
    """NDVI = (NIR - Red) / (NIR + Red)。台帳の ``spec_index`` そのもの。"""
    return fs.spec_index(cube, B_NIR, B_RED)


#: NDVI の端点(材質が分かっているので閉形式で置ける)。実運用ではシーンの分位点で
#: 推定するが、ここで測りたいのは推定誤差ではなく **線形換算そのものの偏り**。
NDVI_SOIL = float((RHO["soil_dry"][B_NIR] - RHO["soil_dry"][B_RED])
                  / (RHO["soil_dry"][B_NIR] + RHO["soil_dry"][B_RED]))
NDVI_LEAF = float((RHO["leaf"][B_NIR] - RHO["leaf"][B_RED])
                  / (RHO["leaf"][B_NIR] + RHO["leaf"][B_RED]))

E_LEAF_SOIL = np.stack([RHO["leaf"], RHO["soil_dry"]], 0)
#: 影を 3 つ目の端成分に置く(photometric shade)。影は「反射率がゼロに近い面」として
#: 振る舞うので、和 1 の制約下では**明るさの自由度**を吸収する係数になる。
E_LEAF_SOIL_SHADE = np.stack([RHO["leaf"], RHO["soil_dry"], np.zeros(4)], 0)


def m_otsu_green(cube):
    """ゼロ点 —— 緑チャネルに大津を掛け、**暗い側**を植生とする。

    向きを固定するのが肝心。乾いた土は緑バンドで 0.150、緑葉は 0.095 なので、
    可視域では **葉のほうが暗い**。この規約は湿った土(緑 0.068)で反転する ——
    崖 (c) がそれ。「明るい側」に取る規約も同じだけ恣意的で、どちらも安全ではない。
    """
    return (~otsu_upper(cube[:, :, B_GREEN])).astype(np.float64)


def m_exg_otsu(cube):
    return otsu_upper(exg(cube)).astype(np.float64)


def m_exg_fixed(cube):
    """ExG > 0 の固定閾値。土の ExG は原理的に 0 付近になる(下の対照表を参照)。"""
    return (exg(cube) > 0.0).astype(np.float64)


def m_ndvi_otsu(cube):
    return otsu_upper(ndvi(cube)).astype(np.float64)


def m_ndvi_fixed(cube):
    return (ndvi(cube) > 0.40).astype(np.float64)


def m_ndvi_linear(cube):
    """NDVI を端点で線形に割り戻して被覆率にする(Gutman & Ignatov 流の 1 次形)。

    NDVI は混合率の **非線形**関数なので、この換算は原理的に偏る。この分光条件では
    上振れで、下の混合画素の節にビンごとの数字を出す。
    """
    return np.clip((ndvi(cube) - NDVI_SOIL) / (NDVI_LEAF - NDVI_SOIL), 0.0, 1.0)


def m_unmix2(cube):
    """線形アンミキシング(葉 + 土、和 1 制約つき)。影の自由度を持っていない。"""
    return np.clip(specops.spec_unmix(cube, E_LEAF_SOIL, constrained=True)[:, :, 0], 0.0, 1.0)


def m_unmix3(cube):
    """線形アンミキシング(葉 + 土 + 影)。影で正規化した葉の割合を返す。

    ``a_leaf / (a_leaf + a_soil)`` = 影の係数を割り落とした「地面の中身の比」。
    影は明るさの自由度なので、これで倍率変化にも影にも効く。
    """
    a = specops.spec_unmix(cube, E_LEAF_SOIL_SHADE, constrained=True)
    return np.clip(a[:, :, 0] / (a[:, :, 0] + a[:, :, 1] + 1e-9), 0.0, 1.0)


#: 可視だけでアンミキシングしたいとき、**青緑赤の 3 バンドは ``spec_unmix`` に渡せない**
#: —— ``_as_cube`` が B=3 を「色画像を分光キューブと取り違えないため」に拒否するため
#: (B=2 は明示的な二バンドキューブとして通る)。色画像を分光的に解く経路が族に無い
#: ので、ここでは緑・赤の 2 バンドに落として解く。★道具の穴。
VIS_BANDS = (B_GREEN, B_RED)


def m_unmix2_vis(cube):
    """可視だけのアンミキシング(近赤外が無い機材の対照)。緑・赤の 2 バンド。"""
    sub = np.stack([cube[:, :, i] for i in VIS_BANDS], -1)
    E = np.stack([E_LEAF_SOIL[:, i] for i in VIS_BANDS], -1)
    return np.clip(specops.spec_unmix(sub, E, constrained=True)[:, :, 0], 0.0, 1.0)


METHODS = (
    ("大津・緑(ゼロ点)", m_otsu_green),
    ("ExG + 大津", m_exg_otsu),
    ("ExG > 0(固定)", m_exg_fixed),
    ("NDVI + 大津", m_ndvi_otsu),
    ("NDVI > 0.4(固定)", m_ndvi_fixed),
    ("NDVI 線形換算", m_ndvi_linear),
    ("アンミックス2(葉+土)", m_unmix2),
    ("アンミックス3(+影)", m_unmix3),
    ("アンミックス2・可視のみ", m_unmix2_vis),
)
SHORT = ("大津・緑", "ExG+大津", "NDVI+大津", "アンミックス3")
SHORT_FN = dict(METHODS)


# --------------------------------------------------------------------------- #
# 指標                                                                          #
# --------------------------------------------------------------------------- #
def pr(pred_map, truth_f):
    """画素単位の (適合率, 再現率)。真値は「葉が画素の半分以上」を陽性とする。

    **別々に返す**。F 値のように 1 つへ丸めると、ゼロ点のように「ほぼ全部を植生と
    答えて再現率だけ高い」壊れ方が、そこそこの数字に化けてしまう。
    """
    p = np.asarray(pred_map) >= 0.5
    t = np.asarray(truth_f) >= 0.5
    tp = float(np.count_nonzero(p & t))
    fp = float(np.count_nonzero(p & ~t))
    fn = float(np.count_nonzero(~p & t))
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    return prec, rec


def _nanmean(xs):
    """nan を除いた平均。**全部 nan なら nan を返す**(0 を返して「当たっている」ように
    見せない —— 陽性を 1 つも出さなかった手法の適合率は 0 ではなく『未定義』)。"""
    a = np.asarray(xs, np.float64)
    a = a[np.isfinite(a)]
    return float(a.mean()) if a.size else float("nan")


def run(scenes, methods):
    """``scenes`` = [(cube, truth), ...] を回して手法ごとの結果をまとめる。

    返り値 ``{名前: dict}``。``bias`` = 平均誤差 [pp]、``scatter`` = 誤差の標準偏差
    [pp]。**この 2 つを混ぜない** —— 被覆率は平均して合っていることが要求される量
    なので、偏りと散らばりは別の欠陥である。
    """
    out = {}
    for name, fn in methods:
        errs, precs, recs = [], [], []
        maps = []
        for cube, truth in scenes:
            m = fn(cube)
            maps.append((m, truth))
            errs.append(100.0 * (float(m.mean()) - float(truth.mean())))
            a, b = pr(m, truth)
            precs.append(a)
            recs.append(b)
        e = np.asarray(errs)
        out[name] = {
            "bias": float(e.mean()),
            "scatter": float(e.std()),
            "mae": float(np.abs(e).mean()),
            "prec": _nanmean(precs),
            "rec": _nanmean(recs),
            "maps": maps,
        }
    return out


# --------------------------------------------------------------------------- #
def main():
    t_start = time.perf_counter()
    SUB = 6                                   # 96x96 画素、画素 / 葉の長さ = 0.10
    N_SEED = 4

    print("=== 1. 何を作ったか(被覆率の真値は自分で置いた葉の面積)===")
    fields = {(s, k): make_field(k, s) for s in range(len(STAGES)) for k in range(N_SEED)}
    scenes = {s: [observe(fields[(s, k)], SUB, seed=k) for k in range(N_SEED)]
              for s in range(len(STAGES))}
    print(f"  副画素格子 {FIELD_SUB}x{FIELD_SUB} に畝(条間 96 副画素)と株(間隔 64)を描き、")
    print(f"  {SUB}x{SUB} 副画素を 1 画素に面積平均 → {FIELD_SUB // SUB}x{FIELD_SUB // SUB} 画素。")
    print(f"  葉の長さ {LEAF_LEN_SUB:.0f} 副画素 = 画素の {LEAF_LEN_SUB / SUB:.1f} 倍。")
    print("  " + pad("生育段階", 12, right=False) + pad("被覆率(真値)", 16)
          + pad("純・葉", 10) + pad("純・土", 10) + pad("混合画素", 12))
    truth_cover = {}
    mixed_frac = {}
    for s, (nm, _, _) in enumerate(STAGES):
        f = np.concatenate([t.ravel() for _, t in scenes[s]])
        truth_cover[s] = float(f.mean())
        mixed_frac[s] = float(np.mean((f > 0) & (f < 1)))
        print("  " + pad(nm, 12, right=False) + pad(f"{100 * f.mean():.2f} %", 16)
              + pad(f"{100 * np.mean(f == 1):.1f} %", 10)
              + pad(f"{100 * np.mean(f == 0):.1f} %", 10)
              + pad(f"{100 * mixed_frac[s]:.1f} %", 12))
    print("  → 画素が葉より十分小さくても混合画素は 2 割前後ある。葉の縁と重なりが")
    print("     面積の割に長いため。ここが被覆率推定の誤差の主産地になる。")

    print("\n  材質の反射率(この合成の前提。影は天空光の割合 = 青ほど大きい):")
    print("  " + pad("材質", 14, right=False)
          + "".join(pad(f"{w:.0f} nm", 10) for w in BANDS_NM)
          + pad("NDVI", 9) + pad("ExG", 9))
    for key, jp in (("leaf", "緑葉"), ("soil_dry", "乾いた土"),
                    ("soil_wet", "湿った土"), ("senescent", "枯れ葉")):
        r = RHO[key]
        nd = (r[B_NIR] - r[B_RED]) / (r[B_NIR] + r[B_RED])
        ssum = r[B_BLUE] + r[B_GREEN] + r[B_RED]
        eg = (2 * r[B_GREEN] - r[B_RED] - r[B_BLUE]) / ssum
        print("  " + pad(jp, 14, right=False)
              + "".join(pad(f"{x:.3f}", 10) for x in r)
              + pad(f"{nd:+.3f}", 9) + pad(f"{eg:+.3f}", 9))
    print(f"  影の中の天空光の割合 {np.array2string(DIFFUSE, precision=2)}(470→840 nm)")
    print("  → 湿った土は乾いた土の 0.45 倍で **形が同じ**。正規化指数(NDVI/ExG)は")
    print("     倍率に不変なので区別できない = そこは弱点ではなく設計どおり。壊れるのは")
    print("     **明るさそのものを手掛かりにする手法**(ゼロ点とアンミックス2)のほう。")

    print("\n=== 2. ゼロ点を先に測る —— 大津の二値化を緑チャネルに掛ける ===")
    z = {s: run(scenes[s], (("大津・緑(ゼロ点)", m_otsu_green),))["大津・緑(ゼロ点)"]
         for s in range(len(STAGES))}
    print("  " + pad("生育段階", 12, right=False) + pad("真値", 10) + pad("推定", 10)
          + pad("偏り [pp]", 12) + pad("散らばり", 11) + pad("適合率", 10) + pad("再現率", 10))
    for s, (nm, _, _) in enumerate(STAGES):
        d = z[s]
        print("  " + pad(nm, 12, right=False) + pad(f"{100 * truth_cover[s]:.1f}%", 10)
              + pad(f"{100 * truth_cover[s] + d['bias']:.1f}%", 10)
              + pad(f"{d['bias']:+.1f}", 12) + pad(f"{d['scatter']:.1f}", 11)
              + pad(f"{d['prec']:.3f}", 10) + pad(f"{d['rec']:.3f}", 10))
    zb = [z[s]["bias"] for s in range(len(STAGES))]
    print(f"  → ゼロ点はどの段階でも **同じ向きに** 上振れする(+{min(zb):.1f} 〜"
          f" +{max(zb):.1f} pp)。散らばりは 0.5 pp 以下なので、")
    print("     これは枚数を増やしても消えない **偏り**である。ここに勝てない手法は")
    print("     採らない、というのがこの表の使い道。")
    print(f"  → **どの指標を見るかで『壊れている段階』が変わる**。偏りの最悪は"
          f" {STAGES[int(np.argmax(np.abs(zb)))][0]}"
          f"({max(zb, key=abs):+.1f} pp)だが、")
    print(f"     適合率の最悪は {STAGES[int(np.argmin([z[s]['prec'] for s in range(3)]))][0]}"
          f"({min(z[s]['prec'] for s in range(3)):.3f})。低被覆率では再現率がほぼ 1 のまま")
    print("     適合率だけが落ちる = **土をまとめて植生と答えている**。被覆率の偏りが")
    print("     そこまで大きく見えないのは、そもそも植生が少なく分母が小さいためで、")
    print("     『被覆率の誤差が小さい = 当たっている』ではない。")

    print("\n=== 3. 手法の比較 —— 生育段階ごとに、偏りと散らばりを分けて ===")
    res = {s: run(scenes[s], METHODS) for s in range(len(STAGES))}
    W = 22
    print("  " + pad("手法", W, right=False)
          + "".join(pad(f"{nm}", 16) for nm, _, _ in STAGES) + pad("全段の |偏り| 平均", 20))
    print("  " + pad("", W, right=False)
          + "".join(pad("偏り±散らばり", 16) for _ in STAGES))
    print("  " + "-" * (W + 16 * len(STAGES) + 20))
    for name, _ in METHODS:
        cells = "".join(pad(f"{res[s][name]['bias']:+.1f}±{res[s][name]['scatter']:.1f}", 16)
                        for s in range(len(STAGES)))
        allb = np.mean([abs(res[s][name]["bias"]) for s in range(len(STAGES))])
        print("  " + pad(name, W, right=False) + cells + pad(f"{allb:.2f} pp", 20))
    print("  → 単位は percentage point(被覆率そのものの差)。**散らばりはどの手法も")
    print("     0.5 pp 以下**で、手法間の差はほぼ全部が偏り = 枚数では消えない。")
    print("     右端の 1 つの数字にまとめると、ExG > 0(固定)が段階でどれだけ動くか")
    print("     (発芽 +50 → 繁茂 +14 pp)が見えなくなる。**同じ 34 pp でも、全段で")
    print("     一様に 34 ずれるのと、段階で 36 pp も動くのとでは別の欠陥**である。")

    print("\n=== 4. 画素単位の分類 —— 適合率と再現率を別々に ===")
    print("  " + pad("手法", W, right=False)
          + "".join(pad(f"{nm[:2]} 適/再", 16) for nm, _, _ in STAGES))
    print("  " + "-" * (W + 16 * len(STAGES)))
    for name, _ in METHODS:
        cells = "".join(pad(f"{res[s][name]['prec']:.3f}/{res[s][name]['rec']:.3f}", 16)
                        for s in range(len(STAGES)))
        print("  " + pad(name, W, right=False) + cells)
    print("  → いちばん極端なのは ExG > 0(固定)の発芽期で、**再現率 1.000 / 適合率 0.119**。")
    print("     F 値に丸めると 0.213 だが、実体は『ほぼ全画素を植生と答えた』であって")
    print("     『2 割正解した』ではない。ゼロ点も向きは同じ(再現率 0.964 / 適合率 0.474)。")
    print("     逆にアンミックス2 は 適合率 1.000 / 再現率 0.94-0.98 で、**落としている**")
    print("     **側**に偏っている。同じ『そこそこの数字』でも欠陥の向きは正反対で、")
    print("     どちらに倒すかは用途で決まる —— 1 つに丸めるとその選択ができなくなる。")

    print("\n=== 5. 混合画素 —— 真値 f のビンごとに、手法は何と答えるか ===")
    edges = np.array([0.0, 1e-9, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0 - 1e-9, 1.0 + 1e-9])
    lbls = ("f=0", "0-0.1", "0.1-0.3", "0.3-0.5", "0.5-0.7", "0.7-0.9", "0.9-1", "f=1")
    allmaps = {name: [(m, t) for s in range(len(STAGES)) for m, t in res[s][name]["maps"]]
               for name, _ in METHODS}
    tcat = np.concatenate([t.ravel() for _, t in allmaps["NDVI + 大津"]])
    idx = np.clip(np.digitize(tcat, edges) - 1, 0, len(lbls) - 1)
    print("  " + pad("手法", W, right=False) + "".join(pad(l, 10) for l in lbls))
    print("  " + pad("画素数", W, right=False)
          + "".join(pad(f"{int(np.count_nonzero(idx == i)):d}", 10) for i in range(len(lbls))))
    print("  " + "-" * (W + 10 * len(lbls)))
    print("  " + pad("真値 f の平均", W, right=False)
          + "".join(pad(f"{tcat[idx == i].mean():.3f}", 10) for i in range(len(lbls))))
    for name in ("大津・緑(ゼロ点)", "ExG + 大津", "NDVI 線形換算",
                 "アンミックス2(葉+土)", "アンミックス3(+影)"):
        v = np.concatenate([m.ravel() for m, _ in allmaps[name]])
        print("  " + pad(name, W, right=False)
              + "".join(pad(f"{v[idx == i].mean():.3f}", 10) for i in range(len(lbls))))
    print("  → 二値手法(上 2 行)はビンの中で 0 か 1 しか返せないので、この行は")
    print("     『そのビンの何割を植生と答えたか』になる。0.5 を跨ぐ位置が真値の 0.5 から")
    print("     ずれていれば、それが被覆率の系統偏差の正体である。アンミックスの行だけが")
    print("     f に沿って連続に上がる = **分数のまま答えられているのはここだけ**。")
    lin = np.concatenate([m.ravel() for m, _ in allmaps["NDVI 線形換算"]])
    mid = (tcat > 0.05) & (tcat < 0.95)
    lin_bias = 100.0 * float((lin[mid] - tcat[mid]).mean())
    print(f"  NDVI 線形換算の混合画素(0.05<f<0.95)での偏り {lin_bias:+.2f} pp"
          f"(画素全体では {100 * float((lin - tcat).mean()):+.2f} pp)。")
    print("     NDVI は混合率の**非線形**関数なので、線形に割り戻すと原理的に上振れする。")
    print("     被覆率全体の偏りが 1-2 pp に見えるのは、純画素(f=0 と f=1)が数で薄める")
    print("     ためで、**混合画素だけを見ると 8 pp を超える**。混ぜて 1 つの数字にすると")
    print("     『NDVI 線形換算はよく当たる』と読めてしまう。")
    print("     なお 2 乗形(Carlson & Ripley 流 fc=((N-Ns)/(Nv-Ns))^2)は、線形混合が")
    print("     前提のこの場面では逆に大きく下振れする: 同じ画素で"
          f" {100 * float(((lin[mid] ** 2) - tcat[mid]).mean()):+.2f} pp。")
    print("     2 乗形が想定しているのは葉面積指数に対する飽和で、面積混合ではない。")

    print("\n=== 6. 崖 (a) 影の強さ —— 何が先に壊れるか ===")
    sh_methods = (("大津・緑(ゼロ点)", m_otsu_green), ("ExG + 大津", m_exg_otsu),
                  ("NDVI + 大津", m_ndvi_otsu), ("アンミックス2(葉+土)", m_unmix2),
                  ("アンミックス3(+影)", m_unmix3))
    print("  発芽期(被覆率 " + f"{100 * truth_cover[0]:.0f} %)と繁茂期("
          + f"{100 * truth_cover[2]:.0f} %)、偏り [pp]")
    print("  " + pad("影の強さ", 12, right=False)
          + "".join(pad(n.split("(")[0], 15) for n, _ in sh_methods))
    shadow_rows = {}
    for s in (0, 2):
        print("  " + pad(f"— {STAGES[s][0]} —", 12, right=False))
        for sv in (0.0, 0.4, 0.8, 1.0):
            sc = [observe(fields[(s, k)], SUB, shadow=sv, seed=k) for k in range(2)]
            r = run(sc, sh_methods)
            shadow_rows[(s, sv)] = r
            print("  " + pad(f"{sv:.1f}", 12, right=False)
                  + "".join(pad(f"{r[n]['bias']:+.1f}", 15) for n, _ in sh_methods))
    print("  → 先に壊れるのはゼロ点。影の中の土は緑バンドで葉より暗く、『暗い側 = 植生』")
    print("     という規約に直接刺さる。アンミックス2 も明るさの自由度を持たないので")
    print("     影を土や葉の量に押し込む。**影に強いのは正規化指数と、影を端成分に")
    print("     置いたアンミックス3** —— 影は明るさの自由度だと分かっていれば設計できる。")

    print("\n=== 7. 崖 (b) 画素の大きさ —— 混合画素が支配的になる境界 ===")
    gsd_methods = (("大津・緑(ゼロ点)", m_otsu_green), ("ExG + 大津", m_exg_otsu),
                   ("NDVI + 大津", m_ndvi_otsu), ("アンミックス3(+影)", m_unmix3))
    print("  葉の長さは固定(" + f"{LEAF_LEN_SUB:.0f} 副画素)、画素だけ大きくする。偏り [pp]")
    print("  " + pad("画素/葉", 10, right=False) + pad("画素数", 10) + pad("混合率", 10)
          + "".join(pad(n.split("(")[0], 15) for n, _ in gsd_methods))
    gsd_rows = {}
    for s in (0, 2):
        print("  " + pad(f"— {STAGES[s][0]} —", 10, right=False))
        for sub in (4, 6, 8, 12, 16, 24, 32, 48):
            sc = [observe(fields[(s, k)], sub, seed=k) for k in range(2)]
            f = np.concatenate([t.ravel() for _, t in sc])
            mf = float(np.mean((f > 0) & (f < 1)))
            r = run(sc, gsd_methods)
            gsd_rows[(s, sub)] = (mf, r)
            print("  " + pad(f"{sub / LEAF_LEN_SUB:.2f}", 10, right=False)
                  + pad(f"{FIELD_SUB // sub}²", 10) + pad(f"{100 * mf:.0f} %", 10)
                  + "".join(pad(f"{r[n]['bias']:+.1f}", 15) for n, _ in gsd_methods))
    print("  → 二値手法は **段階で向きが逆**に伸びる。発芽期は混合画素をまとめて植生と")
    print("     数えて上振れし、繁茂期の ExG は条間の混合画素を土と数えて下振れする。")
    print("     どちらも『半分葉の画素を 0 と答えるか 1 と答えるか』しか選べないことの")
    print("     現れで、**閾値をどこに置いても直らない**。アンミックス3 は混合率 9 割")
    print("     でも数 pp に留まる —— ただしそれは端成分を知っている場合の話で、")
    print("     画像から推定しようとすると次節のとおりになる。")

    print("\n=== 8. 端成分を盲目的に取る(PPI)—— 壊す原因は雑音のほうだった ===")
    print("  アンミックスが強いのは端成分を **知っている** からである。画像から取れるか。")
    print("  PPI(Pixel Purity Index)= 乱数の射影軸に沿って端に来た画素に得点を与え、")
    print("  上位 K 画素を端成分とする。真値: 緑葉の NDVI "
          f"{NDVI_LEAF:+.3f} / 乾いた土 {NDVI_SOIL:+.3f}")

    def ppi_probe(cube, k=2, seed=0):
        """PPI で端成分を取り、``(端成分, NDVI のリスト, 葉らしい側の添字)`` を返す。"""
        E = specops.spec_endmembers_ppi(cube, k, n_projections=1000, seed=seed)
        nd = [float((e[B_NIR] - e[B_RED]) / (e[B_NIR] + e[B_RED])) for e in E]
        return E, nd, int(np.argmax(nd))

    pure_hi = float(np.mean(observe(fields[(2, 0)], SUB, seed=0)[1] == 1))
    print(f"\n  8-a. 雑音を振る(繁茂期、画素 / 葉 = {SUB / LEAF_LEN_SUB:.2f}、"
          f"純粋な葉の画素が {100 * pure_hi:.0f} % ある場面)")
    print("  " + pad("雑音 σ", 12, right=False) + pad("PPI 端成分の NDVI 最大/最小", 32)
          + pad("葉を拾えたか", 16) + pad("被覆率の偏り", 16))
    ppi_noise = {}
    for nz in (0.0, 0.0005, 0.001, 0.002, 0.004):
        cube, truth = observe(fields[(2, 0)], SUB, noise=nz, seed=0)
        E, nd, j = ppi_probe(cube)
        a = specops.spec_unmix(cube, E, constrained=True)
        bias = 100.0 * (float(a[:, :, j].mean()) - float(truth.mean()))
        ok = max(nd) > 0.5 * NDVI_LEAF
        ppi_noise[nz] = (max(nd), ok, bias)
        print("  " + pad(f"{nz:.4f}", 12, right=False)
              + pad(f"{max(nd):+.3f} / {min(nd):+.3f}", 32)
              + pad("はい" if ok else "**いいえ**", 16) + pad(f"{bias:+.1f} pp", 16))
    print("  → 雑音ゼロなら PPI は端成分をぴたりと当てる。**反射率で 0.1 % ほどの雑音を**")
    print("     **足しただけで葉を 1 つも拾わなくなる**。返ってくるのは深い影の画素で、")
    print("     全バンドがほぼ同じ低い値 = 材質の分光ではなく『いちばん暗い点』である。")
    cube_hi, _ = observe(fields[(2, 0)], SUB, seed=0)
    P = cube_hi.reshape(-1, 4)
    E3, _, _ = ppi_probe(cube_hi, k=3)
    fmt = lambda v: "[" + " ".join(f"{x:.4f}" for x in v) + "]"
    print(f"     PPI が返した 3 本 : {fmt(E3[0])} {fmt(E3[1])} {fmt(E3[2])}")
    print(f"     選ばれなかった最輝画素(= 純粋な葉): {fmt(P[int(np.argmax((P ** 2).sum(1)))])}")
    print("     理由は得点の配り方にある。**孤立した 1 点は多方向の射影で同時に端を取る**")
    print("     ので得点が集中するが、純粋な葉は何千画素もあって互いに票を割る。")
    print("     つまり PPI が選ぶのは『純粋な材質』ではなく『孤立した外れ値』で、")
    print("     **純画素が多いほど壊れやすい**という、予想と逆の性質になる。")

    print("\n  8-b. 雑音を消して、純画素のほうを消す(画素を大きくする)")
    print("  " + pad("画素/葉", 10, right=False) + pad("純・葉画素", 12)
          + pad("葉側 NDVI/NIR", 20) + pad("土側 NDVI/NIR", 20) + pad("被覆率の偏り", 15))
    ppi_gsd = {}
    for sub in (6, 12, 24, 48):
        cube, truth = observe(fields[(2, 0)], sub, noise=0.0, seed=0)
        pure = float(np.mean(truth == 1))
        E, nd, j = ppi_probe(cube)
        i = 1 - j
        a = specops.spec_unmix(cube, E, constrained=True)
        bias = 100.0 * (float(a[:, :, j].mean()) - float(truth.mean()))
        ppi_gsd[sub] = (pure, nd[j], bias, float(E[j][B_NIR]), nd[i], float(E[i][B_NIR]))
        print("  " + pad(f"{sub / LEAF_LEN_SUB:.2f}", 10, right=False)
              + pad(f"{100 * pure:.1f} %", 12)
              + pad(f"{nd[j]:+.3f} / {E[j][B_NIR]:.3f}", 20)
              + pad(f"{nd[i]:+.3f} / {E[i][B_NIR]:.3f}", 20) + pad(f"{bias:+.1f} pp", 15))
    print(f"  (真値: 葉 NDVI {NDVI_LEAF:+.3f} / NIR {RHO['leaf'][B_NIR]:.3f}、"
          f"土 NDVI {NDVI_SOIL:+.3f} / NIR {RHO['soil_dry'][B_NIR]:.3f})")
    print("  → 雑音が無ければ、純画素が残っているうちは端成分を当てる。純画素が消えると")
    print("     拾えるのは『いちばん端の混合画素』になる。ここで注意 —— **葉側の列だけを**")
    print("     **見ると最後の行も本物同然**(NDVI +0.849 / NIR 0.495)なのに、被覆率は")
    print("     23 pp ずれる。ずれたのは **土側** で、条間の土までが葉と混ざってしまい、")
    print("     土の端成分に植生が混入する(NDVI が跳ね上がる)。その端成分で解くと")
    print("     『土のところにも葉がある』ことになり、葉の存在量が下振れする。")
    print("     **片方の端成分だけを検算しても足りない** —— 混合画素の場面で崩れるのは")
    print("     たいてい少数派のほうの端成分である。**崖は 2 つあり、雑音のほうが手前**。")
    print("     定石は MNF(雑音で白色化した主成分)空間で PPI を掛け、選ばれた画素の")
    print("     **元の** 分光を引くことだが、``spec_endmembers_ppi`` は選んだ画素の添字を")
    print("     返さず分光そのものを返すので、この経路が素直に組めない。★道具の穴。")
    sc, _, _ = specops.spec_mnf(cube_hi, 4)
    Em = specops.spec_endmembers_ppi(sc, 2, n_projections=1000, seed=0)
    Pm = sc.reshape(-1, sc.shape[2])
    orig = cube_hi.reshape(-1, 4)
    E_mnf = orig[[int(np.argmin(((Pm - e) ** 2).sum(1))) for e in Em]]
    nd_mnf = [float((e[B_NIR] - e[B_RED]) / (e[B_NIR] + e[B_RED])) for e in E_mnf]
    print("     (代用として MNF スコアから最近傍の元画素を逆引きしてみると"
          f" NDVI {max(nd_mnf):+.3f} / {min(nd_mnf):+.3f} で、")
    print(f"      生の PPI の {ppi_noise[0.004][0]:+.3f} から **改善しなかった**。つまり")
    print("      この場面の主因は雑音の白色化ではなく、上の『票が割れる』ほうである。)")

    print("\n=== 9. 崖 (c) 土の湿りと枯れ葉 ===")
    cond_methods = sh_methods
    print("  " + pad("条件", 20, right=False) + pad("真値", 9)
          + "".join(pad(n.split("(")[0], 15) for n, _ in cond_methods))
    cond_rows = {}
    for s in (0, 2):
        print("  " + pad(f"— {STAGES[s][0]} —", 20, right=False))
        for label, kw, sen in (("乾いた土", {}, 0.0),
                               ("湿った土(暗い)", {"soil": "soil_wet"}, 0.0),
                               ("枯れ葉 30 %", {}, 0.30),
                               ("湿った土 + 枯れ葉", {"soil": "soil_wet"}, 0.30)):
            fl = [(fields[(s, k)] if sen == 0.0 else make_field(k, s, senescent_frac=sen))
                  for k in range(2)]
            sc = [observe(fl[k], SUB, seed=k, **kw) for k in range(2)]
            r = run(sc, cond_methods)
            tv = float(np.mean([t.mean() for _, t in sc]))
            cond_rows[(s, label)] = (tv, r)
            print("  " + pad(label, 20, right=False) + pad(f"{100 * tv:.1f}%", 9)
                  + "".join(pad(f"{r[n]['bias']:+.1f}", 15) for n, _ in cond_methods))
    print("  再現率で見た極性の反転(ゼロ点):")
    for s in (0, 2):
        a = cond_rows[(s, "乾いた土")][1]["大津・緑(ゼロ点)"]
        b = cond_rows[(s, "湿った土(暗い)")][1]["大津・緑(ゼロ点)"]
        print(f"    {STAGES[s][0]}: 乾 適合率 {a['prec']:.3f} / 再現率 {a['rec']:.3f}"
              f"  →  湿 {b['prec']:.3f} / {b['rec']:.3f}")
    print("  → 湿った土は緑バンドで 0.068、緑葉は 0.095。**『暗い側 = 植生』が反転する**。")
    print("     ゼロ点が壊れているのは閾値の位置ではなく **向きの規約**のほうで、")
    print("     大津をどれだけ丁寧に計算しても直らない。枯れ葉は逆に可視域指数を刺す ——")
    print("     近赤外が高いままなので NDVI では効きにくいが、ExG では土と紛れる。")

    print("\n=== 10. 崖 (d) 固定閾値 vs 大津 —— 系統偏差はどちらに出るか ===")
    print("  " + pad("手法", 22, right=False)
          + "".join(pad(f"{nm}", 16) for nm, _, _ in STAGES))
    for name in ("ExG > 0(固定)", "ExG + 大津", "NDVI > 0.4(固定)", "NDVI + 大津"):
        print("  " + pad(name, 22, right=False)
              + "".join(pad(f"{res[s][name]['bias']:+.2f}±{res[s][name]['scatter']:.2f}", 16)
                        for s in range(len(STAGES))))
    print("  → 固定閾値は**段階によらず同じ向きに**ずれる(偏り)。大津は段階ごとに")
    print("     閾値が動くので偏りは小さいが、**シーンの構成に閾値が引きずられる** ——")
    print("     被覆率が数 % だと 2 山の仮定が成り立たず、上の 2 節のとおり破綻する。")
    print("     どちらが良いかは『同じ畑を時系列で追う』(固定が有利、偏りは差分で消える)")
    print("     のか『別々の畑を 1 枚ずつ測る』(大津が有利)のかで逆になる。")

    print("\n=== 11. 崖 (e) 照度(曇り / 晴れ)===")
    ill_methods = sh_methods
    print("  " + pad("条件", 22, right=False) + pad("倍率", 8) + pad("影", 7)
          + "".join(pad(n.split("(")[0], 15) for n, _ in ill_methods))
    ill_rows = {}
    # 実際の曇りは「暗くなる」と「影が消える」が同時に起きる。それでは何が効いたのか
    # 分けられないので、**倍率だけを変えた対照**(暗いだけ・影は晴れのまま)を置く。
    for label, gain, sv, nz in (("晴れ", 1.00, 0.8, 0.004),
                                ("暗いだけ(対照)", 0.45, 0.8, 0.004),
                                ("暗い+雑音も比例(対照2)", 0.45, 0.8, 0.0018),
                                ("薄曇り", 0.70, 0.4, 0.004),
                                ("曇り", 0.45, 0.1, 0.004)):
        for s in (0, 2):
            sc = [observe(fields[(s, k)], SUB, shadow=sv, gain=gain, noise=nz, seed=k)
                  for k in range(2)]
            r = run(sc, ill_methods)
            ill_rows[(label, s)] = r
            print("  " + pad(f"{label} / {STAGES[s][0]}", 24, right=False)
                  + pad(f"{gain:.2f}", 8) + pad(f"{sv:.1f}", 7)
                  + "".join(pad(f"{r[n]['bias']:+.1f}", 15) for n, _ in ill_methods))
    print("  → 対照行(倍率だけ 0.45)で大きく壊れるのは **アンミックス2 だけ**。端成分を")
    print("     固定の反射率で持っているので、画像が一様に暗くなると和 1 の制約が行き場を")
    print("     失い、暗いほうの端成分(土)へ寄る。アンミックス3 は影 = 明るさの自由度を")
    print("     持っているので不変。")
    print("  → ただし ExG + 大津も対照行で 2〜3 pp 動く。**正規化指数が倍率に不変なのは**")
    print("     **雑音がゼロの極限だけ**で、暗くすれば同じ雑音が相対的に 2.2 倍になる。")
    print("     対照2(雑音も倍率に比例させた = 反射率に校正されたのと同じ)では元に戻る")
    print("     ので、これは倍率のせいではなく S/N のせいだと切り分けられる。")
    print("  → **対照を置かずに『曇り』の行だけを見ると、ゼロ点が良くなったのを**")
    print("     **『曇りに強い』と読んでしまう** —— 効いたのは倍率ではなく影が消えたほう")
    print("     である。悪条件が必ず全部を悪くするとは限らない。")

    print("\n=== 12. 道具の穴 —— 大津が 3 つあり、同じ入力に違う答えを返す ===")
    cube_lo = scenes[0][0][0]                     # 発芽期 = ExG の半分が負になる場面
    cube_hi2 = scenes[2][0][0]
    print("  " + pad("入力", 30, right=False) + pad("値域", 22)
          + pad("otsu", 11) + pad("sk_otsu", 11) + pad("cv_otsu", 11))
    otsu_frac = {}
    probes = (("緑チャネル(発芽期)", cube_lo[:, :, B_GREEN]),
              ("緑チャネル x4095(生カウント)", 4095.0 * cube_lo[:, :, B_GREEN]),
              ("ExG(発芽期・負が半分)", exg(cube_lo)),
              ("NDVI(繁茂期)", ndvi(cube_hi2)),
              ("NDVI を 0-1 へ線形写像", 0.5 * (ndvi(cube_hi2) + 1.0)))
    for label, arr in probes:
        row = []
        for op in ("otsu", "sk_otsu", "cv_otsu"):
            v = float(fs.apply(np.asarray(arr, np.float64), op).mean())
            row.append(v)
            otsu_frac[(label, op)] = v
        print("  " + pad(label, 30, right=False)
              + pad(f"[{arr.min():+.3g}, {arr.max():+.3g}]", 22)
              + "".join(pad(f"{x:.4f}", 11) for x in row))
    print("  (数字は『閾値より上』と判定された画素の割合。真値の被覆率は 発芽期"
          f" {100 * float(scenes[0][0][1].mean()):.1f} % / 繁茂期"
          f" {100 * float(scenes[2][0][1].mean()):.1f} %)")
    print("  → 1 行目と 2 行目は **同じ画像を 4095 倍しただけ**。大津の閾値はアフィン")
    print("     変換に等変なので、この 2 行は一致しなければならない。``sk_otsu`` は")
    print("     一致するが、``otsu`` と ``cv_otsu`` は [0,1] に切り詰めてから数えるので")
    print("     **全画素が上側に落ちる**(判定が 100 %)。12 bit の生カウントを渡すと")
    print("     そうなる、という警告もログも出ない。ExG の行では負側が 1 ビンに潰れる。")
    print("     ``cv_otsu`` は切り詰めに加えて 8 ビット量子化まで入る。")
    print("     ★同じ働きの op が 3 つ並んでいて、**いちばん短い名前がいちばん罠が多い**。")
    aff = {}
    for op in ("otsu", "sk_otsu", "cv_otsu"):
        a = float(fs.apply(np.asarray(cube_lo[:, :, B_GREEN], np.float64), op).mean())
        b = float(fs.apply(4095.0 * cube_lo[:, :, B_GREEN], op).mean())
        aff[op] = abs(a - b)
        print(f"     {op:>8}: 反射率と生カウント(x4095)で判定が"
              f" {100 * abs(a - b):.2f} pp 違う(大津なら 0 のはず)")

    print("\n=== 13. 速度(この機械での実測、96x96 の 1 枚あたり)===")
    probe = scenes[2][0][0]
    for name, fn in METHODS:
        fn(probe)
        t0 = time.perf_counter()
        for _ in range(3):
            fn(probe)
        print("  " + pad(name, 24, right=False)
              + pad(f"{1e3 * (time.perf_counter() - t0) / 3:.2f}", 9) + " ms")
    print("  → アンミキシングだけ 2 桁遅い。和 1 制約つきの解は画素ごとに非負最小二乗")
    print("     を解くループで、素直にはベクトル化できない(``spec_unmix`` の実装どおり)。")
    print("     制約を外せば 3 桁速いが、負の存在量と 1 を超える存在量が出る。")

    print("\n=== 14. まとめ ===")
    mab = {n: np.mean([abs(res[s][n]["bias"]) for s in range(3)]) for n, _ in METHODS}
    lines = (
        ("ゼロ点(大津・緑)で足りるか",
         f"足りない。全段で同じ向きに上振れ(+{min(zb):.1f}〜+{max(zb):.1f} pp)"),
        ("可視だけでどこまで行けるか",
         f"ExG + 大津で全段 |偏り| 平均 {mab['ExG + 大津']:.2f} pp。近赤外なしでも実用域"),
        ("近赤外を足すと何が変わるか",
         f"NDVI + 大津 {mab['NDVI + 大津']:.2f} pp。効くのは枯れ葉と湿った土のある場面"),
        ("混合画素はどうするか",
         f"分数で答えられるのはアンミックスだけ({mab['アンミックス3(+影)']:.2f} pp)。"
         "ただし端成分を知っている前提"),
        ("端成分を画像から取れるか",
         "PPI は反射率 0.1 % の雑音で葉を見失う。純画素が多いほど壊れやすい"),
        ("いちばん危ないのは",
         "『明るさそのもの』を手掛かりにすること(影・湿った土・照度で反転する)"),
        ("測り方でいちばん危ないのは",
         "1 つの数字に丸めること。段階・偏り/散らばり・適合率/再現率を分ける"),
    )
    for q, a in lines:
        print("  " + pad(q, 32, right=False) + a)
    print(f"\n  全体の所要 {time.perf_counter() - t_start:.1f} 秒")

    # ---- 自己検査(速さは assert しない)------------------------------------- #
    # (1) 合成が要求どおり:混合画素が実在し、被覆率が段階で分かれている
    assert 0.02 < truth_cover[0] < 0.20, truth_cover[0]
    assert 0.60 < truth_cover[2] < 0.95, truth_cover[2]
    for s in range(len(STAGES)):
        assert mixed_frac[s] > 0.10, (s, mixed_frac[s])
    # (2) ゼロ点は全段で同じ向きに上振れし、散らばりでは説明できない(= 偏り)
    for s in range(len(STAGES)):
        d = res[s]["大津・緑(ゼロ点)"]
        assert d["bias"] > 5.0, (s, d["bias"])
        assert d["scatter"] < 1.0, (s, d["scatter"])          # 枚数では消えない
    # 低被覆率では「ほぼ全部を植生と答える」壊れ方 —— 適合率と再現率を分けたから見える
    assert res[0]["大津・緑(ゼロ点)"]["prec"] < 0.6, res[0]["大津・緑(ゼロ点)"]["prec"]
    assert res[0]["大津・緑(ゼロ点)"]["rec"] > 0.90, res[0]["大津・緑(ゼロ点)"]["rec"]
    # 「壊れている段階」は指標で変わる:偏りの最悪と適合率の最悪は別の段階
    assert int(np.argmax([abs(res[s]["大津・緑(ゼロ点)"]["bias"]) for s in range(3)])) \
        != int(np.argmin([res[s]["大津・緑(ゼロ点)"]["prec"] for s in range(3)]))
    # ExG > 0(固定)は「ほぼ全画素を植生」= 再現率 1.0 なのに適合率 0.2 未満
    assert res[0]["ExG > 0(固定)"]["rec"] > 0.99, res[0]["ExG > 0(固定)"]["rec"]
    assert res[0]["ExG > 0(固定)"]["prec"] < 0.20, res[0]["ExG > 0(固定)"]["prec"]
    # (3) 指数を使う手法はゼロ点に勝つ(全段の |偏り| 平均で)
    zero_mab = np.mean([abs(res[s]["大津・緑(ゼロ点)"]["bias"]) for s in range(3)])
    for name in ("ExG + 大津", "NDVI + 大津", "アンミックス3(+影)"):
        m_ab = np.mean([abs(res[s][name]["bias"]) for s in range(3)])
        assert m_ab < 0.5 * zero_mab, (name, m_ab, zero_mab)
    # (4) 混合画素で分数を返せるのはアンミキシングだけ:f のビンに沿って単調に上がる
    u3 = np.concatenate([m.ravel() for m, _ in allmaps["アンミックス3(+影)"]])
    means = [u3[idx == i].mean() for i in range(len(lbls))]
    assert all(means[i] < means[i + 1] for i in range(len(means) - 1)), means
    assert means[0] < 0.15 and means[-1] > 0.85, (means[0], means[-1])
    # (5) 崖 (a) 影:ゼロ点は影で悪化し、アンミックス3 は動かない
    for s in (0, 2):
        zs = [abs(shadow_rows[(s, sv)]["大津・緑(ゼロ点)"]["bias"])
              for sv in (0.0, 0.4, 0.8, 1.0)]
        assert max(zs) > zs[0] + 4.0, (s, zs)
        us = [abs(shadow_rows[(s, sv)]["アンミックス3(+影)"]["bias"])
              for sv in (0.0, 0.4, 0.8, 1.0)]
        assert max(us) < 3.0, (s, us)
    # (6) 崖 (b) 画素の大きさ:混合率は単調に上がり、二値手法の偏りが伸びる
    subs = (4, 6, 8, 12, 16, 24, 32, 48)
    mfs = [gsd_rows[(2, sub)][0] for sub in subs]
    assert all(mfs[i] <= mfs[i + 1] for i in range(len(mfs) - 1)), mfs
    assert mfs[-1] > 0.85, mfs[-1]
    fine = abs(gsd_rows[(0, 4)][1]["NDVI + 大津"]["bias"])
    coarse = abs(gsd_rows[(0, 24)][1]["NDVI + 大津"]["bias"])
    assert coarse > fine + 2.0, (fine, coarse)
    # 繁茂期の ExG は逆向き(下振れ)に伸びる —— 向きは段階で反転する
    assert gsd_rows[(2, 48)][1]["ExG + 大津"]["bias"] \
        < gsd_rows[(2, 4)][1]["ExG + 大津"]["bias"] - 3.0, (
            gsd_rows[(2, 4)][1]["ExG + 大津"]["bias"],
            gsd_rows[(2, 48)][1]["ExG + 大津"]["bias"])
    # (7) ★PPI は雑音で壊れる —— 純画素が 6 割以上あっても葉を拾わない。
    #     一方で雑音ゼロなら同じ場面で当てる = 崖の原因は純画素の不足ではない。
    assert ppi_noise[0.0][1], ppi_noise[0.0]
    assert not ppi_noise[0.004][1], ppi_noise[0.004]
    assert ppi_gsd[6][0] > 0.60, ppi_gsd[6]
    # 純画素が消えるほうの崖も実在する(雑音ゼロで画素を大きくすると被覆率が外れる)。
    # **NDVI では見えない** —— 比は合ったまま大きさ(NIR)が縮むので、そこを assert する。
    assert ppi_gsd[48][0] < 0.05, ppi_gsd[48]
    assert abs(ppi_gsd[48][2]) > 10.0 > abs(ppi_gsd[6][2]), (ppi_gsd[6], ppi_gsd[48])
    # 葉側の端成分は本物同然のまま(比も大きさも)、崩れているのは **土側** である
    assert ppi_gsd[48][1] > 0.8 * NDVI_LEAF, ppi_gsd[48]
    assert ppi_gsd[48][3] > 0.8 * RHO["leaf"][B_NIR], ppi_gsd[48]
    assert ppi_gsd[48][4] > ppi_gsd[6][4] + 0.10, (ppi_gsd[6][4], ppi_gsd[48][4])
    # (8) 崖 (c) 湿った土でゼロ点の極性が反転する(再現率が落ちる)
    dry = cond_rows[(2, "乾いた土")][1]["大津・緑(ゼロ点)"]
    wet = cond_rows[(2, "湿った土(暗い)")][1]["大津・緑(ゼロ点)"]
    assert wet["rec"] < dry["rec"] - 0.30, (dry["rec"], wet["rec"])
    # (9) 崖 (d) 固定閾値は段階によらず同じ符号(偏り)、大津は小さい
    for s in range(3):
        assert res[s]["ExG > 0(固定)"]["bias"] > 5.0, (s, res[s]["ExG > 0(固定)"]["bias"])
        assert abs(res[s]["ExG > 0(固定)"]["bias"]) > abs(res[s]["ExG + 大津"]["bias"])
    # (10) 崖 (e) 照度:**倍率だけ**変えた対照で、壊れるのはアンミックス2 だけ
    ctrl = ill_rows[("暗いだけ(対照)", 2)]
    ctrl2 = ill_rows[("暗い+雑音も比例(対照2)", 2)]
    base = ill_rows[("晴れ", 2)]
    assert abs(ctrl["アンミックス2(葉+土)"]["bias"]) \
        > abs(base["アンミックス2(葉+土)"]["bias"]) + 5.0, (
            base["アンミックス2(葉+土)"]["bias"], ctrl["アンミックス2(葉+土)"]["bias"])
    # 倍率だけでは動かない手法(大津の閾値はアフィン等変、正規化指数は分母で割る)
    for name in ("大津・緑(ゼロ点)", "NDVI + 大津", "アンミックス3(+影)"):
        assert abs(ctrl[name]["bias"] - base[name]["bias"]) < 2.0, (
            name, base[name]["bias"], ctrl[name]["bias"])
    # ExG は倍率そのものではなく S/N で動く:雑音も比例させれば元に戻る
    assert abs(ctrl["ExG + 大津"]["bias"] - base["ExG + 大津"]["bias"]) > 1.0, (
        base["ExG + 大津"]["bias"], ctrl["ExG + 大津"]["bias"])
    assert abs(ctrl2["ExG + 大津"]["bias"] - base["ExG + 大津"]["bias"]) < 1.0, (
        base["ExG + 大津"]["bias"], ctrl2["ExG + 大津"]["bias"])
    # 対照2 でもアンミックス2 は壊れたまま = あちらは倍率そのものが原因
    assert abs(ctrl2["アンミックス2(葉+土)"]["bias"]) \
        > abs(base["アンミックス2(葉+土)"]["bias"]) + 5.0, ctrl2["アンミックス2(葉+土)"]["bias"]
    # (11) ★道具の穴:3 つの大津が同じ入力に違う答えを返す。sk_otsu だけがアフィン不変。
    assert aff["sk_otsu"] < 1e-12, aff
    assert aff["otsu"] > 0.10, aff
    assert aff["cv_otsu"] > 0.10, aff
    # ExG(負が半分ある)でも otsu と sk_otsu は一致しない
    k = "ExG(発芽期・負が半分)"
    assert abs(otsu_frac[(k, "otsu")] - otsu_frac[(k, "sk_otsu")]) > 1e-3, otsu_frac
    # (12) ★道具の穴:spec_unmix は B=3(色画像)を拒否する = RGB を解く経路が無い
    try:
        specops.spec_unmix(cube_hi2[:, :, :3], E_LEAF_SOIL[:, :3], constrained=False)
        raise AssertionError("B=3 が通ってしまった(この PoC の前提が変わっている)")
    except ValueError:
        pass
    # (13) NDVI 線形換算は原理どおり上振れし、**混合画素だけで見ると全体より大きい**
    assert lin_bias > 0.0, lin_bias
    assert lin_bias > 100.0 * abs(float((lin - tcat).mean())), lin_bias
    print("\nPASS")


if __name__ == "__main__":
    main()
