# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""type_connectivity_tour — 行き止まりだった型と入口の無かった型を、本物の産み手からの鎖で通す。

    py -3.11 examples/type_connectivity_tour.py

【この例が解く問題】
Fullseye の op は入力の型と出力の型で鎖を組む。2026-11-03 に全 101 型を数え直すと、
**作られるのに誰も受けない型**(gradient / hessian / frame / graph / pointmap / match)と、
**受ける op はあるのに誰も作らない型**(positions / synapse_table / jones の最初の 1 本)、
**表にも絵にも出られない型**(tokens)が残っていた。そこで止まる鎖は、AI が型だけを
頼りに組むと「次の op が無い」で終わる。``reprconv`` に足した 12 op でそれぞれを
既存の語彙へつなぎ、**本物の産み手の返り**を入れて真値と比べる。

各鎖(左が既存の産み手、→ の先が今回足した op、その先が既存の受け手):

1. ``gradient3d`` / ``sobel3d`` → ``gradient_magnitude``: 傾き (2, 3, −1) の一次関数で |∇| = √14。
   sobel3d の利得 32 を割り忘れると 32 倍に出る。
2. ``gradient3d`` → ``gradient_coherence``: 層状の体積で 1、乱数で 0.5 未満。
3. ``hessian3d`` → ``hessian_determinant``: 二次形式 ½xᵀAx の det H = det A。
4. ``hessian3d`` → ``hessian_vesselness``: 管で高く、球で低い(Frangi 1998)。
5. ``frenet_frame`` → ``frame_axis`` → ``normals_to_angles``: つる巻き線の接線は閉形式。
6. ``knn_graph`` → ``knn_graph_to_conn_graph`` → ``graph_components``: 離れた 2 塊は 2 成分。
7. ``depth_to_organized_points`` → ``pointmap_to_points``: ``depth_to_points`` と同じ点が同じ順。
8. ``area_center`` → ``match_component``: 4×10 の矩形で面積 40。
9. ``find_peaks`` → ``indices_to_positions`` → ``point_spectrum``: 0.1 m おきの事象で 10 /m。
10. ``table_read_csv`` → ``synapse_table_from_table`` → ``graph_from_synapses``: 重みが CSV の和。
11. ``jones_state`` → ``jones_apply``(偏光板 60 度)→ 強度 cos²60° = 0.25(Malus)。
12. ``attention_softmax`` → ``tokens_to_matrix`` → ``mat_cond``: 行列の op へ出られる。
13. ``vx_sobel3x3``(table)→ ``table_field_image2d`` ×2 → ``vx_magnitude``。
14. ``spectrum``(pairs)→ ``pairs_peak_x``: 123.5 Hz の正弦波の主周波数。
15. ``(row, col)`` の点 → ``keypoints_rowcol_to_uv`` → ``dlt_pose``: 鏡に映らない姿勢。
16. ``dlt_pose`` の (R, t) → ``pose_to_matrix``: 4×4。

【グラウンドトゥルース】20 項目、すべて閉形式か既存 op との一致。どれか 1 つでも外れたら
exit 1(数値は毎回印字する)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import conngraph            # noqa: E402
import curve3d              # noqa: E402
import dsp                  # noqa: E402
import edges3d              # noqa: E402
import geodesic3d           # noqa: E402
import llmcore              # noqa: E402
import match3d              # noqa: E402
import ops                  # noqa: E402
import optics               # noqa: E402
import range_image          # noqa: E402
import reprconv as R        # noqa: E402

FAILED: list[str] = []
CHECKED: list[str] = []


def check(label: str, got: float, want: float, tol: float) -> None:
    ok = abs(got - want) <= tol
    CHECKED.append(label)
    print(f"  {'ok ' if ok else 'NG '} {label:58s} {got: .6g}  (真値 {want:.6g}, 許容 {tol:g})")
    if not ok:
        FAILED.append(label)


