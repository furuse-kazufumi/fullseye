"""Fullseye Runtime — the fail-closed load-time gate a recipe must pass to judge.

Studio (design) and Runtime (deployment) share the VM (``fscript``); what the
Runtime adds is a load that REFUSES TO BECOME READY unless, before any part is
inspected, it proves all of:

  1. **ABI major matches.**  A recipe records the contract version it was
     validated against; a runtime refuses a recipe from a different major.
  2. **The source is the one the manifest was signed over** (SHA-256).  Tamper /
     drift detection: a recipe whose bytes changed since validation is rejected.
  3. **Every operator has a WORKING backend** under the industrial profile.  The
     650-op evolution registry is fail-open (a failed op silently returns "no
     defects"); that must never reach a line (docs/FSCRIPT_DECISION.md 1.6b).
  4. **The recipe still returns the SAME judgement on its golden vectors** — the
     proof manufacturing requires instead of "we shipped a migration tool" (R5).

Any failure raises :class:`FsNotReady`.  Nothing degrades, nothing is guessed;
the runtime stops at load rather than run a pipeline that could judge wrongly.

This is the Path-independent common core (fscript VM + fslib L1); it does not
decide whether recipes are authored in plain Python or a DSL (that is the A/B
question still open on the customer's answers), only how a validated recipe is
loaded safely.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

import fscript
import fslib

#: Mirrors ``fullseye_abi.h`` FULLSEYE_ABI_VERSION_MAJOR.  A recipe records the
#: major it was validated against; a runtime refuses to load a different major.
ABI_VERSION_MAJOR = 0

__all__ = [
    "ABI_VERSION_MAJOR", "FsNotReady", "GoldenVector", "Recipe", "ReadyRecipe",
    "sign", "compile_recipe",
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
        """SHA-256 of the source — the thing the manifest signs."""
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()


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
    """Studio-side: seal a recipe by recording the SHA-256 of its source."""
    r = Recipe(source, abi_major=abi_major, goldens=tuple(goldens), build_id=build_id)
    return Recipe(source, abi_major=abi_major, goldens=tuple(goldens),
                  source_sha256=r.digest(), build_id=build_id)


def _compare(name: str, got, exp, tol: float) -> None:
    if isinstance(exp, bool) or isinstance(got, bool):
        if bool(got) != bool(exp):
            raise FsNotReady("golden mismatch on %s: got %r, expected %r" % (name, got, exp))
        return
    if isinstance(exp, (int, float)) and isinstance(got, (int, float, np.integer, np.floating)):
        if abs(float(got) - float(exp)) > tol:
            raise FsNotReady("golden mismatch on %s: got %r, expected %r (tol %g)"
                             % (name, got, exp, tol))
        return
    if isinstance(exp, (list, tuple)):
        seq = list(got) if isinstance(got, (list, tuple, np.ndarray)) else None
        if seq is None or len(seq) != len(exp):
            raise FsNotReady("golden mismatch on %s: got %r, expected %r" % (name, got, exp))
        for i, (g, e) in enumerate(zip(seq, exp)):
            _compare("%s[%d]" % (name, i), g, e, tol)
        return
    if got != exp:
        raise FsNotReady("golden mismatch on %s: got %r, expected %r" % (name, got, exp))


def compile_recipe(recipe: Recipe, profile: str = "industrial") -> ReadyRecipe:
    """Load a recipe fail-closed. Raises :class:`FsNotReady` on any failure.

    On success returns a :class:`ReadyRecipe`; until then the runtime is not READY
    and must not judge a part.
    """
    # 1. ABI major — a recipe from a different contract is not loadable.
    if recipe.abi_major != ABI_VERSION_MAJOR:
        raise FsNotReady(
            "recipe ABI major %d != runtime %d — refusing a recipe validated "
            "against a different contract" % (recipe.abi_major, ABI_VERSION_MAJOR))

    # 2. Manifest source hash — the recipe must be the exact one validated.
    actual = recipe.digest()
    if recipe.source_sha256 and recipe.source_sha256 != actual:
        raise FsNotReady(
            "recipe source SHA-256 mismatch: manifest %s… != actual %s… — the "
            "recipe is not the one that was validated"
            % (recipe.source_sha256[:12], actual[:12]))

    # 3. Parse.
    try:
        program = fscript.parse(recipe.source)
    except fscript.FScriptError as e:
        raise FsNotReady("recipe does not parse: %s" % e)

    # 4. Backend self-check — a clear early error before running goldens.  Name
    #    existence is not availability; the industrial profile has no numpy
    #    fallback, so a missing native backend stops the load.
    op_names = fscript.used_op_names(program)
    fslib_ops = sorted({fscript.FSLIB_OP_FOR_BUILTIN[n] for n in op_names
                        if n in fscript.FSLIB_OP_FOR_BUILTIN})
    try:
        fslib.require_ready(fslib_ops, profile)
    except fslib.FsBackendError as e:
        raise FsNotReady(str(e))

    # 5. Golden verification — definitive: running each golden under the profile
    #    exercises every operator's dispatch AND proves the judgement is unchanged.
    for i, g in enumerate(recipe.goldens):
        try:
            with fslib.profile(profile):
                env = fscript.run(program, images=g.inputs)
        except fslib.FsBackendError as e:
            raise FsNotReady("golden %d: %s" % (i, e))
        except fscript.FScriptError as e:
            raise FsNotReady("golden %d failed to run: %s" % (i, e))
        for var, exp in g.expect.items():
            if var not in env.vars:
                raise FsNotReady("golden %d expects variable %r which the recipe "
                                 "did not produce" % (i, var))
            _compare("golden[%d].%s" % (i, var), env.vars[var], exp, g.tol)

    return ReadyRecipe(program, profile, actual, recipe.build_id, frozenset(op_names))
