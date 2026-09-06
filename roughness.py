# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""roughness — 表面粗さ(areal / profile)のパラメータ・帯域分離・真値つき合成。

動機(2026-09-06): `examples/poc_surface_roughness.py` が実測つきで
「粗さパラメータの op が 1 つも無い」と報告した。Sa/Sq/Sz も Ra/Rq/Rz も、
ISO 流のガウス帯域フィルタも、真値の分かる高さ場の合成器も無い。
ここはその 6 つを op にした層である。

内容(6 op):
  評価  `surface_params`     … 面のパラメータ Sa/Sq/Sp/Sv/Sz/Ssk/Sku/Sdq/Sdr
        `profile_params`     … 断面のパラメータ Ra/Rq/Rz/Rt/Rp/Rv/Rsk/Rku
  帯域  `surface_filter`     … 粗さ / うねりの分離(ガウス、端の扱いを引数に出す)
        `surface_form_remove`… 格子のまま平面 / 二次曲面を除く(LS / RANSAC)
  検算  `surface_synth_psd`  … 指定 PSD から高さ場を作る。**解析 Sq を一緒に返す**
        `surface_psd`        … PSD。規約(面 / 動径)を引数で明示する

規約:
  * 高さ場は 2 次元配列 ``z[i, j]``。``i`` が行 = y 方向(標本間隔 ``dy``)、
    ``j`` が列 = x 方向(標本間隔 ``dx``)。``dy=None`` は正方画素 ``dy=dx``。
  * 長さの単位は呼び出し側が決める。``dx`` と ``lambda_*`` と高さが同じ単位で
    あることは**検査できない**ので、ここは規約で守る(単位を混ぜると
    Sdq/Sdr だけが静かに間違う ―― Sa/Sq は高さの単位だけで決まるため)。
  * カットオフはすべて**波長**で指定する(周波数ではない)。
  * 空間周波数 ``q`` は ``cycles / length``(角周波数ではない)。

**この層の一番大事な主張**: 「粗さ」は帯域の宣言とセットでしか数字にならない。
生の測定値の rms を Sq と呼ぶと桁で間違う(下の実測)ので、`surface_params` は
既定で「帯域処理済みに見えるか」を検査し、見えなければ拒否する。

来歴(公開規格・文献のみ): ISO 25178-2(面のパラメータ)/ ISO 4287(断面の
パラメータ)/ ISO 16610-21(ガウス位相補償フィルタ、透過率
``exp(-π (α λ f)²)``, ``α = √(ln2/π)``)/ ISO 16610-28(端の扱い)/
Persson et al., *J. Phys. Condens. Matter* 17 (2005) R1(自己アフィン面の PSD)/
Jacobs, Junge & Pastewka, *Surf. Topogr.* 5 (2017) 013001(PSD の規約と単位)。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

__all__ = [
    "surface_params", "profile_params", "surface_filter",
    "surface_form_remove", "surface_synth_psd", "surface_psd",
    "GAUSS_ALPHA",
]

#: ISO 16610-21 のガウスフィルタ定数。透過率 ``exp(-π (α λ f)²)`` が
#: ``f = 1/λ`` でちょうど 50 % になるように選ばれている(``α = √(ln2/π)``)。
GAUSS_ALPHA = math.sqrt(math.log(2.0) / math.pi)

#: `surface_filter` が受ける端の扱い。
_END_EFFECTS = ("reject", "mirror", "wrap")

#: `surface_params` が「帯域処理済み」と認める上限。値の根拠(通す側と拒否する側の
#: 実測値、およびその間の余裕)は `surface_params` の docstring にある。
_BAND_LONGWAVE_MAX = 0.25
_BAND_FORM_PTV_MAX = 1.0


# --------------------------------------------------------------------------- #
# 入力検証 — fail closed                                                       #
# --------------------------------------------------------------------------- #
def _as_field(z, op: str, min_side: int = 8, name: str = "z") -> np.ndarray:
    """高さ場を float64 の 2 次元配列にする。壊れた入力はここで止める。"""
    a = np.asarray(z, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"{op}: {name} must be a 2-D height field, got ndim={a.ndim}")
    if min(a.shape) < min_side:
        raise ValueError(
            f"{op}: {name} must be at least {min_side}x{min_side}, got {a.shape}")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{op}: {name} contains NaN or Inf")
    return a


def _as_profile(p, op: str, min_n: int = 8, name: str = "p") -> np.ndarray:
    a = np.asarray(p, dtype=np.float64)
    if a.ndim != 1:
        raise ValueError(f"{op}: {name} must be a 1-D profile, got ndim={a.ndim}")
    if a.size < min_n:
        raise ValueError(f"{op}: {name} must have at least {min_n} samples, got {a.size}")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{op}: {name} contains NaN or Inf")
    return a


def _pitch(dx, dy, op: str) -> tuple[float, float]:
    """``(dx, dy)`` を正の有限値にする。``dy=None`` は正方画素。"""
    fx = float(dx)
    if not math.isfinite(fx) or fx <= 0.0:
        raise ValueError(f"{op}: dx must be a finite positive length, got {dx!r}")
    if dy is None:
        return fx, fx
    fy = float(dy)
    if not math.isfinite(fy) or fy <= 0.0:
        raise ValueError(f"{op}: dy must be a finite positive length or None, got {dy!r}")
    return fx, fy


def _check_cutoff(lam, pitch: float, extent: float, op: str, name: str) -> float:
    """カットオフ波長が標本間隔と評価長さの間にあることを確かめる。"""
    v = float(lam)
    if not math.isfinite(v) or v <= 0.0:
        raise ValueError(f"{op}: {name} must be a finite positive wavelength, got {lam!r}")
    if v < 2.0 * pitch:
        raise ValueError(
            f"{op}: {name}={v:g} is below the Nyquist wavelength 2*pitch={2 * pitch:g}; "
            "a cutoff shorter than two samples cannot be realised")
    if v > extent:
        raise ValueError(
            f"{op}: {name}={v:g} exceeds the evaluation length {extent:g}; "
            "the filtered result would be dominated by the ends")
    return v


# --------------------------------------------------------------------------- #
# ガウスフィルタ(ISO 16610-21)                                                #
# --------------------------------------------------------------------------- #
def _gauss_weights(lam: float, pitch: float) -> np.ndarray:
    """ISO 16610-21 の重み関数を標本化して正規化した 1 次元カーネル。

    重み関数は ``s(x) = 1/(α λ) exp(-π (x/(α λ))²)``。これは標準偏差
    ``σ = α λ / √(2π)`` のガウスと同じで、そのフーリエ変換が規格の透過率
    ``exp(-π (α λ f)²)`` になる。打ち切りは規格どおり ``±λ/2``。
    """
    sigma = GAUSS_ALPHA * lam / (math.sqrt(2.0 * math.pi) * pitch)
    radius = max(1, int(math.ceil(0.5 * lam / pitch)))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    w = np.exp(-0.5 * (x / sigma) ** 2)
    return w / w.sum()


