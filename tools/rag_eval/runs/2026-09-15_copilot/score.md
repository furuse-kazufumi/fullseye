# 2026-09-15_copilot — 採点表(機械採点、平均 95.5)

| 問 | 分野 | 点 | 必須群 | 根拠実在 | 期待根拠 | 実在 op | 作った疑い |
|---|---|---:|---:|---:|:-:|---|---|
| q01 | 2D 欠陥 | 93.3 | 2/2 | 0.667 | ✓ | gaussian, tophat, binary_threshold, otsu, gen_measure_arc, measure_pos, measure_pairs | - |
| q02 | 偏光 | 100.0 | 1/1 | 1.0 | ✓ | polarization_separate | - |
| q03 | 計測 | 93.3 | 4/4 | 0.667 | ✓ | gaussian, edges_sub_pix, create_metrology_model, add_metrology_object_circle_measure, align_metrology_model, apply_metrology_model, xpil_find_edges, gen_measure_arc | - |

点 = 50·必須群の充足率 + 20·根拠パスの実在率 + 10·期待根拠 + 20·(1 − 作った疑い/3)。感想・限界の指摘は採点外(人が読む)。
