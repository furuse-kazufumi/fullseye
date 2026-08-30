# インストール / 環境構築 完全ガイド

Fullseye（作業名 imgevolve）を、開発機から組み込み Linux まで、目的に応じて構築するためのガイドです。5 分で動かすだけなら [GETTING_STARTED.md](GETTING_STARTED.md) が近道です。

Fullseye の設計方針は **「numpy + scipy だけで動くコア」+「重い依存はすべて optional」**。追加バックエンドが無くても、そのバックエンド固有のオペレータだけが無効になるだけで、コアは常に動きます（graceful degradation）。

---

## (a) 前提

| 項目 | 要件 |
|---|---|
| Python | **3.11**（`pyproject.toml` の `requires-python = ">=3.10"`。開発・検証は 3.11） |
| 実行コマンド | Windows: `py -3.11` / Linux: `python3.11` |
| コア依存 | `numpy>=1.23`, `scipy>=1.9`（`pip install -e .` で自動導入） |
| OS | Windows 10/11、Linux（組み込み含む）。macOS も Python が動けば可 |

---

## (b) pip install（extras の意味と使い分け）

リポジトリ直下で editable install します。

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .            # コアのみ（numpy + scipy、約 521 オペレータ）
```

追加バックエンドは **extras** で選びます（`pyproject.toml` の `[project.optional-dependencies]` が実体）。

| extras | 追加される依存 | 何が有効になるか |
|---|---|---|
| `opencv` | `opencv-python>=4.6` | 画像ファイル I/O（`apply`/`pipeline` CLI が必須とする）、`cv_*` 系オペレータ |
| `skimage` | `scikit-image>=0.20` | `sk_*` / `xsk_*` 系（多数の自動生成オペレータの土台） |
| `pil` | `Pillow>=9` | 画像 I/O のフォールバック、`xpil_*` 系（emboss/posterize/solarize 等） |
| `wavelets` | `PyWavelets>=1.4` | ウェーブレット系（VisuShrink/サブバンド/パケット等） |
| `gpu` | `torch>=2.0`, `kornia>=0.7` | GPU バッチバックエンド（`accel.py`/`bench.py`）、`xkor_*`（kornia）系 |
| `extra` | `mahotas>=1.4`, `SimpleITK>=2.2` | `xsitk_*`（curvature flow 等）、mahotas 由来（Zernike/pftas 等） |
| `gui` | `PySide6>=6.5` | **Fullseye Studio**（`studio.py` / `fullseye-studio`） |
| `all` | 上記 GUI 以外の全部（opencv, skimage, pil, wavelets, gpu, extra） | 全オペレータ・バックエンド |

使い分けの目安:

```powershell
# 実務でよく使う最小＋画像 I/O（GUI 不要、コード/CLI 中心）
py -3.11 -m pip install -e ".[opencv]"

# GUI（Studio）も使う
py -3.11 -m pip install -e ".[opencv,gui]"

# フル装備（GUI 込み。all は GUI を含まないので gui を併記）
py -3.11 -m pip install -e ".[all,gui]"

