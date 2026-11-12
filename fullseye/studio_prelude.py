# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Fullseye Studio の Python のモードの前置き(prelude)。

``from fullseye.studio_prelude import *`` で、Studio の Program 欄と同じ名前が手に入る:

* op 名の関数 —— ``gaussian(img, 0.4)``・``otsu(img)``・``blob_count(mask)``。入力を省くと「今の流れ」
  (最後に画像・領域を返した op の結果。最初は入力)に掛ける。組み込み名・予約語と衝突する op は
  ``op("名前", x, a, b)`` で呼ぶ(:func:`studio_program.prelude_collisions`)。
* ``show(x)`` / ``op`` / ``pipeline`` / ``current_pipeline`` / ``load_pipeline`` / ``np`` / ``fs`` /
  ``studio_input`` / ``studio_output``、表示指示(``dev_*`` / ``disp_*`` / ``set_system``。記録するだけ)。

op の呼び出しは記録され(:class:`studio_program.CallRecord`)、メモ化される。Studio の中では Studio の
記録へ、単独のスクリプトではこのプロセスの記録へ入る。実体は top-level の ``studio_program`` にある。
"""
from __future__ import annotations

import studio_program as _sp

_NS = _sp.prelude_namespace()
globals().update(_NS)
__all__ = sorted(_NS)
