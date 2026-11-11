# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""コンクリートのひび割れ幅は 1 画素より細い —— 数える幅と、積分する幅。

橋・トンネル・擁壁の点検で最初に書く数字が「ひび割れ幅 何 mm」です。設計上の
限界(たとえば 0.2 mm)が 1 画素より細いのが普通なので、**2 値化して数える**
やり方は原理的に届きません。この PoC は、真値を仕込んだ合成画像で

* ゼロ点 = 2 値化 → 細線化 → 距離変換の 2 倍(= 整数画素の幅)
* 積分法 = ひび割れに直交する断面の**輝度欠損を積分**して幅に換算

を同じ場面で測り比べ、**どちらがどこで壊れるか**を実測で分けます。

EXTEND: 実写に差し替えるなら :func:`render` が返す辞書の ``img`` を撮影画像に、
``width_mm`` を**クラックスケール(ひび割れゲージ)で読んだ幅**に置き換えます。
経路 ``path_y`` は :func:`measure_integral` に渡す中心線で、実写では
:func:`detect_path` が返すもの(データから引いた尾根)を使ってください。
``PX_MM`` は必ず実測(スケールバーか、既知寸法の目地)で決めること —— この
PoC の結論は全部 mm/px を通して出ているので、そこが 10 % ずれれば全部ずれます。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点は幅 0.20 mm(1.0 px)以下だと何も返さない**。0.20 mm と 0.05 mm の
   区別がつかないのではなく、**どちらも「ひび割れなし」になる**。値が返る
   のは 0.25 mm(1.25 px)から。設計限界が 0.2 mm の世界で、限界そのものが
   測れない。しかも返る値は階段で、**真値 0.25〜0.40 mm の 4 条件が全部
   同じ 0.200 mm を返す**(真値は 1.6 倍違う)。
2. ★**同じマスクから、規約 2 通りで幅がちょうど 0.20 mm 違う**。距離変換の
   2 倍(``2·EDT``)と、離散格子の作法どおりの ``2·EDT − 1`` の差は 1 画素。
   **測ろうとしている量と同じ大きさ**なので、どちらの規約かを書かない
   「幅 0.4 mm」には意味が無い。
3. ★★**積分法は 0.05 mm(0.25 px)まで連続に追える**。きれいな場面での
   偏りは全幅で -0.15 〜 +0.05 %(0.25 px の帯を含む)。輝度欠損の**総量**は
   畳み込み(レンズのぼけ)でも画素化でも保存されるからで、幅が画素を
   下回っても情報は消えていない。1 節でその保存を 1e-8 の桁まで検算する。
4. ★★**積分法の弱点は照明ではなく「ベースラインの次数」だった**。予想は
   「照明の傾斜に弱い」だったが、**傾斜(1 次)は 1 次のベースラインで
   完全に抜ける**(誤差 +0.0000 mm)。壊れるのは照明が**曲がっている**とき
   で、1 次のままだと +0.1741 mm の下駄が乗る。2 次にすると +0.0062 mm。
   予想は半分外れ。
5. ★★**畳むと逆の結論が出る**。ざらつき σ=0.07 で、**点ごと**の RMS は
   積分法 0.2431 / 2 値化 0.1368 mm で 2 値化の勝ち。**経路平均**にすると
   積分法 0.0264 / 2 値化 0.0580 mm で逆転する。積分法の誤差は偏りの無い
   散らばりなので平均で消え、2 値化の誤差は**偏り**(-0.031 〜 -0.102 mm)
   なので消えない。1 つの数字に畳むと、直せる誤差と直せない誤差が混ざる。
   ざらつきをさらに上げると経路平均でも σ=0.16 で入れ替わる —— **入れ替わり
   の位置は「どう畳むか」で 4 倍動く**。
6. ★★**最大幅は必ず過大になり、その量は閉形式で予測できる**。真の幅
   0.60 mm を 4 点で測ると最大 0.839 mm、122 点で測ると 1.184 mm
   (**+57 %。真の幅は 1 μm も変わっていない**)。標本最大値の漸近式
   σ·a_N との比は 0.81〜0.90 で**一貫して 1 未満**。理由も測ってある ——
   隣の測点と窓が重なるので独立でない(1 次自己相関 0.22、有効点数
   77/122)。規格が最大幅で書かれている以上、**測点密度を書かない報告は
   比較できない**。
7. ★**予想が外れた: 経路の検出は測定より易しい**。σ=0.05 なら幅 0.10 mm
   (0.5 px)でも列ごとの尾根追跡は 1 列も外れない(経路誤差 0.16 px)。
   崩れるのは幅ではなく**ざらつき**で、σ=0.10 で 34/91 列が飛び、
   幅が +0.16 mm 過大になる。「細いから検出できない」ではなかった。
8. ★★**実写(公開のひび割れ写真 159 枚)で示せたのは「画素を粗くしたとき幅を保つのはどちらか」まで**。
   1 画素より細いひびの幅は、実写では確かめていない(幅の真値が付いた公開データが無い)。
   ★まず元の画素の値の妥当性: 見た目の幅(断面の半値幅、中央値 11.75 px)に対し、積分を芯の欠損で
   割った値は半値幅の 0.75 倍で「幅 x 深さ」と矛盾しない。★0.75 は 1 枚の中の断面の積分を平均で
   まとめた値(芯の欠損と半値幅は中央値)で、積分も中央値でまとめると 0.82。平均は積分の小さい断面に
   引き下げられ、経路が外れた断面を除くと平均も 0.82 になる。★1 を下回る原因は確かめきれていない(矩形・
   三角・ガウスの断面なら 1.00〜1.06 で、裾が細っても 1 を下回らない)。要因を 1 つずつ振ると、
   ベースラインを 1 次にして 0.84、経路が外れた断面(1 枚あたり 18 %)を除いて 0.82 で、どちらも 1 に
   届かない。中央値・1 次・経路上を組み合わせても 0.88。「経路が外れた」(断面の最大が 3 px より外)は
   幅の広いひびで多めに数える —— 経路が半値幅の区間の外に出る断面で数え直すと 9 % だが、除いた値は 0.82 で
   変わらない。明るい縁は、負の欠損を 0 で切った上がり幅が同じ大きさの雑音の合成と区別できなかった。
   芯が黒い合成は雑音なしで 1.05、実写と同じくらいの雑音で 0.96〜1.12。2 値化は半値幅の 0.24 倍で、芯が灰色の
   実写では芯の一部しか拾わない —— 元の画素の 2 値化の幅は見た目の幅として使えない。
   幅の真値の代わりに**同じひびを画素 k x k の平均で撮り直しても幅は変わらない**ことを使う(各手法の
   自己整合)。4 倍粗くすると幅の比の中央値は 積分法 1.13 倍 / 2 値化 1.44 倍。★言えるのは k=4 の
   中央値までで、四分位は 積分法 0.97〜1.44 / 2 値化 1.22〜1.78 と重なり、k=3 では差が 0.03。
   ★★合成ではざらつき無しなら 1 % 以内だった積分法の保存が、実写では崩れる(地の穴や汚れが
   断面のベースラインに入る)。実写のひびは芯が灰色(欠損 0.54)なので、2 値化は粗くなると「消える」
   より 1 画素の床で「膨らむ」。積分法の値を mm に直すには芯の深さの較正が要る。2 万枚は 458 枚の
   元写真からの切り出しで、100 おきに選んだ写真どうしは遠い番号の写真と同じくらい違う(独立の目安)。
   データは repo に入れない(``tools/fetch_realinsp_data.py``)。無い環境では記録値を印字する。

【グラウンドトゥルース】
ひび割れは「暗い帯」として**解析的に描く**。画素 (i,j) の被覆率は、帯と画素
矩形の重なり面積を **列方向は解析的に、行方向は 1/16 画素刻みの求積**で出す
(ビットマップを描いて数えるのではない)。したがって幅 0.25 画素の帯も
「被覆率 0.25 の 1 画素」として正しく載る。レンズのぼけ(ガウス PSF)は
被覆率に掛けるので、**輝度欠損の総量は厳密に保存される** —— 1 節で検算する。

来歴(公開文献のみ): 土木学会コンクリート標準示方書(ひび割れ幅の照査)/
Zhang-Suen, *CACM* 27 (1984) 236 —— 細線化 / Otsu, *IEEE SMC* 9 (1979) 62 /
Gumbel, *Statistics of Extremes* (1958) —— 標本最大値の期待値。
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, median_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
W_PX, H_PX = 768, 224      # 視野 [px]
PX_MM = 0.20               # 画素寸法 [mm/px] -> 視野 153.6 x 44.8 mm
PSF_SIGMA = 0.8            # レンズ + 画素開口をまとめたガウス PSF [px]

CY, AMP, LAM, PHASE = 112.0, 18.0, 900.0, 0.5   # ひび割れの経路(正弦 + 傾き)
SLOPE = 0.025

R_PROF = 18.0              # 断面の半長 [px]
DT_PROF = 0.25             # 断面の刻み [px]
T_BASE = 11.0              # |t| >= これをベースライン(地の輝度)の当てはめに使う
BG_ROWS = 41               # 2 値化の背景推定に使う列方向メディアン窓 [px]
BIN_LEVEL = 0.5            # 2 値化のしきい値(欠損率の半値 = 教科書の半値幅規約)

SEED = 5


# --------------------------------------------------------------------------- #
# 場面を作る —— 帯の被覆率を解析的に出す                                        #
# --------------------------------------------------------------------------- #
def path_y(x):
    """ひび割れの中心線 y(x) とその傾き dy/dx。"""
    x = np.asarray(x, np.float64)
    k = 2.0 * np.pi / LAM
    y = CY + AMP * np.sin(k * x + PHASE) + SLOPE * (x - 0.5 * W_PX)
    dy = AMP * k * np.cos(k * x + PHASE) + SLOPE
    return y, dy


def width_taper(x):
    """幅 w(s) の一例 —— 中ほどで開いて両端で閉じるひび割れ [mm]。"""
    x = np.asarray(x, np.float64)
    return 0.08 + 1.40 * np.exp(-(((x - 0.42 * W_PX) / (0.28 * W_PX)) ** 2))


def _coverage(width_fn, kx: int = 16) -> np.ndarray:
    """帯が各画素を覆う面積比 (H,W)。行方向は解析、列方向は ``kx`` 分割の求積。

    画素 (i,j) は y in [i-.5, i+.5], x in [j-.5, j+.5]。帯は中心線から
    **垂直距離** w/2 以内なので、abscissa x での縦方向の半幅は
    ``h = (w/2)·sqrt(1+f'^2)``(曲率の効果は 2 次で、この経路では
    半径 ~1.3e3 px なので最大幅でも 0.4 % 以下)。
    """
    sub = (np.arange(kx) + 0.5) / kx - 0.5
    xs = (np.arange(W_PX)[:, None] + sub[None, :]).ravel()        # (W*kx,)
    yc, dy = path_y(xs)
    half = 0.5 * np.asarray(width_fn(xs), np.float64) * np.sqrt(1.0 + dy * dy)
    lo, hi = yc - half, yc + half
    rows = np.arange(H_PX, dtype=np.float64)[:, None]
    cov = np.zeros((H_PX, W_PX))
    step = 64                                                     # 列をまとめて処理
    for j0 in range(0, W_PX, step):
        sl = slice(j0 * kx, min(j0 + step, W_PX) * kx)
        ov = np.minimum(hi[None, sl], rows + 0.5) - np.maximum(lo[None, sl], rows - 0.5)
        np.clip(ov, 0.0, None, out=ov)
        cov[:, j0:j0 + step] = ov.reshape(H_PX, -1, kx).mean(axis=2)
    return cov


