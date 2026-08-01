# imgevolve — sample code (cross-library recipes)

Runnable style; `img` is a float64 HxW in [0,1]. imgevolve calls are exact; the OpenCV/scikit-image lines are the equivalent calls (args are illustrative). The full 57-op x 4-library API table is in `OPERATORS.md`.

## End-to-end workflow (evolve -> codegen -> verify)

```bash
# design an algorithm for a task, holdout-gated (writes into a shared workdir)
py -3.11 baseline.py --problem edge --workdir out/demo --seed 0
py -3.11 evolve.py   --problem edge --workdir out/demo --gens 40 --seed 0
py -3.11 report.py   --problem edge --workdir out/demo          # honest metrics
# emit the champion IR to Python + C, and verify the Python backend == the IR
py -3.11 codegen.py  --problem edge --workdir out/demo
py -3.11 difftest.py --problem edge --workdir out/demo          # diff < tol => faithful
```

The generated `out/demo/gen_edge.py` is a standalone module; `gen_edge.c` targets
the imgops runtime (compile-gated on a C toolchain). Tasks: `denoise / edge /
binarize / count / locate`. Run everything at once via `examples/quickstart.py`.


## Recipes by family

### Smoothing / denoise

```python
# imgevolve (typed stage; sigma = 0.3+2.7*a)
img = ops.RT["gaussian"](img, a=0.26, b=0.0)      # ~sigma 1.0
img = ops.RT["bilateral"](img, a=0.4, b=0.1)      # edge-preserving
# OpenCV
img = cv2.GaussianBlur(img, (0, 0), sigmaX=1.0)
img = cv2.bilateralFilter(img.astype("float32"), d=5, sigmaColor=0.1, sigmaSpace=2.0)
# scikit-image
from skimage import filters, restoration
img = filters.gaussian(img, sigma=1.0)
img = restoration.denoise_bilateral(img, sigma_color=0.1, sigma_spatial=2.0)
```

### Rank filters

```python
img = ops.RT["median"](img, a=0.3, b=0.0)         # 5x5 median
# OpenCV: cv2.medianBlur(img8, 5)
# skimage: filters.median(img, footprint=np.ones((5,5)))
```

### Gray morphology

```python
img = ops.RT["gopen"](img, a=0.3, b=0.0)          # gray opening 5x5
# OpenCV: cv2.morphologyEx(img, cv2.MORPH_OPEN, np.ones((5,5)))
# skimage: morphology.opening(img, morphology.square(5))
```

### Edges

```python
edges = ops.RT["sobel_mag"](img, 0, 0)            # normalised gradient magnitude
# OpenCV: cv2.magnitude(cv2.Sobel(img,-1,1,0), cv2.Sobel(img,-1,0,1))
# skimage: filters.sobel(img)
```

### Threshold / segment (image -> region)

```python
region = ops.RT["otsu"](img, 0, 0)                # Otsu -> binary region
region = ops.RT["canny"](img, a=0.3, b=0.4)       # Canny -> region
# OpenCV: _,region = cv2.threshold(img8,0,255,cv2.THRESH_OTSU); cv2.Canny(img8,50,150)
# skimage: img > filters.threshold_otsu(img); feature.canny(img)
```

### Region ops (region -> region / image)

```python
region = ops.RT["fill_holes"](region, 0, 0)       # fill holes
region = ops.RT["select_largest"](region, 0, 0)   # keep largest blob
dist   = ops.RT["dist_transform"](region, 0, 0)   # -> image (EDT)
# OpenCV: cv2.floodFill(...); connectedComponentsWithStats(...); cv2.distanceTransform(...)
# skimage: ndi.binary_fill_holes; measure.label+regionprops; ndi.distance_transform_edt
```

### Measurements (region -> feature)

```python
n    = ops.RT["blob_count"](region, 0, 0)         # number of connected components
frac = ops.RT["area_frac"](region, 0, 0)          # foreground fraction
# OpenCV: cv2.connectedComponents(region8)[0]-1 ; cv2.countNonZero(region8)/region.size
# skimage: measure.label(region).max() ; region.mean()
```

### XLD contours (image -> contour -> region/feature)

```python
cv_   = ops.RT["edges_sub_pix"](img, a=0.2, b=0)  # contours: {"shape":(H,W), "cs":[Nx2,...]}
cv_   = ops.RT["select_contours"](cv_, a=0.2, b=0)     # keep long contours
cv_   = ops.RT["fit_line_contours"](cv_, 0, 0)         # PCA line fit per contour
region = ops.RT["contours_to_region"](cv_, a=0.3, b=0) # rasterise -> region
length = ops.RT["total_length"](cv_, 0, 0)             # -> feature
# skimage: measure.find_contours(img, level); measure.LineModelND().estimate(pts)
# OpenCV: cv2.findContours(...); cv2.fitLine(...); cv2.arcLength(cnt, True)
```

### Template matching (image -> match)

```python
ops.set_match_template(template)                  # 11x11 reference patch
m = ops.RT["ncc_locate"](img, 0, 0)               # -> np.array([score, row, col])
# OpenCV: res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED); cv2.minMaxLoc(res)
# skimage: feature.match_template(img, template)
```
