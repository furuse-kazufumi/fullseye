# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Hand pose — 手の 21 キーポイント検出と指屈曲角(Physical AI ブリッジ層).

1 行ファサード::

    import handpose; dets = handpose.hand_landmarks(rgb_image)

段階的 API::

    hand_landmarks(image)        画像 → 手ごとの 21 点(正規化座標 + world 座標[m])
    finger_flexions(det)         1 検出 → 指 5 本の屈曲角[deg](retarget の入口)
    hand_skeleton_edges()        骨格の結線(描画/グラフ化用)
    draw_hand_landmarks(img, d)  numpy だけで点+骨を描いた注釈画像を返す

位置づけ(docs/NEXT_OPS_PLAN_2026-08-31.md §C):
    G1 歩行で実証済みの「mocap → 模倣 RL」の手版パイプラインの入口。
    動画 → 21 点 → 指屈曲角 → evis 手(相反 u + 共収縮 c)へのリターゲットが北極星。

依存(optional extra、fail-closed):
    検出には mediapipe(Apache-2.0)と手モデル ``hand_landmarker.task``(~8MB、
    Apache-2.0)が要る。どちらか欠けると **ImportError/FileNotFoundError を
    導入手順つきで明示送出**する(黙って空を返さない)。
    ``finger_flexions`` / ``hand_skeleton_edges`` / ``draw_hand_landmarks`` は
    numpy だけで動く(検出結果さえあれば mediapipe 不要)。

導入手順::

    py -3.11 -m pip install mediapipe
    curl -L -o %USERPROFILE%/.cache/fullseye/hand_landmarker.task ^
        https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/1/hand_landmarker.task")
DEFAULT_MODEL = Path.home() / ".cache" / "fullseye" / "hand_landmarker.task"

# MediaPipe Hands の 21 キーポイント番号(0=手首、各指は付け根→先端の 4 点)
WRIST = 0
FINGERS = {
    "thumb": (1, 2, 3, 4),
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}

_LANDMARKER_CACHE: dict = {}


def hand_skeleton_edges() -> list[tuple[int, int]]:
    """21 キーポイントの骨格結線(手首→各指付け根、指内の連結、掌の橋)。"""
    edges = []
    for chain in FINGERS.values():
        edges.append((WRIST, chain[0]))
        edges.extend(zip(chain[:-1], chain[1:]))
    # 掌を横に渡す橋(付け根同士)
    roots = [c[0] for c in FINGERS.values()]
    edges.extend(zip(roots[:-1], roots[1:]))
    return edges


def _to_rgb_uint8(image) -> np.ndarray:
    """float[0,1] gray / float[0,1] RGB / uint8 RGB を uint8 RGB に正規化。

    fail-closed: float なのに値域が [0,1] を超える(= 0..255 スケールの疑い)
    入力や uint8 以外の整数型は、無言で 2 値に潰さず明示エラーにする
    (敵対レビュー 2026-08-31 D6: 旧版は float 0..255 を {0,255} の 2 値に潰し
    「検出 0 手」という最も静かな失敗になっていた)。"""
    a = np.asarray(image)
    if a.ndim == 2:
        a = np.stack([a, a, a], axis=-1)
    if a.ndim != 3 or a.shape[-1] != 3:
        raise ValueError(f"hand_landmarks: HxW か HxWx3 が必要 (shape={a.shape})")
    if a.dtype == np.uint8:
        return np.ascontiguousarray(a)
    if a.dtype == np.bool_:
        return np.ascontiguousarray(a.astype(np.uint8) * 255)
    if not np.issubdtype(a.dtype, np.floating):
        raise ValueError(
            f"hand_landmarks: 整数画像は uint8 のみ対応 (dtype={a.dtype})。"
            "uint8 に変換するか float [0,1] に正規化してから渡すこと")
    mx = float(a.max()) if a.size else 0.0
    if mx > 1.001:
        raise ValueError(
            f"hand_landmarks: float 画像の値域が [0,1] を超えている (max={mx:.3g})。"
            "0..255 スケールの疑い — 255 で割ってから渡すこと")
    a = (np.clip(a.astype(np.float64), 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    return np.ascontiguousarray(a)


_CACHE_LOCK = __import__("threading").Lock()


def _import_mediapipe():
    """mediapipe を親切なエラーつきで import(fail-closed の唯一の入口)。"""
    try:
        import mediapipe as mp
        return mp
    except ImportError as e:
        raise ImportError(
            "hand_landmarks には mediapipe が必要です: py -3.11 -m pip install mediapipe"
        ) from e


def _get_landmarker(model_path: str, num_hands: int, min_confidence: float):
    key = (model_path, int(num_hands), float(min_confidence))
    with _CACHE_LOCK:
        if key in _LANDMARKER_CACHE:
            return _LANDMARKER_CACHE[key]
        _import_mediapipe()
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"手モデル hand_landmarker.task がありません: {model_path}\n"
                f"取得: curl -L -o \"{model_path}\" {MODEL_URL}")
        opts = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            num_hands=int(num_hands),
            min_hand_detection_confidence=float(min_confidence))
        _LANDMARKER_CACHE[key] = vision.HandLandmarker.create_from_options(opts)
        return _LANDMARKER_CACHE[key]


