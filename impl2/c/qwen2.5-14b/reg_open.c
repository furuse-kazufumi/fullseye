void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は反復回数を 1〜4 に振る。b は未使用。
    int iterations = (int)(a * 4 + 0.5); // 0.5 で丸める
    if (iterations < 1) iterations = 1; // 最小 1 回

    // 二値オープニングは侵食と膨張の反復
    for (int i = 0; i < iterations; i++) {
        // 侵食
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                // 構造要素は十字形。中心画素は (y*w + x)。
                int sum = 0;
                // 上
                if (y > 0) sum += in[(y - 1) * w + x];
                // 下
                if (y < h - 1) sum += in[(y + 1) * w + x];
                // 左
                if (x > 0) sum += in[y * w + x - 1];
                // 右
                if (x < w - 1) sum += in[y * w + x + 1];
                // 中心画素
                sum += in[y * w + x];
                // 5 個の画素のうち 3 個以上が 1 の場合のみ 1 に
                out[y * w + x] = (sum >= 3) ? 1.0 : 0.0;
            }
        }
        // 膨張
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                // 構造要素は十字形。中心画素は (y*w + x)。
                int sum = 0;
                // 上
                if (y > 0) sum += out[(y - 1) * w + x];
                // 下
                if (y < h - 1) sum += out[(y + 1) * w + x];
                // 左
                if (x > 0) sum += out[y * w + x - 1];
                // 右
                if (x < w - 1) sum += out[y * w + x + 1];
                // 中心画素
                sum += out[y * w + x];
                // 5 個の画素のうち 1 個以上が 1 の場合のみ 1 に
                out[y * w + x] = (sum > 0) ? 1.0 : 0.0;
            }
        }
    }
}
