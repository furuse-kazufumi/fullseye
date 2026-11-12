# -*- coding: utf-8 -*-
"""Studio の「プロジェクト」(フォルダそのもの)と、そのファイルのツリー(2026-11-12, 第 2 便)。

* プロジェクト = フォルダ。専用のファイルは要らない(開けば使える)。配置・開閉・最後のフォルダは Studio の設定側に、
  フォルダのパスをキーにして持つ。フォルダの中には何も書かない。
* このモジュールの**上半分は Qt に依らない**(種類の判定・標準の並びの表・フォルダの外へ出るパスの拒否・リンクの判定・
  新しいプロジェクトの作成・食い違いの検出)。``fs.load_pipeline`` などが「プロジェクトの中の名前だけ」で引くときにも、
  ここの表を import して使う(Qt は import しない)。
* 下半分の :func:`build_panel` が Qt のパネル(ドック)。Qt は関数の中で遅延 import する。

標準の並び(決まりであって強制ではない)::

    images/     入力画像            pipelines/  パイプライン(JSON)
    programs/   Python              params/     パラメータの束・定義(下は自由)
    results/    出力・レポート

フォルダ名は英語の固定(Python から相対パスで読むので翻訳しない)。木の上の表示名だけを各言語にする。
種類の判定は**中身**で行い、フォルダ名では決めない(標準の並びでないフォルダもそのまま開ける)。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from collections import namedtuple

# --------------------------------------------------------------------------- 語の表(正本)
#: 種類 id -> (標準のサブフォルダ, 画面の語 = tr() に通す英語)。メニュー・パレット・パネルの題・絞り込みは全部ここから引く。
KINDS = {
    "image": ("images", "Images"),
    "pipeline": ("pipelines", "Pipelines"),
    "python": ("programs", "Python"),
    "params": ("params", "Parameters"),
}
#: 種類を持たない標準フォルダ(出力・レポート)
RESULTS_FOLDER = ("results", "Results")
#: 標準のサブフォルダの並び(新しいプロジェクトで作る順)。(フォルダ名, 種類 or None, 画面の語)
STANDARD_FOLDERS = tuple((folder, kind, label) for kind, (folder, label) in KINDS.items()) + \
    ((RESULTS_FOLDER[0], None, RESULTS_FOLDER[1]),)
STANDARD_FOLDER_NAMES = tuple(f for f, _k, _l in STANDARD_FOLDERS)
#: 種類の絞り込みの選択肢(先頭 = 全部)。(id, 画面の語)
FILTER_CHOICES = (("all", "All"),) + tuple((k, label) for k, (_f, label) in KINDS.items())
#: 定義ファイルの拡張子(中身がパイプラインの .json は別)
PARAMS_EXTS = (".json", ".toml", ".yaml", ".yml", ".xml")
#: 既定の画像拡張子(Studio は IMAGE_FILE_EXTS を渡す。ここは Qt も imgio も import しないための控え)
DEFAULT_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".pgm", ".ppm", ".pnm", ".pbm",
                      ".pfm", ".gif", ".jp2")
#: 木に出さないフォルダ(名前が . で始まるもの = .git / .venv など、と __pycache__)
HIDDEN_DIR_NAMES = ("__pycache__",)
#: 種類の判定のために読む先頭のバイト数(これより大きなファイルは全部は読まない)
HEAD_BYTES = 64 * 1024
#: 読み取り専用で見せる定義ファイルの最大バイト数
VIEW_MAX_BYTES = 1024 * 1024

Entry = namedtuple("Entry", "name path is_dir is_link kind")


def folder_for(kind):
    """種類 -> 標準のサブフォルダ名(``image`` -> ``images``)。表に無ければ None。"""
    if kind in KINDS:
        return KINDS[kind][0]
    return RESULTS_FOLDER[0] if kind == "result" else None


def kind_of_folder(name):
    """標準のサブフォルダ名 -> 種類(``pipelines`` -> ``pipeline``)。results / 標準でない名前は None。"""
    for kind, (folder, _label) in KINDS.items():
        if folder == name:
            return kind
    return None


def label_for(kind):
    """種類 -> 画面の語(英語の原文。表示は tr() に通す)。"""
    if kind in KINDS:
        return KINDS[kind][1]
    return {"result": RESULTS_FOLDER[1], "all": "All", "other": "Other files"}.get(kind, str(kind))


def folder_display(folder, tr=lambda s: s):
    """木の上の標準フォルダの表示名: ``pipelines — パイプライン``。標準でない名前はそのまま。"""
    for f, _k, label in STANDARD_FOLDERS:
        if f == folder:
            return "%s — %s" % (folder, tr(label))
    return folder


# --------------------------------------------------------------------------- 種類の判定(中身で。Qt なし)
_KIND_RE = re.compile(rb'"fullseye_kind"\s*:\s*"([A-Za-z0-9_\-]+)"')


def _json_kind(d):
    """読めた JSON(dict)の種類。封筒 ``fullseye_kind`` があればそれ、無ければ今の保存形式(fullseye_pipeline / stages)。"""
    if not isinstance(d, dict):
        return "params"
    k = d.get("fullseye_kind")
    if isinstance(k, str):
        return "pipeline" if k == "pipeline" else "params"
    if "fullseye_pipeline" in d or isinstance(d.get("stages"), list):
        return "pipeline"
    return "params"


def classify_file(path, image_exts=DEFAULT_IMAGE_EXTS, head_bytes=HEAD_BYTES):
    """ファイルの種類: ``image`` / ``pipeline`` / ``python`` / ``params`` / ``other``。

    拡張子で決められるものは中身を読まない。``.json`` だけ中身を見る: 先頭 *head_bytes* までを読み、全部が収まれば
    ``json.loads``、収まらなければ先頭の ``fullseye_kind`` / ``fullseye_pipeline`` の語だけを探す(大きなファイルを
    全部は読まない)。YAML / TOML / XML は読み込まず拡張子で ``params``。``.py`` は読まない(import も exec もしない)。"""
    ext = os.path.splitext(str(path))[1].lower()
    if ext in tuple(image_exts):
        return "image"
    if ext == ".py":
        return "python"
    if ext == ".json":
        try:
            size = os.path.getsize(path)
            with open(path, "rb") as fh:
                head = fh.read(head_bytes)
        except OSError:
            return "params"
        if size <= head_bytes:
            try:
                return _json_kind(json.loads(head.decode("utf-8-sig")))
            except (ValueError, UnicodeDecodeError):
                return "params"
        m = _KIND_RE.search(head)
        if m:
            return "pipeline" if m.group(1) == b"pipeline" else "params"
        return "pipeline" if b'"fullseye_pipeline"' in head else "params"
    if ext in PARAMS_EXTS:
        return "params"
    return "other"


# --------------------------------------------------------------------------- リンク・隠し・フォルダの外
def is_link(path):
    """シンボリックリンクまたは Windows のジャンクション(再解析ポイント)か。辿らないための判定。"""
    try:
        if os.path.islink(path):
            return True
        st = os.lstat(path)
        return bool(getattr(st, "st_file_attributes", 0) & 0x400)      # FILE_ATTRIBUTE_REPARSE_POINT
    except OSError:
        return False


def is_hidden_dir(name):
    return name.startswith(".") or name in HIDDEN_DIR_NAMES


_BAD_NAME_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')


def validate_name(name):
    """新規・名前の変更で受ける名前(1 つの名前。区切り・``..``・絶対パス・Windows で使えない文字を断る)。
    通ればそのまま返し、断るなら ValueError(理由)。"""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("the name is empty")
    name = name.strip()
    if os.path.isabs(name) or os.path.splitdrive(name)[0]:
        raise ValueError("an absolute path is not accepted; give a name inside the project folder")
    if re.search(r"[\\/]", name):
        raise ValueError("a name cannot contain / or \\ ; it must stay in the folder you chose")
    if name in (".", "..") or name.endswith((".", " ")):
        raise ValueError("'%s' is not a usable name ('..' and names ending in a dot or space are refused)" % name)
    if _BAD_NAME_CHARS.search(name):
        raise ValueError("the name has a character that file names cannot hold: < > : \" | ? *")
    return name


def resolve_inside(root, rel):
    """*root* の中に解決されるパスだけを返す(``..`` ・絶対パス・外へ出るリンクは ValueError)。"""
    if not isinstance(rel, str) or not rel.strip():
        raise ValueError("the path is empty")
    if os.path.isabs(rel) or os.path.splitdrive(rel)[0]:
        raise ValueError("an absolute path is not accepted; give a path inside the project folder")
    if ".." in re.split(r"[\\/]+", rel):
        raise ValueError("'..' is not accepted; the path must stay inside the project folder")
    r = os.path.realpath(root)
    target = os.path.realpath(os.path.join(root, rel))
    try:
        inside = os.path.commonpath([os.path.normcase(r), os.path.normcase(target)]) == os.path.normcase(r)
    except ValueError:                                  # 別のドライブ
        inside = False
    if not inside:
        raise ValueError("the path resolves outside the project folder")
    return target


def is_inside(root, path):
    try:
        r = os.path.realpath(root)
        p = os.path.realpath(path)
        return os.path.commonpath([os.path.normcase(r), os.path.normcase(p)]) == os.path.normcase(r)
    except (ValueError, OSError):
        return False


# --------------------------------------------------------------------------- 一覧
def list_dir(path, kind_filter="all", query="", image_exts=DEFAULT_IMAGE_EXTS):
    """*path* の直下を木に出す順(フォルダが先、名前順)で返す。隠しフォルダは出さない。
    ファイルは名前の部分一致(*query*)と種類(*kind_filter*)で絞る。フォルダは常に出す(中で当たるかは分からないので)。
    リンクは ``is_link`` を立てて出す(展開は呼び出し側がしない)。読めないフォルダは空。"""
    q = (query or "").strip().casefold()
    out = []
    try:
        names = os.listdir(path)
    except OSError:
        return out
    for name in names:
        full = os.path.join(path, name)
        link = is_link(full)
        isdir = os.path.isdir(full)
        if isdir:
            if is_hidden_dir(name):
                continue
            out.append(Entry(name, full, True, link, None))
            continue
        kind = classify_file(full, image_exts)
        if kind_filter != "all" and kind != kind_filter:
            continue
        if q and q not in name.casefold():
            continue
        out.append(Entry(name, full, False, link, kind))
    out.sort(key=lambda e: (not e.is_dir, e.name.casefold()))
    return out


# --------------------------------------------------------------------------- 置き場所・食い違い
def place_for(root, kind):
    """種類の置き場所(標準のサブフォルダのパス。まだ無くてもパスを返す)。表に無い種類は None。"""
    folder = folder_for(kind)
    return os.path.join(root, folder) if folder else None


def top_folder(root, path):
    """*path* がプロジェクトの直下のどのフォルダの中か(直下のファイルや外は None)。"""
    try:
        rel = os.path.relpath(os.path.realpath(path), os.path.realpath(root))
    except ValueError:
        return None
    parts = re.split(r"[\\/]+", rel)
    return parts[0] if len(parts) >= 2 and parts[0] not in ("..", ".") else None


def mismatch(root, path, kind):
    """中身の種類と置き場所が食い違う時、移すべき標準のフォルダ名を返す(例: ``params/`` の中のパイプライン -> ``pipelines``)。
    食い違わない・標準のフォルダの外・種類が標準に無い(other)なら None。移すかは利用者が決める(黙って移さない)。"""
    want = folder_for(kind) if kind in KINDS else None
    if want is None:
        return None
    top = top_folder(root, path)
    if top in STANDARD_FOLDER_NAMES and top != want:
        return want
    return None


def move_to_standard(root, path, kind):
    """食い違うファイルを標準のサブフォルダへ移す(プロジェクトの中だけ)。移した先を返す。
    移動先に同名があれば ValueError で止める(上書きしない)。標準のサブフォルダが無ければ作る(呼び出し側が先に聞く)。"""
    want = folder_for(kind)
    if want is None:
        raise ValueError("no standard folder for this kind")
    if not is_inside(root, path):
        raise ValueError("the file is not inside the project folder")
    dest_dir = resolve_inside(root, want)
    dest = os.path.join(dest_dir, os.path.basename(path))
    if os.path.exists(dest):
        raise ValueError("%s already exists in %s/" % (os.path.basename(path), want))
    os.makedirs(dest_dir, exist_ok=True)
    shutil.move(path, dest)
    return dest


def missing_folders(root):
    """標準のサブフォルダのうち、まだ無いもの(名前の並び)。"""
    return [f for f in STANDARD_FOLDER_NAMES if not os.path.isdir(os.path.join(root, f))]


def create_project(parent, name):
    """*parent* の中に *name* のフォルダを作り、標準のサブフォルダを作る。既にあるフォルダ・ファイルは上書きしない。

    返り値 ``{"root", "created", "existing", "had_content"}``。*name* が既存の中身のあるフォルダなら、足りないサブフォルダだけを
    作る(``had_content=True``。呼び出し側が先にそう言う)。名前が不正・*parent* の外へ出るなら ValueError。"""
    name = validate_name(name)
    root = resolve_inside(parent, name)
    if os.path.exists(root) and not os.path.isdir(root):
        raise ValueError("%s exists and is not a folder" % name)
    had_content = os.path.isdir(root) and bool(os.listdir(root))
    os.makedirs(root, exist_ok=True)
    created, existing = [], []
    for folder in STANDARD_FOLDER_NAMES:
        p = os.path.join(root, folder)
        if os.path.isdir(p):
            existing.append(folder)
        else:
            if os.path.exists(p):
                raise ValueError("%s exists and is not a folder" % folder)
            os.makedirs(p)
            created.append(folder)
    return {"root": root, "created": created, "existing": existing, "had_content": had_content}


def new_pipeline_text():
    """空のパイプラインのファイルの中身(Studio の今の保存形式)。"""
    return json.dumps({"fullseye_pipeline": 1, "stages": []}, indent=2)


def state_key(path):
    """設定側でプロジェクトのフォルダのパスをキーにするための短い印(大文字小文字・区切りを正規化して SHA-1)。"""
    norm = os.path.normcase(os.path.realpath(path))
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def read_text_limited(path, limit=VIEW_MAX_BYTES):
    """読み取り専用の表示用に、先頭 *limit* バイトまでを文字にして返す(全部は読まない)。(文, 切り詰めたか)。"""
    with open(path, "rb") as fh:
        raw = fh.read(limit + 1)
    cut = len(raw) > limit
    return raw[:limit].decode("utf-8", errors="replace"), cut


# --------------------------------------------------------------------------- Qt のパネル
def reveal_in_file_manager(path):
    """エクスプローラー(Windows)/ Finder / ファイルマネージャでそのファイルを表示する(OS の既定のアプリで**開かない**)。"""
    import subprocess
    import sys
    path = os.path.abspath(path)
    if sys.platform.startswith("win"):
        subprocess.Popen(["explorer", "/select,", path])       # list 引数(シェルを通さない)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", path])
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(path)])


def build_panel(parent, hooks):
    """プロジェクトのパネルを *parent*(QWidget)の中に作る。返り値は窓から使う口(dict)。

    *hooks*(窓=Studio が渡す): ``tr`` / ``flash`` / ``settings()`` / ``image_exts`` / ``open_image(path)`` /
    ``open_pipeline(path)`` / ``open_python(path)`` / ``open_params(path)`` / ``compare_images(paths)`` /
    ``confirm(title, text)->bool`` / ``warn(title, text)`` / ``pick_dir(title, start)->str`` / ``ask_text(title, label, default)->str|None`` /
    ``sample_dir`` (str or None) / ``on_change()`` (プロジェクトが変わったとき: 窓の題を直す)。
    テストは ``panel["hooks"]`` の値を差し替えて、ダイアログ無しで動かす。"""
    from PySide6 import QtCore, QtGui, QtWidgets
    H = dict(hooks)
    H.setdefault("tr", lambda s: s)
    H.setdefault("flash", lambda s: None)
    H.setdefault("image_exts", DEFAULT_IMAGE_EXTS)
    H.setdefault("on_change", lambda: None)
    H.setdefault("reveal", reveal_in_file_manager)
    H.setdefault("sample_dir", None)
    tr = lambda s: H["tr"](s)                                           # noqa: E731 - 呼び出し時に言語を引く
    S = {"root": None, "expanded": set(), "kind": "all", "query": ""}
    UR = QtCore.Qt.UserRole
    KEY_RECENT, KEY_LAST, KEY_EXP, KEY_KIND = "project/recent", "project/last_dir", "project/expanded", "project/filter_kind"

    # ---- 部品 ------------------------------------------------------------------------------------
    lay = QtWidgets.QVBoxLayout(parent)
    lay.setContentsMargins(4, 4, 4, 4); lay.setSpacing(4)
    stack = QtWidgets.QStackedWidget()
    lay.addWidget(stack, 1)

    # 空の状態: 何をする場所か 1 行 + 最初の一手(フォルダを開く / 新しいプロジェクト)+ 例(サンプルのフォルダ)
    empty = QtWidgets.QWidget()
    ev = QtWidgets.QVBoxLayout(empty)
    empty_text = QtWidgets.QLabel(); empty_text.setWordWrap(True); empty_text.setProperty("hint", True)
    b_open = QtWidgets.QPushButton()
    b_new = QtWidgets.QPushButton()
    b_sample = QtWidgets.QPushButton()
    ev.addWidget(empty_text); ev.addWidget(b_open); ev.addWidget(b_new); ev.addWidget(b_sample); ev.addStretch(1)
    stack.addWidget(empty)

    full = QtWidgets.QWidget()
    fv = QtWidgets.QVBoxLayout(full); fv.setContentsMargins(0, 0, 0, 0); fv.setSpacing(4)
    head = QtWidgets.QLabel(); head.setWordWrap(True)
    b_close = QtWidgets.QToolButton(); b_close.setAutoRaise(True)
    hr = QtWidgets.QHBoxLayout(); hr.addWidget(head, 1); hr.addWidget(b_close)
    filt = QtWidgets.QLineEdit(); filt.setClearButtonEnabled(True)
    kind_box = QtWidgets.QComboBox()
    for kid, _lbl in FILTER_CHOICES:
        kind_box.addItem("", kid)
    fr = QtWidgets.QHBoxLayout(); fr.addWidget(filt, 1); fr.addWidget(kind_box)
    tree = QtWidgets.QTreeView()
    tree.setHeaderHidden(True)
    tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
    tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    tree.setIconSize(QtCore.QSize(16, 16))
    tree.setAcceptDrops(True)
    model = QtGui.QStandardItemModel(tree)
    tree.setModel(model)
    fv.addLayout(hr); fv.addLayout(fr); fv.addWidget(tree, 1)
    stack.addWidget(full)

    # ---- 文言(言語の切り替えで作り直す)----------------------------------------------------------------
    def retranslate():
        empty_text.setText(tr("Open a folder and its images, pipelines and definition files are listed here."))
        b_open.setText(tr("Open folder…"))
        b_new.setText(tr("New project…"))
        b_sample.setText(tr("Open the sample folder"))
        b_sample.setVisible(bool(H.get("sample_dir")))
        b_open.setToolTip(tr("Choose a folder: it becomes the project. Nothing is written into it"))
        b_new.setToolTip(tr("Create a project folder with the standard sub-folders: images, pipelines, programs, params, results"))
        b_sample.setToolTip(tr("Open the folder of bundled sample images to see how the tree works"))
        filt.setPlaceholderText(tr("Filter by name"))
        filt.setToolTip(tr("Show only the files whose name contains this text"))
        kind_box.setToolTip(tr("Show only one kind of file"))
        for i, (_kid, lbl) in enumerate(FILTER_CHOICES):
            kind_box.setItemText(i, tr(lbl))
        b_close.setText("✕"); b_close.setToolTip(tr("Close the project folder"))
        tree.setToolTip(tr("The project folder. Double-click a file to open it; right-click for more"))
        _title()
    parent.retranslate = retranslate

    def _title():
        if S["root"]:
            head.setText("%s\n%s" % (os.path.basename(S["root"].rstrip("\\/")) or S["root"], S["root"]))
            head.setToolTip(S["root"])

    # ---- アイコン(種類で分かる)------------------------------------------------------------------------
    _ICON = {}
    _TONE = {"image": "#17b8a6", "pipeline": "#e8a33d", "python": "#4f8ef7", "params": "#9b8cff", "other": "#6b7280"}
    _GLYPH = {"image": "I", "pipeline": "P", "python": "Py", "params": "{}", "other": "?"}

    def icon_for(kind):
        ic = _ICON.get(kind)
        if ic is None:
            pm = QtGui.QPixmap(16, 16); pm.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(pm)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setBrush(QtGui.QColor(_TONE.get(kind, "#6b7280"))); p.setPen(QtCore.Qt.NoPen)
            p.drawRoundedRect(0, 0, 16, 16, 3, 3)
            p.setPen(QtGui.QColor("#0b0e14"))
            f = p.font(); f.setPixelSize(9 if len(_GLYPH.get(kind, "?")) > 1 else 11); f.setBold(True); p.setFont(f)
            p.drawText(pm.rect(), QtCore.Qt.AlignCenter, _GLYPH.get(kind, "?"))
            p.end()
            ic = _ICON[kind] = QtGui.QIcon(pm)
        return ic

    def kind_tip(kind):
        return {"image": tr("Image: double-click opens it as the input image"),
                "pipeline": tr("Pipeline: double-click opens it as the current pipeline"),
                "python": tr("Python: not run when opened; the Python mode comes in the next version"),
                "params": tr("Parameters / definitions: double-click shows the text, read-only"),
                "other": tr("Other file: not opened here; use Show in file manager")}.get(kind, "")

    # ---- 木の作り方 ---------------------------------------------------------------------------------------
    PLACEHOLDER = "__placeholder__"

    def _make_item(e, depth):
        it = QtGui.QStandardItem()
        it.setData(e.path, UR); it.setData(e.kind, UR + 1); it.setData(e.is_dir, UR + 2); it.setData(e.is_link, UR + 3)
        it.setEditable(False)
        if e.is_dir:
            it.setText(folder_display(e.name, tr) if depth == 0 else e.name)
            it.setIcon(tree.style().standardIcon(QtWidgets.QStyle.SP_DirLinkIcon if e.is_link else QtWidgets.QStyle.SP_DirIcon))
            if e.is_link:
                it.setToolTip(tr("A link: shown, but not followed (the tree stays inside the project folder)"))
            else:
                ph = QtGui.QStandardItem(PLACEHOLDER); ph.setData(PLACEHOLDER, UR)
                it.appendRow(ph)
                if depth == 0 and e.name in STANDARD_FOLDER_NAMES:
                    it.setToolTip(tr("Standard folder (images / pipelines / programs / params / results)"))
        else:
            it.setText(e.name); it.setIcon(icon_for(e.kind))
            tip = kind_tip(e.kind)
            want = mismatch(S["root"], e.path, e.kind) if S["root"] else None
            if want:
                it.setText(e.name + "  ⚠")
                it.setForeground(QtGui.QColor("#c9a227"))
                tip = (tr("The content is a %s but it sits in %s/. Move it to %s/?")
                       % (tr(label_for(e.kind)), top_folder(S["root"], e.path), want)) + "\n" + tip
                it.setData(want, UR + 4)
            it.setToolTip(tip)
        return it

    def _populate(parent_item, path, depth):
        rows = list_dir(path, S["kind"], S["query"], H["image_exts"])
        parent_item.removeRows(0, parent_item.rowCount())
        for e in rows:
            parent_item.appendRow(_make_item(e, depth))
        if parent_item is not model.invisibleRootItem():
            return
        return

    def _rel(path):
        try:
            return os.path.relpath(path, S["root"])
        except ValueError:
            return path

    def _expand_remembered(parent_item):
        for r in range(parent_item.rowCount()):
            ch = parent_item.child(r)
            if ch.data(UR + 2) and not ch.data(UR + 3) and _rel(ch.data(UR)) in S["expanded"]:
                tree.expand(ch.index())

    def _on_expanded(idx):
        it = model.itemFromIndex(idx)
        if it is None or not it.data(UR + 2) or it.data(UR + 3):
            return
        S["expanded"].add(_rel(it.data(UR)))
        if it.rowCount() == 1 and it.child(0).data(UR) == PLACEHOLDER:
            depth = len([x for x in re_split(_rel(it.data(UR))) if x])
            _populate(it, it.data(UR), depth)
            _expand_remembered(it)
        _save_state()

    def _on_collapsed(idx):
        it = model.itemFromIndex(idx)
        if it is not None and it.data(UR):
            S["expanded"].discard(_rel(it.data(UR)))
            _save_state()

    def re_split(rel):
        return re.split(r"[\\/]+", rel)

    tree.expanded.connect(_on_expanded)
    tree.collapsed.connect(_on_collapsed)

    def reload():
        """木を作り直す(絞り込みの変更・ファイルの作成・名前の変更のあと)。開いていたフォルダは開き直す。"""
        model.removeRows(0, model.rowCount())
        if not S["root"]:
            stack.setCurrentIndex(0); return
        stack.setCurrentIndex(1)
        _populate(model.invisibleRootItem(), S["root"], 0)
        _expand_remembered(model.invisibleRootItem())
        _title()

    # ---- 設定(フォルダのパスをキーに。フォルダの中には書かない)-------------------------------------------------
    def _settings():
        return H["settings"]()

    def _save_state():
        if not S["root"]:
            return
        try:
            s = _settings()
            allx = json.loads(s.value(KEY_EXP, "{}") or "{}")
            allx[state_key(S["root"])] = sorted(S["expanded"])
            s.setValue(KEY_EXP, json.dumps(allx))
            s.setValue(KEY_KIND, S["kind"])
        except Exception:                                                   # noqa: BLE001 - 設定が書けなくても木は動く
            pass

    def recent():
        try:
            v = _settings().value(KEY_RECENT, []) or []
            return [x for x in v if isinstance(x, str)]
        except Exception:                                                   # noqa: BLE001
            return []

    def _push_recent(path):
        keep = [x for x in recent() if os.path.normcase(x) != os.path.normcase(path)]
        _settings().setValue(KEY_RECENT, ([path] + keep)[:8])

    # ---- 開く・閉じる ---------------------------------------------------------------------------------------
    def open_dir(path, remember=True):
        """フォルダをプロジェクトとして開く。開けなければ理由を言って False。"""
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            H["warn"](tr("Could not open the folder"), "%s\n\n%s" % (path, tr("It is not a folder, or it no longer exists.")))
            return False
        S["root"] = path
        try:
            allx = json.loads(_settings().value(KEY_EXP, "{}") or "{}")
            S["expanded"] = set(allx.get(state_key(path), []))
        except Exception:                                                   # noqa: BLE001
            S["expanded"] = set()
        if remember:
            _settings().setValue(KEY_LAST, path)
            _push_recent(path)
        reload()
        _title()
        H["flash"](tr("project folder: %s") % path)
        H["on_change"]()
        return True

    def close_project():
        S["root"] = None
        S["expanded"] = set()
        try:
            _settings().setValue(KEY_LAST, "")
        except Exception:                                                   # noqa: BLE001
            pass
        reload()
        H["on_change"]()

    def restore():
        """次の起動で最後のフォルダを戻す。無くなっていたら黙って空の状態に戻し、1 行で知らせる。"""
        try:
            last = _settings().value(KEY_LAST, "") or ""
            k = _settings().value(KEY_KIND, "all") or "all"
        except Exception:                                                   # noqa: BLE001
            return False
        if k in [c[0] for c in FILTER_CHOICES]:
            S["kind"] = k
            kind_box.blockSignals(True); kind_box.setCurrentIndex([c[0] for c in FILTER_CHOICES].index(k)); kind_box.blockSignals(False)
        if not last:
            return False
        if not os.path.isdir(last):
            H["flash"](tr("The last project folder is gone: %s") % last)
            _settings().setValue(KEY_LAST, "")
            return False
        return open_dir(last, remember=False)

    def choose_dir():
        start = S["root"] or os.path.expanduser("~")
        p = H["pick_dir"](tr("Open folder"), start)
        return open_dir(p) if p else False

    def new_project():
        """場所と名前を聞いて、標準のサブフォルダを作る。既にあるフォルダは上書きしない。"""
        parent_dir = H["pick_dir"](tr("Where should the new project go?"), S["root"] and os.path.dirname(S["root"]) or os.path.expanduser("~"))
        if not parent_dir:
            return False
        name = H["ask_text"](tr("New project"), tr("Project folder name"), "project")
        if not name:
            return False
        try:
            validate_name(name)
            target = resolve_inside(parent_dir, name.strip())
            if os.path.isdir(target) and os.listdir(target):
                if not H["confirm"](tr("New project"), tr("%s already has files. Only the missing sub-folders will be created; nothing is overwritten.\nContinue?") % target):
                    return False
            info = create_project(parent_dir, name)
        except (ValueError, OSError) as exc:
            H["warn"](tr("Could not create the project"), str(exc))
            return False
        return open_dir(info["root"])

    def open_sample():
        d = H.get("sample_dir")
        return open_dir(d) if d else False

    b_open.clicked.connect(lambda _=False: choose_dir())
    b_new.clicked.connect(lambda _=False: new_project())
    b_sample.clicked.connect(lambda _=False: open_sample())
    b_close.clicked.connect(lambda _=False: close_project())

    # ---- 絞り込み -------------------------------------------------------------------------------------------
    def _on_filter(_=None):
        S["query"] = filt.text()
        reload()
    filt.textChanged.connect(_on_filter)

    def _on_kind(i):
        S["kind"] = kind_box.itemData(i) or "all"
        reload(); _save_state()
    kind_box.currentIndexChanged.connect(_on_kind)

    # ---- 開く先(種類ごとに 1 つ。どの入口から開いても同じ)----------------------------------------------------------
    def activate(path):
        """ファイルを種類で決まる行き先へ開く。フォルダは何もしない。"""
        if os.path.isdir(path):
            return None
        kind = classify_file(path, H["image_exts"])
        if kind == "image":
            H["open_image"](path)
        elif kind == "pipeline":
            H["open_pipeline"](path)
        elif kind == "python":
            H["open_python"](path)
        elif kind == "params":
            H["open_params"](path)
        else:
            H["flash"](tr("%s is not opened here (other file). Right-click: Show in file manager") % os.path.basename(path))
        return kind

    def _on_double(idx):
        it = model.itemFromIndex(idx)
        if it is not None and not it.data(UR + 2) and it.data(UR) != PLACEHOLDER:
            activate(it.data(UR))
    tree.doubleClicked.connect(_on_double)

    def selected_paths():
        out = []
        for idx in tree.selectionModel().selectedRows():
            it = model.itemFromIndex(idx)
            if it is not None and it.data(UR) and it.data(UR) != PLACEHOLDER:
                out.append(it.data(UR))
        return out

    # ---- 作る・名前の変更・移す ----------------------------------------------------------------------------------
    def _target_dir(paths):
        """新規の置き場: 選んだフォルダ(またはファイルの親)、無ければプロジェクトの直下。"""
        if paths:
            p = paths[0]
            return p if os.path.isdir(p) else os.path.dirname(p)
        return S["root"]

    def ensure_kind_dir(kind, ask=True):
        """種類の置き場所(例: pipelines/)を返す。サブフォルダが無ければ、黙って作らず聞く(断られたらプロジェクトの直下)。
        プロジェクトが開いていなければ None。"""
        if not S["root"]:
            return None
        d = place_for(S["root"], kind)
        if d is None:
            return S["root"]
        if os.path.isdir(d):
            return d
        if ask and H["confirm"](tr("Create folder"), tr("The project has no %s/ folder yet. Create it?") % folder_for(kind)):
            try:
                os.makedirs(d, exist_ok=True)
                reload()
                return d
            except OSError as exc:
                H["warn"](tr("Could not create the folder"), str(exc))
        return S["root"]

    def new_pipeline(paths=None):
        if not S["root"]:
            return None
        base = ensure_kind_dir("pipeline") if not paths else _target_dir(paths)
        name = H["ask_text"](tr("New pipeline"), tr("File name"), "pipeline.json")
        if not name:
            return None
        try:
            name = validate_name(name)
            if not name.lower().endswith(".json"):
                name += ".json"
            dest = resolve_inside(S["root"], os.path.relpath(os.path.join(base, name), S["root"]))
            if os.path.exists(dest):
                raise ValueError("%s already exists; nothing was overwritten" % name)
            with open(dest, "x", encoding="utf-8") as fh:
                fh.write(new_pipeline_text())
        except (ValueError, OSError) as exc:
            H["warn"](tr("Could not create the pipeline"), str(exc)); return None
        reload()
        H["flash"](tr("created %s") % name)
        return dest

    def new_folder(paths=None):
        if not S["root"]:
            return None
        base = _target_dir(paths)
        name = H["ask_text"](tr("New folder"), tr("Folder name"), "")
        if not name:
            return None
        try:
            name = validate_name(name)
            dest = resolve_inside(S["root"], os.path.relpath(os.path.join(base, name), S["root"]))
            if os.path.exists(dest):
                raise ValueError("%s already exists" % name)
            os.makedirs(dest)
        except (ValueError, OSError) as exc:
            H["warn"](tr("Could not create the folder"), str(exc)); return None
        reload()
        return dest

    def rename(path):
        if not S["root"] or not is_inside(S["root"], path) or os.path.realpath(path) == os.path.realpath(S["root"]):
            return None
        old = os.path.basename(path)
        name = H["ask_text"](tr("Rename"), tr("New name"), old)
        if not name or name == old:
            return None
        try:
            name = validate_name(name)
            dest = resolve_inside(S["root"], os.path.relpath(os.path.join(os.path.dirname(path), name), S["root"]))
            if os.path.exists(dest):
                raise ValueError("%s already exists; nothing was overwritten" % name)
            os.rename(path, dest)
        except (ValueError, OSError) as exc:
            H["warn"](tr("Could not rename"), str(exc)); return None
        reload()
        return dest

    def move_standard(path):
        kind = classify_file(path, H["image_exts"])
        want = mismatch(S["root"], path, kind)
        if not want:
            return None
        if not os.path.isdir(os.path.join(S["root"], want)) and not H["confirm"](
                tr("Create folder"), tr("The project has no %s/ folder yet. Create it?") % want):
            return None
        try:
            dest = move_to_standard(S["root"], path, kind)
        except (ValueError, OSError) as exc:
            H["warn"](tr("Could not move"), str(exc)); return None
        reload()
        H["flash"](tr("moved to %s/") % want)
        return dest

    def copy_path(path, relative=False):
        text = os.path.relpath(path, S["root"]).replace("\\", "/") if (relative and S["root"]) else path
        QtWidgets.QApplication.clipboard().setText(text)
        H["flash"](tr("copied: %s") % text)
        return text

    # ---- 右クリック(項目の表は試験でも使う)---------------------------------------------------------------------------
    def menu_spec(paths):
        """右クリックの項目 ``[(名前, 有効か, ヒント, 動作)]``。削除は入れない。"""
        one = paths[0] if len(paths) == 1 else None
        files = [p for p in paths if not os.path.isdir(p)]
        kinds = [classify_file(p, H["image_exts"]) for p in files]
        spec = []
        spec.append((tr("Open"), bool(files) and len(files) == len(paths), tr("Open the file in the place its kind belongs to"),
                     lambda: [activate(p) for p in files]))
        cmp_ok = len(paths) >= 2 and len(files) == len(paths) and all(k == "image" for k in kinds)
        spec.append((tr("Compare side by side"), cmp_ok,
                     tr("Select two or more images to see them side by side") if not cmp_ok
                     else tr("Show the selected images side by side"),
                     lambda: H["compare_images"](files)))
        spec.append((tr("New pipeline"), bool(S["root"]), tr("Create an empty pipeline file (in pipelines/ unless you chose a folder)"),
                     lambda: new_pipeline(paths if one and os.path.isdir(one) else None)))
        spec.append((tr("New folder"), bool(S["root"]), tr("Create a folder inside the project"), lambda: new_folder(paths)))
        spec.append((tr("Rename"), one is not None, tr("Rename this file or folder (it stays inside the project)"),
                     lambda: rename(one)))
        want = mismatch(S["root"], one, kinds[0]) if (one and files and S["root"]) else None
        if want:
            spec.append((tr("Move to %s/") % want, True, tr("The content does not match the folder it is in. Move it to the standard folder"),
                         lambda: move_standard(one)))
        spec.append((tr("Show in file manager"), one is not None, tr("Show the file in the file manager (it is not opened)"),
                     lambda: H["reveal"](one)))
        spec.append((tr("Copy path"), one is not None, tr("Copy the full path"), lambda: copy_path(one)))
        spec.append((tr("Copy relative path"), one is not None and bool(S["root"]), tr("Copy the path relative to the project folder"),
                     lambda: copy_path(one, True)))
        return spec

    def _context(pos):
        idx = tree.indexAt(pos)
        if idx.isValid() and not tree.selectionModel().isSelected(idx):
            tree.setCurrentIndex(idx)
        paths = selected_paths()
        menu = QtWidgets.QMenu(tree)
        menu.setToolTipsVisible(True)
        for label, enabled, tip, fn in menu_spec(paths):
            a = menu.addAction(label); a.setEnabled(bool(enabled)); a.setToolTip(tip)
            a.triggered.connect(lambda _=False, f=fn: f())
        menu.exec(tree.viewport().mapToGlobal(pos))
    tree.customContextMenuRequested.connect(_context)

    # ---- フォルダのドロップ(このパネルへ)------------------------------------------------------------------------------
    class _DropFilter(QtCore.QObject):
        def eventFilter(self, obj, ev):
            t = ev.type()
            if t in (QtCore.QEvent.DragEnter, QtCore.QEvent.DragMove, QtCore.QEvent.Drop):
                md = ev.mimeData()
                dirs = [u.toLocalFile() for u in md.urls() if u.isLocalFile() and os.path.isdir(u.toLocalFile())] if md.hasUrls() else []
                if dirs:
                    if t == QtCore.QEvent.Drop:
                        open_dir(dirs[0])
                    ev.acceptProposedAction()
                    return True
            return False
    drop_filter = _DropFilter(parent)
    for w in (empty, full, tree.viewport(), tree, stack):
        w.setAcceptDrops(True); w.installEventFilter(drop_filter)

    retranslate()
    stack.setCurrentIndex(0)
    return {
        "widget": parent, "stack": stack, "tree": tree, "model": model, "filter": filt, "kind_box": kind_box,
        "buttons": {"open": b_open, "new": b_new, "sample": b_sample, "close": b_close},
        "empty_text": empty_text, "head": head,
        "open_dir": open_dir, "close": close_project, "restore": restore, "choose_dir": choose_dir,
        "new_project": new_project, "open_sample": open_sample, "activate": activate, "reload": reload,
        "root": lambda: S["root"], "recent": recent, "menu_spec": menu_spec, "selected": selected_paths,
        "ensure_kind_dir": ensure_kind_dir, "new_pipeline": new_pipeline, "new_folder": new_folder,
        "rename": rename, "move_standard": move_standard, "copy_path": copy_path, "retranslate": retranslate,
        "hooks": H, "state": S,
        "names": lambda: [(model.item(r).text()) for r in range(model.rowCount())],
        "expand_all_top": lambda: [tree.expand(model.item(r).index()) for r in range(model.rowCount())],
    }
