---
id: inspection-fixture
title: 既知の良品/不良品セットで検査レシピと仕様を配備前に検定し、余裕を測る
title_en: Validate a recipe and spec on known good/bad sets before deployment, and measure the margins
category: 組み立てる
ops: [inspection_fixture, spec_margins, inspect_batch, judge]
examples: [inspection_fixture]
version: 0.2.1
---

# 既知の良品/不良品セットで検査レシピと仕様を配備前に検定し、余裕を測る

## できること

レシピ(前処理)と計測と仕様を決めたあと、現場が最初に聞くのは「良品は全部通り、不良品は全部止まるのか」と「どれくらい余裕があるのか」です。`fullseye/fixture.py` の `inspection_fixture(good, bad, recipe, measure=..., spec=...)` は、既知の良品セットと不良品セット(フォルダまたはパス列)をそれぞれ `inspect_batch` で回し、**良品が全部 `ok` かつ不良品が全部 `ng` のときだけ `passed=True`** を返します。混同表 `confusion`、見逃した不良品の行 `escapes`、過検出した良品の行 `false_rejects`、読めなかった行 `errors` を並べ、`spec_margins` が仕様キーごとに**良品の計測が限界にどれだけ近いか**(`min_margin`、負なら超過。`tol` や max−min で正規化した `min_margin_norm` は 1.0 が限界幅ぶんの余裕)を出します。`detail` は「passed: good 6/6 ok, bad 4/4 ng; tightest margin bright_px=1.00 of limit width」のような 1 行です。

fail-closed の約束: 空のセットは `ValueError`(0 枚で「全部通った」は証明ではありません)、読めない 1 枚は `error` として `passed` を落とし、仕様の綴り間違いは `judge` と同じく `ValueError` で止まります。`report_path` を渡すと良品と不良品を別々のレポート(`<stem>_good.<ext>` / `<stem>_bad.<ext>`、.xlsx / .md / .jsonl)に書きます。

## What it does

`inspection_fixture(good, bad, recipe, measure=..., spec=...)` runs the known-good and known-bad sets through `inspect_batch` and returns `passed=True` only when every good part is `ok` and every bad part is `ng`. It lists the confusion counts, the escaped bad parts (`escapes`), the falsely rejected good parts (`false_rejects`) and unreadable rows (`errors`), and `spec_margins` reports per spec key how close the good measurements come to the limits (`min_margin` in spec units, negative when exceeded; `min_margin_norm` normalised by the tolerance or half the min–max width, so 1.0 means one limit-width of headroom). An empty set raises `ValueError`, an unreadable file becomes an `error` that fails the fixture, and a misspelled spec raises. With `report_path` the two sets are written to separate `_good` / `_bad` reports.

## 向くところ / 向かないところ

**向く**: レシピ・仕様を変えたときの回帰検定(既知セットを固定して毎回回す)、閾値の余裕を数字で示す(監査・顧客説明)、ゴールデン比較(`golden_measure`)の閾値・`max_shift` の検定、CI に「検査レシピの門」として組み込む。

**向かない**: ★**仕様の自動決定**(余裕は測るが閾値は決めない。決めるのは人。統計的に決めるなら SPC の `spc_capability`)。★良品/不良品のラベルが怪しいセット(ラベルの誤りはそのまま「過検出/見逃し」に見える)。★1 枚ずつのライブ検査(`fsruntime`)。

## 最初の 1 本

```python
import fullseye as fs

def measure(im):
    return {"area": float(fs.apply(im, "area")), "mean": float(im.mean())}

spec = {"area": {"nominal": 400.0, "tol": 60.0}, "mean": {"min": 0.2, "max": 0.6}}
fx = fs.inspection_fixture("known_good/", "known_bad/", ["gaussian"], measure=measure, spec=spec,
                           report_path="fixture.xlsx", title="Recipe v3")
print(fx["passed"], fx["detail"])
print(fx["margins"]["area"])          # {'n': 6, 'min_margin': 60.0, 'min_margin_norm': 1.0, ...}
for r in fx["escapes"]:
    print("見逃し:", r["path"], r["measurements"])
```

## 裏づけ

- 実装: `fullseye/fixture.py`(`inspection_fixture` / `spec_margins`。`inspect_batch` と `judge` の配線、新アルゴリズム無し)
- 例: [`inspection_fixture`](../../examples/inspection_fixture.py)(良品 6 / 不良品 4 で passed → 締めすぎで過検出 → 緩めすぎで見逃し → 壊れた 1 枚で error、すべて assert)
- 試験: `tests/test_fixture.py`(分離 → passed と margin / 締めすぎ → false_rejects / 緩めすぎ → escapes / 壊れた 1 枚 → error / 空セット・壊れた spec は ValueError / 良品・不良品別レポート / spec_margins の数値)
- 来歴: 無し(glue)。語彙は能力ノート `inspection-workflow` と共通。
