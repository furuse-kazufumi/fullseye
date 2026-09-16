void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Kirsch コンパスフィルタのマスク
    const int masks[8][3][3] = {
        {{5, -3, -3}, {5, 0, -3}, {5, -3, -3}},
        {{5, 5, -3}, {5, 0, -3}, {-3, -3, -3}},
        {{-3, 5, 5}, {-3, 0, 5}, {-3, -3, -3}},
        {{-3, -3, 5}, {-3, 0, 5}, {5, -3, -3}},
        {{-3, -3, -3}, {5, 0, 5}, {5, 5, -3}},
        {{-3, -3, -3}, {-3, 0, 5}, {5, 5, 5}},
        {{-3, -3, -3}, {-3, 0, -3}, {5, 5, 5}},
        {{-3, -3, -3}, {-3, 0, -3}, {-3, 5, 5}}
    };

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0;
        }
    }

    // Kirsch コンパスフィルタの適用
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            double max_response = -1.0;
            for (int i = 0; i < 8; ++i) {
                double response = 0.0;
                for (int j = -1; j <= 1; ++j) {
                    for (int k = -1; k <= 1; ++k) {
                        response += masks[i][j + 1][k + 1] * in[(y + j) * w + (x + k)];
                    }
                }
                if (response > max_response) {
                    max_response = response;
                }
            }
            out[y * w + x] = max_response / (8.0 * 5.0); // 正規化
        }
    }

    // 画像の端の処理
    // 画像の端については、境界外のピクセルは周囲の既存のピクセル値を用いて埋めます。
    // ここでは、端のピクセルの値を内部のピクセルの値で置き換えることで処理します。
    for (int y = 0; y < h; ++y) {
        out[y * w] = out[y * w + 1];
        out[y * w + w - 1] = out[y * w + w - 2];
    }
    for (int x = 0; x < w; ++x) {
        out[x] = out[w + x];
        out[h * w - w + x] = out[h * w - w - 1 + x];
    }
}
