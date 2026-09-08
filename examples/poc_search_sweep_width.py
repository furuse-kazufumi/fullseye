# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""捜索救難の走査幅を空撮画像から測る —— 画像が返すのは 1 枚の絵、計画が要るのは 1 本の幅。

海上で人を探すとき、指揮所が知りたいのは「この機で、この時間で、この海域を、
どれだけ潰せるか」です。その数字は **走査幅(sweep width)W** ひとつに集約されます
—— 横距離ごとの検出確率 p(x) を積分した ``W = ∫p(x)dx`` で、「幅 W の帯を
完璧に見た」のと同じ検出数になる幅です。W が決まれば被覆率 ``C = W·v·t/A`` が
決まり、C が決まれば検出確率が決まります。**画像処理の仕事は、この W を
実測して渡すところまで**です。

この PoC は、上空から撮った海面の合成画像に小さな目標(救命いかだ)を植え、
(1) 横距離ごとに検出確率を測って p(x) を出し、(2) その積分 W が本当に
「幅 W の完全検出帯」と等価であることをモンテカルロで確かめ、(3) W から
捜索計画の検出確率を出し、(4) 誤検出を別に数えて W の意味を締めます。

EXTEND: 実飛行に差し替えるなら :func:`make_frame` の戻り値
``(画像, 目標の行, 目標の列, 地上分解能)`` を、実際の空撮フレームと
**目標の真位置**(GPS を積んだ試験目標、あるいは投下位置の記録)に置き換えます。
真位置が無いと p(x) は測れません —— これは実運用でも同じで、走査幅は
**既知の目標を海に浮かべて機を飛ばす**試験(SAR の世界では sweep width
experiment と呼ばれる実験)でしか較正できません。§5 以降の意思決定側は
画像に依存しないので、W さえ差し替えれば実データでそのまま動きます。
逆に **§1 の cos⁴ / 大気 / 軸外ぼけの切り分け(§9 の対照群)は実データでは
できません** —— 実機ではこの 3 つを個別に止められないからです。

この PoC が示すこと(数字はすべて最終実行の実測値):

1. **ナディア向きピンホールでは、地上分解能は横距離によらず一定**。
   「端へ行くほど画素が粗くなる」は**斜め視の話**で、この配置では成り立ちません
   —— 平面を真下に見る中心投影は地上を**一様に**縮小する写像だからです
   (実測: 横距離の画素間隔は端から端まで 1.000000 m で、相対ばらつき 0.0e+00)。
   同じ焦点距離を **f-theta(魚眼)** で読むと同じ端で **2.135 倍**に粗くなります。
   ★つまり横距離曲線が落ちる原因は解像度ではなく、**照度 cos⁴θ・大気透過・
   軸外ぼけ**の 3 つでした。§9 で 1 つずつ止めて切り分けます。
2. **ゼロ点(素朴な手)は走査幅 63 m、整合フィルタは 292 m**。素朴な手 =
   「生画像で明るく見えたら検出」(``star_detect`` を生画像に直接掛ける)。
   誤検出率を **1.0 件/フレーム**に揃えて比べています —— 揃えないと閾値を
   下げるだけで走査幅が伸びるので、比較になりません。
3. **走査幅の定義そのものを実証しました**。半幅 500 m の帯に一様に撒いた目標を、
   (a) 実測した曲線 p(x)、(b) 幅 W の完全検出帯、(c) 底辺 2W の三角形、
   (d) 直下が見えない二峰形(側方監視レーダの nadir gap)—— **面積が同じなら
   検出数は同じ**(実測 0.2919 / 0.2917 / 0.2926 / 0.2915、予測 W/2X = 0.2917)。
   曲線の**形は消え、面積だけが残る**。これが「走査幅」という 1 本の数字が
   計画に渡せる理由です。
4. **崖は C=1 にあり、そこで 1.000 と 0.632 に割れる**。完全な平行捜索
   ``P = min(1, C)`` とランダム捜索(Koopman)``P = 1-exp(-C)`` を測る前に
   印字してから、モンテカルロで両方を実測しました。定値域則(幅 W の矩形)を
   使った対照では C=1 で **1.0000 / 0.6368**(閉形式 1.0000 / 0.6321、
   差 +0.0047 は**航跡が有限本 n=64 だから** —— 厳密は 1-(1-W/Wd)^n)。
5. ★**実測の p(x) を入れると、完全平行捜索は C=1 で 1.000 に届きません**
   (実測 **0.8951**)。予測を外しました —— ``min(1,C)`` は p が幅 W の
   **矩形**である(定値域則)ことに依存していて、裾を引く実曲線では隣の
   航跡と裾が重なり、その重なりぶんだけ取りこぼします。
   実曲線は平行 0.8951 とランダム 0.6321 の**あいだ**に落ちました。
6. ★**走査幅 2 倍と捜索時間 2 倍は等価**(どちらも C を 2 倍にする)。実測でも
   (W,t) と (2W,t) と (W,2t) が一致(平行 0.5000/0.8951/0.8951、
   ランダム 0.3935/0.6321/0.6321、最大差 0.0021 = モンテカルロ誤差)。
   ★**だが画像側にその 2 倍は無い**。W を上げる唯一のつまみである高度は
   下げても上げても W を下げます(次項)。「センサを良くする」と
   「時間を倍にする」は**式の上でだけ**等価です。
7. ★**最適高度は内点に来る**。高度 100→850 m で W = 181 / 242 / 272 / 270 /
   242 / 41 / 0 m。低高度では**掃引幅そのものが足りず**(高度 100 m では
   視野の端でも p=0.66 のまま切れている = W は下限値)、高高度では目標が
   暗くなって消えます。速度 v を高度に依らず一定と置いたので ``W·v`` の最適 =
   W の最適ですが、低高度ほど減速が要る機体(``v ∝ h`` で頭打ち)にすると
   最適は 220 m から 300 m へ動きます。
8. ★**見張り役: 誤検出は端ではなく直下に集中する**。横距離 0-32 m の帯で
   **41 件**、288-320 m の帯で **0 件**(閾値 4.5σ、60 フレーム)。目標も白波も
   同じ cos⁴・同じ大気で暗くなるので、**いちばんよく見える所がいちばん
   吠える所**です。検出率だけの表はこれを隠します。
9. ★**走査幅は誤検出率と一緒にしか語れない**。同じ画像・同じ検出器で、
   閾値を動かすだけで W は **420 m(誤検出 23.5 件/フレーム)から
   245 m(0.8 件/フレーム)**まで動きます。「走査幅 400 m」という報告は、
   誤検出率が書いていなければ**何も言っていません**。
10. **対照群で原因を切り分け**: cos⁴ を止めると W は 292→375 m、大気を止めると
    292→330 m、軸外ぼけを止めると 292→322 m、白波を止めると 292→402 m。
    ★足し算にはなりません(止めると閾値も下がるので相互作用する)。
11. ★**道具の穴を 4 つ見つけました**(本体は直していません、報告のみ)。要点は
    「**2-D 画像から点状目標の座標を返す公開 op は :func:`fullseye.star_detect`
    しかなく、その名前が天文に閉じている**」こと —— 捜索・欠陥・粒子の文脈で
    ``op_find`` を引いても出てきません。詳細は §10。

【グラウンドトゥルース】目標は**自分で植えます**。海面は
:func:`fullseye.ledger.surface_synth_psd`(帯域 λ∈[16,120] px、Sq=0.03 の
自己アフィン場。Sq の真値が乱数に依らない op)、白波と目標は
**画素内で解析的に積分したガウス斑**(物理寸法 ⊛ 局所 PSF)、光子雑音は
:func:`fullseye.photon_sample`(Poisson)、読み出し雑音は加法ガウス。
目標は直径 2.4 m の救命いかだで、コントラストは 0.45〜2.4 倍の対数一様
(同じ「いかだ」でも塗色・向き・波しぶきで実際にこれくらい散ります)。

