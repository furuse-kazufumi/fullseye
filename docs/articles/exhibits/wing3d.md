# 3D 計測ウィング ―― 紙面の科学館

本ファイルは `tools/gen_wing3d_gallery.py` が **実行結果から自動生成**しています(手で数値を書き換えないでください)。
図に焼き込んだ数字はすべてその場の計算結果で、素材は合成データのみです(実データ・AI 生成素材は使っていません)。

生成: seed `20260902` 固定 / `py -3.11 tools/gen_wing3d_gallery.py`

---

### 3D 計測ウィング ―― ボクセルと点群を「測る」ための op

![境界だけ持つと 6 % に痩せる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_boundary_shell.gif)

*↑ **境界だけ持つと 6 % に痩せる** ―― 中実の球(267,731 voxel)を `vol_boundary` で内側 1 層の殻にすると **6.1 %**(16,418 voxel)まで痩せる。その殻を `vol_boundary_points` で mm 座標の点群にして `fit_sphere3` に渡すと、**中心誤差 0.000 mm**(真値 (25.6, 25.6, 25.6) mm)。半径だけは -0.175 mm ずれる — 殻が「内側 1 層」だからで、これは消さずに図に書いてある。 使用 op: `vol_boundary`, `vol_boundary_points`, `fit_sphere3`。*

