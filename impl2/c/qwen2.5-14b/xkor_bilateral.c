void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 空間方向のシグマを計算
    double sigma_s = 1.0 + 3.0 * a;
    // 明度方向のシグマを計算
    double sigma_r = 0.05 + 0.4 * b;

    // バイラテラルフィルタの適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            double weight_sum = 0.0;
            for (int ky = -2; ky <= 2; ++ky) {
                for (int kx = -2; kx <= 2; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 端の処理: BORDER_REFLECT_101 モード
                    if (ny < 0) ny = -ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    double diff = in[ny * w + nx] - in[y * w + x];
                    double g_s = exp(-(kx * kx + ky * ky) / (2.0 * sigma_s * sigma_s));
                    double g_r = exp(-(diff * diff) / (2.0 * sigma_r * sigma_r));
                    double weight = g_s * g_r;
                    sum += in[ny * w + nx] * weight;
                    weight_sum += weight;
                }
            }
            out[y * w + x] = sum / weight_sum;
        }
    }
}