def hand_landmarks(image, num_hands: int = 2, model_path=None,
                   min_confidence: float = 0.5) -> list[dict]:
    """画像から手の 21 キーポイントを検出する(手ごとに 1 dict)。

    Returns:
        list[dict] — 各要素:
          ``handedness``       "Left" / "Right"(画像上の見た目でなく解剖学的左右)
          ``score``            検出信頼度 [0,1]
          ``landmarks``        (21, 3) float。x, y は画像正規化 [0,1]、z は手首基準の相対深度
          ``world_landmarks``  (21, 3) float。手の幾何中心を原点とするメートル座標
                               (関節角の計算はこちらを使う — 遠近で歪まない)
    """
    # 先に _get_landmarker(内部で親切な ImportError/FileNotFoundError を送出)。
    # 素の import を先に置くと fail-closed メッセージが永久に到達しない
    # (敵対レビュー 2026-08-31 D1 で実測された到達不能デッドコード)
    lm = _get_landmarker(str(model_path or DEFAULT_MODEL), num_hands, min_confidence)
    mp = _import_mediapipe()
    rgb = _to_rgb_uint8(image)
    res = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    out = []
    for i, marks in enumerate(res.hand_landmarks):
        hd = res.handedness[i][0] if res.handedness else None
        out.append({
            "handedness": (hd.category_name if hd else "Unknown"),
            "score": float(hd.score) if hd else 0.0,
            "landmarks": np.array([[p.x, p.y, p.z] for p in marks], np.float64),
            "world_landmarks": np.array(
                [[p.x, p.y, p.z] for p in res.hand_world_landmarks[i]], np.float64),
        })
    return out


def _angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """3 点 a-b-c の b における折れ角(伸びきり = 0°、直角 = 90°)。"""
    u = a - b
    v = c - b
    cos = float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12))
    return 180.0 - float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def finger_flexions(det: dict) -> dict:
    """1 検出の world 座標から指 5 本の屈曲角[deg]を出す(retarget の入口)。

    定義(正確に): 各指チェーンの最初の 2 関節 —— 手首→付け根→第 2 点の折れ角と
    付け根→第 2 点→第 3 点の折れ角 —— の**和**。人差し指〜小指では MCP+PIP、
    **親指ではチェーンが CMC から始まるため CMC+MCP** に相当する。先端の関節
    (DIP / 親指 IP)は含めない。伸びきり ~0°、握り込み ~180°+。

    **符号なし**(値域 [0, 360])に注意: 過伸展(反り)は屈曲と同じ正の角で
    出る(−20° の反りと +20° の曲げは区別できない)。反りの分離が要る用途は
    掌法線に対する符号付き定義へ差し替えること(敵対レビュー 2026-08-31 D7)。
    ロボットハンドの相反駆動への写像は「屈曲量を [0,1] に正規化」が最初の近似。
    """
    w = np.asarray(det["world_landmarks"], np.float64)
    if w.shape != (21, 3):
        raise ValueError(f"world_landmarks は (21,3) が必要 (shape={w.shape})")
    out = {}
    for name, (mcp, pip, dip, tip) in FINGERS.items():
        base = w[WRIST]
        flex = _angle_deg(base, w[mcp], w[pip]) + _angle_deg(w[mcp], w[pip], w[dip])
        out[name] = float(flex)
    return out


def draw_hand_landmarks(image, dets: list[dict]) -> np.ndarray:
    """検出結果を点+骨で描いた注釈画像(uint8 RGB)を返す(numpy のみ・非破壊)。"""
    canvas = _to_rgb_uint8(image).copy()
    h, wpx = canvas.shape[:2]
    for det in dets:
        pts = np.asarray(det["landmarks"], np.float64)
        px = np.stack([np.clip(pts[:, 1] * h, 0, h - 1),
                       np.clip(pts[:, 0] * wpx, 0, wpx - 1)], axis=1).astype(int)
        for i0, i1 in hand_skeleton_edges():
            n = int(max(abs(px[i1] - px[i0]).max(), 1))
            ys = np.linspace(px[i0, 0], px[i1, 0], n + 1).astype(int)
            xs = np.linspace(px[i0, 1], px[i1, 1], n + 1).astype(int)
            canvas[ys, xs] = (0, 200, 80)
        for y, x in px:
            canvas[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = (255, 60, 60)
    return canvas
