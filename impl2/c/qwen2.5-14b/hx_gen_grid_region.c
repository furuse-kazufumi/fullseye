void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は格子間隔を決める。b は未使用。
    // a の値域は [0,1]。0.05 から 0.25 の間で格子間隔を決定する。
    double grid_spacing = h * w > 1 ? (0.05 + a * 0.2) : 1.0;
    int grid_size = (int)(MIN(h, w) * grid_spacing);

    // 出力画像を初期化。すべての画素を背景 (0.0) に設定。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 行・列インデックスが grid_size の倍数の画素を前景 (1.0) に設定。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if ((y % grid_size == 0) || (x % grid_size == 0)) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
