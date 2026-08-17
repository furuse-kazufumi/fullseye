"""algo.py — the general-algorithm op tier (algo-c parity, opt-in, image-focus-safe).

Fullseye's core is an *image* algorithm-design AI: the ``ops.REGISTRY`` evolves
image/region/feature/contour/volume pipelines and codegens them to C. General
algorithms (sorting, searching, numerics, graphs) do not thread through a 2-D
raster, so forcing them into that registry would both be awkward and dilute the
image focus. This module is therefore a **separate, opt-in tier** with its own
small registry, its own value sorts (``seq`` = 1-D numeric array, ``scalar`` =
one number), and its own codegen/difftest — none of it touches ``ops.REGISTRY``,
so the image evolution and its Wave-0 champion pins are completely unaffected.

Provenance discipline (``docs/GENERAL_ALGORITHMS.md`` / ``feedback_provenance_
research_method``): every algorithm here is **re-implemented from its textbook
specification**, not copied from the algo-c sources (Okumura, *C言語による標準
アルゴリズム事典*). The book is the category map; the code is our own. Each op
carries a one-line ``provenance`` naming the standard method it implements.

The honest gate (see ``algo_difftest.py``):
  * the Python reference is checked against a ground-truth oracle (``numpy`` for
    sorts, which reorders values the same way regardless of algorithm), and
  * the codegen C is compiled and run, then compared **bit-for-bit** to the
    Python reference on holdout inputs — a real cross-language measurement, not a
    deferred skip, whenever a C toolchain (gcc/clang, or ``python -m ziglang cc``)
    is available.

Single source of truth: each op stores its Python body and its C body as source
strings. The in-process reference callable is compiled from the very same string
that ``algo_codegen`` emits, so the tested oracle and the shipped artifact can
never drift apart.

Scope (honest): inputs are assumed **NaN-free**. Comparison sorts have no total
order on NaN, so quicksort/heapsort/mergesort place a NaN differently from each
other and from ``numpy.sort``, and ``seq_max``/``seq_min`` become order-dependent
with a NaN present. NaN is therefore excluded from the difftest holdout and the
gate is fail-closed on any non-finite value (``algo_difftest``), rather than
silently certifying a divergent result. Later numeric phases (P2) that can
legitimately produce NaN will define their own convention explicitly.

stdlib only (the Python references use no numpy — they mirror the C index-by-index
so "re-implemented from spec" is visibly true). P1: seq/scalar + 3 sorts + 2
reductions. Later phases add ops here: P2 numerics, P3 strings, P4 graphs, P5 number
theory / compression / hashing (gcd, primes, modular exponentiation, CRC-32, RLE),
P6 computational geometry (polygon area, point-in-polygon, convex hull, segment
intersection; integer coords, exact), P8 search / selection (binary search,
k-th smallest), P9 statistics (distinct count, mode), P10 number theory 2
(deterministic Miller-Rabin primality, modular inverse), P11 bit manipulation
(xor reduce, population count), P12 extended Euclidean algorithm (Bezout
coefficients; variable-length seq -> 3-value seq).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

# --- value sorts for the general tier (distinct from the image sorts) -------- #
SEQ = "seq"        # a 1-D sequence of real numbers (Python: list[float]; C: double*)
SCALAR = "scalar"  # a single real number (Python: float; C: double)

# Kinds tell the codegen/driver how an op is called at the C boundary:
#   "sort_inplace" : void f(double* a, int n)                 — reorders a in place
#   "reduce"       : double f(const double* a, int n)         — folds a to one number
#   "map_varlen"   : int  f(const double* a, int n, double* out)
#                        — reads n inputs, writes out_len (<= n) doubles to `out`,
#                          returns out_len (>= 0). A VARIABLE-LENGTH seq -> seq map:
#                          the input length is NOT the output length (unlike a sort).
#                          Fail-soft: returns 0 (empty) on malformed / no-solution
#                          input, so a caller buffer of size n always suffices.
KIND_SORT = "sort_inplace"
KIND_REDUCE = "reduce"
KIND_MAP = "map_varlen"


@dataclass(frozen=True)
class AlgoOp:
    """One general-purpose algorithm, with a Python reference and a C reference.

    ``py_code`` defines a top-level ``run(a)`` (``a`` a Python list of floats):
    a sort returns a new sorted list; a reduction returns a float; a variable-length
    map (``KIND_MAP``) returns a new list whose length may differ from the input.
    ``c_code`` is the C definition of ``c_func`` with the signature implied by
    ``kind``. Both are re-implementations from the named ``provenance`` method.
    """

    name: str
    category: str        # "sort" | "reduce" | "numeric"
    in_sort: str         # SEQ
    out_sort: str        # SEQ | SCALAR
    kind: str            # KIND_SORT | KIND_REDUCE
    c_func: str          # the C function name emitted / called
    py_code: str         # standalone source defining run(a)
    c_code: str          # C source defining c_func
    doc: str
    provenance: str
    # Oracle tolerance for the honest gate's Python-vs-oracle half. Sorts/reductions
    # only move or select existing doubles, so they must match EXACTLY (0.0). Numeric
    # ops accumulate (order-dependent float), so they are checked against an
    # independent oracle within this tolerance — while C-vs-Python stays bit-exact
    # (same algorithm, same order). See docs/GENERAL_ALGORITHMS.md P2.
    tol: float = 0.0


# --------------------------------------------------------------------------- #
# Python references — re-implemented from spec, index-by-index like the C so the
# equivalence is auditable. Pure stdlib; operate on / return Python lists.
# --------------------------------------------------------------------------- #
_PY_QUICKSORT = '''\
def run(a):
    """Quicksort with 3-way (Dutch national flag) partition + median-of-three pivot.

    Three-way partitioning collects keys EQUAL to the pivot in the middle and
    recurses only on the strictly-smaller / strictly-greater sides, so runs of
    equal keys collapse to O(n): all-equal and few-distinct inputs (e.g. a binary
    mask flattened to a sequence) stay O(n log n), where a plain Lomuto quicksort
    degrades to O(n^2). Median-of-three additionally protects sorted / reverse
    inputs. Iterative (explicit stack, larger side pushed first) so stack depth is
    O(log n). In place on a copy. Assumes NaN-free input (see module docstring).
    """
    a = list(a)
    n = len(a)
    if n < 2:
        return a
    stack = [(0, n - 1)]
    while stack:
        lo, hi = stack.pop()
        if lo >= hi:
            continue
        mid = lo + (hi - lo) // 2
        # median-of-three: order a[lo] <= a[mid] <= a[hi]; use a[mid] as pivot value
        if a[mid] < a[lo]:
            a[lo], a[mid] = a[mid], a[lo]
        if a[hi] < a[lo]:
            a[lo], a[hi] = a[hi], a[lo]
        if a[hi] < a[mid]:
            a[mid], a[hi] = a[hi], a[mid]
        pivot = a[mid]
        lt, i, gt = lo, lo, hi          # a[lo..lt-1] < pivot, a[gt+1..hi] > pivot
        while i <= gt:
            if a[i] < pivot:
                a[lt], a[i] = a[i], a[lt]; lt += 1; i += 1
            elif a[i] > pivot:
                a[i], a[gt] = a[gt], a[i]; gt -= 1
            else:
                i += 1                   # a[i] == pivot: leave it in the middle band
        lsz, rsz = lt - lo, hi - gt      # sizes of the two outer ranges
        if lsz > rsz:                    # push the larger side first -> stack O(log n)
            stack.append((lo, lt - 1))
            stack.append((gt + 1, hi))
        else:
            stack.append((gt + 1, hi))
            stack.append((lo, lt - 1))
    return a
'''

_C_QUICKSORT = '''\
/* Quicksort: 3-way (Dutch national flag) partition, median-of-three pivot,
 * explicit stack. Equal keys collect in the middle band, so all-equal /
 * few-distinct inputs stay O(n log n) (a plain Lomuto scan would be O(n^2)). */
static void _swap(double* a, int i, int j) { double t = a[i]; a[i] = a[j]; a[j] = t; }
void quicksort(double* a, int n) {
    if (n < 2) return;
    /* 3-way + push-larger-first bounds depth to ~log2(n); n is a 32-bit int, so
     * depth <= ~31 and 128 slots are comfortably safe. */
    int lo_st[128], hi_st[128], sp = 0;
    lo_st[sp] = 0; hi_st[sp] = n - 1; sp++;
    while (sp > 0) {
        sp--;
        int lo = lo_st[sp], hi = hi_st[sp];
        if (lo >= hi) continue;
        int mid = lo + (hi - lo) / 2;
        if (a[mid] < a[lo]) _swap(a, lo, mid);
        if (a[hi] < a[lo]) _swap(a, lo, hi);
        if (a[hi] < a[mid]) _swap(a, mid, hi);
        double pivot = a[mid];
        int lt = lo, i = lo, gt = hi;
        while (i <= gt) {
            if (a[i] < pivot) { _swap(a, lt, i); lt++; i++; }
            else if (a[i] > pivot) { _swap(a, i, gt); gt--; }
            else i++;
        }
        int lsz = lt - lo, rsz = hi - gt;
        if (lsz > rsz) {
            lo_st[sp] = lo; hi_st[sp] = lt - 1; sp++;
            lo_st[sp] = gt + 1; hi_st[sp] = hi; sp++;
        } else {
            lo_st[sp] = gt + 1; hi_st[sp] = hi; sp++;
            lo_st[sp] = lo; hi_st[sp] = lt - 1; sp++;
        }
    }
}
'''

_PY_HEAPSORT = '''\
def run(a):
    """Heapsort (binary max-heap, sift-down), in place on a copy. Williams 1964."""
    a = list(a)
    n = len(a)

    def sift_down(start, end):
        root = start
        while 2 * root + 1 <= end:
            child = 2 * root + 1
            if child + 1 <= end and a[child] < a[child + 1]:
                child += 1
            if a[root] < a[child]:
                a[root], a[child] = a[child], a[root]
                root = child
            else:
                return

    for start in range(n // 2 - 1, -1, -1):
        sift_down(start, n - 1)
    for end in range(n - 1, 0, -1):
        a[0], a[end] = a[end], a[0]
        sift_down(0, end - 1)
    return a
'''

# Named heapsort_asc, not heapsort: BSD <stdlib.h> already declares heapsort()
# (and mergesort()/radixsort()), so the plain name fails to compile on macOS/BSD.
_C_HEAPSORT = '''\
/* Heapsort: binary max-heap with sift-down (Williams 1964). */
static void _sift_down(double* a, int start, int end) {
    int root = start;
    for (;;) {
        long long child = 2LL * root + 1;      /* 64-bit: 2*root can exceed INT_MAX */
        if (child > end) return;
        int c = (int)child;                    /* child <= end < 2^31, safe to narrow */
        if (c + 1 <= end && a[c] < a[c + 1]) c++;
        if (a[root] < a[c]) {
            double t = a[root]; a[root] = a[c]; a[c] = t;
            root = c;
        } else return;
    }
}
void heapsort_asc(double* a, int n) {
    for (int start = n / 2 - 1; start >= 0; start--) _sift_down(a, start, n - 1);
    for (int end = n - 1; end > 0; end--) {
        double t = a[0]; a[0] = a[end]; a[end] = t;
        _sift_down(a, 0, end - 1);
    }
}
'''

_PY_MERGESORT = '''\
def run(a):
    """Mergesort (top-down, stable, temp buffer), on a copy. von Neumann 1945."""
    a = list(a)
    n = len(a)
    if n < 2:
        return a
    tmp = [0.0] * n

    def msort(lo, hi):                      # sort a[lo:hi]
        if hi - lo <= 1:
            return
        mid = (lo + hi) // 2
        msort(lo, mid)
        msort(mid, hi)
        i, j, k = lo, mid, lo
        while i < mid and j < hi:
            if a[i] <= a[j]:                # <= keeps equal keys in order (stable)
                tmp[k] = a[i]; i += 1
            else:
                tmp[k] = a[j]; j += 1
            k += 1
        while i < mid:
            tmp[k] = a[i]; i += 1; k += 1
        while j < hi:
            tmp[k] = a[j]; j += 1; k += 1
        for t in range(lo, hi):
            a[t] = tmp[t]

    msort(0, n)
    return a
'''

_C_MERGESORT = '''\
/* Mergesort: top-down, stable, single temp buffer (von Neumann 1945). */
static void _msort(double* a, double* tmp, int lo, int hi) {
    if (hi - lo <= 1) return;
    int mid = lo + (hi - lo) / 2;
    _msort(a, tmp, lo, mid);
    _msort(a, tmp, mid, hi);
    int i = lo, j = mid, k = lo;
    while (i < mid && j < hi) {
        if (a[i] <= a[j]) tmp[k++] = a[i++];   /* <= is what makes it stable */
        else tmp[k++] = a[j++];
    }
    while (i < mid) tmp[k++] = a[i++];
    while (j < hi) tmp[k++] = a[j++];
    for (int t = lo; t < hi; t++) a[t] = tmp[t];
}
/* Stable in-place fallback so an allocation failure still returns SORTED output
 * (fail-closed on correctness), not a silently-unsorted array. */
static void _ins_sort(double* a, int n) {
    for (int i = 1; i < n; i++) {
        double key = a[i]; int j = i - 1;
        while (j >= 0 && a[j] > key) { a[j + 1] = a[j]; j--; }
        a[j + 1] = key;
    }
}
void mergesort_asc(double* a, int n) {
    if (n < 2) return;
    double* tmp = (double*)malloc((size_t)n * sizeof(double));
    if (!tmp) { _ins_sort(a, n); return; }     /* OOM: correct (stable) but O(n^2) */
    _msort(a, tmp, 0, n);
    free(tmp);
}
'''

_PY_SEQ_MAX = '''\
def run(a):
    """Maximum of a sequence (exact; order-independent for NaN-free input). Empty -> 0.0."""
    if len(a) == 0:
        return 0.0
    m = a[0]
    for i in range(1, len(a)):
        if a[i] > m:
            m = a[i]
    return m
'''

_C_SEQ_MAX = '''\
/* Maximum of a sequence (exact; order-independent for NaN-free input). Empty -> 0.0. */
double seq_max(const double* a, int n) {
    if (n <= 0) return 0.0;
    double m = a[0];
    for (int i = 1; i < n; i++) if (a[i] > m) m = a[i];
    return m;
}
'''

_PY_SEQ_MIN = '''\
def run(a):
    """Minimum of a sequence (exact; order-independent for NaN-free input). Empty -> 0.0."""
    if len(a) == 0:
        return 0.0
    m = a[0]
    for i in range(1, len(a)):
        if a[i] < m:
            m = a[i]
    return m
'''

_C_SEQ_MIN = '''\
/* Minimum of a sequence (exact; order-independent for NaN-free input). Empty -> 0.0. */
double seq_min(const double* a, int n) {
    if (n <= 0) return 0.0;
    double m = a[0];
    for (int i = 1; i < n; i++) if (a[i] < m) m = a[i];
    return m;
}
'''


# --------------------------------------------------------------------------- #
# P2 — numeric ops (self-contained: the polynomial / samples are packed into the
# input seq, so no function is passed across the boundary and the op stays a pure
# seq -> scalar map that codegens to C exactly like the reductions. Accumulate, so
# C-vs-Python is bit-exact (same order) but Python-vs-oracle uses a tolerance.
# --------------------------------------------------------------------------- #
_PY_SIMPSON = '''\
def run(a):
    """Composite Simpson's rule on samples: a = [h, y0, y1, ..., y_{m-1}].

    Integrates m samples spaced h apart. Uses Simpson over the largest even number
    of intervals; a trailing odd interval (even m) is closed with the trapezoid
    rule. m < 2 integrates to 0.0.
    """
    if len(a) < 2:
        return 0.0
    h = a[0]
    y = a[1:]
    m = len(y)
    if m < 2:
        return 0.0
    total = 0.0
    n_int = m - 1
    k = n_int if n_int % 2 == 0 else n_int - 1   # even interval count for Simpson
    i = 0
    while i < k:
        total = total + (h / 3.0) * (y[i] + 4.0 * y[i + 1] + y[i + 2])
        i = i + 2
    if k < n_int:                                # one leftover interval -> trapezoid
        total = total + (h / 2.0) * (y[m - 2] + y[m - 1])
    return total
'''

_C_SIMPSON = '''\
/* Composite Simpson's rule on samples a = [h, y0..y_{m-1}]. */
double simpson(const double* a, int n) {
    if (n < 2) return 0.0;
    double h = a[0];
    const double* y = a + 1;
    int m = n - 1;
    if (m < 2) return 0.0;
    double total = 0.0;
    int n_int = m - 1;
    int k = (n_int % 2 == 0) ? n_int : n_int - 1;
    for (int i = 0; i < k; i += 2)
        total = total + (h / 3.0) * (y[i] + 4.0 * y[i + 1] + y[i + 2]);
    if (k < n_int)
        total = total + (h / 2.0) * (y[m - 2] + y[m - 1]);
    return total;
}
'''

_PY_BISECTION = '''\
def run(a):
    """Bisection root of a polynomial in a bracket: a = [lo, hi, c0, c1, ..., cn]
    (ascending coeffs, p(x) = sum c_i x^i). 100 iterations. If [lo,hi] does not
    straddle a sign change the precondition is violated: the result is some point in
    [lo,hi] but NOT a root (fail-soft, no crash — verify with |p(x)| if it matters).
    """
    if len(a) < 3:
        return 0.0
    lo = a[0]
    hi = a[1]
    c = a[2:]
    nc = len(c)

    def pev(x):
        r = 0.0
        for i in range(nc - 1, -1, -1):          # Horner, highest degree first
            r = r * x + c[i]
        return r

    flo = pev(lo)
    if flo == 0.0:
        return lo
    if pev(hi) == 0.0:
        return hi
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        fm = pev(mid)
        if fm == 0.0:
            return mid
        if (flo < 0.0) != (fm < 0.0):            # sign change in [lo, mid]
            hi = mid
        else:
            lo = mid
            flo = fm
    return 0.5 * (lo + hi)
'''

_C_BISECTION = '''\
/* Bisection root of a polynomial in a bracket a = [lo, hi, c0..cn]. */
static double _poly_eval(const double* c, int nc, double x) {
    double r = 0.0;
    for (int i = nc - 1; i >= 0; i--) r = r * x + c[i];
    return r;
}
double bisection(const double* a, int n) {
    if (n < 3) return 0.0;
    double lo = a[0], hi = a[1];
    const double* c = a + 2;
    int nc = n - 2;
    double flo = _poly_eval(c, nc, lo);
    if (flo == 0.0) return lo;
    if (_poly_eval(c, nc, hi) == 0.0) return hi;
    for (int it = 0; it < 100; it++) {
        double mid = 0.5 * (lo + hi);
        double fm = _poly_eval(c, nc, mid);
        if (fm == 0.0) return mid;
        if ((flo < 0.0) != (fm < 0.0)) hi = mid;
        else { lo = mid; flo = fm; }
    }
    return 0.5 * (lo + hi);
}
'''

_PY_NEWTON = '''\
def run(a):
    """Newton-Raphson root of a polynomial from x0: a = [x0, c0, c1, ..., cn]
    (ascending coeffs). Up to 100 iterations; stops when |step| < 1e-12 or the
    derivative vanishes. Fail-soft, no crash: on a vanishing derivative, or if it
    cycles / diverges within 100 iterations, it returns the current x, which is NOT
    a root (verify with |p(x)| if it matters — same caveat as bisection)."""
    if len(a) < 2:
        return 0.0
    x = a[0]
    c = a[1:]
    nc = len(c)
    for _ in range(100):
        p = 0.0
        dp = 0.0
        for i in range(nc - 1, -1, -1):          # p and p' by simultaneous Horner
            dp = dp * x + p
            p = p * x + c[i]
        if dp == 0.0:
            return x
        step = p / dp
        x = x - step
        as_ = -step if step < 0.0 else step
        if as_ < 1e-12:
            return x
    return x
'''

_C_NEWTON = '''\
/* Newton-Raphson root of a polynomial from x0: a = [x0, c0..cn]. */
double newton(const double* a, int n) {
    if (n < 2) return 0.0;
    double x = a[0];
    const double* c = a + 1;
    int nc = n - 1;
    for (int it = 0; it < 100; it++) {
        double p = 0.0, dp = 0.0;
        for (int i = nc - 1; i >= 0; i--) {      /* p and p' by simultaneous Horner */
            dp = dp * x + p;
            p = p * x + c[i];
        }
        if (dp == 0.0) return x;
        double step = p / dp;
        x = x - step;
        double as = step < 0.0 ? -step : step;
        if (as < 1e-12) return x;
    }
    return x;
}
'''


# --------------------------------------------------------------------------- #
# P2 — linear solve (variable-length seq -> seq). The whole system is packed into
# the input seq so no matrix object crosses the boundary; the op still codegens to
# C exactly like the others, but produces a shorter output (KIND_MAP). Accumulates,
# so C-vs-Python is bit-exact (same order, -ffp-contract=off) while Python-vs-oracle
# (np.linalg.solve) uses a tolerance.
# --------------------------------------------------------------------------- #
_PY_GAUSS = '''\
def run(a):
    """Solve a linear system A x = b by Gaussian elimination with partial pivoting.

    The whole system is packed into the input sequence (no matrix object crosses the
    boundary, so this codegens to C exactly like the other ops):

        a = [n, row0..., row1..., ..., row_{n-1}...]

    where the augmented matrix is n rows x (n+1) columns in row-major order (each row
    = n coefficients followed by its right-hand side). Returns the solution vector
    [x0, ..., x_{n-1}] (length n) — a VARIABLE-LENGTH output, shorter than the input.

    Fail-soft (no exception): returns [] if the input is malformed (n < 1, n out of
    the int range the C mirror supports, or too few values) or if the matrix is
    singular (a zero pivot survives partial pivoting = no unique solution). Verify a
    result with the residual |A x - b| if it matters. NaN-free input assumed (a NaN
    pivot makes the |pivot| comparison meaningless — see the module docstring)."""
    if len(a) < 1:
        return []
    n_d = a[0]
    # 1 <= n <= 46340 keeps 1 + n*(n+1) within int32 in the C mirror (46341^2 < 2^31).
    if not (n_d >= 1.0 and n_d <= 46340.0):        # also rejects NaN
        return []
    n = int(n_d)
    need = 1 + n * (n + 1)
    if len(a) < need:
        return []
    w = n + 1                                       # columns in the augmented matrix
    # copy the augmented matrix into a mutable n x (n+1) table (row-major -> rows)
    m = [[a[1 + r * w + c] for c in range(w)] for r in range(n)]
    for col in range(n):                            # forward elimination, partial pivoting
        piv = col                                   # row with the largest |entry| in this column
        best = m[col][col]
        if best < 0.0:
            best = -best
        for r in range(col + 1, n):
            v = m[r][col]
            if v < 0.0:
                v = -v
            if v > best:
                best = v
                piv = r
        if best == 0.0:
            return []                               # singular: no unique solution
        if piv != col:
            m[col], m[piv] = m[piv], m[col]
        for r in range(col + 1, n):
            factor = m[r][col] / m[col][col]
            m[r][col] = 0.0                         # exact zero (not factor*pivot) -> matches C
            for c in range(col + 1, w):
                m[r][c] = m[r][c] - factor * m[col][c]
    x = [0.0] * n                                   # back substitution
    for row in range(n - 1, -1, -1):
        s = m[row][n]
        for c in range(row + 1, n):
            s = s - m[row][c] * x[c]
        x[row] = s / m[row][row]
    return x
'''

_C_GAUSS = '''\
/* Solve A x = b by Gaussian elimination with partial pivoting.
 * Input a = [n, augmented n x (n+1) matrix, row-major]; writes the length-n solution
 * to `out` (caller buffer of >= n doubles) and returns n. Returns 0 (empty) on
 * malformed input (n < 1 / out of range / too short) or a singular matrix
 * (fail-soft, no crash). NaN-free input assumed. */
int gauss_solve(const double* a, int n_in, double* out) {
    if (n_in < 1) return 0;
    double n_d = a[0];
    /* 1 <= n <= 46340 keeps 1 + n*(n+1) within int32 (46341^2 < 2^31). */
    if (!(n_d >= 1.0 && n_d <= 46340.0)) return 0;          /* also rejects NaN */
    int n = (int)n_d;
    long long need = 1LL + (long long)n * (n + 1);
    if ((long long)n_in < need) return 0;
    if (!out) return n;                                     /* size probe: out_len upper bound = n */
    int w = n + 1;
    double* m = (double*)malloc((size_t)n * (size_t)w * sizeof(double));
    if (!m) return 0;
    for (int r = 0; r < n; r++)
        for (int c = 0; c < w; c++)
            m[r * w + c] = a[1 + r * w + c];
    for (int col = 0; col < n; col++) {             /* forward elimination, partial pivoting */
        int piv = col;
        double best = m[col * w + col];
        if (best < 0.0) best = -best;
        for (int r = col + 1; r < n; r++) {
            double v = m[r * w + col];
            if (v < 0.0) v = -v;
            if (v > best) { best = v; piv = r; }
        }
        if (best == 0.0) { free(m); return 0; }     /* singular */
        if (piv != col)
            for (int c = 0; c < w; c++) {
                double t = m[col * w + c];
                m[col * w + c] = m[piv * w + c];
                m[piv * w + c] = t;
            }
        for (int r = col + 1; r < n; r++) {
            double factor = m[r * w + col] / m[col * w + col];
            m[r * w + col] = 0.0;                    /* exact zero, matches Python */
            for (int c = col + 1; c < w; c++)
                m[r * w + c] = m[r * w + c] - factor * m[col * w + c];
        }
    }
    for (int row = n - 1; row >= 0; row--) {        /* back substitution */
        double s = m[row * w + n];
        for (int c = row + 1; c < n; c++)
            s = s - m[row * w + c] * out[c];
        out[row] = s / m[row * w + row];
    }
    free(m);
    return n;
}
'''


# --------------------------------------------------------------------------- #
# P3 — string / text ops. A "string" is packed as a sequence of code points stored
# as float64 (exact for every Unicode scalar, < 2^53), so these ride the SAME
# float64 binary harness as the numeric ops — no new wire type. Values are only
# ever compared for equality (exact for integer codes) and indices/counts are exact
# integers, so C-vs-Python is bit-identical and the oracle half is EXACT (tol 0.0).
# strfind returns match positions (variable-length -> KIND_MAP); edit_distance /
# lcs_length fold to one integer (KIND_REDUCE). See text_to_seq() for the encoding.
# --------------------------------------------------------------------------- #
_PY_STRFIND = '''\
def run(a):
    """All start positions of a pattern in a text (Knuth-Morris-Pratt).

    Input packs both strings as code-point sequences: a = [m, p0..p_{m-1}, t0..t_{k-1}]
    where m = pattern length, the next m values are the pattern, the rest are the text.
    Returns the ascending list of 0-based start indices where the pattern occurs in the
    text (overlapping occurrences included) — a VARIABLE-LENGTH output.

    Fail-soft (returns []): empty pattern (m < 1), truncated input (fewer than m pattern
    values), or a pattern longer than the text. Values are compared with ==, so any
    numeric sequence works, but the str oracle only makes sense for code points."""
    if len(a) < 1:
        return []
    m_d = a[0]
    # raw-value guard BEFORE int() so Python matches the C guard EXACTLY: a fractional
    # (int() truncation), negative, NaN (comparison-false), or oversized header fail-softs
    # identically in both -> no Python-vs-C divergence, no int(nan) crash. m >= 1 avoids the
    # degenerate empty-pattern "" -> every-gap convention.
    if not (m_d >= 1.0 and m_d <= 2147483000.0):
        return []
    m = int(m_d)
    if len(a) < 1 + m:
        return []                                   # truncated pattern
    pat = a[1:1 + m]
    text = a[1 + m:]
    k = len(text)
    if m > k:
        return []                                   # pattern longer than text: no matches
    fail = [0] * m                                  # KMP failure = longest proper prefix-suffix
    j = 0
    for i in range(1, m):
        while j > 0 and pat[i] != pat[j]:
            j = fail[j - 1]
        if pat[i] == pat[j]:
            j = j + 1
        fail[i] = j
    res = []
    j = 0
    for i in range(k):
        while j > 0 and text[i] != pat[j]:
            j = fail[j - 1]
        if text[i] == pat[j]:
            j = j + 1
        if j == m:
            res.append(float(i - m + 1))
            j = fail[j - 1]
    return res
'''

_C_STRFIND = '''\
/* All start positions of a pattern in a text (Knuth-Morris-Pratt).
 * Input a = [m, pattern(m), text(k)]; writes ascending match indices to `out` and
 * returns the count. Returns 0 (empty) on m < 1 / truncated / pattern-longer-than-text. */
int strfind(const double* a, int n_in, double* out) {
    if (n_in < 1) return 0;
    double m_d = a[0];
    if (!(m_d >= 1.0 && m_d <= 2147483000.0)) return 0;     /* m >= 1, fits int */
    int m = (int)m_d;
    if ((long long)n_in < 1LL + m) return 0;                /* truncated pattern */
    const double* pat = a + 1;
    const double* text = a + 1 + m;
    int k = n_in - 1 - m;
    if (m > k) return 0;                                    /* pattern longer than text */
    if (!out) return k;                                     /* size probe: at most k matches */
    int* fail = (int*)malloc((size_t)m * sizeof(int));
    if (!fail) return 0;
    fail[0] = 0;
    int j = 0;
    for (int i = 1; i < m; i++) {
        while (j > 0 && pat[i] != pat[j]) j = fail[j - 1];
        if (pat[i] == pat[j]) j++;
        fail[i] = j;
    }
    int cnt = 0;
    j = 0;
    for (int i = 0; i < k; i++) {
        while (j > 0 && text[i] != pat[j]) j = fail[j - 1];
        if (text[i] == pat[j]) j++;
        if (j == m) {
            out[cnt++] = (double)(i - m + 1);
            j = fail[j - 1];
        }
    }
    free(fail);
    return cnt;
}
'''

_PY_EDIT_DISTANCE = '''\
def run(a):
    """Levenshtein edit distance between two strings (insert/delete/substitute = cost 1).

    Input packs both strings as code-point sequences: a = [na, A0..A_{na-1}, B0..B_{nb-1}]
    where na = length of the first string, the next na values are string A, the rest are
    string B. Returns the edit distance as an exact non-negative integer (as a float).
    Bottom-up two-row dynamic programming. Fail-soft: returns 0.0 on na < 0 / truncated
    input. NaN-free assumed (== is used to score matches)."""
    if len(a) < 1:
        return 0.0
    na_d = a[0]
    # raw-value guard BEFORE int() = exact C parity (fractional/negative/NaN/oversized header
    # fail-softs identically; no int(nan) crash).
    if not (na_d >= 0.0 and na_d <= 2147483000.0):
        return 0.0
    na = int(na_d)
    if len(a) < 1 + na:
        return 0.0
    sa = a[1:1 + na]
    sb = a[1 + na:]
    nb = len(sb)
    prev = [float(j) for j in range(nb + 1)]        # distance from "" to B[:j]
    for i in range(1, na + 1):
        cur = [0.0] * (nb + 1)
        cur[0] = float(i)
        ai = sa[i - 1]
        for j in range(1, nb + 1):
            cost = 0.0 if ai == sb[j - 1] else 1.0
            dele = prev[j] + 1.0
            ins = cur[j - 1] + 1.0
            sub = prev[j - 1] + cost
            mn = dele
            if ins < mn:
                mn = ins
            if sub < mn:
                mn = sub
            cur[j] = mn
        prev = cur
    return prev[nb]
'''

_C_EDIT_DISTANCE = '''\
/* Levenshtein edit distance between two strings, two-row DP.
 * Input a = [na, A(na), B(nb)]; returns the distance as an exact integer double. */
double edit_distance(const double* a, int n_in) {
    if (n_in < 1) return 0.0;
    double na_d = a[0];
    if (!(na_d >= 0.0 && na_d <= 2147483000.0)) return 0.0;
    int na = (int)na_d;
    if ((long long)na + 1 > (long long)n_in) return 0.0;
    const double* sa = a + 1;
    const double* sb = a + 1 + na;
    int nb = n_in - 1 - na;
    double* prev = (double*)malloc((size_t)(nb + 1) * sizeof(double));
    double* cur = (double*)malloc((size_t)(nb + 1) * sizeof(double));
    if (!prev || !cur) { free(prev); free(cur); return 0.0; }
    for (int j = 0; j <= nb; j++) prev[j] = (double)j;
    for (int i = 1; i <= na; i++) {
        cur[0] = (double)i;
        double ai = sa[i - 1];
        for (int j = 1; j <= nb; j++) {
            double cost = (ai == sb[j - 1]) ? 0.0 : 1.0;
            double dele = prev[j] + 1.0;
            double ins = cur[j - 1] + 1.0;
            double sub = prev[j - 1] + cost;
            double mn = dele;
            if (ins < mn) mn = ins;
            if (sub < mn) mn = sub;
            cur[j] = mn;
        }
        double* t = prev; prev = cur; cur = t;      /* row i is now in prev */
    }
    double r = prev[nb];
    free(prev); free(cur);
    return r;
}
'''

_PY_LCS_LENGTH = '''\
def run(a):
    """Length of the longest common subsequence of two strings (not substring).

    Input packs both strings as code-point sequences: a = [na, A0..A_{na-1}, B0..B_{nb-1}]
    (same layout as edit_distance). Returns the LCS length as an exact non-negative integer
    (as a float). Bottom-up two-row DP. Fail-soft: returns 0.0 on na < 0 / truncated input."""
    if len(a) < 1:
        return 0.0
    na_d = a[0]
    # raw-value guard BEFORE int() = exact C parity (fractional/negative/NaN/oversized header
    # fail-softs identically; no int(nan) crash).
    if not (na_d >= 0.0 and na_d <= 2147483000.0):
        return 0.0
    na = int(na_d)
    if len(a) < 1 + na:
        return 0.0
    sa = a[1:1 + na]
    sb = a[1 + na:]
    nb = len(sb)
    prev = [0.0] * (nb + 1)
    for i in range(1, na + 1):
        cur = [0.0] * (nb + 1)
        ai = sa[i - 1]
        for j in range(1, nb + 1):
            if ai == sb[j - 1]:
                cur[j] = prev[j - 1] + 1.0
            else:
                cur[j] = prev[j] if prev[j] >= cur[j - 1] else cur[j - 1]
        prev = cur
    return prev[nb]
'''

_C_LCS_LENGTH = '''\
/* Longest common subsequence length of two strings, two-row DP.
 * Input a = [na, A(na), B(nb)]; returns the LCS length as an exact integer double. */
double lcs_length(const double* a, int n_in) {
    if (n_in < 1) return 0.0;
    double na_d = a[0];
    if (!(na_d >= 0.0 && na_d <= 2147483000.0)) return 0.0;
    int na = (int)na_d;
    if ((long long)na + 1 > (long long)n_in) return 0.0;
    const double* sa = a + 1;
    const double* sb = a + 1 + na;
    int nb = n_in - 1 - na;
    double* prev = (double*)malloc((size_t)(nb + 1) * sizeof(double));
    double* cur = (double*)malloc((size_t)(nb + 1) * sizeof(double));
    if (!prev || !cur) { free(prev); free(cur); return 0.0; }
    for (int j = 0; j <= nb; j++) prev[j] = 0.0;
    for (int i = 1; i <= na; i++) {
        cur[0] = 0.0;
        double ai = sa[i - 1];
        for (int j = 1; j <= nb; j++) {
            if (ai == sb[j - 1]) cur[j] = prev[j - 1] + 1.0;
            else cur[j] = (prev[j] >= cur[j - 1]) ? prev[j] : cur[j - 1];
        }
        double* t = prev; prev = cur; cur = t;
    }
    double r = prev[nb];
    free(prev); free(cur);
    return r;
}
'''


# --------------------------------------------------------------------------- #
# P4 — graph ops. A graph is packed into the input seq: a = [n, m, edge triples...]
# where n = node count (0..n-1), m = edge count, then m * (u, v, w) = (endpoint,
# endpoint, weight); undirected. graph_components counts connected components
# (KIND_REDUCE, exact integer). graph_mst_weight = total minimum-spanning-forest
# weight (KIND_REDUCE; sums edge weights, so tol like the numeric ops). graph_dijkstra
# packs a source too — a = [n, m, src, edges...] — and returns the length-n shortest-
# distance vector (KIND_MAP; -1.0 = unreachable). Node/edge counts get the raw-value
# guard (they bound loops/memory); edge endpoints/weights are assumed finite (module
# NaN-free contract). Deterministic union rule + (weight,index) edge sort + lowest-index
# Dijkstra tie-break => C matches Python bit-for-bit; the independent oracle is
# scipy.sparse.csgraph. See docs/GENERAL_ALGORITHMS.md P4.
# --------------------------------------------------------------------------- #
_PY_GRAPH_COMPONENTS = '''\
def run(a):
    """Number of connected components of an undirected graph a = [n, m, (u,v,w)*m].

    Union-find with path halving. Returns the component count as an exact integer
    (weights ignored). Fail-soft 0.0 on malformed input (n<1 / m<0 / truncated) or an
    out-of-range edge endpoint. Edge endpoints assumed finite (NaN-free contract)."""
    if len(a) < 2:
        return 0.0
    nd = a[0]
    md = a[1]
    if not (nd >= 1.0 and nd <= 2147483000.0):
        return 0.0
    if not (md >= 0.0 and md <= 2147483000.0):
        return 0.0
    n = int(nd)
    m = int(md)
    if len(a) < 2 + 3 * m:
        return 0.0
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]                  # path halving
            x = parent[x]
        return x

    for k in range(m):
        u = int(a[2 + 3 * k])
        v = int(a[2 + 3 * k + 1])
        if u < 0 or u >= n or v < 0 or v >= n:
            return 0.0                                     # bad edge -> fail-soft
        ru = find(u)
        rv = find(v)
        if ru != rv:
            parent[ru] = rv                                # deterministic union (ru -> rv)
    c = 0
    for x in range(n):
        if find(x) == x:
            c = c + 1
    return float(c)
'''

_C_GRAPH_COMPONENTS = '''\
/* Connected-component count of an undirected graph a = [n, m, (u,v,w)*m] (union-find). */
static int _uf_find(int* parent, int x) {
    while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; }
    return x;
}
double graph_components(const double* a, int n_in) {
    if (n_in < 2) return 0.0;
    double nd = a[0], md = a[1];
    if (!(nd >= 1.0 && nd <= 2147483000.0)) return 0.0;
    if (!(md >= 0.0 && md <= 2147483000.0)) return 0.0;
    int n = (int)nd, m = (int)md;
    if ((long long)n_in < 2LL + 3LL * m) return 0.0;
    int* parent = (int*)malloc((size_t)n * sizeof(int));
    if (!parent) return 0.0;
    for (int i = 0; i < n; i++) parent[i] = i;
    for (int k = 0; k < m; k++) {
        int u = (int)a[2 + 3 * k], v = (int)a[2 + 3 * k + 1];
        if (u < 0 || u >= n || v < 0 || v >= n) { free(parent); return 0.0; }
        int ru = _uf_find(parent, u), rv = _uf_find(parent, v);
        if (ru != rv) parent[ru] = rv;
    }
    int c = 0;
    for (int x = 0; x < n; x++) if (_uf_find(parent, x) == x) c++;
    free(parent);
    return (double)c;
}
'''

_PY_GRAPH_MST_WEIGHT = '''\
def run(a):
    """Total weight of the minimum spanning forest of an undirected graph
    a = [n, m, (u,v,w)*m] (Kruskal + union-find). Edges are sorted by (weight, index) so
    the choice is deterministic; a disconnected graph yields the spanning FOREST (sum over
    components). Returns the total as a float. Fail-soft 0.0 on malformed / out-of-range."""
    if len(a) < 2:
        return 0.0
    nd = a[0]
    md = a[1]
    if not (nd >= 1.0 and nd <= 2147483000.0):
        return 0.0
    if not (md >= 0.0 and md <= 2147483000.0):
        return 0.0
    n = int(nd)
    m = int(md)
    if len(a) < 2 + 3 * m:
        return 0.0
    edges = []
    for k in range(m):
        u = int(a[2 + 3 * k])
        v = int(a[2 + 3 * k + 1])
        w = a[2 + 3 * k + 2]
        if u < 0 or u >= n or v < 0 or v >= n:
            return 0.0
        edges.append((w, k, u, v))
    edges.sort(key=lambda e: (e[0], e[1]))             # (weight, index): fully determined order
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    total = 0.0
    for w, _idx, u, v in edges:
        ru = find(u)
        rv = find(v)
        if ru != rv:
            parent[ru] = rv
            total = total + w
    return total
'''

_C_GRAPH_MST_WEIGHT = '''\
/* Minimum-spanning-forest total weight of a = [n, m, (u,v,w)*m] (Kruskal, union-find). */
static int _uf_find(int* parent, int x) {
    while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; }
    return x;
}
typedef struct { double w; int idx; int u; int v; } _MstEdge;
static int _mst_cmp(const void* pa, const void* pb) {
    const _MstEdge* a = (const _MstEdge*)pa;
    const _MstEdge* b = (const _MstEdge*)pb;
    if (a->w < b->w) return -1;
    if (a->w > b->w) return 1;
    return (a->idx < b->idx) ? -1 : (a->idx > b->idx ? 1 : 0);   /* unique idx breaks all ties */
}
double graph_mst_weight(const double* a, int n_in) {
    if (n_in < 2) return 0.0;
    double nd = a[0], md = a[1];
    if (!(nd >= 1.0 && nd <= 2147483000.0)) return 0.0;
    if (!(md >= 0.0 && md <= 2147483000.0)) return 0.0;
    int n = (int)nd, m = (int)md;
    if ((long long)n_in < 2LL + 3LL * m) return 0.0;
    int* parent = (int*)malloc((size_t)n * sizeof(int));
    _MstEdge* edges = (_MstEdge*)malloc((size_t)(m > 0 ? m : 1) * sizeof(_MstEdge));
    if (!parent || !edges) { free(parent); free(edges); return 0.0; }
    for (int i = 0; i < n; i++) parent[i] = i;
    for (int k = 0; k < m; k++) {
        int u = (int)a[2 + 3 * k], v = (int)a[2 + 3 * k + 1];
        if (u < 0 || u >= n || v < 0 || v >= n) { free(parent); free(edges); return 0.0; }
        edges[k].w = a[2 + 3 * k + 2]; edges[k].idx = k; edges[k].u = u; edges[k].v = v;
    }
    if (m > 0) qsort(edges, (size_t)m, sizeof(_MstEdge), _mst_cmp);
    double total = 0.0;
    for (int k = 0; k < m; k++) {
        int ru = _uf_find(parent, edges[k].u), rv = _uf_find(parent, edges[k].v);
        if (ru != rv) { parent[ru] = rv; total = total + edges[k].w; }
    }
    free(parent); free(edges);
    return total;
}
'''

_PY_GRAPH_DIJKSTRA = '''\
def run(a):
    """Single-source shortest distances (Dijkstra) on an undirected non-negative-weight
    graph a = [n, m, src, (u,v,w)*m]. Returns the length-n distance vector (src = 0.0),
    with -1.0 for an unreachable node. Deterministic: settle the reachable unsettled node
    of least distance (lowest index on ties), then relax all incident edges in input order.
    Fail-soft []: malformed / out-of-range src or endpoint / a negative edge weight."""
    if len(a) < 3:
        return []
    nd = a[0]
    md = a[1]
    sd = a[2]
    if not (nd >= 1.0 and nd <= 2147483000.0):
        return []
    if not (md >= 0.0 and md <= 2147483000.0):
        return []
    n = int(nd)
    m = int(md)
    if not (sd >= 0.0 and sd < n):                     # bound src against the INTEGER n, not
        return []                                      # raw nd: a fractional nd could pass sd<nd
    src = int(sd)                                      # yet give src==n (out-of-range write)
    if len(a) < 3 + 3 * m:
        return []
    for k in range(m):                                 # validate up front
        u = int(a[3 + 3 * k])
        v = int(a[3 + 3 * k + 1])
        w = a[3 + 3 * k + 2]
        if u < 0 or u >= n or v < 0 or v >= n or w < 0.0:
            return []
    dist = [-1.0] * n
    settled = [False] * n
    dist[src] = 0.0
    for _ in range(n):
        best = -1
        bestd = 0.0
        for x in range(n):
            if (not settled[x]) and dist[x] >= 0.0 and (best < 0 or dist[x] < bestd):
                best = x
                bestd = dist[x]
        if best < 0:
            break                                      # remaining nodes unreachable
        settled[best] = True
        du = dist[best]
        for k in range(m):                             # relax edges incident to `best`
            u = int(a[3 + 3 * k])
            v = int(a[3 + 3 * k + 1])
            w = a[3 + 3 * k + 2]
            if u == best and not settled[v]:
                cand = du + w
                if dist[v] < 0.0 or cand < dist[v]:
                    dist[v] = cand
            elif v == best and not settled[u]:
                cand = du + w
                if dist[u] < 0.0 or cand < dist[u]:
                    dist[u] = cand
    return dist
'''

_C_GRAPH_DIJKSTRA = '''\
/* Single-source Dijkstra on a = [n, m, src, (u,v,w)*m]; writes the length-n distance
 * vector to `out` (-1.0 = unreachable) and returns n. Fail-soft 0 on malformed input. */
int graph_dijkstra(const double* a, int n_in, double* out) {
    if (n_in < 3) return 0;
    double nd = a[0], md = a[1], sd = a[2];
    if (!(nd >= 1.0 && nd <= 2147483000.0)) return 0;
    if (!(md >= 0.0 && md <= 2147483000.0)) return 0;
    int n = (int)nd, m = (int)md;
    if (!(sd >= 0.0 && sd < (double)n)) return 0;      /* bound src against int n, not raw nd */
    int src = (int)sd;
    if ((long long)n_in < 3LL + 3LL * m) return 0;
    for (int k = 0; k < m; k++) {                      /* validate up front */
        int u = (int)a[3 + 3 * k], v = (int)a[3 + 3 * k + 1];
        double w = a[3 + 3 * k + 2];
        if (u < 0 || u >= n || v < 0 || v >= n || w < 0.0) return 0;
    }
    if (!out) return n;                                /* size probe: out_len = n (>= input len when sparse) */
    char* settled = (char*)calloc((size_t)n, 1);
    if (!settled) return 0;
    for (int i = 0; i < n; i++) out[i] = -1.0;
    out[src] = 0.0;
    for (int it = 0; it < n; it++) {
        int best = -1; double bestd = 0.0;
        for (int x = 0; x < n; x++)
            if (!settled[x] && out[x] >= 0.0 && (best < 0 || out[x] < bestd)) { best = x; bestd = out[x]; }
        if (best < 0) break;
        settled[best] = 1;
        double du = out[best];
        for (int k = 0; k < m; k++) {
            int u = (int)a[3 + 3 * k], v = (int)a[3 + 3 * k + 1];
            double w = a[3 + 3 * k + 2];
            if (u == best && !settled[v]) {
                double cand = du + w;
                if (out[v] < 0.0 || cand < out[v]) out[v] = cand;
            } else if (v == best && !settled[u]) {
                double cand = du + w;
                if (out[u] < 0.0 || cand < out[u]) out[u] = cand;
            }
        }
    }
    free(settled);
    return n;
}
'''


# --------------------------------------------------------------------------- #
# P5 — number theory, compression, hashing (educational; honest disclosure). Each
# value is an integer carried as float64: exact while < 2^53, so these ride the same
# binary harness with NO new wire type. Integer/bit work is done in C on unsigned/
# long-long types (the double is cast in, the integer result cast back), so the
# raw-value guard MUST run BEFORE the int cast in BOTH Python and C (a fractional /
# NaN / out-of-range value fail-softs identically — the P3 bug class). Every P5 op is
# EXACT: C == Python bit-for-bit AND Python == an independent oracle with tol 0.
#
# gcd_seq / pow_mod / crc32 fold to one integer (KIND_REDUCE); sieve_primes /
# rle_encode produce a VARIABLE-LENGTH seq whose length can EXCEED the input length
# (KIND_MAP, two-phase size-probe). Honest scope: full crypto (RSA/AES/SHA) needs
# big-integer / large-state that does not fit the float64 seq harness, so this tier
# ships the *primitives* (modular exponentiation, a CRC checksum) with the algorithm
# disclosed, not a cipher. See docs/GENERAL_ALGORITHMS.md P5.
# --------------------------------------------------------------------------- #
_PY_GCD_SEQ = '''\
def run(a):
    """Greatest common divisor of a sequence of non-negative integers (Euclid).

    Folds the Euclidean algorithm across the sequence: gcd(gcd(...gcd(a0,a1)...),a_{k-1}).
    Empty -> 0.0; gcd(0,0) = 0. Returns the gcd as an exact integer double. Fail-soft 0.0 if
    any value is negative, non-integer, or > 2^53 (outside the exact-in-float64 / uint64 range
    the C mirror supports). NaN-free assumed (a NaN fails the >= guard, so it fail-softs)."""
    g = 0
    for x in a:
        # raw-value guard BEFORE int() so Python matches the C guard EXACTLY. The integrality
        # check (x == float(int(x))) is short-circuited AFTER the range check, so int()/the C
        # cast is only reached for a finite in-range x (a NaN / oversized value fail-softs first
        # via >= / <=, never crashing int(nan) or hitting the C (long long)nan UB).
        if not (x >= 0.0 and x <= 9007199254740992.0 and x == float(int(x))):   # 2^53, integer
            return 0.0
        v = int(x)
        while v != 0:                                       # Euclid: gcd(g, v)
            g, v = v, g % v
    return float(g)
'''

_C_GCD_SEQ = '''\
/* GCD of a sequence of non-negative integers (Euclid), folded left to right. */
double gcd_seq(const double* a, int n) {
    unsigned long long g = 0;
    for (int i = 0; i < n; i++) {
        double x = a[i];
        /* range check first, then integrality: under IEEE semantics (long long)x is only reached
         * for a finite in-range x (short-circuit), so NaN / oversized values fail-soft without UB.
         * (-ffast-math would elide the NaN comparison; the codegen #error blocks that build.) */
        if (!(x >= 0.0 && x <= 9007199254740992.0 && x == (double)(long long)x)) return 0.0;
        unsigned long long v = (unsigned long long)x;
        while (v != 0ULL) { unsigned long long t = g % v; g = v; v = t; }
    }
    return (double)g;
}
'''

_PY_SIEVE_PRIMES = '''\
def run(a):
    """Primes <= n by the Sieve of Eratosthenes. Input a = [n]; returns the ascending list
    of primes in [2, n] — a VARIABLE-LENGTH output that can FAR EXCEED the input length (1).

    Fail-soft [] on malformed input (empty), n < 2 (no primes), or n out of range: n is capped
    at 5,000,000 to bound the sieve memory (disclosed). The raw-value guard runs before int()."""
    if len(a) < 1:
        return []
    nd = a[0]
    if not (nd >= 0.0 and nd <= 5000000.0):                 # memory cap; NaN-false
        return []
    n = int(nd)
    if n < 2:
        return []
    is_comp = [False] * (n + 1)
    i = 2
    while i * i <= n:
        if not is_comp[i]:
            j = i * i
            while j <= n:
                is_comp[j] = True
                j = j + i
        i = i + 1
    res = []
    for p in range(2, n + 1):
        if not is_comp[p]:
            res.append(float(p))
    return res
'''

_C_SIEVE_PRIMES = '''\
/* Primes <= n (Sieve of Eratosthenes). Input a = [n]; writes the ascending primes to `out`
 * and returns the count. The output can be LARGER than the input length, so the driver calls
 * with out=NULL first to get the upper bound pi(n) <= n/2 + 1. Fail-soft 0 on malformed /
 * n < 2 / n > 5,000,000 (memory cap). */
int sieve_primes(const double* a, int n_in, double* out) {
    if (n_in < 1) return 0;
    double nd = a[0];
    if (!(nd >= 0.0 && nd <= 5000000.0)) return 0;          /* memory cap; NaN-false */
    int n = (int)nd;
    if (n < 2) return 0;
    if (!out) return n / 2 + 1;                             /* size probe: 2 plus the odds */
    char* is_comp = (char*)calloc((size_t)n + 1, 1);
    if (!is_comp) return 0;
    for (long long i = 2; i * i <= (long long)n; i++) {
        if (!is_comp[i]) {
            for (long long j = i * i; j <= (long long)n; j += i) is_comp[j] = 1;
        }
    }
    int cnt = 0;
    for (int p = 2; p <= n; p++) if (!is_comp[p]) out[cnt++] = (double)p;
    free(is_comp);
    return cnt;
}
'''

_PY_POW_MOD = '''\
def run(a):
    """Modular exponentiation base^exp mod m by right-to-left binary exponentiation
    (square-and-multiply) — the primitive underlying RSA / Diffie-Hellman (educational).

    Input a = [base, exp, mod]; returns (base**exp) mod m as an exact integer double.
    Domain (honest, so the C uint64 mirror never overflows): base, exp in [0, 2^53] and
    mod in [1, 2^32 - 1] — then every intermediate product is < mod^2 < 2^64 and the result
    is < mod < 2^53 (exact in float64). Fail-soft 0.0 on short input or a value outside the
    domain. The raw-value guard runs before int() (exact C parity, no int(nan) crash)."""
    if len(a) < 3:
        return 0.0
    bd = a[0]
    ed = a[1]
    md = a[2]
    # integer values only (short-circuited after each range check for NaN safety).
    if not (bd >= 0.0 and bd <= 9007199254740992.0 and bd == float(int(bd))):        # 2^53
        return 0.0
    if not (ed >= 0.0 and ed <= 9007199254740992.0 and ed == float(int(ed))):
        return 0.0
    if not (md >= 1.0 and md <= 4294967295.0 and md == float(int(md))):   # 2^32-1: mod^2 < 2^64
        return 0.0
    mod = int(md)
    base = int(bd) % mod
    exp = int(ed)
    result = 1 % mod                                        # mod == 1 -> 0
    while exp > 0:
        if exp & 1:
            result = (result * base) % mod
        exp = exp >> 1
        base = (base * base) % mod
    return float(result)
'''

_C_POW_MOD = '''\
/* Modular exponentiation base^exp mod m (right-to-left binary), a = [base, exp, mod].
 * Domain (guarded): base,exp <= 2^53, 1 <= mod <= 2^32-1 so uint64 products never overflow. */
double pow_mod(const double* a, int n) {
    if (n < 3) return 0.0;
    double bd = a[0], ed = a[1], md = a[2];
    /* range check then integrality; under IEEE the short-circuit keeps (long long)x off NaN /
     * oversized x (-ffast-math would elide it — the codegen #error blocks that build). */
    if (!(bd >= 0.0 && bd <= 9007199254740992.0 && bd == (double)(long long)bd)) return 0.0;
    if (!(ed >= 0.0 && ed <= 9007199254740992.0 && ed == (double)(long long)ed)) return 0.0;
    if (!(md >= 1.0 && md <= 4294967295.0 && md == (double)(long long)md)) return 0.0;  /* 2^32-1 */
    unsigned long long mod = (unsigned long long)md;
    unsigned long long base = (unsigned long long)bd % mod;
    unsigned long long exp = (unsigned long long)ed;
    unsigned long long result = 1ULL % mod;                     /* mod == 1 -> 0 */
    while (exp > 0ULL) {
        if (exp & 1ULL) result = (result * base) % mod;
        exp >>= 1;
        base = (base * base) % mod;
    }
    return (double)result;
}
'''

# Named crc32_ieee, not crc32: zlib declares crc32() in <zlib.h>. We never include zlib
# here, so the plain name would compile fine, but the defensive rename (cf. heapsort_asc /
# mergesort_asc vs BSD <stdlib.h>) keeps the emitted C clash-free on any host.
_PY_CRC32 = '''\
def run(a):
    """CRC-32 checksum (IEEE 802.3 / ITU-T V.42: reflected, polynomial 0xEDB88320, init and
    final-xor 0xFFFFFFFF) of a byte sequence — the value zlib.crc32 computes.

    Input a = bytes as integer values in [0, 255]; returns the 32-bit CRC as an exact integer
    double in [0, 2^32 - 1]. Reimplemented bit-by-bit from the spec (not table-copied).
    Fail-soft 0.0 on any value that is not an integer byte in [0, 255]. The Python ints stay
    within 32 bits by construction, mirroring the C uint32 exactly."""
    crc = 0xFFFFFFFF
    for x in a:
        # non-byte (out of range / non-integer / NaN) -> fail-soft, identically to C.
        if not (x >= 0.0 and x <= 255.0 and x == float(int(x))):
            return 0.0
        crc = crc ^ int(x)
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc = crc >> 1
    return float(crc ^ 0xFFFFFFFF)
'''

_C_CRC32 = '''\
/* CRC-32 (IEEE 802.3, reflected, poly 0xEDB88320) of a byte sequence a[0..n-1] in [0,255]. */
double crc32_ieee(const double* a, int n) {
    unsigned int crc = 0xFFFFFFFFu;
    for (int i = 0; i < n; i++) {
        double x = a[i];
        /* not an integer byte in [0,255] -> fail-soft (integrality short-circuited after range;
         * IEEE-only, the codegen #error blocks the -ffast-math build that would elide it). */
        if (!(x >= 0.0 && x <= 255.0 && x == (double)(long long)x)) return 0.0;
        crc ^= (unsigned int)x;
        for (int k = 0; k < 8; k++) {
            if (crc & 1u) crc = (crc >> 1) ^ 0xEDB88320u;
            else crc = crc >> 1;
        }
    }
    return (double)(crc ^ 0xFFFFFFFFu);
}
'''

_PY_RLE_ENCODE = '''\
def run(a):
    """Run-length encode a sequence: maximal runs of consecutive EQUAL values collapse to
    (value, count) pairs. Input a = [v0, v1, ...]; returns [val0, count0, val1, count1, ...]
    (length 2 * number of runs, up to 2 * len(a) when all values differ) — a VARIABLE-LENGTH
    output that can be LARGER than the input. A decodable compression primitive, lossless UP TO
    ==-equality of values: because -0.0 == +0.0, a mixed-sign zero run collapses to whichever sign
    appears first, so the decode is not bit-exact across signed zeros (NaN-free contract assumed).

    Values are compared with == (NaN-free contract); counts are exact integers. Empty -> [].
    Fail-soft [] if len(a) > 2^30 - 1 (so 2 * len fits int32 in the C mirror's size probe)."""
    if len(a) < 1 or len(a) > 1073741823:                   # 2^30 - 1: 2*n stays within int32
        return []
    res = []
    cur = a[0]
    cnt = 1
    for i in range(1, len(a)):
        if a[i] == cur:
            cnt = cnt + 1
        else:
            res.append(cur)
            res.append(float(cnt))
            cur = a[i]
            cnt = 1
    res.append(cur)
    res.append(float(cnt))
    return res
'''

_C_RLE_ENCODE = '''\
/* Run-length encode a[0..n-1] -> [val, count, val, count, ...]. Output can be up to 2n (all
 * distinct), so the driver size-probes (out=NULL -> 2*n) then allocates. Fail-soft 0 on empty
 * or n > 2^30-1 (keeps 2*n within int32). Counts fit int32 (<= n), exact in float64. */
int rle_encode(const double* a, int n, double* out) {
    if (n < 1 || n > 1073741823) return 0;                  /* 2^30 - 1 */
    if (!out) return 2 * n;                                 /* size probe: at most 2 per input */
    int cnt_out = 0;
    double cur = a[0];
    long long run = 1;
    for (int i = 1; i < n; i++) {
        if (a[i] == cur) run++;
        else {
            out[cnt_out++] = cur;
            out[cnt_out++] = (double)run;
            cur = a[i];
            run = 1;
        }
    }
    out[cnt_out++] = cur;
    out[cnt_out++] = (double)run;
    return cnt_out;
}
'''


# --------------------------------------------------------------------------- #
# P6 — computational geometry (bridges to the image tier's contour / region work).
# 2-D points are packed into the input seq; INTEGER coordinates (each in [-100000,
# 100000]) keep every cross product / shoelace sum an EXACT integer < 2^53, so C ==
# Python bit-for-bit AND Python == an independent oracle with tol 0 — no floating
# division anywhere (that would break bit-identity). Orientation / crossing tests use
# integer cross products. A query point exactly on a polygon edge/vertex is left
# implementation-defined and excluded by contract (a boundary point has no crossing-vs-
# winding agreement); the honest gate's holdout only uses strict interior/exterior
# points. See docs/GENERAL_ALGORITHMS.md P6.
# --------------------------------------------------------------------------- #
_PY_POLYGON_AREA2 = '''\
def run(a):
    """Twice the SIGNED area of a polygon by the shoelace formula. Input packs the vertices in
    order: a = [n, x0, y0, x1, y1, ..., x_{n-1}, y_{n-1}] (n >= 3). Returns 2 * signed area — the
    sign is positive for a counter-clockwise vertex order, negative for clockwise (so the winding
    is recoverable) — as an EXACT integer double for integer coordinates.

    Fail-soft 0.0 on malformed input, n < 3, or a coordinate outside [-100000, 100000] / non-integer
    (the bound keeps the accumulated cross-product sum < 2^53, so the result is exact in float64)."""
    if len(a) < 1:
        return 0.0
    nd = a[0]
    if not (nd >= 3.0 and nd <= 100000.0 and nd == float(int(nd))):
        return 0.0
    n = int(nd)
    if len(a) < 1 + 2 * n:
        return 0.0
    for i in range(2 * n):                              # integer, bounded coordinate guard
        c = a[1 + i]
        if not (c >= -100000.0 and c <= 100000.0 and c == float(int(c))):
            return 0.0
    s = 0
    for i in range(n):
        x1 = int(a[1 + 2 * i]); y1 = int(a[1 + 2 * i + 1])
        j = 0 if i + 1 == n else i + 1
        x2 = int(a[1 + 2 * j]); y2 = int(a[1 + 2 * j + 1])
        s = s + x1 * y2 - x2 * y1
    return float(s)
'''

_C_POLYGON_AREA2 = '''\
/* Twice the signed area of a polygon a = [n, x0,y0,...] by the shoelace formula (integer coords
 * in [-100000,100000]; the sum stays < 2^53, exact). Fail-soft 0.0 on malformed / out-of-domain. */
double polygon_area2(const double* a, int n_in) {
    if (n_in < 1) return 0.0;
    double nd = a[0];
    if (!(nd >= 3.0 && nd <= 100000.0 && nd == (double)(long long)nd)) return 0.0;
    int n = (int)nd;
    if ((long long)n_in < 1LL + 2LL * n) return 0.0;
    for (int i = 0; i < 2 * n; i++) {
        double c = a[1 + i];
        if (!(c >= -100000.0 && c <= 100000.0 && c == (double)(long long)c)) return 0.0;
    }
    long long s = 0;
    for (int i = 0; i < n; i++) {
        long long x1 = (long long)a[1 + 2 * i], y1 = (long long)a[1 + 2 * i + 1];
        int j = (i + 1 == n) ? 0 : i + 1;
        long long x2 = (long long)a[1 + 2 * j], y2 = (long long)a[1 + 2 * j + 1];
        s += x1 * y2 - x2 * y1;
    }
    return (double)s;
}
'''

_PY_POINT_IN_POLYGON = '''\
def run(a):
    """Point-in-polygon test by crossing number (ray casting). Input packs the query point and the
    simple polygon: a = [px, py, n, x0, y0, x1, y1, ..., x_{n-1}, y_{n-1}] (n >= 3). Returns 1.0 if
    (px, py) is strictly INSIDE, 0.0 if outside. INTEGER coordinates in [-100000, 100000]; a point
    exactly ON an edge/vertex is implementation-defined and excluded by contract. No floating
    division (an integer cross product decides each crossing), so C == Python bit-for-bit.

    Fail-soft 0.0 on malformed input, n < 3, or an out-of-domain / non-integer coordinate."""
    if len(a) < 3:
        return 0.0
    pxd = a[0]; pyd = a[1]; nd = a[2]
    if not (pxd >= -100000.0 and pxd <= 100000.0 and pxd == float(int(pxd))):
        return 0.0
    if not (pyd >= -100000.0 and pyd <= 100000.0 and pyd == float(int(pyd))):
        return 0.0
    if not (nd >= 3.0 and nd <= 100000.0 and nd == float(int(nd))):
        return 0.0
    n = int(nd)
    if len(a) < 3 + 2 * n:
        return 0.0
    for i in range(2 * n):
        c = a[3 + i]
        if not (c >= -100000.0 and c <= 100000.0 and c == float(int(c))):
            return 0.0
    px = int(pxd); py = int(pyd)
    inside = False
    for i in range(n):
        x1 = int(a[3 + 2 * i]); y1 = int(a[3 + 2 * i + 1])
        j = 0 if i + 1 == n else i + 1
        x2 = int(a[3 + 2 * j]); y2 = int(a[3 + 2 * j + 1])
        if (y1 > py) != (y2 > py):                     # edge straddles the horizontal ray at py
            dy = y2 - y1
            cross = (x2 - x1) * (py - y1) - (px - x1) * dy    # integer, no division
            if (dy > 0 and cross > 0) or (dy < 0 and cross < 0):
                inside = not inside                    # ray crosses this edge to the right of px
    return 1.0 if inside else 0.0
'''

_C_POINT_IN_POLYGON = '''\
/* Point-in-polygon by crossing number (integer coords in [-100000,100000], no division).
 * a = [px, py, n, x0,y0,...]; returns 1.0 inside / 0.0 outside. Fail-soft 0.0 on malformed. */
double point_in_polygon(const double* a, int n_in) {
    if (n_in < 3) return 0.0;
    double pxd = a[0], pyd = a[1], nd = a[2];
    if (!(pxd >= -100000.0 && pxd <= 100000.0 && pxd == (double)(long long)pxd)) return 0.0;
    if (!(pyd >= -100000.0 && pyd <= 100000.0 && pyd == (double)(long long)pyd)) return 0.0;
    if (!(nd >= 3.0 && nd <= 100000.0 && nd == (double)(long long)nd)) return 0.0;
    int n = (int)nd;
    if ((long long)n_in < 3LL + 2LL * n) return 0.0;
    for (int i = 0; i < 2 * n; i++) {
        double c = a[3 + i];
        if (!(c >= -100000.0 && c <= 100000.0 && c == (double)(long long)c)) return 0.0;
    }
    long long px = (long long)pxd, py = (long long)pyd;
    int inside = 0;
    for (int i = 0; i < n; i++) {
        long long x1 = (long long)a[3 + 2 * i], y1 = (long long)a[3 + 2 * i + 1];
        int j = (i + 1 == n) ? 0 : i + 1;
        long long x2 = (long long)a[3 + 2 * j], y2 = (long long)a[3 + 2 * j + 1];
        if ((y1 > py) != (y2 > py)) {
            long long dy = y2 - y1;
            long long cross = (x2 - x1) * (py - y1) - (px - x1) * dy;
            if ((dy > 0 && cross > 0) || (dy < 0 && cross < 0)) inside = !inside;
        }
    }
    return inside ? 1.0 : 0.0;
}
'''


_PY_CONVEX_HULL = '''\
def run(a):
    """Convex hull of a 2-D integer point set (Andrew's monotone chain). Input packs the points:
    a = [n, x0, y0, x1, y1, ..., x_{n-1}, y_{n-1}] (n points). Returns the hull vertices as
    [hx0, hy0, hx1, hy1, ...] in COUNTER-CLOCKWISE order starting from the lexicographically smallest
    vertex (min x, then min y) — a VARIABLE-LENGTH output. Collinear points on a hull edge are
    EXCLUDED (strict hull: only true corners). Integer coordinates in [-100000, 100000] make every
    orientation test an exact integer cross product, so C == Python bit-for-bit.

    Fail-soft [] if malformed / out-of-domain, or the point set is DEGENERATE (fewer than 3 distinct
    points, or all points collinear — no 2-D hull)."""
    if len(a) < 1:
        return []
    nd = a[0]
    if not (nd >= 3.0 and nd <= 100000.0 and nd == float(int(nd))):
        return []
    n = int(nd)
    if len(a) < 1 + 2 * n:
        return []
    for i in range(2 * n):
        c = a[1 + i]
        if not (c >= -100000.0 and c <= 100000.0 and c == float(int(c))):
            return []
    pts = sorted({(int(a[1 + 2 * i]), int(a[1 + 2 * i + 1])) for i in range(n)})   # unique, lex order
    m = len(pts)
    if m < 3:
        return []                                       # fewer than 3 distinct points -> degenerate

    def cross(o, p, q):                                 # >0 left turn, <0 right, 0 collinear
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:   # <=0: drop collinear too
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]                       # drop the shared endpoints (CCW from lex-min)
    if len(hull) < 3:
        return []                                       # all points collinear -> degenerate
    res = []
    for (x, y) in hull:
        res.append(float(x))
        res.append(float(y))
    return res
