---
id: unknown-operator-hides-missing-backend
date: 2026-09-19
found_by: genspark_external_review
kind: discoverability
severity: high
where: [api.py, ops.py, imgevolve.py, fullseye/data/OP_INDEX.json]
ops: [sk_canny, cv_canny, rgb1_to_gray, access_channel]
gate: [test_missing_backend_error_is_a_keyerror_and_names_the_missing_extra, test_unknown_operator_message_names_a_real_cli_and_op_find, test_op_index_rows_carry_module_and_requires, test_optional_deps_table_matches_pyproject_extras]
status: fixed
---

# 「unknown operator」が backend 不足を隠し、存在しない CLI を案内していた

## 症状

第三者(GenSpark)が 0.2.0 を **core**(`pip install fullseye`、693 op)と **all**(`fullseye[all]`、899 op)の 2 環境で使い込んだ。core で `fullseye.apply(img, "sk_canny")` を呼ぶと

```
KeyError: "unknown operator 'sk_canny' — try op name or HALCON alias; list with fullseye.op_names() or `imgevolve.py has sk_canny`"
```

同じ行が all では `(32, 32)` で成功する。`cv_canny`、色の 5 op(`rgb1_to_gray` / `rgb3_to_gray` / `count_channels` / `trans_to_rgb` / `access_channel`)も同様。つまり **「存在しない」と「extra が入っていない」が同じ文に潰れていた**。しかも案内している `imgevolve.py` は `shutil.which` で解決できない —— 配布物の console_scripts は `fullseye`(= `imgevolve:main`)と `fullseye-rag` だけで、checkout の中でしか通らない綴りだった。

## なぜ門が通したか

backend モジュールの `build()` は依存が import できないと **空リストを返す**設計(登録を壊さないため)。だから core 環境では `sk_canny` という名前が**どこにも残らない**。索引 `docs/OP_INDEX.json`(と wheel に同梱の複製 `fullseye/data/OP_INDEX.json`)は全 op を持っていたが、**どのモジュールが、どの optional 依存で**提供するかを書いていなかったので、未登録の名前を引かれた側に「入っていない」と言う材料が無かった。テストは全部 all 相当の環境で走るので、core の利用者が最初に読む文を誰も読んでいなかった([[feedback_gate_must_stand_where_the_accident_happens]] の文言版)。

CLI 名は `imgevolve.py` → `fullseye` に console_scripts を切った 0.1 系のときに、エラー文だけ直し忘れた。文中の CLI 名を数える門は無い。

## 直し

1. **出自を登録の側で残す**: `ops.OP_MODULE`(op 名 → 登録モジュール)。fn は `backend_safe._safe` に包まれて `__module__` を失うので、登録ループで `_mod` を記録する(後勝ち = 重複解消と同じ規則)。
2. **optional 依存を静的に読む**: `ops.module_requirements(mod)` がモジュールのソースを **AST で走査**し、`ops.OPTIONAL_DEPS`(import 名 → pip 名・extra 名)にある import を返す。実行しないので、依存の無い環境でも同じ答えになる。粒度はモジュール単位(`backends` は skimage と cv2 を別々の build で使うので両方「使う」と出る)—— 案内文は「このモジュールが使う」「その中で入っていないもの」を分けて書き、op 単位の必要十分は主張しない。
3. **索引に `module` / `requires` を足す**(`imgevolve.py index` → `docs/OP_INDEX.json` → `fullseye/data/OP_INDEX.json`)。
4. **`api.MissingBackendError(KeyError)`**: 未登録の名前が同梱索引に在れば、モジュール名・使う依存・**この環境に無い依存**・`pip install "fullseye[<extra>]"` を 1 文で言う。依存が全部入っているのに未登録なら `fullseye.FAILED_BACKENDS` の記録を添える。`KeyError` の派生なので既存の `except KeyError` は壊れない。
5. 本当に無い名前の文は `fullseye has <name>`(配布物の CLI)と `fullseye.op_find('<words>')` を案内する。

門: `OPTIONAL_DEPS` の pip 名と extra 名を **pyproject.toml の optional-dependencies と突き合わせる**(食い違えば案内が嘘になる)/ 索引の全 registry 行に `module` と `requires` が在る / 偽の索引行で `MissingBackendError` の文に不足モジュールと `pip install` が入る。

## 同じレビューで「設計判断」として残した点(変えなかった)

レビューは 12 + 3 + 3 件を挙げ、バグと設計判断を自分で分けてくれていた。以下は事実として正しく、**意図した設計**なので変えない。理由をここに置く。

| 指摘 | 判断 |
|---|---|
| 既定 `on_error="fallback"` が契約違反の uint8 を黙って /255 する(`raise` にすべき) | 進化ループと Studio が**1 枚の失敗で止まらない**ことが前提の設計。変換は台帳(`fullseye.fallbacks()`)に全件残り、`FULLSEYE_ON_ERROR=raise` で環境ごとに既定を変えられる。厳格運用のテンプレートは docs/GETTING_STARTED の on_error 節。**変換の定義が無い入力(文字列・複素)は方針に依らず止める**ように直した(別ノート) |
| dtype 変換の警告が uint8 だけで bool / int32 は無警告(不揃い) | 警告は **op ごとに 1 度**(「Further fallbacks of this op are counted silently」と文に書いてある)。同じ op に uint8 → int32 → bool の順で渡すと 2 度目以降は静か。台帳には 3 件とも残る(門 `test_dtype_conversions_are_all_recorded_even_though_only_the_first_warns`) |
| float32 / float16 が無警告で float64 になる | 無損失の昇格で値も範囲も変わらない。契約は「float64 in [0,1]」だが、記録すべき**変換**(/255 のような値の解釈)は起きていない |
| 公開名が 1,125(1,206)個で名前空間が混雑 | ファサードは「op 名で呼ぶ」のが主経路(`fs.apply(img, "otsu")`)、属性は補助。`__all__` を一次情報にし、`tests/test_public_reachability.py` が**見えない公開名**を数える方向で守っている。サブ名前空間への分割は 0.3 の破壊的変更候補として記録 |
| docstring 被覆が 38〜47 % | 数えたのは `Op.doc` だけ。説明の正本は **op ノート**(`docs/ops/**/*.md`、全 op、6 言語)で、`fullseye.op_find` / MCP / Studio ヘルプはそちらを読む。`Op.doc` は lambda で書かれた backend op の受け皿 |
| import に約 1 秒 | 931 op の登録と backend の import。torch は `torch_lazy` で遅延済み。さらに削るなら backend の遅延登録が要り、`REGISTRY` を読む側(進化・索引)の契約が変わる。0.3 の候補 |
| `a` / `b` が自己説明的でない | 全 op が同じ 2 ノブ [0,1] を持つのは**進化(遺伝子 = op 索引 + a + b)の要件**。op ごとの意味は `docs/op_knob.json` と op ノートに表がある |
| `Op` が pickle できない | 直した(名前で復元、別ノート) |
