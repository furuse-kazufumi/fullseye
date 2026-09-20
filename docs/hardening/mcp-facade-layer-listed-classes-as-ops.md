---
id: mcp-facade-layer-listed-classes-as-ops
date: 2026-09-20
found_by: genspark_external_review
kind: silent-wrong
severity: medium
where: [fullseye/mcp/catalog.py]
ops: []
gate: [test_facade_layer_lists_functions_only, test_search_surface_carries_no_class_names, test_real_facade_functions_stay_searchable]
status: fixed
---

# MCP カタログの facade 層がクラス 41 個を op として並べていた

## 症状

GenSpark 第 41 報(2026-09-20)N141: 「facade ソースに facade 表に無い名前が 474 件、Python のクラス名を含む」。
master で再現 —— `Catalog.load()` の 2,497 項目のうち facade だけの項目 501 件に、`Image` / `Pipeline` /
`FullseyeEngine` / `VideoPipeline` / `MissingBackendError` / `TcpChannel` / `ModbusTcpServer` などクラス **41 個**が
op として入っていた。`fullseye_search_ops("Pipeline")` がクラスを「op」として返し、LLM の検索面を汚す。

## なぜ門が通したか

facade 層は「`import fullseye` で呼べる名前」を **`callable` かどうか**だけで op と数えていた。クラスは callable で
ある。門は「facade だけの実関数が検索で出る」(`census_transform`)を問い、**出てはいけない物**を問わなかった。

**474 件の内訳**: 41 件がクラス、460 件は `orient2d` / `point_in_polygon` / `census_transform` のような
`import fullseye` で呼べる実関数。GenSpark が比較相手にした `halcon_facade_map.json` は HALCON 対応表
(鍵は `camera.distort_points` の名前空間つき、601 項目)で、facade 名の正本ではない —— 表の目的が違うので、
「表に無い = 汚染」ではない。「表の鍵 515 件が欠落」も同じ理由(名前空間つきの鍵は項目名にならない)。

## 直し

`fullseye/mcp/catalog.py`: facade 層に数えるのは **関数だけ**(`callable` かつ `inspect.isclass` でも
`inspect.ismodule` でもない)。facade 総数 1,069 → 1,028、項目 2,497 → 2,456。実関数は 1 本も減らない(門で固定)。
