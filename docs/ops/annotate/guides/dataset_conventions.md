---
guide: dataset_conventions
dim: annotate
title: 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: annotate, optics/scene
---

# 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴

fullseye は `inspection_dataset` / `optscene_instances` / `optscene_defect_mask` で
**画素完全な真値**を吐ける。だが真値は、学習フレームワークが読める形に**変換して初めて
使える**。この文書は op の説明ではなく、その受け皿側 —— 座標規約・面積の定義・
評価指標の癖・分割の作り方 —— を書く教材である。
`optics/guides/mv_*.md`（2-D 撮像系）、`3d/guides/depth_sensors.md`（3-D 撮像系）と
同じ位置づけで、こちらは**出口**にあたる。

---

## 1. bbox の表現は 3 つあり、fullseye はさらに別

**ここが事故の 8 割**。同じ矩形が 4 通りの数字で書ける。

| 形式 | 並び | 原点 | 単位 |
| --- | --- | --- | --- |
| **COCO** | `[x, y, width, height]` | 左上、0 始まり | 絶対 px |
| **YOLO**（Ultralytics） | `class x_center y_center width height` | 左上、0 始まり | **画像幅・高さで正規化（0–1）** |
| **Pascal VOC**（XML） | `xmin ymin xmax ymax` | 左上 | 絶対 px、**1 始まりとして扱うのが通例**（MATLAB 由来）。変換コードによって −1 する / しないが割れているので、他人のスクリプトを信じない |
| **fullseye** `optscene_instances` | `(x0, y0, x1, y1)` | 左上、0 始まり | 絶対 px、**右下を含む（inclusive）** |

`optscene_instances` の bbox は**右下を含む**ので、幅は `x1 − x0` ではなく
`x1 − x0 + 1` である。変換式:

```python
w = x1 - x0 + 1
h = y1 - y0 + 1
coco = [x0, y0, w, h]                                   # 絶対 px
yolo = [(x0 + w / 2) / W, (y0 + h / 2) / H, w / W, h / H]   # 0-1 正規化
```

**1 画素の取り違えは小さな欠陥ほど致命的**になる（§4）。

---

## 2. COCO の中身（一次情報で押さえるべき点）

* `bbox` は絶対座標の `(x, y, width, height)` ——
  detectron2 の `BoxMode.XYWH_ABS` がこれにあたる（対して `XYXY_ABS` は `(x1,y1,x2,y2)`）。
* `segmentation` は 3 形態を取り、`pycocotools` はこれを見分けて処理する:
  1. **ポリゴン**（`list`）—— 連結成分ごとに `[x1, y1, ..., xn, yn]`
  2. **非圧縮 RLE**（`counts` が `list` の dict）
  3. **圧縮 RLE**（`{"size": [h, w], "counts": ...}`、LEB128 可変長）
* **RLE のマスクは列優先（column-major）**。`pycocotools.mask` の仕様がそう決めている。
  numpy の既定は行優先なので、`np.asarray(mask, order="F")` を忘れると
  **転置でも反転でもない、意味不明な形に崩れる**。これは静かに壊れるので気づきにくい。
* RLE は「区間長の並び」で、**奇数番目は必ず 0 の連長**（例 `M=[0 0 1 1 1 0 1]`
  → `counts=[2 3 1 1]`）。先頭が 1 で始まるマスクは `counts` が `0` から始まる。
* `area` は **マスク（またはポリゴン）の面積**であって bbox の面積ではない。
  細長い傷では bbox 面積の数分の一になる。§3 の small/medium/large 判定はこの
  `area` を使うので、ここを bbox 面積で埋めると**評価が別物になる**。
* `iscrowd=1` は「群れとして 1 つ」を意味し、評価時に**当たっても外れても罰しない**
  特別扱いを受ける。意味が分からないなら付けない（detectron2 の助言もそうなっている）。
* `category_id` は `[0, num_categories-1]`（detectron2 の規約）。COCO 公式データ自体は
  1 始まりで欠番もあるので、**素の COCO をそのまま添字にすると 1 つずれる**。

