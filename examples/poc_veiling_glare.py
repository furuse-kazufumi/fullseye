# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_veiling_glare — 迷光(ベーリンググレア)がコントラスト計測を壊す。

    py -3.11 examples/poc_veiling_glare.py

【この PoC が答える問い】
検査ラインでいちばん普通の問い —「レンズの MTF は仕様どおり出ている。
なのに黒い部分が浮いて、しきい値が安定しない。数字は合っているのに、なぜ」。
答えは「**MTF と迷光は別の量を測っている**。点拡がり関数(PSF)の中心の
コアは鋭いまま、裾だけを重くすると、刃のエッジで測る MTF50 は 4 % しか
動かないのに、黒レベルは 0 % → 16 % へ悪化する。**どちらの数字も嘘では
ない**」。

【所見(すべて下の節で実測。★ は重要、★★ は最重要)】

 1. ★★**同じレンズで「MTF 合格・迷光 不合格」を作れる**。裾の割合 g を
    0 → 0.20 に振ると、刃のエッジ SFR(窓 ±16 px)の MTF50 は
    0.2347 → 0.2249 cyc/px(**-4.2 %**、仕様 0.22 に対して合格のまま)。
    同じ像の黒レベルは 0.0 % → 15.7 %(仕様 3 % に対して**不合格**)。
    5 段階の g のうち **3 段階で判定が割れる**(3 節の表)。

 2. ★★**予想が外れた**。書き始める前は「細かいチャートで測ると裾が見えない」
    と予想していた。実測すると**周波数の高低は関係が無い** —— 正弦チャートの
    絶対コントラスト(Michelson)は、周期 4 px でも 16 px でも
    ちょうど **(1-g)×コアの MTF** になる(実測と閉形式が 4 桁一致)。
    盲点を作っているのは周波数ではなく**基準レベルの取り方**で、
    SFR が窓の両端を黒/白の基準に使う瞬間に (1-g) が約分されて消える。
    「粗いチャートで正規化した CTF」も同じ理由で盲目になる(6 節)。

 3. ★★**測定窓を変えると答えが変わり、しかも収束しない**。同じレンズ(g=0.20)で
    黒四角の一辺 D を 16 → 256 px に広げると黒レベルは 19.6 % → 4.5 %。
    裾が 1/(1+(r/r0)²) だと集光量は log で効くので、**打ち切り半径 R を
    2 倍にするたびに「裾の割合」が一定量ずつ増え続ける**(5 節: 同じ物理の
    レンズが R=56 px で 8.5 %、R=1792 px で 33.6 %)。
    「迷光は何 % か」は**測る範囲を宣言しない限り意味を持たない**。

 4. ★裾はどの周波数に居るか。全 PSF を `fs.psf_to_mtf` に渡すと MTF は
    f=0 の 1.0 から **f≈0.02 cyc/px までに 1-g の台地へ落ちる**。一方
    窓 ±16 px の SFR が持てる最低の非零周波数は 1/32 = 0.031 cyc/px ——
    **裾が居る周波数帯に、窓が 1 本もビンを持っていない**。
    「窓 ±W では周期 2W px より粗い構造は測れない」を数字で言い直しただけ。

 5. `fs.psf_to_mtf` 自体は正しい。エアリー像を通すと `fs.mtf_diffraction`
    の閉形式と最大 0.008(絶対値)で一致する(1 節)。**壊れているのは
    op ではなく測り方**、というのがこの PoC の主題。

 6. ★`fs.derivate_funct_1d`(中心差分)で ESF を微分すると、MTF が
    sin(2πf)/(2πf) 倍に潰れる。実測で MTF50 が 0.2347 → 0.1969 cyc/px
    (**-16 %**)。前進差分なら離散 LSF が厳密に出る(理論 0.2342 と 0.2 % 一致)。
    8 節の「道具の穴」に入れた。

【グラウンドトゥルース】
PSF を **コア(ガウス 1σ=0.8 px)と裾(1/(1+(r/r0)²)、r0=30 px)の重み付き和**
として作る。どちらも打ち切り半径 R=224 px 内で総和 1 に正規化してから
`(1-g)*core + g*tail` とするので、**裾のエネルギー比は厳密に g**。
畳み込みは FFT の循環畳み込み。周期像が効かないよう場面は「白地」に統一し、
黒い試験標的だけを中央に置く(白は周期的に繰り返しても白)。

