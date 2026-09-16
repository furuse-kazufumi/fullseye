void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 大津の二値化法を適用するためのヒストグラムの初期化
    int histogram[256] = {0};
    int total_pixels = h * w;
    int threshold;

    // ヒストグラムを作成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel_value = (int)(in[y * w + x] * 255.0);
            histogram[pixel_value]++;
        }
    }

    // 大津の二値化法を適用
    int max_variance = 0;
    for (int t = 0; t < 256; t++) {
        int w1 = 0, w2 = 0;
        int m1 = 0, m2 = 0;
        for (int i = 0; i < 256; i++) {
            if (i <= t) {
                w1 += histogram[i];
                m1 += i * histogram[i];
            } else {
                w2 += histogram[i];
                m2 += i * histogram[i];
            }
        }
        if (w1 == 0 || w2 == 0) continue;
        m1 /= w1;
        m2 /= w2;
        int variance = w1 * w2 * (m1 - m2) * (m1 - m2);
        if (variance > max_variance) {
            max_variance = variance;
            threshold = t;
        }
    }

    // 二値化処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel_value = (int)(in[y * w + x] * 255.0);
            out[y * w + x] = (pixel_value > threshold) ? 1.0 : 0.0;
        }
    }
}
