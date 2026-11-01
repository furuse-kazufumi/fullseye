# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC evaluation contracts shared above :mod:`examplefig` and validation helpers.

This package deliberately does not join the public ``fullseye`` facade.  The first
migration wave imports it explicitly so the established facade and operator ledgers
stay unchanged.
"""

from .artifacts import ArtifactSpec, artifacts_from_manifest
from .manifest import build_manifest, compare_manifests, read_manifest, write_manifest
from .metrics import dice, iou, mae, relative_error, rmse
from .result import CaseResult, GateAdapter, GateResult, GateStyle
from .truth import TruthBundle, TruthContractError
from .video import VideoSpec, save_video

__all__ = [
    "ArtifactSpec",
    "CaseResult",
    "GateAdapter",
    "GateResult",
    "GateStyle",
    "TruthBundle",
    "TruthContractError",
    "VideoSpec",
    "artifacts_from_manifest",
    "build_manifest",
    "compare_manifests",
    "dice",
    "iou",
    "mae",
    "read_manifest",
    "relative_error",
    "rmse",
    "save_video",
    "write_manifest",
]
