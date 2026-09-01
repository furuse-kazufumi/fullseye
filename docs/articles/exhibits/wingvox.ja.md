<!-- tools/gen_wingvox_gallery.py が自動生成。記事 md への挿入候補であり、このファイル自体は記事ではない。数値はすべて生成時の実測値。 -->

# ボクセルの色分けウィング ―― 展示キャプション原稿

生成元: `tools/gen_wingvox_gallery.py`(`py -3.11 tools/gen_wingvox_gallery.py`)。
画像はすべて fullseye の op(`volcolor` / `volops` / `render3d`)と numpy 合成で
描いており(matplotlib 不使用)、図に焼いた数値は 1 つ残らずその場で op を呼んで
得た実測値である。乱数は seed 固定・幾何も固定なので再生成でバイト列が一致する
(`--verify` で検査)。

このウィングの主張は 1 つ ―― **3-D のラベルは、切る前に色を付けなければならない**。
断面ごとに色を付けるとラベル番号が断面ごとに振り直され、同じ部品が層ごとに
別の色になる。展示 2 がその差を本数で示す。

束ね方は `tools/exhibit_tile.py` の 3 種に従う。静止画の Markdown は
すべて **サムネイル表示 + クリックで原寸** の形で出してある。

## 1. 色分けしたボクセルの断面送り

![色分けしたボクセルの断面送り](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingvox_slice_flow.gif)

*↑ **色分けしたボクセルの断面送り** ―― 16 粒子を 26 連結でラベリングし、**ボリュームのまま**色を付けてから 24 枚の断面へ切り出した。1 つの粒子は最初から最後まで 1 色 (実測: 全 16 成分の色数が 1)。spacing (0.50, 0.20, 0.20) mm で 総体積 62.560 mm3。 使用 op: `vol_label`, `vol_colorize_labels`, `vol_label_slice_rgb`, `vol_label_shape_stats`, `vol_label_palette`。*

- GIF: `docs/articles/assets/media/wingvox_slice_flow.gif` (24 コマ, 432x616 px, 0.33 MB)
- サムネ: `docs/articles/assets/thumbs/wingvox_slice_flow_thumb.jpg`
- 束ね方: フリップブック GIF(断面が進む・寸法が揃っている)
- SHA-256: `769ad42caa6786932daf625bafa14a34686fc299dc96b23a11404564b9343228`

<details><summary>この図に焼いた実測値</summary>

```json
{
 "components": 16,
 "slices": 24,
 "shape": [
  24,
  48,
  48
 ],
 "spacing_mm": [
  0.5,
  0.2,
  0.2
 ],
 "total_volume_mm3": 62.56,
 "colours_per_component": 1
}
```

</details>

## 2. ちらつきの対比 ―― 違うのは色を付ける順序だけ

![ちらつきの対比 ―― 違うのは色を付ける順序だけ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingvox_flicker.gif)

*↑ **ちらつきの対比 ―― 違うのは色を付ける順序だけ** ―― 左は断面ごとに 2-D ラベリングして色を付けたもの。断面が変わるたびに番号が振り直されるので、**20 / 24 断面**で少なくとも 1 粒子の色が変わる ((粒子, 断面) の変化 62 / 108 組 = 57.4 %、16 粒子すべてが一度は変わる)。右はボリュームで色を付けてから切ったもので、変化は **0 断面 / 0 組**。同じパレット・同じ seed で、違うのは順序だけである。 使用 op: `vol_label`, `vol_label_color_flicker`, `vol_colorize_labels`, `vol_label_slice_rgb`, `colorize_labels`。*

- GIF: `docs/articles/assets/media/wingvox_flicker.gif` (24 コマ, 596x468 px, 0.37 MB)
- サムネ: `docs/articles/assets/thumbs/wingvox_flicker_thumb.jpg`
- 束ね方: フリップブック GIF(左右を 1 コマに合成して同時に進める)
- SHA-256: `b22e88054154f9ce33e1504ed9e4b109955e2e7f86d24227cdff77f8fd732a41`

<details><summary>この図に焼いた実測値</summary>

```json
{
 "components": 16,
 "slices": 24,
 "per_slice_changed_slices": 20,
 "per_slice_changed_pairs": 62,
 "pairs_checked": 108,
 "per_slice_changed_components": 16,
 "flicker_rate_pct": 57.4,
 "volume_changed_slices": 0,
 "volume_changed_pairs": 0,
 "burned_in_running_total": 20
}
```

</details>

## 3. 6 / 18 / 26 連結 ―― 近傍の定義が成分数を決める

