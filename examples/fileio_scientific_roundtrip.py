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

    nrrd_meta = {"space_directions": np.diag([0.5, 0.75, 1.25]),
                 "space_unit": "mm", "space_origin": [1.0, 2.0, 3.0]}
    nrrd_bytes = fs.nrrd_write(volume, meta=nrrd_meta, encoding="gzip")
    nrrd_volume, nrrd_back_meta = fs.nrrd_read(nrrd_bytes)
    np.testing.assert_array_equal(nrrd_volume, volume)
    assert nrrd_back_meta["voxel_spacing"] == [0.5, 0.75, 1.25]
    assert nrrd_back_meta["space_unit"] == "mm"

    affine = np.array([[-0.5, 0.0, 0.0, 10.0], [0.0, 0.75, 0.0, -20.0],
                       [0.0, 0.0, 1.25, 30.0], [0.0, 0.0, 0.0, 1.0]])
    nifti_bytes = fs.nifti_write(volume, meta={"affine": affine, "spatial_unit": "mm"},
                                 compressed=True)
    nifti_volume, nifti_meta = fs.nifti_read(nifti_bytes)
    np.testing.assert_array_equal(nifti_volume, volume)
    np.testing.assert_allclose(nifti_meta["affine"], affine)
    assert nifti_meta["spatial_unit"] == "mm" and nifti_meta["compressed"]

    ome_meta = {"axes": "ZYX", "physical_size_x": 0.5, "physical_size_x_unit": "um",
                "physical_size_y": 0.75, "physical_size_y_unit": "um",
                "physical_size_z": 1.25, "physical_size_z_unit": "um"}
    ome_bytes = fs.ome_tiff_write(volume, meta=ome_meta)
    ome_volume, ome_back_meta = fs.ome_tiff_read(ome_bytes)
    np.testing.assert_array_equal(ome_volume, volume)
    assert ome_back_meta["axes"] == "ZYX" and ome_back_meta["physical_size_x_unit"] == "µm"

    print("PASS: FITS, MRC, NRRD, NIfTI, and OME-TIFF arrays and geometry round-trip in memory")


if __name__ == "__main__":
    main()
