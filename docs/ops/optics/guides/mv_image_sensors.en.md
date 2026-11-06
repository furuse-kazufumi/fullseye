---
guide: mv_image_sensors
dim: optics
title: Industrial image sensors (mainly current products)
title_en: Industrial image sensors (mainly current products)
title_zh: 工业图像传感器(以现行产品为主)
title_tw: 工業影像感測器(以現行產品為主)
title_ko: 산업용 이미지 센서(현행 제품 중심)
title_de: Industrielle Bildsensoren (vorwiegend aktuelle Produkte)
title_hi: Industrial image sensors (मुख्यतः मौजूदा products)
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, optics/scene, 2d/noise
lang: en
translation_of: docs/ops/optics/guides/mv_image_sensors.md
source_sha256: 75db2f3b412e4f7fd88d330e7d0c4b568cb0d7df4503c476ccb7a4ed3bc87c69
---

<!-- fullseye guide: background knowledge around machine vision. Not an op, but teaching
     material that shows where the values passed to ops come from. Related ops: sensor_spec / sensor_catalog / optical_budget -->

# Industrial image sensors (mainly current products)

Unless pixel shift or TDI is used, a camera's **specifications are almost entirely decided by the image sensor**.
What the interface (USB3 Vision / GigE Vision / CoaXPress / 10GigE) changes is
mainly the frame-rate and ROI constraints, not the image quality itself. So the parameters to give
in virtualization are not the camera part number but the **sensor specifications**.

Source: Basler "CMOS sensor selection" (generation, pixel, resolution, shutter, frame rate).
The actual figures for saturation capacity, read noise and QE exist only in **EMVA1288 reports** from Basler and others or in Sony's
datasheets, and are not on general public pages (the tables below state "not public" explicitly).

## Makers

Not many makers build image sensors. Those that are real options for industrial use:

| Maker | Industrial lines | Position |
| --- | --- | --- |
| Sony Semiconductor | Pregius / Pregius S / STARVIS 2 | The de facto standard. The mainstream of global shutter |
| onsemi | XGS / PYTHON | Large format, high speed. XGS is the 3.2 µm generation |
| Gpixel | GMAX / GSPRINT / GSENSE | High resolution, high speed. Strong at medium format and above |
| Teledyne e2v | Emerald / Sapphire | Low noise, high sensitivity. Also leaning toward space / science |
| OmniVision | OG / OS series | Leaning toward automotive and embedded |

## 38 industrial sensors — with EMVA1288 measurements (5 makers side by side)

The source is Basler's table of camera measurements, so **the values listed here are camera-side values**.

* **Resolution** is the number of pixels that camera outputs. Makers sometimes crop the edges and make it **slightly lower than
  the sensor's total effective pixels**, so it may not match the specification of the sensor alone.
* **Frame rate** changes with the interface (USB3 Vision / GigE / 5GigE / CXP-12).
  It is not an attribute of the sensor, so it is not in this table.
* **QE / dark noise / saturation capacity / dynamic range** are EMVA1288 measurements (ace /
  ace 2 / boost), values that include the implementation. A different camera would give slightly different values.
* **Pixel pitch, shutter type and generation** come from the sensor, so they do not change when the camera changes.

### Sony

