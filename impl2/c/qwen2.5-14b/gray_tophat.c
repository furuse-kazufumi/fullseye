void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 矩形構造要素のサイズを計算
    int kernel_size = (int)(a * 8 + 1); // 0.1 -> 3, 0.5 -> 5, 0.9 -> 9
    if (kernel_size % 2 == 0) {
        kernel_size++; // 奇数に丸める
    }
    int half_kernel = (kernel_size - 1) / 2;

    // オープニング処理
    double* opening = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x];
            for (int ky = -half_kernel; ky <= half_kernel; ky++) {
                for (int kx = -half_kernel; kx <= half_kernel; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        min_val = fmin(min_val, in[ny * w + nx]);
                    }
                }
            }
            opening[y * w + x] = min_val;
        }
    }

    // ホワイトトップハット変換
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x] - opening[y * w + x];
        }
    }

    // 正規化
    double max_val = 0.0;
    for (int i = 0; i < h * w; i++) {
        max_val = fmax(max_val, out[i]);
    }
    if (max_val > 0.0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_val;
        }
    }

    free(opening);
}
