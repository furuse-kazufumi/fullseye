void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。この関数では無視する。

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0;
        }
    }

    // 入力画像の各画素を処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像の画素が 1.0 の場合のみ処理を行う
            if (in[y * w + x] == 1.0) {
                // 画素の周囲の 8 方向をチェック
                for (int dy = -1; dy <= 1; ++dy) {
                    for (int dx = -1; dx <= 1; ++dx) {
                        // 周囲の画素が画像の範囲内にあるかチェック
                        if (y + dy >= 0 && y + dy < h && x + dx >= 0 && x + dx < w) {
                            // 周囲の画素が 0.0 の場合、現在の画素は境界画素である
                            if (in[(y + dy) * w + (x + dx)] == 0.0) {
                                out[y * w + x] = 1.0;
                                break;
                            }
                        }
                    }
                    if (out[y * w + x] == 1.0) {
                        break;
                    }
                }
            }
        }
    }
}
