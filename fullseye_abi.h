/* fullseye_abi.h — the Fullseye L1 contract.
 *
 * SPECIFICATION ONLY.  There is no C implementation of this header yet, and
 * writing one is NOT the point.  The point is that `fslib.py` must be a
 * conforming implementation of this contract, which turns "only allow things
 * that can be lowered to a C ABI" from a discipline into a machine check
 * (tests/test_abi_conformance.py).
 *
 * Why this file exists before any C code — docs/FSCRIPT_DECISION.md:
 *   - The point of no return is the PUBLISHED SEMANTICS, not the implementation
 *     language.  Freezing the contract early is what keeps the language, the
 *     backends, and eventually a native core interchangeable.
 *   - A design review scored "write the header first, make Python conform" the
 *     single best idea across four competing designs, precisely because it costs
 *     nothing now and forecloses nothing later.
 *
 * Rules this header encodes, in order of importance:
 *   R-1  Every operator returns fs_status_t.  Results travel through out-params.
 *        There are no exceptions, no sentinel values, and NO BENIGN FALLBACKS —
 *        a failed operator must be distinguishable from an operator that found
 *        nothing.  (The 650-op evolution registry deliberately does the
 *        opposite; that behaviour must never reach a line.  See
 *        docs/FSCRIPT_DECISION.md section 1.6b.)
 *   R-2  Iconic values are OPAQUE HANDLES.  Callers never see the storage, so
 *        Region can move from a dense mask to run-length encoding — the
 *        representation HALCON actually uses — without breaking anyone.
 *   R-3  An image carries its VALUE RANGE.  A threshold therefore means the same
 *        thing on every frame, which the current fscript path does not manage
 *        (one hot pixel changes a part's measured area from 256 to 1).
 *   R-4  The only things crossing this boundary are scalars, typed arrays,
 *        opaque handles, and status codes.  No dictionaries, no closures, no
 *        duck typing, no aliasing rules borrowed from numpy views.
 *   R-5  Ownership is explicit and uniform: every out-param handle is OWNED by
 *        the caller and released with the matching fs_*_release.  Nothing is
 *        borrowed across a call boundary.
 */

#ifndef FULLSEYE_ABI_H
#define FULLSEYE_ABI_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* --------------------------------------------------------------------------
 * Versioning — a recipe records the ABI version it was validated against, and a
 * runtime refuses to load a recipe from a different major version.
 * -------------------------------------------------------------------------- */
#define FULLSEYE_ABI_VERSION_MAJOR 0
#define FULLSEYE_ABI_VERSION_MINOR 1

/* --------------------------------------------------------------------------
 * R-1: status codes.  Every operator returns one of these.
 * -------------------------------------------------------------------------- */
typedef enum fs_status {
    FS_OK                 = 0,
    FS_E_INVALID_ARG      = 1,  /* a parameter is out of its declared domain    */
    FS_E_TYPE             = 2,  /* wrong sort: an image where a region is due   */
    FS_E_SHAPE            = 3,  /* shapes do not agree                          */
    FS_E_RANGE            = 4,  /* value outside the image's declared range     */
    FS_E_NO_BACKEND       = 5,  /* fail-closed: no validated implementation      */
    FS_E_UNSUPPORTED      = 6,  /* declared in the ABI, not implemented here    */
    FS_E_OUT_OF_MEMORY    = 7,
    FS_E_DEADLINE         = 8,  /* the cycle budget expired                     */
    FS_E_INTERNAL         = 9
} fs_status_t;

/* --------------------------------------------------------------------------
 * R-4: the only scalar/array element types that cross the boundary.
 * -------------------------------------------------------------------------- */
typedef enum fs_dtype {
    FS_DTYPE_U8  = 1,
    FS_DTYPE_U16 = 2,
    FS_DTYPE_F32 = 3,
    FS_DTYPE_F64 = 4
} fs_dtype_t;

/* Tuple element type — HALCON's control values are heterogeneous tuples. */
typedef enum fs_elem {
    FS_ELEM_INT    = 1,
    FS_ELEM_REAL   = 2,
    FS_ELEM_STRING = 3
} fs_elem_t;

/* --------------------------------------------------------------------------
 * R-2: opaque iconic and control handles.
 * -------------------------------------------------------------------------- */
typedef struct fs_image     fs_image_t;      /* pixels + dtype + range + domain */
typedef struct fs_region    fs_region_t;     /* a point set; storage unspecified */
typedef struct fs_objectset fs_objectset_t;  /* labelled objects + measurements  */
typedef struct fs_tuple     fs_tuple_t;      /* heterogeneous control tuple      */

