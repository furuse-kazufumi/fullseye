from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
import mrcfile
import nrrd
import nibabel as nib
from astropy.io import fits

import fileio


def test_fits_roundtrip_metadata_and_independent_astropy_reader(tmp_path):
    image = (np.arange(2 * 3 * 5, dtype=np.float32).reshape(2, 3, 5) - 7.5) / 4
    wcs = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CUNIT1": "deg",
           "CUNIT2": "deg", "CRPIX1": 3.0, "CRPIX2": 2.0,
           "CRVAL1": 12.5, "CRVAL2": -4.25, "CDELT1": -0.01, "CDELT2": 0.01}
    before = set(tmp_path.iterdir())
    payload = fileio.astro_fits_write(image, header=wcs)
    assert isinstance(payload, bytes) and len(payload) % 2880 == 0
    assert set(tmp_path.iterdir()) == before

    back, meta = fileio.astro_fits_read(payload)
    np.testing.assert_array_equal(back, image)
    assert meta == {"format": "FITS", "bitpix": -32, "bzero": 0, "bscale": 1,
                    "wcs": wcs}

    with fits.open(io.BytesIO(payload), memmap=False) as hdus:
        assert len(hdus) == 1
        np.testing.assert_array_equal(hdus[0].data, image)
        for key, value in wcs.items():
            assert hdus[0].header[key] == value


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.uint32, np.int16,
                                     np.int32, np.int64, np.float32, np.float64])
def test_fits_supported_dtypes_roundtrip(dtype):
    values = np.arange(24).reshape(4, 6).astype(dtype)
    back, _meta = fileio.astro_fits_read(fileio.astro_fits_write(values, header={}))
    np.testing.assert_array_equal(back, values)
    assert back.dtype == values.dtype


def test_fits_corrupt_and_unsupported_inputs_are_rejected_by_name():
    payload = fileio.astro_fits_write(np.arange(12, dtype=np.int16).reshape(3, 4), header={})
    with pytest.raises(ValueError, match="whole 2880-byte block"):
        fileio.astro_fits_read(payload[:-1])
    with pytest.raises(ValueError, match="unsupported BITPIX 12"):
        fileio.astro_fits_read(payload.replace(b"BITPIX  =                   16",
                                                b"BITPIX  =                   12", 1))
    with pytest.raises(ValueError, match="NAXIS3"):
        fileio.astro_fits_read(payload.replace(b"NAXIS   =                    2",
                                                b"NAXIS   =                    3", 1))
    with pytest.raises(ValueError, match="unsupported header key"):
        fileio.astro_fits_write(np.ones((2, 2)), header={"SIMPLE": True})


def test_fits_public_astropy_worked_example_arange():
    """Read Astropy's published BSD-3 test image, not a file made by this writer."""
    path = Path(fits.__file__).parent / "tests" / "data" / "arange.fits"
    assert path.is_file(), "astropy export-verify installation must include FITS worked examples"
    payload = path.read_bytes()
    actual, meta = fileio.astro_fits_read(payload)
    with fits.open(path, memmap=False) as hdus:
        np.testing.assert_array_equal(actual, hdus[0].data)
    assert actual.shape == (7, 10, 11) and meta["bitpix"] == 32


@pytest.mark.parametrize("dtype,mode", [(np.int8, 0), (np.int16, 1),
                                         (np.float32, 2), (np.uint16, 6)])
def test_mrc_roundtrip_metadata_and_independent_mrcfile_reader(tmp_path, dtype, mode):
    volume = (np.arange(3 * 4 * 5).reshape(3, 4, 5) - (10 if dtype != np.uint16 else 0)).astype(dtype)
    meta = {"voxel_size": [1.25, 2.5, 3.75], "voxel_unit": "angstrom",
            "origin": [-4.0, 5.5, 6.25], "origin_unit": "angstrom"}
    before = set(tmp_path.iterdir())
    payload = fileio.em_mrc_write(volume, meta=meta)
    assert isinstance(payload, bytes) and set(tmp_path.iterdir()) == before
    back, actual_meta = fileio.em_mrc_read(payload)
    np.testing.assert_array_equal(back, volume)
    assert actual_meta["mode"] == mode
    np.testing.assert_allclose(actual_meta["voxel_size"], meta["voxel_size"], rtol=0, atol=1e-7)
    np.testing.assert_allclose(actual_meta["origin"], meta["origin"], rtol=0, atol=0)
    assert actual_meta["voxel_unit"] == actual_meta["origin_unit"] == "angstrom"

    path = tmp_path / "independent.mrc"
    path.write_bytes(payload)
    with mrcfile.open(path, permissive=False) as mrc:
        np.testing.assert_array_equal(mrc.data, volume)
        np.testing.assert_allclose([mrc.voxel_size.x, mrc.voxel_size.y, mrc.voxel_size.z],
                                   meta["voxel_size"], rtol=0, atol=1e-7)
        np.testing.assert_allclose([mrc.header.origin.x, mrc.header.origin.y, mrc.header.origin.z],
                                   meta["origin"], rtol=0, atol=0)


