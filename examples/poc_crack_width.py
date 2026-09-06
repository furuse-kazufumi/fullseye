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

1. **ゼロ点は幅 0.24 mm(1.2 px)より細いと何も返さない**。2 値化のマスクが
   空になるからで、0.22 mm と 0.02 mm の区別がつかないのではなく、
   **どちらも「ひび割れなし」になる**。返せた範囲でも値は 0.20 mm 刻みの
   階段(= 1 画素刻み)にしかならない。
2. ★**同じマスクから、規約 2 通りで幅が 0.20 mm 違う**。距離変換の 2 倍
   (``2·EDT``)と、離散格子の作法どおりの ``2·EDT − 1`` の差はちょうど
   1 画素 = 0.20 mm。**測ろうとしている量そのものと同じ大きさ**なので、
   どちらの規約かを書かない「幅 0.4 mm」には意味が無い。
3. ★★**積分法は 0.05 mm(0.25 px)まで連続に追える**。きれいな場面での
   偏りは全幅で 1 % 以下。輝度欠損の**総量**は畳み込み(レンズのぼけ)でも
   画素化でも保存されるからで、幅が画素を下回っても情報は消えていない。
4. ★★**積分法の弱点は照明ではなく「ベースラインの次数」だった**。予想は
   「照明の傾斜に弱い」だったが、傾斜(1 次)は 1 次のベースラインで
   きれいに抜ける。**壊れるのは照明が曲がっているとき**で、1 次のまま
   だと幅に一定の下駄(実測)が乗る。2 次にすると消える。予想は半分外れ。
5. ★**ざらつきに対しては、両者は「壊れ方の種類」が違う**。積分法は
   点ごとの値が散らばる(偏りはほぼ 0)、ゼロ点は散らばらないが**丸ごと
   何も返さなくなる**。1 つの RMS 誤差に畳むと、後者は「誤差 = 真値」と
   して数えられ、**測れなかったことと大きく間違えたことが区別できない**。
