---
title: 'It Passed Every Static Test, Then Failed Completely the Moment It Started Walking — Putting a Connectome-Constrained Fly Visual Model on a Body'
tags:
  - Python
  - 機械学習
  - 神経科学
  - シミュレーション
  - MuJoCo
public_private: true
public_id: 638f0b0aa7865e17c67c
---

> **Language**: [日本語](https://qiita.com/furuse-kazufumi/private/331af639c2b9a1493576) · **English**

# It Passed Every Static Test, Then Failed Completely the Moment It Started Walking — Putting a Connectome-Constrained Fly Visual Model on a Body

<!--
  This article is the readable form of a running experiment ledger: one more entry is appended
  every time an experiment finishes. How to append (do it in BOTH ja and en, never one only):
    1. Add one row to the "Experiments so far" table — question / current answer / section.
    2. If it fits the narrative, add it to that chapter. If it does not, append
       `### <one line> (YYYY-MM-DD)` under "## Appendix: later experiments", in date order.
       Never reorder existing chapters — section numbers are referenced from the table.
    3. If the result is strong, add one TL;DR bullet. Keep TL;DR at 6-8 bullets: drop a weak one.
    4. Remove the finished item from "What we measure next" (a stale plan reads as a lie).
    5. Figures go in docs/articles/assets/fly/ and are referenced by raw absolute URL
       (never a relative path). Japanese labels in figures are fine — say so in the caption.
    6. Every number comes from a measured json. Nothing that is not in the ledger. Retractions
       are never deleted; they stay in section 8.
    7. After appending, PATCH the Qiita item (check on purpose if the body would shrink).
       The poster is fullsense's tools/qiita_public_post.py (canonical for public qiita.com,
       idempotency key = public_id):  py -3.11 qiita_public_post.py post <file> --yes --private
    8. While unlisted, the other language links to /private/<id>. **When either goes public,
       swap /private/ for /items/ in BOTH articles** — an unlisted URL does not open for others.
-->

![Walking](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fly/flyvis_loop2_000_noise0.30_00_om_efc.gif)

*↑ The moving picture first. A physically simulated *Drosophila* walks towards the brown target guided by **nothing but the image on its compound eye** (3× speed, external camera). The steering correction comes from an optic lobe model whose wiring is fixed by the measured connectome. The legs look like a tripod gait, but **walking here is kinematic**, not leg dynamics — the table below states exactly what is real and what was written by hand before any numbers appear.*

![What the fly is asked to do](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fly/task_setup.png)

*↑ The whole task in one picture. **① The input is the compound-eye image alone** — no GPS, no inertial sensor, no map. **② Read your own rotation while walking**, steer to the target with it, then return to the nest from the heading and distance you accumulated. **③ Scoring is the correlation against the imposed rotation**, and 2 of the 12 places (C and D) are never used for selection or tuning. The null baseline is the textbook motion detector of 1956. Figure labels are in Japanese; every item is repeated in the text.*

## TL;DR

- A pretrained visual model of the fruit fly optic lobe — one whose **wiring is fixed by the measured connectome** — was mounted on a physically simulated fly body and run in closed loop: compound eye → optic lobe → steering. **It passed every test built by rotating the fly in place (monotonicity, symmetry, latency), and then failed completely (correlation 0.06–0.51) when asked to read the same quantity while walking.** A test built under different motion conditions than the deployment guarantees nothing.
- The cause was not the model but the **world**. Optic flow from translation scales as speed ÷ distance; flow from rotation does not depend on distance at all. With the eyes 1.2 mm above the floor, the floor streams past at 330–1000°/s — beyond the passband of the motion detectors, pure noise. **Reading only above the horizon** gives correlation 0.98. But in a world whose distant background has no texture, no motion detector can read rotation at all. **Measure the stimulus statistics before you suspect the model.**
- **Being a good sensor is not the same as improving behaviour.** Feeding that estimate into steering changed arrivals from 7/12 to 6/12 — within noise. A hand-written fixation behaviour dominated. Sensor fidelity and behavioural performance must be measured, and reported, separately.
- Evolving the free parameters showed that **more degrees of freedom destroy generalisation when data is scarce**. Evolving all 734 free parameters on 2 scenes pushed training to +0.76 while held-out scenes fell to **−0.35** (worse than before evolution). Compressing the same search to **260 per-cell-type modulations** gave **+0.70**. With 10 training scenes the two are nearly equal (0.916 vs 0.914). Solving the readout by ridge regression reproduced the same shape (5768 weights vs 80 weights).
- Even when behaviour improves, **biological realism degrades**. The solution that generalised on 10 scenes had direction selectivity in only 1 of 8 T4/T5 types, down from 3. A behavioural objective alone does not produce neural properties.
- Driving a **central-complex model** (ring attractor + path integration) with the visually estimated angular velocity does get the agent home, but the dominant error term is not the gain mismatch (3.8 points) — it is the **residual noise behind a correlation of 0.977 (12.4 points)**. No amount of careful calibration removes it.

