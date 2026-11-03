# レシピの GPU 経路(生成物)

`tools/gen_gpu_routes.py` が `fullseye.explain_pipeline(stages, (2048, 2048), device="auto", assume_cuda=True)` を既存のレシピ全部(`fullseye/data/RECIPE_INDEX.json`)に当てた表。手で直さない。
**前** = 領域の解析の族(`accel_label.ADOPTED`、17 op)を経路から外した場合、**後** = 今の経路。
`assume_cuda=True` は CUDA・CuPy・空き VRAM のある機械として経路表だけで決める(GPU の無い CI でも同じ表)。

| 2 段以上のレシピ 12 本・37 段 | GPU の段 | 全段 GPU | 切り替わり | 往復の見込み |
|---|---:|---:|---:|---:|
| 前 | 28 | 5 | 12 | 16 |
| 後 | 36 | 11 | 5 | 16 |

| レシピ | 前: 切替 / 往復 | 後: 切替 / 往復 | 後の段(CPU の段は理由つき) |
|---|---:|---:|---|
| Denoise — bilateral + unsharp | 0 / 1 | 0 / 1 | bilateral[GPU] → unsharp[GPU] |
| Denoise — total variation | 0 / 1 | 0 / 1 | sk_tv[GPU] |
| Denoise — median | 0 / 1 | 0 / 1 | median[GPU] |
| Edge — Sobel + Otsu | 0 / 1 | 0 / 1 | gaussian[GPU] → sobel_amp[GPU] → otsu[GPU] |
| Edge — Canny | 0 / 1 | 0 / 1 | gaussian[GPU] → canny[GPU] |
| Segment — blob / coin | 1 / 1 | 0 / 1 | gaussian[GPU] → otsu[GPU] → fill_up[GPU] → remove_small[GPU] |
| Count — blobs | 1 / 1 | 0 / 1 | gaussian[GPU] → otsu[GPU] → fill_up[GPU] → count_obj[GPU] |
| Binarize — document (adaptive) | 0 / 1 | 0 / 1 | adaptive_gauss_thresh[GPU] |
| Enhance — CLAHE contrast | 0 / 1 | 0 / 1 | clahe[GPU] |
| Enhance — histogram equalize | 0 / 1 | 0 / 1 | equalize[GPU] |
| Enhance — gamma | 0 / 1 | 0 / 1 | gamma[GPU] |
| Sharpen — unsharp mask | 0 / 1 | 0 / 1 | unsharp[GPU] |
| Sharpen — highpass | 0 / 1 | 0 / 1 | highpass[GPU] |
| Texture — Gabor | 0 / 1 | 0 / 1 | gabor[GPU] |
| Texture — local std | 0 / 1 | 0 / 1 | std_filter[GPU] |
| Keypoints — Harris corners | 0 / 0 | 0 / 0 | sk_corner_harris[CPU:not_listed] |
| Blobs — Difference of Gaussians | 0 / 0 | 0 / 0 | sk_dog[CPU:not_listed] |
| Morphology — gradient | 0 / 1 | 0 / 1 | morph_grad[GPU] |
| Shape — distance transform | 1 / 2 | 1 / 2 | gaussian[GPU] → otsu[GPU] → distance_transform[GPU] |
| Spots — local maxima | 0 / 1 | 0 / 1 | gaussian[GPU] → local_max[GPU] |
| FA — scratch on hairline metal | 3 / 2 | 2 / 2 | gaussian[GPU] → sk_rolling_ball[CPU:not_listed] → threshold[GPU] → select_shape[GPU] |
| FA — dent and foreign fibre on resin | 3 / 3 | 2 / 3 | gaussian[GPU] → hx_plane_deviation[GPU] → threshold[GPU] → select_shape[GPU] |
| FA — engraved lot code (binarize for OCR) | 1 / 1 | 0 / 1 | gaussian[GPU] → otsu[GPU] → select_shape[GPU] |
| FA — count holes in a back-lit plate | 1 / 1 | 0 / 1 | otsu[GPU] → sk_clear_border[GPU] → count_obj[GPU] |
| FA — weld porosity (X-ray) | 1 / 1 | 0 / 1 | gaussian[GPU] → local_threshold[GPU] → select_shape[GPU] |

理由の語: `not_listed` = GPU 経路が無い / `chain_only` = 鎖の枠だけの経路で隣が GPU でない / `crossover` = 損益分岐。往復 = GPU の区間ごとに送り 1 回・戻し 1 回。
