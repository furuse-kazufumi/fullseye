# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""公開 PoC にメーカー名・社名・社名が分かる製品名 / 型番を書かない門(2026-10-15、ユーザーの規則)。

## 規則

公開側の PoC 関連 —— ``examples/poc_*.py``、``docs/articles/assets/poc/**``(figures.json と表)、
``docs/capabilities/*.md``、展示(``docs/articles/exhibits/**``・展示館の記事)、ViEW2026 のページ、
Qiita の記事、CHANGELOG の PoC 項目、examples の索引の PoC 行、PoC が呼ぶ op の docstring —— に、
メーカー名・社名・社名が分かる製品名 / 型番を書かない。置き換えは一般名(「市販の偏光イメージセンサ」
「公開の硝材カタログ値」「BK7 相当のホウケイ酸クラウン」、硝材は n_d・ν_d の 6 桁コード)。

* **例外 1: HALCON** —— 比較の物差しとして名前を出してよい(ユーザー判断)。だから語彙に入れていない
  (発売元の社名は語彙にある)。
* **例外 2: 出典表示** —— ライセンス上の義務(CC BY 等)や引用の行。DOI か URL を含む行、ライセンス名
  (CC BY / CC-BY / CC0)を含む行、明示の印 ``出典表示`` を含む行は数えない。
* **例外 3: 名指しの許可**(:data:`ALLOWED_PHRASES`)—— 理由つきで 1 件ずつ。

## 対象外(理由つき)

* **RAG の層**(ユーザー判断 2026-10-15「RAG 側には記載していてもいい」): 製品名・社名から汎用 op へ
  辿り着かせるための索引。``docs/i18n/op_context.json``、``docs/OP_SEARCH.json`` の文脈列、文献層
  ``docs/literature/**``、評価問題集 ``tests/data/rag_eval_queries.json`` など —— :data:`RAG_EXCLUDED`。
  対象範囲を組む関数はこれらを**読まない**ことを :func:`test_rag_layer_is_outside_the_scope` で固定する。
* ライブラリの実装とデータ表(``materials_data.py`` の硝材のキー、``optscene`` のセンサ台帳、
  ``acquire`` のカメラ SDK、``drivehumanoid.MENAGERIE_HUMANOIDS`` の外部データのディレクトリ名)——
  外部のファイルや装置を開く識別子で、公開 PoC の文ではない。PoC はこれらを**キーをソースに書かずに**
  引く(硝材は n_d・ν_d から、センサは台帳の並び順の番号で、人型は「人型 k」)。

## 数え方(配られる側から)

対象のファイル群を repo から列挙し(登録簿や索引から辿らない)、各グループに**件数の下限**を置く
—— 範囲が黙って縮んで 0 件で素通りしないため(memory: 範囲を自分で読む門は黙って縮む)。

## 正直な限界

図に焼き込まれた文字(PNG / GIF の画素)は OCR しない。焼き込まれる文字の出どころ —— PoC のソースの
文字列と、表(CSV / TSV)・figures.json —— を数えている。ライブラリのデータから図の凡例に流れる名前
(例: 台帳のキーをそのまま凡例にする)は、表に出ない限りこの門をすり抜ける。新しい PoC で台帳のキーを
図に出すときは、表にも同じ名前を出すか、番号・一般名に置き換えること。
"""
from __future__ import annotations

import ast
import os
import re
import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------- #
# 語彙表(拡張しやすいようにモジュール定数。足すときは下の自己検査に 1 行足す) #
# --------------------------------------------------------------------------- #

#: 大文字小文字を区別しない社名・ブランド名(英字)。小文字にしても一般語にならない語だけ。
#: 前後は英数字でない境界(``_`` は境界扱い: ``ZEONEX_E48R`` や ``unitree_g1`` も当てる)。
COMPANY_NAMES_CI: tuple[str, ...] = (
    # カメラ・レンズ・光学
    "Sony", "Nikon", "Fujifilm", "Fujinon", "Olympus", "Panasonic", "Leica", "Hasselblad", "Pentax", "Ricoh",
    "Tamron", "Zeiss", "Basler", "FLIR", "Teledyne", "DALSA", "uEye", r"Allied\s+Vision", r"Point\s*Grey",
    "Baumer", "Hamamatsu", "Andor", "Photometrics", "Keyence", "Cognex", "Omron", "MVTec", "Matrox",
    "Schott", "CDGM", "Sumita", r"Edmund\s+Optics", "Thorlabs", "Navitar", "Computar", "Kowa", "Moritex",
    "Ximea", "Photonfocus", "Photron", r"Vision\s+Research", "Specim", "Headwall", "Resonon", "Cubert",
    r"Princeton\s+Instruments", r"Ocean\s+(?:Optics|Insight)", "Avantes", "Ophir", r"Spectra-Physics", "Trumpf",
    "Lumentum", "Heraeus", "Polytec", "Renishaw", "Heidenhain", "Mitutoyo", "Zygo", "Keysight", "Tektronix",
    "Agilent", "Bruker", "Gatan", r"Thermo\s+Fisher", "JEOL", "Kodak", "Agfa", "X-Rite", "Datacolor",
    "GretagMacbeth", "Calibrite", "Imatest", "DxOMark", "Topcon", "Sokkia", "Sekonic", "Prophesee", "iniVation",
    "Lytro", "Raytrix", "Arducam", r"Konica\s*Minolta", "Minolta", "Stereolabs", "RealSense", "Kinect",
    # センサ・半導体・照明
    "onsemi", r"ON\s+Semiconductor", "Gpixel", "OmniVision", "Samsung", "STMicro\\w*", "Infineon", "Melexis",
    "Excelitas", "Nichia", "Osram", "Lumileds", "Philips", "Exmor", "Pregius", "STARVIS", "Blackfly", "Grasshopper",
    "Lepton", "ASML", r"Applied\s+Materials", r"Lam\s+Research", r"Tokyo\s+Electron", "Lasertec", "Advantest",
    "Hitachi", "Toshiba", "Mitsubishi", "Kyocera", "Renesas", "Epson", "Fujitsu", "Ushio", "Shimadzu", "Horiba",
    "Qualcomm", "NVIDIA", "Intel", "Microsoft", "Google", "Huawei", "Xiaomi", "Hikvision", "Dahua", "Logitech",
    "GoPro", "DJI", "Honeywell", "Beckhoff", "Yokogawa", "Fluke", "Optris", "Datalogic",
    # 測域・車・ロボット
    "Velodyne", "Ouster", "Hesai", "Livox", "Luminar", "Mobileye", "Waymo", "Toyota", "Honda", "Nissan", "Denso",
    "Valeo", "Fanuc", "Yaskawa", "KUKA", r"Universal\s+Robots", r"Boston\s+Dynamics", r"Agility\s+Robotics",
    "Unitree", r"Booster\s+T1", "booster_t1", r"Fourier\s+N1", "fourier_n1", r"PAL\s+Robotics", "pal_talos",
    "TALOS", "Apptronik", "ROBOTIS",
    # ソフト
    "MathWorks", "MATLAB", "Simulink", "Adobe", "Photoshop", "Autodesk", "Ansys", "Zemax", "OpticStudio",
    "Synopsys", r"CODE\s+V", "COMSOL", "Lumerical", "Dassault", "SolidWorks", r"Unreal\s+(?:Engine|Editor)",
    # 素材の商標(一般名がある)
    "Zeonex", r"Zeon\s+Corp\w*", "Pyrex", "Zerodur", "Borofloat", "Suprasil", "Infrasil", "Spectralon", "Teflon",
    "Kapton", "Mylar", "Plexiglas", "Perspex", "Lexan", "Delrin", r"Gorilla\s+Glass", "Iupilon", "Inconel",
    "ColorChecker",
)

#: 大文字小文字を区別する社名(小文字や別の綴りだと一般語・単位・人名になる語)。
COMPANY_NAMES_CS: tuple[str, ...] = (
    "Canon",        # canon(規範)
    "Apple",        # apple
    "Tesla",        # tesla(単位 T)
    "Siemens",      # siemens(単位 S)。解像チャートの通称にも入るので「星形チャート」と書く
    "LUCID",        # lucid
    "KLA",
    "Hoya", "HOYA",  # 人名 Hoya は稀だが、全大文字・先頭大文字だけ
    "OHARA",        # Ohara は論文の著者名(O'Hara / Ohara)と区別できないので全大文字だけ
    "Cree",         # cree(言語名)
    "Corning",
    "Zebra Technologies",
)

#: 社名が分かる型番・硝材の銘柄(パターン)。硝材の銘柄の接頭辞はカタログごとに決まっていて、
#: 名前だけで発売元が分かる。慣用の分類名(BK7・SF11・F2・SK16 など接頭辞の無い古い名前)は
#: 「BK7 相当」のように分類名として使ってよい(ユーザーの例示)ので当てない。
PRODUCT_CODES: tuple[str, ...] = (
    r"N-(?:BK|SF|LAK|LASF|FK|PK|SK|BAF|BASF|KZFS|F|LAF|PSK|SSK|BAK|BALF|ZK|KF|K)\d+[A-Z]?",   # 硝材(N- 系)
    r"P-(?:SF|SK|LAK|LASF|BK)\d+[A-Z]?",
    r"S-(?:BSL|TIH|LAH|FSL|NSL|BAL|LAL|NPH|PHM|FPL|BAH|BSM|TIM|LAM)\d+",                    # 硝材(S- 系)
    r"H-(?:ZF|K|ZK|LAK|ZLAF|QK|BAK|F|ZBAF|LAF)\d+[A-Z]?", r"D-ZK\d+",                        # 硝材(H- 系)
    r"E-FD\d+", r"FD\d{2}", r"FCD\d+", r"M-TAC\d+", r"TAC\d+", r"TAF\d+", r"BSC7",          # 硝材(その他)
    r"ZEONEX_E48R",
    r"IMX\d{3}[A-Z]*", r"ICX\d{3}[A-Z]*",                                                     # イメージセンサの型番
    r"BFS-U3-[0-9A-Z]+", r"TRI\d{3}S-[A-Z]+",                                                # カメラの型番
)

#: 日本語・カタカナの社名(語境界が無いので、一般語と重ならない形だけ。「ショット」「シャープ」
#: 「シグマ」は shot noise / sharp / σ と重なるので社名と分かる形 ``ショット社`` などにする)。
COMPANY_NAMES_JA: tuple[str, ...] = (
    "ソニー", "キヤノン", "キャノン", "ニコン", "富士フイルム", "フジフイルム", "フジノン", "オリンパス", "パナソニック",
    "ライカ", "ハッセルブラッド", "ペンタックス", "リコー", "タムロン", "ツァイス", "バスラー", "キーエンス", "オムロン",
    "コグネックス", "ショット社", "オハラ社", "株式会社オハラ", "ホーヤ", "浜松ホトニクス", "ミツトヨ", "シーシーエス",
    "日亜化学", "東京エレクトロン", "レーザーテック", "アドバンテスト", "ファナック", "安川電機", "デンソー", "トヨタ",
    "本田技研", "日産自動車", "島津製作所", "堀場製作所", "日立", "東芝", "三菱電機", "京セラ", "村田製作所", "ルネサス",
    "エプソン", "富士通", "ウシオ電機", "小糸製作所", "コニカミノルタ", "トプコン", "テスラ社", "グーグル", "アップル社",
    "マイクロソフト", "インテル", "エヌビディア", "ボッシュ", "テレダイン", "モリテックス", "興和", "ユニツリー",
    "エムブイテック", "マスワークス", "ゼオネックス", "日本ゼオン",
)

#: 名指しで許す言い回し(正規表現, 理由)。1 件ずつ理由を書く。
ALLOWED_PHRASES: tuple[tuple[str, str], ...] = (
    (r"Google gemini-2\.5-flash-image",
     "AI 生成の模擬データの来歴の開示(どのモデルで作ったかを隠さない)。社名を消すと来歴が追えない"),
)

#: 出典表示の行(この行の中は数えない): DOI・URL・ライセンス名・明示の印。
ATTRIBUTION_LINE = re.compile(r"https?://|doi\.org|\bdoi:|\bDOI\b|CC[ -]BY|\bCC0\b|出典表示", re.IGNORECASE)

_B = r"(?<![A-Za-z0-9])"
_E = r"(?![A-Za-z0-9])"
PATTERN = re.compile(
    "|".join([_B + "(?i:" + w + ")" + _E for w in COMPANY_NAMES_CI]
             + [_B + w + _E for w in COMPANY_NAMES_CS]
             + [_B + w + _E for w in PRODUCT_CODES]
             + [re.escape(w) for w in COMPANY_NAMES_JA]))
_ALLOWED = [re.compile(p) for p, _why in ALLOWED_PHRASES]

#: N- の無い硝材の型番(2026-10-25)。公開の動く 3-D(docs/anim3d)の画面の文字だけに当てる —— 全体の語彙に
#: 足すと、材料表のキーとして型番を書く既存の公開 PoC(poc_material_optical_library ほか)で 110 件超が当たる
#: (別の便で扱う)。単独の F / K + 数字は焦点距離 f2・F2 や係数 K1 と重なるので入れない(2 文字以上の系列名
#: だけ)。大文字小文字を区別する(sf2 のような変数名は当てない)。
PRODUCT_CODES_BARE: tuple[str, ...] = (
    r"(?:BK|SF|LASF|LAK|LAF|BAF|BASF|BAK|BALF|KZFS|PSK|SSK|SK|FK|PK|ZK|KF)\d+[A-Z]?",
)
PATTERN_BARE = re.compile("|".join(_B + w + _E for w in PRODUCT_CODES_BARE))


def find_company_names(text: str, bare: bool = False) -> list[tuple[int, str, str]]:
    """``text`` の中の社名・銘柄名を (行番号, 語, 行) の列で返す(出典表示の行と許可の言い回しは除く)。

    ``bare=True`` なら N- の無い硝材の型番(``PRODUCT_CODES_BARE``)も数える(公開の動く 3-D の範囲で使う)。
    """
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if ATTRIBUTION_LINE.search(line):
            continue
        masked = line
        for a in _ALLOWED:
            masked = a.sub(lambda m: " " * len(m.group(0)), masked)
        for m in PATTERN.finditer(masked):
            out.append((i, m.group(0), line.strip()[:160]))
        if bare:
            hit = [m.span() for m in PATTERN.finditer(masked)]
            for m in PATTERN_BARE.finditer(masked):
                if not any(a <= m.start() < b for a, b in hit):     # N-BK7 の中の BK7 を二重に数えない
                    out.append((i, m.group(0), line.strip()[:160]))
    return out


# --------------------------------------------------------------------------- #
# 対象範囲(配られる側のファイルから組む)                                       #
# --------------------------------------------------------------------------- #

#: RAG の層(対象外、ユーザー判断 2026-10-15)。範囲を組む関数がここを読まないことを門にする。
RAG_EXCLUDED: tuple[str, ...] = (
    "docs/i18n/op_context.json", "docs/OP_SEARCH.json", "docs/literature", "tests/data/rag_eval_queries.json",
)

_TEXT_SUFFIXES = (".md", ".json", ".csv", ".tsv", ".txt", ".html", ".py")

#: グループごとの件数の下限(2026-10-15 の実数より少し下)。範囲が黙って縮んだら赤。
SCOPE_FLOORS = {
    "poc_scripts": 230,          # examples/poc_*.py(実数 236)
    "poc_assets": 850,           # docs/articles/assets/poc/** の文字のファイル(figures.json と表、実数 896)
    "poc_figures_json": 230,     # そのうち figures.json(実数 236)
    "capabilities": 58,          # docs/capabilities/*.md + docs/CAPABILITIES*.md(実数 63)
    "exhibits": 35,              # docs/articles/exhibits/** + 展示館の記事(実数 38)
    "articles": 20,              # docs/articles/*.md(Qiita の記事、展示館の記事を除く。実数 22)
    "view2026": 7,               # docs/view2026/**(7 言語 + exhibits.json)
    "anim3d": 1,                 # docs/anim3d/*.html(公開の動く 3-D。枝ごとに 1〜2 本: 干渉の枝は干渉・回折の 2、この枝は 1)
    "generators": 5,             # 展示・ViEW2026 の生成元
    "changelog_poc_items": 140,  # CHANGELOG の PoC 項目(実数 151)
    "examples_index_poc": 440,   # examples2d.EXAMPLES の poc_* と examples/README の poc_ 行(実数 473)
    "poc_op_docstrings": 1100,   # PoC が呼ぶ op の docstring(実数 1199)
}


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def _files(base: str, pattern: str) -> list[Path]:
    d = ROOT / base
    return sorted(p for p in d.glob(pattern) if p.is_file() and p.suffix in _TEXT_SUFFIXES) if d.is_dir() else []


def _changelog_poc_items() -> list[tuple[str, str]]:
    """CHANGELOG の箇条のうち、PoC を含む節か PoC を名指す箇条(先頭行の位置, 本文)。"""
    lines = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()
    items, sec, cur = [], "", None
    for i, line in enumerate(lines, 1):
        if line.startswith("#"):
            if cur:
                items.append((sec, cur))
            sec, cur = line, None
        elif line.startswith("- "):
            if cur:
                items.append((sec, cur))
            cur = [(i, line)]
        elif cur is not None:
            cur.append((i, line))
    if cur:
        items.append((sec, cur))
    rx = re.compile(r"PoC|poc_")
    return [("CHANGELOG.md:%d" % it[0][0], "\n".join(l for _i, l in it))
            for s, it in items if rx.search(s + "\n" + "\n".join(l for _i, l in it))]


def _examples_index_poc() -> list[tuple[str, str]]:
    sys.path.insert(0, str(ROOT))
    try:
        import examples2d
    finally:
        sys.path.remove(str(ROOT))
    out = [("examples2d.py:%s" % e["id"], "\n".join(str(v) for v in e.values() if isinstance(v, str)))
           for e in examples2d.EXAMPLES if str(e.get("id", "")).startswith("poc_")]
    readme = ROOT / "examples" / "README.md"
    out += [("examples/README.md:%d" % i, line)
            for i, line in enumerate(readme.read_text(encoding="utf-8").splitlines(), 1) if "poc_" in line]
    return out


def _poc_op_docstrings() -> list[tuple[str, str]]:
    """PoC が ``import <mod> as X`` / ``from <mod> import f`` で呼ぶ repo 直下のモジュールの関数の docstring。"""
    mods = {p.stem: p for p in ROOT.glob("*.py")}
    called: dict[str, set] = {}
    for poc in sorted((ROOT / "examples").glob("poc_*.py")):
        tree = ast.parse(poc.read_text(encoding="utf-8"))
        alias = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    if a.name in mods:
                        alias[a.asname or a.name] = a.name
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module in mods:
                called.setdefault(n.module, set()).update(a.name for a in n.names)
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in alias:
                called.setdefault(alias[n.value.id], set()).add(n.attr)
    out = []
    for m, names in sorted(called.items()):
        with warnings.catch_warnings():                 # 古いモジュールの不正なエスケープの警告は門と無関係
            warnings.simplefilter("ignore", SyntaxWarning)
            warnings.simplefilter("ignore", DeprecationWarning)
            tree = ast.parse(mods[m].read_text(encoding="utf-8"))
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names:
                out.append(("%s.py:%s" % (m, n.name), ast.get_docstring(n) or ""))
    return out


#: HTML に埋めた画像・配列の base64(長い英数字の連なり)。社名の語境界は英数字だけなので、``+Sony/`` の
#: ような偶然の並びが当たりうる —— 文の門なので、数えるのは画面に出る文字だけにする。
_PAYLOAD = re.compile(r"[A-Za-z0-9+/=]{120,}")


#: ビューアの JSON は日本語を ``\uXXXX`` に逃がす。逃がしたままだと日本語の社名(ソニー 等)が素通りするので戻す。
_U_ESC = re.compile(r"\\u([0-9a-fA-F]{4})")


def _strip_payload(text: str) -> str:
    """埋め込みの base64 を消し、JSON の ``\\uXXXX`` を文字に戻す(画面に出る文字だけを数える)。"""
    return _U_ESC.sub(lambda m: chr(int(m.group(1), 16)), _PAYLOAD.sub(" ", text))


def public_poc_scope() -> dict[str, list[tuple[str, str]]]:
    """グループ → [(場所, 本文)]。配られる側のファイルを列挙して組む(RAG の層は読まない)。"""
    def read(paths):
        return [(_rel(p), p.read_text(encoding="utf-8", errors="replace")) for p in paths]

    assets = _files("docs/articles/assets/poc", "**/*")
    exhibits = _files("docs/articles/exhibits", "**/*") + _files("docs/articles", "fullseye_poc_museum_*.md")
    gens = [ROOT / "tools" / n for n in ("build_exhibits.py", "exhibit_tile.py", "gen_exhibit_numbers.py",
                                         "gen_view2026_pages.py", "gen_view2026_thumbs.py", "gen_wingpoc_gallery.py")]
    return {
        "poc_scripts": read(_files("examples", "poc_*.py")),
        "poc_assets": read(assets),
        "poc_figures_json": read([p for p in assets if p.name == "figures.json"]),
        "capabilities": read(_files("docs/capabilities", "*.md") + _files("docs", "CAPABILITIES*.md")),
        "exhibits": read(exhibits),
        "articles": read([p for p in _files("docs/articles", "*.md")
                          if p.name != "README.md" and not p.name.startswith("fullseye_poc_museum_")]),
        "view2026": read(_files("docs/view2026", "**/*")),
        # 公開の動く 3-D(2026-10-25): 物体のラベル・説明・数値の段に硝材のカタログ名(N-BK7 等)を出さない
        "anim3d": [(loc, _strip_payload(txt)) for loc, txt in read(_files("docs/anim3d", "*.html"))],
        "generators": read([p for p in gens if p.is_file()]),
        "changelog_poc_items": _changelog_poc_items(),
        "examples_index_poc": _examples_index_poc(),
        "poc_op_docstrings": _poc_op_docstrings(),
    }


