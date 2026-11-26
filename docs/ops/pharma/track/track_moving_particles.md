---
op: track_moving_particles
dim: pharma
category: track
in: video
out: table
gpu: なし
examples: [poc_vial_particle_pod]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.2.0  # fullseye lib version this note was generated for
---

# track_moving_particles — PHARMA `track` op

- **データ種**: `video` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.track_moving_particles(frames, *, threshold=0.045, max_displacement_px=10.0, min_area_px=2, static_threshold=0.055)` (実装を直接呼ぶなら `import vialops; vialops.track_moving_particles(frames, *, threshold=0.045, max_displacement_px=10.0, min_area_px=2, static_threshold=0.055)`、台帳から引くなら `opspharma.get("track_moving_particles")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

画像列から動く物と静止したガラス傷を分け、軌跡表を返す。

Each frame is compared with the temporal median, so stationary scratches are
reported from the median image and moving objects from residual components.
Consecutive moving detections are linked greedily only within
``max_displacement_px``; ambiguous or too-large jumps start a new track
rather than being silently joined.  Every moving track is deliberately
labelled ``"moving"``: the frame-only API has neither a calibrated lighting
polarity nor enough 3-D trajectory context to identify a particle versus a
bubble.  In particular, residual swirl can make a settling particle have a
negative image-row velocity.  This is a conservative 2-D projection tracker,
not an identity-preserving multi-object tracker through overlap/occlusion.

動く軌跡は常に保守的に ``"moving"`` とし、速度符号だけで粒子/気泡を
推定しない。残留旋回では沈降粒子も画像上向きに見えるためである。

Returns a table with one row per detection: ``frame``, ``track_id``,
``object_class``, centroid, area, and row velocity.  Input must be a finite
non-constant ``(T,H,W)`` sequence with at least three frames.  A sequence
that is constant over both time and space is rejected; call it only for
images with a motion or spatial cue, and record ``no detected motion``
directly when the intended interpretation is no motion.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_vial_particle_pod](../../../../examples/poc_vial_particle_pod.py) — `py -3.11 examples/poc_vial_particle_pod.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`track`)

—

---
*Provenance: vialops.py — PHARMA operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
