<div class="vlang" markdown="1">

[日本語](../index.md) · [English](../en/index.md) · [简体中文](../zh/index.md) · [繁體中文](../tw/index.md) · [한국어](../ko/index.md) · **Deutsch** · [हिन्दी](../hi/index.md)

</div>

# Fullseye — ViEW2026

Physiksimulation und Bildverarbeitung, mit KI kombiniert und an Ground Truth geprüft.

Kachel antippen öffnet Video oder Abbildung (▶ = bewegt).

<style>
.vlang { font-size: 14px; line-height: 2; }
.vg { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0 20px; }
@media (min-width: 600px) { .vg { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (min-width: 900px) { .vg { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
.vg a { display: block; position: relative; text-decoration: none; color: inherit; }
.vg img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 6px; background: #222; }
.vg b { position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,.6); color: #fff; font-size: 12px; padding: 1px 6px; border-radius: 9px; }
.vg span { display: block; font-size: 13px; line-height: 1.3; margin-top: 3px; }
.vl li { margin-bottom: 8px; }
</style>

<div class="vg">
<a href="../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="../thumbs/poc_real_defect_floor.jpg" alt="Schwache Defekte" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Schwache Defekte</span></a>
<a href="../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="../thumbs/poc_active_contours.jpg" alt="Aktive Konturen" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Aktive Konturen</span></a>
<a href="../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="../thumbs/poc_dic_strain.jpg" alt="DIC-Dehnung" loading="lazy" width="320" height="320"><b>&#9654;</b><span>DIC-Dehnung</span></a>
<a href="../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="../thumbs/poc_focus_stacking.jpg" alt="Fokus-Stacking" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Fokus-Stacking</span></a>
<a href="../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="../thumbs/poc_registration_basin.jpg" alt="Punktwolken-ICP" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Punktwolken-ICP</span></a>
<a href="../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="../thumbs/poc_stockpile_volume.jpg" alt="Haldenvolumen" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Haldenvolumen</span></a>
<a href="../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="../thumbs/poc_ct_fidelity.jpg" alt="CT-Rekonstruktion" loading="lazy" width="320" height="320"><span>CT-Rekonstruktion</span></a>
<a href="../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="../thumbs/poc_ct_void_morphology.jpg" alt="CT-Poren" loading="lazy" width="320" height="320"><b>&#9654;</b><span>CT-Poren</span></a>
<a href="../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="../thumbs/poc_interferometry_step.jpg" alt="Weißlicht-Stufen" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Weißlicht-Stufen</span></a>
<a href="../../articles/assets/poc/poc_polarization_specular/03_separation.png"><img src="../thumbs/poc_polarization_specular.jpg" alt="Polarisation" loading="lazy" width="320" height="320"><span>Polarisation</span></a>
<a href="../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="../thumbs/poc_photoelasticity.jpg" alt="Spannungsoptik" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Spannungsoptik</span></a>
<a href="../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png"><img src="../thumbs/poc_thermography_ndt.jpg" alt="Thermografie" loading="lazy" width="320" height="320"><span>Thermografie</span></a>
<a href="../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="../thumbs/poc_motion_magnification.jpg" alt="Bewegungsverstärkung" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Bewegungsverstärkung</span></a>
<a href="../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="../thumbs/poc_table_tennis_bounce.jpg" alt="Tischtennis-Absprung" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Tischtennis-Absprung</span></a>
<a href="../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png"><img src="../thumbs/poc_compound_eye.jpg" alt="Facettenauge" loading="lazy" width="320" height="320"><span>Facettenauge</span></a>
<a href="../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="../thumbs/poc_pegsim_insertion.jpg" alt="Peg-in-Hole" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Peg-in-Hole</span></a>
<a href="../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="../thumbs/poc_air_hockey_intercept.jpg" alt="Airhockey" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Airhockey</span></a>
<a href="../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="../thumbs/poc_tacsim_elastic_membrane.jpg" alt="Taktiler Sensor" loading="lazy" width="320" height="320"><b>&#9654;</b><span>Taktiler Sensor</span></a>
</div>

## Was zu sehen ist, und die gemessene Zahl

Jede Zahl ist gegen eine Ground Truth gemessen, die der PoC selbst eingesetzt hat (geschlossene Form, analytische Lösung oder veröffentlichter Wert); der PoC gibt beim Ausführen denselben Wert aus.

<div class="vl" markdown="1">

**Bildprüfung und Oberfläche**

- [Schwache Defekte](../../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif) (GIF): Derselbe eingesetzte Defekt wird auf einer echten Ziegeltextur und auf einem synthetischen Hintergrund mit gleichem Rauschen stärker. **Selbst bei gleichem Rauschen liegt die Nachweisgrenze auf echten Texturen beim 2.03- bis 3.47-Fachen der synthetischen (Defekte mit bekannter Position und Amplitude).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py)
- [Aktive Konturen](../../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4) (Video): Die klassische Snake (rot) überbrückt die U-Kerbe, GVF (blau) erreicht den Grund. Grün ist die wahre Kante. **Nur die äußere Kraft auf GVF umgestellt: Dice 0.993 gegenüber der wahren Kante.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_active_contours.py)
- [DIC-Dehnung](../../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4) (Video): Dehnungskarten aus Speckle-Bildern, während die Zuglast steigt (die Maschine dreht sich zugleich um 2 Grad). **Wahre Dehnung 3000 µε. Die kleine Dehnung liest wegen der Drehung nur 2341 µε, Green-Lagrange 2961 µε (Theorie 3005 µε).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

**3-D-Messung und Geometrie**

- [Fokus-Stacking](../../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4) (Video): Beim Fokusdurchlauf über 17 Frames entstehen das durchgehend scharfe Bild und die Tiefenkarte. **Scharfes Gesamtbild PSNR 33.69 dB (das 1 mittlere Einzelbild 28.52 dB), Tiefenfehler 0.467 mm (texturierte Bereiche).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)
- [Punktwolken-ICP](../../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4) (Video): ICP, je 1 Iteration pro Schritt, ab anfänglichen Drehfehlern von 30, 90 und 150 Grad. **Drehfehler nach 60 Iterationen: 0.6 Grad ab 30 und 90 (Erfolg), 179.5 Grad ab 150 (Fehlschlag).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)
- [Haldenvolumen](../../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4) (Video): Umlauf um eine Halde, die 3-D-Scanpositionen steigen von 1 auf 3; Farbe = interpolierte minus wahre Oberfläche. **Volumenfehler +17.20 % -> +0.05 % (wahre Basis; Sollvolumen in geschlossener Form 3572.6089 m³).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

