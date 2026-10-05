---
op: plane_topview
dim: drive
category: pegsym
in: image2d × matrix × matrix × signal
out: image2d
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# plane_topview — DRIVE `pegsym` op

- **データ種**: `image2d × matrix × matrix × signal` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.plane_topview(image, K, R, t, z: 'float' = 0.0, centre=(0.0, 0.0), extent: 'float' = 0.02, res: 'float' = 5e-05, fill: 'float' = 0.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import pegsym; pegsym.plane_topview(image, K, R, t, z: 'float' = 0.0, centre=(0.0, 0.0), extent: 'float' = 0.02, res: 'float' = 5e-05, fill: 'float' = 0.0) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("plane_topview")`)

## 使い方

斜めや下からの画像を、世界の平面 z = ``z`` を真上から見た図に打ち直す(ホモグラフィ = 各格子点を投影して双線形で引く)。
カメラは世界 → OpenCV カメラの ``R``・``t``(x_c = R X + t)、内部 ``K``(画素中心が整数の規約)。格子は ``centre`` = (x, y) を中心に
一辺 ``extent`` [m]、画素 ``res`` [m]。列 = +x、行 = −y(北が上)。下から見た画像(鏡像)もこの図では同じ向きになる。カメラの後ろ・
画像の外の格子点は ``fill``。返り = (S, S) の濃淡(カラーは輝度にする)。
**Raises** ValueError: 画像が 2-D 濃淡か (H, W, 3) でない、K・R が 3×3 でない、t が 3 成分でない、extent ≤ 0、res ≤ 0、S > 4096。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_offset](polygon_offset.md) · [polygon_fit_check](polygon_fit_check.md) · [rotation_window](rotation_window.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [polygon_coverage_image](polygon_coverage_image.md) · [polygon_yaw_read](polygon_yaw_read.md) · [relative_yaw_from_images](relative_yaw_from_images.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
