---
guide: dataset_conventions
dim: annotate
title: Training-dataset conventions — COCO / YOLO / VOC and pitfalls in visual inspection
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
lang: en
translation_of: docs/ops/annotate/guides/dataset_conventions.md
source_sha256: 8a3db79f2d8d38d41b827dc0e7131ab22a7f2276545e5eed20b95d6d3344b3ff
---

# Training-dataset conventions — COCO / YOLO / VOC and pitfalls in visual inspection

fullseye can emit **pixel-perfect ground truth** with `inspection_dataset` / `optscene_instances` / `optscene_defect_mask`.
But ground truth **becomes usable only once it is converted** into a form the training framework can read.
This document is not a description of ops; it is teaching material on the receiving side — coordinate conventions, the definition of area,
the quirks of evaluation metrics, how to build splits.
It sits in the same position as `optics/guides/mv_*.md` (2-D imaging chain) and `3d/guides/depth_sensors.md` (3-D imaging chain);
this one is the **exit**.

---

## 1. There are 3 bbox representations, and fullseye's is yet another

**Accidents happen here 8 times out of ten.** The same rectangle can be written as numbers in 4 ways.

| Format | Order | Origin | Unit |
| --- | --- | --- | --- |
| **COCO** | `[x, y, width, height]` | Top-left, 0-based | Absolute px |
| **YOLO** (Ultralytics) | `class x_center y_center width height` | Top-left, 0-based | **Normalised by image width and height (0–1)** |
| **Pascal VOC** (XML) | `xmin ymin xmax ymax` | Top-left | Absolute px, **customarily treated as 1-based** (inherited from MATLAB). Conversion code is split on whether to apply −1 or not, so do not trust other people's scripts |
| **fullseye** `optscene_instances` | `(x0, y0, x1, y1)` | Top-left, 0-based | Absolute px, **bottom-right included (inclusive)** |

The bbox of `optscene_instances` **includes the bottom-right**, so the width is not `x1 − x0` but
`x1 − x0 + 1`. Conversion formulas:

```python
w = x1 - x0 + 1
h = y1 - y0 + 1
coco = [x0, y0, w, h]                                   # absolute px
yolo = [(x0 + w / 2) / W, (y0 + h / 2) / H, w / W, h / H]   # 0-1 normalised
```

**A mix-up of 1 pixel is more fatal the smaller the defect** (§4).

---

## 2. What is inside COCO (points to pin down from primary sources)

* `bbox` is `(x, y, width, height)` in absolute coordinates —
  this corresponds to detectron2's `BoxMode.XYWH_ABS` (whereas `XYXY_ABS` is `(x1,y1,x2,y2)`).
* `segmentation` takes 3 forms, and `pycocotools` distinguishes and handles them:
  1. **Polygon** (`list`) — `[x1, y1, ..., xn, yn]` per connected component
  2. **Uncompressed RLE** (a dict whose `counts` is a `list`)
  3. **Compressed RLE** (`{"size": [h, w], "counts": ...}`, LEB128 variable length)
* **RLE masks are column-major.** The specification of `pycocotools.mask` decides it so.
  numpy defaults to row-major, so forgetting `np.asarray(mask, order="F")` makes the mask
  **collapse into a meaningless shape that is neither a transpose nor a flip**. This breaks silently, so it is hard to notice.
* RLE is "a sequence of run lengths", and **the odd-numbered entries are always runs of 0** (e.g. `M=[0 0 1 1 1 0 1]`
  → `counts=[2 3 1 1]`). For a mask that begins with 1, `counts` starts from `0`.
* `area` is **the area of the mask (or polygon)**, not the area of the bbox.
  For a long thin scratch it is a fraction of the bbox area. The small/medium/large classification in §3 uses this
  `area`, so filling it with the bbox area makes **the evaluation a different thing**.
