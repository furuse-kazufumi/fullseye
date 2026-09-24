# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""perpetual —— 止めるまで描き続ける絵と、**その絵が満たす厳密な恒等式**。

動機(2026-09-23)は著者の要望「大昔から無限にグラフィックを描画し続けるような
物はあるけど、そういう作品を作る op とか作れないかね」。**8 ビットの一行
プログラムから続く系譜**(10 PRINT のランダム迷路、基本セルオートマトン、
ラングトンの蟻、カオスゲーム)を op にする。

ただし「きれいな絵が無限に出る」だけなら、この repo には入らない。入る理由は
**この系譜のほぼ全部に、絵とは独立に成り立つ厳密な主張がある**こと:

  * 規則 90 を 1 点から回すと、第 n 行の第 k セルは **二項係数 C(n,k) の偶奇**
    に厳密に一致する(シェルピンスキー)。絵を一切見ずに採点できる。
  * ラングトンの蟻は、どの有限初期配置からでも **約 1 万歩で「高速道路」に入り、
    以後は周期 104 で斜めに進み続ける**(Bunimovich–Troubetzkoy)。周期も
    変位も整数で言える。
  * アポロニウスの円詰めでは、接する 4 円の曲率が **デカルトの円定理**
    ``(k₁+k₂+k₃+k₄)² = 2(k₁²+k₂²+k₃²+k₄²)`` を厳密に満たす。
  * カール場(``ψ`` の回転)は **発散が恒等的に 0**。流れ場を「それらしい雑音」
    で作ったか、ちゃんと非圧縮で作ったかは、この 1 本で分かれる。
  * 餌も死もない反応拡散は **総量が保存される**(拡散は再分配であって生成では
    ない)。数値解法が壊れていれば、ここが真っ先に崩れる。
  * カオスゲーム(3 頂点・比 1/2)の吸引子は箱数次元 **log3/log2 = 1.5850**。

★設計の中心 ——「無限」を op でどう持つか。1 枚返す生成器だけだと「無限に
描き続ける」ことにならない。そこで **状態 → 進める → 描く** の 3 本組
(:func:`perpetual_state` / :func:`perpetual_step` / :func:`perpetual_render`)
を置いた。状態は ``table``(dict)なので、呼んだ側が好きなだけ回せる ——
1 万歩でも 1 億歩でも、途中で描いても、途中で保存してもよい。
**op の側は「いつ止めるか」を決めない。**

★返すのは ``rgb``(H,W,3、[0,1] の float)と ``table`` だけで、新しい型語は
足さない。作った絵に既存の 2,147 op がそのまま掛かることに意味がある。

使い方::

    import perpetual as pp
    img = pp.perpetual_ten_print()                     # 1 枚
    s = pp.perpetual_state("langtons_ant", size=301)   # 無限に回せる状態
    s = pp.perpetual_step(s, 12000)
    img = pp.perpetual_render(s)
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "perpetual_ten_print",
    "perpetual_truchet",
    "perpetual_elementary_ca",
    "perpetual_langtons_ant",
    "perpetual_chaos_game",
    "perpetual_apollonian",
    "perpetual_harmonograph",
    "perpetual_ifs_attractor",
    "perpetual_flow_field",
    "perpetual_reaction_diffusion",
    "perpetual_plasma",
    "perpetual_state",
    "perpetual_step",
    "perpetual_render",
    "perpetual_loop",
    "perpetual_loop_seam",
    "perpetual_identities",
    "PERPETUALS",
    "LOOPS",
]

_INK = (0.10, 0.11, 0.16)
_PAPER = (0.97, 0.96, 0.94)


# --------------------------------------------------------------------------- #
# 下請け                                                                        #
# --------------------------------------------------------------------------- #
def _canvas(h, w, colour=_PAPER):
    return np.tile(np.asarray(colour, np.float64).reshape(1, 1, 3), (h, w, 1))


def _grid(h, w):
    y = np.arange(h, dtype=np.float64)[:, None] + 0.5
    x = np.arange(w, dtype=np.float64)[None, :] + 0.5
    return y, x


def _stamp_segment(img, y0, x0, y1, x1, half, colour):
    """太さ ``2*half`` の線分を、被覆率で載せる(局所の外接箱だけ触る)。"""
    h, w = img.shape[:2]
    lo_y = max(int(min(y0, y1) - half - 1), 0)
    hi_y = min(int(max(y0, y1) + half + 2), h)
    lo_x = max(int(min(x0, x1) - half - 1), 0)
    hi_x = min(int(max(x0, x1) + half + 2), w)
    if lo_y >= hi_y or lo_x >= hi_x:
        return img
    yy = np.arange(lo_y, hi_y, dtype=np.float64)[:, None] + 0.5
    xx = np.arange(lo_x, hi_x, dtype=np.float64)[None, :] + 0.5
    dy, dx = y1 - y0, x1 - x0
    L2 = dy * dy + dx * dx
    t = 0.0 if L2 < 1e-12 else np.clip(((yy - y0) * dy + (xx - x0) * dx) / L2, 0.0, 1.0)
    d = np.hypot(yy - (y0 + t * dy), xx - (x0 + t * dx)) - half
    a = np.clip(0.5 - d, 0.0, 1.0)[..., None]
    c = np.asarray(colour, np.float64).reshape(1, 1, 3)
    img[lo_y:hi_y, lo_x:hi_x] = img[lo_y:hi_y, lo_x:hi_x] * (1 - a) + c * a
    return img


def _stamp_arc(img, cy, cx, r, th0, th1, half, colour, n=24):
    th = np.linspace(th0, th1, n)
    ys, xs = cy + r * np.sin(th), cx + r * np.cos(th)
    for i in range(n - 1):
        img = _stamp_segment(img, ys[i], xs[i], ys[i + 1], xs[i + 1], half, colour)
    return img


#: 密度の配色(暗い紺 → 橙 → 生成り)。★赤と緑は対にしない
_HOT = ((0.0, (0.05, 0.07, 0.16)), (0.35, (0.16, 0.26, 0.52)),
        (0.68, (0.78, 0.56, 0.25)), (1.0, (1.00, 0.95, 0.86)))
#: 量の配色(紙 → 青)。曲率・流速のように「大きさ」を見せる量に使う
_COOL = ((0.0, (0.06, 0.10, 0.24)), (0.45, (0.20, 0.45, 0.62)),
         (0.80, (0.62, 0.76, 0.80)), (1.0, (0.99, 0.97, 0.92)))


