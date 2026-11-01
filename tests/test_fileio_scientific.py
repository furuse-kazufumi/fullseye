from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
import mrcfile
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
