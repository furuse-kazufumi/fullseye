---
op: speckle_quality
dim: piv
category: solid
in: image2d
out: table
examples: [piv_field_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# speckle_quality — PIV `solid` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import dic; dic.speckle_quality(img: 'Any') -> 'dict[str, float]'` (または `opspiv.get("speckle_quality")`)

## 使い方

撮ったスペックルが DIC に向いているかを 4 つの数字で返す。

`pivops` にも `fullseye` にも無い(``speckle_filter`` は SAR の斑点雑音
**除去**で別物)。撮影の場で「この模様で測れるか」を判定するための口。

引数
  img  スペックル画像(2 次元)。輝度の規格は問わないが、``coverage`` は
       画像内の最小・最大を基準にした相対しきい値で数える。

戻り値は ``dict``:

  ``mig``                     平均輝度勾配 ``sqrt(mean(Ix² + Iy²))``。
                              Pan らの DIC 品質指標。変位の分散の下限が
                              ``σ_noise / (mig √N)`` で決まるので、これが
                              小さいと何をしても測れない。
  ``grad_rms``                x 方向だけの ``sqrt(mean(Ix²))``。
  ``coverage``                ``0.2*(max-min) + min`` を超える画素の割合。
  ``mean_blob_diameter_px``   斑点の平均直径 [px] の**推定値**(下記)。

★ ``mean_blob_diameter_px`` は推定であって測定ではない
  平均を引いた画像の自己相関の動径平均が 0.5 に落ちる半径 ``R½`` を線形
  内挿で求め、``diameter = √2 · R½`` を返す。``√2`` の根拠: 1σ 半径 ``r`` の
  ガウス斑点をランダムに撒いた場の自己相関は 1σ が ``r√2`` のガウスなので
  ``R½ = 2r√(ln2)``、斑点の FWHM は ``2r√(2ln2)``、比がちょうど ``√2``。
  つまり**斑点がガウスで位置が無相関という仮定の上でだけ** FWHM に一致する。

  実測(左: 解析スペックル、1σ 半径を振り被覆率が揃うよう個数を調整。
  右: `piv_synth_particles`、``diameter_px`` は 2σ なので FWHM は
  ``1.1774 × diameter_px``):

      1σ r   FWHM   推定   比   |  d_px   FWHM   推定   比    cov     mig
      0.6    1.41   1.36  0.97  |   1.5   1.77   1.80  1.02  0.043  0.1351
      1.0    2.35   2.39  1.01  |   2.5   2.94   2.93  1.00  0.106  0.1676
      1.6    3.77   3.77  1.00  |   4.0   4.71   4.69  1.00  0.159  0.1775
      2.5    5.89   5.77  0.98  |   6.0   7.06   7.01  0.99  0.286  0.1764
      4.0    9.42   9.18  0.97  |

  **ガウス斑点なら 3 % 以内**。実物のスペックル(印刷・スプレー)は
  ガウスではないので、この表は換算の算数が合っていることの確認であって、
  実写での精度ではない。**何に偏るか**:

  * 斑点の形がガウスでないと ``√2`` の換算そのものがずれる。
  * 低周波のむら(照明勾配)があると自己相関の裾が持ち上がり**過大**に出る。
    先に高域通過を掛けること。
  * 自己相関は循環相関(FFT)なので、周期性のある背景があると乱れる。
  * 環の代表半径は**環内の半径の平均**を使う。ビン番号を使うと半径 1 の環に
    対角の √2 が混ざり、1σ=0.6 px で径が **0.80 倍**(2 割過小)に出た。

★ MIG は下限を切る指標であって、最大化する目的関数ではない
  上の左表で ``mig`` は斑点が細かいほど大きい(1σ=4.0 の 0.0384 に対し
  1σ=0.6 で 0.1127、2.9 倍)。だが直径 1.4 px のスペックルは標本化が
  足りず、`examples/poc_dic_strain.py` の 9 節の実測では偏りも散らばりも
  最悪になる。**MIG を最大化すると測れないスペックルを選ぶ。**
  右表の粒子像では ``d=4.0`` で頭打ちになり ``d=6.0`` でわずかに下がる ——
  同じ指標が入力の作り方で単調にも非単調にもなるので、
  **絶対値ではなく同じ撮り方どうしの比較に使うこと。**

★ ``coverage`` のしきい値は Otsu ではない
  ``0.2*(max-min) + min`` の固定しきい値。Otsu は 2 峰の分布を仮定するが、
  スペックルの輝度分布は斑点の重なりで単峰になることが多く、Otsu だと
  **しきい値が画像ごとに動いて比較できなくなる**。固定なら少なくとも
  同じ規格の画像どうしは比べられる。

★ MIG は単位を持つ
  「輝度 / px」。8 bit 整数のまま渡すか [0, 1] に規格化してから渡すかで
  255 倍違う。**同じ規格の画像どうしでしか比べられない。**

fail-closed
  * 2 次元でない / 8x8 未満 / NaN・Inf を含む。
  * 画像が完全に一様(``max == min``)—— 斑点が 1 つも無い。
  * 自己相関が 0.5 を切らない(視野より斑点が大きい)—— このときだけ
    ``mean_blob_diameter_px`` が ``nan``。他の 3 つは返す。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`solid`)

[strain_from_displacement](strain_from_displacement.md) · [correlation_quality](correlation_quality.md)

---
*Provenance: dic.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
