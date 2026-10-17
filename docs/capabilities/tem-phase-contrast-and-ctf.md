---
id: tem-phase-contrast-and-ctf
title: 仮想の透過電子顕微鏡(電子の波長 → CTF → 位相コントラストの像 → Thon リングから焦点外れを推定 → 補正)
title_en: A virtual transmission electron microscope (electron wavelength, CTF, phase-contrast images, defocus from Thon rings, correction)
category: 測る
ops: [tem_wavelength, tem_scherzer, tem_ctf, tem_ctf_profile, tem_projected_potential, tem_amorphous_film, tem_image_weak_phase, tem_multislice, tem_power_spectrum, tem_ctf_estimate, tem_ctf_correct]
examples: [poc_tem_ctf_thon_rings]
version: 0.6.1
inputs: [image2d]
pipeline: [tem_power_spectrum, tem_ctf_estimate, tem_ctf_correct]
alternatives: [tem_ctf_profile, tem_scherzer, tem_image_weak_phase, tem_amorphous_film, tem_multislice]
limits: 弱位相近似の線形の像は位相の rms が 0.1 rad を超えると 10 % 以上ずれる(非線形は mode="coherent")。推定は CTF² の振動の当てはめで、リングが見えない・零点が 3 本無い・範囲の端・2-D の当てはめが別の谷に落ちた(z が低い)ときは拒否。Cu など重い元素の散乱因子は X 線の当てはめの限界で 10 % 小さい。
calibration: 焦点外れの値は画素寸法の 2 乗と電子の波長に比例して決まる(画素寸法を 2 % 間違えると Δf は 4 % ずれる)。画素寸法は検出器の画素 ÷ 倍率か、格子間隔の既知の試料(金の格子・グラファイト)のリングで校正し、電圧と Cs は装置の値を使う。
---

# 仮想の透過電子顕微鏡(電子の波長 → CTF → 位相コントラストの像 → Thon リングから焦点外れを推定 → 補正)

## できること

透過電子顕微鏡(TEM)は薄い試料を透けた電子の位相を、対物レンズの球面収差 Cs と焦点外れ Δf で強度に変えて見ます。その変え方がコントラスト伝達関数 CTF = −sin(χ + arcsin w) で、周波数ごとに符号が入れ替わるので、写真の細部は焦点によって黒くも白くも写ります。パワースペクトルには CTF の零点が同心円(Thon リング)として出るので、逆にリングから焦点外れを読めます。`temsim`(`opsoptics` の `tem`、11 本)はこの流れを通します。

電子は `tem_wavelength`(相対論補正つきの波長と相互作用定数 σ)と `tem_scherzer`(Scherzer 焦点と点分解能、定義 2 つを並べて)。伝達関数は `tem_ctf`(2-D、非点収差と空間・時間の包絡つき)と `tem_ctf_profile`(1-D の曲線と零点の閉形式)。試料は `tem_projected_potential`(原子の座標から。X 線の散乱因子 `pxrd.FORM_FACTORS` を Mott–Bethe の式で電子の散乱因子に変える)と `tem_amorphous_film`(Thon リングの標準試料)。像は `tem_image_weak_phase`(弱位相物体の線形の像、または `coherent_image` に瞳 e^{iχ} を渡した非線形の像。線量の Poisson 雑音つき)と `tem_multislice`(Fresnel 伝播で厚い試料)。推定と補正は `tem_power_spectrum`(タイルの平均)、`tem_ctf_estimate`(Lomb–Scargle で初期値 → CTF² との正規化相互相関 → 非点収差の 2-D 当てはめ → jackknife の不確かさ、リングが見えないときは拒否)、`tem_ctf_correct`(位相反転 / ウィーナー)。

規約は CTFFIND4 / RELION に合わせ、長さは Å、Cs は mm、焦点外れは**正 = アンダーフォーカス**です。

PoC `poc_tem_ctf_thon_rings` は、波長の公表値(200 kV で 2.5079 pm、300 kV で 1.9687 pm)、零点の閉形式、Scherzer の点分解能 0.66 Cs^¼ λ^¾、正弦位相格子の Raman–Nath の回折、合成写真の Δf と非点収差の回収で採点し、実写(EMPIAR-10028、CC0)3 枚で著者の CTFFIND3 の値と 0.2 % 以内で一致することを確かめます。

## What it does

Eleven ops in `temsim` (category `tem` of `opsoptics`): relativistic electron wavelength and interaction constant, Scherzer defocus and point resolution, the 2-D CTF with astigmatism and spatial/temporal envelopes, the 1-D CTF with closed-form zeros, projected potentials from atom positions (electron scattering factors from the X-ray factors of `pxrd` via Mott–Bethe), an amorphous film, weak-phase or nonlinear (`coherent_image`) bright-field images with dose noise, a simple multislice, the tiled power spectrum, defocus and astigmatism estimation from Thon rings (with a jackknife uncertainty and an explicit refusal when the rings are not visible), and phase-flip or Wiener correction. Conventions follow CTFFIND4/RELION (Å, positive defocus = underfocus). The PoC grades against published wavelengths, closed-form CTF zeros, the Scherzer point resolution, Raman–Nath diffraction, synthetic ground truth, and three EMPIAR-10028 micrographs whose defocus it reproduces within 0.2 % of the authors' CTFFIND3 values.

