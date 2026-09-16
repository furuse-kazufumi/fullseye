void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの決定
    int window_size = (int)(a * 9) + 3; // a が 0.1 のとき 3, 0.5 のとき 7, 0.9 のとき 11 となる
    int half_window = window_size / 2;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 画像の各ピクセルに対してフィルタを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x]; // 初期値は現在のピクセルの値

            // 窓内の各ピクセルに対して最小値を計算
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 窓が画像の外に出た場合、端のピクセル値で埋める
                    if (ny < 0) ny = 0;
                    if (nx < 0) nx = 0;
                    if (ny >= h) ny = h - 1;
                    if (nx >= w) nx = w - 1;

                    // 最小値を更新
                    if (in[ny * w + nx] < min_val) {
                        min_val = in[ny * w + nx];
                    }
                }
            }

            // 最小値を出力画像に設定
            out[y * w + x] = min_val;
        }
    }
}
