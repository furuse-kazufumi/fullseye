# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""疑似カラーは読み手の判断を変える —— **無い境目**の本数と位置を真値つきで数える。

同じ数値を viridis で塗るか jet で塗るかは「好み」ではありません。**なめらかな場**
(真の勾配に段差がゼロ)を塗ったのに、読み手の目には**帯の境目**が見えます。
それは全部**偽**です。この PoC は、その偽の境目を **CIE L\\* と CIEDE2000 色差**で
数え、**どこに立つかを閉形式で先に当ててから**測ります。そのうえで、
写し方(``norm``)・範囲外の番兵色・重み・質的パレットが、読み手が下せる判断を
どれだけ変えるかを 1 つずつ数字にします。

EXTEND: 実際の観測量に差し替えるなら :func:`ramp_field` / :func:`bowl_field` /
:func:`inverse_square_field` が返す **float の 2-D 配列**を、自分の測定値
(温度・深度・強度・残差)に置き換えます。**真値の側を必ず一緒に持つこと** ——
この PoC の全部の数字は「場そのものは滑らかだと分かっている」ことに乗っています。
実測値だけを持ってきて図を眺めても、見えた境目が本物か偽かは**原理的に分かりません**。
場が滑らかだと言えないときは、まずここと同じ合成場で自分の配色を較正してください。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **なめらかな場に、jet は 3 本・hsv は 4 本の偽の境目を立てる**(viridis と
   gray は 0 本)。色差の山を median の 1.3 倍で数えた本数。★同じ場・同じ
   数値・同じ図の大きさで、**見えるものが変わる**。
2. ★★**どこに立つかは閉形式で当たる**。jet の明度は t = 0.375(シアン)/
   0.4490(赤と青の寄与が釣り合う点)/ 0.625(黄)で折り返す —— これは
   sRGB の伝達関数と CIE の Y 係数 (0.2126 R, 0.0722 B) から解ける。
   予測 0.3750 / 0.4490 / 0.6250 に対し実測 0.3750 / 0.4492 / 0.6250、
   **最大ずれ 0.0002**(t の刻み 0.00098 のほぼ 1 目盛)。
3. ★**「明度が単調 = 安全」ではない**。cividis は L\\* の折返し 0 回
   (``PERCEPTUAL_SAFE`` の触れ込みどおり)なのに、色差の山は **3 本**立つ
   (最大 / median = 1.87)。制御点 6 個の折れ線 LUT が原因で、明度だけを
   見る検査では捕まらない。★★予想では 0 本だった。
4. **崖**。なめらかな傾斜に本物の段差を混ぜて掃引すると、段差が**偽の境目より
   目立つ**のは jet で 0.53 %FS から、viridis で 0.35 %FS から(実測 0.53 /
   0.34 %FS)。1-D の利得曲線から予測した値と**実測が一致**(予測 0.53 / 0.35)。
   jet を選ぶと、**本物の段差を見つけるのに 1.5 倍の高さが要る**。
5. ★**写し方(norm)のほうが配色より効く**。4.3 桁ある 1/r² の場では、区別
   できる階調の実効数が linear 1.7 / log 25.9 / percentile 5.2 / rank 60.6
   (viridis、L\\* を 1 単位で刻んだヒストグラムの perplexity)。
   ★★**素朴な順位相関は使えない**: 生の L\\* と真値の Spearman ρ は
   どの norm でも 1.000 —— すべて単調写像だから当たり前で、**この指標では
   linear と rank の差がゼロに見える**。JND で刻んで初めて 0.155 / 0.997 と
   分かれる。
6. ★**外れ値 1 個の対照群で log が落ちる**。1000 倍の画素を 1 個混ぜると
   実効階調は linear 1.7 → 1.1、**log 25.9 → 15.7(-39 %)**。percentile と
   rank はほぼ不変(5.2 → 5.2 / 60.6 → 60.6)。「対数にしておけば安全」は嘘。
7. **範囲外**。``under`` / ``over`` を付けないと、振り切れた 3243 画素を
   読み手は端の色から数えるしかなく、実測 7061 画素を数えてしまう
   (**+117.7 %** の過大)。番兵色を付けると 3243 画素ちょうど(誤差 0)。
8. **二変量**。疎な領域(重み 1/10)の雑音が明るく光るので、素の viridis では
   「最も明るい K 画素」の的中率が **9.4 %**。``colorize_bivariate`` で重みを
   明度に載せると **100.0 %**。同じ数値・同じ配色で、拾える異常が変わる。
9. **質的**。隣り合う 8 領域を連続マップで塗ると、隣接ラベル対の色差の最小が
   viridis 8.9 / jet 12.9。``colorize_categorical`` は tab10 26.3 / wong 33.6。
   ★ただし**負ける場合もある**: ``colorize_labels``(乱数 RGB)は種によって
   3.5 まで落ちる(種 0 で 3.5、この場面の 10 種中 4 種が tab10 を下回る)。

【グラウンドトゥルース】場はすべて閉形式(1 次のランプ / 2 次の椀 / 点源の 1/r²)
で、**真の勾配に段差は 1 つも無い**。したがって色差マップに立った山は定義上すべて偽。
崖の節だけは、既知の高さの段差を 1 本だけ足して掃引する。

来歴(公開文献のみ): CIE 15:2004 *Colorimetry* / CIE 142-2001 *Improvement to
Industrial Colour-Difference Evaluation*(CIEDE2000)/ Wong, *Nature Methods* 8
(2011) 441 —— 色覚安全パレット / Borland & Taylor, *IEEE CG&A* 27 (2007) 14
—— "Rainbow Color Map (Still) Considered Harmful" / Crameri, Shephard & Heron,
*Nature Communications* 11 (2020) 5444 —— 科学図の配色。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 諸元 -------------------------------------------------------------------- #
SEED = 7
N_T = 1025              # 1-D 掃引の刻み(t = 0..1)
H, W = 240, 360         # 2-D の場の大きさ [px]
JND = 1.0               # L* の 1 単位 ≈ 大面積での弁別しきい(階調数を数える刻み)
JND_DE = 2.3            # CIEDE2000 の「ぎりぎり見える」目安(色対の比較用)
PEAK_RATIO = 1.30       # 色差の山と認める高さ(median の何倍か)
SMOOTH_W = 21           # 利得曲線の移動平均の幅 [刻み]
MAPS = ("gray", "jet", "hsv", "turbo", "viridis", "cividis")

