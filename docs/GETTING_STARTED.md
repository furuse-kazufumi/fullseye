# はじめかた（5分で動かす）

Fullseye（作業名 imgevolve）を最短で動かすためのガイドです。**インストール → 最初のパイプラインを作る → 実行する → 結果を見る** の順に、詰まらない導線で進めます。より詳しい環境構築は [INSTALL.md](INSTALL.md)、Studio の全機能は [STUDIO_GUIDE.md](STUDIO_GUIDE.md)、コードからの実行は [ENGINE.md](ENGINE.md) を参照してください。

Fullseye は **numpy 配列を入力・出力とする画像処理オペレータ・ライブラリ**であり、その上に **HDevelop 風のビジュアル・パイプライン設計環境（Fullseye Studio）** と **実行ランタイム（FullseyeEngine）** が載っています。HALCON/HDevelop で言えば「HDevelop で手順を組み、HDevEngine で自分のアプリから呼ぶ」という 2 段構えを、そのまま Python + numpy で再現したものです。

---

## 1. インストール（1分）

前提: **Python 3.11**（Windows は `py -3.11`、Linux は `python3.11`）。

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .          # numpy + scipy のコアだけ（約 521 オペレータ）
```

コアは **numpy と scipy だけ**で動きます。OpenCV / scikit-image / Pillow などの追加バックエンドは任意で、入っていなくても、そのバックエンド固有のオペレータだけが無効になるだけです（graceful degradation）。実務では最低でも画像ファイルの読み書きに OpenCV か Pillow が要るので、次のどちらかを足しておくと快適です。

```powershell
py -3.11 -m pip install -e ".[opencv]"    # 画像 I/O + OpenCV 由来オペレータ
py -3.11 -m pip install -e ".[all]"       # 全バックエンド（opencv, skimage, pil, wavelets, gpu, extra）
py -3.11 -m pip install -e ".[gui]"       # Fullseye Studio（PySide6）を使うなら
```

extras の一覧と意味は [INSTALL.md](INSTALL.md) にまとめてあります。GUI を使うなら `[gui]`（または `[all]` + `[gui]`）が必要です。

> インストールせずに試すこともできます。リポジトリ直下（`<path-to-fullseye>`）を作業ディレクトリにし、環境変数 `PYTHONPATH` にそのパスを通せば `import fullseye` は動きます。ただし `fullseye` / `fullseye-studio` というコマンド（コンソールスクリプト）は `pip install -e .` を実行して初めて使えるようになります。

---

## 2. まず 1 個のオペレータを動かす（Python）

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

edges = fullseye.apply(frame, "sobel_amp")     # image → image（勾配強度）
seg   = fullseye.apply(frame, "otsu")          # image → region（0/1 の二値）
n     = fullseye.apply(seg,   "count_obj")     # region → feature（オブジェクト数＝Python float）
print(n)                                       # 例: 316.0
```

- `apply(image, name, a=0.5, b=0.5)` は **1 個のオペレータ**を適用します。`name` は **オペレータ名**（例 `gaussian`）でも **HALCON エイリアス**（例 `gauss_filter`）でも解決されます。
- `a`、`b` は各オペレータが持つ **2 つのつまみ（0.0〜1.0）**。意味はオペレータごとに異なります（半径・しきい値・σ など）。
- 出力の型（sort）はオペレータで決まります: `image`（gray）/ `region`（二値）/ `feature`（スカラ float）/ `color`（RGB）/ `contour`（XLD）/ `volume`（3D）。

どんなオペレータがあるかは次で探せます。

```python
fullseye.op_names()                 # 全レジストリ・オペレータ名（521 個）
fullseye.list_ops(search="edge")    # 名前 / HALCON 名 / カテゴリを部分一致で検索
fullseye.list_ops(sort="region")    # 入力 sort で絞り込み
fullseye.categories()               # 31 カテゴリ
```

---

## 3. パイプラインを組む（複数オペレータをつなぐ）

複数のオペレータを順に通すのが「パイプライン」です。配列を各段にスレッドして最終結果を返します。

```python
# 全段で同じ a, b を使う（CLI と同じ形）
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])

# 段ごとに違うつまみを使いたいとき（(name, a, b) のタプルで指定）
out = fullseye.run_pipeline(frame, [("gaussian", 0.3, 0.5), ("otsu", 0.4, 0.5)])
```

これは「smooth（平滑化）→ エッジ強度 → Otsu 二値化」で、画像から二値のエッジマップを作る典型例です。すぐ使える組み合わせ（レシピ）は **20 個**同梱されています。

