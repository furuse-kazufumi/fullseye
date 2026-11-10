# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""太陽電池セルの EL 画像から発電損失を推定する —— 「暗い = 不活性」ではない。

結晶シリコンセルに順方向電流を流すと発光する(エレクトロルミネッセンス、EL)。
その像を撮って**クラック・フィンガー断線・電気的に孤立した暗領域**を見つけ、
**不活性面積率**(発電に寄与しない面積の割合)で等級づけする、という仕事です。
やっかいなのは、EL 像には欠陥以外の暗いものが大量に写ること —— 100 本の
フィンガー電極、3 本のバスバー、多結晶の**結晶粒の明暗むら**(暗い粒も発電して
いる)、レンズのビネッティング。「暗い画素の割合」を 1 つの数字に畳んだ瞬間、
これらが全部「損失」に化けます。

EXTEND: 実写に差し替えるなら :func:`make_scene` が返す辞書の ``img`` を EL 画像に、
``iso`` / ``fi_bands`` / ``crack_lines`` を検査員の marking に置き換えます。
**種別ごとに分けた真値が要ります** —— 面積率(孤立領域)・本数(断線)・長さ
(クラック)は別の量なので、「欠陥マスク」1 枚に畳んだ時点で測れません。
フィンガーの周期 :data:`PITCH` はセル設計から先に計算し、行プロファイルの
周期と突き合わせること。ビネッティングの補正は本来フラットフィールド較正で
やるものですが、この PoC は **較正無しで画像自身から cos^4 則を当てはめる**
経路を測っています(較正フレームがあるならそれを使うほうが良い)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★★**ゼロ点(大域しきい値 Otsu の暗画素率)は 20.8 % で、真値 4.77 % の
   4.4 倍**。内訳を真値マスクで割ると、暗画素の 43 % はフィンガー/バスバー、
   31 % はビネッティングと結晶粒 —— **本当の不活性領域は暗画素の 21 % しか
   無い**。等級は D(真値は C)。面積率を 1 つに畳むと結晶粒が損失に化ける。
2. **フィンガー/バスバーを行・列の中央値プロファイルで割り、孤立領域 /
   断線帯 / クラックを別々の門で取る**と、不活性面積率は 4.77 % → 推定
   4.61 %(誤差 -0.15 ポイント)、クラック 5 本の再現率 0.88〜1.00(一致
   423 px / 真値 450 px、偽 0 px)、断線 8 本中 8 本、偽 0。等級 C で真値と一致。
3. ★★**sk_frangi の出力は画像ごとの最大値で正規化される —— 尺度は「その
   画像でいちばん強いリッジ」が決める**。校正線を貼って固定しようとしても、
   実クラックと同じ線(幅 1.5 px)では応答 0.69 で最大にならず何も固定しない。
   幅 3 px・透過 0 の強い線なら 3 場面とも 1.00。校正なしが壊れるのは**欠陥
   ゼロの側**で偽クラック 147 px(校正ありは 0 px)—— 良品ほど偽検出が出る。
   ★予想「深いクラックを 1 本足すと他の 5 本が消える」は外れた(校正なしの
   再現率 0.99 → 0.97。応答は 0.66 → 0.41 に縮んだがしきい値 0.30 の上)。
4. ★結晶粒のコントラスト c を 0 → 0.60 で振ると、偽クラックは c=0.24 から
   30 px を超える。**ヘッセ行列の比からの予測 c≈1.48 は 6 倍外れた** ——
   粒の境界を「段差」と見たのが間違いで、幅 σ 程度の暗い粒は谷そのもの。
   断線は偽が最大 2 本のまま**一致が 8/8 → 2/8 に落ちる**(c=0.24 から、
   予測 c>0.20 と一致)—— 暗い粒が帯を飲み込み、形の門が塊ごと落とす。
   面積率の誤差は c=0.60 でも -2.10 ポイント(T_ISO を割る粒は無い)。
5. ★クラック幅 0.5 → 3.0 px: 再現率 0.5 を超えるのは 1.25 px から。予測
   「幅 × 深さ」の線形則(校正線 3 px × 1.0 = 1.0、上限 0.30 → 1.38 px)と
   一致し、実測の応答は線形予測の 0.62〜1.19 倍。**崖の位置は校正線の
   幅 × 深さとヒステリシス上限の積で決まる**。
6. ★ビネッティング強さ 0 → 1.0: cos^4 当てはめは 4 種の平均で 0.03 / 0.27 /
   0.51 / 0.75 / 0.97(散らばり ≤ 0.12、粒の抽選がリングの明るさを決める)。
   面積率誤差は当てはめ込みで -0.14、行列プロファイルだけでも強さ 1.0 で
   -0.16 ポイント —— **cos^4 の当てはめはこの場面では要らなかった**。予想
   「補正なしなら強さ 0.76 で隅が偽の孤立領域」は、格子除去の行列プロファイル
   が cos^4 の分離可能な部分を先に吸うので起きない(幾何の予測: 隅は 1.14 倍
   に戻り、暗く残るのは辺の中央 0.94)。
7. 光子数 K を 2000 → 8 で振ると、断線は K=200 まで 8/8、K=50 で 7/8。
   予測「σ=1 平滑後の雑音が余裕 0.25 の半分になる K≈12」は **4 倍楽観的**
   —— 帯は割れる前に画素ごとの誤分類で形の門から外れる。雑音の崖では
   偽クラックが先に増え(K=20 で 634 px)、見逃しは後から来る(K=8 で
   再現率 0.23)。
8. ★★**実セル(公開の SIPV-EL、I-V の実測が真値)では、遮光マスク(S1〜S6)なら暗部の面積が
   出力の低下を追うが、S7(9 枚、正体は推定)では追わない**。
   データの暗部は配布元の論文のとおり**セル表面に置いた遮光マスク**(アルミ箔つきの厚紙)で、
   電気的な不活性領域ではない —— ここで測ったのは「暗部の面積が I-V の出力低下を追うか」。
   マスクつき 195 枚(32 セル、S7 を含む)で暗部の増えと出力低下の順位相関は、ゼロ点 ρ 0.44、格子の
   細い成分だけを割る経路 ρ 0.64、合成どおりの中央値プロファイルで割る経路 ρ 0.04(縁の帯状の
   マスクを丸ごと消す。細い成分の窓 15 px と門の閾値は実データを見て決めた)。S7(論文の分類の
   「その他の欠陥」と推定)は EL がセル全体で 0.75〜0.90 倍に暗くなるのに、出力低下は中央値
   8.9 % —— ゼロ点は暗部を +50 pt と数え、細い成分だけ割る経路も +1 pt で 7.6 pt 過小に言う。
   **全体が暗くなる欠陥は、面積ではどちら向きにも測れない**。

【グラウンドトゥルース】
セルは**閉形式**で合成する(2 倍のスーパーサンプリングで描いて平均し、
サブピクセル幅のフィンガーとクラックを正しく写す): フィンガー 100 本
(周期 3.85 px、幅 0.9 px、透過 0.45)、バスバー 3 本(幅 6 px、透過 0.25)、
結晶粒 = 70 個の Voronoi 領域(明るさ 1 ± c)、クラック 5 本(幅 1.5 px、
透過 0.35、向き 15〜155 度)、孤立領域 2 つ(左上と右下の三角形、透過 0.20、
面積 = 幾何で決まる真値 4.77 %)、断線 8 本(フィンガー沿いの帯、透過 0.55)。
撮像 = cos^4 ビネッティング(``aug_vignette``)+ ガウスぼけ σ 0.7 px +
ポアソン雑音(明るさ 1.0 あたり 200 光子)。孤立領域は行・列を丸ごと覆わない
形にしてある —— 右端を帯にしたら列プロファイルが帯ごと割って消した。
等級の数値境界(A<1 % / B<3 % / C<8 % / D)は **IEC TS 60904-13 の欠陥分類
(クラック・不活性領域・断線)に倣った、この PoC の仮置き**であって規格の
数値ではない。

来歴(公開文献のみ): IEC TS 60904-13:2018 *Electroluminescence of photovoltaic
modules* / Fuyuki et al., *Appl. Phys. Lett.* 86 (2005) 262108 —— EL による
セル診断 / Köntges et al., *Solar Energy Materials & Solar Cells* 95 (2011)
1131 —— クラックが発電に与える影響 / Frangi et al., MICCAI (1998) —— 管状
構造検出。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, median_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import realdata                                                  # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N = 400                     # セル 1 枚の視野 [px]
SS = 2                      # スーパーサンプリング倍率(サブピクセル幅を正しく写す)
SEED = 7

PITCH = 3.85                # フィンガー周期 [px]
N_FINGER = 100
FINGER_Y0 = 7.5             # 1 本目の位置 [px]
FINGER_W = 0.9              # フィンガー幅 [px]
FINGER_T = 0.45             # フィンガーの透過率(下は暗い)
BUSBAR_X = (N / 6.0, N / 2.0, 5.0 * N / 6.0)
BUSBAR_W = 6.0
BUSBAR_T = 0.25

GRAIN_N = 70                # 結晶粒の数(Voronoi)
GRAIN_C = 0.12              # 粒の明るさ 1 ± c

CRACK_W = 1.5               # クラック幅 [px]
CRACK_T = 0.35              # クラックの透過率
#: クラック 5 本: (中心 y, 中心 x, 長さ [px], 向き [deg、水平から])
CRACKS = ((120.0, 300.0, 90.0, 15.0), (250.0, 120.0, 110.0, 40.0),
          (300.0, 300.0, 80.0, 70.0), (90.0, 180.0, 70.0, 115.0),
          (330.0, 100.0, 100.0, 155.0))

ISO_T = 0.20                # 孤立領域(発電しない)の透過率
ISO_TRI = (60.0, 80.0)      # 左上の三角形: x/60 + y/80 < 1(クラックで隅が切れた)
ISO_TRI2 = (330.0, 250.0)   # 右下の三角形: (400,330)-(250,400) を結ぶクラックの外側

FI_T = 0.55                 # 断線した先(バスバーへ電流が戻れない帯)の透過率
#: 断線 8 本: (フィンガー番号, 帯の x 範囲) —— 外側区間(端〜バスバー)に置く
FI_BANDS = ((12, 22.0, 58.0), (25, 20.0, 60.0), (38, 0.0, 50.0),
            (47, 10.0, 62.0), (58, 350.0, 400.0), (70, 345.0, 383.0),
            (83, 0.0, 28.0), (91, 300.0, 345.0))

VIG_A, VIG_B = 0.5, 0.5     # aug_vignette の強さ / 落ち込み半径
BLUR = 0.7                  # ぼけ σ [px]
PHOTONS = 200               # 明るさ 1.0 あたりの光子数(ポアソン雑音)
EXPOSURE = 0.8              # 健全部の明るさ

T_ISO, T_FI = 0.40, 0.80    # 分類しきい値(平坦化後の相対明るさ)
REF_W, REF_T = 3.0, 0.0     # 校正線: 幅 3 px・透過 0(画像中のどのリッジより強い)
HYST_LOW, HYST_HIGH = 0.18, 0.30   # リッジのヒステリシス(校正線 = 1.0 の尺度)
MIN_CRACK_PX = 6            # これより短い骨格片はクラックと呼ばない(最小クラック長)
DEEP_CRACK = (200.0, 250.0, 80.0, 80.0, 2.5, 0.0)   # 3 節で足す深いクラック(幅 2.5 px、透過 0)
GRADES = ((1.0, "A"), (3.0, "B"), (8.0, "C"), (100.0, "D"))

_LAB = fs.ledger            # blob 族の公開経路


# --------------------------------------------------------------------------- #
# 場面を作る                                                                    #
# --------------------------------------------------------------------------- #
def _seg_dist(yy, xx, cy, cx, length, deg):
    """点 (yy,xx) から線分(中心・長さ・向き)までの距離。"""
    th = np.deg2rad(deg)
    ux, uy = np.cos(th), np.sin(th)
    dx, dy = xx - cx, yy - cy
    t = np.clip(dx * ux + dy * uy, -length / 2.0, length / 2.0)
    return np.hypot(dx - t * ux, dy - t * uy)


def _iso_mask(yy, xx):
    """孤立領域 2 つ(どちらも隅の三角形。行・列を丸ごと覆わないようにしてある)。"""
    tri = (xx / ISO_TRI[0] + yy / ISO_TRI[1]) < 1.0
    x0, y0 = ISO_TRI2
    tri2 = (xx - x0) * (N - y0) + (yy - N) * (N - x0) > 0.0
    return tri | tri2


