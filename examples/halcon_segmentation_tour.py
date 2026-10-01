# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""halcon_segmentation_tour — HALCON "Segmentation" 章の 9 op を、答えの分かる合成画像で一巡する。

    py -3.11 examples/halcon_segmentation_tour.py

【この例が示すこと】
``fullseye.ledger`` に載った 9 本(check_difference / class_2dim_sup / learn_ndim_norm /
class_ndim_norm / class_2dim_unsup / classify_image_class_lut / expand_gray /
regiongrowing_n / watersheds_marker)を、それぞれ**閉形式で答えが決まる入力**で呼び、
真値と突き合わせる。各節の印字は「真値 / 実測」。PASS 行が出れば全部通っている。

【場面(答えを自分で埋める)】
* 2 本の棒(値 0.2 と 0.6)と背景 0 の階段状画像。第 2 特徴は中央に 1 つ島。
* 尾根(高い 1 列)の左右にマーカーを置いた谷。
* 平坦な島の中に穴を 1 つ開けた画像(expand_gray の候補外)。

【グラウンドトゥルース(すべて assert で落とす)】
1. check_difference: 差を入れた画素の集合そのもの。
2. class_2dim_sup: 参照領域の特徴の [min, max] 箱(箱の外は 0 個)。
3. learn_ndim_norm → class_ndim_norm: 平均の画素は必ず内側、遠い画素は外側、
   内側率 ≈ 1 − exp(−thresh²/2)(2 自由度のカイ二乗)。
4. class_2dim_unsup: Lloyd の不動点(各画素は自分のクラスタ平均に最も近い)。
5. classify_image_class_lut: LUT の総当たりと一致。
6. expand_gray: 候補 ∪ 種の中で種を含む 4 連結成分と画素単位で一致、穴は入らない。
7. regiongrowing_n: 階段状では連結成分ラベリングと同じ分割(番号の付け替えに不変)。
8. watersheds_marker: 尾根で割れる(左 = 1、右 = 2)。
★実測(honest)で分かっている癖(直していない): regiongrowing_n の min_size は効かない /
  expand_gray と regiongrowing_n は隣接画素でなく**種の値**と比べる(HALCON と違う)/
  class_2dim_unsup は初期中心に依存して局所解に落ちうる。詳細はノートに。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fullseye as fs          # noqa: E402  公開経路(fs.ledger.<op>)から呼ぶ


def _same_partition(a, b) -> bool:
    fwd, bwd = {}, {}
    for x, y in zip(np.asarray(a).ravel().tolist(), np.asarray(b).ravel().tolist()):
        if fwd.setdefault(x, y) != y or bwd.setdefault(y, x) != x:
            return False
    return True


def scene(rng):
    """階段状の 2 特徴画像と真のラベル。★EXTEND: f1/f2 を自分の 2 チャネル画像に差し替える。"""
    H, W = 24, 36
    gt = np.zeros((H, W), int)
    gt[:, 12:24] = 1
    gt[:, 24:] = 2
    f1 = np.array([0.0, 0.2, 0.6])[gt]
    f2 = np.zeros((H, W))
    f2[8:14, 15:21] = 0.9                       # 第 2 特徴だけ違う島
    return f1, f2, gt


