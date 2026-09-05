---
op: tb_env_lightbox
dim: 2d
category: typed
in: points
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# tb_env_lightbox — 2D `typed` op

- **データ種**: `points` → `signal`
- **呼び出し**: `fullseye.apply(img, "tb_env_lightbox", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

撮影ボックスの環境(広い天井の明かり + ほんのり明るい周囲)。**無彩色**。

    :func:`env_studio` が「劇的に見せる」ための暗い部屋 + 小さいソフトボックス 2 灯
    なのに対し、こちらは**加工面が加工面に見える**ための環境。2026-09-05 の実測で
    分かった 2 つの条件を満たすように作ってある:

      * 周囲が明るいこと ―― 暗い環境だとアルミが真っ黒になる(反射率 ~0.9 の金属が
        黒く写るのは、映るものが黒いから)。
      * それでも**勾配があること** ―― 完全に一様な環境では、どんな異方性ローブでも
        同じ値を返すので加工目が消える。ブラシ目が見えるのは、目が環境の明暗を
        目方向に引き伸ばすからである。

    加工目は**斜めから見ないと出ない**(真上から見た平面は反射方向が全画素で天頂に
    集中し、環境の勾配を掃かない)。``optical_camera(tilt_deg=50〜70)`` 程度が目安。

2-D 進化レジストリへ橋渡しした optics の op ``env_lightbox``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``base``(既定 0.45)、``b`` が ``key``(既定 4)を振る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[identity](../misc/identity.md) · [tb_create_funct_1d_array](tb_create_funct_1d_array.md) · [tb_smooth_funct_1d_gauss](tb_smooth_funct_1d_gauss.md) · [tb_smooth_funct_1d_mean](tb_smooth_funct_1d_mean.md) · [tb_derivate_funct_1d](tb_derivate_funct_1d.md) · [tb_integrate_funct_1d](tb_integrate_funct_1d.md) · [tb_zero_crossings_funct_1d](tb_zero_crossings_funct_1d.md) · [tb_abs_funct_1d](tb_abs_funct_1d.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
