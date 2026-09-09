---
op: match_phase_3d
dim: 3d
category: match_pose
in: voxel × voxel
out: shift
gpu: true
examples: [shape_desc_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# match_phase_3d — 3D `match_pose` op

- **データ種**: `voxel × voxel` → `shift`
- **呼び出し**: `import fullseye as fs; fs.ledger.match_phase_3d(a, b, device='cpu')` (実装を直接呼ぶなら `import match3d; match3d.match_phase_3d(a, b, device='cpu')`、台帳から引くなら `ops3d.get("match_phase_3d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D 位相相関(FFT)。b を a に合わせる整数シフト (dz,dy,dx) を返す。

Reddy & Chatterji の 3D 版。相互パワースペクトルの逆 FFT のピーク = 平行移動。テンプレート
不要・全 volume・O(N log N)。回転/スケールは別途(PCA / log-polar)。

引数: ``a``, ``b`` は同形の 3-D 配列(違えば ValueError)。float32 に落として FFT する。
返り値: int の tuple ``(dz, dy, dx)``、各軸 ``(−N/2, N/2]`` に折り返し済み。意味は
``np.roll(b, (dz,dy,dx), axis=(0,1,2)) ≈ a``(b をこれだけ動かすと a に重なる)。
- 循環相関なので、はみ出した部分は反対側から回り込む(窓掛けはしない)。シフトが volume の
半分を超えると符号が反転して見える。
- 位相のみ(``R/|R|``)なので振幅・コントラスト差に不変だが、ノイズが白色化されてピークが
埋もれることがある。全 0 の volume は 0 になり index 0 を返す。
- 整数精度。サブボクセルは ``refine_translation_lk`` / ``refine_peak_newton`` へ。
- 回転・スケールがあると効かない(``match_logpolar_z`` → 回転補正 → 本 op の順)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`

## 型が繋がる次の op(`shift` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_pose`)

[match_pca](match_pca.md) · [moment_axes](moment_axes.md) · [match_logpolar_z](match_logpolar_z.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