def _lowpass2(z: np.ndarray, lam: float, dx: float, dy: float, mode: str) -> np.ndarray:
    """可分ガウス低域通過。``mode`` は scipy.ndimage の境界モード。"""
    out = ndimage.correlate1d(z, _gauss_weights(lam, dy), axis=0, mode=mode)
    return ndimage.correlate1d(out, _gauss_weights(lam, dx), axis=1, mode=mode)



def surface_filter(z, dx, lambda_c=None, lambda_s=None, kind="gaussian",
                   end_effect="reject", dy=None):
    """高さ場を粗さとうねりに分ける(ISO 16610-21 のガウスフィルタ)。

    戻り値は ``(roughness, waviness)``。``roughness`` が λc より短い成分、
    ``waviness`` が長い成分で、``end_effect="reject"`` でなければ
    ``roughness + waviness`` は入力(λs を掛けたあとの一次形状)に厳密に一致する。

    引数
      z          高さ場 ``z[i, j]``(行 = y、列 = x)。
      dx, dy     標本間隔。``dy=None`` は正方画素。
      lambda_c   長波長側カットオフ(粗さ / うねりの境)。``None`` なら分けない
                 (``waviness`` はゼロ配列)。
      lambda_s   短波長側カットオフ(雑音を落とす S フィルタ)。``None`` で無効。
      kind       ``"gaussian"`` のみ。他を渡すと **黙って代用せず** 例外にする。
      end_effect ``"reject"``(既定) / ``"mirror"`` / ``"wrap"``。下記。
      dy         行方向の標本間隔(``None`` = ``dx``)。

    ★ 端の扱い(``end_effect``)—— ここがこの op を書いた理由
      畳み込みはカーネル半径 ``λc/2`` のぶん、端で「無い所のデータ」を要る。
      規格(ISO 16610-28)は評価領域を両端 ``λc/2`` ずつ削ることを前提にする。

      * ``"reject"``(既定)—— 両端 ``ceil(λc/2/pitch)`` 標本を**捨てる**。
        出力は入力より小さい配列になる。捨てた領域は「測っていない」ので、
        これが唯一嘘のない選択肢。
      * ``"mirror"`` —— 鏡像で延長して同じ形を返す。端では面が偶関数だと仮定する。
      * ``"wrap"`` —— 循環畳み込み(FFT と同じ)。左端の続きが右端だと仮定する。

      **実測**。真値は 704x704 の面をフィルタしてから中央 512x512 を切り出した
      もの(端の外側に本物のデータがある状態で計算した答え)。dx=1、λc=80、
      端の帯 = 外周 40 標本、そこでの真値の rms は 0.1932。

          面の状態     end_effect   端の帯の rms 誤差    中央部の rms 誤差
          傾きあり     wrap           4.3883 (2272 %)      0.0e+00 (0.000 %)
          傾きあり     mirror         0.1765 (  91 %)      0.0e+00 (0.000 %)
          傾き除去済   wrap           0.0111 ( 5.7 %)      4.4e-15 (0.000 %)
          傾き除去済   mirror         0.0115 ( 5.9 %)      4.4e-15 (0.000 %)
          (どれでも)  reject         —— 返さない ——      0.0e+00 (0.000 %)

      読み取れること 4 つ:
        1. **端の扱いは端でしか効かない。** 中央部はどれも真値と厳密に一致する
           (カーネルが端に届かないので当然だが、確かめた)。
        2. **最悪の組み合わせは「傾きを残したまま wrap」** —— 端の誤差が
           真値そのものの 23 倍。左端の続きが右端だと仮定するので、
           高さの違う 2 辺の継ぎ目に段差が立つ。
        3. **傾きさえ除けば wrap と mirror に差は無い**(5.7 % 対 5.9 %、
           wrap がわずかに良い)。「循環畳み込みは常に悪い」ではなく
           「**傾きを除かずに使うのが悪い**」が正しい。
        4. reject の代償は面積。512x512・λc=80 で **28.8 % を捨てる**
           (432x432 が残る)。捨てる割合は ``1 - (1 - λc/L)²`` で増えるので、
           λc が評価長さの 1/4 を超えると半分近くを失う。

    ★ 透過率は規格どおりか(実測、λc=80、dx=1、整数周期の正弦を射影で測定)

          λ         うねり側    ISO 規格値    差
           16      0.000806     0.000000    +8.1e-04
           32      0.017206     0.013139    +4.1e-03
           40      0.058676     0.062500    -3.8e-03
           64      0.342826     0.338564    +4.3e-03
           80      0.509549     0.500000    +9.6e-03   ← 最大
          128      0.772150     0.762799    +9.4e-03
          256      0.937944     0.934550    +3.4e-03

      **カットオフ波長そのもので 0.5000 でなく 0.5095**(相対 +1.9 %)。原因は
      規格が指定する打ち切り ``±λc/2``(= 2.67 σ)で、裾の 0.8 % が落ちるため。
      打ち切りを 4 σ(``±0.75 λc``)まで広げると最大誤差は 9e-05 に落ちる
      (実測)が、reject で捨てる帯が 1.5 倍になる。**規格に合わせる側を採り、
      ずれを書く**方を選んだ。粗さとうねりの和は常に入力に厳密一致する
      (上の表で ``roughness + waviness = 1.000000``)ので、分配の境目が
      1.9 % ずれるだけで、エネルギーが消えたり湧いたりはしない。

    fail-closed
      * ``kind`` が ``"gaussian"`` 以外 / ``end_effect`` が既知の 3 つ以外。
      * ``lambda_c`` と ``lambda_s`` の両方が ``None``(何もしない呼び出し)。
      * カットオフが Nyquist 波長 ``2*pitch`` 未満、または評価長さ超。
      * ``lambda_s >= lambda_c``(帯域が空になる)。
      * ``"reject"`` で削ったあと配列が残らない。
    """
    op = "surface_filter"
    a = _as_field(z, op)
    fx, fy = _pitch(dx, dy, op)
    if kind != "gaussian":
        raise ValueError(
            f"{op}: kind must be 'gaussian' (ISO 16610-21); got {kind!r}. "
            "No substitute filter is applied silently")
    if end_effect not in _END_EFFECTS:
        raise ValueError(f"{op}: end_effect must be one of {_END_EFFECTS}, got {end_effect!r}")
    if lambda_c is None and lambda_s is None:
        raise ValueError(f"{op}: give at least one of lambda_c / lambda_s")

    ny, nx = a.shape
    ext = min(ny * fy, nx * fx)
    lc = None if lambda_c is None else _check_cutoff(lambda_c, max(fx, fy), ext, op, "lambda_c")
    ls = None if lambda_s is None else _check_cutoff(lambda_s, max(fx, fy), ext, op, "lambda_s")
    if lc is not None and ls is not None and ls >= lc:
        raise ValueError(
            f"{op}: lambda_s={ls:g} must be shorter than lambda_c={lc:g}; "
            "otherwise the roughness band is empty")

    mode = "wrap" if end_effect == "wrap" else "mirror"
    primary = a if ls is None else _lowpass2(a, ls, fx, fy, mode)
    if lc is None:
        wav = np.zeros_like(primary)
    else:
        wav = _lowpass2(primary, lc, fx, fy, mode)
    rough = primary - wav

    if end_effect != "reject":
        return rough, wav

    lam_edge = lc if lc is not None else ls
    ry = int(math.ceil(0.5 * lam_edge / fy))
    rx = int(math.ceil(0.5 * lam_edge / fx))
    if 2 * ry >= ny or 2 * rx >= nx:
        raise ValueError(
            f"{op}: end_effect='reject' would discard the whole field "
            f"(margin {ry}x{rx} of {ny}x{nx}); use a shorter cutoff or a larger field")
    sl = (slice(ry, ny - ry), slice(rx, nx - rx))
    return rough[sl].copy(), wav[sl].copy()