def make_scene(seed: int = SEED, grain_c: float = GRAIN_C, crack_w: float = CRACK_W,
               vig_a: float = VIG_A, photons: float = PHOTONS,
               defects: bool = True, deep: bool = False) -> dict:
    """EL 画像と、種別ごとの真値を返す。``deep`` で 6 本目の深いクラックを足す。"""
    rng = np.random.default_rng(seed)
    n = N * SS
    yy, xx = (np.mgrid[0:n, 0:n] + 0.5) / SS          # 最終画素の座標系 [px]

    # 結晶粒: Voronoi(粗い格子で作って 2 倍に伸ばす)
    seeds = rng.uniform(0, N, (GRAIN_N, 2))
    gain = 1.0 + grain_c * rng.uniform(-1.0, 1.0, GRAIN_N)
    gy, gx = np.mgrid[0:N, 0:N] + 0.5
    d2 = (gy[..., None] - seeds[:, 0]) ** 2 + (gx[..., None] - seeds[:, 1]) ** 2
    grain_lo = gain[np.argmin(d2, axis=-1)]
    base = np.repeat(np.repeat(grain_lo, SS, 0), SS, 1)

    # フィンガー(周期)とバスバー
    fy = yy - FINGER_Y0
    dist_f = np.abs(((fy + PITCH / 2) % PITCH) - PITCH / 2)
    in_rows = (fy > -PITCH / 2) & (fy < (N_FINGER - 1) * PITCH + PITCH / 2)
    finger = (dist_f < FINGER_W / 2) & in_rows
    busbar = np.zeros_like(finger)
    for bx in BUSBAR_X:
        busbar |= np.abs(xx - bx) < BUSBAR_W / 2
    base = base * np.where(finger, FINGER_T, 1.0) * np.where(busbar, BUSBAR_T, 1.0)

    crack_lines = []
    iso = np.zeros((N, N), bool)
    fi_bands = []
    if defects:
        cracks = [(cy, cx, ln, deg, crack_w, CRACK_T) for cy, cx, ln, deg in CRACKS]
        if deep:
            cracks.append(DEEP_CRACK)
        for cy, cx, ln, deg, w, t in cracks:
            base = base * np.where(_seg_dist(yy, xx, cy, cx, ln, deg) < w / 2, t, 1.0)
        yl, xl = np.mgrid[0:N, 0:N] + 0.5
        for cy, cx, ln, deg, w, t in cracks:
            crack_lines.append(_seg_dist(yl, xl, cy, cx, ln, deg) < 0.5)
        iso_hi = _iso_mask(yy, xx)
        base = base * np.where(iso_hi, ISO_T, 1.0)
        iso = iso_hi.reshape(N, SS, N, SS).mean(axis=(1, 3)) > 0.5
        for j, x0, x1 in FI_BANDS:
            yj = FINGER_Y0 + j * PITCH
            band = (np.abs(yy - yj) <= PITCH / 2) & (xx >= x0) & (xx < x1)
            base = base * np.where(band, FI_T, 1.0)
            fi_bands.append((np.abs(yl - yj) <= PITCH / 2) & (xl >= x0) & (xl < x1))

    cell = base.reshape(N, SS, N, SS).mean(axis=(1, 3))
    grid = (finger | busbar).reshape(N, SS, N, SS).mean(axis=(1, 3)) > 0.5

    # 撮像: ビネッティング(op) → ぼけ(op) → ポアソン雑音
    img = np.asarray(fs.apply(np.clip(cell * EXPOSURE, 0, 1), "aug_vignette",
                              a=vig_a, b=VIG_B))
    img = np.asarray(fs.apply(img, "gaussian", a=(BLUR - 0.3) / 2.7))
    img = rng.poisson(img * photons) / float(photons)
    img = np.clip(img, 0.0, 1.0)
    return {"img": img, "cell": cell, "grid": grid, "iso": iso,
            "crack_lines": crack_lines, "fi_bands": fi_bands,
            "crack_len": [c[2] for c in cracks] if defects else [],
            "iso_rate": 100.0 * iso.mean()}


def grade(rate_pct: float) -> str:
    for lim, g in GRADES:
        if rate_pct < lim:
            return g
    return "D"


# --------------------------------------------------------------------------- #
# 解析 —— fullseye の op を並べる                                               #
# --------------------------------------------------------------------------- #
def _radius(shape) -> np.ndarray:
    """``aug_vignette`` と同じ正規化半径(中心 0、隅 1)。"""
    h, w = shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    return np.hypot(yy - cy, xx - cx) / np.hypot(cy, cx)


def vignette_model(shape, a: float, R: float) -> np.ndarray:
    """``aug_vignette`` と同じ cos^4 則。当てはめの前向きモデル。"""
    r = _radius(shape)
    return 1.0 - a + a / (1.0 + (r / R) ** 2) ** 2


FIT_TRIM = 0.7              # リングの 95 % 分位のこの倍率より暗い画素は「欠陥」として捨てる


def _ring_stat(vals: np.ndarray) -> float:
    """リング 1 本の健全な明るさ。暗い側を刈ってから中央値。

    EL の欠陥は暗くしかしない(明るくする欠陥は無い)。そこで上側 95 % 分位
    を「健全の上限」とし、その :data:`FIT_TRIM` 倍より暗い画素を捨てて残りの
    中央値を取る。**単純な上側分位ではだめ**だった: 隅のリングは 4 隅の
    小さな面積しか無く、そのうち 2 隅が孤立領域で暗いと、80 % 分位が
    「健全側の 60 % 分位」にすり替わってリングごとに意味が変わる
    (強さ 0.5 を 0.9 と当てた)。刈ってから中央値なら、暗い割合が
    リングごとに違っても同じ統計量になる。
    """
    hi = float(np.quantile(vals, 0.95))
    keep = vals > FIT_TRIM * hi
    return float(np.median(vals[keep])) if keep.any() else hi


def fit_vignette(img: np.ndarray, nbins: int = 10, valid=None) -> tuple[float, float]:
    """半径ビンの「刈ってから中央値」に cos^4 則を当てはめる(画素数で重みづけ)。

    ``valid`` は当てはめに使う画素(既定は全部)。フィンガーの無い上下の余白は
    外側のリングにだけ混ざって分位を持ち上げるので、フィンガーの範囲
    (設計値)に限る。ビンを画素数で重みづけるのは、中心と隅のリングには
    結晶粒が数個しか入らず、その粒の明暗の抽選がそのまま当てはめに乗るから
    (6 節で種を変えて測る)。
    """
    r = _radius(img.shape)
    if valid is None:
        valid = np.ones(img.shape, bool)
    edges = np.linspace(0, 1.0, nbins + 1)
    rc, med, wt = [], [], []
    for k in range(nbins):
        sel = (r >= edges[k]) & (r < edges[k + 1]) & valid
        if sel.sum() > 50:
            rc.append(0.5 * (edges[k] + edges[k + 1]))
            med.append(_ring_stat(img[sel]))
            wt.append(float(sel.sum()))
    rc, lm = np.asarray(rc), np.log(np.asarray(med))
    wt = np.asarray(wt) / np.sum(wt)
    best = (np.inf, 0.0, 1.0)
    for a in np.linspace(0, 1, 51):
        for R in np.arange(0.35, 1.5001, 0.025):
            m = np.log(1.0 - a + a / (1.0 + (rc / R) ** 2) ** 2)
            res = lm - m
            mu = float(np.sum(wt * res))
            cost = float(np.sum(wt * (res - mu) ** 2))
            if cost < best[0]:
                best = (cost, float(a), float(R))
    return best[1], best[2]


def flatten(img: np.ndarray, use_fit: bool = True) -> tuple[np.ndarray, tuple]:
    """ビネッティングを割る。補正そのものは ``aug_vignette`` を前向きモデルに使う。

    当てはめは **グレースケール・クロージング(3 px)で細い暗線を消した包絡**に
    対して行う。生画像のままだと、フィンガーの無い上下の余白(数行)が隅の
    リングにだけ混ざり、リングの分位が隅で跳ね上がって強さを 0.42 と当てた。
    フィンガー・クラックは 3 px より細いのでクロージングで消え、バスバー・
    孤立領域は残るが暗くしかしないので上側分位が効く。
    """
    if not use_fit:
        return img, (np.nan, np.nan)
    env = np.asarray(fs.apply(img, "gray_closing", a=0.0))
    rows = np.arange(img.shape[0])
    span = (rows >= FINGER_Y0 - PITCH / 2) & (rows <= FINGER_Y0 + (N_FINGER - 1) * PITCH + PITCH / 2)
    a, R = fit_vignette(env, valid=np.repeat(span[:, None], img.shape[1], axis=1))
    b = min(1.0, max(0.0, (R - 0.35) / 1.15))       # 格子探索の端 R=1.5 で 1+1e-16 になる
    v = np.asarray(fs.apply(np.ones_like(img), "aug_vignette", a=a, b=b))
    return img / np.maximum(v, 1e-3), (a, R)


def degrid(flat: np.ndarray) -> np.ndarray:
    """フィンガー(行の関数)とバスバー(列の関数)を中央値プロファイルで割る。"""
    p = np.median(flat, axis=1)
    s1 = flat / np.maximum(p / np.median(p), 1e-3)[:, None]
    q = np.median(s1, axis=0)
    s = s1 / np.maximum(q / np.median(q), 1e-3)[None, :]
    return s / float(np.median(s))


REF_ROWS = 14               # 校正線を貼る帯の高さ [px]


def _skeleton_length(sk: np.ndarray) -> float:
    """8 近傍の骨格の折れ線長(縦横 1、斜め √2)。"""
    sk = sk.astype(bool)
    n_h = int(np.count_nonzero(sk[:, 1:] & sk[:, :-1]))
    n_v = int(np.count_nonzero(sk[1:, :] & sk[:-1, :]))
    n_d = int(np.count_nonzero(sk[1:, 1:] & sk[:-1, :-1]))
    n_d += int(np.count_nonzero(sk[1:, :-1] & sk[:-1, 1:]))
    return n_h + n_v + np.sqrt(2.0) * n_d


def ridge_map(s: np.ndarray, calibrate: bool = True, ref_w: float = REF_W,
              ref_t: float = REF_T) -> tuple[np.ndarray, float]:
    """暗いリッジ(sk_frangi)の応答と、校正線の応答(= 尺度が固定できたかの証拠)。

    ``calibrate=True`` なら、既知の深さ・幅の**校正線**を画像の下に貼ってから
    Frangi を掛ける。``sk_frangi`` は出力を画像ごとの最大値で正規化するので、
    こうしないと「いちばん強いリッジ = 1.0」が雑音でも成り立ってしまう。
    **校正線は画像中のどのリッジより強くなければならない**(最大値で割る
    のだから、2 番目では尺度を決められない)。最初は実クラックと同じ
    幅 1.5 px・透過 0.35 で貼って、校正線の応答が 0.69 —— 尺度はクラック
    のほうで決まっていて、校正線は何も固定していなかった(3 節で測る)。
    返す配列は校正線を切り落とした元の大きさ。
    """
    v = np.clip(s / 1.25, 0.0, 1.0)
    if calibrate:
        strip = np.ones((REF_ROWS, v.shape[1]))
        full = int(np.floor(ref_w))
        r0 = REF_ROWS // 2 - full // 2
        strip[r0:r0 + full, :] = ref_t
        frac = ref_w - full
        if frac > 0:
            strip[r0 + full, :] = 1.0 - frac * (1.0 - ref_t)
        # ★校正線も**同じ撮像系(ぼけ)を通す**。ぼかさずに貼った校正線は実クラック
        #   より 2.4 倍強く応答し、崖が太い側へ寄った(2026-09-07 に踏んだ)。
        strip = np.asarray(fs.apply(strip, "gaussian", a=(BLUR - 0.3) / 2.7))
        v = np.vstack([v, strip / 1.25])
    ridge = np.asarray(fs.apply(v, "sk_frangi", a=0.25, b=0.5))
    if calibrate:
        ref_resp = float(ridge[s.shape[0]:].max())
        ridge = ridge[:s.shape[0]].copy()
        ridge[-2:, :] = 0.0               # 校正線の縁の影響を落とす
        return ridge, ref_resp
    return ridge, float("nan")


def crack_skeleton(s: np.ndarray, calibrate: bool = True, ref_w: float = REF_W,
                   low: float = HYST_LOW, high: float = HYST_HIGH) -> np.ndarray:
    """リッジ応答 → ヒステリシス → 骨格(1 px 幅のクラック中心線)→ 最小長。

    ``hysteresis_threshold`` op のしきい値は下 0.2〜0.5 / 上 0.5〜0.8 に固定
    されているので、応答にゲイン ``0.5/high`` を掛けて上限を 0.5 に合わせる。
    バスバーの縁(設計値 ±4 px)は除く —— 列プロファイルで割っても縁の
    ぼけが 1 px の縦リッジとして残り、短い偽片になる。
    """
    ridge, _ = ridge_map(s, calibrate=calibrate, ref_w=ref_w)
    gain = 0.5 / high
    low_a = (low * gain - 0.2) / 0.3
    assert 0.0 <= low_a <= 1.0, low_a
    hyst = np.asarray(fs.apply(np.clip(ridge * gain, 0, 1), "hysteresis_threshold",
                               a=low_a, b=0.0))
    sk = np.asarray(fs.apply(hyst, "sk_skeleton")) > 0.5
    cols = np.arange(s.shape[1])
    for bx in BUSBAR_X:
        sk[:, np.abs(cols - bx) <= BUSBAR_W / 2 + 1.0] = False
    lab = _LAB.blob_label(sk, connectivity=8)
    if int(lab.max()) > 0:
        sk = _LAB.blob_select(lab, "area", vmin=float(MIN_CRACK_PX)) > 0
    return sk


