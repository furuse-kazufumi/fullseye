---
guide: depth_sensors
dim: 3d
title: Depth sensors — ranging principles, real-device figures, how dropouts appear
title_en: Depth sensors — ranging principles, real-device figures, how dropouts appear
title_zh: 深度传感器知识 —— 测距原理、实机数值、缺测的表现
title_tw: 深度感測器知識 —— 測距原理、實機數值、缺測的表現
title_ko: 깊이 센서 지식 — 측거 원리·실기 수치·결측이 나타나는 방식
title_de: Tiefensensoren — Messprinzipien, Werte realer Geräte, wie Messlücken entstehen
title_hi: Depth sensors — ranging के सिद्धांत, असली devices के आँकड़े, dropouts कैसे दिखते हैं
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: 3d/lidar_projection, 3d/range_image, 3d/structured_light, 3d/plane_sweep_stereo, 3d/two_view, 3d/depth_denoise, 3d/tsdf_fusion, 3d/fusion, 3d/resolution, 3d/preprocess
lang: en
translation_of: docs/ops/3d/guides/depth_sensors.md
source_sha256: 0c782a8f0febb00aab76ed5197768682ade64d5f7ad9929b5c98b8537060f75f
---

# Depth sensors — ranging principles, real-device figures, how dropouts appear

The 3-D family has 347 ops, but **where the point clouds that feed them come from** was not written
anywhere. This document is not a description of ops — it is teaching material on the **origin** of the values passed to
`lidar_projection` / `range_image` / `structured_light` / `plane_sweep_stereo` / `two_view` / `depth_denoise` /
`tsdf_fusion`, and on how real devices fail.
It sits in the same position as `optics/guides/mv_*.md` on the 2-D side (sensors, cameras, frame grabbers, cables, standards);
this is the 3-D counterpart.

---

## 1. There are only 5 ranging principles — and each one's error behaves differently

**The first thing to look at in selection is not the absolute accuracy but how the accuracy scales with distance.**
Get this wrong and you pick the model whose catalogue numbers look good, and miss on site.

| Principle | Representative | Distance dependence of ranging error | Design values that matter |
| --- | --- | --- | --- |
| **Passive stereo** | Ordinary stereo cameras | **σ_Z ∝ Z²** | Baseline B, focal length f, sub-pixel precision of disparity |
| **Active stereo** | RealSense D4xx | Same as above (it only adds texture by projection) | In addition to the above, the reach of the projector |
| **Structured light** (phase shift / Gray code) | Zivid, Photoneo | Same as above, but **B can be made large, so the coefficient is small** | Period, gradation and exposure of the projected pattern |
| **Laser triangulation** (line profiler) | Keyence LJ-X | Same as above. **Cuts the measuring range to a few mm to deliver µm** | Reference distance, receiving angle, X pitch |
| **Direct ToF (dToF)** | Ouster, Livox | **Almost independent of distance** (set by time resolution) | Pulse width, time resolution, amount of returned light |
| (Indirect ToF / iToF) | Some ToF cameras | Set by phase resolution. **Has wrap-around** | Modulation frequency (= unambiguous range) |

### The triangulation formula (it explains everything)

```
Z = B·f / d          B = baseline [mm], f = focal length [px], d = disparity [px]
δZ = Z² / (B·f) · δd
```

**It worsens with the square of distance.** That is why passive / active stereo cannot be used at long range, and
the reason structured light can deliver µm-class results is that it makes B·f large and fixes Z small.

*Reading a catalogue % figure as disparity error*: the D455 has a 95 mm baseline, 1280×720 and HFOV 87°, so
f ≈ (1280/2)/tan(43.5°) ≈ 674 px (**a rough estimate** — strictly, use the HFOV of the left imager.
The published "depth FOV" is narrower by the invalid band, so this f comes out somewhat small).
The nominal "under 2% at 4 m" corresponds to

```
δd = δZ·B·f / Z² = 80 × 95 × 674 / 4000² ≈ 0.32 px
```

In other words, this number is a claim that "sub-pixel matching is working at 1/3 pixel", and
it does not hold as is on surfaces without texture.
**When you see a % figure, do this conversion.**

### The dToF formula

```
σ_Z = c·σ_t / 2      c = speed of light, σ_t = time resolution
```

Distance does not enter — this is why LiDAR can hold cm even at 100 m.
However, the returned light falls off as **1/Z²**, so at long range it is not the accuracy but the **detection probability** that drops.
This is why catalogues write ranges with reflectance attached, such as "170 m @ 80% reflectivity" and "90 m @ 10% reflectivity".
**A maximum range that does not state reflectance cannot be used for comparison.**

---

## 2. Real-device figures (primary sources only)