@pytest.fixture(scope="module")
def scope():
    return public_poc_scope()


def test_scope_is_not_empty(scope):
    """範囲の件数に下限 —— 0 件や半分で素通りしない。"""
    short = {k: (len(scope[k]), floor) for k, floor in SCOPE_FLOORS.items() if len(scope[k]) < floor}
    assert not short, "対象範囲が下限を割った(グループ: (実数, 下限)): %s" % short


def test_rag_layer_is_outside_the_scope(scope):
    """RAG の層(製品名から汎用 op へ辿る索引)は対象外 —— 範囲に入っていないことを固定する。"""
    places = {loc.split(":")[0] for items in scope.values() for loc, _t in items}
    leaked = sorted(p for p in places if any(p == r or p.startswith(r + "/") for r in RAG_EXCLUDED))
    assert not leaked, leaked


def test_no_company_names_in_public_pocs(scope):
    hits = []
    for group, items in scope.items():
        for loc, text in items:
            for line_no, word, line in find_company_names(text, bare=(group == "anim3d")):
                hits.append("%s:%d [%s] %r — %s" % (loc, line_no, group, word, line))
    assert not hits, ("公開 PoC に社名・銘柄名が %d 件(一般名・n_d/ν_d・番号に置き換えるか、出典表示の行に"
                      "するか、ALLOWED_PHRASES に理由つきで足す):\n" % len(hits)) + "\n".join(hits[:80])