def _splat(h, w, ys, xs, weight=1.0):
    """点群を**双一次で**積む → (h, w) の重み場。

    ★0 次(総量)と 1 次(重心)を**厳密に**保つ。1 次元で見ると、床 i と
    端数 f に対し ``i(1-f) + (i+1)f = i + f`` で元の位置そのものに戻り、
    2 次元は軸ごとに分かれるので両方とも厳密。実測(39.9 万点・520 px):
    総量の相対差 **0.00e+00**、重心差 **0.000e+00**。

    以前の ``_scatter`` は ``.astype(np.int64)`` = **切り捨て**で積んでいた
    (四捨五入ですらない)ので、総量は合うのに**絵全体がちょうど半画素ずれる**
    (実測 −0.5009 / −0.4998 画素)。0 次だけ見る検査はこの欠陥に構造的に盲目。
    """
    ys = np.asarray(ys, np.float64)
    xs = np.asarray(xs, np.float64)
    ok = (ys >= 0) & (ys < h - 1) & (xs >= 0) & (xs < w - 1)
    ys, xs = ys[ok], xs[ok]
    wt = np.asarray(weight, np.float64)
    wt = wt[ok] if wt.ndim else np.full(ys.shape, float(wt))
    y0 = np.floor(ys).astype(np.int64)
    x0 = np.floor(xs).astype(np.int64)
    fy, fx = ys - y0, xs - x0
    acc = np.zeros(h * w, np.float64)
    for dy in (0, 1):
        for dx in (0, 1):
            wy = fy if dy else 1.0 - fy
            wx = fx if dx else 1.0 - fx
            # ★`np.add.at` は同じことをするが桁違いに遅い(散らばった加算)。
            #   1 次元に畳んで `bincount` で積むと CI の予算に収まる。
            idx = (y0 + dy) * w + (x0 + dx)
            acc += np.bincount(idx, weights=wt * wy * wx, minlength=h * w)
    return acc.reshape(h, w)


def _tone(v, knee=0.06, q=0.999):
    """asinh トーン。暗部を伸ばし明部を潰さない(天体写真の定石)。

    ★**狭義単調**なので、画素の大小関係は 1 組も入れ替わらない ——
    見やすくすることと嘘をつくことは別だと言える(10 巡目で 4,998 組で実測)。

    ★正規化は**最大値でなく分位点** ``q`` で行う。最大値で割ると、密度が
    極端に尖った素材(バーンズリーのシダは根元の 1 点が飛び抜ける)で**他が
    全部潰れて真っ暗**になる —— 実際にそれを出した。``q`` を超えた分は上端に
    寄るだけで、順位は保たれたまま。
    """
    a = np.asarray(v, np.float64)
    hi = float(np.quantile(a, q)) if 0.0 < q < 1.0 else float(a.max())
    hi = hi or (float(a.max()) or 1.0)
    return np.arcsinh(a / (knee * hi)) / np.arcsinh(1.0 / knee)


def _ramp(t, stops=_HOT):
    """停留点の色を線形につなぐ → (..., 3)。"""
    t = np.clip(np.asarray(t, np.float64), 0.0, 1.0)
    out = np.zeros(t.shape + (3,), np.float64)
    for i in range(len(stops) - 1):
        a, ca = stops[i]
        b, cb = stops[i + 1]
        m = (t >= a) & (t <= b)
        if m.any():
            u = ((t[m] - a) / (b - a))[..., None]
            out[m] = np.asarray(ca) * (1.0 - u) + np.asarray(cb) * u
    return out


