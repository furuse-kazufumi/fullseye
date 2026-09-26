<!-- i18n-source-sha: 8fe28ab585e4 -->
# Fullseye als RAG eines KI-Assistenten nutzen (für Claude Code)

[日本語](./AI_RAG_GUIDE.md) · [English](./AI_RAG_GUIDE.en.md) · [简体中文](./AI_RAG_GUIDE.zh.md) · [繁體中文](./AI_RAG_GUIDE.tw.md) · [한국어](./AI_RAG_GUIDE.ko.md) · **Deutsch**

Die empfohlene Nutzung von Fullseye besteht darin, es **als Wissensbasis (RAG) eines KI-Coding-Assistenten** einzusetzen. Da jeder op eine maschinenlesbare Markdown-Notiz besitzt (`docs/ops`, die einzige Quelle der Wahrheit), ist **keine** zusätzliche Vektordatenbank oder kein Embedding-Dienst nötig. Jede Umgebung, in der grep möglich ist, ist bereits ein RAG.

Es werden drei Einführungsstufen bereitgestellt. **Tier 0/1 haben keinerlei externe Abhängigkeiten** (sie kommen allein mit dem Fullseye-Repository aus).

> **Nutzung über PyPI**: In einer Umgebung, in der `pip install fullseye` ausgeführt wurde, steht das Konsolenskript **`fullseye-rag`** zur Verfügung. Bei einem Checkout (Clone / `pip install -e .`) wird der vollständige `docs/ops`-Korpus an das Skill gepinnt; bei einer reinen Wheel-Installation wird stattdessen die mitgelieferte `OP_CATALOG.md` (der vollständige Op-Katalog für die KI) gepinnt (wer später die vollständigen Pro-Op-Notizen möchte, klont einfach das Repository und führt es erneut aus). Aktualisiert wird mit `py -3.11 tools/update_fullseye.py` (verweigert einen dirty Tree, `--ff-only`, aktualisiert das Skill über ein Backup und rührt die Studio-Einstellungen nicht an — so konzipiert, dass es die Umgebung nicht zerstört).

---

## Tier 0: Einfach das Repository öffnen (null Schritte)

Öffnet man einen Checkout des Fullseye-Repositorys in Claude Code, lassen sich `docs/ops/INDEX.md` und die Pro-Op-Notizen direkt durchsuchen und referenzieren. Der Korpus ist Repository-Inhalt (nicht im Wheel enthalten) — wer also nur per pip installiert hat, sollte zusätzlich das Repository klonen.

```
docs/ops/2d/<category>/<op>.md   # Aufrufform, Typvertrag, HALCON-Alias, Literatur, verwandte Ops
docs/ops/3d/<category>/<op>.md
docs/ops/INDEX.md                # Gesamtinhaltsverzeichnis, automatisch durch Traversieren der Ordnerhierarchie erzeugt
docs/ops/2d/guides/<family>.md   # Anleitungen für 13 Familien (Formeln, Diagramme, Zitate kanonischer Quellen)
docs/OP_INDEX.json               # maschinenlesbarer Index der Registry
```

## Tier 1: Als residentes Skill halten (empfohlen · mitgeliefertes Installationsskript)

Wer beim Arbeiten im eigenen Projekt Fullseye heranziehen möchte, führt einmalig das mitgelieferte Setup-Skript aus:

```bash
py -3.11 tools/setup_claude_rag.py              # Installation (erneuter Lauf = Aktualisierung)
py -3.11 tools/setup_claude_rag.py --uninstall  # Deinstallation
```

Das mitgelieferte Skill `skills/fullseye-ops` wird nach `~/.claude/skills/fullseye-ops` kopiert, und die Zeile `FULLSEYE_REPO =` in SKILL.md wird **automatisch auf den absoluten Pfad dieses Checkouts fixiert** (damit die KI unabhängig davon, in welchem Projekt sie arbeitet, weiß, wo sich der Korpus befindet). Bei einem Checkout, in dem der Korpus (`docs/ops`) nicht gefunden wird, wird die Installation verweigert (fail-closed).

Von da an ruft Claude Code bei Themen aus Bildverarbeitung und geometrischem Sehen dieses Skill automatisch auf und arbeitet nach dem Ablauf: `docs/ops` durchsuchen (retrieve) → Ops auswählen, deren Typen (sort) zusammenpassen, und implementieren → mit dem mitgelieferten Worked Example verifizieren. Der Skill-Text selbst ist die "Bedienungsanleitung für die KI". Wer es manuell installieren möchte, kann `skills/fullseye-ops` einfach nach `~/.claude/skills/` kopieren — das funktioniert ebenfalls (nur ohne die Pfadfixierung sucht die KI den Repository-Ort jedes Mal neu).