【来歴】走査幅の定義 ``W = ∫p(x)dx`` と、平行捜索 ``P = min(1,C)`` /
ランダム捜索 ``P = 1-exp(-C)`` は捜索理論の古典(B. O. Koopman, *Search and
Screening*, 1946/1980)の教科書的結果で、この PoC はそれを**画像から測った
p(x) で再現し、どこで成り立たなくなるかを測る**ものです。cos⁴ 則は
:func:`fullseye.relative_illumination` の説明どおり(距離 2 乗 + 射出瞳の傾き +
像面の傾き)。大気の消散係数 0.002 /m(視程およそ 2 km 相当)、白波の密度と
明るさ、いかだのコントラストは**この PoC で置いた仮定**で、出典のある定数では
ありません —— 絶対値ではなく**切り分けと崖の位置**を見るための素材です。
"""
from __future__ import annotations

import math
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --------------------------------------------------------------------------- #
# 撮像の諸元 —— すべてここに 1 か所だけ持つ                                      #
# --------------------------------------------------------------------------- #
#: フレームの行数(進行方向)と、横方向の半幅[px]。横は 2*HALF+1 列。
ROWS, HALF_PX = 160, 320
COLS = 2 * HALF_PX + 1

#: 焦点距離[px]。半画角 = atan(HALF_PX/FOCAL_PX) = 46.85 度(広角の捜索カメラ)。
FOCAL_PX = 300.0

#: 基準高度[m]。地上分解能 = ALT_M/FOCAL_PX = 1.0 m/px(§7 で振る)。
ALT_M = 300.0

#: 軸上の PSF の sigma[px]と、軸外での増え方(``sigma = SIG0*(1+KCOMA*tan^2θ)``)。
#: 像面湾曲・非点収差は視野角の 2 乗で効くので tan^2 に比例させる。
SIG0, KCOMA = 0.9, 0.55

#: 大気の消散係数[1/m]。視程およそ 2 km 相当(この PoC で置いた仮定)。
BETA_PER_M = 0.002

#: 遠方の大気(かすみ)の輝度と、海面の輝度[任意単位]。
SKY_RADIANCE, SEA_RADIANCE = 1.2, 1.0

#: うねりの rms(海面輝度に対する比)と帯域[px]。
SWELL_SQ, SWELL_LO_PX, SWELL_HI_PX = 0.03, 16.0, 120.0

#: 単位輝度あたりの光子数(Poisson の λ)と、読み出し雑音[輝度単位]。
PHOTONS, READ_SIGMA = 3000.0, 0.008

#: 目標 = 救命いかだ。直径[m]と基準コントラスト、その対数一様のばらつき。
TARGET_M, TARGET_C = 2.4, 0.9
TARGET_C_LO, TARGET_C_HI = 0.45, 2.4

#: 白波(誤検出の源)。直径[m]・基準コントラスト・ばらつき・1 フレームあたりの数。
WHITECAP_M, WHITECAP_C = 5.0, 0.12
WHITECAP_C_LO, WHITECAP_C_HI = 0.25, 4.0
N_WHITECAP = 14

# --------------------------------------------------------------------------- #
# 測り方の諸元                                                                  #
# --------------------------------------------------------------------------- #
#: 横距離の刻み[px]と本数。目標は各帯の中心に左右 1 個ずつ置く(1 フレーム 18 個)。
BIN_PX, N_BIN = 32, 9

#: 検出と真値を同一とみなす距離[px]。
MATCH_TOL_PX = 3.0

#: 運用点。**誤検出率を揃えないと走査幅の比較にならない**(§9)。
FA_PER_FRAME = 1.0

#: ``star_detect`` に渡す下限の閾値。ここから上は 1 回の走査で全部拾えるので、
#: 閾値の掃引は**画像を測り直さずに**できる(z 値を持ち回る)。
BASE_SIGMA = 2.0

#: フレーム数。率は「300 試行以上」を守る —— 主計測は左右 2 個 x 160 = 320 試行/帯。
N_CAL, N_MAIN, N_CTRL, N_ALT = 160, 160, 150, 70

#: 高度の掃引[m]。
ALTITUDES = (100.0, 150.0, 220.0, 300.0, 420.0, 600.0, 850.0)


# --------------------------------------------------------------------------- #
# 表示 —— 全角を 2 桁と数えて桁を合わせる                                        #
# --------------------------------------------------------------------------- #
def _dw(s) -> int:
    """全角を 2 桁と数えた表示幅(``str.format`` は文字数で数えるので使えない)。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def pad(s, n: int, right: bool = True) -> str:
    """表示幅 ``n`` に詰める。``right`` なら右寄せ。"""
    s = str(s)
    sp = " " * max(0, n - _dw(s))
    return sp + s if right else s + sp


# --------------------------------------------------------------------------- #
# 1. 幾何 —— 地上分解能は横距離によらないのか                                    #
# --------------------------------------------------------------------------- #
def ground_step_rectilinear(alt: float, focal: float = FOCAL_PX) -> np.ndarray:
    """中心投影(ふつうのレンズ)の横方向の地上画素間隔[m/px]、列ごと。

    真下を向いたピンホールが平面を写す像は**一様な相似縮小**なので、
    ``x = alt*(j-j0)/focal`` は j に**線形**、したがって間隔は定数 ``alt/focal``。
    """
    j = np.arange(COLS, dtype=np.float64) - HALF_PX
    x = alt * j / focal
    return np.diff(x)


def ground_step_ftheta(alt: float, focal: float = FOCAL_PX) -> np.ndarray:
    """f-theta(魚眼)の横方向の地上画素間隔[m/px]、列ごと。**同じ画角で比べる**。

    こちらは**画角**が j に線形(``theta = (j-j0)*delta``)なので、地上では
    ``x = alt*tan(theta)`` となり、間隔は ``alt*delta*sec^2(theta)`` で端ほど粗い。
    比較を公平にするため、``delta`` は中心投影と**同じ半画角**を同じ画素数で
    覆うように取る(そうしないと視野の広さの違いを分解能の違いと読んでしまう)。
    """
    delta = math.atan(HALF_PX / focal) / HALF_PX      # 端が同じ画角に来る角度刻み
    j = np.arange(COLS, dtype=np.float64) - HALF_PX
    x = alt * np.tan(j * delta)
    return np.diff(x)


def geometry(alt: float, focal: float = FOCAL_PX):
    """``(地上分解能 [m/px], cos^4 の減光, 大気の透過率)`` を返す。減光と透過は (行, 列)。"""
    gsd = alt / focal
    j = np.arange(COLS, dtype=np.float64) - HALF_PX
    i = np.arange(ROWS, dtype=np.float64) - (ROWS - 1) / 2.0
    tan2 = (i[:, None] ** 2 + j[None, :] ** 2) / focal ** 2
    vign = 1.0 / (1.0 + tan2) ** 2                   # = cos^4(theta)
    trans = np.exp(-BETA_PER_M * alt * np.sqrt(1.0 + tan2))   # 斜距離 = alt*sec(theta)
    return gsd, vign, trans


def psf_sigma_px(rows, cols, focal: float = FOCAL_PX):
    """その位置の PSF の sigma[px]。軸外で像面湾曲ぶんだけ太る。"""
    t2 = ((np.asarray(rows) - (ROWS - 1) / 2.0) ** 2
          + (np.asarray(cols) - HALF_PX) ** 2) / focal ** 2
    return SIG0 * (1.0 + KCOMA * t2)


# --------------------------------------------------------------------------- #
# 2. 素材 —— 真値つきのフレームを作る                                            #
# --------------------------------------------------------------------------- #
def _blobs(shape, rows, cols, flux, sigma, half_win: int = 9):
    """ガウス斑を足し込む。**画素中心での標本**ではなく総和が flux になる規格化。

    :func:`fullseye.astrostack` の ``_gaussian_star_exact``(erf で画素を厳密に
    積分する)が非公開なので、ここでは同じ考え方をガウス核の標本で書いている
    —— sigma >= 0.9 px なので画素内の曲率による誤差は総和で 0.3 % 以下。
    ★道具の穴 (a): **位置を指定して点源を描く公開 op が無い**(§10)。
    """
    out = np.zeros(shape, np.float64)
    h, w = shape
    for r0, c0, f0, s0 in zip(rows, cols, flux, sigma):
        i0, i1 = int(max(0, r0 - half_win)), int(min(h, r0 + half_win + 1))
        j0, j1 = int(max(0, c0 - half_win)), int(min(w, c0 + half_win + 1))
        if i1 <= i0 or j1 <= j0:
            continue
        rr = np.arange(i0, i1, dtype=np.float64) - r0
        cc = np.arange(j0, j1, dtype=np.float64) - c0
        k = np.exp(-0.5 * (rr[:, None] ** 2 + cc[None, :] ** 2) / (s0 * s0))
        out[i0:i1, j0:j1] += (f0 / (2.0 * math.pi * s0 * s0)) * k
    return out