No guessed values are included. Everything below is from manufacturers' published specifications (sources at the end).

### 2.1 Active stereo — Intel RealSense D455

| Item | Value |
| --- | --- |
| Method | Stereo (with IR projector) |
| Baseline | **95 mm** (D435 series 50 mm, D415 55 mm, D405 18 mm) |
| Depth FOV (16:9) | H 87° / V 58° / D 95° |
| Depth output | Up to 1280×720, up to 90 fps |
| Recommended range | 0.6 – 6 m |
| **Min-Z** (1280×720) | **520 mm** (350 at 848×480, 180 at 424×240) |

The key point is that **Min-Z changes with resolution**. Lowering the resolution lets you get closer — because the upper limit of disparity is
set by the pixel count; "too close to measure" can sometimes be avoided by lowering the resolution.

**Invalid depth band** (a structural dropout for which Intel publishes a formula):

```
invalid band width [px] = B·f / Z
```

For the D455 at Z = 1 m, 95 × 674 / 1000 ≈ **64 px** at the left edge is always invalid.
It is a region not seen by the right imager, so in principle it cannot be filled. **If you make synthetic depth images,
always include this band** (without it, the learning side ends up with a model that trusts the image edge).

### 2.2 Structured light (industrial) — Zivid 2+ M130

| Item | Value |
| --- | --- |
| Imaging | 2448×2048 (5.0 MPx), native 3D colour |
| Focus distance | 1300 mm / working range 800 – 2700 mm / optimal 1000 – 1600 mm |
| Field of view | 790 × 650 mm @ 1300 mm |
| **Point precision 1σ** | **210 µm** @ focus distance |
| **Local planarity precision 1σ** | 300 µm |
| **Global planarity trueness error** | < 0.24 mm |
| **Dimension trueness error** | < 0.35 % (focus distance, room temperature) / < 0.60 % (optimal range, full temperature range) |
| Acquisition time | 50 ms – 1500 ms (including processing) |
| Light source | Projector 360 lm (1×) to 900 lm (2.5×), IEC 62471-5 RG2 |

**Listing precision and trueness separately** is this manufacturer's virtue,
and that is what to read for. A point precision of 210 µm is "how little it scatters over consecutive captures";
a dimension trueness of 0.35 % is "how far off it is when measuring a calibrated length".
**For measurement applications, the latter is what matters.** A catalogue that lists only the former is showing only the numbers
that improve by averaging. Furthermore, it is stated explicitly that trueness **degrades from 0.35 % → 0.60 % with temperature** —
in equipment that warms up inside a cabinet, using the room-temperature spec as is will not match.

### 2.3 Laser triangulation (line profiler) — Keyence LJ-X8060

| Item | Value |
| --- | --- |
| Reference distance | 64 mm |
| Z measuring range | ±7.3 mm (F.S. 14.6 mm) |
| X measuring range | 15 mm (near side) / 16 mm (reference distance) |
| Light source | 405 nm visible, Class 2M |
| Profile data interval (X pitch) | 5 µm |
| **Z repeatability** | **0.4 µm** |
| **X repeatability** | 0.5 µm |
| Points per 1 profile | 3200 points |

The essence is that **it cuts the measuring range to ±7.3 mm** to deliver µm. The triangulation δZ ∝ Z²
does not change, so there is no other way than narrowing the range.
And **what is listed here is repeatability, not linearity** — reading it as "it can measure to 0.4 µm"
is wrong. If you claim absolute dimensions, linearity and calibration are needed separately.

### 2.4 Rotating LiDAR — Ouster OS1 (Rev7)

| Item | Value |
| --- | --- |
| Wavelength / class | **865 nm** / Class 1 (IEC 60825-1:2014) |
| Range | 170 m @ 80% Lambertian / **90 m @ 10% Lambertian** (1024@10 Hz, detection probability > 90%, 100 klx sunlight) |
| Minimum range | 0.0 m (default 0.5 m, 0.3 m selectable) |
| Vertical FOV | 42.4° ±1.0° (+21.2° to −21.2°) |
| Resolution | Vertical 32 / 64 / 128 ch, horizontal 512 / 1024 / 2048, rotation 10 / 20 Hz |
| **Range accuracy** | **±2.5 cm (Lambertian) / ±5 cm (retroreflector)** |
| **Range precision 1σ** | ±0.5 cm (minimum) to ±3 cm (maximum) |
| Range resolution | 0.1 cm |
| Point rate | Up to 5,242,880 points/s (128 ch) |
| Beam | Exit diameter 9.5 mm, divergence 0.18° (FWHM) |
| Data per 1 point | Range, signal intensity, **reflectivity**, near-infrared, channel, azimuth, timestamp |
| False positive rate | 1/10,000 |

