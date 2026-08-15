"""`fslib.py` must be a conforming implementation of `fullseye_abi.h`.

This is phase I-1 of ``docs/FSCRIPT_DECISION.md``: the header is written first,
as a specification, and this test turns "only allow things that can be lowered
to a C ABI" from a discipline someone has to remember into a check that fails
the build.  No C is compiled — the header is parsed as the contract.

What drift this catches:
  * an operator added to fslib but not to the ABI (or the reverse);
  * an operator whose Python arity stops matching its declaration;
  * a dictionary / arbitrary object escaping across the boundary (ABI rule R-4),
    which is exactly the "shipping Python's semantics as the contract" trap;
  * `Region` growing a public dense-mask attribute again, which would foreclose
    the run-length representation HALCON uses (rule R-2).
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import numpy as np
import pytest

import fslib

ABI = Path(__file__).resolve().parents[1] / "fullseye_abi.h"
SRC = ABI.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# A small parser for the parts of the header that form the contract
# --------------------------------------------------------------------------- #
def status_codes() -> set[str]:
    body = re.search(r"typedef enum fs_status\s*\{(.*?)\}", SRC, re.S).group(1)
    return set(re.findall(r"\b(FS_[A-Z_]+)\s*=", body))


def opaque_types() -> set[str]:
    return set(re.findall(r"typedef struct \w+\s+(fs_\w+_t);", SRC))


def declared_operators() -> dict[str, dict]:
    """`/* @fslib <name> */`-annotated declarations, with their parameters."""
    out = {}
    for m in re.finditer(r"@fslib\s+(\w+)\b(.*?);", SRC, re.S):
        name, tail = m.group(1), m.group(2)
        decl = re.search(r"fs_status_t\s+fs_(\w+)\s*\((.*)\)\s*$", tail, re.S)
        assert decl, "malformed declaration after @fslib %s" % name
        assert decl.group(1) == name, (
            "@fslib %s annotates fs_%s" % (name, decl.group(1)))
        params = [p.strip() for p in decl.group(2).split(",")]
        ins = [p for p in params if not p.endswith("**out")
               and not re.search(r"\*\*\s*\w+$", p)]
        outs = [p for p in params if re.search(r"\*\*\s*\w+$", p)]
        out[name] = {"in": ins, "out": outs}
    return out


OPS = declared_operators()


# --------------------------------------------------------------------------- #
# The header itself must stay well-formed
# --------------------------------------------------------------------------- #
def test_header_declares_the_contract():
    assert "FULLSEYE_ABI_VERSION_MAJOR" in SRC
    assert {"FS_OK", "FS_E_TYPE", "FS_E_NO_BACKEND"} <= status_codes()
    assert {"fs_image_t", "fs_region_t", "fs_objectset_t", "fs_tuple_t"} <= opaque_types()
    assert OPS, "no @fslib-annotated operators found"


def test_every_operator_returns_a_status_code():
    """ABI rule R-1 — results travel through out-params, never a return value."""
    for decl in re.findall(r"\n(fs_\w+\s*\([^;]*\);)", SRC):
        pass  # (declarations are parsed below; this guards the regex shape)
    for m in re.finditer(r"^(\w[\w \t\*]*?)\s+(fs_\w+)\s*\(", SRC, re.M):
        ret, name = m.group(1).strip(), m.group(2)
        if name.endswith("_release"):
            assert ret == "void", "%s must return void" % name
        else:
            assert ret == "fs_status_t", (
                "%s returns %r; every operator must return fs_status_t (R-1)"
                % (name, ret))


# --------------------------------------------------------------------------- #
# fslib must implement exactly the declared operator set
# --------------------------------------------------------------------------- #
def test_operator_sets_agree():
    """The ABI declares the operator SURFACE; fslib must export exactly it.

    Not every operator needs multiple backends — `select_shape` filters ids on
    already-measured values, so it is backend-independent by construction.  What
    must never happen is an operator existing on one side only.
    """
    declared = set(OPS)
    exported = {n for n in declared | set(fslib._REGISTRY)
                if callable(getattr(fslib, n, None))}
    assert declared == exported, (
        "ABI and fslib disagree.\n  only in fullseye_abi.h: %s\n  only in fslib: %s"
        % (sorted(declared - exported), sorted(exported - declared)))


def test_every_backend_op_is_declared_in_the_abi():
    """A backend may only be registered for an operator the ABI knows about."""
    undeclared = set(fslib._REGISTRY) - set(OPS)
    assert not undeclared, (
        "backends registered for operators the ABI does not declare: %s"
        % sorted(undeclared))


@pytest.mark.parametrize("name", sorted(OPS))
def test_public_function_exists_and_arity_matches(name):
    fn = getattr(fslib, name, None)
    assert callable(fn), "fslib.%s is declared in the ABI but not exported" % name
    params = list(inspect.signature(fn).parameters)
    assert len(params) == len(OPS[name]["in"]), (
        "fslib.%s takes %d parameters, fs_%s declares %d inputs (%s)"
        % (name, len(params), name, len(OPS[name]["in"]), OPS[name]["in"]))


@pytest.mark.parametrize("name", sorted(OPS))
def test_declared_parameters_are_abi_representable(name):
    """ABI rule R-4 — scalars, arrays, opaque handles, status codes.  Nothing else."""
    allowed = re.compile(
        r"^(const\s+)?(fs_\w+_t|double|int32_t|int64_t|char|void|fs_dtype_t|fs_elem_t)\b")
    for p in OPS[name]["in"] + OPS[name]["out"]:
        assert allowed.match(p), (
            "fs_%s parameter %r is not an ABI-representable type (R-4)" % (name, p))


# --------------------------------------------------------------------------- #
# Runtime shape: what actually crosses the boundary
# --------------------------------------------------------------------------- #
def _scene():
    yy, xx = np.mgrid[0:64, 0:64]
    a = np.full((64, 64), 40, dtype=np.uint8)
    a[(yy - 20) ** 2 + (xx - 20) ** 2 <= 64] = 220
    a[(yy - 45) ** 2 + (xx - 40) ** 2 <= 49] = 220
    return fslib.FImage.from_u8(a)


ABI_VALUES = (fslib.FImage, fslib.Region, fslib.ObjectSet, np.ndarray,
              int, float, np.integer, np.floating, str, bool, tuple)


def test_no_operator_returns_a_dictionary_or_arbitrary_object():
    """The migration trap: a dict crossing the boundary cannot be lowered to C."""
    img = _scene()
    reg = fslib.threshold(img, 0.5, 1.0)
    objs = fslib.connection(reg)
    results = {
        "gauss": fslib.gauss(img, 1.0),
        "threshold": reg,
        "connection": objs,
        "measure_all": fslib.measure_all(objs),
        "select_shape": fslib.select_shape(objs, "area", 1, 1e12),
    }
    for name, v in results.items():
        assert not isinstance(v, dict), (
            "%s returns a dict; the ABI declares out-params, not a mapping (R-4)" % name)
        flat = v if isinstance(v, tuple) else (v,)
        for item in flat:
            assert isinstance(item, ABI_VALUES), (
                "%s returns %s, which has no ABI representation (R-4)"
                % (name, type(item).__name__))


def test_measure_all_returns_the_three_declared_tuples():
    objs = fslib.connection(fslib.threshold(_scene(), 0.5, 1.0))
    out = fslib.measure_all(objs)
    assert isinstance(out, tuple) and len(out) == len(OPS["measure_all"]["out"]) == 3
    for arr in out:
        assert isinstance(arr, np.ndarray) and arr.shape == (len(objs),)


# --------------------------------------------------------------------------- #
# R-2: the storage of a region is not part of the API
# --------------------------------------------------------------------------- #
def test_region_does_not_expose_its_storage():
    reg = fslib.threshold(_scene(), 0.5, 1.0)
    assert not hasattr(reg, "mask"), (
        "Region.mask is public again — that forecloses the run-length "
        "representation the ABI is written for (R-2)")
    public = {a for a in dir(reg) if not a.startswith("_")}
    assert {"area", "run_count", "runs", "shape"} <= public


def test_region_runs_are_the_representation_independent_view():
    reg = fslib.threshold(_scene(), 0.5, 1.0)
    runs = reg.runs()
    assert runs.ndim == 2 and runs.shape[1] == 3 and runs.dtype == np.int32
    # runs must account for exactly the region's area, whatever the storage is
    assert int((runs[:, 2] - runs[:, 1]).sum()) == reg.area()
    assert reg.run_count() == runs.shape[0]


# --------------------------------------------------------------------------- #
# R-1: errors are status codes, and fslib's exceptions map onto them
# --------------------------------------------------------------------------- #
def test_fslib_error_types_map_onto_declared_status_codes():
    mapping = {fslib.FsTypeError: "FS_E_TYPE", fslib.FsBackendError: "FS_E_NO_BACKEND"}
    codes = status_codes()
    for exc, code in mapping.items():
        assert code in codes, "%s maps to %s, which the ABI does not declare" % (
            exc.__name__, code)

    img = _scene()
    with pytest.raises(fslib.FsTypeError):          # -> FS_E_TYPE
        fslib.connection(img)
    with fslib.profile("industrial"):               # -> FS_E_NO_BACKEND
        @fslib.op("abi_probe_no_native", "numpy")
        def _impl(x):
            return x
        try:
            with pytest.raises(fslib.FsBackendError):
                fslib._dispatch("abi_probe_no_native", img)
        finally:
            fslib._REGISTRY.pop("abi_probe_no_native", None)
