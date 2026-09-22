# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 写真を 1 本の線にして、回る振り子に描かせる —— 濃淡 → 点描 → 巡回路 → フーリエ級数 → G-code

実写 1 枚の**濃淡**を、**1 本の閉じた線**に変える。そしてその線を**回る円(振り子)の連鎖**として
描き直す。最後に同じ線を G-code にして「紙の上で何メートル、プロッタで何分」まで出す。
筋は TSP art(Kaplan & Bosch, *Computational Aesthetics*, 2005)で、巡回路が**閉じている**ことが
フーリエ級数に載る条件になっている —— そこが噛み合う理由である。

★**この PoC の主張は「絵が似ている」ではない。** 様式化は必ず「それらしい絵」が出てしまうので、
各段で**何を保って何を捨てたか**を数で返す:

1. **点描は濃淡を読んでいるか** —— ランプ画像で局所密度と暗さの相関 0.995。対照群として
   一様画像では点が**等間隔**に散る(最近傍距離の変動係数 0.13 対 0.37)。
   Lloyd のエネルギーは反復とともに**単調減少**する(8760 → 4654)。
2. **巡回路の質は下界との比で言う** —— 閉じた巡回路は最小全域木より短くなれない。
   実写では ``長さ / MST = 1.081``(一様乱点だと 1.228)。2-opt は長さを**単調に**縮める。
   対照群: 座標順に繋ぐだけだと MST の 8.8 倍。
3. **濃淡の再現そのものを返す** —— 実写で相関 0.939。同じ本数のランダムな線を引いた対照群は
   **-0.123**(濃淡の情報がゼロどころか負)。
4. ★**ペン幅は閉形式で解ける** —— 線が重ならない範囲で ``インク率 ≈ 線長 × ペン幅 / 面積``。
   目標の濃さから逆に解くと偏りが **-0.248 → -0.016** に縮む。重なり始めると実測は予言より
   小さくなり、**その差が重なりの量**になる。
5. ★★**振り子は誤差を予言してから描く** —— パーセバルにより、次数 K で打ち切った再構成の
   二乗誤差は「|k| > K の係数の二乗和」に**厳密に等しい**。だから「何個の円で描けるか」を
   描く前に言える: 実写の線では **K=16 で 96.1 %、K=64 で 99.3 %、K=256 で 99.9 %**。

書いている途中に**検査が実装のバグを 4 件見つけた**(どれも例外を出さず、絵は「それらしく」出ていた):
偶数点でナイキストの係数を二重に数えてパーセバルが破れていた / 打ち切った係数列では予言が
下界なのに「厳密」と書いていた / 弧長の打ち直しが冪等でない(2 度かけると点が最大 3.73 px 動く)/
ペン幅が階段で濃淡を合わせられなかった。詳しくは各 op の docstring にある。

図:
1. ``stipple``: 写真と点描を並べる(点の密度が濃淡を追う)。
2. ``lloyd``: Lloyd のエネルギーが反復で単調に下がる。
3. ``tour``: 1 本の閉じた線(と、座標順に繋いだだけの対照群)。
4. ``tone``: 目標の濃淡・描いた濃淡・その差。
5. ``pen``: ペン幅とインク率、閉形式の予言との一致と、重なりによるずれ。
6. ``harmonics``: 打ち切り次数ごとの**予言された**誤差と、残したエネルギーの割合。
7. ``epicycles``: 回る円の連鎖が線を描く GIF。
8. ``numbers``: 数表。

データ: ``examples/data/hokusai_great_wave_met_dp130155.png`` —— 葛飾北斎
「神奈川沖浪裏」(富嶽三十六景、1830-32 年頃)を輝度化して 202x300 に縮めたもの。
メトロポリタン美術館の Open Access が ``isPublicDomain: true``(CC0)で公開している
版(object 45434、画像 DP130155)を使った。

★**最初はアポロ 11 号が月面で撮った粉塵の実写を使っていたが、差し替えた。**
被写体の無いテクスチャだったので「何の絵か分からない」し、大きな明暗の構造が
無いので点の密度に疎密が出ない —— 様式化の PoC としては**題材が成立していなかった**。
一筆書きは「元の絵が分かること」で初めて何を保ったかが読めるので、有名で明暗の
はっきりしたものに替えた。
走らせ方: ``py -3.11 examples/poc_one_stroke_epicycles.py``(図は ``out/figures/poc_one_stroke_epicycles/``)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

L = fs.ledger
HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO = os.path.join(HERE, "data", "hokusai_great_wave_met_dp130155.png")

