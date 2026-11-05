---
guide: dataset_conventions
dim: annotate
title: 训练数据集规范知识 —— COCO / YOLO / VOC 及外观检测中的陷阱
title_en: Training-dataset conventions — COCO / YOLO / VOC and pitfalls in visual inspection
title_zh: 训练数据集规范知识 —— COCO / YOLO / VOC 及外观检测中的陷阱
title_tw: 訓練資料集規範知識 —— COCO / YOLO / VOC 及外觀檢測中的陷阱
title_ko: 학습 데이터셋 규약 지식 — COCO / YOLO / VOC와 외관 검사의 함정
title_de: Konventionen für Trainingsdatensätze — COCO / YOLO / VOC und Fallstricke in der Sichtprüfung
title_hi: Training dataset के conventions — COCO / YOLO / VOC और visual inspection में सावधानियाँ
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: annotate, optics/scene
lang: zh
translation_of: docs/ops/annotate/guides/dataset_conventions.md
source_sha256: 8a3db79f2d8d38d41b827dc0e7131ab22a7f2276545e5eed20b95d6d3344b3ff
---

# 训练数据集规范知识 —— COCO / YOLO / VOC 及外观检测中的陷阱

fullseye 可以用 `inspection_dataset` / `optscene_instances` / `optscene_defect_mask`
输出**像素级完全准确的真值**。但真值只有**转换成**训练框架能读取的形式之后
**才能使用**。本文不是 op 的说明，而是讲述接收一侧 —— 坐标约定、面积的定义、
评价指标的特点、数据划分的做法 —— 的教材。
与 `optics/guides/mv_*.md`（2-D 成像系统）、`3d/guides/depth_sensors.md`（3-D 成像系统）
处于同样的位置，本文相当于**出口**。

---

## 1. bbox 的表示有 3 种，而 fullseye 又是另一种

**事故的 8 成出在这里。** 同一个矩形可以写成 4 种数字。

| 格式 | 排列 | 原点 | 单位 |
| --- | --- | --- | --- |
| **COCO** | `[x, y, width, height]` | 左上，从 0 开始 | 绝对 px |
| **YOLO**（Ultralytics） | `class x_center y_center width height` | 左上，从 0 开始 | **按图像宽、高归一化（0–1）** |
| **Pascal VOC**（XML） | `xmin ymin xmax ymax` | 左上 | 绝对 px，**通常按从 1 开始处理**（源自 MATLAB）。转换代码在做不做 −1 上意见分裂，所以不要轻信别人的脚本 |
| **fullseye** `optscene_instances` | `(x0, y0, x1, y1)` | 左上，从 0 开始 | 绝对 px，**包含右下角（inclusive）** |

`optscene_instances` 的 bbox **包含右下角**，因此宽度不是 `x1 − x0`，而是
`x1 − x0 + 1`。转换公式：

```python
w = x1 - x0 + 1
h = y1 - y0 + 1
coco = [x0, y0, w, h]                                   # 绝对 px
yolo = [(x0 + w / 2) / W, (y0 + h / 2) / H, w / W, h / H]   # 0-1 归一化
```

**缺陷越小，1 个像素的弄错就越致命**（§4）。

---

## 2. COCO 的内容（应当用一手资料把握的要点）

* `bbox` 是绝对坐标的 `(x, y, width, height)` ——
  对应 detectron2 的 `BoxMode.XYWH_ABS`（相对地，`XYXY_ABS` 是 `(x1,y1,x2,y2)`）。
* `segmentation` 有 3 种形态，`pycocotools` 会区分并处理它们：
  1. **多边形**（`list`）—— 每个连通分量一组 `[x1, y1, ..., xn, yn]`
  2. **非压缩 RLE**（`counts` 为 `list` 的 dict）
  3. **压缩 RLE**（`{"size": [h, w], "counts": ...}`，LEB128 变长）
* **RLE 的掩膜是列优先（column-major）。** `pycocotools.mask` 的规格就是这样规定的。
  numpy 默认是行优先，所以忘了 `np.asarray(mask, order="F")` 的话，
  掩膜会**崩坏成既不是转置也不是翻转的、莫名其妙的形状**。这种错误是悄无声息的，难以察觉。
