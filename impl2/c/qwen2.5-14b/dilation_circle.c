void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 半径の計算
    int radius = (int)(a * 4); // 半径は 0 から 4 の範囲
    if (radius < 0) radius = 0;
    if (radius > 4) radius = 4;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 円形構造要素のマスク作成
    int mask[9] = {0}; // 3x3 マスクを使用
    for (int y = -radius; y <= radius; y++) {
        for (int x = -radius; x <= radius; x++) {
            if (x * x + y * y <= radius * radius) {
                mask[(y + radius) * 3 + (x + radius)] = 1;
            }
        }
    }

    // 二値膨張処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) { // 入力画像の画素が 1 である場合
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        if (mask[(dy + radius) * 3 + (dx + radius)] == 1) {
                            int ny = y + dy;
                            int nx = x + dx;
                            if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                                out[ny * w + nx] = 1.0;
                            }
                        }
                    }
                }
            }
        }
    }
}
