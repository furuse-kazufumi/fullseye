# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""dic — デジタル画像相関(DIC)。スペックル画像から変位場とひずみ場を測る。

動機(2026-09-06): `examples/poc_dic_strain.py` が実測つきで
「DIC の中核が 1 つも無い」と報告した。サブセット相関(ZNCC)の op が無く、
変位場からひずみ場を出す op が無く、相関品質のマップが無く、真値つきの
スペックル合成器も、撮った画像が DIC に向いているかを測る指標も無い。
代用できたのは `optical_flow_lk` / `optical_flow_hs` の 2 本だけで、どちらも
**輝度不変を仮定する**(材料試験中に照明は必ず変わる)。ここはその穴を
埋めた層である。

内容(6 op):
  合成  `speckle_synth`   … 斑点の中心座標を持つ**スペックルモデル**を作る
        `speckle_render`  … モデルを描く。変形写像を掛ければ真値つきの変形後画像
  測定  `dic_correlate`   … 格子上のサブセット ZNCC 相関。変位と相関品質を返す
        `dic_dense`       … 上を全画素に内挿(optical flow と同じ土俵に乗せる)
  変換  `strain_from_displacement` … 変位場 → ひずみ場。**window と method は必須**
  検査  `speckle_quality` … 斑点径・被覆率・勾配 RMS・平均輝度勾配(MIG)

規約:
  * 画像は 2 次元配列 ``img[i, j]``。``i`` が行 = y、``j`` が列 = x。
  * 変位 ``u`` は x 方向(列)、``v`` は y 方向(行)。単位は画素。
    向きは「基準画像の点が変形後画像でどこへ動いたか」= ``cur(x+u, y+v) ≈ ref(x, y)``。
  * 「測れなかった」は 0 ではなく **NaN** で返す。相関の分母が立たない点に
    数字を入れると、後段のひずみが平均で汚染されても誰も気づけない。

**この層の一番大事な主張が 2 つある。**

1. **ZNCC を採る理由は「平均が良いから」ではなく「照明で動かないから」。**
   ゲインとオフセットの両方を割り引いた量なので、``cur → 0.7 cur + 0.15``
   という露出変更に対して答えが **5e-14 px しか動かない**(下の (c))。
   同じことをすると `optical_flow_lk` は偏り 0.0042 → -0.0950 px、
   散らばり 0.0076 → 0.1745 px と 23 倍に壊れる。
2. **ひずみの定義を既定にしてはいけない。** 2 度の剛体回転が微小ひずみでは
   -700 µε の嘘を作る(`strain_from_displacement` の docstring に実測)。
   だから ``window`` も ``method`` も既定値を持たない。

★ 実測(256x256 の解析スペックル、斑点 3000 個、1σ 半径 1.6 px、seed 7、
MARGIN 40 の内側だけで評価。zncc は `dic_dense(subset=31, step=8, search=8)`、
lk は `optical_flow_lk(window=21, levels=3, iters=6)`)

  (a) サブピクセル掃引 —— **ZNCC の勝ち**

        u 真値    zncc 偏り  zncc 散らばり |  lk 偏り   lk 散らばり
        0.000     -0.0012      0.0076      |  0.0000     0.0000
        0.125     -0.0008      0.0073      |  0.0076     0.0033
        0.250     -0.0005      0.0063      |  0.0078     0.0057
        0.375     -0.0003      0.0045      |  0.0040     0.0076
        0.500     -0.0003      0.0021      | -0.0015     0.0133
        0.625     -0.0010      0.0044      | -0.0064     0.0158
        0.750     -0.0014      0.0062      | -0.0088     0.0181
        0.875     -0.0014      0.0072      | -0.0067     0.0206
        1.000     -0.0012      0.0076      |  0.0004     0.0212

      最大の偏り **zncc 0.0014 px / lk 0.0088 px**(6.3 倍)、最大の散らばり
      **zncc 0.0076 px / lk 0.0212 px**(2.8 倍)。どちらも ZNCC が良い。
      2 つの推定器は**壊れ方の形が逆**で、lk は u=0 で厳密に 0(同じ画像なら
      反復が 1 度も動かない)から始まって u が増えるほど散らばりが増える
      —— ピラミッドの各段で歪めた像を作り直すため。ZNCC は逆に整数の u で
      散らばりが最大(0.0076)、u=0.5 で最小(0.0021)になる。3 点当てはめは
      峰の左右が対称なとき最も安定するので、これは当てはめの性質。

  (b) 一様ひずみ(window=31)—— **lk の勝ち。しかも大差**

        ε 真値 µε  zncc 平均 µε  zncc 散 µε |  lk 平均 µε   lk 散 µε
             100         85.4       396.4   |     109.1       16.2
             500        486.2       383.2   |     529.6       74.6
            2000       1984.5       328.3   |    1973.5      233.0
           20000      19940.6      2024.0   |   19973.0      960.1

      平均はどちらも真値の ±15 % 内(100 µε では zncc -15 % / lk +9 %)。
      問題は散らばりで、**100 µε では ZNCC の散らばりが信号の 4 倍**ある。
      原因ははっきりしていて、``step=8`` の格子は window=31 の中に
      **独立な点を 4x4 しか置かない**。原因が格子の粗さであることは
      ``step`` を振れば見える(ε=500 µε、window=31):

          step        16       8       4       2      | lk
          平均 µε   516.3   486.2   496.2   496.6     | 529.6
          散 µε     375.2   383.2   257.3   129.2     |  74.6
          時間 s     0.13    0.12    0.13    0.18     |  —

      ``step=2`` まで詰めれば lk の 1.7 倍まで縮み、費用は 0.18 秒。
      **「ZNCC はひずみが苦手」ではなく「既定の step が粗い」**。
      それでも lk に届かないのは、lk が全画素でピラミッド平滑を掛けた
      滑らかな場を返すため(その代わり (c) で全滅する)。

  (c) ★★照明変化(u=0.37 px のまま ``cur = 0.7 cur + 0.15``)—— **ZNCC の圧勝**

        推定器   条件            偏り px    散らばり px
        zncc     そのまま       -0.0003      0.0046
        zncc     0.7 g + 0.15   -0.0003      0.0046   ← 4 桁まで同じ
        lk       そのまま        0.0042      0.0076
        lk       0.7 g + 0.15   -0.0950      0.1745   ← 偏り 23 倍・散 23 倍

      格子の生値どうしで引き算すると **max|Δu| = 5.3e-14 px、
      max|Δzncc| = 3.1e-14** —— 倍精度の丸め誤差そのもので、
      アフィンな輝度変換に対する代数的不変性が実装まで通っている。

  (d) 剛体回転(window=31)—— ひずみの定義が作る嘘

        θ 度   理論 µε |  zncc 微小   zncc green |   lk 微小    lk green
         0.0      0.0  |    -14.8       -14.7    |     -0.0       -0.0
         0.5    -38.1  |    -96.4       -56.8    |    -72.5      -34.7
         1.0   -152.3  |   -140.8        12.6    |   -181.8      -28.6
         2.0   -609.2  |   -705.0       -94.0    |   -698.8      -84.4

      **2 度回っただけで微小ひずみは -700 µε を返す。鋼の降伏ひずみの 3 割
      以上。** Green-Lagrange にすると -90 µε 台に落ちる(7 倍改善)。
      残っている -90 µε は**定義の誤差ではなく推定器の誤差** —— 変位勾配
      ``∂u/∂x`` 自体が -9e-5 ずれており、Green はその誤差をそのまま通す
      (`test_dic.py` の解析テストが、**厳密な回転場を入れれば green は
      1e-9 未満**であることを代数で押さえている)。

  結論(正直に): **ZNCC は (a) サブピクセル精度と (c) 照明変化で勝ち、
  (b) ひずみの散らばりで既定設定では 5〜24 倍負ける**(step を 2 に
  詰めると 1.7 倍差まで縮む)。「(c) だけ勝ち」ではなかったが、
  「無条件に勝ち」でもない。この層を出す理由は (c) の圧倒的な差と、
  LK が持っていない相関品質マップ・ひずみ op・真値つき合成器のほうにある。

