---
guide: colorimetry
dim: 2d
title: 测色与光谱知识 —— 颜色只由“光谱 × 光源 × 观察者”决定
title_en: Colorimetry and spectra — colour is fixed only by spectrum × illuminant × observer
title_zh: 测色与光谱知识 —— 颜色只由“光谱 × 光源 × 观察者”决定
title_tw: 測色與光譜知識 —— 顏色只由「光譜 × 光源 × 觀察者」決定
title_ko: 측색과 분광 지식 — 색은 ‘분광 × 광원 × 관찰자’로만 정해진다
title_de: Farbmetrik und Spektren — Farbe ist nur durch Spektrum × Lichtart × Beobachter bestimmt
title_hi: Colorimetry और spectra — रंग केवल spectrum × illuminant × observer से तय होता है
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: 2d/color, imgmetrics/colordiff, imgmetrics/colorspace, colortransport, optics/appearance
lang: zh
translation_of: docs/ops/2d/guides/colorimetry.md
source_sha256: 5202d311d820078eb5c5f7416221be27b3c68b82e6022428f4be74614d072351
---

# 测色与光谱知识 —— 颜色只由“光谱 × 光源 × 观察者”决定

fullseye 本身具备测色功能（`imgmetrics` 族的 `rgb_to_lab` / `delta_e_2000` 等）。
而 2-D 的颜色 op（`trans_from_rgb` / `trans_to_rgb` / `cfa_to_rgb` / `linear_trans_color`
等）是**色彩空间的变换**，并不是测色。
外观检测中判定“颜色不同”时，只看 RGB 的差值，必然会在某处判错。
本文不是 op 的说明，而是讲述**位于 op 之前的物理与规约**的教材。
与 `optics/guides/mv_*.md`（成像系统）、`3d/guides/depth_sensors.md`（深度）、
`annotate/guides/dataset_conventions.md`（输出端）处于同样的位置。

---

## 1. 颜色的定义式（一切都由此导出）

物体色**不是仅由物体决定的**。三刺激值是 3 个因子乘积的积分：

```
X = k ∫ S(λ) · R(λ) · x̄(λ) dλ
Y = k ∫ S(λ) · R(λ) · ȳ(λ) dλ
Z = k ∫ S(λ) · R(λ) · z̄(λ) dλ

S(λ) = 光源的光谱分布   R(λ) = 物体的光谱反射率   x̄ȳz̄ = 配色函数（观察者）
k 的归一化使完全漫反射面的 Y = 100
```

**此式中没有的东西无法决定颜色。** 也就是说：

* **光源变了，颜色就变**（即使是同一物体）。
* **观察者变了，颜色就变** —— CIE 1931 **2° 标准观察者**与 CIE 1964 **10° 标准观察者**是
  不同的东西。检测的视场较宽，因此有使用 10° 的场合。**没有注明用哪一个测得的
  Lab 值无法比较。**
* **相机的 RGB 不是此式的输出**（§4）。

---

## 2. 标准光源 —— 名称与实体并不一致

| 符号 | 实体 | 相关色温 |
| --- | --- | --- |
| **D65** | 平均日光（D 系列于 1964 年根据实测统计定义） | **约 6504 K** |
| D50 | 印刷、图形艺术的基准 | 约 5003 K |
| A | 钨丝灯（黑体） | 2856 K |
| F1–F12 | 荧光灯（12 种） | 因种类而异 |

**D65 的相关色温不正好是 6500 K**，是因为在标准制定之后，普朗克定律中常数
c₂ 的估计值被修订了。名称仍保留为 6500。

而重要的是 —— **D 系列和 F 系列实际上都几乎无法用人工方式再现**
（它们是数学定义的分布，而不是实际存在的光源）。此外：

> **LED 既不属于 D 系列，也不属于 F 系列。**

外观检测的照明如今几乎都是 LED。也就是说，**查标准光源的表也得不到现场的 S(λ)**。
用分光辐射计实测，或使用厂商的光谱数据，是唯一可靠的途径。

---

## 3. 同色异谱 —— 检测中最常踩到的地雷

存在这样的组合：**光谱反射率 R(λ) 不同，但在某一光源下三刺激值一致**。
这称为同色异谱对。

只要是先积分再比较，这就无法避免。在降为 3 个数字（XYZ）的那一刻，
无限维的 R(λ) 的信息就被丢弃了。其结果是：

* **白天和夜间判定结果不同**（发生在混入外界光的检测间）
* **目视 OK 而相机 NG**（人的配色函数与相机的灵敏度不同，§4）
* **把照明换成另一批次的 LED 后合格率变了**（S(λ) 有细微差异）

