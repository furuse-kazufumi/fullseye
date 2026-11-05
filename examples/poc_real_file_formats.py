# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""公開されている実物の科学データファイルを Fullseye の読み込み op で読み、外の読み手と公表値で採点する。

読むファイルはすべて第三者が公開した**実物**で、作り直していない(``data/fileio_real/`` に
配布されたバイト列のまま同梱、SHA-256 を下の :data:`BUNDLED` に固定)。出典とライセンスは
``data/fileio_real/README.md``。各章の門は 3 段:

1. **外の参照実装と一致**: astropy / nibabel / mrcfile / tifffile で同じバイト列を読み、
   形状・dtype・画素(全数の完全一致)・ヘッダの主要値を突き合わせる。
2. **配布元の公表値と一致**: FITS は SDSS DR16 の星表、NIfTI は BIDS の JSON(撮像条件)、
   MRC は EMDB の登録値(寸法・画素間隔・統計量・推奨等値面)。
3. **読んだ後に op を 1〜2 段かけて意味のある結果**: 星を数えて SDSS の等級を再現する、
   頭部の体積、密度地図の塊の体積、点群の外形寸法。

章:

* FITS(SDSS r バンド、散開星団 NGC 2420、SkyView の面積保存の再標本化)
  → ``astro_fits_read`` → ``star_detect`` → ``aperture_photometry``。
* NIfTI(OpenNeuro ds000117 の磁場地図の振幅像、CC0)→ ``nifti_read`` → ``otsu`` →
  ``vol_label`` / ``vol_region_props``。
* MRC(EMDB EMD-3197 の部分トモグラム平均)→ ``em_mrc_read`` → 等値面 → ``vol_label`` /
  ``vol_region_props``。
* OME-TIFF(OME の公開見本 tubhiswt-2D、CC BY 4.0)→ ``ome_tiff_read`` が**拒否する**ことと、
  その理由が事実であることを独立に確かめる(1 ファイルに 1 チャネルしか無い複数ファイル組)。
* E57(libE57 の公開試験点群 bunny、6 つの数値型)→ ``e57_read`` を同じ点の PTS 文字版と
  照合。原本は再配布の条件が書かれていないので**同梱しない**(``tools/fetch_e57_bunny.py`` で
  repo 外へ取得し SHA-256 を照合)。取得していない環境(CI)では代わりに、同梱の
  イトカワ形状(CC0)を pye57 で直接書いた E57 を読み、頂点を PDS ラベルの数・格納値と比べる
  (外形は Fujiwara ほか 2006 の 535 × 294 × 209 m と 5〜21 % 食い違うので印字だけ。理由は未確認)。

★経緯(2026-11-04): 最初は SkyView の既定の再標本化(最近傍)で取った M67 の画像を使い、
開口測光の傾きが 0.52 になった。原因は 2 つ —— 最近傍は 0.396″ の原画素を 1.35″ の格子から
飛び飛びに拾うので星の光が保存されない(``Sampler=Clip`` の面積保存で取り直した)、M67 の
星は SDSS で飽和する(星表の 15〜17 等の 22 % に SATURATED の旗)。飽和しない遠い星団
NGC 2420 に替え、飽和の旗の付いた星を採点から外した。

実行例::

    py -3.11 examples/poc_real_file_formats.py
    py -3.11 tools/fetch_e57_bunny.py     # 任意: E57 の章を libE57 の原本で回す

図(``FULLSEYE_FIGURE_DIR`` があるときだけ): 星の検出と照合(代表図)、等級の再現、
MRI の断面と頭部の領域、密度地図の断面と等値面、E57 点群の投影、形式ごとの判定の表。
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import logging
import math
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import realdata  # noqa: E402

DATA = ROOT / "data" / "fileio_real"

#: 同梱した実物ファイル: 名前 → (バイト数, SHA-256)。2026-11-04 に配布元から取得した値。
BUNDLED = {
    "sdss_r_ngc2420_skyview_clip.fits":
        (653760, "c5d93d066a5842ab65b7696d258568a27b106e4a0bbb1ffda83e9431a7de1006"),
    "sdss_dr16_ngc2420_photoprimary.csv":
        (40859, "c3a6546242c47e2c2d549902dc92e5a2785bd5bf3dd3a3c6f55abc6798828bdf"),
    "ds000117_sub-01_ses-mri_acq-func_magnitude1.nii.gz":
        (184134, "a2bea15c376a1ce424a7fd44afc0a9dd7346d877e6843ead97bca4dea5f1d47c"),
    "ds000117_sub-01_ses-mri_acq-func_magnitude1.json":
        (3072, "0c3e78fa87cb2784750bdd88b14b449b8c42142b209d1f6b313fceb867756427"),
    "emd_3197.map.gz":
        (29083, "a846aadd655eda6a5c2660347978bf1ab9bdefad29ae0af6ebb61cee2d80fe71"),
    "emd_3197_published.json":
        (1619, "acdfc4338aa9b6dd6a39b4c946ed1b9943a9c41f941930bb9ac5c70934324d7f"),
    "tubhiswt_C0.ome.tif":
        (269568, "a1d99f0651baad26a6b5004c115a9c3f4e33d3d6e0b279b34cabbbe88d813ef2"),
    "tubhiswt_C1.ome.tif":
        (269568, "c17cb626103d9a8b3f77b0d49fbff67ced2a6da83f6b2ae8beae183fb1a2a51f"),
}

SOURCE_FITS = ("Sloan Digital Sky Survey DR16 r-band frames (public domain data; images CC BY, "
               "credit SDSS), resampled by NASA GSFC SkyView with the area-weighted Clip sampler")
SOURCE_NIFTI = ("OpenNeuro ds000117 (Wakeman, Apšvalka & Henson; doi:10.18112/openneuro.ds000117.v2.0.0), "
                "CC0")
