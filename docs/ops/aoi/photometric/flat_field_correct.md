---
op: flat_field_correct
dim: aoi
category: photometric
in: image2d × image2d
out: image2d
gpu: なし
examples: [aoi_frontend_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# flat_field_correct — AOI `photometric` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.flat_field_correct(image, flat, dark=None, target=None, min_response=None, clip=True)` (実装を直接呼ぶなら `import aoi; aoi.flat_field_correct(image, flat, dark=None, target=None, min_response=None, clip=True)`、台帳から引くなら `opsaoi.get("flat_field_correct")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

照明ムラとセンサ感度のばらつきを、暗電流つきの割り算で戻す。→ 補正済み画像。

検査画像 ``I``、フラット画像(一様な面を撮ったもの)``F``、暗画像(遮光して撮ったもの)
``D`` から::

    out = (I - D) / (F - D) * target

``target`` の既定は ``mean(F - D)``。このとき返る絵は **``真の反射率 x mean(F - D)``**
に厳密に等しい(実測の差 8.3e-17)。``target=1.0`` を渡せば反射率そのものへ戻る。

★**「入力の明るさが保たれる」とは書かない。** 既定で保たれるのは*尺度*であって平均では
ない —— 被写体と感度分布に相関があると平均はずれる。実測(下と同じ合成系):
``mean(raw - dark) = 0.109256`` に対し ``mean(out) = 0.099548`` で **8.9 % 低い**。
暗いところほど感度も低い、というありふれた配置でこうなる。

**暗電流を無視すると戻らない。** ``D`` を省くと ``D = 0`` として扱うが、実際に暗電流が
ある系ではそれは誤りで、補正後も勾配が残る。実測(cos⁴ 型のビネットで隅の感度が中心の
0.196 倍、暗電流 0.05、``target=1.0``):

===========================  =====================  ======================
量                            dark を渡す            dark を省く
===========================  =====================  ======================
真値との最大相対誤差            **1.755e-16**          **2.252e-01**
隅 / 中心の明るさの比           0.1209(真値と一致)     0.4867(真値 0.1209)
===========================  =====================  ======================

誤差の比は **1.3e+15 倍**。しかも省いた側も絵としては破綻せず「それらしく」出る ——
隅が明るいまま残るだけなので、**目では合格に見えて数字だけが狂う**。この 2 行は
``tests/test_aoi.py::test_flat_field_without_dark_does_not_recover`` が固定しており、
式が本当に ``D`` を使っている証拠でもある。

参考: 引き算で照明ムラを取る ``background_flatten``(低次曲面の当てはめ)を同じ絵に
当てると、隅 / 中心の比は **0.6436**(真値 0.1209)にしかならない。掛け算で効く感度
ムラは、引き算では戻らない。

**ゼロ割りは黙って通さない(既定は fail-closed)。** ``F - D`` に 0 以下の画素があると
``ValueError`` を送出する。「そこは応答が無い画素」だと分かっていて先へ進めたいときだけ、
``min_response`` に**明示の下限**(正の実数)を与える —— そのとき応答はその値で下から
抑えられ、割り算は有限に保たれる。既定で下限を置かないのは、下限を既定にすると
「死んだ画素の上に、それらしい値が生える」ことが黙って起きるため。

Args:
    image: 検査画像 ``(H, W)``。
    flat: フラット画像 ``(H, W)``。``image`` と同じ形。
    dark: 暗画像 ``(H, W)``、一様な暗電流を表す実数 1 つ、または ``None``
        (= 暗電流 0 として扱う。**その仮定が誤りなら補正は戻らない** —— 下の門を参照)。
    target: 補正後の基準レベル。``None`` なら ``mean(flat - dark)``。
    min_response: ``flat - dark`` の下限(正)。``None`` なら 0 以下を拒否する。
    clip: ``True``(既定)なら結果を ``[0, 1]``(この library の画像の約束)へ丸める。
        **飽和はここで起きる**ので、生の値が要るなら ``False`` にする。

Returns:
    ``(H, W)`` float64。``clip=True`` なら値域は ``[0, 1]``、``clip=False`` なら
    入力しだいで 1 を超えうる。dtype はどちらでも float64。

Raises:
    ValueError: 形が違う / 2-D でない / 非有限 / ``flat - dark`` が 0 以下
        (``min_response`` 未指定時)/ ``min_response`` や ``target`` が正の有限でない。

## 詳しい使い方ガイド

- [aoi_frontend ファミリ ガイド](../guides/aoi_frontend.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [aoi_frontend_tour](../../../../examples/aoi_frontend_tour.py) — `py -3.11 examples/aoi_frontend_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[register_image](../geometric/register_image.md) · [tiled_map](../aggregate/tiled_map.md)

## 同カテゴリ(`photometric`)

—

---
*Provenance: aoi.py — AOI operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
