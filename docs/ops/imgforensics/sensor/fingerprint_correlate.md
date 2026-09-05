---
op: fingerprint_correlate
dim: imgforensics
category: sensor
in: image2d × fingerprint
out: table
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# fingerprint_correlate — IMGFORENSICS `sensor` op

- **データ種**: `image2d × fingerprint` → `table`
- **呼び出し**: `import imgforensics; imgforensics.fingerprint_correlate(image, fingerprint, denoiser: 'str' = 'wiener', sigma: 'float' = 0.02, exclude: 'int' = 11) -> 'dict'` (または `opsimgforensics.get("fingerprint_correlate")`)

## 使い方

1 枚の画像を指紋に照合する。**判定は返さない** —— 証拠量と注意書きを返す。

残差 ``W = I - denoise(I)`` と参照信号 ``I·K`` の巡回相互相関を FFT で取り、
正規化相互相関のピークと **PCE**(peak-to-correlation energy)を返す。

返り(``table`` 語彙の dict):

``pce``          PCE。**しきい値は同梱しない**(下の caveats 参照)
``ncc_peak``     正規化相互相関のピーク値([-1, 1])
``peak_shift``   ピークの位置 ``(dy, dx)``。**(0, 0) でなければ位置がずれている**
                 = 切り出し / 手ぶれ補正 / リサイズを疑う手がかり
``n_pixels``     使った画素数
``caveats``      この数値が言えないことの列(文字列)

``peak_shift`` を返すのは重要で、``(0, 0)`` 以外のピークは「同じセンサだが
切り出されている」か「**たまたまの相関**」のどちらかである。どちらかは
この op には決められない。実測では別センサの照合はいつも ``(0, 0)`` 以外に
ピークが立ち(``(-51, -60)`` ``(31, -8)`` など毎回ばらばら)、同一センサは
必ず ``(0, 0)`` に立つ。

**再圧縮で PRNU は消える**(``tests/test_imgforensics.py::test_prnu_dies_under_recompression``、
8 枚から作った指紋・128x128):

========== ========== ==========
再圧縮      PCE        無圧縮比
========== ========== ==========
無圧縮     7246       1.00
品質 95    6174       0.85
品質 90    4214       0.58
品質 75    1412       0.19
品質 50     530       0.07
品質 30     207       0.03
========== ========== ==========

つまり **低い PCE は「別のカメラ」ではなく「情報が残っていない」かもしれない**。
ここでしきい値を同梱すると、圧縮された画像を機械的に「別カメラ」と判定する
道具になってしまう。

**黙って間違う経路(実測)**: ``fingerprint`` に指紋ではなく普通の画像を渡すと、
shape は合っているので例外は出ず、PCE も有限値が返る。指紋は ``(H, W)`` の
float64 なので既存の ``image2d`` 述語を完全に満たし、**実行時には区別できない**。
そこで入口で「ゼロ平均でない」ものを :class:`ValueError` で弾く
(``|mean| > 0.05 * std``)。実測
(``tests/test_imgforensics.py::test_fingerprint_gate_rejects_plain_images``):

============================== ==============
渡したもの                     ``|mean|/std``
============================== ==============
:func:`sensor_fingerprint` の返り 4.8e-18
普通の自然画像                 4.626
暗い画像(平均 0.015)         4.626
高コントラスト画像             1.801
============================== ==============

比は**スケール不変**なので、暗い画像でも明るい画像でも同じように弾ける
(0.05 のしきい値から 1.5 桁以上離れている)。

**それでも完全ではない**: 自分でゼロ平均化した画像を渡すとゲートは通り、
PCE = -5.97 という有限値が返る(実測)。つまり実行時チェックは
**片側しか守れない**。これが「指紋を ``image2d`` に相乗りさせず語彙を分ける」
判断の根拠で、詳細は ``opsimgforensics`` の docstring にある。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`table` を入力に取れる)

[evidence_quantile](../calibration/evidence_quantile.md)

## 同カテゴリ(`sensor`)

[sensor_fingerprint](sensor_fingerprint.md) · [fingerprint_strength_map](fingerprint_strength_map.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
