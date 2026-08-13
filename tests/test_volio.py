"""Ground-truth tests for volumetric / medical volume import (volio.py).

A synthetic 3-D field of known shape (16, 32, 24) is written in every supported
container and read back, asserting the array shape, the recovered voxel spacing,
and value fidelity. The comparison is on the *data*, so a backend is free to store
a different on-disk dtype as long as ``read_volume`` returns the same float64 volume.

The medical formats (NIfTI / NRRD / MetaImage) round-trip through SimpleITK; a
synthetic DICOM *series* is written slice-by-slice with the tags GDCM needs to
re-stack it. Fail-closed behaviour on untrusted / malformed input is exercised
alongside the happy path.
"""
import os

import numpy as np
import pytest

import volio
from volio import VolumeMeta

sitk = pytest.importorskip("SimpleITK")
tifffile = pytest.importorskip("tifffile")

# --------------------------------------------------------------------------- #
# The reference object: a smooth (16, 32, 24) float32 field + a chosen spacing. #
# D=16 slices, H=32 rows, W=24 cols. spacing_mm is (sz, sy, sx).                #
# --------------------------------------------------------------------------- #
D, H, W = 16, 32, 24
SPACING = (2.5, 0.75, 0.5)          # (sz, sy, sx) in mm


def _ref_volume() -> np.ndarray:
    zz, yy, xx = np.mgrid[0:D, 0:H, 0:W].astype(np.float32)
    r = np.sqrt((zz - D / 2) ** 2 + (yy - H / 2) ** 2 + (xx - W / 2) ** 2)
    return (np.sin(xx / 3.0) * np.cos(yy / 4.0) + 0.1 * zz - 0.05 * r).astype(np.float32)


REF = _ref_volume()
REF64 = REF.astype(np.float64)
META = VolumeMeta(spacing_mm=SPACING)


def assert_is_ref(vol, meta, check_spacing=False, atol=1e-4):
    assert vol.dtype == np.float64 and vol.ndim == 3
    assert vol.shape == (D, H, W), "shape %r" % (vol.shape,)
    assert np.isfinite(vol).all()
    assert np.allclose(vol, REF64, atol=atol)
    assert isinstance(meta, VolumeMeta)
    if check_spacing:
        assert np.allclose(meta.spacing_mm, SPACING, atol=1e-4), meta.spacing_mm


# --------------------------------------------------------------------------- #
# A synthetic DICOM series writer (test fixture, not part of volio).           #
# --------------------------------------------------------------------------- #
def _write_dicom_series(directory, vol_zyx, spacing_xyz=(0.5, 0.75, 2.5),
                        series_uid="1.2.826.0.1.3680043.2.1125.1.98765432109876543210",
                        modality="CT", prefix="slice"):
    """Write *vol_zyx* (D,H,W) as one .dcm per slice with the tags GDCM needs to
    re-stack the series (Series UID, per-slice position + instance number).

    *prefix* keeps two series' files apart when they share a study directory."""
    os.makedirs(directory, exist_ok=True)
    img = sitk.GetImageFromArray(np.asarray(vol_zyx, np.int16))     # depth = D
    img.SetSpacing(spacing_xyz)
    writer = sitk.ImageFileWriter()
    writer.KeepOriginalImageUIDOn()
    dirc = img.GetDirection()
    orient = "\\".join(str(x) for x in (dirc[0], dirc[3], dirc[6], dirc[1], dirc[4], dirc[7]))
    for i in range(img.GetDepth()):
        sl = img[:, :, i]
        sl.SetMetaData("0008|0060", modality)                      # Modality
        sl.SetMetaData("0008|0016", "1.2.840.10008.5.1.4.1.1.2")   # SOP Class (CT)
        sl.SetMetaData("0008|0018", series_uid + "." + str(i))     # SOP Instance UID
        sl.SetMetaData("0020|000e", series_uid)                    # Series Instance UID
        sl.SetMetaData("0020|0013", str(i))                        # Instance Number
        sl.SetMetaData("0020|0037", orient)                        # Image Orientation
        pos = img.TransformIndexToPhysicalPoint((0, 0, i))
        sl.SetMetaData("0020|0032", "\\".join(str(x) for x in pos))  # Image Position
        writer.SetFileName(os.path.join(directory, "%s_%03d.dcm" % (prefix, i)))
        writer.Execute(sl)
    return series_uid


