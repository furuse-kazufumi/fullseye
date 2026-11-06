---
op: jones_state
dim: reprconv
category: entry
in: 
out: jones
gpu: なし
examples: [type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# jones_state — REPRCONV `entry` op

- **データ種**: `なし` → `jones`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.jones_state(azimuth_deg=0.0, ellipticity_deg=0.0, amplitude=1.0)` (実装を直接呼ぶなら `import reprconv; reprconv.jones_state(azimuth_deg=0.0, ellipticity_deg=0.0, amplitude=1.0)`、台帳から引くなら `opsreprconv.get("jones_state")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

偏光の向きと楕円率 → Jones ベクトル ``jones``(Ex, Ey)。``jones`` 型の入口。

方位角 ψ = ``azimuth_deg``、楕円率角 χ = ``ellipticity_deg``(|χ| <= 45 度)で

    E = A · [cos ψ cos χ + i sin ψ sin χ,  sin ψ cos χ − i cos ψ sin χ]

を返す。``optics.stokes_from_jones`` の約束(S3 = 2 Im(Ex·conj(Ey)))のもとで
**Stokes が (A², A² cos2χ cos2ψ, A² cos2χ sin2ψ, A² sin2χ) になる**ように符号を選んである
(χ = 0 で直線偏光、χ = +45 度で S3 > 0 の円偏光 = ``[1, -i]/√2``)。
``jones_apply`` に通す入射光の状態として使う。それまで Jones ベクトルを作る op が無く、
``jones_apply`` の第 2 入力と ``stokes_from_jones`` に何も渡せなかった。

Args:
    azimuth_deg: 偏光楕円の長軸の向き [度] (+x から +y へ)。有限。
    ellipticity_deg: 楕円率角 [度]、[-45, 45]。
    amplitude: 振幅 A(>= 0、有限)。強度は A²。
Returns:
    (2,) complex128。
Raises:
    ValueError: 非有限 / ellipticity が [-45, 45] の外 / amplitude < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`jones` を入力に取れる)

—

## 同カテゴリ(`entry`)

[indices_to_positions](indices_to_positions.md) · [synapse_table_from_table](synapse_table_from_table.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