# --------------------------------------------------------------------------- #
# 真値つきの場 —— どれも閉形式で、段差はゼロ                                     #
# --------------------------------------------------------------------------- #
def ramp_field(h: int = H, w: int = W) -> np.ndarray:
    """左から右へ 0 → 1 の 1 次ランプ。**画素あたりの Δt が厳密に 1/(w-1)**。"""
    return np.repeat(np.linspace(0.0, 1.0, w)[None, :], h, axis=0)


def bowl_field(h: int = H, w: int = W) -> np.ndarray:
    """中心 0、周辺 1 の 2 次曲面(椀)。水平線は各 t 値を**2 回**横切る。"""
    v, u = np.mgrid[0:h, 0:w]
    u = (u - (w - 1) / 2.0) / ((w - 1) / 2.0)
    v = (v - (h - 1) / 2.0) / ((h - 1) / 2.0)
    q = u * u + 0.55 * v * v
    return q / float(q[h // 2].max())


def inverse_square_field(n: int = 200, r0: float = 1.0) -> np.ndarray:
    """点源からの 1/r²(桁が広い場の代表)。中心を r0 で丸めて発散を避ける。"""
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot(y - (n - 1) / 2.0, x - (n - 1) / 2.0)
    return 1.0 / np.maximum(r, r0) ** 2


# --------------------------------------------------------------------------- #
# 知覚量 —— すべて fullseye の色差族で取る                                       #
# --------------------------------------------------------------------------- #
def lightness(rgb) -> np.ndarray:
    """sRGB → CIE L\\*(明度だけ)。"""
    return np.asarray(fs.rgb_to_lab(np.asarray(rgb, np.float64)))[..., 0]


def step_delta_e(rgb) -> np.ndarray:
    """横に隣り合う画素どうしの CIEDE2000 色差。→ ``(H, W-1)``。"""
    a = np.asarray(rgb, np.float64)
    return np.asarray(fs.delta_e_map(a[:, :-1], a[:, 1:], kind="2000"))


def _smooth(g: np.ndarray, w: int = SMOOTH_W) -> np.ndarray:
    """移動平均。読み手が見るのは 1 画素ではなく**帯**なので、そこに合わせる。"""
    k = np.ones(w) / w
    return np.convolve(np.pad(g, (w // 2, w // 2), mode="edge"), k, mode="valid")


def count_false_edges(gain: np.ndarray, ratio: float = PEAK_RATIO,
                      sep: int = 20) -> list[int]:
    """利得曲線の山(= 偽の境目)の位置を返す。

    **公開経路に無かった処理**(numpy で自前)。山の定義は「median の
    ``ratio`` 倍を超える極大で、``sep`` 刻み以内に他の山が無い」。
    """
    med = float(np.median(gain))
    raw = [i for i in range(1, gain.size - 1)
           if gain[i] >= gain[i - 1] and gain[i] > gain[i + 1] and gain[i] > ratio * med]
    keep: list[int] = []
    for i in raw:
        if not keep or i - keep[-1] >= sep:
            keep.append(i)
        elif gain[i] > gain[keep[-1]]:
            keep[-1] = i
    return keep


def lightness_reversals(lab_l: np.ndarray) -> list[int]:
    """L\\* の増減が反転した位置(**公開経路に無かった処理**)。"""
    d = np.diff(lab_l)
    nz = np.nonzero(d != 0)[0]
    s = np.sign(d[nz])
    return [int(nz[k + 1]) for k in range(s.size - 1) if s[k] != s[k + 1]]


def effective_levels(lab_l: np.ndarray, jnd: float = JND) -> float:
    """区別できる階調の**実効数** = L\\* を ``jnd`` で刻んだ度数分布の perplexity。

    **公開経路に無かった処理**。単に「使われた bin の数」を数えると、1 画素
    しか入らない bin も 1 と数えてしまう —— 読み手が実際に区別に使えるのは
    画素が乗っている段なので、エントロピーの指数(perplexity)で数える。
    """
    b = np.floor(np.asarray(lab_l, np.float64).ravel() / float(jnd)).astype(np.int64)
    cnt = np.bincount(b - b.min()).astype(np.float64)
    p = cnt[cnt > 0] / cnt.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    """順位相関(同順位は平均順位)。scipy が無くても動くよう numpy で書く。"""
    from scipy.stats import rankdata
    ra = rankdata(np.asarray(a, np.float64).ravel())
    rb = rankdata(np.asarray(b, np.float64).ravel())
    ra = ra - ra.mean()
    rb = rb - rb.mean()
    den = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / den) if den > 0 else 0.0


# --------------------------------------------------------------------------- #
# 1. 無い境目を数える                                                           #
# --------------------------------------------------------------------------- #
def section_false_edges() -> dict:
    print("\n" + "=" * 78)
    print("1) なめらかな場に立つ『無い境目』を数える(立ったものは全部偽)")
    print("=" * 78)
    print("  マップ     色差の山  最大/median   L* 折返し   利得の変動係数")

    t = np.linspace(0.0, 1.0, N_T)
    tc = 0.5 * (t[:-1] + t[1:])
    out, gains, lstars = {}, {}, {}
    for name in MAPS:
        rgb = np.asarray(fs.apply_cmap(t[None, :], name, vmin=0.0, vmax=1.0))
        gain = _smooth(step_delta_e(rgb)[0])
        lab_l = lightness(rgb)[0]
        pk = count_false_edges(gain)
        rev = lightness_reversals(lab_l)
        out[name] = {"peaks": [float(tc[i]) for i in pk],
                     "n_peaks": len(pk), "n_rev": len(rev),
                     "rev_t": [float(t[i]) for i in rev],
                     "ratio": float(gain.max() / np.median(gain)),
                     "cv": float(gain.std() / gain.mean())}
        gains[name], lstars[name] = gain, lab_l
        print("  %-9s   %4d      %5.2f        %4d        %.3f" % (
            name, len(pk), out[name]["ratio"], len(rev), out[name]["cv"]))
        if pk:
            print("             山の位置 t = %s" %
                  ", ".join("%.3f" % tc[i] for i in pk))

    print("\n  ★ gray と viridis は 0 本。jet %d 本 / hsv %d 本 —— "
          "**場は完全になめらかなので全部偽**。"
          % (out["jet"]["n_peaks"], out["hsv"]["n_peaks"]))
    print("  ★★ cividis は L* の折返し 0 回(PERCEPTUAL_SAFE の触れ込みどおり)"
          "なのに\n     色差の山は %d 本(最大/median %.2f)。**明度だけの検査では"
          "捕まらない**。" % (out["cividis"]["n_peaks"], out["cividis"]["ratio"]))
    print("     予想は 0 本だった —— 原因は制御点 6 個の折れ線 LUT。")

    figs.save_plot("gain_profile",
                   [(n, tc, gains[n]) for n in ("jet", "hsv", "turbo", "viridis")],
                   xlabel="正規化した値 t [-]", ylabel="色差の利得 ΔE2000 / 刻み",
                   title="無い境目 = 色差の利得の山(場はなめらか)",
                   caption="平らなら偽の境目は立たない。jet と hsv の山が"
                           "そのまま『見えてしまう帯』になる。")
    figs.save_plot("lightness_profile",
                   [(n, t, lstars[n]) for n in ("jet", "hsv", "turbo", "viridis", "gray")],
                   xlabel="正規化した値 t [-]", ylabel="CIE L* [-]",
                   title="明度が折り返すと『どちらが大きい』が読めなくなる")
    return out


# --------------------------------------------------------------------------- #
# 2. どこに立つかを閉形式で当てる                                                #
# --------------------------------------------------------------------------- #
def predict_jet_reversals() -> dict:
    """jet の明度の折返し位置を**解いて**出す(★この PoC の予測側)。

    jet は ``r = clip(1.5-|4t-3|)`` 等の折れ線なので、区間ごとに RGB が 1 次。
    中央の区間 ``t ∈ [0.375, 0.625]`` では ``g = 1`` 固定で
    ``r = 4t-1.5`` が増え ``b = 2.5-4t`` が減る。相対輝度は
    ``Y = 0.2126 R_lin + 0.7152 G_lin + 0.0722 B_lin`` で、sRGB の伝達関数は
    ``R_lin = ((r+0.055)/1.055)^2.4``。``dY/dt = 0.2126·f'(r)·4 - 0.0722·f'(b)·4 = 0``
    を解くと ``(r+0.055)/(b+0.055) = (0.0722/0.2126)^(1/1.4)``。
    L\\* は Y の単調関数なので、ここが明度の谷。区間の両端(シアン t=0.375、
    黄 t=0.625)は明度の山。
    """
    k = (0.0722 / 0.2126) ** (1.0 / 1.4)
    # 4t-1.5+0.055 = k*(2.5-4t+0.055)
    t_valley = (k * 2.555 + 1.445) / (4.0 + 4.0 * k)
    return {"cyan": 0.375, "valley": float(t_valley), "yellow": 0.625}


def section_closed_form(meas: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) ★どこに立つかを閉形式で当てる —— jet の明度の折返し")
    print("=" * 78)

    pred = predict_jet_reversals()
    got = meas["jet"]["rev_t"]
    names = ("シアン t=3/8", "赤と青の釣り合い", "黄 t=5/8")
    keys = ("cyan", "valley", "yellow")
    rows, errs = [], []
    print("  折返し             予測 t      実測 t     ずれ")
    for nm, key, g in zip(names, keys, got):
        e = abs(pred[key] - g)
        errs.append(e)
        rows.append([nm, "%.4f" % pred[key], "%.4f" % g, "%.4f" % e])
        print("   %-18s %.4f     %.4f    %.4f" % (nm, pred[key], g, e))
    print("\n  刻みの幅 %.5f に対し最大ずれ %.4f —— **ほぼ 1 目盛**。"
          % (1.0 / (N_T - 1), max(errs)))
    print("  ★谷の位置は色の名前では出てこない(緑 t=0.5 ではない)。"
          "sRGB の γ と\n     CIE の Y 係数 0.2126 R / 0.0722 B の"
          "釣り合いで決まるので、**解いて初めて当たる**。")

    figs.save_table("jet_prediction", ["折返し", "予測 t", "実測 t", "ずれ"], rows,
                    title="jet の偽の境目は閉形式で位置が出る",
                    caption="予測は sRGB 伝達関数と CIE Y 係数だけから。")
    return {"pred": pred, "meas": got, "max_err": float(max(errs))}


# --------------------------------------------------------------------------- #
# 3. 崖 —— 本物の段差が偽の境目を上回るのはどこから                              #
# --------------------------------------------------------------------------- #
def _cross(deltas: np.ndarray, real: np.ndarray, false: float) -> float:
    """``real(Δ) = false`` を対数補間で解く(崖の位置 [%FS])。"""
    ok = np.nonzero(real > false)[0]
    if not ok.size:
        return float("nan")
    i = int(ok[0])
    if i == 0:
        return 100.0 * float(deltas[0])
    lr = np.log(real[i - 1:i + 1] / false)
    w = lr[0] / (lr[0] - lr[1])
    return 100.0 * float(np.exp(np.log(deltas[i - 1])
                                + w * np.log(deltas[i] / deltas[i - 1])))


def section_cliff() -> dict:
    print("\n" + "=" * 78)
    print("3) 崖 —— 本物の段差が『偽の境目』より目立つのは何 %FS から")
    print("=" * 78)

    top = 0.98                          # 段差を足しても [0,1] に収まるように
    base = np.repeat(np.linspace(0.0, top, W)[None, :], H, axis=0)
    dt_px = top / (W - 1)               # 画素あたりの真の変化量(厳密)
    x0 = int(np.argmin(np.abs(base[0] - 0.5)))
    t0 = float(base[0, x0])
    deltas = np.array([0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.012, 0.02])
    print("  段差は t=%.3f の列に入れる。画素あたりの真の変化 %.5f(= %.3f %%FS)"
          % (t0, dt_px, 100 * dt_px))

    curves, crit, pred = {}, {}, {}
    for name in ("jet", "viridis"):
        # ---- 予測: **1-D の LUT だけ**から出す(画像は見ない) ----------- #
        tt = np.linspace(0.0, 1.0 - dt_px, 2000)
        a = np.asarray(fs.apply_cmap(tt[None, :], name, vmin=0.0, vmax=1.0))
        b = np.asarray(fs.apply_cmap((tt + dt_px)[None, :], name, vmin=0.0, vmax=1.0))
        false_pred = float(np.asarray(fs.delta_e_map(a, b))[0].max())
        # ★段差の列で読み取れる差は Δ **+ 画素 1 個ぶんのランプ** —— これを
        #   忘れると崖を 2 倍高く見積もる(最初そう書いて 0.57 vs 実測 0.30 になった)
        rr = np.asarray(fs.apply_cmap(np.array([[t0]] * len(deltas)), name,
                                      vmin=0.0, vmax=1.0))
        ss = np.asarray(fs.apply_cmap((t0 + deltas + dt_px)[:, None], name,
                                      vmin=0.0, vmax=1.0))
        real_pred = np.asarray(fs.delta_e_map(rr, ss))[:, 0]
        pred[name] = _cross(deltas, real_pred, false_pred)

        # ---- 実測: 2-D の画像から ---------------------------------------- #
        real, false = [], []
        for d in deltas:
            f = base.copy()
            f[:, x0:] += d
            rgb = np.asarray(fs.apply_cmap(f, name, vmin=0.0, vmax=1.0))
            de = step_delta_e(rgb)
            real.append(float(np.median(de[:, x0 - 1])))
            false.append(float(np.median(np.delete(de, x0 - 1, axis=1), axis=0).max()))
        real, false = np.array(real), np.array(false)
        curves[name] = (real, false)
        crit[name] = _cross(deltas, real, float(false.max()))
        print("  %-8s 偽の境目 %.3f ΔE(予測 %.3f)/ 段差 %.1f %%FS で %.3f ΔE"
              % (name, false.max(), false_pred, 100 * deltas[-1], real[-1]))
        print("           崖: 予測 %.3f %%FS   実測 %.3f %%FS   (ずれ %.3f)"
              % (pred[name], crit[name], abs(pred[name] - crit[name])))

    print("\n  ★jet を選ぶと、本物の段差を見つけるのに **%.1f 倍**の高さが要る"
          "(%.3f vs %.3f %%FS)。" % (crit["jet"] / crit["viridis"],
                                     crit["jet"], crit["viridis"]))
    print("  予測は配色の LUT だけから出していて画像を見ていない —— "
          "**配色を選んだ時点で崖の高さは決まっている**。")

    figs.save_plot("cliff",
                   [("jet: 本物の段差", 100 * deltas, curves["jet"][0]),
                    ("jet: 偽の境目", 100 * deltas, curves["jet"][1]),
                    ("viridis: 本物の段差", 100 * deltas, curves["viridis"][0]),
                    ("viridis: 偽の境目", 100 * deltas, curves["viridis"][1])],
                   xlabel="本物の段差 [%FS]", ylabel="隣接画素の色差 ΔE2000",
                   title="段差が偽の境目を追い越す点(交点が『崖』)",
                   caption="偽の境目(水平線)より下では、本物の段差は"
                           "配色の作った帯に埋もれる。")
    return {"crit": crit, "pred": pred}


# --------------------------------------------------------------------------- #
# 4. 2-D の場で見る —— 帯の本数は 1-D の 2 倍になるはず                          #
# --------------------------------------------------------------------------- #
def section_bowl(meas: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) 2-D の椀で見る —— ★生の色差マップを信じると場の勾配を配色のせいにする")
    print("=" * 78)

    f = bowl_field()
    grad = np.abs(np.diff(f, axis=1))            # 真の勾配(閉形式で分かっている)
    row = H // 2
    half = slice(W // 2 + int(0.10 * W), W - 2)  # 右半分・中心付近の |grad|≈0 は除く
    panels, caps, raw_r, gain_r = [], [], {}, {}
    for name in MAPS:
        rgb = np.asarray(fs.apply_cmap(f, name, vmin=0.0, vmax=1.0))
        panels.append(rgb)
        caps.append(name)
        de = _smooth(step_delta_e(rgb)[row][half], 5)
        raw_r[name] = float(de.max() / np.median(de))
        # ★真の勾配で割る。割らないと「場が急なところ」を境目と数えてしまう
        g = _smooth(step_delta_e(rgb)[row][half]
                    / np.maximum(grad[row][half], 1e-12), 5)
        gain_r[name] = float(g.max() / np.median(g))

    n_px = (half.stop - half.start)
    print("  中央行の右半分 %d 画素で t を 0.1 → 1.0 まで見る"
          "(段差ゼロ、勾配は外側ほど急)" % n_px)
    print("  マップ     1-D 最大/median   2-D 生の色差   2-D 真の勾配で割った後")
    err = []
    for name in MAPS:
        err.append(abs(gain_r[name] - meas[name]["ratio"]))
        print("  %-9s     %5.2f          %6.2f          %6.2f"
              % (name, meas[name]["ratio"], raw_r[name], gain_r[name]))
    print("\n  ★★生の色差マップは gray でも %.2f 倍の山を作る —— "
          "**場はなめらかなのに**。\n     椀は外側ほど急だから。"
          "真の勾配で割ると %.2f に戻り、1-D の %.2f と一致する。"
          % (raw_r["gray"], gain_r["gray"], meas["gray"]["ratio"]))
    print("     真値を持たずに色差マップを眺めると、**場のせいを配色のせいにする**。")
    print("  勾配で割った後の 1-D とのずれは最大 %.2f(6 マップ)。" % max(err))

    figs.save_grid("scene_maps", panels, caps, ncols=3,
                   title="同じなめらかな 2 次曲面(段差ゼロ)を 6 通りに塗る",
                   caption="jet と hsv には無いはずの帯が見える。")
    de_panels = []
    for name in ("jet", "viridis"):
        rgb = np.asarray(fs.apply_cmap(f, name, vmin=0.0, vmax=1.0))
        de = step_delta_e(rgb)
        de_panels.append(de / max(de.max(), 1e-9))
    figs.save_grid("false_edge_map", de_panels, ["jet の色差", "viridis の色差"],
                   ncols=2, title="隣接画素の色差マップ(明るい線 = 無い境目)",
                   caption="真の場に段差は 1 つも無い。線はすべて配色が作った。")
    return {"raw": raw_r, "gain": gain_r, "max_err": float(max(err))}


# --------------------------------------------------------------------------- #
# 5. 写し方(norm)—— 桁の広い場で順序をどれだけ復元できるか                     #
# --------------------------------------------------------------------------- #
def section_norms() -> dict:
    print("\n" + "=" * 78)
    print("5) 写し方(norm)—— 1/r² の場で『区別できる階調』を数える")
    print("=" * 78)

    base = inverse_square_field()
    rng = np.random.default_rng(SEED)
    outlier = base.copy()
    ry, rx = rng.integers(0, base.shape[0], 2)
    outlier[ry, rx] = base.max() * 1000.0     # ★対照群: 外れ値 1 個
    print("  場: 1/r²、動的範囲 %.1f 桁。対照群は 1 画素だけ 1000 倍。"
          % np.log10(base.max() / base.min()))
    print("\n  norm         実効階調  ρ(生 L*)  ρ(JND 刻み)  | 外れ値 1 個で")
    rows, panels, caps = [], [], []
    res = {}
    for norm in ("linear", "log", "sqrt", "percentile", "rank"):
        vals = {}
        for tag, field in (("clean", base), ("outlier", outlier)):
            rgb = np.asarray(fs.apply_cmap(field, "viridis", norm=norm))
            L = lightness(rgb)
            eff = effective_levels(L)
            rho_raw = spearman(L, field)
            rho_jnd = spearman(np.floor(L / JND), field)
            vals[tag] = (eff, rho_raw, rho_jnd)
            if tag == "clean":
                panels.append(rgb)
                caps.append("%s(実効 %.1f 段)" % (norm, eff))
        res[norm] = vals
        c, o = vals["clean"], vals["outlier"]
        rows.append([norm, "%.1f" % c[0], "%.3f" % c[1], "%.3f" % c[2],
                     "%.1f" % o[0], "%+.0f %%" % (100 * (o[0] - c[0]) / c[0])])
        print("  %-11s  %7.1f   %8.3f   %9.3f   | %6.1f (%+.0f %%)"
              % (norm, c[0], c[1], c[2], o[0], 100 * (o[0] - c[0]) / c[0]))

    print("\n  ★★素朴な順位相関は使えない: 生の L* との ρ は全部 %.3f ——"
          " すべて単調写像\n     なので当たり前。**この指標では linear と rank の"
          "差がゼロに見える**。" % res["linear"]["clean"][1])
    print("     JND(L* を %.1f 単位)で刻んで初めて %.3f / %.3f に分かれる。"
          % (JND, res["linear"]["clean"][2], res["rank"]["clean"][2]))
    print("  ★外れ値 1 個で **log が %.0f %% 落ちる**(%.1f → %.1f)。"
          "percentile と rank はほぼ不変。"
          % (100 * (res["log"]["outlier"][0] - res["log"]["clean"][0])
             / res["log"]["clean"][0],
             res["log"]["clean"][0], res["log"]["outlier"][0]))
    print("     「対数にしておけば安全」は嘘 —— 上端が外れ値に引っ張られるから。")

    figs.save_grid("norm_scene", panels, caps, ncols=3,
                   title="同じ 1/r² の場・同じ viridis、写し方だけを変える",
                   caption="配色を変えたのではない。値 → 色の写し方だけ。")
    figs.save_table("norm_table",
                    ["norm", "実効階調", "ρ(生 L*)", "ρ(JND 刻み)",
                     "外れ値あり", "変化"], rows,
                    title="写し方で『区別できる階調』が 35 倍変わる",
                    caption="ρ(生 L*) の列が全部 1.000 なのが、"
                            "素朴な指標の落とし穴。")
    return res


# --------------------------------------------------------------------------- #
# 6. 範囲外 —— under / over が無いと振り切れた画素を数えられない                  #
# --------------------------------------------------------------------------- #
def section_out_of_range() -> dict:
    print("\n" + "=" * 78)
    print("6) 範囲外 —— 振り切れた画素を読み手は数えられるか")
    print("=" * 78)

    # 広くて平らな丘(頂点 9.98 = 範囲内)+ 細い尖り(12.5 = 範囲外)+ 窪み(-0.6)
    y, x = np.mgrid[0:H, 0:W]

    def _bump(cy, cx, sig, amp):
        return amp * np.exp(-(((y - cy) ** 2 + (x - cx) ** 2) / (2.0 * sig * sig)))

    field = (2.0 + _bump(H * 0.5, W * 0.32, 46.0, 7.98)
             + _bump(H * 0.45, W * 0.74, 9.0, 10.5)
             - _bump(H * 0.80, W * 0.86, 14.0, 3.2))
    vmin, vmax = 0.0, 10.0
    n_over = int(np.count_nonzero(field > vmax))
    n_under = int(np.count_nonzero(field < vmin))
    n_true = n_over + n_under
    print("  場: 広い丘(頂点 %.2f = 範囲内)+ 細い尖り(%.1f = 範囲外)+ 窪み(%.2f)"
          % (2.0 + 7.98, field.max(), field.min()))
    print("  vmin=%.0f / vmax=%.0f、実際に範囲外なのは %d 画素"
          "(上 %d / 下 %d、全体の %.2f %%)"
          % (vmin, vmax, n_true, n_over, n_under, 100.0 * n_true / field.size))

    plain = np.asarray(fs.apply_cmap(field, "viridis", vmin=vmin, vmax=vmax))
    sent = np.asarray(fs.apply_cmap(field, "viridis", vmin=vmin, vmax=vmax,
                                    under=(1.0, 0.0, 1.0), over=(1.0, 1.0, 1.0)))

    def _count_like(rgb, colour):
        """その色と ΔE < JND の画素数(= 読み手が『同じ色だ』と判断する範囲)。"""
        tgt = np.broadcast_to(np.asarray(colour, np.float64), rgb.shape)
        return int(np.count_nonzero(np.asarray(fs.delta_e_map(rgb, tgt)) < JND_DE))

    end_hi = np.asarray(fs.apply_cmap(np.array([[vmax]]), "viridis",
                                      vmin=vmin, vmax=vmax))[0, 0]
    end_lo = np.asarray(fs.apply_cmap(np.array([[vmin]]), "viridis",
                                      vmin=vmin, vmax=vmax))[0, 0]
    naive = _count_like(plain, end_hi) + _count_like(plain, end_lo)
    with_s = _count_like(sent, (1.0, 1.0, 1.0)) + _count_like(sent, (1.0, 0.0, 1.0))
    print("  番兵色なし: 端の色から数えると %d 画素 (%+.1f %%) —— "
          "**端の色は『ちょうど端』とも区別できない**" % (naive, 100 * (naive - n_true) / n_true))
    print("  番兵色あり: %d 画素 (%+.1f %%)" % (with_s, 100 * (with_s - n_true) / n_true))

    figs.save_grid("range_sentinel", [plain, sent],
                   ["under/over 無し", "under=マゼンタ / over=白"], ncols=2,
                   title="振り切れた %d 画素が見えるか(vmin=0, vmax=10)" % n_true,
                   caption="左は範囲外と『ちょうど端』が同じ色。"
                           "数えると %+.0f %% 過大になる。"
                           % (100 * (naive - n_true) / n_true))
    return {"true": n_true, "naive": naive, "sentinel": with_s}


# --------------------------------------------------------------------------- #
# 7. 二変量 —— 疎な領域の雑音が目立つのを重みで抑える                            #
# --------------------------------------------------------------------------- #
def section_bivariate() -> dict:
    print("\n" + "=" * 78)
    print("7) 二変量 —— 値 × 信頼度。疎な領域の雑音が『異常』に見える")
    print("=" * 78)

    rng = np.random.default_rng(SEED)
    n = 200
    y, x = np.mgrid[0:n, 0:n]
    # 重み(観測点の密度): 左が密、右が疎
    w_floor, sigma = 0.02, 0.30
    weight = np.clip(1.0 - 0.98 * (x / (n - 1.0)), w_floor, 1.0)
    # 真の異常は密な側に 1 つだけ
    truth = 3.0 * np.exp(-(((x - 45) ** 2 + (y - 100) ** 2) / (2 * 8.0 ** 2)))
    noise = rng.standard_normal((n, n)) * sigma / np.sqrt(weight)
    value = truth + noise
    is_true = truth > 1.5
    k = int(is_true.sum())
    print("  真の異常 %d 画素(密な側)。雑音は 1/√重みで大きくなる"
          "(左 σ=%.2f / 右 σ=%.2f)。"
          % (k, sigma, sigma / np.sqrt(w_floor)))

    plain = np.asarray(fs.apply_cmap(value, "viridis", vmin=0.0, vmax=3.5))
    biv = np.asarray(fs.colorize_bivariate(value, weight, "viridis",
                                           vmin=0.0, vmax=3.5, wmin=0.0, wmax=1.0))

    def _precision(rgb):
        """『いちばん明るい k 画素』の的中率(明度 = 目を引く量、の代理)。"""
        L = lightness(rgb).ravel()
        idx = np.argsort(L)[-k:]
        return 100.0 * float(is_true.ravel()[idx].mean())

    p_plain, p_biv = _precision(plain), _precision(biv)
    print("  最も明るい %d 画素の的中率:  素の viridis %.1f %%  /  "
          "colorize_bivariate %.1f %%" % (k, p_plain, p_biv))
    print("  ★同じ数値・同じ配色で、拾える異常が変わる。"
          "重みを捨てた図は疎な側の雑音を拾う。")

    figs.save_grid("bivariate", [plain, biv],
                   ["値だけ(的中 %.0f %%)" % p_plain,
                    "値 × 信頼度(的中 %.0f %%)" % p_biv], ncols=2,
                   title="右half は観測が疎(重み 1/10)—— 雑音が明るく光る",
                   caption="真の異常は左の 1 か所だけ。")
    figs.save_grid("bivariate_inputs", [value, weight],
                   ["観測値(真の異常 + 雑音)", "重み(観測密度)"], ncols=2,
                   title="二変量の入力(この 2 枚を 1 枚に畳む)")
    return {"plain": p_plain, "biv": p_biv, "k": k}


# --------------------------------------------------------------------------- #
# 8. 質的 —— 隣り合うラベルの色差の最小値                                        #
# --------------------------------------------------------------------------- #
def section_categorical() -> dict:
    print("\n" + "=" * 78)
    print("8) 質的 —— 隣り合うラベルの色差の最小値(連続マップは隣番号が近い色)")
    print("=" * 78)

    h, w = 200, 300

    def _scene(n_lab: int):
        """``n_lab`` 個の領域。番号は**ラスタ順**(連結成分ラベリングと同じ)——
        だから空間的に隣り合う領域ほど番号が近い、という現実の条件になる。"""
        rng = np.random.default_rng(SEED)
        sy = rng.uniform(0, h, n_lab)
        sx = rng.uniform(0, w, n_lab)
        order = np.lexsort((sx, np.round(sy / (h / 3.0))))   # 上の行から左→右
        sy, sx = sy[order], sx[order]
        y, x = np.mgrid[0:h, 0:w]
        d = np.stack([(y - a) ** 2 + (x - b) ** 2 for a, b in zip(sy, sx)])
        lab = (np.argmin(d, axis=0) + 1).astype(np.int32)
        pairs = set()
        for a, b in ((lab[:, :-1], lab[:, 1:]), (lab[:-1], lab[1:])):
            m = a != b
            for p, q in zip(a[m].ravel(), b[m].ravel()):
                pairs.add((min(int(p), int(q)), max(int(p), int(q))))
        return lab, sorted(pairs)

    def _min_de(rgb, lab, pairs, n_lab):
        col = np.array([rgb[lab == k].mean(axis=0) for k in range(1, n_lab + 1)])
        de = [float(np.asarray(fs.delta_e_map(col[p - 1].reshape(1, 1, 3),
                                              col[q - 1].reshape(1, 1, 3)))[0, 0])
              for p, q in pairs]
        return float(min(de)), int(sum(1 for v in de if v < JND_DE))

    res, panels, caps = {}, [], []
    rows = []
    for n_lab in (8, 24):
        lab, pairs = _scene(n_lab)
        lf = lab.astype(np.float64)
        cands = [
            ("viridis(連続)", fs.apply_cmap(lf, "viridis", vmin=0.0, vmax=float(n_lab))),
            ("jet(連続)", fs.apply_cmap(lf, "jet", vmin=0.0, vmax=float(n_lab))),
            ("categorical tab10", fs.colorize_categorical(lab, "tab10")),
            ("categorical wong", fs.colorize_categorical(lab, "wong")),
            ("colorize_labels 種 0", fs.colorize_labels(lab, seed=0)),
        ]
        print("\n  領域 %d 個・隣接する対 %d 組" % (n_lab, len(pairs)))
        print("   塗り方                 隣接対の色差の最小   JND(%.1f)未満の対" % JND_DE)
        for name, rgb in cands:
            mn, bad = _min_de(np.asarray(rgb), lab, pairs, n_lab)
            res[(n_lab, name)] = mn
            rows.append(["%d 領域" % n_lab, name, "%.1f" % mn, str(bad)])
            print("    %-22s %8.1f              %d" % (name, mn, bad))
            if n_lab == 8 and name != "colorize_labels 種 0":
                panels.append(np.asarray(rgb))
                caps.append("%s (最小 %.0f)" % (name, mn))
        if n_lab == 24:
            rand = [_min_de(np.asarray(fs.colorize_labels(lab, seed=s)),
                            lab, pairs, n_lab)[0] for s in range(10)]
            lab24, pairs24 = lab, pairs

    print("\n  ★★崖がある: 領域が %d 個(tab10 の色数 10 を超える)になると、"
          "\n     tab10 の隣接対の最小色差は %.1f まで落ちる —— **循環して"
          "同じ色が隣り合う**。\n     連続マップ viridis (%.1f) にすら負ける。"
          % (24, res[(24, "categorical tab10")], res[(24, "viridis(連続)")]))
    print("  ★勝てないところ: 24 領域では乱数 RGB(colorize_labels)が"
          "10 種すべてで質的パレットに勝つ\n     (最小 %.1f / 最大 %.1f、"
          "tab10 は %.1f)。**色数を超えたら乱数のほうがまし**。"
          % (min(rand), max(rand), res[(24, "categorical tab10")]))

    figs.save_grid("categorical", panels, caps, ncols=2,
                   title="同じ 8 領域(番号はラスタ順 = 隣ほど番号が近い)",
                   caption="番号の大小に意味は無いのに、連続マップは"
                           "『近い番号 = 近い領域』と読ませる。")
    figs.save_grid("categorical_overflow",
                   [np.asarray(fs.colorize_categorical(lab24, "tab10")),
                    np.asarray(fs.colorize_labels(lab24, seed=0))],
                   ["tab10(色数 10 < 領域 24、最小 %.0f)" % res[(24, "categorical tab10")],
                    "colorize_labels 乱数(最小 %.0f)" % rand[0]], ncols=2,
                   title="質的パレットは色数を超えると黙って循環する",
                   caption="同じ色の領域が隣り合っても、戻り値からは分からない。")
    figs.save_table("categorical_table",
                    ["場面", "塗り方", "隣接対の色差の最小 ΔE", "JND 未満の対"], rows,
                    title="隣り合う領域を見分けられるか")
    return {"res": res, "rand": rand}


# --------------------------------------------------------------------------- #
# 9. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("9) 道具の穴(この PoC で疑似カラー族を使ってみて)")
    print("=" * 78)

    for nm in ("cmap_uniformity", "cmap_lightness_profile", "count_false_contours",
               "effective_levels", "region_adjacency"):
        assert not hasattr(fs, nm), "公開された(この節を書き換えること): %s" % nm
    print("  (a) 配色そのものを測る口が無い。この PoC は L* の折返し・利得の"
          "変動係数・\n      色差の山の本数を自前で書いた。"
          "PERCEPTUAL_SAFE は**名簿**であって検査ではない。")
    print("  (b) 『区別できる階調の実効数』(L* を JND で刻んだ perplexity)が"
          "無い。\n      norm の選択はこの 1 数字で決まるのに。")
    print("  (c) ラベル画像の**隣接グラフ**を出す口が無い。質的パレットの良し悪しは"
          "\n      『隣り合う領域の色差』で決まるので、これが要る。")

    # (d) PERCEPTUAL_SAFE は明度しか見ていない —— cividis で実測ずみ
    t = np.linspace(0, 1, 513)
    rgb = np.asarray(fs.apply_cmap(t[None, :], "cividis", vmin=0.0, vmax=1.0))
    assert len(lightness_reversals(lightness(rgb)[0])) == 0
    gain = _smooth(step_delta_e(rgb)[0], 11)
    assert float(gain.max() / np.median(gain)) > 1.5
    print("  (d) PERCEPTUAL_SAFE に cividis が入っているが、明度は単調でも"
          "色差の利得は\n      最大 / median = %.2f。**名簿の基準が明度だけ**。"
          % float(gain.max() / np.median(gain)))

    # (e) 質的パレットは色数を超えると黙って循環する(戻り値から分からない)
    lab = np.arange(1, 13).reshape(3, 4).astype(np.int32)
    rgb = np.asarray(fs.colorize_categorical(lab, "tab10"))
    assert np.allclose(rgb[0, 0], rgb[2, 2]), "ラベル 1 と 11 が同じ色"
    print("  (e) colorize_categorical は色数(tab10 = 10)を超えると黙って循環し、"
          "\n      ラベル 1 と 11 が同じ色になる(docstring には書いてある)。"
          "循環したかを\n      返さないので、呼び手が気づく手段が無い。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("疑似カラーの選び方と値の写し方が、読み手の判断をどれだけ変えるか")
    print("場はすべて閉形式(段差ゼロ)/ 知覚量は CIE L* と CIEDE2000")
    print("=" * 78)

    meas = section_false_edges()
    pred = section_closed_form(meas)
    cliff = section_cliff()
    bowl = section_bowl(meas)
    norms = section_norms()
    rng_out = section_out_of_range()
    biv = section_bivariate()
    cat = section_categorical()
    section_tool_gaps()

    # --- 所見を固定する ----------------------------------------------------- #
    assert meas["gray"]["n_peaks"] == 0 and meas["viridis"]["n_peaks"] == 0
    assert meas["jet"]["n_peaks"] >= 3, meas["jet"]["n_peaks"]
    assert meas["hsv"]["n_peaks"] >= 4, meas["hsv"]["n_peaks"]
    assert meas["jet"]["n_rev"] == 3 and meas["hsv"]["n_rev"] == 5
    assert meas["viridis"]["n_rev"] == 0 and meas["cividis"]["n_rev"] == 0
    assert meas["cividis"]["n_peaks"] >= 2, "明度単調でも色差の山は立つ"
    assert pred["max_err"] < 0.002, pred["max_err"]
    assert cliff["crit"]["jet"] > cliff["crit"]["viridis"]
    assert abs(cliff["crit"]["jet"] - cliff["pred"]["jet"]) < 0.05, cliff
    assert abs(cliff["crit"]["viridis"] - cliff["pred"]["viridis"]) < 0.05, cliff
    assert norms["rank"]["clean"][0] > 10 * norms["linear"]["clean"][0]
    assert abs(norms["linear"]["clean"][1] - 1.0) < 1e-6, "生の ρ は縮退する"
    assert norms["log"]["outlier"][0] < 0.8 * norms["log"]["clean"][0]
    assert abs(norms["rank"]["outlier"][0] - norms["rank"]["clean"][0]) < 1.0
    assert rng_out["sentinel"] == rng_out["true"]
    assert rng_out["naive"] > 2.0 * rng_out["true"]
    assert biv["biv"] > 3 * biv["plain"]
    assert cat["res"][(8, "categorical wong")] > cat["res"][(8, "viridis(連続)")]
    assert cat["res"][(24, "categorical tab10")] < cat["res"][(24, "viridis(連続)")], \
        "色数を超えた質的パレットは連続マップに負ける"

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * なめらかな場に jet は %d 本・hsv は %d 本の偽の境目を立てる"
          "(viridis 0 本)。" % (meas["jet"]["n_peaks"], meas["hsv"]["n_peaks"]))
    print("  * 位置は閉形式で当たる(jet の明度折返し、最大ずれ %.4f)。"
          % pred["max_err"])
    print("  * 崖は jet %.3f %%FS / viridis %.3f %%FS —— 本物の段差に "
          "%.1f 倍の高さが要る。" % (cliff["crit"]["jet"], cliff["crit"]["viridis"],
                                      cliff["crit"]["jet"] / cliff["crit"]["viridis"]))
    print("  * 配色より写し方が効く: 実効階調 linear %.1f → rank %.1f 段。"
          % (norms["linear"]["clean"][0], norms["rank"]["clean"][0]))
    print("  * under/over 無しでは範囲外 %d 画素を %d 画素と数える(+%.0f %%)。"
          % (rng_out["true"], rng_out["naive"],
             100 * (rng_out["naive"] - rng_out["true"]) / rng_out["true"]))
    print("  * 重みを載せると異常の的中率 %.0f → %.0f %%。"
          % (biv["plain"], biv["biv"]))
    print("  * 勝てないところ: 領域が色数(tab10 = 10)を超えると質的パレットは"
          "循環し、\n    24 領域では連続マップにも乱数 RGB にも負ける"
          "(最小色差 %.1f)。" % cat["res"][(24, "categorical tab10")])
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
