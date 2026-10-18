---
op: lens_section_drawing
dim: optics
category: drawing
in: table
out: table
examples: [poc_lens_file_roundtrip, poc_optics_drawings]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# lens_section_drawing — OPTICS `drawing` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lens_section_drawing(system, fields=None, rays=3, lead_mm=None, edge_margin_pct=5.0, scale=None, profile_points=121, title=None)` (実装を直接呼ぶなら `import optdraw; optdraw.lens_section_drawing(system, fields=None, rays=3, lead_mm=None, edge_margin_pct=5.0, scale=None, profile_points=121, title=None)`、台帳から引くなら `opsoptics.get("lens_section_drawing")`)

## 使い方

レンズの子午断面図(``table``、図の dict)—— 処方の面・コバ・絞り・像面と、視野ごとに色を分けた実光線と寸法。

*system* は ``raytrace.lens_system`` の処方。*fields* は視野の列(物体が無限遠なら度、有限なら物体の高さ mm、
既定は処方の ``field`` を F として ``(0, 0.7F, F)``、F = 0 なら軸上だけ)、*rays* は視野ごとに描く光線の本数
(絞りの上で等間隔、両端は口径の縁、1 なら主光線だけ)。光線は**絞りを狙って**実光線で追跡する(割線法で絞りの
上の高さを合わせる)ので、入射瞳が無限遠の物体側テレセンでも描ける。面の形は ``raytrace`` の sag の式(円錐 +
偶数次の非球面)、面の有効半径は面の ``ap``、無ければ全視野の子午面の実光線(視野あたり 21 本)の最大の高さ。
コバ(レンズの外周)は有効半径の最大に *edge_margin_pct* % を足した半径で、有効半径の外は平らな座で描く
(光学設計ソフトの断面図と同じ作法)。

寸法線: BFL(最終面 → 後側焦点 F′)・EFL(後側主点 H′ → F′)・全長(第 1 面 → 像面)・像高(最大視野の主光線)。
処方表(面ごとの R・間隔・n_d・ν_d)と諸元(EFL・BFL・F 値・全長・視野・波長)を文字で書く。*scale* は
紙の mm / 実物の mm(既定は ISO 5455 の推奨尺度から幅 250 mm に収まる最大)。

返り値: ``{"kind": "optdraw", "entities", "dimensions", "values", "meta", "scale", "frame"}``。``values`` は
図に書いた数の正本(``efl`` / ``bfl`` / ``total_track`` / ``image_height`` / ``fno`` / 面ごとの
``vertex_z`` ``semi_diameter`` / 光線ごとの面上の交点 ``rays``)。``drawing_svg`` / ``drawing_dxf`` で書き出す。
平面の ``R`` は ``lens_system`` の規約どおり ``inf``、無焦点の系(両側テレセン)の ``efl`` / ``bfl`` も ``inf``
(非有限は契約。図には描かず、描かなかった寸法の名前を ``dimensions_skipped`` に残す)。
鏡・傾き・偏心のある処方(と ``raytrace3d.noncoaxial_system`` の系)は ``noncoaxial_drawing`` に回す(折り返した系の
断面図)。★縁の厚さが負になる処方は ValueError。

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

- [poc_lens_file_roundtrip](../../../../examples/poc_lens_file_roundtrip.py) — `py -3.11 examples/poc_lens_file_roundtrip.py`
- [poc_optics_drawings](../../../../examples/poc_optics_drawings.py) — `py -3.11 examples/poc_optics_drawings.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`drawing`)

[vision_setup_drawing](vision_setup_drawing.md) · [lens_element_drawing](lens_element_drawing.md) · [drawing_svg](drawing_svg.md) · [drawing_dxf](drawing_dxf.md) · [drawing_raster](drawing_raster.md) · [svg_entities](svg_entities.md) · [dxf_entities](dxf_entities.md) · [noncoaxial_drawing](noncoaxial_drawing.md)

---
*Provenance: optdraw.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