'''

_C_CONVEX_HULL = '''\
/* Convex hull of a 2-D integer point set (Andrew's monotone chain). a = [n, x0,y0,...]; writes the
 * hull vertices [hx,hy,...] CCW from the lex-min vertex to `out` and returns the count (2 per vertex).
 * Collinear edge points excluded. Fail-soft 0 on malformed / out-of-domain / degenerate. Integer
 * coords in [-100000,100000] -> exact cross products, bit-identical to Python. */
typedef struct { long long x, y; } _HullPt;
static int _hull_cmp(const void* pa, const void* pb) {
    const _HullPt* a = (const _HullPt*)pa;
    const _HullPt* b = (const _HullPt*)pb;
    if (a->x < b->x) return -1; if (a->x > b->x) return 1;
    if (a->y < b->y) return -1; if (a->y > b->y) return 1;
    return 0;
}
static long long _hull_cross(_HullPt o, _HullPt p, _HullPt q) {
    return (p.x - o.x) * (q.y - o.y) - (p.y - o.y) * (q.x - o.x);
}
int convex_hull(const double* a, int n_in, double* out) {
    if (n_in < 1) return 0;
    double nd = a[0];
    if (!(nd >= 3.0 && nd <= 100000.0 && nd == (double)(long long)nd)) return 0;
    int n = (int)nd;
    if ((long long)n_in < 1LL + 2LL * n) return 0;
    for (int i = 0; i < 2 * n; i++) {
        double c = a[1 + i];
        if (!(c >= -100000.0 && c <= 100000.0 && c == (double)(long long)c)) return 0;
    }
    if (!out) return 2 * n;                             /* size probe: hull has <= n vertices */
    _HullPt* pts = (_HullPt*)malloc((size_t)n * sizeof(_HullPt));
    if (!pts) return 0;
    for (int i = 0; i < n; i++) { pts[i].x = (long long)a[1 + 2 * i]; pts[i].y = (long long)a[1 + 2 * i + 1]; }
    qsort(pts, (size_t)n, sizeof(_HullPt), _hull_cmp);
    /* dedup adjacent points so this list == Python's sorted(set(pts)) (keeping the two backends in
     * lockstep for bit-parity). This is also defensive redundancy: the strict <=0 monotone-chain pop
     * below already eliminates duplicate/collinear points, and the hv<3 post-check catches residual
     * degeneracy — so dropping the dedup on BOTH sides is a proven-equivalent no-op (review, 200k cases). */
    int m = 0;
    for (int i = 0; i < n; i++)
        if (m == 0 || pts[i].x != pts[m - 1].x || pts[i].y != pts[m - 1].y) pts[m++] = pts[i];
    if (m < 3) { free(pts); return 0; }
    _HullPt* h = (_HullPt*)malloc((size_t)(2 * m) * sizeof(_HullPt));   /* lower+upper <= 2m */
    if (!h) { free(pts); return 0; }
    int k = 0;
    for (int i = 0; i < m; i++) {                       /* lower hull */
        while (k >= 2 && _hull_cross(h[k - 2], h[k - 1], pts[i]) <= 0) k--;
        h[k++] = pts[i];
    }
    int lower_k = k + 1;
    for (int i = m - 2; i >= 0; i--) {                  /* upper hull */
        while (k >= lower_k && _hull_cross(h[k - 2], h[k - 1], pts[i]) <= 0) k--;
        h[k++] = pts[i];
    }
    int hv = k - 1;                                     /* drop the repeated first point */
    if (hv < 3) { free(pts); free(h); return 0; }
    for (int i = 0; i < hv; i++) { out[2 * i] = (double)h[i].x; out[2 * i + 1] = (double)h[i].y; }
    free(pts); free(h);
    return 2 * hv;
}
'''


_PY_SEGMENTS_INTERSECT = '''\
def run(a):
    """Do two closed line segments intersect (share at least one point)? Input packs both segments:
    a = [x1, y1, x2, y2, x3, y3, x4, y4] — segment A = (x1,y1)-(x2,y2), segment B = (x3,y3)-(x4,y4).
    Returns 1.0 if they intersect (a proper crossing, an endpoint touch, or a collinear overlap), else
    0.0. INTEGER coordinates in [-100000, 100000] make every orientation an exact integer cross product,
    so C == Python bit-for-bit. Fail-soft 0.0 on malformed / out-of-domain input (CLRS 33.1)."""
    if len(a) < 8:
        return 0.0
    for i in range(8):
        c = a[i]
        if not (c >= -100000.0 and c <= 100000.0 and c == float(int(c))):
            return 0.0
    x1 = int(a[0]); y1 = int(a[1]); x2 = int(a[2]); y2 = int(a[3])
    x3 = int(a[4]); y3 = int(a[5]); x4 = int(a[6]); y4 = int(a[7])

    def orient(ax, ay, bx, by, cx, cy):                 # sign of cross((b-a),(c-a)): -1/0/1
        v = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        return 0 if v == 0 else (1 if v > 0 else -1)

    def on_seg(ax, ay, bx, by, px, py):                 # (px,py) known collinear: is it on [a,b]?
        return (min(ax, bx) <= px <= max(ax, bx)) and (min(ay, by) <= py <= max(ay, by))

    d1 = orient(x3, y3, x4, y4, x1, y1)
    d2 = orient(x3, y3, x4, y4, x2, y2)
    d3 = orient(x1, y1, x2, y2, x3, y3)
    d4 = orient(x1, y1, x2, y2, x4, y4)
    # proper crossing: each segment's endpoints strictly straddle the other's line
    if ((d1 > 0) != (d2 > 0)) and d1 != 0 and d2 != 0 and \\
       ((d3 > 0) != (d4 > 0)) and d3 != 0 and d4 != 0:
        return 1.0
    if d1 == 0 and on_seg(x3, y3, x4, y4, x1, y1):      # collinear / endpoint-touch special cases
        return 1.0
    if d2 == 0 and on_seg(x3, y3, x4, y4, x2, y2):
        return 1.0
    if d3 == 0 and on_seg(x1, y1, x2, y2, x3, y3):
        return 1.0
    if d4 == 0 and on_seg(x1, y1, x2, y2, x4, y4):
        return 1.0
    return 0.0
