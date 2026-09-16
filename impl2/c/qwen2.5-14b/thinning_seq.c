void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の外側は背景(0)とみなす。
    // これは仕様書で明示的に指定されている。

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // Guo-Hall 細線化アルゴリズムの適用
    int changed;
    do {
        changed = 0;
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                // 8近傍の画素を取得
                double N = in[(y - 1) * w + x];
                double NE = in[(y - 1) * w + x + 1];
                double E = in[y * w + x + 1];
                double SE = in[(y + 1) * w + x + 1];
                double S = in[(y + 1) * w + x];
                double SW = in[(y + 1) * w + x - 1];
                double W = in[y * w + x - 1];
                double NW = in[(y - 1) * w + x - 1];

                // Guo-Hall の条件をチェック
                if (N + NE + E + SE + S + SW + W + NW == 2) {
                    int n = (N + NE + E + SE + S + SW + W + NW) / 2;
                    int p = (N + NE + E + SE + S + SW + W + NW) / 2;
                    if (n == 1 && p == 1) {
                        int A1 = (N && !NE) + (NE && !E) + (E && !SE) + (SE && !S) + (S && !SW) + (SW && !W) + (W && !NW) + (NW && !N);
                        int A2 = (N && !NW) + (NW && !W) + (W && !SW) + (SW && !S) + (S && !SE) + (SE && !E) + (E && !NE) + (NE && !N);
                        if (A1 == 1 && A2 == 1) {
                            int B1 = (N && !S) + (NE && !SW) + (E && !W) + (SE && !NW);
                            int B2 = (N && !NE) + (NE && !E) + (E && !SE) + (SE && !S) + (S && !SW) + (SW && !W) + (W && !NW) + (NW && !N);
                            if (B1 == 1 && B2 == 1) {
                                out[y * w + x] = 0.0;
                                changed = 1;
                            }
                        }
                    }
                }
            }
        }
    } while (changed);

    // 出力画像をコピー
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            if (in[y * w + x] == 1.0) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