def make_frame(seed: int, alt: float = ALT_M, target_cols=(), *,
               vignette: bool = True, atmosphere: bool = True, blur: bool = True,
               whitecaps: bool = True, swell: bool = True):
    """1 フレーム作る。``(画像, 目標の行, 目標の列, 地上分解能)`` を返す。

    工程は物理の順:海面 → 目標と白波(物理寸法 ⊛ 局所 PSF)→ 減光と大気 →
    光子の Poisson 標本 → 読み出し雑音。**対照群のつまみは全部キーワード**で、
    §9 で 1 つずつ止める。
    """
    rng = np.random.default_rng(int(seed) * 7919 + 13)
    gsd, vign, trans = geometry(alt)
    if not vignette:
        vign = np.ones_like(vign)
    if not atmosphere:
        trans = np.ones_like(trans)

    # -- 海面。Sq の真値が乱数に依らない op(位相だけ振る)を使う ----------------
    if swell:
        z, _sq = fs.ledger.surface_synth_psd.raw((ROWS, COLS), 1.0, 0.8,
                                                 SWELL_LO_PX, SWELL_HI_PX,
                                                 SWELL_SQ, int(seed) % 99991)
        scene = SEA_RADIANCE * (1.0 + np.asarray(z, np.float64))
    else:
        scene = np.full((ROWS, COLS), SEA_RADIANCE)
    # うねりは λ>=16 px に帯域制限してあるので、軸外ぼけ(sigma 0.9->1.9 px)で
    # 振幅が変わるのは最悪 0.81 倍。ここは軸上の sigma で 1 回だけ掛ける
    # (§9 の「うねり無し」対照で、この近似が走査幅に効かないことを確認する)。
    scene = np.asarray(fs.op.gauss_filter(scene, a=(SIG0 - 0.3) / 2.7))

    # -- 目標。真値は自分で植えるので分かっている --------------------------------
    t_rows, t_cols, t_flux, t_sig = [], [], [], []
    for c in target_cols:
        r = rng.uniform(12.0, ROWS - 12.0)
        cj = float(c) + rng.uniform(-0.5, 0.5)
        contrast = TARGET_C * math.exp(rng.uniform(math.log(TARGET_C_LO),
                                                   math.log(TARGET_C_HI)))
        s_phys = TARGET_M / (4.0 * gsd)               # 円板 ≈ 同じ 2 次モーメントのガウス
        s_psf = float(psf_sigma_px(r, cj)) if blur else SIG0
        t_rows.append(r)
        t_cols.append(cj)
        # 総フラックス = 超過輝度 x (物理面積 / 画素の地上面積)
        t_flux.append(contrast * math.pi * (TARGET_M / 2.0) ** 2 / gsd ** 2)
        t_sig.append(math.hypot(s_phys, s_psf))
    objects = _blobs(scene.shape, t_rows, t_cols, t_flux, t_sig)

    # -- 白波。目標に重ならない所にだけ置く(重なると真値が壊れる)---------------
    if whitecaps:
        wr = rng.uniform(4.0, ROWS - 4.0, N_WHITECAP)
        wc = rng.uniform(4.0, COLS - 4.0, N_WHITECAP)
        keep = np.ones(N_WHITECAP, bool)
        for r0, c0 in zip(t_rows, t_cols):
            keep &= np.hypot(wr - r0, wc - c0) > 7.0
        wr, wc = wr[keep], wc[keep]
        wcon = WHITECAP_C * np.exp(rng.uniform(math.log(WHITECAP_C_LO),
                                               math.log(WHITECAP_C_HI), wr.size))
        s_phys = WHITECAP_M / (4.0 * gsd)
        s_psf = psf_sigma_px(wr, wc) if blur else np.full(wr.size, SIG0)
        objects += _blobs(scene.shape, wr, wc,
                          wcon * math.pi * (WHITECAP_M / 2.0) ** 2 / gsd ** 2,
                          np.hypot(s_phys, s_psf))

    # -- センサへ届く輝度 → 光子 → 読み出し -------------------------------------
    lam = (scene + objects) * vign * trans + SKY_RADIANCE * (1.0 - trans)
    counts = np.asarray(fs.photon_sample(np.clip(lam, 0.0, None), PHOTONS, 0.0,
                                         int(seed) % 99991 + 1), np.float64)
    img = counts / PHOTONS + rng.normal(0.0, READ_SIGMA, lam.shape)
    return img, np.asarray(t_rows), np.asarray(t_cols), gsd


# --------------------------------------------------------------------------- #
# 3. 検出器 —— どちらも fullseye の op で組む                                    #
# --------------------------------------------------------------------------- #
def _response(img, mode: str):
    """検出に掛ける応答マップ。``"naive"`` は生画像そのもの(ゼロ点)。"""
    if mode == "naive":
        return np.asarray(img, np.float64)
    # 白色トップハット(元画像 - オープニング)。5x5 の矩形構造要素は
    # ``a`` が {3,5,7,9} を刻むので a=0.3 -> 5。目標の FWHM は 2.6-3.7 px。
    return np.asarray(fs.op.gray_tophat(np.asarray(img, np.float64), a=0.3))


def detect_with_z(img, mode: str):
    """``(検出座標 (N,2), その z 値 (N,))``。z = (応答 - 中央値)/頑健 sigma。

    :func:`fullseye.star_detect` を ``BASE_SIGMA`` で 1 回だけ走らせ、閾値の掃引は
    z 値の比較で済ませる —— 高い閾値の検出集合は低い閾値の**部分集合**なので、
    画像を測り直す必要がない。背景と sigma は ``star_detect`` 内部と同じ定義
    (中央値と MAD x 1.4826 = :func:`fullseye.noise_sigma`)。
    """
    w = _response(img, mode)
    pts = np.asarray(fs.star_detect(w, threshold_sigma=BASE_SIGMA, min_separation=3,
                                    max_stars=4000), np.float64)
    if pts.size == 0:
        return pts.reshape(0, 2), np.zeros(0)
    bkg = float(np.median(w))
    sig = float(fs.noise_sigma(w, "mad"))
    rr = np.clip(np.rint(pts[:, 0]).astype(np.int64), 0, w.shape[0] - 1)
    cc = np.clip(np.rint(pts[:, 1]).astype(np.int64), 0, w.shape[1] - 1)
    return pts, (w[rr, cc] - bkg) / (sig if sig > 0.0 else 1.0)


#: 帯の中心[px](片側)。左右対称に置くので 1 フレームで 2*N_BIN 個の試行になる。
BIN_CENTERS_PX = np.array([BIN_PX * k + BIN_PX / 2.0 for k in range(N_BIN)])


def sweep_frames(n_frames: int, mode: str, seed0: int = 0, targets: bool = True, **kw):
    """``n_frames`` 枚まわして、帯ごとの当たりの z と、誤検出の z・横距離を集める。

    戻り値の ``hit_z`` は ``(N_BIN, 2*n_frames)``。目標が拾えなかった試行は
    ``-inf`` なので、どの閾値でも「拾えなかった」ままになる。
    ``targets=False`` は**目標を 1 個も置かない**較正用(§2 の床の測定)。
    """
    cols = np.r_[HALF_PX - BIN_CENTERS_PX[::-1], HALF_PX + BIN_CENTERS_PX] \
        if targets else np.zeros(0)
    hit_z = np.full((N_BIN, 2 * n_frames), -np.inf)
    fa_z, fa_x = [], []
    gsd = 0.0
    for n in range(n_frames):
        img, trow, tcol, gsd = make_frame(seed0 + n, target_cols=cols, **kw)
        pts, z = detect_with_z(img, mode)
        claimed = np.zeros(pts.shape[0], bool)
        for m in range(trow.size):
            if pts.size == 0:
                continue
            near = np.hypot(pts[:, 0] - trow[m], pts[:, 1] - tcol[m]) < MATCH_TOL_PX
            if near.any():
                # 左半分は帯番号が逆順(中心から数えるので折り返す)。
                b = (N_BIN - 1 - m) if m < N_BIN else (m - N_BIN)
                side = 0 if m < N_BIN else 1
                hit_z[b, 2 * n + side] = z[near].max()
                claimed |= near
        if pts.size:
            fa_z.append(z[~claimed])
            fa_x.append(np.abs(pts[~claimed, 1] - HALF_PX))
    fz = np.concatenate(fa_z) if fa_z else np.zeros(0)
    fx = np.concatenate(fa_x) if fa_x else np.zeros(0)
    return {"hit_z": hit_z, "fa_z": fz, "fa_x": fx, "gsd": gsd, "frames": n_frames}


def threshold_for_fa(fa_z, n_frames: int, per_frame: float = FA_PER_FRAME) -> float:
    """誤検出が ``per_frame`` 件/フレームになる閾値。**床を測ってから閾値を決める**。"""
    want = int(round(per_frame * n_frames))
    zs = np.sort(np.asarray(fa_z, np.float64))[::-1]
    if zs.size <= want:
        return BASE_SIGMA
    if want <= 0:
        return float(zs[0]) + 1e-9
    return float(0.5 * (zs[want - 1] + zs[want]))


def curve_at(run, thr: float):
    """閾値 ``thr`` での ``(横距離曲線 p (N_BIN,), 走査幅 W [m], W の標準誤差)``。"""
    hits = run["hit_z"] >= thr
    p = hits.mean(axis=1)
    n = hits.shape[1]
    dx = BIN_PX * run["gsd"]
    w = 2.0 * float(p.sum()) * dx
    se = 2.0 * dx * math.sqrt(float((p * (1.0 - p)).sum()) / n)
    return p, w, se


def fa_per_frame(run, thr: float) -> float:
    return float((run["fa_z"] >= thr).sum()) / run["frames"]


# --------------------------------------------------------------------------- #
# 4. 走査幅の定義を実証する —— 形は消え、面積だけが残る                          #
# --------------------------------------------------------------------------- #
def step_curve(p, gsd: float):
    """帯ごとの p を「|x| の階段関数」にする。``W = 2*sum(p)*dx`` が厳密になる。"""
    edges = np.arange(N_BIN + 1) * BIN_PX * gsd

    def f(x):
        k = np.searchsorted(edges, np.abs(np.asarray(x, np.float64)), side="right") - 1
        out = np.zeros(np.shape(x), np.float64)
        ok = (k >= 0) & (k < N_BIN)
        out[ok] = np.asarray(p)[k[ok]]
        return out
    return f