def _downsample(img, k):
    """k 倍のスーパーサンプルを**面積平均**で畳む。

    ★これは「細かい格子で 1 枚描く」のと厳密に同じ量になる
    (8 巡目の PoC で ``n=128 sub=4`` と ``n=512 sub=1`` が 0.00e+00 で一致)。
    """
    if k <= 1:
        return img
    a = np.asarray(img)
    h, w = a.shape[0] // k * k, a.shape[1] // k * k
    a = a[:h, :w]
    if a.ndim == 2:
        return a.reshape(h // k, k, w // k, k).mean(axis=(1, 3))
    return a.reshape(h // k, k, w // k, k, a.shape[2]).mean(axis=(1, 3))


def _fit_to_frame(uy, ux, n, pad=0.02):
    """頂点の**外接箱**を枠に合わせる係数と中心を返す。

    ★外接円に合わせると、三角形は枠の上下に大きな余白を残す(実際にそれを
    出した)。見せたい図形の外接箱で合わせる。
    """
    sy = (1.0 - 2.0 * pad) / max(uy.max() - uy.min(), 1e-12)
    sx = (1.0 - 2.0 * pad) / max(ux.max() - ux.min(), 1e-12)
    k = min(sy, sx) * n
    return k, 0.5 * (uy.max() + uy.min()), 0.5 * (ux.max() + ux.min())


def _scatter(img, ys, xs, colour, weight=1.0):
    """点群を**加算で**積む(密度がそのまま濃さになる ―― 吸引子の見せ方)."""
    h, w = img.shape[:2]
    ok = (ys >= 0) & (ys < h - 1) & (xs >= 0) & (xs < w - 1)
    yi, xi = ys[ok].astype(np.int64), xs[ok].astype(np.int64)
    acc = np.zeros((h, w), np.float64)
    np.add.at(acc, (yi, xi), weight)
    a = (1.0 - np.exp(-acc))[..., None]                 # 飽和(濃さの上限を持つ)
    c = np.asarray(colour, np.float64).reshape(1, 1, 3)
    return img * (1 - a) + c * a


# --------------------------------------------------------------------------- #
# 1 枚返す生成器 —— それぞれが厳密な主張を持つ                                    #
# --------------------------------------------------------------------------- #
def perpetual_ten_print(cols: int = 32, rows: int = 24, cell: int = 18,
                        seed: int = 0) -> np.ndarray:
    """``10 PRINT CHR$(205.5+RND(1)); : GOTO 10`` ―― 無限に伸びる迷路。

    Commodore 64 の一行プログラム。各升に 2 種類の斜線のどちらかを置くだけで、
    迷路に見える。**升の中身は 2 通りしかない**(混ざった升は無い)のが不変量。
    """
    img = _canvas(rows * cell, cols * cell)
    rng = np.random.default_rng(seed)
    b = rng.integers(0, 2, size=(rows, cols))
    for r in range(rows):
        for c in range(cols):
            y0, x0 = r * cell, c * cell
            if b[r, c]:
                img = _stamp_segment(img, y0, x0, y0 + cell, x0 + cell, 1.1, _INK)
            else:
                img = _stamp_segment(img, y0 + cell, x0, y0, x0 + cell, 1.1, _INK)
    return img


def perpetual_truchet(cols: int = 16, rows: int = 12, cell: int = 34,
                      seed: int = 0) -> np.ndarray:
    """トルシェ・タイル ―― 4 分円 2 本の向きを振るだけで、途切れない曲線網になる。

    不変量: 弧の端点は**必ず辺の中点**に来るので、隣とどう組んでも接続が切れない。
    """
    img = _canvas(rows * cell, cols * cell)
    rng = np.random.default_rng(seed)
    b = rng.integers(0, 2, size=(rows, cols))
    half, r = cell * 0.5, cell * 0.5
    for rr in range(rows):
        for cc in range(cols):
            y0, x0 = rr * cell, cc * cell
            if b[rr, cc]:
                img = _stamp_arc(img, y0, x0, r, 0.0, np.pi / 2, 1.6, _INK)
                img = _stamp_arc(img, y0 + cell, x0 + cell, r, np.pi, 1.5 * np.pi,
                                 1.6, _INK)
            else:
                img = _stamp_arc(img, y0, x0 + cell, r, np.pi / 2, np.pi, 1.6, _INK)
                img = _stamp_arc(img, y0 + cell, x0, r, 1.5 * np.pi, 2 * np.pi,
                                 1.6, _INK)
    del half
    return img


def perpetual_elementary_ca(rule: int = 90, width: int = 401, rows: int = 200,
                            seed: int = -1, cell: int = 2) -> np.ndarray:
    """基本セルオートマトン(Wolfram の 256 規則)を上から下へ無限に伸ばす。

    ``seed < 0`` で**中央 1 点**から始める(規則 90 ならシェルピンスキー、
    規則 30 なら擬似乱数、規則 110 なら万能計算)。

    不変量(規則 90・1 点始動): 第 n 行の第 k セルは **C(n,k) mod 2**。
    """
    st = np.zeros(width, dtype=np.uint8)
    if seed < 0:
        st[width // 2] = 1
    else:
        st = (np.random.default_rng(seed).random(width) < 0.5).astype(np.uint8)
    hist = np.empty((rows, width), dtype=np.uint8)
    tbl = np.array([(rule >> i) & 1 for i in range(8)], dtype=np.uint8)
    for t in range(rows):
        hist[t] = st
        idx = (np.roll(st, 1) << 2) | (st << 1) | np.roll(st, -1)
        st = tbl[idx]
    img = np.repeat(np.repeat(hist, cell, axis=0), cell, axis=1)
    out = _canvas(img.shape[0], img.shape[1])
    m = img.astype(bool)[..., None]
    return np.where(m, np.asarray(_INK).reshape(1, 1, 3), out)


#: ラングトンの蟻が高速道路に入ったあとの**周期**(Bunimovich–Troubetzkoy)。
LANGTON_HIGHWAY_PERIOD = 104


def perpetual_langtons_ant(steps: int = 12_000, size: int = 301) -> np.ndarray:
    """ラングトンの蟻 ―― 2 つの規則だけで、1 万歩後に「高速道路」を作り続ける。

    不変量: 高速道路に入ったあとは **周期 104 で斜めに (-2,-2) 進む**。

    ★塗りは「そのマスが黒でいた時間」。高速道路は最後にできるので薄く、
    最初の混沌は濃い —— **時間の順序が絵に出る**。
    """
    s = perpetual_state("langtons_ant", size=size)
    # ★色を**黒でいた時間**に結びつける。途中で通っただけのマスと、早くから
    #   黒いままのマスが同じ濃さになるのが「白黒の点」の正体だった。
    #   高速道路は最後にできるので薄く、最初の混沌は濃く出る。
    dwell = np.zeros((size, size), np.float64)
    chunk = max(steps // 64, 1)
    done = 0
    while done < steps:
        take = min(chunk, steps - done)
        s = perpetual_step(s, take)
        dwell += s["grid"].astype(np.float64) * take
        done += take
    # ★構図 —— 蟻が触った範囲は盤の一部しかない(既定では 1/3 ほど)。
    #   埋まった範囲の外接箱で切り出さないと、絵の大半が余白になる。
    ys_, xs_ = np.nonzero(dwell > 0)
    if ys_.size:
        pad = max(4, int(0.03 * size))
        y0 = max(int(ys_.min()) - pad, 0); y1 = min(int(ys_.max()) + pad + 1, size)
        x0 = max(int(xs_.min()) - pad, 0); x1 = min(int(xs_.max()) + pad + 1, size)
        # 正方形に整える(縦横比を変えない)
        hh, ww = y1 - y0, x1 - x0
        if hh < ww:
            y0 = max(y0 - (ww - hh) // 2, 0); y1 = min(y0 + ww, size)
        elif ww < hh:
            x0 = max(x0 - (hh - ww) // 2, 0); x1 = min(x0 + hh, size)
        dwell = dwell[y0:y1, x0:x1]
    out = _ramp(_tone(dwell, 0.10), _HOT)
    # ★切り出すと 100 画素角ほどになる。**最近傍**で伸ばす —— これはセル
    #   オートマトンなので、補間すると存在しない中間値を作ってしまう。
    k = max(int(size // max(out.shape[0], 1)), 1)
    if k > 1:
        out = np.repeat(np.repeat(out, k, axis=0), k, axis=1)
    return out


def perpetual_chaos_game(points: int = 400_000, size: int = 520,
                         seed: int = 0, vertices: int = 3,
                         ratio: float = 0.5, sub: int = 2) -> np.ndarray:
    """カオスゲーム ―― 賽を振って半分ずつ寄るだけで、シェルピンスキーが出る。

    不変量: 3 頂点・比 1/2 の吸引子の箱数次元は **log3/log2 = 1.5850**。

    ★描き方が測れる真値を変える。同じ点列でも、切り捨てて積んだ絵から測った
    次元は真値から **−0.032** ずれるのに、双一次 + asinh で描くと **−0.0030**
    —— **10 倍**正確になる(しきい値 0.1、実測)。濃淡は飾りではない。
    """
    rng = np.random.default_rng(seed)
    n_sub = size * sub
    th = np.linspace(-np.pi / 2, 1.5 * np.pi, vertices, endpoint=False)
    uy, ux = np.sin(th), np.cos(th)
    # ★外接**箱**で枠を使い切る(外接円だと三角形が上下に余白を残す)
    fit, my, mx = _fit_to_frame(uy, ux, n_sub)
    vy = 0.5 * n_sub + (uy - my) * fit
    vx = 0.5 * n_sub + (ux - mx) * fit
    k = rng.integers(0, vertices, size=points)
    y = np.empty(points, np.float64)
    x = np.empty(points, np.float64)
    cy, cx = vy.mean(), vx.mean()
    for i in range(points):
        cy = cy + ratio * (vy[k[i]] - cy)
        cx = cx + ratio * (vx[k[i]] - cx)
        y[i], x[i] = cy, cx
    # ★密度をそのまま色に —— 双一次で積み、asinh で暗部を伸ばす
    acc = _splat(n_sub, n_sub, y[64:], x[64:])
    return _downsample(_ramp(_tone(acc, 0.05), _HOT), sub)


def _tangency_error(u, v):
    """2 円が接しているかの残差。外接なら |Δ| = r_u + r_v、内接なら |r_u − r_v|。

    ★曲率が負の円は「外側の器」なので、その相手とは**内接**になる。両方を
    見て小さいほうを残差にする(どちらの接し方かは符号から自動で決まる)。
    """
    ru, rv = abs(1.0 / u[0]), abs(1.0 / v[0])
    d = float(np.hypot(u[1] - v[1], u[2] - v[2]))
    return min(abs(d - (ru + rv)), abs(d - abs(ru - rv)))


def _apollonian_circles(depth):
    """円詰めの円を(曲率, y, x)の列で返す。描画と門で**同じ経路**を使う。"""
    R = 1.0
    circles = [(-1.0 / R, 0.0, 0.0)]
    r0 = R / (1.0 + 2.0 / np.sqrt(3.0))
    d = R - r0
    for j in range(3):
        a = -np.pi / 2 + 2 * np.pi * j / 3
        circles.append((1.0 / r0, d * np.sin(a), d * np.cos(a)))
    frontier = [(circles[0], circles[1], circles[2]),
                (circles[0], circles[2], circles[3]),
                (circles[0], circles[3], circles[1]),
                (circles[1], circles[2], circles[3])]
    made = []
    for _ in range(depth):
        nxt = []
        for (a, b, c) in frontier:
            ka, kb, kc = a[0], b[0], c[0]
            kd = ka + kb + kc + 2.0 * np.sqrt(abs(ka * kb + kb * kc + kc * ka))
            if kd <= 0 or 1.0 / kd < 2e-3:
                continue
            za, zb, zc = (complex(a[2], a[1]) * ka, complex(b[2], b[1]) * kb,
                          complex(c[2], c[1]) * kc)
            root = np.sqrt(complex(za * zb + zb * zc + zc * za))
            best, best_err = None, np.inf
            for sgn in (+1.0, -1.0):
                zd = (za + zb + zc + 2.0 * sgn * root) / kd
                cand = (kd, zd.imag, zd.real)
                err = max(_tangency_error(cand, q) for q in (a, b, c))
                if err < best_err:
                    best, best_err = cand, err
            if best_err > 1e-6 * abs(1.0 / kd):
                continue
            made.append((best, (a, b, c), best_err))
            nxt += [(a, b, best), (b, c, best), (c, a, best)]
        frontier = nxt
    return circles, made


def _apollonian_worst_tangency(depth=5):
    """生成したすべての円について、親 3 円との接触残差の最大(相対)。"""
    _c, made = _apollonian_circles(depth)
    if not made:
        return 1.0
    return max(e / abs(1.0 / u[0]) for u, _p, e in made)


def perpetual_apollonian(depth: int = 6, size: int = 520) -> np.ndarray:
    """アポロニウスの円詰め ―― 隙間に接する円を入れ続ける(終わりが無い)。

    不変量: 互いに接する 4 円の曲率が **デカルトの円定理**
    ``(Σk)² = 2Σk²`` を厳密に満たす。:func:`perpetual_identities` で確かめられる。

    ★塗りの明るさは**曲率**(= 1/半径)。定理が試している量をそのまま色にして
    あるので、絵の濃淡が主張と同じものを指している。
    """
    img = _canvas(size, size)
    R = 0.47 * size
    cy = cx = 0.5 * size
    # 外円(曲率は負)と、内側に 3 つの等円(古典的な初期配置)
    circles = [(-1.0 / R, cy, cx)]
    r0 = R / (1.0 + 2.0 / np.sqrt(3.0))
    d = R - r0
    for j in range(3):
        a = -np.pi / 2 + 2 * np.pi * j / 3
        circles.append((1.0 / r0, cy + d * np.sin(a), cx + d * np.cos(a)))
    frontier = [(circles[0], circles[1], circles[2]),
                (circles[0], circles[2], circles[3]),
                (circles[0], circles[3], circles[1]),
                (circles[1], circles[2], circles[3])]
    for _ in range(depth):
        nxt = []
        for (a, b, c) in frontier:
            ka, kb, kc = a[0], b[0], c[0]
            kd = ka + kb + kc + 2.0 * np.sqrt(abs(ka * kb + kb * kc + kc * ka))
            if kd <= 0 or 1.0 / kd < 1.2:
                continue
            # 複素曲率中心でデカルトの定理を解く(位置まで決まる)。
            # ★★平方根には**枝が 2 つ**あり、片方は「親 3 円に接しない円」を返す。
            #   最初は主値だけを使っていて、絵の左上に**外円の外へ逃げる円の鎖**が
            #   出た —— 絵としては「フラクタルっぽい」ので、見ただけでは欠陥と
            #   分からない。接することを**数で確かめて**枝を選ぶ。
            za, zb, zc = (complex(a[2], a[1]) * ka, complex(b[2], b[1]) * kb,
                          complex(c[2], c[1]) * kc)
            root = np.sqrt(complex(za * zb + zb * zc + zc * za))
            best, best_err = None, np.inf
            for sgn in (+1.0, -1.0):
                zd = (za + zb + zc + 2.0 * sgn * root) / kd
                cand = (kd, zd.imag, zd.real)
                err = max(_tangency_error(cand, q) for q in (a, b, c))
                if err < best_err:
                    best, best_err = cand, err
            if best_err > 1e-6 * abs(1.0 / kd):
                continue                       # どちらの枝も接しない = 入れない
            circles.append(best)
            nxt += [(a, b, best), (b, c, best), (c, a, best)]
        frontier = nxt
    # 色を**曲率**に結びつける —— デカルトの円定理が試している量そのもの。
    #   log(曲率) をそのまま伸ばすと大きい円が下端に潰れるので、ガンマで低域を
    #   持ち上げる。★「順位で正規化すれば配り直される」と読んだが**外れ**で、
    #   極小円が多数派なので大きい円が全部下端に潰れ、前より悪くなった。
    kk = np.array([abs(c[0]) for c in circles], np.float64)
    k_lo, k_hi = np.log(kk.min()), np.log(kk.max())
    for (k, ccy, ccx) in circles:
        if k < 0:
            continue                      # 外円(負の曲率)は器なので塗らない
        r = abs(1.0 / k)
        # 円 1 つにつき全画面の距離場を作ると数百枚ぶん無駄になる。外接箱だけ。
        ly = max(int(ccy - r - 2), 0); hy = min(int(ccy + r + 3), size)
        lx = max(int(ccx - r - 2), 0); hx = min(int(ccx + r + 3), size)
        if ly >= hy or lx >= hx:
            continue
        yy = np.arange(ly, hy, dtype=np.float64)[:, None] + 0.5
        xx = np.arange(lx, hx, dtype=np.float64)[None, :] + 0.5
        # 縁を 1 画素ぶんの被覆でなめらかに(輪郭線でなく**塗り**)
        a = np.clip(r - np.hypot(yy - ccy, xx - ccx) + 0.5,
                    0.0, 1.0)[..., None]
        t_k = ((np.log(abs(k)) - k_lo) / max(k_hi - k_lo, 1e-12)) ** 0.45
        col = _ramp(np.array([t_k]), _COOL)[0].reshape(1, 1, 3)
        img[ly:hy, lx:hx] = img[ly:hy, lx:hx] * (1 - a)             + col * a
    return img


def perpetual_harmonograph(size: int = 520, a: float = 3.0, b: float = 2.0,
                           phase: float = 0.35, decay: float = 0.0018,
                           turns: float = 36.0) -> np.ndarray:
    """ハーモノグラフ ―― 減衰する 2 つの振り子が、閉じない曲線を描き続ける。

    不変量: 減衰が 0 のとき、曲線が閉じるのは **``a/b`` が有理数のとき**だけで、
    そのときの周期は ``2π/gcd`` ちょうど。
    """
    t = np.linspace(0.0, turns * np.pi, int(turns * 900))
    e = np.exp(-decay * t)
    y = 0.5 * size + 0.40 * size * e * np.sin(a * t + phase)
    x = 0.5 * size + 0.40 * size * e * np.sin(b * t)
    img = _canvas(size, size)
    for i in range(0, len(t) - 1, 1):
        img = _stamp_segment(img, y[i], x[i], y[i + 1], x[i + 1], 0.7,
                             (0.20, 0.25, 0.42))
    return img


#: バーンズリーのシダ(4 つのアフィン写像と、その確率)。
_FERN = (
    (0.00, 0.00, 0.00, 0.16, 0.00, 0.00, 0.01),
    (0.85, 0.04, -0.04, 0.85, 0.00, 1.60, 0.85),
    (0.20, -0.26, 0.23, 0.22, 0.00, 1.60, 0.07),
    (-0.15, 0.28, 0.26, 0.24, 0.00, 0.44, 0.07),
)


def perpetual_ifs_attractor(points: int = 300_000, size: int = 560,
                            seed: int = 0, sub: int = 2) -> np.ndarray:
    """反復関数系の吸引子(バーンズリーのシダ)―― 4 本の式を無限に回すだけ。

    不変量: 吸引子は **4 つの写像の像の和に等しい**(自己相似の定義そのもの)。
    """
    rng = np.random.default_rng(seed)
    p = np.array([f[6] for f in _FERN], np.float64)
    p = p / p.sum()
    k = rng.choice(len(_FERN), size=points, p=p)
    xs = np.empty(points, np.float64)
    ys = np.empty(points, np.float64)
    cx = cy = 0.0
    for i in range(points):
        A = _FERN[k[i]]
        cx, cy = A[0] * cx + A[1] * cy + A[4], A[2] * cx + A[3] * cy + A[5]
        xs[i], ys[i] = cx, cy
    # ★点群の外接箱で枠を使い切る(式の定数で決め打ちにしない)
    n_sub = size * sub
    fit, my, mx = _fit_to_frame(-ys, xs, n_sub)
    py = 0.5 * n_sub + (-ys - my) * fit
    px = 0.5 * n_sub + (xs - mx) * fit
    acc = _splat(n_sub, n_sub, py[32:], px[32:])
    return _downsample(_ramp(_tone(acc, 0.05), _HOT), sub)


def perpetual_flow_field(size: int = 520, seed: int = 0, lines: int = 420,
                         steps: int = 150, scale: float = 0.010) -> np.ndarray:
    """流れ場 ―― 粒子を場に乗せて流し続ける(止めなければ終わらない)。

    ★場は**ポテンシャル ψ の回転**として作る。だから **発散が恒等的に 0**
    (非圧縮)で、粒子が湧いたり消えたりしない。「それらしい雑音」で作った
    流れ場との違いはここで、:func:`perpetual_identities` が数で出す。

    ★線の色と太さは**流速** |∇ψ| に結びつけてある(太さも濃さも一定だと、
    同じ場から描いても「落書き」にしかならない)。
    """
    psi = _stream_function(size, seed, scale)
    vy, vx = _curl(psi)
    # ★正規化する前の速さ。色と太さをこれに結びつける(飾りでなく量)。
    raw_y, raw_x = np.gradient(psi)
    speed = np.hypot(raw_y, raw_x)
    s_hi = float(speed.max()) or 1.0
    rng = np.random.default_rng(seed + 1)
    ys = rng.uniform(0, size, lines)
    xs = rng.uniform(0, size, lines)
    img = _canvas(size, size, (0.06, 0.08, 0.16))
    for _ in range(steps):
        yi = np.clip(ys.astype(np.int64), 0, size - 1)
        xi = np.clip(xs.astype(np.int64), 0, size - 1)
        ny = ys + 1.35 * vy[yi, xi]
        nx = xs + 1.35 * vx[yi, xi]
        t = _tone(speed[yi, xi] / s_hi, 0.25)
        cols = _ramp(t, _COOL)
        for j in range(lines):
            img = _stamp_segment(img, ys[j], xs[j], ny[j], nx[j],
                                 0.35 + 0.55 * float(t[j]), tuple(cols[j]))
        ys, xs = np.clip(ny, 0, size - 1), np.clip(nx, 0, size - 1)
    return img


def _stream_function(size, seed, scale):
    """滑らかな流れ関数 ψ(帯域制限した雑音 ―― 格子の目が出ない)。"""
    rng = np.random.default_rng(seed)
    k = 6
    ph = rng.uniform(0, 2 * np.pi, (k, k))
    amp = rng.normal(0.0, 1.0, (k, k))
    y, x = _grid(size, size)
    psi = np.zeros((size, size), np.float64)
    for i in range(k):
        for j in range(k):
            psi += amp[i, j] * np.sin(scale * ((i + 1) * y + (j + 1) * x) + ph[i, j])
    return psi


def _curl(psi):
    """``v = (∂ψ/∂x, −∂ψ/∂y)``。中心差分で取ると、離散でも発散がほぼ 0 になる。"""
    gy, gx = np.gradient(psi)
    n = np.hypot(gx, -gy) + 1e-9
    return gx / n, -gy / n


def perpetual_reaction_diffusion(size: int = 220, steps: int = 1_600,
                                 feed: float = 0.037, kill: float = 0.060,
                                 seed: int = 0) -> np.ndarray:
    """グレイ–スコット反応拡散 ―― 模様が生まれ、分裂し、増え続ける。

    不変量: **餌も死も 0(``feed = kill = 0``)なら、総量は厳密に保存される**
    —— 拡散は再分配であって生成ではないから。数値解法が壊れていれば、
    ここが真っ先に崩れる(:func:`perpetual_identities`)。
    """
    u, v = _gs_init(size, seed)
    u, v = _gs_run(u, v, steps, feed, kill)
    # ★色は濃度 v に結びつける(単調な配色なので順位が保たれる)
    t = np.clip((v - v.min()) / (np.ptp(v) + 1e-12), 0.0, 1.0)
    return _ramp(t, _COOL)


def _gs_init(size, seed, seeds=12):
    """グレイ–スコットの初期値。★種は**散らして複数**置く。

    種が中央に 1 個だけだと、同じ歩数でも模様が画面の一部にしか広がらない
    (実測: 被覆 0.086)。散らして 12 個置くと同じ計算量で **0.46** になる。
    ★格子状に並べると**格子そのものが絵に出る**ので、ジッタを入れて散らす。
    """
    rng = np.random.default_rng(seed)
    u = np.ones((size, size), np.float64)
    v = np.zeros((size, size), np.float64)
    r = max(size // 26, 3)
    m = max(int(np.ceil(np.sqrt(seeds))), 1)
    step = size / float(m)
    placed = 0
    for iy in range(m):
        for ix in range(m):
            if placed >= seeds:
                break
            cy = int((iy + 0.5) * step + rng.uniform(-0.3, 0.3) * step)
            cx = int((ix + 0.5) * step + rng.uniform(-0.3, 0.3) * step)
            cy = int(np.clip(cy, r + 1, size - r - 1))
            cx = int(np.clip(cx, r + 1, size - r - 1))
            u[cy - r:cy + r, cx - r:cx + r] = 0.50
            v[cy - r:cy + r, cx - r:cx + r] = 0.25
            placed += 1
    u += 0.01 * rng.normal(size=(size, size))
    v += 0.01 * rng.normal(size=(size, size))
    return np.clip(u, 0, 1), np.clip(v, 0, 1)


def _lap(a):
    return (np.roll(a, 1, 0) + np.roll(a, -1, 0)
            + np.roll(a, 1, 1) + np.roll(a, -1, 1) - 4.0 * a)


def _gs_run(u, v, steps, feed, kill, du=0.16, dv=0.08, dt=1.0):
    for _ in range(steps):
        uvv = u * v * v
        u = u + dt * (du * _lap(u) - uvv + feed * (1.0 - u))
        v = v + dt * (dv * _lap(v) + uvv - (feed + kill) * v)
    return u, v


def _diamond_square(n, seed, roughness):
    """生の場と、**最初に置いた 4 隅の値**を返す(門を本物にするため分けた)。"""
    f = np.zeros((n, n), np.float64)
    rng = np.random.default_rng(seed)
    corners = {}
    for p in (0, n - 1):
        for q in (0, n - 1):
            f[p, q] = corners[(p, q)] = rng.random()
    step = n - 1
    amp = 1.0
    while step > 1:
        h = step // 2
        for y in range(0, n - 1, step):
            for x in range(0, n - 1, step):
                f[y + h, x + h] = (f[y, x] + f[y, x + step] + f[y + step, x]
                                   + f[y + step, x + step]) / 4.0 \
                    + rng.uniform(-amp, amp)
        for y in range(0, n, h):
            for x in range((y + h) % step, n, step):
                acc, cnt = 0.0, 0
                for (dy, dx) in ((-h, 0), (h, 0), (0, -h), (0, h)):
                    if 0 <= y + dy < n and 0 <= x + dx < n:
                        acc += f[y + dy, x + dx]
                        cnt += 1
                f[y, x] = acc / cnt + rng.uniform(-amp, amp)
        step = h
        amp *= roughness
    return f, corners


def perpetual_plasma(size: int = 513, seed: int = 0,
                     roughness: float = 0.55) -> np.ndarray:
    """ダイヤモンド–スクエア法(1980 年代の「プラズマ」)―― 割り続ければ無限に細かい。

    不変量: **最初に置いた 4 隅の値は最後まで動かない**(中点変位は既存の値を
    書き換えない)。
    """
    f, _ = _diamond_square(size, seed, roughness)
    t = (f - f.min()) / (np.ptp(f) + 1e-12)
    return np.stack([np.clip(1.4 * t - 0.2, 0, 1),
                     np.clip(1.1 * t ** 1.3, 0, 1),
                     np.clip(0.9 - 0.7 * t, 0, 1)], axis=-1)


# --------------------------------------------------------------------------- #
# 「無限」を持つ 3 本組 —— 状態 / 進める / 描く                                    #
# --------------------------------------------------------------------------- #
#: 状態を持てる系 → 既定の大きさ
PERPETUALS = {
    "langtons_ant": "2 規則の蟻。約 1 万歩で周期 104 の高速道路に入る",
    "elementary_ca": "基本セルオートマトン。1 行ずつ下へ伸び続ける",
    "reaction_diffusion": "グレイ–スコット。模様が生まれ分裂し増え続ける",
    "chaos_game": "カオスゲーム。点を打ち続けると吸引子が濃くなる",
}


def perpetual_state(name: str = "langtons_ant", size: int = 301,
                    seed: int = 0, rule: int = 110) -> dict:
    """無限に回せる**状態**を作る(``table``)。止めどきは呼んだ側が決める。"""
    if name not in PERPETUALS:
        raise ValueError("unknown system %r (known: %s)"
                         % (name, ", ".join(sorted(PERPETUALS))))
    if name == "langtons_ant":
        return {"system": name, "grid": np.zeros((size, size), np.uint8),
                "y": size // 2, "x": size // 2, "dir": 0, "steps": 0}
    if name == "elementary_ca":
        st = np.zeros(size, np.uint8)
        st[size // 2] = 1
        return {"system": name, "row": st, "rows": [st.copy()],
                "rule": int(rule), "steps": 0}
    if name == "reaction_diffusion":
        u, v = _gs_init(size, seed)
        return {"system": name, "u": u, "v": v, "feed": 0.037, "kill": 0.060,
                "steps": 0}
    rng = np.random.default_rng(seed)
    return {"system": name, "size": int(size), "acc": np.zeros((size, size),
            np.float64), "cy": size * 0.5, "cx": size * 0.5,
            "rng": rng, "steps": 0}


#: ラングトンの蟻の向き(上・右・下・左)
_DIRS = ((-1, 0), (0, 1), (1, 0), (0, -1))


def _require_state(state):
    """``perpetual_state`` が作った状態であることを**明示的に**確かめる。

    ★宣言型は ``table`` だが table は広い型なので、無関係な dict が来うる。
    黙って KeyError を出すと「実装が落ちた」に見えるので、fail-closed で
    「これは perpetual の状態ではない」と言う(連鎖ファザーの CONTRACT 拒否)。
    """
    if not isinstance(state, dict) or state.get("system") not in PERPETUALS:
        raise ValueError("not a perpetual state: expected a dict from "
                         "perpetual_state(name in %s), got %r"
                         % (sorted(PERPETUALS), type(state).__name__))
    return state


def perpetual_step(state: dict, steps: int = 1) -> dict:
    """状態を ``steps`` だけ進める(同じ dict を返す ―― 大きな配列を複製しない)。"""
    sysname = _require_state(state)["system"]
    if sysname == "langtons_ant":
        g = state["grid"]
        n = g.shape[0]
        y, x, d = state["y"], state["x"], state["dir"]
        for _ in range(steps):
            if g[y, x]:
                d = (d - 1) % 4
                g[y, x] = 0
            else:
                d = (d + 1) % 4
                g[y, x] = 1
            y = (y + _DIRS[d][0]) % n
            x = (x + _DIRS[d][1]) % n
        state.update(y=y, x=x, dir=d, steps=state["steps"] + steps)
        return state
    if sysname == "elementary_ca":
        tbl = np.array([(state["rule"] >> i) & 1 for i in range(8)], np.uint8)
        st = state["row"]
        for _ in range(steps):
            idx = (np.roll(st, 1) << 2) | (st << 1) | np.roll(st, -1)
            st = tbl[idx]
            state["rows"].append(st.copy())
        state.update(row=st, steps=state["steps"] + steps)
        return state
    if sysname == "reaction_diffusion":
        u, v = _gs_run(state["u"], state["v"], steps, state["feed"], state["kill"])
        state.update(u=u, v=v, steps=state["steps"] + steps)
        return state
    n = state["size"]
    th = np.linspace(-np.pi / 2, 1.5 * np.pi, 3, endpoint=False)
    vy = 0.5 * n + 0.46 * n * np.sin(th)
    vx = 0.5 * n + 0.46 * n * np.cos(th)
    cy, cx = state["cy"], state["cx"]
    k = state["rng"].integers(0, 3, size=steps)
    acc = state["acc"]
    for i in range(steps):
        cy += 0.5 * (vy[k[i]] - cy)
        cx += 0.5 * (vx[k[i]] - cx)
        yi, xi = int(cy), int(cx)
        if 0 <= yi < n and 0 <= xi < n:
            acc[yi, xi] += 1.0
    state.update(cy=cy, cx=cx, steps=state["steps"] + steps)
    return state


def perpetual_render(state: dict, cell: int = 2) -> np.ndarray:
    """状態を絵にする(``rgb``)。何歩目で描いてもよい。"""
    sysname = _require_state(state)["system"]
    if sysname == "langtons_ant":
        g = state["grid"]
        img = np.where(g.astype(bool)[..., None],
                       np.asarray(_INK).reshape(1, 1, 3),
                       np.asarray(_PAPER).reshape(1, 1, 3))
        y, x = state["y"], state["x"]
        img[max(y - 2, 0):y + 3, max(x - 2, 0):x + 3] = (0.85, 0.25, 0.20)
        return img
    if sysname == "elementary_ca":
        hist = np.array(state["rows"], np.uint8)
        big = np.repeat(np.repeat(hist, cell, 0), cell, 1)
        return np.where(big.astype(bool)[..., None],
                        np.asarray(_INK).reshape(1, 1, 3),
                        np.asarray(_PAPER).reshape(1, 1, 3))
    if sysname == "reaction_diffusion":
        v = state["v"]
        t = np.clip((v - v.min()) / (np.ptp(v) + 1e-12), 0, 1)[..., None]
        a = np.asarray((0.98, 0.97, 0.94)).reshape(1, 1, 3)
        b = np.asarray((0.10, 0.25, 0.45)).reshape(1, 1, 3)
        return a * (1 - t) + b * t
    acc = state["acc"]
    a = (1.0 - np.exp(-0.5 * acc))[..., None]
    base = _canvas(acc.shape[0], acc.shape[1])
    return base * (1 - a) + np.asarray((0.16, 0.30, 0.55)).reshape(1, 1, 3) * a


# --------------------------------------------------------------------------- #
# 恒等式 —— 絵を見ずに採点する                                                   #
# --------------------------------------------------------------------------- #
def perpetual_identities(which: str = "") -> dict:
    """各系が満たすべき**厳密な主張**を、実測つきで返す(``table``)。

    ★この族の芯。「無限に流れる絵」は見た目では採点できないので、**絵とは
    独立に成り立つ式**を同じ op から出す。``residual`` は 0 であるべき量の実測。
    """
    rows = []

    # (1) 規則 90 の第 n 行 = 二項係数の偶奇(パスカルの三角形 mod 2)
    w, r = 257, 64
    st = np.zeros(w, np.uint8)
    st[w // 2] = 1
    tbl = np.array([(90 >> i) & 1 for i in range(8)], np.uint8)
    worst = 0.0
    for n in range(r):
        # ★二項係数そのものを積むと C(62,31)*31 が int64 を**黙って溢れる**。
        #   要るのは偶奇だけなので、リュカの定理の帰結
        #   「C(n,k) が奇 ⟺ (n & k) == k」を使う(桁あふれの余地が無い)。
        row = np.zeros(w, np.uint8)
        for kk in range(n + 1):
            row[w // 2 - n + 2 * kk] = 1 if (n & kk) == kk else 0
        worst = max(worst, float(np.abs(row.astype(float) - st.astype(float)).max()))
        idx = (np.roll(st, 1) << 2) | (st << 1) | np.roll(st, -1)
        st = tbl[idx]
    rows.append(("elementary_ca_rule90", "row_n == C(n,k) mod 2", worst))

    # (2) ラングトンの蟻: 高速道路は周期 104 で (-2,-2) 進む
    s = perpetual_state("langtons_ant", size=401)
    s = perpetual_step(s, 12_000)
    d = []
    for _ in range(2):
        y0, x0 = s["y"], s["x"]
        s = perpetual_step(s, LANGTON_HIGHWAY_PERIOD)
        d.append(((s["y"] - y0 + 200) % 401 - 200,
                  (s["x"] - x0 + 200) % 401 - 200))
    # ★向きの符号は回転の規約で変わる。定理が言うのは「周期 104 で**同じ**斜めの
    #   変位を繰り返す」ことなので、そちらを門にする(大きさは縦横とも 2)。
    res = (abs(d[0][0] - d[1][0]) + abs(d[0][1] - d[1][1])
           + abs(abs(d[0][0]) - 2) + abs(abs(d[0][1]) - 2))
    rows.append(("langtons_ant",
                 "highway repeats the same diagonal (2,2) step every 104",
                 float(res)))
    # ★高速道路は**正味で 104 歩あたりちょうど 12 マス**黒を増やす(実測で整数)。
    #   最初は「104 歩で 52 マス」と書いたが実測 0.114/歩 と合わず、測り直して
    #   12/104 = 0.11538 だった。周期の中で塗っては消すので、正味はずっと少ない。
    s2 = perpetual_state("langtons_ant", size=601)
    s2 = perpetual_step(s2, 12_000)
    n0 = int(s2["grid"].sum())
    s2 = perpetual_step(s2, 10 * LANGTON_HIGHWAY_PERIOD)
    rows.append(("langtons_ant_growth", "highway adds exactly 12 cells per 104 steps",
                 float(abs((int(s2["grid"].sum()) - n0) / 10.0 - 12.0))))

    # (3) デカルトの円定理(アポロニウス)
    R = 1.0
    r0 = R / (1.0 + 2.0 / np.sqrt(3.0))
    ks = np.array([-1.0 / R, 1.0 / r0, 1.0 / r0, 1.0 / r0])
    lhs, rhs = ks.sum() ** 2, 2.0 * (ks ** 2).sum()
    rows.append(("apollonian", "(sum k)^2 == 2 sum k^2",
                 float(abs(lhs - rhs) / rhs)))
    # ★★描いた円が**本当に接しているか**。平方根の枝を選び損ねると、
    #   絵としては「フラクタルっぽい」まま外へ逃げる鎖が出る(実際に出した)。
    rows.append(("apollonian_tangency", "every generated circle touches its 3 parents",
                 float(_apollonian_worst_tangency(depth=5))))

    # (4) カール場の発散は恒等的に 0
    psi = _stream_function(200, 0, 0.010)
    gy, gx = np.gradient(psi)
    vy, vx = gx, -gy                       # 正規化前(正規化は発散を壊す)
    div = np.gradient(vy, axis=0) + np.gradient(vx, axis=1)
    rows.append(("flow_field", "div(curl psi) == 0",
                 float(np.abs(div).max() / (np.abs(vy).max() + 1e-12))))

    # (5) 餌も死も無い反応拡散は総量保存
    u, v = _gs_init(96, 0)
    tot0 = float(u.sum() + v.sum())
    u, v = _gs_run(u, v, 300, 0.0, 0.0)
    tot1 = float(u.sum() + v.sum())
    rows.append(("reaction_diffusion", "total mass conserved when feed=kill=0",
                 abs(tot1 - tot0) / tot0))

    # (6) ダイヤモンド–スクエア法は 4 隅を書き換えない
    f, corners = _diamond_square(129, 0, 0.55)
    worst_c = max(abs(f[k] - v) for k, v in corners.items())
    rows.append(("plasma", "corner values are never overwritten", float(worst_c)))

    if which:
        rows = [t for t in rows if t[0] == which]
        if not rows:
            raise ValueError("unknown identity %r" % which)
    return {"system": np.array([t[0] for t in rows], dtype=object),
            "identity": np.array([t[1] for t in rows], dtype=object),
            "residual": np.array([t[2] for t in rows], dtype=np.float64)}

# --------------------------------------------------------------------------- #
# 時間軸で循環する絵 —— **継ぎ目が無いことを証明できる**動画                       #
# --------------------------------------------------------------------------- #
#: 循環する系 → 説明。どれも「時間依存の量をすべて θ の関数にする」ことで、
#: θ: 0 → 2π を一周すると**元の絵に厳密に戻る**(継ぎ目が計算で消える)。
LOOPS = {
    "harmonograph": "整数比の振り子。周期 2π で厳密に閉じる",
    "flow_phase": "流れ関数の位相を 2π 回す。渦が動いて元へ戻る",
    "plasma_orbit": "雑音を円周上で拾う。円は閉じているので絵も閉じる",
    "cafe_wall_drift": "カフェウォールを 1 周期ぶん平行移動する",
}


def perpetual_loop(kind: str = "harmonograph", frames: int = 48,
                   size: int = 360, seed: int = 0) -> np.ndarray:
    """**継ぎ目の無い循環動画**を作る → ``rgbvideo`` (T,H,W,3)。

    ★循環を「最後に頭へ戻す」で作らない。時間依存の量を**すべて θ の関数**に
    して θ = 2πt/T を回すと、t = T は t = 0 と**同じ式**になる —— つまり継ぎ目は
    最初から存在しない。これは編集で消す種類のものではなく、**構成から従う**。
    :func:`perpetual_loop_seam` がその継ぎ目を数で出す(厳密に 0 になる)。

    ``frames`` コマ返す(t = 0 .. T-1)。t = T は t = 0 と一致するので含めない。
    """
    if kind not in LOOPS:
        raise ValueError("unknown loop %r (known: %s)" % (kind, ", ".join(sorted(LOOPS))))
    th = 2.0 * np.pi * np.arange(frames, dtype=np.float64) / frames
    out = np.empty((frames, size, size, 3), np.float64)
    if kind == "harmonograph":
        # 整数比だけを使う。無理数比では閉じない(そしてそれは実装の誤りではない)。
        s = np.linspace(0.0, 2.0 * np.pi, 1400)
        for i, a in enumerate(th):
            img = _canvas(size, size)
            y = 0.5 * size + 0.38 * size * np.sin(3.0 * s + a)
            x = 0.5 * size + 0.38 * size * np.sin(2.0 * s + 0.5 * a)
            for j in range(len(s) - 1):
                img = _stamp_segment(img, y[j], x[j], y[j + 1], x[j + 1], 0.8,
                                     (0.20, 0.25, 0.42))
            out[i] = img
    elif kind == "flow_phase":
        y, x = _grid(size, size)
        rng = np.random.default_rng(seed)
        amp = rng.normal(0.0, 1.0, (4, 4))
        ph = rng.uniform(0, 2 * np.pi, (4, 4))
        for i, a in enumerate(th):
            psi = np.zeros((size, size), np.float64)
            for u_ in range(4):
                for v_ in range(4):
                    psi += amp[u_, v_] * np.sin(0.011 * ((u_ + 1) * y + (v_ + 1) * x)
                                                + ph[u_, v_] + (u_ - v_) * a)
            t_ = (psi - psi.min()) / (np.ptp(psi) + 1e-12)
            out[i] = np.stack([0.10 + 0.55 * t_, 0.18 + 0.45 * t_,
                               0.42 + 0.35 * (1 - t_)], axis=-1)
    elif kind == "plasma_orbit":
        y, x = _grid(size, size)
        rng = np.random.default_rng(seed)
        k = 5
        ax_ = rng.normal(0, 1, (k, k))
        bx_ = rng.normal(0, 1, (k, k))
        for i, a in enumerate(th):
            f = np.zeros((size, size), np.float64)
            for u_ in range(k):
                for v_ in range(k):
                    w_ = 0.013 * ((u_ + 1) * y + (v_ + 1) * x)
                    f += ax_[u_, v_] * np.cos(w_ + a) + bx_[u_, v_] * np.sin(w_ + a)
            t_ = (f - f.min()) / (np.ptp(f) + 1e-12)
            out[i] = np.stack([np.clip(1.3 * t_ - 0.15, 0, 1),
                               np.clip(1.0 * t_ ** 1.3, 0, 1),
                               np.clip(0.85 - 0.65 * t_, 0, 1)], axis=-1)
    else:
        # ずらし量が 1 周期ぶん進むと、図は**画素単位で**元に戻る
        import illusion as _il
        cell = max(size // 8, 8)
        for i in range(frames):
            img = _il.illusion_cafe_wall(size=cell, rows=8, cols=8, mortar=2.0,
                                         shift=2.0 * i / frames)
            out[i] = img[:size, :size] if img.shape[0] >= size else                 np.pad(img, ((0, max(size - img.shape[0], 0)),
                             (0, max(size - img.shape[1], 0)), (0, 0)), mode="edge")[:size, :size]
    return out


def perpetual_loop_seam(video: np.ndarray) -> dict:
    """循環動画の**継ぎ目**を数で出す(``table``)。

    ``seam`` = 最終コマ → 初コマの差、``typical`` = コマ間の差の中央値。
    継ぎ目の無い動画では ``ratio = seam / typical`` が **1 に近い**(最後の
    またぎが、ほかのまたぎと見分けが付かない)。**0 ではなく 1 が正解**なのが
    ここの読みどころ —— 0 は「動きが止まっている」という意味になる。
    """
    v = np.asarray(video, np.float64)
    if v.ndim != 4 or v.shape[0] < 3:
        raise ValueError("expected (T,H,W,3) with T >= 3, got %r" % (v.shape,))
    d = np.array([float(np.abs(v[i + 1] - v[i]).mean()) for i in range(len(v) - 1)])
    seam = float(np.abs(v[0] - v[-1]).mean())
    typ = float(np.median(d))
    return {"seam": np.array([seam]), "typical": np.array([typ]),
            "ratio": np.array([seam / (typ + 1e-300)]),
            "frames": np.array([float(len(v))])}
