void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓のサイズを決定
    int window_size = 3; // 初期値
    if (a >= 0.75) {
        window_size = 9;
    } else if (a >= 0.49) {
        window_size = 7;
    } else if (a >= 0.25) {
        window_size = 5;
    }

    // 窓の半径
    int radius = window_size / 2;

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 画像の各ピクセルに対して処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x]; // 初期値として現在のピクセル値を設定

            // 窓内の各ピクセルに対して処理
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 窓が画像外に位置する場合、現在のピクセル値を保持
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        min_val = fmin(min_val, in[ny * w + nx]);
                    }
                }
            }

            // 窓内の最小値を出力画像に設定
            out[y * w + x] = min_val;
        }
    }
}