/* A single run of set pixels on one row.  This is the ONLY view of a region's
 * storage the ABI exposes; it is what makes a run-length region and a dense
 * mask interchangeable behind the same contract. */
typedef struct fs_run {
    int32_t row;
    int32_t col_begin;   /* inclusive */
    int32_t col_end;     /* exclusive */
} fs_run_t;

/* --------------------------------------------------------------------------
 * R-3 + R-5: image lifecycle.  The range is supplied by whoever knows it (the
 * acquisition layer), never inferred from the pixels.
 * -------------------------------------------------------------------------- */
fs_status_t fs_image_create(const void *pixels,
                            int32_t height, int32_t width,
                            int64_t row_stride_bytes,
                            fs_dtype_t dtype,
                            double range_lo, double range_hi,
                            fs_image_t **out);
fs_status_t fs_image_shape(const fs_image_t *img, int32_t *height, int32_t *width);
fs_status_t fs_image_dtype(const fs_image_t *img, fs_dtype_t *out);
fs_status_t fs_image_range(const fs_image_t *img, double *lo, double *hi);
/* Map a 0..1 relative threshold onto this image's declared range. */
fs_status_t fs_image_absolute(const fs_image_t *img, double relative, double *out);
/* The processing domain (HALCON model); NULL region out means "full frame". */
fs_status_t fs_image_domain(const fs_image_t *img, fs_region_t **out);
fs_status_t fs_image_reduce_domain(const fs_image_t *img, const fs_region_t *dom,
                                   fs_image_t **out);
void        fs_image_release(fs_image_t *img);

/* --------------------------------------------------------------------------
 * Region — no dense mask is ever exposed (R-2).
 * -------------------------------------------------------------------------- */
fs_status_t fs_region_area(const fs_region_t *reg, int64_t *out);
fs_status_t fs_region_run_count(const fs_region_t *reg, int64_t *out);
fs_status_t fs_region_runs(const fs_region_t *reg, fs_run_t *buf,
                           int64_t buf_len, int64_t *written);
void        fs_region_release(fs_region_t *reg);

/* --------------------------------------------------------------------------
 * ObjectSet — labels + live ids + measurements that TRAVEL WITH THE SET.
 * Measuring the label image is one pass; an API that recomputes it per query
 * turned a 10 ms cycle into a 40 ms one during the PoC.
 * -------------------------------------------------------------------------- */
fs_status_t fs_objectset_count(const fs_objectset_t *objs, int64_t *out);
fs_status_t fs_objectset_region(const fs_objectset_t *objs, int64_t index,
                                fs_region_t **out);
void        fs_objectset_release(fs_objectset_t *objs);

/* --------------------------------------------------------------------------
 * Tuple — HALCON's control model: one tuple may mix ints, reals and strings.
 * -------------------------------------------------------------------------- */
fs_status_t fs_tuple_length(const fs_tuple_t *t, int64_t *out);
fs_status_t fs_tuple_elem_type(const fs_tuple_t *t, int64_t i, fs_elem_t *out);
/* The element type is carried by the tuple, not chosen by the caller: fetching
 * a FS_ELEM_REAL element with `fs_tuple_get_int` is FS_E_TYPE, not a silent
 * truncation.  This is the same stance `fslib`'s `_require` takes — a sort that
 * can be coerced away stops being a sort. */
fs_status_t fs_tuple_get_real(const fs_tuple_t *t, int64_t i, double *out);
fs_status_t fs_tuple_get_int(const fs_tuple_t *t, int64_t i, int64_t *out);
void        fs_tuple_release(fs_tuple_t *t);

/* --------------------------------------------------------------------------
 * OPERATORS.
 *
 * Naming and shape are the contract `fslib.py` is checked against:
 *   fs_<operator>(<inputs...>, <control...>, <outputs...>) -> fs_status_t
 *
 * `fslib` implements the same operator under the same name minus the `fs_`
 * prefix, taking the inputs and control in the same order and returning the
 * outputs in the same order.  tests/test_abi_conformance.py enforces this.
 * -------------------------------------------------------------------------- */