* `iscrowd=1` means "1 thing as a crowd" and receives special treatment at evaluation:
  **it is not penalised whether it is hit or missed**. If you do not understand it, do not set it (detectron2's advice says the same).
* `category_id` is `[0, num_categories-1]` (detectron2's convention). The official COCO data itself is
  1-based with gaps, so **using raw COCO as indices directly shifts everything by 1**.

---

## 3. What is inside the evaluation metrics (do not take `mAP` at face value)

Defaults of `pycocotools` (`cocoeval.Params`):

| Parameter | Value |
| --- | --- |
| IoU thresholds | `0.50, 0.55, ..., 0.95` (10 steps) |
| Recall thresholds | `0.00 … 1.00` (101 steps) |
| Area ranges | `all` = [0, 1e10] / **`small` = area < 32² = 1024 px²** / `medium` = 32²–96² / `large` > 96² |
| maxDets | `1, 10, 100` |

**Where this bites in visual inspection:**

* **The `small` threshold of 1024 px² is an absolute value.** Everything under 32×32 px falls into `small`.
  Nearly all tiny defects in inspection go here, so if you report, `AP_small` is the number that means anything.
* **`maxDets=100`** — if 1 image has more than 100 defects (powdery foreign matter, clusters of dents),
  that alone caps recall. For applications that count particles, the default cannot measure it.
* **IoU 0.5 is too strict for small objects.** For the same absolute error, the smaller the box, the more the IoU collapses:

  | Box size | 1 px off | 2 px | 3 px | 4 px |
  | --- | --- | --- | --- | --- |
  | 10 × 10 px | 0.82 | 0.67 | 0.54 | **0.43 (fail)** |
  | 100 × 100 px | 0.98 | 0.96 | 0.94 | 0.92 |

  A 10 px defect **is counted as a "missed detection" when it is just 4 px off**. A position-accuracy problem
  turns into a detection-rate problem, so for tiny defects it matches reality better to lower the IoU threshold, or to measure by centre distance or
  pixel IoU (segm). **Do not conclude "the detection rate is low" without changing
  the metric.**

---

## 4. Pitfalls specific to visual inspection

1. **Good parts have no annotations.** COCO allows "images with 0 annotations", and
   YOLO states explicitly that "images without objects need no .txt". Yet
   many training scripts **silently discard images with empty annotations**. If they are discarded,
   not even 1 good image enters training, and you get a model that "always outputs some defect".
   **First, count whether the number of good images matches the number in the training log.**
2. **Extreme class imbalance.** Defect pixels are on the order of 10⁻⁴ to 10⁻⁶ of all pixels.
   A result where pixel-level accuracy is 99.99% but the content is empty comes out all the time.
   **1 number does not distinguish "perfect" from "outputs nothing"**, so
   always report recall on defect pixels and the number of false detections separately.
3. **Leakage across the split.** In synthetic data, several images from the same base material and the same random-number lineage
   easily end up on both the train and val sides. Even if domain randomisation makes them look different,
   **the same defect layout is effectively the same sample**. Form groups from the `seed` of `inspection_dataset` and
   the defect labels, and **split by group** (not by image).
4. **Synthetic data has labels that are too perfect.** Annotations on real data are drawn by people, so
   boundaries wobble by a few px and tiny defects get overlooked. A model trained only on perfect ground truth,
   when evaluated on real data, **has the wobble on the annotation side counted against it as false detections**.
   The sim2real gap is not only in the appearance of the images but **also in the quality of the labels**.
5. **Do not throw away `meta`.** `inspection_dataset` returns lighting type, exposure, amount of perturbation and defect labels
   in `meta`. This is not needed for training, but it is needed for **isolating failures**
   ("it fails only under dark field" cannot be seen without meta).

---

## 5. Exporting from fullseye (correspondence table)

| What you want | Where it comes from in fullseye | Conversion |
| --- | --- | --- |
| Image | `inspection_dataset(...)["image"]` | As is (already quantised) |
| bbox | `optscene_instances(...)["bbox"]` (inclusive) | To COCO / YOLO with the formulas in §1 |
| Class | Same, `["kind"]` | Map to `category_id`. **Align to 0-based** |
| Instance mask | Same, `["mask"]` (H×W bool) | RLE-encode **column-major** (§2) |
| Area | Same, `["area_px"]` | Put into COCO's `area` (not the bbox area) |
| Semantic mask | `optscene_defect_mask` | For segmentation training |
| Depth ground truth | `inspection_dataset(...)["depth_mm"]` | Unit mm. Carry the scale along |
| Reproduction info | Same, `["meta"]` | Keep in the dataset's `info` / custom fields |

---

## 6. Current gaps (honestly)

* **There is no export op.** All the conversions above are currently hand-written. Not even 1 op emits COCO JSON / YOLO txt
  (or reads them in the reverse direction).
* **There is no group-split op.** There is no means of preventing the leakage in §4-3 mechanically.
* **There is no means of imitating label wobble.** As in §4-4, ground truth being too perfect is
  a domain gap in itself, but there is no op that deliberately blurs boundaries.

---

## 7. Diagnostic table — from symptom to cause

| Symptom | Suspect first | How to check |
| --- | --- | --- |
| Signs that not a single good image was learned | Images with empty annotations are being dropped by the loader | Compare **the image count in the training log** with the generated count |
| Pixel accuracy 99.99% yet nothing is output | Class imbalance | Report recall on defect pixels and the number of false detections **separately** |
| val results are too good | Leakage across the split (the same seed and same defect layout on both sides) | Form groups from seed and defect labels, re-split **by group** and retrain |
| AP is low only for small defects | IoU 0.5 is strict on small boxes (table in §3) | Re-measure by centre distance or pixel IoU (segm) |
| All boxes are off by 1 px / everything fails | Inclusive vs exclusive mix-up, VOC's 1-based origin | **Draw the converted bboxes on the image and check by eye** (do not look only at numbers) |
| Masks collapse into meaningless shapes | RLE was built row-major | Rebuild with `order="F"` (§2) |
| Recall plateaus when 1 image has many defects | `maxDets=100` | Raise maxDets and re-evaluate |
| Good on synthetic data but full of false detections on real data | Difference in label quality (ground truth too perfect) | Redraw the GT for a few real images, measure the boundary wobble and reflect it on the synthetic side |
| Class numbers are off by 1 | `category_id` in raw COCO data is 1-based with gaps | Output the category list and explicitly build a dictionary mapping it to consecutive numbers |

---

## Sources (primary)

* Ultralytics — Object Detection Datasets Overview (YOLO label format, normalised xywh, 0-based classes, images without objects need no .txt) — <https://docs.ultralytics.com/datasets/detect>
* `pycocotools/mask.py` module docstring (definition of RLE, column-major, encode/decode/merge/area/toBbox/iou/frPyObjects) — <https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/mask.py>
* `pycocotools/cocoeval.py` `Params` (iouThrs / recThrs / areaRng / areaRngLbl / maxDets, special treatment of iscrowd) — <https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py>
* `pycocotools/coco.py` `annToRLE` (determining the 3 forms of segmentation) — <https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/coco.py>
* detectron2 — Use Custom Datasets (`BoxMode.XYWH_ABS` / `XYXY_ABS`, polygon and compressed RLE for segmentation, `category_id` is 0-based, advice on `iscrowd`) — <https://detectron2.readthedocs.io/en/latest/tutorials/datasets.html>
