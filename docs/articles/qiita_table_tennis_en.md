---
title: 'A Table-Tennis Ball Bounces, So a Tracker That Ignores Physics Misses the Landing Point by 20 cm — A PoC Series That Measures Bounce and Friction from Video'
tags:
  - Python
  - NumPy
  - physics
  - ImageProcessing
  - robotics
public_private: true
public_id: a82bf9f341cc4f04ca75
---

> **言語 / Language**: [日本語](https://qiita.com/furuse-kazufumi/items/b6498dc822bf9eed100f) · **English**

# A Table-Tennis Ball Bounces, So a Tracker That Ignores Physics Misses the Landing Point by 20 cm — A PoC Series That Measures Bounce and Friction from Video

<!--
  How to append (ja and en in the same order; never add to one side only):
    1. Add one row to "Where the series is".
    2. Add one section — figure → procedure → gates and scores → where implementations go wrong → what it is not for → run it.
    3. Figures are absolute raw.githubusercontent URLs. Bump ?v=N when an image changes.
    4. Promote the trailing "Next time" into a section and write a new "Next time".
  ★Write only what helps the reader. No development history, no order of discovery, no list of fixes.
-->

![Two rackets feeding each other](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/07_rally_two_rackets.gif)

*↑ Two freely moving rackets (red, blue) return a ball that bounced once on the opponent's side, aiming with the equations of motion. First 3 seconds at 1/5 speed. That the rally **continued** is visible. The point of this article is that the **number of hits** is a report card for perception, prediction and control at once.*

## About this article

A table-tennis ball weighs 2.7 g, flies at close to 100 km/h, bounces on the table and spins at 3,000 rpm. Air drag slows it, spin bends its path (the Magnus force), and on the table the spin changes how it bounces. A tracker that follows a parabola is right until the bounce and misses the landing point after it by **20 cm**.

Robot table-tennis research triangulates the ball from several high-speed cameras, predicts through the bounce with equations of motion that include drag and Magnus, and measures spin from the ball's markings. This article builds that whole chain in **numpy only**, with a **gate backed by ground truth** at every stage.

> **(i) Is a theorem the gate, (ii) is a second implementation that assumes no closed-form structure the ground truth, or (iii) is there a published value (a standard, a measurement)?**
> Nothing that satisfies none of these is written. **Checking an answer with the formula that produced it is forbidden.**

The criteria are the same as in the autonomous-driving series ([here](https://qiita.com/furuse-kazufumi/items/05de90f4d316cd7c681c)). What differs is the subject — things that bounce, slide and spin — so the friction coefficient and the coefficient of restitution take the lead. Kendama (a ball on a string and a cup) uses the same tools, so it continues in this series.

## Where the series is

| Part | What is measured | Gates (where the truth comes from) |
|---|---|---|
| 1 | [The ball bounces — tracking, triangulation, prediction through the bounce, spin, rally](#part-1-the-ball-bounces--tracking-triangulation-prediction-through-the-bounce-spin-rally) | closed forms in vacuum / angular momentum about the contact point / apex ratio e^{2k}h₀ / the ITTF bounce standard / a world with ground truth / the rally length |
| 2 | [Kendama — the string only pulls, the ball flies a parabola, the cup is carried by a prediction from images](#part-2-kendama--the-string-only-pulls-the-ball-flies-a-parabola-the-cup-is-carried-by-a-prediction-from-images) | elliptic integral and period theorems / closed forms of tension and slack angle / Japan Kendama Association dimensions / a world with ground truth / 3DGS projection and compositing formulas |

---

## Part 1: The ball bounces — tracking, triangulation, prediction through the bounce, spin, rally

### Procedure

```
Dynamics : drag (Reynolds-dependent sphere model) + Magnus (spin ratio) + spin decay + speed-dependent restitution + Coulomb bounce (grip / slip), integrated with RK4
World    : an ITTF table (2.74 × 1.525 m, 0.76 m high, net 15.25 cm) and a 40 mm ball (14 black markers) with ground truth. Two tracking cameras + one close-up camera at the bounce
Video    : detect the ball by chromaticity (sub-pixel) → track with constant-velocity prediction → DLT triangulation → constant-acceleration Kalman
Predict  : detect the bounce at a local minimum of z → fit 6 parameters of the equations of motion by Gauss–Newton to the 15 frames before it → read the landing point through the bounce
Measure  : restitution e from fits to 12 frames on each side; angular velocity from marker correspondences (Kabsch) on the close-up camera
Rally    : two rackets meet the ball after one bounce on the opponent's side and return it to a chosen point. Before each hit they look ahead and rewind if the shot would fail. The hit count is the metric
```

**In plain words**: three formulas decide the motion. **Drag** (the faster, the stronger the deceleration), the **Magnus force** (the ball curves in the direction of spin × velocity), and the **bounce** (the vertical speed comes back scaled by e, the horizontal speed is trimmed by friction, and the spin changes). Tracking finds the ball in the images and puts it back into 3-D; prediction integrates the formulas; measurement is the inverse problem.

[![A frame from tracking camera 1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/01_rig_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/01_rig_view.png)

*↑ Tracking camera 1 at t = 0.15 s. The ball is only 4 px in radius. The cross is the projection of the world's own ground truth.*

### Gates and scores

| # | Gate | Truth | Score |
|---|---|---|---|
| 1 | Identities in vacuum | closed form | RK4 vs closed form 1e-12; a parabola fit returns g = 9.81 to 4e-15 |
| 2 | Bounce theorems | angular momentum about the contact point | 500 random impacts (e ∈ [0.3, 1], μ ∈ [0, 0.6]): relative error at most 4.9e-16, energy never increases, 136 switch to rolling / 364 keep slipping |
| 3 | Apex ratio and the ITTF bounce | e^{2k}h₀ and the 24–26 cm standard | dropped from 30.5 cm: apexes 24.7 / 20.0 / 16.2 / 13.1 cm, 3e-7 from the closed form; total time 4.736 s (closed form 4.738 s) |
| 4 | Detection | projected world truth | 122 / 122 frames, median centre error **0.15 px** (image radius 4.3 px) |
| 5 | Triangulation | world truth | 4e-15 m from projected truth, median **1.6 mm** from detections |
| 6 | Kalman | a parabolic truth | innovation at most 8e-9 m (2e-3 m with drag and Magnus in the truth = outside the model); median velocity error 0.07 m/s |
| 7 | Bounce detection | the world's contact time | **0.6 ms** off (one frame = 10 ms) |
| 8 | Prediction through the bounce | the world's landing point | **0.4 cm** with the true spin, **20.2 cm** ignoring spin, 6.6 cm with a parabola |
| 9 | Spin | the world's angular velocity | markers matched in 19 / 19 frame pairs, relative error **3.7 %** at \|ω\| = 2394 rpm |
| 10 | Restitution | the world's e = 0.90 | **0.911** from equation-of-motion fits; 0.940 from parabola fits (drag and Magnus absorbed into g) |
| 11 | Rally length | the cap, an attacker, perception noise | feeder vs feeder 12 (cap), attacker vs feeder 9 (out), perception noise 0 / 50 / 100 mm → 8 / 8 / 2 hits |

[![Trajectory in the x–z plane](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/03_trajectory_xz_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/03_trajectory_xz.png)

*↑ Points triangulated from detections (median error 1.6 mm) sit on the truth. Reading ahead from the state fitted to the 15 frames before the bounce, the landing point is 0.4 cm off if the 2291 rpm topspin is known, and 20.2 cm off if spin is ignored.*

**How to read gate 11 (the claim of this article)**. The rally length grows only when detection, triangulation, prediction, shot planning and racket motion are **all** right at the same time. If any one stage breaks, it shows in the count, so one number scores the chain. Make one side "play to win" (fast to the far corner) and the rally ends at 9; make both sides "return close to last time, shifted a little" and it runs to the cap. Adding 5 cm of noise to perception does not shorten the rally; 10 cm drops it to 2. The flat part is the slack of the racket face (15 × 16 cm) — errors smaller than half the face do not show in the count, which is also the resolution of the metric.

**Rewinding**. Before each hit, the planner looks ahead with the true physics; if the shot would hit the net, bounce on its own side or arrive at an unreachable height, it **rewinds time and tries again** (counted). The attacker still ends at 9 hits after 99 rewinds because the mismatch between the planner's formulas (a closed-form aim plus iteration) and the world's physics (Reynolds-dependent drag, spin-ratio lift) grows with ball speed. The rewind count can be read as **the amount of mismatch between planner and physics**.

### ★ Where implementations go wrong

#### 1. Gate the Kalman filter on a real trajectory and it looks broken

A constant-acceleration Kalman filter is exact for a parabola (innovation 1e-9 m). Feed it a trajectory with drag and Magnus and the innovation is 2e-3 m — that is being outside the model, not a defect in the filter. Gate it on a parabola, and give the real trajectory to the equations of motion for prediction.

#### 2. Fit a parabola and the restitution is 4 % off

Fitting parabolas before and after the bounce to get v_z absorbs drag and Magnus into gravity: e = 0.940 (truth 0.90). Fitting the equations of motion gives 0.911. The landing point behaves the same way: 6.6 cm with a parabola, 0.4 cm with the equations. **Fit with the same equations you predict with.**

#### 3. One marker does not determine the rotation

Knowing one marker's direction says nothing about rotation around that axis. Kabsch (least-squares rotation from two or more direction pairs) needs at least two markers visible in the same frame pair. With markers on six axes only, 2–3 are visible and some merge with the dark rim into one. With 14 markers (6 axes + 8 corners) and strobe-like lighting on the close-up camera (weak shading), 19 / 19 frame pairs match.

#### 4. A moving racket bounces in relative velocity

The racket face moves, so putting the ball's velocity straight into the bounce formula is wrong. Subtract the face velocity, bounce, add it back. The closed-form aim is the same: n ∝ v_out − v_in and v_r·n = |Δv| / (1 + e) + v_in·n.

#### 5. Bounded motion overshoots the acceleration limit in the last step

Bang-bang motion (full acceleration, then full braking just in time) run in discrete time exceeds the acceleration bound in the step before stopping. Use max(0, √(2ad) − a·dt) for the stopping speed to keep one discrete step of margin.

#### 6. Bounces never end (Zeno)

Apexes follow e^{2k}h₀, the intervals shrink geometrically, and **infinitely many** contacts fit inside the total time √(2h₀/g)(1 + e)/(1 − e). Unless you decide to put the ball on the table once the vertical contact speed drops below a threshold, the integration never stops.

#### 7. A zero normal spreads NaN silently

If normalising by a zero length returns NaN instead of raising, the rest of the rally is NaN and counts as "continued". Fail closed (ValueError); the gates do not let NaN through.

### What it is not for

**No real video yet.** Cameras, table and ball are a synthetic world with ground truth. The chromaticity detector is robust to shading but will pick up anything of the same chromaticity in the background. Real footage is a later part.

**The default drag and lift coefficients are literature values**, not measurements. There is an identification op (fit_aero: Gauss–Newton for C_d and C_L from a trajectory, recovers the truth to 1e-15), but it has not been run on a real ball.

**The rally planner knows the world's physics.** Rewinding uses the true physics to look ahead, so it does not transfer to a real machine as is. On a real machine the predictor (equation-of-motion fits) would do the look-ahead, and rewinds become "the gap between what the predictor said and what happened".

**Spin measurement needs markers.** Kabsch cannot stand on a plain ball. Using the seam or the logo is a different op.

### Run it

```bash
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
py -3.11 examples/poc_ball_bounce.py            # 11 gates and 8 figures (2 GIFs), about 110 s
```

```python
import numpy as np
import fullseye as fs

bp = fs.ledger.ball_params()                      # 40 mm, 2.7 g, drag 0.4, lift from the spin ratio
ip = fs.ledger.impact_params(0.90, 0.25)          # restitution e, friction μ
tp = fs.ledger.table_params()                     # ITTF: 2.74 × 1.525 m, 0.76 m high

# a topspin shot over the table (table at z = 0.76, bounces only inside its outline)
r = fs.ledger.flight_simulate([-1.3, 0.0, 1.0], [5.2, -0.3, 0.6], [0.0, 240.0, 0.0], bp, ip,
                              t_end=0.8, table_z=tp["height"], table_xy=(-1.37, 1.37, -0.7625, 0.7625))
c = r["contacts"][0]
print(round(c["t"], 4), np.round(c["p"][:2], 3), c["regime"], np.round(c["omega_out"], 1))
# 0.2495 [-0.095 -0.07 ] grip [  7.8 228.8   0. ]     ← contact time [s], point [m], grip or slip, spin after the bounce [rad/s]

# drop from 30.5 cm: apex ratio and the ITTF standard (first bounce 24–26 cm)
h = fs.ledger.apex_sequence(0.305, 0.90, 4)              # h₀ and the next 4 apexes
print(np.round(100 * h, 1))
# [30.5 24.7 20.  16.2 13.1]

# two rackets, up to 12 hits (feeder vs feeder)
rp = fs.ledger.racket_params()
from racket import strategy_feeder, strategy_attacker
res = fs.ledger.rally_simulate(bp, rp, tp, strategies=(strategy_feeder, strategy_feeder), retries=0, max_hits=12, seed=1, table_ip=ip)
print(res["hits"], res["end_reason"], res["rewinds"])
# 12 max_hits 0
```

Look at `end_reason`: `out`, `net`, `double_bounce` or `unreachable`. With the attacker it ends at 9 hits with `out`. When the count drops, it is the ball's motion, the perception or the planner — read it together with the rewind count and the stage narrows down.

---

This part produced **8 figures** in total — [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ball_bounce)

#### The remaining figures of this part

![Tracking camera GIF](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/06_rally_gif.gif)

*↑ Tracking camera 1, 100 fps at 1/10 speed. Orange crosses are detections, green is the projected Kalman state, red is the landing point predicted from the 15 frames before the bounce.*

[![Apex ratio](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/04_drop_apexes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/04_drop_apexes.png)

*↑ Apexes of a ball dropped from 30.5 cm (e = 0.90). They match the closed form e^{2k}h₀ to 1e-6, and the first bounce of 24.7 cm is inside the ITTF standard of 24–26 cm.*

[![Spin frames](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/05_spin_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/05_spin_frames.png)

*↑ Four frames from the close-up camera at the bounce (1000 fps, 20°). The directions of the visible black markers (4–6 of 14) are matched to the previous frame and the rotation is solved with Kabsch.*

[![Image-plane tracks](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/02_tracks_2d_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/02_tracks_2d.png)

*↑ The ball's track in camera 1's image: projected truth (line) and detections (points). Median centre error 0.15 px.*

[![Noise vs rally length](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/08_rally_vs_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/08_rally_vs_noise.png)

*↑ Rally length (feeder vs feeder, cap 8) with Gaussian noise added to the perceived ball position. No loss up to 5 cm, 2 hits at 10 cm. The flat part is the slack of the racket face.*

---

## Part 2: Kendama — the string only pulls, the ball flies a parabola, the cup is carried by a prediction from images

![Catching in the big cup in a 3DGS world](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/10_gs_catch_gif.gif)

*↑ Right = the image the closed loop's perception actually saw (the world turned into 3D Gaussian Splatting and rendered), left = the true shape at the same moment. The window at top right re-renders the kendama at three times the resolution. Blue ring = the ball found by chromaticity, cross = the landing point read from the parabola fitted to the frames after the string went slack. The only thing that moves the cup is the image on the right.*

### The basic moves of kendama

From the Japan Kendama Association's graded tricks, this part takes the four in which the ball is pulled straight up and caught in a cup.

| Trick | Grip | Cup |
|---|---|---|
| Big cup (ōzara) | cup grip (spike tilted down, big cup up) | big cup |
| Small cup (kozara) | same grip | small cup |
| Base cup (chūzara) | ken grip (spike almost straight down) | base cup |
| Candle (rōsoku) | pinch the spike | base cup |

The teachers' procedure is the same for all: pull straight up with the knees → **move the ken only after the string goes slack** → carry the cup horizontally under the point where the ball will come down (do not scoop) → bend the knees at touchdown to absorb the impact. This PoC turns that procedure directly into the stages of its controller.

Four rules. **(1)** Only gravity and string tension move the ball (a one-sided constraint, tension ≥ 0). **(2)** The ken and the cross piece are one rigid body whose position may move freely. **(3)** The ball rises after the string goes slack and is caught on the way down after its apex (a straight-up path counts as a parabola). **(4)** The spike is only for the ball's hole — in the cup tricks, touching the spike or the cross piece is a failure.

### Procedure

```
Shape      : from the Japan Kendama Association's published values (60 mm ball, 70 mm across, 180 mm assembled) and the JKA 16-2
             description (160 mm ken, cups 42 / 38 / 35 mm), the ken and cross piece are solids of revolution; so is the ball, hole included
             (a 17 mm wide, 40 mm deep cavity)
Mechanics  : string = one-sided constraint tension ≥ 0 (free fall when slack, radial speed lost when it snaps taut), by projection; with drag
World      : two cameras (480 × 360, 100 fps). A synthetic world with ground truth, additionally turned into 3D Gaussian Splatting before rendering
Perception : ball by chromaticity → triangulate from two cameras → "slack" when the ball is closer to the string hole than the string length
             for two frames in a row → fit a gravity-known parabola (6 unknowns)
Control    : lift (straight up with the knees) → wait (do not move until slack) → hold (do not approach until the ball clears the ken)
             → carry (cup horizontally under the landing point) → absorb (lower it at touchdown)
Scoring    : at the moment of touching the rim, lateral ≤ rim radius, relative speed ≤ 1 m/s, descending. Touching the ken = hit_ken (fail)
```

**In plain words**: a string cannot push. It can only pull — a "one-sided constraint". So when the ball is pulled up hard, at some moment the string goes slack, and from then on the ball flies a parabola. A parabola is fixed by gravity alone, so once a few positions after the slack are known, where the ball will come down can be computed. The cup only has to get there first and wait. What a person does as "watch the ball and wait where it falls" is done here with images and a parabola.

[![Grips of the four tricks](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/02_kendama_closeup_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/02_kendama_closeup.png)

*↑ The poses of the four grips. The ken and cross piece are one rigid body; only where it is held differs. Every dimension measured from the vertices matches the published value to 1e-9.*

### Gates and scores

| # | Gate | Truth | Score |
|---|---|---|---|
| 1 | Elliptic integral and large-amplitude pendulum period | published K(0.5) and the theorem T = 4√(L/g)K(sin θ₀/2) | K error 0; period string 3.0e-4, rod 8.9e-11 |
| 2 | Tension and slack angle | closed forms m(v²/L + g cos θ), cos θ_s = (2/3) cos θ₀ | tension 0.26 %; slack angle 125.04° (closed form 125.26°) |
| 3 | Energy and snap | conserved in flight; loss when taut = ½ m v_r² | spread in flight 2.5e-15 J; snap 0.2362 J vs 0.2367 J; dissipation first order in dt (ratio 9.7) |
| 4 | Shape | published values (70 across, 160 ken, cups 42/38/35, 60 ball, 180 mm assembled) | all 1e-9 |
| 5 | Big cup with true perception | stage order, no contact with the ken, rise after slack, catch descending | caught with 4.22 mm lateral offset; without the dodge the ball hits the cross piece at 0.260 s |
| 6 | Detection → triangulation → slack | world ground truth | median error **0.51 mm**; slack detected +23 ms after truth |
| 7 | Closed loop on images only | success rate with true perception | 20 trials: truth 1.00 / images **1.00** (all 390 estimates the plan received came from images) |
| 8 | Same plan, 3 tricks + candle | flight and contact with the ken | small cup 1.00, base cup 0.95, candle (truth) 0.95; lowering at touchdown cuts relative speed 0.91 → 0.61 m/s |
| 9 | Prediction error | ball position at the catch | **10.51 → 0.98 mm** from 3 to 44 frames after slack |
| 10 | Pixel noise | success rate | 1.00 for 0–2 px, 0.90 at 8 px, 0.40 at 16 px |
| 11 | Hole direction (stationary ball) | true hole axis | seen by both cameras in 14 of 40 poses, median error **1.8°** |
| 12 | Recommended model (49 mm big cup) | JKA model's success rate | 1.00 vs 1.00 |
| 13 | **Closed loop in a 3DGS world** | true perception | on 3DGS images at 4 mm spacing alone, all 1 + 2 trials caught; median triangulation error **0.30 mm** |
| 14 | 3DGS knobs | detection rate | 1.00 for spacing 2–64 mm; 0.25 at 20 mm position error; 0.00 at colour error 0.3 |
| 15 | The hole on 3DGS | true hole axis | 1 of 40 poses at 480 × 360; 16 (median 2.3°) at twice the resolution and 2 mm spacing; 0 at 4 mm |
| 16 | **10 consecutive tricks** (moshikame, three cups) | toss apex v²/2g, no contact with the kendama, rise then descend | both **10 in a row** on images alone (grade 5), relative speed 0.41–0.48 m/s |

[![The y–z trajectory](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/04_catch_yz_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/04_catch_yz.png)

*↑ The ball rises after the string goes slack; the cup waits until the ball clears the ken, returns horizontally, drops just before touchdown and catches. Dots are the two-camera triangulation.*

**Reading gate 9**. A parabola fitted to the first 3 frames after slack misses the catch position by 1 cm — the triangulation error rides on the velocity of a short interval. The error falls as frames accumulate and drops below 1 mm at 44 frames. The cup is re-carried to each new prediction every frame, so a wrong first prediction is still in time — the big cup's rim radius, 21 mm, is the room for "waiting". Gate 10 staying at 1.00 up to 2 px of pixel noise is the same room; meanwhile the lateral offset grows 2.4 → 4.1 mm.

### Recognising after turning the world into 3DGS

Rendering the synthetic world's meshes directly gives images that are "too clean". A real scene reconstructed with 3D Gaussian Splatting (3DGS) is blurred in shape and carries errors in position and colour. So a layer was added that **turns the world into 3DGS before rendering and feeds the result to the same image processing** (`gsplatnp`, numpy only).

```
Gaussians : attached to the world's faces (face index + barycentric coordinates + an error fixed in the face's local frame); they follow the vertices
Size      : σ = spacing (the 3DGS initial value). σ ≤ 0.5 R so a disc does not stick out of a curved surface; faces touching an edge (cup rims, the hole's mouth) get 1/4
Rendering : EWA projection Σ' = J W Σ Wᵀ Jᵀ + 0.3 I, front-to-back alpha compositing, Mip-Splatting's opacity compensation
Knobs     : spacing (density), position error, colour error
```

[![Mesh and 3DGS](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/08_gs_views_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/08_gs_views.png)

*↑ The same close-up camera: mesh and 3DGS (2 mm, 16 mm spacing, with errors). Coarse spacing blurs; errors make it fuzzy with bleeding colour.*

The renderer's gates are three formulas: the second moments of one Gaussian's alpha image equal Σ' (and equal the covariance of 3-D samples projected by a separate projection routine); a pixel covered by two Gaussians has the colour of the front-to-back compositing formula (and the image is the same in either array order); moving the world rigidly moves the Gaussians by the same transform.

The results are rows 13–15 of the table. For following the ball, 3DGS hardly matters — even at 64 mm spacing ball detection stays at 1.00 (the curvature cap keeps at least 146 Gaussians on the ball). What breaks it is **position error** and **colour error**: with chromaticity detection, a colour error beyond the detector's tolerance (0.12) makes the ball disappear. The hole is different.

| Poses where the hole was read (of 40) | Mesh | 3DGS 2 mm spacing | 3DGS 4 mm spacing |
|---|---|---|---|
| 480 × 360 | 14 | 1 | — |
| twice the resolution | 23 | 16 (median error 2.3°) | 0 |

At 480 × 360 the ball is 17 px and the hole 5 px. The 3DGS blur (about 1 px) comes in from both sides and fills the hole. **Reading the hole needs pixels on the ball and Gaussians inside the hole.** To do spike tricks (the spike into the hole), the cameras must sit on the better side of the bottom-right of this table.

### Catching in another cup, one after another (consecutive tricks)

After a catch, carry on from that state and catch in another cup: the association's graded trick **moshikame** (big cup and base cup in turn) and the three-cup sequence big → small → base.

```
Toss     : accelerate the cup holding the ball upwards and stop it harder than g → the ball leaves when the cup decelerates faster than it (apex = v²/2g at release)
Turn     : in flight, rotate the ken and cross piece (one rigid body) to bring the next cup up (wrist ≤ 30 rad/s, assumed)
Catch    : carry the next cup under the landing point and move it with the falling ball to match its speed (a hand controller that targets position and velocity)
Perceive : the "flight start" from the cup is also found from images (two frames in a row 12 mm away from the cup seat) → parabola → next cup
```

![Ball height during the combo](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/11_combo_height.png)

*↑ Ball height over 10 moshikame catches in a row (image-only closed loop). It rises and falls on a parabola and is caught by the next cup after the turn. The small dip after each catch is the cup moving with the ball to match its speed (the knees' cushion).*

On images alone, moshikame and the three cups both run **10 in a row** (grade 5 on the association's moshikame table), relative speed at touchdown 0.41–0.48 m/s. **A hand controller that targets only position catches nothing with the apex 20 cm above the cup** — the cup tries to stop at its target and cannot match a ball arriving at 1.9 m/s. A person "catching with the knees" is a velocity-matching controller.

Honestly: without noise, 100 in a row is the same cycle repeated (the toss is fixed by a closed form and the ball goes straight up), so the count is no evidence of robustness. With 2 px of pixel noise moshikame breaks after 3 and the three cups after 6 (the target jitters with every refit just before touchdown).

### ★ Where implementations go wrong

#### 1. Adding perception does not mean it feeds the controller

It happens that the parts which triangulate from images and fit a parabola exist, while the plan that moves the cup is still handed the world's true (p, v). The prediction is only used for scoring, and the closed loop never looks at the images. Gate it as "number of estimates the plan received = number of estimates that came from images" (rows 7 and 13).

#### 2. A string cannot stay taut above 109.47°

Gate the period of a pendulum released from rest at "string, 120°" and it fails. Above θ₀ = 90° the tension is negative from the start, and even launched from the bottom the string goes slack at cos θ_s = (2/3) cos θ₀. Measure large-amplitude periods with a rod, and give the string a slack-angle gate.

#### 3. Without a dodge, a ball rising from straight below hits the cross piece

Pulled straight up, the ball rises from directly beneath the kendama. Left alone it passes through the cross piece (the physics does not resolve the collision, so it passes silently). Measure the ball–kendama gap every step and count contact as failure, and in the second half of the lift move the hand 10 cm towards the string hole. Dodging the other way let the ken hide the ball from a camera and worsened the prediction.

#### 4. Deciding "slack" on one frame fires while the string is taut

Judging "the ball is closer to the string hole than the string length" on a single frame reports slack while taut under 2 px of pixel noise. Require two frames in a row.

#### 5. A hole made as "a dark disc on the surface" vanishes in 3DGS

On a mesh a disc looks like a hole. 3DGS sorts Gaussians by the depth of their centres, so from an angle the ball's own Gaussians in front cover a disc floating 0.3 mm above the surface, and the hole was read in 0 of 40 poses. Make it what it really is: a 40 mm deep cavity (dark walls and bottom).

#### 6. Gaussians thinner than a pixel get fat unless compensated

Adding 0.3 px² to the 2-D covariance for antialiasing makes sub-pixel Gaussians (the string, cup rims) stay opaque while growing to 0.55 px or more (the string rendered 3 pixels wide). Scaling opacity by √(det Σ / det(Σ + 0.3 I)) (Mip-Splatting) preserves the sum of alpha (gated).

### What it is not for

**This is not real video.** It is a synthetic world with ground truth. The 3DGS is not learned from photos either; it is built from the true shape and degraded with error knobs. It is a tool to measure "does image processing work on the 3DGS representation and renderer", and it claims nothing about reconstruction quality itself.

**The ball's rotation is not solved.** The rendering convention is that the string hole faces the knot while taut and the ball keeps its last pose once slack. The hole direction in flight is not ground truth, and spike tricks are not in yet.

**A catch is a geometric test.** Bounce and rolling on the rim are not handled; relative speed ≤ 1 m/s is an assumed threshold. The 15° tilt of the cup grip, the cup depths and the 75 g ball are assumptions. The JKA 16-2 dimensions come from a user-supplied description; the primary source was not checked.

**Why the candle is harder than the base cup cannot be expressed.** The ken moves as a rigid, translating body, so the weak support of pinching fingers is absent, and the numbers come out as the same relative motion as the base cup.

### Run it

```bash
py -3.11 examples/poc_kendama.py            # 16 gates (about 171 s without figures)
```

```python
import numpy as np
import fullseye as fs

kp = fs.ledger.kendama_params(trick="ozara")          # JKA 16-2 model, big cup (cup grip)
print(round(np.degrees(fs.ledger.tether_slack_angle(np.radians(150.0), kp["pendulum_length"])), 2))
# 125.26                                               ← launched from the bottom with the energy of 150°, the string goes slack here

w = fs.ledger.kendama_world(kp)                       # world with ground truth (ken, cross piece, ball, string)
gs = fs.ledger.gs_from_world(w, spacing=0.004)        # turn the world into 3DGS (4 mm spacing)
rig = fs.ledger.kendama_rig(kp)                       # two cameras
c = rig[0]
img = fs.ledger.gs_render(gs, c["pose"], c["K"], c["width"], c["height"])["color"]
print(img.shape)
# (360, 480, 3)
```

Set `trick` in `kendama_params` to `"kozara"` / `"chuzara"` / `"rousoku"` and only the grip changes, with the same plan. With `camera_perceiver(world, rig, render_fn=fs.ledger.gs_render_fn(gs))` the closed loop's perception looks at 3DGS images.

---

This part produced **11 figures** in all — [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_kendama)

#### The remaining figures of this part

![Catching in the big cup in the mesh world](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/05_catch_gif.gif)

*↑ The image-only closed loop in the mesh world (camera 2, 100 fps at 1/10 speed). The cross is the predicted landing point.*

![Prediction error vs frames](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/06_prediction_error_vs_frames.png)

*↑ Error of the position at the catch read from the parabola fitted to n frames after slack (log10 mm on the vertical axis).*

![3DGS knobs](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/09_gs_noise_knobs.png)

*↑ 3DGS knobs and ball detection rate. Spacing does not matter; position and colour errors do.*

[![Tension closed form](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/03_tension_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/03_tension_closed_form.png)

*↑ The integrator's tension and the closed form m(v²/L + g cos θ). The string goes slack at the angle where it reaches 0.*

[![Pixel noise and success rate](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/07_success_vs_pixel_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/07_success_vs_pixel_noise.png)

*↑ Pixel noise and success rate (20 trials each). Flat up to 2 px because of the room on the cup rim.*

[![A camera frame](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/01_rig_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/01_rig_view.png)

*↑ A frame from camera 2 (ball at its apex). The inset re-renders the same camera at three times the resolution.*

---

## Next time

Spike tricks (the spike into the ball's hole). The ball's rotation is solved and the hole's direction read from images to line up the spike — as row 15 shows, that needs pixels on the ball. After that, the coefficients of restitution and friction are measured from real video (one high-speed camera).