'''

_C_SEGMENTS_INTERSECT = '''\
/* Do two closed segments a = [x1,y1,x2,y2,x3,y3,x4,y4] intersect? 1.0 yes / 0.0 no (CLRS 33.1;
 * integer coords in [-100000,100000], exact orientation cross products). Fail-soft 0.0 on malformed. */
static int _seg_orient(long long ax, long long ay, long long bx, long long by,
                       long long cx, long long cy) {
    long long v = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
    return (v == 0) ? 0 : (v > 0 ? 1 : -1);
}
static int _seg_on(long long ax, long long ay, long long bx, long long by,
                   long long px, long long py) {
    long long minx = ax < bx ? ax : bx, maxx = ax < bx ? bx : ax;
    long long miny = ay < by ? ay : by, maxy = ay < by ? by : ay;
    return (minx <= px && px <= maxx && miny <= py && py <= maxy);
}
double segments_intersect(const double* a, int n_in) {
    if (n_in < 8) return 0.0;
    for (int i = 0; i < 8; i++) {
        double c = a[i];
        if (!(c >= -100000.0 && c <= 100000.0 && c == (double)(long long)c)) return 0.0;
    }
    long long x1=(long long)a[0], y1=(long long)a[1], x2=(long long)a[2], y2=(long long)a[3];
    long long x3=(long long)a[4], y3=(long long)a[5], x4=(long long)a[6], y4=(long long)a[7];
    int d1 = _seg_orient(x3,y3,x4,y4,x1,y1);
    int d2 = _seg_orient(x3,y3,x4,y4,x2,y2);
    int d3 = _seg_orient(x1,y1,x2,y2,x3,y3);
    int d4 = _seg_orient(x1,y1,x2,y2,x4,y4);
    if (((d1 > 0) != (d2 > 0)) && d1 != 0 && d2 != 0 &&
        ((d3 > 0) != (d4 > 0)) && d3 != 0 && d4 != 0) return 1.0;
    if (d1 == 0 && _seg_on(x3,y3,x4,y4,x1,y1)) return 1.0;
    if (d2 == 0 && _seg_on(x3,y3,x4,y4,x2,y2)) return 1.0;
    if (d3 == 0 && _seg_on(x1,y1,x2,y2,x3,y3)) return 1.0;
    if (d4 == 0 && _seg_on(x1,y1,x2,y2,x4,y4)) return 1.0;
    return 0.0;
}
'''


# --------------------------------------------------------------------------- #
# P8 — search / selection. Comparison-based over arbitrary (NaN-free) doubles: the
# result is an index or an EXISTING element, so it is exact (tol 0) and C == Python
# bit-for-bit. binary_search folds to one index (KIND_REDUCE); kth_smallest folds to
# one value (KIND_REDUCE) and its result — the k-th smallest — is order-independent, so
# the quickselect need not partition in the same order in C and Python to match.
# --------------------------------------------------------------------------- #
_PY_BINARY_SEARCH = '''\
def run(a):
    """Binary search for the FIRST occurrence of a target in a sorted sequence (lower bound). Input
    a = [target, v0, v1, ..., v_{n-1}] where v0..v_{n-1} is sorted ASCENDING. Returns the 0-based index
    of the leftmost element equal to target, or -1.0 if the target is absent. Comparison-based (exact
    for any NaN-free doubles); the index is an exact integer. Empty sequence / missing header -> -1.0.
    Behaviour is bounded-but-unspecified if the sequence is not sorted (a precondition, not checked)."""
    if len(a) < 1:
        return -1.0
    target = a[0]
    v = a[1:]
    n = len(v)
    lo = 0
    hi = n                                              # search the half-open range [lo, hi)
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if v[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    if lo < n and v[lo] == target:
        return float(lo)
    return -1.0
'''

_C_BINARY_SEARCH = '''\
/* Binary search (lower bound) for the first index of target in a = [target, v0..v_{n-1}] (v sorted
 * ascending); returns the index as a double, or -1.0 if absent. Comparison-based, bit-identical. */
double binary_search(const double* a, int n_in) {
    if (n_in < 1) return -1.0;
    double target = a[0];
    const double* v = a + 1;
    int n = n_in - 1;
    int lo = 0, hi = n;                                 /* half-open [lo, hi) */
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (v[mid] < target) lo = mid + 1;
        else hi = mid;
    }
    if (lo < n && v[lo] == target) return (double)lo;
    return -1.0;
}
'''

_PY_KTH_SMALLEST = '''\
def run(a):
    """The k-th smallest element of a sequence (0-indexed order statistic; k=0 -> minimum). Input
    a = [k, v0, v1, ..., v_{n-1}]. Returns the k-th smallest value (an existing element, so exact for
    any NaN-free doubles). Quickselect with a 3-way (Dutch national flag) partition + median-of-three
    pivot, in place on a copy: the equal-to-pivot band collapses runs of duplicates, so all-equal /
    few-distinct inputs stay O(n) (a single-pivot Lomuto quickselect degrades to O(n^2) there — the
    same reason quicksort here uses a 3-way partition). The RESULT is order-independent (the k-th
    smallest is unique by value), so it is bit-identical to the C backend regardless of pivot order.
    Fail-soft 0.0 if k is out of [0, n-1] / non-integer / the sequence is empty (n < 1)."""
    if len(a) < 2:
        return 0.0
    kd = a[0]
    v = list(a[1:])
    n = len(v)
    if not (kd >= 0.0 and kd < float(n) and kd == float(int(kd))):
        return 0.0
    k = int(kd)
    lo = 0
    hi = n - 1
    while lo < hi:
        mid = lo + (hi - lo) // 2                        # median-of-three -> order lo <= mid <= hi
        if v[mid] < v[lo]:
            v[lo], v[mid] = v[mid], v[lo]
        if v[hi] < v[lo]:
            v[lo], v[hi] = v[hi], v[lo]
        if v[hi] < v[mid]:
            v[mid], v[hi] = v[hi], v[mid]
        pivot = v[mid]
        lt = lo
        i = lo
        gt = hi
        while i <= gt:                                   # 3-way (Dutch national flag) partition
            if v[i] < pivot:
                v[lt], v[i] = v[i], v[lt]; lt += 1; i += 1
            elif v[i] > pivot:
                v[i], v[gt] = v[gt], v[i]; gt -= 1
            else:
                i += 1                                   # v[i] == pivot: leave it in the middle band
        # [lo, lt-1] < pivot, [lt, gt] == pivot, [gt+1, hi] > pivot
        if k < lt:
            hi = lt - 1
        elif k > gt:
            lo = gt + 1
        else:
            return float(v[k])                           # k in the equal band -> v[k] == pivot
    return float(v[lo])