This is not an article about reproducing a fly brain. It is about **where a pretrained model starts lying once you mount it in your own system** — stated in numbers. The same traps appear when you put someone else's pretrained model on your robot or your production line.

## Experiments so far (this table grows)

One experiment = one question. **This article is appended to every time an experiment finishes.** The "current answer" column is the measurement as it stands, and it can be overturned — one entry already was, and the retraction is kept in §8.

| Question | Current answer | Section |
|---|---|---|
| Does a test built by rotating in place predict performance while walking? | No. Correlation 0.06–0.51 — a total failure | §1 |
| Does texture in the distance make rotation readable while walking? | Yes. Correlation 0.98 (0.06 without the band) | §2 |
| Does a better sensor mean better behaviour? | No change. Arrivals 7 → 6 of 12 | §3 |
| How many points of performance is the connectome wiring worth? | 0.14–0.20. Preprocessing alone takes 0.6 → 0.8 | §4 |
| Does evolving all 734 free parameters generalise? | 2 scenes overfit (−0.25); 10 scenes generalise (+0.92) | §5 |
| What if the search is compressed to 260 per-cell-type dims? | Wins on little data (+0.71), ties on plenty (+0.91) | §5 |
| What if the readout is solved by regression instead? | Same shape: 80 weights ≫ 5768 weights | §5 |
| Does better behaviour bring biological realism with it? | The opposite. Direction selectivity 3/8 → 1/8; untrained is 0/8 | §6 |
| Can the visual estimate drive central-complex homing? | Yes, but the limit is readout correlation, not gain | §7 |
| Does enlarging the eye break it? | No — and the first conclusion here was retracted | §8 |

## Glossary (worth reading first)

- **Connectome** —— The map of which neuron connects to which, reconstructed from serial electron microscopy. For *Drosophila* this now exists at whole-brain scale, so "which cell type contacts which, and with how many synapses" is known.
- **Connectome-constrained model** —— A network whose wiring (who connects to whom, excitatory or inhibitory) is fixed from the measured connectome, leaving only continuous values (per-cell-type bias, time constant, synaptic strength) to be learned. Here: **flyvis** (Lappalainen et al., 2024), the optic lobe model, with 734 free parameters.
- **Ommatidium** —— One tube of a compound eye. Here 721 of them, 4.63° between optical axes (Δφ), 8.23° Gaussian acceptance angle (Δρ).
- **T4 / T5** —— The workhorses of fly motion detection: T4 for brightening edges, T5 for darkening edges, each split into four directions (a/b/c/d).
- **DSI (direction selectivity index)** —— Normalised difference between the response to the preferred and the opposite direction. Here a cell type counts as selective at DSI ≥ 0.3.
- **EMD (elementary motion detector)** —— The textbook motion detector of Hassenstein and Reichardt (1956): take two neighbouring pixels, delay one, multiply. Used here as the **null baseline**.
- **Self-rotation (yaw rate)** —— How fast the agent is turning. Reading this from vision alone is the main task of this article.
- **Hold-out** —— Conditions never used for selection or tuning. Of 12 "places" (worlds with different background layouts), two (C and D) were kept unseen until the very end.
- **Path integration** —— Accumulating heading and speed into a running "home vector". In insects this lives in the central complex.
- **Genomic bottleneck** —— The constraint that a genome cannot possibly specify every synapse, so what it can encode is closer to per-cell-type rules (Zador, 2019). This is the subject of the second half.

## What is real, and where the hand-written part begins

This table comes first. Without it, a reader will assume the fly's brain did all of it.