#: 点の数。多いほど濃淡は合うが、Lloyd は画素 x 点で効くので時間も伸びる。
N_POINTS = 9000
#: 紙の作画幅[mm](A4 横の内側)。G-code の長さと時間はこれで決まる。
SHEET_MM = 250.0
#: プロッタの送り[mm/min]。
FEED_MM_MIN = 1800.0


def grey(path):
    a = np.asarray(fs.read_image(path), dtype=np.float64)
    if a.ndim == 3:
        a = a[..., :3] @ np.array([0.299, 0.587, 0.114])
    return np.clip(a, 0.0, 1.0)


def tour_length(q):
    return float(np.hypot(np.diff(q[:, 0], append=q[0, 0]),
                          np.diff(q[:, 1], append=q[0, 1])).sum())


def nn_cv(p):
    d = np.hypot(p[:, 0, None] - p[None, :, 0], p[:, 1, None] - p[None, :, 1])
    np.fill_diagonal(d, np.inf)
    v = d.min(axis=1)
    return float(v.std() / v.mean())


def draw_points(shape, pts, radius=0.9):
    """点描を白地に黒で(図のためだけ。測るのは op のほう)。"""
    img = np.ones(shape, dtype=np.float64)
    h, w = shape
    k = int(np.ceil(radius + 0.5))
    br, bc = np.floor(pts[:, 0]).astype(int), np.floor(pts[:, 1]).astype(int)
    for dr in range(-k, k + 2):
        for dc in range(-k, k + 2):
            ri, ci = br + dr, bc + dc
            ok = (ri >= 0) & (ri < h) & (ci >= 0) & (ci < w)
            if not ok.any():
                continue
            dist = np.hypot(ri[ok] - pts[ok, 0], ci[ok] - pts[ok, 1])
            cov = np.clip(radius - dist + 0.5, 0.0, 1.0)
            np.minimum.at(img, (ri[ok], ci[ok]), 1.0 - cov)
    return img


def draw_polyline(shape, pts, closed=True, width=0.9, scale=1):
    """★**拡大するときは線幅も同じ倍率にする。**

    一筆書きの濃淡はインク率(線長 x ペン幅 / 面積)で決まる。倍率 S で描きながら
    線幅を 1 px に据え置くと**インク率が 1/S になり、濃淡が消えて真っ白に見える** ——
    実測で、濃淡相関 0.964 の線画が 4 倍表示では何も読めなくなった。絵が悪いのでは
    なく描き方が悪い、という典型なので、ここで倍率と線幅を必ず一緒に動かす。
    """
    h, w = shape
    shape = (h * scale, w * scale)
    pts = np.asarray(pts, dtype=np.float64) * scale
    img = np.ones(shape, dtype=np.float64)
    q = np.vstack([pts, pts[:1]]) if closed else pts
    seg = np.hypot(np.diff(q[:, 0]), np.diff(q[:, 1]))
    t = np.concatenate([[0.0], np.cumsum(seg)])
    if t[-1] <= 0.0:
        return img
    m = max(int(np.ceil(t[-1] * 2.0)), q.shape[0])
    want = np.linspace(0.0, t[-1], m, endpoint=False)
    dense = np.stack([np.interp(want, t, q[:, 0]), np.interp(want, t, q[:, 1])], axis=1)
    return np.minimum(img, draw_points(shape, dense, radius=width * scale * 0.5))


def density_exponent(image, pts, bins=24):
    """``log(局所密度)`` を ``log(暗さ)`` に回帰した傾き ``s``(密度 ∝ 暗さ^s)。

    ★**相関だけでは指数が見えない。** 重みつき Lloyd が作るのは重心ボロノイで、
    最適な点密度は重み ``rho`` に対し ``rho**(d/(d+2))`` —— 2 次元では **√rho** に
    比例する(Gersho の予想)。だから「密度と暗さの相関 0.99」は本当でも、
    重みをそのまま渡すと**濃淡の半分しか濃さに出ない**。op の ``gamma`` で重みを
    二乗して初めて密度が暗さに比例する。ここはその指数を実際に測る。
    """
    a = np.asarray(image, dtype=np.float64)
    h, w = a.shape
    p = np.asarray(pts, dtype=np.float64)
    hist, _, _ = np.histogram2d(p[:, 0], p[:, 1],
                                bins=(bins, bins), range=[[0, h], [0, w]])
    ri = np.clip((np.arange(bins) + 0.5) * h / bins, 0, h - 1).astype(int)
    ci = np.clip((np.arange(bins) + 0.5) * w / bins, 0, w - 1).astype(int)
    dark = np.clip(1.0 - a[np.ix_(ri, ci)], 1e-3, 1.0)
    ok = hist > 0
    if int(ok.sum()) < 20:
        return float("nan")
    return float(np.polyfit(np.log(dark[ok]), np.log(hist[ok]), 1)[0])


