# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``examples/poc_real_file_formats.py`` の門を回す(実物のファイル 5 形式を参照実装と公表値で採点)。"""
from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest

import realdata
from examples import poc_real_file_formats as poc

pytest.importorskip("astropy")
pytest.importorskip("nibabel")
pytest.importorskip("mrcfile")
pytest.importorskip("tifffile")


def test_bundled_files_match_their_pins():
    for name, (size, digest) in poc.BUNDLED.items():
        raw = poc.load_bundled(name)
        assert len(raw) == size and hashlib.sha256(raw).hexdigest() == digest


def test_a_tampered_bundled_file_is_refused(tmp_path, monkeypatch):
    src = poc.DATA / "emd_3197.map.gz"
    bad = tmp_path / "emd_3197.map.gz"
    data = bytearray(src.read_bytes())
    data[100] ^= 0xFF
    bad.write_bytes(bytes(data))
    monkeypatch.setattr(poc, "DATA", tmp_path)
    with pytest.raises(realdata.RealDataError, match="SHA-256"):
        poc.load_bundled("emd_3197.map.gz")


def test_independent_tan_projection_matches_the_reference_point():
    wcs = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRPIX1": 200.5, "CRPIX2": 200.5,
           "CRVAL1": 114.6021, "CRVAL2": 21.575, "CDELT1": -0.000375, "CDELT2": 0.000375}
    ra, dec = poc.tan_pix2world(wcs, 200.5, 200.5)
    assert abs(float(ra) - 114.6021) < 1e-12 and abs(float(dec) - 21.575) < 1e-12
    with pytest.raises(ValueError, match="PC/CD"):
        poc.tan_pix2world(dict(wcs, PC1_1=1.0), 1.0, 1.0)


def test_fits_chapter_reproduces_sdss_magnitudes():
    g = poc.Gates()
    res = poc.chapter_fits(g)
    assert not g.failed(), g.failed()
    assert res["completeness"] >= 0.90
    assert abs(res["slope"] - 1.0) < 0.05 and abs(res["offset_mag"]) < 0.05
    assert res["n_matched"] >= 100            # 中身を数える(空の一致を通さない)


def test_nifti_and_mrc_chapters_match_reference_and_published_values():
    g = poc.Gates()
    nifti = poc.chapter_nifti(g)
    mrc = poc.chapter_mrc(g)
    assert not g.failed(), g.failed()
    assert abs(nifti["tilt_deg"] - 26.4) < 0.05
    assert 1000 < nifti["head_ml"] < 3000
    assert mrc["stat_rel"] < 1e-6 and mrc["start"] == (-2, 0, 0)
    assert mrc["n_components"] >= 1 and math.isfinite(mrc["total_nm3"]) and mrc["total_nm3"] > 0


def test_ome_chapter_refuses_half_of_a_multi_file_set_and_the_reason_is_true():
    g = poc.Gates()
    res = poc.chapter_ome(g)
    assert not g.failed(), g.failed()
    assert all(msg and "found 1" in msg for msg in res["refusals"].values())
    assert res["zero_filled"] and res["own_c1_max"] > 0


def test_e57_substitute_reads_every_itokawa_vertex():
    pytest.importorskip("pye57")
    g = poc.Gates()
    res = poc._e57_itokawa(g)
    assert not g.failed(), g.failed()
    assert len(res["points"]) == poc.ITOKAWA_VERTICES and np.isfinite(res["points"]).all()
    assert res["rows"][0][2] < 2e-5          # float32 で格納した丸めだけ(300 m で 1 ulp 程度)


def test_nifti_qform_follows_nifti1_io_for_near_180_degree_quaternions():
    """★回帰: 1 - |bcd|^2 = 1.2e-8 の実物で、qform の 1 列目(DICOM の行方向 = x 軸そのもの)に
    回転の屑が出ないこと(2026-11-04 までは -1.5e-4 / -6.4e-4 が出て nibabel と 8e-4 ずれた)。"""
    import gzip

    import fullseye as fs
    nib = pytest.importorskip("nibabel")
    raw = poc.load_bundled("ds000117_sub-01_ses-mri_acq-func_magnitude1.nii.gz")
    _, meta = fs.nifti_read(raw)
    ref = nib.Nifti1Image.from_bytes(gzip.decompress(raw)).get_qform()
    np.testing.assert_allclose(meta["qform_affine"], ref, rtol=0, atol=1e-5)
    assert meta["qform_affine"][1, 0] == 0.0 and meta["qform_affine"][2, 0] == 0.0


def test_partial_e57_cache_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_E57_BUNNY_DATA", str(tmp_path))
    assert realdata.e57_bunny_files(required=False) is None
    (tmp_path / "bunnyFloat.e57").write_bytes(b"not an e57")
    with pytest.raises(realdata.RealDataError, match="欠けて"):
        realdata.e57_bunny_files(required=False)