| Part | What it is | Origin |
|---|---|---|
| Body | Full-body *Drosophila* model (mass 0.98 mg, cm/g/s units) in a physics simulator | Public model (flybody) |
| Walking | Leg stance patterns are **kinematic** — it is not walking by leg dynamics | Hand-written |
| Eye | Three body-mounted cameras resampled onto 721 hexagonal ommatidia (including the 1.118× diagonal distortion) | Hand-written (geometry matched to the public model) |
| Optic lobe | 65 cell types, wiring fixed, 734 free parameters, pretrained | Public model (flyvis) |
| Readout | One expression: "above the horizon, (preferred − opposite) ÷ sum" | **Hand-written**, zero parameters |
| Behaviour | Fixate on something darker than the sky, plus optomotor feedback and efference copy | **Hand-written** |
| World | Floor, sky, a target (organic shape), distractors (gear, lattice sphere). The sky texture is synthetic | Hand-written |

![Signal path of the fly brain model](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fly/flybrain_model_map.png)

*↑ The signal path and the boundary between real and hand-written. Only the blue box is wired by the measured connectome — the flyvis optic lobe, 65 cell types, in the order light travels: receptors R1–R6 → lamina L1/L2/L3 → medulla (ON: Mi1, Tm3 / OFF: Tm1, Tm2, Tm4, Tm9 / modulatory: Mi4, Mi9) → T4a–d (ON) → T5a–d (OFF). Every orange box was written here. Evolution moves only the continuous values inside the blue box; not one new connection is ever added. Figure labels are in Japanese; the same content is in the table above.*

![The columnar structure of the optic lobe in 3-D](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fly/flybrain_columns_3d.gif)

*↑ The same optic lobe, rotating in 3-D. **The 721 columns keep their arrangement through all seven stages** — that is the columnar organisation — with one colour per stage (receptors → lamina → medulla ON / OFF / modulatory → T4, the ON direction-selective cells → T5, the OFF ones). Column positions are the **real hexagonal lattice**, but **the depth between stages is schematic**: flyvis is a columns × cell-types network and carries no anatomical 3-D coordinates. When section 5 talks about "folding the degrees of freedom per cell type", these colours are the unit it folds along.*

So **only the optic lobe is genuinely connectome-derived**; everything before and after it (eye geometry, readout, behaviour) was written by hand. Every number below describes "the optic lobe wired up this particular way".

## 1. It passed every static test, then failed while walking

The first step was to calibrate the optic lobe output by rotating the fly in place. Three tests were built:

1. **Monotonicity** —— does the output increase monotonically with rotation speed?
2. **Symmetry** —— is it symmetric about the origin, left versus right?
3. **Latency** —— is the rise time within a physiological range?

All three passed. The output was monotonic and origin-symmetric up to ±2 rad/s, with a 0.11 s latency (63 % rise). Across places the gain varied by only ±35 % after normalisation. At that point it was tempting to call the sensor usable.

Then the same quantity was read **while walking**. Correlation across every candidate readout: 0.06–0.51. **A complete failure.** The three tests that passed had predicted nothing about performance during locomotion.

The reason becomes clear in the next section, but the lesson is already fixed:

> **Put the test where the accident happens.** A verdict obtained from static stimuli says nothing about performance under motion.

This is not specific to flies. A model with good benchmark accuracy that collapses once real motion enters your robot's camera is the same failure, with the same shape.

## 2. Measure the world before suspecting the brain

The first suspects were the model ("maybe the pretrained weights do not fit this body") and the readout expression. Both were wrong.

The cause was the **statistics of the stimulus**. Optic flow splits into two components:

- Flow from **rotation** equals the angular velocity itself. **It does not depend on distance.**
- Flow from **translation** equals speed ÷ distance. **The nearer something is, the faster it streams.**

The fly's eyes sit 1.2 mm above the floor. Even at a walking speed of 2.8 cm/s, **the floor directly below streams past at 330–1000°/s** — far above the band T4/T5 can follow, burying the rotation signal in noise.

The fix was one line: **read only above the horizon.** Distant flow has a large denominator, so the translation term vanishes and only rotation survives. Walking self-rotation estimation then reached **correlation 0.98**.

![Self-rotation estimated while walking](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fly/flyvis_loop2_000_noise0.30_m4.png)

