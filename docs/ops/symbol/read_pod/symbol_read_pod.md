---
op: symbol_read_pod
dim: symbol
category: read_pod
in: table
out: table
gpu: なし
examples: [poc_symbol_lot_ocr, poc_symbol_package_1d, poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# symbol_read_pod — SYMBOL `read_pod` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.symbol_read_pod(trials_table, *, link='logit', level=0.95)` (実装を直接呼ぶなら `import symbolpod; symbolpod.symbol_read_pod(trials_table, *, link='logit', level=0.95)`、台帳から引くなら `opssymbol.get("symbol_read_pod")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

読み取りの試行表から、POD(当たり = 真の文字列を読めた)と誤読の上限を返す(``table``)。

Fit the hit/miss POD (:func:`pod.pod_hitmiss_fit`) to a table from
:func:`symbol_read_trials`. When the factor is worse when larger (defocus, noise …)
the fit runs on ``x = −level`` so that POD rises with ``x``, and the answers are
mapped back: ``level90`` = the degradation read with 90 % probability,
``level90_95`` = its conservative bound at ``level`` confidence (a *smaller*
degradation), ``level50`` likewise. When the factor is better when larger (module
size, contrast, full well) ``level90_95`` is the *larger* value.

``method = "hitmiss_glm"`` then. ★When the outcome is decided by the level (complete
separation — every capture read up to one level and none beyond), the slope is not
estimable; the op then returns ``method = "all_success_demonstration"``: the most
severe level at which every trial read (``separation_bracket`` = that level and the
first one with a failure), and ``level90_95`` = that level only if it holds at least
:func:`pod.trials_for_all_success` (0.90, ``level``) trials (29 at 95 %), else None.
``level50`` / ``level90`` are None in that case.

★``monotone`` is False when a more degraded level reads more often than a milder
one by more than 3 standard errors (``nonmonotone_z``): the POD models assume
monotone degradation, so the fitted numbers are then outside their premise (seen
with a reader that cannot read sharp dot-peen marks but reads them once blur merges
the dots). The result is still returned, flagged.

Also returns ``per_level`` (level, n, hits, misreads, noreads, read_rate),
``misread_total`` / ``decoded_total`` and ``misread_rate_upper`` (one-sided
Clopper-Pearson upper bound of misreads per decode at ``level``; with zero misreads
in n decodes it is ``1 − (1 − level)^(1/n)``), ``fit`` (the POD table) and ``factor``.

空の入力(0 行)は ``ValueError``。
拒否(``ValueError``): 列の欠け、全部読めた/全部読めない、``level`` が (0, 1) の外。
完全分離は拒否せず上の「全数成功の実証」で返す(傾きの無い POD を作らない)。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_lot_ocr](../../../../examples/poc_symbol_lot_ocr.py) — `py -3.11 examples/poc_symbol_lot_ocr.py`
- [poc_symbol_package_1d](../../../../examples/poc_symbol_package_1d.py) — `py -3.11 examples/poc_symbol_package_1d.py`
- [poc_symbol_part_dpm](../../../../examples/poc_symbol_part_dpm.py) — `py -3.11 examples/poc_symbol_part_dpm.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](symbol_read_trials.md) · [ocr_classify](../ocr/ocr_classify.md) · [ocr_read_line](../ocr/ocr_read_line.md) · [ocr_read_trials](../ocr/ocr_read_trials.md)

## 同カテゴリ(`read_pod`)

[symbol_read](symbol_read.md) · [symbol_read_trials](symbol_read_trials.md)

---
*Provenance: symbolpod.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