def _texture(sigma: float, seed: int) -> np.ndarray:
    """コンクリート面のざらつき(相関長 2.5 px の乗算性の場)+ 細かい粒。"""
    if sigma <= 0.0:
        return np.zeros((H_PX, W_PX))
    rng = np.random.default_rng(seed)
    f = gaussian_filter(rng.standard_normal((H_PX, W_PX)), 2.5)
    f /= f.std() or 1.0
    return sigma * f + 0.25 * sigma * rng.standard_normal((H_PX, W_PX))


def _illum(slope: float, curve: float) -> np.ndarray:
    """照明。``slope`` = 左右方向の 1 次傾斜、``curve`` = 上下方向の曲がり。"""
    yy, xx = np.mgrid[0:H_PX, 0:W_PX].astype(np.float64)
    lit = 1.0 - slope * (xx / W_PX)
    if curve:
        lit = lit + curve * np.cos(2.0 * np.pi * (yy - 40.0) / 130.0)
    return lit


def render(width_fn, *, texture=0.0, slope=0.0, curve=0.0, seed=SEED) -> dict:
    """場面 1 枚。``width_fn(x)`` が真の幅 [mm] を返す。

    ひび割れは**光を返さない空洞**として扱う(被覆率 1 の画素は真っ黒)。
    実写のひび割れは奥で少し明るいので、ここは楽観側の仮定 —— 積分法の
    換算係数(欠損 1 = 幅 1 画素)がそのまま使えるのはこの仮定のおかげで、
    実写では最も広い断面の飽和度で較正することになる。
    """
    cov = _coverage(lambda x: np.asarray(width_fn(x)) / PX_MM)
    cov_b = gaussian_filter(cov, PSF_SIGMA)
    base = _illum(slope, curve) * (1.0 + _texture(texture, seed))
    img = np.clip(base * (1.0 - cov_b), 0.0, None)
    xs = np.arange(W_PX, dtype=np.float64)
    return {"img": img, "cov": cov, "cov_blur": cov_b, "base": base,
            "width_mm": np.asarray(width_fn(xs), np.float64),
            "y": path_y(xs)[0], "dy": path_y(xs)[1]}


# --------------------------------------------------------------------------- #
# ゼロ点 —— 2 値化 → 細線化 → 距離変換の 2 倍                                   #
# --------------------------------------------------------------------------- #
def deficit_map(img: np.ndarray) -> np.ndarray:
    """地の輝度で割った輝度欠損 1 - I/bg。地は**列方向のメディアン**で出す。

    ひび割れは最大でも 10 px なので、41 行のメディアンは帯に食われない
    (平均だと食われる。窓 41 で幅 10 px なら地が 24 % 下がる)。
    """
    bg = median_filter(img, size=(BG_ROWS, 1), mode="nearest")
    return 1.0 - img / np.maximum(bg, 1e-6)


def measure_binary(img: np.ndarray) -> dict:
    """ゼロ点。マスク → 細線化 → 距離変換。**幅は 2·EDT と 2·EDT-1 の 2 通り**。"""
    mask = deficit_map(img) > BIN_LEVEL
    if not mask.any():
        return {"n": 0, "w2": np.zeros(0), "w2m1": np.zeros(0), "mask": mask,
                "skel": mask, "area_px": 0}
    thin = np.asarray(fs.apply(mask.astype(np.float64), "thinning")) > 0.5
    edt = np.asarray(fs.ledger.vol_distance_transform(mask[None, ...]))[0]
    r = edt[thin]
    return {"n": int(thin.sum()), "w2": 2.0 * r * PX_MM,
            "w2m1": np.maximum(2.0 * r - 1.0, 0.0) * PX_MM,
            "mask": mask, "skel": thin, "area_px": int(mask.sum())}


# --------------------------------------------------------------------------- #
# 積分法 —— 直交断面の輝度欠損を積分する                                        #
# --------------------------------------------------------------------------- #
_T = np.arange(-R_PROF, R_PROF + 0.5 * DT_PROF, DT_PROF)
_OUT = np.abs(_T) >= T_BASE


def measure_integral(img: np.ndarray, xs, ys, dys, order: int = 2) -> np.ndarray:
    """各測点で断面を切り、ベースラインを ``order`` 次で当てて欠損を積分 [mm]。

    ``fs.line_profile`` は (row, col) の 2 点を結ぶ線分を双一次で標本化する。
    法線は接線 (1, f') に直交する (-f', 1)/|·| ——(x, y) の順で書くと
    (dx, dy) = (-f', 1)/n、これを (row, col) = (y, x) に読み替える。
    """
    n = np.sqrt(1.0 + dys * dys)
    out = np.empty(len(xs))
    for k, (x0, y0, d) in enumerate(zip(xs, ys, dys)):
        ny, nx = 1.0 / n[k], -d / n[k]            # 単位法線(y, x)
        p0 = (y0 - R_PROF * ny, x0 - R_PROF * nx)
        p1 = (y0 + R_PROF * ny, x0 + R_PROF * nx)
        p = np.asarray(fs.line_profile(img, p0, p1, num=_T.size), np.float64)
        coef = np.polyfit(_T[_OUT], p[_OUT], order)
        base = np.polyval(coef, _T)
        out[k] = np.trapezoid(1.0 - p / np.maximum(base, 1e-6), dx=DT_PROF)
    return out * PX_MM


def sample_points(step: int = 8):
    """測点(視野の縁から R_PROF+2 px 離す)。"""
    xs = np.arange(R_PROF + 2.0, W_PX - R_PROF - 2.0, step)
    ys, dys = path_y(xs)
    return xs, ys, dys


def detect_path(img: np.ndarray):
    """データだけからひび割れの中心線を引く(列ごとに欠損の尾根 + 放物線補間)。"""
    d = gaussian_filter(deficit_map(img), (0.0, 2.0))
    r = np.argmax(d, axis=0)
    r = np.clip(r, 1, H_PX - 2)
    c = d[r, np.arange(W_PX)]
    a, b = d[r - 1, np.arange(W_PX)], d[r + 1, np.arange(W_PX)]
    den = a - 2.0 * c + b
    sub = np.where(np.abs(den) > 1e-9, 0.5 * (a - b) / np.where(den == 0, 1, den), 0.0)
    return r + np.clip(sub, -1.0, 1.0)


# --------------------------------------------------------------------------- #
# 1. 描き手の検算 —— 欠損の総量は幅そのもの                                     #
# --------------------------------------------------------------------------- #
def section_renderer() -> None:
    print("\n" + "=" * 78)
    print("1) 描き手の検算 —— 被覆率の総量 = 幅。PSF を掛けても保存されるか")
    print("=" * 78)
    print("  経路が斜めなので、画素の被覆率の総和は**垂直方向の**幅になる。")
    print("  期待値は w/PX_MM · mean(sqrt(1+f'^2)) = w/PX_MM · %.5f。"
          % float(np.sqrt(1.0 + path_y(np.arange(W_PX, dtype=np.float64))[1] ** 2).mean()))
    print("\n   幅 [mm]  幅 [px]   Σcov/長さ [px]   PSF 後 [px]   期待との差")

    xs, ys, dys = sample_points(step=8)
    for w_mm in (0.05, 0.20, 0.60, 2.00):
        sc = render(lambda x, w=w_mm: np.full_like(np.asarray(x, float), w))
        # 帯の総面積 / 経路長 = 垂直方向の平均幅。垂直→垂直距離の換算に
        # sqrt(1+f'^2) が要るので、そこを割って**垂直幅**に戻す。
        n = np.sqrt(1.0 + sc["dy"] ** 2)
        want = float((sc["width_mm"] / PX_MM * n).mean())
        got = float(sc["cov"].sum() / W_PX)
        got_b = float(sc["cov_blur"].sum() / W_PX)
        print("    %5.2f    %6.3f     %10.5f     %10.5f    %+.2e" % (
            w_mm, w_mm / PX_MM, got, got_b, got_b - want))
        assert abs(got - want) < 2e-3 * max(want, 1.0), (got, want)
        assert abs(got_b - got) < 1e-6 * max(got, 1.0), (got_b, got)

    # 積分法そのものの検算(きれいな場面・照明一様)
    sc = render(lambda x: np.full_like(np.asarray(x, float), 0.60))
    est = measure_integral(sc["img"], xs, ys, dys)
    print("\n  きれいな場面で積分法: 真値 0.600 mm -> 平均 %.4f mm "
          "(偏り %+.3f %%, 散らばり %.1e mm)"
          % (est.mean(), 100 * (est.mean() - 0.6) / 0.6, est.std()))
    assert abs(est.mean() - 0.60) < 0.01, est.mean()


# --------------------------------------------------------------------------- #
# 2-3. 幅の掃引 —— 階段と連続                                                   #
# --------------------------------------------------------------------------- #
WIDTHS_MM = (0.05, 0.075, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25, 0.30, 0.35,
             0.40, 0.50, 0.60, 0.80, 1.00, 1.40, 2.00)
FIG_WMAX = 1.00            # 図はここまで(細い側の階段を見せるため)