*↑ Self-rotation during walking at place C, which was never used for any selection. Black is the imposed rotation, red is the estimate read out from T4/T5. Correlation 0.98, bias +0.022 rad/s — but the amplitude comes out at roughly 0.6× the truth (see section 7). Labels are in Japanese: the axes are rotation rate [rad/s] against time [s].*

There is a second trap here. Reading above the horizon helps only if **the distant background has texture at all**. The first world had a smoothly graded sky, so everything above the horizon was nearly uniform and carried no cue whatsoever. Only after adding a cloud band at 20–60° elevation (1/f in azimuth, amplitude 0.12) did the 0.98 appear. Without the band: 0.06.

![What the compound eye sees](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fly/eye_view_skyband.png)

*↑ What the compound eye (721 ommatidia, 4.63° between optical axes) sees at that moment. Left: brightness per ommatidium. Right: the salience of "something dark above the horizon". Whether the sky band exists changes the rotation estimate from 0.06 to 0.98. Figure labels are in Japanese; every number is repeated in the text.*

> **A defect in the world looks exactly like a defect in the brain.** Before measuring a model, measure whether the cue exists in the stimulus.

To be honest about it: adding texture to the sky is a convenient modification. The justification is that real outdoor scenes contain clouds, canopies and terrain silhouettes, and a perfectly uniform distance is the unusual case. Still, since the amount of texture was chosen here, **0.98 is a number that includes the world setting** — it is not the model's performance in isolation.

## 3. Being a good sensor and improving behaviour are different things

With rotation readable, the estimate was fed into steering. Three conditions, twelve runs each:

- **Fixation only** —— the hand-written "turn towards something darker than the sky"
- **+ optomotor** —— add a steering term opposing the visually estimated rotation
- **+ efference copy** —— subtract the agent's own commanded turn from the estimate first

![Closed-loop walking trajectories](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fly/flyvis_loop2_000_noise0.30_tracks.png)

*↑ Twelve trajectories per condition. The coloured disc at the centre is the target; grey discs are distractors (gear, lattice sphere). Left to right: fixation only / + optomotor / + efference copy. Arrivals: 7 / 6 / 6.*

*(Of these three conditions, the one actually moving at the top of this article is "+ efference copy". The approach to the brown target itself is the hand-written fixation behaviour; the optic lobe only contributes a steering correction — which is exactly the point of this section.)*

