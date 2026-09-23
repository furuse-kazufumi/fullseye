---
title: 'Nobody Checks a Mathematical Picture, Because It Already Looks Right — A PoC Series Where the Theorem Is the Test'
tags:
  - Python
  - NumPy
  - 数学
  - アルゴリズム
  - 画像処理
public_private: false
public_id: dc100e7ea90e9575c40b
---

> **Language**: [日本語](https://qiita.com/furuse-kazufumi/private/fe04f6eef40119913894) · **English**

# Nobody Checks a Mathematical Picture, Because It Already Looks Right — A PoC Series Where the Theorem Is the Test

<!--
  How to append (keep ja / en in the same order; never add to only one):
    1. add a row to the "Where the series is" table.
    2. add one section — picture, recipe, gates and scores, what breaks in practice, what it is bad at.
    3. figures are absolute raw.githubusercontent URLs. bump ?v=N when a figure changes.
  ★Write only what helps the reader. Not the order we happened to do things in, not the fixes.
-->

![A chain of rotating circles drawing Hokusai's wave](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/07_epicycles.gif)

*↑ As the arms go 1 → 4 → 16 → 90 → 600 → 4000, the picture gives itself away. How close it gets at each stage is known **before** anything is drawn.*

## About this series

Domain colouring. Newton basins. The Mandelbrot set. Apollonian gaskets. Phyllotactic spirals. Flow around an aerofoil. **Mathematical pictures look right. And things that look right never get checked.**

If the implementation is slightly wrong, the picture is still beautiful. The hues still wind, the boundary is still fractal, the circles still pack. **The error does not show up in the picture** — that is what makes this subject hard to write about honestly.

So the bar for adding a drawing routine was cut down to two questions:

> **(i) Is there a theorem that can act as the gate, or (ii) does an existing, independent implementation supply the truth?**
> If neither, don't write it. **Checking a formula against itself is forbidden.**

Each instalment is one drawing built to that bar, and each one ships with a **scorecard**. The code is in [fullseye](https://github.com/furuse-kazufumi/fullseye), and every figure is the output of the script itself.

## Where the series is

| # | What gets drawn | The gate (where the truth comes from) |
|---|---|---|
| 1 | [A photograph as one line, drawn by rotating circles](#1-a-photograph-as-one-line-drawn-by-rotating-circles) | Parseval's identity / the minimum spanning tree as a lower bound |
| 2 | [The complex plane as an area, not a curve](#2-the-complex-plane-as-an-area-not-a-curve) | The argument principle / Cayley 1879 / the closed form of the main cardioid |
| 3 | [Theorems that happen to be pictures](#3-theorems-that-happen-to-be-pictures) | Descartes' circle theorem / Farey neighbours / Euler's formula / Moran's equation |
| 4 | [One beat — a two-slit fringe and a print moiré are the same mathematics](#4-one-beat--a-two-slit-fringe-and-a-print-moiré-are-the-same-mathematics) | Closed-form eigenvalues / zeros of Bessel functions / the grating equation / a predicted moiré period |
| 5 | [What a picture cannot check — dynamical systems and minimal surfaces](#5-what-a-picture-cannot-check--dynamical-systems-and-minimal-surfaces) | The matrix exponential / the trace identity / exact bifurcation points / the definition H ≡ 0 |

---

## 1. A photograph as one line, drawn by rotating circles

### Recipe

```
photo → stipple → one closed line → resample to equal arc length → Fourier coefficients → redraw with rotating circles
```

Tone becomes point density (**weighted Lloyd**), a tour visits every point exactly once and returns (**TSP**), the tour is resampled to equal arc length and expanded as a **complex Fourier series**. The Fourier series of a closed curve *is* a sum of rotating arms, so it becomes a chain of pendulums with nothing added.

The lineage is TSP art (Kaplan & Bosch 2005). A tour being **closed** is exactly the condition for putting it on a Fourier series, so the two ideas were already made for each other.

| Term | In plain words |
|---|---|
| Stippling | Put more dots where it is dark; density carries the tone |
| Weighted Lloyd | Repeatedly move each point to the centroid of its own territory |
| Minimum spanning tree (MST) | The shortest tree joining all points. **A closed tour can never be shorter than this** |
| Parseval's identity | "Total energy = sum of squared coefficients". The truncation error can be computed **in advance** |

### Gates and scores

Measured on Hokusai's *Great Wave* (202×300 px) with 9,000 points. The truths used are only of three kinds — **a lower bound, a control group, and a closed form**. No special apparatus.

| Claim | Measured | Where the truth comes from | Control |
|---|---|---|---|
| Density follows tone | correlation **0.9946** | banded darkness of a ramp image | evenly spread on a uniform image (cv 0.13 vs 0.37) |
| Tour quality | **1.146 ×** MST | a closed tour cannot beat the MST | joining in coordinate order: **41.4 ×** |
| Tone reproduction | correlation **0.984** | direct comparison with the target | the same number of random lines: **+0.013** |
| Pen width | **0.900 px** | ink ≈ length × width / area | 0.890 × of target; the missing 11 % is overlap |
| Number of circles | **99.0 %** at K=64 | Parseval's identity | prediction vs measurement differ by **7e-15 px** |
| On paper | **15.57 m / 8.6 min** | converted to G-code and measured | — |

![The original print and the stipple](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/01_stipple.png)

![One line, and the control](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/03_tour.png)

*↑ Left: the single stroke (1.146 × MST). Right: the same points joined in coordinate order (41.4 ×). Same points — the difference is entirely in the joining.*

### ★ Where you will get it wrong

Four traps sit on this path. **None of them raises an exception, and the picture looks plausible in every case**, so you only find them by writing the test.

#### 1. High correlation does not mean density is proportional to darkness

Measure "density follows tone" by correlation and you get above 0.99. But **correlation only sees monotonicity.**

Weighted Lloyd produces a centroidal Voronoi tessellation, and by Gersho's conjecture the optimal point density goes like **√ρ** in the weight ρ (ρ^(d/(d+2)) in d dimensions). Pass the weight straight through and **only half of your tone range reaches the paper**.

Measure the exponent directly (the slope of `log density` against `log darkness`) and it is **0.61**. A correlation of 0.9946 and an exponent of 0.61 are not in conflict — the relation is monotone, so the correlation is high.

**If you want proportionality to tone, pass the square of the weight.** Measured, the exponent rises to 0.77 (it will not reach 1 because of the floor and the finite point count).

#### 2. The line has already got shorter before it reaches the Fourier series

When the tour is resampled to equal arc length, **a sample spacing coarser than the segments cuts the corners and shortens the line itself**. Information is lost before the transform, so any later "the prediction was right" rests on nothing.

On a tour whose segments are 2.08 px on average and **1.57 px** at the median:

| Resample points | Spacing | Length retained | Shortest representable period |
|---|---|---|---|
| 16,384 | 1.140 px | **0.935** | 2.28 px |
| 32,768 | 0.570 px | 0.967 | 1.14 px |
| 65,536 | 0.285 px | 0.984 | 0.57 px |

At 1.14 px the dense regions are unresolved and **the line shrinks by 6.5 %**. The error falls cleanly as 1/N, so the rule of thumb is to raise N **until the spacing is below the median segment length**.

#### 3. An even point count double-counts a Fourier coefficient

Taking complex coefficients over `k = −N/2 … +N/2`, **an even N makes the two ends the same coefficient**. Add both and Parseval's identity breaks (1.17e-01 at N=8, 7.5e-03 at N=512).

The nasty part is that **a highly symmetric shape hides it**: check on the outline of a square and the highest-frequency coefficient happens to be near zero, so it passes. **Sweep N over 8, 9, 16, 17, 64, 255, 256** and pin down both the coefficient count and Parseval.

#### 4. Pen width is not tuned, it is solved

While the lines do not overlap, `ink ≈ length × width / area` holds, so **you can solve for the pen width from the target darkness**.

Two caveats. First, stamping the line with integer-pixel discs makes **the width a staircase** — 0.5 / 1.0 / 1.5 px give the same picture. Fill by coverage and it becomes a continuous knob.

Second, **even the solved width undershoots**. Measured ink was **0.890 ×** the target. A union is smaller than a sum, so the measurement is always below the prediction, and **that 11 % gap is the amount of overlap**. Reading it as a measurement of overlap rather than as an error is the point.

### What it is bad at

**It is bad at ink-line drawings.** A centroidal Voronoi tessellation always fills the whole frame, so in a picture where only a few per cent of pixels are dark, most points land on white. On *Chōjū-giga* (5.5 % dark pixels) the original is unreadable. Line art should be thinned and traced, which is a different tool.

**No edge-following term was added.** With one, the fraction of line running near an edge rises from 0.421 to 0.530, but the tone correlation drops from 0.911 to 0.772 and the density contrast from 6.5 to 2.4 — **both get worse**. In this picture the edges are already dark, so raising the tone contrast improves both (the edge area fraction is 0.235, so 0.235 of the line would sit on edges by chance; tone alone gives 0.475, already twice that).

### Run it

```bash
pip install -U fullseye
py -3.11 examples/poc_one_stroke_epicycles.py \
    --image my_photo.jpg --points 12000 --out out/mine
```

Point count scales as pixels × points. Start at `--points 3000` to see the shape, then raise it.

```python
import fullseye as fs

img  = fs.read_image("photo.png")
pts  = fs.ledger.stipple_points_from_image(img, 9000, gamma=1.6)  # dots where it is dark
tour = fs.ledger.stroke_tour_closed(pts)                           # one closed line
err  = fs.ledger.stroke_tone_error(img, tour)                      # what was preserved, as a number
print(err["corr"], err["length_px"])
```

---

## 2. The complex plane as an area, not a curve

### Recipe

```
a rational f(z) → evaluate over an area → domain colouring / basins / escape time → score against a truth outside the picture
```

Visualising complex analysis needs different tools **on a curve** (integrals, winding numbers, Laurent coefficients, conformal maps) and **over an area** (the value field, domain colouring, basins). This instalment is the second kind.

![Domain colouring, Newton basins, escape time, flow around an aerofoil](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/03_newton.png?v=1)

*↑ None of these can be checked by looking. Every score below comes from outside the picture.*

### Gates and scores

| Claim | Measured | Value | Where the truth comes from |
|---|---|---|---|
| Argument principle | winding number | +3 / +1 / −2 | the existing `cplx_winding_number` (zeros outside the window count 0 — the control) |
| The order is readable from the picture | hue winding, **from the pixel RGB alone** | 1 / 2 / 3 / −2 | the argument principle |
| Basins of `z²−1` | agreement with the exact solution | **all 262,144 pixels**, 0 unconverged | Cayley 1879 (two half-planes) |
| Basins of a cubic | boundary pixels on the same grid | 1,026 → **13,348** (13 ×) | the case Cayley could not solve |
| Main cardioid | pixels declared interior without iterating | **0 counterexamples**, covering 90.1 % | a closed form (the fact that it is a lower bound is also a number) |
| Flow around the aerofoil | Cauchy–Riemann residual | **2.06e-04** | controls: random 1.04, conjugated 2.000 |
| Circulation is path-independent | outer / inner contour | −3.0263 / −3.0263 | Cauchy's integral theorem |
| The Kutta condition | trailing-edge speed | 22.9 → **22,020** with zero circulation | the control diverges |

**A bonus that was not in the plan**: the ratio of the lift coefficient to thin-aerofoil theory is **exactly `a/b`** — the radius of the circle over the distance to the singularity of the map — independent of angle of attack and of speed. The measured deviation is 2.2e-16, and letting the thickness go to zero recovers thin-aerofoil theory. The whole effect of thickness collapses into one number.

### ★ Where you will get it wrong

**An existing op looked broken, but the caller was.** `cplx_cr_residual` returned 0.95 on a holomorphic field and 1.04 on noise, which reads as "it does not discriminate". Then the docstring: **"rows run in the direction of increasing imaginary part."** This grid was in image order (rows going down), so the op was correctly measuring **the conjugate field**.

Breaking a convention does not raise an exception. **It returns a different quantity, plausibly.** So the discrepancy was turned into a gate rather than left as a trap — the same test now asserts both "2 when passed as is" and "≈ 0 when flipped".

(Exactly 2 only appears where the central difference is exact, i.e. polynomials of degree ≤ 2. On a general holomorphic field it comes out slightly under, by the same rounding floor — measured 1.999951.)

### What it is bad at

Escape time is cut off at an iteration limit, so near the boundary there is always a "still undecided" band that grows as you raise the limit. The closed-form interior test is a **lower bound** and does not cover the whole interior (90.1 % measured). Domain colouring gives you the order of a zero but **not its position** — that is the job of the op that counts winding numbers.

### The first line to run

```python
import fullseye as fs

z = fs.cplx_plane_grid((-2.0, 1.0), (-1.5, 1.5), (512, 512))
basins = fs.cplx_newton_basins((1.0, 0.0, -1.0), shape=(512, 512))  # z^2 - 1
print("unconverged:", int((basins < 0).sum()))          # Cayley's exact solution says 0
```

---

## 3. Theorems that happen to be pictures

### Recipe

```
a curvature quadruple / Farey denominators / the golden angle / IFS maps / a curve order → a picture
                                   ↓
              then check from the theorem's side, without looking at the picture
```

Apollonian gaskets, Ford circles, geodesic domes, phyllotactic spirals, IFS attractors, space-filling curves. **A slightly wrong implementation still packs circles, still spirals, and still looks fractal.**

![An Apollonian gasket](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/01_apollonian.png?v=1)

### Gates and scores

| Claim | Measured | Value | Where the truth comes from |
|---|---|---|---|
| Descartes' circle theorem | relative error of `(Σk)² − 2Σk²` | **below 1e-13** (all tangent quadruples of the 164 circles at depth 4) | the theorem |
| Integral packing | deviation of curvatures from integers | **0** | Lagarias–Mallows–Wilks |
| Farey adjacency | disagreements between tangency and `\|ps − qr\| = 1` | **0 of 1,081 pairs** (47 circles up to denominator 12) | an identity in integers |
| Ford circle count | `\|F_n\|` | matches | `1 + Σφ(k)` (Euler's totient) |
| Geodesic dome | degree-5 vertices | **exactly 12** at f = 1, 2, 3, 4, 6 | `V − E + F = 2` |
| Phyllotaxis | peaks of the index gap that are Fibonacci | golden angle **7/7**; 137.0° 2/7; 90° 2/7 | the Fibonacci numbers |
| IFS dimension | similarity vs box counting | 1.5850 (closed form) / 1.6164 (boxes) | Moran's equation `Σrᵢᵈ = 1` |
| Space-filling curve | visits 4ⁿ cells once, unit steps | holds for all four kinds | being a permutation |
| Locality | mean distance at k=32 | Hilbert 6.38 / raster 16.07 | `√32 = 5.66` / `32` |

**★ This is the point of the instalment.** The dome's vertex degrees are counted by **a different, existing implementation** (`conngraph.graph_degree_table`). Counting them yourself and agreeing with yourself proves nothing.

Descartes' theorem is set up the same way. Generation uses the reflection `k' = 2(k₁+k₂+k₃) − k₄`, so tangency is **re-discovered from distances** before being fed to the theorem — which makes the centre calculation part of what is being tested.

Then the integral packing. A gasket seeded with `(−1, 2, 2, 3)` has **integer curvatures for ever**. Drift even slightly and the integers break — **an error a picture can never show.**

### ★ Where you will get it wrong

**Two defects were found in the tests themselves.**

1. `pytest.raises(match="similarit")` **always passes, because it matches the op's own name `ifs_similarity_dimension`.** On top of that the preset name was wrong (`"fern"`; the correct one is `"barnsley_fern"`), so the test was watching an unknown-preset rejection and calling it a pass. Checking *that* something was rejected without checking **why** gets you this.
2. Declaring the output type as `points` tripped the type-contract gate. `points` is **(N,3) in three dimensions**; a list of 2-D points is `pairs`. The names are close enough to swap by accident.

**And a figure exposed a blind spot in the numeric tests.** The dome figure rasterised one triangle at a time, so each call normalised to its own bounding box and the result was "a pile of lines each stretched across the whole frame". **All 20 numeric checks passed** — there was no way to notice before opening the picture.

### What it is bad at

The Apollonian gasket grows as **a power of 3** in `depth` (118,100 circles at depth 10). Ford circles shrink as the square of the denominator, so past denominator 30 most of them are under a pixel. The IFS chaos game plots points, so **fine gaps need more points to fill** (which is why the box-counting dimension comes out above the closed form). Moran's equation **applies only to similarities** — Barnsley's fern, affine but not similar, is refused.

### The first line to run

```python
import fullseye as fs

t = fs.ledger.circle_packing_apollonian(curvatures=(-1, 2, 2, 3), depth=4)
print(len(t["x"]), "circles / still integral:",
      abs(t["curvature"] - t["curvature"].round()).max())

pts  = fs.ledger.phyllotaxis_pattern(n_points=800)
gaps = fs.ledger.neighbour_index_gaps(pts, k=6)
print("peaks of the index gap:", gaps.argsort()[::-1][:5])   # 8, 13, 21, ... at the golden angle
```

---

## 4. One beat — a two-slit fringe and a print moiré are the same mathematics

### Recipe

```
membrane eigenmodes / two slits / a diffraction grating      ┐
                                                             ├→ both are "the difference of two frequency vectors"
two superposed halftone screens / engraving / hatching / mosaic ┘
```

A two-slit fringe and the moiré of two superposed halftone screens live in different textbook chapters. **There is only one formula.** This instalment checks that one formula from both ends.

![Membrane eigenmodes and their nodal lines](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/01_membrane.png?v=1)

*↑ The mode shape is signed ([-1, 1]): the phase flips across a nodal line, so calling it an `image2d` would throw the antinode phase away.*

### Gates and scores

| Claim | Measured | Value | Where the truth comes from |
|---|---|---|---|
| Rectangular membrane eigenvalues | max difference from `π²(m²+n²)` | **0.00e+00** | the closed form, degeneracies included |
| Nodal line count | (m,n)=(3,4), vertical / horizontal | 2 / 3 | `m−1` / `n−1` (integers) |
| Circular membrane nodal circles | radii | agree | **the zeros of `J₀`** over k |
| Two slits | measured period / `λD/d` | 0.998–1.003 over four settings | **a different op** measures it back |
| Diffraction grating | wavelength recovered by an existing op | **550.000000 nm** | round trip through `grating_wavelengths` |
| Even orders vanish | orders seen | −3, −1, 0, 1, 3 | the Fourier coefficients of a square wave vanish at even harmonics |
| 3rd / 1st intensity ratio | ratio | 0.1140 | `sinc(m/2)²` → 1/9 |
| Moiré period | measured / **predicted before drawing** | 0.948–0.986 | the closed form `1/(2 f sin(Δ/2))` |
| Halftone preserves density | difference through a four-period window | **0.0517** | only the tone scale was discarded |
| Engraving | ink coverage vs `w/d` | **0.0000** over four tones | the closed form |
| Hatch direction | offset against a 30° grating | **0.3°** | the existing `structure_tensor_orientation` |
| Lloyd | energy, iteration 0 → 16 | 2,782,566 → 1,491,442 | the existing `stipple_energy` measures it (monotone) |
| Cell mean | cells where the minimum is not the mean | **0** (exhaustive) | L2 optimality |

### ★ Two things I misread, both of them the measurement

**The beat is at low frequency.** Take the FFT `argmax` without restricting the search band and you get **16.7 px = the screen's own period 1/f** at every angle, which reads as "the prediction is nowhere near".

**Hatch strokes are at high frequency.** Without a lower cut you pick up not the strokes but the **envelope of where the ink went** (the same 24 px as the original grating), and the direction looks 90° off.

In both cases the op was right and **the defect was in how it was measured**. A spectrum always has several peaks, and `argmax` returns the strongest one, not the one you are looking for. Worse, what comes back is a plausible number — no exception, no NaN, just **a different quantity, quietly**.

### A correction about Chladni figures

The familiar `cos·cos − cos·cos` is the solution for a **membrane, not a plate**. A real Chladni plate obeys the **biharmonic** equation; the sand collects on nodal lines in both pictures, but the frequency ratios do not match. This layer says membrane and scores only against membrane truths (closed-form eigenvalues, Bessel zeros).

And one more: the **nodal circles** of a circular membrane sit at the zeros of `J₀`. The zeros of `J′₀` are the **antinodes**. Swap them and a correct op looks broken — which is what happened here, once.

### What it is bad at

`wave_two_slit` is the Fraunhofer far field; the near field and the Fresnel region are a different op's job. Membrane modes are the **analytic solutions for a rectangle and a disc** only — no arbitrary boundary. `wave_fringe_period` returns **one dominant period**, so on an image with several superposed periods it sees only the strongest. The moiré prediction is for **two screens of the same kind**; three or more plates, and second-order beats from dot-shape differences, are not in it. `hatch_field` can hold only one direction per pixel, so at crossings and junctions the direction is arbitrary — whether to trust it is reported by the **coherence**, not the orientation.

### The first line to run

```python
import fullseye as fs

# The moiré period is known before you print
p = fs.ledger.halftone_moire_period(lpi_a=60.0, angle_a_deg=45.0,
                                    lpi_b=60.0, angle_b_deg=75.0, pixel_um=25.4)
print("moire period %.2f px / direction %.1f deg" % (p["period_px"][0], p["angle_deg"][0]))

# The fringe period is measured back by a different op from the one that drew it
img = fs.wave_two_slit(wavelength_nm=550.0, slit_sep_um=200.0,
                       distance_mm=200.0, shape=(64, 1024), pixel_um=5.0)
print("measured %.2f px / lambda*D/d = %.2f px"
      % (fs.wave_fringe_period(img), 0.55 * 200e3 / (200.0 * 5.0)))
```

---

## 5. What a picture cannot check — dynamical systems and minimal surfaces

### Recipe

```
a named vector field → integrate → sections, exponents, bifurcations, dimensions
exact parametrisations of minimal surfaces → a mesh → let a different op measure the mean curvature
```

**A Lorenz plot is the same butterfly whether the integrator is 1st or 4th order.** A minimal surface looks smooth whether or not its mean curvature vanishes. In this instalment, looking gets you nothing at all.

![The logistic orbit diagram](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/04_bifurcation.png?v=1)

### Gates and scores

| Claim | Measured | Value | Where the truth comes from |
|---|---|---|---|
| Order of RK4 | error ratio per halving | **16.0 / 16.0 / 16.0** | `expm(At)x₀` is the exact solution |
| Order of Euler (control) | the same ratio | 2.08 / 2.04 / 2.02 | first order |
| Error at the same step | dt = 0.01 | 2.02e-02 vs **3.33e-10** | orders of magnitude apart |
| **The trace identity** | `Σλ − (−(σ+1+β))` | **2.57e-06** | exact, and independent of how λ was produced |
| Largest Lyapunov exponent | λ₁ | 0.9142 | published 0.906 |
| Conservative control | `Σλ` of a harmonic oscillator | 4.87e-15 | 0 |
| First bifurcation | r | 2.999401 | **3** (exact) |
| Second bifurcation | r | 3.449260 | **1+√6 = 3.449490** |
| Feigenbaum δ | `(r₂−r₁)/(r₃−r₂)` | 4.7485 | 4.6692 |
| **Field divergence** | existing `piv_divergence` vs `tr(A)` | under 1e-6 in all four cases | exact for a linear system |
| Field vorticity | existing `piv_vorticity` vs `A₁₀−A₀₁` | agrees | exact for a linear system |
| Tube mesh | volume / `2π²Rr²` | 0.99667 | the analytic torus |
| Tube mesh | area / `4π²Rr` | 0.99928 | the same |
| **Minimal surfaces** | median `\|H\|` over four families | 0.00002–0.00014 | **0** — the definition itself |
| Controls | `\|H\|` of a unit sphere / cylinder | **1.00004 / 0.50000** | 1.0 / 0.5 (not minimal) |
| Isometric bending | spread in area | 17.6738–17.6756 | unchanged |
| Gyroid | volume fraction at 48³/64³/96³ | 0.499928 / 0.499981 / 0.499991 | 0.5 by the body-centred symmetry |

**★ The examiner comes from a different family.** `ode_vector_field_grid` returns a `flow2d`, so the **existing PIV (particle image velocimetry) ops** — `piv_divergence`, `piv_vorticity` — consume it directly. They know nothing about this family, which makes them an independent examiner for "the field is right". For a linear system the divergence is exactly `tr(A)` and the vorticity exactly `A₁₀ − A₀₁`.

**For minimal surfaces, the definition is the gate.** "Mean curvature H vanishes everywhere" is measured by the existing `vertex_curvature` — so the claim "this is a minimal surface" is **scored by an op that does not know how it was built**. The controls come out at 1.00004 (unit sphere) and 0.50000 (unit cylinder), which is also the evidence that the gate is not a pass-through.

### Residuals are not hidden

**In both cases the cause was located by measurement before anything was written down.**

**(1) A bifurcation point always looks slightly early.** Convergence at a bifurcation is **algebraic**, not geometric, so a finite burn-in never arrives (δ is biased the same way, 4.7485 against 4.6692, 1.7 %). So the gate is not "the error is small" but **"lengthening the burn-in shrinks it by what you left on the table"** — 2,000 → 20,000 shrinks it **10.9 ×**. That, not the size of the error, is the evidence that the residual is the measurement and not the map.

**(2) The correlation-dimension bias was not the sample count.** A circle gives 1.0061 and a Cantor set 0.6408 (true value log2/log3 = 0.6309), but a filled square gives 1.8789 against a true value of 2. The first suspect — too few points — was **wrong**: 400 → 1,500 → 3,000 points gives 1.8825 / 1.8789 / 1.8709, if anything going down.

The cause is **the radius window over which the power law is read**. The default is the 1st–25th percentile of pair distances, and on a *bounded* set the upper end runs into the boundary, where the correlation sum saturates and flattens the slope. Narrow the window towards small `r` and the estimate walks to 1.887 → 1.947 → **2.050**.

> "Finite sample" and "numerical error" fit anything, which is exactly why writing one **stops the investigation**. An explanation that fits and an explanation that is right are different things, and only the right one tells you which knob fixes it. Here it was `r_lo` / `r_hi`, not `max_points`.

The gyroid is treated the same way. At `level = 0` the field is odd under the body-centred inversion, so the volume fraction is exactly 1/2 by symmetry, independent of the grid. But Schoen's gyroid has `H = 0`, and **the nodal approximation keeps a residual** (`|H|` over the principal-curvature scale = **0.1250**). It is a scaffold and a picture, not a claim of minimality.

### ★ Where you will get it wrong

**A function whose return *type* depends on an argument cannot go in a typed ledger.** `gyroid_isosurface(..., thickness=...)` returned a voxel volume with `thickness` and a mesh without it, but only one output type can be declared — so **either declaration is a lie**. It was split into two ops.

Splitting it paid off: the solid form **dropped its scikit-image dependency** and now runs on bare numpy.

One more. `ode_vector_field_grid` first returned `(H, W, 2)` and was caught by the type checker. That layout reads more naturally, but `flow2d` is an existing type with an existing predicate and existing consumers, so returning the transpose is a type lie. **Matching the existing vocabulary beat readability** — and as a result ten existing ops downstream connected for free.

### What it is bad at

**A system is named, or given as coefficients; `callable` is not accepted** — a typed ledger registers inputs by type, so a function cannot be one. This is not a door for arbitrary ODEs. Lyapunov exponents cover only the **systems whose tangent flow is available**; estimation from a delay embedding is not in it. The orbit diagram is for 1-D maps only. For the correlation dimension, **state the radius window when the answer matters** (the default window reads low on a bounded set, as above). Minimal surfaces are the **four closed-form families plus the gyroid** — no Plateau problem on an arbitrary boundary. The tube mesh **does not detect self-intersection** (a tube fatter than the radius of curvature passes through itself).

### The first line to run

```python
import numpy as np
import fullseye as fs

# Demonstrate the order of the integrator (the exact solution is expm(At)x0)
A, x0, T = np.array([0.0, 1.0, -1.0, 0.0]), np.array([1.0, 0.0]), 4.0
exact = np.array([np.cos(T), -np.sin(T)])
for dt in (0.04, 0.02, 0.01):
    st = fs.ode_flow_states("linear", A, x0, T, dt, "rk4")
    end = np.array([st["x0"][-1], st["x1"][-1]])
    print("dt = %.3f  error %.3e" % (dt, np.linalg.norm(end - exact)))   # 1/16 per halving

# "This is a minimal surface", scored by an op that does not know how it was built
V, F = fs.ledger.minimal_surface("catenoid", nu=90, nv=140, extent=1.2)
H = np.abs(np.asarray(fs.ledger.vertex_curvature((V, F))))
print("median |H| %.5f (the unit-sphere control is 1.0)" % np.median(H[np.isfinite(H)]))
```

---

## Sources

- Image: Katsushika Hokusai, *Under the Wave off Kanagawa* (Thirty-six Views of Mount Fuji, c. 1830–32). The Metropolitan Museum of Art Open Access release marked `isPublicDomain: true` (CC0), object 45434 / image DP130155, converted to luminance and downscaled.
- Method: Craig S. Kaplan and Robert Bosch, "TSP Art", *Computational Aesthetics* (2005).
- Point-density exponent: A. Gersho, "Asymptotically optimal block quantization", *IEEE Trans. Inform. Theory* 25(4), 1979.
- Newton basins: A. Cayley, "The Newton–Fourier imaginary problem", *Amer. J. Math.* 2, 1879.
- Circle packing: R. Descartes (1643) and F. Soddy, "The kiss precise", *Nature* 137, 1936; J. Lagarias, C. Mallows, A. Wilks, "Beyond the Descartes circle theorem", *Amer. Math. Monthly* 109, 2002.
- Ford circles: L. R. Ford, "Fractions", *Amer. Math. Monthly* 45, 1938.
- Phyllotaxis: H. Vogel, "A better way to construct the sunflower head", *Math. Biosci.* 44, 1979.
- Similarity dimension: P. A. P. Moran, "Additive functions of intervals and Hausdorff measure", *Proc. Camb. Phil. Soc.* 42, 1946.
- Membrane eigenvalues: Lord Rayleigh, *The Theory of Sound*, 1877 (Chladni's sand figures are a **plate**; what is solved here is a **membrane**).
- Two slits: T. Young, 1804.
- Vector analysis of moiré: B. Oztan, G. Sharma, R. P. Loce, "Misregistration sensitivity in clustered-dot color halftones", *J. Electronic Imaging* 17, 2008.
- Stippling and quantisation: A. Secord, "Weighted Voronoi stippling", *NPAR 2002*; S. Lloyd, "Least squares quantization in PCM", *IEEE Trans. Inf. Theory* 28, 1982.
- Dynamical systems: E. N. Lorenz, "Deterministic nonperiodic flow", *J. Atmos. Sci.* 20, 1963; O. E. Rössler, "An equation for continuous chaos", *Phys. Lett. A* 57, 1976; M. J. Feigenbaum, *J. Stat. Phys.* 19, 1978; P. Grassberger and I. Procaccia, *Phys. Rev. Lett.* 50, 1983; G. Benettin et al., *Meccanica* 15, 1980.
- Minimal surfaces: H. A. Schwarz, *Gesammelte Mathematische Abhandlungen*, 1890; A. H. Schoen, "Infinite periodic minimal surfaces without self-intersections", *NASA TN D-5541*, 1970.
- Framing a tube: R. L. Bishop, "There is more than one way to frame a curve", *Amer. Math. Monthly* 82, 1975.
