---
guide: mv_image_sensors
dim: optics
title: 工业图像传感器(以现行产品为主)
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
lang: zh
translation_of: docs/ops/optics/guides/mv_image_sensors.md
source_sha256: 75db2f3b412e4f7fd88d330e7d0c4b568cb0d7df4503c476ccb7a4ed3bc87c69
---

<!-- fullseye guide: 机器视觉的周边知识。不是 op,而是说明传给 op 的值
     从何而来的教材。相关 op: sensor_spec / sensor_catalog / optical_budget -->

# 工业图像传感器(以现行产品为主)

只要不使用像素位移或 TDI,相机的**规格几乎完全由图像传感器决定**。
接口(USB3 Vision / GigE Vision / CoaXPress / 10GigE)改变的
主要是帧率和 ROI 的约束,而不是画质本身。因此在虚拟化中
应当给出的参数不是相机型号,而是**传感器的规格**。

出处: Basler"CMOS sensor selection"(代际、像素、分辨率、快门、帧率)。
饱和容量、读出噪声、QE 的实际数值只存在于 Basler 等的 **EMVA1288 报告**或 Sony 的
数据手册中,一般公开页面上没有(下表中明确标注"非公开")。

## 厂商

制造图像传感器的厂商并不多。在工业用途中真正可选的有:

| 厂商 | 工业产品线 | 定位 |
| --- | --- | --- |
| Sony Semiconductor | Pregius / Pregius S / STARVIS 2 | 事实上的标准。全局快门的主流 |
| onsemi | XGS / PYTHON | 大幅面、高速。XGS 为 3.2 µm 代 |
| Gpixel | GMAX / GSPRINT / GSENSE | 高分辨率、高速。中画幅及以上实力强 |
| Teledyne e2v | Emerald / Sapphire | 低噪声、高灵敏度。也偏向航天/科研 |
| OmniVision | OG / OS 系列 | 偏向车载、嵌入式 |

## 工业传感器 38 款 —— 附 EMVA1288 实测值(5 家厂商并列)

出处是 Basler 的相机实测表,因此**这里列出的是相机一侧的值**。

* **分辨率**是该相机输出的像素数。厂商有时会裁掉边缘,使其**略低于
  传感器的全部有效像素**,因此可能与传感器单体的规格不一致。
* **帧率**随接口(USB3 Vision / GigE / 5GigE / CXP-12)
  而变。它不是传感器的属性,因此不列入本表。
* **QE / 暗噪声 / 饱和容量 / 动态范围**是 EMVA1288 实测值(ace /
  ace 2 / boost),是包含实现在内的值。换一台相机会略有不同。
* **像素间距、快门方式、代际**来自传感器,因此换相机也不会变。

### Sony

| 型号 | 系列 | 分辨率 | 像素 [µm] | 快门 | QE | 噪声 [e-] | 饱和 [ke-] | DR [dB] | 状态 |
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

| 型号 | 系列 | 分辨率 | 像素 [µm] | 快门 | QE | 噪声 [e-] | 饱和 [ke-] | DR [dB] | 状态 |
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

| 型号 | 系列 | 分辨率 | 像素 [µm] | 快门 | QE | 噪声 [e-] | 饱和 [ke-] | DR [dB] | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GMAX3265 | Gpixel GMAX | 65.4 MP / 9344×7000 | 3.20 | global | 52% | 8 | 10.4 | 61 | current |
| GMAX0505 | Gpixel GMAX | 26.2 MP / 5120×5120 | 2.50 | global | 51% | 4 | 4.3 | 60 | current |
| GMAX2518 | Gpixel GMAX | 18.5 MP / 4508×4096 | 2.50 | global | 56% | 3 | 6.7 | 66 | current |
| GMAX2509 | Gpixel GMAX | 9.1 MP / 4200×2160 | 2.50 | global | 53% | 1 | 4.6 | 69 | current |
| GMAX2505 | Gpixel GMAX | 5.6 MP / 2600×2160 | 2.50 | global | 53% | 1 | 4.8 | 70 | current |

### ams

| 型号 | 系列 | 分辨率 | 像素 [µm] | 快门 | QE | 噪声 [e-] | 饱和 [ke-] | DR [dB] | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CMV12000 | ams CMV | 12.6 MP / 4096×3072 | 5.50 | global | 45% | 14 | 11.6 | 59 | mature |
| CMV4000 | ams CMV | 4.2 MP / 2048×2048 | 5.50 | global | 62% | 14 | 11.9 | 59 | mature |
| CMV2000 | ams CMV | 2.2 MP / 2048×1088 | 5.50 | global | 63% | 14 | 9.3 | 57 | mature |

### Teledyne

| 型号 | 系列 | 分辨率 | 像素 [µm] | 快门 | QE | 噪声 [e-] | 饱和 [ke-] | DR [dB] | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EV76C570 | Teledyne e2v | 1.9 MP / 1602×1202 | 4.50 | switchable | 47% | 22 | 6.8 | 50 | legacy |
| EV76C661 | Teledyne e2v NIR | 1.3 MP / 1280×1024 | 5.30 | switchable | 59% | 23 | 7.4 | 50 | legacy |

### 各厂商的定位(用同一测量方法比较的结果)

* **Sony Pregius / Pregius S** —— 均衡的基准。QE 62-70%,噪声 2-3 e-,饱和 9.6-10.5 ke-。
  只有第 1 代(5.86 µm)饱和达 31.8 ke-,自成一格,若重视动态范围至今仍是候选。