def classify(s: np.ndarray) -> dict:
    """平坦化後の明るさで 孤立領域 / 断線帯 を分ける。

    断線帯は**クラックより先に**決める。帯(高さ ≈ 周期 3.85 px)は σ=2 の
    Frangi には立派な水平リッジなので、先にクラックを取ると帯が全部
    クラックに化けて断線が 0/8 になった(2026-09-07 に踏んだ)。帯を
    「細長く水平」で先に取り、その近傍を骨格から除く。
    """
    ss = np.asarray(fs.apply(np.clip(s / 1.25, 0, 1), "gaussian", a=(1.0 - 0.3) / 2.7)) * 1.25
    iso_c = ss < T_ISO
    lab = _LAB.blob_label(iso_c)
    iso = np.zeros_like(iso_c)
    if int(lab.max()) > 0:
        iso = _LAB.blob_select(lab, "area", vmin=150.0) > 0
    fi_c = (ss >= T_ISO) & (ss < T_FI) & ~binary_dilation(iso, iterations=2)
    lab = _LAB.blob_label(fi_c)
    fi = np.zeros_like(fi_c)
    fi_blobs = []
    if int(lab.max()) > 0:
        f = _LAB.blob_features(lab)
        hgt = np.asarray(f["bbox_r1"]) - np.asarray(f["bbox_r0"])
        wid = np.asarray(f["bbox_c1"]) - np.asarray(f["bbox_c0"])
        keep = (hgt <= 9) & (wid >= 12) & (np.asarray(f["area"]) >= 30)
        for k in np.nonzero(keep)[0]:
            m = lab == int(f["label"][k])
            fi |= m
            fi_blobs.append(m)
    return {"smooth": ss, "iso": iso, "fi": fi, "fi_blobs": fi_blobs}


def _visible() -> np.ndarray:
    """バスバーの下(設計値 ±4 px)以外。クラックの再現率はここで数える。"""
    cols = np.arange(N)
    vis = np.ones((N, N), bool)
    for bx in BUSBAR_X:
        vis[:, np.abs(cols - bx) <= BUSBAR_W / 2 + 1.0] = False
    return vis


def analyze(sc: dict, use_fit: bool = True, calibrate: bool = True,
            ref_w: float = REF_W) -> dict:
    """1 枚を通しで解析し、種類別に真値と突き合わせる。"""
    flat, fit = flatten(sc["img"], use_fit=use_fit)
    s = degrid(flat)
    cl = classify(s)
    sk_raw = crack_skeleton(s, calibrate=calibrate, ref_w=ref_w)
    near_iso_det = binary_dilation(cl["iso"], iterations=4)
    sk = sk_raw & ~binary_dilation(cl["fi"], iterations=2) & ~near_iso_det

    # クラック: 本ごとの再現率(真値中心線が骨格の 2 px 以内にある割合。
    # バスバーの下は見えないので真値からも外す)
    sk_d = binary_dilation(sk, iterations=2)
    vis = _visible()
    recall = [float(sk_d[m & vis].mean()) for m in sc["crack_lines"]]
    any_true = np.zeros_like(sk)
    for m in sc["crack_lines"]:
        any_true |= m
    near_true = binary_dilation(any_true, iterations=3)
    near_iso = binary_dilation(sc["iso"], iterations=5)
    matched_len = _skeleton_length(sk & near_true)
    false_len = _skeleton_length(sk & ~near_true & ~near_iso)
    iso_edge_len = _skeleton_length(sk_raw & ~near_true & near_iso)

    # 断線: 真値の帯と 30 % 以上重なる検出があれば一致
    fi_matched = 0
    used = set()
    for band in sc["fi_bands"]:
        for k, b in enumerate(cl["fi_blobs"]):
            if k not in used and (b & band).sum() >= 0.3 * band.sum():
                fi_matched += 1
                used.add(k)
                break
    fi_false = len(cl["fi_blobs"]) - len(used)

    iso_rate = 100.0 * cl["iso"].mean()
    grain_as_iso = 100.0 * (cl["iso"] & ~sc["iso"]).mean()
    return {"s": s, "sk": sk, "cl": cl, "fit": fit,
            "recall": recall, "matched_len": matched_len, "false_len": false_len,
            "iso_edge_len": iso_edge_len, "true_len": float(sum(sc["crack_len"])),
            "fi_matched": fi_matched, "fi_false": fi_false, "fi_n": len(cl["fi_blobs"]),
            "iso_rate": iso_rate, "iso_err": iso_rate - sc["iso_rate"],
            "grain_as_iso": grain_as_iso}


