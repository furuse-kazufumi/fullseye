---
guide: mv_illumination_practice
dim: optics
title: Lighting in practice — wavelength, polarisation, drive modes, ambient light, safety
title_en: Lighting in practice — wavelength, polarisation, drive modes, ambient light, safety
title_zh: 照明实务知识 —— 波长、偏振、点亮方式、外部光、安全
title_tw: 照明實務知識 —— 波長、偏振、點亮方式、外部光、安全
title_ko: 조명 실무 지식 — 파장·편광·점등 방식·외광·안전
title_de: Beleuchtung in der Praxis — Wellenlänge, Polarisation, Ansteuerung, Fremdlicht, Sicherheit
title_hi: Lighting व्यवहार में — wavelength, polarisation, drive modes, ambient light, safety
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/illumination, optics/scene, optics/appearance
lang: en
translation_of: docs/ops/optics/guides/mv_illumination_practice.md
source_sha256: 5ac729f887d0ec8773cdeefedabfc6f380d8050585eb560cfc9bf0b094ac8041
---

# Lighting in practice — wavelength, polarisation, drive modes, ambient light, safety

**The lens decides how sharply a defect is imaged; the lighting decides whether the defect has any contrast.**
Something with no contrast cannot be seen by any premium lens or by any AI.
This is where the most effective skill in visual inspection lies.

The **numerical selection** of the geometry (coaxial / ring / dome / dark field / backlight) is
covered by the "Illumination design" section of `optics/guides/optics_imaging.md` (`illumination_design` /
`defect_contrast` / `lighting_sweep` compute the contrast from first principles).
This document is teaching material on what lies outside that —— **the practice of equipment and the shop floor**.

---

## 1. Geometry at a glance (details in `optics_imaging.md`)

| Defect / purpose | Lighting that works | Reasoning |
| --- | --- | --- |
| Unevenness and engraving on mirror surfaces | **Coaxial** | Returns the specular reflection straight to the camera and darkens only the tilted faces |
| General surfaces | High-angle ring | General purpose. Try this first |
| Rough defects (chips, pits, fine scratches) and foreign matter | **Low-angle ring (dark field)** | Picks up only the scattered component. Flat areas are dark and only rough spots light up |
| Glossy curved surfaces, pigment colour | Dome | Illuminates from all directions to remove specular unevenness |
| Outline, dimensions, holes | **Backlight** | Sees only the shape. Not disturbed by surface patterns |
| Directional texture | Bar (oblique) | Emphasizes relief with shadows |

**Caution**: "Scratches light up in dark field" applies to **scratches with rough flanks**.
A surface that is merely smoothly tilted (e.g. 10°) does not light up in dark field —— it only
specularly reflects the low-angle light away from the camera (`defect_contrast` shows this in numbers).

---

## 2. Choice of wavelength —— the most effective degree of freedom in practice

* **Shorter wavelengths favour fine detail.** The diffraction limit is proportional to λ (Airy radius = 1.22 λ N).
  With the same lens, blue (450 nm) can resolve roughly 3 tenths finer than red (630 nm).
  If you are after fine defects, use a short wavelength.
* **Infrared passes through.** Many resins transmit near infrared, so you can see contents through bags or resin covers,
  or look inside adhesive layers. The silicon sensor itself is sensitive up to **about 1100 nm**
  (the band gap of Si), so up to that point an ordinary camera can capture it.
* With **UV-excited fluorescence** you can see "things invisible in the visible range" —— uneven adhesive application, oil,
  residual foreign matter. **What glows is the object itself, not a reflection**, so the exposure becomes orders of magnitude longer.
* **Create contrast with colour.** Shining light of the complementary colour of the target makes that part dark.
  Capturing green foreign matter under red lighting makes it sink to black. **Monochromatic lighting + a monochrome camera**
  is often better than a colour camera in both sensitivity and resolution.
* ★ **A narrow-band LED + band-pass filter is the standard countermeasure against ambient light.**
  Attaching a filter to the lens that passes only the lighting wavelength removes most of the fluorescent light and sunlight.
  Before building a light-shielding cover, this is worth trying first.

---

## 3. Polarisation

