void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ヒットオアミス変換のカーネル
    const int kernel[3][3] = {
        {0, 1, 0},
        {1, -1, 1},
        {0, 1, 0}
    };

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // ヒットオアミス変換の適用
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double sum = 0.0;
            for (int ky = 0; ky < 3; ky++) {
                for (int kx = 0; kx < 3; kx++) {
                    int ny = y + ky - 1;
                    int nx = x + kx - 1;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += kernel[ky][kx] * in[ny * w + nx];
                    }
                }
            }
            // カーネルの合計が 0 であれば、出力画像の該当位置を 1 に設定
            if (sum == 0.0) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
