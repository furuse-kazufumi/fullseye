"""In-memory scientific image and volume format round trips."""
from __future__ import annotations

import numpy as np

import fullseye as fs


def main():
    image = np.arange(24, dtype=np.float32).reshape(4, 6)
    wcs = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CUNIT1": "deg",
           "CUNIT2": "deg", "CRPIX1": 3.5, "CRPIX2": 2.5,
           "CRVAL1": 120.0, "CRVAL2": 35.0, "CDELT1": -0.01, "CDELT2": 0.01}
    fits_bytes = fs.astro_fits_write(image, header=wcs)
    fits_image, fits_meta = fs.astro_fits_read(fits_bytes)
    np.testing.assert_array_equal(fits_image, image)
    assert fits_meta["wcs"] == wcs and len(fits_bytes) % 2880 == 0

    volume = np.arange(3 * 4 * 6, dtype=np.float32).reshape(3, 4, 6)
    mrc_meta = {"voxel_size": [1.5, 1.5, 2.0], "voxel_unit": "angstrom",
                "origin": [-3.0, 0.0, 4.0], "origin_unit": "angstrom"}
    mrc_bytes = fs.em_mrc_write(volume, meta=mrc_meta)
    mrc_volume, mrc_back_meta = fs.em_mrc_read(mrc_bytes)
    np.testing.assert_array_equal(mrc_volume, volume)
    np.testing.assert_allclose(mrc_back_meta["voxel_size"], mrc_meta["voxel_size"])
    np.testing.assert_allclose(mrc_back_meta["origin"], mrc_meta["origin"])

    print("PASS: FITS WCS and MRC voxel geometry round-trip in memory")


if __name__ == "__main__":
    main()
