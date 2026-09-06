---
op: surface_synth_psd
dim: roughness
category: synth
in: 
out: depth
examples: [poc_surface_roughness]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# surface_synth_psd — ROUGHNESS `synth` op

- **データ種**: `なし` → `depth`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import roughness; roughness.surface_synth_psd(n, dx, hurst, lambda_lo, lambda_hi, sq, seed=0)` (または `opsroughness.get("surface_synth_psd")`)

## 使い方

指定した PSD から高さ場を合成する。``(z, sq_analytic)`` を返す。

帯域 ``lambda_lo <= λ <= lambda_hi`` の各モードに振幅
``A(q) ∝ q^-(H+1)``(= 面 PSD ``C(q) ∝ q^-2(H+1)``、自己アフィン)を置き、
**位相だけ**乱数にする。全体を ``sq`` に規格化して返す。

引数
  n           格子の大きさ。整数なら ``n x n``、``(ny, nx)`` でも可。
  dx          標本間隔(正方画素)。
  hurst       Hurst 指数 H(0 < H < 1)。大きいほど滑らか。
  lambda_lo   帯域の**短い**側の波長。
  lambda_hi   帯域の**長い**側の波長。
  sq          目標 Sq(帯域内の rms 高さ)。
  seed        位相の乱数種。

★ 解析 Sq を一緒に返すのが肝
  振幅を固定して位相だけ振るので、Parseval から
  ``<h²> = (1/(ny nx))² Σ_k A_k²`` が **位相の引き方によらず**決まる。
  つまり Sq の真値が乱数に依存しない。実測: ``z.std()`` と
  ``sq_analytic`` の相対差は seed・H・帯域・寸法を振っても
  **最大 2.2e-16**(下の表)。ここを「乱数を振って rms を測る」で
  済ませると、真値そのものが実現ごとにばらついて後段の誤差と混ざる。

      n     H     λ帯域        sq      |std/analytic-1|   尖度   PTV/rms
      128  0.30    4-32     0.5000       2.2e-16         3.084    7.97
      256  0.50    4-64     0.0800       0.0e+00         3.005    7.85
      256  0.80    2-64     0.0800       2.2e-16         2.893    6.92
      512  0.80    2-64     0.0800       0.0e+00         3.113    8.25
      512  0.95   8-256     2.0000       0.0e+00         2.542    5.69

★ PoC が踏んだ落とし穴を実装側に閉じ込めてある
  係数をエルミートにするために位相を ``phi = (u - u[-k]) / 2`` で
  反対称化すると、**確かに反対称にはなるが位相が一様でなくなる**
  (三角分布になって 0 の近くに寄る)。すると全モードが原点で同位相に
  足され、高さ場に 1 本のスパイクが立つ。同じ種・同じ帯域で測った実測
  (512², H=0.8, 帯域 2-64):

      位相の作り方                 PTV/rms    尖度    |std/analytic-1|
      (u - u[-k])/2 で反対称化      55.00     71.81       0.0e+00
      共役対の片方だけに一様乱数     8.47      2.95       0.0e+00  ← 正しい

  **どちらも Sq は解析値と厳密に一致する。** 分散だけ見ていたら
  気づけない壊れ方なので、この関数は共役対の片方だけに一様乱数を引く
  実装に固定し、テストで尖度と PTV/rms も見る。自己共役モード
  (k = -k、4 点)は係数が実でなければならないので、位相ではなく
  符号 ±1 を振る(位相 0 に固定すると全部 +A に偏るため)。

fail-closed
  * ``n`` が 8 未満 / ``dx`` が非正 / ``hurst`` が (0, 1) の外。
  * ``lambda_lo >= lambda_hi``。
  * ``lambda_lo`` が Nyquist 波長 ``2*dx`` 未満(実現できない帯域)。
  * ``lambda_hi`` が評価長さ超(1 周期も入らない)。
  * ``sq`` が非正。
  * 帯域に 1 モードも入らない(格子が粗すぎる / 帯域が狭すぎる)。

## 詳しい使い方ガイド

- [surface_roughness ファミリ ガイド](../guides/surface_roughness.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_surface_roughness](../../../../examples/poc_surface_roughness.py) — `py -3.11 examples/poc_surface_roughness.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[surface_form_remove](../prepare/surface_form_remove.md) · [surface_filter](../prepare/surface_filter.md) · [surface_params](../measure/surface_params.md) · [surface_psd](../measure/surface_psd.md)

## 同カテゴリ(`synth`)

—

---
*Provenance: roughness.py — ROUGHNESS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
