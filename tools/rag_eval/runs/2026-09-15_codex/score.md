# 2026-09-15_codex — 採点表(機械採点、平均 91.7)

| 問 | 分野 | 点 | 必須群 | 根拠実在 | 期待根拠 | 実在 op | 作った疑い |
|---|---|---:|---:|---:|:-:|---|---|
| q01 | 2D 欠陥 | 75.0 | 1/2 | 1.0 | ✓ | gaussian, lines_gauss, select_contours, length_xld, count_contours | - |
| q02 | 偏光 | 100.0 | 1/1 | 1.0 | ✓ | polarization_separate | - |
| q03 | 計測 | 100.0 | 4/4 | 1.0 | ✓ | edges_sub_pix, create_metrology_model, add_metrology_object_circle_measure, apply_metrology_model, hx_fit_circle_contour, rms | - |

点 = 50·必須群の充足率 + 20·根拠パスの実在率 + 10·期待根拠 + 20·(1 − 作った疑い/3)。感想・限界の指摘は採点外(人が読む)。
