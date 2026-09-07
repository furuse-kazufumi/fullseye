---
op: profile_normalise
dim: profile
category: frame
in: pairs
out: pairs
examples: [profile_frame_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# profile_normalise — PROFILE `frame` op

- **データ種**: `pairs` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.profile_normalise(contour)` (実装を直接呼ぶなら `import profileops; profileops.profile_normalise(contour)`、台帳から引くなら `opsprofile.get("profile_normalise")`)

## 使い方

弦長 1・前縁が原点・弦が +x になるよう回転と並進で正規化する。

**スケールは弦長でしか変えない**(形を歪めない)。返りは正規化した輪郭。

手順: ``profile_chord_frame`` で前縁 ``le``・後縁 ``te``(開いた後縁は隙間の
中点)・弦長 ``chord``・弦の向き ``angle_deg`` を求め、
``((contour - le) @ R(-angle).T) / chord`` を返す。回転・並進・一様スケールの
相似変換だけで、点の数と順序は保つ(再標本化しない)。

- ``contour``: ``(N, 2)`` の **(x, y)**、8 点以上、有限。``(row, col)`` を渡すと
  弦は見つかるが上下が入れ替わる(例外は出ない)。閉じているかはここでは
  検査しない(``profile_sides`` 以降が検査する)。
- 返り値: ``(N, 2)`` float64。前縁が ``(0, 0)``、後縁が ``(1, 0)`` 付近、
  ``x`` は ``[0, 1]`` の弦比。``y`` の符号(上面が正か負か)は入力の周回方向
  で決まり、反転はしない。
- 失敗: ``ValueError``(形、点数不足、非有限、弦長が 0 = 全点一致)。

前縁・後縁の判定は「最遠点対のうち、少し内側で断面が太いほう = 前縁」なので、
前後で太さが同じ対称な断面(楕円など)では前後が入れ替わることがある。
``profile_sides`` / ``profile_thickness`` / ``profile_camber`` は内部でこれを呼ぶ。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_frame_tour](../../../../examples/profile_frame_tour.py) — `py -3.11 examples/profile_frame_tour.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[profile_perturb](../synth/profile_perturb.md) · [profile_chord_frame](profile_chord_frame.md) · [profile_resample](profile_resample.md) · [profile_sides](../measure/profile_sides.md) · [profile_thickness](../measure/profile_thickness.md) · [profile_camber](../measure/profile_camber.md) · [profile_leading_edge_radius](../measure/profile_leading_edge_radius.md) · [profile_trailing_edge_gap](../measure/profile_trailing_edge_gap.md)

## 同カテゴリ(`frame`)

[profile_chord_frame](profile_chord_frame.md) · [profile_resample](profile_resample.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