---

## 3. 評価指標の中身（`mAP` を鵜呑みにしない）

`pycocotools` の既定値（`cocoeval.Params`）:

| パラメータ | 値 |
| --- | --- |
| IoU 閾値 | `0.50, 0.55, ..., 0.95`（10 段） |
| Recall 閾値 | `0.00 … 1.00`（101 段） |
| 面積区分 | `all` = [0, 1e10] ／ **`small` = area < 32² = 1024 px²** ／ `medium` = 32²–96² ／ `large` > 96² |
| maxDets | `1, 10, 100` |

**外観検査でここが効く:**

* **`small` の閾値 1024 px² は絶対値**である。32×32 px 未満はすべて `small` に落ちる。
  検査系の微小欠陥はほぼ全部ここに入るので、報告するなら `AP_small` を見ないと意味がない。
* **`maxDets=100`** —— 1 枚に 100 個を超える欠陥（粉状の異物、打痕の群れ）があると、
  それだけで recall の上限が切られる。粒を数える用途では既定のままでは測れない。
* **IoU 0.5 が小物体では厳しすぎる。** 同じ絶対誤差でも小さい箱ほど IoU が崩れる:

  | 箱の大きさ | 1 px ずれ | 2 px | 3 px | 4 px |
  | --- | --- | --- | --- | --- |
  | 10 × 10 px | 0.82 | 0.67 | 0.54 | **0.43（不合格）** |
  | 100 × 100 px | 0.98 | 0.96 | 0.94 | 0.92 |

  10 px の欠陥は **4 px ずれただけで「検出漏れ」に数えられる**。位置精度の問題が
  検出率の問題に化けるので、微小欠陥では IoU 閾値を下げるか、中心距離や
  画素 IoU（segm）で測るほうが実態に合う。**指標を変えずに「検出率が低い」と
  結論づけない。**

---

## 4. 外観検査に固有の落とし穴

1. **良品にはアノテーションが無い。** COCO は「アノテーションが 0 件の画像」を許すし、
   YOLO は「対象が無い画像には .txt を置かなくてよい」と明記している。ところが
   多くの学習スクリプトは**空アノテーションの画像を黙って捨てる**。捨てられると
   良品が 1 枚も学習に入らず、「何かしら欠陥を出す」モデルになる。
   **良品の枚数が学習ログの枚数と一致しているか、最初に数える。**
2. **極端なクラス不均衡。** 欠陥画素は全画素の 10⁻⁴ 〜 10⁻⁶ のオーダー。
   画素単位の accuracy は 99.99% でも中身が空、という結果が普通に出る。
   **1 つの数字は「完璧」と「何も出していない」を区別しない**ので、
   欠陥画素に対する再現率と誤検出数を必ず別に出す。
3. **分割の漏れ（leakage）。** 合成データでは、同じ母材・同じ乱数系統から出た複数枚が
   train と val の両側に入りやすい。ドメインランダム化で見た目が違っても、
   **同じ欠陥配置なら実質同じサンプル**である。`inspection_dataset` の `seed` と
   欠陥ラベルでグループを作り、**グループ単位で分割する**（画像単位で分けない）。
4. **合成データはラベルが完璧すぎる。** 実データのアノテーションは人が引くので、
   境界が数 px 揺れ、微小欠陥は見落とされる。完璧な真値だけで学習したモデルは、
   実データで評価すると**アノテーション側の揺れを誤検出として数えられる**。
   sim2real の差は画像の見た目だけでなく、**ラベルの質にもある**。
5. **`meta` を捨てない。** `inspection_dataset` は照明種別・露光・ゆらぎ量・欠陥ラベルを
   `meta` に返す。これは学習には要らないが、**失敗の切り分け**には要る
   （「暗視野のときだけ落ちる」は meta が無いと分からない）。

---

## 5. fullseye からの書き出し（対応表）

