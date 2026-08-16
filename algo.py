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

stdlib only (the Python references use no numpy — they mirror the C index-by-index
so "re-implemented from spec" is visibly true). P1 scope: seq/scalar + 3 sorts +
2 reductions. Later phases (numerics/strings/graphs) add sorts and ops here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# --- value sorts for the general tier (distinct from the image sorts) -------- #
SEQ = "seq"        # a 1-D sequence of real numbers (Python: list[float]; C: double*)
SCALAR = "scalar"  # a single real number (Python: float; C: double)

# Kinds tell the codegen/driver how an op is called at the C boundary:
#   "sort_inplace" : void f(double* a, int n)   — reorders a in place
#   "reduce"       : double f(const double* a, int n) — folds a to one number
KIND_SORT = "sort_inplace"
KIND_REDUCE = "reduce"


@dataclass(frozen=True)
class AlgoOp:
    """One general-purpose algorithm, with a Python reference and a C reference.

    ``py_code`` defines a top-level ``run(a)`` (``a`` a Python list of floats):
    a sort returns a new sorted list; a reduction returns a float. ``c_code`` is
    the C definition of ``c_func`` with the signature implied by ``kind``. Both
    are re-implementations from the named ``provenance`` method.
    """

    name: str
    category: str        # "sort" | "reduce"
    in_sort: str         # SEQ
    out_sort: str        # SEQ | SCALAR
    kind: str            # KIND_SORT | KIND_REDUCE
    c_func: str          # the C function name emitted / called
    py_code: str         # standalone source defining run(a)
    c_code: str          # C source defining c_func
    doc: str
    provenance: str


# --------------------------------------------------------------------------- #
# Python references — re-implemented from spec, index-by-index like the C so the
# equivalence is auditable. Pure stdlib; operate on / return Python lists.
# --------------------------------------------------------------------------- #
_PY_QUICKSORT = '''\
def run(a):
    """Quicksort (Hoare/Lomuto partition, median-of-three pivot), iterative.

    Median-of-three pivoting keeps sorted / reverse-sorted inputs off the O(n^2)
    path; an explicit stack avoids Python recursion limits. In place on a copy.
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
        mid = (lo + hi) // 2
        # median-of-three: order a[lo] <= a[mid] <= a[hi], park median at hi
        if a[mid] < a[lo]:
            a[lo], a[mid] = a[mid], a[lo]
        if a[hi] < a[lo]:
            a[lo], a[hi] = a[hi], a[lo]
        if a[hi] < a[mid]:
            a[mid], a[hi] = a[hi], a[mid]
        pivot = a[mid]
        a[mid], a[hi] = a[hi], a[mid]      # move pivot to the end (Lomuto)
        i = lo - 1
        for j in range(lo, hi):
            if a[j] <= pivot:
                i += 1
                a[i], a[j] = a[j], a[i]
        i += 1
        a[i], a[hi] = a[hi], a[i]          # place pivot at its final position
        # push the larger side first so the stack stays O(log n)
        if i - lo > hi - i:
            stack.append((lo, i - 1))
            stack.append((i + 1, hi))
        else:
            stack.append((i + 1, hi))
            stack.append((lo, i - 1))
    return a
'''

_C_QUICKSORT = '''\
/* Quicksort: median-of-three pivot, Lomuto partition, explicit stack. */
static void _swap(double* a, int i, int j) { double t = a[i]; a[i] = a[j]; a[j] = t; }
void quicksort(double* a, int n) {
    if (n < 2) return;
    /* stack depth <= 2*ceil(log2(n))+2; 128 handles n up to ~2^63. */
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
        _swap(a, mid, hi);
        int i = lo - 1;
        for (int j = lo; j < hi; j++) {
            if (a[j] <= pivot) { i++; _swap(a, i, j); }
        }
        i++;
        _swap(a, i, hi);
        if (i - lo > hi - i) {
            lo_st[sp] = lo; hi_st[sp] = i - 1; sp++;
            lo_st[sp] = i + 1; hi_st[sp] = hi; sp++;
        } else {
            lo_st[sp] = i + 1; hi_st[sp] = hi; sp++;
            lo_st[sp] = lo; hi_st[sp] = i - 1; sp++;
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

_C_HEAPSORT = '''\
/* Heapsort: binary max-heap with sift-down (Williams 1964). */
static void _sift_down(double* a, int start, int end) {
    int root = start;
    while (2 * root + 1 <= end) {
        int child = 2 * root + 1;
        if (child + 1 <= end && a[child] < a[child + 1]) child++;
        if (a[root] < a[child]) {
            double t = a[root]; a[root] = a[child]; a[child] = t;
            root = child;
        } else return;
    }
}
void heapsort(double* a, int n) {
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
void mergesort_asc(double* a, int n) {
    if (n < 2) return;
    double* tmp = (double*)malloc((size_t)n * sizeof(double));
    if (!tmp) return;                          /* out of memory: leave a unsorted */
    _msort(a, tmp, 0, n);
    free(tmp);
}
'''

_PY_SEQ_MAX = '''\
def run(a):
    """Maximum of a sequence (order-independent, exact). Empty -> 0.0."""
    if len(a) == 0:
        return 0.0
    m = a[0]
    for i in range(1, len(a)):
        if a[i] > m:
            m = a[i]
    return m
'''

_C_SEQ_MAX = '''\
/* Maximum of a sequence (order-independent, exact). Empty -> 0.0. */
double seq_max(const double* a, int n) {
    if (n <= 0) return 0.0;
    double m = a[0];
    for (int i = 1; i < n; i++) if (a[i] > m) m = a[i];
    return m;
}
'''

_PY_SEQ_MIN = '''\
def run(a):
    """Minimum of a sequence (order-independent, exact). Empty -> 0.0."""
    if len(a) == 0:
        return 0.0
    m = a[0]
    for i in range(1, len(a)):
        if a[i] < m:
            m = a[i]
    return m
'''

_C_SEQ_MIN = '''\
/* Minimum of a sequence (order-independent, exact). Empty -> 0.0. */
double seq_min(const double* a, int n) {
    if (n <= 0) return 0.0;
    double m = a[0];
    for (int i = 1; i < n; i++) if (a[i] < m) m = a[i];
    return m;
}
'''


ALGO_REGISTRY: list[AlgoOp] = [
    AlgoOp("quicksort", "sort", SEQ, SEQ, KIND_SORT, "quicksort",
           _PY_QUICKSORT, _C_QUICKSORT,
           "Sort a sequence ascending, in place (average O(n log n)).",
           "Hoare 1961 quicksort; Lomuto partition; median-of-three pivot"),
    AlgoOp("heapsort", "sort", SEQ, SEQ, KIND_SORT, "heapsort",
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

    Returns a Python ``list`` for a sort (``out_sort == SEQ``) or a ``float`` for
    a reduction (``out_sort == SCALAR``). Fail-closed ``KeyError`` for unknown ops.
    """
    return py_fn(name)([float(x) for x in seq])