SOURCE_MRC = ("EMDB EMD-3197 (Hagen et al. 2015, doi:10.1016/j.cell.2015.11.029), "
              "distributed without restriction; wwPDB archive CC0 1.0")
SOURCE_OME = "OME Consortium sample OME-TIFF tubhiswt-2D, CC BY 4.0"
SOURCE_E57 = "libE57 E57 example data (bunny, Stanford 3D Scanning Repository origin), not redistributed"
SOURCE_ITOKAWA = ("Gaskell Itokawa Shape Model V1.1 (NASA PDS, doi:10.26033/3b2j-yy57), CC0 1.0, "
                  "written to E57 by pye57 for this check")

#: SDSS の ``flags`` の SATURATED ビット(SDSS DR16 の PhotoFlags の表)。
SDSS_SATURATED = 1 << 18
#: 星表と検出を同一とみなす角距離[秒角]。再標本化の画素 1.35″ と同程度。
MATCH_ARCSEC = 1.0
#: 採点に使う星の等級範囲(明るい側は飽和、暗い側は S/N の不足で外す)。
MAG_LO, MAG_HI = 15.0, 20.0
#: SDSS の画像の単位はナノマギー: m = 22.5 − 2.5 log10(F)(SDSS DR16 の flux の説明)。
NMGY_ZERO = 22.5
#: イトカワの外形寸法 535 × 294 × 209 m(Fujiwara et al., Science 312, 1330 (2006))。門にはしない:
#: この形状モデル(Gaskell Q = 64)の慣性主軸に沿った長さは 5〜21 % 大きく、理由は未確認
#: (``tools/build_itokawa_anim3d.py`` の限界の行と同じ)。比べた値を印字するだけにする。
ITOKAWA_DIMENSIONS_M = (535.0, 294.0, 209.0)
#: 形状モデル ver64q の頂点数(PDS4 ラベル ver64q.xml の records、``data/itokawa_shape/README.md``)。
ITOKAWA_VERTICES = 25350


class FormatGateError(AssertionError):
    """門を通らなかった(どの形式の何が外れたかを名指しする)。"""


def _require(module: str):
    """参照実装を import する。無ければ黙って章を飛ばさず止まる(fail-closed)。"""
    try:
        return __import__(module, fromlist=["_"])
    except ImportError as exc:
        raise SystemExit("参照実装 %s が無い: `pip install -e .[export-verify]` で入れる(%s)"
                         % (module, exc)) from exc


def load_bundled(name: str) -> bytes:
    """同梱ファイルを読み、バイト数と SHA-256 が台帳と一致したときだけ返す。"""
    if name not in BUNDLED:
        raise KeyError("台帳に無い同梱ファイル: %s" % name)
    size, digest = BUNDLED[name]
    path = DATA / name
    if not path.is_file():
        raise realdata.RealDataError("同梱の実データが無い: data/fileio_real/%s" % name)
    raw = path.read_bytes()
    if len(raw) != size:
        raise realdata.RealDataError("%s のバイト数 %d が台帳 %d と違う" % (name, len(raw), size))
    got = hashlib.sha256(raw).hexdigest()
    if got != digest:
        raise realdata.RealDataError("%s の SHA-256 %s が台帳と違う" % (name, got))
    realdata.mark_read("fileio-real:" + name)   # 成熟度台帳の「実データを読んだ」記録(D6)
    return raw


class Gates:
    """門を 1 つずつ記録し、最後にまとめて判定する(どれが外れたかを全部出す)。"""

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, bool, str]] = []

    def check(self, fmt: str, name: str, ok, detail: str = "") -> bool:
        ok = bool(ok)
        self.rows.append((fmt, name, ok, detail))
        print("  [%s] %s %s%s" % ("OK" if ok else "NG", fmt, name, (" — " + detail) if detail else ""))
        return ok

    def failed(self) -> list[tuple[str, str, bool, str]]:
        return [r for r in self.rows if not r[2]]


def _finite(*values) -> bool:
    return all(math.isfinite(float(v)) for v in values)


# --------------------------------------------------------------------------- #
# FITS
# --------------------------------------------------------------------------- #
def tan_pix2world(wcs: dict, x1, y1):
    """FITS の 1 始まり画素 (x, y) を、基本 WCS(TAN、CDELT のみ)で赤経・赤緯[度]にする。

    ``astro_fits_read`` が返した ``meta['wcs']`` だけを使う独立の実装(Calabretta & Greisen
    2002 の gnomonic 投影)。PC / CD 行列は扱わない —— 入っていれば拒否する。
    """
    if not (str(wcs.get("CTYPE1", "")).endswith("-TAN") and str(wcs.get("CTYPE2", "")).endswith("-TAN")):
        raise ValueError("tan_pix2world: TAN 以外の投影 %r / %r" % (wcs.get("CTYPE1"), wcs.get("CTYPE2")))
    if any(k.startswith(("PC", "CD")) and k[2:3].isdigit() for k in wcs):
        raise ValueError("tan_pix2world: PC/CD 行列は扱わない")
    xi = np.radians(wcs["CDELT1"] * (np.asarray(x1, float) - wcs["CRPIX1"]))
    eta = np.radians(wcs["CDELT2"] * (np.asarray(y1, float) - wcs["CRPIX2"]))
    a0, d0 = math.radians(wcs["CRVAL1"]), math.radians(wcs["CRVAL2"])
    den = math.cos(d0) - eta * math.sin(d0)
    ra = np.degrees(a0 + np.arctan2(xi, den)) % 360.0
    dec = np.degrees(np.arctan2(math.sin(d0) + eta * math.cos(d0), np.hypot(xi, den)))
    return ra, dec


def _unit_vectors(ra_deg, dec_deg) -> np.ndarray:
    ra, dec = np.radians(ra_deg), np.radians(dec_deg)
    return np.c_[np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)]


