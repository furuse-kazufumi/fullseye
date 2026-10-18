---
op: linescan_lens_example
dim: optics
category: linescan
in: 
out: table
examples: [poc_tdi_linescan]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# linescan_lens_example — OPTICS `linescan` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.linescan_lens_example(kind='linescan')` (実装を直接呼ぶなら `import linescan; linescan.linescan_lens_example(kind='linescan')`、台帳から引くなら `opsoptics.get("linescan_lens_example")`)

## 使い方

ラインスキャンの撮像系の模型 2 つ(``raytrace.lens_system`` の ``table``)。

どちらも Cooke の三枚玉(SK16 相当のクラウン / F2 相当のフリント / SK16 相当、絞りは中玉の後ろ)を、57.344 mm(8192 × 7 µm)のセンサで
幅 300 mm の web を見る倍率 −0.1911 に合わせて ``lensopt.optimize_lens`` で最適化した処方:

* ``"linescan"``: f 90 mm、物体距離 519 mm、像高 28.7 mm(センサの端)まで最適化、大きい口径
  —— **ラインスキャン用レンズ**の模型(像円がセンサを覆う)。
* ``"cmount"``: f 35 mm、物体距離 201 mm、2/3 型の像高 5.5 mm までで最適化し、口径も 2/3 型用
  —— **普通の C マウントレンズを長いセンサに流用**した模型。同じ形・同じ硝材で、違いは像円だけ。

実在の型番の処方ではない(メーカーの処方は公開されていない)。像円の大きさと口径食の有無という
**性質**を見るための模型。

**Raises** ``ValueError``: kind が ``"linescan"`` / ``"cmount"`` でない。

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tdi_linescan](../../../../examples/poc_tdi_linescan.py) — `py -3.11 examples/poc_tdi_linescan.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`linescan`)

[tdi_snr](tdi_snr.md) · [tdi_sync_mtf](tdi_sync_mtf.md) · [linescan_acquire](linescan_acquire.md) · [lens_field_profile](lens_field_profile.md) · [linescan_lens_columns](linescan_lens_columns.md)

---
*Provenance: linescan.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
