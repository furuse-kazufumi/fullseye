void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が [0, 1] の範囲内で格子間隔を決定する。範囲外の値は 0.5 にクリッピングする。
    if (a < 0.0) a = 0.0;
    if (a > 1.0) a = 1.0;

    // 格子間隔を計算する。min(h, w) の 5% から 25% の範囲で線形補間する。
    int min_dim = (h < w) ? h : w;
    int grid_interval = (int)(0.05 * min_dim + 0.2 * min_dim * a);

    // 出力領域を初期化する。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 格子線を描画する。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (x % grid_interval == 0 || y % grid_interval == 0) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
