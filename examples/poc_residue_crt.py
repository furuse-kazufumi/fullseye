# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""1 つずつでは決まらない角度と変位を、周期の違う位相を束ねて決める —— 中国剰余定理を画像に。

    py -3.11 examples/poc_residue_crt.py

位相は量を**周期を法として**しか教えない。4 つ穴の部品の向きは 90° ごとに区別できず、
波長 9 px の縞の位相は 9 px ごとにしか変位を区別できない。ところが周期どうしに公約数が
無ければ、剰余の組は最小公倍数の範囲で値を 1 つに決める(中国剰余定理)。Ozaki scheme II
が INT8 の行列積の剰余から FP64 の積を正確に組み直すのと同じ算術である。
:mod:`residue` の 5 op をこの PoC で採点する。

この PoC が測る主張は 3 つ:

1. **定理そのもの**(第 1 章): 整数の CRT(Garner の混合基数)は 0..692 の全数で総当たりと
   一致し、実数版の重み付き CRT は整数入力で整数版と 1 ビットも違わない。冗長な周期を 1 本
   足すと、**どの帯域が壊れたか**を言い当てる —— 言い当てられないときは「判定不能」と返し、
   取り違え(別の帯域を犯人にする)は 0 件。
2. **3 回・4 回・5 回対称の輪を組んだ部品の向きが 360° で一意に決まる**(第 2 章)。
   どの輪も単独では 120° / 90° / 72° ごとに曖昧。輪の 1 つを 40 % 汚しても角度は 1° 以内、
   残差が最大の輪が汚れた輪を指す。
3. **2 つの領域が別々に 20〜30 px 動く実写テクスチャ**で、波長 5/7/9/11/13/16 px の帯域の
   位相から局所変位を求める(第 3 章)。1 帯域の位相法は波長の半分(8 px)で必ず折り返し、
   ピラミッド型 Lucas-Kanade(3〜6 段の最良)は境界から遠い画素の半分前後で 1 px 以上外し、
   大域の位相相関は片方の変位しか返さない。**どこで壊れるかも同じ表に出す**: 変位が窓の中で
   変わる場、境界から 1.5 σ 以内、平坦な領域の多い写真(camera)。

