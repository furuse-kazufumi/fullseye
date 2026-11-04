---
op: keypoints_rowcol_to_uv
dim: reprconv
category: keypoint
in: keypoints
out: keypoints
gpu: なし
examples: [poc_bga_ball_type_roundtrip, type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# keypoints_rowcol_to_uv — REPRCONV `keypoint` op

- **データ種**: `keypoints` → `keypoints`
- **呼び出し**: `import fullseye as fs; fs.ledger.keypoints_rowcol_to_uv(keypoints)` (実装を直接呼ぶなら `import reprconv; reprconv.keypoints_rowcol_to_uv(keypoints)`、台帳から引くなら `opsreprconv.get("keypoints_rowcol_to_uv")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

像面の点 ``(row, col)`` → ``(u, v) = (col, row)``。``keypoints`` 型の 2 つの流儀のつなぎ。

``keypoints`` 型には 2 つの軸の約束が同居している(実測): ``calib.project_3d_point`` などは
**(row, col)**、``project_points`` / ``dlt_pose`` / ``pnp_ransac`` は **(u, v) = (列, 行)**。
取り違えても例外は出ず、姿勢が鏡に映ったように出る(W2 の実測: t = (−0.565, 0.61, 3.21)
のはずが (0.1, −0.05, 3.0))。列を入れ替えるだけだが、**どちらの向きかを op 名に書く**ため
逆向きの :func:`keypoints_uv_to_rowcol` と 2 本に分けてある(中身は同じ入れ替え)。

Args:
    keypoints: (N, 2) の (row, col)。
Returns:
    (N, 2) float64 の (u, v)。
Raises:
    ValueError: (N, 2) でない / 非有限 / 空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_bga_ball_type_roundtrip](../../../../examples/poc_bga_ball_type_roundtrip.py) — `py -3.11 examples/poc_bga_ball_type_roundtrip.py`
- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[keypoints_uv_to_points](keypoints_uv_to_points.md) · [keypoints_to_image2d](keypoints_to_image2d.md) · [keypoints_uv_to_rowcol](keypoints_uv_to_rowcol.md)

## 同カテゴリ(`keypoint`)

[keypoints_uv_to_points](keypoints_uv_to_points.md) · [points_zyx_to_keypoints_uv](points_zyx_to_keypoints_uv.md) · [keypoints_to_image2d](keypoints_to_image2d.md) · [keypoints_from_image2d](keypoints_from_image2d.md) · [position_to_points](position_to_points.md) · [points_to_position](points_to_position.md) · [keypoints_uv_to_rowcol](keypoints_uv_to_rowcol.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
