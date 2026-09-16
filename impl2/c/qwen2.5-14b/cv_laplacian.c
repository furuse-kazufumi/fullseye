void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用パラメータであるため、無視する。
    (void)a;
    (void)b;

    // ラプラシアンフィルタのカーネル
    const double kernel[9] = {
        0.0, 1.0, 0.0,
        1.0,-4.0, 1.0,
        0.0, 1.0, 0.0
    };

    // 出力画像の最大値を初期化
    double max_out = 0.0;

    // 出力画像の各画素を計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int iy = y + ky;
                    int ix = x + kx;
                    // 端の画素を BORDER_REFLECT_101 モードで処理
                    if (iy < 0) iy = -iy - 1;
                    if (iy >= h) iy = 2 * h - iy - 2;
                    if (ix < 0) ix = -ix - 1;
                    if (ix >= w) ix = 2 * w - ix - 2;
                    sum += in[iy * w + ix] * kernel[(ky + 1) * 3 + (kx + 1)];
                }
            }
            out[y * w + x] = sum;
            // 出力画像の最大値を更新
            if (sum > max_out) max_out = sum;
        }
    }

    // 出力画像を最大値で正規化
    if (max_out > 0.0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] /= max_out;
        }
    }
}
