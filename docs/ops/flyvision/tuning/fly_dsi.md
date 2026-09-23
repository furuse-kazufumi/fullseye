---
op: fly_dsi
dim: flyvision
category: tuning
in: signal
out: table
examples: [poc_fly_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# fly_dsi — FLYVISION `tuning` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_dsi(responses, angles_deg)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_dsi(responses, angles_deg)`、台帳から引くなら `opsflyvision.get("fly_dsi")`)

## 使い方

Direction-selectivity index and preferred direction from tuning responses.

A vector sum on the circle::

    DSI = |sum_k r_k exp(i theta_k)| / (sum_k r_k + 1e-9)
    preferred = angle(sum_k r_k exp(i theta_k))

where ``r_k >= 0`` is the response to a stimulus moving at angle
``theta_k = angles_deg[k]`` (negatives clipped to 0).

responses:  a 1-D array of responses, one per direction.
angles_deg: the stimulus directions in degrees, same length.

Returns a dict ``{"dsi": float, "pref_deg": float}`` with ``pref_deg`` in
``[-180, 180]``.

Ground truth: a response at a single direction gives ``dsi == 1``; an isotropic
response over directions evenly spanning the circle gives ``dsi == 0`` (pinned
in the tests).

**Raises** ``ValueError``: a non-1-D / empty / non-finite *responses* or
*angles_deg*, mismatched lengths, an array over :data:`MAX_SIGNAL_POINTS`, and
an all-zero *responses* (no direction tuning to report).

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_vision](../../../../examples/poc_fly_vision.py) — `py -3.11 examples/poc_fly_vision.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fly_t4t5_field](../direction/fly_t4t5_field.md) · [fly_flow_from_directions](../direction/fly_flow_from_directions.md) · [fly_matched_filter](../selfmotion/fly_matched_filter.md) · [fly_egomotion_from_flow](../selfmotion/fly_egomotion_from_flow.md) · [fly_eye_merge](../selfmotion/fly_eye_merge.md) · [fly_hex_resample](../sample/fly_hex_resample.md) · [fly_hs_readout](../integrate/fly_hs_readout.md)

## 同カテゴリ(`tuning`)

—

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
