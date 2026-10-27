# 離散 Gauss–Bonnet の教材が読むメッシュ(合成 2 つ・走査 1 つ、CC0)

`tools/build_gaussbonnet_anim3d.py`(「どんな形でも、曲がり方を全部足すと同じ数になる」の動く 3-D)と
`tests/test_anim3d_gaussbonnet_2026_10_26.py` が読む三角形メッシュ。小惑星イトカワの形は `data/itokawa_shape/` を読む(出典はそちらの README)。

## genus2.npz / genus3.npz(合成)

- 中身: `vertices`(float32 (N, 3))、`faces`(int32 (M, 3)、0 始まり、外向きの巻き)、`genus`(2 か 3)。
- 作り方: `py -3.11 -I tools/import_gaussbonnet_meshes.py --genus`。平面の梯子の形のグラフ(2 本の横棒と g + 1 本の縦棒)を管で太らせた
  陰関数(線分までの距離の滑らかな最小 − 管の半径 0.42)を、格子間隔 0.055 の体積で評価し、等値面 0 を marching cubes で切り
  (scikit-image、任意の依存)、`decimate_qem_manifold` で 7,000 面に減らした。
- 書く前に確かめたこと: 境界辺 0・非多様体辺 0・部品 1 つ・χ = V − E + F = 2 − 2g(合わなければ書かない)。
- 出典・利用条件: 合成(このリポジトリの Apache-2.0)。

## triceratops_scan.npz(実物の 3-D 走査、間引きあり)

- 元データ: *Triceratops horridus* Marsh, 1889(骨格)の 3-D 走査、Smithsonian Institution の公開 3-D データ(150k 面・4096 px テクスチャ版の GLB、
  14,395,048 バイト、SHA-256 `cd8525c7371d14876bcdefe3f579d216bf597db892c2de6ed597da86bf1a98b3`)。`sample_data.py` の台帳 `triceratops` と同じ物。
- 利用条件: **CC0**(館の公開データの表示。CC0 の資産は商用も改変も可で、帰属は求められない)。出典と改変はここに書く。
- 取得: 2026-10-26。原本は repo の外に置く(取得物は untrusted として専用の空ディレクトリに置き、SHA-256 を照合してから読む)。
- 中身: `vertices`(float32 (27456, 3)、glTF の座標のまま。y が上、z が長手)、`faces`(int32 (24000, 3))、
  `source_vertices` 102235・`source_faces` 149998・`source_boundary_edges` 50256・`source_components` 2107・`source_chi` 2108(原本の値)、
  `split_vertices` 119、`source_sha256`。
- 改変: `read_gltf_merged` で全プリミティブを 1 つにし、`decimate_qem_manifold`(境界を保つ)で 149,998 面 → 24,000 面に間引き、
  間引きで扇が 2 つになった頂点(つままれた頂点)119 個を扇ごとに分けた。テクスチャは持たない。
- 性質(一次情報 = この npz を op で数えた値): 走査はテクスチャの継ぎ目で頂点が切れた **開いた面片の集まり**(間引き後 1,919 枚、境界辺 27,074 本、
  χ = 1,919)で、1 つの閉曲面ではない。教材では「境界のある面」の限界の回に使う(面片ごとに離散 Gauss–Bonnet は成り立つが、χ は面片の数を語る)。
- 作り方: `py -3.11 -I tools/import_gaussbonnet_meshes.py --triceratops <取得した GLB>`。境界の項つきの Σ K が 2πχ と 1e-9 以内で
  一致しなければ書かない。
