---
guide: colorimetry
dim: 2d
title: Colorimetry and spectra — colour is fixed only by spectrum × illuminant × observer
title_en: Colorimetry and spectra — colour is fixed only by spectrum × illuminant × observer
title_zh: 测色与光谱知识 —— 颜色只由“光谱 × 光源 × 观察者”决定
title_tw: 測色與光譜知識 —— 顏色只由「光譜 × 光源 × 觀察者」決定
title_ko: 측색과 분광 지식 — 색은 ‘분광 × 광원 × 관찰자’로만 정해진다
title_de: Farbmetrik und Spektren — Farbe ist nur durch Spektrum × Lichtart × Beobachter bestimmt
title_hi: Colorimetry और spectra — रंग केवल spectrum × illuminant × observer से तय होता है
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: 2d/color, imgmetrics/colordiff, imgmetrics/colorspace, colortransport, optics/appearance
lang: en
translation_of: docs/ops/2d/guides/colorimetry.md
source_sha256: 5202d311d820078eb5c5f7416221be27b3c68b82e6022428f4be74614d072351
---

# Colorimetry and spectra — colour is fixed only by spectrum × illuminant × observer

fullseye does have colorimetry proper (the `imgmetrics` family: `rgb_to_lab` / `delta_e_2000` and others).
The 2-D colour ops (`trans_from_rgb` / `trans_to_rgb` / `cfa_to_rgb` / `linear_trans_color`
and others), on the other hand, are **colour-space conversions**, not colorimetry.
When visual inspection has to decide "the colour is different", looking only at RGB differences will miss somewhere, without fail.
This document is not a description of ops; it is teaching material on **the physics and conventions that come before them**.
It sits in the same position as `optics/guides/mv_*.md` (imaging chain), `3d/guides/depth_sensors.md` (depth) and
`annotate/guides/dataset_conventions.md` (output side).

---

## 1. The defining equation of colour (everything follows from here)

An object colour is **not determined by the object alone**. The tristimulus values are integrals of a product of 3 factors:

```
X = k ∫ S(λ) · R(λ) · x̄(λ) dλ
Y = k ∫ S(λ) · R(λ) · ȳ(λ) dλ
Z = k ∫ S(λ) · R(λ) · z̄(λ) dλ

S(λ) = spectral power distribution of the illuminant   R(λ) = spectral reflectance of the object   x̄ȳz̄ = colour-matching functions (observer)
k is normalised so that Y = 100 for a perfect diffuse reflector
```

**Anything not in this equation cannot determine colour.** In other words:

* **Change the illuminant and the colour changes** (even for the same object).
* **Change the observer and the colour changes** — the CIE 1931 **2° standard observer** and the CIE 1964 **10° standard observer**
  are different things. Inspection fields of view are wide, so there are situations where the 10° observer is used. **Lab values
  that do not state which observer they were measured with cannot be compared.**
* **Camera RGB is not the output of this equation** (§4).

---

## 2. Standard illuminants — the name and the substance disagree

| Symbol | Substance | Correlated colour temperature |
| --- | --- | --- |
| **D65** | Average daylight (the D series was defined statistically from measurements in 1964) | **about 6504 K** |
| D50 | Reference for printing and graphic arts | about 5003 K |
| A | Tungsten lamp (blackbody) | 2856 K |
| F1–F12 | Fluorescent lamps (12 types) | Depends on the type |

**The correlated colour temperature of D65 is not exactly 6500 K** because the estimated value of the constant c₂ in Planck's law
was revised after the standard was fixed. The name has stayed at 6500.

And what matters is this — **neither the D series nor the F series can in practice be reproduced artificially to any real degree**
(they are mathematically defined distributions, not real light sources). Furthermore:

> **LEDs fit neither the D series nor the F series.**

Illumination for visual inspection is now almost entirely LED. That means **looking up a table of standard illuminants will not give you the S(λ) on the shop floor**.
Measuring with a spectroradiometer, or using the manufacturer's spectral data, is the only reliable route.

---

## 3. Metamerism — the landmine most often stepped on in inspection

There exist pairs that **have different spectral reflectances R(λ) yet whose tristimulus values match under a particular illuminant**.
Such a pair is called a metameric pair.

As long as you integrate first and compare afterwards, this cannot be avoided. The moment you reduce to 3 numbers (XYZ),
the information in the infinite-dimensional R(λ) has been discarded. As a result:

* **The verdict changes between day and night** (happens in inspection booths where ambient light leaks in)
* **Visual check OK, but camera NG** (human colour-matching functions and camera sensitivity differ, §4)
* **The pass rate changed after the lighting was replaced with LEDs from another lot** (S(λ) differs slightly)

