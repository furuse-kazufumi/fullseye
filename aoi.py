# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""AOI front-end — the three steps that run *before* anything is measured (numpy only).

自動外観検査(AOI)の実務では、欠陥を探す前に必ず 3 つの前処理が入る。この repo は
「測る」層(:mod:`measure1d` / :mod:`blob2d` / :mod:`shapestats` / :mod:`spc`)を深く
持っているのに、その**手前の 3 段**が 4 層(``fullseye.<名前>`` / ``fullseye.op.<名前>`` /
``fullseye.ledger.<名前>`` / ``fullseye.op_find``)のどこにも無かった(2026-09-15 に全層を
引いて確認。近いものと「なぜ代わりにならないか」は下の表)。

  * **photometric** — :func:`flat_field_correct`: 照明の落ちとセンサの感度ばらつきを
    **暗電流つきの割り算**で戻す。既存の ``background_flatten`` は低次曲面の**引き算**で、
    掛け算で効く利得も暗電流も戻せない(この差は下の「なぜ足したか」で数値にした)。
  * **geometric** — :func:`register_image`: 検査画像を基準画像へ合わせる**平行移動 1 個**を、
    **合っていないと分かる量つき**で返す。平行移動しか扱わないので、回転や倍率を渡されたら
    残差が跳ね、``consistent`` が False になる —— 黙って「いちばん近い平行移動」を成功として
    返さない。
  * **aggregate** — :func:`tiled_map`: 画像をタイルに割り、タイルごとの量を**小さな地図**に
    する。半端なタイルを黙って捨てず、捨てたなら返り値に件数を出す。

## なぜ足したか(2026-09-15、全層を引いた実測)

=============================  ====================================================
既にあったもの                  なぜ代わりにならないか
=============================  ====================================================
``background_flatten``         低次曲面を**引く**(加算模型)。照明の落ちは**掛け算**で
                               効くので、利得 0.4 の隅は引き算では戻らない。暗電流の
                               項も無い。
``xsp_detrend_flatten``        1 次のトレンド除去。つまみが ``a``/``b`` の 2 つだけで、
                               基準となるフラット画像を渡す口が無い。
``vignette`` / ``aug_vignette``  照明の落ちを**掛ける**側(合成・水増し)。戻す側ではない。
``relative_illumination``      cos⁴ 則の**曲線**を返す光学計算。画像を補正しない。
``frame_align``                星の対応から変換を推定する。点状の特徴が要り、周期構造では
                               ``inlier_ratio`` 1.00 のまま外す(その op 自身の docstring に
                               実測が書いてある)。
``piv_cross_correlate``        窓ごとの**場**を返す。画像 2 枚の並進を 1 個返す口ではなく、
                               台帳の口は宣言 out 型に合わせて ``info`` を捨てる。
``ncc_locate``                 テンプレートを ``set_match_template`` で先に積む 2-D op。
                               返りは ``[相関, y, x]`` の 3 要素で、不定性の量が出ない。
``scale.process_tiled``        タイルごとに op を掛けて**同じ大きさの画像**を返す
                               (記憶量を抑える道具)。タイルごとの**量**は返らない。
``vol_tiled_map``              その 3-D 版。やはり形を保つ側。
=============================  ====================================================

## 型語彙: **新語を 1 つも作らない**

3 op の入出力は既存の ``image2d``(2-D の画像)と ``table``(dict)にそのまま収まる。
:func:`register_image` が ``table`` を返すのは意図的で、**並進だけを返すと不定性の量が
捨てられる**ため —— 台帳の adapter はタプルの 2 番目以降を捨てるので、``(shift, info)``
にすると ``info`` へ ``.raw`` 無しには届かなくなる(``piv_cross_correlate`` で実際に
起きた事故)。dict 1 つで返せば、どの経路から呼んでも量が揃って出る。

## 来歴(公開文献のみ。docs/PROVENANCE.md の命名規則により製品名・企業名は書かない)

* フラットフィールド補正 ``(I - D) / (F - D)`` —— J. Janesick, *Scientific Charge-Coupled
  Devices*, SPIE Press 2001(暗電流・画素応答非一様性の標準的な扱い)。
* 位相相関による並進推定 —— C. Kuglin & D. Hines, "The phase correlation image alignment
  method", *Proc. IEEE Int. Conf. Cybernetics and Society*, 1975.