**想要区分，只能用光谱测量。** RGB 和 XYZ 都不够。
反过来说，当有人说“用色差来管理”时，如果**用哪个光源、哪个观察者**没有
确定，这种管理就无法再现。

---

## 4. 相机不是观察者

相机的光谱灵敏度是配色函数的线性组合（**Luther–Ives 条件**），
在实际设备上基本不存在。因此：

* **RGB → XYZ / Lab 的 3×3 矩阵，是仅在该光源、该被摄物群下成立的近似。**
  换到别的光源、别的材质群，就会出现系统误差（相机同色异谱）。
* 所以要**用色卡标定**。在相同照明、相同曝光下拍摄 X-Rite ColorChecker（24 色块）等，
  以色块的已知 Lab 为目标，用线性（或多项式）回归估计
  变换。**用未标定的 RGB 算出 ΔE，也只是个数字而已。**

### 预处理的顺序（打乱就会破坏颜色）

1. **暗电流、偏置扣除**
2. **阴影（平场）校正** —— 去除照明不均和镜头的 cos⁴
3. **白平衡** —— von Kries 型的对角缩放，更准确的是 Bradford CAT
4. **在线性空间中运算** —— 这是要点。不去除 sRGB 的伽马就做平均、缩放、插值，
   结果会**变暗变浊**（在非线性空间中求平均没有物理意义）
5. 只在显示时恢复伽马

**饱和的像素作为颜色是无效的。** 哪怕只有 1 个通道被截断，色相也会偏转。
检测时要另外保留饱和掩膜，把它们从色差计算中排除。

---

## 5. 色差 ΔE —— 用哪一个

| 公式 | 年份 | 性质 |
| --- | --- | --- |
| **ΔE\*ab（CIE76）** | 1976 | Lab 的欧氏距离。实现简单，但**在感知上不均匀**（尤其在高彩度处偏差大） |
| **ΔE94（CIE94）** | 1994 | 对明度、彩度、色相加入权重。相对 CIE76 的改善很大 |
| **ΔE00（CIEDE2000）** | 2001 | 进一步加入旋转项和灰色校正。最为精细，但**公式复杂** |

作为研究上的结论，有报告指出 **CIE76 → CIE94 的改善，比 CIE94 → CIEDE2000 的改善
更大**。CIEDE2000 各校正项的贡献，若以彩度差校正为 100，
则依次为色相差 29、旋转项 8、明度差 8、灰色校正 6，**彩度差校正占主导**。

`kL`（明度的权重）**要按用途改变** —— 惯例是图形艺术取 1、纺织取 2。
它是根据检测对象来确定的值，而不是可以直接沿用默认值的东西。

**“ΔE = 1 是辨别极限”应当作为一种俗说**来对待。实际的辨别阈值随色相、彩度、明度、
背景、观察条件而变化。**要针对自己的对象、在自己的观察条件下，实测阈值后再确定。**

---

## 6. fullseye 的现状（如实说明）

| 要素 | 现有的 | 欠缺的 |
| --- | --- | --- |
| 光源 S(λ) | `light_spec(source=led/halogen/laser, wavelength_nm, bandwidth_nm)` —— **中心波长 + 带宽**的模型（附实际照明产品目录） | 无法保存实测的光谱分布。也没有 D65/A/F 系列的表 |
| 反射率 R(λ) | `scene_material(albedo=...)` —— 标量或 RGB | **无法保存光谱反射率**。因此从原理上无法再现同色异谱 |
| 观察者 x̄ȳz̄ | 无 | CIE 1931 2° / 1964 10° 的配色函数表 |
| 相机灵敏度 | `sensor_spec(qe=...)` —— **标量的 QE** | QE(λ) 曲线、彩色滤光片的光谱透过率 |
| 色彩空间变换 | `imgmetrics` 的 `rgb_to_xyz` / `xyz_to_lab` / `rgb_to_lab` / `lab_to_rgb` —— 按 CIE 定义，**白点可用 `white=` 选择**（默认 D65 2°） | 白点的**适应**（Bradford CAT）。逆变换会截断色域外的值，因此往返只在色域内一致 |
| 色差 | **`delta_e_76` / `delta_e_2000` / `delta_e_map`** —— CIEDE2000 以 Sharma 等人的 **34 组验证对**固定（可传入 `kL` / `kC` / `kH`） | ΔE94。基于光谱的色差 |

指标本身的用法（`data_range` 的陷阱、SSIM 的实现差异、在报告中附上条件的格式）
另见 `imgmetrics/guides/image_difference_metrics.md`。

### ★ 同一个变换有 3 个 —— 名称相同，尺度却不同

fullseye 中 RGB → L\*a\*b\* 有 **3 个**：

