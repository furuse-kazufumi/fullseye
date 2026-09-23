---
op: fly_hex_quantize
dim: flyvision
category: sample
in: signal
out: signal
examples: [poc_eye_to_brain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# fly_hex_quantize — FLYVISION `sample` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_hex_quantize(signal, bits=3, mode='log', contrast=0.2)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_hex_quantize(signal, bits=3, mode='log', contrast=0.2)`、台帳から引くなら `opsflyvision.get("fly_hex_quantize")`)

## 使い方

個眼信号を眼と同じやり方で量子化する: 対数圧縮してから個眼あたり n ビット(``mode="onoff"`` は ON / OFF の 2 チャネル)。

複眼は生まれつき量子化器で、片眼およそ 800 個眼(間隔 4.6°)、光受容器は強度を対数圧縮して平均に適応し、
ラミナの L1 / L2 が平均からの偏差を ON と OFF に分ける。この op はその予算を再現し、下流のモデル
(reservoir・網膜部位対応の検査)に「本当に何ビット要るか」を問えるようにする。

A compound eye is a quantizer by construction: ~800 ommatidia per eye at 4.6 deg spacing,
photoreceptors that log-compress intensity and adapt to the mean, and lamina cells (L1/L2)
that split the deviation into ON and OFF channels. This op reproduces that budget so a
downstream model (reservoir, retinotopy test) can be asked how many bits it really needs.

Parameters
----------
signal : (n,) float
    Per-ommatidium intensities >= 0 (``fly_hex_resample`` output).
bits : int
    1..8 levels = 2**bits (``mode="onoff"`` ignores it: the output is the signed pair below).
mode : str
    ``"log"``: log1p-compress relative to the mean, shift the darkest ommatidium to 0, then
    uniform levels over the compressed range; ``"linear"``: uniform levels over [0, max]; ``"onoff"``: deviation from the mean
    relative to ``contrast`` clipped to [-1, 1] and returned as ``2 * n`` values ``[ON..., OFF...]``
    (ON = positive part, OFF = negative part), each >= 0.
contrast : float
    Michelson-style contrast that saturates the ON/OFF channels (``mode="onoff"`` only).

Returns
-------
(n,) float in [0, 1] (levels / (2**bits - 1)); for ``"onoff"`` (2n,) in [0, 1].

Notes
-----
Non-finite or negative inputs are refused. A constant signal quantizes to all-zeros
(``"log"`` / ``"onoff"``) — there is no contrast to encode.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_eye_to_brain](../../../../examples/poc_eye_to_brain.py) — `py -3.11 examples/poc_eye_to_brain.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fly_emd_response](../motion/fly_emd_response.md) · [fly_lgmd_eta](../looming/fly_lgmd_eta.md) · [fly_tau_from_expansion](../looming/fly_tau_from_expansion.md) · [fly_dsi](../tuning/fly_dsi.md)

## 同カテゴリ(`sample`)

[fly_hex_resample](fly_hex_resample.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