[![6 / 18 / 26 連結 ―― 近傍の定義が成分数を決める](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingvox_connectivity_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingvox_connectivity.png)

*↑ **6 / 18 / 26 連結 ―― 近傍の定義が成分数を決める** ―― 同じ 2 つの立方体でも、頂点 1 点だけで接している場合は 6 連結 2 成分 / 18 連結 2 成分 / 26 連結 **1 成分**、稜線で接している場合は 2 / **1** / 1 となる。色数は成分数にそのまま連動する ―― 融合すれば色が 1 つ減る。 使用 op: `vol_label`, `vol_label_volume_render`, `vol_label_palette`。*

- PNG (タイル): `docs/articles/assets/wingvox_connectivity.png` (774x692 px, 31 kB, 6 パネル / 3 列)
- サムネ(記事はこちらを表示): `docs/articles/assets/wingvox_connectivity_thumb.jpg` (57 kB)
- 束ね方: タイル(同じ被写体に近傍の定義違いを当てた 6 枚を比べる)
- SHA-256: `1e71d481fec54a3b648163520a0c954e2077d102f7859d1b9da06e36196a01d6`

<details><summary>この図に焼いた実測値</summary>

```json
{
 "corner": {
  "6": 2,
  "18": 2,
  "26": 1
 },
 "edge": {
  "6": 2,
  "18": 1,
  "26": 1
 },
 "note": "角接触は 26 だけが繋ぎ、稜線接触は 18 から繋がる"
}
```

</details>

## 4. 体積でふるいにかけても、残った粒子の色は動かない

![体積でふるいにかけても、残った粒子の色は動かない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingvox_sieve.gif)

*↑ **体積でふるいにかけても、残った粒子の色は動かない** ―― ``min_volume`` を 0 から 9.320 mm3 まで 17 段で上げ、粒子を 1 つずつ落としていく。落ちた粒子は背景になるが、**残った粒子の色は 1 画素も変わらない**(全 17 コマで実測・確認)。番号を振り直さない (``relabel=False``)からで、振り直すとパレットの行が動いて色は総取り替えになる。 使用 op: `vol_label`, `vol_label_shape_stats`, `vol_select_labels`, `vol_label_volume_render`, `vol_colorize_labels`。*

- GIF: `docs/articles/assets/media/wingvox_sieve.gif` (17 コマ, 432x616 px, 0.30 MB)
- サムネ: `docs/articles/assets/thumbs/wingvox_sieve_thumb.jpg`
- 束ね方: フリップブック GIF(閾値が進む)
- SHA-256: `ed2622bdcb2dbbd98d792fb9c4e15c65ef20c0c688f4e3f272345affcfc97bd6`

<details><summary>この図に焼いた実測値</summary>

```json
{
 "components": 16,
 "steps": 17,
 "volumes_mm3": [
  0.56,
  0.56,
  0.66,
  0.66,
  1.62,
  1.88,
  1.88,
  3.42,
  3.42,
  3.48,
  5.14,
  5.76,
  5.76,
  9.22,
  9.22,
  9.32
 ],
 "all_colours_unchanged": true,
 "sweep": [
  {
   "min_volume_mm3": 0.0,
   "kept": 16,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 0.56,
   "kept": 16,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 0.56,
   "kept": 16,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 0.66,
   "kept": 14,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 0.66,
   "kept": 14,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 1.62,
   "kept": 12,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 1.88,
   "kept": 11,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 1.88,
   "kept": 11,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 3.42,
   "kept": 9,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 3.42,
   "kept": 9,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 3.48,
   "kept": 7,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 5.14,
   "kept": 6,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 5.76,
   "kept": 5,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 5.76,
   "kept": 5,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 9.22,
   "kept": 3,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 9.22,
   "kept": 3,
   "colours_unchanged": true
  },
  {
   "min_volume_mm3": 9.32,
   "kept": 1,
   "colours_unchanged": true
  }
 ]
}
```

</details>

## 5. 元の CT に色ラベルを重ねる ―― α を掃引する

![元の CT に色ラベルを重ねる ―― α を掃引する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingvox_overlay_alpha.gif)

*↑ **元の CT に色ラベルを重ねる ―― α を掃引する** ―― 断面 z=8 で alpha を 0 から 1 へ往復させる。前景の平均変化は 0.0000 → 0.0262 と alpha に**直線**で比例し、**背景の変化は alpha に依らず 0.0000**(色はラベルの上にしか乗らない)。輪郭だけ塗る ``mode='boundary'`` なら前景 3128 ボクセルのうち 1648(52.7 %)しか塗らないので、下の構造が完全に見える。 使用 op: `vol_label`, `vol_label_overlay`, `vol_label_slice_rgb`。*

- GIF: `docs/articles/assets/media/wingvox_overlay_alpha.gif` (20 コマ, 432x616 px, 0.99 MB)
- サムネ: `docs/articles/assets/thumbs/wingvox_overlay_alpha_thumb.jpg`
- 束ね方: フリップブック GIF(alpha を往復掃引)
- SHA-256: `fcb879348b2dcf66cdf37bc2aad03a7cc786499ee3c358d304a6d6f6636c1ca7`

<details><summary>この図に焼いた実測値</summary>

```json
{
 "slice": 8,
 "components": 16,
 "frames": 20,
 "sweep": [
  {
   "alpha": 0.0,
   "fg_mean_abs_diff": 0.0,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.1,
   "fg_mean_abs_diff": 0.0262,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.2,
   "fg_mean_abs_diff": 0.0524,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.3,
   "fg_mean_abs_diff": 0.0786,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.4,
   "fg_mean_abs_diff": 0.1048,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.5,
   "fg_mean_abs_diff": 0.131,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.6,
   "fg_mean_abs_diff": 0.1572,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.7,
   "fg_mean_abs_diff": 0.1834,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.8,
   "fg_mean_abs_diff": 0.2096,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.9,
   "fg_mean_abs_diff": 0.2358,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 1.0,
   "fg_mean_abs_diff": 0.262,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.9,
   "fg_mean_abs_diff": 0.2358,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.8,
   "fg_mean_abs_diff": 0.2096,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.7,
   "fg_mean_abs_diff": 0.1834,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.6,
   "fg_mean_abs_diff": 0.1572,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.5,
   "fg_mean_abs_diff": 0.131,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.4,
   "fg_mean_abs_diff": 0.1048,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.3,
   "fg_mean_abs_diff": 0.0786,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.2,
   "fg_mean_abs_diff": 0.0524,
   "bg_mean_abs_diff": 0.0
  },
  {
   "alpha": 0.1,
   "fg_mean_abs_diff": 0.0262,
   "bg_mean_abs_diff": 0.0
  }
 ],
 "bg_untouched_at_every_alpha": true,
 "boundary_voxels": 1648,
 "fill_voxels": 3128,
 "boundary_share_pct": 52.7
}
```

</details>

## 6. 色付きメッシュのターンテーブル

![色付きメッシュのターンテーブル](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingvox_mesh_turntable.gif)

*↑ **色付きメッシュのターンテーブル** ―― 16 個の成分それぞれの bbox 部分体に marching cubes をかけ、三角形 7088 枚のメッシュ 16 個にした。頂点は spacing (0.50, 0.20, 0.20) mm を掛けた物理座標で、``render3d.render_mesh`` の z バッファで合成している。粒が縦に伸びて見えるのは**そのほうが正しい**からで、z の刻みが面内の 2.5 倍あるためである(展示 4 と同じ話)。**色は断面図とまったく同じパレットの同じ行**なので、切った絵と回した絵で同じ粒子を目で追える。 使用 op: `vol_label`, `vol_labels_to_meshes`, `look_at`, `intrinsics_from_fov`, `render_mesh`。*

- GIF: `docs/articles/assets/media/wingvox_mesh_turntable.gif` (24 コマ, 380x538 px, 0.45 MB)
- サムネ: `docs/articles/assets/thumbs/wingvox_mesh_turntable_thumb.jpg`
- 束ね方: フリップブック GIF(方位が進む)
- SHA-256: `4a2ba556d6751c838b4b68264026913f89e33a444e67eb73fc2606ec9d344240`

<details><summary>この図に焼いた実測値</summary>

```json
{
 "components": 16,
 "meshes": 16,
 "triangles": 7088,
 "azimuth_steps": 24,
 "render_px": 380,
 "spacing_mm": [
  0.5,
  0.2,
  0.2
 ],
 "colours_match_slices": true
}
```

</details>

## 7. 凡例つきの計測表 ―― どの色がどの粒子か

[![凡例つきの計測表 ―― どの色がどの粒子か](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingvox_legend_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingvox_legend.png)

*↑ **凡例つきの計測表 ―― どの色がどの粒子か** ―― 色分けした図は、凡例が無ければ「きれいなだけ」で終わる。16 粒子の色見本・体積 mm3・全体比・等価直径・球形度・伸長度・視野端への接触を並べた。総体積 62.5600 mm3、比率の合計 1.000000。1 ボクセル = 0.020000 mm3。最大は #2ddc8a の 9.3200 mm3、最小は #15d4c9 の 0.5600 mm3。 使用 op: `vol_label`, `vol_region_props`, `vol_label_shape_stats`, `vol_label_legend`, `vol_label_palette`。*

- PNG (原寸 1 枚): `docs/articles/assets/wingvox_legend.png` (900x626 px, 104 kB)
- サムネ(記事はこちらを表示): `docs/articles/assets/wingvox_legend_thumb.jpg` (79 kB)
- 束ね方: 原寸 1 枚(表の数値が主役 ―― 縮めると読めない)
- SHA-256: `996d79e05286f61b29e5add295e2a5519b6e7b87a2eede1d8e5fdec023a2e504`

<details><summary>この図に焼いた実測値</summary>

```json
{
 "components": 16,
 "spacing_mm": [
  0.5,
  0.2,
  0.2
 ],
 "total_volume_mm3": 62.56,
 "share_sum": 1.0,
 "voxel_volume_mm3": 0.02,
 "largest": {
  "label": 5,
  "hex": "#2ddc8a",
  "volume_mm3": 9.32
 },
 "smallest": {
  "label": 16,
  "hex": "#15d4c9",
  "volume_mm3": 0.56
 },
 "sphericity_range": [
  0.587,
  0.662
 ]
}
```

</details>
