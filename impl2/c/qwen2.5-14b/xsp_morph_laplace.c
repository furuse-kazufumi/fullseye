void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを計算
    int size = 3 + 2 * (int)(a * 3);
    // 構造要素の半径
    int radius = size / 2;

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0;
        }
    }

    // 形態学的ラプラシアンの計算
    for (int y = radius; y < h - radius; ++y) {
        for (int x = radius; x < w - radius; ++x) {
            double sum = 0.0;
            for (int dy = -radius; dy <= radius; ++dy) {
                for (int dx = -radius; dx <= radius; ++dx) {
                    sum += in[(y + dy) * w + (x + dx)];
                }
            }
            double center = in[y * w + x];
            out[y * w + x] = center - sum / ((2 * radius + 1) * (2 * radius + 1));
        }
    }

    // 画像の端の処理
    // ここでは、端のピクセルは 0 に設定する。
    // これは、端のピクセルの値が不明確であるため、安全な初期値として 0 を選択する。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (y < radius || y >= h - radius || x < radius || x >= w - radius) {
                out[y * w + x] = 0.0;
            }
        }
    }
}