def read_sdss_catalog(raw: bytes) -> dict[str, np.ndarray]:
    """SkyServer の CSV(先頭行 ``#Table1``)を列ごとの配列にする。"""
    lines = raw.decode("ascii").splitlines()
    if not lines or lines[0].strip() != "#Table1":
        raise ValueError("SDSS CSV の先頭が #Table1 でない")
    rows = list(csv.DictReader(lines[1:]))
    if not rows:
        raise ValueError("SDSS CSV が空")
    return {"ra": np.array([float(r["ra"]) for r in rows]),
            "dec": np.array([float(r["dec"]) for r in rows]),
            "r": np.array([float(r["psfMag_r"]) for r in rows]),
            "type": np.array([int(r["type"]) for r in rows]),
            "flags": np.array([int(r["flags"]) for r in rows], dtype=np.int64)}


def chapter_fits(g: Gates) -> dict:
    print("\n== FITS: SDSS r バンド、散開星団 NGC 2420(%s)" % SOURCE_FITS)
    fits = _require("astropy.io.fits")
    wcs_mod = _require("astropy.wcs")
    raw = load_bundled("sdss_r_ngc2420_skyview_clip.fits")
    image, meta = fs.astro_fits_read(raw)
    with fits.open(io.BytesIO(raw)) as hdul:
        n_hdu = len(hdul)
        header = hdul[0].header.copy()
        ref = np.asarray(hdul[0].data).copy()
    g.check("FITS", "HDU は 1 つ(primary だけ)", n_hdu == 1, "astropy %d" % n_hdu)
    g.check("FITS", "形状・dtype が astropy と一致", image.shape == ref.shape
            and image.dtype == ref.dtype.newbyteorder("="), "%s %s" % (image.shape, image.dtype))
    g.check("FITS", "全画素が astropy と完全一致", np.array_equal(image, ref, equal_nan=True),
            "%d 画素" % image.size)
    g.check("FITS", "画素が全部有限で定数でない", np.isfinite(image).all() and float(np.ptp(image)) > 0,
            "範囲 %.4g〜%.4g nmgy" % (image.min(), image.max()))
    wcs = meta["wcs"]
    same = [k for k in wcs if header.get(k) == wcs[k]]
    g.check("FITS", "WCS の全キーが astropy のヘッダと一致", len(same) == len(wcs) >= 8,
            "%d / %d キー" % (len(same), len(wcs)))
    # 公表値: SkyView への要求(0.15 度角を 400 画素、天体名 NGC 2420)と SURVEY の札。
    g.check("FITS", "画素間隔 = 要求 0.15°/400", abs(abs(wcs["CDELT1"]) - 0.15 / 400) < 1e-12
            and abs(wcs["CDELT2"] - 0.15 / 400) < 1e-12, "%.6g°" % wcs["CDELT2"])
    g.check("FITS", "SURVEY 札が SDSS-r", str(header.get("SURVEY", "")).strip() == "SDSS-r")

    stars = fs.star_detect(image, threshold_sigma=5.0, min_separation=3, max_stars=2000)
    phot = fs.aperture_photometry(image, stars, r_aperture=4.0, r_inner=7.0, r_outer=11.0)
    flux = np.array([p["flux"] for p in phot])
    ra, dec = tan_pix2world(wcs, stars[:, 1] + 1.0, stars[:, 0] + 1.0)
    ra_ref, dec_ref = wcs_mod.WCS(header).all_pix2world(stars[:, 1], stars[:, 0], 0)
    wcs_err = float(max(np.abs(ra - ra_ref).max(), np.abs(dec - dec_ref).max()) * 3600.0)
    g.check("FITS", "読んだ WCS からの天球座標 = astropy.wcs", wcs_err < 1e-6, "最大差 %.2e″" % wcs_err)

    cat = read_sdss_catalog(load_bundled("sdss_dr16_ngc2420_photoprimary.csv"))
    px, py = wcs_mod.WCS(header).all_world2pix(cat["ra"], cat["dec"], 0)
    h, w = image.shape
    inside = (px > 6) & (px < w - 7) & (py > 6) & (py < h - 7)
    saturated = (cat["flags"] & SDSS_SATURATED) != 0
    scored = inside & (cat["type"] == 6) & ~saturated & (cat["r"] >= MAG_LO) & (cat["r"] < MAG_HI)
    dist, nearest = cKDTree(_unit_vectors(ra, dec)).query(_unit_vectors(cat["ra"], cat["dec"]))
    sep = np.degrees(dist) * 3600.0
    matched = scored & (sep < MATCH_ARCSEC)
    completeness = float(matched.sum() / max(1, scored.sum()))
    sep_med = float(np.median(sep[matched])) if matched.any() else float("nan")
    mag = NMGY_ZERO - 2.5 * np.log10(np.where(flux > 0, flux, np.nan))
    x, y = cat["r"][matched], mag[nearest[matched]]
    ok = np.isfinite(y)
    A = np.c_[x[ok], np.ones(int(ok.sum()))]
    slope, icpt = np.linalg.lstsq(A, y[ok], rcond=None)[0]
    resid = y[ok] - (slope * x[ok] + icpt)
    robust = float(1.4826 * np.median(np.abs(resid - np.median(resid))))
    offset = float(np.median(y[ok] - x[ok]))
    print("  検出 %d 個 / 採点する星表の星 %d 個(%.0f〜%.0f 等、飽和の旗なし)/ %.1f″ 以内に対応 %d 個"
          % (len(stars), scored.sum(), MAG_LO, MAG_HI, MATCH_ARCSEC, matched.sum()))
    g.check("FITS", "星表の星の再現率 ≥ 0.90", completeness >= 0.90, "%.3f" % completeness)
    g.check("FITS", "位置のずれの中央値 < 0.2″", sep_med < 0.2, "%.3f″" % sep_med)
    g.check("FITS", "等級の傾き 1 ± 0.05(読んだ画素が線形)", abs(slope - 1.0) < 0.05, "%.4f" % slope)
    g.check("FITS", "零点 22.5 で SDSS の等級に一致(中央値 |Δ| < 0.05 等)", abs(offset) < 0.05,
            "%+.4f 等" % offset)
    g.check("FITS", "等級の頑健なばらつき < 0.1 等", robust < 0.1, "%.4f 等(n=%d)" % (robust, ok.sum()))
    g.check("FITS", "数値が全部有限", _finite(slope, icpt, robust, offset, sep_med))
    return {"image": image, "stars": stars, "cat_px": np.c_[px, py], "scored": scored, "matched": matched,
            "x_mag": x[ok], "y_mag": y[ok], "n_detected": int(len(stars)), "n_scored": int(scored.sum()),
            "n_matched": int(matched.sum()), "completeness": completeness, "sep_median_arcsec": sep_med,
            "slope": float(slope), "offset_mag": offset, "robust_mag": robust, "wcs_err_arcsec": wcs_err,
            "n_catalog_saturated_inside": int((inside & saturated).sum())}


