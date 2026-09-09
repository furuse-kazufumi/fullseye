---
op: surface_psd
dim: roughness
category: measure
in: depth
out: pairs
examples: [poc_surface_roughness]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# surface_psd — ROUGHNESS `measure` op

- **データ種**: `depth` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.surface_psd(z, dx, kind='areal', dy=None)` (実装を直接呼ぶなら `import roughness; roughness.surface_psd(z, dx, kind='areal', dy=None)`、台帳から引くなら `opsroughness.get("surface_psd")`)
- **台帳経由の戻り値**: `fullseye.ledger.surface_psd(...)` は**宣言 out 型 `pairs` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.surface_psd.raw(...)`、または `roughness.surface_psd` を直接呼ぶ。
  - 本体の返り: `(q, C) -> (N,2)`

## 使い方

高さ場のパワースペクトル密度。``(q, C)`` を返す。**規約を引数で明示する。**

引数
  z       高さ場(平均は内部で引く。DC ビンは返さない)。
  dx, dy  標本間隔。``dy=None`` は正方画素。
  kind    ``"areal"`` … 2 次元 PSD ``C_2D(q)`` の環平均。
          ``"radial"`` … 1 次元動径 PSD ``C_1D(q) = 2π q C_2D(q)``。

規約(ここを書かないと較正なしでは読めない ―― 既存の
`radial_power_spectrum` はこれが docstring に無い)
  * ``q`` は **cycles / length**(角周波数 ``2π/λ`` ではない)。``q = 1/λ``。
  * ``C_2D(q) = dx dy |F|² / (ny nx)``。規格化は Parseval に合わせてある:
    ``∫ C_2D d²q = <h²>`` かつ ``∫ C_1D dq = <h²>``。
  * 自己アフィン面 ``H`` に対する傾きは **面 PSD で ``-2(H+1)``、
    動径 PSD で ``-2H-1``**(ちょうど 1 だけ違う)。

★ 実測 —— どちらの規約でも H は較正なしで戻る
  `surface_synth_psd` で H を仕込み、q ∈ [2/λ_hi, 0.4/dx] で対数対数の
  直線を当てはめて H を戻した(512², 帯域 2-64 µm):

      仕込んだ H   面 PSD の傾き   戻した H   動径の傾き   戻した H   傾き差
         0.30        -2.600        0.300      -1.600       0.300     1.0000
         0.50        -3.000        0.500      -2.000       0.500     1.0000
         0.80        -3.600        0.800      -2.600       0.800     1.0000
         0.95        -3.901        0.950      -2.901       0.950     1.0000

  誤差は 4 例とも **±0.0003 以内**、二つの規約の傾き差はどの H でも
  厳密に 1.0000。**較正なしで読める。**

  ★ ここは PoC の測り直しで結論が変わった箇所。PoC は既存
  `radial_power_spectrum` で **一律 -0.013(H の 1.6 %)の系統誤差**を
  見つけ、「環平均の離散化による系統誤差」と結論した。同じ検算をこの
  実装でやると誤差が消える。原因を切り分けたところ、**環の代表 ``q`` に
  ビン番号 ``i·Δq`` を使うか、環内の ``q`` の平均を使うかの差**だった
  —— ビン番号だと -0.0007〜-0.0010 の負のずれが出る(実測、同じ面・同じ
  当てはめ帯域)。向きは PoC の観測と同じだが大きさは 1/15 なので、
  -0.013 の残りは環平均の離散化ではなく、その関数の他の実装差に由来する。
  **この関数は環内の ``q`` の平均を返す。**

★ 落とし穴 —— Nyquist を超える環は「角だけ」で出来ている
  正方格子の最大 ``|q|`` は ``√2/(2 dx)`` だが、``q > 1/(2 dx)`` の環は
  周波数平面の四隅しか含まない。実測(512²): 全 362 ビンのうち上位
  107 ビン(29.6 %)が Nyquist 超。環内の点数が理想値 ``2πq/Δq`` に対して
  どれだけ欠けるかは、Nyquist 以下でも最小 0.838 倍まで落ちる
  (格子の離散化)が、Nyquist 超では 0 まで落ちる。
  **傾きの当てはめには Nyquist 超を使わないこと。**

★ Parseval の検算をどこまで信じてよいか(実測、512²、Sq²=6.400e-03)
  * 2 次元の全格子で ``Σ C_2D Δqx Δqy`` を取ると **+0.0000 %**(厳密)。
  * 返した動径 PSD を台形積分すると **-0.55 %**。環ごとに平均して
    1 次元に潰した時点でこの分は失われる —— **環平均は要約であって
    可逆ではない。** 0.5 % を超える精度が要る用途では 2 次元の
    ``C_2D`` を自分で積分すること。
  * この面は帯域上端が Nyquist なので、Nyquist で打ち切っても -0.55 %
    のまま変わらない(角の分に中身が無い)。角に中身がある面
    (帯域が Nyquist を超える面)では、打ち切ると欠ける。

fail-closed
  * 2 次元でない / 8x8 未満 / NaN・Inf を含む / ``dx``, ``dy`` が非正。
  * ``kind`` が ``"areal"``・``"radial"`` 以外。

## 詳しい使い方ガイド

- [surface_roughness ファミリ ガイド](../guides/surface_roughness.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_surface_roughness](../../../../examples/poc_surface_roughness.py) — `py -3.11 examples/poc_surface_roughness.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

—

## 同カテゴリ(`measure`)

[surface_params](surface_params.md) · [profile_params](profile_params.md)

---
*Provenance: roughness.py — ROUGHNESS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