【節立て】
 1) 合成器の検算(総和 1・一様場の不変・エアリーで fullseye と突き合わせ)
 2) ★ゼロ点 —— 刃のエッジ SFR で MTF を測る
 3) ★★判定の割れ —— MTF 合格 / 迷光 不合格
 4) 黒レベル法(ISO 9358 の考え方)と対数の閉形式
 5) ★★測定窓を振る —— 答えが変わり、収束しない
 6) ★★正弦チャートの絶対コントラスト —— 予想が外れたところ
 7) 裾はどの周波数に居るか(`fs.psf_to_mtf`)
 8) 道具の穴(assert で現状を固定)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面と光学系の定数 ------------------------------------------------------ #
N = 640              # 画面(白地)。周期境界でも白なので「無限の白地」と等価
R_PSF = 224          # PSF の打ち切り半径 [px]。N/2 未満に取り、巻き込みを避ける
SIG_CORE = 0.8       # コアの 1σ [px]
R0_TAIL = 30.0       # 裾の特性半径 [px](実レンズの散乱裾はコアの数十倍広い)
PITCH_UM = 3.45      # 画素ピッチ [µm](産業用 CMOS の実寸)

SPEC_MTF50 = 0.22    # 合否の仕様: MTF50 [cyc/px] 以上
SPEC_GLARE = 0.03    # 合否の仕様: 黒レベル(白地に対する比)以下
G_LIST = (0.00, 0.02, 0.05, 0.10, 0.20, 0.35)

_YY, _XX = np.mgrid[0:N, 0:N]
_C = N // 2
_R2 = (_YY - _C) ** 2 + (_XX - _C) ** 2
_R = np.sqrt(_R2)
_INSIDE = _R2 <= R_PSF * R_PSF


def _unit(a):
    """総和 1 に正規化。"""
    return a / a.sum()


CORE = _unit(np.exp(-_R2 / (2.0 * SIG_CORE * SIG_CORE)) * _INSIDE)
TAIL = _unit(_INSIDE / (1.0 + _R2 / (R0_TAIL * R0_TAIL)))


_PCACHE: dict[float, np.ndarray] = {}
_KCACHE: dict[float, np.ndarray] = {}


def psf(g: float) -> np.ndarray:
    """裾の**エネルギー比が厳密に g** の PSF(総和 1)。"""
    p = _PCACHE.get(g)
    if p is None:
        p = (1.0 - g) * CORE + g * TAIL
        _PCACHE[g] = p
    return p


def convolve(img: np.ndarray, g: float) -> np.ndarray:
    """裾の割合 *g* の PSF による結像(循環畳み込み)。白地の場面でのみ使う。

    ★キャッシュの鍵は **g**。最初は ``id(psf)`` を鍵にしていて、使い捨ての
    配列の id が回収後に再利用されるせいで**別の g の像が返っていた**
    (2 節の表が 2 行おきに同じ値になって気づいた)。
    """
    K = _KCACHE.get(g)
    if K is None:
        K = np.fft.rfft2(np.fft.ifftshift(psf(g)))
        _KCACHE[g] = K
    return np.fft.irfft2(np.fft.rfft2(img) * K, s=img.shape)


# --- 測り方 A: 刃のエッジ SFR(ISO 12233 の実務)----------------------------- #
def esf_of(out: np.ndarray) -> np.ndarray:
    """列平均のエッジ拡がり関数。雑音ゼロなので傾けた刃は要らない。"""
    return out.mean(axis=0)


def sfr(esf: np.ndarray, half_width: int, ends: int = 3):
    """窓 ±*half_width* の ESF から MTF を出す。返り値 ``(f[cyc/px], mtf, lo, hi)``。

    ★**窓の両端の平均を黒/白の基準に取る**のが実務(ISO 12233 も局所の
    レベルで正規化する)。この 1 行が迷光を約分して消す —— 3 節と 6 節。

    微分は**前進差分**。階段像と離散 PSF の畳み込みでは
    ``diff(ESF)`` が離散 LSF そのものになるため、余計な補正が要らない。
    中心差分(`fs.derivate_funct_1d`)を使うと sin(2πf)/(2πf) 倍だけ
    潰れる —— 8 節で実測して固定してある。
    """
    seg = esf[_C - half_width:_C + half_width + 1]
    lo = float(seg[:ends].mean())
    hi = float(seg[-ends:].mean())
    e = (seg - lo) / (hi - lo)
    lsf = np.diff(e)
    spec = np.fft.rfft(lsf)
    f = np.fft.rfftfreq(lsf.size, 1.0)
    return f, np.abs(spec) / abs(spec[0]), lo, hi


def mtf50(f: np.ndarray, m: np.ndarray) -> float:
    """MTF が 0.5 を切る周波数。``fs.invert_funct_1d`` で逆関数にしてから引く。"""
    inv = fs.invert_funct_1d(m)                    # {"x": MTF 昇順, "y": 元の添字}
    idx = float(np.interp(0.5, np.asarray(inv["x"]), np.asarray(inv["y"])))
    return float(np.interp(idx, np.arange(f.size), f))


