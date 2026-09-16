void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int r = 1 + (int)round(a * 2);
    int window_size = 2 * r + 1;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 各ピクセルの値を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double pixel_value = in[y * w + x];
            int count = 0;

            // 窓内の各ピクセルに対して
            for (int dy = -r; dy <= r; dy++) {
                for (int dx = -r; dx <= r; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 端の扱い: 端画素を重複させずに折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    double neighbor_value = in[ny * w + nx];
                    if (pixel_value > neighbor_value) {
                        count++;
                    }
                }
            }

            // ランクを計算
            out[y * w + x] = (double)count / (window_size * window_size);
        }
    }
}
