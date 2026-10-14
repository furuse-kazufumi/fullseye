# 薄膜の PoC の実測データ(CC BY 4.0、改変あり)

`examples/poc_thin_film_reflectometry.py` の「実測の章」が読む小さな表と写真。どれも第三者の公開データで、
ライセンスは **Creative Commons Attribution 4.0 International(CC BY 4.0)**
<https://creativecommons.org/licenses/by/4.0/>。Fullseye の Apache-2.0 とは別のライセンスで、ここに表示を置く。
作り方は `py -3.11 tools/gen_thin_film_real.py <取得した原本のディレクトリ>`(原本は repo の外)。

## 1. Schwarz ら 2024(Zenodo 10.5281/zenodo.13753754)

- 出典: J. Schwarz, M. Niebauer, L. J. Roemling, A. Pham, M. M. Kolesnik-Gray, P. Evanschitzky, N. Vogel,
  V. Krstić, M. Rommel, A. Hutzler, "Spectro-Spatial Unmixing in Optical Microspectroscopy for Thickness
  Determination of Layered Materials", *Advanced Optical Materials* (2024), doi:10.1002/adom.202402502。
  データセット: <https://zenodo.org/records/13753754>(Zenodo の記録に "cc-by-4.0")。取得 2026-10-15。
- `schwarz2024_sio2_si_reflectance.csv`: `Figure_S3a_data.xlsx` の実測反射率 R(λ)(440〜950 nm)。Si 上の
  SiO₂ の縁に分光の測定点を置き、SiO₂ の被覆率を 100 % → 0 % に変えた 11 本。**改変**: 列名を付け直し、数値の桁を
  6 桁に丸めた。
- `schwarz2024_t_model_over_reference.csv`: `Figure_4_data.xlsx` の SiO₂ の列(モデルの膜厚 ÷ 基準の膜厚)。
  被覆率 100 % のモデル値 98.8 nm(`Figure_S4a`)と比 1.003046 から、基準の膜厚は 98.5 nm と逆算した
  (**逆算は Fullseye 側**。基準の膜厚をどの方法で測ったかは論文本文を読めておらず未確認)。
- `schwarz2024_micrograph_sio2_edge_640.jpg`: `Micrographs_SiO2_Sample/48.4%_SiO2_Sample.jpg`(顕微鏡のカラー写真、
  左が裸の Si、右が SiO₂)。**改変**: 1920×1080 → 640×360 に縮小し、JPEG(品質 92)で保存し直した。

## 2. Sánchez-Arriaga ら 2023(figshare 10.15131/shef.data.23285603)

- 出典: N. E. Sánchez-Arriaga, D. Tiwari, W. Hutabarat, A. Leyland, A. Tiwari, "A Spectroscopic
  Reflectance-Based Low-Cost Thickness Measurement System for Thin Films: Development and Testing",
  *Sensors* 23(11), 5326 (2023), doi:10.3390/s23115326。データセット: <https://doi.org/10.15131/shef.data.23285603>
  (figshare の API で "CC BY 4.0")。取得 2026-10-15。
- `sanchez_arriaga2023_sio2_standards.csv`: 市販の SiO₂/Si 膜厚標準(公称 **476.3 nm** = sample 1、
  **198.7 nm** = sample 2)を、安価な小型分光器 2 種と光源 3 種で測った
  反射率(任意単位)。**改変**: 繰り返し 3〜4 回の平均だけを残し、モデル曲線・誤差の列は捨てた。
