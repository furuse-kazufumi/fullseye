void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓のサイズを決定。a が 0.25 と 0.49 の間で切り替わると想定。
    int window_size = (a < 0.25) ? 3 : (a < 0.49) ? 5 : 7;

    // 窓の半径
    int radius = window_size / 2;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // グレースケールオープニングの実装
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x];
            double max_val = in[y * w + x];

            // 窓内の最小値と最大値を計算
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 画像の境界外を無視
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double val = in[ny * w + nx];
                        if (val < min_val) {
                            min_val = val;
                        }
                        if (val > max_val) {
                            max_val = val;
                        }
                    }
                }
            }

            // 收縮と膨張の順序で処理
            out[y * w + x] = max_val;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        out[ny * w + nx] = fmax(out[ny * w + nx], min_val);
                    }
                }
            }
        }
    }
}
