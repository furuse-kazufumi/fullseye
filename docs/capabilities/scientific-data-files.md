---
id: scientific-data-files
title: 科学データのファイルを読む(FITS・NIfTI・MRC・OME-TIFF・E57)
title_en: Reading scientific data files (FITS, NIfTI, MRC, OME-TIFF, E57)
category: 組み立てる
ops: [astro_fits_read, nifti_read, em_mrc_read, ome_tiff_read, e57_read, nrrd_read]
examples: [poc_real_file_formats]
version: 0.9.0
inputs: [any]
pipeline: [astro_fits_read]
alternatives: [nifti_read, em_mrc_read, ome_tiff_read, e57_read, nrrd_read, star_detect, aperture_photometry, vol_label, vol_region_props]
limits: FITS は primary HDU だけ(拡張 HDU・BLANK・random groups は拒否)。MRC は格子の起点 NXSTART を返さない。OME-TIFF は 1 ファイルで完結し物理サイズとチャネル名を持つものだけ(複数ファイルの組は拒否)。NRRD は空間の単位の明示が要る。E57 は 1 scan だけ。
calibration: 物理寸法はファイルのヘッダから読む(FITS は WCS の度、NIfTI は mm、MRC は Å、OME-TIFF は宣言された単位)。ヘッダに無い寸法は推測しない。
---

# 科学データのファイルを読む(FITS・NIfTI・MRC・OME-TIFF・E57)

## できること

天文の FITS、脳画像の NIfTI-1、電子顕微鏡の MRC2014、顕微鏡の OME-TIFF、3-D スキャナの E57 を、ファイルの `bytes` から
`(配列, meta)`(E57 は点群の表)にします。`meta` には寸法を持つ量を単位つきで入れます —— FITS の基本 WCS、NIfTI の qform /
sform と画素間隔(mm)、MRC のボクセル寸法(Å)、OME-TIFF の物理サイズ、E57 の pose。読んだ配列はそのまま 2-D / 3-D の op
(`star_detect`・`aperture_photometry`・`otsu`・`vol_label`・`vol_region_props`・`obb` など)へ渡せます。

壊れたファイル・宣言と中身の食い違い・扱えない拡張は、黙って読まずに**名指しで拒否**します。たとえば 2 チャネルを 2 ファイルに
分けた OME-TIFF の片方は「XML は 2 頁を宣言、1 頁しか無い」と拒否します(参照実装の tifffile は、バイト列だけを渡すと欠けた
チャネルをゼロで埋めて返します)。

PoC `poc_real_file_formats` は、公開されている実物のファイル(SDSS・OpenNeuro・EMDB・OME・libE57)を配布されたバイト列のまま読み、
astropy / nibabel / mrcfile / tifffile と全画素で一致すること、配布元の公表値(星表の等級、撮像条件、EMDB の統計量)と一致することを
門にしています。

## What it does

Turns the bytes of astronomy FITS, neuroimaging NIfTI-1, electron-microscopy MRC2014, microscopy OME-TIFF and 3-D scanner E57 files
into `(array, meta)` (a point table for E57), with dimensioned quantities carried with their units: the basic FITS WCS, NIfTI qform /
sform and voxel spacing in mm, MRC voxel size in angstrom, OME-TIFF physical sizes, E57 pose. The arrays feed straight into Fullseye's
2-D / 3-D operators. Corrupt files, header/content disagreements and unsupported extensions are refused by name rather than read
silently. The PoC reads real public files byte-for-byte and checks them against astropy, nibabel, mrcfile and tifffile pixel for pixel
and against the providers' published values.

## 向くところ / 向かないところ

**向く**: 公開データや装置の出力を、外部の重い依存なしに(FITS・MRC・NIfTI は標準ライブラリと numpy だけ)配列にして、そのまま
計測の op へ渡す。ヘッダの寸法を単位つきで受け取り、画素の大きさを推測しない。受け取ったファイルの束から、読めない物を理由つきで
選り分ける。

**向かない**: FITS の拡張 HDU(多くの装置の生データは primary の後ろに画像や表を持つ)、整数の BLANK、圧縮 FITS。MRC の extended
header と非標準の軸順。複数ファイルに分けた OME-TIFF の組と、物理サイズやチャネル名の無い OME-TIFF。複数 scan の E57。これらは
すべて拒否します(黙って一部だけ読むことはしない)。

## 推奨パイプライン

`astro_fits_read`

ファイルの `bytes` を読み込み op に渡し(FITS なら `astro_fits_read`)、返った `meta` の寸法と単位を先に確かめてから、配列を計測の
op へ渡す(星なら `star_detect` → `aperture_photometry`、体積なら `otsu` → `vol_label` → `vol_region_props`)。読み込み op の出力は
`(配列, meta)` の組なので、型の連鎖は読み込み op で一度切れる(配列を取り出して次へ渡す)。

## 代替

脳画像は `nifti_read`、電顕の密度地図は `em_mrc_read`、顕微鏡のスタックは `ome_tiff_read`、点群は `e57_read`、医用の NRRD は
`nrrd_read`。各形式に対の書き出し op(`astro_fits_write` など)があり、往復で値が保たれることを試験しています。

## 限界

- FITS は primary HDU の 2-D / 3-D 画像だけ。拡張 HDU・random groups・整数の BLANK は拒否する。WCS は基本のキー(CTYPE・CRPIX・
  CRVAL・CDELT・PC・CD・CUNIT など)だけを返し、歪みの多項式(SIP など)は返さない。
- MRC は mode 0/1/2/6 だけ。`em_mrc_read` は格子の起点(NXSTART / NYSTART / NZSTART)を返さないので、起点が 0 でない地図
  (EMD-3197 は −2)を空間に置くと 1 ボクセル単位でずれる(PoC に記録した門)。
- NIfTI は単一ファイルの NIfTI-1(`.nii` / `.nii.gz`)だけ。qform の四元数は参照実装 nifti1_io.c と同じ規則で行列にする
  (1 − |bcd|² < 1e-7 なら 180° 回転とみなす。2026-11-04 に PoC の実物で見つけて直した)。
- OME-TIFF は 1 ファイルで完結し、物理サイズと全チャネルの名前を宣言したものだけ。E57 は 1 scan だけで、読み手は pye57(任意の依存)。

## 実寸校正

物理寸法はすべてファイルのヘッダから読む: FITS は WCS(度)、NIfTI は画素間隔(mm、`spatial_unit`)、MRC はボクセル寸法(Å)、
OME-TIFF は宣言された単位。ヘッダに寸法が無ければ推測せず拒否するか `None` を返す。画素の明るさの校正(FITS の BZERO / BSCALE、
NIfTI の scl_slope)はファイルの規約どおりに当てる。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

# 小さな FITS を書いて読み戻す(実物は examples/poc_real_file_formats.py が data/fileio_real/ から読む)
img = np.arange(12, dtype=np.float32).reshape(3, 4)
payload = fs.astro_fits_write(img, header={"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN",
                                           "CRPIX1": 2.0, "CRPIX2": 1.5, "CRVAL1": 114.6, "CRVAL2": 21.6,
                                           "CDELT1": -0.000375, "CDELT2": 0.000375})
back, meta = fs.astro_fits_read(payload)
print(np.array_equal(back, img), meta["wcs"]["CDELT2"])          # True 0.000375
```

走らせて見るなら `py -3.11 examples/poc_real_file_formats.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
