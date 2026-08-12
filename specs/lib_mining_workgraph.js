export const meta = {
  name: 'imgevolve-lib-mining',
  description: 'Mine installed image libraries (mahotas, PyWavelets, SimpleITK, skimage, cv2) for distinctive, genuinely-implementable single-gray-image ops not yet in the registry',
  phases: [{ title: 'Mine', detail: 'one agent per library group returns vetted op recommendations' }],
}

const DIR = 'C:/dev/projects/imgevolve'

const GROUPS = [
  { slug: 'mahotas', prefix: 'xmh_',
    libs: 'mahotas (Haralick texture, Zernike moments, SURF, template_match, thresholding (rc/bernsen), distance, regional maxima, bwperim, labeled features, sobel, dog, wavelet)',
    note: 'mahotas works on numpy arrays directly; many funcs want uint8 (use (v*255).astype(uint8)).' },
  { slug: 'pywt', prefix: 'xwt_',
    libs: 'PyWavelets / pywt (dwt2, wavedec2, swt2, wavelet-domain denoising/thresholding, wavelet packet)',
    note: 'pywt.dwt2(v, "db2") -> (cA,(cH,cV,cD)); reconstruct with pywt.idwt2. For a single-image output, tile the sub-bands or reconstruct a filtered image.' },
  { slug: 'sitk', prefix: 'xsitk_',
    libs: 'SimpleITK (CurvatureFlow, GradientAnisotropicDiffusion, CurvatureAnisotropicDiffusion, ConnectedThreshold, GeodesicActiveContourLevelSet, SignedMaurerDistanceMap, DiscreteGaussian, GradientMagnitude, LaplacianSharpening, Bilateral, Otsu/watershed, GrayscaleGeodesic)',
    note: 'SimpleITK works on sitk.Image: img=sitk.GetImageFromArray(v.astype("float32")); out=sitk.SomeFilter(img,...); result=sitk.GetArrayFromImage(out). Keep it deterministic; normalise to [0,1].' },
  { slug: 'skimage_r3', prefix: 'xsk3_',
    libs: 'scikit-image functions NOT already wrapped (round 3) — e.g. filters.rank.*, feature.*, morphology.*, restoration.*, exposure.*, transform.* leftovers',
    note: '' },
  { slug: 'cv2_r3', prefix: 'xcv3_',
    libs: 'OpenCV functions NOT already wrapped (round 3) — imgproc/photo/features2d leftovers (e.g. Gabor kernels, phase/spectral, Scharr, cornerSubPix, watershed variants, seamless, decolor)',
    note: '' },
]

const RET = {
  type: 'object',
  properties: {
    library: { type: 'string' },
    recommendations: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          lib_fn: { type: 'string' },
          category: { type: 'string' },
          in_sort: { type: 'string' },
          out_sort: { type: 'string' },
          recipe: { type: 'string' },
          distinctive_because: { type: 'string' },
          caveat: { type: 'string' },
        },
        required: ['name', 'lib_fn', 'in_sort', 'out_sort', 'recipe'],
      },
    },
    skipped_note: { type: 'string' },
  },
  required: ['library', 'recommendations'],
}

function prompt(g) {
  return `You mine ONE image library group for imgevolve: ${g.libs}.
Library note: ${g.note || '(none)'}

imgevolve is a typed image-op registry that already wraps a lot of scipy/OpenCV/
scikit-image/PIL. Find DISTINCTIVE operators in your group that are (1) genuinely
implementable on a SINGLE grayscale image (float64, [0,1], 2-D), (2) NOT already
wrapped, (3) a real image TRANSFORM / SEGMENTATION / MEASUREMENT — not IO, drawing,
plotting, model training, or multi-image ops.

STEPS:
1. Introspect the installed library (import it; list callables; read its docs via help()). It IS installed.
2. Read ${DIR}/backends.py, ${DIR}/backends_extra.py, ${DIR}/backends_pil.py,
   ${DIR}/backends_scipy.py, ${DIR}/backends_ski2.py, ${DIR}/backends_cv2b.py,
   ${DIR}/backends_auto.py and ${DIR}/ops.py to see what is ALREADY wrapped — do
   NOT re-propose duplicates (gaussian, median, min/max, sobel, canny, otsu,
   morphology, bilateral, clahe, gabor, distance transform, blobs, inpaint,
   random_walker, ORB, stylization, HOG, Radon, DCT, wiener, multi-otsu,
   reconstruction, h-maxima, mean-shift, hit-or-miss, FAST, etc. are covered).
3. For each genuinely NEW, distinctive op produce a recommendation:
   - name: ${g.prefix} + short_name
   - lib_fn: the exact library symbol/call
   - in_sort (image or region), out_sort (image | region | feature)
   - recipe: ONE line of Python that, given a gray float64 [0,1] array \`v\` and two
     scalar knobs \`a\`,\`b\` in [0,1], returns the output in the pipeline convention
     (image/region -> 2-D float64 in [0,1]; feature -> a python float). numpy as np;
     the library imported. Deterministic.
   - distinctive_because + caveat (honest).
4. Be CONSERVATIVE and HONEST: only ops whose recipe genuinely computes the
   operation on a single gray image. If it needs color/second image/trained model/
   coordinates, SKIP (note in skipped_note). Aim ~6-15 solid recs, not padding.
5. VERIFY each recipe runs: write a throwaway python -c that builds a 64x64 gray
   test image and evals your recipe for a few (a,b); DROP any that throw or return
   the wrong type/shape. Only return recipes that executed cleanly.

Return the structured object.`
}

phase('Mine')
const results = await parallel(
  GROUPS.map((g) => () => agent(prompt(g), {
    label: `mine-lib:${g.slug}`, phase: 'Mine', agentType: 'general-purpose',
    effort: 'high', schema: RET,
  })),
)

const clean = results.filter(Boolean)
const total = clean.reduce((s, r) => s + (r.recommendations ? r.recommendations.length : 0), 0)
log(`lib mining r3 done: ${clean.length}/${GROUPS.length} agents, ${total} recommendations`)
return { agents: clean.length, total_recommendations: total, groups: clean }
