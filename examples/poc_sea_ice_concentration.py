# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""海氷密接度 —— 混合画素をどう数えるかで答えが変わる(硬い分類 vs 線形混合分解)。

    py -3.11 examples/poc_sea_ice_concentration.py

海氷と開水面が混じった海域を衛星の放射計で撮る、という場面です。**真値は氷の
面積率**(密接度)。センサは点拡がり(PSF)でぼかしてから標本化するので、
1 画素の中に氷と水が同居する **混合画素**が必ずできます。その混合画素を
「氷か水か」に押し込むのが硬い分類、割合のまま扱うのが線形混合分解です。

EXTEND: 実データに差し替えるなら :func:`make_scene` が返す ``cube``(H,W,2 の
反射率)を実観測に、``truth`` を高分解能の氷/水判定(SAR や航空写真)に
置き換えます。**真値の空間分解能が観測より十分細かいこと**が条件で、
同じ分解能の「別の推定値」を真値と呼ぶと、この PoC の主題(混合画素)が
定義ごと消えます。

この PoC が示すこと(数字はすべて実行時に印字される実測値):

 1. ★ゼロ点(band 1 を 1 本のしきい値で 2 値化して数える)は、密接度 0.35 /
    塊の相関長 3 セルで **-6.2 ポイント**外す。同じ画像を線形混合分解に
    かけると **-0.2 ポイント**。31 倍の差です。
 2. ★★**同じしきい値・同じ真値でも、塊の大きさで偏りが変わる**。密接度
    0.35 を固定し相関長を 3 -> 12 セルと振ると、硬い分類の偏りは
    **-6.2 -> -1.9 ポイント**。**周長(混合画素の量)で説明がつき**、
    偏り = -0.192 x 周長率 + 0.006(決定係数 **0.949**)。
 3. ★★**偏りの符号は密接度で反転し、途中でゼロを横切る**。同じ塊の
    大きさ・同じしきい値で、密接度 0.15 -> 0.85 と振ると偏りは
    **-3.7 -> +3.9 ポイント**、**0.49 付近でゼロ**。そこは「正しい」のでは
    なく、**散らばった氷が食われる分と、散らばった水が塗り潰される分が
    釣り合っているだけ**です。密接度 0.5 付近だけ見て検証すると合格します。
 4. しきい値の位置は偏りをまるごと平行移動させる。0.30 -> 0.70 で偏りは
    **+4.5 -> -8.2 ポイント**動く(相関長 3 セル)。
 5. ★端成分の明るさが 5 % ずれると密接度は **-1.6 ポイント**(氷側を明るく
    見積もったとき)。**分解は端成分の誤差をそのまま割り算で受け取る**ので、
    しきい値法より端成分に敏感です。
 6. ★★**第 3 成分(薄氷)は必ずどちらかに配分される**。薄氷 20 % を混ぜると、
    2 端成分の分解は「氷 = 厚氷 + 薄氷」を真値としたとき **-11.4 ポイント**、
    「氷 = 厚氷のみ」を真値としたとき **+8.4 ポイント** —— **同じ数字が、
    真値の定義しだいで低くも高くも外れる**。薄氷を 3 番目の端成分に入れれば
    どちらの定義でも 1 ポイント以下に収まります。

来歴(公開文献のみ): Comiso, *J. Geophys. Res.* 91 (1986) 975 —— 密接度
アルゴリズム / Cavalieri et al., *JGR* 89 (1984) 5355 —— NASA Team /
Heinz & Chang, *IEEE TGRS* 39 (2001) 529 —— FCLS(完全制約つき線形分解)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N_TRUE = 512            # 真値の格子(セル)
DECIM = 8               # 標本化の間引き -> 64 x 64 の観測画像
PSF_SIGMA = 3.0         # センサ PSF の σ [真値セル](FWHM 7.1 セル = 0.88 画素)
NOISE = 0.01            # センサ雑音 [反射率]

#: 端成分の反射率(band 1 = 0.66 µm, band 2 = 0.87 µm)
E_ICE = np.array([0.92, 0.85])       # 厚い海氷 + 積雪
E_WATER = np.array([0.08, 0.04])     # 開水面
E_THIN = np.array([0.42, 0.32])      # 薄氷(ニラス)—— 第 3 成分

ENDMEMBERS2 = np.stack([E_ICE, E_WATER])
ENDMEMBERS3 = np.stack([E_ICE, E_THIN, E_WATER])


