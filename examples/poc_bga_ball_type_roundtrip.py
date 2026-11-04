# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: BGA の半田ボールの高さ画像を、画像 → 点 → 点群 → ガウシアン → 体積 → メッシュ / グラフと
渡り歩いて、また画像へ戻す —— 型を変えても保たれるべき量で、変換の嘘を数値で弾く。

    PYTHONPATH=. py -3.11 examples/poc_bga_ball_type_roundtrip.py

収蔵番号 2026.299。

基板に載った 2 個の BGA パッケージ(各 6 x 6、ピッチ 10 px、ボール半径 3.2 px)を上から測った
高さ画像を**合成で**作る(真値 = 置いたボールの中心と半径そのもの)。パッケージ A の 1 個は
**欠けている**(14 番、実装不良の想定)。ボールの中心は ±0.3 px だけ格子から揺らしてある。

1 本の鎖で、表現変換(reprconv)の op 29 個と、その前後の既存 op 8 個を通す:

    高さ画像 ─ keypoints_from_image2d ─> keypoints ─ keypoints_uv_to_points ─> 点群
       ^                                   │                                    │
       └── keypoints_to_image2d <──────────┘          points_to_gaussians ──────┤
                                                       gaussians_to_voxel ─> 体積 ─ voxel_to_mesh ─> メッシュ
    点群 ─ knn_graph ─ knn_graph_to_conn_graph ─> 連結グラフ ─ graph_components ─> ラベル ─> 添字 ─> 部分点群
    体積 2 つ ─ correlation_score ─> スコア ─ score_to_position / score_to_image2d ─> 位置 / 画像 ─> keypoints

門は「往復して戻るか」と「型を変えても保たれるべき量」(数字はすべてこの実行で測ったもの):

1. **個数の保存**: 置いた 71 個を、keypoints(画像の連結成分)・メッシュのオイラー標数
   (球 1 個 = χ 2、合計 142)・グラフの頂点数の 3 つの独立な型で数え、全部 71 になる。
2. **画素の往復**: 整数位置の応答画像 → keypoints → 画像は**画素ごとに bit 一致**。
   (row, col) ↔ (u, v)、keypoints ↔ 点群(z を渡した向き)も bit 一致。落ちる z の RMS(3.19 px)を出す。
3. **質量の保存(閉形式)**: 点 → ガウシアン(重み 1/N)→ 体積は、6σ 打ち切りで総和
   1 − 1.4e-10(閉形式 1、誤差の上限 1e-8)。3σ では 0.99911 —— 軸並行の箱の極限
   erf(3/√2)³ = 0.99192 より**大きい**(floor/ceil で箱が最大 1 voxel 外へ広がるため。隠さない)。
4. **既知のずれ(閉形式)**: 2 回目の検査を (dz, dy, dx) = (2, −3, 5) voxel ずらすと、
   散在フローの速さは √38 = 6.164414 に一致、2 つの体積の循環相関のピークは**厳密に** (2, 93, 5)
   = (2, −3, 5) mod 形 に立つ。ずらした点から作った体積は元の体積の整数ずらしと
   max|Δ| 2e-19 で一致するので、ピーク値も丸めの範囲で 1(異常に良いのは、そう作ったから)。最大値投影の画像 → keypoints でも同じ (u, v)。
5. **体積(閉形式)**: ガウシアンの等値面は半径 σ√(2 ln(A/c)) の球なので、71 個の球の体積の和が
   真値。marching cubes のメッシュの体積は刻み 1 / 0.5 / 0.25 voxel で −1.20 % / −0.22 % / −0.020 %
   と真値へ収束する(刻みを半分にするたび誤差が 3 倍以上縮む = 細かくしたら合う、の確認)。
6. **位相(連結成分)**: 4 近傍グラフは 2 パッケージ = **2 成分**。ラプラシアンの 0 固有値の数
   (独立な計算)も 2。成分の大きさは欠けを映して (35, 36)。成分 → 添字 → 部分点群 → 重心は、
   置いたボールの中心の平均と 0.02 px 以内で一致。
