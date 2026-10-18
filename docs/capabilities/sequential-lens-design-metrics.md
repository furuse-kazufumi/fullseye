---
id: sequential-lens-design-metrics
title: 逐次光学設計の指標(理想レンズ面 → 囲みエネルギー → 子午/球欠 MTF → スルーフォーカス MTF)
title_en: Sequential lens-design metrics (ideal lens surface, encircled energy, tangential / sagittal MTF, through-focus MTF)
category: 測る
ops: [lens_system, encircled_energy, ensquared_energy, energy_radii, mtf_tangential_sagittal, through_focus_mtf, with_aiming, ray_aiming, set_vignetting]
examples: [optical_design_metrics]
version: 0.7.0
inputs: [table]
pipeline: [lens_system, psf_from_opd, encircled_energy, energy_radii, mtf_tangential_sagittal, through_focus_mtf]
alternatives: [psf_to_mtf, mtf_diffraction, spot_stats, opd_map, wavefront_from_opd, lens_section_drawing]
limits: 理想レンズ面の光路は軸上の物点(第 1 面で有限物体なら光線ごとの物点)に対して等光路で、途中の理想レンズでは平行入射を仮定する(収束光の中の理想レンズの OPD は近似)。理想レンズは非共軸の raytrace3d では読まず、鏡・円錐・非球面・硝材を持たない。囲み/四角エネルギーは PSF の窓の中の割合で、窓が翼を切ると高めに出る(切れて届かない割合は ValueError)。半径が 2 画素前後より小さいと PSF の点標本を画素に均等に広げた近似が効く。スルーフォーカス MTF は 1 視野 1 波長ずつ(多色は波長ごとに呼ぶ)。
calibration: 長さの尺度は PSF の画素ピッチ(psf_from_opd の pixel_pitch_um、または細かい格子の間隔 λ·F#·(size−1)/M)で決まり、周波数は cycles/mm。ピッチを間違えると半径が比例して狂う(探針で確認)。
---

# 逐次光学設計の指標(理想レンズ面 → 囲みエネルギー → 子午/球欠 MTF → スルーフォーカス MTF)

## できること

商用の逐次光学設計ソフトで毎日使う 4 つの道具を、Fullseye の op として足しました。

`raytrace.lens_system` の面に `{"f": 50.0, "t": …}` と書くと**理想レンズ**(paraxial 面)になります。厚み 0・形なし・硝材なしで、薄肉レンズの法則 `tan θ' = tan θ − h/f` を実光線に厳密に当てるので、平行光は f にちょうど集まり、有限の物体はガウスの結像公式の位置・倍率 `m = −s'/s` に結像します。光路は等光路(小さい高さで `−h²/(2f)` の 2 次位相)なので、OPD・PSF・スポットの解析がそのまま動き、収差ゼロの基準として使えます。断面図には細い線と矢じり(収束は外向き、発散は内向き)で描きます。

`encircled_energy` / `ensquared_energy` は PSF から囲み・四角エネルギーの曲線を、`energy_radii` は 50 / 80 / 90 % が入る半径を返します。`mtf_tangential_sagittal` は PSF の 2-D 変換の軸の断面で子午/球欠の MTF を分け(`psf_to_mtf` は半径平均だけでした)、`through_focus_mtf` は像面を動かした PSF ごとに指定周波数の MTF を並べます。

**光線の照準とケラレ係数**(2026-10-19)。既定の打ち出しは近軸の入射瞳へ向けるので、瞳の収差のある系では周辺の光線が絞りの外へ落ち、同梱の三枚玉は軸上で 217 本中 48 本を失います(設計ソフトのスポット・MTF と数字が合わない原因)。`with_aiming(system, "stop")` か `lens_system(..., aim="stop")` で**実光線の照準**に切り替えると、各光線を Newton 法で絞りの指定の点へ通します(許容は絞り半径の 1e-11、収束しなければ ValueError)。三枚玉は全視野で 217 本とも絞りに届き、残差は 1e-13 台、RMS スポットは軸上 5.07 → 4.69 µm、14 度 16.6 → 17.4 µm、20 度 11.9 → 15.6 µm になります(以前は縁の光線を捨てて小さく見えていた)。薄肉の理想レンズでは照準しても動きません(1e-12)。既存の数字を動かさないため、既定は従来の `aim="paraxial"` のままです。

`lens_system(..., vignetting=[{"field", "vdx", "vdy", "vcx", "vcy", "van"}])` は視野ごとのケラレ係数です。正規化した瞳を `q = (VDX, VDY) + R(VAN)·diag(1−VCX, 1−VCY)·R(−VAN)·p` に圧縮・偏心してから光線を狙うので、`VCY = 0.3` なら絞り上の瞳の高さがちょうど 0.7 倍になります(実光線から測って 1e-10 以内)。`.zmx` の `VDXN / VDYN / VCXN / VCYN / VANN` を読み、`lens_file_write` が書き戻します。`set_vignetting(system, fields)` は設計ソフトの "set vignetting" と同じく、開口に切られる光線が 1 本も残らないところまで瞳を縮め・ずらして係数を求めます(切られない系では全部 0)。`ray_aiming` は狙いの検査表(通過本数・残差・絞り上の瞳の広がり)です。スポット・OPD・PSF・MTF の各 op はシステムの `aim` と係数をそのまま使い、回折限界の理想レンズに VCY = 0.3 を入れると子午(y)の MTF は円形瞳の閉形式でカットオフが 0.7 倍、球欠(x)は元のままになります(6e-3 以内)。

真値は外にあります。収差ゼロの PSF の囲みエネルギーは Airy の `1 − J0(v)² − J1(v)²`(第 1 暗環で 83.8 %、Born & Wolf)、四角瞳は sinc² の積分、ガウス PSF は閉形式、円形瞳の MTF は `(2/π)(arccos x − x√(1−x²))`、デフォーカスは Hopkins の瞳の重なりの積分(求積で独立に計算)。ピッチを 2 倍にする、軸を入れ替える、共役の補正を落とすといった壊し方で、各門が赤になることも確かめています。

## What it does

An ideal (paraxial) lens surface for `raytrace.lens_system` and four PSF metrics. The ideal lens turns rays by the thin-lens law exactly with a stigmatic optical path, so an aberration-free lens reads zero OPD and an Airy PSF. `encircled_energy` / `ensquared_energy` give the energy-versus-radius curves, `energy_radii` the radii at chosen fractions, `mtf_tangential_sagittal` the two meridional slices of the 2-D transform, and `through_focus_mtf` the MTF at chosen frequencies across image-plane shifts. Gates: focus at f to 1e-12 mm, Gaussian conjugate and magnification, 83.8 % at the first Airy dark ring, the closed-form circular-pupil MTF, and Hopkins' defocus integral.

Real-ray aiming and vignetting factors (2026-10-19): `with_aiming(system, "stop")` (or `lens_system(..., aim="stop")`) iterates every pupil ray onto its own point of the stop surface (tolerance 1e-11 of the stop radius, `ValueError` if it does not converge), so the stock triplet loses 0 of 217 rays on axis instead of 48; the default stays the paraxial launch so existing numbers do not move. `lens_system(..., vignetting=[...])` carries per-field VDX / VDY / VCX / VCY / VAN (read from and written to `.zmx`), `set_vignetting` computes them from the apertures, `ray_aiming` reports the counts, residual and pupil extent. Spot, OPD, PSF and MTF ops use the aimed, vignetted pupil.

## 向くところ / 向かないところ

**向く**: 設計の出発点を理想レンズで置いて後ろの系の収差だけを見る、スポットの大きさを「何 % が画素に入るか」で言う、軸外の非点収差を子午/球欠の MTF で見る、像面のずれに対する MTF の余裕(焦点深度)を出す。

**向かない**: 色のある多波長の MTF(波長ごとに呼ぶ)、Huygens の PSF、設計ファイルの読み書き、ズーム。理想レンズは非共軸の `raytrace3d` では読めません。

## 推奨パイプライン

`lens_system` → `psf_from_opd` → `encircled_energy` → `energy_radii` → `mtf_tangential_sagittal` → `through_focus_mtf`

`psf_from_opd` には `pixel_pitch_um` を渡す。`encircled_energy` と `energy_radii` は同じ PSF から並べて使う(曲線と、指定した割合に達する半径)。

`lens_system` に `{"f": 50.0, "t": None, "ap": 2.5}` の面を置いて収差ゼロの基準を作り(実際の系なら処方を並べる)→ `psf_from_opd` に `pixel_pitch_um` を渡して PSF を画素へ面積積分し → `encircled_energy` / `energy_radii` で「何 µm の円に 80 % 入るか」→ 細かい格子の PSF を `mtf_tangential_sagittal` に渡して子午/球欠の MTF → 像面のずれに対する余裕は `through_focus_mtf`(処方を直接受ける)。

## 代替

半径平均の MTF で足りるなら `psf_to_mtf`、回折限界の曲線だけなら `mtf_diffraction`。スポットの大きさを幾何光線で見るなら `spot_stats`、波面は `opd_map` / `wavefront_from_opd`。図面は `lens_section_drawing`(理想レンズは細線と矢じりで描く)。

## 限界

- 理想レンズの光路は、軸上の物点(第 1 面で有限物体なら光線ごとの物点)に対して等光路にしてある。途中の理想レンズは平行入射を仮定するので、収束光の中に置いた理想レンズの OPD は近似になる。
- 理想レンズは非共軸の `raytrace3d` では読めず、鏡・円錐・非球面・硝材を持たない(ValueError)。
- 囲み/四角エネルギーは PSF の窓の中の割合で、窓が翼を切ると高めに出る。窓が足りず指定の割合に届かないときは ValueError(`energy_radii`)。半径が 2 画素前後より小さいと、点標本を画素に均等に広げた近似が効く。
- 実光線の照準は既定でなく(`aim="stop"` で入れる)、物体側テレセンの系は従来の絞り照準を使う。照準が収束しない光線(絞りに届かない大きな視野)は ValueError。ケラレ係数の VAN(回転)と VD の符号は設計ソフトの規約を公開資料から読んだ定義で、`.zmx` の x ≠ 0 の視野の係数は瞳を方位角に回さず適用する(`allow_partial` が要る)。視野の間は係数を線形補間、範囲の外は最寄りの記録。OPD / PSF / MTF では係数は瞳の**マスク**(格子は物理瞳のまま)で、基準は暈されていない主光線。
- スルーフォーカス MTF は 1 視野 1 波長ずつ。周波数は回折限界の格子の上限(カットオフ)までで、それを超えると ValueError。

## 実寸校正

長さの尺度は PSF の画素ピッチで決まる。`psf_from_opd` の `pixel_pitch_um` を渡した PSF ならそのピッチ、細かい格子の PSF なら `λ·F#·(size−1)/M`(M は FFT 格子)を `pixel_pitch_um` に渡す。ピッチを 2 倍にすると半径がちょうど 2 倍に狂う(試験の探針で確認)ので、半径は必ず元の格子のピッチで読む。周波数は cycles/mm。

## 最初の 1 本

```python
import lensimage as LI
import optics as O
import raytrace as RT

lens = RT.lens_system([{"f": 50.0, "t": None, "ap": 2.5}], stop=0)           # 理想レンズ f/10: 収差ゼロ
psf = LI.psf_from_opd(lens, size=128, oversample=8, pixel_pitch_um=1.5)
print(O.energy_radii(psf, 1.5, (0.5, 0.8, 0.9))["radius_um"])                 # [3.29, 5.5, 11.33]  Airy の 50/80/90 % 半径
tf = LI.through_focus_mtf(lens, frequency_cpmm=[30.0], defocus_mm=[-0.5, 0.0, 0.5])
print(tf["tangential"][:, 0].round(3), tf["sagittal"][:, 0].round(3))          # 軸上は子午 = 球欠
```

走らせて見るなら `py -3.11 examples/optical_design_metrics.py`(理想レンズの焦点・結像公式・Airy の 83.8 %・回折限界 MTF・非点収差での分離を一巡)。