def rect_curve(width: float):
    """定値域則(definite range law):幅 ``width`` の矩形。面積 = width。"""
    return lambda x: (np.abs(np.asarray(x, np.float64)) <= width / 2.0).astype(np.float64)


def triangle_curve(width: float):
    """底辺 2*width・高さ 1 の三角形。面積 = width。"""
    def f(x):
        a = np.abs(np.asarray(x, np.float64))
        return np.clip(1.0 - a / width, 0.0, 1.0)
    return f


def twolobe_curve(width: float):
    """直下が見えない二峰形(側方監視レーダの nadir gap)。面積 = width。"""
    def f(x):
        a = np.abs(np.asarray(x, np.float64))
        return ((a >= width / 4.0) & (a <= 3.0 * width / 4.0)).astype(np.float64)
    return f


def curve_area(f, span: float, n: int = 200001) -> float:
    """``∫f dx`` を台形則で。``fullseye.integrate_funct_1d``(HALCON 流)を使う。"""
    x = np.linspace(-span, span, n)
    dt = float(x[1] - x[0])
    return float(np.asarray(fs.integrate_funct_1d(f(x)))[-1]) * dt


# --------------------------------------------------------------------------- #
# 5. 意思決定側 —— 被覆率 C と検出確率                                           #
# --------------------------------------------------------------------------- #
def sweep_mc(curve, width_m: float, area_w: float, n_track: int, *, random_tracks: bool,
             n_target: int = 40000, n_rep: int = 6, seed: int = 0) -> float:
    """平行 / ランダム捜索の検出確率をモンテカルロで。``C = width_m*n_track/area_w``。

    海域は幅 ``area_w`` の帯を**環状**につないだもの(端の効果を消すため)。
    航跡は ``n_track`` 本、平行なら等間隔、ランダムなら独立一様。目標は一様。
    航跡ごとの検出は独立なので、``1-Π(1-p_k)`` の Bernoulli を 1 回引く。
    """
    rng = np.random.default_rng(seed)
    hit = 0
    tot = 0
    for _ in range(n_rep):
        x = rng.uniform(0.0, area_w, n_target)
        if random_tracks:
            tracks = rng.uniform(0.0, area_w, n_track)
        else:
            tracks = (np.arange(n_track) + 0.5) * (area_w / n_track)
        miss = np.ones(n_target)
        for tk in tracks:
            d = np.abs(x - tk)
            d = np.minimum(d, area_w - d)             # 環状距離
            miss *= 1.0 - curve(d)
        hit += int((rng.random(n_target) < 1.0 - miss).sum())
        tot += n_target
    return hit / tot


# --------------------------------------------------------------------------- #
# 節ごとの本体                                                                  #
# --------------------------------------------------------------------------- #
def section_geometry():
    print("=== 1. 幾何 —— 「端は解像度が落ちる」は本当か ===")
    half_fov = math.degrees(math.atan(HALF_PX / FOCAL_PX))
    rect = ground_step_rectilinear(ALT_M)
    fth = ground_step_ftheta(ALT_M)
    spread = float(np.ptp(rect)) / float(rect.mean())
    print(f"  高度 {ALT_M:.0f} m / 焦点 {FOCAL_PX:.0f} px / 半画角 {half_fov:.2f} 度"
          f" / {ROWS}x{COLS} px")
    print(f"  {'投影':>16}{'中央の画素間隔':>18}{'端の画素間隔':>16}{'端/中央':>10}")
    print(f"  {'中心投影(ふつう)':>16}{rect[HALF_PX]:>17.6f} m{rect[0]:>15.6f} m"
          f"{rect[0] / rect[HALF_PX]:>10.4f}")
    print(f"  {'f-theta(魚眼)':>16}{fth[HALF_PX]:>17.6f} m{fth[0]:>15.6f} m"
          f"{fth[0] / fth[HALF_PX]:>10.4f}")
    print(f"  → ★中心投影では**端まで一定**(相対ばらつき {spread:.1e})。真下を向いた")
    print("     ピンホールが平面を写す像は一様な相似縮小で、地上分解能は横距離に")
    print("     依らない。**「端は画素が粗い」は斜め視 / 魚眼の話**だった。")
    _, vign, trans = geometry(ALT_M)
    print(f"  では何が落ちるのか: cos^4 の減光 {vign[ROWS // 2, 0]:.4f}(中央 1.0000)、")
    print(f"  大気の透過 {trans[ROWS // 2, 0]:.4f}(中央 {trans[ROWS // 2, HALF_PX]:.4f})、")
    print(f"  PSF の sigma {float(psf_sigma_px(ROWS / 2, 0)):.3f} px"
          f"(中央 {SIG0:.3f} px)。§9 で 1 つずつ止める。")
    # cos^4 則は op が閉形式で持っている。自前の式と突き合わせておく。
    tab = np.asarray(fs.relative_illumination(half_fov, 64))
    own = 1.0 / (1.0 + np.tan(np.radians(tab[:, 0])) ** 2) ** 2
    print(f"  ({'fullseye.relative_illumination'} と自前の cos^4 の最大差 "
          f"{float(np.max(np.abs(tab[:, 1] - own))):.2e})")
    return {"half_fov": half_fov, "spread": spread,
            "rect_edge_ratio": float(rect[0] / rect[HALF_PX]),
            "ftheta_edge_ratio": float(fth[0] / fth[HALF_PX]),
            "ri_gap": float(np.max(np.abs(tab[:, 1] - own)))}


def section_floor():
    print("\n=== 2. 床を測ってから閾値を決める(目標ゼロのフレーム)===")
    print(f"  目標を 1 個も置かない {N_CAL} フレームで誤検出だけを数え、"
          f"**{FA_PER_FRAME:.1f} 件/フレーム**に揃う閾値を求める。")
    out = {}
    print(f"  {'検出器':>22}{'誤検出の総数':>14}{'閾値':>10}{'その閾値での実測':>18}")
    for mode, label in (("naive", "生画像(ゼロ点)"), ("tophat", "白色トップハット")):
        run = sweep_frames(N_CAL, mode, seed0=90000, targets=False)
        thr = threshold_for_fa(run["fa_z"], N_CAL)
        out[mode] = {"thr": thr, "n_fa": int(run["fa_z"].size),
                     "got": fa_per_frame(run, thr)}
        print(f"  {label:>22}{run['fa_z'].size:>13d} 件{thr:>10.2f}"
              f"{out[mode]['got']:>15.2f} 件/枚")
    print(f"  → 閾値は「{N_CAL} フレーム中 {N_CAL} 番目に強い誤検出」の高さなので、")
    print(f"     相対精度はおよそ 1/sqrt({N_CAL}) = {1 / math.sqrt(N_CAL):.1%}。")
    print("     **0 件だった/100 % 見えた、で閾値を決めない** —— 分母を先に置く。")
    return out