# --------------------------------------------------------------------------- #
# 語彙の自己検査(探針): 当たるべき語に当たり、当たってはいけない語に当たらない     #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("text", [
    "偏光カメラ(Sony IMX250MZR 系)", "ZEONEX_E48R", "unitree_g1", "Fourier N1", "N-BK7 の等凸レンズ",
    "S-LAH58", "H-ZF52A", "FD60", "MATLAB の tubeplot", "Zemax の分散式", "Mobileye の RSS", "Siemens スター",
    "独 MVTec 社", "matlab", "キーエンスの照明", "IMX287 だけ食い違う", "Intel の公開実装", "FLIR BFS-U3-51S5P",
])
def test_probe_hits(text):
    assert find_company_names(text), text


@pytest.mark.parametrize("text", [
    "HALCON の 2313 op", "IDs = [1, 2]", "BK7 相当のホウケイ酸クラウン", "SF11 相当", "1 S = 1 siemens",
    "shot noise とショットノイズ", "シャープネス", "σ(シグマ)", "Canonical form", "an apple", "1 tesla",
    "Kaplan & Bosch, TSP Art", "硝材 517642(カタログ B)", "人型 1 は 393,270 → 1,497 三角形",
    "Polyanskiy, Sci. Data 11, 94 (2024), https://doi.org/10.1038/s41597-023-02898-2 (Schott)",
    "*ad-rss-lib*(Apache-2.0、https://github.com/intel/ad-rss-lib)", "MaleCNS v1.0(Janelia × Google Research、CC-BY 4.0)",
    "画像生成 AI(Google gemini-2.5-flash-image)で素材を作り", "Shepp-Logan-Phantom", "coherent imaging",
    "the stated braking pattern", "O'Hara et al.", "Ohara et al. 2019",
])
def test_probe_misses(text):
    assert not find_company_names(text), (text, find_company_names(text))


