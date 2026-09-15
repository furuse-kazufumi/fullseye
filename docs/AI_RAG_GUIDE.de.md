<!-- i18n-source-sha: b50d12a26df4 -->
# Fullseye als RAG eines KI-Assistenten nutzen (für Claude Code)

[日本語](./AI_RAG_GUIDE.md) · [English](./AI_RAG_GUIDE.en.md) · [简体中文](./AI_RAG_GUIDE.zh.md) · [繁體中文](./AI_RAG_GUIDE.tw.md) · [한국어](./AI_RAG_GUIDE.ko.md) · **Deutsch**

Die empfohlene Nutzung von Fullseye besteht darin, es **als Wissensbasis (RAG) eines KI-Coding-Assistenten** einzusetzen. Da jeder op eine maschinenlesbare Markdown-Notiz besitzt (`docs/ops`, die einzige Quelle der Wahrheit), ist **keine** zusätzliche Vektordatenbank oder kein Embedding-Dienst nötig. Jede Umgebung, in der grep möglich ist, ist bereits ein RAG.

Es werden drei Einführungsstufen bereitgestellt. **Tier 0/1 haben keinerlei externe Abhängigkeiten** (sie kommen allein mit dem Fullseye-Repository aus).

## Es gibt mehr als einen Eingang (zuerst lesen)

Mit den Dokumenten allein haben Codex und Copilot beim ersten Versuch **beide den aufgabenorientierten Index nicht gefunden** (2026-09-15). Die Ursache war dieser Leitfaden: Er enthielt keinen Verweis darauf. Es gibt vier Eingänge:

1. **Nach Aufgabe** → [`docs/CAPABILITIES.en.md`](CAPABILITIES.en.md). Eine Datei pro Aufgabe (`docs/capabilities/`) mit **empfohlener Pipeline (geordnete Ops) / Alternativen / Grenzen / Kalibrierung auf reale Maße**; `tests/test_capabilities.py` prüft, dass jeder Op existiert und dass die **Typen (in → out) von Schritt zu Schritt zusammenpassen**.
2. **Nach Op-Name oder Begriff** → [`docs/ops/INDEX.de.md`](ops/INDEX.de.md) → Familienindex → Op-Notiz.
3. **Maschinell** → `fs.op_find(query)` (Freitext, Wortstämme) / `fs.op_assist(op)` (Spezifikation, Presets, was als Nächstes anschließt) / `fs.op_path(from_sort, to_sort)` (Op-Folge von Typ A nach Typ B) / `fs.op_producers(sort)` (Ops, die diesen Typ erzeugen) / `fs.op_accepts(op)` (gemessene akzeptierte Typen); auf der Kommandozeile `fullseye has <op>` (auch mit HALCON-Namen).
4. **Indexdateien** → [`docs/OP_INDEX.json`](OP_INDEX.json) (Typvertrag jedes Ops) und die im Wheel mitgelieferte `OP_CATALOG.md`.


> **Nutzung über PyPI**: In einer Umgebung, in der `pip install fullseye` ausgeführt wurde, steht das Konsolenskript **`fullseye-rag`** zur Verfügung. Bei einem Checkout (Clone / `pip install -e .`) wird der vollständige `docs/ops`-Korpus an das Skill gepinnt; bei einer reinen Wheel-Installation wird stattdessen die mitgelieferte `OP_CATALOG.md` (der vollständige Op-Katalog für die KI) gepinnt (wer später die vollständigen Pro-Op-Notizen möchte, klont einfach das Repository und führt es erneut aus). Aktualisiert wird mit `py -3.11 tools/update_fullseye.py` (verweigert einen dirty Tree, `--ff-only`, aktualisiert das Skill über ein Backup und rührt die Studio-Einstellungen nicht an — so konzipiert, dass es die Umgebung nicht zerstört).

---

## Tier 0: Einfach das Repository öffnen (null Schritte)

Öffnet man einen Checkout des Fullseye-Repositorys in Claude Code, lassen sich `docs/ops/INDEX.md` und die Pro-Op-Notizen direkt durchsuchen und referenzieren. Der Korpus ist Repository-Inhalt (nicht im Wheel enthalten) — wer also nur per pip installiert hat, sollte zusätzlich das Repository klonen.

```
docs/CAPABILITIES.md                    # Aufgabe → Op-Kette (empfohlene Pipeline / Alternativen / Grenzen / Kalibrierung). Hier beginnen
docs/ops/<family>/<category>/<op>.md    # Aufrufform, Typvertrag, HALCON-Alias, Literatur, verwandte Ops (2d / 3d / optics / piv …)
docs/ops/INDEX.md                       # Gesamtinhaltsverzeichnis, automatisch durch Traversieren der Ordnerhierarchie erzeugt (34 Familien)
docs/ops/<family>/guides/<name>.md      # 49 Anleitungen über die 34 Familien (2-D: gallery2d_*; Formeln, Diagramme, kanonische Zitate)
docs/OP_INDEX.json                      # maschinenlesbarer Index der Registry
```

Die Zahlen (34 Familien, 49 Anleitungen, Anzahl der Notizen) sind von den ausgelieferten Dateien her gezählt; `tests/test_docs_index_reachable.py` vergleicht diese Zeile mit den Dateien auf der Platte, damit die Selbstbeschreibung dem Korpus nicht hinterherhinkt.