7. **1 個を拡大した高さ画像**(半径 40 px): 推定法線は球の解析法線と最大 3.7 度で一致、
   方位・仰角との往復は 1e-12 以下、拡張ガウス像の総和は法線の本数と**厳密に**一致。
   主曲率 × R の中央値は 1.001(真値 1)、形状指数の中央値は 0.9999(球の帽子 = +1)。

★★**黙って間違う経路を 1 つ実測する**: ``depth_to_organized_points`` → ``pointmap_to_points``
の点群は列が **(x, y, z)**、``points_zyx_to_keypoints_uv`` が期待するのは **(z, y, x)**。
そのまま繋ぐと**例外も NaN も出ず**、高さを列番号と読んで、15360 画素が左端の 4 列に積もる。
列を反転して渡せば、全画素がちょうど 1 回ずつ落ちる(計数画像が全部 1)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import opsreprconv  # noqa: E402

L = fs.ledger
R = opsreprconv.call          # 表現変換の台帳の op を、宣言された出力型のまま呼ぶ
FAIL = []
ACCESSION = "2026.299"

H, W = 96, 160                # 高さ画像 [px]
PITCH = 10.0                  # ボールのピッチ [px]
BALL_R = 3.2                  # ボールの半径 [px]
PACKAGES = ((18.0, 15.0), (18.0, 90.0))   # 各パッケージの左上ボールの (row, col)。ずらしても 6σ の箱が縁で切れない
MISSING = 14                  # パッケージ A で欠けているボールの番号
SHIFT = (2, -3, 5)            # 2 回目の検査のずれ (dz, dy, dx) [voxel]
GRID_SHAPE = (32, H, W)       # 体積の形 (D, H, W)、刻み 1
GRID_ORIGIN = (-12.0, 0.0, 0.0)  # 6σ の箱が z の上下どちらにも切れない(ずらした後も)


def check(ok, label, detail=""):
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))
    if not ok:
        FAIL.append(label)


def meaningful(a):
    """空・定数・非有限でないこと(「走った」と「意味のある値が出た」を分ける)。"""
    a = np.asarray(a, dtype=float)
    return a.size > 0 and bool(np.all(np.isfinite(a))) and float(np.ptp(a)) > 0.0


def board(seed=2026):
    """2 パッケージの BGA の高さ画像と、置いたボールの真値。"""
    rng = np.random.default_rng(seed)
    rc, pkg = [], []
    for p, (r0, c0) in enumerate(PACKAGES):
        for i in range(6):
            for j in range(6):
                rc.append((r0 + i * PITCH + rng.uniform(-0.3, 0.3),
                           c0 + j * PITCH + rng.uniform(-0.3, 0.3)))
                pkg.append(p)
    rc, pkg = np.array(rc), np.array(pkg)
    keep = np.ones(len(rc), bool)
    keep[MISSING] = False
    rc, pkg = rc[keep], pkg[keep]
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    hm = np.zeros((H, W))
    for r, c in rc:
        hm = np.maximum(hm, np.sqrt(np.clip(BALL_R ** 2 - (yy - r) ** 2 - (xx - c) ** 2, 0.0, None)))
    return {"height": hm, "rowcol": rc, "package": pkg}


def mesh_euler(faces, n_verts):
    """三角形メッシュのオイラー標数 χ = V − E + F。"""
    f = np.asarray(faces, np.int64)
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [0, 2]]]), axis=1)
    return int(n_verts - len(np.unique(e, axis=0)) + len(f))


def nearest(a, b):
    """a の各行に最も近い b の行までの距離。"""
    from scipy.spatial import cKDTree
    d, j = cKDTree(b).query(a)
    return d, j