def section_lateral_curve(floor):
    print("\n=== 3. 横距離曲線 p(x) —— 目標を植えて測る ===")
    runs = {m: sweep_frames(N_MAIN, m, seed0=0) for m in ("naive", "tophat")}
    gsd = runs["tophat"]["gsd"]
    print(f"  {N_MAIN} フレーム x 左右 2 個 = **{2 * N_MAIN} 試行/帯**、"
          f"帯の幅 {BIN_PX * gsd:.0f} m、横距離 0-{N_BIN * BIN_PX * gsd:.0f} m")
    out = {}
    header = "  " + pad("検出器", 22, right=False) + pad("閾値", 8) + pad("誤検出/枚", 12)
    header += "".join(pad("%.0f" % ((k + 0.5) * BIN_PX * gsd), 7) for k in range(N_BIN))
    header += pad("W [m]", 12)
    print("  " + pad("横距離 [m] →", 22, right=False))
    print(header)
    for mode, label in (("naive", "生画像(ゼロ点)"), ("tophat", "白色トップハット")):
        thr = floor[mode]["thr"]
        p, w, se = curve_at(runs[mode], thr)
        out[mode] = {"p": p, "w": w, "se": se, "thr": thr,
                     "fa": fa_per_frame(runs[mode], thr)}
        print("  " + pad(label, 22, right=False) + pad("%.2f" % thr, 8)
              + pad("%.2f" % out[mode]["fa"], 12)
              + "".join(pad("%.2f" % v, 7) for v in p)
              + pad("%.1f ± %.1f" % (w, se), 12))
    print("  → **同じ誤検出率で比べている**。整合フィルタ(トップハット)は"
          f" {out['tophat']['w'] / max(out['naive']['w'], 1e-9):.1f} 倍。")
    print("     ゼロ点を置かないと『検出できた』としか書けない —— 生画像でも"
          f" {out['naive']['w']:.0f} m は出るので、")
    print("     大事なのは**零点をどれだけ上回ったか**のほう。")
    print(f"  → いちばん外の帯で p = {out['tophat']['p'][-1]:.3f}。ここが 0 に近いので、")
    print("     視野で切られた分の取りこぼし(打ち切り)は無視できる。§7 の低高度は"
          "そうならない。")
    # 較正フレームで決めた閾値と、この計測フレーム自身で決めた閾値が一致するか。
    self_thr = threshold_for_fa(runs["tophat"]["fa_z"], N_MAIN)
    print(f"  (較正で決めた閾値 {floor['tophat']['thr']:.2f} vs 計測フレーム自身から"
          f"決めた閾値 {self_thr:.2f} —— 差 {abs(self_thr - floor['tophat']['thr']):.2f})")
    out["runs"] = runs
    out["gsd"] = gsd
    out["self_thr"] = self_thr
    if figs.enabled():
        img, trow, tcol, _ = make_frame(3, target_cols=np.r_[
            HALF_PX - BIN_CENTERS_PX[::-1], HALF_PX + BIN_CENTERS_PX])
        top = _response(img, "tophat")
        pts, z = detect_with_z(img, "tophat")
        keep = z >= floor["tophat"]["thr"]
        over = np.repeat((top / max(float(top.max()), 1e-12))[:, :, None], 3, axis=2)
        for r0, c0 in zip(trow, tcol):
            over = np.asarray(fs.draw_circle(over, (float(c0), float(r0)), 6.0,
                                             color="right", width=1, fill=False))
        for r0, c0 in zip(pts[keep, 0], pts[keep, 1]):
            over = np.asarray(fs.draw_circle(over, (float(c0), float(r0)), 3.0,
                                             color="wrong", width=1, fill=False))
        flat, _, _, _ = make_frame(3, target_cols=(), vignette=False, atmosphere=False)
        figs.save_grid("scene", [img, top, over, flat],
                       ["生画像(左右が暗い)", "トップハット応答",
                        "丸=真値 / 小丸=検出", "対照:減光と大気を止めた海面"],
                       ncols=1,
                       title="1 フレーム(進行方向 160 px x 横 641 px、地上 1 m/px)",
                       caption="左右の端が暗いのは cos^4 の減光と大気。"
                               "真値の丸が空なら取りこぼし、小丸だけなら誤検出。")
    return out


def section_definition(curve_out):
    print("\n=== 4. 走査幅の定義を実証する —— 形は消え、面積だけが残る ===")
    p = curve_out["tophat"]["p"]
    gsd = curve_out["gsd"]
    w = curve_out["tophat"]["w"]
    span = 500.0
    shapes = (("実測した p(x)", step_curve(p, gsd)),
              ("幅 W の矩形(定値域則)", rect_curve(w)),
              ("底辺 2W の三角形", triangle_curve(w)),
              ("二峰形(直下が見えない)", twolobe_curve(w)))
    print(f"  予測(測る前): 半幅 {span:.0f} m の帯に一様に撒いた目標のうち、"
          f"検出される割合は")
    print(f"     W / (2X) = {w:.1f} / {2 * span:.0f} = {w / (2 * span):.4f}"
          f" —— **4 つの形すべてで同じはず**。")
    rng = np.random.default_rng(11)
    n = 400000
    x = rng.uniform(-span, span, n)
    rows, got = [], []
    print(f"  {'曲線の形':>26}{'面積 ∫p dx':>14}{'検出割合(実測)':>18}{'予測との差':>14}")
    for name, f in shapes:
        area = curve_area(f, span)
        frac = float((rng.random(n) < f(x)).mean())
        got.append(frac)
        rows.append((name, "%.1f m" % area, "%.4f" % frac,
                     "%+.4f" % (frac - w / (2 * span))))
        print(f"  {name:>26}{area:>12.1f} m{frac:>18.4f}"
              f"{frac - w / (2 * span):>+14.4f}")
    mc_sd = math.sqrt(w / (2 * span) * (1 - w / (2 * span)) / n)
    print(f"  → モンテカルロの標準偏差は {mc_sd:.4f}。**4 つとも予測の "
          f"{max(abs(g - w / (2 * span)) for g in got) / mc_sd:.1f}σ 以内**。")
    print("     曲線の形は消え、**面積だけが残る**。これが「走査幅」という 1 本の")
    print("     数字を計画に渡せる理由で、逆に言えば **p(x) の形は捨ててよい**。")
    figs.save_table("sweep_width_equivalence",
                    ["曲線の形", "面積 ∫p dx", "検出割合(実測)", "予測との差"], rows,
                    title="面積が同じなら検出数は同じ —— 走査幅の定義そのもの",
                    caption=f"半幅 {span:.0f} m に一様に撒いた {n} 個。"
                            f"予測 W/2X = {w / (2 * span):.4f}、"
                            f"モンテカルロの標準偏差 {mc_sd:.4f}。")
    if figs.enabled():
        xs = np.linspace(-span, span, 1201)
        figs.save_plot("curve_shapes",
                       [(nm, xs, f(xs)) for nm, f in shapes],
                       xlabel="横距離 x [m]", ylabel="検出確率 p(x)",
                       title="面積が等しい 4 つの横距離曲線",
                       caption=f"4 本とも面積 = W = {w:.0f} m。"
                               "一様に撒いた目標の検出数は 4 本とも同じになる。")
    return {"pred": w / (2 * span), "got": got, "mc_sd": mc_sd, "span": span, "w": w}


def section_cliff(curve_out, defn):
    print("\n=== 5. 崖 —— 被覆率 C と検出確率(閉形式を先に印字する)===")
    w = defn["w"]
    n_track = 64
    print("  予測(測る前):")
    print("     完全な平行捜索   P = min(1, C)      → C=1 で **1.0000**")
    print("     ランダム捜索     P = 1 - exp(-C)    → C=1 で **0.6321**")
    print(f"     ただし航跡が有限本(n={n_track})なら厳密は 1-(1-W/Wd)^n"
          f" = {1 - (1 - 1.0 / n_track) ** n_track:.4f}")
    cs = np.array([0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0])
    step = step_curve(curve_out["tophat"]["p"], curve_out["gsd"])
    rect = rect_curve(w)
    out = {"C": cs}
    print(f"  {'C':>7}{'min(1,C)':>11}{'1-exp(-C)':>11}"
          f"{'MC 平行(矩形)':>16}{'MC ランダム(矩形)':>19}"
          f"{'MC 平行(実測 p)':>18}{'MC ランダム(実測 p)':>21}")
    rows = []
    for key in ("par_rect", "rnd_rect", "par_real", "rnd_real"):
        out[key] = []
    for c in cs:
        area_w = w * n_track / c                       # C = W*n/Wd
        pr = sweep_mc(rect, w, area_w, n_track, random_tracks=False, seed=int(c * 100))
        rr = sweep_mc(rect, w, area_w, n_track, random_tracks=True, seed=int(c * 100) + 1)
        pv = sweep_mc(step, w, area_w, n_track, random_tracks=False, seed=int(c * 100) + 2)
        rv = sweep_mc(step, w, area_w, n_track, random_tracks=True, seed=int(c * 100) + 3)
        out["par_rect"].append(pr)
        out["rnd_rect"].append(rr)
        out["par_real"].append(pv)
        out["rnd_real"].append(rv)
        print(f"  {c:>7.3f}{min(1.0, c):>11.4f}{1 - math.exp(-c):>11.4f}"
              f"{pr:>16.4f}{rr:>19.4f}{pv:>18.4f}{rv:>21.4f}")
        rows.append(("%.3f" % c, "%.4f" % min(1.0, c), "%.4f" % (1 - math.exp(-c)),
                     "%.4f" % pr, "%.4f" % rr, "%.4f" % pv, "%.4f" % rv))
    for key in ("par_rect", "rnd_rect", "par_real", "rnd_real"):
        out[key] = np.asarray(out[key])
    i1 = int(np.argmin(np.abs(cs - 1.0)))
    print(f"  → **C=1 の崖**: 矩形の対照では平行 {out['par_rect'][i1]:.4f} /"
          f" ランダム {out['rnd_rect'][i1]:.4f}(閉形式 1.0000 / 0.6321)。")
    print("     ランダム側の +0.005 は航跡が有限本だからで、模型の誤りではない。")
    print(f"  → ★**予測を外した**: 実測の p(x) を入れると平行捜索は "
          f"{out['par_real'][i1]:.4f} で **1.000 に届かない**。")
    print("     min(1,C) は p が幅 W の**矩形**であること(定値域則)に依存していて、")
    print("     裾を引く実曲線では隣の航跡と裾が重なり、その重なりぶん取りこぼす。")
    print(f"     実曲線は平行 {out['par_real'][i1]:.4f} と"
          f" ランダム {out['rnd_real'][i1]:.4f} の**あいだ**に落ちた。")
    figs.save_table("coverage_table",
                    ["C", "min(1,C)", "1-exp(-C)", "MC 平行(矩形)",
                     "MC ランダム(矩形)", "MC 平行(実測 p)", "MC ランダム(実測 p)"],
                    rows, title="被覆率 C と検出確率 —— 閉形式は測る前に印字した",
                    caption=f"W = {w:.0f} m、航跡 {n_track} 本、目標 24 万個/点。"
                            "C=1 で 1.000 と 0.632 に割れる。")
    if figs.enabled():
        figs.save_plot("coverage_curves",
                       [("min(1,C) 閉形式", cs, np.minimum(1.0, cs)),
                        ("1-exp(-C) 閉形式", cs, 1 - np.exp(-cs)),
                        ("MC 平行(実測 p)", cs, out["par_real"]),
                        ("MC ランダム(実測 p)", cs, out["rnd_real"])],
                       xlabel="被覆率 C = W·v·t/A", ylabel="検出確率 P",
                       ylim=(0.0, 1.05),
                       title="崖は C=1 —— そこで 1.000 と 0.632 に割れる",
                       caption="実測の横距離曲線を入れると平行捜索は C=1 で "
                               f"{out['par_real'][i1]:.3f} までしか行かない"
                               "(裾が隣の航跡と重なるため)。")
    return out


