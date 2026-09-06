---
op: profile_params
dim: roughness
category: measure
in: signal
out: table
examples: [poc_surface_roughness]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# profile_params — ROUGHNESS `measure` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import roughness; roughness.profile_params(p, dx=1.0, n_sampling=5)` (または `opsroughness.get("profile_params")`)

## 使い方

断面の粗さパラメータ Ra/Rq/Rz/Rt/Rp/Rv/Rsk/Rku(ISO 4287)。

引数
  p           帯域処理済みの断面(1 次元)。
  dx          標本間隔。パラメータ自体には効かないが ``sampling_length`` の
              報告に要る(単位を持たせないと Rz の条件が書けない)。
  n_sampling  基準長さの分割数。ISO 4287 の既定は 5。

★ Rz と Rt を**両方**返す —— 定義差をここで消す
  ISO 4287 の Rz は「評価長さを ``n_sampling`` 等分し、各区間の
  最大山高さ + 最大谷深さを平均したもの」。一方 Rt は評価長さ全体の
  最大高低差。同じ断面でも値が違い、しかも文献や装置によって
  「Rz」がどちらを指すか揺れる。**両方返せば取り違えようがない。**

  実測(512 点、λc=80 µm で切った断面。深い傷を 1 本含む行を選んだ):

      Rz(5 区間の平均)    1.5076
      Rz_max(区間の最大)  5.4706
      Rt(評価長さ全体)    5.4706
      Rt / Rz               3.63

  傷が 1 区間にしか無いので、5 区間の平均が傷の寄与を 1/5 に薄める。
  **同じ断面で 3.6 倍違う数字が、どちらも「Rz」と呼ばれている。**
  同じ行から傷だけ抜くと Rt/Rz = 1.21 まで下がる ——
  **差が開くのは孤立した特徴があるときだけ**なので、
  「うちの装置では一致するから同じ」は反例に当たっていないだけ。

★ 落とし穴 —— 断面 1 本の Rz は面の Sz を代表しない
  加工目が行方向に走る面(512x512、深い傷 4 本、λc=80 µm)で、断面を
  171 本ずつ取った実測:

    * 目に**直交**する列方向の Rq は、平行な行方向の **2.67 倍**
      (0.1853 対 0.0694)。同じ表面・同じ装置で、向きが違うだけ。
    * 行方向の Rt は最小 0.2765 / 最大 5.4706 で **19.8 倍**ばらつく。
    * 面の Sz(5.9694)の 8 割に届く断面は **171 本中 6 本**(3.5 %)。

  Rq は数本で足りるが Rz は足りない —— **同じ 1 次元断面でも、
  パラメータごとに必要な本数が違う。** Rz を報告するなら本数と向きを
  必ず添えること。

定義の細部(規格からの逸脱をここに明示する)
  * 基準線は評価長さ全体の平均線(最小二乗直線ではない)。傾きは
    `surface_form_remove` か `surface_filter` で先に除いておくこと。
  * Rp / Rv / Rsk / Rku は評価長さ全体で計算する(区間平均ではない)。
  * 評価長さが ``n_sampling`` で割り切れないときは余りを捨てる。捨てた
    点数は ``dropped_samples`` で返す。

fail-closed
  * 1 次元でない / 8 点未満 / NaN・Inf を含む。
  * ``n_sampling`` が 1 未満、または区間あたり 4 点未満になる。
  * 断面が完全に平坦(Rq=0)。

## 詳しい使い方ガイド

- [surface_roughness ファミリ ガイド](../guides/surface_roughness.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_surface_roughness](../../../../examples/poc_surface_roughness.py) — `py -3.11 examples/poc_surface_roughness.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`measure`)

[surface_params](surface_params.md) · [surface_psd](surface_psd.md)

---
*Provenance: roughness.py — ROUGHNESS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
