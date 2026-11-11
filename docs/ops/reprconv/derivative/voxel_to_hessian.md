---
op: voxel_to_hessian
dim: reprconv
category: derivative
in: voxel
out: hessian
gpu: なし
examples: [hessian_numpy_chain]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# voxel_to_hessian — REPRCONV `derivative` op

- **データ種**: `voxel` → `hessian`
- **呼び出し**: `import fullseye as fs; fs.ledger.voxel_to_hessian(vol, sigma=1.0, scale_normalize=False)` (実装を直接呼ぶなら `import reprconv; reprconv.voxel_to_hessian(vol, sigma=1.0, scale_normalize=False)`、台帳から引くなら `opsreprconv.get("voxel_to_hessian")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

体積 ``voxel`` → 3-D Hessian ``hessian`` の 6 成分 (zz, yy, xx, zy, zx, yx)。numpy と scipy だけで作る ``hessian`` 型の入口。

``hessian3d``(torch の conv3d)と**同じ形**を返す: 長さ 6 の list、各 ``(D,H,W)`` float32、
順は (zz, yy, xx, zy, zx, yx)(軸 0=z, 1=y, 2=x)、単位は 1/voxel²、端は replicate
(``scipy.ndimage`` の ``mode="nearest"``)。だから ``hessian_determinant`` /
``hessian_vesselness`` がそのまま読み、torch の無い素の ``pip install fullseye`` でも
``voxel → hessian → voxel`` の鎖が通る。

``sigma`` はガウス平滑の尺度(voxel)。対角成分は「その軸の 2 階 × 他 2 軸の平滑」、交差成分は
「2 軸の 1 階 × 残り軸の平滑」の分離畳み込み。核はガウス微分の形で、和と 1・2 次モーメントを
厳密に合わせてある(標本化したガウス微分核は和が 0 にならず、明るさが 2 階微分に漏れる)ので、
2 次多項式 ½xᵀAx + bᵀx では内部で ``H = A`` が丸めの範囲で出る。``sigma=0`` は平滑なしでなく
``hessian3d`` と同じ 3 タップ核([1,−2,1] / [−0.5,0,0.5] / [1,2,1]/4)—— torch 版と
float32 の丸めの範囲で一致する。``scale_normalize=True`` で σ² を掛ける(Lindeberg の
γ=1 正規化。尺度をまたいで値を比べるとき。``vol_frangi`` の内部 Hessian と同じ規約)。

2-D 画像は受けない: ``hessian`` 型は 3-D の 6 成分で、受け手も ``(D,H,W)`` を要る。
2-D のヘッセ応答は ``sk_hessian`` / ``sk_hessian_det`` / ``xsk_hessian_eig``(image → image)。

Args:
    vol: 3-D の体積 ``(D,H,W)``、実数、有限。
    sigma: ガウス平滑の尺度(voxel)。有限で >= 0。0 で ``hessian3d`` と同じ核。既定 1.0。
    scale_normalize: True で各成分に σ² を掛ける(``sigma=0`` とは併用できない)。
Returns:
    list of 6 ``np.ndarray``、各 ``(D,H,W)`` float32、順は (zz, yy, xx, zy, zx, yx)。
Raises:
    ValueError: 空 / 3-D でない / 非有限 / sigma が有限の非負でない /
        ``scale_normalize`` と ``sigma=0`` の併用。

空の入力(``vol`` が 0 要素)は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [hessian_numpy_chain](../../../../examples/hessian_numpy_chain.py) — `py -3.11 examples/hessian_numpy_chain.py`

## 型が繋がる次の op(`hessian` を入力に取れる)

[hessian_determinant](hessian_determinant.md) · [hessian_vesselness](hessian_vesselness.md)

## 同カテゴリ(`derivative`)

[gradient_magnitude](gradient_magnitude.md) · [gradient_coherence](gradient_coherence.md) · [hessian_determinant](hessian_determinant.md) · [hessian_vesselness](hessian_vesselness.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