# --------------------------------------------------------------------------- #
# 帯域処理済みかどうかの証拠                                                    #
# --------------------------------------------------------------------------- #
def _band_evidence(a: np.ndarray, fx: float, fy: float) -> tuple[float, float]:
    """``(長波長エネルギー比, 形状 PTV / Sq)`` を返す。

    「帯域を切ったあとの粗さ」に見えるかどうかの 2 つの証拠。どちらも
    しきい値ではなく**測った量**として `surface_params` の結果にも入れる。
    """
    ny, nx = a.shape
    z = a - a.mean()
    var = float(np.mean(z ** 2))
    if var <= 0.0:
        return 0.0, 0.0
    # 証拠 1: 評価長さの 1/4 より長い波の取り分。
    lam_lp = 0.25 * min(ny * fy, nx * fx)
    lam_lp = max(lam_lp, 2.0 * max(fx, fy))
    if 2 * int(math.ceil(0.5 * lam_lp / fy)) < ny and 2 * int(math.ceil(0.5 * lam_lp / fx)) < nx:
        low = _lowpass2(z, lam_lp, fx, fy, "mirror")
        long_frac = float(np.mean(low ** 2) / var)
    else:
        long_frac = 0.0
    # 証拠 2: 最小二乗平面そのものの高低差を rms で割ったもの。
    _, coeffs = _fit_form(z, fx, fy, 1)
    yy = (np.arange(ny) - 0.5 * (ny - 1)) * fy
    xx = (np.arange(nx) - 0.5 * (nx - 1)) * fx
    plane = coeffs[0] + coeffs[1] * xx[None, :] + coeffs[2] * yy[:, None]
    form_ptv = float(plane.max() - plane.min()) / math.sqrt(var)
    return long_frac, form_ptv


