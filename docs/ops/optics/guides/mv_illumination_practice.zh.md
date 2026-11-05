---
guide: mv_illumination_practice
dim: optics
title: 照明实务知识 —— 波长、偏振、点亮方式、外部光、安全
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
lang: zh
translation_of: docs/ops/optics/guides/mv_illumination_practice.md
source_sha256: 5ac729f887d0ec8773cdeefedabfc6f380d8050585eb560cfc9bf0b094ac8041
---

# 照明实务知识 —— 波长、偏振、点亮方式、外部光、安全

**镜头决定缺陷成像有多清晰,照明决定缺陷有没有对比度。**
没有对比度的东西,用多高级的镜头、多强的 AI 都看不见。
外观检测中最见效的技能就在这里。

几何(同轴/环形/穹顶/暗场/背光)的**数值选型**
由 `optics/guides/optics_imaging.md` 的"照明设计"一节讨论(`illumination_design` /
`defect_contrast` / `lighting_sweep` 依据第一性原理计算对比度)。
本文是写其外围 —— **设备与现场的实务** —— 的教材。

---

## 1. 几何速查(详见 `optics_imaging.md`)

| 缺陷、目的 | 有效的照明 | 原理 |
| --- | --- | --- |
| 镜面的凹凸、刻印 | **同轴** | 把镜面反射原样送回相机,只让倾斜面变暗 |
| 一般表面 | 高角度环形 | 通用。先从这里试起 |
| 粗糙缺陷(崩边、凹坑、细微划痕)、异物 | **低角度环形(暗场)** | 只拾取散射成分。平面暗,只有粗糙处发亮 |
| 有光泽的曲面、颜料的颜色 | 穹顶 | 从各个方向照射,消除镜面反射的不均 |
| 轮廓、尺寸、孔 | **背光** | 只看形状。不受表面图案干扰 |
| 有方向性的纹理 | 条形(斜射) | 用阴影强调凹凸 |

**注意**: "暗场下划痕会发亮"说的是**带有粗糙侧壁的划痕**。
仅仅是平滑倾斜的面(例: 10°)在暗场下不会发亮 —— 因为它只是把低角度的光
镜面反射到相机之外(`defect_contrast` 用数值给出这一点)。

---

## 2. 波长的选择 —— 实务中最见效的自由度

* **波长越短越有利于细微结构。** 衍射极限与 λ 成正比(Airy 半径 = 1.22 λ N)。
  同一镜头下,蓝光(450 nm)比红光(630 nm)能分辨得精细约 3 成。
  针对细微缺陷就用短波长。
* **红外能透过。** 很多树脂透过近红外,因此可以隔着袋子或树脂罩看内容物、
  看粘接层内部。硅传感器本身的灵敏度可达**约 1100 nm**
  (Si 的带隙),在此范围内用普通相机就能拍到。
* 用 **UV 激发的荧光**看"可见光下看不到的东西" —— 胶水涂布不均、油污、
  残留异物。**发光的不是反射而是被摄体本身**,所以曝光时间会长出几个数量级。
* **用颜色制造对比度。** 用目标颜色的补色光照射,该部分会变暗。
  用红色照明拍绿色异物,它会沉为黑色。比起彩色相机,**单色照明 + 黑白相机**
  往往在灵敏度和分辨率上都更好。
* ★ **窄带 LED + 带通滤光片是对付外部光的标准做法。**
  在镜头上装只透过照明波长的滤光片,荧光灯和日光几乎都能滤掉。
  在制作遮光罩之前,值得先试这个。

---

## 3. 偏振

* **用正交偏振消除反光。** 在光源侧和受光侧放入偏振片并使其正交。
  金属或透明层上的**镜面反射能很好地保持偏振**,因此会被消除。而在内部散射后
  出射的**漫反射的偏振已被解除**,因此会保留下来。
  → 用法例如消除涂装面清漆层的反光以观察底层。
* 利用**应力双折射**可以把透明体(玻璃、树脂)的内部应力可视化。
  成型品的残余应力、钢化玻璃的检测。
