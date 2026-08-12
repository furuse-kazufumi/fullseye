# Multi-library coverage (imgevolve is not HALCON-only)

Installed-library inventories introspected (ground truth, not scraped);
registry references counted via the cross-library catalog.

| library | referenced by registry | in installed inventory | matched |
|---|---|---|---|
| OpenCV (cv2) | 98 | 484 public callables | 44 |
| scikit-image | 132 | 316 submodule functions | 84 |

## Registry ops by source library (10+ libraries incorporated)

| library | ops |
|---|---|
| core (numpy/scipy) | 306 |
| scikit-image | 86 |
| OpenCV | 50 |
| SimpleITK | 14 |
| Pillow | 13 |
| kornia (GPU) | 12 |
| scipy | 11 |
| mahotas | 10 |
| PyWavelets | 9 |
| scipy (3-D) | 8 |
| torch | 2 |
| **total** | **521** |

## Honest reading
- Inventories are ALL public callables (cv2 ~484, skimage ~316); most are not
  image-transform operators (IO, drawing, math, GUI, ML), so raw ratios understate reach.
- imgevolve wraps ecosystems rather than reimplementing them; adding an op with its
  catalog analogue extends this automatically. Distinctive incorporations live in
  `backends_extra.py` (xsk_/xcv_): inpainting, blob detectors, keypoint counts,
  random-walker/flood/grabCut segmentation, structure/Hessian tensors, NPR filters.
