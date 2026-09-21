# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opslive4d —— 生きている組織の 3D+t を古典手法だけで「短い 3D 動画像」にする op の統一レジストリ。

実体は ``live4d.py``(14 op / 5 カテゴリ)。台帳の役目は 3 つ:
docs/ops へノートを出す・連鎖ファザーに食わせる・宣言型と素の返りを橋渡しする。

使い方::

    import opslive4d
    opslive4d.list_ops("time")
    s = opslive4d.call("volseq_synth_beating", (24, 32, 32), n_frames=24, amplitude=0.1)
    big = opslive4d.call("volseq_magnify_motion", s, alpha=8.0, f_lo=0.06, f_hi=0.12, fps=1.0)
    gif = opslive4d.call("volseq_render_orbit", big, n_frames=36, loops=3)

型の語彙は 1 語だけ足す: ``volseq`` = 体積の時系列 ``(T, Z, Y, X)``(T >= 2)。分ける基準は repo 共通の
1 つ ——「混ぜたときに例外ではなく、もっともらしく間違った数値が出るか」。``volseq`` を ``voxel`` や
``video`` の op に渡すと ndim が違って例外になる(黙って間違わない)ので、実は分けなくても事故は起きない。
それでも語を立てるのは、**この族の 8 op が同じ形の入力を受けて、ファザーが種を持てるようにするため**
(語が無いと「産む op が無い型」になり、連鎖の中で一度も到達しない)。既存語は ``video`` (T, H, W)、
``voxel`` (Z, Y, X)、``flow_dense`` (3, Z, Y, X)、``rgb``、``rgbvideo``。

``video`` を受ける ``video_interpolate_flow`` には自動の型付き橋(tb_*)を架けない(``_OP_BRIDGE_SKIP``):
橋が渡す動画は 2-D 画像 1 枚を積んだ静止クリップで、補間しても同じフレームが増えるだけだから。
"""
import live4d

_MOD = {"live4d": live4d}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 生成 —— 真値つきの合成系列(拍動する殻 / 分かれる塊)。テストと PoC の入力、ファザーの種
    "synth": [
        ("volseq_synth_beating", "live4d", [], "volseq"),
        ("volseq_synth_dividing", "live4d", [], "volseq"),
    ],
    # 系列 → 動画 —— videocube(空間 × 時間の立方体)への橋
    "series": [
        ("volseq_mip_video", "live4d", ["volseq"], "video"),
        ("volseq_cut_video", "live4d", ["volseq"], "video"),
    ],
    # 流れ —— 3 次元 Lucas–Kanade、速さ、粒子の軌跡
    "flow": [
        ("vol_flow_3d", "live4d", ["voxel", "voxel"], "flow_dense"),
        ("volseq_speed", "live4d", ["volseq"], "volseq"),
        ("volseq_pathline_render", "live4d", ["volseq"], "rgb"),
        ("volseq_pathline_orbit", "live4d", ["volseq"], "rgbvideo"),
    ],
    # 時間 —— 補間(時間の超解像)と増幅(Eulerian)
    "time": [
        ("video_interpolate_flow", "live4d", ["video"], "video"),
        ("volseq_interpolate_flow", "live4d", ["volseq"], "volseq"),
        ("volseq_magnify_motion", "live4d", ["volseq"], "volseq"),
    ],
    # 描く —— 時間を進めながら回す、焦点掃引から高さ場の動画
    "render": [
        ("volseq_render_orbit", "live4d", ["volseq"], "rgbvideo"),
        ("focus_sweep_height_video", "live4d", ["volseq"], "video"),
        ("focus_sweep_surface_video", "live4d", ["volseq"], "rgbvideo"),
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


OPSLIVE4D = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSLIVE4D.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**この族はどの op もタプルを返さない**ので空。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSLIVE4D[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSLIVE4D[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSLIVE4D[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSLIVE4D.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opslive4d: {len(OPSLIVE4D)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