* 代价是**光量下降**(2 片偏振片下降到 1/4 以下)。要与 §4 的点亮方式一起考虑。

---

## 4. 点亮方式 —— 连续 / 频闪 / 过驱动

| 方式 | 光量 | 适用场合 |
| --- | --- | --- |
| **连续点亮** | 按额定值 | 静止物体、简单的配置。在热达到稳态之前亮度会变动(§6) |
| **频闪(脉冲)** | 与连续**大致相同** | 冻结运动模糊。与曝光同步短暂发光 |
| **过驱动** | **大幅增加(视条件可达额定值的 10 倍左右)** | 一次性解决光量不足、高速输送、偏振导致偏暗等问题 |

**过驱动的要点**(一手资料为照明厂商的应用笔记):

* 脉冲宽度可从数 ms 降到 **1 µs**,占空比可降到低于 1%。
* 由于发热的限制,**占空比一般以 10% 左右为上限**。
* 由于占空比低,**LED 结区的发热反而减少,有利于寿命**。
  还带来了把散热器做小甚至省去的设计余地。
* **必须与相机曝光进行触发同步**。一旦偏离,就会混入"偶尔偏暗的图像",
  而且很难意识到原因在照明(这些图像混入训练数据会降低质量)。

---

## 5. 闪烁与拍频 —— 对线扫描是致命的

* **PWM 调光的频率与行频产生拍频时,图像上会出现横纹。**
  调光调得越暗,占空比越低,横纹越明显。原则是**用恒流调光,而不是 PWM**。
* 外部光也一样。来自工频电源的 100 / 120 Hz,变频荧光灯的数十 kHz。
* 对策的顺序: ①遮光 ②用带通滤光片滤掉(§2)③把曝光时间设为闪烁周期的整数倍
  ④改用恒流调光。

---

## 6. 随时间的变化与维护

* **LED 的光通量会随时间下降。** 即使以恒流驱动,结温升高时光量也会下降。
* 所以要**在热稳态下测量**。刚通电时较亮,数十分钟后趋于稳定。
  刚启动时确定的曝光值,在稳态下会过暗。
* 以绝对亮度作为判定阈值的设备,要**定期用标准板(白色漫射板)校准**,
  或使用带光量反馈的电源。
* 制作合成数据时也一样 —— 如果实机的亮度会变动,就把这个变动幅度
  写进 `inspection_dataset(intensity_jitter=...)`。

---

## 7. 安全(IEC 62471)

把灯和灯系统分为 4 个风险组的标准。

| RG | 含义 | 参考 |
| --- | --- | --- |
| **RG0**(豁免) | 无危险。长时间注视也无害 | 连续照射 ~10,000 s 以内 |
| **RG1**(低风险) | 有限时间内无害 | ~100 s |
| **RG2**(中风险) | **由于眨眼反射等自然回避反应,通常不会造成伤害**,但即使短时间也不适 | ~0.25 s |
| **RG3**(高风险) | **即使短时间也危险**。尤其是近距离 | — |

* **RG2 / RG3 需要警示标识和使用注意事项。** 工业用强光照明属于 RG2 的情况
  很常见(例: Zivid 2+ 的投影仪属于 IEC 62471-5 的 RG2)。
* 检测设备**必然会有人凑近窥视的作业**(换型调试、清洁、故障处理)。
  设计时确认 RG,做成以窥视姿势也不会受到照射的结构。
* **UV 和蓝光尤其要注意**(蓝光视网膜损伤)。UV 荧光检测以遮光外壳为前提。

---

## 8. 外部光与杂散光的实务

* 遮光罩、缩小开口,内侧用**哑光黑**(黑色阳极氧化、植绒片)。
* **杂散光来自"你没在看的地方"**。白色地板、作业人员的白大褂、相邻设备的显示器。
  从相机位置环顾房间,找出明亮的东西。
* 遮光遮不住时就用 §2 的带通滤光片。**把照明加强,使外部光相对可以忽略**也是
  一种办法,这时过驱动(§4)就有用了。

---

## 9. fullseye 的现状(如实说明)