'''

_C_KTH_SMALLEST = '''\
/* The k-th smallest element of a = [k, v0..v_{n-1}] (0-indexed; quickselect, median-of-three, 3-way
 * Dutch-flag partition so all-equal/few-distinct stay O(n)). Returns the value; the result is
 * order-independent so it matches Python bit-for-bit. Fail-soft 0.0. */
double kth_smallest(const double* a, int n_in) {
    if (n_in < 2) return 0.0;
    double kd = a[0];
    int n = n_in - 1;
    if (!(kd >= 0.0 && kd < (double)n && kd == (double)(long long)kd)) return 0.0;
    int k = (int)kd;
    double* v = (double*)malloc((size_t)n * sizeof(double));
    if (!v) return 0.0;
    for (int i = 0; i < n; i++) v[i] = a[1 + i];
    int lo = 0, hi = n - 1;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (v[mid] < v[lo]) { double t = v[lo]; v[lo] = v[mid]; v[mid] = t; }
        if (v[hi] < v[lo]) { double t = v[lo]; v[lo] = v[hi]; v[hi] = t; }
        if (v[hi] < v[mid]) { double t = v[mid]; v[mid] = v[hi]; v[hi] = t; }
        double pivot = v[mid];
        int lt = lo, i = lo, gt = hi;
        while (i <= gt) {                                   /* 3-way (Dutch national flag) partition */
            if (v[i] < pivot) { double t = v[lt]; v[lt] = v[i]; v[i] = t; lt++; i++; }
            else if (v[i] > pivot) { double t = v[i]; v[i] = v[gt]; v[gt] = t; gt--; }
            else i++;
        }
        /* [lo,lt-1] < pivot, [lt,gt] == pivot, [gt+1,hi] > pivot */
        if (k < lt) hi = lt - 1;
        else if (k > gt) lo = gt + 1;
        else { double r = v[k]; free(v); return r; }        /* k in the equal band -> v[k] == pivot */
    }
    double r = v[lo];
    free(v);
    return r;
}
'''


# --------------------------------------------------------------------------- #
# P9 — statistics / aggregation. Comparison-based over arbitrary (NaN-free) doubles:
# the result is an exact integer count or an EXISTING element, so exact (tol 0) and
# C == Python bit-for-bit. Both fold to one number (KIND_REDUCE); both sort a copy and
# scan runs, and their result is order-independent so C's qsort need not match Python's.
# --------------------------------------------------------------------------- #
_PY_COUNT_DISTINCT = '''\
def run(a):
    """The number of DISTINCT values in a sequence (exact integer). Values are compared with ==
    (NaN-free contract; -0.0 and +0.0 count as one value, as they compare equal). Empty -> 0.0.
    Sorts a copy and counts values differing from the previous, so the result is order-independent
    and bit-identical to the C backend."""
    n = len(a)
    if n == 0:
        return 0.0
    v = sorted(a)
    c = 1
    for i in range(1, n):
        if v[i] != v[i - 1]:
            c = c + 1
    return float(c)