# --------------------------------------------------------------------------- #
# 場面を作る —— 真値は「2 値場の氷セルの割合」で、**厳密に**分かる             #
# --------------------------------------------------------------------------- #
def _blur(field: np.ndarray, sigma: float) -> np.ndarray:
    """σ を指定したガウス平滑。**公開経路の op は σ<=3.0 しか出せない**ので、
    σ=3 を n 回掛けて σ*sqrt(n) を作る(道具の穴 (a) を参照)。"""
    n = max(1, int(round((sigma / 3.0) ** 2)))
    out = np.asarray(field, np.float64)
    for _ in range(n):
        out = np.asarray(fs.apply(out, "gauss_filter", a=1.0))
    return out


def make_truth(fraction: float, corr_len: float, seed: int) -> np.ndarray:
    """相関長 ``corr_len`` [セル] の模様で、氷の面積率が**厳密に** ``fraction``
    になる 2 値場を作る(相関つき乱数場を、上位 k セルで切る)。"""
    rng = np.random.default_rng(seed)
    g = _blur(rng.standard_normal((N_TRUE, N_TRUE)), corr_len)
    k = int(round(fraction * g.size))
    thr = np.partition(g.ravel(), g.size - k)[g.size - k]
    m = g >= thr
    if int(m.sum()) != k:                      # 同値があるときだけ端数を詰める
        idx = np.argsort(g.ravel())[::-1][:k]
        m = np.zeros(g.size, bool)
        m[idx] = True
        m = m.reshape(g.shape)
    return m


def perimeter_fraction(truth: np.ndarray) -> float:
    """周長 / 面積の指標 —— 4 近傍で相が変わるセル境界の数を、全境界数で割る。

    「混合画素がどれだけ出るか」の代理変数。塊が細かいほど大きくなります。
    """
    v = int(np.count_nonzero(truth[1:, :] != truth[:-1, :]))
    h = int(np.count_nonzero(truth[:, 1:] != truth[:, :-1]))
    total = truth[1:, :].size + truth[:, 1:].size
    return (v + h) / total


def make_scene(fraction: float = 0.35, corr_len: float = 3.0, seed: int = 0,
               thin_fraction: float = 0.0, noise: float = NOISE) -> dict:
    """真値の 2 値場 -> PSF -> 標本化 -> 2 バンドの反射率キューブ。

    ``thin_fraction`` を入れると、氷のうちその割合を**薄氷**に置き換えます
    (第 3 成分。2 端成分の分解では表現できない)。
    """
    truth = make_truth(fraction, corr_len, seed)
    thin = np.zeros_like(truth)
    if thin_fraction > 0.0:
        # 氷の内側を別の乱数場で 2 つに割る(薄氷は氷の一部として分布する)
        sel = make_truth(thin_fraction, corr_len, seed + 1000)
        thin = truth & sel
    thick = truth & ~thin

    g_thick = _blur(thick.astype(np.float64), PSF_SIGMA)
    g_thin = _blur(thin.astype(np.float64), PSF_SIGMA)
    o = DECIM // 2
    g_thick = g_thick[o::DECIM, o::DECIM]
    g_thin = g_thin[o::DECIM, o::DECIM]
    g_water = np.clip(1.0 - g_thick - g_thin, 0.0, 1.0)

    cube = (g_thick[..., None] * E_ICE + g_thin[..., None] * E_THIN
            + g_water[..., None] * E_WATER)
    if noise > 0.0:
        cube = cube + np.random.default_rng(seed + 7).normal(0.0, noise, cube.shape)
    return {"truth": truth, "thin": thin, "cube": cube,
            "frac_thick": g_thick, "frac_thin": g_thin,
            "c_true_all": float(truth.mean()),
            "c_true_thick": float(thick.mean()),
            "c_sampled_all": float((g_thick + g_thin).mean()),
            "perimeter": perimeter_fraction(truth)}


# --------------------------------------------------------------------------- #
# 2 つの数え方                                                                  #
# --------------------------------------------------------------------------- #
def hard_classify(cube: np.ndarray, level: float = 0.5) -> float:
    """★ゼロ点 —— band 1 を 1 本のしきい値で 2 値化して数える(硬い分類)。

    ``level`` は端成分のあいだの位置(0.5 = 氷と水のちょうど真ん中)。
    """
    thr = E_WATER[0] + level * (E_ICE[0] - E_WATER[0])
    return float(np.mean(cube[..., 0] >= thr))


