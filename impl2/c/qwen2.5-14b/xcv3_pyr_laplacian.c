void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の処理: BORDER_REFLECT_101 モードを採用
    // 左右の端を折り返す
    for (int y = 0; y < h; ++y) {
        out[y * w] = in[(y > 0 ? y - 1 : 0) * w + (w > 1 ? w - 2 : 0)];
        out[y * w + w - 1] = in[(y > 0 ? y - 1 : 0) * w + 1];
    }
    // 上下の端を折り返す
    for (int x = 0; x < w; ++x) {
        out[0 * w + x] = in[(h > 1 ? h - 2 : 0) * w + x];
        out[(h - 1) * w + x] = in[1 * w + x];
    }

    // ラプラシアンピラミッドの計算
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            // 中心画素
            double center = in[y * w + x];
            // 4近傍の平均
            double avg = (in[(y - 1) * w + x] + in[(y + 1) * w + x] +
                          in[y * w + x - 1] + in[y * w + x + 1]) / 4.0;
            // ラプラシアンピラミッドの計算
            double laplacian = center - avg;
            // 強調係数 a を適用
            double sharpened = center + (0.5 + 2.5 * a) * laplacian;
            // [0,1] にクリップ
            out[y * w + x] = (sharpened < 0.0) ? 0.0 : (sharpened > 1.0) ? 1.0 : sharpened;
        }
    }
}
