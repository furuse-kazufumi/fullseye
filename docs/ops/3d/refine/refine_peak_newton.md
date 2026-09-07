---
op: refine_peak_newton
dim: 3d
category: refine
in: score × position
out: position
gpu: true
examples: [refinement]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# refine_peak_newton — 3D `refine` op

- **データ種**: `score × position` → `position`
- **呼び出し**: `import match3d; match3d.refine_peak_newton(score, idx, device='cpu', max_iter=12, tol=0.0001)` (または `ops3d.get("refine_peak_newton")`)
- **台帳経由の戻り値**: `fullseye.ledger.refine_peak_newton(...)` は**宣言 out 型 `position` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.refine_peak_newton.raw(...)`、または `match3d.refine_peak_newton` を直接呼ぶ。
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

スコア/相関 volume の整数ピークを 3D Newton でサブボクセル精緻化する(反復最適化)。

粗いマッチ(整数 NCC / Fourier-Mellin ±3° / Hough ±0.5voxel)が返す整数ピーク idx を、局所の
2 次モデル f(x)≈f0+gᵀΔ+½ΔᵀHΔ の停留点 Δ=-H⁻¹g へ反復更新して連続座標へ収束させる。
軸別の放物線サブピクセルと違い **全 3x3 Hessian(交差曲率 fzy,fzx,fyx を含む)** を使うため、
回転した(相互曲率のある)異方性ピークでも座標軸間の結合バイアスを除去できる。

各反復: 現在位置まわりの 27 近傍を trilinear で取得 → 中心差分で勾配 g と 6 成分 Hessian H を
組み、Δ=solve(H,-g)。各成分を ±1 voxel にクリップ(信頼領域)して位置を更新、|Δ|<tol で収束。
ガウス山では中心差分勾配の零点が真のピークに一致するため停留点へ収束する(単一ステップでは
2 次モデル誤差が残り ±0.05voxel を割れないが、反復で ~0.02voxel まで収束)。H が負定値でない
(=極大でない)real な相関面では上昇方向へ退避(勾配上昇ステップ)して発散を防ぐ。

Parameters
----------
score : array_like または torch.Tensor
    3D スコア/相関 volume (D,H,W)。値が大きいほどピーク。
idx : tuple[int,int,int]
    整数ピーク座標 (z,y,x)(通常 argmax の unravel 結果)。
device : str
    "cpu" / "cuda"。torch 演算の device。
max_iter : int
    最大反復回数(既定 12)。
tol : float
    収束判定(更新量 L2 ノルム、既定 1e-4)。

Returns
-------
numpy.ndarray
    [score_peak, z, y, x] (精緻化後)。score_peak は精緻化位置での trilinear 補間スコア。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [refinement](../../../../examples_3d/refinement.py) — `py -3.11 examples_3d/refinement.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_translation_lk](refine_translation_lk.md) · [refine_lm](refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`refine`)

[refine_translation_lk](refine_translation_lk.md) · [refine_lm](refine_lm.md) · [refine_rotation_z](refine_rotation_z.md) · [icp_point2point_3d](icp_point2point_3d.md) · [icp_point2plane](icp_point2plane.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
