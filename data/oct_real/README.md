# 工業用 OCT の PoC の実測データ(CC BY 4.0、改変あり)

`examples/poc_industrial_oct.py` の「実測の章」が読む、分光器型 OCT(SD-OCT)の生の干渉スペクトル。第三者の公開データで、
ライセンスは **Creative Commons Attribution 4.0 International(CC BY 4.0)**
<https://creativecommons.org/licenses/by/4.0/>。Fullseye の Apache-2.0 とは別のライセンスで、ここに表示を置く。
作り方は `py -3.11 tools/gen_oct_real.py <原本の zip を展開したディレクトリ>`(原本は repo の外)。

## 出典

- データセット: University of Liverpool Research Data Catalogue, record 126 "AppliedOptics2016"
  <https://datacat.liverpool.ac.uk/126/>(記録のライセンス欄 "Creative Commons: Attribution 4.0")。取得 2026-10-15。
- 論文: Y. Dong, S. Lawman, Y. Zheng, D. Williams, J. Zhang, Y.-C. Shen, "Nondestructive analysis of automotive
  paints with spectral domain optical coherence tomography", *Applied Optics* **55**(13), 3695–3700 (2016),
  doi:10.1364/AO.55.003695。論文の本文と図は CC BY ではないので、この repo には**数値だけ**を引用する(図は使わない)。
- 装置(論文の記載): 中心 840 nm・半値全幅 47 nm の SLD、分光器 2048 画素(波長 797.24〜972.04 nm、等間隔でない較正)、
  横 1 mm を 200 本の A スキャン、軸分解能 5.5 µm(空気中、Tukey 窓)、横分解能 12.4 µm。

## 中身(`paint_sdoct_cc_by.npz`)

| 鍵 | 中身 | 原本 |
|---|---|---|
| `wavelength_nm` | 画素ごとの波長 (2048,) | `wavel`(全ファイル共通) |
| `spectra_V-D`, `spectra_VI-D` | 黒の見本 2 枚の B スキャンから 100 本 (100, 2048) uint16 | `solid basecoat/black/…V-D-2.mat`、`…VI-D-2.mat` |
| `spectra_III-B`, `spectra_IV-C` | もう 1 色の濃色の見本 2 枚から 100 本 | `solid basecoat/<もう 1 色>/…III-B-2.mat`、`…IV-C-2.mat` |
| `spectra_II-A` | 白の見本から 100 本 | `solid basecoat/white/…II-A-2.mat` |
| `lines_<見本>`、`n_lines_<見本>` | 抜いた A ラインの番号と、原本の本数 | — |
| `glass_pair` | ガラス板と参照鏡の 2 本 (2, 2048)(論文の図 3、原本の 200・201 本目) | `axial resolution/…III-B-1.mat` |

**改変**: A ラインを原本の 1600〜4000 本から等間隔に 100 本ずつ抜いた。ファイル名を見本の番号だけに付け替えた
(原本のファイル名は色の名前を含む。公開側では「黒」「もう 1 色の濃色」「白」と書く)。値(uint16、暗時の
オフセット約 900 を含む)と波長の較正はそのまま。

## 外部の真値(論文の表 1、µm)

論文の表 1 は同じ見本を OCT・超音波の膜厚計・光学顕微鏡(断面)で測った値を、見本の名前「黒 A / 黒 B /
濃色 A / 濃色 B」で載せている。

| 表の見本 | 透明層 OCT 平均 | 標準偏差 | 超音波 | 顕微鏡 | 着色層 OCT 平均 | 標準偏差 | 超音波 | 顕微鏡 |
|---|---|---|---|---|---|---|---|---|
| 黒 A | 99.8 | 1.33 | 102.4 | 103.3 | 20.9 | 1.71 | 19.8 | 20.6 |
| 黒 B | 72.3 | 1.58 | 74.9 | 74.4 | 15.3 | 1.45 | 15.2 | 14.7 |
| 濃色 A | 44.6 | 1.81 | 45.7 | 45.5 | 11.8 | 2.1 | 11.4 | 12.2 |
| 濃色 B | 85.5 | 1.46 | 87.4 | 87.9 | 15.4 | 2.43 | 17.5 | 18.0 |

厚さへの換算に論文が使った屈折率は透明層 1.56・着色層 1.64(論文の文献 [3]、テラヘルツ帯で測った値。
近赤外の群屈折率ではない)。

★**どのファイルが表のどの行か**は、論文にも原本の ReadMe にも書かれていない。PoC は透明層の厚さだけで対応を
決め(4 つの値 44.6 / 72.3 / 85.5 / 99.8 は互いに 13 µm 以上離れているので、並べ替えは 1 通りに決まる)、
着色層の厚さを**その対応とは独立の**突き合わせに使う。決めた対応では、原本のファイル名の色と表の色名が
入れ替わって見える(黒のファイル 2 枚が表の濃色 A・B に、濃色のファイル 2 枚が表の黒 A・B に当たる)。
理由は分からない —— 確かめられないので、対応は**推定**として扱う。
