"""Fullseye Runtime — the fail-closed load-time gate a recipe must pass to judge.

Studio (design) and Runtime (deployment) share the VM (``fscript``); what the
Runtime adds is a load that REFUSES TO BECOME READY unless, before any part is
inspected, it proves all of:

  1. **ABI major matches.**  A recipe records the contract version it was
     validated against; a runtime refuses a recipe from a different major.
  2. **The recipe is the one the manifest was signed over** (SHA-256 over source
     + goldens + metadata).  Integrity / drift detection — a recipe whose bytes,
     goldens or build-id changed since validation is rejected.  The industrial
     profile refuses an *unsigned* recipe outright.  (This is a checksum, not
     cryptographic authenticity; a keyed signature is a deployment concern.)
  3. **Only vetted, fail-closed operators may judge, each with a WORKING
     backend.**  The industrial profile forbids the 650-op evolution registry
     entirely (its ops fail-open, silently returning "no defects") and verifies a
     backend for every curated op used (docs/FSCRIPT_DECISION.md 1.6b).
  4. **The recipe still returns the SAME judgement on its golden vectors** — the
     proof manufacturing requires instead of "we shipped a migration tool" (R5).
     The industrial profile requires at least one golden, and each must assert
     something.

Any failure raises :class:`FsNotReady`.  Nothing degrades, nothing is guessed;
the runtime stops at load rather than run a pipeline that could judge wrongly.

This is the Path-independent common core (fscript VM + fslib L1); it does not
decide whether recipes are authored in plain Python or a DSL (that is the A/B
question still open on the customer's answers), only how a validated recipe is
loaded safely.
"""
from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field

import numpy as np

import fscript
import fslib

_NUMERIC = (int, float, np.integer, np.floating)

#: Mirrors ``fullseye_abi.h`` FULLSEYE_ABI_VERSION_MAJOR.  A recipe records the
#: major it was validated against; a runtime refuses to load a different major.
ABI_VERSION_MAJOR = 0

__all__ = [
    "ABI_VERSION_MAJOR", "FsNotReady", "GoldenVector", "Recipe", "ReadyRecipe",
    "sign", "compile_recipe", "Verdict", "FullseyeRuntime",
]


class FsNotReady(RuntimeError):
    """The runtime refused to load a recipe; it will not judge until this passes."""


@dataclass(frozen=True)
class GoldenVector:
    """A frozen (inputs -> expected outputs) proof that the judgement is unchanged.

    ``expect`` maps a recipe variable name to the value it MUST produce (reals are
    compared within ``tol``).  These are the "same judgement as when validated"
    evidence a regulated line asks for.
    """

    inputs: dict
    expect: dict
    tol: float = 0.0

    def __post_init__(self):
        # Validate at authoring so a malformed golden can never reach the load
        # path (where a non-dict would AttributeError past the FsNotReady contract,
        # or a non-finite tol would make the comparison assert nothing).
        if not isinstance(self.inputs, dict):
            raise TypeError("GoldenVector.inputs must be a dict, got %s"
                            % type(self.inputs).__name__)
        if not isinstance(self.expect, dict):
            raise TypeError("GoldenVector.expect must be a dict, got %s"
                            % type(self.expect).__name__)
        if not all(isinstance(k, str) for k in self.expect):
            raise TypeError("GoldenVector.expect keys must be strings")
        try:
            t = float(self.tol)
        except (TypeError, ValueError):
            raise ValueError("GoldenVector.tol must be a number, got %r" % (self.tol,))
        if not math.isfinite(t) or t < 0.0:
            raise ValueError(
                "GoldenVector.tol must be finite and >= 0 (an infinite/NaN/negative "
                "tolerance would make the golden prove nothing), got %r" % (self.tol,))


