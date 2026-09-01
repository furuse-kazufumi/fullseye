# Studio 画面 / 3D 表示ウィング —— 展示キャプション原稿(日本語)

生成元: `tools/gen_wingstudio_gallery.py`(再実行で全点を再生成)。
Studio 画面はすべて `studio.build_window()` が組み立てた**実 UI** の `widget.grab()`(オフスクリーン)で、モックアップはありません。
3D 展示は fullseye の op と numpy 合成だけで描いています(matplotlib 不使用、文字のみ Pillow)。**数字はすべて実測値**です。

**このファイルは納品原稿です。記事 md への転記は手動で行ってください**(記事本体は意図的に編集していません)。英語版は `wingstudio.en.md`。

---

## CT を回す —— 面と粒、同じ角度で

![CT を回す —— 面と粒、同じ角度で](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_volume_turntable.gif)

*↑ **CT を回す —— 面と粒、同じ角度で** —— 同梱の骨格 CT (20×97×28 voxel)を等値面 (mean+std = 0.5108) で三角形 9,710 枚 / 頂点 4,866 のメッシュにしたものと、同じ閾値の境界シェル 2,759 voxel を、**同じ yaw・同じ仰角で並べて回して**います。左は面、右は粒。同じ形が同じ向きに回ることが、軸を取り違えていない何よりの証拠になります(36 フレーム)。 使用 op / 機能: `marching_cubes`, `phong_shade`, `vol_boundary`, `render_points_frame`。*

<sub>`wingstudio_volume_turntable.gif` — 36 フレーム / 12 fps / 996×431 px / 1.12 MB / SHA-256 `1cb0def25c830444`</sub>

---

## z スライスを 1 枚ずつ送る

![z スライスを 1 枚ずつ送る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_zslices.gif)

*↑ **z スライスを 1 枚ずつ送る** —— 同じ CT を z = 0 から 19 まで 1 枚ずつ送ります(全 20 フレーム、下のバーが現在位置)。右は全 z を潰した MIP。左の 1 枚には毎フレーム実測した骨占有率・最小/最大/平均を出しているので、**端の 1 枚が欠けている/ 重複している**といった off-by-one はここで必ず露見します。拡大は最近傍 ×6(補間しない —— 画素の粗さ自体が情報)。 使用 op / 機能: `vol_mip`, `apply_cmap`, 最近傍整数拡大。*

<sub>`wingstudio_zslices.gif` — 20 フレーム / 5 fps / 896×726 px / 1.30 MB / SHA-256 `1241579b9480c167`</sub>

---

## 点群を合わせる —— 初期ずれから収束まで

![点群を合わせる —— 初期ずれから収束まで](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_registration.gif)

*↑ **点群を合わせる —— 初期ずれから収束まで** —— 実データ(イトカワ表面 3,000 点)に既知の剛体ずれ 22 度 + 並進 42.451 と等方ノイズ σ = 1.2160 を入れ、trimmed ICP を **1 反復ずつ** 48 回実行した実測の収束です。対応づけ前の素の点間距離平均 74.763 → 1 反復目 22.770 → 最終 1.754(13.0 倍改善)で、注入ノイズの σ にほぼ張り付いて止まります。曲線が下がりきっても橙が青に乗っていなければ「収束したのに合っていない」—— 数字だけでは見えない失敗が、絵にすると一目で分かります。 使用 op / 機能: `registration.icp`(trimmed), `render_points_frame`, `imagedraw.draw_polyline`。*

<sub>`wingstudio_registration.gif` — 48 フレーム / 6 fps / 972×500 px / 0.52 MB / SHA-256 `995ef59ea259ded0`</sub>

---

## 法線の色 —— 3D デバッグで最初に見る絵