| Part number | Series | Resolution | Pixel [µm] | Shutter | QE | Noise [e-] | Saturation [ke-] | DR [dB] | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IMX530 | Pregius S 4th | 24.6 MP / 5328×4608 | 2.74 | global | 66% | 2 | 9.6 | 71 | current |
| IMX540 | Pregius S 4th | 24.6 MP / 5328×4608 | 2.74 | global | 66% | 2 | 9.7 | 71 | current |
| IMX541 | Pregius S 4th | 20.3 MP / 4504×4504 | 2.74 | global | 66% | 2 | 9.7 | 71 | current |
| IMX183 | STARVIS | 20.0 MP / 5472×3648 | 2.40 | rolling | 75% | 3 | 13.8 | 71 | mature |
| IMX542 | Pregius S 4th | 16.1 MP / 5320×3032 | 2.74 | global | 66% | 2 | 9.7 | 71 | current |
| IMX304 | Pregius 2nd | 12.3 MP / 4096×3000 | 3.45 | global | 69% | 2 | 10.2 | 73 | mature |
| IMX545 | Pregius S 4th | 12.3 MP / 4096×3000 | 2.74 | global | 67% | 3 | 9.9 | 70 | current |
| IMX226 | STARVIS | 12.2 MP / 4024×3036 | 1.85 | rolling | 83% | 3 | 11.0 | 70 | mature |
| IMX267 | Pregius 2nd | 8.8 MP / 4096×2160 | 3.45 | global | 69% | 2 | 10.2 | 73 | mature |
| IMX546 | Pregius S 4th | 8.1 MP / 2840×2840 | 2.74 | global | 66% | 2 | 9.8 | 70 | current |
| IMX178 | STARVIS | 6.4 MP / 3088×2064 | 2.40 | rolling | 81% | 3 | 14.3 | 73 | mature |
| IMX264 | Pregius 2nd | 5.0 MP / 2448×2048 | 3.45 | global | 68% | 2 | 10.4 | 73 | mature |
| IMX252 | Pregius 2nd | 3.1 MP / 2048×1536 | 3.45 | global | 69% | 2 | 10.5 | 73 | mature |
| IMX265 | Pregius 2nd | 3.1 MP / 2048×1536 | 3.45 | global | 68% | 2 | 10.5 | 73 | mature |
| IMX174 | Pregius 1st | 2.3 MP / 1920×1200 | 5.86 | global | 70% | 7 | 31.8 | 74 | legacy |
| IMX249 | Pregius 1st | 2.3 MP / 1920×1200 | 5.86 | global | 70% | 7 | 31.9 | 74 | legacy |
| IMX392 | Pregius 2nd | 2.3 MP / 1920×1200 | 3.45 | global | 62% | 3 | 10.5 | 72 | mature |
| IMX273 | Pregius 2nd | 1.6 MP / 1440×1080 | 3.45 | global | 63% | 3 | 10.5 | 71 | mature |
| IMX287 | Pregius 2nd | 0.4 MP / 720×540 | 6.90 | global | 63% | 7 | 21.0 | 74 | mature |

### onsemi

| Part number | Series | Resolution | Pixel [µm] | Shutter | QE | Noise [e-] | Saturation [ke-] | DR [dB] | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XGS 45000 | onsemi XGS | 44.7 MP / 8192×5460 | 3.20 | global | 55% | 5 | 9.0 | 65 | current |
| XGS 32000 | onsemi XGS | 32.5 MP / 6580×4935 | 3.20 | global | 56% | 4 | 9.3 | 66 | current |
| XGS 20000 | onsemi XGS | 20.2 MP / 4500×4500 | 3.20 | global | 55% | 4 | 9.2 | 66 | current |
| MT9J003 | onsemi | 10.6 MP / 3840×2748 | 1.67 | rolling | 46% | 6 | 2.8 | 54 | legacy |
| PYTHON 5000 | onsemi PYTHON | 5.3 MP / 2590×2048 | 4.80 | global | 55% | 12 | 8.2 | 57 | mature |
| PYTHON 2000 | onsemi PYTHON | 2.3 MP / 1920×1200 | 4.80 | global | 54% | 11 | 7.8 | 57 | mature |
| PYTHON 1300 | onsemi PYTHON | 1.3 MP / 1280×1024 | 4.80 | global | 53% | 11 | 6.9 | 56 | mature |
| PYTHON 500 | onsemi PYTHON | 0.5 MP / 800×600 | 4.80 | global | 54% | 11 | 7.8 | 57 | mature |
| PYTHON 300 | onsemi PYTHON | 0.3 MP / 640×480 | 4.80 | global | 52% | 11 | 7.1 | 57 | mature |

### Gpixel

