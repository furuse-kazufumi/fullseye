---
op: tps_fit
dim: 3d
category: deform
in: points × points
out: deformation
examples: [nonrigid_deform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# tps_fit — 3D `deform` op

- **データ種**: `points × points` → `deformation`
- **呼び出し**: `import fullseye as fs; fs.ledger.tps_fit(src_ctrl, dst_ctrl, lam=0.0)` (実装を直接呼ぶなら `import deform3d; deform3d.tps_fit(src_ctrl, dst_ctrl, lam=0.0)`、台帳から引くなら `ops3d.get("tps_fit")`)

## 使い方

3D Thin-Plate-Spline を制御点対応から当てはめる。

移動側の制御点 ``src_ctrl`` を固定側 ``dst_ctrl`` へ写す TPS 係数を、鞍点系
を最小二乗(``numpy.linalg.lstsq``)で解いて求める。λ=0 なら制御点上で厳密に
内挿(``tps_warp(model, src_ctrl) == dst_ctrl``)、λ>0 で平滑化する。

引数:
    src_ctrl: (K,3) 制御点(変形の始点、TPS のカーネル中心 p_i)。
    dst_ctrl: (K,3) 対応する目標点(変形の終点 v_i)。
    lam: 正則化係数 λ≥0。カーネル行列 K の対角へ λ を加える。大きいほど
        変形は滑らか(制御点への当てはめは緩む)。

返り値:
    model: dict。キーは
        "ctrl" (K,3) カーネル中心 p_i、
        "w"    (K,3) 非線形(曲げ)係数、
        "a"    (4,3) アフィン係数([平行移動; 線形部]、a[0]=c, a[1:4]=Aᵀ)、
        "lam"  使用した λ。

例外:
    ValueError: 形状不一致、制御点数不足、非有限値、または制御点数が
        ``TPS_MAX_CTRL``(10,000)超(密な (K+4)² 系は O(K³) のため。
        対応点を間引いてから渡す — TPS は疎な制御点で滑らかな変形を
        表現するのが本来の使い方)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [nonrigid_deform](../../../../examples_3d/nonrigid_deform.py) — `py -3.11 examples_3d/nonrigid_deform.py`

## 型が繋がる次の op(`deformation` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [tps_warp](tps_warp.md)

## 同カテゴリ(`deform`)

[tps_warp](tps_warp.md) · [register_nonrigid](register_nonrigid.md) · [register_cpd_rigid](register_cpd_rigid.md)

---
*Provenance: deform3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
