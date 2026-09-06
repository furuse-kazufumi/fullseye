---
guide: blob_analysis
dim: blob
title: 連結成分解析(散らばった物体を数えて測って選ぶ) — 使い方ガイド
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
---

# 連結成分解析(散らばった物体を数えて測って選ぶ) — 使い方ガイド

## この族は何をする道具箱か

**二値の領域を「物体の集まり」として扱う**層です。入力は 2-D の二値領域、出力はラベル画像 `(H, W)` の `int32`(背景 0、物体 1..n)と、**物体ごとに 1 行の特徴量**。

産業検査でいちばん頻度の高い連鎖 —— *しきい値で前景を出す → 物体に切る → 物体ごとに測る → 条件で選ぶ → 残ったものを数える/描く* —— がこの族です。

7 op / 4 カテゴリ(numpy と scipy のみ。台帳は `opsblob.py`、実体は `blob2d.py`):

- **connect(1)** — `blob_label`: 二値領域 → ラベル画像。4 連結 / 8 連結。
- **measure(1)** — `blob_features`: 物体ごとの 19 項目(面積・重心・外接箱・周長・等価直径・慣性主軸の長短・傾き・離心率・円形度・充填率・凸性・穴の数・縁に接するか)。
- **select(2)** — `blob_select` / `blob_select_largest`: 特徴量の範囲、または面積の順で残す。**残ったものは 1..k に振り直す**。
- **extract(3)** — `blob_region` / `blob_boundaries` / `blob_overlay`: 1 個を領域として抜く、輪郭を取る、元画像に色分けして重ねる(出口)。

## なぜ足したか —— 在庫を数えた結果

`examples/poc_cell_counting.py` が「2 次元の連結成分ラベリングと per-object の region props が facade に無い」と書きました。この repo は**在るものを見落として同じ物を作りかけた前科がある**ので、今度は 3 層すべてを引いてから決めています(2026-09-06):

| 引いた先 | 何が在ったか | なぜ代わりにならないか |
|---|---|---|
| `fullseye.ledger.label_components` / `region_props` | 連結成分とその特徴量 | **3-D 専用**。2-D を渡すと `ValueError: a 3D voxel array (ndim==3) is required` |
| `fullseye.ledger.vol_label` / `vol_region_props` | 同上(体積側の別名) | 同じ |
| `fullseye.op.circularity` / `eccentricity` / `area_center` | 形の量 | **進化 op**。画像 1 枚 → スカラ 1 個。「2 番目の物体の面積」が取れない |
| `fullseye.op.select_shape` / `blob_count` / `select_largest` | 選ぶ/数える | 同じく進化 op。つまみが `a`/`b` の 2 つで、特徴量の名前も境界値も指定できない |
| `regions_setops` / `regions_gen` | 領域の集合演算と生成 | 領域を**分ける**口が無い |
| `segmentation.watersheds_marker` | 分水嶺 | モジュールには在るが facade にも台帳にも出ていない(別件) |

`ndimage.label` 自体は op の実装の**中**に 20 か所以上あります。ただしどれも結果を画像かスカラに畳んでから返すので、利用者からは見えません。**実装が在ることと、公開経路が在ることは別**というのがこの repo で繰り返し出ている形です。

## 使う順序

op は `fullseye.ledger.<名前>` から呼べます(この族の公開経路。実体を直に触るなら `import blob2d`)。

```python
import numpy as np
import fullseye as fs

# 撮った絵の代わりに、丸い部品を 3 個と細長い切り粉を 1 本置いた場面
img = np.zeros((120, 160))
rr, cc = np.mgrid[0:120, 0:160]
for r0, c0, rad in ((30, 40, 12), (30, 100, 9), (85, 70, 15)):
    img[(rr - r0) ** 2 + (cc - c0) ** 2 <= rad * rad] = 0.9
img[100:103, 20:60] = 0.9                 # 切り粉(細長い = 落としたい)

mask = img > 0.5                          # 前景を出す(この族の外)

lab = fs.ledger.blob_label(mask)          # 1) 物体に切る(既定は 8 連結)
f = fs.ledger.blob_features(lab, spacing=0.05)     # 2) 測る(1 px = 0.05 mm)
big = fs.ledger.blob_select(lab, "area", vmin=0.5, spacing=0.05)   # 3) 0.5 mm^2 以上
parts = fs.ledger.blob_select(big, "circularity", vmin=0.85)       #    かつ丸いもの

print("測った物体:", f["n"], "-> 残った部品:", int(parts.max()))
view = fs.ledger.blob_overlay(img, parts)          # 4) 見る
```

