---
op: tb_countrate_to_counts
dim: 2d
category: typed
in: counts
out: counts
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# tb_countrate_to_counts — 2D `typed` op

- **データ種**: `counts` → `counts`
- **呼び出し**: `fullseye.apply(img, "tb_countrate_to_counts", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

計数レート ``[Hz]`` → 計数 ``counts``。``countrate`` の出口(**可逆**)。

    **単位が変換の全内容**: ``[1/s] * [s] = [1]``。``gate_s`` は積算窓の秒数で、
    既定 1 ms。``counts`` は「時間 bin ごとの光子数」の型なので、レート列を
    そのまま counts と名乗らせると**桁が 7 つずれたまま黙って通る**
    (``TYPE_CHECKS`` はどちらも「非負の 1-D」としか見ていない)。

    :func:`counts_to_countrate` と往復して実測 max|Δ| = 9.3e-10(値域が 1e3-1e7 Hz なので
    **相対** 1e-16 = 倍精度の丸め 1 単位ぶん。絶対値だけ見ると大きく見えるので、
    レートのように桁が広い量は相対で言う)。

    Args:
        countrate: (N,) の非負レート [Hz]。
        gate_s: 積算窓 [s]。> 0。
    Returns:
        (N,) float64 の非負計数。
    Raises:
        ValueError: 負のレート / gate_s <= 0 / 形状不正 / 非有限。

2-D 進化レジストリへ橋渡しした reprconv の op ``countrate_to_counts``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``gate_s``(既定 0.001)を振る。``b`` は未使用。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`counts` を入力に取れる)

[identity](../misc/identity.md) · [tb_spad_deadtime_apply](tb_spad_deadtime_apply.md) · [tb_spad_deadtime_correct](tb_spad_deadtime_correct.md) · [tb_tcspc_coates_correct](tb_tcspc_coates_correct.md) · [tb_tcspc_irf_convolve](tb_tcspc_irf_convolve.md) · [tb_tcspc_background_subtract](tb_tcspc_background_subtract.md) · [tb_dtof_depth](tb_dtof_depth.md) · [tb_counts_to_countrate](tb_counts_to_countrate.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