def test_mrc_corrupt_headers_and_payload_are_rejected_by_name():
    meta = {"voxel_size": [1, 1, 1], "voxel_unit": "angstrom",
            "origin": [0, 0, 0], "origin_unit": "angstrom"}
    payload = fileio.em_mrc_write(np.arange(24, dtype=np.float32).reshape(2, 3, 4), meta=meta)
    with pytest.raises(ValueError, match="MRC header is truncated"):
        fileio.em_mrc_read(payload[:512])
    broken_mode = bytearray(payload)
    broken_mode[12:16] = (5).to_bytes(4, "little", signed=True)
    with pytest.raises(ValueError, match="unsupported MRC mode 5"):
        fileio.em_mrc_read(broken_mode)
    broken_axes = bytearray(payload)
    broken_axes[64:76] = np.asarray([3, 2, 1], dtype="<i4").tobytes()
    with pytest.raises(ValueError, match="MAPC/MAPR/MAPS"):
        fileio.em_mrc_read(broken_axes)
    with pytest.raises(ValueError, match="truncated"):
        fileio.em_mrc_read(payload[:-4])
    with pytest.raises(ValueError, match="voxel_unit must be 'angstrom'"):
        fileio.em_mrc_write(np.zeros((2, 2), np.int8), meta={**meta, "voxel_unit": "mm"})


def test_mrc_public_mrcfile_readme_worked_example(tmp_path):
    """Read the public BSD-3 mrcfile README's 5x5 mode-0 worked example."""
    expected = np.zeros((5, 5), dtype=np.int8)
    expected[1:4, 1:4] = 10
    path = tmp_path / "mrcfile-readme.mrc"
    with mrcfile.new(path) as mrc:
        mrc.set_data(expected)
        mrc.voxel_size = (1.0, 1.0, 1.0)
    actual, meta = fileio.em_mrc_read(path.read_bytes())
    np.testing.assert_array_equal(actual, expected)
    assert meta["mode"] == 0 and meta["voxel_unit"] == "angstrom"


@pytest.mark.parametrize("encoding", ["raw", "gzip"])
def test_nrrd_roundtrip_geometry_and_independent_pynrrd_reader(tmp_path, encoding):
    array = np.arange(4 * 3 * 2 * 5, dtype=np.int16).reshape(4, 3, 2, 5)
    directions = [np.array([0.5, 0.0, 0.0]), np.array([0.0, 0.75, 0.0]),
                  np.array([0.0, 0.0, 1.25]), None]
    meta = {"space_directions": directions, "space_unit": "mm",
            "space_origin": [-2.0, 3.0, 4.5], "kinds": ["domain", "domain", "domain", "time"]}
    before = set(tmp_path.iterdir())
    payload = fileio.nrrd_write(array, meta=meta, encoding=encoding)
    assert isinstance(payload, bytes) and set(tmp_path.iterdir()) == before
    back, actual_meta = fileio.nrrd_read(payload)
    np.testing.assert_array_equal(back, array)
    assert actual_meta["encoding"] == encoding
    assert actual_meta["voxel_spacing"] == [0.5, 0.75, 1.25, None]
    assert actual_meta["space_unit"] == "mm"
    np.testing.assert_array_equal(actual_meta["space_origin"], meta["space_origin"])
    for actual, expected in zip(actual_meta["space_directions"], directions):
        if expected is None:
            assert actual is None
        else:
            np.testing.assert_array_equal(actual, expected)

    path = tmp_path / f"independent-{encoding}.nrrd"
    path.write_bytes(payload)
    independent, header = nrrd.read(path, index_order="F")
    np.testing.assert_array_equal(independent, array)
    assert header["encoding"] in (encoding, "gz")
    np.testing.assert_array_equal(header["space origin"], meta["space_origin"])


def test_nrrd_corrupt_input_is_rejected_by_name():
    array = np.arange(24, dtype=np.float32).reshape(2, 3, 4)
    meta = {"space_directions": np.diag([0.5, 0.75, 1.0]), "space_unit": "um",
            "space_origin": [0, 0, 0]}
    raw = fileio.nrrd_write(array, meta=meta, encoding="raw")
    with pytest.raises(ValueError, match="declare 96 data bytes, got 92"):
        fileio.nrrd_read(raw[:-4])
    with pytest.raises(ValueError, match="unsupported encoding 'bzip2'"):
        fileio.nrrd_read(raw.replace(b"encoding: raw", b"encoding: bzip2"))
    with pytest.raises(ValueError, match="space directions must have 3 axis entries"):
        fileio.nrrd_read(raw.replace(b"space directions: (0.5,0,0) (0,0.75,0) (0,0,1)",
                                     b"space directions: (0.5,0,0) (0,0.75,0)        "))
    with pytest.raises(ValueError, match="space_unit must be one of"):
        fileio.nrrd_write(array, meta={**meta, "space_unit": "seconds"}, encoding="raw")


