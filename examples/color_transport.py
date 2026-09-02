# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""color_transport — 輸送 op(colortransport)を「2 台のカメラの色を揃える」筋で一巡する。

    py -3.11 examples/color_transport.py

【この例が解く問題】
1 本のラインに検査カメラが 2 台ある。カメラ B はカラーフィルタの漏れ
(チャネル間クロストーク)と黒レベルのずれを持っていて、**同じワークを
撮っても A と違う色に写る**。このままだと色判定の閾値を 2 セット持つことに
なるので、B の色を A に合わせて 1 セットで済ませたい。最後に、学習用の
合成画像を作るため良品パッチを別の場所へ**継ぎ目なく**貼る。

(1) 物差しを検定する。1 次元の最適輸送を総当たりの割当問題と、2-Wasserstein を
    ガウスの閉形式と突き合わせる。
(2) 輸送計画を作り、**使う**。``transport_cost`` が距離と一致し、
    ``apply_transport`` が並べ替えそのものになること。
(3) B を A に合わせる。3 つの手法が**それぞれ何を保証して何を捨てるか**を
    平均・共分散・周辺分布の残差で表にする。
(4) 仮定が破れる場面を作る。二峰の絵に単峰の参照で Reinhard を掛けると
    **平均も標準偏差もぴたり合うのに分布は遠い**。例外は出ない。
(5) 整数画像の同値(平坦部)をどう扱うか。``ties`` は両方とも何かを失う。
(6) Sinkhorn。正則化を弱めると厳密解に寄るが、距離には**系統的な偏り**が
    残る。``sinkhorn_divergence`` で打ち消す。
(7) Poisson 合成。出力だけから確かめられる不変量 2 つと、素朴な貼り付けとの
    境界段差の比較。

【グラウンドトゥルース(数値で嘘を弾く)】
1. ``wasserstein_1d`` と ``scipy.optimize.linear_sum_assignment`` の総当たり解
   が n=8 で 2.2e-16、n=40 で 8.9e-16。
2. ガウスの 2-Wasserstein 閉形式 ``hypot(m1-m2, s1-s2)`` へ標本数とともに
   単調収束(200 → 20000 標本で 4.5e-03 → 4.7e-05)。
3. ``transport_plan_1d`` の行和 = 1/n・列和 = 1/m が**厳密に 0.0** 誤差、
   ``transport_cost`` が ``wasserstein_1d`` と 8.9e-16 一致。
4. ``method="gaussian"`` は平均と共分散を機械精度(1.4e-15 / 2.0e-15)で再現、
   ``method="histogram"`` は周辺分布を**厳密に 0.0** 再現。どちらも他方は
   再現しない ―― 選択は「何を捨てるか」の選択。
5. ``sinkhorn_distance`` は自分自身との距離が 0 でない(reg=0.2 で 0.152161)、
   ``sinkhorn_divergence`` は同じ条件で 0.0。
6. Poisson 合成: 内部のラプラシアンが元と 2.4e-15、マスク外は貼り先と
   **ビット単位で一致**、線形系の残差 2.2e-15。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.optimize import linear_sum_assignment
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import colortransport as CT  # noqa: E402
import imgmetrics as M  # noqa: E402

#: カメラ B のカラーフィルタの漏れ(行 = 出力チャネル)。**チャネルを混ぜる**
#: ので、各チャネル独立の補正では原理的に戻せない。
CROSSTALK = np.array([[0.82, 0.14, 0.04],
                      [0.09, 0.86, 0.05],
                      [0.03, 0.11, 0.86]])

_LAPLACIAN = np.array([[0.0, -1.0, 0.0], [-1.0, 4.0, -1.0], [0.0, -1.0, 0.0]])


def normal_quantiles(n, mu, sigma):
    """決定論的な正規標本(分位点そのもの)。乱数の揺らぎを消すため。"""
    return mu + sigma * norm.ppf((np.arange(n) + 0.5) / n)