def test_vocabulary_compiles_and_is_large_enough():
    """語彙が誤って空・短縮されていない(足すのは自由、減らすなら理由を)。"""
    assert len(COMPANY_NAMES_CI) >= 150 and len(COMPANY_NAMES_JA) >= 50 and len(PRODUCT_CODES) >= 15
    assert os.path.isfile(__file__)


def test_anim3d_payload_strip_keeps_text_and_drops_base64():
    """base64 を消しても、画面に出る文字(JSON の文字列)の中のカタログ名は残って当たる。"""
    txt = '{"label":{"ja":"ガラス(N-BK7)"},"png":"' + "A" * 200 + '+Sony/' + "B" * 200 + '"}'
    words = [w for _i, w, _l in find_company_names(_strip_payload(txt))]
    assert words == ["N-BK7"], words
    esc = '{"ja":"' + "".join("%su%04x" % (chr(92), ord(c)) for c in "ソニーの硝材") + '"}'
    assert [w for _i, w, _l in find_company_names(_strip_payload(esc))] == ["ソニー"]


@pytest.mark.parametrize("text", [
    "BK7 相当のホウケイ酸クラウン", "SF11 相当", "凸の BK7 と凹の SF2", "LASF9 の高屈折率", "BK7/SF2 の貼り合わせ",
    "N-BK7 + N-SF2 achromat", "FK58 と SF66",
])
def test_bare_glass_codes_hit_in_the_anim3d_scope(text):
    assert find_company_names(text, bare=True), text


@pytest.mark.parametrize("text", [
    "f1 / f2(paraxial_trace)", "1/f = 1/f1 + 1/f2 − d/(f1 f2)", "F2 の焦点", "f2 = 51.1 mm", "K1 と K2 の歪み係数",
    "F1 スコア", "クラウンガラス(n_d = 1.5168, V_d = 64.17)", "sf2 = s.f2", "重フリントガラス(n_d = 1.7847, V_d = 25.68)",
])
def test_bare_glass_codes_do_not_hit_focal_lengths_or_generic_names(text):
    assert not find_company_names(text, bare=True), (text, find_company_names(text, bare=True))


def test_n_prefixed_code_is_counted_once_with_bare():
    assert [w for _i, w, _l in find_company_names("N-BK7 と BK7", bare=True)] == ["N-BK7", "BK7"]