| 在哪里 | 实现 | 尺度、精度 |
| --- | --- | --- |
| `imgmetrics.rgb_to_lab` | CIE 定义（sRGB 原色，可选白点） | float，**L\* 为 0–100**。**这个是正确的** |
| `color_pca.trans_from_rgb(img, "lab")` | **委托**给上面那个 | 相同的值 |
| op 登记表中的 `trans_from_rgb`（`backends_color`） | OpenCV | **先量化为 uint8** 再变换、然后除以 255 的 8-bit 尺度 |

在写本文的过程中发现的不一致，正是这一点 ——
`color_pca.trans_from_rgb()` 只接受 `hsv` / `yuv` / `gray`，传入 `"lab"` 或
`"xyz"` 就会抛出 `ValueError`。**正确的实现早已存在于 `imgmetrics` 中，
但从色彩空间变换的入口却没有通往那里的路径。**

修正方式不是“再写一套实现”，而是**委托**。若持有两套矩阵和传递函数，
只修了其中一套时，就会**不抛出异常而输出不同的颜色**（`imgmetrics` 自身出于同样的理由，
也把 sRGB 的传递函数委托给了 `gfx2d`）。

验证（`tests/test_colorimetry.py`）：白 → `(100, 0, 0)`（残差 2e-5 —— 因为公布的
sRGB 矩阵被舍入到了 7 位），sRGB 原色 → `(53.241, 80.092, 67.203)` 等
与公布值一致，**中灰 0.5 → L\* = 53.389**（不是 50），并且
`color_pca` 与 `imgmetrics` 返回**相同的值**。

---

## 7. 小结（判断的核心）

* **要用数字管理颜色，先固定光源、观察者和白点。** 这些没有确定的
  ΔE 无法再现。
* **RGB 的差不是色差。** 用色卡标定之后才成为色差。
* **不要试图用 3 个数字区分光谱不同的东西。** 这就是同色异谱，
  一旦更换照明就会失效。想要区分就用光谱测量。
* **在线性空间中计算。** 不去除伽马求得的平均值不是物理量。

---

## 8. 诊断表 —— 从症状到原因

| 症状 | 首先怀疑 | 确认方法 |
| --- | --- | --- |
| 目视 OK 而相机 NG | 相机的光谱灵敏度与人不同（相机同色异谱） | 测量光谱反射率。做不到的话，在相同条件下拍摄标定色卡，看**该颜色附近**的残差是否较大 |
| 白天与夜间／不同季节判定结果不同 | 混入外界光，S(λ) 在变化 | 确认遮光后能否再现。用遮光帘围起来比较 |
| 更换照明后合格率变了 | LED 的光谱离散（即使同一型号也有批次差异） | 用新旧照明拍摄**同一块标准板**，比较通道比 |
| 图像缩小或平均后颜色变了 | 在伽马空间中做了运算 | 先恢复为线性再做同样的处理，进行比较 |
| 只有亮部的色相偏转 | 饱和（哪怕只有 1 个通道被截断也会偏转） | 查看各通道最大值的分布。统计停在饱和值上的像素数 |
| 只有视场边缘颜色不同 | 阴影未校正／边缘光量衰减（cos⁴） | 对白板满视场拍摄，取得平场后再判定 |
| ΔE 的数字与现场感觉不符 | 公式的选择（仍在用 CIE76）与 `kL` | 换成 ΔE94 / ΔE00，看与目视排序的相关性。阈值用自己的辨别实验重新确定 |
| Lab 值与其他公司对不上 | 白点和观察者不同（D65/D50、2°/10°） | 向对方确认**白点和观察者**。没有注明就不比较 |

---

## 出处

* CIE Standard Illuminants（D 系列的定义经过、D65 的相关色温约 6504 K、
  c₂ 修订造成与名义值的偏差、D 系列几乎无法人工再现） —
  <https://www.rp-photonics.com/cie_standard_illuminants.html> ／
  <https://www.image-engineering.de/library/technotes/753-cie-standard-illuminants>
* G. Sharma, W. Wu, E. N. Dalal, *The CIEDE2000 color-difference formula:
  Implementation notes, supplementary test data, and mathematical observations* —
  <https://hajim.rochester.edu/ece/sites/gsharma/papers/CIEDE2000CRNAFeb05.pdf>
* CIEDE2000 与 CIE94 各校正项的相对贡献，以及 CIE76 → CIE94 的改善
  大于 CIE94 → CIEDE2000 的改善（比较研究） —
  <https://www.researchgate.net/publication/8127013_Relative_significance_of_the_terms_in_the_CIEDE2000_and_CIE94_color-difference_formulas>
* `kL` 的惯例值（图形艺术 1、纺织 2） — MATLAB `imcolordiff` —
  <https://www.mathworks.com/help/images/ref/imcolordiff.html>
