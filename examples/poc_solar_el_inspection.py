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

1. ★★**ゼロ点(大域しきい値の暗画素率)は 40.9 % で、真値 5.7 % の 7.2 倍**。
   内訳を真値マスクで割ると、暗画素の 57 % はフィンガー/バスバー、
   26 % はビネッティングと結晶粒 —— **本当の欠陥は暗画素の 15 % しか無い**。
   等級は D(真値は C)。面積率を 1 つに畳むと結晶粒が損失に化ける。
2. **ビネッティングを cos^4 則で当てはめ(強さ 0.500 → 推定 0.500)、
   フィンガー/バスバーを行・列の中央値プロファイルで割る**と、
   不活性面積率は 5.75 % → 推定 5.72 %(誤差 -0.03 ポイント)、
   クラック長は 5 本とも再現率 0.94〜1.00、断線 8 本中 8 本、偽検出 0。
   等級 C で真値と一致。
3. ★**sk_frangi の出力は画像ごとの最大値で正規化されるので、欠陥の無い
   セルでは雑音が 1.0 に伸びる**。そのままヒステリシスを掛けると欠陥ゼロの
   対照セルで偽クラック 1108 px。**既知の深さの校正線を 1 本貼って**正規化を
   固定すると 0 px。「相対値しか返さない op」は欠陥の有無で意味が変わる。
4. ★結晶粒のコントラスト c を 0 → 0.40 で振ると、偽クラックは c=0.32 から
   出はじめる(予測はヘッセ行列の比から c≈0.30)。**偽の断線は最後まで 0**
   —— 暗い粒は T_FI=0.82 を c>0.18 で割り込むが、断線を「細長く水平」で
   選ぶ形の門が粒(塊)を全部落とす。面積率の誤差は c=0.40 でも +0.02 ポイント。
5. ★クラック幅 0.5 → 3.0 px: 再現率は 0.75 px で 0.63、1.0 px 以上で 0.9 超。
   予測(校正線 1.5 px を基準にヒステリシス上限 0.5 → 崖は 0.75 px)と一致。
   **崖の位置は校正線の幅が決めている** —— 検出したい最小幅で校正線を作ること。
6. ★ビネッティング強さ 0 → 1.0: cos^4 当てはめ込みなら面積率誤差は
   -0.03〜+0.07 ポイントで動かない。当てはめを外して行列プロファイルだけに
   すると、**予想(隅が T_ISO=0.42 を割る強さ 0.74 で偽の孤立領域)は外れた**:
   分離可能近似が隅を 2.3 倍明るく戻してしまい、隅ではなく**辺の中央**が
   暗く残る。誤差は強さ 1.0 で +0.09 ポイントに留まる。
7. 光子数 K を 2000 → 8 で振ると、断線は K=20 まで 8/8、K=8 で 6/8。
   予測は「σ=1 平滑後の雑音が余裕 0.17 の半分になる K≈21」で、実測の崖は
   その半分 —— 予測は安全側に外れた。クラック再現率は K=8 でも 0.85。

【グラウンドトゥルース】
セルは**閉形式**で合成する(2 倍のスーパーサンプリングで描いて平均し、
サブピクセル幅のフィンガーとクラックを正しく写す): フィンガー 100 本
(周期 3.85 px、幅 0.9 px、透過 0.45)、バスバー 3 本(幅 6 px、透過 0.25)、
結晶粒 = 70 個の Voronoi 領域(明るさ 1 ± c)、クラック 5 本(幅 1.5 px、
透過 0.35、向き 15〜155 度)、孤立領域 2 つ(隅の三角形と右端の帯、透過 0.20、
面積 = 幾何で決まる真値)、断線 8 本(フィンガー沿いの帯、透過 0.65)。撮像 =
cos^4 ビネッティング(``aug_vignette``)+ ガウスぼけ σ 0.7 px + ポアソン雑音。
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
from scipy.ndimage import binary_dilation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

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

FI_T = 0.65                 # 断線した先(バスバーへ電流が戻れない帯)の透過率
#: 断線 8 本: (フィンガー番号, 帯の x 範囲) —— 外側区間(端〜バスバー)に置く
FI_BANDS = ((12, 22.0, 58.0), (25, 20.0, 60.0), (38, 0.0, 50.0),
            (47, 10.0, 62.0), (58, 350.0, 400.0), (70, 345.0, 383.0),
            (83, 0.0, 28.0), (91, 300.0, 345.0))

