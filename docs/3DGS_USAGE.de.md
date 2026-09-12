<!-- i18n-source-sha: 37bc63784e56 -->
# Fullseye 3DGS – Anwendung (ein einziger Befehl)

[日本語](./3DGS_USAGE.md) · [English](./3DGS_USAGE.en.md) · [简体中文](./3DGS_USAGE.zh.md) · [繁體中文](./3DGS_USAGE.tw.md) · [한국어](./3DGS_USAGE.ko.md) · **Deutsch**

Verwandelt eine MuJoCo-Simulationsszene in ein **3D-Gaussian-Splatting**-Modell und erzeugt ein rundum drehbares GIF sowie Bilder aus neuen Blickwinkeln. Die Kameraposen stammen aus den Ground-Truth-Daten der Simulation, daher wird **kein COLMAP benötigt**.

## Die einfachste Anwendung

Im imgevolve-Ordner:

```bat
3dgs go2 --open
```

Allein damit wird go2 (ein vierbeiniger Roboter) in 3DGS umgewandelt und das fertige Rundum-GIF automatisch geöffnet.

- Szene wechseln: `3dgs cassie` / `3dgs apollo` / `3dgs anymal` / `3dgs spot`
- Eigene MJCF: `3dgs <lokaler Arbeitspfad>\path\to\scene.xml`
- Liste anzeigen: `3dgs --list`

## Qualitätsvorgaben

```bat
3dgs go2 --quality fast       :: 128px / 8.000 Gaussians (wenige Sekunden, für einen schnellen Blick)
3dgs go2 --quality balanced   :: 256px / 20.000 Gaussians (Standard)
3dgs go2 --quality high       :: 384px / 45.000 Gaussians (am saubersten)
```

## Noch sauberer (densify)

```bat
3dgs go2 --quality high --densify --open
```

Mit `--densify` **erhöht das Training automatisch die Anzahl der Gaußfunktionen, um mehr Detail zu erzeugen** (nur bei nativem gsplat). Bei go2 wächst die Zahl von etwa 8.000 auf etwa 50.000, wodurch Rumpf und Beine deutlich glatter wirken. Das dauert wenige bis gut ein Dutzend Sekunden.

## Das Backend wird automatisch gewählt

- Ist **natives gsplat** (Tile-CUDA) verfügbar, wird es automatisch verwendet (schnell und detailreich, mehrere hundert it/s)
- Andernfalls fällt es automatisch auf **reines PyTorch** zurück (langsamer, funktioniert aber)
- Mit `--backend torch` / `--backend gsplat` lässt es sich auch explizit festlegen

Die Umgebung (CUDA/Compiler) richtet der Launcher automatisch ein, sodass man sich nicht um vcvars & Co. kümmern muss.

## Über Studio

`spikes/studio_app.py` starten → im Panel "Sim-Modell in 3D ansehen / in 3DGS umwandeln" den Szenennamen (Chip anklicken oder eintippen) und die Qualität wählen, dann "3DGS-Training 🎇" → nach Abschluss öffnet sich das Rundum-GIF.

## Ausgabe

Unter `out/3dgs_<scene>/` (oder dem mit `--out` angegebenen Ziel) entstehen:
- `turntable.gif` … Rundum-Vorschau
- `novelview.png` … links = Ground Truth / rechts = Rendering aus neuem Blickwinkel
- `gaussians.npz` … trainierte Gaußfunktionen (npz)
- `gaussians.ply` … Standard-3DGS-.ply (bei nativem Backend). Lässt sich **per Drag & Drop in einen Web-Viewer wie SuperSplat** öffnen
- `report.json` … Kennzahlen wie PSNR

## Voraussetzungen

- Ein venv `.venv-gsplat` für das GPU-Training (torch cu128)
- Für natives gsplat zusätzlich `.gsplat-cuda` (CUDA 12.8) sowie die C++-Werkzeuge von VS BuildTools. Details und Reproduktionsschritte stehen in `docs/GSPLAT_NATIVE_WINDOWS.md`

> Ehrlicher Hinweis: Wie stark `--densify` hilft, hängt von der Szene ab. Ein massiver Körper wie go2 wird sauber, aber ein dünner Zweibeiner wie cassie kann sich an die Trainingsansichten überanpassen, sodass der Hold-out-Blick etwas weicher ausfällt. Empfehlung: zunächst ohne die Option testen und sie nur bei Bedarf hinzufügen.

## Bewegung abspielen (--motion)

```bat
3dgs go2 --motion --open
```

Statt eines Standbilds entsteht hier ein **3DGS eines sich bewegenden Roboters**. So funktioniert es:
1. 3DGS wird in der kanonischen Pose trainiert
2. Per **Segmentierung** wird bestimmt, von welchem MuJoCo-Body (Glied) jede Gaußfunktion stammt, und entsprechend gerigged
3. Die Gelenke werden bewegt (Standard = Sinuswelle), und für jeden Frame wird anhand der Body-Posen (Ground Truth der Simulation) starres Skinning durchgeführt → neu gerendert → `motion.gif`

Da ein Roboter aus einer Menge starrer Glieder besteht, bewegt er sich natürlich, ohne dass volles 4D-GS nötig wäre. Mit `--frames N` lässt sich die Bildanzahl ändern.

> Ehrlich: Die Standardbewegung ist eine Demo-Sinuswelle (keine echte Gangart-Policy). Da die Posen der Simulation Ground Truth sind, bricht nichts strukturell zusammen, aber in der Nähe der Füße kann leichtes Rauschen auftreten (Grenzbereich der Body-Zuordnung der Initialisierungspunkte).

### Gangart (gait) automatisch erzeugen

```bat
3dgs go2 --motion --gait trot --open
```

Mit `--gait trot` wird automatisch ein **Trab-Gangmuster für Vierbeiner** erzeugt und abgespielt (diagonale Beine treten phasengleich). Die Beine werden anhand der Gelenknamen (FL/FR/RL/RR oder LF/RF/LH/RH + thigh/calf) automatisch erkannt, daher funktioniert es bei go2 und anymal. Nicht erkennbare Modelle fallen auf eine Sinuswelle zurück. Um die Ausgabe einer echten Gangart-Policy zu verwenden, nutzt man `--motion-file traj.npy` (eine qpos-Trajektorie (F,nq)).
