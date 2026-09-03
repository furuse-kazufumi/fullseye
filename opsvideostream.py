# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsvideostream — fullseye ストリーミング動画処理 op の統一レジストリ。

動機(2026-09-03、docs/design/PERF_MEMORY_VIDEO_SURVEY.md §3):既存の
:mod:`videops` は ``(T, H, W)`` を一括で受け取る(1080p 1 秒 = float64 475 MB)。
カメラ・ロボットの眼・長時間録画は「全フレーム」を一度に渡してこない。
本族は **1 フレームずつ**処理する形 — リングバッファ(メモリ = 窓幅 N 枚)、
状態つき op(``push(frame) → out``)、パイプライン — を op として台帳に載せる。

台帳に載る関数は ``(T, H, W)`` を受け取る **一括版**だが、その実体は
ストリーミングクラスをクリップに沿って再生したもの(:func:`videostream.stream_replay`)
なので、**生の配信で 1 フレームずつ得た結果と台帳 op の結果はフレーム単位で
一致する**(tests/test_videostream.py が固定)。

既存 videops との違いは名前に出す(同名で違う数を出さない):
  * ``temporal_median``(全 T の中央値) ↔ ``temporal_median_window``(直近 N 枚、因果)
  * ``moving_average``(中心窓・端複製) ↔ ``moving_average_window``(因果)
  * ``frame_difference``(T−1 枚)       ↔ ``frame_difference_causal``(T 枚、先頭ゼロ)
  * ``background_subtraction``(全 T 中央値背景) ↔ ``background_subtraction_window``
  * ``optical_flow_sequence``(T−1 枚) ↔ ``optical_flow_magnitude_stream``(T 枚)

使い方:
    import opsvideostream
    opsvideostream.list_ops("window")
    opsvideostream.call("temporal_median_window", clip, window=5)
"""
import videostream

_MOD = {"videostream": videostream}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    "window": [
        ("temporal_median_window", "videostream", ["video"], "video"),
        ("moving_average_window", "videostream", ["video"], "video"),
        ("background_subtraction_window", "videostream", ["video"], "video"),
    ],
    "recursive": [
        ("frame_difference_causal", "videostream", ["video"], "video"),
        ("exponential_background", "videostream", ["video"], "video"),
        ("exponential_foreground", "videostream", ["video"], "video"),
        ("running_mean_std", "videostream", ["video"], "table"),
    ],
    "flow": [
        ("optical_flow_magnitude_stream", "videostream", ["video"], "video"),
    ],
    "motion": [
        ("motion_history_image", "videostream", ["video"], "video"),
        ("motion_energy_image", "videostream", ["video"], "video"),
        ("three_frame_difference", "videostream", ["video"], "video"),
    ],
    "background": [
        ("running_gaussian_foreground", "videostream", ["video"], "video"),
        ("running_gaussian_background", "videostream", ["video"], "video"),
    ],
    "denoise": [
        ("temporal_bilateral", "videostream", ["video"], "video"),
    ],
    "restore": [
        ("deflicker", "videostream", ["video"], "video"),
    ],
    "analysis": [
        ("scene_cut_detection", "videostream", ["video"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = ""
            if fn is not None and fn.__doc__:
                doc = fn.__doc__.strip().splitlines()[0]
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSVIDEOSTREAM = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSVIDEOSTREAM.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。空 = 全 op が宣言型そのもの(ndarray /
#: dict)を素で返す。``running_mean_std`` の dict は table として宣言どおり。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSVIDEOSTREAM[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSVIDEOSTREAM[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSVIDEOSTREAM[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSVIDEOSTREAM.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsvideostream: {len(OPSVIDEOSTREAM)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
