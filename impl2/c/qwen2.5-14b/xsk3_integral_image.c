void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 積分画像の計算
    // 画像の外側は背景（0）とみなす
    // 出力は最大値で正規化される

    // 積分画像の初期化
    double integral[h][w];
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            integral[y][x] = 0.0;
        }
    }

    // 積分画像の計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            integral[y][x] = in[y * w + x];
            if (x > 0) {
                integral[y][x] += integral[y][x - 1];
            }
            if (y > 0) {
                integral[y][x] += integral[y - 1][x];
            }
            if (x > 0 && y > 0) {
                integral[y][x] -= integral[y - 1][x - 1];
            }
        }
    }

    // 最大値の計算
    double max_value = 0.0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (integral[y][x] > max_value) {
                max_value = integral[y][x];
            }
        }
    }

    // 正規化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = integral[y][x] / max_value;
        }
    }
}