* **onsemi XGS**(3.2 µm)—— 本领在 **APS-C / 35 mm 的大幅面**。最高到 44.7 MP(8192×5460),
  这种画幅 Sony 没有。QE 55-57%,噪声 4-5 e-。
* **onsemi PYTHON**(4.8 µm)—— 小型、高速。但**噪声 11-12 e- 是 Pregius 的 5 倍**,
  在暗场景、暗场下会产生影响。DR 也偏低,为 56-57 dB。
* **Gpixel GMAX**(2.5 µm)—— 卖点是 **1 e- 级的噪声**(GMAX2505 / 2509)。饱和较小,为 4-5 ke-,
  所以 DR 为 69-70 dB,与 Sony 大致相当。**65 MP(9344×7000)的
  GMAX3265** 是超高分辨率唯一的选择。
* **ams CMV**(5.5 µm,原 CMOSIS)—— 饱和 9-12 ke-,但**噪声 14 e-**。DR 57-59 dB。
* **Teledyne e2v EV76**(可切换快门)—— 噪声 22-23 e-,DR 50 dB。有 NIR 增强版。

**对选型的含义**: "像素小 = 不利"并不成立。GMAX2505(2.5 µm、噪声 1 e-)的
DR 为 70 dB,与 Pregius S(2.74 µm、噪声 2 e-、71 dB)相当。起作用的**不是像素尺寸本身,
而是饱和容量与噪声之比**,在暗场这类信号很小的用途中,噪声起支配作用。

## 自研传感器的相机厂商(无法从型号查到)

上面的表讲的是"采购传感器制造相机"的厂商(Basler / FLIR / IDS / Baumer /
Allied Vision / JAI …)。**自行设计、制造传感器的相机厂商**
结构不同,无法从传感器型号查到规格。**相机的数据手册是唯一的
来源**,因此需要逐 1 家单独查证。

| 厂商 | 传感器 | 获取方式 |
| --- | --- | --- |
| **Canon** | 自 2000 年起制造自有 CMOS。**仅供自家产品**,不对外销售 | 工业/医疗/科研相机的数据手册。像素级的独有结构是性能的依据 |
| **Teledyne DALSA / e2v** | 传感器和相机都是自家的(Teledyne Vision Solutions)。Emerald / Sapphire / Xineos、线扫描的 TDI | 传感器也单独销售,两种数据手册都能查到(例外地省事) |
| **Photron** | FASTCAM SA-Z 等采用自有 CMOS。Mini 4K 采用自有的 4096×2304 | 高速相机的数据手册。帧率与像素数的权衡是主要规格 |
| **Vision Research(Phantom)** | 自行设计的定制 CMOS。v1211/v1611/v2011/v2511 系列为 **28 µm 像素**(灵敏度优先)。TMX 系列为背照式定制传感器 | 相机的数据手册。像素大了一个数量级,饱和容量和灵敏度的前提与上表完全不同 |
| **Hamamatsu** | ORCA 系列。**自研与外购混用**(ORCA-Quest 搭载 Fairchild Imaging 开发的传感器)| 需要逐个机型确认。qCMOS 等光子数分辨的系列另当别论 |
| **Sony** | 传感器和相机都做(XCG 等)| 能查到传感器一侧的资料,可与上表同样处理 |

**对虚拟化的含义**: 28 µm 像素(Phantom)与 2.74 µm 像素(Pregius S)相比,饱和容量
以及进入衍射限制的 F 值都相差一个数量级。`optical_budget` 中"衍射 1.22λN_w 对 采样 2p"的
分界由像素间距决定,所以**若假定的是自研传感器的机型,不按实机的值给出像素间距,
结论就会反过来**。

## Sony STARVIS 2(卷帘/部分全局,低照度)

IMX675 / IMX678 等。卖点是低照度下的动态范围。外观检测中
很多场合需要全局快门,所以它不是主角,但在暗场和低照度用途中是候选。

## 未公开的值(需要 datasheet / EMVA1288)

以下各项对虚拟化是**必需**的,但上表的出处中没有:

* 饱和容量(full well capacity)[e⁻]
* 时间暗噪声 / 读出噪声 [e⁻]
* 量子效率 QE(λ) [%]（光谱灵敏度曲线）
* 暗电流 [e⁻/s] 及其温度依赖性
* 转换增益 [e⁻/DN]、ADC 位深
* PRNU / DSNU(像素间差异)

上表中的 QE / 暗噪声 / 饱和容量 / DR 已用 Basler 的 EMVA1288 实测值填入。
尚未获取的是**暗电流的温度依赖性、转换增益、PRNU / DSNU、光谱灵敏度曲线 QE(λ)**,
这些需要 Sony 的数据手册(相当于 NDA)或各公司的 EMVA1288 详细报告。
`optscene.sensor_spec(model=...)` 使用已填入的值,并在返回值的
`noise_values_are` 中保留其来源(EMVA1288 还是用户指定)。

## 3.45 µm 像素开始起作用的场合(与实现的衔接)

`optical_budget` 的分辨极限是"衍射 1.22λN_w 与 采样 2p 中较大的一方"。
像素 3.45 µm、550 nm 时,工作 F 值 N_w **超过约 5.1 时就变为衍射限制**
(1.22 × 0.55 × 5.1 ≈ 3.4 µm ≈ p)。也就是说,在 3.45 µm 代际,光圈收得比 F5.6 更小
分辨率也不会提高,只有景深变大。Pregius S 的 2.74 µm 下,这一分界
降到 F4 附近。**改变像素间距,光圈的上限也会改变**,这是设计上的结论。
