<!-- tools/gen_wingconv_gallery.py が自動生成。記事 md への挿入候補であり、このファイル自体は記事ではない。数値はすべて生成時の実測値。 -->
# 表現変換ウィング ―― 展示キャプション原稿

生成元: `tools/gen_wingconv_gallery.py`(`py -3.11 tools/gen_wingconv_gallery.py`)。画像はすべて fullseye の op
(`reprconv` / `imagedraw`)と numpy 合成で描いており(matplotlib 不使用)、図に焼いた数値は
1 つ残らずその場で op を呼んで得た実測値である。乱数は seed 固定・幾何も固定なので
再生成でバイト列が一致する(`--verify` で検査)。

このウィングの主張は 1 つ ―― **変換の嘘は往復で露見する**。
変換 op は「入口の型」と「出口の型」の両方を主張するので、嘘をつく面が 2 つある。
だから主役は「A → B → A' を並べ、最後のコマに残差と誤差の数値を焼いた GIF」で、
**可逆なものは残差が真っ黒 = 誤差 0**、**不可逆なものは何がどれだけ落ちるか**を数字で出す。

## 1. 可逆な変換 ―― 法線 ⇄ 方位・仰角[度]
![可逆な変換 ―― 法線 ⇄ 方位・仰角[度]](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingconv_roundtrip_normals.gif)

*↑ **可逆な変換 ―― 法線 ⇄ 方位・仰角[度]** ―— 袋小路だった `normals` に出口を作った。方位 az と仰角 el(**どちらも度**)へ変換し、そこから組み直すと 9216 本の法線が **max|Δ| = 2.289e-12**(角度差 1.207e-06 度)で戻る。最後のコマの残差が真っ黒なのは「絵が暗い」のではなく **0..1 の固定スケールで 0** だからで、自動スケールにすると倍精度の丸めが模様に見えて可逆なのに壊れて見える。*

- GIF: `docs/articles/assets/media/wingconv_roundtrip_normals.gif` (4 frame(s), 792x532 px, 0.14 MB)
- サムネ: `docs/articles/assets/thumbs/wingconv_roundtrip_normals_thumb.jpg`
- SHA-256: `596e13795efe1cb08b5cd3ece7a414e76b261dc2d94ad62cf28f79ffac4580f4`

## 2. 可逆な変換 ―― 主曲率 ⇄ 形状指数(臍点を含めて厳密)
![可逆な変換 ―― 主曲率 ⇄ 形状指数(臍点を含めて厳密)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingconv_roundtrip_curvature.gif)

*↑ **可逆な変換 ―― 主曲率 ⇄ 形状指数(臍点を含めて厳密)** ―— 球・鞍・円柱・平面の 4 パッチ(9216 点。うち臍点・平面 4608 点)を形状指数 S と曲がり C へ移し、戻して **max|Δ| = 2.220e-16**。教科書の `atan((k1+k2)/(k1-k2))` は臍点で 0 除算になるが、`atan2` 形で書けば球 S=+1・鞍 S=0・円柱 S=+0.5 が閉形式のまま全域で厳密に往復する。*

- GIF: `docs/articles/assets/media/wingconv_roundtrip_curvature.gif` (4 frame(s), 792x532 px, 0.26 MB)
- サムネ: `docs/articles/assets/thumbs/wingconv_roundtrip_curvature_thumb.jpg`
- SHA-256: `49783cc6f12b4829dcf731f0e771082a3629a2b7564c9fa1c97afbdb55d0d7c7`

## 3. 不可逆な変換 ―― keypoints ⇄ 画素格子(落ちる量を測る)
![不可逆な変換 ―― keypoints ⇄ 画素格子(落ちる量を測る)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingconv_roundtrip_keypoints.gif)

*↑ **不可逆な変換 ―― keypoints ⇄ 画素格子(落ちる量を測る)** ―— 4 px 間隔に置いた 900 点を計数画像へ焼いて拾い直すと、軸あたり RMS **0.2925 px**(一様量子化の理論 1/√12 = 0.2887)、2-D 距離 RMS 0.4136 px(理論 √(2/12) = 0.4082)。ランダム配置なら 120 → 111 点に融合する ―― **量子化(ずれる)と融合(消える)は別の損失**で、混ぜて 1 つの RMS にするとどちらがどれだけ効いたか言えなくなる。*

- GIF: `docs/articles/assets/media/wingconv_roundtrip_keypoints.gif` (5 frame(s), 792x532 px, 0.14 MB)
- サムネ: `docs/articles/assets/thumbs/wingconv_roundtrip_keypoints_thumb.jpg`
- SHA-256: `945237fc3c62ab0cf43d0830dc6992ac56ed353dd6fa0ca6b5b12a17bbc589ff`

## 4. 不可逆な変換 ―― 点群 → ガウシアン → 体積(質量で測る)
![不可逆な変換 ―― 点群 → ガウシアン → 体積(質量で測る)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingconv_roundtrip_gaussians.gif)

*↑ **不可逆な変換 ―― 点群 → ガウシアン → 体積(質量で測る)** ―— **産む op が 1 つも無かった** `gaussians` に入口を作った。中心 mu は往復 max|Δ| = 0.000e+00 で bit 一致し、sigma と w は往復で消える「追加された情報」。体積へ焼くと 3σ の**箱**打ち切りで**0.99192** が理論値 —— 最初これを 3σ の**球** 0.9707 と書いたが、刻みを 1.0 → 0.125 と細かくすると箱の値へ収束して球へは近づかず、反証できた。*

