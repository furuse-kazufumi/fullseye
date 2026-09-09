---
op: central_moments
dim: 3d
category: moment_invariant
in: points
out: table
examples: [moment_invariants]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# central_moments — 3D `moment_invariant` op

- **データ種**: `points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.central_moments(points, max_order: 'int' = 3) -> 'dict'` (実装を直接呼ぶなら `import moments3d; moments3d.central_moments(points, max_order: 'int' = 3) -> 'dict'`、台帳から引くなら `ops3d.get("central_moments")`)

## 使い方

重心中心化した中心モーメント μ_{pqr}(並進不変、キー=(p,q,r))を返す。

μ_{pqr} = mean( (x-x̄)^p (y-ȳ)^q (z-z̄)^r )。p+q+r <= max_order の全次数を含む。
重心を引いてから計算するので平行移動に厳密に不変。等質量規約なので
μ_{000}=1、1 次モーメント μ_{100}=μ_{010}=μ_{001}=0(中心化の帰結)。

Parameters
----------
points : array_like, shape (N, 3)
    点群。
max_order : int
    含める最大次数 p+q+r(既定 3)。0 以上。

Returns
-------
dict[tuple[int, int, int], float]
    (p, q, r) -> μ_{pqr}。

補足:
- 返る dict のキー数は p+q+r <= max_order の全組合せ(``max_order=3`` で 20 個)。値は float(平均なので点数で割ってある)。
- 単位は長さ^(p+q+r)。並進不変だが回転・スケールには不変でない(回転不変量は ``moment_invariants`` / ``principal_moments``)。
- 2 次モーメント ``(2,0,0)``, ``(1,1,0)`` などは母共分散(N で割る)そのもので、``inertia_tensor`` の素材と同じ。
- 高次は重心から遠い点が支配するので外れ値に弱い。前段で ``statistical_outlier_removal`` などを検討する。
- 入力は (N,3)、N >= 1。``max_order < 0``、形状不正、非有限は ``ValueError``。決定論的。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [moment_invariants](../../../../examples_3d/moment_invariants.py) — `py -3.11 examples_3d/moment_invariants.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`moment_invariant`)

[moment_invariants](moment_invariants.md) · [principal_moments](principal_moments.md) · [inertia_tensor](inertia_tensor.md)

---
*Provenance: moments3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
