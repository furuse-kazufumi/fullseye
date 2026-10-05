---
op: stream_areal_density
dim: drive
category: scoop
in: image2d × scalar
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# stream_areal_density — DRIVE `scoop` op

- **データ種**: `image2d × scalar` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.stream_areal_density(coverage, radius_px: 'float', *, c_max: 'float' = 0.95, mode: 'str' = 'raise') -> 'np.ndarray'` (実装を直接呼ぶなら `import scoop; scoop.stream_areal_density(coverage, radius_px: 'float', *, c_max: 'float' = 0.95, mode: 'str' = 'raise') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("stream_areal_density")`)

## 使い方

被覆率から粒の中心の面密度 [個 / px²] を Boolean 模型で逆に解く ``n = −ln(1 − c) / (π r²)``。

独立に置いた半径 ``r`` の円板の和の被覆率は ``c = 1 − exp(−n π r²)``(重なりを数え落とさない)。素朴な
``c / (π r²)`` は c = 0.8 で 2 倍近く数え落とす(PoC の門)。c が 1 に近いと逆は発散する(厚い流れは向こうが
見えない): ``mode="raise"`` は ``c ≥ c_max`` の画素があれば ``ValueError``、``"clip"`` は ``c_max`` に切る(下限の推定に
なる)。粒の位置が独立でない密な流れ(口の近く、粒が接している)では模型が外れる —— 限界。
**Raises** ``ValueError``: 被覆率でない / 飽和(``mode="raise"``)/ 綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