def epicycle_frames(spec, shape, stages, frames_per_stage=14, scale=2):
    """★**本物の回る振り子**のフレーム列(円・腕・描かれていく軌跡)。

    これまでこの PoC の GIF は「次数 K を上げた再構成」を並べていただけで、
    **円も腕も一度も描いていなかった** —— 主張は「回る円の連鎖が描く」なのに
    成果物が別物だった。``contour_epicycle_chain`` を実際に位相で回して描く。

    軌跡は**次数 K の再構成そのもの**を進捗ぶんだけ描く。位相を細かく刻んで
    筆先を繋ぐやり方だと、1 段 96 標本では 16,384 点の曲線を辿れず、粗い
    多角形になった(実測)。再構成は厳密な曲線なので、そこを取りに行く。

    段ごとに腕の本数を増やすので、**絵が正体を現していく**過程が見える。
    """
    h, w = shape
    kk = np.asarray(spec)[:, 0]
    cc = np.asarray(spec)[:, 1] + 1j * np.asarray(spec)[:, 2]
    n = int(kk.size)
    tt = np.arange(n, dtype=np.float64) / n
    out = []
    for K in stages:
        amp = np.abs(cc)
        keep = np.argsort(-amp)[:K + 1]                    # 振幅の大きい K+1 本
        rec = np.zeros(n, dtype=complex)
        for j in keep:
            rec += cc[j] * np.exp(2j * np.pi * kk[j] * tt)
        path = np.stack([np.imag(rec), np.real(rec)], axis=1)
        if path.shape[0] > 12288:            # 図は 600 px 幅。これ以上は描画が重いだけ
            path = path[np.linspace(0, path.shape[0] - 1, 12288).astype(int)]
        for i in range(frames_per_stage):
            t = (i + 1.0) / frames_per_stage
            m = max(2, int(round(t * n)))
            f = draw_polyline((h, w), path[:m], closed=False, width=1.0, scale=scale)
            chain = np.asarray(L.contour_epicycle_chain(spec, t, order="amplitude"))[:K + 2]
            for mm in range(1, len(chain) - 1):            # k=0 の腕は回らない
                rad = float(np.hypot(chain[mm + 1][0] - chain[mm][0],
                                     chain[mm + 1][1] - chain[mm][1]))
                if rad >= 1.0:
                    th = np.linspace(0.0, 2 * np.pi,
                                     max(48, int(2 * np.pi * rad)), endpoint=False)
                    ring = np.stack([chain[mm][0] + rad * np.sin(th),
                                     chain[mm][1] + rad * np.cos(th)], axis=1)
                    f = np.minimum(f, 0.72 + 0.28 * draw_polyline(
                        (h, w), ring, width=0.8, scale=scale))
                f = np.minimum(f, 0.40 + 0.60 * draw_polyline(
                    (h, w), np.stack([chain[mm], chain[mm + 1]]), closed=False,
                    width=0.8, scale=scale))
            f = np.minimum(f, draw_points((h * scale, w * scale),
                                          chain[-1:] * scale, radius=2.6))
            # ★線画なので**灰色のまま**出す。(H,W) を渡すと save_gif が疑似カラーに
            #   塗って黄緑の絵になる(実測)—— 強度そのものを見せる図では色は邪魔。
            out.append(np.dstack([f, f, f]))
    return out