def workpiece(n=64, seed=0, crosstalk=None, bias=(0.0, 0.0, 0.0)):
    """ワークを 1 枚撮る —— **乱数だけにしない**。

    背景のなだらかな勾配 + 矩形のワーク(平坦=同値だらけ)+ 4 px 周期の縞
    (細かい構造)。前景と背景がはっきり分かれた**二峰**の絵になっていて、
    これが Reinhard の単峰仮定を破る形でもある。
    """
    y, x = np.mgrid[0:n, 0:n] / (n - 1.0)
    bg = 0.18 + 0.10 * y
    img = np.stack([bg, bg * 0.95 + 0.03, bg * 0.85 + 0.08], axis=-1)
    part = (np.abs(y - 0.5) < 0.22) & (np.abs(x - 0.5) < 0.28)
    img[part] = np.array([0.74, 0.52, 0.26])                 # ワーク面
    stripe = part & (((np.arange(n) // 4) % 2).astype(bool)[None, :])
    img[stripe] = np.array([0.62, 0.66, 0.44])               # 表面の縞
    img = img + 0.006 * np.random.default_rng(seed).standard_normal(img.shape)
    if crosstalk is not None:
        img = (img.reshape(-1, 3) @ np.asarray(crosstalk).T).reshape(n, n, 3)
    return np.clip(img + np.asarray(bias), 0.0, 1.0), part


def main():
    cam_a, part = workpiece(seed=1)
    cam_b, _ = workpiece(seed=2, crosstalk=CROSSTALK, bias=(0.05, 0.02, -0.01))
    fa = cam_a.reshape(-1, 3)
    fb = cam_b.reshape(-1, 3)

    # ------------------------------------------------------------------ #
    # 1) 物差しの検定 —— 総当たり解と閉形式に当てる                        #
    # ------------------------------------------------------------------ #
    print("1) 物差しの検定:")
    rng = np.random.default_rng(0)
    for n in (8, 40):
        u = rng.normal(0.0, 1.0, n)
        v = rng.normal(1.0, 2.0, n)
        cost = np.abs(u[:, None] - v[None, :])
        r, c = linear_sum_assignment(cost)                   # 総当たりの割当問題
        brute = float(cost[r, c].sum() / n)
        mine = CT.wasserstein_1d(u, v, p=1)
        print(f"   n={n:3d}  総当たり={brute:.15f}  wasserstein_1d={mine:.15f}  "
              f"差={abs(mine - brute):.2e}")
        assert abs(mine - brute) < 1e-12

    closed = float(np.hypot(2.0 - 0.0, 3.0 - 1.0))           # ガウスの閉形式
    errs = []
    for n in (200, 2000, 20000):
        w2 = CT.wasserstein_1d(normal_quantiles(n, 0.0, 1.0),
                               normal_quantiles(n, 2.0, 3.0), p=2)
        errs.append(abs(w2 - closed))
        print(f"   W2({n:5d} 標本)={w2:.8f}  閉形式 hypot(2,2)={closed:.8f}  "
              f"誤差={errs[-1]:.2e}")
    assert errs[0] > errs[1] > errs[2]                       # 標本数とともに単調に寄る
    assert errs[-1] < 1e-4

    # ------------------------------------------------------------------ #
    # 2) 輸送計画を作って、使う                                            #
    # ------------------------------------------------------------------ #
    src_s = normal_quantiles(24, 0.0, 1.0)
    ref_s = normal_quantiles(24, 1.5, 2.0)
    plan = CT.transport_plan_1d(src_s, ref_s)
    cost = np.abs(src_s[:, None] - ref_s[None, :])
    total = CT.transport_cost(plan, cost)
    exact = CT.wasserstein_1d(src_s, ref_s, p=1)
    moved = CT.apply_transport(plan, ref_s)
    print(f"2) 輸送計画 {plan.shape}: 行和のずれ={np.abs(plan.sum(1) - 1 / 24).max():.1e}  "
          f"列和のずれ={np.abs(plan.sum(0) - 1 / 24).max():.1e}  総質量={plan.sum():.15f}")
    print(f"   transport_cost={total:.15f}  wasserstein_1d={exact:.15f}  "
          f"差={abs(total - exact):.2e}")
    print(f"   apply_transport は並べ替えそのもの: 昇順の行き先との差="
          f"{np.abs(moved - np.sort(ref_s)).max():.2e}")
    assert np.abs(plan.sum(1) - 1 / 24).max() == 0.0         # 構成上厳密
    assert np.abs(plan.sum(0) - 1 / 24).max() == 0.0
    assert abs(total - exact) < 1e-12
    assert np.abs(moved - np.sort(ref_s)).max() < 1e-12
    assert np.all(plan >= 0.0)

    # ------------------------------------------------------------------ #
    # 3) B を A に合わせる —— 何を保証して何を捨てるか                     #
    # ------------------------------------------------------------------ #
    before = M.delta_e_map(cam_b, cam_a)
    print(f"3) 色合わせ(統計は RGB 空間で取る)。補正前の色差: "
          f"ΔE00 平均={before.mean():.4f}  p95={np.percentile(before, 95):.4f}  "
          f"最大={before.max():.4f}")
    print("   手法        ΔE00 平均   平均の残差   共分散の残差   周辺分布の残差")
    residuals = {}
    for method in CT.COLOR_TRANSFER_METHODS:
        out = CT.color_transfer(cam_b, cam_a, method=method, space="rgb")
        fo = out.reshape(-1, 3)
        d = M.delta_e_map(out, cam_a)
        r_mean = float(np.abs(fo.mean(axis=0) - fa.mean(axis=0)).max())
        r_cov = float(np.abs(np.cov(fo, rowvar=False) - np.cov(fa, rowvar=False)).max())
        r_marg = float(max(np.abs(np.sort(fo[:, c]) - np.sort(fa[:, c])).max()
                           for c in range(3)))
        residuals[method] = (d.mean(), r_mean, r_cov, r_marg)
        print(f"   {method:<10}  {d.mean():9.4f}   {r_mean:10.2e}   {r_cov:12.2e}   "
              f"{r_marg:13.2e}")
        assert d.mean() < before.mean()                      # どれも改善はする

    # 3 手法が保証するものは互いに素 —— どれを選んでも何かは捨てる
    assert residuals["gaussian"][2] < 1e-12                  # 共分散を厳密に運ぶ
    assert residuals["reinhard"][2] > 1e-4                   # 各チャネル独立なので運べない
    assert residuals["histogram"][2] > 1e-4
    assert residuals["histogram"][3] == 0.0                  # 周辺分布は厳密に一致
    assert residuals["gaussian"][3] > 1e-4                   # そちらは合わない
    assert residuals["reinhard"][3] > 1e-4
    for m in CT.COLOR_TRANSFER_METHODS:
        assert residuals[m][1] < 1e-12                       # 平均はどれも合う
    print("   → 共分散を厳密に運ぶのは gaussian だけ、周辺分布を厳密に合わせるのは "
          "histogram だけ。両立はしない。")

    # クロストークは**チャネルを混ぜる**変換なので、対角の補正では戻らない。
    # 相関係数で見るとその差が出る。
    corr = lambda v: float(np.corrcoef(v[:, 0], v[:, 2])[0, 1])
    out_g = CT.color_transfer(cam_b, cam_a, method="gaussian", space="rgb").reshape(-1, 3)
    out_r = CT.color_transfer(cam_b, cam_a, method="reinhard", space="rgb").reshape(-1, 3)
    print(f"   R-B 相関: カメラ A={corr(fa):.4f}  カメラ B(クロストーク後)={corr(fb):.4f}  "
          f"→ gaussian 補正後={corr(out_g):.4f}  reinhard 補正後={corr(out_r):.4f}")
    assert abs(corr(out_g) - corr(fa)) < 1e-9                # 相関ごと戻る
    assert abs(corr(out_r) - corr(fa)) > 1e-3                # 戻らない

    # 写像そのものを直接取り出す(色移し op の中身)。手で当てても同じ絵になる。
    A_map, m1, m2 = CT.gaussian_transport_map(fb, fa)
    manual = np.clip(((fb - m1) @ A_map.T + m2).reshape(cam_b.shape), 0.0, 1.0)
    print(f"   gaussian_transport_map: A の行列式={np.linalg.det(A_map):.6f}  "
          f"(1 より大 = 分散を広げる向き)  "
          f"手で当てた結果と color_transfer の差="
          f"{np.abs(manual - CT.color_transfer(cam_b, cam_a, method='gaussian', space='rgb')).max():.1e}")
    assert np.array_equal(
        manual, CT.color_transfer(cam_b, cam_a, method="gaussian", space="rgb"))
    assert np.allclose(((fb - m1) @ A_map.T + m2).mean(axis=0), fa.mean(axis=0), atol=1e-12)

    # ------------------------------------------------------------------ #
    # 4) 仮定が破れる場面 —— 統計は合うのに分布は遠い                      #
    # ------------------------------------------------------------------ #
    unimodal = np.clip(
        0.45 + 0.05 * np.random.default_rng(11).standard_normal((64, 64, 3)), 0, 1)
    rein = CT.color_transfer(cam_b, unimodal, method="reinhard", space="rgb").reshape(-1, 3)
    hist = CT.color_transfer(cam_b, unimodal, method="histogram", space="rgb").reshape(-1, 3)
    fu = unimodal.reshape(-1, 3)
    print(f"4) 二峰の絵(前景 {int(part.sum())} px / 背景 {int((~part).sum())} px)に"
          "単峰の参照で Reinhard:")
    print(f"   平均の残差={np.abs(rein.mean(axis=0) - fu.mean(axis=0)).max():.2e}  "
          f"標準偏差の残差={np.abs(rein.std(axis=0) - fu.std(axis=0)).max():.2e}  "
          "← 統計はぴたり合う")
    assert np.abs(rein.mean(axis=0) - fu.mean(axis=0)).max() < 1e-12
    assert np.abs(rein.std(axis=0) - fu.std(axis=0)).max() < 1e-12
    for c, ch in enumerate("RGB"):
        d_rein = CT.wasserstein_1d(rein[:, c], fu[:, c])
        d_hist = CT.wasserstein_1d(hist[:, c], fu[:, c])
        print(f"   {ch} チャネルの分布距離 W1: reinhard={d_rein:.6f}  "
              f"histogram={d_hist:.6f}  比={d_rein / max(d_hist, 1e-12):.3g}")
        assert d_hist < 1e-9                                 # 分布は厳密に一致
        assert d_rein > 0.01                                 # 統計は合うのに遠い
    print("   → 例外は一切出ない。「平均と分散が合った」を「分布が合った」と"
          "読むと静かに間違う。")

    # ------------------------------------------------------------------ #
    # 5) 整数画像の同値 —— 平坦部か、分布の厳密さか                        #
    # ------------------------------------------------------------------ #
    src_u8 = np.round(cam_b[..., 0] * 255).astype(np.uint8)
    ref_u8 = np.round(cam_a[..., 0] * 255).astype(np.uint8)
    avg = CT.histogram_match(src_u8, ref_u8)                 # 既定 ties="average"
    brk = CT.histogram_match(src_u8, ref_u8, ties="break")
    values, counts = np.unique(src_u8, return_counts=True)
    busiest = int(values[counts.argmax()])                   # 最も画素数の多い値
    n_avg = len(np.unique(avg[src_u8 == busiest]))
    n_brk = len(np.unique(brk[src_u8 == busiest]))
    err_avg = float(np.abs(np.sort(avg.ravel()) - np.sort(ref_u8.ravel().astype(float))).max())
    err_brk = float(np.abs(np.sort(brk.ravel()) - np.sort(ref_u8.ravel().astype(float))).max())
    print(f"5) 整数画像の同値: 値 {busiest} が {int(counts.max())} 画素ある。"
          f"ties='average' → 出力 {n_avg} 値 / ties='break' → 出力 {n_brk} 値")
    print(f"   出力分布と参照のずれ(最大): average={err_avg:.4f} 階調  "
          f"break={err_brk:.4f} 階調")
    print(f"   値の種類: 入力 {len(values)} → average {len(np.unique(avg))} / "
          f"break {len(np.unique(brk))}")
    assert n_avg == 1                                        # 等しい入力は等しい出力へ
    assert n_brk > 1                                         # 平坦部が割れる
    assert err_brk == 0.0                                    # 分布は厳密一致
    assert err_avg > 1.0                                     # そのぶん丸まる
    assert len(np.unique(avg)) == len(values)
    assert len(np.unique(brk)) > len(values)
    print("   → どちらも何かを失う(平坦部の平坦さ か 分布の厳密さ)。"
          "だから既定で片方に決めず引数にしてある。")

    # ------------------------------------------------------------------ #
    # 6) Sinkhorn —— 近似であることを数値で                                #
    # ------------------------------------------------------------------ #
    a_s = np.linspace(0.0, 1.0, 24)
    b_s = np.linspace(0.4, 2.0, 24)
    w = np.full(24, 1.0 / 24)
    # **二乗費用を使う。** 線形費用 |x-y| はこの 2 つの台ではほぼ退化していて
    # (b > a となる組が 576 中 506)、費用は計画にほとんど依らない ―― 距離は
    # 正しく出るのに**計画は決まらない**。実測: reg を 0.5 → 0.005 と下げても
    # 重心写像の誤差は 0.737 → 0.625 で頭打ちになる。二乗費用なら最適計画は
    # 一意なので、下の表のとおり素直に収束する。
    cost2 = (a_s[:, None] - b_s[None, :]) ** 2
    exact_map = CT.apply_transport(CT.transport_plan_1d(a_s, b_s), b_s)
    exact_cost = CT.transport_cost(CT.transport_plan_1d(a_s, b_s), cost2)
    print(f"6) Sinkhorn(二乗費用、厳密な最適費用={exact_cost:.10f} "
          f"= W2^2={CT.wasserstein_1d(a_s, b_s, p=2) ** 2:.10f}):")
    print("   reg      正則化つき費用   厳密との差   重心写像の最大誤差   計画の鋭さ")
    prev_cost_err = prev_map_err = float("inf")
    for reg in (0.2, 0.05, 0.01, 0.004, 0.002):
        pl = CT.sinkhorn(w, w.copy(), cost2, reg=reg, n_iter=100000, tol=1e-13)
        assert np.abs(pl.sum(axis=1) - w).max() < 1e-9       # 要求した周辺分布
        assert np.abs(pl.sum(axis=0) - w).max() < 1e-9
        c = CT.transport_cost(pl, cost2)
        map_err = float(np.abs(CT.apply_transport(pl, b_s) - exact_map).max())
        sharp = float(pl[0].max() / pl[0].sum())
        print(f"   {reg:<7.3f}  {c:14.8f}  {c - exact_cost:11.2e}  {map_err:18.5f}  "
              f"{sharp:11.3f}")
        assert c - exact_cost < prev_cost_err                # 単調に厳密解へ
        assert map_err < prev_map_err
        prev_cost_err, prev_map_err = c - exact_cost, map_err
        assert c >= exact_cost - 1e-12                       # 上から寄る
    assert prev_map_err < 0.02

    # 距離としての偏り。自分自身との「距離」が 0 にならない。
    cost_aa = np.abs(a_s[:, None] - a_s[None, :])
    cost_bb = np.abs(b_s[:, None] - b_s[None, :])
    cost_ab = np.abs(a_s[:, None] - b_s[None, :])
    self_dist = CT.sinkhorn_distance(w, w.copy(), cost_aa, reg=0.2)
    self_div = CT.sinkhorn_divergence(w, w.copy(), cost_aa, reg=0.2)
    print(f"   偏り: sinkhorn_distance(a, a)={self_dist:.6f}(厳密なら 0)  "
          f"sinkhorn_divergence(a, a)={self_div:.2e}")
    assert self_dist > 0.05                                  # 0 にならない
    assert abs(self_div) < 1e-9                              # 引き算で相殺される
    div = CT.sinkhorn_divergence(w, w.copy(), cost_ab, cost_aa=cost_aa,
                                 cost_bb=cost_bb, reg=0.05)
    w1 = CT.wasserstein_1d(a_s, b_s, p=1)
    print(f"   偏りを消した距離: sinkhorn_divergence={div:.6f}  "
          f"厳密な W1={w1:.6f}  差={abs(div - w1):.4f}")
    assert abs(div - w1) < 0.1
    assert div > 0.4                                         # 違う分布はちゃんと離れる

    # ------------------------------------------------------------------ #
    # 7) Poisson 合成 —— 出力だけから正しさを確かめる                      #
    # ------------------------------------------------------------------ #
    patch, _ = workpiece(n=40, seed=3)                       # 貼る良品パッチ
    board, _ = workpiece(n=90, seed=4, bias=(0.10, 0.08, 0.04))   # 貼り先(明るい)
    mask = np.zeros((40, 40), bool)
    mask[6:34, 8:32] = True                                  # 縁に接していない
    off = (20, 25)
    blended, info = CT.poisson_blend(patch, board, mask, offset=off)
    print(f"7) Poisson 合成: 解いた画素={info['solved_pixels']}  "
          f"動いた要素={info['changed_pixels']}"
          f"(= {info['solved_pixels']} px x 3 ch)  "
          f"最大移動={info['max_shift']:.4f}  線形系の残差={info['residual']:.2e}")
    assert info["solved_pixels"] == int(mask.sum())
    assert info["changed_pixels"] == int(mask.sum()) * 3     # カラーは ch ごとに数える
    assert info["residual"] < 1e-10

    # 不変量その 1: 内部のラプラシアンが元の勾配場と一致
    window = blended[off[0]:off[0] + 40, off[1]:off[1] + 40]
    inner = ndimage.binary_erosion(mask)
    lap_err = max(
        float(np.abs(ndimage.convolve(window[..., c], _LAPLACIAN, mode="nearest")[inner]
                     - ndimage.convolve(patch[..., c], _LAPLACIAN, mode="nearest")[inner]).max())
        for c in range(3))
    # 不変量その 2: マスクの外は貼り先と厳密に一致(1 画素も触らない)
    restored = blended.copy()
    restored[off[0]:off[0] + 40, off[1]:off[1] + 40][mask] = \
        board[off[0]:off[0] + 40, off[1]:off[1] + 40][mask]
    print(f"   不変量: 内部のラプラシアンの差={lap_err:.2e}  "
          f"マスク外は貼り先とビット単位で一致={np.array_equal(restored, board)}")
    assert lap_err < 1e-10
    assert np.array_equal(restored, board)

    # 素朴な貼り付けとの比較 —— 境界の段差を数値で
    naive = board.copy()
    naive[off[0]:off[0] + 40, off[1]:off[1] + 40][mask] = patch[mask]
    ring_in = mask & ~ndimage.binary_erosion(mask)
    ring_out = ndimage.binary_dilation(mask) & ~mask
    steps = {}
    for label, img in (("素朴な貼り付け", naive), ("Poisson 合成", blended)):
        win = img[off[0]:off[0] + 40, off[1]:off[1] + 40]
        steps[label] = float(np.abs(win[ring_in].mean(axis=0)
                                    - win[ring_out].mean(axis=0)).max())
        print(f"   境界をまたぐ段差({label}): {steps[label]:.6f}")
    assert steps["Poisson 合成"] < steps["素朴な貼り付け"] / 100.0
    print(f"   → 段差は {steps['素朴な貼り付け'] / steps['Poisson 合成']:.0f} 分の 1 になる。"
          "ただし**貼った物の色そのものが変わる**"
          f"(最大 {info['max_shift']:.4f})ので、色を測る用途にこの出力を流さない。")

    print("PASS: colortransport 11 op すべてを通し、総当たり解・ガウス閉形式・"
          "構成上の不変量と一致")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