@dataclass(frozen=True)
class Recipe:
    """A recipe = fscript source + the ABI it was validated against + goldens +
    an optional signed source hash (the manifest)."""

    source: str
    abi_major: int = ABI_VERSION_MAJOR
    goldens: tuple = ()
    source_sha256: str = ""          # if set, verified against digest() at load
    build_id: str = ""

    def digest(self) -> str:
        """SHA-256 over the WHOLE manifest, not just the source.

        Covering ``abi_major``, ``build_id`` and each golden's ``(expect, tol)``
        means the "same judgement" proof and the provenance stamp cannot be gutted
        (e.g. ``goldens=()`` swapped in, or a forged ``build_id``) while the hash
        still matches.  Golden *input pixels* are not hashed (they are bulk data;
        a weak golden input is a Studio authoring concern, not a drift signal).

        ★This is an unkeyed checksum: it detects accidental drift / corruption /
        field-swaps within a trusted Studio→Runtime pipeline.  It is NOT
        cryptographic authenticity — a party that can edit the Recipe can also
        re-run ``sign``.  Real provenance needs a keyed (HMAC/asymmetric)
        signature and is a deployment concern (see docs/FSCRIPT_DECISION.md).
        """
        h = hashlib.sha256()
        h.update(self.source.encode("utf-8")); h.update(b"\x00")
        h.update(str(self.abi_major).encode("utf-8")); h.update(b"\x00")
        h.update(self.build_id.encode("utf-8")); h.update(b"\x00")
        for g in self.goldens:
            items = sorted(g.expect.items(), key=lambda kv: kv[0])
            h.update(repr(items).encode("utf-8"))
            h.update(("%.12g" % float(g.tol)).encode("utf-8"))
            h.update(b"\x01")
        return h.hexdigest()


@dataclass(frozen=True)
class ReadyRecipe:
    """A recipe that passed every load-time check and may now judge parts."""

    program: object
    profile: str
    source_sha256: str
    build_id: str
    op_names: frozenset

    def run(self, images=None) -> dict:
        """Inspect one frame under the validated profile; returns the variables."""
        with fslib.profile(self.profile):
            return fscript.run(self.program, images=images).vars


def sign(source: str, abi_major: int = ABI_VERSION_MAJOR, goldens=(),
         build_id: str = "") -> Recipe:
    """Studio-side: seal a recipe by recording the manifest digest.

    ★Integrity/drift detection, not cryptographic authenticity (see
    ``Recipe.digest``).  The industrial profile refuses to load an *unsigned*
    recipe, so this is what the Studio calls before shipping one to a line."""
    r = Recipe(source, abi_major=abi_major, goldens=tuple(goldens), build_id=build_id)
    return Recipe(source, abi_major=abi_major, goldens=tuple(goldens),
                  source_sha256=r.digest(), build_id=build_id)


def _compare(name: str, got, exp, tol: float) -> None:
    # Normalise 0-d numpy arrays (returned by numpy reductions) to Python scalars
    # so the tolerance branch applies instead of an exact ndarray compare.
    if isinstance(got, np.ndarray) and got.ndim == 0:
        got = got.item()
    if isinstance(exp, np.ndarray) and exp.ndim == 0:
        exp = exp.item()
    # Only collapse to a truth compare when BOTH sides are bool; a bool-vs-number
    # otherwise fell through to `bool(got)!=bool(exp)` and matched True to any
    # truthy number.  bool is an int subclass, so a mixed pair drops to numeric.
    if isinstance(exp, bool) and isinstance(got, bool):
        if got != exp:
            raise FsNotReady("golden mismatch on %s: got %r, expected %r" % (name, got, exp))
        return
    if isinstance(exp, _NUMERIC) and isinstance(got, _NUMERIC):
        g, e = float(got), float(exp)
        # NaN always slips through `> tol` (IEEE: every NaN comparison is False),
        # so it is rejected explicitly — a NaN result is exactly the silent
        # degradation the golden gate exists to catch.  (tol is validated finite
        # and non-negative at GoldenVector construction.)
        if math.isnan(g) or math.isnan(e) or not (abs(g - e) <= float(tol)):
            raise FsNotReady("golden mismatch on %s: got %r, expected %r (tol %g)"
                             % (name, got, exp, tol))
        return
    if isinstance(exp, (list, tuple)) or isinstance(got, (list, tuple)):
        gseq = list(got) if isinstance(got, (list, tuple, np.ndarray)) else None
        eseq = list(exp) if isinstance(exp, (list, tuple, np.ndarray)) else None
        if gseq is None or eseq is None or len(gseq) != len(eseq):
            raise FsNotReady("golden mismatch on %s: got %r, expected %r" % (name, got, exp))
        for i, (g, e) in enumerate(zip(gseq, eseq)):
            _compare("%s[%d]" % (name, i), g, e, tol)
        return
    if isinstance(got, np.ndarray) or isinstance(exp, np.ndarray):
        ga, ea = np.asarray(got), np.asarray(exp)
        if ga.shape != ea.shape or bool(np.any(ga != ea)):
            raise FsNotReady("golden mismatch on %s: got %r, expected %r" % (name, got, exp))
        return
    if got != exp:
        raise FsNotReady("golden mismatch on %s: got %r, expected %r" % (name, got, exp))


