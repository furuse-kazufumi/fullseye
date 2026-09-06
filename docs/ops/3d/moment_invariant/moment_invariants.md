---
op: moment_invariants
dim: 3d
category: moment_invariant
in: points
out: descriptor
examples: [moment_invariants]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# moment_invariants — 3D `moment_invariant` op

- **データ種**: `points` → `descriptor`
- **呼び出し**: `import moments3d; moments3d.moment_invariants(points) -> 'np.ndarray'` (または `ops3d.get("moment_invariants")`)

## 使い方

並進+回転+スケール不変な形状特徴ベクトル(Sadjadi–Hall 流 + 高次半径分布)。

処方:
    1. 重心中心化(並進を除去)。
    2. RMS 半径 R = sqrt(mean‖p-c‖²) で割ってスケール正規化(R→1)。
       これで正規化後の中心 2 次モーメントは一様スケール s に依らない。
    3. 正規化共分散 C̃ の主不変量(特性多項式の係数)を並べる:
         λ̂1 >= λ̂2 >= λ̂3   … C̃ の固有値(= 正規化した主 2 次モーメント、
                                Σλ̂ = 1、回転不変)
         J2 = λ̂1λ̂2 + λ̂1λ̂3 + λ̂2λ̂3   (Sadjadi–Hall 第 2 不変量 = 2×2 主小行列和)
         J3 = λ̂1λ̂2λ̂3               (第 3 不変量 = det C̃)
    4. 正規化 4 次半径モーメント m4 = mean(‖p̂-c‖⁴)(= mean(r⁴)/mean(r²)²)。
       r = 重心からの距離なので回転+並進不変、RMS 正規化済でスケール不変。

返すベクトルは [λ̂1, λ̂2, λ̂3, J2, J3, m4] (長さ 6)。
第 1 不変量 J1 = Σλ̂ は正規化で常に 1 になり識別に寄与しないため省く。
J2,J3 は固有値の対称式(冗長)だが、Sadjadi–Hall の代数不変量シグネチャとの
互換のため併記する。

識別性の内訳(honest):
    - λ̂1,λ̂2,λ̂3(と対称式 J2,J3)は **2 次モーメント(共分散固有値)のみ** に
      由来し、独立自由度は主軸アスペクト比の 2 つだけ。これだけでは 2 次が
      等方な形状(solid cube と solid sphere は共に λ̂≈(1/3,1/3,1/3))を区別
      できない。
    - m4 は **半径分布の 4 次モーメント** で、2 次では潰れる高次の形状差を
      捉える。一様 solid sphere は m4=75/63≈1.190、一様 solid cube は
      m4=19/15≈1.267 と異なるため、両者を分離できる。
球なら概ね (1/3, 1/3, 1/3, 1/3, 1/27, 1.190)、
細長い棒なら (≈1, ≈0, ≈0, ≈0, ≈0, 大) に近づく。

Returns
-------
np.ndarray, shape (6,)
    並進・回転・スケール不変な特徴ベクトル。

補足:
- 入力は (N,3)、N >= 2。形状不正・非有限・全点一致(中心化後の広がりが 0)は ``ValueError``。縮退判定はスケール相対(``rms <= 1e-12 × max|centered|``)なので、座標が極小なだけの点群は弾かない。
- 返り値は float64 (6,)。``λ̂`` は 0 でクリップ済み、``Σλ̂ = 1``。
- 不変なのは並進・回転・一様スケールのみ。鏡映(反転)にも不変(固有値と半径分布は反転で変わらない)ので鏡像体は区別できない。非一様スケールや点密度の偏り(サンプリングの粗密)は値を変える。
- 点密度に敏感な用途では前段で ``voxel_grid_downsample`` で密度を均す。比較は ``shape_distance``(台帳 op、同じ長さの記述子ベクトル同士の距離)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [moment_invariants](../../../../examples_3d/moment_invariants.py) — `py -3.11 examples_3d/moment_invariants.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`moment_invariant`)

[principal_moments](principal_moments.md) · [central_moments](central_moments.md) · [inertia_tensor](inertia_tensor.md)

---
*Provenance: moments3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
