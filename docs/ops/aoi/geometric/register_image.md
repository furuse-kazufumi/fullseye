---
op: register_image
dim: aoi
category: geometric
in: image2d × image2d
out: table
gpu: なし
examples: [aoi_frontend_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# register_image — AOI `geometric` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.register_image(reference, moving, upsample=20, method='phase', window='hann', max_shift=None, ambiguity_ratio=0.8, residual_tolerance=0.25)` (実装を直接呼ぶなら `import aoi; aoi.register_image(reference, moving, upsample=20, method='phase', window='hann', max_shift=None, ambiguity_ratio=0.8, residual_tolerance=0.25)`、台帳から引くなら `opsaoi.get("register_image")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

検査画像を基準画像へ合わせる平行移動を、合っていないと分かる量つきで返す。→ dict。

相関面(既定は位相相関)の山を整数画素で見つけ、その近傍を上標本 DFT で
``1/upsample`` 画素まで詰める。返りは dict 1 つで、**並進だけでなく「その答えが
どれくらい当てになるか」を必ず一緒に返す**。

符号の約束: ``moving(y, x) ≈ reference(y - dy, x - dx)``。つまり ``moving`` は
``reference`` を ``(dy, dx)`` だけずらしたもので、``moving`` を ``(-dy, -dx)`` 動かせば
重なる。``np.roll(ref, (3, 5), axis=(0, 1))`` を渡せば ``dy=3, dx=5`` が返る。

**平行移動しか扱わない。** 回転や倍率が入った対を渡しても例外は出ないが、
``residual`` が跳ね ``consistent`` が False になる。実測(128x128 の合成模様。
勾配 + 円 + 棒 + 雑音で、乱数だけの画像は対称性の破れを隠すので使わない):

=====================  ==========  ============  ========  ============
与えた変形              residual    peak_ratio    peak      consistent
=====================  ==========  ============  ========  ============
並進 (3, 5) px 整数     0.000000    0.0081        0.9698    True
並進 (2.5, -1.5) px     0.058785    0.2050        —         True
並進 (0.5, 0) px        0.038918    0.2022        —         True
回転 2 度               0.5886      0.1303        0.3200    **False**
回転 5 度               0.6555      0.4827        0.1132    **False**
倍率 1.05               0.6073      0.1687        0.2196    **False**
倍率 1.10               0.6767      0.5205        0.0968    **False**
=====================  ==========  ============  ========  ============

副画素の並進は ``upsample=20`` で**誤差 0.0000 px**(上の 2 例とも真値と一致)。
数字は ``tests/test_aoi.py`` が固定している。**黙って「いちばん近い平行移動」を
成功として返さない**ための量がこの ``residual`` で、返り値を見ずに ``dy``/``dx`` だけ
使うと回転 2 度を「ずれ 0.14 px」として飲み込む(上の表の 4 行目)。

**周期のある模様では答えが 1 つに決まらない —— そして ``peak_ratio`` はその半分しか
見ていない。** 実測(周期 8 px、``np.roll`` で (3, 5) ずらした対):

===========  =========  =========  ============  ===========  ==========
模様          dy         dx         peak_ratio    ambiguous    residual
===========  =========  =========  ============  ===========  ==========
市松 8 px    +2.950     +4.850     1.0000        **True**     0.1322
縞 8 px      +0.000     +4.900     0.1996        **False**    0.0838
===========  =========  =========  ============  ===========  ==========

市松は狙いどおり ``ambiguous=True`` になる(答えは周期 8 を法として等価なものが
並ぶので、返る値は**そのうちの 1 つ**であって間違いではないが一意でもない)。

★**縞は捕まらない、という限界を正直に書いておく。** 縞は縦方向に模様が無いので
``dy`` は原理的に決まらないのに、``ambiguous`` は False で ``dy=0.000`` が返る。
``peak_ratio`` は「離れた 2 番目の**山**」を見る量で、縞が作るのは山ではなく
**尾根**(``dy`` 方向に平らな筋)だから検出できない。しかも尾根の中から ``dy=0`` を
選んでいるのは画像ではなく **Hann 窓の包絡**で、``window="none"`` にすると別の値が
出うる。**片方向だけ模様が無い被写体(縞・織り目・筋目)では ``dy``/``dx`` の
どちらかが窓の産物になりうる**ので、そういう面を測るなら直交する模様を画面に
入れること。この限界は ``tests/test_aoi.py`` が両方向とも固定してある
(市松が True・縞が False であることを、直すまで忘れないために)。

Args:
    reference: 基準画像 ``(H, W)``。
    moving: 合わせる画像 ``(H, W)``。``reference`` と同じ形。
    upsample: 副画素の分解能の逆数(``1`` なら整数画素まで)。
    method: :data:`REGISTER_METHODS`。``"phase"`` は振幅を正規化するので明るさの
        違いに強く、``"cross"`` は素の相互相関で雑音に強い。
    window: :data:`REGISTER_WINDOWS`。
    max_shift: 探索するずれの上限[px]。``None`` なら画像の半分。
    ambiguity_ratio: ``peak_ratio`` がこれ以上なら ``ambiguous=True``。
    residual_tolerance: ``residual`` がこれ以下なら ``consistent=True``。

Returns:
    dict。``dy`` / ``dx``(px、副画素)、``peak``(正規化した山の高さ ``[0, 1]``)、
    ``peak_ratio``(第 2 の山 / 第 1 の山。1 に近いほど当てにならない)、
    ``ambiguous``(bool)、``residual``(合わせたあとの残差 rms / 基準の rms)、
    ``consistent``(bool。平行移動だけで説明できるか)、``model``(``"translation"``)、
    ``method`` / ``window`` / ``upsample``。

Raises:
    ValueError: 形が違う / 2-D でない / 非有限 / どちらかが定数画像(模様が無いので
        ずれが定義できない)/ 引数が値域外(``upsample`` が 1 未満か :data:`MAX_UPSAMPLE`
        超、``max_shift`` / ``ambiguity_ratio`` / ``residual_tolerance`` が正の有限でない)。

## 詳しい使い方ガイド

- [aoi_frontend ファミリ ガイド](../guides/aoi_frontend.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [aoi_frontend_tour](../../../../examples/aoi_frontend_tour.py) — `py -3.11 examples/aoi_frontend_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`geometric`)

—

---
*Provenance: aoi.py — AOI operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
