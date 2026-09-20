---
id: strict-mode-only-covered-some-of-the-guards
date: 2026-09-20
found_by: genspark_external_review
kind: silent-wrong
severity: medium
where: [api.py, opassist.py, imgevolve.py, fullseye/__main__.py, unified.py]
ops: [access_channel]
gate: [test_strict_mode_makes_every_guard_raise, test_op_run_explains_the_argument_order_and_registry_ops, test_python_dash_m_fullseye_is_the_cli, test_index_names_the_difference_from_the_shipped_copy, test_index_default_output_never_lands_inside_an_installed_package, test_unified_pipeline_points_knob_tuples_to_run_pipeline]
status: fixed
---

# `strict_mode()` が経路の一部しか厳密にしていなかった(+ 0.2.1 再測定の 4 件)

## 症状

GenSpark 第 55 報(0.2.1 を入れ直しての再測定、2026-09-20)。修正確認 8 件のあと、残存 8 件・新規 4 件。

- **N199(本物)**: `with fullseye.strict_mode(): apply(gray, "access_channel")` が例外にならず ndarray を返し、台帳に
  `source="input"` の fallback が残る。`on_error="raise"` なら止まる。strict は **op 本体の例外と GPU / 高速路**だけが
  見ていて、入力型の門(`_guard_input`)と非有限出力の門は `on_error` しか見ていなかった —— 「厳密」が経路ごとに別の意味。
- **N200**: `op_run(img, "gaussian")` が `unhashable type: 'numpy.ndarray'`、`op_run("gaussian", img)` が「not in any
  ledger」で終わり、registry op は `apply` で走ることを言わない(第 9 陣で `apply` → `op_run` の案内は付けたが逆向きが無かった)。
- **N150**: `python -m fullseye` が「No module named fullseye.__main__」。
- **N198 / N115**: wheel から `fullseye index` を叩くと site-packages の中に `docs/OP_INDEX.json` を作り、その環境の
  生きた registry(1,994 = 同梱 1,996 − backend 不足 2)を持つ「3 つ目の索引」に見える。数が違うのは正常(同梱 = ビルド環境)
  だが、**違う理由を言わない数字は別の真実に見える**。
- **N201**: `fullseye.Pipeline([("gaussian", 0.5, 0.5)])` が `then() argument after ** must be a mapping`(第 1 陣で
  「(op, {kwargs})」の 1 文にしたが、a / b の段は `run_pipeline` に属することを言っていなかった)。

## なぜ門が通したか

strict の門は `test_guard_reraises_in_strict_mode`(op 本体)と GPU の注入だけで、入力型の門は `on_error="raise"` で
試験していた。**同じ言葉(strict)を使う経路を数えて 1 本にする**([[feedback_count_wrapper_families_not_mechanisms]])。

## 直し

1. `api._policy`: `on_error=None` で `is_strict()` なら `"raise"`。strict_mode / set_strict / `FULLSEYE_STRICT` が
   入力型・非有限出力・op 本体・GPU・高速路の全部で同じ意味に。明示の `on_error` は文脈より強い(引数 > 文脈 > 環境変数 > 既定)。
2. `opassist.run`: 先頭が文字列でなければ「the first argument is the op name … op_run(name, <input>)」の TypeError、
   台帳に無く registry に在る名前は「run it with fullseye.apply(img, name)」を添える。
3. `fullseye/__main__.py`: `python -m fullseye` = CLI(`imgevolve.main`)。
4. `fullseye index`: 書き先の既定は checkout では `docs/OP_INDEX.json`、`docs/` の無い場所(wheel)では cwd。
   出力に「this environment vs the shipped index: N missing here」と、欠けた op が要る backend と `pip install` の行。
5. `unified.Pipeline`: 3 要素タプルの文に「knob stages (name, a, b) belong to run_pipeline / FullseyeEngine」。

**同じ報で分けたもの**: N148 `op_names` 既定に n-ary 無し = 設計(`include_nary=True`)/ N153 既定 `fallback` = 設計 /
N155 `set_strict` / `is_strict` = `backend_safe` に在り facade は `strict_mode` + `on_error`(設計)/ N157-158・N154・
N175-176(os / sys)= 第 2 陣で修正 / `fullseye.fixture` / `golden` / `jsonio` / `mdio` はサブモジュール(属性 API、設計)。