- GIF: `docs/articles/assets/media/wingconv_roundtrip_gaussians.gif` (4 frame(s), 792x532 px, 0.10 MB)
- サムネ: `docs/articles/assets/thumbs/wingconv_roundtrip_gaussians_thumb.jpg`
- SHA-256: `9e19ef2fa00ecb2688237735f958c2ba8e22c477ebb4334c81e81fc97d79319d`

## 5. 表現をまたいで一周 ―― 何が残り、何が消えるか
![表現をまたいで一周 ―― 何が残り、何が消えるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingconv_cross_loop.gif)

*↑ **表現をまたいで一周 ―― 何が残り、何が消えるか** ―— voxel → mesh → points → gaussians → voxel。体積 5444 voxel の立体は mesh の段で**中身を失い**(3268 頂点 / 6584 面、表面積 2461.8)、points で接続と法線を失う。内部の充填率は**100.0% → 38.2%** で、戻ってきたのは立体ではなく殻。一方で重心は 1.2925 voxel しか動かない ―― **一致する指標と一致しない指標を両方出す**のが正直な報告で、重心だけ見せると「一周して戻った」という嘘になる。★この主張は最大値投影では言えない(MIP は薄い殻でも中が詰まって見える。実際に一度そう描きかけた)ので、中心断面と内部の充填率で示している。*

- GIF: `docs/articles/assets/media/wingconv_cross_loop.gif` (5 frame(s), 792x532 px, 0.12 MB)
- サムネ: `docs/articles/assets/thumbs/wingconv_cross_loop_thumb.jpg`
- SHA-256: `fdefdaff55bb3f304a665ed94a74476b979ec3d54d64af23cdf7623273fd7d8a`

## 6. 死んだ型 `flow` が「見える」ようになった
[![死んだ型 `flow` が「見える」ようになった](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingconv_flow_colorwheel_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingconv_flow_colorwheel.png)

*↑ **死んだ型 `flow` が「見える」ようになった** ―— `flow` は単入力で産む op も食う op も無い完全な孤島だった。密なシーンフロー [3, 24, 96, 96] を大きさ(voxel)と色相環(rgbimage)へ出す 2 つの出口を作り、**色の意味の凡例を同じ図に焼いた**。この repo の `flow` は (3,D,H,W) の密フローと (N,3) の散在フローが**同じ型名で同居している**ので、密用 ['flow_magnitude', 'flow_to_rgbimage'] と散在用 ['flow_speed', 'flow_apply'] でop を分け、相手の形は fail-closed にしてある。*

- PNG: `docs/articles/assets/wingconv_flow_colorwheel.png` (1 frame(s), 676x820 px, 0.07 MB)
- サムネ: `docs/articles/assets/wingconv_flow_colorwheel_thumb.jpg`
- SHA-256: `ce75caad5b7d998107f9c879883e480fb2da06c7b04bef349cad4d9c20e15ebf`

## 7. 軸・単位・spacing の取り違えは例外を出さずに通る
[![軸・単位・spacing の取り違えは例外を出さずに通る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingconv_axis_unit_traps_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingconv_axis_unit_traps.png)

*↑ **軸・単位・spacing の取り違えは例外を出さずに通る** ―— (u,v) を (v,u) と読むと重心が 0.2 ずれ、spacing を既定のままにするとピークが [4, 5, 6] でなく[10, 12, 14] に立ち、π/6 rad を「度」として渡すと0.5236 度だけ回る。積算窓を 1 ms でなく 1 s と読めば計数は 1000 倍になる。**どれも例外は出ず、有限で、もっともらしい絵が返る** ―― だから op 名に軸を書き、単位を引数にした。*

- PNG: `docs/articles/assets/wingconv_axis_unit_traps.png` (1 frame(s), 636x1126 px, 0.04 MB)
- サムネ: `docs/articles/assets/wingconv_axis_unit_traps_thumb.jpg`
- SHA-256: `fa59d4e883d82e75021b56f39e6615d2c1359c151b7df1d7a80cecd1ecf70b8a`

## 8. 死んだ語彙 ―― 産む op はあるのに、そこから先へ行けない型
[![死んだ語彙 ―― 産む op はあるのに、そこから先へ行けない型](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingconv_dead_vocabulary_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingconv_dead_vocabulary.png)

*↑ **死んだ語彙 ―― 産む op はあるのに、そこから先へ行けない型** ―— 台帳 515 op を「単入力かつ in 型 ≠ out 型 = 変換」で機械集計すると、他型へ一歩も出られない型が **25 個**あった。`reprconv` の 42 op で **16 型**に出口ができ、変換ペアは121 → 159 種、袋小路は 25 → 9 個。残した 9 型は**埋めない理由**を台帳に書いてある ―― 埋めないことも判断である。*

- PNG: `docs/articles/assets/wingconv_dead_vocabulary.png` (1 frame(s), 1180x720 px, 0.09 MB)
- サムネ: `docs/articles/assets/wingconv_dead_vocabulary_thumb.jpg`
- SHA-256: `ea4ab5aa16bebdd20e8741aab277db3e5ccab6dbc8ca78c1000a265ebf4faf90`