* RLE 是“游程长度的序列”，**奇数位置必定是 0 的游程**（例 `M=[0 0 1 1 1 0 1]`
  → `counts=[2 3 1 1]`）。以 1 开头的掩膜，其 `counts` 从 `0` 开始。
* `area` 是**掩膜（或多边形）的面积**，不是 bbox 的面积。
  对于细长的划痕，它只有 bbox 面积的几分之一。§3 的 small/medium/large 判定使用的就是这个
  `area`，如果这里填入 bbox 面积，**评价就变成了另一回事**。
* `iscrowd=1` 表示“作为一群算 1 个”，在评价时受到**命中与否都不惩罚**的
  特殊对待。不明白其含义就不要设置（detectron2 的建议也是如此）。
* `category_id` 为 `[0, num_categories-1]`（detectron2 的约定）。COCO 官方数据本身是
  从 1 开始且有缺号，所以**直接把原始 COCO 当作下标会错位 1 个**。

---

## 3. 评价指标的内容（不要盲信 `mAP`）

`pycocotools` 的默认值（`cocoeval.Params`）：

| 参数 | 值 |
| --- | --- |
| IoU 阈值 | `0.50, 0.55, ..., 0.95`（10 级） |
| Recall 阈值 | `0.00 … 1.00`（101 级） |
| 面积区间 | `all` = [0, 1e10] ／ **`small` = area < 32² = 1024 px²** ／ `medium` = 32²–96² ／ `large` > 96² |
| maxDets | `1, 10, 100` |

**在外观检测中起作用的地方：**

* **`small` 的阈值 1024 px² 是绝对值。** 小于 32×32 px 的全部落入 `small`。
  检测中的微小缺陷几乎全都在这里，所以报告时不看 `AP_small` 就没有意义。
* **`maxDets=100`** —— 如果 1 张图像中有超过 100 个缺陷（粉状异物、成群的压痕），
  仅此一点就会截断 recall 的上限。在计数颗粒的用途中，保持默认值是测不出来的。
* **IoU 0.5 对小物体太严格。** 同样的绝对误差，框越小 IoU 就崩得越厉害：

  | 框的大小 | 偏 1 px | 2 px | 3 px | 4 px |
  | --- | --- | --- | --- | --- |
  | 10 × 10 px | 0.82 | 0.67 | 0.54 | **0.43（不合格）** |
  | 100 × 100 px | 0.98 | 0.96 | 0.94 | 0.92 |

  10 px 的缺陷**只偏 4 px 就会被算作“漏检”**。位置精度的问题会
  变成检出率的问题，因此对于微小缺陷，降低 IoU 阈值，或者用中心距离、
  像素 IoU（segm）来衡量，更符合实际。**不改变指标就不要得出“检出率低”的
  结论。**

---

## 4. 外观检测特有的陷阱

1. **良品没有标注。** COCO 允许“标注为 0 条的图像”，
   YOLO 也明确写着“没有目标的图像可以不放 .txt”。然而
   许多训练脚本会**悄悄丢弃空标注的图像**。一旦被丢弃，
   连 1 张良品也进不了训练，就会得到“总要报出点什么缺陷”的模型。
   **首先要数一数良品的张数是否与训练日志中的张数一致。**
2. **极端的类别不平衡。** 缺陷像素占全部像素的 10⁻⁴ 至 10⁻⁶ 量级。
   像素级 accuracy 达到 99.99% 而内容却是空的，这种结果很常见。
   **1 个数字无法区分“完美”与“什么都没输出”**，所以
   一定要分别给出对缺陷像素的召回率和误检数。
3. **划分泄漏（leakage）。** 在合成数据中，来自同一母材、同一随机数系列的多张图像
   很容易同时进入 train 和 val 两侧。即使域随机化让外观不同，
   **只要缺陷布置相同，实质上就是同一个样本**。用 `inspection_dataset` 的 `seed` 和
   缺陷标签来建立分组，**按组划分**（不要按图像划分）。
4. **合成数据的标签过于完美。** 实际数据的标注是人画的，
   边界会有几 px 的抖动，微小缺陷也会被漏标。只用完美真值训练出来的模型，
   在实际数据上评价时，**标注一侧的抖动会被算作误检**。
   sim2real 的差距不仅在于图像的外观，**也在于标签的质量**。
