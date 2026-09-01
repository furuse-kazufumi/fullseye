# Studio 画面 / 3D 表示ウィング —— 展示キャプション原稿

生成元: `tools/gen_wingstudio_gallery.py`(再実行で全点を再生成)。
Studio 画面はすべて `studio.build_window()` が組み立てた**実 UI** の `widget.grab()`(オフスクリーン)で、モックアップはありません。
3D 展示は fullseye の op と numpy 合成だけで描いています(matplotlib 不使用、文字のみ Pillow)。**数字はすべて実測値**です。

**このファイルは納品原稿です。記事 md への転記は手動で行ってください**(記事本体は意図的に編集していません)。

---

## CT を回す —— 面と粒、同じ角度で

![CT を回す —— 面と粒、同じ角度で](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_volume_turntable.gif)

*↑ **CT を回す —— 面と粒、同じ角度で** —— 同梱の骨格 CT (20×97×28 voxel)を等値面 (mean+std = 0.5108) で三角形 9,710 枚 / 頂点 4,866 のメッシュにしたものと、同じ閾値の境界シェル 2,759 voxel を、**同じ yaw・同じ仰角で並べて回して**います。左は面、右は粒。同じ形が同じ向きに回ることが、軸を取り違えていない何よりの証拠になります(36 フレーム)。 使用 op / 機能: `marching_cubes`, `phong_shade`, `vol_boundary`, `render_points_frame`。*

<sub>`wingstudio_volume_turntable.gif` — 36 フレーム / 12 fps / 996×640 px / 1.05 MB / SHA-256 `b6386d706b8b91e2`</sub>

---

## z スライスを 1 枚ずつ送る

![z スライスを 1 枚ずつ送る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_zslices.gif)

*↑ **z スライスを 1 枚ずつ送る** —— 同じ CT を z = 0 から 19 まで 1 枚ずつ送ります(全 20 フレーム、下のバーが現在位置)。右は全 z を潰した MIP。左の 1 枚には毎フレーム実測した骨占有率・最小/最大/平均を出しているので、**端の 1 枚が欠けている/ 重複している**といった off-by-one はここで必ず露見します。拡大は最近傍 ×5(補間しない —— 画素の粗さ自体が情報)。 使用 op / 機能: `vol_mip`, `apply_cmap`, 最近傍整数拡大。*

<sub>`wingstudio_zslices.gif` — 20 フレーム / 5 fps / 612×633 px / 0.71 MB / SHA-256 `46eddbd8fd732f16`</sub>

---