/* NOTE on placement: the `@fslib <name>` tag must sit in the comment block that
 * IMMEDIATELY precedes its declaration, and nothing between the tag and the
 * declaration may contain a `;` — tests/test_abi_conformance.py reads from the
 * tag to the first semicolon.  Prose that needs semicolons goes ABOVE the tag.
 * (Learned 2026-09-14: a long comment written between `@fslib gauss` and
 * `fs_gauss(...)` killed COLLECTION of that test file, which aborted the WHOLE
 * suite — pytest reported `Interrupted: 1 error during collection` and the
 * runner still exited 0.  Same family as [[feedback_test_import_kills_collection]]:
 * one file's parse error silently takes every other test with it.)
 *
 * The kernel is the sampled Gaussian truncated at FOUR standard deviations:
 * radius = (int)(4.0 * sigma + 0.5), weights normalised to sum to one, applied
 * separably.  Left unstated, two implementations pick different radii and the
 * results differ everywhere by a little.
 *
 * Pixels outside the image are obtained by reflecting ON the border:
 * `(d c b a | a b c d)` — index -1 reads pixel 0, index -2 reads pixel 1.  This
 * is scipy's `mode='reflect'` and OpenCV's `BORDER_REFLECT`.  It is NOT
 * OpenCV's default `BORDER_REFLECT_101` (`d c b | a b c d`), which reflects
 * about the border pixel instead.  Both are called "reflect"; they differ by
 * half a pixel, and the difference appears ONLY within `radius` of the edge.
 * (Measured 2026-09-14 on a 32x32 random image at sigma=1.0: the interior of the
 * two agreed to 4.6e-08 while the border differed by up to 0.13 — 13% of the
 * declared range.  A test that samples the interior cannot see this.)
 *
 * `sigma <= 0` is FS_E_INVALID_ARG, not a pass-through: R-1 again.
 *
 * NOTE (open): this header exposes no way to READ PIXELS BACK, so the output of
 * `fs_gauss` is observable across the ABI only by thresholding it.  Adding a
 * pixel accessor is a real decision (it fixes a memory layout at the boundary),
 * so it is deliberately NOT made here. */
fs_status_t fs_gauss(const fs_image_t *in, double sigma, fs_image_t **out);

/* @fslib threshold  — lo/hi are RELATIVE (0..1) and resolved through the
 * image's declared range, which is what makes the operator frame-independent.
 *
 * The interval is CLOSED on both ends: a pixel is selected when
 * `absolute(lo) <= v <= absolute(hi)`.  Left unstated, this is exactly the kind
 * of thing two implementations settle differently and nobody notices.
 *
 * `lo > hi` is FS_E_INVALID_ARG, not an empty region.  Rule R-1 says a failed
 * operator must be distinguishable from one that found nothing, and an inverted
 * interval is a caller mistake, not a legitimate way to ask for nothing.
 * (Measured 2026-09-14: a Rust implementation of this header rejected it while
 * `fslib` silently returned an empty region — found by running both on the same
 * inputs.  That is what a second implementation is for.)
 *
 * Pixels outside the image's DECLARED range are compared as they are: the range
 * is a declaration by the acquisition layer (R-3), not a claim about the data,
 * and clamping here would hide a mis-declared range. */
fs_status_t fs_threshold(const fs_image_t *in, double lo, double hi,
                         fs_region_t **out);

/* @fslib connection
 *
 * Connectivity is EIGHT-CONNECTED: pixels touching at a corner belong to the
 * same object.  This follows HALCON's default and is what a 3x3 morphological
 * neighbourhood implies.  An implementation that uses four-connectivity reports
 * a different object COUNT on the same region — a checkerboard is one object at
 * eight and N/2 objects at four — so this cannot be left to the backend.
 *
 * The objects are ordered by the position of their first run: increasing row,
 * then increasing column.  Ordering is part of the contract because callers
 * index into the set (`fs_objectset_region`), and an unspecified order makes a
 * recipe's output depend on which backend happened to run. */
fs_status_t fs_connection(const fs_region_t *in, fs_objectset_t **out);

/* @fslib measure_all — every live object measured in one pass. */
fs_status_t fs_measure_all(const fs_objectset_t *in,
                           fs_tuple_t **area, fs_tuple_t **row, fs_tuple_t **column);

/* @fslib select_shape — filters ids, sharing the label image and measurements.
 *
 * The interval is CLOSED on both ends, like `fs_threshold`, and the surviving
 * objects keep the input's order.
 *
 * `vmin > vmax` is FS_E_INVALID_ARG.  This is the same rule `fs_threshold`
 * already states, and it had to be written here too because the implementation
 * that obeyed it there did NOT obey it here: a recipe that swapped an area's
 * lower and upper bound silently selected nothing, which on a line reads as
 * "no defects".  (Found 2026-09-14 by running a second implementation of this
 * header against `fslib` — the same way the connectivity split was found.)
 *
 * An unrecognised `feature` is FS_E_INVALID_ARG.  The known names are
 * "area", "row" and "column" — the three `fs_measure_all` produces. */
fs_status_t fs_select_shape(const fs_objectset_t *in, const char *feature,
                            double vmin, double vmax, fs_objectset_t **out);

#ifdef __cplusplus
}
#endif
#endif /* FULLSEYE_ABI_H */
