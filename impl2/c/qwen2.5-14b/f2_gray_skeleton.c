void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を背景(0)とみなす。
    // つまみ b は無視する。

    // スキレットの生成
    int kernel[3][3] = {
        {0, 1, 0},
        {1, -4, 1},
        {0, 1, 0}
    };

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // スキレット適用
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double sum = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    sum += kernel[ky + 1][kx + 1] * in[(y + ky) * w + (x + kx)];
                }
            }
            double value = sum / 4.0; // データ範囲を [0,1] に保つためのスケーリング
            if (value > a) {
                out[y * w + x] = value;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
