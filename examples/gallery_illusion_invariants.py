# -*- coding: utf-8 -*-
"""事例: 錯視図と終わらない絵を、目でなく数で確かめる(illusion / perpetual ギャラリー)

平たく言うと:
  錯視図は「目が否定している事実」を図にしたもの —— 同じ灰色、同じ長さ、同心円、描かれていない輪郭。
  その事実は画素の数として厳密に成り立っていなければならない(絵は「それらしく」見えるので、
  数で確かめるまで壊れていても気づけない)。ここでは錯視 7 op と、規則で描き続ける絵 2 op を呼び、
  幾何の不変量・独立に書いたシミュレーションを真値にして照合する。外れたら exit 1。図は作らない。

確かめ方(op ごとの真値):
  * illusion_checker_shadow       —— CHECKER_PATCHES の 2 マス(影の外の暗・影の中の明)が厳密に同値、明マス同士は違う
  * illusion_simultaneous_contrast —— 左右のパッチが厳密に 0.5、周りは 0.16 と 0.84
  * illusion_hermann_grid         —— 全交点 = 帯 = 白 1.0、帯の幅 12 px・間隔 size px、黒マスは 0
  * illusion_scintillating_grid   —— 81 個の白丸の切り出しがビット一致、中心が 1.0、帯は 0.62
  * illusion_fraser_spiral        —— どの環も角度によらず半径が一定(渦なら 1 周で環の間隔ぶん増える)
  * illusion_kanizsa              —— 三角形の辺の上(円盤の外)は背景 0.97 の定数、勾配 0
  * illusion_ponzo                —— 上下の棒の塗りつぶし画素数が一致、bar を 50 減らすと両方ちょうど 50 減る
  * perpetual_harmonograph        —— 減衰 0・a/b = 3/2 なら周期 2π で閉じる(2 周目が 1 周目をなぞる)、√2 では閉じない
  * perpetual_langtons_ant        —— 独立に書いた蟻で、塗られたマスが「最後に黒」⊆ 塗り ⊆「一度でも黒」、
                                    1 万歩後の高速道路は周期 104 で (−2, −2)

    py -3.11 examples/gallery_illusion_invariants.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import illusion as IL  # noqa: E402
import perpetual as PP  # noqa: E402

ROWS: list = []


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def demo_brightness() -> None:
    size, n = 46, 8
    img = IL.illusion_checker_shadow(size=size, n=n, light=0.62, dark=0.31)
    (r1, c1), (r2, c2) = IL.CHECKER_PATCHES

    def patch(r, c):
        return img[r * size:(r + 1) * size, c * size:(c + 1) * size]

    a, b = patch(r1, c1), patch(r2, c2)
    flat = np.ptp(a) == 0 and np.ptp(b) == 0
    check("illusion_checker_shadow", f"マス {IL.CHECKER_PATCHES[0]} と {IL.CHECKER_PATCHES[1]}",
          "どちらも平坦で差が厳密に 0(= 0.31)", f"{a[0, 0, 0]!r} / {b[0, 0, 0]!r}、平坦 {flat}",
          flat and np.array_equal(a, b) and a[0, 0, 0] == 0.31)
    lo, li = patch(0, 0)[0, 0, 0], patch(4, 4)[0, 0, 0]
    check("illusion_checker_shadow", "明マス 影の外 (0,0) と 影の中 (4,4)", "0.62 と 0.62·(0.31/0.62) = 0.31(同じ明暗は一致しない)",
          f"{lo!r} / {li!r}", lo == 0.62 and abs(li - 0.31) < 1e-15)

    sc = IL.illusion_simultaneous_contrast(patch=90, size=320)
    h, w = sc.shape[:2]
    y = h // 2
    left, right = sc[y, w // 4], sc[y, 3 * w // 4]
    check("illusion_simultaneous_contrast", "左右のパッチの中心", "厳密に同じ 0.5", f"{left[0]!r} / {right[0]!r}",
          np.array_equal(left, right) and left[0] == 0.5)
    y0 = (h - 90) // 2
    pl = sc[y0:y0 + 90, w // 4 - 45:w // 4 + 45]
    pr = sc[y0:y0 + 90, 3 * w // 4 - 45:3 * w // 4 + 45]
    check("illusion_simultaneous_contrast", "パッチ全体と周り", "90×90 が全部 0.5、周りは 0.16 / 0.84",
          f"左右一致 {np.array_equal(pl, pr)}、周り {sc[5, 5, 0]} / {sc[5, w - 5, 0]}",
          np.array_equal(pl, pr) and np.all(pl == 0.5) and sc[5, 5, 0] == 0.16 and sc[5, w - 5, 0] == 0.84)

    s, n, bar = 44, 8, 12.0
    hg = IL.illusion_hermann_grid(size=s, n=n, bar=bar)
    cs = [k * s + s // 2 for k in range(n + 1)]
    inter = np.array([hg[cy, cx, 0] for cy in cs for cx in cs])
    band = hg[cs[0], cs[0] + s // 2, 0]
    holes = np.array([hg[cy + s // 2, cx + s // 2, 0] for cy in cs[:-1] for cx in cs[:-1]])
    row = hg[cs[0] + s // 2, :, 0]                       # 黒マスを横切る行
    runs = np.diff(np.flatnonzero(np.diff(np.r_[0, row, 0])))[::2]
    check("illusion_hermann_grid", "81 交点・帯・64 黒マス", "交点 = 帯 = 1.0、黒マス 0", f"交点 {set(inter.tolist())}、帯 {band}、黒 {set(holes.tolist())}",
          set(inter.tolist()) == {1.0} and band == 1.0 and set(holes.tolist()) == {0.0})
    starts = np.flatnonzero(np.diff(np.r_[0, row]) > 0)
    check("illusion_hermann_grid", "黒マスを横切る行の白い帯", f"幅 {int(bar)} px が {n + 1} 本、間隔 {s} px",
          f"幅 {sorted(set(runs.tolist()))}、本数 {len(runs)}、間隔 {sorted(set(np.diff(starts).tolist()))}",
          set(runs.tolist()) == {int(bar)} and len(runs) == n + 1 and set(np.diff(starts).tolist()) == {s})

    sg = IL.illusion_scintillating_grid(size=s, n=n, bar=bar, dot=6.0)
    half = 9
    pats = [sg[cy - half:cy + half, cx - half:cx + half] for cy in cs for cx in cs]
    same = all(np.array_equal(p, pats[0]) for p in pats)
    check("illusion_scintillating_grid", "81 個の白丸を 18×18 で切り出す", "全部ビット一致、中心 1.0",
          f"一致 {same}、中心 {pats[0][half, half, 0]}", same and pats[0][half, half, 0] == 1.0)
    # 下地は交点の帯の灰 0.62(半径 7.5 px の内側は十字の帯の中)→ 白丸の被覆率
    py_, px_ = np.mgrid[0:2 * half, 0:2 * half] + 0.5
    near = np.hypot(py_ - half, px_ - half) < 7.5
    cov = (pats[0][..., 0] - 0.62) / (1.0 - 0.62)
    area = float(cov[near].sum())
    check("illusion_scintillating_grid", "白丸の被覆率の総和(= 面積)と帯の灰", f"π·6² = {math.pi * 36:.2f} ± 0.5、帯 0.62",
          f"{area:.2f}、帯 {sg[cs[0], cs[0] + s // 2, 0]:.2f}", abs(area - math.pi * 36) < 0.5 and abs(sg[cs[0], cs[0] + s // 2, 0] - 0.62) < 1e-12)


def demo_geometry() -> None:
    size, rings = 520, 7
    fr = IL.illusion_fraser_spiral(rings=rings, tilt_deg=22.0, size=size)
    ink = np.abs(fr[..., 0] - 0.5)
    yy, xx = np.mgrid[0:size, 0:size] + 0.5
    rr = np.hypot(yy - size / 2, xx - size / 2)
    th = np.mod(np.arctan2(yy - size / 2, xx - size / 2), 2 * np.pi)
    sec = (th / (2 * np.pi) * 24).astype(int)
    spreads, offs = [], []
    for k in range(1, rings + 1):
        rk = size * 0.5 * k / (rings + 1)
        ring = np.abs(rr - rk) < 10
        means = [np.sum(rr[ring & (sec == j)] * ink[ring & (sec == j)]) / np.sum(ink[ring & (sec == j)]) for j in range(24)]
        spreads.append(np.ptp(means))
        offs.append(abs(np.mean(means) - rk))
    gap = size * 0.5 / (rings + 1)
    check("illusion_fraser_spiral", "各環の半径を 24 の角度ごとに測る",
          f"角度による振れ < 3 px(渦なら 1 周で {gap:.1f} px 振れる)、平均が真の半径 ±1 px",
          f"最大の振れ {max(spreads):.2f} px(線分の離散化)、真の半径との差 最大 {max(offs):.2f} px",
          max(spreads) < 3.0 and max(offs) < 1.0)

    size = 420
    kz = IL.illusion_kanizsa(radius=54.0, size=size)
    c, R = size * 0.5, size * 0.30
    pts = [(c - R, c), (c + R * 0.5, c - R * np.sqrt(3) / 2), (c + R * 0.5, c + R * np.sqrt(3) / 2)]
    vals = []
    for i in range(3):
        (ya, xa), (yb, xb) = pts[i], pts[(i + 1) % 3]
        for t in np.linspace(0, 1, 400):
            y, x = ya + t * (yb - ya), xa + t * (xb - xa)
            iy, ix = int(y), int(x)
            if min(math.hypot(iy + 0.5 - py, ix + 0.5 - px) for py, px in pts) > 54.0 + 2:
                vals.append(kz[iy - 1:iy + 2, ix - 1:ix + 2])
    v = np.array(vals)
    check("illusion_kanizsa", f"三角形の 3 辺の上で円盤の外 {len(vals)} 点の 3×3 近傍", "背景 0.97 の定数(勾配 0)",
          f"値 {sorted(set(np.round(v.ravel(), 15).tolist()))}", len(vals) > 300 and np.all(v == 0.97))
    disc = [kz[int(py - 30 * (c - py) / R), int(px - 30 * (c - px) / R), 0] for py, px in pts]
    check("illusion_kanizsa", "円盤の外向き側(三角形と反対)", "黒い円盤 0.12 が 3 つ", str(np.round(disc, 3).tolist()),
          np.allclose(disc, 0.12))

    def bar_pixels(img):
        out = []
        for cy in (90, 210):
            r = img[cy]
            out.append(int(np.sum((r[:, 0] == 0.85) & (r[:, 1] == 0.25) & (r[:, 2] == 0.2))))
        return out

    p150 = bar_pixels(IL.illusion_ponzo(bar=150.0))
    p100 = bar_pixels(IL.illusion_ponzo(bar=100.0))
    check("illusion_ponzo", "上下の棒の真ん中の行の塗りつぶし画素", "上 = 下(bar 150 + 端の丸み)",
          f"{p150}", p150[0] == p150[1] and 150 <= p150[0] <= 150 + 2 * 2.4 + 1)
    check("illusion_ponzo", "bar を 150 → 100", "上下ともちょうど 50 減る", f"{p100}(差 {[a - b for a, b in zip(p150, p100)]})",
          p100[0] == p100[1] and p150[0] - p100[0] == 50)


def langton(steps: int, size: int):
    """独立に書いたラングトンの蟻(上向きで出発、白で右・黒で左、盤は巻き戻し)。"""
    g = np.zeros((size, size), bool)
    ever = np.zeros_like(g)
    y = x = size // 2
    dy, dx = -1, 0
    trace = []
    for _ in range(steps):
        if g[y, x]:
            dy, dx = -dx, dy            # 左
            g[y, x] = False
        else:
            dy, dx = dx, -dy            # 右
            g[y, x] = True
            ever[y, x] = True
        y, x = (y + dy) % size, (x + dx) % size
        trace.append((y, x))
    return g, ever, trace


def demo_perpetual() -> None:
    def ink(img):
        return img[..., 0] < 0.97 - 0.02                 # 少しでも線が載った画素

    size = 200
    c2 = ink(PP.perpetual_harmonograph(size=size, a=3.0, b=2.0, phase=0.35, decay=0.0, turns=2))
    c4 = ink(PP.perpetual_harmonograph(size=size, a=3.0, b=2.0, phase=0.35, decay=0.0, turns=4))
    i2 = ink(PP.perpetual_harmonograph(size=size, a=3.0, b=2.0 * math.sqrt(2), phase=0.35, decay=0.0, turns=2))
    i4 = ink(PP.perpetual_harmonograph(size=size, a=3.0, b=2.0 * math.sqrt(2), phase=0.35, decay=0.0, turns=4))
    mis_c = np.sum(c2 ^ c4) / np.sum(c2 | c4)
    mis_i = np.sum(i2 ^ i4) / np.sum(i2 | i4)
    check("perpetual_harmonograph", "減衰 0、t ∈ [0, 2π] と [0, 4π] の線の画素", "a/b = 3/2 は周期 2π で閉じる → ほぼ同じ線、√2 倍は 2 周目が新しい線",
          f"食い違い 3/2: {mis_c:.3f}、無理数比: {mis_i:.3f}", mis_c < 0.1 and mis_i > 0.3)
    ys, xs = np.nonzero(c4)
    lo, hi = 0.5 * size - 0.4 * size, 0.5 * size + 0.4 * size
    check("perpetual_harmonograph", "線の外接箱(振幅 0.4·size)", f"[{lo:.0f}, {hi:.0f}] の内側 ±2 px",
          f"y [{ys.min()}, {ys.max()}]、x [{xs.min()}, {xs.max()}]",
          ys.min() >= lo - 2 and ys.max() <= hi + 2 and xs.min() >= lo - 2 and xs.max() <= hi + 2)

    steps, n = 12_000, 301
    fin, ever, trace = langton(steps, n)
    out = PP.perpetual_langtons_ant(steps=steps, size=n)
    bg = out[0, 0]
    painted_full = np.any(out != bg, axis=-1)
    # 最近傍の拡大を戻す: 塗りの境目から拡大率 k を読み、k 画素おきに標本
    ys, xs = np.nonzero(fin | ever)
    k = max(n // out.shape[0], 1)
    for kk in range(1, 6):
        if out.shape[0] % kk == 0 and np.array_equal(np.repeat(np.repeat(painted_full[::kk, ::kk], kk, 0), kk, 1), painted_full):
            k = kk
    painted = painted_full[::k, ::k]
    py, px = np.nonzero(painted)
    oy, ox = py.min() - ys.min(), px.min() - xs.min()   # 盤 → 絵の平行移動(外接箱の左上で合わせる)

    def on_canvas(mask):
        yy, xx = np.nonzero(mask)
        yy, xx = yy + oy, xx + ox
        inside = (yy >= 0) & (yy < painted.shape[0]) & (xx >= 0) & (xx < painted.shape[1])
        return inside.all(), painted[yy[inside], xx[inside]]

    in_f, pf = on_canvas(fin)
    in_e, _ = on_canvas(ever)
    e_canvas = np.zeros_like(painted)
    yy, xx = np.nonzero(ever)
    e_canvas[yy + oy, xx + ox] = True
    check("perpetual_langtons_ant", f"{steps} 歩、独立に書いた蟻と照合(拡大 {k} 倍を戻す)", "最後に黒 ⊆ 塗り ⊆ 一度でも黒",
          f"最後に黒 {int(fin.sum())} のうち塗り {int(pf.sum())}、塗り {int(painted.sum())} のうち一度でも黒の外 {int((painted & ~e_canvas).sum())}",
          in_f and in_e and pf.all() and not (painted & ~e_canvas).any())
    T = PP.LANGTON_HIGHWAY_PERIOD
    disp = [(trace[i + T][0] - trace[i][0], trace[i + T][1] - trace[i][1]) for i in (10_500, 11_000, 11_500)]
    # ★docstring は (−2, −2) と書くが、この盤(行・列、上向きで出発・白で右)では (+2, −2)。
    #   定理が言うのは「周期 104 で同じ斜めの 2 マス」で、符号は回転の規約で変わる(perpetual.py の自己検査と同じ読み)。
    check("perpetual_langtons_ant", "高速道路の周期(1 万歩より後の 3 か所)", f"{T} 歩ごとに同じ斜め (行 +2, 列 −2)", str(disp),
          all(d == (2, -2) for d in disp))


def main() -> int:
    t0 = time.time()
    demo_brightness()
    demo_geometry()
    demo_perpetual()
    w_op = max(len(r[0]) for r in ROWS)
    print(f"{'op':<{w_op}} | 確かめたこと | 期待 | 出た値 | 判定")
    for op, what, exp, got, ok in ROWS:
        print(f"{op:<{w_op}} | {what} | {exp} | {got} | {'合格' if ok else '★不合格'}")
    bad = [r for r in ROWS if not r[4]]
    if bad:
        print(f"FAIL: {len(bad)}/{len(ROWS)} 行が外れた({', '.join(sorted({r[0] for r in bad}))})")
        return 1
    print(f"PASS: {len({r[0] for r in ROWS})} op を {len(ROWS)} 行の真値で確認({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