def unmix(cube: np.ndarray, endmembers=None, ice_rows=(0,)) -> float:
    """★対比 —— 線形混合分解(``fs.spec_unmix``、FCLS)で画素ごとの割合を出す。"""
    e = ENDMEMBERS2 if endmembers is None else endmembers
    a = np.asarray(fs.spec_unmix(cube, e, constrained=True))
    return float(sum(a[..., i] for i in ice_rows).mean())


SEEDS = (0, 1, 2, 3, 4)


def measure(fraction: float, corr_len: float, level: float = 0.5,
            endmembers=None, ice_rows=(0,), thin_fraction: float = 0.0,
            truth_key: str = "c_true_all") -> dict:
    """5 つの乱数種で測って、偏り(平均)とばらつき(標準偏差)を分けて返す。"""
    hb, ub, samp, per = [], [], [], []
    for s in SEEDS:
        sc = make_scene(fraction, corr_len, s, thin_fraction)
        t = sc[truth_key]
        hb.append(hard_classify(sc["cube"], level) - t)
        ub.append(unmix(sc["cube"], endmembers, ice_rows) - t)
        samp.append(sc["c_sampled_all"] - sc["c_true_all"])
        per.append(sc["perimeter"])
    return {"hard": float(np.mean(hb)), "hard_sd": float(np.std(hb)),
            "unmix": float(np.mean(ub)), "unmix_sd": float(np.std(ub)),
            "sampling": float(np.mean(samp)), "sampling_sd": float(np.std(samp)),
            "perimeter": float(np.mean(per))}


# --------------------------------------------------------------------------- #
# 1. 合成器の検算                                                               #
# --------------------------------------------------------------------------- #
def section_sanity() -> None:
    print("\n" + "=" * 78)
    print("1) 合成器の検算 —— 真値と混合模型が本当に厳密か")
    print("=" * 78)

    m = make_truth(0.35, 3.0, 0)
    print("  真値の面積率 %.10f(狙い 0.35、%d / %d セル)" % (
        m.mean(), m.sum(), m.size))
    assert abs(m.mean() - 0.35) < 1.0 / m.size + 1e-12   # 丸めは 1 セル分だけ

    # 線形混合模型が厳密か —— 反射率は割合の 1 次結合そのもの
    sc = make_scene(0.35, 3.0, 0, noise=0.0)
    g = sc["frac_thick"]
    rebuilt = g[..., None] * E_ICE + (1.0 - g)[..., None] * E_WATER
    err = float(np.max(np.abs(rebuilt - sc["cube"])))
    print("  反射率 = 割合の 1 次結合 との差 %.2e(混合模型は厳密)" % err)
    assert err < 1e-12

    # 雑音なし・端成分を真値どおり与えたら、分解は割合を厳密に返すか
    a = np.asarray(fs.spec_unmix(sc["cube"], ENDMEMBERS2, constrained=True))
    print("  FCLS が返す氷の割合と真の割合の最大差 %.2e" % float(np.max(np.abs(a[..., 0] - g))))
    assert float(np.max(np.abs(a[..., 0] - g))) < 1e-6

    # 周長の代理変数を fullseye の blob 族と突き合わせる
    lab = fs.ledger.blob_label(m, connectivity=4)
    feats = fs.ledger.blob_features(lab)
    p_blob = float(np.sum(feats["perimeter"])) / (2.0 * m.size)
    print("  周長率: 自前の境界数え %.4f / blob_features の周長和 %.4f(%d 塊)" % (
        perimeter_fraction(m), p_blob, int(feats["n"])))
    print("  -> 桁と傾向は一致(定義が違うので一致はしない。以後は自前の指標を使う)。")