## 向くところ / 向かないところ

**向く**: TEM の結像の勉強と、焦点・Cs・電圧・照明の開き角がどの周波数を写すかの見積り、cryo-EM の写真の焦点外れ・非点収差の確認(CTFFIND / Gctf の結果の検算)、位相反転・ウィーナーの効き方の比較、ドリフトしたフレームの位置合わせの効果の確認。

**向かない**: ★散乱因子は X 線の 5 ガウスの当てはめ(Waasmaier–Kirfel)からの Mott–Bethe で、軽元素の f_e(0) は DFT の孤立原子の表と 2.3 % 以内ですが、Cu は 10 % 小さい(外側の 4s 電子に f_e(0) が敏感)。重い元素の定量には Kirkland / Peng の電子の散乱因子の表を使ってください(未同梱、収録元素も `pxrd.FORM_FACTORS` の 16 種だけ)。熱散漫散乱・非弾性散乱・吸収ポテンシャル・試料の傾き・結晶の Bloch 波は扱いません。マルチスライスは簡易版(帯域 2/3 の規則だけ)で、公開の数値ベンチマークとの照合はまだです。推定は CTF² の振動の当てはめで、位相板の移相は引数で固定値を与えるだけ(推定しない)、Cs が分からない写真や、非点収差がリングの間隔より大きい写真では外れます。タイルが少ない(像に 3 枚入らない)と非点収差の当てはめが別の谷に落ちやすく、そのときは z の門で拒否されます。

## 推奨パイプライン

`tem_power_spectrum` → `tem_ctf_estimate` → `tem_ctf_correct`

写真(電子の数か強度、2-D)のタイルの平均のパワースペクトルでリングを目で確かめる → `tem_ctf_estimate` に画素寸法・電圧・Cs・振幅コントラストと焦点外れの探索範囲を渡して Δf・非点収差・不確かさを得る(拒否されたら理由を読む)→ `tem_ctf_correct` に推定値を渡して位相反転かウィーナー。線量分割のフレームがあるなら、先に `phase_correlation_fft` で位置を合わせて足す(合わせないとずれの向きのリングが消える)。

## 代替

撮る前の見積りは `tem_scherzer`(Scherzer 焦点と点分解能)と `tem_ctf_profile`(包絡つきの CTF と零点、情報限界)。合成の写真は `tem_amorphous_film` か `tem_projected_potential` → `tem_image_weak_phase`、厚い試料は `tem_multislice` の出射波を `coherent_image` の瞳に通す。

## 限界

- 弱位相近似の線形の像は位相の rms に比例してずれる(0.1 rad で約 10 %)。厚い試料の伝播はマルチスライスで扱うが、簡易版(帯域 2/3 の規則だけ)で公開ベンチマークとの照合は未了。
- 推定は CTF² の振動への当てはめ。位相板の移相は固定値を渡すだけで推定しない。タイルが少ないと非点収差の当てはめが別の谷に落ち、その場合は z の門で拒否される(PoC で実演)。リングがタイルの刻みで均される周波数より上は自動で帯域を下げる。
- 散乱因子は X 線の 5 ガウスの当てはめからの Mott–Bethe。軽元素は DFT の表と 2.3 % 以内、Cu は 10 % 小さい。収録は `pxrd.FORM_FACTORS` の元素だけ。

## 実寸校正

Δf の値は画素寸法の 2 乗と電子の波長に比例して決まる(PoC の探針: 画素寸法 +2 % で Δf は 1.039 倍、電圧の取り違えは Cs の項込みの最小 2 乗の予測どおり)。画素寸法は検出器の画素 ÷ 倍率か、格子間隔の既知の試料のリングで校正し、電圧と Cs は装置の値を使う。実写の PoC では写真のヘッダとログの撮影条件(300 kV、Cs 2.0 mm、14 µm ÷ 104478 倍 = 1.34 Å/画素)だけを使った。

## 最初の 1 本

```python
import temsim as TM

print(round(TM.tem_wavelength(300.0)["wavelength_pm"], 4))          # 1.9687
film = TM.tem_amorphous_film(512, 1.0, 50.0, seed=1)                  # 非晶質炭素 50 Å の投影ポテンシャル
img = TM.tem_image_weak_phase(film, 1.0, 300.0, 2.7, 15000.0, dose_e_per_A2=40.0, seed=3)
r = TM.tem_ctf_estimate(img, 1.0, 300.0, 2.7, 0.07)
print(round(r["defocus_A"]), round(r["defocus_sigma_A"], 1))         # 15000 前後と、jackknife の σ
```

走らせて見るなら `py -3.11 examples/poc_tem_ctf_thon_rings.py`(実写の章は `FULLSEYE_TEM_DOWNLOAD=1` で取得、図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