def section_width_sweep() -> dict:
    print("\n" + "=" * 78)
    print("2-3) 幅の掃引 —— ゼロ点(2 値化)は階段、積分法は連続")
    print("=" * 78)
    print("  真値 mm   px     2値 2·EDT    2値 2·EDT-1    積分法        積分の散らばり")

    xs, ys, dys = sample_points(step=8)
    rows, true_l, bin_l, int_l, bin2_l = [], [], [], [], []
    for w in WIDTHS_MM:
        sc = render(lambda x, w=w: np.full_like(np.asarray(x, float), w))
        b = measure_binary(sc["img"])
        e = measure_integral(sc["img"], xs, ys, dys)
        w2 = float(np.mean(b["w2"])) if b["n"] else float("nan")
        w2m1 = float(np.mean(b["w2m1"])) if b["n"] else float("nan")
        tag = "" if b["n"] else "   <- マスクが空(何も返さない)"
        print("   %5.3f  %5.2f    %8s    %8s    %8.4f      %.4f%s" % (
            w, w / PX_MM,
            "-" if b["n"] == 0 else "%.3f" % w2,
            "-" if b["n"] == 0 else "%.3f" % w2m1,
            e.mean(), e.std(), tag))
        rows.append([("%.3f" % w), ("%.2f" % (w / PX_MM)),
                     "-" if b["n"] == 0 else "%.3f" % w2,
                     "-" if b["n"] == 0 else "%.3f" % w2m1,
                     "%.4f" % e.mean(), "%+.1f" % (100 * (e.mean() - w) / w)])
        true_l.append(w)
        bin_l.append(0.0 if b["n"] == 0 else w2)
        bin2_l.append(0.0 if b["n"] == 0 else w2m1)
        int_l.append(float(e.mean()))

    dead = [w for w, v in zip(true_l, bin_l) if v == 0.0]
    print("\n  ★ゼロ点が何も返さない範囲: %.3f 〜 %.3f mm(%d 条件、= %.2f px 以下)。"
          % (min(dead), max(dead), len(dead), max(dead) / PX_MM))
    # 同じ値を返してしまう真値の幅を数える(= 階段の踏み面)
    tie, best = {}, None
    for t, v in zip(true_l, bin2_l):
        if v > 0:
            tie.setdefault(round(v, 6), []).append(t)
    for v, ts in tie.items():
        if len(ts) >= 2 and (best is None or max(ts) / min(ts) > best[1]):
            best = (v, max(ts) / min(ts), min(ts), max(ts), len(ts))
    if best:
        print("  ★階段の踏み面: 真値 %.3f 〜 %.3f mm の %d 条件が**すべて同じ "
              "%.3f mm** を返す(真値は %.2f 倍違う)。"
              % (best[2], best[3], best[4], best[0], best[1]))
    print("  ★同じマスクから 2 通りの幅が出て、差は常に 1 px = %.2f mm。" % PX_MM)
    ok = [(t, i) for t, i in zip(true_l, int_l)]
    err = [100 * (i - t) / t for t, i in ok]
    print("  ★積分法の偏りは全幅で %+.2f 〜 %+.2f %%(0.05 mm = 0.25 px を含む)。"
          % (min(err), max(err)))

    m = [i for i, t in enumerate(true_l) if t <= FIG_WMAX]
    pick = (lambda v: [v[i] for i in m])
    figs.save_plot("width_sweep",
                   [("真値(y=x)", pick(true_l), pick(true_l)),
                    ("積分法", pick(true_l), pick(int_l)),
                    ("2 値化 2·EDT", pick(true_l), pick(bin_l)),
                    ("2 値化 2·EDT-1", pick(true_l), pick(bin2_l))],
                   xlabel="真の幅 [mm]", ylabel="推定した幅 [mm]",
                   ylim=(-0.05, 1.55), kinds=["line", "scatter", "line", "line"],
                   title="幅の掃引(きれいな場面)。0 は「何も返さなかった」",
                   caption="2 値化の 2 本は階段。0.20 mm(1 px)以下ではマスクが"
                           "空になり 0(= 未検出)へ落ちる。積分法は 0.05 mm "
                           "(0.25 px)まで直線 y=x に乗る。")
    return {"true": true_l, "bin": bin_l, "bin2": bin2_l, "int": int_l, "rows": rows}


# --------------------------------------------------------------------------- #
# 4. テーパのあるひび割れ —— w(s) を追えるか                                    #
# --------------------------------------------------------------------------- #
def section_taper() -> dict:
    print("\n" + "=" * 78)
    print("4) 幅が変わるひび割れ w(s) —— どこまで形が追えるか")
    print("=" * 78)

    sc = render(width_taper, texture=0.05, slope=0.30, curve=0.0, seed=3)
    xs, ys, dys = sample_points(step=6)
    truth = width_taper(xs)
    est = measure_integral(sc["img"], xs, ys, dys)
    b = measure_binary(sc["img"])

    # 2 値化の幅は骨格画素ごとにしか出ないので、測点の列に最も近い骨格画素を拾う
    sk_r, sk_c = np.nonzero(b["skel"])
    edt = np.asarray(fs.ledger.vol_distance_transform(b["mask"][None, ...]))[0]
    bw = np.full(xs.size, np.nan)
    for k, x0 in enumerate(xs):
        sel = np.abs(sk_c - x0) <= 2
        if sel.any():
            bw[k] = float(np.max(2.0 * edt[sk_r[sel], sk_c[sel]] - 1.0)) * PX_MM
    got = np.isfinite(bw)

    # 経路方向に 5 点(30 px)の移動平均。実務でも「区間の幅」を報告するので
    # これが素の使い方に近い。**偏りが無い推定器は平均すれば散らばりが落ちる**。
    ker = np.ones(5) / 5.0
    est_s = np.convolve(np.pad(est, 2, mode="edge"), ker, mode="valid")

    rms_i = float(np.sqrt(np.mean((est - truth) ** 2)))
    rms_s = float(np.sqrt(np.mean((est_s - truth) ** 2)))
    rms_b = float(np.sqrt(np.mean((bw[got] - truth[got]) ** 2))) if got.any() else np.nan
    rms_ball = float(np.sqrt(np.mean(np.where(got, bw - truth, truth) ** 2)))
    print("  測点 %d 点(6 px 間隔)。真の幅 %.2f 〜 %.2f mm。"
          % (xs.size, truth.min(), truth.max()))
    print("  積分法    : 全点で値が出る。RMS 誤差 %.4f mm(5 点移動平均で %.4f mm)"
          % (rms_i, rms_s))
    print("  2 値化    : %d/%d 点でしか値が出ない(残りはマスクが空)。"
          "出た点だけの RMS 誤差 %.4f mm" % (int(got.sum()), xs.size, rms_b))
    print("\n  ★「出た点だけ」で数えると 2 値化 %.4f mm < 積分法 %.4f mm で、"
          "**2 値化のほうが良く見える**。" % (rms_b, rms_i))
    print("     中身は違う。積分法の誤差は**散らばり**なので 5 点平均すると "
          "%.4f mm まで落ちる(偏りが無いから)。" % rms_s)
    print("     2 値化の未検出は平均しても消えない: 未検出を真値との差として"
          "数え直すと %.4f mm。" % rms_ball)

    thr = 0.20
    below = truth < thr
    print("  ★設計限界 %.2f mm 未満の区間(%d/%d 点)で、2 値化が値を返せたのは"
          " %d 点。" % (thr, int(below.sum()), xs.size, int((got & below).sum())))

    figs.save_grid("scene",
                   [sc["img"], sc["cov"], b["mask"].astype(np.float64)],
                   ["撮った絵(ざらつき 5 %・照明傾斜)", "真の被覆率",
                    "2 値化のマスク(細い側で消えている)"],
                   ncols=1, title="幅が %.2f〜%.2f mm のひび割れ(1 px = %.2f mm)"
                                  % (truth.min(), truth.max(), PX_MM))
    return {"rms_int": rms_i, "rms_smooth": rms_s, "rms_bin": rms_b,
            "rms_bin_all": rms_ball, "n_got": int(got.sum()), "n": int(xs.size),
            "n_below": int(below.sum()), "n_below_got": int((got & below).sum())}


# --------------------------------------------------------------------------- #
# 5. 入れ替わる条件 —— ざらつきと照明の曲がり                                   #
# --------------------------------------------------------------------------- #
def section_crossover() -> dict:
    print("\n" + "=" * 78)
    print("5) どこで入れ替わるか —— ざらつきと、照明の「曲がり」")
    print("=" * 78)

    xs, ys, dys = sample_points(step=8)
    sigmas = (0.0, 0.02, 0.04, 0.07, 0.11, 0.16)
    seeds = (3, 17, 41)
    w_true = 0.60
    print("  幅 0.60 mm 固定。ざらつき σ を振る(3 種の平均)。")
    print("  ★**点ごと**と**経路平均**を分けて出す —— 畳むと『散らばり』と")
    print("    『偏り』が混ざって、直せる誤差と直せない誤差の区別が消える。")
    print("\n   σ      積分 点ごと  積分 平均   2値 点ごと  2値 平均   2値の偏り  未検出")
    int_rms, bin_rms, int_mean_rms, bin_mean_rms = [], [], [], []
    int_bias, bin_bias, miss = [], [], []
    for s in sigmas:
        ei, bi, em, bm, ms = [], [], [], [], []
        for sd in seeds:
            sc = render(lambda x: np.full_like(np.asarray(x, float), w_true),
                        texture=s, slope=0.30, seed=sd)
            e = measure_integral(sc["img"], xs, ys, dys)
            ei.append(e)
            em.append(float(e.mean()))
            b = measure_binary(sc["img"])
            if b["n"]:
                bi.append(np.asarray(b["w2m1"], np.float64))
                bm.append(float(np.mean(b["w2m1"])))
            ms.append(0.0 if b["n"] else 1.0)
        e = np.concatenate(ei)
        bpix = np.concatenate(bi) if bi else np.zeros(0)
        int_rms.append(float(np.sqrt(np.mean((e - w_true) ** 2))))
        int_mean_rms.append(float(np.sqrt(np.mean((np.asarray(em) - w_true) ** 2))))
        int_bias.append(float(e.mean() - w_true))
        bin_rms.append(float(np.sqrt(np.mean((bpix - w_true) ** 2)))
                       if bpix.size else np.nan)
        bin_mean_rms.append(float(np.sqrt(np.mean((np.asarray(bm) - w_true) ** 2)))
                            if bm else np.nan)
        bin_bias.append((float(np.mean(bm)) - w_true) if bm else np.nan)
        miss.append(float(np.mean(ms)))
        print("   %.2f    %8.4f   %8.4f    %8s   %8s   %+8.4f   %.0f %%" % (
            s, int_rms[-1], int_mean_rms[-1],
            "-" if not np.isfinite(bin_rms[-1]) else "%.4f" % bin_rms[-1],
            "-" if not np.isfinite(bin_mean_rms[-1]) else "%.4f" % bin_mean_rms[-1],
            bin_bias[-1], 100 * miss[-1]))

    cross = [s for s, a, b in zip(sigmas, int_rms, bin_rms)
             if np.isfinite(b) and a > b]
    crossm = [s for s, a, b in zip(sigmas, int_mean_rms, bin_mean_rms)
              if np.isfinite(b) and a > b]
    print("\n  ★**点ごと**で見ると σ >= %s で 2 値化が下回る。"
          % ("%.2f" % min(cross) if cross else "(掃引範囲では起きない)"))
    print("     **経路平均**で見ると %s。"
          % ("σ >= %.2f で入れ替わる" % min(crossm) if crossm
             else "この範囲では入れ替わらない(積分法が全域で下)"))
    print("     2 値化が点ごとに散らばらないのは強さではなく、**1 画素の階段に"
          "張り付いている**ため。")
    fb = [v for v in bin_bias if np.isfinite(v)]
    print("     その代わり偏りは消せない(表の『2値の偏り』列 = "
          "%+.4f 〜 %+.4f mm、平均しても残る)。" % (min(fb), max(fb)))

    # --- 照明の曲がり: ベースラインの次数が効く -------------------------------
    print("\n  照明の「曲がり」に対する感度(ざらつき無し・幅 0.60 mm)")
    print("   曲がり   1 次ベースライン      2 次ベースライン")
    curves = (0.0, 0.05, 0.10, 0.20)
    e1_l, e2_l = [], []
    for c in curves:
        sc = render(lambda x: np.full_like(np.asarray(x, float), w_true),
                    texture=0.0, slope=0.30, curve=c)
        e1 = measure_integral(sc["img"], xs, ys, dys, order=1).mean() - w_true
        e2 = measure_integral(sc["img"], xs, ys, dys, order=2).mean() - w_true
        e1_l.append(float(e1))
        e2_l.append(float(e2))
        print("    %.2f    %+8.4f mm         %+8.4f mm" % (c, e1, e2))
    print("\n  ★予想は「積分法は照明の傾斜に弱い」だったが、**傾斜(1 次)は"
          "1 次のベースラインで完全に抜ける**(曲がり 0 の行)。")
    print("     効くのは曲がりのほうで、1 次だと %+.4f mm、2 次だと %+.4f mm"
          "(曲がり %.2f)。予想は半分外れ。" % (e1_l[-1], e2_l[-1], curves[-1]))

    figs.save_plot("crossover",
                   [("積分法 点ごと RMS", sigmas, int_rms),
                    ("積分法 経路平均 RMS", sigmas, int_mean_rms),
                    ("2 値化 点ごと RMS", sigmas,
                     [b if np.isfinite(b) else 0.0 for b in bin_rms]),
                    ("2 値化 経路平均 RMS", sigmas,
                     [b if np.isfinite(b) else 0.0 for b in bin_mean_rms])],
                   xlabel="ざらつき σ", ylabel="幅の誤差 RMS [mm]",
                   ylim=(-0.02, 0.92),
                   title="ざらつきに対する壊れ方(幅 0.60 mm)",
                   caption="点ごとでは 2 値化が下に見えるが、経路平均に直すと"
                           "積分法の散らばりは消え、2 値化の偏りは残る。"
                           "同じ場面・同じ画像から出した 4 本。")
    return {"sigmas": sigmas, "int_rms": int_rms, "bin_rms": bin_rms,
            "int_mean_rms": int_mean_rms, "bin_mean_rms": bin_mean_rms,
            "bin_bias": bin_bias, "curves": curves, "e1": e1_l, "e2": e2_l}