# --------------------------------------------------------------------------- #
# 2. ★ゼロ点 vs 線形混合分解                                                   #
# --------------------------------------------------------------------------- #
def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("2) ★ゼロ点(硬い分類)vs 線形混合分解 —— 密接度 0.35 / 相関長 3 セル")
    print("=" * 78)
    r = measure(0.35, 3.0)
    print("  硬い分類    偏り %+.4f  ばらつき %.4f" % (r["hard"], r["hard_sd"]))
    print("  線形混合分解 偏り %+.4f  ばらつき %.4f" % (r["unmix"], r["unmix_sd"]))
    print("  (対照群)標本化そのものの誤差 %+.4f ± %.4f" % (
        r["sampling"], r["sampling_sd"]))
    print("\n  硬い分類は %.1f ポイント低く出る。分解は %.1f ポイント。%.0f 倍の差。"
          % (100 * r["hard"], 100 * r["unmix"], abs(r["hard"] / r["unmix"])))
    print("  ★対照群が効いている —— 標本化の誤差は %.1f ポイントしかないので、"
          % (100 * abs(r["sampling"])))
    print("  硬い分類の偏りは**標本化のせいではなく、数え方のせい**です。")
    return r


# --------------------------------------------------------------------------- #
# 3. ★★塊の大きさ(周長)が偏りを決める                                        #
# --------------------------------------------------------------------------- #
CORR_LENS = (3.0, 6.0, 9.0, 12.0)


def section_floe_size() -> dict:
    print("\n" + "=" * 78)
    print("3) ★★同じ真値・同じしきい値でも、**塊の大きさ**で偏りが変わる")
    print("=" * 78)
    print("  相関長[セル]  周長率    硬い分類の偏り      分解の偏り")

    per, bias, out = [], [], {}
    for cl in CORR_LENS:
        r = measure(0.35, cl)
        out[cl] = r
        per.append(r["perimeter"])
        bias.append(r["hard"])
        print("     %5.1f      %.4f   %+.4f ± %.4f   %+.4f ± %.4f" % (
            cl, r["perimeter"], r["hard"], r["hard_sd"], r["unmix"], r["unmix_sd"]))

    # 偏りは周長率で説明できるか(fs.mat_lstsq で 1 次回帰)
    a = np.column_stack([per, np.ones(len(per))])
    sol = fs.mat_lstsq(a, np.asarray(bias))
    slope, icpt = float(sol["x"][0]), float(sol["x"][1])
    pred = a @ sol["x"]
    ss_res = float(np.sum((np.asarray(bias) - pred) ** 2))
    ss_tot = float(np.sum((np.asarray(bias) - np.mean(bias)) ** 2))
    r2 = 1.0 - ss_res / ss_tot
    print("\n  ★★偏り = %.3f x 周長率 + %.3f、決定係数 R^2 = %.3f。"
          % (slope, icpt, r2))
    print("  **混合画素の量(周長)が偏りをほぼ全部説明する** —— 塊が細かいほど")
    print("  混合画素が増え、そのすべてを「氷でない」側へ倒すので低く出ます。")
    print("  分解の偏りは %+.4f 〜 %+.4f で、周長にほとんど反応しません。"
          % (min(out[c]["unmix"] for c in CORR_LENS),
             max(out[c]["unmix"] for c in CORR_LENS)))
    return {"per": per, "bias": bias, "slope": slope, "r2": r2, "out": out}


# --------------------------------------------------------------------------- #
# 4. ★★密接度で偏りの符号が反転する(打ち消し点)                              #
# --------------------------------------------------------------------------- #
FRACTIONS = (0.15, 0.30, 0.50, 0.70, 0.85)


def section_concentration() -> dict:
    print("\n" + "=" * 78)
    print("4) ★★密接度を振ると偏りの**符号が反転**する —— 打ち消し点は正しさではない")
    print("=" * 78)
    print("  真の密接度   周長率    硬い分類の偏り      分解の偏り")

    hard, unm = [], []
    for f in FRACTIONS:
        r = measure(f, 3.0)
        hard.append(r["hard"])
        unm.append(r["unmix"])
        print("     %.2f      %.4f   %+.4f ± %.4f   %+.4f ± %.4f" % (
            f, r["perimeter"], r["hard"], r["hard_sd"], r["unmix"], r["unmix_sd"]))

    # 符号が変わる密接度を線形内挿で探す
    zero = None
    for i in range(len(FRACTIONS) - 1):
        if hard[i] * hard[i + 1] < 0:
            t = -hard[i] / (hard[i + 1] - hard[i])
            zero = FRACTIONS[i] + t * (FRACTIONS[i + 1] - FRACTIONS[i])
            break
    print("\n  ★★偏りは %+.4f -> %+.4f と符号を変え、密接度 %s でゼロを横切る。"
          % (hard[0], hard[-1], "%.2f" % zero if zero else "(範囲内に無し)"))
    print("  低密接度では**散らばった氷がしきい値に届かず食われる**、高密接度では")
    print("  **散らばった水が塗り潰される** —— 逆向きの 2 つの失敗が、途中で")
    print("  釣り合うだけです。ここだけで検証すると硬い分類は合格してしまいます。")
    return {"hard": hard, "unmix": unm, "zero": zero}


