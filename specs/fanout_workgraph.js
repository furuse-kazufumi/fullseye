export const meta = {
  name: 'imgevolve-halcon-fanout',
  description: 'Per-chapter mining of uncovered HALCON algorithm ops onto the fixed backends_auto shape vocabulary (genuine analogs only, honest skips)',
  phases: [{ title: 'Mine', detail: 'one agent per algorithm chapter maps uncovered unary ops to shapes' }],
}

const DIR = 'C:/dev/projects/imgevolve'

// The FIXED shape vocabulary (backends_auto.SHAPES). Agents MUST map onto these
// exact shapes + param enums — they never invent shapes or write code.
const VOCAB = `
FIXED SHAPE VOCABULARY (shape : in_sort->out_sort : params). Use ONLY these.
- pointwise  : image->image  : {func: abs|sqrt|square|exp|log|sin|cos|tan|asin|acos|atan|reciprocal}   pointwise gray math
- lut        : image->image  : {kind: gamma|scale|invert|sigmoid|log_gain|equalize|equalize_local|rescale|clip_range|illuminate|monotony}  gray LUT/contrast
- linfilter  : image->image  : {kind: gauss|mean|binomial|smooth|derivate_gauss|laplace_gauss|dog|mean_curvature|motion}  linear/smoothing/derivative/motion-blur
- rank       : image->image  : {kind: median|median_rect|min|max|rank|range|sigma|trimmed_mean}   rank/order-stat (min=gray erosion rect, max=gray dilation rect, range=local max-min)
- graymorph  : image->image  : {op: erosion|dilation|opening|closing|tophat|bothat|gradient, shape: rect|disk}   grayscale morphology
- edge       : image->image  : {kind: sobel|sobel_dir|prewitt|prewitt_dir|roberts|scharr|kirsch|kirsch_dir|frei|frei_dir|robinson|robinson_dir|laplace}  edge amplitude (_dir=direction)
- freq       : image->image  : {kind: fft_power|fft_power_real|fft_phase|ifft|lowpass|highpass|bandpass}   FFT domain (ifft=inverse transform)
- diffusion  : image->image  : {kind: isotropic|anisotropic|tv|bilateral|nlm}   edge-preserving denoise
- texture    : image->image  : {kind: deviation|variance|entropy|gabor|lbp|coherence}   texture response
- cooc       : image->feature : {prop: contrast|dissimilarity|homogeneity|energy|correlation|ASM}   Haralick co-occurrence texture feature (scalar)
- noise      : image->image  : {kind: gaussian|sp}   add deterministic noise
- geom       : image->image (mirror/transpose/affine/projective/zoom/polar may be region->region) : {kind: mirror|transpose|rotate|zoom|affine|projective|polar|polar_inv|swirl}   geometric transform
- threshold  : image->region : {method: fixed|otsu|li|yen|triangle|isodata|mean|minimum|sauvola|niblack|dyn|local_gauss|hysteresis|dual}   threshold to binary region (dual=signed |x-0.5|>t)
- segment    : image->region : {kind: canny|sk_canny|local_max|watershed|felzenszwalb|slic|chan_vese|regiongrow|mser}   segmentation to region/boundaries
- binmorph   : region->region: {op: erosion|dilation|opening|closing|erosion_it|dilation_it, shape: disk|rect}   binary morphology
- region_trans: region->region (dist_transform->image): {kind: fill_up|boundary|skeleton|medial|thin|convex|clear_border|remove_small|remove_holes|select_largest|dist_transform|shape_bbox}
- region_feat: region->feature: {metric: count|area|circularity|compactness|convexity|solidity|rectangularity|eccentricity|orientation|roundness|diameter|euler|anisometry|perimeter|area_holes|aspect|moment2|moment3|moment_central|hu1|hu2|hu3|hu4}   scalar shape measurement
- img_feat   : image->feature : {metric: min|max|mean|std|median|entropy|area_gray|noise_est}   gray statistics (scalar)
- xld        : image->contour {kind: edges_sub_pix|lines_gauss} ; contour->contour {kind: select_contours|smooth_contours|close|affine|projective|polar} ; contour->region {kind: to_region} ; contour->feature {kind: count|length|area|circularity|compactness|convexity|num_points}
Sorts are exactly: image, region, feature, contour. (Color/multichannel and 3D/volume ops are handled elsewhere — SKIP them here.)
`

// 8 chapter groups over the algorithm operators. XLD/Filters/Regions are the big
// ones; the rest are grouped. 3D/OCR/Classification/Deep-Learning are OUT of scope.
const GROUPS = [
  { slug: 'filters',        chapters: ['Filters'] },
  { slug: 'image',          chapters: ['Image'] },
  { slug: 'regions',        chapters: ['Regions'] },
  { slug: 'morph_segment',  chapters: ['Morphology', 'Segmentation'] },
  { slug: 'xld',            chapters: ['XLD'] },
  { slug: 'transform_tools',chapters: ['Transformations', 'Tools'] },
  { slug: 'matching',       chapters: ['Matching'] },
  { slug: 'misc_legacy',    chapters: ['Inspection', 'Legacy', 'Object', '2D Metrology', '1D Measuring'] },
]

