---
guide: mv_cameras
dim: optics
title: Industrial camera makers (sensor mapping, line scan / TDI)
title_en: Industrial camera makers (sensor mapping, line scan / TDI)
title_zh: 工业相机厂商(与传感器的对应、线扫描 / TDI)
title_tw: 工業相機廠商(與感測器的對應、線掃描 / TDI)
title_ko: 산업용 카메라 제조사(센서와의 대응·라인 스캔 / TDI)
title_de: Hersteller von Industriekameras (Sensorzuordnung, Zeilenkamera / TDI)
title_hi: Industrial camera निर्माता (sensor mapping, line scan / TDI)
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, optics/scene, optics/imaging
lang: en
translation_of: docs/ops/optics/guides/mv_cameras.md
source_sha256: 605125b29a4c6cd9d419ec3eefe6f94d51ea87ffa13f54c28b8ec65efa354d59
---

<!-- fullseye guide: background knowledge around machine vision. Not an op, but teaching
     material that shows where the values passed to ops come from. Related ops: linescan_capture / sensor_spec -->

# Industrial camera makers (sensor mapping, line scan / TDI)

The sensor-side catalogue is `image_sensors.md`. This page covers the **camera side**, and in particular
the areas that "cannot be looked up from a sensor part number" and the areas that "are not area scan".

## 1. Makers that buy sensors and build cameras

Basler / FLIR (Teledyne) / IDS / Baumer / Allied Vision / JAI / XIMEA / SVS-Vistek /
Matrix Vision / The Imaging Source, among others. The sensors they use (IMX / XGS / GMAX …) are published,
so the specifications can be looked up in the tables of `image_sensors.md`. **What the camera changes is how the resolution is cropped
(the edges are sometimes dropped) and the frame-rate and ROI constraints that come from the interface**;
the image quality itself is decided by the sensor.

## 2. Makers that build their own sensors (cannot be looked up by part number)

Canon (for its own products only) / Teledyne DALSA / e2v (also sells sensors externally) / Photron (high-speed cameras) /
Vision Research = Phantom (custom sensors with 28 µm pixels; TMX is back-side illuminated) / Hamamatsu (a mix of in-house and
external sensors; ORCA-Quest was developed by Fairchild Imaging) / Sony (both).
→ For details, see the corresponding section of `image_sensors.md`.

## 3. Makers strong in large-format, ultra-high-resolution and TDI cameras

### Vieworks (Korea)

A wide range of area scan (VC / VN / VP / VNP / VQ / VZ / VX) and line scan / TDI (VT / VL) cameras.
From the point of view of virtualization, the following 3 points matter:

| Series | Characteristics (published specifications) | Implication for the optical model |
| --- | --- | --- |
| **VP** | 25 MP to **288 MP**, 4.2 to 31 fps. **The sensor is cooled up to 20 °C below ambient temperature** | Dark current stays low even in long exposures → helps in dark field and with weak signals. `sensor_spec(dark_e_per_s=)` can be set to a value that assumes cooling |
| **VN** | Ultra-high resolution for stationary objects. The VN-200MX extends 50 MP to **427 MP by pixel shift**, 30 fps over CoaXPress | Pixel shift is an example where the equation "sensor = camera" breaks. The effective pixel pitch is mechanically subdivided |
| **VT** | **TDI** (time delay integration). 256 stages give **256× sensitivity**, line rate up to 300 kHz. For FPD / semiconductor inspection | Cannot be represented by an area-sensor model (see below) |

### Takenaka System (Japan, founded 1975)

**A pioneer of line scan cameras**. It was 1 of the earliest companies to automate manual visual inspection with line scan;
its cameras are used for pinhole inspection, defect detection and sheet-width measurement. In recent years adoption has centred on semiconductor manufacturing equipment and
LCD panel inspection. Its cameras have also been adopted on the International Space Station module "Kibo".
Products are the `TL-` series (e.g. TL-16KNCL / TL-8K35ACL / TL-4096UCL) and the `TLC-` series (colour).

> Note: as of 2026-09-05, `takex-system.co.jp` could not be resolved by DNS from this environment,
> so the pixel counts and line rates of individual part numbers have not been obtained. That the part-number naming (16K / 8K / 4096)
> indicates the **number of pixels in 1 line** is an industry convention, but the actual figures must be checked against the datasheet.

## 4. Line scan / TDI needs a different model (a current gap)

The camera in `optscene` is an area sensor (2-D grid) only, and cannot represent line scan or TDI.
Since this is where both companies' main products are, it is a large omission for virtualization. Required parameters:

| Parameter | Meaning | Difference from area scan |
| --- | --- | --- |
| Pixels in 1 line | 4096 / 8192 / 16384 … | A "sensor" of height 1 |
| Line rate [kHz] | Number of lines in 1 s | Corresponds to the frame rate |
| Transport speed [mm/s] | Speed of the conveyor or stage | **Together with this, it determines the resolution in the scan direction** |
| Physical pixel size in the scan direction | speed ÷ line rate | If the speed drifts, **the aspect ratio breaks** (a failure mode that area scan does not have) |
| TDI stages | 32 / 64 / 128 / 256 | Sensitivity is multiplied by the number of stages. But **if synchronization slips, the image blurs by that many stages** |
| Illumination | **Line illumination** is mandatory | Ring / dome lights cannot be used (only 1 line is needed) |

If implemented: make the sensor a camera of height 1, give the layout a transport speed and a line rate,
and capture and stack 1 line at a time. For TDI, accumulating M lines and giving the synchronization error as a shift amount would
reproduce even the main failure mode of real hardware, "blurring when synchronization slips".
