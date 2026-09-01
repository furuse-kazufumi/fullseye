<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## Airy パターンと Rayleigh 基準

![Airy パターンと Rayleigh 基準](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_airy_rayleigh.gif)

*↑ **Airy パターンと Rayleigh 基準** ―― 円形瞳の Airy 像で 2 点を近づけていくと、谷は**崖ではなく連続に**浅くなります。第 1 暗環の実測位置は **3.760 µm**(理論 1.2197λN = 3.757 µm)、Rayleigh 間隔 3.758 µm での谷は実測 **0.7336**(教科書の 0.735)で、谷がそもそも現れ始めるのは 3.000 µm からです。 使用 op: `airy_pattern`, `draw_polyline`, `draw_line`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_airy_rayleigh_thumb.jpg`)。37 フレーム / 10 fps / 1000×516 px / 2.50 MB。</small>

## 偏光で金属のテカりを消す

![偏光で金属のテカりを消す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_polarizer.gif)

*↑ **偏光で金属のテカりを消す** ―― 鏡面反射(完全偏光)を Jones 行列で、拡散反射(無偏光)を Mueller 行列で通し、検光子を 0° → 180° で回します。鏡面成分の透過強度は Malus 則で **1.0000 → 0.0000(厳密に 0)**、拡散成分は角度に依らず 0.5 のまま —— 飽和画素が **18.08 % → 0.00 %** に減り、テカりに埋もれていた傷の IoU が **0.126 → 0.635** へ回復して検出に転じます。 使用 op: `jones_element`, `jones_apply`, `stokes_from_jones`, `mueller_element`, `mueller_apply`, `defect_scratch`, `surface_texture`, `image_formation`, `draw_circle`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_polarizer_thumb.jpg`)。37 フレーム / 10 fps / 1000×652 px / 4.60 MB。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| Airy パターンと Rayleigh 基準 | GIF | 1000×516 | 37 | 2500 kB | `fa760d6fb63dd6d0` |
| 偏光で金属のテカりを消す | GIF | 1000×652 | 37 | 4597 kB | `3f0eb504b1e1eddc` |
