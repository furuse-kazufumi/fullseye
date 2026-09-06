---
op: refine_lm
dim: 3d
category: refine
in: voxel × voxel × position
out: table
gpu: true
examples: [refinement]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# refine_lm — 3D `refine` op

- **データ種**: `voxel × voxel × position` → `table`
- **呼び出し**: `import match3d; match3d.refine_lm(scene, template, init_pos, device='cpu', iters=50, scale=True, gain=False, lam0=0.001, tol=1e-08)` (または `ops3d.get("refine_lm")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

Levenberg-Marquardt による並進(+等方スケール/輝度ゲイン)サブボクセル精緻化。

粗いマッチ位置 init_pos(テンプレ中心の scene 内座標 [z,y,x])を出発点に、
forward-additive Lucas-Kanade を減衰付き Gauss-Newton(LM)で解き SSD
    E(p) = Σ_x [ I(W(x;p)) - g·T(x) ]²
を最小化する。整数 NCC / Fourier-Mellin / Hough の粗推定を連続座標へ収束させる後段。

ワープ        W(x;p) = t + s·(x - c_T)   (c_T=テンプレ中心, t=並進, s=等方スケール)
ヤコビアン    ∂I(W)/∂p は grid_sample を自動微分に通して厳密取得(三線形補間の解析勾配。
              固定点が真の SSD 最小に一致 → sobel 定数倍のバイアスを避け高精度)。
LM           Δp = -(H + λ·diag(H))⁻¹ b、成功(コスト減)で λ×0.4 減衰・失敗で λ×5 増加。

引数:
    scene      : シーン volume (D,H,W)。
    template   : テンプレ volume (Td,Th,Tw)。scene より小。
    init_pos   : 粗いテンプレ中心位置 [z,y,x] (voxel。NCC locate の [d,h,w] 等)。
    device     : "cpu" / "cuda"。device 非依存。
    iters      : 最大反復数(通常 4-6 で収束)。
    scale      : True で等方スケール s を同時最適化(4パラメータ)。False なら並進のみ。
    gain       : True で輝度ゲイン g(残差 I(W)-g·T)を追加最適化。明るさ差/ノイズに頑健。
    lam0, tol  : 初期減衰係数 / 収束閾値(ステップノルム・相対コスト減)。

返り値(dict):
    pos   : 精緻化テンプレ中心 [z,y,x] (連続座標)
    scale : 等方スケール(scale=False なら 1.0)
    gain  : 輝度ゲイン(gain=False なら 1.0)
    cost  : 最終 SSD、rms: 1voxel あたり残差 RMS、iters: 実行反復数

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [refinement](../../../../examples_3d/refinement.py) — `py -3.11 examples_3d/refinement.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`refine`)

[refine_peak_newton](refine_peak_newton.md) · [refine_translation_lk](refine_translation_lk.md) · [refine_rotation_z](refine_rotation_z.md) · [icp_point2point_3d](icp_point2point_3d.md) · [icp_point2plane](icp_point2plane.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
