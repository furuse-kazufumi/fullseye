<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 設計から判定までの一本道

![設計から判定までの一本道](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_pipeline_flow.gif)

*↑ **設計から判定までの一本道** ―― 「設計 → 限界 → 仮想の部品 → 撮像 → 検査 → 判定」の 6 工程を、1 コマずつ止めて読めるコマ送りにしました。系が決まると **16.264 µm/画素**が確定し、そこから光学限界 **32.53 µm**(sampling 律速)が出て、120 µm の傷は 7.38 画素になり、最後に IoU **0.4228** で 検出と判定される —— **正解マスクは撮像でぼけても動かない**ので、この採点が成立します(判定は `marginal`)。 使用 op: `system_geometry`, `resolving_power`, `system_feasibility`, `surface_texture`, `defect_scratch`, `composite_defect`, `defect_stats`, `image_formation`, `draw_polyline`, `draw_circle`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_pipeline_flow_thumb.jpg`)。6 フレーム / 700 ms/コマ / 940×514 px / 0.30 MB。</small>

## 欠陥ジェネレータの見本帳

[![欠陥ジェネレータの見本帳](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_defect_atlas_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_defect_atlas.png)

*↑ **欠陥ジェネレータの見本帳** ―― 欠陥 5 種(scratch / pits / crack / blob / composite)を同じ系(**16.264 µm/画素**)で撮り、左列が撮れる画像、右列が**画素完全な正解マスク**です。マスクは撮像前の幾何から作るので、撮像でぼけても正解は動かず、**注釈作業が存在しません** —— 各行のマスク面積は実測で 682 / 949 / 441 / 2318 / 1749 画素、光学限界は 32.53 µm(sampling 律速)です。 使用 op: `defect_scratch`, `defect_pits`, `defect_crack`, `defect_blob`, `surface_texture`, `composite_defect`, `defect_stats`, `image_formation`。*

<small>クリックで原寸 (998×882 px / 146 kB)。</small>

## 律速の入れ替わり

![律速の入れ替わり](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_limit_crossover.gif)

*↑ **律速の入れ替わり** ―― 作動距離を 120 → 320 mm と掃くと、**回折律速と標本化律速が入れ替わります**。閉形式で解いた交点は **WD 157.64 mm**、そこでは 2 本の限界がどちらも **24.18 µm** で一致します(倍率 0.28539)。記事本文の 44 段掃引が入れ替わりを最初に報告するのは 160.5 mm —— その差は物理ではなく**格子の粗さ**です。 使用 op: `system_geometry`, `resolving_power`, `thin_lens`, `draw_polyline`, `draw_line`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_limit_crossover_thumb.jpg`)。42 フレーム / 10 fps / 1000×474 px / 0.46 MB。</small>

## cos⁴ 則の周辺光量落ち

![cos⁴ 則の周辺光量落ち](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_cos4_falloff.gif)

*↑ **cos⁴ 則の周辺光量落ち** ―― 焦点距離を 42 → 8 mm と短くすると半画角が 5.91° → 33.45° へ広がり、視野の角の明るさが **0.9789 → 0.4846**(中心比)まで落ちます。右の曲線は `relative_illumination` の出力そのもので、左のマップは同じ cos⁴ をセンサ座標で評価したもの —— **独立な 2 経路の角の値が最大でも 0.0e+00 しか違いません**(片方が壊れたら気付ける作りにしてあります)。 使用 op: `relative_illumination`, `thin_lens`, `system_feasibility`, `draw_polyline`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_cos4_falloff_thumb.jpg`)。36 フレーム / 10 fps / 1000×494 px / 1.66 MB。</small>

## 回折限界の MTF

![回折限界の MTF](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_mtf.gif)

*↑ **回折限界の MTF** ―― F 値を f/1.4 から f/22.0 まで絞ると、カットオフ周波数 1/(λN) が **1299 → 83 cyc/mm** へ下がります。左のバーは飾りではなく、**右の曲線から読んだコントラストをそのまま振幅にして描いた**もので、200 cyc/mm のバーは f/1.4 では 0.805 だったのが f/22.0 では 0.000 —— 完全に消えます。 使用 op: `mtf_diffraction`, `draw_polyline`, `draw_markers`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_mtf_thumb.jpg`)。34 フレーム / 10 fps / 1000×536 px / 0.99 MB。</small>