'''

_C_COUNT_DISTINCT = '''\
/* Number of distinct values in a[0..n-1] (sort a copy, count adjacent-distinct). Order-independent
 * result, bit-identical to Python. Empty -> 0.0. */
static int _cd_cmp(const void* pa, const void* pb) {
    double a = *(const double*)pa, b = *(const double*)pb;
    return (a < b) ? -1 : (a > b ? 1 : 0);
}
double count_distinct(const double* a, int n) {
    if (n <= 0) return 0.0;
    double* v = (double*)malloc((size_t)n * sizeof(double));
    if (!v) return 0.0;
    for (int i = 0; i < n; i++) v[i] = a[i];
    qsort(v, (size_t)n, sizeof(double), _cd_cmp);
    int c = 1;
    for (int i = 1; i < n; i++) if (v[i] != v[i - 1]) c++;
    free(v);
    return (double)c;
}
'''

_PY_MODE_VALUE = '''\
def run(a):
    """The MODE of a sequence: the most frequently occurring value, with the SMALLEST value winning
    ties (deterministic). Returns an existing element (exact for any NaN-free doubles). Empty -> 0.0.
    Sorts a copy and scans equal runs; the result (value + tie rule) is order-independent, so it is
    bit-identical to the C backend. A ZERO mode is canonicalized to +0.0 (adding 0.0 maps -0.0 -> +0.0
    and is a no-op for every other value) so the sign is not left to the sort's handling of -0.0 == +0.0."""
    n = len(a)
    if n == 0:
        return 0.0
    v = sorted(a)                                       # ascending -> the first max-run is the smallest
    best_val = v[0]
    best_cnt = 1
    cur_cnt = 1
    for i in range(1, n):
        if v[i] == v[i - 1]:
            cur_cnt = cur_cnt + 1
        else:
            cur_cnt = 1
        if cur_cnt > best_cnt:                          # strictly greater -> earliest (smallest) wins ties
            best_cnt = cur_cnt
            best_val = v[i]
    return float(best_val) + 0.0                        # canonicalize -0.0 -> +0.0 (see docstring)