* サブピクセルの上標本 DFT —— M. Guizar-Sicairos, S. Thurman & J. Fienup, "Efficient
  subpixel image registration algorithms", *Optics Letters* 33:156, 2008.
* 正規化相互相関 —— J. P. Lewis, "Fast Normalized Cross-Correlation", *Vision Interface*, 1995.
"""
from __future__ import annotations

import numpy as np

#: 受け取る画像の画素数の上限(倍精度へ昇格する前に確かめる)。
MAX_IMAGE_ELEMENTS = 1 << 24

#: :func:`register_image` の相関の取り方。
REGISTER_METHODS = ("phase", "cross")

#: :func:`register_image` の窓関数。``"none"`` は端の不連続をそのまま食うので、
#: 周期を仮定できる合成画像でしか勧められない。
REGISTER_WINDOWS = ("hann", "none")

#: :func:`tiled_map` が出せるタイルごとの量。``"mean"`` と ``"sum"`` と ``"count"`` は
#: **分解可能**(タイル統計から全体量を復元できる)で、残りはそうではない。
TILE_STATS = ("mean", "std", "min", "max", "median", "sum", "count", "ptp")

#: 第 2 ピークがこの比を超えたら「答えが 1 つに決まらない」と見なす既定値。
#: 市松や縞のように同じ模様が周期的に並ぶ画像では、格子 1 つぶんずれた答えも
#: 同じ高さの山を作るので、比は 1 に近づく(:func:`register_image` の実測表を参照)。
DEFAULT_AMBIGUITY_RATIO = 0.8

#: 平行移動だけで説明できると見なす残差の上限(基準画像の rms に対する比)。
DEFAULT_RESIDUAL_TOLERANCE = 0.25


# --------------------------------------------------------------------------- #
# 入力の検査(fail-closed)。黙って近似しない —— 理由つきで拒む。               #
# --------------------------------------------------------------------------- #
def _require_image(a, name: str, op: str) -> np.ndarray:
    """2-D の有限 float64 画像であることを確かめて返す。"""
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked (invalid) entries — "
                         "fill or drop them explicitly" % (op, name))
    if isinstance(a, (str, bytes)):
        raise ValueError("%s: %s is a string — expected a 2-D array of numbers" % (op, name))
    arr = np.asarray(a)
    if arr.dtype.kind == "c":
        raise ValueError("%s: %s is complex — expected a real image" % (op, name))
    if arr.dtype.kind not in "fiub":
        raise ValueError("%s: %s has dtype %r — expected a numeric image" % (op, name, arr.dtype))
    arr = arr.astype(np.float64, copy=False)
    if arr.ndim != 2:
        raise ValueError("%s: %s must be a 2-D image, got shape %r" % (op, name, arr.shape))
    if arr.shape[0] < 2 or arr.shape[1] < 2:
        raise ValueError("%s: %s must be at least 2x2, got %r" % (op, name, arr.shape))
    if arr.size > MAX_IMAGE_ELEMENTS:
        raise ValueError("%s: %s has %d pixels, over the %d cap (aoi.MAX_IMAGE_ELEMENTS)"
                         % (op, name, arr.size, MAX_IMAGE_ELEMENTS))
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s has %d non-finite pixel(s) — a NaN/Inf here spreads over the "
                         "whole result, so it is refused rather than propagated"
                         % (op, name, int((~np.isfinite(arr)).sum())))
    return np.ascontiguousarray(arr)


def _same_shape(a: np.ndarray, b: np.ndarray, na: str, nb: str, op: str) -> None:
    if a.shape != b.shape:
        raise ValueError("%s: %s %r and %s %r must have the same shape"
                         % (op, na, a.shape, nb, b.shape))


def _choice(value, name: str, allowed, op: str):
    if value not in allowed:
        raise ValueError("%s: %s must be one of %r, got %r" % (op, name, tuple(allowed), value))
    return value


def _positive_int(value, name: str, op: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, value))
    v = int(value)
    if v < minimum:
        raise ValueError("%s: %s must be >= %d, got %d" % (op, name, minimum, v))
    return v


# --------------------------------------------------------------------------- #
# photometric                                                                  #
# --------------------------------------------------------------------------- #
def flat_field_correct(image, flat, dark=None, target=None, min_response=None, clip=True):
    """照明ムラとセンサ感度のばらつきを、暗電流つきの割り算で戻す。→ 補正済み画像。

    検査画像 ``I``、フラット画像(一様な面を撮ったもの)``F``、暗画像(遮光して撮ったもの)
    ``D`` から::

        out = (I - D) / (F - D) * target

    ``target`` の既定は ``mean(F - D)`` で、こうすると**入力の明るさの尺度が保たれる**
    (補正は「ムラを平らにする」だけで、全体の明るさを勝手に変えない)。

    **暗電流を無視すると戻らない。** ``D`` を省くと ``D = 0`` として扱うが、実際に暗電流が
    ある系ではそれは誤りで、補正後も勾配が残る。この repo に同梱の門
    (``tests/test_aoi.py::test_flat_field_without_dark_does_not_recover``)は、暗電流 0.05 を
    与えた合成系で **dark を渡したときの相対誤差 4.6e-16 に対し、省くと 0.11(24 兆倍)** に
    なることを実測して固定してある —— 式が本当に ``D`` を使っている証拠であり、同時に
    「省いてもそれらしい絵が出る」ことの警告でもある。

    **ゼロ割りは黙って通さない(既定は fail-closed)。** ``F - D`` に 0 以下の画素があると
    ``ValueError`` を送出する。「そこは応答が無い画素」だと分かっていて先へ進めたいときだけ、
    ``min_response`` に**明示の下限**(正の実数)を与える —— そのとき応答はその値で下から
    抑えられ、割り算は有限に保たれる。既定で下限を置かないのは、下限を既定にすると
    「死んだ画素の上に、それらしい値が生える」ことが黙って起きるため。

    Args:
        image: 検査画像 ``(H, W)``。
        flat: フラット画像 ``(H, W)``。``image`` と同じ形。
        dark: 暗画像 ``(H, W)`` か ``None``(= 暗電流 0 として扱う)。
        target: 補正後の基準レベル。``None`` なら ``mean(flat - dark)``。
        min_response: ``flat - dark`` の下限(正)。``None`` なら 0 以下を拒否する。
        clip: ``True``(既定)なら結果を ``[0, 1]``(この library の画像の約束)へ丸める。
            **飽和はここで起きる**ので、生の値が要るなら ``False`` にする。

    Returns:
        ``(H, W)`` float64。``clip=True`` なら値域は ``[0, 1]``、``clip=False`` なら
        入力しだいで 1 を超えうる。dtype はどちらでも float64。

    Raises:
        ValueError: 形が違う / 2-D でない / 非有限 / ``flat - dark`` が 0 以下
            (``min_response`` 未指定時)/ ``min_response`` や ``target`` が正の有限でない。
    """
    op = "flat_field_correct"
    img = _require_image(image, "image", op)
    flt = _require_image(flat, "flat", op)
    _same_shape(img, flt, "image", "flat", op)
    if dark is None:
        drk = np.zeros_like(img)
    elif np.ndim(dark) == 0 and not isinstance(dark, (str, bytes)):
        # 暗電流が一様(遮光した平均値 1 つ)という、現場でいちばん多い渡し方。
        if isinstance(dark, bool) or not isinstance(dark, (int, float, np.integer,
                                                           np.floating)):
            raise ValueError("%s: dark must be a 2-D image or a real number, got %r"
                             % (op, dark))
        dval = float(dark)
        if not np.isfinite(dval):
            raise ValueError("%s: dark must be finite, got %r" % (op, dark))
        drk = np.full_like(img, dval)
    else:
        drk = _require_image(dark, "dark", op)
        _same_shape(img, drk, "image", "dark", op)

    response = flt - drk
    if min_response is None:
        bad = int((response <= 0.0).sum())
        if bad:
            raise ValueError(
                "%s: flat - dark has %d pixel(s) <= 0 (min %.6g) — dividing by them would be a "
                "zero-divide. Give an explicit positive `min_response` floor if those pixels are "
                "known-dead and you want to continue." % (op, bad, float(response.min())))
    else:
        if (isinstance(min_response, bool)
                or not isinstance(min_response, (int, float, np.integer, np.floating))
                or not np.isfinite(float(min_response)) or float(min_response) <= 0.0):
            raise ValueError("%s: min_response must be a positive finite number, got %r"
                             % (op, min_response))
        response = np.maximum(response, float(min_response))

    if target is None:
        tgt = float(np.mean(response))
    else:
        if (isinstance(target, bool)
                or not isinstance(target, (int, float, np.integer, np.floating))
                or not np.isfinite(float(target)) or float(target) <= 0.0):
            raise ValueError("%s: target must be a positive finite number, got %r" % (op, target))
        tgt = float(target)
    if tgt <= 0.0:
        raise ValueError("%s: the reference level (mean of flat - dark) is %.6g, which is not "
                         "positive — the flat image carries no signal" % (op, tgt))

    out = (img - drk) / response * tgt
    if clip:
        out = np.clip(out, 0.0, 1.0)
    return np.ascontiguousarray(out, dtype=np.float64)


# --------------------------------------------------------------------------- #
# geometric                                                                    #
# --------------------------------------------------------------------------- #
def _hann2d(shape) -> np.ndarray:
    """2-D の Hann 窓。端の不連続が相関面に十字の筋を作るのを抑える。"""
    h, w = shape
    wy = np.hanning(h + 2)[1:-1] if h > 1 else np.ones(1)
    wx = np.hanning(w + 2)[1:-1] if w > 1 else np.ones(1)
    return np.outer(wy, wx)


def _upsampled_dft(data: np.ndarray, region: int, factor: int, offsets) -> np.ndarray:
    """行列積による上標本 DFT(Guizar-Sicairos 2008)。

    相関面の**ピーク近傍だけ**を細かく評価する。画像全体をゼロ詰めして逆変換するのに
    比べて、記憶量も計算量も領域の大きさだけで決まる。
    """
    out = data
    for n_items, ax_offset in zip(data.shape[::-1], offsets[::-1]):
        kernel = ((np.arange(region) - ax_offset)[:, None]
                  * np.fft.fftfreq(n_items, factor))
        out = np.tensordot(np.exp(-2j * np.pi * kernel), out, axes=(1, -1))
    return out


def _shift_fourier(img: np.ndarray, dy: float, dx: float) -> np.ndarray:
    """帯域制限を仮定した副画素の平行移動(残差を測るためだけに使う)。"""
    h, w = img.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    ramp = np.exp(-2j * np.pi * (fy * dy + fx * dx))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * ramp))


def register_image(reference, moving, upsample=20, method="phase", window="hann",
                   max_shift=None, ambiguity_ratio=DEFAULT_AMBIGUITY_RATIO,
                   residual_tolerance=DEFAULT_RESIDUAL_TOLERANCE):
    """検査画像を基準画像へ合わせる平行移動を、合っていないと分かる量つきで返す。→ dict。

    相関面(既定は位相相関)の山を整数画素で見つけ、その近傍を上標本 DFT で
    ``1/upsample`` 画素まで詰める。返りは dict 1 つで、**並進だけでなく「その答えが
    どれくらい当てになるか」を必ず一緒に返す**。

    符号の約束: ``moving(y, x) ≈ reference(y - dy, x - dx)``。つまり ``moving`` は
    ``reference`` を ``(dy, dx)`` だけずらしたもので、``moving`` を ``(-dy, -dx)`` 動かせば
    重なる。``np.roll(ref, (3, 5), axis=(0, 1))`` を渡せば ``dy=3, dx=5`` が返る。

    **平行移動しか扱わない。** 回転や倍率が入った対を渡しても例外は出ないが、
    ``residual`` が跳ね ``consistent`` が False になる。実測(128x128 の合成模様):

    ===================  ==========  ============  ============
    与えた変形            residual    peak_ratio    consistent
    ===================  ==========  ============  ============
    並進 (3, 5) px       0.0000      0.10          True
    並進 (2.5, -1.5) px  0.0182      0.13          True
    回転 5 度            0.5306      0.29          **False**
    倍率 1.05            0.3411      0.22          **False**
    ===================  ==========  ============  ============

    数字は ``tests/test_aoi.py`` が固定している。**黙って「いちばん近い平行移動」を
    成功として返さない**ための量がこの ``residual`` で、返り値を見ずに ``dy``/``dx`` だけ
    使うと回転を並進として飲み込む。

    **周期のある模様では答えが 1 つに決まらない。** 市松や縞は、格子 1 つぶんずれた
    答えも同じ高さの山を作る。そのとき ``peak_ratio`` が 1 に近づき ``ambiguous`` が
    True になる —— 返る ``dy``/``dx`` は**同じくらいもっともらしい答えのうちの 1 つ**で
    あって、間違いではないが一意でもない。実測では周期 8 px の市松で ``peak_ratio``
    1.000 / ``ambiguous`` True、雑な模様では 0.10 前後。

    Args:
        reference: 基準画像 ``(H, W)``。
        moving: 合わせる画像 ``(H, W)``。``reference`` と同じ形。
        upsample: 副画素の分解能の逆数(``1`` なら整数画素まで)。
        method: :data:`REGISTER_METHODS`。``"phase"`` は振幅を正規化するので明るさの
            違いに強く、``"cross"`` は素の相互相関で雑音に強い。
        window: :data:`REGISTER_WINDOWS`。
        max_shift: 探索するずれの上限[px]。``None`` なら画像の半分。
        ambiguity_ratio: ``peak_ratio`` がこれ以上なら ``ambiguous=True``。
        residual_tolerance: ``residual`` がこれ以下なら ``consistent=True``。

    Returns:
        dict。``dy`` / ``dx``(px、副画素)、``peak``(正規化した山の高さ ``[0, 1]``)、
        ``peak_ratio``(第 2 の山 / 第 1 の山。1 に近いほど当てにならない)、
        ``ambiguous``(bool)、``residual``(合わせたあとの残差 rms / 基準の rms)、
        ``consistent``(bool。平行移動だけで説明できるか)、``model``(``"translation"``)、
        ``method`` / ``window`` / ``upsample``。

    Raises:
        ValueError: 形が違う / 2-D でない / 非有限 / どちらかが定数画像(模様が無いので
            ずれが定義できない)/ 引数が値域外。
    """
    op = "register_image"
    ref = _require_image(reference, "reference", op)
    mov = _require_image(moving, "moving", op)
    _same_shape(ref, mov, "reference", "moving", op)
    _choice(method, "method", REGISTER_METHODS, op)
    _choice(window, "window", REGISTER_WINDOWS, op)
    ups = _positive_int(upsample, "upsample", op)

    # 定数画像は「情報ゼロ」。相関面が平らになり、argmax が原点を返して
    # 「ずれ 0 で完全に合った」という嘘になるので、手前で拒む。
    for arr, name in ((ref, "reference"), (mov, "moving")):
        if float(np.ptp(arr)) == 0.0:
            raise ValueError("%s: %s is constant (every pixel = %.6g) — a flat image carries no "
                             "structure, so no shift is defined. This is refused rather than "
                             "returning (0, 0) with a perfect score."
                             % (op, name, float(arr.flat[0])))

    h, w = ref.shape
    lim = min(h, w) / 2.0 if max_shift is None else float(max_shift)
    if not np.isfinite(lim) or lim <= 0.0:
        raise ValueError("%s: max_shift must be a positive finite number, got %r" % (op, max_shift))

    a = ref - ref.mean()
    b = mov - mov.mean()
    if window == "hann":
        win = _hann2d(ref.shape)
        a = a * win
        b = b * win

    fa, fb = np.fft.fft2(a), np.fft.fft2(b)
    prod = fa * np.conj(fb)
    if method == "phase":
        mag = np.abs(prod)
        # 0 で割らない。振幅が消えている周波数は情報が無いので 0 のまま残す。
        prod = np.divide(prod, mag, out=np.zeros_like(prod), where=mag > 1e-12)
    corr = np.real(np.fft.ifft2(prod))

    # 探索範囲の外は見ない(折り返した座標で評価する)。
    dy_grid = np.fft.fftfreq(h, 1.0 / h)[:, None]
    dx_grid = np.fft.fftfreq(w, 1.0 / w)[None, :]
    inside = (np.abs(dy_grid) <= lim) & (np.abs(dx_grid) <= lim)
    masked = np.where(inside, corr, -np.inf)

    peak_idx = np.unravel_index(int(np.argmax(masked)), masked.shape)
    peak_val = float(corr[peak_idx])

    # 第 2 の山 —— 第 1 の山の周り 3x3 を除いた最大値。周期構造ではここが第 1 に並ぶ。
    guard = masked.copy()
    for ddy in (-1, 0, 1):
        for ddx in (-1, 0, 1):
            guard[(peak_idx[0] + ddy) % h, (peak_idx[1] + ddx) % w] = -np.inf
    finite = guard[np.isfinite(guard)]
    second = float(finite.max()) if finite.size else 0.0
    denom = abs(peak_val) if abs(peak_val) > 1e-15 else 1e-15
    peak_ratio = float(max(second, 0.0) / denom)

    shifts = np.array([float(dy_grid[peak_idx[0], 0]), float(dx_grid[0, peak_idx[1]])])
    if ups > 1:
        # ピーク近傍だけを細かく評価する(Guizar-Sicairos 2008)。
        region = int(np.ceil(ups * 1.5))
        dftshift = float(region // 2)
        coarse = np.round(shifts * ups) / ups
        offsets = dftshift - coarse * ups
        fine = _upsampled_dft(np.conj(prod), region, ups, offsets)
        fine = np.abs(np.conj(fine))
        fine_idx = np.unravel_index(int(np.argmax(fine)), fine.shape)
        shifts = coarse + (np.array(fine_idx, dtype=np.float64) - dftshift) / ups
    dy, dx = float(shifts[0]), float(shifts[1])

    # 残差 —— **合っていないことが分かる量**。moving を (-dy, -dx) 戻して基準と比べる。
    back = _shift_fourier(mov, -dy, -dx)
    margin = int(np.ceil(max(abs(dy), abs(dx)))) + 1
    if 2 * margin < min(h, w) - 2:
        sl = (slice(margin, h - margin), slice(margin, w - margin))
    else:                                   # ずれが大きすぎて中央が取れないときは全面
        sl = (slice(None), slice(None))
    ra, rb = ref[sl], back[sl]
    ra = ra - ra.mean()
    rb = rb - rb.mean()
    base = float(np.sqrt(np.mean(ra * ra)))
    residual = float(np.sqrt(np.mean((ra - rb) ** 2)) / base) if base > 1e-15 else float("inf")

    # 正規化した山の高さ(相関係数と同じ尺度)。method によらず比べられるようにする。
    norm = float(np.sqrt(np.mean(a * a) * np.mean(b * b))) * a.size
    peak_norm = float(peak_val / norm) if norm > 1e-15 else 0.0

    return {
        "dy": dy, "dx": dx,
        "peak": peak_norm,
        "peak_ratio": peak_ratio,
        "ambiguous": bool(peak_ratio >= float(ambiguity_ratio)),
        "residual": residual,
        "consistent": bool(residual <= float(residual_tolerance)),
        "model": "translation",
        "method": method,
        "window": window,
        "upsample": ups,
    }


# --------------------------------------------------------------------------- #
# aggregate                                                                    #
# --------------------------------------------------------------------------- #
def tiled_map(image, tile=16, stat="mean", overlap=0, drop_partial=False):
    """画像をタイルに割り、タイルごとの量を小さな地図にする。→ dict。

    ``tile`` 画素角のタイルを ``tile - overlap`` 画素ずつずらして敷き、各タイルの中の量
    (:data:`TILE_STATS`)を 1 つずつ計算して ``(h, w)`` の地図にする。AOI では、明るさの
    むら・ざらつき・欠陥の密度を「どのあたりが怪しいか」の粗い地図にして、次の段
    (閾値・:mod:`spc` の管理図)へ渡すのに使う。

    **半端なタイルを黙って捨てない。** 画像の辺が ``tile`` で割り切れないとき、縁のタイルは
    小さくなる。既定(``drop_partial=False``)ではそれも計算に入れ、``partial_tiles`` に
    件数を出す。``drop_partial=True`` にすると縁を落とすが、そのときも ``dropped_tiles`` と
    ``covered_fraction`` に**何をどれだけ捨てたか**が出る —— どちらを選んでも、捨てたことが
    返り値に残る。

    **分解可能な量なら検算できる。** ``overlap=0`` なら、タイルは画像を重なりなく覆う。
    ``stat="mean"`` の地図を ``counts`` で重み付けして平均すると、**全画素の平均に一致する**
    (門で 1e-15 の水準を固定してある)。``"std"`` や ``"median"`` にこの性質は無い ——
    タイルごとの標準偏差を平均しても全体の標準偏差にはならないので、地図を「まとめ直す」
    使い方をするなら ``"mean"`` / ``"sum"`` / ``"count"`` に限ること。

    ``tile`` が画像より大きいときは、タイルは 1 枚(= 画像全体)で ``partial_tiles=1``。
    ``drop_partial=True`` だと残るタイルが 1 枚も無くなるので ``ValueError`` にする
    (空の地図を返すと、後段が「異常なし」と読む)。

    Args:
        image: ``(H, W)``。
        tile: タイルの一辺[px]。1 以上。
        stat: :data:`TILE_STATS` のどれか。
        overlap: 隣のタイルと重ねる画素数。``0 <= overlap < tile``。
        drop_partial: 縁の半端なタイルを落とすか。

    Returns:
        dict。``map``(``(h, w)`` float64)、``counts``(``(h, w)`` int、タイルごとの画素数)、
        ``rows`` / ``cols``(各タイルの左上の座標)、``tile`` / ``overlap`` / ``stat``、
        ``partial_tiles``(小さいタイルの数)、``dropped_tiles``(落とした数)、
        ``covered_fraction``(残したタイルが覆う画素の割合。``overlap>0`` では重なるので
        1 を超えうる)、``shape``(元の画像の形)。

    Raises:
        ValueError: 2-D でない / 非有限 / ``stat`` が未知 / ``overlap`` が範囲外 /
            ``drop_partial=True`` でタイルが 1 枚も残らない。
    """
    op = "tiled_map"
    img = _require_image(image, "image", op)
    t = _positive_int(tile, "tile", op)
    _choice(stat, "stat", TILE_STATS, op)
    ov = _positive_int(overlap, "overlap", op, minimum=0)
    if ov >= t:
        raise ValueError("%s: overlap must be < tile (%d), got %d — a step of zero or less would "
                         "never advance" % (op, t, ov))
    step = t - ov
    h, w = img.shape

    rows = list(range(0, max(h - t, 0) + 1, step))
    cols = list(range(0, max(w - t, 0) + 1, step))
    # 端が余っていれば、そこから始まる縁のタイルを 1 枚足す(捨てない側の既定)。
    if rows and rows[-1] + t < h:
        rows.append(rows[-1] + step)
    if cols and cols[-1] + t < w:
        cols.append(cols[-1] + step)
    if not rows:
        rows = [0]
    if not cols:
        cols = [0]

    kept_r, kept_c, dropped = [], [], 0
    for r in rows:
        if drop_partial and r + t > h:
            dropped += len(cols)
            continue
        kept_r.append(r)
    for c in cols:
        if drop_partial and c + t > w:
            dropped += len(kept_r)
            continue
        kept_c.append(c)
    if not kept_r or not kept_c:
        raise ValueError(
            "%s: drop_partial=True leaves no whole %dx%d tile in a %dx%d image — an empty map "
            "would read downstream as 'nothing found'. Use a smaller tile, or keep the partial "
            "tiles (drop_partial=False)." % (op, t, t, h, w))

    out = np.empty((len(kept_r), len(kept_c)), dtype=np.float64)
    counts = np.empty((len(kept_r), len(kept_c)), dtype=np.int64)
    partial = 0
    for i, r in enumerate(kept_r):
        r1 = min(r + t, h)
        for j, c in enumerate(kept_c):
            c1 = min(c + t, w)
            block = img[r:r1, c:c1]
            if block.shape != (t, t):
                partial += 1
            counts[i, j] = block.size
            if stat == "mean":
                out[i, j] = block.mean()
            elif stat == "std":
                out[i, j] = block.std()
            elif stat == "min":
                out[i, j] = block.min()
            elif stat == "max":
                out[i, j] = block.max()
            elif stat == "median":
                out[i, j] = np.median(block)
            elif stat == "sum":
                out[i, j] = block.sum()
            elif stat == "count":
                out[i, j] = float(block.size)
            else:                                    # "ptp"
                out[i, j] = float(np.ptp(block))

    return {
        "map": out,
        "counts": counts,
        "rows": np.asarray(kept_r, dtype=np.int64),
        "cols": np.asarray(kept_c, dtype=np.int64),
        "tile": t,
        "overlap": ov,
        "stat": stat,
        "partial_tiles": int(partial),
        "dropped_tiles": int(dropped),
        "covered_fraction": float(counts.sum()) / float(img.size),
        "shape": (int(h), int(w)),
    }


#: この族の op(:mod:`opsaoi` が同じ並びを台帳にする)。
AOI_OPS = (flat_field_correct, register_image, tiled_map)