## Tier 2 (optional): geclusterter Korpus — eine erweiterte Form mit externen Werkzeugen

Man kann außerdem einen "navigierbaren Korpus" erstellen, der die **2.195 Notizen** hierarchisch in thematische Cluster gliedert und jedem Cluster eine LLM-Zusammenfassung beigibt. Intern verwenden wir dafür `corpus2skill` aus einem Fork von [RAPTOR](https://github.com/gadievron/raptor) (TF-IDF + k-means + LLM-Zusammenfassung), aber **das ist eine optionale Optimierung, keine Voraussetzung**. Die einzige Anforderung lautet: "`docs/ops` als Eingabe nehmen und eine SKILL.md-Hierarchie pro Cluster ausgeben" — jedes gleichwertige Werkzeug kann also einspringen.

Beispiel für die erneute Aufnahme (nach einer Aktualisierung der Notizen) — ehrlich genau so dokumentiert, wie wir es intern betreiben:

```powershell
$env:RAPTOR_DIR="<path-to-raptor-checkout>"
py -3.11 raptor_corpus2skill.py --source <fullseye>/docs/ops --name fullseye_ops_corpus_v2 `
  --overwrite --max-depth 2 --max-clusters 6 --min-cluster-size 8   # benötigt ANTHROPIC_API_KEY
```

Hinweis: Ein geclusterter Korpus ist eine **Momentaufnahme zum Zeitpunkt der Aufnahme**. Wird `docs/ops` aktualisiert, veraltet er, sofern man ihn nicht erneut einliest (Tier 0/1 veralten nie, da sie stets die aktuellen Notizen lesen).

---

## Tier 3 (mitgeliefert): die Literaturschicht — Fertigungswissen auf „welche Ops“ heruntergebrochen

Eine Op-Notiz beantwortet „was tut dieser Op“, nicht „was messe ich in diesem Prozess, an diesem Teil“.
[`docs/literature/`](literature/INDEX.md) schließt diese Lücke: externe Literaturkorpora (Maschinenbau-Konstruktion,
Mechatronik-Bauteile, Fertigungsprozesse — etwa 7.000 OpenAlex-Metadatensätze), je Cluster zusammengefasst, mit **den in
jedem Cluster zu verwendenden Ops** (eine handgeschriebene Thema → Op-Tabelle, deren Op-Namen beim Erzeugen gegen die
ausgelieferten Notizen geprüft werden) und Titel / Jahr / DOI repräsentativer Arbeiten als Herkunft. Lesereihenfolge:
Prozess oder Bauteil → Literatur-Cluster → Ops → Op-Notiz (Typvertrag, lauffähiges Beispiel) → Implementierung.
Abstracts werden nicht kopiert, und Ops werden nie über Wortüberlappung gewählt (das brachte nachweislich unpassende Ops
bei Allerweltswörtern und wurde verworfen). Da die Korpora außerhalb des Repos liegen, wird nur diese Schicht mit
`tools/gen_literature_notes.py --rad-root <RAD>` neu erzeugt; `tests/test_literature_notes.py` sichert ihre Form.

---

## Warum das funktioniert (die Designbegründung)

1. **md = einzige Quelle der Wahrheit**: Die Notizen werden deterministisch automatisch aus der Registry erzeugt, und ein CI-Drift-Test erzwingt, dass die committete Notiz gleich der aus dem aktuellen Code erzeugten Notiz ist. **Das Dokument, das die KI liest, und der tatsächliche Code sind immer dieselbe Version** (Frontmatter `version` + Fingerprint).
2. **Typ-(Sort-)Vertrag**: Jede Notiz trägt `in:`/`out:` sowie "verwandte Ops, deren Typen zusammenpassen", sodass die KI eine Pipeline **unter gleichzeitiger Typprüfung** zusammensetzen kann.
3. **Verifizierbar**: Jeder Op verfügt über ein Worked Example mit Ground Truth (`examples/` / `examples_3d/`), sodass die KI ihren eigenen Vorschlag selbst ausführen und überprüfen kann.
4. **Durchgängig bis zur Anzeige**: Öffnet man Studio (`py -3.11 studio.py`), kann ein Mensch das von der KI zusammengestellte Ergebnis als Bildfenster bzw. 3D-Ansicht auf demselben Bildschirm prüfen (über `dev_open_window` u. Ä. lassen sich auch mehrere Fenster aus einem Skript heraus anordnen).
