void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素の半径を計算
    int radius = (int)(a * 3.5 + 0.5); // 0.1 -> 1, 0.5 -> 2, 0.9 -> 4
    if (radius < 1) radius = 1; // 最小半径は 1

    // クロージング処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double max_val = in[y * w + x]; // 初期値は元のピクセル値
            // 円盤形構造要素の範囲内にあるピクセルについて最大値を計算
            for (int dy = -radius; dy <= radius; ++dy) {
                for (int dx = -radius; dx <= radius; ++dx) {
                    int dist = dx * dx + dy * dy;
                    if (dist <= radius * radius) { // 円盤内
                        int nx = x + dx, ny = y + dy;
                        if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                            double val = in[ny * w + nx];
                            if (val > max_val) max_val = val;
                        }
                    }
                }
            }
            out[y * w + x] = max_val; // 最大値を出力に設定
        }
    }
}
