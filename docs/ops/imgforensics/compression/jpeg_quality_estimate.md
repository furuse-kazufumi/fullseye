---
op: jpeg_quality_estimate
dim: imgforensics
category: compression
in: image2d
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# jpeg_quality_estimate — IMGFORENSICS `compression` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import imgforensics; imgforensics.jpeg_quality_estimate(image, max_step: 'int' = 64, n_coeff: 'int' = 21) -> 'dict'` (または `opsimgforensics.get("jpeg_quality_estimate")`)

## 使い方

デコード済み画像から **量子化表と JPEG 品質をブラインド推定**する。``table``。

ファイルの DQT を読むのではなく、**画素だけ**から推定する(そこが要点で、
PNG に保存し直された / 貼り付けられた画像でも「元は JPEG 品質 N だった」が
見える)。8x8 ブロック DCT を取り、係数ごとに櫛の間隔を推定して
(Fan & de Queiroz 2003)、IJG の公開スケーリング規則で作った標準表の族から
最も合う品質を選ぶ。

返り(dict):

``jpeg_compressed`` 櫛が立った係数が ``n_coeff`` 個中いくつあったかで判断した
                    bool。**「JPEG である」証明ではない**(下記 caveats)
``quality``         推定品質 1..100(櫛が無ければ ``None``)
``table``           推定した ``(8, 8)`` の量子化ステップ(0 = 推定できず)
``n_quantized``     櫛が立った係数の数 / ``n_coeff``
``fit_error``       選ばれた品質の標準表との平均絶対差
``caveats``         この数値が言えないこと

実測(``tests/test_imgforensics.py::test_jpeg_quality_estimate_recovers_quality``、
256x256 の 1/f^1.6 画像を Pillow で符号化 → 復号して推定):

======= ========= =============== ============
真の Q  推定 Q    櫛が立った係数  fit_error
======= ========= =============== ============
95      95        11/20           0.091
90      90        19/20           0.579
80      80        13/20           1.308
70      **71**    12/20           2.083
60      60         9/20           2.111
50      **52**     7/20           1.857
40      40         6/20           3.333
30      **None**   4/20           —
======= ========= =============== ============

**低品質側で崩れるのは原理的な限界**である。品質が下がるほど高周波係数は 0 に
量子化され、櫛を読む材料そのものが画像から消える(「櫛が立った係数」の列が
その消え方)。品質 30 では材料が足りず、**推定を返さない**(``quality=None``)。
ここで無理に答えを出さないのがこの op の設計方針である。

そして **無圧縮 PNG では ``jpeg_compressed=False`` / ``quality=None``**
(4 つの seed で確認、同テストで固定)。ここで黙って「品質 100」と答えないことが
肝で、そうすると「無圧縮」と「ほぼ無劣化の JPEG」が同じ答えになる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[evidence_quantile](../calibration/evidence_quantile.md)

## 同カテゴリ(`compression`)

[error_level_map](error_level_map.md) · [jpeg_ghost_map](jpeg_ghost_map.md) · [jpeg_ghost_quality](jpeg_ghost_quality.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
