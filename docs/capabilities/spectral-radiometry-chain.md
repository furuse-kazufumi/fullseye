---
id: spectral-radiometry-chain
title: 光源 × 対象 × センサの分光の鎖(Planck・CIE A・LED・フィルタ・Si の QE、曲線の積と積分)
title_en: The spectral chain source × object × sensor (Planck, CIE A, LEDs, filters, Si QE, curve products and integrals)
category: 光と色
ops: [blackbody_spectrum, cie_illuminant_a, led_spectrum, bandpass_spectrum, silicon_photodiode_qe, energy_to_photons, spectral_product, spectral_integral, spectral_stats]
examples: [poc_nir_silicon_transmission]
version: 0.6.1
---

# 光源 × 対象 × センサの分光の鎖(Planck・CIE A・LED・フィルタ・Si の QE、曲線の積と積分)

## できること

像の明るさは、光源の分光分布 × 光学系と対象の透過・反射 × センサの量子効率を波長で積分した値で決まります。材料の透過率・反射率は `materials` が pairs(λ [nm], 値)で返しますが、光源とセンサの曲線が op として無く、「この光源で、このウェハ越しに、このセンサで何電子になるか」を組めませんでした。`spectralrad` の 9 本がその残り半分で、どの曲線も同じ pairs で返します。

光源は `blackbody_spectrum`(Planck、SI 2019 の定義値の定数)、`cie_illuminant_a`(CIE 15:2004 の定義式。表の値はこの式の値なので外部の真値になる)、`led_spectrum`(Ohno 2005 のモデルか Gauss。半値全幅が指定どおりになるよう幅を解いて決める)。フィルタは `bandpass_spectrum`(超 Gauss、遮断域の床つき)。センサは `silicon_photodiode_qe` で、Si の n,k(Green 2008、材料表)から QE = (1 − R)[e^{−αd₀} − e^{−α(d₀+W)}] を計算します。演算は `energy_to_photons`(λ/hc)、`spectral_product`(範囲の足りない曲線を掛けると ValueError)、`spectral_integral`、`spectral_stats`(ピーク・重心・FWHM・積分)。

★QE は「光子 1 個あたりの電子数」なので、エネルギーの分光分布に掛ける前に `energy_to_photons` を通します。通さないと 1100 nm と 550 nm で重みが 2 倍ずれます。

PoC `poc_nir_silicon_transmission` は、Si ウェハ越しの近赤外透過検査で LED の波長を選びます。同じ Si の吸収端が、ウェハでは窓・センサでは壁になる矛盾を、材料表の 1 つの Si のレコードで両側から計算しています。

## What it does

Nine ops in `spectralrad` complete the spectral chain image = source × optics/object × sensor QE, all as `pairs` (λ nm, value) like the material curves: Planck blackbody (SI 2019 constants), CIE illuminant A (the defining formula), LED spectra (Ohno 2005 or Gaussian, width solved to the requested FWHM), a super-Gaussian band-pass filter, the Si photodiode QE from the material table's Si n,k, the energy-to-photon conversion, and curve product, integral and summary. Gates: the CIE A table, Wien and Stefan–Boltzmann, the QE closed form and its thick-detector limit, and Poisson statistics in the rendered images.

## 向くところ / 向かないところ

**向く**: NIR / SWIR の照明波長の選定、フィルタとセンサの組合せの比較、ウェハ・窓越しの像の電子数と CNR の見積り、ハロゲンと LED の比較、光子数と露光時間の当たりをつけること。

**向かない**: ★センサの QE は Si の吸収だけの模型で、画素の構造(マイクロレンズ・裏面照射の反射防止膜・深いトレンチ分離)は `collection_depth_um` と `front_reflectance` の 2 つにまとめています。メーカーの QE の曲線を使うなら、測った曲線を pairs で渡して `spectral_product` に掛けてください。InGaAs・Ge のセンサの QE はまだありません。Si の k の表(Green 2008)は 250〜1450 nm で、その外の QE は ValueError です。光源の配光と光学系の集光効率(何光子が画素に届くか)はこの層の外です(`illumdesign` / `optscene`)。

## 最初の 1 本

```python
import materials as M
import spectralrad as S

# 1065 nm の LED を 775 µm の Si ウェハ越しに Si センサで見ると、光子 1 個あたり何電子か
led = S.energy_to_photons(S.led_spectrum(1065.0, 50.0, 700.0, 1350.0, 651))
led[:, 1] /= S.spectral_integral(led)                       # 光子 1 個に規格化
T = M.material_transmittance("SI", 0.775, 700.0, 1350.0, 651)
qe = S.silicon_photodiode_qe(3.0, 0.0, None, 700.0, 1350.0, 651)
print(S.spectral_integral(S.spectral_product(S.spectral_product(led, T), qe)))   # ≈ 3.6e-4
```

走らせて見るなら `py -3.11 examples/poc_nir_silicon_transmission.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