# --------------------------------------------------------------------------- #
# 面のパラメータ(ISO 25178-2)                                                  #
# --------------------------------------------------------------------------- #
def surface_params(z, dx=1.0, dy=None, assume_filtered=False):
    """面の粗さパラメータ Sa/Sq/Sp/Sv/Sz/Ssk/Sku/Sdq/Sdr(ISO 25178-2)。

    引数
      z               帯域処理済みの高さ場(形状とうねりを除いたもの)。
      dx, dy          標本間隔。``dy=None`` は正方画素。
      assume_filtered ``True`` で帯域の検査を飛ばす。既定は ``False`` = **検査する**。

    戻り値は ``dict``。パラメータ 9 個に加えて、判断の根拠を数字で残すため
    ``band_long_wave_fraction`` / ``band_form_ptv_over_sq`` / ``n_points`` /
    ``assume_filtered`` を入れる。

    ★ なぜ既定で拒否するのか(実測)
      512x512, dx=1 µm の合成面(自己アフィン PSD + 加工目 λ=32 µm + 深い傷
      4 本 + うねり λ=256 µm + 傾き 0.050/-0.025)を、手順を変えて評価した。
      真値は「傷と加工目と PSD を λc=80 µm で切ったもの」:

          手順                        Sq        Sq 誤差      Sa       Ssk     Sku
          生の高さ場そのまま        8.3057   +1931.4 %   6.9089   +0.05    2.26
          最小二乗平面だけ除去      0.7520     +83.9 %   0.5273   -2.04   10.21
          平面 + λc=80µm ハイパス   0.4104      +0.4 %   0.2501   -2.88   18.76
          真値                      0.4089          —    0.2502   -2.80   18.52

      **生の rms を Sq と呼ぶと 20.3 倍**。Ssk は -2.80 が **+0.05 になって
      符号ごと消え**、Sku は 18.5 が 2.26(ガウスの 3 より下)になる。うねりと
      傾きが分布を支配すると、深い傷の情報が跡形もなく無くなる。
      平面だけ除いてもまだ 1.8 倍ずれる。「どのパラメータなら安全か」という
      逃げ道は無い —— 帯域を宣言しないまま出した数字は、パラメータの
      選び方では救えない。

    ★ 検査の中身と、しきい値の根拠(実測)
      証拠は 2 つ。**長波長比** = 評価長さの 1/4 より長い波が持つ分散の割合。
      **形状 PTV/Sq** = 最小二乗平面そのものの高低差を rms で割ったもの。

          面                                  長波長比   形状PTV/Sq   判定
          生の高さ場                            0.9714      4.62      拒否
          最小二乗平面だけ除去                  0.4415      0.00      拒否
          うねりだけ残した面(別の面)          0.5539      0.15      拒否
          平面 + λc=80µm ハイパス               0.0086      0.00      通す
          真値(λc=80µm)                       0.0042      0.00      通す
          純正弦波 λ=32(256 角)                0.0038      0.03      通す

      通す側の余裕は λc をどこまで上げても保たれるか —— **正当な運用で誤って
      拒否されないこと**を確かめるほうが大事なので、λc を振って測った
      (512², 加工目 + 傷 1 個を含む面):

          λc         16     32     64     80    128    170    256(=L/2)
          長波長比  0.0005 0.0011 0.0044 0.0085 0.0306 0.0563  0.1056

      **λc を評価長さの半分まで上げても 0.106 までしか上がらない。**
      拒否したい面の最小は 0.4415。しきい値 0.25 はその間(通す側の 2.4 倍上、
      拒否側の 1.8 倍下)に置いた。形状 PTV/Sq のほうは、帯域処理済みの面では
      実測 0.001〜0.03 にしかならず、傾きが残った面では 3.46 / 4.62。
      しきい値 1.0 はその間(通す側の 33 倍上、拒否側の 3.5 倍下)。
      なおこの 2 つは **or** で判定する —— 傾きは無いがうねりが残っている面
      (上の表の「うねりだけ残した面」)は形状 PTV では捕まらず、長波長比だけが
      鳴る。片方だけでは穴が開く。
      それでも判断を機械に預けきらないよう、``assume_filtered=True`` で
      明示的に外せる(黙って外れはしない)。証拠の数値そのものも
      ``band_long_wave_fraction`` / ``band_form_ptv_over_sq`` で返す。

    ★ 落とし穴 (a) —— Sz は「表面の性質」ではなく「どれだけ長く見たか」を測る
      同じ標本間隔(1 µm)のまま評価窓だけ広げると、Sz は頭打ちにならず
      単調に増える(実測、傷を抜いた面):

          窓          32²     64²    128²    256²    512²
          窓の数      256      64      16       4       1
          Sz平均   0.7112  0.8011  0.8693  0.9248  1.0058
          実測/予測 0.5204  0.5295  0.5314  0.5287  0.5420

      面積 256 倍で **+41.4 %**。予測はガウス極値の ``2√(2 ln M) · Sq``。
      比が窓によらずほぼ一定(0.520〜0.542、平均のまわり ±2.0 %)なので
      **増え方の形(領域の対数)は当たっている**が、絶対値は 1.9 倍外す ——
      面に相関があり、独立な標本の数が点数 M より少ないため。
      **頭打ちにならないので「真の Sz」は存在しない。Sz を報告するときは
      窓の大きさと窓の数を必ず添える。**

    ★ 落とし穴 (b) —— 標本間隔に対していちばん強いのは Sa ではなく **Sq**
      同じ面を点標本化で間引き、毎回同じ手順(傾き除去 → λc=80 µm ハイパス)
      で評価した、真値に対する相対誤差(実測):

          dx        Sa       Sq       Sz      Ssk      Sku
           1 µm   -0.0 %   +0.4 %   +0.2 %   +2.8 %   +1.3 %
           2 µm   -0.1 %   +0.4 %   -0.2 %   +3.0 %   +1.4 %
           4 µm   -0.3 %   +0.4 %   -1.3 %   +3.4 %   +1.7 %
           8 µm   -3.4 %   +0.6 %  -19.8 %   +2.3 %   -3.9 %
          16 µm  +23.5 %   +1.6 %  -29.1 %  -38.4 %  -40.8 %

      10 % を最初に超えるのは **Sz が dx=8 µm**、Sa / Ssk / Sku が dx=16 µm、
      **Sq は最後まで超えない**(最大 1.6 %)。Sq が残るのは、エイリアシングが
      エネルギーを折り返すだけで **2 次モーメントを保つ**から。Sa は分布の形が
      変わると動き、Sz は「傷の底がたまたま標本点に乗るか」で決まる極値。
      dx=8 µm では **Sa は ±5 % 合格・Sz は不合格** —— 同じデータで、
      どちらの数字を見たかだけで結論が反転する。

    ★ 落とし穴 (c) —— Sdq / Sdr は標本間隔にも単位にも効かれる
      Sdq は勾配の rms、Sdr は展開面積比 ``mean(√(1+|∇z|²)) - 1``。どちらも
      中心差分で計算するので、波長 λ の正弦では ``sinc(2 dx/λ)`` の分だけ
      **過小**に出る(実測、λ=32 µm、振幅 1、解析値 Sdq=0.138840):

          dx      Sdq 実測    実測の誤差   sinc(2dx/λ) の予想
          1 µm    0.138471      -0.27 %        -0.64 %
          2 µm    0.136212      -1.89 %        -2.55 %
          4 µm    0.126004      -9.25 %        -9.97 %
          8 µm    0.088388     -36.34 %       -36.34 %

      **粗く測るほど面は滑らかに見える。** Sdr のほうは形自体は正しく、
      十分細かく測れば解析値と +0.116 % で一致する(λ=32、dx=0.25 で実測)。
      高さと ``dx`` の単位が違うと **ここだけが静かに壊れる**(Sa/Sq は
      高さの単位しか使わないので気づけない)。
      端の 1 行 1 列は片側差分になるので**評価から外している**。

    fail-closed
      * 2 次元でない / 8x8 未満 / NaN・Inf を含む。
      * ``dx`` や ``dy`` が非正・非有限。
      * 帯域処理済みに見えない(``assume_filtered=False`` のとき)。
      * 全点が同じ高さ(Sq=0 で Ssk/Sku が定義できない)。
    """
    op = "surface_params"
    a = _as_field(z, op)
    fx, fy = _pitch(dx, dy, op)

    long_frac, form_ptv = _band_evidence(a, fx, fy)
    if not assume_filtered:
        if long_frac > _BAND_LONGWAVE_MAX or form_ptv > _BAND_FORM_PTV_MAX:
            raise ValueError(
                f"{op}: z does not look band-limited "
                f"(long-wave energy fraction {long_frac:.3f} > {_BAND_LONGWAVE_MAX}, "
                f"or form peak-to-valley {form_ptv:.2f} x Sq > {_BAND_FORM_PTV_MAX}). "
                "Remove form with surface_form_remove and apply surface_filter first, "
                "or pass assume_filtered=True to state that the band is already declared")

    h = a - a.mean()
    sq = float(math.sqrt(float(np.mean(h ** 2))))
    if sq <= 0.0:
        raise ValueError(f"{op}: z is perfectly flat (Sq = 0); skewness and kurtosis undefined")

    gy, gx = np.gradient(a, fy, fx)
    gy = gy[1:-1, 1:-1]
    gx = gx[1:-1, 1:-1]
    grad2 = gx ** 2 + gy ** 2
    sdq = float(math.sqrt(float(np.mean(grad2))))
    sdr = float(np.mean(np.sqrt(1.0 + grad2)) - 1.0)

    sp = float(h.max())
    sv = float(-h.min())
    return {
        "Sa": float(np.mean(np.abs(h))),
        "Sq": sq,
        "Sp": sp,
        "Sv": sv,
        "Sz": sp + sv,
        "Ssk": float(np.mean(h ** 3) / sq ** 3),
        "Sku": float(np.mean(h ** 4) / sq ** 4),
        "Sdq": sdq,
        "Sdr": sdr,
        "band_long_wave_fraction": long_frac,
        "band_form_ptv_over_sq": form_ptv,
        "n_points": int(a.size),
        "assume_filtered": bool(assume_filtered),
    }