# --------------------------------------------------------------------------- #
# 5. しきい値の位置                                                             #
# --------------------------------------------------------------------------- #
LEVELS = (0.30, 0.40, 0.50, 0.60, 0.70)


def section_threshold() -> dict:
    print("\n" + "=" * 78)
    print("5) しきい値の位置 —— 偏りをまるごと平行移動させる")
    print("=" * 78)
    print("  しきい値  " + "".join("  相関長 %.0f " % c for c in (3.0, 6.0, 12.0)))

    out = {c: [] for c in (3.0, 6.0, 12.0)}
    for lv in LEVELS:
        line = "    %.2f   " % lv
        for c in (3.0, 6.0, 12.0):
            b = measure(0.35, c, level=lv)["hard"]
            out[c].append(b)
            line += "   %+.4f " % b
        print(line)
    print("\n  相関長 3 セルでは %.2f -> %.2f で %+.1f -> %+.1f ポイント。"
          % (LEVELS[0], LEVELS[-1], 100 * out[3.0][0], 100 * out[3.0][-1]))
    print("  **どのしきい値を選んでも、塊の細かさに応じた傾きが残ります** ——")
    print("  しきい値の調整では模様依存を消せない(切片を動かしているだけ)。")
    return out


# --------------------------------------------------------------------------- #
# 6. ★端成分が 5 % ずれたとき                                                  #
# --------------------------------------------------------------------------- #
def section_endmember_error() -> dict:
    print("\n" + "=" * 78)
    print("6) ★端成分の明るさが 5 % ずれると —— 分解は割り算でそれを受け取る")
    print("=" * 78)
    print("  ずらす端成分      密接度の偏り(分解)   硬い分類の偏り")

    out = {}
    base = measure(0.35, 3.0)
    out["真値どおり"] = (base["unmix"], base["hard"])
    print("  %-16s   %+.4f              %+.4f" % ("真値どおり", base["unmix"], base["hard"]))
    for name, e in (("氷 +5 %", np.stack([E_ICE * 1.05, E_WATER])),
                    ("氷 -5 %", np.stack([E_ICE * 0.95, E_WATER])),
                    ("水 +5 %", np.stack([E_ICE, E_WATER * 1.05]))):
        r = measure(0.35, 3.0, endmembers=e)
        out[name] = (r["unmix"], r["hard"])
        print("  %-16s   %+.4f              %+.4f" % (name, r["unmix"], r["hard"]))
    print("\n  ★氷側を 5 % 明るく見積もると密接度は %+.1f ポイント。分解の答えは"
          % (100 * out["氷 +5 %"][0]))
    print("  ほぼ (観測 - 水) / (氷 - 水) なので、端成分の誤差が**そのまま**乗ります。")
    print("  硬い分類はこの列では動きません(しきい値を端成分から作っていないため)")
    print("  —— **端成分に鈍いのは長所ではなく、そもそも割合を見ていないから**です。")
    return out


# --------------------------------------------------------------------------- #
# 7. ★★第 3 成分(薄氷)                                                       #
# --------------------------------------------------------------------------- #
def section_thin_ice() -> dict:
    print("\n" + "=" * 78)
    print("7) ★★第 3 成分(薄氷 20 %)—— 2 端成分は必ずどちらかに配分する")
    print("=" * 78)
    print("  真値の定義           2 端成分の分解    3 端成分の分解    硬い分類")

    out = {}
    for label, key, rows2, rows3 in (
            ("氷 = 厚氷 + 薄氷", "c_true_all", (0,), (0, 1)),
            ("氷 = 厚氷のみ", "c_true_thick", (0,), (0,))):
        r2 = measure(0.35, 3.0, thin_fraction=0.2, truth_key=key)
        r3 = measure(0.35, 3.0, thin_fraction=0.2, truth_key=key,
                     endmembers=ENDMEMBERS3, ice_rows=rows3)
        out[label] = (r2["unmix"], r3["unmix"], r2["hard"])
        print("  %-18s   %+.4f          %+.4f          %+.4f" % (
            label, r2["unmix"], r3["unmix"], r2["hard"]))

    a = out["氷 = 厚氷 + 薄氷"]
    b = out["氷 = 厚氷のみ"]
    print("\n  ★★**同じ画像・同じアルゴリズムの答えが、真値の定義しだいで**")
    print("  %+.1f ポイントにも %+.1f ポイントにもなる。薄氷は 2 端成分の張る"
          % (100 * a[0], 100 * b[0]))
    print("  直線上に無いので、FCLS は最も近い点(氷 %.2f 相当)へ射影します ——"
          % float((E_THIN[0] - E_WATER[0]) / (E_ICE[0] - E_WATER[0])))
    print("  「どちらかに配分される」のではなく「**必ず中途半端に配分される**」。")
    print("  薄氷を 3 番目の端成分に入れると %+.1f / %+.1f ポイントまで縮みます。"
          % (100 * a[1], 100 * b[1]))
    return out


