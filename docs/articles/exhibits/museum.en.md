Now the discipline-by-discipline exhibit rooms. Medicine, archaeology, biology, space, paleontology, geology, meteorology, oceanography, botany — this corner exists to show that **the same op system cuts straight into images from any field**. Caption conventions from here on are the same as above (real data gets a source link; AI-generated is labeled as such).

#### Paleontology

[![Spiral extraction from an ammonite fossil](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_real_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_real.png)

*↑ The spiral of an ammonite fossil ([Smithsonian Open Access, CC0](http://n2t.net/ark:/65665/34afa6692-b3f9-408d-90dc-cc53097171b6)) extracted with `canny`. Ops used: `rgb1_to_gray`, `canny`, `overlay_mask`.*

[![Skin-texture analysis of a T. rex life reconstruction](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trex_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trex.png)

*↑ Skin texture of a Tyrannosaurus life reconstruction analyzed with `std_filter` / `texture_laws`. The material is **AI-generated (gemini-2.5-flash-image) simulated data** (not a real specimen).*

[![Multi-Otsu classification of a Triceratops life reconstruction](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_triceratops_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_triceratops.png)

*↑ A Triceratops life reconstruction region-classified by multi-Otsu. The material is **AI-generated simulated data**. Ops used: `xsk2_multiotsu`, `colorize_labels`.*

[![Feather-flow analysis of a feathered dinosaur](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_feathered_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_feathered.png)

*↑ The flow of a feathered dinosaur's plumage analyzed with Gabor filters. The material is **AI-generated simulated data**. Ops used: `sk_gabor`, `std_filter`.*

[![Log-spiral FFT of an ammonite cross-section](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_section_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_section.png)

*↑ The logarithmic spiral of an ammonite cross-section observed through its FFT spectrum. The material is **AI-generated simulated data**. Ops used: `cv_clahe`, `cx_fft`, `cx_magnitude`.*

[![Relief-enhancing a trilobite's segments](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trilobite_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trilobite.png)

*↑ A trilobite's body segments relief-enhanced with `gray_tophat`. The material is **AI-generated simulated data**.*

#### Space

[![Filament extraction in the Carina Nebula](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_carina_thumb.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_carina.png)

*↑ The filament structure of the Carina Nebula ([NASA/STScI Webb, public domain](https://images.nasa.gov/details/carina_nebula)) extracted with `sk_frangi` — an op originally for enhancing blood vessels. A case of a medical op cutting into astronomy.*

[![Texture analysis of the Nili Patera dunes on Mars](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_mars_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_mars.png)

*↑ The texture of Martian dunes ([NASA/JPL-Caltech/Univ. of Arizona, public domain](https://images.nasa.gov/details/PIA18244)) analyzed with `std_filter` / `texture_laws`.*

[![FFT spectrum of the Sunflower Galaxy](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_galaxy_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_galaxy.png)

*↑ The frequency structure of a spiral galaxy ([NASA GSFC, public domain](https://images.nasa.gov/details/hubble-sees-a-galactic-sunflower_21136469209_o)) visualized with `cx_fft`.*

#### Medicine (Everything in This Block Is AI-Generated Simulated Data)

[![Enhancement and edge extraction of a chest-X-ray-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_chest_xray_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_chest_xray.png)

*↑ A chest-X-ray-**style** image enhanced and edge-extracted with `cv_clahe` + `sobel_amp`. **AI-generated simulated data** (not a real patient or scan).*

[![Multi-Otsu classification of an H&E-histology-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_histology_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_histology.png)

*↑ An H&E-tissue-section-**style** image tissue-classified by multi-Otsu. **AI-generated simulated data**.*

[![Contrast enhancement of a brain-MRI-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_brain_mri_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_brain_mri.png)

*↑ A brain-MRI-**style** image with tissue contrast enhanced by `cv_clahe` + `unsharp`. **AI-generated simulated data**.*

[![Blood-cell counting on a blood-smear-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_blood_smear_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_blood_smear.png)

*↑ Blood cells in a blood-smear-**style** image segmented and counted (131 detected). **AI-generated simulated data**. Ops used: `segment_objects(otsu)`, `colorize_labels`.*

[![Contour extraction of an anatomical-illustration-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_anatomy_heart_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_anatomy_heart.png)

*↑ The contours of an anatomical-illustration-**style** image extracted with `canny`. **AI-generated simulated data**.*

#### Biology

[![Tracing a neuron's dendrites](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_neuron_thumb.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_neuron.png)

*↑ The dendrites in a neuron fluorescence image traced with `sk_frangi`. **AI-generated simulated data**.*

[![Segmenting and counting diatoms](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_diatoms_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_diatoms.png)

*↑ A diatom micrograph segmented and counted (123 detected). **AI-generated simulated data**.*

[![Shadow-region enhancement of a deep-sea anglerfish](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_deepsea_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_deepsea.png)

*↑ The dark regions of a deep-sea creature enhanced with `cv_clahe`. **AI-generated simulated data**.*

[![Periodic-structure analysis of butterfly wing scales](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_butterfly_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_butterfly.png)

*↑ The periodic structure of a butterfly's wing scales analyzed with `sk_gabor`. **AI-generated simulated data**.*

#### Archaeology

[![Elliptic Fourier descriptors of a pottery silhouette](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_amphora_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_amphora.png)

*↑ The silhouette of an amphora ([The Metropolitan Museum of Art Open Access, CC0](https://www.metmuseum.org/art/collection/search/254896)) shape-reconstructed with elliptic Fourier descriptors (EFD). Raising the harmonics 2 → 8 → 32 makes the curve cling ever closer to the contour — a method actually used in archaeological pottery-shape classification. Ops used: `otsu`, `fourierdesc.elliptic_fourier`, `fourierdesc.reconstruct`.*

[![Relief enhancement of a stone stele](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_relief_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_relief.png)

*↑ The carving of an Assyrian stone relief ([The Metropolitan Museum of Art, CC0](https://www.metmuseum.org/art/collection/search/322611)) relief-enhanced with `gray_tophat`.*

[![Pigment enhancement of a cave painting (the DStretch approach)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cave_painting_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cave_painting.png)

*↑ The fading pigments of a cave painting enhanced with decorrelation stretch (the same family of technique as DStretch, the rock-art survey standard). **AI-generated simulated data**. Op used: `principal_comp`.*

[![Enhancing the impressions on a cuneiform tablet](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cuneiform_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cuneiform.png)

*↑ The character impressions of a cuneiform clay tablet enhanced with `gray_tophat`. **AI-generated simulated data**.*

#### Geology, Meteorology, Oceanography, Botany

[![Decorrelation stretch of satellite-image lithology](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_earth_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_earth.png)

*↑ The lithology in a satellite image ([NASA JSC, public domain](https://images.nasa.gov/details/SL2-04-018)) enhanced with decorrelation stretch (a remote-sensing standard).*

[![Extracting facet ridgelines of a mineral crystal](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_mineral_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_mineral.png)

*↑ The facet ridgelines of an amethyst crystal extracted with `canny`. **AI-generated simulated data**.*

[![Mineral-grain classification of a rock thin section](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_thin_section_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_thin_section.png)

*↑ A rock thin section (polarized-microscope style) classified into mineral grains by multi-Otsu. **AI-generated simulated data**.*

[![Gradient-direction wheel of a hurricane's vortex structure](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_hurricane_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_hurricane.png)

*↑ The vortex structure of a hurricane ([NASA JSC, public domain](https://images.nasa.gov/details/iss056e162187)) visualized with a gradient-direction wheel (`sobel_dir` + `colorize_flow`).*

[![Structure enhancement of a supercell thunderstorm](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_supercell_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_supercell.png)

*↑ A supercell thunderstorm structure-enhanced with `cv_clahe` + `unsharp`. **AI-generated simulated data**.*

[![Coral-reef coverage classification](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_ocean_coral_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_ocean_coral.png)

*↑ A coral reef coverage-classified by multi-Otsu (marine-survey style). **AI-generated simulated data**.*

[![Extracting fern leaf veins](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_fern_thumb.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_fern.png)

*↑ The leaf veins of a fern extracted with `sk_frangi`. **AI-generated simulated data**.*

[![Segmenting and counting a pollen-SEM-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_pollen_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_pollen.png)

*↑ A pollen-SEM-**style** image segmented and counted (41 detected). **AI-generated simulated data**.*

Across these 41 exhibits, **every piece of real data carries its source and license** (the detailed attribution table is in [ACADEMIC_ATTRIBUTION.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/ACADEMIC_ATTRIBUTION.md)), and **every AI-generated piece is labeled as such**. One bonus — this exercise of "running diverse real data through the ops" turned out to be a **bug detector** in its own right. Five op defects that had never surfaced on synthetic data showed up on real data, and **all five were fixed before publication** (the discovery stories and regression tests are in [docs/KNOWN_ISSUES.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/KNOWN_ISSUES.md)). Behind the pretty exhibits, it doubled as a test — two birds with one stone.

---