**選ぶ前に測る必要はありません** —— `blob_select` は中で `blob_features` を呼びます。ただし何度も選ぶなら、`blob_features` を 1 回だけ呼んで自分で `np.isin` する方が速い(下の「速さ」節)。

## 押さえておく約束

### 1. ラベルは連番。穴を開けない

`blob_select` は残った物体を **1..k に振り直します**。元の番号は消えるので、必要なら選ぶ前に `blob_features(lab)["label"]` を取っておくこと。

振り直す理由は、`features["area"][k]` の `k` が何番の物体なのか呼び手が追えなくなるからです。歯抜けを許すと「ラベル番号」と「配列の添字」が別物になり、その食い違いは例外ではなく**もっともらしく間違った数値**として出ます。

### 2. 二値マスクは `blob_features` に渡せない

```python
import numpy as np
import fullseye as fs

mask = np.zeros((40, 40), bool)
mask[5:15, 5:15] = True
mask[25:35, 25:35] = True

try:
    fs.ledger.blob_features(mask)       # bool は受けない
except ValueError as exc:
    print("拒否された:", str(exc)[:60])

f = fs.ledger.blob_features(fs.ledger.blob_label(mask))   # 正しい
print("物体の数:", f["n"])               # -> 2(マスクのままなら 1 個として測る)
```

拒否するのは意地悪ではありません。マスクをそのまま測ると**別々の 2 個の細胞が 1 個の物体として測られ、2 つの中心のあいだに重心が出ます**。例外にならず、それらしい数字が返る —— この repo が型を分ける基準そのものです。

### 3. `spacing` は長さに 1 乗、面積に 2 乗。ただし添字は素通し

`spacing` は画素 1 個の大きさです。`area` には 2 乗、`perimeter` / `major` / `minor` / `equiv_diameter` には 1 乗が掛かります。**`bbox_*` と `row` / `col` は画素のまま**です —— あれは長さではなく添字だからです。

読み違いを防ぐため、`blob_features` の返り値には `units` が入っています:

```python
f = fs.blob_features(lab, spacing=0.05)
f["units"]["area"]        # 'unit^2'
f["units"]["bbox_r0"]     # 'px index'
f["units"]["angle"]       # 'rad (+col -> +row, clockwise on screen)'
```

### 4. `angle` は画面では時計回りが正

行は下向き、列は右向きです。`angle` は **+列(右)から +行(下)へ**測るので、画面で見ると時計回りが正になります。数学の慣習と符号が逆なので、図に重ねるときは向きを 1 度確かめてください。

検算は済んでいます: 長半径 40 px・短半径 15 px の楕円を 30 度に置くと、`major` 79.98(真値 80)、`minor` 29.94(真値 30)、`angle` 29.79 度、`eccentricity` 0.9273(真値 0.9270)。

## 数え方をどう選んだか(実測)

### 周長 —— 3 通り測って Crofton にした

半径 r の円板(真値 2πr):

| r | 真値 | 境界画素を数える | Serra の重み | Crofton 4 方向 |
|---|---|---|---|---|
| 10 | 62.83 | 76 (+21.0 %) | 65.94 (+4.95 %) | 65.20 (+3.77 %) |
| 20 | 125.66 | 156 (+24.1 %) | 131.88 (+4.95 %) | 127.71 (+1.63 %) |
| 40 | 251.33 | 316 (+25.7 %) | 263.76 (+4.95 %) | **252.75 (+0.56 %)** |

素朴に数えると 2 割超の過大。Serra の重み(1 / √2 / (1+√2)/2)は**大きさを変えても +4.95 % のまま**で、円板の円形度が 0.908 で頭打ちになります —— 「円らしさ 0.9 以上」で切る使い方が成り立ちません。Crofton は大きさとともに真値へ寄り、r=40 で円形度 **0.988**。

