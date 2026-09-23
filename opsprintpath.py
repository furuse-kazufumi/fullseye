# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsprintpath —— 3D プリンタのデータ(G-code / 3MF / スライス / 層画像の検査)を扱う op の統一レジストリ。

実体は ``printpath.py``(11 op / 4 カテゴリ、numpy + 標準ライブラリ)。台帳の役目は 3 つ:
docs/ops へノートを出す・連鎖ファザーに食わせる・宣言型と素の返りを橋渡しする。

使い方::

    import opsprintpath
    t = opsprintpath.call("gcode_read", "part.gcode")
    mm3 = opsprintpath.call("gcode_extrusion_volume", t)
    img = opsprintpath.call("gcode_layer_image", t, 12)

型は全部既存の語彙: G-code の線分と輪郭は ``table``(列の辞書)、メッシュは ``mesh`` = (V, F)、層のラスタは
``image2d``、層の積みは ``voxel``、体積と時間は ``measurement``、書いたパスは ``text``。新語は作らない ——
「混ぜたときに例外でなく、もっともらしく間違うか」で見ると、線分の表と輪郭の表は列名が違うので受け側が
名指しで拒む(fail-closed)。
"""
import printpath

_MOD = {"printpath": printpath}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # G-code —— 読む・書く・量る・描く
    "gcode": [
        ("gcode_read", "printpath", ["text"], "table"),
        ("gcode_write", "printpath", ["table", "text"], "text"),
        ("gcode_extrusion_volume", "printpath", ["table"], "measurement"),
        ("gcode_time_estimate", "printpath", ["table"], "measurement"),
        ("gcode_layer_image", "printpath", ["table"], "image2d"),
    ],
    # スライス —— 形 → 層 → 経路
    "slice": [
        ("mesh_slice_contours", "printpath", ["mesh"], "table"),
        ("mesh_slice_stack", "printpath", ["mesh"], "voxel"),
        ("contours_to_gcode", "printpath", ["table"], "table"),
    ],
    # 3MF —— 読む・書く
    "format": [
        ("read_3mf", "printpath", ["text"], "mesh"),
        ("write_3mf", "printpath", ["text", "mesh"], "text"),
    ],
    # 濃淡 → 1 本の閉じた線(2026-09-22)。点描 → 巡回路 → 打ち直し → 濃淡の検算。
    # 巡回路は**閉じている**ので fourierdesc の複素フーリエ 3 op にそのまま載る。
    "stroke": [
        ("stipple_points_from_image", "printpath", ["image2d"], "pairs"),
        ("stipple_energy", "printpath", ["image2d", "pairs"], "measurement"),
        ("stroke_tour_closed", "printpath", ["pairs"], "pairs"),
        ("mst_length", "printpath", ["pairs"], "measurement"),
        ("stroke_resample_closed", "printpath", ["pairs"], "pairs"),
        ("stroke_tone_error", "printpath", ["image2d", "pairs"], "table"),
    ],
    # ★様式化(2026-09-23)。「きれいな絵」を返す op ではなく、**保った量と捨てた
    # 量を数で返す** op にする —— 既存の NPR ライブラリは絵しか返さない。真値は
    # モアレ周期の予言(描く前に分かる)、被覆率 w/d の閉形式、既知の縞の向き、
    # Lloyd の単調減少(既存 stipple_energy が測る)、セル平均の L2 最適性。
    # 点描の 6 op と同じ族に入れたのは、どちらも「濃淡を離散的な墨に落とす」
    # 同じ問題で、入口も出口も同じ語彙(image2d / pairs)だから。
    "npr": [
        ("halftone_screen", "printpath", ["image2d"], "image2d"),
        # 2 版のうなり。描く前に周期と向きを言える(実測との比 0.986)。
        ("halftone_moire_period", "printpath", [], "table"),
        ("engrave_lines", "printpath", ["image2d"], "image2d"),
        ("hatch_field", "printpath", ["image2d"], "image2d"),
        ("mosaic_tiles_sites", "printpath", ["image2d"], "pairs"),
        ("mosaic_tiles_render", "printpath", ["image2d", "pairs"], "image2d"),
    ],
    # 検査 —— 観測した層と期待の層
    "inspect": [
        ("print_layer_defect_map", "printpath", ["image2d", "image2d"], "image2d"),
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


OPSPRINTPATH = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSPRINTPATH.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**この族はどの op もタプルを返さない**(mesh は (V, F) のタプルそのものが型)。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSPRINTPATH[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSPRINTPATH[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSPRINTPATH[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSPRINTPATH.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsprintpath: {len(OPSPRINTPATH)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
