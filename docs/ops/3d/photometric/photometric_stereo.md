---
op: photometric_stereo
dim: 3d
category: photometric
in: images
out: normalmap
examples: [photometric_stereo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# photometric_stereo — 3D `photometric` op

- **データ種**: `images` → `normalmap`
- **呼び出し**: `import fullseye as fs; fs.ledger.photometric_stereo(images, lights, mask=None, normalize=True, *, lit_only=False, lit_thresh=0.001)` (実装を直接呼ぶなら `import photometric; photometric.photometric_stereo(images, lights, mask=None, normalize=True, *, lit_only=False, lit_thresh=0.001)`、台帳から引くなら `ops3d.get("photometric_stereo")`)
- **台帳経由の戻り値**: `fullseye.ledger.photometric_stereo(...)` は**宣言 out 型 `normalmap` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.photometric_stereo.raw(...)`、または `photometric.photometric_stereo` を直接呼ぶ。

## 使い方

Lambertian フォトメトリックステレオ: 既知光源方向の N 枚から法線とアルベドを復元。→ (normals HxWx3, albedo HxW)。

I_n = albedo * max(N·L_n, 0)。各画素で g = albedo*N を最小二乗 g = pinv(L) @ I で解き、
albedo=|g|, normal=g/|g|。N>=3 必要。albedo~0 や mask 外の画素は normal=(0,0,1)。
normalize=True で光源ベクトルを単位方向に正規化(render_lambertian と同一規約 = アルベド絶対値が正しく出る)。
強度重み付き光源を使うなら normalize=False にし、合成側も生ベクトルで揃えること。

lit_only(2026-09-04 追加): **付着影(attached shadow)を外して解く**。モデルの
max(·, 0) は非線形なので、N·L < 0 の観測(真の値は 0)を線形最小二乗にそのまま入れると
解が偏る ―― 実測: 影も AO も無い球で中央値 **9°**、点灯している光源だけで解くと
**0.000°**。既定は False(従来の挙動を変えない)。True にすると画素ごとに
`I > lit_thresh` の光源だけを使って解き直す。**同じ点灯パターンの画素をまとめて**
1 回の疑似逆行列で処理するので、追加コストは光源数ぶんのパターン数に比例する程度
(6 灯なら最大 64 群)。点灯光源が 3 未満の画素は全光源の解に戻す(fail-open:
解けない画素を NaN にするより、偏っていても値がある方が下流の積分が壊れない)。

lit_thresh: 「点灯している」とみなす輝度の下限。撮影ノイズより上に置く。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photometric_stereo](../../../../examples_3d/photometric_stereo.py) — `py -3.11 examples_3d/photometric_stereo.py`

## 型が繋がる次の op(`normalmap` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [render_shaded](../render/render_shaded.md) · [phong_shade](../render/phong_shade.md) · [matcap_shade](../render/matcap_shade.md) · [brdf_lommel_seeliger](../render/brdf_lommel_seeliger.md) · [brdf_hapke](../render/brdf_hapke.md) · [bump_normals_fbm](../terrain/bump_normals_fbm.md) · [integrate_normals](integrate_normals.md)

## 同カテゴリ(`photometric`)

[surface_normals](surface_normals.md) · [integrate_normals](integrate_normals.md) · [render_lambertian](render_lambertian.md)

---
*Provenance: photometric.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
