void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用。パラメータを無視する。

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 領域の境界を計算
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            // 8-近傍の画素を確認
            int sum = 0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    if (in[(y + dy) * w + (x + dx)] == 1.0) {
                        sum++;
                    }
                }
            }

            // 8-近傍のうち、領域の画素が 1 つ以上存在し、かつその画素が 2 つ以下である場合、境界画素とみなす
            if (sum > 0 && sum <= 2) {
                out[y * w + x] = 1.0;
            }
        }
    }

    // 画像の端の境界を計算
    // 画像の端の境界は、端の画素が領域に属する場合、その画素自体が境界とみなす。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) {
                // 8-近傍のうち、領域の画素が 1 つ以上存在しない場合、境界画素とみなす
                int sum = 0;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            if (in[ny * w + nx] == 1.0) {
                                sum++;
                            }
                        }
                    }
                }
                if (sum == 0) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }
}
