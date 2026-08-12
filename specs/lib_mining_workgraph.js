export const meta = {
  name: 'imgevolve-lib-mining',
  description: 'Mine installed image libraries (PIL, scipy.signal/fft, skimage, cv2) for distinctive, genuinely-implementable single-gray-image ops not yet in the registry',
  phases: [{ title: 'Mine', detail: 'one agent per library group returns vetted op recommendations' }],
}

const DIR = 'C:/dev/projects/imgevolve'

const GROUPS = [
  { slug: 'pillow', libs: 'PIL / Pillow (ImageFilter, ImageOps, ImageEnhance, ImageChops)' },
  { slug: 'scipy', libs: 'scipy.signal (wiener, order_filter, ...) and scipy.fft (dct/idct) and scipy.ndimage extras' },
  { slug: 'skimage_more', libs: 'scikit-image submodules (filters, morphology, feature, segmentation, restoration, exposure, transform) — functions NOT already wrapped' },
  { slug: 'cv2_more', libs: 'OpenCV (cv2) functions NOT already wrapped — ximgproc-style, photo, features2d, imgproc' },
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
          name: { type: 'string' },           // proposed registry name, e.g. xpil_emboss
          lib_fn: { type: 'string' },          // the exact library call, e.g. PIL.ImageFilter.EMBOSS
          category: { type: 'string' },
          in_sort: { type: 'string' },         // image | region
          out_sort: { type: 'string' },        // image | region | feature
          recipe: { type: 'string' },          // one-line python: given gray float64 [0,1] `v`, produce the output
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
  return `You mine ONE image-processing library group for imgevolve: ${g.libs}.

imgevolve is a typed image-op registry. It already wraps a lot of scipy/OpenCV/
scikit-image. Your job: find DISTINCTIVE operators in your library group that are
(1) genuinely implementable on a SINGLE grayscale image (float64, values in [0,1],
2-D), (2) NOT already in the registry, (3) a real image TRANSFORM / SEGMENTATION /
MEASUREMENT — not IO, drawing, plotting, model training, or multi-image ops.

STEPS:
1. Introspect the installed library (import it; list its callables). It IS installed.
2. Read ${DIR}/backends.py, ${DIR}/backends_extra.py, ${DIR}/catalog.py and
   ${DIR}/ops.py to see what is ALREADY wrapped (avoid duplicates — e.g. gaussian,
   median, min/max, sobel, canny, otsu, morphology, bilateral, clahe, gabor,
   distance transform, blob detectors, inpaint, random_walker, ORB, stylization,
   pencil sketch are already covered — do NOT re-propose those).
3. For each genuinely NEW, distinctive op, produce a recommendation with:
   - name: xpil_/xsp_/xsk_/xcv_ + short_name (match your group's prefix: pillow=xpil_,
     scipy=xsp_, skimage_more=xsk2_, cv2_more=xcv2_)
   - lib_fn: the exact library symbol/call
   - in_sort (image or region), out_sort (image | region | feature)
   - recipe: ONE line of Python that, given a gray float64 [0,1] array \`v\` and two
     scalar knobs \`a\`,\`b\` in [0,1], returns the output IN THE PIPELINE CONVENTION
     (image/region -> 2-D float64 in [0,1]; feature -> a python float). Assume numpy
     as np, and the library imported. Keep it deterministic and exception-safe-able.
     Example: "np.asarray(PIL.Image.fromarray((v*255).astype('uint8')).filter(PIL.ImageFilter.EMBOSS),np.float64)/255"
   - distinctive_because: why HALCON/the core registry doesn't already cover it
   - caveat: any honest limitation (needs color? approximate? border effects?)
4. Be CONSERVATIVE and HONEST: only propose ops whose recipe genuinely computes the
   operation on a single gray image. If it needs color/multichannel, a second image,
   a trained model, or coordinates, SKIP it (summarise in skipped_note). Aim for
   quality: ~6-15 solid recommendations, not a padded list.
5. VERIFY each recipe runs: write a tiny throwaway check (python -c) that builds a
   64x64 gray test image and evals your recipe for a few (a,b); drop any that throw
   or return the wrong type/shape. Only return recipes that executed cleanly.

Return the structured object: library (your group), recommendations (verified),
skipped_note.`
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
log(`lib mining done: ${clean.length}/${GROUPS.length} agents, ${total} recommendations`)
return { agents: clean.length, total_recommendations: total, groups: clean }
