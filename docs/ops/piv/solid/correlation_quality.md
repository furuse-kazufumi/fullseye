---
op: correlation_quality
dim: piv
category: solid
in: image2d × image2d × flow2d
out: image2d
examples: [piv_field_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# correlation_quality — PIV `solid` op

- **データ種**: `image2d × image2d × flow2d` → `image2d`
- **呼び出し**: `import dic; dic.correlation_quality(ref: 'Any', cur: 'Any', flow: 'Any', info: 'Optional[dict]' = None, subset: 'int' = 31) -> 'np.ndarray'` (または `opspiv.get("correlation_quality")`)

## 使い方

与えられた変位場が**どれだけ合っているか**を点ごとに返す ZNCC マップ。

引数
  ref     基準画像。
  cur     変形後画像。``ref`` と同じ形。
  flow    `pivops` の ``flow2d`` ``(2, h, w)``、成分は ``(dy, dx)`` [px]。
          ``info`` を渡さないなら ``(2, H, W)`` の**全画素**の場。
  info    `piv_cross_correlate` が返した dict。渡すと窓格子の ``flow`` を
          画素へ双一次で広げてから測る。
  subset  相関を取る正方サブセットの一辺 [px]。**奇数**。

戻り値は入力画像と同じ形の float 配列。値は ``[-1, 1]`` の ZNCC で、
**測れなかった点は NaN**(サブセットが画像からはみ出す縁、変形後の
標本点が画像の外へ出る点、分散の無いサブセット)。

★ これは相関器ではない —— **既にある変位場の採点係**
  `piv_cross_correlate` も `optical_flow_lk` も `demons_register` も、
  出した変位が正しいかは返さない。ここは ``cur`` を ``flow`` で基準側へ
  引き戻し(双一次)、``ref`` との ZNCC を ``subset`` の箱で測るだけ。
  **どの推定器の出力でも同じ口で採点できる**のが要点で、相関器を
  もう 1 つ増やさずに品質だけを足せる。

  平均と標準偏差の両方を割り引くので、**ゲインとオフセットには不変**。
  露出が変わった対でも「合っているか」だけを見る。

★★ 既存の ``info["peak_ratio"]`` では足りない場面がある(実測)
  ``peak_ratio``(第 1 ピーク / 第 2 ピーク)は PIV の標準的な SN 比で、
  **相関面に競合する峰が立つ**種類の失敗を捕まえる。捕まえないのは
  「その場所が別物になった」種類の失敗。u=0.37 px の対のうち 60x60 画素
  だけを無関係な模様に差し替えた実測:

      指標                    差し替え領域   健全領域   区別
      peak_ratio                 1.207        1.304    7.5 % 差(重なる)
      correlation_quality        0.1101       0.9993   9 倍差

  品質で切って変位誤差 RMS がどう変わるか:

      門                  残る割合   誤差 RMS [px]
      なし                 100.0 %      1.8110
      zncc >= 0.8           84.9 %      0.0031    ← 584 倍改善
      peak_ratio >= 1.2     81.8 %      1.2183    ← 1.5 倍
      peak_ratio >= 1.3     41.6 %      1.4471    ← 6 割捨てて**悪化**

  **両方見るのが正しい。** peak_ratio は競合ピークを、ZNCC は
  デコリレーションを見る。片方だけでは穴が開く。

★★ 落とし穴 —— **品質が高いことは精度が高いことではない**
  ZNCC はサブピクセルの誤差にほとんど反応しない。真の変位 0.37 px の対に
  わざと誤差を入れた場を採点した実測(斑点の直径 3.8 px):

      変位の誤差 [px]   0.00     0.05     0.10     0.25     0.50    1.00    2.00
      zncc 中央値      0.99945  0.99920  0.99845  0.99330  0.97615 0.90617 0.67655

  **0.05 px 間違えても 0.9992** —— 完全に合っている 0.99945 との差は
  2.5e-4 しかない。この指標が測れるのは「斑点の大きさに比べて大きな
  ずれ・欠測・別物への置き換え」であって、0.01 px の精度ではない。
  一様な雑音で全点が等しく劣化した場合(σ=0.15)も、門で切って残るのは
  21.8 % で誤差 RMS は 0.1736 → 0.1292 の 1.34 倍改善にとどまる ——
  **効くのは失敗が局所的なときだけ。**

★ 引き戻しはサブセットごとの平行移動ではなく**場そのもの**
  普通の DIC はサブセットを剛体的にずらして相関を取るが、ここは画素ごとの
  ``flow`` で ``cur`` を歪めてから箱で相関を取る。``flow`` が滑らかなら
  両者は一致し、そうでないなら**こちらのほうが正しい**(サブセット内の
  変形も込みで残差を見るため)。費用も O(N) で済む(256² で 0.003 秒)。

fail-closed
  * ``ref`` / ``cur`` が 2 次元でない、形が違う、NaN・Inf を含む。
  * ``flow`` が ``(2, h, w)`` でない。
  * ``info`` 無しで ``flow`` が画像と違う形(直し方つきで拒否)。
  * ``info`` に ``rows`` / ``cols`` が無い、格子と ``flow`` の形が食い違う、
    格子がどちらかの軸で 2 未満。
  * ``subset`` が偶数・3 未満・画像より大きい。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[piv_cross_correlate](../estimate/piv_cross_correlate.md) · [piv_multipass](../estimate/piv_multipass.md) · [piv_deform_pass](../estimate/piv_deform_pass.md) · [strain_from_displacement](strain_from_displacement.md) · [speckle_quality](speckle_quality.md)

## 同カテゴリ(`solid`)

[strain_from_displacement](strain_from_displacement.md) · [speckle_quality](speckle_quality.md)

---
*Provenance: dic.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