# --------------------------------------------------------------------------- #
# NIfTI
# --------------------------------------------------------------------------- #
def chapter_nifti(g: Gates) -> dict:
    print("\n== NIfTI: 磁場地図の振幅像(%s)" % SOURCE_NIFTI)
    nib = _require("nibabel")
    _require("skimage.filters")
    from skimage.filters import threshold_otsu
    raw = load_bundled("ds000117_sub-01_ses-mri_acq-func_magnitude1.nii.gz")
    side = json.loads(load_bundled("ds000117_sub-01_ses-mri_acq-func_magnitude1.json").decode("utf-8"))
    vol, meta = fs.nifti_read(raw)
    img = nib.Nifti1Image.from_bytes(gzip.decompress(raw))
    ref = np.asanyarray(img.dataobj)
    g.check("NIfTI", "形状・dtype が nibabel と一致", vol.shape == ref.shape and vol.dtype == ref.dtype,
            "%s %s" % (vol.shape, vol.dtype))
    g.check("NIfTI", "全ボクセルが nibabel と完全一致", np.array_equal(vol, ref), "%d ボクセル" % vol.size)
    g.check("NIfTI", "qform / sform が nibabel と一致(1e-5 mm)",
            np.allclose(meta["qform_affine"], img.get_qform(), atol=1e-5)
            and np.allclose(meta["sform_affine"], img.get_sform(), atol=1e-5)
            and meta["qform_code"] == int(img.header["qform_code"])
            and meta["sform_code"] == int(img.header["sform_code"]))
    g.check("NIfTI", "画素間隔と単位が nibabel と一致",
            np.allclose(meta["pixdim"], img.header.get_zooms()[:3])
            and (meta["spatial_unit"], "s" if meta["time_unit"] == "s" else meta["time_unit"])
            == (img.header.get_xyzt_units()[0], "s"), "%s %s" % (meta["pixdim"].tolist(), meta["spatial_unit"]))
    # 公表値(BIDS の JSON = 撮像装置が書いた撮像条件)。
    g.check("NIfTI", "面内の行列 = BaseResolution / AcquisitionMatrixPE",
            vol.shape[0] == side["BaseResolution"] and vol.shape[1] == side["AcquisitionMatrixPE"],
            "%d×%d" % vol.shape[:2])
    g.check("NIfTI", "スライス数 = SliceTiming の個数", vol.shape[2] == len(side["SliceTiming"]),
            "%d" % vol.shape[2])
    g.check("NIfTI", "スライス間隔 = SpacingBetweenSlices", abs(meta["pixdim"][2] - side["SpacingBetweenSlices"]) < 1e-6,
            "%.3f mm(厚さ %.1f mm、隙間 %.2f mm)" % (meta["pixdim"][2], side["SliceThickness"],
                                                 meta["pixdim"][2] - side["SliceThickness"]))
    lps = np.asarray(side["ImageOrientationPatientDICOM"], float).reshape(2, 3)
    ras = lps * np.array([-1.0, -1.0, 1.0])
    cols = meta["sform_affine"][:3, :2] / np.linalg.norm(meta["sform_affine"][:3, :2], axis=0)
    dots = [abs(float(cols[:, k] @ ras[k])) for k in range(2)]
    tilt = math.degrees(math.atan2(abs(cols[2, 1]), abs(cols[1, 1])))
    want = abs(float(re.search(r"\(([-0-9.]+)\)", side["ImageOrientationText"]).group(1)))
    g.check("NIfTI", "向き = ImageOrientationPatientDICOM(|cos| > 0.99999)", min(dots) > 0.99999,
            "%.7f / %.7f" % tuple(dots))
    g.check("NIfTI", "傾き = ImageOrientationText の %.1f°" % want, abs(tilt - want) < 0.05, "%.3f°" % tilt)

    mosaic = vol.reshape(-1, vol.shape[-1]).astype(np.float64)
    head = np.asarray(fs.op.otsu(mosaic)).reshape(vol.shape) > 0.5
    ref_mask = vol > threshold_otsu(vol)
    agree = float((head == ref_mask).mean())
    labels, n = fs.vol_label(head, connectivity=26)
    props = fs.vol_region_props(labels, spacing=tuple(float(v) for v in meta["pixdim"]))
    largest = max(props, key=lambda p: p["voxel_count"])
    head_ml = float(largest["volume"]) / 1000.0
    fov_ml = float(np.prod(np.asarray(vol.shape) * meta["pixdim"])) / 1000.0
    g.check("NIfTI", "大津の領域が skimage の大津と 99 % 以上一致", agree >= 0.99, "%.4f" % agree)
    g.check("NIfTI", "最大成分の体積が視野の中で空でも全部でもない", 0.2 * fov_ml < head_ml < 0.8 * fov_ml,
            "%.0f mL(視野 %.0f mL)" % (head_ml, fov_ml))
    return {"vol": vol, "mask": labels == largest["label"], "head_ml": head_ml, "fov_ml": fov_ml,
            "otsu_agree": agree, "tilt_deg": tilt, "n_components": int(n),
            "shape": tuple(int(s) for s in vol.shape), "pixdim": [float(v) for v in meta["pixdim"]]}


