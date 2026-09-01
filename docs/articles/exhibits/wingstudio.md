# Studio 画面 / 3D 表示ウィング —— 展示キャプション原稿

生成元: `tools/gen_wingstudio_gallery.py`(再実行で全点を再生成)。
Studio 画面はすべて `studio.build_window()` が組み立てた**実 UI** の `widget.grab()`(オフスクリーン)で、モックアップはありません。
3D 展示は fullseye の op と numpy 合成だけで描いています(matplotlib 不使用、文字のみ Pillow)。**数字はすべて実測値**です。

**このファイルは納品原稿です。記事 md への転記は手動で行ってください**(記事本体は意図的に編集していません)。

---

## CT を回す —— 面と粒、同じ角度で

![CT を回す —— 面と粒、同じ角度で](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_volume_turntable.gif)

*↑ **CT を回す —— 面と粒、同じ角度で** —— 同梱の骨格 CT (20×97×28 voxel)を等値面 (mean+std = 0.5108) で三角形 9,710 枚 / 頂点 4,866 のメッシュにしたものと、同じ閾値の境界シェル 2,759 voxel を、**同じ yaw・同じ仰角で並べて回して**います。左は面、右は粒。同じ形が同じ向きに回ることが、軸を取り違えていない何よりの証拠になります(36 フレーム)。 使用 op / 機能: `marching_cubes`, `phong_shade`, `vol_boundary`, `render_points_frame`。*

<sub>`wingstudio_volume_turntable.gif` — 36 フレーム / 12 fps / 996×431 px / 1.12 MB / SHA-256 `c5277f4189bf59f1`</sub>

---

## z スライスを 1 枚ずつ送る

![z スライスを 1 枚ずつ送る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_zslices.gif)

*↑ **z スライスを 1 枚ずつ送る** —— 同じ CT を z = 0 から 19 まで 1 枚ずつ送ります(全 20 フレーム、下のバーが現在位置)。右は全 z を潰した MIP。左の 1 枚には毎フレーム実測した骨占有率・最小/最大/平均を出しているので、**端の 1 枚が欠けている/ 重複している**といった off-by-one はここで必ず露見します。拡大は最近傍 ×6(補間しない —— 画素の粗さ自体が情報)。 使用 op / 機能: `vol_mip`, `apply_cmap`, 最近傍整数拡大。*

<sub>`wingstudio_zslices.gif` — 20 フレーム / 5 fps / 896×726 px / 1.30 MB / SHA-256 `d89832df12dd0ae3`</sub>

---

## 点群を合わせる —— 初期ずれから収束まで

![点群を合わせる —— 初期ずれから収束まで](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_registration.gif)

*↑ **点群を合わせる —— 初期ずれから収束まで** —— 実データ(イトカワ表面 3,000 点)に既知の剛体ずれ 22 度 + 並進 42.451 と等方ノイズ σ = 1.2160 を入れ、trimmed ICP を **1 反復ずつ** 48 回実行した実測の収束です。対応づけ前の素の点間距離平均 74.763 → 1 反復目 22.770 → 最終 1.754(13.0 倍改善)で、注入ノイズの σ にほぼ張り付いて止まります。曲線が下がりきっても橙が青に乗っていなければ「収束したのに合っていない」—— 数字だけでは見えない失敗が、絵にすると一目で分かります。 使用 op / 機能: `registration.icp`(trimmed), `render_points_frame`, `imagedraw.draw_polyline`。*

<sub>`wingstudio_registration.gif` — 48 フレーム / 6 fps / 972×500 px / 0.52 MB / SHA-256 `25a7ea2cfd2e6b4c`</sub>

---

## 法線の色 —— 3D デバッグで最初に見る絵

