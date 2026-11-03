# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Explicit video timing contract backed by :func:`examplefig.save_video`.

The selected base is ``examplefig.save_video``.  First-wave PoCs previously folded
capture timing, playback timing, tail holds, GIF thinning, and display scaling into
``fps``, ``gif_every``, and hand-built frame lists.  This adapter only separates
those inputs and then calls the established writer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np


@dataclass(frozen=True)
class VideoSpec:
    capture_fps: float
    playback_fps: float
    hold_frames: int
    gif_stride: int
    display_scale: float
    interpolation: str

    def __post_init__(self) -> None:
        if not np.isfinite(self.capture_fps) or self.capture_fps <= 0:
            raise ValueError("capture_fps must be positive and finite")
        if not np.isfinite(self.playback_fps) or self.playback_fps <= 0:
            raise ValueError("playback_fps must be positive and finite")
        if isinstance(self.hold_frames, bool) or int(self.hold_frames) != self.hold_frames or self.hold_frames < 0:
            raise ValueError("hold_frames must be a non-negative integer")
        if isinstance(self.gif_stride, bool) or int(self.gif_stride) != self.gif_stride or self.gif_stride < 1:
            raise ValueError("gif_stride must be a positive integer")
        if not np.isfinite(self.display_scale) or self.display_scale <= 0:
            raise ValueError("display_scale must be positive and finite")
        if self.interpolation not in {"nearest", "linear"}:
            raise ValueError("interpolation must be 'nearest' or 'linear'")

    def as_dict(self) -> dict[str, Any]:
        return {
            "capture_fps": float(self.capture_fps),
            "playback_fps": float(self.playback_fps),
            "hold_frames": int(self.hold_frames),
            "gif_stride": int(self.gif_stride),
            "display_scale": float(self.display_scale),
            "interpolation": self.interpolation,
        }


def save_video(
    name: str,
    frames: Sequence[Any],
    *,
    caption: str,
    capture_fps: float,
    playback_fps: float,
    hold_frames: int,
    gif_stride: int,
    display_scale: float,
    interpolation: str,
    signed: bool = False,
):
    """Save via :func:`examplefig.save_video` with every timing choice explicit.

    ``hold_frames`` appends copies of the last frame.  ``display_scale`` controls the
    lightweight GIF width; the MP4 remains full size exactly as in ``examplefig``.
    ``linear`` maps to the existing high-quality continuous-image resize.  ``nearest``
    pre-scales the GIF frames because ``examplefig`` intentionally uses a continuous
    filter for its own resize path.
    """
    spec = VideoSpec(
        capture_fps=capture_fps,
        playback_fps=playback_fps,
        hold_frames=hold_frames,
        gif_stride=gif_stride,
        display_scale=display_scale,
        interpolation=interpolation,
    )
    seq = list(frames)
    if not seq:
        raise ValueError("save_video: frames must not be empty")
    if spec.hold_frames:
        seq.extend([np.array(seq[-1], copy=True) for _ in range(spec.hold_frames)])
    width = int(np.shape(seq[0])[1])
    gif_width = max(1, round(width * spec.display_scale))
    if spec.interpolation == "nearest" and gif_width != width:
        from PIL import Image

        height = int(np.shape(seq[0])[0])
        gif_height = max(1, round(height * spec.display_scale))
        rgb_source = seq
        seq = [np.asarray(Image.fromarray(np.asarray(frame)).resize((gif_width, gif_height), Image.NEAREST)) for frame in seq]
        gif_width = None
        # The MP4 must remain full size.  ``examplefig`` cannot receive separate MP4/GIF
        # sequences, so nearest scaling is only valid when display_scale == 1 for now.
        if spec.display_scale != 1.0:
            seq = rgb_source
            raise ValueError("nearest display scaling below 1 requires separate MP4/GIF frames")
    import examplefig

    return examplefig.save_video(
        name,
        seq,
        caption=caption,
        fps=spec.playback_fps,
        gif_every=spec.gif_stride,
        gif_width=gif_width,
        signed=signed,
    )