* **Remove glare with crossed polarisers.** Put polarisers on the light-source side and the receiving side and cross them.
  **Specular reflection** from metal or transparent layers **preserves polarisation well**, so it disappears. On the other hand, **diffuse reflection**,
  which comes out after scattering inside, **has lost its polarisation**, so it remains.
  → Used, for example, to remove the glare of the clear coat on a painted surface and see the base layer.
* **Stress birefringence** makes the internal stress of transparent bodies (glass, resin) visible.
  Residual stress in moulded parts, inspection of tempered glass.
* The price is **less light** (1/4 or less with 2 polarisers). Consider it together with the drive modes of §4.

---

## 4. Drive modes —— continuous / strobe / overdrive

| Mode | Light output | Where to use |
| --- | --- | --- |
| **Continuous** | As rated | Stationary objects, simple setups. Brightness drifts until the heat reaches steady state (§6) |
| **Strobe (pulsed)** | **About the same** as continuous | Freezes motion blur. Flashes briefly in sync with the exposure |
| **Overdrive** | **Greatly increased (around 10 times the rating, depending on conditions)** | Solves insufficient light, fast transport and darkness caused by polarisers all at once |

**Key points of overdrive** (primary sources are the lighting makers' application notes):

* The pulse width can be reduced from a few ms down to **1 µs**, and the duty cycle to below 1%.
* Because of heat constraints, **a duty cycle of about 10% is considered the upper limit**.
* Because the duty cycle is low, **heating of the LED junction actually decreases, which favours lifetime**.
  It also gives design room to make the heat sink smaller or unnecessary.
* **Trigger synchronization with the camera exposure is mandatory**. If it slips, "occasionally dark images" get mixed in,
  and it is hard to notice that the lighting is the cause (if these get into the training data, quality drops).

---

## 5. Flicker and beat —— fatal for line scan

* **If the PWM dimming frequency and the line rate produce a beat, horizontal stripes appear in the image.**
  The further you dim, the lower the duty cycle and the more visible they become. The rule is **dim with constant current, not PWM**.
* Ambient light is the same. 100 / 120 Hz from mains power, several tens of kHz from inverter fluorescent lamps.
* Order of countermeasures: ① shield the light ② remove it with a band-pass filter (§2) ③ make the exposure time an integer multiple of the flicker period
  ④ switch to constant-current dimming.

---

## 6. Ageing and maintenance

* **LED luminous flux degrades over time.** Even when driven at constant current, the light output falls as the junction temperature rises.
* That is why you **measure at thermal steady state**. Right after power-on it is bright, and it settles after several tens of minutes.
  An exposure value decided right after start-up is too dark in steady state.
* Equipment that holds its decision threshold in absolute luminance should **be calibrated periodically with a reference plate (white diffuse plate)**,
  or use a power supply with light-output feedback.
* The same applies when making synthetic data —— if the brightness of the real hardware drifts, put that range of variation
  into `inspection_dataset(intensity_jitter=...)`.

---

## 7. Safety (IEC 62471)

A standard that classifies lamps and lamp systems into 4 risk groups.

| RG | Meaning | Guideline |
| --- | --- | --- |
| **RG0** (exempt) | No hazard. No harm even when viewed for a long time | Continuous exposure up to ~10,000 s |
| **RG1** (low risk) | No harm for a limited time | ~100 s |
| **RG2** (moderate risk) | **Does not normally lead to injury because of natural aversion responses such as the blink reflex**, but is uncomfortable even briefly | ~0.25 s |
| **RG3** (high risk) | **Hazardous even briefly**. Especially at close range | — |

* **RG2 / RG3 require warning labels and precautions for use.** Strong industrial lighting commonly falls into RG2
  (e.g. the projector of the Zivid 2+ is RG2 under IEC 62471-5).
* With inspection equipment, **work in which people look into the machine always occurs** (setup, cleaning, troubleshooting).
  Check the RG at design time and make a structure in which no one is exposed in a looking-in posture.
* **Take particular care with UV and blue** (blue-light retinal hazard). UV fluorescence inspection presupposes a light-tight enclosure.

---

## 8. Ambient light and stray light in practice

* Light-shielding covers, small openings, and **matte black** on the inside (black anodizing, flocked sheet).
* **Stray light comes from "where you are not looking"**. A white floor, an operator's white coat, the monitor of the neighbouring machine.
  Look around the room from the camera position and look for bright things.
* If shielding is not enough, use the band-pass filter of §2. **Making the lighting stronger so that ambient light becomes relatively negligible** is
  another option, and that is where overdrive (§4) helps.

---

## 9. Where fullseye stands now (honestly)

| Element | What exists now | What is missing |
| --- | --- | --- |
| Geometry | `light_source` / `light_spec` (ring / dome / bar / coaxial / backlight), `illumination_design` | — |
| Wavelength | `light_spec(wavelength_nm, bandwidth_nm)`, `light_wavelengths` | Real spectral distributions, fluorescence (wavelength conversion from excitation → emission) |
| Polarisation | `light_spec(polarization=)`, `jones_*` / `mueller_*` op | Rendering **carried through polarisation** from lighting → surface → receiver |
| Drive mode | None | Strobe / overdrive, synchronization slip with the exposure |
| Flicker | None | Beat stripes in line scan (a main failure mode of real hardware) |
| Ageing | Can be varied with `inspection_dataset(intensity_jitter=)` | Systematic drift due to heat (monotonic, not random) |
| Safety | None | Risk-group calculation |
| Rendering | `illumdesign` is a sum of point sources | No multiple reflection or interreflection, anisotropic BRDF not supported |

---

## 10. Diagnostic table —— from symptom to cause

| Symptom | Suspect first | How to check |
| --- | --- | --- |
| The defect is not visible at all | The lighting geometry does not fit | Get candidates with `illumination_design(surface, defect)` and try them on real hardware from the top |
| Scratches are visible but the flat area also glares | Specular reflection is entering the camera | Put in crossed polarisers, or change the elevation angle (`lighting_sweep`) |
| A smoothly tilted defect does not light up in dark field | That is normal. Dark field works on **roughness** | Look at the `regime` of `defect_contrast`. If it is `topographic`, dark field is unsuitable |
| Horizontal stripes appear in the image (line scan) | Beat between PWM dimming and ambient light | Constant-current dimming, shielding, exposure an integer multiple of the period |
| Occasionally dark images are mixed in | Synchronization slip between strobe and camera exposure | Look at the trigger signal on an oscilloscope. Check whether it reproduces with continuous lighting |
| Decisions differ between morning and evening | Ambient light getting in | Does it reproduce with shielding? Compare with a band-pass filter inserted |
| The pass rate is high only right after start-up | The LED has not reached thermal steady state | For 60 min after power-on, image the reference plate every 10 min and record the luminance |
| Gradually drifts out of the threshold over several months | LED ageing | Look at the history of the reference plate's luminance. Include periodic calibration in operation |
| Light is insufficient and exposure cannot be extended | Upper limit of continuous lighting | Switch to a power supply that supports overdrive (duty cycle within 10%) |
| Operators say it is dazzling | Risk group | Check the RG and review the exposure at the looking-in position |

---

## Sources

* Advanced Illumination — *The Mechanics of Strobe Overdriving LED Lights for Machine
  Vision Applications* (distinction between continuous / strobe / overdrive, lowering the duty cycle,
  reduced junction heating) — <https://advancedillumination.com/the-mechanics-of-strobe-overdriving-led-lights-for-machine-vision-applications/>
* Smart Vision Lights — *OverDrive Driver* (pulse width from a few ms to 1 µs, duty cycle below 1%,
  duty-cycle upper limit 10%, current on the order of 10 times the rating) — <https://machinevisiondirect.com/blogs/news/svl-overdrive>
* Opto Engineering — *LED pulsing and strobing* — <https://www.opto-e.com/basics/led-pulsing-and-strobing>
* Advanced Illumination — *IEC 62471 Photobiological Safety of Lamps and Lamp Systems*
  (classification RG0–RG3) — <https://www.advancedillumination.com/wp-content/uploads/2023/04/IEC-040119-Photobiological-Safety-of-Lamps-and-Lamp-Systems_042723.pdf>
* Luminus Devices — *Understanding IEC 62471 and IEC 62778 Eye Safety Risk Groups* —
  <https://luminusdevices.zendesk.com/hc/en-us/articles/10532958752397-Safety-Understanding-IEC-62471-and-IEC-62778-Eye-Safety-Risk-Groups-visible-and-nonvisible-light-sources>