VIG_A, VIG_B = 0.5, 0.5     # aug_vignette の強さ / 落ち込み半径
BLUR = 0.7                  # ぼけ σ [px]
PHOTONS = 200               # 明るさ 1.0 あたりの光子数(ポアソン雑音)
EXPOSURE = 0.8              # 健全部の明るさ

T_ISO, T_FI = 0.42, 0.82    # 分類しきい値(平坦化後の相対明るさ)
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
               defects: bool = True) -> dict:
    """EL 画像と、種別ごとの真値を返す。"""
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
        for cy, cx, ln, deg in CRACKS:
            base = base * np.where(_seg_dist(yy, xx, cy, cx, ln, deg) < crack_w / 2,
                                   CRACK_T, 1.0)
        yl, xl = np.mgrid[0:N, 0:N] + 0.5
        for cy, cx, ln, deg in CRACKS:
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
            "crack_len": [c[2] for c in CRACKS] if defects else [],
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


FIT_Q = 0.8                 # 半径ビンの代表値に使う分位(欠陥は暗くしかしないので上側)


def fit_vignette(img: np.ndarray, nbins: int = 20) -> tuple[float, float]:
    """半径ビンの上側分位に cos^4 則を当てはめる。

    中央値ではなく **80 % 分位**を使う —— EL の欠陥は暗くしかしない(明るく
    する欠陥は無い)ので、上側の分位は暗い欠陥に頑健。隅のリングは 4 隅の
    小さな面積しか無く、そのうち 2 隅が孤立領域で暗いと**中央値は落ちる**
    (最初は中央値で書いて、強さ 0.5 を 1.0 と当ててしまった)。
    """
    r = _radius(img.shape)
    edges = np.linspace(0, 1.0, nbins + 1)
    rc, med = [], []
    for k in range(nbins):
        sel = (r >= edges[k]) & (r < edges[k + 1])
        if sel.sum() > 50:
            rc.append(0.5 * (edges[k] + edges[k + 1]))
            med.append(float(np.quantile(img[sel], FIT_Q)))
    rc, lm = np.asarray(rc), np.log(np.asarray(med))
    best = (np.inf, 0.0, 1.0)
    for a in np.linspace(0, 1, 51):
        for R in np.arange(0.35, 1.5001, 0.025):
            m = np.log(1.0 - a + a / (1.0 + (rc / R) ** 2) ** 2)
            res = lm - m
            cost = float(np.sum((res - res.mean()) ** 2))
            if cost < best[0]:
                best = (cost, float(a), float(R))
    return best[1], best[2]


def flatten(img: np.ndarray, use_fit: bool = True) -> tuple[np.ndarray, tuple]:
    """ビネッティングを割る。補正そのものは ``aug_vignette`` を前向きモデルに使う。"""
    if not use_fit:
        return img, (np.nan, np.nan)
    a, R = fit_vignette(img)
    v = np.asarray(fs.apply(np.ones_like(img), "aug_vignette", a=a, b=(R - 0.35) / 1.15))
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


def ridge_map(s: np.ndarray, calibrate: bool = True, ref_w: float = CRACK_W) -> np.ndarray:
    """暗いリッジ(sk_frangi)の応答。

    ``calibrate=True`` なら、既知の深さ・幅の**校正線**を画像の下に貼ってから
    Frangi を掛ける。``sk_frangi`` は出力を画像ごとの最大値で正規化するので、
    こうしないと「いちばん強いリッジ = 1.0」が雑音でも成り立ってしまう。
    返す配列は校正線を切り落とした元の大きさ(校正線 = 1.0 の尺度)。
    """
    v = np.clip(s / 1.25, 0.0, 1.0)
    if calibrate:
        strip = np.ones((REF_ROWS, v.shape[1]))
        full = int(np.floor(ref_w))
        r0 = REF_ROWS // 2 - full // 2
        strip[r0:r0 + full, :] = CRACK_T
        frac = ref_w - full
        if frac > 0:
            strip[r0 + full, :] = 1.0 - frac * (1.0 - CRACK_T)
        v = np.vstack([v, strip])
    ridge = np.asarray(fs.apply(v, "sk_frangi", a=0.25, b=0.5))
    if calibrate:
        ridge = ridge[:s.shape[0]].copy()
        ridge[-2:, :] = 0.0               # 校正線の縁の影響を落とす
    return ridge


def crack_skeleton(s: np.ndarray, calibrate: bool = True, ref_w: float = CRACK_W,
                   low: float = 0.2, high: float = 0.5) -> np.ndarray:
    """リッジ応答 → ヒステリシス → 骨格(1 px 幅のクラック中心線)。"""
    ridge = ridge_map(s, calibrate=calibrate, ref_w=ref_w)
    hyst = np.asarray(fs.apply(ridge, "hysteresis_threshold",
                               a=(low - 0.2) / 0.3, b=(high - 0.5) / 0.3))
    return np.asarray(fs.apply(hyst, "sk_skeleton")) > 0.5