# --------------------------------------------------------------------------- #
# 1. ゼロ点 —— 大域しきい値の暗画素率                                          #
# --------------------------------------------------------------------------- #
def section_zero_point(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点 —— 大域しきい値(Otsu)で暗画素率を出し、不活性面積率と呼ぶ")
    print("=" * 78)
    bright = np.asarray(fs.apply(sc["img"], "otsu")) > 0.5
    dark = ~bright
    rate = 100.0 * dark.mean()
    truth = sc["iso_rate"]
    print("  暗画素率 %.1f %%(真値の不活性面積率 %.2f %% の %.1f 倍)-> 等級 %s"
          "(真値は %s)" % (rate, truth, rate / truth, grade(rate), grade(truth)))

    any_crack = np.zeros_like(dark)
    for m in sc["crack_lines"]:
        any_crack |= m
    any_crack = binary_dilation(any_crack, iterations=1)
    any_fi = np.zeros_like(dark)
    for m in sc["fi_bands"]:
        any_fi |= m
    parts = [("フィンガー/バスバー", sc["grid"]),
             ("孤立領域(本物)", sc["iso"] & ~sc["grid"]),
             ("断線の帯", any_fi & ~sc["grid"] & ~sc["iso"]),
             ("クラック", any_crack & ~sc["grid"] & ~sc["iso"] & ~any_fi)]
    rest = dark.copy()
    print("\n   暗画素の内訳                  画素      暗画素の %   セルの %")
    out = {}
    for name, m in parts:
        n = int((dark & m).sum())
        rest &= ~m
        out[name] = n
        print("   %-24s %8d     %6.1f     %6.2f" % (name, n, 100.0 * n / dark.sum(),
                                                   100.0 * n / dark.size))
    n = int(rest.sum())
    out["結晶粒/ビネッティング"] = n
    print("   %-24s %8d     %6.1f     %6.2f" % ("結晶粒/ビネッティング", n,
                                               100.0 * n / dark.sum(), 100.0 * n / dark.size))
    real = out["孤立領域(本物)"]
    print("\n  ★暗画素のうち本当の不活性領域は %.0f %%。フィンガー/バスバー %.0f %%、"
          "結晶粒とビネッティング %.0f %%。" % (100.0 * real / dark.sum(),
                                            100.0 * out["フィンガー/バスバー"] / dark.sum(),
                                            100.0 * n / dark.sum()))
    print("     **暗い = 不活性ではない**。暗い結晶粒も発電している。")
    figs.save_grid("zero_point_map", [sc["img"], dark.astype(np.float64),
                                      sc["iso"].astype(np.float64)],
                   ["EL 画像(ゼロ点の入力)", "Otsu の暗画素 %.1f %%" % rate,
                    "真値の孤立領域 %.2f %%" % truth],
                   ncols=3, title="ゼロ点: 暗画素率は不活性面積率ではない",
                   caption="単位は %% of セル面積。暗画素の %.0f %% はフィンガーとバスバー、"
                           "%.0f %% は結晶粒とビネッティング。"
                           % (100.0 * out["フィンガー/バスバー"] / dark.sum(), 100.0 * n / dark.sum()))
    return {"rate": rate, "parts": out, "dark_n": int(dark.sum())}


# --------------------------------------------------------------------------- #
# 2. fullseye の経路 —— 種類別に測る                                           #
# --------------------------------------------------------------------------- #
def section_pipeline(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) 平坦化(cos^4 当てはめ)→ 格子除去(行列プロファイル)→ 種類別マスク")
    print("=" * 78)
    r = analyze(sc)
    a_hat, R_hat = r["fit"]
    print("  ビネッティング当てはめ: 強さ %.3f(真値 %.3f)半径 %.3f(真値 %.3f)"
          % (a_hat, VIG_A, R_hat, 0.35 + 1.15 * VIG_B))
    print("  不活性面積率: 真値 %.2f %% / 推定 %.2f %%(誤差 %+.2f ポイント、"
          "粒を孤立と誤った面積 %.2f %%)-> 等級 %s(真値 %s)"
          % (sc["iso_rate"], r["iso_rate"], r["iso_err"], r["grain_as_iso"],
             grade(r["iso_rate"]), grade(sc["iso_rate"])))
    print("  クラック長: 真値 %.0f px / 一致した骨格長 %.0f px / 偽 %.0f px"
          "(孤立領域の縁 %.0f px は別勘定)" % (r["true_len"], r["matched_len"],
                                              r["false_len"], r["iso_edge_len"]))
    print("   本ごとの再現率: " + " / ".join(
        "%.0f°: %.2f" % (c[3], rc) for c, rc in zip(CRACKS, r["recall"])))
    print("  断線: 真値 %d 本 / 一致 %d 本 / 偽 %d 本" % (len(FI_BANDS), r["fi_matched"],
                                                     r["fi_false"]))

    rows = [["不活性面積率 [%]", "%.2f" % sc["iso_rate"], "%.2f" % r["iso_rate"],
             "%+.2f pt" % r["iso_err"]],
            ["クラック長 [px]", "%.0f" % r["true_len"], "%.0f" % r["matched_len"],
             "偽 %.0f px" % r["false_len"]],
            ["クラック再現率(最小)", "1.00", "%.2f" % min(r["recall"]), ""],
            ["断線 [本]", "%d" % len(FI_BANDS), "%d" % r["fi_matched"],
             "偽 %d" % r["fi_false"]],
            ["等級", grade(sc["iso_rate"]), grade(r["iso_rate"]), ""]]
    figs.save_table("by_type", ["量", "真値", "推定", "誤差"], rows,
                    title="種類別に測る(1 つの数字に畳まない)")

    truth_map = np.zeros((N, N))
    for m in sc["fi_bands"]:
        truth_map[m] = 0.4
    for m in sc["crack_lines"]:
        truth_map[binary_dilation(m, iterations=1)] = 0.7
    truth_map[sc["iso"]] = 1.0
    det_map = np.zeros((N, N))
    det_map[r["cl"]["fi"]] = 0.4
    det_map[binary_dilation(r["sk"], iterations=1)] = 0.7
    det_map[r["cl"]["iso"]] = 1.0
    ridge, _ = ridge_map(r["s"])
    figs.save_grid("scene_map",
                   [sc["img"], np.clip(r["s"] / 1.25, 0, 1), ridge, truth_map, det_map,
                    r["cl"]["smooth"] / 1.25],
                   ["EL 画像(フィンガー 100 本・バスバー 3 本)",
                    "平坦化 + 格子除去(相対明るさ)", "Frangi のリッジ応答",
                    "真値(帯 0.4 / クラック 0.7 / 孤立 1.0)",
                    "検出(同じ色分け)", "分類に使う平滑像(σ 1 px)"],
                   ncols=3, title="EL 検査の場面(%d x %d px、1 セル)" % (N, N),
                   caption="孤立領域 2 つ・クラック 5 本・断線 8 本。相対明るさは 1.25 で"
                           "割って [0,1] に収めてある。")
    return r


# --------------------------------------------------------------------------- #
# 3. Frangi の正規化 —— 欠陥ゼロで雑音が 1.0 に伸びる                          #
# --------------------------------------------------------------------------- #
def section_frangi_norm() -> dict:
    print("\n" + "=" * 78)
    print("3) ★sk_frangi は画像ごとの最大値で正規化する —— 尺度は「いちばん強いもの」が決める")
    print("=" * 78)
    scenes = (("欠陥ゼロ", make_scene(defects=False)), ("既定", make_scene()),
              ("既定 + 深いクラック 1 本", make_scene(deep=True)))
    print("  校正線(幅 %.0f px・透過 %.1f、ぼけを通す)の応答 = その画像で校正線が最大かどうか:"
          % (REF_W, REF_T))
    out = {}
    for name, sc in scenes:
        s = degrid(flatten(sc["img"])[0])
        _, weak = ridge_map(s, ref_w=CRACK_W, ref_t=CRACK_T)
        rm, strong = ridge_map(s)
        raw, _ = ridge_map(s, calibrate=False)
        anyt = np.zeros_like(rm, bool)
        for m in sc["crack_lines"][:len(CRACKS)]:
            anyt |= m
        r_cal = analyze(sc, calibrate=True)
        r_raw = analyze(sc, calibrate=False)
        med_cal = float(np.median(rm[anyt])) if anyt.any() else float("nan")
        med_raw = float(np.median(raw[anyt])) if anyt.any() else float("nan")
        out[name] = {"weak": weak, "strong": strong, "false_cal": r_cal["false_len"],
                     "false_raw": r_raw["false_len"],
                     "rec_cal": float(np.mean(r_cal["recall"][:len(CRACKS)])) if anyt.any() else float("nan"),
                     "rec_raw": float(np.mean(r_raw["recall"][:len(CRACKS)])) if anyt.any() else float("nan"),
                     "med_cal": med_cal, "med_raw": med_raw}
        print("   %-22s 校正線の応答: 実クラックと同じ線 %.2f / 強い線 %.2f"
              % (name, weak, strong))
    print("\n   場面                   クラック応答(中央値): 校正あり / なし   偽クラック [px]: あり / なし"
          "   再現率(5 本平均): あり / なし")
    for name, o in out.items():
        print("   %-22s        %5.2f / %5.2f                 %5.0f / %5.0f              %s"
              % (name, o["med_cal"], o["med_raw"], o["false_cal"], o["false_raw"],
                 "  -  " if np.isnan(o["rec_cal"]) else "%.2f / %.2f" % (o["rec_cal"], o["rec_raw"])))
    o0, o1, o2 = out.values()
    print("\n  ★実クラックと同じ線を貼っても応答 %.2f で最大ではない —— 尺度はクラック"
          "の側で決まり、校正線は何も固定しない。" % o1["weak"])
    print("     幅 %.0f px・透過 %.1f の強い線なら 3 場面とも %.2f〜%.2f で最大 = 尺度が固定。"
          % (REF_W, REF_T, min(o["strong"] for o in out.values()),
             max(o["strong"] for o in out.values())))
    print("  ★校正なしが壊れるのは**欠陥ゼロの側**: 偽クラック %.0f px(雑音が 1.0 に伸びる)。"
          "校正ありは %.0f px。" % (o0["false_raw"], o0["false_cal"]))
    print("  ★予想「深いクラックを 1 本足すと他の 5 本が消える」は%s: 校正なしの再現率 "
          "%.2f → %.2f(クラック応答は %.2f → %.2f に縮んだが、しきい値 %.2f の上に残った)。"
          "校正ありは %.2f → %.2f。"
          % ("外れた" if o2["rec_raw"] > 0.8 else "当たった", o1["rec_raw"], o2["rec_raw"],
             o1["med_raw"], o2["med_raw"], HYST_HIGH, o1["rec_cal"], o2["rec_cal"]))
    print("     つまり最大値正規化が危ないのは「強い欠陥がある画像」ではなく"
          "「何も無い画像」—— 良品ほど偽検出が出る検査器になる。")
    assert o1["weak"] < 0.9 and o1["strong"] > 0.99, (o1["weak"], o1["strong"])
    assert o0["false_raw"] > 10 * max(o0["false_cal"], 1.0), (o0["false_raw"], o0["false_cal"])
    sc2 = scenes[2][1]
    s2 = degrid(flatten(sc2["img"])[0])
    figs.save_grid("frangi_norm",
                   [ridge_map(s2, calibrate=False)[0], ridge_map(s2)[0],
                    analyze(sc2, calibrate=False)["sk"].astype(np.float64),
                    analyze(sc2)["sk"].astype(np.float64)],
                   ["校正なし: 深いクラックが 1.0、他は縮む", "校正あり: 強い校正線が 1.0",
                    "校正なしの骨格(再現率 %.2f)" % o2["rec_raw"],
                    "校正ありの骨格(再現率 %.2f)" % o2["rec_cal"]],
                   ncols=2, title="最大値で正規化する op は、いちばん強い欠陥が尺度を決める")
    return {"out": out}


# --------------------------------------------------------------------------- #
# 4. 崖: 結晶粒のコントラスト                                                   #
# --------------------------------------------------------------------------- #
def section_grain_sweep() -> dict:
    print("\n" + "=" * 78)
    print("4) 崖: 結晶粒のコントラスト c を上げると、どこで粒が欠陥に化けるか")
    print("=" * 78)
    sig = 1.0
    step_h = 1.0 / (sig ** 2 * np.sqrt(2 * np.pi * np.e))          # 段差 1 の 2 階微分の最大
    line_h = REF_W * (1 - REF_T) / (np.sqrt(2 * np.pi) * sig ** 3)  # 校正線の 2 階微分
    c_pred = HYST_HIGH * line_h / step_h
    print("  予測: 暗い粒が T_FI=%.2f を割るのは c > %.2f —— そこから粒が帯を飲み込んで"
          "断線の一致が落ちる。T_ISO=%.2f を割るのは c > %.2f。"
          % (T_FI, 1 - T_FI, T_ISO, 1 - T_ISO))
    print("        粒の段差(高さ c)がヒステリシス上限 %.2f に届くのは、σ=%.0f の"
          "ヘッセ行列の比 %.3f/%.3f から c ≈ %.2f。" % (HYST_HIGH, sig, step_h, line_h, c_pred))
    print("\n     c     偽クラック [px]  偽の断線  一致した断線  面積率誤差 [pt]  粒→孤立 [%]")
    cs, false_len, fi_false, fi_ok, iso_err = [], [], [], [], []
    for c in (0.0, 0.06, 0.12, 0.18, 0.24, 0.32, 0.40, 0.50, 0.60):
        sc = make_scene(grain_c=c)
        r = analyze(sc)
        cs.append(c)
        false_len.append(r["false_len"])
        fi_false.append(r["fi_false"])
        fi_ok.append(r["fi_matched"])
        iso_err.append(r["iso_err"])
        print("   %5.2f      %8.0f        %3d         %2d/%d        %+7.2f        %6.2f"
              % (c, r["false_len"], r["fi_false"], r["fi_matched"], len(FI_BANDS),
                 r["iso_err"], r["grain_as_iso"]))
    onset = next((c for c, f in zip(cs, false_len) if f > 30.0), None)
    fi_drop = next((c for c, n in zip(cs, fi_ok) if n < len(FI_BANDS)), None)
    print("\n  ★偽クラックが 30 px を超えるのは c=%s —— **予測 %.2f は %.0f 倍外れた**。"
          "粒の境界を「段差」と見た予測が間違いで、幅が σ 程度の暗い粒は段差ではなく"
          "**谷そのもの**(深さ ≈ 2c)になる。" % (onset, c_pred, c_pred / onset))
    print("  ★偽の断線は最大 %d 本だが**一致が %d/%d → %d/%d に落ちる**(落ちはじめ c=%s、"
          "予測 c>%.2f)—— 暗い粒が帯を飲み込み、「細長く水平」の形の門が塊ごと落とす。"
          % (max(fi_false), fi_ok[0], len(FI_BANDS), fi_ok[-1], len(FI_BANDS),
             fi_drop, 1 - T_FI))
    print("     面積率の誤差は c=%.2f でも %+.2f ポイント(T_ISO を割る粒は無い、予測どおり)。"
          % (cs[-1], iso_err[-1]))
    figs.save_plot("grain_contrast", [("偽クラック長 [px]", cs, false_len),
                                      ("一致した断線 [本] x 50", cs, [50 * v for v in fi_ok]),
                                      ("面積率誤差 [pt] x 100", cs, [100 * v for v in iso_err])],
                   xlabel="結晶粒のコントラスト c", ylabel="偽クラック長 [px] / 断線 x50 / 誤差 x100",
                   title="粒のコントラストを上げると、クラックは偽が出て断線は飲まれる",
                   caption="面積率は c=0.60 でも 3 ポイント以内。壊れ方は 3 種で別々。")
    return {"c": cs, "false_len": false_len, "fi_false": fi_false, "fi_ok": fi_ok,
            "iso_err": iso_err, "onset": onset, "c_pred": c_pred, "fi_drop": fi_drop}


# --------------------------------------------------------------------------- #
# 5. 崖: クラック幅                                                             #
# --------------------------------------------------------------------------- #
def section_width_sweep() -> dict:
    print("\n" + "=" * 78)
    print("5) 崖: クラック幅 0.5 → 3.0 px の再現率")
    print("=" * 78)
    unit = REF_W * (1 - REF_T)              # 校正線の「幅 × 深さ」
    w_pred = HYST_HIGH * unit / (1 - CRACK_T)
    print("  予測: Frangi の応答は「幅 × 深さ」に比例(σ より細い間)。校正線 %.0f px × %.1f = 1.0 "
          "なので、幅 w のクラック(深さ %.2f)は w×%.2f/%.1f。ヒステリシス上限 %.2f を"
          "割るのは幅 < %.2f px。" % (REF_W, 1 - REF_T, 1 - CRACK_T, 1 - CRACK_T, unit,
                                    HYST_HIGH, w_pred))
    print("\n    幅 [px]   応答(中心線の中央値)   線形予測   再現率(5 本平均)   最小   偽 [px]")
    ws, rec, mn, resp, pred = [], [], [], [], []
    for w in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0):
        sc = make_scene(crack_w=w)
        r = analyze(sc)
        rm, _ = ridge_map(degrid(flatten(sc["img"])[0]))
        any_true = np.zeros_like(rm, bool)
        for m in sc["crack_lines"]:
            any_true |= m
        ws.append(w)
        rec.append(float(np.mean(r["recall"])))
        mn.append(float(min(r["recall"])))
        resp.append(float(np.median(rm[any_true])))
        pred.append(min(w * (1 - CRACK_T) / unit, 1.0))
        print("    %4.2f          %.2f                %.2f          %.2f          %.2f    %.0f"
              % (w, resp[-1], pred[-1], rec[-1], mn[-1], r["false_len"]))
    cliff = next((w for w, v in zip(ws, rec) if v >= 0.5), None)
    ratio = [a / b for a, b in zip(resp, pred)]
    print("\n  ★再現率 0.5 を超えるのは幅 %.2f px から(予測 %.2f px)。実測の応答は線形予測の"
          " %.2f〜%.2f 倍 —— %s。" % (cliff, w_pred, min(ratio), max(ratio),
                                     "幅 × 深さの線形則で崖が読める" if abs(cliff - w_pred) <= 0.3
                                     else "線形則は崖の位置を外す"))
    print("     崖の位置は校正線の「幅 × 深さ」とヒステリシス上限の積で決まる —— "
          "検出したい最小幅から逆算して決めること。")
    figs.save_plot("crack_width", [("再現率(5 本平均)", ws, rec), ("再現率(最小)", ws, mn),
                                   ("中心線の応答(校正線=1)", ws, resp),
                                   ("線形予測 w×%.2f/%.1f" % (1 - CRACK_T, unit), ws, pred)],
                   xlabel="クラック幅 [px]", ylabel="再現率 / 応答",
                   title="クラック幅の崖は「幅 × 深さ」の線形則で読める")
    return {"w": ws, "recall": rec, "resp": resp, "cliff": cliff, "w_pred": w_pred,
            "ratio": ratio}


