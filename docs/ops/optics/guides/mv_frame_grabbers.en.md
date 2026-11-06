---
guide: mv_frame_grabbers
dim: optics
title: Frame grabber boards (not optics, but they decide whether you can capture at all)
title_en: Frame grabber boards (not optics, but they decide whether you can capture at all)
title_zh: 图像采集卡(不属于光学系统,却决定能否采到图像)
title_tw: 影像擷取卡(不屬於光學系統,卻決定能否擷取到影像)
title_ko: 프레임 그래버 보드(광학계는 아니지만 촬영 가능 여부를 정한다)
title_de: Framegrabber-Karten (keine Optik, entscheiden aber, ob überhaupt aufgenommen werden kann)
title_hi: Frame grabber boards (optics नहीं, पर यही तय करते हैं कि capture हो भी सकता है या नहीं)
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, videostream
lang: en
translation_of: docs/ops/optics/guides/mv_frame_grabbers.md
source_sha256: 557994798a3a248f2fe13b8bb85a8726615d9d18e501d9db5e52ca968d06ed0f
---

<!-- fullseye guide: background knowledge around machine vision. Not an op, but teaching
     material that shows where the values passed to ops come from. Related op: interface_budget -->

# Frame grabber boards (not optics, but they decide whether you can capture at all)

Whereas optics decides "whether the image is formed with the required contrast", the frame grabber decides
**whether it can be carried without being dropped**. At high resolution, high speed and with line scan, it is common for
the bottleneck to be the **transmission bandwidth** rather than the sensor.

## Interface bandwidth (values checked against primary sources)

| Standard | Per 1 connection | Practical configuration | Notes |
| --- | --- | --- | --- |
| **CoaXPress CXP-6** | 6.25 Gbps | 1 to 8 connections | Power (PoCXP), control and data over 1 coaxial cable |
| **CoaXPress CXP-12** | **12.5 Gbps** | **4 connections = 50 Gbps = 5 GB/s** | Bandwidth that can run an 8 bit, 16k line sensor at **300 kHz** |
| **Camera Link Base** | 2.04 Gbps | 24 bit × 85 MHz, 1 connector | Old but still in service. The cable is thick and short (up to 10 m) |
| **Camera Link Medium** | 4.08 Gbps | 48 bit, 2 connectors | |
| **Camera Link Full** | 5.44 Gbps | 64 bit | |
| **Camera Link Deca** | 6.80 Gbps | 80 bit | The upper limit of Camera Link |
| Camera Link HS | 3.125 Gbps/lane | Multiple lanes | Long distance (optical fibre possible) |
| **Opt-C:Link** (proprietary to AVAL DATA) | **6.25 Gbps/ch**, **12.5 Gbps** with 2 ch bundled | Optical fibre (core 50 / 62.5 µm, cladding 125 µm) | **Extendable to several hundred m, robust against noise**. With 5 packet types (image, serial, trigger, link and user), even control is carried over light. Camera Link cameras connect through a conversion unit (AOC-162 etc.) |
| GigE Vision | 1 / 5 / 10 / 25 GigE | — | Cables are cheap and long. CPU load is relatively high |

The design is such that **16k × 300 kHz × 8 bit ≈ 4.9 GB/s** fits exactly into the 5 GB/s of CXP-12 ×4.
The Vieworks VT series (TDI, up to 300 kHz) is a product that presupposes this bandwidth.

## Main makers and current boards

| Maker | Product | Specifications checked |
| --- | --- | --- |
| **Euresys** | Coaxlink Quad CXP-12 | PCIe 3.0 x8, camera bandwidth 5000 MB/s, CXP-12 ×4 |
| Euresys | Coaxlink Quad CXP-12 JPEG | 4 independent channels + **baseline JPEG encoder 250 Mpixel/s** (compression on the board) |
| Euresys | Coaxlink QSFP+ / Duo / Mono LH | Configurable for 1 to 8 cameras, across the range CXP-6 to CXP-12 |
| **Matrox** | Rapixo CXP (RAP8G4C12P602) | CoaXPress 2.0, CXP-12 ×4, PCIe 3.1 x8, **12.5 GB/s camera bandwidth**, PoCXP |
| **Teledyne DALSA** | Xtium2-CXP PX8 Quad | CXP-12 ×4, camera bandwidth 5000 MB/s, PCIe Gen3 x8 (bus up to 7000 MB/s) |
| BitFlow | Claxon / Cyton | CXP / Camera Link |
| Active Silicon | FireBird | CXP / Camera Link |
| Kaya Instruments | Komodo | CXP |
| **AVAL DATA** | APX-3312A / APX-3313A (Camera Link), Opt-C:Link family | Has both Camera Link boards and a proprietary optical I/F. Strong for equipment in the Japanese domestic market |
| Euresys | Grablink (Camera Link) | Continues Camera Link as a line separate from the CXP-based Coaxlink |

## Why it cannot be ignored in virtualization

0. **If long distance is needed, the options narrow**. Camera Link tops out at around 10 m,
   but Opt-C:Link (optical) reaches several hundred m. On sites where the equipment is large or electrical noise is high (welding,
   near motor drives), the standard is decided by **distance and noise immunity** before bandwidth.
1. **In area scan the sensor is usually the bottleneck**. The IMX541 (20.3 MP, 8 bit) is 20.3 MB per 1 frame, so
   at 5 GB/s it could theoretically reach 246 fps, but the sensor itself runs at 18 to 42 fps. → Bandwidth is left over.
2. **In line scan / TDI the bandwidth becomes the bottleneck**. 16k × 300 kHz uses up 4.9 GB/s.
   If you want a higher line rate, it first becomes a question of the board and the number of cables.
3. **Encoder synchronization** (line scan only). Synchronizing the transport speed with the line rate is
   the grabber's job, and if this slips, **the aspect ratio of the image breaks**. This failure mode does not exist
   in area scan, and no amount of tuning the optics fixes it.
4. **Pre-processing on the board**. Doing shading correction, bit packing and JPEG compression on the board
   lowers the host load. When deploying a model trained on synthetic data,
   **this correction sits in front of inference**, so you need to decide beforehand whether to pass the training data through the same correction
   or to train on the raw data before correction.
5. **Trigger jitter**. When synchronizing with pulsed lighting or a strobe, jitter becomes exposure variation =
   brightness variation. This is where the domain-randomization `intensity_jitter` properly finds its grounds.

## Connection to the implementation

`optscene.interface_budget()` returns the **bandwidth-limited maximum frame rate / line rate**
from the sensor's pixel count, bit depth and interface. It is an op for finding out first "which one is the bottleneck"
by checking it against the sensor-side upper limit.
