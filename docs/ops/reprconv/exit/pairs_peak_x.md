---
op: pairs_peak_x
dim: reprconv
category: exit
in: pairs
out: measurement
gpu: なし
examples: [type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# pairs_peak_x — REPRCONV `exit` op

- **データ種**: `pairs` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.pairs_peak_x(pairs, x_min=None, x_max=None)` (実装を直接呼ぶなら `import reprconv; reprconv.pairs_peak_x(pairs, x_min=None, x_max=None)`、台帳から引くなら `opsreprconv.get("pairs_peak_x")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

対 ``pairs (x, y)`` → y が最大になる x(放物線で標本の間まで補間)``measurement``。

``spectrum`` の ``(freqs, magnitude)`` から主周波数、``surface_psd`` の (周波数, PSD) から
卓越波長の逆数を読む、のように **対の列のピークの位置**を返す。最大の標本と両隣の 3 点に
放物線を当て、頂点の x を返す(端の標本が最大のときは補間せずその x)。**補間の偏りは
窓しだい**: 窓を掛けない(矩形)正弦波の振幅スペクトルでは最大 0.25 bin ほど(実測 1 Hz 刻みで
123.4 Hz → 123.18、123.25 → 123.05、整数と半整数の周波数では 1e-2 bin 以下)。
細かく要るなら窓を掛けた信号か ``peak_subbin`` を使う。``x_min`` / ``x_max`` で探す範囲を切る ——
**スペクトルでは DC(x = 0)が最大になりやすい**ので、主周波数を探すなら ``x_min`` を 0 より
大きくする。y の同点は最初の標本。

Args:
    pairs: (n, 2) か 2-tuple の (x, y)。x は昇順。
    x_min, x_max: 探す x の範囲(含む)。None で端まで。
Returns:
    float(ピークの x)。
Raises:
    ValueError: 対でない / x が昇順でない / 範囲に標本が無い / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`exit`)

[tokens_to_matrix](tokens_to_matrix.md) · [pose_to_matrix](pose_to_matrix.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
