---
op: read_barcode1d
dim: symbol
category: barcode1d
in: image2d
out: table
gpu: なし
examples: [poc_symbol_package_1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# read_barcode1d — SYMBOL `barcode1d` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.read_barcode1d(image, symbologies=None, *, angle_deg=None, n_lines=10, itf_min_length=6, min_agree=2)` (実装を直接呼ぶなら `import barcode1d; barcode1d.read_barcode1d(image, symbologies=None, *, angle_deg=None, n_lines=10, itf_min_length=6, min_agree=2)`、台帳から引くなら `opssymbol.get("read_barcode1d")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

画像から 1 次元バーコードを読む(``table``)。

Read a 1-D symbol from a 2-D reflectance image at any in-plane angle: sample
``n_lines`` scan lines across the bars (:func:`barcode_scan_profiles`), decode each
(:func:`decode_barcode_profile`) and take the majority text. Returns ``text``,
``symbology``, ``n_lines``, ``n_decoded`` (lines that decoded), ``n_agree`` (lines
agreeing with the majority), ``votes`` (text -> count), ``line_results`` (one dict
or None per line), ``angle_deg``, ``x_dim_px``.

★2 本以上の走査線が**違う**文字列で復号したときは多数決の結果に ``conflict = True``
を立てる(誤読の兆候。検査では読み取り不能と同じに扱うべき)。多数の文字列に同意した
走査線が ``min_agree``(既定 2)本に満たなければ読み取り不能とする —— 1 本だけの
偶然の一致(ぼけた断片が検査数字を通る)を返さない。
Two or more lines decoding to different strings sets ``conflict = True``; fewer than
``min_agree`` lines agreeing on the majority text is a no-read.

向きを与えないときは 2 回読む: 構造テンソルの向きで 1 回、多数の文字列を読んだ走査線の
最初のバーの縁(バーに平行な直線に乗る)から当て直した向きでもう 1 回(多数の票が減らない
ときだけ採る)。With ``angle_deg=None`` the scan direction is refined from the leading
edges of the majority lines and the symbol is read again.

空の入力は ``ValueError``。
拒否(``ValueError``): 2-D でない、非有限、未知の体系名。1 本も読めなければ
:class:`Barcode1DError`。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_package_1d](../../../../examples/poc_symbol_package_1d.py) — `py -3.11 examples/poc_symbol_package_1d.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](../read_pod/symbol_read_trials.md) · [symbol_read_pod](../read_pod/symbol_read_pod.md) · [ocr_classify](../ocr/ocr_classify.md) · [ocr_read_line](../ocr/ocr_read_line.md) · [ocr_read_trials](../ocr/ocr_read_trials.md)

## 同カテゴリ(`barcode1d`)

[encode_barcode1d](encode_barcode1d.md) · [ean_check_digit](ean_check_digit.md) · [barcode_scan_profiles](barcode_scan_profiles.md) · [decode_barcode_profile](decode_barcode_profile.md)

---
*Provenance: barcode1d.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
