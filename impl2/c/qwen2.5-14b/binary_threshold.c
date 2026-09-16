void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の全ピクセル数
    int num_pixels = h * w;

    // ヒストグラムの最大値
    int hist_max = 256;
    int hist[hist_max] = {0};

    // ヒストグラムを作成
    for (int i = 0; i < num_pixels; i++) {
        int value = (int)(in[i] * hist_max);
        hist[value]++;
    }

    // 最適なしきい値を計算
    int optimal_threshold = 0;
    int max_variance = 0;
    for (int t = 0; t < hist_max; t++) {
        int w1 = 0, w2 = 0;
        int m1 = 0, m2 = 0;
        for (int i = 0; i < hist_max; i++) {
            if (i < t) {
                w1 += hist[i];
                m1 += i * hist[i];
            } else {
                w2 += hist[i];
                m2 += i * hist[i];
            }
        }
        if (w1 == 0 || w2 == 0) continue;
        m1 /= w1;
        m2 /= w2;
        int variance = w1 * w2 * (m1 - m2) * (m1 - m2);
        if (variance > max_variance) {
            max_variance = variance;
            optimal_threshold = t;
        }
    }

    // 二値化処理
    for (int i = 0; i < num_pixels; i++) {
        int value = (int)(in[i] * hist_max);
        out[i] = (value >= optimal_threshold) ? 1.0 : 0.0;
    }
}