# --------------------------------------------------------------------------- #
# 6. 最大幅 vs 平均幅 —— 標本最大値の過大量は閉形式で予測できる                  #
# --------------------------------------------------------------------------- #
def _expected_max(n: int) -> float:
    """N 個の標準正規標本の期待最大値(Cramer の漸近展開)。"""
    if n < 2:
        return 0.0
    a = np.sqrt(2.0 * np.log(n))
    return float(a - (np.log(np.log(n)) + np.log(4.0 * np.pi)) / (2.0 * a)
                 + 0.5772156649 / a)


def section_max_vs_mean() -> dict:
    print("\n" + "=" * 78)
    print("6) 最大幅は必ず過大になる —— 過大量は sqrt(2 ln N) で予測できる")
    print("=" * 78)

    w_true = 0.60
    xs, ys, dys = sample_points(step=6)
    seeds = tuple(range(101, 121))
    allw = []
    for sd in seeds:
        sc = render(lambda x: np.full_like(np.asarray(x, float), w_true),
                    texture=0.07, slope=0.30, seed=sd)
        allw.append(measure_integral(sc["img"], xs, ys, dys))
    allw = np.asarray(allw)                       # (seeds, points)
    sigma = float(allw.std(axis=1).mean())
    print("  幅 0.60 mm・ざらつき σ=0.07・測点 %d 点 x %d 種。"
          % (allw.shape[1], allw.shape[0]))
    print("  点ごとの推定の散らばり σ_w = %.4f mm(偏り %+.4f mm)"
          % (sigma, float(allw.mean() - w_true)))
    print("\n   測点 N   平均の幅      最大の幅     過大量(実測)   予測 σ_w·a_N   比")
    rows, ns, meas, pred = [], [], [], []
    for n in (4, 8, 16, 32, 64, allw.shape[1]):
        stride = max(1, allw.shape[1] // n)
        sub = allw[:, ::stride][:, :n]
        mn = float(sub.mean())
        mx = float(sub.max(axis=1).mean())
        p = sigma * _expected_max(n)
        rows.append([str(n), "%.4f" % mn, "%.4f" % mx, "%+.4f" % (mx - mn),
                     "%.4f" % p, "%.2f" % ((mx - mn) / p if p else np.nan)])
        ns.append(n)
        meas.append(mx - mn)
        pred.append(p)
        print("     %3d    %.4f mm   %.4f mm    %+.4f mm     %.4f mm     %.2f"
              % (n, mn, mx, mx - mn, p, (mx - mn) / p if p else np.nan))

    # 予測が一貫して上振れする理由を測る: 隣り合う測点は独立でない。
    # 断面の半長は測点の間隔より大きいので、窓が重なって相関が残る。
    z = (allw - allw.mean(axis=1, keepdims=True))
    r1 = float(np.mean(np.sum(z[:, :-1] * z[:, 1:], axis=1)
                       / np.sum(z * z, axis=1)))
    n_eff = allw.shape[1] * (1.0 - r1) / (1.0 + r1)

    print("\n  ★測点を %d 点から %d 点へ増やすと、報告する「最大幅」は "
          "%.4f -> %.4f mm(%+.1f %%)。" % (
              ns[0], ns[-1], w_true + meas[0], w_true + meas[-1],
              100 * (meas[-1] - meas[0]) / w_true))
    print("     真の幅は 1 μm も変わっていない。**密に測るほど不合格に近づく**。")
    ratio = [m / p for m, p in zip(meas, pred) if p]
    print("  ★過大量は sqrt(2 ln N) の漸近式と比 %.2f 〜 %.2f で一致する —— "
          "**一貫して 1 を下回る**。" % (min(ratio), max(ratio)))
    print("     理由は測ってある: 隣り合う測点は独立でない(1 次の自己相関 "
          "%.2f、有効な独立点数 %.0f / %d)。"
          % (r1, n_eff, allw.shape[1]))
    print("     断面の半長 %.0f px に対して測点の間隔が 6 px なので窓が重なる。"
          "iid を仮定した予測は**上振れ側の安全な見積り**になる。" % R_PROF)
    print("  ★規格が「最大幅」で書かれている以上、**測点密度を書かない報告は"
          "比較できない**。")

    figs.save_table("max_vs_mean",
                    ["測点 N", "平均 mm", "最大 mm", "過大量 mm", "予測 mm", "比"],
                    rows, title="最大幅の過大量と、標本最大値の理論値",
                    caption="真の幅は 0.60 mm 固定。N は同じ場面を何点で測るか。")
    return {"sigma": sigma, "n": ns, "meas": meas, "pred": pred}


# --------------------------------------------------------------------------- #
# 7. 検出は測定と別 —— データから経路を引けるか                                 #
# --------------------------------------------------------------------------- #
def section_detection() -> dict:
    print("\n" + "=" * 78)
    print("7) 検出と測定を分ける —— データから引いた経路で測り直す")
    print("=" * 78)
    print("  (2〜6 節は経路に真値を渡している。ここだけデータから引く)")
    print("   幅 mm   σ     経路の誤差 [px]   外れた列   幅の誤差(真)  幅の誤差(引いた)")

    xs, ys, dys = sample_points(step=8)
    idx = xs.astype(int)
    rows, tbl = [], []
    for w, s in ((0.10, 0.05), (0.10, 0.10), (0.10, 0.16),
                 (0.30, 0.05), (0.30, 0.16), (0.80, 0.16)):
        sc = render(lambda x, w=w: np.full_like(np.asarray(x, float), w),
                    texture=s, slope=0.30, seed=9)
        rr = detect_path(sc["img"])
        dev = rr[idx] - ys
        perr = float(np.sqrt(np.mean(dev ** 2)))
        lost = int(np.count_nonzero(np.abs(dev) > 2.0))
        e_true = float(measure_integral(sc["img"], xs, ys, dys).mean() - w)
        rs = gaussian_filter(rr, 12.0)                # 傾きは平滑化してから差分
        d = np.gradient(rs)[idx]
        e_det = float(measure_integral(sc["img"], xs, rr[idx], d).mean() - w)
        rows.append((w, s, perr, lost, e_true, e_det))
        print("   %.2f   %.2f      %8.3f       %3d/%3d      %+7.4f mm    %+7.4f mm"
              % (w, s, perr, lost, xs.size, e_true, e_det))
        tbl.append(["%.2f" % w, "%.2f" % s, "%.3f" % perr,
                    "%d/%d" % (lost, xs.size), "%+.4f" % e_true, "%+.4f" % e_det])

    easy = [r for r in rows if r[3] == 0]
    hard = [r for r in rows if r[3] > 0]
    print("\n  ★予想は「細い側ほど経路が引けない」だったが、**幅より"
          "ざらつきのほうがはるかに効いた**。")
    if easy:
        print("     経路が 1 列も外れない条件では、真の経路との幅の差は "
              "最大 %.4f mm(= 経路は測定の律速ではない)。"
              % max(abs(r[5] - r[4]) for r in easy))
    if hard:
        print("     外れる条件(%d 件)では、外れた列で断面が別の場所を切るので"
              "幅は %+.4f mm ずれる。"
              % (len(hard), max((r[5] - r[4]) for r in hard)))
    else:
        print("     この掃引の範囲では、列ごとの尾根追跡は一度も外れなかった"
              "(σ=0.16 の幅 0.10 mm でも)。**検出は思ったより易しい** —— "
              "難しいのは幅のほう。")
    return {"rows": rows, "tbl": tbl}


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)

    m = np.zeros((40, 60))
    m[15:25, 10:50] = 1.0

    # (a) 2-D の距離変換は**最大値で正規化される**ので画素単位の距離が取れない。
    dn = np.asarray(fs.apply(m, "distance_transform"))
    assert abs(float(dn.max()) - 1.0) < 1e-9, float(dn.max())
    # 逃げ道: 3-D の距離変換に (1,H,W) を渡すと**画素単位のまま**返る。
    d3 = np.asarray(fs.ledger.vol_distance_transform(m[None, ...] > 0.5))[0]
    assert abs(float(d3.max()) - 5.0) < 1e-9, float(d3.max())
    print("  (a) 進化 op の distance_transform は最大値で正規化する(最大 %.1f)。"
          % dn.max())
    print("      画素単位が要るときは **3-D の vol_distance_transform に "
          "(1,H,W) を渡す**と通る(最大 %.1f = 正しい)。2-D の公開経路が"
          "無いのが穴。" % d3.max())

    # (b) 細線化は 3 つ在るが、どれも**幅を返さない**(距離変換と組む前提)。
    for nm in ("thinning", "skeleton", "sk_medial"):
        assert any(o.name == nm for o in __import__("ops").REGISTRY), nm
    assert not hasattr(fs, "medial_axis_width") and not hasattr(fs.ledger, "ridge_width")
    print("  (b) 細線化は thinning / skeleton / sk_medial の 3 通り在るが、"
          "**骨格に沿った幅(局所半径)を返す口が無い**。2-D の medial axis "
          "transform(距離つき骨格)が欲しい。")

    # (c) 直交断面を**まとめて**切る口が無い。1 点ずつ line_profile を呼んでいる。
    assert hasattr(fs, "line_profile")
    assert not hasattr(fs, "line_profiles") and not hasattr(fs.ledger, "normal_profiles")
    print("  (c) fs.line_profile は 1 本ずつ。中心線に沿って**法線断面を"
          "まとめて切る**口(いわゆる straightening / ribbon 展開)が無い。"
          "この PoC は自前で %d 本回している。" % len(_T))

    # (d) 断面のベースライン当てはめ(外側だけで多項式)を持つ op が無い。
    assert not hasattr(fs, "profile_baseline") and not hasattr(fs.ledger, "profile_baseline")
    print("  (d) 1-D 断面の**ベースライン除去**(外側だけで多項式を当てる)が"
          "無い。分光にもクロマトにも共通する形なので族に入る価値がある —— "
          "しかも 5 節のとおり**次数の選択が結論を変える**。")

    # (e) 標本最大値の期待値(極値統計)が無い。規格が最大値で書かれる分野では要る。
    assert not hasattr(fs, "expected_max") and not hasattr(fs.ledger, "gumbel_expected_max")
    print("  (e) 極値統計(標本最大値の期待値・Gumbel 当てはめ)が無い。"
          "「最大幅」で合否を決める分野では、測点密度の補正にこれが要る。")

    # (f) ざらつきの相関長を測る口が無い(この PoC は与えた値を知っているだけ)。
    assert not hasattr(fs, "autocorrelation_length")
    print("  (f) 面のざらつきの**相関長**を測る口が無い。積分法の散らばりは "
          "σ·sqrt(2R·l) で決まるので、実写では l を測らないと不確かさが出せない。")


