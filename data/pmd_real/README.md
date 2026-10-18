# デフレクトメトリの PoC の実データ(CC0 1.0、改変あり)

`examples/poc_phase_measuring_deflectometry.py` の 4 節(実データの章)が読む、鏡面の鋼板をハンマーで叩いたときの
格子の鏡像。第三者の公開データで、ライセンスは **CC0 1.0 Universal(パブリックドメイン献呈)**
<https://creativecommons.org/publicdomain/zero/1.0/>。CC0 は表示を求めないが、出典はここと図の台帳に残す。
作り方は `py -3.11 tools/gen_pmd_real.py <原本のディレクトリ>`(原本は repo の外)。

## 出典

- データセット: R. Kaufmann, S. N. Olufsen, E. Fagerholt (NTNU), "Experimental data for force reconstruction using
  impact hammer and deflectometry", DataverseNO, V1, <https://doi.org/10.18710/TKS7SI>(2021-10-29 公開、
  記録のライセンス欄 "CC0 1.0")。取得 2026-10-18、画像 280 枚は記録の MD5 と一致を確かめた。
- 手法と装置の説明: R. Kaufmann, S. N. Olufsen, E. Fagerholt, V. Aune, "Reconstruction of surface pressures on flat
  plates impacted by blast waves using the Virtual Fields Method", *Int. J. Impact Eng.* **171**, 104369 (2023),
  doi:10.1016/j.ijimpeng.2022.104369(CC BY 4.0)。表 1 の装置の値と、式 1(傾き = u / 2h)、画素の間隔 p_G / 10 を使った。
- 第 2 の実装: S. N. Olufsen ら, "RECOLO: A python package for the reconstruction of surface pressure loads from kinematic
  fields using the virtual fields method", *JOSS* **6**(67), 3869 (2021)、<https://github.com/PolymerGuy/recolo>(MIT、
  commit 05b14f0)。repo には入れず、手元で同じ画像に走らせた結果の数だけを PoC に書いた。
- 装置(原本の experimental_setup.txt): 板 300 × 300 × 4.95 mm(E 190 GPa、ν 0.3、ρ 7900 kg/m³)、周縁を固定。印刷した
  十字格子の周期 5.88433 mm、板と格子の距離 1.37 m、格子 1 周期 = 5 画素。高速度カメラ 75 000 駒/秒、露光 5 µs、
  512 × 512 画素、12 bit。ハンマーの先のロードセルの力(N)と時刻(s、51.2 kHz)。

## 中身(`hammer_grid_cc0.npz`)

| 鍵 | 中身 | 原本 |
|---|---|---|
| `ref_mean_x8` | 打撃の前の 30 枚の平均 × 8(uint16)、行 0:512 × 列 30:460 | `image_0001.tif`〜`image_0030.tif` |
| `frame_hammer_peak` | ハンマーの力が峰の駒、同じ切り出し(uint16、値はそのまま) | `image_0283.tif` |
| `frame_max_slope` | 傾きが最大の駒、同じ切り出し | `image_0326.tif` |
| `frame_numbers`、`crop_origin` | 上の 2 駒の番号と、切り出しの左上 | — |
| `rec_*` | 原本 280 枚の全解析の記録(力の時系列、均したハンマーの記録、対照の窓、選んだ窓、探針の結果) | 全画像とハンマーの記録 |

**改変**: 画像を切り出した(512 → 512 × 430 画素)、打撃の前の 30 枚を平均した、Fullseye の解析
(`analyze_hammer_dataset`)の結果を `rec_*` として足した。画素の値とハンマーの記録の値はそのまま。

## 外部の真値

ハンマーの先のロードセルの力(峰 365.5 N @ 1.777 ms、力積 0.233 N·s)。時刻の対応は「ハンマーの 0 秒 = image_0150」で、
データの著者の公開コード(recolo の例 `impact_hammer_experiment.py`)に従った。原本には `image_0031`〜`image_0149` と
`image_0384` が無い。
