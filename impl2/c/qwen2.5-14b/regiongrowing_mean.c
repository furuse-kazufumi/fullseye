void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double threshold = a; // しきい値
    const int iterations = (int)(b * 10); // 膨張の反復回数 (0.1 から 1.0 までを 10 にスケーリング)

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0; // 初期値は 0.0
        }
    }

    // シードの生成
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double pixel_value = in[y * w + x];
            if (pixel_value > threshold) {
                out[y * w + x] = 1.0; // シードとしてマーク
            }
        }
    }

    // 膨張処理
    for (int i = 0; i < iterations; i++) {
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                if (out[y * w + x] == 1.0) {
                    // 4近傍のチェック
                    if (out[(y - 1) * w + x] == 0.0) out[(y - 1) * w + x] = 1.0;
                    if (out[(y + 1) * w + x] == 0.0) out[(y + 1) * w + x] = 1.0;
                    if (out[y * w + x - 1] == 0.0) out[y * w + x - 1] = 1.0;
                    if (out[y * w + x + 1] == 0.0) out[y * w + x + 1] = 1.0;
                }
            }
        }
    }
}
