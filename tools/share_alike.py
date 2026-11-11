# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""継承条件つき(CC BY-SA など)のデータセットの台帳と、その図に付ける帰属表示。

repo のコードは Apache-2.0 だが、継承条件つきのデータのコマ(画素)を含む図は、図そのものがその
ライセンスで配られる。どの図がそうかを作者が図ごとに書く文言に頼ると、書き忘れた図が黙って
抜ける。ここではデータセットの名前と、それを使う PoC と、コマの画素を含まない図(グラフ・表)を
台帳に持ち、判定はすべてここから行う:

* ``NOTICE`` の一覧(``tests/test_notice_sharealike.py`` が配布物の側から数える)
* ViEW の案内ページのタイルとクレジット欄(``tools/gen_view2026_pages.py``)
* 展示館の記事の図の下の表記(``tools/gen_wingpoc_gallery.py``)

新しく継承条件つきのデータを使うときは、ここに 1 行足す。足さずに図の出典へ名前を書くと、門が
「台帳に無い PoC が継承条件つきのデータを使っている」として止める。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "articles" / "assets" / "poc"
VIEW_THUMBS = ROOT / "docs" / "view2026" / "thumbs" / "all"
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif")
#: 読者がたどれる NOTICE(改変の内容と継承条件つきのファイルの一覧)。
NOTICE_URL = "https://github.com/furuse-kazufumi/fullseye/blob/master/NOTICE"

#: 継承条件つきのデータセット。``match`` は図の出典・説明にこの語があれば当たり(大文字小文字を区別しない)。
DATASETS = (
    {
        "name": "LASIESTA",
        "match": ("LASIESTA",),
        "license": "CC BY-SA 4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "source_url": "https://www.gti.ssr.upm.es/data/lasiesta_database",
        "credit": "LASIESTA (C. Cuevas, E. M. Yáñez, N. García, CVIU 152, 2016; GTI, Universidad Politécnica de Madrid)",
        #: PoC → コマの画素を含まない図(数だけのグラフ・表)。それ以外の画像はすべて継承条件つき。
        "pocs": {"poc_real_bg_kalman_tracking": ("06_track_error", "07_scores")},
    },
)

_LINE = {
    "ja": "この図は {credit}(出典 {src})の改変物で、{lic}({url})。Apache-2.0 ではない。改変の内容は [NOTICE]({notice})。",
    "en": "This figure is adapted from {credit} (source: {src}) and licensed {lic} ({url}), not Apache-2.0; changes are listed in [NOTICE]({notice}).",
    "zh": "此图改编自 {credit}(来源 {src}),采用 {lic}({url}),不适用 Apache-2.0。修改内容见 [NOTICE]({notice})。",
    "tw": "此圖改編自 {credit}(來源 {src}),採用 {lic}({url}),不適用 Apache-2.0。修改內容見 [NOTICE]({notice})。",
    "ko": "이 그림은 {credit}(출처 {src})의 개작물이며 {lic}({url})입니다. Apache-2.0이 아닙니다. 변경 내용은 [NOTICE]({notice}).",
    "de": "Diese Abbildung ist eine Bearbeitung von {credit} (Quelle: {src}) und steht unter {lic} ({url}), nicht Apache-2.0; Änderungen siehe [NOTICE]({notice}).",
    "hi": "यह चित्र {credit} (स्रोत: {src}) का रूपांतरण है और {lic} ({url}) के अंतर्गत है, Apache-2.0 नहीं; बदलाव [NOTICE]({notice}) में।",
    "fr": "Cette figure est une adaptation de {credit} (source : {src}), sous licence {lic} ({url}), et non Apache-2.0 ; modifications dans [NOTICE]({notice}).",
}
_SHORT = {"ja": "図: {name} · {lic}", "en": "Figure: {name} · {lic}", "zh": "图: {name} · {lic}",
          "tw": "圖: {name} · {lic}", "ko": "그림: {name} · {lic}", "de": "Abb.: {name} · {lic}",
          "hi": "चित्र: {name} · {lic}", "fr": "Figure : {name} · {lic}"}
HEADING = {"ja": "図のライセンス(継承条件つき)", "en": "Figure licences (share-alike)",
           "zh": "图的许可(相同方式共享)", "tw": "圖的授權(相同方式分享)", "ko": "그림 라이선스(동일조건변경허락)",
           "de": "Lizenzen der Abbildungen (Weitergabe unter gleichen Bedingungen)",
           "hi": "चित्रों का लाइसेंस (share-alike)", "fr": "Licences des figures (partage dans les mêmes conditions)"}


def dataset_for(poc_id: str) -> dict | None:
    """その PoC が使う継承条件つきのデータセット(無ければ ``None``)。"""
    for ds in DATASETS:
        if poc_id in ds["pocs"]:
            return ds
    return None


def mentions(text: str) -> list[dict]:
    """文に名前が出てくる継承条件つきのデータセット。"""
    low = (text or "").lower()
    return [ds for ds in DATASETS if any(m.lower() in low for m in ds["match"])]


def _stem(name: str) -> str:
    stem = Path(name).stem
    return stem[:-4] if stem.endswith("_720") else stem


def is_share_alike_file(poc_id: str, name: str) -> bool:
    """PoC の図の置き場のファイルが継承条件つきか(画像で、台帳の「画素なし」に当たらない)。"""
    ds = dataset_for(poc_id)
    if ds is None or Path(name).suffix.lower() not in IMAGE_SUFFIXES:
        return False
    return _stem(name) not in ds["pocs"][poc_id]


def share_alike_files() -> list[str]:
    """継承条件つきの配布物(repo の根からの相対、``/`` 区切り)。NOTICE に全部載っていなければならない。"""
    out = []
    for ds in DATASETS:
        for poc in ds["pocs"]:
            d = ASSETS / poc
            for f in sorted(d.iterdir()) if d.is_dir() else []:
                if f.is_file() and is_share_alike_file(poc, f.name):
                    out.append(f.relative_to(ROOT).as_posix())
            view = VIEW_THUMBS / (poc + ".jpg")
            if view.is_file():
                out.append(view.relative_to(ROOT).as_posix())
    return out


def attribution(poc_id: str, lang: str) -> str | None:
    """図の下に置く帰属表示(1 文、URL つき)。継承条件つきでなければ ``None``。"""
    ds = dataset_for(poc_id)
    if ds is None:
        return None
    return _LINE.get(lang, _LINE["en"]).format(credit=ds["credit"], src=ds["source_url"], lic=ds["license"],
                                               url=ds["license_url"], notice=NOTICE_URL)


def short_label(poc_id: str, lang: str) -> str | None:
    """タイルに添える短い表記(リンクなし)。"""
    ds = dataset_for(poc_id)
    if ds is None:
        return None
    return _SHORT.get(lang, _SHORT["en"]).format(name=ds["name"], lic=ds["license"])
