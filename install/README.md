# Fullseye インストーラ

Fullseye（画像処理オペレータライブラリ / パイプライン設計）と **Fullseye Studio**
（PySide6 製 GUI ワークベンチ）を、**1 コマンド**で導入・起動できるようにする
クロスプラットフォーム インストーラです。

- **Windows**: `install.ps1` / `uninstall.ps1`
- **Linux・macOS**: `install.sh` / `uninstall.sh`
- スタート メニュー / デスクトップ（Windows）、アプリメニュー（Linux）に
  「**Fullseye Studio**」ランチャーを作成します。

インストーラは **venv（`<repo>/.venv`）を既定**とし、システムの Python を汚しません。
何度実行しても壊れない（**冪等**）よう作ってあります。

---

## 前提

- **Python 3.11**（3.10 以上でも可）。
  - Windows: `py -3.11 --version` が通ること（Python 公式インストーラの
    "py launcher" を入れておくと確実）。
  - Linux/macOS: `python3.11`（無ければ `python3`）が 3.10 以上であること。
- インターネット接続（pip が依存パッケージを取得します）。
- 既定の `all,gui` は **torch / opencv などを含み数百 MB～** になります。
  軽く済ませたい場合は後述の `--minimal` / `-Minimal` を使ってください。

> **extras について（重要）**
> Fullseye Studio の GUI は `gui` extra（PySide6）に依存します。
> pyproject の `all` extra には **GUI が含まれない**ため、本インストーラは
> 既定で **`all,gui`** をインストールします（`all` の全バックエンド＋GUI）。

---

## Windows

PowerShell を開き、リポジトリのルートで実行します
（エクスプローラで `install.ps1` を右クリック →「PowerShell で実行」でも可）。

```powershell
# 標準（venv + 全 extras + GUI、ショートカット作成）
powershell -ExecutionPolicy Bypass -File install\install.ps1

# 軽量（core + GUI のみ。torch/opencv 等の重い依存を省く）
powershell -ExecutionPolicy Bypass -File install\install.ps1 -Minimal

# venv を作らず user-site へ入れる
powershell -ExecutionPolicy Bypass -File install\install.ps1 -UserSite

# extras を明示指定（例: GUI + OpenCV + scikit-image）
powershell -ExecutionPolicy Bypass -File install\install.ps1 -Extras "gui,opencv,skimage"

# ショートカットを作らない
powershell -ExecutionPolicy Bypass -File install\install.ps1 -NoShortcut
```

### 起動方法（Windows）

- **ショートカット**: デスクトップ / スタート メニューの「**Fullseye Studio**」
- **コンソールスクリプト**: `.venv\Scripts\fullseye-studio.exe`
- **直接**: `py -3.11 studio.py`
- **CLI**: `.venv\Scripts\fullseye.exe --help`

### アンインストール（Windows）

```powershell
# ショートアップ削除 + fullseye パッケージ削除（venv は残す）
powershell -ExecutionPolicy Bypass -File install\uninstall.ps1

# venv ごと削除
powershell -ExecutionPolicy Bypass -File install\uninstall.ps1 -RemoveVenv
```

---

## Linux / macOS

まず実行権限を付けてから実行します（`bash` 経由なら chmod は不要）。

```bash
# bash 経由（chmod 不要）
bash install/install.sh

# もしくは実行権限を付けて直接
chmod +x install/install.sh install/uninstall.sh
./install/install.sh
```

### オプション（Linux/macOS）

```bash
bash install/install.sh --minimal                 # core + GUI のみ
bash install/install.sh --user-site               # venv を作らず --user
bash install/install.sh --extras "gui,opencv"     # extras を明示
bash install/install.sh --no-shortcut             # .desktop を作らない
bash install/install.sh --repo /path/to/imgevolve # リポジトリを明示
```

### 起動方法（Linux/macOS）

- **アプリメニュー**: 「**Fullseye Studio**」
- **コンソールスクリプト**: `.venv/bin/fullseye-studio`
- **直接**: `.venv/bin/python studio.py`
- **CLI**: `.venv/bin/fullseye --help`

### アンインストール（Linux/macOS）

```bash
bash install/uninstall.sh                 # .desktop 削除 + パッケージ削除
bash install/uninstall.sh --remove-venv   # venv ごと削除
```

---

## トラブルシュート

- **`py -3.11` が見つからない（Windows）**
  Python 3.11 を <https://www.python.org/downloads/> から入れ、インストール時に
  "Add python.exe to PATH" と "py launcher" にチェックを入れてください。

- **`python3.11` が見つからない（Linux）**
  - Debian/Ubuntu: `sudo apt install python3.11 python3.11-venv`
  - Fedora: `sudo dnf install python3.11`
  - macOS: `brew install python@3.11`

- **`venv` 作成に失敗（Debian/Ubuntu）**
  `python3.11-venv` パッケージが必要です（上記コマンドで導入）。

- **PowerShell の実行ポリシーで弾かれる**
  `-ExecutionPolicy Bypass` を付けて起動してください（上の例のとおり）。
  この指定はそのプロセス限りで、システム設定は変更しません。

- **GUI が起動しない / PySide6 が無いと言われる**
  `-Minimal`（Windows）/ `--minimal`（Linux）でも **GUI（PySide6）は入ります**。
  それでも駄目な場合は venv の pip で `pip install PySide6>=6.5` を試してください。
  Linux では追加のシステムライブラリ（例: `libEGL`, `libxkbcommon`, `xcb` 系）が
  必要になることがあります。ディストリのパッケージで補ってください。

- **torch / opencv のダウンロードが重い・失敗する**
  `-Minimal` / `--minimal`（`gui` extra のみ）で導入すれば、Studio と core の
  ~75 オペレータは動きます。個別バックエンドは後から
  `pip install -e ".[opencv]"` のように追加できます。

- **ショートカットのアイコンが出ない（Linux）**
  `.desktop` は `assets/fullseye_256.png` を参照します（Linux は `.ico` を
  メニュー表示できないため PNG を使用）。メニューへの反映には再ログインや
  `update-desktop-database` が要る環境があります。

---

## 導入内容の確認（検証済みの経路）

このインストーラの pip 経路は temp venv で実証済みです:

```
python -m venv <tmp>
<tmp>/Scripts/python -m pip install -e "<repo>[gui]"
python -c "import fullseye, PySide6, numpy, scipy"   # -> OK
# コンソールスクリプト fullseye(.exe) / fullseye-studio(.exe) が生成される
```

`gui` extra（core + PySide6）での editable インストールと import は確認済みです。
`all`（torch 等）を含む完全版はダウンロードが大きいため各環境で実行してください。
（経路・仕組みは同一です。）