def compile_recipe(recipe: Recipe, profile: str = "industrial") -> ReadyRecipe:
    """Load a recipe fail-closed. Raises :class:`FsNotReady` on any failure.

    On success returns a :class:`ReadyRecipe`; until then the runtime is not READY
    and must not judge a part.
    """
    industrial = profile == "industrial"

    # 1. ABI major — a recipe from a different contract is not loadable.
    if recipe.abi_major != ABI_VERSION_MAJOR:
        raise FsNotReady(
            "recipe ABI major %d != runtime %d — refusing a recipe validated "
            "against a different contract" % (recipe.abi_major, ABI_VERSION_MAJOR))

    # 2. Manifest digest — the recipe must be the exact one validated.  A missing
    #    manifest is not "nothing to verify" on a line: the industrial profile
    #    refuses an unsigned recipe outright (absence must fail closed).
    try:
        actual = recipe.digest()
    except Exception as e:                              # contract: only FsNotReady escapes
        raise FsNotReady("recipe manifest cannot be digested: %s" % e)
    if recipe.source_sha256:
        if recipe.source_sha256 != actual:
            raise FsNotReady(
                "recipe digest mismatch: manifest %s… != actual %s… — the recipe "
                "is not the one that was validated (source/goldens/build_id changed)"
                % (recipe.source_sha256[:12], actual[:12]))
    elif industrial:
        raise FsNotReady(
            "industrial profile requires a signed recipe (source_sha256); an "
            "unsigned recipe cannot prove it is the validated one")

    # 3. Parse.
    try:
        program = fscript.parse(recipe.source)
    except fscript.FScriptError as e:
        raise FsNotReady("recipe does not parse: %s" % e)

    # 4. Operator vocabulary + backend self-check.
    #    ★A judging recipe may use ONLY the curated fslib-backed builtins, under
    #    EVERY profile (not just industrial).  Any other call is a 650-op
    #    evolution-registry op resolved through fscript._call_registry_op →
    #    api.RT, whose _safe wrapper is fail-OPEN (it swallows an op failure and
    #    returns a benign "no defects" value).  That surface must never be a
    #    recipe's operator — a studio/reference runtime judges parts too — so a
    #    recipe that uses it is rejected at load (docs/FSCRIPT_DECISION.md 1.6b).
    op_names = fscript.used_op_names(program)
    un_vetted = sorted(n for n in op_names if n not in fscript.BUILTINS)
    if un_vetted:
        raise FsNotReady(
            "recipe uses un-vetted operator(s) %s — only the curated fslib "
            "vocabulary may judge parts; the fail-open evolution registry must not "
            "be a recipe's operator (any profile)" % ", ".join(un_vetted))
    #    Name existence is not availability; the industrial profile has no numpy
    #    fallback, so a missing native backend stops the load.
    fslib_ops = sorted({fscript.FSLIB_OP_FOR_BUILTIN[n] for n in op_names
                        if n in fscript.FSLIB_OP_FOR_BUILTIN})
    try:
        fslib.require_ready(fslib_ops, profile)
    except fslib.FsBackendError as e:
        raise FsNotReady(str(e))

    # 5. Golden verification — the proof the judgement is unchanged.  The
    #    industrial profile requires at least one, and every golden must assert
    #    something (an empty ``expect`` proves only that the program ran).
    if industrial and not recipe.goldens:
        raise FsNotReady(
            "industrial profile requires at least one golden vector (the proof the "
            "judgement is unchanged, R5); none were supplied")
    for i, g in enumerate(recipe.goldens):
        if not g.expect:
            raise FsNotReady("golden %d asserts nothing (empty 'expect') — it "
                             "cannot prove the judgement is unchanged" % i)
        try:
            with fslib.profile(profile):
                env = fscript.run(program, images=g.inputs)
        except fslib.FsBackendError as e:
            raise FsNotReady("golden %d: %s" % (i, e))
        except fscript.FScriptError as e:
            raise FsNotReady("golden %d failed to run: %s" % (i, e))
        except Exception as e:                          # contract: only FsNotReady escapes
            raise FsNotReady("golden %d could not run: %s" % (i, e))
        for var, exp in g.expect.items():
            if var not in env.vars:
                raise FsNotReady("golden %d expects variable %r which the recipe "
                                 "did not produce" % (i, var))
            try:
                _compare("golden[%d].%s" % (i, var), env.vars[var], exp, g.tol)
            except FsNotReady:
                raise
            except Exception as e:                     # contract: only FsNotReady escapes
                raise FsNotReady("golden %d: cannot compare %r: %s" % (i, var, e))

    return ReadyRecipe(program, profile, actual, recipe.build_id, frozenset(op_names))


