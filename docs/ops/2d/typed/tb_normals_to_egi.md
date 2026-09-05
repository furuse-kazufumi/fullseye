---
op: tb_normals_to_egi
dim: 2d
category: typed
in: points
out: image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# tb_normals_to_egi — 2D `typed` op

- **データ種**: `points` → `image`
- **呼び出し**: `fullseye.apply(img, "tb_normals_to_egi", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

法線 ``(N,3)`` → 拡張ガウス像 ``(n_el, n_az)`` の ``image2d``。

    方向の 2-D ヒストグラム(Horn, *Extended Gaussian Images*, Proc. IEEE 72(12)
    1984)。「どの向きの面がどれだけあるか」の地図で、平面が支配的な物体では
    1 つの bin に山が立つ。**不可逆** —— bin 幅ぶんの方向解像度を捨てる。
    捨てた量は測れる: 最頻 bin の中心方向と入力の平均方向の角度差が量子化誤差で、
    既定 (36, 18) では bin 幅 10 度に対し実測 3.7 度(``selftest`` が出す)。

    仰角の bin は ``sin(el)`` で等分する(等立体角)。度で等分すると極が過剰に
    細かくなり、「北極に面が集中している」という嘘の山が立つ。

    Args:
        normals: (N, 3)。
        n_az: 方位の bin 数(既定 36 = 10 度刻み)。
        n_el: 仰角の bin 数(既定 18)。
    Returns:
        (n_el, n_az) float64 の計数マップ(行 = 仰角、列 = 方位)。
    Raises:
        ValueError: bin 数が 1 未満 / 上限超 / 入力不正。

2-D 進化レジストリへ橋渡しした reprconv の op ``normals_to_egi``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``n_az``(既定 36)、``b`` が ``n_el``(既定 18)を振る。

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
