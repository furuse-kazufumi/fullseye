void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 円形構造要素の半径を計算
    int radius = (int)(a * 4); // 0.1 から 0.9 までで 1 から 4 までの半径を生成
    if (radius < 1) radius = 1; // 最小半径は 1

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // グレースケール収縮を適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x]; // 初期値として現在のピクセルの値を設定
            // 円形構造要素内のすべてのピクセルについて最小値を計算
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // ピクセルが画像の範囲内にあるかチェック
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        // ピクセルが円形構造要素内にあるかチェック
                        if (dx * dx + dy * dy <= radius * radius) {
                            min_val = fmin(min_val, in[ny * w + nx]);
                        }
                    }
                }
            }
            // 最小値を出力画像に設定
            out[y * w + x] = min_val;
        }
    }
}