# --------------------------------------------------------------------------- #
# 8. 図                                                                         #
# --------------------------------------------------------------------------- #
def _up(a: np.ndarray) -> np.ndarray:
    return np.repeat(np.repeat(np.asarray(a, np.float64), DECIM, 0), DECIM, 1)


def section_figures(floe: dict, conc: dict, thr: dict, endm: dict, thin: dict) -> None:
    if not figs.enabled():
        return
    sc = make_scene(0.35, 3.0, 0)
    a = np.asarray(fs.spec_unmix(sc["cube"], ENDMEMBERS2, constrained=True))
    hard = (sc["cube"][..., 0] >= E_WATER[0] + 0.5 * (E_ICE[0] - E_WATER[0]))
    figs.save_grid("scene",
                   [sc["truth"].astype(float), _up(sc["cube"][..., 0]),
                    _up(a[..., 0]), _up(hard.astype(float) - sc["frac_thick"])],
                   ["真値 2 値場", "観測 band1", "分解の氷割合", "硬い分類 - 割合"],
                   title="海氷密接度 0.35 / 相関長 3 セル", ncols=2,
                   signed=[False, False, False, True])

    figs.save_plot("bias_vs_threshold",
                   [("相関長 %.0f セル" % c, np.asarray(LEVELS), 100 * np.asarray(v))
                    for c, v in thr.items()]
                   + [("偏りゼロ", np.asarray(LEVELS), np.zeros(len(LEVELS)))],
                   xlabel="しきい値(氷と水のあいだの位置)",
                   ylabel="密接度の偏り [ポイント]",
                   title="しきい値は偏りを平行移動するだけ")

    figs.save_plot("bias_vs_concentration",
                   [("硬い分類", np.asarray(FRACTIONS), 100 * np.asarray(conc["hard"])),
                    ("線形混合分解", np.asarray(FRACTIONS), 100 * np.asarray(conc["unmix"])),
                    ("偏りゼロ", np.asarray(FRACTIONS), np.zeros(len(FRACTIONS)))],
                   xlabel="真の密接度", ylabel="密接度の偏り [ポイント]",
                   title="偏りの符号は密接度で反転する")

    rows = [["相関長 %.0f セル" % c, "%.4f" % floe["out"][c]["perimeter"],
             "%+.1f" % (100 * floe["out"][c]["hard"]),
             "%+.1f" % (100 * floe["out"][c]["unmix"])] for c in CORR_LENS]
    rows += [[k, "-", "%+.1f" % (100 * v[1]), "%+.1f" % (100 * v[0])]
             for k, v in endm.items()]
    rows += [[k, "-", "%+.1f" % (100 * v[2]), "%+.1f" % (100 * v[0])]
             for k, v in thin.items()]
    figs.save_table("summary", ["条件", "周長率", "硬い分類", "分解"], rows,
                    title="密接度の偏り [ポイント]",
                    caption="下 3 段は端成分 5 % 誤差と薄氷 20 %(2 端成分の分解)。")


