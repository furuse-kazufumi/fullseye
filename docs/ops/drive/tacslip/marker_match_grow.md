---
op: marker_match_grow
dim: drive
category: tacslip
in: matrix × matrix × scalar
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# marker_match_grow — DRIVE `tacslip` op

- **データ種**: `matrix × matrix × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.marker_match_grow(p0, p1, pitch_px: 'float', seed_tol: 'float' = 0.25, tols=(0.2, 0.3, 0.45), nb_r: 'float' = 1.6, border: 'float' = 2.0, max_iter: 'int' = 80) -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.marker_match_grow(p0, p1, pitch_px: 'float', seed_tol: 'float' = 0.25, tols=(0.2, 0.3, 0.45), nb_r: 'float' = 1.6, border: 'float' = 2.0, max_iter: 'int' = 80) -> 'dict'`、台帳から引くなら `opsdrive.get("marker_match_grow")`)

## 使い方

基準マーカー p0 と荷重後 p1(各 (N, 2) [px])の対応を**連続性で伸ばして**取る。返り ``i0``・``i1``(対応の index 配列)、``matched``。

規則格子では |u| がピッチ/2 を超えると最近傍も相関も隣のマーカーに飛ぶ(実測: 8 px 格子で 5 px のずれを PIV は −3 px と読む)。
種 = p0 の外接矩形の**縁(border·ピッチ以内)**にあるマーカーで、予測なしの最近傍が seed_tol·ピッチ以内かつ 2 番目が 0.75 ピッチより
遠いもの(「接触は視野の内側にあり縁は遠方場 = 小変位」という物理の前提。どこでも種にすると、核の変位 6.4 px が隣の基準位置から
1.6 px なのでピッチ 1 つ飛んだ偽の種が 27 個できた)。以後、未対応のマーカーは nb_r·ピッチ以内の既対応 2 点以上の変位の平均を予測にして
tol·ピッチ以内の最近傍を取り、tol は小さい値から段階的に緩める。1 つの p1 は 1 回しか使わない。
**Raises** ValueError: p0/p1 が (N, 2) でない、pitch_px ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