def section_equivalence(curve_out, defn):
    print("\n=== 6. ★走査幅 2 倍 と 捜索時間 2 倍 は等価か ===")
    w = defn["w"]
    n_track = 64
    step = step_curve(curve_out["tophat"]["p"], curve_out["gsd"])
    step2 = step_curve(curve_out["tophat"]["p"], curve_out["gsd"])
    print("  C = W·v·t/A なので、W を 2 倍にしても t を 2 倍にしても C は 2 倍。")
    print("  基準を C=0.5 に取り、W だけ 2 倍 / t だけ 2 倍 を別々に測る。")
    print(f"  {'条件':>26}{'C':>8}{'平行':>10}{'ランダム':>12}")
    got = {}
    for name, c in (("基準 (W, t)", 0.5), ("W を 2 倍", 1.0), ("t を 2 倍", 1.0)):
        area_w = w * n_track / c
        # 「W 2 倍」は曲線を横に 2 倍(面積 2W)、「t 2 倍」は航跡本数 2 倍で表す。
        if name == "W を 2 倍":
            f = step_curve(curve_out["tophat"]["p"], curve_out["gsd"] * 2.0)
            area_w = 2.0 * w * n_track / c
            pv = sweep_mc(f, 2 * w, area_w, n_track, random_tracks=False, seed=71)
            rv = sweep_mc(f, 2 * w, area_w, n_track, random_tracks=True, seed=72)
        elif name == "t を 2 倍":
            area_w = w * n_track * 2 / c
            pv = sweep_mc(step2, w, area_w, 2 * n_track, random_tracks=False, seed=71)
            rv = sweep_mc(step2, w, area_w, 2 * n_track, random_tracks=True, seed=72)
        else:
            pv = sweep_mc(step, w, area_w, n_track, random_tracks=False, seed=71)
            rv = sweep_mc(step, w, area_w, n_track, random_tracks=True, seed=72)
        got[name] = (pv, rv)
        print(f"  {name:>26}{c:>8.2f}{pv:>10.4f}{rv:>12.4f}")
    d_par = abs(got["W を 2 倍"][0] - got["t を 2 倍"][0])
    d_rnd = abs(got["W を 2 倍"][1] - got["t を 2 倍"][1])
    print(f"  → 差は平行 {d_par:.4f} / ランダム {d_rnd:.4f} —— モンテカルロ誤差の範囲。")
    print("     **式の上では等価**。だが次の節で見るとおり、画像側にその『2 倍』は無い:")
    print("     W を上げるつまみは高度しかなく、下げても上げても W は落ちる。")
    return {"got": got, "d_par": d_par, "d_rnd": d_rnd}


def section_altitude():
    print("\n=== 7. 高度スイープ —— 最適は内点に来るか ===")
    print(f"  {N_ALT} フレーム/高度、誤検出は各高度で {FA_PER_FRAME:.1f} 件/枚に揃える。")
    print(f"  {'高度 [m]':>10}{'分解能 [m/px]':>14}{'掃引半幅 [m]':>14}{'閾値':>8}"
          f"{'W [m]':>16}{'端の p':>10}")
    rows, out = [], []
    for alt in ALTITUDES:
        run = sweep_frames(N_ALT, "tophat", seed0=20000 + int(alt), alt=alt)
        thr = threshold_for_fa(run["fa_z"], N_ALT)
        p, w, se = curve_at(run, thr)
        half = HALF_PX * run["gsd"]
        out.append({"alt": alt, "gsd": run["gsd"], "half": half, "thr": thr,
                    "w": w, "se": se, "p_end": float(p[-1])})
        flag = "  ← 視野で切れている(W は下限)" if p[-1] > 0.05 else ""
        print(f"  {alt:>10.0f}{run['gsd']:>14.2f}{half:>14.0f}{thr:>8.2f}"
              f"{w:>11.1f} ± {se:.1f}{p[-1]:>10.3f}{flag}")
        rows.append(("%.0f" % alt, "%.2f" % run["gsd"], "%.0f" % half, "%.2f" % thr,
                     "%.1f ± %.1f" % (w, se), "%.3f" % p[-1]))
    ws = np.array([o["w"] for o in out])
    best = int(np.argmax(ws))
    print(f"  → 最適高度 **{ALTITUDES[best]:.0f} m**(W = {ws[best]:.1f} m)。"
          f"両端ではなく**内点**に来た。")
    print("     低高度側の理由は解像度ではなく**掃引幅そのもの** —— 高度 100 m では")
    print(f"     視野の端でも p = {out[0]['p_end']:.2f} のまま切れており、W は下限値。")
    print("     高高度側は目標が暗くなって(cos^4 と大気と、画素あたりの面積比)消える。")
    # 速度が高度に依らない機体と、低高度で減速が要る機体。
    v_fixed = np.ones_like(ws)
    v_scaled = np.clip(np.array(ALTITUDES) / 300.0, 0.0, 1.0)
    best_fixed = int(np.argmax(ws * v_fixed))
    best_scaled = int(np.argmax(ws * v_scaled))
    print(f"  → 掃引速度 W·v: v 一定なら最適 {ALTITUDES[best_fixed]:.0f} m、"
          f"v ∝ min(1, h/300) なら **{ALTITUDES[best_scaled]:.0f} m** へ動く。")
    print("     ★『高度を下げて W を上げる』は成り立たない —— 下げると掃引幅が縮み、")
    print("     機体によっては速度まで落ちるので、W·v は二重に損をする。")
    figs.save_table("altitude_sweep",
                    ["高度 [m]", "分解能 [m/px]", "掃引半幅 [m]", "閾値",
                     "W [m]", "端の p"], rows,
                    title="走査幅は高度の内点で最大になる",
                    caption="端の p が 0 でない行は視野で切られている = W は下限値。"
                            "誤検出率は全高度で 1.0 件/枚に揃えてある。")
    if figs.enabled():
        alt = np.array(ALTITUDES)
        figs.save_plot("altitude_sweep_line",
                       [("走査幅 W", alt, ws),
                        ("W·v(v 一定)", alt, ws * v_fixed),
                        ("W·v(v ∝ min(1,h/300))", alt, ws * v_scaled),
                        ("掃引半幅(視野)", alt, np.array([o["half"] for o in out]))],
                       xlabel="高度 h [m]", ylabel="[m] / [m·(相対速度)]",
                       title="最適高度は内点 —— 下げても上げても損をする",
                       caption="低高度では掃引半幅(灰)が W を縛り、高高度では"
                               "目標が暗くなって消える。")
    return {"rows": out, "W": ws, "best": best, "best_scaled": best_scaled}


