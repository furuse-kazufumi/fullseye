---
op: tb_wetness
dim: 2d
category: typed
in: rgbimage
out: rgbimage
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# tb_wetness — 2D `typed` op

- **データ種**: `rgbimage` → `rgbimage`
- **呼び出し**: `fullseye.apply(img, "tb_wetness", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

濡れた面の下地色。**拡散が暗くなる**(そして鏡面が増える)。

    base_rgb: 乾いた状態の色 (H,W,3) または (3,)。wet: 濡れ具合(0–1)。
    ior: 水膜の屈折率。

    返り値: 濡れた状態の拡散色(同形)。

    なぜ暗くなるか: 水膜の内側で全反射が起き、拡散光が何度も表面へ戻されて
    そのたびに吸収される。近似として、乾いた反射率 ρ に対し内部反射率
    Ri = 1 − (1 − Ri0)/n² 相当の再吸収を掛ける ―― 濡れた砂が黒く見える現象そのもの
    (鏡面が増えるのは `clearcoat_shade(coat=wet)` を重ねて表す)。

2-D 進化レジストリへ橋渡しした optics の op ``wetness``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``wet``(既定 1)、``b`` が ``ior``(既定 1.33)を振る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`rgbimage` を入力に取れる)

[identity](../misc/identity.md) · [tb_sensor_capture](tb_sensor_capture.md) · [tb_specular_diffuse_split](tb_specular_diffuse_split.md) · [tb_specular_coefficient_map](tb_specular_coefficient_map.md) · [tb_specular_free_transform](tb_specular_free_transform.md) · [tb_rgb_to_quaternion](tb_rgb_to_quaternion.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