def run() -> dict:
    t0 = time.perf_counter()
    rng = np.random.default_rng(0)
    f1, f2, gt = scene(rng)
    H, W = f1.shape
    L = fs.ledger
    out = {}

    print("1) check_difference —— 基準との差が tol を超える画素")
    ref = f1.copy()
    noisy = f1.copy()
    bump = np.zeros((H, W), bool)
    bump[2:5, 2:7] = True
    noisy[bump] += 0.3
    diff = np.asarray(L.check_difference(noisy, ref, tol=0.1))
    assert diff.dtype == bool and np.array_equal(diff, bump)
    print("   真値 %d 画素 / 実測 %d 画素" % (bump.sum(), diff.sum()))
    out["check_difference"] = int(diff.sum())

    print("2) class_2dim_sup —— 参照領域の特徴空間の箱")
    refreg = gt == 1
    sup = np.asarray(L.class_2dim_sup(f1, f2, refreg))
    want = (f1 >= 0.2) & (f1 <= 0.2) & (f2 >= 0.0) & (f2 <= 0.9)
    assert np.array_equal(sup, want)
    print("   真値 %d 画素 / 実測 %d 画素(箱 = f1∈[0.2,0.2] × f2∈[0,0.9])" % (want.sum(), sup.sum()))
    out["class_2dim_sup"] = int(sup.sum())

    print("3) learn_ndim_norm → class_ndim_norm —— 学習した正規分布の等高線")
    X = rng.normal(size=(500, 2)) * np.array([2.0, 0.5]) + np.array([0.3, -0.2])
    model = L.learn_ndim_norm(X)
    assert set(model) == {"mean", "cov", "inv"}
    y, x = np.mgrid[-4:4:33j, -4:4:33j]
    fa = x + 0.3
    fb = y * 0.25 - 0.2
    inside = np.asarray(L.class_ndim_norm([fa, fb], model, thresh=2.0))
    assert inside[16, 16] and not inside[0, 0]
    sample = np.asarray(L.class_ndim_norm([X[:, 0].reshape(20, 25), X[:, 1].reshape(20, 25)], model, thresh=2.0))
    frac = float(sample.mean())
    assert abs(frac - (1.0 - np.exp(-2.0))) < 0.05, frac
    print("   標本の内側率: 真値 %.3f / 実測 %.3f" % (1.0 - np.exp(-2.0), frac))
    out["class_ndim_norm_frac"] = frac

    print("4) class_2dim_unsup —— k-means の不動点")
    g1 = f1 + rng.normal(0, 0.01, (H, W))
    g2 = f2 + rng.normal(0, 0.01, (H, W))
    lab = np.asarray(L.class_2dim_unsup(g1, g2, n_clusters=3))
    Xp = np.column_stack([g1.ravel(), g2.ravel()])
    C = np.array([Xp[lab.ravel() == k].mean(0) for k in range(3)])
    near = ((Xp[:, None, :] - C[None, :, :]) ** 2).sum(2).argmin(1)
    assert np.array_equal(near, lab.ravel())
    print("   各画素が自分のクラスタ平均に最も近い: 真値 %d / 実測 %d" % (H * W, int((near == lab.ravel()).sum())))
    out["class_2dim_unsup_k"] = int(len(np.unique(lab)))

    print("5) classify_image_class_lut —— LUT の総当たり")
    lut = np.array([0, 0, 1, 2, 2])
    cls = np.asarray(L.classify_image_class_lut(f1, lut))
    want = lut[np.clip(np.round(f1 * 4).astype(int), 0, 4)]
    assert np.array_equal(cls, want)
    print("   一致 %d / %d 画素" % (int((cls == want).sum()), H * W))
    out["classify_image_class_lut"] = sorted(np.unique(cls).tolist())

    print("6) expand_gray —— 種から平坦な島へ(穴は入らない)")
    im = rng.random((H, W))
    im[6:18, 6:30] = 0.5 + rng.normal(0, 0.01, (12, 24))
    im[11:13, 16:18] = 0.95
    seed = np.zeros((H, W), bool)
    seed[8:10, 8:10] = True
    grown = np.asarray(L.expand_gray(im, seed, tol=0.05))
    cand = (np.abs(im - im[seed].mean()) < 0.05) | seed
    cc, _n = ndimage.label(cand)
    want = np.isin(cc, np.unique(cc[seed])) & (cc > 0)
    assert np.array_equal(grown, want) and not grown[11:13, 16:18].any()
    print("   真値 %d 画素 / 実測 %d 画素" % (want.sum(), grown.sum()))
    out["expand_gray"] = int(grown.sum())

    print("7) regiongrowing_n —— 階段状では連結成分ラベリングと同じ分割")
    rg = np.asarray(L.regiongrowing_n([f1, f2], tol=0.05))
    key = np.round(f1 * 10).astype(int) * 100 + np.round(f2 * 10).astype(int)
    want = np.zeros((H, W), int)
    nxt = 0
    for v in np.unique(key):
        c, n = ndimage.label(key == v)
        want[c > 0] = c[c > 0] + nxt
        nxt += n
    assert _same_partition(rg, want)
    print("   領域数: 真値 %d / 実測 %d" % (nxt, len(np.unique(rg))))
    out["regiongrowing_n"] = int(len(np.unique(rg)))

    print("8) watersheds_marker —— 尾根で割れる")
    yy, xx = np.mgrid[0:H, 0:W]
    valley = -np.abs(xx - 18).astype(float)
    mk = np.zeros((H, W), int)
    mk[H // 2, 3] = 1
    mk[H // 2, W - 4] = 2
    ws = np.asarray(L.watersheds_marker(valley, mk))
    assert (ws[:, :18] == 1).all() and (ws[:, 19:] == 2).all()
    print("   左 %d 画素 = 1 / 右 %d 画素 = 2(尾根の列 18 はどちらか)" % (int((ws == 1).sum()), int((ws == 2).sum())))
    out["watersheds_marker"] = sorted(np.unique(ws).tolist())

    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  halcon_segmentation_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