# --------------------------------------------------------------------------- #
# 断面のパラメータ(ISO 4287)                                                   #
# --------------------------------------------------------------------------- #
def profile_params(p, dx=1.0, n_sampling=5):
    """断面の粗さパラメータ Ra/Rq/Rz/Rt/Rp/Rv/Rsk/Rku(ISO 4287)。

    引数
      p           帯域処理済みの断面(1 次元)。
      dx          標本間隔。パラメータ自体には効かないが ``sampling_length`` の
                  報告に要る(単位を持たせないと Rz の条件が書けない)。
      n_sampling  基準長さの分割数。ISO 4287 の既定は 5。

    ★ Rz と Rt を**両方**返す —— 定義差をここで消す
      ISO 4287 の Rz は「評価長さを ``n_sampling`` 等分し、各区間の
      最大山高さ + 最大谷深さを平均したもの」。一方 Rt は評価長さ全体の
      最大高低差。同じ断面でも値が違い、しかも文献や装置によって
      「Rz」がどちらを指すか揺れる。**両方返せば取り違えようがない。**

      実測(512 点、λc=80 µm で切った断面。深い傷を 1 本含む行を選んだ):

          Rz(5 区間の平均)    1.5076
          Rz_max(区間の最大)  5.4706
          Rt(評価長さ全体)    5.4706
          Rt / Rz               3.63

      傷が 1 区間にしか無いので、5 区間の平均が傷の寄与を 1/5 に薄める。
      **同じ断面で 3.6 倍違う数字が、どちらも「Rz」と呼ばれている。**
      同じ行から傷だけ抜くと Rt/Rz = 1.21 まで下がる ——
      **差が開くのは孤立した特徴があるときだけ**なので、
      「うちの装置では一致するから同じ」は反例に当たっていないだけ。

    ★ 落とし穴 —— 断面 1 本の Rz は面の Sz を代表しない
      加工目が行方向に走る面(512x512、深い傷 4 本、λc=80 µm)で、断面を
      171 本ずつ取った実測:

        * 目に**直交**する列方向の Rq は、平行な行方向の **2.67 倍**
          (0.1853 対 0.0694)。同じ表面・同じ装置で、向きが違うだけ。
        * 行方向の Rt は最小 0.2765 / 最大 5.4706 で **19.8 倍**ばらつく。
        * 面の Sz(5.9694)の 8 割に届く断面は **171 本中 6 本**(3.5 %)。

      Rq は数本で足りるが Rz は足りない —— **同じ 1 次元断面でも、
      パラメータごとに必要な本数が違う。** Rz を報告するなら本数と向きを
      必ず添えること。

    定義の細部(規格からの逸脱をここに明示する)
      * 基準線は評価長さ全体の平均線(最小二乗直線ではない)。傾きは
        `surface_form_remove` か `surface_filter` で先に除いておくこと。
      * Rp / Rv / Rsk / Rku は評価長さ全体で計算する(区間平均ではない)。
      * 評価長さが ``n_sampling`` で割り切れないときは余りを捨てる。捨てた
        点数は ``dropped_samples`` で返す。

    fail-closed
      * 1 次元でない / 8 点未満 / NaN・Inf を含む。
      * ``n_sampling`` が 1 未満、または区間あたり 4 点未満になる。
      * 断面が完全に平坦(Rq=0)。
    """
    op = "profile_params"
    a = _as_profile(p, op)
    fx, _ = _pitch(dx, None, op)
    ns = int(n_sampling)
    if ns < 1:
        raise ValueError(f"{op}: n_sampling must be >= 1, got {n_sampling!r}")
    seg = a.size // ns
    if seg < 4:
        raise ValueError(
            f"{op}: n_sampling={ns} leaves only {seg} samples per sampling length "
            f"(profile has {a.size}); need at least 4")

    h = a - a.mean()
    rq = float(math.sqrt(float(np.mean(h ** 2))))
    if rq <= 0.0:
        raise ValueError(f"{op}: p is perfectly flat (Rq = 0); skewness and kurtosis undefined")

    blocks = h[:seg * ns].reshape(ns, seg)
    per = blocks.max(axis=1) - blocks.min(axis=1)
    rp = float(h.max())
    rv = float(-h.min())
    return {
        "Ra": float(np.mean(np.abs(h))),
        "Rq": rq,
        "Rz": float(np.mean(per)),
        "Rz_max": float(np.max(per)),
        "Rt": rp + rv,
        "Rp": rp,
        "Rv": rv,
        "Rsk": float(np.mean(h ** 3) / rq ** 3),
        "Rku": float(np.mean(h ** 4) / rq ** 4),
        "n_sampling": ns,
        "sampling_length": float(seg * fx),
        "evaluation_length": float(a.size * fx),
        "dropped_samples": int(a.size - seg * ns),
    }


# --------------------------------------------------------------------------- #
# 形状除去(格子のまま)                                                        #
# --------------------------------------------------------------------------- #
def _form_basis(ny: int, nx: int, fx: float, fy: float, order: int):
    """``(A, scale)`` を返す。``A`` は正規化座標の単項式基底(列が項)、
    ``scale`` は係数を物理単位へ戻す倍率。

    条件数を保つため内部では ``[-1, 1]`` に正規化した座標で解き、係数だけを
    物理単位に戻す。項の順は order=1 が ``[1, x, y]``、
    order=2 が ``[1, x, y, x², xy, y²]``。
    """
    yy = (np.arange(ny, dtype=np.float64) - 0.5 * (ny - 1)) * fy
    xx = (np.arange(nx, dtype=np.float64) - 0.5 * (nx - 1)) * fx
    hx = max(abs(xx[0]), abs(xx[-1]), fx)
    hy = max(abs(yy[0]), abs(yy[-1]), fy)
    u = (xx / hx)[None, :] * np.ones((ny, 1))
    v = (yy / hy)[:, None] * np.ones((1, nx))
    one = np.ones((ny, nx))
    if order == 1:
        basis = [one, u, v]
        scale = [1.0, 1.0 / hx, 1.0 / hy]
    else:
        basis = [one, u, v, u * u, u * v, v * v]
        scale = [1.0, 1.0 / hx, 1.0 / hy, 1.0 / hx ** 2, 1.0 / (hx * hy), 1.0 / hy ** 2]
    return np.stack([b.ravel() for b in basis], axis=1), np.asarray(scale)


