# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Artifact declarations above the established :mod:`examplefig` manifest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


_KINDS = frozenset({"image", "grid", "plot", "table", "video"})


@dataclass(frozen=True)
class ArtifactSpec:
    """The semantic information for one generated figure, table, or video."""

    name: str
    kind: str
    caption: str
    units: str | Mapping[str, str] = ""
    truth_overlay: str | bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("ArtifactSpec.name must be a non-empty string")
        if self.kind not in _KINDS:
            raise ValueError("ArtifactSpec.kind must be image/grid/plot/table/video")
        if not isinstance(self.caption, str):
            raise TypeError("ArtifactSpec.caption must be a string")

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "caption": self.caption,
            "units": dict(self.units) if isinstance(self.units, Mapping) else self.units,
            "truth_overlay": self.truth_overlay,
        }


def artifacts_from_manifest(
    manifest: Sequence[Mapping[str, Any]],
    *,
    units: Mapping[str, str | Mapping[str, str]] | None = None,
    truth_overlays: Mapping[str, str | bool] | None = None,
) -> list[ArtifactSpec]:
    """Promote existing ``examplefig`` rows without changing ``figures.json``."""
    unit_map = dict(units or {})
    overlay_map = dict(truth_overlays or {})
    out = []
    for row in manifest:
        name = str(row["name"])
        if row.get("animated") or row.get("video"):
            kind = "video"
        elif row.get("csv") or row.get("tsv"):
            kind = "table"
        else:
            kind = str(row.get("kind", "image"))
            if kind not in _KINDS:
                kind = "image"
        out.append(
            ArtifactSpec(
                name=name,
                kind=kind,
                caption=str(row.get("caption", "")),
                units=unit_map.get(name, row.get("unit", "")),
                truth_overlay=overlay_map.get(name, False),
            )
        )
    return out