What matters is that **accuracy is worse on retroreflective targets (±5 cm)**. It is counter-intuitive, but the returned light is
so strong that the received waveform saturates and the rise time shifts (range walk).
**Synthetic data that uses reflective tape or signs as references will not match reality unless this error is included.**

Also, **the beam angles are not evenly spaced** (the sensor's specification returns beam angles as intrinsics).
Building a range image on the assumption that channel numbers are evenly spaced elevation angles distorts it systematically.

### 2.5 Non-repetitive scanning LiDAR — Livox Mid-360

| Item | Value |
| --- | --- |
| Wavelength | 905 nm |
| Range | 70 m @ 80% reflectivity / **40 m @ 10% reflectivity** (ambient 25 °C) |
| Minimum range | 0.1 m |
| FOV | Horizontal 360° / vertical −7° to +52° |
| Point rate | 200,000 points/s (first return) |
| Range precision 1σ | ≤ 2 cm @ 10 m, ≤ 3 cm @ 0.2 m |
| Angular precision 1σ | < 0.15° |
| Built-in IMU | ICM40609 |

Because **the scan is non-repetitive**, looking at only 1 frame shows it full of holes, and it becomes denser the more you accumulate.
Algorithms that assume "1 scan gives a complete point cloud" break down here.
That the vertical FOV is asymmetric up/down (−7° to +52°) also matters in practice — it cannot see directly below.

---

## 3. How dropouts and errors appear (the heart of synthetic data)

**Putting uniform Gaussian noise on depth** is the most common lie in this field.
The way real devices fail is determined by each principle, and each has its own shape.

| Principle | Failure modes that appear |
| --- | --- |
| Passive stereo | **Holes** on textureless surfaces / **disparity jumps** on repetitive patterns (mismatches become smooth errors, so they are hard to notice) / dropouts on only one side at occlusion boundaries |
| Active stereo | In addition to the above, degrades to passive at long range beyond the projector's reach / **the pattern is drowned out in sunlight** (performance drops suddenly outdoors) |
| Structured light | **Jumps** on specular surfaces (no return) / **interreflection** in concave regions breaks the phase and makes the surface bulge / on transparent or translucent material, subsurface scattering **shifts it deeper** |
| dToF | Inside corners rounded by **multipath** / **flying pixels** at edges (2 distances mix in 1 pixel, giving an intermediate value) / **range walk** on retroreflectors / false points from rain, fog and dust |
| iToF | Multipath is even stronger / **phase wrap-around** turns far objects into near ones (when beyond the unambiguous range set by the modulation frequency) |
| Laser triangulation | **2 kinds** of occlusion (shadow on the projector side, shadow on the receiver side) / no return from specular surfaces / coordinates get dragged at step edges |

**Common to all**: reflectance and intensity channels depend on distance and incidence angle (1/Z², cos θ). Using raw intensity
as a feature as is leads to **learning that depends on distance**. Normalise it, or give the distance explicitly.

---

## 4. Pitfalls of coordinate systems and units

1. **Is depth "z along the optical axis" or "slant range"?** Range images (from LiDAR) are slant range;
   depth cameras usually give optical-axis z. Mix them up and they agree at the centre and **drift systematically only at the edges of the field of view**,
   so a test that looks only at the centre will pass. fullseye adopts optical-axis z in `optscene_depth`
   (the machine-vision convention).
2. **Depth scale.** RealSense defaults to 1 unit = 1 mm, but this changes with model and settings.
   When you receive a depth image as uint16, always carry the scale along with it.
3. **LiDAR rings / channels are not evenly spaced.** As in §2.4.
4. **Origin of the point cloud.** A camera's origin is not the front glass (RealSense: centre of the left imager;
   Ouster: the reference plane of the housing). This becomes a systematic offset of a few mm to a dozen or more mm.
5. **Time.** On a moving platform, things move during the scan even within 1 frame (LiDAR skew).
   For a sensor that attaches a timestamp to each point, the point cloud is meant to be corrected using it.

---

## 5. How to decide on a selection

It is decided in the order **application → distance → required accuracy → principle**. In reverse order (starting from the model) you miss.

| Application | Distance | Required accuracy | Principle |
| --- | --- | --- | --- |
| Inline shape and step inspection | Tens of mm | µm | Laser triangulation (line profiler) |
| Bin picking, assembly | 0.5 – 2 m | 0.1 – 0.5 mm | Structured light |
| Rough perception of people and fixtures | 0.5 – 6 m | cm | Active stereo |
| Localisation and obstacles for mobile robots | 0.5 – 100 m | cm | LiDAR |
| Outdoor wide area, terrain | 10 m and up | cm | LiDAR / photogrammetry |

