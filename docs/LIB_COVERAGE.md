# Multi-library coverage (imgevolve is not HALCON-only)

Installed-library inventories introspected (ground truth, not scraped);
registry references counted via the cross-library catalog.

| library | referenced by registry | in installed inventory | matched |
|---|---|---|---|
| OpenCV (cv2) | 90 | 484 public callables | 44 |
| scikit-image | 118 | 316 submodule functions | 76 |

## Honest reading
- Inventories are ALL public callables (cv2 ~484, skimage ~316); most are not
  image-transform operators (IO, drawing, math, GUI, ML), so raw ratios understate reach.
- imgevolve wraps ecosystems rather than reimplementing them; adding an op with its
  catalog analogue extends this automatically. Distinctive incorporations live in
  `backends_extra.py` (xsk_/xcv_): inpainting, blob detectors, keypoint counts,
  random-walker/flood/grabCut segmentation, structure/Hessian tensors, NPR filters.
