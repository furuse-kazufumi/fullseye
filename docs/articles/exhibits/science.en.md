[![Rainbow ripples of the distance transform](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_distance_ripple_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_distance_ripple.png)

*↑ **Rainbow ripples of the distance transform** — split a coin photo into black and white, then paint "how many pixels from the edge?" in rainbow colors, and ripple-like contour lines emerge. Ops used: `otsu`, `fill_up`, `distance_transform`.*

[![The Fourier world](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_fourier_stars_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_fourier_stars.png)

*↑ **The Fourier world** — view an image in frequency space, and "what fineness of pattern, in what direction" becomes points of light. A regular weave glows like a constellation (the weave panel only is synthetic). Op used: `fft_image`.*

[![Watershed — coloring-book segmentation of coins](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam.png)

*↑ **Watershed's coloring-book segmentation** — mimic water flowing downhill and pooling, and each coin gets its own color. Ops used: `otsu`, `distance_transform`, `watersheds`, `colorize_labels`.*

[![The edge compass](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_edge_compass_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_edge_compass.png)

*↑ **The edge compass** — paint contour direction with the colors of a hue wheel, and lines pointing the same way glow the same color. Ops used: `sobel_amp`, `sobel_dir`.*

[![Six universes born from simple rules](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_alife_worlds_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_alife_worlds.png)

*↑ **Six universes born from simple rules** — from nothing more than "look at your neighbors and decide your own color" come fractals, chaos, sandpile mandalas, dendrites, and coral patterns (simulation imagery). Ops used: `alife_wolfram1d`, `alife_sandpile`, `alife_dla`, `alife_lenia`, `alife_cyclic_ca`.*

[![An X-ray photograph of a Triceratops](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_xray_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_xray.png)

*↑ **An X-ray photograph of a Triceratops** — pack the Smithsonian's real skeleton scan (CC0) into voxels and take a maximum-intensity projection (MIP), and it comes out looking just like an X-ray. Ribs and horns both show. Ops used: `voxelize`, `vol_gaussian`, `vol_mip`.*

[![A dragon that pops out with red-blue glasses](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dragon_anaglyph_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dragon_anaglyph.png)

*↑ **A dragon that pops out with red-blue glasses** — the real Stanford dragon scan rendered from 2 viewpoints and overlaid in red-cyan as an anaglyph. Put on red-blue glasses and it floats. Ops used: `read_mesh`, `look_at`, `render_mesh`.*

[![The Triceratops mountain range](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_terrain_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_terrain.png)

*↑ **The Triceratops mountain range** — turn the skeleton into a 600,000-point cloud and build an elevation map from directly above, and the spine becomes a mountain range, the ribs its ridgelines. The same ops a robot uses to read terrain. Ops used: `sample_surface`, `elevation_map`, `colorize_height`.*

![Shapes growing and shrinking (morphology)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_morph_pulse.gif)

*↑ **Shapes growing and shrinking** — coins puff up and merge under dilation, then slim down under erosion. Fundamental ops used in factory image inspection too. Ops used: `dilation_circle`, `erosion_circle`.*

[![Space gone wobbly — three deformation algorithms](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_wobble_warp_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_wobble_warp.png)

*↑ **Space gone wobbly** — imagine an invisible rubber sheet under the image, then pinch and pull it in three different styles: TPS / FFD / MLS. Ops used: `deform_tps`, `deform_ffd`, `deform_mls`.*

[![Extracting a skeleton from a dinosaur silhouette](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_skeleton_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_skeleton.png)

*↑ **Extracting a skeleton from a dinosaur silhouette** — the centerline (skeleton) of a Triceratops skeleton's shadow, extracted at 1-pixel width. Legs, horns, and tail remain like wirework. Ops used: `sk_skeleton`, `distance_transform`, and others.*
