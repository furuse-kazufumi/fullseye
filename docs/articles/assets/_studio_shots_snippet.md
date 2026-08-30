# Studio スクリーンショット — GALLERY.md / 記事への挿入用スニペット

生成元: `tools/gen_studio_screenshots.py`(再実行で全画像を再生成可能)。
すべて `studio.build_window()` が組み立てた実際の Studio UI の `widget.grab()`
(3D surface のみ実 GL の `Q3DSurface.renderToImage`)で、モックアップ・合成は一切なし。
フルサイズ PNG + 幅 720px サムネイル(`*_thumb.jpg`, JPG q85)を
`docs/articles/assets/` に配置済み。

**注意: このファイルは納品スニペット。GALLERY.md と記事 md への転記は手動で行う**
(自動編集は他作業と衝突するため意図的にしていない)。

---

## A. GALLERY.md へ追記する節(そのままコピー可)

```markdown
### 1.x Studio スクリーンショット(`studio_*.png`)

生成元: `tools/gen_studio_screenshots.py`。すべて `studio.build_window()` が組み立てた
実際の Studio UI をヘッドレスで `grab()` した本物の画面です(3D surface のみ実 GL
コンテキストでの `Q3DSurface.renderToImage`)。モックアップはありません。

![studio_main](articles/assets/studio_main.png)

| 画像 | 内容 |
|---|---|
| `studio_main.png` | メインウィンドウ。coins サンプル画像に blob 分割パイプライン(gaussian → otsu → opening_circle → sk_clear_border)を適用し、region overlay 表示で 21 個のコインを重畳表示。下部 Program パネルに HDevelop 風のパイプラインコード、右に演算子ブラウザ(検索+シグネチャ表示)、ステータスバーに `21 obj` |
| `studio_3d_surface.png` | Ctrl+3 で開く回転可能な 3-D surface ビュー(Q3DSurface)。データは小惑星イトカワの Gaskell 形状モデル(JAXA はやぶさ)を `render3d.render_mesh` で深度画像化した実データの起伏。アプリ内ではこのビューをマウスドラッグで回転・ホイールでズームできる(画像は renderToImage による同一 GL シーンの静止画) |
| `studio_python_editor.png` | Python Editor(タブ式・複数スクリプト同時編集)。`examples_3d/itokawa_curvature.py` を開いて F5 実行した直後で、下部コンソールに実際のイトカワ曲率解析の出力(PASS, exit 0)がストリームされている |
| `studio_3d_examples.png` | 3-D Examples ギャラリー(105 の実データ worked example)。itokawa_curvature を選択して Run した直後で、Output タブにグラウンドトゥルース検証つきの実行結果(PASS) |
| `studio_3d_ops.png` | 3-D Operators リファレンス(265 op)。icp_point2plane の生成済みヘルプページ(呼び出しシグネチャ・使い方・実行できる検証済みサンプル・型が繋がる次の op へのリンク) |

![studio_3d_surface](articles/assets/studio_3d_surface.png)
![studio_python_editor](articles/assets/studio_python_editor.png)
![studio_3d_examples](articles/assets/studio_3d_examples.png)
![studio_3d_ops](articles/assets/studio_3d_ops.png)
```

---

## B. 記事へ挿入する候補スニペット(raw GitHub URL・サムネ使用)

### B-1. Studio メイン画面(パイプライン workbench)

```markdown
Fullseye Studio は HDevelop 風のビジュアルパイプライン workbench です。左に結果ビュー
(ホイールでズーム、ドラッグでパン)、下に Program パネル、右に演算子ブラウザという構成で、
op を選んでつなぎ、ノブを回すと結果がライブ更新されます。下の画面は coins サンプルに
blob 分割パイプラインを適用し、検出した 21 枚のコインを region overlay で重畳した状態です。

![Fullseye Studio メイン画面](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_main_thumb.jpg)
*Studio メイン画面 — coins サンプル + blob 分割パイプライン(region overlay 表示、ステータスバーに 21 obj)*
```

### B-2. 3D surface ビュー(マウスで回転・ズーム)

```markdown
深度画像や高さ場は Ctrl+3 で回転可能な 3-D surface ビューに切り替えられます。
マウスドラッグで視点を回し、ホイールでズームしながら起伏を確認できます。下の画像は
小惑星イトカワの実形状モデル(JAXA はやぶさ / Gaskell モデル)を深度レンダした起伏を
表示したもので、アプリ内ではこのシーンをそのままマウスで動かせます。

![Studio 3D surface ビュー(イトカワ)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_3d_surface_thumb.jpg)
*Ctrl+3 の 3-D surface ビュー — イトカワ実形状の深度起伏(マウスで回転・ズーム可能)*
```

### B-3. Python Editor(IDE 面)

```markdown
Studio には タブ式の Python Editor も組み込まれています。worked example をそのまま
開いて編集し、F5 で(リポジトリを PYTHONPATH に載せた)サブプロセス実行、出力は下の
コンソールにストリームされます。下の画面はイトカワ曲率解析の example を実行した直後です。

![Studio Python Editor](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_python_editor_thumb.jpg)
*Python Editor — itokawa_curvature.py を F5 実行(PASS, exit 0)。実データの曲率統計が出力されている*
```

### B-4. 3-D Examples ギャラリー + Operators リファレンス

```markdown
3-D 側は 105 本の worked example(実イトカワ点群・骨格 CT・合成データ)をギャラリーから
選んでその場で Run でき、265 の 3-D op それぞれに生成済みヘルプページ(シグネチャ・
使い方・検証済みサンプルへのリンク・型が繋がる次の op)が付いています。

![Studio 3-D Examples ギャラリー](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_3d_examples_thumb.jpg)
*3-D Examples ギャラリー — itokawa_curvature を選択して Run した直後(Output に PASS)*

![Studio 3-D Operators リファレンス](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_3d_ops_thumb.jpg)
*3-D Operators リファレンス — icp_point2plane のヘルプページ*
```

---

## 画像ファイル一覧

| フルサイズ PNG | サムネ(幅 720) | 解像度 |
|---|---|---|
| `studio_main.png` | `studio_main_thumb.jpg` | 1680×1000 |
| `studio_3d_surface.png` | `studio_3d_surface_thumb.jpg` | 1500×950 |
| `studio_python_editor.png` | `studio_python_editor_thumb.jpg` | 1500×950 |
| `studio_3d_examples.png` | `studio_3d_examples_thumb.jpg` | 1500×900 |
| `studio_3d_ops.png` | `studio_3d_ops_thumb.jpg` | 1500×900 |
