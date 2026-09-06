---
op: tb_quaternion_to_rgb
dim: 2d
category: typed
in: qimage
out: rgbimage
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# tb_quaternion_to_rgb — 2D `typed` op

- **データ種**: `qimage` → `rgbimage`
- **呼び出し**: `fullseye.apply(img, "tb_quaternion_to_rgb", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![tb_quaternion_to_rgb: input → output](../../_fig/tb_quaternion_to_rgb.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![tb_quaternion_to_rgb: stages](../../_fig/tb_quaternion_to_rgb.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![tb_quaternion_to_rgb: other inputs](../../_fig/tb_quaternion_to_rgb.inputs.jpg)

## 使い方

Vector part of a quaternion image, as linear RGB. → (H, W, 3).

    The inverse of :func:`rgb_to_quaternion` — and, by default, a *checked*
    inverse. A quaternion image that picked up a scalar component somewhere (a
    Hamilton product with a non-pure quaternion, a monogenic signal handed here
    by mistake) is **refused** rather than silently truncated, because dropping
    the ``w`` component is exactly the kind of loss that produces a plausible
    picture from the wrong data. Pass ``allow_scalar=True`` to opt in to the
    truncation when it is what you meant.

    The tolerance is relative to the field's own peak modulus
    (:data:`_MONOGENIC_K_TOL`, 1e-9): a quaternion image that really is pure
    carries ``|w|`` at the 1e-17 level after a round trip through two FFTs, and
    anything with a meaningful scalar part is many orders above that. Nothing
    real lives in between.

    **Raises** ``ValueError``: *qimage* is not a finite ``(H, W, 4)`` array; or
    it has a non-negligible scalar part and ``allow_scalar`` is False.

Typed bridge of the quat op ``quaternion_to_rgb`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
img_to_rgb 0.50 0.50
tb_rgb_to_quaternion 0.50 0.50
tb_quaternion_to_rgb 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `quaternion_to_rgb` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

[identity](../misc/identity.md) · [tb_wetness](tb_wetness.md) · [tb_sensor_capture](tb_sensor_capture.md) · [tb_specular_diffuse_split](tb_specular_diffuse_split.md) · [tb_specular_coefficient_map](tb_specular_coefficient_map.md) · [tb_specular_free_transform](tb_specular_free_transform.md) · [tb_rgb_to_quaternion](tb_rgb_to_quaternion.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