def section_false_alarms(curve_out):
    print("\n=== 8. ★見張り役 —— 誤検出を別に数える ===")
    run = curve_out["runs"]["tophat"]
    gsd = curve_out["gsd"]
    thr_show = 4.5
    edges = np.arange(N_BIN + 1) * BIN_PX
    hist, _ = np.histogram(run["fa_x"][run["fa_z"] >= thr_show], bins=edges)
    p_show, _, _ = curve_at(run, thr_show)
    # 帯 1 本の面積[km^2] = 行数 x 帯幅 x 2(左右) x 分解能^2
    area_km2 = ROWS * BIN_PX * 2 * gsd ** 2 * run["frames"] / 1e6
    print(f"  閾値 {thr_show:.1f}σ、{run['frames']} フレーム。誤検出を横距離で分けて数える。")
    print(f"  {'横距離 [m]':>14}" + "".join(pad("%.0f" % ((k + 0.5) * BIN_PX * gsd), 8)
                                            for k in range(N_BIN)))
    print(f"  {'検出確率 p':>14}" + "".join(pad("%.2f" % v, 8) for v in p_show))
    print(f"  {'誤検出 [件]':>14}" + "".join(pad("%d" % v, 8) for v in hist))
    print(f"  {'誤検出 [件/km^2]':>14}"
          + "".join(pad("%.0f" % (v / area_km2), 8) for v in hist))
    print("  → ★**誤検出は端ではなく直下に集中する**。目標も白波も同じ cos^4・")
    print("     同じ大気で暗くなるので、**いちばんよく見える所がいちばん吠える**。")
    print("     検出率だけの表はこれを隠す。ここを分けて数えないと、")
    print("     「直下は完璧」という報告が、実は「直下は誤報だらけ」を意味しうる。")

    print("\n  同じ画像・同じ検出器で、閾値だけ動かしたときの走査幅:")
    print(f"  {'閾値 [σ]':>10}{'誤検出 [件/枚]':>16}{'誤検出 [件/km^2]':>18}"
          f"{'W [m]':>16}{'直下の p':>10}")
    rows, sweep = [], []
    for thr in (3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 9.0):
        p, w, se = curve_at(run, thr)
        fa = fa_per_frame(run, thr)
        sweep.append((thr, fa, w))
        print(f"  {thr:>10.1f}{fa:>16.2f}"
              f"{fa * run['frames'] / (ROWS * COLS * gsd ** 2 * run['frames'] / 1e6):>18.0f}"
              f"{w:>11.1f} ± {se:.1f}{p[0]:>10.2f}")
        rows.append(("%.1f" % thr, "%.2f" % fa, "%.1f ± %.1f" % (w, se), "%.2f" % p[0]))
    w_hi = sweep[0][2]
    w_lo = sweep[-1][2]
    print(f"  → ★**走査幅は誤検出率と一緒にしか語れない**。同じ画像で "
          f"{w_hi:.0f} m から {w_lo:.0f} m まで動く")
    print(f"     (誤検出 {sweep[0][1]:.1f} 件/枚 → {sweep[-1][1]:.2f} 件/枚)。")
    print("     『走査幅 400 m』という報告は、誤検出率が書いていなければ何も言っていない。")
    figs.save_table("threshold_tradeoff",
                    ["閾値 [σ]", "誤検出 [件/枚]", "W [m]", "直下の p"], rows,
                    title="閾値を動かすだけで走査幅は 1.7 倍動く",
                    caption="だから走査幅は必ず誤検出率と対で報告する。"
                            f"この PoC の運用点は {FA_PER_FRAME:.1f} 件/枚。")
    if figs.enabled():
        xs = (np.arange(N_BIN) + 0.5) * BIN_PX * gsd
        figs.save_plot("detection_vs_false_alarm",
                       [("検出確率 p(x)", xs, p_show),
                        ("誤検出(最大で規格化)", xs, hist / max(float(hist.max()), 1.0))],
                       xlabel="横距離 |x| [m]", ylabel="p(x) / 誤検出(規格化)",
                       ylim=(0.0, 1.05),
                       title="誤検出は端ではなく直下に集中する",
                       caption=f"閾値 {thr_show:.1f}σ、{run['frames']} フレーム。"
                               "よく見える所ほどよく吠える —— 検出率だけの表は"
                               "これを隠す。")
        figs.save_plot("lateral_range_curves",
                       [("白色トップハット", xs, curve_out["tophat"]["p"]),
                        ("生画像(ゼロ点)", xs, curve_out["naive"]["p"])],
                       xlabel="横距離 |x| [m]", ylabel="検出確率 p(x)",
                       ylim=(0.0, 1.05),
                       title="横距離曲線 —— 誤検出率を揃えて比べる",
                       caption=f"どちらも誤検出 {FA_PER_FRAME:.1f} 件/枚。"
                               f"面積が走査幅で、{curve_out['tophat']['w']:.0f} m 対 "
                               f"{curve_out['naive']['w']:.0f} m。")
    return {"hist": hist, "p_show": p_show, "sweep": sweep, "area_km2": area_km2,
            "w_hi": w_hi, "w_lo": w_lo}


def section_controls(curve_out):
    print("\n=== 9. 対照群 —— 落ちる原因を 1 つずつ止める ===")
    print(f"  {N_CTRL} フレーム(= {2 * N_CTRL} 試行/帯)。止めたぶん誤検出も減るので、")
    print(f"  各条件で改めて {FA_PER_FRAME:.1f} 件/枚に揃えた閾値を使う。")
    base_w = curve_out["tophat"]["w"]
    conds = (("基準(全部入り)", {}),
             ("cos^4 の減光を止める", {"vignette": False}),
             ("大気を止める", {"atmosphere": False}),
             ("軸外ぼけを止める", {"blur": False}),
             ("白波を止める", {"whitecaps": False}),
             ("うねりを止める", {"swell": False}))
    print(f"  {'条件':>24}{'閾値':>8}{'W [m]':>16}{'基準との差':>14}{'端の p':>10}")
    rows, out = [], {}
    for name, kw in conds:
        run = sweep_frames(N_CTRL, "tophat", seed0=50000, **kw)
        thr = threshold_for_fa(run["fa_z"], N_CTRL)
        p, w, se = curve_at(run, thr)
        out[name] = {"w": w, "se": se, "thr": thr, "p": p}
        print(f"  {name:>24}{thr:>8.2f}{w:>11.1f} ± {se:.1f}"
              f"{w - base_w:>+13.1f} m{p[-1]:>10.3f}")
        rows.append((name, "%.2f" % thr, "%.1f ± %.1f" % (w, se),
                     "%+.1f" % (w - base_w), "%.3f" % p[-1]))
    tot = sum(out[n]["w"] - base_w for n, _ in conds[1:5])
    print(f"  → cos^4 がいちばん効く(+{out['cos^4 の減光を止める']['w'] - base_w:.0f} m)。")
    print(f"  → ★**足し算にならない**: 4 つの差を足すと {tot:+.0f} m だが、")
    print("     止めると誤検出も減って閾値が下がるので、原因どうしが絡む。")
    print("     「cos^4 で x m、大気で y m 損している」と足し上げる報告はここで嘘になる。")
    print(f"  → うねりを止めても W は {out['うねりを止める']['w'] - base_w:+.1f} m しか")
    print("     動かない。トップハットがうねりをほぼ全部落とすからで、")
    print("     §2 で海面のぼけを軸上 1 本で近似したことが走査幅に効かない根拠になる。")
    figs.save_table("controls", ["条件", "閾値", "W [m]", "基準との差", "端の p"], rows,
                    title="原因を 1 つずつ止める —— ただし足し算にはならない",
                    caption="止めると誤検出も減るので閾値が下がる。"
                            "各条件で誤検出率を揃え直してある。")
    return out


