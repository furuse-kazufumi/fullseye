void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 円形構造要素の半径を計算
    int radius = (int)(1 + (a < 0.33 ? 0 : a < 0.67 ? 1 : 2)); // a による段階的な半径変更

    // 出力画像を初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // グレースケール膨張処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double max_val = in[y * w + x];
            for (int dy = -radius; dy <= radius; ++dy) {
                for (int dx = -radius; dx <= radius; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の境界外を無視
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double val = in[ny * w + nx];
                        if (val > max_val) {
                            max_val = val;
                        }
                    }
                }
            }
            out[y * w + x] = max_val;
        }
    }
}