'''

_C_MODE_VALUE = '''\
/* Mode of a[0..n-1] (most frequent; smallest value wins ties). Sort a copy ascending, scan equal runs,
 * keep the first (smallest) value reaching the max run length. Order-independent, bit-identical. */
static int _mode_cmp(const void* pa, const void* pb) {
    double a = *(const double*)pa, b = *(const double*)pb;
    return (a < b) ? -1 : (a > b ? 1 : 0);
}
double mode_value(const double* a, int n) {
    if (n <= 0) return 0.0;
    double* v = (double*)malloc((size_t)n * sizeof(double));
    if (!v) return 0.0;
    for (int i = 0; i < n; i++) v[i] = a[i];
    qsort(v, (size_t)n, sizeof(double), _mode_cmp);
    double best_val = v[0];
    int best_cnt = 1, cur_cnt = 1;
    for (int i = 1; i < n; i++) {
        if (v[i] == v[i - 1]) cur_cnt++;
        else cur_cnt = 1;
        if (cur_cnt > best_cnt) { best_cnt = cur_cnt; best_val = v[i]; }
    }
    double r = best_val + 0.0;      /* canonicalize -0.0 -> +0.0 so the sign is not qsort-dependent */
    free(v);
    return r;
}
'''


# --------------------------------------------------------------------------- #
# P10 — number theory (part 2): primality and modular inverse, building on the P5
# integer machinery. Integers ride float64 (exact < 2^53); the honest domains keep
# every modular product within uint64 in the C mirror, so C == Python bit-for-bit and
# Python == an independent oracle (sympy.isprime / builtin pow(a,-1,m)). Both fold to
# one value (KIND_REDUCE). See docs/GENERAL_ALGORITHMS.md P10.
# --------------------------------------------------------------------------- #
_PY_IS_PRIME = '''\
def run(a):
    """Primality test by deterministic Miller-Rabin. Input a = [n]; returns 1.0 if n is prime, 0.0
    otherwise. Domain (honest): 0 <= n <= 2^32 - 1 (integer) so the modular squarings a*a mod n fit
    uint64 in the C mirror and the witness set {2,3,5,7,11,13,17,19,23,29,31,37} is DETERMINISTIC
    (it certifies primality for every n < 3.3e24, far past the domain). n < 2 and out-of-domain -> 0.0."""
    if len(a) < 1:
        return 0.0
    nd = a[0]
    if not (nd >= 0.0 and nd <= 4294967295.0 and nd == float(int(nd))):   # 2^32 - 1
        return 0.0
    n = int(nd)
    if n < 2:
        return 0.0
    witnesses = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in witnesses:
        if n == p:
            return 1.0
        if n % p == 0:
            return 0.0                                  # a small prime divides n (and n > p)
    d = n - 1                                           # write n-1 = d * 2^s with d odd
    s = 0
    while d % 2 == 0:
        d = d // 2
        s = s + 1
    for w in witnesses:
        x = pow(w, d, n)                                # w^d mod n (square-and-multiply)
        if x == 1 or x == n - 1:
            continue
        composite = True
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                composite = False
                break
        if composite:
            return 0.0                                  # w is a witness to compositeness
    return 1.0
