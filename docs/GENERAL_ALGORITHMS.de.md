<!-- i18n-source-sha: bd321cfbdaaa -->
# Allgemeine Algorithmen implementierbar machen — algo-c Kompatibilitäts-Roadmap

[日本語](./GENERAL_ALGORITHMS.md) · [English](./GENERAL_ALGORITHMS.en.md) · [简体中文](./GENERAL_ALGORITHMS.zh.md) · [繁體中文](./GENERAL_ALGORITHMS.tw.md) · [한국어](./GENERAL_ALGORITHMS.ko.md) · **Deutsch**

> Nutzerwunsch (2026-08-16): Wie bei <https://github.com/okumuralab/algo-c> (Haruhiko Okumura,
> vollständiger Quellcode zu „[Revidierte Neuauflage] Standard-Algorithmen-Lexikon in der Sprache C")
> sollen auch **allgemeine Algorithmen** in Fullseye implementiert werden können.
>
> **Ehrliche Einschätzung des Ist-Zustands**: Fullseye ist derzeit eine **Bild-Algorithmus-Design-KI**
> (op-Registry = sort von image/region/feature/contour/volume, Evolution + Holdout-Gate + Python→C-Codegen).
> Allgemeine Algorithmen (Sortieren/Suchen/Graphen/Zahlentheorie/Kryptographie/Kompression) passen nicht auf
> das Bild-sort, daher ist eine **Erweiterung von Sprache, Typen und Codegen** nötig.
> Das ist Arbeit über mehrere Sessions. Dieses Dokument ist der **verbindliche Plan** dafür
> (das Grunddokument, das die nächste Session mit vollem Kontext ausführt).

## Kategorien von algo-c (Buch-TOC · Implementierungs-Zielkarte)
※ Als verbindliche, vollständige Abdeckung gilt das `/src` des Repos.

| Bereich | Repräsentative Algorithmen | Aufnahme in Fullseye |
|---|---|---|
| Numerik | Gleichungen (Bisektion/Newton), numerische Integration (Simpson/Romberg), lineare Gleichungssysteme (Gauss/LU), Interpolation (Spline), FFT | vorhandenes `dsp` (FFT) + neue `numeric`-op-Familie |
| Zufallszahlen · Statistik | Mersenne Twister, Verteilungen, Kennzahlen | neue `rng`/`stat`-op (deterministischer Seed) |
| Sortieren | quick/heap/merge/shell/radix | neue `array`-Sortierung + `seq`-Typ |
| Suchen | Binärsuche, Hashing, BST/AVL/B-Baum | neue `array`/`map`-op |
| Zeichenketten | KMP/BM/Rabin-Karp, Editierdistanz, reguläre Ausdrücke | neuer `text`-Typ + op |
| Graphen | DFS/BFS, Dijkstra, Warshall-Floyd, MST, maximaler Fluss | neuer `graph`-Typ + op |
| Geometrie | konvexe Hülle, Streckenschnitt, Voronoi | vorhandenes `pcseg`/Geometrie + neu `geom2d` |
| Zahlentheorie · Kryptographie | Primzahlen, GGT, RSA, MD5/SHA, AES | neu `numtheory`/`crypto` (zu Lehrzwecken · honest disclosure) |
| Datenkompression | Huffman, LZ/LZW, arithmetische Codierung | neue `compress`-op |
| DP/Suche | 8-Damen, Rucksackproblem, DP | Kontrollfluss von fscript + `array` |

## Implementierungsarchitektur (verbindliche Ausrichtung)
Die bestehenden Ressourcen von Fullseye werden auf das Allgemeine erweitert. **Der Fokus auf Bild-KI wird nicht verwässert** (allgemeine op sind ein separater Tier / opt-in).

1. **Erweiterung des Typsystems**: Zu den aktuellen 6+1 sort (image/region/feature/contour/match/any/volume)
   kommen **`seq` (1-D-Array)/`text` (Zeichenkette)/`graph`/`scalar`** hinzu (sort in `ops.py` · `fslib`-Typen).
2. **fscript zur Allgemeinsprache machen**: if/for/while, Zuweisung und Tupel existieren bereits. **Array-/String-
   Literale, Indizierung, Prozedur (Funktion)** werden schrittweise ergänzt (der Sprachumfang war bisher bewusst
   eingeschränkt, daher wird der allgemeine Tier in einem separaten Profil freigeschaltet). Verbindliches
   Dokument = die A/B-Verzweigung in `docs/FSCRIPT_DECISION.md` erneut prüfen.