# --------------------------------------------------------------------------- #
# 6. 崖: ビネッティング                                                         #
# --------------------------------------------------------------------------- #
def section_vignette_sweep() -> dict:
    print("\n" + "=" * 78)
    print("6) 崖: ビネッティングの強さ 0 → 1.0 —— 隅の孤立領域は消えるか、増えるか")
    print("=" * 78)
    corner = 1.0 / (1.0 + (1.0 / (0.35 + 1.15 * VIG_B)) ** 2) ** 2
    a_iso = (1 - T_ISO) / (1 - corner)
    print("  予測(補正なし): 隅の透過は 1-a+a·%.3f。T_ISO=%.2f を割るのは a > %.2f。"
          % (corner, T_ISO, a_iso))
    # 行列プロファイル(分離可能近似)だけで割った場合の隅・辺の残差を幾何で予測
    v = vignette_model((N, N), 1.0, 0.35 + 1.15 * VIG_B)
    p = np.median(v, axis=1)
    q = np.median(v / (p / np.median(p))[:, None], axis=0)
    resid = v / (p / np.median(p))[:, None] / (q / np.median(q))[None, :]
    resid /= np.median(resid)
    print("  予測(プロファイルだけ): a=1 で隅の残差 %.2f、辺の中央 %.2f、中心 %.2f "
          "—— 分離可能近似は隅を明るく戻し、辺の中央を暗く残す。"
          % (resid[0, 0], resid[N // 2, 0], resid[N // 2, N // 2]))
    seeds = (7, 3, 11, 23)
    print("\n    強さ a   当てはめ a(%d 種の平均±散らばり)  面積率誤差 [pt]: 当てはめ込み / "
          "プロファイルだけ   断線: 込み / だけ   ゼロ点暗画素率 [%%]" % len(seeds))
    as_, e_fit, e_grid, zero, ahat, asd, fi_fit, fi_grid = [], [], [], [], [], [], [], []
    for a in (0.0, 0.25, 0.5, 0.75, 1.0):
        ah, ef, eg, ff, fg, zp = [], [], [], [], [], []
        for sd in seeds:
            sc = make_scene(vig_a=a, seed=sd)
            r1 = analyze(sc, use_fit=True)
            r2 = analyze(sc, use_fit=False)
            ah.append(r1["fit"][0])
            ef.append(r1["iso_err"])
            eg.append(r2["iso_err"])
            ff.append(r1["fi_matched"])
            fg.append(r2["fi_matched"])
            zp.append(100.0 * float((np.asarray(fs.apply(sc["img"], "otsu")) < 0.5).mean()))
        as_.append(a)
        ahat.append(float(np.mean(ah)))
        asd.append(float(np.std(ah)))
        e_fit.append(float(np.mean(ef)))
        e_grid.append(float(np.mean(eg)))
        fi_fit.append(float(np.mean(ff)))
        fi_grid.append(float(np.mean(fg)))
        zero.append(float(np.mean(zp)))
        print("    %4.2f        %.2f ± %.2f                    %+6.2f            %+6.2f"
              "            %.1f / %.1f         %5.1f"
              % (a, ahat[-1], asd[-1], e_fit[-1], e_grid[-1], fi_fit[-1], fi_grid[-1],
                 zero[-1]))
    print("\n  ★当てはめ込みは %+.2f〜%+.2f ポイントで動かない。プロファイルだけでも "
          "a=1.0 で %+.2f ポイント —— 「a>%.2f で隅が偽の孤立領域になる」は補正を何も"
          "しない場合の話で、格子除去の行列プロファイルが cos^4 の分離可能な部分を"
          "先に吸ってしまう。" % (min(e_fit), max(e_fit), e_grid[-1], a_iso))
    print("     幾何の予測どおり、残るのは隅(%.2f 倍に戻る)でなく辺の中央(%.2f)で、"
          "T_ISO=%.2f までは遠い。cos^4 の当てはめは**この場面では要らなかった**。"
          % (resid[0, 0], resid[N // 2, 0], T_ISO))
    print("  ★当てはめの強さは種で %.2f まで散る(粒の抽選がリングの明るさを決める)"
          "が、面積率と断線はその誤差に鈍い。" % max(asd))
    figs.save_plot("vignette", [("cos^4 当てはめ込み", as_, e_fit),
                                ("行列プロファイルだけ", as_, e_grid)],
                   xlabel="ビネッティングの強さ a", ylabel="不活性面積率の誤差 [pt]",
                   title="隅の孤立領域はビネッティングに食われない")
    return {"a": as_, "e_fit": e_fit, "e_grid": e_grid, "zero": zero, "ahat": ahat,
            "asd": asd, "a_iso": a_iso, "resid_corner": float(resid[0, 0]),
            "resid_edge": float(resid[N // 2, 0])}


# --------------------------------------------------------------------------- #
# 7. 崖: SNR                                                                    #
# --------------------------------------------------------------------------- #
def section_snr_sweep() -> dict:
    print("\n" + "=" * 78)
    print("7) 崖: 光子数 K を下げると断線が見えなくなる点")
    print("=" * 78)
    margin = T_FI - FI_T
    k_pred = (0.282 / (margin / 2)) ** 2 / (FI_T * EXPOSURE)
    print("  予測: 帯の明るさ %.2f と T_FI=%.2f の余裕 %.2f。σ=1 平滑後の雑音 "
          "0.282/√(%.2f·K) がその半分になる K ≈ %.0f で帯が割れはじめる。"
          % (FI_T, T_FI, margin, FI_T * EXPOSURE, k_pred))
    print("\n     K      断線 一致/偽    クラック再現率(平均)   面積率誤差 [pt]   偽クラック [px]")
    ks, fi_ok, rec, err, fl = [], [], [], [], []
    for k in (2000, 500, 200, 50, 20, 8):
        sc = make_scene(photons=k)
        r = analyze(sc)
        ks.append(k)
        fi_ok.append(r["fi_matched"])
        rec.append(float(np.mean(r["recall"])))
        err.append(r["iso_err"])
        fl.append(r["false_len"])
        print("   %5d       %d/%d  %2d         %.2f               %+6.2f          %6.0f"
              % (k, r["fi_matched"], len(FI_BANDS), r["fi_false"], rec[-1], r["iso_err"],
                 r["false_len"]))
    k_fail = next((k for k, n in zip(ks, fi_ok) if n < len(FI_BANDS)), None)
    print("\n  ★断線が 8/8 を割るのは K=%s(予測 K≈%.0f —— 予測は %.0f 倍楽観的)。帯は"
          "「割れる」より先に**画素ごとの誤分類で形の門(高さ ≤ 9 px)から外れる**。"
          % (k_fail, k_pred, k_fail / k_pred))
    print("     クラック再現率は K=%d で %.2f、偽クラックは K=%d で %.0f px —— 雑音の崖では"
          "偽が先に増え、見逃しは後から来る。" % (ks[-1], rec[-1], ks[-2], fl[-2]))
    figs.save_plot("snr", [("断線 一致 [本]", ks, fi_ok),
                           ("クラック再現率 x 8", ks, [8 * v for v in rec])],
                   xlabel="光子数 K(明るさ 1.0 あたり)", ylabel="検出",
                   title="雑音で先に消えるのは断線(帯の余裕 %.2f)" % margin)
    return {"k": ks, "fi_ok": fi_ok, "recall": rec, "k_fail": k_fail, "k_pred": k_pred}


# --------------------------------------------------------------------------- #
# 8. 対照群                                                                     #
# --------------------------------------------------------------------------- #
def section_controls(default: dict) -> dict:
    print("\n" + "=" * 78)
    print("8) 対照群 —— むらなし / ビネッティングなし")
    print("=" * 78)
    print("   条件                 面積率誤差 [pt]  偽クラック [px]  再現率(最小)  断線")
    out = {}
    rows = [("既定", default)]
    for name, kw in (("結晶粒むらなし", {"grain_c": 0.0}), ("ビネッティングなし", {"vig_a": 0.0}),
                     ("両方なし", {"grain_c": 0.0, "vig_a": 0.0})):
        rows.append((name, analyze(make_scene(**kw))))
    for name, r in rows:
        out[name] = r
        print("   %-18s     %+6.2f           %6.0f          %.2f       %d/%d"
              % (name, r["iso_err"], r["false_len"], min(r["recall"]),
                 r["fi_matched"], len(FI_BANDS)))
    print("  既定条件の残差は、どちらの要因を止めても同じ桁 —— 残っているのは"
          "ぼけと雑音の分。")
    return out


# --------------------------------------------------------------------------- #
# 9. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("9) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)

    # (a) aug_vignette の式は文書どおり(当てはめの前向きモデルに使ってよい)
    v_op = np.asarray(fs.apply(np.ones((N, N)), "aug_vignette", a=1.0, b=0.5))
    v_eq = vignette_model((N, N), 1.0, 0.35 + 1.15 * 0.5)
    dmax = float(np.abs(v_op - v_eq).max())
    assert dmax < 1e-6, dmax
    print("  (a) aug_vignette の cos^4 則は文書の式と %.1e で一致 —— 撮像を壊す op を"
          "そのまま補正の前向きモデルに使えた。ただし**当てはめる口は無い**"
          "(半径ビン中央値の格子探索は自前)。" % dmax)

    # (b) 大きなスケールの背景推定が無い(σ 最大 3.0、ローリングボール半径 25)
    print("  (b) 大窓の背景推定が無い: gaussian は σ 3.0 まで、sk_rolling_ball は"
          "半径 25 px まで、f2_gauss_pyramid は 1/16 まで。セル 1 枚(数百 px)の"
          "ビネッティングは届かない。")

    # (c) 周期格子(行の関数 x 列の関数)を割る口が無い
    print("  (c) 「行の関数 × 列の関数」で割る(分離可能な格子の除去)口が無い。"
          "中央値プロファイルの割り算は自前 4 行。")

    # (d) sk_frangi の正規化(3 節)
    print("  (d) sk_frangi / sk_meijering / sk_hessian は _norm で画像ごとの最大値に"
          "正規化する。絶対しきい値が要る検査では校正線を貼るしかない(3 節)。")

    # (e) lines_gauss の輪郭は画素集合(順序なし)で、total_length が過大
    im = np.full((120, 120), 0.9)
    yy, xx = np.mgrid[0:120, 0:120]
    d = np.abs((yy - 20) - (xx - 20)) / np.sqrt(2)
    im[(d < 0.75) & (xx >= 20) & (xx <= 100)] = 0.3
    xld = fs.apply(im, "lines_gauss", a=0.5)
    tl = float(fs.apply(xld, "total_length"))
    true_len = 80.0 * np.sqrt(2.0)
    print("  (e) lines_gauss は連結成分の画素を**ラスタ順**に並べた「輪郭」を返すので、"
          "total_length が %.0f px(真値 %.0f px の %.1f 倍)。骨格の折れ線長は自前。"
          % (tl, true_len, tl / true_len))
    assert tl > 1.5 * true_len, tl

    # (f) hysteresis_threshold のしきい値範囲が固定(下 0.2〜0.5、上 0.5〜0.8)
    print("  (f) hysteresis_threshold のしきい値は下 0.2〜0.5 / 上 0.5〜0.8 に固定で、"
          "校正線 = 1.0 の尺度では上限 %.2f が指定できない。応答にゲイン %.2f を掛けて"
          "範囲に入れている。" % (HYST_HIGH, 0.5 / HYST_HIGH))


# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# 9. 実データ —— SIPV-EL(実セルの EL 像 + I-V で測った出力)                    #
# --------------------------------------------------------------------------- #
#: 実データの置き場の環境変数(``<root>/sipv_el/`` を見る)。
REAL_DATA_ENV = "FULLSEYE_POC_REAL_DATA"
#: SIPV-EL(Mateo-Romero, Hernández-Callejo, Alonso-Gómez, Morales、Zenodo 14439369、CC BY 4.0)。
#: 書庫と CSV の SHA-256(2026-11-08 に取得、``tools/fetch_realinsp_data.py`` の台帳と同じ値)。
#: 書庫が置き場に在れば読む前に照合する(取得器を通さずに置かれた書庫も黙って使わない)。
SIPV_ZIP_SHA256 = "3fca8d9a3eb748f55f742b5e3651e9caa4da004c0c86e756d5afb24ad1a3a216"
SIPV_ZIP_BYTES = 484_606_354
SIPV_CSV_SHA256 = "31497f080963b4a972858be5e53ef6d9e3a721ddef40442245d949b596891e9b"
SIPV_CREDIT = ("SIPV-EL: H. F. Mateo Romero, L. Hernández Callejo, V. Alonso Gómez, J. I. Morales, "
               "Zenodo doi:10.5281/zenodo.14439369, CC BY 4.0")
#: 撮影条件の一次情報(配布元の著者の論文、Zenodo 11285233 に全文): 「The shadowing in the cells was
#: performed using cardboard masks with a layer of aluminum. The zones covered by the mask do not contribute
#: to the production of current since the aluminum foil is capable of blocking photons. [...] These masks have
#: been placed on the surface of the cell.」、Fig. 2 の分類は 0 = Original Image、1 = Long Horizontal Line、
#: 2 = Long Vertical Line、3 = Big Central Circle、4 = Small Central Circle、5 = Two small circles in the
#: corners、6 = Big circle in one corner、7 = Other defects(Mateo Romero et al., Solar Energy 265 (2023)
#: 112089, doi:10.1016/j.solener.2023.112089)。★したがって S1〜S6 の暗部は**セルの表面に置いた
#: 遮光マスク**で、電気的な不活性領域ではない。★ファイル名の S 番号と論文の番号の対応は配布元に
#: 書かれていない。画像で確かめると S3〜S6 の形は論文と一致するが、S1 / S2 は「上の帯」と「左の帯」が
#: セルによって入れ替わる(電流 6 の 69 枚で S1 = 上 18・左 17、S2 = 左 18・上 16、2026-11-08 に実測)。
#: S7 を「その他の欠陥」と読むのは番号の対応からの推定で、種類の内訳も配布元に無い。
SIPV_PAPER = ("Mateo Romero et al., Solar Energy 265 (2023) 112089, "
              "doi:10.1016/j.solener.2023.112089(Zenodo 11285233)")
SIPV_MASKS = {0: "マスクなし", 1: "縁の帯", 2: "縁の帯", 3: "中央の大円", 4: "中央の小円",
              5: "隅の小円 2 つ", 6: "隅の大円", 7: "その他の欠陥(推定)"}
#: 1 セルにつき使う注入電流(ファイル名の C の値)。無いセルは中央の電流で代える(決定的)。
REAL_CURRENT = "6"
#: 狭い成分だけ割るときの、行・列プロファイルのメディアン窓 [px]。バスバー(幅 ≈ 5 px)より
#: 十分広く、影(直径 100 px 級)より十分狭い。★この値は実データを見てから決めた(事後の選択)。
NARROW_WIN = 15
#: 代表の図の上段に使う 1 枚(セル番号, 電流, マスクの番号)。下段は S7 の出力低下の中央値に
#: いちばん近いセルを実行時に選ぶ(都合の良いセルを手で選ばない)。
REP_SHADOW = (20, "6", 3)

#: 実データで出た数値(2026-11-08、上の SHA-256 の書庫から。実行の stdout から転記)。
#: データが無い環境(CI)ではこれを印字し、鍵と中身と docstring の見出しの数値を照合する。
#: データがある環境では実測をこれと同じ丸め(小数 3 桁)で照合する(ずれたら鳴る)。
RECORDED_REAL = {
    # ★2026-11-09: otsu が実データの範囲で 256 ビンを張るようになり、ゼロ点の列が 3 桁目で動いた
    #   (ρ 0.44 → 0.438、平均差 0.073 → 0.074、S3/S4/S7 の Δ +0.001〜0.002)。文中の 2 桁の値は変わらない。
    "cells": 32, "shadow_images": 195,
    "rho": {"zero": 0.438, "median": 0.041, "narrow": 0.638},
    "mean_abs_gap_vs_loss": {"zero": 0.074, "median": 0.154, "narrow": 0.051},
    "s0_area_median": {"zero": 0.089, "median": 0.014, "narrow": 0.022},
    # マスクごとの中央値: (出力低下, ゼロ点 Δ, 中央値で割る Δ, 細い成分だけ Δ)
    "by_shadow": {"S1": (0.211, 0.184, -0.008, 0.218), "S2": (0.227, 0.188, -0.006, 0.216),
                  "S3": (0.287, 0.246, 0.103, 0.279), "S4": (0.122, 0.094, 0.112, 0.113),
                  "S5": (0.221, 0.181, 0.205, 0.206), "S6": (0.275, 0.219, 0.099, 0.254),
                  "S7": (0.089, 0.499, 0.002, 0.013)},
    "s7_brightness": (0.752, 0.895), "s7_col_ratio": (0.134, 1.776),
    "s7_rep": {"cell": 2, "loss": 0.089, "d_zero": 0.499, "d_narrow": 0.011},
}
#: RECORDED_REAL に必ず要る鍵(CI 経路の門が見る)。
REAL_KEYS = ("cells", "shadow_images", "rho", "mean_abs_gap_vs_loss", "s0_area_median",
             "by_shadow", "s7_brightness", "s7_col_ratio", "s7_rep")


def real_data_root() -> Path:
    """SIPV-EL の置き場(``<root>/sipv_el``)。手元の絶対パスはソースに書かない。"""
    import os

    configured = os.environ.get(REAL_DATA_ENV, "").strip()
    if configured:
        return Path(configured).expanduser() / "sipv_el"
    here = Path(__file__).resolve().parents[1]
    if here.parent.name.lower() == "projects":
        return here.parent.parent / "data" / "fullseye_poc_real" / "sipv_el"
    return Path.home() / ".cache" / "fullseye" / "poc_real" / "sipv_el"


def _sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def degrid_narrow(flat: np.ndarray, win: int = NARROW_WIN) -> np.ndarray:
    """格子(バスバー・フィンガー)の**細い**成分だけを行・列プロファイルで割る。

    :func:`degrid` は中央値プロファイルそのもので割る。合成の場面では十分だったが、
    実セルの**帯状の暗部**(片側の縁を全高で覆うマスク)は列の中央値ごと暗いので、列で割った
    瞬間に暗部が消える(合成でも「右端を帯にしたら列プロファイルが帯ごと割って消した」と
    書いた形)。そこでプロファイルを ``win`` px のメディアンで平らにした基準で割り、
    窓より細い凹み(= バスバー)だけを落とす。比は [0.05, 1.5] に切る(真っ暗な列で
    0/0 にしない)。
    """
    def ratio(v):
        ref = median_filter(v, size=win, mode="nearest")
        return np.clip(v / np.maximum(ref, 1e-3), 0.05, 1.5)

    p = np.median(flat, axis=1)
    s1 = flat / ratio(p)[:, None]
    q = np.median(s1, axis=0)
    s = s1 / ratio(q)[None, :]
    return s / max(float(np.quantile(s, 0.75)), 1e-6)


def _cell_rect(img0: np.ndarray) -> tuple[int, int, int, int]:
    """マスクの無い像(S0)からセルの外枠(行・列の範囲)を出す。枠外の黒は数えない。"""
    bright = img0 > 0.3 * float(np.quantile(img0, 0.95))
    rr = np.nonzero(bright.mean(axis=1) > 0.3)[0]
    cc = np.nonzero(bright.mean(axis=0) > 0.3)[0]
    if rr.size < 50 or cc.size < 50:
        raise ValueError("セルの外枠が取れない(明るい行 %d / 列 %d)" % (rr.size, cc.size))
    return int(rr[0]) + 2, int(rr[-1]) - 1, int(cc[0]) + 2, int(cc[-1]) - 1


def _real_masks(img: np.ndarray, rect) -> dict:
    """1 枚から 3 通りの「暗部」マスク(セル外枠の中)を返す。

    合成の章の :func:`classify` は孤立領域(``iso``)を「不活性」と呼ぶが、実データの暗部は
    遮光マスクなので、ここでは**暗部の面積**として数えるだけにする。
    """
    r0, r1, c0, c1 = rect
    dark = ~(np.asarray(fs.apply(img, "otsu")) > 0.5)
    crop = img[r0:r1, c0:c1]
    return {"zero": dark[r0:r1, c0:c1],
            "median": classify(degrid(crop))["iso"],
            "narrow": classify(degrid_narrow(crop))["iso"]}


def _load_real(root: Path):
    """CSV(; 区切り・小数はカンマ)と画像の対応表を作る。1 セル 1 電流・マスク S0〜S7。

    書庫(``raw/all_cells.zip``)が在ればバイト数と SHA-256 を、CSV は SHA-256 を照合してから読む。
    """
    import csv
    import re

    from PIL import Image

    zp = root / "raw" / "all_cells.zip"
    if zp.is_file():
        if zp.stat().st_size != SIPV_ZIP_BYTES or _sha256(zp) != SIPV_ZIP_SHA256:
            raise ValueError("SIPV-EL の書庫が台帳と違う(バイト数か SHA-256): %s" % zp)
    else:
        print("  (書庫 raw/all_cells.zip が無いので展開物だけを読む。照合は CSV の SHA-256 と画像の型)")
    cp = root / "raw" / "features_labels_poli_y_mono_IV.csv"
    if _sha256(cp) != SIPV_CSV_SHA256:
        raise ValueError("SIPV-EL の CSV の SHA-256 が台帳と違う: %s" % cp)
    rows = list(csv.DictReader(open(cp, encoding="utf-8"), delimiter=";"))
    if len(rows) < 1000:
        raise ValueError("SIPV-EL の CSV が %d 行しか無い" % len(rows))
    by = {}
    for r in rows:
        m = re.fullmatch(r"P(\d+)C([\d.]+)S(\d+)\.tiff", r["filename"])
        if m is None:
            raise ValueError("想定外のファイル名: %r" % r["filename"])
        by[(int(m.group(1)), m.group(2), int(m.group(3)))] = r

    def img(key):
        p, c, s = key
        a = np.asarray(Image.open(root / "extracted" / ("P%dC%sS%d.tiff" % (p, c, s))))
        if a.dtype != np.uint16 or a.shape != (400, 400):
            raise ValueError("想定外の画像 %s: %s %s" % (key, a.dtype, a.shape))
        return a.astype(np.float64) / 65535.0

    return by, img


def _r3(v):
    """記録と照合の丸め(小数 3 桁)。入れ子の辞書・組も同じ形で丸める。"""
    if isinstance(v, dict):
        return {k: _r3(x) for k, x in v.items()}
    if isinstance(v, (tuple, list)):
        return tuple(_r3(x) for x in v)
    if isinstance(v, (int, np.integer)) and not isinstance(v, bool):
        return int(v)
    return round(float(v), 3)


def _flat_numbers(v):
    if isinstance(v, dict):
        for x in v.values():
            yield from _flat_numbers(x)
    elif isinstance(v, (tuple, list)):
        for x in v:
            yield from _flat_numbers(x)
    elif isinstance(v, (int, float)) and not isinstance(v, bool):
        yield float(v)


def _squash(text: str) -> str:
    """空白・改行・強調の ``*`` を落とす(docstring の折り返しに左右されずに照合するため)。"""
    return "".join(text.split()).replace("*", "")


def check_doc_synthetic(zp: dict, sc: dict, pipe: dict, fr: dict, gr: dict, wd: dict, sn: dict) -> None:
    """合成部の門: docstring(展示の見出しの正本)の数値が、**文脈つきの文字列**で実行の印字と一致すること。

    2026-11-08 の再レビューで、docstring 1 番とキャプションが 21.7 % / 42 % / 33 % / 20 % のまま、
    実行は 22.7 % / 41 % / 35 % / 19 % だった(master からの持ち越し。合成部に照合の門が無かった)。
    ★2026-11-09: otsu が [0,1] に収まる像も実データの範囲で 256 ビンを張るようになり、20.8 % / 43 % / 31 % / 21 %
    (4.4 倍)に動いた。この門が実行との食い違いを見つけ、docstring とキャプションを転記し直した。
    短い数字の部分一致では別の文脈の数でも通るので、前後の語ごと照合する。
    """
    dark = zp["dark_n"]
    o0 = next(iter(fr["out"].values()))           # 欠陥ゼロの場面
    want = [
        "ゼロ点(大域しきい値Otsuの暗画素率)は%.1f%%で、真値%.2f%%の%.1f倍"
        % (zp["rate"], sc["iso_rate"], zp["rate"] / sc["iso_rate"]),
        "暗画素の%.0f%%はフィンガー/バスバー" % (100.0 * zp["parts"]["フィンガー/バスバー"] / dark),
        "%.0f%%はビネッティングと結晶粒" % (100.0 * zp["parts"]["結晶粒/ビネッティング"] / dark),
        "本当の不活性領域は暗画素の%.0f%%しか" % (100.0 * zp["parts"]["孤立領域(本物)"] / dark),
        "推定%.2f%%(誤差%+.2fポイント)" % (pipe["iso_rate"], pipe["iso_err"]),
        "クラック5本の再現率%.2f〜%.2f" % (min(pipe["recall"]), max(pipe["recall"])),
        "偽クラック%.0fpx(校正ありは%.0fpx)" % (o0["false_raw"], o0["false_cal"]),
        "偽クラックはc=%sから" % gr["onset"],
        "再現率0.5を超えるのは%.2fpxから" % wd["cliff"],
        "K=%sで7/8" % sn["k_fail"],
    ]
    doc = _squash(__doc__ or "")
    absent = [w for w in want if _squash(w) not in doc]
    assert not absent, "docstring の合成部の数値が実行と違う(印字から転記し直す): %s" % absent


def check_recorded_real(rec: dict) -> None:
    """CI 経路の門: 記録値の鍵がそろい、中身が有限の数で、見出しの数値が docstring と同じであること。

    以前の ``assert RECORDED_REAL`` は定数の辞書が空でないかを見るだけで常に真だった
    (2026-11-08 の敵対的レビュー)。ここでは docstring(展示の見出しの正本)に書いた順位相関・
    S7 の数値が、記録値を同じ書式に丸めた文字列として載っていることまで見る。
    """
    missing = [k for k in REAL_KEYS if k not in rec]
    assert not missing, "RECORDED_REAL に鍵が無い: %s" % missing
    nums = list(_flat_numbers(rec))
    assert nums and all(np.isfinite(nums)), "RECORDED_REAL に有限でない数がある"
    assert rec["cells"] >= 30 and rec["shadow_images"] >= 150, rec
    doc = __doc__ or ""
    heads = ["ρ %.2f" % rec["rho"]["zero"], "ρ %.2f" % rec["rho"]["narrow"],
             "ρ %.2f" % rec["rho"]["median"],
             "%.1f %%" % (100 * rec["by_shadow"]["S7"][0]),
             "%+.0f pt" % (100 * rec["by_shadow"]["S7"][1]),
             "%.2f〜%.2f 倍" % tuple(rec["s7_brightness"])]
    absent = [h for h in heads if h not in doc]
    assert not absent, "docstring の見出しに記録値が載っていない: %s" % absent


def section_real_el() -> dict | None:
    """実セルで「暗い面積」と格子除去の経路を、**I-V の出力**で採点する。"""
    import os

    print("\n" + "=" * 78)
    print("9) 実データ —— SIPV-EL の実セル EL 像の暗部を、I-V で測った出力の低下で採点する")
    print("=" * 78)
    root = real_data_root()
    have = (root / "extracted").is_dir() and (root / "raw" / "features_labels_poli_y_mono_IV.csv").is_file()
    if (os.environ.get("CI") and not os.environ.get(REAL_DATA_ENV)) or not have:
        print("  実データが無いので実データの章を飛ばす。取得は py -3.11 tools/fetch_realinsp_data.py sipv_el")
        print("  記録値(RECORDED_REAL): %s" % RECORDED_REAL)
        check_recorded_real(RECORDED_REAL)
        print("  記録値の門: 鍵 %d 個・有限・docstring の見出しと一致" % len(REAL_KEYS))
        return None
    from scipy.stats import spearmanr

    by, load = _load_real(root)
    realdata.mark_read("zenodo:14439369/SIPV-EL")
    print("  " + SIPV_CREDIT)
    print("  撮影条件(配布元の論文 %s):" % SIPV_PAPER)
    print("    暗部 S1〜S6 は**セルの表面に置いたアルミ箔つきの厚紙のマスク**(遮光)。マスクの下は電流を作らない。")
    print("    S7 は論文の分類の 7「その他の欠陥」と読む(番号の対応は推定: S1 / S2 は上の帯と左の帯が")
    print("    セルによって入れ替わるので、ファイル名の番号が論文の番号と一致する保証は無い。内訳も無い)。")
    print("  ★したがってここで測るのは**暗部の面積が I-V の出力低下を追うか**で、合成の章の「不活性面積」")
    print("    (電気的に孤立した領域)の検証ではない。")
    print("  真値は画像の外にある: 同じセル・同じ注入電流で、マスクの無い S0 に対する I-V 出力の低下 1 - P/P0。")

    def num(s):
        return float(s.replace(",", "."))

    recs = []
    cache = {}
    for p in sorted({k[0] for k in by}):
        cur = REAL_CURRENT
        if (p, cur, 0) not in by:
            cands = sorted({k[1] for k in by if k[0] == p and k[2] == 0}, key=float)
            if not cands:
                continue
            cur = cands[len(cands) // 2]
        img0 = load((p, cur, 0))
        rect = _cell_rect(img0)
        r0, r1, c0, c1 = rect
        m0 = _real_masks(img0, rect)
        p0 = num(by[(p, cur, 0)]["power"])
        for s in range(8):
            key = (p, cur, s)
            if key not in by:
                continue
            im = img0 if s == 0 else load(key)
            m = m0 if s == 0 else _real_masks(im, rect)
            col = (np.median(im[r0:r1, c0:c1], axis=0)
                   / np.maximum(np.median(img0[r0:r1, c0:c1], axis=0), 1e-6))
            rec = {"key": key, "kind": by[key]["pv_kind"], "loss": 1.0 - num(by[key]["power"]) / p0,
                   "bright": float(im[r0:r1, c0:c1].mean() / max(img0[r0:r1, c0:c1].mean(), 1e-9)),
                   "col": (float(np.percentile(col, 5)), float(np.percentile(col, 95)))}
            for name in ("zero", "median", "narrow"):
                rec[name] = float(m[name].mean())
                rec["d_" + name] = rec[name] - float(m0[name].mean())
            recs.append(rec)
            cache[key] = (im, rect, m, m0, rec)
    n_cells = len({r["key"][0] for r in recs})
    sh = [r for r in recs if r["key"][2] > 0]
    print("\n  セル %d 枚(多結晶 %d / 単結晶 %d)・マスクつき %d 枚 + マスクなし %d 枚。"
          % (n_cells, len({r["key"][0] for r in recs if r["kind"] == "Poli"}),
             len({r["key"][0] for r in recs if r["kind"] == "Mono"}), len(sh), len(recs) - len(sh)))

    names = {"zero": "ゼロ点(Otsu の暗画素)", "median": "格子除去(中央値プロファイル)",
             "narrow": "格子除去(細い成分だけ)"}
    loss = np.array([r["loss"] for r in sh])
    out = {"n_cells": n_cells, "n_shadow": len(sh)}
    print("\n   方法                         順位相関 ρ   |Δ暗部 − 出力低下| の平均   マスクなしの暗部率(中央値)")
    for k, label in names.items():
        d = np.array([r["d_" + k] for r in sh])
        rho = float(spearmanr(d, loss).correlation)
        mae = float(np.mean(np.abs(d - loss)))
        lvl = float(np.median([r[k] for r in recs if r["key"][2] == 0]))
        out[k] = {"rho": rho, "mae": mae, "s0": lvl}
        print("   %-28s %+.3f        %.3f                    %5.1f %%" % (label, rho, mae, 100 * lvl))

    print("\n   マスク        枚数   出力低下   ゼロ点 Δ   中央値プロファイル Δ   細い成分だけ Δ   (いずれも中央値)")
    table = []
    by_shadow = {}
    for s in range(1, 8):
        g = [r for r in sh if r["key"][2] == s]
        if not g:
            continue
        row = {k: float(np.median([r[k] for r in g])) for k in ("loss", "d_zero", "d_median", "d_narrow")}
        by_shadow[s] = row
        print("   S%d %-10s %3d    %5.1f %%    %+6.1f %%      %+6.1f %%             %+6.1f %%"
              % (s, SIPV_MASKS[s], len(g), 100 * row["loss"], 100 * row["d_zero"], 100 * row["d_median"],
                 100 * row["d_narrow"]))
        table.append(["S%d %s" % (s, SIPV_MASKS[s]), "%d" % len(g), "%.1f" % (100 * row["loss"]),
                      "%+.1f" % (100 * row["d_zero"]), "%+.1f" % (100 * row["d_median"]),
                      "%+.1f" % (100 * row["d_narrow"])])
    out["by_shadow"] = by_shadow
    plate = [s for s in by_shadow if s <= 6]
    out["narrow_plate_err"] = float(np.max([abs(by_shadow[s]["d_narrow"] - by_shadow[s]["loss"])
                                            for s in plate]))
    out["median_strip"] = float(np.max([abs(by_shadow[s]["d_median"]) for s in (1, 2) if s in by_shadow]))

    odd = _odd_rows(sh)
    if odd:
        print("  ★CSV の出力をそのまま使った外れ(|出力低下| > 50 %%、除かない): %s" % _odd_text(odd))
    s7 = [r for r in sh if r["key"][2] == 7]
    s7_med = float(np.median([r["loss"] for r in s7]))
    rep7 = min(s7, key=lambda r: (abs(r["loss"] - s7_med), r["key"]))
    br = np.array([r["bright"] for r in s7])
    out["s7_brightness"] = (float(br.min()), float(br.max()))
    out["s7_col_ratio"] = (float(min(r["col"][0] for r in s7)), float(max(r["col"][1] for r in s7)))
    out["s7_rep"] = {"cell": rep7["key"][0], "loss": rep7["loss"], "d_zero": rep7["d_zero"],
                     "d_narrow": rep7["d_narrow"]}

    z, md, nw = out["zero"], out["median"], out["narrow"]
    print("\n  ★外の真値(I-V)で見ると、出力の低下をいちばん素直に追うのは「格子の細い成分だけを割る」経路"
          "(ρ %+.2f、平均のずれ %.1f ポイント)。" % (nw["rho"], 100 * nw["mae"]))
    gap = [100 * (by_shadow[s]["d_zero"] - by_shadow[s]["loss"]) for s in plate]
    print("  ★マスク(S1〜S6)では、ゼロ点も出力低下との差 %+.1f〜%+.1f ポイントで追う —— マスクは真っ黒で、"
          "暗いものを数えれば当たる。" % (min(gap), max(gap)))
    print("  ★★分かれるのは S7(「その他の欠陥」と推定、%d 枚)。セル全体の EL が S0 の %.2f〜%.2f 倍に"
          % (len(s7), round(float(br.min()), 3), round(float(br.max()), 3)))   # 記録値と同じ丸めを経て書く
    print("     暗くなる(列ごとの明るさの比は 5〜95 %% 分位で %.2f〜%.2f と列でまちまち —— 一様な減光ではない)。"
          % out["s7_col_ratio"])
    print("     I-V の出力低下は中央値 %.1f %%。ゼロ点はこの暗さを暗部 %+.0f ポイントに数える —— "
          "**S1〜S6 の遮光マスクでは暗部の面積が出力低下を追うが、S7 では追わない**(S7 は %d 枚、正体は推定)。"
          % (100 * by_shadow[7]["loss"], 100 * by_shadow[7]["d_zero"], len(s7)))
    print("     ★ただし細い成分だけ割る経路も S7 では %+.1f ポイントで、出力低下を %.1f ポイント過小に言う"
          "(全体が暗くなる欠陥は面積では測れない)。"
          % (100 * by_shadow[7]["d_narrow"], 100 * (by_shadow[7]["loss"] - by_shadow[7]["d_narrow"])))
    print("  ★★合成で使った格子除去(中央値プロファイルで割る)は、実セルでは**縁の帯状のマスクを丸ごと消す**"
          "(S1・S2 で Δ %+.1f / %+.1f ポイント、出力は %.0f / %.0f %% 落ちている)。合成の 4.61 %%(誤差 -0.15)"
          "は、暗部が行・列を丸ごと覆わない形に限った結果だった。"
          % (100 * by_shadow[1]["d_median"], 100 * by_shadow[2]["d_median"],
             100 * by_shadow[1]["loss"], 100 * by_shadow[2]["loss"]))
    print("     プロファイルを %d px のメディアンで平らにしてから割る(バスバーだけ落とす)と、"
          "マスク 6 種の中央値で出力低下とのずれは最大 %.1f ポイント(窓 %d px は実データを見て決めた)。"
          % (NARROW_WIN, 100 * out["narrow_plate_err"], NARROW_WIN))
    print("  代表の図の下段は S7 の出力低下の中央値に最も近いセル P%d(出力低下 %.1f %%、ゼロ点 %+.0f pt、"
          "細い成分だけ %+.0f pt)。" % (rep7["key"][0], 100 * rep7["loss"], 100 * rep7["d_zero"],
                                      100 * rep7["d_narrow"]))
    print("  マスクなし(S0)の暗部率の中央値: ゼロ点 %.1f %% / 細い成分だけ %.1f %%(セルの面取りの隅・元からの割れを含む)。"
          % (100 * z["s0"], 100 * nw["s0"]))

    rec = _r3({"cells": n_cells, "shadow_images": len(sh),
               "rho": {k: out[k]["rho"] for k in names}, "mean_abs_gap_vs_loss": {k: out[k]["mae"] for k in names},
               "s0_area_median": {k: out[k]["s0"] for k in names},
               "by_shadow": {"S%d" % s: (v["loss"], v["d_zero"], v["d_median"], v["d_narrow"])
                             for s, v in by_shadow.items()},
               "s7_brightness": out["s7_brightness"], "s7_col_ratio": out["s7_col_ratio"],
               "s7_rep": out["s7_rep"]})
    print("\n  RECORDED_REAL = %r" % (rec,))
    out["record"] = rec

    # --- 所見を固定する(実データがあるときだけ鳴る) ---
    # ★下の閾値(+0.1 / +0.3 / 0.03 / 0.04 / +0.2)はすべて**実データを見てから置いた**(事後の門)。
    #   緩めずに、実測の記録値そのものとの一致(丸め 3 桁)を別に見る。
    assert nw["rho"] > z["rho"] + 0.1 and nw["rho"] > md["rho"] + 0.3, (z, md, nw)
    assert nw["mae"] < z["mae"] and nw["mae"] < md["mae"], (z, md, nw)
    assert out["median_strip"] < 0.03, out["median_strip"]
    assert out["narrow_plate_err"] < 0.04, out["narrow_plate_err"]
    assert by_shadow[7]["d_zero"] > by_shadow[7]["loss"] + 0.2, by_shadow[7]
    assert by_shadow[7]["d_narrow"] < by_shadow[7]["loss"], by_shadow[7]     # 過小に言うことも固定する
    if RECORDED_REAL:
        assert rec == RECORDED_REAL, "実測が記録値と違う(丸め 3 桁): %r" % (rec,)
        check_recorded_real(RECORDED_REAL)
    _real_figures(out, by_shadow, table, sh, s7, cache, rep7)
    return out


def _gray3(im: np.ndarray, rect) -> np.ndarray:
    r0, r1, c0, c1 = rect
    crop = im[r0:r1, c0:c1]
    g = np.clip(crop / max(float(np.quantile(crop, 0.995)), 1e-6), 0, 1)
    return np.repeat(g[..., None], 3, axis=2)


def _tint(g: np.ndarray, mask: np.ndarray, rgb) -> np.ndarray:
    o = g.copy()
    o[mask] = 0.45 * o[mask] + 0.55 * np.asarray(rgb)
    return o


def _odd_rows(sh) -> list:
    """CSV の出力をそのまま使った外れ(|出力低下| > 50 %)。除かずに印字と図の説明に出す。"""
    return [r for r in sh if abs(r["loss"]) > 0.5]


def _odd_text(odd) -> str:
    """外れの一覧の文字列(印字と散布図の説明で同じものを使う)。"""
    return "、".join("P%d S%d 出力低下 %+.0f %%" % (r["key"][0], r["key"][2], 100 * r["loss"]) for r in odd)


def _real_figures(out, by_shadow, table, sh, s7, cache, rep7) -> None:
    """実データの図: 表・代表(重ね)・入力・処理・結果・限界。"""
    if not figs.enabled():
        return
    figs.save_table("real_by_shadow", ["マスク", "枚数", "出力低下 %", "ゼロ点 Δ%", "中央値で割る Δ%",
                                       "細い成分だけ Δ%"], table,
                    title="実セル: マスクごとの出力低下と、暗部率の増え(中央値)",
                    caption="SIPV-EL(CC BY 4.0)。出力低下は I-V の実測、Δ はマスクなし S0 からの暗部率の増え。"
                            "マスクの分類は配布元の論文 Fig. 2。")
    # 代表: 上 = 中央の大円のマスク、下 = S7 の出力低下の中央値に最も近いセル
    panels, caps = [], []
    for key in (REP_SHADOW, rep7["key"]):
        if key not in cache:
            continue
        im, rect, m, m0, rec = cache[key]
        g = _gray3(im, rect)
        kind = "単結晶" if rec["kind"] == "Mono" else "多結晶"
        panels += [g, _tint(g, m["zero"], (1.0, 0.45, 0.1)), _tint(g, m["narrow"], (0.15, 0.55, 1.0))]
        caps += ["%s P%d S%d %s(I-V 出力低下 %.0f %%)" % (kind, key[0], key[2], SIPV_MASKS[key[2]],
                                                       100 * rec["loss"]),
                 "ゼロ点 暗部 %.0f %%(S0 比 %+.0f pt)" % (100 * rec["zero"], 100 * rec["d_zero"]),
                 "格子の細い成分を割る 暗部 %.0f %%(S0 比 %+.0f pt)" % (100 * rec["narrow"], 100 * rec["d_narrow"])]
    figs.save_grid("real_el_overlay", panels, caps, ncols=3,
                   title="実セルの EL 像: 遮光マスク(上)では暗部の面積が出力低下を追い、S7(下)では追わない"
                         "(橙 = ゼロ点の暗画素、青 = 格子を割った暗部)",
                   caption="SIPV-EL(Zenodo 14439369、CC BY 4.0)の実セル。上: セル表面に置いた遮光マスク(中央の大円)。"
                           "下: S7(論文の分類 7「その他の欠陥」と推定)のうち、出力低下が S7 の中央値 %.1f %% に最も近いセル。"
                           "灰色は実測の EL 強度、色は判定の重ね。出力低下は同じセル・同じ電流の I-V から。"
                           % (100 * by_shadow[7]["loss"]))
    # 入力: 同じセルのマスク 0〜6 と、S7 の代表セルの S0 / S7
    p, cur, _ = REP_SHADOW
    ins, icap = [], []
    for s in range(7):
        k = (p, cur, s)
        if k in cache:
            im, rect, _, _, rec = cache[k]
            ins.append(_gray3(im, rect)[..., 0])
            icap.append("S%d %s 出力低下 %.0f %%" % (s, SIPV_MASKS[s], 100 * rec["loss"]))
    for s in (0, 7):
        k = (rep7["key"][0], rep7["key"][1], s)
        if k in cache:
            im, rect, _, _, rec = cache[k]
            ins.append(_gray3(im, rect)[..., 0])
            icap.append("P%d S%d %s 出力低下 %.0f %%" % (k[0], s, SIPV_MASKS[s], 100 * rec["loss"]))
    figs.save_grid("real_input_masks", ins, icap, ncols=3, gray=[True] * len(ins),
                   title="実データの入力: 同じセルにマスクを置いて EL と I-V を撮る(SIPV-EL)",
                   caption="上 7 枚は単結晶セル P%d(電流 %s)の S0〜S6。マスクはアルミ箔つきの厚紙で、セルの表面に置いた"
                           "(配布元の論文)。S1 / S2 の帯の位置はセルによって入れ替わる。下 2 枚は S7 の代表セルとその S0。灰色は各像の 99.5 %% 分位で正規化。"
                           % (p, cur))
    # 処理: 縁の帯(S1)で、中央値プロファイルで割ると帯が消え、細い成分だけ割ると残る
    k1 = (p, cur, 1)
    if k1 in cache:
        im, rect, m, _, rec = cache[k1]
        r0, r1, c0, c1 = rect
        crop = im[r0:r1, c0:c1]
        flat_med = np.clip(degrid(crop) / 1.25, 0, 1)
        flat_nar = np.clip(degrid_narrow(crop) / 1.25, 0, 1)
        g = _gray3(im, rect)
        figs.save_grid("real_process_degrid",
                       [g, _tint(np.repeat(flat_med[..., None], 3, 2), m["median"], (0.15, 0.55, 1.0)),
                        _tint(np.repeat(flat_nar[..., None], 3, 2), m["narrow"], (0.15, 0.55, 1.0))],
                       ["実写 S1 縁の帯(出力低下 %.0f %%)" % (100 * rec["loss"]),
                        "中央値プロファイルで割る: 暗部 %+.0f pt" % (100 * rec["d_median"]),
                        "細い成分だけ割る(窓 %d px): 暗部 %+.0f pt" % (NARROW_WIN, 100 * rec["d_narrow"])],
                       ncols=3, title="格子を割る処理: 合成のレシピは縁の帯状のマスクを丸ごと消す",
                       caption="灰色は格子を割った後の像(1.25 で割って [0,1])、青は暗部判定。帯は行の中央値ごと暗いので、"
                               "行で割った瞬間に消える。窓 %d px は実データを見て決めた値。" % NARROW_WIN)
    # 結果: 出力低下 vs 暗部の増え(マスクつき全枚)
    lo = np.array([r["loss"] for r in sh]) * 100
    dz = np.array([r["d_zero"] for r in sh]) * 100
    dn = np.array([r["d_narrow"] for r in sh]) * 100
    ref = np.array([0.0, 60.0])
    figs.save_plot("real_result_scatter",
                   [("ゼロ点 ρ %.2f" % out["zero"]["rho"], lo, dz),
                    ("細い成分だけ割る ρ %.2f" % out["narrow"]["rho"], lo, dn),
                    ("暗部の増え = 出力低下", ref, ref)],
                   kinds=["scatter", "scatter", "line"], styles=[None, None, "dashed"],
                   colors=["wrong", "right", "reference"],
                   xlabel="I-V の出力低下 [%]", ylabel="暗部率の増え [pt]",
                   title="結果: 暗部の増えは I-V の出力低下を追うか(マスクつき %d 枚)" % len(sh),
                   caption="左上に離れた橙の点の群れは S7(「その他の欠陥」と推定)。全体が暗くなるのでゼロ点は面積を大きく数える。"
                           + ("外れ %d 点(%s)は CSV の出力をそのまま使った値で、除いていない。"
                              % (len(_odd_rows(sh)), _odd_text(_odd_rows(sh))) if _odd_rows(sh) else ""))
    # 限界: S7 は全体が暗くなるが出力は少ししか落ちない
    lo7 = np.array([r["loss"] for r in s7]) * 100
    br7 = np.array([r["bright"] for r in s7])
    figs.save_plot("real_limit_s7_dimming",
                   [("S7 の各セル", lo7, br7), ("出力低下と同じ割合で暗くなる線", ref, 1.0 - ref / 100.0)],
                   kinds=["scatter", "line"], styles=[None, "dashed"], colors=["wrong", "reference"],
                   xlabel="I-V の出力低下 [%]", ylabel="EL の平均の明るさ(S7 / S0)",
                   xlim=(min(-5.0, float(lo7.min()) - 2.0), max(60.0, float(lo7.max()) + 2.0)),
                   ylim=(0.0, max(1.1, float(br7.max()) + 0.05)),
                   title="限界: S7 は EL が %.2f〜%.2f 倍に暗いのに出力低下は中央値 %.1f %%"
                         % (round(float(br7.min()), 3), round(float(br7.max()), 3), 100 * by_shadow[7]["loss"]),
                   caption="明るさはセルの外枠の中の平均。暗さの原因は配布元に書かれていない。面積で数える方法は"
                           "どれもこの欠陥の出力低下を測れない(ゼロ点は過大、細い成分だけ割る経路は過小)。")


def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("太陽電池セルの EL 画像から発電損失を推定する —— 「暗い = 不活性」ではない")
    print("%d x %d px / フィンガー %d 本(周期 %.2f px)/ バスバー %d 本 / 結晶粒 %d 個"
          % (N, N, N_FINGER, PITCH, len(BUSBAR_X), GRAIN_N))
    print("=" * 78)

    sc = make_scene()
    print("  真値: 不活性面積率 %.2f %%(等級 %s)/ クラック %d 本 計 %.0f px / 断線 %d 本"
          % (sc["iso_rate"], grade(sc["iso_rate"]), len(CRACKS), sum(sc["crack_len"]),
             len(FI_BANDS)))

    zp = section_zero_point(sc)
    pipe = section_pipeline(sc)
    fr = section_frangi_norm()
    gr = section_grain_sweep()
    wd = section_width_sweep()
    vg = section_vignette_sweep()
    sn = section_snr_sweep()
    section_controls(pipe)
    section_tool_gaps()
    check_doc_synthetic(zp, sc, pipe, fr, gr, wd, sn)
    print("  docstring の合成部の数値: 実行の印字と文脈つきで一致")
    real = section_real_el()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点の暗画素率 %.1f %% は真値 %.2f %% の %.1f 倍(等級 %s、真値 %s)。"
          "暗画素のうち本物の不活性領域は %.0f %%。"
          % (zp["rate"], sc["iso_rate"], zp["rate"] / sc["iso_rate"], grade(zp["rate"]),
             grade(sc["iso_rate"]), 100.0 * zp["parts"]["孤立領域(本物)"] / zp["dark_n"]))
    print("  * 種類別に測ると 面積率誤差 %+.2f pt / クラック再現率 %.2f〜%.2f / 断線 %d/%d"
          "(等級 %s)。" % (pipe["iso_err"], min(pipe["recall"]), max(pipe["recall"]),
                          pipe["fi_matched"], len(FI_BANDS), grade(pipe["iso_rate"])))
    o0, o1, o2 = fr["out"].values()
    print("  * sk_frangi の最大値正規化: 校正なしは欠陥ゼロで偽クラック %.0f px、深いクラック"
          " 1 本で 5 本の再現率 %.2f → %.2f。強い校正線で %.0f px / %.2f → %.2f。"
          % (o0["false_raw"], o1["rec_raw"], o2["rec_raw"], o0["false_cal"],
             o1["rec_cal"], o2["rec_cal"]))
    print("  * 崖: 粒コントラスト c=%s で偽クラック(予測 %.2f)、断線は c=%s から飲まれる"
          "(予測 %.2f)/ クラック幅 %.2f px(予測 %.2f)/ 断線は K=%s で 8/8 を割る"
          "(予測 %.0f)/ ビネッティングは当てはめ込みで %+.2f〜%+.2f pt。"
          % (gr["onset"], gr["c_pred"], gr["fi_drop"], 1 - T_FI, wd["cliff"], wd["w_pred"],
             sn["k_fail"], sn["k_pred"], min(vg["e_fit"]), max(vg["e_fit"])))

    # 所見を固定する(壊れたら鳴る)
    assert zp["rate"] > 3.0 * sc["iso_rate"], zp["rate"]
    assert abs(pipe["iso_err"]) < 0.3, pipe["iso_err"]
    assert min(pipe["recall"]) > 0.85, pipe["recall"]
    assert pipe["fi_matched"] == len(FI_BANDS) and pipe["fi_false"] == 0, (
        pipe["fi_matched"], pipe["fi_false"])
    assert grade(pipe["iso_rate"]) == grade(sc["iso_rate"])
    assert max(abs(v) for v in vg["e_fit"]) < 0.3, vg["e_fit"]
    assert gr["onset"] is not None and gr["onset"] <= 0.32, gr["onset"]
    assert gr["fi_drop"] is not None and 0.18 <= gr["fi_drop"] <= 0.32, gr["fi_drop"]
    assert wd["cliff"] is not None and abs(wd["cliff"] - wd["w_pred"]) <= 0.3, (wd["cliff"], wd["w_pred"])
    assert sn["k_fail"] is not None and sn["k_fail"] <= 200, sn["k_fail"]
    if real is not None:
        print("  * 実セル(SIPV-EL、I-V が真値): 暗部の増えと出力低下の順位相関 ゼロ点 %+.2f / 中央値で割る %+.2f /"
              " 細い成分だけ割る %+.2f。中央値で割る経路は縁の帯状のマスクを消す。S7(その他の欠陥)は"
              "出力低下 %.1f %% にゼロ点 %+.0f pt。"
              % (real["zero"]["rho"], real["median"]["rho"], real["narrow"]["rho"],
                 100 * real["by_shadow"][7]["loss"], 100 * real["by_shadow"][7]["d_zero"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
