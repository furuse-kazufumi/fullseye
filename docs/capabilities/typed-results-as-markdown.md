---
id: typed-results-as-markdown
title: op の返り値(型付き)を Markdown で読める形にし、JSON を埋め込んで戻す
title_en: Render typed op results as Markdown, with an exact JSON block to read back
category: 組み立てる
ops: [to_markdown, json_block, extract_json, report]
examples: [typed_results_markdown]
version: 0.2.1
---

# op の返り値(型付き)を Markdown で読める形にし、JSON を埋め込んで戻す

## できること

JSON と Markdown は一緒に使う場面が多い —— 結果を報告書の中に貼る、数の表を「読ませる」、レビューに残す。機械に厳密な JSON 形(能力ノート `typed-results-as-json`)に対し、`fullseye/mdio.py` は**人が読む形**と、その**間の橋**を与えます。

- `to_markdown(value, sort)` は型付きの値を GitHub 風 Markdown にします。`table` / `points` / `matrix` / `signal` は本物の表(`max_rows` × `max_cols` で頭打ち、切ったら注記)、文字にできないもの(`image` は形・dtype・値域、`region` は被覆率と外接矩形)は 1 行の要約。**画素を絵に描いたふりはしません**。
- `json_block(value, sort)` は**厳密な** JSON 封筒を ```` ```json ```` フェンスに包みます。Markdown 文書の中に値を置いても bit 一致で戻せます(`readable=True` が既定なので差分に優しい)。
- `extract_json(md)` は Markdown 文字列を読み、フェンスの中の fullseye 封筒を全部 `(value, sort)` で返します。fullseye 封筒でないフェンス(普通の json や python)は無視、fullseye 封筒なのに壊れていれば fail-closed。
- `report(sections)` は `(見出し, value, sort)` の列を 1 つの Markdown 文書にします。各節に読める描画を並べ、`with_json=True` なら厳密な封筒を `<details>` に畳んで下に置く —— **同じ文書が「読める」と「機械で戻せる」を両立**します。

## What it does

The Markdown companion of jsonio. `to_markdown` renders a typed value as GFM — real tables for tabular and small numeric sorts (capped, with a truncation note), a one-line summary for things that are not text (an image is its shape and range). `json_block` wraps the exact JSON envelope in a ```` ```json ```` fence so a value survives inside prose and round-trips bit-for-bit through `extract_json`, which pulls every fullseye envelope out of a Markdown string and ignores foreign fences. `report` folds a list of sections into one document that is both readable and, with `with_json=True`, machine-recoverable. Fail-closed on an unknown sort, exact wherever a machine reads it back.

## 向くところ / 向かないところ

**向く**: 検査結果を報告書・PR・ドキュメントに読める形で載せる、数の表や台帳を Markdown 表にする、「読める文書」に厳密な JSON を同梱して後で機械が回収する、MCP の人間向け出力(text)と構造化出力(structuredContent)を 1 か所で作る。

**向かない**: ★画像そのものの表示(要約しかしません —— 図は `examplefig` / 疑似カラー op へ)。★大きな数値配列を表に全部出すこと(頭打ちが既定。厳密さが要るなら `json_block` か `.npy`)。★`to_markdown` の描画から値を読み戻すこと(丸めるので、戻すのは常に `json_block` / `extract_json` 経由)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

blobs = [{"id": 1, "area": 12.5, "label": "A"}, {"id": 2, "area": 3.0, "label": "B"}]
print(fs.to_markdown(blobs, "table"))                 # 本物の GFM 表

pts = np.array([[1.5, 2.0], [3.25, 4.0]])
doc = fs.report([("Blobs", blobs, "table"), ("Points", pts, "points")],
                title="Inspection", with_json=True)   # 読める + 機械で戻せる 1 文書
back = fs.extract_json(doc)                            # [(array, 'table'?...), (pts, 'points')]
assert np.array_equal(back[-1][0], pts)
```

## 裏づけ

- 実装: `fullseye/mdio.py`(jsonio を土台に。sort の一覧は `fs.JSON_SORTS`)
- 例: [`typed_results_markdown`](../../examples/typed_results_markdown.py)
- 試験: `tests/test_mdio.py`(dict 列の GFM 表と鍵の和集合 / 数値 sort の頭打ち / 非テキストの要約 / パイプのエスケープ / fail-closed / json_block ↔ extract_json の bit 一致往復 / 異種フェンス無視 / report の読める+戻せる)