def classify(s: np.ndarray, crack_sk: np.ndarray) -> dict:
    """平坦化後の明るさで 孤立領域 / 断線帯 を分ける。"""
    ss = np.asarray(fs.apply(np.clip(s / 1.25, 0, 1), "gaussian", a=(1.0 - 0.3) / 2.7)) * 1.25
    iso_c = ss < T_ISO
    lab = _LAB.blob_label(iso_c)
    iso = np.zeros_like(iso_c)
    if int(lab.max()) > 0:
        iso = _LAB.blob_select(lab, "area", vmin=150.0) > 0
    near_crack = binary_dilation(crack_sk, iterations=2)
    fi_c = (ss >= T_ISO) & (ss < T_FI) & ~near_crack & ~binary_dilation(iso, iterations=2)
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


def analyze(sc: dict, use_fit: bool = True, calibrate: bool = True,
            ref_w: float = CRACK_W) -> dict:
    """1 枚を通しで解析し、種類別に真値と突き合わせる。"""
    flat, fit = flatten(sc["img"], use_fit=use_fit)
    s = degrid(flat)
    sk = crack_skeleton(s, calibrate=calibrate, ref_w=ref_w)
    cl = classify(s, sk)

    # クラック: 本ごとの再現率(真値中心線が骨格の 2 px 以内にある割合)
    sk_d = binary_dilation(sk, iterations=2)
    recall = [float(sk_d[m].mean()) for m in sc["crack_lines"]]
    any_true = np.zeros_like(sk)
    for m in sc["crack_lines"]:
        any_true |= m
    near_true = binary_dilation(any_true, iterations=3)
    near_iso = binary_dilation(sc["iso"], iterations=5)
    matched_len = _skeleton_length(sk & near_true)
    false_len = _skeleton_length(sk & ~near_true & ~near_iso)
    iso_edge_len = _skeleton_length(sk & ~near_true & near_iso)

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
                   caption="単位は % of セル面積。暗画素の 6 割はフィンガーとバスバー。")
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
    ridge = np.asarray(fs.apply(np.clip(r["s"] / 1.25, 0, 1), "sk_frangi", a=0.25, b=0.5))
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
    print("3) ★sk_frangi は画像ごとの最大値で正規化する —— 欠陥ゼロの対照セル")
    print("=" * 78)
    sc0 = make_scene(defects=False)
    s0 = degrid(flatten(sc0["img"])[0])
    v = np.clip(s0 / 1.25, 0, 1)
    ridge = np.asarray(fs.apply(v, "sk_frangi", a=0.25, b=0.5))
    print("  欠陥ゼロの平坦化像に Frangi: 最大 %.3f / 99 %% 分位 %.3f / 中央値 %.4f"
          % (ridge.max(), np.quantile(ridge, 0.99), np.median(ridge)))
    raw = crack_skeleton(s0, calibrate=False)
    cal = crack_skeleton(s0, calibrate=True)
    len_raw, len_cal = _skeleton_length(raw), _skeleton_length(cal)
    print("  同じヒステリシス(0.2 / 0.5)で偽クラック: 校正線なし %.0f px / "
          "校正線あり %.0f px" % (len_raw, len_cal))
    sc = make_scene()
    s = degrid(flatten(sc["img"])[0])
    ridge1 = np.asarray(fs.apply(np.clip(s / 1.25, 0, 1), "sk_frangi", a=0.25, b=0.5))
    print("  欠陥ありでは 99 %% 分位 %.3f —— 同じ op、同じ雑音でも欠陥の有無で"
          "スケールが変わる。" % np.quantile(ridge1, 0.99))
    print("  ★対処: 既知の深さ %.2f・幅 %.1f px の校正線を画像の下に貼り、"
          "正規化の分母をそれに固定する。" % (CRACK_T, CRACK_W))
    assert len_cal < 0.05 * max(len_raw, 1.0), (len_raw, len_cal)
    figs.save_grid("frangi_norm", [ridge, raw.astype(np.float64), cal.astype(np.float64)],
                   ["欠陥ゼロ: Frangi 応答(最大 1.0 に伸びる)",
                    "校正線なし: 偽クラック %.0f px" % len_raw,
                    "校正線あり: %.0f px" % len_cal],
                   ncols=3, title="相対値しか返さない op は欠陥の有無で意味が変わる")
    return {"len_raw": len_raw, "len_cal": len_cal, "q99_clean": float(np.quantile(ridge, 0.99)),
            "q99_defect": float(np.quantile(ridge1, 0.99))}