'''

_C_IS_PRIME = '''\
/* Deterministic Miller-Rabin primality of a = [n] (0 <= n <= 2^32-1). 1.0 prime / 0.0 not.
 * Domain keeps a*a mod n within uint64 (n <= 2^32-1 -> n^2 < 2^64). Fail-soft 0.0. */
static unsigned long long _mr_powmod(unsigned long long b, unsigned long long e, unsigned long long m) {
    unsigned long long r = 1ULL % m;
    b %= m;
    while (e > 0ULL) {
        if (e & 1ULL) r = (r * b) % m;
        e >>= 1;
        b = (b * b) % m;
    }
    return r;
}
double is_prime(const double* a, int n_in) {
    if (n_in < 1) return 0.0;
    double nd = a[0];
    if (!(nd >= 0.0 && nd <= 4294967295.0 && nd == (double)(long long)nd)) return 0.0;
    unsigned long long n = (unsigned long long)nd;
    if (n < 2ULL) return 0.0;
    static const unsigned long long W[12] = {2,3,5,7,11,13,17,19,23,29,31,37};
    for (int i = 0; i < 12; i++) {
        if (n == W[i]) return 1.0;
        if (n % W[i] == 0ULL) return 0.0;
    }
    unsigned long long d = n - 1;
    int s = 0;
    while (d % 2ULL == 0ULL) { d /= 2ULL; s++; }
    for (int i = 0; i < 12; i++) {
        unsigned long long x = _mr_powmod(W[i], d, n);
        if (x == 1ULL || x == n - 1) continue;
        int composite = 1;
        for (int r = 0; r < s - 1; r++) {
            x = (x * x) % n;
            if (x == n - 1) { composite = 0; break; }
        }
        if (composite) return 0.0;
    }
    return 1.0;
}
'''

_PY_MODULAR_INVERSE = '''\
def run(a):
    """Modular inverse a^-1 mod m by the extended Euclidean algorithm. Input a = [a_val, m]; returns
    the inverse in [0, m-1] with a_val * inv == 1 (mod m) if gcd(a_val, m) == 1, else -1.0 (no inverse).
    Domain: 0 <= a_val <= 2^53, 1 <= m <= 2^53 (integers); the Bezout coefficients stay exact. m == 1 ->
    0.0 (every residue is 0 mod 1). Fail-soft -1.0 on malformed / out-of-domain input."""
    if len(a) < 2:
        return -1.0
    ad = a[0]
    md = a[1]
    if not (ad >= 0.0 and ad <= 9007199254740992.0 and ad == float(int(ad))):
        return -1.0
    if not (md >= 1.0 and md <= 9007199254740992.0 and md == float(int(md))):
        return -1.0
    m = int(md)
    if m == 1:
        return 0.0
    a_val = int(ad) % m
    old_r, r = a_val, m                                 # extended Euclid on (a_val, m)
    old_s, s = 1, 0
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
    if old_r != 1:
        return -1.0                                     # gcd(a_val, m) != 1 -> no inverse
    return float(old_s % m)                             # normalize to [0, m-1] (Python floor mod)
'''

_C_MODULAR_INVERSE = '''\
/* Modular inverse a_val^-1 mod m of a = [a_val, m] by the extended Euclidean algorithm.
 * Returns the inverse in [0, m-1], or -1.0 if gcd != 1. Domain: a_val,m in [0, 2^53] / [1, 2^53]
 * (Bezout coefficients fit long long). Fail-soft -1.0. */
double modular_inverse(const double* a, int n_in) {
    if (n_in < 2) return -1.0;
    double ad = a[0], md = a[1];
    if (!(ad >= 0.0 && ad <= 9007199254740992.0 && ad == (double)(long long)ad)) return -1.0;
    if (!(md >= 1.0 && md <= 9007199254740992.0 && md == (double)(long long)md)) return -1.0;
    long long m = (long long)md;
    if (m == 1) return 0.0;
    long long a_val = (long long)ad % m;
    long long old_r = a_val, r = m;
    long long old_s = 1, s = 0;
    while (r != 0) {
        long long q = old_r / r;
        long long tr = old_r - q * r; old_r = r; r = tr;
        long long ts = old_s - q * s; old_s = s; s = ts;
    }
    if (old_r != 1) return -1.0;
    long long inv = old_s % m;                          /* C truncated mod -> normalize to [0, m-1] */
    if (inv < 0) inv += m;
    return (double)inv;
}
'''


# --------------------------------------------------------------------------- #
# P11 — bit manipulation. Non-negative integers carried as float64; the domain
# [0, 2^53 - 1] keeps every value inside 53 bits, so bitwise XOR stays < 2^53 (exact)
# and popcounts are exact small integers. Bit work is done on uint64 in C (the double
# is cast in, the integer result cast back). Both fold to one integer (KIND_REDUCE).
# See docs/GENERAL_ALGORITHMS.md P11.
# --------------------------------------------------------------------------- #
_PY_XOR_REDUCE = '''\
def run(a):
    """Bitwise XOR of a sequence of non-negative integers (exact). Each value in [0, 2^53 - 1]
    (integer), so every value fits in 53 bits and the XOR result stays < 2^53 (exact in float64).
    Empty -> 0.0. Fail-soft 0.0 if any value is negative / non-integer / >= 2^53. The raw-value +
    integrality guard runs before the int cast (NaN-safe short-circuit; the codegen #errors under
    -ffast-math)."""
    acc = 0
    for x in a:
        if not (x >= 0.0 and x <= 9007199254740991.0 and x == float(int(x))):   # 2^53 - 1
            return 0.0
        acc = acc ^ int(x)
    return float(acc)
'''

_C_XOR_REDUCE = '''\
/* Bitwise XOR of a[0..n-1] (non-negative integers in [0, 2^53-1]). Result < 2^53, exact. Fail-soft
 * 0.0 on a negative / non-integer / >= 2^53 value. */
double xor_reduce(const double* a, int n) {
    unsigned long long acc = 0;
    for (int i = 0; i < n; i++) {
        double x = a[i];
        if (!(x >= 0.0 && x <= 9007199254740991.0 && x == (double)(long long)x)) return 0.0;
        acc ^= (unsigned long long)x;
    }
    return (double)acc;
}
'''

_PY_POPCOUNT_TOTAL = '''\
def run(a):
    """Total number of set (1) bits across a sequence of non-negative integers (exact). Each value in
    [0, 2^53 - 1] (integer). Empty -> 0.0. Fail-soft 0.0 if any value is negative / non-integer /
    >= 2^53. Counts bits by clearing the lowest set bit (Kernighan), so it mirrors the C exactly."""
    total = 0
    for x in a:
        if not (x >= 0.0 and x <= 9007199254740991.0 and x == float(int(x))):
            return 0.0
        v = int(x)
        while v != 0:
            v = v & (v - 1)                             # clear the lowest set bit
            total = total + 1
    return float(total)
'''

_C_POPCOUNT_TOTAL = '''\
/* Total set-bit count across a[0..n-1] (non-negative integers in [0, 2^53-1]), by Kernighan's
 * lowest-set-bit clearing. Result is a small exact integer. Fail-soft 0.0 on out-of-domain. */
double popcount_total(const double* a, int n) {
    unsigned long long total = 0;
    for (int i = 0; i < n; i++) {
        double x = a[i];
        if (!(x >= 0.0 && x <= 9007199254740991.0 && x == (double)(long long)x)) return 0.0;
        unsigned long long v = (unsigned long long)x;
        while (v != 0ULL) { v &= (v - 1ULL); total++; }
    }
    return (double)total;
}
'''


# --------------------------------------------------------------------------- #
# P12 — extended Euclidean algorithm (KIND_MAP, exactly 3 outputs). Builds on the P5
# gcd / P10 modular_inverse machinery. Non-negative integers <= 2^53; the Bezout
# coefficients stay exact (|q*s| = |old_s - new_s| <= 2*max(a,b) <= 2^54, within long
# long), so C == Python bit-for-bit. See docs/GENERAL_ALGORITHMS.md P12.
# --------------------------------------------------------------------------- #
_PY_EXTENDED_GCD = '''\
def run(a):
    """Extended Euclidean algorithm. Input a = [a_val, b_val] (non-negative integers <= 2^53). Returns
    [g, x, y] with a_val * x + b_val * y == g == gcd(a_val, b_val) — a VARIABLE-LENGTH output of exactly
    3 values (or [] fail-soft on malformed / out-of-domain input). Iterative; the Bezout coefficients
    stay exact (|q*s| = |old_s - new_s| <= 2*max(a,b) <= 2^54, within the C long long mirror)."""
    if len(a) < 2:
        return []
    ad = a[0]
    bd = a[1]
    if not (ad >= 0.0 and ad <= 9007199254740992.0 and ad == float(int(ad))):
        return []
    if not (bd >= 0.0 and bd <= 9007199254740992.0 and bd == float(int(bd))):
        return []
    old_r, r = int(ad), int(bd)
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    return [float(old_r), float(old_s), float(old_t)]        # g = old_r, x = old_s, y = old_t
'''

_C_EXTENDED_GCD = '''\
/* Extended Euclidean algorithm of a = [a_val, b_val] -> [g, x, y] with a_val*x + b_val*y = g = gcd.
 * KIND_MAP with a fixed output length of 3. Non-negative integers <= 2^53 (Bezout coefficients fit
 * long long). Fail-soft 0 (empty) on malformed / out-of-domain input. */
