---
op: contour_fourier_truncation_energy
dim: shape2d
category: descriptor
in: matrix
out: table
examples: [poc_one_stroke_epicycles]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# contour_fourier_truncation_energy — SHAPE2D `descriptor` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.contour_fourier_truncation_energy(spectrum, orders=None)` (実装を直接呼ぶなら `import fourierdesc; fourierdesc.contour_fourier_truncation_energy(spectrum, orders=None)`、台帳から引くなら `opsshape2d.get("contour_fourier_truncation_energy")`)

## 使い方

打ち切り次数ごとの**予言される**誤差(``table``)—— パーセバルの厳密式。

次数 ``K`` で打ち切った再構成 ``z^K`` について、標本上の二乗平均誤差は
``mean|z - z^K|^2 = Σ_{|k| > K} |c_k|^2`` に**厳密に等しい**。だから
再構成を 1 度もせずに「何項あれば何画素まで似るか」を先に言える。

★**予言が厳密なのは、係数列が完全なときだけ**である(``contour_fourier_complex``
を ``n_harmonics=None`` で呼んだ場合)。打ち切った係数列を渡されると、
捨てられた側のエネルギーは**知りようがない**ので、返る誤差は**下界**になる
—— 過小に見える誤差を「厳密」と言わないために、ここに書いておく。

返り値: dict(``table``)
    "order": 打ち切り次数 ``K`` の 1-D
    "rms_error": 予言される rms 誤差[入力の単位]
    "energy_fraction": 残した項が担うエネルギーの割合(``0..1``、単調増加)
    "total_energy": ``Σ_{k≠0} |c_k|^2``(位置 ``c_0`` を除いた形のエネルギー)
    "k_max": スペクトルが持つ最大次数

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_one_stroke_epicycles](../../../../examples/poc_one_stroke_epicycles.py) — `py -3.11 examples/poc_one_stroke_epicycles.py`

## 型が繋がる次の op(`table` を入力に取れる)

[from_xld](from_xld.md)

## 同カテゴリ(`descriptor`)

[elliptic_fourier](elliptic_fourier.md) · [reconstruct](reconstruct.md) · [invariants](invariants.md) · [normalize](normalize.md) · [descriptor_distance](descriptor_distance.md) · [fourier_smooth](fourier_smooth.md) · [from_xld](from_xld.md) · [contour_fourier_complex](contour_fourier_complex.md)

---
*Provenance: fourierdesc.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
