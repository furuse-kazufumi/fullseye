---
op: tb_shape_perturb
dim: 2d
category: typed
in: points
out: points
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# tb_shape_perturb — 2D `typed` op

- **データ種**: `points` → `points`
- **呼び出し**: `fullseye.apply(img, "tb_shape_perturb", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

*図なし: この op は `points` を入力に取る。画像から始まる Studio のプログラムでは型が届かないので、下の「実行できる例」で使い方を見ること。*

## 使い方

形に**既知の**変形を 1 つ入れる。→ ``(N, 3)``。

    ``mode``:

    * ``"bulge"``  —— *center* のまわりをガウス重みで外向きに膨らませる。
      片側だけに入れれば左右非対称性の真値になる。
    * ``"shift"``  —— *center* 方向へ一様に平行移動(Procrustes が消す成分)。
    * ``"scale"``  —— 一様拡大(``scaling=True`` の Procrustes が消す成分)。
    * ``"noise"``  —— 等方ガウス雑音(どの手法でも消えない床)。

    「Procrustes が消してくれる変形」と「消してはいけない変形」を分けて試せる
    ように 4 つ置いてある。位置合わせの検算はこの区別が要る。

2-D 進化レジストリへ橋渡しした shapestat の op ``shape_perturb``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``amplitude``(既定 0.05)、``b`` が ``sigma``(既定 0.4)を振る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`points` を入力に取れる)

[identity](../misc/identity.md) · [tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