# --------------------------------------------------------------------------- #
# 4. 崖: 結晶粒のコントラスト                                                   #
# --------------------------------------------------------------------------- #
def section_grain_sweep() -> dict:
    print("\n" + "=" * 78)
    print("4) 崖: 結晶粒のコントラスト c を上げると、どこで粒が欠陥に化けるか")
    print("=" * 78)
    sig = 1.0
    step_h = 1.0 / (sig ** 2 * np.sqrt(2 * np.pi * np.e))          # 段差 1 の 2 階微分の最大
    line_h = CRACK_W * (1 - CRACK_T) / (np.sqrt(2 * np.pi) * sig ** 3)  # 線の 2 階微分
    c_pred = 0.2 * line_h / step_h
    print("  予測: 暗い粒が T_FI=%.2f を割るのは c > %.2f、T_ISO=%.2f を割るのは c > %.2f。"
          % (T_FI, 1 - T_FI, T_ISO, 1 - T_ISO))
    print("        粒の段差(高さ c)がヒステリシス下限 0.2 に届くのは、σ=%.0f の"
          "ヘッセ行列の比 %.3f/%.3f から c ≈ %.2f。" % (sig, step_h, line_h, c_pred))
    print("\n     c     偽クラック [px]  偽の断線  一致した断線  面積率誤差 [pt]  粒→孤立 [%]")
    cs, false_len, fi_false, fi_ok, iso_err = [], [], [], [], []
    for c in (0.0, 0.06, 0.12, 0.18, 0.24, 0.32, 0.40):
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
    print("\n  ★偽クラックが 30 px を超えるのは c=%s(予測 %.2f)。偽の断線は最大 %d 本 —— "
          "暗い粒は c>%.2f で T_FI を割るが、「細長く水平」の形の門が塊を落とす。"
          % (onset, c_pred, max(fi_false), 1 - T_FI))
    print("     面積率の誤差は c=%.2f でも %+.2f ポイント。" % (cs[-1], iso_err[-1]))
    figs.save_plot("grain_contrast", [("偽クラック長 [px]", cs, false_len),
                                      ("偽の断線 [本] x 100", cs, [100 * v for v in fi_false]),
                                      ("面積率誤差 [pt] x 100", cs, [100 * v for v in iso_err])],
                   xlabel="結晶粒のコントラスト c", ylabel="偽検出",
                   title="粒のコントラストを上げると先に壊れるのはクラック",
                   caption="断線と面積率は c=0.40 でも壊れない。形の門と面積の門が効く。")
    return {"c": cs, "false_len": false_len, "fi_false": fi_false, "iso_err": iso_err,
            "onset": onset, "c_pred": c_pred}


