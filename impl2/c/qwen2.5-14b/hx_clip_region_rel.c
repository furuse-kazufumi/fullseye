void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a 以外のパラメータは無視
    if (a < 0.0 || a > 1.0) {
        a = 0.5; // a の範囲外の値が来た場合、デフォルト値 0.5 を使用
    }

    // 入力画像の外周を 0 で埋める。これは入力画像の端を背景(0)とみなすという仕様に基づく。
    // これは、領域が画像の端に達している場合でも、領域の外側を背景とみなすための処理である。
    // 画像の端の画素は、外接矩形の計算に影響を与えるため、この処理が必要となる。
    int padded_h = h + 2;
    int padded_w = w + 2;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    memset(padded_in, 0, padded_h * padded_w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + 1) * padded_w + (x + 1)] = in[y * w + x];
        }
    }

    // 外接矩形の計算
    int y0 = padded_h, y1 = 0, x0 = padded_w, x1 = 0;
    for (int y = 0; y < padded_h; y++) {
        for (int x = 0; x < padded_w; x++) {
            if (padded_in[y * padded_w + x] > 0.5) {
                if (y < y0) y0 = y;
                if (y > y1) y1 = y;
                if (x < x0) x0 = x;
                if (x > x1) x1 = x;
            }
        }
    }

    // 削る量の計算
    int my = (y1 - y0) * 0.5 * a;
    int mx = (x1 - x0) * 0.5 * a;

    // 出力画像の生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 外接矩形の内側の矩形に含まれる画素だけを残す
            if (y >= y0 + my && y <= y1 - my && x >= x0 + mx && x <= x1 - mx) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    free(padded_in);
}
