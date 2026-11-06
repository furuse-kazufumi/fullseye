---
guide: measurement_uncertainty
dim: math
title: Measurement uncertainty and calibration — what it takes to claim you are measuring
title_en: Measurement uncertainty and calibration — what it takes to claim you are measuring
title_zh: 测量不确定度与校准知识 —— 为了能主张“测得准”
title_tw: 量測不確定度與校正知識 —— 為了能主張「量得準」
title_ko: 측정 불확도와 교정 지식 — ‘측정되고 있다’고 주장하려면
title_de: Messunsicherheit und Kalibrierung — was nötig ist, um zu behaupten, dass man misst
title_hi: Measurement uncertainty और calibration — 'हम माप रहे हैं' कहने के लिए क्या चाहिए
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: math/stats, 2d/measure1d, 2d/subpix, 3d/metrics, 3d/regionprops, optics/imaging
lang: en
translation_of: docs/ops/math/guides/measurement_uncertainty.md
source_sha256: 47c11ae624a37fd6ddd913f984e4587fcea3fbeb5dd9798e1c835f46e8a198a9
---

# Measurement uncertainty and calibration — what it takes to claim you are measuring

fullseye has ops that measure (`measure3d` / `math_metrology` / `measure1d` / `contour`).
But **whether the measured values can be said to mean anything** is decided outside the ops.
This document is not a description of ops; it is teaching material on the conventions needed when reporting dimensions as numbers — terminology, calibration,
how to build up uncertainty. The authoritative source for the definitions of terms is the VIM (JCGM 200:2012),
and for the evaluation of uncertainty the GUM (JCGM 100:2008).

---

## 1. Terms, strictly (mix them up here and the discussion cannot stand)

VIM definitions (with clause numbers; the original is an English–French bilingual text):

| Term | VIM | Definition (gist) |
| --- | --- | --- |
| **Accuracy** (measurement accuracy) | 2.13 | Closeness of agreement between a measured value and the **true value**. **NOTE 1: this is not a quantity and is not expressed numerically** |
| **Trueness** (measurement trueness) | 2.14 | Closeness of agreement between the **average** of an **infinite number** of replicate measured values and a reference value. **Inversely related to systematic error, unrelated to random error** |
| **Precision** (measurement precision) | 2.15 | Closeness of agreement **between measured values** obtained by replicate measurements under specified conditions. Expressed numerically by standard deviation, variance or coefficient of variation |
| Error | 2.16 | Measured value − reference value |
| Systematic error | 2.17 | The component that remains constant or varies predictably in replicate measurements |
| Random error | 2.19 | The component that varies unpredictably in replicate measurements |
| Repeatability condition | 2.20 | Repetition with the same procedure, same operators, same measuring system, same conditions, same location, **over a short period** |
| Reproducibility condition | 2.24 | Repetition under conditions where **location, operators and measuring systems differ** |
| Uncertainty | 2.26 | A **non-negative parameter characterising the dispersion** of the values attributed to a measurand |
| Calibration | 2.39 | **An operation in 2 steps** (§2) |
| Metrological traceability | 2.41 | The property of being related to a reference through **a documented unbroken chain of calibrations** |

VIM 2.13 NOTE 2 drives the point home by name —
**do not use "accuracy" to mean trueness, and do not use "precision" to mean accuracy.**

Where this matters in practice:

> A sensor catalogue says "**repeatability 0.4 µm**". This is precision (2.15),
> neither accuracy nor trueness. **That the same value comes out repeatedly and that the value is correct are
> unrelated.** If you claim absolute dimensions, you separately need trueness and its basis (calibration).

(The same story is in `3d/guides/depth_sensors.md` §2.2–2.3. Some manufacturers state trueness,
and some state only precision.)

### Uncertainty is evaluated in 2 ways (GUM)

* **Type A** — evaluated from the **statistical distribution** of a series of measurements (characterised by a standard deviation).
* **Type B** — evaluated from a **probability density function** based on experience or other information.

Both are put on the same footing (standard uncertainty) before being combined.
**Expanded uncertainty** is the combined standard uncertainty multiplied by **a factor greater than 1 (the coverage factor k)**;
k is determined by the probability distribution of the output quantity and the chosen coverage probability. By custom k = 2 (about 95%) is common, but
**an expanded uncertainty that does not state k has no definite meaning.**

---

## 2. Calibration has 2 steps (it tends to be thought of as 1 step)

VIM 2.39 states explicitly that there are 2 steps:

1. Establish a relation between **the quantity values provided by measurement standards** (with uncertainties) and **the corresponding indications**
   (with uncertainties).
2. Use that information to establish **a relation for obtaining a measurement result from an indication**.

In other words —

> **"Calibrated" = the deviation is known, not that it has been fixed.**
> The measured values change only once you go as far as step 2 (applying the correction).

And a calibration certificate **always carries an uncertainty**. That uncertainty is **added** to the uncertainty of
your own measurement (VIM 2.41: "each link in the chain contributes to the uncertainty").
In principle you cannot achieve an uncertainty better than that of the standard.

---

## 3. The uncertainty budget for image-based measurement (what it contains in practice)

The terms that actually pile up to report 1 dimension:

| Type | Term | Notes |
| --- | --- | --- |
| Type A | Dispersion of **repeated imaging** of the same part in the same field of view | Measure this first. 10 repetitions are often not enough |
| Type A | Dispersion when **the workpiece is re-placed** | Measure separately from the above. This is often dominant |
| Type B | **Uncertainty on the calibration certificate** of the calibration target | Upstream in the chain |
| Type B | **Pixel quantisation** (resolution / √12 is the standard deviation of a uniform distribution) | A lower bound, not actual capability |
| Type B | **Residual of lens distortion** | Estimate from the reprojection residuals after calibration |
| Type B | **Temperature drift** | Measure the difference before and after warm-up. Metals are on the order of 10⁻⁵/K |
| Type B | **Illumination variation and edge bias** | ★ Specific to image-based measurement and among the largest |

