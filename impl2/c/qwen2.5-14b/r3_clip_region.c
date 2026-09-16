void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窗口の高さと幅を計算
    int wh = MAX(1, (int)round(a * h));
    int ww = MAX(1, (int)round(b * w));

    // 窗口の左上座標を計算
    int y0 = (h - wh) / 2;
    int x0 = (w - ww) / 2;

    // 入力画像の各画素を処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 画素が窗口内にあるかどうかを判定
            if (y >= y0 && y < y0 + wh && x >= x0 && x < x0 + ww) {
                // 入力画像の画素が領域に属する場合、出力画像の画素も領域に属す
                out[y * w + x] = (in[y * w + x] > 0.5) ? 1.0 : 0.0;
            } else {
                // 窗口外の画素は領域に属さない
                out[y * w + x] = 0.0;
            }
        }
    }
}