| Part number | Series | Resolution | Pixel [µm] | Shutter | QE | Noise [e-] | Saturation [ke-] | DR [dB] | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GMAX3265 | Gpixel GMAX | 65.4 MP / 9344×7000 | 3.20 | global | 52% | 8 | 10.4 | 61 | current |
| GMAX0505 | Gpixel GMAX | 26.2 MP / 5120×5120 | 2.50 | global | 51% | 4 | 4.3 | 60 | current |
| GMAX2518 | Gpixel GMAX | 18.5 MP / 4508×4096 | 2.50 | global | 56% | 3 | 6.7 | 66 | current |
| GMAX2509 | Gpixel GMAX | 9.1 MP / 4200×2160 | 2.50 | global | 53% | 1 | 4.6 | 69 | current |
| GMAX2505 | Gpixel GMAX | 5.6 MP / 2600×2160 | 2.50 | global | 53% | 1 | 4.8 | 70 | current |

### ams

| Part number | Series | Resolution | Pixel [µm] | Shutter | QE | Noise [e-] | Saturation [ke-] | DR [dB] | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CMV12000 | ams CMV | 12.6 MP / 4096×3072 | 5.50 | global | 45% | 14 | 11.6 | 59 | mature |
| CMV4000 | ams CMV | 4.2 MP / 2048×2048 | 5.50 | global | 62% | 14 | 11.9 | 59 | mature |
| CMV2000 | ams CMV | 2.2 MP / 2048×1088 | 5.50 | global | 63% | 14 | 9.3 | 57 | mature |

### Teledyne

| Part number | Series | Resolution | Pixel [µm] | Shutter | QE | Noise [e-] | Saturation [ke-] | DR [dB] | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EV76C570 | Teledyne e2v | 1.9 MP / 1602×1202 | 4.50 | switchable | 47% | 22 | 6.8 | 50 | legacy |
| EV76C661 | Teledyne e2v NIR | 1.3 MP / 1280×1024 | 5.30 | switchable | 59% | 23 | 7.4 | 50 | legacy |

### Where each maker stands (results compared with the same measurement method)

* **Sony Pregius / Pregius S** — the reference for balance. QE 62-70%, noise 2-3 e-, saturation 9.6-10.5 ke-.
  Only the 1st generation (5.86 µm) is in a class of its own with saturation 31.8 ke-, and it is still a candidate if dynamic range matters most.
* **onsemi XGS** (3.2 µm) — its real strength is **large format, APS-C / 35 mm**. It goes up to 44.7 MP (8192×5460),
  a format Sony does not have. QE 55-57%, noise 4-5 e-.
* **onsemi PYTHON** (4.8 µm) — small and fast. But **noise of 11-12 e- is 5 times that of Pregius**,
  which starts to matter in dark scenes and dark field. DR is also lowish at 56-57 dB.
* **Gpixel GMAX** (2.5 µm) — its selling point is **noise on the order of 1 e-** (GMAX2505 / 2509). Saturation is small at 4-5 ke-,
  so DR comes to 69-70 dB, roughly equal to Sony. **The 65 MP (9344×7000)
  GMAX3265** is the only option here for ultra-high resolution.
* **ams CMV** (5.5 µm, formerly CMOSIS) — saturation 9-12 ke-, but **noise 14 e-**. DR 57-59 dB.
* **Teledyne e2v EV76** (switchable shutter) — noise 22-23 e-, DR 50 dB. There is an NIR-enhanced version.

**Implication for selection**: "small pixels = disadvantage" is not true. The GMAX2505 (2.5 µm, noise 1 e-) reaches
DR 70 dB, on a par with Pregius S (2.74 µm, noise 2 e-, 71 dB). What matters is **not the pixel size alone
but the ratio of saturation capacity to noise**, and in applications with small signals such as dark field, noise dominates.

## Camera makers that build their own sensors (cannot be looked up by part number)

The tables above concern makers that "buy sensors and build cameras" (Basler / FLIR / IDS / Baumer /
Allied Vision / JAI …). **Camera makers that design and manufacture their own sensors** have
a different structure, and the specifications cannot be looked up from a sensor part number. **The camera datasheet is the only
source**, so the makers have to be checked individually, 1 company at a time.