# --------------------------------------------------------------------------- #
# MRC
# --------------------------------------------------------------------------- #
def _published_value(node) -> float:
    return float(node["valueOf_"]) if isinstance(node, dict) else float(node)


def chapter_mrc(g: Gates) -> dict:
    print("\n== MRC: EMD-3197(%s)" % SOURCE_MRC)
    mi = _require("mrcfile.mrcinterpreter")
    raw = gzip.decompress(load_bundled("emd_3197.map.gz"))
    pub = json.loads(load_bundled("emd_3197_published.json").decode("utf-8"))["map"]
    vol, meta = fs.em_mrc_read(raw)
    ref = mi.MrcInterpreter(iostream=io.BytesIO(raw), permissive=False)
    try:
        g.check("MRC", "形状・dtype が mrcfile と一致", vol.shape == ref.data.shape
                and vol.dtype == ref.data.dtype.newbyteorder("="), "%s %s" % (vol.shape, vol.dtype))
        g.check("MRC", "全ボクセルが mrcfile と完全一致", np.array_equal(vol, ref.data), "%d ボクセル" % vol.size)
        vs = ref.voxel_size
        g.check("MRC", "ボクセル寸法が mrcfile と一致",
                np.allclose(meta["voxel_size"], [vs.x, vs.y, vs.z]), "%s Å" % meta["voxel_size"].tolist())
        start = (int(ref.header.nxstart), int(ref.header.nystart), int(ref.header.nzstart))
    finally:
        ref.close()
    dims = (int(pub["dimensions"]["sec"]), int(pub["dimensions"]["row"]), int(pub["dimensions"]["col"]))
    g.check("MRC", "寸法 = EMDB の登録値", vol.shape == dims, "%s" % (dims,))
    spacing = [_published_value(pub["pixel_spacing"][k]) for k in ("x", "y", "z")]
    g.check("MRC", "画素間隔 = EMDB の登録値", np.allclose(meta["voxel_size"], spacing), "%s Å" % spacing)
    cell = [_published_value(pub["cell"][k]) for k in ("a", "b", "c")]
    g.check("MRC", "単位胞 = 画素間隔 × 寸法", np.allclose(cell, meta["voxel_size"] * np.asarray(vol.shape[::-1])),
            "%s Å" % cell)
    st = pub["statistics"]
    got = {"minimum": float(vol.min()), "maximum": float(vol.max()), "average": float(vol.mean(dtype=np.float64)),
           "std": float(vol.std(dtype=np.float64))}
    rel = max(abs(got[k] - float(st[k])) / max(1e-12, abs(float(st[k]))) for k in got)
    g.check("MRC", "最小・最大・平均・標準偏差 = EMDB の統計量(相対 1e-6)", rel < 1e-6, "最大の相対差 %.1e" % rel)
    pub_start = (int(pub["origin"]["col"]), int(pub["origin"]["row"]), int(pub["origin"]["sec"]))
    g.check("MRC", "mrcfile の格子の起点 = EMDB の origin(col, row, sec)", start == pub_start, "%s" % (pub_start,))
    # ★記録した穴: em_mrc_read の meta は NXSTART を返さないので、この地図を空間に置くと
    #   x が 2 ボクセル = 22.8 Å ずれる。塞がったら(meta に起点が載ったら)この門が鳴る。
    has_start = any("start" in k for k in meta)
    g.check("MRC", "既知の穴: em_mrc_read は格子の起点(NXSTART)を返さない", not has_start,
            "EMDB の起点 col %d = %.1f Å が meta に無い" % (pub_start[0], pub_start[0] * spacing[0]))

    level = float(pub["contour_list"]["contour"][0]["level"])
    body = vol > level
    labels, n = fs.vol_label(body, connectivity=26)
    props = fs.vol_region_props(labels, spacing=tuple(float(v) for v in meta["voxel_size"][::-1]))
    volumes_nm3 = sorted((float(p["volume"]) / 1000.0 for p in props), reverse=True)
    total = float(body.sum() * np.prod(meta["voxel_size"]) / 1000.0)
    g.check("MRC", "推奨等値面 %.2f の中身が空でも全部でもない" % level, 0 < body.sum() < body.size,
            "%d / %d ボクセル" % (body.sum(), body.size))
    g.check("MRC", "成分の体積の和 = ボクセル数 × 体積", abs(sum(volumes_nm3) - total) < 1e-6 * total,
            "%.1f nm³ / %d 成分" % (total, n))
    return {"vol": vol, "body": body, "level": level, "n_components": int(n), "volumes_nm3": volumes_nm3,
            "total_nm3": total, "stat_rel": rel, "start": pub_start}


# --------------------------------------------------------------------------- #
# OME-TIFF
# --------------------------------------------------------------------------- #
def _ome_xml(raw: bytes) -> str:
    a, b = raw.find(b"<OME"), raw.find(b"</OME>")
    if a < 0 or b < 0:
        raise ValueError("OME-XML が見つからない")
    return raw[a:b + 6].decode("utf-8")


def chapter_ome(g: Gates) -> dict:
    print("\n== OME-TIFF: tubhiswt-2D(%s)" % SOURCE_OME)
    tifffile = _require("tifffile")
    raws = {c: load_bundled("tubhiswt_%s.ome.tif" % c) for c in ("C0", "C1")}
    # tifffile は欠けた頁を警告のログで知らせるだけ —— 端末を汚さないよう、この章の間だけ黙らせる
    # (黙らせても下の門が「ゼロで埋めた」ことを数値で確かめる)。
    log = logging.getLogger("tifffile")
    prev = log.level
    log.setLevel(logging.CRITICAL)
    try:
        return _chapter_ome(g, tifffile, raws)
    finally:
        log.setLevel(prev)


