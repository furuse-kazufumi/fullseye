void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓のサイズを決定
    int window_size = (a < 0.25) ? 3 : (a < 0.49) ? 5 : (a < 0.75) ? 7 : 9;
    int half_window = window_size / 2;

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 窓を滑らせる
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = in[y * w + x];
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の外側のピクセルは無視
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        max_val = (in[ny * w + nx] > max_val) ? in[ny * w + nx] : max_val;
                    }
                }
            }
            out[y * w + x] = max_val;
        }
    }
}
