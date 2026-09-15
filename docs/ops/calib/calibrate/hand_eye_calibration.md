---
op: hand_eye_calibration
dim: calib
category: calibrate
in: pose
out: pose
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# hand_eye_calibration — CALIB `calibrate` op

- **データ種**: `pose` → `pose`
- **呼び出し**: `import fullseye as fs; fs.ledger.hand_eye_calibration(poses_a, poses_b)` (実装を直接呼ぶなら `import calib; calib.hand_eye_calibration(poses_a, poses_b)`、台帳から引くなら `opscalib.get("hand_eye_calibration")`)

## 使い方

一連の運動対から AX=XB を解き X(4x4)を推定(hand_eye_calibration)。
poses_a/poses_b: 4x4 剛体変換のリスト。隣接運動から相対運動を構成。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`pose` を入力に取れる)

—

## 同カテゴリ(`calibrate`)

[camera_calibration](camera_calibration.md) · [find_marks_and_pose](find_marks_and_pose.md)

---
*Provenance: calib.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