3. **Erweiterung der op-Registry**: Jeder Algorithmus von algo-c wird als **op** (name/in-out-sort/params/**c_stmt**)
   registriert. Der bestehende Python→C-Codegen (`engine.to_python`/`to_c`) + **difftest** (honest gate: Python als
   Oracle, C wird gegen Diff geprüft) werden unverändert weiterverwendet → **„kann als C implementiert werden"
   wird durch reale Messung garantiert**.
4. **Honest Gate**: Der C-Code von algo-c wird als Referenzimplementierung an `difftest` übergeben und gegen den
   generierten C-Code von Fullseye auf numerische/Bit-Übereinstimmung geprüft (Erweiterung des bestehenden Gates).
   **Die Lizenz des Originalcodes** (algo-c = Buchbeilage, Nutzungsbedingungen sind zu prüfen) wird respektiert,
   **keine Abschrift, sondern Neuimplementierung aus der Spezifikation** (Offenlegungspolitik).

## Phasenplan (ab der nächsten Session)
- **P1**: `seq`/`scalar`-Typen + 3 Sortierarten (quick/heap/merge) als op + C-Codegen + difftest.
  = minimaler Nachweis, dass „Fullseye auch für allgemeine Algorithmen C generieren kann".
- **P2**: Numerik-op-Familie (Bisektion/Newton/Simpson/Gauss).
- **P3**: Zeichenketten (KMP/BM/Editierdistanz) + `text`-Typ.
- **P4**: Graphen (Dijkstra/BFS/MST) + `graph`-Typ.
- **P5**: Kompression/Zahlentheorie/Kryptographie (zu Lehrzwecken · honest disclosure, keine Abschrift).
- Für jede Phase gilt: Das Evolutions-Gate ist nicht anwendbar (allgemeine op sind deterministisch, keine
  Holdout-Evolution), **die C-Übereinstimmung wird via difftest honest gemessen**, im op-Browser von Studio
  wird der neue Tier angezeigt.

## Ehrliche Grenzen und Disziplin
- **Keine Abschrift**: Der C-Code von algo-c dient als Referenz, die **Neuimplementierung erfolgt aus der
  Spezifikation** (`feedback_provenance_research_method`). Kein Code wird übernommen, bevor die Lizenz geklärt ist.
- **Der Fokus auf Bild-KI wird nicht verwässert**: Allgemeine op sind ein opt-in Tier. Der Nordstern
  (vollständige Abdeckung von Bild-op auf HALCON-Niveau + honest Holdout) bleibt unverändert.

---

## P1-Abschlussbericht (2026-08-16, Opus5[1m]/ultracode)
**Minimaler Nachweis erreicht: „Fullseye kann auch für allgemeine Algorithmen C generieren und die
C-Übereinstimmung honest messen."**

- **Neuer Tier (vollständig getrennt von der Bild-REGISTRY · opt-in)** = `algo.py`. Die Typen `seq`
  (1-D-Zahlenfolge)/`scalar` (einzelne reelle Zahl) wurden neu eingeführt. Da `ops.REGISTRY` für Bilder in
  keiner Weise berührt wird, sind Evolutionssuche und Wave-0-Champion-Pinning unbeeinflusst (durch Tests belegt).
- **op (5)**: 3 Sortierarten `quicksort` (Hoare/Median-of-three/Lomuto/expliziter Stack) · `heapsort` (Williams
  1964, binärer Max-Heap) · `mergesort` (von Neumann 1945, top-down, stabil) = `seq→seq`. Zusätzlich erhält der
  `scalar`-Typ mit den Reduktionen `seq_max`/`seq_min` (`seq→scalar`, reihenfolgeunabhängig und exakt) eine
  Aufgabe. **Alle vollständig aus der Spezifikation neu implementiert** (der algo-c-Quellcode wurde nicht
  abgeschrieben · für jede op ist `provenance` dokumentiert).
- **Single Source of Truth**: Jede op hält ihren Python- und C-Rumpf **als String** vor, die In-Process-Referenz
  kompiliert über `algo.py_fn` denselben String, `algo_codegen` emittiert denselben String als eigenständige
  `.py`/`.c`-Datei. → Das getestete Oracle und das ausgelieferte Artefakt driften nicht auseinander (durch den
  Test `test_emitted_python_*` belegt).
- **Codegen** = `algo_codegen.py` (`emit_python`/`emit_c`. Der C-Code ist Funktion + Binär-I/O-Treiber =
  ein vollständig kompilierbares Einzelprogramm).
- **Honest Gate** = `algo_difftest.py` (2 reale Messungen, kein Deferred-Skip):
  (1) Python-Referenz **== numpy-Oracle** (`np.sort`/`np.max`/`np.min`), (2) generiertes **C == Python bitgenau**
  (Holdout = 10 Randfälle + 40 Zufallsfälle). Da diese op nur vorhandene Doubles verschieben/auswählen, ist die
  korrekte Implementierung bitgenau identisch (tol=0.0).
- **★Reale Messung (2026-08-16, `zig cc` = `python -m ziglang cc`, ziglang 0.16.0 via pip installiert)**:
  Für alle 5 op **Python-Diff 0,00e+00 / C-vs-Python-Diff 0,00e+00 / passed=True** (echte Kompilierung → echter
  Lauf → Bit-Vergleich). = „C-Übereinstimmung honest gemessen" als **echte Messung, kein Deferred-Skip** erreicht.
- **Fail-closed**: Ohne Toolchain → die C-Hälfte wird honest übersprungen (die Python-Hälfte läuft). Bei
  Kompilier-/Laufzeitfehler → Gate FAIL (kein neutrales Skip. Durch den Test
  `test_difftest_compile_error_fails_closed` belegt).
- **Fassade**: `fullseye.algo_ops()/run_algo()/algo_to_c()/algo_to_python()/algo_difftest()`
  (+ `api.py`). **Skill** = im Abschnitt „General algorithms (algo-c tier)" von
  `~/.claude/skills/image-processing/SKILL.md` ergänzt (von Subagenten nutzbar).
- **Tests**: `tests/test_algo.py` (42 Fälle = Registry-Konsistenz · Python==sorted/Oracle · Stabilität ·
  Single Source of Truth · C-Bit-Übereinstimmung [bei vorhandener Toolchain] · Fail-closed bei Compile-Fehler ·
  keine Kontamination der Bild-Registry · Fassade).
- **Ehrliche Grenzen**: ① Zahlenfolgen mit NaN werden aus dem Holdout ausgeschlossen, da die Konvention beim
  Vergleichssortieren zwischen Python/C/numpy divergiert (offen gelegt). ② **Operationen, bei denen Kumulation
  (z. B. Summen von Gleitkommazahlen) Reihenfolgeabhängigkeit erzeugt, sind nicht Teil von P1** (seq_max/min
  sind exakt). ③ Die Integration von CLI-Subkommandos (`imgevolve.py algo ...`) und die Tier-Anzeige im
  Studio-op-Browser folgen in einer späteren Phase (P1.5). ④ Die Versprachlichung von Array/Prozedur in fscript
  (Architekturpunkt 2 des Design-Dokuments) liegt außerhalb des P1-Umfangs (separater Track).

## Verstärkung nach der P1-Adversarial-Review (2026-08-16, [[feedback_no_solo_ai_judgment]])
Für den in dieser Session selbst geschriebenen Code wurde eine unabhängige Adversarial-Review durchgeführt
(Workflow mit 4 Linsen = Algorithmus-Korrektheit / Codegen · C-Sicherheit / Gate-Gesundheit / Integration ·
Fokus-Sicherheit, 22 Findings). Alle Findings habe ich selbst am realen Code verifiziert (v11-Disziplin) und
die echten Mängel behoben:
- **[HIGH] Fail-open des Gates (NaN/vorzeichenbehaftete Null)**: `_max_diff_*` unterdrückte mit
  `max(0.0, nan)=0.0` die NaN-Differenz und behauptete fälschlich „Bit-Übereinstimmung" (real reproduziert)
  → getrennt in **(1) Python×Oracle = Wertvergleich, aber fail-closed bei nicht-endlichen Werten (inf, keine
  Toleranz durchlässt), (2) C×Python = echter Bit-Vergleich (rohe IEEE-Float64-Bytes = erkennt auch
  vorzeichenbehaftete Null/NaN-Payload)**. Das Feld `c_verified` unterscheidet zwischen „echt kompiliert und
  verifiziert pass" und „ohne Toolchain unverified pass".
- **[HIGH] quicksort ist bei stark duplizierter Eingabe O(n²)** (bei Lomuto `<=` landen alle Gleichwerte auf
  einer Seite. Binärmasken-Flatten = ein realistischer Input, real gemessen quadratisch) → auf **3-Wege
  (Dutch-National-Flag)-Partitionierung + Median-of-three** in Python und C umgeschrieben (bei lauter
  Gleichwerten O(n)). Performance-Guard-Test hinzugefügt (20000 identische Werte < 2 s).
- **[HIGH] das generierte C-`heapsort` kollidiert mit der `heapsort()`-Funktion aus BSD `<stdlib.h>`**
  (nicht kompilierbar unter macOS/BSD, real mit `zig cc -target x86_64-macos` gemessen) → das C-Symbol wurde
  in **`heapsort_asc`** umbenannt (analog zu `mergesort_asc`). **Cross-Compile-Test für macOS für alle op**
  hinzugefügt (Regressionsschutz).
- **[LOW] 3 Fail-open/UB-Fälle in C**: Bei Malloc-Fehlschlag in mergesort wurde unsortierte Ausgabe
  geliefert → **Fallback auf In-place-Insertion-Sort (fail-closed · Stabilität erhalten)** / bei heapsort
  Integer-Overflow bei `2*root+1` → auf **long long** umgestellt / bei 32-Bit-`len` im Treiber Size-t-Wrap
  → **Obergrenzenprüfung `SIZE_MAX/sizeof(double)` + `<stdint.h>`**.
- **[MED] test_mergesort_is_stable war inhaltsleer** (Wertvergleich = jede Sortierung besteht) →
  umgeschrieben auf reale Beobachtung der Stabilität durch **Erhaltung der Reihenfolge vorzeichenbehafteter
  Nullen** (erkennt Regression zu instabilem `<`). Auch ein **No-Mutation-Test** hinzugefügt (`run(a)`
  zerstört die Liste des Aufrufers nicht).
- **[MED] Holdout zu klein · zu wenig Duplikate** → große All-Equal- (300)/Binär- (300)/Few-Distinct-Fälle
  (300) + Zufallsdaten mit vielen Duplikaten hinzugefügt (das C-Gate prüft nun real Duplikat-/Größenregime).
- **[MED/Ehrlichkeit] NaN-Konvention nicht dokumentiert** → im Modul-Docstring und in den op-Docstrings
  „NaN-frei vorausgesetzt · nicht-endliche Werte führen im Gate zu Fail-closed" vermerkt. Bei seq_max/min
  wurde „order-independent" zu „order-independent bei NaN-freier Eingabe" präzisiert.
- **Angrenzender bestehender Ship-Bug**: `sample_images` (von Studio zur Laufzeit importiert) fehlt in den
  `py-modules` von `pyproject.toml` = verschwindet in nicht-editierbaren Wheels → ergänzt (mit echtem
  Wheel-Build verifiziert).
- Tests **43→58** (Bit-Check · Fail-closed · macOS-Cross-Compile · Duplikat-Performance · No-Mutation ·
  c_verified · Beobachtung der Stabilität ergänzt). Difftest für alle op erneut ausgeführt = für Python und C
  Diff 0,0 · Bit-Übereinstimmung · passed=True.
- **Nicht behoben (Nutzerentscheidung, bestehendes Problem außerhalb des P1-Umfangs)**: (a) das Glob-Muster
  `"*"` in `[tool.setuptools.package-data]` von `pyproject.toml` kann `studio_assets/`·`data/` auf oberster
  Ebene nicht ins Wheel aufnehmen (Studio-i18n/op-Hilfe/Beispielbilder fehlen im installierten Wheel =
  bestehend, benötigt MANIFEST.in oder eine Design-Änderung der Paketierung) / (b) `fullseye.__all__` fehlen
  18 pcseg-Namen der api (fallen beim Star-Import weg = bestehend). **Der algo-Tier ist davon nicht betroffen**
  (algo* wird über py-modules zuverlässig mitgeliefert · die Fassade ist konsistent).

## Weiter (ab P2)
- **P1.5a (erledigt, 2026-08-16)**: Das Subkommando `imgevolve.py algo <list|run|emit-c|emit-py|difftest>`
  wurde hinzugefügt (einheitlicher CLI-Einstiegspunkt. `algo run quicksort --seq 3,1,2` /
  `algo emit-c mergesort` / `algo difftest all`). 2 CLI-Regressionstests + CLI-Beispiele im Skill aktualisiert.
- **P1.5b (abgeschlossen 2026-08-17)**: Im op-Browser von Studio wird der general-(algo)-Tier
  **schreibgeschützt angezeigt** (Bericht unten).
- **P2 (abgeschlossen 2026-08-16)**: Numerik-op auf Basis der seq/scalar-Typen. **simpson / bisection /
  newton** (Polynom · Stichproben werden in der Eingabe-seq eingebettet = seq→scalar, läuft über den
  bestehenden Reduce-Treiber) + **gauss_solve** (Gauss-Elimination mit Teilpivotisierung für lineare
  Gleichungssysteme = P2-Abschlussbericht unten). Honest Gate = **C-vs-Python bitgenau** (derselbe Algorithmus
  + `-ffp-contract=off` zur Unterdrückung von FMA) / **Python-vs-Oracle mit numerischer Toleranz**
  (`AlgoOp.tol`) gegen ein unabhängiges Oracle (simpson=scipy / Nullstellensuche=Residuum |p(root)| /
  gauss=`np.linalg.solve`). Fail-soft wird honest dokumentiert.
- **P3 (abgeschlossen 2026-08-17)**: String-op (P3-Abschlussbericht unten). Der `text`-Typ wird nach der
  Konvention „Codepoint-Folge, übertragen als float64" (`text_to_seq`/`seq_to_text`) auf dem bestehenden
  Float64-Harness realisiert, ohne einen neuen Wire-Typ einzuführen.
- **P4 (abgeschlossen 2026-08-17)**: Graph-op (components/mst_weight/dijkstra, P4-Abschlussbericht unten).
  `graph` wird als `[n, m, (u,v,w)*m]`-Paket auf dem bestehenden Harness geführt (kein neuer Wire-Typ nötig).
- **P5 (abgeschlossen 2026-08-17)**: Zahlentheorie · Kompression · Lehrzweck-Hashing (gcd_seq / sieve_primes /
  pow_mod / crc32 / rle_encode, P5-Abschlussbericht unten). Ganzzahlen werden als float64 übertragen
  (exakt <2^53), daher kein neuer Wire-Typ nötig. Alle op sind **exakt** (C bitgenau übereinstimmend und
  Python==unabhängiges Oracle bei Toleranz 0). **Kryptographie nur als Primitive** (nur modulare
  Exponentiation / CRC) = vollständiges RSA/AES/SHA benötigt Bignum/große Zustände und passt nicht auf das
  float64-seq-Harness, daher als außerhalb des Umfangs honest offengelegt.

## P3-Abschlussbericht — String-op (2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**3 String-Algorithmen dem algo-Tier hinzugefügt.** Nach der Konvention „Zeichenkette = Codepoint-Folge,
übertragen als float64" (Unicode-Skalare sind < 2^53, daher exakt) **passt dies ohne Änderung auf das
bestehende Float64-Binär-Harness** (kein neuer Wire-Typ nötig). Werte werden nur auf Gleichheit verglichen
(bei ganzzahligen Codes exakt) · Position/Distanz sind exakte Ganzzahlen → **C-vs-Python bitgenau UND
Python-vs-Oracle EXAKT (Toleranz 0)**.

- **op (3)**: `strfind` (Knuth-Morris-Pratt = Präfix-Automat via Fehlerfunktion. Eingabe
  `[m, pattern(m), text]` → aufsteigende Liste aller Fundstellen-Startpositionen, einschließlich
  überlappender Treffer = **variable Länge, KIND_MAP**, wiederverwendet den für gauss geschaffenen
  Wire-Mechanismus für variable Länge) / `edit_distance` (Wagner-Fischer/Levenshtein, 2-zeiliges DP =
  **KIND_REDUCE** · exakte Ganzzahl) / `lcs_length` (Länge der längsten gemeinsamen Teilfolge, 2-zeiliges DP
  = KIND_REDUCE). Alle vollständig aus der Spezifikation neu implementiert (Provenance dokumentiert).
  Fail-soft = bei leerem Muster/abgeschnittener Eingabe/Muster länger als Text `[]`, bei na<0/Abschneiden `0.0`.
- **Single Source of Truth + text-Typ-Hilfsfunktionen**: `text_to_seq(s)`/`seq_to_text(seq)`
  (Codepoint↔float64) hinzugefügt.
- **Reale Messung des Honest Gate (alle 3 op passed=True · c_verified=true)**: Python==**unabhängiges Oracle**
  (strfind = naiver All-Occurrences-Scan [unabhängig von KMP] / edit·lcs = **rekursive Top-down-Memoisierung**
  [ein von der Bottom-up-2-Zeilen-DP getrennter Codepfad]) mit **Diff 0,0 (exakt)** / generiertes
  **C==Python bitgenau** (ziglang cc).
- **Work-Graph-op-Welle (Demonstration von Kandidat d)**: Für jede neue op wird ein `algo_gate`-Gate-Node
  aufgesetzt = **1 op = 1 Node**. Die 3 op wurden über `raptor-worklog add --capability tool` →
  `run-once --available tool:command` **unbeaufsichtigt fertiggestellt** (gate_ok.json erzeugt).
- **Regression**: In `tests/test_algo.py` Testgruppen für strfind/edit_distance/lcs_length (bekannte
  Lösungen · Zufallswerte×unabhängiges Oracle · Fail-soft · variable Ausgabelänge · No-Mutation ·
  Python exakt · C bitgenau). Gesamte Testsuite **4669 passed / 0 failed** (nach P2 von 4649 aus +20) ·
  ruff clean · mypy-Regression 0. Commit + Push erfolgten in dieser Session (Nutzerfreigabe 2026-08-16 vor
  dem Schlafengehen = Push-Gate geöffnet).

### Verstärkung nach der P3-String-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Unabhängige Adversarial-Review als Workflow (4 Linsen · jedes Finding wird von einem Verifikations-Agenten
am echten Code/echter Kompilierung bestätigt) = **alle 3 Findings CONFIRMED** (davon 2 mit demselben
Grundursache aus verschiedenen Linsen berichtet). Nach eigener Verifikation alle behoben:
- **[MED] Python führt `int(a[0])` vor der Bereichsprüfung aus → Inkonsistenz zu C**: Bei
  edit_distance/lcs_length wertete Python zuerst `na = int(a[0])` aus (Truncation), während C zuerst den
  rohen Double-Wert prüfte. **Für `a[0]` ∈ (-1.0, 0.0)** (z. B. -0.5) setzte Python fort mit na=0 (gültige
  leere Zeichenkette) und lieferte die reale Distanz, während C mit der Roh-Guard ablehnte und 0.0 lieferte
  → **Verletzung des Bit-Übereinstimmungsvertrags** (real mit ziglang cc gemessen: `[-0.5,65,66]` = Python
  2.0 vs. C 0.0). Da der Holdout nur nicht-negative Ganzzahlen als na enthielt, wurde dies vom Gate nicht
  erkannt.
- **[LOW] Python stürzt bei NaN im Header ab** (C ist fail-soft): `int(nan)` löst einen ValueError aus, was
  dem im op-Docstring versprochenen Fail-soft-Verhalten widerspricht (C nutzt eine NaN-false-Guard und
  liefert 0.0/`[]`). ※NaN liegt zwar „außerhalb des NaN-freien Vertrags", aber es handelt sich um denselben
  Guard-Reihenfolge-Fehler.
- **Behebung (eine Änderung für beides)**: Bei allen 3 op wurde die Python-Guard **vor** den `int()`-Aufruf
  auf den Roh-Wert verschoben (`not (x >= lo and x <= hi)` = NaN-false) = **exakte Spiegelung von C**. gauss
  hatte bereits von Anfang an die korrekte Roh-Guard (jetzt einheitlich).
- **Abdeckung der Grenzfälle**: Da dies außerhalb des vom Oracle geprüften Bereichs liegt (das Oracle liefert
  durch Truncation einen anderen Wert – genau dieser Bug), wird die **C-vs-Python-Parität bei kleinen
  negativen Werten/NaN/Overflow-Headern in einem dedizierten Test direkt fixiert**
  (`test_string_c_python_parity_on_bad_headers`) + ein No-Crash-Test für Python-Fail-soft. Die Kernbefunde zu
  Algorithmus-Korrektheit/C-Sicherheit sind 0 (KMP/DP/Speichersicherheit sind sauber).
- Nach der Review: Für alle 3 op difftest = Python exakt / C bitgenau / c_verified=true, gesamte Testsuite
  grün (unten) · ruff/mypy-Regression 0.

## P2-Abschlussbericht — gauss_solve (2026-08-16, Opus5[1m]/ultracode, `graph-loop-engineering`)
**Gauss-Elimination mit Teilpivotisierung für lineare Gleichungssysteme hinzugefügt, damit ist P2 (Numerik)
abgeschlossen.** Wie vom Nutzer angewiesen, wurde dies mit dem Skill `graph-loop-engineering` als Node im
raptor-Work-Graph modelliert und von einem Tool-Treiber unbeaufsichtigt ausgeführt (Zwei-Schichten-Prinzip:
die Breite läuft über das Difftest-Gate des Work-Graph, die Annahme der Adversarial-Findings sowie der Push
bleiben der menschliche Checkpoint der Session).

- **Neue Art `KIND_MAP` (`map_varlen`) = seq→seq mit variabler Länge**: Die bisherigen op waren nur sort
  (Eingabelänge=Ausgabelänge) / reduce (→1 Wert); bei der Lösung eines Gleichungssystems (Eingabe
  `[n, erweiterte Koeffizientenmatrix n×(n+1) row-major]` → Lösungsvektor der Länge n) unterscheiden sich
  Eingabe- und Ausgabelänge. Die C-Schnittstelle `int f(const double* a, int n, double* out)` schreibt
  out_len (≤ n) Werte in out und gibt out_len zurück (fail-soft=0).
- **Modus für variable Ausgabelänge im `algo_codegen`-Treiber**: Der KIND_MAP-Zweig schreibt
  `{int32 out_len, out_len*float64}` (gleiches Wire-Format wie sort, aber out_len≠Eingabelänge). Der
  Ausgabepuffer wird mit der Eingabelänge allokiert (der Vertrag out_len≤n garantiert die Obergrenze) +
  **Fail-closed-Clamp** auf `out_len ∈ [0,len]` (verhindert, dass eine außer Kontrolle geratene op den Leser
  über das Ende hinauslesen lässt).
- **gauss_solve (`algo.py`)**: Python-Referenz (nur stdlib · spiegelt C Index für Index) und C-Referenz sind
  eine einzige Quelle. Vorwärts-Elimination (Teilpivotisierung = Zeile mit maximalem |Element| wählen) +
  Rückwärts-Einsetzung. Singulär (Pivot bleibt 0) / fehlformt liefern fail-soft **[] / 0** (keine Exceptions).
  **Die Fließkomma-Operationsreihenfolge von Python und C stimmt exakt überein** (dieselbe Division ·
  Subtract-then-multiply · zu eliminierende Elemente exakt auf `0.0` gesetzt · Betrag über inline
  Vorzeichenumkehr, unabhängig von `math.h`/`-lm`), daher Bit-Übereinstimmung. Integer-Overflow wird durch
  `n≤46340` + `long long need` verhindert.
- **Zweistufiges Honest Gate (real gemessen)**: (1) Python **== `np.linalg.solve`** (unabhängiges Oracle ·
  gut konditionierter Holdout mit 34 Fällen = Diagonaldominanz + Zeilenvertauschung + **Pivot-erzwingende
  Fälle** [exakte Null (0,0) · sehr klein (0,0) · 3×3 mit Nulldiagonale]) → **maximale absolute Abweichung
  3,55e-15** (Toleranz 1e-9). (2) Generiertes **C == Python bitgenau** (`ziglang cc` · `-ffp-contract=off`)
  → **Diff 0,0 / c_verified=true**. Dass das **Fail-soft-Verhalten von C bei singulären/fehlformten Eingaben
  exakt mit Python übereinstimmt**, wird in einem separaten Test direkt geprüft (außerhalb des vom Oracle
  abgedeckten Bereichs, daher direkter C-vs-Python-Vergleich statt Holdout).
- **`tools/algo_gate.py` (wiederverwendbarer Gated-Stage-Runner)**: Der `CommandWorker` des Work-Graph
  entscheidet über „done" anhand von erzeugten Artefakten oder Exit-Code 0; da difftest auch bei FAIL eine
  JSON-Datei schreibt, entstand dadurch **Fail-open** (ein fehlgeschlagenes Gate galt als done). Das wurde
  geschlossen = **der Marker `gate_ok.json` wird nur bei Erfolg geschrieben, der Exit-Code entscheidet**.
  Zeigt der `produces`-Eintrag des Node auf den Marker, führt ein fehlgeschlagenes Gate zu **Fail-closed**
  und der Node schlägt fehl. Dies lässt sich direkt für die op-Wellen ab P3 verwenden (1 op = 1 Node).
- **Work-Graph-Modellierung**: `raptor-worklog add --capability tool --project imgevolve --priority 0`
  (spec = `tools/algo_gate.py --op gauss_solve --out <OUT>`, produces = `<OUT>/gate_ok.json`) →
  `run-once --available tool:command` führt **unbeaufsichtigt aus → status=done** (exit0 ·
  c_verified=true · Marker für Bit-Übereinstimmung erzeugt).
- **Regression**: In `tests/test_algo.py` wurden Testgruppen für gauss + algo_gate + C-Fail-soft +
  require_c ergänzt (Algorithmus-Tests **93 passed**), gesamte Testsuite **4649 passed / 0 failed**
  (vor der Review 4637, also +12). Für alle meine Dateien **ruff clean** · mypy-Regression 0 (bestehende
  Baseline = nur fehlende scipy/ziglang-Stubs und eine bestehende Eigenheit der difftest-Signatur, 0 aus
  meinen hinzugefügten Zeilen). Alles lokal committet, **noch nicht gepusht = menschliches Gate**.

### Verstärkung nach der P2-gauss-Adversarial-Review (2026-08-16, [[feedback_no_solo_ai_judgment]])
Für den selbst geschriebenen gauss-Code wurde eine unabhängige Adversarial-Review als Workflow durchgeführt
(4 Linsen = numerische Korrektheit / C-Sicherheit / Gate-Gesundheit / Integration · Abdeckung, jedes Finding
vom Verifikations-Agenten **real ausgeführt reproduziert**). Von 5 Findings wurden **4 CONFIRMED**, nach
eigener Code-Verifikation alle behoben:
- **[HIGH] Fail-open von algo_gate (unbekannte op)**: `marker.unlink()` in `find_algo` stand **nach** dem
  `SystemExit`, sodass der `gate_ok.json`-Marker eines alten Pass erhalten blieb → der CommandWorker
  entschied fälschlich auf **done** aufgrund vorhandener produces (tritt bei erneutem Lauf nach
  Umbenennung/Tippfehler einer op auf). → **mkdir + Löschen des veralteten Markers vor** die
  Registry-Prüfung verschoben (kein früher Exit übernimmt einen alten Pass mehr). Regressionstest
  hinzugefügt.
- **[MED] Das Gate kann Teilpivotisierung nicht widerlegen**: Der Holdout enthielt nur diagonaldominante
  Fälle (keine exakte Null als Pivot) → ein Mutant ohne Pivotsuche stimmte mit `np.linalg.solve` bis auf
  2,2e-14 überein und **bestand** (pytest fängt das ab, aber der vom Work-Graph ausgeführte algo_gate
  verwendet den difftest-Holdout und erkennt es daher nicht). → **Pivot-erzwingende Fälle** (exakte Null
  (0,0) = `[[0,1],[1,0]]` · sehr klein (0,0) = `[[1e-14,1],[1,1]]` · 3×3 mit Nulldiagonale) zum Holdout
  hinzugefügt = der Mutant ohne Pivotsuche wird nun **durch strukturelle Divergenz→inf→FAIL** widerlegt
  (selbst real gemessen bestätigt). Irreführende Kommentare ebenfalls korrigiert.
- **[MED] Pass-Marker auch bei C-Skip**: Fehlt die Toolchain, wird die C-Hälfte übersprungen (honest, aber
  **unverifiziert**), dennoch wurde allein anhand von `res["passed"]` der Marker geschrieben, und der Graph
  liest nur das Vorhandensein des Markers → **unkompiliertes C wurde zertifiziert**. →
  `require_c` (Default True) hinzugefügt = ein unverifizierter Pass schreibt kein `gate_ok.json`
  (Diagnose in `gate_unverified.json`) und ist **fail-closed**. Mit `--allow-unverified-c` explizites
  Opt-out, `--no-c` ist die bewusst schwächere Nur-Python-Gate-Variante.
- **[REFUTED] „Der wire mit out_len==0 ist ungetestet"**: Der von mir vorausschauend hinzugefügte Test
  `test_gauss_c_fail_soft_matches_python` kompiliert und führt bereits echtes C aus und deckt dies ab →
  der Verifikations-Agent bestätigte die Robustheit per Mutation und **verwarf** den Fund. Übrig blieb nur
  eine geringfügige Anmerkung zum macOS-Cross-Compile-Guard (`_ALL`→`_ALL_OPS`, damit numeric/gauss
  ebenfalls abgedeckt sind), die übernommen wurde.
Auch nach der Review: gauss-difftest = Python 3,55e-15 / C bitgenau / c_verified=true · Work-Graph-Node
(gehärtet) = done.

## P1.5b-Abschlussbericht — General-Tier schreibgeschützt in Studio anzeigen (2026-08-17, Opus5[1m]/ultracode)
**Anzeige des general-(algo)-Tiers im op-Browser.** Um den Bild-Fokus nicht zu verwässern, sind general-op
ein eigenes Berechnungsmodell für seq/scalar und daher **schreibgeschützt** (werden nicht in die
Bild-Pipeline eingefügt).
- `api.list_ops(include_algo=False)` erhielt einen Opt-in-Parameter + `api.algo_rows()` (backend="general" ·
  category "algo:*" · Tier "z_algo" wird ans Ende sortiert · halcon None · mit Provenance). **Der Default
  bleibt unverändert** (bestehende Aufrufer sehen weiterhin nur Bild-op = Fokus bleibt gewahrt).
- Studio: `all_ops = list_ops(include_algo=True)` zur Anzeige im Browser / `_op_row` mit algo-Fallback /
  `op_signature_detail`·`op_tooltip` mit general-Zweig („seq/scalar-op · keine Bild-op · Ausführung via CLI"
  + Provenance) / `on_op_selected` deaktiviert bei Auswahl einer general-op Insert/Run once/Help/a-b-Regler /
  `add_op`·`run_op_once`·Palette lehnen general per Flash ab. Mehrfache Absicherung = **`PipelineModel.add_stage`
  wirft bei der Bild-REGISTRY fail-closed einen KeyError**.
- **Adversarial-Review (2 Linsen · Ausführungsverifikation) = 3 CONFIRMED (2 mit derselben Grundursache),
  alle behoben**:
  - **[HIGH/MED] Der „Apply → pipeline"-Button des Program-Editors (HDevelop-Code) war ungeschützt**:
    `op_names` wurde aus `list_ops(include_algo=True)` abgeleitet, sodass general-Namen in Code-Parser/
    Autovervollständigung/Help-Picker durchsickerten → `apply_program` schrieb direkt `model.stages=` und
    **umging damit den Backstop von add_stage** → general-op drangen in die Pipeline ein. →
    **`op_names` auf Bild-op beschränkt** (Ausschluss bei `backend != "general"`, die Browser-Anzeige
    `all_ops` behält general) + `apply_program` erhielt eine Ablehnungs-Guard für general-Stages (mehrfache
    Absicherung).
  - **[MED] Der Picker im Help-Dialog zeigte für general-op falsche Angaben** („Two knobs a,b tune this
    operator") → dieselbe Beschränkung von `op_names` auf Bild-op entfernte general auch aus dem
    Help-Picker (die Root-Fix behebt beides).
- Regressionstests: general-Zweige in `_op_row`/Signature/Tooltip, im Offscreen-Modus zeigt der Browser
  general zwar an, aber Insert etc. bleiben deaktiviert · `win._op_names` schließt general aus · der
  Code-Parser lehnt general-Zeilen ab. Gesamte Testsuite grün · ruff net-new 0 (neue Tests sauber, der
  Flash in studio.py folgt konsistent dem `%`-Format-Idiom der Datei) · mypy-Regression 0. Auch die
  **op-Welle für Kandidat (d)** wurde demonstriert = alle 12 algo-op wurden mit 1 op = 1 Node in den
  Work-Graph geladen und mit `run-once` unbeaufsichtigt fertiggestellt.

## P4-Abschlussbericht — Graph-op (2026-08-17, Opus5[1m]/ultracode, Bonus)
**3 Graph-Algorithmen dem algo-Tier hinzugefügt** (außerhalb der ursprünglichen Kandidaten, aber ein Bonus
gemäß Nutzerwunsch „alles vorantreiben" + 7-8h Autonomie). Graphen werden in eine Eingabe-seq gepackt
(`[n, m, (u,v,w)*m]`, ungerichtet; bei dijkstra wird src vorangestellt: `[n, m, src, ...]`) und laufen so auf
dem bestehenden Float64-Harness.
- **op (3)**: `graph_components` (Union-Find · Anzahl der Zusammenhangskomponenten = KIND_REDUCE, exakte
  Ganzzahl) / `graph_mst_weight` (Kruskal · Gesamtgewicht eines minimalen Spannwaldes = KIND_REDUCE) /
  `graph_dijkstra` (kürzeste Distanzen von einer Startquelle = **KIND_MAP** · -1.0 = nicht erreichbar).
  Deterministische Union-Regel + Sortierung nach (Gewicht,Index) + Settle-Reihenfolge nach minimaler
  Distanz·minimalem Index sorgen für **C==Python bitgenaue Übereinstimmung**.
- **★Zweistufiger KIND_MAP-Treiber (Size-Probe)**: Bei dijkstra kann die Ausgabelänge n die Eingabelänge
  3+3m **übersteigen** (dünn besetzte Graphen). Der alte Treiber allokierte out mit der Eingabelänge, was
  einen Heap-OOB-Fehler verursachte → der Treiber fragt mit `f(a,n,NULL)` die Obergrenze von out_len ab,
  allokiert entsprechend und schreibt erst dann real (bei gauss/strfind/dijkstra `if(!out) return <bound>`).
- **Honest Gate**: Python == unabhängiges Oracle **scipy.sparse.csgraph**
  (connected_components/minimum_spanning_tree/dijkstra). Mit ganzzahligem Gewichts-Holdout **components
  exakt (Toleranz 0) / mst·dijkstra Toleranz 1e-9 (real gemessen 0)**. C==Python bitgenau (ziglang cc).
  Der MST/Dijkstra-Holdout verwendet einfache Graphen (um doppelte Kantenaddition in CSR zu vermeiden),
  components erlaubt Mehrfachkanten (nur Zusammenhang zählt).
- **Adversarial-Review (3 Linsen · Ausführungsverifikation) = 2 CONFIRMED (beide HIGH, Dijkstra-
  Speichersicherheit), alle behoben**: (#2) Der Ausgabepuffer hatte Eingabelängengröße → bei n>3+3m OOB-
  Schreibzugriff → durch den **zweistufigen Treiber** gelöst (bereits vor der Meldung vorsorglich behoben).
  (#1) Die src-Guard verglich rohes `sd < nd` → bei nicht-ganzzahligem nd konnte src==n durchgehen und
  out[n] OOB verursachen → **auf ganzzahliges n gebunden** (`sd < n`). 1 REFUTED (nicht erreichbare Knoten
  waren bereits über Known-Answer-/Sparse-Tests abgedeckt).  Keine weiteren Findings aus den Numerik-/
  Oracle-Linsen.
- **op-Welle**: Auch die 3 Graph-op wurden im Work-Graph als Gate modelliert (alle algo-op = 15 sind nun
  1 op = 1 Node, unbeaufsichtigt done). Gesamte Testsuite grün · ruff clean · mypy-Regression 0. Push
  erfolgte in dieser Session (Nutzerfreigabe).

## P5-Abschlussbericht — Zahlentheorie · Kompression · Lehrzweck-Hashing (2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**5 allgemeine Algorithmen dem algo-Tier hinzugefügt, damit ist die algo-c-Roadmap (P1→P5) abgeschlossen.**
Ganzzahlen werden als float64 übertragen (exakt < 2^53), daher kein neuer Wire-Typ nötig. Bit-/Ganzzahl-
Operationen werden auf der C-Seite als `unsigned long long`/`unsigned int` gecastet ausgeführt und dann
zurück nach double konvertiert (das Ergebnis ist < 2^53, also exakt). **Alle 5 op sind exakt**
(C==Python bitgenau UND Python==unabhängiges Oracle Toleranz 0).
- **op (5)**:
  - `gcd_seq` (KIND_REDUCE): GGT einer Folge nicht-negativer Ganzzahlen (Euklid · über die Folge gefaltet).
    Oracle = `math.gcd`.
  - `sieve_primes` (**KIND_MAP**): Sieb des Eratosthenes. Eingabe `[n]` (Länge 1) → aufsteigende Primzahlen
    ≤ n = **repräsentatives Beispiel für eine Ausgabe, die die Eingabelänge deutlich übersteigt**. Size-Probe-
    Obergrenze `π(n) ≤ n/2 + 1` (2 plus die ungeraden Zahlen, kein Log nötig = unabhängig von `math.h`).
    Oracle = Probedivision (unabhängiger Pfad).
  - `pow_mod` (KIND_REDUCE): Modulare Potenzierung base^exp mod m (Square-and-multiply = Primitive für
    RSA/DH, zu Lehrzwecken). Oracle = eingebautes `pow`.
  - `crc32` (KIND_REDUCE): CRC-32 (IEEE 802.3 · reflektiert · Polynom 0xEDB88320). **c_func heißt
    `crc32_ieee`** (defensiv umbenannt, um Symbolkollision mit `crc32` aus zlib/BSD zu vermeiden, vgl.
    heapsort_asc). Oracle = `zlib.crc32` (die zlib-C-Bibliothek = vollständig unabhängig).
  - `rle_encode` (**KIND_MAP**): Lauflängenkodierung → `[value, count, ...]` (**Ausgabe maximal 2× Eingabe**,
    bei lauter unterschiedlichen Werten 2n). Verlustfrei · Oracle = `itertools.groupby`.
- **★Offenlegung des honest Bereichs (pow_mod)**: Damit das uint64-Zwischenprodukt nicht überläuft, gilt
  **mod ≤ 2^32−1** (Produkt < mod² < 2^64), base/exp ≤ 2^53. Das Ergebnis < mod < 2^53 ist float64-exakt.
  Außerhalb des Bereichs fail-soft 0.0 (Roh-Guard vor `int()`, NaN-sicher).
- **★Kryptographie nur als Primitive (honest Scope)**: Vollständiges RSA/AES/SHA benötigt Bignum/große
  Zustände und passt nicht auf das float64-seq-Harness, dies wird als außerhalb des Umfangs dokumentiert.
  Die passenden Primitiven (modulare Exponentiation / CRC-Prüfsumme) werden als **Algorithmus-Offenlegung**
  bereitgestellt (kein Chiffre).
- **★Ganzzahligkeits-Guard (neu, honest Verbesserung)**: gcd_seq/pow_mod/crc32 behandeln nicht-ganzzahlige
  **Datenwerte** als fehlformt → fail-soft. `x == float(int(x))` / `x == (double)(long long)x` werden
  **kurzgeschlossen nach der Bereichsprüfung** (bei NaN/Overflow-Werten wird der Cast nicht erreicht,
  vermeidet `int(nan)`-Absturz bzw. `(long long)nan`-UB in C). Header-Werte (z. B. n bei sieve) folgen der
  gleichen Abschneidekonvention wie bei gauss/dijkstra.
- **★Zweistufige KIND_MAP-Size-Probe für 2 neue op genutzt**: sieve (Ausgabe ≫ Eingabe) · rle (Ausgabe ≤ 2×
  Eingabe) nutzen beide `if(!out) return <Obergrenze>`, sodass der Treiber die Obergrenze abfragt → allokiert
  → real schreibt. Ein dedizierter Test fixiert per echter Kompilierung/Ausführung, dass **kein Heap-OOB
  auftritt, wenn die C-Ausgabe die Eingabelänge übersteigt**.
- **Reale Messung des Honest Gate (alle 5 op passed=True · c_verified=true · ziglang cc)**: Python==
  unabhängiges Oracle **Diff 0,0 (exakt)** / generiertes **C==Python bitgenau Diff 0,0**. Bei crc32 wurde
  die Übereinstimmung mit `zlib.crc32` für alle Bytewerte, "Hello" und alle 256 Bytewerte bestätigt.
- **Work-Graph-op-Welle**: Die 5 P5-op wurden als `algo_gate`-Gate-Nodes modelliert (`1 op = 1 Node` ·
  priority 0 · tool capability) → `run-once --available tool:command` führt **5 Nodes unbeaufsichtigt zu
  done** (jeweils `gate_ok.json` = Marker für c_verified/Bit-Übereinstimmung erzeugt). = **alle 20 algo-op
  sind nun im Work-Graph als Gate modelliert** (15→20).
- **Regression**: In `tests/test_algo.py` P5-Testgruppen (bekannte Lösungen · Abgleich mit unabhängigem
  Oracle über Zufallsdaten hinaus · Fail-soft · Ganzzahligkeit · Überschreiten der Ausgabelänge bei der
  zweistufigen Probe · C-vs-Python-Parität bei fehlerhafter Eingabe · No-Mutation · Python exakt · C
  bitgenau). Gesamte Testsuite **4700 → 4736 passed / 0 failed** (+36) · meine neuen Dateien ruff clean ·
  mypy keine neuen Fehler (nur bestehende Baseline).

### Verstärkung nach der P5-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Für den selbst geschriebenen P5-Code wurde eine unabhängige Adversarial-Review als Workflow durchgeführt
(4 Linsen = Algorithmus-Korrektheit / C-Sicherheit-Codegen / Gate-Ehrlichkeit / Integration-Fokus, jedes
Finding vom Verifikations-Agenten **durch echte Kompilierung/Ausführung reproduziert**, 18 Agenten). **14
Rohbefunde → 9 CONFIRMED / 5 REFUTED**. Alle CONFIRMED habe ich selbst reproduziert (selbst mit ziglang
kompiliert und ausgeführt) und behoben. **Bemerkenswert ist der tiefgehende Fokus darauf, „ob das Gate den
selbst gebauten Guard widerlegen kann"**:
- **[MED] Der honest Bereich von pow_mod (base/exp ≤ 2^53) wurde vom Holdout nicht abgedeckt** → ein
  C-Mutant, der exp auf uint32 abschneidet, bestand das Gate (bei base/exp maximal 1e6/1e5 blieben die
  oberen ~33 Bit unabgedeckt). **Behebung** = Grenzfälle bei 2^53 zum Holdout hinzugefügt ([2,2^53,7]·
  [2^53,2^53,2^32-1] usw.) + Zufallsdaten über den gesamten Bereich [0,2^53] ausgeweitet. **Reproduktion
  bestätigt**: Nach der Fix schlägt der exp→uint32-Mutant mit `passed=False` fehl.
- **[LOW] gcd (2^53-Guard)/sieve (5.000.000-Cap) hatten dieselbe Art unabgedeckter Grenzen** → gcd-Grenze
  zum Holdout hinzugefügt (Mutation-Falsifizierung bestätigt), da der Python-Referenztest für sieve an der
  Cap-Grenze langsam ist (~7,7s), wurde ein **dedizierter Nur-C-Test** ergänzt, der n=5.000.000 akzeptiert
  (π=348513, per unabhängigem numpy-Sieb verifiziert) und n=5.000.001 ablehnt.
- **[MED] -ffast-math / -ffinite-math-only heben NaN-Guards auf** → wird das ausgelieferte C-Artefakt mit
  Fast-Math kompiliert, entfällt die NaN-Ablehnung von `x >= 0.0` und `(long long)NaN`-UB wird ausgeführt
  (**selbst reproduziert**: `gcd_seq([NaN,6])` liefert mit `-ffinite-math-only` 2.0, während das Gate mit
  Default `-ffp-contract=off` 0.0 liefert). **Behebung** = in `algo_codegen.emit_c` wird
  `#if __FAST_MATH__ || __FINITE_MATH_ONLY__ → #error` eingefügt (das Artefakt kompiliert nicht mehr
  stillschweigend falsch = **Build-Ablehnung, fail-closed**) + der C-Kommentar „UB unerreichbar" wurde
  honest auf die IEEE-Voraussetzung korrigiert + Test hinzugefügt, der den Fast-Math-Build ablehnt.
- **[MED] Kurze Eingabe-Guards in C (pow_mod `n<3` / sieve `n_in<1`) waren nicht falsifizierbar** → da alle
  Holdout-Fälle feste Länge hatten, bestanden auch nach Entfernen der Guard alle Tests trotz zugelassenem
  OOB-Heap-Read grün. **Behebung** = leere/kurze Arrays zu Holdout-/Paritätstests hinzugefügt, um den
  Grenzpfad zu durchlaufen. **Honest Offenlegung**: Ein reiner Black-Box-Wertvergleich kann das Entfernen
  von Safety-Guards **nicht deterministisch** erfassen (der OOB-Lesewert ist nichtdeterministisch).
  Eigentlich wäre ASan der richtige Ansatz, aber **ziglangs ASan lässt sich in dieser Windows-Umgebung nicht
  linken** (`__asan_shadow_memory_dynamic_address` undefiniert). Die Python-Seite der Guard ist deterministisch
  falsifizierbar, die C-Seite kann durch Grenzpfad-Ausübung + Sanitizer erfasst werden (aus Umgebungsgründen
  bleibt die Automatisierung vorerst zurückgestellt).
- **[MED] Der Sonderzweig `1 % mod` in pow_mod war nicht falsifizierbar** (der Fall exp==0 UND mod==1
  gleichzeitig kam nirgends vor) → [7,0,1]·[0,0,1] zum Holdout hinzugefügt + bekannte Lösung assertiert
  (**Reproduktion bestätigt**: der Mutant `1%mod→1` schlägt mit `passed=False` fehl).
- **[MED] P5-Oracle stürzte bei Eingaben außerhalb des Bereichs ab** (zlib.crc32 / pow() / int(nan) werfen
  Exceptions) → fügt man dem Holdout Fälle außerhalb des Bereichs hinzu, wirft difftest eine Exception =
  das Gate kann die Guard-Konvention **strukturell nicht abdecken** (nur 1 Unit-Test erfasst dies).
  **Behebung** = jedes P5-Oracle wurde **bereichsbewusst** gemacht (`_int_in` spiegelt den deklarierten
  Bereich der op → außerhalb des Bereichs wird der Fail-soft-Wert der op 0.0/[] zurückgegeben = kein
  Absturz). Damit kann das Gate selbst Guard-Abweichungen falsifizieren (**Reproduktion bestätigt**: Mutanten
  mit entfernter crc-Ganzzahligkeit bzw. verkleinerter gcd-Guard schlagen jeweils mit `passed=False` fehl).
- **[LOW] Die Operator-Hilfekarte in Studio zeigte für general-op fälschlich „Two knobs a,b"** (P1.5b hatte
  den Picker geschlossen, aber der Fallthrough von `op_help_html` bei Browser-Auswahl blieb ungeschützt und
  betraf alle 20 algo-op) → general-Zweig zu `op_help_html` hinzugefügt (zeigt Provenance + Packed-Input-
  Vertrag + CLI-Ausführung) + `desc` (op.doc) zu `_op_row`/`api.algo_rows` hinzugefügt + Regressionstest.
- **[LOW] Das YAML-Frontmatter-description (Auto-Trigger-Fläche) des image-processing-Skills warb nur für
  P1** (der Body war bereits mit 20 op aktualisiert) → der algo-Abschnitt der description wurde auf den
  vollen P2–P5-Umfang + Trigger-Wörter (primes/modular exponentiation/CRC-32/RLE/shortest path) erweitert.
- **5 REFUTED**: In allen Fällen war der bestehende Code korrekt und das Finding hatte reales Verhalten
  fehlinterpretiert (vom Verifikations-Agenten durch Ausführung widerlegt).
- Nach der Review: Für alle 5 P5-op difftest = Python exakt / C bitgenau / c_verified=true, gesamte
  Testsuite **4742 passed / 0 failed** (Review-Fixes +6) · meine neuen Dateien ruff clean · mypy keine
  neuen Fehler. Auch die 5 Work-Graph-Nodes wurden nach der Fix erneut vergated (done).

## P6-Abschlussbericht — Computergeometrie (2026-08-17, Opus5[1m]/ultracode, 12h autonom, `graph-loop-engineering`)
**3 geometrische Algorithmen dem algo-Tier hinzugefügt** (Erweiterung nach Abschluss der algo-c-Roadmap
P1→P5 = P6. Entspricht der „Geometrie = konvexe Hülle/Streckenschnitt"-Kategorie aus dem ursprünglichen TOC).
**Dient auch als Brücke zur Kontur-/Regionsverarbeitung im Bild-Tier**. 2-D-Punkte werden in eine Eingabe-seq
gepackt, mit **ganzzahligen Koordinaten** (jeweils [-100000, 100000]) werden alle Orientierungsentscheidungen/
Schnürsenkelsummen **exakt ganzzahlig** (keine Gleitkommadivision) = C bitgenau UND Python==unabhängiges
Oracle Toleranz 0.
- **op (3)**:
  - `polygon_area2` (KIND_REDUCE): mit der Schnürsenkelformel die **2× vorzeichenbehaftete Fläche** eines
    Polygons (Vorzeichen = Umlaufrichtung). Oracle = numpy-vektorisierte Schnürsenkelformel
    (`dot`+`roll` = separater Codepfad). **Honest Bereich**: Bei Koordinaten ≤1e5 · n ≤1e5 ist die Summe
    maximal 2e15 < 2^53 (real gemessen bei einer kastenförmig umlaufenden Spirale = exakt).
  - `point_in_polygon` (KIND_REDUCE): Innen-/Außenbestimmung über die Schnittzahl (Ray Casting). Die
    Schnittentscheidung erfolgt über ganzzahliges Kreuzprodukt (keine Division). Oracle = **Umlaufzahl-
    Algorithmus** (eine vom Schnittzahl-Verfahren unabhängige Methode, beide stimmen bei einfachen Polygonen
    exakt in Innen/Außen überein). Auch bei konkaven Polygonen korrekt (Kerbe=außen wird verifiziert).
    **Punkte auf dem Rand sind implementierungsabhängig**, dies wird offengelegt und aus dem Holdout
    ausgeschlossen (da Schnittzahl vs. Umlaufzahl am Rand divergieren können).
  - `convex_hull` (**KIND_MAP**): konvexe Hülle über Andrews Monotone-Chain. Ausgabe = **Eckenfolge im
    Gegenuhrzeigersinn ab dem lexikografisch kleinsten Punkt** (kollineare Punkte werden ausgeschlossen =
    Strict Hull, konsistent mit scipy). Oracle = Vergleich der **Eckpunktmenge** von
    `scipy.spatial.ConvexHull` (die Reihenfolge wird separat über C-vs-Python-Bit-Übereinstimmung
    abgesichert). Bei Entartung (weniger als 3 verschiedene Punkte / alle kollinear) liefern beide Seiten
    fail-soft []. **Vorab real gemessen: 0 Abweichungen zu scipy bei 2000 zufälligen Punktmengen**.
- **KIND_MAP**: Bei convex_hull ist die Ausgabe ≤ Eingabelänge (Eckpunkte ≤ n), dennoch wird die
  zweistufige Size-Probe (Obergrenze 2n) beibehalten.
- **Reale Messung des Honest Gate (alle 3 op passed=True · c_verified=true · ziglang cc)**: Python==
  unabhängiges Oracle Diff 0,0 / C==Python bitgenau Diff 0,0.
- **Work-Graph-op-Welle**: Auch die 3 Geometrie-op wurden als `algo_gate`-Node modelliert
  (`1 op = 1 Node`) → mit `run-once` unbeaufsichtigt done (alle 23 algo-op sind nun gated).
- **Regression**: In `tests/test_algo.py` Geometrie-Testgruppen (bekannte Lösungen · Abgleich mit mehreren
  unabhängigen Oracles [scipy/numpy/matplotlib/Umlaufzahl] · strukturelle Prüfung von Konvexität/CCW/
  Punktzugehörigkeit · Fail-soft · Entartung · No-Mutation · Python exakt · C bitgenau). Gesamte Testsuite
  **4742 → 4765 passed / 0 failed** (+23) · ruff clean · mypy keine neuen Fehler.

### P6-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
2 unabhängige Adversarial-Review-Workflows parallel (jedes Finding vom Verifikations-Agenten durch echte
Kompilierung/Ausführung/Stresstest reproduziert):
- **P6a (polygon_area2 / point_in_polygon, 4 Linsen · 102 Tool-Aufrufe) = 0 Findings**. Geometrie-
  Korrektheit / C-Sicherheit / Gate-Ehrlichkeit / Integration-Fokus allesamt null (Ganzzahl-Exaktheit,
  offengelegte Randfälle und vorab vermessener 2^53-Bereich). Auch ich habe im schlimmsten Fall (kastenförmig
  umlaufende Spirale n=1e5) real gemessen 2×Fläche=2,0e15 < 2^53, mit op==numpy==C übereinstimmend bestätigt.
- **P6b (convex_hull, 3 Linsen · 85 Tool-Aufrufe) = 1 Rohbefund → 0 CONFIRMED** (1 REFUTED). Der einzige
  Hinweis „ein Mutant, der die Dedup entfernt, besteht difftest" wurde durch Verifikation als **kein Mangel**
  verworfen: Die Dedup ist bereits durch das strikte `<=0`-Monotone-Chain-Pop + die nachgelagerte
  `hv<3`-Prüfung als **defensive Redundanz** garantiert (in beiden Backends liefert Entfernen dasselbe
  Ergebnis = bei 200.000 stark duplizierten Punktmengen 0 Divergenz). Der Verifikations-Agent bestätigte
  unabhängig: **die 2n-Size-Probe ist eine straffe, nicht übersteigbare Obergrenze** (bei parabolischer
  Eingabe out_len=2n) / **ASan+UBSan bleiben bei 1104 feindseligen Fällen sauber** (kein OOB-Schreiben in
  out[], kein Overflow beim Long-long-Kreuzprodukt) / C==Python bitgenau · Python==scipy stimmt vollständig
  in der Eckpunktmenge überein / auch die CCW-ab-lex-min-Reihenfolge wird per Test abgesichert / qsort-
  Instabilität ist durch den Vergleicher mit voller (x,y)-Ordnung + angrenzende Dedup unschädlich
  (=`sorted(set())`). → Nur ein erklärender Kommentar wurde ergänzt, dass die Dedup defensiv redundant ist
  (Verhalten unverändert).
- **Fazit**: In den 3 Geometrie-op von P6 wurde kein ausgelieferter Bug gefunden. Commit + Push erfolgten
  in dieser Session (`24bc8ad`).

## P7-Abschlussbericht — Streckenschnitt (2026-08-17, Opus5[1m]/ultracode, 12h autonom)
**Das Geometrie-Toolkit um 1 op erweitert**: `segments_intersect` (KIND_REDUCE) = ob sich zwei abgeschlossene
Strecken `[x1,y1,x2,y2,x3,y3,x4,y4]` schneiden (1.0/0.0). **Brücke zur Geraden-/Konturanalyse bei Bildern.**
Nach dem ganzzahligen Orientierungsverfahren aus CLRS 33.1 (Proper Crossing = ein Endpunkt überquert die
andere Strecke exakt + 4 kollineare On-Segment-Sonderfälle). Bei ganzzahligen Koordinaten [-100000,100000]
ist das Kreuzprodukt exakt (|cross| ≤ 8e10 passt in long long) = C bitgenau. **Oracle = die Segmentschnitt-
Berechnung von `sympy.geometry`** (symbolische Berechnung = eine völlig andere Methode als Orientierung).
Real gemessen: 8 feste Fälle korrekt + **0 Abweichungen zu sympy bei 2970 zufälligen ganzzahligen
Streckenpaaren** (einschließlich kollinearer Überlappung/T-Form/gemeinsamem Endpunkt/Beinahe-Treffer).
Entartete (punktförmige) Strecken werden aus dem Holdout ausgeschlossen, da sympy dafür kein Segment bilden
kann (die op funktioniert mit der allgemeinen Orientierungslogik, ist aber ungegatet = offengelegt). Difftest
passed (Python exakt / C bitgenau / c_verified), Work-Graph-Node unbeaufsichtigt done (alle 24 algo-op sind
gated).

### Verstärkung nach der P7-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Adversarial-Review mit 3 Linsen (vom Verifikations-Agenten durch echte Kompilierung/Ausführung reproduziert)
= **1 Rohbefund → 1 CONFIRMED** (MED · Gate-Ehrlichkeit). **Die op selbst ist korrekt** (stimmt vollständig
mit sympy überein), aber **der Difftest-Holdout treibt niemals die On-Segment-Sonderfälle d1/d3/d4 als
alleinigen Grund für eine 1.0-Entscheidung an** (ein Endpunkt liegt im Inneren der anderen Strecke, kein
gemeinsamer Endpunkt), sodass ein Mutant, der diesen Zweig entfernt, das Gate besteht (keine der 50
Holdout-Entscheidungen ändert sich). Durch Eigenreproduktion bestätigt (der d3+d4-Drop-Mutant liefert
`passed=True` · `[0,0,10,0,3,0,3,5]`→fälschlich 0.0). **Behebung** = für jeden on_seg-Zweig (d1/d2/d3/d4)
wurde ein fester Holdout-Fall als alleiniger Grund hinzugefügt (Endpunkt im Inneren der anderen Strecke ·
4 achsparallele + 2 diagonale Fälle) → **jetzt schlägt das Entfernen jedes einzelnen Zweigs difftest fehl**
(d1/d2/d3/d4 alle `passed=False`), selbst bestätigt. Auch den bekannten-Lösung-Tests wurden 4 Endpunkt-im-
Inneren-Fälle hinzugefügt. Gesamte Testsuite **4765 → 4772 passed / 0 failed** (+7) · ruff clean · mypy
keine neuen Fehler.

## P8-Abschlussbericht — Suchen/Auswahl (2026-08-17, Opus5[1m]/ultracode, 12h autonom)
**2 Such-/Auswahlalgorithmen dem algo-Tier hinzugefügt** (Wechsel von Geometrie zu einer anderen Domäne, um
die Tiers auszugleichen). Vergleichsbasiert für beliebige (NaN-freie) Doubles = das Ergebnis ist ein Index
oder ein vorhandenes Element, daher exakt (Toleranz 0) · C bitgenau.
- **op (2)**: `binary_search` (KIND_REDUCE): der **linkeste Index** (Lower Bound) des Targets in der
  sortierten Folge `[target, v0..v_{n-1}]`, sonst -1.0. Oracle = `bisect_left` + unabhängige
  Existenzprüfung. / `kth_smallest` (KIND_REDUCE): der k-t-kleinste Wert (0-indizierte Ordnungsstatistik)
  von `[k, v0..]` per **Quickselect** (Median-of-three-Pivot · Lomuto). Da der **k-t-kleinste Wert
  reihenfolgeunabhängig** ist, stimmen C und Python bitgenau überein, auch bei unterschiedlicher
  Pivot-Reihenfolge. Oracle = `sorted()[k]` (Timsort = anderer Algorithmus). Mit Median-of-three ist auch
  bei sortierter Eingabe O(n) (n=40001 < 2s).
- **Reale Messung des Honest Gate**: Beide op passed=True · Python exakt / C bitgenau / c_verified.
  **0 Abweichungen zum Oracle bei je 5000 Zufallsfällen** vorab real gemessen. Fail-soft = binary_search
  bei leer/nicht gefunden -1.0, kth_smallest bei k außerhalb des Bereichs/nicht-ganzzahlig/leer 0.0.
- **Work-Graph**: Auch die 2 op wurden über `algo_gate`-Nodes unbeaufsichtigt done (alle 26 algo-op sind
  gated). Regression = P8-Testgruppe in `tests/test_algo.py` (bekannte Lösungen · Abgleich mit bisect/
  sorted · O(n²)-Guard · Fail-soft · No-Mutation · Python exakt · C bitgenau). ruff clean · mypy keine
  neuen Fehler.

### Verstärkung nach der P8-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Adversarial-Review mit 2 Linsen (echte Kompilierung/Ausführungsverifikation) = **1 Rohbefund → 1 CONFIRMED**
(LOW · Korrektheit). **Die Korrektheit bleibt unverändert, aber es gibt ein Performance-Problem**:
Quickselect von kth_smallest verwendet eine einzelne Lomuto-Pivotisierung und ist daher **bei großen
Eingaben mit lauter gleichen/niedriger Kardinalität O(n²)** (Median-of-three schützt nicht vor Duplikaten;
bei n=40000 mit lauter gleichen Werten 7,44s, sortiert/umgekehrt sortiert ist schnell). Die Tests hatten
Holdout n≤30 und der Timing-Test deckte nur den sortierten Fall ab, daher unentdeckt. Der Schwester-
Algorithmus quicksort verwendet bereits eine 3-Wege-Partitionierung (Dutch Flag). **Behebung** =
kth_smallest wurde auf eine **3-Wege-Partitionierung (Dutch National Flag)** umgeschrieben
(Equal-Band faltet Duplikate zusammen → all-equal wird O(n) · nur Vergleiche + reihenfolgeunabhängig,
sodass **C==Python==sorted()[k]-Parität erhalten bleibt**). Selbst reproduziert bestätigt: **all-equal
n=40000 von 7,44s → 0,0019s** (O(n) erreicht) · Korrektheit bei 5000 Fällen 0 Abweichungen · Difftest
bitgenau. Der Timing-Test wurde um sortiert/umgekehrt/**all_equal/few_distinct** erweitert (schützt
tatsächlich vor Regression).

## P9-Abschlussbericht — Statistik/Aggregation (2026-08-17, Opus5[1m]/ultracode, 12h autonom)
**2 Statistik-op dem algo-Tier hinzugefügt**: `count_distinct` (Anzahl der distinkten Werte = Ganzzahl-
Count) / `mode_value` (Modus/häufigster Wert · bei Gleichstand gewinnt der kleinere). Vergleichsbasiert
(beliebiges NaN-freies Double) · das Ergebnis ist Count oder ein vorhandenes Element, daher exakt
(Toleranz 0). Beide op sortieren eine Kopie und laufen sie durch (das Ergebnis ist reihenfolgeunabhängig,
daher bitgenau, selbst wenn C-qsort und Python-sorted unterschiedlich sortieren). Oracle = `len(set())` /
`collections.Counter` (unabhängige Mechanismen).
**★Proaktive Härtung**: Bei mode_value führte eine Mischung von ±0.0 beim Modus 0 dazu, dass C-instabiles
qsort und Python-stabiles sort im Vorzeichen des Rückgabewerts divergieren konnten und Bit-Nichtübereinstimmung
entstehen konnte → **Kanonisierung von −0.0→+0.0 via `+ 0.0`** (andere Werte bleiben unverändert) macht
C==Python robust (dieselbe Systematik wie die Offenlegung zu vorzeichenbehafteter Null bei rle_encode).
Real gemessen: 0 Abweichungen zum Oracle bei je 5000 Zufallsfällen · difftest passed (Python exakt / C
bitgenau / c_verified). Alle 28 algo-op sind gated. ruff clean · mypy keine neuen Fehler.

### Verstärkung nach der P9-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Adversarial-Review mit 2 Linsen (echte Kompilierung/Ausführung/Mutation-Verifikation) = **1 Rohbefund →
1 CONFIRMED** (MED · Gate-Sicherheit). **Die Korrektheit bleibt unverändert, aber es gibt eine Gate-
Abdeckungslücke**: Ein Mutant, der die `+0.0`-Kanonisierung von mode_value entfernt, konnte vom Holdout
nicht falsifiziert werden (der einzige Fall mit vorzeichenbehafteter Null `[0.0,-0.0,0.0]` wird in beiden
Backends auf +0.0-zuletzt sortiert → auch ohne Kanonisierung Bit-Übereinstimmung). Der Kommentar behauptete
eine Absicherung durch den Bit-Check, der die Kanonisierung aber nie tatsächlich auslöste. **Behebung** =
`[0.0,-0.0]`·`[-0.0,0.0]` (bei denen -0.0 nicht am Ende der Reihe landet) wurden zum Holdout hinzugefügt
(beide Reihenfolgen sorgen dafür, dass mindestens eine unabhängig von der qsort-Tie-Reihenfolge divergiert).
Selbst reproduziert bestätigt: **der Mutant ohne Kanonisierung schlägt difftest fehl** · der aktuelle
(kanonisierte) Code besteht bei den zusätzlichen Fällen bitgenau. Gesamte Testsuite
**4787 → 4796 passed / 0 failed**.

## P10-Abschlussbericht — Zahlentheorie (Teil 2) (2026-08-17, Opus5[1m]/ultracode, 12h autonom)
**2 Zahlentheorie-op hinzugefügt** (aufbauend auf der Ganzzahl-Infrastruktur von P5 · gemeinsame Kategorie
numtheory). Ganzzahlen werden als float64 übertragen (exakt <2^53) · im honest Bereich passen alle modularen
Produkte in uint64/long long = C bitgenau UND Python==unabhängiges Oracle Toleranz 0.
- **op (2)**: `is_prime` (KIND_REDUCE): **deterministischer Miller-Rabin-Test** (Zeugen {2..37}). Honest
  Bereich 0≤n≤2^32−1 (a·a mod n passt in uint64 und die Zeugenmenge ist deterministisch = Primalitätsbeweis
  bis n<3,3e24). Oracle = `sympy.isprime`. ★Korrekt erkannte Carmichael-Zahlen (561/1105/1729/2465…) als
  zusammengesetzt. / `modular_inverse` (KIND_REDUCE): a^−1 mod m über den **erweiterten euklidischen
  Algorithmus** (bei gcd≠1 −1.0). Bereich a≤2^53 · m≤2^53 (die Bezout-Koeffizienten erfüllen die Invariante
  |q·s|=|old_s−new_s|≤2m, passen also in long long) · m=1→0. Der abgeschnittene C-Mod wird auf [0,m−1]
  normalisiert (+m) und stimmt so mit Pythons Floor-Mod überein. Oracle = eingebautes `pow(a,−1,m)`.
- **Reale Messung des Honest Gate**: Beide op passed=True · Python exakt / C bitgenau / c_verified.
  **is_prime wurde mit sympy bei 8000 Zufalls- + 2000 erschöpfenden Fällen (inkl. Carmichael-Zahl 561) mit
  0 Abweichungen verglichen / modular_inverse mit pow bei 8000 Fällen 0 Abweichungen** vorab real gemessen.
  Alle 30 algo-op sind gated. ruff clean · mypy keine neuen Fehler.

### Verstärkung nach der P10-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Adversarial-Review mit 2 Linsen (echte Kompilierung/Ausführung/Mutation-Verifikation) = **1 Rohbefund →
1 CONFIRMED** (MED · C-Sicherheit-Gate). **Die op selbst ist korrekt und overflow-sicher** (mit 353
feindseligen Fällen verifiziert), aber **der Holdout von modular_inverse deckt den deklarierten Bereich bis
2^53 nicht ab** (in-domain m erreichte nur ~1e9), sodass ein C-Mutant mit Breiten-Verengung
`long long→int` (der den 2^53-Bereich zerstört) das Gate bitgenau besteht. Während die Schwestern-op
pow_mod (base=exp=2^53 gepinnt)/gcd_seq (2^53-Guard-Grenze)/is_prime (nahe 2^32) dieselbe Mutationsart
erfassen, tat modular_inverse dies nicht. **Behebung** = Grenzfälle bei 2^53 zum Holdout hinzugefügt
(`[2, 2^53−1]` teilerfremd→Inverse · großes teilerfremdes Paar nahe 2^53 · `[2^52, 2^53]` beide gerade→−1),
sodass die Bezout-Operation |q·s|~2m~2^54 durchläuft. Selbst reproduziert bestätigt: **der
`long long→int`-Mutant schlägt difftest fehl**, die Baseline besteht bitgenau. Das Oracle (pow) war bereits
geeignet, es musste nur der Holdout ergänzt werden. Gesamte Testsuite grün.

## P11-Abschlussbericht — Bitoperationen (2026-08-17, Opus5[1m]/ultracode, 12h autonom)
**2 Bitoperations-op hinzugefügt**: `xor_reduce` (bitweises XOR aller Elemente) / `popcount_total`
(Gesamtzahl gesetzter Bits aller Elemente = Kernighan-Verfahren). Nicht-negative Ganzzahlen werden als
float64 übertragen, im Bereich [0, 2^53−1] passen alle Werte in 53 Bit (auch das XOR-Ergebnis ist < 2^53,
also exakt · popcount ist eine kleine Ganzzahl) = C bitgenau UND Python==unabhängiges Oracle
(`functools.reduce(operator.xor)` / eingebautes `int.bit_count()` = ein anderer Mechanismus als Kernighan)
Toleranz 0. Beide op passed=True · Python exakt / C bitgenau / c_verified. 0 Abweichungen zum Oracle bei je
3000 Zufallsfällen vorab real gemessen. Fail-soft = bei negativ/nicht-ganzzahlig/≥2^53 → 0.0. Alle 32 algo-op
sind gated. ruff clean (FURB161: `bin().count('1')`→`.bit_count()` umgestellt) · mypy keine neuen Fehler.

### Ergebnis der P11-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Adversarial-Review-Workflow mit 2 Linsen (Korrektheit + Gate-Sicherheit, `wf_7d130631-c0f`) = **0 Findings
(keine Mängel)**. Reviewer 1 lieferte `{findings:[]}`, Reviewer 2 wurde während des Mutation-Testings des
Gates (Implementierung absichtlich beschädigen und prüfen, ob das Gate es erkennt) durch Fenster-Kompression
unterbrochen (kein Ergebnis produziert). **Der Disziplin folgend wurde der abgebrochene Background-Prozess
nicht wiederbelebt, stattdessen habe ich denselben Mutation-Test selbst zur Erstverifikation durchgeführt**:
7 repräsentative Mutanten von xor_reduce/popcount_total (leere Initialisierung acc=1 / fälschliches OR /
Off-by-one an der 2^53-Grenze / entfernte Negativ-Guard / Kernighan→Shift [popcount≠Bitlänge] / +2-Fehler /
Zulassung von 2^53) gegen den Holdout ausgeführt → **alle 7 Mutanten wurden vom unabhängigen Oracle erfasst**
(oracle_err > 0). **Fazit = das P11-Gate ist falsifizierend, kein bestätigter Mangel** (`fed093a` ist
korrekt, kein Folge-Commit nötig).

## P12-Abschlussbericht — Erweiterter Euklidischer Algorithmus (2026-08-17, Opus5[1m]/ultracode, 12h autonom)
**1 Zahlentheorie-op hinzugefügt** (aufbauend auf der Ganzzahl-Infrastruktur von P5 + der Bezout-Invariante
von P10 · gemeinsame Kategorie numtheory=P5+P10+P12).
`extended_gcd` (**KIND_MAP**): Eingabe `[a, b]` (nicht-negative Ganzzahlen ≤ 2^53) → Ausgabe `[g, x, y]`
(**exakte 3 Werte**, `a·x + b·y = g = gcd(a,b)`), außerhalb des Bereichs fail-soft `[]`. Ein iterativer
Two-Variable-Sweep berechnet die Koeffizienten. **Die Koeffizienten sind exakt** (die Invariante
`|q·s| = |old_s − new_s| ≤ 2·max(a,b) ≤ 2^54` passt in long long), daher C == Python bitgenau. Der Bereich
ist **[0, 2^53] inklusive** (2^53 ist exakt · auch die Koeffizienten |x|,|y| ≲ 2^52 sind in float64 exakt).
- **★Zum Punkt der Oracle-Unabhängigkeit (Lehre aus P10)**: Bezout-Paare (x,y) sind nicht eindeutig, daher
  kann **die Prüfung der Identität „a·x+b·y==g"** Vorzeichen-/Normalform-Abweichungen **nicht** durch das
  Gate falsifizieren. → Das Oracle berechnet (g,x,y) über eine **unabhängige rekursive Variante des
  erweiterten euklidischen Algorithmus `_ext_gcd_rec` (separater Codepfad)** und vergleicht die Elemente.
  Die iterative und die rekursive Variante liefern dieselben kanonischen Koeffizienten (rekursiv entfaltet
  ergibt sich die iterative Form = mathematisch identisch, bestätigt für alle Randfälle `[0,b]`/`[a,0]`/
  `[0,0]`/Gleichheit).
- **Reale Messung des Honest Gate (passed=True · c_verified=true · ziglang cc · 70 Fälle)**: Python==
  unabhängiges rekursives Oracle **Diff 0,0 (exakt)** / generiertes **C==Python bitgenau Diff 0,0**. Vorab
  real gemessen = **bei 200.000 Zufallsfällen (inkl. Grenzen des 2^53-Bereichs) 0 Abweichungen zwischen
  iterativer op und rekursivem Oracle sowie 0 Fehlschläge bei der Identität `a·x+b·y==g==math.gcd(a,b)`**
  (unabhängig mit Bignum nachgerechnet). Fail-soft = bei kurz/nicht-ganzzahlig/negativ/NaN/>2^53 → `[]`.
- **★Gate-Mutation-Test (Selbstverifikation)**: 5 terminierende Mutanten (x,y vertauschen / x negieren /
  Aktualisierung von old_s auslassen / Guard aufweichen [>2^53 zulassen] / falsche Länge) werden **alle
  erfasst** (Element-Nichtübereinstimmung oder strukturelle Nichtübereinstimmung inf). Bei einem falschen
  Quotienten q+1 gerät die op selbst in eine Endlosschleife (das Difftest-Harness-Timeout erkennt dies als
  Fehlschlag) = jeder terminierende Fehlerfall wird falsifiziert.
- **Holdout (deckt Randfälle und alle Zweige einzeln ab)**: bekannte Werte `[35,15]→(5,1,-2)` usw. +
  teilerfremd/nicht teilerfremd + Gleichheit `[7,7]` + eine Seite 0 (`[0,5]`/`[5,0]`/`[0,0]`) + a=1 +
  **Grenzen des 2^53-Bereichs** (`[2, 2^53−1]` teilerfremd · großes teilerfremdes Paar nahe 2^53 ·
  `[2^52, 2^53]` gcd 2^52 · `[2^53, 6]` inklusive Obergrenze) + Fail-soft außerhalb des Bereichs (kurz/
  `>2^53`=`[2^53+2,3]`/nicht-ganzzahlig/negativ/NaN) + 48 Zufallsfälle.
- **Work-Graph-op-Welle**: extended_gcd wurde als `algo_difftest --op`-Gate-Node modelliert
  (`1 op = 1 Node` · priority 0 · tool capability · produces=Gate-JSON) →
  `run-once --available tool:command` **unbeaufsichtigt done** (passed:true · c_verified · Marker für
  Bit-Übereinstimmung erzeugt). = **alle 33 algo-op sind nun im Work-Graph als Gate modelliert** (32→33).
- **Regression**: In `tests/test_algo.py` P12-Testgruppen (bekannte Werte · Bezout-Identität über 5000
  Zufallsfälle · Übereinstimmung mit unabhängigem rekursivem Oracle über 5000 Zufallsfälle · Fail-soft ·
  Kategoriegruppierung [numtheory=P5+P10+P12] · difftest Python exakt · C bitgenau). Gesamte Testsuite
  **4827 passed / 0 failed** (test_algo.py allein 260) · alle meine Änderungen ruff clean · mypy keine neuen
  Fehler (origin/master=15, also dieselbe Anzahl = 0 netto-neue).

### Verstärkung nach der P12-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Adversarial-Review-Workflow mit 3 Linsen (Korrektheit / C-Sicherheit+Gate-Ehrlichkeit / Integration, jedes
Finding vom Verifikations-Agenten **durch echte Kompilierung/Ausführung als Mutation reproduziert**,
5 Agenten · 125 Tool-Aufrufe) = **2 Rohbefunde (dieselbe Grundursache) → 1 CONFIRMED**
(MED · Gate-kann-nicht-falsifizieren). **Die op selbst ist korrekt** (bei 200k + allen Randfällen verifiziert ·
divergiert nicht vom rekursiven Oracle · kein Long-long-Overflow im gültigen Bereich), aber **alle
Außer-Bereich-Fälle im Difftest-Holdout betreffen nur den Operanden `a`** (`[2^53+2,3]`/`[2.5,7]`/`[-1,7]`),
während der einzige Fall mit fehlerhaftem `b`, `[7,NaN]`, durch den Kurzschluss bei `bd>=0.0` keinen der 3
b-Guard-Zweige allein antreibt → **eine einseitige Regression der `b`-Guard (a/b sind kopiert-symmetrisch,
also plausibel) besteht beide Gate-Hälften** (dieselbe Gate-Abdeckungslehre wie bei P5/P7/P9/P10). **Selbst
reproduziert bestätigt**: Entfernt man `bd>=0` / `bd<=2^53` / `bd==int` aus _PY und _C, ergibt sich jeweils
**`passed=True` (verpasst)**, während das symmetrische Entfernen auf der `a`-Seite jeweils `passed=False`
liefert (erfasst, da die a-Randfälle im Holdout enthalten sind). **Behebung** = Fälle `[valid_a,
finite_bad_b]` (`[3, 2^53+2]` · `[7,-1]` · `[7,2.5]`) wurden zum Holdout und zu den Fail-soft-Tests
hinzugefügt → bei erneuter Messung werden **alle 3 b-seitigen Entfernungen erfasst (passed=False,
pydiff=inf)** · die Baseline besteht bei 70 Fällen bitgenau. ★**Die honest Korrektur des Verifikations-
Agenten wurde übernommen** (eine überzogene Behauptung des Findings wurde verworfen): Die Aussage „das
Entfernen von `bd<=2^53` verursacht bei b=2^62 einen Long-long-Overflow-UB in C" ist **ungenau** — bei
b=2^62 stimmen C (long long) und Python (Bignum) bitgenau überein (kein Overflow). Der eigentliche Fehler ist
ein **Präzisionsverlust in der Ausgabe** (die Bezout-Koeffizienten können bei > 2^53 nicht mehr exakt als
float64 dargestellt werden, wodurch `a·x+b·y==g` verletzt wird), und genau diese Präzision wird durch die
Obergrenze `b<=2^53` geschützt. Der Mechanismus war falsch beschrieben, aber Mangel und Abhilfe waren korrekt
= übernommen.

## P13-Abschlussbericht — Nächstes Punktpaar (Divide-and-Conquer) (2026-08-17, Opus5[1m]/ultracode, 12h autonom)
**Die Computergeometrie um 1 op erweitert (zweite Geometrie-Runde nach P6/P7)**: `closest_pair`
(KIND_REDUCE) = die **minimale quadrierte Distanz** in einer Menge 2-D-Ganzzahlpunkte wird per
**Divide-and-Conquer** (CLRS 33.4) bestimmt. Eingabe `[x0,y0,x1,y1,...]` (2n Werte · ganzzahlige Koordinaten
[-1e5,1e5]) → Ausgabe = minimale quadrierte euklidische Distanz (ganzzahlig exakt). **Nur die quadrierte
Distanz (kein Sqrt)**, daher bleibt alles in long long/ganzzahligem float64, C==Python bitgenau. Die maximale
quadrierte Distanz = (2e5)²×2 = 8e10 < 2^53 = exakt. Fail-soft = bei Punkten <2 (n<4) / ungerader Länge /
nicht-ganzzahligen Koordinaten / außerhalb von [-1e5,1e5] → -1.0.
- **Algorithmus**: Sortierung nach x (bei Gleichstand nach y) → rekursiv linke/rechte Hälfte → d=min(dl,dr)
  → Punkte mit (x−midx)²<d um die Mittellinie bilden den Streifen → Streifen wird nach y sortiert → für
  jeden Punkt Vorwärtsdurchlauf, solange `(yj−yi)²<d` gilt (Obergrenze von 7 Nachbarn). Basisfall (m≤3) per
  Brute Force. Duplikate (Distanz 0) liegen nach der Sortierung mit gleichem x benachbart und werden auch
  über die Teilungslinie hinweg vom Streifen erfasst. In C werden `CpPt`-Struct + `cp_rec`-Rekursion +
  `cp_cmp_x/cp_cmp_y` (qsort) im op.c_code definiert (der Codegen fügt c_code wörtlich ein, daher sind
  statische Hilfsfunktionen möglich). Der Streifenpuffer wird über die Rekursion hinweg als ein einziger
  Puffer geteilt (das Kind ist stets vor dem Elternteil fertig = Post-order, daher kein Aliasing). Die
  Rekursionstiefe beträgt ~log2(n) (bei n=1e5 also 17) = Stack-sicher.
- **Reale Messung des Honest Gate (passed=True · c_verified=true · ziglang cc · 58 Fälle)**: Python==
  **unabhängiges Brute-Force-O(n²)-Oracle** (separater Codepfad ohne Sortierung/Streifen) **Diff 0,0
  (exakt)** / generiertes **C==Python bitgenau Diff 0,0**. Vorab real gemessen = **30.000 Zufallsfälle
  (Cluster R=3/8/30 zur Steuerung der Streifentiefe) + 16.000 feindselige Layouts (dichtes Raster/
  senkrechte-waagerechte Linien [alle Punkte im Streifen]/Mikrocluster/Randkoordinaten) mit 0 Abweichungen
  zum Brute-Force-Verfahren**.
- **★Gate-Mutation-Test (Selbstverifikation)**: 6 Mutanten (Streifen-Scan ausgelassen / sq ignoriert y /
  Koordinaten-Obergrenze entfernt / Koordinaten-Untergrenze entfernt / Ganzzahligkeit entfernt / leerer
  Streifen) werden **alle erfasst** (passed=False). Ein Fall mit minimalem Cross-Strip-Paar
  ([-5,-5,-1,0,1,0,5,5]→4) treibt die Streifen-Logik, und Grenzfälle in beiden Koordinaten-Slots treiben die
  Guards jeweils allein an (spiegelt die Lehre der einseitigen Guard aus P12).
- **Holdout**: bekannte Werte (einzelnes Paar 25 · 3 Punkte · Duplikat-Distanz0 · senkrechte Reihe ·
  **minimaler Cross-Strip-Fall**) + extreme In-Domain-Koordinaten (obere Grenze 8e10) + Fälle außerhalb des
  Bereichs jeweils als alleiniger Grund in **beiden Koordinaten-Slots** (ungerade Länge/1 Punkt/nicht-
  ganzzahliges x·y/±1e5-Überschreitung x·y/NaN x·y) + 40 Zufallsfälle (Cluster).
- **Work-Graph-op-Welle**: closest_pair wurde als `algo_difftest --op`-Gate-Node modelliert
  (`1 op = 1 Node`) → mit `run-once` unbeaufsichtigt done. = **alle 34 algo-op sind nun im Work-Graph als
  Gate modelliert** (33→34).
- **Regression**: In `tests/test_algo.py` P13-Testgruppen (bekannte Werte · Übereinstimmung mit
  Brute-Force über 4000 Zufallsfälle · Fail-soft [beide Koordinaten-Slots] · Kategoriegruppierung
  [geometry=P6+P7+P13] · difftest Python exakt · C bitgenau). Gesamte Testsuite
  **4834 passed / 0 failed** (+7) · ruff clean · mypy keine neuen Fehler (origin/master=15, also dieselbe
  Anzahl). Ergebnis der Adversarial-Review siehe unten (1 CONFIRMED, selbst reproduziert und behoben).

### Verstärkung nach der P13-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Adversarial-Review-Workflow mit 3 Linsen (Korrektheit / C-Sicherheit+Gate-Ehrlichkeit / Integration, jedes
Finding vom Verifikations-Agenten **durch echte Kompilierung/Ausführung als Mutation reproduziert**) =
**alle 3 Linsen konvergieren auf dieselbe Grundursache → 1 CONFIRMED** (Schweregrad: meine anfängliche
Einschätzung MED / **der Verifikations-Agent bewertete HIGH** [Gate-Ehrlichkeitsversagen, das Gate hätte
einen fehlerhaften op durchgewinkt, was schwerwiegender gewertet wurde. Honest werden beide Einschätzungen
dokumentiert, der Fix ist identisch]. **Die op selbst ist korrekt** (bei 30k+16k feindseligen Fällen 0
Abweichungen zum Brute-Force), aber **der Difftest-Holdout treibt den y-Scan im Streifen nie über den
unmittelbaren Nachbarn (j==i+1) hinaus** → wird der Vorwärtsdurchlauf im Streifen auf **nur j==i+1**
verkürzt, kann das Gate dies nicht falsifizieren (das 7-Nachbarn-Theorem besagt „höchstens 7", nicht „1",
daher kann das nächste Paar in y-Reihenfolge nicht-benachbart sein). **Selbst reproduziert bestätigt**: Der
Mutant mit `range(i+1, min(i+2, sc))` wurde auf _PY und _C angewendet → `passed=True` (verpasst). Ein
minimaler falsifizierender Fall wurde im Ganzzahlgitter gesucht und gefunden (z. B.
`[0,-6,-2,-2,4,-3,-5,3]` = das nächste Paar liegt in y-Reihenfolge 2 Positionen auseinander → korrekt/
Brute-Force 20, aber nur-j==i+1 liefert 25). **Behebung** = 3 Fälle, bei denen das nächste Paar im Streifen
y-sortiert nicht benachbart ist (`[0,-6,-2,-2,4,-3,-5,3]`→20 / `[-4,5,-1,-3,0,-1,3,-3]`→5 /
`[-1,-6,-1,0,-5,-4,1,-4,4,4]`→8), wurden zum Holdout und zu den bekannten-Werte-Tests hinzugefügt → bei
erneuter Messung wird **der nur-j==i+1-Mutant erfasst (passed=False, pydiff=12)** · die Baseline besteht
bei 61 Fällen bitgenau · die anderen 5 Mutanten zeigen keine Regression. Zusätzlich zu den bestehenden 6
Mutanten (Streifen ausgelassen/sq ignoriert y/Koordinaten-Ober-/Untergrenze/Ganzzahligkeit/leerer Streifen)
ist nun auch die Streifen-Scan-Tiefe falsifizierbar (die Gate-Abdeckungslehre aus P12 wurde auf den
Geometrie-Streifen-Scan übertragen).

## P14-Abschlussbericht — Optimale Präfixcode-Kosten nach Huffman (2026-08-17, Opus5[1m]/ultracode, 12h autonom)
**Die Datenkompression um 1 op erweitert (zweite Kompressionsrunde nach P5 rle_encode)**: `huffman_cost`
(KIND_REDUCE) = für Symbolhäufigkeiten `[f0,f1,...]` (nicht-negative Ganzzahlen ≤2^40) die **minimalen
Gesamtkosten eines optimalen Präfixcodes (Huffman)** = die Summe der kombinierten Gewichte aller inneren
Knoten (= Σ freq×Codelänge). **★Kernpunkt = die optimalen Kosten sind gegenüber Gleichständen invariant**
(die Codelänge pro Symbol kann sich durch Tie-Breaking ändern, aber die Gesamtkosten sind bei einem
Häufigkeits-Multiset eindeutig), daher ist es unerheblich, in welcher Reihenfolge C und Python
gleichgewichtige Elemente ziehen = **die Gesamtsumme ist identisch, Bit-Übereinstimmung ergibt sich sauber**.
Ganzzahlen werden als long long übertragen (durch Bereichs-Guard auf < 2^54 begrenzt = kein Overflow).
- **Algorithmus = Zwei-Warteschlangen-Verfahren** (Huffman O(n log n)): Häufigkeiten aufsteigend sortiert in
  q1 [Blätter], q2 [Zusammenführungsknoten] wird monoton wachsend erzeugt → aus den jeweiligen Köpfen von
  q1/q2 werden die 2 kleinsten entnommen, deren Summe s zum Total addiert und ans Ende von q2 gehängt (n−1
  Wiederholungen). In C dieselbe Implementierung mit 2 Arrays + 2 Kopf-Indizes (qsort-Vergleicher hc_cmp).
- **Bereich und Fail-soft**: jede Häufigkeit 0≤f≤2^40 (ganzzahlig) · sonst -1.0. **Übersteigt die
  Zusammenführungssumme 2^53, wird -1.0 zurückgegeben** (float64 kann dies nicht mehr exakt darstellen) =
  **eine für die Exaktheit kritische, falsifizierbare Verzweigung**. Die Gesamthäufigkeit total_freq wird
  während der Guard-Prüfung akkumuliert und liefert bei >2^53 frühzeitig -1.0 = Long-long-Sicherheit (jedes
  s≤total_freq≤2^53 · total≤2^54<2^63). Bei n=0/1 → 0.0. ★**Honest Offenlegung**: Der vorgelagerte
  total_freq-Guard ist eine Sicherheitsgrenze gegen extreme n (>~4M Symbole), bei denen die Häufigkeitssumme
  selbst long long überlaufen ließe — bei realistischen n liefert der Merge-Bail dasselbe -1.0, daher lässt
  sich dies per Wertvergleich kaum allein falsifizieren (dieselbe Struktur wie die OOB-Guard-Offenlegung
  bei P5). Der Merge-Total-Bail, der die Exaktheit schützt, wird durch den Holdout-Fall `[2^40]×1024`
  (Summe 2^50<2^53, passiert die vorgelagerte Prüfung, Kosten~2^53,3 lösen den Merge-Bail aus) allein
  angetrieben = falsifizierbar.
- **Reale Messung des Honest Gate (passed=True · c_verified=true · ziglang cc)**: Python==**unabhängige
  Heapq-(Min-Heap)-Variante der Huffman-Kosten** (separater Codepfad zu den zwei Warteschlangen) **Diff 0,0
  (exakt)** / generiertes **C==Python bitgenau Diff 0,0**. Vorab real gemessen = **50k Zufallsfälle (lauter
  gleiche Häufigkeiten/Häufigkeit 0/Grenzwert 2^40 zur Auslösung von Gleichständen) mit 0 Abweichungen zu
  heapq** · **4k Mikrofälle mit 0 Abweichungen zum Brute-Force-Optimum über alle Zusammenführungs-
  reihenfolgen** (= Greedy erreicht das Optimum) · **20k mit umgekehrter Tie-Reihenfolge im Heap, 0
  Abweichungen** (= belegt die Tie-Invarianz).
- **★Gate-Mutation-Test (Selbstverifikation)**: 6 Wertverzweigungs-Mutanten (Häufigkeitsobergrenze entfernt /
  Negativ-Guard entfernt / Ganzzahligkeit entfernt / **Merge-Total-Bail deaktiviert** [`[2^40]×1024`
  falsifiziert dies] / Merge lässt x2 aus / n==1 liefert 1.0) werden **alle erfasst** (passed=False).
- **Work-Graph-op-Welle**: huffman_cost wurde als `algo_difftest --op`-Gate-Node modelliert
  (`1 op = 1 Node`) → mit `run-once` unbeaufsichtigt done. = **alle 35 algo-op sind nun im Work-Graph als
  Gate modelliert** (34→35).
- **Regression**: In `tests/test_algo.py` P14-Testgruppen (bekannte Werte · Übereinstimmung mit heapq über
  5000 Zufallsfälle · Fail-soft/Overflow · Kategoriegruppierung [compress=P5+P14] · difftest Python exakt ·
  C bitgenau). Gesamte Testsuite **4841 passed / 0 failed** (+7) · ruff clean · mypy keine neuen Fehler
  (origin/master=15, also dieselbe Anzahl).

### Verstärkung nach der P14-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Adversarial-Review-Workflow mit 3 Linsen (Korrektheit / C-Sicherheit+Gate-Ehrlichkeit / Integration, jedes
Finding vom Verifikations-Agenten **durch echte Mutation reproduziert**) = **3 CONFIRMED** (alle betreffen
die Gate-Abdeckung an der Overflow-Bail-Grenze · die op selbst ist korrekt, Tie-Invarianz bereits mit
50k+4k+20k abgesichert). **0 Findings zur Korrektheit** (die Behauptung der Tie-Invarianz und die Optimalität
des Zwei-Warteschlangen-Verfahrens sind robust). Alle CONFIRMED betreffen die vollständige Abdeckung der
„Fail-soft-Grenze bei merge-total>2^53":
- **[MED] Der Schwellenwert ist über ~6 Größenordnungen nicht fixiert** (ein Mutant, der die Merge-Total-
  Schwelle 2^53 auf z. B. 2^50 verengt, besteht das Gate) = **Selbstreproduktion bestätigt** (2^53→2^50-
  Mutant liefert passed=True). **Behebung** = `[2^40]×837` (Kosten 8997303650091008 ≈ 2^52,998 · GÜLTIG,
  exakt zurückgegeben) + `[2^40]×838` (Kosten > 2^53 → -1.0) wurden zum Holdout hinzugefügt, um den
  Schwellenwert **eng auf 2^53 ±~1e13 zu fixieren** → bei erneuter Messung werden alle Schwellenwert-
  Verengungen (2^53→2^50 · →8e15) **erfasst**. Auch 837/838 wurden in die bekannten-Werte-Tests aufgenommen.
- **[MED] Der exakte Fall cost == 2^53 fehlte im Holdout, sodass ein Off-by-one `>`→`>=` unentdeckt blieb →
  per WITNESS behoben**: Zunächst wurde angenommen, „bei freq ≤ 2^40 kann cost nie exakt 2^53 werden" und
  fast als Offenlegung dokumentiert, doch **der Verifikations-Agent entdeckte eine Konstruktion** =
  `2^16 Symbole × freq 2^33` (= 2^33 ≤ 2^40) ergibt bei jeder Tiefe 16 **cost = 2^16 · 2^33 · 16 = exakt
  2^53**. 2^53 ist darstellbar, also GÜLTIG (liefert 2^53), und ein `>=`-Mutant setzt dies fälschlich auf
  -1.0. **Selbst verifiziert** (mit Bignum bestätigt, dass cost==2^53 · die op 2^53 zurückgibt ·
  total_freq=2^49<2^53 die vorgelagerte Prüfung passiert), dieser Witness-Fall wurde in Holdout und
  bekannte-Werte-Tests **übernommen** → das `>`→`>=`-Off-by-one ist nun falsifizierbar (dieser eine
  Grenzwert wird gezielt gepinnt). **Ein gutes Beispiel dafür, dass die Adversarial-Review nicht nur die
  Lücke, sondern auch die Fix selbst entdeckte** (widerlegte meine anfängliche Einschätzung „unerreichbar").
- **[LOW] Der vorgelagerte `total_freq > 2^53`-Guard-Zweig ist unangetrieben/nicht falsifizierbar** =
  **honest Offenlegung**: Dies ist eine Sicherheitsgrenze gegen extreme n (>~4M Symbole), bei denen die
  Häufigkeitssumme selbst long long überlaufen ließe. Bei realistischen n liefert der Merge-Bail dasselbe
  -1.0 (auch ohne diesen Guard käme es zu keinem Long-long-Overflow, das Ergebnis bliebe unverändert), daher
  lässt sich dies per Wertvergleich nicht allein falsifizieren (dieselbe Struktur wie die OOB-Guard-
  Offenlegung bei P5). Ein Holdout für extreme n wäre unrealistisch langsam und wurde nicht hinzugefügt.
- Der Verifikations-Agent bewertete alle 3 Punkte als CONFIRMED, weil das Gate bestimmte Fehlimplementierungen
  nicht falsifizieren kann. **Die Korrektheit der op bleibt unverändert** (kein fehlerhafter op wurde
  ausgeliefert), die Gate-Abdeckung wurde bei #2 verstärkt, #1/#3 wurden honest offengelegt.

## P15-Abschlussbericht — Länge der längsten aufsteigenden Teilfolge (2026-08-17, Opus5[1m]/ultracode, 12h autonom)
**Suchen/Auswahl um 1 op erweitert (zweite Suchrunde nach P8 binary_search/kth_smallest · neue
DP-/Patience-Sorting-Algorithmenfamilie)**: `lis_length` (KIND_REDUCE) = die **Länge der längsten strikt
aufsteigenden Teilfolge (LIS)** einer beliebigen NaN-freien Double-Folge wird per **Patience Sorting**
bestimmt. Nur Vergleiche (keine Arithmetik auf den Werten), daher ist die Länge für ein gegebenes Array
eindeutig = **C==Python bitgenau**. tails[k] hält das minimale Ende einer aufsteigenden Teilfolge der Länge
k+1, für jedes Element wird an Position `tails[mid] < x` (bisect_left · **strikt**) ersetzt oder das Ende
erweitert (O(n log n)). Leer→0.0, gemischt mit NaN→-1.0 Fail-soft (Erkennung über `x != x`).
- **Reale Messung des Honest Gate (passed=True · c_verified=true · ziglang cc)**: Python==**unabhängiges
  O(n²)-DP-Oracle** (`dp[i]=1+max(dp[j]|j<i,a[j]<a[i])` = separater Codepfad zu Patience Sorting) **Diff 0,0
  (exakt)** / generiertes **C==Python bitgenau Diff 0,0**. Vorab real gemessen = **40k Zufallsfälle
  (Ganzzahlen+Float · kleiner Wertebereich zur massiven Erzeugung von Gleichständen = treibt den strikten
  Vergleich an) mit 0 Abweichungen zur DP**.
- **★Gate-Mutation-Test (Selbstverifikation)**: 3 Mutanten (strikt `<`→`<=` [nicht-fallend = anderes
  Ergebnis] / NaN-Guard entfernt / Richtung der Binärsuche umgekehrt) werden **alle erfasst** (passed=False).
  Der Fall lauter gleicher Werte `[2,2,2,2]`→1 sowie alternierende Duplikate treiben den strikten Vergleich
  allein an, der NaN-Holdout treibt die Guard an.
- **Holdout**: bekannte Werte (`[3,1,2,4]`→3 · `[5,4,3,2,1]`→1 · vollständig aufsteigend→n · leer→0 ·
  einzelnes Element→1) + **lauter gleiche Werte→1 (strikt, keine Verlängerung bei Duplikaten)** +
  alternierende Duplikate + -0.0/+0.0-Gleichheit + ±inf + Float-Gleichstände + NaN an **Anfang/Mitte/Ende**
  als Fail-soft + Zufallsfälle (viele Ganzzahl-Gleichstände + Float).
- **C-Sicherheit**: tails-Puffer malloc(n) · Schreibzugriff tails[lo] mit lo≤len<n = kein OOB · n=0 malloc(1)
  + Schleife läuft nicht = 0.0 · Malloc-Fehlschlag liefert -1.0 · NaN-Guard steht vor allen Vergleichen
  (NaN-sicher).
- **Work-Graph-op-Welle**: lis_length wurde als `algo_difftest --op`-Gate-Node modelliert
  (`1 op = 1 Node`) → mit `run-once` unbeaufsichtigt done. = **alle 36 algo-op sind nun im Work-Graph als
  Gate modelliert** (35→36).
- **Regression**: In `tests/test_algo.py` P15-Testgruppen (bekannte Werte · Übereinstimmung mit DP über
  5000 Zufallsfälle · NaN-Fail-soft [3 Positionen] · Kategoriegruppierung [search=P8+P15] · difftest Python
  exakt · C bitgenau). Gesamte Testsuite **4848 passed / 0 failed** (+7) · ruff clean · mypy keine neuen
  Fehler (origin/master=15, also dieselbe Anzahl).

### Ergebnis der P15-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Adversarial-Review-Workflow mit 3 Linsen (Korrektheit / C-Sicherheit+Gate-Ehrlichkeit / Integration,
Mutation-Verifikation) = **0 Findings** (keine Linse hatte Beanstandungen). Der strikte Vergleich beim
Patience Sorting, die NaN-Guard, die Sicherheit des tails-Puffers, die Unabhängigkeit des O(n²)-DP-Oracles
und die Frage, ob der Holdout den strikten Vergleich allein antreibt, wurden geprüft, ohne dass ein
falsifizierbarer Mangel gefunden wurde. Die vorab durchgeführte Mutation (3/3 erfasst: strikt `<`→`<=`/
NaN-Guard/Richtung der Binärsuche) und die 40k-DP-Übereinstimmung belegen ein robustes Gate.

## P16-Abschlussbericht — Inversionszahl (Mergesort-Verfahren) (2026-08-17, Opus5[1m]/ultracode, 12h autonom)
**Statistik um 1 op erweitert (zweite Statistikrunde nach P9 count_distinct/mode_value)**:
`count_inversions` (KIND_REDUCE) = die **Inversionszahl** (Anzahl der **strikten** Paare mit i<j und
a[i] > a[j]) einer beliebigen NaN-freien Double-Folge wird per **Zähl-Mergesort** in O(n log n) bestimmt.
Nur Vergleiche (keine Arithmetik auf den Werten), daher ist der Count für ein gegebenes Array eindeutig =
**C==Python bitgenau**. Beim Merge wird bei jeder Vorwegnahme der rechten Spalte die verbleibende Anzahl der
linken Spalte addiert (klassisches Verfahren). Der Count ist eine nicht-negative Ganzzahl, daher ist
**-1.0 ein sicherer Sentinel-Wert**: NaN→-1.0 Fail-soft, leer/einzeln→0.0. Gleichheit ist keine Inversion
(bei Gleichstand wird links zuerst genommen = `arr[i] <= arr[j]`).
- **Reale Messung des Honest Gate (passed=True · c_verified=true · ziglang cc)**: Python==**unabhängige
  O(n²)-Brute-Force-Zählung** (separater Codepfad zu Mergesort) **Diff 0,0 (exakt)** / generiertes
  **C==Python bitgenau Diff 0,0**. Vorab real gemessen = **40k Zufallsfälle (Ganzzahlen+Float · kleiner
  Wertebereich, viele Gleichstände = treibt den strikten Vergleich an) mit 0 Abweichungen zur Brute-Force**.
- **★Gate-Mutation-Test (Selbstverifikation)**: 4 Mutanten (Gleichstandsbehandlung `<=`→`<` [zählt Gleichheit
  fälschlich als Inversion] / Off-by-one bei der Inv-Zählung / NaN-Guard entfernt / keine Zählung [inv=0])
  werden **alle erfasst** (passed=False). Der Fall lauter gleicher Werte `[2,2,2]`→0 sowie Duplikatfälle
  treiben den strikten Vergleich allein an.
- **Holdout**: bekannte Werte (sortiert→0 · umgekehrt sortiert→n(n-1)/2 · `[2,1,3]`→1 · `[3,1,2]`→2 ·
  leer/einzeln→0) + **lauter gleiche Werte→0 (strikt)** + Duplikate (sortiert→0 · `[2,1,2,1]`→3) +
  -0.0/+0.0-Gleichheit (beide Reihenfolgen) + ±inf + NaN an **Anfang/Mitte/Ende** als Fail-soft +
  Zufallsfälle (viele Ganzzahl-Gleichstände + Float).
- **C-Sicherheit**: arr/tmp per malloc(n) · Rekursionstiefe O(log n) · Malloc-Fehlschlag liefert -1.0 ·
  NaN-Guard steht vor allen Vergleichen. Der Count wird als long long geführt (n(n-1)/2 < 2^63 für
  n < 4,3e9), der zurückgegebene Double ist bei n(n-1)/2 < 2^53 exakt (honest: bei extremen n kann dies
  ungenau werden, im Holdout-/Praxisbereich jedoch exakt).
- **Work-Graph-op-Welle**: count_inversions wurde als `algo_difftest --op`-Gate-Node modelliert
  (`1 op = 1 Node`) → mit `run-once` unbeaufsichtigt done. = **alle 37 algo-op sind nun im Work-Graph als
  Gate modelliert** (36→37).
- **Regression**: In `tests/test_algo.py` P16-Testgruppen (bekannte Werte · Übereinstimmung mit
  Brute-Force über 5000 Zufallsfälle · NaN-Fail-soft [3 Positionen] · Kategoriegruppierung [stat=P9+P16] ·
  difftest Python exakt · C bitgenau). Gesamte Testsuite **4855 passed / 0 failed** (+7) · ruff clean ·
  mypy keine neuen Fehler (origin/master=15, also dieselbe Anzahl). **Die Adversarial-Review wurde in
  einem isolierten Worktree durchgeführt** (Lehre aus P14, wo der Review-Agent die algo.py des Zielrepos
  mutierte = nach dem Commit erfolgt die Review in einem isolierten Worktree → das Ergebnis fließt als
  Follow-up ein).

### Verstärkung nach der P16-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
**★Der erste Einsatz der Worktree-isolierten Review war erfolgreich**: 3 Linsen × isolierter Git-Worktree
(jeder Agent erstellt ab cd76da0 eine eigene Kopie und mutiert dort) → **das algo.py im Haupt-Repo blieb
durchgehend sauber** (auch der Verifikations-Agent vermerkte explizit „das reale Repo ist read-only, mutiert
wurde im isolierten Worktree, aufgeräumt"). Das Kontaminationsproblem von P14 wurde damit strukturell gelöst.
Ergebnis = **2 CONFIRMED (beide LOW)** · Korrektheitssystem 0 (die op ist korrekt):
- **[LOW Gate-Abdeckung] Long-long-Breite nicht falsifiziert**: Der maximale Inversionswert im Holdout lag
  unter INT_MAX (Länge ≤ 40 → maximal ~700), sodass ein Mutant, der den C-Akkumulator von `long long` auf
  `int` verengt, das Gate besteht (obwohl das ausgelieferte long long korrekt ist). **Selbst reproduziert
  bestätigt** (der Int-Verengungs-Mutant liefert passed=True · bei n=65537 in strikt absteigender Reihenfolge
  wird der wahre Wert 2147516416 > INT_MAX von int fälschlich zu -2147450880 gewrapt). **Behebung** =
  (1) ein **unabhängiges Fenwick-(BIT)-Oracle `_fenwick_inversions`** hinzugefügt (O(n log n) · anderer
  Algorithmus als Mergesort = kann auch bei großem n, wo O(n²)-Brute-Force zu langsam ist, prüfen), (2) ein
  **Witness in strikt absteigender Reihenfolge** (n=65537, Inversionszahl 2147516416 > INT_MAX) wurde zum
  Holdout+den bekannten-Werte-Tests hinzugefügt → bei erneuter Messung wird der Int-Verengungs-Mutant
  **erfasst** (passed=False).
- **[LOW Anmerkung] Kommentarfehler**: Bei `[inf,1,-inf]` wurde `-> 2` vermerkt, tatsächlich ist es 3 (alle
  3 Paare sind Inversionen). Das Gate vergleicht mit dem Oracle (stimmt bei 3 überein), daher lässt eine
  Fehlimplementierung nicht durch = **nur die Anmerkung war ungenau**. **Behebung** = Kommentar auf `-> 3`
  korrigiert (op/Oracle/Fenwick stimmen alle auf 3 überein, bestätigt).
- **★Bestätigung der Prozessverbesserung**: Ab sofort ist die Worktree-Isolierung Standard für Reviews.
  Gesamte Testsuite grün · ruff clean · mypy keine neuen Fehler.

## P17-Abschlussbericht — Maximale Teilfolgensumme (Kadane-Verfahren) (2026-08-17, Opus5[1m]/ultracode, 12h autonom)
**Suchen/Optimierung um 1 op erweitert (dritte Suchrunde nach P8 binary_search/kth_smallest · P15
lis_length)**: `max_subarray` (KIND_REDUCE) = für eine Folge ganzzahliger Double-Werte wird die **maximale
Summe einer zusammenhängenden Teilfolge** per **Kadanes O(n)-Reset-Durchlauf**
(`cur = max(0, cur+x); best = max(best, cur)`) bestimmt. **Die leere Teilfolge ist zulässig** (Summe 0),
daher ist das Ergebnis **stets ≥ 0** (bei lauter negativen Werten 0.0) = **-1.0 ist ein sicherer
Sentinel-Wert**. Im ganzzahligen Bereich (jeweils `|x| ≤ 2^52` und die laufende Summe der Beträge ≤ 2^52)
bleiben alle Teilsummen exakt ganzzahlig < 2^53 → das Ergebnis ist exakt · **C==Python bitgenau**. Das
unabhängige Oracle (Brute-Force-Maximum über alle O(n²) Teilfolgen) stimmt wegen der **Assoziativität der
Ganzzahladdition** exakt mit Kadane überein. Fail-soft -1.0 = bei NaN / inf / nicht-ganzzahlig /
`|x| > 2^52` / Overflow der laufenden Summe.
- **Reale Messung des Honest Gate (passed=True · c_verified=true · ziglang cc)**: Python==**unabhängiges
  O(n²)-Brute-Force-Verfahren** (separater Codepfad zu Kadane) **Diff 0,0 (exakt)** / generiertes
  **C==Python bitgenau Diff 0,0**. Vorab real gemessen = **5000 Zufallsfälle (Ganzzahlen · gemischte
  Vorzeichen · kleiner Wertebereich zur massiven Erzeugung von Gleichständen/Resets) mit 0 Abweichungen
  zur Brute-Force**.
- **★Gate-Mutation-Test (Selbstverifikation)**: (1) Overflow-Guard `>`→`>=` (Witness exakt bei 2^52 löst
  fälschlichen Bail aus) → **erfasst**, (2) Entfernen des Resets `if cur<0: cur=0` (wird zur Suffix-Summe =
  falsch) → **erfasst**, (3) Entfernen der Bereichs-Guard (bei inf stürzt `int()` ab) → **erfasst**,
  (4) **echtes nicht-leeres Kadane** (keine leere Option) → beim Holdout mit lauter negativen Werten
  `[-1,-2,-3]` (korrekt 0.0) → **erfasst** (err=5.0), (5) Update von best mit `>`→`>=` (äquivalent) → wie
  erwartet nicht erfasst.
- **★Beleg für die Designentscheidung**: Ein echtes nicht-leeres Kadane liefert bei `[-1,-2,-3]` das größte
  Element -1.0 zurück = **kollidiert mit dem Fail-soft-Sentinel -1.0**. Der Mutation-Test belegt, dass die
  Designentscheidung „leere Teilfolge zulässig ⇒ Ergebnis ≥ 0 ⇒ -1.0 ist sicher" genau diese Kollision
  vermeidet (die Zulässigkeit der leeren Teilfolge ist die Voraussetzung für die Sicherheit des Sentinels).
- **Holdout**: leer/einzeln positiv (5)/einzeln negativ (0) · **lauter negativ→0 (pinnt die Zulässigkeit der
  leeren Teilfolge allein)** · klassisches Kadane-Beispiel `[-2,1,-3,4,-1,2,1,-5,4]`→6 · Reset durch
  Einbruch in der Mitte · 0/-0.0-vorzeichenbehaftete Null · **Overflow-Grenze bei 2^52 gepinnt**
  (`[2^52]` = laufende Summe 2^52 → **gültig** [pinnt `>` vs. `>=`] / `[2^52,1]` = 2^52+1 → -1.0 /
  `[2^51,2^51]` = 2^52 → gültig / einzeln `[2^52+1]` > 2^52 → -1.0) · nicht-ganzzahlig/±inf (Anfang/Mitte) /
  NaN (Anfang/Mitte/Ende) als Fail-soft · zufällige Ganzzahlen.
- **C-Sicherheit**: Die Bereichsprüfung `x >= -LIM && x <= LIM` fängt NaN/inf/übergroße Werte **vor** dem
  Cast auf (long long) ab (NaN→int ist UB). Die Akkumulation erfolgt als long long, laufende Summe ≤ 2^52,
  daher alle Teilsummen < 2^63 (kein Overflow), der zurückgegebene Double ist bei best < 2^53 exakt.
- **Work-Graph-op-Welle**: max_subarray wurde als `algo_difftest --op`-Gate-Node modelliert
  (`1 op = 1 Node`) → mit `run-once --available tool:command` unbeaufsichtigt done (Gate-JSON passed=True ·
  c_verified=true). = **alle 38 algo-op sind nun im Work-Graph als Gate modelliert** (37→38).
- **Regression**: In `tests/test_algo.py` P17-Testgruppen (registered_kind · bekannte Werte ·
  Übereinstimmung mit Brute-Force über 5000 Zufallsfälle · Fail-soft/Overflow · difftest Python exakt · C
  bitgenau). **Honest**: Beim ersten vollständigen Lauf schlug `test_search_ops_registered_kinds` mit
  1 Fehlschlag fehl (die Aktualisierung der search-Kategoriemenge war nur an **einer von zwei** Stellen
  erfolgt [`test_categories_grouping` fehlte]) → erkannt und sofort behoben, beim erneuten Lauf
  **test_algo.py 295 passed / 0 failed** · ruff clean · mypy keine neuen Fehler (origin/master=15, also
  dieselbe Anzahl). **Die Adversarial-Review wurde in einem isolierten Worktree durchgeführt** (Standard
  seit P16).

### Verstärkung nach der P17-Adversarial-Review (2026-08-17, [[feedback_no_solo_ai_judgment]])
**Worktree-isolierte Review (4 Agenten · 3 Linsen + Adversarial-Verifikation) = 1 CONFIRMED (LOW ·
Gate-Ehrlichkeit) / 0 REFUTED**. Der Verifikations-Agent reproduzierte alles im isolierten Worktree und
vermerkte, dass das algo.py im Haupt-Repo nicht kontaminiert wurde (`status --porcelain` zeigt nur die
automatische SESSION_SUMMARY). Korrektheit/Integration 0 (die op ist korrekt):
- **[LOW Gate-Ehrlichkeit] Dass C „NaN vor dem Cast ablehnt" kann vom Gate nicht falsifiziert werden**: Das
  Honest Gate kompiliert C nur mit `-O2 -std=c99 -ffp-contract=off` (ohne UBSan). Schreibt man die C-
  Bereichs-Guard nach De Morgan um: `if (!(x>=-LIM && x<=LIM))` → `if (x<-LIM || x>LIM)` (bei NaN sind beide
  Vergleiche false = NaN rutscht durch), dann ist in der nächsten Zeile `x != (double)(long long)x` das
  **`(long long)NaN` UB**, das unter -O2 zufällig zu -1.0-artigem Verhalten führt und mit Python bitgenau
  übereinstimmt → das Gate liefert passed=True. Aber dieselbe Mutation **stürzt bei einem UBSan-/
  ReleaseSafe-Build hart ab** (`panic: nan is outside the range of representable values of type
  'long long'`). **Die ausgelieferte op ist korrekt** (die Guard `!(x>=-LIM && x<=LIM)` lehnt NaN vor dem
  Cast ab) = eine Lücke in der Gate-Abdeckung (kein Produktionsfehler). Die Python-Hälfte ist bereits
  gepinnt (Entfernen der Bereichs-Guard führt zu `int(nan)` → ValueError → das Gate lässt das nicht durch),
  nur die C-Seite war asymmetrisch ungepinnt.
- **Eigene Verifikation (Selbstreproduktion)**: Eine eigenständige Probe wurde mit denselben Gate-Flags
  `-O2 -std=c99 -ffp-contract=off` kompiliert: Ausgelieferte Guard = NaN→-1.0 normal / De Morgan+UBSan =
  Trap bei `(long long)NaN` (übereinstimmend mit dem Panic aus dem Finding) / Ausgelieferte Guard+UBSan =
  kein Trap (NaN wird vor dem Cast abgelehnt = **UBSan-sauber**). **Honest Unterschied**: In meiner eigenen
  Probe stürzte De Morgan+-O2 mit Exit 3 ab, aber **im echten Gate** (`algo_difftest --op`) wurde bestätigt,
  dass es wie vom Verifikations-Agenten berichtet passed durchläuft = das UB-Verhalten von -O2 ist
  unbestimmt und in jedem Fall gilt: „mit -O2 allein lässt sich reject-before-cast nicht zuverlässig pinnen".
- **Behebung (verstärkt alle op)**: `run_c_backend` erhielt einen **UBSan-Pass** — nach dem Bit-Vergleich
  unter -O2 wird derselbe C-Code zusätzlich mit `-fsanitize=undefined -fno-sanitize-recover=all`
  rekompiliert und derselbe Holdout erneut ausgeführt. Erreichen NaN/inf/Werte außerhalb des Bereichs den
  Ganzzahl-Cast, löst das einen Trap aus → **Gate-Fehlschlag** (bei Toolchains ohne UBSan-Unterstützung
  liefert dies `"unsupported"` = neutral, um Fehlalarme zu vermeiden). **Vorab real gemessen**: Alle 38 op
  sind UBSan-sauber (0 Traps) = sicher übernehmbar, keine Fehlalarme. **Nach der Fix real gemessen**:
  ausgelieferte op = passed=True/ubsan=ok, **De-Morgan-Mutant = passed=False/ubsan=trap** (bitgenau unter
  -O2, aber von UBSan erfasst), keine Regression bei anderen op. = **„reject-before-cast" wird nun auch in
  C load-bearing** (symmetrisch zum `int(nan)`-Raise in Python). Regressionstest
  `test_ubsan_pass_catches_nan_slip_through_cast` hinzugefügt. Gesamte Testsuite
  **295→296 passed / 0 failed** · ruff clean · mypy keine neuen Fehler.
- **★Dies ist keine max_subarray-spezifische, sondern eine Verstärkung der Gate-Infrastruktur** = ab sofort
  kann das Gate bei allen algo-op falsifizieren, wenn ein nicht-endlicher Wert den Cast als UB erreicht.

## 2026-09-03: 8 Korrekturen aus der Adversarial-Review (algo + C-Codegen)

- **[HIGH] Beim C-`unsharp` (`sharpen`) fehlt das Clipping auf [0,1], wodurch nachgelagerte op von Python
  abweichen** (unsharp→gaussian maximale Abweichung 6,6e-2, unsharp→threshold(1.0) mit 512 invertierten
  Pixeln). Am Ausgang von `sharpen` wurde ein Clamp ergänzt + `codegen.py` gibt nach jeder Clip-relevanten
  Sort-Stage `clamp01()` aus (doppelte Absicherung). Nach der Fix ≤ 3e-7.
- `difftest.py` suchte nur nach gcc/cc/clang, sodass **das C-Gate in dieser Umgebung stillschweigend
  übersprungen wurde** (= die obige Abweichung blieb unsichtbar). `algo_difftest.find_c_compiler()`
  (ziglang-Fallback) wird nun gemeinsam genutzt. Das Ergebnis-Dict vermerkt jetzt `compiler`.
- Das `n` bei Graph-op war bis zur int32-Obergrenze unbegrenzt (`graph_components([2147483000,0])`
  allokierte 17 GB) → **`n ≤ 5.000.000`** (dieselbe explizite Obergrenze wie bei sieve), `m ≤ 2147483000`,
  sowohl in Python als auch in C.
- Endpunkte wurden vor der Bereichsprüfung nach `(int)` gecastet (Float→Int-Overflow-UB, UBSan-Trap) →
  Bereichs- und Ganzzahligkeitsprüfung erfolgen nun zuerst am rohen Double. UBSan-Traps 3 → 0, 39/39
  bitgenau.
- **Änderung des Sentinel-Werts (ABI)**: Bei op, „bei denen 0.0 auch eine gültige Antwort sein kann", wurde
  der Fail-soft-Sentinel von **0.0 auf −1.0** geändert — `is_prime` / `segments_intersect` /
  `edit_distance` / `point_in_polygon` / `lcs_length` (dieselbe Konvention wie bei P13–P18). Beispiel:
  `is_prime([4294967311])` (außerhalb des Definitionsbereichs) liefert nicht mehr 0.0 „zusammengesetzt",
  sondern −1.0. Unverändert (mögliche Kollision, noch zu prüfen): `pow_mod` / `gcd_seq` /
  `popcount_total` / `polygon_area2`.
- `run_algo` rundete Ganzzahlen > 2^53 über `float()`, bevor die Bereichsprüfung erfolgte → mit
  `wire_float()` löst eine Ganzzahleingabe mit |x|>2^53 nun einen `ValueError` aus (fail-closed).
- Bei geradem k nahm `box` k+1 Taps statt k / geteilt durch k (Gain 1,25) → nun mit demselben Origin wie
  scipy `uniform_filter` genau k Taps.
- Bei `difftest` führte NaN über `max(0.0, nan)=0.0` zum Bestehen des Tests → nicht-endliche Werte werden
  nun als inf behandelt und lassen den Test fehlschlagen.
- Regression: `tests/test_imgops_c.py` (neu, 11 Tests) sowie 35 weitere Tests, 5 Dateien, 355 passed
  (alle C-Tests laufen mit ziglang).
