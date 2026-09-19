---
id: cli-help-and-subcommands-broke-in-the-wheel
date: 2026-09-19
found_by: genspark_external_review
kind: gate-gap
severity: medium
where: [imgevolve.py, honest_summary.py, backends_color.py, backends_r3.py, backends_auto.py, studio.py]
ops: [xwt_visushrink, xwt_firm_denoise]
gate: [test_help_examples_use_the_installed_cli_name_when_run_as_fullseye, test_parity_subcommand_resets_argv_before_delegating, test_coverage_explains_the_missing_reference_data_instead_of_crashing, test_color_backend_name_check_is_fail_closed_without_the_json, test_registry_does_not_shrink_when_warnings_are_errors]
status: fixed
---

# 配布物の CLI で、help が別の入口を案内し、3 つのサブコマンドが使えなかった

## 症状

GenSpark 第 6・7 報(0.2.0 を `pip install` した Linux で `fullseye` を叩いた実測)。

| コマンド | 起きたこと |
|---|---|
| `fullseye --help` | 実行例が全部 `py -3.11 imgevolve.py …`(checkout 専用の綴り。K2 の CLI 側) |
| `fullseye parity` | `error: unrecognized arguments: parity`(rc 2)—— help には載っている |
| `fullseye coverage` | `FileNotFoundError: …/site-packages/data/halcon_operators.json`(rc 1) |
| `fullseye samples` | `the following arguments are required: action`(rc 2) |
| Studio 起動 | `QMainWindow::saveState(): 'objectName' not set for QToolBar` / import のたびに `pywt … Level value of 2 is too high` |

加えてこの木で数えると: `python -W error::UserWarning -c "import ops"` で **REGISTRY が 931 → 929**。`xwt_visushrink` / `xwt_firm_denoise` が黙って消え、`FAILED_BACKENDS` にも残らない。import 時にも `unclosed file` の ResourceWarning が 3 本(`backends_auto.py:1761`)。

## なぜ門が通したか

CLI のテストは全部 **checkout の `imgevolve.py`** で走る。console_script `fullseye` として呼ばれる経路(argv[0] が違う、`data/` が無い)を通る門が無かった([[feedback_gate_must_stand_where_the_accident_happens]] の CLI 版。wheel の門 `tools/ci_wheel_check.py` は**中身の有無**を数え、**サブコマンドが走るか**は見ない)。

- `parity`: `cmd_parity` が `parity.main()` を呼び、そちらが `sys.argv` を自分で parse する。`accel` / `bench` は argv を差し替えていたのに parity だけ素通し。
- `coverage`: `honest_summary` が `data/halcon_operators.json`(MVTec のリファレンス説明文を含むので**同梱しない**判断済み)を無条件に開く。名前だけの出荷版 `halcon_names_data` は在ったが、こちらは読まない。
- `backends_color._real_ops`: 同じ JSON しか読まず、wheel では**空集合 → `if real and n not in real` が全部通す**。`backends_auto` が 0.1 系で潰したのと同じ fail-open が、色の層に残っていた。
- `backends_r3._gate`: import 時に各レシピを 24 px の探針で叩く。db4 / sym4 の level=2 は 28 px 要るので pywt が警告し、警告を例外にする環境では try/except が「動かないレシピ」と誤判定して落とす。**探針は機能の門で、警告の門ではない**のに区別していなかった。

## 直し

1. **`imgevolve._prog()`** —— argv[0] が `fullseye…` なら help の実行例を `fullseye <cmd>` に、checkout なら従来の綴りに。epilog に両方を書く。
2. **`cmd_parity`** —— `sys.argv = ["parity.py"]` に差し替えてから委譲(accel / bench と同じ)。
3. **`samples`** —— `action` を省略可(既定 `list`)。
4. **`honest_summary.main`** —— JSON が無ければ「何が要るか・数字の在処(`docs/HALCON_PARITY.md`)・出荷しているのは名前だけ」を印字して rc 1。クラッシュしない。
5. **`backends_color._real_ops`** —— `halcon_names_data.HALCON_NAMES` を先に読む(JSON と 2,313 名で完全一致、色 op 12 本は全部実在名)。
6. **`backends_r3._gate`** —— 探針を 32 px に、探針の中の警告は `catch_warnings` で無視。`-W error` でも REGISTRY は 931 のまま(門 = サブプロセス 2 本で数を突き合わせる)。
7. `backends_auto` の JSON 読みを `with open`、Studio の主ツールバーに `setObjectName("main_tools")`。

**GenSpark 第 6・7 報で設計として残したもの**: `device="cuda"` が GPU 無しでも返る(N7)—— 台帳に `source="gpu"` で**記録され、op ごとに 1 度警告**する(この木で実測: `AssertionError: Torch not compiled with CUDA enabled` が残る)。「無警告」に見えたのは同じ op が先に別の理由で fallback していたか、警告の once-per-op。非 ASCII のウィンドウ名が `xwininfo` で化ける(N11)は X クライアント側のロケール変換で、Qt は `_NET_WM_NAME` を UTF-8 で正しく立てている。
