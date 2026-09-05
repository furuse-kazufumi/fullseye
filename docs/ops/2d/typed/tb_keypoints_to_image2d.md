---
op: tb_keypoints_to_image2d
dim: 2d
category: typed
in: keypoints
out: image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# tb_keypoints_to_image2d — 2D `typed` op

- **データ種**: `keypoints` → `image`
- **呼び出し**: `fullseye.apply(img, "tb_keypoints_to_image2d", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

画像座標 ``(N,2) = (u, v)`` → 計数画像 ``(H, W)``。``keypoints`` の 2 つ目の出口。

    ``round(v)`` を行、``round(u)`` を列として 1 ずつ加算する。**画素格子への
    量子化が損失**で、:func:`keypoints_from_image2d` と往復すると位置が
    最大 0.5 画素ずれる(よく離れた 225 点での実測: **軸あたり** RMS 0.2835 px =
    一様量子化の理論値 1/sqrt(12) = 0.2887 と一致。2-D 距離では sqrt(2) 倍の
    0.4009 px で、理論 sqrt(2/12) = 0.4082)。
    ★ここも一度間違えた: 2-D 距離の実測を 1-D の理論値と並べて「0.29 のはずが
    0.40 だ」と読みかけた —— 軸ごとの量と距離の量を混ぜると、正しい実装が
    誤っているように見える。
    近接した点は連結成分として融合するので、往復で点数も減りうる
    (実測: 60 点をランダムに置くと 54 点)。

    範囲外の点は**黙って捨てない** —— 捨てると「検出が減った」のか
    「画像が小さすぎた」のかが区別できなくなる。

    Args:
        keypoints: (N, 2) の (u, v)。
        shape: (H, W)。
    Returns:
        (H, W) float64 の計数画像。
    Raises:
        ValueError: 形状不正 / 非有限 / 範囲外の点がある / shape が上限超。

2-D 進化レジストリへ橋渡しした reprconv の op ``keypoints_to_image2d``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。この op に調整点は無く、``a`` も ``b`` も使われない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
