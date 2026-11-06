---
guide: mv_cables
dim: optics
title: Cables (standards, speed, power delivery, robot cables)
title_en: Cables (standards, speed, power delivery, robot cables)
title_zh: 线缆(规格、速度、供电、机器人线缆)
title_tw: 線纜(規格、速度、供電、機器人線纜)
title_ko: 케이블(규격·속도·급전·로봇 케이블)
title_de: Kabel (Standards, Geschwindigkeit, Stromversorgung, Roboterkabel)
title_hi: Cables (standards, speed, power delivery, robot cables)
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, videostream
lang: en
translation_of: docs/ops/optics/guides/mv_cables.md
source_sha256: 5d7d8639d770339112419d7dcc30bbe05e1686c3aee990c7d5548b715fc0c0a0
---

<!-- fullseye guide: background knowledge around machine vision. Not an op; teaching material
     showing where the values passed to ops come from. Related op: interface_budget -->

# Cables (standards, speed, power delivery, robot cables)

The differences between interfaces are in `frame_grabbers.md`. This one is about **the cables themselves**, and
many of the reasons a configuration is decided on site lie here (distance, power delivery, moving parts). It is short.

## 1. Cables by standard

| Standard | Cable / connector | Practical length (standard grade) | Power delivery |
| --- | --- | --- | --- |
| **Camera Link** | MDR-26 / SDR-26 (thick, heavy) | Around 10 m for Base. **The higher the clock, the shorter it gets** | **PoCL** about 4 W. Needs dedicated cables |
| **Camera Link HS** | CX4 / SFP+ / optical fibre | Tens of m in copper, hundreds of m and more in fibre | None (separate power supply) |
| **CoaXPress** | 75 Ω coax (BNC / DIN 1.0-2.3 / Micro-BNC), 1 to 4 cables | Around 40 m at CXP-12; longer if the speed is lowered | **PoCXP** 24 V, about 13 W. **Power, control and data all ride on 1 coax cable** |
| **GigE Vision** | Cat5e/6/6a (RJ45; M12 X-coded for industrial use) | **100 m** (upper limit of the standard) | **PoE** 802.3af 15.4 W / 802.3at 30 W |
| **10GigE** | Cat6a (100 m) or SFP+ DAC / fibre | Same as above | Few devices support PoE++ |
| **USB3 Vision** | micro-B / Type-C | **3–5 m** (passive). To extend, use active optical cables | Bus power 4.5 W (5 V, 900 mA) |
| **Opt-C:Link** (AVAL DATA) | Optical fibre (core 50 / 62.5 µm, cladding 125 µm) | **Hundreds of m** | Being optical, it **cannot deliver power** (the camera side needs a separate supply) |

**Examples where distance decides the configuration**: on sites where the equipment is large or there is much electrical noise (welding, near servo drives),
the standard is decided by distance and noise immunity before bandwidth. Camera Link tops out at the 10 m class,
GigE at 100 m, and fibre (CLHS / Opt-C:Link) at hundreds of m. But fibre cannot deliver power, so
power wiring to the camera side is needed separately — "getting by with 1 cable" is possible with PoCXP or PoE.

## 2. How to think about power delivery

* **PoCXP / PoE / PoCL / USB bus power** are all mechanisms for "getting by with 1 cable".
  With less wiring, the risk of breakage in moving parts also goes down.
* However, **power has an upper limit** (PoCL 4 W < USB 4.5 W < PoCXP 13 W < PoE 15.4/30 W).
  Cameras with cooling (such as the Peltier cooling of the Vieworks VP) and high-speed models exceed the limit, so
  **a separate power supply is assumed**.
* With PoE, the power budget on the switch side matters too. Putting 8 cameras on 1 switch,
  you hit both the per-port limit and the limit of the whole switch.

## 3. Robot cables (moving parts)

Fixed wiring and moving wiring are completely different things, and **an ordinary cable used in a moving part will break, without fail**.

| Type | Use | Specifications that matter |
| --- | --- | --- |
| **Standard (fixed)** | Inside cabinets, stationary | Loose bend-radius specification |
| **High-flex (for cable carriers)** | Linear reciprocation (gantries, XY stages) | **Minimum bend radius** (7.5–10 times the outer diameter as a guide), **flex life** (specified at the 10-million-cycle class), jacket often PUR |
| **Robot cable (torsion-resistant)** | Arms of articulated robots | A structure that withstands **torsion** in addition to flexing. Lay pitch and braided-shield design differ |

* **The shield often fails first.** Foil shields tear easily when flexed; moving parts need braided
  shields. When the shield degrades, it shows up not as a break but as **transmission errors due to noise**,
  so the symptom becomes "the image is occasionally corrupted" and the cause is hard to find.
* If the bend radius cannot be respected, life drops by orders of magnitude. The radius of a cable carrier is decided from the cable's outer diameter, so
  **the thicker the cable (Camera Link), the worse it is for moving parts**. CoaXPress on 1 coax cable or
  GigE on Cat6a is easier to route.
* Fibre (Opt-C:Link / CLHS) is thin, light and noise-immune, but **its bend radius is strict** (the core breaks).
  For moving parts, flex-resistant fibre is needed.

## 4. Implications for virtualisation (few, but definitely there)

1. **The effective frame rate / line rate** can drop with cable length (CXP negotiates
   speed by distance). `interface_budget` returns the bandwidth according to the standard, so for long-distance configurations
   estimate with a value 1 step lower.
2. **Transmission errors due to noise** appear in images as **random missing lines and bit corruption**.
   Including this failure mode in synthetic data gives a model that is robust to "images that occasionally break" on site
   (currently not implemented in `optscene`).
3. **The power-delivery limit** decides whether cooling is possible, and whether cooling is possible decides the dark current (`sensor_spec(dark_e_per_s=)`).
   The story of cables ultimately connects all the way to sensor noise.