# --------------------------------------------------------------------------- #
# The resident Runtime — what actually judges parts on the line.
#
# It ties the load-time gate (compile_recipe) to the tail mitigations the N1b
# work SUGGESTS (docs/FSCRIPT_MEASUREMENTS.md 9.1 — indicative, N=1, NOT
# established): the large tail appears strongly tied to external CPU-core
# contention preempting cv2's worker threads.  The lever that helped most in a
# 24-core probe was *core availability* (a deployment/OS concern, not something a
# process sets for itself), but that was measured on ONE many-core host and is
# unverified on 4-8-core line PCs — so it is a candidate, not a proven fix.  The
# Runtime's own self-help levers are weaker and reported honestly: (a) bounding
# cv2 threads (modest, noisy) and (b) attempting HIGH process priority (which did
# NOT take effect in the probe — SetPriorityClass needs elevation/a service
# context — so ``high_priority`` reports whether it actually applied).  Plus it
# reports a deadline overrun instead of pretending to abort a native call (R4:
# "make a Python that missed its deadline safe for the line to handle", not "make
# Python hard-real-time").  Verdicts are the boundary a PLC layer consumes:
# OK / NG / ERROR / TIMEOUT.
# --------------------------------------------------------------------------- #
_VERDICTS = ("ok", "ng", "error", "timeout")


@dataclass(frozen=True)
class Verdict:
    """The result of inspecting one frame, in the vocabulary a PLC understands."""

    status: str                       # one of _VERDICTS
    result: dict = field(default=None, compare=False)
    elapsed_ms: float = 0.0
    detail: str = ""

    def __post_init__(self):
        if self.status not in _VERDICTS:
            raise ValueError("verdict status %r not in %s" % (self.status, _VERDICTS))


def _bound_cv2_threads(n) -> bool:
    if n is None:
        return False
    try:
        import cv2
        cv2.setNumThreads(int(n))
        return True
    except Exception:
        return False


def _raise_process_priority() -> bool:
    """Attempt Win32 HIGH_PRIORITY_CLASS so the Runtime wins scheduling against
    other work.  Returns whether it actually applied — it commonly does NOT
    without elevation / a service context (measured), so callers must not assume
    it took effect.  The reliable tail fix is reserving cores, not this."""
    try:
        import ctypes
        HIGH_PRIORITY_CLASS = 0x00000080
        h = ctypes.windll.kernel32.GetCurrentProcess()
        return bool(ctypes.windll.kernel32.SetPriorityClass(h, HIGH_PRIORITY_CLASS))
    except Exception:
        return False


