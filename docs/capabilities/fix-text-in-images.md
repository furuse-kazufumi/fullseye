---
id: fix-text-in-images
title: 画像の中の文字を、正しい文字列に合わせて直す
title_en: Fix the text inside an image against the string it should read
category: 見つける
ops: [glyph_correct_spec, glyph_rewrite_line, glyph_find_plate, glyph_typeface_noise_floor, glyph_rendering_noise_floor, glyph_distance, glyph_replace, glyph_split_cells, glyph_fonts]
examples: [fix_text_in_image, poc_glyph_typo_detection]
version: 0.2.1
---

# 画像の中の文字を、正しい文字列に合わせて直す

## できること

生成 AI が出したレポート用の画像や看板の文字が 1 字だけ壊れている —— そういうとき、画像を作り直さずに、**本当はこう書いてあるべき文字列**を渡して直せます。入口は JSON 一枚(`spec = {"items": [{"text": "電気設備", "bbox": [x, y, w, h]}]}`)で、Python の `glyph_correct_spec` からも MCP の `fullseye_fix_text` からも同じ形で呼べます。文字を**認識はしません**: 正しい文字列が与えられるので、各マスを指定の 1 字と 1 対 1 で照合するだけで済み、6,000 字の分類器は要りません。閾値は勘で置かず、その環境の書体で同じ字を描き分けた距離の 95 % 点(書体雑音の床)から導きます。

直し方は 2 つ。`mode="repair_flagged"`(既定)は床を超えた字**だけ**置き換えて正しい字には触らず、置換後に床より近くならなければ**元に戻します**(`failed_verification`)。`mode="rewrite_line"` は bbox の行を**同じ書体で丸ごと描き直す**ので、見逃し・誤検出が結果に残らず字数の違いも直りますが、書体は変わります。看板の板は `glyph_find_plate` で起こせます(縁の直線 4 本の交点で四隅を取る)。

報告は行ごとに `status`(`ok / replaced / failed_verification / skipped / rewritten`)、直せないときの `reason` と機械向けの `reason_code`(`glyphops.REASON_CODES` の鍵)、そして `mismatch`(`typo` = 誤字 / `unrelated` = **元の字が指示と無関係**な疑い / `none` / `unknown`)を返します。描き直しは別物でも成功してしまうので、「指示か画像のどちらかが違う」を別枝で返します。

## What it does

Fix the text inside an image against the string it should read, without regenerating the image: pass `{"items": [{"text": "...", "bbox": [x, y, w, h]}]}` to `glyph_correct_spec` (Python) or `fullseye_fix_text` (MCP). Nothing is recognised — the intended string is given, so each cell is verified one-to-one against one character, and the threshold comes from the typeface noise floor measured on the fonts of the environment. `repair_flagged` replaces only the glyphs above the floor and rolls back any replacement that does not verify; `rewrite_line` redraws the whole line in one typeface. The report carries a per-line `status`, a machine-readable `reason_code` for refusals, and `mismatch` (`typo` / `unrelated`) so that a caller notices when the original text has nothing to do with the intended one.

## 向くところ / 向かないところ

**向く**: 生成 AI の画像の誤字(レポートの図表の題、スライドの見出し、看板)。正しい文字列が分かっていて、行の位置(bbox)を与えられる場面。背景が単色で、文字が 1 色(縁取り・影・グラデが無い)。

**向かない**: ★**文字認識(OCR)ではありません**。何が書いてあるかは教えてもらう前提です。★**行の位置は呼ぶ側が与えます**。bbox を外したときの見逃しは `rewrite_line` でも防げません。★縁取り・影・グラデーションの文字は色が多峰なので**断ります**(`reason_code = multimodal_colour`)。黙って塗りません。★字が小さい(マス幅 90 px 未満)と距離の順序が壊れるので、看板は先に板を起こして拡大してください。★`mismatch` の境(床の 2 倍)は生成画像 26 枚での実測で、目安であって保証ではありません —— 比そのもの(`mismatch_ratio`)を併記します。★書体は環境のものを使います(`glyph_fonts()`)。CJK を描ける書体が無い環境では例外になります。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np
from PIL import Image

rgb = np.asarray(Image.open("report_figure.png").convert("RGB"), np.float64) / 255.0
spec = {"items": [{"text": "電気設備", "bbox": [24, 40, 384, 96]}],   # 行に密着した箱
        "policy": {"mode": "repair_flagged"}}                         # or "rewrite_line"
fixed, report = fs.glyph_correct_spec(rgb, spec)
for it in report["items"]:
    print(it["status"], it["text"], it.get("mismatch"), it.get("reason_code", ""))
    # replaced 電気設備 typo   ← 壊れた 1 字だけ置き換わり、正しい字には触っていない
Image.fromarray((fixed * 255).round().astype("uint8")).save("report_figure_fixed.png")
```

## 裏づけ

- op: `glyph_correct_spec`(入口)/ `glyph_rewrite_line` / `glyph_find_plate` / `glyph_typeface_noise_floor` / `glyph_rendering_noise_floor` / `glyph_distance` / `glyph_replace` / `glyph_split_cells`
- MCP: `fullseye_fix_text`([`docs/MCP.md`](../MCP.md) に呼び出し例)
- 例: [`fix_text_in_image`](../../examples/fix_text_in_image.py)(2 つのモード・`unrelated`・断る例、前後の図)、[`poc_glyph_typo_detection`](../../examples/poc_glyph_typo_detection.py)(真値を植えて検出率と誤検出を数える)
- 試験: `tests/test_glyphops.py`(床・置換・巻き戻し・描き直し・誤字/別物・理由の語彙)、`tests/test_mcp_server.py`(`fix_text` の本体・入口の拒否・`unrelated`)
