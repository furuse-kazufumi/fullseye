void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素の半径を計算
    int radius = (int)(a * 3 + 0.5); // a は [0, 1] の範囲で、半径は 1〜4 の範囲に変換
    if (radius < 1) radius = 1;
    if (radius > 4) radius = 4;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // グレースケールオープニングの実装
    // ここでは、収縮と膨張を順に適用します。
    // 収縮: 入力画像から最小値を抽出
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x];
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        min_val = fmin(min_val, in[ny * w + nx]);
                    }
                }
            }
            out[y * w + x] = min_val;
        }
    }

    // 膨張: 出力画像から最大値を抽出
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = out[y * w + x];
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        max_val = fmax(max_val, out[ny * w + nx]);
                    }
                }
            }
            out[y * w + x] = max_val;
        }
    }
}
