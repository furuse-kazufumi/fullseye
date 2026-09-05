---
op: gaussians_to_voxel
dim: reprconv
category: gaussians
in: gaussians
out: voxel
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# gaussians_to_voxel — REPRCONV `gaussians` op

- **データ種**: `gaussians` → `voxel`
- **呼び出し**: `import reprconv; reprconv.gaussians_to_voxel(gaussians, shape=(32, 32, 32), origin=(0.0, 0.0, 0.0), spacing=(1.0, 1.0, 1.0), truncate=3.0)` (または `opsreprconv.get("gaussians_to_voxel")`)

## 使い方

``gaussians`` → 密度 ``voxel (D,H,W)``。``gaussians`` の 2 つ目の出口。

各ガウシアンを ``truncate * sigma`` で打ち切って加算する。**格子の原点と
刻みを明示引数にしてある**のが要点で、既定の ``spacing=(1,1,1)`` を
そのまま使うと「世界座標をそのまま添字にする」ことになり、実データでは
まず間違う —— しかも例外は出ず、密度が別の場所に立つだけなので気づけない。
``tests/test_reprconv.py`` はこの取り違えを明示的に測っている。

**不可逆**。損失は 3 つあり、どれも数字で測れる:
  * **打ち切り** —— 打ち切りは**軸並行の箱**(各軸 ±truncate*sigma)なので、
    残る質量は ``erf(t/sqrt(2))**3``。t = 3 で **99.194%**。
    ★ここは一度間違えた: 最初「3 sigma の**球**の質量 97.07%」と書いたが、
    実装は箱なので値が違う。刻みを 1.0 → 0.125 と細かくして極限を取ると
    99.30% → 99.19% へ収束し、球の 97.07% には**近づかない**ことで反証できた
    (``tests/test_reprconv.py::test_gaussians_to_voxel_mass_matches_box_truncation``)。
    例外も NaN も出ない、まさに「黙って間違った数字を返す」種類の誤り。
  * **格子求積** —— 中点則なので刻みが sigma に対して粗いと**上振れ**する
    (実測: sigma = 1.5 で刻み 1.0 のとき 99.94%、0.125 で 99.30%)。
  * **境界の切り落とし** —— 箱が volume の外へ出た分は落ちる。中心が縁に
    近いガウシアンでは打ち切りより遥かに大きい損失になる。

Args:
    gaussians: ``mu`` / ``sigma`` / ``w`` を持つ dict。``mu`` は (z, y, x)。
    shape: (D, H, W)。
    origin: 格子の (z, y, x) 原点(世界座標)。
    spacing: 格子の (dz, dy, dx) 刻み(世界単位 / voxel)。
    truncate: 何 sigma で打ち切るか(既定 3)。
Returns:
    (D, H, W) float64 の密度(値は「voxel あたりの重み和」で、体積積分が
    ``sum(w)`` に近づく)。
Raises:
    ValueError: shape/spacing 不正 / truncate <= 0 / gaussians 不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[correlation_score](../score/correlation_score.md)

## 同カテゴリ(`gaussians`)

[points_to_gaussians](points_to_gaussians.md) · [gaussians_to_points](gaussians_to_points.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