def main():
    t0 = time.time()
    print("=" * 76)
    print("PoC: BGA の半田ボールを、画像 → 点 → 点群 → 体積 → メッシュ / グラフ → 画像と渡す")
    print("=" * 76)
    b = board()
    hm, rc, pkg = b["height"], b["rowcol"], b["package"]
    n_true = len(rc)
    print("  置いたボール %d 個(2 x 36 − 欠け 1)、高さ画像 %d x %d、最大高さ %.2f px"
          % (n_true, H, W, hm.max()))
    check(meaningful(hm), "高さ画像が空・定数・非有限でない")

    # ---------------------------------------------------------------- [1]
    print("\n[1] 画像 → keypoints → 画像(画素の往復)")
    kp = R("keypoints_from_image2d", hm, threshold=0.0)
    uv_true = R("keypoints_rowcol_to_uv", rc)
    d, _ = nearest(uv_true, kp)
    check(len(kp) == n_true, "keypoints の個数 = 置いた数", "(%d / %d)" % (len(kp), n_true))
    check(float(d.max()) < 0.1, "重心と置いた中心の差(最大)< 0.1 px",
          "(最大 %.4f、RMS %.4f px)" % (d.max(), math.sqrt(float((d ** 2).mean()))))
    check(np.array_equal(R("keypoints_uv_to_rowcol", uv_true), rc),
          "(row, col) → (u, v) → (row, col) が bit 一致")
    kpi = np.rint(uv_true)
    impulse = R("keypoints_to_image2d", kpi, shape=(H, W))
    kp_back = R("keypoints_from_image2d", impulse)
    impulse_back = R("keypoints_to_image2d", kp_back, shape=(H, W))
    check(float(impulse.sum()) == n_true and np.array_equal(impulse, impulse_back),
          "整数位置の応答画像 → keypoints → 画像が画素ごとに bit 一致",
          "(総和 %d)" % int(impulse_back.sum()))
    check(np.array_equal(np.sort(kp_back, axis=0), np.sort(kpi, axis=0)),
          "keypoints → 画像 → keypoints が bit 一致(整数位置)")

    # ---------------------------------------------------------------- [2]
    print("\n[2] keypoints → 点群(z = 高さ)→ keypoints、高さ画像 → pointmap → 点群")
    z = hm[np.rint(kp[:, 1]).astype(int), np.rint(kp[:, 0]).astype(int)]
    pts = R("keypoints_uv_to_points", kp, z=z)
    check(np.array_equal(R("points_zyx_to_keypoints_uv", pts), kp),
          "keypoints → 点群 → keypoints が bit 一致", "(落ちる z の RMS %.2f px)"
          % math.sqrt(float((z ** 2).mean())))
    check(meaningful(pts[:, 1]) and meaningful(pts[:, 2]) and float(z.min()) > 0.9 * BALL_R,
          "点群の z はボールの頂(半径 3.2 px)近く", "(z 最小 %.3f)" % z.min())
    pmap_pts = R("pointmap_to_points", L.depth_to_organized_points(hm))
    check(pmap_pts.shape == (H * W, 3), "pointmap → 点群の点数 = 画素数", "(%d)" % len(pmap_pts))
    naive_err = None
    try:
        naive = R("keypoints_to_image2d", R("points_zyx_to_keypoints_uv", pmap_pts), shape=(H, W))
    except ValueError as exc:
        naive, naive_err = None, str(exc)
    flipped = pmap_pts[:, ::-1]                        # (x, y, z) -> (z, y, x)
    right = R("keypoints_to_image2d", R("points_zyx_to_keypoints_uv", flipped), shape=(H, W))
    check(np.array_equal(right, np.ones((H, W))),
          "列を (z, y, x) に直せば全画素がちょうど 1 回ずつ落ちる(計数画像が全部 1)")
    check(np.array_equal(flipped[:, 0].reshape(H, W), hm), "点群の z を並べ直すと高さ画像に bit 一致")
    naive_cols = 0 if naive is None else int(np.count_nonzero(naive.sum(axis=0)))
    check(naive_err is None and naive is not None and naive_cols <= 4
          and float(naive.sum()) == H * W,
          "★(x, y, z) のまま繋ぐと例外なしに間違う(実測の記録)",
          "(%d 画素が左端の %d 列に積もる)" % (H * W, naive_cols))

    # ---------------------------------------------------------------- [3]
    print("\n[3] 点群 → ガウシアン → 点群 / 体積(質量の保存)")
    g = R("points_to_gaussians", pts, k=4, scale=0.15)
    check(np.array_equal(R("gaussians_to_points", g), pts), "ガウシアン → 中心の点群が bit 一致")
    check(len(g["mu"]) == n_true and bool(np.all(g["w"] == 1.0 / n_true))
          and abs(float(g["w"].sum()) - 1.0) < 1e-12,
          "ガウシアンの個数 = 置いた数、重みは 1/N", "(σ %.3f〜%.3f px)"
          % (g["sigma"].min(), g["sigma"].max()))
    vox6 = R("gaussians_to_voxel", g, shape=GRID_SHAPE, origin=GRID_ORIGIN, truncate=6.0)
    vox3 = R("gaussians_to_voxel", g, shape=GRID_SHAPE, origin=GRID_ORIGIN, truncate=3.0)
    box = math.erf(3.0 / math.sqrt(2.0)) ** 3
    check(meaningful(vox6) and abs(float(vox6.sum()) - 1.0) < 1e-8,
          "6σ 打ち切りの総和 = 1(閉形式)", "(1 − %.1e)" % (1.0 - vox6.sum()))
    check(box < float(vox3.sum()) < 1.0,
          "3σ 打ち切りの総和は箱の極限 erf(3/√2)³ と 1 の間",
          "(%.5f、極限 %.5f)" % (vox3.sum(), box))

    # ---------------------------------------------------------------- [4]
    print("\n[4] 2 回目の検査: 既知のずれ (dz, dy, dx) = %s voxel" % (SHIFT,))
    flow = np.tile(np.array(SHIFT, float), (len(pts), 1))
    pts_b = R("flow_apply", pts, flow)
    speed = R("flow_speed", flow)
    check(np.array_equal(pts_b, pts + np.array(SHIFT, float)), "散在フローを当てた点群 = 点群 + ずれ")
    check(float(np.abs(speed - math.sqrt(38.0)).max()) < 1e-12, "フローの速さ = √38",
          "(%.6f)" % speed[0])
    vox_b = R("gaussians_to_voxel", dict(g, mu=pts_b), shape=GRID_SHAPE, origin=GRID_ORIGIN,
              truncate=6.0)
    roll_err = float(np.abs(np.roll(vox6, SHIFT, axis=(0, 1, 2)) - vox_b).max())
    check(roll_err < 1e-9 * float(vox6.max()), "ずらした点の体積 = 体積を整数ずらし(格子に乗る)",
          "(max|Δ| %.1e、最大値 %.2e)" % (roll_err, vox6.max()))
    score = R("correlation_score", vox6, vox_b)
    pos = R("score_to_position", score)
    want = tuple(float(v) for v in np.mod(SHIFT, GRID_SHAPE))
    check(pos == want and float(score.max()) > 1.0 - 1e-9,
          "相関のピーク = ずれ(mod 形)", "(位置 %s、ピーク 1 − %.1e)" % (pos, 1.0 - score.max()))
    shift = R("vector_to_shift", np.array(pos))
    signed = tuple(int(s - n) if s > n // 2 else int(s) for s, n in zip(shift, GRID_SHAPE))
    check(signed == SHIFT and np.array_equal(R("shift_to_vector", shift), np.array(pos)),
          "位置 → 整数シフト → ベクトルの往復と、符号つきのずれ", "(%s)" % (signed,))
    mip = R("score_to_image2d", score, axis=0)
    check(float(mip.max()) == float(score.max()) and meaningful(mip), "最大値投影の最大 = スコアの最大")
    peak_kp = R("keypoints_from_image2d", mip, threshold=0.99 * float(mip.max()))
    check(len(peak_kp) == 1 and float(np.hypot(*(peak_kp[0] - (want[2], want[1])))) < 0.5,
          "最大値投影 → keypoints はピーク 1 個、(u, v) = (dx, dy mod H)",
          "(%d 個、(%.2f, %.2f))" % (len(peak_kp), peak_kp[0][0], peak_kp[0][1]))

    # ---------------------------------------------------------------- [5]
    print("\n[5] 体積 → メッシュ(位相と体積、閉形式)")
    amp = g["w"] / ((2.0 * np.pi) ** 1.5 * g["sigma"] ** 3)     # 各ガウシアンの頂の密度
    iso = 0.25 * float(amp.min())
    radius = g["sigma"] * np.sqrt(2.0 * np.log(amp / iso))
    v_true = float((4.0 / 3.0 * np.pi * radius ** 3).sum())
    errs, chi = [], None
    for h in (1.0, 0.5, 0.25):
        shp = tuple(int(round(n / h)) for n in GRID_SHAPE)
        vol = R("gaussians_to_voxel", g, shape=shp, origin=GRID_ORIGIN, spacing=(h, h, h),
                truncate=6.0)
        verts, faces = L.voxel_to_mesh(vol, iso=iso * h ** 3)
        if h == 1.0:
            chi = mesh_euler(faces, len(verts))
        errs.append((abs(L.mesh_volume((verts, faces))) * h ** 3 - v_true) / v_true)
        print("    刻み %.2f voxel: メッシュの体積の相対誤差 %+.4f %%" % (h, 100.0 * errs[-1]))
    check(chi == 2 * n_true, "メッシュのオイラー標数 = 2 × 個数(閉じた球が 1 個ずつ)",
          "(χ %d = 2 × %d)" % (chi, n_true))
    check(abs(errs[-1]) < 1e-3 and all(abs(a) > 3.0 * abs(b) for a, b in zip(errs, errs[1:])),
          "メッシュの体積が閉形式の球の和へ収束(半分の刻みで 3 倍以上縮む)",
          "(真値 %.1f px³)" % v_true)

    # ---------------------------------------------------------------- [6]
    print("\n[6] 点群 → k 近傍グラフ → 連結グラフ(位相)→ 添字 → 部分点群")
    idx, dist = L.knn_graph(pts, k=4)
    graph = R("knn_graph_to_conn_graph", (idx, dist), weight="binary")
    comp = L.graph_components(graph)
    spec = L.graph_laplacian_spectrum(graph)
    sizes = tuple(sorted(np.bincount(comp).tolist()))
    zeros = int(np.count_nonzero(np.abs(spec) < 1e-9))
    check(graph.shape == (n_true, n_true) and int(comp.max()) + 1 == 2 and zeros == 2,
          "連結成分 = 2 パッケージ、ラプラシアンの 0 固有値も 2", "(成分 %d、0 固有値 %d)"
          % (int(comp.max()) + 1, zeros))
    check(sizes == (35, 36), "成分の大きさが欠けを映す", "(%s)" % (sizes,))
    small = int(np.argmin(np.bincount(comp)))
    sel = R("labels_to_indices", (comp == small).astype(np.int64))
    labels = R("indices_to_labels", sel)
    check(np.array_equal(R("labels_to_indices", labels), sel), "添字 → ラベル → 添字が bit 一致")
    cen = R("points_to_position", R("select_points", pts, sel))
    _, j = nearest(kp[sel], uv_true)
    truth_c = rc[j].mean(axis=0)
    err_c = float(np.hypot(cen[1] - truth_c[0], cen[2] - truth_c[1]))
    check(err_c < 0.02 and bool(np.all(pkg[j] == pkg[j][0])),
          "欠けのある成分の重心 = 置いた中心の平均", "(差 %.4f px)" % err_c)
    check(np.array_equal(R("position_to_points", cen)[0], np.array(cen)),
          "位置 → 1 点の点群 → 位置が bit 一致")

    # ---------------------------------------------------------------- [7]
    print("\n[7] 1 個を拡大した高さ画像(半径 40 px): 法線と曲率")
    rz, nz, cz = 40.0, 101, 50.0
    yy, xx = np.mgrid[0:nz, 0:nz].astype(float)
    hz = np.sqrt(np.clip(rz ** 2 - (yy - cz) ** 2 - (xx - cz) ** 2, 0.0, None))
    cap = R("pointmap_to_points", L.depth_to_organized_points(hz))          # (x, y, z)
    cap = cap[(cap[:, 0] - cz) ** 2 + (cap[:, 1] - cz) ** 2 < (0.8 * rz) ** 2]
    nrm = L.estimate_normals(cap, k=25)
    truth_n = np.c_[cap[:, 0] - cz, cap[:, 1] - cz, cap[:, 2]] / rz
    ang = np.degrees(np.arccos(np.clip(np.abs((nrm * truth_n).sum(axis=1)), -1.0, 1.0)))
    check(len(cap) > 3000 and float(ang.max()) < 5.0,
          "推定法線と球の解析法線の差 < 5 度", "(%d 点、最大 %.2f、中央 %.2f 度)"
          % (len(cap), ang.max(), np.median(ang)))
    unit = nrm / np.linalg.norm(nrm, axis=1)[:, None]
    rt = float(np.abs(R("angles_to_normals", R("normals_to_angles", nrm)) - unit).max())
    check(rt < 1e-12, "法線 → 方位・仰角 → 法線の往復", "(max|Δ| %.1e)" % rt)
    egi = R("normals_to_egi", nrm)
    check(float(egi.sum()) == len(nrm) and meaningful(egi),
          "拡張ガウス像の総和 = 法線の本数(方向の計数の保存)", "(%d)" % int(egi.sum()))
    k1, k2 = L.principal_curvatures(cap, k=25)
    si = R("curvature_to_shape_index", (k1, k2))
    back = R("shape_index_to_curvature", si)
    kk = np.c_[np.maximum(k1, k2), np.minimum(k1, k2)]
    check(abs(float(np.median(kk[:, 0])) * rz - 1.0) < 0.01
          and abs(float(np.median(kk[:, 1])) * rz - 1.0) < 0.01,
          "主曲率 × R の中央値 = 1(半径 R の球)", "(%.4f, %.4f)"
          % (np.median(kk[:, 0]) * rz, np.median(kk[:, 1]) * rz))
    check(float(np.median(si[:, 0])) > 0.99 and float(np.abs(back - kk).max()) < 1e-12,
          "形状指数の中央値 ≈ +1(帽子)、曲率との往復", "(S %.4f、max|Δ| %.1e)"
          % (np.median(si[:, 0]), np.abs(back - kk).max()))
    tab = R("curvature_to_table", (k1, k2))
    check(abs(float(tab["p50"]) * rz - 1.0) < 0.01 and int(tab["n"]) == len(cap),
          "曲率の表の中央値 × R = 1、件数 = 点数", "(%.4f)" % (tab["p50"] * rz))

    used = sorted({"keypoints_from_image2d", "keypoints_to_image2d", "keypoints_rowcol_to_uv",
                   "keypoints_uv_to_rowcol", "keypoints_uv_to_points", "points_zyx_to_keypoints_uv",
                   "pointmap_to_points", "points_to_gaussians", "gaussians_to_points",
                   "gaussians_to_voxel", "flow_apply", "flow_speed", "correlation_score",
                   "score_to_position", "score_to_image2d", "vector_to_shift", "shift_to_vector",
                   "knn_graph_to_conn_graph", "labels_to_indices", "indices_to_labels",
                   "select_points", "points_to_position", "position_to_points",
                   "normals_to_angles", "angles_to_normals", "normals_to_egi",
                   "curvature_to_shape_index", "shape_index_to_curvature", "curvature_to_table"})
    unknown = [n for n in used if n not in opsreprconv.OPSREPRCONV]
    check(not unknown and len(used) == 29, "使った表現変換の op が台帳に全部ある",
          "(%d / %d op)" % (len(used), len(opsreprconv.OPSREPRCONV)))

    if figs.enabled():
        figs.save_grid("bga_types", [hm, impulse_back, mip,
                                    naive if naive is not None else np.zeros((H, W))],
                       ["高さ画像(71 個、欠け 1)", "keypoints → 画像(71 画素)",
                        "相関スコアの最大値投影(ピーク = ずれ)",
                        "(x, y, z) のまま渡すと左端 4 列に積もる"],
                       ncols=2, title="BGA の型を渡り歩いて戻る", colorbar=True,
                       caption="同じボールを画像・keypoints・体積・スコアで見る。右下は軸の流儀を取り違えた計数画像。")
        figs.save_table("bga_mesh_volume", ["刻み [voxel]", "相対誤差 [%]"],
                        [["%.2f" % h, "%+.4f" % (100.0 * e)] for h, e in zip((1.0, 0.5, 0.25), errs)],
                        title="メッシュの体積 vs 閉形式", col_w=170)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\n%.1f 秒。" % (time.time() - t0))
    if FAIL:
        print("FAIL: %s" % FAIL)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