**Röntgen-CT und Volumen**

- [CT-Rekonstruktion](../../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png) (Abbildung): Das Shepp-Logan-Phantom wird mit 180 bis hinab zu 12 Projektionen aufgenommen und rekonstruiert. **FBP mit 12 Projektionen (RMSE 0.2576) unterliegt sogar einem leeren Bild (0.2420). Eine Massenprüfung fand -3.34 % Verlust, korrigiert auf -0.0099 %.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)
- [CT-Poren](../../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4) (Video): 2 Fügeschichten mit fast gleichem Porenanteil: Schnittdurchlauf mit rotierenden 3-D-Poren (Video 4.3 MB). **Porenanteil 2.46 % zu 2.63 %, aber der Median des Abstands zur Grenzfläche beträgt 60.0 µm zu 10.0 µm.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

**Optik, Interferometrie, Polarisation**

- [Weißlicht-Stufen](../../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4) (Video): Die eingesetzte Stufe wächst von 0 auf 0.90 µm, gemessen über die Kohärenz-Einhüllende und per Phasenschieben. **Bias unter 2.4 nm bei 1 % Rauschen (Stufen 50-500 nm). Phasenschieben springt bei 0.153 µm um λ/2.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)
- [Polarisation](../../articles/assets/poc/poc_polarization_specular/03_separation.png) (Abbildung): Mit Polarisation entfernte Spiegelreflexion und die Form des Restfehlers. **Der Fehler des diffusen Anteils folgt der geschlossenen Form R_p·E und ist beim Brewster-Winkel 56.31 Grad gleich 0.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)
- [Spannungsoptik](../../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4) (Video): Unter Last quellen Streifen aus der Scheibe; drehen der Polarisatoren verschiebt die Isoklinen. **Streifenordnung in der Mitte 2.38, wie die geschlossene Form sagt. Das Polariskop des op stimmt mit dem Lehrbuch auf 2.2e-16 überein.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

**Wärme, Akustik, Zeitreihen**

- [Thermografie](../../articles/assets/poc/poc_thermography_ndt/02_depth_map.png) (Abbildung): Tiefenkarte von 16 Delaminationen aus der Oberflächentemperatur nach einem Blitz. **Ein 0.5 mm tiefer, 2 mm breiter Defekt: +612 % mit 25 s Anpassungsfenster, -9 % mit 4 s.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)
- [Bewegungsverstärkung](../../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4) (Video): Eine Oberfläche schwingt um 0.1 px: links das Rohvideo, rechts 10-fach verstärkt. **Wahre Amplitude 0.1000 px; gemessen roh 0.10012, nach Verstärkung 0.10013 px. Sie hilft dem Auge, nicht der Messung.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)
- [Tischtennis-Absprung](../../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (Video): ITTF-Tischtest: Ball aus 30 cm fallen lassen und die Sprunghöhe aus dem Video lesen. **Aus dem Video gelesene Sprunghöhe 23.0 cm (Ground Truth 23.0 cm).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)

