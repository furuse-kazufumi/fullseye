# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Small fail-closed guards for array inputs shared by public operators.

The guard reads an input's shape before a dtype conversion or a contiguous copy.
That order matters: a float64 conversion of an oversized uint8 view can allocate
many times the advertised cap before the operator has a chance to refuse it.
"""
from __future__ import annotations

import numpy as np


# Each caller passes one of these remedies to the shared refusal formatter.  The
# formatter owns the bilingual wording, measured value, cap, and reason; an op
# owns only the action that is useful for its particular kind of input.
IMAGE_CAP_ADVICE = (
    "Downsample the image first (for example, scipy.ndimage.zoom), or process it in tiles.",
    "先に画像を縮小（例: scipy.ndimage.zoom）するか、タイルに分割して処理してください。",
)
VOLUME_CAP_ADVICE = (
    "Call volops.volume_downsample(vol, factor=2) first, or process the volume in tiles.",
    "先に volops.volume_downsample(vol, factor=2) を呼ぶか、ボリュームをタイルに分割して処理してください。",
)
VIDEO_CAP_ADVICE = (
    "Reduce frames or spatial resolution (for example, video[::2, ::2, ::2]), or process shorter clips.",
    "フレーム数または空間解像度を下げる（例: video[::2, ::2, ::2]）か、短いクリップに分けて処理してください。",
)
MATRIX_CAP_ADVICE = (
    "Subsample rows or columns first, or process the observations in batches.",
    "先に行または列を間引くか、観測値をバッチに分けて処理してください。",
)
CHANNEL_CAP_ADVICE = (
    "Use at most 16 threshold channels in thresholds_kev, or split the acquisition into separate calls.",
    "thresholds_kev は 16 チャンネル以下にするか、取得を複数回の呼び出しに分けてください。",
)
CAMERA_COUNT_ADVICE = (
    "Pass one pose and one intrinsic calibration for every image or track; make the three sequence lengths equal.",
    "画像または軌跡ごとに pose と内部パラメータを 1 件ずつ渡し、3 つの系列の長さを一致させてください。",
)


def _advice_pair(advice: tuple[str, str]) -> tuple[str, str]:
    """日英の対処を必須にする / Require an English and Japanese remedy."""
    if not isinstance(advice, tuple) or len(advice) != 2 or not all(isinstance(s, str) and s for s in advice):
        raise TypeError("arrayguard advice must be a non-empty (English, Japanese) tuple")
    return advice


def _cap_message(op: str, name: str, actual: int, cap: int, *,
                 shape: tuple[int, ...] | None, advice: tuple[str, str],
                 unit: tuple[str, str]) -> str:
    """上限拒否を日英で組み立てる / Build a bilingual cap-refusal message."""
    advice_en, advice_ja = _advice_pair(advice)
    unit_en, unit_ja = _advice_pair(unit)
    shape_text = "" if shape is None else " (shape %s)" % (shape,)
    return (
        "English: %s: argument '%s' has %s %s%s, exceeding the limit of %s %s.\n"
        "Why: it is refused before conversion because the operation may allocate oversized working arrays.\n"
        "How: %s\n"
        "日本語: %s: 引数 '%s' は %s %s%sで、上限 %s %sを超えています。\n"
        "理由: 処理用配列の過大な確保を避けるため、変換前に拒否しました。\n"
        "対処: %s"
        % (op, name, format(actual, ","), unit_en, shape_text, format(cap, ","), unit_en, advice_en,
           op, name, format(actual, ","), unit_ja, shape_text, format(cap, ","), unit_ja, advice_ja)
    )


def refuse_cap_exceeded(op: str, name: str, actual: int, cap: int, *,
                        shape: tuple[int, ...] | None,
                        advice: tuple[str, str],
                        unit: tuple[str, str] = ("elements", "要素")) -> None:
    """要素数上限を親切に拒否する / Refuse an element cap with a useful remedy."""
    raise ValueError(_cap_message(op, name, actual, cap, shape=shape, advice=advice, unit=unit))


def refuse_count_mismatch(op: str, counts: dict[str, int], *,
                          advice: tuple[str, str]) -> None:
    """対応する系列の件数不一致を親切に拒否する / Refuse mismatched related counts."""
    advice_en, advice_ja = _advice_pair(advice)
    actual = ", ".join("%s=%s" % (name, format(count, ",")) for name, count in counts.items())
    raise ValueError(
        "English: %s: related argument counts must be equal (%s).\n"
        "Why: each input needs exactly one corresponding camera parameter, so unmatched items cannot be paired safely.\n"
        "How: %s\n"
        "日本語: %s: 対応する引数の件数は一致している必要があります（%s）。\n"
        "理由: 各入力には対応するカメラパラメータが 1 件ずつ必要で、安全に対応付けできません。\n"
        "対処: %s"
        % (op, actual, advice_en, op, actual, advice_ja)
    )


def precheck_shape_and_elements(a, name: str, op: str, cap: int, *,
                                expected_ndim: int | None = None,
                                multiplier: int = 1,
                                advice: tuple[str, str]) -> tuple[int, ...] | None:
    """変換前に shape と要素数上限を検査する / Check shape and cap before coercion.

    ``np.shape`` reads ``ndarray.shape`` without materialising its data, including
    a zero-stride virtual array. Inputs whose shape cannot be read are left to
    the operator's normal coercion path, where its post-coercion guard calls this
    helper again. ``multiplier`` accounts for a known output frame count.
    """
    try:
        shape = tuple(int(d) for d in np.shape(a))
    except (TypeError, ValueError, OverflowError):
        return None
    if expected_ndim is not None and len(shape) != expected_ndim:
        raise ValueError("%s: %s must be %d-D, got shape %r"
                         % (op, name, expected_ndim, shape))
    n = 1
    for dim in shape:
        if dim < 0:
            return None
        n *= dim
    total = n * int(multiplier)
    if total > cap:
        refuse_cap_exceeded(op, name, total, cap, shape=shape, advice=advice)
    return shape