The core of the decision can be said in 1 line — **if you need µm, cut the measuring range (triangulation);
if you need distance, use a method whose accuracy does not depend on distance (ToF). You cannot have both.**

---

## 6. Connecting to fullseye ops

| Value passed | Origin | Ops used |
| --- | --- | --- |
| Vertical FOV, channel count, angular resolution | §2.4 / §2.5 | `lidar_projection` family (3 op), `range_image` family (4 op) |
| Baseline, focal length, Min-Z, invalid band | §2.1 | `two_view` family (5 op), `plane_sweep_stereo` (2 op) |
| Pattern period, number of phase steps | §2.2 | `structured_light` family (7 op) |
| Point precision 1σ, planarity | §2.2 | `surface_fit` / `registration_metrics` / `metrics` |
| Flying pixels, edge dropouts | §3 | `depth_denoise` family (3 op) |
| Point spacing (voxels coarser than this) | Spatial resolution in §2.2 | `tsdf_fusion` (3 op), `occupancy` (4 op) |
| Distance and angle dependence of reflectance | End of §3 | `photometric` family (4 op) |

---

## 7. Current gaps (honestly)

* **There is no op for a sensor error model.** The 2-D side has `optscene`, which assembles lens, lighting and
  sensor and produces defect images with ground truth. Of the 3-D counterparts — putting **Z²-dependent noise** on depth /
  creating an **invalid depth band** / growing **flying pixels** / **rounding inside corners by multipath** — not even 1
  exists. If synthetic 3-D data is used for learning, this is what is needed first.
* There is no entry point for handling **non-uniform beam angles** (`lidar_projection` assumes even spacing).
* There is no vocabulary for **timestamped point clouds** (skew correction).
* There is no means of reproducing iToF **phase wrap-around**.

---

## 8. Diagnostic table — from symptom to cause

This is what to open first on site. **A symptom can always be explained by tracing it back to the principle.**

| Symptom | Suspect first | How to check |
| --- | --- | --- |
| Accuracy is poor only at long range | Triangulation used at long range (σ_Z ∝ Z²) | Change the distance, measure σ, and see whether it follows Z². If it does, it is **the limit of the method** and post-processing will not fix it |
| A plane warps / dimensions do not match | A trueness-side problem — calibration, temperature | Shoot a calibrated flat plate at **several positions** in the field of view and look at the plane-fit residuals. Compare before and after warm-up (10 min) |
| Holes appear on only one side of the image | Stereo **invalid depth band** | Calculate whether the width matches `B·f/Z` px. If it does, it is a dropout by principle and cannot be filled |
| Only black parts or shiny parts drop out | Returned light (reflectance for ToF, specular reflection for structured light) | Re-shoot with a **white matte dummy** of the same shape. If that fixes it, it is due to the material |
| Rounded inside corners / points at intermediate distance on edges | ToF multipath and **flying pixels** | Extract only the points near the edge and look at the distance histogram. **Points sit in the valley** between the two peaks |
| Only the position of reflective tape is off | Range walk (receiver saturation) | Lower the exposure or intensity and re-measure. If the offset decreases, it is due to saturation |
| The point cloud is dragged diagonally | Movement during the scan (skew) / per-point timestamps not used | Re-shoot while stationary. If that fixes it, motion compensation is needed |
| Horizontal stripes appear when made into a range image | Assumed channel = evenly spaced elevation | Query the sensor's **beam angles** (intrinsics) and re-project |
| Agrees at the centre but drifts only at the edges of the field | Mixing up optical-axis z and slant range | At edge points, look at the ratio of `z` to `‖p‖`. If it is a factor of `cos θ`, they were mixed up |
| 1 frame is full of holes | A non-repetitive-scanning LiDAR used with a single frame | Accumulate several frames and see whether the density rises |

---

## Sources (primary)

* Livox Mid-360 Specs — <https://www.livoxtech.com/mid-360/specs>
* Ouster OS1 Rev7 Datasheet (FW 3.1.x) — <https://data.ouster.io/downloads/datasheets/datasheet-rev7-v3p1-os1.pdf>
* Zivid 2+ M130 Technical Specification (1.5 – 7/25) — <https://www.zivid.com/hubfs/User%20guides%20and%20datasheets/Zivid%202+%20M130%20Datasheet.pdf>
* Intel RealSense D400 Series Datasheet, Doc. 337029-017 (Oct 2025) — <https://realsenseai.com/wp-content/uploads/2025/09/Intel-RealSense-D400-Series-Datasheet-October-2025.pdf>
* Keyence LJ-X8000 series — LJ-X8060 — <https://www.keyence.com/products/measure/laser-2d/lj-x8000/models/lj-x8060/>
