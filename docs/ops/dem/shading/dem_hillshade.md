---
op: dem_hillshade
dim: dem
category: shading
in: depth
out: image2d
examples: [poc_dem_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_hillshade — DEM `shading` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import demops; demops.dem_hillshade(dem, cell_size, azimuth_deg=315.0, altitude_deg=45.0, z_factor=1.0, method='horn')` (または `opsdem.get("dem_hillshade")`)

## 使い方

陰影起伏 [0,1]。``azimuth_deg`` は光源の方位(北 0 度・東回り)。

Lambert の余弦則そのもので、**遮蔽は考えない**(自分より手前の尾根で
影になる分は含まれない)。落ちる影が要るなら :func:`dem_horizon_angle` と
組み合わせること —— 「陰影起伏に影が入っている」と思い込むのが定番の誤解。

平坦面では ``sin(altitude)`` に一致する(実測 1e-15 以下)。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dem_terrain](../../../../examples/poc_dem_terrain.py) — `py -3.11 examples/poc_dem_terrain.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

—

## 同カテゴリ(`shading`)

—

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