class FullseyeRuntime:
    """A loaded, READY recipe that inspects frames and returns PLC verdicts.

    Not READY until :meth:`start` returns — it refuses to construct from a recipe
    that fails the load-time gate (that is the whole point of the Runtime profile).
    """

    def __init__(self, ready: ReadyRecipe, deadline_ms: float | None = None):
        if deadline_ms is not None:
            try:
                d = float(deadline_ms)
            except (TypeError, ValueError):
                raise ValueError("deadline_ms must be a number or None, got %r" % (deadline_ms,))
            # A NaN deadline would silently disable the TIMEOUT guard (elapsed > NaN
            # is always False); 0/negative would time out every cycle.  Reject both.
            if not math.isfinite(d) or d <= 0.0:
                raise ValueError("deadline_ms must be a finite positive number or "
                                 "None, got %r" % (deadline_ms,))
        self.ready = ready
        self.deadline_ms = deadline_ms
        self.cv2_threads_bounded = False
        self.high_priority = False

    @classmethod
    def start(cls, recipe: Recipe, profile: str = "industrial",
              deadline_ms: float | None = None, cv2_threads: int | None = None,
              high_priority: bool = False) -> "FullseyeRuntime":
        """Load fail-closed, apply the tail mitigations, and become READY.

        Raises :class:`FsNotReady` if the recipe does not pass the load gate.
        """
        ready = compile_recipe(recipe, profile)          # the READY gate
        rt = cls(ready, deadline_ms=deadline_ms)
        rt.cv2_threads_bounded = _bound_cv2_threads(cv2_threads)
        rt.high_priority = _raise_process_priority() if high_priority else False
        return rt

    @property
    def profile(self) -> str:
        return self.ready.profile

    def inspect(self, images=None, judge=None) -> Verdict:
        """Inspect one frame. ``judge(vars) -> bool`` marks a defect (NG); without
        it the verdict is OK/ERROR/TIMEOUT only.

        An operator failure is ERROR (never a silent benign value — the fail-open
        registry is refused at load, so it cannot reach here); a cycle over
        ``deadline_ms`` is TIMEOUT with the (late) result attached, so the PLC
        decides, not the vision code.  ★Honest limit: the deadline is checked
        *after* the cycle returns — a true hang inside a native call cannot be
        interrupted from this thread, so a hard hang would need a watchdog
        thread/process, not this post-hoc check.  Every non-hanging outcome maps
        to exactly one of OK/NG/ERROR/TIMEOUT (any unexpected exception is ERROR).
        """
        t0 = time.perf_counter()
        try:
            with fslib.profile(self.ready.profile):
                out = fscript.run(self.ready.program, images=images).vars
        except fslib.FsBackendError as e:
            return Verdict("error", elapsed_ms=(time.perf_counter() - t0) * 1e3,
                           detail="backend unavailable: %s" % e)
        except fscript.FScriptError as e:
            return Verdict("error", elapsed_ms=(time.perf_counter() - t0) * 1e3,
                           detail="operator error: %s" % e)
        except Exception as e:                          # never crash the line
            return Verdict("error", elapsed_ms=(time.perf_counter() - t0) * 1e3,
                           detail="unexpected error: %s" % e)
        elapsed = (time.perf_counter() - t0) * 1e3
        if self.deadline_ms is not None and elapsed > self.deadline_ms:
            return Verdict("timeout", result=out, elapsed_ms=elapsed,
                           detail="cycle %.2f ms exceeded deadline %.2f ms"
                                  % (elapsed, self.deadline_ms))
        try:
            is_ng = bool(judge(out)) if judge is not None else False
        except Exception as e:
            return Verdict("error", result=out, elapsed_ms=elapsed,
                           detail="judge raised: %s" % e)
        return Verdict("ng" if is_ng else "ok", result=out, elapsed_ms=elapsed)
