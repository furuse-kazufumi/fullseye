---
op: icp_point2plane
dim: 3d
category: refine
in: points × points × normals
out: pose
examples: [refinement]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# icp_point2plane — 3D `refine` op

- **データ種**: `points × points × normals` → `pose`
- **呼び出し**: `import fullseye as fs; fs.ledger.icp_point2plane(src, dst, dst_normals, iters=30, tol=1e-09, init=None, trim=None, device='cpu')` (実装を直接呼ぶなら `import match3d; match3d.icp_point2plane(src, dst, dst_normals, iters=30, tol=1e-09, init=None, trim=None, device='cpu')`、台帳から引くなら `ops3d.get("icp_point2plane")`)

## 使い方

点-面 ICP(Gauss-Newton, 小角近似)で剛体変換を高精度に精緻化する。

粗マッチ(整数 NCC / Fourier-Mellin ±3° / Hough ±0.5voxel)の初期姿勢を
表面点群の点-面距離最小化で締め上げる精緻化手法。各反復で src 各点の dst
最近傍を対応付け、**点-面残差** ``r_i = n_i·(R·p_i + t - q_i)`` を最小化する。
R を小角近似 ``R ≈ I + [ω]×`` で線形化すると各対応のヤコビアンは
``J_i = [p_i×n_i | n_i]``(スカラー三重積 ``n·(ω×p)=ω·(p×n)`` より)、
定数項 ``b_i = -n_i·(p_i - q_i)``。正規方程式 ``(JᵀJ)x = Jᵀb`` を 6×6 で
解いて増分 ``x=[ω|t]`` を得、Rodrigues で回転に戻して累積する。点-面は
接平面内の滑りを許すため、point-to-point より少ない反復で表面にタイトに
収束する(Low 2004)。

実測(波打つ表面 N=2025, CPU float64): 初期6°/並進0.06 を 4 反復で euclid
RMSE 1.7e-16・回転誤差 0° に回復(point-to-point は 17 反復で RMSE 4e-2・
回転 1.9° 停滞)。初期角 3〜20° でも 4〜5 反復で機械精度。

引数:
    src (N,3): 動かす側の点群(粗マッチ後の初期姿勢)。
    dst (M,3): 参照側の点群(固定)。
    dst_normals (M,3): dst の単位法線(未正規化でも内部で正規化)。
                       未知なら pointcloud.estimate_normals(dst) 等で事前推定。
    iters: 最大反復数。
    tol: RMSE 変化がこの値未満で収束打ち切り。
    init ((R0,t0)): 初期姿勢(粗マッチの R,t を渡す)。None なら単位。
    trim (float|None): [0,1) の割合。点-面残差の大きい上位を毎反復捨てる
                       Trimmed ICP(部分重なり・外れ値に頑健)。
    device: "cpu"/"cuda" 等。torch device 文字列(device 非依存)。

返り値:
    R (3,3), t (3,), aligned (N,3)=R·src+t, rmse(採用点の点-面 RMSE),
    n_iter(実反復数)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [refinement](../../../../examples_3d/refinement.py) — `py -3.11 examples_3d/refinement.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`refine`)

[refine_peak_newton](refine_peak_newton.md) · [refine_translation_lk](refine_translation_lk.md) · [refine_lm](refine_lm.md) · [refine_rotation_z](refine_rotation_z.md) · [icp_point2point_3d](icp_point2point_3d.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