★ **In image-based measurement, illumination is among the largest sources of uncertainty**, yet the discussion often stops at
mechanics and optics. When the illumination changes, the apparent position of an edge moves — with a threshold method by the position of the threshold,
and even with sub-pixel methods through asymmetry of the intensity gradient. **Measuring the same part with only the illumination changed,
and seeing whether the value moves,** is the quickest check.

---

## 4. Resolution ≠ precision ≠ accuracy

* Even if 1 pixel = 10 µm, that does not mean you can measure to 10 µm.
  If the edge contrast is high, sub-pixel methods can sometimes reach 1/10,
  and if it is low, the dispersion can be 1 pixel or more. **Pixel size is a guide to resolution, not precision.**
* Conversely, **do not confuse the number of displayed digits with precision**. A display in 0.001 mm does not mean an accuracy of 0.001 mm.
* The diffraction limit (Airy radius) and pixel limit returned by `optical_budget` are
  **upper limits beyond which things cannot be separated**, not achieved values.

---

## 5. Gage R&R (measurement system analysis)

A method that splits the dispersion of measurement into **repeatability** (same person, same machine = the conditions of VIM 2.20) and
**reproducibility** (person and machine change = the conditions of VIM 2.24), decomposing it into variances.

By custom, %GRR relative to the tolerance is judged as **< 10% acceptable / 10–30% conditional / > 30% unacceptable**
(this is AIAG MSA custom; no international standard sets these thresholds).

**In image-based measurement there tends to be an assumption that there is no "person", but in reality the human contribution remains**:
how the workpiece is placed, adjustment of illumination angle and intensity, setting of thresholds and parameters — these are
the "operator" variance. Even on automatic machines it enters at every changeover.

---

## 6. Calibration targets (image-based measurement)

| Target | Strength | Trap |
| --- | --- | --- |
| Checkerboard | Good corner localisation. Effective for estimating distortion | Distortion is not determined unless the corners at the edges are included. Flatness is required |
| Circle grid | Centroids are obtained stably | **Under projection, "the centroid of the circle" and "the centre of the circle" diverge** (a systematic error under perspective projection). Matters unless telecentric |
| Rings / concentric circles | Strong centre estimation | The same divergence as above remains |

* **With a planar target in 1 pose, focal length and distance are degenerate.** Vary the pose and take several images.
* The target itself needs **a calibration certificate for flatness and scale** (the chain in §2).
  A printed checkerboard is not a calibrated artefact.

---

## 7. Where fullseye stands now (honestly)

| Element | What exists now | What is missing |
| --- | --- | --- |
| Measuring | `measure3d` / `math_metrology` / `measure1d` / `contour` | **Does not return uncertainty** (returns values only) |
| Upper limit of resolution | `optical_budget` (Airy radius, pixel limit) | Usable as one Type B term |
| Calibration targets | None | **Generation** of checkerboards / circle grids (should be possible with ground truth via `optscene`) |
| Uncertainty budget | None | An op that builds up Type A / Type B and outputs expanded uncertainty |
| Gage R&R | None | An op for variance decomposition |

**If building something next**: the sound approach is to generate calibration targets with ground truth in `optscene` and make it possible to run
the closed loop calibration → correction → residual. With synthesis **the ground truth is known**,
so the trueness of the calibration procedure itself can be verified (which cannot be done on real equipment).

---

## 8. Diagnostic table — from symptom to cause

| Symptom | Suspect first | How to check |
| --- | --- | --- |
| The value moves every time even for the same part | A precision problem (Type A) | Shoot 30 times without re-placing and compute σ. Then re-place and shoot 30 times. Compare them **separately** |
| The value is stable but does not agree with other instruments | A trueness problem (systematic error) | Measure a calibrated gauge. If the difference is constant, a correction removes it |
| Values differ between morning and afternoon | Temperature drift | Measure with different warm-up times. Record the equipment and room temperatures |
| The dimension changed after adjusting the illumination | Edge bias | Vary only the illumination, measure how much the value changes, and enter it as Type B in the budget |
| Dimensions disagree only at the edges of the field | Distortion residual / edge points not included during calibration | Plot the reprojection residuals **by image position** |
| Circle centres shift slightly outward | Centroid shift of circles under perspective projection | Shoot telecentric, or estimate the centre from the circle's **contour** |
| The display is in 0.1 µm steps but it does not reproduce | Confusing displayed digits with precision | Rewrite with resolution, precision and accuracy stated separately |
| Gage R&R is poor even on an automatic machine | Human contribution from changeover, placement and parameter settings | Repeat with different operators and separate out the reproducibility component |

---

## Sources (primary)

* JCGM 200:2012 *International vocabulary of metrology (VIM), 3rd edition* —
  2.13 accuracy / 2.14 trueness / 2.15 precision / 2.16 error / 2.17 systematic /
  2.19 random / 2.20 repeatability condition / 2.24 reproducibility condition /
  2.26 uncertainty (NOTEs on Type A and Type B) / expanded uncertainty and coverage factor /
  2.39 calibration (2 steps) / 2.41 metrological traceability —
  <https://www.bipm.org/documents/20126/2071204/JCGM_200_2012.pdf>
* JCGM 100:2008 *Evaluation of measurement data — Guide to the expression of
  uncertainty in measurement (GUM)* —
  <https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf>
