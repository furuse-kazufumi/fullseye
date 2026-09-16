void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = (int)(a * (w < h ? w : h));
    window_size = window_size % 2 == 0 ? window_size + 1 : window_size; // 奇数に丸める

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 局所極小点の検出
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x];
            int min_x = x;
            int min_y = y;

            // 窓内の最小値を求める
            for (int dy = -window_size / 2; dy <= window_size / 2; dy++) {
                for (int dx = -window_size / 2; dx <= window_size / 2; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 窓内の画素を処理
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] < min_val) {
                            min_val = in[ny * w + nx];
                            min_x = nx;
                            min_y = ny;
                        }
                    }
                }
            }

            // 局所極小点の判定
            if (min_x == x && min_y == y && in[y * w + x] < 0.7 - 0.4 * b) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