def _fit_form(a: np.ndarray, fx: float, fy: float, order: int):
    """最小二乗で形状を当てはめる。``(residual, coeffs_physical)``。"""
    ny, nx = a.shape
    A, scale = _form_basis(ny, nx, fx, fy, order)
    c, *_ = np.linalg.lstsq(A, a.ravel(), rcond=None)
    resid = a - (A @ c).reshape(ny, nx)
    return resid, c * scale


def surface_form_remove(z, dx, order=1, method="ls", thresh=None, dy=None,
                        iters=200, seed=0):
    """格子のまま平面 / 二次曲面を除く。``(residual, coeffs)`` を返す。

    引数
      z       高さ場。
      dx, dy  標本間隔。``dy=None`` は正方画素。
      order   1 = 平面、2 = 二次曲面。
      method  ``"ls"``(最小二乗)または ``"ransac"``(ロバスト)。
      thresh  RANSAC の内点しきい値(高さの単位)。``None`` なら最小二乗残差の
              ロバストな散らばり ``2.5 x 1.4826 x MAD`` を使う。
      iters   RANSAC の試行回数。``seed`` で決定的。

    ``coeffs`` は **場の中心を原点とする物理座標の単項式係数**。
    ``order=1`` なら ``[c0, gx, gy]`` で ``gx``/``gy`` がそのまま勾配、
    ``order=2`` なら ``[c0, gx, gy, cxx, cxy, cyy]``(``x^2, xy, y^2`` の順)。

    ★ なぜ格子のまま受けるのか
      既存の `fit_plane` / `fit_plane_ransac` は (N,3) 点群しか受けない。
      512² の高さ場を渡すには毎回 ``column_stack`` で 262144x3 = **6.3 MB** に
      展開する必要がある(実測)。ここは格子を格子のまま受け、基底も
      1 次元ベクトルの外積で作るので展開が要らない。

    ★ 費用(実測、1024x1024、``iters=200``)
      ``method="ls"`` 47 ms に対し ``method="ransac"`` は **1.8 秒**(38 倍)。
      RANSAC は毎回 1024² 点の残差を数え直すので、``iters`` に線形に効く。
      粗さだけを見るなら「LS + λc ハイパス」で同じ答えが 40 分の 1 で出る
      (下の実測を参照)—— **RANSAC を既定にしない理由がこれ。**

    ★ 落とし穴 —— ロバストが要るのは「深い傷」ではなく「**広い**外れ値」。
      ただし外れ値が多数派になると RANSAC も同時に壊れる。
      深さ 3 µm の傷 4 本を片側に寄せた 512x512 の面で、傷の**幅だけ**を
      変えた実測(傾き 0.050/-0.025 を仕込んで除く。真値は傷を含む面そのもの):

          傷の半値半幅   面積比    LS の Sq 誤差   RANSAC の Sq 誤差   改善
             4 µm         5.6 %      -1.94 %          -0.39 %        5.0 倍
            12 µm        16.3 %      -6.47 %          -3.03 %        2.1 倍
            24 µm        31.0 %     -13.79 %         -11.53 %        1.2 倍
            40 µm        46.0 %     -23.80 %         -23.56 %        1.0 倍

      3 つ読める:
        * 効くのは深さではなく**面積比**。「深い傷 = ロバスト必須」は早合点で、
          正しくは「**広い**外れ値 = ロバスト必須」。
        * 誤差は必ず**過小側**に出る —— 最小二乗が「傷が片側に寄っている
          ことによる本物の非対称」まで平面として吸い上げるから。
          **合否判定では危険な向きに壊れる。**
        * **面積比 46 % では RANSAC も助けにならない**(改善 1.0 倍)。
          外れ値が半分近くを占めると、RANSAC の多数決そのものが傷を選ぶ。
          ロバスト当てはめは「外れ値が少数派である」という前提の道具で、
          その前提が切れる所は表で示すしかない。

    ★ 落とし穴 —— λc を後段に置くと LS と RANSAC の差は消える
      同じ面(半値半幅 4 µm)に λc=80 µm のハイパスを後から掛けると、
      Sq 誤差は **LS +0.00 % / RANSAC -0.00 %**(上の表では 5.0 倍差)。
      余計に除いた平面は純粋な長波長なので、ハイパスが同じものをもう一度
      捨てるだけ。**当てはめのロバスト性が効くのは λc を掛けない運用
      (平面度・形状偏差)のとき。** 粗さだけを見るなら順序で救える。
      なお平面そのものの回復は LS でも良く、上の面で仕込んだ勾配
      0.050 / -0.025 に対し 0.050006 / -0.025127 が返る(実測)。

    fail-closed
      * ``order`` が 1 か 2 以外 / ``method`` が ``"ls"``・``"ransac"`` 以外。
      * ``thresh`` が非正・非有限。
      * RANSAC が内点を規定数集められない(退化した面)。
    """
    op = "surface_form_remove"
    a = _as_field(z, op)
    fx, fy = _pitch(dx, dy, op)
    if order not in (1, 2):
        raise ValueError(f"{op}: order must be 1 (plane) or 2 (quadric), got {order!r}")
    if method not in ("ls", "ransac"):
        raise ValueError(f"{op}: method must be 'ls' or 'ransac', got {method!r}")

    resid_ls, coef_ls = _fit_form(a, fx, fy, order)
    if method == "ls":
        return resid_ls, coef_ls

    if thresh is None:
        mad = float(np.median(np.abs(resid_ls - np.median(resid_ls))))
        t = 2.5 * 1.4826 * mad
        if t <= 0.0:
            t = 2.5 * float(np.sqrt(np.mean(resid_ls ** 2)))
    else:
        t = float(thresh)
    if not math.isfinite(t) or t <= 0.0:
        raise ValueError(f"{op}: thresh must be a finite positive height, got {thresh!r}")

    ny, nx = a.shape
    A, scale = _form_basis(ny, nx, fx, fy, order)
    b = a.ravel()
    ncoef = A.shape[1]
    msub = 3 * ncoef
    rng = np.random.default_rng(int(seed))
    best_inl, best_c = -1, None
    for _ in range(int(iters)):
        idx = rng.choice(b.size, size=msub, replace=False)
        try:
            c, *_ = np.linalg.lstsq(A[idx], b[idx], rcond=None)
        except np.linalg.LinAlgError:            # 退化した部分集合は捨てて次へ
            continue
        n_in = int(np.count_nonzero(np.abs(b - A @ c) < t))
        if n_in > best_inl:
            best_inl, best_c = n_in, c
    if best_c is None or best_inl < ncoef:
        raise ValueError(
            f"{op}: RANSAC found no consensus (best {max(best_inl, 0)} inliers of "
            f"{b.size} at thresh={t:g}); the surface may be degenerate or thresh too small")
    inl = np.abs(b - A @ best_c) < t
    c, *_ = np.linalg.lstsq(A[inl], b[inl], rcond=None)
    return a - (A @ c).reshape(ny, nx), c * scale


