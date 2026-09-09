---
op: shape_perturb
dim: shapestat
category: synth
in: points
out: points
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# shape_perturb — SHAPESTAT `synth` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.shape_perturb(shape, amplitude: 'float' = 0.05, mode: 'str' = 'bulge', center=(1.0, 0.0, 0.0), sigma: 'float' = 0.4, seed: 'int' = 0)` (実装を直接呼ぶなら `import shapestats; shapestats.shape_perturb(shape, amplitude: 'float' = 0.05, mode: 'str' = 'bulge', center=(1.0, 0.0, 0.0), sigma: 'float' = 0.4, seed: 'int' = 0)`、台帳から引くなら `opsshapestat.get("shape_perturb")`)

## 使い方

形に**既知の**変形を 1 つ入れる。→ ``(N, 3)``。

``mode``:

* ``"bulge"``  —— *center* のまわりをガウス重みで外向きに膨らませる。
  片側だけに入れれば左右非対称性の真値になる。
* ``"shift"``  —— *center* 方向へ一様に平行移動(Procrustes が消す成分)。
* ``"scale"``  —— 一様拡大(``scaling=True`` の Procrustes が消す成分)。
* ``"noise"``  —— 等方ガウス雑音(どの手法でも消えない床)。

「Procrustes が消してくれる変形」と「消してはいけない変形」を分けて試せる
ように 4 つ置いてある。位置合わせの検算はこの区別が要る。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`points` を入力に取れる)

[procrustes_fit](../procrustes/procrustes_fit.md) · [procrustes_align](../procrustes/procrustes_align.md) · [procrustes_distance](../procrustes/procrustes_distance.md) · [shape_project](../model/shape_project.md) · [shape_mahalanobis](../model/shape_mahalanobis.md) · [mirror_plane_from_pairs](../symmetry/mirror_plane_from_pairs.md) · [landmark_asymmetry](../symmetry/landmark_asymmetry.md) · [signed_surface_distance](../deviation/signed_surface_distance.md)

## 同カテゴリ(`synth`)

[shape_synth_family](shape_synth_family.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