int extended_gcd(const double* a, int n_in, double* out) {
    if (n_in < 2) return 0;
    double ad = a[0], bd = a[1];
    if (!(ad >= 0.0 && ad <= 9007199254740992.0 && ad == (double)(long long)ad)) return 0;
    if (!(bd >= 0.0 && bd <= 9007199254740992.0 && bd == (double)(long long)bd)) return 0;
    if (!out) return 3;                                      /* size probe: always 3 outputs */
    long long old_r = (long long)ad, r = (long long)bd;
    long long old_s = 1, s = 0;
    long long old_t = 0, t = 1;
    while (r != 0) {
        long long q = old_r / r;
        long long tr = old_r - q * r; old_r = r; r = tr;
        long long ts = old_s - q * s; old_s = s; s = ts;
        long long tt = old_t - q * t; old_t = t; t = tt;
    }
    out[0] = (double)old_r; out[1] = (double)old_s; out[2] = (double)old_t;
    return 3;
}
'''


ALGO_REGISTRY: list[AlgoOp] = [
    AlgoOp("quicksort", "sort", SEQ, SEQ, KIND_SORT, "quicksort",
           _PY_QUICKSORT, _C_QUICKSORT,
           "Sort a sequence ascending, in place (O(n log n), robust to duplicates).",
           "Hoare 1961 quicksort; 3-way (Dutch national flag) partition; median-of-three pivot"),
    AlgoOp("heapsort", "sort", SEQ, SEQ, KIND_SORT, "heapsort_asc",
           _PY_HEAPSORT, _C_HEAPSORT,
           "Sort a sequence ascending, in place (worst-case O(n log n)).",
           "Williams 1964 heapsort; binary max-heap sift-down"),
    AlgoOp("mergesort", "sort", SEQ, SEQ, KIND_SORT, "mergesort_asc",
           _PY_MERGESORT, _C_MERGESORT,
           "Sort a sequence ascending, stable (O(n log n), O(n) extra).",
           "von Neumann 1945 mergesort; top-down stable merge"),
    AlgoOp("seq_max", "reduce", SEQ, SCALAR, KIND_REDUCE, "seq_max",
           _PY_SEQ_MAX, _C_SEQ_MAX,
           "Maximum element of a sequence (exact, order-independent).",
           "linear scan"),
    AlgoOp("seq_min", "reduce", SEQ, SCALAR, KIND_REDUCE, "seq_min",
           _PY_SEQ_MIN, _C_SEQ_MIN,
           "Minimum element of a sequence (exact, order-independent).",
           "linear scan"),
    AlgoOp("simpson", "numeric", SEQ, SCALAR, KIND_REDUCE, "simpson",
           _PY_SIMPSON, _C_SIMPSON,
           "Definite integral of samples [h, y0..y_{m-1}] by composite Simpson's rule.",
           "Simpson's rule; composite, trapezoid tail for an odd interval", tol=1e-9),
    AlgoOp("bisection", "numeric", SEQ, SCALAR, KIND_REDUCE, "bisection",
           _PY_BISECTION, _C_BISECTION,
           "Root of a polynomial in a bracket [lo,hi,c0..cn] by bisection (100 iters).",
           "bisection method (Bolzano); Horner evaluation", tol=1e-6),
    AlgoOp("newton", "numeric", SEQ, SCALAR, KIND_REDUCE, "newton",
           _PY_NEWTON, _C_NEWTON,
           "Root of a polynomial from x0 [x0,c0..cn] by Newton-Raphson.",
           "Newton-Raphson; simultaneous Horner for p and p'", tol=1e-6),
    AlgoOp("gauss_solve", "numeric", SEQ, SEQ, KIND_MAP, "gauss_solve",
           _PY_GAUSS, _C_GAUSS,
           "Solve a linear system [n, augmented n x (n+1) matrix] by Gaussian "
           "elimination with partial pivoting (variable-length seq -> seq).",
           "Gaussian elimination with partial pivoting; back substitution", tol=1e-9),
    AlgoOp("strfind", "string", SEQ, SEQ, KIND_MAP, "strfind",
           _PY_STRFIND, _C_STRFIND,
           "All start positions of a pattern in a text [m, pattern(m), text] by "
           "Knuth-Morris-Pratt (variable-length seq -> seq of match indices).",
           "Knuth-Morris-Pratt string search; failure-function prefix automaton"),
    AlgoOp("edit_distance", "string", SEQ, SCALAR, KIND_REDUCE, "edit_distance",
           _PY_EDIT_DISTANCE, _C_EDIT_DISTANCE,
           "Levenshtein edit distance between two strings [na, A(na), B] (two-row DP).",
           "Wagner-Fischer / Levenshtein edit distance; two-row dynamic programming"),
    AlgoOp("lcs_length", "string", SEQ, SCALAR, KIND_REDUCE, "lcs_length",
           _PY_LCS_LENGTH, _C_LCS_LENGTH,
           "Longest-common-subsequence length of two strings [na, A(na), B] (two-row DP).",
           "longest common subsequence; two-row dynamic programming"),
    AlgoOp("graph_components", "graph", SEQ, SCALAR, KIND_REDUCE, "graph_components",
           _PY_GRAPH_COMPONENTS, _C_GRAPH_COMPONENTS,
           "Connected-component count of an undirected graph [n, m, (u,v,w)*m] (union-find).",
           "union-find (path halving); connected components"),
    AlgoOp("graph_mst_weight", "graph", SEQ, SCALAR, KIND_REDUCE, "graph_mst_weight",
           _PY_GRAPH_MST_WEIGHT, _C_GRAPH_MST_WEIGHT,
           "Minimum-spanning-forest total weight of [n, m, (u,v,w)*m] (Kruskal).",
           "Kruskal minimum spanning tree; union-find; (weight,index) sort", tol=1e-9),
    AlgoOp("graph_dijkstra", "graph", SEQ, SEQ, KIND_MAP, "graph_dijkstra",
           _PY_GRAPH_DIJKSTRA, _C_GRAPH_DIJKSTRA,
           "Single-source shortest distances of [n, m, src, (u,v,w)*m] (Dijkstra; -1=unreachable).",
           "Dijkstra shortest paths; deterministic settle order", tol=1e-9),
    AlgoOp("gcd_seq", "numtheory", SEQ, SCALAR, KIND_REDUCE, "gcd_seq",
           _PY_GCD_SEQ, _C_GCD_SEQ,
           "Greatest common divisor of a sequence of non-negative integers (Euclid).",
           "Euclidean algorithm (Euclid, Elements VII); folded across the sequence"),
    AlgoOp("sieve_primes", "numtheory", SEQ, SEQ, KIND_MAP, "sieve_primes",
           _PY_SIEVE_PRIMES, _C_SIEVE_PRIMES,
           "Primes <= n by the Sieve of Eratosthenes; input [n] -> ascending primes "
           "(variable-length seq -> seq, output can exceed the input length).",
           "Sieve of Eratosthenes"),
    AlgoOp("pow_mod", "numtheory", SEQ, SCALAR, KIND_REDUCE, "pow_mod",
           _PY_POW_MOD, _C_POW_MOD,
           "Modular exponentiation base^exp mod m of [base, exp, mod] "
           "(the RSA / Diffie-Hellman primitive; educational).",
           "right-to-left binary exponentiation (square-and-multiply)"),
    AlgoOp("crc32", "hash", SEQ, SCALAR, KIND_REDUCE, "crc32_ieee",
           _PY_CRC32, _C_CRC32,
           "CRC-32 checksum (IEEE 802.3, reflected poly 0xEDB88320) of a byte sequence "
           "in [0, 255] (matches zlib.crc32).",
           "CRC-32 (IEEE 802.3 / ITU-T V.42); reflected bit-by-bit, poly 0xEDB88320"),
    AlgoOp("rle_encode", "compress", SEQ, SEQ, KIND_MAP, "rle_encode",
           _PY_RLE_ENCODE, _C_RLE_ENCODE,
           "Run-length encode a sequence -> [value, count, ...] "
           "(variable-length seq -> seq, output up to 2x the input).",
           "run-length encoding (lossless)"),
    AlgoOp("polygon_area2", "geometry", SEQ, SCALAR, KIND_REDUCE, "polygon_area2",
           _PY_POLYGON_AREA2, _C_POLYGON_AREA2,
           "Twice the signed area of a polygon [n, x0,y0,...] by the shoelace formula "
           "(integer coordinates; sign encodes winding).",
           "shoelace / surveyor's formula for polygon area"),
    AlgoOp("point_in_polygon", "geometry", SEQ, SCALAR, KIND_REDUCE, "point_in_polygon",
           _PY_POINT_IN_POLYGON, _C_POINT_IN_POLYGON,
           "Point-in-polygon test of [px, py, n, x0,y0,...] by crossing number "
           "(ray casting; 1.0 inside / 0.0 outside; integer coordinates).",
           "crossing-number / ray-casting point-in-polygon (integer cross products)"),
    AlgoOp("convex_hull", "geometry", SEQ, SEQ, KIND_MAP, "convex_hull",
           _PY_CONVEX_HULL, _C_CONVEX_HULL,
           "Convex hull of a 2-D integer point set [n, x0,y0,...] by Andrew's monotone "
           "chain -> hull vertices CCW from the lex-min vertex (variable-length seq -> seq).",
           "Andrew's monotone-chain convex hull (integer orientation cross products)"),
    AlgoOp("segments_intersect", "geometry", SEQ, SCALAR, KIND_REDUCE, "segments_intersect",
           _PY_SEGMENTS_INTERSECT, _C_SEGMENTS_INTERSECT,
           "Do two closed segments [x1,y1,x2,y2,x3,y3,x4,y4] intersect? "
           "1.0 / 0.0 (orientation test; integer coordinates; handles collinear overlap).",
           "CLRS 33.1 segment-intersection via integer orientation + on-segment tests"),
    AlgoOp("binary_search", "search", SEQ, SCALAR, KIND_REDUCE, "binary_search",
           _PY_BINARY_SEARCH, _C_BINARY_SEARCH,
           "First index of a target in a sorted sequence [target, v0..v_{n-1}] "
           "(lower bound; -1.0 if absent).",
           "binary search / lower bound on a sorted sequence"),
    AlgoOp("kth_smallest", "search", SEQ, SCALAR, KIND_REDUCE, "kth_smallest",
           _PY_KTH_SMALLEST, _C_KTH_SMALLEST,
           "The k-th smallest element (0-indexed order statistic) of [k, v0..v_{n-1}] "
           "by quickselect.",
           "quickselect order statistic (median-of-three pivot, 3-way Dutch-flag partition)"),
    AlgoOp("count_distinct", "stat", SEQ, SCALAR, KIND_REDUCE, "count_distinct",
           _PY_COUNT_DISTINCT, _C_COUNT_DISTINCT,
           "The number of distinct values in a sequence (exact integer count).",
           "distinct-value count via sort + adjacent comparison"),
    AlgoOp("mode_value", "stat", SEQ, SCALAR, KIND_REDUCE, "mode_value",
           _PY_MODE_VALUE, _C_MODE_VALUE,
           "The mode (most frequent value; smallest wins ties) of a sequence.",
           "mode via sort + longest equal run (smallest-value tie-break)"),
    AlgoOp("is_prime", "numtheory", SEQ, SCALAR, KIND_REDUCE, "is_prime",
           _PY_IS_PRIME, _C_IS_PRIME,
           "Primality test of [n] by deterministic Miller-Rabin (1.0 prime / 0.0 not; "
           "0 <= n <= 2^32-1).",
           "deterministic Miller-Rabin primality (witnesses 2..37)"),
    AlgoOp("modular_inverse", "numtheory", SEQ, SCALAR, KIND_REDUCE, "modular_inverse",
           _PY_MODULAR_INVERSE, _C_MODULAR_INVERSE,
           "Modular inverse a^-1 mod m of [a, m] by the extended Euclidean algorithm "
           "(-1.0 if gcd != 1).",
           "extended Euclidean algorithm for the modular inverse"),
    AlgoOp("xor_reduce", "bits", SEQ, SCALAR, KIND_REDUCE, "xor_reduce",
           _PY_XOR_REDUCE, _C_XOR_REDUCE,
           "Bitwise XOR of a sequence of non-negative integers in [0, 2^53-1] (exact).",
           "bitwise XOR reduction"),
    AlgoOp("popcount_total", "bits", SEQ, SCALAR, KIND_REDUCE, "popcount_total",
           _PY_POPCOUNT_TOTAL, _C_POPCOUNT_TOTAL,
           "Total number of set bits across a sequence of non-negative integers "
           "in [0, 2^53-1] (Kernighan).",
           "population count (Kernighan lowest-bit clearing), summed over the sequence"),
    AlgoOp("extended_gcd", "numtheory", SEQ, SEQ, KIND_MAP, "extended_gcd",
           _PY_EXTENDED_GCD, _C_EXTENDED_GCD,
           "Extended Euclidean algorithm of [a, b] -> [g, x, y] with a*x + b*y = "
           "g = gcd(a, b) (non-negative integers <= 2^53; variable-length seq -> "
           "exactly 3 values, or [] fail-soft).",
           "extended Euclidean algorithm; Bezout coefficients"),
]

ALGO_BY_NAME: dict[str, AlgoOp] = {op.name: op for op in ALGO_REGISTRY}

# Compiled reference callables, cached (compiled from the very source string the
# codegen also emits, so oracle and artifact cannot drift).
_PY_FN_CACHE: dict[str, Callable] = {}


def find_algo(name: str) -> AlgoOp | None:
    return ALGO_BY_NAME.get(name)


def algo_names() -> list[str]:
    return [op.name for op in ALGO_REGISTRY]


def algo_categories() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for op in ALGO_REGISTRY:
        out.setdefault(op.category, []).append(op.name)
    return out


def py_fn(name: str) -> Callable:
    """The in-process Python reference for ``name`` (``run(a)`` -> list|float).

    Compiled from ``op.py_code`` — the identical string ``algo_codegen`` writes to
    the standalone ``.py`` — so the tested oracle equals the shipped artifact.
    """
    fn = _PY_FN_CACHE.get(name)
    if fn is None:
        op = ALGO_BY_NAME[name]              # KeyError (fail-closed) for unknown ops
        ns: dict = {}
        exec(compile(op.py_code, f"<algo:{name}>", "exec"), ns)  # noqa: S102 - trusted, in-repo source
        fn = ns["run"]
        _PY_FN_CACHE[name] = fn
    return fn


def run_algo(name: str, seq):
    """Run the general-algorithm ``name`` on ``seq`` (any iterable of numbers).

    Returns a Python ``list`` for a sort or variable-length map (``out_sort == SEQ``)
    or a ``float`` for a reduction (``out_sort == SCALAR``). Fail-closed ``KeyError``
    for unknown ops.
    """
    return py_fn(name)([float(x) for x in seq])


def text_to_seq(s: str) -> list[float]:
    """Encode a string as a code-point sequence (float64) for the P3 string ops.

    Unicode scalars are all < 2^53, so the encoding is exact. Use it to pack inputs,
    e.g. ``[len(p)] + text_to_seq(p) + text_to_seq(t)`` for ``strfind``.
    """
    return [float(ord(c)) for c in s]


def seq_to_text(seq) -> str:
    """Decode a code-point sequence (as produced/consumed by the string ops) to a str."""
    return "".join(chr(round(float(x))) for x in seq)