# --------------------------------------------------------------------------- #
# read/write round-trips — one test per format                                #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("ext", [".nii", ".nii.gz", ".nrrd", ".nhdr", ".mha", ".mhd"])
def test_sitk_roundtrip_shape_spacing_values(tmp_path, ext):
    """NIfTI / NRRD / MetaImage: write via SimpleITK, recover shape + spacing + values."""
    p = str(tmp_path / ("vol" + ext))
    volio.write_volume(p, REF, META)
    vol, meta = volio.read_volume(p)
    assert_is_ref(vol, meta, check_spacing=True)
    assert meta.direction.shape == (3, 3) and meta.origin.shape == (3,)


def test_analyze_hdr_img_pair(tmp_path):
    """Analyze 7.5 writes an .hdr + .img pair; reading either recovers the volume."""
    p = str(tmp_path / "vol.hdr")
    volio.write_volume(p, REF, META)
    assert os.path.isfile(str(tmp_path / "vol.img"))
    for target in ("vol.hdr", "vol.img"):
        vol, meta = volio.read_volume(str(tmp_path / target))
        assert vol.shape == (D, H, W)
        assert np.allclose(vol, REF64, atol=1e-4)


def test_dicom_series_from_directory(tmp_path):
    d = str(tmp_path / "series")
    uid = _write_dicom_series(d, REF - REF.min())              # non-negative int16
    vol, meta = volio.read_volume(d)
    assert vol.shape == (D, H, W)                              # D slices re-stacked
    assert vol.dtype == np.float64
    assert meta.modality == "CT"
    assert meta.n_series == 1
    assert meta.dtype in ("int16", "int32")                   # original on-disk dtype
    # spacing (sx,sy,sz)=(0.5,0.75,2.5) -> meta (sz,sy,sx)=(2.5,0.75,0.5)
    assert np.allclose(meta.spacing_mm, (2.5, 0.75, 0.5), atol=1e-4)
    assert uid in volio.list_dicom_series(d)