def _chapter_ome(g: Gates, tifffile, raws: dict) -> dict:
    refusals = {}
    for c, raw in raws.items():
        try:
            fs.ome_tiff_read(raw)
            refusals[c] = None
        except ValueError as exc:
            refusals[c] = str(exc)
    for c, msg in refusals.items():
        g.check("OME-TIFF", "%s を拒否(1 ファイルに頁が足りない)" % c,
                msg is not None and "declare 2 TIFF pages, found 1" in msg, msg or "読めてしまった")
    xml = _ome_xml(raws["C0"])
    size_c = int(re.search(r'SizeC="(\d+)"', xml).group(1))
    files = set(re.findall(r'FileName="([^"]+)"', xml))
    g.check("OME-TIFF", "拒否の理由は事実: XML は SizeC=2 を 2 ファイルに分けて宣言",
            size_c == 2 and files == {"tubhiswt_C0.ome.tif", "tubhiswt_C1.ome.tif"},
            "SizeC=%d、%s" % (size_c, sorted(files)))
    pages = {}
    for c, raw in raws.items():
        with tifffile.TiffFile(io.BytesIO(raw)) as tif:
            pages[c] = len(tif.pages)
    g.check("OME-TIFF", "拒否の理由は事実: 各ファイルの TIFF の頁は 1 枚", pages == {"C0": 1, "C1": 1}, "%s" % pages)
    # 参照実装はバイト列だけを渡されると、もう 1 枚を**黙ってゼロで埋める**(警告のログだけ)。
    with tifffile.TiffFile(io.BytesIO(raws["C0"])) as tif:
        filled = tif.asarray()
    with tifffile.TiffFile(io.BytesIO(raws["C1"])) as tif:
        own_c1 = tif.pages[0].asarray()
    zero_filled = filled.shape == (2, 512, 512) and not filled[1].any() and own_c1.any()
    g.check("OME-TIFF", "tifffile はバイト列から C1 をゼロで埋めて返す(実物の C1 は非ゼロ)", zero_filled,
            "埋めた C1 の最大 %d、実物の C1 の最大 %d" % (int(filled[1].max()), int(own_c1.max())))
    no_phys = "PhysicalSizeX" not in xml
    no_names = not re.search(r"<Channel [^>]*Name=", xml)
    g.check("OME-TIFF", "2 ファイルを束ねても足りない物: 物理サイズとチャネル名が XML に無い", no_phys and no_names)
    return {"refusals": refusals, "size_c": size_c, "zero_filled": bool(zero_filled),
            "own_c1_max": int(own_c1.max()), "no_physical_size": no_phys, "no_channel_names": no_names}


# --------------------------------------------------------------------------- #
# E57
# --------------------------------------------------------------------------- #
def _read_pts(path: Path) -> np.ndarray:
    with path.open("r", encoding="ascii") as fh:
        n = int(fh.readline().strip())
        pts = np.loadtxt(fh, dtype=np.float64)
    if pts.shape != (n, 3):
        raise ValueError("PTS の点数 %d と中身 %s が合わない" % (n, pts.shape))
    return pts


def _e57_bunny(g: Gates, files: dict) -> dict:
    truth = _read_pts(files["bunnyData.pts"])
    tree = cKDTree(truth)
    rows, dims = [], []
    for kind in realdata.E57_BUNNY_KINDS:
        table = fs.e57_read(files["bunny%s.e57" % kind].read_bytes())
        pts = table["points"]
        dist, idx = tree.query(pts)
        bijective = len(np.unique(idx)) == len(truth) == len(pts)
        tol = 2.0 ** -24 * float(np.abs(truth).max()) * 2.0 if kind == "Float" else 1e-9
        g.check("E57", "bunny%s: 点数 = PTS の %d" % (kind, len(truth)), len(pts) == len(truth), "%d" % len(pts))
        g.check("E57", "bunny%s: PTS と 1 対 1 で一致(≤ %.1e m)" % (kind, tol),
                bijective and float(dist.max()) <= tol, "最大 %.2e m" % float(dist.max()))
        box = fs.obb(pts)
        dims.append(np.sort(2.0 * np.asarray(box["extents"]))[::-1])
        rows.append((kind, len(pts), float(dist.max())))
    spread = float(np.ptp(np.asarray(dims), axis=0).max())
    g.check("E57", "6 つの数値型で外形寸法が同じ(差 < 1 µm)", spread < 1e-6, "%.2e m" % spread)
    down = fs.voxel_downsample(truth, voxel=0.005)
    return {"mode": "libE57 bunny", "rows": rows, "dims_m": dims[0].tolist(), "points": truth,
            "n_down": int(len(down)), "source": SOURCE_E57}


def _e57_itokawa(g: Gates) -> dict:
    pye57 = _require("pye57")
    data = np.load(ROOT / "data" / "itokawa_shape" / "gaskell_q64.npz")
    truth = data["vertices_cm"].astype(np.float64) / 100.0          # m
    work = Path(tempfile.mkdtemp(prefix="fileio_e57_"))
    try:
        path = work / "itokawa.e57"
        writer = pye57.E57(str(path), mode="w")
        writer.write_scan_raw({"cartesianX": truth[:, 0], "cartesianY": truth[:, 1], "cartesianZ": truth[:, 2]})
        writer.close()
        raw = path.read_bytes()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    table = fs.e57_read(raw)
    pts = table["points"]
    stored = truth.astype(np.float32).astype(np.float64)
    g.check("E57", "点数 = PDS ラベルの頂点数 %d" % ITOKAWA_VERTICES,
            len(pts) == len(truth) == ITOKAWA_VERTICES, "%d" % len(pts))
    g.check("E57", "全点が pye57 の格納値(float32)と完全一致", np.array_equal(pts, stored),
            "元の値との最大差 %.2e m" % float(np.abs(pts - truth).max()))
    box = fs.obb(pts)
    dims = np.sort(2.0 * np.asarray(box["extents"]))[::-1]
    rel = np.abs(dims / np.asarray(ITOKAWA_DIMENSIONS_M) - 1.0)
    print("  外形(PCA の箱)%.0f × %.0f × %.0f m、Fujiwara ほか 2006 の 535 × 294 × 209 m より %s %% 大きい"
          "(既知の食い違い・理由未確認なので門にしない)"
          % (dims[0], dims[1], dims[2], " / ".join("%.0f" % (100 * r) for r in rel)))
    g.check("E57", "外形寸法が有限で長い順に並ぶ", np.isfinite(dims).all() and dims[0] >= dims[1] >= dims[2] > 0)
    down = fs.voxel_downsample(pts, voxel=10.0)
    return {"mode": "itokawa substitute", "rows": [("pye57 float32", len(pts), float(np.abs(pts - truth).max()))],
            "dims_m": dims.tolist(), "dims_rel": rel.tolist(), "points": pts, "n_down": int(len(down)),
            "source": SOURCE_ITOKAWA}


