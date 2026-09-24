> **Language**: [日本語](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/fullseye_poc_museum_what_qiita_ja.md) · **English**

# A Metrology Museum on Paper — The What-Is-Measured Wing (industrial, dimensional, biomedical, sky and ground)

> One wing of **[A Metrology Museum on Paper — the entrance](https://qiita.com/furuse-kazufumi/items/8a8f23e53b19ee8cdc10)**, where the other wings, the glossary and the thesis live.

**84 exhibits** hang in this wing. The numbers are accession numbers: they do not change when an exhibit moves or when an article is split.

> The "Ops used" line under each exhibit links to that op's note (type contract, pitfalls, figures, a runnable Studio program): [Operator catalogue](https://furuse.work/OP_CATALOG.html) / [Op notes index](https://furuse.work/ops/INDEX.html).

### The Industrial Inspection Wing — A Passing Number and a Failing Number Can Coexist

Numbers on an inspection line decide pass or fail, so there is a strong pull toward collapsing them into a single figure. The ten exhibits in this room show what disappears the moment you do: a pooled ROC that hides one defect class's blind spot in woven fabric, veiling glare that leaves the MTF passing while the black level fails, a barcode decoder that looks better by read rate alone because it never says 'unreadable'.

Every ground truth is planted: a closed-form periodic background, the laser-profile h(x), the analytic 1-D heat-conduction solution, closed-form bearing defect frequencies. That is what lets each exhibit measure 'where detection stops working' instead of 'detection worked', without fitting the threshold afterwards.

The other shared feature is that failure arrives as a cliff, not a slope: 15 versus 16 degrees of tilt, a 25-second versus a 4-second fitting window, ΔT of 1.6 K. Most of those positions can be predicted from geometry or physics first, and wherever they could be, the prediction is checked against the measurement.

## No.2026.003 —— Where a 1-D Barcode Stops Reading — Counting Misreads and Unreadables Separately

[![Where a 1-D Barcode Stops Reading — Counting Misreads and Unreadables Separately](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/01_misread_split_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/01_misread_split.png)

*↑ **Where a 1-D Barcode Stops Reading — Counting Misreads and Unreadables Separately** ―― A home-made simple code (not a real standard) damaged four ways, with success, misread and unreadable counted as three separate outcomes. Over the 384 images past the onset of damage, the strict decoder that checks run structure misreads 7.3 %, while the lenient decoder that always returns nine digits misreads 46.1 % — and has the higher success rate (47.7 % versus 40.1 %). The tilt cliff is pure geometry (predicted 15.95 degrees) and lands between 15 and 16 degrees.*

[![小さい汚れは行が「読めてしまう」ので誤った票を投じる。大きい汚れは棄権するので多数決が効く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/02_smudge_nonmonotone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/02_smudge_nonmonotone.png)

*↑ The measurement ―― 小さい汚れは行が「読めてしまう」ので誤った票を投じる。大きい汚れは棄権するので多数決が効く。 (figure labels are in Japanese; the numbers are the same)*

[![ぼけ 3 本(m=2,3,4 px)は 1 本に重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/03_collapse_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/03_collapse.png)

*↑ ぼけ 3 本(m=2,3,4 px)は 1 本に重なる。*

[![(d) は走査線が符号の上下からはみ出す角度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/04_barcode_damage_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/04_barcode_damage.png)

*↑ (d) は走査線が符号の上下からはみ出す角度。*

```
py -3.11 examples/poc_barcode_1d.py
```

Source: [examples/poc_barcode_1d.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_barcode_1d.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_barcode_1d)

Ops used (notes): [`decode_barcode`](https://furuse.work/ops/2d/barcode/decode_barcode.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html)

## No.2026.093 —— Electrode tortuosity from CT — the rule of thumb only sees porosity

[![Electrode tortuosity from CT — the rule of thumb only sees porosity](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/01_scene.png)

*↑ **Electrode tortuosity from CT — the rule of thumb only sees porosity** ―― A synthetic micro-CT of a lithium-ion electrode coating, measured for porosity and tortuosity. Against the shop-floor default (Bruggeman tau = eps^-0.5) we put the real thing: the steady-state diffusion equation solved on the same volume. At eps = 0.4448 the rule gives 1.499 against a true 1.843 (-18.6 %), and sweeping eps from 0.691 to 0.168 widens the error from -8.2 % to -69.1 % (fitted exponents 1.78 and 2.70 — never 1.5). The geodesic tortuosity that imaging papers report (1.182) merely has a square that hugs Bruggeman to within 1 %; neither goes near the truth. The decisive control: hold porosity at 0.4448 vs 0.4510 and flatten the particles 4:1, and through-plane tau jumps 1.843 -> 6.794 (anisotropy 0.97 -> 4.20) while the rule returns the same 1.5 for both — in-plane looks right (-8 %), through-plane collapses (-78 %). Closed pores peak at 1.92 % and are not the culprit; the necks, 0.40 of a particle radius wide, are. We predicted a resolution cliff and found none: coarsening the voxel 5.5x moves eps by -0.4 % but tau by +72 %, with no warning of any kind.*

[![左: 上端 1 / 下端 0 の濃度場。等濃度線が固相を避けて曲がる分が遠回り。右: bond ごとの散逸(明るいほど流れが集中している = 首)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/02_map_transport_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/02_map_transport.png)

*↑ The measurement ―― 左: 上端 1 / 下端 0 の濃度場。等濃度線が固相を避けて曲がる分が遠回り。右: bond ごとの散逸(明るいほど流れが集中している = 首)。 (figure labels are in Japanese; the numbers are the same)*

[![ε が下がるほど経験則と真値が開く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/03_porosity_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/03_porosity_sweep.png)

*↑ ε が下がるほど経験則と真値が開く。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/04_bruggeman_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/04_bruggeman_error.png)

*↑ この回の図*

[![経験則は向きを持てない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/05_anisotropy_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/05_anisotropy.png)

*↑ 経験則は向きを持てない。*

[![同じ物理構造を粗い格子から細かい格子まで。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/06_resolution_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/06_resolution.png)

*↑ 同じ物理構造を粗い格子から細かい格子まで。*

```
py -3.11 examples/poc_battery_electrode_tortuosity.py
```

Source: [examples/poc_battery_electrode_tortuosity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_tortuosity.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity)

Ops used (notes): [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html)

## No.2026.004 —— Rolling-Bearing Diagnosis — How Deep in Noise Can It Still Be Caught?

[![Rolling-Bearing Diagnosis — How Deep in Noise Can It Still Be Caught?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw.png)

*↑ **Rolling-Bearing Diagnosis — How Deep in Noise Can It Still Be Caught?** ―― An impulse train synthesised at the closed-form defect frequency (BPFO 104.556 Hz), sunk into noise, with detection rates of the raw spectrum and the envelope spectrum side by side. The worst SNR at which 10 of 10 seeds still detect is -0.9 dB for the raw spectrum and -18.4 dB for the envelope, a 17.5 dB gap. But a record with no defect at all still produces a global prominence of 43; had the threshold not been set from the null recording, this PoC would have been its own false positive.*

[![どちらも最悪条件では 0 に落ちる。包絡線は万能ではなく、崖が悪い SNR 側へ動くだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/02_detection_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/02_detection_sweep.png)

*↑ The measurement ―― どちらも最悪条件では 0 に落ちる。包絡線は万能ではなく、崖が悪い SNR 側へ動くだけ。 (figure labels are in Japanese; the numbers are the same)*

[![win=32 は毎回共振を含み、win=256 は毎回外す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/03_sk_bands_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/03_sk_bands.png)

*↑ win=32 は毎回共振を含み、win=256 は毎回外す。*

```
py -3.11 examples/poc_bearing_diagnosis.py
```

Source: [examples/poc_bearing_diagnosis.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bearing_diagnosis.py)

This run produced **3 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_bearing_diagnosis)

Ops used (notes): [`bearing_defect_frequencies`](https://furuse.work/ops/acoustics/bearing/bearing_defect_frequencies.html) · [`envelope_spectrum`](https://furuse.work/ops/acoustics/bearing/envelope_spectrum.html) · [`spectral_kurtosis`](https://furuse.work/ops/acoustics/bearing/spectral_kurtosis.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`synthesize_bearing_signal`](https://furuse.work/ops/acoustics/synthesis/synthesize_bearing_signal.html)

## No.2026.094 —— Bump coplanarity versus substrate warpage — subtract too much and the real defect goes with it

[![Bump coplanarity versus substrate warpage — subtract too much and the real defect goes with it](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/01_scene.png)

*↑ **Bump coplanarity versus substrate warpage — subtract too much and the real defect goes with it** ―― A height map of 256 Cu pillars is planted with 50 µm PV warpage, 4 µm 1-sigma pillar-to-pillar spread and six short bumps. The zero point — subtract only a least-squares plane, the JEDEC seating plane — reads the individual deviation with 8.84 µm RMS error (2.2x the real spread), raising 58 false rejects while missing one genuinely short bump. A quadratic reference surface brings it to 1.23 µm with zero false rejects; a cubic one is worse (1.37 µm), because the planted high-order mode is quartic and the four extra terms only absorb real signal. The cliff is predictable from geometry: the quadratic fit degrades to the 4 µm level at 169.9 µm PV (predicted) versus 169.4 µm (measured). Adding a real low-order defect — the centre sagging 8 µm — removes 88.2 % of it from the residual while the short-bump detection count stays at 5 of 6, and misses rise from 0 to 2; the lost signal reappears as warpage growing 30.06 to 36.20 µm.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/02_deviation_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/02_deviation_map.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![真値の共平面性は 38.44 µm、本当に仕様外なのは 5 本。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/03_order_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/03_order_table.png)

*↑ 真値の共平面性は 38.44 µm、本当に仕様外なのは 5 本。*

[![左端の 6 本が仕込んだ短小。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/04_sorted_deviation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/04_sorted_deviation.png)

*↑ 左端の 6 本が仕込んだ短小。*

[![そりの形を固定すれば、取り切れない残りは PV に比例する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/05_warpage_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/05_warpage_cliff.png)

*↑ そりの形を固定すれば、取り切れない残りは PV に比例する。*

[![消えた分はそり側の数字に足されている(+6.14 µm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/06_absorbed_defect_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/06_absorbed_defect.png)

*↑ 消えた分はそり側の数字に足されている(+6.14 µm)。*

```
py -3.11 examples/poc_bump_coplanarity.py
```

Source: [examples/poc_bump_coplanarity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bump_coplanarity.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_bump_coplanarity)

Ops used (notes): [`auto_threshold`](https://furuse.work/ops/2d/segmentation/auto_threshold.html) · [`background_flatten`](https://furuse.work/ops/3d/surface_fit/background_flatten.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`eval_poly_surface`](https://furuse.work/ops/3d/surface_fit/eval_poly_surface.html) · [`fit_poly_surface`](https://furuse.work/ops/3d/surface_fit/fit_poly_surface.html) · [`surface_form_error`](https://furuse.work/ops/3d/surface_fit/surface_form_error.html)

## No.2026.009 —— Concrete Crack Width Is Thinner Than a Pixel — Counting Width Versus Integrating Width

[![Concrete Crack Width Is Thinner Than a Pixel — Counting Width Versus Integrating Width](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/02_scene.png)

*↑ **Concrete Crack Width Is Thinner Than a Pixel — Counting Width Versus Integrating Width** ―― Cracks from 0.05 to 2.0 mm wide in a field where 1 px = 0.20 mm, measured by thresholding-and-counting and by integrating the intensity deficit across the crack. Thresholding returns nothing at or below 0.20 mm and reports 0.200 mm for all four true widths between 0.25 and 0.40 mm. Integration tracks continuously down to 0.05 mm (0.25 px), but curved illumination adds a +0.1741 mm offset under a first-order baseline (+0.0062 mm with second order).*

[![2 値化の 2 本は階段。0.20 mm(1 px)以下ではマスクが空になり 0(= 未検出)へ落ちる。積分法は 0.05 mm (0.25 px)まで直線 y=x に乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/01_width_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/01_width_sweep.png)

*↑ The measurement ―― 2 値化の 2 本は階段。0.20 mm(1 px)以下ではマスクが空になり 0(= 未検出)へ落ちる。積分法は 0.05 mm (0.25 px)まで直線 y=x に乗る。 (figure labels are in Japanese; the numbers are the same)*

[![点ごとでは 2 値化が下に見えるが、経路平均に直すと積分法の散らばりは消え、2 値化の偏りは残る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/03_crossover_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/03_crossover.png)

*↑ 点ごとでは 2 値化が下に見えるが、経路平均に直すと積分法の散らばりは消え、2 値化の偏りは残る。*

[![真の幅は 0.60 mm 固定。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/04_max_vs_mean_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/04_max_vs_mean.png)

*↑ 真の幅は 0.60 mm 固定。*

```
py -3.11 examples/poc_crack_width.py
```

Source: [examples/poc_crack_width.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_crack_width)

Ops used (notes): [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`sk_medial`](https://furuse.work/ops/2d/region/sk_medial.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`thinning`](https://furuse.work/ops/2d/region/thinning.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html)

## No.2026.017 —— Defects Buried in a Periodic Background — What a Pooled ROC Hides

[![Defects Buried in a Periodic Background — What a Pooled ROC Hides](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/04_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/04_scene.png)

*↑ **Defects Buried in a Periodic Background — What a Pooled ROC Hides** ―― Three defect classes (thread break, stain, dim patch) buried in a weave of period 8 px, with the detector's score map and per-class ROC curves side by side. The everyday recipe 'notch out the grid, remove low frequencies' pools to an AUC of 0.8113 and looks like a pass, but the dim-patch class alone scores 0.4746, worse than chance. The one line that removes low frequencies was deleting the defect along with the lighting; drop it and the class recovers to 0.9998.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/01_auc_by_type_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/01_auc_by_type.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![対角線に乗っている系列が盲点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/02_roc_by_type_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/02_roc_by_type.png)

*↑ 対角線に乗っている系列が盲点。*

[![欠陥の無い地だけで測った残差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/03_period_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/03_period_error.png)

*↑ 欠陥の無い地だけで測った残差。*

```
py -3.11 examples/poc_fabric_defect.py
```

Source: [examples/poc_fabric_defect.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fabric_defect.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fabric_defect)



## No.2026.069 —— Digging Where the Sound Says — A Clean Correlation Still Digs in the Wrong Place

[![Digging Where the Sound Says — A Clean Correlation Still Digs in the Wrong Place](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/01_scene.png)

*↑ **Digging Where the Sound Says — A Clean Correlation Still Digs in the Wrong Place** ―― Locating a leak in a 120 m buried main from the arrival-time difference at two sensors, with the source, sound speed, attenuation and reflections all planted as ground truth. With the true sound speed the estimate lands within 0.0107 m at 0 dB SNR (1.2x the Knapp-Carter bound of 0.0091 m); the threshold was predicted at -20.1 dB but measured at -12.5 dB, below which the error jumps to 36.0 m — the whole search window. Yet a 10 % error in the assumed sound speed alone moves the dig by 1.798 m (against the predicted (dc/c)(x-L/2) = 1.800 m), and on a pipe that changes from ductile iron to plastic mid-run the time difference is exactly zero, so iron, plastic or their average all miss by 18.001 m: no calibration of a single speed can fix a factor multiplying zero. The reflection prediction failed — GCC-PHAT beat the plain correlation by only 10 %, because 0.121 m of its 0.121 m RMS is bias, and whitening acts on the magnitude while the delay lives in the phase.*

[![同じ漏水源に既知の遅れ 28.80 ms・距離に応じた減衰・独立な広帯域雑音を乗せた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/02_waveforms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/02_waveforms.png)

*↑ The measurement ―― 同じ漏水源に既知の遅れ 28.80 ms・距離に応じた減衰・独立な広帯域雑音を乗せた。 (figure labels are in Japanese; the numbers are the same)*

[![探索窓は管路 0-120 m のぶんだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/03_correlation_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/03_correlation_curves.png)

*↑ 探索窓は管路 0-120 m のぶんだけ。*

[![漏水位置を 41 点振った。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/05_quantization_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/05_quantization.png)

*↑ 漏水位置を 41 点振った。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/08_gross_rate_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/08_gross_rate.png)

*↑ この回の図*

[![相関の形も相関係数も一切変わらない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/11_sound_speed_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/11_sound_speed_error.png)

*↑ 相関の形も相関係数も一切変わらない。*

```
py -3.11 examples/poc_leak_localization.py
```

Source: [examples/poc_leak_localization.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leak_localization.py)

This run produced **13 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_leak_localization)

Ops used (notes): [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`bandpass`](https://furuse.work/ops/oned/signal/bandpass.html) · [`correlation_score`](https://furuse.work/ops/reprconv/score/correlation_score.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`transfer_function`](https://furuse.work/ops/acoustics/dual/transfer_function.html)

## No.2026.071 —— Fusing thermal, vibration and geometry for machine health — three sensors, one fact

[![Fusing thermal, vibration and geometry for machine health — three sensors, one fact](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/01_scene_machine_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/01_scene_machine.png)

*↑ **Fusing thermal, vibration and geometry for machine health — three sensors, one fact** ―― Six states of a rotating machine (healthy, misalignment, unbalance, outer-race spall, poor lubrication, looseness) are built from closed-form bearing defect frequencies, the exact steady fin-equation solution for the casing temperature, and a planted shaft offset, then classified from three sensors. Fused accuracy is 100.0 % — but vibration alone is also 100.0 %: thermal and geometry add nothing. Misalignment reaches 100.0 % from any single sensor (correlations with the true severity 0.843 / 0.841 / 0.978 — three faces of one number), while thermal alone can never separate healthy, unbalance and looseness (48/48 confusions inside that trio) and dropping vibration takes them from 100.0 % to 50.0 % / 31.2 %. Fusion only earns its keep once vibration breaks: at noise sigma 1.6 it lifts 45.8 % to 78.1 %. The cliffs were predicted on single features: the 0.5X order bin needs T > 2/f_r = 68.6 ms (measured d' 2.45 -> 4.32 across the 50 -> 70 ms step), the thermal spread dies past the 66 mm half-diameter (d' 0.00 at 96 mm pitch). The sideband prediction 1/T < FTF = 86.1 ms was wrong; the peak-reading window condition 1.2/FTF = 103 ms is the right one.*

[![軸受外輪傷は狭く熱く、潤滑不良は広く熱い。最高温度だけ見ると同じ顔になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/02_thermal_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/02_thermal_maps.png)

*↑ The measurement ―― 軸受外輪傷は狭く熱く、潤滑不良は広く熱い。最高温度だけ見ると同じ顔になる。 (figure labels are in Japanese; the numbers are the same)*

[![芯ずれは 2X、アンバランスは 1X、ゆるみは 0.5X と櫛。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/03_order_spectra_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/03_order_spectra.png)

*↑ 芯ずれは 2X、アンバランスは 1X、ゆるみは 0.5X と櫛。*

[![平行ずれ(切片)と角度ずれ(傾き)を fit_line3 で分けて取る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/05_misalignment_geometry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/05_misalignment_geometry.png)

*↑ 平行ずれ(切片)と角度ずれ(傾き)を fit_line3 で分けて取る。*

[![芯ずれと軸受外輪傷は無傷。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/08_confusion_without_vibration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/08_confusion_without_vibration.png)

*↑ 芯ずれと軸受外輪傷は無傷。*

[![予測は 68.6 ms(0.5X の次数ビン)と 86.1 ms(FTF 側帯波)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/11_sweep_record_length_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/11_sweep_record_length.png)

*↑ 予測は 68.6 ms(0.5X の次数ビン)と 86.1 ms(FTF 側帯波)。*

```
py -3.11 examples/poc_machine_condition_fusion.py
```

Source: [examples/poc_machine_condition_fusion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_machine_condition_fusion.py)

This run produced **13 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_machine_condition_fusion)

Ops used (notes): [`angle_between_lines`](https://furuse.work/ops/3d/geometry/angle_between_lines.html) · [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`bearing_defect_frequencies`](https://furuse.work/ops/acoustics/bearing/bearing_defect_frequencies.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`distance_point_line`](https://furuse.work/ops/3d/geometry/distance_point_line.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`jitter`](https://furuse.work/ops/3d/augment/jitter.html) · [`mat_pinv`](https://furuse.work/ops/math/linalg/mat_pinv.html) · [`rounded_rect`](https://furuse.work/ops/annotate/shape/rounded_rect.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html) · [`synthesize_bearing_signal`](https://furuse.work/ops/acoustics/synthesis/synthesize_bearing_signal.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.024 —— Reading a Binary Matrix Code — Geometry Always Dies First

[![Reading a Binary Matrix Code — Geometry Always Dies First](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors.png)

*↑ **Reading a Binary Matrix Code — Geometry Always Dies First** ―― A code with QR-style layout and random data bits (no error correction), damaged by blur, tilt and occlusion, with the raw bit error rate counted directly. The nulls sit at chance (0.526 / 0.507) while the reader scores 0.0000. Cliffs: 78 degrees of tilt, two modules of finder-pattern occlusion; run beside the condition that receives the true homography, localisation is always the stage that fails first.*

[![自力検出の線は sigma/m 0.50 を最後に途切れる(0.60 では位置検出パターンが見つからない)。標本化はそこでまだ BER 0.07 で読めている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/02_blur_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/02_blur_cliff.png)

*↑ The measurement ―― 自力検出の線は sigma/m 0.50 を最後に途切れる(0.60 では位置検出パターンが見つからない)。標本化はそこでまだ BER 0.07 で読めている。 (figure labels are in Japanese; the numbers are the same)*

[![照明ムラ 0.9 固定。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/03_threshold_window_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/03_threshold_window.png)

*↑ 照明ムラ 0.9 固定。*

[![位置検出パターンは一辺 2 モジュール(全体の 0.6 %)で致命的。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/04_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/04_occlusion.png)

*↑ 位置検出パターンは一辺 2 モジュール(全体の 0.6 %)で致命的。*

```
py -3.11 examples/poc_matrix_code_reading.py
```

Source: [examples/poc_matrix_code_reading.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_matrix_code_reading.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_matrix_code_reading)

Ops used (notes): [`adaptive_gauss_thresh`](https://furuse.work/ops/2d/segmentation/adaptive_gauss_thresh.html) · [`corner_response`](https://furuse.work/ops/2d/edges/corner_response.html) · [`illuminate`](https://furuse.work/ops/2d/gray/illuminate.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_sauvola`](https://furuse.work/ops/2d/segmentation/sk_sauvola.html)

## No.2026.025 —— Can Display-Inspection Moire Be Told From Real Non-Uniformity?

[![Can Display-Inspection Moire Be Told From Real Non-Uniformity?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/04_moire_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/04_moire_scene.png)

*↑ **Can Display-Inspection Moire Be Told From Real Non-Uniformity?** ―― Moire from the interference of the display's stripes with the camera's pixel grid, overlaid on genuine luminance non-uniformity in one image. At a smoothing σ of 8 px the total error is +0.9 %, made of +8.3 % moire leakage cancelling -7.4 % attenuation of the real defect. At k = 0.67 the fundamental beat looks safe, yet the third harmonic lands in the defect band and the leakage reaches +202.6 % of the true value.*

[![σ≈8 px で漏れと減衰が釣り合う。合計だけ見ると「良い測り方」に見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/01_failure_split_plot_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/01_failure_split_plot.png)

*↑ The measurement ―― σ≈8 px で漏れと減衰が釣り合う。合計だけ見ると「良い測り方」に見える。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/02_methods.png)

*↑ この回の図*

[![縦線がムラの周波数。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/03_separability_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/03_separability.png)

*↑ 縦線がムラの周波数。*

```
py -3.11 examples/poc_moire_screen.py
```

Source: [examples/poc_moire_screen.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_moire_screen.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_moire_screen)

Ops used (notes): [`background_flatten`](https://furuse.work/ops/3d/surface_fit/background_flatten.html) · [`fft_image`](https://furuse.work/ops/2d/frequency/fft_image.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`halftone_moire_period`](https://furuse.work/ops/printpath/npr/halftone_moire_period.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## No.2026.102 —— Print Misregistration from the Sheet — A Halftone Is a Lattice, So the Answer Is Not Unique

[![Print Misregistration from the Sheet — A Halftone Is a Lattice, So the Answer Is Not Unique](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/04_sweep_wrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/04_sweep_wrap.png)

*↑ **Print Misregistration from the Sheet — A Halftone Is a Lattice, So the Answer Is Not Unique** ―― Measuring print misregistration from the printed sheet. Four CMYK plates carry the conventional screen angles (C 15, M 75, Y 0, K 45 degrees) at 133 lpi scanned at 1200 dpi, giving a screen pitch of 9.02 px, and each plate is displaced by a known amount. The central claim is geometry: a halftone is a lattice, so correlation recovers not the displacement d but d modulo the screen lattice. Along the lattice axes that limit is p/2 = 4.51 px and along the diagonal p/sqrt(2) = 6.38 px; beyond it the measurement folds back. Stated in closed form before measuring, it matches at 144 of 148 points (four plates by 37 sweep positions) to within 0.1096 px. The four exceptions are ties on the boundary of the fundamental cell, with at most 0.165 px of margin, and reducing modulo the lattice makes every point agree: the estimator is not wrong, it returns one of the lattice-equivalent answers, and two independent estimators fold identically. The consequence is concrete. A true displacement of 9.64 px, 4.8 times the 2.0 px tolerance, appears as 1.09 to 3.32 px depending only on the screen angle, so two of the four plates look like they pass — from one sheet displaced by one amount. The null baseline, the centroid of ink, does not fold but loses its scale: the slope follows the closed form k = 1 - beta, where beta is the ink of the flat background over the total ink, predicted 0.3983 against 0.3711 measured. One effect was not predicted at all: a 0.9864 px ripple at the screen pitch, caused by rows of dots entering and leaving at the window edge, which a tapered-window control drops to 0.0048 px. Switching to an FM (stochastic) screen removes the folding entirely, with an error of at most 0.0029 px across the whole sweep, which places the blame on the periodicity of the AM screen rather than on the estimator, at the cost of 0.91 times the contrast. A window containing a registration mark reads correctly to 0.0823 px, but with 0.600 % paper stretch and 0.120 degrees of plate rotation the error grows linearly with distance at 0.006319 px per px and exceeds tolerance from 316.5 px predicted, 322.5 px measured — 44 % of the sheet. Two rulers reverse the ranking: raw correlation is the most accurate at 0.0071 px yet agrees with the pass/fail verdict only 67.6 % of the time, while low-pass filtering agrees 89.2 % of the time at 94 times the error; a two-stage estimator that picks the representative with the blunt method and refines with the sharp one wins both, and it fails exactly at the points where the coarse error exceeded the cell radius of 4.511 px. The synthesiser itself was a trap: at 150 lpi and 1200 dpi the pitch is exactly 8.00 px, every dot samples in phase, and the centroid jumps 1.4 px for each 0.5 px of displacement — avoiding the integer ratio is the fix, not supersampling. Finally, an operator used outside its domain failed confidently: fs.frame_align returned inlier_ratio 1.00 and rms_px 0.645 while missing the true (0.00, +1.30) by 80.85 px, and the answer was not even a lattice vector. That finding was fixed in the operator: its docstring now records the measurement, and the vote histogram's runner-up over winner is returned as vote_margin — 1.000 on this halftone against 0.143 on a star field, where the agreement ratio is 1.00 in both.*

[![スクリーン角が違うので格子の向きが違う。ピッチはどれも 9.02 px。同じ物理的なずれでも、この格子の違いが「見かけのずれ」を版ごとに変える(5 節)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/01_plates_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/01_plates.png)

*↑ The measurement ―― スクリーン角が違うので格子の向きが違う。ピッチはどれも 9.02 px。同じ物理的なずれでも、この格子の違いが「見かけのずれ」を版ごとに変える(5 節) (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/02_zero_point_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/02_zero_point.png)

*↑ この回の図*

[![スクリーン角が違えば格子も違う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/05_sweep_all_plates_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/05_sweep_all_plates.png)

*↑ スクリーン角が違えば格子も違う。*

[![絵柄も推定器も同じ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/08_control_fm_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/08_control_fm.png)

*↑ 絵柄も推定器も同じ。*

[![十字は非周期なので相関のピークが 1 つに決まる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/11_mark_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/11_mark_scene.png)

*↑ 十字は非周期なので相関のピークが 1 つに決まる。*

```
py -3.11 examples/poc_print_registration.py
```

Source: [examples/poc_print_registration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_registration.py)

This run produced **13 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_print_registration)

Ops used (notes): [`fly_hex_lattice`](https://furuse.work/ops/flyvision/lattice/fly_hex_lattice.html) · [`frame_align`](https://furuse.work/ops/astrostack/align/frame_align.html) · [`halftone_moire_period`](https://furuse.work/ops/printpath/npr/halftone_moire_period.html) · [`halftone_screen`](https://furuse.work/ops/printpath/npr/halftone_screen.html) · [`peak_subbin`](https://furuse.work/ops/oned/signal/peak_subbin.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html)

## No.2026.116 —— How Faint a Defect Can Still Be Found — Planting a Known Truth in a Real Background

[![How Faint a Defect Can Still Be Found — Planting a Known Truth in a Real Background](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_defect_floor/01_defect_floor_panels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_defect_floor/01_defect_floor_panels.png)

*↑ **How Faint a Defect Can Still Be Found — Planting a Known Truth in a Real Background** ―― The usual way to estimate "how faint a defect can we still catch" is to measure the limit on a synthetic image: a flat field plus white noise. This exhibit measures how optimistic that estimate is, while keeping an exact ground truth. The backgrounds are three CC0 photographs (brick / grass / gravel); what is planted into them is a Gaussian defect of known position, width and amplitude. The control is a synthetic field whose **residual sigma — the variation the detector actually sees — is matched to the real one**, so the amount of noise is equal and only structure differs. The verdict is the smallest amplitude at which the planted position becomes the peak of the response; no threshold is involved, so per-image normalisation inside an operator cannot skew it. **Matching the noise is not enough: the real backgrounds raise the floor by 2.03x to 3.47x.** What sets the floor is structure, not noise. The gap survives all 18 knob settings (three background windows x two defect sizes x three grounds, 1.72x-4.56x) and both detectors — a matched filter and fullseye's `laplace_of_gauss`. **A prediction that failed:** "the gap widens for larger defects" turned out to be an artefact of the amplitude grid — on 34 steps the two sizes round to different grid points, on 60 steps both land at 3.30x. The grid is a knob too. **"Real data is position-dependent" is also wrong:** the spread of the floor across positions is 16.8x on brick but 2.4x on grass and 3.3x on gravel, indistinguishable from the 3.3x of the matched synthetic control. What creates the spread is the mortar lattice — a structure — not the fact that the image is a photograph. **And the null model wins on a single metric.** Taking the brightest raw pixel, with no background removed, localises the defect at 0.65x-0.90x the amplitude the matched filter needs, because the matched filter amplifies the background's structure too; false alarms on a defect-free surface tie at 0 on brick. The two separate the moment the lamp drifts by 2 %: the null model fires 10.3 times per 10,000 pixels while the matched filter stays at 0.0, because a raw-pixel threshold is an absolute brightness. **Count localisation, false alarms and drift separately, or a useless detector can be made to win.***

[![同じ欠陥を振幅 0.02 から 1.20 まで上げていく。左=実写の brick、右=**残差 σ を揃えた**合成の地。雑音の量は同じなのに、右のほうが先に見えてくる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif)

*↑ The measurement ―― 同じ欠陥を振幅 0.02 から 1.20 まで上げていく。左=実写の brick、右=**残差 σ を揃えた**合成の地。雑音の量は同じなのに、右のほうが先に見えてくる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_real_defect_floor.py
```

Source: [examples/poc_real_defect_floor.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py)

This run produced **2 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_defect_floor)

Ops used (notes): [`annotate_inset`](https://furuse.work/ops/annotate/paper/annotate_inset.html) · [`annotate_legend`](https://furuse.work/ops/annotate/paper/annotate_legend.html) · [`laplace_of_gauss`](https://furuse.work/ops/2d/edges/laplace_of_gauss.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## No.2026.109 —— Rotating Real Textures — Rotation Invariance Holds Only Where It Is Not Needed

[![Rotating Real Textures — Rotation Invariance Holds Only Where It Is Not Needed](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/01_textures_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/01_textures.png)

*↑ **Rotating Real Textures — Rotation Invariance Holds Only Where It Is Not Needed** ―― Three real textures (brick, grass, gravel, all CC0) rotated by known angles, measuring how far the descriptor drifts from itself. The benchmark is set before measuring: the smallest distance between materials, 0.01250 between grass and gravel, is the resolution of the task, and any rotation drift beyond it means a rotated sample is further from itself than from a different material. The anisotropic brick drifts 0.0433 at five degrees and 0.1205 at sixty, 9.6 times the resolution, while grass and gravel stay at 0.0005 to 0.0024, effectively invariant. Two controls isolate the cause: interpolation alone, measured by rotating plus seven and back minus seven degrees, contributes 0.03685 for brick, and an exact ninety-degree rotation with no interpolation at all still gives 0.08501, or 6.8 times the resolution. Anisotropy can be measured independently and explains the ranking: the global concentration of gradient orientation is 0.309 for brick against 0.027 and 0.029 for the others. Switching to rotation-invariant encodings brings brick from 9.64 down through 5.49 to 1.72 — never below one — while the isotropic pair improves tenfold, from 0.17 to 0.02. LBP's rotation invariance applies to the cyclic shift of a local pattern; it cannot remove the orientation distribution of the material itself.*

[![brick だけが 1 を大きく超える(最大 9.6 倍)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/02_drift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/02_drift.png)

*↑ The measurement ―― brick だけが 1 を大きく超える(最大 9.6 倍)。 (figure labels are in Japanese; the numbers are the same)*

[![等方な 2 つは 10 倍良くなる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/03_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/03_methods.png)

*↑ 等方な 2 つは 10 倍良くなる。*

[![単位はどれも「分解能に対する比」。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/04_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/04_summary.png)

*↑ 単位はどれも「分解能に対する比」。*

```
py -3.11 examples/poc_real_texture_invariance.py
```

Source: [examples/poc_real_texture_invariance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_texture_invariance.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_texture_invariance)

Ops used (notes): [`cooc_feature_matrix`](https://furuse.work/ops/2d/texture/cooc_feature_matrix.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sk_lbp`](https://furuse.work/ops/2d/texture/sk_lbp.html)

## No.2026.079 —— Sorting mixed waste by material — what a preprocessor can erase is decided by algebra

[![Sorting mixed waste by material — what a preprocessor can erase is decided by algebra](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/01_scene.png)

*↑ **Sorting mixed waste by material — what a preprocessor can erase is decided by algebra** ―― Fragments on a belt carry material, dirt, wetness, tilt and occlusion in known amounts, imaged in 64 SWIR bands. Per-fragment degradation is closed form, s(l)=g*R(l)*exp(-w*A_w(l))+(a*u(l)+c), so invariance can be predicted before measuring: the spectral angle is invariant to the multiplicative g (0.995 to 0.990 as dirt goes 0 to 0.8; 0.993 at 70 degrees of tilt), and a second derivative annihilates the linear baseline (raw SAM falls 0.995 to 0.827 under an additive baseline while the derivative stays at 0.995 at every level). Two predictions failed: wetness is largely removed by the second derivative (0.818 against 0.282 for raw SAM) because a second derivative weights Gaussian bands by 1/sigma^2 ((43/70)^2 = 0.37), and continuum removal beats raw SAM while the baseline is weak (0.983 vs 0.865) but loses once it is strong (0.736 vs 0.827). Featureless metal vanishes under differentiation (recall 0.06) and a flatness gate restores it to 0.98.*

[![PP と PE は骨格が同じ(-CH2-)なのでわざと似せてある。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/02_library_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/02_library.png)

*↑ The measurement ―― PP と PE は骨格が同じ(-CH2-)なのでわざと似せてある。 (figure labels are in Japanese; the numbers are the same)*

[![乗算汚れ・傾き・重なりは平ら(SAM は明るさに不変)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/03_sweep_raw_sam_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/03_sweep_raw_sam.png)

*↑ 乗算汚れ・傾き・重なりは平ら(SAM は明るさに不変)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/06_sweep_detection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/06_sweep_detection.png)

*↑ この回の図*

[![1 個の正解率には出ない盲点がここに出る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/09_confusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/09_confusion.png)

*↑ 1 個の正解率には出ない盲点がここに出る。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/12_mixed_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/12_mixed_map.png)

*↑ この回の図*

```
py -3.11 examples/poc_recycling_sorting.py
```

Source: [examples/poc_recycling_sorting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_recycling_sorting.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_recycling_sorting)

Ops used (notes): [`overlay_labels`](https://furuse.work/ops/annotate/overlay/overlay_labels.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html)

## No.2026.084 —— Power loss from solar-cell EL images — dark is not the same as inactive

[![Power loss from solar-cell EL images — dark is not the same as inactive](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/01_zero_point_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/01_zero_point_map.png)

*↑ **Power loss from solar-cell EL images — dark is not the same as inactive** ―― A crystalline-silicon cell (100 fingers, 3 busbars, 70 grains) is rendered in closed form as an EL image with two electrically isolated regions (true inactive area 4.77 %), 5 cracks and 8 finger interruptions, then imaged through cos^4 vignetting and photon noise. The zero-point global threshold reports a dark-pixel fraction of 21.7 % as the inactive area, but 42 % of those pixels are fingers and busbars and 33 % are grains and vignetting; only 20 % are truly inactive. Dividing out the grid with row/column profiles and gating each defect type separately gives 4.61 % (-0.15 points), crack recall 0.88–1.00 and 8/8 interruptions. Because sk_frangi normalises by the per-image maximum, a calibration line only fixes the scale if it is the strongest ridge in the image (a line like the real cracks responds 0.69, a 3 px black line 1.00); without calibration the defect-free cell produces 147 px of false cracks. From grain contrast c=0.24 false cracks and swallowed interruption bands start together, and the crack-width cliff at 1.25 px follows the linear width-times-depth rule (predicted 1.38 px).*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/02_by_type_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/02_by_type.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![孤立領域 2 つ・クラック 5 本・断線 8 本。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/03_scene_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/03_scene_map.png)

*↑ 孤立領域 2 つ・クラック 5 本・断線 8 本。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/04_frangi_norm_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/04_frangi_norm.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/06_crack_width_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/06_crack_width.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/07_vignette_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/07_vignette.png)

*↑ この回の図*

```
py -3.11 examples/poc_solar_el_inspection.py
```

Source: [examples/poc_solar_el_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_el_inspection.py)

This run produced **8 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_solar_el_inspection)

Ops used (notes): [`aug_vignette`](https://furuse.work/ops/2d/augmentation/aug_vignette.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`gray_closing`](https://furuse.work/ops/2d/morphology/gray_closing.html) · [`hysteresis_threshold`](https://furuse.work/ops/2d/segmentation/hysteresis_threshold.html) · [`lines_gauss`](https://furuse.work/ops/2d/contour/lines_gauss.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_frangi`](https://furuse.work/ops/2d/texture/sk_frangi.html) · [`sk_skeleton`](https://furuse.work/ops/2d/region/sk_skeleton.html) · [`total_length`](https://furuse.work/ops/2d/features/total_length.html) · [`vignette`](https://furuse.work/ops/gfx2d/post/vignette.html)

## No.2026.085 —— Solder fillet AOI — three ring lights are a 3-level tilt quantiser, and 70 % of the fillet height sits in the dark

[![Solder fillet AOI — three ring lights are a 3-level tilt quantiser, and 70 % of the fillet height sits in the dark](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/02_scene_grid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/02_scene_grid.png)

*↑ **Solder fillet AOI — three ring lights are a 3-level tilt quantiser, and 70 % of the fillet height sits in the dark** ―― A 1608 chip's pads and terminations carry circular-arc fillets fixed by contact angle and cross-section area; three ring lights at different elevations (red 30-40°, green 15-30°, blue 0-15° of surface tilt) are integrated over a GGX lobe to synthesise the AOI image, and joints are graded good / insufficient / bridge / tombstone. With an 18° contact angle the concave arc rises to 72° at the wall, so even the lowest ring sees only 28.8 % of the height (predicted): naively integrating the band tilts recovers 0.284 of the true height. Extrapolating the arc to the wall from the positions where the colour changes lands at +1.7 % ± 5.3 % for free arcs, but once extra solder pins the toe at the pad edge it drifts to -42.3 %. A 0.16 mm placement offset steepens the toe past 30°, the green band vanishes and a good joint is called insufficient although its true height has risen (predicted 0.16 mm; the truth only fails at 0.28 mm). Surface roughness, against expectation, does not move the dark edge; it breaks at roughness 0.5 together with the loss of the red band and at 0.6 the whole fillet drops below the dark threshold. The zero point (Lab distance of the pad mean colour) is 100 % right under reference conditions yet flags 56 % of good joints and 68 % of bridges once offset, roughness and lighting vary — no discrimination — while the arc-based grading scores good 98 % / insufficient 98 % / bridge 100 % / tombstone 88 %, the misses all being lifts of 8.7-11.0°.*

[![鏡面なら窓の端が階段になる。傾き 40° を超えるとどのリングも届かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut.png)

*↑ The measurement ―― 鏡面なら窓の端が階段になる。傾き 40° を超えるとどのリングも届かない。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/03_tilt_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/03_tilt_map.png)

*↑ この回の図*

[![E1 は 0.28 倍の直線に乗る(暗部を見ていない)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/05_volume_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/05_volume_sweep.png)

*↑ E1 は 0.28 倍の直線に乗る(暗部を見ていない)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/08_shift_verdict_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/08_shift_verdict.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/10_ring_lut_rough_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/10_ring_lut_rough.png)

*↑ この回の図*

```
py -3.11 examples/poc_solder_fillet_aoi.py
```

Source: [examples/poc_solder_fillet_aoi.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solder_fillet_aoi.py)

This run produced **12 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_solder_fillet_aoi)

Ops used (notes): [`access_channel`](https://furuse.work/ops/2d/color/access_channel.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`brdf_microfacet`](https://furuse.work/ops/specular/reflectance/brdf_microfacet.html) · [`illumination_design`](https://furuse.work/ops/optics/illumination/illumination_design.html) · [`intensity`](https://furuse.work/ops/2d/features/intensity.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html) · [`trans_from_rgb`](https://furuse.work/ops/2d/color/trans_from_rgb.html)

## No.2026.121 —— Is the Process in Control, and Is It Capable? — Statistical Process Control from Closed-Form Alone

[![Is the Process in Control, and Is It Capable? — Statistical Process Control from Closed-Form Alone](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spc/01_spc_xbar_chart_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spc/01_spc_xbar_chart.png)

*↑ **Is the Process in Control, and Is It Capable? — Statistical Process Control from Closed-Form Alone** ―― A series of dimensions and defect counts measured by machine vision, fed through four SPC ops that use no learning at all (each a textbook closed-form with an exact identity to check against). The Xbar-R chart catches a +4σ shift planted at the tail across 4 subgroups at once (n=5 constants A2/D3/D4 = 0.577/0.000/2.115, ISO 8258); CUSUM catches a +0.8σ sustained drift that Shewhart 3σ never flags, at #45 (right after the drift starts). Process capability separates "capable" from "capable at the current centre": centred on the spec midpoint Cpk = Cp = 1.307, shifted by +1 Cpk = 0.981 < Cp. Multivariate T² folds the simultaneous drift of three correlated measurements into one verdict (UCL from the F-distribution). As with image restoration, a process running and a process in control are measured separately.*

[![Shewhart 3σ は 0 件、CUSUM は #46(ドリフト開始の直後)で h=5 を超えて警報。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spc/02_spc_cusum_chart_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spc/02_spc_cusum_chart.png)

*↑ The measurement ―― Shewhart 3σ は 0 件、CUSUM は #46(ドリフト開始の直後)で h=5 を超えて警報。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_spc.py
```

Source: [examples/poc_spc.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_spc.py)

This run produced **2 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_spc)

Ops used (notes): [`spc_capability`](https://furuse.work/ops/spc/capability/spc_capability.html) · [`spc_cusum`](https://furuse.work/ops/spc/change/spc_cusum.html) · [`spc_ewma`](https://furuse.work/ops/spc/change/spc_ewma.html) · [`spc_hotelling_t2`](https://furuse.work/ops/spc/multivariate/spc_hotelling_t2.html) · [`spc_xbar_r`](https://furuse.work/ops/spc/chart/spc_xbar_r.html)

## No.2026.042 —— How Much Camera Thermal Drift Costs a Dimensional Measurement

[![How Much Camera Thermal Drift Costs a Dimensional Measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/04_error_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/04_error_maps.png)

*↑ **How Much Camera Thermal Drift Costs a Dimensional Measurement** ―― A 40 mm square measured by a camera whose focal length, mount and principal point drift with temperature ΔT, the error split into a + b·R in image radius. At ΔT = 15 K the constant term is +224.5 ppm (the single-cause control gives +225.3 ppm). Drift rises above the noise floor (23 ppm for a 25-frame average) only from ΔT = 1.6 K; below that, the honest report is that no temperature effect is visible.*

[![焦点距離ドリフトは R に依らない。主点ドリフトは R に比例(歪みを外す中心がずれるため)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts.png)

*↑ The measurement ―― 焦点距離ドリフトは R に依らない。主点ドリフトは R に比例(歪みを外す中心がずれるため)。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/02_countermeasures_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/02_countermeasures.png)

*↑ この回の図*

[![周辺のワークのほうが感度が高い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/03_budget_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/03_budget.png)

*↑ 周辺のワークのほうが感度が高い。*

```
py -3.11 examples/poc_thermal_drift_metrology.py
```

Source: [examples/poc_thermal_drift_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_drift_metrology.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_thermal_drift_metrology)



## No.2026.113 —— A Thermal Image Is Not a Temperature Image — Emissivity, Reflection, and an Uncertainty That Does Not Add

[![A Thermal Image Is Not a Temperature Image — Emissivity, Reflection, and an Uncertainty That Does Not Add](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/15_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/15_scene.png)

*↑ **A Thermal Image Is Not a Temperature Image — Emissivity, Reflection, and an Uncertainty That Does Not Add** ―― Take a thermal camera's digital numbers all the way back to temperature, with the truth planted: L = tau [ eps L_bb(T_obj) + (1-eps) L_bb(T_refl) ] + (1-tau) L_bb(T_atm). The floor is measured first — 1.75e-06 K round trip, 6.28e-03 K with quantisation, 2.71e-02 K with NETD — and re-measured off the calibration knots, because at exactly 350.0 K the error came out identically zero and calling that a floor would be a lie. The closed form was printed before measuring, and it was wrong: the naive Planck exponent n = c2/(lambda T) misses the numerical derivative by up to 16.6 %, and the culprit is not the choice of effective wavelength but the missing e^x/(e^x - 1) factor; with it the error is 0.00 %. The direction of the cliff was wrong too. 'Colder is steeper' was printed, but the absolute error grows with temperature (0.233 K at 305 K against 16.907 K at 800 K for a 5 % emissivity error), with a measured log-log slope of 2.717 that decomposes exactly as T/n = 1.741 plus a reflection term of 0.977 — the closed form had said so all along and was misread. 'Colder is steeper' does hold when the error is scaled by the rise above ambient, but the culprit is different: the emissivity term only moves 1.40 times and converges, while getting the reflected temperature wrong moves 972 times. The centre of the exhibit is that uncertainty does not add. With emissivity 0.60 +/- 0.05, reflected temperature 300 +/- 5 K and a correlation of +0.7, a '95 % interval' actually contains the truth 88.03 % of the time under independent root-sum-square and 94.44 % under a correlated Monte Carlo — and the floor was measured first, since at zero correlation the two agree (95.03 % and 94.52 %), so the gap is the neglected correlation itself and nothing else. The RSS interval is 20.2 % too narrow; at a correlation of -0.7 it becomes 99.64 %, too wide. Assuming independence is neither the safe side nor the dangerous side — it is the unknown side. On an acceptance decision over 40000 trials the false-accept rate runs 8.03 % ignoring uncertainty, 0.81 % with RSS and 0.14 % with the correlated Monte Carlo: RSS lets through 5.6 times as many bad parts. Of eight unit and convention mistakes, three raise and five pass silently — and the same mistake (writing the reflected temperature in Celsius) passes quietly at emissivity 0.95 while raising at 0.10, so whether the code stops depends on the scene, not on the kind of error. In the image itself a bolt at emissivity 0.10 sitting directly over the heat source reads 62.3 K colder than the painted metal around it at the same 375.0 K: the hottest place looks the healthiest. Correcting with an emissivity map recovers 375.0 K, but trades bias for variance — the residual is 6.4 times noisier on the bolt than on the paint. Along the way a real defect was found and fixed: the robust noise estimate collapses to zero on integer digital numbers, and the downstream point-target detector was silently returning nothing at all.*

[![LWIR・350 K・ε=0.95。校正表と直接積分の相対差は最大 8.9e-16。以下の誤差はすべてこの床の上。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/01_floor_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/01_floor.png)

*↑ The measurement ―― LWIR・350 K・ε=0.95。校正表と直接積分の相対差は最大 8.9e-16。以下の誤差はすべてこの床の上。 (figure labels are in Japanese; the numbers are the same)*

[![n = d ln L_bb/d ln T。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/02_planck_index_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/02_planck_index.png)

*↑ n = d ln L_bb/d ln T。*

[![LWIR・T_obj = 350 K・T_refl = 300 K。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/06_cliff_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/06_cliff_curves.png)

*↑ LWIR・T_obj = 350 K・T_refl = 300 K。*

[![20000 試行 / 点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/10_coverage_rho_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/10_coverage_rho.png)

*↑ 20000 試行 / 点。*

[![止まるのは校正表の範囲外に落ちたときだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/14_units_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/14_units.png)

*↑ 止まるのは校正表の範囲外に落ちたときだけ。*

```
py -3.11 examples/poc_thermal_radiometry.py
```

Source: [examples/poc_thermal_radiometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_radiometry.py)

This run produced **18 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_thermal_radiometry)

Ops used (notes): [`beer_lambert_transmittance`](https://furuse.work/ops/optics/glassbody/beer_lambert_transmittance.html) · [`interp_linear`](https://furuse.work/ops/math/interp_poly/interp_linear.html) · [`mat_eigh`](https://furuse.work/ops/math/linalg/mat_eigh.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`photon_uncertainty`](https://furuse.work/ops/photon/counting/photon_uncertainty.html) · [`poly_fit`](https://furuse.work/ops/math/interp_poly/poly_fit.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html) · [`stat_covariance`](https://furuse.work/ops/math/stats/stat_covariance.html) · [`stat_describe`](https://furuse.work/ops/math/stats/stat_describe.html) · [`stat_histogram`](https://furuse.work/ops/math/stats/stat_histogram.html)

## No.2026.043 —— Depth of a Subsurface Defect by Pulsed Thermography

[![Depth of a Subsurface Defect by Pulsed Thermography](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map.png)

*↑ **Depth of a Subsurface Defect by Pulsed Thermography** ―― Surface temperature after a flash, generated from the exact 1-D heat-conduction solution, with delamination depth estimated from the image sequence. Where the diameter is at least four times the depth the estimate lands within a few percent; at 0.5 mm deep and 2 mm across it is off by +627 %. The cause is not lateral diffusion but the fitting window: shortening it from 25 s to 4 s brings that case back to -9 %.*

[![右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table.png)

*↑ The measurement ―― 右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。 (figure labels are in Japanese; the numbers are the same)*

[![早期の勾配は -1/2。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/03_tsr_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/03_tsr_curves.png)

*↑ 早期の勾配は -1/2。*

```
py -3.11 examples/poc_thermography_ndt.py
```

Source: [examples/poc_thermography_ndt.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)

This run produced **3 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_thermography_ndt)



## No.2026.047 —— Veiling Glare Breaks Contrast Measurement — MTF Passes While Black Level Fails

[![Veiling Glare Breaks Contrast Measurement — MTF Passes While Black Level Fails](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/04_glare_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/04_glare_scene.png)

*↑ **Veiling Glare Breaks Contrast Measurement — MTF Passes While Black Level Fails** ―― A PSF whose core stays sharp while only its tail is made heavier, with the slanted-edge MTF and the black level of a dark square measured on the same image. Raising the tail fraction from 0 to 0.20 moves MTF50 from 0.2347 to 0.2249 cyc/px (-4.2 %, still passing) while the black level goes from 0.0 to 15.7 % (failing). A ±16 px measurement window captures only 6 % of the tail's energy; a glare figure means nothing until the measurement extent is declared.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/01_verdict_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/01_verdict.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![D を 16 倍にすると 19.6 % が 4.5 % になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/02_window_dependence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/02_window_dependence.png)

*↑ D を 16 倍にすると 19.6 % が 4.5 % になる。*

[![全 PSF の MTF と正弦チャートの絶対コントラストは 0.80 の台地を見る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/03_mtf_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/03_mtf_curves.png)

*↑ 全 PSF の MTF と正弦チャートの絶対コントラストは 0.80 の台地を見る。*

```
py -3.11 examples/poc_veiling_glare.py
```

Source: [examples/poc_veiling_glare.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_veiling_glare.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_veiling_glare)

Ops used (notes): [`airy_pattern`](https://furuse.work/ops/optics/wave/airy_pattern.html) · [`create_funct_1d_pairs`](https://furuse.work/ops/oned/function/create_funct_1d_pairs.html) · [`derivate_funct_1d`](https://furuse.work/ops/oned/function/derivate_funct_1d.html) · [`get_y_value_funct_1d`](https://furuse.work/ops/oned/function/get_y_value_funct_1d.html) · [`invert_funct_1d`](https://furuse.work/ops/oned/function/invert_funct_1d.html) · [`mtf_diffraction`](https://furuse.work/ops/optics/imaging/mtf_diffraction.html) · [`psf_to_mtf`](https://furuse.work/ops/optics/imaging/psf_to_mtf.html)

## No.2026.114 —— Naming the Damaged Roller from a Period — You Run Out of Evidence Before You Reach the Cliff

[![Naming the Damaged Roller from a Period — You Run Out of Evidence Before You Reach the Cliff](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/01_scene_web_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/01_scene_web.png)

*↑ **Naming the Damaged Roller from a Period — You Run Out of Evidence Before You Reach the Cliff** ―― In roll-to-roll production of film, battery electrode, copper foil and paper, a single scar on a conveying roller prints itself onto the web once per roller circumference. Can the machine-direction spectrum of a defect map recover that circumference and name the culprit against a table of pi*D? Reading the naive spectral maximum names a real but innocent roller: an impulse train has a comb whose harmonics are as tall as the fundamental, so the maximum grabs C/2 = 235.62 mm, and that lands on the cooling roller at 314.16 mm in the table. A circumference that exists nowhere would be caught; one that exists elsewhere in the table passes review. That error stays at 235.9 mm as the miss rate goes from 0 to 50 % — a constant error is not evidence of robustness, it is the same mistake repeated. The fix is fail-closed: take the lowest frequency at which harmonics k=1..3 all stand. The null baseline, the median spacing between detected defects, is right when detection is perfect (-0.03 mm) but at a 40 % miss rate it errs by 472.1 mm and the mean by 813.5 mm, while the comb method holds at 3.2 mm — a missed defect removes amplitude without moving phase. A 25 mm meander, uncorrected, splits one roller's defect line into two across the web (periodic defects remaining in the lane fall from 100 % to 44 %), yet the MD spectrum is bit-for-bit unchanged: meander only breaks methods that cut lanes in the cross direction. Sixty control trials with only healthy rollers give a 1.7 % false-positive rate, and the floor is not zero — the healthy side reaches 3.99 times the band median, above the 2.5 threshold on its own, so what actually holds the line is the demand that every harmonic stand. There are two cliffs. The prediction L_crit = C^2/dC = 14137 mm matches the measured resolution cliff at 14000 mm, a ratio of 0.99. But the detection cliff, the shortest record that still always reports, is 17000 mm — longer. Shortening the record makes you say nothing before it makes you say the wrong roller, so the cliff Rayleigh predicted correctly is never reached. The criterion itself needed repair: at 24 trials a clean 0 % existed, at 120 trials 2 % survives even at the longest record, so 0 % was a small-sample artefact rather than a floor. The most frequent wrong answer, at seven of nine sweep points, is the cooling roller, and 471.24 / 314.16 = 1.500 is exactly 3:2: an integer ratio inside the table gives the comb method a misidentification of its own. The two gaps this PoC found have since been filled: fs.point_spectrum takes a periodogram straight from event positions and carries its own resolution in the return value, and fs.peak_subbin refines a peak below the bin without clamping the shift, since a vertex further than half a sample away means the index was not a maximum at all.*

[![見逃しは位相を飛ばさないので、櫛の山は低くなるだけで動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/02_null_vs_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/02_null_vs_spectrum.png)

*↑ The measurement ―― 見逃しは位相を飛ばさないので、櫛の山は低くなるだけで動かない。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/03_null_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/03_null_table.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/05_meander_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/05_meander_table.png)

*↑ この回の図*

[![縦線が閉形式の予測 C²/ΔC。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/07_cliff_length_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/07_cliff_length.png)

*↑ 縦線が閉形式の予測 C²/ΔC。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/09_cliff_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/09_cliff_table.png)

*↑ この回の図*

```
py -3.11 examples/poc_web_roll_periodicity.py
```

Source: [examples/poc_web_roll_periodicity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_web_roll_periodicity.py)

This run produced **10 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_web_roll_periodicity)

Ops used (notes): [`cepstrum`](https://furuse.work/ops/acoustics/bearing/cepstrum.html) · [`find_peaks`](https://furuse.work/ops/oned/signal/find_peaks.html) · [`local_min_max_funct_1d`](https://furuse.work/ops/oned/function/local_min_max_funct_1d.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`peak_subbin`](https://furuse.work/ops/oned/signal/peak_subbin.html) · [`point_spectrum`](https://furuse.work/ops/oned/signal/point_spectrum.html) · [`smooth_funct_1d_gauss`](https://furuse.work/ops/oned/function/smooth_funct_1d_gauss.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html)

## No.2026.050 —— Weld Bead From a Laser-Triangulation Profile — The Sin of Writing 0 Where Nothing Was Measured

[![Weld Bead From a Laser-Triangulation Profile — The Sin of Writing 0 Where Nothing Was Measured](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/01_laser_images_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/01_laser_images.png)

*↑ **Weld Bead From a Laser-Triangulation Profile — The Sin of Writing 0 Where Nothing Was Measured** ―― The profile h(x) recovered from the row position of a single laser line, with reinforcement height, width and undercut read off it. The centroid beats the null (integer argmax per column) by 9.3x, and with zero noise the log-parabola is exact to machine precision, 12 orders better than a plain parabola; at 1 % noise the two are 0.00272 versus 0.00260 mm, indistinguishable. Five spatter points break all three estimators together to 0.11 mm (40x); what matters is not refinement but which peak you pick.*

[![0 で埋めた線は影の区間で h=0 に張り付き、左のアンダーカットが消えて偽のつま先ができる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/02_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/02_profile.png)

*↑ The measurement ―― 0 で埋めた線は影の区間で h=0 に張り付き、左のアンダーカットが消えて偽のつま先ができる。 (figure labels are in Japanese; the numbers are the same)*

[![真値 0.45 mm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/03_undercut_vs_angle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/03_undercut_vs_angle.png)

*↑ 真値 0.45 mm。*

[![遮蔽が無ければ全部 1 % 以内。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/04_quantities_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/04_quantities.png)

*↑ 遮蔽が無ければ全部 1 % 以内。*

```
py -3.11 examples/poc_weld_bead_profile.py
```

Source: [examples/poc_weld_bead_profile.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_profile.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_weld_bead_profile)

Ops used (notes): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`smooth_funct_1d_mean`](https://furuse.work/ops/oned/function/smooth_funct_1d_mean.html)

## No.2026.115 —— Light-section scanning of a weld bead — resolution and occlusion share one knob

[![Light-section scanning of a weld bead — resolution and occlusion share one knob](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/01_scene.png)

*↑ **Light-section scanning of a weld bead — resolution and occlusion share one knob** ―― A fillet-weld cross-section is built in closed form with convexity, leg lengths, throat and undercut depth varied along the weld line by known functions, then the triangulation angle is swept from 15 to 70 degrees. Height resolution improves as 1/sin(theta) while any face rising steeper than cot(theta) hides in its own shadow, so the far parent plate turns away exactly at the predicted 37.0 degrees and the far undercut starts vanishing earlier, at 20.8-34.5 degrees (the deeper the groove, the sooner). The dangerous parts are that at 28 degrees every cross-section still reports a value while 25 % of the groove span is unmeasured and the depth reads 27 % shallow, and that raising the angle further drops the deepest cross-sections out of the average (true mean drifting 0.260 to 0.047 mm) — a survivorship bias; the optimal angle differs per measurand at 20 / 24 / 36 / 64 degrees.*

[![θ を大きくすると高さの伸び K が増えて分解能は上がる(輝線の起伏が大きくなる)が、左半分の輝線が消えていく。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/02_frames.png)

*↑ The measurement ―― θ を大きくすると高さの伸び K が増えて分解能は上がる(輝線の起伏が大きくなる)が、左半分の輝線が消えていく。 (figure labels are in Japanese; the numbers are the same)*

[![θ = 28 度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/03_profile_28_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/03_profile_28.png)

*↑ θ = 28 度。*

[![下に凸の谷がアンダーカット。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/05_undercut_zoom_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/05_undercut_zoom.png)

*↑ 下に凸の谷がアンダーカット。*

[![同じノブの表裏。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/07_resolution_vs_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/07_resolution_vs_occlusion.png)

*↑ 同じノブの表裏。*

[![脚長は sin²(母材角)、溝深さは cos²(母材角) —— 同じ母材面で足すと 1。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/09_calibration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/09_calibration.png)

*↑ 脚長は sin²(母材角)、溝深さは cos²(母材角) —— 同じ母材面で足すと 1。*

```
py -3.11 examples/poc_weld_bead_scan_angle.py
```

Source: [examples/poc_weld_bead_scan_angle.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_scan_angle.py)

This run produced **11 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_weld_bead_scan_angle)

Ops used (notes): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`intersect_planes`](https://furuse.work/ops/3d/geometry/intersect_planes.html) · [`lines_gauss`](https://furuse.work/ops/2d/contour/lines_gauss.html) · [`normals_from_depth`](https://furuse.work/ops/3d/range_image/normals_from_depth.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html)

## No.2026.090 —— Porosity in Weld Radiographs — Closing With the Share of Images Misgraded by One Class

[![Porosity in Weld Radiographs — Closing With the Share of Images Misgraded by One Class](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph.png)

*↑ **Porosity in Weld Radiographs — Closing With the Share of Images Misgraded by One Class** ―― A radiograph drawn in closed form with Beer–Lambert: 10 mm plate, arc-shaped reinforcement, spherical pores, plus scatter, unsharpness and film grain. The fixed-threshold baseline counts the weld toe as pores (124 blobs, total area 15.19 mm² against 7.93 true). The detection cliff is predictable from CNR = 16.12·d²: Rose's CNR = 4 misses (0.50 mm), while the prediction that includes smoothing and the 3 px minimum area gives 0.58 mm against 0.57 mm measured. The 9 px window cap of the background-estimation op (rectangular opening) becomes a cliff: detection drops below 50 % from 2.0 mm and reaches 0 % at 2.5 mm — choosing the op chooses the measuring range. Scatter at SPR = 1 shrinks the volumetric diameter by (1+SPR)^(-1/3): -22.6 % measured against -20.6 % predicted. Images misgraded by one class: 90 % for the baseline, 23 % with the volumetric diameter.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/02_map_detections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/02_map_detections.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![小さい側の崖は CNR で予測どおり。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/03_detect_vs_diameter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/03_detect_vs_diameter.png)

*↑ 小さい側の崖は CNR で予測どおり。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/04_toe_detection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/04_toe_detection.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/06_frames_scatter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/06_frames_scatter.png)

*↑ この回の図*

[![視認基準 CNR ≥ 3(Rose)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/08_iqi_visibility_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/08_iqi_visibility.png)

*↑ 視認基準 CNR ≥ 3(Rose)。*

```
py -3.11 examples/poc_weld_radiograph_porosity.py
```

Source: [examples/poc_weld_radiograph_porosity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_radiograph_porosity.py)

This run produced **9 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_weld_radiograph_porosity)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`estimate_noise`](https://furuse.work/ops/2d/features/estimate_noise.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`gray_opening_rect`](https://furuse.work/ops/2d/morphology/gray_opening_rect.html) · [`identity`](https://furuse.work/ops/2d/misc/identity.html) · [`log_image`](https://furuse.work/ops/2d/arithmetic/log_image.html) · [`measure_pairs`](https://furuse.work/ops/measure1d/caliper/measure_pairs.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median_rect`](https://furuse.work/ops/2d/rank/median_rect.html) · [`sk_rolling_ball`](https://furuse.work/ops/2d/smoothing/sk_rolling_ball.html) · [`xsitk_grayscale_grindpeak`](https://furuse.work/ops/2d/extra/xsitk_grayscale_grindpeak.html)

## No.2026.122 —— Finding and Fixing Wrong Characters Without Recognising Them — the Threshold Comes from Typeface Spread

[![Finding and Fixing Wrong Characters Without Recognising Them — the Threshold Comes from Typeface Spread](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_glyph_typo_detection/01_sign_before_after_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_glyph_typo_detection/01_sign_before_after.png)

*↑ **Finding and Fixing Wrong Characters Without Recognising Them — the Threshold Comes from Typeface Spread** ―― Because the intended string is given as input, no 6000-way classification is needed: each cell is compared against one specified character. The threshold is not guessed but derived from the 95th percentile of the distance between the same character in different typefaces (0.058). The distance is the 99th percentile rather than the mean — a substitution usually keeps one radical and swaps the rest, so the mean sinks the 検/横 pair to 0.0171, below the typeface floor, making it undetectable in principle. On a synthetic sign all four planted errors are found with no false alarms, and after replacement the distance drops from 0.0805 to 0.0258, below the floor for all four.*

[![床を超えたマスが誤字。壊した位置は 2, 3, 5, 7。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_glyph_typo_detection/02_cell_distance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_glyph_typo_detection/02_cell_distance.png)

*↑ The measurement ―― 床を超えたマスが誤字。壊した位置は 2, 3, 5, 7。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_glyph_typo_detection.py
```

Source: [examples/poc_glyph_typo_detection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_glyph_typo_detection.py)

This run produced **2 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_glyph_typo_detection)



## No.2026.130 —— Print Layer Inspection — Closing the Shape → Layer → Path → Image Loop and Catching Planted Defects by the Numbers

[![Print Layer Inspection — Closing the Shape → Layer → Path → Image Loop and Catching Planted Defects by the Numbers](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/02_layers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/02_layers.png)

*↑ **Print Layer Inspection — Closing the Shape → Layer → Path → Image Loop and Catching Planted Defects by the Numbers** ―― 3D-printer data flows shape (mesh) → layers (slices) → path (G-code) → the layer images taken during printing. The new family printpath (11 ops, numpy + stdlib, no new types) closes that loop with the existing vocabulary (mesh / voxel / table / image2d), so the truth can be planted by hand. A box with a square hole and a gear-like boss with a round hole sliced at 0.2 mm give layer-mask areas matching the closed form (184.00 mm² exactly and within 0.07 %), a layer where only the hole remains is empty (contours oriented by the triangle normals, nonzero winding), the extrusion of a path that walks the contours equals perimeter × width × height / filament area exactly, G-code round-trips through write and read (relative coordinates, relative E, retracts, G92 and inches are honoured; arcs and missing coordinates are refused), and 3MF round-trips too. Inspection: six gaps and six blobs (1–4 mm) planted into the expected layer raster (gcode_layer_image) are caught by print_layer_defect_map with sign, recall 0.959 and zero false positives at a 3 px (0.3 mm) tolerance; a 0.2 mm camera shift drops recall to 0.895 and precision to 0.946 because the tolerance eats the defect edges — the curve over tolerance is shown as it is.*

[![gear-like boss with a round hole sliced at 0.2 mm into 30 layer masks (mesh_slice_stack) and rendered as a solid, grey =](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/01_slice_stack_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/01_slice_stack.png)

*↑ The measurement ―― gear-like boss with a round hole sliced at 0.2 mm into 30 layer masks (mesh_slice_stack) and rendered as a solid, grey = height (figure labels are in Japanese; the numbers are the same)*

[![precision and recall of the defect map against the injected truth as the tolerance grows, without an](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/03_tolerance_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/03_tolerance_curve.png)

*↑ precision and recall of the defect map against the injected truth as the tolerance grows, without and with a 0.2 mm camera shift: a small tolerance ab…*

[![every number with the bar it had to clear](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/04_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/04_numbers.png)

*↑ every number with the bar it had to clear*

```
py -3.11 examples/poc_print_layer_inspection.py
```

Source: [examples/poc_print_layer_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_layer_inspection.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_print_layer_inspection)

Ops used (notes): [`contours_to_gcode`](https://furuse.work/ops/printpath/slice/contours_to_gcode.html) · [`gcode_extrusion_volume`](https://furuse.work/ops/printpath/gcode/gcode_extrusion_volume.html) · [`gcode_layer_image`](https://furuse.work/ops/printpath/gcode/gcode_layer_image.html) · [`gcode_read`](https://furuse.work/ops/printpath/gcode/gcode_read.html) · [`gcode_time_estimate`](https://furuse.work/ops/printpath/gcode/gcode_time_estimate.html) · [`gcode_write`](https://furuse.work/ops/printpath/gcode/gcode_write.html) · [`mesh_slice_contours`](https://furuse.work/ops/printpath/slice/mesh_slice_contours.html) · [`mesh_slice_stack`](https://furuse.work/ops/printpath/slice/mesh_slice_stack.html) · [`print_layer_defect_map`](https://furuse.work/ops/printpath/inspect/print_layer_defect_map.html) · [`read_3mf`](https://furuse.work/ops/printpath/format/read_3mf.html) · [`vol_render_transfer`](https://furuse.work/ops/videocube/render/vol_render_transfer.html) · [`write_3mf`](https://furuse.work/ops/printpath/format/write_3mf.html)

### The Dimensional and Shape Metrology Wing — Keep Bias and Scatter Apart

To state that a part is 50.50 pixels wide, you need bias (the part that always shifts the same way) and scatter (the part that changes from shot to shot) as two separate numbers. Pass/fail is decided by bias; repeatability by scatter. Merge them into one 'error' and you no longer know which countermeasure to take.

The ten exhibits here hold their ground truth in closed form or analytic rendering — a signed-distance-function part, an involute gear, a roughness surface synthesised from a prescribed PSD, a white-light interferometry stack, analytic speckle, Frocht's stress field, a perfectly symmetric synthetic skull — and then score caliper, correlation and phase readings against it.

The recurring finding is that a number without its definition cannot be compared: crack widths that differ by 0.20 mm between two distance-transform conventions, a D50 that differs by 1.66x between number- and area-weighting, an Sz that never plateaus as the evaluation area grows, an orientation index that moves 5 % depending on whether the truth is counted by fibre or by length. These are not instrument errors; they are questions of what you are comparing against.

## No.2026.120 —— Matching Full 2-D Inspection to Sampled 3-D Inspection — A Grid Overlaps Itself

[![Matching Full 2-D Inspection to Sampled 3-D Inspection — A Grid Overlaps Itself](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct.png)

*↑ **Matching Full 2-D Inspection to Sampled 3-D Inspection — A Grid Overlaps Itself** ―― The real line has two stages: AOI images every unit from above, X-ray CT samples a few and images the inside. What the floor wants to know is how far the CT numbers follow from the AOI numbers — which is not a question about one instrument's accuracy but about whether two instruments' indices point at the same joint. A regular array does not match one-to-one on point positions alone: all 30 pads of a 6x5 grid have degenerate distance signatures (9 distinct ones), because the grid maps onto itself and the orientation cannot be read. Fiducials with three distinct side lengths (3600/5200/6325 um) pin rotation and reflection uniquely, and the correspondence is recovered exactly under translation, rotation and re-indexing. With that closed, AOI's apparent void fraction correlates 0.973 with CT volume fraction and the worst five agree 5/5 — yet of the 27 parts carrying an interface-touching void (the kind that shortens life), those five catch only 19 %. Agreeing on the ranking does not mean catching the dangerous ones. The failed first attempt (Kabsch alone) is kept.*

[![直線は「面積率に比例する」という素朴な仮定。点はそこから両側へ離れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/02_area_vs_volume_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/02_area_vs_volume.png)

*↑ The measurement ―― 直線は「面積率に比例する」という素朴な仮定。点はそこから両側へ離れる。 (figure labels are in Japanese; the numbers are the same)*

[![AOI の面積率が大きい接合部が、界面に接するボイドを持つとは限らない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/03_interface_voids_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/03_interface_voids.png)

*↑ AOI の面積率が大きい接合部が、界面に接するボイドを持つとは限らない。*

[![同じロットを同じ「悪い順」で並べても、順位は一致しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/04_worst_first_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/04_worst_first.png)

*↑ 同じロットを同じ「悪い順」で並べても、順位は一致しない。*

```
py -3.11 examples/poc_aoi_ct_traceability.py
```

Source: [examples/poc_aoi_ct_traceability.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_aoi_ct_traceability.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_aoi_ct_traceability)

Ops used (notes): [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html)

## No.2026.091 —— As-built wall deviation — the bounding box measures the room's heading, not its size

[![As-built wall deviation — the bounding box measures the room's heading, not its size](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/01_scene.png)

*↑ **As-built wall deviation — the bounding box measures the room's heading, not its size** ―― A 6.0 x 4.0 x 2.7 m indoor point cloud carries known defects: wall plumb errors of 1.20-9.00 mrad, a 5.00 mrad plan-view squareness error, and a 9 mm out-of-plane bulge. The naive axis-aligned bounding box over-reports the width by 19.1 mm, and rotating the room by just 1 deg relative to the scanner axes adds 80.1 mm (611.1 mm at 10 deg) — it is measuring W cos psi + D sin psi, the room's heading, while the plane-pair distance stays at +2.24 mm regardless. The AABB also grows with sample size (+14.9 to +19.7 mm for 256x more points, the 2-sigma-sqrt(2 ln N) extreme-value law), so adding measurements makes it worse. Furniture outliers break the two estimators differently: least squares is off by 11x the truth at 10 % contamination (66.3 mrad vs a closed-form 63.8), while RANSAC holds to 45 % and then jumps onto the cabinet at 55 % — where the plumb error stays a harmless 0.13 mrad but the plane itself is 449.9 mm out, so one number hides the failure. A single bulge corrupts plumb (-1.258 mrad), squareness (+0.500 mrad) and the internal dimension (+2.2 mm) at once, all predicted in closed form to within 0.06 mrad.*

[![許容 ±10 mm。AABB は ψ=0.5 度で既に外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/02_aabb_vs_yaw_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/02_aabb_vs_yaw.png)

*↑ The measurement ―― 許容 ±10 mm。AABB は ψ=0.5 度で既に外れる。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/03_aabb_grows_with_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/03_aabb_grows_with_points.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/05_squareness_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/05_squareness.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/08_outlier_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/08_outlier_maps.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/10_bulge_fake_tilt_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/10_bulge_fake_tilt.png)

*↑ この回の図*

```
py -3.11 examples/poc_asbuilt_wall_deviation.py
```

Source: [examples/poc_asbuilt_wall_deviation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_asbuilt_wall_deviation.py)

This run produced **12 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation)

Ops used (notes): [`aabb`](https://furuse.work/ops/3d/bounds/aabb.html) · [`angle_between_planes`](https://furuse.work/ops/3d/geometry/angle_between_planes.html) · [`angle_line_plane`](https://furuse.work/ops/3d/geometry/angle_line_plane.html) · [`distance_point_plane`](https://furuse.work/ops/3d/geometry/distance_point_plane.html) · [`fit_plane3`](https://furuse.work/ops/3d/geometry/fit_plane3.html) · [`ransac_plane`](https://furuse.work/ops/3d/robust_fit/ransac_plane.html)

## No.2026.092 —— Measuring electrode breathing in microns — sub-pixel is not enough

[![Measuring electrode breathing in microns — sub-pixel is not enough](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/01_scene.png)

*↑ **Measuring electrode breathing in microns — sub-pixel is not enough** ―― Electrode swelling is read from two cross-sections by tracking layer boundaries to sub-pixel accuracy. Ground truth: anode 1.00 %, cathode 0.20 %, separator 0 %, stack 480.0 -> 482.136 um (+2.136 um = +0.4450 %). Counting binarised pixels resolves 0 of 12 layers, while a fixed-threshold crossing is also sub-pixel and lands on the answer with no noise (+0.004495) — what kills it is the control group: with zero strain, an illumination offset of +0.10 alone yields -1.07e-02, a false strain 2.4x the true one and of the opposite sign, and a gain of x1.30 halves the crossings so the measurement fails outright. The gradient-peak estimator (measure_pos) stays at exactly 0.0 under both. Doubting our own '1.8e-14 px error' and shifting the stack by fractions of a pixel showed that figure to be an artefact of putting the truth on pixel centres: the real error is peak locking, RMS 0.0088 / max 0.0122 px, worth 3.0 % on the anode's strain. The cliff has two steps, and the one where boundary counts collapse arrives 5.5x earlier than the predicted 3-sigma limit.*

[![境界は erf の重ね合わせで解析的に置いてあるので、真値は浮動小数点の精度で既知。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/02_profiles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/02_profiles.png)

*↑ The measurement ―― 境界は erf の重ね合わせで解析的に置いてあるので、真値は浮動小数点の精度で既知。 (figure labels are in Japanese; the numbers are the same)*

[![階段状に増えるのは、伸びる層(負極 1.00 %)と伸びない層(セパレータ 0 %)が交互だから。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/03_displacement_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/03_displacement.png)

*↑ 階段状に増えるのは、伸びる層(負極 1.00 %)と伸びない層(セパレータ 0 %)が交互だから。*

[![真値を画素の中心に置いた検査は、推定器を実力以上に良く見せる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/04_peak_locking_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/04_peak_locking.png)

*↑ 真値を画素の中心に置いた検査は、推定器を実力以上に良く見せる。*

[![横線は真値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/06_noise_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/06_noise_scaling.png)

*↑ 横線は真値。*

[![実測が予測から離れる左端は、雑音が増えたのではなく**境界を数え損ねている**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/08_contrast_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/08_contrast_cliff.png)

*↑ 実測が予測から離れる左端は、雑音が増えたのではなく**境界を数え損ねている**。*

```
py -3.11 examples/poc_battery_electrode_breathing.py
```

Source: [examples/poc_battery_electrode_breathing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_breathing.py)

This run produced **9 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_battery_electrode_breathing)

Ops used (notes): [`auto_threshold`](https://furuse.work/ops/2d/segmentation/auto_threshold.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`piv_peak_locking`](https://furuse.work/ops/piv/assess/piv_peak_locking.html)

## No.2026.005 —— Measuring Bilateral Asymmetry — The Symmetry Plane Gets Dragged by the Deformation

[![Measuring Bilateral Asymmetry — The Symmetry Plane Gets Dragged by the Deformation](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/03_deviation_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/03_deviation_map.png)

*↑ **Measuring Bilateral Asymmetry — The Symmetry Plane Gets Dragged by the Deformation** ―― A perfectly symmetric synthetic skull with a known bulge added on one side, mirrored and overlaid. Even a perfectly symmetric specimen never scores 0: the floor drops from 1.33 mm (point-to-point) to 0.030 mm (point-to-plane) to 0.012 mm (neighbourhood smoothing). The residual-minimising plane is dragged 2.92 mm / 1.72 degrees by a 6.33 mm bulge, and 46 % of the asymmetry disappears.*

[![完全対称な標本を測った残差。点対点は点間隔がそのまま床になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing.png)

*↑ The measurement ―― 完全対称な標本を測った残差。点対点は点間隔がそのまま床になる。 (figure labels are in Japanese; the numbers are the same)*

[![真値の線は利得 1.0。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/02_gain_vs_amplitude_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/02_gain_vs_amplitude.png)

*↑ 真値の線は利得 1.0。*

[![margin < 0.1 で採用を止めれば、66〜88 度の外しは弾ける。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/04_degenerate_margin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/04_degenerate_margin.png)

*↑ margin < 0.1 で採用を止めれば、66〜88 度の外しは弾ける。*

```
py -3.11 examples/poc_bilateral_asymmetry.py
```

Source: [examples/poc_bilateral_asymmetry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bilateral_asymmetry.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_bilateral_asymmetry)

Ops used (notes): [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`detect_reflection_symmetry`](https://furuse.work/ops/3d/symmetry/detect_reflection_symmetry.html) · [`detect_rotational_symmetry`](https://furuse.work/ops/3d/symmetry/detect_rotational_symmetry.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`reflect_points`](https://furuse.work/ops/3d/symmetry/reflect_points.html) · [`reflection_symmetry_score`](https://furuse.work/ops/3d/symmetry/reflection_symmetry_score.html) · [`sample_surface`](https://furuse.work/ops/3d/superquadric/sample_surface.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html)

## No.2026.013 —— Strain From Speckle Images (DIC)

[![Strain From Speckle Images (DIC)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/04_strain_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/04_strain_map.png)

*↑ **Strain From Speckle Images (DIC)** ―― Displacement and strain read from a speckle pair in which 3000 Gaussian spots were moved by the deformation map and redrawn, not interpolated. For a true shift of 0.37 px the window-correlation estimator (piv) is biased by 0.0002 px with 0.0022 px scatter, 167x better than the null that answers 'no motion'. A rigid rotation manufactures several hundred µε of false strain under the small-strain definition; Green-Lagrange gives exactly 0.*

[![変形は補間ではなく斑点の再描画。だから真値が厳密。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/01_speckle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/01_speckle.png)

*↑ The measurement ―― 変形は補間ではなく斑点の再描画。だから真値が厳密。 (figure labels are in Japanese; the numbers are the same)*

[![lk は 0.5 px 側へ寄る(教科書の peak locking と逆)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/02_subpixel_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/02_subpixel_bias.png)

*↑ lk は 0.5 px 側へ寄る(教科書の peak locking と逆)。*

[![窓を広げると尖頭が下がり幅が広がる(空間分解能の限界)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/03_strain_concentration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/03_strain_concentration.png)

*↑ 窓を広げると尖頭が下がり幅が広がる(空間分解能の限界)。*

```
py -3.11 examples/poc_dic_strain.py
```

Source: [examples/poc_dic_strain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dic_strain)

Ops used (notes): [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`strain_from_displacement`](https://furuse.work/ops/piv/solid/strain_from_displacement.html)

## No.2026.097 —— Die tilt and TSV overlay from one CT — tilt fakes rotation too

[![Die tilt and TSV overlay from one CT — tilt fakes rotation too](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene.png)

*↑ **Die tilt and TSV overlay from one CT — tilt fakes rotation too** ―― Two stacked dies carry a 7x7 TSV lattice with a planted overlay of (+0.800, -0.450) um, +0.01500 deg of rotation and a die tilt of (1.20, 0.70) deg; a single CT volume is the whole measurement. Comparing the top-surface via openings directly misses by 2.419 um — 2.4x the +-1.0 um spec, and larger than the 0.918 um real overlay. The bias matches the closed form 'die thickness x lateral part of the top-surface normal' to a ratio of 0.996 / 0.999, and re-projecting each via down its own fitted axis recovers the truth to 0.0023 um. The prediction that failed: tilt fakes rotation as well as translation, through the sin(alpha)sin(beta) shear of Rx Ry — predicted +0.00733 deg against +0.00696 deg measured as the difference from the zero-tilt control. Axis correction does not remove it; only de-projecting with the measured tilt does. The cliff lands at 0.492 deg measured against 0.491 deg predicted.*

[![雲ごと 2.42 µm ずれるのが傾きの偽装。散らばりの広がりは測定精度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/02_overlay_scatter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/02_overlay_scatter.png)

*↑ The measurement ―― 雲ごと 2.42 µm ずれるのが傾きの偽装。散らばりの広がりは測定精度。 (figure labels are in Japanese; the numbers are the same)*

[![偽の回転の予測 +0.00733°、倍率の予測 -147.0 ppm(対照群との差で実測 +0.00696° / -144.5 ppm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/03_estimator_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/03_estimator_table.png)

*↑ 偽の回転の予測 +0.00733°、倍率の予測 -147.0 ppm(対照群との差で実測 +0.00696° / -144.5 ppm)。*

[![ゼロ点(青)と予測(赤)は重なっている —— 誤差はダイ厚 x |法線の横成分| そのもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/04_tilt_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/04_tilt_cliff.png)

*↑ ゼロ点(青)と予測(赤)は重なっている —— 誤差はダイ厚 x |法線の横成分| そのもの。*

[![真の回転 0.01500° を超えるのは α ≈ 1.2°。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/05_rotation_vs_tilt_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/05_rotation_vs_tilt.png)

*↑ 真の回転 0.01500° を超えるのは α ≈ 1.2°。*

```
py -3.11 examples/poc_die_tilt_tsv_overlay.py
```

Source: [examples/poc_die_tilt_tsv_overlay.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_die_tilt_tsv_overlay.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay)

Ops used (notes): [`fit_line3`](https://furuse.work/ops/3d/geometry/fit_line3.html) · [`procrustes_fit`](https://furuse.work/ops/shapestat/procrustes/procrustes_fit.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html)

## No.2026.014 —— Dimensional Inspection of a Machined Part — Bias and Scatter as Two Numbers

[![Dimensional Inspection of a Machined Part — Bias and Scatter as Two Numbers](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/01_slot_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/01_slot_bias.png)

*↑ **Dimensional Inspection of a Machined Part — Bias and Scatter as Two Numbers** ―― A part defined by a signed distance function (slot width 50.50 px, 1 px = 12.5 µm), imaged through a known PSF and noise and measured by four caliper systems. Otsu's integer width (the null) has an RMS error of 0.464 px = 5.8 µm; the buried 1-D measuring implementation is biased by -0.0113 px = -0.14 µm, 41x better. Once the edge spacing drops below 3.09 PSF widths the width comes out systematically large, and the API keeps returning success.*

[![偏りはどちらも正(対が互いを押し広げる)。符号が一定なので繰り返し測っても消えない。下端 -4 は表示の打ち切り(|偏り| < 1e-4 px)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/02_blur_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/02_blur_cliff.png)

*↑ The measurement ―― 偏りはどちらも正(対が互いを押し広げる)。符号が一定なので繰り返し測っても消えない。下端 -4 は表示の打ち切り(|偏り| < 1e-4 px)。 (figure labels are in Japanese; the numbers are the same)*

[![偏りは SNR 140 まで動かず、増えるのは散らばりだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/03_noise_bias_spread_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/03_noise_bias_spread.png)

*↑ 偏りは SNR 140 まで動かず、増えるのは散らばりだけ。*

[![3 本の縦線は 16.0 px = 200 um 離れている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/04_edge_definition_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/04_edge_definition.png)

*↑ 3 本の縦線は 16.0 px = 200 um 離れている。*

```
py -3.11 examples/poc_dimensional_inspection.py
```

Source: [examples/poc_dimensional_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dimensional_inspection.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dimensional_inspection)

Ops used (notes): [`add_metrology_object_circle_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_circle_measure.html) · [`add_metrology_object_ellipse_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_ellipse_measure.html) · [`add_metrology_object_generic`](https://furuse.work/ops/measure1d/model/add_metrology_object_generic.html) · [`add_metrology_object_line_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_line_measure.html) · [`add_metrology_object_rectangle2_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_rectangle2_measure.html) · [`align_metrology_model`](https://furuse.work/ops/measure1d/apply/align_metrology_model.html) · [`apply_metrology_model`](https://furuse.work/ops/measure1d/apply/apply_metrology_model.html) · [`create_metrology_model`](https://furuse.work/ops/measure1d/model/create_metrology_model.html) · [`edge_points`](https://furuse.work/ops/3d/edges/edge_points.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`fuzzy_measure_pairing`](https://furuse.work/ops/measure1d/caliper/fuzzy_measure_pairing.html) · [`gen_measure_arc`](https://furuse.work/ops/measure1d/caliper/gen_measure_arc.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`m1_measure_pairs`](https://furuse.work/ops/2d/measure1d/m1_measure_pairs.html) · [`m1_measure_pos`](https://furuse.work/ops/2d/measure1d/m1_measure_pos.html) · [`measure_pairs`](https://furuse.work/ops/measure1d/caliper/measure_pairs.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`translate_measure`](https://furuse.work/ops/measure1d/caliper/translate_measure.html)

## No.2026.018 —— Fibre Orientation Distribution — Angles Repeat Every 180 Degrees, and a Naive Mean Is 90 Degrees Off

[![Fibre Orientation Distribution — Angles Repeat Every 180 Degrees, and a Naive Mean Is 90 Degrees Off](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/01_scene.png)

*↑ **Fibre Orientation Distribution — Angles Repeat Every 180 Degrees, and a Naive Mean Is 90 Degrees Off** ―― Orientation of 140 fibres drawn from a von Mises distribution, read with a structure tensor. For a true mean of 177.9 degrees the arithmetic mean reports 105.55 degrees (-72.33), while the doubled-angle circular mean is off by +0.17 degrees — with not one bit of the image or the measurement changed. Weighting every pixel equally drops the orientation index by -31.3 %.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/02_wrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/02_wrap.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/03_field_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/03_field.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/04_histogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/04_histogram.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/05_density_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/05_density.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/06_scales_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/06_scales.png)

*↑ この回の図*

```
py -3.11 examples/poc_fiber_orientation.py
```

Source: [examples/poc_fiber_orientation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fiber_orientation.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fiber_orientation)

Ops used (notes): [`coherence`](https://furuse.work/ops/acoustics/dual/coherence.html) · [`dc_structure_texture`](https://furuse.work/ops/2d/decomposition/dc_structure_texture.html) · [`moment_axes`](https://furuse.work/ops/3d/match_pose/moment_axes.html) · [`principal_moments`](https://furuse.work/ops/3d/moment_invariant/principal_moments.html) · [`smooth_funct_1d_gauss`](https://furuse.work/ops/oned/function/smooth_funct_1d_gauss.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`sobel_dir`](https://furuse.work/ops/2d/edges/sobel_dir.html)

## No.2026.021 —— Gear Tooth Metrology — Eccentricity Is Order 1, Teeth Are Order z

[![Gear Tooth Metrology — Eccentricity Is Order 1, Teeth Are Order z](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/01_scene.png)

*↑ **Gear Tooth Metrology — Eccentricity Is Order 1, Teeth Are Order z** ―― Eccentricity and tooth profile read from a gear drawn with the closed-form involute. The null's least-squares circle has a diameter of 47.278 mm, which is neither the pitch (48), tip (52) nor root (43) circle. One missing tooth turns an eccentricity of 0.050 mm into 0.1285 mm (+157 %); the traditional method of one sample per tooth returns 0.0501 mm (+0.2 %).*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/02_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/02_profile.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![歯の次数 24/48/72 は 2.6 mm あるので 0.35 mm で切った](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/03_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/03_spectrum.png)

*↑ 歯の次数 24/48/72 は 2.6 mm あるので 0.35 mm で切った*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/04_missing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/04_missing.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/05_illumination_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/05_illumination.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/06_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/06_summary.png)

*↑ この回の図*

```
py -3.11 examples/poc_gear_tooth_metrology.py
```

Source: [examples/poc_gear_tooth_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gear_tooth_metrology.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_gear_tooth_metrology)

Ops used (notes): [`blob_boundaries`](https://furuse.work/ops/blob/extract/blob_boundaries.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_region`](https://furuse.work/ops/blob/extract/blob_region.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`polar_trans_image`](https://furuse.work/ops/2d/geometry/polar_trans_image.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.022 —— How Accurately a White-Light Interferometer Measures a Nanometre Step

[![How Accurately a White-Light Interferometer Measures a Nanometre Step](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram.png)

*↑ **How Accurately a White-Light Interferometer Measures a Nanometre Step** ―― A synthesised coherence-scanning stack with steps of 50 to 500 nm measured back. At 1 % noise the bias stays within 2.4 nm and the standard deviation within 14.1 nm, almost independent of step height. The null (envelope's maximum sample) errs by exactly half the scan step, and at 0.14 µm, just inside the Nyquist ceiling of 0.15 µm, the noise-free error is already +14.1 nm.*

[![0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep.png)

*↑ The measurement ―― 0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。 (figure labels are in Japanese; the numbers are the same)*

[![centroid は散らばりが gaussian の 1/3〜1/5 なのに総合誤差では上に来る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/03_noise_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/03_noise_sweep.png)

*↑ centroid は散らばりが gaussian の 1/3〜1/5 なのに総合誤差では上に来る。*

[![4 種の段差でゲインが揃う = オフセットではなく倍率の誤差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/04_centroid_gain_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/04_centroid_gain.png)

*↑ 4 種の段差でゲインが揃う = オフセットではなく倍率の誤差。*

```
py -3.11 examples/poc_interferometry_step.py
```

Source: [examples/poc_interferometry_step.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_interferometry_step)

Ops used (notes): [`csi_design`](https://furuse.work/ops/interferometry/design/csi_design.html) · [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`csi_stack_simulate`](https://furuse.work/ops/interferometry/simulate/csi_stack_simulate.html) · [`decode_fringe`](https://furuse.work/ops/3d/structured_light/decode_fringe.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`synthesize_fringes`](https://furuse.work/ops/3d/structured_light/synthesize_fringes.html)

## No.2026.073 —— Metallographic Grain Size — The Planimetric and Intercept Methods Fall Off Different Cliffs

[![Metallographic Grain Size — The Planimetric and Intercept Methods Fall Off Different Cliffs](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/01_scene.png)

*↑ **Metallographic Grain Size — The Planimetric and Intercept Methods Fall Off Different Cliffs** ―― Grains are synthesized as a 2-D Voronoi tessellation with 2-px boundaries, then etching unevenness, noise and boundary gaps are added; ASTM E112 grain size G is measured by the planimetric method (Otsu + connected components) and the lineal-intercept method (local threshold + test lines in 4 directions). The planimetric method survives noise alone (-0.02) and etching unevenness alone (-0.40) but dies under both (+3.82), and loses one G step at 7.2 % boundary gaps; the intercept method holds to 40.7 % — the predicted 29.3 % was wrong because only 0.76 f of the boundary actually disappears in the mask. A duplex structure gives a whole-field G of 7.82 that matches neither the fine (9.01) nor the coarse (6.15) population; only 4 of 64 tiles fall within ±0.5 of it.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/02_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/02_controls.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/03_stages_intercept_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/03_stages_intercept.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/04_stages_area_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/04_stages_area.png)

*↑ この回の図*

[![融合した塊の数は f = 5 % を頂点に減る(塊どうしがさらに融合して 1 つになる)が、飲まれた粒の数は増え続ける。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/06_failure_area_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/06_failure_area.png)

*↑ 融合した塊の数は f = 5 % を頂点に減る(塊どうしがさらに融合して 1 つになる)が、飲まれた粒の数は増え続ける。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/08_intercept_cdf_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/08_intercept_cdf.png)

*↑ この回の図*

```
py -3.11 examples/poc_metal_grain_size.py
```

Source: [examples/poc_metal_grain_size.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_metal_grain_size.py)

This run produced **9 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_metal_grain_size)

Ops used (notes): [`bin_threshold`](https://furuse.work/ops/2d/segmentation/bin_threshold.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`bothat`](https://furuse.work/ops/2d/morphology/bothat.html) · [`dyn_threshold`](https://furuse.work/ops/2d/segmentation/dyn_threshold.html) · [`gray_bothat`](https://furuse.work/ops/2d/morphology/gray_bothat.html) · [`hx_close_edges`](https://furuse.work/ops/2d/halcon_ext/hx_close_edges.html) · [`invert_image`](https://furuse.work/ops/2d/gray/invert_image.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.100 —— Why the Seafloor Smiles — A Wrong Sound-Speed Profile Breaks Only the Outer Beams

[![Why the Seafloor Smiles — A Wrong Sound-Speed Profile Breaks Only the Outer Beams](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/12_across_track_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/12_across_track.png)

*↑ **Why the Seafloor Smiles — A Wrong Sound-Speed Profile Breaks Only the Outer Beams** ―― Multibeam echosounding: get the water-column sound-speed profile wrong and a flat seafloor curls up (the classic smile / frown). Only the outer beams break — nadir is almost untouched, which is exactly the part the field checks with a bar check. The ground truth is planted here: a perfectly horizontal bottom at 50.0 m, sound speed 1520 to 1480 m/s (gradient -0.800 /s), 141 beams over +/-70 degrees, and the verdict comes from a real standard, IHO S-44 Order 1a (TVU at 50 m = 0.8201 m). The cliff was predicted twice before measuring: a rough expansion, dz = (g D^2 / 2 c0) tan^2(theta), gives 48.15 degrees, and the exact closed form (rays are circular arcs inside a constant-gradient layer) gives 48.68. The measurement with echo detection disabled lands on 48.68 — the exact form is right to 2.0e-11 m, while the expansion misses by 0.53 degrees (within 3.0 % out to 45 degrees, 19.4 % high at 70). One prediction was wrong: echo detection was expected to be a negligible floor, but the full-chain cliff is 47.95 degrees, 0.73 degrees earlier. At 70 degrees the illuminated strip stretches the echo to 21396 us (171 times the nadir value) and skews it, pulling the amplitude peak 0.725 m shallow — which is why real systems switch to phase detection on the outer beams. Controls separate the culprit: refraction alone is -2.6974 m, angle estimation contributes 0.000000 m and echo detection -0.2221 m. The textbook footprint formula is only 34 % of the truth at 70 degrees (cos^2 gives 8.21 m against a measured 24.14 m) because a steered array widens its beam as 1/cos(theta), so the correct exponent is three (cos^3 is off by -0.6 %). Discretisation alone can breach the standard: treating each cast layer as iso-velocity puts +1.2994 m on a 65-degree beam with two layers, converging first order to +0.0785 m with 32. The only check available without truth is the overlap between adjacent lines: 2.697 m of disagreement at the edge (3.3 times TVU) but exactly 0.0000 m in the middle of the overlap, where both lines use the same beam angle and the errors cancel — so it is invisible unless the full swath edge is compared. With upward refraction the outer beams never reach bottom: nothing is recorded rather than recorded wrongly (critical angle predicted at 73.90 degrees, bracketed by the last beam that arrives at 73.0 and the first that does not at 74.0). Across a 200-case grid of 25 sound-speed differences and 8 depths, 78.0 % of +/-65-degree swaths fail Order 1a at the edge. Finally, a one-way documentation hole was closed on the way: the vector-form refract only told callers to loop one ray at a time, never mentioning that refract_rays already returns a per-ray TIR mask.*

[![エコーは beamform_delay_sum の角度応答 × Lambert 後方散乱で海底の帯を足し上げて合成。find_peaks + peak_subbin で検出。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/01_floor_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/01_floor.png)

*↑ The measurement ―― エコーは beamform_delay_sum の角度応答 × Lambert 後方散乱で海底の帯を足し上げて合成。find_peaks + peak_subbin で検出。 (figure labels are in Japanese; the numbers are the same)*

[![長さは 125 / 2271 / 21396 µs(170 倍の開き)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/02_echo_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/02_echo.png)

*↑ 長さは 125 / 2271 / 21396 µs(170 倍の開き)。*

[![勾配ゼロ + 真の平均音速がゼロ点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/05_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/05_controls.png)

*↑ 勾配ゼロ + 真の平均音速がゼロ点。*

[![beamform_delay_sum の角度スペクトルの -3 dB 幅。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/09_beamwidth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/09_beamwidth.png)

*↑ beamform_delay_sum の角度スペクトルの -3 dB 幅。*

[![2 点キャスト(表層と海底だけ)の一定勾配当てはめ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/13_thermocline_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/13_thermocline.png)

*↑ 2 点キャスト(表層と海底だけ)の一定勾配当てはめ。*

```
py -3.11 examples/poc_multibeam_bathymetry.py
```

Source: [examples/poc_multibeam_bathymetry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_multibeam_bathymetry.py)

This run produced **16 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_multibeam_bathymetry)

Ops used (notes): [`beamform_delay_sum`](https://furuse.work/ops/rangedoppler/beamform/beamform_delay_sum.html) · [`beamform_doa`](https://furuse.work/ops/rangedoppler/beamform/beamform_doa.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`find_peaks`](https://furuse.work/ops/oned/signal/find_peaks.html) · [`interp_scattered`](https://furuse.work/ops/math/interp_poly/interp_scattered.html) · [`peak_subbin`](https://furuse.work/ops/oned/signal/peak_subbin.html) · [`snell_angle`](https://furuse.work/ops/3d/optics/snell_angle.html)

## No.2026.029 —— Particle Size Distribution From Images — Merging and Edge Cuts Pull Opposite Ways and Cancel

[![Particle Size Distribution From Images — Merging and Edge Cuts Pull Opposite Ways and Cancel](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/01_scene.png)

*↑ **Particle Size Distribution From Images — Merging and Edge Cuts Pull Opposite Ways and Cancel** ―― D10 / D50 / D90 from a synthetic scatter of particles, with merges (pulling large) and edge cuts (pulling small) counted separately. At an area fraction of 13.8 % the D50 error is +0.55 % — because 28 merges and 19 edge cuts happen to balance. Number- and area-weighting give D50 values of 26.9 and 44.7 µm (1.66x) from the same blobs.*

[![薄いところで 0 なのは正確だから。濃いところで 0 をまたぐのは融合と縁切れが釣り合っただけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/02_density_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/02_density_sweep.png)

*↑ The measurement ―― 薄いところで 0 なのは正確だから。濃いところで 0 をまたぐのは融合と縁切れが釣り合っただけ。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/03_failure_counts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/03_failure_counts.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/04_merge_separability_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/04_merge_separability.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/05_merge_filter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/05_merge_filter.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/06_edge_rules_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/06_edge_rules.png)

*↑ この回の図*

```
py -3.11 examples/poc_particle_sizing.py
```

Source: [examples/poc_particle_sizing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_sizing.py)

This run produced **7 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_particle_sizing)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_region`](https://furuse.work/ops/blob/extract/blob_region.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html)

## No.2026.031 —— Stress by Photoelasticity — Unwrapping Fails First at the Isotropic Point

[![Stress by Photoelasticity — Unwrapping Fails First at the Isotropic Point](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/01_polariscope_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/01_polariscope.png)

*↑ **Stress by Photoelasticity — Unwrapping Fails First at the Isotropic Point** ―― The closed-form stress field of a diametrally loaded disc (4.2441 MPa at the centre, fringe order 2.380) turned into polariscope images by the Mueller-matrix ops and read back to stress. The op-built polariscope matches the textbook formula to 2.2e-16 across 125 cases. Phase wraps in the 84.2 % of pixels above fringe order 0.5, and unwrapping breaks first not where stress is highest but at the isotropic point, where modulation vanishes.*

[![左下 2 枚が「壊れる予報」。どちらもマスクで外せる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap.png)

*↑ The measurement ―― 左下 2 枚が「壊れる予報」。どちらもマスクで外せる。 (figure labels are in Japanese; the numbers are the same)*

```
py -3.11 examples/poc_photoelasticity.py
```

Source: [examples/poc_photoelasticity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

This run produced **2 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_photoelasticity)

Ops used (notes): [`mueller_apply`](https://furuse.work/ops/optics/polarization/mueller_apply.html) · [`mueller_element`](https://furuse.work/ops/optics/polarization/mueller_element.html) · [`unwrap_phase_2d`](https://furuse.work/ops/3d/structured_light/unwrap_phase_2d.html)

## No.2026.103 —— Measuring Rail with a Chord — At the Wavelengths Where the Transfer Function Is Zero, Any Amplitude Reads Zero

[![Measuring Rail with a Chord — At the Wavelengths Where the Transfer Function Is Zero, Any Amplitude Reads Zero](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/02_transfer_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/02_transfer.png)

*↑ **Measuring Rail with a Chord — At the Wavelengths Where the Transfer Function Is Zero, Any Amplitude Reads Zero** ―― Reading track irregularity with a chord (versine) — the distance from the mid-point to a chord drawn between two points, still the working method in track recording and in acceptance of rail re-profiling. The null baseline, reading the versine directly as height, ranges from 0.0 % to 200.0 % of the truth depending on wavelength: one and the same 10 m chord reads lambda=10 m at +100 %, lambda=1.5 m at +50 %, lambda=30 m at -50 %, and lambda=5.0 / 2.5 / 1.0 m at -100 %. Over-reading and under-reading happen at once, so no single correction factor repairs it. The blind spots are exact geometry: |H(lambda)| = |1 - cos(pi L / lambda)| is exactly zero at lambda = L/(2n) and doubles at lambda = L/(2n+1). Across ten wavelengths and two chords, twenty cases, prediction and measurement differ by at most 0.00000, and a 0.600 mm undulation at lambda=5.00 m gives a versine whose largest absolute value over 200 m is 0.00000 mm. Sorting into third-octave wavelength bands does not remove it (the ratio spans 0.00041 to 2.000, a factor of 4924), and the operator's total_power earned its place here: the band sum is only 0.519 of the sum over all FFT bins, and the missing 48 % is the 30 m irregularity sitting below f_min — invisible if only the bands are read. Dividing by |H| to invert diverges to 6.9e7 mm at the blind wavelengths, and regularising it makes three wavelengths quietly report 'no irregularity'. Two chords (10 m and 6 m) recover eight of the ten wavelengths to within 0.1 %, but the shared blind spot is not a point: it is the comb lambda = 1.000/k. One prediction was wrong — the planted lambda=0.100 m also survived, and it turned out to be the k=10 tooth. The relative spacing of the comb equals lambda itself, so it thickens toward short wavelengths: the corrugation band 0.03-0.30 m alone holds 30 blind wavelengths. At the 0.25 m sampling of a recording car, a 30 mm corrugation reappears as a 0.750 m undulation of 0.0528 mm, nine times the 0.00584 mm floor of a control with the short waves switched off. An asymmetric chord (3.7 m and 6.3 m arms) removes the long-wave blind spots, but |H| = 0 requires a/lambda and b/lambda to be integers together, so the blind spots move to lambda = gcd(a, b)/k = 0.100 m: the chord built to measure corrugation is blind inside the corrugation band.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/01_planted_components_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/01_planted_components.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![10 m 弦は λ=5.0 / 2.5 / 1.67 / 1.25 / 1.0 m で厳密に 0、λ=10 / 3.33 m で 2 倍。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/03_transfer_zoom_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/03_transfer_zoom.png)

*↑ 10 m 弦は λ=5.0 / 2.5 / 1.67 / 1.25 / 1.0 m で厳密に 0、λ=10 / 3.33 m で 2 倍。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/05_octave_bands_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/05_octave_bands.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/07_dual_chord_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/07_dual_chord.png)

*↑ この回の図*

[![0.750 m の周期がきれいに立つ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/09_aliasing_seen_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/09_aliasing_seen.png)

*↑ 0.750 m の周期がきれいに立つ。*

```
py -3.11 examples/poc_rail_corrugation.py
```

Source: [examples/poc_rail_corrugation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rail_corrugation.py)

This run produced **11 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_rail_corrugation)

Ops used (notes): [`octave_bands`](https://furuse.work/ops/acoustics/level/octave_bands.html) · [`octave_spectrum`](https://furuse.work/ops/acoustics/level/octave_spectrum.html)

## No.2026.104 —— Counting and Measuring Real Coins — A Correct Answer Is Not a Safe One

[![Counting and Measuring Real Coins — A Correct Answer Is Not a Safe One](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/01_scene.png)

*↑ **Counting and Measuring Real Coins — A Correct Answer Is Not a Safe One** ―― The real photograph famous for 'a global threshold cannot work here, the lighting falls away across the frame' (scikit-image coins). The background does slope, 0.427 to 0.161 down the rows and 0.331 to 0.059 across the columns — and yet a plain global Otsu with hole filling and an area floor of 150 lands exactly on the true 24. The truth is fixed by three independent paths agreeing (an area plateau spanning 50 to 800, a Hough circle search with the radii stated explicitly, and Sobel plus hole filling) and then checked one-to-one, each circle falling inside exactly one component. The margin, however, is 0.05: adding a little more of the same slope drops the count to 22. A correct answer is not evidence of a safe one. At +0.30 the median area moves by only -0.27 % while the worst single coin moves -24.20 %, and the drift correlates with row position at r = -0.90 — true area does not depend on where a coin sits, so that correlation is error, entire. Flattening with gray_tophat keeps the count but shrinks the median area to 0.29x, and the raw component count differs by 30 % between 4- and 8-connectivity.*

[![見た目はほとんど変わらないのに 2 枚落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/02_margin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/02_margin.png)

*↑ The measurement ―― 見た目はほとんど変わらないのに 2 枚落ちる。 (figure labels are in Japanese; the numbers are the same)*

[![代表値で報告すると、壊れているのに壊れていないように見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/03_drift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/03_drift.png)

*↑ 代表値で報告すると、壊れているのに壊れていないように見える。*

[![生の個数は近傍の規約で 3 割違う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/04_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/04_truth.png)

*↑ 生の個数は近傍の規約で 3 割違う。*

```
py -3.11 examples/poc_real_coin_metrology.py
```

Source: [examples/poc_real_coin_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_coin_metrology.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_coin_metrology)

Ops used (notes): [`blob_count`](https://furuse.work/ops/2d/features/blob_count.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`canny`](https://furuse.work/ops/2d/segmentation/canny.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`hough_circle_trans`](https://furuse.work/ops/2d/features/hough_circle_trans.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html)

## No.2026.083 —— Pitch, Flank Angle and Pitch Diameter From a Thread Silhouette — Tilt Shows Up With Opposite Signs on the Two Flanks

[![Pitch, Flank Angle and Pitch Diameter From a Thread Silhouette — Tilt Shows Up With Opposite Signs on the Two Flanks](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/07_sampling_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/07_sampling_frames.png)

*↑ **Pitch, Flank Angle and Pitch Diameter From a Thread Silhouette — Tilt Shows Up With Opposite Signs on the Two Flanks** ―― An M6-like silhouette drawn from the ISO 68-1 basic triangle in closed form (1 px = 25 µm). An FFT of the binarised column widths reports half the true pitch, 20 px, because the two profiles are offset by P/2 and their sum is constant. Tilting the axis by 3 degrees splits the flank angles into 33.18 / 26.74 degrees: their half-sum 29.81 is the true flank angle and their half-difference 3.19 estimates the tilt. Pitch measured on one flank drifts at first order (+3.28 / -2.79 %) while the crest spacing drifts at second order (-0.12 %); undoing the tilt leaves P -0.009 % and d2 +0.033 %.*

[![幅の系列は上下輪郭(P/2 ずれ)の和なので基本波が消える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum.png)

*↑ The measurement ―― 幅の系列は上下輪郭(P/2 ずれ)の和なので基本波が消える。 (figure labels are in Japanese; the numbers are the same)*

[![片側のフランクだけで測ると 1 度あたり約 1 % 狂う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/02_tilt_pitch_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/02_tilt_pitch.png)

*↑ 片側のフランクだけで測ると 1 度あたり約 1 % 狂う。*

[![半差が θ、半和が α。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/03_tilt_angles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/03_tilt_angles.png)

*↑ 半差が θ、半和が α。*

[![生 = 水平 caliper 4 山、補正 = θ_est の向きの caliper 16 山(3 種の平均)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/05_tilt_correction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/05_tilt_correction.png)

*↑ 生 = 水平 caliper 4 山、補正 = θ_est の向きの caliper 16 山(3 種の平均)。*

[![帯はフランクの中央 30 %(両端の丸みから 7.6 px)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/06_blur_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/06_blur_sweep.png)

*↑ 帯はフランクの中央 30 %(両端の丸みから 7.6 px)。*

```
py -3.11 examples/poc_screw_thread_metrology.py
```

Source: [examples/poc_screw_thread_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_screw_thread_metrology.py)

This run produced **8 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_screw_thread_metrology)

Ops used (notes): [`fit_line_contours`](https://furuse.work/ops/2d/contour/fit_line_contours.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`hx_split_contours`](https://furuse.work/ops/2d/halcon_ext/hx_split_contours.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`threshold_sub_pix`](https://furuse.work/ops/2d/contour/threshold_sub_pix.html) · [`xg_regress_contours`](https://furuse.work/ops/2d/xldgeom/xg_regress_contours.html)

## No.2026.112 —— Stockpile Inventory — The Answer Is Fixed by the Ground Nobody Measured

[![Stockpile Inventory — The Answer Is Fixed by the Ground Nobody Measured](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/05_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/05_scene.png)

*↑ **Stockpile Inventory — The Answer Is Fixed by the Ground Nobody Measured** ―― Stockpile inventory from a 3-D scan, for mining, aggregates and ports. The pile and the ground beneath it are written as separate formulas, and making the pile a sum of three cones at a 37 degree angle of repose closes the volume analytically at 3572.6089 m^3, matching a numerical integration at 0.025 m cells. The point is that the single number everyone quotes is fixed by a surface nobody measured: the ground under the pile. The first cliff is the assumed base, stated in closed form as dV = -A dh before measuring and matching to 0.0000 m^3 over seven offsets. The surprise is not the agreement but the size: 5 cm, which no survey would call an error, is 1.269 % of the inventory, or 72.5 t at a bulk density of 1.6 t/m^3 — three truckloads. The second cliff is occlusion. A cone is a ruled surface, so the visible fraction is arccos((H - h_s)/(D tan phi))/pi, matching to within 0.0201 over six geometries, and that residual halves with the cell size (0.0339, 0.0171, 0.0120 at 1.2, 0.6 and 0.4 m), which identifies it as discretisation rather than a wrong model. One prediction was wrong: interpolating across the occluded side was expected to under-estimate the volume, since a cone is concave and a chord passes below it, but the measurement is +17.20 %, an over-estimate. The far side is hidden all the way to the toe, so the triangulation connects the ridge not to the pile but to the ground beyond it, and a chord thrown 30 m past the ridge has a slope of 0.37 m/m that passes above the true 0.75 m/m slope. Then a cancellation trap: with the same single scan, using the true ground gives +17.20 % while the field practice of a horizontal base at the mean perimeter height gives +0.51 %. Nothing improved — the perimeter was lifted by the same interpolation, by +0.728 m, and the subtraction hides it; using only the perimeter points that were actually seen returns +12.05 %. A contaminated ruler applied to a contaminated object makes the error look like it went away. The same shape recurs with a berm of spoil at the toe: the outlier-resistant RANSAC fit reads worse (+2.48 %) than total least squares (+0.61 %), but RANSAC correctly rejected the berm and returned to the no-berm answer of +1.91 %, while TLS looked good because the berm's lift happened to cancel the bias from the undulating ground. Averaging the perimeter cancels the ground's tilt whenever the footprint is roughly symmetric — the flat control reads +0.01 % — so the remaining +1.79 % is entirely undulation, and fitting a tilted plane makes it worse (+1.91 %): more freedom does not mean less bias. The rulers disagree on the winner, with the horizontal base slightly better on volume and the fitted plane six times better on the centroid (0.07 m against 0.42 m), which is the quantity a loading plan uses. And the two errors do not add: -0.70 % expected against +0.51 % measured, because the occlusion fill moves the perimeter that fixes the base. Finally, a real bug was found and fixed: dem_viewshed reported every cell above the observer's eye as not visible — the apex of a cone on open flat ground read 0.0, none of the 1541 cells above eye level were visible, and the occluded fraction came out 0.8863 against a closed-form 0.5710. Line-of-sight samples rounded onto the target cell itself, occluding it against its own height; skipping those samples restores 1.0 at the apex and 0.5900 for the occluded fraction. The existing tests missed it because they only checked flat ground and what lies behind a wall, never whether the wall itself is visible.*

[![A = 906.5 m^2。閉形式は測る前に印字してある。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/01_base_offset_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/01_base_offset.png)

*↑ The measurement ―― A = 906.5 m^2。閉形式は測る前に印字してある。 (figure labels are in Japanese; the numbers are the same)*

[![2 本は重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/02_base_offset_line_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/02_base_offset_line.png)

*↑ 2 本は重なる。*

[![可視率 = arccos((H-h_s)/(D tanφ))/π。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/03_occlusion_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/03_occlusion_closed_form.png)

*↑ 可視率 = arccos((H-h_s)/(D tanφ))/π。*

[![3 か所で遮蔽は 1.4 % まで落ちるが、うねり由来の +1.8 % は何か所測っても消えない(底面は誰も測っていない)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/04_scan_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/04_scan_sweep.png)

*↑ 3 か所で遮蔽は 1.4 % まで落ちるが、うねり由来の +1.8 % は何か所測っても消えない(底面は誰も測っていない)。*

[![対照群(平ら/全周)で 2 つを切り分けてから、両方入れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/06_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/06_summary.png)

*↑ 対照群(平ら/全周)で 2 つを切り分けてから、両方入れる。*

```
py -3.11 examples/poc_stockpile_volume.py
```

Source: [examples/poc_stockpile_volume.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_stockpile_volume)

Ops used (notes): [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`dem_viewshed`](https://furuse.work/ops/dem/visibility/dem_viewshed.html) · [`interp_scattered`](https://furuse.work/ops/math/interp_poly/interp_scattered.html) · [`moment_axes`](https://furuse.work/ops/3d/match_pose/moment_axes.html)

## No.2026.038 —— Strain History in a Creep Test — Cumulative or Direct?

[![Strain History in a Creep Test — Cumulative or Direct?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle.png)

*↑ **Strain History in a Creep Test — Cumulative or Direct?** ―― One hour of creep in 25 frames, with strain history from accumulating adjacent-frame displacements versus comparing each frame directly with the reference. At the end, cumulative errs by 61 µε and direct by 1878 µε — cumulative wins 31x and the textbook crossover in time never appears (it lives on the noise axis instead). Thinning from 24 to 4 steps worsens cumulative from -60 to -606 µε; what matters is the deformation per step, not the number of steps.*

[![直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors.png)

*↑ The measurement ―― 直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。 (figure labels are in Japanese; the numbers are the same)*

[![因果フィルタの偏りは遅れ (w-1)/2 の閉形式にほぼ乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/03_rate_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/03_rate_tradeoff.png)

*↑ 因果フィルタの偏りは遅れ (w-1)/2 の閉形式にほぼ乗る。*

[![予測 = w=1 の偏り + 閉形式(中央はなまり、因果は遅れ)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/04_rate_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/04_rate_table.png)

*↑ 予測 = w=1 の偏り + 閉形式(中央はなまり、因果は遅れ)。*

```
py -3.11 examples/poc_strain_history.py
```

Source: [examples/poc_strain_history.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_strain_history.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_strain_history)

Ops used (notes): [`moving_average_window`](https://furuse.work/ops/videostream/window/moving_average_window.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_multipass`](https://furuse.work/ops/piv/estimate/piv_multipass.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_synth_pair`](https://furuse.work/ops/piv/synth/piv_synth_pair.html) · [`poly_fit`](https://furuse.work/ops/math/interp_poly/poly_fit.html)

## No.2026.040 —— How Far Sa / Sq / Sz Survive Sampling and Cutoff

[![How Far Sa / Sq / Sz Survive Sampling and Cutoff](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/01_surface_components_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/01_surface_components.png)

*↑ **How Far Sa / Sq / Sz Survive Sampling and Cutoff** ―― A surface synthesised from a prescribed PSD (so the true Sq follows analytically from Parseval), with tilt, waviness, lay and scratches added before the roughness parameters are measured. Calling the raw rms 'Sq' overstates it 20x; removing only the plane still leaves 1.8x. At 8 µm sampling Sa is -3.5 % (pass) while Sz is -19.8 % (fail); Sz keeps growing with evaluation area and never plateaus, so there is no such thing as the true Sz.*

[![dx=8 µm では Sa が ±5 % 合格で Sz が不合格。同じデータでも見るパラメータで結論が反転する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/02_sampling_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/02_sampling_cliff.png)

*↑ The measurement ―― dx=8 µm では Sa が ±5 % 合格で Sz が不合格。同じデータでも見るパラメータで結論が反転する。 (figure labels are in Japanese; the numbers are the same)*

[![頭打ちにならないので『真の Sz』は存在しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/03_sz_vs_window_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/03_sz_vs_window.png)

*↑ 頭打ちにならないので『真の Sz』は存在しない。*

[![左は加工目(λ=32µm)を落として過小、右はうねり(λ=256µm)が漏れて過大。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/04_lambda_c_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/04_lambda_c_sweep.png)

*↑ 左は加工目(λ=32µm)を落として過小、右はうねり(λ=256µm)が漏れて過大。*

```
py -3.11 examples/poc_surface_roughness.py
```

Source: [examples/poc_surface_roughness.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_surface_roughness.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_surface_roughness)

Ops used (notes): [`profile_params`](https://furuse.work/ops/roughness/measure/profile_params.html) · [`surface_filter`](https://furuse.work/ops/roughness/prepare/surface_filter.html) · [`surface_form_remove`](https://furuse.work/ops/roughness/prepare/surface_form_remove.html) · [`surface_params`](https://furuse.work/ops/roughness/measure/surface_params.html) · [`surface_psd`](https://furuse.work/ops/roughness/measure/surface_psd.html) · [`surface_synth_psd`](https://furuse.work/ops/roughness/synth/surface_synth_psd.html)

## No.2026.142 —— How Much of That Number Is Your Measuring - Gauge R&R and Measurement Uncertainty

[![How Much of That Number Is Your Measuring - Gauge R&R and Measurement Uncertainty](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/01_scene.png)

*↑ **How Much of That Number Is Your Measuring - Gauge R&R and Measurement Uncertainty** ―― Separate how much of a number comes from the parts and how much from the act of measuring, then combine the components of one measurement into a reportable uncertainty - scored entirely from outside the picture. The analysis-of-variance decomposition closes algebraically (1e-16); repeatability equals the mean of the per-cell sample variance numpy computes independently; the published worked example is reproduced to 1.5e-06 with contribution percentages 3.4/4.4/7.8/92.2 exactly. Keeping or pooling the interaction moves EV by 7.3 %, so the model actually used is reported; a negative variance component appears in 24 of 40 runs when the true component is zero and is declared, not hidden. Ignoring correlation errs in both directions on the same data (0.0702 -> 0.1945, a 2.8x overestimate, while reactance goes the other way). The effective degrees of freedom are truncated immediately before the t lookup (16.64 -> 16, k = 2.1199). At a stationary point the propagation law returns u = 0 and says so through structure rather than silently; Monte Carlo returns [0, 150]e-6 there. A sum of four rectangular distributions has an exact Irwin-Hall interval of -3.879407, against which the normal approximation is structurally 0.040521 too wide.*

[![測定の行為(GRR)が総変動に占めるのは 7.8 %、部品どうしの差が 92.2 %。どちらも公表値と一致する(最大差 1.5e-06)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/02_components_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/02_components.png)

*↑ The measurement ―― 測定の行為(GRR)が総変動に占めるのは 7.8 %、部品どうしの差が 92.2 %。どちらも公表値と一致する(最大差 1.5e-06)。 (figure labels are in Japanese; the numbers are the same)*

[![交互作用が**無い**ところ(左端)では畳むほうが真値 0.30 に近く、あるところでは畳むと交互作用を誤差に混ぜてしまうので上へ外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/03_pooling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/03_pooling.png)

*↑ 交互作用が**無い**ところ(左端)では畳むほうが真値 0.30 に近く、あるところでは畳むと交互作用を誤差に混ぜてしまうので上へ外れる。*

[![偏り = 0.070 -0.013 x 基準値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/05_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/05_bias.png)

*↑ 偏り = 0.070 -0.013 x 基準値。*

[![電圧と電流の相関だけを振った(他の 2 つは実測値で固定)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/08_correlation_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/08_correlation_sweep.png)

*↑ 電圧と電流の相関だけを振った(他の 2 つは実測値で固定)。*

[![感度 c₁ = 2x₁ なので x₁=0 では 1 次近似が情報を全部失い、伝播則は [0, 0) を返す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/11_breakdown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/11_breakdown.png)

*↑ 感度 c₁ = 2x₁ なので x₁=0 では 1 次近似が情報を全部失い、伝播則は [0, 0] を返す。*

[![評価点 x₁ を 0 から 0.026 へ動かしたもの。★左端では真の分布が**原点に肩を持つ指数**(u²χ²₂)で、伝播則は感度 c = 2x₁ が 0 になるため区間が**1 点に潰れる**。少し動かすと今度は区間が**負の損失**へ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/12_breakdown_movie.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/12_breakdown_movie.gif)

*↑ The animation ―― 評価点 x₁ を 0 から 0.026 へ動かしたもの。★左端では真の分布が**原点に肩を持つ指数**(u²χ²₂)で、伝播則は感度 c = 2x₁ が 0 になるため区間が**1 点に潰れる**。少し動かすと今度は区間が**負の損失**へ張り出す(物理的にありえない)。さらに離れると真の分布が正規に近づき、両者はようやく重なる —— **壊れ方は連続ではなく、3 つの段階がある**。*

```
py -3.11 examples/poc_measurement_system_analysis.py
```

Source: [examples/poc_measurement_system_analysis.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_measurement_system_analysis.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_measurement_system_analysis)

Ops used (notes): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`grid_lines`](https://furuse.work/ops/annotate/plot/grid_lines.html) · [`gum_expanded`](https://furuse.work/ops/spc/uncertainty/gum_expanded.html) · [`gum_monte_carlo`](https://furuse.work/ops/spc/uncertainty/gum_monte_carlo.html) · [`gum_propagate`](https://furuse.work/ops/spc/uncertainty/gum_propagate.html) · [`gum_standard_uncertainty`](https://furuse.work/ops/spc/uncertainty/gum_standard_uncertainty.html) · [`gum_validate`](https://furuse.work/ops/spc/uncertainty/gum_validate.html) · [`legend_box`](https://furuse.work/ops/annotate/furniture/legend_box.html) · [`msa_anova_table`](https://furuse.work/ops/spc/msa/msa_anova_table.html) · [`msa_attribute_agreement`](https://furuse.work/ops/spc/msa/msa_attribute_agreement.html) · [`msa_bias_linearity`](https://furuse.work/ops/spc/msa/msa_bias_linearity.html) · [`msa_gauge_rr`](https://furuse.work/ops/spc/msa/msa_gauge_rr.html) · [`nice_ticks`](https://furuse.work/ops/annotate/plot/nice_ticks.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.150 —— Scoring an Aberration as a Picture: Zernike Polynomials and the Point Spread Function

[![Scoring an Aberration as a Picture: Zernike Polynomials and the Point Spread Function](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/01_zernike_pyramid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/01_zernike_pyramid.png)

*↑ **Scoring an Aberration as a Picture: Zernike Polynomials and the Point Spread Function** ―― A picture of an optical aberration can be scored as a picture: the coefficients can be read back out of it, and what comes back agrees with closed forms. The only operators used are ones already in the box - fit_zernike, which takes a disk image to a dictionary of coefficients, and wavefront_stats, which reports RMS, peak-to-valley and the Strehl ratio. Zernike polynomials form an orthogonal system on the unit disk and are the vocabulary of aberration itself: (2,0) is defocus, (2,+-2) astigmatism, (3,+-1) coma, (4,0) spherical. The twenty-eight modes with n at most six - the closed form (n+1)(n+2)/2 - all equal one exactly at the rim, and the number of radial zeros matches (n-|m|)/2 for every one of them. Orthogonality agrees with the closed form pi/(2(n+1))(1+delta) to 4.86e-06 on the diagonal, with 5.50e-07 off it. The first finding is that the operator's own disclosure named the wrong cause. Its docstring says that at the default sampling up to ten percent leaks between modes, and advises raising the polar resolution. But the leak falls only as one over the radial step - ratios of 1.93, 1.78 and 1.50 per doubling, far from the four that a second-order law would give, and getting worse as the resolution rises - so eight times the resolution, at sixty-four times the work, buys a factor of five. The real cause is the single outermost ring of the polar grid sitting on the pupil edge, where bilinear interpolation draws in the zero background. Discarding that one ring, with no change in resolution at all, takes the worst leak across four modes from 0.09801 to 0.000259, a factor of 379, and leaves the recovered coefficient off by one part in a hundred thousand. Extending the polynomial two percent past the rim, which moves the same discontinuity away from the edge, reaches 0.000042 and confirms the diagnosis. The second finding is that the picture turns while the measurement does not: rotation multiplies each coefficient by a phase, so the paired amplitude is exactly invariant - 1.1e-16 across six angles, and the sum of squares identical to the last bit - and even after drawing the wavefront and reading it back, three rotations spread the amplitude by 2.03e-09. The third is that the rings of the point spread function are set by a Bessel zero: the first dark ring sits at the first zero of J1 divided by pi, 1.219670 in units of lambda over D, and reading it off the picture lands within 3.6e-04 across a threefold range of pupil size. An unaberrated Strehl ratio is exactly one, and the Marechal approximation that wavefront_stats returns differs from the exact diffraction integral by 8.8e-06 at an RMS of 0.02 waves but by 2.0e-02 at 0.18 - a gap that opens by a factor of 2308. The fourth concerns interference fringes: the gradient of spherical aberration vanishes at a radius of one over root two, and the fringes open into a broad band exactly there; measured off the picture the radius comes out at 0.70462 against 0.70711, with the error falling in inverse proportion to the number of fringes. The fifth is that the rotational symmetry of the point spread reveals the azimuthal order, but even orders appear at twice their own frequency. Modes with m of zero are exactly rotationally symmetric; odd orders appear at their own harmonic; even orders vanish there exactly and appear only at twice it - which is why astigmatism looks fourfold rather than twofold. The reason is that an even order makes the wavefront periodic over half a turn, the pupil field centrosymmetric, and the first-order cross term identically zero, so halving the aberration divides the odd harmonics by two and the even ones by four, measured at 2.06 and 3.67. The sixth is that tone mapping is not decoration: rendering the outer rings linearly collapses them to a single level of an eight-bit image, while an inverse hyperbolic sine gives sixty-six - and because that curve is strictly monotone, not one of five thousand sampled pixel pairs changes order. Three predictions were wrong and have been left in, along with two defects in the author's own measurement. No new operator was added.*

[![**波面を立体に起こす**(箱の `render3d` で描画)。左上がデフォーカス(お椀)、右上が非点収差(鞍)、左下がコマ、右下が球面収差。収差の名前は、この形の名前です。立体にしても採点は変わりません —— 係数は絵ではなく多項式に属](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/02_wavefront_3d_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/02_wavefront_3d.png)

*↑ The measurement ―― **波面を立体に起こす**(箱の `render3d` で描画)。左上がデフォーカス(お椀)、右上が非点収差(鞍)、左下がコマ、右下が球面収差。収差の名前は、この形の名前です。立体にしても採点は変わりません —— 係数は絵ではなく多項式に属しているからで、後の図で**絵を回しても数が動かないこと**を見せます。 (figure labels are in Japanese; the numbers are the same)*

[![**干渉縞** cos(2πW)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/03_interferogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/03_interferogram.png)

*↑ **干渉縞** cos(2πW)。*

[![**濃淡の付け方は飾りではありません。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/05_tone_matters_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/05_tone_matters.png)

*↑ **濃淡の付け方は飾りではありません。*

[![**28 × 28 のグラム行列** ∫Z_n^m Z_n'^m' ρdρdθ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/10_gram_matrix_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/10_gram_matrix.png)

*↑ **28 × 28 のグラム行列** ∫Z_n^m Z_n'^m' ρdρdθ。*

[![`wavefront_stats` が返すストレール比はマレシャル近似 exp(−(2πσ)²) です。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/12_strehl_vs_marechal_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/12_strehl_vs_marechal.png)

*↑ `wavefront_stats` が返すストレール比はマレシャル近似 exp(−(2πσ)²) です。*

[![**スルーフォーカス** —— デフォーカスを −0.55 波から +0.55 波まで振って戻します。輪が**同心のまま**伸縮するのがデフォーカスの特徴で、ピントの前後で絵が対称になります(だから往復させても継ぎ目が見えません)。中央の ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/06_through_focus.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/06_through_focus.gif)

*↑ The animation ―― **スルーフォーカス** —— デフォーカスを −0.55 波から +0.55 波まで振って戻します。輪が**同心のまま**伸縮するのがデフォーカスの特徴で、ピントの前後で絵が対称になります(だから往復させても継ぎ目が見えません)。中央の 1 コマだけが無収差のエアリーで、そこだけストレール比が厳密に **1.000000000000** です。*

[![**絵は回るのに、測った数は動きません。** 左が波面(コマ 0.62 ＋ 非点収差 0.35 ＋ 球面収差 0.18)、右がその点像。1 周ぶん回しています。回転は係数を exp(−imθ) 倍するだけなので、対の振幅 √(c₊²+c₋²](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/07_rotating_coma.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/07_rotating_coma.gif)

*↑ The animation ―― **絵は回るのに、測った数は動きません。** 左が波面(コマ 0.62 ＋ 非点収差 0.35 ＋ 球面収差 0.18)、右がその点像。1 周ぶん回しています。回転は係数を exp(−imθ) 倍するだけなので、対の振幅 √(c₊²+c₋²) は**厳密に**不変 —— 6 通りの角度で最大 **1.1e-16**。しかも**絵に描いてから `fit_zernike` で読み返しても**、3 通りの回転で振幅の幅は **3.3e-10** しかありません(真値 0.664831)。★球面収差(m = 0)だけは絵そのものが回りません —— m = 0 は回転で変わらないモードだからで、これも絵から読めます。*

```
py -3.11 examples/poc_zernike_aberrations.py
```

Source: [examples/poc_zernike_aberrations.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_zernike_aberrations.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_zernike_aberrations)

Ops used (notes): [`fit_zernike`](https://furuse.work/ops/3d/curvilinear/fit_zernike.html) · [`wavefront_stats`](https://furuse.work/ops/optics/imaging/wavefront_stats.html)

## No.2026.151 —— Every Speedup Is the Same Arithmetic Regrouped: Scoring Attention with Identities

[![Every Speedup Is the Same Arithmetic Regrouped: Scoring Attention with Identities](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/01_attention_masks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/01_attention_masks.png)

*↑ **Every Speedup Is the Same Arithmetic Regrouped: Scoring Attention with Identities** ―― Every speed and memory trick in the lineage that leads to large language models turns out to be a regrouping of the same arithmetic rather than an approximation, and each identity can be checked to machine precision. The operators are a new family of ten, written in numpy alone - no torch - and the input is a sequence of image patches (a 64 by 64 picture cut into sixty-four eight-by-eight tiles), so attention here is literally the entrance to a vision transformer and the claims hold on the picture side too. The first finding is that tiled attention with an online softmax, the core of FlashAttention, is exact: across seven tile sizes from one row to sixty-four the worst disagreement with the one-pass computation is 1.33e-15. What makes it fast is not a different computation but never forming the T by T matrix at all. A prediction was wrong here: error was expected to accumulate with the number of tiles, and it does, but sixty-four tiles give 1.33e-15 against 1.22e-15 for one - a factor of 1.1. The second is that linear attention is associativity and nothing else: (QK^T)V and Q(K^T V) agree to 1.18e-15, and the causal running-state form to 9.39e-16. The quadratic and linear costs are two bracketings of one product, and the operation counts stand in a ratio of exactly T over d (32 at T of 2048, an integer) -- which is why the crossover sits at T equal to d. A second prediction was half right: the measured time ratio stalls at fifteen or sixteen instead of the thirty-two the formula promises, because the quadratic path becomes bandwidth-bound. Time, though, is decided by the machine: the same commit measured 11.6x here and 2.0x on the CI runner, so this PoC gates on the operation-count identity alone and reports the timing without a verdict.*

[![縦軸は **1e-16 単位**。タイルを 64 枚に割っても相対差は **1.3e-15** —— 近似ではなく、同じ和を別の順で足しているだけ。★外した予言: 誤差はタイル数に比例して積もる → **64 倍のタイル数で 1.1 倍**](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/02_tiled_exactness_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/02_tiled_exactness.png)

*↑ The measurement ―― 縦軸は **1e-16 単位**。タイルを 64 枚に割っても相対差は **1.3e-15** —— 近似ではなく、同じ和を別の順で足しているだけ。★外した予言: 誤差はタイル数に比例して積もる → **64 倍のタイル数で 1.1 倍**にしかならない。 (figure labels are in Japanese; the numbers are the same)*

[![**答えは同じ**(相対差 1.2e-15)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/03_linear_crossover_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/03_linear_crossover.png)

*↑ **答えは同じ**(相対差 1.2e-15)。*

[![2 枚目と 3 枚目は**差 4.4e-16** —— パッチを並べ替えてから戻すと元に戻る(置換同変)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/05_patch_shuffle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/05_patch_shuffle.png)

*↑ 2 枚目と 3 枚目は**差 4.4e-16** —— パッチを並べ替えてから戻すと元に戻る(置換同変)。*

[![2 本の線は 64 本すべてで重なる(最大差 **4.4e-16**)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/07_rope_norm_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/07_rope_norm.png)

*↑ 2 本の線は 64 本すべてで重なる(最大差 **4.4e-16**)。*

[![行和が 1 なので出力は入力の凸結合で、値域 [0.025, 1.000) を出ない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/09_convex_mixing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/09_convex_mixing.png)

*↑ 行和が 1 なので出力は入力の凸結合で、値域 [0.025, 1.000] を出ない。*

```
py -3.11 examples/poc_attention_identities.py
```

Source: [examples/poc_attention_identities.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_attention_identities.py)

This run produced **10 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_attention_identities)

Ops used (notes): [`attention_apply`](https://furuse.work/ops/llmcore/score/attention_apply.html) · [`attention_grouped`](https://furuse.work/ops/llmcore/attend/attention_grouped.html) · [`attention_linear`](https://furuse.work/ops/llmcore/attend/attention_linear.html) · [`attention_scores`](https://furuse.work/ops/llmcore/score/attention_scores.html) · [`attention_softmax`](https://furuse.work/ops/llmcore/attend/attention_softmax.html) · [`attention_tiled`](https://furuse.work/ops/llmcore/attend/attention_tiled.html) · [`attention_weights`](https://furuse.work/ops/llmcore/score/attention_weights.html) · [`kv_cache_decode`](https://furuse.work/ops/llmcore/decode/kv_cache_decode.html) · [`project`](https://furuse.work/ops/3d/bundle_adjust/project.html) · [`rms_norm`](https://furuse.work/ops/llmcore/prepare/rms_norm.html) · [`rope_rotate`](https://furuse.work/ops/llmcore/prepare/rope_rotate.html)

### The Medical and Biological Wing — The Count Is Right and the Contents Are Wrong

Counting cells, reading a nucleus's DNA content, measuring vessel branching, tracking a wound's area: all of these tend to be reported as one number, and there are situations in which that number is right anyway. Cell counting where over- and under-segmentation balance to a +0.3-cell bias; ploidy classification that survives a forgotten background subtraction; a calibration that returns the most stable and most wrong healing constant.

The four exhibits carry ground truth that a label image alone cannot hold — which cells overlap which, area and DNA content varying independently, a tree that satisfies the branching law exactly. Each docstring warns that calling a label image 'the truth' on real data erases the very thing being tested.

The thing to watch for is a method that appears to improve while the quantity it measures quietly swaps: the area classifier gets better with more blur because 'area' is leaking DNA content. Unless the reason for every improvement is traced, this kind of lie gets carried home as a result.

## No.2026.057 —— Trabecular Thickness, Separation and Bone Volume Fraction — The Plate Model and the Direct Method Disagree on the Same Image

[![Trabecular Thickness, Separation and Bone Volume Fraction — The Plate Model and the Direct Method Disagree on the Same Image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth.png)

*↑ **Trabecular Thickness, Separation and Bone Volume Fraction — The Plate Model and the Direct Method Disagree on the Same Image** ―― A 2-D trabecular network drawn in closed form as a set of segments (median width 120 µm), observed through partial-volume blur, CT noise and a cupping bias. There is more than one ground truth: the length-weighted mean width is 104.8 µm, the largest-inscribed-circle definition gives 121.6 µm and the plate model 118.4 µm — the choice of truth moves the answer by 9–16 % before any threshold does. The resolution cliff hits the distribution, not the mean (overlap with truth 0.83 → 0.09 at 60 µm pixels; the mean survives because quantisation at -29.5 % and Otsu thickening at +27.1 % cancel). Noise breaks from two sides, speckles from σ 0.10 and gaps from σ 0.15, and an area opening removes only the speckles.*

[![Tb.Th の平均は 2 px/骨梁でも持つが、BV/TV と分布は壊れている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/02_resolution_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/02_resolution_sweep.png)

*↑ The measurement ―― Tb.Th の平均は 2 px/骨梁でも持つが、BV/TV と分布は壊れている。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/03_thickness_distribution_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/03_thickness_distribution.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/06_thickness_map_measured_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/06_thickness_map_measured.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/09_noise_remedies_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/09_noise_remedies.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/12_bias_masks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/12_bias_masks.png)

*↑ この回の図*

```
py -3.11 examples/poc_bone_trabecular_thickness.py
```

Source: [examples/poc_bone_trabecular_thickness.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bone_trabecular_thickness.py)

This run produced **14 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_bone_trabecular_thickness)

Ops used (notes): [`blob_distance`](https://furuse.work/ops/blob/split/blob_distance.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`dc_retinex`](https://furuse.work/ops/2d/decomposition/dc_retinex.html) · [`dist_transform`](https://furuse.work/ops/2d/region/dist_transform.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`get_region_thickness`](https://furuse.work/ops/2d/features/get_region_thickness.html) · [`local_thickness`](https://furuse.work/ops/2d/morphology/local_thickness.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_area_opening`](https://furuse.work/ops/2d/morphology/sk_area_opening.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.008 —— Counting Overlapping Cells — Count, Over-Segmentation and Under-Segmentation as Three Numbers

[![Counting Overlapping Cells — Count, Over-Segmentation and Under-Segmentation as Three Numbers](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/01_scene_dense_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/01_scene_dense.png)

*↑ **Counting Overlapping Cells — Count, Over-Segmentation and Under-Segmentation as Three Numbers** ―― Synthetic overlapping cells with the count, over-segmentation and under-segmentation tallied separately. In the densest condition the null misses 25 of 78 cells, every one of them an under-segmentation. Sweeping the seed suppression finds a balance point where the count bias is +0.3 cells while 13.3 segmentation errors remain; report the count alone and it passes as the best setting.*

[![誤り合計の谷と |偏り| の谷は同じ場所に来ない。どちらを最適と呼ぶかで答えが変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/02_h_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/02_h_tradeoff.png)

*↑ The measurement ―― 誤り合計の谷と |偏り| の谷は同じ場所に来ない。どちらを最適と呼ぶかで答えが変わる。 (figure labels are in Japanese; the numbers are the same)*

[![偏りが 0 を横切る間隔 6 で分割誤りは 13.3 件残る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/03_count_cancellation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/03_count_cancellation.png)

*↑ 偏りが 0 を横切る間隔 6 で分割誤りは 13.3 件残る。*

[![真値の前景率 11.6 %。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/04_noise_vs_shading_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/04_noise_vs_shading.png)

*↑ 真値の前景率 11.6 %。*

```
py -3.11 examples/poc_cell_counting.py
```

Source: [examples/poc_cell_counting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cell_counting.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_cell_counting)

Ops used (notes): [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html) · [`vol_watershed`](https://furuse.work/ops/3d/segment/vol_watershed.html) · [`xsk2_h_maxima`](https://furuse.work/ops/2d/segmentation/xsk2_h_maxima.html)

## No.2026.061 —— Colocalization lies under bleed-through — Pearson and Manders break in different places

[![Colocalization lies under bleed-through — Pearson and Manders break in different places](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels.png)

*↑ **Colocalization lies under bleed-through — Pearson and Manders break in different places** ―― Two channels of vesicle-like puncta are scattered over a synthetic cell body, with 0 / 25 / 50 / 100 % of the B puncta placed exactly on A puncta so the true colocalization is known. After the bleed-through matrix [[1, α], [β, 1]], cytoplasm, PSF and photon noise, two unrelated channels give Pearson r=0.203 and Otsu-Manders M1=0.133 at α=β=10 %. Estimating α=0.0996 (truth 0.10) from single-stain controls and unmixing linearly restores r to 0.007, but Manders stays at 0.705 even for 100 % (the Gaussian tails below the Otsu threshold are lost; closed-form prediction 0.756). Pearson crosses 0.5 at symmetric α=0.282 (predicted 2−√3=0.268); blur only breaks Manders, with a step at σ=2.5 px where Otsu's foreground jumps from puncta to the whole cell. The Costes shuffle test calls pure bleed-through 'significant' at p=0.000.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/02_scene_unmixed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/02_scene_unmixed.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/03_cytofluorogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/03_cytofluorogram.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/05_costes_significance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/05_costes_significance.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/07_crosstalk_sweep_manders_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/07_crosstalk_sweep_manders.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/09_psf_masks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/09_psf_masks.png)

*↑ この回の図*

```
py -3.11 examples/poc_colocalization_crosstalk.py
```

Source: [examples/poc_colocalization_crosstalk.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colocalization_crosstalk.py)

This run produced **11 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_colocalization_crosstalk)

Ops used (notes): [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html) · [`mat_solve`](https://furuse.work/ops/math/linalg/mat_solve.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`photon_sample`](https://furuse.work/ops/photon/counting/photon_sample.html) · [`reg_erode`](https://furuse.work/ops/2d/region/reg_erode.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html)

## No.2026.074 —— MRI Bias Field and Tissue Area — Grey and White Matter Fail in Opposite Directions, and the Sum Hides It

[![MRI Bias Field and Tissue Area — Grey and White Matter Fail in Opposite Directions, and the Sum Hides It](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/02_scene.png)

*↑ **MRI Bias Field and Tissue Area — Grey and White Matter Fail in Opposite Directions, and the Sum Hides It** ―― A brain-slice phantom of elliptical shells (skull / CSF / wrinkled cortex / WM, areas known from geometry) is multiplied by a surface-coil bias field and Rician noise, and the three tissue areas are measured with global three-class Otsu (xsk2_multiotsu). At 30 % amplitude GM is +20.2 % and WM -7.7 % while GM+WM is +0.0 % — the sum hides the error — and removing the noise flips the sign (GM -11.8 %). The geometric cliff prediction was 30 %; the measured cliff is 17.5 %. Naively smoothing log I damages a field-free image by GM +81.8 %; iterating on the segmentation residual (Wells-type) holds +1.8 % even at 40 %. Every corrector fails once the field is as fine as 4 px, and at SNR 15 GM is +8.5 % even without a field (WM is 2.6× larger, so the error lands on the smaller tissue).*

[![雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/01_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/01_controls.png)

*↑ The measurement ―― 雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。 (figure labels are in Japanese; the numbers are the same)*

[![幾何予測(しきい値固定・雑音なし)と大津の実測は同じ振幅で崖を越える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/03_amplitude_sweep_zero_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/03_amplitude_sweep_zero.png)

*↑ 幾何予測(しきい値固定・雑音なし)と大津の実測は同じ振幅で崖を越える。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/05_amplitude_residual_cv_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/05_amplitude_residual_cv.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/07_bias_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/07_bias_map.png)

*↑ この回の図*

[![σ_b 4 px は皮質リボンの太さ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/09_frequency_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/09_frequency_sweep.png)

*↑ σ_b 4 px は皮質リボンの太さ。*

```
py -3.11 examples/poc_mri_bias_field.py
```

Source: [examples/poc_mri_bias_field.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mri_bias_field.py)

This run produced **11 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_mri_bias_field)

Ops used (notes): [`dc_homomorphic`](https://furuse.work/ops/2d/decomposition/dc_homomorphic.html) · [`eval_bspline_surface`](https://furuse.work/ops/3d/freeform/eval_bspline_surface.html) · [`eval_poly_surface`](https://furuse.work/ops/3d/surface_fit/eval_poly_surface.html) · [`fit_bspline_surface`](https://furuse.work/ops/3d/freeform/fit_bspline_surface.html) · [`fit_poly_surface`](https://furuse.work/ops/3d/surface_fit/fit_poly_surface.html) · [`overlay_labels`](https://furuse.work/ops/annotate/overlay/overlay_labels.html) · [`xsk2_multiotsu`](https://furuse.work/ops/2d/segmentation/xsk2_multiotsu.html)

## No.2026.027 —— Ploidy From Integrated Nuclear Intensity — Area Cannot Separate It

[![Ploidy From Integrated Nuclear Intensity — Area Cannot Separate It](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/04_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/04_scene.png)

*↑ **Ploidy From Integrated Nuclear Intensity — Area Cannot Separate It** ―― Fluorescent nuclei whose DNA content D and area A were drawn with independent spread, classified by area and by integrated intensity. Even the true area misclassifies 15.4 %; integrated intensity misclassifies 0 %. Forgetting to subtract background leaves the classification intact while the DNA index alone breaks from 2.115 to 1.702 (-20 %) — invisible if you only watch the classification.*

[![累積分布。積分輝度の 4n は 2.1 付近に固まり、面積の 2 本は大きく重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/01_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/01_histograms.png)

*↑ The measurement ―― 累積分布。積分輝度の 4n は 2.1 付近に固まり、面積の 2 本は大きく重なる。 (figure labels are in Japanese; the numbers are the same)*

[![誤分類率はほぼ 0 のままだが、DNA 指数は背景とともに 2.00 から落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/02_background_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/02_background.png)

*↑ 誤分類率はほぼ 0 のままだが、DNA 指数は背景とともに 2.00 から落ちる。*

[![特徴量が分かれてさえいれば割り方は選ばない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/03_mixture_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/03_mixture.png)

*↑ 特徴量が分かれてさえいれば割り方は選ばない。*

```
py -3.11 examples/poc_nuclei_ploidy.py
```

Source: [examples/poc_nuclei_ploidy.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_nuclei_ploidy.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_nuclei_ploidy)

Ops used (notes): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`sg_gmm_segment`](https://furuse.work/ops/2d/segment/sg_gmm_segment.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html)

## No.2026.048 —— Extracting a Vessel Network — Spurs, Overestimated Radii Near Branches, and a Fragile Exponent

[![Extracting a Vessel Network — Spurs, Overestimated Radii Near Branches, and a Fragile Exponent](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/01_scene.png)

*↑ **Extracting a Vessel Network — Spurs, Overestimated Radii Near Branches, and a Fragile Exponent** ―― A synthetic vessel tree obeying Murray's law exactly, skeletonised and measured for branch points, radii and the exponent. Counting branch pixels directly gives 47 pixels for 25 branches; grouping them into connected components gives exactly 25. Spurs come not from the skeletonisation but from boundary roughness (spurious branches 0 → 72), and radii within 3 px of a branch are overestimated by +26.2 %.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/02_prune_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/02_prune.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/03_radius_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/03_radius_bias.png)

*↑ この回の図*

[![分岐から 2 px の点は 1 つも解けなかったので図から外した](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/04_murray_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/04_murray.png)

*↑ 分岐から 2 px の点は 1 つも解けなかったので図から外した*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/05_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/05_summary.png)

*↑ この回の図*

```
py -3.11 examples/poc_vessel_network.py
```

Source: [examples/poc_vessel_network.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vessel_network.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_vessel_network)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`medial_axis_points`](https://furuse.work/ops/3d/medial/medial_axis_points.html) · [`r2_split_skeleton_lines`](https://furuse.work/ops/2d/region/r2_split_skeleton_lines.html) · [`sk_medial`](https://furuse.work/ops/2d/region/sk_medial.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`skeleton_branches3d`](https://furuse.work/ops/3d/medial/skeleton_branches3d.html) · [`skeleton_endpoints3d`](https://furuse.work/ops/3d/medial/skeleton_endpoints3d.html) · [`skeleton_junctions3d`](https://furuse.work/ops/3d/medial/skeleton_junctions3d.html) · [`skeleton_prune3d`](https://furuse.work/ops/3d/medial/skeleton_prune3d.html) · [`skeletonize_vol`](https://furuse.work/ops/3d/medial/skeletonize_vol.html) · [`thinning`](https://furuse.work/ops/2d/region/thinning.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html)

## No.2026.052 —— Wound Area Over Time — Calibration Error Enters the Area Squared

[![Wound Area Over Time — Calibration Error Enters the Area Squared](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/02_scenes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/02_scenes.png)

*↑ **Wound Area Over Time — Calibration Error Enters the Area Squared** ―― A star-shaped wound on a millimetre plane (closed-form area), photographed day by day through a pinhole camera to estimate the healing constant k. A 4 % change in distance moves the area by 7.7 %; with the distance drifting 1.2 % per day the null reports k = 0.1424 against a true 0.1200 (+18.7 %). Its standard deviation, 0.0049, is smaller than the 0.0059 of recalibrating every time — the most stable and the most wrong answer.*

[![ゼロ点の面積誤差。実測は閉形式の 2 乗則に乗り、線形近似からは外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/01_dist_square_law_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/01_dist_square_law.png)

*↑ The measurement ―― ゼロ点の面積誤差。実測は閉形式の 2 乗則に乗り、線形近似からは外れる。 (figure labels are in Japanese; the numbers are the same)*

[![ゼロ点は毎回もっともらしい値を返しながら、傾きだけが系統的に急になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/03_healing_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/03_healing_curve.png)

*↑ ゼロ点は毎回もっともらしい値を返しながら、傾きだけが系統的に急になる。*

[![較正は d に対して (1+d)²-1、しきい値はほぼ線形。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/04_sensitivity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/04_sensitivity.png)

*↑ 較正は d に対して (1+d)²-1、しきい値はほぼ線形。*

[![ゼロ点は散らばりがいちばん小さく、偏りがいちばん大きい。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/05_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/05_summary.png)

*↑ ゼロ点は散らばりがいちばん小さく、偏りがいちばん大きい。*

```
py -3.11 examples/poc_wound_area_tracking.py
```

Source: [examples/poc_wound_area_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_wound_area_tracking.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_wound_area_tracking)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## No.2026.123 —— A Larval Connectome as a Reservoir Reads Digits — and the Wiring Is Not What Does It

[![A Larval Connectome as a Reservoir Reads Digits — and the Wiring Is Not What Does It](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/01_adjacency_binned_connectome_vs_shuffle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/01_adjacency_binned_connectome_vs_shuffle.png)

*↑ **A Larval Connectome as a Reservoir Reads Digits — and the Wiring Is Not What Does It** ―― The complete larval Drosophila connectome (Winding 2023: 2,952 neurons, 110,677 edges) used as a fixed recurrent network with only a closed-form ridge readout reads an MNIST subset (4,000 train, 1,000 test) at 91.9 % (ridge on raw pixels: 77.6 %). Prior work stops there; this exhibit adds the controls: a graph with every neuron's in- and out-degree preserved but the edges rewired reaches 91.6 %, a random graph of the same density 91.9 %, a Gaussian random reservoir 91.5 %. The gap is +0.3 points over 3 seeds. What the readout uses is the reservoir as a mechanism, not the wiring evolution chose. The setting (input scale and regularisation) is chosen once on the connectome's validation split and reused for every control.*

[![|state| of the 300 highest-degree neurons over 6 steps for one test digit: connectome | shuffle](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/02_activity_raster_connectome_vs_shuffle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/02_activity_raster_connectome_vs_shuffle.png)

*↑ The measurement ―― |state| of the 300 highest-degree neurons over 6 steps for one test digit: connectome | shuffle (figure labels are in Japanese; the numbers are the same)*

[![test accuracy per reservoir variant (rows: no reservoir, connectome, shuffle, ER, Gaussian)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/03_accuracy_bars_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/03_accuracy_bars.png)

*↑ test accuracy per reservoir variant (rows: no reservoir, connectome, shuffle, ER, Gaussian)*

```
py -3.11 examples/poc_larval_connectome_reservoir.py
```

Source: [examples/poc_larval_connectome_reservoir.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_larval_connectome_reservoir.py)

This run produced **3 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_larval_connectome_reservoir)

Ops used (notes): [`graph_degree_preserving_shuffle`](https://furuse.work/ops/conngraph/construct/graph_degree_preserving_shuffle.html) · [`graph_degree_table`](https://furuse.work/ops/conngraph/stats/graph_degree_table.html) · [`graph_spectral_radius`](https://furuse.work/ops/conngraph/stats/graph_spectral_radius.html) · [`reservoir_encode`](https://furuse.work/ops/conngraph/reservoir/reservoir_encode.html) · [`reservoir_from_graph`](https://furuse.work/ops/conngraph/reservoir/reservoir_from_graph.html) · [`ridge_predict`](https://furuse.work/ops/conngraph/reservoir/ridge_predict.html) · [`ridge_readout`](https://furuse.work/ops/conngraph/reservoir/ridge_readout.html)

## No.2026.124 —— Watching a Pulse Travel the Wiring on the 3-D Fly Brain — Connectome vs Degree-Preserving Shuffle

[![Watching a Pulse Travel the Wiring on the 3-D Fly Brain — Connectome vs Degree-Preserving Shuffle](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/02_activity_wave_three_views.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/02_activity_wave_three_views.gif)

*↑ **Watching a Pulse Travel the Wiring on the 3-D Fly Brain — Connectome vs Degree-Preserving Shuffle** ―― The previous exhibit ended with 'readout accuracy cannot tell the connectome from a random graph'. This one uses the same reservoir to *look*: the 3,000 somatic neurons of the MaleCNS with the most synapses (344,719 edges) receive a pulse into the right optic lobe only, and the activity is drawn on the rotating 3-D brain and VNC (grey = all 141,781 somata, orange = right, blue = left). Next to it, a graph with every neuron's in- and out-degree preserved but the edges rewired gets the *same pulse through the same input matrix*. Measured: in the connectome the |x|-weighted mean distance from the stimulus grows 88 → 230 µm over 17 steps, and neurons light in order optic (latency 0) → central (2) → descending (2), never reaching the VNC within 36 steps. In the shuffle the activity scatters to 300 µm in 3 steps and 93 % of the farthest quarter of the neurons light within the first period (connectome: 0 %). The spatial structure of the wiring that accuracy could not see is visible in motion. One brightness scale for every frame. Besides the rotating view, a second animation shows the same instant from three fixed directions at once (dorsal, lateral, along the body axis; `views=`). Raw data is never committed (the subgraph is built from local feather files and cached; without them a distance-wired synthetic surrogate runs the same path).*

[![a pulse into the right optic lobe (orange = right, blue = left somata; grey = all 141781 somata) propagates through the ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif)

*↑ The measurement ―― a pulse into the right optic lobe (orange = right, blue = left somata; grey = all 141781 somata) propagates through the real wiring (left) and through the same degrees rewired at random (right); 3000 neurons, 344719 edges, 36 steps, one brightness scale for every frame (figure labels are in Japanese; the numbers are the same)*

[![when each neuron first lights up (yellow = step 0, orange = step 3, blue = step 6 or later, grey = n](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/03_activation_latency_map_connectome_vs_shuffle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/03_activation_latency_map_connectome_vs_shuffle.png)

*↑ when each neuron first lights up (yellow = step 0, orange = step 3, blue = step 6 or later, grey = never within 36 steps): connectome | shuffle*

[![graph_activity_spread: |x|-weighted mean distance from the stimulated somata](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/04_activity_spread_mean_distance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/04_activity_spread_mean_distance.png)

*↑ graph_activity_spread: |x|-weighted mean distance from the stimulated somata*

```
py -3.11 examples/poc_malecns_activity_wave.py
```

Source: [examples/poc_malecns_activity_wave.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_malecns_activity_wave.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_malecns_activity_wave)

Ops used (notes): [`graph_activation_latency`](https://furuse.work/ops/conngraph/activity/graph_activation_latency.html) · [`graph_activity_spread`](https://furuse.work/ops/conngraph/activity/graph_activity_spread.html) · [`graph_degree_preserving_shuffle`](https://furuse.work/ops/conngraph/construct/graph_degree_preserving_shuffle.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`reservoir_from_graph`](https://furuse.work/ops/conngraph/reservoir/reservoir_from_graph.html) · [`reservoir_states`](https://furuse.work/ops/conngraph/reservoir/reservoir_states.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.125 —— What the Compound Eye Sees, and Where the Brain Answers — Trace an Ommatidium and the Response Travels the Wiring

[![What the Compound Eye Sees, and Where the Brain Answers — Trace an Ommatidium and the Response Travels the Wiring](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/02_image_through_the_eye.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/02_image_through_the_eye.gif)

*↑ **What the Compound Eye Sees, and Where the Brain Answers — Trace an Ommatidium and the Response Travels the Wiring** ―― The MaleCNS annotations give every optic-lobe neuron a hexagonal column (the column that belongs to one ommatidium of the retina). The 892 right-eye columns (top 3 neurons each) plus 1,400 central and descending hubs form a subgraph of 4,076 neurons and 150,487 edges, stimulated at the resolution of a single ommatidium. Animation 1: as the stimulated column moves along a row of the eye, the response (yellow = stimulated, orange = right, blue = left; scale = response peak excluding the stimulus) moves the same way inside the optic lobe — the correlation between the stimulated column and the response centroid is −0.92 for the connectome and +0.01 for the degree-preserving shuffle with the same input matrix. Retinotopy lives in the wiring and not in the degrees. Animation 2: a bar crossing the visual field is resampled onto the ommatidial lattice (`fly_hex_resample`) and each ommatidium's brightness drives its column; the response follows the bar (dorsal and lateral views). In Studio, Tools ▸ Compound eye → brain runs the same parts interactively: hover to stimulate the column under the mouse, drag to orbit, feed the current Studio image through the eye, switch to the shuffle. The column-to-ommatidium mapping is an approximation by normalised hexagonal coordinates. Neither the raw data nor the subgraph is committed (cached from local feather files; without them a synthetic surrogate with hexagonal columns runs the same path).*

[![a stimulus of one eye column (+ its 6 neighbours) moves along a row of the right eye; yellow = stimulated neurons, orang](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif)

*↑ The measurement ―― a stimulus of one eye column (+ its 6 neighbours) moves along a row of the right eye; yellow = stimulated neurons, orange/blue = response (scale = response peak); the connectome answers retinotopically, the shuffle does not (figure labels are in Japanese; the numbers are the same)*

[![|x|-weighted centroid of the responding optic-lobe neurons vs the stimulated column](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/03_retinotopy_scatter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/03_retinotopy_scatter.png)

*↑ |x|-weighted centroid of the responding optic-lobe neurons vs the stimulated column*

[![fly_hex_quantize(mode=log): a low-contrast soft bar (0.5 + 0.3, sigma 6 px) crossing the visual fiel](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/04_retinotopy_vs_bits_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/04_retinotopy_vs_bits.png)

*↑ fly_hex_quantize(mode=log): a low-contrast soft bar (0.5 + 0.3, sigma 6 px) crossing the visual field is quantized to n bits per ommatidium before ent…*

```
py -3.11 examples/poc_eye_to_brain.py
```

Source: [examples/poc_eye_to_brain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_eye_to_brain.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_eye_to_brain)

Ops used (notes): [`fly_hex_quantize`](https://furuse.work/ops/flyvision/sample/fly_hex_quantize.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.126 —— A Second Opinion for EM Connectome Proofreading — Membranes Belong Only on Label Boundaries

[![A Second Opinion for EM Connectome Proofreading — Membranes Belong Only on Label Boundaries](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/01_second_opinion_slice_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/01_second_opinion_slice.png)

*↑ **A Second Opinion for EM Connectome Proofreading — Membranes Belong Only on Label Boundaries** ―― Automatic segmentation of serial EM sections leaves merges (two cells under one id) and splits (one cell under two ids); every prior detector is a deep network. This PoC counts the same two errors without learning, from one premise read two ways — a cell membrane (dark ridge) belongs only on label boundaries: a membrane chord crossing the inside of a label = merge suspect (closed rings, i.e. mitochondria, are excluded by their hole), a boundary without membrane = split suspect. Artificial merges and splits are injected into the ground-truth labels of CREMI sample A (12 slices of 512², raw data never committed); with thresholds chosen on the first 6 slices and every number reported on the last 6, splits reach AUC 1.00 (TPR 1.00 / FPR 0.11) and merges AUC 0.83 against area-matched negatives (TPR 0.12 / FPR 0.01; random 0.53, area only 0.70). Merge detection is weak: membrane-rich cells score like chords. Because an injected merge is the union of two large labels, measuring without area matching yields 0.87 from 'big label = suspicious' alone — the reason holdout_threshold, which separates the slices that choose the threshold from the slices that are measured, is an operator. The animation rotates the stacked cube with suspects on top (magenta = merge, cyan = split, brightness = score). New family emproof (7 ops, numpy + scipy only).*

[![suspects on the stacked cube: magenta = merge suspects (membrane chords), cyan = split suspects (membrane-free boundarie](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/02_suspects_on_the_cube.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/02_suspects_on_the_cube.gif)

*↑ The measurement ―― suspects on the stacked cube: magenta = merge suspects (membrane chords), cyan = split suspects (membrane-free boundaries), brightness = score, grey = all label boundaries (figure labels are in Japanese; the numbers are the same)*

[![ROC on the held-out slices; thresholds were chosen on the other half](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/03_holdout_roc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/03_holdout_roc.png)

*↑ ROC on the held-out slices; thresholds were chosen on the other half*

[![tau = smallest threshold with train FPR <= 5 %; every number in the test columns comes from slices t](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/04_holdout_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/04_holdout_numbers.png)

*↑ tau = smallest threshold with train FPR <= 5 %; every number in the test columns comes from slices the threshold never saw*

```
py -3.11 examples/poc_em_second_opinion.py
```

Source: [examples/poc_em_second_opinion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_em_second_opinion.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_em_second_opinion)

Ops used (notes): [`holdout_threshold`](https://furuse.work/ops/emproof/evaluate/holdout_threshold.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`seg_boundary_membrane_gap`](https://furuse.work/ops/emproof/suspect/seg_boundary_membrane_gap.html) · [`seg_inject_merge`](https://furuse.work/ops/emproof/inject/seg_inject_merge.html) · [`seg_inject_split`](https://furuse.work/ops/emproof/inject/seg_inject_split.html) · [`seg_label_changes`](https://furuse.work/ops/emproof/inject/seg_label_changes.html) · [`seg_membrane_chord_score`](https://furuse.work/ops/emproof/suspect/seg_membrane_chord_score.html) · [`seg_membrane_response`](https://furuse.work/ops/emproof/response/seg_membrane_response.html)

## No.2026.129 —— Motor Quantisation — Where the Command Dimension Collapses Between Brain and Muscle (the Fly's Neck and an RL Policy's Joints on One Scale)

[![Motor Quantisation — Where the Command Dimension Collapses Between Brain and Muscle (the Fly's Neck and an RL Policy's Joints on One Scale)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/03_activity_flow.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/03_activity_flow.gif)

*↑ **Motor Quantisation — Where the Command Dimension Collapses Between Brain and Muscle (the Fly's Neck and an RL Policy's Joints on One Scale)** ―― You do not think about individual muscles when you raise an arm: the tens of thousands of brain states must be folded into a few commands somewhere, and in the fly that somewhere is visible in the wiring — MaleCNS v1.0 (Janelia, CC BY 4.0): 32,164 central-brain interneurons → the narrow neck of 1,314 descending neurons (DN) → 13,161 nerve-cord interneurons → 708 motor neurons (MN). With four ops added to conngraph (graph_layer_propagate / graph_block_shuffle / states_participation_ratio / states_layer_dimension) the brain → DN → VNC → MN subgraph (4,022 neurons) is driven by 400 random sparse stimuli and the effective dimension of each layer's states (participation ratio, Gao et al. 2017) is read. With sparse firing (kWTA 10 %) it falls monotonically 282 > 61 > 8.7 > 2.4; picking 708 columns of the brain states still gives 249, so the fall is not the layer size. A control that keeps every receiver's input weights but shuffles who sends them leaves the MN at 21.9 — the VNC → muscle stage compresses by the specific wiring, while the neck (DN) stage matches the control (61 vs 62) and compresses by convergence alone. Honest breakdown: the raw PR is also pulled by a heavy tail (a few stimuli drive the MN 17× harder than the median), so the direction-only dimension (every response scaled to unit norm) was measured too — real wiring 25 vs control 54 (kWTA), 7 vs 42 (linear). The same formula on Physical AI: joint trajectories of the G1 humanoid's RL walking and running score 2.4–4.1 (median 3.2), dance 9.3, fight 11.9, and 73 evis muscle activations 6–9. An order-of-magnitude comparison, not a claim of identity. Raw data and subgraphs are never committed.*

[![effective dimension of the states each layer takes under 400 random sparse stimuli of the brain layer: real wiring vs a ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/01_funnel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/01_funnel.png)

*↑ The measurement ―― effective dimension of the states each layer takes under 400 random sparse stimuli of the brain layer: real wiring vs a control that keeps every receiver's input weights but shuffles who sends them; the neck (DN) compresses by convergence alone, the VNC -> MN stage compresses by the specific wiring (figure labels are in Japanese; the numbers are the same)*

[![the same funnel after every stimulus response is scaled to unit norm (magnitude removed, direction k](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/02_funnel_direction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/02_funnel_direction.png)

*↑ the same funnel after every stimulus response is scaled to unit norm (magnitude removed, direction kept): the real wiring still leaves fewer MN direct…*

[![the 400 stimuli projected on the first two principal components of the MN states: real wiring folds ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/04_command_space_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/04_command_space.png)

*↑ the 400 stimuli projected on the first two principal components of the MN states: real wiring folds them onto a few directions, the shuffled control s…*

[![participation ratio of joint-angle trajectories (G1 humanoid, RL policies and mocap retargets) and o](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/05_physical_ai_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/05_physical_ai.png)

*↑ participation ratio of joint-angle trajectories (G1 humanoid, RL policies and mocap retargets) and of muscle activations (evis), next to the fly's MN…*

[![every number, with the bar it had to clear](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/06_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/06_numbers.png)

*↑ every number, with the bar it had to clear*

```
py -3.11 examples/poc_connectome_motor_bottleneck.py
```

Source: [examples/poc_connectome_motor_bottleneck.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_connectome_motor_bottleneck.py)

This run produced **6 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck)

Ops used (notes): [`graph_block_shuffle`](https://furuse.work/ops/conngraph/dimension/graph_block_shuffle.html) · [`graph_layer_propagate`](https://furuse.work/ops/conngraph/dimension/graph_layer_propagate.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`states_layer_dimension`](https://furuse.work/ops/conngraph/dimension/states_layer_dimension.html) · [`states_participation_ratio`](https://furuse.work/ops/conngraph/dimension/states_participation_ratio.html)

## No.2026.131 —— The MICrONS Brain Wave — How Much of the Measured Response Does the Wiring Explain in 1 mm^3 of Visual Cortex

[![The MICrONS Brain Wave — How Much of the Measured Response Does the Wiring Explain in 1 mm^3 of Visual Cortex](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/01_brain_wave.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/01_brain_wave.gif)

*↑ **The MICrONS Brain Wave — How Much of the Measured Response Does the Wiring Explain in 1 mm^3 of Visual Cortex** ―― MICrONS (about 1 mm^3 of mouse V1 plus higher visual areas) is the rare dataset that holds both the electron-microscopy wiring and the two-photon activity of the same neurons. The public tables of Ding et al. 2025 (Nature) — 12,894 neurons with soma position, visual area and a 120-frame trial-averaged response to a natural movie, and 1.69 M pairs from 148 proofread axons (Connected 8,128 / ADP = axon and dendrite touch without a synapse 287 k / Same region 1.40 M) — are read without committing the raw data or the subgraph. The measured responses are shown as they are, a brain wave over the 1 mm^3 turned by points_activity_video (a cell lights only when it is in its own top quartile), and three rulers measure how much of that wave the wiring explains. (1) Like-to-like reproduced: signal correlation is Connected 0.071 > ADP 0.045 > Same region 0.025, and against a permutation null that shuffles the labels within each axon (sd 0.0018) the difference of 0.027 is 15 sd; ADP and Connected pairs have the same soma distance (289 vs 295 um), so ADP is the distance-matched control. (2) Wiring adds to proximity: the correlation of each axon's response with the mean response of its partners (a similarity on the same 120 frames, not a held-out prediction) is 0.24 for the connected ones, 0.18 for the same number of touching-but-unconnected ones and 0.12 for the same number of same-region ones; per axon, the connected partners win 73 % of the time. (3) The wave on the wiring: the 148 measured responses driven through the conngraph reservoir of a 4,096-node subgraph (269 axon-to-axon edges dropped) give a correlation of 0.085 between the one-step-delayed target states and the measured responses, above all 20 degree-preserving shuffles (mean 0.048 ± 0.002, max 0.053), with the same order at 0.3× and 3× gain. Honest breakdown: the absolute value is small — a one-hop graph with 1.8 inputs per target from 148 proofread axons — and the spread of the wave (mean distance from the axons 316 um) equals the control: spatial locality is already in the candidate set (ADP), not in who gets chosen. Without the data a synthetic cortex (8 latent signals plus like-to-like wiring among neighbours) runs the same steps and only the orderings are asserted.*

[![signal correlation of the in vivo responses: pairs in the same region binned by soma distance (curve), against the means](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/02_like_to_like_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/02_like_to_like.png)

*↑ The measurement ―― signal correlation of the in vivo responses: pairs in the same region binned by soma distance (curve), against the means of the connected pairs and of the ADP pairs whose axon and dendrite touch without a synapse; the per-axon permutation null of Connected - ADP has sd 0.0018 (figure labels are in Japanese; the numbers are the same)*

[![each axon's response predicted from the mean response of its connected partners (y) versus the same ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/03_wiring_vs_proximity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/03_wiring_vs_proximity.png)

*↑ each axon's response predicted from the mean response of its connected partners (y) versus the same number of touching-but-unconnected partners (x): a…*

[![every number, with the bar it had to clear](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/05_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/05_numbers.png)

*↑ every number, with the bar it had to clear*

[![the measured responses of the 148 proofread axons (pale yellow) driven through the reservoir of the 4096-node connected ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif)

*↑ The animation ―― the measured responses of the 148 proofread axons (pale yellow) driven through the reservoir of the 4096-node connected subgraph over all somata (grey): a target lights when the drive it receives through its real synapses is in its own top quartile; correlation of the reservoir states with the measured responses 0.085 vs 0.048 for a degree-preserving shuffle*

```
py -3.11 examples/poc_microns_brain_wave.py
```

Source: [examples/poc_microns_brain_wave.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_microns_brain_wave.py)

This run produced **5 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_microns_brain_wave)

Ops used (notes): [`graph_activity_spread`](https://furuse.work/ops/conngraph/activity/graph_activity_spread.html) · [`graph_degree_preserving_shuffle`](https://furuse.work/ops/conngraph/construct/graph_degree_preserving_shuffle.html) · [`graph_from_synapses`](https://furuse.work/ops/conngraph/construct/graph_from_synapses.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`reservoir_states`](https://furuse.work/ops/conngraph/reservoir/reservoir_states.html)

## No.2026.132 —— Branch Territories — Handing Every Voxel Its Nearest Branch, Not Just Its Distance, Makes Per-Branch Volume and Radius Countable

[![Branch Territories — Handing Every Voxel Its Nearest Branch, Not Just Its Distance, Makes Per-Branch Volume and Radius Countable](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/02_territory_turning.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/02_territory_turning.gif)

*↑ **Branch Territories — Handing Every Voxel Its Nearest Branch, Not Just Its Distance, Makes Per-Branch Volume and Radius Countable** ―― A neuron cut out of serial EM sections becomes a graph of branches once skeletonised, but the per-branch volume and radius that morphometry needs (the compartment parameters of cable theory) can only be counted after every voxel of the volume is told which branch it belongs to. A distance transform returns how far the nearest skeleton is (a value) and discards which skeleton voxel is nearest (a direction), so on its own it cannot draw branch territories. On a synthetic dendrite with true branch labels (5 branches of different radius, one detached piece, 6 debris blobs), the pieces are held per component by vol_rle_components and selected by volume (8 components, 2 kept, 6 debris dropped), the branch ids of skeletonize_vol -> skeleton_branches3d are placed on the skeleton, and vol_nearest_label hands every voxel the id of its nearest branch (a Voronoi partition) which is then cut to the piece: the territories agree with the true nearest axis on 0.978 of the voxels and the per-branch volumes are within 2.9 %. The radius from vol_nearest_seed_vector (surface-to-skeleton displacement) plus 0.5 (the surface voxel centre sits half a voxel inside the boundary) is within 0.24 voxel for every branch, the same accuracy as the classic distance transform on the skeleton (0.23 voxel), but this one gives a radius at every surface voxel. The value-only classic (carve balls around the junctions, then connected components) either fails to separate the branches when the ball is small (agreement 0.63-0.65 for r = 0-4) or throws volume away when it is large (0.78 at r = 6 with 22 % unassigned) - the evidence that the direction is needed. Honest breakdown: skeleton branches end at every junction, so the trunk becomes three branch ids (9 ids onto 6 true branches, matched by majority overlap), and the +0.5 on the radius is a known discretisation bias added explicitly.*

[![z projection of the synthetic dendrite: every voxel gets the branch whose skeleton is nearest, so the branch volumes can](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/01_territories_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/01_territories.png)

*↑ The measurement ―― z projection of the synthetic dendrite: every voxel gets the branch whose skeleton is nearest, so the branch volumes can be counted; cutting balls around the junctions instead either fails to separate the branches or throws volume away (figure labels are in Japanese; the numbers are the same)*

[![both readings recover the radius of every branch to within half a voxel (the surface voxel centre si](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/03_radius_recovery_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/03_radius_recovery.png)

*↑ both readings recover the radius of every branch to within half a voxel (the surface voxel centre sits half a voxel inside the boundary, hence the +0.…*

[![volume per branch comes from the territory; the junction-cut rows show that no ball radius separates](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/04_branch_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/04_branch_numbers.png)

*↑ volume per branch comes from the territory; the junction-cut rows show that no ball radius separates the branches without throwing volume away*

```
py -3.11 examples/poc_em_branch_territory.py
```

Source: [examples/poc_em_branch_territory.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_em_branch_territory.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_em_branch_territory)

Ops used (notes): [`identity`](https://furuse.work/ops/2d/misc/identity.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`skeleton_branches3d`](https://furuse.work/ops/3d/medial/skeleton_branches3d.html) · [`skeleton_graph3d`](https://furuse.work/ops/3d/medial/skeleton_graph3d.html) · [`skeletonize_vol`](https://furuse.work/ops/3d/medial/skeletonize_vol.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_nearest_label`](https://furuse.work/ops/3d/medial/vol_nearest_label.html) · [`vol_nearest_seed_vector`](https://furuse.work/ops/3d/medial/vol_nearest_seed_vector.html) · [`vol_rle_components`](https://furuse.work/ops/3d/rle_region/vol_rle_components.html) · [`vol_rle_decode`](https://furuse.work/ops/3d/rle_region/vol_rle_decode.html) · [`vol_rle_volume`](https://furuse.work/ops/3d/rle_region/vol_rle_volume.html)

### The Astronomy and Environment Wing — Biased by Position, Flipped by the Definition of Truth

Stellar brightness and position, the solar limb, all-sky cloud cover, sea-ice concentration, crop cover, terrain, river stage. The subjects are far away and ground truth is normally out of reach. The eight exhibits here turn that around, placing their truth in closed forms and public data: celestial coordinates, the solid angle of a spherical cap, Eddington limb darkening, elevation tiles from the Geospatial Information Authority of Japan.

The shared finding is that the same object reads differently depending on where it is: the same cloud counts 1.45x more at the horizon than at the zenith; clouds of equal optical thickness are detected or not depending on their angular distance from the sun; the same reflection makes one detector read quietly low and another stop silently.

The other is that the definition of truth decides the conclusion. Counting thin ice as 'ice' or not sends the same estimate to -4.4 or +2.7 points; a cloud fraction reported without its horizon-mask angle can legitimately claim anything from 0.18 to 0.23. What you call the truth has to be written down before the instrument is.

## No.2026.001 —— All-Sky Cloud Cover — Counting Pixels Is Biased by Position

[![All-Sky Cloud Cover — Counting Pixels Is Biased by Position](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/03_mask_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/03_mask_sweep.png)

*↑ **All-Sky Cloud Cover — Counting Pixels Is Biased by Position** ―― Spherical-cap clouds (closed-form solid angle) placed in an equidistant fisheye sky, with cloud fraction counted by pixel ratio and by solid-angle weight. The same cloud reads 0.00789 at the zenith and 0.01142 at 82 degrees (1.45x). Geometry alone errs by -5.02 %, detection alone by +37.95 %, and the naive count cancels them to +29.73 %.*

[![画素数比は天頂で 0.81、地平線側で 1.17。重みを掛けると 1 に張り付く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/01_jacobian_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/01_jacobian.png)

*↑ The measurement ―― 画素数比は天頂で 0.81、地平線側で 1.17。重みを掛けると 1 に張り付く。 (figure labels are in Japanese; the numbers are the same)*

[![偽陽性は実測と閉形式が重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/02_rbr_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/02_rbr_threshold.png)

*↑ 偽陽性は実測と閉形式が重なる。*

[![4 枚目が sinθ/θ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/04_allsky_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/04_allsky.png)

*↑ 4 枚目が sinθ/θ。*

```
py -3.11 examples/poc_allsky_cloud_cover.py
```

Source: [examples/poc_allsky_cloud_cover.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_allsky_cloud_cover.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_allsky_cloud_cover)

Ops used (notes): [`polar_trans_image`](https://furuse.work/ops/2d/geometry/polar_trans_image.html)

## No.2026.002 —— How Many Frames for What Photometric Precision?

[![How Many Frames for What Photometric Precision?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/01_stack_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/01_stack_scaling.png)

*↑ **How Many Frames for What Photometric Precision?** ―― A star field placed to specification and stacked N deep, to see whether aperture-photometry error falls as 1/√N. From N = 1 to 16 the median error drops from 0.6350 % to 0.1616 %, within 4.6 % of theory in all eight cases. One cosmic ray pushes the plain mean to +5.89 % while κ-σ clipping holds +0.30 %; the rejection rate does not move, so 'the rejection rate went up, therefore it worked' is not an available argument.*

[![単純平均だけが 5.9 % 残る。κ-σ は汚染なしと区別できないところまで戻すが、棄却率はほとんど動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/02_cosmic_ray_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/02_cosmic_ray.png)

*↑ The measurement ―― 単純平均だけが 5.9 % 残る。κ-σ は汚染なしと区別できないところまで戻すが、棄却率はほとんど動かない。 (figure labels are in Japanese; the numbers are the same)*

[![開口を広く取れるなら、ぼけたフレームも同じ明るさを持っている(r=12 では 3 本が重なる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/03_aperture_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/03_aperture_tradeoff.png)

*↑ 開口を広く取れるなら、ぼけたフレームも同じ明るさを持っている(r=12 では 3 本が重なる)。*

[![悪いほうは星が広がっている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/04_lucky_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/04_lucky_frames.png)

*↑ 悪いほうは星が広がっている。*

```
py -3.11 examples/poc_astro_photometry.py
```

Source: [examples/poc_astro_photometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_astro_photometry)

Ops used (notes): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`lucky_select`](https://furuse.work/ops/astrostack/quality/lucky_select.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`synth_frame_series`](https://furuse.work/ops/astrostack/synth/synth_frame_series.html) · [`synth_starfield`](https://furuse.work/ops/astrostack/synth/synth_starfield.html)

## No.2026.059 —— Change detection under misregistration — false positives are edge bands, with a cliff

[![Change detection under misregistration — false positives are edge bands, with a cliff](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/03_map_fp_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/03_map_fp_shift.png)

*↑ **Change detection under misregistration — false positives are edge bands, with a cliff** ―― A two-date synthetic land surface (fields, roads, buildings, forest, lake) with planted changes (new buildings, clear-cut, lake expansion); date 2 is degraded by sub-pixel shift, small rotation and an illumination change, and the false-positive area of plain differencing is measured. False positives stay at the noise floor up to 0.3 px and jump at 0.5 px (matching the PSF-derived onset δ*=τσ√2π/C=0.351 px), reaching 7175 px at 3 px. The edge-length × shift rule gives 0.78× at 3 px but cannot explain the cliff; the PSF+noise edge-ledger prediction is within 0.84–1.07×. Three registration paths (PIV, keypoints, LK) bring the residual down to 0.02–0.13 px, but the only phase-correlation path is 3-D and integer-valued (residual 0.72 px), and its 995 px of false positives lands on the shift-only sweep read at the same residual (915 px). Clear-cut recall is 0.33 even with perfect alignment; the illumination-only 17198 px vanish with radiometric normalisation while the 3497 px from shift do not.*

[![0.35 px までゼロ、そこから立ち上がる。比例則は崖を説明しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift.png)

*↑ The measurement ―― 0.35 px までゼロ、そこから立ち上がる。比例則は崖を説明しない。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/02_table_fp_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/02_table_fp_shift.png)

*↑ この回の図*

[![回転 1 度の偽陽性地図(橙)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/05_map_rotation_1deg_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/05_map_rotation_1deg.png)

*↑ 回転 1 度の偽陽性地図(橙)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/07_table_size_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/07_table_size_cliff.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/09_table_registration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/09_table_registration.png)

*↑ この回の図*

```
py -3.11 examples/poc_change_detection_misreg.py
```

Source: [examples/poc_change_detection_misreg.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_change_detection_misreg.py)

This run produced **11 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_change_detection_misreg)

Ops used (notes): [`affine_trans_image`](https://furuse.work/ops/2d/geometry/affine_trans_image.html) · [`histogram_match`](https://furuse.work/ops/colortransport/matching/histogram_match.html) · [`match_phase_3d`](https://furuse.work/ops/3d/match_pose/match_phase_3d.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_outlier_mask`](https://furuse.work/ops/piv/validate/piv_outlier_mask.html) · [`procrustes_fit`](https://furuse.work/ops/shapestat/procrustes/procrustes_fit.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## No.2026.096 —— A 3-D Thermal Field from Sparse Sensors — The Grid's Blind Spot Erases a Rack

[![A 3-D Thermal Field from Sparse Sensors — The Grid's Blind Spot Erases a Rack](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth.png)

*↑ **A 3-D Thermal Field from Sparse Sensors — The Grid's Blind Spot Erases a Rack** ―― A temperature field for a 12 x 8.4 x 3.0 m server room is written as a formula, then reconstructed from a grid of temperature sensors to find three overloaded racks. The null baseline, the mean of all sensors spread over the whole room, gives an RMSE of 2.192 degrees and finds no hot spot at all; the best method, a thin-plate RBF, gives 0.214, ten times better. The cliff can be stated in closed form before measuring: on a grid of spacing d the point furthest from a peak is the cell centre at d*sqrt(3)/2, so a Gaussian of width sigma is recovered at exp(-3d^2/8sigma^2) and halves at d* = 1.3596 sigma. Isolating the geometry, prediction and measurement differ by at most 1.2e-15. What failed was not the formula but the quantity a site can actually measure: the peak of a reconstructed field carries the background's reconstruction error at the same place, so a naive measurement exceeds the prediction by up to +0.2598 and the cliff looks shallower than it is. The sigma=0.22 m rack is recovered at 0.000014 at d=1.20 m, effectively gone, yet naively appears to hold 0.1609 — what remains is the background error. The closed form is a floor, not a curve: at the same d=0.60 m, recovery jumps from 0.0615 at a cell centre to 1.0 directly above a sensor, so only the worst phase is usable for design. Random placement does not remove blind spots; it only reshuffles which rack falls into one. Measured, 6.17 % of random points exceed the grid's worst distance against a Poisson prediction of 6.58 %. The grid never breaks its geometric lower bound while random placement broke it for two of the three racks: with the same sensor count, only one of them supports a guarantee. Swapping the interpolator moves the coefficient, not the exponent — all three slopes of log recovery against d^2 sit within 3.05 % of the predicted -3.0612 — but the prediction that the cliff position is method-independent was wrong: the thin-plate spline overshoots its own nodes by a factor of 1.372 and shifts the half-recovery spacing from 0.4777 to 0.6015 m, a 26 % move. The follow-up prediction, that an overshooting method raises the false peaks by the same factor, was also wrong: the nearest-neighbour floor is 0.975 degrees, 6.5 times the sensor noise, because a staircase approximation of a smooth background is itself a step. No method wins all three rulers at once, and at d=1.20 m linear interpolation falls outside the convex hull for 71.2 % of the evaluation points, silently becoming nearest-neighbour at the walls. The gap this PoC found has since been filled: fs.interp_scattered interpolates a field from scattered N-D points and returns the fraction of query points that fell outside the convex hull — the 71.2 % measured here is exactly the quantity that would otherwise turn silently into NaN or into another method under the first method's name.*

[![幾何の実測は予測と最大 1.2e-15 しか違わない。素朴な実測が上に浮くぶんが背景の復元誤差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/02_cliff_prediction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/02_cliff_prediction.png)

*↑ The measurement ―― 幾何の実測は予測と最大 1.2e-15 しか違わない。素朴な実測が上に浮くぶんが背景の復元誤差。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/03_cliff_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/03_cliff_table.png)

*↑ この回の図*

[![格子の最悪距離 0.520 m を乱数の 6.17 % が超えた(予測 6.58 %)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/04_grid_vs_random_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/04_grid_vs_random.png)

*↑ 格子の最悪距離 0.520 m を乱数の 6.17 % が超えた(予測 6.58 %)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/06_metric_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/06_metric_table.png)

*↑ この回の図*

[![横=x 0..12 m、縦=y 0..8.4 m。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/07_map_reconstruction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/07_map_reconstruction.png)

*↑ 横=x 0..12 m、縦=y 0..8.4 m。*

```
py -3.11 examples/poc_datacenter_thermal_field.py
```

Source: [examples/poc_datacenter_thermal_field.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_datacenter_thermal_field.py)

This run produced **8 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_datacenter_thermal_field)

Ops used (notes): [`interp_scattered`](https://furuse.work/ops/math/interp_poly/interp_scattered.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html)

## No.2026.012 —— Measuring Terrain — Slope, Flow and Insolation Against Closed Forms

[![Measuring Terrain — Slope, Flow and Insolation Against Closed Forms](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/01_cone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/01_cone.png)

*↑ **Measuring Terrain — Slope, Flow and Insolation Against Closed Forms** ―― Slope, curvature and sky-view factor checked against closed forms on a plane, a cone and a Gaussian hill. Halving the cell size cuts the hill's curvature error by about four — a discretisation error, not a wrong formula. The sky-view factor takes 2.03 s on a 513×513 grid with 8 directions; before the rewrite it took 41.9 s, and the tests had only ever checked that it runs.*

[![参照線と平行 = 2 次収束 = 離散化の誤差。式が違えばセルを細かくしても誤差は下げ止まる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/02_curvature_convergence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/02_curvature_convergence.png)

*↑ The measurement ―― 参照線と平行 = 2 次収束 = 離散化の誤差。式が違えばセルを細かくしても誤差は下げ止まる。 (figure labels are in Japanese; the numbers are the same)*

[![同じ地形・同じ op。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/03_nodata_policies_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/03_nodata_policies.png)

*↑ 同じ地形・同じ op。*

[![陰影の平均は 北向き 0.354 / 東向き 0.811 / 南向き 0.811 / 西向き 0.354。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/04_hillshade_aspect_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/04_hillshade_aspect.png)

*↑ 陰影の平均は 北向き 0.354 / 東向き 0.811 / 南向き 0.811 / 西向き 0.354。*

```
py -3.11 examples/poc_dem_terrain.py
```

Source: [examples/poc_dem_terrain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dem_terrain)

Ops used (notes): [`dem_aspect`](https://furuse.work/ops/dem/surface/dem_aspect.html) · [`dem_curvature`](https://furuse.work/ops/dem/surface/dem_curvature.html) · [`dem_fill_sinks`](https://furuse.work/ops/dem/hydrology/dem_fill_sinks.html) · [`dem_flow_accumulation`](https://furuse.work/ops/dem/hydrology/dem_flow_accumulation.html) · [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_sky_view_factor`](https://furuse.work/ops/dem/visibility/dem_sky_view_factor.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html)

## No.2026.066 —— Exoplanet transit from aperture photometry — depth and duration fail separately

[![Exoplanet transit from aperture photometry — depth and duration fail separately](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/01_scene_starfield_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/01_scene_starfield.png)

*↑ **Exoplanet transit from aperture photometry — depth and duration fail separately** ―― A synthetic star field (240 frames) carries a 10 ppt limb-darkened transit on the target only, with transparency variation, sub-pixel drift, flat-field non-uniformity and photon noise injected from separate random streams; fullseye's star_detect → frame_align → aperture_photometry extracts the light curve. The zero point (target aperture sum alone) breaks under clouds to a depth error of +72 ppt; the ratio to comparison stars gives -0.13 ppt / T14 -0.9 fr. Comparison-star choice moves the residual rms from 1.91 to 11.43 ppt (6.0x), and inverse-variance weights computed from raw variance are fooled by clouds into 1.52x worse than a plain sum. The small-aperture cliff at 1σ was not the predicted centroid error but the op's aperture-mask staircase (supersample=8: a static star sits 1.69x above theory, 0.93x at 32). The SNR=5 detection limit is 1.48 ppt measured vs 1.45 ppt theory with a known ephemeris, 2.0 ppt blind, where the duration breaks before the depth. Drift 2 px and a 3 % flat are harmless alone (0.16 / 0.08 ppt) but multiply into a 0.94 ppt false depth, 2.97 ppt (30 % of truth) at 4 px.*

[![前/入/最深部/出/後の各段階で平均した画像からトランジット外の平均を引いた [e-)。4 倍拡大](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/02_frames_transit_phases_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/02_frames_transit_phases.png)

*↑ The measurement ―― 前/入/最深部/出/後の各段階で平均した画像からトランジット外の平均を引いた [e-]。4 倍拡大 (figure labels are in Japanese; the numbers are the same)*

[![ゼロ点と比較星の和は雲(全星共通)そのもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/03_lightcurve_zero_vs_relative_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/03_lightcurve_zero_vs_relative.png)

*↑ ゼロ点と比較星の和は雲(全星共通)そのもの。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/05_comparison_choice_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/05_comparison_choice.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/07_aperture_depth_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/07_aperture_depth_bias.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/09_depth_cliff_t14_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/09_depth_cliff_t14.png)

*↑ この回の図*

```
py -3.11 examples/poc_exoplanet_transit.py
```

Source: [examples/poc_exoplanet_transit.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_exoplanet_transit.py)

This run produced **11 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_exoplanet_transit)

Ops used (notes): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`frame_align`](https://furuse.work/ops/astrostack/align/frame_align.html) · [`normalize`](https://furuse.work/ops/shape2d/descriptor/normalize.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html)

## No.2026.098 —— Coordinates Go Wrong by Tens of Metres While Still Looking Plausible

[![Coordinates Go Wrong by Tens of Metres While Still Looking Plausible](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames.png)

*↑ **Coordinates Go Wrong by Tens of Metres While Still Looking Plausible** ―― GNSS returns an ellipsoidal height; maps and drawings use an orthometric one, and the two differ by the geoid undulation — 30 to 40 m around Japan. This exhibit plants a synthetic geoid field and measures which quantities that confusion reaches and which ones it cancels out of. The floor is taken twice: the round trip of the existing operators closes to 1.07e-06 m, and an independent iterative implementation agrees to 7.2e-07 m in latitude — because a round trip alone cannot rule out both directions being wrong the same way. Several closed forms landed: the bound on slope error, atan|grad N|, predicted 0.008771 degrees against 0.008600 measured, with the constant-undulation control at 2.0e-14 degrees, which is exactly zero; the volume error A times the mean undulation agreed to 1.5e-08 cubic metres; the fraction of flat ground whose flow direction reverses was predicted at 76.1 % and measured at 76.2 %. One prediction was badly wrong: the bound on line-of-sight clearance was set at 2.60 m and measured 0.052 m, fifty times smaller, because the linear part of the undulation rides on the sight line and the ground equally and cancels; Earth curvature matters 276 times more. The flat-earth cliff has a closed form but not a single number — at 10 km the prediction of -7.8481 m brackets measurements of -7.8652 m north-south and -7.8303 m east-west, the difference between the meridional and prime-vertical radii. The theme is that the same 36 m is everything or nothing depending on the quantity: it nearly vanishes from differences and survives whole in absolutes, changing an earthwork volume by 3.97e+07 cubic metres and a flooded area from 41.9 % to zero. A control where the design surface is built from the same GNSS shows zero error — a contaminated ruler applied to a contaminated object hides the error. A datum mix-up shifts positions by 446.6 m on average while a relative check between baselines shows only 0.106 m per kilometre, four thousand times less; the danger is not the size but the plausibility. Counting quiet failures against loud ones over a 3600-point global grid, the only mistake that raises is swapping latitude and longitude, and only half the time; radians-for-degrees, a flipped longitude sign, swapped ECEF axes (whose results land in a valid latitude and longitude range 100 % of the time) and feet-for-metres all pass silently. Ten of eleven entries fail quietly. Along the way a real defect was found and fixed: near the Earth's centre the ECEF-to-geodetic conversion returned a latitude of 180 degrees — a value that does not exist, and one its own inverse rejects.*

[![分母 58081 セル。真値 24325(41.9 %)に対し、誤用は 0 と 58081。**どちらの絵も「もっともらしい」**(全面浸水は津波の図に見える)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/02_flood_masks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/02_flood_masks.png)

*↑ The measurement ―― 分母 58081 セル。真値 24325(41.9 %)に対し、誤用は 0 と 58081。**どちらの絵も「もっともらしい」**(全面浸水は津波の図に見える)。 (figure labels are in Japanese; the numbers are the same)*

[![真の勾配の中央値 9.15e-05 に対し |∇N| は 1.2e-04。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/03_flow_flip_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/03_flow_flip.png)

*↑ 真の勾配の中央値 9.15e-05 に対し |∇N| は 1.2e-04。*

[![2.5 cm/年(代表値)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/05_epoch_drift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/05_epoch_drift.png)

*↑ 2.5 cm/年(代表値)。*

[![真の ECEF(dem_geodetic_to_ecef)を自前の ENU 回転に通して測った。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/08_enu_drop_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/08_enu_drop.png)

*↑ 真の ECEF(dem_geodetic_to_ecef)を自前の ENU 回転に通して測った。*

[![全球 3600 点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/11_axis_order_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/11_axis_order.png)

*↑ 全球 3600 点。*

```
py -3.11 examples/poc_geodetic_height_frames.py
```

Source: [examples/poc_geodetic_height_frames.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_height_frames.py)

This run produced **13 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_geodetic_height_frames)

Ops used (notes): [`dem_aspect`](https://furuse.work/ops/dem/surface/dem_aspect.html) · [`dem_datum_shift_3param`](https://furuse.work/ops/dem/geodesy/dem_datum_shift_3param.html) · [`dem_earth_curvature_drop`](https://furuse.work/ops/dem/geodesy/dem_earth_curvature_drop.html) · [`dem_ecef_to_geodetic`](https://furuse.work/ops/dem/geodesy/dem_ecef_to_geodetic.html) · [`dem_enu_from_geodetic`](https://furuse.work/ops/dem/geodesy/dem_enu_from_geodetic.html) · [`dem_flow_direction`](https://furuse.work/ops/dem/hydrology/dem_flow_direction.html) · [`dem_geodetic_from_enu`](https://furuse.work/ops/dem/geodesy/dem_geodetic_from_enu.html) · [`dem_geodetic_to_ecef`](https://furuse.work/ops/dem/geodesy/dem_geodetic_to_ecef.html) · [`dem_geoid_height`](https://furuse.work/ops/dem/geodesy/dem_geoid_height.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`median`](https://furuse.work/ops/2d/rank/median.html)

## No.2026.068 —— Leaf disease severity — colour axes survive the lighting; the grade is decided by the leaf mask and the edge convention

[![Leaf disease severity — colour axes survive the lighting; the grade is decided by the leaf mask and the edge convention](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/01_scene.png)

*↑ **Leaf disease severity — colour axes survive the lighting; the grade is decided by the leaf mask and the edge convention** ―― A closed-form leaf outline with lesions of known area, over soil, side lighting, clipped highlights and a shadow, gives ground truth for disease severity (lesion pixels / leaf pixels). A fixed threshold on the green channel (the zero point) is off by +65.2 pt with soil alone; cutting the leaf with the illuminant-projected G and the lesions with Lab a* lands at -0.8 pt on the standard scene. Illumination falloff up to 50 % does not move a*, but clipped highlights produce only false positives for a* (+12.6 pt at 20 % coverage, 0.0 false negatives) versus +2.0 pt for hue, which is invariant to added white. With a 4 px soft lesion edge, choosing the 25 % or 75 % opacity contour as the boundary alone shifts the severity by ±3.5 pt (predicted within 0.4 pt by Steiner's formula), and of 40 images placed within ±3 pt of a grade boundary, 19-35 are misgraded on soil by every method — on black cloth with a brightness leaf mask, a fixed hue threshold misgrades 8.*

[![FN(青)の大きな塊は影と鏡面反射が重なった病斑(葉マスクごと落ちる)。FP(赤)は鏡面反射の下と病斑の縁。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/02_error_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/02_error_map.png)

*↑ The measurement ―― FN(青)の大きな塊は影と鏡面反射が重なった病斑(葉マスクごと落ちる)。FP(赤)は鏡面反射の下と病斑の縁。 (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/03_frames_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/03_frames_conditions.png)

*↑ この回の図*

[![ゼロ点は固定しきい値を葉が割る列から予測できる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/04_cliff_illumination_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/04_cliff_illumination.png)

*↑ ゼロ点は固定しきい値を葉が割る列から予測できる。*

[![色相は白を足しても動かない(定義)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/06_cliff_specular_amplitude_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/06_cliff_specular_amplitude.png)

*↑ 色相は白を足しても動かない(定義)。*

[![予測の崖 1.8 px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/08_cliff_lesion_size_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/08_cliff_lesion_size.png)

*↑ 予測の崖 1.8 px。*

```
py -3.11 examples/poc_leaf_disease_area.py
```

Source: [examples/poc_leaf_disease_area.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leaf_disease_area.py)

This run produced **9 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_leaf_disease_area)

Ops used (notes): [`access_channel`](https://furuse.work/ops/2d/color/access_channel.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`reg_close`](https://furuse.work/ops/2d/region/reg_close.html) · [`reg_erode`](https://furuse.work/ops/2d/region/reg_erode.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html) · [`select_largest`](https://furuse.work/ops/2d/region/select_largest.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`specular_free_transform`](https://furuse.work/ops/specular/dichromatic/specular_free_transform.html) · [`srgb_to_linear`](https://furuse.work/ops/gfx2d/colorspace/srgb_to_linear.html) · [`trans_from_rgb`](https://furuse.work/ops/2d/color/trans_from_rgb.html)

## No.2026.078 —— Drone Thermography of a PV Plant — You Think You Are Measuring Temperature Difference, but You Are Measuring Wind and Viewing Angle

[![Drone Thermography of a PV Plant — You Think You Are Measuring Temperature Difference, but You Are Measuring Wind and Viewing Angle](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/06_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/06_scene.png)

*↑ **Drone Thermography of a PV Plant — You Think You Are Measuring Temperature Difference, but You Are Measuring Wind and Viewing Angle** ―― A megawatt PV array synthesised from a closed-form steady-state heat balance, seeded with known electrical faults (an in-cell hotspot, a bypassed string) and with real-but-not-electrical temperature differences (shading, soiling). A hotspot dissipating 320 W/m² is 11.20 K before dilution yet reaches the camera as 4.23 K — and the dilution comes not from the lateral conduction we expected (x0.960) but from the camera (x0.511). A control scene containing no electrical fault at all still raises 6 blobs when the whole-image mean is the reference (1 healthy, 5 non-fault). The cliff is set by the minimum-area gate rather than the threshold: the hotspot disappears at 1.0 m/s of wind, matching the area-based prediction of 1.1 m/s while the peak-based prediction of 3.0 m/s is wrong. Row-to-row shading warms the sunlit cells of the same string by +4.68 K, only 0.87 K away from the genuine string fault at +5.55 K.*

[![「偽」= 故障でも影でも汚れでもない場所に出た塊。しきい値 3.0 K、風速 1.0 m/s。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/01_norm_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/01_norm_table.png)

*↑ The measurement ―― 「偽」= 故障でも影でも汚れでもない場所に出た塊。しきい値 3.0 K、風速 1.0 m/s。 (figure labels are in Japanese; the numbers are the same)*

[![U(v) = 1.75·(5.7 + 3.8v + h_rad)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/02_wind_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/02_wind_sweep.png)

*↑ U(v) = 1.75·(5.7 + 3.8v + h_rad)。*

[![半径 30 mm の熱源。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/03_gsd_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/03_gsd_sweep.png)

*↑ 半径 30 mm の熱源。*

[![ε(θ) は Fresnel(等価屈折率 1.8)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/04_angle_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/04_angle_sweep.png)

*↑ ε(θ) は Fresnel(等価屈折率 1.8)。*

[![風速 1.0 m/s、モジュールごとの中央値を基準。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/05_netd_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/05_netd_sweep.png)

*↑ 風速 1.0 m/s、モジュールごとの中央値を基準。*

```
py -3.11 examples/poc_pv_thermal_survey.py
```

Source: [examples/poc_pv_thermal_survey.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pv_thermal_survey.py)

This run produced **7 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pv_thermal_survey)

Ops used (notes): [`beer_lambert_transmittance`](https://furuse.work/ops/optics/glassbody/beer_lambert_transmittance.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`fresnel_dielectric`](https://furuse.work/ops/optics/interface/fresnel_dielectric.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`overlay_mask`](https://furuse.work/ops/annotate/overlay/overlay_mask.html) · [`surface_form_remove`](https://furuse.work/ops/roughness/prepare/surface_form_remove.html) · [`volume_downsample`](https://furuse.work/ops/3d/preprocess/volume_downsample.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html) · [`zoom_image_factor`](https://furuse.work/ops/2d/geometry/zoom_image_factor.html)

## No.2026.106 —— Planting Known Stars in a Real Deep Field — Contamination Lies About the Measurement and the Confidence in the Same Direction

[![Planting Known Stars in a Real Deep Field — Contamination Lies About the Measurement and the Confidence in the Same Direction](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/01_scene.png)

*↑ **Planting Known Stars in a Real Deep Field — Contamination Lies About the Measurement and the Confidence in the Same Direction** ―― Gaussian stars of known flux planted in the real background of the Hubble Deep Field (NASA/STScI, public domain) — the truth is certain because it was planted, and only the background is real. The real sky is not Gaussian: a robust spread of 1,474 e- against a plain standard deviation of 6,698 e- (4.54x), so taking std for noise reports a detection limit 4.5 times too generous. The background is not one number either, ranging 3,176 to 8,448 e- across 195 tiles of 64x64, which leaves up to 3.6 sigma of systematic error after a single global subtraction. Even in the emptiest thirty per cent of the field a fixed amount leaks into the aperture: recovery runs 4.38x at F = 2,000 e- and 1.058x at 100,000, and it is an addition rather than a factor — 1 + C/(F·frac) fits all five points to within 0.9 %, with C = 6,677 e-, a mere 3.0 % of background times effective area. Predicting first that the bias falls below 10 % from 67,521 e- and then measuring there gives 1.086 against the predicted 1.100. In crowded positions the order of magnitude changes, 341x down to 7.80x: a median is robust to outliers, but when half the field is contaminated the median is the contamination. The confidence lies in the same direction — the op reports an SNR of 19.2 where the closed form on the same background gives 4.2 — so gating on S/N passes the contaminated measurements first.*

[![開口 1 つあたり C = 6677 e- の足し算として説明できる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/02_recovery_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/02_recovery.png)

*↑ The measurement ―― 開口 1 つあたり C = 6677 e- の足し算として説明できる。 (figure labels are in Japanese; the numbers are the same)*

[![SNR は測ったフラックスから作るので、混入で分子が膨らむと S/N も膨らむ(F=2000 で 19.2 対 4.2)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/03_snr_lies_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/03_snr_lies.png)

*↑ SNR は測ったフラックスから作るので、混入で分子が膨らむと S/N も膨らむ(F=2000 で 19.2 対 4.2)。*

[![混雑側は桁が変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/04_recovery_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/04_recovery_table.png)

*↑ 混雑側は桁が変わる。*

```
py -3.11 examples/poc_real_sky_photometry.py
```

Source: [examples/poc_real_sky_photometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_sky_photometry.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_sky_photometry)

Ops used (notes): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html)

## No.2026.080 —— River surface velocity from an oblique video (LSPIV) — velocity error and discharge error are different numbers

[![River surface velocity from an oblique video (LSPIV) — velocity error and discharge error are different numbers](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/01_scene.png)

*↑ **River surface velocity from an oblique video (LSPIV) — velocity error and discharge error are different numbers** ―― A power-law surface velocity profile (8 m wide, 1.5 m/s peak) is the ground truth; foam tracers are advected frame by frame and imaged for 60 frames by an oblique bank camera with a known homography, with sky reflection, ripples and noise injected separately. fullseye's piv_cross_correlate → warp_by_plane (orthorectification) → piv_to_velocity yields u(y) and discharge Q = h∫u dy. The zero point (correlate the oblique frames, convert with one scale) errs +0.31 m/s near bank and -0.28 m/s far bank, the apparent width collapses to 3.3 m and Q is -57 %. Orthorectification gives 0.074 m/s RMS and Q -7.8 %, yet even the control group's Q -3.0 % is mostly (-2.5 %) the bank trapezoid rule, unrelated to velocity. The tracer-density cliff arrives as outliers, not NaNs (44 % flagged at 0.05 %; ensemble correlation does not rescue the lost windows). Widening the window smears the bank velocity by only -0.008 m/s, orders below the predicted window x gradient, while Q drifts from -1.1 to -7.0 %. Static reflections matter only when fine-grained: the estimate is first pulled (ratio 0.70) then pinned to zero (0.03), and a temporal median restores 0.998. The dt cliff is pair loss, not the quarter rule: removing the search limit leaves the cliff at the same k=4.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/02_frames_oblique_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/02_frames_oblique.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/03_map_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/03_map_speed.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/05_density_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/05_density_cliff.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/08_window_discharge_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/08_window_discharge.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/10_reflection_modes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/10_reflection_modes.png)

*↑ この回の図*

```
py -3.11 examples/poc_river_surface_velocity.py
```

Source: [examples/poc_river_surface_velocity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_river_surface_velocity.py)

This run produced **12 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_river_surface_velocity)

Ops used (notes): [`highpass_image`](https://furuse.work/ops/2d/frequency/highpass_image.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_ensemble_correlate`](https://furuse.work/ops/piv/estimate/piv_ensemble_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_outlier_mask`](https://furuse.work/ops/piv/validate/piv_outlier_mask.html) · [`piv_replace_outliers`](https://furuse.work/ops/piv/validate/piv_replace_outliers.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_to_velocity`](https://furuse.work/ops/piv/field/piv_to_velocity.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## No.2026.035 —— Sea-Ice Concentration — The Answer Depends on How Mixed Pixels Are Counted

[![Sea-Ice Concentration — The Answer Depends on How Mixed Pixels Are Counted](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/01_scene.png)

*↑ **Sea-Ice Concentration — The Answer Depends on How Mixed Pixels Are Counted** ―― Ice concentration from a PSF-blurred two-band ice/water image, by hard classification and by linear unmixing. Hard classification is off by -4.2 points, unmixing by +0.02. The bias is explained by the perimeter fraction (R² = 0.984) and crosses zero near a concentration of 0.49 — validate only there and it passes.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/02_bias_vs_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/02_bias_vs_threshold.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/03_bias_vs_concentration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/03_bias_vs_concentration.png)

*↑ この回の図*

[![下 3 段は端成分 5 % 誤差と薄氷 20 %(2 端成分の分解)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/04_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/04_summary.png)

*↑ 下 3 段は端成分 5 % 誤差と薄氷 20 %(2 端成分の分解)。*

```
py -3.11 examples/poc_sea_ice_concentration.py
```

Source: [examples/poc_sea_ice_concentration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sea_ice_concentration.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_sea_ice_concentration)

Ops used (notes): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html)

## No.2026.110 —— Sweep Width — One Number Measured from Aerial Images Decides Whether the Search Works

[![Sweep Width — One Number Measured from Aerial Images Decides Whether the Search Works](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/01_scene.png)

*↑ **Sweep Width — One Number Measured from Aerial Images Decides Whether the Search Works** ―― Measure the lateral range curve p(x) from aerial imagery — detection probability as a function of cross-track distance — and hand its area, W = integral of p dx, to the search plan as the sweep width. This is where image processing and decision-making meet in a single number. The definition itself is demonstrated first: four curves of different shape (the measured p, a rectangle of width W, a triangle of base 2W, and a bimodal curve that cannot see nadir) all scaled to the same area of 256.2 m detect 0.2559 / 0.2563 / 0.2556 / 0.2566 of targets scattered uniformly over a half-width of 500 m, every one within 0.8 sigma of the predicted 0.2562. The shape vanishes; only the area survives. The cliff sits at coverage C = W v t / A = 1, printed in closed form before measuring: min(1, C) = 1.0000 and 1 - exp(-C) = 0.6321, against a rectangular control measuring 1.0000 and 0.6348 (the excess comes from having a finite 64 tracks; the exact value is 0.6350). Four predictions were wrong. Feeding the real p into a parallel sweep gives only 0.8464, not 1.000, because min(1, C) assumes the rectangular definite range law and a curve with tails overlaps its neighbouring tracks. The flatter curve was expected to be the more rectangle-like and therefore stronger, but it was the weaker (0.7705 against 0.8464): rectangle-like means standing inside W without tails, not being flat — while under random search the two curves tie, since random search only sees area. Ground resolution was expected to fall towards the swath edge, but for a nadir-looking central projection it is constant to 0.0e+00 relative spread; what falls is cos^4 vignetting, atmosphere and off-axis blur (an f-theta lens would coarsen the edge by 2.132 times). And subtracting a global background does nothing, because dividing by the whole-frame median and sigma is an affine map that cannot change the ranking (174.4 to 172.0 m); only a per-location subtraction helps (239.6 m). The optimum altitude lands in the interior at 220 m with W = 258.1 +/- 4.0 m, though 220 and 300 m are honestly not resolved apart; with an aircraft whose speed scales as min(1, h/600) the optimum moves to 420 m, so lowering the altitude to raise W does not work. The chaperone here is the false-alarm count, which concentrates at nadir rather than at the edge (113 in the 0-32 m band, zero in the outermost) because targets and whitecaps dim through the same cos^4: the best-seen place barks the most. Moving only the threshold slides W from 406 m to 170 m, so a sweep width quoted without a false-alarm rate says nothing at all.*

[![半幅 500 m に一様に撒いた 400000 個。予測 W/2X = 0.2562、モンテカルロの標準偏差 0.0007。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/02_sweep_width_equivalence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/02_sweep_width_equivalence.png)

*↑ The measurement ―― 半幅 500 m に一様に撒いた 400000 個。予測 W/2X = 0.2562、モンテカルロの標準偏差 0.0007。 (figure labels are in Japanese; the numbers are the same)*

[![4 本とも面積 = W = 256 m。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/03_curve_shapes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/03_curve_shapes.png)

*↑ 4 本とも面積 = W = 256 m。*

[![完全平行は C=1 でちょうど 0 に落ちるが、実測の横距離曲線では 0.154 残る(裾が隣の航跡と重なるため)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/05_coverage_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/05_coverage_curves.png)

*↑ 完全平行は C=1 でちょうど 0 に落ちるが、実測の横距離曲線では 0.154 残る(裾が隣の航跡と重なるため)。*

[![だから走査幅は必ず誤検出率と対で報告する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/08_threshold_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/08_threshold_tradeoff.png)

*↑ だから走査幅は必ず誤検出率と対で報告する。*

[![3 本とも誤検出 1.0 件/枚。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/10_lateral_range_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/10_lateral_range_curves.png)

*↑ 3 本とも誤検出 1.0 件/枚。*

```
py -3.11 examples/poc_search_sweep_width.py
```

Source: [examples/poc_search_sweep_width.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_search_sweep_width.py)

This run produced **12 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_search_sweep_width)

Ops used (notes): [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`integrate_funct_1d`](https://furuse.work/ops/oned/function/integrate_funct_1d.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`ncc_locate`](https://furuse.work/ops/2d/matching/ncc_locate.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`photon_sample`](https://furuse.work/ops/photon/counting/photon_sample.html) · [`relative_illumination`](https://furuse.work/ops/optics/geometric/relative_illumination.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html) · [`tophat`](https://furuse.work/ops/2d/morphology/tophat.html) · [`vignette`](https://furuse.work/ops/gfx2d/post/vignette.html) · [`xsk_blob_log`](https://furuse.work/ops/2d/features/xsk_blob_log.html)

## No.2026.036 —— Where Is the Edge of a Limb-Darkened Disc? The 50 % Rule Reads the Radius Small

[![Where Is the Edge of a Limb-Darkened Disc? The 50 % Rule Reads the Radius Small](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/01_scene.png)

*↑ **Where Is the Edge of a Limb-Darkened Disc? The 50 % Rule Reads the Radius Small** ―― A limb-darkened solar disc seen through seeing, its radius measured by the 50 % rule, by gradient maximum and by model fitting. The prediction 'bias scales with the darkening coefficient' failed: at u = 0.8 the bias is -12.76 px (pure geometry predicts -13.14 px). The cancellation point near threshold 0.26, where blur appears to have no effect, moves to 0.38 when u changes.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/02_bias_vs_u_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/02_bias_vs_u.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/03_seeing_cancel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/03_seeing_cancel.png)

*↑ この回の図*

[![縁に載った黒点だけが効く(内側の黒点は縁の点列に入らない)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/04_sunspot_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/04_sunspot.png)

*↑ 縁に載った黒点だけが効く(内側の黒点は縁の点列に入らない)。*

```
py -3.11 examples/poc_solar_limb_darkening.py
```

Source: [examples/poc_solar_limb_darkening.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_limb_darkening.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_solar_limb_darkening)

Ops used (notes): [`edge_points`](https://furuse.work/ops/3d/edges/edge_points.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html)

## No.2026.037 —— To What Fraction of a Pixel Can a Star Be Located, and Where Is the Cliff?

[![To What Fraction of a Pixel Can a Star Be Located, and Where Is the Cliff?](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/03_starfield_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/03_starfield.png)

*↑ **To What Fraction of a Pixel Can a Star Be Located, and Where Is the Cliff?** ―― Stars rendered from known celestial coordinates, located by four methods and compared with the Fisher-information bound. At S/N 298 the centroid (null) sits at 5.56x the bound and the background-subtracted centroid at 1.03x; no method beats the bound. At the faint end the null appears to beat it (0.2790 px versus 0.3471 px), but with a sensitivity of 0.038 it is merely returning the rounded initial guess.*

[![暗い端で素の重心が下限を割って見えるのは「動かない推定器」だから(感度 0.038)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/01_snr_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/01_snr_sweep.png)

*↑ The measurement ―― 暗い端で素の重心が下限を割って見えるのは「動かない推定器」だから(感度 0.038)。 (figure labels are in Japanese; the numbers are the same)*

[![素の重心だけ FWHM に依らない(空の希釈)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/02_phase_systematic_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/02_phase_systematic.png)

*↑ 素の重心だけ FWHM に依らない(空の希釈)。*

[![混ぜた中央値は孤立星とも二重星とも違う「どこでもない値」。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/04_sky_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/04_sky_error.png)

*↑ 混ぜた中央値は孤立星とも二重星とも違う「どこでもない値」。*

```
py -3.11 examples/poc_star_astrometry.py
```

Source: [examples/poc_star_astrometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_star_astrometry.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_star_astrometry)

Ops used (notes): [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`psf_fit`](https://furuse.work/ops/astrostack/photometry/psf_fit.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html)

## No.2026.088 —— Counting tree rings and extracting the width series — ring count and width correlation fail separately

[![Counting tree rings and extracting the width series — ring count and width correlation fail separately](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/01_scene.png)

*↑ **Counting tree rings and extracting the width series — ring count and width correlation fail separately** ―― A 36-ring disc is synthesised in closed form with an off-centre pith, eccentric growth, circumferential wobble, wandering cracks, decay spots, grain texture and blur. A single-ray peak count (baseline) gets the ring count right in only 18 of 24 directions, yet the 6 wrong directions still give a width-series correlation of median 0.900. The consensus method (pith-centred polar unwrap, radius normalised by the disc edge, theta-median, 24 sector measure lines, median) returns exactly 36 rings, 0 missing, width correlation 0.996 (mean error 0.13 px). A 20 px pith error leaves the width correlation at 0.994: the cosine modulation lands on the radii (slope -14.9 px), not on the widths (-0.02 px); what it removes is the innermost rings (predicted 2 / measured 2). The thinnest ring is lost at 2.5 px (consensus) and 3.0 px (baseline), and at blur sigma 4 px the baseline counts 13 false rings.*

[![偏心成長で境界が θ とともに斜めに走るので、正規化しないとθ 窓の中で外側の年輪がにじむ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/02_polar_stages_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/02_polar_stages.png)

*↑ The measurement ―― 偏心成長で境界が θ とともに斜めに走るので、正規化しないとθ 窓の中で外側の年輪がにじむ。 (figure labels are in Japanese; the numbers are the same)*

[![展開図(横 = 半径 px、縦 = 角度)に、扇形ごとの測定線が拾った境界(赤、下)と真値(青、上)を重ねた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/03_polar_edges_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/03_polar_edges_map.png)

*↑ 展開図(横 = 半径 px、縦 = 角度)に、扇形ごとの測定線が拾った境界(赤、下)と真値(青、上)を重ねた。*

[![ゼロ点は θ=0 方向の局所幅なので偏心成長ぶん尺度がずれる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/04_ring_widths_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/04_ring_widths.png)

*↑ ゼロ点は θ=0 方向の局所幅なので偏心成長ぶん尺度がずれる。*

[![幅系列の相関はほぼ動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/06_cliff_pith_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/06_cliff_pith_error.png)

*↑ 幅系列の相関はほぼ動かない。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/08_cliff_blur_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/08_cliff_blur.png)

*↑ この回の図*

```
py -3.11 examples/poc_tree_ring_dendro.py
```

Source: [examples/poc_tree_ring_dendro.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tree_ring_dendro.py)

This run produced **9 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tree_ring_dendro)

Ops used (notes): [`derivate_funct_1d`](https://furuse.work/ops/oned/function/derivate_funct_1d.html) · [`find_peaks`](https://furuse.work/ops/oned/signal/find_peaks.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median_rect`](https://furuse.work/ops/2d/rank/median_rect.html) · [`polar_unwrap`](https://furuse.work/ops/3d/curvilinear/polar_unwrap.html) · [`smooth_funct_1d_gauss`](https://furuse.work/ops/oned/function/smooth_funct_1d_gauss.html)

## No.2026.046 —— Counting Crop Green — Ground Truth as Per-Pixel Leaf Area Fraction

[![Counting Crop Green — Ground Truth as Per-Pixel Leaf Area Fraction](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response.png)

*↑ **Counting Crop Green — Ground Truth as Per-Pixel Leaf Area Fraction** ―― Cover fraction from a four-band field image, scored against the per-pixel leaf area fraction. The null (Otsu on the green channel) overshoots by +16.3 pp at mid-season, and since every method scatters by under 0.5 pp, nearly all of the difference is bias. At emergence on wet soil the null's cover bias is -0.2 pp while precision and recall are both 0.000 — the number is right and not a single pixel is.*

[![影ゼロならゼロ点も悪くない。影は『暗さ』を手掛かりにする手法に直接刺さる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/02_shadow_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/02_shadow_sweep.png)

*↑ The measurement ―― 影ゼロならゼロ点も悪くない。影は『暗さ』を手掛かりにする手法に直接刺さる。 (figure labels are in Japanese; the numbers are the same)*

[![純粋な葉が 67 % ある場面。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/03_ppi_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/03_ppi_noise.png)

*↑ 純粋な葉が 67 % ある場面。*

[![白い画素の数だけが釣り合っている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/04_wet_soil_zero_hits_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/04_wet_soil_zero_hits.png)

*↑ 白い画素の数だけが釣り合っている。*

```
py -3.11 examples/poc_vegetation_cover.py
```

Source: [examples/poc_vegetation_cover.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vegetation_cover.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_vegetation_cover)

Ops used (notes): [`cv_otsu`](https://furuse.work/ops/2d/segmentation/cv_otsu.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html)

## No.2026.049 —— River Stage From an Oblique Photo — Ignoring Perspective Bends the Row-Number Error Into an Arc

[![River Stage From an Oblique Photo — Ignoring Perspective Bends the Row-Number Error Into an Arc](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/01_scene.png)

*↑ **River Stage From an Oblique Photo — Ignoring Perspective Bends the Row-Number Error Into an Arc** ―― The waterline detected on an obliquely photographed staff gauge and converted to stage. Linear conversion from two gauge marks bends off by up to -6.4 cm (at 1.00 m), and the sign is decided not by the stage but by whether the reading interpolates (-6.6 cm) or extrapolates (+16.3 cm). A four-point homography brings it under 0.2 cm; what remains is waterline detection, not perspective.*

[![measurement](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/02_bias_vs_level_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/02_bias_vs_level.png)

*↑ The measurement (figure labels are in Japanese; the numbers are the same)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/03_anchors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/03_anchors.png)

*↑ この回の図*

[![負 = 低く読む。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/04_reflection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/04_reflection.png)

*↑ 負 = 低く読む。*

```
py -3.11 examples/poc_water_level.py
```

Source: [examples/poc_water_level.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_water_level.py)

This run produced **4 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_water_level)

Ops used (notes): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`mat_svd`](https://furuse.work/ops/math/linalg/mat_svd.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`projective_trans_image`](https://furuse.work/ops/2d/geometry/projective_trans_image.html) · [`ransac_line`](https://furuse.work/ops/3d/robust_fit/ransac_line.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.136 —— There Are Two Kinds of Height, for Real — Putting a Height-Frame Mix-Up Under a Detector with 523 Published Survey Marks

[![There Are Two Kinds of Height, for Real — Putting a Height-Frame Mix-Up Under a Detector with 523 Published Survey Marks](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/03_misuse_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/03_misuse.png)

*↑ **There Are Two Kinds of Height, for Real — Putting a Height-Frame Mix-Up Under a Detector with 523 Published Survey Marks** ―― The synthetic companion (poc_geodetic_height_frames) showed that mixing ellipsoidal and orthometric heights costs tens of metres, using numbers we made ourselves. This exhibit checks the same claim against numbers somebody else measured and published. An NGS datasheet gives, for one mark, the ellipsoidal height h (NAD 83(2011)), the orthometric height H (NAVD 88), the geoid height N (GEOID18) and the Cartesian coordinates (x,y,z) — all four — so 523 marks were taken from the Colorado Front Range, where the geoid is steep enough for interpolation error to show. An existing operator was finally checked against the outside world: dem_geodetic_to_ecef lands within 0.5 mm rms (0.8 mm worst) of the published Cartesian coordinates, and the inverse closes to 7.1e-09 degrees, inside the 9.0e-09-degree floor set by the millimetre rounding of the published data — until now this operator had only been checked against its own inverse, which tests consistency, not correctness. Interpolating a coarse grid costs more than a generation of geoid model: bilinear interpolation of a 0.25-degree GEOID18 grid differs from the published point values by 11.1 cm rms (44.5 cm worst), while GEOID18 minus GEOID12B is -1.0 cm on average (range -9.8 to +6.3 cm). Fifteen of the 523 marks fall outside the grid and are refused rather than clamped, because an extrapolated undulation is not a survey value. A height-frame mix-up does not look like an outlier: putting h into the orthometric column places every single mark exactly on the line -N, lifting the whole table by 16.75 m. And the residual sorts the marks by how they were surveyed even though it never reads that metadata: median |h-H-N| is 1.6 cm for levelling, 1.9 cm for network adjustment, 3.8 cm for GPS observation and 8.3 cm (1.02 m worst) for VERTCON3, a modelled datum conversion. Even the published triples do not close exactly (10.6 cm rms): NAVD 88 comes from levelling and GEOID18 from gravity, and the mismatch shows up here. Only a 56 KB aggregate ships; the raw download stays out of the repository.*

[![523 NGS marks, each publishing ellipsoidal height h (NAD 83), orthometric height H (NAVD 88) and geoid height N (GEOID18](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/01_residual_sorted_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/01_residual_sorted.png)

*↑ The measurement ―― 523 NGS marks, each publishing ellipsoidal height h (NAD 83), orthometric height H (NAVD 88) and geoid height N (GEOID18). The residual h - H - N is not exactly zero: NAVD 88 and GEOID18 were built from different measurements, and the mismatch shows up here at the centimetre level (rms 0.106 m, median -0.004 m). 74 of 523 marks exceed 0.1 m (figure labels are in Japanese; the numbers are the same)*

[![dem_height_frame_residual reads only the three height columns — never the metadata saying how each m](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/02_by_provenance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/02_by_provenance.png)

*↑ dem_height_frame_residual reads only the three height columns — never the metadata saying how each mark was measured.*

[![the published GEOID18 undulation on a 0.25-degree grid over the Colorado Front Range (-19.40 to -11.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/04_geoid_grid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/04_geoid_grid.png)

*↑ the published GEOID18 undulation on a 0.25-degree grid over the Colorado Front Range (-19.40 to -11.15 m, 9x7 nodes).*

[![GEOID18 minus GEOID12B on the same nodes: mean -0.010 m, range -0.098 to +0.063 m.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/06_model_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/06_model_shift.png)

*↑ GEOID18 minus GEOID12B on the same nodes: mean -0.010 m, range -0.098 to +0.063 m.*

[![523 marks placed in the east-north-up frame of one of them (AB3303).](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/08_enu_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/08_enu_map.png)

*↑ 523 marks placed in the east-north-up frame of one of them (AB3303).*

```
py -3.11 examples/poc_geodetic_benchmarks_real.py
```

Source: [examples/poc_geodetic_benchmarks_real.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_benchmarks_real.py)

This run produced **9 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real)

Ops used (notes): [`dem_datum_shift_3param`](https://furuse.work/ops/dem/geodesy/dem_datum_shift_3param.html) · [`dem_ecef_to_geodetic`](https://furuse.work/ops/dem/geodesy/dem_ecef_to_geodetic.html) · [`dem_enu_from_geodetic`](https://furuse.work/ops/dem/geodesy/dem_enu_from_geodetic.html) · [`dem_geodetic_from_enu`](https://furuse.work/ops/dem/geodesy/dem_geodetic_from_enu.html) · [`dem_geodetic_to_ecef`](https://furuse.work/ops/dem/geodesy/dem_geodetic_to_ecef.html) · [`dem_geoid_height`](https://furuse.work/ops/dem/geodesy/dem_geoid_height.html) · [`dem_height_frame_convert`](https://furuse.work/ops/dem/geodesy/dem_height_frame_convert.html) · [`dem_height_frame_residual`](https://furuse.work/ops/dem/geodesy/dem_height_frame_residual.html)

## No.2026.147 —— Scoring Gravitational-Lens Images with Ordinary Industrial Measurement Operators

[![Scoring Gravitational-Lens Images with Ordinary Industrial Measurement Operators](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/01_images_vs_u_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/01_images_vs_u.png)

*↑ **Scoring Gravitational-Lens Images with Ordinary Industrial Measurement Operators** ―― Gravitational lensing carries exact invariants that can be measured straight off the picture, and the tools that measure them are ordinary 2-D operators already in the box: connected components, area and centroid. Writing a point-mass lens in units of the Einstein radius, a source at position u produces images at theta = (u +/- sqrt(u^2+4))/2 with magnifications mu = (u^2+2)/(2 u sqrt(u^2+4)) +/- 1/2, from which two equalities hold no matter where the source sits: the product of the image positions is exactly -1, and the difference of the magnifications is exactly 1, an integer. Across nine source positions the first moves by 8.9e-16 and the second by 2.2e-16. The first core finding is that the integer comes out of the picture: rendering by tracing image-plane pixels back to the source plane, splitting the result into two images with blob_label and subtracting their areas gives a deviation from 1 of 0.0660, 0.0216 and 0.0126 on grids of 801, 1601 and 3201 - measured from the drawing, not read off the model. The second is that surface brightness is exactly conserved, as Liouville's theorem requires: the interior value of the images stays at 1.000000000000000 while the area falls from 2,322 to 480 pixels, so one frame yields both a quantity that does not change and one that does. The third is that the width of the Einstein ring equals the radius of the source, because the radial magnification on the ring is exactly one half; across four source radii the largest discrepancy is 7.2e-05. The fourth is that the singularity manufactures a one-pixel false image: with the source exactly behind the lens the image should be a single ring, yet the connected components number two, the extra one being the pixel at the lens centre where the deflection diverges - a gate that counts images lies here. Two predictions were wrong and have been left in. The first was that measuring from the picture would struggle where the faint image shrinks, at u = 1.5; in fact the worst case at every resolution was u = 0.3, near the caustic, and the faint image at u = 1.5 still covers 209 pixels - the difficulty is not small images but images stretched into thin arcs. The second was the anti-aliasing itself: the edge coverage was being computed from a distance in the source plane while the pixel width belongs to the image plane, and dividing the distance field by its image-plane gradient dropped the u = 0.3 deviation from 0.0214 to 0.0126. For a singular isothermal sphere the image separation is independent of source position at twice the Einstein radius, with a largest discrepancy of 9.3e-03 over four positions. In the animation of a source crossing behind the lens, the measured magnification tracks the closed form to a relative difference of 0.009 while |u| >= 0.3 and opens to 0.161 closer to the caustic, so the range over which the method works is reported alongside the claim. The figures use a calibration target as the source - four concentric rings and twelve radial spokes - so the shear can be read by eye. No new operator was added.*

[![面積を測るのに模様は要らない。明るいほうの像は外側(θ₊ > 1)、暗いほうは内側(|θ₋| < 1)に出て、離れるほど内側の像は小さく暗くなる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/02_disc_images_vs_u_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/02_disc_images_vs_u.png)

*↑ The measurement ―― 面積を測るのに模様は要らない。明るいほうの像は外側(θ₊ > 1)、暗いほうは内側(|θ₋| < 1)に出て、離れるほど内側の像は小さく暗くなる。 (figure labels are in Japanese; the numbers are the same)*

[![9 通りの u で θ₊·θ₋ は −1 から **8.9e-16**、μ₊ − μ₋ は 1 から **2.2e-16** しか動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/03_closed_form_invariants_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/03_closed_form_invariants.png)

*↑ 9 通りの u で θ₊·θ₋ は −1 から **8.9e-16**、μ₊ − μ₋ は 1 から **2.2e-16** しか動かない。*

[![像の内部の値はどちらも厳密に **1.000000000000000**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/05_brightness_and_area_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/05_brightness_and_area.png)

*↑ 像の内部の値はどちらも厳密に **1.000000000000000**。*

[![環の上では動径方向の倍率が**厳密に 1/2** なので、直径 2ρ の光源は太さ ρ の環になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/07_ring_width_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/07_ring_width.png)

*↑ 環の上では動径方向の倍率が**厳密に 1/2** なので、直径 2ρ の光源は太さ ρ の環になる。*

[![重心は `blob_label` で分けた成分ごとに、被覆率で重みを付けて出している。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/09_sis_separation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/09_sis_separation.png)

*↑ 重心は `blob_label` で分けた成分ごとに、被覆率で重みを付けて出している。*

[![光源がレンズの裏を横切る(図は校正ターゲット)。最接近で 2 つの像が伸びて環に近づく。**倍率の数字は同じ光源位置を無地の円盤で描き直して測ったもの**で、最大 19.61 倍。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/10_source_crossing.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/10_source_crossing.gif)

*↑ The animation ―― 光源がレンズの裏を横切る(図は校正ターゲット)。最接近で 2 つの像が伸びて環に近づく。**倍率の数字は同じ光源位置を無地の円盤で描き直して測ったもの**で、最大 19.61 倍。*

```
py -3.11 examples/poc_gravitational_lens_invariants.py
```

Source: [examples/poc_gravitational_lens_invariants.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gravitational_lens_invariants.py)

This run produced **12 figures** in total - [see them all](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_gravitational_lens_invariants)

Ops used (notes): [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html)




---

**This museum was built together with Claude Code.** I set the questions and the direction; Claude Code did the implementation, the sweeps, the control groups and the adversarial checks. That division of labour is what made it possible to run 53 PoCs and collect their figures in two days. If you want to try it, this invitation link gives you a **one-week free trial**: [claude.ai/referral/0sqPw8E_lw](https://claude.ai/referral/0sqPw8E_lw)

If even one exhibit was worth your time, a **like or a stock** helps: the reactions decide which wing grows next, so tell me in the comments which measurement from your own field you would want to see. And if you swapped in real data and the cliff moved, that is the story I most want to hear.
