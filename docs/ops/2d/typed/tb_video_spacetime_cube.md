---
op: tb_video_spacetime_cube
dim: 2d
category: typed
in: video
out: volume
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# tb_video_spacetime_cube — 2D `typed` op

- **データ種**: `video` → `volume`
- **呼び出し**: `fullseye.apply(img, "tb_video_spacetime_cube", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

動画 (T, H, W) を空間 × 時間の立方体 ``(T, H, W)`` float [0, 1] にする(``voxel``)。

    ``mode="motion"``: 隣り合うフレームの差の大きさ |I_t − I_{t−1}| を空間で σ = ``sigma`` のガウスで平滑し、
    ``percentile`` 分位で 1 に正規化、``floor`` 未満を 0 に落として [0, 1] に伸ばす(先頭フレームは 0。
    センサ雑音の差分は床の下に沈む)。動く物体だけが立つので、``vol_render_transfer`` の**不透明度**になる ——
    静止した背景は透けて、軌跡が浮かぶ(Summagator の伝達関数)。
    ``mode="intensity"``: 明るさを [0, 1] に正規化(色の元、または背景を薄く敷く用)。
    ``mode="dark"`` / ``"bright"``: 暗い / 明るい所を不透明にする(σ で平滑、``floor`` 未満は 0)。動画でなく
    **z スタック**(EM の連続断面: 膜は暗い、蛍光: 細胞は明るい)を同じ立方体として見るため —— 先頭軸を
    時間でなく奥行きと読むだけで、断面(``video_cube_cut``)も回転(``video_cube_orbit``)も同じ op で動く。

    >>> alpha = video_spacetime_cube(clip, "motion")
    >>> color = video_spacetime_cube(clip, "intensity")
    >>> rgb = vol_render_transfer(alpha, color, yaw=35.0, pitch=25.0)
    >>> membranes = video_spacetime_cube(em_stack, "dark", sigma=1.0)      # ハエの脳の断面を積んだ立方体

2-D 進化レジストリへ橋渡しした videocube の op ``video_spacetime_cube``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``sigma``(既定 1)、``b`` が ``percentile``(既定 99.5)を振る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `video_spacetime_cube` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [poc_video_cube](../../../../examples/poc_video_cube.py) — `py -3.11 examples/poc_video_cube.py`

## 型が繋がる次の op(`volume` を入力に取れる)

[identity](../misc/identity.md) · [vol_gaussian](../3d/vol_gaussian.md) · [vol_median](../3d/vol_median.md) · [vol_erode](../3d/vol_erode.md) · [vol_dilate](../3d/vol_dilate.md) · [vol_threshold](../3d/vol_threshold.md) · [vol_reg_dilate](../3d/vol_reg_dilate.md) · [vol_reg_erode](../3d/vol_reg_erode.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
