---
op: skeleton_graph3d
dim: 3d
category: medial
in: voxel
out: table
examples: [medial_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# skeleton_graph3d — 3D `medial` op

- **データ種**: `voxel` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.skeleton_graph3d(vol, distance=None, spacing=(1.0, 1.0, 1.0), min_branch_len=0.0)` (実装を直接呼ぶなら `import medial; medial.skeleton_graph3d(vol, distance=None, spacing=(1.0, 1.0, 1.0), min_branch_len=0.0)`、台帳から引くなら `ops3d.get("skeleton_graph3d")`)

## 使い方

3D 骨格を **ノード(接合点・端点)と枝(長さ・半径)のグラフ**に組み立てる。

``skeleton_junctions3d`` / ``skeleton_endpoints3d`` / ``skeleton_branches3d`` は
「どの voxel がノードか/枝か」を **マスク**で返すだけで、**どの枝がどのノードと
どのノードを繋ぐか**は返さない。回路にするにはその接続が要る —— 神経形態の
ケーブル理論では、区画の軸方向コンダクタンスが **直径と長さ**で決まり、区画同士の
**繋がり方**が回路そのものになる。この op はその 1 段を埋める。

引数:
    vol: 3-D の骨格(bool か ``{0, 1}``。``skeletonize_vol`` の出力)。中身が
        塊(6 近傍がすべて前景の interior voxel がある)なら、族の他の op と
        同じく内部で ``skeletonize_vol`` を先に掛ける。
    distance: 任意。同形の距離変換ボリューム(``vol_distance_transform`` の
        出力)。渡すと各ノード・各枝に半径が付く。**単位は渡した距離場に従う**
        —— 物理単位が要るなら ``vol_distance_transform(mask, spacing)`` を渡す。
    spacing: ``(sz, sy, sx)``。枝の長さを **実距離**で測る(EM の異方ボクセルが
        既定の想定)。``VolumeMeta`` も受ける。
    min_branch_len: これ未満の**末端の枝(ヒゲ)**を刈る(既定 0 = 刈らない)。
        単位は ``spacing`` の実距離。刈るのは「片端が端点(次数 1)で、もう
        片端が次数 2 以上」の枝 —— **両端とも端点**の枝は刈らない。それは
        それ自体が 1 つの連結成分(短い孤立した管)なので、刈ると構造ごと
        消えてしまう。刈ったぶんは ``n_pruned_branches`` に返す。

返り値: ``dict``(台帳の宣言 out 型 = ``table``)。

    * ``nodes``: ノード表。``id`` / ``z,y,x``(voxel 添字での重心。実座標は
      spacing を掛ける)/ ``kind`` / ``degree`` / ``n_voxels`` / ``radius``
      (``distance`` を渡したとき、そのノードの voxel での最大値 = 内接半径)/
      ``component``。
    * ``edges``: 枝表。``u`` / ``v``(ノード id の対)/ ``length``(骨格に沿った
      実距離、spacing 込み)/ ``radius_mean`` / ``radius_min`` / ``n_points``
      (経路上の voxel 数、両端のノード voxel を含む)/ ``component``。
    * ``n_nodes`` / ``n_edges`` / ``n_components`` / ``n_cycles`` /
      ``n_pruned_branches`` / ``n_skeleton_voxels`` / ``spacing`` / ``has_radius``。

規約(ここが位相を決める):
    * 26 近傍次数 **2** の voxel は枝の途中であってノードにしない。次数 **1 以下**
      が端点(孤立 voxel を含む)、**3 以上**が接合。
    * 接合 voxel は 1 つとは限らない(離散骨格では分岐が数 voxel の塊になる)。
      26 連結で塊にまとめて **1 ノード**として数え、座標はその重心。
    * **連結成分が複数なら黙って繋がない。** ``n_components`` に本数を返し、
      各ノード・各枝に ``component`` を付ける。
    * 閉ループだけの成分(ノードになる voxel が 1 つも無い輪)は、その成分の
      先頭 voxel を 1 つだけ種のノードに立てて自己ループの枝 1 本にする。
      こうすると **オイラーの関係 ``n_cycles = n_edges - n_nodes +
      n_components``** が輪でも成り立つ(木だと仮定していない)。
    * ``kind`` は**刈った後の**次数で決まる: 0 = ``isolated`` / 1 = ``endpoint`` /
      2 = ``chain``(輪の種ノード、または刈った結果そうなったノード)/
      3 以上 = ``junction``。刈ると接合が次数 2 に落ちることがあり、その
      ノードは残る(区画の境界としては正しいが、「次数 2 はノードにしない」
      という上の規約は**刈る前**の話であることに注意)。
    * 接合の塊どうしが直接隣接している(間に次数 2 の道が無い)場合は、その
      対に対して **1 本**の枝を作る(長さ = 隣接する voxel 対の最短)。

検証(すべて ``ValueError`` で fail-closed): 3-D でない/空配列/NaN・Inf/
bool でも ``{0,1}`` でもない値(中間値の「たぶん前景」を黙って丸めない)/
前景がゼロ/``distance`` の形が違う・負・非有限/``spacing`` が 3 つの正の
有限値でない/``min_branch_len`` が負。細線化が要る入力で scikit-image が
無ければ ``ImportError``。

注意(honest、いずれも実測):

* 長さは **26 近傍の折れ線**の和なので、曲がった枝は連続曲線より長く出る。
  半径 14 voxel の閉じた管(真の周長 87.96)で **94.7 = +7.7 %**。
* **太い入力は端が縮む。** 自由端の細線化は端の蓋の手前で止まる。長さ 35 の
  直円柱で実測すると 半径 1・2 は **35.00(縮みゼロ)**、半径 3 は 33、
  半径 4 は 31 —— 半径が 3 以上になると片端あたり 1〜2 voxel 内側に寄る。
  長さを真値と比べるなら、**細線化を通らない 1 voxel 幅の骨格**を渡すこと
  (そのときは厳密に一致する: 31 voxel の直線で 30.0)。
* 分岐では、接合の塊(次数 3 以上が 26 連結でまとまったもの)に呑まれたぶん
  だけ枝が短くなる。**接合より短いヒゲは枝にならず、ノードの ``n_voxels``
  に含まれて消える**(``min_branch_len`` で刈る対象にすらならない)。
* 半径は ``distance`` の値そのもの。端点は端の蓋までの距離で決まるので
  **管の半径より小さく出る**(半径 3 の円柱で端点 2.0、枝の平均 3.07)。
  枝の太さを見るなら ``radius_mean`` / ``radius_min`` を使う。
* **90 度回転**: 1 voxel 幅の骨格を入れた場合、グラフは同型で長さも厳密に
  一致する(9 通り実測)。太い塊を渡した場合はノード数・枝数は一致するが、
  長さは最大 1.41(= 対角 1 歩)ずれる —— ずれているのはこの op ではなく
  **細線化ヘルパ(skimage Lee)が回転で厳密には同じ骨格を作らない**ため。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [medial_topology](../../../../examples_3d/medial_topology.py) — `py -3.11 examples_3d/medial_topology.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [topology_signature](topology_signature.md) · [medial_match](medial_match.md) · [skeleton_junctions3d](skeleton_junctions3d.md) · [skeleton_endpoints3d](skeleton_endpoints3d.md) · [skeleton_prune3d](skeleton_prune3d.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