def test_dicom_single_file_reads_whole_series(tmp_path):
    """Pointing read_volume at one .dcm slice returns the entire stacked volume."""
    d = str(tmp_path / "series")
    _write_dicom_series(d, REF - REF.min())
    one = os.path.join(d, sorted(os.listdir(d))[D // 2])
    vol, meta = volio.read_volume(one)
    assert vol.shape[0] == D
    assert meta.modality == "CT"


def test_dicom_multiple_series_requires_series_id(tmp_path):
    d = str(tmp_path / "study")
    uid_a = _write_dicom_series(d, REF - REF.min(), prefix="a",
                                series_uid="1.2.826.0.1.3680043.2.1125.1.111", modality="CT")
    uid_b = _write_dicom_series(d, (REF - REF.min())[:8], prefix="b",
                                series_uid="1.2.826.0.1.3680043.2.1125.1.222", modality="MR")
    ids = volio.list_dicom_series(d)
    assert uid_a in ids and uid_b in ids
    with pytest.raises(ValueError, match="series"):
        volio.read_volume(d)                                   # ambiguous -> must raise
    vol_a, meta_a = volio.read_volume(d, series_id=uid_a)
    assert vol_a.shape[0] == D
    vol_b, meta_b = volio.read_volume(d, series_id=uid_b)
    assert vol_b.shape[0] == 8                                 # the shorter series
    with pytest.raises(ValueError, match="not found"):
        volio.read_volume(d, series_id="1.2.826.0.1.3680043.2.1125.1.999")


def test_multipage_tiff_roundtrip(tmp_path):
    p = str(tmp_path / "vol.tif")
    tifffile.imwrite(p, REF)                                   # (D,H,W) multipage
    vol, meta = volio.read_volume(p)
    assert vol.shape == (D, H, W)
    assert np.allclose(vol, REF64)
    assert meta.source_format == "tiff"
    # write via volio, too
    q = str(tmp_path / "out.tiff")
    volio.write_volume(q, REF)
    vol2, _ = volio.read_volume(q)
    assert np.allclose(vol2, REF64)


def test_raw_roundtrip_exact(tmp_path):
    p = str(tmp_path / "vol.raw")
    REF.tofile(p)
    vol, meta = volio.read_volume(p, shape=(D, H, W), dtype=np.float32)
    assert np.array_equal(vol, REF64)                          # exact, not just close
    assert meta.dtype == "float32"
    # .vol shares the raw path; a uint16 cube round-trips exactly too
    u = (np.arange(D * H * W, dtype=np.uint16)).reshape(D, H, W)
    pv = str(tmp_path / "vol.vol")
    u.tofile(pv)
    volu, mu = volio.read_volume(pv, shape=(D, H, W), dtype=np.uint16)
    assert np.array_equal(volu, u.astype(np.float64)) and mu.dtype == "uint16"


def test_npy_and_npz_roundtrip_exact(tmp_path):
    p = str(tmp_path / "vol.npy")
    np.save(p, REF)
    vol, meta = volio.read_volume(p)
    assert np.array_equal(vol, REF64) and meta.source_format == "npy"

    z = str(tmp_path / "sole.npz")
    np.savez(z, REF)                                           # single unnamed array
    volz, _ = volio.read_volume(z)
    assert np.array_equal(volz, REF64)

    zk = str(tmp_path / "multi.npz")
    np.savez(zk, ct=REF, mask=(REF > 0).astype(np.uint8))
    with pytest.raises(ValueError, match="key="):
        volio.read_volume(zk)                                  # ambiguous
    volk, _ = volio.read_volume(zk, key="ct")
    assert np.array_equal(volk, REF64)


def test_write_volume_npy_npz(tmp_path):
    p = str(tmp_path / "w.npy")
    volio.write_volume(p, REF)
    assert np.array_equal(volio.read_volume(p)[0], REF64)
    q = str(tmp_path / "w.npz")
    volio.write_volume(q, REF)                                 # key is "volume"
    assert np.array_equal(volio.read_volume(q, key="volume")[0], REF64)


# --------------------------------------------------------------------------- #
# fail-closed on untrusted / malformed input                                  #
# --------------------------------------------------------------------------- #
def test_garbage_file_raises(tmp_path):
    for name in ("junk.nii", "junk.nrrd", "junk.mha"):
        p = tmp_path / name
        p.write_bytes(np.random.default_rng(0).integers(0, 256, 800, dtype=np.uint8).tobytes())
        with pytest.raises(ValueError):
            volio.read_volume(str(p))


def test_raw_wrong_declared_size_raises(tmp_path):
    p = str(tmp_path / "v.raw")
    REF.tofile(p)                                              # 16*32*24 float32
    with pytest.raises(ValueError, match="size mismatch"):
        volio.read_volume(p, shape=(D, H, W + 1), dtype=np.float32)
    with pytest.raises(ValueError, match="size mismatch"):
        volio.read_volume(p, shape=(D, H, W), dtype=np.float64)   # right count, wrong itemsize
    with pytest.raises(ValueError):                              # missing shape/dtype
        volio.read_volume(p)


def test_oversized_shape_hits_max_volume_bytes(tmp_path):
    p = str(tmp_path / "v.raw")
    REF.tofile(p)
    with pytest.raises(ValueError, match="MAX_VOLUME_BYTES"):
        volio.read_volume(p, shape=(2000, 2000, 2000), dtype=np.float64)   # ~64 GiB
    assert volio.MAX_VOLUME_BYTES == 4 * (1 << 30)


def test_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        volio.read_volume(str(tmp_path / "nope.nii"))
    with pytest.raises(FileNotFoundError):
        volio.read_volume(str(tmp_path / "nope.npy"))


def test_two_dimensional_tiff_is_not_a_volume(tmp_path):
    p = str(tmp_path / "flat.tif")
    tifffile.imwrite(p, REF[0])                                # a single 2-D page
    with pytest.raises(ValueError, match="not a volume"):
        volio.read_volume(p)


def test_non_finite_voxel_rejected(tmp_path):
    bad = REF.copy()
    bad[0, 0, 0] = np.nan
    p = str(tmp_path / "nan.npy")
    np.save(p, bad)
    with pytest.raises(ValueError, match="non-finite"):
        volio.read_volume(p)
    with pytest.raises(ValueError, match="non-finite"):
        volio.write_volume(str(tmp_path / "nan.nii"), bad)


def test_unsupported_extension_raises(tmp_path):
    p = tmp_path / "vol.xyz"
    p.write_bytes(b"\0" * 16)
    with pytest.raises(ValueError, match="unsupported volume format"):
        volio.read_volume(str(p))
    with pytest.raises(ValueError, match="unsupported write format"):
        volio.write_volume(str(tmp_path / "vol.foo"), REF)


def test_npy_two_dimensional_rejected(tmp_path):
    p = str(tmp_path / "flat.npy")
    np.save(p, REF[0])
    with pytest.raises(ValueError, match="3-D"):
        volio.read_volume(p)


def test_write_rejects_non_3d_and_out_of_scope(tmp_path):
    with pytest.raises(ValueError, match="3-D"):
        volio.write_volume(str(tmp_path / "x.nii"), REF[0])   # 2-D
    with pytest.raises(ValueError, match="DICOM"):
        volio.write_volume(str(tmp_path / "x.dcm"), REF)
    with pytest.raises(ValueError, match="raw"):
        volio.write_volume(str(tmp_path / "x.raw"), REF)


# --------------------------------------------------------------------------- #
# values are kept raw (medical intensities not crushed to [0,1])              #
# --------------------------------------------------------------------------- #
def test_values_are_kept_raw_not_normalized(tmp_path):
    """A CT-like volume in Hounsfield units survives with its range intact."""
    hu = (np.mgrid[0:D, 0:H, 0:W][2].astype(np.int16) * 40 - 1000)  # ~[-1000, +?] HU
    p = str(tmp_path / "ct.nii")
    volio.write_volume(p, hu, META)
    vol, meta = volio.read_volume(p)
    assert vol.min() < -900 and vol.max() > 0                  # not squashed into [0,1]
    assert np.allclose(vol, hu.astype(np.float64))


# --------------------------------------------------------------------------- #
# integration: a read volume flows into the existing vol_* op sort            #
# --------------------------------------------------------------------------- #
def test_volume_feeds_existing_vol_ops(tmp_path):
    """The deliverable claim: an imported volume is consumed by ops' volume sort."""
    import ops
    p = str(tmp_path / "vol.nrrd")
    volio.write_volume(p, REF - REF.min(), META)              # non-negative for thresholds
    vol, _ = volio.read_volume(p)

    sm = ops.RT["vol_gaussian"](vol, 0.5, 0.0)                # volume -> volume
    assert sm.shape == (D, H, W) and np.isfinite(sm).all()

    mip = ops.RT["vol_mip"](vol, 0.0, 0.0)                    # volume -> 2-D image
    assert mip.shape == (H, W)

    sl = ops.RT["vol_slice"](vol, 0.5, 0.0)                   # volume -> 2-D image
    assert sl.shape == (H, W)

    n = ops.RT["vol_count"](vol, 0.0, 0.0)                    # volume -> feature (scalar)
    assert np.isscalar(n) or np.ndim(n) == 0


def test_volio_exports_match_all():
    for name in volio.__all__:
        assert hasattr(volio, name), name