# GPU バッチ経路も試す（要 CUDA 対応 torch）
py -3.11 -m pip install -e ".[gpu]"
```

> `all` には **`gui` は含まれません**（GUI は用途が分かれるため別枠）。Studio を使うなら必ず `gui` を明示的に足してください。

インストールが成功すると、次の **2 つのコンソールスクリプト**が使えるようになります（`[project.scripts]`）。

| コマンド | 実体 | 相当する直接実行 |
|---|---|---|
| `fullseye` | `imgevolve:main`（CLI） | `py -3.11 imgevolve.py ...` |
| `fullseye-studio` | `studio:main`（GUI） | `py -3.11 studio.py` |

未インストールで試したい場合は、リポジトリ直下を `PYTHONPATH` に通せば `import fullseye` は動きます（コンソールスクリプトは使えません）。

```powershell
$env:PYTHONPATH = "<path-to-fullseye>"
py -3.11 -c "import fullseye; print(fullseye.version())"      # 0.1.0
```

---

## (c) Windows インストーラ

`install\install.ps1` を実行すると、環境構築とデスクトップ連携が一括で行われます（PowerShell）。

```powershell
cd <path-to-fullseye>
powershell -ExecutionPolicy Bypass -File install\install.ps1
```

このインストーラを実行すると、おおよそ次が行われます。

- Python 3.11 の存在確認
- `pip install -e .`（必要な extras 込み）による Fullseye の導入
- **Fullseye Studio のショートカット（`Fullseye Studio.lnk`）の作成** — コンソール窓を出さずに起動できるよう `pyw.exe` 経由で登録され、`assets\fullseye.ico` のアイコンが付きます

以後、スタートメニュー / デスクトップのショートカットから Studio を起動できます。

> 実行ポリシーで止まる場合は `-ExecutionPolicy Bypass` を付けてください（上記コマンドに含まれています）。

---

## (d) Linux インストーラ + `.desktop` ランチャ

`install/install.sh` を実行すると、Linux 環境で同等の構築が行われます。

```bash
cd /path/to/imgevolve
bash install/install.sh
```

このスクリプトを実行すると、おおよそ次が行われます。

- `python3.11` の存在確認
- `pip install -e .`（必要な extras 込み）
- **`.desktop` ランチャの作成** — アプリケーションメニューから Fullseye Studio を起動できるよう、`assets/fullseye.ico` をアイコンにしたデスクトップエントリが登録されます

以後、デスクトップ環境のアプリ一覧から Studio を起動できます。

---

## (e) 最小構成 / 組み込み（embedded Linux）

Fullseye のコアは **numpy + scipy だけ**で動くよう作られています。GUI・GPU・重いバックエンドが不要な組み込み用途では、コアだけを入れれば十分です。

```bash
python3.11 -m pip install -e .        # numpy + scipy のみ。GUI/torch/opencv 不要
```

組み込みでの使い方の要点:

- **numpy 配列で入出力が完結**します。ファイル I/O を一切介さずに、センサ/カメラから得た numpy フレームを直接渡せます。

  ```python
  import fullseye, numpy as np
  frame = get_camera_frame()                       # 自前で取得した float64 gray [0,1]
  seg = fullseye.apply(frame, "otsu")              # ディスクへの書き出し不要
  out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
  ```

- **ファイル I/O が必要なとき**（`fullseye.load` / `fullseye.save`、`imgevolve.py run`、examples）は **OpenCV か Pillow のどちらか**があれば動きます（`imgio` が自動でフォールバック）。組み込みで軽さを優先するなら Pillow（`[pil]`）が小さめです。
- **設計は開発機、実行は組み込み機**という分業ができます。開発機の Studio でパイプラインを組んで JSON を書き出し、組み込み機では `FullseyeEngine.load("pipeline.json").run(frame)` で実行するだけ（GUI 不要）。詳細は [ENGINE.md](ENGINE.md)。
- **知覚スタック**（stereo / terrain / flow / detect / registration / pose）も numpy + scipy で動きます（`fullseye.disparity_map` など）。ロボット/ビジョン用途で追加依存なしに使えます。

> GPU（`torch`）はあくまで **バッチ高速化の opt-in** です。組み込みの単画像処理では不要で、入れなくてもすべてのオペレータが CPU で動きます。

---

## (f) よくあるトラブル

| 症状 | 原因 | 対処 |
|---|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | 未インストール／パス未設定 | `pip install -e .`、または `PYTHONPATH` にリポジトリ直下を追加 |
| `fullseye` / `fullseye-studio` コマンドが見つからない | コンソールスクリプト未登録 | `pip install -e .` を実行。未インストールなら `py -3.11 imgevolve.py` / `py -3.11 studio.py` |
| Studio 起動時に PySide6 の ImportError | GUI extras 未導入 | `pip install -e ".[gui]"` |
| `apply` / `pipeline` で `cannot read <path>` | 画像 I/O バックエンド無し | `pip install -e ".[opencv]"`（または `[pil]`） |
| `read_image` / `write_image`（API）で cv2 の ImportError | これらは **OpenCV 専用** | `pip install -e ".[opencv]"`。Pillow で済ませたいなら `fullseye.load` / `fullseye.save` を使う |
| `list_ops` に期待したオペレータが無い / `has` が unknown | 該当バックエンド未導入 | 対応する extras（`skimage`/`wavelets`/`extra` 等）を追加 |
| GPU バッチ（`accel`/`bench`）が CPU で遅い | `torch` が CPU 版 | GPU では `--device cuda`。CPU では自明な pointwise は変換コストで不利（設計どおり） |
| Studio の 3D surface が開かない | `QtDataVisualization` 不在 | best-effort 機能。PySide6 のバージョン/構成に依存し、無ければ静かにスキップ |

### 画像 I/O の依存関係（重要）

ファイル読み書きの必要バックエンドは経路によって異なります。

| 経路 | 必要バックエンド |
|---|---|
| `fullseye.load` / `fullseye.save`（= `imgio`）、`imgevolve.py run`、examples | **OpenCV または Pillow**（どちらか一方でよい／自動フォールバック） |
| `imgevolve.py apply` / `pipeline` | **OpenCV 必須** |
| `fullseye.read_image` / `fullseye.write_image`（API） | **OpenCV 必須** |

numpy 配列を直接渡す `apply` / `run_pipeline` / `FullseyeEngine.run` は、**画像 I/O バックエンドを一切必要としません**（コアの numpy + scipy だけで動く）。

---

## 動作確認

```powershell
py -3.11 imgevolve.py coverage        # honest な被覆数（269/2313 HALCON op 実装）
py -3.11 imgevolve.py ops --search edge
py -3.11 -c "import fullseye; print(fullseye.version(), len(fullseye.op_names()), 'ops')"
```

`fullseye.version()` は `0.1.0`、`op_names()` は 521 個のレジストリ・オペレータを返します。