[![法線の色 —— 3D デバッグで最初に見る絵](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingstudio_normals_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingstudio_normals.png)

*↑ **法線の色 —— 3D デバッグで最初に見る絵** —— itokawa_f0049152.stl (JAXA はやぶさ Gaskell 形状モデル)(三角形 49,152 枚 / 頂点 24,578、表面積 0.399)を表と裏 180 度から撮り、陰影と **world 法線をそのまま RGB にした絵**を並べました。world 法線は「同じ色 = 同じ向き」なので、裏に回っても地面向きの面は同じ色のまま残ります。ここがまだらなら向き付け(巻き方向)が壊れています。実測では外向き面 48,639 / 49,152 = 99.0 %。被覆画素は表 38,540 px / 裏 39,686 px。 使用 op / 機能: `render_mesh`, `phong_shade`, world 法線の RGB 化。*

<sub>`wingstudio_normals.png` — 1840×600 px / 337 kB / SHA-256 `f94a57b604090a34`</sub>

---

## ライトフィールドの視点移動 —— 49 個のカメラで撮る

![ライトフィールドの視点移動 —— 49 個のカメラで撮る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_lightfield.gif)

*↑ **ライトフィールドの視点移動 —— 49 個のカメラで撮る** —— 7×7 = 49 視点 × 128×128 画素の合成ライトフィールドで、アパーチャの周を1 周(全 24 フレーム)します。近いものほど大きく動く —— 中央視点との差がそのまま「どこが手前か」の絵になります。実測の最大視差は 21.33 px、EPI(行 y = 64)の線の傾きがそれに対応します。再合焦の分散は slope = 0 で 0.00682、slope = 3 で 0.01487。 使用 op / 機能: `lf_synthesize`, `lf_subaperture`, `lf_epi`, `lf_refocus`, `lf_stats`。*

<sub>`wingstudio_lightfield.gif` — 24 フレーム / 8 fps / 864×484 px / 2.33 MB / SHA-256 `96b9cf0e8fe3b147`</sub>

---

## 深度マップを持ち上げて 3D にする

![深度マップを持ち上げて 3D にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_depth3d.gif)

*↑ **深度マップを持ち上げて 3D にする** —— itokawa_f0049152.stl を 200×200 px の深度画像にし、有効画素 9,715(24.3 %)だけを逆投影して立体に起こす過程です。深度は 0.7363〜0.8827。ここで **画素中心の規約が 2 つある** ことが効きます —— `render3d` は「添字 + 0.5」を画素中心としてレイを飛ばし、`camera.depth_to_points` は添字そのものを中心とみなすので、素直に繋ぐと雲全体が 0.00229 world 単位(ちょうど半画素)ずれます。この展示は +0.5 側を採用しています。 使用 op / 機能: `render_mesh`, `camera.backproject`, `render_points_frame`。*

<sub>`wingstudio_depth3d.gif` — 30 フレーム / 10 fps / 812×620 px / 0.68 MB / SHA-256 `9979afba20ff75e6`</sub>

---

## 欠陥を CAD 面へ逆写像し、見えていない面を数える

![欠陥を CAD 面へ逆写像し、見えていない面を数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_cadmap.gif)

*↑ **欠陥を CAD 面へ逆写像し、見えていない面を数える** —— SDF から作った段付き部品(三角形 1,400 枚、表面積 8856.6)を 240×240 px の検査カメラで撮り、①見え方 ②画素 → CAD 面 ID ③画像上の欠陥ラベル 4 件の逆写像 ④見えた面(緑)/ 見えない面(赤)を並べました。命中画素 15,980(27.7 %)。カメラを向いている面積は 48.3 % ですが、塔が自分の台座を隠すため **実際に見えたのは 46.8 %**(面数では 608 / 1,400 = 43.4 %)。表面点 26,000 でも可視 41.3 % / 遮蔽 58.7 % と一致します。欠陥 #3 #4 は CAD の外(命中 0)なので実面積 0 のまま残る —— 黙って消えないのが大事なところです。 使用 op / 機能: `cad_pixel_to_surface`, `cad_defect_to_cad`, `cad_visible_faces`, `cad_surface_to_pixel`。*

<sub>`wingstudio_cadmap.gif` — 24 フレーム / 10 fps / 1200×518 px / 0.50 MB / SHA-256 `9537345acb9d7e99`</sub>

---

## 3D の処理領域 —— 切り出して、処理して、貼り戻す

![3D の処理領域 —— 切り出して、処理して、貼り戻す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_crop3d.gif)

*↑ **3D の処理領域 —— 切り出して、処理して、貼り戻す** —— 20×97×28 の CT から y ∈ [20, 56) を margin 2 で切り出すと 20×40×28(offset (z,y,x) = (0, 18, 0))になります。その中だけ勾配を計算し、元の座標系へ貼り戻すまでを 4 段で 3D 表示しました(右は元の全体を灰色で重ねたもの)。往復の実測は **箱の外の最大値 0(厳密に 0)/ 箱の中の元との最大差 0(ビット一致)**。貼り戻しで 1 voxel ずれても 2D の表では気づけませんが、重ねて回せば一発です。 使用 op / 機能: `vol_crop_domain`, `vol_gradient_magnitude`, `vol_uncrop`, `vol_boundary`。*

<sub>`wingstudio_crop3d.gif` — 36 フレーム / 8 fps / 976×491 px / 0.46 MB / SHA-256 `862ef4b4faa3d367`</sub>

---

## F キーで 3D データの中を歩く(実 Studio 画面)

![F キーで 3D データの中を歩く(実 Studio 画面)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_walk.gif)

*↑ **F キーで 3D データの中を歩く(実 Studio 画面)** —— 本物の Fullseye Studio(1280×800 px、オフスクリーン)にイトカワの実形状モデル(頂点 24,578 / 三角形 49,152、スプラット 73,730 点)を開き、**実際の QKeyEvent** で F → W で前進 → ドラッグで見回し → +/- で視野角 → A で左へ → R で入口 → F で軌道カメラへ、と操作した 24 フレームです。透視投影なので近づくほど手前が大きくなり、視野角を変えると遠近感そのものが変わります。1 タップ = 半径/50 = 0.00592 の 1 歩(既定 FOV 70 度、可変域 40〜100 度)。下端の細い帯はこの GIF の進行バーで、UI ではありません。 使用 op / 機能: Studio 3D ビューアの一人称モード(`render_points_frame_fp`)、`viewer3d_project_persp`。*

<sub>`wingstudio_studio_walk.gif` — 24 フレーム / 4 fps / 1280×800 px / 1.59 MB / SHA-256 `8debe840b4191009`</sub>

---

## 軌道カメラで回す —— ボリュームをそのまま 3D ビューアで開く

![軌道カメラで回す —— ボリュームをそのまま 3D ビューアで開く](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_turntable.gif)

*↑ **軌道カメラで回す —— ボリュームをそのまま 3D ビューアで開く** —— 同梱の骨格 CT(20×97×28)を Studio が「ボリュームファイル」として開く経路そのままです。Otsu 閾値 0.5389 で前景を取り、その **境界シェルだけ** を 2,733 点の物理座標に落として(間引き 1/1)表示しています。回しているのは合成ではなく、**実際の左ドラッグ**(1 回 = yaw +12 度)を 30 回送った結果で、最終 yaw は 35 度。 使用 op / 機能: `volume_to_shell_points`(Otsu → 境界シェル)、Studio 3D ビューアの軌道カメラ。*

<sub>`wingstudio_studio_turntable.gif` — 30 フレーム / 10 fps / 1280×800 px / 0.92 MB / SHA-256 `1ee6c8952c0409fe`</sub>

---

## 新しい族の op ヘルプを Studio の中で開く

![新しい族の op ヘルプを Studio の中で開く](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_help.gif)

*↑ **新しい族の op ヘルプを Studio の中で開く** —— ライトフィールド → FMCW レンジドップラ → 四元数モノジェニック → 光子計数(SPAD)→ 音響ビームフォーミング → 干渉(角スペクトル伝搬)→ 3D の ICP・主曲率、と 8 ページを実際に開き、各ページを上から下までスクロールした 24 フレームです。ヘルプ本文は `docs/ops/**/*.md` から自動生成された実ファイル(2D 879 枚 / 3D 310 枚)。族別ディレクトリには合計 155 枚が生成済みで、そのうち Studio から開けるのは `tb_*` 型付き op 経由の 45 枚、残り 110 枚はまだ画面から辿れません(干渉は 9 枚中 0 枚)。 使用 op / 機能: Studio のヘルプダイアログ(`op_help_html` / `op_help_html_3d`)、`tools/opdocs.py` 生成の HTML。*

<sub>`wingstudio_studio_help.gif` — 24 フレーム / 3 fps / 1000×720 px / 0.53 MB / SHA-256 `01b8bd80f77113db`</sub>

---

## 書いて、F5 で走らせて、結果が出るまで

![書いて、F5 で走らせて、結果が出るまで](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_editor.gif)

*↑ **書いて、F5 で走らせて、結果が出るまで** —— タブエディタに 18 行のコードを打ち込み、F5 で実行して出力コンソールを読み下すまでの 24 フレームです(1060×740 px のダイアログ)。実行はモックではなく本物の子プロセスで、ステータスは「PASS ✓ (exit 0)」。出力 6 行の末尾は `foreground fraction = 0.2995` / `objects = 21` / `area  min/median/max = 1118 / 1494 / 3084` —— コインの分割結果です。 使用 op / 機能: Studio の Python エディタ(タブ + F5 実行)、`fullseye.apply`, `fullseye.segment_objects`。*

<sub>`wingstudio_studio_editor.gif` — 24 フレーム / 6 fps / 1060×740 px / 0.35 MB / SHA-256 `80307838551abd4c`</sub>

---

## 900 超の op から目的の 1 個へ

![900 超の op から目的の 1 個へ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_opsearch.gif)

*↑ **900 超の op から目的の 1 個へ** —— 検索欄に 1 文字ずつ「watershed」と打つと、903 個の一覧が 4 件まで絞れます(実測の内訳: (空):903 → w:77 → wa:11 → wat:4 → wate:4 → water:4 → waters:4 → watersh:4 → watershe:4 → watershed:4)。選ぶと `in_sort → out_sort` のシグネチャが右下に出る —— 型が見えるので、次に何を繋げるかがその場で分かります。最後に「cad」で引くと 0 件。 使用 op / 機能: Studio の演算子検索(名前 / HALCON 別名 / 分類 / docstring を横断)。*

<sub>`wingstudio_studio_opsearch.gif` — 17 フレーム / 4 fps / 1280×800 px / 0.54 MB / SHA-256 `0f07b77035141574`</sub>

---

## パイプラインを組む —— 型が合わないと Problems に出る

![パイプラインを組む —— 型が合わないと Problems に出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingstudio_studio_pipeline.gif)

*↑ **パイプラインを組む —— 型が合わないと Problems に出る** —— coins サンプルに `gaussian → otsu → opening_circle → sk_clear_border` を1 段ずつ足していき、⑤でわざと **region を受け取れない** `circularity_xld`(contour 入力)を足します。すると Problems に 「stage 3 (sk_clear_border) outputs 'region' but circularity_xld expects 'contour'」と出る —— Fullseye は繋いだ後に落ちるのではなく、繋いだ瞬間に型の不一致を言います。⑥で外すと「no problems」に戻ります(全 24 フレーム)。 使用 op / 機能: Studio の Program パネル(HDevelop 風)+ Problems、`engine.diagnose_stages`。*

<sub>`wingstudio_studio_pipeline.gif` — 24 フレーム / 4 fps / 1280×800 px / 0.49 MB / SHA-256 `c7d90678baa3e80c`</sub>

---

## 付録: この展示を作る過程で見つかった「見た目の異常」

可視化はバグ発見の道具でもある、という前提で作りました。以下はすべて**実測**で、
op のコードは 1 行も変更していません(判断は著者に委ねます)。

### 1. `(z,y,x) -> (x,y,z)` の `V[:, ::-1]` は軸の入れ替えではなく**鏡映**

`render3d.marching_cubes` はボクセル添字 `(z,y,x)` の頂点を返す。world `(x,y,z)` に
直すために座標だけ反転すると、行列式が -1 なので**全三角形の巻き方向が裏返る**。

```python
Vz, F = render3d.marching_cubes(vol, 0.0)
sv = lambda V, F: float(np.einsum("ij,ij->i", V[F][:,0], np.cross(V[F][:,1], V[F][:,2])).sum()/6)
sv(Vz, F)                       # 期待 +体積 : 実測 +37294.7  (占有ボクセル 35746)
sv(Vz[:, ::-1], F)              # 期待 +体積 : 実測 -37294.7  ← 内向きになった
sv(Vz[:, ::-1], F[:, ::-1])     # 面の巻きも反転して打ち消す : +37294.7
```

### 2. `cadmap` は「内向きに巻かれた閉メッシュ」を黙って受け取り、可視率を過大に返す

上の内向きメッシュに `cull_backfaces=True`(既定)で問い合わせると、本来の遮蔽面が
カリングされて光線が突き抜ける。**閉じているのに符号つき体積が負**という条件は
安価に検出できるので、fail-closed 方針なら弾くか警告してよい箇所だと思います。

| メッシュ | `cad_surface_to_pixel` の可視率 | 面法線がカメラを向く面積 | `cad_visible_faces` の面積比 |
|---|---|---|---|
| 内向き(バグ状態) | **0.857** | 0.517 | 0.508 |
| 外向き(修正後) | 0.415 | 0.483 | 0.468 |

可視率が「カメラを向いている面積」を上回った時点で物理的におかしい、というのが
気づきの糸口でした(遮蔽は減らすことしかできない)。

### 3. 画素中心の規約が 2 つあり、繋ぐと半画素ずれる

`render3d.render_mesh` は `arange + 0.5` を画素中心としてレイを飛ばし
(`render3d.py:318-319`)、主点も `w * 0.5`。一方 `camera.depth_to_points` は
`np.mgrid[0:H, 0:W]` の**整数**添字を画素中心として逆投影する。

```python
pose, K = render3d.auto_view(V, width=200, height=200)      # K[0,2] = 100.0
buf = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=200, height=200)
P_int  = camera.backproject(pix,       buf["depth"][valid], K)   # 添字
P_half = camera.backproject(pix + 0.5, buf["depth"][valid], K)   # 添字 + 0.5
# 実測: 平均 |P_half - P_int| = 0.0022879 world 単位 = ちょうど 0.5 px 相当
```
絵としては見えませんが、寸法計測に使うと系統誤差になります。

### 4. Problems の 1 行の中で stage 番号が 0 起点と 1 起点で混ざる

`engine.diagnose_stages` のメッセージは 0 起点、Studio の Problems リストの見出しは
1 起点なので、同じ 1 行に別の番号体系が並びます。

```
! stage 5 (circularity_xld): stage 3 (sk_clear_border) outputs 'region' but circularity_xld expects 'contour'
```
`sk_clear_border` は Program パネルの行番号でも Problems の見出しでも **4** 段目です。
期待: `stage 4 (sk_clear_border)`。実際: `stage 3 (sk_clear_border)`。

### 5. ボリュームを 3D ビューアで開くと「横倒し」になる

`studio.volume_to_shell_points` は docstring どおり `(z, y, x)` 順の点を返しますが、
消費側(`render_points_frame` / `viewer3d_project`)は **3 番目の成分を world の上方向**
として扱います。つまりボリュームの z 軸(スライス方向)が画面の左右に、x 軸が上下に写る。

```python
v = np.zeros((40, 8, 8)); v[:, 3:5, 3:5] = 1.0     # z 方向に伸びた棒
P, C, info = studio.volume_to_shell_points(v)
P.max(0) - P.min(0)      # 期待(上が z): [1, 1, 39] / 実測: [39, 1, 1]
```
既定の viridis 高さランプ(`colors=None` のとき)も同じ理由で x 添字を色にします。

### 6. 新しい族の生成済みヘルプ 155 枚のうち 110 枚は画面から辿れない

`studio_assets/op_help/<族>/` に `tools/opdocs.py` が生成した HTML が 155 枚あるのに、
Studio のヘルプ検索は 2D 名 + 3D 名しか引かないため、`tb_*` 型付き op として
登録された 45 枚しか開けません。

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

あわせて、開ける 45 枚も「実行できる例」が空で、「同カテゴリ」欄は typed 105 個が
1 カテゴリに同居しているため無関係な op が並びます。

### 7. `vol_mip` は正規化して返す(生の最大値投影ではない)

`ops.RT["vol_mip"]` は表示向けに `[0,1]` へ正規化した像を返します。累積 MIP の
到達率を測るのに使うと分母が変わり、**121.5 %** という値が出ました(実測)。
比率を測る側は `vol.max(axis=0)` を使うべき、という住み分けです。

### 8. GIF の書き出しは「連続する同一フレーム」を 1 枚に畳む

`video.write_video` の GIF 経路(Pillow)は完全同一の連続フレームを結合するので、
静止の「間」を作るために同じ grab を並べると、**18 枚書いて 6 枚しか戻らない**。
書き出し後に読み戻して枚数を突き合わせない限り気づけません(本スクリプトは
毎回突き合わせています)。

### 9. 再現性: 14 点中 12 点は SHA-256 まで一致、2 点は一致しない

`studio_opsearch` は検索欄のクリアボタン(✕)の描画タイミングが揺れ、
`studio_editor` は Studio が実行に使う一時ファイル名(`scratch_<pid>.py`)が
出力コンソールに出るため、生成のたびにバイト列が変わります。**絵の内容は同一**
ですが、bit 単位の再現は保証できません(隠さず書きます)。
