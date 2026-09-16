void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の全ピクセル数
    int num_pixels = h * w;

    // ヒストグラムの最大値
    int hist_max = 256;
    int hist[hist_max] = {0};

    // ヒストグラムを作成
    for (int i = 0; i < num_pixels; i++) {
        int pixel_value = (int)(in[i] * 255.0);
        hist[pixel_value]++;
    }

    // 最適なしきい値を計算
    int optimal_threshold = 0;
    double max_variance = 0.0;
    for (int t = 0; t < hist_max; t++) {
        double w0 = 0.0, w1 = 0.0, m0 = 0.0, m1 = 0.0;
        for (int i = 0; i < t; i++) {
            w0 += hist[i];
            m0 += i * hist[i];
        }
        for (int i = t; i < hist_max; i++) {
            w1 += hist[i];
            m1 += i * hist[i];
        }
        if (w0 > 0 && w1 > 0) {
            double variance = w0 * w1 * ((m0 / w0) - (m1 / w1)) * ((m0 / w0) - (m1 / w1));
            if (variance > max_variance) {
                max_variance = variance;
                optimal_threshold = t;
            }
        }
    }

    // しきい値を適用して出力画像を作成
    for (int i = 0; i < num_pixels; i++) {
        out[i] = (in[i] * 255.0) > optimal_threshold ? 1.0 : 0.0;
    }
}
