---
guide: virtual_machine_vision
dim: optics
title: Virtual machine vision — enumerating the parameters and an object model
title_en: Virtual machine vision — enumerating the parameters and an object model
title_zh: 虚拟机器视觉 —— 梳理参数与对象模型
title_tw: 虛擬機器視覺 —— 梳理參數與物件模型
title_ko: 가상 머신 비전 — 파라미터 도출과 객체 모형
title_de: Virtuelle Bildverarbeitung — Parameter erfassen und Objektmodell
title_hi: Virtual machine vision — parameters की सूची और एक object model
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, optics/scene, optics/imaging
lang: en
translation_of: docs/ops/optics/guides/virtual_machine_vision.md
source_sha256: cbfb71e92e1e9418da597e5f8b96b9f8641a650352d1a49624bfd0befef7f0cb
---

# Virtual machine vision — enumerating the parameters and an object model

A ledger that enumerates **what has to be given for the image to be determined**, in order to build an observation optical system
in physical space and generate images. If implementation is added while this remains vague, the result is a generator whose output only looks right
and does not correspond to real hardware (user instruction of 2026-09-05: "Please enumerate the sensor parameters, the lens parameters,
the light-source parameters and the layout parameters before proceeding. I think those will naturally
become objects").

## 0. Primary sources (the basis of this ledger)

| Source | Facts taken from it |
| --- | --- |
| SYNOSIS, arXiv:2410.14844 (image synthesis for metal surface inspection) | Rough metal BRDF (roughness 0.05–0.3) / the surface topography is turned into a normal map from focus-variation microscope measurements (lateral 0.44–1.75 µm, vertical 410 nm) (13107², 6.1 µm spacing) / machined surfaces use a procedural model (tool-rotation rings, path, cosine, vibration noise; ring diameter 4–8 mm, centre spacing 0.09 mm) / sandblasting uses ADSN + Efros–Freeman / defects are Boolean differences of 3-D shapes, and the mask is the intersection with the tool shape scaled 0.9–1.0 times / path tracing 256 spp, 8 bounces, 1224×1025 / torus-shaped ring light |
| Adimec / Vision Doctor (bright field versus dark field) | A scratch appears **dark in bright field and bright in dark field** (the contrast inverts). The standard incidence angle for dark field is 10–15° |
| automatica Munich “Virtualising Machine Vision” | Optical digital twin × PBR × defect models × pixel-accurate automatic annotation |

The RAD corpus has **no machine-vision optics field** (the closest are
`halcon_operators_corpus_v2` and `fullseye_3d_vision_corpus_v2`). This file is the knowledge layer that fills that gap,
and subsequent implementation starts from here.

---

## 1. Sensor

| Parameter | Symbol / unit | Effect on the image | fullseye status |
| --- | --- | --- | --- |
| Pixel pitch | p [µm] | Sampling limit 2p. Whether it or the diffraction limit is larger decides what is limiting | `optical_camera(pixel_um=)` ✓ |
| Resolution | W×H [px] | Field of view = W·p·WD/f | ✓ |
| Quantum efficiency | QE(λ) [-] | Electrons = photons × QE. Varies with wavelength | `sensor_spec(quantum_efficiency=)` ✓ (constant) / **the QE(λ) curve is not implemented** |
| Full well | FW [e⁻] | Saturation. Blown highlights do not wrap around | `sensor_capture(full_well_e=)` ✓ |
| Read noise | σ_r [e⁻] | Lower limit in dark areas. Matters in dark field | ✓ |
| Dark current | [e⁻/s] | Matters in long exposures. Dark field uses long exposures | `sensor_spec(dark_e_per_s=)` ✓ (`layout_capture` combines it with the exposure time) / temperature dependence is not implemented |
| ADC bit depth | [bit] | Quantization. At 8 bit, faint contrast is chopped up and lost | ✓ |
| Gain | [e⁻/DN] | Ratio to shot noise | ✓ |
| Shutter type | rolling / global | Distortion of moving objects. Matters for parts on a conveyor | `sensor_spec(shutter=)` is **recorded only**. Rolling distortion is not implemented |
| Spectral sensitivity | S(λ) | Its product with the light-source spectrum decides the effective brightness | **Not implemented** |

## 2. Lens

| Parameter | Symbol / unit | Effect on the image | fullseye status |
| --- | --- | --- | --- |
| Focal length | f [mm] | Magnification m = f/(WD−f), field of view | ✓ |
| F-number / NA | N, NA = 1/(2N) | Diffraction, depth of field, brightness. Working F-number N_w = (1+\|m\|)·N | `optical_budget(f_number=/na=)` ✓ |
| Working distance | WD [mm] | Magnification, layout, where the lighting goes | ✓ |
| Permissible circle of confusion | c [µm] | Depth of field DOF ≈ 2·N_w·c/m² (geometric) + 2λN_w²/m² (wave) | ✓ |
| Airy radius | 1.22·λ·N_w [µm] | Lower limit of how fine defects appear. **Compare with the pixel** | `airy_radius_um` ✓ / `optics.airy_pattern` ✓ |
| MTF | MTF(ν) | Contrast transfer. Defects are high-frequency, so this matters | `optics.mtf_diffraction` / `psf_to_mtf` ✓ |
| Aberrations | Seidel / Zernike | Blurring and asymmetry at the edge of the field | `raytrace.seidel_coefficients` / `opd_map` ✓ (not wired) |
| Distortion | k1, k2 … | Directly affects dimensional measurement | `lensimage.distortion_map` ✓ (not wired) |
| Relative illumination | cos⁴θ and others | Dark edges = defects at the edges are not visible | `optics.relative_illumination` ✓ (not wired) |
| Telecentricity | object-side / bi-telecentric | Magnification does not change with distance = the premise of dimensional measurement | **Not implemented** |
| Chromatic aberration | Δf(λ) | The focus position differs by wavelength | `raytrace.chromatic_shift` ✓ (not wired) |

## 3. Light

| Parameter | Unit | Effect on the image | fullseye status |
| --- | --- | --- | --- |
| Type | LED / halogen / laser | Spectral width and coherence differ | `light_spec(source=)` ✓ (LED narrow-band / halogen broadband / laser single wavelength). Coherence is not implemented |
| Spectrum | S(λ) | Material reflectance depends on wavelength (gold drops at short wavelengths). The specular fraction due to roughness, exp(−(4πσcosθ/λ)²), also depends on wavelength | `render_optscene(wavelength_nm=)` single wavelength ✓ / broadband by superposition with `layout_capture(spectral_samples=)` ✓ |
| Coherence | spatial / temporal | Lasers produce speckle. Halogen does not | **Not implemented** (`optics.gaussian_beam` / `angular_spectrum_propagate` are the foundation) |
| Radiant intensity distribution | I(θ) = I₀cosⁿθ | Uniformity. Illuminance fall-off at the edges | `light_source(cos_exponent=)` ✓ |
| Physical size of the fixture | [mm] | **Whether it appears as a mirror image** = the essence of bright field / dark field | `light["size_mm"]` ✓ (added 2026-09-05) |
| Polarization | linear / circular | Removal of reflections. Jones/Mueller | `optics.jones_*` / `mueller_*` ✓ (not wired) |
| Pulsed / continuous | [µs] | Suppression of motion blur | **Not implemented** |

## 4. Layout

| Parameter | Unit | Effect on the image | fullseye status |
| --- | --- | --- | --- |
| Lighting elevation | [deg] | The dividing line between bright field (the fixture enters the mirror image) and dark field (it does not, 10–15°) | `light_source(height_mm, radius_mm)` ✓ |
| Lighting azimuth | [deg] | Contrast changes with its relation to the scratch direction | ✓ |
| Lighting shape | coaxial / ring / dome / bar / backlight | What enters the mirror image | ✓ |
| Camera tilt | [deg] | **Viewing a flat surface from directly above concentrates the reflection direction at the zenith, and machining marks do not show** (measured) | `optical_camera(tilt_deg=)` ✓ |
| Working distance | [mm] | Magnification, where the lighting goes, depth of field | ✓ |
| Field of view | [mm] | Whether the part fits | `camera["fov_mm"]` ✓ |
| Variation in part pose | [mm], [deg] | The main axis of domain randomization | `inspection_dataset(jitter_mm=, tilt_jitter_deg=)` ✓ |
| Background / jigs | — | The main cause of false detections | Only `scene_plane` / `scene_box` / CSG (CAD meshes not supported) |

---

## 5. Object model (implemented)

Once enumerated, the parameters fall naturally into 4 clusters. Make **1 object per cluster**,
with the layout bundling the remaining 3.

`sensor_spec` / `lens_spec` / `light_spec` / `vision_layout` / `layout_capture`.

```
Layout ─┬─ Sensor  (画素・雑音・飽和・分光感度)
        ├─ Lens    (f, NA/F, WD, 収差, 歪曲, MTF)
        ├─ Light[] (スペクトル, コヒーレンス, 配光, 実体寸法, 姿勢)
        └─ Scene   (部品 + 材質 + 仕上げ + 欠陥)   ← 既存の scene_* op
```

The derived quantities (magnification, working F-number, Airy radius, depth of field, field of view, resolution limit) are
returned by `optical_budget` **in closed form**. The purpose of having this layer is to look here before capturing
and judge whether the configuration is feasible.

## 6. Order of the PoCs (starting from the basic form)

1. **Basic form**: aluminium + hairline + coaxial lighting + single wavelength. 1 line with `observe_surface`.
   The pass criterion is that "the scratch appears dark in bright field" (the sign agrees with the textbook).
2. Add dark field and confirm that the **contrast inversion** appears ✓ (see §7. The roughness of the defect is the key).
3. Sweep the wavelength and confirm that the relation between roughness and wavelength, exp(−(4πσcosθ/λ)²), takes effect.
4. Extend to broadband (halogen) = superposition of several wavelengths, LED = narrow-band, laser = single wavelength +
   speckle.
5. Aberrations, distortion and relative illumination are merged by applying `lensimage.render_through_lens` as a later stage.

## 7. What has been solved / what remains (as of 2026-09-05)

### Solved: contrast inversion between bright field and dark field

With a specular-only model, dark field **cannot work in principle**. To return low-angle 12° light to a camera directly above,
the surface normal must **tilt by (90−12)/2 = 39°**, and the slope of a scratch (5–15°) does not reach that.
Real dark field lights up because a scratch, being the trace where material was scraped away, is **locally rough and returns light by scattering**.

Giving the defect a `roughness_um` makes 1 roughness value cause both
"the specular fraction exp(−(4πσcosθ/λ)²) drops → dark in bright field" and
"the scattering lobe widens (RMS slope √2σ/T) → bright in dark field" at the same time.
Measured: **at roughness 0.4 µm, bright field −59% / dark field +91%**.

**Where the line is drawn**: this is not a rigorous scattering calculation but pseudo-generation by "specular fraction × granularity of the surface texture".
The inversion appears for defect roughness of **0.2–0.6 µm**. Rougher than that, the scattering spreads too much and the defect becomes darker than its surroundings
even in dark field. The division of representation is "resolvable relief = normals, unresolvable relief = roughness", and
the machining marks of `surface_finish` correspond to the former **compressed** into a few octaves of noise.

### Solved: line scan / TDI

`linescan_capture` stacks lines while transporting. If the aspect ratio = (speed/line rate) / (pixel pitch·WD/f)
deviates from 1, the image is distorted (a failure mode specific to line scan that optics cannot fix).
In TDI the charge is transferred together with the object, so **with perfect synchronization all stages see the same object point**
(it only gets brighter). It smears by the amount of synchronization error.

### Solved: transmission bandwidth

`interface_budget` returns the bandwidth-limited rate from the bandwidth of CXP / Camera Link / CLHS / GigE / Opt-C:Link.
16k, 8bit over CXP-12 ×4 gives **324 kHz** ―― consistent with the nominal 300 kHz of the Vieworks VT.
In area scan, conversely, bandwidth is left over (the IMX541 could do 262 fps while
the sensor runs at 18–42 fps). **Which one is limiting swaps depending on the configuration**.

### What remains

* Sensor: the QE(λ) spectral curve, temperature dependence of dark current, conversion gain, PRNU / DSNU,
  rolling-shutter distortion. The catalogue values are Basler's EMVA1288 measurements (including the camera implementation).
* Lens: aberrations, distortion and relative illumination are implemented in `raytrace` / `lensimage` / `optics` but
  are **not wired**. Telecentricity is not implemented. Lenses dedicated to line scan (large image circle,
  sagittal/tangential aberration balance) are not modelled either.
* Light: coherence (laser speckle), polarization (Jones/Mueller exists in `optics`),
  pulsed drive. Broadband goes only as far as superposition with `layout_capture(spectral_samples=)`.
* Parts: CAD meshes cannot be read (analytic shapes + CSG differences only). There are no jigs or transport mechanisms either.
