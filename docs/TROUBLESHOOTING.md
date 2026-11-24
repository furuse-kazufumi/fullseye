# Windows のトラブルシューティング

まず、**失敗したのと同じ Python** で次を実行します。表示の `Checked` は推測ではなく、その実行で確認した値です。`fullseye doctor --json` はサポート窓口や自動化に渡せます。`--fix` は変更内容を先に表示し、対話端末で確認を得た可逆な修復だけを行います。現在の自動修復は、存在しない場所を指すユーザー環境変数 `QT_PLUGIN_PATH` の削除です。CI、パイプ、端末のない起動では何も変えません。

```powershell
py -3.11 -m fullseye doctor
py -3.11 -m fullseye doctor --json
```

Studio、CLI、MCP が起動時に失敗した場合も、元の例外を詳細として残したうえで、このコマンドを案内します。C/C++ SDK が入っている環境では `fullseye doctor` がその `python -m fullseye.sdk --doctor --json` も呼んで結果をまとめます。

| ID | 症状 | 原因 | 確かめ方 | 直しの命令 / 操作 |
|---|---|---|---|---|
| <!-- doctor: console_encoding --> `console_encoding` | `UnicodeEncodeError`、日本語や `—` をパイプへ出すと止まる | 出力先が cp932 | `fullseye doctor` の `stdout encoding` | `chcp 65001; $env:PYTHONUTF8='1'` を同じ PowerShell で実行 |
| <!-- doctor: long_path --> `long_path` | 深い venv や展開で `File name too long`、260 文字付近で失敗 | MAX_PATH / Win32 long paths が無効 | `LongPathsEnabled=0` | 管理者で Windows の「長いパスを有効にする」を有効化して再起動。急ぎなら `C:\src` のような短い場所へ置く |
| <!-- doctor: unicode_space_path --> `unicode_space_path` | 一部の native tool だけが起動しない | 日本語または空白を含むパスを引用していない | doctor の `Python path` | パスを常に `"..."` で引用。直らない古い DLL は `C:\venvs\fullseye` に venv を作る |
| <!-- doctor: onedrive_known_folders --> `onedrive_known_folders` | Desktop/Documents の入力が消える、同期中に保存失敗 | OneDrive の既知フォルダー移動 | doctor の `OneDrive path detected` | `New-Item -ItemType Directory -Force C:\src, C:\data`、プロジェクトと大量データはそこへ移して Studio で再選択 |
| <!-- doctor: store_python --> `store_python` | スタートメニューや Apps の登録が見えない、書込み拒否 | Microsoft Store Python の隔離・リダイレクト | executable に `WindowsApps` | python.org 版 Python か venv を使用: `py -3.11 -m venv $HOME\venvs\fullseye` |
| <!-- doctor: conda_pythonw --> `conda_pythonw` | ショートカットから Studio が DLL エラー | activate せず conda の `pythonw.exe` を直接起動 | `CONDA_PREFIX` と executable | `conda activate fullseye; fullseye-studio`。`pythonw.exe` を直接ダブルクリックしない |
| <!-- doctor: python_path --> `python_path` | `python` / `fullseye` が見つからない | Python の Scripts が PATH に無い | `python/py found` | `py -3.11 -m fullseye doctor` のように Python を明示、または venv を activate |
| <!-- doctor: multiple_python --> `multiple_python` | install は成功したのに `import fullseye` できない | 複数 Python の別環境へ pip が入れた | `PATH has ... Python-like entries` | 常に同じ `<python> -m pip install ...` と `<python> -m fullseye ...` を使う |
| <!-- doctor: pip_target --> `pip_target` | version や import 元が期待と違う | pip の配布先と import 元が違う | `imported=...; distribution=...` | doctor が示す Python で `<python> -m pip install --upgrade fullseye`、続けて `<python> -c "import fullseye; print(fullseye.__file__)"` |
| <!-- doctor: native_dll --> `native_dll` | `DLL load failed`、`Qt platform plugin`、`python3XX.dll` が無い | VC++ runtime、Qt plugin path、Python DLL のいずれか | `PySide6` と `QT_PLUGIN_PATH` | `<python> -m pip install --upgrade fullseye[gui]`。VC++ 2015–2022 x64 を入れる: `winget install Microsoft.VCRedist.2015+.x64`。SDK の `python3XX.dll` は SDK doctor の指示に従う |
| <!-- doctor: antivirus_lock --> `antivirus_lock` | install 中の `PermissionError`、exe/DLL が隔離された | Defender 等がファイルをロック・隔離 | `Get-MpThreatDetection`、保護履歴 | 出所・ハッシュを確認後、Fullseye の venv/プロジェクトだけを復元・除外。Python 全体を除外しない |
| <!-- doctor: powershell_policy --> `powershell_policy` | `.ps1 cannot be loaded because running scripts is disabled` | 実行ポリシー | `Get-ExecutionPolicy -List` | 内容を確認後、現在のプロセスだけ `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`。全体のポリシーは下げない |
| <!-- doctor: proxy_certificate --> `proxy_certificate` | pip/MCP の TLS 証明書エラー、社内ネットワークで接続不可 | proxy または社内 CA | doctor の `proxy configured` | IT から PEM を受け `$env:REQUESTS_CA_BUNDLE='C:\certs\company-root.pem'`。`--trusted-host` や TLS 無効化を常用しない |
| <!-- doctor: write_permission --> `write_permission` | `Program Files` への install/設定保存が拒否される | 管理者保護ディレクトリ | `Python under Program Files=True` | 管理者でなくユーザー venv を作る: `py -3.11 -m venv $HOME\venvs\fullseye` |
| <!-- doctor: high_dpi --> `high_dpi` | Studio の文字や図が小さすぎる・ぼやける | 高 DPI 倍率と Qt の組合せ | doctor の `DPI scale`、Windows Display 設定 | Windows **設定 > システム > ディスプレイ > 拡大縮小**を 100% でも一度確認し、Studio を再起動。読みやすい倍率を採用 |
| <!-- doctor: cuda_driver --> `cuda_driver` | `CUDA is not available`、torch/CUDA DLL エラー | GPU driver と torch の CUDA build が不一致 | `nvidia-smi` と doctor が示す `torch.version.cuda` | 対応する NVIDIA driver に更新、または CPU を使う。任意の CUDA toolkit を venv に混ぜない |
| <!-- doctor: smartscreen --> `smartscreen` | ダウンロードした installer/zip の起動がブロック | Defender SmartScreen / Zone.Identifier | `Get-Item -LiteralPath C:\path\to\downloaded-file -Stream Zone.Identifier` | 出所とハッシュを検証後、そのファイルだけ **プロパティ > 許可する**。SmartScreen は無効化しない |

## 起動エラーの見方

`ImportError`、DLL 読み込み、Unicode、パス、権限エラーでは、入口は「何が起きたか」「考えられる理由」「貼り付ける修復コマンド」「`fullseye doctor`」を表示します。最後の「元の例外」は消していないため、報告にはその部分と `fullseye doctor --json` の出力を添えてください。

Studio が Qt を読めた場合は同じ文をエラーダイアログにも表示します。Qt 自体を読めない場合や `pythonw.exe` でコンソールがない場合は、Windows のメッセージボックスを使い、利用できなければ標準エラーへ出します。
