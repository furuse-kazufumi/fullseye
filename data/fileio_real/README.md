# 読み込み op の実物ファイル(第三者の公開データ、配布されたバイト列のまま)

`examples/poc_real_file_formats.py` と `tests/test_poc_real_file_formats.py` が読む、公開されている実物の科学データファイル。
**作り直していない** —— 配布元から取得したバイト列をそのまま置き、PoC が読む前にバイト数と SHA-256 を照合する
(台帳は PoC の `BUNDLED`)。ライセンスはファイルごとに違い、Fullseye の Apache-2.0 とは別。取得はすべて 2026-11-04。

| ファイル | バイト数 | SHA-256 | 出典 | ライセンス |
|---|---|---|---|---|
| `sdss_r_ngc2420_skyview_clip.fits` | 653,760 | `c5d93d066a5842ab65b7696d258568a27b106e4a0bbb1ffda83e9431a7de1006` | SDSS DR16 r バンド(散開星団 NGC 2420)、NASA GSFC SkyView が再標本化 | SDSS のデータは public domain、画像は CC BY(表示「Sloan Digital Sky Survey」) |
| `sdss_dr16_ngc2420_photoprimary.csv` | 40,859 | `c3a6546242c47e2c2d549902dc92e5a2785bd5bf3dd3a3c6f55abc6798828bdf` | SDSS DR16 SkyServer の `PhotoPrimary`(同じ視野、psfMag_r < 22) | public domain |
| `ds000117_sub-01_ses-mri_acq-func_magnitude1.nii.gz` | 184,134 | `a2bea15c376a1ce424a7fd44afc0a9dd7346d877e6843ead97bca4dea5f1d47c` | OpenNeuro ds000117 sub-01 の磁場地図の振幅像 | CC0(データセットの `dataset_description.json` の License) |
| `ds000117_sub-01_ses-mri_acq-func_magnitude1.json` | 3,072 | `0c3e78fa87cb2784750bdd88b14b449b8c42142b209d1f6b313fceb867756427` | 同じ像の BIDS の撮像条件(dcm2niix が DICOM から書いた) | CC0 |
| `emd_3197.map.gz` | 29,083 | `a846aadd655eda6a5c2660347978bf1ab9bdefad29ae0af6ebb61cee2d80fe71` | EMDB EMD-3197(wwPDB の書庫 `files.wwpdb.org/pub/emdb/structures/EMD-3197/map/`) | 下記 |
| `emd_3197_published.json` | 1,619 | `acdfc4338aa9b6dd6a39b4c946ed1b9943a9c41f941930bb9ac5c70934324d7f` | EMDB の entry API の `map` 記録の抜き出し(値はそのまま) | 同上 |
| `tubhiswt_C0.ome.tif` / `tubhiswt_C1.ome.tif` | 269,568 ずつ | `a1d99f06…13ef2` / `c17cb626…a51f`(全桁は PoC の台帳) | OME Consortium の見本 OME-TIFF `2016-06/tubhiswt-2D/` | CC BY 4.0(「Sample OME-TIFF files (c) by the OME Consortium」) |

## 出典の詳細

- **SDSS**: 画像は SkyView(<https://skyview.gsfc.nasa.gov/>)に `Survey=SDSSr&Position=NGC 2420&Pixels=400&Size=0.15&Sampler=Clip`
  で要求した(SDSS DR16 の frame 4 枚を面積保存の `Clip` で 1.35″/画素の TAN 投影に再標本化。画素の単位はナノマギー)。
  SDSS の利用条件(<https://www.sdss.org/collaboration/image-use-policy/>): 「All SDSS data released in our public data releases
  are considered in the public domain」、画像は CC BY で表示は「Sloan Digital Sky Survey」。星表は
  <https://skyserver.sdss.org/dr16/> の SQL(`PhotoPrimary` の同じ箱、`psfMag_r < 22`)で取った CSV をそのまま置いた。
- **OpenNeuro ds000117**: D. G. Wakeman, D. Apšvalka, R. N. Henson, "Multisubject, multimodal face processing",
  doi:10.18112/openneuro.ds000117.v2.0.0。論文 Wakeman & Henson, *Sci. Data* 2, 150001 (2015)。
  「This data was obtained from the OpenNeuro database. Its accession number is ds000117」。
- **EMDB EMD-3197**: C. Hagen et al., "Structural Basis of Vesicle Formation at the Inner Nuclear Membrane", 2015,
  doi:10.1016/j.cell.2015.11.029(PrV の核膜からの出芽複合体の部分トモグラム平均、20³、11.4 Å)。EMDB の方針は
  「Upon release, EM data and metadata of an EMDB entry are distributed publicly without restriction」
  (<https://www.ebi.ac.uk/emdb/documentation/policies>)。取得元の wwPDB の利用条件は「Data files contained in the PDB archive
  are available under the CC0 1.0 Universal (CC0 1.0) Public Domain Dedication」(<https://www.wwpdb.org/about/usage-policies>)。
- **OME**: <https://downloads.openmicroscopy.org/images/OME-TIFF/2016-06/tubhiswt-2D/>(同じ場所の `readme.txt` と `COPYING`)。
  2 チャネルを 2 ファイルに分けた「複数ファイルの OME-TIFF」の見本で、各ファイルの OME-XML は組全体(SizeC = 2)を宣言する。

## 同梱しないもの

- **libE57 の試験点群 bunny**(6 つの数値型の E57 と同じ点の PTS 文字版、計 3.1 MB)。配布元
  <http://www.libe57.org/data.html> にデータの再配布の条件が書かれていない(書かれているのはソフトウェアの許諾)ので repo に
  入れない。`py -3.11 tools/fetch_e57_bunny.py` が repo の外へ取得し、`realdata.E57_BUNNY_FILES` の SHA-256 を照合する。
  取得していない環境では、PoC は同梱のイトカワ形状(`data/itokawa_shape/`、CC0)を pye57 で直接書いた E57 で章を回す。