素材: 第 2 章は解析的に描いた部品(角度が真値)、第 3 章は scikit-image 同梱の公開画像
(grass / gravel / camera / brick)を厳密なサブピクセル巡回シフト(フーリエ位相の掛け算)で
動かしたもの。scikit-image が無ければ第 3 章を飛ばし、その旨を印字する。
"""
from __future__ import annotations

import sys
from math import gcd
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import examplefig as figs  # noqa: E402
import residue as R  # noqa: E402

N = 161                     # 部品画像の一辺 [px]
C = (N - 1) / 2.0
ORDERS = (3, 4, 5)          # 輪ごとの対称の回数
RINGS = ((14, 24), (30, 40), (46, 56))


# --------------------------------------------------------------------------- #
# 第 1 章: 定理                                                                #
# --------------------------------------------------------------------------- #
def chapter_theorem(rng):
    print("== 第 1 章: 定理そのもの ==")
    m = [7, 9, 11]
    for v in range(693):
        assert R.residue_integer_crt([v % x for x in m], m)["value"] == v
    vs = np.arange(693)
    out = R.residue_crt((vs[None] % np.array(m)[:, None]).astype(float), m)
    assert np.array_equal(out["value"], vs.astype(float))
    print("整数 CRT(Garner)= 総当たり、0..692 の 693 件すべて。実数版も整数入力で完全一致。")
    big = [101, 103, 107, 109, 113, 127, 131, 137]
    P = 1
    for x in big:
        P *= x
    v = P - 12345
    assert R.residue_integer_crt([v % x for x in big], big)["value"] == v
    print("法 8 本(積 %d 桁)でも任意精度で厳密: Ozaki scheme II が FP64 を組み直すのと同じ算術。" % len(str(P)))

    # 冗長な周期で犯人探し(RRNS)
    p4 = np.array([7.0, 9.0, 11.0, 13.0])
    n = 3000
    true = rng.uniform(-40, 40, n)
    res = (true[None] + rng.normal(0, 0.1, (4, n))) % p4[:, None]
    bad = rng.integers(0, 4, n)
    res[bad, np.arange(n)] = (res[bad, np.arange(n)] + rng.uniform(0.3, 0.7, n) * p4[bad]) % p4[bad]
    fl = R.residue_fault_locate(res, p4, lo=-40, hi=40)
    right = float((fl["faulty"] == bad).mean())
    undecided = float((fl["faulty"] == -2).mean())
    wrong = float(((fl["faulty"] >= 0) & (fl["faulty"] != bad)).mean())
    located = fl["faulty"] == bad
    err = float(np.abs(fl["value"][located] - true[located]).max())
    print("4 帯域のうち 1 本を壊した %d 件: 犯人を当てた %.1f %% / 判定不能 %.1f %% / 取り違え %.2f %%"
          "(当てた件の値の誤差は最大 %.3f)" % (n, 100 * right, 100 * undecided, 100 * wrong, err))
    assert wrong <= 0.002, "RRNS は取り違えてはいけない"
    assert right > 0.8
    return {"rrns_right": right, "rrns_undecided": undecided, "rrns_wrong": wrong}


# --------------------------------------------------------------------------- #
# 第 2 章: 360° の向き                                                          #
# --------------------------------------------------------------------------- #
def render_part(theta_ccw_deg, ss=4):
    """3 枚羽根(内)・4 つ穴の輪(中)・5 つ溝の輪(外)の部品を、画面上で反時計回りに
    theta 回した姿で**解析的に**描く(4x4 超標本化、補間なし = 角度が真値)。"""
    th = np.radians(theta_ccw_deg)
    g = (np.arange(N * ss) + 0.5) / ss - 0.5
    X, Y = np.meshgrid(g - C, g - C)
    r = np.hypot(X, Y)
    a = np.arctan2(-Y, X) - th            # 行は下向きなので -Y で数学の向きに
    img = ((r > 14) & (r < 24) & (np.cos(3 * a) > 0.3)).astype(float)
    ring = (r > 30) & (r < 40)
    holes = np.zeros_like(r, bool)
    for k in range(4):
        ca = a - 2 * np.pi * k / 4
        holes |= np.hypot(r * np.cos(ca) - 35.0, r * np.sin(ca)) < 4.0
    img += (ring & ~holes).astype(float)
    img += ((r > 46) & (r < 56) & (np.cos(5 * a) < 0.6)).astype(float)
    return img.reshape(N, ss, N, ss).mean((1, 3))


def smudge(img, ring_idx, angle, rng):
    yy, xx = np.mgrid[0:N, 0:N]
    r = np.hypot(xx - C, yy - C)
    a = np.arctan2(-(yy - C), xx - C)
    r0, r1 = RINGS[ring_idx]
    blob = (r > r0 - 2) & (r < r1 + 2) & (np.cos(a - angle) > 0.2)      # 輪の約 4 割
    return np.where(blob, 0.5, img)


def _angle_err(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def chapter_rotation(rng):
    print("\n== 第 2 章: 3・4・5 回対称の輪で向きを 360° 決める ==")
    ref = render_part(0.0)
    truth = np.linspace(0.0, 360.0, 73)[:-1] + 1.7
    est, single = [], {n: [] for n in ORDERS}
    for t in truth:
        o = R.harmonic_rotation(render_part(t) + rng.normal(0, 0.03, (N, N)), ref,
                                orders=ORDERS, rings=RINGS)
        est.append(o["angle_deg"])
        for n, pd in zip(ORDERS, o["per_order_deg"]):
            single[n].append(pd)
    est = np.array(est)
    errs = np.array([_angle_err(e, t) for e, t in zip(est, truth)])
    print("真値 72 角度(雑音 σ=0.03): 最大誤差 %.3f° / 中央値 %.4f°" % (errs.max(), np.median(errs)))
    for n in ORDERS:
        s = np.array(single[n])
        amb = np.array([_angle_err(x, t) for x, t in zip(s, truth)])
        print("  %d 回対称の輪だけ: 角度は 360/%d = %.0f° を法としてしか分からない(真値との差の最大 %.0f°)"
              % (n, n, 360.0 / n, amb.max()))
    assert errs.max() < 0.5

    hit, smax, total = 0, 0.0, 0
    for k in range(30):
        t = rng.uniform(0, 360)
        ring = int(rng.integers(0, 3))
        img = smudge(render_part(t), ring, rng.uniform(0, 2 * np.pi), rng)
        o = R.harmonic_rotation(img, ref, orders=ORDERS, rings=RINGS)
        rel = np.abs(o["residual_deg"]) / (360.0 / np.array(ORDERS))
        hit += int(np.argmax(rel) == ring)
        smax = max(smax, _angle_err(o["angle_deg"], t))
        total += 1
    print("輪の 1 つを約 4 割汚した %d 件: 角度の誤差は最大 %.2f°、残差が最大の輪 = 汚れた輪 %d/%d"
          % (total, smax, hit, total))
    assert smax < 2.0 and hit >= 0.7 * total

    # 図: 実物 / 各輪だけの答え(のこぎり歯)と CRT の答え / 動く図
    t_show = 137.0
    img_show = render_part(t_show)
    img_dirty = smudge(img_show, 2, 1.0, rng)
    figs.save_grid("residue_part", [ref, img_show, img_dirty],
                   ["基準の姿(0°)", "%.0f° 回した姿" % t_show, "外の輪を汚した姿"],
                   title="3 枚羽根・4 つ穴・5 つ溝 —— どれも単独では向きが決まらない", ncols=3, gray=True)
    series = [("CRT(3 輪を束ねる)", truth, est)]
    for n in ORDERS:
        series.append(("%d 回対称の輪だけ" % n, truth, np.array(single[n])))
    figs.save_plot("residue_rotation_sawtooth", series, xlabel="真の角度 [°]", ylabel="推定した角度 [°]",
                   title="単独の輪は 120°/90°/72° で折り返す。束ねると対角線 1 本になる",
                   caption="真値は解析的に描いた角度。のこぎり歯 = 剰余、対角線 = 中国剰余定理で戻した値。",
                   xlim=(0, 360), ylim=(0, 360))
    frames = []
    for t in np.linspace(0, 360, 37)[:-1]:
        im = render_part(t)
        o = R.harmonic_rotation(im, ref, orders=ORDERS, rings=RINGS)
        view = np.repeat(im[..., None], 3, axis=2) * 0.8
        a = np.radians(o["angle_deg"])
        for rr in np.linspace(0, 70, 140):           # 推定した向きの針(橙)
            y = int(round(C - rr * np.sin(a)))
            x = int(round(C + rr * np.cos(a)))
            if 0 <= y < N and 0 <= x < N:
                view[y, x] = (1.0, 0.5, 0.0)
        frames.append(view)
    figs.save_gif("residue_rotation_needle", frames, caption="針 = CRT で決めた向き(1 フレームごとに独立に推定)", fps=6)
    return {"rot_max_err": float(errs.max()), "smudge_max_err": smax, "smudge_hit": hit / total}


# --------------------------------------------------------------------------- #
# 第 3 章: 2 つの領域が別々に大きく動く                                          #
# --------------------------------------------------------------------------- #
def _fshift(img, d):
    F = np.fft.fft2(img)
    fu = np.fft.fftfreq(img.shape[1])[None, :]
    return np.real(np.fft.ifft2(F * np.exp(-2j * np.pi * fu * d)))


def chapter_displacement():
    print("\n== 第 3 章: 実写テクスチャの 2 領域が別々に 20〜30 px 動く ==")
    try:
        from skimage import data
    except ImportError:
        print("[skip] scikit-image が無いので第 3 章は飛ばす(pip install scikit-image)")
        return {}
    from flow import optical_flow_lk
    from filters_freq import phase_correlation_fft

    rows = []
    shown = None
    for name in ("grass", "gravel", "camera", "brick"):
        img = getattr(data, name)().astype(float)
        if img.ndim == 3:
            img = img.mean(2)
        img = img[:256, :384]
        img = (img - img.mean()) / img.std()
        cols = np.arange(img.shape[1])[None, :]
        for d1, d2 in ((20.0, -15.0), (30.0, 12.0)):
            b = np.where(cols < 192, _fshift(img, d1), _fshift(img, d2))
            D = np.where(cols < 192, d1, d2) * np.ones(img.shape)
            m = np.zeros(img.shape, bool)
            m[40:-40, 40:-40] = True
            far = m & (np.abs(cols - 192) > 60)
            near = m & ~far
            o = R.crt_displacement(img, b)
            e = np.abs(o["d"] - D)
            lk = 1.0
            lk_u = None
            for lv in (3, 4, 5, 6):
                u, _ = optical_flow_lk(img.astype(np.float32), b.astype(np.float32), window=21, levels=lv)
                f = float((np.abs(u - D)[far] > 1).mean())
                if f < lk:
                    lk, lk_u = f, u
            # 1 帯域の位相法の**理想**(雑音ゼロでも): 波長 16 px なら真値を ±8 px に折り返した値しか出ない
            single = R._wrap_signed(D, 16.0)
            pc = phase_correlation_fft(img, b)
            rows.append((name, d1, d2, float((e[far] > 1).mean()), float((e[near] > 1).mean()), lk,
                         float((np.abs(single - D)[far] > 1).mean()), float(pc["col_shift"])))
            if name == "grass" and d1 == 20.0:
                shown = (img, b, D, o["d"], lk_u)
    print("1 px 以上外した画素の割合(境界から 60 px 以上離れた画素 / 境界の近く)")
    print("  素材    動き(左/右)   CRT 遠   CRT 近   LK最良 遠   1帯域(理想)  大域位相相関")
    for name, d1, d2, cf, cn, lk, s1, pc in rows:
        print("  %-7s %+5.1f/%+5.1f   %5.1f%%   %5.1f%%   %6.1f%%   %6.1f%%   %+6.1f px(1 つだけ)"
              % (name, d1, d2, 100 * cf, 100 * cn, 100 * lk, 100 * s1, -pc))
    good = [r for r in rows if r[0] in ("grass", "gravel")]
    assert all(r[3] < r[5] for r in good), "CRT はテクスチャのある 2 領域で LK に勝つはず"
    assert all(r[3] < 0.2 for r in good)

    # 壊れる場所: 窓の中で変位が変わる場
    from scipy.ndimage import map_coordinates
    img = data.grass().astype(float)[:256, :256]
    img = (img - img.mean()) / img.std()
    yy, xx = np.mgrid[0:256, 0:256].astype(float)
    Dv = 6.0 * np.sin(2 * np.pi * yy / 512 + 0.4)
    bv = map_coordinates(img, [yy, xx - Dv], order=5, mode="grid-wrap")
    ov = R.crt_displacement(img, bv)
    m = np.zeros(img.shape, bool)
    m[40:-40, 40:-40] = True
    fv = float((np.abs(ov["d"] - Dv)[m] > 1).mean())
    print("壊れる場所: 窓(σ=40 px)の中で変位が変わる場(振幅 6 px、勾配 ≤ 0.07)で CRT は %.0f %% を外す"
          "—— 局所周波数を安定させる狭い帯域と、場に追従する狭い窓は両立しない(不確定性)。" % (100 * fv))
    if shown is not None:
        img, b, D, d, u = shown

        def _same_scale(v, lim=25.0):
            # 3 枚の変位を同じ色尺度で見せる: ±lim に切り、角の 2 画素に ±lim を置いて尺度を固定
            v = np.clip(np.array(v, float), -lim, lim)
            v[0, 0], v[0, 1] = lim, -lim
            return v

        figs.save_grid("residue_two_regions", [img, _same_scale(D), _same_scale(d), _same_scale(u)],
                       ["grass(公開画像)", "真の変位(左 +20 / 右 -15 px)", "CRT(帯域 6 本)", "ピラミッド LK(最良の段数)"],
                       title="2 つの領域が別々に大きく動く", ncols=4, signed=[False, True, True, True])
    figs.save_table("residue_displacement_table",
                    ["素材", "動き", "CRT 遠", "CRT 近", "LK 最良", "1 帯域", "位相相関"],
                    [[n, "%+.0f/%+.0f" % (a, b_), "%.1f%%" % (100 * cf), "%.1f%%" % (100 * cn),
                      "%.1f%%" % (100 * lk), "%.1f%%" % (100 * s1), "%+.0f px" % -pc]
                     for n, a, b_, cf, cn, lk, s1, pc in rows],
                    title="1 px 以上外した画素の割合", caption="遠 = 境界から 60 px 以上。位相相関は大域なので値 1 つ。")
    return {"rows": rows, "varying_field_fail": fv}


def main():
    rng = np.random.default_rng(20261006)
    assert gcd(gcd(*ORDERS[:2]), ORDERS[2]) == 1
    t = chapter_theorem(rng)
    r = chapter_rotation(rng)
    d = chapter_displacement()
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    msg = ("PASS: 定理(整数 CRT 693/693、RRNS 取り違え %.2f %%)/ 向き 360° を最大誤差 %.2f°(汚れ 4 割で %.2f°)"
           % (100 * t["rrns_wrong"], r["rot_max_err"], r["smudge_max_err"]))
    if d:
        g = [row for row in d["rows"] if row[0] == "grass"]
        msg += " / 2 領域の大変位: grass で CRT %.1f %% vs LK %.1f %%" % (100 * g[0][3], 100 * g[0][5])
    print("\n" + msg + "。")


if __name__ == "__main__":
    main()
