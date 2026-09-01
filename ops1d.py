# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ops1d — fullseye 1D op の統一レジストリ(funct1d + dsp を一望・発見可能に)。

3D に ops3d があるのに 1D には目録が無く、**funct1d(HALCON funct_1d 対応の
23 関数)は完全な孤児**(未出荷・未文書)、dsp(信号処理 16 関数)は出荷済みでも
OP_CATALOG から不可視だった(2026-08-31 監査)。1D は「op が足りない」のでなく
「あるのに接続されていない」— 本レジストリがその接続点。

1D データの源流は 3 つ: 2D の measure1d(ops.REGISTRY 内)、3D の volprobe
(ops3d "probe")、そして dsp の音声/センサー系列。どれも「プロファイル
(x, y の列)を取り出したら funct1d/dsp で加工して測る」に合流する。

使い方:
    import ops1d
    ops1d.list_ops("function")      # カテゴリ内の op 名
    ops1d.get("derivate_funct_1d")  # 実体を取得して呼ぶ
"""
import numpy as np

import dsp
import funct1d

_MOD = {"funct1d": funct1d, "dsp": dsp}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   種別語彙: signal(1-D array)/ pairs((x,y))/ indices / measurement / file
_CATALOG = {
    "function": [  # HALCON funct_1d 対応の関数処理(プロファイル計測の後段)
        ("create_funct_1d_array", "funct1d", ["signal"], "signal"),
        # 名前は「pairs から作る」の意味で、**返りは等間隔格子へ再標本化した
        # funct_1d(1-D の y 列)**(実測 ndarray (n,)、docstring も
        # "resampled to an equidistant grid")。pairs を名乗っていたのは型の嘘で、
        # 2026-09-02 に pairs の述語(それまで lambda v: True)を入れて顕在化した
        ("create_funct_1d_pairs", "funct1d", ["signal", "signal"], "signal"),
        ("smooth_funct_1d_gauss", "funct1d", ["signal"], "signal"),
        ("smooth_funct_1d_mean", "funct1d", ["signal"], "signal"),
        ("derivate_funct_1d", "funct1d", ["signal"], "signal"),
        ("integrate_funct_1d", "funct1d", ["signal"], "signal"),
        ("zero_crossings_funct_1d", "funct1d", ["signal"], "indices"),
        # {"max": indices, "min": indices} の dict — 両極値は同格で片方だけ剥がすと
        # 情報が欠けるため table 宣言(連鎖ファザー wave-4 TYPEMISS 修正)
        ("local_min_max_funct_1d", "funct1d", ["signal"], "table"),
        ("abs_funct_1d", "funct1d", ["signal"], "signal"),
        ("negate_funct_1d", "funct1d", ["signal"], "signal"),
        ("invert_funct_1d", "funct1d", ["signal"], "pairs"),
        ("scale_y_funct_1d", "funct1d", ["signal"], "signal"),
        ("transform_funct_1d", "funct1d", ["signal"], "pairs"),
        ("compose_funct_1d", "funct1d", ["signal", "signal"], "signal"),
        ("sample_funct_1d", "funct1d", ["signal"], "signal"),
        # {"shift": int, "score": float} の dict — shift と score は同格の対で
        # スカラ 1 個に潰せないため table 宣言(wave-4 TYPEMISS 修正)
        ("match_funct_1d_trans", "funct1d", ["signal", "signal"], "table"),
        ("distance_funct_1d", "funct1d", ["signal", "signal"], "measurement"),
        ("num_points_funct_1d", "funct1d", ["signal"], "measurement"),
        ("x_range_funct_1d", "funct1d", ["signal"], "pairs"),
        ("y_range_funct_1d", "funct1d", ["signal"], "pairs"),
        ("get_pair_funct_1d", "funct1d", ["signal"], "pairs"),
        ("get_y_value_funct_1d", "funct1d", ["signal"], "measurement"),
        ("funct_1d_to_pairs", "funct1d", ["signal"], "pairs"),
    ],
    "signal": [  # センサー/音声系列の信号処理(dsp)
        ("lowpass", "dsp", ["signal"], "signal"),
        ("highpass", "dsp", ["signal"], "signal"),
        ("bandpass", "dsp", ["signal"], "signal"),
        ("envelope", "dsp", ["signal"], "signal"),
        ("rms", "dsp", ["signal"], "measurement"),   # frame= で framewise 配列
        ("resample", "dsp", ["signal"], "signal"),
        ("spectrum", "dsp", ["signal"], "pairs"),
        ("spectrogram", "dsp", ["signal"], "image2d"),
        ("zero_crossing_rate", "dsp", ["signal"], "measurement"),
        ("find_peaks", "dsp", ["signal"], "indices"),
        ("signal_features", "dsp", ["signal"], "table"),
    ],
    "io": [  # 音声/波形の入出力
        ("read_wav", "dsp", ["file"], "signal"),
        ("write_wav", "dsp", ["signal"], "file"),
        ("read_audio", "dsp", ["file"], "signal"),
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


OPS1D = _build()

#: 宣言 out 型の値を実返却から取り出すアダプタ(ops3d.RESULT_ADAPTERS と同思想)
RESULT_ADAPTERS = {
    "resample": lambda r: r[0],       # (signal, new_rate)
    "spectrogram": lambda r: r[2],    # (freqs, times, S) — S が本体
    # --- pairs の正典 = **(N,2)**(2026-09-02)---------------------------------- #
    # それまで tools/chain_fuzz.TYPE_CHECKS["pairs"] は ``lambda v: True`` で、
    # 何を返しても TYPEMISS にならなかった。正典は消費側 6 op を実行して確定:
    # (N,2) か「同じ長さの 1-D 2 本のタプル」だけを受け、**(2,N) は名指しで拒否**
    # される("pairs: must be (N, 2) or a 2-tuple of equal-length 1-D arrays")。
    "spectrum": lambda r: np.stack(r, axis=1) if isinstance(r, tuple) else r,
    # invert_funct_1d は {"x": ..., "y": ...}(逆関数の (y, x) 対)を dict で返す。
    # 中身は正直な対なので関数側は変えず、宣言型を名乗る call() 側で (N,2) に組む
    "invert_funct_1d": lambda r: np.stack([r["x"], r["y"]], axis=1)
    if isinstance(r, dict) else r,
    # x_range / y_range は (lo, hi) の 2 スカラ、get_pair は (x, y) の 1 対。
    # どれも「対が 1 つ」なので (1,2) にする — reprconv.polar_to_cscalar が
    # 「1 つの複素スカラの極形式は (1,2)」と要求しており、この repo で
    # 「対 1 つ」を表す形は (1,2) だと消費側が実行時に言っている(実測)
    "x_range_funct_1d": lambda r: np.asarray(r, np.float64).reshape(1, 2),
    "y_range_funct_1d": lambda r: np.asarray(r, np.float64).reshape(1, 2),
    "get_pair_funct_1d": lambda r: np.asarray(r, np.float64).reshape(1, 2),
}


def call(name, *args, **kwargs):
    """op を呼び、目録の out 型どおりの値を返す(補助情報つきタプルは剥がす)。"""
    result = OPS1D[name]["func"](*args, **kwargs)
    adapter = RESULT_ADAPTERS.get(name)
    return adapter(result) if adapter is not None else result


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPS1D.items() if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable)。"""
    return OPS1D[name]["func"]


def info(name):
    """op のメタ情報。"""
    return OPS1D[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPS1D.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"ops1d: {len(OPS1D)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for c in categories():
        print(f"  [{c}] {len(list_ops(c))} ops")
