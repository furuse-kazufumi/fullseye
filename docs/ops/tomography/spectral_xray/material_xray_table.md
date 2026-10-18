---
op: material_xray_table
dim: tomography
category: spectral_xray
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# material_xray_table — TOMOGRAPHY `spectral_xray` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.material_xray_table() -> 'list'` (実装を直接呼ぶなら `import materials; materials.material_xray_table() -> 'list'`、台帳から引くなら `opstomography.get("material_xray_table")`)

## 使い方

X 線の列(質量減衰係数 μ/ρ)を引ける材料の一覧を返す。

返り値: 1 材料 1 行の dict(name, kind = table / mixture / element, density_g_cm3, composition
((記号, 質量分率), …), optical(光学の表にも同じ名前のレコードがあるか), reference)。
元素 49 種と NIST の化合物 20 種は NIST SRD 126(Hubbell & Seltzer)の表そのもの、それ以外は
:data:`XRAY_SOLID`(と電子線の表)の組成から混合則で作る。範囲は 1 keV〜1 MeV(表の外は外挿しない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`spectral_xray`)

[material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md) · [xray_channel_projection](xray_channel_projection.md)

---
*Provenance: materials.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
