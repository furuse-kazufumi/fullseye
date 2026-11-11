---
op: symbol_read_trials
dim: symbol
category: read_pod
in: table
out: table
gpu: なし
examples: [poc_symbol_package_1d, poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# symbol_read_trials — SYMBOL `read_pod` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.symbol_read_trials(symbol, factor, levels, *, trials=20, reader='auto', symbologies=None, truth=None, module_px=4.0, render=None, capture=None, rotate='random', rotate_jitter_deg=5.0, level_jitter=0.0, refine=False, seed=0)` (実装を直接呼ぶなら `import symbolpod; symbolpod.symbol_read_trials(symbol, factor, levels, *, trials=20, reader='auto', symbologies=None, truth=None, module_px=4.0, render=None, capture=None, rotate='random', rotate_jitter_deg=5.0, level_jitter=0.0, refine=False, seed=0)`、台帳から引くなら `opssymbol.get("symbol_read_trials")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

劣化量の各水準でシンボルを ``trials`` 回撮って読み、1 行 = 1 回の結果の表を返す(``table``)。

For each level of the degradation ``factor`` (see :data:`DEGRADATION_FACTORS`),
render the symbol (:func:`symrender.render_symbol`), capture it
(:func:`symrender.capture_degrade`) and read it (:func:`symbol_read`), ``trials``
times with fresh nuisance: in-plane rotation (``rotate="random"``: uniform over
360° for 2-D symbols, ±``rotate_jitter_deg`` around 0 for 1-D; a number fixes it),
a sub-pixel offset in [0, 1) px and the sensor-noise seed. For a 1-D table the
reader is restricted to the table's own symbology unless ``symbologies`` is given
(a line reader enables only what it expects; all-symbology reading short-reads). ``render`` / ``capture``
hold the fixed settings of the other knobs; the sensor defaults to
``full_well_e = 20000``, ``read_noise_e = 10``, 8 bits. ``truth`` defaults to the
table's ``text``.

Returns columns ``level``, ``trial``, ``hit`` (1 = read the true text), ``misread``
(1 = read a different text), ``noread``, ``text`` (object array), plus
``factor``, ``worse_when_larger``, ``truth``, ``reader``, ``stage``.

``level_jitter`` (relative, default 0) multiplies each trial's actual level by
``1 + level_jitter · N(0, 1)`` while the table keeps the nominal level — the
process variation of the line (e.g. part height moving the focus). It is a
declared assumption, not a fit knob.

``refine=True`` first runs every level with ``max(4, trials // 4)`` trials, brackets
the transition (the last level read >= 95 % and the first read <= 5 %, in the order of
increasing degradation) and then runs ``len(levels)`` evenly spaced levels across
that bracket with ``trials`` each (``stage`` = ``"coarse"`` / ``"fine"``; both enter
the table). Without it a coarse sweep easily ends in complete separation.

空の入力(``levels`` が 3 未満)は ``ValueError``。
拒否(``ValueError``): 未知の ``factor``、``trials`` < 1、水準の重複・非有限、
``render`` / ``capture`` に掃引中の因子と同じ鍵、読み取り器を決められない表。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_package_1d](../../../../examples/poc_symbol_package_1d.py) — `py -3.11 examples/poc_symbol_package_1d.py`
- [poc_symbol_part_dpm](../../../../examples/poc_symbol_part_dpm.py) — `py -3.11 examples/poc_symbol_part_dpm.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_pod](symbol_read_pod.md) · [ocr_classify](../ocr/ocr_classify.md) · [ocr_read_line](../ocr/ocr_read_line.md) · [ocr_read_trials](../ocr/ocr_read_trials.md)

## 同カテゴリ(`read_pod`)

[symbol_read](symbol_read.md) · [symbol_read_pod](symbol_read_pod.md)

---
*Provenance: symbolpod.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
