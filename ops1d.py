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
import dsp
import funct1d

_MOD = {"funct1d": funct1d, "dsp": dsp}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   種別語彙: signal(1-D array)/ pairs((x,y))/ indices / measurement / file
_CATALOG = {
    "function": [  # HALCON funct_1d 対応の関数処理(プロファイル計測の後段)
        ("create_funct_1d_array", "funct1d", ["signal"], "signal"),
        ("create_funct_1d_pairs", "funct1d", ["signal", "signal"], "pairs"),
        ("smooth_funct_1d_gauss", "funct1d", ["signal"], "signal"),
        ("smooth_funct_1d_mean", "funct1d", ["signal"], "signal"),
        ("derivate_funct_1d", "funct1d", ["signal"], "signal"),
        ("integrate_funct_1d", "funct1d", ["signal"], "signal"),
        ("zero_crossings_funct_1d", "funct1d", ["signal"], "indices"),
        ("local_min_max_funct_1d", "funct1d", ["signal"], "indices"),
        ("abs_funct_1d", "funct1d", ["signal"], "signal"),
        ("negate_funct_1d", "funct1d", ["signal"], "signal"),
        ("invert_funct_1d", "funct1d", ["signal"], "pairs"),
        ("scale_y_funct_1d", "funct1d", ["signal"], "signal"),
        ("transform_funct_1d", "funct1d", ["signal"], "pairs"),
        ("compose_funct_1d", "funct1d", ["signal", "signal"], "signal"),
        ("sample_funct_1d", "funct1d", ["signal"], "signal"),
        ("match_funct_1d_trans", "funct1d", ["signal", "signal"], "measurement"),
        ("distance_funct_1d", "funct1d", ["signal", "signal"], "measurement"),
        ("num_points_funct_1d", "funct1d", ["signal"], "measurement"),
        ("x_range_funct_1d", "funct1d", ["signal"], "measurement"),
        ("y_range_funct_1d", "funct1d", ["signal"], "measurement"),
        ("get_pair_funct_1d", "funct1d", ["signal"], "measurement"),
        ("get_y_value_funct_1d", "funct1d", ["signal"], "measurement"),
        ("funct_1d_to_pairs", "funct1d", ["signal"], "pairs"),
    ],
    "signal": [  # センサー/音声系列の信号処理(dsp)
        ("lowpass", "dsp", ["signal"], "signal"),
        ("highpass", "dsp", ["signal"], "signal"),
        ("bandpass", "dsp", ["signal"], "signal"),
        ("envelope", "dsp", ["signal"], "signal"),
        ("rms", "dsp", ["signal"], "signal"),
        ("resample", "dsp", ["signal"], "signal"),
        ("spectrum", "dsp", ["signal"], "pairs"),
        ("spectrogram", "dsp", ["signal"], "image2d"),
        ("zero_crossing_rate", "dsp", ["signal"], "measurement"),
        ("find_peaks", "dsp", ["signal"], "indices"),
        ("signal_features", "dsp", ["signal"], "measurement"),
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