## 被写界深度と錯乱円

![被写界深度と錯乱円](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_dof_coc.gif)

*↑ **被写界深度と錯乱円** ―― 被写界深度は**レンズの性質ではなく、許容錯乱円という「こちらの決め事」**です。錯乱円を 1 画素から 10 画素へ広げると深度は **0.7435 mm → 7.4377 mm**(比 10.0034)と、ほぼ厳密に比例して伸びます。記事のライトフィールドの利得表(6×6 で 6.0016 倍)は**この直線を 2 回読んだだけ**で、要求公差 1 mm が収まるのは錯乱円 1.345 画素からです。 使用 op: `depth_of_field`, `draw_polyline`, `draw_line`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_dof_coc_thumb.jpg`)。37 フレーム / 10 fps / 1000×496 px / 0.44 MB。</small>

## 横分解能 対 被写界深度

![横分解能 対 被写界深度](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_res_vs_dof.gif)

*↑ **横分解能 対 被写界深度** ―― 横分解能と被写界深度は**独立な 2 軸**です。60 µm の欠陥が解像できるのは **f/7.82 まで**、部品の1 mm 公差が収まるのは **f/5.38 から** —— 使える窓は **f/5.38 〜 f/7.82** の帯だけです。これを 1 つの `resolvable` に畳むと「光学限界に未到達」と出てしまい、**読んだ人はレンズを買いに行きます**(直すべきは絞りか公差かフォーカス機構)。 使用 op: `resolving_power`, `depth_of_field`, `system_geometry`, `draw_polyline`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_res_vs_dof_thumb.jpg`)。43 フレーム / 10 fps / 1000×548 px / 0.33 MB。</small>

## Airy パターンと Rayleigh 基準

![Airy パターンと Rayleigh 基準](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_airy_rayleigh.gif)

*↑ **Airy パターンと Rayleigh 基準** ―― 円形瞳の Airy 像で 2 点を近づけていくと、谷は**崖ではなく連続に**浅くなります。第 1 暗環の実測位置は **3.760 µm**(理論 1.2197λN = 3.757 µm)、Rayleigh 間隔 3.758 µm での谷は実測 **0.7336**(教科書の 0.735)で、谷がそもそも現れ始めるのは 3.000 µm からです。 使用 op: `airy_pattern`, `draw_polyline`, `draw_line`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_airy_rayleigh_thumb.jpg`)。33 フレーム / 10 fps / 1000×516 px / 2.31 MB。</small>

## 偏光で金属のテカりを消す

![偏光で金属のテカりを消す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_polarizer.gif)

*↑ **偏光で金属のテカりを消す** ―― 鏡面反射(完全偏光)を Jones 行列で、拡散反射(無偏光)を Mueller 行列で通し、検光子を 0° → 180° で回します。鏡面成分の透過強度は Malus 則で **1.0000 → 0.0000(厳密に 0)**、拡散成分は角度に依らず 0.5 のまま —— 飽和画素が **18.14 % → 0.00 %** に減り、テカりに埋もれていた傷の IoU が **0.140 → 0.787** へ回復して検出に転じます。 使用 op: `jones_element`, `jones_apply`, `stokes_from_jones`, `mueller_element`, `mueller_apply`, `defect_scratch`, `surface_texture`, `image_formation`, `draw_circle`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_polarizer_thumb.jpg`)。31 フレーム / 10 fps / 1000×492 px / 2.65 MB。</small>

## thin lens / ABCD 行列

![thin lens / ABCD 行列](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_abcd_rays.gif)