def main() -> int:
    z, y, x = np.mgrid[0:14, 0:14, 0:14].astype(float)
    inner = (slice(3, -3),) * 3

    print("1-2. gradient → voxel")
    ramp = 2 * z + 3 * y - x
    check("gradient3d → gradient_magnitude(一次関数)",
          float(R.gradient_magnitude(edges3d.gradient3d(ramp, sigma=0))[inner].mean()), np.sqrt(14), 1e-9)
    check("sobel3d → gradient_magnitude(利得 32 を割る)",
          float(R.gradient_magnitude(match3d.sobel3d(ramp))[inner].mean()), np.sqrt(14), 1e-4)
    check("gradient_coherence(層状、面らしさ 1)",
          float(R.gradient_coherence(edges3d.gradient3d(np.sin(0.8 * z), 1.0))[inner].mean()), 1.0, 1e-3)
    noise = np.random.default_rng(0).random(z.shape)
    c_noise = float(R.gradient_coherence(edges3d.gradient3d(noise, 1.0))[inner].mean())
    print(f"      gradient_coherence(乱数)= {c_noise:.3f}")
    check("乱数の面らしさは 0.5 未満(1 = 真)", float(c_noise < 0.5), 1.0, 0.0)

    print("3-4. hessian → voxel")
    A = np.array([[2.0, 0.5, 0.1], [0.5, -1.0, 0.3], [0.1, 0.3, 1.5]])
    P = np.stack([z, y, x], -1)
    q = 0.5 * np.einsum("...i,ij,...j->...", P, A, P)
    check("hessian3d → hessian_determinant(det A)",
          float(R.hessian_determinant(match3d.hessian3d(q))[inner].mean()), float(np.linalg.det(A)), 1e-3)
    tube = np.exp(-((y - 7) ** 2 + (x - 7) ** 2) / 4.0)
    blob = np.exp(-((z - 7) ** 2 + (y - 7) ** 2 + (x - 7) ** 2) / 4.0)
    vt = float(R.hessian_vesselness(match3d.hessian3d(tube))[7, 7, 7])
    vb = float(R.hessian_vesselness(match3d.hessian3d(blob))[7, 7, 7])
    print(f"      hessian_vesselness 中心: 管 {vt:.3f} / 球 {vb:.3f}")
    check("管 − 球(管の方が高い = 正)", float(vt - vb > 0.4), 1.0, 0.0)

    print("5. frame → normals")
    t = np.linspace(0, 4 * np.pi, 400)
    helix = np.stack([np.cos(t), np.sin(t), 0.3 * t], 1)
    T = R.frame_axis(curve3d.frenet_frame(helix), "tangent")
    check("frame_axis(接線の z 成分 = c/√(a²+c²))", float(T[200, 2]), 0.3 / np.hypot(1.0, 0.3), 1e-3)
    az_el = R.normals_to_angles(T)
    check("→ normals_to_angles(仰角は一定)", float(np.ptp(az_el[5:-5, 1])), 0.0, 1e-2)

    print("6. graph → conn_graph")
    rng = np.random.default_rng(1)
    pts = np.concatenate([rng.random((40, 3)), rng.random((40, 3)) + 10.0])
    W = R.knn_graph_to_conn_graph(geodesic3d.knn_graph(pts, 5))
    check("→ graph_components(離れた 2 塊)", float(len(np.unique(conngraph.graph_components(W)))), 2.0, 0.0)

    print("7. pointmap → points")
    depth = 1.0 + rng.random((9, 11))
    K = dict(fx=120.0, fy=110.0, cx=5.0, cy=4.0)
    got = R.pointmap_to_points(range_image.depth_to_organized_points(depth, **K), drop_nonpositive_z=True)
    check("pointmap_to_points vs depth_to_points(最大差)",
          float(np.abs(got - match3d.depth_to_points(depth, **K)).max()), 0.0, 1e-12)

    print("8. match → measurement")
    reg = np.zeros((20, 20))
    reg[5:9, 2:12] = 1.0
    check("area_center → match_component(面積)",
          R.match_component(ops.RT["area_center"](reg, 0.5, 0.5), 0), 40.0, 0.0)

    print("9. indices → positions → point_spectrum")
    sig = np.zeros(2000)
    sig[::25] = 1.0
    pos = R.indices_to_positions(dsp.find_peaks(sig), spacing=0.004)   # 25 標本 x 4 mm = 0.1 m おき
    sp = dsp.point_spectrum(pos, f_max=15.0)
    f, pw = np.asarray(sp["freq"]), np.asarray(sp["power"])
    check("point_spectrum のピーク [1/m]", float(f[np.argmax(pw * (f > 1.0))]), 10.0, 0.2)

    print("10. table → synapse_table → conn_graph")
    import fullseye as fs
    csv_text = ("pre,post,n\n# units:,id,id,count\n# source: synthetic\n"
                "# generated_at: 2026-11-03\n# coordinate_meaning: neuron ids\n"
                "0,1,3\n1,2,1\n2,0,2\n0,1,4\n")
    tab = fs.ledger.table_read_csv(csv_text)
    Wsyn = conngraph.graph_from_synapses(R.synapse_table_from_table(tab, count="n"))
    check("graph_from_synapses の W[0,1](3 + 4)", float(Wsyn[0, 1]), 7.0, 0.0)

    print("11. jones_state → jones_apply → Malus")
    out = optics.jones_apply(optics.jones_element("polarizer", angle_deg=60.0), R.jones_state(0.0, 0.0))
    check("偏光板 60 度を通った強度(cos² 60°)", float(np.sum(np.abs(out) ** 2)), 0.25, 1e-12)
    st = optics.stokes_analyze(optics.stokes_from_jones(R.jones_state(10.0, -15.0)))
    check("stokes_analyze で楕円率が戻る [度]", float(st["ellipticity_deg"]), -15.0, 1e-9)

    print("12. tokens → matrix")
    q_, k_, v_ = (np.random.default_rng(s).standard_normal((16, 8)) for s in (2, 3, 4))
    att = llmcore.attention_softmax(q_, k_, v_)
    M = R.tokens_to_matrix(att)
    check("tokens_to_matrix は値を変えない(最大差)", float(np.abs(M - att).max()), 0.0, 0.0)
    print(f"      → 注意の出力の条件数 {float(np.linalg.cond(M)):.3g}(matrix の op が掛かる)")

    print("13. table を返す op の欄 → 画像 / 行列(vx_sobel3x3 → vx_magnitude)")
    import vxcore
    img = (np.tile(np.arange(12.0), (10, 1)) * 10).astype(np.uint8)
    t = vxcore.vx_sobel3x3(img, border="replicate")
    mag = np.asarray(vxcore.vx_magnitude(R.table_field_image2d(t, "gx"), R.table_field_image2d(t, "gy")))
    check("vx_magnitude の中央(一定の横勾配で一定)", float(np.ptp(mag[2:-2, 2:-2])), 0.0, 0.0)

    print("14. spectrum → pairs_peak_x(主周波数)")
    xs = np.arange(1000) / 1000.0
    freqs, magn = dsp.spectrum(np.sin(2 * np.pi * 123.5 * xs), 1000.0)
    check("主周波数 [Hz](DC を除いて)", R.pairs_peak_x((freqs, magn), x_min=1.0), 123.5, 0.01)

    print("15. keypoints (row, col) → (u, v) → dlt_pose")
    import pnp3d
    P3 = np.random.default_rng(5).uniform(-0.5, 0.5, (12, 3))
    Kc = np.array([[800.0, 0, 320], [0, 800.0, 240], [0, 0, 1]])
    uvw = (Kc @ (P3 + [0.1, -0.05, 3.0]).T).T
    rowcol = (uvw[:, :2] / uvw[:, 2:])[:, ::-1]
    _Rm, t_est = pnp3d.dlt_pose(P3, R.keypoints_rowcol_to_uv(rowcol), Kc)
    check("dlt_pose の t_z(真値 3.0)", float(t_est[2]), 3.0, 1e-6)

    print("16. pose → 4x4")
    M4 = R.pose_to_matrix((np.eye(3), t_est))
    check("pose_to_matrix の右下", float(M4[3, 3]), 1.0, 0.0)

    print()
    if FAILED:
        print(f"NG {len(FAILED)} 件: {FAILED}")
        return 1
    print(f"20 op、{len(CHECKED)} の真値すべて一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
