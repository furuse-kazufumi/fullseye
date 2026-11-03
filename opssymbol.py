# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opssymbol —— 記号の読み取り(1-D / 2-D コード・印字品質・読み取りの POD・OCR)の統一レジストリ。

Symbol reading for inspection: encode and decode 1-D bar codes (EAN-13 / UPC-A /
Code 128 / Code 39 / ITF) and 2-D codes (QR Code, Data Matrix ECC200), simulate how a
camera sees a printed or marked symbol, grade its print quality (the published
structure of the 1-D and 2-D verification methods), measure the read-rate POD under a
swept physical degradation, and read limited-charset text (lot numbers, date codes)
with classical OCR (built-in 5x7 dot-matrix and stroke fonts, k-NN with rejection; no
deep-learning training), whose legibility POD uses the same chain.

呼び出し例::

    import fullseye as fs

    sym = fs.ledger.dm_encode("LOT2026-1103")                 # 16x16 の Data Matrix
    img = fs.ledger.render_symbol(sym, 5.0, rotate_deg=30.0, dot=0.8)   # 刻印の点、30° 回転
    img = fs.ledger.capture_degrade(img, defocus_px=3.0, full_well_e=20000.0,
                                    read_noise_e=10.0, bits=8, seed=1)
    print(fs.ledger.dm_read(img)["text"])
    g = fs.ledger.grade_datacode2d(img, expected_text="LOT2026-1103")
    print(g["letter"], g["limiting"])

出力は ``LOT2026-1103`` と ``C ['symbol_contrast']``(デフォーカス 3 px のぼけで点の底が
浅くなり、シンボルコントラストが C に落ちる)。``tests/test_opssymbol.py`` がこの例を実行し、
読めることと等級を確かめる。

## なぜこの族か(2026-11-03)

監査(2026-11-03 の完成度監査、リポジトリ外の資料)で、1-D は既存の ``decode_barcode`` が
**暗い棒を数えるだけ**、2-D コードは語彙が**全層ゼロ**、印字品質の等級は**全層ゼロ**、
OCR は文字領域の検出(``opstext``)と期待文字との照合(``glyphops``)だけだった。
差別化の型: 復号の土台は標準(自前 + zxing-cpp を独立な第 2 の実装として仲介)、その上に
Fullseye だけの層 —— **物理劣化を振ったときの読み取りの POD**(既存の MIL-HDBK-1823A の
``pod`` 族を使う)と、**印字品質の等級**(RAD の文献 0 件の空白地帯)。

## 型語彙: **新語をひとつも作らない**

* ``table``  —— シンボルの表(``encode_*`` の返り: 幅の列 / モジュール格子と符号語の対応)、
  読み取り・等級・POD の結果。
* ``image2d`` —— 撮った(合成した)画像。``render_symbol`` が table → image2d の入口、
  読み取り・等級はすべて image2d → table。
