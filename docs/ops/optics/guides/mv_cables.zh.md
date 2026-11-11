---
guide: mv_cables
dim: optics
title: 线缆(规格、速度、供电、机器人线缆)
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
lang: zh
translation_of: docs/ops/optics/guides/mv_cables.md
source_sha256: 5d7d8639d770339112419d7dcc30bbe05e1686c3aee990c7d5548b715fc0c0a0
---

<!-- fullseye guide: 机器视觉的周边知识。不是 op，而是说明传给 op 的值
     从何而来的教材。相关 op: interface_budget -->

# 线缆（规格、速度、供电、机器人线缆）

接口之间的差异见 `frame_grabbers.md`。本文讲的是**线缆本身**，
现场之所以决定采用某种构成，很多原因都在这里（距离、供电、运动部件）。篇幅不长。

## 1. 各规格的线缆

| 规格 | 线缆 / 连接器 | 实用长度（标准等级） | 供电 |
| --- | --- | --- | --- |
| **Camera Link** | MDR-26 / SDR-26（粗、重） | Base 约 10 m。**时钟越高越短** | **PoCL** 约 4 W。需要专用线缆 |
| **Camera Link HS** | CX4 / SFP+ / 光纤 | 铜缆几十 m，光纤几百 m 以上 | 无（另接电源） |
| **CoaXPress** | 75 Ω 同轴（BNC / DIN 1.0-2.3 / Micro-BNC）1 根至 4 根 | CXP-12 约 40 m，降低速度可以延长 | **PoCXP** 24 V、约 13 W。**电源、控制、数据全部走 1 根同轴线** |
| **GigE Vision** | Cat5e/6/6a（RJ45，工业用为 M12 X-coded） | **100 m**（规格上限） | **PoE** 802.3af 15.4 W / 802.3at 30 W |
| **10GigE** | Cat6a（100 m）或 SFP+ DAC / 光纤 | 同上 | 支持 PoE++ 的设备有限 |
| **USB3 Vision** | micro-B / Type-C | **3〜5 m**（无源）。要延长就用有源光缆 | 总线供电 4.5 W（5 V、900 mA） |
| **Opt-C:Link**（AVAL DATA） | 光纤（纤芯 50 / 62.5 µm，包层 125 µm） | **几百 m** | 因为是光纤，**无法供电**（相机一侧需要另接电源） |

**由距离决定构成的例子**：在设备大、电气噪声多（焊接、伺服驱动器附近）的现场，
先于带宽、由距离和抗噪声能力决定规格。Camera Link 到 10 m 级就到顶了，
GigE 是 100 m，光纤（CLHS / Opt-C:Link）是几百 m。但光纤无法供电，所以
还需要另外给相机一侧布电源线 —— “1 根线缆就能解决”的是 PoCXP 或 PoE 的情况。

## 2. 供电的思路

* **PoCXP / PoE / PoCL / USB 总线供电**都是为了“用 1 根线缆解决”的机制。
  布线减少，运动部件断线的风险也随之降低。
* 但**电力有上限**（PoCL 4 W < USB 4.5 W < PoCXP 13 W < PoE 15.4/30 W）。
  带冷却机构的相机（如 Vieworks VP 的帕尔贴冷却）或高速相机会超过上限，
  **以另接电源为前提**。
* PoE 还要考虑交换机一侧的电力预算。把 8 台相机接到 1 台交换机上，
  会同时碰到每个端口的上限和整台交换机的上限。

## 3. 机器人线缆（运动部件）

固定布线与活动布线完全是两回事，**把普通线缆用在运动部件上必然会断线**。

| 类别 | 用途 | 起作用的规格 |
| --- | --- | --- |
| **标准（固定）** | 柜内、固定安装 | 弯曲半径的规定较宽松 |
| **高柔性（拖链用）** | 直线往复（龙门、XY 平台） | **最小弯曲半径**（以外径的 7.5〜10 倍为参考）、**弯曲寿命**（以 1000 万次级规定）、护套多为 PUR |
| **机器人线缆（耐扭转）** | 多关节机器人的手臂 | 除弯曲外还能耐受**扭转**的结构。绞距与编织屏蔽的设计不同 |

* **往往是屏蔽层先坏。** 箔屏蔽在弯曲时容易撕裂，运动部件上需要编织
  屏蔽。屏蔽层劣化后，表现出来的不是断线，而是**噪声引起的传输错误**，
  症状变成“图像偶尔会乱”，原因难以查明。
* 不能遵守弯曲半径的话，寿命会按数量级下降。拖链的半径由线缆外径决定，所以
  **线缆越粗（Camera Link），在运动部件上越不利**。1 根同轴线的 CoaXPress 或
  Cat6a 的 GigE 更便于布线。
* 光纤（Opt-C:Link / CLHS）细、轻、抗噪声，但**弯曲半径要求严格**（纤芯会折断）。
  用于运动部件时需要耐弯曲规格的光纤。

## 4. 对虚拟化的启示（不多，但确实存在）

1. **帧率 / 行率的有效值**可能随线缆长度下降（CXP 会根据距离
   协商速度）。`interface_budget` 返回的是规格上的带宽，所以在长距离构成中
   要按降 1 档的值来估算。
2. **噪声引起的传输错误**在图像中表现为**随机的行缺失、比特错误**。
   在合成数据中加入这种故障模式，就能得到对现场“偶尔会坏的图像”更鲁棒的模型
   （目前 `optscene` 尚未实现）。
3. **供电的上限**决定能否冷却，能否冷却决定暗电流（`sensor_spec(dark_e_per_s=)`）。
   线缆的话题最终一直联系到传感器的噪声。