# --------------------------------------------------------------------------- #
# PSD からの合成(真値つき)                                                     #
# --------------------------------------------------------------------------- #
def surface_synth_psd(n, dx, hurst, lambda_lo, lambda_hi, sq, seed=0):
    """指定した PSD から高さ場を合成する。``(z, sq_analytic)`` を返す。

    帯域 ``lambda_lo <= λ <= lambda_hi`` の各モードに振幅
    ``A(q) ∝ q^-(H+1)``(= 面 PSD ``C(q) ∝ q^-2(H+1)``、自己アフィン)を置き、
    **位相だけ**乱数にする。全体を ``sq`` に規格化して返す。

    引数
      n           格子の大きさ。整数なら ``n x n``、``(ny, nx)`` でも可。
      dx          標本間隔(正方画素)。
      hurst       Hurst 指数 H(0 < H < 1)。大きいほど滑らか。
      lambda_lo   帯域の**短い**側の波長。
      lambda_hi   帯域の**長い**側の波長。
      sq          目標 Sq(帯域内の rms 高さ)。
      seed        位相の乱数種。

    ★ 解析 Sq を一緒に返すのが肝
      振幅を固定して位相だけ振るので、Parseval から
      ``<h²> = (1/(ny nx))² Σ_k A_k²`` が **位相の引き方によらず**決まる。
      つまり Sq の真値が乱数に依存しない。実測: ``z.std()`` と
      ``sq_analytic`` の相対差は seed・H・帯域・寸法を振っても
      **最大 2.2e-16**(下の表)。ここを「乱数を振って rms を測る」で
      済ませると、真値そのものが実現ごとにばらついて後段の誤差と混ざる。

          n     H     λ帯域        sq      |std/analytic-1|   尖度   PTV/rms
          128  0.30    4-32     0.5000       2.2e-16         3.084    7.97
          256  0.50    4-64     0.0800       0.0e+00         3.005    7.85
          256  0.80    2-64     0.0800       2.2e-16         2.893    6.92
          512  0.80    2-64     0.0800       0.0e+00         3.113    8.25
          512  0.95   8-256     2.0000       0.0e+00         2.542    5.69

    ★ PoC が踏んだ落とし穴を実装側に閉じ込めてある
      係数をエルミートにするために位相を ``phi = (u - u[-k]) / 2`` で
      反対称化すると、**確かに反対称にはなるが位相が一様でなくなる**
      (三角分布になって 0 の近くに寄る)。すると全モードが原点で同位相に
      足され、高さ場に 1 本のスパイクが立つ。同じ種・同じ帯域で測った実測
      (512², H=0.8, 帯域 2-64):

          位相の作り方                 PTV/rms    尖度    |std/analytic-1|
          (u - u[-k])/2 で反対称化      55.00     71.81       0.0e+00
          共役対の片方だけに一様乱数     8.47      2.95       0.0e+00  ← 正しい

      **どちらも Sq は解析値と厳密に一致する。** 分散だけ見ていたら
      気づけない壊れ方なので、この関数は共役対の片方だけに一様乱数を引く
      実装に固定し、テストで尖度と PTV/rms も見る。自己共役モード
      (k = -k、4 点)は係数が実でなければならないので、位相ではなく
      符号 ±1 を振る(位相 0 に固定すると全部 +A に偏るため)。

    fail-closed
      * ``n`` が 8 未満 / ``dx`` が非正 / ``hurst`` が (0, 1) の外。
      * ``lambda_lo >= lambda_hi``。
      * ``lambda_lo`` が Nyquist 波長 ``2*dx`` 未満(実現できない帯域)。
      * ``lambda_hi`` が評価長さ超(1 周期も入らない)。
      * ``sq`` が非正。
      * 帯域に 1 モードも入らない(格子が粗すぎる / 帯域が狭すぎる)。
    """
    op = "surface_synth_psd"
    if isinstance(n, (tuple, list)):
        if len(n) != 2:
            raise ValueError(f"{op}: n must be an int or a 2-tuple (ny, nx), got {n!r}")
        ny, nx = int(n[0]), int(n[1])
    else:
        ny = nx = int(n)
    if min(ny, nx) < 8:
        raise ValueError(f"{op}: n must be at least 8, got {(ny, nx)}")
    fx, _ = _pitch(dx, None, op)
    h_exp = float(hurst)
    if not math.isfinite(h_exp) or not (0.0 < h_exp < 1.0):
        raise ValueError(f"{op}: hurst must be in (0, 1), got {hurst!r}")
    lo, hi = float(lambda_lo), float(lambda_hi)
    if not (math.isfinite(lo) and math.isfinite(hi)) or lo <= 0.0 or hi <= 0.0:
        raise ValueError(f"{op}: lambda_lo / lambda_hi must be finite positive wavelengths")
    if lo >= hi:
        raise ValueError(
            f"{op}: lambda_lo={lo:g} must be shorter than lambda_hi={hi:g} "
            "(lo is the short-wavelength end of the band)")
    if lo < 2.0 * fx:
        raise ValueError(
            f"{op}: lambda_lo={lo:g} is below the Nyquist wavelength {2 * fx:g}")
    ext = max(ny, nx) * fx
    if hi > ext:
        raise ValueError(
            f"{op}: lambda_hi={hi:g} exceeds the field extent {ext:g}; "
            "not even one period would fit")
    target = float(sq)
    if not math.isfinite(target) or target <= 0.0:
        raise ValueError(f"{op}: sq must be a finite positive height, got {sq!r}")

    fy_ax = np.fft.fftfreq(ny, d=fx)[:, None]
    fx_ax = np.fft.fftfreq(nx, d=fx)[None, :]
    q = np.hypot(fy_ax, fx_ax)
    band = (q >= 1.0 / hi) & (q <= 1.0 / lo)
    if not band.any():
        raise ValueError(
            f"{op}: no discrete mode falls inside the band "
            f"[{lo:g}, {hi:g}]; widen the band or enlarge the grid")
    amp = np.zeros_like(q)
    amp[band] = q[band] ** (-(h_exp + 1.0))

    rng = np.random.default_rng(int(seed))
    raw = rng.uniform(-np.pi, np.pi, (ny, nx))
    neg_i = (-np.arange(ny)) % ny
    neg_j = (-np.arange(nx)) % nx
    ii, jj = np.mgrid[0:ny, 0:nx]
    ni, nj = neg_i[ii], neg_j[jj]
    # 共役対 (k, -k) の「片方だけ」を辞書式順序で選び、もう片方は符号反転で置く。
    # ここを「位相を反対称化する」で済ませると位相が一様でなくなる(上の docstring)。
    half = (ii < ni) | ((ii == ni) & (jj < nj))
    selfc = (ii == ni) & (jj == nj)
    phi = np.where(half, raw, -raw[ni, nj])
    coef = amp * np.exp(1j * phi)
    # 自己共役モードは係数が実でなければならない。位相 0 に固定すると全部 +A に
    # 偏るので、符号だけ振る(|coef|² は変わらないので Parseval は保たれる)。
    signs = np.where(rng.random((ny, nx)) < 0.5, -1.0, 1.0)
    coef = np.where(selfc, amp * signs, coef)

    z = np.fft.ifft2(coef).real
    sq_raw = float(np.sqrt(float(np.sum(amp ** 2))) / (ny * nx))
    z *= target / sq_raw
    return z, target


