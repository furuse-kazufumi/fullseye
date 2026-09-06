# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""dic — DIC(デジタル画像相関)で **pivops に無かったものだけ**を足す 3 op。

動機と、**最初の設計を実測で捨てた経緯**(2026-09-06):
`examples/poc_dic_strain.py` は「fullseye に DIC が無い」と結論し、
ZNCC サブセット相関・ひずみ op・相関品質・真値つきスペックル合成器・
スペックル品質指標の 5 つを新設せよと書いた。だが repo には既に
`pivops.py`(23 op、``fullseye.ledger.piv_*``)がある。5 つを**実測で
突き合わせた結果、3 つは既にあり、2 つ半だけが本当に無かった**。
以下がその棚卸しで、この層が 3 op しかない理由そのものである。

  A. サブセット相関 + サブピクセル … **既にある。しかも自作より良い**
     `piv_cross_correlate(window=32, overlap=0.75)` を PoC と同じ解析
     スペックル(256², 斑点 3000, 1σ=1.6 px, seed 7、MARGIN 40 の内側)で
     測ると、u を 0〜1 px まで 0.125 刻みで振って

         最大 |偏り|  piv 0.0015 px / 自作 ZNCC 0.0014 px / optical_flow_lk 0.0088 px
         最大 散らばり piv 0.0057 px / 自作 ZNCC 0.0093 px / optical_flow_lk 0.0212 px
         時間          piv 0.053 s   / 自作 ZNCC 0.114 s

     **偏りは互角、散らばりは piv が 1.6 倍良く、速さは 2 倍。**
     いったん書いた ZNCC 相関器は測ってから捨てた。

  B. 照明変化への強さ … **既にある。しかも自作より厳密**
     ``cur → 0.7 cur + 0.15``(ゲインとオフセット)を掛けて変位の差を測ると

         piv_cross_correlate   max|Δu| = 3.7e-15 px   ← 倍精度の丸め
         自作 ZNCC             max|Δu| = 5.3e-14 px
         optical_flow_lk       max|Δu| = 1.31 px      ← 全域で破綻

     piv が不変な理由は 2 つ重なっている。``subtract_mean=True`` が
     **オフセット**を消し、``peak="gauss3"`` の対数当てはめが
     ``ln(a·c) = ln a + ln c`` の形で**ゲイン**を分子・分母の両方から
     打ち消す。実際 ``subtract_mean=False`` にすると max|Δu| は 156 px に
     壊れる(オフセットだけで破綻する)。
     **「ZNCC でなければ照明に勝てない」は誤りだった。** この層を作る
     いちばんの動機だと思っていたものが、測ったら既に満たされていた。

  C. 真値つきスペックル合成器 … **既にある**
     `piv_synth_pair(shape, displacement, ...)` は**粒子を動かしてから
     描き直す**(補間で歪めない)。実測: 整数 3 px シフトの再現誤差 0.0、
     ``displacement`` に callable を渡せるので剛体回転もひずみ集中も書ける、
     同じ ``seed`` で 1 枚目が完全に再現する。そもそも**正規化を一切しない**
     ので「像ごとに割り直して明るさが動く」問題自体が起きない。
     自作の合成器は不要。

  D. 変位場 → ひずみ場 … **半分ある。solid-mechanics 側が無い**
     `piv_velocity_gradient` / `piv_strain_rate` はある。だが
     **流体の rate-of-strain 規約しか無い**。厳密な剛体回転の変位場を
     直接入れた実測(画像を使わない代数の検算):

         θ [度]   cosθ-1 [µε]   piv dudx   piv strain_rate   dic green
           0.5        -38.1       -38.1          76.2         5.3e-14
           1.0       -152.3      -152.3         304.6         9.3e-14
           2.0       -609.2      -609.2        1218.3         2.0e-13
           5.0      -3805.3     -3805.3        7610.6         6.5e-13

     `piv_velocity_gradient["dudx"]` は ``cosθ-1`` を**厳密に**返す ——
     つまり微小ひずみの定義そのもので、**剛体回転の嘘をそのまま持つ**。
     `piv_strain_rate` は ``2|cosθ-1|``、2 度で **+1218 µε** を返す。
     真のひずみが 0 の運動に対してである。docstring の「剛体回転では 0」は
     流体の**線形化した**回転 ``u=-ωy, v=ωx`` の話で、**有限回転では成り立た
     ない**。DIC が扱うのは有限回転なので、ここは規約が違う。
     → `strain_from_displacement` を足した(Green-Lagrange + ``method`` 必須)。

     もう 1 つ、微分の**やり方**も違った。`piv_velocity_gradient` は
     ``np.gradient``(隣り合う 2 節点の中心差分)。DIC の標準は窓の最小二乗。
     同じ piv 変位場から一様ひずみを読み戻した実測(MARGIN 40 の内側):

         真値 µε   piv_vgrad ± 散    LS w=3 ± 散    LS w=5 ± 散    LS w=9 ± 散
             100   100.4 ± 21.8    100.4 ± 16.0   100.3 ±  6.4   100.3 ±  1.7
             500   501.8 ± 107.2   502.0 ± 78.9   501.4 ± 31.3   501.2 ±  8.6
            2000  1996.3 ± 342.0  1996.6 ± 259.5 1994.8 ± 99.3  1995.6 ± 25.9
           20000 19768.8 ±2909.9 19768.9 ±2210.5 19742.7 ±790.9 19754.1 ± 209.6

     平均はどれも同じ。**散らばりが w=9 で 13.9 倍小さい**(21.8 → 1.7 µε)。
     費用は 0.000 秒。空間分解能を捨てて散らばりを買う取引なので、
     ``window`` を既定にせず呼び手に選ばせる理由でもある。

  E. 相関品質(点ごと)… **別物がある。測ったら肝心な失敗に盲目**
     `piv_cross_correlate` の ``info["peak_ratio"]``(第 1 / 第 2 ピーク)は
     PIV の標準的な SN 比で、**偽ベクトル**は捕まえる。だが「変形して
     しまった / 隠れた / 別物になった」領域は捕まえない。実測:
     u=0.37 px の対の 60x60 画素だけを無関係な模様に差し替えると

         指標                     全域中央値    差し替え領域   健全領域
         peak_ratio                  1.279         1.207        1.304
         correlation_quality         0.9992        0.1101       0.9993

     peak_ratio は健全部との差が 7.5 % しかなく分布が重なる。品質で切って
     誤差がどれだけ減るかを測ると、差は決定的:

         門                   残る割合   変位誤差 RMS [px]
         なし                  100.0 %       1.8110
         zncc >= 0.8            84.9 %       0.0031   ← 584 倍改善
         peak_ratio >= 1.2      81.8 %       1.2183   ← 1.5 倍
         peak_ratio >= 1.3      41.6 %       1.4471   ← 6 割捨てて**悪化**

     → `correlation_quality` を足した。**相関器は作らない** ——
     すでに得られた変位場を受け取り、その場の良し悪しだけを返す。
     `piv_cross_correlate` でも `optical_flow_lk` でも同じ口で測れる。

  F. スペックルの品質指標(平均輝度勾配 MIG など)… **どこにも無い**
     `pivops` にも `fullseye` にも無い(``speckle_filter`` は SAR の
     斑点雑音**除去**で無関係)。撮った画像が DIC に向いているかは
     撮影時に判定したいので、3 行で出せる指標をまとめる口を足した。

