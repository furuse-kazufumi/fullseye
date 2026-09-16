void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素サイズを決定
    int kernel_size = (a < 0.25) ? 3 : (a < 0.49) ? 5 : (a < 0.75) ? 7 : 9;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 膨張処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = in[y * w + x];
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
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
