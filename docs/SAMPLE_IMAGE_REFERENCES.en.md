<!-- i18n-source-sha: b2e247e3558a -->
# Sample images — provenance, source papers & public repositories

[日本語](./SAMPLE_IMAGE_REFERENCES.md) · **English**

> User note (2026-08-16): "There must be plenty of source papers and GitHub repos behind these."
> Following Fullseye's public-disclosure policy ([[project_imgevolve_goal_knowledge_layer_2026_08_13]]),
> we record the **provenance, license, source paper, and public repository** of the collected
> sample images in an auditable form.
> **We do not download any images from external sources without permission** (synthetic = our own work;
> everything else = only the classic images bundled with scikit-image).
> **The MVTec/HALCON sample images are proprietary, so we do not collect them.**

Collection = `studio_assets/sample_images/` (machine-readable provenance is in `manifest.json` in the same dir).
Regenerate = `py -3.11 tools/gen_sample_images.py`, access = `sample_images.py`.

## Collected sample images

### Synthetic (own work · Fullseye-generated · license-free)
`gradient` / `blobs` / `shapes` / `checker_noisy` — generated deterministically by `tools/gen_sample_images.py`.
Contains no third-party rights whatsoever.

### scikit-image `skimage.data` (BSD-3-Clause project · each image as below)
Canonical source = <https://github.com/scikit-image/scikit-image> (`skimage/data/`; the license of each image is in
`skimage/data/README.txt` / `LICENSE.txt`) / API = <https://scikit-image.org/docs/stable/api/skimage.data.html>

| name | content | license / provenance |
|---|---|---|
| `coins` | Photo of Greek coins (a staple for blob/segmentation) | Bundled with scikit-image · effectively public domain (`skimage/data/README.txt`) |
| `camera` | "cameraman" (classic test image) | **CC0** (photographer Lav Varshney). The CC0 version substituted in v0.18 out of copyright consideration |
| `page` | A scanned document page (binarization / OCR preprocessing) | Bundled with scikit-image · effectively public domain |
| `cell` | Quantitative phase imaging (derived from a digital hologram) | **CC0** (public domain). Credit = Paul Müller, Mirjam Schürmann, Salvatore Girardo, Gheorghe Cojoc, Jochen Guck. Source paper = accurate assessment of the size/refractive index of spherical objects (quantitative phase imaging). Acquisition library = `qpformat` |

> honest: The original photographers of `coins`/`page` are bundled by skimage as "public domain / no known copyright."
> The strict tracing of the original source treats `skimage/data/README.txt` as canonical (it may be updated across versions).

## Public datasets/repositories with many more sample images (reference only · not imported)

There are many classic image-processing benchmark images in the following. **If you import any, verify each license
individually** (many are restricted to research/academic use). Fullseye does not currently bundle these (kept as reference only).

| dataset / repo | content | source paper / URL · license |
|---|---|---|
| **scikit-image data** | The classic set above + astronaut/coffee/chelsea, etc. | github.com/scikit-image/scikit-image (BSD-3; each image CC0/PD) |
| **OpenCV samples** | lena replacement · fruits · building, etc. | github.com/opencv/opencv `samples/data/` (Apache-2.0) |
| **USC-SIPI Image Database** | Standard test images such as Baboon (Mandrill)/Peppers/cameraman | sipi.usc.edu/database (research use). Note: Lena is discouraged out of ethical consideration |
| **BSDS500** (Berkeley Segmentation) | 500 natural images + human segmentations | Arbeláez, Maire, Fowlkes, Malik, "Contour Detection and Hierarchical Image Segmentation", IEEE TPAMI 2011 (academic) |
| **Set5 / Set14 / BSD68 / DIV2K** | Super-resolution / denoising benchmarks | The respective SR/denoising papers (DIV2K = Agustsson & Timofte, CVPRW 2017) |
| **MVTec AD** (anomaly detection) | Industrial defect images | Bergmann et al., "MVTec AD", CVPR 2019 (**research-only · non-commercial**, license check required) |

> ★ Caution: **The sample images bundled with HALCON (MVTec) are proprietary**, so they are not collected into Fullseye.
> The source papers for the ops / algorithms are already recorded in each backend's docstring and in `docs/REFERENCES.md`
> (RANSAC = Fischler & Bolles 1981, SGM = Hirschmüller, PPF = Drost 2010, etc.).

## Sources (primary confirmation for authoring this doc)
- scikit-image data API: <https://scikit-image.org/docs/stable/api/skimage.data.html>
- scikit-image repository (per-image license): <https://github.com/scikit-image/scikit-image>
