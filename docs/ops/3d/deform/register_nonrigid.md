---
op: register_nonrigid
dim: 3d
category: deform
in: points × points
out: points
examples: [nonrigid_deform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# register_nonrigid — 3D `deform` op

- **データ種**: `points × points` → `points`
- **呼び出し**: `import deform3d; deform3d.register_nonrigid(src, dst, iters=20, lam=1.0, k_smooth=None)` (または `ops3d.get("register_nonrigid")`)
- **台帳経由の戻り値**: `fullseye.ledger.register_nonrigid(...)` は**宣言 out 型 `points` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.register_nonrigid.raw(...)`、または `deform3d.register_nonrigid` を直接呼ぶ。
  - 本体の返り: `(warped, info, info)`

## 使い方

非剛体 ICP で ``src`` を ``dst`` へ寄せる。

各反復で「現在の変形後 src」から ``dst`` への最近傍対応を張り直し、その対応を
制御点対応(制御中心 = 元の src)として TPS を正則化つきで再当てはめし、src を
変形する。対応が既知でなくとも滑らかな非線形変形を回復できる。

実装上の要点(頑健性):
    - **スケール不変**: λ は dst の重心まわり RMS 半径に対する相対値として扱う
      (内部で λ_eff = λ·scale)。座標が 100 倍でも同じ λ が同じ挙動を与える。
    - **発散ガード**: 対応が曖昧だと単純な NN 反復は正のフィードバックで発散し得る。
      反復ごとの対応 RMS を監視し、**最良反復**(最小 RMS)の変形とモデルを返す。
      これにより悪い λ でも「初期より悪い」結果を返さない。
    - λ が大きいほど剛(変形が小さい)。既定 λ=1.0 は保守的(ほぼ剛)なので、
      大きな非線形変形を回復させたい場合は λ を小さく(例 0.01〜0.05)する。

引数:
    src: (N,3) 移動側点群。
    dst: (M,3) 固定側(参照)点群。
    iters: 最大反復回数。
    lam: TPS 正則化 λ(スケール相対)。大きいほど変形が滑らか(外れ対応に頑健、
        当てはめは緩い)。小さいほど密着(細かい変形を回復)。
    k_smooth: None なら最近傍1点を目標にする(ハード対応)。整数を与えると
        ``dst`` 側の k 近傍の平均を目標にして対応を平滑化する(ノイズに頑健)。

返り値:
    warped_src: (N,3) 最良反復での変形後 src。
    model: 対応する TPS モデル(制御中心 = 元 src、原座標系でそのまま
        ``tps_warp`` に渡せる)。1回も当てはめできなければ None。
    info: dict。"rms"(最良の対応 RMS)、"rms_init"(初期=恒等時の対応 RMS)、
          "rms_history"(list)、"iters"(実反復数)、"best_iter"、"converged"(bool)。

例外:
    ValueError: 形状不正、点数不足、k_smooth 不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [nonrigid_deform](../../../../examples_3d/nonrigid_deform.py) — `py -3.11 examples_3d/nonrigid_deform.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`deform`)

[tps_fit](tps_fit.md) · [tps_warp](tps_warp.md) · [register_cpd_rigid](register_cpd_rigid.md)

---
*Provenance: deform3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
