---
title: 'Self-Driving Demos Move, So Nobody Measures Whether They Are Right — A PoC Series Scored by Theorems and Second Implementations'
tags:
  - Python
  - NumPy
  - 自動運転
  - アルゴリズム
  - robotics
public_private: false
public_id: 05de90f4d316cd7c681c
---

> **Language**: [日本語](https://qiita.com/furuse-kazufumi/private/1f128b8a36df373c11c7) · **English**

# Self-Driving Demos Move, So Nobody Measures Whether They Are Right — A PoC Series Scored by Theorems and Second Implementations

<!--
  How to append (same order in ja and en; never add to only one):
    1. Add one row to "Where the series stands".
    2. Add one section: figure → recipe → gates and scores → where you will get it wrong → what it is bad at → run it.
    3. Figures are absolute raw.githubusercontent URLs. Bump ?v=N when a figure changes.
    4. Promote the closing "Next" into a section and write a new "Next".
  ★Write only what helps the reader. No development history, no order in which things were fixed.
-->

![A car following the Hybrid A* path into a gap between two parked cars](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/04_parking_gif.gif)

*↑ The car (orange) follows the Hybrid A* path into the gap: 30 forward segments, 12 reversed, 8 gear changes. You can see that it **got in**. You cannot see **how far this path is from the lower bound**.*

## About this article

A car backs into a parallel-parking bay. It finds the lane and follows it. It keeps its distance from the car ahead. Self-driving demos **move**, and nobody checks whether a thing that moves is right.

If the path is not the shortest, the car still ends up in the bay. If the time to collision is overestimated by 20 %, the car still stops in most scenes. If the lane curvature is off by 10 %, the overlay still looks like it hugs the line. **The error does not show in the motion** — that is what makes this field hard to write about.

So the bar for adding self-driving code is three questions:

> **(i) Is there a theorem to use as the gate? (ii) Is there a second implementation, one that assumes nothing about the closed-form structure, to use as ground truth? (iii) Is there a published value (an official dataset metric)?**
> Nothing that fails all three gets written. **Checking an answer with the formula that produced it is forbidden.**

This series lines up the ops built on that bar, one per instalment. Every instalment ships a moving figure and a **score sheet**. No trained models: numpy and scipy only, so every number reproduces on your machine. The code is in [fullseye](https://github.com/furuse-kazufumi/fullseye) and every figure is the script's own output.

## Where the series stands

| # | What is measured | Gate (where the truth comes from) |
|---|---|---|
| 1 | [How a car turns shortest](#1-how-a-car-turns-shortest) | Dubins / Reeds–Shepp theorems / forward integration / SLSQP second implementation / Hybrid A* = closed form on an empty grid |
| 2 | [The driving school opens — build the world that carries its own truth first](#2-the-driving-school-opens--build-the-world-that-carries-its-own-truth-first) | Closed-form areas from the regulation sizes / closed-form ray hits on a plane / two sensors, one world / two point-in-polygon implementations |
| 3 | [Time to collision and safe distance — optical-flow τ and the RSS closed forms, scored by the driving-school world's truth](#3-time-to-collision-and-safe-distance--optical-flow-τ-and-the-rss-closed-forms-scored-by-the-driving-school-worlds-truth) | Closed-form τ from depth + rigid motion / the one-frame identity / published RSS parameters and test values / Lemma 2 = worst-case integration |

---

## 1. How a car turns shortest

### Recipe

```
two poses (x, y, θ) → relative frame → closed-form segment lengths per word → forward-integrate every candidate to verify the endpoint → take the shortest
with obstacles: A* over {left, straight, right} × {forward, reverse} on an occupancy grid, trying a closed-form shot from each node to the goal
```

A front-steered car has a **minimum turning radius ρ** and cannot turn tighter. Under that constraint the shortest path from pose (x, y, θ) to pose (x', y', θ') is **known as a theorem**.

| Term | In plain words |
|---|---|
| Dubins (1957) | For a car that only drives forward the shortest path is arc–line–arc, and the ordering (the word) is one of **LSL / RSR / LSR / RSL / RLR / LRL** — six, no more |
| Reeds–Shepp (1990) | Allow reversing and the shortest path has at most five segments from **48 words** (46 suffice, Sussmann and Tang 1991). Segment lengths are closed form |
| Word | The sequence of segments. L = full left, S = straight, R = full right. **Lower case means reversing** |
| Occupancy grid | The ground cut into cells, each marked obstacle or free |
| Hybrid A* (Dolgov et al. 2010) | A* over continuous poses, pruned per discrete cell (x, y, θ). The practical answer when obstacles exist |
| Admissible heuristic | An estimate of the remaining cost that **never exceeds** the truth. The obstacle-free Reeds–Shepp length is one |
| Analytic shot | Trying, mid-search, whether the closed-form path from here to the goal is collision-free. If it is, the search ends |

There are three ops.

- `car_dubins_path(poses, radius)` — forward only, six closed-form words.
- `car_reeds_shepp_path(poses, radius)` — reversing allowed, 48 words (the same 44 formulas as OMPL).
- `car_hybrid_astar(occupancy, poses, radius, cell, footprint, ...)` — Hybrid A* on an occupancy grid, with a rectangular body or a clearance, and penalties for reversing, gear changes and steering changes.

The closed-form ops **forward-integrate every candidate and verify that it reaches the goal**; a candidate that misses is discarded and counted in `n_rejected`. A copying error in a formula does not raise — **it shows up as a number**.

[![The six Dubins words](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/01_dubins_six_words_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/01_dubins_six_words.png)

*↑ The six words for one pair of poses. Five reach the goal here; the shortest is the answer. The theorem only says "the answer is one of these six", so all six are built and measured.*

### Gates and scores

The only ground truths used are **theorems, a second implementation and a lower bound**. No trained model, no external planner.

| Claim | Measured | Where the truth comes from |
|---|---|---|
| Every closed-form candidate reaches the goal | **0** rejected over 400 random pairs, 6.6 RS candidates per pair (3–12) | Forward integration |
| All 48 words are alive | All **18 word families** appear both as candidates and as the optimum | Counting families |
| The closed form really is shortest | Matches the second implementation to **1e-6** on 3 pairs × RS / Dubins (6 cases) | SLSQP over the segment lengths of each word (assumes nothing about the closed form) |
| The theorem's inequalities and symmetries | distance ≤ RS ≤ Dubins, reversibility, reflection, rigid motion, scaling with ρ, triangle inequality — all hold on 400 pairs + 200 triples | Theorem |
| What reversing buys | Dubins − RS at most **10.647 m** (ρ = 1 m) | — |
| An aligned goal | Dubins 5.000000 = RS 5.000000, word S. Straight back 2 m: RS 2.000000, word s | Distance is the lower bound |
| Hybrid A* reproduces the closed form | On an obstacle-free grid the cost is **23.353319 m = RS 23.353319 m** (1 expansion, first shot). Forward-only equals the Dubins length | Closed form |
| Parallel parking | Cost **16.018 m ≥ lower bound 7.986 m**, 3,385 expansions, 42 segments (12 reversed, 8 gear changes), 0.7 s. The poses are collision-free with the body and satisfy \|Δθ\| ≤ Δs/ρ | Lower bound and kinematics |
| Blocked means refused | Wall the bay off and you get `ValueError`. No partial path | Fail-closed |

The second implementation takes the five segment lengths of a word as unknowns l₁…l₅ (signed; negative = reversing), imposes the three endpoint equations (x, y, and the heading as 2 sin(Δθ/2)) as constraints, and minimises Σ|lᵢ| by SLSQP from many random starts, keeping the smallest. It **knows nothing about the closed form**, so a match rules out both a copying error and a missing word at once.

[![Reeds–Shepp paths to 16 goals](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/02_reeds_shepp_gallery_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/02_reeds_shepp_gallery.png)

*↑ From the origin to 16 goals. Red = forward, blue = reverse, grey = the Dubins (forward-only) path to the same goal. Lower-case letters are reversed segments. With reversing allowed the path is never longer than Dubins.*

[![The parallel-parking search tree](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/03_parking_tree_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/03_parking_tree.png)

*↑ Parallel parking (18 × 8 m, cell 0.25 m, 72 heading bins, body 4.5 × 1.8 m, ρ 5.5 m, a 7.5 m bay). Grey = obstacles (kerb and two parked cars), pale green dots = expanded poses, red = forward, blue = reverse. The obstacle-free Reeds–Shepp path (lower bound 7.986 m) drives through the parked cars, so the cost of 16.018 m is twice the bound. The gap splits into "because of the obstacles" and "because of the pruning approximation", and **the two cannot be separated** (see below).*

### ★ Where you will get it wrong

Anyone who writes this pipeline will step into four holes. None raises an exception and **the car drives plausibly in every one**, so without a gate you will not notice.

#### 1. Fold mod 2π the wrong way and eight words never appear

The 44 Reeds–Shepp formulas are normally copied from OMPL. OMPL's `mod2pi` folds into **(−π, π]**. Copy them into an implementation that folds into [0, 2π) and the condition `t ≥ 0` on a segment length becomes **always true**: the eight CCSC words (LRSL, LRSR and their symmetric images) never appear as candidates. A negative segment length turns into a detour of 2π − |t|, so **you still get an answer and it still reaches the goal** — it just is not the shortest.

A gate that asks "does each candidate reach the goal?" cannot catch this, because it does. Only a **family-counting gate** — group the 48 words into 18 families and demand, over random poses, that every family appears both as a candidate and as the optimum — brings it out. Eight families at zero over 400 random pairs means dead formulas.

#### 2. Write four endpoint equations and the optimiser will not converge

If the second implementation states endpoint agreement as four equations — x, y, cos θ, sin θ — the problem is **over-determined** (five unknowns, effectively three constraints, four equations) and SLSQP returns infeasible or inf. Write the heading agreement as **one** equation, `2 sin((θ_end − θ_goal) / 2)`. Never make both sin and cos equalities.

#### 3. Collision checking eats 80 % of the time

A naive Hybrid A* takes tens of seconds for one parallel-parking run. Profile it and **collision checking is 80 %**. Three things work: (a) sample the rectangular body, transform all samples to grid coordinates at once, and look them up through a flat index `flat[iy·W + ix]`; (b) collision-check only the **shortest** analytic candidate, not all of them; (c) shoot more often near the goal (once every ⌈h / step⌉ expansions for a node with cost-to-go h). Together, **37 seconds become 1 second**. Do (a) first — (b) and (c) do not change correctness, which makes their effect hard to measure in isolation.

#### 4. "Unreachable" is sometimes the right answer

Discretisation changes the answer. A 6.5 m bay (car length + 2.0 m) was **unreachable** at cell 0.25 m with 72 heading bins; a 7.5 m bay is reachable. On a narrow 12 × 8 m grid, a forward-only (Dubins) path **leaves the grid**, and unreachable is the correct result. In both cases the op raises `ValueError`. Refusing is safer for whatever runs downstream than returning a partial path that looks like a near miss. If you keep the gate **"exact match with the closed form on an empty grid"**, you can tell whether an unreachable result is the discretisation's fault or the implementation's.

### What it is bad at

**No moving obstacles and no speed.** This is geometry only — which path — and when and how fast to drive it is another layer. Planning around pedestrians and oncoming traffic is a different tool that adds a time axis on top of this op.

**Hybrid A* is not optimal.** Pruning per discrete cell introduces an approximation, so there is no guarantee that 16.018 m is the shortest path among the obstacles. Of the 8 m gap to the lower bound of 7.986 m, the obstacle part and the approximation part cannot be separated. All that can be said is "at or above the lower bound, collision-free, kinematically feasible" — and that is what the score sheet says.

**Curvature is not continuous.** Both Dubins and Reeds–Shepp switch the steering instantly at segment boundaries. A real car needs clothoid joins (CC-steer) or downstream smoothing.

**Large grids are slow.** This is pure-Python heapq; do not use it for 100 × 100 m at cell 0.1 m. It is for ground truth in research, small car parks and teaching.

### Run it

```bash
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
py -3.11 examples/poc_car_parking.py            # 7 gates and 5 figures, about 16 s
```

```python
import numpy as np
import fullseye as fs

poses = np.array([[0.0, 0.0, 0.0],            # start (x, y, θ)
                  [4.0, 3.0, np.pi / 2]])     # goal
rs = fs.ledger.car_reeds_shepp_path(poses, radius=1.0)
print(rs["word"], round(rs["length"], 4), rs["n_candidates"], rs["n_rejected"])
# LSL 5.1763 9 0     ← word, length [m], surviving candidates, candidates the integration rejected (if not 0, suspect the formulas)

occ = np.zeros((32, 72), bool)                # 8 × 18 m at cell 0.25 m
occ[:2, :] = True                              # kerb
res = fs.ledger.car_hybrid_astar(occ, np.array([[2.0, 4.2, 0.0], [7.5, 1.5, 0.0]]),
                                 radius=5.5, cell=0.25, footprint=(4.5, 1.8, 1.0))
print(res["cost"], ">=", res["lower_bound"], res["n_expanded"])
```

Always look at `n_rejected`. A non-zero value does not mean your poses are bad — it means **a formula somewhere is dead**.

---

This instalment produced **5** figures in all — [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_car_parking)

#### The remaining figure of this instalment

[![Ground-truth scatter](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/05_truths_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/05_truths.png)

*↑ All 11 ground truths: 6 from the second implementation, 3 aligned goals, 2 empty grids. Every point sits on the diagonal.*

## 2. The driving school opens — build the world that carries its own truth first

![Waiting at a red light, threading the crank, merging onto the loop](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/05_drive_gif.gif)

*↑ A chase camera with the LiDAR (16 beams) points overlaid. Grey = road, yellow = kerb, red = car, green = signal. Red light → intersection → crank (with reversing) → link road → loop. That the car **drove** is visible. How many centimetres its corners crossed the kerb line, and which face every LiDAR point came from, is not — but the world knows, so it can be counted.*

Part 1 had only the geometry of paths; there were no sensors. To score a sensor you need a **world in which what it sees is decided in advance**. The ground truth of real datasets is human labelling: the edge of every box and the label of every point is somebody's judgement. So this part builds the world instead — not with arbitrary sizes, but with the numbers of **Appendix 3 of the Road Traffic Act Enforcement Regulations (standards for designated driving-school courses, ordinary licence)**.

### Recipe

```
regulation sizes → one polygon per element (crank, S-curve, slope, parallel parking, turnaround, level crossing, loop, main roads)
       → place with (x, y, yaw) → union = drivable region
       → 3-D world: ground plane + kerb bands + lane paint + CC0 cars / signals / signs (every face carries a label and a colour)
       → fire a spinning LiDAR at the mesh (points, range image, face labels) / render the in-car camera (colour, label, depth)
       → drive it with round 13's Hybrid A* and score every pose and every frame
```

| Term | Meaning here |
|---|---|
| Loop course | Oval. Straights ≥ 80 m, width ≥ 8 m. The outer ring of a driving school; the exercises sit inside it |
| Main roads | Roads ≥ 7 m wide crossing at right angles and joining the loop. Corner radius ≥ 3 m |
| Crank | 3.5 m wide, 12 m between the bends, entries ≥ 4 m, 1 m fillet on the inner corners (ordinary licence) |
| S-curve | 3.5 m wide, 7.5 m radius (outer arc), two arcs of 3/8 of a circle in opposite senses |
| Turnaround | A 3.5 m bay, 5 m deep, beside a 3.5 m road, 1 m fillets |
| Slope | ≥ 7 m wide, ≥ 1.5 m rise, gentle grade 6.5–9 %, steep 10–12.5 %, ≥ 4 m flat top |
| Range image | One LiDAR sweep on a grid: row = elevation (beam), column = azimuth, value = range |
| Inverse sensor model | The rule that turns "a return came back at this range" into occupancy updates of grid cells (here: just dropping kerb points into cells) |

The new ops live in three modules. **drivecourse** (regulation-size 2-D polygons; truth = closed-form areas), **driveworld** (the 3-D world; CC0 Kenney Car Kit / City Kit Roads meshes scaled to real dimensions; the camera image is looked up from triangle ids), and **lidarsim** (Möller–Trumbore ray–triangle intersection, accelerated by binning every triangle by the azimuth and elevation intervals it subtends from the sensor; 80 k triangles × 58 k rays in under a second).

[![Plan of the school](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/01_course_plan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/01_course_plan.png)

*↑ From above. The loop (80 m straights, 8 m wide, R 30 semicircles) with the cross of main roads inside (four signals). Crank to the north-east, S-curve south-west, slope south-east (the dark patch is the ramp), parallel parking and turnaround north-west, level crossing on the eastern main road. The exits rejoin the loop through link roads, so you can circulate.*

[![The same world at an angle](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/02_world_oblique_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/02_world_oblique.png)

*↑ The 3-D world. Kerbs (0.15 m) and lane paint follow the polygon edges and are left out at the joints. Cars, signals, signs, street lights and cones are CC0 meshes. Every face has a label and a colour.*

### Gates and scores

Three kinds of truth: **closed forms derived from the regulation sizes, closed-form ray hits on planes and boxes, and the identity between two sensors looking at one world**. No trained model and no external simulator.

| Claim | Measured | Where the truth comes from |
|---|---|---|
| The polygons are the regulation sizes | For the 5 elements with arcs, the shoelace area **converges monotonically** to the closed form as the arc goes 16 → 64 → 256 → 1024 points (crank 3.1e-5 → 7.5e-9, S-curve 2.8e-3 → 6.8e-7). The 4 arc-free elements match **exactly** | Closed forms (crank = w·L + 2r²(1 − π/4), S-curve = 2·(3/8)·π·(7.5² − 4²) + entries, semicircle = π R w) |
| The LiDAR measures a plane correctly | **10,903 points** on flat road: range vs h/(−sin e), relative difference **2.1e-16** | Closed form |
| The two sensors see one world | 3,450 LiDAR points projected into the camera: median relative depth difference **2.9e-3**, label agreement **100 %** (1-pixel tolerance; 99.1 % pixel-exact) | Identity |
| Car points are inside cars | 1,607 points labelled "car" lie inside the placed car boxes (pose + real size): **100 %** | The world's own placement |
| Kerb points are off the road | An occupancy grid built from 4,667 kerb points is a subset of the true occupancy (outside the polygons) dilated by one cell (precision **1.0000**), in all 68 driving frames | Point-in-polygon (two implementations: even-odd and winding) |
| The driven path does not derail | Over 997 poses the corners of the body cross the kerb line by at most **0.117 m ≤ half a cell (0.125 m)**; on the exact polygons 11 poses cross (the planner's resolution) | Polygons |
| Zero point | Driving the crank in a straight line derails in **50** of 60 poses | — |
| The camera reads the signal | From the lit pixels of the 160 lamp pixels: red → `red`, green → `green`; with the lamps off → `unknown` | The world's own state |

[![One LiDAR sweep](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/03_lidar_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/03_lidar_sweep.png)

*↑ A sweep 10 m before the stop line (32 beams, −25° to +15°, 0.5°; 10,903 points on the road). Points are coloured by the label of the face they hit — that this is generation-time truth rather than human labelling is the whole value of the world.*

[![LiDAR over the in-car camera](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/04_camera_with_lidar_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/04_camera_with_lidar.png)

*↑ The same instant from the in-car camera (60°, 640 × 400) with the LiDAR points projected onto it. Point depth vs pixel depth and point label vs pixel label agreeing is the "two sensors, one world" gate. The signal is red.*

### ★ Where you will get it wrong

#### 1. The regulation 3.5 m width cannot be driven forward with max-steer-and-straight primitives

Part 1's Hybrid A* uses {left, straight, right} × {forward, reverse} motion primitives. With a 4.5 × 1.8 m car, the regulation crank (3.5 m wide, 1 m fillets) is **unreachable forward-only** — at 0.25 m cells with 72 heading bins and at 0.125 m with 144 — the search exhausts its open set after a few dozen expansions. The S-curve (outer 7.5 m, inner 4 m) is the same. Allowing reversing gets through (crank: cost 57.9 m, 14 reverse segments; S-curve: 29.5 m, 1). The real driving test allows reversing too, with points deducted per manoeuvre. Without **intermediate steering angles** in the primitives, a corridor that fits geometrically does not fit after discretisation — the opposite of "it moved so it is right": **it did not move, and that was not wrong**.

#### 2. "Collision-free" from the planner still pokes 12 cm over the polygon

Collision checking is per cell (0.25 m). Measured on the exact polygons, 11 of 997 poses have a body corner over the kerb line, by up to 0.117 m. That is within half a cell, so the planner kept its promise — but **"collision-free" is only as strict as the resolution**. The gate sits at half a cell and reports the number of crossing poses and the largest excursion. If you must not touch the kerb, add clearance or refine the grid; both cost time.

#### 3. Elements that touch edge to edge grow a kerb wall across the joint

If the loop's straights and semicircles meet exactly on a shared edge, neither end edge is "inside the neighbour", so both grow kerbs — **a wall across the road**. The LiDAR saw it and dropped kerb points into cells that should be drivable (precision 0.90). Two fixes: overlap adjacent elements by 5 cm, and skip a 0.5 m edge piece if **either endpoint or the midpoint** lies inside a neighbour. Testing only the midpoint leaves pieces half across a mouth, and they become walls.

#### 4. The lamps end up buried inside the signal head

The signal mesh has a box for a head; placing the lamp discs just in front of its centre hides them behind the box face — **0 pixels** in the camera. Moving them outside the front face gives 160. A second trap: classifying by the **mean colour** of one lit and two dark lamps lets the dark ones dominate and green cannot be read. Classify on lit pixels only (max channel > 0.5).

#### 5. Thin objects land on a different face one pixel over

A kerb is 0.15 m tall — a two-pixel band at 20 m. Comparing a projected LiDAR point with the label of **the same pixel** gives 99.1 %, and most misses are kerb points landing on the neighbouring road pixel. Counting a match if the same label appears in the 3 × 3 window gives 100 %. Lane paint (0.12 m wide) is under one pixel far away, so it is counted as the road surface it is painted on. Writing "100 % label agreement" without **the tolerance in pixels** means nothing.

#### 6. Huge triangles vanish behind the camera

Modelling the ground as two enormous triangles makes the road disappear from the in-car camera: the rasteriser drops any triangle with a vertex behind the camera (it does no near-plane clipping by design). A 4 m grid confines the loss to the cell under the camera. The LiDAR has a cousin of this trap: taking a triangle's elevation interval from its vertices' min and max misses the middle of **an edge passing over the sensor** (an edge between two 5.7° vertices reaches 78.7°). Each edge needs its great-circle extremum added.

### What it is bad at

**No moving objects and no time.** The world is static and the car merely follows a pose sequence. No oncoming traffic with speed, no pedestrians. The signal changes colour but has no rule for when.

**Sensor physics is geometry only.** The LiDAR has single returns, no intensity, no beam divergence, no rain or fog, no distortion from ego-motion during the sweep. The camera is Lambert shading only, no shadows, no exposure. This is not evidence that a detector works on a real car; it is a tool for **finding geometric mistakes**.

**The car meshes have toy proportions.** Kenney's CC0 models are stretched per axis to the box dimensions (4.5 m long, 1.8 m wide). The point-cloud shapes differ from real cars.

**Parallel parking has no size in the regulation.** The appendix of the circular is a figure and no primary numeric source was found, so the default bay is car length + 3.0 m, and the docstring says so.

### Run it

```bash
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
py -3.11 examples/poc_driving_school.py         # 14 gates and 6 figures, about 37 s
```

```python
import numpy as np
import fullseye as fs

crank = fs.ledger.course_crank()                                  # regulation: 3.5 wide, 12 between bends, 4 entries, 1 fillet
P = crank["polygon"]                                             # counter-clockwise polygon (K, 2)
area = 0.5 * abs(np.dot(P[:, 0], np.roll(P[:, 1], -1)) - np.dot(P[:, 1], np.roll(P[:, 0], -1)))   # shoelace
print(crank["params"]["regulation"], round(area, 3), round(crank["area_closed_form"], 3))
# {'A': 3.5, 'B': 12.0, 'C': 4.0, 'D': 1.0} 82.682 82.679

world = fs.ledger.world_build(crank, props=[("sedan", 20.0, 2.0, np.pi / 2)])   # make it 3-D and park one car
spec = fs.ledger.lidar_spec(n_beams=16, azimuth_res_deg=1.0)
T = np.eye(4); T[:3, 3] = (2.0, 0.0, 1.64)                        # inside the entry, sensor 1.64 m up
scan = fs.ledger.lidar_scan(world["V"], world["F"], spec, T, labels=world["face_label"])
hit = scan["ranges"] > 0
print(scan["n_hits"], np.bincount(scan["labels"][hit]))
# 2641 [2455  140   22    0    0    0    0    0    0   24]   ← number of points, per face label (road 2455, kerb 140, car 22, …, paint 24)
```

`labels` is the label of the face each ray hit. It is **generation-time truth**, so once you write a detector you can score it against this without waiting for human labels.

---

This part produced **6 figures** in all — [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_school)

#### The remaining figure of this part

[![Truth scatter](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/06_truths_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/06_truths.png)

*↑ Areas of the 8 element kinds (shoelace vs closed form) and 200 road ranges (measured vs h/(−sin e)). Everything sits on the diagonal.*

---

## 3. Time to collision and safe distance — optical-flow τ and the RSS closed forms, scored by the driving-school world's truth

![An oncoming car approaches, passes, and RSS stops the ego car in front of a parked one](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/06_approach_gif.gif)

*↑ In-car camera, 0 → 10 s. While the oncoming car is in view its pixels carry the optical flow (arrows) and the true focus of expansion (cross), with the "true τ" and the "τ from flow" side by side at the top. After it passes, RSS flags the parked car in the ego lane as dangerous (t = 6.0 s), the ego brakes and stops 10.25 m short. **The numbers move** because the world holds the truth — τ and gap are not estimates, they are fixed at generation time.*

Part 2 built the world, but nothing in it moved. This part sends a car the other way. Two questions: **how many seconds until we collide**, and **how many metres should we keep**. The first is Lee's (1976) τ theory — the time to collision with an approaching surface follows from how fast its image grows, with no distance and no speed; flies and humans brake on it. The second is Mobileye's RSS (Shalev-Shwartz et al. 2017) — from a response time and bounds on acceleration it gives, in closed form, the distance below which you are to blame. Both are **textbook formulas**, and in this world both can be checked against truth.

### Recipe

```
Part 2's loop course (south straight, 80 m, left-hand traffic) → ego 8 m/s (north lane), oncoming 8 m/s (south lane), parked car ahead in the ego lane
   → in-car camera 60°, 640 × 400, 10 Hz, 4.5 s (46 frames)
   → τ three ways: truth (depth image + rigid motion between frames, closed form) / from flow (LK → time_to_contact) / from size (square root of area)
   → RSS: closed-form safe distances with the published parameters → time-integrate the worst case and compare → three school scenes with verdict and braking
```

| Term | Meaning here |
|---|---|
| τ (tau) | Time to collision. With Z the depth of the surface and Ż its rate, τ = Z / (−Ż). At constant speed it falls one second per second (dτ/dt = −1) |
| Focus of expansion (FoE) | For a translating camera, the image point the flow radiates from — the image of the heading |
| Optical flow | Where each pixel moved between two frames, (u, v). Here pyramidal Lucas–Kanade, 5 levels |
| RSS | Responsibility-Sensitive Safety: the definition and closed form of the distance at which, whatever the other car does within bounds, your prescribed response avoids contact |
| ρ (response time) | Time from the situation becoming dangerous to the start of braking; the worst case assumes you may accelerate meanwhile |
| a_min,brake / a_max,brake | The least deceleration you are guaranteed to apply / the most the other car might apply |
| Proper response | What RSS prescribes: anything up to a_max,accel during ρ, then at least a_min,brake until stopped |

Two new modules. **drivettc** derives, per pixel and in closed form, the true flow and the true τ from the depth image and the rigid motion; the flow-based τ wraps the existing `time_to_contact` and converts it to seconds. **rsssafety** holds the RSS closed forms for same-direction, opposite-direction and lateral distances, the worst-case time integration, and the verdicts. All three τ values are aligned to **the time of the first frame** — there is a one-frame trap here, described below.

[![In-car camera and flow at t = 4 s](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/02_incar_flow_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/02_incar_flow.png)

*↑ t = 4 s. The flow on the oncoming car's pixels (arrows ×3) points outward from the focus of expansion (cross); its radial speed gives τ = 0.84 s (truth 0.84 s). The road has no texture, so flow exists only on the car and the lamp post.*

### Gates and scores

Three kinds of truth: **closed forms from the depth image and the rigid motion** (τ), **published values** (the RSS parameter table and test values), and **a theorem agreeing with an integration** (Lemma 2).

| Claim | Measured | Where the truth comes from |
|---|---|---|
| The true flow gives τ back (identity) | Feeding the true flow to `time_to_contact` and adding one frame matches the true τ₀ to **8.5e-14** (46 frames, every pixel of the car) | Closed form |
| τ falls one second per second | The car's nearest pixel's τ equals "distance to the front bumper / closing speed" within 8.3e-3, slope **−1.0045** | Poses and speeds |
| Flow yields τ | Over the 22 frames where the car covers ≥ 150 px, LK τ has median relative error **0.026** (90th percentile 0.30); over all 46 frames 0.135 | Closed form |
| Size yields τ | From the square root of the area (0.5 s apart), median relative error **0.045** (90th percentile 0.12); the truth lies inside the quantisation band [area ± perimeter/2] in 17 / 19 frames | Closed form |
| RSS closed forms match the published values | ad-rss-lib's five lateral test values within **0.0065** (tolerance 0.01). Same direction at 50 km/h: **39.8 m** with no acceleration (published ≈ 40), **83.6 m** with 4 m/s² (published "about 80") | Published values |
| Lemma 2 agrees with the worst-case integration | At v = 8 m/s, d_min = 26.28 m; integrating from there the minimum gap is **4.3e-14**. Over 50 random parameter sets \|min_gap − (d₀ − d_min)\| < 1e-13, and collision/no collision agree | Second implementation |
| The school stops in time | Danger at 26.25 m (< 26.28) → speed held for ρ = 1 s, then 4 m/s² → final gap **10.25 m** = gap(t_b) − (vρ + v²/2b) to 1e-9 | Closed form |
| τ shouts, RSS does not | For the car in the other lane true τ falls to **0.30 s**, yet the lateral safe distance is **0.725 m** < the 2.2 m lane gap, and RSS never flags danger | Closed form |
| Drift over and it is dangerous | If the oncoming car drifts sideways at 0.6 m/s the lateral safe distance jumps to **2.45 m** and danger starts at t = 1 s; the longitudinal gap of 58.25 m is then already inside the **82.9 m** opposite-direction distance, and the worst case collides (minimum gap −24.7 m) | Second implementation |

[![The four τ curves](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/03_tau_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/03_tau_curves.png)

*↑ The two truth lines (overlapping) fall from 5 s at slope −1. Flow-based τ (light blue) sits on the truth from t ≥ 2 s and scatters at range where the flow is below one pixel. Size-based τ (orange) stays close throughout.*

[![RSS stops before the parked car](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/04_rss_same_direction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/04_rss_same_direction.png)

*↑ The gap to the parked car (blue) drops below the safe distance (orange, 26.28 m at v = 8) at t = 6.0 s: danger. Speed held for one second, then 4 m/s². The safe distance falls with v during braking.*

### ★ Where you will get it wrong

#### 1. τ from a two-frame flow is the τ one frame later

τ = Z / (−Ż) is an instantaneous quantity. With flow from two frames, an image point moves to Z₀/Z₁ times its distance from the focus of expansion, so `time_to_contact`'s "radius² / (radial flow · radius)" is **Z₁ / (Z₀ − Z₁) frames** — the τ at the second frame, exactly **one frame less** than at the first. At 10 Hz that is 0.1 s, which is 20 % when τ is 0.5 s. Add one frame and it matches the truth to 1e-13 (gate 1). The difference is one frame even when the speed is not constant, so it suffices to decide which instant your τ refers to and be consistent. The size-based τ has the same one-frame offset (Δt·w₁/(w₁ − w₀) at the first frame, Δt·w₀/(w₁ − w₀) at the second).

#### 2. Flow-based τ works only while the flow is one to a dozen pixels

At range (car under 100 px, flow under one pixel) LK τ is 20–70 % off; too close (flow over 50 px) even five pyramid levels lose track. In between, 22 frames give a median of 2.6 %. Lengthening the frame interval to gain flow sounds right and made things worse here (0.3 s apart: four times the error) — LK assumes appearance does not change, and an approaching car changes appearance. "Flow gives τ" is conditional, and the condition can be written in pixels of flow.

#### 3. Size-based τ loses to area quantisation

Since the square root of the area n scales as 1/Z, τ₀ = Δt / (1 − √(n₀/n₁)). One frame apart (0.1 s) the area gain (30 px at τ = 2 s and 300 px) is smaller than the edge quantisation (half of an 80 px perimeter) and the band opens to infinity. Half a second apart the truth lies inside the band in 17 of 19 frames; the two outliers are the car's silhouette not being planar (its side comes into view as it nears). **From the same two frames, flow wants a short interval and size wants a long one** — keep separate intervals if you use both.

#### 4. The lateral RSS formula differs in sign handling between the paper and the public implementation

The paper's lemma is written for the case where both cars are still moving toward each other after ρ; outside that case (one is still moving away) the literal formula adds the receding car's stopping distance **in the approaching direction**. Intel's public ad-rss-lib adds the stopping distance only when the post-response velocity points at the other car, and treats μ differently (paper μ + [·]₊, library [· + μ]₊). The published test values are the library's, so this implementation follows the library and gates that it agrees with the paper inside the paper's assumption (over 100 of 300 random cases satisfy it; agreement to 1e-9). "The paper's formula verbatim" and "the same as the public implementation" are different claims.

#### 5. The closing speed is v cos θ by the camera's pitch

The in-car camera looks slightly down (1.4°). Depth is measured along the optical axis, so the closing speed of the oncoming car is not 16 m/s but 16·cos 1.4° = 15.995 m/s. Writing the truth as "distance / 16" is off by 3e-4 — small, but a 1e-9 gate does not pass. The truth formula must carry the axis direction.

#### 6. The focus of expansion cannot be estimated from flow in this world

A least-squares FoE from the whole flow field lands a median 62 px from the truth: the road has no texture, so flow exists only on the car and the lamp post. This part takes the ego motion as known and supplies the true FoE (reported, not gated). In real footage the road texture is what pins the FoE — **a world without texture kills the estimate**, a failure that tells you what to add to the world next.

### What it is bad at

**Ego motion is known.** The focus of expansion and the mask of the oncoming car's pixels (the world's face ids, standing in for a perfect detector) come from the truth. This is not a score for a whole perception pipeline with a detector and ego-motion estimation; it scores **whether the τ formulas and the RSS formulas agree with the world**.

**RSS verdicts use two axes only**, longitudinal and lateral; intersections, right of way and occlusion (the paper's second half) are not included. The parameters are ad-rss-lib's "initial values for discussion"; neither the paper nor any law fixes numbers.

**The oncoming car moves at constant speed in a straight line.** τ under deceleration, acceleration or mid-lane-change (dτ/dt ≠ −1) is not covered. The formulas apply as they are, but the "slope −1" gate is a constant-speed property.

**The world ends 8 m outside the course** and the road surface is plain. No street trees, pedestrians or crosswalks yet — which is also why no flow can be taken from the road.

### Run it

```bash
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
py -3.11 examples/poc_ttc_rss.py         # 10 gates and 6 figures, about 35 seconds
```

```python
import numpy as np
import fullseye as fs

# τ: one depth image, approaching at 8 m/s for 0.1 s (+z is forward in the camera frame)
K = np.array([[34.6, 0.0, 31.5], [0.0, 34.6, 19.5], [0.0, 0.0, 1.0]])   # 64 × 40, 60° vertical (τ does not depend on K)
depth = np.full((40, 64), 20.0)                                  # a wall 20 m ahead
T = np.eye(4); T[2, 3] = 0.8                                     # 0.8 m closer per frame
truth = fs.ledger.ttc_truth(depth, K, T, 0.1)
flow = fs.ledger.flow_from_depth_motion(depth, K, T)              # the true flow (u, v)
est = fs.ledger.ttc_from_flow(flow["u"], flow["v"], 0.1, foe=fs.ledger.foe_from_motion(K, T))
print(round(float(np.nanmedian(truth["tau"])), 6), round(est["tau"], 6))
# 2.5 2.5                                                         ← 20 m / 8 m/s; identical with the one-frame correction

# RSS: ego at 8 m/s, a stopped car ahead. ρ 1 s, accel 3.5, braking 4 / 8 m/s² (the ad-rss-lib table)
p = fs.ledger.rss_params()
d_min = fs.ledger.rss_longitudinal_same(8.0, 0.0, p)
sim = fs.ledger.rss_worst_case_gap(d_min, 8.0, 0.0, p)
print(round(d_min, 3), round(sim["min_gap"], 9), sim["collided"])
# 26.281 0.0 False                                                ← closed form = integration, exactly zero and no contact
```

---

This part produced **6 figures** in all — [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ttc_rss)

#### The remaining figures of this part

[![Plan view](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/01_scene_plan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/01_scene_plan.png)

*↑ The 80 m south straight from above (t = 3 s): ego (north lane, eastbound), oncoming car (south lane, westbound), parked car (x = 40).*

[![Lateral safe distance](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/05_rss_lateral_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/05_rss_lateral.png)

*↑ In their lanes the lateral gap of 2.2 m exceeds the 0.725 m safe distance, so falling τ (grey) never becomes danger. Once the oncoming car drifts at 0.6 m/s the safe distance jumps to 2.45 m and danger starts at t = 1 s.*

---

## Next
**Widen the world.** This part showed that without road texture the optical flow cannot pin the focus of expansion, and that the world ends 8 m outside the course. Next comes terrain — a generator for continuous relief and road-surface texture — plus signs, street trees, crosswalks and pedestrians, each carrying its truth (which pixel is which object, where the pedestrian is) from generation time. On top of that, the ego motion (focus of expansion) will be estimated from the flow, replacing this part's "known" quantities one at a time.

## References

- L. E. Dubins, "On curves of minimal length with a constraint on average curvature, and with prescribed initial and terminal positions and tangents", *Amer. J. Math.* 79, 1957.
- J. A. Reeds and L. A. Shepp, "Optimal paths for a car that goes both forwards and backwards", *Pacific J. Math.* 145, 1990.
- H. J. Sussmann and G. Tang, "Shortest paths for the Reeds–Shepp car: a worked out example of the use of geometric techniques in nonlinear optimal control", *Rutgers SYCON 91-10*, 1991.
- A. M. Shkel and V. Lumelsky, "Classification of the Dubins set", *Robotics and Autonomous Systems* 34, 2001.
- D. Dolgov, S. Thrun, M. Montemerlo, J. Diebel, "Path planning for autonomous vehicles in unknown semi-structured environments", *Int. J. Robotics Research* 29, 2010.
- The arrangement of the 44 Reeds–Shepp formulas follows OMPL (`ReedsSheppStateSpace`).
- D. N. Lee, "A theory of visual control of braking based on information about time-to-collision", *Perception* 5, 1976.
- H. C. Longuet-Higgins and K. Prazdny, "The interpretation of a moving retinal image", *Proc. R. Soc. Lond. B* 208, 1980 (focus of expansion).
- S. Shalev-Shwartz, S. Shammah, A. Shashua, "On a Formal Model of Safe and Scalable Self-driving Cars", arXiv:1708.06374, 2017 (RSS; Lemma 2 and the opposite-direction and lateral closed forms).
- Intel, *ad-rss-lib* (Apache-2.0): the parameter table in `doc/ad_rss/Appendix-ParameterDiscussion.md` and the expected values in `RssFormulaTests*.cpp`.
