# SEGMENTATION operator help — 25 ops in 6 categories

自動生成(`tools/opdocs.py toc`)。フォルダ階層 `docs/ops/segmentation/<category>/<op>.md` を走査。

## ファミリ使い方ガイド(用途→op の教材)

- [halcon_segmentation](guides/halcon_segmentation.md) — 画素分類・領域成長・マーカー分水嶺(HALCON Segmentation 章の 9 op) — 使い方ガイド

## 背景知識ガイド(op の手前にある物理・規約)

- [segmentation_scoring_and_worlds](guides/segmentation_scoring_and_worlds.md) — 分割の採点と真値つき合成世界 — どの物差しがどの壊れ方に盲目か

## カテゴリ

### classify (5)

[class_2dim_sup](classify/class_2dim_sup.md) · [class_2dim_unsup](classify/class_2dim_unsup.md) · [class_ndim_norm](classify/class_ndim_norm.md) · [classify_image_class_lut](classify/classify_image_class_lut.md) · [learn_ndim_norm](classify/learn_ndim_norm.md)

### compare (1)

[check_difference](compare/check_difference.md)

### grow (2)

[expand_gray](grow/expand_gray.md) · [regiongrowing_n](grow/regiongrowing_n.md)

### score (8)

[seg_boundary_f](score/seg_boundary_f.md) · [seg_confusion_table](score/seg_confusion_table.md) · [seg_dice_jaccard](score/seg_dice_jaccard.md) · [seg_hausdorff](score/seg_hausdorff.md) · [seg_mean_surface_distance](score/seg_mean_surface_distance.md) · [seg_object_counts_match](score/seg_object_counts_match.md) · [seg_score_card](score/seg_score_card.md) · [seg_under_over_segmentation](score/seg_under_over_segmentation.md)

### watershed (1)

[watersheds_marker](watershed/watersheds_marker.md)

### world (8)

[lens_area](world/lens_area.md) · [voronoi_cells](world/voronoi_cells.md) · [world_blobs_touching](world/world_blobs_touching.md) · [world_gradient_illumination](world/world_gradient_illumination.md) · [world_grains_voronoi](world/world_grains_voronoi.md) · [world_parts_with_shadow](world/world_parts_with_shadow.md) · [world_texture_regions](world/world_texture_regions.md) · [world_thin_structures](world/world_thin_structures.md)

---
© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
