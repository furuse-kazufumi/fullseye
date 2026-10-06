---
op: repose_angle_heightmap
dim: drive
category: granular
in: image2d × scalar
out: table
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# repose_angle_heightmap — DRIVE `granular` op

- **データ種**: `image2d × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.repose_angle_heightmap(hm, pitch: 'float', *, ground=None, min_rel_height: 'float' = 0.1, max_rel_height: 'float' = 0.9, bin_deg: 'float' = 0.25, method: 'str' = 'horn', smooth_cells: 'int' = 1) -> 'dict'` (実装を直接呼ぶなら `import granular; granular.repose_angle_heightmap(hm, pitch: 'float', *, ground=None, min_rel_height: 'float' = 0.1, max_rel_height: 'float' = 0.9, bin_deg: 'float' = 0.25, method: 'str' = 'horn', smooth_cells: 'int' = 1) -> 'dict'`、台帳から引くなら `opsdrive.get("repose_angle_heightmap")`)

## 使い方

高さ図から安息角 φ —— ``demops.dem_slope`` の勾配のヒストグラムの最頻値。

手順: ①``ground`` があれば引く(datum の補正; 無ければ外周 1 画素の中央値を地面とする)②``smooth_cells``
(奇数)の移動平均 —— **粒が見える高さ図では必須**: 球の山(粒径 5.3 px)を平滑なしで測ると勾配の最頻は
62 度(球面の縁)、2 粒径 = 11 セルで 24.5 度(MuJoCo の球の山の実測)。粒が見えない粉の山では 1 のまま
③高さが最大の ``min_rel_height``〜``max_rel_height`` の帯のセルだけ使う(裾の丸みと頂の鈍りを除く)
④``dem_slope(method)`` を ``bin_deg`` 刻みで数え、最頻ビンとその両隣に入る値の平均で φ(ビン中心の重心だと半ビン = 0.125 度の偏りが出た、実測)。
返り: ``phi_deg``, ``phi_median_deg``, ``frac_within_1deg``(最頻 ±1 度に入るセルの割合 —— 円錐なら
≈ 1、起伏があれば下がる)、``n_cells``, ``hist_centers``, ``hist_counts``。
**Raises** ``ValueError``: 形・pitch・選択肢(``method`` は ``"horn"`` / ``"central"`` のみ)/ 山が無い
(地面より高いセルが無い)/ 帯に 20 セル未満。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
