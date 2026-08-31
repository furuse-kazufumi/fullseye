# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""デモ: 写真/Web カメラから手の 21 キーポイントと指の屈曲角を取る.

使い方::

    py -3.11 examples/hand_tracking_demo.py photo.jpg      # 画像 1 枚
    py -3.11 examples/hand_tracking_demo.py --camera 0     # Web カメラ 1 フレーム

要件(optional extra、無ければ導入手順つきで明示エラー):
    py -3.11 -m pip install mediapipe
    手モデル hand_landmarker.task(handpose.MODEL_URL、~8MB、Apache-2.0)

出力:
    - 手ごとの左右・信頼度・指 5 本の屈曲角[deg](伸びきり 0° / 直角 90°)
    - <入力名>_hands.png(点+骨の注釈画像)
このデモは Physical AI ブリッジの入口 — 屈曲角を [0,1] に正規化すれば
ロボットハンド(相反駆動)の目標指令への最初のリターゲットになる。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import handpose as H  # noqa: E402


def _load_image(argv):
    if len(argv) >= 3 and argv[1] == "--camera":
        import cv2
        cap = cv2.VideoCapture(int(argv[2]))
        ok, frame = cap.read()
        cap.release()
        if not ok:
            raise SystemExit(f"カメラ {argv[2]} からフレームを取得できない")
        return frame[:, :, ::-1].copy(), Path("camera_frame")
    if len(argv) >= 2:
        from PIL import Image
        p = Path(argv[1])
        return np.asarray(Image.open(p).convert("RGB")), p
    raise SystemExit(__doc__)


def main():
    rgb, src = _load_image(sys.argv)
    dets = H.hand_landmarks(rgb)
    print(f"検出: {len(dets)} 手  (入力 {src.name}, {rgb.shape[1]}x{rgb.shape[0]})")
    for i, det in enumerate(dets):
        flex = H.finger_flexions(det)
        print(f"  hand{i}: {det['handedness']}  score={det['score']:.2f}")
        print("    屈曲角[deg]: " +
              "  ".join(f"{k}={v:5.1f}" for k, v in flex.items()))
    if dets:
        from PIL import Image
        out = Path(f"{src.stem}_hands.png")
        Image.fromarray(H.draw_hand_landmarks(rgb, dets)).save(out)
        print(f"注釈画像: {out}")
    else:
        print("手が写っていないか、写りが小さすぎる(手が画面の 1/10 以上を占める距離で)")


if __name__ == "__main__":
    main()