# --------------------------------------------------------------------------- #
# PSD                                                                          #
# --------------------------------------------------------------------------- #
def surface_psd(z, dx, kind="areal", dy=None):
    """高さ場のパワースペクトル密度。``(q, C)`` を返す。**規約を引数で明示する。**

    引数
      z       高さ場(平均は内部で引く。DC ビンは返さない)。
      dx, dy  標本間隔。``dy=None`` は正方画素。
      kind    ``"areal"`` … 2 次元 PSD ``C_2D(q)`` の環平均。
              ``"radial"`` … 1 次元動径 PSD ``C_1D(q) = 2π q C_2D(q)``。

    規約(ここを書かないと較正なしでは読めない ―― 既存の
    `radial_power_spectrum` はこれが docstring に無い)
      * ``q`` は **cycles / length**(角周波数 ``2π/λ`` ではない)。``q = 1/λ``。
      * ``C_2D(q) = dx dy |F|² / (ny nx)``。規格化は Parseval に合わせてある:
        ``∫ C_2D d²q = <h²>`` かつ ``∫ C_1D dq = <h²>``。
      * 自己アフィン面 ``H`` に対する傾きは **面 PSD で ``-2(H+1)``、
        動径 PSD で ``-2H-1``**(ちょうど 1 だけ違う)。

    ★ 実測 —— どちらの規約でも H は較正なしで戻る
      `surface_synth_psd` で H を仕込み、q ∈ [2/λ_hi, 0.4/dx] で対数対数の
      直線を当てはめて H を戻した(512², 帯域 2-64 µm):

          仕込んだ H   面 PSD の傾き   戻した H   動径の傾き   戻した H   傾き差
             0.30        -2.600        0.300      -1.600       0.300     1.0000
             0.50        -3.000        0.500      -2.000       0.500     1.0000
             0.80        -3.600        0.800      -2.600       0.800     1.0000
             0.95        -3.901        0.950      -2.901       0.950     1.0000

      誤差は 4 例とも **±0.0003 以内**、二つの規約の傾き差はどの H でも
      厳密に 1.0000。**較正なしで読める。**

      ★ ここは PoC の測り直しで結論が変わった箇所。PoC は既存
      `radial_power_spectrum` で **一律 -0.013(H の 1.6 %)の系統誤差**を
      見つけ、「環平均の離散化による系統誤差」と結論した。同じ検算をこの
      実装でやると誤差が消える。原因を切り分けたところ、**環の代表 ``q`` に
      ビン番号 ``i·Δq`` を使うか、環内の ``q`` の平均を使うかの差**だった
      —— ビン番号だと -0.0007〜-0.0010 の負のずれが出る(実測、同じ面・同じ
      当てはめ帯域)。向きは PoC の観測と同じだが大きさは 1/15 なので、
      -0.013 の残りは環平均の離散化ではなく、その関数の他の実装差に由来する。
      **この関数は環内の ``q`` の平均を返す。**

    ★ 落とし穴 —— Nyquist を超える環は「角だけ」で出来ている
      正方格子の最大 ``|q|`` は ``√2/(2 dx)`` だが、``q > 1/(2 dx)`` の環は
      周波数平面の四隅しか含まない。実測(512²): 全 362 ビンのうち上位
      107 ビン(29.6 %)が Nyquist 超。環内の点数が理想値 ``2πq/Δq`` に対して
      どれだけ欠けるかは、Nyquist 以下でも最小 0.838 倍まで落ちる
      (格子の離散化)が、Nyquist 超では 0 まで落ちる。
      **傾きの当てはめには Nyquist 超を使わないこと。**

    ★ Parseval の検算をどこまで信じてよいか(実測、512²、Sq²=6.400e-03)
      * 2 次元の全格子で ``Σ C_2D Δqx Δqy`` を取ると **+0.0000 %**(厳密)。
      * 返した動径 PSD を台形積分すると **-0.55 %**。環ごとに平均して
        1 次元に潰した時点でこの分は失われる —— **環平均は要約であって
        可逆ではない。** 0.5 % を超える精度が要る用途では 2 次元の
        ``C_2D`` を自分で積分すること。
      * この面は帯域上端が Nyquist なので、Nyquist で打ち切っても -0.55 %
        のまま変わらない(角の分に中身が無い)。角に中身がある面
        (帯域が Nyquist を超える面)では、打ち切ると欠ける。

    fail-closed
      * 2 次元でない / 8x8 未満 / NaN・Inf を含む / ``dx``, ``dy`` が非正。
      * ``kind`` が ``"areal"``・``"radial"`` 以外。
    """
    op = "surface_psd"
    a = _as_field(z, op)
    fx, fy = _pitch(dx, dy, op)
    if kind not in ("areal", "radial"):
        raise ValueError(f"{op}: kind must be 'areal' or 'radial', got {kind!r}")

    ny, nx = a.shape
    h = a - a.mean()
    F = np.fft.fft2(h)
    c2d = (fx * fy / (ny * nx)) * np.abs(F) ** 2

    qy = np.fft.fftfreq(ny, d=fy)[:, None]
    qx = np.fft.fftfreq(nx, d=fx)[None, :]
    qr = np.hypot(qy, qx)
    dq = max(1.0 / (ny * fy), 1.0 / (nx * fx))
    idx = np.rint(qr / dq).astype(np.int64)
    nb = int(idx.max()) + 1
    cnt = np.bincount(idx.ravel(), minlength=nb).astype(np.float64)
    qsum = np.bincount(idx.ravel(), weights=qr.ravel(), minlength=nb)
    csum = np.bincount(idx.ravel(), weights=c2d.ravel(), minlength=nb)
    keep = np.zeros(nb, dtype=bool)
    keep[1:] = cnt[1:] > 0                      # DC ビンは落とす
    q = qsum[keep] / cnt[keep]
    c = csum[keep] / cnt[keep]
    if kind == "radial":
        c = 2.0 * math.pi * q * c
    return q, c
