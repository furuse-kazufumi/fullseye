<!-- i18n-source-sha: 7b8e76645291 -->
# Windows troubleshooting

Run the doctor with **the same Python that failed**. Its `Checked` field is an observed value, not a guess. `fullseye doctor --json` is for automation or a support ticket. `--fix` shows its plan first and makes only a reversible repair after confirmation in an interactive terminal: it removes only missing `QT_PLUGIN_PATH` entries from the per-user value and current process, preserving valid entries. It makes no change in CI or a pipe. A console-less launch reports through a dialog and otherwise returns the location of a UTF-8 log.

```powershell
py -3.11 -m fullseye doctor
py -3.11 -m fullseye doctor --json
```

CLI, Studio, and MCP startup errors keep the original exception as detail and point here. When the C/C++ SDK is installed, the doctor delegates to `python -m fullseye.sdk --doctor --json` and includes that result rather than reimplementing it.

| ID | Symptom | Cause | Check | Repair command / action |
|---|---|---|---|---|
| <!-- doctor: console_encoding --> `console_encoding` | `UnicodeEncodeError` when Japanese text or `—` is piped | cp932 output | doctor: `stdout encoding` | `chcp 65001; $env:PYTHONUTF8='1'` in the same PowerShell |
| <!-- doctor: long_path --> `long_path` | deep venv/extraction fails near 260 characters | MAX_PATH / Win32 long paths disabled | `LongPathsEnabled=0` | Enable Windows long paths as Administrator and reboot; meanwhile use a short root such as `$env:SystemDrive\src` |
| <!-- doctor: unicode_space_path --> `unicode_space_path` | only a native helper fails to start | unquoted Unicode or space-containing path | doctor: `Python path` | Quote paths as `"..."`; for an old DLL that still fails, make the venv at `$env:USERPROFILE\fullseye-venv` |
| <!-- doctor: onedrive_known_folders --> `onedrive_known_folders` | Desktop/Documents input disappears or saving fails during sync | OneDrive known-folder redirection | doctor: `OneDrive path detected` | `New-Item -ItemType Directory -Force $env:SystemDrive\src, $env:SystemDrive\data`; move your projects and input files there and reselect them in Studio |
| <!-- doctor: store_python --> `store_python` | Start menu/Apps registration is missing or writes fail | Microsoft Store Python sandbox/redirection | executable contains `WindowsApps` | Use python.org Python or a venv: `py -3.11 -m venv $env:USERPROFILE\fullseye-venv` |
| <!-- doctor: conda_pythonw --> `conda_pythonw` | Studio shortcut has a DLL error | conda `pythonw.exe` was launched without activation | `CONDA_PREFIX` and executable | `conda activate fullseye; if ($?) { fullseye-studio }`; do not double-click `pythonw.exe` |
| <!-- doctor: python_path --> `python_path` | `python` / `fullseye` is not found | Python Scripts is absent from PATH | `python/py found` | Use `py -3.11 -m fullseye doctor`, or activate the venv |
| <!-- doctor: multiple_python --> `multiple_python` | install worked but `import fullseye` fails | pip installed into another Python | `PATH has ... Python-like entries` | Use the same `<python> -m pip install ...` and `<python> -m fullseye ...` |
| <!-- doctor: pip_target --> `pip_target` | unexpected version or import location | pip distribution and imported package differ | `imported=...; distribution=...` | With the shown Python run `<python> -m pip install --upgrade fullseye`, then `<python> -c "import fullseye; print(fullseye.__file__)"` |
| <!-- doctor: native_dll --> `native_dll` | `DLL load failed`, `Qt platform plugin`, or missing `python3XX.dll` | VC++ runtime, Qt plugin path, or Python DLL | `PySide6` and `QT_PLUGIN_PATH` | `<python> -m pip install --upgrade fullseye[gui]`; install VC++ 2015–2022 x64: `winget install Microsoft.VCRedist.2015+.x64`; follow SDK doctor for `python3XX.dll` |
| <!-- doctor: antivirus_lock --> `antivirus_lock` | `PermissionError` while installing, or an exe/DLL is quarantined | Defender/AV lock or quarantine | `Get-MpThreatDetection`, Protection history | Verify source/hash, then restore/exclude only the Fullseye venv/project; never exclude all Python |
| <!-- doctor: powershell_policy --> `powershell_policy` | `.ps1 cannot be loaded because running scripts is disabled` | execution policy | `Get-ExecutionPolicy -List` | Inspect first, then only for this process: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` |
| <!-- doctor: proxy_certificate --> `proxy_certificate` | pip/MCP TLS certificate failure on a corporate network | proxy or corporate CA | doctor: `proxy configured` | Obtain the PEM from IT and set `$env:REQUESTS_CA_BUNDLE = Join-Path $env:USERPROFILE 'company-root.pem'`; do not routinely disable TLS |
| <!-- doctor: write_permission --> `write_permission` | install/settings write fails under `Program Files` | protected directory | `Python under Program Files=True` | Use a user venv, not Administrator: `py -3.11 -m venv $env:USERPROFILE\fullseye-venv` |
| <!-- doctor: high_dpi --> `high_dpi` | Studio text/figures are tiny or blurry | high-DPI scaling / Qt combination | doctor `DPI scale`, Windows Display settings | Test **Settings > System > Display > Scale** at 100%, restart Studio, then keep the readable value |
| <!-- doctor: cuda_driver --> `cuda_driver` | `CUDA is not available` or torch/CUDA DLL failure | GPU driver and torch CUDA build mismatch | `nvidia-smi` and doctor’s `torch.version.cuda` | Update to a supported NVIDIA driver or use CPU; do not mix an arbitrary CUDA toolkit into the venv |
| <!-- doctor: smartscreen --> `smartscreen` | downloaded installer/zip is blocked | Defender SmartScreen / Zone.Identifier | `Get-Item -LiteralPath '<downloaded-file>' -Stream Zone.Identifier` | Verify source and hash, then use **Properties > Unblock** for that file only; do not disable SmartScreen |

## Reading startup errors

For import, DLL-load, encoding, path, and permission errors, every entry point states what happened, the likely cause, copyable repairs, and `fullseye doctor`. `Original exception` is retained. Include it and `fullseye doctor --json` in a report.

If Qt loaded, Studio also shows the text in a dialog. If Qt itself cannot load, or `pythonw.exe` has no console, it uses a Windows message box and falls back to standard error when that is unavailable.
