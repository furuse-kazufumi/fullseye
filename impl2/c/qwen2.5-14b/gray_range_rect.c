void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓のサイズを計算
    int window_size = (int)(a * 9) + 3; // a が 0.1 から 0.9 の範囲で、窓サイズが 3 から 9 の範囲に変化する
    int half_window = window_size / 2;

    // 出力画像の各ピクセルに対して処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = 1.0;
            double max_val = 0.0;

            // 窓内のピクセルの最小値と最大値を計算
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int nx = x + dx;
                    int ny = y + dy;

                    // 窓が画像の外に出た場合、そのピクセルは無視する
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        double val = in[ny * w + nx];
                        if (val < min_val) min_val = val;
                        if (val > max_val) max_val = val;
                    }
                }
            }

            // 局所的なレンジを正規化して出力
            if (max_val - min_val > 0) {
                out[y * w + x] = (in[y * w + x] - min_val) / (max_val - min_val);
            } else {
                out[y * w + x] = 0.0; // レンジが 0 の場合、出力は 0
            }
        }
    }
}
