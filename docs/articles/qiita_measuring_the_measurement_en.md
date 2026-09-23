---
title: 'I Got All 52 Tests Green, Then Checked Against the Standard’s Own Answers — 5 Failed'
tags:
  - 計測
  - 統計
  - 品質管理
  - Python
  - OSS
public_private: false
public_id: 415a59ddbab04d0b42df
---

> **Language**: 日本語(準備中) · **English**

# I Got All 52 Tests Green, Then Checked Against the Standard’s Own Answers — 5 Failed

I added nine operators for **measurement system analysis (gauge R&R) and measurement uncertainty (GUM)** to [Fullseye](https://furuse.work/), my image-metrology library.

As always, I decided **how the code would be graded before writing it**. The rule in this repo is: *either a theorem is the gate, or a separate existing implementation is the ground truth.* No test is allowed to score a formula against itself. Working that way I built 52 tests out of algebraic identities, closed forms and control groups, and got every one of them green.

Then I ran the **published values from the worked examples in the standards**.

**Five failed. Not one of the synthetic tests had.**

This article is about what those five were, why synthetic tests are *structurally* unable to find them, and how I designed the tool to **fail honestly** when the method itself breaks down.

---

## TL;DR

- Starting from **52 green tests** built on identities, closed forms and controls, the published values in the standards exposed **5 defects**
- All five were **missing specification** — a path that was never implemented, steps in the wrong order, a claim stated too broadly
- A synthetic test can only check that the code does what *I* specified. **Anything outside my specification is invisible to it, in principle**
- The sharpest tool was an **exact solution** (the sum of four uniforms is Irwin–Hall) — it let me prove that two identical-looking validation failures had **opposite causes**
- Where the law of propagation breaks down it returns `u = 0`. That is a limit of the method, not a bug, so the tool reports it **as structure, not as a warning**

---

## 1. What is actually being measured here

When an inspection line says "the spread on this dimension is 0.3 mm", **the spread of the measuring instrument is inside that 0.3 mm**. Control charts and process capability indices are all looking at the mixed number.

Gauge R&R separates it. Total variation is decomposed into

- **repeatability** — the scatter when one person measures the same part again
- **reproducibility** — the scatter added when the operator changes
- **part-to-part** — the thing you actually wanted to see

and you ask whether the act of measuring is eating the thing being measured.

GUM (the Guide to the expression of uncertainty in measurement) asks the same question about **a single measurement**. Temperature correction, the value on the calibration certificate, the quantization of the readout — you list the components, combine them, and end up able to report "this value is ±U".

Both are closed-form models defined by standards, and both carry **exact identities you can check against**. That is what qualifies them for Fullseye.

![Measurements grouped by part](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/01_scene.png)

*↑ The worked example from the standard (10 parts × 3 operators × 3 trials = 90 points), drawn the classic way: one vertical cluster per part. **How far apart the clusters sit** is the part-to-part difference (92.2 % of total variation); **how thick each cluster is** is the spread from re-measuring the same part (7.8 %). Whether the gauge is usable is decided by the ratio of those two.*

![Variance components](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/02_components.png)

*↑ Variance components for the same 90 points. Measured and published values lie on top of each other. The act of measuring (GRR) accounts for 7.8 % of total variation, the parts for 92.2 %.*

---

## 2. The 52 tests I built from synthetic data

Before implementing anything I fixed the three — and only three — sources of truth the tests were allowed to use.

### (a) Algebraic identities

In the analysis of variance the sums of squares **always** close:

```
SS_total = SS_part + SS_operator + SS_interaction + SS_error
```

This is the algebra of the decomposition itself, so it holds no matter how the variance components are derived. That means it pins down the implementation **at a layer independent of whether the estimates are right**. Measured relative difference: **1e-16**.

### (b) A separate implementation becomes the ground truth

For a balanced design, repeatability `var_repeat = MS_err` is **algebraically equal** to "the mean of `np.var(ddof=1)` over the cells". Different derivation, different code — if either breaks, they stop agreeing.

```python
cells = values.reshape(10, 3, 3)
by_cell = np.array([[np.var(cells[i, j], ddof=1) for j in range(3)] for i in range(10)])
assert abs(ev ** 2 - by_cell.mean()) < 1e-12 * by_cell.mean()   # passes
```

### (c) Data whose answer is known by construction

Plant a bias `a + b·reference` with zero noise and least squares must recover `a` and `b` **exactly, to 1e-15**.

Those three gave me 52 tests. All green. **Had I stopped there, the next five defects would never have been found.**

---

## 3. The five that failed

### ① There was no path to pool the interaction at all

Running the worked example gave repeatability **0.214435**. The published value is **0.199933** — **off by 7.3 %**.

The cause was not an arithmetic error. The procedure in the standard says:

> If the F-test on the interaction is not significant, drop the interaction term and recompute.

In this example the interaction does nothing at all (`F = 0.434`, `p = 0.9741`), so the **pooled** value is what gets published. My implementation had no pooling path; it always kept the interaction.

Recomputing with pooling:

| | measured | published | difference |
|---|---|---|---|
| repeatability EV | 0.199933 | 0.199933 | 1.8e-07 |
| reproducibility AV | 0.226838 | 0.226838 | 4.8e-07 |
| combined GRR | 0.302372 | 0.302373 | 1.5e-06 |
| part PV | 1.042327 | 1.042327 | 4.9e-07 |
| % contribution | 3.4 / 4.4 / 7.8 / 92.2 % | same | **exact match** |

![Model choice moves the answer](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/03_pooling.png)

*↑ Same 90 points. Keeping the interaction or pooling it moves EV by 7.3 %, and nothing else changes.*

**This changed one design decision.** If the choice of model moves the answer, then **which model was used has to ride along with the answer**.

```python
g = fs.ledger.msa_gauge_rr(table)
g["interaction_pooled"]   # True / False
g["interaction_p"]        # 0.9741
g["pool_alpha"]           # 0.25
```

Switch silently and the same tool returns different numbers for the same process, with **the reason recorded nowhere in the output**.

One honest note about the threshold: **0.25 is not a number the standard states**. The text only gives a qualitative instruction — *choose a high significance level* so that a real interaction is not overlooked — and 0.25 is simply what most software settled on (other implementations default to 0.05). The example table declares α = 0.05 in a footnote, so **any test that claims to reproduce that table passes 0.05 explicitly**. Whether a default is reasonable and what a published example requires are two different questions.

### ② I was reading the t-table without truncating the effective degrees of freedom

In the end-standard calibration example the coverage factor came out as **2.1132**. Published: **2.12**.

The standard requires that when the effective degrees of freedom is not an integer, you **truncate to the next lower integer immediately before** entering the t-table. Reading `ν_eff = 16.64` directly gives 2.1132; truncating to 16 first gives **2.1199**.

![The coverage-factor staircase](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/07_coverage_staircase.png)

*↑ Effective degrees of freedom need not be an integer, so the standard says to **truncate down first**, then read the table (it errs on the safe side). Against the smooth `t₀.₉₇₅(ν)`, the required procedure is a **staircase**. As ν → ∞ both converge on the normal 1.959964.*

**Both t-distribution implementations were correct; only the order of the steps differed.** I could make that diagnosis only because the published example also prints the intermediate result (`ν_eff = 16.7`).

The uncertainty budget itself reproduces too:

| component | measured (nm) | published (nm) |
|---|---|---|
| standard | 25 | 25 |
| mean of readings | 5.8 | 5.8 |
| comparator ① | 3.9 | 3.9 |
| comparator ② | 6.7 | 6.7 |
| difference in expansion coefficient | **2.9** | 2.9 |
| temperature difference | **16.68** | 16.6 |

The last two arrive in units of `1/°C` and `°C`; they **only become nanometres after the sensitivity coefficient is applied**. Getting those right means the handling of sensitivity coefficients is right as well.

### ③ A claim in my own docstring was false

I had written this in the description of `gum_propagate`:

> Treating correlated quantities as independent **underestimates** the uncertainty.

It is a commonly repeated statement. **And it is false.**

In the example that derives resistance and reactance simultaneously from voltage, current and phase (all three quantities correlated), dropping the correlation matrix gives:

| | with correlation | without | |
|---|---|---|---|
| resistance `u_c(R)` | 0.0702 | **0.1945** | **2.8× overestimate** |
| reactance `u_c(X)` | 0.2961 | 0.2009 | underestimate |
| impedance `u_c(Z)` | 0.2367 | 0.2041 | underestimate |

![Which way the error goes](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/08_correlation_sweep.png)

*↑ Three quantities derived from one set of observations. Drop the correlation and the direction of the error flips depending on which quantity you look at.*

**From one and the same data, the direction reverses between quantities.** It follows from the product of the sign of the sensitivity coefficient and the sign of the correlation, so in hindsight it is obvious — but "you can skip it, it errs on the safe side" means **reporting an uncertainty nearly three times too large** for the resistance.

I rewrote the docstring around the measurement. This is the shape of defect where **your own prose is refuted by the standard's example**.

### ④ The Monte Carlo was linear-only, so it could not show why it exists

GUM has a Supplement 1 that propagates the distributions themselves by Monte Carlo. **Why would anyone need that?** Because there are situations where the law of propagation — a first-order approximation — does not hold.

But my `gum_monte_carlo` only handled the linear model `y = Σ cᵢxᵢ`. For a linear model it agrees with the law of propagation by construction, so it **cannot reproduce the situations where they disagree**. It only half-deserved the name "independent check".

I extended it to sums of powers, `y = Σ cᵢ (xᵢ + εᵢ)^{pᵢ}`. It does not take an arbitrary callable because an operator on the ledger has to be **declarative** (a callable is not something the type system can carry). That is still enough to express the non-linear example in the standard.

### ⑤ "The position is unstable" was not restricted to symmetric distributions

This is number five, but it was the last one found. It comes later in the article.

---

## 4. Failing honestly

Take the comparison loss `δY = X₁² + X₂²` (each with `u = 0.005`), evaluated at `x₁ = x₂ = 0`.

The sensitivity coefficients are `cᵢ = ∂δy/∂xᵢ = 2xᵢ`, so **both are zero**. The law of propagation dutifully returns

```
u_c = 0,  95 % interval = [0, 0]
```

The inputs are uncertain; the output has no uncertainty at all.

**This is not an implementation error.** It is the method's own limit: a first-order approximation loses all of its information at a stationary point. In the same situation Monte Carlo returns `δy = 50×10⁻⁶ / u = 50×10⁻⁶ / [0, 150×10⁻⁶]` — matching the published value.

![Where the law of propagation breaks](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/11_breakdown.png)

*↑ Move the evaluation point and near the extremum the propagated interval contains **negative loss**, which is physically impossible. Move away and the two approaches converge.*

![The true distribution at the stationary point](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/10_stationary_density.png)

*↑ At `x₁ = x₂ = 0`, `X₁²+X₂²` is **`u²χ²₂` — an exponential distribution with mean `2u²`**: strongly asymmetric with its shoulder at the origin, and its 95 % point is the closed form **`2u²ln20 = 149.79×10⁻⁶`** (the published value is 150). The law of propagation, with `c = 2x₁` equal to zero, can only return the single point at the origin.*

**And the breakdown is not continuous.**

![From breakdown to catching up](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/12_breakdown_movie.gif)

*↑ The evaluation point `x₁` moving from 0 to 0.026 (random seed fixed). At the left edge the true distribution is exponential and the propagated interval **collapses to a point**. Move a little and the interval instead **extends into negative loss**. Move further and the true distribution approaches normal, and the two finally overlap — **three distinct stages**.*

| evaluation point | law of propagation | Monte Carlo |
|---|---|---|
| x₁ = 0.000 | `[0, 0]` ← breakdown | `[0, 149]` |
| x₁ = 0.010 | `[−96, +296]` ← **negative loss** | `[0, 366]` |
| x₁ = 0.050 | `[1520, 3480]` | `[1588, 3543]` |

**The problem is that returning `u = 0` silently reads, to the caller, as "the measurement was perfect".**

It is not an exception — as a law-of-propagation calculation it is correct. It is not a warning either — warnings get swallowed and disappear into logs. **It travels with the result.**

```python
b = fs.ledger.gum_propagate({"u": [0.005, 0.005], "sensitivity": [0.0, 0.0]})
b["u_combined"]        # 0.0
b["guf_valid"]         # False
b["invalid_reasons"]   # ['stationary_point']
```

There are two detectors: the **stationary point**, where every sensitivity coefficient is zero, and the **unrealizable interval**, where the interval leaves the domain.

The second one carries a design decision. **It only runs when the caller supplies bounds.** "It's a loss, so it can't be negative" is knowledge only the caller has; assuming a lower bound of 0 by default would produce false positives on quantities that legitimately go negative (deviations, temperature differences).

And to be clear, **these two detection conditions are my own judgement**. What the standard enumerates are its three linear and five non-linear conditions of applicability; the two I implemented are what it **looks like from the outside** when those conditions break. The docstring says so.

---

## 5. An exact solution separated two identical failures

The standard also specifies a procedure for **validating** the law of propagation against Monte Carlo: form a numerical tolerance `δ` from expressing `u(y)` to `ndig` digits, and if the difference at **both endpoints of the coverage interval** is within `δ`, the validation passes.

On the additive model (four inputs with `u = 1`), both normal and rectangular inputs pass at `ndig = 2` and fail at `ndig = 3`.

**They look like the same failure. This is where the exact solution earned its keep.**

Each uniform input with `u = 1` is `U(−√3, √3)`. The sum of four is a scaled **Irwin–Hall(4)**, whose CDF on `s ∈ [0,1]` is `F(s) = s⁴/24` (and `F(1) = 0.0417 > 0.025`, so the 2.5 % point really is on that branch). Inverting:

```
y₂.₅% = √3 (2 · 0.6^(1/4) − 4) = −3.879407
```

**A ground truth with no random numbers anywhere in it.** The published "MCM interval [−3.88, +3.88]" turns out to be **not a Monte Carlo product at all, but a rounded exact quantile**.

With that, the two failures separate:

| example | why `ndig=3` fails |
|---|---|
| **normal** input | the law of propagation is **exactly right**; what fails is the jitter in the **position** of the shortest interval — an estimator problem |
| **rectangular** input | the true half-width is `1.939703σ`, but the law of propagation uses the normal `1.959964σ`. The gap of **0.040521** is **8×** the tolerance `δ = 0.005` — **error of the method itself** |

The rectangular case comes out structurally wider because the **excess kurtosis of Irwin–Hall(4) is `−6/(5n) = −0.3`**: lighter tails than the normal.

![Exact solution for the rectangular sum](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/13_rectangular.png)

### And then the fifth

"The shortest interval pins down its width precisely but not its position" — I learned that by measuring, but I had **written it down as an unconditional property**.

For a symmetric distribution the width `W(a) = F(a+w) − F(a)` has `W' = 0` at the centre with little curvature, i.e. a **flat valley**, so `argmin` wobbles. But **for a skewed distribution the optimum is unique and strongly determined**.

Measured over 12 seeds each (sd of position / sd of width):

| | n = 200,000 | n = 1,000,000 |
|---|---|---|
| symmetric (sum of normals) | **5.2** | **4.1** |
| skewed (sum of squares) | **1.0** | **1.0** |

I corrected the docstring to "for symmetric (or near-symmetric) outputs" and wrote down the mechanism.

---

## 6. A by-product — percent agreement and kappa

I also added agreement measures for attribute (pass/fail) inspection. There is a classic trap here.

On a process with a 95 % pass rate, **two inspectors stamping completely at random** still agree more than 90 % of the time.

![Agreement and kappa](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/06_kappa.png)

*↑ The judgements are **completely independent** (random). The higher the pass rate, the higher the raw agreement — while kappa stays pinned near zero.*

Measured: at a pass rate of 0.95, raw agreement **0.920** against kappa **0.101**. Kappa is `(p_o − p_e)/(1 − p_e)`, which measures what is **left after discounting the agreement chance alone would produce**. Look only at raw agreement and you read it as "they agree well".

---

## 7. One more piece of honesty — negative variance components

Variance components come from **differences** of expected mean squares, so when the true component is near zero they **go negative**.

This is not a rare edge case. On synthetic data with the operator effect set to **exactly zero**, 40 seeds produced a negative reproducibility component in **31 of them**.

Clamping to zero is reasonable. But **an implementation that does not declare the clamp is asserting "there is no operator effect"**. The correct statement is "**it could not be estimated**".

```python
g["clamped"]   # [False, True, False, False, False] ← reproducibility was clamped
```

Nor does it hide the jitter in the estimators. Repeatability with a true value of 0.4 came out over 40 seeds as mean 0.39710, sd 0.00788 (theory `σ/√(2df)` is 0.00913 at 960 degrees of freedom). Reproducibility, by contrast, is estimated from 4 operators — 3 degrees of freedom — so against a true value of 0.5 its sd is **0.159**: a quantity where **getting the order of magnitude right is a good day**.

![Spread of the estimators](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/04_spread.png)

---

## 8. On how the work was done

For this round I **handed the primary-source checking to a different AI**. It pulled the raw data and published values of the worked examples out of the standards' PDFs, and I verified them **by running them through my own implementation and seeing whether they reproduced**.

That worked because I had an **independent way to confirm** whether the numbers I was handed were right. In practice:

- the transcription of the raw data was correct (proved at the same time, since the published table reproduced to six decimals)
- but **the model was different** (the interaction pooling) — that never shows up in a numerical comparison; it only appeared once I tried to reproduce
- the **last digits of the exact solution it gave me were wrong** (−3.8797 → correct −3.879407). Because it had shown its derivation, I could pin that down **three independent ways**: the closed form, numerical inversion of the full branched CDF, and 2×10⁷ direct samples
- one section attribution was also wrong (the conditions of applicability live in a different section) — corrected after asking for the clauses again

**A claim that shows its steps can be checked. A claim that is only a number cannot.** I think that is the dividing line when you bring outside information in.

---

## 9. Takeaways

- **52 green tests** built on identities, closed forms and controls still cannot see **missing specification**
- The **worked examples** in a standard are answers printed independently of your derivation — that is the only place an external difference can come from
- **If an exact solution exists, throw away the random numbers** — it was the exact solution that proved two identical failures had opposite causes
- A tool should **fail honestly**, and the failure should come back **as structure, not as a warning**

Nine operators, 55 tests in the end, and a PoC with 30 checks and 14 figures (one of them animated). All of it is on [GitHub](https://github.com/furuse-kazufumi/fullseye).

- Capability note: [How much of that number belongs to the way you measured it](https://furuse.work/capabilities/measurement-system-and-uncertainty.html)
- PoC: [`examples/poc_measurement_system_analysis.py`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_measurement_system_analysis.py)
- Exhibition: [A Metrology Museum on Paper](https://qiita.com/furuse-kazufumi/items/8a8f23e53b19ee8cdc10) (143 exhibits)

---

## Sources

- Measurement Systems Analysis Reference Manual, 4th edition (gauge R&R by the ANOVA method, and its worked example)
- JCGM 100:2008 *Evaluation of measurement data — Guide to the expression of uncertainty in measurement* (law of propagation, Welch–Satterthwaite, Annexes H.1 / H.2)
- JCGM 101:2008 *Supplement 1 — Propagation of distributions using a Monte Carlo method* (numerical tolerance §7.9.2, validation procedure §8.1.3, conditions of applicability §5.7.2 / §5.8.1)
- B. L. Welch, *Biometrika* **34** (1947); F. E. Satterthwaite, *Biometrics Bulletin* **2** (1946)
- J. Cohen, *Educational and Psychological Measurement* **20** (1960); J. L. Fleiss, *Psychological Bulletin* **76** (1971)
- J. O. Irwin, *Biometrika* **19** (1927); P. Hall, *Biometrika* **19** (1927)