def test_nrrd_public_pynrrd_readme_worked_example(tmp_path):
    """Read pynrrd's published MIT-licensed zeros((5,4,3,2)) worked example."""
    expected = np.zeros((5, 4, 3, 2), dtype=np.float64)
    path = tmp_path / "pynrrd-readme.nrrd"
    nrrd.write(str(path), expected, index_order="F")
    actual, meta = fileio.nrrd_read(path.read_bytes())
    np.testing.assert_array_equal(actual, expected)
    assert meta["space_directions"] is None and meta["space_unit"] is None


@pytest.mark.parametrize("compressed", [False, True])
def test_nifti_roundtrip_affine_and_independent_nibabel_reader(tmp_path, compressed):
    volume = (np.arange(4 * 5 * 6).reshape(4, 5, 6) - 20).astype(np.int16)
    affine = np.array([[-2.0, 0.0, 0.0, 32.0], [0.0, 2.5, 0.0, -40.0],
                       [0.0, 0.0, 3.0, -16.0], [0.0, 0.0, 0.0, 1.0]])
    meta = {"affine": affine, "spatial_unit": "mm"}
    before = set(tmp_path.iterdir())
    payload = fileio.nifti_write(volume, meta=meta, compressed=compressed)
    assert isinstance(payload, bytes) and set(tmp_path.iterdir()) == before
    back, actual_meta = fileio.nifti_read(payload)
    np.testing.assert_array_equal(back, volume)
    np.testing.assert_allclose(actual_meta["affine"], affine, rtol=0, atol=0)
    np.testing.assert_allclose(actual_meta["qform_affine"], affine, rtol=0, atol=1e-6)
    np.testing.assert_allclose(actual_meta["sform_affine"], affine, rtol=0, atol=0)
    np.testing.assert_array_equal(actual_meta["pixdim"], [2.0, 2.5, 3.0])
    assert actual_meta["spatial_unit"] == "mm" and actual_meta["compressed"] is compressed

    path = tmp_path / ("independent.nii.gz" if compressed else "independent.nii")
    path.write_bytes(payload)
    independent = nib.load(path)
    np.testing.assert_array_equal(np.asanyarray(independent.dataobj), volume)
    np.testing.assert_allclose(independent.affine, affine, rtol=0, atol=0)
    assert independent.header.get_xyzt_units() == ("mm", "unknown")


def test_nifti_4d_time_pixdim_roundtrip():
    data = np.arange(2 * 3 * 4 * 5, dtype=np.float32).reshape(2, 3, 4, 5)
    affine = np.diag([0.8, 0.9, 1.5, 1.0])
    payload = fileio.nifti_write(data, meta={"affine": affine, "spatial_unit": "mm",
                                             "time_step": 2.5, "time_unit": "s"}, compressed=True)
    actual, meta = fileio.nifti_read(payload)
    np.testing.assert_array_equal(actual, data)
    np.testing.assert_allclose(meta["pixdim"], [0.8, 0.9, 1.5, 2.5], rtol=0, atol=1e-7)
    assert meta["time_unit"] == "s"


def test_nifti_corrupt_input_is_rejected_by_name():
    data = np.arange(24, dtype=np.int16).reshape(2, 3, 4)
    meta = {"affine": np.eye(4), "spatial_unit": "mm"}
    payload = fileio.nifti_write(data, meta=meta, compressed=False)
    with pytest.raises(ValueError, match="header is truncated"):
        fileio.nifti_read(payload[:200])
    broken_datatype = bytearray(payload)
    broken_datatype[70:72] = (32).to_bytes(2, "little", signed=True)
    with pytest.raises(ValueError, match="unsupported NIfTI datatype code 32"):
        fileio.nifti_read(broken_datatype)
    with pytest.raises(ValueError, match="declare .* total bytes"):
        fileio.nifti_read(payload[:-2])
    shear = np.eye(4); shear[0, 1] = 0.25
    with pytest.raises(ValueError, match="affine contains shear"):
        fileio.nifti_write(data, meta={"affine": shear, "spatial_unit": "mm"}, compressed=False)


def test_nifti_public_nibabel_anatomical_worked_example():
    """Read NiBabel's published MIT/BSD anatomical.nii worked file."""
    path = Path(nib.__file__).parent / "tests" / "data" / "anatomical.nii"
    assert path.is_file(), "nibabel export-verify installation must include NIfTI worked examples"
    actual, meta = fileio.nifti_read(path.read_bytes())
    independent = nib.load(path)
    np.testing.assert_array_equal(actual, np.asanyarray(independent.dataobj))
    np.testing.assert_allclose(meta["affine"], independent.affine, rtol=0, atol=0)
    assert actual.shape == (33, 41, 25) and meta["spatial_unit"] == "mm"
