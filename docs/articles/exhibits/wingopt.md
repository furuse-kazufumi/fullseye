<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 偏光で金属のテカりを消す

![偏光で金属のテカりを消す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_polarizer.gif)

*↑ **偏光で金属のテカりを消す** ―― 鏡面反射(完全偏光)を Jones 行列で、拡散反射(無偏光)を Mueller 行列で通し、検光子を 0° → 180° で回します。鏡面成分の透過強度は Malus 則で **1.0000 → 0.0000(厳密に 0)**、拡散成分は角度に依らず 0.5 のまま —— 飽和画素が **18.47 % → 0.00 %** に減り、テカりに埋もれていた傷の IoU が **0.166 → 0.729** へ回復して検出に転じます。 使用 op: `jones_element`, `jones_apply`, `stokes_from_jones`, `mueller_element`, `mueller_apply`, `defect_scratch`, `surface_texture`, `image_formation`, `draw_circle`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_polarizer_thumb.jpg`)。31 フレーム / 10 fps / 1000×564 px / 2.93 MB。</small>

## thin lens / ABCD 行列

![thin lens / ABCD 行列](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_abcd_rays.gif)

*↑ **thin lens / ABCD 行列** ―― 物体距離を動かしながら ABCD 行列で 3 本の光線を追うと、共役面では **B 要素が 0 になり、出射高さが入射角に依存しなくなります** —— それが「結像している」の定義そのものです。センサは 42.424 mm に固定してあるので、物体が前後するとぼけ円が広がり、**光線追跡がぼけ 1 画素以内と言う範囲 199.6〜200.4 mm** は、独立な閉形式 `depth_of_field` の 199.629〜200.372 mm と格子の刻みぶんだけの差で一致します。 使用 op: `abcd_matrix`, `abcd_trace`, `thin_lens`, `depth_of_field`, `draw_line`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_abcd_rays_thumb.jpg`)。39 フレーム / 10 fps / 1000×474 px / 0.49 MB。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 偏光で金属のテカりを消す | GIF | 1000×564 | 31 | 2929 kB | `eb6282f072fcb819` |
| thin lens / ABCD 行列 | GIF | 1000×474 | 39 | 485 kB | `86cff589a6287a47` |