**Beim Lesen aus einer Windows-Shell UTF-8 erzwingen** — die Notizen sind UTF-8 ohne BOM; mit der Standard-Codepage geöffnet wird der japanische Text zu Zeichensalat, und ein Assistent, der eine Notiz nicht lesen konnte, schließt daraus, dass sie nicht existiert (bei Codex tatsächlich passiert). PowerShell: `Get-Content -Encoding utf8` und `[Console]::OutputEncoding = [Text.Encoding]::UTF8` (oder `chcp 65001`); Python: `PYTHONUTF8=1`.

## Tier 1: Als residentes Skill halten (empfohlen · mitgeliefertes Installationsskript)

Wer beim Arbeiten im eigenen Projekt Fullseye heranziehen möchte, führt einmalig das mitgelieferte Setup-Skript aus:

```bash
py -3.11 tools/setup_claude_rag.py              # Installation (erneuter Lauf = Aktualisierung)
py -3.11 tools/setup_claude_rag.py --uninstall  # Deinstallation
```

Das mitgelieferte Skill `skills/fullseye-ops` wird nach `~/.claude/skills/fullseye-ops` kopiert, und die Zeile `FULLSEYE_REPO =` in SKILL.md wird **automatisch auf den absoluten Pfad dieses Checkouts fixiert** (damit die KI unabhängig davon, in welchem Projekt sie arbeitet, weiß, wo sich der Korpus befindet). Bei einem Checkout, in dem der Korpus (`docs/ops`) nicht gefunden wird, wird die Installation verweigert (fail-closed).

Von da an ruft Claude Code bei Themen aus Bildverarbeitung und geometrischem Sehen dieses Skill automatisch auf und arbeitet nach dem Ablauf: `docs/ops` durchsuchen (retrieve) → Ops auswählen, deren Typen (sort) zusammenpassen, und implementieren → mit dem mitgelieferten Worked Example verifizieren. Der Skill-Text selbst ist die "Bedienungsanleitung für die KI". Wer es manuell installieren möchte, kann `skills/fullseye-ops` einfach nach `~/.claude/skills/` kopieren — das funktioniert ebenfalls (nur ohne die Pfadfixierung sucht die KI den Repository-Ort jedes Mal neu).

## Tier 2 (optional): geclusterter Korpus — eine erweiterte Form mit externen Werkzeugen

Man kann außerdem einen "navigierbaren Korpus" erstellen, der die **1.949 Notizen** hierarchisch in thematische Cluster gliedert und jedem Cluster eine LLM-Zusammenfassung beigibt. Intern verwenden wir dafür `corpus2skill` aus einem Fork von [RAPTOR](https://github.com/gadievron/raptor) (TF-IDF + k-means + LLM-Zusammenfassung), aber **das ist eine optionale Optimierung, keine Voraussetzung**. Die einzige Anforderung lautet: "`docs/ops` als Eingabe nehmen und eine SKILL.md-Hierarchie pro Cluster ausgeben" — jedes gleichwertige Werkzeug kann also einspringen.

Beispiel für die erneute Aufnahme (nach einer Aktualisierung der Notizen) — ehrlich genau so dokumentiert, wie wir es intern betreiben:

```powershell
$env:RAPTOR_DIR="<path-to-raptor-checkout>"
py -3.11 raptor_corpus2skill.py --source <fullseye>/docs/ops --name fullseye_ops_corpus_v2 `
  --overwrite --max-depth 2 --max-clusters 6 --min-cluster-size 8   # benötigt ANTHROPIC_API_KEY
```

Hinweis: Ein geclusterter Korpus ist eine **Momentaufnahme zum Zeitpunkt der Aufnahme**. Wird `docs/ops` aktualisiert, veraltet er, sofern man ihn nicht erneut einliest (Tier 0/1 veralten nie, da sie stets die aktuellen Notizen lesen).

---

## Warum das funktioniert (die Designbegründung)

1. **md = einzige Quelle der Wahrheit**: Die Notizen werden deterministisch automatisch aus der Registry erzeugt, und ein CI-Drift-Test erzwingt, dass die committete Notiz gleich der aus dem aktuellen Code erzeugten Notiz ist. **Das Dokument, das die KI liest, und der tatsächliche Code sind immer dieselbe Version** (Frontmatter `version` + Fingerprint).
2. **Typ-(Sort-)Vertrag**: Jede Notiz trägt `in:`/`out:` sowie "verwandte Ops, deren Typen zusammenpassen", sodass die KI eine Pipeline **unter gleichzeitiger Typprüfung** zusammensetzen kann.
3. **Verifizierbar**: Jeder Op verfügt über ein Worked Example mit Ground Truth (`examples/` / `examples_3d/`), sodass die KI ihren eigenen Vorschlag selbst ausführen und überprüfen kann.
4. **Durchgängig bis zur Anzeige**: Öffnet man Studio (`py -3.11 studio.py`), kann ein Mensch das von der KI zusammengestellte Ergebnis als Bildfenster bzw. 3D-Ansicht auf demselben Bildschirm prüfen (über `dev_open_window` u. Ä. lassen sich auch mehrere Fenster aus einem Skript heraus anordnen).