```python
import recipes
recipes.names()                                   # レシピ名の一覧
stages = recipes.stages("Edge — Sobel + Otsu")    # [(op, a, b), ...]
out = fullseye.run_pipeline(frame, stages)
```

---

## 4. ビジュアルに組む（Fullseye Studio）

コードを書かずに、オペレータを検索して並べ、つまみをスライダーで回し、1 段ずつ実行して途中結果を目で見ながら組めます。GUI extras（`pip install -e ".[gui]"` = PySide6）が必要です。

```powershell
py -3.11 studio.py          # または、インストール済みなら: fullseye-studio
```

3 パネル構成です。

- **左（Operators）**: オペレータをカテゴリ / 検索で絞り、**ダブルクリックで挿入**。サンプルパイプラインもここから読み込めます。
- **中央（Pipeline）**: 並べた段の一覧。ドラッグや Ctrl+↑/↓ で並べ替え、選択した段の **つまみ a / b をスライダー**で調整。**Reset（Home）→ Step（Ctrl+→）→ Run all（Ctrl+Enter）** で 1 段ずつ、または一気に実行。
- **右（Image / Perception / Analysis）**: 結果画像をズーム・パン表示、ヒストグラム、Inspector（image / region / feature の値を検査）、v14 の知覚パネル（オプティカルフロー / ステレオ深度など）。

組んだパイプラインは **Export（Ctrl+E）** で `--ops` 文字列や Python コードとして書き出せ、**Save pipeline（Ctrl+Shift+S）** で JSON 保存できます。全機能とショートカットは [STUDIO_GUIDE.md](STUDIO_GUIDE.md)、アプリ内では **F1** で一覧が出ます。

---

## 5. 保存したパイプラインを実行する（CLI / コード）

Studio で `Save pipeline` した JSON（あるいは `--ops` 文字列）を、そのままファイルに対して実行できます。これが HDevEngine 相当の「設計したものを書き直さずに実行する」経路です。

```powershell
# 保存した JSON の I/O と各段を確認（画像なしで構造チェック）
py -3.11 imgevolve.py run edge.json --describe

# 画像に適用して結果を保存
py -3.11 imgevolve.py run edge.json in.png --out result.png

# 1 段ずつ結果を保存（result_00.png, result_01.png, ...）
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png

# パイプラインを単体 Python 関数として書き出す
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python
```

コードから実行する場合は `FullseyeEngine` を使います（詳細は [ENGINE.md](ENGINE.md)）。

```python
import fullseye
eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # 各段の途中結果（リスト）
```

---

## 6. 1 個ずつ CLI で適用する

画像ファイルを直接処理したいときは CLI が手軽です（画像 I/O に OpenCV か Pillow が必要）。

```powershell
py -3.11 imgevolve.py ops --search edge                    # オペレータを検索
py -3.11 imgevolve.py has gauss_filter                     # HALCON 名が実装済みか + 呼び方
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py pipeline in.png out.png --ops "gaussian,sobel_amp,otsu"
```

`apply` / `pipeline` は各段で共通の `--a` / `--b` を取ります。段ごとに違うつまみを使いたいときは、上の `run_pipeline`（Python）か Studio を使ってください。

---

## つまずいたら

| 症状 | 対処 |
|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | `pip install -e .` を実行するか、リポジトリ直下を `PYTHONPATH` に通す |
| `fullseye` / `fullseye-studio` コマンドが無い | コンソールスクリプトは `pip install -e .` で登録される。未インストールなら `py -3.11 imgevolve.py ...` / `py -3.11 studio.py` を使う |
| Studio が起動しない | GUI extras 未導入。`pip install -e ".[gui]"`（PySide6） |
| `apply` / `pipeline` で `cannot read ...` | 画像 I/O 用に OpenCV（`[opencv]`）か Pillow（`[pil]`）を入れる |
| 追加バックエンドのオペレータが「unknown」 | そのバックンドが未導入。`.[skimage]` `.[wavelets]` `.[extra]` などを足す |

より詳しいトラブルシュートは [INSTALL.md](INSTALL.md) を参照してください。

## 次に読む

- **[INSTALL.md](INSTALL.md)** — 環境構築の完全ガイド（extras の使い分け、Windows/Linux インストーラ、最小構成・組み込み）
- **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** — Fullseye Studio 完全ガイド
- **[ENGINE.md](ENGINE.md)** — FullseyeEngine（設計 → 実行）ガイド
- **[README.md](README.md)** — ドキュメント索引