| Maker | Sensor | How to get the values |
| --- | --- | --- |
| **Canon** | Has manufactured its own CMOS since 2000. **For its own products only**, not sold externally | Datasheets of its industrial / medical / scientific cameras. The proprietary pixel-level structure is the basis of the performance |
| **Teledyne DALSA / e2v** | Both sensors and cameras in-house (Teledyne Vision Solutions). Emerald / Sapphire / Xineos, line scan TDI | Since it also sells the sensors alone, both datasheets can be consulted (exceptionally easy) |
| **Photron** | In-house CMOS in the FASTCAM SA-Z and others. The Mini 4K uses an in-house 4096×2304 sensor | High-speed camera datasheets. The trade-off between frame rate and pixel count is the main specification |
| **Vision Research (Phantom)** | Custom CMOS of its own design. The v1211/v1611/v2011/v2511 family has **28 µm pixels** (sensitivity first). The TMX family is a back-side-illuminated custom sensor | Camera datasheets. Since the pixels are an order of magnitude larger, the assumptions about saturation capacity and sensitivity are completely different from the tables above |
| **Hamamatsu** | ORCA family. **A mix of in-house and external sensors** (the ORCA-Quest carries a sensor developed by Fairchild Imaging) | Needs checking model by model. Photon-number-resolving lines such as qCMOS are a separate category |
| **Sony** | Makes both sensors and cameras (XCG etc.) | The sensor-side documents can be consulted, so it can be treated the same as the tables above |

**Implication for virtualization**: between 28 µm pixels (Phantom) and 2.74 µm pixels (Pregius S), both the saturation capacity and
the F-number at which diffraction becomes limiting differ by an order of magnitude. The boundary in `optical_budget` of "diffraction 1.22λN_w versus sampling 2p"
is decided by the pixel pitch, so **if you assume a camera with an in-house sensor, unless you give the pixel pitch as the value of the real device,
the conclusion is reversed**.

## Sony STARVIS 2 (rolling / partly global, low light)

IMX675 / IMX678 and others. Their selling point is dynamic range in low light. In visual inspection,
global shutter is needed in many situations, so they are not the main players, but they are candidates for dark-field and low-light applications.

## Values that are not publicly available (datasheet / EMVA1288 required)

The following are **essential** for virtualization but are not in the sources of the tables above:

* Saturation capacity (full well capacity) [e⁻]
* Temporal dark noise / read noise [e⁻]
* Quantum efficiency QE(λ) [%] (spectral sensitivity curve)
* Dark current [e⁻/s] and its temperature dependence
* Conversion gain [e⁻/DN], ADC bit depth
* PRNU / DSNU (pixel-to-pixel variation)

The QE / dark noise / saturation capacity / DR in the tables above were filled in from Basler's EMVA1288 measurements.
What remains unobtained is **the temperature dependence of dark current, conversion gain, PRNU / DSNU and the spectral sensitivity curve QE(λ)**;
these require Sony's datasheets (NDA-level) or each company's detailed EMVA1288 reports.
`optscene.sensor_spec(model=...)` uses the values that are filled in, and records their origin (EMVA1288 or user-specified)
in `noise_values_are` of the return value.

## Where 3.45 µm pixels start to matter (connection to the implementation)

The resolution limit in `optical_budget` is "the larger of diffraction 1.22λN_w and sampling 2p".
With 3.45 µm pixels at 550 nm, it switches to **diffraction-limited once the working F-number N_w exceeds about 5.1**
(1.22 × 0.55 × 5.1 ≈ 3.4 µm ≈ p). In other words, with the 3.45 µm generation, stopping down beyond F5.6
does not increase resolution; only the depth of field extends. With the 2.74 µm of Pregius S, this boundary
drops to around F4. **If you change the pixel pitch, the upper limit of the aperture also changes** — that is the design consequence.
