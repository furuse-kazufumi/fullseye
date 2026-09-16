void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ラプラシアンフィルタのカーネル
    const double laplace_kernel[3][3] = {
        {0, -1, 0},
        {-1, 4, -1},
        {0, -1, 0}
    };

    // 出力画像の最大値を初期化
    double max_out = 0.0;

    // 出力画像の各ピクセルに対してラプラシアンフィルタを適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 端のピクセルの処理
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                        ny = y; // 端のピクセルは同じピクセルとみなす
                        nx = x;
                    }
                    sum += laplace_kernel[ky + 1][kx + 1] * in[ny * w + nx];
                }
            }
            out[y * w + x] = fabs(sum);
            if (out[y * w + x] > max_out) {
                max_out = out[y * w + x];
            }
        }
    }

    // 出力画像を最大値で正規化
    for (int i = 0; i < h * w; ++i) {
        out[i] /= max_out;
    }
}