# --------------------------------------------------------------------------- #
# 9. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(3 層すべて引いてみて)")
    print("=" * 78)

    # (a) σ を直接指定できるガウス平滑が公開経路に無い
    import ops
    op = {o.name: o for o in ops.REGISTRY}["gauss_filter"]
    assert "0.3〜3.0" in (op.doc or ""), op.doc
    for n in ("gaussian_blur", "smooth_gaussian", "blur_gaussian"):
        assert not hasattr(fs, n) and not hasattr(fs.ledger, n), n
    print("  (a) **σ を指定するガウス平滑が公開経路に無い**。進化 op の")
    print("      gauss_filter / gauss_image / cv_gaussian はどれも σ = 0.3+2.7a で")
    print("      3.0 が上限。この PoC は σ=3 を n 回掛けて σ√n を作っている。")
    print("      PSF も相関長も 3 px を超えるのが普通なので、これは実害がある。")

    # (b) spec_unmix は在った(★「無い」と書く前に 3 層引いた)
    assert hasattr(fs, "spec_unmix") and hasattr(fs, "spec_endmembers_ppi")
    print("  (b) ★線形混合分解は**在った**(fs.spec_unmix = FCLS、")
    print("      fs.spec_endmembers_ppi = PPI)。自前で最小二乗を書く必要は無かった。")

    # (c) PPI は混合画素だらけの場面では端成分を外す —— 実測
    sc = make_scene(0.35, 3.0, 0)
    e = np.asarray(fs.spec_endmembers_ppi(sc["cube"], 2, n_projections=400))
    d = min(float(np.max(np.abs(e[0] - E_ICE))), float(np.max(np.abs(e[1] - E_ICE))))
    print("  (c) PPI が返した端成分は真の氷から最大 %.3f ずれた(反射率)。" % d)
    print("      純粋画素が無い場面では PPI は**視野の中で最も端の混合画素**を")
    print("      返すので、そのまま分解に食わせると密接度が系統的にずれる。")
    print("      doc に honest limits として書いてあるが、**代わりに使える")
    print("      端成分推定(N-FINDR / VCA)は 3 層のどこにも無い**。")
    for n in ("spec_endmembers_nfindr", "spec_endmembers_vca", "vca", "nfindr"):
        assert not hasattr(fs, n) and not hasattr(fs.ledger, n), n

    # (d) 分解の不確かさ(残差・条件数)を返す口が無い
    a = np.asarray(fs.spec_unmix(sc["cube"], ENDMEMBERS2, constrained=True))
    assert a.ndim == 3 and a.shape[-1] == 2, a.shape
    print("  (d) spec_unmix は**割合だけ**を返す。画素ごとの残差(モデルが合って")
    print("      いない画素 = 第 3 成分の在りかを示す量)が取れないので、7 節の")
    print("      「薄氷が混じっている」を**推定側から検出できない**。")
    print("      mat_lstsq は residual_ss を返すのに、分解は返さない。")

    # (e) 密接度のような「面積率の推定」を要約する口が無い
    for n in ("area_fraction", "coverage_fraction"):
        assert not hasattr(fs, n) and not hasattr(fs.ledger, n), n
    print("  (e) 2 値場の面積率・周長率を返す口が無い(blob_features は塊ごと)。")
    print("      場全体の被覆率と周長率は remote sensing でも検査でも定番の 2 つ。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("海氷密接度 —— 混合画素をどう数えるかで答えが変わる")
    print("真値 %d^2 セル -> PSF σ=%.1f -> %d 分の 1 に標本化 = %d^2 画素 / 2 バンド"
          % (N_TRUE, PSF_SIGMA, DECIM, N_TRUE // DECIM))
    print("=" * 78)

    section_sanity()
    section_zero_point()
    floe = section_floe_size()
    conc = section_concentration()
    thr = section_threshold()
    endm = section_endmember_error()
    thin = section_thin_ice()
    section_figures(floe, conc, thr, endm, thin)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 硬い分類の偏りは**周長(混合画素の量)で決まる**(R^2 = %.3f)。" % floe["r2"])
    print("  * その符号は密接度で反転し、%s 付近で打ち消し合う —— そこは正しくない。"
          % ("%.2f" % conc["zero"] if conc["zero"] else "(範囲外)"))
    print("  * 分解は模様に鈍いが、**端成分の誤差と第 3 成分には弱い**。")
    print("  * 「密接度 = 0.35」と書くとき、薄氷をどちらに数えたかを書かないと")
    print("    同じ数字が %+.1f にも %+.1f ポイントにもずれる。"
          % (100 * thin["氷 = 厚氷 + 薄氷"][0], 100 * thin["氷 = 厚氷のみ"][0]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