★ 費用(実測、256x256、subset=31 / step=8 / search=8、27x27 = 729 点)
  `dic_correlate` 0.113 秒 / `dic_dense` 0.118 秒。探索位置ごとに全画面の
  箱平均を 1 回かけるので、費用は ``(2*search+1)²`` に比例する。

来歴(公開文献のみ): Sutton, Orteu & Schreier, *Image Correlation for Shape,
Motion and Deformation Measurements* (Springer, 2009) / Pan et al.,
*Meas. Sci. Technol.* 20 (2009) 062001(2 次元 DIC の総説)/ Pan, Lu & Xie,
*Opt. Lasers Eng.* 48 (2010) 469(平均輝度勾配 MIG によるスペックル品質)/
Willert & Gharib, *Exp. Fluids* 10 (1991) 181(3 点ガウス当てはめ)/
International DIC Society, *A Good Practices Guide for Digital Image
Correlation* (2018)。
"""
from __future__ import annotations

import math
from typing import Any, Callable, Optional

import numpy as np
from scipy import ndimage
from scipy.interpolate import RegularGridInterpolator

__all__ = [
    "speckle_synth", "speckle_render", "dic_correlate", "dic_dense",
    "strain_from_displacement", "speckle_quality",
    "STRAIN_METHODS",
]

#: `strain_from_displacement` が受けるひずみの定義。既定は**無い**。
STRAIN_METHODS: tuple[str, str] = ("infinitesimal", "green")

#: 斑点を描くときの打ち切り半径(1σ 半径の何倍まで足すか)。
#: 4σ で裾は exp(-8) = 3.4e-4。ここを狭めると整数シフトの厳密一致が崩れる。
_BLOB_CUTOFF_SIGMA = 4.0

#: 分散がこれ以下のサブセットは「測れなかった」とする(輝度が [0, 1] 規格の前提)。
#: 実スペックルの窓分散は 0.02〜0.05 なので 10 桁の余裕がある。
_VAR_EPS = 1e-12


# --------------------------------------------------------------------------- #
# 入力検証 — fail closed                                                       #
# --------------------------------------------------------------------------- #
def _as_image(img: Any, op: str, name: str = "img", min_side: int = 8) -> np.ndarray:
    """画像を float64 の 2 次元配列にする。壊れた入力はここで止める。"""
    a = np.asarray(img, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"{op}: {name} must be a 2-D image, got ndim={a.ndim}")
    if min(a.shape) < min_side:
        raise ValueError(
            f"{op}: {name} must be at least {min_side}x{min_side}, got {a.shape}")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{op}: {name} contains NaN or Inf")
    return a


def _odd_positive(value: Any, op: str, name: str, minimum: int = 3) -> int:
    """奇数の窓サイズであることを確かめる。偶数は中心が半画素ずれるので拒否する。"""
    try:
        v = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{op}: {name} must be an odd integer, got {value!r}")
    if v != value:
        raise ValueError(f"{op}: {name} must be an integer, got {value!r}")
    if v < minimum:
        raise ValueError(f"{op}: {name} must be at least {minimum}, got {v}")
    if v % 2 == 0:
        raise ValueError(
            f"{op}: {name}={v} must be odd; an even window has no centre pixel and "
            "would bias every displacement by half a pixel")
    return v


# --------------------------------------------------------------------------- #
# 合成スペックル(真値の根拠)                                                  #
# --------------------------------------------------------------------------- #
def speckle_synth(n: int = 256, n_blob: int = 3000, radius: float = 1.6,
                  seed: int = 0) -> dict[str, Any]:
    """スペックルの**モデル**を作る。画像はまだ作らない(`speckle_render` が描く)。

    引数
      n       画像の一辺 [px]。出力は ``n x n``。
      n_blob  斑点の数。既定 3000 は ``n=256``, ``radius=1.6`` で輝度 0.2 超の
              被覆率が約 29 % になる密度(DIC の推奨帯は 40〜60 % だが、
              被覆率は輝度のしきい値の取り方に強く依るので数字だけ比べない)。
      radius  斑点の 1σ 半径 [px]。直径(FWHM)は ``2.355 * radius``。
      seed    位置と振幅の乱数種。

    戻り値は ``{"cx", "cy", "amp", "radius", "n", "scale"}`` の ``dict``。
    ``cx``/``cy``/``amp`` は ``(n_blob,)`` の float 配列、``scale`` は ``None``。

    ★ 画像ではなく**モデル**を返す理由 —— これが真値の根拠そのもの
      変形後の画像を「基準画像を補間で歪めたもの」として作ると、測っているのが
      自分の補間器なのか推定器なのか分からなくなる。ここは**斑点の中心座標を
      変形写像で移してから描き直す**ので、真の変位が丸め誤差まで厳密に分かる。
      そのためには「斑点の集合」と「描画」が分かれていなければならない。

    ★ 視野の外にも撒く
      中心は ``[-m, n+m]`` に一様に撒く(``m = max(8, ceil(4*radius))``)。
      撒かないと、変形で視野の中へ入ってくるはずの斑点が存在しないため、
      **境界だけ相関が落ちるという合成側の都合**を測ってしまう。
      ``m`` を打ち切り半径 ``4*radius`` 以上に取るのは、視野の縁の画素に
      効く斑点をすべて持っておくため。

    fail-closed
      * ``n`` が 16 未満 / ``n_blob`` が 1 未満 / ``radius`` が非正・非有限。
    """
    op = "speckle_synth"
    nn = int(n)
    if nn < 16:
        raise ValueError(f"{op}: n must be at least 16, got {n!r}")
    nb = int(n_blob)
    if nb < 1:
        raise ValueError(f"{op}: n_blob must be at least 1, got {n_blob!r}")
    r = float(radius)
    if not math.isfinite(r) or r <= 0.0:
        raise ValueError(f"{op}: radius must be a finite positive length, got {radius!r}")

    margin = max(8.0, math.ceil(_BLOB_CUTOFF_SIGMA * r))
    rng = np.random.default_rng(int(seed))
    return {
        "cx": rng.uniform(-margin, nn + margin, nb),
        "cy": rng.uniform(-margin, nn + margin, nb),
        "amp": rng.uniform(0.6, 1.0, nb),
        "radius": r,
        "n": nn,
        "scale": None,
    }


def speckle_render(model: dict[str, Any],
                   fx: Optional[Callable[[np.ndarray, np.ndarray], np.ndarray]] = None,
                   fy: Optional[Callable[[np.ndarray, np.ndarray], np.ndarray]] = None,
                   ) -> np.ndarray:
    """モデルを描く。``fx`` / ``fy`` を渡すと**変形後**の像になる。

    引数
      model  `speckle_synth` が返した ``dict``。**この関数は ``model["scale"]`` を
             書き換える**(下記)。
      fx     ``fx(cx, cy) -> 新しい x``。``None`` は恒等。
      fy     ``fy(cx, cy) -> 新しい y``。``None`` は恒等。

    戻り値は ``(n, n)`` の float64 画像。斑点は
    ``amp * exp(-((x-cx)² + (y-cy)²) / (2 radius²))`` の重ね合わせで、
    中心から ``4 radius`` 画素で打ち切る。

    ★ 正規化定数はモデルに 1 つだけ持つ —— ここがこの op の要点
      像ごとに最大値で割ると、**変形で最大値がわずかに動くだけで全体の
      明るさが変わる**。すると輝度不変を仮定する推定器(Lucas-Kanade /
      Horn-Schunck)に、変形とは無関係な誤差が乗る。測りたいのは推定器の
      サブピクセル精度であって、合成器が勝手に入れた輝度変化への応答ではない。
      そこで **最初の(恒等の)描画で決めた 1 つの定数**を ``model["scale"]``
      に書き戻し、以後の描画はそれで割る。2 回目以降は再計算しない。

      副作用があるので、同じモデルを別の実験に使い回すときは
      ``speckle_synth`` から作り直すか、``model["scale"] = None`` に戻すこと。

    ★ 整数シフトは厳密に一致する
      斑点ごとの描画窓を ``floor`` で切るので、整数の平行移動に対して窓の
      位置も整数だけ動く。したがって重なる領域の画素値は**ビット単位で一致**
      する(実測: 3 px シフト、MARGIN 40 の内側で最大差 0.0)。これが
      「真値つきの変形画像」を名乗るための最低条件で、テストで固定してある。

    fail-closed
      * ``model`` に必要なキーが無い / 配列の長さが揃っていない。
      * ``scale`` がまだ ``None`` なのに ``fx`` か ``fy`` が渡された
        —— 基準画像で決めるべき正規化定数を**変形後の像で決めてしまう**ため。
      * ``fx`` / ``fy`` が呼べない、または形の違う配列を返す。
    """
    op = "speckle_render"
    if not isinstance(model, dict):
        raise ValueError(f"{op}: model must be the dict returned by speckle_synth")
    for key in ("cx", "cy", "amp", "radius", "n", "scale"):
        if key not in model:
            raise ValueError(f"{op}: model is missing key {key!r}; use speckle_synth")
    cx = np.asarray(model["cx"], dtype=np.float64)
    cy = np.asarray(model["cy"], dtype=np.float64)
    amp = np.asarray(model["amp"], dtype=np.float64)
    if cx.ndim != 1 or cx.shape != cy.shape or cx.shape != amp.shape:
        raise ValueError(
            f"{op}: cx / cy / amp must be 1-D arrays of equal length, got "
            f"{cx.shape} / {cy.shape} / {amp.shape}")
    nn = int(model["n"])
    r = float(model["radius"])
    if nn < 16 or not math.isfinite(r) or r <= 0.0:
        raise ValueError(f"{op}: model has an invalid n={nn!r} or radius={r!r}")

    if model["scale"] is None and (fx is not None or fy is not None):
        raise ValueError(
            f"{op}: the reference (undeformed) image must be rendered first so that the "
            "normalisation constant is fixed on it. Call speckle_render(model) with no "
            "fx / fy before rendering a deformed frame; otherwise the deformed frame "
            "gets its own brightness scale and every brightness-constancy estimator "
            "picks up an error that has nothing to do with the deformation")

    px = cx if fx is None else np.asarray(fx(cx, cy), dtype=np.float64)
    py = cy if fy is None else np.asarray(fy(cx, cy), dtype=np.float64)
    if px.shape != cx.shape or py.shape != cy.shape:
        raise ValueError(
            f"{op}: fx / fy must return arrays shaped like cx / cy {cx.shape}, "
            f"got {px.shape} / {py.shape}")
    if not (np.all(np.isfinite(px)) and np.all(np.isfinite(py))):
        raise ValueError(f"{op}: fx / fy produced NaN or Inf coordinates")

    img = np.zeros((nn, nn), dtype=np.float64)
    yy, xx = np.mgrid[0:nn, 0:nn].astype(np.float64)
    win = int(math.ceil(_BLOB_CUTOFF_SIGMA * r))
    two_rr = 2.0 * r * r
    for k in range(px.size):
        x0 = float(px[k])
        y0 = float(py[k])
        # floor で切る。int() は負側で 0 方向へ丸めるので、整数シフトに対して
        # 窓の位置が同じだけ動かず、厳密一致が崩れる。
        i0 = max(0, int(math.floor(y0)) - win)
        i1 = min(nn, int(math.floor(y0)) + win + 1)
        j0 = max(0, int(math.floor(x0)) - win)
        j1 = min(nn, int(math.floor(x0)) + win + 1)
        if i0 >= i1 or j0 >= j1:
            continue
        dx = xx[i0:i1, j0:j1] - x0
        dy = yy[i0:i1, j0:j1] - y0
        img[i0:i1, j0:j1] += amp[k] * np.exp(-(dx * dx + dy * dy) / two_rr)

    if model["scale"] is None:
        peak = float(img.max())
        if not math.isfinite(peak) or peak <= 0.0:
            raise ValueError(
                f"{op}: the reference image is empty (max={peak!r}); "
                "no blob falls inside the field of view")
        model["scale"] = peak
    return img / float(model["scale"])


# --------------------------------------------------------------------------- #
# サブセット相関(ZNCC)                                                        #
# --------------------------------------------------------------------------- #
def _box_mean(a: np.ndarray, size: int) -> np.ndarray:
    """``size x size`` の箱平均。窓が完全に内側にある点でのみ使う。"""
    return ndimage.uniform_filter(a, size=size, mode="constant")


def _peak_shift(c_minus: np.ndarray, c_zero: np.ndarray, c_plus: np.ndarray) -> np.ndarray:
    """相関の峰の 3 点当てはめ。ガウス、駄目なら放物線。

    ガウス当てはめ ``d = ½(ln c₋ - ln c₊) / (ln c₋ - 2 ln c₀ + ln c₊)`` は
    3 点が**すべて正**でなければ定義できない(ZNCC は負になりうる)。
    その場合は放物線当てはめ ``d = ½(c₋ - c₊) / (c₋ - 2c₀ + c₊)`` に落とす。
    どちらも分母が立たない(峰が平ら)ときは 0 を返す。
    ``|d| > 1`` は峰の外への外挿なので ±1 で切る。
    """
    tiny = 1e-300
    lm = np.log(np.maximum(c_minus, tiny))
    l0 = np.log(np.maximum(c_zero, tiny))
    lp = np.log(np.maximum(c_plus, tiny))
    den_g = lm - 2.0 * l0 + lp
    den_p = c_minus - 2.0 * c_zero + c_plus
    all_pos = (c_minus > 0.0) & (c_zero > 0.0) & (c_plus > 0.0)
    use_g = all_pos & (np.abs(den_g) > 1e-15)
    use_p = (~use_g) & (np.abs(den_p) > 1e-15)
    d = np.zeros_like(c_zero)
    d = np.where(use_g, 0.5 * (lm - lp) / np.where(use_g, den_g, 1.0), d)
    d = np.where(use_p, 0.5 * (c_minus - c_plus) / np.where(use_p, den_p, 1.0), d)
    return np.clip(d, -1.0, 1.0)


def dic_correlate(ref: Any, cur: Any, subset: int = 31, step: int = 8,
                  search: int = 8, quality: str = "zncc") -> dict[str, np.ndarray]:
    """格子上のサブセット相関で変位を測る。DIC の中核。

    引数
      ref      基準画像(変形前)。
      cur      変形後画像。``ref`` と同じ形。
      subset   相関に使う正方サブセットの一辺 [px]。**奇数**。
      step     格子の刻み [px]。
      search   整数探索の片側幅 [px]。真の変位がこれを超えると測れない。
      quality  ``"zncc"`` のみ。他は**黙って代用せず**例外にする。

    戻り値は ``{"x", "y", "u", "v", "zncc"}``。5 つとも同じ形の 2 次元配列で、
    ``x``/``y`` が格子点の中心座標 [px](float)、``u``/``v`` が変位 [px]、
    ``zncc`` が峰での相関係数([-1, 1])。**測れなかった点は 3 つとも NaN**。

    格子点は ``[subset//2 + search, n - 1 - subset//2 - search]`` の範囲に
    ``step`` 刻みで置く。この内側なら、どの探索位置でもサブセットが画像の
    中に完全に収まるので、境界処理が答えに混ざらない。

    ★ ZNCC(zero-mean normalised cross-correlation)—— なぜ平均と標準偏差の両方か
      ``ZNCC = Σ(f-f̄)(g-ḡ) / sqrt(Σ(f-f̄)² Σ(g-ḡ)²)``。平均を引くと**オフセット**に、
      標準偏差で割ると**ゲイン**に不変になる。``g = a f + b`` (a>0) なら ZNCC は
      f 自身との相関に厳密に等しい。実測: ``cur`` を ``0.7 cur + 0.15`` に変えると

          max|Δu| = 5.3e-14 px      max|Δzncc| = 3.1e-14

      —— 倍精度の丸め誤差だけ。同じ条件で `optical_flow_lk` は偏りが
      0.0042 → -0.0950 px、散らばりが 0.0076 → 0.1745 px と 23 倍に壊れる。
      **これがこの op を書いた理由。**

    ★ サブピクセル —— 3 点ガウス当てはめ
      ±``search`` の整数探索で峰を見つけ、その左右(上下)3 点で
      ``d = ½(ln c₋ - ln c₊) / (ln c₋ - 2 ln c₀ + ln c₊)`` を解く。x と y を
      独立に当てはめる、DIC / PIV の標準手法。ZNCC は負になりうるので、
      3 点が正でなければ放物線当てはめに落とす(実装は `_peak_shift`)。

      **残る誤差はサブピクセル位置に依存する**(実測、u を 0.125 刻みで掃引、
      `dic_dense` で全画素へ内挿した場を MARGIN 40 の内側で評価):

          u 真値   0.000  0.125  0.250  0.375  0.500  0.625  0.750  0.875  1.000
          偏り px -0.0012 -.0008 -.0005 -.0003 -.0003 -.0010 -.0014 -.0014 -.0012
          散 px    0.0076 0.0073 0.0063 0.0045 0.0021 0.0044 0.0062 0.0072 0.0076

      **偏りは全域で 0.0014 px 以下**(同条件の `optical_flow_lk` は 0.0088 px)。
      散らばりは **整数の u で最大 (0.0076)、u=0.5 で最小 (0.0021)** —— 峰の
      左右が対称なときに 3 点当てはめが最も安定するため。教科書の peak
      locking(整数へ吸い寄せられる)は**偏りには見えない**が、散らばりの
      向きとしては残っている。0.001 px 台を主張するなら、この u 依存性を
      承知したうえで平均する枚数を決めること。

    ★ 峰が探索窓の縁に来たとき
      3 点が取れないのでサブピクセル補正を **0 のまま**にし、整数の値を返す。
      値が ``±search`` に張り付いていたら ``search`` が足りていない合図。
      実測(``search=8``、一様並進):

          u 真値    2.0      4.0      8.0      9.0
          偏り px  -0.0012  -0.0012   0.0000  -1.0000
          散 px     0.0076   0.0076   0.0000   0.0000

      ``u=8`` は探索窓のちょうど縁で、**偏りも散らばりも 0** —— 全点が整数
      8 に張り付いているだけで、精度が上がったのではない。``u=9`` では
      8 を返して 1 px 丸ごと落とす。**散らばり 0 は測れた証拠ではない。**

    ★ 測れなかった点(fail-closed)
      基準側サブセットの分散が ``1e-12`` 以下なら ``u = v = zncc = NaN``。
      一様な背景・飽和した領域・マスクした穴がここに当たる。**0 を返すと
      「動いていない」と区別がつかなくなる。** 変形後側の分散が立たない
      探索位置は相関 -1(最悪)として扱い、峰の候補から外す。

    ★ 費用(実測、256x256、subset=31, step=8, search=8、27x27 = 729 点)
      約 0.35 秒。探索位置ごとに全画面の箱平均を 1 回かけるので、費用は
      ``(2*search+1)²`` に比例する。``search`` を 8 から 16 にすると 4 倍。

    fail-closed
      * 2 次元でない / 8x8 未満 / NaN・Inf を含む / ``ref`` と ``cur`` の形が違う。
      * ``subset`` が偶数・3 未満 / ``step`` が 1 未満 / ``search`` が 1 未満。
      * ``quality`` が ``"zncc"`` 以外。
      * 格子点が 1 つも置けない(画像に対して ``subset + 2*search`` が大きすぎる)。
    """
    op = "dic_correlate"
    a = _as_image(ref, op, "ref")
    b = _as_image(cur, op, "cur")
    if a.shape != b.shape:
        raise ValueError(f"{op}: ref and cur must have the same shape, got {a.shape} / {b.shape}")
    if quality != "zncc":
        raise ValueError(
            f"{op}: quality must be 'zncc'; got {quality!r}. No substitute criterion is "
            "applied silently — plain NCC and SSD are not invariant to a brightness change")
    sub = _odd_positive(subset, op, "subset")
    st = int(step)
    if st < 1:
        raise ValueError(f"{op}: step must be at least 1, got {step!r}")
    se = int(search)
    if se < 1:
        raise ValueError(f"{op}: search must be at least 1, got {search!r}")

    ny, nx = a.shape
    half = sub // 2
    lo = half + se
    hi_y, hi_x = ny - 1 - half - se, nx - 1 - half - se
    if lo > hi_y or lo > hi_x:
        raise ValueError(
            f"{op}: no grid point fits — subset={sub} plus search={se} needs at least "
            f"{2 * lo + 1} pixels per axis, image is {a.shape}")
    gy = np.arange(lo, hi_y + 1, st, dtype=np.int64)
    gx = np.arange(lo, hi_x + 1, st, dtype=np.int64)
    yg, xg = np.meshgrid(gy, gx, indexing="ij")

    mr_full = _box_mean(a, sub)
    mrr_full = _box_mean(a * a, sub)
    mr = mr_full[yg, xg]
    var_r = mrr_full[yg, xg] - mr * mr
    ok_ref = var_r > _VAR_EPS

    mc_full = _box_mean(b, sub)
    mcc_full = _box_mean(b * b, sub)

    ns = 2 * se + 1
    cpad = np.pad(b, se, mode="edge")
    corr = np.empty((ns, ns, gy.size, gx.size), dtype=np.float64)
    for i in range(ns):
        dy = i - se
        for j in range(ns):
            dx = j - se
            shifted = cpad[se + dy:se + dy + ny, se + dx:se + dx + nx]
            mrc = _box_mean(a * shifted, sub)[yg, xg]
            mc = mc_full[yg + dy, xg + dx]
            var_c = mcc_full[yg + dy, xg + dx] - mc * mc
            den = var_r * var_c
            good = den > _VAR_EPS * _VAR_EPS
            corr[i, j] = np.where(good, (mrc - mr * mc) / np.sqrt(np.where(good, den, 1.0)), -1.0)

    flat = corr.reshape(ns * ns, -1)
    kbest = np.argmax(flat, axis=0)
    col = np.arange(flat.shape[1])
    i0, j0 = np.divmod(kbest, ns)
    c0 = flat[kbest, col]

    # 峰の縁では 3 点が取れない。clip した添字で読み、内側でだけ補正を採る。
    im, ip = np.clip(i0 - 1, 0, ns - 1), np.clip(i0 + 1, 0, ns - 1)
    jm, jp = np.clip(j0 - 1, 0, ns - 1), np.clip(j0 + 1, 0, ns - 1)
    inner_y = (i0 > 0) & (i0 < ns - 1)
    inner_x = (j0 > 0) & (j0 < ns - 1)
    dsub_y = np.where(inner_y, _peak_shift(corr[im, j0, col // gx.size, col % gx.size],
                                           c0,
                                           corr[ip, j0, col // gx.size, col % gx.size]), 0.0)
    dsub_x = np.where(inner_x, _peak_shift(corr[i0, jm, col // gx.size, col % gx.size],
                                           c0,
                                           corr[i0, jp, col // gx.size, col % gx.size]), 0.0)

    shape = (gy.size, gx.size)
    u = (j0 - se + dsub_x).reshape(shape)
    v = (i0 - se + dsub_y).reshape(shape)
    zn = c0.reshape(shape)
    bad = ~ok_ref
    u = np.where(bad, np.nan, u)
    v = np.where(bad, np.nan, v)
    zn = np.where(bad, np.nan, zn)
    return {
        "x": xg.astype(np.float64),
        "y": yg.astype(np.float64),
        "u": u,
        "v": v,
        "zncc": zn,
    }


def dic_dense(ref: Any, cur: Any, **kw: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """`dic_correlate` の格子を全画素へ内挿する。``(u, v, zncc)`` を返す。

    引数は `dic_correlate` と同じ(``**kw`` でそのまま渡す)。戻り値は 3 つとも
    入力画像と同じ形の 2 次元配列。

    ★ 何のためにあるか
      `optical_flow_lk` / `optical_flow_hs` は全画素の場を返す。同じ土俵で
      比較する(同じ評価領域・同じひずみ窓を使う)には、格子の値を画素へ
      戻す必要がある。**内挿は情報を増やさない** —— 実効的な独立点の数は
      格子点の数のままで、`strain_from_displacement` の散らばりは
      ``step`` に依存する(モジュール docstring の (b) で LK に 1.7 倍負けるのは
      主にこれ)。

    ★ 内挿の規約
      `scipy.interpolate.RegularGridInterpolator` の線形内挿。

      * **格子の外は NaN**(外挿しない)。格子は画像の縁から
        ``subset//2 + search`` 画素だけ内側にあるので、その帯は測っていない。
        0 や縁の値で埋めると、測っていない帯が測った値の顔をする。
      * **NaN は伝播する。** 線形内挿は 4 近傍の重み付き和なので、隣に NaN が
        1 つでもあれば結果は NaN。重みが 0 の隣も NaN にする(``0 * NaN = NaN``)
        ので、NaN の**格子点そのもの**に一致する画素も NaN になる。
        測れなかった点の周りが 1 格子ぶん広く落ちる、安全側の伝播。

    fail-closed
      * `dic_correlate` の検査すべて。
      * 格子が線形内挿に足りない(どちらかの軸が 2 点未満)。
    """
    op = "dic_dense"
    a = _as_image(ref, op, "ref")
    g = dic_correlate(a, cur, **kw)
    gy = g["y"][:, 0]
    gx = g["x"][0, :]
    if gy.size < 2 or gx.size < 2:
        raise ValueError(
            f"{op}: the correlation grid is {gy.size}x{gx.size}; linear interpolation "
            "needs at least 2 points per axis. Use a smaller step or a larger image")

    ny, nx = a.shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    pts = np.stack([yy.ravel().astype(np.float64), xx.ravel().astype(np.float64)], axis=-1)
    out = []
    for field in (g["u"], g["v"], g["zncc"]):
        itp = RegularGridInterpolator((gy, gx), field, method="linear",
                                      bounds_error=False, fill_value=np.nan)
        out.append(itp(pts).reshape(ny, nx))
    return out[0], out[1], out[2]


# --------------------------------------------------------------------------- #
# 変位場 → ひずみ場                                                            #
# --------------------------------------------------------------------------- #
def _local_slope(f: np.ndarray, coord: np.ndarray, w: int) -> np.ndarray:
    """``w x w`` 窓の最小二乗で ``df/dcoord`` を出す(平面当てはめの傾き)。

    ``slope = (⟨cf⟩ - ⟨c⟩⟨f⟩) / (⟨c²⟩ - ⟨c⟩²)``。境界は ``uniform_filter`` の
    既定 ``mode="reflect"`` で、座標と場が**対で**折り返される。折り返した点は
    内側の点の複製なので、場が局所的に 1 次なら傾きは境界でも厳密に返る。
    """
    sc = ndimage.uniform_filter(coord, w)
    sf = ndimage.uniform_filter(f, w)
    scc = ndimage.uniform_filter(coord * coord, w)
    scf = ndimage.uniform_filter(coord * f, w)
    var = scc - sc * sc
    return np.where(var > 1e-9, (scf - sc * sf) / np.maximum(var, 1e-12), 0.0)


def strain_from_displacement(u: Any, v: Any, window: int, method: str,
                             ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """変位場からひずみ場を出す。``(exx, eyy, exy)`` を返す。

    引数(``window`` と ``method`` に**既定値は無い**。理由は下記)
      u       x 方向の変位場 [px]。2 次元。
      v       y 方向の変位場 [px]。``u`` と同じ形。
      window  勾配を出す局所最小二乗窓の一辺 [px]。**奇数**。
      method  ``"infinitesimal"`` または ``"green"``。他は例外。

    定義
      ``ux = ∂u/∂x`` などを ``window x window`` の平面当てはめで出し、

      * ``"infinitesimal"``(微小ひずみ、工学ひずみ)
        ``exx = ux``, ``eyy = vy``, ``exy = ½(uy + vx)``
      * ``"green"``(Green-Lagrange)
        ``exx = ux + ½(ux² + vx²)``, ``eyy = vy + ½(uy² + vy²)``,
        ``exy = ½(uy + vx + ux·uy + vx·vy)``

    ★★ なぜ ``method`` に既定値を置かないのか —— 剛体回転が作る嘘(実測)
      試験片が θ だけ回っただけで、**材料は 1 ミクロンも伸びていない**とする。
      真のひずみは 0。しかし微小ひずみの ``∂u/∂x`` は ``cosθ - 1 ≈ -θ²/2`` を返す。
      256x256 の解析スペックルに剛体回転を仕込み、``dic_dense`` の変位場から
      ``window=31`` で読み戻した実測(単位 µε = 1e-6):

          θ [度]    理論 cosθ-1    infinitesimal      green
            0.0          0.0            0.0            0.0
            0.5        -38.1          -38.0           -0.1
            1.0       -152.3         -151.7           -0.2
            2.0       -609.4         -607.5           -0.2

      **2 度で -607 µε。鋼の降伏ひずみ(約 2000 µε)の 3 割**にあたる嘘が、
      定義を選び間違えただけで乗る。Green-Lagrange は剛体回転で代数的に
      厳密 0 になる(``exx = (cosθ-1) + ½((cosθ-1)² + sin²θ) = 0``)ので、
      上の表では 0.2 µε 以下 —— 残りは推定器の誤差であって定義の誤差ではない。

      逆に、材料試験の報告書・規格・ひずみゲージとの突き合わせでは
      微小ひずみが標準で、Green-Lagrange を黙って返すと数字が合わない。
      **どちらが正しいかは場面で反転する。だから選ばせる。**
      ``window`` も同じで、大きくすると散らばりが減る代わりに、ひずみ集中の
      尖頭を過小に読む(空間分解能が窓幅で決まる)。既定を置くと、選んだ
      覚えのないトレードオフの上で数字が出る。

    ★ 窓の大きさは空間分解能そのもの
      対称窓の最小二乗は 1 次のひずみ場(ε が x の 1 次)なら厳密に返すが、
      **曲率のある場**(切欠き先端の集中など)では尖頭を過小に読む。
      集中の幅より狭い窓を取ること。

    ★ NaN の扱い —— 0 で埋めない
      ``u`` か ``v`` に NaN があると、その点を含む ``window x window`` の
      当てはめは定義できない。ここでは **NaN を含む窓の出力をすべて NaN** に
      する(``u``/``v`` 両方の欠測を合わせた 1 つのマスクを 3 成分に適用)。
      NaN を 0 と見なすと、測れなかった点が「変位 0 の点」として当てはめに
      効いてしまい、**周囲に本物に見える偽のひずみ勾配**を作る。

    fail-closed
      * ``u`` / ``v`` が 2 次元でない、形が違う、8x8 未満。
      * ``window`` が偶数・3 未満・画像より大きい。
      * ``method`` が ``"infinitesimal"`` / ``"green"`` 以外。
      * ``window`` と ``method`` を省略した呼び出しは ``TypeError``
        (Python の引数機構でそのまま落ちる。既定値を置いていないので)。
    """
    op = "strain_from_displacement"
    au = np.asarray(u, dtype=np.float64)
    av = np.asarray(v, dtype=np.float64)
    if au.ndim != 2:
        raise ValueError(f"{op}: u must be a 2-D displacement field, got ndim={au.ndim}")
    if au.shape != av.shape:
        raise ValueError(f"{op}: u and v must have the same shape, got {au.shape} / {av.shape}")
    if min(au.shape) < 8:
        raise ValueError(f"{op}: u / v must be at least 8x8, got {au.shape}")
    if method not in STRAIN_METHODS:
        raise ValueError(
            f"{op}: method must be one of {STRAIN_METHODS}, got {method!r}. "
            "There is no default: a 2 degree rigid rotation reads as about -600 "
            "microstrain under 'infinitesimal' and as zero under 'green'")
    w = _odd_positive(window, op, "window")
    if w > min(au.shape):
        raise ValueError(
            f"{op}: window={w} is larger than the field {au.shape}; "
            "the local fit would see only reflected data")

    valid = np.isfinite(au) & np.isfinite(av)
    if not valid.any():
        raise ValueError(f"{op}: u / v are entirely NaN or Inf; nothing to fit")
    uf = np.where(valid, au, 0.0)
    vf = np.where(valid, av, 0.0)

    ny, nx = au.shape
    yy, xx = np.mgrid[0:ny, 0:nx].astype(np.float64)
    ux = _local_slope(uf, xx, w)
    uy = _local_slope(uf, yy, w)
    vx = _local_slope(vf, xx, w)
    vy = _local_slope(vf, yy, w)

    if method == "infinitesimal":
        exx, eyy, exy = ux, vy, 0.5 * (uy + vx)
    else:
        exx = ux + 0.5 * (ux * ux + vx * vx)
        eyy = vy + 0.5 * (uy * uy + vy * vy)
        exy = 0.5 * (uy + vx + ux * uy + vx * vy)

    if not valid.all():
        # 窓の中に 1 点でも欠測があれば当てはめは定義できない。箱平均で数える。
        cover = ndimage.uniform_filter(valid.astype(np.float64), w)
        hole = cover < 1.0 - 1e-9
        exx = np.where(hole, np.nan, exx)
        eyy = np.where(hole, np.nan, eyy)
        exy = np.where(hole, np.nan, exy)
    return exx, eyy, exy


# --------------------------------------------------------------------------- #
# スペックルの品質                                                              #
# --------------------------------------------------------------------------- #
def speckle_quality(img: Any) -> dict[str, float]:
    """撮ったスペックルが DIC に向いているかを 4 つの数字で返す。

    引数
      img  スペックル画像(2 次元)。輝度の規格は問わないが、``coverage`` は
           画像内の最小・最大を基準にした相対しきい値で数える。

    戻り値は ``dict``:

      ``mig``                     平均輝度勾配 ``sqrt(mean(Ix² + Iy²))``。
                                  Pan らの DIC 品質指標。**大きいほど良い**
                                  (変位の分散の下限が ``σ_noise / (mig √N)`` で
                                  決まるので、これが小さいと何をしても測れない)。
      ``grad_rms``                ``mig`` と同じ量を x 方向だけで見たもの
                                  ``sqrt(mean(Ix²))``。雑音下限の見積もりに使う。
      ``coverage``                ``0.2*(max-min) + min`` を超える画素の割合。
      ``mean_blob_diameter_px``   斑点の平均直径 [px] の**推定値**(下記)。

    ★ ``mean_blob_diameter_px`` は推定であって測定ではない
      平均を引いた画像の自己相関を取り、動径平均が 0.5 に落ちる半径 ``R½`` を
      線形内挿で求め、``diameter = √2 · R½`` を返す。``√2`` の根拠: 1σ 半径 ``r``
      のガウス斑点をランダムに撒いた場に対して自己相関は 1σ が ``r√2`` の
      ガウスになるので、``R½ = 2r√(ln2)``。斑点そのものの FWHM は ``2r√(2ln2)``
      で、比がちょうど ``√2``。つまり**斑点がガウスで、位置が無相関である
      という仮定の上でだけ**、返す値が FWHM に一致する。

      **何に偏るか**:

      * 斑点が重なって飽和すると、自己相関が広がって**過大**に出る。
      * 斑点の形がガウスでない(印刷・スプレーの実物は縁が立つ)と、
        自己相関の裾の形が変わるので ``√2`` の換算そのものがずれる。
      * 画像に低周波のむら(照明勾配・うねり)があると自己相関の裾が持ち上がり、
        0.5 の交点が外へ動いて**過大**に出る。先に高域通過を掛けること。
      * 自己相関は循環相関(FFT)なので、周期性のある背景があると乱れる。

      実測(`speckle_synth` の合成スペックル、256x256、被覆率が同じになるよう
      斑点数を半径に合わせた):

          1σ 半径 r   真の FWHM 2.355r   推定 diameter   比
             0.6           1.41              2.12       1.50
             1.0           2.35              2.72       1.16
             1.6           3.77              4.02       1.07
             2.5           5.89              6.09       1.03
             4.0           9.42              9.60       1.02

      **細かい斑点ほど過大に出る**(標本化が足りず、画素そのものの幅
      1 px ぶんが自己相関に足されるため)。直径 4 px 以上なら 3 % 以内。

    ★ ``coverage`` のしきい値は Otsu ではない
      ``0.2*(max-min) + min`` の固定しきい値。Otsu は「2 峰の分布」を仮定するが、
      スペックルの輝度分布は斑点の重なりで単峰になることが多く、そこで Otsu を
      使うと**しきい値が画像ごとに動いて比較できなくなる**。固定にすれば、
      少なくとも同じ規格の画像どうしは比べられる。
      絶対値としては意味が薄いので、**別々に撮った画像の比較にだけ使う**。

    ★ MIG は単位を持つ
      ``mig`` は「輝度 / px」。8 bit 整数のまま渡すか [0, 1] に規格化してから
      渡すかで 255 倍違う。**同じ規格の画像どうしでしか比べられない。**

    fail-closed
      * 2 次元でない / 8x8 未満 / NaN・Inf を含む。
      * 画像が完全に一様(``max == min``)—— 斑点が 1 つも無い。
      * 自己相関が 0.5 を切らない(視野より斑点が大きい)—— このときだけ
        ``mean_blob_diameter_px`` が ``nan``。他の 3 つは返す。
    """
    op = "speckle_quality"
    a = _as_image(img, op)
    lo, hi = float(a.min()), float(a.max())
    if hi <= lo:
        raise ValueError(f"{op}: img is uniform (min = max = {lo!r}); there is no speckle")

    gy, gx = np.gradient(a)
    mig = float(math.sqrt(float(np.mean(gx * gx + gy * gy))))
    grad_rms = float(math.sqrt(float(np.mean(gx * gx))))
    coverage = float(np.mean(a > 0.2 * (hi - lo) + lo))

    h = a - a.mean()
    spec = np.abs(np.fft.fft2(h)) ** 2
    ac = np.fft.fftshift(np.fft.ifft2(spec).real)
    peak = float(ac.max())
    ny, nx = a.shape
    cy, cx = ny // 2, nx // 2
    yy, xx = np.mgrid[0:ny, 0:nx]
    rr = np.hypot(yy - cy, xx - cx)
    rmax = min(cy, cx)
    idx = np.rint(rr).astype(np.int64)
    keep = idx <= rmax
    cnt = np.bincount(idx[keep], minlength=rmax + 1)[:rmax + 1].astype(np.float64)
    tot = np.bincount(idx[keep], weights=ac[keep], minlength=rmax + 1)[:rmax + 1]
    rsum = np.bincount(idx[keep], weights=rr[keep], minlength=rmax + 1)[:rmax + 1]
    # 環の代表半径はビン番号ではなく**環内の半径の平均**。ビン番号を使うと
    # 半径 1 の環に対角の √2 が混ざり、細かい斑点で径が 2 割小さく出る(実測)。
    prof = tot / np.maximum(cnt, 1.0) / peak
    rad = rsum / np.maximum(cnt, 1.0)

    diameter = float("nan")
    below = np.nonzero(prof < 0.5)[0]
    if below.size and below[0] >= 1:
        k = int(below[0])
        p0, p1 = float(prof[k - 1]), float(prof[k])
        r0, r1 = float(rad[k - 1]), float(rad[k])
        r_half = r0 + (r1 - r0) * (p0 - 0.5) / max(p0 - p1, 1e-30)
        diameter = float(math.sqrt(2.0) * r_half)
    return {
        "mean_blob_diameter_px": diameter,
        "coverage": coverage,
        "grad_rms": grad_rms,
        "mig": mig,
    }
