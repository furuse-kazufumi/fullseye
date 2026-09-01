![投影からボクセルまで ―― CT の一本道](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingct_pipeline.gif)

*↑ **投影からボクセルまで、CT の一本道** ―― ファントム → 投影 → サイノグラム → 再構成 → 窓 → 分離 → ボクセル → メッシュ の 8 工程。体積が閉形式で分かる部品(真値 16839 mm³)を 128 本の投影から作り直すと 16896 mm³(+0.3%)になった。再構成 nRMS 0.0177、メッシュ 67744 面、境界点群 27696 点。使用 op: `radon_volume`, `fbp_volume`, `vol_window_level`, `vol_label`, `vol_region_props`, `marching_cubes`, `vol_boundary_points`。*

![投影数を増やすと像が立ち上がる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingct_view_sweep.gif)

*↑ **投影数を増やすと像が立ち上がる、が体積はそれを教えない** ―― 同じ被写体を 8 / 16 / 32 / 64 / 128 本で撮り直す。**16 本以降**、再構成の nRMS は 0.2341 → 0.0334 と 7.0 倍良くなるのに、体積は +0.38% → +0.34% と 0.04% しか動かない ―― ストリークは物体のまわりに正負が対称に出るので、体積という 1 つの積分量では相殺して消えてしまう。**8 本だけは別**で、そこは体積 +3.4% も含めて指標そのものが信用できない領域(同じ部品を面内 128 画素で測り直すと -0.0% になり再現しない)。壊れを教えるのは体積ではなく連結成分の数(175 個 対 1 個)。使用 op: `projection_angles`, `ellipse_sinogram`, `filtered_backprojection`。*

[![投影数と体積誤差のタイル](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_view_tiles_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_view_tiles.png)

*↑ **同じものをタイルでも** ―― 左上が真値、以下が 8 / 16 / 32 / 64 / 128 本。ラベルは再構成 nRMS と体積誤差。8 本ではストリークで頭蓋の内側がまったく読めず、16 本でもまだ縞が残る。ところが体積誤差のほうは 16 本ですでに +0.38% で、128 本の +0.34% と見分けがつかない ―― **絵が良くなっていく過程が、体積という 1 つの数字には現れない**。使用 op: `ellipse_phantom`, `ellipse_sinogram`, `filtered_backprojection`。*

![回転中心のずれ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingct_center_shift.gif)

*↑ **回転中心が半画素ずれると、もう二重像になる** ―― 0 / 0.5 / 1 / 2 画素。再構成の nRMS は 0.0250 → 0.0537 → 0.1016 → 0.1630。**半画素で誤差が 2.1 倍**になるが、見た目は「少し眠い画像」で、間違いには見えない。`sinogram_center_of_rotation` は重心の恒等式からこれを 0.0029 px の誤差で当てる。使用 op: `sinogram_center_shift`, `sinogram_center_of_rotation`。*

[![角度範囲が足りないとき](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_limited_angle_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_limited_angle.png)

*↑ **角度範囲が足りないと、特定の向きの輪郭だけが消える** ―― 180 / 120 / 90 / 60 度。中心スライス定理どおり、撮らなかった角度の帯だけが空になる。30 度ごとの周波数保持率で見ると、90 度スキャンでは撮った側が 0.96 を保つのに撮らなかった側は 0.07 まで落ちる。全体がぼけるのではなく**方向が消える**ので、残った方向は鋭いままで、それが説得力を持ってしまう。使用 op: `ellipse_sinogram`, `filtered_backprojection`。*

[![ビームハードニング(カッピング偽像)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_beam_hardening_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_beam_hardening.png)

*↑ **ビームハードニング ―― 一様な円板の中心がへこむ** ―― 実際の X 線は単色ではないので、厚い経路を通った線ほどビームが硬くなり、線積分が経路長に比例しなくなる。一様な円板の中心/縁の比が 1.0006 → 0.9335 に沈み、`beam_hardening_correct` が 1.0006 に戻す。差分図(青=減った / 橙=増えた)が、沈んだのが中心だけであることを示す。使用 op: `beam_hardening_apply`, `beam_hardening_correct`。*

[![リング偽像](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_rings_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_rings.png)

*↑ **リング偽像 ―― 検出器 1 画素の狂いが 1 本の円になる** ―― ゲインが g の検出器は対数を取ったあと **どの角度でも同じ定数**だけずれる。定数の列を逆投影すると回転軸まわりの完全な円になる。ゲインばらつき 2 % で nRMS が 0.0250 → 0.0643(2.6 倍)、`ring_artifact_remove` で 0.0358(被害の 72% を回復)。使用 op: `ring_artifact_apply`, `ring_artifact_remove`。*

[![体積の答え合わせ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_volume_check_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingct_volume_check.png)

*↑ **体積の答え合わせ ―― 何が効いて、何が効かないか** ―― 真値 16839 mm³(閉形式)、この格子で二値化しただけの天井が 16863 mm³。左は投影数 16→128 で振れ幅 8 mm³(8 本を含めると 522 mm³ になるが、その点は格子を変えると再現しない)、右は二値化しきい値 0.30→0.70 で振れ幅 533 mm³。**しきい値の任意性のほうが 71 倍効く**ので、体積を報告するときに書くべきなのは「何本で撮ったか」より「どのしきい値で切ったか」。使用 op: `radon_volume`, `fbp_volume`, `vol_label`, `vol_region_props`。*
