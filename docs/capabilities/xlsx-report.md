---
id: xlsx-report
title: 型付きの検査結果を Excel(.xlsx)レポートに書き出す
title_en: Write typed inspection results to an Excel (.xlsx) report
category: 組み立てる
ops: [save_xlsx_report, report, to_markdown, save_json]
examples: [xlsx_report]
version: 0.2.1
---

# 型付きの検査結果を Excel(.xlsx)レポートに書き出す

## できること

検査の結果は現場では Excel で回ることが多い —— 測定表を貼る、良否を並べる、プレビュー画像を添える。`fullseye/xlsxio.py` の `save_xlsx_report(sections, path)` は、能力ノート `typed-results-as-markdown` の `report` と**同じ材料**(`(見出し, value, sort)` の列)から、そのまま `.xlsx` を作ります。`table` / `points` / `matrix` / `signal` / `vector` / `keypoints` / `counts` は本物のセルの表に、`feature` / `scalar` は 1 セルに、画像系(`image` / `color` / `region` …)はサムネイルを 1 枚埋め込みます。jsonio が「機械が bit で戻せる JSON」、mdio が「人が読む Markdown」なのに対し、xlsxio は「**現場が配る Excel**」—— 出力先が違うだけで、同じ 1 つの `sections` から 3 系統すべてを出せます。

openpyxl(optional 依存、`pip install "fullseye[xlsx]"`)を使います。無い環境では黙って別形式に落とさず、明示的に `ImportError`(何が要るかを言う)。画像の埋め込みに失敗しても**レポート本体は壊しません** —— その節は形・値域の 1 行要約セルに落ちます(fail-soft)。未知の sort は `ValueError` で断ります。

## What it does

`save_xlsx_report(sections, path)` writes the same `(heading, value, sort)` sections that `mdio.report` renders as Markdown, but as a real Excel workbook: tabular sorts (`table`, `points`, `matrix`, `signal`, `vector`, `keypoints`, `counts`) become spreadsheet cells, `feature` / `scalar` a single cell, and image-like sorts (`image`, `color`, `region` …) an embedded thumbnail. jsonio is the machine-exact JSON, mdio the human-readable Markdown, and xlsxio the shop-floor Excel — the same one `sections` list feeds all three, only the destination differs. It uses openpyxl (the optional `xlsx` extra) and raises a clear `ImportError` when it is missing rather than silently degrading; an image that cannot be embedded falls back to a one-line shape/range cell so a thumbnail never breaks the report (fail-soft). Unknown sorts raise `ValueError`.

## 向くところ / 向かないところ

**向く**: 検査結果(測定表・良否・座標・被覆率など)を Excel レポートにして配る/貼る、プレビュー画像つきの一枚もの報告、同じ `sections` から Markdown(PR・docs)と JSON(機械)と Excel(現場)を同時に出す、既存の測定 op(measure1d / shapestat / blob / spc)の出力をそのまま報告書化する。

**向かない**: ★**ライブの Excel アプリの特定セルへ貼り付ける**こと(それは win32com 等の OS/アプリ連携で、クロスプラットフォームでもテスト可能でもない —— ここは `.xlsx` ファイルを書き出す)。★大きな数値配列の全セル出力(`max_rows` で頭打ち。厳密さが要るなら `save_json` か `.npy`)。★画素そのものの精査(サムネイルは縮小 —— 原寸は `write_image` で別途)。★グラフ(チャート)の作図は現状しない(値のセルまで。図は `examplefig` / 疑似カラー op で作って埋める)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

blobs = [{"id": 1, "area": 12.5, "label": "OK"}, {"id": 2, "area": 3.0, "label": "NG"}]
pts = np.array([[10.5, 20.0], [30.25, 40.0]])
preview = fs.read_image("part.png")                    # プレビューに添える画像
fs.save_xlsx_report(
    [("欠陥ブロブ", blobs, "table"),
     ("重心座標", pts, "points"),
     ("被覆率", 0.42, "feature"),
     ("プレビュー", preview, "image")],
    "report.xlsx", title="検査レポート")                # 測定表 + 画像 1 枚の .xlsx
```

## 裏づけ

- 実装: `fullseye/xlsxio.py`(`save_xlsx_report`。sort ごとにセル/表/埋め込みを振り分け、画像は fail-soft)
- 例: [`xlsx_report`](../../examples/xlsx_report.py)(表・点群・スカラ・埋め込み画像を書いて openpyxl で開き直し検算 / 同じ sections から Markdown も)
- 試験: `tests/test_xlsxio.py`(書いて開き直しセル値と画像枚数 / facade 露出 / 未知 sort 拒否 / 節の形の検査 / thumbnails=False の要約フォールバック)
- 来歴: openpyxl(MIT、`docs/REFERENCES.md`)。`sections` の設計は能力ノート `typed-results-as-markdown` の `report` と共通。