5. **不要丢掉 `meta`。** `inspection_dataset` 会在 `meta` 中返回照明类型、曝光、扰动量、缺陷标签。
   这些对训练不是必需的，但对**失败原因的定位**是必需的
   （“只在暗场时失败”，没有 meta 就看不出来）。

---

## 5. 从 fullseye 导出（对应表）

| 想要的东西 | 在 fullseye 中的来源 | 转换 |
| --- | --- | --- |
| 图像 | `inspection_dataset(...)["image"]` | 原样（已量化） |
| bbox | `optscene_instances(...)["bbox"]`（inclusive） | 用 §1 的公式转换为 COCO / YOLO |
| 类别 | 同上 `["kind"]` | 映射到 `category_id`。**统一为从 0 开始** |
| 实例掩膜 | 同上 `["mask"]`（H×W bool） | RLE 编码要**列优先**（§2） |
| 面积 | 同上 `["area_px"]` | 填入 COCO 的 `area`（不是 bbox 面积） |
| 语义掩膜 | `optscene_defect_mask` | 用于分割训练 |
| 深度真值 | `inspection_dataset(...)["depth_mm"]` | 单位 mm。把尺度一起传递 |
| 复现信息 | 同上 `["meta"]` | 保留在数据集的 `info` / 自定义字段中 |

---

## 6. 现有的缺口（如实说明）

* **没有导出 op。** 上面的转换目前都要手写。输出 COCO JSON / YOLO txt 的
  op（以及反方向的读取）连 1 个都没有。
* **没有分组划分的 op。** 没有用机器防止 §4-3 泄漏的手段。
* **没有模拟标签抖动的手段。** 如 §4-4 所述，真值过于完美
  本身就是一种域差距，但没有刻意模糊边界的 op。

---

## 7. 诊断表 —— 从症状到原因

| 症状 | 首先怀疑 | 确认方法 |
| --- | --- | --- |
| 似乎一张良品都没学到 | 空标注的图像在加载器中被丢掉了 | 把**训练日志中的张数**与生成张数对照 |
| 像素 accuracy 99.99% 却什么都不输出 | 类别不平衡 | **分别**给出缺陷像素的召回率和误检数 |
| val 的成绩好得过分 | 划分泄漏（同一 seed、同一缺陷布置出现在两侧） | 用 seed 和缺陷标签建立分组，**按组**重新划分并重新训练 |
| 只有小缺陷的 AP 低 | IoU 0.5 对小框太严格（§3 的表） | 改用中心距离或像素 IoU（segm）重新衡量 |
| 框全部偏移 1 px／全军覆没 | inclusive 与 exclusive 弄混、VOC 的从 1 开始 | **把转换后的 bbox 画到图像上用眼睛确认**（不要只看数字） |
| 掩膜崩坏成莫名其妙的形状 | 按行优先生成了 RLE | 用 `order="F"` 重新生成（§2） |
| 1 张图像中缺陷很多时召回率到顶 | `maxDets=100` | 提高 maxDets 重新评价 |
| 合成数据上很好，实际数据上却满是误检 | 标签质量的差异（真值过于完美） | 对几张实际数据重新标注 GT，测量边界抖动幅度并反映到合成一侧 |
| 类别编号错位 1 个 | COCO 原始数据的 `category_id` 从 1 开始且有缺号 | 输出类别列表，显式建立映射到连续编号的字典 |

---

## 出处（一手资料）

* Ultralytics — Object Detection Datasets Overview（YOLO 标签格式、归一化 xywh、从 0 开始的类别、没有目标的图像不需要 .txt） — <https://docs.ultralytics.com/datasets/detect>
* `pycocotools/mask.py` module docstring（RLE 的定义、列优先、encode/decode/merge/area/toBbox/iou/frPyObjects） — <https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/mask.py>
* `pycocotools/cocoeval.py` `Params`（iouThrs / recThrs / areaRng / areaRngLbl / maxDets、iscrowd 的特殊对待） — <https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py>
* `pycocotools/coco.py` `annToRLE`（segmentation 3 种形态的判定） — <https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/coco.py>
* detectron2 — Use Custom Datasets（`BoxMode.XYWH_ABS` / `XYXY_ABS`、segmentation 的 polygon 与压缩 RLE、`category_id` 从 0 开始、关于 `iscrowd` 的建议） — <https://detectron2.readthedocs.io/en/latest/tutorials/datasets.html>
