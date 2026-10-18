---
op: surface_filter
dim: roughness
category: prepare
in: depth
out: depth
examples: [poc_robust_profile_filter, poc_surface_roughness]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# surface_filter — ROUGHNESS `prepare` op

- **データ種**: `depth` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.surface_filter(z, dx, lambda_c=None, lambda_s=None, kind='gaussian', end_effect='reject', dy=None)` (実装を直接呼ぶなら `import roughness; roughness.surface_filter(z, dx, lambda_c=None, lambda_s=None, kind='gaussian', end_effect='reject', dy=None)`、台帳から引くなら `opsroughness.get("surface_filter")`)
- **台帳経由の戻り値**: `fullseye.ledger.surface_filter(...)` は**宣言 out 型 `depth` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.surface_filter.raw(...)`、または `roughness.surface_filter` を直接呼ぶ。
  - 本体の返り: `(roughness, waviness)`

## 使い方

高さ場を粗さとうねりに分ける(ISO 16610-21 のガウスフィルタ)。

戻り値は ``(roughness, waviness)``。``roughness`` が λc より短い成分、
``waviness`` が長い成分で、``end_effect="reject"`` でなければ
``roughness + waviness`` は入力(λs を掛けたあとの一次形状)に厳密に一致する。

引数
  z          高さ場 ``z[i, j]``(行 = y、列 = x)。
  dx, dy     標本間隔。``dy=None`` は正方画素。
  lambda_c   長波長側カットオフ(粗さ / うねりの境)。``None`` なら分けない
             (``waviness`` はゼロ配列)。
  lambda_s   短波長側カットオフ(雑音を落とす S フィルタ)。``None`` で無効。
  kind       ``"gaussian"`` のみ。他を渡すと **黙って代用せず** 例外にする。
  end_effect ``"reject"``(既定) / ``"mirror"`` / ``"wrap"``。下記。
  dy         行方向の標本間隔(``None`` = ``dx``)。

★ 端の扱い(``end_effect``)—— ここがこの op を書いた理由
  畳み込みはカーネル半径(``GAUSS_TRUNCATE·λc`` = 0.75 λc、4 σ)のぶん、端で「無い所の
  データ」を要る。規格(ISO 16610-28)は評価領域を両端から削ることを前提にする。

  * ``"reject"``(既定)—— 両端 ``ceil(0.75 λc/pitch)`` 標本を**捨てる**。
    出力は入力より小さい配列になる。捨てた領域は「測っていない」ので、
    これが唯一嘘のない選択肢。
  * ``"mirror"`` —— 鏡像で延長して同じ形を返す。端では面が偶関数だと仮定する。
  * ``"wrap"`` —— 循環畳み込み(FFT と同じ)。左端の続きが右端だと仮定する。

  **実測**(★次の表は打ち切りが ``±λc/2`` だった 2026-10-18 以前の測定。核を ``±0.75 λc`` に
  広げたあとも 1.〜3. の傾向は同じで、端の帯が 40 → 60 標本に増えるだけ。数値は測り直していない)。
  真値は 704x704 の面をフィルタしてから中央 512x512 を切り出した
  もの(端の外側に本物のデータがある状態で計算した答え)。dx=1、λc=80、
  端の帯 = 外周 40 標本、そこでの真値の rms は 0.1932。

      面の状態     end_effect   端の帯の rms 誤差    中央部の rms 誤差
      傾きあり     wrap           4.3883 (2272 %)      0.0e+00 (0.000 %)
      傾きあり     mirror         0.1765 (  91 %)      0.0e+00 (0.000 %)
      傾き除去済   wrap           0.0111 ( 5.7 %)      4.4e-15 (0.000 %)
      傾き除去済   mirror         0.0115 ( 5.9 %)      4.4e-15 (0.000 %)
      (どれでも)  reject         —— 返さない ——      0.0e+00 (0.000 %)

  読み取れること 4 つ:
    1. **端の扱いは端でしか効かない。** 中央部はどれも真値と厳密に一致する
       (カーネルが端に届かないので当然だが、確かめた)。
    2. **最悪の組み合わせは「傾きを残したまま wrap」** —— 端の誤差が
       真値そのものの 23 倍。左端の続きが右端だと仮定するので、
       高さの違う 2 辺の継ぎ目に段差が立つ。
    3. **傾きさえ除けば wrap と mirror に差は無い**(5.7 % 対 5.9 %、
       wrap がわずかに良い)。「循環畳み込みは常に悪い」ではなく
       「**傾きを除かずに使うのが悪い**」が正しい。
    4. reject の代償は面積。512x512・λc=80 で **41.4 % を捨てる**
       (392x392 が残る。打ち切りが ``±λc/2`` だった頃は 28.8 %)。捨てる割合は
       ``1 - (1 - 1.5 λc/L)²`` で増えるので、λc が評価長さの 1/6 を超えると半分近くを失う。

