void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定義されたしきい値
    double low_threshold = 0.2 + 0.3 * a;
    double high_threshold = 0.5 + 0.3 * b;

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double pixel_value = in[y * w + x];

            // しきい値を超えるかどうかを判定
            if (pixel_value >= high_threshold) {
                out[y * w + x] = 1.0; // 高いしきい値を超える場合
            } else if (pixel_value >= low_threshold) {
                // 低いしきい値を超える場合、近傍の画素を確認して決定
                // 近傍の画素は上下左右の4方向を確認
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dy == 0 && dx == 0) continue; // 自身を除く
                        int ny = y + dy;
                        int nx = x + dx;
                        // 画像の境界外を避ける
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            double neighbor_value = out[ny * w + nx];
                            if (neighbor_value == 1.0) {
                                out[y * w + x] = 1.0;
                                break;
                            }
                        }
                    }
                    if (out[y * w + x] == 1.0) break; // 1つでも近傍が1.0なら終了
                }
            } else {
                out[y * w + x] = 0.0; // 両方のしきい値を下回る場合
            }
        }
    }
}
