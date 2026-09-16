void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 局所的な最大値の検出
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double center = in[y * w + x];
            double max_neighbor = 0.0;

            // 8近傍の最大値を求める
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    if (dx == 0 && dy == 0) continue; // 中心画素はスキップ
                    double neighbor = in[(y + dy) * w + (x + dx)];
                    if (neighbor > max_neighbor) {
                        max_neighbor = neighbor;
                    }
                }
            }

            // 中心画素が近傍の最大値である場合、出力画像に1を設定
            if (center >= max_neighbor) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
