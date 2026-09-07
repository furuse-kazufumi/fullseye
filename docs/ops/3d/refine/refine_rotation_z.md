---
op: refine_rotation_z
dim: 3d
category: refine
in: voxel × voxel × angle
out: angle
gpu: true
examples: [refinement]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# refine_rotation_z — 3D `refine` op

- **データ種**: `voxel × voxel × angle` → `angle`
- **呼び出し**: `import fullseye as fs; fs.ledger.refine_rotation_z(scene, template, init_angle_deg=0.0, device='cpu', iters=40, tol=0.001, max_step_deg=5.0)` (実装を直接呼ぶなら `import match3d; match3d.refine_rotation_z(scene, template, init_angle_deg=0.0, device='cpu', iters=40, tol=0.001, max_step_deg=5.0)`、台帳から引くなら `ops3d.get("refine_rotation_z")`)
- **台帳経由の戻り値**: `fullseye.ledger.refine_rotation_z(...)` は**宣言 out 型 `angle` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.refine_rotation_z.raw(...)`、または `match3d.refine_rotation_z` を直接呼ぶ。
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

z 軸回転角の **Gauss-Newton 精緻化**(Lucas-Kanade on SSD、1 パラメータ)。

Fourier-Mellin 等の粗い z 軸回転推定(±3° 級)を、SSD を回転角 θ だけで最小化して高精度化
する下流精緻化器。scene ≈ rotate_z(template, θ_true) を仮定し、warp_z(template, θ) が scene に
一致する θ を求める。返り値の角は match_logpolar_z と同符号(scene = template を θ 回転)。

定式化: 残差 r(θ)=T_warp(θ)−S を θ で線形化。回転の steepest-descent image(解析ヤコビアン)
は、中心化格子 (X=W−cx, Y=H−cy) と warp 済みテンプレの空間勾配 (gx,gy) から
J = ∂T_warp/∂θ = (−gx·Y + gy·X)(rad あたり)。1 パラメータ GN 更新は Δθ = −(JᵀWr)/(JᵀWJ)。
回転で 0 詰めされた隅は valid マスク W で除外。step は max_step_deg で制限し発散を防ぐ。

実測(48³ 非対称 volume, CPU, 別補間器 scipy order=3 で scene 生成=inverse crime 回避):
clean 誤差 ~0.0006°、5% ノイズ 0.009°、10% ノイズ 0.017°(いずれも <0.3°)。捕捉レンジは
最低 ±10°、収束 3-5 反復・~12ms。粗推定 ±3° をそのまま使う場合(誤差 3°)比で ~5000 倍改善。

Parameters
----------
scene : array_like (D,H,W)     基準 volume(この姿勢へ template を合わせる)。
template : array_like (D,H,W)  回転させて scene に合わせるテンプレ volume。同一格子・同一中心。
init_angle_deg : float         粗推定角(deg)。Fourier-Mellin 等の初期値。
device : str                   "cpu" / "cuda"。device 非依存。
iters : int                    最大反復数。
tol : float                    |Δθ|(deg)がこれ未満で収束打ち切り。
max_step_deg : float           1 反復あたりの角ステップ上限(deg、発散防止)。

Returns
-------
(angle_deg, n_iters) : (float, int)  精緻化角(deg)と実行反復数。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [refinement](../../../../examples_3d/refinement.py) — `py -3.11 examples_3d/refinement.py`

## 型が繋がる次の op(`angle` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`refine`)

[refine_peak_newton](refine_peak_newton.md) · [refine_translation_lk](refine_translation_lk.md) · [refine_lm](refine_lm.md) · [icp_point2point_3d](icp_point2point_3d.md) · [icp_point2plane](icp_point2plane.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