| 欲しいもの | fullseye の出どころ | 変換 |
| --- | --- | --- |
| 画像 | `inspection_dataset(...)["image"]` | そのまま（量子化済み） |
| bbox | `optscene_instances(...)["bbox"]`（inclusive） | §1 の式で COCO / YOLO へ |
| クラス | 同 `["kind"]` | `category_id` に写す。**0 始まりに揃える** |
| インスタンスマスク | 同 `["mask"]`（H×W bool） | RLE 化は**列優先**で（§2） |
| 面積 | 同 `["area_px"]` | COCO の `area` に入れる（bbox 面積ではない） |
| 意味的マスク | `optscene_defect_mask` | セグメンテーション学習用 |
| 深度真値 | `inspection_dataset(...)["depth_mm"]` | 単位 mm。スケールを一緒に運ぶ |
| 再現情報 | 同 `["meta"]` | データセットの `info` / 独自フィールドに残す |

---

## 6. 現状の穴（正直に）

* **書き出し op が無い。** 上の変換は今すべて手書きになる。COCO JSON / YOLO txt を
  吐く op（および逆方向の読み込み）は 1 つも無い。
* **グループ分割の op が無い。** §4-3 の漏れを機械で防ぐ手立てが無い。
* **ラベルの揺れを模す手立てが無い。** §4-4 のとおり、真値が完璧すぎるのは
  それ自体がドメインギャップだが、境界を意図的にぼかす op が無い。

---

## 7. 診断表 —— 症状から原因へ

| 症状 | まず疑う | 確かめ方 |
| --- | --- | --- |
| 良品を一枚も学習していない気配 | 空アノテーションの画像がローダで落ちている | **学習ログの枚数**と生成枚数を突き合わせる |
| 画素 accuracy 99.99% なのに何も出ない | クラス不均衡 | 欠陥画素の再現率と誤検出数を**別々に**出す |
| val の成績が良すぎる | 分割の漏れ（同じ seed・同じ欠陥配置が両側にいる） | seed と欠陥ラベルでグループを作り、**グループ単位**で分け直して再学習 |
| 小さい欠陥だけ AP が低い | IoU 0.5 が小箱に厳しい（§3 の表） | 中心距離、または画素 IoU（segm）で測り直す |
| 箱が全部 1 px ずれている／全滅する | inclusive と exclusive の取り違え、VOC の 1 始まり | 変換後の bbox を**画像に描いて目で確認する**（数字だけ見ない） |
| マスクが意味不明な形に崩れる | RLE を行優先で作った | `order="F"` で作り直す（§2） |
| 1 枚に大量の欠陥があると再現率が頭打ち | `maxDets=100` | maxDets を上げて再評価 |
| 合成では良いのに実データで誤検出だらけ | ラベルの質の差（真値が完璧すぎる） | 実データの GT を数枚引き直し、境界の揺れ幅を測って合成側に反映する |
| クラス番号が 1 つずれる | COCO 素データの `category_id` は 1 始まり・欠番あり | カテゴリ一覧を出力し、連番に写す辞書を明示的に作る |

---

## 出典（一次情報）

* Ultralytics — Object Detection Datasets Overview（YOLO ラベル形式・正規化 xywh・0 始まりクラス・対象が無い画像は .txt 不要） — <https://docs.ultralytics.com/datasets/detect>
* `pycocotools/mask.py` module docstring（RLE の定義、列優先、encode/decode/merge/area/toBbox/iou/frPyObjects） — <https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/mask.py>
* `pycocotools/cocoeval.py` `Params`（iouThrs / recThrs / areaRng / areaRngLbl / maxDets、iscrowd の特別扱い） — <https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py>
* `pycocotools/coco.py` `annToRLE`（segmentation の 3 形態の判定） — <https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/coco.py>
* detectron2 — Use Custom Datasets（`BoxMode.XYWH_ABS` / `XYXY_ABS`、segmentation の polygon と圧縮 RLE、`category_id` は 0 始まり、`iscrowd` の助言） — <https://detectron2.readthedocs.io/en/latest/tutorials/datasets.html>
