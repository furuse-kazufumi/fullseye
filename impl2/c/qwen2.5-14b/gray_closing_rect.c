void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの決定
    int window_size = 3; // 初期値
    if (a < 0.25) {
        window_size = 3;
    } else if (a < 0.49) {
        window_size = 5;
    } else if (a < 0.75) {
        window_size = 7;
    } else {
        window_size = 9;
    }

    // 窓サイズが奇数であることを確認
    if (window_size % 2 == 0) {
        window_size++; // 偶数の場合は奇数に調整
    }

    // 窓の半径
    int radius = (window_size - 1) / 2;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // クロージングの実行
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = -1.0;
            double min_val = 2.0; // 値域は [0,1] なので、2.0 は最大値を表す

            // 窓内の最大値と最小値の計算
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double val = in[ny * w + nx];
                        if (val > max_val) {
                            max_val = val;
                        }
                        if (val < min_val) {
                            min_val = val;
                        }
                    }
                }
            }

            // 膨張と収縮の適用
            out[y * w + x] = max_val;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double val = out[ny * w + nx];
                        if (val < min_val) {
                            out[y * w + x] = min_val;
                        }
                    }
                }
            }
        }
    }
}
