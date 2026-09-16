void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // σ_s = 1.0 + 3.0a, σ_r = 0.05 + 0.4b
    double sigma_s = 1.0 + 3.0 * a;
    double sigma_r = 0.05 + 0.4 * b;

    // 近傍窓の半径は固定で r=2 (5x5)
    int radius = 2;
    int window_size = (2 * radius + 1) * (2 * radius + 1);

    // 端の画素を最近傍の画素値で埋める
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            double weight_sum = 0.0;

            for (int dy = -radius; dy <= radius; ++dy) {
                for (int dx = -radius; dx <= radius; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 画像の端を処理
                    if (ny < 0) ny = 0;
                    if (ny >= h) ny = h - 1;
                    if (nx < 0) nx = 0;
                    if (nx >= w) nx = w - 1;

                    double weight = exp(-((dy * dy + dx * dx) / (2 * sigma_s * sigma_s))) *
                                    exp(-((in[y * w + x] - in[ny * w + nx]) * (in[y * w + x] - in[ny * w + nx])) / (2 * sigma_r * sigma_r));
                    sum += in[ny * w + nx] * weight;
                    weight_sum += weight;
                }
            }

            // 重みの合計が 0 の場合、元の画素値を出力
            if (weight_sum == 0.0) {
                out[y * w + x] = in[y * w + x];
            } else {
                out[y * w + x] = sum / weight_sum;
            }
        }
    }
}
