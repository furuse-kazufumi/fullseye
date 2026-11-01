---
op: gs_catalog_html
dim: drive
category: gsplat
in: table
out: table
gpu: なし
examples: [gsplat_product_viewer]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# gs_catalog_html — DRIVE `gsplat` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gs_catalog_html(items, out_path=None, *, title='3DGS catalogue', lang=('ja', 'en', 'zh', 'tw', 'ko', 'de', 'hi', 'fr'), up=(0.0, 0.0, 1.0), bg: 'str' = 'gray', max_bytes: 'int' = 16777216, unit_mm: 'float' = 1000.0, fov_deg: 'float' = 35.0, thumb_px: 'int' = 256, dims=True, spin: 'bool' = True, spin_deg_per_s: 'float' = 20.0, bake_light=(0.3, -0.5, 0.8), ambient: 'float' = 0.35, max_radius: 'int' = 64, mobile_quality=0.5, mobile_above: 'int' = 300000) -> 'dict'` (実装を直接呼ぶなら `import gsviewer; gsviewer.gs_catalog_html(items, out_path=None, *, title='3DGS catalogue', lang=('ja', 'en', 'zh', 'tw', 'ko', 'de', 'hi', 'fr'), up=(0.0, 0.0, 1.0), bg: 'str' = 'gray', max_bytes: 'int' = 16777216, unit_mm: 'float' = 1000.0, fov_deg: 'float' = 35.0, thumb_px: 'int' = 256, dims=True, spin: 'bool' = True, spin_deg_per_s: 'float' = 20.0, bake_light=(0.3, -0.5, 0.8), ambient: 'float' = 0.35, max_radius: 'int' = 64, mobile_quality=0.5, mobile_above: 'int' = 300000) -> 'dict'`、台帳から引くなら `opsdrive.get("gs_catalog_html")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

複数の 3DGS をサムネイルの一覧から選んで見る、1 枚で完結するカタログの HTML を書く。

各品のサムネイルは :func:`gsplatnp.gs_render`(numpy の EWA 描画)が、ページの最初の視点と同じカメラで描いた PNG
(``thumb_px`` 四方)。押すと同じページの中で 3-D の表示に切り替わり、「一覧に戻る」(Esc でも)で戻る。
データは選ばれた品の分だけ ``DecompressionStream`` で伸ばし、切り替えると前の品のテクスチャ・バッファを解放する。
容量の上限 ``max_bytes`` は全体で、品ごとの割り当て = (上限 − ページ − サムネイル) をガウシアンの数に比例して配る。
割り当てを超える品は :func:`gs_viewer_html` と同じ順で間引き、品ごとの記録を返す。

Parameters
----------
items : list of dict
    ``{"gs": dict | "path": str, "name": str|{lang}, "desc": str|{lang}, "note": str|{lang}, "hotspots": [...],
    "camera": {...}}``。``name`` は必須。
out_path, title, lang, up, bg, max_bytes, unit_mm, fov_deg, dims, spin, bake_light, ambient, max_radius, mobile_quality :
    :func:`gs_viewer_html` と同じ。
thumb_px : int
    サムネイルの 1 辺(画素)。

Returns
-------
dict
    ``path``・``bytes``・``items``(品ごとの ``n_input`` / ``n_kept`` / ``n_dropped`` / ``thinned`` / ``dims_mm`` /
    ``thumb_bytes`` / ``camera``)・``n_dropped_total``・``external_urls``(= 0)。``out_path`` が None なら ``html`` も。

Raises
------
ValueError
    items が空・name が無い・gs と path のどちらも無い、ほかは :func:`gs_viewer_html` と同じ。

空の入力(``items`` が空の list)は ValueError。

Examples
--------
>>> import gsviewer
>>> r = gsviewer.gs_catalog_html([{"path": "mug.ply", "name": "Mug"}, {"path": "shoe.splat", "name": "Shoe"}],
...                              "catalog.html", title="Shop")                        # doctest: +SKIP

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gsplat_product_viewer](../../../../examples/gsplat_product_viewer.py) — `py -3.11 examples/gsplat_product_viewer.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`gsplat`)

[gs_from_world](gs_from_world.md) · [gs_update](gs_update.md) · [gs_render](gs_render.md) · [gs_render_fn](gs_render_fn.md) · [gs_read_file](gs_read_file.md) · [gs_viewer_html](gs_viewer_html.md)

---
*Provenance: gsviewer.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
