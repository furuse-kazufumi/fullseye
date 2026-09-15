void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端をどう処理するか: 画像の端の画素は境界線に含まれない。
    // つまり、端の画素が 1.0 であっても、それが境界線に含まれるためには隣接する 0.0 が必要だが、
    // 端の画素には隣接する 0.0 がないため、端の画素は境界線にならない。

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            if (in[index] == 1.0) {
                // Check if this pixel is a boundary pixel
                if ((x > 0 && in[index - 1] == 0.0) ||  // left
                    (x < w - 1 && in[index + 1] == 0.0) ||  // right
                    (y > 0 && in[index - w] == 0.0) ||  // top
                    (y < h - 1 && in[index + w] == 0.0)) {  // bottom
                    out[index] = 1.0;
                } else {
                    out[index] = 0.0;
                }
            } else {
                out[index] = 0.0;
            }
        }
    }
}