def chapter_e57(g: Gates) -> dict:
    _require("pye57")
    try:
        files = realdata.e57_bunny_files(required=False)
    except realdata.RealDataError as exc:
        raise SystemExit("E57 の取得物を拒否: %s" % exc) from exc
    if files is not None:
        print("\n== E57: libE57 の試験点群 bunny × 6 型(%s)" % SOURCE_E57)
        return _e57_bunny(g, files)
    print("\n== E57: 原本(libE57 bunny)が未取得 → 同梱のイトカワ形状を pye57 で書いた E57 で代える")
    print("   原本で回すには: py -3.11 tools/fetch_e57_bunny.py")
    return _e57_itokawa(g)


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def _asinh_gray(image: np.ndarray) -> np.ndarray:
    lo = float(np.percentile(image, 1.0))
    v = np.arcsinh(np.clip(image - lo, 0, None) / max(1e-6, float(np.percentile(image, 50) - lo) * 3))
    v = v / max(1e-12, float(np.percentile(v, 99.8)))
    return (np.clip(v, 0, 1) * 255).astype(np.uint8)


def render_fits_overlay(res: dict, scale: int = 2) -> np.ndarray:
    gray = _asinh_gray(res["image"])[::-1]                       # FITS は y 上向き → 北を上に
    h, w = gray.shape
    im = Image.fromarray(np.repeat(gray[:, :, None], 3, axis=2)).resize((w * scale, h * scale), Image.NEAREST)
    draw = ImageDraw.Draw(im)
    for r, c in res["stars"]:
        y = (h - 1 - r) * scale
        draw.ellipse([c * scale - 2, y - 2, c * scale + 2, y + 2], outline=(80, 160, 255))
    px, py = res["cat_px"][:, 0], res["cat_px"][:, 1]
    for k in np.nonzero(res["scored"])[0]:
        x, y = px[k] * scale, (h - 1 - py[k]) * scale
        color = (60, 220, 90) if res["matched"][k] else (255, 60, 60)
        draw.ellipse([x - 9, y - 9, x + 9, y + 9], outline=color, width=2)
    return np.asarray(im)


def _gray8(a: np.ndarray, lo=None, hi=None) -> np.ndarray:
    lo = float(np.percentile(a, 1)) if lo is None else lo
    hi = float(np.percentile(a, 99.5)) if hi is None else hi
    return (np.clip((a - lo) / max(1e-12, hi - lo), 0, 1) * 255).astype(np.uint8)


def _overlay(gray: np.ndarray, mask: np.ndarray, color) -> np.ndarray:
    from scipy import ndimage as ndi
    rgb = np.repeat(gray[:, :, None], 3, axis=2).astype(np.uint8)
    edge = mask & ~ndi.binary_erosion(mask)
    rgb[edge] = color
    return rgb


def _upscale(rgb: np.ndarray, width: int, height: int) -> np.ndarray:
    return np.asarray(Image.fromarray(rgb).resize((int(round(width)), int(round(height))), Image.NEAREST))