The result: **7 / 6 / 6**. With the disturbance tripled it became **7 / 4 / 6**, meaning feedback **without** efference copy actively hurt (the agent's own turns were mistaken for disturbance and cancelled).

So a sensor with correlation 0.98 changed behaviour not at all on this task. Fixation dominated; the optomotor path was redundant.

> **Measure and report sensor fidelity and behavioural success separately.** One being good says nothing about the other.

This bears directly on objective design. Optimise for behaviour and the hand-written part wins, leaving the model almost stationary. Optimise for sensor accuracy and it overfits — which is the next section.

## 4. How much is the wiring actually worth?

The selling point of a connectome-constrained model is that the wiring is measured. So: **how many points of performance is that wiring worth?** Answering this requires comparing against a classical motion detector on the same stimulus with the same readout.

The comparison is the 1956 EMD (two neighbouring samples, delay one, multiply). It was implemented with operators from a self-built image-processing library, and its parameters (time constants for the delay and the high-pass) were chosen **using training places only**, leaving C and D unseen.

| Motion detector | A | B | C (held out) | D (held out) |
|---|---|---|---|---|
| EMD on raw luminance (τ 0.05 s) | 0.45 | 0.57 | 0.62 | 0.77 |
| EMD + high-pass (τ 0.1 s, τ_hp 0.2 s) | 0.79 | 0.88 | **0.84** | **0.78** |
| flyvis (connectome-constrained, pretrained) | 0.90 | 0.94 | **0.98** | **0.98** |

Two things follow.

1. **Preprocessing closes most of the gap.** Adding the high-pass stage — the analogue of the lamina, the layer right after the photoreceptors — lifts the EMD from the low 0.6s to the low 0.8s. It is not "the connectome lets it see"; it is mostly **removing the slowly varying part of brightness**.
2. **The remaining 0.14–0.20 is the wiring's share.** ON/OFF pathway separation, normalisation and spatial integration earn that. Not zero, but not an order of magnitude either.

That number is directly usable: if 0.84 is good enough for your application, ten lines of EMD will do.

## 5. More degrees of freedom, less generalisation from little data

Now the main result. **Keep the wiring fixed; evolve only the free parameters.**

Setup: CMA-ES, 1500 evaluations, step size σ0 = 0.1, objective = correlation of walking self-rotation estimation on the training places. Held-out places C and D are never used for selection.

![Round one of evolution](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fly/evo_r1_report.png)

*↑ Evolution with two training places. Left: training progress. Middle: held-out score before and after. Right: relative distance travelled from the pretrained weights. Starting point 007 improved on training while its held-out score went negative; starting points 000 and 001 never moved at all (distance 0). Labels are in Japanese; the numbers are all in the text below.*

Two things happened.

- **Good starting points do not move.** Individuals that already generalised (000, 001) produced nothing better than their pretrained point in 1500 evaluations; the distance travelled was exactly 0 — a strong local optimum. Raising the step size to 0.2 destroyed them instead (mean 0.13).
- **Bad starting points overfit.** Individual 007 went from −0.37 / +0.31 to +0.76 / +0.49 on training, while its held-out scores went from **+0.27 / −0.30 to −0.35 / −0.14** — worse than before evolution. It had simply memorised scene features.

Two levers were tried against this.

**Lever A: more environments.** Raising the training set from 2 places to 10 brought the same 734-dimensional evolution to **C 0.887 / D 0.944** on held-out places. The overfitting disappears. A plain result.

**Lever B: compress the degrees of freedom.** This one is more interesting. The 734 free parameters live "per synapse". A genome cannot hold per-synapse values — the most it can encode is something like **rules per cell type** (Zador's genomic bottleneck, 2019).

So the search variables were folded into 260 dimensions:

- bias per cell type (65)
- log time constant per cell type (65)
- synaptic gain per **presynaptic** cell type (65)
- synaptic gain per **postsynaptic** cell type (65)

Each synaptic strength becomes presynaptic gain × postsynaptic gain × pretrained value. Not a single new connection is created (attempting one is a hard failure).

![Degrees of freedom versus generalisation](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fly/dof_vs_generalisation.png)

*↑ Left: evolution (moving the brain's parameters). Right: readout (brain frozen, solving linear weights). In both panels the vertical axis is the mean correlation on places C and D, never used for selection. Red is 2 training places, blue is 10. Figure labels are in Japanese; all values appear in the tables below.*

In numbers:

| Degrees of freedom | 2 training places | 10 training places |
|---|---|---|
| Free, 734 dims (per synapse) | **−0.25** | +0.92 |
| Bottleneck, 260 dims (per cell type) | **+0.71** | +0.91 |

**Two wins.**

1. **It wins when data is scarce.** Same two scenes, same starting point, same evaluation budget: the free search overfits into negative territory while the bottleneck generalises to +0.71. Cutting the degrees of freedom to a third *reverses* the ranking.
2. **It ties when data is plentiful.** With 10 scenes: free 0.916, bottleneck 0.914. **The same generalisation with one third of the freedom.**

The same shape appeared without touching the brain at all, by solving the **readout** side (right panel) — a ridge regression from T4/T5 activity to self-rotation, with λ chosen by leave-one-out on the training places only:

| Readout | 2 training places | 10 training places |
|---|---|---|
| Hand-written (0 parameters) | +0.98 | +0.98 |
| Structured (cell type × elevation band = 80 weights) | +0.96 | +0.98 |
| Free (cell type × column = 5768 weights) | **−0.03** | +0.83 |

The 5768-weight fit memorised the scene outright on two places (held-out C 0.13 / D −0.19) and still had not caught up on ten (D 0.72). The **80-weight version, which only pools over elevation bands, reaches 0.96 with two places**. Opening up its closed-form weights showed it had rediscovered the structure of the hand-written expression: T4a negative and T4b positive, concentrated in elevation bands 6–8 (exactly where the cloud band sits), essentially zero in the lower half.

> **An inductive bias wins when data is scarce and costs nothing when it is not** — provided the axis you fold along is a real structural unit (cell type, elevation band).

Honest caveats. (a) The hand-written readout already sits at 0.98, so **mathematical optimisation buys no performance on this task**; what it bought was confirmation that the hand-written form is near-optimal, and an explanation of its structure. (b) The 260-dimensional cut is a design decision about granularity, not a deduction from biology. (c) The 2-place condition starts from 007, a starting point that is particularly bad for the free search; a different start changes the size of the gap.

## 6. Behaviour improves, biological realism degrades

One more quantity was measured at every step: **direction selectivity (DSI) of T4/T5**, probed with moving edges at six speeds.

- The solution that overfitted on 2 scenes: 3/8 types selective → **2/8**. T4a fell from 0.59 to **0.00**.
- The solution that generalised on 10 scenes: training and held-out both improved, yet selectivity went 3/8 → **1/8**.
- An individual that already generalised, evolved further: 7/8 → **4/8**.

**Behavioural performance and biological realism dissociated cleanly.** Reading self-rotation, as a single task, does not require T4/T5 to discriminate direction. Indeed, an individual whose T5 cells are almost non-selective still estimates self-rotation at 0.96 — **T5 is redundant for this task.**

For completeness, the untrained network (wiring only, parameters from the initial distribution) was also measured: **direction selectivity 0/8, self-rotation estimation ≈ 0**, insensitive to the random seed. The wiring does not supply the function; it supplies the scaffold that makes learning it fast.

> **Optimise for a single task and every property that task does not need will be removed.** To keep a property, include a task that requires it.

## 7. Closing the loop: see → orient → move

Finally, the visual estimate was connected to **navigation**. The insect central complex contains a ring attractor representing heading (a bump travelling around a circle) and a path integrator accumulating the home vector. Both were implemented with closed-form checks (bound on phase error, closed-loop residual, monotonic approach on the homeward leg), and the flyvis angular velocity estimate was fed into the compass.

![Homing from the visual pathway through the central complex](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fly/poc_cx_flyvis_link.png)

*↑ Left: a ground-truth compass (zero visual error). Middle: the raw visual estimate. Right: the visual estimate with its amplitude corrected by a walking calibration. Grey is the outbound path, colour is the homeward path, the star is the nest. Labels are in Japanese; the error percentages are in the text.*

- **Ground-truth compass**: homing error 7.4 % (closest approach relative to a 28.8 cm outbound path)
- **Raw visual estimate**: 23.5 % (does not get home)
- **Amplitude calibrated**: 19.8 %

The visual estimate has only 0.63× the true amplitude, so naively multiplying by 1.54 ought to fix it. It does not — calibration recovers only as far as 19.8 %. Decomposing the error:

- due to the amplitude mismatch: **3.8 points**
- due to residual noise behind a correlation of 0.977: **12.4 points**

**The residual dominates by 3.4×.** Path integration accumulates error, so even an instantaneous correlation of 0.977 matters after a few seconds. In other words, **the next effective lever is not calibration but raising the readout correlation itself** — which ties this section back to the previous ones: environment diversity, compressed degrees of freedom and staged task curricula all feed straight into homing accuracy.

The 7.4 % that remains even with a perfect compass comes from holding forward speed constant, which makes the agent circle over the nest. Insects decelerate on approach; adding deceleration interferes with the memory update, so that needs its own experiment.

## 8. A retracted result

One conclusion here was wrong and has been withdrawn.

In an experiment that enlarged the eye (721 → 1951 ommatidia, same pretrained weights), the first write-up said: "if you add ommatidia without narrowing the acceptance angle, performance collapses — the optics must co-adapt." A plausible story, and the numbers did collapse (correlations −0.11 to 0.45).

The cause was not optics. It was a **tooling defect in which the second eye constructed inside the same process rendered a broken image** — the giveaway was near-zero variance across columns and a comparison EMD returning nan. Rebuilt in a separate process, the same configuration behaved normally (0.96–0.99).

What actually holds: **enlarging the eye does not break anything even without retraining; it improves slightly and saturates** (0.98 → 0.98–0.99). Shrinking (331 ommatidia) does hurt. Acceptance-angle co-adaptation does not matter over this range.

> **When a result surprises you, suspect tool ordering before you reach for physics.** The second object built in one process, the second call to a function, the second run that hit a cache — reproduce it in isolation before interpreting it.

## What to take away

Folded into forms that survive without the author, there are six:

1. **Put the test where the accident happens.** A verdict from static stimuli does not predict performance under motion.
2. **Measure the world before suspecting the brain.** If the cue is absent from the stimulus, no model can read it — and any performance number includes the world's settings.
3. **Report sensor fidelity and behavioural success separately.** One says nothing about the other.
4. **Cut degrees of freedom along structural units.** Variables folded per cell type or per elevation band win when data is scarce and cost nothing when it is not — provided the fold matches real structure.
5. **Single-task optimisation deletes every property the task does not need.** Include a task that needs what you want to keep.
6. **Surprising results: suspect tool ordering before physics.**

None of these are specific to flies. They appear whenever someone else's pretrained model is mounted in your own system.

## What was not measured

- Walking is **kinematic**. There is no leg dynamics, so image motion from ground reaction forces and slipping is absent.
- Everything downstream of the optic lobe (LC cells, descending pathways, motor commands) is **hand-written**. This is not "a fly brain steering".
- In the experiment that silences cell types stage by stage, the selectivity index reads 0.0 even when the response is identically zero, so "lost selectivity" and "no response at all" are not distinguishable. Response magnitude per type has to be checked separately; that check is not done yet.
- Evolution was run mostly from starting point 007, an individual that does not generalise. A different starting point changes the size of the effects.
- The connectome constrains **the optic lobe**, not the whole brain.
- Screening 50 pretrained individuals found **zero of the top ten with direction selectivity in all 8 T4/T5 types** (one had 7). Two had their T4 directions inverted by a full 180°. "This model reproduces direction selectivity" carries a large individual variance — **screen before you use it.**

## Public models and papers this rests on

- **flyvis** —— the connectome-constrained optic lobe model (Lappalainen et al., 2024): wiring, synapse counts and signs fixed from measurement, continuous values learned on a task. This is the "optic lobe" here.
- **flybody** —— the full-body *Drosophila* physics model (Vaxenburg et al., 2025), supplying body, joints and eye cameras.
- **Hassenstein & Reichardt (1956)** —— the elementary motion detector, used here as the null baseline.
- **Stone et al. (2017)** —— an anatomically constrained path integration model of the bee central complex; section 7 follows its structure.
- **Zador (2019)** —— the genomic bottleneck, the basis for folding per cell type in section 5.

The EMD implementation and the image-processing operators come from **Fullseye**, a self-built vision library. Using it as a measurement bench is what made the quantitative comparison in section 4 — the wiring's share — possible at all.

---

## Appendix: later experiments

<!-- Append new experiments here as `### <one line> (YYYY-MM-DD)`, in date order. Do not move the chapters above. -->

Nothing yet. What is currently running is listed below.

### What we measure next

When a result lands, it gains a row in "Experiments so far" and loses its line here.

- [ ] **Shuffled-connectome control** —— rewire while preserving degree, then evolve from the same initialisation on the same task, to measure the wiring's share (§4) from the evolutionary side too. Running.
- [ ] **Developmental ladder** —— silence cell types stage by stage and line up which function disappears where. A pilot showed that silencing all of T4 drops self-rotation estimation from 0.95 to 0.52, and that of the four T5 types only T5d loses its selectivity. Running.
- [ ] **Staged curriculum** (contrast → ON/OFF → direction → rotation) —— the countermeasure to the dissociation in §6. If a behavioural objective alone will not produce direction selectivity, will a task sequence that demands discrimination? A pilot showed **forgetting**: after learning a later stage, earlier-stage scores fell from 0.044 to 0.017.
- [ ] **Cumulative objective** —— does that forgetting disappear if stage *k*'s objective is the mean over stages 1…*k*?
- [ ] **Homing with deceleration** —— the 7.4 % that remains even with a perfect compass (§7) comes from constant forward speed circling over the nest. Deceleration interferes with the memory update, so it needs its own experiment.

### About the author

The questions and the direction are mine; implementation, sweeps, added controls and the checks that disproved my predictions were delegated to Claude Code. Section 8 records one of those disproofs.

---

**These experiments were run together with Claude Code.** I set the questions and the direction; Claude Code did the implementation, the sweeps, the management of long overnight jobs and the adversarial checks. If you want to try it, this invitation link gives you a **one-week free trial**: [claude.ai/referral/0sqPw8E_lw](https://claude.ai/referral/0sqPw8E_lw)

"I mounted a pretrained model in my own system, it passed the static tests, and it fell over in production" — that is the story I most want to hear from you. A **like or a stock** helps decide which experiment gets written up next.
