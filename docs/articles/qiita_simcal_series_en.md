---
title: 'A Good Fit Is Not a Right Answer: Calibrating Physics-Model Coefficients to Real Images, Starting from Multivariate Analysis'
tags:
  - Python
  - ImageProcessing
  - Statistics
  - DesignOfExperiments
  - Simulation
public_private: false
public_id: 9f52c52064d7dfa0cf5a
---

# A Good Fit Is Not a Right Answer: Calibrating Physics-Model Coefficients to Real Images, Starting from Multivariate Analysis

> 日本語版: [実写に合わせて物理モデルの係数を決める](https://qiita.com/furuse-kazufumi/items/cf97ea24c7711e7a302d)

<!--
  How to extend this series (do the same in the ja and en articles, in the same order):
    1. Add a row to the "Where the series stands" table and remove it from "Coming next".
    2. Add one section: terms -> plain explanation -> figure -> recipe -> numbers (checked against the run log) -> limits.
    3. Put figures under docs/articles/assets/qiita_simcal_series/ and link them by absolute raw.githubusercontent URL.
       Bump ?v=N whenever a figure changes (Qiita caches images).
    4. Regenerate figures: py -3.11 tools/gen_simcal_article_figs.py
       (numbers land in numbers.json next to the figures; the text must match it and the tours' printout)
    5. Where the numbers come from: py -3.11 examples/simcal_tour.py / py -3.11 examples/simcal_checks_tour.py
  Write only what helps the reader. No development history.
-->

![The gain-illumination valley floor is a line](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/qiita_simcal_series/valley_floor_en.png?v=1)

*Hold the illumination at a fixed value, refit only the camera gain, and every result (orange) lands on the truth line gain x illumination = 900 (dashed). The image is explained equally well at every point, so the image alone cannot tell you which one is right.*

## What this is about

When a simulated image doesn't match a photograph, the natural move is to tune the model's coefficients - focal length, refractive index, film thickness, camera gain - until it does. This series started from two lines the author wrote down:

> Given a real image, it would be nice to feed the error back and adjust the coefficients the simulation uses automatically.
>
> Shouldn't that start from something like multivariate analysis?

The first line is ordinary least-squares fitting. The second one is the point: unless you first find out which coefficients the photograph can actually pin down, you have no reason to trust what the fit gives you. This article shows why, with three concrete cases.

The short version:

- A small fit residual does not mean the coefficients are right. Some combinations of coefficients cannot be separated by the images (they are confounded), and when the model is missing something, the coefficients bend to absorb it and the fit still looks good.
- Multivariate analysis catches this *before* fitting: how to choose the capture conditions (design of experiments), which coefficients actually move the image (sensitivity), and which ones move it the same way (confounding).
- Identifiability, held-out images, residual PCA, and an *absolute* chi-squared test against the noise model catch it *after* fitting.

Every example runs from tours in Fullseye, an open-source image-measurement library (<https://github.com/furuse-kazufumi/fullseye>). The numbers below were checked against the printout of:

```bash
py -3.11 examples/simcal_tour.py
py -3.11 examples/simcal_checks_tour.py
```

## Terms

| Term | In plain words | Used here for |
|---|---|---|
| knob | a model coefficient you adjust to match the images | illumination, gain, refractive index n, thickness d, focal length f |
| reduced chi^2 | residuals divided by the noise level, squared and averaged | 1 means "the residual is just noise"; 60 means 60 times the noise |
| confounding | two knobs move the image in the same way | only a combination (e.g. a product) is determined, not each knob |
| identifiability | whether the images pin a knob to a single value | if not, the fit refuses to return a value |
| holdout | images kept aside and not used for fitting | checks that the fitted model also explains images it hasn't seen |
| residual PCA | splitting the residual images into principal components | a shape above the noise means the model is missing something |

## Case 1: gain x illumination - only the product is determined

### In plain words

Two knobs make the image brighter: the light level and the camera gain. Double the light and halve the gain, and the image is identical. The images determine the product illumination x gain, and nothing else.

Obvious - yet hand both knobs to a least-squares solver and it will usually return *some* pair of values. That pair depends on where the solver started and has nothing to do with the truth.

### Figure and numbers

The opening figure fixes the illumination at 13 values from 0.4 to 4 and refits the gain each time. The truth is illumination 1.5, gain 600 (product 900). Every refitted gain lies on gain = 900 / illumination.

The next figure shows how well each of those fits explains the images. Every point sits at a reduced chi^2 of about 0.94, just under the pure-noise value of 1. Illumination 0.4 or 4 - the images can't tell the difference.

![Every point on the line fits equally well](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/qiita_simcal_series/valley_chi2_en.png?v=1)

Fullseye's fitter (`simcal_fit`) refuses to return values in this situation and reports only what is determined:

- determined combination: `illum^1 * gain^1 = 899.4` (truth 900, off by 0.06 %)
- illumination and gain separately: no values (an empty dict)
- with illumination fixed at 1.5: gain = 599.6 (truth 600)

When a knob is not determined, either fix one of them from an independent source (a light meter, a datasheet value) or change the capture so that the knob does move the image. A thin film measured at a single wavelength behaves the same way: refractive index n and thickness d are not separable, and only roughly n·d (the optical path) is determined.

## Case 2: a fit stuck at the wrong interference order passes every relative check

### In plain words

A transparent film (n = 1.46, d = 520 nm) sits on silicon, and we measure its reflectance at 31 wavelengths from 400 to 700 nm. Reflectance oscillates with wavelength, and the number of peaks depends on the thickness. The chi^2 surface has a separate valley for each interference order, and a solver that starts in the wrong place can settle in a neighbouring one.

The fit in that neighbouring valley still looks reasonable. The trouble is that most of the usual validation checks are *relative* comparisons.

### Figure and numbers

![A fit stuck one interference order away](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/qiita_simcal_series/film_orders_en.png?v=1)

Levenberg-Marquardt started from a small design (two start points) landed at n = 1.329, d = 356.5 nm (dashed), with a reduced chi^2 of 60.4. A multistart with 16 start points reached n = 1.4591, d = 520.7 nm, reduced chi^2 0.93 (solid).

Both results were then put through the six gates of `simcal_validate`, using held-out images:

| Gate | Compared against | Wrong order | Right order |
|---|---|---|---|
| 1. better than the start point | chi^2 before fitting | pass | pass |
| 2. holdout / train <= 1 + tau | error ratio, held-out vs training images | pass | pass |
| 3. better than gain + offset only | the simplest possible model | pass | pass |
| 4. bounds, priors, edges | is a value pinned to the edge of its range? | pass | pass |
| 5. knobs <= image directions | over-fitting | pass | pass |
| 6. absolute: chi^2 tail probability p >= 0.001 | the noise model | **fail** | pass |

The wrong-order fit beats its start point, does just as well on the held-out images as on the training ones (holdout reduced chi^2 53.1, *lower* than the training 60.4), and beats the trivial model. Gates 1-5 all ask "is it better than something?", so it passes all five.

Only gate 6 asks "how many times the noise is the residual?". A reduced chi^2 of 60.4 on training and 53.1 on holdout has essentially zero probability under the noise model (p < 0.001), and that is where the fit is finally rejected.

This gate has a blind spot of its own. If the noise is overestimated (say the variance is set 4 times too large), p sticks at 1 and the gate passes; the only symptom is a reduced chi^2 well below 1. The noise model has to come from a measurement of the camera (a linear camera model in the style of EMVA 1288).

## Case 3: out-of-family data shows up as a shape in residual PCA

### In plain words

A model's *family* is the set of images it can produce for any knob setting. Vignetting from a lens whose optical axis is off-centre cannot be produced by a centred cos⁴ model, whatever the knobs. That data is out of family.

The fit still returns numbers. Some knob absorbs what the model is missing and settles at a distorted value.

### Figure and numbers

A flat target was captured at four exposure levels through a lens with its axis shifted by (5, −4) px, then fitted with the centred cos⁴ model (knobs: focal length f, gain, black level):

- f = 41.75 px (truth 40): a value comes back, 4 % off
- reduced chi^2 = 31.6

![Out of family: an off-axis lens](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/qiita_simcal_series/out_of_family_maps_en.png?v=1)

From left: the captured flat, the residual divided by the noise, the first principal component of the four residual images, and the true miss (off-axis image minus the centred model). The first component matches the true miss with a correlation of 0.99.

![Residual PCA singular values](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/qiita_simcal_series/pca_singular_values_en.png?v=1)

For pure noise, the singular values stay below an edge set by random-matrix theory (the 99 % point of the Tracy-Widom distribution, 42.6 here). With the off-axis lens the first singular value is 444, more than ten times the edge. With a centred lens (in family) all four stay below it. `simcal_discrepancy` then notes "one component of structure above the noise; the uncertainties are optimistic".

Residual PCA tells you the *shape* of what is missing. Here, one look at the first component says "the vignetting centre has moved", which is what tells you whether to add an optical-axis knob to the model.

## How to use it

1. Before fitting, measure each knob's sensitivity (`simcal_screen`, a Morris screen) to find knobs that do nothing and pairs that are confounded.
2. If a combination is not determined, change the capture (more wavelengths, a test chart) or fix one knob from an independent value.
3. Fit (`simcal_fit`). Use multistart when the problem has several valleys.
4. Run the six gates on held-out images (`simcal_validate`). Keep the absolute chi^2 gate on.
5. Look at the shape of what is missing with residual PCA (`simcal_discrepancy`).

```python
import fullseye as fs
L = fs.ledger

obs = L.simcal_observe(model, images)          # pair the model with the images
screen = L.simcal_screen(obs)                  # moves the image / does nothing / only in combination
fit = L.simcal_fit(obs)                        # refuses if a knob is not determined
checked = L.simcal_validate(fit, holdout)      # the six gates
report = L.simcal_discrepancy(checked)         # residual PCA
print(L.simcal_report(report)["text"])
```

How to build `model` is shown at the top of examples/simcal_tour.py.

## Limits

- Alignment is whole-pixel only; sub-pixel shifts stay in the residual.
- The yardstick is the camera noise model. Get the noise wrong and the bounds and intervals are wrong too.
- With several valleys and too few start points the fit can land in the wrong one. It still returns values, and says so through a warning and gate 6.

## Where the series stands

| Part | Topic | Status |
|---|---|---|
| 1 | Synthetic images: undetermined coefficients, the wrong interference order, out-of-family data (this article) | published |
| 2 | Real thin-film data (public dataset): fitting n and d | planned |
| 3 | Real images through telecentric optics | planned |
| 4 | Real pixel-shift captures | planned |
| 5 | Calibrating a forward model solved by iteration (interreflection) | planned |

## Coming next

From the next part on, the images are real. First up is a public spectral-reflectance dataset of thin films: does the same recipe as Case 2 (sensitivity -> fit -> six gates -> residual PCA) hold up on measured data? After that come real telecentric and pixel-shift captures, and calibrating a forward model that is itself solved iteratively, such as interreflection.