[![run-length で 1/71](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing3d_rle_compression_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing3d_rle_compression.png)

*↑ **run-length で 1/71** ―― 256³ の合成部品を run-length で持つと **1/71**(16.78 MB → 0.237 MB、19,764 run)。しかも展開せずに体積 1,610,948 voxel を **241 倍速**、BBox を **24 倍速**で返し、集合演算(球 ∪ 軸 = 1,508,456 voxel)も run のまま解ける。decode の往復は bit 一致。 使用 op: `vol_rle_encode`, `vol_rle_decode`, `vol_rle_volume`, `vol_rle_bbox`, `vol_rle_centroid`, `vol_rle_union`, `vol_rle_intersect`, `vol_rle_difference`。*

[![Frangi 対 Sato ―― 否定対照(粒状度)を並べて初めて分かる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing3d_vesselness_control_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing3d_vesselness_control.png)

*↑ **Frangi 対 Sato ―― 否定対照(粒状度)を並べて初めて分かる** ―― 管 1 本と球 2 個だけの合成 CT に、管状度 2 種と粒状度 1 種を掛けた。`vol_frangi` は管を球より **1.26 倍**強く出すが、`vol_sato` は **0.97 倍**でほとんど区別しない。否定対照の `vol_hessian_blobness` は **0.32 倍** = 管より球を選び、向きがきれいに逆転する。「血管が光った」だけでは管状度の証明にならない、という当たり前を図にした。 使用 op: `vol_frangi`, `vol_sato`, `vol_hessian_blobness`。*

![3-D スケルトンをグラフにする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_skeleton_graph.gif)

*↑ **3-D スケルトンをグラフにする** ―― 合成した枝分かれ構造(8,690 voxel)を `skeletonize_vol` に通すと 192 voxel の 1 voxel 幅の針金になる(**2.21 %**)。そこから枝 **4 本**・分岐 **1 か所**・端点 **4 点**をグラフとして取り出した。白が分岐、ローズが端点、枝は連結成分ごとに色分け。ターンテーブルで1 周するとつながり方が読める。 使用 op: `skeletonize_vol`, `skeleton_branches3d`, `skeleton_junctions3d`, `skeleton_endpoints3d`。*

[![virtual probe で壁厚 2.000 mm(真値 2.000 mm)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing3d_wall_thickness_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing3d_wall_thickness.png)

*↑ **virtual probe で壁厚 2.000 mm(真値 2.000 mm)** ―― 外径 10.000 mm / 内径 8.000 mm の合成パイプにプローブを 1 本だけ刺す。`vol_edge_probe` が 4 つのエッジをサブサンプル精度で拾い、`vol_wall_thickness` が立ち上がり→立ち下がりの対から壁厚 **2.0000 mm / 2.0000 mm**(真値 2.000 mm)を返す。平滑化 sigma を 3.0 まで上げると 2.1252 mm (**+6.3 %**)に太る — ノイズ対策がそのまま寸法の偏りになる、という測定の基本も一緒に。 使用 op: `vol_profile_line`, `vol_edge_probe`, `vol_wall_thickness`。*

![Richardson-Lucy ―― 前方一貫性 0.033x に対し真値 RMSE は 0.689x](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_richardson_lucy.gif)

*↑ **Richardson-Lucy ―― 前方一貫性 0.033x に対し真値 RMSE は 0.689x** ―― sigma 2.0 のガウス PSF でぼかした合成ボリュームを `vol_richardson_lucy` で反復復元する。復元をもう一度ぼかして観測と比べる**前方一貫性は 0.033 倍**まで一気に落ちるのに、**真値との RMSE は 0.689 倍**までしか下がらない。残っているのは球のふちの階段で、「観測をよく説明できた」ことは「真値に近い」ことではない ―― という反例をそのまま展示にした。 使用 op: `vol_gaussian_psf`, `vol_richardson_lucy`。*

![visual hull ―― 影を重ねて形を削り出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_visual_hull.gif)

*↑ **visual hull ―― 影を重ねて形を削り出す** ―― L 字の合成物体を 16 方向から撮ったシルエットで `visual_hull` を彫る。1 枚では真の体積の **5.12 倍**という柱状の塊だが、枚数を足すと 16 枚で **1.24 倍**(IoU 0.755)まで縮む。ただし L 字の凹みは何枚重ねても埋まらない ―― これは実装の粗さではなく visual hull の原理的な限界で、収束先が真値でないことが図から読める。 使用 op: `look_at`, `synthesize_silhouette`, `visual_hull`。*

![外から抱く箱(OBB)と中に入る箱(inner_box3)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_obb_innerbox.gif)

*↑ **外から抱く箱(OBB)と中に入る箱(inner_box3)** ―― z 軸まわりに 30° 傾けた合成直方体(13,617 voxel)に 3 つの箱を同時に描いた。軸平行の AABB は **1.99 倍**まで膨らむが、`obb`(PCA で向きを合わせた外接箱)は **0.94 倍**、半幅は 19.99 / 10.00 / 8.00 voxel (真値 20 / 10 / 8)。逆に `inner_box3` の最大内接箱は **0.32 倍**まで痩せる。掴み幅なら OBB、部品が通るかなら内接箱。 使用 op: `obb`, `inner_box3`, `vol_bounding_box`。*

![断層を送る ―― `z = 48 / 95` は 38.40 mm のこと](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_slice_zsweep.gif)

*↑ **断層を送る ―― `z = 48 / 95` は 38.40 mm のこと** ―― 合成 CT(96×128×128、spacing (0.8, 0.3, 0.3) mm)を 1 スライスずつ 96 コマ送る。各コマに**添字と物理位置の両方**(`z = 48 / 95` = 38.40 mm)と位置バーを焼いた。1 スライス送りは 0.80 mm、面内 1 画素は 0.30 mm = **0.37 倍**なので、下の折れ線のとおり「添字を 1 つ動かす」は軸ごとに違う距離を意味する ―― 異方性 CT でいちばん踏みやすい段差。 使用 op: `vol_window_level`。*

![3 直交断面(MPR)とクロスヘア](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_mpr_crosshair.gif)

*↑ **3 直交断面(MPR)とクロスヘア** ―― 同じ 1 点を 3 方向から見る MPR。axial(`vol[z]`)・coronal(`vol[:, y, :]`)・sagittal(`vol[:, :, x]`)を横に並べ、らせん状の目印を追いながら 3 本のクロスヘアを同時に動かした。各パネルに**どの軸が横でどの軸が縦か**を書き、`+x` に球・`-y` に横棒・`+z` にリングという非対称なランドマークを入れてある ―― 軸の入れ替わりや左右反転が起きたら、この 3 つの位置がずれて必ず露見する。 使用 op: `(numpy スライス + imagedraw)`。*

![斜めに切ると円が楕円になる(長径は 1/cos で伸びる)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_oblique_slice.gif)

*↑ **斜めに切ると円が楕円になる(長径は 1/cos で伸びる)** ―― 半径 5.00 mm の合成円柱を、切断面を 0° から 80° まで倒しながら切る(`vol_rotate` の逆回し)。短径は角度によらず 10.000 mm のままなのに、長径は **2r / cos θ** に沿って伸び、80° では 29.238 mm = 2.92 倍になる。36 角度(0°〜70°)すべてで理論値との差は最大 0.0000 mm(0.00 画素)。「斜めの断面で測った直径」をそのまま寸法にしてはいけない、という一本。 使用 op: `vol_rotate`。*

![CT の窓を掃引する ―― 見えるものは窓が決めている](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_window_sweep.gif)

*↑ **CT の窓を掃引する ―― 見えるものは窓が決めている** ―― 同じ 1 枚の断面に `vol_window_level` の窓だけを 70 通り当てる。center を動かすと明るさの基準が、width を動かすと捨てる範囲が変わる。各コマに center / width の実数値と、黒潰れ・白飛びの割合、6 つの組織が「いま何色に見えるか」を焼いた。軟部窓では骨が 1.00 で飽和し、骨窓では軟部と肺が 0 付近に沈む ―― どちらも情報を捨てている、というのが 1 本で見える。 使用 op: `vol_window_level`。*

![等値面のしきい値で面が育ち、くびれ、割れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_isosurface_sweep.gif)

*↑ **等値面のしきい値で面が育ち、くびれ、割れる** ―― 2 つの球をぼかして重ねた合成ボリュームに `voxel_to_mesh`(marching cubes)を掛け、level を 0.06 から 0.82 まで 40 段階で動かした。表面積は 6679 → 2842 voxel² へ縮み、level 0.742 を超えると 1 つだった面が **2 つに割れる**。各コマに level・頂点数・三角形数・表面積・連結成分数を焼いてある。しきい値を書かない 3D 計測は再現できない、ということでもある。 使用 op: `voxel_to_mesh`, `mesh_area`。*

![管に沿って切る ―― 軸に直交しないと内径が 1.13 倍に太る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_vessel_reslice.gif)

*↑ **管に沿って切る ―― 軸に直交しないと内径が 1.13 倍に太る** ―― 28° 傾いた合成管(中央に狭窄)を 49 断面ぶん送る。軸に直交する断面で測った短径は真の内径をほぼそのまま返す(平均誤差 **0.0206 mm**)のに、素朴に z 方向へ切った断面の長径は 1/cos θ = **1.133 倍**に伸びて平均 0.5776 mm ずれる。狭窄部では真値 2.801 mm が素朴断面では 3.217 mm ―― 狭窄が浅く見えてしまう。 使用 op: `vol_rotate`。*

---

## 生成物の実測(読み戻して確認した値)

| 展示 | 形式 | ファイル | 実測 |
|---|---|---|---|
| boundary | GIF+mp4 | `media/wing3d_boundary_shell.gif` | 36 フレーム, 1120x640, 2.75 MB, 128 色, mp4 1.59 MB |
| rle | PNG | `wing3d_rle_compression.png` | 1120x720, 52 kB |
| vesselness | PNG | `wing3d_vesselness_control.png` | 1120x700, 72 kB |
| skeleton | GIF+mp4 | `media/wing3d_skeleton_graph.gif` | 48 フレーム, 1120x660, 1.40 MB, 256 色, mp4 0.26 MB |
| wall | PNG | `wing3d_wall_thickness.png` | 1120x680, 99 kB |
| rl | GIF+mp4 | `media/wing3d_richardson_lucy.gif` | 18 フレーム, 1120x660, 0.63 MB, 256 色, mp4 0.09 MB |
| visualhull | GIF+mp4 | `media/wing3d_visual_hull.gif` | 16 フレーム, 1120x690, 0.73 MB, 256 色, mp4 0.27 MB |
| obb | GIF+mp4 | `media/wing3d_obb_innerbox.gif` | 48 フレーム, 1120x700, 2.26 MB, 256 色, mp4 0.40 MB |
| zsweep | GIF+mp4 | `media/wing3d_slice_zsweep.gif` | 96 フレーム, 1120x748, 1.16 MB, 256 色, mp4 0.16 MB |
| mpr | GIF+mp4 | `media/wing3d_mpr_crosshair.gif` | 60 フレーム, 1120x620, 1.18 MB, 256 色, mp4 0.22 MB |
| oblique | GIF+mp4 | `media/wing3d_oblique_slice.gif` | 36 フレーム, 1120x640, 0.90 MB, 256 色, mp4 0.11 MB |
| windowsweep | GIF+mp4 | `media/wing3d_window_sweep.gif` | 70 フレーム, 1120x660, 1.44 MB, 256 色, mp4 0.20 MB |
| isosurface | GIF+mp4 | `media/wing3d_isosurface_sweep.gif` | 40 フレーム, 1120x640, 1.18 MB, 256 色, mp4 0.31 MB |
| vessel | GIF+mp4 | `media/wing3d_vessel_reslice.gif` | 49 フレーム, 1120x664, 0.98 MB, 256 色, mp4 0.15 MB |
