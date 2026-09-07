---
op: dem_fill_sinks
dim: dem
category: hydrology
in: depth
out: depth
examples: [poc_dem_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_fill_sinks — DEM `hydrology` op

- **データ種**: `depth` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_fill_sinks(dem, epsilon=0.0, nodata='error')` (実装を直接呼ぶなら `import demops; demops.dem_fill_sinks(dem, epsilon=0.0, nodata='error')`、台帳から引くなら `opsdem.get("dem_fill_sinks")`)

## 使い方

窪地を埋めた DEM。Barnes, Lehman & Mulla (2014) の priority-flood。

``epsilon`` に微小値(例 1e-6)を与えると、埋めた平坦面にわずかな傾斜を付ける
(これが無いと平坦面で流向が決まらず、集水量が途中で消える)。

``nodata`` は :data:`NODATA_POLICIES`。``"outlet"`` なら欠測セルを外周と同じ
**種**として扱う(水域に流れ込んだ水はそこで系を出る)。``"barrier"`` なら
欠測は埋めの対象から外し、値を ``nan`` のまま返す。

出力は入力以上(``filled >= dem``、欠測を除く)。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dem_terrain](../../../../examples/poc_dem_terrain.py) — `py -3.11 examples/poc_dem_terrain.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[dem_slope](../surface/dem_slope.md) · [dem_aspect](../surface/dem_aspect.md) · [dem_curvature](../surface/dem_curvature.md) · [dem_roughness](../surface/dem_roughness.md) · [dem_tpi](../surface/dem_tpi.md) · [dem_hillshade](../shading/dem_hillshade.md) · [dem_flow_direction](dem_flow_direction.md) · [dem_flow_accumulation](dem_flow_accumulation.md)

## 同カテゴリ(`hydrology`)

[dem_flow_direction](dem_flow_direction.md) · [dem_flow_accumulation](dem_flow_accumulation.md) · [dem_stream_network](dem_stream_network.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
