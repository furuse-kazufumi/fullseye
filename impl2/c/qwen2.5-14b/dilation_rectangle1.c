void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は正方形の半径を表す。0.1 から 0.9 の範囲で、3, 5, 7, 9 のいずれかに丸められる。
    int radius = (int)(a * 4 + 0.5); // 0.1 -> 3, 0.5 -> 5, 0.9 -> 9
    if (radius < 3) radius = 3; // 最小半径は 3
    if (radius > 9) radius = 9; // 最大半径は 9

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 二値膨張処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) {
                // 正方形構造要素の範囲内にある画素を 1 に設定
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        // 画像の境界外を無視
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            out[ny * w + nx] = 1.0;
                        }
                    }
                }
            }
        }
    }
}