*↑ **thin lens / ABCD 行列** ―― 物体距離を動かしながら ABCD 行列で 3 本の光線を追うと、共役面では **B 要素が 0 になり、出射高さが入射角に依存しなくなります** —— それが「結像している」の定義そのものです。センサは 42.424 mm に固定してあるので、物体が前後するとぼけ円が広がり、**光線追跡がぼけ 1 画素以内と言う範囲 199.6〜200.4 mm** は、独立な閉形式 `depth_of_field` の 199.629〜200.372 mm と格子の刻みぶんだけの差で一致します。 使用 op: `abcd_matrix`, `abcd_trace`, `thin_lens`, `depth_of_field`, `draw_line`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_abcd_rays_thumb.jpg`)。39 フレーム / 10 fps / 1000×474 px / 0.53 MB。</small>

## 検出限界マップ

[![検出限界マップ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_detect_map_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_detect_map.png)

*↑ **検出限界マップ** ―― 欠陥サイズ(横・対数)とコントラスト(縦)の平面で検出率を測ると、**光学限界 32.53 µm(sampling 律速)は縦の直線として動かず**、実際の検出境界(白線 = 実測 50 % 等高線)はコントラストだけで 53.2 → 27.7 µm と動きます。コントラスト 0.06 では 53 µm(限界の 1.64 倍)必要なのに、0.40 まで上げると 28 µm(0.85 倍)で足ります —— 13 段のうち 4 段は境界が限界より**左**に出ます(ここの検出は IoU ≥ 0.1 の当たり判定であって、2 画素に分かれて見えること = 解像ではありません)。**右側はレンズの問題ではありません**。 使用 op: `render_part`, `system_geometry`, `resolving_power`, `draw_polyline`, `draw_line`。*

<small>クリックで原寸 (1028×488 px / 40 kB)。</small>

## 照明を変えると何が見えるか

![照明を変えると何が見えるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_illumination.gif)

*↑ **照明を変えると何が見えるか** ―― 同じ幾何の 60 µm の傷を、明視野風(明るい面に暗い傷)と暗視野風(暗い場に光る傷)で並べ、コントラストを掃きます。50 % 検出に届くのは明視野風が |contrast| **0.044**、暗視野風が **0.018** で、光学限界 32.53 µm は両方とも余裕で超えています —— **差はレンズではなく見せ方**です(これは `defectgen` の appearance モデル = 符号と露光であって、リング照明の光輸送計算ではありません)。 使用 op: `render_part`, `defect_scratch`, `image_formation`, `draw_polyline`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_illumination_thumb.jpg`)。33 フレーム / 10 fps / 1000×502 px / 0.30 MB。</small>

## 画素ピッチとサンプリング

![画素ピッチとサンプリング](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_pixel_pitch.gif)

*↑ **画素ピッチとサンプリング** ―― 130 µm の傷を固定して画素ピッチだけを粗くすると、欠陥が **2 画素を割るのはピッチ 13.79 µm** (Nyquist の境界)で、実測の 50 % 検出が保つのはピッチ **15.02 µm** までです。拡大は最近傍なので**見えている四角は本物の画素**で、滑らかに見せるための補間は入れていません。 使用 op: `render_part`, `system_geometry`, `resolving_power`, `draw_polyline`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_pixel_pitch_thumb.jpg`)。40 フレーム / 10 fps / 1000×502 px / 0.58 MB。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 設計から判定までの一本道 | GIF | 940×514 | 6 | 303 kB | `46c1de110827b53c` |
| 欠陥ジェネレータの見本帳 | PNG | 998×882 | 1 | 146 kB | `c732c5100726f75c` |
| 律速の入れ替わり | GIF | 1000×474 | 42 | 459 kB | `353cbabaa24686ab` |
| cos⁴ 則の周辺光量落ち | GIF | 1000×494 | 36 | 1661 kB | `50142cb5931e55a0` |
| 回折限界の MTF | GIF | 1000×536 | 34 | 991 kB | `b52ec1dd5cf66bd8` |
| 被写界深度と錯乱円 | GIF | 1000×496 | 37 | 439 kB | `0f2b9c69b1bb6dc5` |
| 横分解能 対 被写界深度 | GIF | 1000×548 | 43 | 327 kB | `b89bed20b13b8978` |
| Airy パターンと Rayleigh 基準 | GIF | 1000×516 | 33 | 2312 kB | `5d8a032aef0b8560` |
| 偏光で金属のテカりを消す | GIF | 1000×492 | 31 | 2651 kB | `7201c5f510b43e36` |
| thin lens / ABCD 行列 | GIF | 1000×474 | 39 | 533 kB | `9b69c483a02265f2` |
| 検出限界マップ | PNG | 1028×488 | 1 | 40 kB | `81b870b0b2bbbd90` |
| 照明を変えると何が見えるか | GIF | 1000×502 | 33 | 297 kB | `9de5ff51d03720e0` |
| 画素ピッチとサンプリング | GIF | 1000×502 | 40 | 577 kB | `54e2158fdb88a94a` |
