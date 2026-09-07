"""Input/output enrichment for fullseye — coercion, colormap visualisation, and
export helpers so other projects can *feed* varied inputs and *see / save* the
results without pulling in matplotlib.

Core (coercion + colormaps + overlays + PLY) is numpy-only. File save/load uses
opencv-python if present, else Pillow, else raises a clear error.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "to_float01", "to_uint8", "ensure_gray", "ensure_color", "normalize",
    "apply_cmap", "colorize_depth", "colorize_disparity", "colorize_labels",
    "colorize_height", "colorize_flow", "shaded_relief", "overlay_mask",
    "save", "load", "save_ply", "COLORMAPS",
    # 2026-09-08: 疑似カラーの「種類」を増やした回(ユーザー指摘)
    "colorize_categorical", "colorize_bivariate", "colorize_significance",
    "NORMS", "QUALITATIVE", "PERCEPTUAL_SAFE", "CYCLIC",
]

# A library of false-colour palettes (HDevelop-style pseudo-colour). Sequential
# ones are control-point ramps; a few are analytic. All are approximations of the
# well-known public-domain maps, chosen to read as distinct, legible palettes.
_LUTS = {
    "viridis": [[0.267, 0.005, 0.329], [0.283, 0.141, 0.458], [0.254, 0.265, 0.530],
                [0.207, 0.372, 0.553], [0.164, 0.471, 0.558], [0.128, 0.567, 0.551],
                [0.135, 0.659, 0.518], [0.267, 0.749, 0.441], [0.478, 0.821, 0.318],
                [0.741, 0.873, 0.150], [0.993, 0.906, 0.144]],
    "turbo": [[0.19, 0.07, 0.23], [0.27, 0.31, 0.84], [0.11, 0.56, 0.99],
              [0.07, 0.79, 0.75], [0.30, 0.92, 0.44], [0.71, 0.96, 0.22],
              [0.95, 0.76, 0.16], [0.98, 0.47, 0.12], [0.85, 0.20, 0.05], [0.63, 0.07, 0.02]],
    "magma": [[0.0, 0.0, 0.02], [0.1, 0.06, 0.2], [0.28, 0.06, 0.4], [0.5, 0.12, 0.42],
              [0.72, 0.2, 0.33], [0.9, 0.36, 0.24], [0.98, 0.6, 0.35], [0.99, 0.8, 0.55],
              [0.99, 0.99, 0.75]],
    "plasma": [[0.05, 0.03, 0.53], [0.35, 0.0, 0.65], [0.6, 0.13, 0.6], [0.8, 0.3, 0.47],
               [0.93, 0.47, 0.33], [0.99, 0.65, 0.2], [0.96, 0.83, 0.14], [0.94, 0.98, 0.13]],
    "inferno": [[0.0, 0.0, 0.02], [0.15, 0.04, 0.24], [0.4, 0.07, 0.35], [0.65, 0.17, 0.28],
                [0.87, 0.35, 0.14], [0.98, 0.6, 0.06], [0.99, 0.85, 0.35], [0.99, 1.0, 0.9]],
    "cividis": [[0.0, 0.13, 0.3], [0.0, 0.3, 0.5], [0.3, 0.45, 0.55], [0.55, 0.58, 0.55],
                [0.78, 0.72, 0.45], [1.0, 0.9, 0.2]],
    "terrain": [[0.2, 0.2, 0.6], [0.0, 0.6, 1.0], [0.0, 0.8, 0.4], [0.9, 0.9, 0.5],
                [0.6, 0.45, 0.35], [1.0, 1.0, 1.0]],
    "ocean": [[0.0, 0.0, 0.0], [0.0, 0.15, 0.35], [0.0, 0.4, 0.55], [0.3, 0.7, 0.8],
              [0.75, 0.95, 1.0]],
    "coolwarm": [[0.23, 0.30, 0.75], [0.55, 0.6, 0.85], [0.87, 0.87, 0.87],
                 [0.9, 0.6, 0.5], [0.71, 0.02, 0.15]],       # diverging (blue-white-red)
}
# --------------------------------------------------------------------------- #
# 2026-09-08 に足したパレット —— 「種類が少なくないか」(ユーザー)への答え        #
# --------------------------------------------------------------------------- #
# 数えると 16 あったが、**足りないのは枚数ではなく種類**だった。実測した内訳:
#
#   * **巡回**(位相・向き)は ``hsv`` の 1 枚だけ。しかも明度が 5 回行き来する
#     (同じ尺度で viridis は 0 回)。干渉計・モノジェニック位相・四元数と、
#     この repo は位相を扱う op を多く持つのに、位相用の素直なマップが無い。
#   * **質的**(ラベル・分類)は ``colorize_labels`` の乱数 RGB だけ。隣り合う
#     ラベルが似た色になることがあり、色覚特性への配慮も無い。
#   * **等輝度**(構造の上に色だけ重ねる)が無い。明度が動くマップを重ねると、
#     下の陰影と混ざって「明るい = 値が大きい」なのか「明るい = 山の南斜面」なのか
#     読者に区別できない。
#
# 明度の実測(CIE L*、256 段、折返し = 明度の増減が反転した回数):
#   hsv 5 / jet 3 / terrain 2 / turbo 1 / viridis 0 / cividis 0 / gray 0
_LUTS.update({
    # 巡回(端と端が同じ色。位相・方位・時刻に使う)
    "twilight": [[0.886, 0.850, 0.887], [0.606, 0.720, 0.858], [0.325, 0.545, 0.767],
                 [0.208, 0.373, 0.596], [0.180, 0.212, 0.376], [0.180, 0.110, 0.196],
                 [0.373, 0.129, 0.196], [0.596, 0.208, 0.212], [0.767, 0.373, 0.325],
                 [0.858, 0.606, 0.545], [0.886, 0.850, 0.887]],
    # 干渉縞・位相マップの慣用色(赤→黄→緑→青→紫→赤)。twilight より彩度が高い
    "phase": [[0.850, 0.180, 0.180], [0.910, 0.560, 0.130], [0.800, 0.800, 0.150],
              [0.300, 0.750, 0.300], [0.150, 0.700, 0.700], [0.180, 0.400, 0.850],
              [0.480, 0.220, 0.780], [0.780, 0.220, 0.560], [0.850, 0.180, 0.180]],
    # 等輝度(L* をほぼ一定に保つ。陰影つきの図に色だけ重ねる用)
    "isolum": [[0.60, 0.52, 0.78], [0.44, 0.60, 0.83], [0.34, 0.66, 0.70],
               [0.42, 0.66, 0.47], [0.62, 0.61, 0.36], [0.78, 0.53, 0.44],
               [0.76, 0.49, 0.66]],
})

#: 質的(カテゴリ)パレット。**順序の無い量**に使う —— 連続マップを離散ラベルに
#: 使うと、番号の大小が「近さ」に見えてしまう(ラベル 3 とラベル 4 は隣ではない)。
QUALITATIVE = {
    # 10 色。色覚特性(P/D 型)でも隣り合わないように明度差を付けてある
    "tab10": [[0.121, 0.466, 0.705], [1.000, 0.498, 0.054], [0.172, 0.627, 0.172],
              [0.839, 0.152, 0.156], [0.580, 0.403, 0.741], [0.549, 0.337, 0.294],
              [0.890, 0.466, 0.760], [0.498, 0.498, 0.498], [0.737, 0.741, 0.133],
              [0.090, 0.745, 0.811]],
    # 8 色。Wong (2011) "Points of view: Color blindness", Nature Methods 8, 441.
    # 公開されている色覚安全パレット
    "wong": [[0.000, 0.447, 0.698], [0.902, 0.624, 0.000], [0.000, 0.620, 0.451],
             [0.941, 0.894, 0.259], [0.337, 0.706, 0.914], [0.835, 0.369, 0.000],
             [0.800, 0.475, 0.655], [0.000, 0.000, 0.000]],
}

#: 順序を素直に見せるマップ。「どれを選べばよいか」を道具の側が持つ ——
#: 19 個並べて選ばせるのは案内ではない。
#:
#: ★**判定は 2 つ**(2026-09-08、同日中に直した)。最初は「CIE L* の折返しが 0 回」
#: だけで選んでいたが、``poc_colormap_readability`` が **``cividis`` は折返し 0 回
#: なのに色差の尾根を立てる**ことを実測した。明度が単調でも、色差の刻みが不均一なら
#: なめらかな場に**無い境目**が見える —— 片側の基準で「安全」と名乗っていた。
#:
#: 実測(512 段、隣接色差の max / median と、中央値の 1.6 倍を超える局所最大の数):
#:
#: ==========  ==========  ==============  ==========
#: マップ      L* 折返し   ΔE max/median   尾根の本数
#: ==========  ==========  ==============  ==========
#: ``gray``             0            1.33           0
#: ``viridis``          0            1.38           0
#: ``plasma``           0            1.38           0
#: ``magma``            0            1.48           0
#: ``inferno``          0            1.50           0
#: ``cividis``          0            **2.23**       **1**
#: ``turbo``            1            1.78           1
#: ==========  ==========  ==============  ==========
#:
#: ``cividis`` を外したのは**この repo の近似 LUT が粗いから**で、公開されている
#: cividis そのものの問題ではない(制御点 6 個は逐次マップの中で最少)。
#: 色覚特性への配慮で選びたい向きには :data:`CVD_SAFE` を用意した。
#: ``tests/test_pseudocolour_family.py`` が両方の基準を毎回測る。
PERCEPTUAL_SAFE = ("viridis", "plasma", "magma", "inferno", "gray")

#: 色覚特性(P/D 型)でも順序が読めるとされるマップ。★``cividis`` の近似 LUT は
#: 制御点が 6 個で色差の刻みが粗く、:data:`PERCEPTUAL_SAFE` の基準は満たさない
#: (実測 ΔE max/median 2.23)。制御点を増やせば両方に入れられる ——
#: 一次情報の値を手で写すと誤記の前科があるので、出典を確認できるまで保留。
CVD_SAFE = ("viridis", "cividis")

#: 端と端が同じ色のマップ(位相・方位に使ってよいもの)。
CYCLIC = ("twilight", "phase", "hsv")

COLORMAPS = ("gray", "jet", "viridis", "turbo", "magma", "plasma", "inferno",
             "cividis", "hot", "cool", "hsv", "terrain", "ocean", "coolwarm", "spring", "bone",
             # 2026-09-08 追加
             "twilight", "phase", "isolum")


# ---- input coercion -------------------------------------------------------- #
def to_float01(x):
    """Coerce an image-like to float64 in [0, 1].

    Handles bool (0/1), unsigned ints (divide by the dtype max: uint8 -> /255,
    uint16 -> /65535), signed ints and float (passed through — assumed already
    normalised). PIL images and file paths are read if the optional backend is
    available.

    **Signed integers** map the *full dtype range* affinely onto [0, 1]:
    ``int16 -32768 -> 0.0``, ``0 -> 0.5``, ``32767 -> 1.0`` (before 2026-09-03
    they were divided by the dtype max, which put a signed image in [-1, 1] and
    broke the [0, 1] contract every operator relies on). A signed array that is
    known to hold only non-negative values and should scale like its unsigned
    twin must be cast first (``a.astype(np.uint16)``).
    """
    if isinstance(x, str):
        return load(x)
    if type(x).__module__.startswith("PIL"):
        x = np.asarray(x)
    a = np.asarray(x)
    if a.dtype == bool:
        return a.astype(np.float64)
    if a.dtype.kind == "u":
        return a.astype(np.float64) / float(np.iinfo(a.dtype).max)
    if a.dtype.kind == "i":
        info = np.iinfo(a.dtype)
        lo, hi = float(info.min), float(info.max)
        return (a.astype(np.float64) - lo) / (hi - lo)
    return a.astype(np.float64)


def to_uint8(x):
    """Clip a [0, 1] array to uint8 [0, 255]."""
    return np.clip(np.asarray(x, np.float64) * 255.0, 0, 255).astype(np.uint8)


def normalize(x, vmin=None, vmax=None):
    """Linearly rescale finite values to [0, 1] over [vmin, vmax] (auto if None).
    Non-finite entries are left as-is (callers usually mask them).

    退化ケース(``hi <= lo``、定数配列や 1 要素配列)では ``hi = lo + 1`` に倒すので
    **出力は一様 0** になる。値の大小は失われるが例外は出ない —— 尺度を固定したい
    呼び出し側は ``vmin`` / ``vmax`` を明示すること(:func:`apply_cmap` の注記)。"""
    a = np.asarray(x, np.float64)
    fin = np.isfinite(a)
    if not fin.any():
        return np.zeros_like(a)
    lo = float(a[fin].min()) if vmin is None else float(vmin)
    hi = float(a[fin].max()) if vmax is None else float(vmax)
    if hi <= lo:
        hi = lo + 1.0
    return (a - lo) / (hi - lo)


def ensure_gray(x):
    a = np.asarray(x, np.float64)
    if a.ndim == 3 and a.shape[-1] == 3:
        return a @ np.array([0.299, 0.587, 0.114])
    return a


def ensure_color(x):
    a = np.asarray(x, np.float64)
    if a.ndim == 2:
        return np.repeat(a[:, :, None], 3, axis=2)
    return a


# ---- colormaps (numpy-only) ------------------------------------------------ #
def _lut(t, ctrl):
    ctrl = np.asarray(ctrl, np.float64)
    k = len(ctrl)
    pos = np.clip(t, 0, 1) * (k - 1)
    i0 = np.clip(np.floor(pos).astype(int), 0, k - 1)
    i1 = np.clip(i0 + 1, 0, k - 1)
    f = (pos - i0)[..., None]
    return ctrl[i0] * (1 - f) + ctrl[i1] * f


def _jet(t):
    t = np.clip(t, 0, 1)
    r = np.clip(1.5 - np.abs(4 * t - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * t - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * t - 1), 0, 1)
    return np.stack([r, g, b], axis=-1)


def _hsv(t):
    h = np.clip(t, 0, 1) * 6.0
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    v = np.ones_like(t); p = np.zeros_like(t); q = 1 - f
    cond = [i == 0, i == 1, i == 2, i == 3, i == 4, i == 5]
    r = np.select(cond, [v, q, p, p, f, v])
    g = np.select(cond, [f, v, v, q, p, p])
    b = np.select(cond, [p, p, f, v, v, q])
    return np.stack([r, g, b], axis=-1)


_LUTS["bone"] = [[0.0, 0.0, 0.0], [0.33, 0.33, 0.46], [0.66, 0.78, 0.78], [1.0, 1.0, 1.0]]

_ANALYTIC = {
    "gray": lambda t: np.repeat(t[..., None], 3, axis=-1),
    "jet": _jet,
    "hot": lambda t: np.stack([np.clip(3 * t, 0, 1), np.clip(3 * t - 1, 0, 1),
                               np.clip(3 * t - 2, 0, 1)], axis=-1),
    "cool": lambda t: np.stack([t, 1 - t, np.ones_like(t)], axis=-1),
    "spring": lambda t: np.stack([np.ones_like(t), t, 1 - t], axis=-1),
    "hsv": _hsv,
}


#: 値 → [0,1] の**写し方**。パレットと直交する軸で、実務ではこちらのほうが効く
#: (2026-09-08: それまで線形しか無かった)。``percentile`` / ``rank`` は配列全体を
#: 見るので、複数枚を比べるときは ``vmin`` / ``vmax`` を明示すること。
NORMS = ("linear", "log", "symlog", "sqrt", "power", "percentile", "rank", "symmetric")


def _scale(a, fin, vmin, vmax, norm, gamma, percentile):
    """有限セルを [0,1] へ写す。``norm`` ごとに写し方を変える。"""
    v = a[fin] if fin.any() else np.zeros(1)
    if norm == "percentile":
        lo_p, hi_p = percentile
        lo = float(np.percentile(v, lo_p)) if vmin is None else float(vmin)
        hi = float(np.percentile(v, hi_p)) if vmax is None else float(vmax)
        return np.clip(normalize(a, lo, hi), 0.0, 1.0)
    if norm == "rank":
        # 分位(ヒストグラム平坦化)。外れ値が 1 個あっても中身が潰れない
        out = np.zeros_like(a)
        order = np.argsort(v, kind="stable")
        ranks = np.empty(v.size)
        ranks[order] = np.linspace(0.0, 1.0, v.size) if v.size > 1 else 0.0
        out[fin] = ranks
        return out
    if norm == "symmetric":
        m = float(np.max(np.abs(v))) if vmax is None else float(vmax)
        m = m if m > 0 else 1.0
        return np.clip((a / m) * 0.5 + 0.5, 0.0, 1.0)     # 0 が必ず中央
    lo = float(v.min()) if vmin is None else float(vmin)
    hi = float(v.max()) if vmax is None else float(vmax)
    if norm == "log":
        # 正の量(強度・計数)専用。負や 0 があると対数が定義できないので
        # **黙って持ち上げず**、最小の正の値を下端にする(そう書いてあること)
        pos = v[v > 0]
        lo = float(pos.min()) if (vmin is None and pos.size) else max(lo, 1e-300)
        hi = max(hi, lo * (1.0 + 1e-12))
        t = (np.log10(np.maximum(a, lo)) - np.log10(lo)) / (np.log10(hi) - np.log10(lo))
        return np.clip(t, 0.0, 1.0)
    if norm == "symlog":
        m = float(np.max(np.abs(v))) if vmax is None else float(vmax)
        m = m if m > 0 else 1.0
        s = np.sign(a) * np.log10(1.0 + np.abs(a) / (m * 1e-3)) / np.log10(1.0 + 1e3)
        return np.clip(s * 0.5 + 0.5, 0.0, 1.0)
    t = normalize(a, lo, hi)
    if norm == "sqrt":
        return np.sqrt(np.clip(t, 0.0, 1.0))
    if norm == "power":
        return np.clip(t, 0.0, 1.0) ** float(gamma)
    return t                                              # linear(clip は呼び手側)


def apply_cmap(x, name: str = "viridis", vmin=None, vmax=None, invalid=(0, 0, 0),
               norm: str = "linear", gamma: float = 2.2, percentile=(2.0, 98.0),
               levels: int | None = None, under=None, over=None):
    """Map a scalar field to an (H, W, 3) RGB image in [0, 1] using a false-colour
    palette (see ``COLORMAPS``).

    Values are normalised over [vmin, vmax] (auto from finite data if None).
    Non-finite cells (e.g. ``inf`` in a depth map) are painted *invalid*.

    ★★ 正規化は「渡した配列の中だけ」で行う(2026-09-02 に明文化)★★
        ``vmin`` / ``vmax`` を省くと **その呼び出しで渡された配列の min/max** が
        両端になる。したがって

        * **1 点ずつ呼ぶと必ず同じ色になる**。要素が 1 つなら min==max なので
          ``normalize`` が ``hi = lo + 1`` に倒し、``t = 0`` = カラーマップの下端に
          なる(実測: ``apply_cmap([[0.0]])`` / ``[[0.3]]`` / ``[[0.9]]`` はどれも
          viridis の (0.267, 0.005, 0.329))。**警告も例外も出ない**ので、
          値が色に効いていないことに気づけない。
        * 同じ理由で、**複数の画像を別々に呼ぶと色スケールが揃わない**
          (各画像が自分の min/max で伸ばされる)。

        値と色の対応を固定したい / 複数枚を比較したいときは **必ず ``vmin`` と
        ``vmax`` を明示**すること::

            rgb = apply_cmap(depth, "viridis", vmin=0.0, vmax=5.0)   # 常に同じ尺度

        1 点だけ色にしたい場合も同じ(``apply_cmap([[v]], vmin=lo, vmax=hi)``)。

    ★**写し方(``norm``)はパレットと直交する軸**で、実務ではこちらのほうが効く
    (2026-09-08 に追加。それまで線形しか無かった):

    ==============  =======================================================
    ``norm``        いつ使うか
    ==============  =======================================================
    ``linear``      既定。物理量をそのまま比べる
    ``log``         強度・計数など**正の量で桁が広い**もの。負や 0 は
                    下端へ寄せる(黙って持ち上げない)
    ``symlog``      符号があって桁も広い(残差・流れの発散)
    ``sqrt``        暗部を持ち上げる。``power`` は ``gamma`` で任意
    ``percentile``  外れ値 1 個で全体が潰れるのを防ぐ(既定 2–98 %)
    ``rank``        分位。**分布の形を捨てて順序だけ見せる**ので、
                    「どこが高いか」は分かるが「どれだけ高いか」は分からない
    ``symmetric``   0 を必ず中央に置く(発散マップと組で使う)
    ==============  =======================================================

    ``levels`` を与えると **n 段に量子化**する(計測の等高線・干渉縞のように
    段を数えたいとき。連続で塗ると 1 段の差が読めない)。

    ★``under`` / ``over`` を与えると、``[vmin, vmax]`` の**外側を別の色**にする。
    既定(``None``)は今までどおり端の色へ丸める —— つまり**範囲外と正当な最小値が
    同じ色になる**。実測(2026-09-08): ``vmin`` 省略でも ``-5`` は viridis の下端
    ``(0.267, 0.005, 0.329)`` になり、区別する手段が無かった。図で「振り切れた」と
    「ちょうど下端」を見分けたいときは必ず指定すること。

    Args:
        norm: 上の表。``NORMS`` のいずれか。
        gamma: ``norm="power"`` の指数(既定 2.2)。
        percentile: ``norm="percentile"`` の下端・上端 [%](既定 (2, 98))。
        levels: 段数(``None`` で連続)。
        under, over: 範囲外の色 ``(r, g, b)``。``None`` で丸める(従来どおり)。
    Raises:
        ValueError: 未知の ``name`` / ``norm``、``levels < 2``。
    """
    a = np.asarray(x, np.float64)
    fin = np.isfinite(a)
    if norm not in NORMS:
        raise ValueError("unknown norm %r (have %s)" % (norm, NORMS))
    safe = np.where(fin, a, 0.0)
    t = _scale(safe, fin, vmin, vmax, norm, gamma, percentile)
    if levels is not None:
        n = int(levels)
        if n < 2:
            raise ValueError("levels must be >= 2 (got %r) — one band is not a map" % (levels,))
        t = np.clip(np.floor(np.clip(t, 0, 1) * n), 0, n - 1) / (n - 1)
    if name in _ANALYTIC:
        rgb = _ANALYTIC[name](t)
    elif name in _LUTS:
        rgb = _lut(t, _LUTS[name])
    else:
        raise ValueError("unknown colormap %r (have %s)" % (name, COLORMAPS))
    rgb = np.clip(rgb, 0, 1).copy()
    if under is not None or over is not None:
        v = a[fin] if fin.any() else np.zeros(1)
        lo = float(v.min()) if vmin is None else float(vmin)
        hi = float(v.max()) if vmax is None else float(vmax)
        if under is not None:
            rgb[fin & (a < lo)] = np.asarray(under, np.float64)
        if over is not None:
            rgb[fin & (a > hi)] = np.asarray(over, np.float64)
    rgb[~fin] = np.asarray(invalid, np.float64)
    return rgb


def colorize_depth(depth, name="viridis", **kw):
    """Colourise a depth map; ``inf``/unknown -> black.

    ★2026-09-08: ``vmin`` / ``vmax`` / ``norm`` / ``levels`` / ``under`` / ``over``
    をそのまま :func:`apply_cmap` へ渡すようにした。それまでこの薄い包みは
    **``name`` しか受けず**、下の層に在る値域指定と番兵色を落としていた
    (族の中で契約が片側だけ、という形。KNOWN_ISSUES §42)。
    """
    return apply_cmap(depth, name=name, **kw)


def colorize_disparity(disp, name="turbo", **kw):
    """視差マップを塗る。

    ★**既定を ``jet`` から ``turbo`` に変えた**(2026-09-08)。虹色という見た目は
    現場の慣習として残しつつ、``jet`` は明度が行ったり来たりするので**無い境目を
    作る**。CIE L* を 256 段で測った折返しの回数(増減が反転した回数):

    ====================  ==========  ==================
    マップ                折返し      刻みの変動係数
    ====================  ==========  ==================
    ``hsv``                        5                0.97
    ``jet``(旧既定)              3                0.60
    ``turbo``(新既定)            1                0.42
    ``viridis``                    0                0.08
    ====================  ==========  ==================

    順序をいちばん正直に見せたいなら ``viridis``(``PERCEPTUAL_SAFE`` の一覧)。
    ``name="jet"`` と明示すれば従来の色に戻せる。
    """
    return apply_cmap(disp, name=name, **kw)


def colorize_categorical(labels, palette="tab10", background=(0.0, 0.0, 0.0), cycle=False):
    """ラベル(**順序の無い量**)を質的パレットで塗る。→ ``(H, W, 3)``。

    :func:`colorize_labels` は乱数 RGB を割り当てるので、隣り合うラベルが似た色に
    なることがあり、色覚特性への配慮も無い。こちらは公開されている質的パレットを
    順に割り当てる(``QUALITATIVE`` = ``tab10`` / ``wong``)。

    ★連続マップ(viridis 等)をラベルに使ってはいけない —— 番号の大小が「近さ」に
    見え、ラベル 3 とラベル 4 が隣の領域だと**読者が誤解する**。

    Args:
        labels: 整数ラベル(0 = 背景)。
        palette: ``QUALITATIVE`` のキー。色数を超えたラベルは循環する
            (循環したことは戻り値からは分からないので、色数を超える数の
            ラベルには :func:`colorize_labels` を使うほうが誠実)。
        background: ラベル 0 の色。
    Raises:
        ValueError: 未知の ``palette``。
    """
    if palette not in QUALITATIVE:
        raise ValueError("unknown qualitative palette %r (have %s)"
                         % (palette, tuple(QUALITATIVE)))
    lab = np.asarray(labels)
    pal = np.asarray(QUALITATIVE[palette], np.float64)
    out = np.zeros(lab.shape + (3,), np.float64)
    out[...] = np.asarray(background, np.float64)
    pos = lab > 0
    if pos.any():
        idx = (lab[pos].astype(np.int64) - 1) % len(pal)
        out[pos] = pal[idx]
    return out


def colorize_bivariate(value, weight, name="viridis", vmin=None, vmax=None,
                       wmin=None, wmax=None, floor=0.15, norm="linear"):
    """**2 つの量を 1 枚に**塗る: 色 = ``value``、明るさ = ``weight``。

    「どこがどれだけか」と「その値をどれだけ信じてよいか」は別の量なのに、
    図では 1 枚に畳まれがちで、**疎な領域の外れ値が濃い色で目立つ**という
    決まった嘘が出る。重み(点数・信頼度・SN 比)で明度を落とすと、
    薄いところは薄く見える。

    実例: 沈下量(``value``)× 有意性の余裕(``weight`` = |d| / LoD)。
    光学なら位相 × 変調度、写真なら深度 × マッチングコスト。

    Args:
        value: 色にする量。
        weight: 明るさにする量(同形)。``[wmin, wmax]`` で [0,1] に写す。
        floor: 重み 0 のときの明るさ(0 だと真っ黒になり、形が読めない)。
    Returns:
        ``(H, W, 3)`` float [0,1]。
    Raises:
        ValueError: 形が違う。
    """
    v = np.asarray(value, np.float64)
    w = np.asarray(weight, np.float64)
    if v.shape != w.shape:
        raise ValueError("colorize_bivariate: value %r and weight %r must have the "
                         "same shape" % (v.shape, w.shape))
    rgb = apply_cmap(v, name=name, vmin=vmin, vmax=vmax, norm=norm)
    fw = np.isfinite(w)
    k = normalize(np.where(fw, w, 0.0), wmin, wmax)
    k = np.clip(k, 0.0, 1.0) * (1.0 - float(floor)) + float(floor)
    k = np.where(fw, k, float(floor))
    return np.clip(rgb * k[..., None], 0.0, 1.0)


def colorize_significance(value, significant, name="coolwarm", vmin=None, vmax=None,
                          norm="symmetric", dim=0.25):
    """有意でないところを**灰色に落として**塗る。→ ``(H, W, 3)``。

    「平均は -2.43 mm 沈んだ」と「有意に沈んだのは 49.9 % で、その平均は
    -4.34 mm」は別の話で、1 枚の色地図に全部を濃く塗ると前者しか読めない
    (``poc_settlement_significance`` の実測)。判定を通らなかったセルは彩度を
    落とし、**在るけれど言い切れない**ことを図の上で表す。

    Args:
        significant: bool 配列(同形)。True のセルだけ元の色で塗る。
        dim: 有意でないセルに残す彩度(0 = 完全な灰、1 = そのまま)。
    Raises:
        ValueError: 形が違う。
    """
    v = np.asarray(value, np.float64)
    s = np.asarray(significant, bool)
    if v.shape != s.shape:
        raise ValueError("colorize_significance: value %r and significant %r must "
                         "have the same shape" % (v.shape, s.shape))
    rgb = apply_cmap(v, name=name, vmin=vmin, vmax=vmax, norm=norm)
    gray = rgb @ np.array([0.299, 0.587, 0.114])
    d = float(dim)
    mixed = gray[..., None] * (1.0 - d) + rgb * d
    return np.where(s[..., None], rgb, mixed)


def shaded_relief(heightmap, azimuth: float = 315.0, altitude: float = 45.0, z: float = 1.0):
    """Hillshade of a height map -> gray [0,1] shaded surface (a pseudo-3-D view of
    a height/depth image). *azimuth*/*altitude* are the light direction in degrees."""
    h = np.asarray(heightmap, np.float64)
    if not np.isfinite(h).all():
        fill = float(np.nanmin(h[np.isfinite(h)])) if np.isfinite(h).any() else 0.0
        h = np.where(np.isfinite(h), h, fill)
    gy, gx = np.gradient(h * float(z))
    slope = np.pi / 2 - np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az = np.deg2rad(360.0 - azimuth + 90.0)
    alt = np.deg2rad(altitude)
    shade = (np.sin(alt) * np.sin(slope)
             + np.cos(alt) * np.cos(slope) * np.cos(az - aspect))
    return np.clip(shade, 0, 1)


def colorize_height(heightmap, name="terrain", relief=True, azimuth=315.0, altitude=45.0):
    """False-colour a height map and (optionally) modulate it by hillshade so the
    surface reads as 2.5-D. Returns an (H, W, 3) RGB image."""
    rgb = apply_cmap(heightmap, name=name)
    if relief:
        sh = shaded_relief(heightmap, azimuth, altitude)[..., None]
        rgb = np.clip(rgb * (0.4 + 0.6 * sh), 0, 1)
    return rgb


def colorize_flow(u, v, max_mag=None):
    """Middlebury-style colour wheel for an optical-flow field: hue = motion
    direction, brightness = speed. Zero motion -> black. Returns (H, W, 3) in
    [0, 1]. *max_mag* fixes the speed that saturates to full brightness (auto =
    the field's max), so several frames can share one scale."""
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    ang = (np.arctan2(v, u) / (2.0 * np.pi)) % 1.0     # direction -> hue in [0,1)
    mag = np.hypot(u, v)
    m = float(max_mag) if max_mag else (float(mag.max()) if mag.size and mag.max() > 0 else 1.0)
    val = np.clip(mag / m, 0.0, 1.0)                   # speed -> brightness
    rgb = _hsv(ang) * val[..., None]
    return np.clip(rgb, 0.0, 1.0)


def colorize_labels(labels, seed: int = 0):
    """Distinct random colour per positive label; label 0 (background) -> black."""
    lab = np.asarray(labels).astype(int)
    n = int(lab.max())
    rng = np.random.default_rng(seed)
    cols = rng.random((n + 1, 3))
    cols[0] = 0.0
    return cols[np.clip(lab, 0, n)]


def overlay_mask(image, mask, color=(1.0, 0.0, 0.0), alpha: float = 0.5,
                 mode: str = "fill", line_width: int = 1):
    """Blend *color* onto *image* on the region *mask* (mask > 0.5).

    ``mode='fill'`` (default) paints the whole region; ``mode='margin'`` paints only
    its boundary, ``line_width`` px thick — HDevelop ``dev_set_draw('margin')``."""
    img = ensure_color(image).copy()
    m = np.asarray(mask) > 0.5
    if mode == "margin" and m.any():
        from scipy import ndimage
        er = ndimage.binary_erosion(m, iterations=max(1, int(line_width)))
        m = m & ~er                               # a boundary band of the requested width
    col = np.asarray(color, np.float64)
    img[m] = (1 - alpha) * img[m] + alpha * col
    return np.clip(img, 0, 1)


# ---- file save / load ------------------------------------------------------ #
def _cv2():
    try:
        import cv2
        return cv2
    except Exception:
        return None


def save(path: str, arr) -> None:
    """Save an image/region/color array (or a colourised scalar field) to *path*.

    The input **dtype is honoured first**: bool -> 0/1 and unsigned integers are
    scaled by their dtype max (uint8 -> /255, uint16 -> /65535, via
    :func:`to_float01`), so a uint8 grey image saves as that grey image and a
    uint8 RGB image saves as that RGB image — they are *not* colourised or
    saturated to white (a 2026-09-03 fix; before, every array was taken as raw
    float values). Signed-integer and float arrays are taken as raw values.

    Then: a 2-D array already in [0, 1] saves as grayscale; a 2-D array with
    values outside [0, 1] (a depth map, an int label map, NaN/inf) is colourised
    (viridis) first; ``(H, W, 3)`` saves as RGB, ``(H, W, 4)`` as RGBA with the
    alpha channel kept (R/G/B/A land in the file's R/G/B/A — the cv2 path used to
    reverse *all four* channels and write R into alpha), ``(H, W, 1)`` as
    grayscale. Any other channel count raises ``ValueError``.

    Non-ASCII paths (a Japanese file name on Windows) work: the image is encoded
    in memory (``cv2.imencode``) and the bytes are written by numpy, so the
    ``cv2.imwrite`` code-page limitation never applies. Unwritable paths and
    unknown extensions both raise ``OSError``.
    """
    import os
    a0 = np.asarray(arr)
    if a0.dtype == bool or a0.dtype.kind == "u":
        a = to_float01(a0)                      # dtype-aware: uint8 stays grey/RGB
    else:
        a = np.asarray(a0, np.float64)          # signed ints / floats = raw values
    if a.ndim == 3 and a.shape[-1] == 1:
        a = a[:, :, 0]
    if a.ndim == 2 and (a.min() < -1e-9 or a.max() > 1 + 1e-9 or not np.isfinite(a).all()):
        a = apply_cmap(a)
    if a.ndim not in (2, 3) or (a.ndim == 3 and a.shape[-1] not in (3, 4)):
        raise ValueError("save expects (H, W), (H, W, 1), (H, W, 3) or (H, W, 4), got "
                         "shape %r" % (a.shape,))
    u8 = to_uint8(a)
    cv2 = _cv2()
    if cv2 is not None:
        if u8.ndim == 3:
            # RGB -> BGR, RGBA -> BGRA: the alpha channel stays in place.
            order = [2, 1, 0, 3] if u8.shape[-1] == 4 else [2, 1, 0]
            bgr = np.ascontiguousarray(u8[:, :, order])
        else:
            bgr = np.ascontiguousarray(u8)
        ext = os.path.splitext(path)[1]
        # cv2.imencode RAISES cv2.error on an unknown extension (or returns False);
        # tofile raises OSError on an unwritable path. Normalise ALL of them to a
        # clean OSError so a caller's try/except sees one exception type.
        try:
            ok, buf = cv2.imencode(ext, bgr)
        except cv2.error as e:
            raise OSError("could not write image to %r (unknown extension %r?): %s"
                          % (path, ext, e))
        if not ok:
            raise OSError("could not encode image for %r (unknown extension %r?)"
                          % (path, ext))
        try:
            np.asarray(buf, np.uint8).ravel().tofile(path)
        except OSError as e:
            raise OSError("could not write image to %r (unwritable path?): %s" % (path, e))
        return
    try:
        from PIL import Image
        Image.fromarray(u8).save(path)
    except Exception as e:  # pragma: no cover
        raise RuntimeError("save needs opencv-python or Pillow: %s" % e)


_JPEG_MAGIC = b"\xff\xd8\xff"


def _check_jpeg_complete(path: str) -> None:
    """Fail closed on a truncated JPEG — run BEFORE any backend decodes it.

    libjpeg-based readers *pad* a truncated JPEG with grey and return a partial
    image without any error (``cv2.imread`` does; ``cv2.imdecode`` returns None
    and the ``raster`` fallback then decodes the partial file), so a
    half-downloaded photo silently loads as "top half picture, bottom half
    grey". Pillow's decoder refuses instead (``OSError: image file is
    truncated``), so when Pillow is available the file is decoded once by Pillow
    in 1/8-scale ``draft`` mode (the entropy data must still be consumed in
    full, so truncation is detected, at a fraction of a full decode). Without
    Pillow the EOI marker ``FF D9`` is required to appear in the last 4 KiB of
    the file (weaker: a file truncated right after an embedded EXIF thumbnail,
    which carries its own EOI, would pass). Non-JPEG files (by magic bytes) and
    unreadable paths return silently — the decoders report those.
    Raises ``ValueError`` — the contract :func:`load` promises for a file no
    backend can decode *correctly*.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(3)
            if not head.startswith(_JPEG_MAGIC):
                return
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 4096))
            tail = fh.read()
    except OSError:
        return
    try:
        from PIL import Image
    except Exception:  # pragma: no cover - Pillow absent
        if b"\xff\xd9" not in tail:
            raise ValueError("cannot decode image: %s (truncated JPEG: no EOI marker "
                             "in the file tail)" % path)
        return
    try:
        with Image.open(path) as im:
            im.draft(None, (max(1, im.width // 8), max(1, im.height // 8)))
            im.load()
    except OSError as e:
        raise ValueError("cannot decode image: %s (truncated or corrupt JPEG: %s)"
                         % (path, e))


def _as_gray_or_color(f, color: bool):
    """Coerce an already-normalised [0, 1] float array to the load() shape:
    grayscale (H, W) by default, RGB (H, W, 3) when *color*."""
    a = np.asarray(f, np.float64)
    if color:
        if a.ndim == 2:
            return np.repeat(a[:, :, None], 3, axis=2)
        if a.shape[-1] >= 3:
            return a[..., :3]
        return np.repeat(a[..., :1], 3, axis=2)
    if a.ndim == 2:
        return a
    if a.shape[-1] >= 3:
        return a[..., :3] @ np.array([0.299, 0.587, 0.114])
    return a[..., 0]


def _to01_by_depth(im):
    """Normalise a decoded raster to float64 [0, 1] by its *true* max level
    (uint8 -> /255, uint16 -> /65535), so a 16-bit read keeps its 65536 levels.
    Float samples are assumed already normalised and merely clipped — the same
    rule :func:`raster.to01` applies, so both read paths agree."""
    a = np.asarray(im)
    if a.dtype.kind in "ui":
        return a.astype(np.float64) / float(np.iinfo(a.dtype).max)
    return np.clip(a.astype(np.float64), 0.0, 1.0)


def _load_via_fallback(path: str, color: bool):
    """Decode a file OpenCV could *see* but not decode (a 16-bit / float TIFF, a
    PFM, ...) via the bit-depth-preserving `raster` reader, then Pillow. Returns
    float64 [0, 1]. Raises a clear ValueError if no backend can decode it."""
    f = None
    try:
        import raster
        arr, meta = raster.read_raster(path, keep_dtype=True)
        f = raster.to01(arr, meta)
    except FileNotFoundError:
        raise
    except Exception:
        f = None
    if f is None:
        try:
            from PIL import Image, ImageOps
            im = ImageOps.exif_transpose(Image.open(path))   # honour EXIF orientation
            im = im.convert("RGB") if color else im.convert("L")
            return np.asarray(im, np.float64) / 255.0
        except FileNotFoundError:
            raise
        except Exception:
            f = None
    if f is None:
        raise ValueError("cannot decode image: %s (no backend among opencv / raster / "
                         "Pillow could read it)" % path)
    return _as_gray_or_color(f, color)


def load(path: str, color: bool = False):
    """Load *path* as float64 [0, 1] (grayscale by default).

    8-bit PNG/JPG go through OpenCV (or Pillow) divided by 255 — the contract the
    whole operator suite depends on, unchanged. A 16-bit raster OpenCV *can*
    decode keeps its depth (``IMREAD_ANYDEPTH``) and is divided by its own max
    level (65535), not crushed to 8 bits first. When OpenCV cannot decode a file
    it can nevertheless *see* (a float TIFF, a PFM, ...), the read falls back to
    the bit-depth-preserving :mod:`raster` reader (then Pillow) instead of
    reporting the failure as a missing file. A file that genuinely does not exist
    raises ``FileNotFoundError``; a file that exists but no backend can decode
    raises a clear ``ValueError`` — and so does a **truncated JPEG** (libjpeg
    would otherwise hand back a partial image padded with grey, silently; see
    :func:`_check_jpeg_complete`).

    The bytes are read by numpy and decoded with ``cv2.imdecode`` (not
    ``cv2.imread``), so non-ASCII paths work on Windows too. EXIF orientation is
    honoured on every path (``imdecode`` applies it like ``imread``; the Pillow
    branches use ``ImageOps.exif_transpose``).
    """
    import os
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    _check_jpeg_complete(path)                  # before ANY backend touches it
    cv2 = _cv2()
    if cv2 is not None:
        # ANYDEPTH keeps 16-bit / float samples native; the channel coercion
        # (gray vs 3-channel) is untouched, so 8-bit files decode as before.
        flag = (cv2.IMREAD_COLOR if color else cv2.IMREAD_GRAYSCALE) | cv2.IMREAD_ANYDEPTH
        try:
            buf = np.fromfile(path, dtype=np.uint8)
        except OSError:                         # a directory, a locked file, ...
            buf = np.zeros(0, np.uint8)
        im = cv2.imdecode(buf, flag) if buf.size else None
        if im is not None:
            if color:
                im = im[:, :, ::-1]
            return _to01_by_depth(im)
        return _load_via_fallback(path, color)  # present -> undecodable by cv2
    try:
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(path))   # honour EXIF orientation
        im = im.convert("RGB") if color else im.convert("L")
        return np.asarray(im, np.float64) / 255.0
    except Exception as e:  # pragma: no cover
        raise ValueError("cannot decode image: %s (%s)" % (path, e))


def save_ply(path: str, points, colors=None) -> None:
    """Write an ASCII PLY point cloud. *points* (N,3); *colors* optional (N,3) in [0,1]."""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    n = len(P)
    lines = ["ply", "format ascii 1.0", "element vertex %d" % n,
             "property float x", "property float y", "property float z"]
    C = None
    if colors is not None:
        C = np.clip(np.asarray(colors, np.float64) * 255, 0, 255).astype(int)
        lines += ["property uchar red", "property uchar green", "property uchar blue"]
    lines.append("end_header")
    body = []
    for i in range(n):
        if C is not None:
            body.append("%g %g %g %d %d %d" % (P[i, 0], P[i, 1], P[i, 2],
                                               C[i, 0], C[i, 1], C[i, 2]))
        else:
            body.append("%g %g %g" % (P[i, 0], P[i, 1], P[i, 2]))
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(lines + body) + "\n")