# --------------------------------------------------------------------------- #
# 8. 実写 —— 公開のひび割れ写真を、粗い画素で撮り直す                           #
# --------------------------------------------------------------------------- #
#: 実写データ: Özgenel, "Concrete Crack Images for Classification", Mendeley Data v2,
#: DOI 10.17632/5y9wdsg2zt.2、ライセンス "CC BY 4.0"(配布元の表記)。227x227 px の RGB、
#: ひび割れ有り 20,000 枚。取得は ``tools/fetch_realinsp_data.py concrete_crack``(repo には入れない)。
REAL_DATASET = "concrete_crack_ozgenel"
REAL_CREDIT = ("Özgenel, Concrete Crack Images for Classification, Mendeley Data v2, "
               "DOI 10.17632/5y9wdsg2zt.2, CC BY 4.0")
REAL_STRIDE = 100          # Positive の名前順で 100 枚おきに 200 枚を見る(決定的)
REAL_BINS = (1, 2, 3, 4)   # 画素を k x k でまとめる = 同じひびを k 倍粗い画素で撮り直す
#: 代表の図に出す 1 枚。芯が暗く(欠損 > 0.65)、元の画素で 2 つの手法が 10 % 以内で一致する
#: 写真から選んだ(芯が灰色の写真では積分法の値が「幅 x 深さ」になり、見た目の幅と合わない)。
REAL_SHOW = "12701_1.jpg"

#: 実データで出た数値(2026-11-08、Python 3.11。下の section_real の stdout から転記)。
#: データが無い環境(CI)ではこれを印字する。
RECORDED_REAL = {'n_seen': 200, 'n_path': 199, 'n_used': 159, 'int_ratio_kmax': 1.134,
                 'bin_ratio_kmax': 1.442, 'bin_empty_kmax': 0.069, 'native_int_px': 4.98,
                 'native_bin_px': 2.62, 'core_deficit': 0.539, 'int_q_kmax': [0.97, 1.44],
                 'bin_q_kmax': [1.22, 1.78], 'int_ratio_k3': 1.091, 'bin_ratio_k3': 1.119,
                 'lag_ratio_1': 0.45, 'lag_ratio_100': 0.9, 'fwhm_px': 11.75, 'int_depth_over_fwhm': 0.75,
                 'int_depth_over_fwhm_q': [0.6, 0.85], 'bin_over_fwhm': 0.24, 'bin_under_half_fwhm': 0.84,
                 'ratio_base1': 0.84, 'ratio_onpath': 0.82, 'offpath_frac': 0.18, 'rim_bright_side': 0.017,
                 'clip_rise_real': 0.21, 'clip_rise_syn': [0.35, 0.57], 'syn_ratio_noise': [1.05, 1.12, 0.96],
                 'ratio_median': 0.82, 'ratio_combo': 0.88, 'offpath_frac_run': 0.09, 'ratio_onpath_run': 0.82,
                 'ratio_combo_run': 0.87}


def real_data_root() -> Path:
    """公開実データの置き場の根。

    ``FULLSEYE_POC_REAL_DATA`` があればそれ、無ければ開発の作業木(``<root>/projects/<checkout>``)
    の隣の ``<root>/data/fullseye_poc_real``、それ以外はユーザーキャッシュ。手元の絶対パスを
    ソースに書かないための分岐。
    """
    configured = os.environ.get("FULLSEYE_POC_REAL_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    root = Path(__file__).resolve().parents[1]
    if root.parent.name.lower() == "projects":
        return root.parent.parent / "data" / "fullseye_poc_real"
    return Path.home() / ".cache" / "fullseye" / "poc_real"


def _real_files():
    """採る写真の一覧。CI(置き場の指定なし)やデータが無いときは ``None``。"""
    if os.environ.get("CI") and not os.environ.get("FULLSEYE_POC_REAL_DATA"):
        return None
    pos = real_data_root() / REAL_DATASET / "extracted" / "Positive"
    if not pos.is_dir():
        return None
    files = sorted(pos.glob("*.jpg"))
    if len(files) != 20000:
        raise RuntimeError("ひび割れ有りの写真が %d 枚(配布物は 20,000 枚): %s" % (len(files), pos))
    return files[::REAL_STRIDE]


def _bin(a: np.ndarray, k: int) -> np.ndarray:
    """k x k の画素をまとめる(開口率 100 % の k 倍粗いセンサで撮ったのと同じ)。"""
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    return a[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))


def _deficit_real(a: np.ndarray, rows: int) -> np.ndarray:
    """:func:`deficit_map` と同じ式。窓の行数だけ画素の粗さに合わせて渡す。"""
    bg = median_filter(a, size=(rows, 1), mode="nearest")
    return 1.0 - a / np.maximum(bg, 1e-6)


def _real_path(a: np.ndarray, rows: int):
    """列ごとの欠損の尾根(最暗)→ 中央値で外れを抑え、ガウスで滑らかにした経路と傾き。

    ひびの中心線ではない: 幅のあるひびでは片側の縁に寄り、地や別のひびへ飛ぶ列もある
    (:func:`_ratio_factors` で断面の最大が経路から外れた割合を数える)。
    """
    d = gaussian_filter(_deficit_real(a, rows), (0.0, 1.0))
    arg = np.argmax(d, axis=0)
    peak = d[arg, np.arange(a.shape[1])]
    y = gaussian_filter(median_filter(arg.astype(np.float64), size=9, mode="nearest"), 1.5)
    return np.arange(a.shape[1], dtype=np.float64), y, np.gradient(y), peak


def _real_integral(a, xs, ys, dys, R):
    """直交断面の欠損の積分(2 次のベースライン)[px]。:func:`measure_integral` と同じ式で、
    断面の半長だけ画素の粗さに合わせて渡す。"""
    t = np.arange(-R, R + 0.125, 0.25)
    outer = np.abs(t) >= 0.6 * R
    w = np.empty(len(xs))
    pk = np.empty(len(xs))
    fw = np.empty(len(xs))
    for k, (x0, y0, d) in enumerate(zip(xs, ys, dys)):
        n = np.sqrt(1.0 + d * d)
        ny, nx = 1.0 / n, -d / n
        p = np.asarray(fs.line_profile(a, (y0 - R * ny, x0 - R * nx),
                                       (y0 + R * ny, x0 + R * nx), num=t.size), np.float64)
        base = np.polyval(np.polyfit(t[outer], p[outer], 2), t)
        df = 1.0 - p / np.maximum(base, 1e-6)
        w[k] = np.trapezoid(df, dx=0.25)
        pk[k] = float(df.max())
        fw[k] = float(np.count_nonzero(df >= 0.5 * pk[k])) * 0.25   # 断面の半値幅(その断面の芯の半分)
    _real_integral.last = (pk, fw)
    return w


#: 断面の最大がこれより経路から離れていたら「経路が外れた断面」と数える [px]。
OFFPATH_PX = 3.0


def _ratio_factors(a: np.ndarray, R: float = 24.0) -> np.ndarray:
    """「積分 ÷ 芯の欠損 ÷ 半値幅」が 1 を下回る原因を、要因を 1 つずつ振って測る(元の画素、k=1)。

    経路・測点・断面は :func:`_measure_real` の k=1 と同じ。返す列:
    0 そのまま(2 次のベースライン。:func:`_real_integral` と同じ式なので比の検算になる)/
    1 ベースラインを 1 次に / 2 断面の最大が経路から :data:`OFFPATH_PX` 以内の断面だけ /
    3 芯の帯(|t| < 0.6R)の負の欠損を 0 で切る / 4 外側の残差の標準偏差(雑音の大きさ)/
    5 経路が外れた断面の割合 / 6 経路の両側の帯の生の輝度(当てはめ無し)の、明るい側の地に対する比 − 1 /
    7 1 枚の中の積分を平均でなく中央値でまとめる / 8 組み合わせ(中央値 + 1 次 + 経路から 3 px 以内)/
    9 「経路が外れた」を「経路が断面の半値幅の連続区間の外」で数えた割合(幅の広いひびで 3 px が厳しすぎないかの確かめ)/
    10 その判定で経路上の断面だけの平均 / 11 その判定での組み合わせ(中央値 + 1 次 + 経路上)。
    """
    x, y, dy, _ = _real_path(a, 41)
    h, w = a.shape
    sel = (x > R + 1) & (x < w - R - 1) & (y > R) & (y < h - R)
    t = np.arange(-R, R + 0.125, 0.25)
    outer = np.abs(t) >= 0.6 * R
    rows = []
    for x0, y0, d in zip(x[sel][::4], y[sel][::4], dy[sel][::4]):
        n = np.sqrt(1.0 + d * d)
        ny, nx = 1.0 / n, -d / n
        p = np.asarray(fs.line_profile(a, (y0 - R * ny, x0 - R * nx),
                                       (y0 + R * ny, x0 + R * nx), num=t.size), np.float64)
        out = []
        for order in (2, 1):
            df = 1.0 - p / np.maximum(np.polyval(np.polyfit(t[outer], p[outer], order), t), 1e-6)
            i = int(np.argmax(df))
            out += [np.trapezoid(df, dx=0.25), float(df[i]), float(np.count_nonzero(df >= 0.5 * df[i])) * 0.25]
        df2 = 1.0 - p / np.maximum(np.polyval(np.polyfit(t[outer], p[outer], 2), t), 1e-6)
        i2 = int(np.argmax(df2))
        clip = np.trapezoid(np.where(outer, df2, np.maximum(df2, 0.0)), dx=0.25)
        g = float(np.median(p[outer]))
        hw = 0.5 * out[2] + 0.25
        dist = t - t[i2]
        sides = [float(np.median(p[m])) / g - 1.0 for m in
                 ((dist < -hw) & (dist >= -3 * hw) & ~outer, (dist > hw) & (dist <= 3 * hw) & ~outer) if m.sum() >= 2]
        lo, hi = i2, i2
        while lo > 0 and df2[lo - 1] >= 0.5 * df2[i2]:
            lo -= 1
        while hi < df2.size - 1 and df2[hi + 1] >= 0.5 * df2[i2]:
            hi += 1
        in_run = float(t[lo] <= 0.0 <= t[hi])
        rows.append(out + [clip, float(df2[outer].std()), abs(float(t[i2])), max(sides) if sides else np.nan, in_run])
    r = np.asarray(rows)
    on = r[:, 8] <= OFFPATH_PX
    on_run = r[:, 10] > 0.5

    def ratio(i_int, i_pk, i_fw, m=None, agg=np.mean):
        m = np.ones(len(r), bool) if m is None else m
        if m.sum() < 3:
            return np.nan
        return float(agg(r[m, i_int]) / np.median(r[m, i_pk]) / np.median(r[m, i_fw]))
    return np.array([ratio(0, 1, 2), ratio(3, 4, 5), ratio(0, 1, 2, on), ratio(6, 1, 2),
                     float(np.median(r[:, 7])), float(1.0 - on.mean()), float(np.nanmedian(r[:, 9])),
                     ratio(0, 1, 2, agg=np.median), ratio(3, 4, 5, on, np.median),
                     float(1.0 - on_run.mean()), ratio(0, 1, 2, on_run), ratio(3, 4, 5, on_run, np.median)])


