void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを決定
    int kernel_size = 3; // 初期値
    if (a >= 0.75) {
        kernel_size = 9;
    } else if (a >= 0.49) {
        kernel_size = 7;
    } else if (a >= 0.25) {
        kernel_size = 5;
    } else {
        kernel_size = 3;
    }

    // 窓の半径
    int radius = kernel_size / 2;

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 最大値フィルタリング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = in[y * w + x];
            for (int ky = -radius; ky <= radius; ky++) {
                for (int kx = -radius; kx <= radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 画像の境界外を無視
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        max_val = (in[ny * w + nx] > max_val) ? in[ny * w + nx] : max_val;
                    }
                }
            }
            out[y * w + x] = max_val;
        }
    }
}
