void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 使用するカーネル。PIL.ImageFilter.EDGE_ENHANCE_MORE の固定カーネルを基に。
    const double kernel[9] = {
        -1, -1, -1,
        -1,  8, -1,
        -1, -1, -1
    };

    // 出力画像の各ピクセルに対してカーネルを適用
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
            // 結果を出力画像に格納
            out[y * w + x] = sum;
        }
    }

    // 画像の端のピクセルは、境界外のピクセルを無視して、内部のピクセルのみを使用して計算する。
    // これは、仕様書で明示的に指定されていないため、この実装では内部ピクセルのみを使用する。
    // 画像の端のピクセルは、内部のピクセルと同じ値を保持する。
    for (int y = 0; y < h; y++) {
        out[y * w] = in[y * w];
        out[y * w + w - 1] = in[y * w + w - 1];
    }
    for (int x = 0; x < w; x++) {
        out[x] = in[x];
        out[(h - 1) * w + x] = in[(h - 1) * w + x];
    }
}
