from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
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
