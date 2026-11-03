---
op: pose_to_matrix
dim: reprconv
category: exit
in: pose
out: matrix
gpu: なし
examples: [type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# pose_to_matrix — REPRCONV `exit` op

- **データ種**: `pose` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.pose_to_matrix(pose)` (実装を直接呼ぶなら `import reprconv; reprconv.pose_to_matrix(pose)`、台帳から引くなら `opsreprconv.get("pose_to_matrix")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

剛体姿勢 ``pose (R, t)`` → 4×4 の同次変換 ``matrix``。

``dlt_pose`` / ``icp_point2point_3d`` / ``fit_rigid`` などは ``(R (3,3), t (3,))`` を返すが、
``rotation_translation_error`` などは 4×4 を受ける。``[[R, t], [0, 0, 0, 1]]`` に詰める。
既に 4×4 の配列が来たら、最下行が (0, 0, 0, 1) であることを確かめて写しを返す。
R が回転行列であること(``RᵀR = I``、``det R = +1``、公差 1e-6)を確かめる ——
相似変換や鏡映を黙って剛体として通さない。

Args:
    pose: ``(R, t)`` の 2-tuple / list、``{"R": .., "t": ..}`` の dict、または 4×4 配列。
Returns:
    (4, 4) float64。
Raises:
    ValueError: 形が違う / R が回転行列でない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[matrix_to_descriptor](../descriptor/matrix_to_descriptor.md) · [matrix_to_angle](../algebra/matrix_to_angle.md) · [matrix_to_rot_scale](../algebra/matrix_to_rot_scale.md)

## 同カテゴリ(`exit`)

[tokens_to_matrix](tokens_to_matrix.md) · [pairs_peak_x](pairs_peak_x.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