* ``signal`` —— 1 本の走査線(反射率の 1-D 列)。
* ``matrix`` —— 0/1 のモジュール格子(``qr_decode_modules`` / ``dm_decode_modules``)。
* ``scalar`` —— 検査数字。
* OCR: 描いた行と模型は ``table``、1 字の特徴量は ``signal``、特徴量の束は ``matrix``。
"""
import barcode1d
import dmsym
import ocrclassic
import qrsym
import symbolpod
import symgrade
import symrender
import symzxing

_MOD = {"barcode1d": barcode1d, "qrsym": qrsym, "dmsym": dmsym, "symrender": symrender,
        "symgrade": symgrade, "symbolpod": symbolpod, "symzxing": symzxing,
        "ocrclassic": ocrclassic}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 1-D バーコード。真値 = 符号化した文字列そのもの。
    "barcode1d": [
        ("encode_barcode1d", "barcode1d", [], "table"),
        ("ean_check_digit", "barcode1d", [], "scalar"),
        ("barcode_scan_profiles", "barcode1d", ["image2d"], "table"),
        ("decode_barcode_profile", "barcode1d", ["signal"], "table"),
        ("read_barcode1d", "barcode1d", ["image2d"], "table"),
    ],
    # 2-D コード(QR / Data Matrix)。Reed-Solomon は symrs(直した語数を返す)。
    "datacode2d": [
        ("qr_encode", "qrsym", [], "table"),
        ("qr_decode_modules", "qrsym", ["matrix"], "table"),
        ("qr_locate", "qrsym", ["image2d"], "table"),
        ("qr_sample", "qrsym", ["image2d"], "table"),
        ("qr_read", "qrsym", ["image2d"], "table"),
        ("dm_encode", "dmsym", [], "table"),
        ("dm_decode_modules", "dmsym", ["matrix"], "table"),
        ("dm_locate", "dmsym", ["image2d"], "table"),
        ("dm_sample", "dmsym", ["image2d"], "table"),
        ("dm_read", "dmsym", ["image2d"], "table"),
    ],
    # 撮像のシミュレーション(印字 → 投影 → 照明 → レンズ → センサ)。
    "symbol_capture": [
        ("render_symbol", "symrender", ["table"], "image2d"),
        ("capture_degrade", "symrender", ["image2d"], "image2d"),
    ],
    # 印字品質の等級(1-D は走査線、2-D はモジュール格子)。
    "print_quality": [
        ("grade_barcode_profile", "symgrade", ["signal"], "table"),
        ("grade_barcode1d", "symgrade", ["image2d"], "table"),
        ("grade_datacode2d", "symgrade", ["image2d"], "table"),
    ],
    # 読み取りの POD(劣化を掃引 → 成功 / 誤読 / 不能 → pod_hitmiss_fit)。
    "read_pod": [
        ("symbol_read", "symbolpod", ["image2d"], "table"),
        ("symbol_read_trials", "symbolpod", ["table"], "table"),
        ("symbol_read_pod", "symbolpod", ["table"], "table"),
    ],
    # 古典的な OCR(限られた字種、内蔵の 5x7 ドット / 線の書体、k 最近傍 + 棄却)。学習は DL でない。
    "ocr": [
        ("ocr_font", "ocrclassic", [], "table"),
        ("ocr_render_text", "ocrclassic", [], "table"),
        ("ocr_segment_line", "ocrclassic", ["image2d"], "table"),
        ("ocr_features", "ocrclassic", ["image2d"], "signal"),
        ("ocr_train", "ocrclassic", [], "table"),
        ("ocr_classify", "ocrclassic", ["matrix", "table"], "table"),
        ("ocr_read_line", "ocrclassic", ["image2d", "table"], "table"),
        ("ocr_score", "ocrclassic", [], "table"),
        ("ocr_read_trials", "symbolpod", ["table"], "table"),
    ],
    # 外部の読み取り器の仲介(optional extra ``symbols`` = zxing-cpp、Apache-2.0)。
    "symbol_bridge": [
        ("read_symbols_zxing", "symzxing", ["image2d"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = fn.__doc__.strip().splitlines()[0] if fn is not None and fn.__doc__ else ""
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSSYMBOL = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSSYMBOL.items() if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。空 —— 全 op が宣言どおりの型(dict = table、
#: ndarray = image2d、int = scalar)を素で返す。
RESULT_ADAPTERS = {}


def get(name):
    """op 名から関数を引く(無ければ KeyError)。"""
    return OPSSYMBOL[name]["func"]


def info(name):
    """op の登録情報(category / module / in / out / doc)。"""
    m = OPSSYMBOL[name]
    return {k: m[k] for k in ("category", "module", "in", "out", "doc")}


def call(name, *args, **kwargs):
    """登録名で呼ぶ。"""
    return get(name)(*args, **kwargs)


def missing():
    """台帳に在るが実体が無い op(ゼロであることを試験が確かめる)。"""
    return [n for n, m in OPSSYMBOL.items() if m["func"] is None]