def _real_binary(a, rows, xs, ys):
    """ゼロ点(:func:`measure_binary` と同じ: 欠損 > 0.5 → 細線化 → 2·EDT)。

    測点の列で、中心線から ±6 px にある骨格画素の 2·EDT を読む(骨格のひげで値を薄めない)。
    """
    mask = _deficit_real(a, rows) > BIN_LEVEL
    if not mask.any():
        return np.zeros(len(xs)), mask
    thin = np.asarray(fs.apply(mask.astype(np.float64), "thinning")) > 0.5
    edt = np.asarray(fs.ledger.vol_distance_transform(mask[None, ...]))[0]
    out = np.zeros(len(xs))
    for i, (x0, y0) in enumerate(zip(xs, ys)):
        c, r0 = int(round(x0)), int(round(y0))
        lo, hi = max(0, r0 - 6), min(a.shape[0], r0 + 7)
        v = edt[lo:hi, c] * thin[lo:hi, c]
        out[i] = 2.0 * float(v.max()) if v.size else 0.0
    return out, mask


def _measure_real(a: np.ndarray, k: int) -> dict:
    """1 枚を k 倍粗くして、積分法と 2 値化の平均幅を**元の画素**の単位で返す。"""
    b = _bin(a, k)
    rows = max(9, int(41 / k) | 1)
    R = max(5.0, 24.0 / k)
    x, y, dy, peak = _real_path(b, rows)
    h, w = b.shape
    sel = (x > R + 1) & (x < w - R - 1) & (y > R) & (y < h - R)
    step = max(1, 4 // k)
    xs, ys, dys = x[sel][::step], y[sel][::step], dy[sel][::step]
    if xs.size < 3:
        return {"ok": False}
    wi = _real_integral(b, xs, ys, dys, R)
    pk, fw = _real_integral.last
    wb, mask = _real_binary(b, rows, xs, ys)
    return {"ok": True, "int": float(np.mean(wi)) * k, "bin": float(np.mean(wb)) * k,
            "peak": float(np.median(peak[sel])), "mask": mask, "b": b,
            "prof_peak": float(np.median(pk)), "fwhm": float(np.median(fw)) * k,
            "path": (x, y)}


#: docstring の 8 番の項に**文脈ごと**載っていなければならない記録値(鍵 → 書式)。短い数字の
#: 部分一致では別の文脈の同じ数でも通るので、前後の語まで含めて照合する。
RECORDED_IN_DOC = {"int_ratio_kmax": "積分法 %.2f 倍", "bin_ratio_kmax": "2 値化 %.2f 倍",
                   "core_deficit": "欠損 %.2f", "int_depth_over_fwhm": "半値幅の %.2f 倍",
                   "bin_over_fwhm": "2 値化は半値幅の %.2f 倍",
                   "ratio_base1": "ベースラインを 1 次にして %.2f", "ratio_onpath": "を除いて %.2f",
                   "ratio_median": "積分も中央値でまとめると %.2f", "ratio_combo": "組み合わせても %.2f"}


def _recorded_gate(measured) -> None:
    """記録値の門。「記録値の辞書が空でない」は定数なので常に真 —— 代わりに中身を見る。

    データが無いとき: 必要な鍵が全部あり有限の数で、見出しの値が docstring に同じ書式で載っている。
    データがあるとき: 実測を同じ丸めで出して記録値と一致する(記録は実行ログからの転記)。
    """
    need = {"n_seen", "n_path", "n_used", "int_ratio_kmax", "bin_ratio_kmax", "bin_empty_kmax",
            "native_int_px", "native_bin_px", "core_deficit", "int_q_kmax", "bin_q_kmax",
            "int_ratio_k3", "bin_ratio_k3", "lag_ratio_100", "lag_ratio_1",
            "fwhm_px", "int_depth_over_fwhm", "int_depth_over_fwhm_q", "bin_over_fwhm", "bin_under_half_fwhm",
            "ratio_base1", "ratio_onpath", "offpath_frac", "rim_bright_side", "clip_rise_real", "clip_rise_syn",
            "syn_ratio_noise", "ratio_median", "ratio_combo", "offpath_frac_run", "ratio_onpath_run",
            "ratio_combo_run"}
    missing = need - set(RECORDED_REAL)
    assert not missing, "記録値の鍵が足りない: %s" % sorted(missing)
    for k, v in RECORDED_REAL.items():
        for x in (v if isinstance(v, (list, tuple)) else [v]):
            assert np.isfinite(float(x)), (k, v)
    for k, fmt in RECORDED_IN_DOC.items():
        txt = fmt % RECORDED_REAL[k]
        assert txt in (__doc__ or ""), "docstring に記録値 %s の文「%s」が無い" % (k, txt)
    if measured is not None:
        diff = {k: (measured[k], RECORDED_REAL[k]) for k in need if measured[k] != RECORDED_REAL[k]}
        assert not diff, "実測と記録値が違う(記録を実行ログから転記し直す): %s" % diff


def _lag_similarity(files) -> dict:
    """番号の近い写真ほど似ているか(同じ元写真からの切り出しか)の目安。

    配布元の記述では 2 万枚は 458 枚の元写真からの切り出しで、どの切り出しがどの元写真かは
    配布物に無い。そこで色と明るさの平均・標準偏差(6 次元)の差を、番号の差 1 / 100 / 1000 で比べる。
    """
    from PIL import Image
    pos = files[0].parent
    allf = sorted(pos.glob("*.jpg"))
    where = {p.name: i for i, p in enumerate(allf)}

    def feat(i):
        a = np.asarray(Image.open(allf[i]).convert("RGB"), np.float64)
        return np.r_[a.mean((0, 1)), a.std((0, 1))]
    d = {1: [], 100: [], 1000: []}
    for p in files:
        i = where[p.name]
        f0 = feat(i)
        for lag in d:
            if i + lag < len(allf):
                d[lag].append(float(np.abs(f0 - feat(i + lag)).mean()))
    med = {k: float(np.median(v)) for k, v in d.items()}
    return {"lag1": med[1] / med[1000], "lag100": med[100] / med[1000]}


def section_real():
    print("\n" + "=" * 78)
    print("8) 実写 —— 公開のひび割れ写真を、k 倍粗い画素で撮り直す")
    print("=" * 78)
    files = _real_files()
    if files is None:
        print("  実データが無いので実データの章を飛ばす。取得は "
              "py -3.11 tools/fetch_realinsp_data.py concrete_crack")
        print("  記録値(RECORDED_REAL): %s" % RECORDED_REAL)
        _recorded_gate(None)
        return None
    from PIL import Image
    import realdata
    print("  データ: %s" % REAL_CREDIT)
    print("  真値の幅は付いていない。代わりに**同じひびは、粗い画素で撮っても幅が変わらない**")
    print("  ことを外の真値に使う(k x k の画素平均 = 開口率 100 % の粗いセンサ)。")
    print("  基準は k=1(元の画素)の各手法自身の値 —— 手法どうしの比較ではなく自己整合を見る。")
    # 道具の検算: 同じ測り方を合成のひび(芯が黒、幅 0.3〜1.0 mm)に掛ける。ざらつき無しなら
    # 粗くしても積分法は保存される(道具は正しい)。ざらつき 5 % を足すと細いひびから崩れる。
    syn = {}
    for tex in (0.0, 0.05):
        dev = []
        for wmm in (0.3, 0.6, 1.0):
            sc = render(lambda x, w=wmm: np.full_like(np.asarray(x, np.float64), w), texture=tex)
            per = [_measure_real(sc["img"][:224, :224], k) for k in REAL_BINS]
            dev.append(max(abs(m["int"] / per[0]["int"] - 1.0) for m in per))
        syn[tex] = dev
    print("  道具の検算(合成、芯が黒、幅 0.3/0.6/1.0 mm): 粗くしたときの積分法のずれの最大")
    print("    ざらつき無し %s %% / ざらつき 5 %% %s %%"
          % ("/".join("%.1f" % (100 * v) for v in syn[0.0]),
             "/".join("%.1f" % (100 * v) for v in syn[0.05])))
    assert max(syn[0.0]) < 0.02, syn
    res = []
    for p in files:
        a = np.asarray(Image.open(p).convert("L"), np.float64) / 255.0
        ys_, xs_ = np.nonzero(_deficit_real(a, 41) > 0.25)
        if xs_.size < 20:
            continue
        if np.ptp(ys_) > np.ptp(xs_):           # 縦向きは転置して横向きにそろえる
            a = a.T
        per = [_measure_real(a, k) for k in REAL_BINS]
        if not all(m["ok"] for m in per):
            continue
        res.append((p.name, per))
    realdata.mark_read("mendeley:5y9wdsg2zt/Concrete-Crack-Images")
    # 採否は k=1 だけで決める(粗くした後の結果で選ばない)
    good = [(n, per) for n, per in res
            if 1.0 <= per[0]["int"] <= 14.0 and per[0]["bin"] > 0.0]
    print("\n  見た写真 %d 枚 / 経路が引けた %d 枚 / 採った %d 枚(k=1 で両手法が値を返し、"
          "積分 1〜14 px)" % (len(files), len(res), len(good)))
    lag = _lag_similarity(files)
    print("  独立性の目安: 2 万枚は 458 枚の元写真からの切り出し(配布元の記述)で、対応は配布物に無い。")
    print("    色と明るさの差を番号の差 1000 を 1 として測ると、番号の差 1 は %.2f、差 100 は %.2f。"
          % (lag["lag1"], lag["lag100"]))
    print("    100 おきに選んだ写真どうしは、遠く離れた写真と同じくらい違う —— 同じ元写真からの切り出しが")
    print("    重なっている可能性は低いが、確かめきれてはいない(%d 枚を独立な %d 本とは言い切らない)。"
          % (len(good), len(good)))
    print("\n   k    積分法 k/1 の中央値(四分位)     2 値化 k/1 の中央値(四分位)     2値が空")
    rows_out = []
    for i, k in enumerate(REAL_BINS):
        ri = np.array([per[i]["int"] / per[0]["int"] for _, per in good])
        rb = np.array([per[i]["bin"] / per[0]["bin"] for _, per in good])
        z = float(np.mean([per[i]["bin"] == 0.0 for _, per in good]))
        q_i, q_b = np.percentile(ri, [25, 75]), np.percentile(rb, [25, 75])
        rows_out.append({"k": k, "int_med": float(np.median(ri)), "int_q": q_i.tolist(),
                         "bin_med": float(np.median(rb)), "bin_q": q_b.tolist(), "bin_empty": z})
        print("   %d    %.3f(%.3f〜%.3f)            %.3f(%.3f〜%.3f)            %.2f"
              % (k, np.median(ri), q_i[0], q_i[1], np.median(rb), q_b[0], q_b[1], z))
    nat_i = np.array([per[0]["int"] for _, per in good])
    nat_b = np.array([per[0]["bin"] for _, per in good])
    peak = np.array([per[0]["peak"] for _, per in good])
    print("\n  元の画素での値: 積分法の中央値 %.2f px、2 値化 %.2f px、ひびの芯の欠損の中央値 %.2f"
          % (np.median(nat_i), np.median(nat_b), np.median(peak)))
    # --- 元の画素の値は見た目の幅と合っているか(比の自己整合だけでは経路の取り違えを見つけられない) ---
    fwhm = np.array([per[0]["fwhm"] for _, per in good])
    ppk = np.array([per[0]["prof_peak"] for _, per in good])
    r_int = nat_i / ppk / fwhm
    r_bin = nat_b / fwhm
    q_r = np.percentile(r_int, [25, 75])
    print("\n  元の画素の値の妥当性: 見た目の幅 = 断面の半値幅(その断面の芯の欠損の半分を超える幅)は"
          " 中央値 %.2f px。" % np.median(fwhm))
    print("    積分 ÷ 断面の芯の欠損 は半値幅の %.2f 倍(四分位 %.2f〜%.2f)—— 積分は「幅 x 深さ」で、深さで割ると"
          % (np.median(r_int), q_r[0], q_r[1]))
    print("    見た目の幅に近づく。")
    # --- 1 を下回る原因の切り分け: 要因を 1 つずつ振る(同じ写真・同じ経路と測点、元の画素) ---
    # 矩形・三角・ガウスの断面ではこの比は 1.00〜1.06 で、裾が細っても 1 を下回らない。
    fac = np.array([_ratio_factors(per[0]["b"]) for _, per in good])
    assert np.allclose(fac[:, 0], r_int, rtol=1e-9, atol=0.0), "要因の切り分けが本文の比を再現しない"
    fm = np.nanmedian(fac, axis=0)
    syn_f = {}
    for tex in (0.0, 0.10, 0.15):
        v = [_ratio_factors(render(lambda x: np.full_like(np.asarray(x, np.float64), 0.6), texture=tex,
                                   seed=SEED + s)["img"][:224, :224]) for s in (1, 2, 3)]
        syn_f[tex] = np.median(np.array(v), axis=0)
    clip_rise = float(np.nanmedian(fac[:, 3] - fac[:, 0]))
    print("    ★この %.2f は、1 枚の中の断面の積分を**平均**でまとめた値(芯の欠損と半値幅は中央値)。積分も中央値で"
          % np.median(r_int))
    print("    まとめると %.2f になる。平均は積分の小さい断面に引き下げられ、経路が外れた断面を除くと平均も %.2f"
          % (fm[7], fm[2]))
    print("    になる。見出しは平均の %.2f を使う(どちらのまとめ方でも 1 を下回る)。" % np.median(r_int))
    print("    ★1 を下回る原因は確かめきれていない。要因を 1 つずつ振った(同じ %d 枚・同じ経路と測点、中央値):"
          % len(good))
    print("      そのまま %.2f / ベースラインを 1 次に %.2f / 経路が外れた断面(断面の最大が経路から %.0f px より外、"
          % (fm[0], fm[1], OFFPATH_PX))
    print("      1 枚あたり中央値 %.0f %%)を除く %.2f —— どれも単独では 1 に届かない。"
          % (100 * fm[5], fm[2]))
    print("      明るい縁: 経路の両側の帯の生の輝度(当てはめ無し)は、明るい側でも地の %+.1f %%。芯の帯の負の欠損を"
          % (100 * fm[6]))
    print("      0 で切ると %+.2f 上がるが、同じ大きさの雑音を足した合成(地の残差の標準偏差 実写 %.3f / 合成 %.3f〜%.3f)"
          % (clip_rise, fm[4], syn_f[0.10][4], syn_f[0.15][4]))
    print("      でも %+.2f〜%+.2f 上がる —— 雑音の負の側と区別できず、明るい縁が効いているとは言えない。"
          % (syn_f[0.10][3] - syn_f[0.10][0], syn_f[0.15][3] - syn_f[0.15][0]))
    print("      合成(芯が黒、幅 0.6 mm)は 雑音なし %.2f / 雑音 0.10 で %.2f / 0.15 で %.2f(種 3 本の中央値)。"
          % (syn_f[0.0][0], syn_f[0.10][0], syn_f[0.15][0]))
    print("      組み合わせ(中央値 + ベースライン 1 次 + 経路から %.0f px 以内)でも %.2f —— 組み合わせても 1 に届かない。"
          % (OFFPATH_PX, fm[8]))
    print("      「経路が外れた」の判定の確かめ: %.0f px でなく「経路が断面の半値幅の連続区間の外」で数えると、外れは"
          % OFFPATH_PX)
    print("      %.0f %%(%.0f px の判定では %.0f %%)、除いた平均 %.2f、組み合わせ %.2f。"
          % (100 * fm[9], OFFPATH_PX, 100 * fm[5], fm[10], fm[11]))
    print("    ★2 値化(欠損 > 0.5 の絶対しきい値)は半値幅の %.2f 倍しか返さず、%.0f %% の写真で半分に届かない。"
          % (np.median(r_bin), 100 * np.mean(r_bin < 0.5)))
    print("    芯の欠損が 0.5 前後の実写では芯の一部しか拾わない —— 元の画素の 2 値化の幅は見た目の幅として")
    print("    使えない。下の比(k / 元の画素)は各手法の**自己整合**で、幅の正しさは言わない。")
    kh = rows_out[-1]
    k3 = rows_out[REAL_BINS.index(3)]
    print("  ★言えるのは k=%d の**中央値**までで、分布は重なる: 四分位は積分法 %.2f〜%.2f、2 値化 %.2f〜%.2f。"
          % (REAL_BINS[-1], kh["int_q"][0], kh["int_q"][1], kh["bin_q"][0], kh["bin_q"][1]))
    print("    k=3 では中央値の差も %.2f しかない(積分 %.3f / 2 値化 %.3f)。2 値化の比は k=2・3・4 で"
          % (k3["bin_med"] - k3["int_med"], k3["int_med"], k3["bin_med"]))
    print("    %.2f → %.2f → %.2f と単調でない(1 画素の階段に丸まる位置がひびごとに違う)。"
          % tuple(r["bin_med"] for r in rows_out[1:]))
    print("  ★画素を %d 倍粗くすると、積分法は中央値 %.2f 倍(四分位 %.2f〜%.2f)、2 値化は %.2f 倍"
          % (REAL_BINS[-1], kh["int_med"], kh["int_q"][0], kh["int_q"][1], kh["bin_med"]))
    print("     (四分位 %.2f〜%.2f)。順位は合成と同じ(積分法のほうが保存される)が、★★実写では"
          % (kh["bin_q"][0], kh["bin_q"][1]))
    print("     積分法の保存も崩れる —— ざらつき無しの合成では 1 %% 以内(上の検算)、実写では +%.0f %%。"
          % (100 * (kh["int_med"] - 1.0)))
    print("     ひびの外の地(骨材の穴・汚れ)が断面の外側に入り、粗い画素ほど 2 次のベースラインが")
    print("     それを拾う。合成でもざらつき 5 %% を足すと最も細いひびで %.0f %% ずれるので、向きは同じ。"
          % (100 * syn[0.05][0]))
    print("  ★合成と違った点: 合成のひびは芯が黒く、細くなると 2 値化は**何も返さなかった**。")
    print("     実写のひびは芯が灰色(欠損の中央値 %.2f)で、粗くすると 2 値化は空になるより"
          % np.median(peak))
    print("     **過大**に出る(空になったのは k=%d で %.0f %%)。壊れ方は「消える」より「膨らむ」。"
          % (REAL_BINS[-1], 100 * kh["bin_empty"]))
    print("  ★積分法が返すのは「幅 x 深さ」(欠損の面積)で、芯が灰色の実写では幅そのものではない。")
    print("     mm に直すには芯の欠損(深さ)の較正が要る —— 合成で 0.05 mm まで読めたのは芯が黒だったから。")
    rec = {"n_seen": len(files), "n_path": len(res), "n_used": len(good),
           "int_ratio_kmax": round(kh["int_med"], 3), "bin_ratio_kmax": round(kh["bin_med"], 3),
           "bin_empty_kmax": round(kh["bin_empty"], 3),
           "native_int_px": round(float(np.median(nat_i)), 2),
           "native_bin_px": round(float(np.median(nat_b)), 2),
           "core_deficit": round(float(np.median(peak)), 3),
           "int_q_kmax": [round(x, 2) for x in kh["int_q"]], "bin_q_kmax": [round(x, 2) for x in kh["bin_q"]],
           "int_ratio_k3": round(k3["int_med"], 3), "bin_ratio_k3": round(k3["bin_med"], 3),
           "lag_ratio_1": round(lag["lag1"], 2), "lag_ratio_100": round(lag["lag100"], 2),
           "fwhm_px": round(float(np.median(fwhm)), 2),
           "int_depth_over_fwhm": round(float(np.median(r_int)), 2),
           "int_depth_over_fwhm_q": [round(float(x), 2) for x in q_r],
           "bin_over_fwhm": round(float(np.median(r_bin)), 2),
           "bin_under_half_fwhm": round(float(np.mean(r_bin < 0.5)), 2),
           "ratio_base1": round(float(fm[1]), 2), "ratio_onpath": round(float(fm[2]), 2),
           "offpath_frac": round(float(fm[5]), 2), "rim_bright_side": round(float(fm[6]), 3),
           "clip_rise_real": round(clip_rise, 2),
           "clip_rise_syn": [round(float(syn_f[t_][3] - syn_f[t_][0]), 2) for t_ in (0.10, 0.15)],
           "syn_ratio_noise": [round(float(syn_f[t_][0]), 2) for t_ in (0.0, 0.10, 0.15)],
           "ratio_median": round(float(fm[7]), 2), "ratio_combo": round(float(fm[8]), 2),
           "offpath_frac_run": round(float(fm[9]), 2), "ratio_onpath_run": round(float(fm[10]), 2),
           "ratio_combo_run": round(float(fm[11]), 2)}
    print("\n  RECORDED_REAL = %s" % rec)
    _recorded_gate(rec)
    # --- 所見を固定する(実データがあるときだけ。下の 4 本の閾値はどれも実データを見て置いた値) ---
    assert len(good) >= 30, len(good)
    assert 1.0 <= kh["int_med"] < 1.25, kh["int_med"]            # 実写では保存が崩れる(合成は 1 % 以内)
    assert kh["bin_med"] > kh["int_med"] + 0.2, (kh["bin_med"], kh["int_med"])
    assert 0.40 < float(np.median(peak)) < 0.75, float(np.median(peak))   # 芯は黒くない
    assert lag["lag100"] > 0.85 and lag["lag1"] < 0.6, lag      # 100 おきは遠い写真と同程度に違う
    # 積分 ÷ 深さ が見た目の幅(半値幅)の半分を超える(主張「積分 = 幅 x 深さ」の妥当性。実データを見て置いた)。
    # ★前の版は上限 < 1.0 も置いていた —— 実写の偏り(1 を下回る、原因は未確認)を門で固定する逆向きの門で、
    #   合成(1.00〜1.12)なら落ちるので外した。1 を下回ることは記録値と文で示す。
    assert float(np.median(r_int)) > 0.5, float(np.median(r_int))
    _real_figure(good, rows_out, (float(fm[5]), float(fm[9])))
    return {"rows": rows_out, "rec": rec}


def _real_figure(good, rows_out, offpath) -> None:
    """代表の図(実写 2 枚: 元の画素 / k 倍粗い画素)と、比の折れ線。"""
    if not figs.enabled():
        return
    from scipy.ndimage import binary_erosion
    name, pick = next(((n, per) for n, per in good if n == REAL_SHOW), good[0])
    k_hi = REAL_BINS[-1]

    def _panel(m, k):
        g = np.clip(m["b"], 0.0, 1.0)
        msk = m["mask"]
        if k > 1:
            g = np.kron(g, np.ones((k, k)))
            msk = np.kron(msk, np.ones((k, k), bool))
        rgb = np.dstack([g, g, g])
        edge = msk & ~binary_erosion(msk)      # 実写は塗らず、2 値化の輪郭だけ橙で重ねる
        rgb[edge] = (1.0, 0.55, 0.0)
        return rgb

    m1, mk = pick[0], pick[-1]
    kr = rows_out[-1]
    figs.save_grid(
        "real_crack_rebin",
        [_panel(m1, 1), _panel(mk, k_hi)],
        ["元の画素: 積分 %.1f px / 2値化 %.1f px" % (m1["int"], m1["bin"]),
         "%d 倍粗い画素: 積分 %.1f px / 2値化 %.1f px" % (k_hi, mk["int"], mk["bin"])],
        ncols=2,
        title="実写のひびを %d 倍粗い画素で: 幅の比の中央値 積分 x%.2f / 2 値化 x%.2f(%d 枚、四分位は重なる)"
              % (k_hi, kr["int_med"], kr["bin_med"], len(good)),
        caption="%s。橙の輪郭は 2 値化(欠損 > 0.5)のマスク。幅は元の画素の単位。四分位は積分 %.2f〜%.2f / "
                "2 値化 %.2f〜%.2f。%s"
                % (name, kr["int_q"][0], kr["int_q"][1], kr["bin_q"][0], kr["bin_q"][1], REAL_CREDIT))
    ks = np.array([r["k"] for r in rows_out], np.float64)
    figs.save_table("real_crack_ratio",
                    ["画素の倍率 k", "積分法 中央値", "積分法 四分位", "2 値化 中央値", "2 値化 四分位", "2 値化が空"],
                    [["%d" % r["k"], "%.3f" % r["int_med"], "%.2f〜%.2f" % tuple(r["int_q"]),
                      "%.3f" % r["bin_med"], "%.2f〜%.2f" % tuple(r["bin_q"]), "%.0f %%" % (100 * r["bin_empty"])]
                     for r in rows_out],
                    title="同じひびを粗い画素で測った幅の比(k / 元の画素、実写 %d 枚)" % len(good),
                    caption="中央値は k=4 で積分法のほうが 1 に近いが、四分位は重なり、k=3 では差 0.03。"
                            "合成なら積分法は 1 のまま(1 % 以内)。")
    from PIL import Image
    tiles, caps = [], []
    for n, per in good[:: max(1, len(good) // 8)][:8]:
        m = per[0]
        g = np.clip(m["b"], 0.0, 1.0)
        rgb = np.dstack([g, g, g])
        px, py = m["path"]
        ok = (py >= 0) & (py < g.shape[0])
        rgb[np.round(py[ok]).astype(int), px[ok].astype(int)] = (0.1, 0.85, 0.3)   # 測った経路(緑、列ごとの最暗の尾根)
        tiles.append(np.kron(rgb, np.ones((2, 2, 1))))
        caps.append("半値幅 %.0f / 積分÷芯 %.1f / 2値化 %.1f px" % (m["fwhm"], m["int"] / m["prof_peak"], m["bin"]))
    figs.save_grid("real_crack_samples", tiles, caps, ncols=4,
                   title="使った実写のひび(等間隔に 8 枚)。緑 = 列ごとの最暗の尾根(測った経路。中心線ではない)",
                   caption="緑はひびの中心ではなく片側の縁に寄りやすく、地や別のひびへ飛ぶ列もある(断面の最大が経路から "
                           "%.0f px より外の断面は 1 枚あたり中央値 %.0f %%、経路が断面の半値幅の区間の外に出る断面は "
                           "%.0f %%)。見た目の幅は断面の半値幅。積分は「幅 x 深さ」なので芯の欠損で割って並べた。"
                           "2 値化(欠損 > 0.5)は芯が灰色のひびで芯の一部しか拾わない。%s"
                           % (OFFPATH_PX, 100 * offpath[0], 100 * offpath[1], REAL_CREDIT))
    kk, yi, yb = [], [], []
    for i, k in enumerate(REAL_BINS[1:], start=1):
        for j, (_, per) in enumerate(good):
            jit = 0.25 * ((j % 9) / 8.0 - 0.5)
            kk.append(k + jit)
            yi.append(per[i]["int"] / per[0]["int"])
            yb.append(per[i]["bin"] / per[0]["bin"])
    kk, yi, yb = np.asarray(kk), np.asarray(yi), np.asarray(yb)
    lo, hi = 0.0, 3.0                       # この外の点は描かず、数を題と説明に出す(枠に貼り付けない)
    oi = ~((yi >= lo) & (yi <= hi))
    ob = ~((yb >= lo) & (yb <= hi))
    k_med = np.array([r["k"] for r in rows_out[1:]], np.float64)
    figs.save_plot("real_crack_ratio_spread",
                   [("積分法(1 枚 1 点)", kk[~oi] - 0.17, yi[~oi]), ("2 値化(1 枚 1 点)", kk[~ob] + 0.17, yb[~ob]),
                    ("積分法の中央値", k_med - 0.17, np.array([r["int_med"] for r in rows_out[1:]])),
                    ("2 値化の中央値", k_med + 0.17, np.array([r["bin_med"] for r in rows_out[1:]]))],
                   kinds=["scatter", "scatter", "line", "line"], colors=["right", "wrong", "right", "wrong"],
                   xlabel="画素をまとめる倍率 k", ylabel="幅の比(k / 元の画素)",
                   title="幅の比の散らばり(実写 %d 枚): 中央値は積分法が 1 に近いが、点の雲は重なる" % len(good),
                   caption="比は各手法の自己整合で、幅の正しさは言わない。0〜3 の外の点(積分法 %d 点・2 値化 %d 点、"
                           "粗い画素でベースラインの当てはめが壊れた断面を含む)は描いていない。" % (int(oi.sum()), int(ob.sum())))

# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("コンクリートのひび割れ幅は 1 画素より細い —— 数える幅と、積分する幅")
    print("視野 %d x %d px / 1 px = %.2f mm / PSF σ = %.1f px" % (
        W_PX, H_PX, PX_MM, PSF_SIGMA))
    print("=" * 78)

    section_renderer()
    sweep = section_width_sweep()
    taper = section_taper()
    cross = section_crossover()
    mx = section_max_vs_mean()
    det = section_detection()
    section_tool_gaps()
    real = section_real()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    dead = [t for t, v in zip(sweep["true"], sweep["bin"]) if v == 0.0]
    print("  * 2 値化は %.2f mm(%.1f px)以下で**何も返さない**。返せる範囲でも"
          " %.2f mm 刻みの階段。" % (max(dead), max(dead) / PX_MM, PX_MM))
    print("  * 同じマスクから 2·EDT と 2·EDT-1 で %.2f mm 違う —— 測りたい量と"
          "同じ大きさの規約差。" % PX_MM)
    print("  * 積分法は 0.05 mm(0.25 px)まで連続。弱点は照明の傾斜ではなく"
          "**ベースラインの次数**(1 次だと %+.4f mm の下駄)。" % cross["e1"][-1])
    print("  * テーパ試験: 積分法は全 %d 点、2 値化は %d 点でしか値が出ない"
          "(設計限界 0.20 mm 未満の %d 点では %d 点)。"
          % (taper["n"], taper["n_got"], taper["n_below"], taper["n_below_got"]))
    print("  * 畳むと結論が反転する: 点ごとでは 2 値化が勝ち、経路平均では"
          "積分法が勝つ(σ=0.07 で %.4f/%.4f vs %.4f/%.4f mm)。"
          % (cross["int_rms"][3], cross["bin_rms"][3],
             cross["int_mean_rms"][3], cross["bin_mean_rms"][3]))
    print("  * 最大幅は測点 N とともに増える(%d 点 %+.4f -> %d 点 %+.4f mm)。"
          "予測は σ_w·a_N。" % (mx["n"][0], mx["meas"][0], mx["n"][-1], mx["meas"][-1]))
    lost = [r for r in det["rows"] if r[3] > 0]
    print("  * 経路の検出は測定より易しい。外れたのは %d/%d 条件で、"
          "いずれも幅ではなくざらつきが原因。" % (len(lost), len(det["rows"])))
    rec = real["rec"] if real else RECORDED_REAL
    print("  * 実写(公開データ %d 枚): 画素を %d 倍粗くしても積分法は %.2f 倍、2 値化は %.2f 倍。"
          "芯が灰色の実写では 2 値化は消えるより膨らむ%s。"
          % (rec["n_used"], REAL_BINS[-1], rec["int_ratio_kmax"], rec["bin_ratio_kmax"],
             "" if real else "(記録値)"))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
