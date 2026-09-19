---
id: engine-load-on-an-instance-was-silently-ignored
date: 2026-09-20
found_by: genspark_external_review
kind: silent-wrong
severity: medium
where: [engine.py, imgevolve.py]
ops: [gaussian, otsu]
gate: [test_load_on_an_instance_loads_into_it, test_dict_stages_are_understood_and_bad_stage_types_are_refused, test_upto_is_an_inclusive_stage_index_and_out_of_range_is_refused, test_to_python_carries_the_ops_string_and_a_coding_line]
status: fixed
---

# `engine.load(path)` がインスタンスでは何もせず、空のエンジンが入力をそのまま返していた

## 症状

GenSpark 第 16 報(N37 / N39 / N40 / N41)。

```python
e = fullseye.FullseyeEngine(); e.load("/tmp/x.json")
e.run(img)        # (48, 48) —— JSON の中身が何であっても
e.describe()      # []
e.validate()      # []
```

未知 op を含む JSON でも、`stages: []` でも、`{"op": "gaussian"}` の段でも、`load` は通り `run` は「結果」を返す。第三者はこれを「パイプライン JSON を一切検証せず無言で結果を返す」と観測した。加えて `--upto 9` / `--upto -1` が rc 0(全段 / 0 段)、`--to-python` の生成物に GUI Export が出す `--ops` 文字列が無い。

## なぜ門が通したか

`load` / `from_dict` / `from_ops` は **classmethod** で、`e.load(path)` は新しいエンジンを返して捨てられ、`e` は空のまま。空のエンジンの `run` は仕様どおり入力を返す(「0 段の pipeline は恒等」)。つまり JSON は読まれもしなかった —— 「検証していない」のではなく「そのエンジンに入っていない」。`FullseyeEngine.load(path)` と書く利用者しかテストしていなかった([[feedback_one_probe_input_is_not_coverage]] の呼び方版)。

段の正規化は `str(op)` で何でも名前にしていたので、`{"op": "gaussian"}` は `"{'op': 'gaussian'}"` という op 名になり、`run` で「unknown operator」になる(= 中身のある dict 段は黙って壊れる)。`_stage_tuples(upto)` は `min(upto+1, len)` / `max(0, ·)` で範囲外を黙って丸めていた。

## 直し

1. **`_hybridmethod`** —— `load` / `from_dict` / `from_ops` は classmethod としてもインスタンスメソッドとしても呼べる。インスタンスに対して呼ばれたら**そのインスタンスに読み込んで self を返す**。`from_ops` は名前のリストも受ける。
2. **段の正規化** —— `{"op"|"name", "a", "b"}` を受け、op が空でない文字列でなければ「stage i: the op must be a non-empty name …」の `ValueError`(以前の `str()` を廃止)。
3. **`upto`** —— `0..len-1` の整数以外は `ValueError`(意味は従来どおり「段 0..upto を走らせる」、CLI の help も同じ)。
4. **`to_python`** —— 先頭に `# -*- coding: utf-8 -*-`(コメントに日本語の op 説明が入る)と `# --ops "gaussian,otsu"`(GUI Export と同じ CLI 文字列)。

**同報で設計・撤回として分けたもの**: N38(87 op の恒等化)は GenSpark 自身が訂正 —— 80 件は signal / video / points 入力の op に 2-D 画像を渡した fallback(台帳に記録、once-per-op 警告)、無警告の 7 件(`identity` / `abs_image` の [0,1] 入力 / `it_full_domain` など)は恒等が仕様。N43(生成器が公開 API に無い)は `FullseyeEngine.to_python()` / `to_dict()` がその API。N42(`img_to_volume` に 3-D)は KNOWN_ISSUES #32-4 の族。