# --------------------------------------------------------------------------- #
# 5. 崖: クラック幅                                                             #
# --------------------------------------------------------------------------- #
def section_width_sweep() -> dict:
    print("\n" + "=" * 78)
    print("5) 崖: クラック幅 0.5 → 3.0 px の再現率")
    print("=" * 78)
    w_pred = 0.5 * CRACK_W
    print("  予測: Frangi の応答は幅に比例(σ より細い間)。校正線 %.1f px = 1.0 なので、"
          "ヒステリシス上限 0.5 を割るのは幅 < %.2f px。" % (CRACK_W, w_pred))
    print("\n    幅 [px]   再現率(5 本の平均)  最小   一致長/真値   偽 [px]")
    ws, rec, mn = [], [], []
    for w in (0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
        sc = make_scene(crack_w=w)
        r = analyze(sc)
        ws.append(w)
        rec.append(float(np.mean(r["recall"])))
        mn.append(float(min(r["recall"])))
        print("    %4.2f         %.2f            %.2f      %.2f        %.0f"
              % (w, rec[-1], mn[-1], r["matched_len"] / r["true_len"], r["false_len"]))
    cliff = next((w for w, v in zip(ws, rec) if v >= 0.5), None)
    print("\n  ★再現率 0.5 を超えるのは幅 %.2f px から(予測 %.2f px)。"
          "**崖の位置は校正線の幅が決める** —— 検出したい最小幅で校正線を作ること。"
          % (cliff, w_pred))
    figs.save_plot("crack_width", [("再現率(平均)", ws, rec), ("再現率(最小)", ws, mn),
                                   ("予測の崖 %.2f px" % w_pred, [w_pred, w_pred], [0, 1])],
                   xlabel="クラック幅 [px]", ylabel="再現率",
                   title="クラック幅の崖は校正線の幅の半分に出る")
    return {"w": ws, "recall": rec, "cliff": cliff, "w_pred": w_pred}


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
    print("\n    強さ a   当てはめ a   面積率誤差 [pt]: 当てはめ込み / プロファイルだけ"
          "   ゼロ点暗画素率 [%]")
    as_, e_fit, e_grid, zero, ahat = [], [], [], [], []
    for a in (0.0, 0.25, 0.5, 0.75, 1.0):
        sc = make_scene(vig_a=a)
        r1 = analyze(sc, use_fit=True)
        r2 = analyze(sc, use_fit=False)
        dark = 100.0 * float((np.asarray(fs.apply(sc["img"], "otsu")) < 0.5).mean())
        as_.append(a)
        ahat.append(r1["fit"][0])
        e_fit.append(r1["iso_err"])
        e_grid.append(r2["iso_err"])
        zero.append(dark)
        print("    %4.2f       %.3f          %+6.2f            %+6.2f              %5.1f"
              % (a, r1["fit"][0], r1["iso_err"], r2["iso_err"], dark))
    print("\n  ★当てはめ込みは %+.2f〜%+.2f ポイントで動かない。プロファイルだけでも "
          "a=1.0 で %+.2f ポイント —— 予想「a>%.2f で隅が偽の孤立領域になる」は外れた。"
          % (min(e_fit), max(e_fit), e_grid[-1], a_iso))
    print("     分離可能近似が隅を %.1f 倍に戻すので、暗く残るのは隅でなく辺の中央。"
          % resid[0, 0])
    figs.save_plot("vignette", [("cos^4 当てはめ込み", as_, e_fit),
                                ("行列プロファイルだけ", as_, e_grid)],
                   xlabel="ビネッティングの強さ a", ylabel="不活性面積率の誤差 [pt]",
                   title="隅の孤立領域はビネッティングに食われない")
    return {"a": as_, "e_fit": e_fit, "e_grid": e_grid, "zero": zero, "ahat": ahat,
            "a_iso": a_iso, "resid_corner": float(resid[0, 0])}


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
    ks, fi_ok, rec, err = [], [], [], []
    for k in (2000, 500, 200, 50, 20, 8):
        sc = make_scene(photons=k)
        r = analyze(sc)
        ks.append(k)
        fi_ok.append(r["fi_matched"])
        rec.append(float(np.mean(r["recall"])))
        err.append(r["iso_err"])
        print("   %5d       %d/%d  %2d         %.2f               %+6.2f          %6.0f"
              % (k, r["fi_matched"], len(FI_BANDS), r["fi_false"], rec[-1], r["iso_err"],
                 r["false_len"]))
    k_fail = next((k for k, n in zip(ks, fi_ok) if n < len(FI_BANDS)), None)
    print("\n  ★断線が 8/8 を割るのは K=%s(予測 K≈%.0f)。クラック再現率は K=%d でも %.2f。"
          % (k_fail, k_pred, ks[-1], rec[-1]))
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


# --------------------------------------------------------------------------- #
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
    print("  * sk_frangi の最大値正規化: 欠陥ゼロで偽クラック %.0f px → 校正線で %.0f px。"
          % (fr["len_raw"], fr["len_cal"]))
    print("  * 崖: 粒コントラスト c=%s で偽クラック(予測 %.2f)/ クラック幅 %.2f px"
          "(予測 %.2f)/ 断線は K=%s で 8/8 を割る(予測 %.0f)/ ビネッティングは"
          "当てはめ込みで %+.2f〜%+.2f pt。"
          % (gr["onset"], gr["c_pred"], wd["cliff"], wd["w_pred"], sn["k_fail"],
             sn["k_pred"], min(vg["e_fit"]), max(vg["e_fit"])))

    # 所見を固定する(壊れたら鳴る)
    assert zp["rate"] > 5.0 * sc["iso_rate"], zp["rate"]
    assert abs(pipe["iso_err"]) < 0.3, pipe["iso_err"]
    assert min(pipe["recall"]) > 0.85, pipe["recall"]
    assert pipe["fi_matched"] == len(FI_BANDS) and pipe["fi_false"] == 0, (
        pipe["fi_matched"], pipe["fi_false"])
    assert grade(pipe["iso_rate"]) == grade(sc["iso_rate"])
    assert max(abs(v) for v in vg["e_fit"]) < 0.3, vg["e_fit"]
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