内容(3 op):
  変換  `strain_from_displacement` … 変位場 → ひずみ場。**window と method は必須**
  検査  `correlation_quality`      … 与えられた変位場の ZNCC 品質マップ
        `speckle_quality`          … 斑点径・被覆率・勾配 RMS・MIG

規約:
  * 画像は ``img[i, j]``、``i`` = 行 = y、``j`` = 列 = x。
  * **変位場は `pivops` の ``flow2d`` に合わせる**: ``(2, h, w)`` で成分は
    ``(dy, dx)``、単位は画素。`correlation_quality` はこの形で受ける。
    `strain_from_displacement` だけは成分を別々に ``(u, v)`` = ``(dx, dy)``
    で受けるので、**``flow[0]`` を ``u`` に渡すと軸が入れ替わる** ——
    例外にならずもっともらしく間違うので、3 次元配列を渡したら
    直し方つきで拒否する(`_as_component`)。正しくは
    ``strain_from_displacement(flow[1], flow[0], w, method, spacing=info["step"])``。
  * 「測れなかった」は 0 ではなく **NaN**。

来歴(公開文献のみ): Sutton, Orteu & Schreier, *Image Correlation for Shape,
Motion and Deformation Measurements* (Springer, 2009) / Pan et al.,
*Meas. Sci. Technol.* 20 (2009) 062001(2 次元 DIC の総説)/ Pan, Lu & Xie,
*Opt. Lasers Eng.* 48 (2010) 469(平均輝度勾配 MIG)/ International DIC
Society, *A Good Practices Guide for Digital Image Correlation* (2018) /
Malvern, *Introduction to the Mechanics of a Continuous Medium* (1969)
(Green-Lagrange ひずみ)。
"""
from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
from scipy import ndimage

__all__ = [
    "strain_from_displacement", "correlation_quality", "speckle_quality",
    "STRAIN_METHODS",
]

#: `strain_from_displacement` が受けるひずみの定義。既定は**無い**。
STRAIN_METHODS: tuple[str, str] = ("infinitesimal", "green")

#: 分散がこれ以下のサブセットは「測れなかった」とする(輝度が [0, 1] 規格の前提)。
_VAR_EPS = 1e-12


# --------------------------------------------------------------------------- #
# 入力検証 — fail closed                                                       #
# --------------------------------------------------------------------------- #
def _as_image(img: Any, op: str, name: str, min_side: int = 8) -> np.ndarray:
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
    """奇数の窓であることを確かめる。偶数は中心が半画素ずれるので拒否する。"""
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
            f"{op}: {name}={v} must be odd; an even window has no centre node and "
            "would shift every result by half a step")
    return v


def _as_component(a: Any, op: str, name: str) -> np.ndarray:
    """変位の 1 成分を受ける。``flow2d`` を丸ごと渡した事故をここで捕まえる。"""
    arr = np.asarray(a, dtype=np.float64)
    if arr.ndim == 3 and arr.shape[0] == 2:
        raise ValueError(
            f"{op}: {name} looks like a pivops flow2d array {arr.shape}, not a single "
            "component. pivops orders it (dy, dx), so pass u=flow[1], v=flow[0] — "
            "passing flow[0] as u silently transposes the axes and returns a "
            "plausible wrong answer instead of raising")
    if arr.ndim != 2:
        raise ValueError(f"{op}: {name} must be a 2-D field, got ndim={arr.ndim}")
    return arr


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
                             spacing: float = 1.0,
                             ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """変位場からひずみ場を出す。``(exx, eyy, exy)`` を返す。

    引数(``window`` と ``method`` に**既定値は無い**。理由は下記)
      u        x 方向(列)の変位場 [px]。2 次元。
      v        y 方向(行)の変位場 [px]。``u`` と同じ形。
      window   局所最小二乗の窓の一辺。**単位は格子の節点数**(画素ではない)。
               **奇数**。
      method   ``"infinitesimal"`` または ``"green"``。他は例外。
      spacing  節点の間隔 [px]。全画素の密な場なら 1.0(既定)。
               `piv_cross_correlate` の格子なら ``info["step"]``。

    ★ `pivops` から渡すとき —— **成分の順を間違えると静かに壊れる**
      ``flow2d`` は ``(dy, dx)`` の順。正しくは::

          flow, info = piv_cross_correlate(a, b, window=32, overlap=0.75)
          exx, eyy, exy = strain_from_displacement(
              flow[1], flow[0], 9, "green", spacing=info["step"])

      ``flow[0]`` を ``u`` に渡すと x と y が入れ替わり、例外にならずに
      もっともらしい別の答えが返る。3 次元配列をそのまま渡した場合だけは
      直し方つきで拒否できるので、そこは検査してある。

    定義
      ``ux = ∂u/∂x`` などを ``window x window`` の平面当てはめで出し、

      * ``"infinitesimal"``(微小ひずみ、工学ひずみ)
        ``exx = ux``, ``eyy = vy``, ``exy = ½(uy + vx)``
      * ``"green"``(Green-Lagrange)
        ``exx = ux + ½(ux² + vx²)``, ``eyy = vy + ½(uy² + vy²)``,
        ``exy = ½(uy + vx + ux·uy + vx·vy)``

    ★★ なぜ ``method`` に既定値を置かないのか —— 剛体回転が作る嘘
      試験片が θ だけ回っただけで、**材料は 1 ミクロンも伸びていない**とする。
      真のひずみは 0。厳密な剛体回転の変位場
      ``u = (cosθ-1)x - sinθ·y``, ``v = sinθ·x + (cosθ-1)y`` を**画像を通さず
      直接**入れた実測(単位 µε = 1e-6):

          θ [度]   cosθ-1     infinitesimal   piv_velocity_gradient   green
            0.5     -38.1        -38.1              -38.1           5.3e-14
            1.0    -152.3       -152.3             -152.3           9.3e-14
            2.0    -609.2       -609.2             -609.2           2.0e-13
            5.0   -3805.3      -3805.3            -3805.3           6.5e-13

      **2 度で -609 µε。鋼の降伏ひずみ(約 2000 µε)の 3 割。** Green-Lagrange
      は ``exx = (cosθ-1) + ½((cosθ-1)² + sin²θ) = 0`` が**代数的に厳密**なので
      1e-13 に落ちる。既存の `piv_velocity_gradient` は微小ひずみと同じ値を
      返す(= 同じ嘘を持つ)し、`piv_strain_rate` は 2 度で **+1218 µε**
      (``2|cosθ-1|``)を返す —— 流体の線形化した回転 ``u=-ωy, v=ωx`` なら 0 に
      なる量だが、**有限回転では 0 にならない**。

      逆に、材料試験の報告書・規格・ひずみゲージとの突き合わせでは
      微小ひずみが標準で、Green-Lagrange を黙って返すと数字が合わない。
      **どちらが正しいかは場面で反転する。だから選ばせる。**

    ★ ただし「green にすれば安全」ではない —— 推定の誤差はそのまま通る
      Green の補正項 ``½(ux²+vx²)`` は**推定した勾配**から作るので、勾配の
      推定が悪ければ補正も悪い。実測(解析スペックル 256²、剛体回転、
      MARGIN 40 の内側の平均 ± 散らばり、単位 µε):

          θ [度]  cosθ-1  |  piv+LS w=9 微小     green     | lk+LS w=31 微小     green
            2.0   -609.2  |   -42.9 ±  428    564.7 ±  429 |  -698.8 ± 2122   -84.4 ± 2132
            5.0  -3805.3  |   364.9 ± 9532   3843.4 ± 9638 | -1372.9 ±22909  2759.6 ±25685

      ``lk`` の 2 度は教科書どおり(-699 ≒ -609 の嘘 → green で -84 に減る)。
      だが ``piv`` の 2 度は微小ひずみですら -42.9 しか返さない —— 回転する
      サブセットが相関を鈍らせて**勾配の推定自体が ±500 µε 揺れている**ため
      で、そこへ +609 µε の Green 補正を足すと逆に +565 µε になる。
      **5 度以上ではどちらの推定器も散らばりが 1e4 µε を超え、平均に意味が無い。**
      定義の議論が効くのは、まず勾配がその精度で測れているときだけ。

    ★ ``window`` は空間分解能そのもの
      同じ piv 変位場から一様ひずみを読み戻した実測(µε):

          真値      piv_velocity_gradient        w=3            w=5            w=9
           100       100.4 ±   21.8      100.4 ±   16.0  100.3 ±   6.4  100.3 ±   1.7
           500       501.8 ±  107.2      502.0 ±   78.9  501.4 ±  31.3  501.2 ±   8.6
          2000      1996.3 ±  342.0     1996.6 ±  259.5 1994.8 ±  99.3 1995.6 ±  25.9
         20000     19768.8 ± 2909.9    19768.9 ± 2210.5 19742.7 ± 790.9 19754.1 ± 209.6

      平均は全部同じ。**散らばりだけが w とともに 13.9 倍まで縮む。**
      その代わり ``w=9`` は 9 節点(step=8 なら 72 px)を平らとみなすので、
      切欠き先端のような**曲率のあるひずみ場では尖頭を過小に読む**。
      対称窓の最小二乗は 1 次のひずみ場なら厳密に返すが、曲がった場は鈍る。
      既定を置くと、選んだ覚えのないトレードオフの上で数字が出る。

    ★ NaN の扱い —— 0 で埋めない
      ``u`` か ``v`` に NaN があると、その点を含む ``window x window`` の
      当てはめは定義できない。**NaN を含む窓の出力をすべて NaN** にする
      (``u``/``v`` 両方の欠測を合わせた 1 つのマスクを 3 成分に適用)。
      NaN を 0 と見なすと、測れなかった点が「変位 0 の点」として当てはめに
      効き、**周囲に本物に見える偽のひずみ勾配**を作る。

    fail-closed
      * ``u`` / ``v`` が 2 次元でない、形が違う、4x4 未満。
      * ``u`` に ``(2, h, w)`` の ``flow2d`` を丸ごと渡した(直し方つきで拒否)。
      * ``window`` が偶数・3 未満・場より大きい。
      * ``spacing`` が非正・非有限。
      * ``method`` が ``"infinitesimal"`` / ``"green"`` 以外。
      * ``window`` と ``method`` を省いた呼び出しは ``TypeError``
        (既定値を置いていないので Python の引数機構でそのまま落ちる)。
    """
    op = "strain_from_displacement"
    au = _as_component(u, op, "u")
    av = _as_component(v, op, "v")
    if au.shape != av.shape:
        raise ValueError(f"{op}: u and v must have the same shape, got {au.shape} / {av.shape}")
    if min(au.shape) < 4:
        raise ValueError(f"{op}: u / v must be at least 4x4, got {au.shape}")
    if method not in STRAIN_METHODS:
        raise ValueError(
            f"{op}: method must be one of {STRAIN_METHODS}, got {method!r}. "
            "There is no default: a 2 degree rigid rotation reads as -609 microstrain "
            "under 'infinitesimal' and as exactly zero under 'green'")
    w = _odd_positive(window, op, "window")
    if w > min(au.shape):
        raise ValueError(
            f"{op}: window={w} is larger than the field {au.shape}; "
            "the local fit would see only reflected data")
    sp = float(spacing)
    if not math.isfinite(sp) or sp <= 0.0:
        raise ValueError(f"{op}: spacing must be a finite positive pitch, got {spacing!r}")

    valid = np.isfinite(au) & np.isfinite(av)
    if not valid.any():
        raise ValueError(f"{op}: u / v are entirely NaN or Inf; nothing to fit")
    uf = np.where(valid, au, 0.0)
    vf = np.where(valid, av, 0.0)

    ny, nx = au.shape
    yy, xx = np.mgrid[0:ny, 0:nx].astype(np.float64)
    yy *= sp
    xx *= sp
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
# 相関品質(与えられた変位場に対する ZNCC)                                     #
# --------------------------------------------------------------------------- #
def _bilinear(img: np.ndarray, ry: np.ndarray, rx: np.ndarray) -> np.ndarray:
    """``img`` を実数座標 ``(ry, rx)`` で双一次標本化。外は NaN。"""
    ny, nx = img.shape
    inside = (ry >= 0.0) & (ry <= ny - 1) & (rx >= 0.0) & (rx <= nx - 1)
    cy = np.clip(np.nan_to_num(ry, nan=0.0), 0.0, ny - 1.0)
    cx = np.clip(np.nan_to_num(rx, nan=0.0), 0.0, nx - 1.0)
    y0 = np.floor(cy).astype(np.int64)
    x0 = np.floor(cx).astype(np.int64)
    y1 = np.minimum(y0 + 1, ny - 1)
    x1 = np.minimum(x0 + 1, nx - 1)
    fy = cy - y0
    fx = cx - x0
    out = ((1 - fy) * ((1 - fx) * img[y0, x0] + fx * img[y0, x1])
           + fy * ((1 - fx) * img[y1, x0] + fx * img[y1, x1]))
    return np.where(inside, out, np.nan)


def _grid_to_pixels(g: np.ndarray, rows: np.ndarray, cols: np.ndarray,
                    shape: tuple[int, int]) -> np.ndarray:
    """窓格子の場を画素格子へ双一次で広げる。格子の外は端の値を保つ。"""
    ny, nx = shape
    ri = np.interp(np.arange(ny, dtype=np.float64), rows,
                   np.arange(g.shape[0], dtype=np.float64))
    ci = np.interp(np.arange(nx, dtype=np.float64), cols,
                   np.arange(g.shape[1], dtype=np.float64))
    return _bilinear(g, ri[:, None] * np.ones((1, nx)), ci[None, :] * np.ones((ny, 1)))


def correlation_quality(ref: Any, cur: Any, flow: Any, info: Optional[dict] = None,
                        subset: int = 31) -> np.ndarray:
    """与えられた変位場が**どれだけ合っているか**を点ごとに返す ZNCC マップ。

    引数
      ref     基準画像。
      cur     変形後画像。``ref`` と同じ形。
      flow    `pivops` の ``flow2d`` ``(2, h, w)``、成分は ``(dy, dx)`` [px]。
              ``info`` を渡さないなら ``(2, H, W)`` の**全画素**の場。
      info    `piv_cross_correlate` が返した dict。渡すと窓格子の ``flow`` を
              画素へ双一次で広げてから測る。
      subset  相関を取る正方サブセットの一辺 [px]。**奇数**。

    戻り値は入力画像と同じ形の float 配列。値は ``[-1, 1]`` の ZNCC で、
    **測れなかった点は NaN**(サブセットが画像からはみ出す縁、変形後の
    標本点が画像の外へ出る点、分散の無いサブセット)。

    ★ これは相関器ではない —— **既にある変位場の採点係**
      `piv_cross_correlate` も `optical_flow_lk` も `demons_register` も、
      出した変位が正しいかは返さない。ここは ``cur`` を ``flow`` で基準側へ
      引き戻し(双一次)、``ref`` との ZNCC を ``subset`` の箱で測るだけ。
      **どの推定器の出力でも同じ口で採点できる**のが要点で、相関器を
      もう 1 つ増やさずに品質だけを足せる。

      平均と標準偏差の両方を割り引くので、**ゲインとオフセットには不変**。
      露出が変わった対でも「合っているか」だけを見る。

    ★★ 既存の ``info["peak_ratio"]`` では足りない場面がある(実測)
      ``peak_ratio``(第 1 ピーク / 第 2 ピーク)は PIV の標準的な SN 比で、
      **相関面に競合する峰が立つ**種類の失敗を捕まえる。捕まえないのは
      「その場所が別物になった」種類の失敗。u=0.37 px の対のうち 60x60 画素
      だけを無関係な模様に差し替えた実測:

          指標                    差し替え領域   健全領域   区別
          peak_ratio                 1.207        1.304    7.5 % 差(重なる)
          correlation_quality        0.1101       0.9993   9 倍差

      品質で切って変位誤差 RMS がどう変わるか:

          門                  残る割合   誤差 RMS [px]
          なし                 100.0 %      1.8110
          zncc >= 0.8           84.9 %      0.0031    ← 584 倍改善
          peak_ratio >= 1.2     81.8 %      1.2183    ← 1.5 倍
          peak_ratio >= 1.3     41.6 %      1.4471    ← 6 割捨てて**悪化**

      **両方見るのが正しい。** peak_ratio は競合ピークを、ZNCC は
      デコリレーションを見る。片方だけでは穴が開く。

    ★★ 落とし穴 —— **品質が高いことは精度が高いことではない**
      ZNCC はサブピクセルの誤差にほとんど反応しない。真の変位 0.37 px の対に
      わざと誤差を入れた場を採点した実測(斑点の直径 3.8 px):

          変位の誤差 [px]   0.00     0.05     0.10     0.25     0.50    1.00    2.00
          zncc 中央値      0.99945  0.99920  0.99845  0.99330  0.97615 0.90617 0.67655

      **0.05 px 間違えても 0.9992** —— 完全に合っている 0.99945 との差は
      2.5e-4 しかない。この指標が測れるのは「斑点の大きさに比べて大きな
      ずれ・欠測・別物への置き換え」であって、0.01 px の精度ではない。
      一様な雑音で全点が等しく劣化した場合(σ=0.15)も、門で切って残るのは
      21.8 % で誤差 RMS は 0.1736 → 0.1292 の 1.34 倍改善にとどまる ——
      **効くのは失敗が局所的なときだけ。**

    ★ 引き戻しはサブセットごとの平行移動ではなく**場そのもの**
      普通の DIC はサブセットを剛体的にずらして相関を取るが、ここは画素ごとの
      ``flow`` で ``cur`` を歪めてから箱で相関を取る。``flow`` が滑らかなら
      両者は一致し、そうでないなら**こちらのほうが正しい**(サブセット内の
      変形も込みで残差を見るため)。費用も O(N) で済む(256² で 0.003 秒)。

    fail-closed
      * ``ref`` / ``cur`` が 2 次元でない、形が違う、NaN・Inf を含む。
      * ``flow`` が ``(2, h, w)`` でない。
      * ``info`` 無しで ``flow`` が画像と違う形(直し方つきで拒否)。
      * ``info`` に ``rows`` / ``cols`` が無い、格子と ``flow`` の形が食い違う、
        格子がどちらかの軸で 2 未満。
      * ``subset`` が偶数・3 未満・画像より大きい。
    """
    op = "correlation_quality"
    a = _as_image(ref, op, "ref")
    b = _as_image(cur, op, "cur")
    if a.shape != b.shape:
        raise ValueError(f"{op}: ref and cur must have the same shape, got {a.shape} / {b.shape}")
    sub = _odd_positive(subset, op, "subset")
    if sub > min(a.shape):
        raise ValueError(f"{op}: subset={sub} is larger than the image {a.shape}")

    f = np.asarray(flow, dtype=np.float64)
    if f.ndim != 3 or f.shape[0] != 2:
        raise ValueError(
            f"{op}: flow must be a pivops flow2d array (2, h, w) with components "
            f"(dy, dx), got shape {f.shape}")
    ny, nx = a.shape
    if info is None:
        if f.shape[1:] != a.shape:
            raise ValueError(
                f"{op}: flow is {f.shape[1:]} but the image is {a.shape}. Either pass a "
                "dense per-pixel flow, or pass the info dict from piv_cross_correlate "
                "so the window grid can be expanded to pixels")
        dy, dx = f[0], f[1]
    else:
        for key in ("rows", "cols"):
            if key not in info:
                raise ValueError(f"{op}: info is missing {key!r}; pass the dict that "
                                 "piv_cross_correlate returned")
        rows = np.asarray(info["rows"], dtype=np.float64)
        cols = np.asarray(info["cols"], dtype=np.float64)
        if f.shape[1:] != (rows.size, cols.size):
            raise ValueError(
                f"{op}: flow is {f.shape[1:]} but info describes a "
                f"{rows.size}x{cols.size} window grid")
        if rows.size < 2 or cols.size < 2:
            raise ValueError(
                f"{op}: the window grid is {rows.size}x{cols.size}; expanding it to "
                "pixels needs at least 2 windows per axis")
        dy = _grid_to_pixels(f[0], rows, cols, a.shape)
        dx = _grid_to_pixels(f[1], rows, cols, a.shape)

    yy, xx = np.mgrid[0:ny, 0:nx].astype(np.float64)
    warped = _bilinear(b, yy + dy, xx + dx)

    ok = np.isfinite(warped)
    g = np.where(ok, warped, 0.0)
    cover = ndimage.uniform_filter(ok.astype(np.float64), sub, mode="constant")
    mf = ndimage.uniform_filter(a, sub, mode="constant")
    mg = ndimage.uniform_filter(g, sub, mode="constant")
    mff = ndimage.uniform_filter(a * a, sub, mode="constant")
    mgg = ndimage.uniform_filter(g * g, sub, mode="constant")
    mfg = ndimage.uniform_filter(a * g, sub, mode="constant")
    var_f = mff - mf * mf
    var_g = mgg - mg * mg
    den = var_f * var_g
    good = (cover > 1.0 - 1e-9) & (var_f > _VAR_EPS) & (var_g > _VAR_EPS)
    zncc = np.where(good, (mfg - mf * mg) / np.sqrt(np.where(good, den, 1.0)), np.nan)

    # サブセットが画像の外へはみ出す縁は測っていない。
    h = sub // 2
    edge = np.ones((ny, nx), dtype=bool)
    edge[h:ny - h, h:nx - h] = False
    return np.where(edge, np.nan, zncc)


# --------------------------------------------------------------------------- #
# スペックルの品質                                                              #
# --------------------------------------------------------------------------- #
def speckle_quality(img: Any) -> dict[str, float]:
    """撮ったスペックルが DIC に向いているかを 4 つの数字で返す。

    `pivops` にも `fullseye` にも無い(``speckle_filter`` は SAR の斑点雑音
    **除去**で別物)。撮影の場で「この模様で測れるか」を判定するための口。

    引数
      img  スペックル画像(2 次元)。輝度の規格は問わないが、``coverage`` は
           画像内の最小・最大を基準にした相対しきい値で数える。

    戻り値は ``dict``:

      ``mig``                     平均輝度勾配 ``sqrt(mean(Ix² + Iy²))``。
                                  Pan らの DIC 品質指標。変位の分散の下限が
                                  ``σ_noise / (mig √N)`` で決まるので、これが
                                  小さいと何をしても測れない。
      ``grad_rms``                x 方向だけの ``sqrt(mean(Ix²))``。
      ``coverage``                ``0.2*(max-min) + min`` を超える画素の割合。
      ``mean_blob_diameter_px``   斑点の平均直径 [px] の**推定値**(下記)。

    ★ ``mean_blob_diameter_px`` は推定であって測定ではない
      平均を引いた画像の自己相関の動径平均が 0.5 に落ちる半径 ``R½`` を線形
      内挿で求め、``diameter = √2 · R½`` を返す。``√2`` の根拠: 1σ 半径 ``r`` の
      ガウス斑点をランダムに撒いた場の自己相関は 1σ が ``r√2`` のガウスなので
      ``R½ = 2r√(ln2)``、斑点の FWHM は ``2r√(2ln2)``、比がちょうど ``√2``。
      つまり**斑点がガウスで位置が無相関という仮定の上でだけ** FWHM に一致する。

      実測(左: 解析スペックル、1σ 半径を振り被覆率が揃うよう個数を調整。
      右: `piv_synth_particles`、``diameter_px`` は 2σ なので FWHM は
      ``1.1774 × diameter_px``):

          1σ r   FWHM   推定   比   |  d_px   FWHM   推定   比    cov     mig
          0.6    1.41   1.36  0.97  |   1.5   1.77   1.80  1.02  0.043  0.1351
          1.0    2.35   2.39  1.01  |   2.5   2.94   2.93  1.00  0.106  0.1676
          1.6    3.77   3.77  1.00  |   4.0   4.71   4.69  1.00  0.159  0.1775
          2.5    5.89   5.77  0.98  |   6.0   7.06   7.01  0.99  0.286  0.1764
          4.0    9.42   9.18  0.97  |

      **ガウス斑点なら 3 % 以内**。実物のスペックル(印刷・スプレー)は
      ガウスではないので、この表は換算の算数が合っていることの確認であって、
      実写での精度ではない。**何に偏るか**:

      * 斑点の形がガウスでないと ``√2`` の換算そのものがずれる。
      * 低周波のむら(照明勾配)があると自己相関の裾が持ち上がり**過大**に出る。
        先に高域通過を掛けること。
      * 自己相関は循環相関(FFT)なので、周期性のある背景があると乱れる。
      * 環の代表半径は**環内の半径の平均**を使う。ビン番号を使うと半径 1 の環に
        対角の √2 が混ざり、1σ=0.6 px で径が **0.80 倍**(2 割過小)に出た。

    ★ MIG は下限を切る指標であって、最大化する目的関数ではない
      上の左表で ``mig`` は斑点が細かいほど大きい(1σ=4.0 の 0.0384 に対し
      1σ=0.6 で 0.1127、2.9 倍)。だが直径 1.4 px のスペックルは標本化が
      足りず、`examples/poc_dic_strain.py` の 9 節の実測では偏りも散らばりも
      最悪になる。**MIG を最大化すると測れないスペックルを選ぶ。**
      右表の粒子像では ``d=4.0`` で頭打ちになり ``d=6.0`` でわずかに下がる ——
      同じ指標が入力の作り方で単調にも非単調にもなるので、
      **絶対値ではなく同じ撮り方どうしの比較に使うこと。**

    ★ ``coverage`` のしきい値は Otsu ではない
      ``0.2*(max-min) + min`` の固定しきい値。Otsu は 2 峰の分布を仮定するが、
      スペックルの輝度分布は斑点の重なりで単峰になることが多く、Otsu だと
      **しきい値が画像ごとに動いて比較できなくなる**。固定なら少なくとも
      同じ規格の画像どうしは比べられる。

    ★ MIG は単位を持つ
      「輝度 / px」。8 bit 整数のまま渡すか [0, 1] に規格化してから渡すかで
      255 倍違う。**同じ規格の画像どうしでしか比べられない。**

    fail-closed
      * 2 次元でない / 8x8 未満 / NaN・Inf を含む。
      * 画像が完全に一様(``max == min``)—— 斑点が 1 つも無い。
      * 自己相関が 0.5 を切らない(視野より斑点が大きい)—— このときだけ
        ``mean_blob_diameter_px`` が ``nan``。他の 3 つは返す。
    """
    op = "speckle_quality"
    a = _as_image(img, op, "img")
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
