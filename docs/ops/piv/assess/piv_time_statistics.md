---
op: piv_time_statistics
dim: piv
category: assess
in: images
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# piv_time_statistics — PIV `assess` op

- **データ種**: `images` → `table`
- **呼び出し**: `import pivops; pivops.piv_time_statistics(images, window=32, overlap=0.5, **kw)` (または `opspiv.get("piv_time_statistics")`)

## 使い方

画像列 → 時間平均・変動の RMS・レイノルズ応力。

連続する対ごとに変位を測り、時間方向の統計を取る。乱流の記述はこの 3 つが
出発点で、``u'v'`` の符号と大きさが運動量輸送そのものになる。

**1 対だけでは意味が無い**(変動が定義できない)ので 3 枚以上を要求する。

Args:
    images: 3 枚以上の画像列。
    window / overlap / kw: :func:`piv_cross_correlate` へ渡す。
Returns:
    dict: ``mean``(``(2, h, w)``)、``rms``(同)、``reynolds``
    (``<u'v'>``、``(h, w)``)、``turbulence_intensity``、``n_pairs``、
    ``rows`` / ``cols`` / ``step``。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`assess`)

[piv_sample_at_windows](piv_sample_at_windows.md) · [piv_error_stats](piv_error_stats.md) · [piv_peak_locking](piv_peak_locking.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
