void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ラプラシアンフィルタのカーネル
    const double kernel[9] = {
        0.0, -1.0, 0.0,
        -1.0, 4.0, -1.0,
        0.0, -1.0, 0.0
    };

    // 出力画像の各ピクセルに対してラプラシアンフィルタを適用
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double sum = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int in_index = (y + ky) * w + (x + kx);
                    int kernel_index = (ky + 1) * 3 + (kx + 1);
                    sum += in[in_index] * kernel[kernel_index];
                }
            }
            out[y * w + x] = sum;
        }
    }

    // 画像の端のピクセルは、端のピクセルの値をそのまま出力する。
    // これは、端のピクセルに対してラプラシアンフィルタを適用するための
    // 代替的な方法であり、境界外のピクセルへのアクセスを避ける。
    for (int y = 0; y < h; y++) {
        out[y * w] = in[y * w];
        out[y * w + w - 1] = in[y * w + w - 1];
    }
    for (int x = 0; x < w; x++) {
        out[x] = in[x];
        out[(h - 1) * w + x] = in[(h - 1) * w + x];
    }
}