def render_volume_panels(vol: np.ndarray, mask: np.ndarray, color, spacing, height: int = 320) -> np.ndarray:
    """3 つの直交する中央断面に領域の輪郭を重ねて横に並べる(縦横は物理寸法の比のまま)。

    ``spacing`` は配列の軸 0, 1, 2 の画素間隔。断面は ``np.rot90`` で回すので、表示の横 =
    残った 2 軸の前、縦 = 後ろ。
    """
    g = _gray8(vol.astype(np.float64))
    c = [s // 2 for s in vol.shape]
    sp = [float(s) for s in spacing]
    panels = [(g[c[0]], mask[c[0]], (1, 2)), (g[:, c[1]], mask[:, c[1]], (0, 2)),
              (g[:, :, c[2]], mask[:, :, c[2]], (0, 1))]
    tiles = []
    for a, m, (u, v) in panels:
        rgb = _overlay(np.ascontiguousarray(np.rot90(a)), np.ascontiguousarray(np.rot90(m)), color)
        w_mm, h_mm = vol.shape[u] * sp[u], vol.shape[v] * sp[v]
        tiles.append(_upscale(rgb, height * w_mm / h_mm, height))
    gap = np.full((height, 8, 3), 255, np.uint8)
    return np.hstack([tiles[0], gap, tiles[1], gap, tiles[2]])


def render_points(points: np.ndarray, size: int = 520) -> np.ndarray:
    """点群を主軸の第 1・第 2 軸の面へ投影した密度像。"""
    c = points - points.mean(0)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    uv = c @ vt[:2].T
    lo, hi = uv.min(0), uv.max(0)
    span = float((hi - lo).max())
    ij = ((uv - lo) / span * (size - 1)).astype(int)
    img = np.zeros((size, size))
    np.add.at(img, (size - 1 - ij[:, 1], ij[:, 0]), 1.0)
    v = np.log1p(img)
    return (255 - np.clip(v / max(1e-12, v.max()), 0, 1) * 255).astype(np.uint8)


def write_figures(fits_res, nifti_res, mrc_res, ome_res, e57_res, g: Gates) -> None:
    if not figs.enabled():
        return
    figs.save("stars_matched", render_fits_overlay(fits_res),
              caption="SDSS r の NGC 2420(北が上)。青=star_detect の検出、緑=SDSS の星表の星(%g〜%g 等、"
                      "飽和なし)で %.1f″ 以内に対応、赤=対応なし。星団の中心は SDSS の自動測光が混み合いで星表に載せて"
                      "いないので採点の外(検出の青だけが並ぶ)。" % (MAG_LO, MAG_HI, MATCH_ARCSEC),
              source=SOURCE_FITS)
    x, y = fits_res["x_mag"], fits_res["y_mag"]
    line = np.array([MAG_LO, MAG_HI])
    figs.save_plot("magnitudes", [("開口測光(読んだ画素から)", list(x), list(y)),
                                  ("y = x", list(line), list(line))],
                   kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"],
                   xlabel="SDSS DR16 psfMag_r [等]", ylabel="22.5 − 2.5 log10(F) [等]",
                   title="読んだ画素で SDSS の等級を再現(傾き %.3f、零点のずれ %+.3f 等)"
                         % (fits_res["slope"], fits_res["offset_mag"]),
                   caption="nanomaggy の画素を開口(半径 4 画素)で足し、零点 22.5 で等級にした。破線は y = x。",
                   source=SOURCE_FITS)
    figs.save("mri_head", render_volume_panels(nifti_res["vol"], nifti_res["mask"], (255, 80, 60), nifti_res["pixdim"]),
              caption="磁場地図の振幅像(3×3×3.75 mm)の 3 つの中央断面。赤=大津の領域の最大成分"
                      "(%.0f mL)。" % nifti_res["head_ml"], source=SOURCE_NIFTI)
    figs.save("em_density", render_volume_panels(mrc_res["vol"], mrc_res["body"], (60, 200, 255), (1.0, 1.0, 1.0), height=240),
              caption="EMD-3197(20³、11.4 Å)の 3 つの中央断面。水色=登録された推奨等値面 %.2f の輪郭。"
                      % mrc_res["level"], source=SOURCE_MRC)
    figs.save("e57_points", render_points(e57_res["points"]), gray=True,
              caption="E57 から読んだ点群を主軸の面へ投影した密度(%s)。" % e57_res["mode"], source=e57_res["source"])
    header = ["形式", "読み手", "判定", "主な数字"]
    rows = [
        ["FITS", "astro_fits_read", "読めた・一致",
         "画素完全一致、星表の再現率 %.3f、零点のずれ %+.3f 等" % (fits_res["completeness"], fits_res["offset_mag"])],
        ["NIfTI", "nifti_read", "読めた・一致",
         "ボクセル完全一致、傾き %.2f°、頭部 %.0f mL" % (nifti_res["tilt_deg"], nifti_res["head_ml"])],
        ["MRC", "em_mrc_read", "読めた・一致(起点は落ちる)",
         "統計量の相対差 %.0e、等値面の中身 %.0f nm³" % (mrc_res["stat_rel"], mrc_res["total_nm3"])],
        ["OME-TIFF", "ome_tiff_read", "拒否(正しい)",
         "2 ファイル組の片方、参照実装は C1 をゼロで埋める"],
        ["E57", "e57_read", "読めた・一致",
         "%s、外形 %.3g × %.3g × %.3g" % (e57_res["mode"], *e57_res["dims_m"])],
    ]
    figs.save_table("verdicts", header, rows, title="実物のファイル 5 形式の判定(門 %d 本、外れ %d 本)"
                    % (len(g.rows), len(g.failed())),
                    caption="参照実装(astropy / nibabel / mrcfile / tifffile)と配布元の公表値で採点した。")


def main() -> None:
    t0 = time.perf_counter()
    g = Gates()
    fits_res = chapter_fits(g)
    nifti_res = chapter_nifti(g)
    mrc_res = chapter_mrc(g)
    ome_res = chapter_ome(g)
    e57_res = chapter_e57(g)
    record = {
        "fits": {k: fits_res[k] for k in ("n_detected", "n_scored", "n_matched", "completeness",
                                          "sep_median_arcsec", "slope", "offset_mag", "robust_mag",
                                          "wcs_err_arcsec", "n_catalog_saturated_inside")},
        "nifti": {k: nifti_res[k] for k in ("shape", "pixdim", "tilt_deg", "otsu_agree", "head_ml",
                                            "fov_ml", "n_components")},
        "mrc": {k: mrc_res[k] for k in ("level", "n_components", "volumes_nm3", "total_nm3", "stat_rel", "start")},
        "ome_tiff": {k: ome_res[k] for k in ("size_c", "zero_filled", "own_c1_max",
                                             "no_physical_size", "no_channel_names")},
        "e57": {"mode": e57_res["mode"], "dims_m": e57_res["dims_m"], "n_down": e57_res["n_down"],
                "rows": e57_res["rows"]},
        "gates": len(g.rows), "failed": len(g.failed()),
    }
    print("\nRECORDED_JSON=" + json.dumps(record, ensure_ascii=False, sort_keys=True))
    write_figures(fits_res, nifti_res, mrc_res, ome_res, e57_res, g)
    errors = figs.errors()
    if errors:
        raise SystemExit("図の書き出しで失敗: " + "; ".join(errors))
    bad = g.failed()
    if bad:
        raise FormatGateError("門が %d 本外れた: %s" % (len(bad), "; ".join("%s %s" % r[:2] for r in bad)))
    print("門 %d 本すべて通過(%.1f s)\nPASS" % (len(g.rows), time.perf_counter() - t0))


if __name__ == "__main__":
    main()
