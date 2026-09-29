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

## Next time

Kendama. The string is a **one-sided constraint** (tension is non-negative, the ball falls freely when the string is slack, and the radial speed is lost when it snaps taut), and catching in the cup is a geometric test. The same bounce-and-friction tools score the ball landing in the cup against ground truth. After that, the coefficients of restitution and friction are measured from real video (one high-speed camera).