| 要素 | 现有的 | 缺少的 |
| --- | --- | --- |
| 几何 | `light_source` / `light_spec`(ring / dome / bar / coaxial / backlight)、`illumination_design` | — |
| 波长 | `light_spec(wavelength_nm, bandwidth_nm)`、`light_wavelengths` | 实际光谱分布、荧光(激发 → 发射的波长转换) |
| 偏振 | `light_spec(polarization=)`、`jones_*` / `mueller_*` op | 照明 → 表面 → 受光**全程考虑偏振**的渲染 |
| 点亮方式 | 无 | 频闪/过驱动、与曝光的同步偏离 |
| 闪烁 | 无 | 线扫描的拍频横纹(实机的主要故障模式) |
| 随时间的变化 | 可用 `inspection_dataset(intensity_jitter=)` 扰动 | 热引起的系统性漂移(单调而非随机) |
| 安全 | 无 | 风险组的计算 |
| 渲染 | `illumdesign` 是点光源之和 | 无多次反射、相互反射,不支持各向异性 BRDF |

---

## 10. 诊断表 —— 从症状到原因

| 症状 | 首先怀疑 | 确认方法 |
| --- | --- | --- |
| 完全看不到缺陷 | 照明的几何不合适 | 用 `illumination_design(surface, defect)` 给出候选,从排名靠前的开始在实机上试 |
| 划痕能看到,但平面也刺眼 | 镜面反射进入了相机 | 正交放入偏振片,或改变仰角(`lighting_sweep`) |
| 平滑倾斜的缺陷在暗场下不发亮 | 这是正常的。暗场对**粗糙**有效 | 查看 `defect_contrast` 的 `regime`。若为 `topographic` 则暗场不合适 |
| 图像上出现横纹(线扫描) | PWM 调光与外部光的拍频 | 改为恒流调光、遮光、把曝光设为周期的整数倍 |
| 偶尔混入偏暗的图像 | 频闪与相机曝光的同步偏离 | 用示波器看触发信号。确认改为连续点亮后是否仍能复现 |
| 早上和傍晚的判定结果不同 | 外部光混入 | 遮光后是否仍复现。放入带通滤光片进行比较 |
| 只有刚启动时合格率高 | LED 尚未达到热稳态 | 通电后 60 分钟内,每 10 分钟拍一次标准板并记录亮度 |
| 几个月内逐渐超出阈值 | LED 随时间衰减 | 查看标准板亮度的历史。把定期校准纳入运行 |
| 无法延长曝光且光量不足 | 连续点亮的上限 | 改用支持过驱动的电源(占空比 10% 以内) |
| 作业人员说刺眼 | 风险组 | 确认 RG,重新评估窥视位置的照射量 |

---

## 出处

* Advanced Illumination — *The Mechanics of Strobe Overdriving LED Lights for Machine
  Vision Applications*(连续 / 频闪 / 过驱动的区别、降低占空比、
  结区发热的降低) — <https://advancedillumination.com/the-mechanics-of-strobe-overdriving-led-lights-for-machine-vision-applications/>
* Smart Vision Lights — *OverDrive Driver*(脉冲宽度 数 ms〜1 µs、占空比低于 1%、
  占空比上限 10%、额定值 10 倍级的电流) — <https://machinevisiondirect.com/blogs/news/svl-overdrive>
* Opto Engineering — *LED pulsing and strobing* — <https://www.opto-e.com/basics/led-pulsing-and-strobing>
* Advanced Illumination — *IEC 62471 Photobiological Safety of Lamps and Lamp Systems*
  (RG0–RG3 的分类) — <https://www.advancedillumination.com/wp-content/uploads/2023/04/IEC-040119-Photobiological-Safety-of-Lamps-and-Lamp-Systems_042723.pdf>
* Luminus Devices — *Understanding IEC 62471 and IEC 62778 Eye Safety Risk Groups* —
  <https://luminusdevices.zendesk.com/hc/en-us/articles/10532958752397-Safety-Understanding-IEC-62471-and-IEC-62778-Eye-Safety-Risk-Groups-visible-and-nonvisible-light-sources>
