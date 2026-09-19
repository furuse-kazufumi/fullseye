---
id: golden-compare
title: 基準画像(ゴールデン)と比べて欠陥を測り、ロットごと判定する
title_en: Compare against a golden image — align, diff, count defects, judge the lot
category: 組み立てる
ops: [compare_to_golden, golden_measure, golden_spec, inspect_batch, judge, ssim, psnr]
examples: [golden_compare]
version: 0.2.1
---

# 基準画像(ゴールデン)と比べて欠陥を測り、ロットごと判定する

## できること

現場でいちばん多い検査は「良品の画像と比べて違うところを探す」です。`fullseye/golden.py` の `compare_to_golden(image, golden)` はそれを 1 回の呼び出しにします —— 位相相関で整数並進を合わせ(`max_shift` を超える推定は採用せず `align_ok=0` で返す)、任意でガウス平滑してから差分 `|image − golden|` を取り、`threshold` を超えた画素を検査領域 `mask` の中で連結成分にして `min_area` 未満を落とし、計測 dict `{shift_row, shift_col, align_ok, ssim, psnr, max_diff, mean_diff, defect_area, defect_count, defect_area_max, valid_fraction}` と差分の絵(`diff` / `defect_mask` / `labels`)を返します。位置合わせで画像の外から巻き込んだ縁は `valid` から外し、欠陥にも平均にも数えません。

この計測 dict はそのまま能力ノート `inspection-workflow` の `judge` に渡せます。`golden_measure(golden, ...)` は `inspect_batch` の `measure` を作り、`golden_spec(max_defect_area=0, max_shift=3, ...)` は対応する仕様を組みます —— フォルダを指すだけでロット全体がゴールデン比較され、欠陥品と大きくずれた品だけが `ng` になります。形が違う・2-D でない・NaN を含む画像、golden と形の違う `mask`、`min_area < 1` は `ValueError` で止まります(黙って 0 欠陥にしない)。

## What it does

`compare_to_golden(image, golden)` turns "find what differs from a known-good part" into one call: estimate the integer translation by phase correlation (estimates beyond `max_shift` are not applied and flagged `align_ok=0`), optionally Gaussian-smooth both images, take `|image − golden|`, threshold it inside the inspection `mask`, label the connected components and drop those under `min_area`. It returns a measurement dict (`shift_row`, `shift_col`, `align_ok`, `ssim`, `psnr`, `max_diff`, `mean_diff`, `defect_area`, `defect_count`, `defect_area_max`, `valid_fraction`) plus the pictures (`diff`, `defect_mask`, `labels`, `valid`). Border pixels wrapped in by the alignment are excluded from every count. `golden_measure(golden, ...)` makes the `measure` callable for `inspect_batch` and `golden_spec(...)` the matching `judge` spec, so pointing at a folder inspects the whole lot against the golden. Mismatched shapes, non-2-D or non-finite images, a mask of the wrong shape and `min_area < 1` raise `ValueError` — never a silent zero-defect result.

## 向くところ / 向かないところ

**向く**: 治具で位置がほぼ決まる部品の異物・欠け・印刷抜け(並進 ±数 px)、良品 1 枚を基準にしたロット検査、差分の絵を `defect_mask` で図に出す、`ssim` / `psnr` を品質の連続指標として SPC(`inspect_batch` の `spc`)に流す、検査領域を `mask` で限定する(ラベル・可変部を除外)。

**向かない**: ★**回転・スケール・サブピクセルのずれ**(整数並進のみ。先に `frame_align` や形状マッチで合わせる)。★**照明が毎回違う**現場(差分に乗る。前処理レシピで正規化してから)。★**周期構造**(網点・格子)の位置合わせ —— 位相相関は格子 1 個ぶんずれた答えを自信をもって返しうるので `max_shift` で縛る。★良品ばらつきが大きい品(基準 1 枚では ng が増える。統計的な基準や学習モデルの領域)。

## 最初の 1 本

```python
import fullseye as fs

golden = fs.read_image("golden.png")
out = fs.compare_to_golden(fs.read_image("part_017.png"), golden, threshold=0.2, max_shift=3, min_area=4)
print(out["measurements"]["defect_count"], out["measurements"]["defect_area"])
fs.write_image("part_017_defects.png", out["defect_mask"])          # 欠陥の絵

# ロット全体をゴールデン比較 → 欠陥品と大ずれ品だけ ng → レポート
res = fs.inspect_batch("lot_0002/", None, measure=fs.golden_measure(golden, threshold=0.2, max_shift=3),
                       spec=fs.golden_spec(max_defect_area=0, max_shift=3),
                       report_path="lot_0002.xlsx", title="Lot 0002")
print(res["summary"])
```

## 裏づけ

- 実装: `fullseye/golden.py`(`compare_to_golden` / `golden_measure` / `golden_spec`。並進 = `filters_freq.phase_correlation_fft`、類似 = `imgmetrics.ssim` / `psnr`、連結成分 = `scipy.ndimage.label`。新アルゴリズム無し)
- 例: [`golden_compare`](../../examples/golden_compare.py)(同一 / 3 px ずれ / 異物 48 px / 6 px 大ずれ / 6 枚のロットで 2 枚だけ ng、すべて assert)
- 試験: `tests/test_golden.py`(同一→欠陥 0・SSIM 1 / 並進を合わせれば欠陥 0 / 異物の個数と面積 / mask と min_area / max_shift 超えは合わせず ng / blur で 1 px の縁ずれ抑制 / 形違い・NaN・3-D・空・mask 違い・min_area 0 は ValueError / inspect_batch 連携)
- 来歴: 位相相関は Kuglin & Hines (1975)(既存 `phase_correlation_fft`)、SSIM は Wang et al. (2004)(既存 `imgmetrics`)。`docs/REFERENCES.md` の `compare_to_golden` 行に記載。判定語彙は能力ノート `inspection-workflow` と共通。
