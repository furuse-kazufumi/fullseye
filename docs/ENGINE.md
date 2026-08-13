# FullseyeEngine — 設計したパイプラインを実行するランタイム

`FullseyeEngine`（`engine.py`）は、Fullseye Studio で**組んだ**画像オペレータ・パイプラインを、自分のコードや CLI から**実行する**ためのランタイムです。MVTec の **HDevEngine** に相当します — ビジュアルツールで手順を設計し、書き直すことなくそのままアプリから呼び出す、という 2 段構えの後半を担います。

- **設計（author）**: Fullseye Studio → `Save pipeline` で JSON を書き出す（[STUDIO_GUIDE.md](STUDIO_GUIDE.md)）。
- **実行（execute）**: `FullseyeEngine.load("pipeline.json").run(frame)` — **numpy 配列 in、numpy 配列 out**。ファイル I/O も GUI も不要。

パイプラインは `(op, a, b)` の段のリストです。エンジンは Studio の JSON・`--ops` 文字列・Python のリストのいずれからも読み込め、入出力の sort を調べ、各段のつまみを調整し、numpy フレームに対して（全体・途中まで・1 段ずつ）実行できます。構造検証（未知オペレータ・sort 不整合）も行い、これは Studio の診断パネルと同じチェックです。

---

## 最短の使い方

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # 各段の途中結果（リスト）
```

`FullseyeEngine` と `diagnose_stages` は `fullseye`（および `engine`）から公開されています。

---

## 4 通りの読み込み

| 構築方法 | シグネチャ | 用途 |
|---|---|---|
| JSON ファイル | `FullseyeEngine.load(path)` | Studio の `Save pipeline` 出力を読む |
| ops 文字列 | `FullseyeEngine.from_ops(ops, a=0.5, b=0.5, name="pipeline")` | `"gaussian,sobel_amp,otsu"` のようなカンマ区切り（共通つまみ） |
| dict | `FullseyeEngine.from_dict(d, name="pipeline")` | `{"stages": [...]}` を持つ辞書から |
| 段のリスト | `FullseyeEngine(stages=None, name="pipeline")` | `[("gaussian",0.4,0.5), "otsu"]` を直接（名前だけの段は a=b=0.5） |

`from_dict` は `"stages"` キーが無いと `ValueError`。`load` は JSON を読んで `from_dict` に渡し、ファイル名（拡張子なし）を `name` にします。

---

## メソッド一覧

| メソッド | 返り値 | 説明 |
|---|---|---|
| `load(path)` *(classmethod)* | `FullseyeEngine` | Studio の JSON からロード |
| `from_ops(ops, a=0.5, b=0.5, name=…)` *(classmethod)* | `FullseyeEngine` | カンマ区切り ops 文字列から（共通つまみ） |
| `from_dict(d, name=…)` *(classmethod)* | `FullseyeEngine` | `{"stages": [...]}` からロード |
| `describe()` | `list[dict]` | 段ごとの `{index, op, a, b, in_sort, out_sort, halcon, known}` |
| `op_names()` | `list[str]` | 各段のオペレータ名 |
| `input_sort()` | `str \| None` | パイプラインが期待する入力 sort（最初の既知 op の in_sort） |
| `output_sort()` | `str \| None` | パイプラインが返す出力 sort（最後の既知 op の out_sort） |
| `validate()` | `list[dict]` | 構造問題 `{index, op, severity, message}`。`[]` なら健全 |
| `is_runnable()` | `bool` | すべての段が既知オペレータに解決すれば `True`（error が無い） |
| `get_knobs(i)` | `tuple` | 段 `i` のつまみ `(a, b)` |
| `set_knobs(i, a=None, b=None)` | `self` | 段 `i` のつまみを変更（チェイン可） |
| `run(image, upto=None, coerce=True)` | ndarray / float / dict | パイプラインを実行。`upto` で 0..upto 段のみ |
| `run_stepwise(image, coerce=True)` | `list` | 各段適用後の途中結果（長さ = 段数） |
| `run_file(in_path, out_path=None, upto=None)` | 生の結果 | 画像を読み、実行し、ラスタ結果なら任意で保存 |
| `to_dict()` | `dict` | `{"fullseye_pipeline": 1, "name", "stages"}` |
| `to_ops()` | `str` | カンマ区切り ops 文字列 |
| `to_python()` | `str` | 単体 Python 関数のソース（Studio の Export と同一） |
| `save(path)` | `None` | `to_dict()` を JSON で保存 |
| `len(eng)` | `int` | 段数 |

`diagnose_stages(stages)` はエンジンを作らずに段リストを検証する関数で、`validate()` の実体です。`severity` は未知オペレータで `"error"`、隣接段の sort 不整合で `"warning"`。

### sort（型）について

各オペレータは入力/出力の **sort** を宣言します: `image`（gray H×W float64 [0,1]）/ `region`（二値 {0,1}）/ `color`（H×W×3 RGB）/ `feature`（スカラ float）/ `contour`（XLD dict）/ `volume`（3D stack）/ `any`（何とでも接続）。`validate()` は隣接段の out→in が食い違うと warning を出します（`any` は常に整合）。

---

## Python からの利用例

### 検証してから実行する

```python
import fullseye

