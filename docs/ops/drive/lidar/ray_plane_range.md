---
op: ray_plane_range
dim: drive
category: lidar
in: points × points
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# ray_plane_range — DRIVE `lidar` op

- **データ種**: `points × points` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.ray_plane_range(origin, dirs, plane) -> 'np.ndarray'` (実装を直接呼ぶなら `import lidarsim; lidarsim.ray_plane_range(origin, dirs, plane) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("ray_plane_range")`)

## 使い方

原点 ``origin`` から方向 ``dirs (...,3)`` のレイが平面 ``ax+by+cz+d=0`` に当たるまでの距離。

閉形式 ``t = −(n·O + d)/(n·D)``、距離は ``t·‖D‖``。前方(t > 0)に当たらない・平行なら ``inf``。
法線がゼロなら ``ValueError``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

—

## 同カテゴリ(`lidar`)

[lidar_spec](lidar_spec.md) · [lidar_scan](lidar_scan.md) · [ray_box_ranges](ray_box_ranges.md)

---
*Provenance: lidarsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