def section_tool_holes():
    print("\n=== 10. 道具の穴 —— 4 層(fs / fs.op / fs.ledger / op_find)を引いた結果 ===")
    found = {stem: sorted({r["op"] for r in fs.op_find(stem)})
             for stem in ("match", "correl", "tophat", "blob", "laplace")}
    print("  引いた語幹と当たった op(抜粋):")
    for stem in ("tophat", "blob", "match"):
        print(f"    {stem:>8}: " + ", ".join(found[stem][:8])
              + (" ..." if len(found[stem]) > 8 else ""))
    print("  使えたもの: fs.op.gray_tophat(整合フィルタ)/ fs.star_detect(点の検出)")
    print("            / fs.photon_sample / fs.noise_sigma / fs.op.gauss_filter")
    print("            / fs.ledger.surface_synth_psd / fs.integrate_funct_1d")
    print("            / fs.relative_illumination / fs.draw_circle")

    # (a) 位置を指定して点源を描く公開 op が無い。
    import astrostack
    has_public = hasattr(fs, "gaussian_star_exact") or hasattr(fs.ledger,
                                                               "gaussian_star_exact")
    print("\n  (a) **位置を指定して点源を描く公開 op が無い**。")
    print(f"      astrostack._gaussian_star_exact(erf で画素を厳密積分)は非公開"
          f"(公開されている: {has_public})。")
    print("      公開されているのは synth_starfield だけで、**位置は内部で乱数**。")
    print("      真値つきの検出試験では位置を指定できないと使えないので、"
          "この PoC は自前で描いた。")

    # (b) 整合フィルタの相関マップが出せない。
    tmpl = np.exp(-0.5 * ((np.arange(9) - 4)[:, None] ** 2
                          + (np.arange(9) - 4)[None, :] ** 2) / 1.2 ** 2)
    fs.set_match_template(tmpl / tmpl.sum())
    probe, trow, tcol, _ = make_frame(1, target_cols=(HALF_PX - 100, HALF_PX + 100))
    loc = np.asarray(fs.op.ncc_locate(probe, a=0.5))
    print("\n  (b) **NCC の相関マップを返す op が無い**。")
    print(f"      fs.op.ncc_locate は最良の 1 個だけを返す: shape={loc.shape}"
          f" 値={np.round(loc, 3).tolist()}")
    print(f"      目標は {len(trow)} 個植ててあるのに 1 個しか返らない。"
          "HALCON の find_ncc_model は")
    print("      N 個返すが、こちらは argmax 固定(_ncc_map は非公開)。"
          "多目標の捜索には使えない。")

    # (c) blob 族は座標を返さない。
    b_log = np.asarray(fs.op.xsk_blob_log(probe, a=0.4))
    print("\n  (c) **2-D の blob 族はスカラーしか返さない**。")
    print(f"      fs.op.xsk_blob_log(probe) -> shape={b_log.shape}"
          f"(= 個数のような 1 個の特徴量)。")
    print("      座標が要るなら fs.ledger.blob_label で二値化してから連結成分、"
          "つまり**先に閾値**が要る。")
    print("      閾値を決めるために検出したいのに順序が逆で、"
          "点状目標には向かない。")

    # (d) 名前が天文に閉じている。
    hits = {r["op"] for r in fs.op_find("小さい目標 検出")} | \
           {r["op"] for r in fs.op_find("point target detection")}
    print("\n  (d) ★**点状目標の座標を返す 2-D op は star_detect だけで、"
          "名前が天文に閉じている**。")
    print(f"      「小さい目標 検出」「point target detection」で引いても "
          f"star_detect は{'出る' if 'star_detect' in hits else '出ない'}。")
    print("      捜索・欠陥・粒子・医用の文脈から辿り着けない。"
          "中身は「背景 + kσ を超える局所最大 + 重心」で")
    print("      分野に依らないので、``peak_detect`` のような中立な別名を"
          "台帳に足すのが筋。")
    print("\n  ★埋めるべき op(具体案): (1) 位置指定の点源描画 "
          "``draw_point_sources(shape, rows, cols, flux, sigma)``、")
    print("     (2) 相関マップを返す ``ncc_map(image, template)``、")
    print("     (3) 分野中立な ``peak_detect``(star_detect の別名)、")
    print("     (4) 横距離曲線 → 走査幅の ``sweep_width(p, dx)`` と")
    print("         被覆率則 ``search_detection_probability(W, v, t, A, law)``。")
    print("     (4) は画像 op ではないので台帳の外だが、"
          "**画像から意思決定へ渡す最後の 1 段**がここに無い。")
    return {"loc_shape": tuple(loc.shape), "blob_shape": tuple(b_log.shape),
            "star_in_hits": "star_detect" in hits, "has_public_point": has_public,
            "n_target_probe": len(trow)}


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    geo = section_geometry()
    floor = section_floor()
    curve = section_lateral_curve(floor)
    defn = section_definition(curve)
    cliff = section_cliff(curve, defn)
    equiv = section_equivalence(curve, defn)
    alt = section_altitude()
    fa = section_false_alarms(curve)
    ctrl = section_controls(curve)
    holes = section_tool_holes()

    print("\n=== 11. まとめ ===")
    rows = [
        ("横距離曲線から出した走査幅 W", "%.1f m" % defn["w"]),
        ("ゼロ点(生画像)の走査幅", "%.1f m" % curve["naive"]["w"]),
        ("誤検出率(両者そろえた運用点)", "%.1f 件/枚" % FA_PER_FRAME),
        ("C=1 の検出確率(閉形式・平行/ランダム)", "1.0000 / 0.6321"),
        ("C=1 の検出確率(実測 p・平行/ランダム)",
         "%.4f / %.4f" % (cliff["par_real"][4], cliff["rnd_real"][4])),
        ("最適高度(v 一定 / v ∝ h)",
         "%.0f m / %.0f m" % (ALTITUDES[alt["best"]], ALTITUDES[alt["best_scaled"]])),
        ("閾値だけで動く W の幅", "%.0f - %.0f m" % (fa["w_lo"], fa["w_hi"])),
        ("誤検出(直下の帯 / 最外の帯)", "%d 件 / %d 件" % (fa["hist"][0], fa["hist"][-1])),
    ]
    for name, val in rows:
        print("  " + pad(name, 40, right=False) + pad(val, 20))
    figs.save_table("summary", ["項目", "実測"], rows,
                    title="空撮から走査幅まで、走査幅から捜索計画まで",
                    caption="走査幅は誤検出率と対でしか意味を持たない。"
                            "C=1 の崖は 1.000 対 0.632、実曲線はそのあいだ。")

    # ---- 自己検査(所見を固定する。壊れたら鳴る)------------------------------
    # (1) 幾何: 中心投影では地上分解能が横距離に依らない。魚眼では依る。
    assert geo["spread"] < 1e-12, geo["spread"]
    assert abs(geo["rect_edge_ratio"] - 1.0) < 1e-12, geo["rect_edge_ratio"]
    assert geo["ftheta_edge_ratio"] > 2.0, geo["ftheta_edge_ratio"]
    assert geo["ri_gap"] < 1e-12, geo["ri_gap"]
    # (2) 床: 較正した閾値が本当にその誤検出率を出す
    for mode in ("naive", "tophat"):
        assert abs(floor[mode]["got"] - FA_PER_FRAME) < 0.3, floor[mode]
    # (3) 横距離曲線: 単調に落ち、外の帯でほぼ 0(打ち切りが無視できる)
    p = curve["tophat"]["p"]
    assert p[0] > 0.80, p
    assert p[-1] < 0.05, p
    assert p[0] - p[-1] > 0.5, p
    # ★ゼロ点を上回っていること(誤検出率を揃えた上で)
    assert curve["tophat"]["w"] > 2.0 * curve["naive"]["w"], (curve["tophat"]["w"],
                                                              curve["naive"]["w"])
    # 較正フレームで決めた閾値と、計測フレーム自身で決めた閾値が近い
    assert abs(curve["self_thr"] - floor["tophat"]["thr"]) < 1.5, curve["self_thr"]
    # (4) 定義: 形の違う 4 本が、面積が同じなら同じ検出数を出す
    for g in defn["got"]:
        assert abs(g - defn["pred"]) < 5.0 * defn["mc_sd"], (g, defn["pred"])
    # (5) 崖: 矩形の対照では閉形式に乗る。C=1 で 1.000 / 0.632
    i1 = 4
    assert abs(cliff["C"][i1] - 1.0) < 1e-9, cliff["C"]
    assert cliff["par_rect"][i1] > 0.995, cliff["par_rect"][i1]
    assert abs(cliff["rnd_rect"][i1] - (1 - math.exp(-1.0))) < 0.02, cliff["rnd_rect"][i1]
    assert np.all(np.abs(cliff["par_rect"] - np.minimum(1.0, cliff["C"])) < 0.02)
    # ★外した予測: 実測の p では平行捜索が C=1 で 1.000 に届かない
    assert cliff["par_real"][i1] < 0.97, cliff["par_real"][i1]
    assert cliff["par_real"][i1] > cliff["rnd_real"][i1], (cliff["par_real"][i1],
                                                           cliff["rnd_real"][i1])
    # (6) ★W 2 倍 と t 2 倍 は等価
    assert equiv["d_par"] < 0.01, equiv["d_par"]
    assert equiv["d_rnd"] < 0.01, equiv["d_rnd"]
    # (7) 高度: 最適が内点(両端でない)。低高度は視野で切られている
    assert 0 < alt["best"] < len(ALTITUDES) - 1, alt["best"]
    assert alt["rows"][0]["p_end"] > 0.05, alt["rows"][0]["p_end"]
    assert alt["rows"][-1]["w"] < 0.5 * alt["W"][alt["best"]], alt["rows"][-1]
    assert alt["best_scaled"] >= alt["best"], (alt["best_scaled"], alt["best"])
    # (8) ★見張り役: 誤検出は直下に集中する。閾値だけで W が大きく動く
    assert fa["hist"][0] > 3 * max(int(fa["hist"][-1]), 1), fa["hist"]
    assert fa["hist"][0] > fa["hist"][-1], fa["hist"]
    assert fa["w_hi"] > 1.5 * fa["w_lo"], (fa["w_hi"], fa["w_lo"])
    # (9) 対照群: どれを止めても走査幅は伸びる(= どれも本当に効いている)
    base = ctrl["基準(全部入り)"]["w"]
    for name in ("cos^4 の減光を止める", "大気を止める", "軸外ぼけを止める",
                 "白波を止める"):
        assert ctrl[name]["w"] > base, (name, ctrl[name]["w"], base)
    # うねりは効かない(§2 の近似の根拠)
    assert abs(ctrl["うねりを止める"]["w"] - base) < 0.15 * base, ctrl["うねりを止める"]
    # (10) 道具の穴。埋まったらここが鳴る(それが目的)
    assert holes["loc_shape"] == (3,), holes["loc_shape"]
    assert holes["blob_shape"] == (), holes["blob_shape"]
    assert holes["n_target_probe"] == 2, holes["n_target_probe"]
    assert not holes["star_in_hits"], "op_find で star_detect が引けるようになった"
    assert not holes["has_public_point"], "点源描画が公開された"

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print(f"\n所要 {time.perf_counter() - t0:.1f} s")
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