eng = fullseye.FullseyeEngine.from_ops("gaussian,sobel_amp,otsu")
problems = eng.validate()
if not eng.is_runnable():                      # error（未知 op）があるなら止める
    raise SystemExit(problems)
result = eng.run(frame)                         # region（二値）を返す
```

### 途中まで / 1 段ずつ

```python
mid = eng.run(frame, upto=1)                    # 0..1 段目まで（gaussian → sobel_amp）
for i, s in enumerate(eng.run_stepwise(frame)):  # 各段の途中結果
    print(i, eng.stages[i][0], getattr(s, "shape", s))
```

### つまみを調整して再実行

```python
eng.set_knobs(0, a=0.3).set_knobs(2, a=0.4)     # チェイン可
out = eng.run(frame)
```

### ファイル入出力（コード内で完結）

```python
eng = fullseye.FullseyeEngine.load("edge.json")
result = eng.run_file("in.png", "out.png")      # 読み込み→実行→ラスタなら保存
```

### 保存・エクスポート

```python
eng.save("edge.json")                           # JSON 保存（Studio で再オープン可）
print(eng.to_ops())                             # "gaussian,sobel_amp,otsu"
print(eng.to_python())                          # 単体 Python 関数として出力
```

`to_python()` の出力例:

```python
import fullseye, numpy as np

def pipeline(frame):
    return fullseye.run_pipeline(frame, [
        ('gaussian', 0.500, 0.500),
        ('sobel_amp', 0.500, 0.500),
        ('otsu', 0.500, 0.500),
    ])
```

---

## CLI: `imgevolve.py run`

保存したパイプライン（JSON または ops 文字列）を CLI から実行できます。内部で `FullseyeEngine` を使います。

```
py -3.11 imgevolve.py run <pipeline.json|ops> [inp] [--out PATH]
                          [--upto N] [--stepwise] [--describe] [--to-python] [--a A] [--b B]
```

| 引数 / オプション | 意味 |
|---|---|
| `pipeline` | パイプライン `.json`（Studio の Save pipeline）またはカンマ区切り ops 文字列 |
| `inp` | 入力画像（省略時は `--describe` / `--to-python` のみ実行可） |
| `--out PATH` | 結果の保存先（ラスタ結果のみ保存） |
| `--upto N` | 0..N 段目までを実行 |
| `--stepwise` | 各段の結果を報告し、`--out` 指定時は `PATH_00`, `PATH_01`, … として保存 |
| `--describe` | パイプラインの I/O と各段・検証結果を表示（入力なしなら表示だけで終了） |
| `--to-python` | パイプラインを Python 関数として出力 |
| `--a` / `--b` | ops 文字列で作る場合の共通つまみ（デフォルト 0.5） |

例:

```powershell
# 構造だけ確認（画像不要）
py -3.11 imgevolve.py run edge.json --describe
#   pipeline 'edge': image -> region
#     0. gaussian      a=0.50 b=0.50   [image -> image]
#     1. sobel_amp     a=0.50 b=0.50   [image -> image]
#     2. otsu          a=0.50 b=0.50   [image -> region]

py -3.11 imgevolve.py run edge.json in.png --out result.png       # 実行して保存
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png  # 各段を保存
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python   # ops 文字列 → Python
```

未知オペレータ（error）を含むパイプラインは `--describe` では表示できますが、実行時には停止して問題を報告します。

---

## 他プロジェクトからの呼び出し（onocollo / evis / hillco など）

`fullseye` は numpy 配列で入出力が完結するので、ロボティクス/ビジョンのパイプラインに直接差し込めます。**設計は Studio、実行は各プロジェクト**という分業が可能です。

```python
import fullseye

# 起動時に一度だけロード（軽量。ops の解決とつまみだけを保持）
PIPELINE = fullseye.FullseyeEngine.load("assets/segment.json")

def perceive(frame):                            # frame: 自前で用意した float64 gray [0,1]
    seg = PIPELINE.run(frame)                   # numpy in, numpy out（ディスク不要）
    return seg
```

ポイント:

- **ファイル I/O 不要**: センサ/シミュレータから得た numpy フレームを直接渡し、numpy を受け取れます。組み込みや GPU シミュレーション環境でも I/O バックエンド無しで動きます。
- **軽量**: `load` / `from_ops` はオペレータ名とつまみを保持するだけ。重い計算は `run` 呼び出し時のみ。
- **バージョン独立**: パイプライン JSON はデータなので、パイプラインを差し替えても呼び出し側コードは不変。研究の反復（パイプラインを Studio で調整 → JSON 更新）が、利用側に波及しません。
- **単一オペレータでよいなら** `fullseye.apply(frame, "otsu")`、複数段なら `fullseye.run_pipeline(frame, [...])` を直接呼んでもよい（エンジンを介さない軽い経路）。

知覚スタック（stereo / terrain / flow / detect / registration / pose）も同じく numpy で動きます（`fullseye.disparity_map` など）。使用例は `examples/`（[../examples/README.md](../examples/README.md)）と [PERCEPTION.md](PERCEPTION.md) / [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md) を参照してください。

---

## 関連ドキュメント

- [STUDIO_GUIDE.md](STUDIO_GUIDE.md) — パイプラインを組んで JSON を書き出す
- [GETTING_STARTED.md](GETTING_STARTED.md) — 5 分ではじめる
- [INSTALL.md](INSTALL.md) — 環境構築（組み込み・最小構成含む）