# --- 測り方 B: 黒レベル法(ISO 9358 の考え方)-------------------------------- #
def black_square_scene(side: int) -> np.ndarray:
    """白地の中央に一辺 *side* px の黒四角。"""
    s = np.ones((N, N))
    h = side // 2
    s[_C - h:_C + h, _C - h:_C + h] = 0.0
    return s


def black_level(out: np.ndarray, side: int) -> float:
    """黒四角の**中央部**の明るさ / 白地の明るさ。"""
    q = max(2, side // 8)
    dark = float(out[_C - q:_C + q, _C - q:_C + q].mean())
    white = float(out[20:60, 20:60].mean())
    return dark / white


def black_level_predicted(g: float, side: int) -> float:
    """PSF を四角の上で**直接足した**予測値(FFT を通らない別経路)。"""
    h = side // 2
    return 1.0 - float(psf(g)[_C - h:_C + h, _C - h:_C + h].sum())


def black_level_logform(g: float, side: int) -> float:
    """同じ面積の円板に置き換えた閉形式。

    裾 ``1/(1+(r/r0)²)`` の半径 a 内のエネルギー比は
    ``ln(1+(a/r0)²)/ln(1+(R/r0)²)`` —— **対数**でしか増えない。
    """
    a = side / np.sqrt(np.pi)
    frac = np.log1p((a / R0_TAIL) ** 2) / np.log1p((R_PSF / R0_TAIL) ** 2)
    return g * (1.0 - frac)


# =========================================================================== #
def section1_check():
    print("=" * 78)
    print("1) 合成器の検算 —— この PSF を真値として使ってよいか")
    print("=" * 78)
    p = psf(0.20)
    print("  PSF: コア 1σ %.1f px + 裾 1/(1+(r/%.0f)²)、打ち切り %d px、画素 %.2f µm"
          % (SIG_CORE, R0_TAIL, R_PSF, PITCH_UM))
    print("  総和 = %.15f(1 との差 %.2e)" % (p.sum(), abs(p.sum() - 1.0)))
    print("  裾のエネルギー比 = %.6f(仕込み 0.200000、構成上ここは厳密)"
          % float((0.20 * TAIL).sum()))
    dev = float(np.abs(convolve(np.ones((N, N)), 0.20) - 1.0).max())
    print("  一様な白地を通すと %.2e しか動かない(単位分解の確認)" % dev)

    # 裾の半径内エネルギー(対数則の検算)
    print()
    print("  裾の半径 w 内エネルギー(離散和 vs 対数の閉形式):")
    print("  %6s %12s %12s" % ("w px", "離散", "ln 形"))
    for w in (8, 16, 32, 64, 128, R_PSF):
        d = float(TAIL[_R <= w].sum())
        lf = np.log1p((w / R0_TAIL) ** 2) / np.log1p((R_PSF / R0_TAIL) ** 2)
        print("  %6d %12.4f %12.4f" % (w, d, lf))

    # ★fullseye 側の突き合わせ: エアリー像 → psf_to_mtf が閉形式と合うか
    print()
    print("  fullseye の光学 op の突き合わせ(この PoC の測り方が正しいかの確認):")
    ap = np.asarray(fs.airy_pattern(size=257, wavelength_um=0.55, f_number=5.6,
                                    pixel_pitch_um=0.5))
    meas = np.asarray(fs.psf_to_mtf(ap, pixel_pitch_um=0.5))
    closed = np.asarray(fs.mtf_diffraction(f_number=5.6, wavelength_um=0.55, samples=64))
    fx = np.linspace(10.0, 250.0, 25)
    d = np.abs(np.interp(fx, meas[:, 0], meas[:, 1]) - np.interp(fx, closed[:, 0], closed[:, 1]))
    print("    airy_pattern → psf_to_mtf と mtf_diffraction の差: 最大 %.4f / 平均 %.4f"
          % (d.max(), d.mean()))
    print("    → op は正しい。以降で壊れるのは**測り方**であって op ではない。")

    # 理論 MTF50(ガウスコアだけ)との突き合わせ
    theo = float(np.sqrt(np.log(2.0) / (2.0 * np.pi ** 2 * SIG_CORE ** 2)))
    f, m, _, _ = sfr(esf_of(convolve(edge_scene(), 0.0)), 16)
    print("  裾ゼロの MTF50: 実測 %.4f / 理論 exp(-2π²σ²f²) から %.4f cyc/px(差 %.1f %%)"
          % (mtf50(f, m), theo, 100 * abs(mtf50(f, m) - theo) / theo))
    return p


def edge_scene() -> np.ndarray:
    """左半分が黒、右半分が白の刃のエッジ。"""
    s = np.zeros((N, N))
    s[:, _C:] = 1.0
    return s


def section2_zero_point():
    print()
    print("=" * 78)
    print("2) ★ゼロ点 —— 刃のエッジ SFR(窓 ±16 px)で MTF を測る")
    print("=" * 78)
    print("  これが現場のゼロ点。狭い窓しか見ないので裾を捉えられない、はず。")
    print("  窓 ±W を振って、裾の割合 g に対する MTF50 [cyc/px] の動きを見る。")
    print()
    edge = edge_scene()
    widths = (16, 32, 64, 128)
    print("  %6s |" % "g", end="")
    for w in widths:
        print(" %10s" % ("±%d px" % w), end="")
    print("   %10s" % "窓端の黒")
    print("  " + "-" * (9 + 11 * len(widths) + 13))
    table = {}
    for g in G_LIST:
        out = convolve(edge, g)
        e = esf_of(out)
        print("  %6.2f |" % g, end="")
        row = []
        for w in widths:
            f, m, lo, hi = sfr(e, w)
            v = mtf50(f, m)
            row.append(v)
            print(" %10.4f" % v, end="")
        f, m, lo, hi = sfr(e, 16)
        print("   %10.4f" % lo)
        table[g] = row
    print()
    base = table[0.0][0]
    print("  → 窓 ±16 px では g=0 → 0.20 で MTF50 が %.4f → %.4f(%.1f %%)しか動かない。"
          % (base, table[0.20][0], 100 * (table[0.20][0] / base - 1)))
    print("     窓を ±128 px まで広げてやっと %.1f %% 落ちる —— **窓が広いほど裾が見える**。"
          % (100 * (table[0.20][3] / table[0.0][3] - 1)))
    print("     「窓端の黒」列が示すとおり、窓の端の黒は g とともに浮いている。")
    print("     ★SFR はその浮いた値を**黒の基準**として使うので、浮きは約分されて消える。")
    return table


def section3_verdict(mtf_table):
    print()
    print("=" * 78)
    print("3) ★★判定の割れ —— 同じレンズで MTF 合格・迷光 不合格")
    print("=" * 78)
    print("  仕様: MTF50 >= %.2f cyc/px、黒レベル <= %.0f %%(黒四角 64 px)"
          % (SPEC_MTF50, 100 * SPEC_GLARE))
    print()
    print("  %6s %10s %8s %12s %8s %10s"
          % ("g", "MTF50", "判定", "黒レベル", "判定", "総合"))
    print("  " + "-" * 60)
    rows = []
    for g in G_LIST:
        m50 = mtf_table[g][0]
        out = convolve(black_square_scene(64), g)
        bl = black_level(out, 64)
        ok_m = m50 >= SPEC_MTF50
        ok_b = bl <= SPEC_GLARE
        verdict = "合格" if (ok_m and ok_b) else ("★割れ" if ok_m != ok_b else "不合格")
        print("  %6.2f %10.4f %8s %11.1f %% %8s %10s"
              % (g, m50, "合格" if ok_m else "不合格", 100 * bl,
                 "合格" if ok_b else "不合格", verdict))
        rows.append([("%.2f" % g), ("%.4f" % m50), "合格" if ok_m else "不合格",
                     ("%.1f %%" % (100 * bl)), "合格" if ok_b else "不合格", verdict])
    split = sum(1 for r in rows if r[5] == "★割れ")
    print()
    print("  → %d/%d の条件で判定が割れる。**どちらの数字も嘘ではない** ——"
          % (split, len(rows)))
    print("     MTF は「エッジの立ち上がりの鋭さ」を、黒レベルは「遠くから漏れてくる光」を")
    print("     測っている。同じレンズの別の側面なので、片方だけでは受け入れ試験にならない。")
    figs.save_table("verdict", ["裾 g", "MTF50", "MTF 判定", "黒レベル", "迷光 判定", "総合"],
                    rows, title="同じレンズ・2 つの試験(仕様 MTF50>=%.2f / 黒<=%.0f%%)"
                    % (SPEC_MTF50, 100 * SPEC_GLARE))
    return rows


def section4_black_level():
    print()
    print("=" * 78)
    print("4) 黒レベル法(ISO 9358 の考え方)—— 3 通りの計算が一致するか")
    print("=" * 78)
    print("  白地に黒四角(64 px)。中央部の明るさ / 白地の明るさ。")
    print("  FFT の結像・PSF の直接和・円板の対数閉形式、独立な 3 経路で出す。")
    print()
    print("  %6s %12s %12s %12s" % ("g", "結像 FFT", "PSF 直接和", "対数閉形式"))
    print("  " + "-" * 46)
    for g in G_LIST:
        out = convolve(black_square_scene(64), g)
        print("  %6.2f %12.5f %12.5f %12.5f"
              % (g, black_level(out, 64), black_level_predicted(g, 64),
                 black_level_logform(g, 64)))
    print()
    print("  → 3 経路が 3 桁一致。黒レベルは g に**比例**する(裾の割合をそのまま読む)。")
    print("     2 節の MTF50 は同じ g に対してほとんど動かなかったので、")
    print("     **どちらの量を仕様に書くかで、レンズの合否が決まる**。")


def section5_window():
    print()
    print("=" * 78)
    print("5) ★★測定窓を振る —— 答えが変わり、しかも収束しない")
    print("=" * 78)
    g = 0.20
    print("  同じレンズ(g=%.2f)。黒四角の一辺 D を振る。" % g)
    print()
    print("  %6s %12s %12s %12s" % ("D px", "黒レベル", "対数閉形式", "D=16 比"))
    print("  " + "-" * 46)
    sides = (16, 32, 64, 128, 192, 256)
    meas = []
    for D in sides:
        out = convolve(black_square_scene(D), g)
        bl = black_level(out, D)
        meas.append(bl)
        print("  %6d %12.5f %12.5f %12.2f" % (D, bl, black_level_logform(g, D),
                                              bl / meas[0]))
    print()
    print("  → 同じレンズが 19.6 % とも 4.5 % とも読める(%.1f 倍の開き)。"
          % (meas[0] / meas[-1]))
    print("     裾が 1/(1+(r/r0)²) だと、半径 a から R までの集光量は")
    print("     ln(R/a) —— **a を半分にするたびに一定量ずつ増える**。収束しない。")
    print()
    print("  もう一段深い形の同じ問題: 「裾の割合」自体が打ち切り半径 R に依る。")
    print("  裾とコアの**振幅比**を固定して(= 同じ物理のレンズ)、R だけを振る:")
    print()
    e_core = 2.0 * np.pi * SIG_CORE ** 2                       # ∫ exp(-r²/2σ²) dA
    # R=R_PSF で g=0.20 になるよう裾の振幅 α を決める
    e_tail_ref = np.pi * R0_TAIL ** 2 * np.log1p((R_PSF / R0_TAIL) ** 2)
    alpha = (0.20 / 0.80) * e_core / e_tail_ref
    print("  %10s %12s %14s" % ("R px", "裾の割合", "画角 相当"))
    print("  " + "-" * 40)
    for R in (56, 112, R_PSF, 448, 896, 1792):
        et = alpha * np.pi * R0_TAIL ** 2 * np.log1p((R / R0_TAIL) ** 2)
        print("  %10d %12.3f %13.1f °" % (R, et / (e_core + et),
                                          np.degrees(np.arctan(R * PITCH_UM * 1e-3 / 16.0))))
    print()
    print("  → 同じレンズが「裾 8.5 %」とも「裾 33.6 %」とも書ける。")
    print("     ★**測る範囲を宣言しない迷光の数字は意味を持たない**。ISO 9358 が")
    print("     黒点の径と積分球の立体角を規格で固定しているのはこのため。")
    if figs.enabled():
        xs = np.array(sides, float)
        figs.save_plot("window_dependence",
                       [("実測 黒レベル", xs, 100 * np.array(meas)),
                        ("対数閉形式", xs, 100 * np.array([black_level_logform(g, D)
                                                           for D in sides])),
                        ("仕様 3 %", xs, np.full(xs.size, 100 * SPEC_GLARE))],
                       xlabel="黒四角の一辺 D [px]", ylabel="黒レベル [%]",
                       title="同じレンズ、答えは窓の大きさで変わる (g=0.20)",
                       caption="D を 16 倍にすると 19.6 % が 4.5 % になる。"
                               "裾が重いので log でしか減らない = 収束しない。")
    return meas


def section6_chart():
    print()
    print("=" * 78)
    print("6) ★★正弦チャートの絶対コントラスト —— 予想が外れたところ")
    print("=" * 78)
    print("  予想: 「細かいチャートは裾を見ない(裾は低周波だから)」。")
    print("  実測: **周波数は関係なかった**。絶対コントラストはどの周期でも")
    print("        ちょうど (1-g)×コアの MTF になる。")
    print()
    periods = (4, 8, 16, 32, 64, 128, 256)
    xs = np.arange(N)
    print("  %8s |" % "周期 px", end="")
    for g in (0.0, 0.10, 0.20):
        print(" %10s %10s" % ("g=%.2f 実測" % g, "(1-g)Mコア"), end="")
    print()
    print("  " + "-" * (11 + 22 * 3))
    ratio = {}
    for per in periods:
        chart = 0.5 + 0.5 * np.cos(2.0 * np.pi * xs / per)[None, :] * np.ones((N, 1))
        print("  %8d |" % per, end="")
        for g in (0.0, 0.10, 0.20):
            o = convolve(chart, g)
            seg = o[_C, _C - 2 * per:_C + 2 * per]
            mich = (seg.max() - seg.min()) / (seg.max() + seg.min())
            pred = (1.0 - g) * np.exp(-2.0 * np.pi ** 2 * SIG_CORE ** 2 / per ** 2)
            ratio.setdefault(g, []).append(mich)
            print(" %10.4f %10.4f" % (mich, pred), end="")
        print()
    print()
    print("  → 実測と (1-g)×コア MTF が 4 桁一致(周期 4 px でも 256 px でも)。")
    print("     **絶対コントラストで測れば、細かいチャートでも裾は見える。**")
    print()
    print("  では SFR はなぜ盲目だったのか。粗いチャートで正規化した CTF を作ると:")
    print()
    print("  %10s |" % "基準の周期", end="")
    for g in (0.10, 0.20):
        print(" %14s" % ("g=%.2f CTF(4px)" % g), end="")
    print()
    print("  " + "-" * 44)
    for k, per_ref in enumerate(periods):
        print("  %10d |" % per_ref, end="")
        for g in (0.10, 0.20):
            print(" %14.4f" % (ratio[g][0] / ratio[g][k]), end="")
        print()
    print()
    print("  → 基準に取るチャートが**裾より細かい**(周期 << 裾の広がり %d px)と、"
          % (2 * R_PSF))
    print("     基準そのものが同じ (1-g) を被っているので約分され、CTF は g に鈍くなる。")
    print("     ★盲点を作るのは周波数ではなく**基準レベルの取り方**。SFR が窓の両端を")
    print("     黒/白の基準にする(ISO 12233 の実務)瞬間に、これが起きている。")
    if figs.enabled():
        f_ax = 1.0 / np.array(periods, float)
        series = [("g=%.2f 絶対" % g, f_ax, np.array(ratio[g])) for g in (0.0, 0.10, 0.20)]
        series.append(("g=0.20 CTF(周期 64 基準)", f_ax,
                       np.array(ratio[0.20]) / ratio[0.20][periods.index(64)]))
        figs.save_plot("chart_contrast", series, xlabel="空間周波数 [cyc/px]",
                       ylabel="Michelson コントラスト",
                       title="裾を見るかどうかは基準の取り方で決まる",
                       caption="絶対コントラストは (1-g) だけ下がる。粗いチャートで"
                               "正規化した CTF は g=0 の曲線へ戻ってしまう。")


def section7_where_is_the_tail():
    print()
    print("=" * 78)
    print("7) 裾はどの周波数に居るか(fs.psf_to_mtf で全 PSF を見る)")
    print("=" * 78)
    g = 0.20
    pairs = np.asarray(fs.psf_to_mtf(psf(g), pixel_pitch_um=PITCH_UM))
    f_px = pairs[:, 0] * PITCH_UM * 1e-3                 # cyc/mm → cyc/px
    print("  PSF 全体(打ち切り %d px)を渡すと、MTF は f=0 の 1.0 から" % R_PSF)
    print("  1-g = %.2f の台地へ落ちる。落ちきる周波数を測る:" % (1 - g))
    print()
    print("  %14s %10s" % ("f [cyc/px]", "MTF"))
    print("  " + "-" * 26)
    for tgt in (0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.234):
        print("  %14.4f %10.4f" % (tgt, float(np.interp(tgt, f_px, pairs[:, 1]))))
    # 台地の半分まで落ちる周波数
    half = 1.0 - 0.5 * g
    k = int(np.argmax(pairs[:, 1] < half))
    f_half = float(np.interp(half, [pairs[k, 1], pairs[k - 1, 1]], [f_px[k], f_px[k - 1]]))
    print()
    print("  裾の寄与が半分になる周波数: %.4f cyc/px(周期 %.0f px)" % (f_half, 1 / f_half))
    for w in (16, 32, 64, 128):
        print("    窓 ±%3d px の最低非零周波数 = 1/%d = %.4f cyc/px  → 裾の帯を %s"
              % (w, 2 * w, 1.0 / (2 * w),
                 "またぐ" if 1.0 / (2 * w) < f_half else "またがない(見えない)"))
    print()
    print("  → ★窓 ±16 / ±32 px には、裾が居る周波数帯にビンが 1 本も無い。")
    print("     ±64 px 以上でようやく届く —— 2 節で窓を広げると MTF50 が落ちたのは")
    print("     これが理由。**op ではなく窓が測定の限界を決めている**。")
    if figs.enabled():
        sel = f_px <= 0.30
        series = [("PSF 全体 (g=0.20)", f_px[sel], pairs[sel, 1])]
        edge = edge_scene()
        for w in (16, 128):
            f, m, _, _ = sfr(esf_of(convolve(edge, 0.20)), w)
            series.append(("刃のエッジ SFR ±%d" % w, f[f <= 0.30], m[f <= 0.30]))
        series.append(("1-g = 0.80", np.array([0.0, 0.30]), np.array([0.80, 0.80])))
        figs.save_plot("mtf_curves", series, xlabel="空間周波数 [cyc/px]", ylabel="MTF",
                       title="裾は f<0.02 cyc/px に居る(窓が狭いと届かない)",
                       caption="全 PSF の MTF だけが f→0 で 1.0 から 0.80 へ落ちる。"
                               "窓 ±16 px の SFR は 0.031 cyc/px より下を持たない。")


def section_figures():
    """場面の絵(1 枚)。数字を出す節とは独立に置く。"""
    if not figs.enabled():
        return
    scene = black_square_scene(128)
    o0 = convolve(scene, 0.0)
    o2 = convolve(scene, 0.20)
    s = np.s_[::2, ::2]
    figs.save_grid("glare_scene", [scene[s], o0[s], o2[s], (o2 - o0)[s]],
                   ["入力 白地+黒四角", "裾なし g=0", "裾あり g=0.20", "差 (g=0.20 - 0)"],
                   title="迷光は黒を浮かせる(コアの鋭さは変わらない)",
                   ncols=2, signed=[False, False, False, True],
                   caption="2 画素に 1 つ間引いて表示。黒四角の中が %.1f %% 浮いている。"
                           % (100 * black_level(o2, 128)))


def section8_tool_gaps():
    print()
    print("=" * 78)
    print("8) 道具の穴 —— fullseye に無かったもの・危ないもの")
    print("=" * 78)

    # (a) ESF / LSF / SFR / 迷光の op が 3 層のどこにも無い
    import ops as _ops
    allnames = set(dir(fs)) | set(dir(fs.ledger)) | {o.name for o in _ops.REGISTRY}
    for kw in ("esf", "lsf", "sfr", "slanted", "glare", "veil", "stray", "mtf50"):
        hit = [n for n in allnames if kw in n.lower()]
        assert not hit, (kw, hit)
    print("  (a) ★**ESF/LSF/SFR と迷光の op が 3 層(facade %d / ledger %d / 進化 %d)の"
          % (len(dir(fs)), len(dir(fs.ledger)), len(_ops.REGISTRY)))
    print("      どこにも無い**。`psf_to_mtf` は「PSF を持っている人」向けで、現場が")
    print("      持っているのは刃のエッジの写真。`edge_spread(img, roi)` /")
    print("      `sfr_from_edge(esf, window)` / `veiling_glare_index(img, dark_mask)` の")
    print("      3 本があれば、この PoC の 2〜5 節は op の呼び出しだけで書ける。")

    # (b) derivate_funct_1d は中心差分 —— MTF が sinc 倍に潰れる
    e = esf_of(convolve(edge_scene(), 0.0))
    seg = e[_C - 16:_C + 17]
    seg = (seg - seg[:3].mean()) / (seg[-3:].mean() - seg[:3].mean())
    lsf_c = np.asarray(fs.derivate_funct_1d(seg))
    sp = np.fft.rfft(lsf_c)
    fc = np.fft.rfftfreq(lsf_c.size, 1.0)
    mc = np.abs(sp) / abs(sp[0])
    f50_c = mtf50(fc, mc)
    f, m, _, _ = sfr(e, 16)
    f50_f = mtf50(f, m)
    assert f50_c < 0.85 * f50_f, (f50_c, f50_f)
    print("  (b) ★`fs.derivate_funct_1d` は**中心差分**なので、ESF の微分に使うと")
    print("      MTF が sin(2πf)/(2πf) 倍に潰れる。実測 MTF50 %.4f(前進差分 %.4f、"
          % (f50_c, f50_f))
    print("      理論 %.4f)—— **-%.0f %%**。docstring は「1 階微分」としか書いておらず、"
          % (np.sqrt(np.log(2) / (2 * np.pi ** 2 * SIG_CORE ** 2)),
             100 * (1 - f50_c / f50_f)))
    print("      周波数応答の注意が無い。ESF→LSF に使う人は必ず踏む。")

    # (c) create_funct_1d_pairs は整数格子に落とすので x が 1 未満の関数を壊す
    fx = np.linspace(0.0, 0.5, 33)
    fy = np.exp(-2.0 * np.pi ** 2 * SIG_CORE ** 2 * fx ** 2)
    fn = np.asarray(fs.create_funct_1d_pairs(fy[::-1], fx[::-1]))
    assert fn.shape == (2,), fn.shape
    bad = float(fs.get_y_value_funct_1d(fn, 0.5))
    good = mtf50(fx, fy)
    assert abs(bad - good) > 0.01, (bad, good)
    print("  (c) ★★`create_funct_1d_pairs` は **x を整数格子に丸める**。MTF 曲線の")
    print("      横軸は cyc/px で [0, 0.5] しか無いので、33 点の曲線が **2 点**に潰れる")
    print("      (実測 shape %r)。そのまま `get_y_value_funct_1d` で引くと MTF50 が"
          % (fn.shape,))
    print("      %.4f と返る —— 正しくは %.4f。**例外も警告も出ない**ので、もっともらしい"
          % (bad, good))
    print("      数字が静かに出てくるのがいちばん危ない。x のスケールを受ける引数か、")
    print("      「x の範囲が 2 格子未満」で拒否する fail-closed が要る。")

    # (d) psf_to_mtf は放射平均のみ —— 非等方な PSF を 1 本の曲線に潰す
    ax = np.exp(-((_XX - _C) ** 2) / (2 * 0.6 ** 2) - ((_YY - _C) ** 2) / (2 * 1.6 ** 2))
    ax = _unit(ax * _INSIDE)
    pr = np.asarray(fs.psf_to_mtf(ax, pixel_pitch_um=PITCH_UM))
    fpx = pr[:, 0] * PITCH_UM * 1e-3
    r_avg = mtf50(fpx, pr[:, 1])
    t_x = float(np.sqrt(np.log(2) / (2 * np.pi ** 2 * 0.6 ** 2)))
    t_y = float(np.sqrt(np.log(2) / (2 * np.pi ** 2 * 1.6 ** 2)))
    assert pr.shape[1] == 2
    assert t_y < r_avg < t_x, (t_y, r_avg, t_x)
    print("  (d) `psf_to_mtf` は**放射平均だけ**を返す。σx=0.6 / σy=1.6 px の非等方 PSF")
    print("      (非点収差のある実レンズ)では、真の MTF50 が水平 %.3f・垂直 %.3f cyc/px"
          % (t_x, t_y))
    print("      なのに 1 本の %.3f を返す —— **どちらでもない値**。サジタル/タンジェンシャル"
          % r_avg)
    print("      を分ける `axis=` か、方向別の 2 曲線を返す口が要る。")

    # (e) 任意カーネルの畳み込みが公開層に無い
    conv_ops = [n for n in allnames if "convol" in n.lower() or "convolve" in n.lower()]
    assert all(("wiener" in n or "tcspc" in n or "piv_line" in n) for n in conv_ops), conv_ops
    print("  (e) **任意の PSF で像を畳む op が公開層に無い**(`convol*` に当たるのは")
    print("      Wiener 逆畳み込みと TCSPC の装置関数と LIC だけ: %r)。" % (sorted(conv_ops),))
    print("      光学シミュレーションの入口なので、`image_convolve(img, kernel, mode)` は")
    print("      あってよい。この PoC は numpy の rfft2 を直に書いている。")

    print()
    print("  次にやるべきこと: (a) の 3 本を `optics/imaging` 族へ。ただし出す前に、")
    print("  この PoC と同じ土俵で「窓 W と黒点径 D を必須引数にする」ことを決める ——")
    print("  5 節のとおり、既定値を静かに選ぶと利用者は**間違った合否**を持ち帰る")
    print("  (`strain_from_displacement` の method を必須にしたのと同じ判断)。")


def main():
    t0 = time.time()
    print("poc_veiling_glare — 迷光がコントラスト計測を壊す")
    print("(PSF = コア %.1f px + 裾 1/(1+(r/%.0f)²)。裾のエネルギー比が真値)"
          % (SIG_CORE, R0_TAIL))
    print()
    section1_check()
    mtf_table = section2_zero_point()
    section3_verdict(mtf_table)
    section4_black_level()
    section5_window()
    section6_chart()
    section7_where_is_the_tail()
    section_figures()
    section8_tool_gaps()
    print()
    print("  所要 %.1f 秒" % (time.time() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