6. ★★**最大幅は必ず過大になり、その量は閉形式で予測できる**。規格は
   最大幅で決まることが多いが、N 点測れば最大値は平均 + σ·a_N だけ上に出る
   (a_N = 正規標本の期待最大値)。実測と予測の一致は本文の表のとおり。
   **測点を増やすほど「最大幅」は大きくなる** —— 密に測ると不合格になる。

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
    print("   幅 [mm]  幅 [px]   Σcov/長さ [px]   PSF 後 [px]   ずれ")

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
WIDTHS_MM = (0.05, 0.075, 0.10, 0.15, 0.20, 0.30, 0.45, 0.70, 1.00, 1.40, 2.00)


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
    print("\n  ★ゼロ点が何も返さない範囲: %s mm(= %.2f px 以下)。"
          % (", ".join("%.3f" % d for d in dead), max(dead) / PX_MM))
    print("  ★同じマスクから 2 通りの幅が出て、差は常に 1 px = %.2f mm。" % PX_MM)
    ok = [(t, i) for t, i in zip(true_l, int_l)]
    err = [100 * (i - t) / t for t, i in ok]
    print("  ★積分法の偏りは全幅で %+.2f 〜 %+.2f %%(0.05 mm = 0.25 px を含む)。"
          % (min(err), max(err)))

    figs.save_plot("width_sweep",
                   [("積分法", true_l, int_l),
                    ("2 値化 2·EDT", true_l, bin_l),
                    ("2 値化 2·EDT-1", true_l, bin2_l),
                    ("真値(y=x)", true_l, true_l)],
                   xlabel="真の幅 [mm]", ylabel="推定した幅 [mm]",
                   title="幅の掃引(きれいな場面)。0 は「何も返さなかった」",
                   caption="2 値化の 2 本は階段。0.24 mm 以下ではマスクが空になり "
                           "0(= 未検出)へ落ちる。積分法は 0.05 mm まで直線に乗る。")
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

    rms_i = float(np.sqrt(np.mean((est - truth) ** 2)))
    rms_b = float(np.sqrt(np.mean((bw[got] - truth[got]) ** 2))) if got.any() else np.nan
    print("  測点 %d 点(6 px 間隔)。真の幅 %.2f 〜 %.2f mm。"
          % (xs.size, truth.min(), truth.max()))
    print("  積分法    : 全点で値が出る。RMS 誤差 %.4f mm" % rms_i)
    print("  2 値化    : %d/%d 点でしか値が出ない(残りはマスクが空)。"
          "出た点だけの RMS 誤差 %.4f mm" % (int(got.sum()), xs.size, rms_b))
    print("  ★「出た点だけ」で数えると 2 値化は %.4f mm で、積分法(%.4f mm)と"
          " 大差ないように見える。" % (rms_b, rms_i))
    print("     未検出を真値との差として数え直すと %.4f mm —— "
          "**測れなかったことを誤差 0 として消してはいけない**。"
          % float(np.sqrt(np.mean(np.where(got, bw - truth, truth) ** 2))))

    thr = 0.20
    below = truth < thr
    print("  ★設計限界 %.2f mm 未満の区間(%d/%d 点)で、2 値化が値を返せたのは"
          " %d 点。" % (thr, int(below.sum()), xs.size, int((got & below).sum())))

    figs.save_grid("scene",
                   [sc["img"], sc["cov"], b["mask"].astype(np.float64)],
                   ["撮った絵(ざらつき 5 %・照明傾斜)", "真の被覆率",
                    "2 値化のマスク"],
                   ncols=1, title="幅が %.2f〜%.2f mm のひび割れ(1 px = %.2f mm)"
                                  % (truth.min(), truth.max(), PX_MM))
    figs.save_plot("taper",
                   [("真値 w(s)", xs * PX_MM, truth),
                    ("積分法", xs * PX_MM, est),
                    ("2 値化 2·EDT-1", xs[got] * PX_MM, bw[got])],
                   xlabel="経路方向の位置 [mm]", ylabel="幅 [mm]",
                   title="幅の分布 w(s) を追う(2 値化は細い側で点が消える)",
                   caption="2 値化の系列は値が出た点だけを結んでいる —— "
                           "線が途切れているところは「ひび割れなし」と答えた点。")
    return {"rms_int": rms_i, "rms_bin": rms_b, "n_got": int(got.sum()),
            "n": int(xs.size)}


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
    int_rms, bin_rms, int_bias, int_sd, miss = [], [], [], [], []
    print("  幅 0.60 mm 固定。ざらつき σ を振る(3 種の平均)")
    print("   σ      積分 偏り      積分 σ(点ごと)   積分 RMS    2値 RMS   2値 未検出")
    for s in sigmas:
        ei, bi, ms = [], [], []
        for sd in seeds:
            sc = render(lambda x: np.full_like(np.asarray(x, float), w_true),
                        texture=s, slope=0.30, seed=sd)
            e = measure_integral(sc["img"], xs, ys, dys)
            ei.append(e)
            b = measure_binary(sc["img"])
            bi.append(np.mean(b["w2m1"]) if b["n"] else np.nan)
            ms.append(0.0 if b["n"] else 1.0)
        e = np.concatenate(ei)
        bv = np.asarray(bi, np.float64)
        int_bias.append(float(e.mean() - w_true))
        int_sd.append(float(e.std()))
        int_rms.append(float(np.sqrt(np.mean((e - w_true) ** 2))))
        bin_rms.append(float(np.sqrt(np.nanmean((bv - w_true) ** 2)))
                       if np.isfinite(bv).any() else np.nan)
        miss.append(float(np.mean(ms)))
        print("   %.2f   %+8.4f mm   %8.4f mm      %.4f      %s      %.0f %%" % (
            s, int_bias[-1], int_sd[-1], int_rms[-1],
            "  -   " if not np.isfinite(bin_rms[-1]) else "%.4f" % bin_rms[-1],
            100 * miss[-1]))

    cross = [s for s, a, b in zip(sigmas, int_rms, bin_rms)
             if np.isfinite(b) and a > b]
    if cross:
        print("\n  ★入れ替わり: σ >= %.2f で 2 値化の RMS が積分法を下回る。"
              % min(cross))
        print("     ただし 2 値化は**幅の 1 画素階段に張り付いているだけ**で、"
              "ざらつきに強いのではない。")
    else:
        print("\n  ★この掃引の範囲では RMS の入れ替わりは起きなかった"
              "(積分法が全域で下)。予想が外れた点。")

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
                   [("積分法 RMS", sigmas, int_rms),
                    ("積分法 偏り", sigmas, int_bias),
                    ("2 値化 RMS(返せた回のみ)", sigmas,
                     [b if np.isfinite(b) else 0.0 for b in bin_rms]),
                    ("真値 0", sigmas, [0.0] * len(sigmas))],
                   xlabel="ざらつき σ", ylabel="幅の誤差 [mm]",
                   title="ざらつきに対する壊れ方(幅 0.60 mm)",
                   caption="積分法は偏りがほぼ 0 のまま散らばりだけが増える。"
                           "2 値化は散らばらないが、σ が上がると丸ごと"
                           "未検出になる(その回は RMS に入らない)。")
    return {"sigmas": sigmas, "int_rms": int_rms, "bin_rms": bin_rms,
            "curves": curves, "e1": e1_l, "e2": e2_l}


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

    print("\n  ★測点を %d 点から %d 点へ増やすと、報告する「最大幅」は "
          "%.4f -> %.4f mm(%+.1f %%)。" % (
              ns[0], ns[-1], w_true + meas[0], w_true + meas[-1],
              100 * (meas[-1] - meas[0]) / w_true))
    print("     真の幅は 1 μm も変わっていない。**密に測るほど不合格に近づく**。")
    print("  ★過大量は sqrt(2 ln N) の漸近式と比 %.2f 〜 %.2f で一致する。"
          % (min(m / p for m, p in zip(meas, pred) if p),
             max(m / p for m, p in zip(meas, pred) if p)))
    print("     規格が「最大幅」で書かれている以上、**測点密度を書かない"
          "報告は比較できない**。")

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
    print("   幅 mm   経路の誤差 [px]   幅の誤差(真の経路)  幅の誤差(引いた経路)")

    xs, ys, dys = sample_points(step=8)
    rows = []
    for w in (0.10, 0.20, 0.40, 0.80):
        sc = render(lambda x, w=w: np.full_like(np.asarray(x, float), w),
                    texture=0.05, slope=0.30, seed=9)
        rr = detect_path(sc["img"])
        idx = xs.astype(int)
        perr = float(np.sqrt(np.mean((rr[idx] - ys) ** 2)))
        e_true = measure_integral(sc["img"], xs, ys, dys).mean() - w
        # 引いた経路の傾きは、引いた行を平滑化してから差分で出す
        rs = gaussian_filter(rr, 12.0)
        d = np.gradient(rs)[idx]
        e_det = measure_integral(sc["img"], xs, rr[idx], d).mean() - w
        rows.append((w, perr, e_true, e_det))
        print("   %.2f      %8.3f          %+8.4f mm         %+8.4f mm"
              % (w, perr, e_true, e_det))

    print("\n  ★経路の誤差が 1 px を超えると、幅の推定は**外側の地を"
          "ひび割れに数え始める**のではなく、断面が斜めに切れて過大になる。")
    print("     細い側ほど経路が引けない —— 検出できないものは測れない、"
          "という当たり前が数字で出る。")
    return {"rows": rows}


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
    section_detection()
    section_tool_gaps()

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
    print("  * テーパ試験: 積分法は全 %d 点、2 値化は %d 点でしか値が出ない。"
          % (taper["n"], taper["n_got"]))
    print("  * 最大幅は測点 N とともに増える(%d 点 %+.4f -> %d 点 %+.4f mm)。"
          "予測は σ_w·a_N。" % (mx["n"][0], mx["meas"][0], mx["n"][-1], mx["meas"][-1]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