★ 透過率は規格どおりか(実測、λc=80、dx=1、整数周期の正弦を射影で測定。2026-10-18 に直した)

      λ         うねり側    ISO 規格値    差      (直す前のうねり側 / 差)
       16      0.000030     0.000000    +3.0e-05    0.000806 / +8.1e-04
       32      0.013094     0.013139    -4.5e-05    0.017206 / +4.1e-03
       40      0.062544     0.062500    +4.4e-05    0.058676 / -3.8e-03
       64      0.338531     0.338564    -3.3e-05    0.342826 / +4.3e-03
       80      0.500012     0.500000    +1.2e-05    0.509549 / +9.6e-03   ← λc
      128      0.762894     0.762799    +9.5e-05    0.772150 / +9.4e-03
      256      0.934601     0.934550    +5.1e-05    0.937944 / +3.4e-03

  **直す前はカットオフ波長そのもので 0.5000 でなく 0.5095**(相対 +1.9 %)だった。原因は
  定数 α(``√(ln2/π)``)でも標本化後の正規化でもなく、**規格の文面の打ち切り ``±λc/2``
  (= 2.67 σ)**。裾の 0.8 % が落ち、残りを 1 に正規化し直すので、低域の取り分が増える。
  打ち切りを ``±0.75 λc``(4 σ)にすると λc で 0.500012、全波長で最大誤差 9.5e-05 に落ちる
  (上の表)。代償は reject で捨てる端の帯が 1.5 倍になること。粗さとうねりの和は
  どちらでも入力に厳密一致する。

fail-closed
  * ``kind`` が ``"gaussian"`` 以外 / ``end_effect`` が既知の 3 つ以外。
  * ``lambda_c`` と ``lambda_s`` の両方が ``None``(何もしない呼び出し)。
  * カットオフが Nyquist 波長 ``2*pitch`` 未満、または評価長さ超。
  * ``lambda_s >= lambda_c``(帯域が空になる)。
  * ``"reject"`` で削ったあと配列が残らない。

## 詳しい使い方ガイド

- [surface_roughness ファミリ ガイド](../guides/surface_roughness.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_robust_profile_filter](../../../../examples/poc_robust_profile_filter.py) — `py -3.11 examples/poc_robust_profile_filter.py`
- [poc_surface_roughness](../../../../examples/poc_surface_roughness.py) — `py -3.11 examples/poc_surface_roughness.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[surface_form_remove](surface_form_remove.md) · [robust_gaussian_surface](robust_gaussian_surface.md) · [surface_params](../measure/surface_params.md) · [surface_psd](../measure/surface_psd.md)

## 同カテゴリ(`prepare`)

[surface_form_remove](surface_form_remove.md) · [robust_gaussian_profile](robust_gaussian_profile.md) · [robust_spline_profile](robust_spline_profile.md) · [robust_gaussian_surface](robust_gaussian_surface.md)

---
*Provenance: roughness.py — ROUGHNESS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