**正直に書いておく偏り**: 軸に平行な多角形では逆に小さく出ます。20×20 の正方形(真値 80)で 74.73(**−6.6 %**)、円形度は π/4 = 0.785 のところ 0.900。**角ばった物体の円形度を絶対値で語らないこと**(同じ形どうしの相対比較なら向きは保たれます)。

### 円形度の定義 —— HALCON と違う

`circularity` は **4πA/P²**(等周比)です。**HALCON の `circularity` は「面積 / 最遠点を半径とする円の面積」で別物**なので、値を突き合わせるときは定義を確かめてください。

### 充填率(`solidity`)—— 凸包は塗り直して数える

分母の凸包面積を多角形として出すと、「画素を点と見るか正方形と見るか」でどちらかへ必ずずれ、**凸な物体でも 1 になりません**(半径 40 px の円板で 0.977 か 1.025)。分子が画素の数なら分母も画素の数で揃える —— 凸包を塗り直して数えると 1.000 になります。

実測: 円板 1.000 / 正方形 1.000 / 直角三角形 1.000 / 1 画素 1.000 / 1 画素幅の線 1.000 / 三日月 0.528。

### 慣性モーメントに 1/12 を足す

画素を点ではなく 1 辺 1 の正方形として扱う補正です。これが無いと **1 画素幅の線で `minor` が 0 になり `eccentricity` が 1 に張り付きます**。補正を入れると `minor` = 1.155、`eccentricity` = 0.986。

### 4 連結か 8 連結か

既定は **8**(`ndimage.label` と HALCON `connection` の既定)。市松に並べた 2 個は 8 連結で 1 個、4 連結で 2 個になります。`poc_cell_counting` の実測では、4 連結にすると斜めに接した細胞が別々に数えられて過剰計数になりました。

## 速さ

512×512 に 153 物体(半径 4–10 px の円を 200 個、重なりあり)、2026-09-06 実測:

| | 時間 |
|---|---|
| `blob_label` | 0.7 ms |
| `blob_features` | 33.6 ms(0.22 ms/物体) |
| `blob_select("area", vmin=…)` | 中で `blob_features` を呼ぶので同程度 |

`blob_features` の内訳は凸包が 19.4 ms・周長 3.4 ms・穴の数 3.4 ms。凸包は Qhull を呼ばず monotone chain を自前で持っています(Qhull 版は 74.1 ms、**3.8 倍**遅い —— 小さな点集合を何千回も包む用途では起動費が支配的)。

**何度も選ぶなら `blob_features` を 1 回だけ**:

```python
f = fs.blob_features(lab)
keep = f["label"][(f["area"] >= 50) & (f["circularity"] >= 0.85)]
sel = np.isin(lab, keep) * lab          # 番号を振り直さない版
```

## この族で測れないこと(正直に)

- **重なった物体は 1 個になります。** 連結成分は「触れているかどうか」しか見ないので、重なった細胞や部品は割れません。割るには距離変換 + 分水嶺が要りますが、**2-D の分水嶺は facade に出ていません**(`segmentation.watersheds_marker` はモジュールに在るだけ)。`poc_cell_counting` がこの穴を測っています。
- **縁で切れた物体**は面積も周長も切れた分だけ小さく出ます。`touches_border` で捨てるか、真値の側も同じ規約で数えてください。**危ないのは規約の選択ではなく、推定と真値で違う規約を使うこと**です。
- **穴の数**は 4 連結で数えています(物体を 8 連結で取ったので、背景は 4 連結が対)。8/8 や 4/4 で数えると、斜めにつながった細い穴の数え方が物体側と食い違います。

## 関連

- 3-D の同じ操作は `label_components` / `region_props` / `vol_label` / `vol_region_props`。
- 形を「1 つの輪郭」として記述して比べるなら `opsshape2d`(楕円フーリエ記述子)。
- 領域そのものの集合演算・生成は `regions_setops` / `regions_gen`。

来歴(公開文献のみ): Rosenfeld & Pfaltz, *J. ACM* 13 (1966) 471 —— 連結成分ラベリング / Serra, *Image Analysis and Mathematical Morphology* (Academic Press, 1982) —— Crofton の公式による周長推定 / Hu, *IRE Trans. Inf. Theory* 8 (1962) 179 —— 2 次モーメントと慣性主軸 / Andrew, *Inf. Process. Lett.* 9 (1979) 216 —— monotone chain。
