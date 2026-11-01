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

    print("PASS: FITS image values and WCS round-trip in memory")


if __name__ == "__main__":
    main()