**If you want to discriminate them, the only way is to measure spectrally.** Neither RGB nor XYZ is enough.
Conversely, when someone says "we control it by colour difference", unless **which illuminant and which observer** are
fixed, that control will not reproduce.

---

## 4. A camera is not an observer

A real camera whose spectral sensitivities are a linear combination of the colour-matching functions (the **Luther–Ives condition**)
practically does not exist. Therefore:

* **A 3×3 matrix for RGB → XYZ / Lab is an approximation that holds only for that illuminant and that set of subjects.**
  Take it to another illuminant or another set of materials and systematic errors appear (camera metamerism).
* That is why **you calibrate with a colour chart**. Shoot an X-Rite ColorChecker (24 patches) or similar under
  the same lighting and the same exposure, and estimate the transform by linear (or polynomial) regression against
  the known Lab of the patches. **A ΔE computed from uncalibrated RGB is only a number.**

### Order of preprocessing (break it and colour breaks)

1. **Dark current / offset subtraction**
2. **Shading (flat-field) correction** — removes illumination non-uniformity and the lens cos⁴ fall-off
3. **White balance** — von Kries-type diagonal scaling, or more accurately the Bradford CAT
4. **Compute in linear space** — this is the key point. Averaging, resizing or interpolating without removing the sRGB gamma
   makes things **darker and muddier** (averaging in a non-linear space has no physical meaning)
5. Re-apply gamma only for display

**Saturated pixels are invalid as colour.** Clipping even 1 channel rotates the hue.
In inspection, keep a separate saturation mask and exclude those pixels from the colour-difference calculation.

---

## 5. Colour difference ΔE — which one to use

| Formula | Year | Properties |
| --- | --- | --- |
| **ΔE\*ab (CIE76)** | 1976 | Euclidean distance in Lab. Simple to implement but **not perceptually uniform** (deviates especially at high chroma) |
| **ΔE94 (CIE94)** | 1994 | Adds weights for lightness, chroma and hue. A large improvement over CIE76 |
| **ΔE00 (CIEDE2000)** | 2001 | Adds a rotation term and a grey correction on top. The most refined, but **the formula is complex** |

As a research finding, it has been reported that **the improvement from CIE76 → CIE94 is larger than the improvement
from CIE94 → CIEDE2000**. As for the contributions of the CIEDE2000 correction terms, taking the chroma-difference correction as 100,
the order is hue difference 29, rotation term 8, lightness difference 8, grey correction 6 — **the chroma-difference correction dominates**.

`kL` (the lightness weight) **is changed by application** — 1 for graphic arts and 2 for textiles is the convention.
It is a value to be decided for the object under inspection, not something to be used as the default as is.

Treat **"ΔE = 1 is the limit of discrimination" as folklore**. The actual discrimination threshold changes with hue, chroma, lightness,
background and viewing conditions. **Measure the threshold on your own objects, under your own viewing conditions, and decide it from that.**

---

## 6. Where fullseye stands now (honestly)

| Element | What exists now | What is missing |
| --- | --- | --- |
| Illuminant S(λ) | `light_spec(source=led/halogen/laser, wavelength_nm, bandwidth_nm)` — a **centre wavelength + bandwidth** model (with a catalogue of real illuminators) | Cannot hold a measured spectral distribution. No D65/A/F-series tables either |
| Reflectance R(λ) | `scene_material(albedo=...)` — scalar or RGB | **Cannot hold spectral reflectance**. So metamerism cannot be reproduced in principle |
| Observer x̄ȳz̄ | None | Colour-matching function tables for CIE 1931 2° / 1964 10° |
| Camera sensitivity | `sensor_spec(qe=...)` — **scalar QE** | QE(λ) curve, spectral transmittance of the colour filters |
| Colour-space conversion | `imgmetrics`'s `rgb_to_xyz` / `xyz_to_lab` / `rgb_to_lab` / `lab_to_rgb` — by the CIE definitions, **the white point is selectable with `white=`** (default D65 2°) | White-point **adaptation** (Bradford CAT). The inverse transform clips out-of-gamut values, so a round trip matches only inside the gamut |
| Colour difference | **`delta_e_76` / `delta_e_2000` / `delta_e_map`** — CIEDE2000 is pinned by Sharma et al.'s **34 verification pairs** (`kL` / `kC` / `kH` can be passed) | ΔE94. Spectrum-based colour difference |

How to use the metrics themselves (the `data_range` trap, implementation differences in SSIM, a template for attaching conditions to a report) is
split out into `imgmetrics/guides/image_difference_metrics.md`.

### ★ The same conversion exists 3 times — same name, different scale

fullseye has RGB → L\*a\*b\* **3 times**:

| Where | Implementation | Scale / precision |
| --- | --- | --- |
| `imgmetrics.rgb_to_lab` | CIE definition (sRGB primaries, selectable white point) | float, **L\* is 0–100**. **This is the correct one** |
| `color_pca.trans_from_rgb(img, "lab")` | **Delegates** to the above | Same values |
| `trans_from_rgb` in the op registry (`backends_color`) | OpenCV | 8-bit scale: **quantised to uint8** before conversion, then divided by 255 |

An inconsistency found while writing this document was exactly this —
`color_pca.trans_from_rgb()` accepted only `hsv` / `yuv` / `gray`, and passing `"lab"` or
`"xyz"` raised `ValueError`. **The correct implementation already existed in `imgmetrics`,
but there was no path from the colour-space conversion entry point to reach it.**

The fix was not "write one more implementation" but **delegation**. Holding two sets of matrices and transfer functions means that
when only one of them is fixed, **a different colour comes out without any exception** (`imgmetrics` itself delegates
the sRGB transfer function to `gfx2d` for the same reason).

Verification (`tests/test_colorimetry.py`): white → `(100, 0, 0)` (residual 2e-5 — because the published
sRGB matrix is rounded to 7 digits), sRGB primaries → `(53.241, 80.092, 67.203)` and others
match the published values, **mid grey 0.5 → L\* = 53.389** (not 50), and
`color_pca` and `imgmetrics` return **identical values**.

---

## 7. Summary (the core of the judgement)

* **If you manage colour by numbers, fix the illuminant, observer and white point first.** A ΔE for which these are not fixed
  does not reproduce.
* **An RGB difference is not a colour difference.** It becomes a colour difference only after calibration with a colour chart.
* **Do not try to separate things with different spectra using 3 numbers.** That is metamerism, and it
  collapses the moment the lighting changes. If you want to separate them, measure spectrally.
* **Compute in linear space.** An average taken without removing gamma is not a physical quantity.

---

## 8. Diagnostic table — from symptom to cause

| Symptom | Suspect first | How to check |
| --- | --- | --- |
| Visual check OK, but camera NG | Camera spectral sensitivity differs from the human one (camera metamerism) | Measure the spectral reflectance. If that is impossible, shoot a calibration chart under the same conditions and see whether the residual is large **in the neighbourhood of that colour** |
| The verdict changes between day and night / with the season | Ambient light leaks in and S(λ) is changing | Check whether it reproduces with light blocked. Enclose with a blackout curtain and compare |
| The pass rate changed after the lighting was replaced | Spectral variation of LEDs (lot-to-lot differences exist even for the same model number) | Shoot **the same reference plate** with the old and new lighting and compare the channel ratios |
| The colour changed after shrinking or averaging the image | The computation was done in gamma space | Convert back to linear, apply the same processing and compare |
| The hue rotates only in bright areas | Saturation (clipping even 1 channel rotates it) | Look at the distribution of the per-channel maxima. Count the pixels stuck at the saturation value |
| The colour differs only at the edges of the field | Shading not corrected / peripheral illumination fall-off (cos⁴) | Shoot a white plate over the full field, take a flat field, then judge again |
| The ΔE numbers do not match the feel on the shop floor | Choice of formula (still CIE76) and `kL` | Switch to ΔE94 / ΔE00 and look at the correlation with the visual ranking. Re-decide the threshold by your own discrimination experiment |
| Lab values do not match another company's | Different white point and observer (D65/D50, 2°/10°) | Confirm **the white point and observer** with the other party. If they are not stated, do not compare |

---

## Sources

* CIE Standard Illuminants (how the D series was defined, the correlated colour temperature of D65 of about 6504 K,
  the offset from the nominal value due to the c₂ revision, the D series can hardly be reproduced artificially) —
  <https://www.rp-photonics.com/cie_standard_illuminants.html> /
  <https://www.image-engineering.de/library/technotes/753-cie-standard-illuminants>
* G. Sharma, W. Wu, E. N. Dalal, *The CIEDE2000 color-difference formula:
  Implementation notes, supplementary test data, and mathematical observations* —
  <https://hajim.rochester.edu/ece/sites/gsharma/papers/CIEDE2000CRNAFeb05.pdf>
* Relative contributions of the correction terms in CIEDE2000 and CIE94, and that the improvement from CIE76 → CIE94 is
  larger than that from CIE94 → CIEDE2000 (comparative study) —
  <https://www.researchgate.net/publication/8127013_Relative_significance_of_the_terms_in_the_CIEDE2000_and_CIE94_color-difference_formulas>
* Conventional values of `kL` (graphic arts 1, textiles 2) — MATLAB `imcolordiff` —
  <https://www.mathworks.com/help/images/ref/imcolordiff.html>