const RET = {
  type: 'object',
  properties: {
    chapter: { type: 'string' },
    file: { type: 'string' },
    n_mapped: { type: 'integer' },
    n_skipped: { type: 'integer' },
    mapped_names: { type: 'array', items: { type: 'string' } },
    notable_skips: { type: 'array', items: { type: 'string' } },
  },
  required: ['chapter', 'n_mapped', 'n_skipped'],
}

function prompt(g) {
  const chs = g.chapters.map((c) => `"${c}"`).join(', ')
  return `You extend imgevolve's HALCON-parity operator registry for chapter group: ${g.chapters.join(' + ')}.

CONTEXT. imgevolve genuinely IMPLEMENTS HALCON operators by wrapping numpy/scipy/skimage/cv2 through a FIXED vocabulary of verified factory "shapes". Your job: map REAL uncovered HALCON operators in your chapters onto that vocabulary, as DATA only. You never write Python; you emit a JSON spec list. The user's bar is CAPABILITY PARITY ("do the same thing HALCON does"), so an analog counts ONLY if the chosen shape genuinely computes what the operator's short_desc describes. When unsure, SKIP — a wrong mapping is worse than a gap.

${VOCAB}

STEPS (do them):
1. Read ${DIR}/data/halcon_graph.json . It has {"nodes": {name: {top_chapter, short_desc, signature, arity, unary, is_algorithm, is_model, covered, sort_in_hint, sort_out_hint}}}.
2. Read ${DIR}/backends_auto.py — study the SHAPES factory bodies so you know EXACTLY what each shape/param computes, and see the SEED list of names already claimed (do NOT re-map those).
3. Select candidate operators: nodes where top_chapter is one of [${chs}] AND is_algorithm==true AND unary==true AND covered==false AND is_model==false.
4. For EACH candidate decide:
   - Is there a shape+params in the vocabulary that GENUINELY performs this operator (per its short_desc + signature)? Infer the correct in_sort/out_sort from the shape's contract and the operator (image filters -> image->image; thresholds/segmentation -> image->region; region morphology -> region->region; measurements returning tuples of scalars -> region->feature or image->feature; XLD -> contour). Use the sort_*_hint as a prior but TRUST the short_desc.
   - If yes -> emit a spec. If no genuine analog (needs a second image / color/multichannel / trained model / calibration / domain-ROI plumbing / 3D / arbitrary user LUT / interactive) -> SKIP it and add a one-line reason to notable_skips (keep to the most informative ~15).
5. WRITE the result to ${DIR}/data/auto_specs/${g.slug}.json as a UTF-8 JSON array. Each element:
   {"halcon": <real op name>, "category": <short family label>, "in_sort": <image|region|feature|contour>, "out_sort": <...>, "shape": <shape name>, "params": {<enum params>}}
   The array must be valid JSON (no comments, no trailing commas).
6. VERIFY your own file before returning: run
      cd ${DIR} && py -3.11 -W ignore -c "import json,backends_auto as B; real=B._real_ops(); S=json.load(open('data/auto_specs/${g.slug}.json',encoding='utf-8')); bad=[s['halcon'] for s in S if s['halcon'] not in real or s['shape'] not in B.SHAPES]; print('specs',len(S),'bad',bad)"
   Then run  cd ${DIR} && py -3.11 -W ignore verify_auto.py --failures  and confirm NONE of your mapped names appear under failures. REMOVE from your file any of your ops that fail the functional gate or are 'bad', and re-write the file. Iterate until your ops are clean.

HONESTY RULES (hard):
- Only use operator names that exist in the graph nodes for your chapters (they are real). Never invent names.
- Never map onto a shape that does something materially different from the operator. Prefer skipping.
- Every param value must be from the documented enums. No new shapes.
- Do not touch any file other than data/auto_specs/${g.slug}.json.

Return the structured summary: chapter (join of your chapters), file path, n_mapped, n_skipped, mapped_names (all), notable_skips.`
}

phase('Mine')
const results = await parallel(
  GROUPS.map((g) => () => agent(prompt(g), {
    label: `mine:${g.slug}`, phase: 'Mine', agentType: 'general-purpose',
    effort: 'high', schema: RET,
  })),
)

const clean = results.filter(Boolean)
const total = clean.reduce((s, r) => s + (r.n_mapped || 0), 0)
log(`fan-out done: ${clean.length}/${GROUPS.length} agents, ${total} ops mapped total`)
return { agents: clean.length, total_mapped: total, per_chapter: clean }