**Robotik und räumliche Wahrnehmung**

- [Facettenauge](../../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (Abbildung): Ein Facettenaugen-Array als Lichtfeldsensor simuliert; derselbe Punkt wird aus N Ommatidien überlagert. **SNR-Gewinn 2.25 bei N=5 (√5 = 2.24) und 5.33 bei N=49 (√49 = 7.00).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [Peg-in-Hole](../../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): Eine Handgelenkkamera misst das Loch, der Arm fährt darüber, ein nachgiebiges Handgelenk setzt den Stift ein (MuJoCo). **7 Servoschritte verringern den wahren Versatz von 2.24 auf 0.03 mm; korrigiertes Einsetzen gelingt 12 / 12.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [Airhockey](../../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): Ein Puck wird mit einer groben Kamera verfolgt und sein Schnittpunkt mit der Abwehrlinie vorhergesagt; mit mehr Frames wird das Band schmaler. **Das 95-%-Band des Schnittpunkts schrumpft von 145 mm bei N = 3 Frames auf 7 mm bei N = 16.** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [Taktiler Sensor](../../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): Eine Kugel drückt stärker auf eine elastische Membran; der Kontaktradius wird aus dem Membranbild gelesen. **Gegenüber der geschlossenen Hertz-Form: Kontaktradius 0.05-0.26 %, Kraft 0.14-0.79 % (0.02-0.12 N).** [Quelle](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

</div>

## Was Fullseye ist

Eine Plattform, die Physiksimulation (einschließlich Sensorik wie Optikdesign und 3-D-Messung) und klassische Bildverarbeitung über MCP und RAG an eine KI übergibt, sie für jede Aufgabe eine Kombination ausarbeiten lässt und die Aufgabe interaktiv löst, geprüft durch Typkonsistenz und Bewertung gegen Ground Truth. Open Source (Apache-2.0).

<details markdown="1">
<summary><b>Ausprobieren</b> (Python 3.11)</summary>

```
pip install fullseye
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
python examples/poc_focus_stacking.py
```

Der Fokus-Stacking-PoC läuft etwa 20 Sekunden und gibt seine Zahlen gegen Ground Truth sowie `PASS` aus. Abbildungen landen in `out/figures/poc_focus_stacking/`.

</details>

<details markdown="1">
<summary><b>Links</b></summary>

- [GitHub (Quellcode)](https://github.com/furuse-kazufumi/fullseye)
- [Galerie (alle Abbildungen)](../../GALLERY.en.md)
- [Operatoren finden / aus einer KI nutzen (RAG)](../../AI_RAG_GUIDE.de.md) · [Über MCP nutzen](../../MCP.md) _(ja)_
- [Dokumentationsindex](../../README.de.md)

</details>

<details markdown="1">
<summary><b>Paper</b></summary>

- **Titel**: Fullseye：型付き演算子と物理シミュレーションに基づく画像検査・三次元計測基盤 _(ja)_ (eine Plattform für Bildprüfung und 3-D-Messung auf Basis typisierter Operatoren und Physiksimulation)
- **Autor**: Kazufumi Furuse (unabhängiger Forscher)
- **Veranstaltung**: ViEW2026, Workshop zur praktischen Anwendung von Bildverarbeitung
- **Paper-PDF**: ab 2026-11-26 verfügbar

**Zusammenfassung (aus dem Japanischen übersetzt)**: Wir stellen Fullseye vor, eine Open-Source-Plattform, die Verarbeitungen für Bildprüfung und 3-D-Messung als Ketten von Operatoren mit deklarierten Ein- und Ausgabedatentypen aufbaut, sie quantitativ gegen eine durch Physik- und Abbildungssimulation erzeugte Ground Truth bewertet und Ablauf, Bewertung und Fehlerbedingungen zur Wiederverwendung festhält. Sie besteht aus rund 3,000 typisierten Operatoren, einer Prüfung, die Typfehler vor der Ausführung ablehnt, einer mehrsprachigen Operatorsuche (RAG) und über 200 Machbarkeitsprogrammen mit Ground Truth. Berichtet werden die quantitative Bewertung repräsentativer Beispiele und die Unterscheidung zwischen synthetischer, gemessener und Hardware-Validierung.

</details>