[![法線の色 —— 3D デバッグで最初に見る絵](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingstudio_normals_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingstudio_normals.png)

*↑ **法線の色 —— 3D デバッグで最初に見る絵** —— itokawa_f0049152.stl (JAXA はやぶさ Gaskell 形状モデル)(三角形 49,152 枚 / 頂点 24,578、表面積 0.399)を表と裏 180 度から撮り、陰影と **world 法線をそのまま RGB にした絵**を並べました。world 法線は「色 = 向き」なので、面が滑らかに繋がっていれば色も滑らかに繋がります。ごま塩状にまだらなら巻き方向(向き付け)が壊れている合図。実測では外向き面 48,639 / 49,152 = 98.96 %(残り 1 % は非凸の小惑星に「重心から外向きか」という判定を当てたことによる取りこぼし)。被覆画素は表 38,540 px / 裏 39,686 px。 使用 op / 機能: `render_mesh`, `phong_shade`, world 法線の RGB 化。*

<sub>`wingstudio_normals.png` — 1840×600 px / 339 kB / SHA-256 `155b586afb9f5615`</sub>

---

## ライトフィールドの視点移動 —— 49 個のカメラで撮る

![ライトフィールドの視点移動 —— 49 個のカメラで撮る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_lightfield.gif)

*↑ **ライトフィールドの視点移動 —— 49 個のカメラで撮る** —— 7×7 = 49 視点 × 128×128 画素の合成ライトフィールドで、アパーチャの周を1 周(全 24 フレーム)します。近いものほど大きく動く —— 中央視点との差がそのまま「どこが手前か」の絵になります。実測の最大視差は 21.33 px、EPI(行 y = 64)の線の傾きがそれに対応します。再合焦の分散は slope = 0 で 0.00682、slope = 3 で 0.01487。 使用 op / 機能: `lf_synthesize`, `lf_subaperture`, `lf_epi`, `lf_refocus`, `lf_stats`。*

<sub>`wingstudio_lightfield.gif` — 24 フレーム / 8 fps / 864×484 px / 2.33 MB / SHA-256 `bcca4f45d63d9d65`</sub>

---

## 深度マップを持ち上げて 3D にする

![深度マップを持ち上げて 3D にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_depth3d.gif)

*↑ **深度マップを持ち上げて 3D にする** —— itokawa_f0049152.stl を 200×200 px の深度画像にし、有効画素 9,715(24.3 %)だけを逆投影して立体に起こす過程です。深度は 0.7363〜0.8827。ここで効くのが **画素中心の規約** です —— `render3d` も `camera.depth_to_points` も `cadmap` も画素中心を**整数添字**に揃えたので、逆投影した点を投影し直すと残差 rms は 1.31e-14 px(= 丸め誤差)に収まります。うっかり +0.5 を足すと雲全体が 0.00229 world 単位、全点が同じ側へ系統的にずれます。 使用 op / 機能: `render_mesh`, `camera.backproject`, `render_points_frame`。*

<sub>`wingstudio_depth3d.gif` — 30 フレーム / 10 fps / 812×620 px / 0.68 MB / SHA-256 `6ed4d91ac7009986`</sub>

---

## 欠陥を CAD 面へ逆写像し、見えていない面を数える

![欠陥を CAD 面へ逆写像し、見えていない面を数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_cadmap.gif)

*↑ **欠陥を CAD 面へ逆写像し、見えていない面を数える** —— SDF から作った段付き部品(三角形 1,400 枚、表面積 8856.6)を 240×240 px の検査カメラで撮り、①見え方 ②画素 → CAD 面 ID ③画像上の欠陥ラベル 4 件の逆写像 ④見えた面(緑)/ 見えない面(赤)を並べました。命中画素 15,980(27.7 %)。カメラを向いている面積は 48.3 % ですが、塔が自分の台座を隠すため **実際に見えたのは 46.8 %**(面数では 608 / 1,400 = 43.4 %)。表面点 26,000 でも可視 41.3 % / 遮蔽 58.7 % と一致します。欠陥 #3 #4 は CAD の外(命中 0)なので実面積 0 のまま残る —— 黙って消えないのが大事なところです。 使用 op / 機能: `cad_pixel_to_surface`, `cad_defect_to_cad`, `cad_visible_faces`, `cad_surface_to_pixel`。*

<sub>`wingstudio_cadmap.gif` — 24 フレーム / 10 fps / 1200×518 px / 0.50 MB / SHA-256 `eda5aa159d5dd0c4`</sub>

---

## 3D の処理領域 —— 切り出して、処理して、貼り戻す

![3D の処理領域 —— 切り出して、処理して、貼り戻す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_crop3d.gif)

*↑ **3D の処理領域 —— 切り出して、処理して、貼り戻す** —— 20×97×28 の CT から y ∈ [20, 56) を margin 2 で切り出すと 20×40×28(offset (z,y,x) = (0, 18, 0))になります。その中だけ勾配を計算し、元の座標系へ貼り戻すまでを 4 段で 3D 表示しました(右は元の全体を灰色で重ねたもの)。往復の実測は **箱の外の最大値 0(厳密に 0)/ 箱の中の元との最大差 0(ビット一致)**。貼り戻しで 1 voxel ずれても 2D の表では気づけませんが、重ねて回せば一発です。 使用 op / 機能: `vol_crop_domain`, `vol_gradient_magnitude`, `vol_uncrop`, `vol_boundary`。*

<sub>`wingstudio_crop3d.gif` — 36 フレーム / 8 fps / 976×491 px / 0.46 MB / SHA-256 `3902cbec3f013592`</sub>

---

## F キーで 3D データの中を歩く(実 Studio 画面)

![F キーで 3D データの中を歩く(実 Studio 画面)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_walk.gif)

*↑ **F キーで 3D データの中を歩く(実 Studio 画面)** —— 本物の Fullseye Studio(1280×800 px、オフスクリーン)にイトカワの実形状モデル(頂点 24,578 / 三角形 49,152、スプラット 73,730 点)を開き、**実際の QKeyEvent** で F → W で前進 → ドラッグで見回し → +/- で視野角 → A で左へ → R で入口 → F で軌道カメラへ、と操作した 24 フレームです。透視投影なので近づくほど手前が大きくなり、視野角を変えると遠近感そのものが変わります。1 タップ = 半径/50 = 0.00592 の 1 歩(既定 FOV 70 度、可変域 40〜100 度)。下端の細い帯はこの GIF の進行バーで、UI ではありません。 使用 op / 機能: Studio 3D ビューアの一人称モード(`render_points_frame_fp`)、`viewer3d_project_persp`。*

<sub>`wingstudio_studio_walk.gif` — 24 フレーム / 4 fps / 1280×800 px / 2.93 MB / SHA-256 `bec27bc1ab57984b`</sub>

---

## 軌道カメラで回す —— ボリュームをそのまま 3D ビューアで開く

![軌道カメラで回す —— ボリュームをそのまま 3D ビューアで開く](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_turntable.gif)

*↑ **軌道カメラで回す —— ボリュームをそのまま 3D ビューアで開く** —— 同梱の骨格 CT(20×97×28)を Studio が「ボリュームファイル」として開く経路そのままです。Otsu 閾値 0.5389 で前景を取り、その **境界シェルだけ** を 2,733 点の物理座標に落として(間引き 1/1)表示しています。回しているのは合成ではなく、**実際の左ドラッグ**(1 回 = yaw +12 度)を 30 回送った結果で、最終 yaw は 35 度。 使用 op / 機能: `volume_to_shell_points`(Otsu → 境界シェル)、Studio 3D ビューアの軌道カメラ。*

<sub>`wingstudio_studio_turntable.gif` — 30 フレーム / 10 fps / 1280×800 px / 0.92 MB / SHA-256 `02c1ff44094868fe`</sub>

---

## 新しい族の op ヘルプを Studio の中で開く

![新しい族の op ヘルプを Studio の中で開く](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_help.gif)

*↑ **新しい族の op ヘルプを Studio の中で開く** —— ライトフィールド → FMCW レンジドップラ → 四元数モノジェニック → 光子計数(SPAD)→ 音響ビームフォーミング → 干渉(角スペクトル伝搬)→ 3D の ICP・主曲率、と 8 ページを実際に開き、各ページを上から下までスクロールした 24 フレームです。ヘルプ本文は `docs/ops/**/*.md` から自動生成された実ファイル(2D 879 枚 / 3D 310 枚)。族別ディレクトリには合計 155 枚が生成済みで、そのうち Studio から開けるのは `tb_*` 型付き op 経由の 45 枚、残り 110 枚はまだ画面から辿れません(干渉は 9 枚中 0 枚)。 使用 op / 機能: Studio のヘルプダイアログ(`op_help_html` / `op_help_html_3d`)、`tools/opdocs.py` 生成の HTML。*

<sub>`wingstudio_studio_help.gif` — 24 フレーム / 3 fps / 1000×720 px / 0.53 MB / SHA-256 `c61185a31e5cbf8d`</sub>

---

## 書いて、F5 で走らせて、結果が出るまで

![書いて、F5 で走らせて、結果が出るまで](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_editor.gif)

*↑ **書いて、F5 で走らせて、結果が出るまで** —— タブエディタに 18 行のコードを打ち込み、F5 で実行して出力コンソールを読み下すまでの 24 フレームです(1060×740 px のダイアログ)。実行はモックではなく本物の子プロセスで、ステータスは「PASS ✓ (exit 0)」。出力 6 行の末尾は `foreground fraction = 0.2995` / `objects = 21` / `area  min/median/max = 1118 / 1494 / 3084` —— コインの分割結果です。 使用 op / 機能: Studio の Python エディタ(タブ + F5 実行)、`fullseye.apply`, `fullseye.segment_objects`。*

<sub>`wingstudio_studio_editor.gif` — 24 フレーム / 6 fps / 1060×740 px / 0.36 MB / SHA-256 `fc35f56ab0340f6f`</sub>

---

## 900 超の op から目的の 1 個へ

![900 超の op から目的の 1 個へ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_opsearch.gif)

*↑ **900 超の op から目的の 1 個へ** —— 検索欄に 1 文字ずつ「watershed」と打つと、903 個の一覧が 4 件まで絞れます(実測の内訳: (空):903 → w:79 → wa:11 → wat:4 → wate:4 → water:4 → waters:4 → watersh:4 → watershe:4 → watershed:4)。選ぶと `in_sort → out_sort` のシグネチャが右下に出る —— 型が見えるので、次に何を繋げるかがその場で分かります。最後に「cad」で引くと 0 件。 使用 op / 機能: Studio の演算子検索(名前 / HALCON 別名 / 分類 / docstring を横断)。*

<sub>`wingstudio_studio_opsearch.gif` — 17 フレーム / 4 fps / 1280×800 px / 0.54 MB / SHA-256 `8270e44188b4b2a6`</sub>

---

## パイプラインを組む —— 型が合わないと Problems に出る

![パイプラインを組む —— 型が合わないと Problems に出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_pipeline.gif)

*↑ **パイプラインを組む —— 型が合わないと Problems に出る** —— coins サンプルに `gaussian → otsu → opening_circle → sk_clear_border` を1 段ずつ足していき、⑤でわざと **region を受け取れない** `circularity_xld`(contour 入力)を足します。すると Problems に 「stage 4 (sk_clear_border) outputs 'region' but circularity_xld expects 'contour'」と出る —— Fullseye は繋いだ後に落ちるのではなく、繋いだ瞬間に型の不一致を言います。⑥で外すと「no problems」に戻ります(全 24 フレーム)。 使用 op / 機能: Studio の Program パネル(HDevelop 風)+ Problems、`engine.diagnose_stages`。*

<sub>`wingstudio_studio_pipeline.gif` — 24 フレーム / 4 fps / 1280×800 px / 0.54 MB / SHA-256 `0fdcb11fdc1bceca`</sub>

---

## 付録: この展示を作る過程で見つかった「見た目の異常」と、その後

可視化はバグ発見の道具でもある、という前提で作りました。ここに出す数字はすべて
**実測**です。報告した 8 件のうち **5 件は本体側で修正済み**、**2 件は未解決**、
1 件は仕様どおりでした。修正済みは「こうだった → こう直った」の形で残します
(消してしまうと、なぜ今の形なのかが分からなくなるため)。

### 修正済み(5 件)

#### 1. GIF の書き出しが「連続する同一フレーム」を 1 枚に畳んでいた

**こうだった** —— `video.write_video` の GIF 経路(Pillow)は完全に同一の連続フレームを
結合するので、静止の「間」を作るために同じ grab を並べると **18 枚書いて 6 枚しか
戻らない**。書き出し後に読み戻して枚数を突き合わせない限り気づけませんでした。

**こう直った** —— GIF は `video._write_gif_all_frames` が Pillow を直接駆動し、
重複フレームも 1 枚ずつ保存します(代償はファイルサイズ)。同じ再現で実測:

```python
seq = [base] * 6 + [other] * 6 + [base] * 6      # 18 枚(連続同一の塊が 3 つ)
video.write_video(path, seq, fps=6)
# 実測: wrote 18 frames -> read back 18
```

本スクリプトの `save_gif` は、直ったあとも毎回読み戻して枚数を照合します
(検算を外す理由が無いため)。

#### 2. ボリュームを 3D ビューアで開くと「横倒し」になっていた

**こうだった** —— `studio.volume_to_shell_points` が `(z, y, x)` 順の点を返す一方、
消費側(`render_points_frame` / `viewer3d_project`)は **3 番目の成分を world の
上方向**として扱うため、スライス方向が画面の左右に寝ていました。既定の viridis
高さランプも同じ理由で x 添字を色にしていました。

**こう直った** —— この関数が「voxel の並び順 → ビューアの world」の境界になり、
world `(x, y, z)` を返します。`spacing`(`(sz, sy, sx)`)も添字と一緒に反転されます。

```python
v = np.zeros((40, 8, 8)); v[:, 3:5, 3:5] = 1.0      # z 方向に伸びた棒
P, C, info = studio.volume_to_shell_points(v)
P.max(0) - P.min(0)      # 実測 [1.0, 1.0, 39.0](3 番目 = 上 が長い)
info["axis_order"]       # 実測 "xyz"(規約を表明する印)
studio.volume_to_shell_points(v, spacing=(2.0, 1.0, 1.0))   # 実測 [1.0, 1.0, 78.0]
```

展示「軌道カメラで回す」はこの経路そのものなので、図の向きも直っています。

#### 3. 画素中心の規約が 2 つあり、繋ぐと半画素ずれていた

**こうだった** —— `render3d.render_mesh` は「添字 + 0.5」を画素中心としてレイを
飛ばし、`camera.depth_to_points` は整数添字を中心として逆投影していたので、
素直に繋ぐと雲全体が半画素ぶん、しかも**全点が同じ側へ**ずれました。

**こう直った** —— `render3d` / `camera` / `cadmap` が **整数添字**という 1 つの規約に
揃い(主点も `(w - 1) * 0.5`)、逆投影 → 再投影が閉じます。この展示での実測:

| 測ったもの | 実測 |
|---|---|
| 逆投影 → 再投影の残差 rms | **1.31e-14 px**(= 丸め誤差) |
| うっかり +0.5 を足したときの雲のずれ | 0.00229 world 単位(= 半画素、fx = 241.42) |

#### 4. `cadmap` が「内向きに巻かれた閉メッシュ」を黙って受けていた

**こうだった** —— `cull_backfaces=True`(既定)だと本来の遮蔽面がカリングされて
光線が突き抜け、可視率が **0.857** と過大に出ました。「カメラを向いている面積」
0.517 を上回った時点で物理的にありえません(遮蔽は減らすことしかできない)—— それが
気づきの糸口でした。

**こう直った** —— 巻き方向を検める箇所が 1 つにまとまり、閉じているのに符号つき体積が
負なら **直したうえで `winding_fixed` で申告**します。`cad_visible_faces` は既定で拒否、
`strict=True` なら 3 つとも `ValueError`。段付き部品(1,400 面、符号つき体積 ±37290.4)
で実測:

| 呼び方 | 内向きメッシュ | 外向きメッシュ |
|---|---|---|
| `cad_surface_to_pixel` の可視率 | **0.4129**(`winding_fixed=True`) | 0.4129(`winding_fixed=False`) |
| `cad_surface_to_pixel(strict=True)` | `ValueError` | 0.4129 |
| `cad_visible_faces`(既定) | `ValueError` | 608 面 |

ただし **呼ぶ側の注意は消えていません**。`(z,y,x) -> (x,y,z)` の `V[:, ::-1]` は軸の
入れ替えではなく**鏡映**(行列式 -1)なので、座標だけ反転すると全三角形の巻きが
裏返ります。本スクリプトの `voxel_mesh_to_world` は面の巻きも同時に反転して
打ち消しています。

```python
Vz, F = render3d.marching_cubes(vol, 0.0)         # 内側ボクセル 35,746
signed_volume(Vz, F)                     # 実測 +37294.7
signed_volume(Vz[:, ::-1], F)            # 実測 -37294.7  ← 内向きになった
signed_volume(Vz[:, ::-1], F[:, ::-1])   # 実測 +37294.7  ← 打ち消した
```

#### 5. Problems の 1 行の中で stage 番号が 0 起点と 1 起点で混ざっていた

**こうだった** —— `engine.diagnose_stages` のメッセージは 0 起点、Studio の Problems の
見出しは 1 起点。同じ 1 行に別の番号体系が並び、読者を違う段へ案内していました。

```
! stage 5 (circularity_xld): stage 3 (sk_clear_border) outputs 'region' but ...
```
(`sk_clear_border` は Program パネルでも Problems の見出しでも **4** 段目)

**こう直った** —— `message` は人が読む散文として **1 起点に統一**され、機械が使う
`index` / `prev_index`(0 起点、行の選択にそのまま使える)と `prev_op` が別に載ります。
展示⑤の実測はこうなります:

```
! stage 5 (circularity_xld): stage 4 (sk_clear_border) outputs 'region' but circularity_xld expects 'contour'
```

### 未解決(2 件)

#### 6. 新しい族の生成済みヘルプ 155 枚のうち 110 枚が画面から辿れない

`studio_assets/op_help/<族>/` に `tools/opdocs.py` が生成した HTML が 155 枚あるのに、
Studio のヘルプ検索は 2D 名 + 3D 名しか引かないため、`tb_*` 型付き op として
登録された 45 枚しか開けません(今回の再生成でも同じ内訳です)。

| 族 | 生成済み | `tb_*` 経由で開ける | 開けない |
|---|---|---|---|
| acoustics | 19 | 3 | 16 |
| interferometry | 9 | 0 | **9** |
| lightfield | 17 | 8 | 9 |
| math | 26 | 6 | 20 |
| motionmag | 9 | 2 | 7 |
| optics | 18 | 1 | **17** |
| photon | 17 | 6 | 11 |
| quat | 19 | 12 | 7 |
| rangedoppler | 8 | 4 | 4 |
| specular | 13 | 3 | 10 |
| **合計** | **155** | **45** | **110** |

あわせて、開ける 45 枚も「実行できる例」が空で、「同カテゴリ」欄は typed op が
1 カテゴリに同居しているため無関係な op が並びます —— 展示の図でそのまま見えます。

#### 7. `vol_mip` の正規化が `ops.py` 本体には書かれていない

`ops.RT["vol_mip"]` は表示向けに `[0,1]` へ正規化した像を返すので、累積 MIP の
到達率の**分母**に使うと 100 % を超えます。同梱の骨格 CT(20×97×28、生の値域は
最大 1.2264)で実測:

| 分母に使ったもの | 完全な累積 MIP の到達率 |
|---|---|
| `ops.RT["vol_mip"](vol, 0.0, 0.0)` | **122.64 %** |
| `vol.max(axis=0)`(生の投影) | 100.00 % |

`volops.py` と `volio.py` の module docstring には注記が入りましたが、
`ops.py` の `_vol_mip` 本体と登録表には何も書かれていないので、`ops.py` だけを
読む人には見えません。op の挙動自体は「表示用なら正規化が正しい」ので、
これはバグではなく**使い分けの明記漏れ**です。

### 仕様どおりだったもの(1 件)

* **演算子ブラウザに「ツリー」は無い** —— 実装は 1 枚のリスト + 検索欄 + 分類コンボで、
  ツリー表示はもともとありません。展示のキャプションも「一覧」と書いています。

### 再現性(今回、全点を 2 回生成して実測)

14 点中 **11 点は SHA-256 まで一致**し、3 点は一致しません。内訳:

| 展示 | 何が揺れるか | 実測 |
|---|---|---|
| `studio_editor` | Studio が実行に使う一時ファイル名 `scratch_<pid>.py` が出力コンソールに出る | 1 フレームの 8×27 px 領域だけが最大 191 階調ぶん変わる |
| `studio_pipeline` | Pipeline パネルの**段ごとの実測 ms**(壁時計)が写り込む | 一覧の枠内 444 px が変わる |
| `studio_opsearch` | 描画タイミングのゆらぎ(局所的な文字の差は無し) | 1,741 万画素中 13,317 px、最大 29 階調 |

残りの差は GIF のパレット再量子化(中央値 1〜2 階調)で、**絵の内容は同一**です。
`studio_pipeline` は今回 Problems パネルを前面に出したので、以前は写っていなかった
実測 ms が入り、bit 再現しなくなりました —— 主役(型不一致の 1 行)が見えることを
優先しています。