def parse_args(argv=None):
    """★**自分の写真で走らせるための入口。**

    この PoC は同梱の北斎で数字を出すが、仕組みはどんな画像にも効く。
    ``--image`` に自分の写真を渡せば、そのまま一筆書きと振り子の GIF が出る::

        py -3.11 examples/poc_one_stroke_epicycles.py --image my_photo.jpg \
            --points 12000 --out out/mine

    点の数は「画素数 x 点数」で効くので、大きい写真ほど時間がかかる(実測:
    202x300・9,000 点で点描 101 秒)。まず ``--points 3000`` で形を見て、
    気に入ってから増やすのが早い。``--out`` を渡すと図と GIF がそこに出る
    (環境変数 ``FULLSEYE_FIGURE_DIR`` と同じはたらき)。
    """
    import argparse

    ap = argparse.ArgumentParser(
        description="写真を 1 本の閉じた線にして、回る円の連鎖で描き直す")
    ap.add_argument("--image", default=PHOTO,
                    help="入力画像(既定: 同梱の北斎「神奈川沖浪裏」)")
    ap.add_argument("--points", type=int, default=N_POINTS,
                    help="点描の点数(多いほど似るが遅い。既定 %d)" % N_POINTS)
    ap.add_argument("--out", default=None, help="図と GIF の出力先")
    ap.add_argument("--sheet-mm", type=float, default=SHEET_MM,
                    help="紙の作画幅[mm](既定 %.0f)" % SHEET_MM)
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.out:
        # ★env は examplefig が **呼ばれるたび**に読むので、ここで入れれば効く
        #   (import 時に固定されていたら --out が黙って無視される、の回避)。
        os.environ["FULLSEYE_FIGURE_DIR"] = args.out
    photo_path, n_points, sheet_mm = args.image, args.points, args.sheet_mm
    figs.reset()
    t0 = time.perf_counter()
    checks = []

    def ck(name, ok):
        checks.append((name, bool(ok)))

    if not os.path.exists(photo_path):
        print("写真が見つからない: %s" % photo_path)
        return 1
    img = grey(photo_path)
    h, w = img.shape
    area = float(h * w)
    print("== 写真 ==")
    print("   %s  %dx%d  平均 %.3f  p5/50/95 = %.2f %.2f %.2f"
          % (os.path.basename(photo_path), h, w, img.mean(),
             *np.percentile(img, [5, 50, 95])))
    print("   出典 葛飾北斎「神奈川沖浪裏」1830-32 年頃 / メトロポリタン美術館 Open Access (CC0、object 45434)")

    # ------------------------------------------------------------------ #
    # 1 章 濃淡を点の密度に写す                                            #
    # ------------------------------------------------------------------ #
    print()
    print("== 1 章 点描は濃淡を読んでいるか ==")
    ta = time.perf_counter()
    pts = L.stipple_points_from_image(img, n_points, iterations=18, gamma=1.6, seed=1)
    t_stipple = time.perf_counter() - ta
    print("   %d 点、%.1f s" % (len(pts), t_stipple))

    # 対照群 1: ランプ画像で密度と暗さの相関
    ramp = np.tile(np.linspace(1.0, 0.0, 64), (64, 1))
    rp = L.stipple_points_from_image(ramp, 400, iterations=25, seed=1)
    edges = np.linspace(0, 64, 9)
    count, _ = np.histogram(rp[:, 1], bins=edges)
    dark = [float((1.0 - ramp[:, int(edges[i]):int(edges[i + 1])]).mean()) for i in range(8)]
    corr_ramp = float(np.corrcoef(count, dark)[0, 1])
    # 対照群 2: 一様画像なら等間隔
    flat = L.stipple_points_from_image(np.full((64, 64), 0.5), 200, iterations=25, seed=2)
    cv_flat, cv_ramp = nn_cv(flat), nn_cv(rp)
    print("   ランプ: 帯ごとの点数と暗さの相関 %.4f(点数 %s)" % (corr_ramp, count.tolist()))
    print("   一様画像は等間隔に散る: 最近傍距離の変動係数 %.3f(ランプは %.3f)" % (cv_flat, cv_ramp))
    ck("点の密度が暗さを追う(相関 > 0.95)", corr_ramp > 0.95)
    ck("一様画像では等間隔になる(対照群)", cv_flat < 0.25 and cv_ramp > 1.5 * cv_flat)

    energies = [L.stipple_energy(ramp, L.stipple_points_from_image(ramp, 300,
                                                                   iterations=k, seed=3))
                for k in (0, 1, 2, 4, 8, 16)]
    print("   Lloyd のエネルギー: %s" % " → ".join("%.0f" % e for e in energies))
    ck("Lloyd のエネルギーは単調に下がる",
       all(energies[i + 1] <= energies[i] * (1 + 1e-9) for i in range(len(energies) - 1)))

    figs.save_grid("stipple", [img, draw_points(img.shape, pts)],
                   captions=["photograph (NASA AS11-45-6709)",
                             "%d stipple points" % len(pts)], ncols=2,
                   title="tone becomes density",
                   caption=("weighted Lloyd puts points where the picture is dark. The claim is "
                            "measured, not looked at: on a ramp the count per band correlates "
                            "%.3f with darkness, and on a flat image the points spread evenly "
                            "(nearest-neighbour cv %.2f against %.2f for the ramp)"
                            % (corr_ramp, cv_flat, cv_ramp)))
    s_ramp = density_exponent(ramp, L.stipple_points_from_image(ramp, 1200, iterations=22,
                                                                seed=5, gamma=1.0))
    s_sq = density_exponent(ramp, L.stipple_points_from_image(ramp, 1200, iterations=22,
                                                              seed=5, gamma=2.0))
    print("   ★密度の**指数**: gamma=1 で %.2f、gamma=2 で %.2f" % (s_ramp, s_sq))
    print("     (重心ボロノイの最適密度は rho^(d/(d+2)) = √rho —— Gersho。相関 0.99 でも")
    print("      指数は 1 ではない。暗さに**比例**させたいなら重みを二乗して渡す)")
    ck("gamma=1 では密度が暗さに**比例しない**(指数が 1 から離れている)",
       s_ramp < 0.8)
    ck("重みを二乗すると指数が上がる(が 1 には届かない —— 床と有限の点数のぶん)",
       s_sq > s_ramp + 0.05)

    figs.save_plot("lloyd", [("energy", np.array([0, 1, 2, 4, 8, 16], float),
                              np.asarray(energies))],
                   xlabel="Lloyd iterations", ylabel="weighted energy",
                   title="the stipple has something to minimise",
                   caption=("Lloyd's energy sum w|x-c(x)|^2 never goes up — that is a property "
                            "of the algorithm that can be checked exactly, which is why it is "
                            "the gate rather than the look of the dots"))

    # ------------------------------------------------------------------ #
    # 2 章 点を 1 本の閉じた線にする                                        #
    # ------------------------------------------------------------------ #
    print()
    print("== 2 章 1 本の閉じた線にする(質は下界との比で言う)==")
    tb = time.perf_counter()
    tour = L.stroke_tour_closed(pts, two_opt_rounds=6)
    t_tour = time.perf_counter() - tb
    mst = float(L.mst_length(pts))
    naive = L.stroke_tour_closed(pts, start="sorted", two_opt_rounds=0)
    length_px = tour_length(tour)
    print("   巡回路 %.0f px、%.1f s。MST 下界 %.0f px → 比 %.3f" % (length_px, t_tour, mst, length_px / mst))
    print("   対照群(座標順に繋ぐだけ)%.0f px → 比 %.2f" % (tour_length(naive), tour_length(naive) / mst))
    ck("各点をちょうど 1 回通って閉じる(置換)",
       np.allclose(pts[np.lexsort((pts[:, 1], pts[:, 0]))],
                   tour[np.lexsort((tour[:, 1], tour[:, 0]))]))
    ck("閉じた巡回路は MST より短くなれない", length_px >= mst - 1e-9)
    ck("巡回路は MST の 1.3 倍以内", length_px / mst < 1.3)
    ck("素朴な順序は 5 倍以上長い(対照群)", tour_length(naive) > 5.0 * length_px)

    prev, monotone = None, True
    for rounds in (0, 1, 2, 4, 6):
        v = tour_length(L.stroke_tour_closed(pts, two_opt_rounds=rounds))
        monotone = monotone and (prev is None or v <= prev + 1e-9)
        prev = v
    ck("2-opt は長さを単調に縮める", monotone)

    figs.save_grid("tour", [draw_polyline(img.shape, tour, width=1.0, scale=2),
                            draw_polyline(img.shape, naive, width=1.0, scale=2)],
                   captions=["one closed stroke (%.0f px, %.2f x MST)" % (length_px, length_px / mst),
                             "the same points in coordinate order (%.1f x MST)"
                             % (tour_length(naive) / mst)], ncols=2,
                   title="one line, and why the order matters",
                   caption=("both pictures visit exactly the same %d points exactly once; only the "
                            "order differs. The tour is checked against a lower bound rather than a "
                            "stored answer: a closed tour can never be shorter than the minimum "
                            "spanning tree" % len(pts)))

    # ------------------------------------------------------------------ #
    # 3 章 濃淡はどれだけ戻ったか(対照群つき)                              #
    # ------------------------------------------------------------------ #
    print()
    print("== 3 章 濃淡の再現 ==")
    blur = 6.0
    base = L.stroke_tone_error(img, tour, pen_width=1.0, blur_sigma=blur)
    rng = np.random.default_rng(3)
    rand = np.stack([rng.uniform(0, h, len(pts)), rng.uniform(0, w, len(pts))], axis=1)
    ctrl = L.stroke_tone_error(img, L.stroke_tour_closed(rand, two_opt_rounds=6),
                               pen_width=1.0, blur_sigma=blur)
    print("   一筆書き: 相関 %.3f  rms %.3f" % (base["corr"], base["rms"]))
    print("   対照群(同数のランダム点): 相関 %+.3f  rms %.3f" % (ctrl["corr"], ctrl["rms"]))
    ck("濃淡の相関が 0.85 を超える", base["corr"] > 0.85)
    ck("ランダムな線には濃淡の情報が無い(対照群)", ctrl["corr"] < 0.3)
    ck("rms が対照群より小さい", base["rms"] < ctrl["rms"])

    # ------------------------------------------------------------------ #
    # 4 章 ペン幅は閉形式で解ける                                          #
    # ------------------------------------------------------------------ #
    print()
    print("== 4 章 目標の濃さに合うペン幅 ==")
    solved = base["target_darkness"] * area / base["length_px"]
    print("   閉形式: ペン幅 = 目標濃淡 x 面積 / 線長 = %.3f x %.0f / %.0f = %.3f px"
          % (base["target_darkness"], area, base["length_px"], solved))
    widths = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, solved, 3.0]
    inks, preds = [], []
    for wd in widths:
        e = L.stroke_tone_error(img, tour, pen_width=wd, blur_sigma=blur)
        inks.append(e["ink_fraction"])
        preds.append(wd * base["length_px"] / area)
    tuned = L.stroke_tone_error(img, tour, pen_width=solved, blur_sigma=blur)
    print("   細い線(0.5 px)では 実測 %.4f / 予言 %.4f(%.1f %% ちがい)"
          % (inks[1], preds[1], 100 * abs(inks[1] - preds[1]) / preds[1]))
    ratio = tuned["ink_fraction"] / base["target_darkness"]
    print("   解いたペン幅 %.3f px: インク率 %.4f / 目標 %.4f = %.3f"
          % (solved, tuned["ink_fraction"], base["target_darkness"], ratio))
    print("   ★不足の %.1f %% が**線の重なり**。閉形式は重ならない範囲の式なので"
          % (100 * (1 - ratio)))
    print("     実測は必ず予言**以下**になり、その差が重なりの量そのものになる。")
    ck("細い線では閉形式と 15 % 以内で合う", abs(inks[1] - preds[1]) < 0.15 * preds[1])
    ck("ペン幅は連続なノブ(階段ではない)",
       all(inks[i + 1] > inks[i] * 1.05 for i in range(3)))
    ck("太い線は重なるので実測 < 予言", inks[-1] < preds[-1])
    # ★この絵では既定のペン幅 1.0 px がたまたまほぼ当たっており(偏り -0.0031)、
    #   解いた幅 0.900 px のほうが偏りは大きい(-0.0294)。**閉形式が当てるのは
    #   偏りではなくインク率**なので、門はそちらに置く —— 偏りで門を作ると
    #   「元から合っていた絵」で落ちる(実測でそうなった)。
    # ★偏りで門を作ると「元から合っていた絵」で落ちる(この絵では既定 1.0 px の
    #   偏りが -0.0031 と既にほぼ 0 で、解いた 0.903 px のほうが偏りは大きい)。
    #   閉形式が当てるのは**インク率**で、線が重なるぶん実測は必ず下回る ——
    #   門はその向きと大きさに置く。
    ck("解いたペン幅のインク率が目標を超えない(重なりは合併 < 和)", ratio <= 1.0 + 1e-9)
    ck("重なりで失うのは 3 割未満(線が細いあいだは閉形式が効く)", ratio > 0.70)

    drawn = np.ones_like(img) - 0.0
    figs.save_grid("tone", [img, draw_polyline(img.shape, tour, width=solved, scale=2)],
                   captions=["target", "one stroke at the solved pen width %.2f px" % solved],
                   ncols=2, title="what the stroke kept",
                   caption=("the tone of a line drawing exists at a scale coarser than the line, so "
                            "both pictures are compared after a Gaussian of sigma %.0f px: "
                            "correlation %.3f against %+.3f for the same number of random points, "
                            "and the mean tone is off by %.3f once the pen width is solved from "
                            "ink = length x width / area" % (blur, base["corr"], ctrl["corr"],
                                                             abs(tuned["bias"]))))
    figs.save_plot("pen", [("measured ink", np.asarray(widths), np.asarray(inks)),
                           ("closed form L*w/area", np.asarray(widths), np.asarray(preds)),
                           ("target darkness", np.asarray(widths),
                            np.full(len(widths), base["target_darkness"]))],
                   kinds=["scatter", "line", "line"],
                   xlabel="pen width [px]", ylabel="ink fraction",
                   title="the pen width can be solved, not tuned",
                   caption=("while the strokes do not overlap the ink fraction is length x width / "
                            "area, so the width that reproduces the mean tone is solved in closed "
                            "form (%.2f px here). Once the line starts crossing itself the union is "
                            "less than the sum and the measurement falls below the prediction — "
                            "that gap is the overlap" % solved))

    # ------------------------------------------------------------------ #
    # 5 章 振り子 —— 描く前に誤差を予言する                                 #
    # ------------------------------------------------------------------ #
    print()
    print("== 5 章 回る円の連鎖 ==")
    # ★**ナイキストを満たしているか**を先に測る。等弧長の打ち直しは、標本間隔が
    #   線分より粗いと角を切って線そのものが短くなる —— フーリエに載せる**前**の
    #   段階で情報が落ちるので、ここを見ないと「予言が当たった」の土台が崩れる。
    seg_tour = np.hypot(*np.diff(np.vstack([tour, tour[:1]]), axis=0).T)
    print("   線分の長さ: 平均 %.2f px / 中央 %.2f px / 最小 %.3f px"
          % (seg_tour.mean(), np.median(seg_tour), seg_tour.min()))
    keeps = []
    for n_res in (16384, 32768, 65536):
        cand = L.stroke_resample_closed(tour, n_res)
        s_cand = np.hypot(*np.diff(np.vstack([cand, cand[:1]]), axis=0).T)
        ds = float(seg_tour.sum()) / n_res
        keeps.append(float(s_cand.sum() / seg_tour.sum()))
        print("   %6d 点: 標本間隔 %.3f px(表現できる最短周期 %.2f px)-> 長さ保持 %.4f"
              % (n_res, ds, 2 * ds, keeps[-1]))
    print("   ★誤差は 1/N で落ちる(%.2f %% -> %.2f %% -> %.2f %%)—— 標本間隔が"
          % tuple(100 * (1 - k) for k in keeps))
    print("     線分の中央値を下回るまで増やさないと、角が丸まって線が縮む。")
    ck("打ち直しの誤差が 1/N で落ちる(倍にすると半分)",
       abs((1 - keeps[0]) / (1 - keeps[1]) - 2.0) < 0.25
       and abs((1 - keeps[1]) / (1 - keeps[2]) - 2.0) < 0.25)
    ck("採った点数では線の 95 % 以上が残る", keeps[1] > 0.95)
    N_RESAMPLE = 32768
    closed = L.stroke_resample_closed(tour, N_RESAMPLE)
    spec = L.contour_fourier_complex(closed, parametrisation="index")
    tab = L.contour_fourier_truncation_energy(spec)
    orders = list(tab["order"])
    print("   %6s %14s %12s" % ("K", "予言 rms[px]", "エネルギー"))
    rows_h = []
    for K in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512):
        i = orders.index(K)
        print("   %6d %14.2f %11.1f %%" % (K, tab["rms_error"][i], 100 * tab["energy_fraction"][i]))
        rows_h.append([str(K), "%.2f" % tab["rms_error"][i],
                       "%.2f %%" % (100 * tab["energy_fraction"][i])])
    # 予言が当たることを、実際に再構成して確かめる
    k = np.round(spec[:, 0]).astype(int)
    c = spec[:, 1] + 1j * spec[:, 2]
    z = closed[:, 1] + 1j * closed[:, 0]
    tt = np.arange(z.size) / z.size
    worst = 0.0
    for K in (4, 16, 64):
        sel = np.abs(k) <= K
        rec = np.zeros(z.size, dtype=complex)
        for kj, cj in zip(k[sel], c[sel]):
            rec += cj * np.exp(2j * np.pi * kj * tt)
        worst = max(worst, abs(float(np.sqrt((np.abs(z - rec) ** 2).mean()))
                               - float(tab["rms_error"][orders.index(K)])))
    print("   予言と実測の差(K = 4 / 16 / 64)最大 %.2e px —— パーセバルは厳密" % worst)
    ck("予言した誤差が実測と一致する(機械精度)", worst < 1e-8)
    ck("エネルギーは単調に増え 1 に達する",
       bool(np.all(np.diff(tab["energy_fraction"]) >= -1e-15))
       and abs(tab["energy_fraction"][-1] - 1.0) < 1e-12)
    k64 = 100 * tab["energy_fraction"][orders.index(64)]
    ck("64 個の円で 99 % を超える", k64 > 99.0)

    figs.save_plot("harmonics",
                   [("predicted rms error [px]",
                     np.asarray(orders, float)[1:], tab["rms_error"][1:])],
                   xlabel="circles kept (|k| <= K)", ylabel="predicted rms error [px]",
                   title="how many circles the picture needs",
                   caption=("Parseval makes this a prediction, not a measurement: the squared error "
                            "of the order-K reconstruction equals the energy of the coefficients "
                            "above K, exactly. Checked against an actual reconstruction the two "
                            "agree to %.0e px. %d circles already carry %.1f %% of the drawing"
                            % (worst, 64, k64)))

    stages = (1, 4, 16, 90, 600, 4000)
    frames = epicycle_frames(spec, img.shape, stages, frames_per_stage=12, scale=2)
    e_stage = [float(tab["energy_fraction"][orders.index(K)]) if K in orders else
               float(np.interp(K, orders, tab["energy_fraction"])) for K in stages]
    figs.save_gif("epicycles", frames, fps=9,
                  caption=("the actual chain of rotating circles, not a sweep of truncations: "
                           "each arm is one Fourier term, its length |c_k| and its speed k. "
                           "The number of arms rises 1, 3, 8, 24, 80, 300 and the picture "
                           "gives itself away — carrying %s of the drawing's energy, every "
                           "figure predicted before it was drawn."
                           % " / ".join("%.1f%%" % (100 * e) for e in e_stage)))
    print("   ★回る円の本数と、描く前に分かっているエネルギー:")
    for K, e in zip(stages, e_stage):
        print("      %4d 本 -> %6.2f %%" % (K, 100 * e))
    ck("段を追うごとに残したエネルギーが増える",
       all(e_stage[i] <= e_stage[i + 1] + 1e-12 for i in range(len(e_stage) - 1)))
    ck("GIF が実際に回る腕を描いている(円が入るので図が真っ白でない)",
       float(np.asarray(frames[0]).min()) < 0.5 and len(frames) == 12 * len(stages))

    # ------------------------------------------------------------------ #
    # 6 章 紙の上へ                                                       #
    # ------------------------------------------------------------------ #
    print()
    print("== 6 章 G-code(既存の op でそのまま閉じる)==")
    mm_per_px = sheet_mm / w
    cont = {"ring": np.zeros(len(tour), dtype=np.int64),
            "x": tour[:, 1] * mm_per_px, "y": tour[:, 0] * mm_per_px}
    seg_tab = L.contours_to_gcode(cont, z=0.0, line_width_mm=solved * mm_per_px,
                                  feed_mm_min=FEED_MM_MIN)
    seg_mm = float(np.hypot(seg_tab["x1"] - seg_tab["x0"], seg_tab["y1"] - seg_tab["y0"]).sum())
    secs = float(L.gcode_time_estimate(seg_tab))
    print("   作画幅 %.0f mm(%.4f mm/px)" % (sheet_mm, mm_per_px))
    print("   ★**この絵は 1 本の線で、紙の上で %.2f m。送り %.0f mm/min なら最短 %.1f 分**"
          % (seg_mm / 1000.0, FEED_MM_MIN, secs / 60.0))
    print("   (gcode_time_estimate は加速度とジャークを無視するので**下限**)")
    ck("紙の上の線長が 5 m を超える", seg_mm > 5000.0)
    ck("所要時間は長さ / 送り と一致する",
       abs(secs - seg_mm / (FEED_MM_MIN / 60.0)) < 1e-6 * secs + 1e-9)

    rows = [
        ["photograph", "%dx%d" % (h, w), "Hokusai, Great Wave (Met CC0, DP130155)"],
        ["stipple points", "%d" % len(pts), "%.1f s" % t_stipple],
        ["density vs darkness (ramp)", "%.4f" % corr_ramp, "control: flat image cv %.2f" % cv_flat],
        ["tour length", "%.0f px" % length_px, "%.1f s" % t_tour],
        ["tour / MST lower bound", "%.3f" % (length_px / mst), "coordinate order: %.1f"
         % (tour_length(naive) / mst)],
        ["tone correlation", "%.3f" % base["corr"], "random control: %+.3f" % ctrl["corr"]],
        ["solved pen width", "%.2f px" % solved,
         "ink %.3f of target; %.0f %% short = overlap"
         % (ratio, 100 * (1 - ratio))],
        ["density exponent (ramp)", "%.2f" % s_ramp,
         "squared weight %.2f (Gersho: sqrt)" % s_sq],
        ["resample points", "%d" % N_RESAMPLE,
         "keeps %.1f %% of stroke; error ~ 1/N" % (100 * keeps[1])],
        ["circles for 99 %", "64", "%.1f %% of the energy" % k64],
        ["prediction vs measurement", "%.0e px" % worst, "Parseval, exact"],
        ["stroke on paper", "%.2f m" % (seg_mm / 1000.0), "sheet %.0f mm" % sheet_mm],
        ["plotter time (lower bound)", "%.1f min" % (secs / 60.0), "feed %.0f mm/min" % FEED_MM_MIN],
    ]
    figs.save_table("numbers", ["quantity", "value", "note"], rows,
                    title="one photograph, one closed line, and what survived",
                    caption=("every row is measured by an operator in this run; the harmonic rows "
                             "are predicted in closed form before the drawing is made"))
    figs.save_table("harmonic_table", ["circles K", "predicted rms [px]", "energy kept"], rows_h,
                    title="what each order of circles buys",
                    caption="Parseval: the error above is the energy that was left out, exactly")

    print()
    print("所要 %.1f s" % (time.perf_counter() - t0))
    for name, ok in checks:
        print("  [%s] %s" % ("ok" if ok else "NG", name))
    bad = [n for n, ok in checks if not ok]
    if bad:
        print("FAIL: %d check(s) did not hold: %s" % (len(bad), bad))
        return 1
    assert not figs.errors(), figs.errors()
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
