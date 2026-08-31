"""torch_lazy — a lazy stand-in for ``torch`` and ``torch.nn.functional``.

**Why.** Measured with ``py -3.11 -X importtime`` on this machine, ``import
torch`` costs ~700 ms, and six modules reachable from ``import api``
(``accel_match``, ``match3d``, ``feat_fpfh``, ``feat_harris``, ``feat_shot``,
``feat_spin``) used to pay it at module load. That made every Fullseye Studio
start and every CLI invocation wait for a deep-learning stack most sessions never
touch — against fullseye's contract that numpy+scipy is the baseline and torch is
an *optional extra*.

**What.** ``torch_lazy.torch`` and ``torch_lazy.F`` forward every attribute to the
real modules, importing them on the FIRST ATTRIBUTE ACCESS instead of at module
load. ``HAS_TORCH`` answers "is it installed?" with
:func:`importlib.util.find_spec`, which locates the package without executing its
``__init__``. Drop-in: a module keeps writing ``torch.as_tensor(...)`` and
``F.conv2d(...)`` unchanged.

**The guard that must stay free.** ``torch.is_tensor(x)`` is used across
``match3d`` as an input-kind test, usually on a numpy array, so routing it
through a 700 ms import would defeat the whole point. It is answered *without*
importing torch whenever ``torch`` is absent from :data:`sys.modules`: a value
can only be a ``torch.Tensor`` if torch has already been imported by somebody,
because nothing else can construct one. Once torch is loaded — by a real GPU path
or by the caller — the call delegates to the genuine ``torch.is_tensor``. The
answer is therefore exact in both states, not an approximation.

**When torch is not installed at all**, attribute access raises the same
``ImportError`` the previous hand-written ``_TorchMissing`` shims raised, so the
3-D registry still imports and only the GPU paths fail, with a clear message.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys

_MSG = ("this operator needs the optional 'torch' backend — "
        "install with: pip install \"fullseye[gpu]\"")


def _installed(mod: str) -> bool:
    """True when *mod* is importable, without executing it (cheap path probe)."""
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:  # pragma: no cover - broken meta path finder / namespace pkg
        return False


#: Whether the optional torch extra is present. Same role as the old per-module
#: ``_HAS_TORCH``, resolved without importing torch.
HAS_TORCH = _installed("torch")


class _LazyModule:
    """Attribute-forwarding proxy that imports its target module on first use."""

    __slots__ = ("_name", "_mod")

    def __init__(self, name: str) -> None:
        self._name = name
        self._mod = None

    def _load(self):
        mod = self._mod
        if mod is None:
            try:
                mod = importlib.import_module(self._name)
            except Exception as exc:  # not installed, or a broken build
                raise ImportError(_MSG) from exc
            self._mod = mod
        return mod

    def __getattr__(self, attr):
        # Only reached for names that are not slots/methods of this class, i.e.
        # every real torch attribute.
        return getattr(self._load(), attr)

    def __repr__(self) -> str:
        state = "imported" if self._mod is not None else "not imported yet"
        return "<lazy module %r (%s)>" % (self._name, state)


class _LazyTorch(_LazyModule):
    """``torch`` proxy whose ``is_tensor`` never forces the import."""

    __slots__ = ()

    def __init__(self) -> None:
        super().__init__("torch")

    @staticmethod
    def is_tensor(x) -> bool:
        """Exact ``torch.is_tensor`` that costs nothing while torch is unloaded.

        Nothing but torch itself can build a ``torch.Tensor``, so if ``torch`` is
        not in ``sys.modules`` the answer is provably ``False``.
        """
        mod = sys.modules.get("torch")
        return bool(mod.is_tensor(x)) if mod is not None else False


torch = _LazyTorch()
F = _LazyModule("torch.nn.functional")

__all__ = ["torch", "F", "HAS_TORCH"]
