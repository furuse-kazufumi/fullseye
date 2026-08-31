# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""handpose(手の 21 キーポイント + 指屈曲角)のテスト。

- 幾何(finger_flexions / 骨格結線 / 描画)は numpy だけで GT 検証(常時実行)。
- 検出経路(mediapipe + モデル)は optional — 不在なら skip、在れば
  空画像 → 0 検出の機械的 e2e と fail-closed(モデル不在の明示エラー)を確認。
"""
import numpy as np
import pytest

import handpose as H


def _straight_hand():
    """全指が伸びきった合成 world 座標(21,3)— 屈曲 0° の GT。

    屈曲角は「手首→付け根」も 1 節として測るので、各指は**原点(手首)からの
    放射直線**上に置く(y 一定のオフセットだと付け根で折れて 18° 出る)。
    """
    w = np.zeros((21, 3))
    for f, chain in enumerate(H.FINGERS.values()):
        d = np.array([1.0, 0.15 * f, 0.0])
        d /= np.linalg.norm(d)
        for j, idx in enumerate(chain):
            w[idx] = 0.03 * (j + 1) * d
    return w


def test_skeleton_edges_cover_all_keypoints():
    edges = H.hand_skeleton_edges()
    seen = {i for e in edges for i in e}
    assert seen == set(range(21))
    assert len(edges) == len(set(edges))               # 重複結線なし


def test_finger_flexions_straight_is_zero():
    flex = H.finger_flexions({"world_landmarks": _straight_hand()})
    assert set(flex) == set(H.FINGERS)
    for name, v in flex.items():
        assert abs(v) < 0.1, f"{name}: 伸びきりで屈曲 {v} != 0"  # arccos は cos~1 で悪条件、0.005°級のジッタを許す


def test_finger_flexions_right_angle_bend():
    w = _straight_hand()
    mcp, pip, dip, tip = H.FINGERS["index"]
    w[dip] = w[pip] + (0.0, 0.0, 0.03)                 # PIP で直角に折る
    w[tip] = w[dip] + (0.0, 0.0, 0.03)
    flex = H.finger_flexions({"world_landmarks": w})
    assert abs(flex["index"] - 90.0) < 0.1, flex["index"]
    assert abs(flex["middle"]) < 0.1                  # 他の指は不変


def test_finger_flexions_rejects_bad_shape():
    with pytest.raises(ValueError):
        H.finger_flexions({"world_landmarks": np.zeros((5, 3))})


def test_draw_is_nondestructive_and_marks_points():
    img = np.zeros((60, 80), np.float64)
    det = {"landmarks": np.full((21, 3), 0.5), "handedness": "Left", "score": 1.0,
           "world_landmarks": _straight_hand()}
    out = H.draw_hand_landmarks(img, [det])
    assert out.shape == (60, 80, 3) and out.dtype == np.uint8
    assert img.sum() == 0                              # 入力は非破壊
    assert (out[30, 40] == (255, 60, 60)).all()        # 正規化 0.5 → 中央に点


_HAS_MP = True
try:
    import mediapipe  # noqa: F401
except ImportError:
    _HAS_MP = False
_HAS_MODEL = H.DEFAULT_MODEL.exists()


@pytest.mark.skipif(not _HAS_MP, reason="mediapipe 不在(optional extra)")
def test_model_missing_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError, match="hand_landmarker"):
        H.hand_landmarks(np.zeros((32, 32)), model_path=tmp_path / "no.task")


@pytest.mark.skipif(not (_HAS_MP and _HAS_MODEL), reason="mediapipe/モデル不在")
def test_blank_image_detects_nothing():
    dets = H.hand_landmarks(np.zeros((240, 320), np.float64))
    assert dets == []
